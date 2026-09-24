"""Dienste, die die OpenAI-Form sprechen – und das sind fast alle.

Ein Modul, viele Anbieter: Ollama, LM Studio, OpenRouter, DeepSeek, Mistral,
Groq und ChatGPT selbst hören alle auf dieselbe Anfrage unter
`/chat/completions`. Was sich unterscheidet, sind Adresse, Modellname und ob
ein Schlüssel nötig ist – und das steht in der Einstellung, nicht im Code.

**Ollama ist der Grund, warum dieser Weg zuerst kam.** Er läuft auf dem
eigenen Rechner, kostet nichts je Beitrag und braucht kein Konto; für einen
Mastodon-Text mit 500 Zeichen reicht ein kleines Modell. Wer lieber einen
Dienst im Netz nimmt, trägt dessen Adresse ein und ändert sonst nichts.
"""

from __future__ import annotations

from typing import Any

from . import netz, vorlagen
from .netz import DenkerFehler

#: Wo Ollama auf demselben Rechner hört. Vorgabe, wenn nichts anderes
#: eingetragen ist - der Weg soll ohne Konto und ohne Schlüssel anfangen.
STAMM = "http://localhost:11434/v1"
MODELL = "llama3.1:8b"


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
    """Ob der Dienst antwortet. Für »denker pruefen« und die Oberfläche."""
    try:
        _aufrufen("Antworte genau mit: {\"fassungen\": {}}", einstellungen or {},
                  hoechstens=32)
    except DenkerFehler:
        return False
    return True


def _aufrufen(anweisung: str, einstellungen: dict[str, Any],
              hoechstens: int = 4000) -> str:
    stamm = str(einstellungen.get("adresse") or STAMM).rstrip("/")
    modell = str(einstellungen.get("modell") or MODELL)

    kopfzeilen = {"Content-Type": "application/json"}
    schluessel = einstellungen.get("schluessel")
    if schluessel:
        kopfzeilen["Authorization"] = f"Bearer {schluessel}"

    rumpf: dict[str, Any] = {
        "model": modell,
        "messages": [{"role": "user", "content": anweisung}],
        "max_tokens": hoechstens,
        # Die Anweisung verlangt JSON. Manche Dienste halten sich ohne diesen
        # Schalter nicht daran; die, die ihn nicht kennen, übergehen ihn.
        "response_format": {"type": "json_object"},
    }
    if "temperatur" in einstellungen:
        rumpf["temperature"] = float(einstellungen["temperatur"])

    daten = netz.json_senden(f"{stamm}/chat/completions", kopfzeilen, rumpf)
    return _text_holen(daten)


def _text_holen(daten: dict[str, Any]) -> str:
    """Den Antworttext aus der Hülle holen.

    Erst den geraden Weg, dann die Abweichler: Manche Dienste liefern
    `content` als Liste von Bausteinen statt als Zeichenkette, und wer eine
    Denkstufe eingeschaltet hat, bekommt das Ergebnis mitunter unter einem
    anderen Feld. Ein Werkzeug, das daran stehen bleibt, ist ärgerlicher als
    ein paar Zeilen Vorsicht.
    """
    wahlen = daten.get("choices")
    if not isinstance(wahlen, list) or not wahlen:
        raise DenkerFehler(f"In der Antwort steht keine Wahl: {str(daten)[:200]}")

    nachricht = wahlen[0].get("message") if isinstance(wahlen[0], dict) else None
    if not isinstance(nachricht, dict):
        raise DenkerFehler(f"Unerwarteter Aufbau: {str(wahlen[0])[:200]}")

    inhalt = nachricht.get("content")
    if isinstance(inhalt, str) and inhalt.strip():
        return inhalt
    if isinstance(inhalt, list):
        stuecke = [str(teil.get("text", "")) for teil in inhalt
                   if isinstance(teil, dict)]
        zusammen = "".join(stuecke).strip()
        if zusammen:
            return zusammen

    grund = wahlen[0].get("finish_reason")
    if grund == "length":
        raise DenkerFehler(
            "Die Antwort war abgeschnitten – das Modell hat die Grenze für "
            "die Ausgabe erreicht. Ein kürzerer Quelltext oder ein größeres "
            "Modell hilft."
        )
    raise DenkerFehler(f"Die Antwort enthielt keinen Text: {str(nachricht)[:200]}")
