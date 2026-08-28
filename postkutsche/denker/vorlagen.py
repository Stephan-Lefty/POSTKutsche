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

Was du nicht tust:

- Keine Preise nennen, auch keine ungefähren. Sie ändern sich, der Beitrag
  bleibt stehen.
- Nichts erfinden. Was nicht im Quelltext steht, steht nicht im Beitrag -
  keine Maße, keine Normen, keine Eigenschaften, keine Jahreszahlen.
- Keine Versprechen zu Lieferzeit, Verfügbarkeit oder Eignung für einen
  bestimmten Zweck.

Wenn du unsicher bist:

Schreib deine Frage in »rueckfrage« und lass den Text trotzdem so gut wie
möglich stehen. Ein Beitrag mit offener Frage wird nicht veröffentlicht,
bevor jemand geantwortet hat - das ist besser als eine glatte Erfindung.
Frag zum Beispiel, wenn der Quelltext widersprüchlich ist, wenn eine
Fachangabe unklar bleibt oder wenn du nicht erkennen kannst, worum es
eigentlich geht. Ist alles klar, setz »rueckfrage« auf null.\
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


def anweisung(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
) -> str:
    """Baut die vollständige Anweisung für einen Beitrag.

    `inhalt` ist, was eine Quelle geliefert hat: titel, text, adresse,
    bild_adresse, kategorien. `fuer` sind die Netzwerkkennungen.
    """
    if not fuer:
        raise ValueError("Ohne Netzwerk gibt es nichts zu schreiben.")

    quelle = [f"Titel: {inhalt.get('titel', '')}"]
    if inhalt.get("adresse"):
        quelle.append(f"Adresse: {inhalt['adresse']}")
    if inhalt.get("kategorien"):
        quelle.append(f"Themen: {', '.join(inhalt['kategorien'])}")
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
