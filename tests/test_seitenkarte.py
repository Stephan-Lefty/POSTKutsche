"""Seiten ohne Schnittstelle: was aus einer alten Seitenkarte zu holen ist."""

import unittest
from unittest import mock

from postkutsche.quellen import seitenkarte
from postkutsche.quellen.abrufen import AbrufFehler


class FortgezogeneAdressen(unittest.TestCase):
    """Eine Seitenkarte, die zehn Jahre nicht gepflegt wurde, luegt."""

    def test_umleitung_auf_uebersicht_ist_kein_produkt(self):
        for ziel in ("https://x.example/kat_486/list.html",
                     "https://x.example/errordoc/404.html"):
            with self.subTest(ziel=ziel):
                self.assertTrue(seitenkarte._ist_keine_produktseite(ziel))

    def test_echte_produktadresse_bleibt(self):
        self.assertFalse(seitenkarte._ist_keine_produktseite(
            "https://x.example/kat_486/tuer_1810.html"))

    def test_fliesstext_nimmt_absaetze_nur_einmal(self):
        # Verschachtelung: derselbe Absatz steckt in zwei divs. Wer die divs
        # liest statt der Blaetter, hat ihn doppelt.
        satz = "Feuerhemmend nach DIN 4102, rauchdicht nach DIN 18095. " * 2
        roh = f"<div><div><p>{satz}</p></div></div><p>{satz}</p>"
        self.assertEqual(seitenkarte._fliesstext(roh).count("DIN 4102"), 2)

    def test_fliesstext_ueberspringt_schaltflaechen(self):
        self.assertEqual(seitenkarte._fliesstext("<p>In den Warenkorb</p>"), "")

    def test_fliesstext_haelt_die_grenze_ein(self):
        roh = "<p>" + ("a" * 500 + "</p><p>") * 40 + "</p>"
        self.assertLessEqual(len(seitenkarte._fliesstext(roh)),
                             seitenkarte.TEXTGRENZE)


class ProdukteEinerKategorie(unittest.TestCase):
    """Shopware legt Produkte flach ab, nicht unter der Kategorie."""

    SEITE = """
      <a href="/Fenstersicherung/">Kategorie</a>
      <a href="/ADE-Sicherungsstange-S/ADE-S">Stange</a>
      <a href="/ADE-Sicherungsstange-S/ADE-S"><img></a>
      <a href="/ADE-Verbindungsplatte/ADE-VP-Z20">Platte</a>
      <a href="/account/profile">Mein Profil</a>
      <a href="/page/cms/018ecf08670770a1a802dafa0da91c97">Datenschutz</a>
      <a href="/Rechtliches/Versand-Zahlungen/">Versand</a>
      <a href="https://fremd.example/Ding/X1">fremd</a>
      <a href="/Angebote">flach</a>
    """

    def _lesen(self):
        with mock.patch.object(seitenkarte, "text_holen",
                               return_value=self.SEITE):
            return seitenkarte.produkte_der_kategorie(
                "https://x.example/Fenstersicherung/")

    def test_findet_die_produkte(self):
        self.assertEqual(self._lesen(), [
            "https://x.example/ADE-Sicherungsstange-S/ADE-S",
            "https://x.example/ADE-Verbindungsplatte/ADE-VP-Z20",
        ])

    def test_zaehlt_dieselbe_kachel_nur_einmal(self):
        # Bild und Titel verweisen auf dasselbe Produkt.
        self.assertEqual(len(self._lesen()), 2)

    def test_kontoseiten_sind_keine_produkte(self):
        # Ohne die Sperre stuenden »Profil« und »Adressen« in jeder Kategorie.
        self.assertNotIn("https://x.example/account/profile", self._lesen())

    def test_inhaltsseiten_aus_dem_fussbereich_bleiben_draussen(self):
        # »/page/cms/<Kennung>« ist nach der Adressform ein lupenreines
        # Produkt: drei Ebenen, kein Schraegstrich am Ende.
        self.assertFalse([a for a in self._lesen() if "/page/cms" in a])

    def test_fremde_adressen_bleiben_draussen(self):
        self.assertFalse([a for a in self._lesen() if "fremd.example" in a])

    def test_eine_ebene_ist_keine_produktadresse(self):
        # /Angebote ist eine Uebersicht, kein Artikel.
        self.assertNotIn("https://x.example/Angebote", self._lesen())

    def test_zweitname_zeigt_auf_dieselbe_funktion(self):
        # produkte_der_kategorie ist seit dem Zusammenlegen nur noch ein
        # Zweitname. Wer den Zweitnamen aendert, ohne es zu merken, sieht es
        # hier.
        self.assertIs(seitenkarte.produkte_der_kategorie, seitenkarte.kategorie)


