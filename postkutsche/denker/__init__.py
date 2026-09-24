"""Wer die Texte schreibt.

Vier Wege, eine Schnittstelle:

- `kommando` ruft `claude -p` auf. Nutzt ein vorhandenes Abo, keine Kosten je
  Beitrag, braucht aber Claude Code auf der Maschine.
- `offen` spricht mit allem, was die OpenAI-Form kennt: Ollama auf dem eigenen
  Rechner, LM Studio, OpenRouter, DeepSeek, Mistral, ChatGPT. Ein Modul für
  viele Anbieter – sie unterscheiden sich in Adresse, Modellname und
  Schlüssel, nicht in der Anfrage.
- `anthropisch` geht über die Anthropic-Schnittstelle mit eigenem Schlüssel.
  Für Maschinen ohne Claude Code – etwa einen Server, der sonst nur sendet.
- `hand` schreibt nichts: Titel und Anriss stehen im Feld, den Rest schreibst
  du selbst.

Alle liefern dasselbe: je Netzwerk ein Wörterbuch mit »text«, »schlagworte«
und »rueckfrage«. Deshalb steht in `entwerfen.py` und `kampagnenlauf.py` nur
ein Aufruf und keine Verzweigung.

**Welcher Weg gilt**, entscheidet in dieser Reihenfolge: die Einstellung des
Projekts (`"denker"` in `projekte.json`), dann `~/.config/postkutsche/
denker.json`, dann die Vorgabe `kommando`. So kann ein Blog von Hand
geschrieben werden, während der Shop weiterläuft.
"""

from __future__ import annotations

from typing import Any

from .. import konfiguration, zugaenge
from . import anthropisch, hand, kommando, netz, offen, vorlagen
from .netz import DenkerFehler, DenkerFehlt
from .vorlagen import BLOG, PRODUKT, AntwortFehler

#: Die alten Namen. Sie stehen in Tests und in fremden Zweigen, und ein
#: Umbenennen wäre Arbeit ohne Gewinn.
ClaudeFehler = DenkerFehler
ClaudeFehlt = DenkerFehlt

__all__ = ["kommando", "offen", "anthropisch", "hand", "vorlagen", "netz",
           "schreiben", "nachbessern", "verfuegbar", "waehlen", "wege", "nicht_da",
           "DenkerFehler", "DenkerFehlt", "ClaudeFehler", "ClaudeFehlt",
           "AntwortFehler", "BLOG", "PRODUKT",
           "KOMMANDO", "OFFEN", "ANTHROPISCH", "HAND"]

KOMMANDO = "kommando"
OFFEN = "offen"
ANTHROPISCH = "anthropisch"
HAND = "hand"

WEGE = {
    KOMMANDO: kommando,
    OFFEN: offen,
    ANTHROPISCH: anthropisch,
    HAND: hand,
}

#: Was in der Oberfläche steht. Kurz, und es sagt, woran der Weg hängt.
NAMEN = {
    KOMMANDO: "Claude Code (Abo)",
    OFFEN: "Offene Schnittstelle (Ollama, ChatGPT …)",
    ANTHROPISCH: "Anthropic-Schnittstelle (Schlüssel)",
    HAND: "Von Hand – ich schreibe selbst",
}


def wege() -> list[dict[str, Any]]:
    """Alle Wege mit Namen und dem, was gerade eingestellt ist."""
    angaben = konfiguration.denker_lesen()
    gewaehlt = str(angaben.get("weg") or KOMMANDO)
    return [
        {
            "kennung": kennung,
            "name": NAMEN[kennung],
            "gewaehlt": kennung == gewaehlt,
            "modell": str((angaben.get(kennung) or {}).get("modell") or ""),
        }
        for kennung in WEGE
    ]


def waehlen(projekt: Any = None) -> tuple[str, dict[str, Any]]:
    """Welcher Weg gilt und womit er arbeitet.

    Gibt (Weg, Einstellungen) zurück. In den Einstellungen steckt auch der
    Schlüssel – geholt aus dem Schlüsselbund, nicht aus einer Datei im
    Klartext und niemals aus der Datenbank.
    """
    angaben = konfiguration.denker_lesen()
    weg = str(angaben.get("weg") or KOMMANDO)

    eigene = getattr(projekt, "einstellungen", None) or {}
    if isinstance(eigene, dict) and eigene.get("denker"):
        weg = str(eigene["denker"])

    if weg not in WEGE:
        raise DenkerFehler(
            f"Unbekannter Weg: {weg!r}. Bekannt: {', '.join(WEGE)}."
        )

    einstellungen = _einstellungen_fuer(weg, angaben)
    if isinstance(eigene, dict) and isinstance(eigene.get("denker_einstellungen"), dict):
        einstellungen.update(eigene["denker_einstellungen"])
    return weg, einstellungen


