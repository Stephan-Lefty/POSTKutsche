"""Eine Kampagne ausführen: aus Kategorien wird ein Wochenplan.

`kampagnen.py` rechnet – Termine, Streuung, Herstellerfilter. Hier wird
daraus wirklich etwas: Produkte holen, Claude schreiben lassen, Bilder
beschaffen, Beiträge anlegen.

**Was schiefgeht, geht einzeln schief.** Scheitert ein Produkt – die Seite
antwortet nicht, Claude liefert Unsinn –, wird das vermerkt und der Rest
läuft weiter. Eine Woche mit acht statt zehn Beiträgen ist brauchbar; ein
Abbruch nach dem dritten wäre es nicht.
"""

from __future__ import annotations

from typing import Any

from . import bilder, denker, kampagnen, sendezeiten, zeiten
from .quellen import seitenkarte


def produkte_sammeln(kampagne: kampagnen.Kampagne,
                     grenze_je_kategorie: int = 40) -> list[dict[str, Any]]:
    """Holt die Produktadressen aus den Kategorien der Kampagne.

    Nur die Adressen, nicht die Seiten selbst - das wären hundert Abrufe für
    zehn Beiträge. Ausgelesen wird erst, was nach dem Streuen übrig bleibt.
    """
    gesammelt: list[dict[str, Any]] = []
    for adresse in kampagne.kategorien:
        name = _kategoriename(adresse)
        for produkt in seitenkarte.kategorie(adresse, grenze_je_kategorie):
            gesammelt.append({
                "adresse": produkt,
                "kategorie": name,
                # Für Streuung und Herstellersuche reicht der Adressteil; der
                # richtige Titel kommt erst beim Auslesen der Seite.
                "titel": produkt.rsplit("/", 1)[-1].replace("_", " ").replace(".html", ""),
            })
    return gesammelt


def ausfuehren(ablage, kampagne: kampagnen.Kampagne, melden=None) -> dict[str, Any]:
    """Legt die Beiträge einer Kampagne an. Gibt einen Bericht zurück."""
    sagen = melden or (lambda *_: None)

    projekt = ablage.projekt(kampagne.projekt)
    if projekt is None:
        raise ValueError(f"Kein Projekt »{kampagne.projekt}«.")
    if not denker.verfuegbar():
        raise ValueError("»claude« ist nicht im Suchpfad oder nicht angemeldet.")

    sagen("Produkte sammeln …")
    alle = produkte_sammeln(kampagne)
    if not alle:
        return _bericht([], [], "In diesen Kategorien stehen keine Produkte. "
                                "Übersichtsseiten enthalten oft nur Unterkategorien.")

    unklar: list[dict[str, Any]] = []
    if kampagne.hersteller:
        alle, unklar = kampagnen.nach_hersteller(alle, kampagne.hersteller)
        if not alle:
            return _bericht([], unklar,
                            "Kein Produkt dieser Hersteller in den Kategorien.")

    gewaehlt = kampagnen.streuen(alle, kampagne.anzahl)
    zielgruppe = sendezeiten.zielgruppe_von(projekt)
    netze = kampagne.netzwerke or ["facebook"]
    termine = kampagnen.termine(kampagne, netze[0], zielgruppe)

    angelegt: list[dict[str, Any]] = []
    gescheitert: list[dict[str, Any]] = []

    for nummer, produkt in enumerate(gewaehlt):
        if nummer >= len(termine):
            break
        termin, grund = termine[nummer]
        sagen(f"{nummer + 1}/{len(gewaehlt)}: {produkt['titel'][:50]}")
        try:
            angelegt.append(
                _ein_beitrag(ablage, projekt, produkt, termin, grund, netze,
                             kampagne.thema)
            )
        except Exception as fehler:  # noqa: BLE001
            # Einzeln scheitern lassen: Acht Beiträge statt zehn sind
            # brauchbar, ein Abbruch nach dem dritten nicht.
            gescheitert.append({"titel": produkt["titel"],
                                "adresse": produkt["adresse"],
                                "grund": str(fehler)[:300]})
            sagen(f"   gescheitert: {fehler}")

    return _bericht(angelegt, unklar, None, gescheitert)


def _ein_beitrag(ablage, projekt, produkt, termin, grund, netze, thema):
    seite = seitenkarte.seite(produkt["adresse"])

    nummer, _ = ablage.inhalt_merken(
        projekt.id, seite["fremd_id"], seite["titel"], seite["adresse"],
        str(seite.get("text", "")), seite.get("bild_adresse"),
    )

    zusatz = f"Diese Woche steht unter dem Thema: {thema}." if thema else ""
    fassungen = denker.schreiben(seite, netze, projekt.name, zusatz)

    bild = None
    if seite.get("bild_adresse"):
        try:
            bild = str(bilder.beschaffen(str(seite["bild_adresse"])))
        except bilder.BildFehler:
            # Ein fehlendes Bild ist kein Grund, den Beitrag zu verwerfen -
            # bei Facebook geht es auch ohne. Wo es Pflicht ist, meldet die
            # Fassung das ohnehin als Rückfrage.
            bild = None

    beitrag = ablage.beitrag_anlegen(projekt.id, termin, inhalt_id=nummer)
    fragen = 0
    for netz in netze:
        f = fassungen[netz]
        ablage.fassung_setzen(beitrag, netz, f["text"], f["schlagworte"], bild,
                              rueckfrage=f.get("rueckfrage"))
        fragen += 1 if f.get("rueckfrage") else 0

    return {
        "id": beitrag,
        "titel": seite["titel"],
        "geplant": termin,
        "lesbar": zeiten.lesbar(termin),
        "grund": grund,
        "bild": bool(bild),
        "rueckfragen": fragen,
    }


def _kategoriename(adresse: str) -> str:
    teile = [t for t in adresse.split("/") if t and t != "list.html"]
    return teile[-1] if teile else adresse


def _bericht(angelegt, unklar, hinweis=None, gescheitert=None) -> dict[str, Any]:
    return {
        "angelegt": angelegt,
        "anzahl": len(angelegt),
        "gescheitert": gescheitert or [],
        # Was sich keinem Hersteller zuordnen ließ, wird genannt und nicht
        # verschwiegen: Sonst fehlen in einer Herstellerwoche zwei Türen, und
        # niemand erfährt, warum.
        "nicht_zugeordnet": [u["titel"] for u in unklar],
        "hinweis": hinweis,
    }
