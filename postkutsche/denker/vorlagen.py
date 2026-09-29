"""Was Claude gesagt bekommt, damit brauchbare Beiträge herauskommen.

Die Anweisung ist der eigentliche Kern der Anbindung. Ein Aufruf mit »schreib
mir einen Beitrag« liefert Werbesprache mit Ausrufezeichen; was hier steht,
ist der Unterschied zwischen einem Text, den man freigeben kann, und einem,
den man neu schreibt.

Drei Dinge sind dabei nicht verhandelbar:

**Keine Preise.** Ein Preis ändert sich, der Beitrag bleibt stehen - aus einem
alten Beitrag wird dann schnell der Vorwurf, mit falschen Preisen geworben zu
haben.

**Rückfragen statt Erfindungen.** Wo etwas unklar ist, soll Claude fragen und
nicht raten. Ein erfundenes Detail in einem Beitrag über Brandschutztüren ist
schlimmer als ein Beitrag, der einen Tag später erscheint.

**Je Netzwerk anders.** Ein Mastodon-Beitrag hat 500 Zeichen, LinkedIn klappt
nach dem ersten Satz zu, bei Instagram ist kein Verweis anklickbar. Dieselbe
Meldung viermal einzufügen führt dazu, dass sie dreimal nicht passt.
"""

from __future__ import annotations

import json
from typing import Any

from .. import netzwerke

# Das Ausgabeformat. Knapp gehalten und ohne Verschachtelung: Je mehr Struktur
# man verlangt, desto häufiger kommt etwas zurück, das fast passt.
FORMAT = """{
  "fassungen": {
    "<netzwerk>": {
      "text": "der fertige Beitragstext",
      "schlagworte": ["ohne", "raute"],
      "rueckfrage": null
    }
  }
}"""

GRUNDREGELN = """\
So schreibst du:

- Deutsch, in ganzen Sätzen, sachlich. Kein Werbesprech, keine Superlative,
  höchstens ein Ausrufezeichen im ganzen Text - besser keines.
- Der erste Satz muss allein tragen. Auf dem Handy sieht man oft nur ihn.
- Kurze Absätze mit Leerzeile dazwischen. Ein Block aus acht Zeilen wird
  auf einem Telefon nicht gelesen.
- Keine Überschrift in Großbuchstaben, keine Rahmen aus Sonderzeichen.
- Keine Markdown-Auszeichnung: kein **fett**, kein # und keine [Verweise](…).
  Die Netzwerke stellen das nicht dar, es erscheint als Zeichensalat.
- Emojis sparsam, höchstens eines, und nur wenn es etwas beiträgt.
- **Schreib die Adresse des Artikels nicht in den Text.** Sie wird beim
  Veröffentlichen angehängt, je Netzwerk an der richtigen Stelle. Wer sie
  mitschreibt, hat sie am Ende zweimal drin - genau das ist am 2026-08-28 in
  einem echten Beitrag passiert.
- Schlagwörter sind eine Obergrenze, kein Ziel. Nimm so wenige wie möglich.
  Eines, das trifft, ist besser als vier, die ungefähr passen.

Was du nicht tust:

- Keine Preise nennen, auch keine ungefähren. Sie ändern sich, der Beitrag
  bleibt stehen.
- **Nichts zu Garantie oder Gewährleistung.** Keine Dauer, keine Bedingungen,
  keine Einschränkungen - auch dann nicht, wenn es im Quelltext steht. Das
  sind Zusagen mit rechtlicher Wirkung; sie ändern sich, und ein zwei Jahre
  alter Beitrag mit überholten Bedingungen wird zum Vorwurf. Wer sie wissen
  will, findet sie im Shop.
- Nichts erfinden. Was nicht im Quelltext steht, steht nicht im Beitrag -
  keine Maße, keine Normen, keine Eigenschaften, keine Jahreszahlen.
- Keine Versprechen zu Verfügbarkeit oder Eignung für einen bestimmten Zweck.
- Zur Lieferzeit sagst du nur das, was der Betreiber dir ausdrücklich
  vorgegeben hat - er kennt seine Ware. Ohne eine solche Vorgabe schweigst du
  darüber, auch wenn im Quelltext eine Frist steht. Das ist die einzige
  Ausnahme dieser Art: Bei allem anderen gilt die Regel, nicht der Quelltext.

Wenn du unsicher bist:

Schreib deine Frage in »rueckfrage« und lass den Text trotzdem so gut wie
möglich stehen. Ein Beitrag mit offener Frage wird nicht veröffentlicht,
bevor jemand geantwortet hat - das ist besser als eine glatte Erfindung.
Frag zum Beispiel:

- wenn der Quelltext sich widerspricht oder mitten im Satz abbricht
- wenn eine Fachangabe unklar bleibt - ein Maß ohne Einheit, eine Norm
  ohne Nummer, eine Modellbezeichnung, die zweimal verschieden geschrieben ist
- wenn nicht zu erkennen ist, was das Beworbene eigentlich tut
- wenn für ein Netzwerk mit Bildpflicht kein Bild vorliegt
- wenn der Text eine Zusage enthält, die du nicht prüfen kannst

Ist alles klar, setz »rueckfrage« auf null. Eine erfundene Rückfrage ist so
schlecht wie ein erfundenes Detail.\
"""


