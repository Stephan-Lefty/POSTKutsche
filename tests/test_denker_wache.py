"""Beim Start nachsehen, ob der Denker antwortet.

Der Anlass war eine abgelaufene Claude-Anmeldung: Sie fiel erst auf, als
mitten in einer Wochenplanung eine rote Zeile kam. Dass jemand nicht
antwortet, soll beim Start dastehen und in der Oberfläche stehen bleiben.

Zwei Dinge sind hier wichtiger als es aussieht. Erstens kostet die Prüfung
eine echte Anfrage – bei Claude Code einen Prozessstart –, sie darf also
weder den Start noch jeden Aufruf des Kalenders aufhalten. Zweitens ist
»noch nicht geprüft« nicht dasselbe wie »geht nicht«: Wer das verwechselt,
zeigt beim Start jedes Mal eine Warnung, die sich Sekunden später selbst
widerruft, und die lernt man zu übersehen.
"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from postkutsche import ablage as ablage_modul
from postkutsche import denker, konfiguration
from postkutsche.web import dienst

#: Der Grund, den eine abgelaufene Anmeldung wirklich nennt. Wortgetreu aus
#: dem Lauf vom 2026-10-29 - er ist der Grund, warum der Grund jetzt
#: durchgereicht wird.
ABGELAUFEN = "Failed to authenticate: OAuth session expired"


def _sagt_ja():
    """Claude Code antwortet. Geprüft wird `antwortet`, nicht `erreichbar`:
    Nur die wirft, und nur durch das Werfen kommt der Grund nach außen."""
    return mock.patch.object(denker.kommando, "antwortet", return_value=None)


def _sagt_nein(grund: str = ABGELAUFEN):
    """Claude Code antwortet nicht – mit Grund."""
    return mock.patch.object(denker.kommando, "antwortet",
                             side_effect=denker.DenkerFehler(grund))


class Pruefstand(unittest.TestCase):
    """Der Zwischenspeicher für sich."""

    def setUp(self):
        dienst.denker_vergessen()
        self.addCleanup(dienst.denker_vergessen)

    def test_ohne_pruefung_weiss_man_nichts(self):
        self.assertIsNone(dienst.denker_stand(denker.KOMMANDO))

    def test_geprueft_wird_gemerkt(self):
        with _sagt_ja():
            self.assertTrue(dienst.denker_nachsehen(denker.KOMMANDO, {}))
        self.assertEqual(dienst.denker_stand(denker.KOMMANDO)["geht"], True)

    def test_auch_ein_nein_wird_gemerkt(self):
        with _sagt_nein():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        self.assertEqual(dienst.denker_stand(denker.KOMMANDO)["geht"], False)

    def test_eine_alte_auskunft_gilt_nicht_mehr(self):
        with mock.patch.object(dienst.time, "monotonic", return_value=1000.0), \
             _sagt_ja():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        spaeter = 1000.0 + dienst.DENKER_STAND_GILT + 1
        with mock.patch.object(dienst.time, "monotonic", return_value=spaeter):
            self.assertIsNone(dienst.denker_stand(denker.KOMMANDO))

    def test_frisch_genug_gilt_noch(self):
        with mock.patch.object(dienst.time, "monotonic", return_value=1000.0), \
             _sagt_ja():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        with mock.patch.object(dienst.time, "monotonic",
                               return_value=1000.0 + dienst.DENKER_STAND_GILT - 1):
            self.assertIsNotNone(dienst.denker_stand(denker.KOMMANDO))

    def test_wege_werden_getrennt_gemerkt(self):
        with _sagt_nein():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        self.assertIsNone(dienst.denker_stand(denker.OFFEN))

    def test_der_grund_wird_mitgemerkt(self):
        with _sagt_nein():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        self.assertIn("OAuth session expired",
                      dienst.denker_stand(denker.KOMMANDO)["grund"])

    def test_wer_antwortet_hat_keinen_grund(self):
        with _sagt_ja():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        self.assertEqual(dienst.denker_stand(denker.KOMMANDO)["grund"], "")


class Endpunkt(unittest.TestCase):
    """Was `/api/denker` dazu sagt."""

    def setUp(self):
        dienst.denker_vergessen()
        self.addCleanup(dienst.denker_vergessen)
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        self.pfad = Path(ordner.name) / "probe.db"
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("blog", "Mein Blog", "https://blog.example",
                              "wordpress")

        self.antwort: dict = {}
        self.behelf = SimpleNamespace(
            _ablage=lambda: ablage_modul.Ablage(self.pfad),
            _json=lambda daten, kode=200: self.antwort.update(daten),
            _fehler=lambda meldung, kode=400: None,
            _denker_nachsehen_still=dienst.Behandler._denker_nachsehen_still,
        )

    def _fragen(self, weg: str = denker.KOMMANDO, projekt: str = ""):
        with mock.patch.object(konfiguration, "denker_lesen",
                               lambda: {"weg": weg}), \
             mock.patch.object(dienst.threading, "Thread") as faden:
            dienst.Behandler._denker(self.behelf,
                                     {"projekt": [projekt]} if projekt else {})
        return faden

    def test_ungeprueft_heisst_nicht_kaputt(self):
        self._fragen()
        # None, nicht False: Die Oberfläche warnt nur bei einem echten Nein.
        self.assertIsNone(self.antwort["geht"])

    def test_ungeprueft_stoesst_das_nachsehen_an(self):
        faden = self._fragen()
        faden.assert_called_once()
        self.assertTrue(faden.return_value.start.called)

    def test_ein_bekanntes_nein_kommt_durch(self):
        with _sagt_nein():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        faden = self._fragen()
        self.assertIs(self.antwort["geht"], False)
        # Der Stand ist da, es muss nicht noch einmal nachgesehen werden.
        faden.assert_not_called()

    def test_die_abhilfe_steht_dabei(self):
        self._fragen()
        self.assertIn("claude", self.antwort["abhilfe"].lower())

    def test_der_grund_kommt_mit_durch(self):
        with _sagt_nein():
            dienst.denker_nachsehen(denker.KOMMANDO, {})
        self._fragen()
        self.assertIn("OAuth session expired", self.antwort["grund"])

    def test_ohne_pruefung_gibt_es_keinen_grund(self):
        # Kein Grund heißt leer, nicht None: Die Leiste hängt ihn an die
        # Abhilfe, und »null – Claude Code antwortet nicht« wäre Unsinn.
        self._fragen()
        self.assertEqual(self.antwort["grund"], "")

    def test_von_hand_antwortet_immer(self):
        faden = self._fragen(denker.HAND)
        self.assertIs(self.antwort["geht"], True)
        faden.assert_not_called()

    def test_der_weg_des_projekts_zaehlt(self):
        with ablage_modul.Ablage(self.pfad) as a:
            a.projekt_anlegen("blog", "Mein Blog", "https://blog.example",
                              "wordpress",
                              einstellungen={"denker": denker.HAND})
        self._fragen(denker.KOMMANDO, projekt="blog")
        self.assertEqual(self.antwort["weg"], denker.HAND)


class BeimStart(unittest.TestCase):
    """Was auf der Konsole steht, wenn der Dienst hochkommt."""

    def setUp(self):
        dienst.denker_vergessen()
        self.addCleanup(dienst.denker_vergessen)
        self.zeilen: list[str] = []

    def _starten(self, weg: str, antwortet: bool = True):
        probe = (mock.patch.object(denker.WEGE[weg], "antwortet",
                                   return_value=None) if antwortet
                 else mock.patch.object(
                     denker.WEGE[weg], "antwortet",
                     side_effect=denker.DenkerFehler(ABGELAUFEN)))
        with mock.patch.object(konfiguration, "denker_lesen",
                               lambda: {"weg": weg}), probe:
            dienst._denker_beim_start(self.zeilen.append)
        return "\n".join(self.zeilen)

    def test_antwortet_wird_gesagt(self):
        self.assertIn("antwortet", self._starten(denker.KOMMANDO, True))

    def test_antwortet_nicht_wird_deutlich_gesagt(self):
        ausgabe = self._starten(denker.KOMMANDO, False)
        self.assertIn("NICHT", ausgabe)
        # Und was zu tun ist, gleich dazu - sonst sucht man wieder.
        self.assertIn("claude auth login", ausgabe)

    def test_der_grund_steht_auf_der_konsole(self):
        # Am 2026-10-29 stand hier nur die Abhilfe »Installiert?« - während
        # Claude Code installiert war und »OAuth session expired« meldete.
        self.assertIn("OAuth session expired",
                      self._starten(denker.KOMMANDO, False))

    def test_von_hand_wird_nicht_geprueft(self):
        with mock.patch.object(konfiguration, "denker_lesen",
                               lambda: {"weg": denker.HAND}), \
             mock.patch.object(denker.hand, "antwortet") as gefragt:
            dienst._denker_beim_start(self.zeilen.append)
        gefragt.assert_not_called()
        self.assertIn("Von Hand", "\n".join(self.zeilen))

    def test_ein_fehler_beim_pruefen_reisst_nichts_mit(self):
        # Der Faden läuft beim Start des Dienstes. Fliegt hier eine Ausnahme,
        # steht sie unkommentiert im Terminal und sieht aus wie ein Absturz.
        with mock.patch.object(konfiguration, "denker_lesen",
                               side_effect=OSError("Datei kaputt")):
            dienst._denker_beim_start(self.zeilen.append)
        self.assertIn("Datei kaputt", "\n".join(self.zeilen))


if __name__ == "__main__":
    unittest.main()


class TippseitenWache(unittest.TestCase):
    """Wacht darüber, dass die Tipp-Seite die laufende Woche zeigt."""

    def setUp(self):
        dienst.tippseite_vergessen()
        self.addCleanup(dienst.tippseite_vergessen)

    def test_ohne_pruefung_ist_der_stand_unbekannt(self):
        # »noch nicht nachgesehen« ist nicht »veraltet«.
        self.assertIsNone(dienst.tippseite_stand("tipp-woche"))

    def test_eine_geholte_woche_wird_gemerkt(self):
        seite = ('<!-- ============ TIPP AKTUELL ============ -->'
                 '<p><strong>Kalenderwoche 41</strong></p><h2>Thema</h2>'
                 '<!-- ============ ENDE TIPP AKTUELL ============ -->')
        with mock.patch.object(konfiguration, "marke",
                               return_value={"tippseite": "https://x.example/t.html"}), \
             mock.patch("postkutsche.quellen.abrufen.holen", return_value=seite):
            dienst.tippseite_nachsehen("tipp-woche")
        self.assertEqual(dienst.tippseite_stand("tipp-woche")["woche"], 41)

    def test_ohne_eingetragene_adresse_wird_nicht_geprueft(self):
        with mock.patch.object(konfiguration, "marke", return_value={}):
            self.assertIsNone(dienst.tippseite_nachsehen("tipp-woche"))

    def test_eine_stumme_seite_loest_keine_warnung_aus(self):
        # Ein Hinweis, der auch bei einer Netzstörung erscheint, wird
        # bald übersehen.
        with mock.patch.object(konfiguration, "marke",
                               return_value={"tippseite": "https://x.example/t.html"}), \
             mock.patch("postkutsche.quellen.abrufen.holen",
                        side_effect=OSError("kein Netz")):
            stand = dienst.tippseite_nachsehen("tipp-woche")
        self.assertIsNone(stand["woche"])

    def test_der_stand_verfaellt(self):
        with mock.patch.object(konfiguration, "marke",
                               return_value={"tippseite": "https://x.example/t.html"}), \
             mock.patch("postkutsche.quellen.abrufen.holen", return_value="<html></html>"):
            dienst.tippseite_nachsehen("tipp-woche")
        with mock.patch.object(dienst.time, "monotonic",
                               return_value=time.monotonic() + dienst.TIPPSEITE_GILT + 1):
            self.assertIsNone(dienst.tippseite_stand("tipp-woche"))
