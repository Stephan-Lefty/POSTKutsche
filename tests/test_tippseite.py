"""Die Seite »Tipp der Woche« fortschreiben.

Geprüft wird an einer Seite, die genauso gebaut ist wie die echte: mit den
vier Marken, einer H1, einem Tipp, einem Archiv samt auskommentiertem Muster
und den vier Stellen im Kopf und am Fuß, die mitgezogen werden müssen.
"""

from __future__ import annotations

import unittest
from datetime import date

from postkutsche import tippseite

SEITE = """<html><head>
<title>Tipp der Woche - Praxistipps zu Türen und Toren | Laden.example</title>
<meta name="description" content="Jeden Montag ein neuer Praxistipp. Diese Woche: Dichtungen vor dem Frost." />
<meta name="date" content="2026-09-28" />
<link rel="canonical" href="https://a.example/Tipp-der-Woche.html" />
</head><body>
<!-- ==================================================================
     TIPP DER WOCHE  -  ANLEITUNG FUER DAS MONTAGS-UPDATE
     ==================================================================
     Hier steht, was montags zu tun ist.
     ================================================================== -->

    <div class="page-header">
        <h1>Tipp der Woche von Laden.example</h1>
    </div>

    <div class="row"><div class="col-xs-12">
        <p>Jede Woche ein neuer Tipp. Lohnt sich das Lesezeichen? Ja.</p>
    </div></div>

<!-- ============ TIPP AKTUELL  (jeden Montag ersetzen) ============ -->
    <div class="row"><div class="col-xs-12">
        <p class="noMargin"><small><strong>Kalenderwoche 40</strong> &middot; ab Montag, 28. September 2026</small></p>
        <h2>Vor dem Winter: Türdichtungen prüfen</h2>
    </div></div>
    <div class="row"><div class="col-xs-12"><p>Alter Text.</p>
        <p class="text-center"><a href="https://a.example/kw40.png" target="_blank" rel="noopener">
            <img src="https://a.example/kw40.png" class="img-responsive" alt="Grafik KW 40" /></a></p>
    </div></div>
<!-- ============ ENDE TIPP AKTUELL ============ -->

<!-- ============ TIPP ARCHIV ============ -->
    <div class="row"><div class="col-xs-12">
        <h2>Die Tipps der Vorwochen</h2>
    </div></div>
    <div class="row">

<!-- MUSTER fuer einen Archiv-Eintrag:
    	<div class="col-xs-12 col-sm-6">
        	<div class="row">
                <div class="col-xs-12">
                	<p class="noMargin"><small><strong>Kalenderwoche 99</strong></small></p>
                    <p><a href="/tipp-archiv/muster.html"><strong>Muster</strong></a></p>
                </div>
            </div>
            <div class="clearfix">&nbsp;</div>
        </div>
-->
    	<div class="col-xs-12 col-sm-6">
        	<div class="row">
            	<div class="col-xs-5">
                	<a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html"><img src="https://a.example/kw39.png"
                         class="img-responsive"
                         alt="KW 39" /></a>
                </div>
                <div class="col-xs-7">
                	<p class="noMargin"><small><strong>Kalenderwoche 39</strong> &middot; 21. September 2026</small></p>
                    <p><a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html"><strong>Garagentor einwintern</strong></a><br />
                    Zwei Sätze dazu.
                    <a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html">Weiterlesen &raquo;</a></p>
                </div>
            </div>
            <div class="clearfix">&nbsp;</div>
        </div>
    </div>
<!-- ============ ENDE TIPP ARCHIV ============ -->
<p><small>Zuletzt aktualisiert: 28. September 2026 (KW 40)</small></p>
</body></html>"""