#: Die beiden Sorten Quelle. »produkt« ist der Regelfall und bleibt die
#: Vorgabe: Was vorher gebaut wurde, verhält sich unverändert.
PRODUKT = "produkt"
BLOG = "blog"

BLOGREGELN = """\
Die Quelle ist ein Blogbeitrag, kein Artikel aus einem Sortiment. Deshalb
gelten hier zusätzlich diese Regeln:

- **Der Beitrag ist das Ziel, nicht die Ware.** Du wirbst nicht für etwas, das
  jemand kaufen soll, sondern gibst einen Grund, den Text zu lesen.
- **Erzähl nicht alles.** Ein Beitrag, der die Pointe schon im Netzwerk
  ausspricht, nimmt sich selbst den Anlass. Ein Gedanke reicht - der, der am
  meisten Neugier weckt. Aber kein Ködern mit leeren Versprechen: keine
  Formeln wie »du wirst nicht glauben« oder »das hätte ich nie gedacht«.
- **Der Quelltext hört mittendrin auf, und das ist in Ordnung.** Lange
  Beiträge werden gekürzt übergeben. Das ist kein Widerspruch und kein Grund
  für eine Rückfrage - schreib aus dem, was da ist.
- **Sag nicht, der Beitrag sei neu.** Es kommen auch ältere wieder an die
  Reihe. »Heute erschienen«, »frisch im Blog«, »gerade veröffentlicht« - nichts
  davon, es sei denn, das Datum unten sagt es ausdrücklich.
- Erzählt der Beitrag in der Ich-Form, darfst du das übernehmen; es ist das
  eigene Blog. Erfinde aber nichts Persönliches dazu - kein Erlebnis, keine
  Meinung, kein Gefühl, das nicht im Text steht.

Preise, Lieferzeiten und Garantiebedingungen kommen in einem Blogbeitrag
selten vor. Stehen sie doch einmal darin, gilt trotzdem, was oben steht: Sie
bleiben draußen.\
"""


def _netzwerkteil(kennung: str) -> str:
    netz = netzwerke.netzwerk(kennung)
    zeilen = [
        f"### {netz.name} (Schlüssel »{netz.kennung}«)",
        f"- Ziellänge etwa {netz.zeichen_ziel} Zeichen, {netz.zeichen_max} sind "
        f"die harte Grenze. Bleib darunter.",
        f"- Höchstens {netz.schlagworte_max} Schlagwörter, ohne Raute, "
        f"kleingeschrieben, einzeln im Feld »schlagworte«.",
        f"- {netz.hinweis}",
    ]
    if netz.bild_pflicht:
        zeilen.append(
            "- Ohne Bild geht hier nichts. Fehlt eines, gehört das in die "
            "Rückfrage."
        )
    return "\n".join(zeilen)


