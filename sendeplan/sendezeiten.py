"""Wann ein Beitrag rausgehen sollte.

**Das hier sind Startwerte, keine Wahrheit.** Die Zahlen stammen aus den
Auswertungen von Sprout Social, Buffer, Brandwatch und Metricool (Stand
Anfang 2026). Solche Auswertungen mitteln über Millionen Konten quer durch alle
Branchen – für die eigene Leserschaft können sie deutlich danebenliegen.

Für das Handwerk liegen sie sogar planmäßig daneben. Die Studien empfehlen
zehn bis zwölf Uhr; ein Dachdecker ist um zehn auf dem Dach. Der schaut um
halb sieben aufs Handy, bevor der Wagen losfährt, und wieder gegen halb fünf,
wenn er ihn ausräumt. Deshalb steht für die Zielgruppe `handwerk` etwas anderes
hier als in den Ratgebern.

Was hier steht, ist ein Vorschlag, den man im Kalender überschreiben kann. Ab
Etappe »Resonanz« werden die eigenen Zahlen mitgeschrieben, und dann gilt, was
tatsächlich gelesen wurde – nicht, was ein Blog behauptet.

**Zur Altersfrage.** Die entscheidet sich an der Plattform, nicht an der
Uhrzeit: Facebook liegt im Schwerpunkt zwischen 35 und 65, Instagram zwischen
18 und 34, LinkedIn bei den Berufstätigen zwischen 25 und 54. Wer Türen und
Brandschutz verkauft, erreicht seine Käufer auf Facebook und LinkedIn; auf
Instagram sieht das Bild schön aus und kauft niemand.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import zeiten
from .netzwerke import FACEBOOK, INSTAGRAM, LINKEDIN, MASTODON

# Zielgruppen. Ein Projekt bekommt genau eine zugewiesen; steht keine dabei,
# gilt `gemischt`.
HANDWERK = "handwerk"        # Handwerk, Fachhandel, Bauherren – die Altbauseite und die Shops
VERBRAUCHER = "verbraucher"  # Freizeit, Natur, Reise – Zweitblog
BETROFFENE = "betroffene"    # Angehörige und Betroffene – Mein Blog
GEMISCHT = "gemischt"

MO, DI, MI, DO, FR, SA, SO = range(7)
WERKTAGS = (MO, DI, MI, DO, FR)
KERNTAGE = (DI, MI, DO)       # die drei, die in fast jeder Auswertung vorn liegen
WOCHENENDE = (SA, SO)


@dataclass(frozen=True)
class Fenster:
    """Ein Zeitfenster, in dem gepostet werden sollte."""

    tage: tuple[int, ...]
    stunde: int
    minute: int
    rang: int      # 1 ist das beste Fenster, höhere Zahlen sind Ausweichtermine
    grund: str

    def beschriftung(self) -> str:
        namen = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
        tage = "/".join(namen[t] for t in self.tage)
        return f"{tage} {self.stunde:02d}:{self.minute:02d}"


# Aufgeschlüsselt nach Netzwerk und Zielgruppe. Fehlt eine Kombination, greift
# der Eintrag unter GEMISCHT.
FENSTER: dict[tuple[str, str], list[Fenster]] = {
    # -- Facebook ---------------------------------------------------------
    # Die älteste Nutzerschaft der vier, Schwerpunkt 35 bis 65. Für Türen,
    # Brandschutz und Sicherungstechnik das wichtigste Netz.
    (FACEBOOK, HANDWERK): [
        Fenster(WERKTAGS, 6, 30, 1,
                "Vor Arbeitsbeginn. Handwerker schauen aufs Handy, bevor der "
                "Wagen losfährt – da ist der Wettbewerb um Aufmerksamkeit gering."),
        Fenster(WERKTAGS, 12, 0, 2, "Mittagspause, in jeder Auswertung stabil."),
        Fenster(WERKTAGS, 16, 30, 2,
                "Feierabend auf dem Bau. Früher als im Büro, deshalb nicht 18 Uhr."),
        Fenster((SA,), 9, 0, 3,
                "Samstagvormittag – der Bauherr plant, der Handwerker hat frei."),
    ],
    (FACEBOOK, VERBRAUCHER): [
        Fenster(KERNTAGE, 19, 0, 1, "Abends auf dem Sofa, die verlässlichste Zeit."),
        Fenster((SA, SO), 10, 0, 1, "Wochenende vormittags, in Ruhe gelesen."),
        Fenster(WERKTAGS, 12, 30, 2,
                "Mittagspause. Schwächer als der Abend, aber verlässlich."),
    ],
    (FACEBOOK, BETROFFENE): [
        Fenster((SO,), 10, 30, 1,
                "Sonntagvormittag. Angehörige haben Zeit und Muße – für ein "
                "Thema, das man nicht nebenbei liest, der beste Moment."),
        Fenster(KERNTAGE, 19, 30, 1, "Abends, wenn der Tag geschafft ist."),
        Fenster((SA,), 10, 30, 2, "Samstagvormittag als Ausweichtermin."),
    ],
    (FACEBOOK, GEMISCHT): [
        Fenster(KERNTAGE, 12, 0, 1, "Mittagsfenster, plattformweit am stabilsten."),
        Fenster(KERNTAGE, 19, 0, 2,
                "Abends auf dem Sofa – die zweite verlässliche Zeit des Tages."),
    ],

    # -- LinkedIn ---------------------------------------------------------
    # Berufstätige zwischen 25 und 54. Wochenende ist hier tote Zeit.
    (LINKEDIN, HANDWERK): [
        Fenster(KERNTAGE, 7, 30, 1,
                "Vor dem ersten Termin. Im Bauhandwerk beginnt der Tag früher "
                "als die Ratgeber annehmen."),
        Fenster(KERNTAGE, 11, 0, 2, "Klassisches Vormittagsfenster."),
        Fenster(KERNTAGE, 16, 0, 3, "Später Nachmittag, zieht laut 2026er Zahlen an."),
    ],
    (LINKEDIN, BETROFFENE): [
        Fenster(KERNTAGE, 9, 0, 1,
                "Vormittags. Wer beruflich mit Barrierefreiheit zu tun hat – "
                "Pflege, Verwaltung, Sozialverbände –, liest das im Dienst."),
        Fenster(KERNTAGE, 16, 0, 2,
                "Später Nachmittag, bevor der Feierabend die Aufmerksamkeit abzieht."),
    ],
    (LINKEDIN, GEMISCHT): [
        Fenster(KERNTAGE, 10, 30, 1, "Dienstag bis Donnerstag vormittags."),
        Fenster(KERNTAGE, 15, 30, 2, "Nachmittagsfenster."),
    ],

    # -- Instagram --------------------------------------------------------
    # 18 bis 34 im Schwerpunkt. Für die Shops eher Schaufenster als Verkaufsweg.
    (INSTAGRAM, VERBRAUCHER): [
        Fenster(KERNTAGE, 19, 0, 1, "Abends, das stärkste Fenster."),
        Fenster(WERKTAGS, 12, 0, 2, "Mittagspause, die kleine Auszeit."),
        Fenster((SA, SO), 11, 0, 2, "Wochenende vormittags."),
    ],
    (INSTAGRAM, GEMISCHT): [
        Fenster(KERNTAGE, 12, 0, 1, "Mittags zwischen 11 und 14 Uhr."),
        Fenster(KERNTAGE, 19, 0, 1, "Abends zwischen 18 und 21 Uhr."),
    ],

    # -- Mastodon ---------------------------------------------------------
    # Technikaffines Publikum, keine Sortierung nach Beliebtheit: Was jetzt
    # gepostet wird, sieht man jetzt – und später kaum noch. Deshalb zählt
    # hier die Uhrzeit mehr als anderswo.
    (MASTODON, GEMISCHT): [
        Fenster(WERKTAGS, 9, 0, 1,
                "Vormittags. Die Zeitleiste läuft streng chronologisch, ein "
                "Beitrag um Mitternacht ist am Morgen vergessen."),
        Fenster(WERKTAGS, 17, 0, 2,
                "Früher Abend, wenn die Zeitleiste sich nach Feierabend füllt."),
    ],
    (MASTODON, BETROFFENE): [
        Fenster(WERKTAGS, 9, 0, 1,
                "Vormittags. Die Barrierefreiheits-Gemeinde ist auf Mastodon "
                "auffallend gut vertreten und liest tagsüber."),
        Fenster(WERKTAGS, 17, 0, 2,
                "Früher Abend, wenn die Zeitleiste sich nach Feierabend füllt."),
    ],
}


def fenster_fuer(netzwerk: str, zielgruppe: str = GEMISCHT) -> list[Fenster]:
    """Die Zeitfenster für eine Kombination, bestes zuerst."""
    gefunden = FENSTER.get((netzwerk, zielgruppe)) or FENSTER.get((netzwerk, GEMISCHT))
    if not gefunden:
        # Sollte nicht vorkommen, aber ein Kalender ohne Vorschlag ist besser
        # als ein Absturz.
        return [Fenster(KERNTAGE, 12, 0, 1, "Allgemeines Mittagsfenster.")]
    return sorted(gefunden, key=lambda f: f.rang)


def vorschlagen(
    netzwerk: str,
    zielgruppe: str = GEMISCHT,
    ab: datetime | None = None,
    anzahl: int = 3,
) -> list[tuple[str, str]]:
    """Die nächsten passenden Termine ab einem Zeitpunkt.

    Gibt Paare aus UTC-Zeitstempel und Begründung zurück – die Begründung
    steht im Kalender neben dem Vorschlag, damit erkennbar bleibt, warum
    ausgerechnet Dienstag halb acht.

    Der erste Vorschlag liegt immer mindestens eine Stunde in der Zukunft. Ein
    Termin, der schon vorbei ist, während man ihn noch freigibt, hilft niemandem.
    """
    beginn = (ab or datetime.now(zeiten.ORTSZONE)).astimezone(zeiten.ORTSZONE)
    frühestens = beginn + timedelta(hours=1)

    treffer: list[tuple[datetime, Fenster]] = []
    for versatz in range(14):  # zwei Wochen reichen für drei Vorschläge
        tag = (beginn + timedelta(days=versatz)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for fenster in fenster_fuer(netzwerk, zielgruppe):
            if tag.weekday() not in fenster.tage:
                continue
            zeitpunkt = tag.replace(hour=fenster.stunde, minute=fenster.minute)
            if zeitpunkt >= frühestens:
                treffer.append((zeitpunkt, fenster))

    # Nach Zeitpunkt sortieren, bei gleichem Zeitpunkt das bessere Fenster zuerst.
    treffer.sort(key=lambda paar: (paar[0], paar[1].rang))
    return [
        (zeiten.schreiben(zeitpunkt), fenster.grund)
        for zeitpunkt, fenster in treffer[:anzahl]
    ]


def zielgruppe_von(projekt) -> str:  # type: ignore[no-untyped-def]
    """Liest die Zielgruppe aus den Einstellungen eines Projekts."""
    return projekt.einstellungen.get("zielgruppe", GEMISCHT)
