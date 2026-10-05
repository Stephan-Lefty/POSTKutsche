"""Die Seite »Tipp der Woche« fortschreiben – ausführlicher als die Grafik.

Auf der Grafik steht, was in zwölf Stichpunkte passt. Auf der Seite steht der
Tipp, wie man ihn jemandem am Telefon erklären würde: mit Vorgeschichte, einer
Handlungsanweisung zum Nachmachen und dem Hinweis, wann es nicht mehr selbst
zu machen ist. Beides entsteht im selben Lauf aus demselben Thema.

**Die Seite trägt ihre eigene Pflegeanleitung.** Im Kopf der Datei steht, was
montags zu tun ist: den ablaufenden Tipp ins Archiv retten, den aktuellen
ersetzen, die Übersicht ergänzen, Titel, Beschreibung und Datum nachziehen.
Dieses Modul tut genau das – die Anleitung ist die Spezifikation, und wenn
sich die Seite ändert, ändert sich die Anleitung mit.

**Das Archiv hat seit dem 2026-10-05 zwei Ebenen.** Unten auf der Tipp-Seite
steht der Schnellzugriff: zweispaltig, höchstens vier Wochen, je mit
Vorschaubild und zwei Sätzen. Darunter führt ein Verweis auf `/tipp-archiv/`,
wo *alle* Tipps chronologisch stehen. Jeder Tipp bekommt dort eine eigene
Seite mit eigenem Titel und eigenem Canonical.

Vorher waren die Archiveinträge Kacheln, die die Grafik der Woche in einem
neuen Reiter öffneten – ohne Unterseiten, »die niemand mehr durchsieht«. Das
war sparsamer zu pflegen und für Google wertlos: Ein Tipp, der nach fünf
Wochen spurlos verschwindet, kann nicht gefunden werden. Die Unterseiten
entstehen jetzt automatisch, damit bleibt der Einwand erledigt.

**Geschrieben wird in Dateien, nicht auf den Server.** Die fertige Seite, die
neue Archivseite und die fortgeschriebene Übersicht landen im Wochenordner
unter »Dokumente« und werden von Hand hochgeladen, wie die Bilder für
Facebook und Instagram. Eine Datei, die man erst ansieht, ist harmloser als
eine, die sofort öffentlich ist.

Gearbeitet wird mit Textersatz an benannten Marken, nicht mit einem
HTML-Parser. Das ist hier die robustere Wahl: Ein Parser schreibt die ganze
Datei neu und formatiert dabei Stellen um, die niemand angefasst hat – bei
einer von Hand gepflegten Seite sieht man danach im Vergleich nicht mehr, was
sich wirklich geändert hat.
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

#: Die Marken, zwischen denen gearbeitet wird. Sie stehen so in der Datei.
AKTUELL_AUF = "<!-- ============ TIPP AKTUELL"
AKTUELL_ZU = "<!-- ============ ENDE TIPP AKTUELL ============ -->"
ARCHIV_AUF = "<!-- ============ TIPP ARCHIV ============ -->"
ARCHIV_ZU = "<!-- ============ ENDE TIPP ARCHIV ============ -->"

#: In der Übersichtsseite `/tipp-archiv/index.html`.
LISTE_AUF = "<!-- ============ ARCHIVLISTE  (montags oben erweitern) ============ -->"
LISTE_ZU = "<!-- ============ ENDE ARCHIVLISTE ============ -->"

#: So viele Wochen stehen unten auf der Tipp-Seite. Steht auch so auf der
#: Seite: »höchstens die letzten vier«. Mehr sind es nur in der Übersicht –
#: dort wird nichts entfernt.
ARCHIV_WOCHEN = 4

#: Wo die Archivseiten liegen, relativ zur Tipp-Seite. Lässt sich über
#: `marken.json` unter »tipparchiv« überschreiben.
ARCHIV_ORDNER = "tipp-archiv"

MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")


class SeitenFehler(Exception):
    """Die Seite ließ sich nicht fortschreiben. Die Meldung ist für Menschen."""


def erneuern(seite: str, tipp: dict[str, Any], woche: int, montag,
             archiv: str = "/tipp-archiv/") -> str:
    """Gibt die Seite mit dem neuen Tipp zurück – das Alte wandert ins Archiv.

    `tipp` braucht »titel«, »absaetze« (Liste aus Absätzen und
    Zwischenüberschriften), »kurz« für das Archiv und »beschreibung« für
    Google. `montag` ist ein `date`. `archiv` ist die Adresse der
    Übersichtsseite; darunter liegen auch die einzelnen Archivseiten.

    Die Archivseite des ablaufenden Tipps entsteht hier nicht – dafür gibt
    es `archivseite()`. Dieses Modul schreibt Text, es schreibt keine
    Dateien; wohin etwas gehört, weiß der Aufrufer.
    """
    for marke in (AKTUELL_AUF, AKTUELL_ZU, ARCHIV_AUF, ARCHIV_ZU):
        if marke not in seite:
            raise SeitenFehler(
                f"In der Seite fehlt die Marke »{marke[:40]}…«. Ohne sie ist "
                "nicht zu erkennen, welcher Teil ersetzt werden soll.")

    bisher = _bisheriger_tipp(seite)
    # Wird innerhalb derselben Woche nachgebessert, wird ersetzt und nicht
    # archiviert. Sonst stünde dieselbe Kalenderwoche zweimal auf der Seite –
    # einmal oben als der aktuelle Tipp, einmal darunter als Vorwoche.
    if bisher and str(bisher["woche"]) == str(woche):
        bisher = None
    datum = f"{montag.day}. {MONATE[montag.month - 1]} {montag.year}"

    seite = _ersetzen(seite, AKTUELL_AUF, AKTUELL_ZU,
                      _aktuell(tipp, woche, datum))
    seite = _ersetzen(seite, ARCHIV_AUF, ARCHIV_ZU,
                      _archiv(seite, bisher, archiv))
    return _kopf_nachziehen(seite, tipp, woche, montag, datum)


def abgelaufener_tipp(seite: str) -> dict[str, str] | None:
    """Was beim nächsten Lauf ins Archiv wandert – oder nichts.

    Gibt dasselbe zurück, was `erneuern` intern für den Archiveintrag
    verwendet: Woche, Titel, Kurzfassung, Bild und Datum. Damit kann der
    Aufrufer die Archivseite bauen, bevor er die Seite überschreibt.
    """
    return _bisheriger_tipp(seite)


def woche_auf_der_seite(seite: str) -> int | None:
    """Welche Kalenderwoche oben auf der Seite steht – oder nichts.

    Damit lässt sich die Wirklichkeit prüfen statt eines Kalenders: Steht
    dort eine ältere Woche, ist entweder kein Tipp geschrieben oder die
    Datei nicht hochgeladen worden. Beides sieht von außen gleich aus, und
    beides muss derselbe Hinweis abdecken.
    """
    gefunden = _bisheriger_tipp(seite)
    try:
        return int(gefunden["woche"]) if gefunden else None
    except (TypeError, ValueError):
        return None


def _bisheriger_tipp(seite: str) -> dict[str, str] | None:
    """Alles über den Tipp, der gerade noch oben steht.

    Woche, Titel, Datum und Bild stehen im Block selbst. Die Kurzfassung
    steht im Kopf der Seite: `_kopf_nachziehen` hat sie dort als
    `meta description` hinterlassen. Sie dort wieder abzuholen ist der
    einzige Weg, ohne sie ein zweites Mal pflegen zu müssen – wenn der
    Tipp abläuft, sind die Daten, aus denen er entstand, längst weg.
    """
    anfang = seite.find(AKTUELL_AUF)
    ende = seite.find(AKTUELL_ZU)
    if anfang < 0 or ende < 0:
        return None
    block = seite[anfang:ende]
    woche = re.search(r"Kalenderwoche\s+(\d+)", block)
    titel = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
    if not (woche and titel):
        return None
    gefunden = {"woche": woche.group(1),
                "titel": html.unescape(
                    re.sub(r"<[^>]+>", "",
                           re.sub(r"\s+", " ", titel.group(1))).strip())}

    # Das Datum steht im Block, nicht im Kalender des Aufrufers: Wird am
    # Jahreswechsel archiviert, gehört die Jahreszahl zum alten Tipp.
    datum = re.search(r"ab Montag,\s*(\d{1,2})\.\s*([^\s<]+)\s*(\d{4})", block)
    if datum:
        gefunden["datum"] = f"{datum.group(1)}. {datum.group(2)} {datum.group(3)}"
        gefunden["jahr"] = datum.group(3)

    kurz = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', seite)
    if kurz:
        text = html.unescape(kurz.group(1))
        # »Jede Woche ein neuer Praxistipp. Diese Woche: …« – gebraucht wird
        # nur der zweite Teil. Er stand dort hinter einem Doppelpunkt und
        # beginnt deshalb manchmal klein; im Archiv steht er allein und
        # fängt einen Absatz an.
        text = text.split("Diese Woche:", 1)[-1].strip()
        gefunden["kurz"] = text[:1].upper() + text[1:] if text else ""

    # Die Grafik der Woche wandert mit: Sie ist die Kurzfassung in Bildform.
    bild = re.search(r'<img src="([^"]+)"[^>]*?alt="([^"]*)"', block, re.S)
    if bild:
        gefunden["vorschau"] = bild.group(1)
        gefunden["alt"] = bild.group(2)
        # Der Verweis zeigt auf die volle Fassung, das img auf die kleine.
        gross = re.search(r'<a href="([^"]+)" target="_blank"', block)
        gefunden["bild"] = gross.group(1) if gross else bild.group(1)
    return gefunden


def archivname(eintrag: dict[str, str]) -> str:
    """Der Dateiname der Archivseite: `2026-KW40-aussentueren-im-herbst.html`.

    Jahr und Woche vorn, damit die Dateien im Ordner von selbst in der
    richtigen Reihenfolge stehen. Der Titel folgt gekürzt – eine Adresse,
    die über eine Zeile läuft, teilt niemand.
    """
    jahr = eintrag.get("jahr") or ""
    woche = str(eintrag.get("woche", "")).zfill(2)
    return f"{jahr}-KW{woche}-{_kennwort(eintrag.get('titel', ''))}.html"


#: Wörter, die am Rand einer Adresse nichts beitragen. In der Mitte bleiben
#: sie stehen - »aussentueren-im-herbst« liest sich besser als
#: »aussentueren-herbst«.
_FUELLWOERTER = {"der", "die", "das", "ein", "eine", "einen", "einem", "und",
                 "was", "wie", "wann", "warum", "so", "es", "man"}


def _kennwort(titel: str, woerter: int = 5) -> str:
    """Aus einer Überschrift ein Stück Adresse machen.

    Die Überschriften sind zweiteilig gebaut: »Außentüren im Herbst: die
    halbe Stunde, die den Winter rettet«. Vor dem Doppelpunkt steht das
    Thema, dahinter der Haken – für die Adresse zählt das Thema. Wer
    stattdessen die ersten Wörter nimmt, bekommt »aussentueren-im-herbst-die«.

    Umlaute werden ausgeschrieben statt weggeworfen: »aussentueren« findet
    man wieder, »auentren« nicht.
    """
    thema = titel.split(":", 1)[0] if ":" in titel else titel
    ersatz = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
              "Ä": "ae", "Ö": "oe", "Ü": "ue"}
    text = "".join(ersatz.get(z, z) for z in thema).lower()
    # Was danach noch an Zeichen mit Haken übrig ist (é, à), wird zerlegt
    # und der Haken verworfen - er gehört nicht in eine Adresse.
    text = "".join(z for z in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(z))
    teile = [t for t in re.split(r"[^a-z0-9]+", text) if t][:woerter]
    while teile and teile[-1] in _FUELLWOERTER:
        teile.pop()
    return "-".join(teile) or "tipp"


def _ersetzen(seite: str, auf: str, zu: str, neu: str) -> str:
    anfang = seite.index(auf)
    # Die öffnende Marke bleibt stehen: Sie trägt bei »TIPP AKTUELL« den
    # Hinweis »(jeden Montag ersetzen)«, und der soll nicht verschwinden.
    zeilenende = seite.index("-->", anfang) + 3
    ende = seite.index(zu)
    return seite[:zeilenende] + neu + seite[ende:]


def _verweise(eintraege: list[dict[str, str]]) -> str:
    """Passende Artikel am Ende des Tipps – als Kasten, nicht im Fließtext.

    Ein Ratgeber, in dem mitten im Satz ein Shoplink steht, liest sich wie
    eine Anzeige mit Ratgeberanstrich. Unten ein abgesetzter Hinweis
    »passend dazu« bleibt ein Angebot und drängt sich nicht auf.

    Die Verweise gibt der Betreiber vor; sie werden nicht vom Modell erfunden.
    Ein erfundener Artikellink führt ins Leere und ist schlimmer als keiner.
    """
    brauchbar = [e for e in eintraege if e.get("adresse")]
    if not brauchbar:
        return ""
    zeilen = ""
    for e in brauchbar:
        ziel = html.escape(str(e["adresse"]), quote=True)
        name = html.escape(str(e.get("text") or e["adresse"]))
        # Mit Bild wird daraus ein Kästchen, ohne Bild eine Zeile. Ein
        # Artikel, den man sieht, wird eher angeklickt als einer, der als
        # blauer Text unter einem Fachtext steht.
        if e.get("bild"):
            zeilen += f"""            <div class="row">
            \t<div class="col-xs-4 col-sm-3">
                \t<a href="{ziel}"><img src="{html.escape(str(e["bild"]), quote=True)}"
                         class="img-responsive"
                         alt="{html.escape(str(e.get("alt") or e.get("text") or ""), quote=True)}" /></a>
                </div>
                <div class="col-xs-8 col-sm-9">
                \t<p><a href="{ziel}"><strong>{name}</strong></a><br />
                    {html.escape(str(e.get("warum") or ""))}</p>
                </div>
            </div>
