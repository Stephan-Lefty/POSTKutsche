"""Was mehrere Tests brauchen.

Vor allem eines: **Tests dürfen die eigene Konfiguration weder lesen noch
schreiben.** Läge in `~/.config/sendeplan/projekte.json` etwas anderes als
erwartet, schlügen Tests auf dem einen Rechner fehl und auf dem anderen nicht –
und der Fehler stünde nirgends im Repository. Deshalb zeigt `SENDEPLAN_CONFIG`
in Tests immer auf ein leeres, frisch angelegtes Verzeichnis.
"""

from __future__ import annotations

import os
import tempfile
import unittest


class OhneEigeneKonfiguration(unittest.TestCase):
    """Basisklasse, die SENDEPLAN_CONFIG auf einen leeren Ordner lenkt."""

    def setUp(self):
        super().setUp()
        self._ordner = tempfile.TemporaryDirectory()
        self.addCleanup(self._ordner.cleanup)

        vorher = os.environ.get("SENDEPLAN_CONFIG")
        os.environ["SENDEPLAN_CONFIG"] = self._ordner.name
        self.addCleanup(self._zuruecksetzen, vorher)

        # kampagnen.HERSTELLER wird beim Laden des Moduls einmal gefüllt.
        # Ohne das Neuladen sähe ein Test die Hersteller des Rechners, auf dem
        # er läuft.
        from sendeplan import kampagnen

        kampagnen.hersteller_neu_laden()
        self.addCleanup(kampagnen.hersteller_neu_laden)

    @property
    def konfigurationsordner(self) -> str:
        return self._ordner.name

    @staticmethod
    def _zuruecksetzen(vorher: str | None) -> None:
        if vorher is None:
            os.environ.pop("SENDEPLAN_CONFIG", None)
        else:
            os.environ["SENDEPLAN_CONFIG"] = vorher
