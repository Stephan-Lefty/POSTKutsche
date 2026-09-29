"""Die Grafik – geprüft an der erzeugten Seite, nicht am Bild.

Ob Firefox richtig malt, ist nicht zu testen und auch nicht nötig. Was sich
prüfen lässt: dass die Seite überhaupt entsteht, dass beide Formate dasselbe
Gerüst tragen, und dass nichts hineingerät, was niemand hineingeschrieben hat.

Dass die Seite *gebaut* wird, ist dabei der Punkt. Am 2026-09-29 lief der
Tipp auf einen fehlenden Schlüssel »farbe« – die Tests davor hatten immer nur
mit abgeschaltetem Browser gearbeitet und die Seite nie erzeugt.
"""

from __future__ import annotations

import unittest

from postkutsche import grafik

MARKE = {"name": "Beispielhaus", "telefon": "030 - 000 000 00",
         "zeiten": "Mo.–Fr.", "netz": "www.beispiel.example",
         "mail": "info@example.org", "ueber": ["eins", "zwei"]}

PRODUKT = {
    "name": "Musterwerk MW 40", "unterzeile": "Bodentreppe – Jetzt zugreifen!",
    "merkmale": ["eins", "zwei", "drei", "vier"],
    "preis": "959,00 €", "preis_alt": "1.100,00 €", "ersparnis": "141,00 €",
    "gueltig": "Angebot gültig bis So 04.10.2026, 23:59 Uhr",
}

BLOCK = {"titel": "A\nB", "unter": "c", "punkte": ["1", "2", "3", "4"]}
TIPP = {
    "titel": "AUSSENTÜREN IM HERBST", "unterzeile": "RICHTIG PFLEGEN",
    "vorspann": "Worum es geht.", "warum": "Weil es nass wird.",
    "bloecke": [dict(BLOCK), dict(BLOCK), dict(BLOCK)],
    "beachten": ["a", "b", "c", "d"], "wissen": "Etwas Überraschendes.",
    "cta": "JETZT BERATEN LASSEN!",
}


class BeideFormate(unittest.TestCase):
    """Was in beiden steht, steht an derselben Stelle – das ist der Zweck."""

    def test_produktseite_entsteht(self):
        seite = grafik.produkt_seite(PRODUKT, MARKE)
        self.assertIn("PRODUKT", seite)
        self.assertIn("959,00 €", seite)
        self.assertIn("141,00 €", seite)

    def test_tippseite_entsteht(self):
        # Genau hier lief es auf einen fehlenden Schlüssel »farbe«.
        seite = grafik.tipp_seite(TIPP, MARKE)
        self.assertIn("AUSSENTÜREN IM HERBST", seite)
        self.assertIn("Etwas Überraschendes.", seite)

    def test_die_blockfarben_kommen_nicht_vom_modell(self):
        # Wer die Farbe erfinden lässt, bekommt jede Woche eine andere.
        seite = grafik.tipp_seite(TIPP, MARKE)
        for farbe in grafik.BLOCKFARBEN:
            self.assertIn(farbe, seite)

    def test_eine_vorgegebene_blockfarbe_sticht(self):
        eigen = dict(TIPP, bloecke=[dict(BLOCK, farbe="#123456"),
                                    dict(BLOCK), dict(BLOCK)])
        self.assertIn("#123456", grafik.tipp_seite(eigen, MARKE))

    def test_beide_tragen_dasselbe_geruest(self):
        fuer_beide = (grafik.produkt_seite(PRODUKT, MARKE),
                      grafik.tipp_seite(TIPP, MARKE))
        for seite in fuer_beide:
            with self.subTest():
                self.assertIn('class="logo"', seite)
                self.assertIn('class="kontakt"', seite)
                self.assertIn('class="fuss"', seite)
                self.assertIn("030 - 000 000 00", seite)
                self.assertIn("info@example.org", seite)

    def test_das_hochformat_setzt_nur_abweichungen(self):
        quer = grafik.produkt_seite(PRODUKT, MARKE)
        hoch = grafik.produkt_seite(PRODUKT, MARKE, hoch=True)
        self.assertNotIn(f"width:{grafik.BREITE_HOCH}px", quer)
        self.assertIn(f"width:{grafik.BREITE_HOCH}px", hoch)
        # Im Hochformat fällt Weniges weg, aber der Absender bleibt.
        self.assertIn("display:none", hoch)
        self.assertIn('class="kontakt"', hoch)

    def test_ohne_logodatei_bleibt_der_name_stehen(self):
        # Eine Grafik ganz ohne Absender wäre schlimmer als eine ohne Bildmarke.
        seite = grafik.produkt_seite(PRODUKT, dict(MARKE, logo="/gibt/es/nicht.png"))
        self.assertIn("Beispielhaus", seite)

    def test_spitze_klammern_im_namen_werden_entschaerft(self):
        seite = grafik.produkt_seite(dict(PRODUKT, name="<script>x</script>"), MARKE)
        self.assertNotIn("<script>", seite)

    def test_ein_wort_darf_im_tipp_hervorgehoben_werden(self):
        # Die Punkte dürfen <b> tragen - das ist gewollt und darf nicht
        # mit entschärft werden.
        eigen = dict(TIPP, bloecke=[
            dict(BLOCK, punkte=["<b>niemals</b> ölen", "2", "3", "4"]),
            dict(BLOCK), dict(BLOCK)])
        self.assertIn("<b>niemals</b>", grafik.tipp_seite(eigen, MARKE))


class Alternativtext(unittest.TestCase):
    def test_der_produkttext_nennt_preis_und_laufzeit(self):
        text = grafik.alternativtext("produkt", PRODUKT)
        self.assertIn("959,00 €", text)
        self.assertIn("04.10.2026", text)

    def test_der_tipptext_gibt_die_bloecke_wieder(self):
        text = grafik.alternativtext("tipp", TIPP)
        self.assertIn("Wichtig zu beachten", text)
        self.assertIn("Etwas Überraschendes", text)

    def test_auszeichnung_steht_nicht_im_alternativtext(self):
        eigen = dict(TIPP, bloecke=[
            dict(BLOCK, punkte=["<b>niemals</b> ölen", "2", "3", "4"]),
            dict(BLOCK), dict(BLOCK)])
        text = grafik.alternativtext("tipp", eigen)
        self.assertIn("niemals ölen", text)
        self.assertNotIn("<b>", text)


if __name__ == "__main__":
    unittest.main()
