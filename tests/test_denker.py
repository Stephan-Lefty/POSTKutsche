"""Die Claude-Anbindung – Anweisung, Antwortauswertung, Aufruf.

Kein Netzzugriff und kein echter Aufruf: `claude` wird vorgetäuscht. Was hier
geprüft wird, ist nicht, ob Claude gut schreibt, sondern ob wir eine
schlechte Antwort *erkennen* – ein Text über der Zeichengrenze, eine fehlende
Fassung, ein Satz vor dem JSON.
"""

from __future__ import annotations

import json
import unittest
from unittest import mock

from postkutsche import netzwerke
from postkutsche.denker import kommando, vorlagen
from postkutsche.denker.vorlagen import AntwortFehler

INHALT = {
    "titel": "Sprachsteuerung ohne Internet",
    "text": "Ein Rechner, der zuhört, ohne dass etwas den Raum verlässt.",
    "adresse": "https://blog.example/sprachsteuerung/",
    "bild_adresse": "https://blog.example/bild.png",
    "kategorien": ["Barrierefreiheit", "Technik"],
}


def _antwort(**fassungen) -> str:
    return json.dumps({"fassungen": fassungen})


def _fassung(text="Ein Text.", schlagworte=None, rueckfrage=None):
    return {"text": text, "schlagworte": schlagworte or [], "rueckfrage": rueckfrage}


class Anweisung(unittest.TestCase):
    def test_enthaelt_die_quelle(self):
        a = vorlagen.anweisung(INHALT, ["mastodon"])
        self.assertIn("Sprachsteuerung ohne Internet", a)
        self.assertIn("https://blog.example/sprachsteuerung/", a)
        self.assertIn("Barrierefreiheit", a)

    def test_nennt_die_zeichengrenze_des_netzwerks(self):
        a = vorlagen.anweisung(INHALT, ["mastodon"])
        netz = netzwerke.netzwerk("mastodon")
        self.assertIn(str(netz.zeichen_ziel), a)
        self.assertIn(str(netz.zeichen_max), a)

    def test_mehrere_netzwerke_stehen_alle_drin(self):
        a = vorlagen.anweisung(INHALT, ["mastodon", "linkedin", "instagram"])
        for name in ("Mastodon", "LinkedIn", "Instagram"):
            self.assertIn(name, a)

    def test_verbietet_preise_und_erfindungen(self):
        a = vorlagen.anweisung(INHALT, ["facebook"])
        self.assertIn("Preise", a)
        self.assertIn("erfinden", a)

    def test_verbietet_markdown(self):
        # Markdown erscheint in den Netzwerken als Zeichensalat.
        self.assertIn("Markdown", vorlagen.anweisung(INHALT, ["facebook"]))

    def test_verbietet_die_adresse_im_text(self):
        # Am 2026-08-28 stand der Verweis zweimal in einem Facebook-Beitrag:
        # einmal von Claude geschrieben, einmal beim Zusammensetzen angehängt.
        # Die Anweisung muss das eindeutig regeln.
        a = vorlagen.anweisung(INHALT, ["facebook"])
        self.assertIn("nicht in den Text", a)

    def test_fordert_rueckfragen_statt_raten(self):
        self.assertIn("rueckfrage", vorlagen.anweisung(INHALT, ["mastodon"]))

    def test_instagram_bekommt_den_bildhinweis(self):
        a = vorlagen.anweisung(INHALT, ["instagram"])
        self.assertIn("Ohne Bild", a)

    def test_sagt_ob_ein_bild_da_ist(self):
        mit = vorlagen.anweisung(INHALT, ["instagram"])
        ohne = vorlagen.anweisung({**INHALT, "bild_adresse": None}, ["instagram"])
        self.assertIn("Bild vorhanden: ja", mit)
        self.assertIn("Bild vorhanden: nein", ohne)

    def test_langer_text_wird_gekuerzt(self):
        # Ein Blogbeitrag mit 20.000 Zeichen macht die Anweisung teuer, ohne
        # dass die letzten Absätze für 500 Zeichen Ausgabe etwas beitragen.
        lang = {**INHALT, "text": "Wort " * 4000}
        a = vorlagen.anweisung(lang, ["mastodon"])
        self.assertIn("[hier gekürzt]", a)
        # Der Inhalt wird bei 6.000 Zeichen gekappt; alles Weitere sind die
        # Regeln. Die Grenze wacht darüber, dass die Regeln nicht unbemerkt
        # ausufern - jede Zeile darin steckt in jedem einzelnen Aufruf.
        self.assertLess(len(a), 10_000)

    def test_die_regeln_bleiben_ueberschaubar(self):
        # Ohne Inhalt ist die Anweisung reines Regelwerk. Wächst das über
        # diese Grenze, gehört aufgeräumt statt angebaut.
        nackt = vorlagen.anweisung({"titel": "x", "text": ""}, ["mastodon"])
        self.assertLess(len(nackt), 4_000)

    def test_ohne_netzwerk_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            vorlagen.anweisung(INHALT, [])

    def test_zusatz_kommt_mit(self):
        a = vorlagen.anweisung(INHALT, ["mastodon"], zusatz="Thema der Woche: Türen")
        self.assertIn("Thema der Woche: Türen", a)


