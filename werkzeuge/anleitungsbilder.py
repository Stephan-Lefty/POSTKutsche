"""Die Bilder der Bedienungsanleitung – aus einer erfundenen Ablage.

Warum ein Skript und nicht ein paar Bildschirmfotos von Hand: Die Oberfläche
ändert sich, die Bilder sollen mitwandern, und niemand erinnert sich nach
einem halben Jahr, welcher Ausschnitt in welcher Größe gezeigt wurde.

**In den Bildern steht keine einzige echte Adresse.** Aufgenommen wird nicht
die eigene Ablage, sondern eine eigens angelegte unter `/tmp` mit den
Beispielprojekten aus `erstbestueckung.py` – `.example`-Adressen, erfundene
Titel, erfundene Texte. `POSTKUTSCHE_CONFIG` zeigt dabei auf einen leeren
Ordner, sonst zöge das Skript die eigenen Seiten aus
`~/.config/postkutsche/` heran und man hätte sie im Bild.

    python werkzeuge/anleitungsbilder.py

Gebraucht wird Firefox. Er nimmt die Bilder im Kopflos-Betrieb auf; ein
Fenster geht dabei nicht auf.
"""

from __future__ import annotations

import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

ZIEL = WURZEL / "docs" / "bilder"
BREITE = 1360

# Firefox schießt das Bild, sobald die Seite geladen ist – der Kalender holt
# seine Kärtchen aber erst danach per fetch, und das Fenster, das im Bild
# offen stehen soll, öffnet niemand von selbst. Beides erledigt eine
# Aufnahmeseite, die den Kalender in einem Rahmen lädt; damit sie an ihn
# herankommt, muss sie vom selben Dienst kommen und liegt deshalb für die
# Dauer der Aufnahme in `web/static/`.
AUFNAHMESEITE = "_aufnahme.html"

SEITE = """<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Aufnahme</title>
<style>
  html, body { margin: 0; padding: 0; overflow: hidden; }
  iframe { width: %(breite)spx; border: 0; display: block; }
</style>
</head>
<body>
<iframe id="rahmen" src="/"></iframe>
<!-- Das Bild antwortet erst nach ein paar Sekunden. Solange gilt die Seite
     als nicht fertig geladen, und Firefox wartet mit der Aufnahme - lange
     genug, damit der Kalender seine Kärtchen hat und das Fenster offen ist. -->
<img src="%(bremse)s" width="1" height="1" alt="">
<script>
const angaben = new URLSearchParams(location.search);
const szene = angaben.get("szene") || "kalender";
const rahmen = document.getElementById("rahmen");
rahmen.style.height = (angaben.get("hoehe") || "900") + "px";

function warten(pruefen, dann, versuche = 60) {
  const d = rahmen.contentDocument;
  if (d && pruefen(d)) return dann(d);
  if (versuche > 0) setTimeout(() => warten(pruefen, dann, versuche - 1), 100);
}

rahmen.onload = () => {
  if (szene === "kalender") return;
  if (szene === "beitrag") {
    warten((d) => d.querySelector("#raster .kaertchen"),
           (d) => d.querySelector("#raster .kaertchen").click());
    return;
  }
  if (szene === "planung") {
    warten((d) => d.querySelector("#k-projekt option"), (d) => {
      d.querySelector("#kampagne-auf").click();
      d.querySelector("#k-thema").value = "Fensterbank streichen";
      d.querySelector("#k-woche").value = "%(woche)s";
    });
    return;
  }
  if (szene === "rueckfrage") {
    // Nicht über die Reihenfolge der Kärtchen: Die haengt am Wochentag, und
    // wer einen Beitrag dazwischenschiebt, nimmt sonst das falsche Bild auf.
    warten((d) => [...d.querySelectorAll("#raster .kaertchen")]
                    .some((k) => k.textContent.includes("Kastenfenster")),
           (d) => [...d.querySelectorAll("#raster .kaertchen")]
                    .find((k) => k.textContent.includes("Kastenfenster")).click());
    return;
  }
  if (szene === "gelerntes") {
    // Die Projektliste des Fensters entsteht erst beim Öffnen - hier also
    // auf die Projektspalte warten, nicht auf »#w-projekt option«.
    warten((d) => d.querySelector("#projekte input"),
           (d) => d.querySelector("#wissen-auf").click());
  }
};
</script>
</body>
</html>
"""


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# Kategorien, die im Planungsfenster stehen sollen. Erfunden wie alles hier.
KULISSENKATEGORIEN = [
    {"id": 3, "name": "Garten im Jahreslauf", "slug": "garten", "count": 24},
    {"id": 7, "name": "Werkstatt", "slug": "werkstatt", "count": 16},
    {"id": 4, "name": "Selbst versorgen", "slug": "versorgen", "count": 11},
    {"id": 9, "name": "Werkzeugpflege", "slug": "werkzeugpflege", "count": 6},
]
KULISSENBEITRAEGE = 48     # weniger als die Summe: einer steht in zweien


