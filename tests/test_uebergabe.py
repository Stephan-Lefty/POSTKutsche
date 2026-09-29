"""Den Arbeitsstand mitnehmen und zurückholen.

Keine Synchronisation: Zu jedem Zeitpunkt ist genau ein Ort der gültige.
Geprüft wird vor allem der eine Fall, in dem man sich schaden kann – das
Überschreiben einer neueren Fassung.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from postkutsche import bilder, konfiguration, uebergabe


class Zweiseitig(unittest.TestCase):

    def setUp(self):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.wurzel = Path(ordner.name)

        self.lokal = self.wurzel / "lokal"
        self.stick = self.wurzel / "stick"
        (self.lokal / "ablage").mkdir(parents=True)
        (self.lokal / "einstellungen").mkdir()
        (self.lokal / "dokumente").mkdir()
        (self.lokal / "ablage" / "postkutsche.db").write_text("hier", encoding="utf-8")
        (self.lokal / "einstellungen" / "projekte.json").write_text("[]", encoding="utf-8")

        self.db = self.lokal / "ablage" / "postkutsche.db"
        for ziel, wert in (("POSTKUTSCHE_CONFIG", self.lokal / "einstellungen"),
                           ("POSTKUTSCHE_DOKUMENTE", self.lokal)):
            anstelle = mock.patch.dict(os.environ, {ziel: str(wert)})
            anstelle.start()
            self.addCleanup(anstelle.stop)
        # »dokumente« heißt unter Dokumente wie der Sammelordner.
        (self.lokal / bilder.SAMMELORDNER).mkdir(exist_ok=True)
        (self.lokal / bilder.SAMMELORDNER / "bild.png").write_text("x", encoding="utf-8")

    def test_mitnehmen_legt_den_stand_auf_den_traeger(self):
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        self.assertTrue((self.stick / "ablage" / "postkutsche.db").exists())
        self.assertTrue((self.stick / "einstellungen" / "projekte.json").exists())

    def test_am_alten_ort_bleibt_alles_liegen(self):
        # Kopiert, nicht verschoben: Beim ersten Mal will man vergleichen.
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        self.assertTrue(self.db.exists())

    def test_zurueckholen_bringt_den_stand_wieder_her(self):
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        (self.stick / "ablage" / "postkutsche.db").write_text("dort", encoding="utf-8")
        uebergabe.uebergeben(self.db, self.stick, "zurueckholen")
        self.assertEqual(self.db.read_text(encoding="utf-8"), "dort")

    def test_eine_neuere_zielseite_wird_nicht_ueberschrieben(self):
        # Der einzige Weg, sich hier zu schaden – deshalb der einzige,
        # der nachfragt.
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        time.sleep(0.01)
        (self.stick / "ablage" / "postkutsche.db").write_text("neuer", encoding="utf-8")
        with self.assertRaises(uebergabe.UebergabeFehler) as fehler:
            uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        self.assertIn("neuere Arbeit", str(fehler.exception))
        self.assertEqual(
            (self.stick / "ablage" / "postkutsche.db").read_text(encoding="utf-8"),
            "neuer")

    def test_mit_trotzdem_wird_doch_ueberschrieben(self):
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        time.sleep(0.01)
        (self.stick / "ablage" / "postkutsche.db").write_text("neuer", encoding="utf-8")
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen", trotzdem=True)
        self.assertEqual(
            (self.stick / "ablage" / "postkutsche.db").read_text(encoding="utf-8"),
            "hier")

    def test_ohne_stand_auf_dem_traeger_gibt_es_nichts_zu_holen(self):
        with self.assertRaises(uebergabe.UebergabeFehler) as fehler:
            uebergabe.uebergeben(self.db, self.stick, "zurueckholen")
        self.assertIn("keinen Arbeitsstand", str(fehler.exception))

    def test_eine_unbekannte_richtung_wird_abgelehnt(self):
        with self.assertRaises(uebergabe.UebergabeFehler):
            uebergabe.uebergeben(self.db, self.stick, "seitwaerts")

    def test_der_vergleich_nennt_die_neuere_seite(self):
        v = uebergabe.vergleich(self.db, self.stick)
        self.assertEqual(v["neuer"], "hier")
        self.assertFalse(v["dort"]["da"])
        uebergabe.uebergeben(self.db, self.stick, "mitnehmen")
        time.sleep(0.01)
        (self.stick / "ablage" / "postkutsche.db").write_text("neuer", encoding="utf-8")
        self.assertEqual(uebergabe.vergleich(self.db, self.stick)["neuer"], "dort")


class Datentraeger(unittest.TestCase):
    """Erkannt wird am Namen, nicht an einem gemerkten Pfad."""

    def test_ein_passend_benannter_ordner_wird_gefunden(self):
        with tempfile.TemporaryDirectory() as o:
            wurzel = Path(o) / "stephan"
            (wurzel / "POSTKUTSCHE").mkdir(parents=True)
            (wurzel / "Urlaubsbilder").mkdir()
            with mock.patch.object(uebergabe, "WECHSELORTE", (str(Path(o)),)):
                gefunden = uebergabe.datentraeger_suchen("stephan")
        self.assertEqual([p.name for p in gefunden], ["POSTKUTSCHE"])

    def test_ohne_wechselmedien_kommt_eine_leere_liste(self):
        with mock.patch.object(uebergabe, "WECHSELORTE", ("/gibt/es/nicht",)):
            self.assertEqual(uebergabe.datentraeger_suchen("wer"), [])


if __name__ == "__main__":
    unittest.main()
