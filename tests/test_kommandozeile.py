"""Die Kommandozeile – Rückgabewerte und was auf dem Schirm landet."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from hilfen import OhneEigeneKonfiguration
from postkutsche.__main__ import main


class Lauf:
    """Ergebnis eines Aufrufs: Rückgabewert, Ausgabe, Fehlerausgabe."""

    def __init__(self, rueckgabe: int, ausgabe: str, fehler: str) -> None:
        self.rueckgabe = rueckgabe
        self.ausgabe = ausgabe
        self.fehler = fehler


class Basis(OhneEigeneKonfiguration):
    def setUp(self):
        super().setUp()
        self.ordner = tempfile.TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.db = Path(self.ordner.name) / "probe.db"

    def rufe(self, *befehl: str) -> Lauf:
        aus, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(aus), contextlib.redirect_stderr(err):
            rueckgabe = main(["--ablage", str(self.db), *befehl])
        return Lauf(rueckgabe, aus.getvalue(), err.getvalue())

    def eingerichtet(self) -> None:
        self.rufe("einrichten")


class Einrichten(Basis):
    def test_legt_die_datei_an(self):
        lauf = self.rufe("einrichten")
        self.assertEqual(lauf.rueckgabe, 0)
        self.assertTrue(self.db.exists())

    def test_nennt_die_beispiele(self):
        # Ohne eigene Konfiguration kommen die Beispiele aus BEISPIELE.
        lauf = self.rufe("einrichten")
        for kennung in ("blog", "shop", "altbau"):
            self.assertIn(kennung, lauf.ausgabe)

    def test_zweimal_geht_gut(self):
        self.rufe("einrichten")
        self.assertEqual(self.rufe("einrichten").rueckgabe, 0)

    def test_legt_verzeichnisse_an(self):
        tief = Path(self.ordner.name) / "a" / "b" / "c.db"
        aus = io.StringIO()
        with contextlib.redirect_stdout(aus):
            self.assertEqual(main(["--ablage", str(tief), "einrichten"]), 0)
        self.assertTrue(tief.exists())


class Projekte(Basis):
    def test_liste_ohne_projekte_erklaert_sich(self):
        lauf = self.rufe("projekt", "liste")
        self.assertEqual(lauf.rueckgabe, 0)
        self.assertIn("einrichten", lauf.ausgabe)

    def test_liste_zeigt_umlaute(self):
        self.eingerichtet()
        self.rufe("projekt", "neu", "umlaut", "Mörtelspritzgerät",
                  "https://umlaut.example", "--art", "wordpress")
        self.assertIn("Mörtelspritzgerät", self.rufe("projekt", "liste").ausgabe)

    def test_neues_projekt_bekommt_seine_adresse(self):
        self.eingerichtet()
        lauf = self.rufe(
            "projekt", "neu", "testblog", "Testblog", "https://test.example/",
            "--art", "wordpress",
        )
        self.assertEqual(lauf.rueckgabe, 0)
        # Der Schrägstrich am Ende darf nicht doppelt auftauchen.
        self.assertIn("https://test.example/wp-json/wp/v2", lauf.ausgabe)

    def test_shopware_wird_auf_den_schluessel_hingewiesen(self):
        self.eingerichtet()
        lauf = self.rufe(
            "projekt", "neu", "shop", "Shop", "https://zweitshop.example", "--art", "shopware"
        )
        self.assertIn("Zugangsschlüssel", lauf.ausgabe)

    def test_pausieren_und_starten(self):
        self.eingerichtet()
        self.assertEqual(self.rufe("projekt", "pausieren", "blog").rueckgabe, 0)
        self.assertIn("pausiert", self.rufe("projekt", "liste").ausgabe)
        self.assertEqual(self.rufe("projekt", "starten", "blog").rueckgabe, 0)

    def test_unbekanntes_projekt_meldet_fehler(self):
        self.eingerichtet()
        lauf = self.rufe("projekt", "pausieren", "gibtsnicht")
        self.assertEqual(lauf.rueckgabe, 1)
        self.assertIn("gibtsnicht", lauf.fehler)

    def test_loeschen_braucht_den_schalter(self):
        # Ein Tippfehler darf kein Projekt kosten.
        self.eingerichtet()
        lauf = self.rufe("projekt", "loeschen", "blog")
        self.assertEqual(lauf.rueckgabe, 1)
        self.assertIn("pausieren", lauf.fehler)
        self.assertIn("blog", self.rufe("projekt", "liste").ausgabe)

    def test_loeschen_mit_schalter(self):
        self.eingerichtet()
        self.assertEqual(
            self.rufe("projekt", "loeschen", "blog", "--wirklich").rueckgabe, 0
        )
        self.assertNotIn("Mein Blog", self.rufe("projekt", "liste").ausgabe)


class Plan(Basis):
    def test_leerer_monat(self):
        self.eingerichtet()
        lauf = self.rufe("plan", "--monat", "2026-09")
        self.assertEqual(lauf.rueckgabe, 0)
        self.assertIn("Nichts geplant", lauf.ausgabe)

    def test_krummer_monat_wird_abgelehnt(self):
        self.eingerichtet()
        lauf = self.rufe("plan", "--monat", "September")
        self.assertEqual(lauf.rueckgabe, 1)

    def test_ohne_monat_geht_auch(self):
        self.eingerichtet()
        self.assertEqual(self.rufe("plan").rueckgabe, 0)


class Netzwerke(Basis):
    def test_zeigt_alle_vier(self):
        lauf = self.rufe("netzwerke")
        for kuerzel in ("MA", "LI", "FB", "IG"):
            self.assertIn(kuerzel, lauf.ausgabe)

    def test_nennt_die_bildpflicht_bei_instagram(self):
        self.assertIn("Pflicht", self.rufe("netzwerke").ausgabe)


class OhneBefehl(Basis):
    def test_zeigt_hilfe_und_meldet_fehler(self):
        aus = io.StringIO()
        with contextlib.redirect_stdout(aus):
            rueckgabe = main([])
        self.assertEqual(rueckgabe, 1)
        self.assertIn("postkutsche", aus.getvalue())


if __name__ == "__main__":
    unittest.main()
