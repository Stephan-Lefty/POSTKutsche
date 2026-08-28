"""Kampagnen: Kalenderwochen, Termine, Streuung über Produkte."""

from __future__ import annotations

import unittest
from datetime import date

from hilfen import OhneEigeneKonfiguration
from postkutsche import kampagnen, sendezeiten, zeiten
from postkutsche.netzwerke import FACEBOOK, LINKEDIN


def _kampagne(**änderungen):
    vorgabe = dict(
        thema="Warengruppe des Monats", projekt="shop",
        kalenderwoche=36, jahr=2026,
    )
    vorgabe.update(änderungen)
    return kampagnen.Kampagne(**vorgabe)


class Anlegen(unittest.TestCase):
    def test_anzahl_ergibt_sich_aus_tagen_und_je_tag(self):
        self.assertEqual(_kampagne(je_tag=2).anzahl, 10)  # 5 Werktage × 2
        self.assertEqual(_kampagne(je_tag=1).anzahl, 5)

    def test_kalenderwoche_wird_geprueft(self):
        for falsch in (0, 54, -1):
            with self.subTest(kw=falsch):
                with self.assertRaises(ValueError):
                    _kampagne(kalenderwoche=falsch)

    def test_je_tag_muss_mindestens_eins_sein(self):
        with self.assertRaises(ValueError):
            _kampagne(je_tag=0)

    def test_ohne_tage_keine_kampagne(self):
        with self.assertRaises(ValueError):
            _kampagne(tage=())


class Kalenderwochen(unittest.TestCase):
    def test_kw_36_2026(self):
        self.assertEqual(kampagnen.woche_beginnt(2026, 36), date(2026, 8, 31))

    def test_beginnt_immer_montags(self):
        for kw in (1, 10, 27, 52):
            with self.subTest(kw=kw):
                self.assertEqual(kampagnen.woche_beginnt(2026, kw).weekday(), 0)

    def test_kw_1_kann_im_vorjahr_beginnen(self):
        # Die erste Woche ist die mit dem ersten Donnerstag – KW 1 von 2026
        # beginnt am 29. Dezember 2025. Selbst gerechnet geht das schief.
        self.assertEqual(kampagnen.woche_beginnt(2026, 1), date(2025, 12, 29))


class Termine(unittest.TestCase):
    def test_ein_termin_je_beitrag(self):
        kampagne = _kampagne(je_tag=2)
        termine = kampagnen.termine(kampagne, FACEBOOK, sendezeiten.HANDWERK)
        self.assertEqual(len(termine), kampagne.anzahl)

    def test_termine_liegen_in_der_richtigen_woche(self):
        termine = kampagnen.termine(_kampagne(), FACEBOOK, sendezeiten.HANDWERK)
        for stempel, _ in termine:
            tag = zeiten.nach_ortszeit(stempel).date()
            self.assertGreaterEqual(tag, date(2026, 8, 31))
            self.assertLessEqual(tag, date(2026, 9, 6))

    def test_keine_zwei_beitraege_zur_selben_minute(self):
        # Zwei Beiträge zur selben Zeit sieht niemand – der eine verdeckt den
        # anderen.
        termine = kampagnen.termine(_kampagne(je_tag=3), FACEBOOK, sendezeiten.HANDWERK)
        stempel = [s for s, _ in termine]
        self.assertEqual(len(stempel), len(set(stempel)))

    def test_mehr_beitraege_als_fenster_wird_versetzt(self):
        # LinkedIn hat für das Handwerk drei Fenster. Bei vier Beiträgen am Tag
        # muss der vierte versetzt werden, nicht doppelt gelegt.
        termine = kampagnen.termine(
            _kampagne(je_tag=4, tage=(sendezeiten.DI,)), LINKEDIN, sendezeiten.HANDWERK
        )
        self.assertEqual(len(termine), 4)
        self.assertEqual(len({s for s, _ in termine}), 4)
        self.assertIn("versetzt", termine[-1][1])

    def test_termine_sind_aufsteigend(self):
        termine = kampagnen.termine(_kampagne(je_tag=2), FACEBOOK, sendezeiten.HANDWERK)
        stempel = [s for s, _ in termine]
        self.assertEqual(stempel, sorted(stempel))

    def test_jeder_termin_hat_eine_begruendung(self):
        for _, grund in kampagnen.termine(_kampagne(), FACEBOOK, sendezeiten.HANDWERK):
            self.assertTrue(grund)

    def test_wochenende_wenn_ausdruecklich_gewuenscht(self):
        kampagne = _kampagne(tage=(sendezeiten.SA, sendezeiten.SO))
        termine = kampagnen.termine(kampagne, FACEBOOK, sendezeiten.VERBRAUCHER)
        for stempel, _ in termine:
            self.assertIn(zeiten.nach_ortszeit(stempel).weekday(), (5, 6))

    def test_termin_auch_wenn_kein_fenster_auf_den_tag_faellt(self):
        # LinkedIn hat samstags kein Fenster. Wer trotzdem samstags will,
        # bekommt einen Termin statt einer leeren Liste.
        kampagne = _kampagne(tage=(sendezeiten.SA,))
        termine = kampagnen.termine(kampagne, LINKEDIN, sendezeiten.HANDWERK)
        self.assertEqual(len(termine), 1)
        self.assertEqual(zeiten.nach_ortszeit(termine[0][0]).weekday(), 5)


