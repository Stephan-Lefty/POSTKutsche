"""Claude über die Anthropic-Schnittstelle, mit eigenem Schlüssel.

Der Unterschied zu `kommando.py` ist nicht das Modell, sondern die Rechnung:
Dort zahlt ein vorhandenes Abo, hier wird je Beitrag abgerechnet. Dafür
braucht dieser Weg kein Claude Code auf der Maschine – auf einem Server, der
sonst nur sendet, ist das der Unterschied zwischen »läuft« und »läuft nicht«.

**Zwei Eigenheiten, die man kennen muss.** Erstens nimmt die Schnittstelle
seit Opus 4.7 keine Regler für Zufälligkeit mehr an – wer `temperature`
mitschickt, bekommt eine 400 statt einer Antwort. Zweitens kann eine Anfrage
mit Erfolg beantwortet und trotzdem abgelehnt werden: Dann steht in
`stop_reason` das Wort »refusal« und der Inhalt ist leer. Wer nur auf den
Statuscode schaut, liest anschließend ins Leere.
"""

from __future__ import annotations

from typing import Any

from . import netz, vorlagen
from .netz import DenkerFehler

ADRESSE = "https://api.anthropic.com/v1/messages"

#: Die Fassung der Schnittstelle. Sie steht seit 2023 still und gehört in
#: jede Anfrage - ohne sie antwortet der Dienst gar nicht.
FASSUNG = "2023-06-01"

#: Vorgabe. Wer sparen will, trägt in der Einstellung ein kleineres Modell
#: ein - für 500 Zeichen Mastodon reicht auch Haiku.
MODELL = "claude-opus-4-8"


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
    """Lässt die Fassungen schreiben und gibt zurück, was die Ablage erwartet."""
    text = _aufrufen(
        vorlagen.anweisung(inhalt, fuer, projekt, zusatz, frueher, wissen, art),
        einstellungen or {},
    )
    return vorlagen.antwort_lesen(text, fuer)


def nachbessern(
    inhalt: dict[str, Any],
    netzwerk: str,
    bisher: str,
    frage: str,
    antwort: str,
    zusatz: str = "",
    einstellungen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bessert einen Text mit der Antwort auf die Rückfrage nach."""
    text = _aufrufen(
        vorlagen.nachbesserung(inhalt, netzwerk, bisher, frage, antwort, zusatz),
        einstellungen or {},
    )
    return vorlagen.antwort_lesen(text, [netzwerk])[netzwerk]


def erreichbar(einstellungen: dict[str, Any] | None = None) -> bool:
    """Ob Schlüssel und Modell stimmen – geprüft mit einer winzigen Anfrage."""
    try:
        _aufrufen("Antworte genau mit: {\"fassungen\": {}}", einstellungen or {},
                  hoechstens=32)
    except DenkerFehler:
        return False
    return True


def _aufrufen(anweisung: str, einstellungen: dict[str, Any],
              hoechstens: int = 4000) -> str:
    schluessel = einstellungen.get("schluessel")
    if not schluessel:
        raise DenkerFehler(
            "Für die Anthropic-Schnittstelle fehlt der Zugangsschlüssel. "
            "Einmal »postkutsche denker schluessel anthropisch« ausführen."
        )

    rumpf: dict[str, Any] = {
        "model": str(einstellungen.get("modell") or MODELL),
        "max_tokens": hoechstens,
        "messages": [{"role": "user", "content": anweisung}],
    }
    # Kein »temperature«, kein »top_p«: Die neueren Modelle lehnen beides ab.
    # Wer den Ton ändern will, ändert die Anweisung in vorlagen.py.

    daten = netz.json_senden(
        str(einstellungen.get("adresse") or ADRESSE),
        {
            "Content-Type": "application/json",
            "x-api-key": str(schluessel),
            "anthropic-version": str(einstellungen.get("fassung") or FASSUNG),
        },
        rumpf,
    )
    return _text_holen(daten)


def _text_holen(daten: dict[str, Any]) -> str:
    grund = daten.get("stop_reason")
    if grund == "refusal":
        raise DenkerFehler(
            "Claude hat die Anfrage abgelehnt. Das kommt bei harmlosen Texten "
            "selten vor; wenn doch, hilft meist ein anderer Quelltext."
        )

    bausteine = daten.get("content")
    if not isinstance(bausteine, list):
        raise DenkerFehler(f"Unerwartete Antwort: {str(daten)[:200]}")

    stuecke = [str(teil.get("text", "")) for teil in bausteine
               if isinstance(teil, dict) and teil.get("type") == "text"]
    zusammen = "".join(stuecke).strip()
    if zusammen:
        return zusammen

    if grund == "max_tokens":
        raise DenkerFehler(
            "Die Antwort war abgeschnitten – die Grenze für die Ausgabe war "
            "zu niedrig für so viele Fassungen."
        )
    raise DenkerFehler(f"Die Antwort enthielt keinen Text: {str(daten)[:200]}")
