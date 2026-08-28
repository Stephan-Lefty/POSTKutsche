"""Zeitrechnung an einer Stelle.

In der Ablage steht ausnahmslos UTC, angezeigt und eingegeben wird Ortszeit.
Die Umrechnung gehört deshalb genau hierher und nirgendwo sonst hin – sobald
sie an zwei Stellen steht, weicht eine davon irgendwann ab, und man merkt es
am letzten Sonntag im Oktober.

Dieser Sonntag ist auch der Grund, warum nicht einfach eine feste Stundenzahl
addiert wird: Zwischen Sommer- und Winterzeit sind es mal eine, mal zwei
Stunden, und in der Nacht der Umstellung gibt es eine Ortszeit zweimal.
`zoneinfo` weiß das, eine Konstante nicht.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Wo Stephan sitzt. Bewusst keine Systemabfrage: Der POSTKutsche richtet sich nach
# dem Publikum in Deutschland, auch wenn der Rechner im Urlaub woanders steht.
ORTSZONE = ZoneInfo("Europe/Berlin")

# So sehen die Zeitstempel in der Ablage aus. Sekundengenau reicht; Sekunden­
# bruchteile machen die Datei nur unleserlich.
FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def jetzt_utc() -> str:
    """Der aktuelle Zeitpunkt, so wie er in die Ablage gehört."""
    return datetime.now(timezone.utc).strftime(FORMAT)


def lesen(stempel: str) -> datetime:
    """Wandelt einen Zeitstempel aus der Ablage in ein datetime mit UTC-Zone."""
    return datetime.strptime(stempel, FORMAT).replace(tzinfo=timezone.utc)


def schreiben(zeitpunkt: datetime) -> str:
    """Wandelt ein datetime in einen Zeitstempel für die Ablage.

    Ein datetime ohne Zeitzone wird als Ortszeit verstanden. Das ist die
    freundlichere Annahme: Wer im Programm `datetime(2026, 9, 1, 18, 0)`
    schreibt, meint sechs Uhr abends hier, nicht in Greenwich.
    """
    if zeitpunkt.tzinfo is None:
        zeitpunkt = zeitpunkt.replace(tzinfo=ORTSZONE)
    return zeitpunkt.astimezone(timezone.utc).strftime(FORMAT)


def nach_ortszeit(stempel: str) -> datetime:
    """Zeitstempel aus der Ablage als Ortszeit – so wird er angezeigt."""
    return lesen(stempel).astimezone(ORTSZONE)


def von_ortszeit(text: str) -> str:
    """Eingabe wie »2026-09-01 18:00« oder »2026-09-01T18:00« nach UTC.

    Nimmt entgegen, was der Kalender und die Kommandozeile liefern.
    """
    roh = text.strip().replace("T", " ")
    for muster in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            zeitpunkt = datetime.strptime(roh, muster)
        except ValueError:
            continue
        return schreiben(zeitpunkt.replace(tzinfo=ORTSZONE))
    raise ValueError(
        f"Zeitpunkt nicht verstanden: {text!r}. Erwartet wird etwas wie "
        "»2026-09-01 18:00«."
    )


def monatsgrenzen(jahr: int, monat: int) -> tuple[str, str]:
    """Anfang und Ende eines Monats in UTC – für die Kalenderansicht.

    Die Grenzen werden aus der Ortszeit gerechnet, nicht aus UTC: Der September
    beginnt für den Betrachter am 1. September um Mitternacht *hier*, das sind
    im Sommer 22 Uhr UTC am 31. August. Wer das übergeht, dem fehlt der erste
    Abend des Monats in der Ansicht.
    """
    anfang = datetime(jahr, monat, 1, tzinfo=ORTSZONE)
    if monat == 12:
        ende = datetime(jahr + 1, 1, 1, tzinfo=ORTSZONE)
    else:
        ende = datetime(jahr, monat + 1, 1, tzinfo=ORTSZONE)
    return schreiben(anfang), schreiben(ende)


def wochengrenzen(bezug: datetime) -> tuple[str, str]:
    """Montag bis Montag um den angegebenen Tag herum, in UTC."""
    ort = bezug.astimezone(ORTSZONE) if bezug.tzinfo else bezug.replace(tzinfo=ORTSZONE)
    montag = (ort - timedelta(days=ort.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return schreiben(montag), schreiben(montag + timedelta(days=7))


def lesbar(stempel: str) -> str:
    """Für Ausgaben auf der Kommandozeile: »Mo 01.09.2026, 18:00«."""
    tage = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    ort = nach_ortszeit(stempel)
    return f"{tage[ort.weekday()]} {ort.strftime('%d.%m.%Y, %H:%M')}"


def kalenderwoche(stempel: str) -> tuple[int, int]:
    """Jahr und Kalenderwoche eines Zeitstempels, nach ISO 8601.

    Nicht selbst rechnen: Die erste Woche ist die mit dem ersten Donnerstag,
    weshalb der 1. Januar mitunter in KW 52 des Vorjahres liegt. `isocalendar`
    weiß das - und gibt auch das passende Jahr dazu, das dann eben das
    Vorjahr ist.
    """
    ort = nach_ortszeit(stempel)
    jahr, woche, _ = ort.isocalendar()
    return jahr, woche
