"""Nach Mastodon senden.

Das einfachste der vier Netzwerke: Ein Token aus den Kontoeinstellungen, kein
Prüfverfahren, keine App-Freigabe. Deshalb steht es am Anfang – daran zeigt
sich, ob die Kette hält, ohne dass man wochenlang auf Meta wartet.

Zwei Eigenheiten, die man kennen muss:

**Das Bild wird hochgeladen, nicht verlinkt.** Anders als Instagram, wo Meta
sich das Bild von einer öffentlichen Adresse holt. Hier geht die Datei über
die Leitung, und man muss warten, bis der Server sie verarbeitet hat.

**Der Idempotenzschlüssel ist wichtiger, als er aussieht.** Bricht die
Verbindung ab, nachdem der Server den Beitrag angelegt hat, aber bevor die
Antwort ankommt, sieht es für uns nach einem Fehler aus. Ein zweiter Versuch
erzeugt dann einen zweiten Beitrag. Mit dem Schlüssel erkennt Mastodon die
Wiederholung und gibt denselben Beitrag zurück.
"""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from ..quellen.abrufen import KENNZEICHEN

#: Wie lange auf die Verarbeitung eines Bildes gewartet wird.
BILD_WARTEN = 60


class MastodonFehler(Exception):
    """Der Versand ging schief. Die Meldung ist für Menschen gedacht."""


def senden(
    instanz: str,
    token: str,
    text: str,
    bild: str | Path | None = None,
    bildbeschreibung: str = "",
    schluessel: str | None = None,
) -> dict[str, Any]:
    """Veröffentlicht einen Beitrag. Gibt id und url zurück.

    `schluessel` sollte über Wiederholungen hinweg gleich bleiben – dann legt
    Mastodon den Beitrag kein zweites Mal an.
    """
    stamm = instanz.rstrip("/")
    anhaenge = []

    if bild:
        anhaenge.append(_bild_hochladen(stamm, token, bild, bildbeschreibung))

    rumpf: dict[str, Any] = {"status": text}
    if anhaenge:
        rumpf["media_ids"] = anhaenge

    kopf = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Idempotency-Key": schluessel or str(uuid.uuid4()),
    }
    antwort = _anfragen(f"{stamm}/api/v1/statuses", kopf,
                        json.dumps(rumpf).encode("utf-8"))
    return {"id": str(antwort.get("id", "")), "url": antwort.get("url", "")}


def pruefen(instanz: str, token: str) -> dict[str, Any]:
    """Prüft Zugang und Konto, ohne etwas zu veröffentlichen."""
    stamm = instanz.rstrip("/")
    konto = _anfragen(
        f"{stamm}/api/v1/accounts/verify_credentials",
        {"Authorization": f"Bearer {token}"},
    )
    return {
        "name": konto.get("acct") or konto.get("username", ""),
        "anzeigename": konto.get("display_name", ""),
        "beitraege": konto.get("statuses_count", 0),
    }


def zeichengrenze(instanz: str) -> int:
    """Die Zeichengrenze der Instanz.

    Die Voreinstellung ist 500, aber einzelne Instanzen erlauben mehr. Wer
    seine Instanz kennt, kann mehr schreiben; wir fragen lieber nach, als 500
    zu behaupten.
    """
    try:
        angaben = _anfragen(f"{instanz.rstrip('/')}/api/v1/instance", {})
    except MastodonFehler:
        return 500
    grenze = (angaben.get("configuration", {})
              .get("statuses", {})
              .get("max_characters"))
    return int(grenze) if grenze else 500


# -- Innereien --------------------------------------------------------------


