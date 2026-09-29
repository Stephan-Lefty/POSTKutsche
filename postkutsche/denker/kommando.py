"""Claude über die Kommandozeile aufrufen: `claude -p`.

Nutzt das vorhandene Abo statt eines API-Schlüssels; je Beitrag entstehen
keine zusätzlichen Kosten. Der Preis dafür ist, dass Claude Code auf der
Maschine installiert und angemeldet sein muss - auf einem Server, der nur
sendet, ist `anthropisch.py` der bessere Weg, und wer gar nichts bezahlen
will, nimmt `offen.py` mit einem Modell auf dem eigenen Rechner.

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
from .netz import ZEITLIMIT, DenkerFehler, DenkerFehlt

BEFEHL = "claude"

#: Umgebungsvariable, über die Claude Code einen langlebigen Zugang annimmt.
#: `claude setup-token` legt einen an, der ein Jahr gilt - der Weg für einen
#: Dienst, hinter dem niemand sitzt, der sich alle paar Tage neu anmeldet.
ZUGANGSVARIABLE = "CLAUDE_CODE_OAUTH_TOKEN"

#: Die alten Namen dieses Moduls. Seit es vier Wege gibt, heißen die Fehler
#: nicht mehr nach Claude - aber ein Umbenennen in jedem Aufrufer wäre Arbeit
#: ohne Gewinn.
ClaudeFehlt = DenkerFehlt
ClaudeFehler = DenkerFehler


def vorhanden() -> bool:
    """Ob `claude` aufrufbar ist."""
    return shutil.which(BEFEHL) is not None


#: Wie lange eine Probe höchstens dauern darf. Kürzer als `ZEITLIMIT`, weil
#: hier niemand auf einen Text wartet, sondern auf ein Ja oder Nein.
PROBEZEIT = 60


def erreichbar(einstellungen: dict[str, Any] | None = None) -> bool:
    """Ob Claude Code antwortet – geprüft mit einer winzigen Anfrage.

    Der Suchpfad allein genügt nicht: Eine abgelaufene Anmeldung merkt man
    ihm nicht an, und dann meldet »denker pruefen« »Antwortet«, ohne je
    gefragt zu haben. Die anderen Wege fragen auch nach.
    """
    if not vorhanden():
        return False
    try:
        _aufrufen(
            'Antworte genau mit: {"fassungen": {}}',
            (einstellungen or {}).get("modell"),
            zeitlimit=PROBEZEIT,
            schluessel=(einstellungen or {}).get("schluessel"),
        )
    except DenkerFehler:
        return False
    return True


def fassungen(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    modell: str | None = None,
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
    art: str = vorlagen.PRODUKT,
    einstellungen: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Lässt Claude die Fassungen für die genannten Netzwerke schreiben.

    Gibt je Netzwerk ein Wörterbuch mit »text«, »schlagworte« und
    »rueckfrage« zurück - genau das, was `ablage.fassung_setzen` erwartet.
    """
    text = _aufrufen(
        vorlagen.anweisung(inhalt, fuer, projekt, zusatz, frueher, wissen, art),
        modell or (einstellungen or {}).get("modell"),
        schluessel=(einstellungen or {}).get("schluessel"),
    )
    return vorlagen.antwort_lesen(text, fuer)


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
    einstellungen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bessert einen Text mit der Antwort auf die Rückfrage nach."""
    text = _aufrufen(
        vorlagen.nachbesserung(inhalt, netzwerk, bisher, frage, antwort, zusatz),
        (einstellungen or {}).get("modell"),
        schluessel=(einstellungen or {}).get("schluessel"),
    )
    return vorlagen.antwort_lesen(text, [netzwerk])[netzwerk]


def _aufrufen(anweisung: str, modell: str | None = None,
              zeitlimit: int = ZEITLIMIT, schluessel: str | None = None) -> str:
    if not vorhanden():
        raise DenkerFehlt(
            "»claude« ist nicht im Suchpfad. Claude Code installieren "
            "(npm install -g @anthropic-ai/claude-code), danach einmal "
            "»claude« starten und mit /login anmelden."
        )

    befehl = [BEFEHL, "-p", anweisung, "--output-format", "json"]
    if modell:
        befehl += ["--model", modell]

    # Ein hinterlegter Zugang schlägt die Anmeldung auf der Maschine. Er geht
    # über die Umgebung des Kindprozesses, nicht über die Befehlszeile - was
    # dort steht, liest jeder mit »ps«.
    umgebung = {**os.environ, "CLAUDE_CODE_ENTRYPOINT": "postkutsche"}
    if schluessel:
        umgebung[ZUGANGSVARIABLE] = schluessel

    # Der Aufruf soll schreiben, nicht stöbern. Ein leeres Arbeitsverzeichnis
    # nimmt ihm die Gelegenheit, im Projekt herumzulesen.
    with tempfile.TemporaryDirectory(prefix="postkutsche-") as leer:
        try:
            lauf = subprocess.run(
                befehl,
                capture_output=True,
                text=True,
                timeout=zeitlimit,
                cwd=leer,
                # Ohne das erbt der Aufruf unsere eigene Sitzung samt
                # Berechtigungen - er soll für sich stehen.
                env=umgebung,
            )
        except FileNotFoundError as fehler:
            raise DenkerFehlt(str(fehler)) from fehler
        except subprocess.TimeoutExpired as fehler:
            raise DenkerFehler(
                f"Claude hat nach {zeitlimit} Sekunden nicht geantwortet."
            ) from fehler

    if lauf.returncode != 0:
        meldung = (lauf.stderr or "").strip() or _grund(lauf.stdout)
        _anmeldung_pruefen(meldung)
        raise DenkerFehler(
            f"claude endete mit Rückgabewert {lauf.returncode}: {meldung[:300]}"
        )

    return _auspacken(lauf.stdout)


#: Woran eine abgelaufene oder fehlende Anmeldung zu erkennen ist. »login«
#: allein genügt nicht: Beim abgelaufenen Zugang lautet die Meldung »Failed to
#: authenticate: OAuth session expired and could not be refreshed« und enthält
#: das Wort nirgends.
ANMELDEWORTE = ("login", "logged in", "authenticate", "oauth", "unauthorized")


def _anmeldung_pruefen(meldung: str) -> None:
    """Wirft die Anleitung zum Anmelden, wenn die Meldung danach aussieht."""
    klein = meldung.lower()
    if any(wort in klein for wort in ANMELDEWORTE):
        raise DenkerFehler(
            "Claude Code ist nicht angemeldet. Einmal »claude« starten "
            f"und /login ausführen. ({meldung[:200]})"
        )


def _grund(roh: str) -> str:
    """Holt den lesbaren Grund aus dem Hüllobjekt eines gescheiterten Laufs.

    Scheitert der Aufruf, steht auf der Fehlerausgabe oft nichts und auf der
    normalen Ausgabe das volle Hüllobjekt - der Grund ganz am Ende, unter
    »result«. Wer das JSON ungelesen weiterreicht, kürzt es auf 300 Zeichen
    und schneidet damit genau die Auskunft ab, um die es geht.
    """
    import json

    roh = (roh or "").strip()
    try:
        huelle = json.loads(roh)
    except json.JSONDecodeError:
        return roh
    if not isinstance(huelle, dict):
        return roh
    for feld in ("result", "error", "message"):
        wert = huelle.get(feld)
        if isinstance(wert, str) and wert.strip():
            return wert.strip()
    return roh


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
        grund = _grund(roh)
        _anmeldung_pruefen(grund)
        raise DenkerFehler(f"Claude meldet einen Fehler: {grund[:300]}")

    for feld in ("result", "text", "content"):
        wert = huelle.get(feld)
        if isinstance(wert, str) and wert.strip():
            return wert
    return roh


def roh(anweisung: str, einstellungen: dict[str, Any] | None = None) -> str:
    """Eine fertige Anweisung stellen und die Antwort unausgewertet liefern.

    Für Aufrufer, die ihre Anweisung selbst bauen – die Wochenformate
    verlangen neben den Fassungen auch die Felder der Grafik.
    """
    e = einstellungen or {}
    return _aufrufen(anweisung, e.get("modell"), schluessel=e.get("schluessel"))