"""
        else:
            zeilen += f'            <p><a href="{ziel}">{name}</a></p>\n'
    return f"""            <div class="border-top">&nbsp;</div>
            <p class="noMargin"><small><strong>Passend dazu aus unserem Sortiment</strong></small></p>
{zeilen}"""


def _merksatz(text: str) -> str:
    """Ein abgesetzter Kasten mitten im Text.

    Neun Absätze am Stück liest niemand zu Ende. Ein hervorgehobener Satz
    unterbricht die Fläche und ist zugleich das, was hängenbleibt, wenn
    jemand nur überfliegt – deshalb gehört dort die Kernaussage hinein und
    keine Zusammenfassung.
    """
    if not text.strip():
        return ""
    return (f'            <blockquote>\n            \t<p>'
            f'{_mit_auszeichnung(text)}</p>\n            </blockquote>\n')


def _bild(bild: dict[str, str]) -> str:
    """Ein Bild im Textfluss, über die ganze Breite und anklickbar.

    Keine schmale Spalte daneben: Der Text nutzt die Breite des ersten
    Absatzes, und das Bild tut es auch. Ein Klick öffnet es in einem neuen
    Reiter in voller Größe – auf einer Seite über Beschläge und Dichtungen
    will man Einzelheiten sehen, und die Fassung im Fließtext ist dafür zu
    klein.

    `rel="noopener"` gehört zu jedem `target="_blank"`: Ohne das kann die
    geöffnete Seite über `window.opener` auf die aufrufende zugreifen.

    `alt` ist Pflicht. Fehlt es, bleibt das Attribut leer statt zu raten –
    eine falsche Beschreibung ist schlimmer als keine.

    `center-block` muss neben `img-responsive` stehen. Letzteres setzt
    `display:block`, und auf einem Blockelement wirkt das `text-center` des
    Absatzes nicht mehr – am 2026-10-05 an der fertigen Seite gemessen: 15 px
    Rand links, 515 px rechts.
    """
    if not bild.get("adresse"):
        return ""
    ziel = html.escape(str(bild["adresse"]), quote=True)
    # Gezeigt wird die schmale Fassung, verlinkt die volle. Ohne Vorschau
    # steht beides auf derselben Datei - dann ist der Klick eben umsonst.
    zeigen = html.escape(str(bild.get("vorschau") or bild["adresse"]), quote=True)
    stueck = f"""            <p class="text-center">
            \t<a href="{ziel}" target="_blank" rel="noopener">
                \t<img src="{zeigen}"
                         class="img-responsive center-block"
                         alt="{html.escape(str(bild.get("alt") or ""), quote=True)}" />
                </a>
            </p>
