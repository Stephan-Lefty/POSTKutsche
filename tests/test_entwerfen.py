"""Der Weg vom Inhalt zum Entwurf."""

from __future__ import annotations

import unittest
from unittest import mock

from postkutsche import entwerfen
from postkutsche.ablage import BEITRAG_RUECKFRAGE, Ablage, RueckfrageOffen

INHALT = {
    "fremd_id": "1", "titel": "Eine Tür", "text": "Kurzer Text.",
    "adresse": "https://shop.example/tuer_1.html",
    "bild_adresse": None, "kategorien": [],
}


class Rueckfragen(unittest.TestCase):
    """Eine Rückfrage muss in der Ablage landen, nicht nur auf dem Schirm."""

    def setUp(self):
        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "seitenkarte"
        )
        # Zweiter Abruf vortäuschen: Der erste bleibt absichtlich stumm.
        self.ablage.geholt_vermerken(self.projekt.id)

    def _lauf(self, rueckfrage):
        antwort = {"facebook": {"text": "Ein Text.", "schlagworte": "tuer",
                                "rueckfrage": rueckfrage}}
        with mock.patch.object(entwerfen, "inhalte_holen", return_value=[INHALT]), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True), \
             mock.patch("postkutsche.denker.schreiben", return_value=antwort):
            return entwerfen.entwerfen(
                self.ablage, "shop", ["facebook"], melden=lambda *a: None
            )

    def test_rueckfrage_wird_gespeichert(self):
        beitrag = self._lauf("Was leistet die Spindel genau?")[0]
        offen = self.ablage.rueckfragen(beitrag)
        self.assertEqual(len(offen), 1)
        self.assertIn("Spindel", offen[0]["rueckfrage"])

    def test_rueckfrage_blockiert_die_freigabe(self):
        # Der ganze Zweck: Was unklar ist, geht nicht ungeprüft raus.
        beitrag = self._lauf("Ist Steinau der Hersteller?")[0]
        self.assertEqual(self.ablage.beitrag(beitrag)["zustand"], BEITRAG_RUECKFRAGE)
        with self.assertRaises(RueckfrageOffen):
            self.ablage.freigeben(beitrag)

    def test_ohne_rueckfrage_freigebbar(self):
        beitrag = self._lauf(None)[0]
        self.assertEqual(self.ablage.rueckfragen(beitrag), [])
        self.ablage.freigeben(beitrag)


class PausiertesProjekt(unittest.TestCase):
    def test_wird_nicht_abgerufen(self):
        ablage = Ablage(":memory:")
        self.addCleanup(ablage.schliessen)
        ablage.projekt_anlegen("shop", "Shop", "https://shop.example", "seitenkarte")
        ablage.projekt_zustand("shop", "pausiert")
        with self.assertRaises(entwerfen.EntwurfFehler) as f:
            entwerfen.entwerfen(ablage, "shop", ["facebook"], melden=lambda *a: None)
        self.assertIn("pausiert", str(f.exception))


if __name__ == "__main__":
    unittest.main()
