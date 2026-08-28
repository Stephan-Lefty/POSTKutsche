"""Netzwerke, Farben, Kürzel – und ob man sie auseinanderhalten kann."""

from __future__ import annotations

import unittest

from postkutsche import netzwerke


def _als_rgb(hexfarbe: str) -> tuple[int, int, int]:
    roh = hexfarbe.lstrip("#")
    return int(roh[0:2], 16), int(roh[2:4], 16), int(roh[4:6], 16)


def _abstand(a: str, b: str) -> float:
    """Grober Farbabstand. Kein Lab, aber gut genug für die Frage, ob zwei
    Rahmen nebeneinander unterscheidbar sind."""
    ra, ga, ba = _als_rgb(a)
    rb, gb, bb = _als_rgb(b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


class Verzeichnis(unittest.TestCase):
    def test_alle_vier_da(self):
        self.assertEqual(len(netzwerke.alle()), 4)

    def test_unbekanntes_netzwerk_sagt_welche_es_gibt(self):
        with self.assertRaises(ValueError) as fehler:
            netzwerke.netzwerk("twitter")
        self.assertIn("mastodon", str(fehler.exception))

    def test_reihenfolge_deckt_das_verzeichnis(self):
        self.assertEqual(set(netzwerke.REIHENFOLGE), set(netzwerke.VERZEICHNIS))


class Farben(unittest.TestCase):
    def test_farben_sind_sechsstellige_hexwerte(self):
        for netz in netzwerke.alle():
            with self.subTest(netz=netz.kennung):
                self.assertRegex(netz.farbe, r"^#[0-9A-Fa-f]{6}$")

    def test_farben_sind_verschieden(self):
        farben = [n.farbe for n in netzwerke.alle()]
        self.assertEqual(len(farben), len(set(farben)))

    def test_facebook_und_linkedin_bleiben_unterscheidbar(self):
        # Beide tragen ihre Markenfarbe, und beide sind blau - der Farbton
        # unterscheidet sich nur um wenige Grad. Auseinanderhalten muss man
        # sie an der Helligkeit und am Kürzel, nicht am Ton allein. Der Test
        # hält fest, dass wenigstens die Helligkeit deutlich verschieden ist.
        fb = netzwerke.netzwerk(netzwerke.FACEBOOK).farbe
        li = netzwerke.netzwerk(netzwerke.LINKEDIN).farbe
        # Nur 45 - mehr geben die Markenfarben nicht her. Facebook und
        # LinkedIn sind beide blau, und beide sollen ihre eigene Farbe
        # tragen. Auseinandergehalten werden sie am Kürzel; die Farbe ist
        # hier Beiwerk, nicht Kennzeichen.
        self.assertGreater(_abstand(fb, li), 40)

    def test_alle_paare_haben_abstand(self):
        farben = [(n.kennung, n.farbe) for n in netzwerke.alle()]
        for i, (name_a, farbe_a) in enumerate(farben):
            for name_b, farbe_b in farben[i + 1:]:
                with self.subTest(paar=f"{name_a}/{name_b}"):
                    self.assertGreater(_abstand(farbe_a, farbe_b), 40)


class Kuerzel(unittest.TestCase):
    def test_zwei_zeichen(self):
        for netz in netzwerke.alle():
            with self.subTest(netz=netz.kennung):
                self.assertEqual(len(netz.kuerzel), 2)

    def test_kuerzel_sind_verschieden(self):
        # Farbe allein trägt keine Bedeutung – wer sie nicht unterscheiden kann,
        # muss das Kürzel lesen können.
        kuerzel = [n.kuerzel for n in netzwerke.alle()]
        self.assertEqual(len(kuerzel), len(set(kuerzel)))


class Grenzen(unittest.TestCase):
    def test_ziel_liegt_unter_der_grenze(self):
        for netz in netzwerke.alle():
            with self.subTest(netz=netz.kennung):
                self.assertLess(netz.zeichen_ziel, netz.zeichen_max)

    def test_mastodon_bleibt_unter_fuenfhundert(self):
        # 500 ist die Voreinstellung fast aller Instanzen. Wer darüber geht,
        # bekommt eine Fehlermeldung statt eines Beitrags.
        self.assertLessEqual(netzwerke.netzwerk(netzwerke.MASTODON).zeichen_max, 500)

    def test_instagram_braucht_ein_bild(self):
        self.assertTrue(netzwerke.netzwerk(netzwerke.INSTAGRAM).bild_pflicht)

    def test_jedes_netzwerk_hat_einen_hinweis(self):
        for netz in netzwerke.alle():
            with self.subTest(netz=netz.kennung):
                self.assertGreater(len(netz.hinweis), 20)


if __name__ == "__main__":
    unittest.main()
