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


class Wiederholungen(unittest.TestCase):
    """Was in den letzten vier Wochen dran war, wird gemeldet.

    Sonst bewirbt man im September dieselbe Tür wie im August, ohne es zu
    merken - bei einem Sortiment mit hundert Artikeln fällt das niemandem auf.
    """

    def setUp(self):
        from postkutsche import zeiten

        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "seitenkarte"
        )
        self.zeiten = zeiten

    def _beitrag_fuer(self, adresse, vor_tagen):
        from datetime import timedelta

        nummer, _ = self.ablage.inhalt_merken(
            self.projekt.id, adresse, "Eine Tür", adresse
        )
        wann = self.zeiten.schreiben(
            self.zeiten.lesen(self.zeiten.jetzt_utc()) - timedelta(days=vor_tagen)
        )
        return self.ablage.beitrag_anlegen(self.projekt.id, wann, inhalt_id=nummer)

    def test_kuerzlich_beworbenes_wird_gefunden(self):
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_1.html", 10)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_1.html", "titel": "Tür"}],
        )
        self.assertEqual(len(treffer), 1)
        self.assertIn("tuer_1", treffer[0]["adresse"])

    def test_aelteres_faellt_nicht_auf(self):
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_1.html", 60)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_1.html", "titel": "Tür"}],
        )
        self.assertEqual(treffer, [])

    def test_unbekanntes_produkt_ist_frei(self):
        from postkutsche import kampagnenlauf

        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/neu_9.html", "titel": "Neu"}],
        )
        self.assertEqual(treffer, [])

    def test_geplantes_zaehlt_mit(self):
        # Ein Produkt, das für nächste Woche schon eingeplant ist, soll nicht
        # ein zweites Mal drankommen, nur weil der Beitrag noch nicht raus ist.
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_2.html", -3)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_2.html", "titel": "Tür"}],
        )
        self.assertEqual(len(treffer), 1)

    def test_lauf_bricht_ab_und_fragt(self):
        from postkutsche import kampagnen, kampagnenlauf

        adresse = "https://shop.example/tuer_1.html"
        self._beitrag_fuer(adresse, 5)
        self.ablage.geholt_vermerken(self.projekt.id)
        k = kampagnen.Kampagne(thema="Probe", projekt="shop",
                               kalenderwoche=36, jahr=2026, je_tag=1)

        with mock.patch.object(kampagnenlauf, "produkte_sammeln",
                               return_value=[{"adresse": adresse, "titel": "Tür",
                                              "kategorie": "a"}]), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True):
            bericht = kampagnenlauf.ausfuehren(self.ablage, k)

        self.assertTrue(bericht["rueckfrage"])
        self.assertEqual(bericht["anzahl"], 0)
        self.assertEqual(len(bericht["wiederholungen"]), 1)