def _bild_hochladen(stamm: str, token: str, bild: str | Path,
                    beschreibung: str) -> str:
    pfad = Path(bild)
    if not pfad.is_file():
        raise MastodonFehler(f"Das Bild gibt es nicht: {pfad}")

    art = mimetypes.guess_type(pfad.name)[0] or "application/octet-stream"
    grenze = f"----postkutsche{uuid.uuid4().hex}"
    teile: list[bytes] = []

    def feld(name: str, wert: str) -> None:
        teile.append(
            f"--{grenze}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            f"{wert}\r\n".encode("utf-8")
        )

    if beschreibung:
        # Eine Bildbeschreibung ist auf Mastodon nicht Kür. Wer sie weglässt,
        # schließt Leute aus, die den Beitrag mit einer Sprachausgabe lesen.
        feld("description", beschreibung)

    teile.append(
        f"--{grenze}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{pfad.name}\"\r\nContent-Type: {art}\r\n\r\n".encode("utf-8")
    )
    teile.append(pfad.read_bytes())
    teile.append(f"\r\n--{grenze}--\r\n".encode("utf-8"))

    kopf = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={grenze}",
    }
    # v2 antwortet mit 202, wenn der Server noch rechnet - dann muss man warten.
    antwort = _anfragen(f"{stamm}/api/v2/media", kopf, b"".join(teile))
    kennung = str(antwort.get("id", ""))
    if not kennung:
        raise MastodonFehler("Der Server hat keine Bildnummer zurückgegeben.")

    if not antwort.get("url"):
        _auf_bild_warten(stamm, token, kennung)
    return kennung


def _auf_bild_warten(stamm: str, token: str, kennung: str) -> None:
    """Wartet, bis der Server das Bild verarbeitet hat.

    Ohne das Warten schlägt das Veröffentlichen mit »media not processed«
    fehl - und zwar nur bei großen Bildern, also genau dann, wenn man es beim
    Ausprobieren nicht merkt.
    """
    kopf = {"Authorization": f"Bearer {token}"}
    ende = time.monotonic() + BILD_WARTEN
    while time.monotonic() < ende:
        try:
            stand = _anfragen(f"{stamm}/api/v1/media/{kennung}", kopf)
            if stand.get("url"):
                return
        except MastodonFehler:
            pass
        time.sleep(1.5)
    raise MastodonFehler(
        f"Der Server hat das Bild nach {BILD_WARTEN} Sekunden nicht "
        "verarbeitet. Vielleicht ist es zu groß."
    )


def _anfragen(adresse: str, kopfzeilen: dict[str, str],
              daten: bytes | None = None) -> dict[str, Any]:
    anfrage = urllib.request.Request(adresse, data=daten)
    anfrage.add_header("User-Agent", KENNZEICHEN)
    for name, wert in kopfzeilen.items():
        anfrage.add_header(name, wert)

    try:
        with urllib.request.urlopen(anfrage, timeout=120) as antwort:
            roh = antwort.read()
    except urllib.error.HTTPError as fehler:
        raise MastodonFehler(_httpfehler(fehler)) from fehler
    except urllib.error.URLError as fehler:
        raise MastodonFehler(f"{adresse} nicht erreichbar: {fehler.reason}") from fehler

    if not roh:
        return {}
    try:
        return json.loads(roh)
    except json.JSONDecodeError as fehler:
        raise MastodonFehler(f"Der Server antwortet nicht mit JSON: {fehler}") from fehler


def _httpfehler(fehler: urllib.error.HTTPError) -> str:
    """Übersetzt die häufigen Fälle in etwas, das weiterhilft."""
    try:
        angaben = json.loads(fehler.read() or b"{}")
        meldung = str(angaben.get("error") or angaben.get("error_description") or "")
    except (json.JSONDecodeError, OSError):
        meldung = ""

    if fehler.code == 401:
        return ("Das Zugangstoken wird abgelehnt (401). Neu erzeugen unter "
                "Einstellungen › Entwicklung in deinem Mastodon-Konto.")
    if fehler.code == 403:
        return ("Das Token darf das nicht (403). Es braucht die Berechtigung "
                "»write:statuses«, für Bilder außerdem »write:media«.")
    if fehler.code == 422:
        return f"Der Beitrag wurde abgelehnt (422): {meldung or 'zu lang?'}"
    if fehler.code == 429:
        return "Zu viele Anfragen (429). Später noch einmal versuchen."
    return f"Der Server antwortet mit {fehler.code}{f': {meldung}' if meldung else ''}."
