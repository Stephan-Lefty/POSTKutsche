"""Die Ablage: Projekte, Inhalte, Beiträge, Fassungen."""

from __future__ import annotations

import unittest

from hilfen import OhneEigeneKonfiguration
from postkutsche import erstbestueckung
from postkutsche.ablage import (
    BEITRAG_ENTWURF,
    BEITRAG_FREIGEGEBEN,
    BEITRAG_RUECKFRAGE,
    FASSUNG_ABGEHOLT,
    FASSUNG_GESENDET,
    FASSUNG_OFFEN,
    PROJEKT_AKTIV,
    PROJEKT_PAUSIERT,
    VERSAND_HAND,
    Ablage,
    HandarbeitWuerdeVerloren,
    RueckfrageOffen,
)


class Basis(unittest.TestCase):
    def setUp(self):
        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)


class Projekte(Basis):
    def test_anlegen_und_finden(self):
        self.ablage.projekt_anlegen("blog", "Mein Blog", "https://blog.example", "wordpress")
        projekt = self.ablage.projekt("blog")
        self.assertIsNotNone(projekt)
        self.assertEqual(projekt.name, "Mein Blog")
        self.assertTrue(projekt.aktiv)
        self.assertTrue(projekt.freigabe_noetig)

    def test_zweites_anlegen_frischt_auf_statt_zu_scheitern(self):
        # Ein zweites »postkutsche einrichten« darf nicht mit einem Fehler enden.
        self.ablage.projekt_anlegen("blog", "Mein Blog", "https://blog.example", "wordpress")
        self.ablage.projekt_anlegen("blog", "Mein Blog neu", "https://blog.example", "wordpress")
        self.assertEqual(len(self.ablage.projekte()), 1)
        self.assertEqual(self.ablage.projekt("blog").name, "Mein Blog neu")

    def test_einstellungen_ueberleben_die_runde(self):
        self.ablage.projekt_anlegen(
            "shop", "Shop", "https://shop.example", "shopware",
            einstellungen={"store_api": "https://shop.example/store-api", "zahl": 7},
        )
        self.assertEqual(
            self.ablage.projekt("shop").einstellungen["store_api"],
            "https://shop.example/store-api",
        )
        self.assertEqual(self.ablage.projekt("shop").einstellungen["zahl"], 7)

    def test_umlaute_im_namen(self):
        self.ablage.projekt_anlegen(
            "strassenmoebel", "Straßenmöbel", "https://x.example", "shopware"
        )
        self.assertEqual(self.ablage.projekt("strassenmoebel").name, "Straßenmöbel")

    def test_pausieren_und_starten(self):
        self.ablage.projekt_anlegen("blog", "Mein Blog", "https://blog.example", "wordpress")
        self.assertTrue(self.ablage.projekt_zustand("blog", PROJEKT_PAUSIERT))
        self.assertFalse(self.ablage.projekt("blog").aktiv)
        self.ablage.projekt_zustand("blog", PROJEKT_AKTIV)
        self.assertTrue(self.ablage.projekt("blog").aktiv)

    def test_pausieren_eines_unbekannten_projekts_meldet_das(self):
        self.assertFalse(self.ablage.projekt_zustand("gibtsnicht", PROJEKT_PAUSIERT))

    def test_unbekannter_zustand_wird_abgelehnt(self):
        self.ablage.projekt_anlegen("blog", "Mein Blog", "https://blog.example", "wordpress")
        with self.assertRaises(ValueError):
            self.ablage.projekt_zustand("blog", "schlafend")

    def test_nur_aktive(self):
        self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        self.ablage.projekt_anlegen("b", "B", "https://b.example", "wordpress")
        self.ablage.projekt_zustand("b", PROJEKT_PAUSIERT)
        self.assertEqual([p.kennung for p in self.ablage.projekte(nur_aktive=True)], ["a"])
        self.assertEqual(len(self.ablage.projekte()), 2)

    def test_loeschen_raeumt_die_beitraege_mit_weg(self):
        projekt = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        beitrag = self.ablage.beitrag_anlegen(projekt.id, "2026-09-01T16:00:00Z")
        self.ablage.fassung_setzen(beitrag, "mastodon", "Text")
        self.assertTrue(self.ablage.projekt_loeschen("a"))
        # Ohne PRAGMA foreign_keys=ON bliebe hier eine Waise zurück.
        uebrig = self.ablage.db.execute("SELECT COUNT(*) FROM fassungen").fetchone()[0]
        self.assertEqual(uebrig, 0)


