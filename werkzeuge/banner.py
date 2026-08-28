"""Erzeugt den Banner fürs README – hell und dunkel, in drei Breiten.

Aufruf aus dem Wurzelverzeichnis des Repositorys:

    python werkzeuge/banner.py

Braucht `rsvg-convert` (Paket librsvg) für die PNG. Ohne das Programm werden
nur die SVG geschrieben.

**Warum ein Skript und nicht von Hand gezeichnet:** Der Banner besteht aus
sechs Dateien – zwei Themen mal drei Breiten. Von Hand gepflegt weichen die
irgendwann voneinander ab, und man merkt es erst, wenn im dunklen Thema noch
der alte Untertitel steht.

**Warum `<text>` statt Buchstabenpfaden:** MailBurg hat seine Wortmarke in
Pfade gewandelt, damit sie ohne die passende Schrift richtig aussieht. Das ist
sauberer, kostet aber ein Werkzeug, das hier fehlt. Der Ausweg: Was ins README
eingebunden wird, sind die **PNG**. Die entstehen einmal auf einem Rechner mit
DejaVu Sans, und danach ist die Schrift des Betrachters gleichgültig. Das SVG
ist die Quelle zum Nacharbeiten, nicht das Auslieferungsformat.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ASSETS = WURZEL / "assets"

sys.path.insert(0, str(WURZEL))
from postkutsche import farben  # noqa: E402

BREITE, HOEHE = 1200, 420
BREITEN = (800, 1600, 2800)

# Die Wortmarke in zwei Teilen: »POST« in der ruhigen Farbe, »Kutsche« im Blau
# der Marke. Die Schreibweise mit großem POST ist Vorgabe und folgt
# NEXTBookmarks und NEXTStatus.
WORT_EINS = "POST"
WORT_ZWEI = "Kutsche"
# Eine Redewendung für Schwung - und hier zugleich wörtlich wahr.
UNTERTITEL = "AB GEHT DIE POST."

# DejaVu Sans ist auf Arch und Debian vorhanden. Die weiteren Namen sind
# Ausweichwege für Rechner, auf denen sie fehlt.
SCHRIFT = "DejaVu Sans, Liberation Sans, Noto Sans, sans-serif"

# Schriftgrößen und die zugehörigen Textbreiten. Die Breiten sind *gemessen*,
# nicht geschätzt:
#
#     magick -font DejaVu-Sans-Bold -pointsize 96 label:"POSTKutsche" \
#            -format "%w" info:
#
# Der erste Anlauf hatte 128 Punkt und schätzte die Breite - die Wortmarke lief
# 963 Pixel breit und damit rechts aus dem Bild. Wer diese Werte ändert, misst
# vorher nach; Buchstabenbreiten lassen sich nicht aus der Punktgröße ableiten.
WORT_GROESSE = 96
WORT_BREITE = 723          # »POSTKutsche« bei 96 Punkt
UNTER_GROESSE = 30
UNTER_SPERRUNG = 4.2
UNTER_BREITE = 360         # 289 gemessen, plus 17 Zeichen mal Sperrung

ICON_X, ICON_Y, ICON_KANTE = 70, 60, 300
WORT_X = 410
WORT_GRUNDLINIE = 228
UNTER_GRUNDLINIE = 292


def _icon_eingebettet() -> str:
    """Das Icon als Datenadresse, damit das SVG für sich allein steht.

    Ein Verweis auf die Nachbardatei ginge auch, aber dann ist das SVG nur im
    Repository vollständig - verschickt oder in eine Vorschau gezogen wäre es
    ein leerer Kasten.
    """
    daten = (ASSETS / "icon-512.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(daten).decode("ascii")


def svg(dunkel: bool) -> str:
    wort_ruhig = farben.GRAU_HELL if dunkel else farben.BLAU_NACHT
    unterton = farben.GRAU_MITTE if dunkel else farben.GRAU
    linie = farben.GRAU_DUNKEL if dunkel else farben.GRAU_HELL

    mitte = WORT_X + WORT_BREITE / 2
    # Die Linien rücken an den Untertitel heran statt bündig unter der
    # Wortmarke zu stehen: Der Untertitel ist mit 350 Pixeln deutlich kürzer
    # als die 723 der Wortmarke, und bündige Linien ließen links und rechts
    # je 160 Pixel Leere zwischen Linie und Text.
    linie_laenge = 70
    linie_links = mitte - UNTER_BREITE / 2 - 26 - linie_laenge
    linie_rechts = mitte + UNTER_BREITE / 2 + 26
    linie_y = UNTER_GRUNDLINIE - 10

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BREITE} {HOEHE}"
     width="{BREITE}" height="{HOEHE}" role="img"
     aria-label="{WORT_EINS}{WORT_ZWEI} – Ab geht die Post.">
  <title>{WORT_EINS}{WORT_ZWEI}</title>

  <!-- Kein Hintergrund: Der Banner soll sich in helle wie dunkle READMEs
       einfügen. Eine weiße Fläche säße im dunklen Thema als Kasten darin. -->

  <image href="{_icon_eingebettet()}" x="{ICON_X}" y="{ICON_Y}"
         width="{ICON_KANTE}" height="{ICON_KANTE}"/>

  <!-- Wortmarke: »POST« im ruhigen Ton, »Kutsche« im Blau der Marke - wie bei
       MailBurg, wo »Mail« dunkel und »Burg« blau steht. -->
  <text x="{WORT_X}" y="{WORT_GRUNDLINIE}" font-family="{SCHRIFT}"
        font-weight="bold" font-size="{WORT_GROESSE}"
        fill="{wort_ruhig}">{WORT_EINS}<tspan
        fill="{farben.BLAU}">{WORT_ZWEI}</tspan></text>

  <!-- Untertitel, gesperrt und zwischen zwei Zierlinien. Die Linien enden
       bündig mit der Wortmarke darüber; laufen sie darüber hinaus, zieht der
       Blick an den Rand statt in die Mitte. -->
  <rect x="{linie_links}" y="{linie_y}" width="{linie_laenge}" height="2" fill="{linie}"/>
  <rect x="{linie_rechts}" y="{linie_y}" width="{linie_laenge}" height="2" fill="{linie}"/>
  <text x="{mitte}" y="{UNTER_GRUNDLINIE}" text-anchor="middle"
        font-family="{SCHRIFT}" font-size="{UNTER_GROESSE}"
        letter-spacing="{UNTER_SPERRUNG}" fill="{unterton}">{UNTERTITEL}</text>
</svg>
"""


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    rsvg = shutil.which("rsvg-convert")

    for dunkel in (False, True):
        stamm = "banner-dark" if dunkel else "banner"
        quelle = ASSETS / f"{stamm}.svg"
        quelle.write_text(svg(dunkel), encoding="utf-8")
        print(f"geschrieben: {quelle.relative_to(WURZEL)}")

        if not rsvg:
            continue
        for breite in BREITEN:
            ziel = ASSETS / f"{stamm}-{breite}.png"
            subprocess.run(
                [rsvg, "-w", str(breite), str(quelle), "-o", str(ziel)],
                check=True,
            )
            print(f"geschrieben: {ziel.relative_to(WURZEL)}")

    if not rsvg:
        print("\nrsvg-convert fehlt – nur die SVG wurden geschrieben.")
        print("Unter Arch: pacman -S librsvg, unter Debian: apt install librsvg2-bin")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