class MehrereSeiten(unittest.TestCase):
    """Eine Kategorie kann mehr als eine Seite haben.

    Am 2026-08-31 nachgemessen: Von 119 Kategorien haben drei eine zweite
    Seite, zusammen zwoelf Produkte. Wenig - aber es waren zwoelf Produkte,
    die stillschweigend fehlten, und die Wochenplanung streute aus einem
    Ausschnitt, ohne dass jemand merkte, dass es einer war.
    """

    KAT = "https://x.example/shop-tueren/t30_489/list.html"

    EINS = """
      <a href="/shop-tueren/t30_489/a_1.html">A</a>
      <a href="/shop-tueren/t30_489/b_2.html">B</a>
      <a href="/shop-tueren/t30_489/list.html?page=1">1</a>
      <a href="/shop-tueren/t30_489/list.html?page=2">2</a>
    """
    ZWEI = """
      <a href="/shop-tueren/t30_489/b_2.html">B</a>
      <a href="/shop-tueren/t30_489/c_3.html">C</a>
      <a href="/shop-tueren/t30_489/list.html?page=1">1</a>
    """

    def _seiten(self):
        return {self.KAT: self.EINS, f"{self.KAT}?page=2": self.ZWEI}

    def _lesen(self, **mehr):
        seiten = self._seiten()
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=lambda a: seiten[a]):
            return seitenkarte.kategorie(self.KAT, **mehr)

    def test_die_zweite_seite_kommt_mit(self):
        self.assertEqual(self._lesen(), [
            "https://x.example/shop-tueren/t30_489/a_1.html",
            "https://x.example/shop-tueren/t30_489/b_2.html",
            "https://x.example/shop-tueren/t30_489/c_3.html",
        ])

    def test_was_auf_beiden_steht_zaehlt_einmal(self):
        self.assertEqual(len(self._lesen()), 3)

    def test_die_reihenfolge_bleibt_seite_fuer_seite(self):
        # Das erste Produkt der ersten Seite bleibt das erste - die
        # Wochenplanung nimmt die ersten.
        self.assertTrue(self._lesen()[0].endswith("a_1.html"))

    def test_seite_eins_wird_nicht_noch_einmal_geholt(self):
        # Der Shop verlinkt »?page=1« mit, damit die Blaetterleiste
        # vollstaendig aussieht. Wer ihr folgt, holt dieselbe Seite zweimal.
        geholt = []
        seiten = self._seiten()

        def antworten(a):
            geholt.append(a)
            return seiten[a]

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            seitenkarte.kategorie(self.KAT)
        self.assertEqual(geholt, [self.KAT, f"{self.KAT}?page=2"])

    def test_ohne_blaetterverweise_wird_nichts_geraten(self):
        # »?page=2« anzuhaengen und zu sehen, was kommt, waere die falsche
        # Loesung: Eine Seite, die es nicht gibt, antwortet selten mit 404.
        geholt = []

        def antworten(a):
            geholt.append(a)
            return '<a href="/shop-tueren/t30_489/a_1.html">A</a>'

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            seitenkarte.kategorie(self.KAT)
        self.assertEqual(geholt, [self.KAT])

    def test_eine_stumme_folgeseite_kostet_nur_sich_selbst(self):
        def antworten(a):
            if "page=2" in a:
                raise AbrufFehler("antwortet nicht")
            return self.EINS

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            gefunden = seitenkarte.kategorie(self.KAT)
        self.assertEqual(len(gefunden), 2)

    def test_die_grenze_gilt_ueber_alle_seiten(self):
        self.assertEqual(len(self._lesen(grenze=2)), 2)

    def test_abschaltbar(self):
        self.assertEqual(len(self._lesen(folgeseiten=False)), 2)

    def test_fremde_frage_gilt_nicht_als_folgeseite(self):
        # Nur derselbe Pfad mit anderer Frage. Ein Verweis auf eine andere
        # Kategorie ist keine zweite Seite dieser.
        seiten = self._seiten()
        seiten[self.KAT] = (
            self.EINS + '<a href="/shop-tueren/anders_1/list.html?page=2">X</a>')
        geholt = []

        def antworten(a):
            geholt.append(a)
            return seiten[a]

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            seitenkarte.kategorie(self.KAT)
        self.assertNotIn("anders_1", " ".join(geholt))

    def test_die_zahl_im_bestand_zaehlt_die_folgeseiten_mit(self):
        # Eine Kategorie, die 30 meldet und 37 hat, ist eine Kategorie, der
        # man nicht mehr glaubt.
        seiten = self._seiten()
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=lambda a: seiten[a]):
            _, anzahl = seitenkarte._seite_lesen(self.KAT)
        self.assertEqual(anzahl, 3)


