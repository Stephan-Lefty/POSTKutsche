"""Die systemd-Einheiten. Was hier fehlt, faellt erst nach Wochen auf."""

import unittest
from pathlib import Path

from postkutsche import dienste


class Einheiten(unittest.TestCase):

    def setUp(self):
        self.alle = dienste.einheiten(port=8770)

    def test_suchpfad_enthaelt_das_eigene_bin(self):
        # Dort liegt claude nach einer npm-Installation. Ohne diesen Eintrag
        # meldet der Dienst »claude ist nicht im Suchpfad«, waehrend das
        # Terminal es anstandslos findet.
        eigene = str(Path.home() / ".local" / "bin")
        self.assertIn(eigene, dienste._suchpfad())

    def test_beide_dienste_setzen_den_suchpfad(self):
        for name in (dienste.KALENDER, dienste.SENDEN_DIENST):
            with self.subTest(einheit=name):
                self.assertIn("Environment=\"PATH=", self.alle[name])

    def test_pfade_stehen_in_anfuehrungszeichen(self):
        # Der Projektordner traegt ein Leerzeichen im Namen. Ohne
        # Anfuehrungszeichen schneidet systemd den Wert dort ab, und
        # PYTHONPATH zeigt auf ein Verzeichnis, das es nicht gibt.
        for name in (dienste.KALENDER, dienste.SENDEN_DIENST):
            with self.subTest(einheit=name):
                self.assertIn('Environment="PYTHONPATH=', self.alle[name])

    def test_kalender_startet_nicht_endlos_neu(self):
        self.assertIn("StartLimitBurst", self.alle[dienste.KALENDER])

    def test_timer_holt_verpasstes_nach(self):
        self.assertIn("Persistent=true", self.alle[dienste.SENDEN_TIMER])