UEBERSICHT = """<html><head>
<title>Alle Tipps der Woche im Überblick - das Archiv von Laden.example</title>
<meta name="description" content="Das Archiv." />
<link rel="canonical" href="https://a.example/tipp-archiv/" />
</head><body>
    <div class="page-header"><h1>Alle Tipps der Woche im Überblick</h1></div>
<!-- ============ ARCHIVLISTE  (montags oben erweitern) ============ -->
    <div class="row">
    	<div class="col-xs-12">
        	<div class="border-top">&nbsp;</div>
            <h2>2026</h2>
        </div>
    </div>

    <div class="row">
    	<div class="col-xs-4 col-sm-3">
        	<a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html"><img src="https://a.example/kw39.png"
                 class="img-responsive"
                 alt="KW 39" /></a>
        </div>
        <div class="col-xs-8 col-sm-9">
        	<p class="noMargin"><small><strong>Kalenderwoche 39</strong> &middot; 21. September 2026</small></p>
            <p><a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html"><strong>Garagentor einwintern</strong></a><br />
            Zwei Sätze dazu.
            <a href="/tipp-archiv/2026-KW39-garagentor-einwintern.html">Weiterlesen &raquo;</a></p>
        </div>
    </div>
    <div class="clearfix">&nbsp;</div>
<!-- ============ ENDE ARCHIVLISTE ============ -->
<!-- ============ TIPP DER WOCHE - Seitenreiter links (Anfang) ============
     Dieser Block darf unveraendert bleiben, auch wenn der Tipp wechselt.
     ==================================================================== -->
<style type="text/css">
#tdwReiter{position:fixed;left:0;top:45%;display:none}
</style>
<div id="tdwReiter">
	<a href="/Tipp-der-Woche.html" title="Tipp der Woche - jede Woche neu">
    	<div class="tdwSchmal"><span>Tipp der Woche &raquo;</span></div>
    </a>
</div>
<!-- ============ TIPP DER WOCHE - Seitenreiter links (Ende) ============ -->
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
        self.assertIn("Kalenderwoche 40", archiv)
        self.assertIn("Türdichtungen prüfen", archiv)
        # Der bisherige steht oben, der ältere darunter.
        self.assertLess(archiv.find("Kalenderwoche 40"),
                        archiv.find("Kalenderwoche 39"))

    def test_der_eintrag_traegt_die_kurzfassung_aus_dem_kopf(self):
        # Sie stand als meta description auf der Seite. Wenn der Tipp
        # abläuft, sind die Daten, aus denen er entstand, längst weg - sie
        # dort abzuholen ist der einzige Weg ohne doppelte Pflege.
        archiv = self.neu[self.neu.find(tippseite.ARCHIV_AUF):
                          self.neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn("Dichtungen vor dem Frost.", archiv)

    def test_der_eintrag_verlinkt_die_archivseite(self):
        archiv = self.neu[self.neu.find(tippseite.ARCHIV_AUF):
                          self.neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn("/tipp-archiv/2026-KW40-vor-dem-winter.html", archiv)
        # Die Grafik ist nicht mehr das Ziel: Auf ihr stehen zwölf
        # Stichpunkte, auf der Seite der ganze Tipp.
        self.assertNotIn('href="https://a.example/kw40.png"', archiv)

    def test_unter_dem_archiv_steht_der_verweis_auf_die_uebersicht(self):
        archiv = self.neu[self.neu.find(tippseite.ARCHIV_AUF):
                          self.neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn('href="/tipp-archiv/"', archiv)
        self.assertIn("Alle Tipps im Archiv ansehen", archiv)

    def test_das_auskommentierte_muster_wird_nicht_uebernommen(self):
        # Es sieht einem Eintrag zum Verwechseln ähnlich. Wer es mitnimmt,
        # hat nach zwei Wochen einen erfundenen Tipp im Archiv.
        self.assertNotIn("Kalenderwoche 99", self.neu)

    def test_der_schnellzugriff_wird_nach_vier_wochen_gekuerzt(self):
        seite = SEITE
        for nummer in range(41, 48):
            seite = tippseite.erneuern(
                seite, dict(TIPP, titel=f"Thema {nummer}"), nummer, MONTAG)
        archiv = seite[seite.find(tippseite.ARCHIV_AUF):
                       seite.find(tippseite.ARCHIV_ZU)]
        self.assertEqual(archiv.count('class="col-xs-12 col-sm-6"'),
                         tippseite.ARCHIV_WOCHEN)

    def test_zwei_eintraege_je_zeile(self):
        # Bootstrap 3 bricht ungleich hohe Spalten treppenförmig um, wenn
        # mehr als zwei in derselben row stehen.
        seite = SEITE
        for nummer in range(41, 45):
            seite = tippseite.erneuern(
                seite, dict(TIPP, titel=f"Thema {nummer}"), nummer, MONTAG)
        archiv = seite[seite.find(tippseite.ARCHIV_AUF):
                       seite.find(tippseite.ARCHIV_ZU)]
        self.assertEqual(archiv.count('class="col-xs-12 col-sm-6"'), 4)
        for zeile in archiv.split('<div class="row">\n\n')[1:]:
            self.assertLessEqual(zeile.count('class="col-xs-12 col-sm-6"'), 2)

    def test_titel_und_beschreibung_werden_nachgezogen(self):
        # »Beides ist fuer Google wichtig und darf nicht stehen bleiben«,
        # sagt die Anleitung in der Datei selbst.
        self.assertIn("<title>Tipp der Woche - Außentüren im Herbst richtig "
                      "pflegen | Laden.example</title>", self.neu)
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



class GleicheWoche(unittest.TestCase):
    """Wird innerhalb derselben Woche nachgebessert, wird ersetzt."""

    def test_dieselbe_woche_wandert_nicht_ins_archiv(self):
        # Sonst stünde KW 40 zweimal auf der Seite: oben als aktueller Tipp,
        # darunter als Vorwoche. Am 2026-09-29 genau so passiert.
        neu = tippseite.erneuern(SEITE, TIPP, 40, date(2026, 9, 28))
        archiv = neu[neu.find(tippseite.ARCHIV_AUF):
                     neu.find(tippseite.ARCHIV_ZU)]
        self.assertNotIn("Kalenderwoche 40", archiv)
        self.assertIn("Kalenderwoche 39", archiv)   # der ältere bleibt
        self.assertIn("Kalenderwoche 40", neu)      # oben steht der neue

    def test_die_naechste_woche_archiviert_wie_gehabt(self):
        neu = tippseite.erneuern(SEITE, TIPP, 41, MONTAG)
        archiv = neu[neu.find(tippseite.ARCHIV_AUF):
                     neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn("Kalenderwoche 40", archiv)


class Verweise(unittest.TestCase):
    """Passende Artikel stehen unten im Kasten, nicht im Fließtext."""

    EINER = [{"text": "Kriechöl", "adresse": "https://shop.example/oel.html"}]

    def test_der_verweis_steht_am_ende_des_tipps(self):
        neu = tippseite.erneuern(SEITE, dict(TIPP, verweise=self.EINER),
                                 41, MONTAG)
        aktuell = neu[neu.find(tippseite.AKTUELL_AUF):
                      neu.find(tippseite.AKTUELL_ZU)]
        self.assertIn("Passend dazu aus unserem Sortiment", aktuell)
        self.assertIn('href="https://shop.example/oel.html"', aktuell)
        # Nach dem letzten Absatz, nicht mittendrin.
        self.assertLess(aktuell.find("<strong>Betonung</strong>"),
                        aktuell.find("Passend dazu"))

    def test_ohne_verweise_entsteht_kein_leerer_kasten(self):
        neu = tippseite.erneuern(SEITE, TIPP, 41, MONTAG)
        self.assertNotIn("Passend dazu", neu)

    def test_ein_eintrag_ohne_adresse_wird_uebergangen(self):
        neu = tippseite.erneuern(
            SEITE, dict(TIPP, verweise=[{"text": "ohne Ziel"}]), 41, MONTAG)
        self.assertNotIn("Passend dazu", neu)

    def test_anfuehrungszeichen_in_der_adresse_brechen_nichts_auf(self):
        boese = [{"text": "x", "adresse": 'https://a.example/"><script>'}]
        neu = tippseite.erneuern(SEITE, dict(TIPP, verweise=boese), 41, MONTAG)
        self.assertNotIn("<script>", neu)


class ArchivMitGrafiken(unittest.TestCase):
    """Die Grafik der Woche wandert als Vorschaubild mit."""

    def test_die_grafik_des_alten_tipps_landet_im_archiv(self):
        neu = tippseite.erneuern(SEITE, TIPP, 41, MONTAG)
        archiv = neu[neu.find(tippseite.ARCHIV_AUF):
                     neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn('src="https://a.example/kw40.png"', archiv)
        self.assertIn("Kalenderwoche 40", archiv)

    def test_das_bild_steht_neben_dem_text_und_nicht_darueber(self):
        # Die Grafiken sind querformatig. Über die volle Spaltenbreite
        # gelegt nehmen sie halbe Seitenbreite ein und erschlagen den Tipp.
        neu = tippseite.erneuern(SEITE, TIPP, 41, MONTAG)
        archiv = neu[neu.find(tippseite.ARCHIV_AUF):
                     neu.find(tippseite.ARCHIV_ZU)]
        self.assertIn('<div class="col-xs-5">', archiv)
        self.assertIn('<div class="col-xs-7">', archiv)

    def test_ohne_bild_nimmt_der_text_die_ganze_spalte(self):
        # Ein leerer Platzhalter sieht nach einem kaputten Bild aus.
        ohne = SEITE.replace(
            '<img src="https://a.example/kw40.png" class="img-responsive" '
            'alt="Grafik KW 40" />', "")
        neu = tippseite.erneuern(ohne, TIPP, 41, MONTAG)
        archiv = neu[neu.find(tippseite.ARCHIV_AUF):
                     neu.find(tippseite.ARCHIV_ZU)]
        # Nur der neue Eintrag ist bildlos - der Bestand bringt seines mit.
        # Er steht als erster Block im Archiv, also bis zum zweiten.
        erster = archiv.find('class="col-xs-12 col-sm-6"')
        eintrag = archiv[erster:archiv.find('class="col-xs-12 col-sm-6"',
                                            erster + 1)]
        self.assertIn("Türdichtungen prüfen", eintrag)
        self.assertNotIn('<div class="col-xs-5">', eintrag)

    def test_das_bild_im_text_steht_mittig(self):
        # img-responsive setzt display:block, und auf einem Blockelement
        # wirkt das text-center des Absatzes nicht. Am 2026-10-05 an der
        # fertigen Seite gemessen: 15 px Rand links, 515 px rechts.
        mit = dict(TIPP, bilder=[{"adresse": "https://a.example/neu.png",
                                  "alt": "Neu"}])
        neu = tippseite.erneuern(SEITE, mit, 41, MONTAG)
        self.assertIn('class="img-responsive center-block"', neu)

    def test_das_bild_im_text_ist_anklickbar_und_volle_breite(self):
        mit = dict(TIPP, bilder=[{"adresse": "https://a.example/neu.png",
                                  "alt": "Neu", "unterschrift": "Die Woche"}])
        neu = tippseite.erneuern(SEITE, mit, 41, MONTAG)
        aktuell = neu[neu.find(tippseite.AKTUELL_AUF):
                      neu.find(tippseite.AKTUELL_ZU)]
        self.assertIn('href="https://a.example/neu.png" target="_blank"', aktuell)
        self.assertIn("zum Vergrößern anklicken", aktuell)
        # Keine schmale Spalte mehr - alles so breit wie der erste Absatz.
        self.assertNotIn("col-sm-7", aktuell)
        self.assertIn('<div class="col-xs-12">', aktuell)

    def test_das_bild_steht_hinter_dem_ersten_absatz(self):
        mit = dict(TIPP, bilder=[{"adresse": "https://a.example/neu.png",
                                  "alt": "Neu"}])
        neu = tippseite.erneuern(SEITE, mit, 41, MONTAG)
        self.assertLess(neu.find("Ein erster Absatz."),
                        neu.find("https://a.example/neu.png"))
        self.assertLess(neu.find("https://a.example/neu.png"),
                        neu.find("Eine Überschrift"))

class Vorschau(unittest.TestCase):
    """Gezeigt wird die kleine Fassung, verlinkt die große."""

    BILD = [{"adresse": "https://a.example/gross.png",
             "vorschau": "https://a.example/klein.jpg", "alt": "x"}]

    def test_im_text_zeigt_die_kleine_und_verlinkt_die_grosse(self):
        neu = tippseite.erneuern(SEITE, dict(TIPP, bilder=self.BILD), 41, MONTAG)
        self.assertIn('src="https://a.example/klein.jpg"', neu)
        self.assertIn('href="https://a.example/gross.png" target="_blank"', neu)

    def test_ohne_vorschau_steht_beides_auf_derselben_datei(self):
        ohne = [{"adresse": "https://a.example/nur.png", "alt": "x"}]
        neu = tippseite.erneuern(SEITE, dict(TIPP, bilder=ohne), 41, MONTAG)
        self.assertIn('src="https://a.example/nur.png"', neu)
        self.assertIn('href="https://a.example/nur.png"', neu)

    def test_der_eintrag_zeigt_die_kleine_fassung(self):
        # Erst den Tipp mit Vorschau setzen, dann eine Woche weiter.
        eins = tippseite.erneuern(SEITE, dict(TIPP, bilder=self.BILD), 41, MONTAG)
        zwei = tippseite.erneuern(eins, TIPP, 42, MONTAG)
        archiv = zwei[zwei.find(tippseite.ARCHIV_AUF):
                      zwei.find(tippseite.ARCHIV_ZU)]
        self.assertIn("klein.jpg", archiv)
        # Die große geht nicht mehr mit: Verlinkt wird die Archivseite.
        self.assertNotIn("gross.png", archiv)


class Adressen(unittest.TestCase):
    """Wie aus einer Überschrift ein Dateiname wird."""

    def name(self, titel, woche="40", jahr="2026"):
        return tippseite.archivname(
            {"titel": titel, "woche": woche, "jahr": jahr})

    def test_jahr_und_woche_stehen_vorn(self):
        # Damit die Dateien im Ordner von selbst richtig sortiert sind.
        self.assertTrue(self.name("Irgendwas").startswith("2026-KW40-"))

    def test_einstellige_wochen_bekommen_eine_null(self):
        self.assertTrue(self.name("Irgendwas", woche="7").startswith("2026-KW07-"))

    def test_vor_dem_doppelpunkt_steht_das_thema(self):
        self.assertEqual(
            self.name("Außentüren im Herbst: die halbe Stunde, die den Winter rettet"),
            "2026-KW40-aussentueren-im-herbst.html")

    def test_umlaute_werden_ausgeschrieben(self):
        # »auentren« findet niemand wieder.
        self.assertIn("tuerdichtungen", self.name("Türdichtungen prüfen"))

    def test_fuellwoerter_am_ende_fallen_weg(self):
        self.assertEqual(self.name("Die Baustelle verschließen: was die "
                                   "Spanplatte nicht leistet"),
                         "2026-KW40-die-baustelle-verschliessen.html")

    def test_ohne_brauchbaren_titel_bleibt_ein_name_uebrig(self):
        self.assertEqual(self.name("???"), "2026-KW40-tipp.html")


class Archivseite(unittest.TestCase):
    """Aus dem ablaufenden Tipp wird eine Seite, die bleibt."""

    def setUp(self):
        self.alt = tippseite.abgelaufener_tipp(SEITE)
        self.seite = tippseite.archivseite(
            SEITE, self.alt, "https://a.example/tipp-archiv/",
            "https://a.example/Tipp-der-Woche.html")

    def test_der_abgelaufene_tipp_wird_vollstaendig_gelesen(self):
        self.assertEqual(self.alt["woche"], "40")
        self.assertEqual(self.alt["titel"], "Vor dem Winter: Türdichtungen prüfen")
        self.assertEqual(self.alt["jahr"], "2026")
        self.assertEqual(self.alt["datum"], "28. September 2026")
        self.assertEqual(self.alt["kurz"], "Dichtungen vor dem Frost.")

    def test_die_kurzfassung_faengt_gross_an(self):
        # Sie stand hinter »Diese Woche:« und beginnt deshalb manchmal
        # klein. Im Archiv fängt sie einen Absatz an.
        klein = SEITE.replace("Diese Woche: Dichtungen",
                              "Diese Woche: dichtungen")
        self.assertEqual(tippseite.abgelaufener_tipp(klein)["kurz"],
                         "Dichtungen vor dem Frost.")

    def test_titel_und_canonical_zeigen_auf_die_eigene_seite(self):
        self.assertIn("<title>Vor dem Winter: Türdichtungen prüfen | "
                      "Laden.example</title>", self.seite)
        self.assertIn('href="https://a.example/tipp-archiv/'
                      '2026-KW40-vor-dem-winter.html"', self.seite)

    def test_der_name_des_auftritts_wird_geerbt(self):
        # Er gehört nicht ins Programm - er steht schon auf der Seite. Wer
        # ihn einträgt, setzt ihn beim nächsten Kunden falsch.
        fremd = SEITE.replace("| Laden.example", "| Anderer Laden")
        seite = tippseite.archivseite(
            fremd, tippseite.abgelaufener_tipp(fremd), "/a/")
        self.assertIn("| Anderer Laden</title>", seite)

    def test_ohne_strich_im_titel_wird_nichts_angehaengt(self):
        ohne = SEITE.replace(
            "<title>Tipp der Woche - Praxistipps zu Türen und Toren "
            "| Laden.example</title>", "<title>Tipp der Woche</title>")
        seite = tippseite.archivseite(
            ohne, tippseite.abgelaufener_tipp(ohne), "/a/")
        self.assertIn("<title>Vor dem Winter: Türdichtungen prüfen</title>",
                      seite)

    def test_die_ueberschrift_ist_der_tipp_und_nicht_die_rubrik(self):
        self.assertIn("<h1>Vor dem Winter: Türdichtungen prüfen</h1>", self.seite)
        self.assertNotIn("Tipp der Woche von Laden.example", self.seite)

    def test_die_ueberschrift_steht_nicht_doppelt(self):
        self.assertEqual(self.seite.count("Vor dem Winter: Türdichtungen prüfen"),
                         2)  # einmal im title, einmal als h1

    def test_die_einleitung_sagt_woher_der_beitrag_stammt(self):
        self.assertIn("Tipp der Woche aus Kalenderwoche 40", self.seite)
        self.assertIn("erschienen am 28. September 2026", self.seite)
        self.assertNotIn("Lohnt sich das Lesezeichen", self.seite)

    def test_der_text_des_tipps_bleibt_erhalten(self):
        self.assertIn("Alter Text.", self.seite)
        self.assertIn("https://a.example/kw40.png", self.seite)

    def test_unten_stehen_rueckverweise_statt_eines_archivs(self):
        self.assertIn("Zum aktuellen Tipp der Woche", self.seite)
        self.assertIn('href="https://a.example/tipp-archiv/"', self.seite)
        self.assertNotIn("Die Tipps der Vorwochen", self.seite)

    def test_die_montagsanleitung_bleibt_auf_der_lebenden_seite(self):
        self.assertNotIn("ANLEITUNG FUER DAS MONTAGS-UPDATE", self.seite)

    def test_ohne_marken_wird_nichts_geschnitten(self):
        with self.assertRaises(tippseite.SeitenFehler):
            tippseite.archivseite("<html>nichts</html>", self.alt, "/a/")

    def test_ohne_reiter_bleibt_die_seite_wie_sie_war(self):
        self.assertNotIn("tdwReiter", self.seite)


class Seitenreiter(unittest.TestCase):
    """Der Block am linken Rand, der zum aktuellen Tipp führt.

    Auf der Tipp-Seite steht er nicht - dort ist man schon. Im Archiv
    gehört er hin, sonst führt von dort nur der Fließtext zurück.
    """

    def setUp(self):
        self.reiter = tippseite.seitenreiter(UEBERSICHT)
        self.alt = tippseite.abgelaufener_tipp(SEITE)

    def test_er_wird_samt_css_aus_der_seite_geholt(self):
        # Übernommen statt nachgebaut: Farben, Haltepunkte und Text gehören
        # dem Betreiber, nicht dem Programm.
        self.assertIn("#tdwReiter{position:fixed", self.reiter)
        self.assertIn('<div id="tdwReiter">', self.reiter)
        self.assertTrue(self.reiter.endswith(tippseite.REITER_ZU))

    def test_aus_einer_seite_ohne_reiter_kommt_nichts(self):
        self.assertEqual(tippseite.seitenreiter(SEITE), "")
        self.assertEqual(tippseite.seitenreiter("<html></html>"), "")

    def test_er_landet_vor_dem_body_ende(self):
        seite = tippseite.archivseite(SEITE, self.alt, "/a/", "/t.html",
                                      self.reiter)
        self.assertIn("tdwReiter", seite)
        self.assertLess(seite.find("tdwReiter"), seite.find("</body>"))
        self.assertEqual(seite.count("</body>"), 1)

    def test_er_kommt_kein_zweites_mal_hinein(self):
        # Läuft der Archivlauf zweimal über dieselbe Seite, stünde der
        # Reiter sonst doppelt - und mit ihm sein CSS.
        einmal = tippseite.archivseite(SEITE, self.alt, "/a/", "/t.html",
                                       self.reiter)
        zweimal = tippseite.archivseite(einmal, self.alt, "/a/", "/t.html",
                                        self.reiter)
        self.assertEqual(zweimal.count('<div id="tdwReiter">'), 1)

    def test_ohne_ueberschrift_wird_abgebrochen(self):
        with self.assertRaises(tippseite.SeitenFehler):
            tippseite.archivseite(SEITE, {"woche": "40"}, "/a/")


class Uebersicht(unittest.TestCase):
    """`/tipp-archiv/index.html` – hier wird nie etwas entfernt."""

    ALT = {"woche": "40", "jahr": "2026", "titel": "Vor dem Winter: Türdichtungen prüfen",
           "datum": "28. September 2026", "kurz": "Dichtungen vor dem Frost.",
           "vorschau": "https://a.example/kw40.png", "alt": "Grafik KW 40"}

    def setUp(self):
        self.neu = tippseite.uebersicht_erneuern(
            UEBERSICHT, self.ALT, "/tipp-archiv/")

    def test_der_neue_eintrag_steht_oben(self):
        self.assertLess(self.neu.find("Kalenderwoche 40"),
                        self.neu.find("Kalenderwoche 39"))

    def test_der_alte_eintrag_bleibt(self):
        # Das ist der Zweck der Seite: Hier verschwindet nichts.
        self.assertIn("Garagentor einwintern", self.neu)

    def test_das_jahr_bekommt_keine_zweite_ueberschrift(self):
        self.assertEqual(self.neu.count("<h2>2026</h2>"), 1)

    def test_ein_neues_jahr_bekommt_eine_eigene_ueberschrift(self):
        neu = tippseite.uebersicht_erneuern(
            UEBERSICHT, dict(self.ALT, jahr="2027", woche="1"), "/tipp-archiv/")
        self.assertIn("<h2>2027</h2>", neu)
        self.assertIn("<h2>2026</h2>", neu)
        self.assertLess(neu.find("<h2>2027</h2>"), neu.find("<h2>2026</h2>"))

    def test_zweimal_derselbe_eintrag_steht_nur_einmal(self):
        # Wird in derselben Woche nachgebessert, läuft alles ein zweites Mal.
        zweimal = tippseite.uebersicht_erneuern(self.neu, self.ALT, "/tipp-archiv/")
        self.assertEqual(zweimal.count("Kalenderwoche 40"), 1)

    def test_ohne_marken_wird_nichts_angefasst(self):
        with self.assertRaises(tippseite.SeitenFehler):
            tippseite.uebersicht_erneuern("<html>nichts</html>", self.ALT, "/a/")


if __name__ == "__main__":
    unittest.main()
