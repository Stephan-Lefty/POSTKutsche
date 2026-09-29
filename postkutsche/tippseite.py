"""Die Seite »Tipp der Woche« fortschreiben – ausführlicher als die Grafik.

Auf der Grafik steht, was in zwölf Stichpunkte passt. Auf der Seite steht der
Tipp, wie man ihn jemandem am Telefon erklären würde: mit Vorgeschichte, einer
Handlungsanweisung zum Nachmachen und dem Hinweis, wann es nicht mehr selbst
zu machen ist. Beides entsteht im selben Lauf aus demselben Thema.

**Die Seite trägt ihre eigene Pflegeanleitung.** Im Kopf der Datei steht, was
montags zu tun ist: den aktuellen Tipp ersetzen, den bisherigen ins Archiv
schieben, Titel, Beschreibung und Datum nachziehen, höchstens fünf Wochen
stehen lassen. Dieses Modul tut genau das – die Anleitung ist die
Spezifikation, und wenn sich die Seite ändert, ändert sich die Anleitung mit.

**Geschrieben wird in eine Datei, nicht auf den Server.** Die fertige Seite
landet im Wochenordner unter »Dokumente« und wird von Hand hochgeladen, wie
die Bilder für Facebook und Instagram. Eine Datei, die man erst ansieht, ist
harmloser als eine, die sofort öffentlich ist.

Gearbeitet wird mit Textersatz an benannten Marken, nicht mit einem
HTML-Parser. Das ist hier die robustere Wahl: Ein Parser schreibt die ganze
Datei neu und formatiert dabei Stellen um, die niemand angefasst hat – bei
einer von Hand gepflegten Seite sieht man danach im Vergleich nicht mehr, was
sich wirklich geändert hat.
"""

from __future__ import annotations

import html
import re
from typing import Any

#: Die Marken, zwischen denen gearbeitet wird. Sie stehen so in der Datei.
AKTUELL_AUF = "<!-- ============ TIPP AKTUELL"
AKTUELL_ZU = "<!-- ============ ENDE TIPP AKTUELL ============ -->"
ARCHIV_AUF = "<!-- ============ TIPP ARCHIV ============ -->"
ARCHIV_ZU = "<!-- ============ ENDE TIPP ARCHIV ============ -->"

#: So viele Wochen bleiben im Archiv stehen. Steht auch so auf der Seite:
#: »lieber wenige aktuelle Hinweise als ein Archiv, in dem veraltete Normen
#: weiterleben«.
ARCHIV_WOCHEN = 5

MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")


class SeitenFehler(Exception):
    """Die Seite ließ sich nicht fortschreiben. Die Meldung ist für Menschen."""


def erneuern(seite: str, tipp: dict[str, Any], woche: int, montag) -> str:
    """Gibt die Seite mit dem neuen Tipp zurück – das Alte wandert ins Archiv.

    `tipp` braucht »titel«, »absaetze« (Liste aus Absätzen und
    Zwischenüberschriften), »kurz« für das Archiv und »beschreibung« für
    Google. `montag` ist ein `date`.
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
                      _archiv(seite, bisher))
    return _kopf_nachziehen(seite, tipp, woche, montag, datum)


def _bisheriger_tipp(seite: str) -> dict[str, str] | None:
    """Woche und Überschrift des Tipps, der gerade noch oben steht."""
    anfang = seite.find(AKTUELL_AUF)
    ende = seite.find(AKTUELL_ZU)
    if anfang < 0 or ende < 0:
        return None
    block = seite[anfang:ende]
    woche = re.search(r"Kalenderwoche\s+(\d+)", block)
    titel = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
    if not (woche and titel):
        return None
    return {"woche": woche.group(1),
            "titel": re.sub(r"\s+", " ", titel.group(1)).strip()}


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
    if not eintraege:
        return ""
    zeilen = "".join(
        f'                \t<li><a href="{html.escape(str(e["adresse"]), quote=True)}">'
        f'{html.escape(str(e.get("text") or e["adresse"]))}</a></li>\n'
        for e in eintraege if e.get("adresse"))
    if not zeilen:
        return ""
    return f"""            <div class="border-top">&nbsp;</div>
            <p class="noMargin"><small><strong>Passend dazu aus unserem Sortiment</strong></small></p>
            <ul>
{zeilen}            </ul>
"""


def _aktuell(tipp: dict[str, Any], woche: int, datum: str) -> str:
    """Der Block mit dem Tipp dieser Woche."""
    text = ("".join(_stueck(s) for s in tipp["absaetze"])
            + _verweise(tipp.get("verweise") or []))
    return f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
            <p class="noMargin"><small><strong>Kalenderwoche {woche}</strong> &middot; ab Montag, {html.escape(datum)}</small></p>
            <h2>{html.escape(tipp["titel"])}</h2>
        </div>
    </div>

    <div class="row">
    \t<div class="col-xs-12 col-sm-7 col-md-8">
{text}        </div>
    </div>

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


def _archiv(seite: str, bisher: dict[str, str] | None) -> str:
    """Die Liste der Vorwochen – der bisherige Tipp kommt nach oben."""
    alt = _archiveintraege(seite)
    neu = []
    if bisher:
        neu.append(f"""            \t<li>
                \t<strong>KW {html.escape(bisher["woche"])} &middot; {html.escape(bisher["titel"])}</strong>
                </li>