class _Kulisse(http.server.BaseHTTPRequestHandler):
    """Spielt WordPress und bremst die Aufnahme.

    Zwei Aufgaben in einem Dienst, weil beide nur zur Aufnahme gebraucht
    werden:

    `/wp-json/…` beantwortet, was `quellen/wordpress.py` fragt. Damit steht im
    Planungsfenster eine echte Kategorienliste statt »nicht erreichbar« –
    abgerufen und ausgewertet wird dabei wirklich, nur der Blog dahinter ist
    erfunden. Ein Bild, das eine Fehlermeldung zeigt, wäre als Anleitung
    wertlos.

    `/warte.png` antwortet erst nach ein paar Sekunden. Firefox schießt sein
    Bild, sobald die Seite geladen ist; solange dieses Bild aussteht, gilt sie
    als unfertig, und der Kalender hat Zeit, seine Kärtchen zu holen.
    """

    LEER = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000d49444154789c6360000002000100ffff03000006"
        "00057d6f2b0000000049454e44ae426082"
    )

    def do_HEAD(self) -> None:  # noqa: N802 – von BaseHTTPRequestHandler vorgegeben
        # Die Gesamtzahl kommt bei WordPress aus dem Kopf, nicht aus dem Rumpf.
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-WP-Total", str(KULISSENBEITRAEGE))
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/warte.png"):
            time.sleep(6)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(self.LEER)))
            self.end_headers()
            self.wfile.write(self.LEER)
            return

        if "/categories" in self.path:
            rumpf = json.dumps(KULISSENKATEGORIEN).encode("utf-8")
        else:
            rumpf = b"[]"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(rumpf)))
        self.send_header("X-WP-Total", str(KULISSENBEITRAEGE))
        self.end_headers()
        self.wfile.write(rumpf)

    def log_message(self, *_: object) -> None:
        pass


def _daten_anlegen(pfad: Path, kulisse_port: int) -> None:
    """Eine Woche, wie sie nach dem Planen aussieht – alles erfunden."""
    from postkutsche import ablage as ablage_modul
    from postkutsche import erstbestueckung

    with ablage_modul.Ablage(pfad) as a:
        for beispiel in erstbestueckung.BEISPIELE:
            einstellungen = dict(beispiel.get("einstellungen") or {})
            if beispiel["kennung"] == "blog":
                # Die Kategorien im Planungsfenster sollen von der Kulisse
                # kommen und nicht von blog.example, das niemandem gehört.
                einstellungen["rest"] = f"http://127.0.0.1:{kulisse_port}/wp-json/wp/v2"
            a.projekt_anlegen(
                beispiel["kennung"], beispiel["name"], beispiel["adresse"],
                beispiel["art"], beispiel.get("farbe", "#6b7280"),
                einstellungen=einstellungen)
        projekte = {p.kennung: p for p in a.projekte()}

        heute = datetime.now(timezone.utc).replace(
            hour=6, minute=30, second=0, microsecond=0)
        montag = heute - timedelta(days=heute.weekday())

        for tag, (kennung, titel, text, netze, zustand, frage) in enumerate(WOCHE):
            projekt = projekte[kennung]
            inhalt_id, _ = a.inhalt_merken(
                projekt.id, f"demo-{tag}", titel,
                f"{projekt.adresse}/{tag}", text)
            wann = montag + timedelta(days=tag, hours=tag % 3)
            beitrag = a.beitrag_anlegen(
                projekt.id, ablage_modul.zeiten_modul().schreiben(wann),
                inhalt_id=inhalt_id, zustand=zustand)
            for stelle, (netz, fassung) in enumerate(netze.items()):
                # Die Rückfrage hängt an der ersten Fassung – so sieht das
                # Blatt aus, wenn Claude etwas nicht entscheiden konnte.
                a.fassung_setzen(beitrag, netz, fassung,
                                 rueckfrage=frage if stelle == 0 else None)

        blog = projekte["blog"]
        a.wissen_merken(blog.id, "Duzen oder siezen?",
                        "Duzen. Der Blog duzt seit je.")
        a.wissen_merken(blog.id, "Darf der Preis genannt werden?",
                        "Nur die Spanne, keine Einzelpreise.")