def _produkte(*paare):
    return [{"kategorie": kat, "titel": titel} for kat, titel in paare]


class Streuen(unittest.TestCase):
    def test_leere_eingabe(self):
        self.assertEqual(kampagnen.streuen([], 5), [])

    def test_null_gewuenscht(self):
        self.assertEqual(kampagnen.streuen(_produkte(("a", "x")), 0), [])

    def test_nicht_mehr_als_vorhanden(self):
        # Lieber weniger Beiträge als derselbe Beitrag zweimal.
        gewaehlt = kampagnen.streuen(_produkte(("a", "x"), ("a", "y")), 10)
        self.assertEqual(len(gewaehlt), 2)

    def test_keine_wiederholungen(self):
        produkte = _produkte(*[("a", f"tuer {i}") for i in range(6)])
        gewaehlt = kampagnen.streuen(produkte, 4)
        self.assertEqual(len({p["titel"] for p in gewaehlt}), 4)

    def test_wechselt_zwischen_kategorien(self):
        # Wer zwei Kategorien angibt, will nicht drei Tage die eine.
        produkte = _produkte(
            *[("K1", f"ware eins {i}") for i in range(5)],
            *[("K2", f"ware zwei {i}") for i in range(5)],
        )
        kategorien = [p["kategorie"] for p in kampagnen.streuen(produkte, 4)]
        self.assertEqual(kategorien.count("K1"), 2)
        self.assertEqual(kategorien.count("K2"), 2)

    def test_massvarianten_kommen_zuletzt(self):
        # »… Breite 1500 mm«, »… Breite 1750 mm«, »… Breite 2000 mm« sind für
        # einen Leser dasselbe Produkt. Solange es anderes gibt, kommt das
        # andere zuerst.
        produkte = _produkte(
            ("B", "Modell X einflügelig Breite 1500 mm Höhe 4000mm"),
            ("B", "Modell X einflügelig Breite 1750 mm Höhe 4000mm"),
            ("B", "Modell X einflügelig Breite 2000 mm Höhe 4000mm"),
            ("B", "Notausgang Sonderbau"),
        )
        titel = [p["titel"] for p in kampagnen.streuen(produkte, 2)]
        self.assertIn("Notausgang Sonderbau", titel)

    def test_ohne_kategorie_geht_auch(self):
        produkte = [{"titel": f"tuer {i}"} for i in range(4)]
        self.assertEqual(len(kampagnen.streuen(produkte, 3)), 3)

    def test_alle_ausgewaehlten_stammen_aus_der_eingabe(self):
        produkte = _produkte(("a", "x"), ("b", "y"), ("a", "z"))
        titel = {p["titel"] for p in produkte}
        for gewaehlt in kampagnen.streuen(produkte, 3):
            self.assertIn(gewaehlt["titel"], titel)


