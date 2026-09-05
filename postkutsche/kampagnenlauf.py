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

from datetime import timedelta

from . import bilder, denker, kampagnen, sendezeiten, zeiten
from .quellen import seitenkarte, wordpress


def produkte_sammeln(kampagne: kampagnen.Kampagne,
                     grenze_je_kategorie: int = 40,
                     projekt: Any = None) -> list[dict[str, Any]]:
    """Holt die Adressen aus den Kategorien der Kampagne.

    Nur die Adressen, nicht die Seiten selbst - das wären hundert Abrufe für
    zehn Beiträge. Ausgelesen wird erst, was nach dem Streuen übrig bleibt.

    **Ein Blog wird anders gelesen als ein Shop.** WordPress sagt selbst, was
    in einer Kategorie steht; bei einem Shop ohne Schnittstelle muss man die
    Kategorieseite durchsehen. Was hinten herauskommt, ist dasselbe: Adresse,
    Kategorie, Titel.

    Ohne `projekt` bleibt es beim Shopweg - so, wie es vor dem 2026-09-05 war.
    """
    if projekt is not None and getattr(projekt, "art", "") == "wordpress":
        return _beitraege_sammeln(kampagne, projekt, grenze_je_kategorie)

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


def _beitraege_sammeln(kampagne: kampagnen.Kampagne, projekt: Any,
                       grenze: int) -> list[dict[str, Any]]:
    """Der Blogweg: Beiträge aus WordPress-Kategorien.

    Die Kennung des Beitrags wird mitgeführt, damit der ganze Beitrag später
    über die Schnittstelle geholt werden kann statt über die Seite. Der
    Sprachfilter des Projekts gilt auch hier - sonst planten die zweisprachigen
    Blogs jeden Beitrag zweimal, einmal deutsch und einmal englisch.
    """
    stamm = wordpress.rest_adresse_von(projekt)
    ausschliessen = (projekt.einstellungen or {}).get("ausschliessen")
    kategorien = _kategorienamen(stamm, kampagne.kategorien)

    gesammelt: list[dict[str, Any]] = []
    gesehen: set[str] = set()
    for adresse in kampagne.kategorien:
        name = kategorien.get(adresse, _kategoriename(adresse))
        for eintrag in wordpress.beitragsliste(adresse, grenze, ausschliessen):
            # Ein Beitrag kann in zwei gewählten Kategorien stehen. Er soll
            # deshalb nicht zweimal in der Woche erscheinen.
            if eintrag["adresse"] in gesehen:
                continue
            gesehen.add(str(eintrag["adresse"]))
            gesammelt.append({
                "adresse": eintrag["adresse"],
                "kategorie": name,
                "titel": eintrag["titel"],
                "fremd_id": eintrag["fremd_id"],
            })
    return gesammelt


def _kategorienamen(stamm: str, adressen: list[str]) -> dict[str, str]:
    """Ordnet den gewählten Kategorieadressen ihre Namen zu.

    Für die Streuung genügte die Nummer, für den Bericht nicht: »Wandern« sagt
    etwas, »posts?categories=5« nichts. Scheitert der Abruf, wird nicht der
    ganze Lauf hingeworfen - dann steht eben die Adresse da.
    """
    try:
        bekannt = {str(k["adresse"]): str(k["name"])
                   for k in wordpress.kategorien(stamm)}
    except seitenkarte.AbrufFehler:
        return {}
    return {a: bekannt[a] for a in adressen if a in bekannt}


#: Wie lange ein Produkt als »neulich beworben« gilt. Vier Wochen sind lang
#: genug, dass niemand die Wiederholung bemerkt hätte, und kurz genug, dass
#: ein Sortiment mit hundert Artikeln nicht durchgesperrt wird.
SCHONFRIST_TAGE = 28


