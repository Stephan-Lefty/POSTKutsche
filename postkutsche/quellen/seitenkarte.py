"""Seiten ohne Schnittstelle: über ihre Seitenkarte und das, was auf der Seite steht.

Der Weg für Seiten ohne jede Schnittstelle – gern ein Eigenbau, der seit über
zehn Jahren läuft. Was in solchen Seitenkarten steht, ist mit Vorsicht zu
genießen:

**Dem `lastmod`-Datum ist nicht zu trauen.** Es gibt Seitenkarten, in denen
alle paar tausend Adressen dasselbe Datum tragen – das der letzten Umstellung,
vor über zehn Jahren. Neue Seiten lassen sich daran nicht erkennen, sondern
nur daran, dass eine Adresse vorher nicht in unserer Ablage stand.

**Nicht jede Adresse ist ein Produkt.** In derselben Karte stehen Warenkorb,
Bestellformular und Übersichtsseiten. Sie werden ausgeschlossen, sonst schlägt
das Werkzeug vor, den Warenkorb zu bewerben.

**Der erste Abgleich muss stumm sein.** Ein paar tausend Adressen auf einmal
als »neu« zu melden wäre kein Kalender mehr, sondern eine Lawine.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Iterator

from .abrufen import AbrufFehler, entmarken, holen, og_angaben, text_holen

# Namensraum der Sitemap-Norm. Ohne den findet ElementTree nichts.
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Adressen, die keine Produkte sind. Bewusst als Bruchstücke und nicht als
# Reguläre Ausdrücke – das soll jemand ohne Übung ergänzen können.
KEINE_PRODUKTE = (
    "/cart.", "/order.", "/warenkorb", "/checkout", "/login", "/konto",
    "/agb", "/impressum", "/datenschutz", "/widerruf", "/kontakt",
    "/list.html", "/suche", "/search", "/sitemap",
)


def adressen(karte: str, grenze: int = 5000) -> list[str]:
    """Alle Adressen aus einer Seitenkarte, auch aus verschachtelten.

    Eine Sitemap darf auf weitere Sitemaps verweisen. Ältere Eigenbauten tun das
    selten, Shopware und WordPress fast immer – deshalb wird beides behandelt.
    """
    gefunden: list[str] = []
    for adresse in _adressen_aus(karte, tiefe=0):
        gefunden.append(adresse)
        if len(gefunden) >= grenze:
            break
    return gefunden


def _adressen_aus(karte: str, tiefe: int) -> Iterator[str]:
    # Zwei Ebenen reichen. Wer tiefer verschachtelt, hat andere Sorgen; und
    # eine unbegrenzte Rekursion über fremde Adressen läuft irgendwann im Kreis.
    if tiefe > 2:
        return

    roh = holen(karte)
    try:
        wurzel = ET.fromstring(roh)
    except ET.ParseError as fehler:
        raise AbrufFehler(f"{karte} ist keine gültige Seitenkarte: {fehler}") from fehler

    # Ein <sitemapindex> verweist auf weitere Karten.
    for unterkarte in wurzel.findall("sm:sitemap/sm:loc", NS):
        if unterkarte.text:
            yield from _adressen_aus(unterkarte.text.strip(), tiefe + 1)

    for ort in wurzel.findall("sm:url/sm:loc", NS):
        if ort.text:
            yield ort.text.strip()


def produktadressen(karte: str, muster: str | None = None,
                    grenze: int = 5000) -> list[str]:
    """Adressen aus der Seitenkarte, die nach Produktseiten aussehen.

    `muster` ist ein regulärer Ausdruck, der zusätzlich passen muss – damit
    lässt sich je Seite nachschärfen, ohne den Quelltext zu ändern.
    """
    geprueft = re.compile(muster) if muster else None
    treffer = []
    for adresse in adressen(karte, grenze):
        klein = adresse.lower()
        if any(stueck in klein for stueck in KEINE_PRODUKTE):
            continue
        if geprueft and not geprueft.search(adresse):
            continue
        treffer.append(adresse)
    return treffer


# Ein verbreitetes Muster älterer Shops: Produktadressen enden auf
# »_<Zahl>.html«, wobei die Zahl die Artikelnummer ist, und Übersichtsseiten
# heißen »list.html«. Wo das anders ist, hilft der Parameter `muster` in
# `produktadressen`.
_PRODUKTVERWEIS = re.compile(r"""href\s*=\s*["']([^"']*_\d+\.html)["']""", re.IGNORECASE)


def kategorie(adresse: str, grenze: int = 100) -> list[str]:
    """Die Produktadressen einer Kategorieseite.

    Der Weg für Kampagnen: Statt darauf zu warten, dass ein neues Produkt
    auftaucht, gibt man die Kategorie vor und holt sich, was darin steht.

    Achtung bei Übersichtsseiten: Eine Kategorie der obersten Ebene verweist oft
    nur auf ihre Unterkategorien und enthält selbst kein einziges Produkt. Eine
    leere Liste heißt hier also nicht »Fehler«, sondern »eine Ebene tiefer
    nachsehen«.
    """
    roh = text_holen(adresse)
    stamm = _stamm_von(adresse)

    gefunden: list[str] = []
    gesehen: set[str] = set()
    for verweis in _PRODUKTVERWEIS.findall(roh):
        voll = verweis if verweis.startswith("http") else f"{stamm}{verweis}"
        if voll not in gesehen:
            gesehen.add(voll)
            gefunden.append(voll)
        if len(gefunden) >= grenze:
            break
    return gefunden


def _stamm_von(adresse: str) -> str:
    """Schema und Rechnername einer Adresse – für Verweise, die mit / beginnen."""
    treffer = re.match(r"(https?://[^/]+)", adresse)
    return treffer.group(1) if treffer else ""


def seite(adresse: str) -> dict[str, object]:
    """Liest eine einzelne Seite aus.

    Die og:-Angaben sind der beste verfügbare Halt: Sie stehen genau dafür da,
    dass ein soziales Netzwerk eine Vorschau bauen kann, und sind deshalb
    meistens gepflegter als der Rest der Seite. Fehlen sie, wird der Titel aus
    `<title>` genommen.
    """
    roh = text_holen(adresse)
    angaben = og_angaben(roh)

    titel = angaben.get("title") or _titel_aus(roh) or adresse
    beschreibung = angaben.get("description") or _beschreibung_aus(roh) or ""
    bild = angaben.get("image") or _produktbild(roh, adresse)

    return {
        "fremd_id": adresse,
        "titel": entmarken(titel),
        "text": entmarken(beschreibung),
        "adresse": angaben.get("url") or adresse,
        "bild_adresse": bild,
        "veroeffentlicht": None,  # Solche Seiten haben kein Datum, dem zu trauen wäre
        "kategorien": [],
    }


_TITEL = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_BESCHREIBUNG = re.compile(
    r"""<meta[^>]+name\s*=\s*["']description["'][^>]*content\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)


# Bilder, die auf jeder Seite stehen und nichts über das Produkt sagen.
ZIERRAT = ("/elements/", "logo", "banner", "icon", "sprite", "pixel",
           "trustedshops", "paypal", "facebook", "instagram", "/flags/",
           "spacer", "blank", "arrow", "button")


def _produktbild(roh: str, adresse: str) -> str | None:
    """Sucht das Produktfoto im Seitenquelltext.

    Der Weg für Seiten ohne og:image. Zwei Regeln, beide aus dem Blick auf
    eine echte Seite: Logos, Zahlungssymbole und Sternebewertungen sind keine
    Produktfotos - sie stehen auf jeder Seite und tragen »elements« oder
    »logo« im Pfad. Und bei mehreren Größen desselben Bildes ist die größere
    die richtige; ein 80-Pixel-Vorschaubild taugt für keinen Beitrag.
    """
    stamm = _stamm_von(adresse)
    gefunden: list[str] = []

    for treffer in re.findall(r"""<img[^>]+src\s*=\s*["\']([^"\']+)["\']""",
                              roh, re.IGNORECASE):
        quelle = treffer.strip()
        if any(stueck in quelle.lower() for stueck in ZIERRAT):
            continue
        if not quelle.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        voll = quelle if quelle.startswith("http") else f"{stamm}{quelle}"
        gefunden.append(voll)

    if not gefunden:
        return None

    # Nach Größenordner sortieren, falls es einen gibt: /pictures/item/2/ ist
    # größer als /pictures/item/1/.
    def rang(quelle: str) -> int:
        treffer = re.search(r"/(\d+)/[^/]+$", quelle)
        return -int(treffer.group(1)) if treffer else 0

    gefunden.sort(key=rang)
    return gefunden[0]


def _titel_aus(roh: str) -> str | None:
    treffer = _TITEL.search(roh)
    return treffer.group(1).strip() if treffer else None


def _beschreibung_aus(roh: str) -> str | None:
    treffer = _BESCHREIBUNG.search(roh)
    return treffer.group(1).strip() if treffer else None