def _wissensteil(wissen: list[dict[str, Any]]) -> list[str]:
    """Was der Betreiber auf frühere Rückfragen geantwortet hat.

    **Der eigentliche Sinn der Sammlung.** Ohne diesen Abschnitt fragt Claude
    bei jedem Produkt derselben Art dasselbe, und der Betreiber beantwortet
    wöchentlich, dass die Lieferzeit nicht in den Text gehört.

    Der Ton ist derselbe wie bei der Nachbesserung: Das ist Auskunft vom
    Betreiber, sie gilt, und sie wird nicht ausgeschmückt. Ohne diesen Satz
    wird aus »T30-2 ist zweiflügelig« ein Absatz über die Vorzüge
    zweiflügeliger Türen – erfunden aus einer Auskunft, die nur einen
    Widerspruch klären sollte.
    """
    zeilen = [
        "",
        "## Was der Betreiber schon beantwortet hat",
        "",
        "Das steht hier, weil er es auf eine frühere Rückfrage geantwortet "
        "hat. Es gilt, und du prüfst es nicht nach.",
        "",
        "**Übernimm es sinngemäß, wenn es zum Text passt, und schmücke es "
        "nicht aus** - kein Wort mehr, als dort steht. Passt es nicht zu "
        "diesem Produkt, lass es weg. Frag auf keinen Fall noch einmal "
        "danach.",
        "",
    ]
    for eintrag in wissen:
        wofuer = ("für dieses Produkt" if eintrag.get("adresse")
                  else "für das ganze Projekt")
        frage = str(eintrag.get("frage") or "").strip()
        # Die Frage kommt mit, wo es eine gibt: Eine Antwort ohne ihre Frage
        # ist oft nicht zu deuten. »Ja, immer« sagt allein gar nichts.
        if frage:
            zeilen.append(f"- Auf »{frage}« ({wofuer}): {eintrag['antwort']}")
        else:
            zeilen.append(f"- ({wofuer}): {eintrag['antwort']}")
    return zeilen


def anweisung(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
    art: str = PRODUKT,
) -> str:
    """Baut die vollständige Anweisung für einen Beitrag.

    `inhalt` ist, was eine Quelle geliefert hat: titel, text, adresse,
    bild_adresse, kategorien. `fuer` sind die Netzwerkkennungen.

    `wissen` sind frühere Antworten des Betreibers auf Rückfragen - je
    Eintrag »frage«, »antwort« und »adresse«. Wer sie mitgibt, bekommt
    dieselbe Frage nicht zum vierten Mal gestellt.

    `art` ist `PRODUKT` oder `BLOG`. Ein Blogbeitrag wird anders beworben als
    eine Tür: Er soll gelesen werden, nicht gekauft, und er ist oft nicht von
    gestern. Beides muss dastehen, sonst schreibt Claude eine Inhaltsangabe
    und nennt einen Beitrag vom März »neu«.
    """
    if not fuer:
        raise ValueError("Ohne Netzwerk gibt es nichts zu schreiben.")

    quelle = [f"Titel: {inhalt.get('titel', '')}"]
    if inhalt.get("adresse"):
        quelle.append(f"Adresse: {inhalt['adresse']}")
    if inhalt.get("kategorien"):
        quelle.append(f"Themen: {', '.join(inhalt['kategorien'])}")
    # Das Datum nur, wo es eines gibt. Produktseiten haben keines, dem zu
    # trauen wäre; ein Blogbeitrag schon - und ohne das Datum kann Claude
    # nicht wissen, dass er einen halbjährigen Text vor sich hat.
    if inhalt.get("veroeffentlicht"):
        quelle.append(f"Erschienen am: {inhalt['veroeffentlicht']}")
    quelle.append(
        "Bild vorhanden: " + ("ja" if inhalt.get("bild_adresse") else "nein")
    )
    # Der Volltext wird gekürzt. Ein Blogbeitrag mit 14.000 Zeichen macht die
    # Anweisung teuer, ohne dass die letzten Absätze für einen 500-Zeichen-
    # Beitrag noch etwas beitragen.
    text = str(inhalt.get("text", "")).strip()
    if len(text) > 6000:
        text = text[:6000] + "\n[hier gekürzt]"
    quelle.append(f"\nInhalt:\n{text}")

    teile = [
        "Du schreibst Beiträge für soziale Netzwerke aus einem vorliegenden "
        "Text. Du erfindest nichts dazu.",
        "",
        f"## Die Quelle{f' (Projekt: {projekt})' if projekt else ''}",
        "",
        "\n".join(quelle),
        "",
        "## Für diese Netzwerke",
        "",
        "\n\n".join(_netzwerkteil(k) for k in fuer),
        "",
        "## Regeln",
        "",
        GRUNDREGELN,
    ]
    if art == BLOG:
        teile += ["", "## Was bei einem Blogbeitrag anders ist", "", BLOGREGELN]
    if frueher:
        # Der frühere Text kommt mit, damit der neue anders klingt. Facebook
        # und Instagram drosseln wortgleiche Wiederholungen - ein zweiter
        # Beitrag mit denselben Sätzen erreicht weniger als gar keiner.
        teile += [
            "",
            ("## Dieser Beitrag war schon einmal dran" if art == BLOG
             else "## Dieses Produkt war schon einmal dran"),
            "",
            "Unten steht, was damals veröffentlicht wurde. **Schreib etwas "
            "anderes.** Dieselbe Aussage, aber ein anderer Einstieg, ein "
            "anderer Blickwinkel, andere Sätze. Wortgleiche Wiederholungen "
            "werden von den Netzwerken zurückgehalten.",
            "",
            "Wechsle den Blickwinkel, statt Wörter zu tauschen: Ging es beim "
            "ersten Mal um die Eigenschaft, geht es jetzt um die Anwendung. "
            "Stand vorher der Einbau im Vordergrund, jetzt der Zweck.",
            "",
        ]
        for netz, alt in frueher.items():
            teile += [f"### Damals für {netzwerke.netzwerk(netz).name}", "", alt, ""]

    if wissen:
        teile += _wissensteil(wissen)

    if zusatz:
        teile += ["", "## Zusätzlich für diesen Beitrag", "", zusatz]
    teile += [
        "",
        "## Antwortformat",
        "",
        "Antworte ausschließlich mit JSON in genau dieser Form, ohne "
        "einleitenden Satz und ohne Code-Zaun:",
        "",
        FORMAT,
        "",
        "Es muss für jedes genannte Netzwerk ein Eintrag da sein, mit den "
        f"Schlüsseln: {', '.join(fuer)}.",
    ]
    return "\n".join(teile)