class ZweiShopformen(unittest.TestCase):
    """Eine Funktion, zwei Adressformen - entschieden wird an der Adresse.

    Der Eigenbau nennt seine Produkte »..._<Artikelnummer>.html«, Shopware
    haengt die Artikelnummer als eigene Pfadebene an. Beides muss dieselbe
    Funktion erkennen, ohne dass die eine Regel die andere verunreinigt.
    """

    EIGENBAU = """
      <a href="/shop-tueren/brandschutz_489/t30_stahl_1810.html">Tuer</a>
      <a href="/shop-tueren/brandschutz_489/t30_holz_1811.html">Tuer</a>
      <a href="/shop-tueren/brandschutz_489/t30_holz_1811.html"><img></a>
      <a href="/shop-tueren/brandschutz_490/list.html">Unterkategorie</a>
      <a href="/info_service/versandkosten.html">Versandkosten</a>
      <a href="/info_service/impressum.html">Impressum</a>
    """

    UEBERSICHT = """
      <a href="/shop-garagentore/antriebe_542/list.html">Antriebe</a>
      <a href="/info_service/versandkosten.html">Versandkosten</a>
    """

    def _lesen(self, roh, adresse):
        with mock.patch.object(seitenkarte, "text_holen", return_value=roh):
            return seitenkarte.kategorie(adresse)

    def test_eigenbau_nimmt_nur_die_artikelnummern(self):
        self.assertEqual(
            self._lesen(self.EIGENBAU,
                        "https://x.example/shop-tueren/brandschutz_489/list.html"),
            ["https://x.example/shop-tueren/brandschutz_489/t30_stahl_1810.html",
             "https://x.example/shop-tueren/brandschutz_489/t30_holz_1811.html"],
        )

    def test_versandkosten_bleiben_draussen(self):
        # »/info_service/versandkosten.html« erfuellt die Shopware-Regel
        # muehelos: zwei Ebenen, kein Schraegstrich am Ende. Wuerde beim
        # Eigenbau auch nur ersatzweise danach gesucht, staende die Seite in
        # der Kampagne.
        gefunden = self._lesen(
            self.EIGENBAU,
            "https://x.example/shop-tueren/brandschutz_489/list.html")
        self.assertFalse([a for a in gefunden if "info_service" in a])

    def test_leere_uebersicht_bleibt_leer(self):
        # Eine Kategorie der obersten Ebene hat kein eigenes Produkt. Das ist
        # kein Fehler und darf nicht mit Beiwerk aufgefuellt werden.
        self.assertEqual(
            self._lesen(self.UEBERSICHT,
                        "https://x.example/shop-garagentore/list.html"), [])

    def test_shopware_wird_an_der_adresse_erkannt(self):
        # Dieselbe Funktion, Adresse ohne ».html« - jetzt gilt die andere Regel.
        self.assertEqual(
            self._lesen(ProdukteEinerKategorie.SEITE,
                        "https://x.example/Fenstersicherung/"),
            ["https://x.example/ADE-Sicherungsstange-S/ADE-S",
             "https://x.example/ADE-Verbindungsplatte/ADE-VP-Z20"],
        )

    def test_schieber_ueber_der_liste_zaehlen_nicht_mit(self):
        # Shopware stellt ueber die Produktliste Schieber mit Empfehlungen -
        # Produkte aus dem ganzen Shop. Am 2026-08-31 nachgezaehlt: eine
        # Kategorie mit drei Produkten meldete elf. Weil die Schieber oben
        # stehen, waeren genau die falschen in der Kampagne gelandet.
        roh = f"""
          <a href="/Empfehlung/EMP-1">Schieber</a>
          <div class="{seitenkarte.LISTENBAUSTEIN}">
            <a href="/ADE-Stange/ADE-S">Stange</a>
          </div>
        """
        self.assertEqual(self._lesen(roh, "https://x.example/Fenstersicherung/"),
                         ["https://x.example/ADE-Stange/ADE-S"])

    def test_ohne_listenbaustein_bleibt_die_ganze_seite(self):
        # Lieber zu viel finden als eine Kategorie faelschlich fuer leer
        # erklaeren.
        roh = '<a href="/ADE-Stange/ADE-S">Stange</a>'
        self.assertEqual(self._lesen(roh, "https://x.example/Fenstersicherung/"),
                         ["https://x.example/ADE-Stange/ADE-S"])

    def test_der_eigenbau_wird_nicht_zugeschnitten(self):
        # Der Baustein ist eine Shopware-Sache. Ein Eigenbau, der das Wort
        # zufaellig irgendwo stehen haette, duerfte davon nichts merken.
        roh = (f'<a href="/kat_1/a_1.html">A</a><div class="{seitenkarte.LISTENBAUSTEIN}">'
               f'<a href="/kat_1/b_2.html">B</a></div>')
        self.assertEqual(len(self._lesen(roh, "https://x.example/kat_1/list.html")), 2)

    def test_grenze_wird_eingehalten(self):
        roh = "".join(f'<a href="/kat_1/artikel_{n}.html">A</a>' for n in range(50))
        gefunden = self._lesen(roh, "https://x.example/kat_1/list.html")
        self.assertEqual(len(gefunden), 50)
        with mock.patch.object(seitenkarte, "text_holen", return_value=roh):
            self.assertEqual(
                len(seitenkarte.kategorie("https://x.example/kat_1/list.html", 5)), 5)