class Hersteller(OhneEigeneKonfiguration):
    """Herstellerfilter, geprüft an den Beispielmarken aus BEISPIEL_HERSTELLER.

    Mit welchen Herstellern tatsächlich gearbeitet wird, steht in
    ~/.config/postkutsche/hersteller.json und nicht im Repository.
    """

    def setUp(self):
        super().setUp()
        self.produkte = [
            {"kategorie": "A", "titel": "Brandschutztür Musterwerk Trockenbauwand",
             "adresse": "https://x.example/tuer-musterwerk_2905.html"},
            {"kategorie": "B", "titel": "Tür Modell BB7 einflügelig",
             "adresse": "https://x.example/bb7_4149.html"},
            {"kategorie": "A", "titel": "Tür ohne Marke im Namen",
             "adresse": "https://x.example/tuer_9999.html"},
        ]

    def test_hersteller_aus_dem_namen(self):
        self.assertEqual(kampagnen.hersteller_von(self.produkte[0]), "musterwerk")

    def test_hersteller_aus_der_modellreihe(self):
        # Nicht jedes Produkt trägt den Hersteller im Namen; manche heißen nur
        # nach ihrer Modellreihe. Ohne die Zuordnung fielen sie durch.
        self.assertEqual(kampagnen.hersteller_von(self.produkte[1]), "beispielbau")

    def test_ohne_hinweis_kein_hersteller(self):
        self.assertIsNone(kampagnen.hersteller_von(self.produkte[2]))

    def test_name_schlaegt_modellreihe(self):
        # Ein Produkt mit dem Herstellernamen ist dessen Produkt, auch wenn
        # irgendwo eine fremde Modellbezeichnung vorkommt.
        produkt = {"titel": "Musterwerk Tür mit BB7-ähnlichem Beschlag", "adresse": ""}
        self.assertEqual(kampagnen.hersteller_von(produkt), "musterwerk")

    def test_schreibvarianten_finden_dasselbe(self):
        for schreibweise in ("Musterwerk", "musterwerk", "MUSTERWERK", "Muster-Werk"):
            with self.subTest(schreibweise=schreibweise):
                passend, _ = kampagnen.nach_hersteller(self.produkte, [schreibweise])
                self.assertEqual(len(passend), 1)

    def test_unbekannter_hersteller_ist_ein_fehler(self):
        # Eine Kampagne, die stillschweigend null Beiträge erzeugt, fällt erst
        # am Montag auf – wenn nichts erscheint.
        with self.assertRaises(kampagnen.UnbekannterHersteller) as fehler:
            kampagnen.nach_hersteller(self.produkte, ["Gibtsnicht"])
        self.assertIn("musterwerk", str(fehler.exception))

    def test_nicht_zuzuordnendes_wird_gemeldet(self):
        # Sonst fehlen in einer Herstellerwoche zwei Türen, und niemand
        # erfährt, warum.
        _, unklar = kampagnen.nach_hersteller(self.produkte, ["Musterwerk"])
        self.assertEqual(len(unklar), 1)
        self.assertEqual(unklar[0]["titel"], "Tür ohne Marke im Namen")

    def test_mehrere_hersteller(self):
        passend, unklar = kampagnen.nach_hersteller(
            self.produkte, ["Musterwerk", "Beispielbau"]
        )
        self.assertEqual(len(passend), 2)
        self.assertEqual(len(unklar), 1)

    def test_ohne_angabe_passt_alles(self):
        passend, unklar = kampagnen.nach_hersteller(self.produkte, [])
        self.assertEqual(len(passend), 3)
        self.assertEqual(unklar, [])

    def test_kennung_kommt_ans_produkt(self):
        passend, _ = kampagnen.nach_hersteller(self.produkte, ["Musterwerk"])
        self.assertEqual(passend[0]["hersteller"], "musterwerk")

    def test_eingabe_bleibt_unveraendert(self):
        kampagnen.nach_hersteller(self.produkte, ["Musterwerk"])
        self.assertNotIn("hersteller", self.produkte[0])

    def test_kennung_von_unbekanntem(self):
        self.assertIsNone(kampagnen.kennung_von("Gibtsnicht"))
        self.assertIsNone(kampagnen.kennung_von(""))

    def test_herstellerwoche_streut_ueber_kategorien(self):
        # Eine Herstellerwoche geht quer durch die Kategorien, nicht durch eine.
        produkte = [
            {"kategorie": f"K{i % 2 + 1}", "titel": f"Musterwerk Tür Modell {i}",
             "adresse": ""} for i in range(6)
        ]
        passend, _ = kampagnen.nach_hersteller(produkte, ["Musterwerk"])
        kategorien = [p["kategorie"] for p in kampagnen.streuen(passend, 4)]
        self.assertEqual(kategorien.count("K1"), 2)
        self.assertEqual(kategorien.count("K2"), 2)

    def test_kampagne_nimmt_hersteller_entgegen(self):
        kampagne = _kampagne(hersteller=["Musterwerk"])
        self.assertEqual(kampagne.hersteller, ["Musterwerk"])

    def test_kampagne_ohne_hersteller_ist_leer(self):
        self.assertEqual(_kampagne().hersteller, [])

    def test_eigene_hersteller_stechen_die_beispiele(self):
        # Wer eine eigene hersteller.json anlegt, arbeitet mit seinen Marken –
        # die Beispiele verschwinden dann vollständig.
        from pathlib import Path
        import json

        Path(self.konfigurationsordner, "hersteller.json").write_text(
            json.dumps({"eigenmarke": {"namen": ["eigenmarke"], "reihen": ["em9"]}}),
            encoding="utf-8",
        )
        kampagnen.hersteller_neu_laden()
        self.assertEqual(
            kampagnen.hersteller_von({"titel": "Eigenmarke Tür", "adresse": ""}),
            "eigenmarke",
        )
        self.assertIsNone(
            kampagnen.hersteller_von({"titel": "Musterwerk Tür", "adresse": ""})
        )


