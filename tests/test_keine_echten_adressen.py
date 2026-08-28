"""Wacht darüber, dass keine echten Adressen ins Repository geraten.

POSTKutsche ist quelloffen, die Seiten, die damit bespielt werden, sind es nicht.
Adressen im Quelltext haben die unangenehme Eigenschaft, dass sie auch dann
noch dastehen, wenn man sie längst entfernt hat – in der Versionsgeschichte.
Deshalb prüft dieser Test von der anderen Seite: Nicht, ob bestimmte Adressen
fehlen (die müssten dann ja hier stehen), sondern ob **jede** Adresse im
Repository entweder unter `.example` liegt oder in einer kurzen, offenen Liste
steht.

`.example` ist nach RFC 2606 für Beispiele reserviert und kann niemandem
gehören. Wer eine neue Beispieladresse braucht, nimmt eine solche.

Die eigenen Seiten stehen in `~/.config/postkutsche/`, siehe `konfiguration.py`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# Adressen, die im Repository stehen dürfen. Alles hier ist entweder
# Werkzeugkette, Norm oder Anbieterdokumentation – nichts davon verrät, wer
# POSTKutsche wofür einsetzt.
ERLAUBT = {
    "github.com",
    "raw.githubusercontent.com",
    "keepachangelog.com",
    "semver.org",
    "spdx.org",
    "www.sitemaps.org",
    "sitemaps.org",
    "www.w3.org",
    "schemas.microsoft.com",
    "opensource.org",
    "docs.joinmastodon.org",
    "joinmastodon.org",
    "developer.linkedin.com",
    "learn.microsoft.com",
    "developers.facebook.com",
    "graph.facebook.com",
    "api.linkedin.com",
    "api.anthropic.com",
    "www.anthropic.com",
    "claude.ai",
    "python.org",
    "docs.python.org",
    "pypi.org",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

# Was durchsucht wird. Die Ablage und alles Erzeugte bleiben außen vor.
ENDUNGEN = (".py", ".md", ".toml", ".yml", ".yaml", ".json", ".sh", ".txt")
AUSGENOMMEN = {".git", "__pycache__", ".venv", "venv", "build", "dist",
               ".pytest_cache", "postkutsche.egg-info"}

ADRESSE = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _wurzel() -> Path:
    return Path(__file__).resolve().parent.parent


def _dateien():
    for pfad in _wurzel().rglob("*"):
        if not pfad.is_file() or pfad.suffix not in ENDUNGEN:
            continue
        if any(teil in AUSGENOMMEN for teil in pfad.parts):
            continue
        yield pfad


class KeineEchtenAdressen(unittest.TestCase):
    def test_alle_adressen_sind_beispiele_oder_erlaubt(self):
        beanstandet: list[str] = []
        for pfad in _dateien():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for nummer, zeile in enumerate(text.splitlines(), 1):
                for rechner in ADRESSE.findall(zeile):
                    rechner = rechner.rstrip(".")
                    if rechner in ERLAUBT or rechner.endswith(".example"):
                        continue
                    if rechner == "example" or rechner.endswith((".invalid", ".test")):
                        continue
                    beanstandet.append(
                        f"{pfad.relative_to(_wurzel())}:{nummer}  {rechner}"
                    )

        self.assertEqual(
            beanstandet, [],
            "Echte Adressen im Repository gefunden. Beispiele gehören unter "
            ".example (RFC 2606), die eigenen Seiten nach "
            "~/.config/postkutsche/projekte.json:\n  " + "\n  ".join(beanstandet),
        )

    def test_keine_mailadressen_ausser_der_eigenen_kennzeichnung(self):
        # Mailadressen haben im Quelltext nichts zu suchen. Ausgenommen ist,
        # was zur Lizenz oder zum Projekt selbst gehört.
        erlaubt = re.compile(r"(noreply@|@example\.|name@company)")
        muster = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        beanstandet: list[str] = []
        for pfad in _dateien():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for nummer, zeile in enumerate(text.splitlines(), 1):
                for adresse in muster.findall(zeile):
                    if not erlaubt.search(adresse):
                        beanstandet.append(
                            f"{pfad.relative_to(_wurzel())}:{nummer}  {adresse}"
                        )
        self.assertEqual(
            beanstandet, [],
            "Mailadressen im Repository gefunden:\n  " + "\n  ".join(beanstandet),
        )

    def test_die_eigene_konfiguration_ist_ausgeschlossen(self):
        # Wer versehentlich seine projekte.json ins Repository legt, soll sie
        # nicht mitcommitten können.
        gitignore = (_wurzel() / ".gitignore").read_text(encoding="utf-8")
        for eintrag in ("projekte.json", "hersteller.json", "zugaenge.json"):
            with self.subTest(eintrag=eintrag):
                self.assertIn(eintrag, gitignore)

    def test_beispieladressen_sind_wirklich_beispiele(self):
        from postkutsche import erstbestueckung

        for eintrag in erstbestueckung.BEISPIELE:
            with self.subTest(kennung=eintrag["kennung"]):
                self.assertTrue(
                    eintrag["adresse"].endswith(".example"),
                    f"{eintrag['adresse']} ist keine Beispieladresse",
                )


if __name__ == "__main__":
    unittest.main()