class NavigationAlsQuelle(unittest.TestCase):
    """Die Navigation ist die Quelle, nicht der Filter.

    Die Seitenkarte war fuer die Kategorienliste die schlechtere Quelle: Am
    2026-08-31 verschwieg sie 57 Kategorien, die es gibt, und fuehrte 115, die
    es nicht mehr gibt. Gezaehlt wird jetzt, was die Seite selbst verlinkt.
    """

    SEITEN = {
        "https://x.example/": """
          <a href="/shop-tueren/list.html">Türen Shop</a>
          <a href="https://x.example/shop-tueren/list.html">Türen</a>
          <a href="/info_service/kontakt.html">Kontakt</a>
        """,
        "https://x.example/shop-tueren/list.html": """
          <a href="/shop-tueren/brandschutz_455/list.html">Brandschutztüren</a>
          <a href="/shop-tueren/muenchen_680/list.html">Abholgebiet Raum München</a>
          <a href="/shop-tueren/tuerkonfigurator_99/list.html">Konfigurator</a>
        """,
        # Die dritte Ebene: Diese Unterkategorie steht weder auf der
        # Startseite noch auf der Bereichsseite. Genau hier liegt die Ware.
        "https://x.example/shop-tueren/brandschutz_455/list.html": """
          <a href="/shop-tueren/t30-1_stahl_489/list.html">T30-1 Stahltüren</a>
          <a href="/shop-tueren/brandschutz_455/tuer_1810.html">Tür</a>
        """,
        "https://x.example/shop-tueren/t30-1_stahl_489/list.html": """
          <a href="/shop-tueren/t30-1_stahl_489/a_1.html">A</a>
          <a href="/shop-tueren/t30-1_stahl_489/b_2.html">B</a>
          <a href="/shop-tueren/t30-1_stahl_489/b_2.html"><img></a>
        """,
    }

    def _lesen(self, seiten=None, **mehr):
        seiten = seiten if seiten is not None else self.SEITEN
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=lambda a: seiten[a]):
            return seitenkarte.navigation("https://x.example/", **mehr)

    def test_die_dritte_ebene_kommt_mit(self):
        # Startseite und Bereichsseite allein haetten »T30-1 Stahltueren«
        # uebersehen - und dort liegen die Produkte.
        kategorien, _ = self._lesen()
        self.assertIn("T30-1 Stahltüren", [k["name"] for k in kategorien])

    def test_produkte_werden_beim_lesen_gezaehlt(self):
        # Nicht aus der Seitenkarte uebernommen: Die behauptete fuer eine
        # Kategorie zwoelf Produkte, auf der Seite stand eines.
        kategorien, _ = self._lesen()
        nach_namen = {k["name"]: k["produkte"] for k in kategorien}
        self.assertEqual(nach_namen["T30-1 Stahltüren"], 2)
        self.assertEqual(nach_namen["Brandschutztüren"], 1)

    def test_der_bereich_ist_dabei_aber_als_tiefe_eins(self):
        # Aussortiert wird er erst in der Oberflaeche - hier steht er, weil
        # das Auswahlfeld oben ihn braucht.
        kategorien, _ = self._lesen()
        bereiche = [k for k in kategorien if k["tiefe"] == 1]
        self.assertEqual([k["name"] for k in bereiche], ["Türen Shop"])

    def test_die_laengste_beschriftung_gewinnt(self):
        kategorien, _ = self._lesen()
        self.assertIn("Türen Shop", [k["name"] for k in kategorien])

    def test_abholgebiete_und_konfiguratoren_bleiben_draussen(self):
        # Beide aus demselben Grund: Dahinter steht kein Produkt, das man
        # zeigen und verlinken koennte. Ein Konfigurator ist ein Formular,
        # ein Abholgebiet ein Ort.
        kategorien, ausgelassen = self._lesen()
        namen = [k["name"] for k in kategorien]
        self.assertNotIn("Abholgebiet Raum München", namen)
        self.assertFalse([n for n in namen if "onfigurator" in n])
        self.assertEqual(len(ausgelassen), 2)

    def test_ortsnamen_allein_reichen_nicht_zum_ausschluss(self):
        # »Garagentore Berlin« ist ein Sortiment fuer eine Region und hat
        # Ware. Das Merkmal ist das Wort »Abholgebiet«, nicht die Stadt.
        seiten = dict(self.SEITEN)
        seiten["https://x.example/shop-tueren/list.html"] = (
            '<a href="/shop-tueren/berlin_540/list.html">Türen Berlin</a>')
        seiten["https://x.example/shop-tueren/berlin_540/list.html"] = (
            '<a href="/shop-tueren/berlin_540/a_1.html">A</a>')
        kategorien, _ = self._lesen(seiten)
        self.assertIn("Türen Berlin", [k["name"] for k in kategorien])

    def test_nur_gelesene_seiten_kommen_zurueck(self):
        # Eine Kategorie, die erst in der letzten Runde auftaucht, hat keine
        # gezaehlten Produkte. Sie aufzunehmen hiesse, eine Null zu
        # behaupten, die nichts bedeutet.
        kategorien, _ = self._lesen(klicks=1)
        self.assertEqual([k["name"] for k in kategorien], ["Türen Shop"])

    def test_eine_stumme_seite_bricht_nichts_ab(self):
        def antworten(adresse):
            if "brandschutz_455" in adresse:
                raise AbrufFehler("antwortet nicht")
            return self.SEITEN[adresse]

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            kategorien, _ = seitenkarte.navigation("https://x.example/")
        self.assertIn("Türen Shop", [k["name"] for k in kategorien])

    def test_eine_stumme_startseite_ist_ein_fehler(self):
        # Antwortet sie nicht, ist die ganze Bestandsaufnahme wertlos, und
        # der Aufrufer soll das erfahren, statt eine leere Liste fuer den
        # Bestand zu halten.
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=AbrufFehler("stumm")):
            with self.assertRaises(AbrufFehler):
                seitenkarte.navigation("https://x.example/")

    def test_die_seitengrenze_haelt(self):
        viele = "".join(f'<a href="/shop-{n}/list.html">B {n}</a>'
                        for n in range(60))
        seiten = {"https://x.example/": viele}
        for n in range(60):
            seiten[f"https://x.example/shop-{n}/list.html"] = ""
        geholt = []

        def antworten(adresse):
            geholt.append(adresse)
            return seiten[adresse]

        with mock.patch.object(seitenkarte, "text_holen", side_effect=antworten):
            seitenkarte.navigation("https://x.example/", seitengrenze=10)
        self.assertLessEqual(len(geholt), 10)

    def test_schaltflaechen_sind_keine_namen(self):
        # »anzeigen >>« steht auf der Tuerenseite zweimal als Verweistext.
        seiten = {
            "https://x.example/": '<a href="/shop-x/list.html">anzeigen &gt;&gt;</a>',
            "https://x.example/shop-x/list.html": "",
        }
        kategorien, _ = self._lesen(seiten)
        self.assertEqual(kategorien[0]["name"], "Shop X")

    def test_kaputte_kodierung_wird_nicht_angezeigt(self):
        # Auf einer Seite steht »H<?>rmann ThermoSafe Haust<?>ren«. Lieber
        # den hoelzernen Namen aus der Adresse als kaputte Zeichen.
        seiten = {
            "https://x.example/": '<a href="/shop-x/list.html">H�rmann</a>',
            "https://x.example/shop-x/list.html": "",
        }
        kategorien, _ = self._lesen(seiten)
        self.assertEqual(kategorien[0]["name"], "Shop X")


