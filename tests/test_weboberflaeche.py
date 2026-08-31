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


class WissenImDienst(unittest.TestCase):
    """Antworten enden nicht mehr beim einzelnen Beitrag.

    Vorher wurde die Antwort am Beitrag vermerkt, und das war alles - beim
    naechsten Produkt derselben Art kam dieselbe Frage wieder.
    """

    def setUp(self):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)

        # Der Behandler baut sich seine Ablage je Anfrage neu. Eine Datei
        # muss es deshalb sein - mit ":memory:" bekaeme jeder Aufruf eine
        # frische, leere Datenbank.
        pfad = Path(ordner.name) / "p.db"
        vorher = dienst.Behandler.ablage_pfad
        dienst.Behandler.ablage_pfad = pfad
        self.addCleanup(setattr, dienst.Behandler, "ablage_pfad", vorher)

        self.gesendet = []
        for name, was in (("_json", lambda _s, d, code=200: self.gesendet.append(d)),
                          ("_fehler", lambda _s, t, code=400:
                           self.gesendet.append({"fehler": t, "code": code}))):
            flicken = mock.patch.object(dienst.Behandler, name, was)
            flicken.start()
            self.addCleanup(flicken.stop)

        self.behandler = object.__new__(dienst.Behandler)

        from postkutsche.ablage import Ablage
        self.Ablage = Ablage
        with Ablage(pfad) as a:
            projekt = a.projekt_anlegen("shop", "Shop", "https://shop.example",
                                        "seitenkarte")
            self.projekt_id = projekt.id
            nummer, _ = a.inhalt_merken(projekt.id, "t1", "Eine Tür",
                                        "https://shop.example/tuer_1.html")
            beitrag = a.beitrag_anlegen(projekt.id, "2026-09-01T08:00:00Z",
                                        inhalt_id=nummer)
            a.fassung_setzen(beitrag, "mastodon", "Ein Text.", "",
                             rueckfrage="Soll die Lieferzeit in den Text?")
            self.fassung_id = int(a.fassungen(beitrag)[0]["id"])
        self.pfad = pfad

    def _antworten(self, antwort="Nein, nie.", allgemein=False):
        nachgebessert = {"text": "Besser.", "schlagworte": "", "rueckfrage": None}
        with mock.patch("postkutsche.denker.nachbessern",
                        return_value=nachgebessert):
            self.behandler._antwort({"fassung": self.fassung_id,
                                     "antwort": antwort,
                                     "allgemein": allgemein})
        return self.gesendet[-1]

    def _gesammelt(self):
        with self.Ablage(self.pfad) as a:
            return a.wissen_alles(self.projekt_id)

    def test_die_antwort_wird_gemerkt(self):
        ergebnis = self._antworten()
        self.assertTrue(ergebnis["gemerkt"])
        gesammelt = self._gesammelt()
        self.assertEqual(len(gesammelt), 1)
        self.assertEqual(gesammelt[0]["antwort"], "Nein, nie.")
        self.assertEqual(gesammelt[0]["frage"], "Soll die Lieferzeit in den Text?")

    def test_ohne_schalter_gilt_es_nur_fuer_das_produkt(self):
        # Die harmlosere Annahme: Eine falsch verallgemeinerte Regel steht bei
        # jedem kuenftigen Entwurf im Weg.
        self._antworten(allgemein=False)
        self.assertEqual(self._gesammelt()[0]["adresse"],
                         "https://shop.example/tuer_1.html")

    def test_mit_schalter_gilt_es_fuer_das_projekt(self):
        self._antworten(allgemein=True)
        self.assertEqual(self._gesammelt()[0]["adresse"], "")

    def test_der_vermerk_am_beitrag_bleibt(self):
        # Er erklaert den einzelnen Beitrag; die Sammlung erklaert das Projekt.
        # Das eine ersetzt das andere nicht.
        self._antworten()
        with self.Ablage(self.pfad) as a:
            notiz = a.db.execute("SELECT notiz FROM beitraege").fetchone()[0]
        self.assertIn("Nein, nie.", notiz)

    def test_die_liste_zeigt_was_in_die_anweisung_geht(self):
        self._antworten(allgemein=True)
        self.behandler._wissen({"projekt": ["shop"]})
        daten = self.gesendet[-1]
        self.assertEqual(len(daten["eintraege"]), 1)
        self.assertTrue(daten["eintraege"][0]["allgemein"])
        self.assertTrue(daten["eintraege"][0]["in_anweisung"])

    def test_produktwissen_geht_nicht_in_jede_anweisung(self):
        self._antworten(allgemein=False)
        self.behandler._wissen({"projekt": ["shop"]})
        eintrag = self.gesendet[-1]["eintraege"][0]
        self.assertFalse(eintrag["allgemein"])
        self.assertFalse(eintrag["in_anweisung"])

    def test_streichen_geht(self):
        self._antworten(allgemein=True)
        nummer = int(self._gesammelt()[0]["id"])
        self.behandler._wissen_streichen({"wissen": nummer})
        self.assertEqual(self._gesammelt(), [])

    def test_streichen_eines_unbekannten_meldet_sich(self):
        self.behandler._wissen_streichen({"wissen": 9999})
        self.assertEqual(self.gesendet[-1]["code"], 404)

    def test_unbekanntes_projekt_meldet_sich(self):
        self.behandler._wissen({"projekt": ["gibtsnicht"]})
        self.assertEqual(self.gesendet[-1]["code"], 404)


