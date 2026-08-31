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


class ProdukteEinerKategorie(unittest.TestCase):
    """Shopware legt Produkte flach ab, nicht unter der Kategorie."""

    SEITE = """
      <a href="/Fenstersicherung/">Kategorie</a>
      <a href="/ADE-Sicherungsstange-S/ADE-S">Stange</a>
      <a href="/ADE-Sicherungsstange-S/ADE-S"><img></a>
      <a href="/ADE-Verbindungsplatte/ADE-VP-Z20">Platte</a>
      <a href="/account/profile">Mein Profil</a>
      <a href="/Rechtliches/Versand-Zahlungen/">Versand</a>
      <a href="https://fremd.example/Ding/X1">fremd</a>
      <a href="/Angebote">flach</a>
    """

    def _lesen(self):
        from unittest import mock
        with mock.patch.object(seitenkarte, "text_holen",
                               return_value=self.SEITE):
            return seitenkarte.produkte_der_kategorie(
                "https://x.example/Fenstersicherung/")

    def test_findet_die_produkte(self):
        self.assertEqual(self._lesen(), [
            "https://x.example/ADE-Sicherungsstange-S/ADE-S",
            "https://x.example/ADE-Verbindungsplatte/ADE-VP-Z20",
        ])

    def test_zaehlt_dieselbe_kachel_nur_einmal(self):
        # Bild und Titel verweisen auf dasselbe Produkt.
        self.assertEqual(len(self._lesen()), 2)

    def test_kontoseiten_sind_keine_produkte(self):
        # Ohne die Sperre stuenden »Profil« und »Adressen« in jeder Kategorie.
        self.assertNotIn("https://x.example/account/profile", self._lesen())

    def test_fremde_adressen_bleiben_draussen(self):
        self.assertFalse([a for a in self._lesen() if "fremd.example" in a])

    def test_eine_ebene_ist_keine_produktadresse(self):
        # /Angebote ist eine Uebersicht, kein Artikel.
        self.assertNotIn("https://x.example/Angebote", self._lesen())
