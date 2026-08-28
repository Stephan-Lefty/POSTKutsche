"""Terminvorschläge – Wochentage, Uhrzeiten, Zeitumstellung."""

from __future__ import annotations

import unittest
from datetime import datetime

from sendeplan import sendezeiten, zeiten
from sendeplan.netzwerke import FACEBOOK, INSTAGRAM, LINKEDIN, MASTODON


class Fenster(unittest.TestCase):
    def test_jede_kombination_liefert_etwas(self):
        gruppen = (sendezeiten.HANDWERK, sendezeiten.VERBRAUCHER,
                   sendezeiten.BETROFFENE, sendezeiten.GEMISCHT)
        for netz in (MASTODON, LINKEDIN, FACEBOOK, INSTAGRAM):
            for gruppe in gruppen:
                with self.subTest(netz=netz, gruppe=gruppe):
                    self.assertTrue(sendezeiten.fenster_fuer(netz, gruppe))

    def test_unbekanntes_faellt_auf_gemischt_zurueck(self):
        # Ein Kalender ohne Vorschlag ist besser als ein Absturz.
        self.assertTrue(sendezeiten.fenster_fuer("bluesky", "irgendwas"))

    def test_bestes_fenster_zuerst(self):
        raenge = [f.rang for f in sendezeiten.fenster_fuer(FACEBOOK, sendezeiten.HANDWERK)]
        self.assertEqual(raenge, sorted(raenge))

    def test_handwerk_beginnt_frueher_als_die_ratgeber(self):
        # Ein Dachdecker ist um zehn auf dem Dach. Wenn dieser Test fällt, ist
        # jemand auf die Studienwerte zurückgefallen.
        stunden = [f.stunde for f in sendezeiten.fenster_fuer(FACEBOOK, sendezeiten.HANDWERK)]
        self.assertLessEqual(min(stunden), 7)

    def test_linkedin_meidet_das_wochenende(self):
        for gruppe in (sendezeiten.HANDWERK, sendezeiten.BETROFFENE, sendezeiten.GEMISCHT):
            for fenster in sendezeiten.fenster_fuer(LINKEDIN, gruppe):
                with self.subTest(gruppe=gruppe, fenster=fenster.beschriftung()):
                    self.assertNotIn(sendezeiten.SA, fenster.tage)
                    self.assertNotIn(sendezeiten.SO, fenster.tage)

    def test_jedes_fenster_hat_eine_begruendung(self):
        # Die steht im Kalender neben dem Vorschlag – sonst bleibt unklar,
        # warum ausgerechnet Dienstag halb acht.
        for (netz, gruppe), fenster in sendezeiten.FENSTER.items():
            for eintrag in fenster:
                with self.subTest(netz=netz, gruppe=gruppe):
                    self.assertGreater(len(eintrag.grund), 15)

    def test_uhrzeiten_sind_gueltig(self):
        for fenster in sendezeiten.FENSTER.values():
            for eintrag in fenster:
                self.assertIn(eintrag.stunde, range(24))
                self.assertIn(eintrag.minute, range(60))
                self.assertTrue(all(t in range(7) for t in eintrag.tage))

    def test_beschriftung(self):
        eintrag = sendezeiten.Fenster((sendezeiten.DI,), 7, 30, 1, "Grund")
        self.assertEqual(eintrag.beschriftung(), "Di 07:30")