class Erstbestueckung(OhneEigeneKonfiguration):
    """Die Erstbestückung – ohne eigene Konfiguration sind es die Beispiele.

    Im Repository stehen keine echten Adressen; die eigenen Seiten liegen in
    ~/.config/postkutsche/projekte.json. Diese Tests laufen deshalb gegen einen
    leeren Konfigurationsordner und sehen die Beispiele.
    """

    def setUp(self):
        super().setUp()
        self.ablage = Ablage(":memory:")
        self.addCleanup(self.ablage.schliessen)

    def test_beispiele_werden_angelegt(self):
        kennungen = erstbestueckung.einrichten(self.ablage)
        self.assertEqual(len(kennungen), len(erstbestueckung.BEISPIELE))
        self.assertEqual(len(self.ablage.projekte()), len(erstbestueckung.BEISPIELE))

    def test_jedes_projekt_hat_eine_eigene_farbe(self):
        erstbestueckung.einrichten(self.ablage)
        farben = [p.farbe for p in self.ablage.projekte()]
        self.assertEqual(len(farben), len(set(farben)))

    def test_arten_sind_bekannt(self):
        erstbestueckung.einrichten(self.ablage)
        for projekt in self.ablage.projekte():
            self.assertIn(projekt.art, ("wordpress", "shopware", "seitenkarte"))

    def test_jede_art_bringt_ihre_adresse_mit(self):
        erstbestueckung.einrichten(self.ablage)
        schluessel = {"wordpress": "rest", "shopware": "store_api",
                      "seitenkarte": "seitenkarte"}
        for projekt in self.ablage.projekte():
            with self.subTest(projekt=projekt.kennung):
                self.assertIn(schluessel[projekt.art], projekt.einstellungen)

    def test_zweimal_einrichten_aendert_die_zahl_nicht(self):
        erstbestueckung.einrichten(self.ablage)
        erstbestueckung.einrichten(self.ablage)
        self.assertEqual(len(self.ablage.projekte()), len(erstbestueckung.BEISPIELE))

    def test_beispiele_verraten_nichts(self):
        # Alle Beispieladressen liegen unter .example – reserviert nach
        # RFC 2606 und damit garantiert niemandes Eigentum.
        for eintrag in erstbestueckung.BEISPIELE:
            with self.subTest(kennung=eintrag["kennung"]):
                self.assertRegex(eintrag["adresse"], r"^https://[a-z0-9.-]+\.example$")

    def test_eigene_datei_sticht_die_beispiele(self):
        import json
        from pathlib import Path as Pfad

        Pfad(self.konfigurationsordner, "projekte.json").write_text(
            json.dumps([{
                "kennung": "eigenes", "name": "Eigenes", "adresse": "https://e.example",
                "art": "wordpress", "farbe": "#123456",
                "einstellungen": {"rest": "https://e.example/wp-json/wp/v2"},
            }]),
            encoding="utf-8",
        )
        kennungen = erstbestueckung.einrichten(self.ablage)
        self.assertEqual(kennungen, ["eigenes"])
        self.assertTrue(erstbestueckung.aus_eigener_datei())

    def test_ohne_eigene_datei_meldet_das(self):
        self.assertFalse(erstbestueckung.aus_eigener_datei())


