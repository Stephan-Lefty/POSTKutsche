"""Tipp und Produkt der Woche: von einer Eingabe zum fertigen Beitrag.

Beide Formate erscheinen wöchentlich und laufen denselben Weg: etwas
hineingeben, Claude schreiben lassen, Grafik zeichnen, Beitrag in den Kalender.
Was hineingeht, unterscheidet sich – beim Produkt ein Verweis in den Shop,
beim Tipp ein Thema –, der Rest ist gleich und steht deshalb hier einmal.

**Ein Fehlschlag verwirft den Beitrag nicht.** Wenn Claude nicht antwortet
oder kein Browser da ist, entsteht der Kalendereintrag trotzdem – mit
Gerüsttexten und ohne Bild, und mit einer Meldung, die sagt warum. Der Termin
ist das Wertvolle; Text und Bild lassen sich nachliefern. Das ist dieselbe
Entscheidung wie bei »Beitrag von Hand«.

**Ohne ausgezeichneten Preis entsteht kein Produktbeitrag.** Hier wird
abgebrochen statt weitergemacht: Eine Anzeige mit falschem Preis ist
schlimmer als keine Anzeige. Welcher Preis gemeint ist, steht in
`quellen/seitenkarte.preis`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import bilder, denker, grafik, konfiguration, netzwerke, zeiten
from .denker import vorlagen
from .quellen import seitenkarte

#: Welches Bild welches Netzwerk bekommt. Instagram zeigt 4:5 und schneidet
#: alles andere zu; die übrigen zeigen Querformat.
HOCHFORMAT_FUER = {"instagram"}

PRODUKT = "produkt"
TIPP = "tipp"

#: Zu welchem Projekt ein Format gehört, wenn nichts anderes gesagt wird.
#:
#: Beide Formate erscheinen wöchentlich im selben Laden – nach dem Projekt zu
#: fragen hieße, eine Frage zu stellen, deren Antwort schon in der Überschrift
#: des Fensters steht. Gibt es das Projekt nicht, bleibt die Auswahl sichtbar;
#: wer ein zweites »Produkt der Woche« für einen anderen Laden anlegt,
#: bekommt sie ebenfalls zurück, weil dann nicht mehr eindeutig ist, welches
#: gemeint war.
VORGABEPROJEKT = {PRODUKT: "produkt-woche", TIPP: "tipp-woche"}


class WochenFehler(Exception):
    """Der Beitrag konnte nicht entstehen. Die Meldung ist für Menschen."""


def produkt(ablage, kennung: str, adresse: str, geplant: str,
            netze: list[str]) -> dict[str, Any]:
    """»Produkt der Woche« aus einem Verweis in den Shop.

    `geplant` ist der Sendezeitpunkt in UTC; bis wann das Angebot gilt, wird
    daraus gerechnet – Montag bis Sonntag, siehe `zeiten.wochenschluss`.
    """
    projekt = _projekt(ablage, kennung, PRODUKT)
    try:
        seiteninhalt = seitenkarte.seite(adresse)
    except seitenkarte.AbrufFehler as fehler:
        raise WochenFehler(f"Die Produktseite ließ sich nicht lesen: {fehler}") from fehler

    preis = seiteninhalt.get("preis")
    if not preis or not preis.get("jetzt"):
        raise WochenFehler(
            "Auf dieser Seite steht kein ausgezeichneter Preis "
            "(itemprop=\"price\"). Ohne ihn entsteht kein Beitrag: Der Preis "
            "im Fließtext gehört oft zu einem Artikel aus der "
            "Empfehlungsliste daneben.")

    gueltig = zeiten.lesbar(zeiten.wochenschluss(zeiten.lesen(geplant)))
    quelle = {
        "titel": seiteninhalt["titel"],
        "adresse": seiteninhalt["adresse"],
        "text": seiteninhalt["text"],
        "merkmale": seiteninhalt.get("merkmale") or [],
        "preis": preis,
        "gueltig": f"Angebot gültig bis {gueltig} Uhr",
    }
    return _bauen(ablage, projekt, PRODUKT, quelle, geplant, netze,
                  seiteninhalt.get("bild_adresse"), _preisfelder(preis, quelle))


def _preisfelder(preis: dict[str, str], quelle: dict[str, Any]) -> dict[str, str]:
    """Was in die Preisbox gehört – aus der Seite, nicht aus dem Modell.

    Claude füllt Name und Merkmale; Preis und Laufzeit stehen fest und werden
    deshalb hier ergänzt. Sie durch das Modell zu schicken, hieße, eine
    bekannte Zahl abschreiben zu lassen – und irgendwann schriebe es sie falsch ab.
    """
    felder = {"preis": preis["jetzt"], "gueltig": quelle["gueltig"]}
    if preis.get("vorher"):
        felder["preis_alt"] = preis["vorher"]
        gespart = _differenz(preis["vorher"], preis["jetzt"])
        if gespart:
            felder["ersparnis"] = gespart
    return felder


def _differenz(vorher: str, jetzt: str) -> str | None:
    """»1.100,00 €« minus »959,00 €« ergibt »141,00 €«.

    Gerechnet statt erfragt: Eine Ersparnis, die jemand tippt, ist eine
    Ersparnis, die irgendwann nicht mehr zum Preis daneben passt. Lässt sich
    eine der Zahlen nicht lesen, kommt nichts zurück – lieber keine Angabe
    als eine erfundene.
    """
    zahlen = []
    for text in (vorher, jetzt):
        roh = "".join(z for z in text if z.isdigit() or z in ",.")
        roh = roh.replace(".", "").replace(",", ".").strip(".")
        try:
            zahlen.append(float(roh))
        except ValueError:
            return None
    gespart = zahlen[0] - zahlen[1]
    if gespart <= 0:
        return None
    waehrung = "".join(
        z for z in jetzt if not (z.isdigit() or z in ",.- ")).strip()
    return f"{gespart:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".") \
        + (f" {waehrung}" if waehrung else "")


def tipp(ablage, kennung: str, thema: str, geplant: str, netze: list[str],
         bild_adresse: str | None = None, hinweise: str = "") -> dict[str, Any]:
    """»Tipp der Woche« aus einem vorgegebenen Thema.

    `bild_adresse` ist ein Stimmungsbild. Anders als beim Produkt liefert
    niemand eines mit – ein Thema hat kein Foto. Fehlt es, bleibt die
    Fotospalte dunkel; das ist brauchbar, aber blass.
    """
    projekt = _projekt(ablage, kennung, TIPP)
    if not thema.strip():
        raise WochenFehler("Ohne Thema gibt es nichts zu schreiben.")
    quelle = {"thema": thema.strip(), "hinweise": hinweise.strip()}
    return _bauen(ablage, projekt, TIPP, quelle, geplant, netze, bild_adresse)


def _projekt(ablage, kennung: str, art: str = ""):
    """Das Projekt – oder das vorgesehene, wenn keines genannt wurde."""
    if not kennung and art:
        kennung = VORGABEPROJEKT.get(art, "")
    projekt = ablage.projekt(kennung)
    if projekt is None:
        raise WochenFehler(
            f"Kein Projekt »{kennung}«. Für dieses Format ist "
            f"»{VORGABEPROJEKT.get(art, '?')}« vorgesehen; anlegen mit "
            f"»postkutsche projekt neu«.")
    return projekt


def _bauen(ablage, projekt, art: str, quelle: dict[str, Any], geplant: str,
           netze: list[str], bild_adresse: str | None,
           feste_felder: dict[str, str] | None = None) -> dict[str, Any]:
    """Der gemeinsame Teil: schreiben lassen, zeichnen, in den Kalender.

    `feste_felder` sind Grafikangaben, die nicht vom Modell kommen – beim
    Produkt der Preis und die Laufzeit des Angebots.
    """
    if not netze:
        raise WochenFehler("Mindestens ein Netzwerk muss dabei sein.")
    for netz in netze:
        netzwerke.netzwerk(netz)  # wirft, wenn es das Netzwerk nicht gibt

    meldungen: list[str] = []
    marke = konfiguration.marke(projekt.kennung) or dict(grafik.BEISPIEL_MARKE)

    # Das Foto wird nicht zugeschnitten: Die Grafik legt es selbst in ihre
    # Spalte, und ein auf 4:5 beschnittenes Bild wäre dort zweimal zugeschnitten.
    foto = None
    if bild_adresse:
        try:
            foto = bilder.beschaffen(bild_adresse, zuschneiden=False)
        except bilder.BildFehler as fehler:
            meldungen.append(f"Bild nicht geholt: {fehler}")

    fassungen, grafikdaten = _schreiben_lassen(art, quelle, netze, projekt, meldungen)
    if grafikdaten and feste_felder:
        grafikdaten = {**grafikdaten, **feste_felder}

    bild_quer = bild_hoch = None
    if grafikdaten:
        bild_quer, bild_hoch = _zeichnen(art, grafikdaten, marke, foto,
                                         projekt.kennung, geplant, meldungen)

    inhalt_id = _inhalt_merken(ablage, projekt, art, quelle, grafikdaten)
    beitrag = ablage.beitrag_anlegen(projekt.id, geplant, inhalt_id=inhalt_id)
    for netz, fassung in fassungen.items():
        pfad = bild_hoch if netz in HOCHFORMAT_FUER else bild_quer
        ablage.fassung_setzen(
            beitrag, netz, fassung["text"], fassung.get("schlagworte", ""),
            bild_pfad=str(pfad) if pfad else None,
            rueckfrage=fassung.get("rueckfrage"))

    return {
        "id": beitrag,
        "geplant": geplant,
        "lesbar": zeiten.lesbar(geplant),
        "bild": str(bild_quer) if bild_quer else None,
        "bild_hoch": str(bild_hoch) if bild_hoch else None,
        "alternativtext": grafik.alternativtext(art, grafikdaten) if grafikdaten else "",
        "meldung": " ".join(meldungen),
    }


def _schreiben_lassen(art, quelle, netze, projekt, meldungen):
    """Claude fragen – und bei einem Fehlschlag mit Gerüsten weitermachen."""
    try:
        anweisung = vorlagen.wochenanweisung(art, quelle, netze, projekt.name)
        roh = denker.fragen(anweisung, projektdaten=projekt)
        return vorlagen.wochenantwort_lesen(roh, netze, art)
    except (denker.DenkerFehler, vorlagen.AntwortFehler, ValueError) as fehler:
        meldungen.append(f"Angelegt, aber nicht geschrieben: {fehler}")
        geruest = {"titel": quelle.get("titel") or quelle.get("thema", ""),
                   "text": quelle.get("text", ""),
                   "adresse": quelle.get("adresse", "")}
        return denker.hand.fassungen(geruest, netze), None


def _zeichnen(art, grafikdaten, marke, foto, kennung, geplant, meldungen):
    """Beide Formate zeichnen. Fehlt der Browser, bleibt es bei der Meldung."""
    if not grafik.vorhanden():
        meldungen.append(grafik.nicht_da())
        return None, None
    daten = dict(grafikdaten, bild=str(foto) if foto else None)
    seite = grafik.produkt_seite if art == PRODUKT else grafik.tipp_seite
    mitbringen = [p for p in (foto, marke.get("logo")) if p]
    ordner = bilder.ordner()
    stamm = f"{art}-{kennung}-{geplant.replace(':', '').replace('-', '')}"
    try:
        quer = grafik.zeichnen(seite(daten, marke), ordner / f"{stamm}.png",
                               mitbringen)
        hoch = grafik.zeichnen(seite(daten, marke, hoch=True),
                               ordner / f"{stamm}-hoch.png", mitbringen, hoch=True)
    except grafik.GrafikFehler as fehler:
        meldungen.append(f"Grafik nicht gezeichnet: {fehler}")
        return None, None
    return quer, hoch


def _inhalt_merken(ablage, projekt, art, quelle, grafikdaten):
    """Den Inhalt eintragen, auf den der Beitrag zeigt.

    Beim Produkt ist das die Shopseite. Beim Tipp gibt es keine – dann wird
    wie bei »Beitrag von Hand« eine eigene Kennung vergeben, sonst überschriebe
    der nächste Tipp mit gleichem Titel den vorigen.
    """
    if art == PRODUKT:
        titel = (grafikdaten or {}).get("name") or quelle["titel"]
        return ablage.inhalt_merken(
            projekt.id, quelle["adresse"], titel, quelle["adresse"],
            quelle.get("text", ""))[0]
    titel = " ".join(x for x in ((grafikdaten or {}).get("titel", ""),
                                 (grafikdaten or {}).get("unterzeile", "")) if x)
    fremd_id = f"tipp-{zeiten.jetzt_utc()}"
    return ablage.inhalt_merken(
        projekt.id, fremd_id, titel or quelle["thema"], f"hand:{fremd_id}",
        quelle["thema"])[0]