class VorgegebeneKategorien(unittest.TestCase):
    """Wo die Seitenkarte die Zugehoerigkeit nicht verraet, nennt man sie."""

    SEITE = """
      <a href="/ADE-Stange/ADE-S">Stange</a>
      <a href="/ADE-Platte/ADE-VP">Platte</a>
    """

    def _lesen(self, vorgaben):
        with mock.patch.object(seitenkarte, "text_holen", return_value=self.SEITE):
            return seitenkarte.vorgegebene_kategorien(vorgaben)

    def test_zaehlt_die_produkte_der_seite(self):
        eintraege = self._lesen(["https://x.example/Fenstersicherung/"])
        self.assertEqual(eintraege[0]["produkte"], 2)

    def test_name_kommt_aus_der_adresse(self):
        eintraege = self._lesen(["https://x.example/Tuersicherung/"])
        self.assertEqual(eintraege[0]["name"], "Türsicherung")

    def test_bindestriche_werden_zu_worten(self):
        eintraege = self._lesen(["https://x.example/Duesen-und-Adapter/"])
        self.assertEqual(eintraege[0]["name"], "Düsen und Adapter")

    def test_eigener_name_sticht_die_adresse(self):
        eintraege = self._lesen([
            {"adresse": "https://x.example/Zubehoer/", "name": "Kleinkram"}])
        self.assertEqual(eintraege[0]["name"], "Kleinkram")

    def test_tiefe_ist_nie_null(self):
        # Die Oberflaeche rueckt nach »tiefe - 1« ein und kaeme sonst auf
        # einen negativen Abstand.
        eintraege = self._lesen(["https://x.example/Zubehoer/"])
        self.assertGreaterEqual(int(eintraege[0]["tiefe"]), 1)

    def test_stumme_kategorie_verschwindet_nicht(self):
        with mock.patch.object(seitenkarte, "text_holen",
                               side_effect=AbrufFehler("antwortet nicht")):
            eintraege = seitenkarte.vorgegebene_kategorien(
                ["https://x.example/Weg/"])
        self.assertEqual(len(eintraege), 1)
        self.assertEqual(eintraege[0]["produkte"], 0)
        self.assertIn("antwortet nicht", str(eintraege[0]["fehler"]))


