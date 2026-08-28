"""Was nicht ins Repository gehört: die eigenen Seiten.

POSTKutsche ist quelloffen, die Seiten, die damit bespielt werden, sind es nicht.
Adressen, Artikeladressen und Mailadressen stehen deshalb nicht im Quelltext,
sondern in einer Datei unter `~/.config/postkutsche/`. Im Repository liegt nur
eine Beispielfassung mit `.example`-Adressen – die sind nach RFC 2606 für
genau diesen Zweck reserviert und können niemandem gehören.

Das ist keine Geheimniskrämerei um ihrer selbst willen. Ein öffentliches
Repository ist durchsuchbar, wird geklont und landet in Suchmaschinen; wer
darin nachliest, welche Läden jemand betreibt und mit welchen Herstellern er
arbeitet, bekommt ein Bild, das so nirgends stehen sollte. Und Adressen im
Quelltext haben die unangenehme Eigenschaft, dass sie auch dann noch dort
stehen, wenn man sie längst entfernt hat – in der Versionsgeschichte.

Ein Test wacht darüber: `test_keine_echten_adressen.py` verlangt, dass jede
Adresse im Repository entweder auf `.example` endet oder in einer kurzen
Positivliste steht.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ordner() -> Path:
    """Wo die eigenen Angaben liegen.

    `POSTKUTSCHE_CONFIG` sticht alles – das brauchen die Tests, damit sie nicht
    versehentlich die echte Konfiguration lesen oder überschreiben.
    """
    aus_umgebung = os.environ.get("POSTKUTSCHE_CONFIG")
    if aus_umgebung:
        return Path(aus_umgebung)
    return Path.home() / ".config" / "postkutsche"


def projektdatei() -> Path:
    return ordner() / "projekte.json"


def herstellerdatei() -> Path:
    return ordner() / "hersteller.json"


def projekte_lesen() -> list[dict[str, Any]]:
    """Die eigenen Projekte, wenn es welche gibt.

    Fehlt die Datei, ist das kein Fehler: Dann arbeitet man mit den Beispielen
    oder legt Projekte über die Kommandozeile an.
    """
    datei = projektdatei()
    if not datei.exists():
        return []
    return _lesen(datei, "projekte")


def hersteller_lesen() -> dict[str, dict[str, list[str]]]:
    """Zusätzliche Hersteller und ihre Modellreihen.

    Welche Marken jemand führt und wie deren Modellreihen heißen, ist
    Sortimentswissen und gehört niemandem sonst.
    """
    datei = herstellerdatei()
    if not datei.exists():
        return {}
    daten = _lesen(datei, "hersteller")
    if not isinstance(daten, dict):
        raise KonfigurationsFehler(
            f"{datei} muss ein Objekt enthalten, kein {type(daten).__name__}."
        )
    return daten


class KonfigurationsFehler(Exception):
    """Die Konfigurationsdatei lässt sich nicht lesen."""


def _lesen(datei: Path, was: str) -> Any:
    try:
        roh = datei.read_text(encoding="utf-8")
    except OSError as fehler:
        raise KonfigurationsFehler(f"{datei} nicht lesbar: {fehler}") from fehler
    try:
        return json.loads(roh)
    except json.JSONDecodeError as fehler:
        # Zeile und Spalte nennen. »Expecting ',' delimiter« allein hilft
        # niemandem, der eine 40-zeilige Datei von Hand geschrieben hat.
        raise KonfigurationsFehler(
            f"{datei} ist kein gültiges JSON – Zeile {fehler.lineno}, "
            f"Spalte {fehler.colno}: {fehler.msg}. "
            f"Erwartet wird eine Liste von {was}."
        ) from fehler


def rechte_pruefen(datei: Path) -> str | None:
    """Warnt, wenn eine Datei mit Zugangsdaten für andere lesbar ist.

    Gibt einen Text zurück, wenn etwas nicht stimmt – sonst None. Auf Systemen
    ohne Unix-Rechte (Windows) wird nicht geprüft, statt etwas Falsches zu
    behaupten.
    """
    if os.name != "posix" or not datei.exists():
        return None
    rechte = datei.stat().st_mode & 0o777
    if rechte & 0o077:
        return (
            f"{datei} ist auch für andere Benutzer lesbar (Rechte {rechte:o}). "
            f"Besser: chmod 600 {datei}"
        )
    return None