class Wiederholung(unittest.TestCase):
    """Kommt ein Produkt erneut dran, muss der Text anders klingen.

    Facebook und Instagram halten wortgleiche Wiederholungen zurück - derselbe
    Beitrag zweimal erreicht weniger als einer.
    """

    def test_frueherer_text_kommt_in_die_anweisung(self):
        a = vorlagen.anweisung(INHALT, ["facebook"],
                               frueher={"facebook": "So stand es im August."})
        self.assertIn("So stand es im August.", a)
        self.assertIn("Schreib etwas anderes", a)

    def test_verlangt_anderen_blickwinkel_statt_wortsalat(self):
        a = vorlagen.anweisung(INHALT, ["facebook"], frueher={"facebook": "alt"})
        self.assertIn("Wechsle den Blickwinkel", a)

    def test_ohne_frueheren_text_steht_nichts_davon_drin(self):
        a = vorlagen.anweisung(INHALT, ["facebook"])
        self.assertNotIn("schon einmal dran", a)

    def test_nur_die_genannten_netzwerke(self):
        a = vorlagen.anweisung(INHALT, ["facebook"],
                               frueher={"facebook": "alt-fb", "mastodon": "alt-ma"})
        self.assertIn("alt-fb", a)
        self.assertIn("alt-ma", a)


