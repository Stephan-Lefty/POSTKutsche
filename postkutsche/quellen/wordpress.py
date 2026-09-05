"""Beiträge aus WordPress über die REST-Schnittstelle.

Zwei Dinge sind hier nicht selbstverständlich, beide am 2026-08-28 an den
echten Seiten aufgefallen:

**Beitragsbilder gibt es nicht immer.** Auf blog.example steht bei jedem Beitrag
`featured_media: 0` – trotzdem hat jeder Beitrag ein Bild, nämlich im Text und
in der og:image-Angabe. Wer sich auf `wp:featuredmedia` verlässt, bekommt für
diese Seite nie ein Bild und kann nie auf Instagram veröffentlichen. Deshalb
drei Stufen: Beitragsbild, erstes Bild im Text, og:image der Seite.

**Zweisprachige Seiten liefern jeden Beitrag doppelt.** blog.example hat zu
jedem deutschen Beitrag einen englischen unter `/en/`, auf die Sekunde gleich
datiert. Ohne Filter stünde jeder Beitrag zweimal im Kalender und ginge zweimal
raus. Es ist kein WPML und kein Polylang installiert – die Übersetzungen sind
eigene Beiträge, erkennbar allein an der Adresse.

Seit dem 2026-09-05 dient dieses Modul zwei Zwecken. `beitraege` holt die
neuesten für den täglichen Abgleich; `kategorien`, `beitragsliste` und
`beitrag` bedienen die Wochenplanung, in der ein Blog genauso gewählt wird wie
ein Shop. Der Unterschied liegt im Zuschnitt, nicht im Ergebnis: Für die
Planung werden erst nur Titel und Adresse geholt und der ganze Beitrag erst
für die sieben, die wirklich drankommen. Wer für vierzig Beiträge sofort
alles holt, löst vierzig Bildabrufe aus, um sieben davon zu benutzen.
"""

from __future__ import annotations

from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .abrufen import (
    AbrufFehler,
    entmarken,
    erstes_bild,
    json_holen,
    kopfzeile_holen,
    og_angaben,
    text_holen,
)