"""
    if bild.get("unterschrift"):
        stueck += (f'            <p class="text-center"><small>'
                   f'{html.escape(str(bild["unterschrift"]))} '
                   f'<em>(zum Vergrößern anklicken)</em></small></p>\n')
    return stueck


def _aktuell(tipp: dict[str, Any], woche: int, datum: str) -> str:
    """Der Block mit dem Tipp dieser Woche."""
    stuecke = [_stueck(s) for s in tipp["absaetze"]]
    # Das Bild kommt hinter den ersten Absatz: früh genug, um gesehen zu
    # werden, aber erst, nachdem der Einstieg gesagt hat, worum es geht.
    for bild in reversed(tipp.get("bilder") or []):
        stuecke.insert(1, _bild(bild))
    text = "".join(stuecke) + _verweise(tipp.get("verweise") or [])
    bilder = ""
    # Alles über die volle Breite - so breit wie der erste Absatz.
    breite = "col-xs-12"
    return f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
            <p class="noMargin"><small><strong>Kalenderwoche {woche}</strong> &middot; ab Montag, {html.escape(datum)}</small></p>
            <h2>{html.escape(tipp["titel"])}</h2>
        </div>
    </div>

    <div class="row">
    \t<div class="{breite}">
{text}        </div>
{bilder}    </div>

"""