class BilderImDienst(unittest.TestCase):
    """Ablegen, wo der Benutzer sie findet - und zwei je Beitrag."""

    def setUp(self):
        import os
        from postkutsche.ablage import Ablage

        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.heim = Path(ordner.name)

        os.environ["POSTKUTSCHE_DOKUMENTE"] = str(self.heim / "Dokumente")
        self.addCleanup(os.environ.pop, "POSTKUTSCHE_DOKUMENTE", None)

        db = self.heim / "p.db"
        vorher = dienst.Behandler.ablage_pfad
        dienst.Behandler.ablage_pfad = db
        self.addCleanup(setattr, dienst.Behandler, "ablage_pfad", vorher)

        self.gesendet = []
        for name, was in (("_json", lambda _s, d, code=200: self.gesendet.append(d)),
                          ("_fehler", lambda _s, t, code=400:
                           self.gesendet.append({"fehler": t, "code": code}))):
            flicken = mock.patch.object(dienst.Behandler, name, was)
            flicken.start()
            self.addCleanup(flicken.stop)
        self.behandler = object.__new__(dienst.Behandler)

        self.eins = self.heim / "eins.jpg"
        self.zwei = self.heim / "zwei.jpg"
        self.eins.write_bytes(b"erstes")
        self.zwei.write_bytes(b"zweites")

        self.Ablage = Ablage
        self.db = db
        with Ablage(db) as a:
            projekt = a.projekt_anlegen("habefa", "HaBeFa", "https://h.example",
                                        "seitenkarte")
            nummer, _ = a.inhalt_merken(projekt.id, "t1", "T30-2 Brandschutztür",
                                        "https://h.example/t.html")
            beitrag = a.beitrag_anlegen(projekt.id, "2026-09-01T08:00:00Z",
                                        inhalt_id=nummer)
            self.fassung = a.fassung_setzen(beitrag, "facebook", "Text",
                                            bild_pfad=str(self.eins))

    def _zweites_setzen(self):
        with self.Ablage(self.db) as a:
            a.db.execute("UPDATE fassungen SET bild_pfad2 = ? WHERE id = ?",
                         (str(self.zwei), self.fassung))
            a.db.commit()

    def test_ein_bild_wird_abgelegt(self):
        self.behandler._ablegen({"fassung": self.fassung})
        daten = self.gesendet[-1]
        self.assertEqual(len(daten["dateien"]), 1)
        self.assertTrue(Path(daten["dateien"][0]).is_file())

    def test_der_ordner_nennt_woche_und_projekt(self):
        self.behandler._ablegen({"fassung": self.fassung})
        ordner = Path(self.gesendet[-1]["ordner"])
        self.assertEqual(ordner.name, "habefa")
        self.assertEqual(ordner.parent.name, "2026-KW36")

    def test_beide_bilder_werden_abgelegt(self):
        self._zweites_setzen()
        self.behandler._ablegen({"fassung": self.fassung})
        dateien = self.gesendet[-1]["dateien"]
        self.assertEqual(len(dateien), 2)
        # Die Reihenfolge steht im Namen: Wer sie von Hand einfuegt, braucht
        # sie in der richtigen Folge.
        self.assertTrue(dateien[0].endswith("-1.jpg"))
        self.assertTrue(dateien[1].endswith("-2.jpg"))

    def test_ohne_bild_gibt_es_nichts_abzulegen(self):
        with self.Ablage(self.db) as a:
            a.db.execute("UPDATE fassungen SET bild_pfad = NULL WHERE id = ?",
                         (self.fassung,))
            a.db.commit()
        self.behandler._ablegen({"fassung": self.fassung})
        self.assertEqual(self.gesendet[-1]["code"], 404)

    def test_unbekannte_fassung_meldet_sich(self):
        self.behandler._ablegen({"fassung": 9999})
        self.assertEqual(self.gesendet[-1]["code"], 404)

    def test_zweites_bild_laesst_sich_entfernen(self):
        self._zweites_setzen()
        self.behandler._bild_weg({"fassung": self.fassung, "nummer": 2})
        with self.Ablage(self.db) as a:
            zeile = a.db.execute("SELECT * FROM fassungen WHERE id = ?",
                                 (self.fassung,)).fetchone()
        self.assertIsNone(zeile["bild_pfad2"])
        # Das erste bleibt.
        self.assertEqual(zeile["bild_pfad"], str(self.eins))

    def test_der_ordnerknopf_nennt_den_pfad(self):
        # Auch wenn kein xdg-open da ist, muss der Pfad kommen - sonst weiss
        # der Benutzer nicht, wohin er greifen soll.
        with mock.patch("postkutsche.bilder.ordner_zeigen", return_value=False):
            self.behandler._ordner_zeigen({})
        daten = self.gesendet[-1]
        self.assertFalse(daten["geoeffnet"])
        self.assertTrue(daten["ordner"].endswith("POSTKutsche"))


