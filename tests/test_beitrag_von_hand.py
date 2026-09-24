"""Einen Beitrag selbst in den Kalender stellen.

Bisher entstand ein Beitrag nur aus einem abgerufenen Inhalt oder aus der
Wochenplanung. Für eine Ankündigung, die auf keiner eigenen Seite steht,
führte kein Weg hinein.

Geprüft wird der Endpunkt ohne laufenden Dienst: Die Methode wird an einem
Behelf aufgerufen, der `_ablage`, `_json` und `_fehler` bereitstellt. Ein
Test, der einen Webserver hochfährt, prüft `http.server` – und das haben
andere schon getan.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from postkutsche import ablage as ablage_modul
from postkutsche import denker, konfiguration, zeiten
from postkutsche.web import dienst


class BeitragVonHand(unittest.TestCase):

    def setUp(self):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.pfad = Path(ordner.name) / "probe.db"
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("blog", "Mein Blog", "https://blog.example",
                              "wordpress")

        self.antwort: dict = {}
        self.fehler: list = []
        self.behelf = SimpleNamespace(
            _ablage=lambda: ablage_modul.Ablage(self.pfad),
            _json=lambda daten, kode=200: self.antwort.update(daten),
            _fehler=lambda meldung, kode=400: self.fehler.append((meldung, kode)),
        )

    def _anlegen(self, weg: str = "hand", **mehr):
        rumpf = {
            "projekt": "blog",
            "titel": "Wir machen Betriebsferien",
            "text": "Vom 24. Dezember bis zum 6. Januar bleibt die Werkstatt zu.",
            "geplant": "2026-12-20T09:00",
            "netzwerke": ["mastodon"],
        }
        rumpf.update(mehr)
        with mock.patch.object(konfiguration, "denker_lesen",
                               lambda: {"weg": weg}):
            dienst.Behandler._beitrag_neu(self.behelf, rumpf)
        return rumpf

    def test_beitrag_und_fassung_entstehen(self):
        self._anlegen()
        self.assertFalse(self.fehler, self.fehler)
        with ablage_modul.Ablage(self.pfad) as a:
            beitrag = a.beitrag(int(self.antwort["id"]))
            fassungen = a.fassungen(int(self.antwort["id"]))
        self.assertEqual(beitrag["zustand"], ablage_modul.BEITRAG_ENTWURF)
        self.assertEqual([f["netzwerk"] for f in fassungen], ["mastodon"])
        self.assertIn("Betriebsferien", fassungen[0]["text"])

    def test_termin_kommt_als_ortszeit_und_liegt_in_utc(self):
        self._anlegen()
        with ablage_modul.Ablage(self.pfad) as a:
            beitrag = a.beitrag(int(self.antwort["id"]))
        # Neun Uhr im Dezember in Berlin ist acht Uhr UTC.
        self.assertTrue(beitrag["geplant"].startswith("2026-12-20T08:00"),
                        beitrag["geplant"])

    def test_ohne_titel_geht_nichts(self):
        with self.assertRaises(ValueError):
            self._anlegen(titel="   ")

    def test_ohne_netzwerk_geht_nichts(self):
        with self.assertRaises(ValueError):
            self._anlegen(netzwerke=[])

    def test_erfundenes_netzwerk_faellt_auf(self):
        with self.assertRaises(ValueError) as f:
            self._anlegen(netzwerke=["telegramm"])
        self.assertIn("telegramm", str(f.exception))

    def test_unbekanntes_projekt_meldet_404(self):
        self._anlegen(projekt="gibtsnicht")
        self.assertEqual(self.fehler[0][1], 404)

    def test_zwei_gleiche_titel_bleiben_zwei_beitraege(self):
        """»inhalt_merken« würde den ersten sonst überschreiben."""
        self._anlegen()
        erste = int(self.antwort["id"])
        self._anlegen()
        zweite = int(self.antwort["id"])
        self.assertNotEqual(erste, zweite)
        with ablage_modul.Ablage(self.pfad) as a:
            self.assertIsNotNone(a.beitrag(erste))
            self.assertIsNotNone(a.beitrag(zweite))

    def test_ein_klemmender_dienst_verwirft_den_termin_nicht(self):
        """Der Kalendereintrag ist das Wichtigere – Text lässt sich tippen."""
        def klemmt(*a, **k):
            raise denker.DenkerFehler("Ollama antwortet nicht")

        with mock.patch.object(denker, "schreiben", klemmt):
            self._anlegen(weg="offen")

        self.assertFalse(self.fehler, self.fehler)
        self.assertIn("nicht geschrieben", self.antwort["meldung"])
        with ablage_modul.Ablage(self.pfad) as a:
            fassungen = a.fassungen(int(self.antwort["id"]))
        self.assertIn("Betriebsferien", fassungen[0]["text"])

    def test_der_weg_des_projekts_gilt(self):
        """Steht beim Projekt »hand«, ruft auch dieser Endpunkt niemanden an."""
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("blog", "Mein Blog", "https://blog.example",
                              "wordpress", einstellungen={"denker": "hand"})

        def darf_nicht(*a, **k):
            raise AssertionError("Hier hätte niemand anrufen dürfen.")

        with mock.patch.object(denker.offen, "fassungen", darf_nicht):
            self._anlegen(weg="offen")
        self.assertEqual(self.antwort["weg"], "hand")


if __name__ == "__main__":
    unittest.main()
