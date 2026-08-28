"""Der Versand – wer gesendet wird und wer nicht.

Kein Netzzugriff: Mastodon wird vorgetäuscht. Die wichtigsten Prüfungen sind
die *negativen* – was **nicht** rausgehen darf. Ein Beitrag, der einen Tag zu
spät erscheint, ist ein Ärgernis; einer, der ungewollt erscheint, steht
öffentlich.
"""

from __future__ import annotations

import unittest
from unittest import mock

from postkutsche import versand
from postkutsche.ablage import (
    BEITRAG_ENTWURF,
    BEITRAG_ERLEDIGT,
    BEITRAG_FREIGEGEBEN,
    FASSUNG_GESCHEITERT,
    FASSUNG_GESENDET,
    PROJEKT_PAUSIERT,
    VERSAND_HAND,
    Ablage,
)

KONTEN = {"mastodon": {"kennung": "probe", "instanz": "https://m.example"}}
FRUEHER = "2026-06-01T10:00:00Z"
SPAETER = "2099-01-01T10:00:00Z"


class Basis(unittest.TestCase):
    def setUp(self):
        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "blog", "Blog", "https://blog.example", "wordpress"
        )

    def _beitrag(self, zustand=BEITRAG_FREIGEGEBEN, geplant=FRUEHER,
                 versandart="schnittstelle", netz="mastodon"):
        nummer = self.ablage.beitrag_anlegen(self.projekt.id, geplant, zustand=zustand)
        self.ablage.fassung_setzen(nummer, netz, "Ein Text.", "technik",
                                   versandart=versandart)
        if zustand == BEITRAG_FREIGEGEBEN:
            self.ablage.beitrag_zustand(nummer, BEITRAG_FREIGEGEBEN)
        return nummer

    def _senden(self, **kwargs):
        antwort = {"id": "1", "url": "https://m.example/@x/1"}
        with mock.patch("postkutsche.zugaenge.holen", return_value="geheim"), \
             mock.patch("postkutsche.netzwerke.mastodon.senden",
                        return_value=antwort) as gesendet:
            ergebnis = versand.senden(self.ablage, KONTEN, melden=lambda *a: None,
                                      **kwargs)
        return ergebnis, gesendet


class WasNichtRausgeht(Basis):
    def test_entwuerfe_bleiben_liegen(self):
        self._beitrag(zustand=BEITRAG_ENTWURF)
        (gut, schlecht), gesendet = self._senden()
        self.assertEqual((gut, schlecht), (0, 0))
        gesendet.assert_not_called()

    def test_pausiertes_projekt_sendet_nicht(self):
        self._beitrag()
        self.ablage.projekt_zustand("blog", PROJEKT_PAUSIERT)
        (gut, _), gesendet = self._senden()
        self.assertEqual(gut, 0)
        gesendet.assert_not_called()

    def test_zukunft_bleibt_liegen(self):
        self._beitrag(geplant=SPAETER)
        (gut, _), gesendet = self._senden()
        self.assertEqual(gut, 0)
        gesendet.assert_not_called()

    def test_handbetrieb_geht_nicht_von_selbst(self):
        # Facebook und Instagram werden von Hand eingestellt. Der Zeitplan
        # darf sie nicht anfassen.
        self._beitrag(versandart=VERSAND_HAND)
        (gut, _), gesendet = self._senden()
        self.assertEqual(gut, 0)
        gesendet.assert_not_called()

    def test_schon_gesendetes_nicht_noch_einmal(self):
        nummer = self._beitrag()
        fassung = self.ablage.fassungen(nummer)[0]
        self.ablage.fassung_vermerken(int(fassung["id"]), FASSUNG_GESENDET)
        (gut, _), gesendet = self._senden()
        self.assertEqual(gut, 0)
        gesendet.assert_not_called()

    def test_probelauf_sendet_nichts(self):
        self._beitrag()
        (gut, _), gesendet = self._senden(probelauf=True)
        self.assertEqual(gut, 1)
        gesendet.assert_not_called()