def _stueck(teil: Any) -> str:
    """Ein Absatz oder eine Zwischenüberschrift.

    Ein Eintrag ist entweder Text (dann ein Absatz) oder ein Paar
    `{"ueber": "…"}` für eine Zwischenüberschrift. Mehr Formen gibt es nicht –
    was sich nicht als Absatz oder Überschrift schreiben lässt, gehört nicht
    auf diese Seite.
    """
    if isinstance(teil, dict) and teil.get("ueber"):
        return f'            <h3>{html.escape(teil["ueber"])}</h3>\n'
    if isinstance(teil, dict) and teil.get("merksatz"):
        return _merksatz(str(teil["merksatz"]))
    return (f'            <p>\n            \t'
            f'{_mit_auszeichnung(str(teil))}\n            </p>\n')


_ERLAUBT = re.compile(r"&lt;(/?)(strong|em)&gt;")


def _mit_auszeichnung(text: str) -> str:
    """Text entschärfen, aber <strong> und <em> durchlassen.

    Die Seite lebt davon, dass der entscheidende Halbsatz hervorgehoben ist.
    Alles andere wird entschärft: Was aus einem Modell kommt, darf keine
    Auszeichnung mitbringen, die niemand vorgesehen hat.
    """
    return _ERLAUBT.sub(r"<\1\2>", html.escape(text))


