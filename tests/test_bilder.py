"""Wo Bilder liegen, und dass der Benutzer sie wiederfindet.

Kein Netzzugriff: Es geht um Pfade und Namen, nicht ums Herunterladen.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from postkutsche import bilder


class Dokumentenordner(unittest.TestCase):
    """Der Ordner heisst nicht ueberall gleich - also wird gefragt.

    Ein Werkzeug, das Dateien an einem Ort ablegt, den der Benutzer nicht
    findet, ist schlimmer als eines, das gar nichts ablegt.
    """

    def setUp(self):
        self.heim = tempfile.TemporaryDirectory()
        self.addCleanup(self.heim.cleanup)
        self.pfad = Path(self.heim.name)
        flicken = mock.patch.object(Path, "home", staticmethod(lambda: self.pfad))
        flicken.start()
        self.addCleanup(flicken.stop)
        # Die Umgebungsvariable sticht alles - hier soll sie nicht stoeren.
        umgebung = mock.patch.dict(os.environ, {}, clear=False)
        umgebung.start()
        self.addCleanup(umgebung.stop)
        os.environ.pop("POSTKUTSCHE_DOKUMENTE", None)

    def test_umgebung_sticht_alles(self):
        os.environ["POSTKUTSCHE_DOKUMENTE"] = "/anderswo"
        self.assertEqual(bilder.dokumentenordner(), Path("/anderswo"))

    def test_user_dirs_wird_gelesen(self):
        konfig = self.pfad / ".config"
        konfig.mkdir()
        (konfig / "user-dirs.dirs").write_text(
            'XDG_DESKTOP_DIR="$HOME/Schreibtisch"\n'
            'XDG_DOCUMENTS_DIR="$HOME/Unterlagen"\n', encoding="utf-8")
        self.assertEqual(bilder.dokumentenordner(), self.pfad / "Unterlagen")

    def test_vorhandener_ordner_wird_genommen(self):
        (self.pfad / "Documents").mkdir()
        with mock.patch.object(bilder, "_aus_xdg_werkzeug", return_value=None):
            self.assertEqual(bilder.dokumentenordner(), self.pfad / "Documents")

    def test_deutscher_name_hat_vorrang_vor_englischem(self):
        (self.pfad / "Documents").mkdir()
        (self.pfad / "Dokumente").mkdir()
        with mock.patch.object(bilder, "_aus_xdg_werkzeug", return_value=None):
            self.assertEqual(bilder.dokumentenordner(), self.pfad / "Dokumente")

    def test_ohne_alles_wird_dokumente_gewaehlt(self):
        # POSTKutsche spricht Deutsch, also ist das die bessere Wette.
        with mock.patch.object(bilder, "_aus_xdg_werkzeug", return_value=None):
            self.assertEqual(bilder.dokumentenordner(), self.pfad / "Dokumente")

    def test_heimatverzeichnis_gilt_nicht_als_dokumentenordner(self):
        # xdg-user-dir gibt das Heimatverzeichnis zurueck, wenn es nichts zu
        # sagen hat. Dort alles hinzuschuetten waere das Gegenteil von Ordnung.
        lauf = mock.Mock(returncode=0, stdout=str(self.pfad) + "\n")
        with mock.patch.object(bilder.subprocess, "run", return_value=lauf):
            self.assertIsNone(bilder._aus_xdg_werkzeug())

    def test_fehlendes_werkzeug_ist_kein_fehler(self):
        with mock.patch.object(bilder.subprocess, "run",
                               side_effect=FileNotFoundError):
            self.assertIsNone(bilder._aus_xdg_werkzeug())


class Ablegen(unittest.TestCase):
    """Die Woche steht vorn, weil nach Wochen aufgeraeumt wird."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        os.environ["POSTKUTSCHE_DOKUMENTE"] = self.ordner.name
        self.addCleanup(os.environ.pop, "POSTKUTSCHE_DOKUMENTE", None)

        self.quelle = Path(self.ordner.name) / "quelle.jpg"
        self.quelle.write_bytes(b"kein echtes Bild, aber eine Datei")

    def _ablegen(self, nummer=1, titel="T30-2 Brandschutztür"):
        return bilder.ablegen(self.quelle, "habefa", "2026-09-01T08:00:00Z",
                              "facebook", titel, 42, nummer)

    def test_landet_unter_woche_und_projekt(self):
        ziel = self._ablegen()
        self.assertEqual(ziel.parent.name, "habefa")
        # Der 1.9.2026 ist ein Dienstag der KW 36.
        self.assertEqual(ziel.parent.parent.name, "2026-KW36")
        self.assertEqual(ziel.parent.parent.parent.name, bilder.SAMMELORDNER)

    def test_der_name_verraet_den_beitrag(self):
        # Ohne Datenbank erkennbar: Datum, Netzwerk, Titel.
        name = self._ablegen().name
        self.assertTrue(name.startswith("2026-09-01_facebook_"))
        self.assertIn("T30-2-Brandschutztuer", name)

    def test_umlaute_werden_umgeschrieben_nicht_geworfen(self):
        # »Tr« waere nicht mehr zu lesen.
        self.assertIn("Tuer", self._ablegen(titel="Tür").name)

    def test_zwei_bilder_ueberschreiben_sich_nicht(self):
        erstes, zweites = self._ablegen(1), self._ablegen(2)
        self.assertNotEqual(erstes, zweites)
        self.assertTrue(erstes.is_file() and zweites.is_file())

    def test_die_datei_ist_wirklich_da(self):
        self.assertEqual(self._ablegen().read_bytes(), self.quelle.read_bytes())

    def test_fehlende_quelle_meldet_sich(self):
        with self.assertRaises(bilder.BildFehler):
            bilder.ablegen(Path(self.ordner.name) / "gibtsnicht.jpg", "p",
                           "2026-09-01T08:00:00Z", "facebook", "T", 1)

    def test_ein_titel_aus_lauter_sonderzeichen_gibt_keinen_leeren_namen(self):
        name = self._ablegen(titel="???").name
        self.assertIn("ohne-titel", name)

    def test_woche_kommt_aus_der_ortszeit(self):
        # Der 4. Januar 2026 liegt in KW 1, der 1. Januar noch in KW 1 des
        # Vorjahres - deshalb wird nicht selbst gerechnet.
        ziel = bilder.ablegen(self.quelle, "p", "2026-01-01T08:00:00Z",
                              "facebook", "T", 1)
        self.assertEqual(ziel.parent.parent.name, "2026-KW01")