def wiederholungen_finden(ablage, projekt_id: int,
                          produkte: list[dict[str, Any]],
                          tage: int = SCHONFRIST_TAGE) -> list[dict[str, Any]]:
    """Welche der Produkte in den letzten Wochen schon dran waren.

    Gibt je Treffer Titel, Adresse und den letzten Termin zurück - genug, um
    zu entscheiden, ob man es trotzdem will.
    """
    adressen = [str(p["adresse"]) for p in produkte]
    bekannt = ablage.zuletzt_beworben(projekt_id, adressen)
    if not bekannt:
        return []

    grenze = zeiten.schreiben(
        zeiten.lesen(zeiten.jetzt_utc()) - timedelta(days=tage)
    )
    treffer = []
    for produkt in produkte:
        wann = bekannt.get(str(produkt["adresse"]))
        if wann and wann >= grenze:
            treffer.append({
                "titel": produkt.get("titel", ""),
                "adresse": produkt["adresse"],
                "zuletzt": wann,
                "lesbar": zeiten.lesbar(wann),
            })
    return treffer


#: Was mit kürzlich beworbenen Produkten geschehen soll.
FRAGEN = "fragen"        # abbrechen und zurückmelden
TROTZDEM = "trotzdem"    # nehmen, wie sie sind
ERSETZEN = "ersetzen"    # durch andere ersetzen, die länger nicht dran waren