class AntwortLesen(unittest.TestCase):
    def test_saubere_antwort(self):
        roh = _antwort(mastodon=_fassung("Kurz und gut.", ["technik"]))
        e = vorlagen.antwort_lesen(roh, ["mastodon"])
        self.assertEqual(e["mastodon"]["text"], "Kurz und gut.")
        self.assertEqual(e["mastodon"]["schlagworte"], "technik")
        self.assertIsNone(e["mastodon"]["rueckfrage"])

    def test_satz_vor_dem_json(self):
        # Sprachmodelle setzen gern etwas davor, auch wenn man es verbietet.
        roh = "Gerne! Hier ist das Ergebnis:\n" + _antwort(mastodon=_fassung())
        self.assertIn("mastodon", vorlagen.antwort_lesen(roh, ["mastodon"]))

    def test_code_zaun(self):
        roh = "```json\n" + _antwort(mastodon=_fassung()) + "\n```"
        self.assertIn("mastodon", vorlagen.antwort_lesen(roh, ["mastodon"]))

    def test_rauten_werden_entfernt(self):
        roh = _antwort(mastodon=_fassung("Text", ["#Technik", "#BAU"]))
        self.assertEqual(
            vorlagen.antwort_lesen(roh, ["mastodon"])["mastodon"]["schlagworte"],
            "technik bau",
        )

    def test_schlagworte_als_zeichenkette(self):
        roh = _antwort(mastodon=_fassung("Text", "technik bau"))
        self.assertEqual(
            vorlagen.antwort_lesen(roh, ["mastodon"])["mastodon"]["schlagworte"],
            "technik bau",
        )

    def test_zu_viele_schlagworte_werden_gekappt(self):
        netz = netzwerke.netzwerk("mastodon")
        roh = _antwort(mastodon=_fassung("Text", [f"w{i}" for i in range(20)]))
        anzahl = len(
            vorlagen.antwort_lesen(roh, ["mastodon"])["mastodon"]["schlagworte"].split()
        )
        self.assertEqual(anzahl, netz.schlagworte_max)

    def test_rueckfrage_kommt_durch(self):
        roh = _antwort(instagram=_fassung("Text", rueckfrage="Welches Bild?"))
        e = vorlagen.antwort_lesen(roh, ["instagram"])
        self.assertEqual(e["instagram"]["rueckfrage"], "Welches Bild?")

    def test_leere_rueckfrage_wird_zu_nichts(self):
        roh = _antwort(mastodon=_fassung("Text", rueckfrage="   "))
        self.assertIsNone(vorlagen.antwort_lesen(roh, ["mastodon"])["mastodon"]["rueckfrage"])

    def test_zu_langer_text_wird_abgelehnt(self):
        # Nicht selbst kürzen: Ein abgeschnittener Satz ist schlimmer als ein
        # Text, der neu geschrieben wird.
        netz = netzwerke.netzwerk("mastodon")
        roh = _antwort(mastodon=_fassung("x" * (netz.zeichen_max + 1)))
        with self.assertRaises(AntwortFehler) as f:
            vorlagen.antwort_lesen(roh, ["mastodon"])
        self.assertIn(str(netz.zeichen_max), str(f.exception))

    def test_fehlende_fassung_wird_gemeldet(self):
        roh = _antwort(mastodon=_fassung())
        with self.assertRaises(AntwortFehler):
            vorlagen.antwort_lesen(roh, ["mastodon", "linkedin"])

    def test_leerer_text_wird_gemeldet(self):
        with self.assertRaises(AntwortFehler):
            vorlagen.antwort_lesen(_antwort(mastodon=_fassung("   ")), ["mastodon"])

    def test_kein_json(self):
        with self.assertRaises(AntwortFehler):
            vorlagen.antwort_lesen("Tut mir leid, das geht nicht.", ["mastodon"])

    def test_json_ohne_fassungen(self):
        with self.assertRaises(AntwortFehler):
            vorlagen.antwort_lesen('{"text": "irgendwas"}', ["mastodon"])


class Nachbesserung(unittest.TestCase):
    """Die Schleife: Claude fragt, Stephan antwortet, der Text wird genauer."""

    def test_anweisung_enthaelt_frage_und_antwort(self):
        a = vorlagen.nachbesserung(
            INHALT, "facebook", "Der bisherige Text.",
            "Was verstellt die Spindel?", "Die Breite, stufenlos.",
        )
        self.assertIn("Der bisherige Text.", a)
        self.assertIn("Was verstellt die Spindel?", a)
        self.assertIn("Die Breite, stufenlos.", a)

    def test_verlangt_ergaenzen_statt_neuschreiben(self):
        # Der bisherige Text war nicht falsch, ihm fehlte eine Angabe. Wer
        # neu schreiben lässt, bekommt einen anderen - womöglich schlechteren.
        a = vorlagen.nachbesserung(INHALT, "facebook", "Text", "Frage?", "Antwort")
        self.assertIn("ergänze ihn, schreib ihn nicht neu", a)

    def test_verbietet_ausschmuecken(self):
        # »verstellt die Breite« darf nicht zu »stufenlos um bis zu 30
        # Zentimeter« werden.
        a = vorlagen.nachbesserung(INHALT, "facebook", "Text", "Frage?", "Antwort")
        self.assertIn("Erfinde aus der Antwort nichts dazu", a)

    def test_erlaubt_erneutes_nachfragen(self):
        a = vorlagen.nachbesserung(INHALT, "facebook", "Text", "Frage?", "Antwort")
        self.assertIn("frag erneut", a)

    def test_nachbessern_liest_die_antwort(self):
        antwort = json.dumps({"fassungen": {"facebook": _fassung("Jetzt genauer.")}})
        huelle = json.dumps({"result": antwort})
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", return_value=_lauf(stdout=huelle)):
            e = kommando.nachbessern(INHALT, "facebook", "Vorher",
                                     "Was denn?", "Das hier.")
        self.assertEqual(e["text"], "Jetzt genauer.")
        self.assertIsNone(e["rueckfrage"])

    def test_erneute_rueckfrage_kommt_durch(self):
        antwort = json.dumps({"fassungen": {"facebook": _fassung(
            "Immer noch unklar.", rueckfrage="Und in welcher Einheit?")}})
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run",
                        return_value=_lauf(stdout=json.dumps({"result": antwort}))):
            e = kommando.nachbessern(INHALT, "facebook", "Vorher", "Was?", "Das.")
        self.assertEqual(e["rueckfrage"], "Und in welcher Einheit?")


