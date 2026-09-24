"""Die vier Wege, auf denen ein Text entsteht.

**Kein Netz.** Geprüft wird gegen aufgezeichnete Antworten: `json_senden`
wird ersetzt, und was hineingeht, wird genauso geprüft wie das, was
herauskommt. Ein Test, der wirklich anruft, prüft die Leitung und nicht den
Code – und er fällt, sobald jemand ohne Netz arbeitet.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from typing import Any
from unittest import mock

from postkutsche import konfiguration
from postkutsche.denker import anthropisch, hand, netz, offen
from postkutsche.denker.netz import DenkerFehler

INHALT = {
    "titel": "Kastenfenster, saniert statt ersetzt",
    "text": ("Ein Kastenfenster muss nicht raus, damit es dicht wird. "
             "Die Bänder werden nachgestellt, die Dichtung erneuert. "
             "Der dritte Satz beschreibt den Anstrich, der im Frühjahr "
             "fällig wird, und braucht deshalb Platz."),
    "adresse": "https://altbau.example/kastenfenster",
    "bild_adresse": None,
    "kategorien": [],
}

ANTWORT = {"fassungen": {"mastodon": {
    "text": "Ein Kastenfenster muss nicht raus, damit es dicht wird.",
    "schlagworte": ["#altbau", "fenster"],
}}}


def _offene_antwort(text: str, grund: str = "stop") -> dict[str, Any]:
    return {"choices": [{"message": {"content": text}, "finish_reason": grund}]}


def _anthropische_antwort(text: str, grund: str = "end_turn") -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "stop_reason": grund}


class OffenerWeg(unittest.TestCase):
    """Alles, was die OpenAI-Form spricht – Ollama, ChatGPT, der Rest."""

    def test_anfrage_traegt_modell_und_anweisung(self):
        gesehen = {}

        def merken(adresse, kopfzeilen, rumpf, **_):
            gesehen.update(adresse=adresse, kopfzeilen=kopfzeilen, rumpf=rumpf)
            return _offene_antwort(json.dumps(ANTWORT))

        with mock.patch.object(netz, "json_senden", merken):
            offen.fassungen(INHALT, ["mastodon"],
                            einstellungen={"adresse": "http://127.0.0.1:1234/v1",
                                           "modell": "kleines-modell"})

        self.assertEqual(gesehen["adresse"],
                         "http://127.0.0.1:1234/v1/chat/completions")
        self.assertEqual(gesehen["rumpf"]["model"], "kleines-modell")
        self.assertIn("Kastenfenster",
                      gesehen["rumpf"]["messages"][0]["content"])

    def test_ohne_schluessel_keine_kopfzeile(self):
        """Ollama läuft ohne Konto – eine leere Vollmacht wäre schlechter Stil."""
        gesehen = {}
        with mock.patch.object(netz, "json_senden",
                               lambda a, k, r, **_: gesehen.update(k=k)
                               or _offene_antwort(json.dumps(ANTWORT))):
            offen.fassungen(INHALT, ["mastodon"], einstellungen={})
        self.assertNotIn("Authorization", gesehen["k"])

    def test_mit_schluessel_als_traeger(self):
        gesehen = {}
        with mock.patch.object(netz, "json_senden",
                               lambda a, k, r, **_: gesehen.update(k=k)
                               or _offene_antwort(json.dumps(ANTWORT))):
            offen.fassungen(INHALT, ["mastodon"],
                            einstellungen={"schluessel": "geheim"})
        self.assertEqual(gesehen["k"]["Authorization"], "Bearer geheim")

    def test_text_auch_als_liste_von_bausteinen(self):
        """Manche Dienste liefern den Inhalt zerlegt statt am Stück."""
        antwort = {"choices": [{"message": {"content": [
            {"type": "text", "text": json.dumps(ANTWORT)[:20]},
            {"type": "text", "text": json.dumps(ANTWORT)[20:]},
        ]}}]}
        with mock.patch.object(netz, "json_senden", lambda *a, **k: antwort):
            fassungen = offen.fassungen(INHALT, ["mastodon"])
        self.assertIn("Kastenfenster", fassungen["mastodon"]["text"])

    def test_abgeschnittene_antwort_sagt_das(self):
        with mock.patch.object(netz, "json_senden",
                               lambda *a, **k: _offene_antwort("", "length")):
            with self.assertRaises(DenkerFehler) as f:
                offen.fassungen(INHALT, ["mastodon"])
        self.assertIn("abgeschnitten", str(f.exception))

    def test_erreichbar_ist_falsch_wenn_niemand_antwortet(self):
        def schweigen(*a, **k):
            raise DenkerFehler("niemand da")

        with mock.patch.object(netz, "json_senden", schweigen):
            self.assertFalse(offen.erreichbar({}))


class AnthropischerWeg(unittest.TestCase):

    def test_kopfzeilen_und_fassung(self):
        gesehen = {}
        with mock.patch.object(netz, "json_senden",
                               lambda a, k, r, **_: gesehen.update(a=a, k=k, r=r)
                               or _anthropische_antwort(json.dumps(ANTWORT))):
            anthropisch.fassungen(INHALT, ["mastodon"],
                                  einstellungen={"schluessel": "sk-test"})

        self.assertEqual(gesehen["a"], anthropisch.ADRESSE)
        self.assertEqual(gesehen["k"]["x-api-key"], "sk-test")
        self.assertEqual(gesehen["k"]["anthropic-version"], anthropisch.FASSUNG)

    def test_kein_regler_fuer_zufall(self):
        """»temperature« lehnen die neueren Modelle mit einer 400 ab."""
        gesehen = {}
        with mock.patch.object(netz, "json_senden",
                               lambda a, k, r, **_: gesehen.update(r=r)
                               or _anthropische_antwort(json.dumps(ANTWORT))):
            anthropisch.fassungen(INHALT, ["mastodon"],
                                  einstellungen={"schluessel": "sk", "temperatur": 0.9})
        self.assertNotIn("temperature", gesehen["r"])
        self.assertNotIn("top_p", gesehen["r"])

    def test_ohne_schluessel_nennt_den_befehl(self):
        with self.assertRaises(DenkerFehler) as f:
            anthropisch.fassungen(INHALT, ["mastodon"], einstellungen={})
        self.assertIn("denker schluessel", str(f.exception))

    def test_abgelehnte_anfrage_ist_kein_leerer_text(self):
        """Eine Ablehnung kommt mit Erfolg zurück – nur eben ohne Inhalt."""
        antwort = {"content": [], "stop_reason": "refusal"}
        with mock.patch.object(netz, "json_senden", lambda *a, **k: antwort):
            with self.assertRaises(DenkerFehler) as f:
                anthropisch.fassungen(INHALT, ["mastodon"],
                                      einstellungen={"schluessel": "sk"})
        self.assertIn("abgelehnt", str(f.exception))

    def test_abgeschnittene_antwort_sagt_das(self):
        with mock.patch.object(netz, "json_senden",
                               lambda *a, **k: _anthropische_antwort("", "max_tokens")):
            with self.assertRaises(DenkerFehler) as f:
                anthropisch.fassungen(INHALT, ["mastodon"],
                                      einstellungen={"schluessel": "sk"})
        self.assertIn("abgeschnitten", str(f.exception))


class VonHand(unittest.TestCase):

    def test_gibt_ein_geruest_statt_eines_leeren_feldes(self):
        fassungen = hand.fassungen(INHALT, ["mastodon", "facebook"])
        self.assertIn("Kastenfenster", fassungen["mastodon"]["text"])
        self.assertIsNone(fassungen["mastodon"]["rueckfrage"])
        self.assertEqual(fassungen["facebook"]["schlagworte"], "")

    def test_haelt_die_zeichengrenze_ein(self):
        """Mastodon nimmt 500 Zeichen. Was länger ist, wird nicht angenommen."""
        lang = dict(INHALT, text="Ein sehr langer Satz. " * 200)
        fassungen = hand.fassungen(lang, ["mastodon"])
        self.assertLessEqual(len(fassungen["mastodon"]["text"]), 500)

    def test_schneidet_keinen_satz_mitten_durch(self):
        fassungen = hand.fassungen(INHALT, ["mastodon"])
        text = fassungen["mastodon"]["text"].strip()
        self.assertTrue(text.endswith((".", "!", "?")) or "\n" not in text,
                        f"Endet mitten im Satz: {text[-60:]!r}")

    def test_ohne_anriss_bleibt_der_titel(self):
        fassungen = hand.fassungen({"titel": "Nur ein Titel", "text": ""},
                                   ["mastodon"])
        self.assertEqual(fassungen["mastodon"]["text"], "Nur ein Titel")

    def test_nachbessern_gibt_es_nicht(self):
        with self.assertRaises(NotImplementedError):
            hand.nachbessern(INHALT, "mastodon", "Vorher", "Was?", "Das.")

    def test_ist_immer_erreichbar(self):
        self.assertTrue(hand.erreichbar())


class FehlerLesen(unittest.TestCase):
    """Aus einem Statuscode soll ein Satz werden, der weiterhilft."""

    def _fehler(self, code: int, rumpf: str) -> str:
        # Mit echtem Rumpf statt vorgetäuschtem read(): So liest der Code
        # denselben Weg wie im Betrieb, und nichts bleibt ungeschlossen.
        fehler = urllib.error.HTTPError(
            "https://dienst.example/v1", code, "egal", {},  # type: ignore[arg-type]
            io.BytesIO(rumpf.encode("utf-8")))
        try:
            return netz._httpfehler_lesen(fehler)
        finally:
            fehler.close()

    def test_schluessel_abgelehnt(self):
        meldung = self._fehler(401, json.dumps(
            {"error": {"message": "invalid x-api-key"}}))
        self.assertIn("Zugangsschlüssel", meldung)
        self.assertIn("invalid x-api-key", meldung)

    def test_zu_viele_anfragen(self):
        self.assertIn("Zu viele Anfragen", self._fehler(429, ""))

    def test_serverfehler_macht_hoffnung(self):
        self.assertIn("späterer Versuch", self._fehler(503, ""))

    def test_begruendung_auch_ohne_huelle(self):
        """Nicht jeder Dienst packt die Begründung unter »error«."""
        self.assertIn("model not found",
                      self._fehler(404, json.dumps({"message": "model not found"})))


class WegWaehlen(unittest.TestCase):
    """Projekt sticht Datei, Datei sticht Vorgabe."""

    def _mit_konfiguration(self, angaben: dict[str, Any]):
        return mock.patch.object(konfiguration, "denker_lesen",
                                 lambda: angaben)

    def test_vorgabe_ist_das_kommando(self):
        from postkutsche import denker
        with self._mit_konfiguration({}):
            weg, _ = denker.waehlen()
        self.assertEqual(weg, denker.KOMMANDO)

    def test_datei_entscheidet(self):
        from postkutsche import denker
        with self._mit_konfiguration({"weg": "offen",
                                      "offen": {"modell": "eigenes"}}):
            weg, einstellungen = denker.waehlen()
        self.assertEqual(weg, denker.OFFEN)
        self.assertEqual(einstellungen["modell"], "eigenes")

    def test_projekt_sticht_datei(self):
        from postkutsche import denker
        projekt = mock.Mock(einstellungen={"denker": "hand"})
        with self._mit_konfiguration({"weg": "offen"}):
            weg, _ = denker.waehlen(projekt)
        self.assertEqual(weg, denker.HAND)

    def test_unbekannter_weg_faellt_auf(self):
        from postkutsche import denker
        with self._mit_konfiguration({"weg": "zauberei"}):
            with self.assertRaises(DenkerFehler) as f:
                denker.waehlen()
        self.assertIn("zauberei", str(f.exception))

    def test_schluessel_kommt_nicht_aus_der_datei(self):
        """Er wird zum Weg dazugeholt, steht aber nicht in denker.json."""
        from postkutsche import denker
        from postkutsche import zugaenge
        with self._mit_konfiguration({"weg": "anthropisch"}):
            with mock.patch.object(zugaenge, "holen", lambda k: f"schluessel-{k}"):
                _, einstellungen = denker.waehlen()
        self.assertEqual(einstellungen["schluessel"], "schluessel-denker-anthropisch")

    def test_fehlender_schluessel_ist_kein_absturz(self):
        from postkutsche import denker
        from postkutsche import zugaenge

        def nichts(kennung):
            raise zugaenge.KeinZugang(kennung)

        with self._mit_konfiguration({"weg": "offen"}):
            with mock.patch.object(zugaenge, "holen", nichts):
                _, einstellungen = denker.waehlen()
        self.assertNotIn("schluessel", einstellungen)


class DieWeicheStellt(unittest.TestCase):
    """Was gewählt ist, wird auch aufgerufen."""

    def test_schreiben_geht_zum_gewaehlten_weg(self):
        from postkutsche import denker
        with mock.patch.object(konfiguration, "denker_lesen",
                               lambda: {"weg": "hand"}):
            fassungen = denker.schreiben(INHALT, ["mastodon"])
        # »hand« ruft nichts an und stellt keine Rückfrage - daran ist es
        # eindeutig zu erkennen.
        self.assertIsNone(fassungen["mastodon"]["rueckfrage"])
        self.assertIn("Kastenfenster", fassungen["mastodon"]["text"])

    def test_meldung_passt_zum_weg(self):
        from postkutsche import denker
        self.assertIn("ollama serve", denker.nicht_da(denker.OFFEN).lower())
        self.assertIn("claude code", denker.nicht_da(denker.KOMMANDO).lower())


if __name__ == "__main__":
    unittest.main()