# Erfundene Beiträge. Sie müssen gut aussehen und dürfen nichts verraten:
# keine echten Seiten, keine echten Hersteller, keine echten Ortsnamen.
WOCHE: list[tuple[str, str, str, dict[str, str], str, str | None]] = [
    ("blog", "Zehn Quadratmeter Wildwiese",
     "Was im ersten Jahr blüht und was erst im zweiten kommt.",
     {"mastodon": "Zehn Quadratmeter reichen für den Anfang. Was im ersten "
                  "Jahr blüht, steht im neuen Beitrag – und warum der zweite "
                  "Sommer der schönere ist.",
      "facebook": "Zehn Quadratmeter Wildwiese: Im ersten Jahr blüht der "
                  "Mohn, im zweiten kommen die Stauden."},
     "freigegeben", None),
    ("shop", "Kreissäge mit Absaugung",
     "Für die Werkstatt, in der es sauber bleiben soll.",
     {"mastodon": "Wer in der Werkstatt nicht dauernd fegen will, hängt die "
                  "Absaugung gleich an die Säge."},
     "entwurf", None),
    ("blog", "Der Kompost im Winter",
     "Warum er im Januar nicht stillsteht.",
     {"mastodon": "Der Kompost ruht im Januar nicht, er arbeitet nur "
                  "langsamer. Was das für die Schichten bedeutet.",
      "instagram": "Der Kompost im Winter – was unter der Decke passiert."},
     "entwurf", None),
    ("altbau", "Kastenfenster, saniert statt ersetzt",
     "Was der Handwerker dafür braucht.",
     {"mastodon": "Ein Kastenfenster muss nicht raus, damit es dicht wird."},
     "rueckfrage",
     "Auf der Seite stehen zwei Preise – 890 € und »ab 640 €«. Welcher gilt?"),
    ("shop", "Hobelbank, zwei Meter",
     "Buche massiv, mit Vorderzange.",
     {"mastodon": "Zwei Meter Buche, Vorderzange, kein Wackeln: die "
                  "Hobelbank für Leute, die stehend arbeiten."},
     "erledigt", None),
    ("blog", "Saatgut tauschen im Februar",
     "Wo die Tauschbörsen stattfinden und was man mitbringt.",
     {"mastodon": "Im Februar wird getauscht. Was man mitbringt, damit man "
                  "nicht mit leeren Händen dasteht."},
     "entwurf", None),
]


def _dienst_starten(ablage_pfad: Path, port: int, konfig: Path):
    umgebung = dict(os.environ,
                    PYTHONPATH=str(WURZEL),
                    POSTKUTSCHE_CONFIG=str(konfig))
    return subprocess.Popen(
        [sys.executable, "-m", "postkutsche", "--ablage", str(ablage_pfad),
         "kalender", "--port", str(port), "--nicht-oeffnen"],
        cwd=str(WURZEL), env=umgebung,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _warten_bis_da(port: int, sekunden: float = 15.0) -> None:
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.3):
                return
        except OSError:
            time.sleep(0.2)
    raise SystemExit("Der Dienst kam nicht hoch.")


def _aufnehmen(port: int, szene: str, hoehe: int, datei: Path) -> None:
    adresse = (f"http://127.0.0.1:{port}/static/{AUFNAHMESEITE}"
               f"?szene={szene}&hoehe={hoehe}")
    with tempfile.TemporaryDirectory() as profil:
        subprocess.run(
            ["firefox", "--headless", "--profile", profil,
             "--window-size", f"{BREITE},{hoehe}",
             "--screenshot", str(datei), adresse],
            check=True, timeout=180,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not datei.exists():
        raise SystemExit(f"Firefox hat {datei.name} nicht geschrieben.")


# Die Höhe je Szene: Ein Kalender mit vier leeren Wochen darunter zeigt
# nichts, was die Anleitung erklären will.
SZENEN = [
    ("kalender", 620, "Der Kalender mit einer geplanten Woche"),
    ("beitrag", 900, "Ein Beitrag, aufgeschlagen"),
    ("planung", 940, "Das Fenster »Woche planen«"),
    ("rueckfrage", 760, "Ein Beitrag mit offener Rückfrage"),
    ("gelerntes", 700, "Was aus Rückfragen gelernt wurde"),
]


def main() -> None:
    if not shutil.which("firefox"):
        raise SystemExit("Firefox wird gebraucht und ist nicht da.")

    ZIEL.mkdir(parents=True, exist_ok=True)
    kulisse_port = _freier_port()
    dienst_port = _freier_port()
    woche = datetime.now().isocalendar()[1] + 1

    seite = WURZEL / "postkutsche" / "web" / "static" / AUFNAHMESEITE
    seite.write_text(SEITE % {
        "breite": BREITE, "woche": woche,
        "bremse": f"http://127.0.0.1:{kulisse_port}/warte.png",
    }, encoding="utf-8")

    kulisse = http.server.ThreadingHTTPServer(("127.0.0.1", kulisse_port), _Kulisse)
    threading.Thread(target=kulisse.serve_forever, daemon=True).start()

    with tempfile.TemporaryDirectory() as behelf:
        konfig = Path(behelf) / "konfig"     # leer – also die Beispielprojekte
        konfig.mkdir()
        datenbank = Path(behelf) / "anleitung.db"
        os.environ["POSTKUTSCHE_CONFIG"] = str(konfig)
        _daten_anlegen(datenbank, kulisse_port)

        dienst = _dienst_starten(datenbank, dienst_port, konfig)
        try:
            _warten_bis_da(dienst_port)
            for szene, hoehe, beschreibung in SZENEN:
                datei = ZIEL / f"{szene}.png"
                _aufnehmen(dienst_port, szene, hoehe, datei)
                print(f"{datei.relative_to(WURZEL)} – {beschreibung}")
        finally:
            dienst.terminate()
            dienst.wait(timeout=10)
            kulisse.shutdown()
            seite.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
