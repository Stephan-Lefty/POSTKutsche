"""Seiten ohne Schnittstelle: was aus einer alten Seitenkarte zu holen ist."""

import unittest
from unittest import mock

from postkutsche.quellen import seitenkarte
from postkutsche.quellen.abrufen import AbrufFehler


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
      <a href="/page/cms/018ecf08670770a1a802dafa0da91c97">Datenschutz</a>
      <a href="/Rechtliches/Versand-Zahlungen/">Versand</a>
      <a href="https://fremd.example/Ding/X1">fremd</a>
      <a href="/Angebote">flach</a>
    """

    def _lesen(self):
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

    def test_inhaltsseiten_aus_dem_fussbereich_bleiben_draussen(self):
        # »/page/cms/<Kennung>« ist nach der Adressform ein lupenreines
        # Produkt: drei Ebenen, kein Schraegstrich am Ende.
        self.assertFalse([a for a in self._lesen() if "/page/cms" in a])

    def test_fremde_adressen_bleiben_draussen(self):
        self.assertFalse([a for a in self._lesen() if "fremd.example" in a])

    def test_eine_ebene_ist_keine_produktadresse(self):
        # /Angebote ist eine Uebersicht, kein Artikel.
        self.assertNotIn("https://x.example/Angebote", self._lesen())

    def test_zweitname_zeigt_auf_dieselbe_funktion(self):
        # produkte_der_kategorie ist seit dem Zusammenlegen nur noch ein
        # Zweitname. Wer den Zweitnamen aendert, ohne es zu merken, sieht es
        # hier.
        self.assertIs(seitenkarte.produkte_der_kategorie, seitenkarte.kategorie)


class ZweiShopformen(unittest.TestCase):
    """Eine Funktion, zwei Adressformen - entschieden wird an der Adresse.

    Der Eigenbau nennt seine Produkte »..._<Artikelnummer>.html«, Shopware
    haengt die Artikelnummer als eigene Pfadebene an. Beides muss dieselbe
    Funktion erkennen, ohne dass die eine Regel die andere verunreinigt.
    """

    EIGENBAU = """
      <a href="/shop-tueren/brandschutz_489/t30_stahl_1810.html">Tuer</a>
      <a href="/shop-tueren/brandschutz_489/t30_holz_1811.html">Tuer</a>
      <a href="/shop-tueren/brandschutz_489/t30_holz_1811.html"><img></a>
      <a href="/shop-tueren/brandschutz_490/list.html">Unterkategorie</a>
      <a href="/info_service/versandkosten.html">Versandkosten</a>
      <a href="/info_service/impressum.html">Impressum</a>
    """

    UEBERSICHT = """
      <a href="/shop-garagentore/antriebe_542/list.html">Antriebe</a>
      <a href="/info_service/versandkosten.html">Versandkosten</a>
    """

    def _lesen(self, roh, adresse):
        with mock.patch.object(seitenkarte, "text_holen", return_value=roh):
            return seitenkarte.kategorie(adresse)

    def test_eigenbau_nimmt_nur_die_artikelnummern(self):
        self.assertEqual(
            self._lesen(self.EIGENBAU,
                        "https://x.example/shop-tueren/brandschutz_489/list.html"),
            ["https://x.example/shop-tueren/brandschutz_489/t30_stahl_1810.html",
             "https://x.example/shop-tueren/brandschutz_489/t30_holz_1811.html"],
        )

    def test_versandkosten_bleiben_draussen(self):
        # »/info_service/versandkosten.html« erfuellt die Shopware-Regel
        # muehelos: zwei Ebenen, kein Schraegstrich am Ende. Wuerde beim
        # Eigenbau auch nur ersatzweise danach gesucht, staende die Seite in
        # der Kampagne.
        gefunden = self._lesen(
            self.EIGENBAU,
            "https://x.example/shop-tueren/brandschutz_489/list.html")
        self.assertFalse([a for a in gefunden if "info_service" in a])

    def test_leere_uebersicht_bleibt_leer(self):
        # Eine Kategorie der obersten Ebene hat kein eigenes Produkt. Das ist
        # kein Fehler und darf nicht mit Beiwerk aufgefuellt werden.
        self.assertEqual(
            self._lesen(self.UEBERSICHT,
                        "https://x.example/shop-garagentore/list.html"), [])

    def test_shopware_wird_an_der_adresse_erkannt(self):
        # Dieselbe Funktion, Adresse ohne ».html« - jetzt gilt die andere Regel.
        self.assertEqual(
            self._lesen(ProdukteEinerKategorie.SEITE,
                        "https://x.example/Fenstersicherung/"),
            ["https://x.example/ADE-Sicherungsstange-S/ADE-S",
             "https://x.example/ADE-Verbindungsplatte/ADE-VP-Z20"],
        )

    def test_schieber_ueber_der_liste_zaehlen_nicht_mit(self):
        # Shopware stellt ueber die Produktliste Schieber mit Empfehlungen -
        # Produkte aus dem ganzen Shop. Am 2026-08-31 nachgezaehlt: eine
        # Kategorie mit drei Produkten meldete elf. Weil die Schieber oben
        # stehen, waeren genau die falschen in der Kampagne gelandet.
        roh = f"""
          <a href="/Empfehlung/EMP-1">Schieber</a>
          <div class="{seitenkarte.LISTENBAUSTEIN}">
            <a href="/ADE-Stange/ADE-S">Stange</a>
          </div>
        """
        self.assertEqual(self._lesen(roh, "https://x.example/Fenstersicherung/"),
                         ["https://x.example/ADE-Stange/ADE-S"])

    def test_ohne_listenbaustein_bleibt_die_ganze_seite(self):
        # Lieber zu viel finden als eine Kategorie faelschlich fuer leer
        # erklaeren.
        roh = '<a href="/ADE-Stange/ADE-S">Stange</a>'
        self.assertEqual(self._lesen(roh, "https://x.example/Fenstersicherung/"),
                         ["https://x.example/ADE-Stange/ADE-S"])

    def test_der_eigenbau_wird_nicht_zugeschnitten(self):
        # Der Baustein ist eine Shopware-Sache. Ein Eigenbau, der das Wort
        # zufaellig irgendwo stehen haette, duerfte davon nichts merken.
        roh = (f'<a href="/kat_1/a_1.html">A</a><div class="{seitenkarte.LISTENBAUSTEIN}">'
               f'<a href="/kat_1/b_2.html">B</a></div>')
        self.assertEqual(len(self._lesen(roh, "https://x.example/kat_1/list.html")), 2)

    def test_grenze_wird_eingehalten(self):
        roh = "".join(f'<a href="/kat_1/artikel_{n}.html">A</a>' for n in range(50))
        gefunden = self._lesen(roh, "https://x.example/kat_1/list.html")
        self.assertEqual(len(gefunden), 50)
        with mock.patch.object(seitenkarte, "text_holen", return_value=roh):
            self.assertEqual(
                len(seitenkarte.kategorie("https://x.example/kat_1/list.html", 5)), 5)


class VorgegebeneKategorien(unittest.TestCase):
    """Wo die Seitenkarte die Zugehoerigkeit nicht verraet, nennt man sie."""

    SEITE = """
      <a href="/ADE-Stange/ADE-S">Stange</a>
      <a href="/ADE-Platte/ADE-VP">Platte</a>
    """

    def _lesen(self, vorgaben):
        with mock.patch.object(seitenkarte, "text_holen", return_value=self.SEITE):
            return seitenkarte.vorgegebene_kategorien(vorgaben)

    def test_zaehlt_die_produkte_der_seite(self):
        eintraege = self._lesen(["https://x.example/Fenstersicherung/"])
        self.assertEqual(eintraege[0]["produkte"], 2)

    def test_name_kommt_aus_der_adresse(self):
        eintraege = self._lesen(["https://x.example/Tuersicherung/"])
        self.assertEqual(eintraege[0]["name"], "Türsicherung")

    def test_bindestriche_werden_zu_worten(self):
        eintraege = self._lesen(["https://x.example/Duesen-und-Adapter/"])
        self.assertEqual(eintraege[0]["name"], "Düsen und Adapter")

    def test_eigener_name_sticht_die_adresse(self):
        eintraege = self._lesen([
            {"adresse": "https://x.example/Zubehoer/", "name": "Kleinkram"}])
        self.assertEqual(eintraege[0]["name"], "Kleinkram")

    def test_tiefe_ist_nie_null(self):
        # Die Oberflaeche rueckt nach »tiefe - 1« ein und kaeme sonst auf
        # einen negativen Abstand.
        eintraege = self._lesen(["https://x.example/Zubehoer/"])
        self.assertGreaterEqual(int(eintraege[0]["tiefe"]), 1)

    def test_stumme_kategorie_verschwindet_nicht(self):
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=AbrufFehler("antwortet nicht")):
            eintraege = seitenkarte.vorgegebene_kategorien(
                ["https://x.example/Weg/"])
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["produkte"], 0)
        self.assertIn("antwortet nicht", str(eintraege[0]["fehler"]))