def _archiv(seite: str, bisher: dict[str, str] | None, archiv: str) -> str:
    """Der Schnellzugriff unten auf der Seite – der bisherige Tipp nach oben.

    Zwei Spalten, höchstens vier Wochen. Wer herausfällt, verschwindet nicht:
    Seine Seite bleibt liegen und steht weiter in der Übersicht, auf die der
    Verweis am Ende führt.
    """
    alt = _archiveintraege(seite)
    neu = []
    if bisher:
        neu.append(_teaser(bisher, archiv))
    eintraege = (neu + alt)[:ARCHIV_WOCHEN]
    if not eintraege:
        inhalt = """    <div class="row">
        <div class="col-xs-12">
        \t<p><em>Der erste Tipp ist gerade erschienen.</em> Ab der kommenden Woche finden Sie
                an dieser Stelle die Tipps der Vorwochen zum Nachlesen.</p>
        </div>
    </div>
"""
    else:
        # Zwei Blöcke je Zeile. Jede Zeile ist eine eigene `row`: Bootstrap
        # 3 bricht ungleich hohe Spalten sonst treppenförmig um, weil die
        # erste Spalte der zweiten Reihe an der höchsten der ersten hängt.
        inhalt = ""
        for i in range(0, len(eintraege), 2):
            inhalt += ('    <div class="row">\n\n'
                       + "\n".join(eintraege[i:i + 2])
                       + "\n    </div>\n")
    ziel = html.escape(str(archiv), quote=True)
    return f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
        \t<h2>Die Tipps der Vorwochen</h2>
            <p>
            \tHier stehen die Tipps der Vorwochen zum Anklicken, höchstens die letzten vier.
                Ältere Themen bleiben im Archiv - dort finden Sie alles, was bisher erschienen ist.
            </p>
        </div>
    </div>

{inhalt}
    <div class="row">
    \t<div class="col-xs-12">
        \t<p><strong><a href="{ziel}">Alle Tipps im Archiv ansehen &raquo;</a></strong>
                &nbsp;&middot;&nbsp; chronologisch nach Kalenderwochen, nichts verschwindet.</p>
        </div>
    </div>