class Inhalte(Basis):
    def setUp(self):
        super().setUp()
        self.projekt = self.ablage.projekt_anlegen(
            "blog", "Mein Blog", "https://blog.example", "wordpress"
        )

    def test_neuer_inhalt_ist_neu(self):
        _, neu = self.ablage.inhalt_merken(
            self.projekt.id, "42", "Titel", "https://blog.example/x"
        )
        self.assertTrue(neu)

    def test_bekannter_inhalt_ist_nicht_neu(self):
        # Sonst stünde jeder nachträglich korrigierte Blogbeitrag wieder als
        # Vorschlag im Kalender.
        self.ablage.inhalt_merken(self.projekt.id, "42", "Titel", "https://blog.example/x")
        kennung, neu = self.ablage.inhalt_merken(
            self.projekt.id, "42", "Titel geändert", "https://blog.example/x"
        )
        self.assertFalse(neu)
        self.assertEqual(self.ablage.inhalte(self.projekt.id)[0]["titel"], "Titel geändert")

    def test_gleiche_fremd_id_in_zwei_projekten(self):
        # WordPress zählt je Seite ab 1 – Beitrag 42 gibt es zweimal.
        anderes = self.ablage.projekt_anlegen(
            "zweitblog", "Zweitblog", "https://zweitblog.example", "wordpress"
        )
        _, neu_a = self.ablage.inhalt_merken(self.projekt.id, "42", "A", "https://a.example")
        _, neu_b = self.ablage.inhalt_merken(anderes.id, "42", "B", "https://b.example")
        self.assertTrue(neu_a)
        self.assertTrue(neu_b)


class Beitraege(Basis):
    def setUp(self):
        super().setUp()
        self.projekt = self.ablage.projekt_anlegen(
            "blog", "Mein Blog", "https://blog.example", "wordpress"
        )

    def test_im_zeitraum(self):
        self.ablage.beitrag_anlegen(self.projekt.id, "2026-09-15T10:00:00Z")
        self.ablage.beitrag_anlegen(self.projekt.id, "2026-10-15T10:00:00Z")
        treffer = self.ablage.beitraege_im_zeitraum(
            "2026-08-31T22:00:00Z", "2026-09-30T22:00:00Z"
        )
        self.assertEqual(len(treffer), 1)

    def test_ausblenden_ist_ansichtssache(self):
        # Das Häkchen links filtert die Ansicht – mit dem Zustand des Projekts
        # hat das nichts zu tun.
        anderes = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        self.ablage.beitrag_anlegen(self.projekt.id, "2026-09-15T10:00:00Z")
        self.ablage.beitrag_anlegen(anderes.id, "2026-09-15T11:00:00Z")
        treffer = self.ablage.beitraege_im_zeitraum(
            "2026-09-01T00:00:00Z", "2026-09-30T00:00:00Z", ["blog"]
        )
        self.assertEqual(len(treffer), 1)
        self.assertEqual(treffer[0]["projekt_kennung"], "blog")

    def test_alle_ausgeblendet_heisst_leer(self):
        self.ablage.beitrag_anlegen(self.projekt.id, "2026-09-15T10:00:00Z")
        treffer = self.ablage.beitraege_im_zeitraum(
            "2026-09-01T00:00:00Z", "2026-09-30T00:00:00Z", []
        )
        self.assertEqual(treffer, [])

    def test_verschieben(self):
        beitrag = self.ablage.beitrag_anlegen(self.projekt.id, "2026-09-15T10:00:00Z")
        self.assertTrue(self.ablage.beitrag_verschieben(beitrag, "2026-09-16T10:00:00Z"))
        treffer = self.ablage.beitraege_im_zeitraum(
            "2026-09-16T00:00:00Z", "2026-09-17T00:00:00Z"
        )
        self.assertEqual(len(treffer), 1)

    def test_faellig_nur_wenn_freigegeben(self):
        self.ablage.beitrag_anlegen(
            self.projekt.id, "2026-09-15T10:00:00Z", zustand=BEITRAG_ENTWURF
        )
        self.assertEqual(self.ablage.faellige_beitraege("2026-09-20T00:00:00Z"), [])

    def test_faellig_wenn_freigegeben(self):
        self.ablage.beitrag_anlegen(
            self.projekt.id, "2026-09-15T10:00:00Z", zustand=BEITRAG_FREIGEGEBEN
        )
        self.assertEqual(len(self.ablage.faellige_beitraege("2026-09-20T00:00:00Z")), 1)

    def test_pausiertes_projekt_sendet_nicht(self):
        # Das ist der ganze Sinn des Pausierens.
        self.ablage.beitrag_anlegen(
            self.projekt.id, "2026-09-15T10:00:00Z", zustand=BEITRAG_FREIGEGEBEN
        )
        self.ablage.projekt_zustand("blog", PROJEKT_PAUSIERT)
        self.assertEqual(self.ablage.faellige_beitraege("2026-09-20T00:00:00Z"), [])

    def test_pausieren_loescht_nichts(self):
        self.ablage.beitrag_anlegen(self.projekt.id, "2026-09-15T10:00:00Z")
        self.ablage.projekt_zustand("blog", PROJEKT_PAUSIERT)
        treffer = self.ablage.beitraege_im_zeitraum(
            "2026-09-01T00:00:00Z", "2026-09-30T00:00:00Z"
        )
        self.assertEqual(len(treffer), 1)

    def test_zukunft_ist_noch_nicht_faellig(self):
        self.ablage.beitrag_anlegen(
            self.projekt.id, "2026-12-24T10:00:00Z", zustand=BEITRAG_FREIGEGEBEN
        )
        self.assertEqual(self.ablage.faellige_beitraege("2026-09-20T00:00:00Z"), [])


