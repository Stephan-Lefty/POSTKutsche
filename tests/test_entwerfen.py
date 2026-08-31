"""Der Weg vom Inhalt zum Entwurf."""

from __future__ import annotations

import unittest
from unittest import mock

from postkutsche import entwerfen
from postkutsche.ablage import BEITRAG_RUECKFRAGE, Ablage, RueckfrageOffen

INHALT = {
    "fremd_id": "1", "titel": "Eine Tür", "text": "Kurzer Text.",
    "adresse": "https://shop.example/tuer_1.html",
    "bild_adresse": None, "kategorien": [],
}


class Rueckfragen(unittest.TestCase):
    """Eine Rückfrage muss in der Ablage landen, nicht nur auf dem Schirm."""

    def setUp(self):
        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "seitenkarte"
        )
        # Zweiter Abruf vortäuschen: Der erste bleibt absichtlich stumm.
        self.ablage.geholt_vermerken(self.projekt.id)

    def _lauf(self, rueckfrage):
        antwort = {"facebook": {"text": "Ein Text.", "schlagworte": "tuer",
                                "rueckfrage": rueckfrage}}
        with mock.patch.object(entwerfen, "inhalte_holen", return_value=[INHALT]), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True), \
             mock.patch("postkutsche.denker.schreiben", return_value=antwort):
            return entwerfen.entwerfen(
                self.ablage, "shop", ["facebook"], melden=lambda *a: None
            )

    def test_rueckfrage_wird_gespeichert(self):
        beitrag = self._lauf("Was leistet die Spindel genau?")[0]
        offen = self.ablage.rueckfragen(beitrag)
        self.assertEqual(len(offen), 1)
        self.assertIn("Spindel", offen[0]["rueckfrage"])

    def test_rueckfrage_blockiert_die_freigabe(self):
        # Der ganze Zweck: Was unklar ist, geht nicht ungeprüft raus.
        beitrag = self._lauf("Ist Steinau der Hersteller?")[0]
        self.assertEqual(self.ablage.beitrag(beitrag)["zustand"], BEITRAG_RUECKFRAGE)
        with self.assertRaises(RueckfrageOffen):
            self.ablage.freigeben(beitrag)

    def test_ohne_rueckfrage_freigebbar(self):
        beitrag = self._lauf(None)[0]
        self.assertEqual(self.ablage.rueckfragen(beitrag), [])
        self.ablage.freigeben(beitrag)


class PausiertesProjekt(unittest.TestCase):
    def test_wird_nicht_abgerufen(self):
        ablage = Ablage(":memory:")
        self.addCleanup(ablage.schliessen)
        ablage.projekt_anlegen("shop", "Shop", "https://shop.example", "seitenkarte")
        ablage.projekt_zustand("shop", "pausiert")
        with self.assertRaises(entwerfen.EntwurfFehler) as f:
            entwerfen.entwerfen(ablage, "shop", ["facebook"], melden=lambda *a: None)
        self.assertIn("pausiert", str(f.exception))


if __name__ == "__main__":
    unittest.main()


