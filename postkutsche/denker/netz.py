"""Ein Aufruf über die Leitung – für alle Dienste, die auf JSON hören.

Hier steht nur, was Anthropic und die OpenAI-kompatiblen Dienste gemeinsam
haben: JSON hin, JSON zurück, und Fehlermeldungen, aus denen ein Mensch
schließen kann, was zu tun ist. Was die beiden unterscheidet – Kopfzeilen,
Aufbau der Anfrage, wo der Text in der Antwort steht –, steht in
`anthropisch.py` und `offen.py`.

**Ohne Fremdpakete.** Weder `anthropic` noch `openai` noch `requests`: Die
Standardbibliothek kann POST mit JSON, und ein Werkzeug, das man einmal
einrichtet und jahrelang laufen lässt, soll nicht an drei Bibliotheken
hängen, die jede ihren eigenen Veröffentlichungsrhythmus haben.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

#: Wie lange ein Aufruf höchstens dauern darf. Vier Fassungen aus einem langen
#: Blogbeitrag brauchen gut eine Minute; drei Minuten sind reichlich Luft.
ZEITLIMIT = 180


class DenkerFehler(Exception):
    """Der Aufruf ist schiefgegangen. Die Meldung ist für Menschen gedacht."""


class DenkerFehlt(DenkerFehler):
    """Das Werkzeug ist gar nicht da – Claude Code fehlt, ein Schlüssel fehlt.

    Eine eigene Klasse, weil die Abhilfe eine andere ist: Ein Fehler beim
    Aufruf kann beim nächsten Mal weg sein, ein fehlendes Programm nicht.
    Sie erbt von `DenkerFehler`, damit ein Aufrufer, der nur »ging nicht«
    unterscheiden muss, mit einem `except` auskommt.
    """


def json_senden(adresse: str, kopfzeilen: dict[str, str],
                rumpf: dict[str, Any], zeitlimit: int = ZEITLIMIT) -> dict[str, Any]:
    """Schickt JSON hin und gibt JSON zurück.

    Fehler werden in `DenkerFehler` übersetzt, weil die Meldung in der
    Oberfläche landet. Eine rohe `HTTPError`-Ausgabe hilft dort niemandem;
    »Schlüssel abgelehnt« oder »zu viele Anfragen« schon.
    """
    daten = json.dumps(rumpf, ensure_ascii=False).encode("utf-8")
    anfrage = urllib.request.Request(adresse, data=daten, method="POST")
    for name, wert in kopfzeilen.items():
        anfrage.add_header(name, wert)

    try:
        with urllib.request.urlopen(anfrage, timeout=zeitlimit) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as fehler:
        raise DenkerFehler(_httpfehler_lesen(fehler)) from fehler
    except urllib.error.URLError as fehler:
        raise DenkerFehler(
            f"{adresse} ist nicht erreichbar: {fehler.reason}"
        ) from fehler
    except TimeoutError as fehler:
        raise DenkerFehler(
            f"Keine Antwort innerhalb von {zeitlimit} Sekunden."
        ) from fehler

    try:
        ergebnis = json.loads(roh)
    except json.JSONDecodeError as fehler:
        raise DenkerFehler(
            f"Die Antwort war kein JSON. Anfang: {roh[:200]!r}"
        ) from fehler

    if not isinstance(ergebnis, dict):
        raise DenkerFehler(f"Unerwartete Antwort: {roh[:200]!r}")
    return ergebnis


def _httpfehler_lesen(fehler: urllib.error.HTTPError) -> str:
    """Macht aus einem Fehlercode einen Satz, der weiterhilft.

    Die Dienste legen ihre Begründung in den Rumpf, nicht in den Statustext –
    wer nur »HTTP Error 400: Bad Request« meldet, verschweigt genau die
    Zeile, die sagt, welches Feld falsch war.
    """
    try:
        rumpf = fehler.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 – der Rumpf ist Beiwerk, der Code zählt
        rumpf = ""

    grund = _grund_finden(rumpf) or rumpf.strip()[:300]
    anfang = {
        400: "Die Anfrage wurde abgelehnt",
        401: "Der Zugangsschlüssel wurde nicht angenommen",
        403: "Der Zugangsschlüssel darf das nicht",
        404: "Diese Adresse oder dieses Modell gibt es nicht",
        413: "Die Anfrage ist zu groß",
        429: "Zu viele Anfragen – oder das Guthaben ist aufgebraucht",
    }.get(fehler.code)
    if anfang is None:
        anfang = ("Der Dienst hat einen Fehler gemeldet; ein späterer Versuch "
                  "kann klappen" if fehler.code >= 500 else "Fehler")

    return f"{anfang} ({fehler.code}){': ' + grund if grund else '.'}"


def _grund_finden(rumpf: str) -> str:
    """Die Begründung aus dem Fehlerrumpf, egal welcher Dienst antwortet."""
    try:
        daten = json.loads(rumpf)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(daten, dict):
        return ""
    fehler = daten.get("error")
    if isinstance(fehler, dict):
        return str(fehler.get("message") or "")[:300]
    if isinstance(fehler, str):
        return fehler[:300]
    return str(daten.get("message") or "")[:300]