def antwort_lesen(roh: str, erwartet: list[str]) -> dict[str, dict[str, Any]]:
    """Liest die Antwort und prüft, ob sie brauchbar ist.

    Sprachmodelle setzen gern einen Satz davor oder packen das JSON in einen
    Code-Zaun, auch wenn man es ausdrücklich verbietet. Deshalb wird nicht
    stur geparst, sondern das JSON aus dem Text herausgeschnitten.
    """
    daten = _json_finden(roh)
    fassungen = daten.get("fassungen")
    if not isinstance(fassungen, dict):
        raise AntwortFehler(
            "In der Antwort steht kein Feld »fassungen«. "
            f"Anfang der Antwort: {roh[:160]!r}"
        )

    ergebnis: dict[str, dict[str, Any]] = {}
    for kennung in erwartet:
        eintrag = fassungen.get(kennung)
        if not isinstance(eintrag, dict):
            raise AntwortFehler(f"Für {kennung} fehlt eine Fassung.")
        text = str(eintrag.get("text", "")).strip()
        if not text:
            raise AntwortFehler(f"Die Fassung für {kennung} hat keinen Text.")

        netz = netzwerke.netzwerk(kennung)
        if len(text) > netz.zeichen_max:
            # Nicht selbst kürzen: Ein abgeschnittener Satz ist schlimmer als
            # ein Text, der neu geschrieben wird.
            raise AntwortFehler(
                f"Die Fassung für {kennung} hat {len(text)} Zeichen, "
                f"erlaubt sind {netz.zeichen_max}."
            )

        schlagworte = eintrag.get("schlagworte") or []
        if isinstance(schlagworte, str):
            schlagworte = schlagworte.split()
        schlagworte = [
            str(s).lstrip("#").strip().lower() for s in schlagworte if str(s).strip()
        ][: netz.schlagworte_max]

        rueckfrage = eintrag.get("rueckfrage")
        if rueckfrage is not None:
            rueckfrage = str(rueckfrage).strip() or None

        ergebnis[kennung] = {
            "text": text,
            "schlagworte": " ".join(schlagworte),
            "rueckfrage": rueckfrage,
        }
    return ergebnis


class AntwortFehler(Exception):
    """Die Antwort ließ sich nicht verwenden. Die Meldung ist für Menschen."""


