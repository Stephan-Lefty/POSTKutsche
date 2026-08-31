"""Die Anweisung an Claude - besonders die Regeln, die einander widersprechen könnten."""

import unittest

from postkutsche.denker import vorlagen


class LieferzeitIstDieAusnahme(unittest.TestCase):
    """Die einzige Hausregel, die eine Betreibervorgabe sticht.

    Der Betreiber hat am 2026-08-31 entschieden: »Bei Lieferzeit 4 Tage immer
    4-7 Tage angeben« - und ausdruecklich dazu, dass das die einzige Ausnahme
    ist. Ohne diesen Vorrang bekaeme Claude zwei widersprechende Ansagen:
    »keine Lieferzeit« aus der Vorlage und »immer 4-7 Tage« aus dem
    Gelernten. Was dann herauskommt, ist Zufall.
    """

    def test_die_ausnahme_ist_benannt(self):
        # Ohne Zeilenumbrueche pruefen: Der Satz ist umbrochen, und ein Test,
        # der an der Zeilenbreite haengt, faellt beim naechsten Umformatieren.
        einzeilig = " ".join(vorlagen.GRUNDREGELN.split())
        self.assertIn("die einzige Ausnahme dieser Art", einzeilig)

    def test_ohne_vorgabe_wird_geschwiegen(self):
        # Auch wenn im Quelltext eine Frist steht. Der Quelltext ist keine
        # Vorgabe - er ist die Seite, von der abgeschrieben wird.
        self.assertIn("schweigst du", vorlagen.GRUNDREGELN)

    def test_verfuegbarkeit_bleibt_verboten(self):
        # Die Ausnahme gilt der Lieferzeit allein. Wer sie auf Verfuegbarkeit
        # und Eignung ausweitet, hat die Regel abgeschafft.
        self.assertIn("Verfügbarkeit oder Eignung", vorlagen.GRUNDREGELN)

    def test_preise_bleiben_unverhandelbar(self):
        # Die Gegenprobe: Es gibt genau eine Ausnahme, nicht zwei.
        self.assertIn("Keine Preise nennen", vorlagen.GRUNDREGELN)
