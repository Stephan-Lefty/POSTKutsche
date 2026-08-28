"""Vom Blogbeitrag zum Entwurf im Kalender.

Der Weg, der die Teile verbindet: Quelle abrufen, neue Inhalte merken, Claude
schreiben lassen, Beitrag mit Termin anlegen, Fassungen ablegen.

**Der erste Abruf ist stumm.** Eine Seitenkarte kann mehrere tausend Adressen
enthalten, ein Blog hunderte Beiträge - die alle als »neu« zu melden wäre kein
Kalender mehr, sondern eine Lawine. Beim ersten Mal wird deshalb nur gemerkt,
was da ist; Entwürfe entstehen erst ab dem zweiten Abruf, für das, was seither
dazugekommen ist. Wer das übergehen will, nimmt `--auch-bekannte`.
"""

from __future__ import annotations

from typing import Any

from . import ablage as ablage_modul
from . import denker, sendezeiten, zeiten
from .quellen import seitenkarte, wordpress


class EntwurfFehler(Exception):
    """Etwas hat gefehlt. Die Meldung ist für Menschen gedacht."""


def inhalte_holen(projekt, anzahl: int = 10) -> list[dict[str, Any]]:
    """Ruft die Quelle des Projekts ab."""
    e = projekt.einstellungen
    if projekt.art == "wordpress":
        adresse = e.get("rest") or f"{projekt.adresse.rstrip('/')}/wp-json/wp/v2"
        return list(wordpress.beitraege(adresse, anzahl, e.get("ausschliessen")))

    if projekt.art == "seitenkarte":
        karte = e.get("seitenkarte") or f"{projekt.adresse.rstrip('/')}/sitemap.xml"
        adressen = seitenkarte.produktadressen(karte, e.get("produktmuster"))
        # Nur die ersten paar auslesen: Jede Seite ist ein eigener Abruf, und
        # für einen Entwurf braucht es nicht die ganze Karte.
        return [seitenkarte.seite(a) for a in adressen[:anzahl]]

    if projekt.art == "shopware":
        raise EntwurfFehler(
            f"Für {projekt.name} fehlt noch die Shopware-Anbindung. "
            "Sie braucht den Zugangsschlüssel des Verkaufskanals."
        )

    raise EntwurfFehler(f"Unbekannte Projektart: {projekt.art!r}")


def entwerfen(
    ablage,
    kennung: str,
    netzwerke: list[str],
    anzahl: int = 1,
    auch_bekannte: bool = False,
    melden=print,
) -> list[int]:
    """Legt Entwürfe an. Gibt die Nummern der neuen Beiträge zurück."""
    projekt = ablage.projekt(kennung)
    if projekt is None:
        raise EntwurfFehler(f"Kein Projekt mit der Kennung »{kennung}«.")
    if not projekt.aktiv:
        raise EntwurfFehler(
            f"»{kennung}« ist pausiert. Erst starten: postkutsche projekt starten {kennung}"
        )
    if not denker.verfuegbar():
        raise EntwurfFehler(
            "»claude« ist nicht im Suchpfad. Claude Code installieren, "
            "starten und mit /login anmelden."
        )

    erster_abruf = projekt.zuletzt_geholt is None
    melden(f"Rufe {projekt.name} ab …")
    gefunden = inhalte_holen(projekt, max(anzahl * 5, 10))

    neue: list[tuple[int, dict[str, Any]]] = []
    for inhalt in gefunden:
        nummer, ist_neu = ablage.inhalt_merken(
            projekt.id, inhalt["fremd_id"], inhalt["titel"], inhalt["adresse"],
            inhalt.get("text", ""), inhalt.get("bild_adresse"),
            inhalt.get("veroeffentlicht"),
        )
        if ist_neu or auch_bekannte:
            neue.append((nummer, inhalt))
    ablage.geholt_vermerken(projekt.id)

    melden(f"{len(gefunden)} gefunden, davon {len(neue)} neu.")

    if erster_abruf and not auch_bekannte:
        melden(
            "\nErster Abruf – es wird nur gemerkt, was da ist. Entwürfe "
            "entstehen ab dem nächsten Mal für das, was dazukommt.\n"
            "Trotzdem jetzt entwerfen: --auch-bekannte anhängen."
        )
        return []

    if not neue:
        melden("Nichts Neues. Kein Entwurf angelegt.")
        return []

    zielgruppe = sendezeiten.zielgruppe_von(projekt)
    angelegt: list[int] = []

    for nummer, inhalt in neue[:anzahl]:
        melden(f"\n» {inhalt['titel'][:70]}")
        melden("  Claude schreibt …")
        fassungen = denker.schreiben(inhalt, netzwerke, projekt.name)

        # Der Termin richtet sich nach dem ersten Netzwerk; die übrigen
        # Fassungen gehen zur selben Zeit raus. Ein Beitrag ist ein Kärtchen.
        termin, grund = sendezeiten.vorschlagen(netzwerke[0], zielgruppe, anzahl=1)[0]
        beitrag = ablage.beitrag_anlegen(projekt.id, termin, inhalt_id=nummer)
        angelegt.append(beitrag)

        for netz in netzwerke:
            f = fassungen[netz]
            ablage.fassung_setzen(
                beitrag, netz, f["text"], f["schlagworte"],
                inhalt.get("bild_adresse"),
            )
            zeichen = len(f["text"])
            hinweis = f"  ? {f['rueckfrage']}" if f["rueckfrage"] else ""
            melden(f"  {netz:<10} {zeichen:>4} Zeichen{hinweis}")

        melden(f"  Termin: {zeiten.lesbar(termin)} – {grund[:60]}")
        offen = ablage.rueckfragen(beitrag)
        if offen:
            melden(f"  {len(offen)} Rückfrage(n) offen – nicht freigebbar.")

    return angelegt
