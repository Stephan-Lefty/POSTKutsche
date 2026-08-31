"""Was der Webdienst beantwortet, ohne dass er dafuer laufen muss."""

import unittest
from types import SimpleNamespace
from unittest import mock

from postkutsche.quellen.abrufen import AbrufFehler
from postkutsche.web import dienst


def projekt(einstellungen, adresse="https://shop.example"):
    return SimpleNamespace(adresse=adresse, einstellungen=einstellungen)


def kategorie(pfad, produkte=1, name=None):
    """Ein Eintrag, wie ihn `seitenkarte.kategorien` liefert."""
    return {
        "adresse": f"http://shop.example{pfad}",
        "pfad": pfad.strip("/").rsplit("/", 1)[0],
        "tiefe": pfad.strip("/").count("/"),
        "name": name or pfad.strip("/").split("/")[-2],
        "nummer": None,
        "produkte": produkte,
    }


class KategorienHerkunft(unittest.TestCase):
    """Zwei Shopformen, zwei Herkuenfte - und keine Vermischung.

    Aus einer Seitenkarte laesst sich die Gliederung ablesen, weil der Pfad
    eines Produkts seine Kategorie nennt. Shopware legt Produkte flach ab;
    dort muessen die Kategorien von Hand genannt werden.
    """

    def setUp(self):
        # Kein Netzzugriff in Tests: Der Abgleich mit der Navigation ruft
        # sonst die Startseite ab.
        flicken = mock.patch("postkutsche.quellen.seitenkarte.verlinkte_kategorien",
                             return_value={})
        self.navigation = flicken.start()
        self.addCleanup(flicken.stop)

    def test_seitenkarte_wird_gelesen_wenn_nichts_vorgegeben_ist(self):
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[]) as gelesen:
            dienst.kategorien_des_projekts(
                projekt({"seitenkarte": "https://shop.example/sitemap.xml"}))
        gelesen.assert_called_once_with("https://shop.example/sitemap.xml", None)

    def test_ohne_angabe_wird_die_uebliche_seitenkarte_geraten(self):
        # Besser als ein Absturz auf None: /sitemap.xml ist der Ort, an dem
        # sie in neun von zehn Faellen liegt.
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[]) as gelesen:
            dienst.kategorien_des_projekts(projekt({}))
        gelesen.assert_called_once_with("https://shop.example/sitemap.xml", None)

    def test_vorgabe_sticht_die_seitenkarte(self):
        vorgaben = ["https://shop.example/Fenstersicherung/"]
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien") as karte, \
             mock.patch("postkutsche.quellen.seitenkarte.vorgegebene_kategorien",
                        return_value=[]) as vorgabe:
            dienst.kategorien_des_projekts(projekt({
                "seitenkarte": "https://shop.example/sitemap.xml",
                "kategorien": vorgaben,
            }))
        vorgabe.assert_called_once_with(vorgaben)
        karte.assert_not_called()

    def test_bereich_schraenkt_auch_vorgaben_ein(self):
        alle = [{"pfad": "Fenstersicherung", "adresse": "a"},
                {"pfad": "Tuersicherung", "adresse": "b"}]
        with mock.patch("postkutsche.quellen.seitenkarte.vorgegebene_kategorien",
                        return_value=alle):
            gefunden, _ = dienst.kategorien_des_projekts(
                projekt({"kategorien": ["a", "b"]}), "Tuer")
        self.assertEqual([k["pfad"] for k in gefunden], ["Tuersicherung"])

    def test_vorgaben_werden_nicht_abgeglichen(self):
        # Die Vorgaben kommen vom Benutzer. Er hat nachgesehen, wir nicht -
        # und ein Abgleich wuerde sie alle wegwerfen, weil eine
        # Shopware-Startseite keine list.html verlinkt.
        with mock.patch("postkutsche.quellen.seitenkarte.vorgegebene_kategorien",
                        return_value=[{"pfad": "a", "adresse": "a"}]):
            dienst.kategorien_des_projekts(projekt({"kategorien": ["a"]}))
        self.navigation.assert_not_called()


class AbgleichImDienst(unittest.TestCase):
    """Die Seitenkarte ist ein Versprechen, die Navigation ist der Bestand."""

    ALLE = [kategorie("/shop-tueren/haustueren_1/list.html", 9),
            kategorie("/shop-tueren/passivhaustueren_2/list.html", 40)]

    def _laufen_lassen(self, verlinkt, gemeldet=None):
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[dict(k) for k in self.ALLE]), \
             mock.patch("postkutsche.quellen.seitenkarte.verlinkte_kategorien",
                        return_value=verlinkt):
            return dienst.kategorien_des_projekts(
                projekt({}), melden=gemeldet or (lambda *_: None))

    def test_was_nicht_verlinkt_ist_faellt_weg(self):
        gefunden, _ = self._laufen_lassen(
            {"/shop-tueren/haustueren_1/list.html": "Haustüren"})
        self.assertEqual([k["name"] for k in gefunden], ["Haustüren"])

    def test_der_hinweis_nennt_zahl_und_beispiel(self):
        _, hinweis = self._laufen_lassen(
            {"/shop-tueren/haustueren_1/list.html": "Haustüren"})
        self.assertIn("1 von 2", hinweis)
        # Nach Produktzahl sortiert: Was die Karte gross macht, vermisst man
        # am ehesten.
        self.assertIn("passivhaustueren_2", hinweis)

    def test_der_hinweis_steht_auch_im_protokoll(self):
        gesagt = []
        self._laufen_lassen({"/shop-tueren/haustueren_1/list.html": "H"},
                            gemeldet=gesagt.append)
        self.assertEqual(len(gesagt), 1)

    def test_ohne_verlust_kein_hinweis(self):
        _, hinweis = self._laufen_lassen({
            "/shop-tueren/haustueren_1/list.html": "Haustüren",
            "/shop-tueren/passivhaustueren_2/list.html": "Passivhaustüren",
        })
        self.assertIsNone(hinweis)

    def test_unerreichbare_startseite_wirft_nichts_weg(self):
        # Lieber zu viel anbieten als das Formular leer lassen. Aber sagen,
        # dass nicht geprueft wurde.
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[dict(k) for k in self.ALLE]), \
             mock.patch("postkutsche.quellen.seitenkarte.verlinkte_kategorien",
                        side_effect=AbrufFehler("antwortet nicht")):
            gefunden, hinweis = dienst.kategorien_des_projekts(projekt({}))
        self.assertEqual(len(gefunden), 2)
        self.assertIn("Ungeprüft", hinweis)

    def test_eigene_navigationsadresse_wird_genommen(self):
        with mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[]), \
             mock.patch("postkutsche.quellen.seitenkarte.verlinkte_kategorien",
                        return_value={}) as navigation:
            dienst.kategorien_des_projekts(
                projekt({"navigation": "https://shop.example/shop/"}))
        navigation.assert_called_once_with("https://shop.example/shop/")
