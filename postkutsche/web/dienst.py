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
import time
import webbrowser
from datetime import datetime, timedelta
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .. import ablage as ablage_modul
from .. import netzwerke, zeiten

STATISCH = Path(__file__).parent / "static"


#: Wie lange eine Bestandsaufnahme gilt. Ein Shop stellt sein Sortiment nicht
#: stündlich um; zwölf Stunden heißt: einmal am Morgen wartet man zwanzig
#: Sekunden, den Rest des Tages nicht mehr. Ohne diesen Zwischenspeicher
#: kostete jedes Öffnen des Planungsfensters 130 Abrufe.
BESTAND_STUNDEN = 12


def kategorien_des_projekts(projekt: Any,
                            bereich: str | None = None,
                            melden=None,
                            speicher: Path | None = None,
                            stunden: float = BESTAND_STUNDEN,
                            ) -> tuple[list[dict[str, Any]], str | None]:
    """Die Gliederung eines Shops – aus der Navigation oder von Hand genannt.

    Gibt die Kategorien und einen Hinweis zurück; der Hinweis ist None, wenn
    es nichts zu sagen gibt.

    **Von Hand genannt** wird bei Shopware. Dort liegen die Produkte flach,
    nicht unterhalb ihrer Kategorie, und die Seitenkarte verrät nur, dass es
    eine Kategorie gibt, nicht, was darin liegt. Diese Vorgaben kommen vom
    Benutzer und werden nicht nachgeprüft: Er hat nachgesehen, wir nicht.

    **Sonst zählt, was die Seite selbst verlinkt.** Die Seitenkarte war für
    diesen Zweck die schlechtere Quelle – sie verschwieg 57 Kategorien, die es
    gibt, und führte 115, die es nicht mehr gibt. Gelesen wird deshalb die
    Navigation; die Karte bleibt nur als Rückfall, wenn die Seite schweigt.
    Für die Produktadressen selbst ist sie weiter zuständig, es geht allein um
    die Liste im Planungsfenster.

    **Die Bereiche stehen nicht in der Liste.** »Türen Shop« ist eine
    Übersichtsseite, die nur auf Unterkategorien verweist; sie meldete 1646
    Produkte und lieferte keines. Die Bereiche sind das Auswahlfeld oben, nicht
    die Liste unten.

    Steht hier statt im Behandler, damit es ohne laufenden Webdienst zu
    prüfen ist.
    """
    from ..quellen import seitenkarte

    vorgaben = projekt.einstellungen.get("kategorien")
    if vorgaben:
        kategorien = seitenkarte.vorgegebene_kategorien(vorgaben)
        if bereich:
            kategorien = [k for k in kategorien
                          if str(k["pfad"]).startswith(bereich)]
        return kategorien, None

    kategorien, hinweis = _bestand(projekt, melden, speicher, stunden)

    # Bereiche heraus, dann erst der gewählte Bereich - sonst filterte man
    # eine Liste, in der die Übersichtsseiten noch stehen.
    kategorien = [k for k in kategorien if not _ist_uebersicht(k)]
    if bereich:
        kategorien = [k for k in kategorien
                      if str(k["pfad"]).startswith(bereich)]
    return kategorien, hinweis


