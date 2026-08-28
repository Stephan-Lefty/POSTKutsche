"""Der kleine Webdienst, auf dem der Kalender läuft.

`http.server` aus der Standardbibliothek statt Flask oder FastAPI. Für ein
Werkzeug mit einem einzigen Benutzer auf dem eigenen Rechner reicht das, und
es erspart eine Abhängigkeit, die in zwei Jahren eine andere Hauptfassung hat.

**Der Dienst hört nur auf localhost.** Er hat keine Anmeldung - wer ihn
erreicht, darf alles. Das ist vertretbar, solange er die Maschine nicht
verlässt; auf `0.0.0.0` gestellt wäre es ein offenes Scheunentor. Wer ihn
später doch von außen erreichen will, gehört hinter einen Vorschaltserver mit
Anmeldung, nicht direkt ins Netz.
"""

from __future__ import annotations

import json
import mimetypes
import webbrowser
from datetime import datetime
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .. import ablage as ablage_modul
from .. import netzwerke, zeiten

STATISCH = Path(__file__).parent / "static"


class Behandler(BaseHTTPRequestHandler):
    """Bedient die Anfragen. Eine Instanz je Anfrage, wie bei http.server üblich."""

    ablage_pfad: Path | None = None
    server_version = "POSTKutsche"
    sys_version = ""

    #: Wie weit der laufende Kampagnenlauf ist. Klassenweit, weil je Anfrage
    #: eine neue Instanz entsteht - und weil immer nur ein Lauf gleichzeitig
    #: sinnvoll ist.
    lauf: dict[str, Any] = {"aktiv": False}

    # -- Gerüst ------------------------------------------------------------

    def log_message(self, format: str, *args: Any) -> None:
        # Standardmäßig schreibt http.server jede Anfrage nach stderr. Bei
        # einem Kalender, der alle paar Sekunden nachlädt, ist das nur Lärm.
        pass

    def _senden(self, inhalt: bytes, art: str, kode: int = 200) -> None:
        self.send_response(kode)
        self.send_header("Content-Type", art)
        self.send_header("Content-Length", str(len(inhalt)))
        # Der Kalender soll beim Neuladen wirklich neu laden.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(inhalt)

    def _json(self, daten: Any, kode: int = 200) -> None:
        roh = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self._senden(roh, "application/json; charset=utf-8", kode)

    def _fehler(self, meldung: str, kode: int = 400) -> None:
        self._json({"fehler": meldung}, kode)

    def _ablage(self):
        return ablage_modul.Ablage(self.ablage_pfad)

    # -- Anfragen ----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802  (von http.server vorgegeben)
        zerlegt = urlparse(self.path)
        pfad = zerlegt.path
        frage = parse_qs(zerlegt.query)

        try:
            if pfad in ("/", "/index.html"):
                return self._datei("kalender.html")
            if pfad.startswith("/static/"):
                return self._datei(pfad[len("/static/"):])
            if pfad == "/api/projekte":
                return self._projekte()
            if pfad == "/api/netzwerke":
                return self._netzwerke()
            if pfad == "/api/beitraege":
                return self._beitraege(frage)
            if pfad.startswith("/api/beitrag/"):
                return self._beitrag(int(pfad.rsplit("/", 1)[-1]))
            if pfad == "/api/lauf":
                return self._json(Behandler.lauf)
            if pfad == "/api/kategorien":
                return self._kategorien(frage)
            if pfad.startswith("/bild/"):
                return self._bild(int(pfad.rsplit("/", 1)[-1]))
        except ValueError as fehler:
            return self._fehler(str(fehler))
        except Exception as fehler:  # noqa: BLE001
            return self._fehler(f"Unerwartet: {fehler}", 500)

        self._fehler("Nicht gefunden", 404)

    def do_POST(self) -> None:  # noqa: N802
        pfad = urlparse(self.path).path
        laenge = int(self.headers.get("Content-Length") or 0)
        try:
            rumpf = json.loads(self.rfile.read(laenge) or b"{}")
        except json.JSONDecodeError:
            return self._fehler("Der Rumpf ist kein gültiges JSON.")

        try:
            if pfad == "/api/verschieben":
                return self._verschieben(rumpf)
            if pfad == "/api/freigeben":
                return self._freigeben(rumpf)
            if pfad == "/api/bearbeiten":
                return self._bearbeiten(rumpf)
            if pfad == "/api/abgehakt":
                return self._abgehakt(rumpf)
            if pfad == "/api/bild":
                return self._bild_setzen(rumpf)
            if pfad == "/api/kampagne":
                return self._kampagne(rumpf)
        except (ValueError, KeyError) as fehler:
            return self._fehler(str(fehler))
        except ablage_modul.RueckfrageOffen as fehler:
            return self._fehler(str(fehler), 409)
        except Exception as fehler:  # noqa: BLE001
            return self._fehler(f"Unerwartet: {fehler}", 500)

        self._fehler("Nicht gefunden", 404)

    # -- Auslieferung ------------------------------------------------------

    def _datei(self, name: str) -> None:
        # Kein Ausbruch aus dem statischen Ordner: Ein Pfad wie
        # »../../../etc/passwd« darf nicht ans Ziel kommen.
        ziel = (STATISCH / name).resolve()
        if not str(ziel).startswith(str(STATISCH.resolve())) or not ziel.is_file():
            return self._fehler("Nicht gefunden", 404)
        art = mimetypes.guess_type(ziel.name)[0] or "application/octet-stream"
        if art.startswith("text/") or art.endswith(("javascript", "json")):
            art += "; charset=utf-8"
        self._senden(ziel.read_bytes(), art)

    # -- Antworten ---------------------------------------------------------

    def _projekte(self) -> None:
        with self._ablage() as a:
            self._json([
                {
                    "kennung": p.kennung, "name": p.name, "farbe": p.farbe,
                    "art": p.art, "aktiv": p.aktiv,
                    "freigabe_noetig": p.freigabe_noetig,
                    "zuletzt_geholt": p.zuletzt_geholt,
                }
                for p in a.projekte()
            ])

    def _netzwerke(self) -> None:
        self._json([
            {
                "kennung": n.kennung, "name": n.name, "kuerzel": n.kuerzel,
                "farbe": n.farbe, "zeichen_max": n.zeichen_max,
                "bild_pflicht": n.bild_pflicht,
            }
            for n in netzwerke.alle()
        ])

    def _beitraege(self, frage: dict[str, list[str]]) -> None:
        """Alles, was der Kalender für einen Monat braucht – in einem Zug.

        Bewusst mit den Fassungen zusammen: Ein Kärtchen zeigt die Kürzel der
        Netzwerke, und eine zweite Anfrage je Beitrag wären bei dreißig
        Kärtchen dreißig Anfragen.
        """
        heute = datetime.now(zeiten.ORTSZONE)
        jahr = int(frage.get("jahr", [heute.year])[0])
        monat = int(frage.get("monat", [heute.month])[0])
        if not 1 <= monat <= 12:
            raise ValueError(f"Monat {monat} gibt es nicht.")

        nur = frage.get("projekt")
        von, bis = zeiten.monatsgrenzen(jahr, monat)

        with self._ablage() as a:
            zeilen = a.beitraege_im_zeitraum(von, bis, nur)
            self._json({
                "jahr": jahr, "monat": monat,
                "beitraege": [self._kaertchen(a, z) for z in zeilen],
            })

    def _kaertchen(self, a, zeile) -> dict[str, Any]:
        fassungen = a.fassungen(int(zeile["id"]))
        return {
            "id": int(zeile["id"]),
            "geplant": zeile["geplant"],
            "geplant_ort": zeiten.nach_ortszeit(zeile["geplant"]).isoformat(),
            "zustand": zeile["zustand"],
            "projekt": zeile["projekt_kennung"],
            "projekt_name": zeile["projekt_name"],
            "farbe": zeile["projekt_farbe"],
            "titel": zeile["inhalt_titel"] or zeile["notiz"] or "(ohne Titel)",
            "adresse": zeile["inhalt_adresse"],
            "netzwerke": [f["netzwerk"] for f in fassungen],
            "rueckfragen": sum(1 for f in fassungen if f["rueckfrage"]),
            "ohne_bild": [
                f["netzwerk"] for f in fassungen
                if not f["bild_pfad"] and netzwerke.netzwerk(f["netzwerk"]).bild_pflicht
            ],
        }

    def _beitrag(self, nummer: int) -> None:
        with self._ablage() as a:
            zeile = a.beitrag(nummer)
            if zeile is None:
                return self._fehler("Diesen Beitrag gibt es nicht.", 404)
            inhalt = a.db.execute(
                "SELECT titel, adresse FROM inhalte WHERE id = ?",
                (zeile["inhalt_id"],),
            ).fetchone() if zeile["inhalt_id"] else None

            self._json({
                "id": nummer,
                "titel": inhalt["titel"] if inhalt else (zeile["notiz"] or ""),
                "quelle": inhalt["adresse"] if inhalt else None,
                "geplant": zeile["geplant"],
                "geplant_ort": zeiten.nach_ortszeit(zeile["geplant"]).isoformat(),
                "zustand": zeile["zustand"],
                "notiz": zeile["notiz"],
                "wiederholung_von": zeile["wiederholung_von"],
                "fassungen": [
                    {
                        "id": int(f["id"]),
                        "netzwerk": f["netzwerk"],
                        "text": f["text"],
                        "schlagworte": f["schlagworte"],
                        "bild_pfad": f["bild_pfad"],
                        "bild": f"/bild/{int(f['id'])}" if f["bild_pfad"] else None,
                        "versandart": f["versandart"],
                        "zustand": f["zustand"],
                        "rueckfrage": f["rueckfrage"],
                        "von_hand": bool(f["von_hand"]),
                        "fehler": f["fehler"],
                    }
                    for f in a.fassungen(nummer)
                ],
            })

    def _kategorien(self, frage: dict[str, list[str]]) -> None:
        """Die Kategorien eines Projekts – die Gliederung des Shops.

        Wird beim Anlegen einer Kampagne gebraucht: Man wählt aus, was der
        Shop ohnehin hat, statt Adressen abzutippen.
        """
        from ..quellen import seitenkarte

        kennung = frage.get("projekt", [""])[0]
        with self._ablage() as a:
            projekt = a.projekt(kennung)
        if projekt is None:
            return self._fehler(f"Kein Projekt »{kennung}«.", 404)
        if projekt.art != "seitenkarte":
            return self._fehler(
                f"Kategorien gibt es bisher nur für Seiten ohne Schnittstelle, "
                f"nicht für {projekt.art}.", 400
            )

        karte = projekt.einstellungen.get("seitenkarte")
        bereich = frage.get("bereich", [None])[0]
        kategorien = seitenkarte.kategorien(karte, bereich)

        with self._ablage() as a:
            zuletzt = a.kategorien_zuletzt(projekt.id)

        for eintrag in kategorien:
            ordner = str(eintrag["adresse"]).rsplit("/", 1)[0]
            wann = zuletzt.get(ordner)
            if wann:
                jahr, woche = zeiten.kalenderwoche(wann)
                eintrag["zuletzt"] = f"KW {woche}/{str(jahr)[2:]}"
                eintrag["zuletzt_stempel"] = wann
            else:
                eintrag["zuletzt"] = None

        self._json(kategorien)

    def _bild(self, fassung_id: int) -> None:
        """Liefert das Bild einer Fassung aus.

        Nur Dateien aus dem Bilderordner: Der Pfad kommt zwar aus unserer
        eigenen Ablage, aber ein Dienst, der beliebige Pfade ausliefert, ist
        ein Dienst, der irgendwann /etc/passwd ausliefert.
        """
        from .. import bilder

        with self._ablage() as a:
            zeile = a.db.execute(
                "SELECT bild_pfad FROM fassungen WHERE id = ?", (fassung_id,)
            ).fetchone()

        if zeile is None or not zeile["bild_pfad"]:
            return self._fehler("Zu dieser Fassung gibt es kein Bild.", 404)

        datei = Path(zeile["bild_pfad"]).resolve()
        erlaubt = bilder.ordner().resolve()
        if not str(datei).startswith(str(erlaubt)) or not datei.is_file():
            return self._fehler("Das Bild liegt nicht mehr da.", 404)

        art = mimetypes.guess_type(datei.name)[0] or "application/octet-stream"
        self._senden(datei.read_bytes(), art)

    # -- Änderungen --------------------------------------------------------

    def _verschieben(self, rumpf: dict[str, Any]) -> None:
        """Das Ziehen im Kalender landet hier."""
        nummer = int(rumpf["id"])
        # Die Oberfläche schickt Ortszeit - der Benutzer denkt in Ortszeit.
        geplant = zeiten.von_ortszeit(str(rumpf["geplant"]))
        with self._ablage() as a:
            if not a.beitrag_verschieben(nummer, geplant):
                return self._fehler("Diesen Beitrag gibt es nicht.", 404)
            self._json({"id": nummer, "geplant": geplant,
                        "lesbar": zeiten.lesbar(geplant)})

    def _freigeben(self, rumpf: dict[str, Any]) -> None:
        nummer = int(rumpf["id"])
        with self._ablage() as a:
            a.freigeben(nummer)  # wirft RueckfrageOffen, wenn Fragen offen sind
            self._json({"id": nummer, "zustand": ablage_modul.BEITRAG_FREIGEGEBEN})

    def _bearbeiten(self, rumpf: dict[str, Any]) -> None:
        with self._ablage() as a:
            a.fassung_bearbeiten(
                int(rumpf["fassung"]),
                str(rumpf["text"]),
                rumpf.get("schlagworte"),
            )
            self._json({"fassung": int(rumpf["fassung"]), "von_hand": True})

    def _kampagne(self, rumpf: dict[str, Any]) -> None:
        """Legt eine Kampagne an: Thema, Woche, Kategorien, Hersteller.

        Der Aufruf kann Minuten dauern - je Beitrag ein Claude-Aufruf. Er
        läuft trotzdem geradeaus und nicht im Hintergrund: Ein halb angelegter
        Wochenplan wäre schlimmer als eine Anzeige, die eine Weile wartet.
        """
        from .. import kampagnen
        from ..kampagnenlauf import ausfuehren

        kampagne = kampagnen.Kampagne(
            thema=str(rumpf["thema"]).strip(),
            projekt=str(rumpf["projekt"]),
            kalenderwoche=int(rumpf["kalenderwoche"]),
            jahr=int(rumpf["jahr"]),
            kategorien=[str(k) for k in rumpf.get("kategorien", [])],
            netzwerke=[str(n) for n in rumpf.get("netzwerke", ["facebook"])],
            je_tag=int(rumpf.get("je_tag", 1)),
            # Ohne Angabe die Werktage - so war es, bevor die Auswahl kam.
            tage=tuple(int(t) for t in rumpf.get("tage", [0, 1, 2, 3, 4])),
            hersteller=[str(h) for h in rumpf.get("hersteller", [])],
        )
        if Behandler.lauf.get("aktiv"):
            return self._fehler("Es läuft schon eine Planung.", 409)

        def melden_fortschritt(getan: int, gesamt: int, text: str) -> None:
            Behandler.lauf.update({
                "aktiv": True, "getan": getan, "gesamt": gesamt, "text": text,
            })

        Behandler.lauf = {"aktiv": True, "getan": 0,
                          "gesamt": kampagne.anzahl, "text": "beginnt …"}
        try:
            with self._ablage() as a:
                bericht = ausfuehren(a, kampagne, fortschritt=melden_fortschritt)
        finally:
            Behandler.lauf = {"aktiv": False}
        self._json(bericht)

    def _bild_setzen(self, rumpf: dict[str, Any]) -> None:
        """Tauscht das Bild einer Fassung aus.

        Erwartet den Inhalt als Datenadresse aus dem Browser. Der Weg über
        die Ablage statt über einen Dateipfad ist Absicht: Der Browser kennt
        den Pfad einer hochgeladenen Datei nicht, und ein Dienst, der
        beliebige Pfade entgegennimmt, liest irgendwann fremde Dateien.
        """
        import base64
        import re as _re

        from .. import bilder

        roh = str(rumpf.get("daten", ""))
        treffer = _re.match(r"data:image/(\w+);base64,(.+)$", roh, _re.DOTALL)
        if not treffer:
            raise ValueError("Das ist kein Bild.")

        inhalt = base64.b64decode(treffer.group(2))
        if len(inhalt) > bilder.GROESSE_MAX:
            raise ValueError("Das Bild ist zu groß.")

        fassung = int(rumpf["fassung"])
        ziel = bilder.ordner() / f"eigenes-{fassung}.{treffer.group(1)}"
        ziel.write_bytes(inhalt)

        # Zuschneiden, wenn Pillow da ist - sonst bleibt es, wie es kam.
        pfad = ziel
        if bilder.pillow_da():
            try:
                pfad = bilder._zuschneiden(ziel, bilder.ordner() / f"eigenes-{fassung}-4x5.jpg")
            except Exception:  # noqa: BLE001
                pass

        with self._ablage() as a:
            a.db.execute("UPDATE fassungen SET bild_pfad = ? WHERE id = ?",
                         (str(pfad), fassung))
            a.db.commit()
        self._json({"fassung": fassung, "bild": f"/bild/{fassung}"})

    def _abgehakt(self, rumpf: dict[str, Any]) -> None:
        """»Von Hand veröffentlicht« – der Weg für Facebook und Instagram."""
        with self._ablage() as a:
            a.fassung_vermerken(
                int(rumpf["fassung"]),
                ablage_modul.FASSUNG_ABGEHOLT,
                rumpf.get("adresse"),
            )
            self._json({"fassung": int(rumpf["fassung"]),
                        "zustand": ablage_modul.FASSUNG_ABGEHOLT})


def starten(
    ablage_pfad: Path | None = None,
    port: int = 8770,
    oeffnen: bool = True,
    melden=print,
) -> None:
    """Startet den Dienst und öffnet den Browser."""
    behandler = partial(Behandler)
    Behandler.ablage_pfad = ablage_pfad

    # Ausdrücklich 127.0.0.1 und nicht 0.0.0.0: Der Dienst hat keine
    # Anmeldung. Im WLAN eines Hotels wäre er sonst für alle offen.
    server = ThreadingHTTPServer(("127.0.0.1", port), behandler)
    adresse = f"http://127.0.0.1:{port}/"

    melden(f"Kalender läuft auf {adresse}")
    melden("Beenden mit Strg+C.")
    if oeffnen:
        webbrowser.open(adresse)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        melden("\nKalender beendet.")
    finally:
        server.server_close()
