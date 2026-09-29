"""Die Seite »Tipp der Woche« fortschreiben.

Geprüft wird an einer Seite, die genauso gebaut ist wie die echte: mit den
vier Marken, einem Tipp, einem Archiv samt auskommentiertem Muster und den
vier Stellen im Kopf und am Fuß, die mitgezogen werden müssen.
"""

from __future__ import annotations

import unittest
from datetime import date

from postkutsche import tippseite

SEITE = """<html><head>
<title>Tipp der Woche - Praxistipps zu Türen und Toren | HaBeFa.de</title>
<meta name="description" content="Jeden Montag ein neuer Praxistipp. Diese Woche: Altes." />
<meta name="date" content="2026-09-28" />
</head><body>
<!-- ============ TIPP AKTUELL  (jeden Montag ersetzen) ============ -->
    <div class="row"><div class="col-xs-12">
        <p class="noMargin"><small><strong>Kalenderwoche 40</strong> &middot; ab Montag, 28. September 2026</small></p>
        <h2>Vor dem Winter: Türdichtungen prüfen</h2>
    </div></div>
    <div class="row"><div class="col-xs-12"><p>Alter Text.</p></div></div>
<!-- ============ ENDE TIPP AKTUELL ============ -->

<!-- ============ TIPP ARCHIV ============ -->
    <div class="row"><div class="col-xs-12">
        <h2>Die Tipps der Vorwochen</h2>
        <ul>
<!-- MUSTER fuer einen Archiv-Eintrag:
            <li><strong>KW 99 &middot; Muster</strong></li>
-->
            <li><strong>KW 39 &middot; Garagentor einwintern</strong></li>
        </ul>
    </div></div>
<!-- ============ ENDE TIPP ARCHIV ============ -->
<p><small>Zuletzt aktualisiert: 28. September 2026 (KW 40)</small></p>
</body></html>"""

TIPP = {
    "titel": "Außentüren im Herbst richtig pflegen",
    "kurz": "Dichtung pflegen statt fetten.",
    "beschreibung": "Dichtung, Schwelle und Zylinder im Herbst.",
    "absaetze": ["Ein erster Absatz.", {"ueber": "Eine Überschrift"},
                 "Ein zweiter mit <strong>Betonung</strong>."],
}

MONTAG = date(2026, 10, 5)


class Fortschreiben(unittest.TestCase):

    def setUp(self):
        self.neu = tippseite.erneuern(SEITE, TIPP, 41, MONTAG)

    def test_der_neue_tipp_steht_oben(self):
        self.assertIn("Außentüren im Herbst richtig pflegen", self.neu)
        self.assertIn("Kalenderwoche 41", self.neu)
        self.assertIn("ab Montag, 5. Oktober 2026", self.neu)

    def test_der_alte_tipp_ist_oben_verschwunden(self):
        aktuell = self.neu[self.neu.find(tippseite.AKTUELL_AUF):
                           self.neu.find(tippseite.AKTUELL_ZU)]
        self.assertNotIn("Alter Text", aktuell)

    def test_der_alte_tipp_steht_jetzt_im_archiv(self):
        archiv = self.neu[self.neu.find(tippseite.ARCHIV_AUF):
                          self.neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn("KW 40", archiv)
        self.assertIn("Türdichtungen prüfen", archiv)
        # Der bisherige steht oben, der ältere darunter.
        self.assertLess(archiv.find("KW 40"), archiv.find("KW 39"))

    def test_das_auskommentierte_muster_wird_nicht_uebernommen(self):
        # Es sieht einem Eintrag zum Verwechseln ähnlich. Wer es mitnimmt,
        # hat nach zwei Wochen einen erfundenen Tipp im Archiv.
        self.assertNotIn("KW 99", self.neu)

    def test_das_archiv_wird_nach_fuenf_wochen_gekuerzt(self):
        seite = SEITE
        for nummer in range(41, 48):
            seite = tippseite.erneuern(
                seite, dict(TIPP, titel=f"Thema {nummer}"), nummer, MONTAG)
        archiv = seite[seite.find(tippseite.ARCHIV_AUF):
                       seite.find(tippseite.ARCHIV_ZU)]
        self.assertEqual(archiv.count("<li>"), tippseite.ARCHIV_WOCHEN)

    def test_titel_und_beschreibung_werden_nachgezogen(self):
        # »Beides ist fuer Google wichtig und darf nicht stehen bleiben«,
        # sagt die Anleitung in der Datei selbst.
        self.assertIn("<title>Tipp der Woche - Außentüren im Herbst richtig "
                      "pflegen | HaBeFa.de</title>", self.neu)
        self.assertIn("Diese Woche: Dichtung, Schwelle und Zylinder im Herbst.",
                      self.neu)

    def test_beide_datumsangaben_werden_nachgezogen(self):
        self.assertIn('<meta name="date" content="2026-10-05" />', self.neu)
        self.assertIn("Zuletzt aktualisiert: 5. Oktober 2026 (KW 41)", self.neu)

    def test_erlaubte_auszeichnung_bleibt_erhalten(self):
        self.assertIn("<strong>Betonung</strong>", self.neu)

    def test_alles_andere_wird_entschaerft(self):
        eigen = dict(TIPP, absaetze=["<script>alert(1)</script>"])
        neu = tippseite.erneuern(SEITE, eigen, 41, MONTAG)
        self.assertNotIn("<script>", neu)

    def test_zwischenueberschriften_werden_zu_h3(self):
        self.assertIn("<h3>Eine Überschrift</h3>", self.neu)

    def test_ohne_marken_wird_nichts_angefasst(self):
        # Lieber gar nicht schreiben als an der falschen Stelle.
        with self.assertRaises(tippseite.SeitenFehler) as fehler:
            tippseite.erneuern("<html>nichts</html>", TIPP, 41, MONTAG)
        self.assertIn("Marke", str(fehler.exception))

    def test_die_seite_bleibt_ansonsten_unberuehrt(self):
        # Kein Parser, der die ganze Datei neu formatiert: Was niemand
        # angefasst hat, soll im Vergleich auch nicht auftauchen.
        self.assertIn("<h2>Die Tipps der Vorwochen</h2>", self.neu)
        self.assertTrue(self.neu.startswith("<html><head>"))


if __name__ == "__main__":
    unittest.main()
