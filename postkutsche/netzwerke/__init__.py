"""Die Netzwerke und was sie voneinander unterscheidet.

Hier steht das Verzeichnis, nicht der Versand – der liegt je Netzwerk in einer
eigenen Datei daneben. Farben, Kürzel und Grenzen an einer Stelle zu halten
lohnt sich, weil sie an drei Orten gebraucht werden: im Kalender, in den
Anweisungen an Claude und beim Zuschneiden der Bilder.

**Zu den Farben.** Es sind die Markenfarben, mit einer Ausnahme: LinkedIn steht
hier im dunklen Petrolblau statt im gewohnten #0A66C2. Facebook und LinkedIn
sind beide blau, und an einem drei Pixel schmalen Rahmen ist ein Blau vom
anderen nicht zu unterscheiden. Deshalb außerdem: Jedes Kärtchen trägt sein
Kürzel. Farbe allein trägt keine Bedeutung – wer rot-grün-blind ist oder auf
einem schlecht eingestellten Bildschirm sitzt, muss es trotzdem lesen können.
"""

from __future__ import annotations

from dataclasses import dataclass

MASTODON = "mastodon"
LINKEDIN = "linkedin"
FACEBOOK = "facebook"
INSTAGRAM = "instagram"


@dataclass(frozen=True)
class Netzwerk:
    kennung: str
    name: str
    kuerzel: str      # zwei Zeichen, steht im Kärtchen neben der Farbe
    farbe: str        # Rahmen des Kärtchens im Kalender
    zeichen_max: int  # harte Grenze des Netzwerks
    zeichen_ziel: int  # was Claude anpeilen soll – deutlich darunter
    schlagworte_max: int
    bild_format: str  # Seitenverhältnis, auf das zugeschnitten wird
    bild_pflicht: bool
    hinweis: str


VERZEICHNIS: dict[str, Netzwerk] = {
    MASTODON: Netzwerk(
        kennung=MASTODON,
        name="Mastodon",
        kuerzel="MA",
        farbe="#563ACC",
        # 500 ist die Voreinstellung; einzelne Instanzen erlauben mehr. Wir
        # rechnen mit 500, dann passt es überall.
        zeichen_max=500,
        zeichen_ziel=420,
        # Drei statt vier: Der erste Durchlauf am 2026-08-28 lieferte prompt
        # die erlaubte Höchstzahl. Auf Mastodon gelten vier schon als
        # reichlich - was erlaubt ist, wird ausgeschöpft, also erlaubt man
        # weniger.
        schlagworte_max=3,
        bild_format="4:5",
        bild_pflicht=False,
        hinweis="Kurz und sachlich. Der Verweis darf im Text stehen, aber "
                "danach kommt kein Satz mehr - sonst hängt er hinter dem Link "
                "in der Luft. Schlagwörter sehr sparsam, ein bis zwei reichen; "
                "zu viele gelten dort als Lärm.",
    ),
    LINKEDIN: Netzwerk(
        kennung=LINKEDIN,
        name="LinkedIn",
        kuerzel="LI",
        # Nicht das Marken-Blau #0A66C2, sondern das dunklere aus derselben
        # Palette – sonst ist der Rahmen von Facebook nicht zu unterscheiden.
        farbe="#0a66c2",
        zeichen_max=3000,
        # Nach etwa 200 Zeichen klappt LinkedIn den Text zu. Was danach kommt,
        # liest nur, wer auf »mehr anzeigen« tippt. Der Kern muss also vorn stehen.
        zeichen_ziel=900,
        schlagworte_max=5,
        bild_format="4:5",
        bild_pflicht=False,
        hinweis="Erster Satz muss allein tragen – danach wird abgeschnitten. "
                "Fachlicher Ton, keine Werbesprache, kein Ausrufezeichen-Regen.",
    ),
    FACEBOOK: Netzwerk(
        kennung=FACEBOOK,
        name="Facebook",
        kuerzel="FB",
        farbe="#1877F2",
        # Facebook erlaubt über 60.000 Zeichen. Das ist keine Empfehlung.
        zeichen_max=5000,
        zeichen_ziel=600,
        schlagworte_max=3,
        bild_format="4:5",
        bild_pflicht=False,
        hinweis="Ansprechend, aber nicht anbiedernd. Verweis ans Ende, "
                "davor muss der Text auch ohne ihn Sinn ergeben.",
    ),
    INSTAGRAM: Netzwerk(
        kennung=INSTAGRAM,
        name="Instagram",
        kuerzel="IG",
        farbe="#E1306C",
        zeichen_max=2200,
        zeichen_ziel=700,
        schlagworte_max=12,
        bild_format="4:5",
        # Ohne Bild geht bei Instagram nichts, weder über die Schnittstelle
        # noch von Hand.
        bild_pflicht=True,
        hinweis="Verweise sind im Text nicht anklickbar – deshalb nie »hier "
                "klicken«, sondern auf das Profil verweisen. Erste Zeile ist "
                "die Überschrift, Schlagwörter kommen ans Ende.",
    ),
}

#: Reihenfolge für Anzeige und Ausgaben. Erst die, die von selbst senden,
#: dann die beiden, die vorerst von Hand bedient werden.
REIHENFOLGE = [MASTODON, LINKEDIN, FACEBOOK, INSTAGRAM]


def netzwerk(kennung: str) -> Netzwerk:
    try:
        return VERZEICHNIS[kennung]
    except KeyError:
        bekannt = ", ".join(REIHENFOLGE)
        raise ValueError(f"Unbekanntes Netzwerk {kennung!r}. Bekannt: {bekannt}") from None


def alle() -> list[Netzwerk]:
    return [VERZEICHNIS[k] for k in REIHENFOLGE]