def _json_finden(roh: str) -> dict[str, Any]:
    text = roh.strip()
    if text.startswith("```"):
        # Code-Zaun abtragen, mit oder ohne Sprachangabe.
        zeilen = text.splitlines()
        text = "\n".join(zeilen[1:-1] if zeilen[-1].startswith("```") else zeilen[1:])

    try:
        daten = json.loads(text)
    except json.JSONDecodeError:
        anfang, ende = text.find("{"), text.rfind("}")
        if anfang == -1 or ende <= anfang:
            raise AntwortFehler(
                f"Die Antwort enthält kein JSON. Anfang: {roh[:160]!r}"
            ) from None
        try:
            daten = json.loads(text[anfang : ende + 1])
        except json.JSONDecodeError as fehler:
            raise AntwortFehler(f"Die Antwort ist kein gültiges JSON: {fehler}") from fehler

    if not isinstance(daten, dict):
        raise AntwortFehler("Die Antwort ist kein JSON-Objekt.")
    return daten


def nachbesserung(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
) -> str:
    """Anweisung zum Nachbessern eines Textes mit der Antwort auf die Rückfrage.

    Der Unterschied zum Neuschreiben ist wesentlich: Der bisherige Text war
    nicht falsch, ihm fehlte eine Angabe. Wer neu schreiben lässt, bekommt
    einen anderen Text - womöglich einen schlechteren, und die Arbeit am
    ersten war umsonst. Deshalb bekommt Claude den alten Text mit und den
    Auftrag, ihn zu ergänzen statt zu ersetzen.
    """
    netz = netzwerke.netzwerk(netzwerk)
    teile = [
        "Du hast einen Beitrag geschrieben und dabei nachgefragt. Die Antwort "
        "liegt jetzt vor. Bessere den Text nach - ergänze ihn, schreib ihn "
        "nicht neu.",
        "",
        "## Der bisherige Text",
        "",
        bisher,
        "",
        "## Deine Rückfrage",
        "",
        frage,
        "",
        "## Die Antwort",
        "",
        antwort,
        "",
        "## Das Netzwerk",
        "",
        _netzwerkteil(netzwerk),
        "",
        "## Regeln",
        "",
        GRUNDREGELN,
        "",
        "## Zusätzlich",
        "",
        "- Behalte, was gut war. Ändere nur, was die Antwort betrifft.",
        "- Erfinde aus der Antwort nichts dazu. Steht dort »verstellt die "
        "Breite«, schreibst du das - nicht »verstellt die Breite stufenlos "
        "um bis zu 30 Zentimeter«.",
        "- Reicht die Antwort nicht aus, frag erneut. Lieber zweimal fragen "
        "als einmal raten.",
    ]
    if zusatz:
        teile += ["", zusatz]
    teile += [
        "",
        "## Antwortformat",
        "",
        "Antworte ausschließlich mit JSON, ohne einleitenden Satz und ohne "
        "Code-Zaun:",
        "",
        json.dumps({"fassungen": {netzwerk: {
            "text": "der nachgebesserte Text",
            "schlagworte": ["ohne", "raute"],
            "rueckfrage": None,
        }}}, indent=2, ensure_ascii=False),
    ]
    return "\n".join(teile)


# -- Die Wochenformate -----------------------------------------------------
#
# »Tipp der Woche« und »Produkt der Woche« brauchen mehr als Text: Sie füllen
# auch die Felder der Grafik. Deshalb ein eigener Weg statt eines Zusatzes zu
# `anweisung` - und weil eine der Grundregeln hier ausdrücklich *nicht* gilt.

#: Wie viele Merkmale die Produktkarte trägt und wie lang sie sein dürfen.
#: Beides ist keine Vorliebe, sondern Platz: Die Schriftgrößen der Grafik sind
#: auf vier einzeilige Merkmale ausgelegt. Ein fünftes oder ein umbrechendes
#: läuft unten aus der Karte heraus. Deshalb muss der Text passen, statt dass
#: die Grafik sich wehrt.
MERKMALE_ANZAHL = 4
MERKMAL_ZEICHEN = 42

