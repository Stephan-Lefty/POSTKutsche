"""Kampagnen: ein Thema, eine Woche, ein paar Kategorien – und der Plan steht.

Für die Shops ist das der eigentliche Arbeitsweg, nicht das automatische
Erkennen neuer Produkte. Stephan sagt: »In KW 36 machen wir Modell X
Stahlblechtüren«, gibt zwei Kategorieadressen dazu, und daraus entstehen ein
bis zwei Beiträge je Tag. Das Werkzeug sucht die Produkte, verteilt sie auf die
Woche und legt Entwürfe an; geschrieben werden sie von Claude, freigegeben von
Hand.

Warum nicht einfach der Reihe nach durch die Kategorie? Weil eine Kategorie wie
»Modell X Brandschutztüren« fünfzehn Produkte enthält, die sich nur in Breite und
Höhe unterscheiden. Vier Tage hintereinander dieselbe Tür in vier Maßen ist
kein Redaktionsplan, sondern ein Ausdruck der Preisliste. Deshalb wird
gestreut: erst über die Kategorien, dann innerhalb der Kategorie über möglichst
verschiedene Produkte.

**Preise stehen standardmäßig nicht im Beitrag.** Ein Preis ändert sich, der
Beitrag bleibt stehen – und aus einem alten Beitrag wird dann schnell der
Vorwurf, mit falschen Preisen geworben zu haben. Wer es anders will, setzt
`preise=True`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from . import sendezeiten, zeiten


# Hersteller und woran man sie erkennt.
#
# In Produktnamen steht der Hersteller meistens ausgeschrieben. Wo nicht, hilft
# nur die Modellreihe – und welche Reihe zu welcher Marke gehört, ist
# Sortimentswissen. Es steht deshalb **nicht hier**, sondern in
# `~/.config/postkutsche/hersteller.json`; siehe `konfiguration.py`. Mit welchen
# Herstellern jemand arbeitet, muss nicht in einem öffentlichen Repository
# nachzulesen sein.
#
# Was hier steht, ist ein Beispiel, das die Form zeigt: Unter »namen« die
# Schreibvarianten (mit Umlaut, ausgeschrieben, und ohne alles – in Dateinamen
# steht selten ein ö), unter »reihen« die Modellbezeichnungen.
BEISPIEL_HERSTELLER: dict[str, dict[str, list[str]]] = {
    "musterwerk": {
        "namen": ["musterwerk", "muster-werk"],
        "reihen": ["mw12", "mw40"],
    },
    "beispielbau": {
        "namen": ["beispielbau"],
        "reihen": ["bb7"],
    },
}


def _hersteller_laden() -> dict[str, dict[str, list[str]]]:
    from . import konfiguration

    eigene = konfiguration.hersteller_lesen()
    return eigene if eigene else dict(BEISPIEL_HERSTELLER)


#: Wird beim Laden des Moduls einmal gefüllt. `hersteller_neu_laden()` liest
#: die Datei erneut – das brauchen die Tests und die Oberfläche nach dem
#: Bearbeiten der Konfiguration.
HERSTELLER: dict[str, dict[str, list[str]]] = _hersteller_laden()


def hersteller_neu_laden() -> None:
    """Liest ~/.config/postkutsche/hersteller.json erneut ein."""
    global HERSTELLER
    HERSTELLER = _hersteller_laden()


@dataclass
class Kampagne:
    """Was gemacht werden soll, in welcher Woche, aus welchen Quellen."""

    thema: str
    projekt: str
    kalenderwoche: int
    jahr: int
    kategorien: list[str] = field(default_factory=list)
    netzwerke: list[str] = field(default_factory=list)
    je_tag: int = 1
    tage: tuple[int, ...] = sendezeiten.WERKTAGS
    preise: bool = False
    # Leer heißt: alle Hersteller. Sonst nur diese – so entsteht eine
    # Herstellerwoche quer durch die Kategorien.
    hersteller: list[str] = field(default_factory=list)
    hinweis: str = ""

    def __post_init__(self) -> None:
        if not 1 <= self.kalenderwoche <= 53:
            raise ValueError(
                f"Kalenderwoche {self.kalenderwoche} gibt es nicht. "
                "Erlaubt ist 1 bis 53."
            )
        if self.je_tag < 1:
            raise ValueError("Mindestens ein Beitrag je Tag.")
        if not self.tage:
            raise ValueError("Ohne Tage keine Kampagne.")

    @property
    def anzahl(self) -> int:
        """Wie viele Beiträge insgesamt entstehen."""
        return len(self.tage) * self.je_tag


def woche_beginnt(jahr: int, kalenderwoche: int) -> date:
    """Der Montag einer Kalenderwoche nach ISO 8601.

    Nicht selbst rechnen: Die erste Woche eines Jahres ist die mit dem ersten
    Donnerstag, und deshalb beginnt KW 1 mitunter im Dezember des Vorjahres.
    `fromisocalendar` weiß das.
    """
    return date.fromisocalendar(jahr, kalenderwoche, 1)


def termine(kampagne: Kampagne, netzwerk: str, zielgruppe: str) -> list[tuple[str, str]]:
    """Die Sendezeitpunkte der Kampagne, mit Begründung.

    Je Tag werden so viele Fenster belegt, wie `je_tag` verlangt – das beste
    zuerst. Reichen die Fenster für einen Tag nicht, wird das letzte um zwei
    Stunden versetzt wiederholt, statt zwei Beiträge auf dieselbe Minute zu
    legen. Zwei Beiträge zur selben Zeit sieht niemand, der eine verdeckt den
    anderen.
    """
    montag = woche_beginnt(kampagne.jahr, kampagne.kalenderwoche)
    fenster = sendezeiten.fenster_fuer(netzwerk, zielgruppe)

    geplant: list[tuple[str, str]] = []
    for wochentag in sorted(kampagne.tage):
        tag = montag + timedelta(days=wochentag)
        passend = [f for f in fenster if wochentag in f.tage] or fenster[:1]

        for nummer in range(kampagne.je_tag):
            if nummer < len(passend):
                gewaehlt = passend[nummer]
                stunde, minute = gewaehlt.stunde, gewaehlt.minute
                grund = gewaehlt.grund
            else:
                # Mehr Beiträge als Fenster: das letzte versetzt wiederholen.
                gewaehlt = passend[-1]
                versatz = 2 * (nummer - len(passend) + 1)
                stunde = min(gewaehlt.stunde + versatz, 22)
                minute = gewaehlt.minute
                grund = f"{gewaehlt.grund} (versetzt, weil mehrere Beiträge am Tag)"

            zeitpunkt = datetime(
                tag.year, tag.month, tag.day, stunde, minute,
                tzinfo=zeiten.ORTSZONE,
            )
            geplant.append((zeiten.schreiben(zeitpunkt), grund))

    return geplant


def _vereinfachen(text: str) -> str:
    """Macht Schreibvarianten vergleichbar.

    »Musterwerk«, »MUSTERWERK« und »Muster-Werk« sollen dasselbe treffen. In
    Produktadressen steht praktisch nie ein Umlaut, in Titeln fast immer –
    also werden beide auf eine Form gebracht. Zusätzlich fällt der Umlaut auch
    auf den nackten Vokal, weil »Hormann« im Netz häufiger vorkommt, als einem
    lieb ist.
    """
    klein = text.lower()
    for umlaut, ersatz in (("ö", "oe"), ("ä", "ae"), ("ü", "ue"), ("ß", "ss")):
        klein = klein.replace(umlaut, ersatz)
    # Trennzeichen vereinheitlichen, damit »h3_od«, »h3-od« und »h3 od« gleich sind.
    return re.sub(r"[^a-z0-9]+", " ", klein)


def hersteller_von(produkt: dict) -> str | None:
    """Welcher Hersteller steckt hinter einem Produkt – oder keiner.

    Gesucht wird in Titel und Adresse. Erst nach dem Namen, dann nach den
    Modellreihen: Ein Produkt, das »Musterwerk« im Namen trägt, ist eines, auch
    wenn irgendwo eine fremde Modellbezeichnung vorkommt.
    """
    heuhaufen = _vereinfachen(
        f"{produkt.get('titel', '')} {produkt.get('adresse', '')} "
        f"{produkt.get('fremd_id', '')}"
    )

    for kennung, angaben in HERSTELLER.items():
        for name in angaben["namen"]:
            if _vereinfachen(name) in heuhaufen:
                return kennung
    for kennung, angaben in HERSTELLER.items():
        for reihe in angaben["reihen"]:
            if _reihe_kommt_vor(reihe, heuhaufen):
                return kennung
    return None


def _reihe_kommt_vor(reihe: str, heuhaufen: str) -> bool:
    """Prüft eine Modellreihe – am Wortanfang und ohne folgende Ziffer.

    Kürzel wie »mw12«, »bb7« und »d65« sind kurz genug, um versehentlich in
    anderen Modellnummern zu stecken. Ohne diese Prüfung fände »mw12« auch die
    »H30«, und eine Herstellerwoche bewürbe fremde Türen. Die Bedingung »keine
    Ziffer danach« ist der entscheidende Teil: »mw12« soll »mw40x« treffen, aber
    nicht »h35«.
    """
    muster = rf"\b{re.escape(_vereinfachen(reihe).strip())}(?!\d)"
    return re.search(muster, heuhaufen) is not None


def kennung_von(name: str) -> str | None:
    """Bildet eine Eingabe auf eine Herstellerkennung ab.

    »Musterwerk«, »MUSTERWERK« und »Muster-Werk« sollen alle auf dieselbe
    Kennung führen –
    wer den Hersteller eintippt, soll nicht wissen müssen, wie er hier
    geschrieben steht.
    """
    gesucht = _vereinfachen(name).strip()
    if not gesucht:
        return None
    for kennung, angaben in HERSTELLER.items():
        varianten = [kennung, *angaben["namen"]]
        if any(_vereinfachen(v).strip() == gesucht for v in varianten):
            return kennung
    return None


class UnbekannterHersteller(ValueError):
    """Ein Hersteller, den das Verzeichnis nicht kennt."""


def nach_hersteller(
    produkte: list[dict], gewuenscht: list[str]
) -> tuple[list[dict], list[dict]]:
    """Trennt Produkte in »passt« und »nicht zuzuordnen«.

    Gibt zwei Listen zurück, und das ist der Punkt: Was sich keinem Hersteller
    zuordnen ließ, wird **gemeldet, nicht verschwiegen**. Sonst fehlen in einer
    Herstellerwoche zwei Türen, und niemand erfährt, warum.

    Ein Hersteller, den das Verzeichnis nicht kennt, ist ein Fehler und keine
    leere Ergebnisliste. Eine Kampagne, die stillschweigend null Beiträge
    erzeugt, fällt erst am Montag auf – wenn nichts erscheint.

    Ist `gewuenscht` leer, passt alles.
    """
    if not gewuenscht:
        return list(produkte), []

    verlangt: set[str] = set()
    for name in gewuenscht:
        kennung = kennung_von(name)
        if kennung is None:
            bekannt = ", ".join(sorted(HERSTELLER))
            raise UnbekannterHersteller(
                f"Hersteller {name!r} steht nicht im Verzeichnis. "
                f"Bekannt sind: {bekannt}. Neue trägt man in HERSTELLER "
                "in kampagnen.py ein."
            )
        verlangt.add(kennung)

    passend: list[dict] = []
    unklar: list[dict] = []

    for produkt in produkte:
        kennung = hersteller_von(produkt)
        if kennung is None:
            unklar.append(produkt)
        elif kennung in verlangt:
            passend.append(dict(produkt, hersteller=kennung))

    return passend, unklar


def streuen(produkte: list[dict], anzahl: int) -> list[dict]:
    """Wählt aus vielen Produkten wenige aus, die sich unterscheiden.

    Zwei Regeln, beide aus dem Blick auf echte Kategorien entstanden:

    1. **Erst reihum durch die Kategorien.** Wer zwei Kategorien angibt, will
       nicht drei Tage die eine und zwei Tage die andere.
    2. **Innerhalb einer Kategorie nach Namensstamm.** »Modell X, Breite
       1500 mm«, »… Breite 1750 mm«, »… Breite 2000 mm« sind für einen Leser
       dasselbe Produkt. Von jedem Stamm kommt zuerst nur eines dran; erst wenn
       die Stämme ausgehen, wird nachgelegt.
    """
    if anzahl <= 0 or not produkte:
        return []

    nach_kategorie: dict[str, list[dict]] = {}
    for produkt in produkte:
        nach_kategorie.setdefault(str(produkt.get("kategorie", "")), []).append(produkt)

    # Je Kategorie eine Reihenfolge bilden, in der verschiedene Stämme vorn stehen.
    reihen = {
        name: _nach_stamm_sortieren(eintraege)
        for name, eintraege in nach_kategorie.items()
    }

    gewaehlt: list[dict] = []
    runde = 0
    while len(gewaehlt) < anzahl:
        etwas_genommen = False
        for name in sorted(reihen):
            if runde < len(reihen[name]):
                gewaehlt.append(reihen[name][runde])
                etwas_genommen = True
                if len(gewaehlt) >= anzahl:
                    break
        if not etwas_genommen:
            break  # Produkte alle – lieber weniger Beiträge als Wiederholungen
        runde += 1

    return gewaehlt


# Trennt den beschreibenden Teil eines Produktnamens von den Maßangaben.
# »… Breite 1500 mm Höhe 4000mm« und »… 1000x2125« sollen denselben Stamm ergeben.
_MASSE = re.compile(
    r"(breite|hoehe|höhe|h[oö]he|width|height)?\s*\d{3,4}\s*(mm|cm|x)?",
    re.IGNORECASE,
)


def _stamm(titel: str) -> str:
    ohne_masse = _MASSE.sub(" ", titel.lower())
    # Was übrig bleibt, auf Wörter reduzieren; die ersten paar tragen die Bedeutung.
    woerter = [w for w in re.split(r"[^a-zäöüß0-9]+", ohne_masse) if len(w) > 2]
    return " ".join(woerter[:5])


def _nach_stamm_sortieren(produkte: list[dict]) -> list[dict]:
    """Ordnet so um, dass verschiedene Produkte vor Varianten desselben kommen."""
    nach_stamm: dict[str, list[dict]] = {}
    for produkt in produkte:
        nach_stamm.setdefault(_stamm(str(produkt.get("titel", ""))), []).append(produkt)

    geordnet: list[dict] = []
    runde = 0
    while True:
        etwas = False
        for stamm in sorted(nach_stamm):
            if runde < len(nach_stamm[stamm]):
                geordnet.append(nach_stamm[stamm][runde])
                etwas = True
        if not etwas:
            return geordnet
        runde += 1