class Wiederholungen(unittest.TestCase):
    """Was in den letzten vier Wochen dran war, wird gemeldet.

    Sonst bewirbt man im September dieselbe Tür wie im August, ohne es zu
    merken - bei einem Sortiment mit hundert Artikeln fällt das niemandem auf.
    """

    def setUp(self):
        from postkutsche import zeiten

        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "seitenkarte"
        )
        self.zeiten = zeiten

    def _beitrag_fuer(self, adresse, vor_tagen, gesendet=True):
        """Legt einen Beitrag an. Standardmäßig als gesendet vermerkt, damit
        das Aufräumen ihn stehen lässt - hier geht es um die
        Wiederholungsprüfung, nicht ums Aufräumen."""
        from datetime import timedelta

        nummer, _ = self.ablage.inhalt_merken(
            self.projekt.id, adresse, "Eine Tür", adresse
        )
        wann = self.zeiten.schreiben(
            self.zeiten.lesen(self.zeiten.jetzt_utc()) - timedelta(days=vor_tagen)
        )
        beitrag = self.ablage.beitrag_anlegen(self.projekt.id, wann, inhalt_id=nummer)
        if gesendet:
            from postkutsche.ablage import FASSUNG_GESENDET

            kennung = self.ablage.fassung_setzen(beitrag, "facebook", "Text")
            self.ablage.fassung_vermerken(kennung, FASSUNG_GESENDET)
        return beitrag

    def test_kuerzlich_beworbenes_wird_gefunden(self):
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_1.html", 10)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_1.html", "titel": "Tür"}],
        )
        self.assertEqual(len(treffer), 1)
        self.assertIn("tuer_1", treffer[0]["adresse"])

    def test_aelteres_faellt_nicht_auf(self):
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_1.html", 60)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_1.html", "titel": "Tür"}],
        )
        self.assertEqual(treffer, [])

    def test_unbekanntes_produkt_ist_frei(self):
        from postkutsche import kampagnenlauf

        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/neu_9.html", "titel": "Neu"}],
        )
        self.assertEqual(treffer, [])

    def test_geplantes_zaehlt_mit(self):
        # Ein Produkt, das für nächste Woche schon eingeplant ist, soll nicht
        # ein zweites Mal drankommen, nur weil der Beitrag noch nicht raus ist.
        from postkutsche import kampagnenlauf

        self._beitrag_fuer("https://shop.example/tuer_2.html", -3)
        treffer = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id,
            [{"adresse": "https://shop.example/tuer_2.html", "titel": "Tür"}],
        )
        self.assertEqual(len(treffer), 1)

    def test_lauf_bricht_ab_und_fragt(self):
        from postkutsche import kampagnen, kampagnenlauf

        adresse = "https://shop.example/tuer_1.html"
        self._beitrag_fuer(adresse, 5)
        self.ablage.geholt_vermerken(self.projekt.id)
        k = kampagnen.Kampagne(thema="Probe", projekt="shop",
                               kalenderwoche=36, jahr=2026, je_tag=1)

        with mock.patch.object(kampagnenlauf, "produkte_sammeln",
                               return_value=[{"adresse": adresse, "titel": "Tür",
                                              "kategorie": "a"}]), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True):
            bericht = kampagnenlauf.ausfuehren(self.ablage, k)

        self.assertTrue(bericht["rueckfrage"])
        self.assertEqual(bericht["anzahl"], 0)
        self.assertEqual(len(bericht["wiederholungen"]), 1)

    def test_ersetzen_nimmt_andere_produkte(self):
        # Absagen soll »nimm andere« heißen, nicht »mach gar nichts«.
        from postkutsche import kampagnen, kampagnenlauf

        alt = "https://shop.example/alt_1.html"
        neu = "https://shop.example/neu_2.html"
        self._beitrag_fuer(alt, 5)
        self.ablage.geholt_vermerken(self.projekt.id)

        vorrat = [
            {"adresse": alt, "titel": "Alte Tür", "kategorie": "a"},
            {"adresse": neu, "titel": "Neue Tür", "kategorie": "a"},
        ]
        k = kampagnen.Kampagne(thema="Probe", projekt="shop",
                               kalenderwoche=36, jahr=2026, je_tag=1,
                               tage=(0,))
        antwort = {"facebook": {"text": "Text", "schlagworte": "", "rueckfrage": None}}

        with mock.patch.object(kampagnenlauf, "produkte_sammeln", return_value=vorrat), \
             mock.patch.object(kampagnenlauf.seitenkarte, "seite",
                               return_value={"fremd_id": neu, "titel": "Neue Tür",
                                             "text": "x", "adresse": neu,
                                             "bild_adresse": None, "kategorien": []}), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True), \
             mock.patch("postkutsche.denker.schreiben", return_value=antwort):
            bericht = kampagnenlauf.ausfuehren(
                self.ablage, k, wiederholungen=kampagnenlauf.ERSETZEN
            )

        self.assertEqual(bericht["anzahl"], 1)
        self.assertNotIn("rueckfrage", bericht)

    def test_ersetzen_meldet_wenn_nichts_uebrig_ist(self):
        from postkutsche import kampagnen, kampagnenlauf

        alt = "https://shop.example/alt_1.html"
        self._beitrag_fuer(alt, 5)
        self.ablage.geholt_vermerken(self.projekt.id)
        k = kampagnen.Kampagne(thema="Probe", projekt="shop",
                               kalenderwoche=36, jahr=2026, je_tag=1, tage=(0,))

        with mock.patch.object(kampagnenlauf, "produkte_sammeln",
                               return_value=[{"adresse": alt, "titel": "Alt",
                                              "kategorie": "a"}]), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True):
            bericht = kampagnenlauf.ausfuehren(
                self.ablage, k, wiederholungen=kampagnenlauf.ERSETZEN
            )

        self.assertEqual(bericht["anzahl"], 0)
        self.assertIn("schon dran", bericht["hinweis"])