class TextEndetAufEinemSatz(unittest.TestCase):
    """Ein Text, der mitten im Wort endet, erzeugt eine Rueckfrage, die keine ist."""

    def test_kein_absatz_wird_zerschnitten(self):
        # Absaetze knapp unter der Grenze: der letzte passt nicht mehr ganz.
        gross = "A" * 1500
        roh = "".join(f"<p>{gross}{n}</p>" for n in range(5))
        ergebnis = seitenkarte._fliesstext(roh)
        for absatz in ergebnis.split("\n\n"):
            self.assertIn(absatz, roh, "ein Absatz wurde zerschnitten")

    def test_haelt_die_grenze_trotzdem_ein(self):
        roh = "".join(f"<p>{'B' * 900}{n}</p>" for n in range(12))
        self.assertLessEqual(len(seitenkarte._fliesstext(roh)),
                             seitenkarte.TEXTGRENZE)

    def test_ein_einzelner_zu_langer_absatz_faellt_weg(self):
        # Lieber nichts als ein Satz ohne Ende. Wer den Text braucht, sieht
        # ihn auf der Seite.
        self.assertEqual(seitenkarte._fliesstext(f"<p>{'C' * 5000}</p>"), "")


class KategorienameBeimEigenbau(unittest.TestCase):
    """»list.html« ist kein Name - und zweimal derselbe ist kein Name mehr."""

    def test_list_html_wird_uebersprungen(self):
        self.assertEqual(
            seitenkarte._letztes_stueck("shop-zubehoer/einbruchschutz_fenster_608/list.html"),
            "einbruchschutz_fenster_608")

    def test_shopware_bleibt_wie_es_war(self):
        self.assertEqual(seitenkarte._letztes_stueck("Fenstersicherung"),
                         "Fenstersicherung")

    def test_ein_pfad_aus_nichts_als_list_html(self):
        # Nicht schoen, aber besser als eine leere Beschriftung.
        self.assertEqual(seitenkarte._letztes_stueck("list.html"), "list.html")