def _bestand(projekt: Any, melden, speicher: Path | None,
             stunden: float) -> tuple[list[dict[str, Any]], str | None]:
    """Der Bestand, aus dem Zwischenspeicher oder frisch von der Seite."""
    from ..quellen import seitenkarte

    datei = speicher if speicher is not None else _bestandsdatei(projekt.kennung)
    gemerkt = _bestand_lesen(datei, stunden)
    if gemerkt is not None:
        return gemerkt, None

    startseite = projekt.einstellungen.get("navigation") or projekt.adresse
    angefangen = time.monotonic()
    try:
        kategorien, ausgelassen = seitenkarte.navigation(startseite)
    except seitenkarte.AbrufFehler as schiefgegangen:
        # Die Seite schweigt. Dann lieber die veraltete Karte als ein leeres
        # Formular - aber mit der Ansage, dass die Liste nicht stimmen muss.
        karte = (projekt.einstellungen.get("seitenkarte")
                 or f"{projekt.adresse.rstrip('/')}/sitemap.xml")
        hinweis = (
            f"{startseite} war nicht zu lesen ({schiefgegangen}). Die Liste "
            f"kommt aus der Seitenkarte und kann Kategorien enthalten, die es "
            f"nicht mehr gibt."
        )
        (melden or print)(hinweis)
        return seitenkarte.kategorien(karte), hinweis

    dauer = time.monotonic() - angefangen
    _bestand_schreiben(datei, kategorien)

    # Gezählt wird, was nachher wirklich zur Auswahl steht - die Bereiche
    # fallen gleich heraus. Eine Zahl im Hinweis, die nicht zur Liste
    # darunter passt, ist schlimmer als gar keine.
    angeboten = sum(1 for k in kategorien if not _ist_uebersicht(k))
    hinweis = (
        f"Bestand neu erhoben: {angeboten} Kategorien aus der Navigation "
        f"von {startseite}, {dauer:.0f} Sekunden. Gilt {stunden:.0f} Stunden, "
        f"bis dahin geht das Formular sofort auf."
    )
    if ausgelassen:
        hinweis += (f" Ausgelassen: {len(ausgelassen)} Konfiguratoren und "
                    f"Abholgebiete – dahinter steht keine Ware.")
    # Auch ins Protokoll: Wer im Dienst nachliest, warum das Formular einmal
    # lange brauchte, findet es dort und nicht nur in einem Fenster, das
    # längst wieder zu ist.
    (melden or print)(hinweis)
    return kategorien, hinweis


def _ist_uebersicht(eintrag: dict[str, Any]) -> bool:
    """Ob der Eintrag ein Bereich ist und keine Kategorie.

    Ein Bereich liegt eine Pfadebene tief (»shop-tueren«) und verweist nur
    auf das, was unter ihm hängt. »Türen Shop« meldete 1646 Produkte und
    lieferte keines.
    """
    return int(eintrag.get("tiefe") or 0) <= 1


def _bestandsdatei(kennung: str) -> Path:
    """Wo die Bestandsaufnahme eines Projekts liegt.

    Neben der Ablage, aber nicht darin: Das hier ist weggeworfenes Wissen, das
    sich jederzeit neu holen lässt. In der Datenbank hätte es eine Tabelle
    gebraucht, eine Schemafassung und eine Wanderung – für etwas, das nach
    zwölf Stunden ungültig ist.
    """
    return ablage_modul.standard_pfad().parent / "bestand" / f"{kennung}.json"


def _bestand_lesen(datei: Path, stunden: float) -> list[dict[str, Any]] | None:
    """Die gemerkte Bestandsaufnahme, falls sie noch frisch ist.

    None heißt »neu holen«. Jeder Zweifel führt hierher: fehlende Datei,
    kaputtes JSON, fehlender Zeitstempel. Ein Zwischenspeicher darf nie der
    Grund sein, warum etwas nicht geht.
    """
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    gespeichert = str(daten.get("gespeichert") or "")
    kategorien = daten.get("kategorien")
    if not gespeichert or not isinstance(kategorien, list):
        return None

    try:
        alter = zeiten.lesen(zeiten.jetzt_utc()) - zeiten.lesen(gespeichert)
    except ValueError:
        return None
    # Auch ein Stempel aus der Zukunft gilt nicht: Nach einer verstellten Uhr
    # bliebe die Liste sonst für immer stehen.
    if alter < timedelta(0) or alter > timedelta(hours=stunden):
        return None
    return kategorien