class KampagnenLesenNichtDieSeitenkarte(unittest.TestCase):
    """Die Produkte einer Kampagne kommen von der Kategorieseite.

    Am 2026-08-31 nachgemessen, weil die Vermutung im Raum stand, sie kaemen
    aus `sitemap.xml`: Von 60 Adressen, die nur die Seitenkarte kennt und die
    Navigation nicht verlinkt, leben sieben - elf Prozent. Die Karte
    zusaetzlich heranzuziehen wuerde den Vorrat zu knapp der Haelfte mit
    toten Adressen fuellen, und jede davon kostet beim Planen einen Platz in
    der Woche: `ausfuehren` waehlt genau `anzahl` Produkte und sucht fuer ein
    gescheitertes keinen Ersatz.
    """

    def test_es_wird_nur_die_kategorieseite_geholt(self):
        from unittest import mock

        from postkutsche import kampagnen, kampagnenlauf
        from postkutsche.quellen import seitenkarte

        geholt = []

        def antworten(adresse):
            geholt.append(adresse)
            return '<a href="/kat_1/tuer_1810.html">Tür</a>'

        k = kampagnen.Kampagne(
            thema="", projekt="shop", kalenderwoche=36, jahr=2026,
            kategorien=["https://shop.example/kat_1/list.html"])

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            gefunden = kampagnenlauf.produkte_sammeln(k)

        self.assertEqual(geholt, ["https://shop.example/kat_1/list.html"])
        self.assertFalse([a for a in geholt if "sitemap" in a])
        self.assertEqual(len(gefunden), 1)

    def test_folgeseiten_kommen_in_die_kampagne(self):
        from unittest import mock

        from postkutsche import kampagnen, kampagnenlauf
        from postkutsche.quellen import seitenkarte

        kat = "https://shop.example/kat_1/list.html"
        seiten = {
            kat: ('<a href="/kat_1/a_1.html">A</a>'
                  '<a href="/kat_1/list.html?page=2">2</a>'),
            f"{kat}?page=2": '<a href="/kat_1/b_2.html">B</a>',
        }
        k = kampagnen.Kampagne(thema="", projekt="shop", kalenderwoche=36,
                               jahr=2026, kategorien=[kat])

        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=lambda a: seiten[a]):
            gefunden = kampagnenlauf.produkte_sammeln(k)

        self.assertEqual([p["adresse"] for p in gefunden], [
            "https://shop.example/kat_1/a_1.html",
            "https://shop.example/kat_1/b_2.html",
        ])