#: Muss in beiden Wochenformaten dabeistehen.
#:
#: Die Grundregeln verlangen eine Rückfrage, wenn für ein Netzwerk mit
#: Bildpflicht kein Bild vorliegt - richtig im Regelfall, falsch hier: Aus
#: den Feldern, die gerade gefüllt werden, entsteht anschließend die Grafik,
#: und zwar für jedes Netzwerk. Beim ersten echten Durchlauf am 2026-09-29
#: fragte Instagram prompt nach einem Bild. Eine offene Rückfrage sperrt die
#: Freigabe - das wäre jede Woche passiert.
BILD_ENTSTEHT = """\
**Zum Bild frag nicht.** Aus den Feldern unter »grafik« wird anschließend
eine Grafik gezeichnet, für jedes Netzwerk und im passenden Format. Es liegt
also für alle ein Bild vor, auch für Instagram. Schreib deshalb nichts über
fehlende Bilder in »rueckfrage« und fordere keines an.\
"""

WOCHE_FORMAT = """{
  "grafik": { … siehe unten … },
  "fassungen": {
    "<netzwerk>": {
      "text": "der fertige Beitragstext",
      "schlagworte": ["ohne", "raute"],
      "rueckfrage": null
    }
  }
}"""

PRODUKTREGELN = f"""\
Dies ist das »Produkt der Woche«. Zwei Dinge gelten hier anders als sonst:

- **Der Preis gehört hinein**, in den Text wie in die Grafik. Er ist der
  Anlass des Beitrags. Sonst gilt die Regel, keine Preise zu nennen, weil ein
  Beitrag stehenbleibt und ein Preis sich ändert - hier steht dabei, bis wann
  das Angebot gilt, und damit erledigt sich der Einwand.
- **Du nennst nur den Preis, den du bekommen hast.** Rechne nichts aus, runde
  nicht, und übernimm keine Zahl aus dem Fließtext des Artikels. Auf einer
  Produktseite stehen Preise fremder Artikel aus Empfehlungslisten daneben;
  einer davon wäre in einer Anzeige ein teurer Fehler.

Zusätzlich zu den Fassungen füllst du »grafik«:

  "grafik": {{
    "unterzeile": "Bodentreppe – Jetzt zugreifen!",
    "name": "kurzer Produktname, höchstens 30 Zeichen",
    "merkmale": ["…", "…", "…", "…"]
  }}

Für die Grafik gilt:

- **Genau {MERKMALE_ANZAHL} Merkmale, je höchstens {MERKMAL_ZEICHEN} Zeichen.**
  Das ist kein Richtwert: Die Karte hat Platz für vier einzeilige Zeilen. Was
  länger ist, bricht um und läuft unten heraus. Kürze lieber hart - »U-Wert
  0,7 W/m²K, 6 cm Steinwolle« statt eines ganzen Satzes.
- Keine Satzzeichen am Ende, keine ganzen Sätze. Es sind Stichpunkte.
- Die wichtigsten vier, nicht die ersten vier. Was das Stück von anderen
  unterscheidet, gehört nach oben.
- Der »name« ist der Produktname ohne Werbezusätze: Hersteller und
  Typbezeichnung, sonst nichts. Nicht der Seitentitel - der ist meist ein
  ganzer Werbesatz.
- Die »unterzeile« nennt die Warengattung und einen kurzen Aufruf.\
"""

