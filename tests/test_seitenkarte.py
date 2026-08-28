"""Seiten ohne Schnittstelle: was aus einer alten Seitenkarte zu holen ist."""

import unittest

from postkutsche.quellen import seitenkarte


class FortgezogeneAdressen(unittest.TestCase):
    """Eine Seitenkarte, die zehn Jahre nicht gepflegt wurde, luegt."""

    def test_umleitung_auf_uebersicht_ist_kein_produkt(self):
        for ziel in ("https://x.example/kat_486/list.html",
                     "https://x.example/errordoc/404.html"):
            with self.subTest(ziel=ziel):
                self.assertTrue(seitenkarte._ist_keine_produktseite(ziel))

    def test_echte_produktadresse_bleibt(self):
        self.assertFalse(seitenkarte._ist_keine_produktseite(
            "https://x.example/kat_486/tuer_1810.html"))

    def test_fliesstext_nimmt_absaetze_nur_einmal(self):
        # Verschachtelung: derselbe Absatz steckt in zwei divs. Wer die divs
        # liest statt der Blaetter, hat ihn doppelt.
        satz = "Feuerhemmend nach DIN 4102, rauchdicht nach DIN 18095. " * 2
        roh = f"<div><div><p>{satz}</p></div></div><p>{satz}</p>"
        self.assertEqual(seitenkarte._fliesstext(roh).count("DIN 4102"), 2)

    def test_fliesstext_ueberspringt_schaltflaechen(self):
        self.assertEqual(seitenkarte._fliesstext("<p>In den Warenkorb</p>"), "")

    def test_fliesstext_haelt_die_grenze_ein(self):
        roh = "<p>" + ("a" * 500 + "</p><p>") * 40 + "</p>"
        self.assertLessEqual(len(seitenkarte._fliesstext(roh)),
                             seitenkarte.TEXTGRENZE)