"""


def _teaser(eintrag: dict[str, str], archiv: str, halb: bool = True) -> str:
    """Ein Eintrag: Vorschaubild links, Woche, Thema und zwei Sätze rechts.

    Das Bild sitzt neben dem Text und nicht darüber. Die Grafiken sind
    querformatig; über die volle Spaltenbreite gelegt nehmen sie halbe
    Seitenbreite ein und erschlagen den Tipp, zu dem sie gehören.

    Verlinkt wird die Archivseite, nicht mehr die Grafik. Auf der Grafik
    stehen zwölf Stichpunkte, auf der Seite der ganze Tipp – und sie lässt
    sich finden, verlinken und vorlesen.
    """
    woche = html.escape(str(eintrag.get("woche", "")))
    titel = html.escape(str(eintrag.get("titel", "")))
    datum = html.escape(str(eintrag.get("datum", "")))
    kurz = html.escape(str(eintrag.get("kurz", "")))
    ziel = html.escape(_archivadresse(archiv, eintrag), quote=True)
    wann = f" &middot; {datum}" if datum else ""
    vorschau = eintrag.get("vorschau") or eintrag.get("bild")
    if vorschau:
        bild = f"""            	<div class="col-xs-5">
                	<a href="{ziel}"><img src="{html.escape(str(vorschau), quote=True)}"
                         class="img-responsive"
                         alt="{html.escape(str(eintrag.get("alt") or titel), quote=True)}" /></a>
                </div>
                <div class="col-xs-7">
"""
        zu = "                </div>\n"
    else:
        # Ohne Bild nimmt der Text die ganze Spalte - ein leerer Platzhalter
        # sieht nach einem kaputten Bild aus.
        bild = '            	<div class="col-xs-12">\n'
        zu = "                </div>\n"
    return f"""    	<div class="col-xs-12 col-sm-6">
        	<div class="row">
{bild}                	<p class="noMargin"><small><strong>Kalenderwoche {woche}</strong>{wann}</small></p>
                    <p><a href="{ziel}"><strong>{titel}</strong></a><br />
                    {kurz}
                    <a href="{ziel}">Weiterlesen &raquo;</a></p>
{zu}            </div>
            <div class="clearfix">&nbsp;</div>
        </div>"""


def _archivadresse(archiv: str, eintrag: dict[str, str]) -> str:
    """Die Adresse der Archivseite zu einem Eintrag."""
    return archiv.rstrip("/") + "/" + archivname(eintrag)


def _titelanhang(seite: str) -> str:
    """Was im `<title>` hinter dem letzten Strich steht, etwa » | Laden.de«.

    Der Name des Auftritts gehört nicht ins Programm – er steht schon auf
    der Seite. Wer ihn hier einträgt, hat ihn an zwei Stellen zu pflegen
    und setzt ihn beim nächsten Kunden falsch.
    """
    vorhanden = re.search(r"<title>(.*?)</title>", seite, re.S)
    if not vorhanden or "|" not in vorhanden.group(1):
        return ""
    return " |" + vorhanden.group(1).rsplit("|", 1)[1].rstrip()


def _archiveintraege(seite: str) -> list[str]:
    """Die bisherigen Einträge – ohne die Umschläge und ohne Kommentare.

    Gesucht sind die halben Spalten mit einer Wochenangabe darin. Der
    einleitende Absatz und der Verweis aufs Archiv stehen in `col-xs-12`
    und tragen keine.
    """
    anfang = seite.find(ARCHIV_AUF)
    ende = seite.find(ARCHIV_ZU)
    if anfang < 0 or ende < 0:
        return []
    block = re.sub(r"<!--.*?-->", "", seite[anfang:ende], flags=re.S)
    eintraege = re.findall(
        r'(    \t<div class="col-xs-12 col-sm-6">.*?\n        </div>)',
        block, re.S)
    return [e for e in eintraege if "Kalenderwoche" in e]


def archivseite(seite: str, eintrag: dict[str, str], archiv: str,
                tippadresse: str = "/Tipp-der-Woche.html") -> str:
    """Aus dem ablaufenden Tipp eine Seite machen, die bleibt.

    Gebaut wird aus der Tipp-Seite selbst, solange der alte Tipp noch oben
    steht – damit erbt die Archivseite Kopf, Navigation, Fuß und den
    Cookie-Hinweis, ohne dass eine zweite Vorlage gepflegt werden muss.
    Zwei Vorlagen driften auseinander, sobald an einer etwas geändert wird.

    Geändert werden fünf Dinge: Titel und Beschreibung, das Canonical auf
    die eigene Adresse, die Überschrift, die Einleitung (aus »jede Woche
    neu« wird »dieser Beitrag stammt aus KW …«) und das Archiv unten, das
    zu Rückverweisen wird.
    """
    for marke in (AKTUELL_AUF, AKTUELL_ZU, ARCHIV_AUF, ARCHIV_ZU):
        if marke not in seite:
            raise SeitenFehler(
                f"In der Seite fehlt die Marke »{marke[:40]}…«. Ohne sie "
                "lässt sich keine Archivseite daraus schneiden.")
    titel = str(eintrag.get("titel", ""))
    if not titel:
        raise SeitenFehler("Dem abgelaufenen Tipp fehlt die Überschrift.")
    woche = str(eintrag.get("woche", ""))
    datum = str(eintrag.get("datum", ""))
    eigene = _archivadresse(archiv, eintrag)

    # Die Montagsanleitung gehört auf die lebende Seite, nicht ins Archiv.
    seite = re.sub(r"<!--\s*=+\s*\n\s*TIPP DER WOCHE.*?=+\s*-->\s*", "",
                   seite, flags=re.S)

    seite = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(titel)}{_titelanhang(seite)}</title>",
        seite, count=1, flags=re.S)
    kurz = str(eintrag.get("kurz", ""))
    if kurz:
        seite = re.sub(
            r'(<meta\s+name="description"\s+content=")[^"]*(")',
            lambda m: m.group(1) + html.escape(kurz, quote=True) + m.group(2),
            seite, count=1)
    seite = re.sub(r'(<link\s+rel="canonical"\s+href=")[^"]*(")',
                   lambda m: m.group(1) + html.escape(eigene, quote=True) + m.group(2),
                   seite, count=1)

    # Überschrift und Einleitung: von der H1 bis zum Tippblock steht auf der
    # lebenden Seite die Werbung fürs Lesezeichen. Im Archiv gehört dorthin,
    # woher der Beitrag stammt und wo der aktuelle steht.
    kopf = re.search(r"<h1[^>]*>.*?</h1>", seite, re.S)
    anfang = seite.find(AKTUELL_AUF)
    if not kopf or anfang < 0 or kopf.end() > anfang:
        raise SeitenFehler(
            "Zwischen Überschrift und Tippblock ist die Seite nicht so "
            "aufgebaut, wie die Archivseite es erwartet.")
    schluss = seite.index("</div>", kopf.end()) + len("</div>")
    wann = f", erschienen am {html.escape(datum)}" if datum else ""
    hinweis = f"""

    <div class="row">
    \t<div class="col-xs-12">
        \t<p>
            \t<small>Dieser Beitrag ist der <strong>Tipp der Woche aus Kalenderwoche {html.escape(woche)}</strong>{wann}.
                Den aktuellen Tipp finden Sie auf
                <a href="{html.escape(tippadresse, quote=True)}">Tipp der Woche</a>,
                alle bisherigen im <a href="{html.escape(archiv, quote=True)}">Tipp-Archiv</a>.</small>
            </p>
        </div>
    </div>

    <div class="clearfix">&nbsp;</div>