class WasRausgeht(Basis):
    def test_freigegebenes_geht_raus(self):
        nummer = self._beitrag()
        (gut, schlecht), gesendet = self._senden()
        self.assertEqual((gut, schlecht), (1, 0))
        gesendet.assert_called_once()
        fassung = self.ablage.fassungen(nummer)[0]
        self.assertEqual(fassung["zustand"], FASSUNG_GESENDET)
        self.assertEqual(fassung["fremd_adresse"], "https://m.example/@x/1")

    def test_schlagworte_kommen_an_den_text(self):
        self._beitrag()
        _, gesendet = self._senden()
        text = gesendet.call_args[1]["text"]
        self.assertIn("Ein Text.", text)
        self.assertIn("#technik", text)

    def test_idempotenzschluessel_haengt_an_der_fassung(self):
        # Bricht die Verbindung nach dem Anlegen ab, darf der zweite Versuch
        # keinen zweiten Beitrag erzeugen.
        nummer = self._beitrag()
        fassung = int(self.ablage.fassungen(nummer)[0]["id"])
        _, gesendet = self._senden()
        self.assertIn(str(fassung), gesendet.call_args[1]["schluessel"])

    def test_beitrag_gilt_danach_als_erledigt(self):
        nummer = self._beitrag()
        self._senden()
        self.assertEqual(self.ablage.beitrag(nummer)["zustand"], BEITRAG_ERLEDIGT)


class WennEsSchiefgeht(Basis):
    def test_fehler_wird_vermerkt_statt_verschluckt(self):
        nummer = self._beitrag()
        with mock.patch("postkutsche.zugaenge.holen", return_value="geheim"), \
             mock.patch("postkutsche.netzwerke.mastodon.senden",
                        side_effect=RuntimeError("Server sagt nein")):
            gut, schlecht = versand.senden(self.ablage, KONTEN, melden=lambda *a: None)
        self.assertEqual((gut, schlecht), (0, 1))
        fassung = self.ablage.fassungen(nummer)[0]
        self.assertEqual(fassung["zustand"], FASSUNG_GESCHEITERT)
        self.assertIn("Server sagt nein", fassung["fehler"])

    def test_gescheitertes_bleibt_sichtbar(self):
        # Ein Beitrag, bei dem etwas schiefging, darf nicht stillschweigend
        # als erledigt gelten - sonst sucht man ihn nie wieder.
        nummer = self._beitrag()
        with mock.patch("postkutsche.zugaenge.holen", return_value="geheim"), \
             mock.patch("postkutsche.netzwerke.mastodon.senden",
                        side_effect=RuntimeError("kaputt")):
            versand.senden(self.ablage, KONTEN, melden=lambda *a: None)
        self.assertNotEqual(self.ablage.beitrag(nummer)["zustand"], BEITRAG_ERLEDIGT)

    def test_ohne_konto_kommt_eine_anleitung(self):
        nummer = self._beitrag()
        gut, schlecht = versand.senden(self.ablage, {}, melden=lambda *a: None)
        self.assertEqual((gut, schlecht), (0, 1))
        self.assertIn("konto neu", self.ablage.fassungen(nummer)[0]["fehler"])

    def test_ungebautes_netzwerk_wird_benannt(self):
        self._beitrag(netz="linkedin")
        konten = {**KONTEN, "linkedin": {"kennung": "li"}}
        gut, schlecht = versand.senden(self.ablage, konten, melden=lambda *a: None)
        self.assertEqual(schlecht, 1)


class Faellige(Basis):
    def test_aelteste_zuerst(self):
        self._beitrag(geplant="2026-06-03T10:00:00Z")
        self._beitrag(geplant="2026-06-01T10:00:00Z")
        termine = [e["geplant"] for e in
                   versand.faillige_pruefen(versand.faellige(self.ablage))]
        self.assertEqual(termine, sorted(termine))

    def test_verspaetung_wird_erkannt(self):
        self.assertIsNotNone(versand._verspaetung("2020-01-01T00:00:00Z"))
        self.assertIsNone(versand._verspaetung("2099-01-01T00:00:00Z"))


if __name__ == "__main__":
    unittest.main()