def ausfuehren(ablage, kampagne: kampagnen.Kampagne, melden=None,
               fortschritt=None, bestaetigt: bool = False,
               wiederholungen: str = FRAGEN,
               abbrechen=None) -> dict[str, Any]:
    """Legt die Beiträge einer Kampagne an. Gibt einen Bericht zurück.

    `fortschritt(getan, gesamt, text)` wird nach jedem Schritt gerufen. Ein
    Lauf über zehn Produkte dauert Minuten - ohne Rückmeldung sieht das aus
    wie ein Absturz, und jemand bricht ab, während es noch läuft.

    `abbrechen()` wird zwischen den Produkten gefragt. Sagt es ja, wird
    zurückgenommen, was der Lauf schon angelegt hat - **Abbrechen heißt
    abbrechen und wegräumen**, nicht »hier stehen bleiben«. Sonst gälten die
    schon bearbeiteten Produkte vier Wochen als beworben, obwohl nie etwas
    erschienen ist, und die nächste Woche fände sie nicht mehr.

    Gefragt wird zwischen den Produkten und nicht mittendrin: Einen laufenden
    `claude -p`-Aufruf mitten im Satz abzuschneiden spart ein paar Sekunden
    und macht den Zustand unübersichtlich.

    Waren Produkte in den letzten vier Wochen schon dran, entscheidet
    `wiederholungen`: `FRAGEN` bricht ab und meldet sie zurück, `TROTZDEM`
    nimmt sie, `ERSETZEN` sucht andere. Der Aufruf kommt also zweimal: einmal
    zum Prüfen, einmal zum Ausführen.
    """
    sagen = melden or (lambda *_: None)
    schritt = fortschritt or (lambda *_: None)
    abgebrochen = abbrechen or (lambda: False)

    projekt = ablage.projekt(kampagne.projekt)
    if projekt is None:
        raise ValueError(f"Kein Projekt »{kampagne.projekt}«.")
    if not denker.verfuegbar():
        raise ValueError("»claude« ist nicht im Suchpfad oder nicht angemeldet.")

    # Vor dem Planen aufräumen: Verfallene Entwürfe sperren sonst über die
    # Vier-Wochen-Regel Produkte, die nie beworben wurden.
    weggeraeumt = ablage.aufraeumen()
    if weggeraeumt:
        sagen(f"{len(weggeraeumt)} verfallene Entwürfe entfernt.")

    sagen("Produkte sammeln …")
    schritt(0, kampagne.anzahl, "Produkte sammeln …")
    alle = produkte_sammeln(kampagne, projekt=projekt)
    # Auch hier schon fragen: Das Sammeln kann eine halbe Minute dauern, und
    # wer in dieser Zeit abbricht, soll nicht noch zehn Beiträge bekommen.
    if abgebrochen():
        return _bericht([], [], "Abgebrochen, bevor etwas angelegt wurde.",
                        abgebrochen=True)
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

    # Was in den letzten vier Wochen schon dran war, wird gemeldet - nicht
    # stillschweigend übersprungen. Vielleicht ist die Wiederholung gewollt.
    wiederholt = wiederholungen_finden(ablage, projekt.id, gewaehlt)

    if wiederholt and wiederholungen == ERSETZEN:
        # Andere nehmen statt weniger: Wer eine Woche plant, will eine volle
        # Woche. Aussortiert wird aus dem ganzen Vorrat, nicht nur aus der
        # bereits getroffenen Auswahl - sonst bleiben Lücken.
        schon_dran = {w["adresse"] for w in wiederholt}
        frisch = [p for p in alle if p["adresse"] not in schon_dran]
        weitere = wiederholungen_finden(ablage, projekt.id, frisch)
        noch_frei = {w["adresse"] for w in weitere}
        frisch = [p for p in frisch if p["adresse"] not in noch_frei]

        gewaehlt = kampagnen.streuen(frisch, kampagne.anzahl)
        sagen(f"{len(wiederholt)} ersetzt, {len(gewaehlt)} Produkte übrig.")
        if not gewaehlt:
            return _bericht([], unklar,
                            "Alle Produkte dieser Kategorien waren in den "
                            "letzten vier Wochen schon dran. Nimm andere "
                            "Kategorien oder plane sie trotzdem ein.")
        wiederholt = []

    if wiederholt and not bestaetigt:
        return {
            "rueckfrage": True,
            "wiederholungen": wiederholt,
            "anzahl": 0,
            "angelegt": [],
            "gescheitert": [],
            "nicht_zugeordnet": [u["titel"] for u in unklar],
            "hinweis": None,
        }
    zielgruppe = sendezeiten.zielgruppe_von(projekt)
    netze = kampagne.netzwerke or ["facebook"]
    termine = kampagnen.termine(kampagne, netze[0], zielgruppe)

    angelegt: list[dict[str, Any]] = []
    gescheitert: list[dict[str, Any]] = []

    for nummer, produkt in enumerate(gewaehlt):
        if nummer >= len(termine):
            break
        if abgebrochen():
            entfernt = _zuruecknehmen(ablage, angelegt, sagen)
            return _bericht(
                [], unklar,
                f"Abgebrochen nach {nummer} von {len(gewaehlt)} Produkten. "
                f"{entfernt} angefangene Entwürfe wurden wieder entfernt.",
                gescheitert, weggeraeumt, abgebrochen=True, entfernt=entfernt,
            )
        termin, grund = termine[nummer]
        sagen(f"{nummer + 1}/{len(gewaehlt)}: {produkt['titel'][:50]}")
        schritt(nummer, len(gewaehlt), produkt["titel"][:60])
        try:
            # Bei einer Wiederholung den alten Text mitgeben, damit der neue
            # anders klingt. Immer, ohne Schalter: Wortgleich ist in keinem
            # Netzwerk besser - Facebook und Instagram halten es zurück, und
            # bei Mastodon liest es niemand zweimal.
            alt = ablage.frueherer_text(projekt.id, str(produkt["adresse"]))
            frueher = {n: alt[n] for n in netze if n in alt} or None

            angelegt.append(
                _ein_beitrag(ablage, projekt, produkt, termin, grund, netze,
                             kampagne.thema, frueher)
            )
        except Exception as fehler:  # noqa: BLE001
            # Einzeln scheitern lassen: Acht Beiträge statt zehn sind
            # brauchbar, ein Abbruch nach dem dritten nicht.
            gescheitert.append({"titel": produkt["titel"],
                                "adresse": produkt["adresse"],
                                "grund": str(fehler)[:300]})
            sagen(f"   gescheitert: {fehler}")

    schritt(len(gewaehlt), len(gewaehlt), "fertig")
    return _bericht(angelegt, unklar, None, gescheitert, weggeraeumt)


