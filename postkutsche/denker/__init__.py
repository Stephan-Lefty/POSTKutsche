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

__all__ = ["kommando", "vorlagen", "schreiben", "verfuegbar",
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
) -> dict[str, dict[str, Any]]:
    """Lässt die Fassungen schreiben – über den gewählten Weg."""
    if weg == KOMMANDO:
        return kommando.fassungen(inhalt, fuer, projekt, zusatz)
    if weg == API:
        raise NotImplementedError(
            "Der Weg über die Anthropic-Schnittstelle ist noch nicht gebaut. "
            "Bis dahin: weg=\"kommando\"."
        )
    raise ValueError(f"Unbekannter Weg: {weg!r}. Bekannt: {KOMMANDO}, {API}")
