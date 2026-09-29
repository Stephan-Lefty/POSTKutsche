"""Den Arbeitsstand mitnehmen und wieder zurückbringen.

**Keine Synchronisation, eine Stabübergabe.** Zu jedem Zeitpunkt ist genau
ein Ort der gültige. Das ist keine Bequemlichkeit, sondern die einzige
Bauweise, die hier nichts verlieren kann: Die Ablage ist eine SQLite-Datei,
und wer an zwei Orten Beiträge anlegt, hat zwei Dateien, die sich nicht
zusammenführen lassen. Eine gewinnt, die andere ist weg – und kein Programm
kann entscheiden, welche die richtige war.

Deshalb zwei Richtungen und eine Merkregel: **mitnehmen** schreibt von hier
nach dort, **zurückholen** von dort nach hier. Wer in die falsche Richtung
greift, bekommt eine Rückfrage statt eines stillen Überschreibens – erkennbar
daran, dass die Zielseite neuer ist als die Quelle.

Kopiert wird, nicht verschoben. Die abgegebene Seite bleibt liegen: Beim
ersten Mal will man vergleichen können, und eine Sicherung, die von selbst
entsteht, ist die beste.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import bilder, konfiguration

#: Die drei Stücke, aus denen ein Arbeitsstand besteht.
STUECKE = ("einstellungen", "ablage", "dokumente")

#: Woran man erkennt, wie frisch ein Stand ist. Die Ablage ist der einzige
#: Teil, der sich bei jeder Änderung anfasst – Bilder kommen hinzu, aber
#: ein geänderter Text ändert nur die Datenbank.
KENNDATEI = Path("ablage") / "postkutsche.db"


#: Der Ordner auf dem Datenträger. Alles liegt darunter, nichts im
#: Wurzelverzeichnis – so bleibt der Stick für anderes brauchbar, und man
#: sieht auf einen Blick, was zu POSTKutsche gehört.
UNTERORDNER = "POSTKutsche"

#: Woran ein Datenträger zu erkennen ist. Entweder er trägt einen Ordner
#: dieses Namens, oder er heißt selbst so. Nicht an einem gemerkten Pfad:
#: Der heißt am nächsten Rechner womöglich anders, und Gerätenummern und
#: UUIDs wären genau die Einstellung, die man unterwegs nachziehen müsste.
ERKENNUNG = "postkutsche"

#: Wo Wechseldatenträger unter Linux auftauchen.
WECHSELORTE = ("/run/media", "/media")


def datentraeger_suchen(benutzer: str | None = None) -> list[Path]:
    """Angesteckte Datenträger, die nach POSTKutsche aussehen.

    Gesucht wird nach dem Namen des Einhängepunktes, nicht nach einem
    gemerkten Pfad: `/run/media/name/POSTKUTSCHE` heißt am nächsten Rechner
    vielleicht `/media/name/POSTKUTSCHE`, und eine gespeicherte Adresse wäre
    dort falsch.
    """
    import getpass

    benutzer = benutzer or getpass.getuser()
    gefunden = []
    for ort in WECHSELORTE:
        wurzel = Path(ort) / benutzer
        if not wurzel.is_dir():
            continue
        try:
            for eintrag in sorted(wurzel.iterdir()):
                if not eintrag.is_dir():
                    continue
                # Ein Ordner »POSTKutsche« darauf zählt – dann darf der
                # Datenträger heißen, wie er will, und für anderes dienen.
                if (eintrag / UNTERORDNER).is_dir():
                    gefunden.append(eintrag)
                elif ERKENNUNG in eintrag.name.lower():
                    gefunden.append(eintrag)
        except OSError:
            continue
    return gefunden


class UebergabeFehler(Exception):
    """Die Übergabe war nicht möglich. Die Meldung ist für Menschen."""


def hier(ablage_pfad: Path | str) -> dict[str, Path]:
    """Wo der lokale Stand liegt."""
    ablage_pfad = Path(ablage_pfad)
    return {
        "einstellungen": konfiguration.ordner(),
        "ablage": ablage_pfad.parent,
        "dokumente": bilder.dokumentenordner() / bilder.SAMMELORDNER,
    }


def dort(ziel: Path | str) -> dict[str, Path]:
    """Wo der Stand auf dem Datenträger liegt – immer unter `POSTKutsche/`."""
    wurzel = Path(ziel)
    # Zeigt das Ziel schon auf den Unterordner, nicht doppelt anhängen.
    if wurzel.name != UNTERORDNER:
        wurzel = wurzel / UNTERORDNER
    return {name: wurzel / name for name in STUECKE}


def stand(orte: dict[str, Path]) -> dict[str, Any]:
    """Wie frisch ein Stand ist – und ob es überhaupt einen gibt."""
    kenn = orte["ablage"] / KENNDATEI.name
    if not kenn.exists():
        return {"da": False, "zeit": None, "dateien": 0, "groesse": 0}
    dateien = groesse = 0
    for ort in orte.values():
        if not ort.exists():
            continue
        for datei in ort.rglob("*"):
            if datei.is_file():
                dateien += 1
                groesse += datei.stat().st_size
    return {"da": True, "zeit": kenn.stat().st_mtime,
            "dateien": dateien, "groesse": groesse}


#: Ab wann zwei Stände als verschieden gelten. Direkt nach einer Übergabe
#: unterscheiden sich die Zeitstempel um Sekundenbruchteile – je nachdem,
#: wie lange das Kopieren dauerte und was das Dateisystem an Auflösung
#: mitbringt. Ohne diese Spanne meldete die Oberfläche am 2026-09-29 »dort
#: ist der neuere Stand«, unmittelbar nachdem dorthin kopiert worden war.
GLEICH_SPANNE = 120


def vergleich(ablage_pfad: Path | str, ziel: Path | str) -> dict[str, Any]:
    """Was auf beiden Seiten liegt – für die Anzeige vor dem Klick."""
    a, b = stand(hier(ablage_pfad)), stand(dort(ziel))
    neuer = None
    if a["da"] and b["da"]:
        if abs(a["zeit"] - b["zeit"]) <= GLEICH_SPANNE:
            neuer = "gleich"
        else:
            neuer = "hier" if a["zeit"] > b["zeit"] else "dort"
    elif a["da"]:
        neuer = "hier"
    elif b["da"]:
        neuer = "dort"
    return {"hier": a, "dort": b, "neuer": neuer, "ziel": str(ziel)}


def uebergeben(ablage_pfad: Path | str, ziel: Path | str, richtung: str,
               trotzdem: bool = False) -> dict[str, Any]:
    """Kopiert den Stand in eine Richtung: »mitnehmen« oder »zurueckholen«.

    `trotzdem` übergeht die Warnung, dass die Zielseite neuer ist. Ohne den
    Schalter wird abgebrochen – das ist der einzige Weg, wie man sich in
    diesem Ablauf schaden kann, und deshalb der einzige, der nachfragt.
    """
    if richtung not in ("mitnehmen", "zurueckholen"):
        raise UebergabeFehler(f"Unbekannte Richtung: {richtung}")

    von = hier(ablage_pfad) if richtung == "mitnehmen" else dort(ziel)
    nach = dort(ziel) if richtung == "mitnehmen" else hier(ablage_pfad)
    quelle, zielstand = stand(von), stand(nach)

    if not quelle["da"]:
        wo = "hier" if richtung == "mitnehmen" else "auf dem Datenträger"
        raise UebergabeFehler(f"Es gibt {wo} keinen Arbeitsstand zum Kopieren.")

    if (not trotzdem and zielstand["da"] and quelle["zeit"]
            and zielstand["zeit"] > quelle["zeit"]):
        raise UebergabeFehler(
            "Auf der Zielseite liegt neuere Arbeit als auf der Quellseite. "
            "Kopieren würde sie überschreiben. Wenn das gewollt ist, noch "
            "einmal mit »trotzdem«.")

    kopiert = []
    for name in STUECKE:
        if not von[name].exists():
            continue
        try:
            nach[name].parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(von[name], nach[name], dirs_exist_ok=True)
        except OSError as fehler:
            raise UebergabeFehler(
                f"»{name}« ließ sich nicht kopieren: {fehler}") from fehler
        kopiert.append(name)

    # Zugangsdaten sind auch am neuen Ort schutzbedürftig. Auf FAT bleibt
    # das wirkungslos - dort hilft nur ein anderes Dateisystem.
    zugaenge = nach["einstellungen"] / "zugaenge.json"
    if zugaenge.exists():
        try:
            zugaenge.chmod(0o600)
        except OSError:
            pass

    return {"richtung": richtung, "kopiert": kopiert,
            "dateien": quelle["dateien"], "groesse": quelle["groesse"]}