def _bestand_schreiben(datei: Path, kategorien: list[dict[str, Any]]) -> None:
    try:
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(
            json.dumps({"gespeichert": zeiten.jetzt_utc(),
                        "kategorien": kategorien}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # Ein Zwischenspeicher, der sich nicht schreiben lässt, macht den
        # nächsten Aufruf langsam. Das Formular scheitern zu lassen wäre
        # schlimmer.
        pass


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
            if pfad == "/api/projektfarben":
                from .. import farben as farbpalette

                return self._json([
                    {"farbe": f, "ton": round(farbpalette.farbton(f))}
                    for f in farbpalette.PROJEKTFARBEN
                ])
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
            if pfad == "/api/wissen":
                return self._wissen(frage)
            if pfad.startswith("/bild/"):
                return self._bild(int(pfad.rsplit("/", 1)[-1]),
                                  int(frage.get("nr", ["1"])[0]))
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
            if pfad == "/api/entfernen":
                return self._entfernen(rumpf)
            if pfad == "/api/bild":
                return self._bild_setzen(rumpf)
            if pfad == "/api/bild/weg":
                return self._bild_weg(rumpf)
            if pfad == "/api/ablegen":
                return self._ablegen(rumpf)
            if pfad == "/api/ordner":
                return self._ordner_zeigen(rumpf)
            if pfad == "/api/projektfarbe":
                return self._projektfarbe(rumpf)
            if pfad == "/api/antwort":
                return self._antwort(rumpf)
            if pfad == "/api/wissen/streichen":
                return self._wissen_streichen(rumpf)
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
        nur = frage.get("projekt")

        # Zwei Wege: ein Zeitraum in Ortszeit (»2026-08-31« bis »2026-10-12«)
        # oder ein Monat. Der Zeitraum ist der neue Weg für die rollende
        # Wochenansicht; der Monat bleibt, weil die Kommandozeile ihn nutzt.
        if frage.get("von") and frage.get("bis"):
            von = zeiten.von_ortszeit(frage["von"][0])
            bis = zeiten.von_ortszeit(frage["bis"][0])
            kopf = {"von": frage["von"][0], "bis": frage["bis"][0]}
        else:
            heute = datetime.now(zeiten.ORTSZONE)
            jahr = int(frage.get("jahr", [heute.year])[0])
            monat = int(frage.get("monat", [heute.month])[0])
            if not 1 <= monat <= 12:
                raise ValueError(f"Monat {monat} gibt es nicht.")
            von, bis = zeiten.monatsgrenzen(jahr, monat)
            kopf = {"jahr": jahr, "monat": monat}

        with self._ablage() as a:
            zeilen = a.beitraege_im_zeitraum(von, bis, nur)
            self._json({
                **kopf,
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
                        # Das zweite Bild als eigene Felder und nicht als
                        # Liste: Eine ältere Oberfläche liest »bild« weiter
                        # und zeigt eben nur das erste, statt zu scheitern.
                        "bild_pfad2": f["bild_pfad2"],
                        "bild2": (f"/bild/{int(f['id'])}?nr=2"
                                  if f["bild_pfad2"] else None),
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

        kategorien, hinweis = kategorien_des_projekts(
            projekt, frage.get("bereich", [None])[0])

        with self._ablage() as a:
            zuletzt = a.kategorien_zuletzt(projekt.id)

        # »Zuletzt bespielt« liest sich aus dem Pfad der beworbenen Produkte.
        # Bei Shopware bleibt es leer, und das ist richtig so: Dort liegt das
        # Produkt nicht im Pfad seiner Kategorie, also lässt sich aus der
        # Adresse nicht ablesen, wozu es gehörte. Lieber nichts anzeigen als
        # eine Woche behaupten, die nicht stimmt.
        for eintrag in kategorien:
            ordner = str(eintrag["adresse"]).rstrip("/").rsplit("/", 1)[0]
            wann = zuletzt.get(ordner)
            if wann:
                jahr, woche = zeiten.kalenderwoche(wann)
                eintrag["zuletzt"] = f"KW {woche}/{str(jahr)[2:]}"
                eintrag["zuletzt_stempel"] = wann
            else:
                eintrag["zuletzt"] = None

        # Ein Objekt und keine Liste, damit der Hinweis mitkommt. Wer den
        # Kalender im Browser stehen hat, muss nach einer Änderung hier hart
        # neu laden - eine alte kalender.js bekäme sonst eine Liste ohne
        # Einträge.
        self._json({"kategorien": kategorien, "hinweis": hinweis})

    def _bild(self, fassung_id: int, nummer: int = 1) -> None:
        """Liefert das Bild einer Fassung aus.

        Nur Dateien aus dem Bilderordner: Der Pfad kommt zwar aus unserer
        eigenen Ablage, aber ein Dienst, der beliebige Pfade ausliefert, ist
        ein Dienst, der irgendwann /etc/passwd ausliefert.
        """
        from .. import bilder

        with self._ablage() as a:
            zeile = a.db.execute(
                "SELECT bild_pfad, bild_pfad2 FROM fassungen WHERE id = ?",
                (fassung_id,)
            ).fetchone()

        # »?nr=2« holt das zweite Bild. Als Frage und nicht als eigener Pfad,
        # damit eine ältere Oberfläche ohne diesen Zusatz weiter das erste
        # bekommt - statische Dateien wirken beim Benutzer sofort, der
        # Dienst erst nach seinem Neustart.
        spalte = "bild_pfad2" if nummer == 2 else "bild_pfad"
        if zeile is None or not zeile[spalte]:
            return self._fehler("Zu dieser Fassung gibt es kein Bild.", 404)

        datei = Path(zeile[spalte]).resolve()
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

    def _antwort(self, rumpf: dict[str, Any]) -> None:
        """Beantwortet eine Rückfrage und lässt den Text nachbessern.

        Die Schleife, die POSTKutsche besser macht statt nur schneller:
        Claude fragt, du antwortest, der Text wird genauer. Ohne sie bleibt
        nur, den Text von Hand zu ergänzen - dann lernt niemand etwas.
        """
        from .. import denker

        fassung_id = int(rumpf["fassung"])
        antwort = str(rumpf.get("antwort", "")).strip()
        if not antwort:
            raise ValueError("Ohne Antwort lässt sich nichts nachbessern.")
        # Der Schalter aus der Oberfläche. Fehlt er - etwa weil eine ältere
        # Seite im Browser steht -, gilt die Antwort nur für dieses Produkt.
        # Das ist die harmlosere Annahme: Produktwissen geht niemanden sonst
        # etwas an, eine falsch verallgemeinerte Regel dagegen steht bei
        # jedem künftigen Entwurf im Weg.
        allgemein = bool(rumpf.get("allgemein"))

        with self._ablage() as a:
            zeile = a.db.execute(
                """SELECT f.*, b.inhalt_id, b.projekt_id FROM fassungen f
                   JOIN beitraege b ON b.id = f.beitrag_id
                   WHERE f.id = ?""", (fassung_id,)
            ).fetchone()
            if zeile is None:
                return self._fehler("Diese Fassung gibt es nicht.", 404)
            if not zeile["rueckfrage"]:
                return self._fehler("Zu dieser Fassung ist keine Frage offen.")

            inhalt = a.db.execute(
                "SELECT titel, text, adresse, bild_adresse FROM inhalte WHERE id = ?",
                (zeile["inhalt_id"],),
            ).fetchone() if zeile["inhalt_id"] else None

            quelle = {
                "titel": inhalt["titel"] if inhalt else "",
                "text": inhalt["text"] if inhalt else "",
                "adresse": inhalt["adresse"] if inhalt else "",
                "bild_adresse": inhalt["bild_adresse"] if inhalt else None,
                "kategorien": [],
            }

            neu = denker.nachbessern(
                quelle, zeile["netzwerk"], zeile["text"],
                zeile["rueckfrage"], antwort,
            )

            # Die Antwort wird an den Beitrag geschrieben. Sie gehört zur
            # Geschichte: Wer später liest, warum dort etwas Bestimmtes steht,
            # findet Frage und Antwort beieinander.
            beitrag = a.beitrag(int(zeile["beitrag_id"]))
            vermerk = (beitrag["notiz"] + "\n\n" if beitrag["notiz"] else "")
            vermerk += f"F: {zeile['rueckfrage']}\nA: {antwort}"
            a.db.execute("UPDATE beitraege SET notiz = ? WHERE id = ?",
                         (vermerk, int(zeile["beitrag_id"])))

            a.db.execute(
                """UPDATE fassungen SET text = ?, schlagworte = ?,
                       rueckfrage = ?, von_hand = 0 WHERE id = ?""",
                (neu["text"], neu["schlagworte"], neu["rueckfrage"], fassung_id),
            )
            a.db.commit()
            a._beitrag_nachfuehren(int(zeile["beitrag_id"]))

            # Und dasselbe noch einmal, damit es beim nächsten Mal nicht
            # wieder gefragt wird. Der Vermerk oben gehört zum Beitrag und
            # erklärt ihn; hier geht es um das Projekt.
            adresse = "" if allgemein else str(quelle["adresse"] or "")
            # Ein Beitrag ohne Inhalt hat keine Adresse. Die Antwort dann als
            # allgemein zu verbuchen wäre eine Unterstellung - lieber gar
            # nicht merken als etwas zur Regel machen, was keine sein sollte.
            gemerkt = (a.wissen_merken(int(zeile["projekt_id"]),
                                       str(zeile["rueckfrage"]), antwort,
                                       adresse=adresse)
                       if allgemein or adresse else None)

        self._json({
            "fassung": fassung_id,
            "text": neu["text"],
            "schlagworte": neu["schlagworte"],
            # Claude darf erneut fragen - lieber zweimal fragen als einmal raten.
            "rueckfrage": neu["rueckfrage"],
            "gemerkt": bool(gemerkt),
            "allgemein": allgemein,
        })

    def _wissen(self, frage: dict[str, list[str]]) -> None:
        """Was ein Projekt aus Rückfragen gelernt hat – zum Durchsehen.

        **Eine Sammlung, die nur wächst, wird zur Last.** Nach einem halben
        Jahr steht dort etwas, das nicht mehr stimmt – ein Lieferant hat
        gewechselt, eine Norm ist abgelöst –, und wenn niemand es findet,
        schreibt Claude es weiter in jeden Beitrag. Deshalb ist diese Liste
        genauso wichtig wie das Sammeln selbst.

        Zurück kommt alles, nicht nur die zwölf, die in eine Anweisung gehen:
        Aufräumen kann nur, wer alles sieht.
        """
        kennung = frage.get("projekt", [""])[0]
        with self._ablage() as a:
            projekt = a.projekt(kennung)
            if projekt is None:
                return self._fehler(f"Kein Projekt »{kennung}«.", 404)
            zeilen = a.wissen_alles(projekt.id)
            # Welche Einträge wirklich in jede Anweisung gehen: die
            # allgemeinen, und davon nur so viele, wie die Grenze zulässt.
            # Wer zwanzig gesammelt hat, soll sehen, dass acht davon
            # stillschweigend nicht mitgehen.
            in_anweisung = {int(z["id"]) for z in a.wissen(projekt.id)}

        self._json({
            "projekt": projekt.kennung,
            "grenze": ablage_modul.Ablage.WISSENSGRENZE,
            "eintraege": [
                {
                    "id": int(z["id"]),
                    "frage": z["frage"],
                    "antwort": z["antwort"],
                    "adresse": z["adresse"],
                    # Ohne Adresse gilt es für das ganze Projekt und geht bei
                    # jedem Entwurf mit. Das ist der Unterschied, der zählt.
                    "allgemein": not z["adresse"],
                    "angelegt": z["angelegt"],
                    "angelegt_ort": zeiten.nach_ortszeit(z["angelegt"]).isoformat(),
                    "in_anweisung": int(z["id"]) in in_anweisung,
                }
                for z in zeilen
            ],
        })

    def _wissen_streichen(self, rumpf: dict[str, Any]) -> None:
        nummer = int(rumpf["wissen"])
        with self._ablage() as a:
            if not a.wissen_streichen(nummer):
                return self._fehler("Diesen Eintrag gibt es nicht.", 404)
        self._json({"gestrichen": nummer})

    def _projektfarbe(self, rumpf: dict[str, Any]) -> None:
        """Ändert die Farbe eines Projekts.

        Geprüft wird nur die Form, nicht die Palette: Wer eine eigene Farbe
        will, soll sie nehmen dürfen. Die Palette ist ein Vorschlag, keine
        Vorschrift - sie hält Abstand zu den Netzwerkfarben, aber das muss
        niemand hinnehmen, der es besser weiß.
        """
        import re as _re

        farbe = str(rumpf.get("farbe", "")).strip().lower()
        if not _re.fullmatch(r"#[0-9a-f]{6}", farbe):
            raise ValueError(f"»{farbe}« ist keine Farbe im Format #rrggbb.")

        kennung = str(rumpf["projekt"])
        with self._ablage() as a:
            projekt = a.projekt(kennung)
            if projekt is None:
                return self._fehler(f"Kein Projekt »{kennung}«.", 404)
            a.db.execute("UPDATE projekte SET farbe = ? WHERE id = ?",
                         (farbe, projekt.id))
            a.db.commit()

        from .. import farben as farbpalette
        from .. import netzwerke as netze

        # Warnen, nicht verbieten: Wer eine Farbe nimmt, die aussieht wie eine
        # Netzwerkmarke, soll das erfahren - entscheiden darf er trotzdem.
        naechstes = min(netze.alle(),
                        key=lambda n: farbpalette.tonabstand(farbe, n.farbe))
        warnung = None
        if farbpalette.tonabstand(farbe, naechstes.farbe) < 35:
            warnung = (f"Diese Farbe liegt nah an {naechstes.name} – "
                       "im Kalender könnte man sie verwechseln.")

        self._json({"projekt": kennung, "farbe": farbe, "warnung": warnung})

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
        bestaetigt = bool(rumpf.get("bestaetigt"))
        umgang = str(rumpf.get("wiederholungen", "fragen"))
        # Immer neu formulieren, ohne Wahlmöglichkeit: Es gibt keinen Fall,
        # in dem wortgleich besser wäre. Facebook und Instagram halten solche
        # Beiträge zurück, und bei Mastodon liest sie niemand zweimal.
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
                bericht = ausfuehren(a, kampagne, fortschritt=melden_fortschritt,
                                     bestaetigt=bestaetigt,
                                     wiederholungen=umgang)
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
        # Ohne Angabe das erste Bild: Eine ältere Oberfläche kennt die Nummer
        # nicht und meint immer das erste.
        nummer = 2 if int(rumpf.get("nummer") or 1) == 2 else 1
        marke = "" if nummer == 1 else "-2"

        ziel = bilder.ordner() / f"eigenes-{fassung}{marke}.{treffer.group(1)}"
        ziel.write_bytes(inhalt)

        # Zuschneiden, wenn Pillow da ist - sonst bleibt es, wie es kam. Der
        # Zuschnitt gilt für beide Bilder; ein Beitrag mit einem 4:5- und
        # einem Querformatbild sieht im Karussell schief aus.
        pfad = ziel
        if bilder.pillow_da():
            try:
                pfad = bilder._zuschneiden(
                    ziel, bilder.ordner() / f"eigenes-{fassung}{marke}-4x5.jpg")
            except Exception:  # noqa: BLE001
                pass

        spalte = "bild_pfad2" if nummer == 2 else "bild_pfad"
        with self._ablage() as a:
            a.db.execute(f"UPDATE fassungen SET {spalte} = ? WHERE id = ?",
                         (str(pfad), fassung))
            a.db.commit()
        self._json({"fassung": fassung, "nummer": nummer,
                    "bild": f"/bild/{fassung}?nr={nummer}"})

    def _bild_weg(self, rumpf: dict[str, Any]) -> None:
        """Nimmt ein Bild von der Fassung.

        Betrifft nur den Eintrag, nicht die Datei: Dieselbe Datei kann an
        einem anderen Beitrag hängen, und der Bilderordner wird ohnehin
        aufgeräumt, nicht einzeln geleert.
        """
        fassung = int(rumpf["fassung"])
        nummer = 2 if int(rumpf.get("nummer") or 1) == 2 else 1
        spalte = "bild_pfad2" if nummer == 2 else "bild_pfad"
        with self._ablage() as a:
            a.db.execute(f"UPDATE fassungen SET {spalte} = NULL WHERE id = ?",
                         (fassung,))
            a.db.commit()
        self._json({"fassung": fassung, "nummer": nummer})

    def _ablegen(self, rumpf: dict[str, Any]) -> None:
        """Legt die Bilder einer Fassung unter »Dokumente« ab.

        **Warum der Dienst das tut und nicht der Browser.** Wohin ein
        Download geht, entscheidet der Browser – meist »Downloads«, und eine
        Webseite kann daran nichts ändern; ein `download`-Attribut setzt nur
        den Dateinamen. Der Dienst läuft aber auf demselben Rechner und kann
        die Datei hinlegen, wo sie hingehört. Der Knopf zum Herunterladen
        bleibt daneben stehen: Er ist der Weg, das Bild in Facebook zu
        bekommen.
        """
        from .. import bilder

        fassung_id = int(rumpf["fassung"])
        with self._ablage() as a:
            zeile = a.db.execute(
                """SELECT f.bild_pfad, f.bild_pfad2, f.netzwerk, b.geplant,
                          p.kennung AS projekt, i.titel
                   FROM fassungen f
                   JOIN beitraege b ON b.id = f.beitrag_id
                   JOIN projekte p ON p.id = b.projekt_id
                   LEFT JOIN inhalte i ON i.id = b.inhalt_id
                   WHERE f.id = ?""", (fassung_id,)
            ).fetchone()

        if zeile is None:
            return self._fehler("Diese Fassung gibt es nicht.", 404)

        titel = zeile["titel"] or zeile["projekt"]
        gelegt: list[str] = []
        for nummer, spalte in ((1, "bild_pfad"), (2, "bild_pfad2")):
            if not zeile[spalte]:
                continue
            try:
                gelegt.append(str(bilder.ablegen(
                    zeile[spalte], zeile["projekt"], zeile["geplant"],
                    zeile["netzwerk"], titel, fassung_id, nummer)))
            except bilder.BildFehler as fehler:
                return self._fehler(str(fehler))

        if not gelegt:
            return self._fehler("Zu dieser Fassung gibt es kein Bild.", 404)

        self._json({
            "fassung": fassung_id,
            "dateien": gelegt,
            "ordner": str(Path(gelegt[0]).parent),
        })

    def _ordner_zeigen(self, rumpf: dict[str, Any]) -> None:
        """Öffnet den Ablageordner in der Dateiverwaltung.

        Ohne Parameter, und das ist der Punkt: Der Pfad kommt aus dem
        Programm. Ein Dienst, der einen Pfad aus der Anfrage öffnet, öffnet
        irgendwann etwas anderes.
        """
        from .. import bilder

        ziel = bilder.dokumentenordner() / bilder.SAMMELORDNER
        ziel.mkdir(parents=True, exist_ok=True)
        self._json({"ordner": str(ziel), "geoeffnet": bilder.ordner_zeigen(ziel)})

    def _entfernen(self, rumpf: dict[str, Any]) -> None:
        """Löscht einen Beitrag, der noch nicht erschienen ist.

        Was draußen war, weist die Ablage ab - hier wird das nicht noch
        einmal geprüft, sondern die Begründung durchgereicht. Zwei Prüfungen
        derselben Regel weichen irgendwann voneinander ab.
        """
        with self._ablage() as a:
            a.beitrag_entfernen(int(rumpf["id"]))
            self._json({"entfernt": int(rumpf["id"])})

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