def beitraege(
    rest_adresse: str,
    anzahl: int = 20,
    ausschliessen: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Die neuesten Beiträge, aufbereitet.

    `ausschliessen` sind Bruchstücke von Adressen, die übergangen werden –
    für blog.example steht dort `["/en/"]`.
    """
    adresse = (
        f"{rest_adresse.rstrip('/')}/posts"
        f"?per_page={min(anzahl, 100)}&_embed=1&orderby=date&order=desc"
    )
    rohdaten = json_holen(adresse)
    if not isinstance(rohdaten, list):
        raise AbrufFehler(
            f"{adresse} liefert keine Liste von Beiträgen. "
            "Ist das wirklich eine WordPress-Schnittstelle?"
        )

    muster = ausschliessen or []
    for eintrag in rohdaten:
        verweis = eintrag.get("link", "")
        if any(stueck in verweis for stueck in muster):
            continue
        yield _aufbereiten(eintrag)


#: Ab so vielen Kategorien lohnt der Eintrag »Alle Beiträge«. Bei genau einer
#: wäre er eine Dublette: DialOS führt alle 16 Beiträge unter »Allgemein«, und
#: zwei Zeilen, die dasselbe tun, sind keine Auswahl, sondern eine Stolperfalle.
_ALLE_AB = 2


def kategorien(rest_adresse: str, alle_ab: int = _ALLE_AB,
               ausschliessen: list[str] | None = None) -> list[dict[str, Any]]:
    """Die Kategorien eines Blogs, in der Form, die das Planungsfenster erwartet.

    Ein Blog hat seine Gliederung selbst und muss dafür nicht durchsucht
    werden – ein Abruf, keine 130 wie bei einem Shop ohne Schnittstelle.
    Deshalb gibt es hier auch keinen Zwischenspeicher.

    **Leere Kategorien kommen nicht mit.** Naturlust führt ein »Allgemein« mit
    null Beiträgen; wer es wählt, plant eine Woche, die keine Beiträge findet,
    und sucht den Fehler dann bei uns.

    **Mit `ausschliessen` wird nachgezählt.** WordPress zählt alles, was in der
    Kategorie steht – bei einem zweisprachigen Blog also auch die englischen
    Fassungen. DialOS meldet so 16 Beiträge, planbar sind acht. Wer daraufhin
    zwei Beiträge am Tag plant, bekommt eine halb leere Woche und erfährt den
    Grund nicht. Das kostet mindestens einen Abruf je Kategorie – bei mehr als
    hundert Beiträgen auch zwei – und geschieht nur, wo ein Filter eingetragen
    ist.

    Sortiert wird nach Anzahl, die größte zuerst: Wer eine Woche füllen will,
    braucht Vorrat, und die Kategorie mit 44 Beiträgen ist der wahrscheinlichere
    Griff als die mit vier.
    """
    stamm = rest_adresse.rstrip("/")
    roh = json_holen(f"{stamm}/categories?per_page=100&orderby=count&order=desc")
    if not isinstance(roh, list):
        raise AbrufFehler(
            f"{stamm}/categories liefert keine Liste. "
            "Ist das wirklich eine WordPress-Schnittstelle?"
        )

    gefunden: list[dict[str, Any]] = []
    for eintrag in roh:
        if not isinstance(eintrag, dict):
            continue
        anzahl = int(eintrag.get("count") or 0)
        if anzahl <= 0:
            continue
        nummer = eintrag.get("id")
        gefunden.append({
            "adresse": f"{stamm}/posts?categories={nummer}",
            # Ein Pfad mit gemeinsamem ersten Stück: Die Oberfläche baut aus
            # dem ersten Teil die Bereichsauswahl, und ein Blog hat nur einen.
            "pfad": f"blog/{eintrag.get('slug') or nummer}",
            "tiefe": 1,
            "name": entmarken(str(eintrag.get("name") or f"Kategorie {nummer}")),
            "nummer": nummer,
            "produkte": anzahl,
            "fehler": None,
        })

    if ausschliessen:
        for eintrag in gefunden:
            eintrag["produkte"] = _planbare(str(eintrag["adresse"]),
                                            int(eintrag["produkte"]),
                                            ausschliessen)
        gefunden = [k for k in gefunden if int(k["produkte"]) > 0]

    gefunden.sort(key=lambda k: (-int(k["produkte"]), str(k["name"])))

    if len(gefunden) >= alle_ab or not gefunden:
        gefunden.insert(0, {
            "adresse": f"{stamm}/posts",
            "pfad": "blog/alle",
            "tiefe": 1,
            "name": "Alle Beiträge",
            "nummer": None,
            # Mit Filter wird nachgezählt, ohne genügt die Kopfzeile. Der
            # Rückfall ist in beiden Fällen derselbe: Scheitert das Zählen,
            # steht dort die größte Kategorie. Eine 0 wäre schlimmer als eine
            # zu kleine Zahl - die Oberfläche blendet aus, was null meldet,
            # und »Alle Beiträge« verschwände genau dann aus der Auswahl, wenn
            # der Blog gerade klemmt.
            "produkte": (_planbare(f"{stamm}/posts",
                                   _groesste(gefunden), ausschliessen)
                         if ausschliessen else _gesamtzahl(stamm, gefunden)),
            "fehler": None,
        })
    return gefunden


def _planbare(adresse: str, gemeldet: int, ausschliessen: list[str]) -> int:
    """Wie viele Beiträge nach dem Sprachfilter übrig bleiben.

    Gezählt wird, indem die Liste geholt wird – anders geht es nicht, denn der
    Filter greift an der Adresse und nicht an einem Feld, nach dem WordPress
    suchen könnte. Scheitert der Abruf, bleibt die gemeldete Zahl stehen: eine
    zu hohe Zahl ist besser als eine Kategorie, die aus der Auswahl fällt.

    **Bei hundert ist Schluss.** Mehr zu zählen kostet weitere Abrufe für eine
    Zahl, die niemand braucht: Geplant wird eine Woche, und schon vierzig
    Beiträge in einer Kategorie sind mehr Auswahl, als eine Woche verlangt. Ein
    Blog mit mehr planbaren Beiträgen zeigt deshalb 100 an.
    """
    try:
        return len(beitragsliste(adresse, _JE_SEITE, ausschliessen))
    except AbrufFehler:
        return gemeldet


def _groesste(kategorien: list[dict[str, Any]]) -> int:
    """Die größte Kategorie – die ehrlichste Untergrenze für den ganzen Blog."""
    return max((int(k["produkte"]) for k in kategorien), default=0)


def _gesamtzahl(stamm: str, kategorien: list[dict[str, Any]]) -> int:
    """Wie viele Beiträge der Blog insgesamt führt.

    **Nicht die Summe der Kategorien.** Ein Beitrag steht oft in mehreren und
    zählt dann mehrfach: Naturlust käme so auf 98 statt 52. WordPress sagt die
    richtige Zahl im Kopf der Antwort. Schweigt es, ist die größte Kategorie
    die ehrlichere Schätzung als eine Summe, die zu hoch ist - so viele sind
    es mindestens.
    """
    gemeldet = kopfzeile_holen(f"{stamm}/posts?per_page=1", "X-WP-Total")
    try:
        if gemeldet is not None:
            return int(gemeldet)
    except ValueError:
        pass
    return _groesste(kategorien)


#: Wie viele Beiträge je Abfrage. WordPress lässt höchstens 100 zu.
_JE_SEITE = 100


def beitragsliste(kategorie_adresse: str, grenze: int = 40,
                  ausschliessen: list[str] | None = None) -> list[dict[str, Any]]:
    """Titel und Adresse der Beiträge einer Kategorie – mehr noch nicht.

    `kategorie_adresse` ist, was `kategorien` unter »adresse« geliefert hat:
    eine fertige REST-Abfrage auf `/posts`, mit oder ohne `categories=`.

    Ohne `_embed`, und das ist der Punkt: Diese Liste dient dem Streuen und
    der Wiederholungsprüfung. Der ganze Beitrag mit Bild wird erst geholt,
    wenn feststeht, dass er auch drankommt.

    Die Reihenfolge ist die von WordPress – neueste zuerst. Sie bleibt
    erhalten, damit ein frisch erschienener Beitrag vorn steht und nicht im
    Alphabet verschwindet.
    """
    muster = ausschliessen or []
    # Reichlich holen und selbst zählen: Was der Sprachfilter aussortiert,
    # zieht sonst die Ausbeute unter die Grenze, ohne dass jemand nachlegt.
    je_seite = min(max(grenze, 20), _JE_SEITE)

    gefunden: list[dict[str, Any]] = []
    seite = 1
    while len(gefunden) < grenze:
        adresse = _mit_werten(kategorie_adresse, {
            "per_page": str(je_seite),
            "page": str(seite),
            "orderby": "date",
            "order": "desc",
            "_fields": "id,link,title",
        })
        roh = json_holen(adresse)
        if not isinstance(roh, list):
            raise AbrufFehler(
                f"{adresse} liefert keine Liste von Beiträgen. "
                "Ist das wirklich eine WordPress-Schnittstelle?"
            )
        if not roh:
            break

        for eintrag in roh:
            verweis = str(eintrag.get("link", ""))
            if any(stueck in verweis for stueck in muster):
                continue
            gefunden.append({
                "fremd_id": str(eintrag.get("id", "")),
                "titel": entmarken(_gerendert(eintrag, "title")),
                "adresse": verweis,
            })
            if len(gefunden) >= grenze:
                break

        if len(roh) < je_seite:
            break  # das war die letzte Seite
        seite += 1

    return gefunden


def beitrag(rest_adresse: str, fremd_id: str) -> dict[str, Any]:
    """Ein einzelner Beitrag, vollständig – wie ihn `beitraege` liefern würde.

    Gibt dieselben Felder zurück wie `seitenkarte.seite`, damit die
    Wochenplanung nicht wissen muss, woher ein Beitrag kommt.
    """
    stamm = rest_adresse.rstrip("/")
    roh = json_holen(f"{stamm}/posts/{fremd_id}?_embed=1")
    if not isinstance(roh, dict) or not roh.get("id"):
        raise AbrufFehler(
            f"{stamm}/posts/{fremd_id} liefert keinen Beitrag."
        )
    return _aufbereiten(roh)


def rest_adresse_von(projekt: Any) -> str:
    """Wo die Schnittstelle eines Projekts liegt.

    Steht sie nicht in den Einstellungen, wird sie an der üblichen Stelle
    vermutet – jede WordPress-Installation legt sie dorthin.
    """
    eingetragen = (projekt.einstellungen or {}).get("rest")
    if eingetragen:
        return str(eingetragen)
    return f"{str(projekt.adresse).rstrip('/')}/wp-json/wp/v2"


def _mit_werten(adresse: str, werte: dict[str, str]) -> str:
    """Setzt Abfragewerte, ohne vorhandene zu verlieren.

    »?categories=9« muss stehen bleiben, wenn »per_page« dazukommt – sonst
    plant man aus Versehen den ganzen Blog statt einer Kategorie.
    """
    teile = urlsplit(adresse)
    vorhanden = dict(parse_qsl(teile.query))
    vorhanden.update(werte)
    return urlunsplit(teile._replace(query=urlencode(vorhanden)))


#: Wie viel Text an Claude geht. Gemessen am 2026-09-05: Blogbeiträge reichen
#: bis 15.200 Zeichen, der Mittelwert liegt bei 5.600. Alles mitzuschicken
#: bläht die Anweisung auf das Vierfache, ohne dass ein Beitrag für Facebook
#: davon besser würde - worum es geht, steht am Anfang. Dieselbe Grenze wie
#: bei den Shopseiten, aus demselben Grund.
TEXTGRENZE = 4000


def _kuerzen(text: str, grenze: int = TEXTGRENZE) -> str:
    """Kürzt auf ganze Absätze.

    **Nie mitten im Wort.** Ein hart abgeschnittener Text hat am 2026-08-31
    reihenweise Rückfragen ausgelöst - Claude meldete zu Recht, der Quelltext
    breche mitten im Satz ab, und der Beitrag blieb liegen.

    Der erste Absatz kommt immer mit, auch wenn er allein schon zu lang ist:
    Ein leerer Text wäre schlechter als ein zu langer.
    """
    if len(text) <= grenze:
        return text

    stuecke: list[str] = []
    laenge = 0
    for absatz in text.split("\n\n"):
        if stuecke and laenge + len(absatz) > grenze:
            break
        stuecke.append(absatz)
        laenge += len(absatz) + 2
    return "\n\n".join(stuecke)


def _aufbereiten(eintrag: dict[str, Any]) -> dict[str, Any]:
    inhalt_roh = _gerendert(eintrag, "content")
    return {
        "fremd_id": str(eintrag.get("id", "")),
        "titel": entmarken(_gerendert(eintrag, "title")),
        "text": _kuerzen(entmarken(inhalt_roh)),
        "adresse": eintrag.get("link", ""),
        "bild_adresse": _bild(eintrag, inhalt_roh),
        "veroeffentlicht": _zeitpunkt(eintrag),
        "kategorien": _kategorien(eintrag),
    }


def _gerendert(eintrag: dict[str, Any], feld: str) -> str:
    """WordPress verpackt Text als {"rendered": "…"} – manchmal auch nicht."""
    wert = eintrag.get(feld)
    if isinstance(wert, dict):
        return str(wert.get("rendered", ""))
    return str(wert or "")


def _bild(eintrag: dict[str, Any], inhalt_roh: str) -> str | None:
    """Das Bild zum Beitrag, in drei Stufen.

    Die Reihenfolge ist nach Qualität sortiert: Ein gepflegtes Beitragsbild ist
    für die Vorschau gedacht und hat das richtige Format. Ein Bild aus dem Text
    kann alles sein. og:image ist der letzte Halt.
    """
    medien = (eintrag.get("_embedded") or {}).get("wp:featuredmedia") or []
    for medium in medien:
        # Fehlt das Bild oder darf es nicht gelesen werden, steht hier ein
        # Fehlerobjekt statt eines Mediums.
        if isinstance(medium, dict) and medium.get("source_url"):
            return str(medium["source_url"])

    im_text = erstes_bild(inhalt_roh)
    if im_text:
        return im_text

    verweis = eintrag.get("link")
    if not verweis:
        return None
    try:
        angaben = og_angaben(text_holen(verweis))
    except AbrufFehler:
        # Kein Bild ist ärgerlich, aber kein Grund, den ganzen Abruf
        # abzubrechen. Der Kalender zeigt dann eine Warnung.
        return None
    return angaben.get("image") or None


def _zeitpunkt(eintrag: dict[str, Any]) -> str | None:
    """Der Veröffentlichungszeitpunkt in UTC.

    WordPress liefert `date_gmt` ohne Zonenkennzeichen – »2026-08-27T15:00:00«
    ist bereits UTC, sieht aber aus wie Ortszeit. Wer das übersieht, verschiebt
    jeden Beitrag um ein bis zwei Stunden.
    """
    roh = eintrag.get("date_gmt")
    if not roh:
        return None
    text = str(roh)
    return text if text.endswith("Z") else f"{text}Z"


def _kategorien(eintrag: dict[str, Any]) -> list[str]:
    """Kategorien und Schlagwörter – hilft Claude beim Ton."""
    namen: list[str] = []
    for gruppe in (eintrag.get("_embedded") or {}).get("wp:term") or []:
        if not isinstance(gruppe, list):
            continue
        for begriff in gruppe:
            if isinstance(begriff, dict) and begriff.get("name"):
                namen.append(str(begriff["name"]))
    return namen
