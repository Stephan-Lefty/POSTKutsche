"""Wer die Texte schreibt.

Zwei Wege, eine Schnittstelle:

- `kommando` ruft `claude -p` auf. Nutzt ein vorhandenes Abo, keine Kosten je
  Beitrag, braucht aber Claude Code auf der Maschine.
- `api` geht über die Anthropic-Schnittstelle mit eigenem Schlüssel. Läuft
  auch dort, wo kein Claude Code installiert ist – etwa auf einem Server, der
  nur sendet. Noch nicht gebaut.

Beide liefern dasselbe: je Netzwerk ein Wörterbuch mit »text«, »schlagworte«
und »rueckfrage«.
"""

from __future__ import annotations

from typing import Any

from . import kommando, vorlagen
from .kommando import ClaudeFehler, ClaudeFehlt
from .vorlagen import AntwortFehler

__all__ = ["kommando", "vorlagen", "schreiben", "nachbessern", "verfuegbar",
           "ClaudeFehler", "ClaudeFehlt", "AntwortFehler"]

KOMMANDO = "kommando"
API = "api"


def verfuegbar(weg: str = KOMMANDO) -> bool:
    """Ob dieser Weg gerade benutzbar ist."""
    if weg == KOMMANDO:
        return kommando.vorhanden()
    return False


def schreiben(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    weg: str = KOMMANDO,
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Lässt die Fassungen schreiben – über den gewählten Weg.

    `frueher` sind die Texte, mit denen dasselbe Produkt schon einmal beworben
    wurde. Sie werden mitgegeben, damit der neue Beitrag anders klingt.

    `wissen` sind frühere Antworten des Betreibers auf Rückfragen. Sie
    ersparen ihm, dieselbe Frage jede Woche neu zu beantworten.
    """
    if weg == KOMMANDO:
        return kommando.fassungen(inhalt, fuer, projekt, zusatz,
                                  frueher=frueher, wissen=wissen)
    if weg == API:
        raise NotImplementedError(
            "Der Weg über die Anthropic-Schnittstelle ist noch nicht gebaut. "
            "Bis dahin: weg=\"kommando\"."
        )
    raise ValueError(f"Unbekannter Weg: {weg!r}. Bekannt: {KOMMANDO}, {API}")


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
    weg: str = KOMMANDO,
) -> dict[str, Any]:
    """Bessert einen Text mit der Antwort auf eine Rückfrage nach."""
    if weg == KOMMANDO:
        return kommando.nachbessern(inhalt, netzwerk, bisher, frage, antwort, zusatz)
    raise NotImplementedError(f"Weg {weg!r} ist noch nicht gebaut.")
