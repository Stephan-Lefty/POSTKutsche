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


class Wochenformate(unittest.TestCase):
    """Tipp und Produkt der Woche füllen auch die Felder der Grafik."""

    QUELLE = {"titel": "Gedämmte Bodentreppe", "adresse": "https://x.example/t.html",
              "preis": {"jetzt": "959,00 €", "vorher": "1.100,00 €"},
              "gueltig": "Sonntag, 04.10.2026", "merkmale": ["U-Wert 0,7"],
              "text": "Beschreibung."}

    def test_beim_produkt_ist_der_preis_ausdruecklich_erlaubt(self):
        # Die Grundregeln verbieten Preise, weil ein Beitrag stehenbleibt und
        # ein Preis sich ändert. Hier steht dabei, bis wann das Angebot gilt.
        anweisung = vorlagen.wochenanweisung("produkt", self.QUELLE, ["facebook"])
        self.assertIn("Keine Preise nennen", anweisung)      # die Grundregel
        self.assertIn("Der Preis gehört hinein", anweisung)  # und die Ausnahme

    def test_der_preis_aus_dem_fliesstext_wird_ausdruecklich_verboten(self):
        anweisung = vorlagen.wochenanweisung("produkt", self.QUELLE, ["facebook"])
        self.assertIn("keine Zahl aus dem Fließtext", anweisung)

    def test_beim_tipp_steht_nur_das_thema_in_der_anweisung(self):
        anweisung = vorlagen.wochenanweisung(
            "tipp", {"thema": "Herbstpflege von Außentüren"}, ["facebook"])
        self.assertIn("Herbstpflege von Außentüren", anweisung)
        self.assertIn("Genau drei Blöcke", anweisung)

    def test_ohne_netzwerk_gibt_es_nichts_zu_schreiben(self):
        with self.assertRaises(ValueError):
            vorlagen.wochenanweisung("produkt", self.QUELLE, [])


class WochenantwortLesen(unittest.TestCase):
    """Was die Fläche erzwingt, wird geprüft – sonst sieht man es erst im Bild."""

    def _antwort(self, grafik):
        import json
        return json.dumps({
            "grafik": grafik,
            "fassungen": {"facebook": {"text": "Ein Satz.", "schlagworte": [],
                                       "rueckfrage": None}}})

    GUT = {"unterzeile": "Bodentreppe – Jetzt zugreifen!",
           "name": "Wippro BasicStair SMART",
           "merkmale": ["U-Wert 0,7 W/m²K", "bis 250 kg", "2,50–2,70 m",
                        "einbaufertig"]}

    def test_vier_merkmale_gehen_durch(self):
        fassungen, grafik = vorlagen.wochenantwort_lesen(
            self._antwort(self.GUT), ["facebook"], "produkt")
        self.assertEqual(len(grafik["merkmale"]), 4)
        self.assertIn("facebook", fassungen)

    def test_fuenf_merkmale_werden_abgelehnt(self):
        # Ein fünftes liefe unten aus der Karte heraus. Lieber neu schreiben
        # lassen als eine Grafik mit abgeschnittener Zeile.
        zu_viele = dict(self.GUT, merkmale=self.GUT["merkmale"] + ["noch eins"])
        with self.assertRaises(vorlagen.AntwortFehler):
            vorlagen.wochenantwort_lesen(self._antwort(zu_viele), ["facebook"], "produkt")

    def test_ein_zu_langes_merkmal_wird_abgelehnt(self):
        lang = dict(self.GUT, merkmale=["x" * 60] + self.GUT["merkmale"][1:])
        with self.assertRaises(vorlagen.AntwortFehler) as fehler:
            vorlagen.wochenantwort_lesen(self._antwort(lang), ["facebook"], "produkt")
        self.assertIn("aus der Karte laufen", str(fehler.exception))

    def test_ohne_grafik_ist_die_antwort_unbrauchbar(self):
        import json
        roh = json.dumps({"fassungen": {"facebook": {"text": "x", "rueckfrage": None}}})
        with self.assertRaises(vorlagen.AntwortFehler):
            vorlagen.wochenantwort_lesen(roh, ["facebook"], "produkt")

    def test_der_tipp_braucht_drei_bloecke_mit_je_vier_punkten(self):
        block = {"titel": "A\nB", "unter": "c", "punkte": ["1", "2", "3", "4"]}
        gut = {"titel": "T", "unterzeile": "U", "vorspann": "v", "warum": "w",
               "bloecke": [block, block, block],
               "beachten": ["a", "b", "c", "d"], "wissen": "x", "cta": "y"}
        _, grafik = vorlagen.wochenantwort_lesen(
            self._antwort(gut), ["facebook"], "tipp")
        self.assertEqual(len(grafik["bloecke"]), 3)

        zwei = dict(gut, bloecke=[block, block])
        with self.assertRaises(vorlagen.AntwortFehler):
            vorlagen.wochenantwort_lesen(self._antwort(zwei), ["facebook"], "tipp")
