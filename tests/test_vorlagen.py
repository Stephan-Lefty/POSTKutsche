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


class GarantieGehoertNichtInEinenBeitrag(unittest.TestCase):
    """Zusagen mit rechtlicher Wirkung ueberleben den Beitrag nicht.

    Ansage des Betreibers vom 2026-08-31: »Garantiebedingungen sollten nie in
    einen Post rein.« Dieselbe Begruendung wie bei den Preisen - sie aendern
    sich, der Beitrag bleibt stehen, und ein zwei Jahre alter Beitrag mit
    ueberholten Bedingungen wird zum Vorwurf.
    """

    def test_garantie_ist_verboten(self):
        einzeilig = " ".join(vorlagen.GRUNDREGELN.split())
        self.assertIn("Nichts zu Garantie oder Gewährleistung", einzeilig)

    def test_auch_wenn_es_im_quelltext_steht(self):
        # Der entscheidende Zusatz. Ohne ihn schreibt Claude ab, was auf der
        # Produktseite steht - und dort steht es oft.
        einzeilig = " ".join(vorlagen.GRUNDREGELN.split())
        self.assertIn("auch dann nicht, wenn es im Quelltext steht", einzeilig)

    def test_ist_keine_ausnahme_wie_die_lieferzeit(self):
        # Die Lieferzeit haengt an einer Vorgabe des Betreibers. Die Garantie
        # nicht: Sie ist verboten, und dabei bleibt es.
        stelle = vorlagen.GRUNDREGELN.index("Garantie")
        abschnitt = " ".join(vorlagen.GRUNDREGELN[stelle:stelle + 400].split())
        self.assertNotIn("Ausnahme", abschnitt.split("- Nichts erfinden")[0])
