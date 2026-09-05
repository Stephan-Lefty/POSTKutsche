"""Ein Blog in der Wochenplanung: Kategorien, Beitragslisten, Anweisung.

Seit dem 2026-09-05 lässt sich eine Woche nicht nur aus einem Shop planen,
sondern auch aus einem WordPress-Blog. Der Unterschied liegt im Weg, nicht im
Ergebnis: WordPress sagt selbst, was in einer Kategorie steht, ein Shop ohne
Schnittstelle muss durchgesehen werden. Was hinten herauskommt, sieht in
beiden Fällen gleich aus - und genau das prüfen die Tests hier.

**Kein Netzzugriff.** Gefälscht wird auf der Ebene, auf der auch die anderen
Quellentests fälschen: `json_holen`, `kopfzeile_holen` und `text_holen` im
jeweiligen Modul. Wer stattdessen `urlopen` verstellte, prüfte urllib mit.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from postkutsche import kampagnen, kampagnenlauf
from postkutsche.denker import vorlagen
from postkutsche.quellen import wordpress
from postkutsche.quellen.abrufen import AbrufFehler

STAMM = "https://blog.example/wp-json/wp/v2"


def projekt(art="wordpress", adresse="https://blog.example", **einstellungen):
    """Ein Projekt, wie es aus der Ablage käme - nur so viel, wie gebraucht wird."""
    return SimpleNamespace(art=art, adresse=adresse, kennung="blog",
                           name="Blog", einstellungen=einstellungen or {})


def kategorie_roh(nummer, name, anzahl, slug=None):
    """Ein Eintrag, wie ihn `/wp/v2/categories` liefert."""
    return {"id": nummer, "name": name, "count": anzahl,
            "slug": slug or name.lower()}


def beitrag_roh(nummer, titel="Ein Beitrag", verweis=None):
    """Ein Eintrag, wie ihn `/wp/v2/posts` mit `_fields` liefert."""
    return {"id": nummer, "title": {"rendered": titel},
            "link": verweis or f"https://blog.example/beitrag-{nummer}/"}


# -- Adressen ---------------------------------------------------------------


class AbfragewerteBleibenErhalten(unittest.TestCase):
    """`_mit_werten` darf nichts verlieren, was schon in der Adresse stand.

    Der Fehler wäre nicht sichtbar, sondern still: Verschwindet
    »?categories=9«, holt die Planung die neuesten Beiträge des ganzen Blogs
    statt der einen gewählten Kategorie. Das Ergebnis sieht plausibel aus -
    es sind ja Beiträge -, nur ist die Kategorieauswahl wirkungslos geworden.
    """

    def test_kategorie_ueberlebt_die_seitenwerte(self):
        adresse = wordpress._mit_werten(
            f"{STAMM}/posts?categories=9", {"per_page": "40", "page": "1"})
        werte = parse_qs(urlsplit(adresse).query)
        self.assertEqual(werte["categories"], ["9"])
        self.assertEqual(werte["per_page"], ["40"])
        self.assertEqual(werte["page"], ["1"])

    def test_der_pfad_bleibt_stehen(self):
        adresse = wordpress._mit_werten(
            f"{STAMM}/posts?categories=9", {"per_page": "40"})
        self.assertEqual(urlsplit(adresse).path, "/wp-json/wp/v2/posts")
        self.assertEqual(urlsplit(adresse).netloc, "blog.example")

    def test_ohne_vorhandene_werte_geht_es_auch(self):
        adresse = wordpress._mit_werten(f"{STAMM}/posts", {"per_page": "20"})
        self.assertEqual(parse_qs(urlsplit(adresse).query), {"per_page": ["20"]})

    def test_neuer_wert_sticht_den_alten(self):
        # Zweimal »page« in einer Adresse wäre eine Wette darauf, welches
        # WordPress nimmt.
        adresse = wordpress._mit_werten(f"{STAMM}/posts?page=1", {"page": "2"})
        self.assertEqual(parse_qs(urlsplit(adresse).query), {"page": ["2"]})

    def test_mehrere_vorhandene_werte_bleiben_alle(self):
        adresse = wordpress._mit_werten(
            f"{STAMM}/posts?categories=9&sticky=1", {"per_page": "40"})
        werte = parse_qs(urlsplit(adresse).query)
        self.assertEqual(werte["categories"], ["9"])
        self.assertEqual(werte["sticky"], ["1"])


class RestAdresseEinesProjekts(unittest.TestCase):
    """Wo die Schnittstelle liegt, steht selten in den Einstellungen."""

    def test_eingetragene_adresse_gilt(self):
        self.assertEqual(
            wordpress.rest_adresse_von(projekt(rest="https://x.example/api")),
            "https://x.example/api")

    def test_sonst_wird_die_uebliche_stelle_vermutet(self):
        self.assertEqual(wordpress.rest_adresse_von(projekt()), STAMM)

    def test_schraegstrich_am_ende_stoert_nicht(self):
        # Sonst stünde »//wp-json« in jeder Abfrage.
        self.assertEqual(
            wordpress.rest_adresse_von(projekt(adresse="https://blog.example/")),
            STAMM)

    def test_leere_einstellungen_sind_kein_fehler(self):
        ohne = SimpleNamespace(art="wordpress", adresse="https://blog.example",
                               einstellungen=None)
        self.assertEqual(wordpress.rest_adresse_von(ohne), STAMM)


# -- Kategorien -------------------------------------------------------------


class KategorienEinesBlogs(unittest.TestCase):
    """Was das Planungsfenster zur Auswahl bekommt."""

    def _kategorien(self, roh, gesamt="52", **mehr):
        with mock.patch.object(wordpress, "json_holen", return_value=roh), \
             mock.patch.object(wordpress, "kopfzeile_holen", return_value=gesamt):
            return wordpress.kategorien(STAMM, **mehr)

    def test_leere_kategorien_kommen_nicht_mit(self):
        # Wer »Allgemein« mit null Beiträgen wählt, plant eine Woche, die
        # nichts findet - und sucht den Fehler dann bei uns.
        gefunden = self._kategorien([
            kategorie_roh(1, "Wandern", 44),
            kategorie_roh(2, "Allgemein", 0),
            kategorie_roh(3, "Radeln", 8),
        ])
        self.assertNotIn("Allgemein", [k["name"] for k in gefunden])

    def test_die_groesste_steht_oben(self):
        # Wer eine Woche füllen will, braucht Vorrat.
        gefunden = self._kategorien([
            kategorie_roh(1, "Radeln", 8),
            kategorie_roh(2, "Wandern", 44),
        ])
        self.assertEqual([k["name"] for k in gefunden],
                         ["Alle Beiträge", "Wandern", "Radeln"])

    def test_alle_beitraege_erst_ab_zwei_kategorien(self):
        # Bei genau einer wäre der Eintrag eine Dublette: Er führte zu
        # denselben Beiträgen, und zwei Zeilen, die dasselbe tun, sind keine
        # Auswahl, sondern eine Stolperfalle.
        gefunden = self._kategorien([kategorie_roh(1, "Allgemein", 16)])
        self.assertEqual([k["name"] for k in gefunden], ["Allgemein"])

    def test_bei_zwei_kategorien_kommt_alle_beitraege_dazu(self):
        gefunden = self._kategorien([
            kategorie_roh(1, "Wandern", 44),
            kategorie_roh(2, "Radeln", 8),
        ])
        self.assertEqual(gefunden[0]["name"], "Alle Beiträge")
        self.assertIsNone(gefunden[0]["nummer"])

    def test_die_schwelle_ist_einstellbar(self):
        gefunden = self._kategorien([kategorie_roh(1, "Allgemein", 16)],
                                    alle_ab=1)
        self.assertEqual(gefunden[0]["name"], "Alle Beiträge")

    def test_ohne_jede_kategorie_bleibt_alle_beitraege(self):
        # Führt ein Blog nur leere Kategorien, wäre eine leere Liste das
        # Ende der Planung. Der Sammeleintrag hält sie offen.
        gefunden = self._kategorien([kategorie_roh(1, "Allgemein", 0)])
        self.assertEqual([k["name"] for k in gefunden], ["Alle Beiträge"])

    def test_alle_beitraege_filtert_keine_kategorie(self):
        # Der ganze Sinn des Eintrags: Er darf kein »categories=« tragen.
        gefunden = self._kategorien([
            kategorie_roh(1, "Wandern", 44), kategorie_roh(2, "Radeln", 8)])
        self.assertEqual(gefunden[0]["adresse"], f"{STAMM}/posts")

    def test_jede_kategorie_traegt_ihre_nummer_in_der_adresse(self):
        gefunden = self._kategorien([
            kategorie_roh(7, "Wandern", 44), kategorie_roh(9, "Radeln", 8)])
        self.assertEqual(gefunden[1]["adresse"], f"{STAMM}/posts?categories=7")
        self.assertEqual(gefunden[2]["adresse"], f"{STAMM}/posts?categories=9")

    def test_der_pfad_hat_ein_gemeinsames_erstes_stueck(self):
        # Die Oberfläche baut daraus die Bereichsauswahl, und ein Blog hat
        # nur einen Bereich.
        gefunden = self._kategorien([
            kategorie_roh(7, "Wandern", 44, slug="wandern"),
            kategorie_roh(9, "Radeln", 8, slug="radeln")])
        self.assertTrue(all(k["pfad"].startswith("blog/") for k in gefunden))

    def test_namen_kommen_ohne_auszeichnung(self):
        # WordPress liefert Kategorienamen mit HTML-Entitäten.
        gefunden = self._kategorien([
            kategorie_roh(1, "Wandern &amp; Radeln", 44),
            kategorie_roh(2, "Sonstiges", 8)])
        self.assertIn("Wandern & Radeln", [k["name"] for k in gefunden])

    def test_die_anzahl_kommt_mit(self):
        gefunden = self._kategorien([
            kategorie_roh(1, "Wandern", 44), kategorie_roh(2, "Radeln", 8)])
        self.assertEqual([k["produkte"] for k in gefunden[1:]], [44, 8])

    def test_etwas_anderes_als_eine_liste_ist_ein_fehler(self):
        # Wer die Adresse einer Seite statt der Schnittstelle einträgt, soll
        # das lesen und nicht über einen AttributeError stolpern.
        with mock.patch.object(wordpress, "json_holen", return_value={"code": "x"}):
            with self.assertRaises(AbrufFehler) as f:
                wordpress.kategorien(STAMM)
        self.assertIn("WordPress-Schnittstelle", str(f.exception))

    def test_die_kategorien_werden_in_einem_abruf_geholt(self):
        # Ein Blog sagt seine Gliederung selbst - ein Abruf, keine 130 wie bei
        # einem Shop ohne Schnittstelle. Deshalb gibt es dafür auch keinen
        # Zwischenspeicher.
        with mock.patch.object(wordpress, "json_holen",
                               return_value=[kategorie_roh(1, "A", 4)]) as geholt, \
             mock.patch.object(wordpress, "kopfzeile_holen", return_value="4"):
            wordpress.kategorien(STAMM)
        self.assertEqual(geholt.call_count, 1)


class GesamtzahlKommtAusDemKopf(unittest.TestCase):
    """»Alle Beiträge« zählt nicht die Kategorien zusammen.

    Ein Beitrag steht oft in mehreren Kategorien und zählte dann mehrfach:
    44 + 30 + 24 ergäbe 98, obwohl der Blog 52 Beiträge hat. Die richtige
    Zahl steht in `X-WP-Total` und in keinem Feld der Antwort.
    """

    KATEGORIEN = [{"produkte": 44}, {"produkte": 30}, {"produkte": 24}]

    def test_die_kopfzeile_gilt(self):
        with mock.patch.object(wordpress, "kopfzeile_holen", return_value="52"):
            self.assertEqual(wordpress._gesamtzahl(STAMM, self.KATEGORIEN), 52)

    def test_nicht_die_summe_der_kategorien(self):
        # Die Gegenprobe zum Test darüber: 98 wäre die Summe.
        with mock.patch.object(wordpress, "kopfzeile_holen", return_value="52"):
            self.assertNotEqual(wordpress._gesamtzahl(STAMM, self.KATEGORIEN), 98)

    def test_ohne_kopfzeile_gilt_die_groesste_kategorie(self):
        # So viele sind es mindestens. Eine zu hohe Summe wäre die
        # unehrlichere Schätzung.
        with mock.patch.object(wordpress, "kopfzeile_holen", return_value=None):
            self.assertEqual(wordpress._gesamtzahl(STAMM, self.KATEGORIEN), 44)

    def test_unbrauchbare_kopfzeile_faellt_ebenso_zurueck(self):
        # Manche Zwischenspeicher schreiben dort Unsinn hinein.
        with mock.patch.object(wordpress, "kopfzeile_holen", return_value="viele"):
            self.assertEqual(wordpress._gesamtzahl(STAMM, self.KATEGORIEN), 44)

    def test_ohne_alles_bleibt_null(self):
        with mock.patch.object(wordpress, "kopfzeile_holen", return_value=None):
            self.assertEqual(wordpress._gesamtzahl(STAMM, []), 0)

    def test_gefragt_wird_mit_einem_einzigen_beitrag(self):
        # Es geht um den Kopf, nicht um den Rumpf. Wer dafür hundert Beiträge
        # herunterlädt, überträgt ein Megabyte für eine Zahl.
        with mock.patch.object(wordpress, "kopfzeile_holen",
                               return_value="52") as gefragt:
            wordpress._gesamtzahl(STAMM, self.KATEGORIEN)
        gefragt.assert_called_once_with(f"{STAMM}/posts?per_page=1", "X-WP-Total")

    def test_in_kategorien_steht_die_gemeldete_zahl(self):
        # Der Weg durch die ganze Funktion, nicht nur durch den Helfer.
        with mock.patch.object(wordpress, "json_holen", return_value=[
                kategorie_roh(1, "Wandern", 44), kategorie_roh(2, "Radeln", 30)]), \
             mock.patch.object(wordpress, "kopfzeile_holen", return_value="52"):
            gefunden = wordpress.kategorien(STAMM)
        self.assertEqual(gefunden[0]["produkte"], 52)


class KategorienZaehlenDenSprachfilterMit(unittest.TestCase):
    """Mit einem Sprachfilter stimmt die gemeldete Zahl nicht mehr.

    WordPress zählt alles, was in der Kategorie steht - bei einem
    zweisprachigen Blog also auch die englischen Fassungen. Gemeldet werden
    16, planbar sind acht. Wer daraufhin zwei Beiträge am Tag plant, bekommt
    eine halb leere Woche und erfährt den Grund nicht.
    """

    def _antworten(self, kategorien, beitraege):
        """Beantwortet Kategorie- und Beitragsabfragen nach der Adresse."""
        def json_holen(adresse):
            teile = urlsplit(adresse)
            if teile.path.endswith("/categories"):
                return kategorien
            nummer = parse_qs(teile.query).get("categories", [None])[0]
            return beitraege.get(nummer, [])
        return json_holen

    def _kategorien(self, kategorien, beitraege, gesamt="16", **mehr):
        with mock.patch.object(wordpress, "json_holen",
                               side_effect=self._antworten(kategorien, beitraege)), \
             mock.patch.object(wordpress, "kopfzeile_holen",
                               return_value=gesamt) as kopf:
            gefunden = wordpress.kategorien(STAMM, **mehr)
        self.kopf = kopf
        return {k["name"]: k["produkte"] for k in gefunden}

    @staticmethod
    def _zweisprachig(anzahl, ab=1):
        """Zu jedem deutschen Beitrag einen englischen unter »/en/«."""
        posten = []
        for n in range(ab, ab + anzahl):
            posten.append(beitrag_roh(n, f"DE {n}", f"https://blog.example/b-{n}/"))
            posten.append(beitrag_roh(1000 + n, f"EN {n}",
                                      f"https://blog.example/en/b-{n}/"))
        return posten

    def test_gezaehlt_wird_was_planbar_ist(self):
        gefunden = self._kategorien(
            [kategorie_roh(1, "Allgemein", 16)],
            {"1": self._zweisprachig(8), None: self._zweisprachig(8)},
            ausschliessen=["/en/"])
        self.assertEqual(gefunden["Allgemein"], 8)

    def test_ohne_filter_bleibt_die_gemeldete_zahl(self):
        # Ein Abruf je Kategorie kostet Zeit. Er geschieht nur, wo ein Filter
        # eingetragen ist.
        gefunden = self._kategorien(
            [kategorie_roh(1, "Allgemein", 16)],
            {"1": self._zweisprachig(8)})
        self.assertEqual(gefunden["Allgemein"], 16)

    def test_auch_alle_beitraege_wird_nachgezaehlt(self):
        gefunden = self._kategorien(
            [kategorie_roh(1, "Wandern", 16), kategorie_roh(2, "Radeln", 6)],
            {"1": self._zweisprachig(8), "2": self._zweisprachig(3),
             None: self._zweisprachig(10)},
            ausschliessen=["/en/"])
        self.assertEqual(gefunden["Alle Beiträge"], 10)

    def test_mit_filter_wird_die_kopfzeile_nicht_gebraucht(self):
        # `X-WP-Total` zählt die englischen Fassungen mit und wäre hier die
        # falsche Zahl.
        self._kategorien(
            [kategorie_roh(1, "Wandern", 16), kategorie_roh(2, "Radeln", 6)],
            {"1": self._zweisprachig(8), "2": self._zweisprachig(3),
             None: self._zweisprachig(10)},
            ausschliessen=["/en/"])
        self.kopf.assert_not_called()

    def test_eine_nur_englische_kategorie_faellt_heraus(self):
        # Nach dem Filter bleibt nichts übrig - sie zu zeigen hieße, eine
        # Woche planbar zu nennen, die keine Beiträge findet.
        englisch = [beitrag_roh(1001, "EN", "https://blog.example/en/x/")]
        gefunden = self._kategorien(
            [kategorie_roh(1, "Wandern", 16), kategorie_roh(2, "English", 4)],
            {"1": self._zweisprachig(8), "2": englisch,
             None: self._zweisprachig(8)},
            ausschliessen=["/en/"])
        self.assertNotIn("English", gefunden)

    def test_sortiert_wird_nach_der_nachgezaehlten_zahl(self):
        # »Radeln« meldet weniger, hat aber nach dem Filter mehr. Wer nach der
        # gemeldeten Zahl sortiert, stellt die kleinere nach oben.
        with mock.patch.object(wordpress, "json_holen",
                               side_effect=self._antworten(
                                   [kategorie_roh(1, "Wandern", 20),
                                    kategorie_roh(2, "Radeln", 12)],
                                   {"1": self._zweisprachig(2),
                                    "2": [beitrag_roh(n) for n in range(1, 13)],
                                    None: self._zweisprachig(14)})), \
             mock.patch.object(wordpress, "kopfzeile_holen", return_value="32"):
            gefunden = wordpress.kategorien(STAMM, ausschliessen=["/en/"])
        self.assertEqual([k["name"] for k in gefunden],
                         ["Alle Beiträge", "Radeln", "Wandern"])

    def test_scheitert_das_nachzaehlen_bleibt_die_gemeldete_zahl(self):
        # Eine zu hohe Zahl ist besser als eine Kategorie, die aus der Auswahl
        # fällt, weil ein Abruf einmal danebenging.
        with mock.patch.object(wordpress, "beitragsliste",
                               side_effect=AbrufFehler("keine Verbindung")):
            self.assertEqual(wordpress._planbare(f"{STAMM}/posts", 16, ["/en/"]), 16)

    def test_alle_beitraege_faellt_nicht_auf_null_zurueck(self):
        """Scheitert das Zählen, steht dort die größte Kategorie – nie null.

        Die Oberfläche blendet aus, was null meldet. »Alle Beiträge« würde
        also genau dann aus der Auswahl verschwinden, wenn der Blog gerade
        klemmt – und niemand wüsste, warum die Zeile fehlt.
        """
        def zaehlen(adresse, grenze, ausschliessen=None):
            # Die Kategorien lassen sich zählen, der Sammeleintrag nicht.
            if adresse.endswith("/posts"):
                raise AbrufFehler("keine Verbindung")
            return [beitrag_roh(n) for n in range(1, 8)]

        with mock.patch.object(wordpress, "json_holen",
                               return_value=[kategorie_roh(1, "Wandern", 20),
                                             kategorie_roh(2, "Radeln", 12)]), \
             mock.patch.object(wordpress, "beitragsliste", side_effect=zaehlen):
            gefunden = wordpress.kategorien(STAMM, ausschliessen=["/en/"])

        alle = next(k for k in gefunden if k["name"] == "Alle Beiträge")
        self.assertEqual(alle["produkte"], 7)


# -- Beitragslisten ---------------------------------------------------------


class BeitragslisteFuerDiePlanung(unittest.TestCase):
    """Titel und Adresse - mehr wird beim Planen nicht gebraucht.

    Der ganze Beitrag mit Bild wird erst geholt, wenn feststeht, dass er
    drankommt. Wer für vierzig Beiträge sofort alles holt, löst vierzig
    Bildabrufe aus, um sieben davon zu benutzen.
    """

    def _liste(self, seiten, adresse=None, **mehr):
        """`seiten` ist eine Liste von Antworten, eine je Seitenabruf."""
        self.geholt: list[str] = []

        def antworten(gefragt):
            self.geholt.append(gefragt)
            return seiten[len(self.geholt) - 1]

        with mock.patch.object(wordpress, "json_holen", side_effect=antworten):
            return wordpress.beitragsliste(adresse or f"{STAMM}/posts", **mehr)

    def test_titel_adresse_und_kennung(self):
        gefunden = self._liste([[beitrag_roh(7, "Über den Kamm")]])
        self.assertEqual(gefunden, [{
            "fremd_id": "7",
            "titel": "Über den Kamm",
            "adresse": "https://blog.example/beitrag-7/",
        }])

    def test_die_kategorie_geht_nicht_verloren(self):
        # Der wichtigste Fall: Sonst plant man den ganzen Blog statt einer
        # Kategorie, ohne dass es auffällt.
        self._liste([[]], adresse=f"{STAMM}/posts?categories=9")
        self.assertEqual(parse_qs(urlsplit(self.geholt[0]).query)["categories"],
                         ["9"])

    def test_ohne_embed(self):
        # `_embed` zöge Bilder und Begriffe mit - für eine Titelliste ist das
        # ein Vielfaches an Daten.
        self._liste([[]])
        self.assertNotIn("_embed", self.geholt[0])

    def test_nur_die_drei_gebrauchten_felder(self):
        self._liste([[]])
        self.assertEqual(parse_qs(urlsplit(self.geholt[0]).query)["_fields"],
                         ["id,link,title"])

    def test_neueste_zuerst(self):
        # Ein frisch erschienener Beitrag soll vorn stehen und nicht im
        # Alphabet verschwinden.
        self._liste([[]])
        werte = parse_qs(urlsplit(self.geholt[0]).query)
        self.assertEqual(werte["orderby"], ["date"])
        self.assertEqual(werte["order"], ["desc"])

    def test_reihenfolge_von_wordpress_bleibt(self):
        gefunden = self._liste([[beitrag_roh(3, "C"), beitrag_roh(1, "A"),
                                 beitrag_roh(2, "B")]])
        self.assertEqual([b["titel"] for b in gefunden], ["C", "A", "B"])

    def test_ausgeschlossene_adressen_bleiben_draussen(self):
        # Die zweisprachigen Blogs liefern jeden Beitrag doppelt, deutsch und
        # unter »/en/«. Ohne Filter stünde jeder zweimal im Kalender.
        seite = [beitrag_roh(1, "Deutsch", "https://blog.example/kamm/"),
                 beitrag_roh(2, "English", "https://blog.example/en/ridge/")]
        gefunden = self._liste([seite], ausschliessen=["/en/"])
        self.assertEqual([b["titel"] for b in gefunden], ["Deutsch"])

    def test_ohne_filter_kommt_alles_mit(self):
        seite = [beitrag_roh(1, "Deutsch", "https://blog.example/kamm/"),
                 beitrag_roh(2, "English", "https://blog.example/en/ridge/")]
        self.assertEqual(len(self._liste([seite])), 2)

    def test_die_grenze_wird_eingehalten(self):
        seite = [beitrag_roh(n) for n in range(1, 41)]
        self.assertEqual(len(self._liste([seite], grenze=25)), 25)

    def test_letzte_seite_wird_erkannt(self):
        # Eine unvollständige Seite ist die letzte. Wer trotzdem weiterblättert,
        # bekommt von WordPress einen Fehler statt einer leeren Liste.
        self._liste([[beitrag_roh(n) for n in range(1, 5)]], grenze=30)
        self.assertEqual(len(self.geholt), 1)

    def test_es_wird_geblaettert_wenn_die_seite_voll_war(self):
        # Eine volle Seite, aus der der Filter etwas herausgenommen hat: Dann
        # fehlt hinten etwas, und es muss nachgelegt werden.
        erste = [beitrag_roh(1000, "EN", "https://blog.example/en/x/")]
        erste += [beitrag_roh(n) for n in range(2, 26)]
        zweite = [beitrag_roh(n) for n in range(26, 51)]
        gefunden = self._liste([erste, zweite], grenze=25,
                               ausschliessen=["/en/"])
        self.assertEqual(len(gefunden), 25)
        self.assertEqual(
            [parse_qs(urlsplit(a).query)["page"][0] for a in self.geholt],
            ["1", "2"])

    def test_der_sprachfilter_zieht_die_ausbeute_nicht_unter_die_grenze(self):
        # Der eigentliche Grund für die Blätterung: Auf einem zweisprachigen
        # Blog ist die Hälfte jeder Seite englisch. Ohne Nachlegen käme eine
        # Woche mit fünfzehn statt dreißig Beiträgen heraus.
        def gemischt(erster, letzter):
            posten = []
            for n in range(erster, letzter):
                posten.append(beitrag_roh(n, f"DE {n}",
                                          f"https://blog.example/b-{n}/"))
                posten.append(beitrag_roh(1000 + n, f"EN {n}",
                                          f"https://blog.example/en/b-{n}/"))
            return posten

        gefunden = self._liste([gemischt(1, 16), gemischt(16, 31)],
                               grenze=30, ausschliessen=["/en/"])
        self.assertEqual(len(gefunden), 30)
        self.assertTrue(all("/en/" not in b["adresse"] for b in gefunden))

    def test_eine_leere_seite_beendet_das_blaettern(self):
        # Der Blog hat weniger Beiträge, als die Grenze verlangt. Ohne diesen
        # Abbruch liefe die Blätterung endlos.
        erste = [beitrag_roh(1000, "EN", "https://blog.example/en/x/")]
        erste += [beitrag_roh(n) for n in range(2, 26)]
        gefunden = self._liste([erste, []], grenze=25, ausschliessen=["/en/"])
        self.assertEqual(len(gefunden), 24)
        self.assertEqual(len(self.geholt), 2)

    def test_titel_kommen_ohne_auszeichnung(self):
        gefunden = self._liste([[beitrag_roh(1, "Käse &amp; Brot")]])
        self.assertEqual(gefunden[0]["titel"], "Käse & Brot")

    def test_etwas_anderes_als_eine_liste_ist_ein_fehler(self):
        with mock.patch.object(wordpress, "json_holen",
                               return_value={"code": "rest_no_route"}):
            with self.assertRaises(AbrufFehler):
                wordpress.beitragsliste(f"{STAMM}/posts")


class EinzelnerBeitrag(unittest.TestCase):
    """Der ganze Beitrag, geholt für die sieben, die wirklich drankommen."""

    ROH = {
        "id": 42,
        "title": {"rendered": "Über den Kamm"},
        "content": {"rendered": "<p>Erster Absatz.</p><p>Zweiter Absatz.</p>"},
        "link": "https://blog.example/ueber-den-kamm/",
        "date_gmt": "2026-08-27T15:00:00",
        "_embedded": {
            "wp:featuredmedia": [{"source_url": "https://blog.example/b.jpg"}],
            "wp:term": [[{"name": "Wandern"}], [{"name": "Alpen"}]],
        },
    }

    def _beitrag(self, roh=None):
        with mock.patch.object(wordpress, "json_holen",
                               return_value=self.ROH if roh is None else roh) as geholt:
            ergebnis = wordpress.beitrag(STAMM, "42")
        self.geholt = geholt.call_args[0][0]
        return ergebnis

    def test_liefert_dieselben_felder_wie_eine_seite(self):
        # Die Wochenplanung soll nicht wissen müssen, woher ein Beitrag kommt.
        gefunden = self._beitrag()
        self.assertEqual(set(gefunden), {"fremd_id", "titel", "text", "adresse",
                                         "bild_adresse", "veroeffentlicht",
                                         "kategorien"})

    def test_hier_wird_eingebettet_geholt(self):
        # Anders als bei der Liste: Jetzt werden Bild und Begriffe gebraucht.
        self._beitrag()
        self.assertIn("_embed=1", self.geholt)
        self.assertIn("/posts/42", self.geholt)

    def test_das_datum_bekommt_seine_zone(self):
        # `date_gmt` ist bereits UTC, sieht aber aus wie Ortszeit. Wer das
        # übersieht, verschiebt jeden Beitrag um ein bis zwei Stunden.
        self.assertEqual(self._beitrag()["veroeffentlicht"],
                         "2026-08-27T15:00:00Z")

    def test_beitragsbild_wird_genommen(self):
        self.assertEqual(self._beitrag()["bild_adresse"],
                         "https://blog.example/b.jpg")

    def test_kategorien_kommen_mit(self):
        self.assertEqual(self._beitrag()["kategorien"], ["Wandern", "Alpen"])

    def test_ohne_beitrag_ist_es_ein_fehler(self):
        # WordPress antwortet auf eine unbekannte Kennung mit einem
        # Fehlerobjekt, nicht mit 404.
        with mock.patch.object(wordpress, "json_holen",
                               return_value={"code": "rest_post_invalid_id"}):
            with self.assertRaises(AbrufFehler):
                wordpress.beitrag(STAMM, "999")

    def test_der_text_wird_gekuerzt(self):
        # Blogbeiträge reichen bis 15.200 Zeichen. Alles mitzuschicken bläht
        # die Anweisung auf das Vierfache, ohne dass ein Beitrag für Facebook
        # davon besser würde.
        roh = dict(self.ROH)
        roh["content"] = {"rendered": "".join(
            f"<p>{'Wort ' * 100}</p>" for _ in range(30))}
        self.assertLessEqual(len(self._beitrag(roh)["text"]),
                             wordpress.TEXTGRENZE)


class TextWirdAnAbsaetzenGekuerzt(unittest.TestCase):
    """`_kuerzen` schneidet nie mitten im Wort.

    Ein hart abgeschnittener Text hat am 2026-08-31 reihenweise Rückfragen
    ausgelöst - Claude meldete zu Recht, der Quelltext breche mitten im Satz
    ab, und der Beitrag blieb liegen.
    """

    ABSAETZE = ["A" * 100, "B" * 100, "C" * 100]

    def test_kurzer_text_bleibt_unangetastet(self):
        self.assertEqual(wordpress._kuerzen("Kurz.", 100), "Kurz.")

    def test_genau_auf_der_grenze_bleibt_ganz(self):
        text = "x" * 100
        self.assertEqual(wordpress._kuerzen(text, 100), text)

    def test_nur_ganze_absaetze_kommen_zurueck(self):
        gekuerzt = wordpress._kuerzen("\n\n".join(self.ABSAETZE), 150)
        self.assertTrue(all(a in self.ABSAETZE for a in gekuerzt.split("\n\n")))

    def test_der_zu_lange_absatz_bleibt_draussen(self):
        gekuerzt = wordpress._kuerzen("\n\n".join(self.ABSAETZE), 150)
        self.assertEqual(gekuerzt, self.ABSAETZE[0])

    def test_der_erste_absatz_kommt_immer_mit(self):
        # Auch wenn er allein schon zu lang ist: Ein leerer Text wäre
        # schlechter als ein zu langer.
        lang = "Wort " * 2000
        self.assertEqual(wordpress._kuerzen(lang, 100), lang)

    def test_wird_nicht_mitten_im_wort_geschnitten(self):
        text = "\n\n".join(["Erster Absatz mit Wörtern."] * 60)
        gekuerzt = wordpress._kuerzen(text, 200)
        self.assertTrue(gekuerzt.endswith("."))
        self.assertNotIn("Wörter\n", gekuerzt)

    def test_die_vorgabe_ist_die_textgrenze(self):
        # Dieselbe Grenze wie bei den Shopseiten, aus demselben Grund.
        lang = "\n\n".join(["Satz." * 100] * 40)
        self.assertLessEqual(len(wordpress._kuerzen(lang)), wordpress.TEXTGRENZE)


# -- Der Weg durch den Kampagnenlauf ----------------------------------------


def kampagne(kategorien, **mehr):
    vorgabe = dict(thema="", projekt="blog", kalenderwoche=36, jahr=2026,
                   kategorien=kategorien)
    vorgabe.update(mehr)
    return kampagnen.Kampagne(**vorgabe)


class ProdukteSammelnWaehltDenWeg(unittest.TestCase):
    """Ein Blog wird anders gelesen als ein Shop - aber nur ein Blog.

    Der alte Weg muss unverändert bleiben: Er ist der Regelfall, und ein
    Projekt ohne `art` gibt es auch (etwa beim Aufruf ohne Projektobjekt).
    """

    KAT = f"{STAMM}/posts?categories=9"

    def test_ein_blog_geht_ueber_die_schnittstelle(self):
        with mock.patch.object(kampagnenlauf.wordpress, "beitragsliste",
                               return_value=[{"fremd_id": "7", "titel": "T",
                                              "adresse": "https://blog.example/t/"}]) as blog, \
             mock.patch.object(kampagnenlauf.wordpress, "kategorien",
                               return_value=[]), \
             mock.patch.object(kampagnenlauf.seitenkarte, "kategorie") as shop:
            gefunden = kampagnenlauf.produkte_sammeln(
                kampagne([self.KAT]), projekt=projekt())

        blog.assert_called_once()
        shop.assert_not_called()
        self.assertEqual(gefunden[0]["adresse"], "https://blog.example/t/")

    def test_ein_shop_geht_weiter_ueber_die_seite(self):
        kat = "https://shop.example/kat_1/list.html"
        with mock.patch.object(kampagnenlauf.seitenkarte, "kategorie",
                               return_value=["https://shop.example/kat_1/tuer_1.html"]) as shop, \
             mock.patch.object(kampagnenlauf.wordpress, "beitragsliste") as blog:
            gefunden = kampagnenlauf.produkte_sammeln(
                kampagne([kat]), projekt=projekt(art="seitenkarte"))

        shop.assert_called_once()
        blog.assert_not_called()
        self.assertEqual(gefunden[0]["kategorie"], "kat_1")

    def test_ohne_projekt_bleibt_es_beim_shopweg(self):
        # So, wie es vor dem 2026-09-05 war. Wer hier etwas ändert, ändert
        # das Verhalten aller alten Aufrufe mit.
        kat = "https://shop.example/kat_1/list.html"
        with mock.patch.object(kampagnenlauf.seitenkarte, "kategorie",
                               return_value=[]) as shop, \
             mock.patch.object(kampagnenlauf.wordpress, "beitragsliste") as blog:
            kampagnenlauf.produkte_sammeln(kampagne([kat]))
        shop.assert_called_once()
        blog.assert_not_called()

    def test_ein_projekt_ohne_art_geht_ebenfalls_den_alten_weg(self):
        ohne = SimpleNamespace(adresse="https://shop.example", einstellungen={})
        with mock.patch.object(kampagnenlauf.seitenkarte, "kategorie",
                               return_value=[]) as shop:
            kampagnenlauf.produkte_sammeln(
                kampagne(["https://shop.example/kat_1/list.html"]), projekt=ohne)
        shop.assert_called_once()

    def test_die_grenze_wird_durchgereicht(self):
        with mock.patch.object(kampagnenlauf.wordpress, "beitragsliste",
                               return_value=[]) as blog, \
             mock.patch.object(kampagnenlauf.wordpress, "kategorien",
                               return_value=[]):
            kampagnenlauf.produkte_sammeln(kampagne([self.KAT]), 12,
                                           projekt=projekt())
        self.assertEqual(blog.call_args[0][1], 12)


class BeitraegeSammeln(unittest.TestCase):
    """Der Blogweg im Einzelnen."""

    EINS = f"{STAMM}/posts?categories=1"
    ZWEI = f"{STAMM}/posts?categories=2"

    def _sammeln(self, listen, kategorien=None, fehler=None, projekt_=None):
        """`listen` ordnet Kategorieadressen ihre Beitragslisten zu."""
        self.gefragt: list[tuple] = []

        def liste(adresse, grenze, ausschliessen=None):
            self.gefragt.append((adresse, grenze, ausschliessen))
            return listen.get(adresse, [])

        namen = mock.patch.object(
            kampagnenlauf.wordpress, "kategorien",
            side_effect=fehler) if fehler else mock.patch.object(
            kampagnenlauf.wordpress, "kategorien",
            return_value=kategorien or [])

        with mock.patch.object(kampagnenlauf.wordpress, "beitragsliste",
                               side_effect=liste), namen:
            return kampagnenlauf.produkte_sammeln(
                kampagne(list(listen)), projekt=projekt_ or projekt())

    def test_ein_beitrag_in_zwei_kategorien_kommt_nur_einmal(self):
        # Sonst stünde er zweimal in derselben Woche - und zweimal derselbe
        # Beitrag fällt jedem Leser auf.
        doppelt = {"fremd_id": "7", "titel": "Über den Kamm",
                   "adresse": "https://blog.example/kamm/"}
        anders = {"fremd_id": "8", "titel": "Anderes",
                  "adresse": "https://blog.example/anderes/"}
        gefunden = self._sammeln({self.EINS: [doppelt],
                                  self.ZWEI: [doppelt, anders]})
        self.assertEqual([p["adresse"] for p in gefunden],
                         ["https://blog.example/kamm/",
                          "https://blog.example/anderes/"])

    def test_die_erste_kategorie_behaelt_den_beitrag(self):
        doppelt = {"fremd_id": "7", "titel": "T",
                   "adresse": "https://blog.example/kamm/"}
        gefunden = self._sammeln(
            {self.EINS: [doppelt], self.ZWEI: [doppelt]},
            kategorien=[{"adresse": self.EINS, "name": "Wandern"},
                        {"adresse": self.ZWEI, "name": "Radeln"}])
        self.assertEqual([p["kategorie"] for p in gefunden], ["Wandern"])

    def test_die_kennung_wird_mitgefuehrt(self):
        # Ohne sie müsste der Beitrag später über die Seite gelesen werden.
        gefunden = self._sammeln({self.EINS: [
            {"fremd_id": "7", "titel": "T", "adresse": "https://blog.example/t/"}]})
        self.assertEqual(gefunden[0]["fremd_id"], "7")

    def test_der_titel_kommt_aus_der_liste(self):
        # Beim Shop ist der Titel bis zum Auslesen ein Stück Adresse. Hier
        # steht der richtige schon in der Liste.
        gefunden = self._sammeln({self.EINS: [
            {"fremd_id": "7", "titel": "Über den Kamm",
             "adresse": "https://blog.example/ueber-den-kamm/"}]})
        self.assertEqual(gefunden[0]["titel"], "Über den Kamm")

    def test_kategorienamen_werden_nachgeschlagen(self):
        # »Wandern« sagt etwas, »posts?categories=1« nichts.
        gefunden = self._sammeln(
            {self.EINS: [{"fremd_id": "7", "titel": "T",
                          "adresse": "https://blog.example/t/"}]},
            kategorien=[{"adresse": self.EINS, "name": "Wandern"}])
        self.assertEqual(gefunden[0]["kategorie"], "Wandern")

    def test_ohne_namen_steht_die_adresse_da(self):
        # Scheitert der Abruf, wird nicht der ganze Lauf hingeworfen.
        gefunden = self._sammeln(
            {self.EINS: [{"fremd_id": "7", "titel": "T",
                          "adresse": "https://blog.example/t/"}]},
            fehler=AbrufFehler("keine Verbindung"))
        self.assertEqual(gefunden[0]["kategorie"], "posts?categories=1")

    def test_der_sprachfilter_des_projekts_gilt_auch_hier(self):
        self._sammeln({self.EINS: []},
                      projekt_=projekt(ausschliessen=["/en/"]))
        self.assertEqual(self.gefragt[0][2], ["/en/"])

    def test_ohne_eintrag_wird_nichts_ausgeschlossen(self):
        self._sammeln({self.EINS: []})
        self.assertIsNone(self.gefragt[0][2])


class AuslesenNimmtDieSchnittstelle(unittest.TestCase):
    """Bei einem Blog ist der Weg über die Schnittstelle der bessere.

    WordPress liefert den Text ohne Menü, Fußzeile und Beiwerk, dazu das
    gepflegte Beitragsbild und das Datum. Aus dem HTML derselben Seite müsste
    man all das erst wieder herausschneiden.
    """

    PRODUKT = {"adresse": "https://blog.example/kamm/", "titel": "T",
               "kategorie": "Wandern", "fremd_id": "42"}

    def _auslesen(self, produkt, projekt_):
        with mock.patch.object(kampagnenlauf.wordpress, "beitrag",
                               return_value={"quelle": "rest"}) as ueber_rest, \
             mock.patch.object(kampagnenlauf.seitenkarte, "seite",
                               return_value={"quelle": "seite"}) as ueber_seite:
            ergebnis = kampagnenlauf._auslesen(projekt_, produkt)
        return ergebnis, ueber_rest, ueber_seite

    def test_mit_kennung_ueber_die_schnittstelle(self):
        ergebnis, rest, seite = self._auslesen(self.PRODUKT, projekt())
        self.assertEqual(ergebnis["quelle"], "rest")
        rest.assert_called_once_with(STAMM, "42")
        seite.assert_not_called()

    def test_ohne_kennung_wird_die_seite_gelesen(self):
        # Etwa bei einem alten Entwurf aus der Zeit vor dem 2026-09-05.
        # Lieber ein schlechterer Text als ein Abbruch.
        ohne = dict(self.PRODUKT)
        del ohne["fremd_id"]
        ergebnis, rest, seite = self._auslesen(ohne, projekt())
        self.assertEqual(ergebnis["quelle"], "seite")
        rest.assert_not_called()
        seite.assert_called_once_with("https://blog.example/kamm/")

    def test_leere_kennung_zaehlt_wie_keine(self):
        ergebnis, _, seite = self._auslesen(
            dict(self.PRODUKT, fremd_id=""), projekt())
        self.assertEqual(ergebnis["quelle"], "seite")
        seite.assert_called_once()

    def test_ein_shop_wird_weiter_ueber_die_seite_gelesen(self):
        # Auch dann, wenn zufällig eine Kennung dabeisteht.
        ergebnis, rest, _ = self._auslesen(self.PRODUKT, projekt(art="seitenkarte"))
        self.assertEqual(ergebnis["quelle"], "seite")
        rest.assert_not_called()

    def test_die_eingetragene_schnittstelle_wird_benutzt(self):
        _, rest, _ = self._auslesen(
            self.PRODUKT, projekt(rest="https://blog.example/eigene/api"))
        rest.assert_called_once_with("https://blog.example/eigene/api", "42")


# -- Die Anweisung an Claude ------------------------------------------------


INHALT = {
    "titel": "Über den Kamm",
    "text": "Ein Absatz über eine Wanderung.",
    "adresse": "https://blog.example/ueber-den-kamm/",
    "bild_adresse": "https://blog.example/b.jpg",
    "kategorien": ["Wandern"],
    "veroeffentlicht": "2026-03-14T09:00:00Z",
}


class BlogregelnStehenNurBeiEinemBlog(unittest.TestCase):
    """Ein Blogbeitrag wird anders beworben als eine Tür.

    Er soll gelesen werden, nicht gekauft, und er ist oft nicht von gestern.
    Beides muss dastehen, sonst schreibt Claude eine Inhaltsangabe und nennt
    einen Beitrag vom März »neu«.
    """

    def test_mit_blog_stehen_die_blogregeln_drin(self):
        text = vorlagen.anweisung(INHALT, ["facebook"], art=vorlagen.BLOG)
        self.assertIn(vorlagen.BLOGREGELN, text)

    def test_die_vorgabe_ist_produkt(self):
        # Was vorher gebaut wurde, verhält sich unverändert.
        text = vorlagen.anweisung(INHALT, ["facebook"])
        self.assertNotIn(vorlagen.BLOGREGELN, text)

    def test_produkt_bleibt_wortgleich_zur_vorgabe(self):
        # Die Gegenprobe: Der neue Schalter darf den alten Weg nicht anfassen.
        self.assertEqual(
            vorlagen.anweisung(INHALT, ["facebook"]),
            vorlagen.anweisung(INHALT, ["facebook"], art=vorlagen.PRODUKT))

    def test_die_grundregeln_gelten_in_beiden_faellen(self):
        for art in (vorlagen.PRODUKT, vorlagen.BLOG):
            with self.subTest(art=art):
                self.assertIn(vorlagen.GRUNDREGELN,
                              vorlagen.anweisung(INHALT, ["facebook"], art=art))

    def test_der_blog_hebt_die_preisregel_nicht_auf(self):
        # In einem Blogbeitrag kommen Preise selten vor. Stehen sie doch
        # einmal darin, bleiben sie trotzdem draußen.
        einzeilig = " ".join(vorlagen.BLOGREGELN.split())
        self.assertIn("Preise, Lieferzeiten und Garantiebedingungen", einzeilig)
        self.assertIn("bleiben draußen", einzeilig)

    def test_der_abbruch_des_quelltextes_ist_kein_grund_zur_rueckfrage(self):
        # Sonst fragt Claude bei jedem langen Beitrag nach, weil der Text nach
        # 4.000 Zeichen aufhört - und der Beitrag bleibt liegen.
        einzeilig = " ".join(vorlagen.BLOGREGELN.split())
        self.assertIn("kein Grund für eine Rückfrage", einzeilig)

    def test_kein_beitrag_wird_neu_genannt(self):
        einzeilig = " ".join(vorlagen.BLOGREGELN.split())
        self.assertIn("Sag nicht, der Beitrag sei neu", einzeilig)

    def test_bei_der_wiederholung_heisst_es_beitrag_und_nicht_produkt(self):
        frueher = {"facebook": "Der alte Text."}
        blog = vorlagen.anweisung(INHALT, ["facebook"], frueher=frueher,
                                  art=vorlagen.BLOG)
        ware = vorlagen.anweisung(INHALT, ["facebook"], frueher=frueher)
        self.assertIn("Dieser Beitrag war schon einmal dran", blog)
        self.assertIn("Dieses Produkt war schon einmal dran", ware)


class ErschienenAmStehtInDerQuelle(unittest.TestCase):
    """Ohne das Datum kann Claude nicht wissen, wie alt der Text ist.

    Produktseiten haben kein Datum, dem zu trauen wäre; ein Blogbeitrag
    schon. Deshalb steht die Zeile nur da, wo es eine gibt.
    """

    def test_das_datum_kommt_mit(self):
        text = vorlagen.anweisung(INHALT, ["facebook"], art=vorlagen.BLOG)
        self.assertIn("Erschienen am: 2026-03-14T09:00:00Z", text)

    def test_ohne_datum_steht_die_zeile_nicht_da(self):
        ohne = dict(INHALT)
        del ohne["veroeffentlicht"]
        self.assertNotIn("Erschienen am", vorlagen.anweisung(ohne, ["facebook"]))

    def test_das_datum_haengt_nicht_an_der_art(self):
        # Ein Shop, der eines liefert, soll es auch mitschicken dürfen.
        self.assertIn("Erschienen am",
                      vorlagen.anweisung(INHALT, ["facebook"],
                                         art=vorlagen.PRODUKT))


# -- Das Planungsfenster ----------------------------------------------------


class KategorienImWebdienst(unittest.TestCase):
    """Was »Woche planen« für ein Blogprojekt anbietet."""

    def _fragen(self, bereich=None, kategorien=None, projekt_=None):
        from postkutsche.web import dienst

        with mock.patch("postkutsche.quellen.wordpress.kategorien",
                        return_value=kategorien or []) as blog, \
             mock.patch("postkutsche.quellen.seitenkarte.navigation") as navigation:
            gefunden, hinweis = dienst.kategorien_des_projekts(
                projekt_ or projekt(), bereich, melden=lambda *a: None)
        self.blog, self.navigation = blog, navigation
        return gefunden, hinweis

    def test_die_schnittstelle_wird_gefragt_und_nicht_die_seite(self):
        self._fragen()
        self.blog.assert_called_once_with(STAMM, ausschliessen=None)
        self.navigation.assert_not_called()

    def test_der_sprachfilter_des_projekts_zaehlt_mit(self):
        # Sonst steht in der Auswahl die doppelte Zahl, und die Woche wird
        # halb leer, ohne dass jemand den Grund erfährt.
        self._fragen(projekt_=projekt(ausschliessen=["/en/"]))
        self.blog.assert_called_once_with(STAMM, ausschliessen=["/en/"])

    def test_es_gibt_nichts_zu_warten_und_nichts_zu_melden(self):
        # Ein Abruf statt einer Erhebung über 132 Seiten: kein
        # Zwischenspeicher, kein Hinweis über zwanzig Sekunden Wartezeit.
        self.assertIsNone(self._fragen()[1])

    def test_der_bereich_filtert_ueber_den_pfad(self):
        alle = [{"pfad": "blog/alle", "adresse": "a"},
                {"pfad": "blog/wandern", "adresse": "b"},
                {"pfad": "anderes/x", "adresse": "c"}]
        gefunden, _ = self._fragen("blog", alle)
        self.assertEqual([k["pfad"] for k in gefunden],
                         ["blog/alle", "blog/wandern"])


if __name__ == "__main__":
    unittest.main()
