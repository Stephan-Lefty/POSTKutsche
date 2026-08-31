"""Was der Webdienst beantwortet, ohne dass er dafuer laufen muss."""

import unittest
from types import SimpleNamespace
from unittest import mock

from postkutsche.web import dienst


def projekt(einstellungen, adresse="https://shop.example"):
    return SimpleNamespace(adresse=adresse, einstellungen=einstellungen)


class KategorienHerkunft(unittest.TestCase):
    """Zwei Shopformen, zwei Herkuenfte - und keine Vermischung.

    Aus einer Seitenkarte laesst sich die Gliederung ablesen, weil der Pfad
    eines Produkts seine Kategorie nennt. Shopware legt Produkte flach ab;
    dort muessen die Kategorien von Hand genannt werden.
    """

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
            gefunden = dienst.kategorien_des_projekts(
                projekt({"kategorien": ["a", "b"]}), "Tuer")
        self.assertEqual([k["pfad"] for k in gefunden], ["Tuersicherung"])
