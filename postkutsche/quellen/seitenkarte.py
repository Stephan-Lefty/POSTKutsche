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

from .abrufen import (AbrufFehler, entmarken, holen, og_angaben, text_holen,
                      text_und_ziel)


class ProduktFortgezogen(AbrufFehler):
    """Die Adresse führt nicht mehr auf ein Produkt, sondern woandershin."""

    def __init__(self, adresse: str, gelandet: str) -> None:
        super().__init__(
            f"{adresse} führt nicht mehr auf ein Produkt, sondern auf "
            f"{gelandet}. Die Seitenkarte ist an dieser Stelle veraltet."
        )
        self.adresse = adresse
        self.gelandet = gelandet

# Namensraum der Sitemap-Norm. Ohne den findet ElementTree nichts.
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Adressen, die keine Produkte sind. Bewusst als Bruchstücke und nicht als
# Reguläre Ausdrücke – das soll jemand ohne Übung ergänzen können.
KEINE_PRODUKTE = (
    "/cart.", "/order.", "/warenkorb", "/checkout", "/login", "/konto",
    "/agb", "/impressum", "/datenschutz", "/widerruf", "/kontakt",
    "/list.html", "/suche", "/search", "/sitemap",
    # Shopware führt diese unter englischen Pfaden - ohne sie stehen
    # »Profil bearbeiten« und »Adressen« als Produkte in der Kategorie.
    "/account", "/rechtliches", "/newsletter", "/merkzettel", "/wishlist",
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
_ARTIKELNUMMER_HTML = re.compile(r"_\d+\.html$", re.IGNORECASE)

# Nur die Verweise, auf die man klicken kann. Jedes `href` zu nehmen wäre
# bequemer, führt aber bei der Shopware-Regel in die Irre: `<link
# href="/theme/1a2b/css/all.css">` hat zwei Pfadebenen und endet nicht auf
# einem Schrägstrich, sieht also aus wie ein Produkt. Am Eigenbau nachgesehen
# (2026-08-31): Dort steht kein einziger Produktverweis außerhalb eines `<a>`.
_VERWEIS = re.compile(r"""<a[^>]+href\s*=\s*["']([^"'#?]+)["']""", re.IGNORECASE)


def kategorie(adresse: str, grenze: int = 100) -> list[str]:
    """Die Produktadressen einer Kategorieseite.

    Der Weg für Kampagnen: Statt darauf zu warten, dass ein neues Produkt
    auftaucht, gibt man die Kategorie vor und holt sich, was darin steht.

    **Warum es zwei Erkennungsregeln braucht.** Woran ein Produktverweis zu
    erkennen ist, sagt das HTML nicht – Klassennamen wechseln mit jedem
    Theme. Es sagt die Adressform, und die ist je Shopform eine andere:

    *Eigenbau:* Produkte enden auf »_<Artikelnummer>.html«, Übersichten auf
    »list.html«. Nur das darf gelten. Auf derselben Seite stehen
    »/info_service/versandkosten.html« und zwei Dutzend weitere Verweise, die
    jede lockerere Regel mitnähme.

    *Shopware:* Produkte enden nicht auf einem Schrägstrich. Kategorien tun
    das (»/Fenstersicherung/«), Produkte tragen hinten die Artikelnummer
    (»/ADE-Sicherungsstange-S/ADE-S«) und liegen mindestens zwei Pfadebenen
    tief. Ein Muster wie beim Eigenbau gibt es dort nicht – die Artikelnummer
    ist keine Zahl, sondern ein Kürzel.

    Welche Regel gilt, entscheidet die Adresse der Kategorieseite selbst:
    Endet sie auf ».html«, ist es ein Eigenbau. Das ist bewusst kein »nimm die
    andere Regel, wenn die erste nichts findet« – bei der Übersichtsseite
    eines Eigenbaus, die zu Recht kein Produkt enthält, stünden danach
    Versandkosten und Impressum in der Kampagne.

    Achtung bei Übersichtsseiten: Eine Kategorie der obersten Ebene verweist oft
    nur auf ihre Unterkategorien und enthält selbst kein einziges Produkt. Eine
    leere Liste heißt hier also nicht »Fehler«, sondern »eine Ebene tiefer
    nachsehen«.

    Was der Shop mehrfach verlinkt – Bild und Titel derselben Kachel – steht
    hier nur einmal, in der Reihenfolge der Seite.
    """
    roh = text_holen(adresse)
    stamm = _stamm_von(adresse)
    eigenbau = adresse.split("?", 1)[0].lower().endswith(".html")

    gefunden: list[str] = []
    gesehen: set[str] = set()
    for verweis in _VERWEIS.findall(roh):
        voll = verweis if verweis.startswith("http") else f"{stamm}{verweis}"
        if _ist_keine_produktseite(voll) or _ist_beiwerk(voll):
            continue
        passt = (bool(_ARTIKELNUMMER_HTML.search(voll)) if eigenbau
                 else _wie_ein_shopware_produkt(voll, stamm))
        if not passt or voll in gesehen:
            continue
        gesehen.add(voll)
        gefunden.append(voll)
        if len(gefunden) >= grenze:
            break
    return gefunden


def _wie_ein_shopware_produkt(adresse: str, stamm: str) -> bool:
    """Zwei Ebenen, kein Schrägstrich am Ende, eigener Rechnername.

    Der Rechnername muss geprüft werden, weil auf einer Shopware-Seite auch
    Hersteller und Zahlungsanbieter verlinkt sind; ohne die Prüfung stünde
    deren Startseite als Produkt in der Kampagne.
    """
    if not adresse.startswith(stamm) or adresse.endswith("/"):
        return False
    # Zwei Ebenen: /Produktname/Artikelnummer. Weniger ist eine Übersicht,
    # mehr gibt es in diesen Shops nicht.
    return len(adresse[len(stamm):].strip("/").split("/")) >= 2


#: Der Name aus der Zeit, als es zwei getrennte Wege gab. Bleibt als
#: Zweitname stehen, damit vorhandene Aufrufe nicht brechen.
produkte_der_kategorie = kategorie


def _stamm_von(adresse: str) -> str:
    """Schema und Rechnername einer Adresse – für Verweise, die mit / beginnen."""
    treffer = re.match(r"(https?://[^/]+)", adresse)
    return treffer.group(1) if treffer else ""


_KATEGORIE = re.compile(r"https?://[^/]+/(.+?)/?list\.html$", re.IGNORECASE)
_PRODUKT = re.compile(r"_\d+\.html$", re.IGNORECASE)


def kategorien(karte: str, bereich: str | None = None,
               grenze: int = 5000) -> list[dict[str, object]]:
    """Die Kategorieseiten aus der Seitenkarte, als flache Liste mit Tiefe.

    Ein Shop hat seine Ordnung im Adresspfad: /shop-tueren/brandschutztueren/
    t30-1_brandschutztueren_stahl_489/list.html sagt, was worunter liegt. Die
    Seitenkarte kennt keine Verschachtelung, aber die Pfade tun es - und das
    reicht, um dieselbe Gliederung anzubieten, die man im Shop sieht.

    `bereich` schränkt auf einen Zweig ein, etwa »shop-tueren«.

    Jede Kategorie bekommt die Zahl der Produkte mit, die in ihr oder in ihren
    Unterkategorien liegen. Abgezählt wird aus der Seitenkarte, nicht durch
    Abrufen der Seiten - für hundert Kategorien wären das hundert Anfragen
    für eine Auskunft, die schon dasteht. Kategorien ohne Produkte sind
    Übersichtsseiten; sie zur Auswahl anzubieten führt zu leeren Kampagnen.

    Die Nummer am Ende jedes Namens ist die Kategorienummer des Shops. Sie
    wird für die Anzeige abgeschnitten, bleibt aber in der Adresse - man
    braucht sie zum Abrufen.
    """
    alle = adressen(karte, grenze)

    # Wie viele Produkte in welcher Kategorie liegen - abgezählt aus der
    # Seitenkarte selbst. Jede Kategorieseite einzeln abzurufen wären hier
    # 101 Anfragen für eine Information, die schon dasteht: Eine Produkt-
    # adresse liegt im Pfad ihrer Kategorie.
    zaehlung: dict[str, int] = {}
    for adresse in alle:
        if adresse.endswith("list.html") or not _PRODUKT.search(adresse):
            continue
        ordner = adresse.rsplit("/", 1)[0]
        # Auch den übergeordneten Kategorien zurechnen: Wer »Brandschutztüren«
        # wählt, bekommt, was in T30-1 und T30-2 liegt.
        while "/" in ordner:
            zaehlung[ordner] = zaehlung.get(ordner, 0) + 1
            ordner = ordner.rsplit("/", 1)[0]

    gefunden: list[dict[str, object]] = []
    gesehen: set[str] = set()

    for adresse in alle:
        treffer = _KATEGORIE.match(adresse)
        if not treffer:
            continue
        pfad = treffer.group(1)
        if bereich and not pfad.startswith(bereich):
            continue
        if adresse in gesehen:
            continue
        gesehen.add(adresse)

        teile = [t for t in pfad.split("/") if t]
        letzter = teile[-1] if teile else ""
        # Der Ordner der Kategorieseite, ohne »/list.html«.
        ordner = adresse.rsplit("/", 1)[0]
        gefunden.append({
            "adresse": adresse,
            "pfad": pfad,
            "tiefe": max(len(teile) - (1 if bereich else 0), 0),
            "name": _lesbar(letzter),
            "nummer": _nummer(letzter),
            "produkte": zaehlung.get(ordner, 0),
        })

    gefunden.sort(key=lambda e: str(e["pfad"]))
    return gefunden


#: Wörter, die im Deutschen klein bleiben, auch wenn sie in einer Adresse
#: zwischen zwei Hauptwörtern stehen. »Düsen und Adapter«, nicht »Düsen Und
#: Adapter«. Die Liste ist kurz und wird länger, wenn etwas auffällt.
KLEINSCHREIBUNG = ("und", "oder", "fuer", "mit", "aus", "von", "im", "am", "zum")


def _lesbar(stueck: str) -> str:
    """»t30-1_brandschutztueren_stahl_489« zu »T30-1 Brandschutztüren Stahl«."""
    ohne_nummer = re.sub(r"_\d+$", "", stueck)
    if not ohne_nummer:
        return "Übersicht"
    # Der Eigenbau trennt mit Unterstrich, Shopware mit Bindestrich. Wo kein
    # Unterstrich vorkommt, ist der Bindestrich die Worttrennung – sonst
    # bliebe »Duesen-und-Adapter« ein einziges Wort und käme als
    # »Duesen-und-adapter« heraus.
    if "_" not in ohne_nummer:
        ohne_nummer = ohne_nummer.replace("-", "_")
    worte = ohne_nummer.split("_")
    lesbar = " ".join(w.lower() if w.lower() in KLEINSCHREIBUNG
                      else (w.capitalize() if not re.match(r"^[a-z]\d", w) else w.upper())
                      for w in worte if w)
    # Umlaute, die in Adressen umschrieben sind, zurückholen. Nicht vollständig
    # möglich - »tueren« wird zu »Türen«, »neue« bliebe »neue«. Deshalb nur
    # die Fälle, die in Shopadressen tatsächlich häufig sind.
    # Die Liste ist absichtlich lang und stumpf statt clever: »ue« pauschal zu
    # »ü« zu machen ginge bei »neue« und »Steuerung« schief. Was hier fehlt,
    # trägt man nach, wenn es auffällt.
    for falsch, richtig in (("Tueren", "Türen"), ("tueren", "türen"),
                            ("Tuer", "Tür"), ("tuer", "tür"),
                            ("Zubehoer", "Zubehör"), ("zubehoer", "zubehör"),
                            ("Moertel", "Mörtel"), ("moertel", "mörtel"),
                            ("Duesen", "Düsen"), ("duesen", "düsen"),
                            ("Duese", "Düse"), ("duese", "düse"),
                            ("fuer", "für"),
                            ("Schloesser", "Schlösser"), ("schloesser", "schlösser"),
                            ("Tuergriffe", "Türgriffe"), ("Schluessel", "Schlüssel"),
                            ("Buerst", "Bürst"), ("Boegen", "Bögen"),
                            ("Oeffner", "Öffner"), ("oeffner", "öffner"),
                            ("Gefaelzt", "Gefälzt"), ("Waende", "Wände"),
                            ("Aussen", "Außen"), ("aussen", "außen"),
                            ("Fluegelig", "flügelig"), ("fluegelig", "flügelig"),
                            ("Fluegel", "Flügel"), ("fluegel", "flügel"),
                            ("Groesse", "Größe"), ("Hoehe", "Höhe"),
                            ("Staerke", "Stärke"), ("Waermeschutz", "Wärmeschutz")):
        lesbar = lesbar.replace(falsch, richtig)
    return lesbar


def _nummer(stueck: str) -> int | None:
    treffer = re.search(r"_(\d+)$", stueck)
    return int(treffer.group(1)) if treffer else None


def vorgegebene_kategorien(vorgaben: list[object],
                           grenze: int = 200) -> list[dict[str, object]]:
    """Kategorien, die von Hand vorgegeben wurden, mit ihrer Produktzahl.

    Der Weg für Shops, deren Seitenkarte die Zugehörigkeit nicht verrät.
    Shopware legt Produkte flach ab, nicht unterhalb der Kategorie – wer in
    der Seitenkarte nach dem Kategoriepfad filtert, findet dort nur die
    Kategorieseite selbst und hält den Shop für leer. Also nennt man die
    Handvoll Kategorien, die einen interessieren, in der Projektdatei.

    **Hier wird abgerufen, in `kategorien` nicht.** Dort stünde die Zahl schon
    in der Seitenkarte, hundert Abrufe für eine vorhandene Auskunft wären
    Unfug. Hier steht sie nirgends – sie kostet einen Abruf je Kategorie, und
    das sind vier statt hundert.

    Eine Vorgabe ist entweder die Adresse allein oder ein Objekt mit
    `adresse` und `name`. Der Name lohnt sich, wo die Adresse ihn schlecht
    hergibt: »Duesen-und-Adapter« liest sich als »Düsen und Adapter« besser.

    Eine Kategorieseite, die gerade nicht antwortet, wird mit null Produkten
    und ihrem Fehler zurückgegeben und nicht ausgelassen. Sonst verschwindet
    sie stillschweigend aus der Auswahl, und niemand weiß, warum die Woche
    nur halb voll wurde.
    """
    gefunden: list[dict[str, object]] = []
    for vorgabe in vorgaben:
        if isinstance(vorgabe, str):
            adresse, name = vorgabe, None
        else:
            angaben = dict(vorgabe)  # type: ignore[arg-type]
            adresse = str(angaben.get("adresse", ""))
            name = angaben.get("name")
        if not adresse:
            continue

        pfad = adresse[len(_stamm_von(adresse)):].strip("/")
        fehler: str | None = None
        try:
            anzahl = len(kategorie(adresse, grenze))
        except AbrufFehler as schiefgegangen:
            anzahl, fehler = 0, str(schiefgegangen)

        gefunden.append({
            "adresse": adresse,
            "pfad": pfad,
            # Tiefe 1, nicht 0: Die Oberfläche rückt nach `tiefe - 1` ein und
            # käme sonst auf einen negativen Abstand.
            "tiefe": 1,
            "name": str(name) if name else _lesbar(pfad.rsplit("/", 1)[-1]),
            "nummer": None,
            "produkte": anzahl,
            "fehler": fehler,
        })
    return gefunden


def _ist_beiwerk(adresse: str) -> bool:
    unten = adresse.lower()
    return any(stueck in unten for stueck in KEINE_PRODUKTE)


def seite(adresse: str) -> dict[str, object]:
    """Liest eine einzelne Seite aus.

    Die og:-Angaben sind der beste verfügbare Halt: Sie stehen genau dafür da,
    dass ein soziales Netzwerk eine Vorschau bauen kann, und sind deshalb
    meistens gepflegter als der Rest der Seite. Fehlen sie, wird der Titel aus
    `<title>` genommen.
    """
    roh, gelandet = text_und_ziel(adresse)

    # Wer umgeleitet wurde, ist woanders. Landet man auf einer Übersicht oder
    # einer Fehlerseite, gibt es das Produkt nicht mehr - ein Beitrag darüber
    # bewirbt eine Adresse, die niemanden zum Angekündigten führt.
    if _ist_keine_produktseite(gelandet):
        raise ProduktFortgezogen(adresse, gelandet)

    angaben = og_angaben(roh)

    titel = angaben.get("title") or _titel_aus(roh) or gelandet
    beschreibung = angaben.get("description") or _beschreibung_aus(roh) or ""
    fliesstext = _fliesstext(roh)
    if fliesstext:
        beschreibung = f"{beschreibung}\n\n{fliesstext}" if beschreibung else fliesstext
    bild = angaben.get("image") or _produktbild(roh, gelandet)

    return {
        "fremd_id": gelandet,
        "titel": entmarken(titel),
        "text": entmarken(beschreibung),
        "adresse": gelandet,
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


#: Endadressen, hinter denen kein einzelnes Produkt steckt.
KEIN_ZIEL = ("/list.html", "/errordoc/", "/404", "/suche", "/search")


def _ist_keine_produktseite(adresse: str) -> bool:
    unten = adresse.lower()
    return any(stueck in unten for stueck in KEIN_ZIEL)


#: Wie viel Fließtext höchstens mitgenommen wird. Genug für die Beschreibung
#: samt Merkmalen, zu wenig, um eine ganze Kategorieseite einzuschleppen.
TEXTGRENZE = 4000

#: Kürzer als das ist eine Schaltfläche oder eine Zeile aus dem Menü.
KUERZESTER_ABSATZ = 60


def _fliesstext(roh: str) -> str:
    """Sammelt, was auf der Seite wirklich über das Produkt steht.

    Die og:description reicht nicht. Sie ist für die Vorschau in sozialen
    Netzwerken geschrieben, also 150 Zeichen Werbung mit Häkchen-Zeichen -
    daraus lässt sich kein Beitrag bauen, der etwas aussagt. Am 2026-08-28
    gemessen: 172 Zeichen Werbung, während auf derselben Seite 2.800 Zeichen
    Fachtext standen, mit Normnummer und Herstellernamen. Genau das, wonach
    Claude sonst zurückfragen muss.

    Nur Blattelemente (`p`, `li`, Überschriften), nie umschließende `div`.
    Sonst nimmt man denselben Satz dreimal mit, einmal je Verschachtelung.
    """
    stuecke: list[str] = []
    gesehen: set[str] = set()
    for treffer in re.finditer(r"<(p|li|h1|h2|h3|h4)\b[^>]*>(.*?)</\1>",
                               roh, re.IGNORECASE | re.DOTALL):
        text = entmarken(treffer.group(2))
        if len(text) < KUERZESTER_ABSATZ or text in gesehen:
            continue
        gesehen.add(text)
        stuecke.append(text)
        if sum(len(s) for s in stuecke) >= TEXTGRENZE:
            break
    return "\n\n".join(stuecke)[:TEXTGRENZE]


def _titel_aus(roh: str) -> str | None:
    treffer = _TITEL.search(roh)
    return treffer.group(1).strip() if treffer else None


def _beschreibung_aus(roh: str) -> str | None:
    treffer = _BESCHREIBUNG.search(roh)
    return treffer.group(1).strip() if treffer else None
