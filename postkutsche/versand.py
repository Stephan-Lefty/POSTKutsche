"""Fällige Beiträge senden.

Der Teil, der von selbst laufen soll – aus einem systemd-Timer heraus, alle
paar Minuten. Deshalb gilt hier eine Regel strenger als anderswo: **Im
Zweifel nicht senden.** Ein Beitrag, der einen Tag später erscheint, ist ein
Ärgernis; einer, der zweimal erscheint oder falsch, steht öffentlich.

Vier Bedingungen, alle müssen erfüllt sein:

- Der Beitrag ist freigegeben – also gelesen und gewollt.
- Sein Projekt ist aktiv, nicht pausiert.
- Der Zeitpunkt ist erreicht.
- Die Fassung ist noch offen, also nicht schon gesendet.

**Verspätung wird vermerkt, nicht verschwiegen.** Läuft der Rechner nachts
nicht, geht ein Beitrag von 6:30 Uhr erst um 9 raus. Das ist in Ordnung, aber
man soll es sehen können.
"""

from __future__ import annotations

import contextlib

from typing import Any

import tempfile
from pathlib import Path

from . import ablage as ablage_modul
from . import zeiten, zugaenge
from .netzwerke import mastodon
from .quellen.abrufen import AbrufFehler, holen as netz_holen

#: Ab wann eine Verspätung erwähnenswert ist.
VERSPAETUNG_MELDEN = 3600


class VersandFehler(Exception):
    """Etwas fehlte. Die Meldung ist für Menschen gedacht."""


def faellige(ablage, bis: str | None = None) -> list[dict[str, Any]]:
    """Was jetzt raus müsste – ohne es zu senden."""
    grenze = bis or zeiten.jetzt_utc()
    offen = []
    for beitrag in ablage.faellige_beitraege(grenze):
        for fassung in ablage.fassungen(int(beitrag["id"])):
            if fassung["zustand"] != ablage_modul.FASSUNG_OFFEN:
                continue
            if fassung["versandart"] != ablage_modul.VERSAND_SCHNITTSTELLE:
                continue  # Handbetrieb wird nicht von selbst gesendet
            offen.append({
                "beitrag": int(beitrag["id"]),
                "projekt": beitrag["projekt_kennung"],
                "geplant": beitrag["geplant"],
                "fassung": int(fassung["id"]),
                "netzwerk": fassung["netzwerk"],
                "text": fassung["text"],
                "schlagworte": fassung["schlagworte"],
                "bild_pfad": fassung["bild_pfad"],
            })
    return offen


def senden(ablage, konten: dict[str, dict[str, Any]], bis: str | None = None,
           probelauf: bool = False, melden=print) -> tuple[int, int]:
    """Sendet, was fällig ist. Gibt (gesendet, gescheitert) zurück."""
    anstehend = faillige_pruefen(faellige(ablage, bis))
    if not anstehend:
        melden("Nichts fällig.")
        return 0, 0

    gut = schlecht = 0
    for eintrag in anstehend:
        kennzeichen = f"{eintrag['projekt']} → {eintrag['netzwerk']}"
        verspaetet = _verspaetung(eintrag["geplant"])
        zusatz = f" (verspätet um {verspaetet})" if verspaetet else ""

        if probelauf:
            melden(f"  würde senden: {kennzeichen}{zusatz}")
            gut += 1
            continue

        try:
            ergebnis = _eine_fassung(eintrag, konten)
        except Exception as fehler:  # noqa: BLE001
            ablage.fassung_vermerken(
                eintrag["fassung"], ablage_modul.FASSUNG_GESCHEITERT,
                fehler=str(fehler)[:400],
            )
            melden(f"  gescheitert: {kennzeichen} – {fehler}")
            schlecht += 1
            continue

        ablage.fassung_vermerken(
            eintrag["fassung"], ablage_modul.FASSUNG_GESENDET,
            fremd_adresse=ergebnis.get("url"),
        )
        melden(f"  gesendet: {kennzeichen}{zusatz} {ergebnis.get('url', '')}")
        gut += 1

    if not probelauf:
        for beitrag in {e["beitrag"] for e in anstehend}:
            _beitrag_abschliessen(ablage, beitrag)

    return gut, schlecht