class LaufSperre(unittest.TestCase):
    """Eine Sperre, die niemand loesen kann, ist schlimmer als zwei Laeufe.

    Der Benutzer meldete: »es wird mir gesagt, es ist eine Planung bereits
    aktiv«. Ursache war, dass der Lauf nach dem Schliessen des Fensters
    weiterlief - dagegen hilft das Abbrechen. Bleibt trotzdem etwas haengen,
    darf »Woche planen« nicht bis zum Neustart des Dienstes gesperrt sein.
    """

    def setUp(self):
        vorher = dict(dienst.Behandler.lauf)
        self.addCleanup(setattr, dienst.Behandler, "lauf", vorher)
        self.addCleanup(dienst.Behandler.abbruch.clear)

        self.gesendet = []
        for name, was in (("_json", lambda _s, d, code=200: self.gesendet.append(d)),
                          ("_fehler", lambda _s, t, code=400:
                           self.gesendet.append({"fehler": t, "code": code}))):
            flicken = mock.patch.object(dienst.Behandler, name, was)
            flicken.start()
            self.addCleanup(flicken.stop)
        self.behandler = object.__new__(dienst.Behandler)

    def test_ohne_lauf_ist_nichts_gesperrt(self):
        dienst.Behandler.lauf = {"aktiv": False}
        self.assertFalse(dienst.Behandler.laeuft_noch())

    def test_ein_frischer_lauf_sperrt(self):
        import time

        dienst.Behandler.lauf = {"aktiv": True, "zuletzt": time.monotonic()}
        self.assertTrue(dienst.Behandler.laeuft_noch())

    def test_ein_lauf_ohne_lebenszeichen_gilt_als_tot(self):
        import time

        dienst.Behandler.lauf = {
            "aktiv": True,
            "zuletzt": time.monotonic() - dienst.LAUF_VERFALL - 1,
        }
        self.assertFalse(dienst.Behandler.laeuft_noch())

    def test_ein_lauf_ohne_zeitstempel_gilt_als_tot(self):
        # So sah der Zustand aus, bevor es den Stempel gab. Ein Rest davon
        # soll nicht ewig sperren.
        dienst.Behandler.lauf = {"aktiv": True}
        self.assertFalse(dienst.Behandler.laeuft_noch())

    def test_abbrechen_setzt_das_signal(self):
        import time

        dienst.Behandler.lauf = {"aktiv": True, "zuletzt": time.monotonic()}
        self.behandler._kampagne_abbrechen({})
        self.assertTrue(self.gesendet[-1]["abgebrochen"])
        self.assertTrue(dienst.Behandler.abbruch.is_set())

    def test_abbrechen_ohne_lauf_ist_kein_fehler(self):
        # Wer zweimal drueckt, soll keine rote Meldung bekommen.
        dienst.Behandler.lauf = {"aktiv": False}
        self.behandler._kampagne_abbrechen({})
        self.assertFalse(self.gesendet[-1]["abgebrochen"])
        self.assertFalse(dienst.Behandler.abbruch.is_set())