"""
    seite = (seite[:kopf.start()]
             + f"<h1>{html.escape(titel)}</h1>"
             + seite[kopf.end():schluss] + hinweis + seite[anfang:])

    # Im Tippblock steht die Überschrift jetzt doppelt - oben als H1.
    anfang = seite.find(AKTUELL_AUF)
    ende = seite.find(AKTUELL_ZU)
    block = seite[anfang:ende]
    block = re.sub(r"[ \t]*<h2[^>]*>.*?</h2>\n?", "", block, count=1, flags=re.S)
    block = block.replace("&middot; ab Montag,", "&middot;", 1)
    seite = seite[:anfang] + block + seite[ende:]

    return _ersetzen(seite, ARCHIV_AUF, ARCHIV_ZU, f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
            <p>
            \t<strong><a href="{html.escape(tippadresse, quote=True)}">&laquo; Zum aktuellen Tipp der Woche</a></strong>
                &nbsp;&middot;&nbsp;
                <a href="{html.escape(archiv, quote=True)}">Alle Tipps im Archiv</a>
                &nbsp;&middot;&nbsp; Jeden Montag ein neues Thema aus der Praxis.
            </p>
        </div>
    </div>
""")


def uebersicht_erneuern(uebersicht: str, eintrag: dict[str, str],
                        archiv: str) -> str:
    """Den neuen Tipp oben in `/tipp-archiv/index.html` eintragen.

    Hier wird nichts entfernt – das ist der Zweck der Seite. Ein neues Jahr
    bekommt eine eigene Überschrift; so bleibt die Liste lesbar, wenn sie
    über fünfzig Einträge lang ist.
    """
    for marke in (LISTE_AUF, LISTE_ZU):
        if marke not in uebersicht:
            raise SeitenFehler(
                f"In der Übersicht fehlt die Marke »{marke[:40]}…«.")
    anfang = uebersicht.index(LISTE_AUF) + len(LISTE_AUF)
    ende = uebersicht.index(LISTE_ZU)
    liste = uebersicht[anfang:ende]

    if _archivadresse(archiv, eintrag) in liste:
        # Zweiter Lauf in derselben Woche: Der Eintrag steht schon da.
        return uebersicht

    jahr = str(eintrag.get("jahr", ""))
    kopf = f"<h2>{html.escape(jahr)}</h2>"
    neu = _uebersichtzeile(eintrag, archiv)
    if jahr and kopf in liste:
        # Unter die vorhandene Jahreszahl, vor den bisher obersten Eintrag.
        stelle = liste.index(kopf)
        stelle = liste.index("</div>\n    </div>\n", stelle) + len("</div>\n    </div>\n")
        liste = liste[:stelle] + neu + liste[stelle:]
    else:
        liste = f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
            {kopf}
        </div>
    </div>
{neu}""" + liste
    return uebersicht[:anfang] + liste + uebersicht[ende:]


def _uebersichtzeile(eintrag: dict[str, str], archiv: str) -> str:
    """Ein Eintrag in der Übersicht – wie der Teaser, nur über die volle Breite."""
    woche = html.escape(str(eintrag.get("woche", "")))
    titel = html.escape(str(eintrag.get("titel", "")))
    datum = html.escape(str(eintrag.get("datum", "")))
    kurz = html.escape(str(eintrag.get("kurz", "")))
    ziel = html.escape(_archivadresse(archiv, eintrag), quote=True)
    wann = f" &middot; {datum}" if datum else ""
    vorschau = eintrag.get("vorschau") or eintrag.get("bild")
    if vorschau:
        bild = f"""    	<div class="col-xs-4 col-sm-3">
        	<a href="{ziel}"><img src="{html.escape(str(vorschau), quote=True)}"
                 class="img-responsive"
                 alt="{html.escape(str(eintrag.get("alt") or titel), quote=True)}" /></a>
        </div>
        <div class="col-xs-8 col-sm-9">