TIPPREGELN = """\
Dies ist der »Tipp der Woche«: ein Ratschlag, keine Werbung. Du verkaufst
nichts, du erklärst etwas - und am Ende weiß der Leser, was er an diesem
Wochenende tun kann.

Zusätzlich zu den Fassungen füllst du »grafik«:

  "grafik": {
    "titel": "AUSSENTÜREN IM HERBST",
    "unterzeile": "RICHTIG PFLEGEN",
    "vorspann": "zwei Sätze, worum es geht",
    "warum": "ein Satz: warum gerade jetzt",
    "bloecke": [
      {"titel": "DICHTUNGEN\\nUND SCHWELLE", "unter": "Der wichtigste Punkt",
       "punkte": ["…", "…", "…", "…"]},
      … genau drei …
    ],
    "beachten": ["…", "…", "…", "…"],
    "wissen": "ein bis zwei Sätze, die überraschen",
    "cta": "JETZT BERATEN LASSEN & PASSENDE TÜR FINDEN!"
  }

Für die Grafik gilt:

- **Genau drei Blöcke mit je vier Punkten.** Weniger wirkt dünn, mehr passt
  nicht auf die Fläche.
- Blocktitel in Großbuchstaben, zweizeilig mit »\\n« getrennt, je Zeile
  höchstens 14 Zeichen. »unter« ist eine knappe Einordnung, keine
  Zusammenfassung.
- Die Punkte sind Anweisungen, höchstens 80 Zeichen. Was zu tun ist, nicht
  was gut wäre. Ein einzelnes Wort darf mit <b>…</b> hervorgehoben werden -
  aber höchstens eines im ganzen Block, sonst trägt es nichts mehr.
- »titel« und »unterzeile« sind Großbuchstaben, zusammen höchstens 40
  Zeichen. Die Unterzeile erscheint in Gold.
- Unter »beachten« stehen vier Warnungen: was schiefgeht, wenn man es falsch
  macht. Wenn es um Bauteile mit Zulassung geht (Brandschutz, Rauchschutz),
  gehört ein Hinweis dazu, dass daran nichts verändert werden darf.
- »wissen« ist der Punkt, den auch ein Fachmann nicht auf dem Schirm hat.
  Keine Wiederholung aus den Blöcken.

Für die Texte gilt zusätzlich: Der stärkste Aufhänger ist der verbreitete
Fehler - das, was viele gut gemeint falsch machen. Damit beginnst du, nicht
mit einer Aufzählung.

Dazu füllst du »seite« – denselben Tipp, aber ausführlich für eine Webseite:

  "seite": {
    "titel": "Außentüren im Herbst: die halbe Stunde, die den Winter rettet",
    "beschreibung": "ein Satz für Google, höchstens 150 Zeichen",
    "kurz": "ein Satz fürs Archiv der Vorwochen",
    "absaetze": [
      "Ein Absatz, der beim Alltag anfängt und nicht bei der Technik.",
      {"ueber": "Eine Zwischenüberschrift"},
      "Weitere Absätze …"
    ]
  }

Für die Seite gilt:

- **Fünf bis acht Absätze, davon zwei bis drei Zwischenüberschriften.** Das
  ist der Text, den man jemandem am Telefon erklären würde – mit
  Vorgeschichte, einer Anleitung zum Nachmachen und dem Hinweis, wann es
  nicht mehr selbst zu machen ist.
- Der erste Absatz beginnt bei dem, was jemand bemerkt – »es zieht am Boden«,
  »die Matte ist morgens feucht« –, nicht bei der Bauteilbezeichnung.
- Eine Handlungsanweisung, die man wirklich ausführen kann: mit Werkzeug,
  Reihenfolge und einem Merkmal, an dem man erkennt, ob es geklappt hat.
- **Ein Absatz sagt, wo Selbermachen aufhört.** Bei Brand- und
  Rauchschutztüren, bei Zulassungen, bei allem, was an der Statik hängt.
- `<strong>` und `<em>` sind erlaubt, sonst keine Auszeichnung, keine
  Verweise. Der Titel ist eine Aussage, keine Überschrift aus Stichworten.
- Der Titel der Seite darf länger und griffiger sein als der auf der Grafik –
  dort zählen Zeichen, hier zählt, ob jemand weiterliest.
"""