def _ein_beitrag(ablage, projekt, produkt, termin, grund, netze, thema,
                 frueher=None):
    seite = _auslesen(projekt, produkt)

    nummer, _ = ablage.inhalt_merken(
        projekt.id, seite["fremd_id"], seite["titel"], seite["adresse"],
        str(seite.get("text", "")), seite.get("bild_adresse"),
    )

    zusatz = f"Diese Woche steht unter dem Thema: {thema}." if thema else ""
    # Was der Betreiber auf frühere Rückfragen geantwortet hat, geht mit:
    # allgemein Geltendes immer, Produktwissen nur zu dieser Adresse.
    wissen = [dict(z) for z in ablage.wissen(projekt.id, str(seite["adresse"]))]
    art = (denker.BLOG if getattr(projekt, "art", "") == "wordpress"
           else denker.PRODUKT)
    fassungen = denker.schreiben(seite, netze, projekt.name, zusatz,
                                 frueher=frueher, wissen=wissen, art=art)

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


def _auslesen(projekt, produkt) -> dict[str, Any]:
    """Holt den ganzen Inhalt – über die Schnittstelle, wo es eine gibt.

    Bei einem Blog ist der Weg über die Schnittstelle besser als der über die
    Seite: WordPress liefert den Text ohne Menü, Fußzeile und Beiwerk, dazu
    das gepflegte Beitragsbild und das Datum. Aus dem HTML derselben Seite
    müsste man all das erst wieder herausschneiden.

    Fehlt die Kennung - etwa bei einem alten Entwurf aus der Zeit vor dem
    2026-09-05 -, wird die Seite gelesen wie bei einem Shop. Lieber ein
    schlechterer Text als ein Abbruch.
    """
    if getattr(projekt, "art", "") == "wordpress" and produkt.get("fremd_id"):
        stamm = wordpress.rest_adresse_von(projekt)
        return wordpress.beitrag(stamm, str(produkt["fremd_id"]))
    return seitenkarte.seite(produkt["adresse"])


def _kategoriename(adresse: str) -> str:
    teile = [t for t in adresse.split("/") if t and t != "list.html"]
    return teile[-1] if teile else adresse


def _zuruecknehmen(ablage, angelegt: list[dict[str, Any]], sagen) -> int:
    """Nimmt zurück, was ein abgebrochener Lauf schon angelegt hat.

    **Sonst wäre »abbrechen« nur »aufhören«.** Die schon angelegten Beiträge
    blieben stehen, und ihre Produkte gälten über die Vier-Wochen-Regel als
    beworben, obwohl nie etwas erschienen ist - die nächste Wochenplanung
    fände sie nicht mehr, ohne dass jemand wüsste, warum.

    Der Inhalt geht mit, wenn kein anderer Beitrag daran hängt; darum kümmert
    sich `beitrag_entfernen`. Veröffentlichtes bleibt stehen: In einem frisch
    abgebrochenen Lauf gibt es davon zwar nichts, aber die Regel wird hier
    nicht zur Ausnahme gemacht.
    """
    from .ablage import HandarbeitWuerdeVerloren

    entfernt = 0
    for eintrag in angelegt:
        try:
            ablage.beitrag_entfernen(int(eintrag["id"]))
            entfernt += 1
        except (KeyError, HandarbeitWuerdeVerloren) as fehler:
            sagen(f"   bleibt stehen: {fehler}")
    if entfernt:
        sagen(f"{entfernt} angefangene Entwürfe wieder entfernt.")
    return entfernt


def _bericht(angelegt, unklar, hinweis=None, gescheitert=None,
             weggeraeumt=None, abgebrochen: bool = False,
             entfernt: int = 0) -> dict[str, Any]:
    return {
        "angelegt": angelegt,
        "anzahl": len(angelegt),
        "gescheitert": gescheitert or [],
        # Was sich keinem Hersteller zuordnen ließ, wird genannt und nicht
        # verschwiegen: Sonst fehlen in einer Herstellerwoche zwei Türen, und
        # niemand erfährt, warum.
        "nicht_zugeordnet": [u["titel"] for u in unklar],
        "weggeraeumt": weggeraeumt or [],
        # Ein Abbruch ist kein leeres Ergebnis: Die Oberfläche soll sagen
        # können, dass abgebrochen *und* aufgeräumt wurde.
        "abgebrochen": abgebrochen,
        "entfernt": entfernt,
        "hinweis": hinweis,
    }