class Fassungen(Basis):
    def setUp(self):
        super().setUp()
        projekt = self.ablage.projekt_anlegen(
            "blog", "Mein Blog", "https://blog.example", "wordpress"
        )
        self.beitrag = self.ablage.beitrag_anlegen(projekt.id, "2026-09-15T10:00:00Z")

    def test_eine_fassung_je_netzwerk(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Erster Text")
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Zweiter Text")
        fassungen = self.ablage.fassungen(self.beitrag)
        self.assertEqual(len(fassungen), 1)
        self.assertEqual(fassungen[0]["text"], "Zweiter Text")

    def test_mehrere_netzwerke_am_selben_beitrag(self):
        # Ein Beitrag, drei Netzwerke – ein Kärtchen im Kalender, nicht drei.
        for netz in ("mastodon", "linkedin", "facebook"):
            self.ablage.fassung_setzen(self.beitrag, netz, f"Text für {netz}")
        self.assertEqual(len(self.ablage.fassungen(self.beitrag)), 3)

    def test_neu_geschrieben_heisst_wieder_offen(self):
        kennung = self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text")
        self.ablage.fassung_vermerken(kennung, FASSUNG_GESENDET, "https://mastodon.example/x")
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Anderer Text")
        fassung = self.ablage.fassungen(self.beitrag)[0]
        self.assertEqual(fassung["zustand"], FASSUNG_OFFEN)
        self.assertIsNone(fassung["gesendet"])
        self.assertIsNone(fassung["fremd_adresse"])

    def test_von_hand_abgeholt(self):
        kennung = self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text", versandart=VERSAND_HAND
        )
        self.ablage.fassung_vermerken(kennung, FASSUNG_ABGEHOLT)
        fassung = self.ablage.fassungen(self.beitrag)[0]
        self.assertEqual(fassung["zustand"], FASSUNG_ABGEHOLT)
        self.assertIsNotNone(fassung["gesendet"])

    def test_gescheitert_bekommt_keinen_sendezeitpunkt(self):
        kennung = self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text")
        self.ablage.fassung_vermerken(
            kennung, "gescheitert", fehler="Server antwortet mit 503"
        )
        fassung = self.ablage.fassungen(self.beitrag)[0]
        self.assertIsNone(fassung["gesendet"])
        self.assertIn("503", fassung["fehler"])