def _einstellungen_fuer(weg: str,
                        angaben: dict[str, Any] | None = None) -> dict[str, Any]:
    """Adresse, Modell und Schlüssel für einen Weg."""
    if angaben is None:
        angaben = konfiguration.denker_lesen()
    einstellungen = dict(angaben.get(weg) or {})

    if weg in (OFFEN, ANTHROPISCH) and "schluessel" not in einstellungen:
        kennung = str(einstellungen.get("schluessel_kennung") or f"denker-{weg}")
        try:
            einstellungen["schluessel"] = zugaenge.holen(kennung)
        except zugaenge.KeinZugang:
            # Ollama läuft ohne Schlüssel. Fehlt einer, wo er gebraucht wird,
            # sagt das der Weg selbst - mit einer Meldung, die den Befehl nennt.
            pass
    return einstellungen


def verfuegbar(weg: str | None = None, projekt: Any = None) -> bool:
    """Ob dieser Weg gerade benutzbar ist."""
    weg, einstellungen = _bestimmen(weg, None, projekt)
    return WEGE[weg].erreichbar(einstellungen)


def nicht_da(weg: str) -> str:
    """Was zu tun ist, wenn der gewählte Weg nicht antwortet.

    Vier Wege, vier Abhilfen – eine Meldung, die pauschal »claude
    installieren« sagt, schickt jemanden mit Ollama in die Irre.
    """
    return {
        KOMMANDO: ("»claude« ist nicht im Suchpfad. Claude Code installieren "
                   "(npm install -g @anthropic-ai/claude-code), starten und "
                   "mit /login anmelden."),
        OFFEN: ("Der Dienst antwortet nicht. Läuft er? Bei Ollama: »ollama "
                "serve«. Adresse und Modell stehen in "
                "~/.config/postkutsche/denker.json."),
        ANTHROPISCH: ("Die Anthropic-Schnittstelle antwortet nicht. Schlüssel "
                      "hinterlegt? »postkutsche denker schluessel anthropisch«."),
        HAND: "Von Hand geht immer – diese Meldung sollte nie erscheinen.",
    }.get(weg, f"Der Weg »{weg}« ist nicht benutzbar.")


def schreiben(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    weg: str | None = None,
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
    art: str = vorlagen.PRODUKT,
    einstellungen: dict[str, Any] | None = None,
    projektdaten: Any = None,
) -> dict[str, dict[str, Any]]:
    """Lässt die Fassungen schreiben – über den gewählten Weg.

    `frueher` sind die Texte, mit denen dasselbe Produkt schon einmal beworben
    wurde. Sie werden mitgegeben, damit der neue Beitrag anders klingt.

    `wissen` sind frühere Antworten des Betreibers auf Rückfragen. Sie
    ersparen ihm, dieselbe Frage jede Woche neu zu beantworten.

    `art` unterscheidet Blogbeitrag von Produkt – siehe `vorlagen.anweisung`.

    `projektdaten` ist das Projekt selbst, nicht sein Name: Daraus kommt die
    Einstellung, welcher Weg für dieses Projekt gilt.
    """
    weg, einstellungen = _bestimmen(weg, einstellungen, projektdaten)
    return WEGE[weg].fassungen(
        inhalt, fuer, projekt, zusatz,
        einstellungen=einstellungen, frueher=frueher, wissen=wissen, art=art)


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
    weg: str | None = None,
    einstellungen: dict[str, Any] | None = None,
    projektdaten: Any = None,
) -> dict[str, Any]:
    """Bessert einen Text mit der Antwort auf eine Rückfrage nach."""
    weg, einstellungen = _bestimmen(weg, einstellungen, projektdaten)
    return WEGE[weg].nachbessern(
        inhalt, netzwerk, bisher, frage, antwort, zusatz,
        einstellungen=einstellungen)


def _bestimmen(weg: str | None, einstellungen: dict[str, Any] | None,
               projektdaten: Any) -> tuple[str, dict[str, Any]]:
    if weg is None:
        return waehlen(projektdaten)
    if weg not in WEGE:
        raise DenkerFehler(
            f"Unbekannter Weg: {weg!r}. Bekannt: {', '.join(WEGE)}."
        )
    if einstellungen is not None:
        return weg, einstellungen
    # Ein ausdrücklich genannter Weg bekommt trotzdem seine Einstellungen -
    # sonst müsste jeder Aufrufer Adresse, Modell und Schlüssel selbst
    # heraussuchen.
    return weg, _einstellungen_fuer(weg)