def faillige_pruefen(eintraege: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sortiert nach Termin – Ältestes zuerst, damit die Reihenfolge stimmt."""
    return sorted(eintraege, key=lambda e: e["geplant"])


def _eine_fassung(eintrag: dict[str, Any],
                  konten: dict[str, dict[str, Any]]) -> dict[str, Any]:
    netz = eintrag["netzwerk"]
    konto = konten.get(netz)
    if not konto:
        raise VersandFehler(
            f"Für {netz} ist kein Konto eingerichtet. "
            f"Anlegen mit: postkutsche konto neu {netz} <kennung>"
        )

    if netz != "mastodon":
        raise VersandFehler(
            f"Der Versand nach {netz} ist noch nicht gebaut. "
            "Bis dahin läuft er von Hand über den Kalender."
        )

    text = eintrag["text"]
    if eintrag["schlagworte"]:
        schlagworte = " ".join(f"#{w}" for w in eintrag["schlagworte"].split())
        text = f"{text}\n\n{schlagworte}"

    with _bild_bereitstellen(eintrag.get("bild_pfad")) as bild:
        return mastodon.senden(
            instanz=konto["instanz"],
            token=zugaenge.holen(konto["kennung"]),
            text=text,
            bild=bild,
            bildbeschreibung=konto.get("bildbeschreibung", ""),
            # Derselbe Schlüssel über Wiederholungen hinweg: Bricht die
            # Verbindung nach dem Anlegen ab, erzeugt der zweite Versuch
            # keinen zweiten Beitrag.
            schluessel=f"postkutsche-fassung-{eintrag['fassung']}",
        )


@contextlib.contextmanager
def _bild_bereitstellen(bild: str | None):
    """Sorgt dafür, dass das Bild als Datei vorliegt.

    Im Feld kann beides stehen: ein Pfad auf der Platte oder eine Adresse im
    Netz. Beim Entwerfen wird die Adresse aus der Quelle eingetragen - das
    Herunterladen und Zuschneiden ist eine eigene Etappe und noch nicht
    gebaut. Bis dahin wird hier geholt, was gebraucht wird.

    Mastodon lädt die Datei hoch; eine Adresse hilft ihm nicht. (Instagram ist
    genau umgekehrt - dort holt Meta sich das Bild selbst von einer
    öffentlichen Adresse.)
    """
    if not bild:
        yield None
        return

    if not str(bild).startswith(("http://", "https://")):
        yield bild
        return

    endung = Path(str(bild).split("?")[0]).suffix or ".jpg"
    ziel = None
    try:
        roh = netz_holen(str(bild))
    except AbrufFehler as fehler:
        raise VersandFehler(f"Das Bild ließ sich nicht holen: {fehler}") from fehler

    try:
        with tempfile.NamedTemporaryFile(
            prefix="postkutsche-bild-", suffix=endung, delete=False
        ) as datei:
            datei.write(roh)
            ziel = datei.name
        yield ziel
    finally:
        if ziel:
            Path(ziel).unlink(missing_ok=True)


def _beitrag_abschliessen(ablage, beitrag_id: int) -> None:
    """Setzt den Beitrag auf erledigt, wenn keine Fassung mehr offen ist."""
    zustaende = {f["zustand"] for f in ablage.fassungen(beitrag_id)}
    if ablage_modul.FASSUNG_OFFEN in zustaende:
        return
    if ablage_modul.FASSUNG_GESCHEITERT in zustaende:
        return  # Gescheitertes bleibt sichtbar, nicht stillschweigend erledigt
    ablage.beitrag_zustand(beitrag_id, ablage_modul.BEITRAG_ERLEDIGT)


def _verspaetung(geplant: str) -> str | None:
    sekunden = (zeiten.lesen(zeiten.jetzt_utc()) - zeiten.lesen(geplant)).total_seconds()
    if sekunden < VERSPAETUNG_MELDEN:
        return None
    stunden = int(sekunden // 3600)
    if stunden < 24:
        return f"{stunden} Stunden"
    return f"{stunden // 24} Tage"


def konten_lesen(ablage) -> dict[str, dict[str, Any]]:
    """Die eingerichteten Konten, nach Netzwerk – ohne Token."""
    import json as _json

    ergebnis: dict[str, dict[str, Any]] = {}
    for zeile in ablage.konten():
        einstellungen = _json.loads(zeile["einstellungen"] or "{}")
        ergebnis[zeile["netzwerk"]] = {
            "kennung": zeile["kennung"],
            "anzeigename": zeile["anzeigename"],
            **einstellungen,
        }
    return ergebnis
