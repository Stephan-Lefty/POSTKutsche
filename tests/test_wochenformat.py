"""Tipp und Produkt der Woche: von der Eingabe zum Beitrag.

Geprüft wird ohne Netz und ohne Browser. Die Produktseite kommt aus einer
aufgezeichneten Antwort, Claude wird vorgetäuscht, und ob Firefox ein Bild
malt, ist hier nicht die Frage – wohl aber, dass ein fehlender Browser den
Beitrag nicht verhindert.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from postkutsche import ablage as ablage_modul
from postkutsche import denker, grafik, wochenformat
from postkutsche.quellen import seitenkarte

# Eine Produktseite, wie sie wirklich aussieht: Merkmale über dem Preis, der
# ausgezeichnete Preis im itemprop-Feld, darunter ein Empfehlungsschieber mit
# einem fremden Artikel und dessen Preis.
SEITE = """<html><head>
<meta property="og:title" content="Gedämmte Bodentreppe – Musterwerk MW 40">
<meta property="og:image" content="https://shop.example/bild.jpg">
</head><body>
<ul><li>U-Wert: 0,7 W/m&sup2;K</li><li>bis 250 kg</li></ul>
<p><strong><strike>1.100,00 &euro;</strike></strong></p>
<span><strong><span itemprop="price">959,00 &euro;</span></strong></span>
<div><p>Andere Treppe</p><p>Inhalt 1 Stk. - 1.329,00 &euro;/ Stk.</p></div>
</body></html>"""

ANTWORT = json.dumps({
    "grafik": {
        "unterzeile": "Bodentreppe – Jetzt zugreifen!",
        "name": "Musterwerk MW 40",
        "merkmale": ["U-Wert 0,7 W/m²K", "bis 250 kg", "2,50–2,70 m",
                     "einbaufertig geliefert"],
    },
    "fassungen": {
        "facebook": {"text": "Ein brauchbarer Satz über die Treppe.",
                     "schlagworte": ["bodentreppe"], "rueckfrage": None},
    },
})


class ProduktDerWoche(unittest.TestCase):

    def setUp(self):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.pfad = Path(ordner.name) / "probe.db"
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("shop", "Mein Shop", "https://shop.example",
                              "seitenkarte")
        # Kein Browser und kein Bilderholen in Tests.
        self.addCleanup(mock.patch.object(
            grafik, "vorhanden", return_value=False).stop)
        mock.patch.object(grafik, "vorhanden", return_value=False).start()

    def _anlegen(self, antwort=ANTWORT, seite=SEITE, **mehr):
        with mock.patch.object(seitenkarte, "text_und_ziel",
                               return_value=(seite, "https://shop.example/t.html")), \
             mock.patch.object(denker, "fragen", return_value=antwort), \
             ablage_modul.Ablage(self.pfad) as a:
            return wochenformat.produkt(
                a, "shop", "https://shop.example/t.html",
                "2026-10-01T08:00:00Z", ["facebook"], **mehr)

    def test_der_beitrag_entsteht_mit_fassung(self):
        ergebnis = self._anlegen()
        with ablage_modul.Ablage(self.pfad) as a:
            fassungen = a.fassungen(ergebnis["id"])
        self.assertEqual(len(fassungen), 1)
        self.assertIn("Treppe", fassungen[0]["text"])

    def test_ohne_ausgezeichneten_preis_entsteht_nichts(self):
        # Hier wird abgebrochen und nicht weitergemacht: Eine Anzeige mit
        # falschem Preis ist schlimmer als keine Anzeige.
        ohne = SEITE.replace('itemprop="price"', 'itemprop="nixda"')
        with self.assertRaises(wochenformat.WochenFehler) as fehler:
            self._anlegen(seite=ohne)
        self.assertIn("kein ausgezeichneter Preis", str(fehler.exception))

    def test_der_preis_aus_dem_schieber_wird_nicht_verwendet(self):
        # 1.329 gehört zum fremden Artikel. Er darf nicht in der Anweisung
        # an Claude als Preis auftauchen.
        gesehen = {}

        def merken(anweisung, **rest):
            gesehen["text"] = anweisung
            return ANTWORT

        with mock.patch.object(seitenkarte, "text_und_ziel",
                               return_value=(SEITE, "https://shop.example/t.html")), \
             mock.patch.object(denker, "fragen", side_effect=merken), \
             ablage_modul.Ablage(self.pfad) as a:
            wochenformat.produkt(a, "shop", "https://shop.example/t.html",
                                 "2026-10-01T08:00:00Z", ["facebook"])
        self.assertIn("Preis: 959,00 €", gesehen["text"])
        self.assertNotIn("Preis: 1.329", gesehen["text"])

    def test_das_angebotsende_wird_gerechnet_nicht_gefragt(self):
        # Der 01.10.2026 ist ein Donnerstag; die Woche endet am Sonntag.
        gesehen = {}

        def merken(anweisung, **rest):
            gesehen["text"] = anweisung
            return ANTWORT

        with mock.patch.object(seitenkarte, "text_und_ziel",
                               return_value=(SEITE, "https://shop.example/t.html")), \
             mock.patch.object(denker, "fragen", side_effect=merken), \
             ablage_modul.Ablage(self.pfad) as a:
            wochenformat.produkt(a, "shop", "https://shop.example/t.html",
                                 "2026-10-01T08:00:00Z", ["facebook"])
        self.assertIn("So 04.10.2026", gesehen["text"])

    def test_ohne_browser_entsteht_der_beitrag_trotzdem(self):
        # Der Termin ist das Wertvolle; ein Bild lässt sich nachliefern.
        ergebnis = self._anlegen()
        self.assertIsNone(ergebnis["bild"])
        self.assertIn("Firefox", ergebnis["meldung"])
        self.assertTrue(ergebnis["id"])

    def test_ein_stummer_denker_verwirft_den_beitrag_nicht(self):
        with mock.patch.object(seitenkarte, "text_und_ziel",
                               return_value=(SEITE, "https://shop.example/t.html")), \
             mock.patch.object(denker, "fragen",
                               side_effect=denker.DenkerFehler("nichts da")), \
             ablage_modul.Ablage(self.pfad) as a:
            ergebnis = wochenformat.produkt(
                a, "shop", "https://shop.example/t.html",
                "2026-10-01T08:00:00Z", ["facebook"])
        self.assertIn("nicht geschrieben", ergebnis["meldung"])
        self.assertTrue(ergebnis["id"])

    def test_ohne_netzwerk_gibt_es_nichts_zu_tun(self):
        with self.assertRaises(wochenformat.WochenFehler):
            self._anlegen_ohne_netz()

    def _anlegen_ohne_netz(self):
        with mock.patch.object(seitenkarte, "text_und_ziel",
                               return_value=(SEITE, "https://shop.example/t.html")), \
             ablage_modul.Ablage(self.pfad) as a:
            return wochenformat.produkt(a, "shop", "https://shop.example/t.html",
                                        "2026-10-01T08:00:00Z", [])

    def test_ein_unbekanntes_projekt_wird_benannt(self):
        with ablage_modul.Ablage(self.pfad) as a, \
             self.assertRaises(wochenformat.WochenFehler) as fehler:
            wochenformat.produkt(a, "gibtsnicht", "https://shop.example/t.html",
                                 "2026-10-01T08:00:00Z", ["facebook"])
        self.assertIn("gibtsnicht", str(fehler.exception))


TIPPANTWORT = json.dumps({
    "grafik": {
        "titel": "AUSSENTÜREN IM HERBST", "unterzeile": "RICHTIG PFLEGEN",
        "vorspann": "Worum es geht.", "warum": "Weil es nass wird.",
        "bloecke": [
            {"titel": "A\nB", "unter": "c", "punkte": ["1", "2", "3", "4"]},
            {"titel": "C\nD", "unter": "e", "punkte": ["1", "2", "3", "4"]},
            {"titel": "E\nF", "unter": "g", "punkte": ["1", "2", "3", "4"]},
        ],
        "beachten": ["a", "b", "c", "d"], "wissen": "Etwas Überraschendes.",
        "cta": "JETZT BERATEN LASSEN!",
    },
    "fassungen": {
        "facebook": {"text": "Ein Tipp zur Türpflege.", "schlagworte": [],
                     "rueckfrage": None},
    },
})


class TippDerWoche(unittest.TestCase):

    def setUp(self):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.pfad = Path(ordner.name) / "probe.db"
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("shop", "Mein Shop", "https://shop.example",
                              "seitenkarte")
        anstelle = mock.patch.object(grafik, "vorhanden", return_value=False)
        anstelle.start()
        self.addCleanup(anstelle.stop)

    def test_aus_einem_thema_entsteht_ein_beitrag(self):
        with mock.patch.object(denker, "fragen", return_value=TIPPANTWORT), \
             ablage_modul.Ablage(self.pfad) as a:
            ergebnis = wochenformat.tipp(
                a, "shop", "Herbstpflege von Außentüren",
                "2026-10-01T08:00:00Z", ["facebook"])
        self.assertTrue(ergebnis["id"])
        self.assertIn("AUSSENTÜREN IM HERBST", ergebnis["alternativtext"])

    def test_ohne_thema_gibt_es_nichts_zu_schreiben(self):
        with ablage_modul.Ablage(self.pfad) as a, \
             self.assertRaises(wochenformat.WochenFehler):
            wochenformat.tipp(a, "shop", "   ", "2026-10-01T08:00:00Z",
                              ["facebook"])

    def test_der_alternativtext_gibt_die_grafik_wieder(self):
        # Die ganze Aussage steckt im Bild. Wer einen Vorleser benutzt,
        # bekäme sonst nichts.
        with mock.patch.object(denker, "fragen", return_value=TIPPANTWORT), \
             ablage_modul.Ablage(self.pfad) as a:
            ergebnis = wochenformat.tipp(
                a, "shop", "Herbstpflege", "2026-10-01T08:00:00Z", ["facebook"])
        self.assertIn("AUSSENTÜREN IM HERBST", ergebnis["alternativtext"])
        self.assertIn("Überraschendes", ergebnis["alternativtext"])


class Bildzuordnung(unittest.TestCase):
    def test_instagram_bekommt_das_hochformat(self):
        # Instagram zeigt 4:5 und schneidet alles andere zu.
        self.assertIn("instagram", wochenformat.HOCHFORMAT_FUER)
        self.assertNotIn("facebook", wochenformat.HOCHFORMAT_FUER)


if __name__ == "__main__":
    unittest.main()