def _lauf(rueckgabe=0, stdout="", stderr=""):
    ergebnis = mock.Mock()
    ergebnis.returncode = rueckgabe
    ergebnis.stdout = stdout
    ergebnis.stderr = stderr
    return ergebnis


class Aufruf(unittest.TestCase):
    def test_ohne_claude_kommt_eine_anleitung(self):
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(kommando.ClaudeFehlt) as f:
                kommando.fassungen(INHALT, ["mastodon"])
        self.assertIn("/login", str(f.exception))

    def test_huellobjekt_wird_ausgepackt(self):
        huelle = json.dumps({"result": _antwort(mastodon=_fassung("Aus der Hülle."))})
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", return_value=_lauf(stdout=huelle)):
            e = kommando.fassungen(INHALT, ["mastodon"])
        self.assertEqual(e["mastodon"]["text"], "Aus der Hülle.")

    def test_antwort_ohne_huelle_geht_auch(self):
        # Falls sich das Ausgabeformat wieder ändert.
        roh = _antwort(mastodon=_fassung("Ohne Hülle."))
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", return_value=_lauf(stdout=roh)):
            e = kommando.fassungen(INHALT, ["mastodon"])
        self.assertEqual(e["mastodon"]["text"], "Ohne Hülle.")

    def test_fehlende_anmeldung_wird_erklaert(self):
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run",
                        return_value=_lauf(1, stderr="Not logged in · Please run /login")):
            with self.assertRaises(kommando.ClaudeFehler) as f:
                kommando.fassungen(INHALT, ["mastodon"])
        self.assertIn("angemeldet", str(f.exception))

    def test_fehler_von_claude_wird_gemeldet(self):
        huelle = json.dumps({"is_error": True, "result": "Etwas ging schief"})
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", return_value=_lauf(stdout=huelle)):
            with self.assertRaises(kommando.ClaudeFehler) as f:
                kommando.fassungen(INHALT, ["mastodon"])
        self.assertIn("Etwas ging schief", str(f.exception))

    def test_der_aufruf_bekommt_die_anweisung(self):
        roh = _antwort(mastodon=_fassung())
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", return_value=_lauf(stdout=roh)) as lauf:
            kommando.fassungen(INHALT, ["mastodon"], projekt="blog")
        befehl = lauf.call_args[0][0]
        self.assertEqual(befehl[0], "claude")
        self.assertEqual(befehl[1], "-p")
        self.assertIn("Sprachsteuerung ohne Internet", befehl[2])
        self.assertIn("--output-format", befehl)

    def test_aufruf_laeuft_in_einem_eigenen_leeren_ordner(self):
        # Der Aufruf soll schreiben, nicht im Projekt stöbern. Geprüft wird
        # der Ordner *während* des Aufrufs - danach ist er weg, und genau so
        # soll es sein.
        import os
        roh = _antwort(mastodon=_fassung())
        gesehen = {}

        def merken(*args, **kwargs):
            ordner = kwargs["cwd"]
            gesehen["pfad"] = ordner
            gesehen["inhalt"] = os.listdir(ordner)
            return _lauf(stdout=roh)

        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run", side_effect=merken):
            kommando.fassungen(INHALT, ["mastodon"])

        self.assertEqual(gesehen["inhalt"], [])
        self.assertIn("postkutsche-", gesehen["pfad"])
        self.assertFalse(os.path.exists(gesehen["pfad"]), "Ordner wurde nicht aufgeräumt")

    def test_zeitueberschreitung_wird_gemeldet(self):
        import subprocess
        with mock.patch("shutil.which", return_value="/x/claude"), \
             mock.patch("subprocess.run",
                        side_effect=subprocess.TimeoutExpired("claude", 180)):
            with self.assertRaises(kommando.ClaudeFehler) as f:
                kommando.fassungen(INHALT, ["mastodon"])
        self.assertIn("nicht geantwortet", str(f.exception))


if __name__ == "__main__":
    unittest.main()
