"""Kein Sprachmodell: Du schreibst selbst.

Der Weg für alles, was keine Maschine formulieren soll – die Ankündigung mit
dem eigenen Ton, die Nachricht, bei der es auf jedes Wort ankommt, oder
schlicht den Tag, an dem kein Dienst erreichbar ist.

Leer bleibt das Feld trotzdem nicht: Titel und Anriss stehen schon da,
gekürzt auf das, was das jeweilige Netzwerk zulässt. Ein Gerüst schreibt sich
leichter um als ein leeres Feld – und der Termin, die Bildwahl und der
Handbetrieb funktionieren genauso wie bei einem geschriebenen Beitrag.

Eine Rückfrage gibt es hier nie: Es fragt ja niemand.
"""

from __future__ import annotations

from typing import Any

from .. import netzwerke
from . import vorlagen


def fassungen(
    inhalt: dict[str, Any],
    fuer: list[str],
    projekt: str = "",
    zusatz: str = "",
    einstellungen: dict[str, Any] | None = None,
    frueher: dict[str, str] | None = None,
    wissen: list[dict[str, Any]] | None = None,
    art: str = vorlagen.PRODUKT,
) -> dict[str, dict[str, Any]]:
    """Ein Gerüst je Netzwerk – ohne Rückfrage, ohne Aufruf nach draußen.

    Die übrigen Angaben (`projekt`, `zusatz`, `frueher`, `wissen`, `art`)
    nimmt dieser Weg entgegen und benutzt sie nicht. Sie gehören zur
    gemeinsamen Schnittstelle: Wer den Weg umstellt, soll an den Aufrufen
    nichts ändern müssen.
    """
    titel = str(inhalt.get("titel") or "").strip()
    anriss = str(inhalt.get("text") or "").strip()

    ergebnis: dict[str, dict[str, Any]] = {}
    for kennung in fuer:
        netz = netzwerke.netzwerk(kennung)
        ergebnis[kennung] = {
            "text": _geruest(titel, anriss, netz.zeichen_ziel) or titel[:netz.zeichen_max],
            "schlagworte": "",
            "rueckfrage": None,
        }
    return ergebnis


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
    einstellungen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gibt es nicht: Wer selbst schreibt, bessert selbst nach."""
    raise NotImplementedError(
        "»Von Hand« kennt kein Nachbessern – der Text steht im Feld und "
        "lässt sich dort ändern."
    )


def erreichbar(einstellungen: dict[str, Any] | None = None) -> bool:
    """Immer. Dieser Weg hängt an nichts."""
    return True


def _geruest(titel: str, anriss: str, ziel: int) -> str:
    """Titel und so viel Anriss, wie ohne abgehackten Satz hineinpasst."""
    if not titel:
        return _saetze_bis(anriss, ziel)
    rest = ziel - len(titel) - 2
    weiter = _saetze_bis(anriss, rest) if rest > 40 else ""
    return f"{titel}\n\n{weiter}".strip() if weiter else titel


def _saetze_bis(text: str, grenze: int) -> str:
    """Ganze Sätze bis zur Grenze. Lieber einer weniger als einer halb."""
    if not text:
        return ""
    if len(text) <= grenze:
        return text

    gesammelt = ""
    for stueck in text.replace("! ", "!\n").replace("? ", "?\n").split(". "):
        satz = stueck if stueck.endswith((".", "!", "?")) else f"{stueck}."
        if len(gesammelt) + len(satz) + 1 > grenze:
            break
        gesammelt = f"{gesammelt} {satz}".strip()
    return gesammelt