"""
    else:
        bild = '    	<div class="col-xs-12">\n'
    return f"""
    <div class="row">
{bild}        	<p class="noMargin"><small><strong>Kalenderwoche {woche}</strong>{wann}</small></p>
            <p><a href="{ziel}"><strong>{titel}</strong></a><br />
            {kurz}
            <a href="{ziel}">Weiterlesen &raquo;</a></p>
        </div>
    </div>
    <div class="clearfix">&nbsp;</div>
"""


def _kopf_nachziehen(seite: str, tipp: dict[str, Any], woche: int,
                     montag, datum: str) -> str:
    """Titel, Beschreibung und die beiden Datumsangaben.

    Die Anleitung in der Datei nennt das ausdrücklich: »Beides ist für Google
    wichtig und darf nicht stehen bleiben.« Genau das vergisst man beim
    Bearbeiten von Hand zuerst.
    """
    kurz = tipp.get("beschreibung") or tipp["kurz"]
    seite = re.sub(
        r"<title>.*?</title>",
        f"<title>Tipp der Woche - {html.escape(tipp['titel'])}"
        f"{_titelanhang(seite)}</title>",
        seite, count=1, flags=re.S)
    seite = re.sub(
        r'(<meta\s+name="description"\s+content=")[^"]*(")',
        lambda m: m.group(1) + html.escape(
            f"Jede Woche ein neuer Praxistipp. Diese Woche: {kurz}",
            quote=True) + m.group(2),
        seite, count=1)
    seite = re.sub(
        r'(<meta\s+name="date"\s+content=")[^"]*(")',
        lambda m: m.group(1) + montag.isoformat() + m.group(2), seite, count=1)
    seite = re.sub(
        r"Zuletzt aktualisiert:\s*[^<(]*\(KW\s*\d+\)",
        f"Zuletzt aktualisiert: {datum} (KW {woche})", seite, count=1)
    return seite