class Modellreihen(OhneEigeneKonfiguration):
    """Modellreihen werden am Wortanfang und ohne folgende Ziffer geprüft."""

    def pruefe(self, titel, erwartet):
        self.assertEqual(
            kampagnen.hersteller_von({"titel": titel, "adresse": ""}), erwartet
        )

    def test_reihen_werden_erkannt(self):
        for titel, erwartet in (
            ("Tür Modell MW12 zweiflügelig", "musterwerk"),
            ("mw40_zweifluegelige_tuer", "musterwerk"),
            ("Modell BB7 einflügelig", "beispielbau"),
        ):
            with self.subTest(titel=titel):
                self.pruefe(titel, erwartet)

    def test_aehnliche_nummern_werden_nicht_verwechselt(self):
        # »mw12« soll »mw12x« treffen, aber nicht »mw120«. Ohne die Prüfung auf
        # eine folgende Ziffer bewürbe eine Herstellerwoche fremde Ware.
        for titel in (
            "Tür Modell MW120 von wem auch immer",
            "Modell MW125 Spezial",
            "Beschlag BB70 Variante",
            "Baustellentür mit Spindel-Schnellverstellung",
        ):
            with self.subTest(titel=titel):
                self.pruefe(titel, None)

    def test_reihe_wird_auch_in_der_adresse_gefunden(self):
        produkt = {"titel": "Brandschutztür einflügelig",
                   "adresse": "https://x.example/serie_mw40_4149.html"}
        self.assertEqual(kampagnen.hersteller_von(produkt), "musterwerk")


class Preise(unittest.TestCase):
    def test_preise_sind_standardmaessig_aus(self):
        # Ein Preis ändert sich, der Beitrag bleibt stehen. Wer das umstellt,
        # soll es ausdrücklich tun.
        self.assertFalse(_kampagne().preise)

    def test_preise_lassen_sich_einschalten(self):
        self.assertTrue(_kampagne(preise=True).preise)


if __name__ == "__main__":
    unittest.main()