class Vorschlagen(unittest.TestCase):
    def test_anzahl_wird_eingehalten(self):
        ab = datetime(2026, 9, 1, 8, 0, tzinfo=zeiten.ORTSZONE)
        self.assertEqual(len(sendezeiten.vorschlagen(FACEBOOK, ab=ab, anzahl=3)), 3)

    def test_vorschlaege_liegen_in_der_zukunft(self):
        # Ein Termin, der vorbei ist, während man ihn freigibt, hilft niemandem.
        ab = datetime(2026, 9, 1, 11, 55, tzinfo=zeiten.ORTSZONE)
        for stempel, _ in sendezeiten.vorschlagen(FACEBOOK, ab=ab, anzahl=3):
            self.assertGreater(zeiten.lesen(stempel), zeiten.lesen(zeiten.schreiben(ab)))

    def test_mindestens_eine_stunde_luft(self):
        ab = datetime(2026, 9, 1, 11, 30, tzinfo=zeiten.ORTSZONE)
        stempel, _ = sendezeiten.vorschlagen(
            FACEBOOK, sendezeiten.GEMISCHT, ab=ab, anzahl=1
        )[0]
        abstand = zeiten.lesen(stempel) - zeiten.lesen(zeiten.schreiben(ab))
        self.assertGreaterEqual(abstand.total_seconds(), 3600)

    def test_vorschlaege_sind_aufsteigend(self):
        ab = datetime(2026, 9, 1, 8, 0, tzinfo=zeiten.ORTSZONE)
        stempel = [s for s, _ in sendezeiten.vorschlagen(FACEBOOK, ab=ab, anzahl=4)]
        self.assertEqual(stempel, sorted(stempel))

    def test_begruendung_kommt_mit(self):
        ab = datetime(2026, 9, 1, 8, 0, tzinfo=zeiten.ORTSZONE)
        for _, grund in sendezeiten.vorschlagen(FACEBOOK, ab=ab, anzahl=3):
            self.assertTrue(grund)

    def test_vorschlaege_treffen_die_richtigen_wochentage(self):
        ab = datetime(2026, 9, 1, 8, 0, tzinfo=zeiten.ORTSZONE)
        erlaubt = set()
        for fenster in sendezeiten.fenster_fuer(LINKEDIN, sendezeiten.HANDWERK):
            erlaubt.update(fenster.tage)
        for stempel, _ in sendezeiten.vorschlagen(
            LINKEDIN, sendezeiten.HANDWERK, ab=ab, anzahl=5
        ):
            self.assertIn(zeiten.nach_ortszeit(stempel).weekday(), erlaubt)

    def test_vorschlaege_treffen_die_richtigen_uhrzeiten(self):
        ab = datetime(2026, 9, 1, 8, 0, tzinfo=zeiten.ORTSZONE)
        erlaubt = {
            (f.stunde, f.minute)
            for f in sendezeiten.fenster_fuer(FACEBOOK, sendezeiten.HANDWERK)
        }
        for stempel, _ in sendezeiten.vorschlagen(
            FACEBOOK, sendezeiten.HANDWERK, ab=ab, anzahl=5
        ):
            ort = zeiten.nach_ortszeit(stempel)
            self.assertIn((ort.hour, ort.minute), erlaubt)

    def test_ueber_die_zeitumstellung_bleibt_die_ortszeit_stehen(self):
        # Die Rückstellung 2026 ist am 25. Oktober. Ein Fenster um 12:00 muss
        # davor wie danach 12:00 Ortszeit ergeben, nicht 11:00 oder 13:00.
        ab = datetime(2026, 10, 22, 6, 0, tzinfo=zeiten.ORTSZONE)
        for stempel, _ in sendezeiten.vorschlagen(
            INSTAGRAM, sendezeiten.GEMISCHT, ab=ab, anzahl=6
        ):
            ort = zeiten.nach_ortszeit(stempel)
            self.assertIn(ort.minute, (0, 30))
            self.assertIn(ort.hour, (12, 19))

    def test_wochenende_wird_uebersprungen(self):
        # Ab Samstag früh darf LinkedIn erst am Dienstag vorschlagen.
        ab = datetime(2026, 9, 5, 6, 0, tzinfo=zeiten.ORTSZONE)  # Samstag
        stempel, _ = sendezeiten.vorschlagen(
            LINKEDIN, sendezeiten.HANDWERK, ab=ab, anzahl=1
        )[0]
        self.assertEqual(zeiten.nach_ortszeit(stempel).strftime("%Y-%m-%d"), "2026-09-08")


if __name__ == "__main__":
    unittest.main()