class AbbrechenBrichtAb(unittest.TestCase):
    """Abbrechen heisst abbrechen und wegraeumen, nicht »hier stehen bleiben«.

    Vorher schloss der Knopf nur das Fenster: Der Lauf lief im Dienst weiter,
    legte Beitraege an und hielt die Sperre. Am 2026-08-31 nachgemessen -
    nach dem Anhalten mitten im Lauf standen fuenf Beitraege in der Ablage,
    und fuenf von zehn Produkten galten ueber die Vier-Wochen-Regel als
    beworben, obwohl nie etwas erschienen war.
    """

    def setUp(self):
        from postkutsche.ablage import Ablage

        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)
        self.projekt = self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "seitenkarte")
        self.produkte = [
            {"adresse": f"https://shop.example/kat_1/t_{n}.html",
             "titel": f"Tür {n}", "kategorie": "kat_1"} for n in range(1, 7)]

    def _laufen(self, abbrechen, anzahl=6):
        from unittest import mock

        from postkutsche import kampagnen, kampagnenlauf

        def seite(adresse):
            return {"fremd_id": adresse, "titel": adresse.rsplit("/", 1)[-1],
                    "text": "Text.", "adresse": adresse, "bild_adresse": None,
                    "veroeffentlicht": None, "kategorien": []}

        k = kampagnen.Kampagne(
            thema="", projekt="shop", kalenderwoche=36, jahr=2026,
            kategorien=["https://shop.example/kat_1/list.html"],
            netzwerke=["facebook"], je_tag=2)

        with mock.patch.object(kampagnenlauf, "produkte_sammeln",
                               return_value=self.produkte), \
             mock.patch("postkutsche.denker.verfuegbar", return_value=True), \
             mock.patch("postkutsche.denker.schreiben", return_value={
                 "facebook": {"text": "Ein Text.", "schlagworte": "",
                              "rueckfrage": None}}), \
             mock.patch("postkutsche.quellen.seitenkarte.seite",
                        side_effect=seite):
            return kampagnenlauf.ausfuehren(self.ablage, k, bestaetigt=True,
                                            abbrechen=abbrechen)

    def _zaehlen(self):
        return (
            self.ablage.db.execute("SELECT COUNT(*) FROM beitraege").fetchone()[0],
            self.ablage.db.execute("SELECT COUNT(*) FROM inhalte").fetchone()[0],
        )

    def test_ohne_abbruch_laeuft_alles_durch(self):
        bericht = self._laufen(lambda: False)
        self.assertGreater(bericht["anzahl"], 0)
        self.assertFalse(bericht["abgebrochen"])

    def _sobald(self, beitraege: int):
        """Bricht ab, sobald so viele Beitraege in der Ablage stehen.

        Unabhaengig davon, an wie vielen Stellen gefragt wird: `ausfuehren`
        fragt auch schon nach dem Sammeln, und ein Test, der Aufrufe zaehlt,
        geht bei der naechsten Pruefstelle kaputt.
        """
        return lambda: self._zaehlen()[0] >= beitraege

    def test_abbruch_nach_zwei_raeumt_beide_weg(self):
        bericht = self._laufen(self._sobald(2))
        self.assertTrue(bericht["abgebrochen"])
        self.assertEqual(bericht["entfernt"], 2)
        self.assertEqual(bericht["anzahl"], 0)
        beitraege, inhalte = self._zaehlen()
        self.assertEqual(beitraege, 0)
        # Der Inhalt geht mit, sonst gilt das Produkt vier Wochen als
        # beworben, obwohl nie etwas erschienen ist.
        self.assertEqual(inhalte, 0)

    def test_nach_dem_abbruch_ist_kein_produkt_gesperrt(self):
        from postkutsche import kampagnenlauf

        self._laufen(self._sobald(2))
        gesperrt = kampagnenlauf.wiederholungen_finden(
            self.ablage, self.projekt.id, self.produkte)
        self.assertEqual(gesperrt, [])

    def test_abbruch_vor_dem_ersten_produkt_legt_nichts_an(self):
        bericht = self._laufen(lambda: True)
        self.assertTrue(bericht["abgebrochen"])
        self.assertEqual(bericht["entfernt"], 0)
        self.assertEqual(self._zaehlen(), (0, 0))

    def test_der_bericht_sagt_was_geschah(self):
        # Stilles Verschwinden waere das Schlimmste: Dann fragt man sich, wo
        # die angefangenen Entwuerfe geblieben sind.
        bericht = self._laufen(self._sobald(1))
        self.assertIn("Abgebrochen", bericht["hinweis"])
        self.assertIn("entfernt", bericht["hinweis"])

    def test_veroeffentlichtes_bleibt_stehen(self):
        # Die Regel wird auch beim Aufraeumen nicht zur Ausnahme gemacht.
        from postkutsche.ablage import FASSUNG_GESENDET

        def abbrechen():
            beitraege = self._zaehlen()[0]
            if beitraege == 2:
                # So tun, als waere der erste Beitrag schon draussen.
                fassung = self.ablage.db.execute(
                    "SELECT id FROM fassungen ORDER BY id LIMIT 1").fetchone()
                self.ablage.fassung_vermerken(int(fassung["id"]), FASSUNG_GESENDET)
                return True
            return False

        bericht = self._laufen(abbrechen)
        self.assertEqual(bericht["entfernt"], 1)
        beitraege, _ = self._zaehlen()
        self.assertEqual(beitraege, 1)
