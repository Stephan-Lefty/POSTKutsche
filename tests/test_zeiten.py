"""Zeitrechnung – der Teil, der zweimal im Jahr Ärger macht."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from postkutsche import zeiten


class Umrechnung(unittest.TestCase):
    def test_sommerzeit_zwei_stunden(self):
        # 1. September, 18 Uhr in Berlin ist 16 Uhr UTC.
        self.assertEqual(zeiten.von_ortszeit("2026-09-01 18:00"), "2026-09-01T16:00:00Z")

    def test_winterzeit_eine_stunde(self):
        # 1. Dezember, 18 Uhr in Berlin ist 17 Uhr UTC.
        self.assertEqual(zeiten.von_ortszeit("2026-12-01 18:00"), "2026-12-01T17:00:00Z")

    def test_hin_und_zurueck(self):
        for eingabe in ("2026-03-29 03:30", "2026-10-25 03:30", "2026-06-15 12:00"):
            with self.subTest(eingabe=eingabe):
                utc = zeiten.von_ortszeit(eingabe)
                zurueck = zeiten.nach_ortszeit(utc)
                self.assertEqual(zurueck.strftime("%Y-%m-%d %H:%M"), eingabe)

    def test_t_als_trenner_erlaubt(self):
        self.assertEqual(
            zeiten.von_ortszeit("2026-09-01T18:00"),
            zeiten.von_ortszeit("2026-09-01 18:00"),
        )

    def test_nur_datum_meint_mitternacht(self):
        self.assertEqual(zeiten.von_ortszeit("2026-09-01"), "2026-08-31T22:00:00Z")

    def test_unsinn_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            zeiten.von_ortszeit("morgen abend")

    def test_ohne_zone_gilt_ortszeit(self):
        # Wer datetime(2026, 9, 1, 18, 0) schreibt, meint 18 Uhr hier.
        self.assertEqual(
            zeiten.schreiben(datetime(2026, 9, 1, 18, 0)), "2026-09-01T16:00:00Z"
        )

    def test_mit_zone_wird_geachtet(self):
        self.assertEqual(
            zeiten.schreiben(datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)),
            "2026-09-01T18:00:00Z",
        )


class Grenzen(unittest.TestCase):
    def test_monat_beginnt_nach_ortszeit(self):
        # Der September beginnt für den Betrachter am 1.9. um Mitternacht hier –
        # das ist der 31.8. um 22 Uhr UTC. Wer stur nach UTC rechnet, dem fehlt
        # der erste Abend des Monats in der Ansicht.
        von, bis = zeiten.monatsgrenzen(2026, 9)
        self.assertEqual(von, "2026-08-31T22:00:00Z")
        self.assertEqual(bis, "2026-09-30T22:00:00Z")

    def test_dezember_springt_ins_neue_jahr(self):
        von, bis = zeiten.monatsgrenzen(2026, 12)
        self.assertEqual(von, "2026-11-30T23:00:00Z")
        self.assertEqual(bis, "2026-12-31T23:00:00Z")

    def test_woche_beginnt_montags(self):
        # Der 2026-09-03 ist ein Donnerstag; die Woche beginnt am Montag, dem 31.8.
        von, _ = zeiten.wochengrenzen(datetime(2026, 9, 3, 15, 0))
        self.assertEqual(zeiten.nach_ortszeit(von).strftime("%Y-%m-%d %H:%M"),
                         "2026-08-31 00:00")

    def test_woche_dauert_sieben_tage(self):
        von, bis = zeiten.wochengrenzen(datetime(2026, 9, 3, 15, 0))
        spanne = zeiten.lesen(bis) - zeiten.lesen(von)
        self.assertEqual(spanne.days, 7)

    def test_woche_ueber_die_zeitumstellung(self):
        # In der Woche der Rückstellung (25.10.2026) hat der Montag-zu-Montag-
        # Abstand 169 Stunden, nicht 168. Die Anzeige muss trotzdem montags
        # um Mitternacht beginnen und enden.
        von, bis = zeiten.wochengrenzen(datetime(2026, 10, 28, 12, 0))
        self.assertEqual(zeiten.nach_ortszeit(von).strftime("%H:%M"), "00:00")
        self.assertEqual(zeiten.nach_ortszeit(bis).strftime("%H:%M"), "00:00")


class Anzeige(unittest.TestCase):
    def test_lesbar(self):
        self.assertEqual(zeiten.lesbar("2026-09-01T16:00:00Z"), "Di 01.09.2026, 18:00")


if __name__ == "__main__":
    unittest.main()
