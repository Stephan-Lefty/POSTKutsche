"""Claude über die Kommandozeile aufrufen: `claude -p`.

Nutzt das vorhandene Abo statt eines API-Schlüssels; je Beitrag entstehen
keine zusätzlichen Kosten. Der Preis dafür ist, dass Claude Code auf der
Maschine installiert und angemeldet sein muss - auf einem Server, der nur
sendet, wäre der API-Weg der bessere (siehe `api.py`).

**Zum Ausgabeformat.** `--output-format json` liefert ein Hüllobjekt, in dem
der eigentliche Text unter »result« steht. Weil sich das zwischen Fassungen
geändert hat und wieder ändern kann, wird beides behandelt: Steckt in der
Antwort ein Hüllobjekt, wird ausgepackt; steht das JSON direkt da, wird es
direkt genommen. Ein Werkzeug, das bei einem Versionssprung des Aufgerufenen
stehen bleibt, ist ärgerlicher als ein paar Zeilen Vorsicht.

**Keine Werkzeuge.** Der Aufruf soll einen Text schreiben, nicht im
Dateisystem herumsuchen. Deshalb wird das Arbeitsverzeichnis auf einen leeren
Ordner gelegt - was Claude dort fände, wäre nichts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any

from . import vorlagen

#: Wie lange ein Aufruf höchstens dauern darf. Vier Fassungen aus einem langen
#: Blogbeitrag brauchen gut eine Minute; drei sind reichlich Luft.
ZEITLIMIT = 180

BEFEHL = "claude"


class ClaudeFehlt(Exception):
    """Claude Code ist nicht installiert oder nicht im Suchpfad."""


class ClaudeFehler(Exception):
    """Der Aufruf ist schiefgegangen. Die Meldung ist für Menschen gedacht."""


def vorhanden() -> bool:
    """Ob `claude` aufrufbar ist."""
    return shutil.which(BEFEHL) is not None


def fassungen(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    modell: str | None = None,
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Lässt Claude die Fassungen für die genannten Netzwerke schreiben.

    Gibt je Netzwerk ein Wörterbuch mit »text«, »schlagworte« und
    »rueckfrage« zurück - genau das, was `ablage.fassung_setzen` erwartet.
    """
    text = _aufrufen(
        vorlagen.anweisung(inhalt, fuer, projekt, zusatz, frueher, wissen), modell
    )
    return vorlagen.antwort_lesen(text, fuer)


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
) -> dict[str, Any]:
    """Bessert einen Text mit der Antwort auf die Rückfrage nach."""
    text = _aufrufen(
        vorlagen.nachbesserung(inhalt, netzwerk, bisher, frage, antwort, zusatz)
    )
    return vorlagen.antwort_lesen(text, [netzwerk])[netzwerk]


def _aufrufen(anweisung: str, modell: str | None = None) -> str:
    if not vorhanden():
        raise ClaudeFehlt(
            "»claude« ist nicht im Suchpfad. Claude Code installieren "
            "(npm install -g @anthropic-ai/claude-code), danach einmal "
            "»claude« starten und mit /login anmelden."
        )

    befehl = [BEFEHL, "-p", anweisung, "--output-format", "json"]
    if modell:
        befehl += ["--model", modell]

    # Der Aufruf soll schreiben, nicht stöbern. Ein leeres Arbeitsverzeichnis
    # nimmt ihm die Gelegenheit, im Projekt herumzulesen.
    with tempfile.TemporaryDirectory(prefix="postkutsche-") as leer:
        try:
            lauf = subprocess.run(
                befehl,
                capture_output=True,
                text=True,
                timeout=ZEITLIMIT,
                cwd=leer,
                # Ohne das erbt der Aufruf unsere eigene Sitzung samt
                # Berechtigungen - er soll für sich stehen.
                env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "postkutsche"},
            )
        except FileNotFoundError as fehler:
            raise ClaudeFehlt(str(fehler)) from fehler
        except subprocess.TimeoutExpired as fehler:
            raise ClaudeFehler(
                f"Claude hat nach {ZEITLIMIT} Sekunden nicht geantwortet."
            ) from fehler

    if lauf.returncode != 0:
        meldung = (lauf.stderr or lauf.stdout or "").strip()
        if "login" in meldung.lower() or "not logged in" in meldung.lower():
            raise ClaudeFehler(
                "Claude Code ist nicht angemeldet. Einmal »claude« starten "
                "und /login ausführen."
            )
        raise ClaudeFehler(
            f"claude endete mit Rückgabewert {lauf.returncode}: {meldung[:300]}"
        )

    return _auspacken(lauf.stdout)


def _auspacken(roh: str) -> str:
    """Holt den Antworttext aus dem Hüllobjekt von --output-format json.

    Steht dort kein Hüllobjekt, wird die Ausgabe unverändert zurückgegeben -
    dann hat entweder eine andere Fassung geantwortet oder das Format hat sich
    geändert, und `vorlagen.antwort_lesen` kommt damit ebenfalls zurecht.
    """
    import json

    try:
        huelle = json.loads(roh)
    except json.JSONDecodeError:
        return roh

    if not isinstance(huelle, dict):
        return roh

    if huelle.get("is_error"):
        raise ClaudeFehler(
            f"Claude meldet einen Fehler: {str(huelle.get('result'))[:300]}"
        )

    for feld in ("result", "text", "content"):
        wert = huelle.get(feld)
        if isinstance(wert, str) and wert.strip():
            return wert
    return roh
