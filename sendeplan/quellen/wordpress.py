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
"""

from __future__ import annotations

from typing import Any, Iterator

from .abrufen import AbrufFehler, entmarken, erstes_bild, json_holen, og_angaben, text_holen


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


def _aufbereiten(eintrag: dict[str, Any]) -> dict[str, Any]:
    inhalt_roh = _gerendert(eintrag, "content")
    return {
        "fremd_id": str(eintrag.get("id", "")),
        "titel": entmarken(_gerendert(eintrag, "title")),
        "text": entmarken(inhalt_roh),
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
