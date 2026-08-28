"""Zugangstoken – im Schlüsselbund, ersatzweise in einer Datei.

**Sie stehen nicht in der Datenbank.** Ein Test in `test_ablage.py` verbietet
sogar die entsprechenden Spalten. Der Grund ist nicht Förmlichkeit: Die
Datenbank wird kopiert, gesichert und in einen Ordner gelegt, den Nextcloud
synchronisiert. Ein Token darin wäre irgendwann an fünf Orten.

Der Schlüsselbund ist der richtige Ort, aber er ist nicht überall da – auf
einem Server ohne Sitzung gibt es keinen. Deshalb der Rückfall auf
`~/.config/postkutsche/zugaenge.json` mit Rechten 600, und eine Warnung, wenn
die Rechte lockerer sind.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import konfiguration

DIENST = "postkutsche"


def datei() -> Path:
    return konfiguration.ordner() / "zugaenge.json"


class KeinZugang(Exception):
    """Für dieses Konto ist kein Token hinterlegt."""


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def setzen(kennung: str, token: str) -> str:
    """Legt ein Token ab. Gibt zurück, wo es gelandet ist."""
    ring = _keyring()
    if ring is not None:
        try:
            ring.set_password(DIENST, kennung, token)
            return "Schlüsselbund"
        except Exception:  # noqa: BLE001
            # Kein laufender Schlüsselbunddienst - dann eben die Datei.
            pass

    ziel = datei()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    daten = _datei_lesen()
    daten[kennung] = token
    ziel.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    if os.name == "posix":
        ziel.chmod(0o600)
    return str(ziel)


def holen(kennung: str) -> str:
    """Das Token zu einem Konto. Fehlt es, sagt die Meldung, was zu tun ist."""
    ring = _keyring()
    if ring is not None:
        try:
            token = ring.get_password(DIENST, kennung)
            if token:
                return token
        except Exception:  # noqa: BLE001
            pass

    token = _datei_lesen().get(kennung)
    if token:
        return token

    raise KeinZugang(
        f"Für das Konto »{kennung}« ist kein Zugangstoken hinterlegt. "
        f"Eintragen mit: postkutsche konto token {kennung}"
    )


def vorhanden(kennung: str) -> bool:
    try:
        holen(kennung)
        return True
    except KeinZugang:
        return False


def entfernen(kennung: str) -> bool:
    """Löscht ein Token an beiden möglichen Orten."""
    weg = False
    ring = _keyring()
    if ring is not None:
        try:
            ring.delete_password(DIENST, kennung)
            weg = True
        except Exception:  # noqa: BLE001
            pass

    daten = _datei_lesen()
    if kennung in daten:
        del daten[kennung]
        datei().write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        weg = True
    return weg


def rechte_warnung() -> str | None:
    """Warnt, wenn die Datei für andere lesbar ist."""
    return konfiguration.rechte_pruefen(datei())


def _datei_lesen() -> dict[str, str]:
    p = datei()
    if not p.exists():
        return {}
    try:
        daten = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return daten if isinstance(daten, dict) else {}