class Wiederholen(Basis):
    def setUp(self):
        super().setUp()
        self.projekt = self.ablage.projekt_anlegen(
            "strassenmoebel", "Straßenmöbel", "https://m.example", "shopware"
        )
        self.alt = self.ablage.beitrag_anlegen(
            self.projekt.id, "2026-06-15T10:00:00Z", notiz="Sommeraktion"
        )
        for netz in ("facebook", "instagram"):
            kennung = self.ablage.fassung_setzen(
                self.alt, netz, f"Sommertext für {netz}", "sommer bau", "/bilder/a.jpg"
            )
            self.ablage.fassung_vermerken(kennung, FASSUNG_GESENDET, "https://fb.example/1")

    def test_alter_beitrag_bleibt_stehen(self):
        # Der Kalender im Juni muss danach immer noch aussehen wie im Juni.
        self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        alt = self.ablage.beitrag(self.alt)
        self.assertEqual(alt["geplant"], "2026-06-15T10:00:00Z")
        self.assertEqual(
            self.ablage.fassungen(self.alt)[0]["zustand"], FASSUNG_GESENDET
        )

    def test_wiederholung_ist_entwurf(self):
        neu = self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        self.assertEqual(self.ablage.beitrag(neu)["zustand"], BEITRAG_ENTWURF)

    def test_texte_und_bilder_kommen_mit(self):
        neu = self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        fassungen = {f["netzwerk"]: f for f in self.ablage.fassungen(neu)}
        self.assertEqual(len(fassungen), 2)
        self.assertEqual(fassungen["facebook"]["text"], "Sommertext für facebook")
        self.assertEqual(fassungen["facebook"]["bild_pfad"], "/bilder/a.jpg")
        self.assertEqual(fassungen["facebook"]["schlagworte"], "sommer bau")

    def test_uebernommene_fassung_gilt_als_ungesendet(self):
        # Sonst hielte der Zeitplan sie für erledigt und schickte sie nie.
        neu = self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        for fassung in self.ablage.fassungen(neu):
            with self.subTest(netz=fassung["netzwerk"]):
                self.assertEqual(fassung["zustand"], FASSUNG_OFFEN)
                self.assertIsNone(fassung["gesendet"])

    def test_ohne_texte_bleibt_die_huelle(self):
        neu = self.ablage.beitrag_wiederholen(
            self.alt, "2027-06-15T10:00:00Z", texte_uebernehmen=False
        )
        self.assertEqual(self.ablage.fassungen(neu), [])

    def test_kette_zeigt_auf_den_urahn(self):
        # Die dritte Runde darf nicht auf die zweite zeigen, sonst muss man
        # sich für »die wievielte ist das?« durch die Kette hangeln.
        zweite = self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        dritte = self.ablage.beitrag_wiederholen(zweite, "2028-06-15T10:00:00Z")
        self.assertEqual(self.ablage.beitrag(dritte)["wiederholung_von"], self.alt)

    def test_alle_runden_auffindbar(self):
        zweite = self.ablage.beitrag_wiederholen(self.alt, "2027-06-15T10:00:00Z")
        self.ablage.beitrag_wiederholen(zweite, "2028-06-15T10:00:00Z")
        runden = self.ablage.wiederholungen(zweite)
        self.assertEqual(len(runden), 3)
        self.assertEqual([r["id"] for r in runden][0], self.alt)

    def test_unbekannter_beitrag_wird_gemeldet(self):
        with self.assertRaises(ValueError):
            self.ablage.beitrag_wiederholen(9999, "2027-06-15T10:00:00Z")


class Veroeffentlichte(Basis):
    def setUp(self):
        super().setUp()
        self.projekt = self.ablage.projekt_anlegen(
            "a", "A", "https://a.example", "wordpress"
        )

    def _beitrag_mit(self, zustand, termin="2026-06-15T10:00:00Z"):
        beitrag = self.ablage.beitrag_anlegen(self.projekt.id, termin)
        kennung = self.ablage.fassung_setzen(beitrag, "mastodon", "Text")
        if zustand is not None:
            self.ablage.fassung_vermerken(kennung, zustand)
        return beitrag

    def test_entwuerfe_sind_kein_vorrat(self):
        self._beitrag_mit(None)
        self.assertEqual(self.ablage.veroeffentlichte(), [])

    def test_gesendetes_taucht_auf(self):
        self._beitrag_mit(FASSUNG_GESENDET)
        self.assertEqual(len(self.ablage.veroeffentlichte()), 1)

    def test_von_hand_eingestelltes_zaehlt_mit(self):
        # Für »was lief schon?« ist der Weg nach draußen gleichgültig.
        self._beitrag_mit(FASSUNG_ABGEHOLT)
        self.assertEqual(len(self.ablage.veroeffentlichte()), 1)

    def test_beitrag_in_zwei_netzen_erscheint_einmal(self):
        beitrag = self.ablage.beitrag_anlegen(self.projekt.id, "2026-06-15T10:00:00Z")
        for netz in ("facebook", "instagram"):
            kennung = self.ablage.fassung_setzen(beitrag, netz, "Text")
            self.ablage.fassung_vermerken(kennung, FASSUNG_GESENDET)
        vorrat = self.ablage.veroeffentlichte()
        self.assertEqual(len(vorrat), 1)
        self.assertEqual(vorrat[0]["anzahl_fassungen"], 2)

    def test_nach_projekt_gefiltert(self):
        anderes = self.ablage.projekt_anlegen("b", "B", "https://b.example", "wordpress")
        self._beitrag_mit(FASSUNG_GESENDET)
        beitrag = self.ablage.beitrag_anlegen(anderes.id, "2026-06-16T10:00:00Z")
        self.ablage.fassung_vermerken(
            self.ablage.fassung_setzen(beitrag, "mastodon", "T"), FASSUNG_GESENDET
        )
        self.assertEqual(len(self.ablage.veroeffentlichte(["a"])), 1)
        self.assertEqual(len(self.ablage.veroeffentlichte()), 2)