def wochenanweisung(
    art: str,
    quelle: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    wissen: list[dict[str, Any]] | None = None,
) -> str:
    """Die Anweisung für ein Wochenformat – Text und Grafikfelder in einem.

    `art` ist »produkt« oder »tipp«. Bei »produkt« steht in `quelle`, was die
    Produktseite hergab, samt Preis; bei »tipp« nur das Thema.
    """
    if not fuer:
        raise ValueError("Ohne Netzwerk gibt es nichts zu schreiben.")

    angaben = []
    if art == "produkt":
        angaben.append(f"Titel der Seite: {quelle.get('titel', '')}")
        angaben.append(f"Adresse: {quelle.get('adresse', '')}")
        preis = quelle.get("preis") or {}
        angaben.append(f"Preis: {preis.get('jetzt', '– nicht bekannt –')}")
        if preis.get("vorher"):
            angaben.append(f"Früherer Preis: {preis['vorher']}")
        angaben.append(f"Angebot läuft bis: {quelle.get('gueltig', '')}")
        if quelle.get("merkmale"):
            angaben.append("Merkmale laut Seite:\n- " +
                           "\n- ".join(quelle["merkmale"]))
        text = str(quelle.get("text", "")).strip()
        if len(text) > 6000:
            text = text[:6000] + "\n[hier gekürzt]"
        angaben.append(f"\nText der Seite:\n{text}")
    else:
        angaben.append(f"Thema: {quelle.get('thema', '')}")
        if quelle.get("hinweise"):
            angaben.append(f"Vorgaben: {quelle['hinweise']}")

    teile = [
        "Du schreibst einen wöchentlich erscheinenden Beitrag für soziale "
        "Netzwerke und füllst dazu die Felder einer Grafik. Du erfindest "
        "nichts dazu.",
        "",
        f"## Die Quelle{f' (Projekt: {projekt})' if projekt else ''}",
        "",
        "\n".join(angaben),
        "",
        "## Für diese Netzwerke",
        "",
        "\n\n".join(_netzwerkteil(k) for k in fuer),
        "",
        "## Regeln",
        "",
        GRUNDREGELN,
        "",
        "## Was bei diesem Format anders ist",
        "",
        PRODUKTREGELN if art == "produkt" else TIPPREGELN,
        "",
        BILD_ENTSTEHT,
    ]
    teile += _wissensteil(wissen or [])
    teile += [
        "",
        "## Antworte ausschließlich mit diesem JSON",
        "",
        WOCHE_FORMAT,
        "",
        f"Erwartet werden Fassungen für: {', '.join(fuer)}.",
        "Kein Text davor, kein Text danach, kein Code-Zaun.",
    ]
    return "\n".join(teile)


def wochenantwort_lesen(
    roh: str, erwartet: list[str], art: str
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Fassungen *und* Grafikfelder aus einer Antwort holen.

    Die Fassungen gehen durch dieselbe Prüfung wie sonst. Für die Grafik wird
    nur geprüft, was die Fläche erzwingt – Anzahl und Länge. Was dort nicht
    passt, sieht man sonst erst im fertigen Bild.
    """
    fassungen = antwort_lesen(roh, erwartet)
    daten = _json_finden(roh)
    grafik = daten.get("grafik")
    if not isinstance(grafik, dict):
        raise AntwortFehler(
            "In der Antwort steht kein Feld »grafik«. "
            f"Anfang der Antwort: {roh[:160]!r}")

    if art == "produkt":
        merkmale = [str(m).strip() for m in (grafik.get("merkmale") or []) if str(m).strip()]
        if len(merkmale) != MERKMALE_ANZAHL:
            raise AntwortFehler(
                f"Die Grafik braucht genau {MERKMALE_ANZAHL} Merkmale, "
                f"bekommen sind {len(merkmale)}.")
        zu_lang = [m for m in merkmale if len(m) > MERKMAL_ZEICHEN]
        if zu_lang:
            raise AntwortFehler(
                f"Diese Merkmale sind länger als {MERKMAL_ZEICHEN} Zeichen und "
                f"würden aus der Karte laufen: {zu_lang}")
        grafik["merkmale"] = merkmale
        if not str(grafik.get("name", "")).strip():
            raise AntwortFehler("Der Grafik fehlt der »name«.")
    else:
        bloecke = grafik.get("bloecke") or []
        if len(bloecke) != 3:
            raise AntwortFehler(
                f"Der Tipp braucht genau drei Blöcke, bekommen sind {len(bloecke)}.")
        for nummer, block in enumerate(bloecke, 1):
            punkte = [str(p).strip() for p in (block.get("punkte") or []) if str(p).strip()]
            if len(punkte) != 4:
                raise AntwortFehler(
                    f"Block {nummer} braucht vier Punkte, hat aber {len(punkte)}.")
            block["punkte"] = punkte
        if len(grafik.get("beachten") or []) != 4:
            raise AntwortFehler("Unter »beachten« gehören vier Punkte.")
        seite = daten.get("seite")
        if isinstance(seite, dict) and seite.get("absaetze"):
            # Die Seite ist Kür: Fehlt sie, entsteht der Beitrag trotzdem und
            # nur die HTML-Datei bleibt aus. Ist sie aber da, muss sie
            # brauchbar sein - ein Titel ohne Text nützt niemandem.
            if not str(seite.get("titel", "")).strip():
                raise AntwortFehler("Der Seite fehlt der Titel.")
            if not str(seite.get("kurz", "")).strip():
                raise AntwortFehler("Der Seite fehlt die Kurzfassung fürs Archiv.")
            grafik["_seite"] = seite
    return fassungen, grafik
