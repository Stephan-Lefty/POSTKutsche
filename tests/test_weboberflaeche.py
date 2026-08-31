"""Was der Webdienst beantwortet, ohne dass er dafuer laufen muss."""

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from postkutsche import zeiten
from postkutsche.quellen.abrufen import AbrufFehler
from postkutsche.web import dienst


def projekt(einstellungen, adresse="https://shop.example", kennung="shop"):
    return SimpleNamespace(adresse=adresse, einstellungen=einstellungen,
                           kennung=kennung)


def kategorie(pfad, produkte=1, name=None, tiefe=2):
    """Ein Eintrag, wie ihn `seitenkarte.navigation` liefert."""
    ohne_liste = pfad.strip("/").rsplit("/", 1)[0]
    return {
        "adresse": f"https://shop.example{pfad}",
        "pfad": ohne_liste,
        "tiefe": tiefe,
        "name": name or ohne_liste.split("/")[-1],
        "nummer": None,
        "produkte": produkte,
    }


class OhneSpeicher(unittest.TestCase):
    """Gemeinsames Geruest: eigener Zwischenspeicher, kein Netz, kein Reden."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.datei = Path(self.ordner.name) / "bestand.json"
        self.gesagt = []

    def _laufen_lassen(self, projekt_, bereich=None, **mehr):
        return dienst.kategorien_des_projekts(
            projekt_, bereich, melden=self.gesagt.append,
            speicher=self.datei, **mehr)


class KategorienHerkunft(OhneSpeicher):
    """Zwei Shopformen, zwei Herkuenfte - und keine Vermischung.

    Bei Shopware nennt der Benutzer die Kategorien, weil die Produkte flach
    abgelegt sind. Sonst zaehlt, was die Seite selbst verlinkt.
    """

    def test_vorgabe_sticht_die_navigation(self):
        vorgaben = ["https://shop.example/Fenstersicherung/"]
        with mock.patch("postkutsche.quellen.seitenkarte.navigation") as gelaufen, \
             mock.patch("postkutsche.quellen.seitenkarte.vorgegebene_kategorien",
                        return_value=[]) as vorgabe:
            self._laufen_lassen(projekt({"kategorien": vorgaben}))
        vorgabe.assert_called_once_with(vorgaben)
        # Die Vorgaben kommen vom Benutzer. Er hat nachgesehen, wir nicht -
        # und eine Shopware-Startseite verlinkt keine list.html, es bliebe
        # nichts uebrig.
        gelaufen.assert_not_called()

    def test_bereich_schraenkt_auch_vorgaben_ein(self):
        alle = [{"pfad": "Fenstersicherung", "adresse": "a"},
                {"pfad": "Tuersicherung", "adresse": "b"}]
        with mock.patch("postkutsche.quellen.seitenkarte.vorgegebene_kategorien",
                        return_value=alle):
            gefunden, _ = self._laufen_lassen(
                projekt({"kategorien": ["a", "b"]}), "Tuer")
        self.assertEqual([k["pfad"] for k in gefunden], ["Tuersicherung"])

    def test_ohne_vorgabe_wird_die_navigation_gelesen(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])) as gelaufen:
            self._laufen_lassen(projekt({}))
        gelaufen.assert_called_once_with("https://shop.example")

    def test_eigene_navigationsadresse_wird_genommen(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])) as gelaufen:
            self._laufen_lassen(projekt({"navigation": "https://shop.example/shop/"}))
        gelaufen.assert_called_once_with("https://shop.example/shop/")


class BereicheUndFilter(OhneSpeicher):
    """Die Bereiche sind das Auswahlfeld oben, nicht die Liste unten."""

    ALLE = [kategorie("/shop-tueren/list.html", 1646, "Türen Shop", tiefe=1),
            kategorie("/shop-tueren/kellertueren_525/list.html", 8, "Kellertüren"),
            kategorie("/shop-zubehoer/hochwasserschutz_715/list.html", 1,
                      "Hochwasserschutz")]

    def _mit(self, bereich=None):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([dict(k) for k in self.ALLE], [])):
            return self._laufen_lassen(projekt({}), bereich)

    def test_uebersichtsseiten_stehen_nicht_in_der_liste(self):
        # »Tueren Shop« meldete 1646 Produkte und lieferte keines. Wer sie
        # ankreuzt, plant eine leere Woche.
        gefunden, _ = self._mit()
        self.assertEqual([k["name"] for k in gefunden],
                         ["Kellertüren", "Hochwasserschutz"])

    def test_bereich_filtert_die_liste(self):
        gefunden, _ = self._mit("shop-tueren")
        self.assertEqual([k["name"] for k in gefunden], ["Kellertüren"])


class BestandAusDerNavigation(OhneSpeicher):
    """Die Navigation ist die Quelle, die Seitenkarte nur der Rueckfall."""

    def test_der_hinweis_nennt_zahl_und_dauer(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([kategorie("/a/b/list.html")], [])):
            _, hinweis = self._laufen_lassen(projekt({}))
        self.assertIn("1 Kategorien", hinweis)
        self.assertIn("Sekunden", hinweis)

    def test_ausgelassenes_wird_genannt(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([kategorie("/a/b/list.html")],
                                      ["Abholgebiet Raum Gotha"])):
            _, hinweis = self._laufen_lassen(projekt({}))
        self.assertIn("Ausgelassen: 1", hinweis)

    def test_der_hinweis_steht_auch_im_protokoll(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])):
            self._laufen_lassen(projekt({}))
        self.assertEqual(len(self.gesagt), 1)

    def test_stumme_seite_faellt_auf_die_seitenkarte_zurueck(self):
        # Lieber die veraltete Karte als ein leeres Formular - aber mit der
        # Ansage, dass die Liste nicht stimmen muss.
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        side_effect=AbrufFehler("antwortet nicht")), \
             mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[kategorie("/a/b/list.html")]) as karte:
            gefunden, hinweis = self._laufen_lassen(
                projekt({"seitenkarte": "https://shop.example/sitemap.xml"}))
        karte.assert_called_once_with("https://shop.example/sitemap.xml")
        self.assertEqual(len(gefunden), 1)
        self.assertIn("nicht mehr gibt", hinweis)

    def test_ohne_angabe_wird_die_uebliche_seitenkarte_geraten(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        side_effect=AbrufFehler("stumm")), \
             mock.patch("postkutsche.quellen.seitenkarte.kategorien",
                        return_value=[]) as karte:
            self._laufen_lassen(projekt({}))
        karte.assert_called_once_with("https://shop.example/sitemap.xml")


class Zwischenspeicher(OhneSpeicher):
    """130 Abrufe bei jedem Oeffnen des Formulars waeren nicht zumutbar."""

    def _einmal_erheben(self):
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([kategorie("/a/b/list.html")], [])) as lauf:
            self._laufen_lassen(projekt({}))
        return lauf

    def test_der_zweite_aufruf_geht_ohne_abruf(self):
        self._einmal_erheben()
        with mock.patch("postkutsche.quellen.seitenkarte.navigation") as lauf:
            gefunden, hinweis = self._laufen_lassen(projekt({}))
        lauf.assert_not_called()
        self.assertEqual(len(gefunden), 1)
        # Aus dem Speicher gibt es nichts zu erzaehlen.
        self.assertIsNone(hinweis)

    def test_abgelaufenes_wird_neu_geholt(self):
        gestern = zeiten.schreiben(
            zeiten.lesen(zeiten.jetzt_utc()) - timedelta(hours=13))
        self.datei.write_text(json.dumps(
            {"gespeichert": gestern, "kategorien": [kategorie("/a/b/list.html")]}),
            encoding="utf-8")
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])) as lauf:
            self._laufen_lassen(projekt({}))
        lauf.assert_called_once()

    def test_ein_stempel_aus_der_zukunft_gilt_nicht(self):
        # Nach einer verstellten Uhr bliebe die Liste sonst fuer immer stehen.
        kuenftig = zeiten.schreiben(
            zeiten.lesen(zeiten.jetzt_utc()) + timedelta(days=3))
        self.datei.write_text(json.dumps(
            {"gespeichert": kuenftig, "kategorien": [kategorie("/a/b/list.html")]}),
            encoding="utf-8")
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])) as lauf:
            self._laufen_lassen(projekt({}))
        lauf.assert_called_once()

    def test_kaputter_speicher_ist_kein_fehler(self):
        # Ein Zwischenspeicher darf nie der Grund sein, warum etwas nicht geht.
        self.datei.write_text("{kein json", encoding="utf-8")
        with mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([], [])) as lauf:
            self._laufen_lassen(projekt({}))
        lauf.assert_called_once()

    def test_unschreibbarer_speicher_ist_kein_fehler(self):
        nicht_schreibbar = Path(self.ordner.name) / "fehlt" / "tief" / "x.json"
        with mock.patch.object(Path, "mkdir", side_effect=OSError("voll")), \
             mock.patch("postkutsche.quellen.seitenkarte.navigation",
                        return_value=([kategorie("/a/b/list.html")], [])):
            gefunden, _ = dienst.kategorien_des_projekts(
                projekt({}), melden=self.gesagt.append, speicher=nicht_schreibbar)
        self.assertEqual(len(gefunden), 1)

    def test_je_projekt_eine_eigene_datei(self):
        self.assertNotEqual(dienst._bestandsdatei("habefa"),
                            dienst._bestandsdatei("naturlust"))