class Rueckfragen(Basis):
    def setUp(self):
        super().setUp()
        projekt = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        self.beitrag = self.ablage.beitrag_anlegen(projekt.id, "2026-09-15T10:00:00Z")

    def test_fassung_ohne_rueckfrage_bleibt_entwurf(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text")
        self.assertEqual(self.ablage.beitrag(self.beitrag)["zustand"], BEITRAG_ENTWURF)

    def test_rueckfrage_setzt_den_beitrag_um(self):
        self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text",
            rueckfrage="Kein Bild vorhanden – welches soll genommen werden?",
        )
        self.assertEqual(
            self.ablage.beitrag(self.beitrag)["zustand"], BEITRAG_RUECKFRAGE
        )

    def test_rueckfrage_verhindert_die_freigabe(self):
        # Der ganze Sinn einer Rückfrage ist, dass sie beantwortet wird, bevor
        # der Text rausgeht. Wer sie übergehen kann, übergeht sie.
        self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text", rueckfrage="Welches Bild?"
        )
        with self.assertRaises(RueckfrageOffen) as fehler:
            self.ablage.freigeben(self.beitrag)
        self.assertIn("Welches Bild?", str(fehler.exception))

    def test_freigabe_ohne_text_geht_nicht(self):
        with self.assertRaises(RueckfrageOffen):
            self.ablage.freigeben(self.beitrag)

    def test_freigabe_wenn_alles_klar_ist(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text")
        self.ablage.freigeben(self.beitrag)
        self.assertEqual(
            self.ablage.beitrag(self.beitrag)["zustand"], BEITRAG_FREIGEGEBEN
        )

    def test_bearbeiten_beantwortet_die_rueckfrage(self):
        # Wer den Text selbst in die Hand nimmt, hat die Frage beantwortet.
        kennung = self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text", rueckfrage="Welches Bild?"
        )
        self.ablage.fassung_bearbeiten(kennung, "Mein eigener Text")
        self.assertEqual(self.ablage.rueckfragen(self.beitrag), [])
        self.ablage.freigeben(self.beitrag)

    def test_eine_von_zwei_rueckfragen_reicht_zum_blockieren(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text")
        self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text", rueckfrage="Welches Bild?"
        )
        with self.assertRaises(RueckfrageOffen):
            self.ablage.freigeben(self.beitrag)

    def test_zustand_geht_zurueck_auf_entwurf(self):
        kennung = self.ablage.fassung_setzen(
            self.beitrag, "instagram", "Text", rueckfrage="Welches Bild?"
        )
        self.ablage.fassung_bearbeiten(kennung, "Antwort")
        self.assertEqual(self.ablage.beitrag(self.beitrag)["zustand"], BEITRAG_ENTWURF)

    def test_leere_rueckfrage_zaehlt_nicht(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Text", rueckfrage="")
        self.assertEqual(self.ablage.rueckfragen(self.beitrag), [])


class Handarbeit(Basis):
    def setUp(self):
        super().setUp()
        projekt = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        self.beitrag = self.ablage.beitrag_anlegen(projekt.id, "2026-09-15T10:00:00Z")
        self.fassung = self.ablage.fassung_setzen(self.beitrag, "mastodon", "Von Claude")

    def test_bearbeiten_merkt_sich_die_handarbeit(self):
        self.ablage.fassung_bearbeiten(self.fassung, "Von mir gefeilt")
        zeile = self.ablage.fassungen(self.beitrag)[0]
        self.assertEqual(zeile["text"], "Von mir gefeilt")
        self.assertTrue(zeile["von_hand"])

    def test_neu_schreiben_wuerde_handarbeit_verwerfen(self):
        # Zwanzig Minuten Feilarbeit dürfen nicht auf einen Klick verschwinden.
        self.ablage.fassung_bearbeiten(self.fassung, "Von mir gefeilt")
        with self.assertRaises(HandarbeitWuerdeVerloren):
            self.ablage.fassung_setzen(self.beitrag, "mastodon", "Wieder von Claude")
        self.assertEqual(self.ablage.fassungen(self.beitrag)[0]["text"],
                         "Von mir gefeilt")

    def test_ausdruecklich_erlaubt_geht_es_doch(self):
        self.ablage.fassung_bearbeiten(self.fassung, "Von mir gefeilt")
        self.ablage.fassung_setzen(
            self.beitrag, "mastodon", "Wieder von Claude",
            handarbeit_ueberschreiben=True,
        )
        zeile = self.ablage.fassungen(self.beitrag)[0]
        self.assertEqual(zeile["text"], "Wieder von Claude")
        self.assertFalse(zeile["von_hand"])

    def test_unberuehrte_fassung_darf_ueberschrieben_werden(self):
        self.ablage.fassung_setzen(self.beitrag, "mastodon", "Zweiter Versuch")
        self.assertEqual(self.ablage.fassungen(self.beitrag)[0]["text"],
                         "Zweiter Versuch")

    def test_anderes_netzwerk_ist_nicht_betroffen(self):
        self.ablage.fassung_bearbeiten(self.fassung, "Von mir gefeilt")
        self.ablage.fassung_setzen(self.beitrag, "linkedin", "Von Claude")
        texte = {f["netzwerk"]: f["text"] for f in self.ablage.fassungen(self.beitrag)}
        self.assertEqual(texte["mastodon"], "Von mir gefeilt")
        self.assertEqual(texte["linkedin"], "Von Claude")

    def test_schlagworte_und_bild_lassen_sich_mitaendern(self):
        self.ablage.fassung_bearbeiten(
            self.fassung, "Text", schlagworte="bau tuer", bild_pfad="/bilder/x.jpg"
        )
        zeile = self.ablage.fassungen(self.beitrag)[0]
        self.assertEqual(zeile["schlagworte"], "bau tuer")
        self.assertEqual(zeile["bild_pfad"], "/bilder/x.jpg")

    def test_wiederholung_erbt_die_handarbeit_nicht(self):
        # Die Wiederholung ist ein neuer Entwurf; die Handarbeit bleibt am
        # Original. Sonst ließe sich der neue Text nie von Claude schreiben.
        self.ablage.fassung_bearbeiten(self.fassung, "Von mir gefeilt")
        neu = self.ablage.beitrag_wiederholen(self.beitrag, "2027-09-15T10:00:00Z")
        self.assertFalse(self.ablage.fassungen(neu)[0]["von_hand"])


class Konten(Basis):
    def test_anlegen_und_zuordnen(self):
        projekt = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        konto = self.ablage.konto_anlegen(
            "mastodon", "beispiel-instanz", einstellungen={"instanz": "https://mastodon.example"}
        )
        self.ablage.konto_zuordnen(projekt.id, konto)
        zugeordnet = self.ablage.konten_von(projekt.id)
        self.assertEqual(len(zugeordnet), 1)
        self.assertEqual(zugeordnet[0]["netzwerk"], "mastodon")

    def test_zweimal_zuordnen_bleibt_einmal(self):
        projekt = self.ablage.projekt_anlegen("a", "A", "https://a.example", "wordpress")
        konto = self.ablage.konto_anlegen("mastodon", "beispiel-instanz")
        self.ablage.konto_zuordnen(projekt.id, konto)
        self.ablage.konto_zuordnen(projekt.id, konto)
        self.assertEqual(len(self.ablage.konten_von(projekt.id)), 1)

    def test_kein_token_in_der_ablage(self):
        # Geheimnisse gehören in den Schlüsselbund, nicht hierher. Der Test
        # hält das fest, damit es niemand aus Bequemlichkeit ändert.
        self.ablage.konto_anlegen(
            "mastodon", "beispiel-instanz", einstellungen={"instanz": "https://mastodon.example"}
        )
        spalten = [
            zeile[1] for zeile in self.ablage.db.execute("PRAGMA table_info(konten)")
        ]
        for verboten in ("token", "passwort", "geheimnis", "secret"):
            self.assertNotIn(verboten, spalten)


if __name__ == "__main__":
    unittest.main()