""")
    eintraege = (neu + alt)[:ARCHIV_WOCHEN]
    if not eintraege:
        eintraege = ["""            \t<li>
                \t<em>Der erste Tipp ist gerade erschienen.</em> Ab der kommenden Woche finden Sie
                    an dieser Stelle die Tipps der Vorwochen zum Nachlesen.
                </li>
"""]
    return f"""
    <div class="row">
    \t<div class="col-xs-12">
        \t<div class="border-top">&nbsp;</div>
        \t<h2>Die Tipps der Vorwochen</h2>
            <p>
            \tHier sammeln wir die letzten fünf Tipps als Kurzfassung. Ältere Themen nehmen wir
                heraus, sobald sie fachlich überholt sind - lieber wenige aktuelle Hinweise
                als ein Archiv, in dem veraltete Normen weiterleben.
            </p>
            <ul>
{"".join(eintraege)}            </ul>
        </div>
    </div>
"""


def _archiveintraege(seite: str) -> list[str]:
    """Die bisherigen Einträge – ohne das auskommentierte Muster.

    Das Muster steht als Kommentar in der Datei und sieht einem Eintrag zum
    Verwechseln ähnlich. Wer es mitnimmt, hat nach zwei Wochen einen Tipp
    doppelt: einmal echt, einmal aus der Vorlage.
    """
    anfang = seite.find(ARCHIV_AUF)
    ende = seite.find(ARCHIV_ZU)
    if anfang < 0 or ende < 0:
        return []
    block = re.sub(r"<!--.*?-->", "", seite[anfang:ende], flags=re.S)
    eintraege = re.findall(r"(\s*<li>.*?</li>\n?)", block, re.S)
    # Der Platzhalter »Der erste Tipp ist gerade erschienen« ist kein Eintrag.
    return [e for e in eintraege if "gerade erschienen" not in e]


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
        f"<title>Tipp der Woche - {html.escape(tipp['titel'])} | HaBeFa.de</title>",
        seite, count=1, flags=re.S)
    seite = re.sub(
        r'(<meta\s+name="description"\s+content=")[^"]*(")',
        lambda m: m.group(1) + html.escape(
            f"Jeden Montag ein neuer Praxistipp von HaBeFa.de. Diese Woche: {kurz}",
            quote=True) + m.group(2),
        seite, count=1)
    seite = re.sub(
        r'(<meta\s+name="date"\s+content=")[^"]*(")',
        lambda m: m.group(1) + montag.isoformat() + m.group(2), seite, count=1)
    seite = re.sub(
        r"Zuletzt aktualisiert:\s*[^<(]*\(KW\s*\d+\)",
        f"Zuletzt aktualisiert: {datum} (KW {woche})", seite, count=1)
    return seite
