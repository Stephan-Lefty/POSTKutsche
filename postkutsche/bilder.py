"""Bilder holen und fürs Handy zuschneiden.

**Warum 4:5 und nicht quadratisch.** Auf dem Telefon ist der Bildschirm hoch,
nicht breit. Ein 4:5-Bild füllt ihn fast; ein quadratisches lässt oben und
unten Luft, ein Querformat wird zu einem Streifen in der Mitte. Alle vier
Netzwerke zeigen 4:5 vollständig an, mehr Höhe beschneidet Instagram.

**Warum beschnitten und nicht gestaucht.** Ein verzerrtes Bild fällt sofort
auf und sieht nach Pfusch aus. Beschnitten wird aus der Mitte - das trifft
bei Produktfotos fast immer, bei Landschaftsbildern manchmal nicht. Wer es
genauer will, tauscht die Datei aus; der Pfad steht in der Ablage.

**Ohne Pillow geht es auch**, dann bleibt das Bild wie es ist. Es wird
trotzdem heruntergeladen - Mastodon braucht eine Datei, keine Adresse.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from .quellen.abrufen import AbrufFehler, holen

#: Das Zielformat. 1080 Pixel Breite ist, was die Netzwerke ohnehin
#: herunterrechnen; mehr kostet Übertragung ohne sichtbaren Gewinn.
BREITE, HOEHE = 1080, 1350

#: Grenze fürs Herunterladen. Ein Produktfoto hat selten mehr als ein paar
#: Megabyte; alles darüber ist ein Versehen oder ein Rohbild.
GROESSE_MAX = 25 * 1024 * 1024


class BildFehler(Exception):
    """Das Bild ließ sich nicht beschaffen. Die Meldung ist für Menschen."""


def ordner() -> Path:
    """Wo die zugeschnittenen Bilder liegen."""
    from .ablage import standard_pfad

    ziel = standard_pfad().parent / "bilder"
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


#: Der Ordner unter »Dokumente«, in dem die abgelegten Bilder landen.
SAMMELORDNER = "POSTKutsche"


def dokumentenordner() -> Path:
    """Wo der Benutzer seine Dokumente vermutet – gefragt, nicht geraten.

    **Der Ordner heißt nicht überall gleich.** Auf einem deutschen System
    »Dokumente«, auf einem englischen »Documents«, und wer ihn verschoben hat,
    hat ihn woanders. Ein Werkzeug, das Dateien an einem Ort ablegt, den der
    Benutzer nicht findet, ist schlimmer als eines, das gar nichts ablegt.

    Vier Anläufe, vom Verlässlichsten zum Notbehelf:

    1. `POSTKUTSCHE_DOKUMENTE` – für Tests und für alle, die es anders wollen.
    2. `~/.config/user-dirs.dirs`, die Datei, aus der auch die
       Dateiverwaltung liest. Reines Textlesen, kein fremdes Programm.
    3. `xdg-user-dir DOCUMENTS`, falls die Datei fehlt oder nichts hergibt.
    4. Ein vorhandener Ordner »Dokumente« oder »Documents« im Heimat-
       verzeichnis. Gibt es keinen, wird »Dokumente« angelegt – POSTKutsche
       spricht Deutsch, also ist das die bessere Wette als »Documents«.
    """
    aus_umgebung = os.environ.get("POSTKUTSCHE_DOKUMENTE")
    if aus_umgebung:
        return Path(aus_umgebung).expanduser()

    return (_aus_user_dirs() or _aus_xdg_werkzeug() or _vorhandener_ordner()
            or (Path.home() / "Dokumente"))


def _aus_user_dirs() -> Path | None:
    """Liest XDG_DOCUMENTS_DIR aus ~/.config/user-dirs.dirs."""
    datei = Path.home() / ".config" / "user-dirs.dirs"
    try:
        roh = datei.read_text(encoding="utf-8")
    except OSError:
        return None
    treffer = re.search(r'^\s*XDG_DOCUMENTS_DIR\s*=\s*"?([^"\n]+)"?',
                        roh, re.MULTILINE)
    if not treffer:
        return None
    # In der Datei steht »$HOME/Dokumente«, nicht der ausgeschriebene Pfad.
    pfad = treffer.group(1).replace("$HOME", str(Path.home())).strip()
    return Path(pfad) if pfad else None


def _aus_xdg_werkzeug() -> Path | None:
    try:
        lauf = subprocess.run(["xdg-user-dir", "DOCUMENTS"],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        # Kein xdg-user-dir da (macOS, Windows, karge Systeme). Kein Fehler,
        # nur ein Anlauf weniger.
        return None
    ziel = lauf.stdout.strip()
    # Gibt es nichts zu sagen, gibt das Werkzeug das Heimatverzeichnis
    # zurück - und das ist kein Dokumentenordner.
    if lauf.returncode or not ziel or Path(ziel) == Path.home():
        return None
    return Path(ziel)


def _vorhandener_ordner() -> Path | None:
    for name in ("Dokumente", "Documents"):
        pfad = Path.home() / name
        if pfad.is_dir():
            return pfad
    return None


def ablageordner(projekt: str, geplant: str) -> Path:
    """Wohin ein Bild gehört: ein Ordner je Kalenderwoche, darin je Projekt.

    **Die Woche steht vorn, weil danach aufgeräumt wird.** Der Benutzer will
    »die Bilder der KW 36 löschen«, und das soll ein Handgriff sein und nicht
    ein Gang durch fünf Projektordner. »2026-KW36« statt »KW36-2026«, damit
    die Ordner in der Dateiverwaltung von selbst in der richtigen Reihenfolge
    stehen.
    """
    from . import zeiten

    jahr, woche = zeiten.kalenderwoche(geplant)
    ziel = (dokumentenordner() / SAMMELORDNER / f"{jahr}-KW{woche:02d}"
            / _dateiname_tauglich(projekt))
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


def ablegen(quelle: Path | str, projekt: str, geplant: str, netzwerk: str,
            titel: str, fassung: int, nummer: int = 1) -> Path:
    """Legt ein Bild dort ab, wo der Benutzer es wiederfindet.

    Der Browser entscheidet beim Herunterladen selbst, wohin – meist in
    »Downloads«, und eine Webseite kann das nicht bestimmen. Also legt der
    Dienst die Datei selbst ab; er läuft ohnehin auf demselben Rechner.

    **Der Name muss den Beitrag verraten, ohne die Datenbank.** Datum,
    Netzwerk, Titel, dazu die Nummer der Fassung, damit zwei Beiträge
    desselben Tages mit ähnlichem Titel sich nicht überschreiben.
    """
    quelle = Path(quelle)
    if not quelle.is_file():
        raise BildFehler(f"Das Bild gibt es nicht: {quelle}")

    tag = str(geplant)[:10]
    name = (f"{tag}_{_dateiname_tauglich(netzwerk)}"
            f"_{_dateiname_tauglich(titel)[:60]}"
            f"_f{int(fassung)}-{int(nummer)}{quelle.suffix.lower() or '.jpg'}")
    ziel = ablageordner(projekt, geplant) / name
    try:
        shutil.copyfile(quelle, ziel)
    except OSError as fehler:
        raise BildFehler(f"Das Bild ließ sich nicht ablegen: {fehler}") from fehler
    return ziel


def ordner_zeigen(pfad: Path | str) -> bool:
    """Öffnet einen Ordner in der Dateiverwaltung. Sagt, ob es geklappt hat.

    Eine Webseite kann das nicht, der Dienst schon – er läuft auf demselben
    Rechner. Der Pfad kommt aus dem Programm und nicht aus der Anfrage; hier
    ist nichts einzuschleusen.
    """
    for befehl in ("xdg-open", "open", "explorer"):
        try:
            subprocess.Popen([befehl, str(pfad)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def _dateiname_tauglich(text: str) -> str:
    """Aus »T30-2 Brandschutztür« wird »T30-2-Brandschutztuer«.

    Umlaute umgeschrieben und nicht weggeworfen: »Tr« wäre nicht mehr zu
    lesen. Alles, was in einem Dateinamen Ärger macht, wird zum Bindestrich -
    das ist stumpf, aber es geht hier um Wiederfinden, nicht um Schönheit.
    """
    ersetzt = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
               .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
               .replace("ß", "ss"))
    ohne_zeichen = unicodedata.normalize("NFKD", ersetzt).encode(
        "ascii", "ignore").decode("ascii")
    sauber = re.sub(r"[^A-Za-z0-9]+", "-", ohne_zeichen).strip("-")
    return sauber or "ohne-titel"


def pillow_da() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def beschaffen(adresse: str, zuschneiden: bool = True) -> Path:
    """Holt ein Bild und legt es zugeschnitten ab. Gibt den Pfad zurück.

    Dieselbe Adresse ergibt immer dieselbe Datei - der Name kommt aus dem
    Streuwert der Adresse. Wer denselben Blogbeitrag zweimal entwirft, lädt
    das Bild nicht zweimal herunter.
    """
    if not adresse.startswith(("http://", "https://")):
        pfad = Path(adresse)
        if not pfad.is_file():
            raise BildFehler(f"Das Bild gibt es nicht: {adresse}")
        return pfad

    endung = Path(adresse.split("?")[0]).suffix.lower() or ".jpg"
    if endung not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        endung = ".jpg"

    kennung = hashlib.sha256(adresse.encode("utf-8")).hexdigest()[:16]
    roh_ziel = ordner() / f"{kennung}-roh{endung}"
    fertig = ordner() / f"{kennung}-4x5.jpg"

    if fertig.is_file():
        return fertig

    if not roh_ziel.is_file():
        try:
            daten = holen(adresse)
        except AbrufFehler as fehler:
            raise BildFehler(f"Das Bild ließ sich nicht holen: {fehler}") from fehler
        if len(daten) > GROESSE_MAX:
            raise BildFehler(
                f"Das Bild ist {len(daten) // 1024 // 1024} MB groß – das ist "
                "zu viel für einen Beitrag."
            )
        roh_ziel.write_bytes(daten)

    if not zuschneiden or not pillow_da():
        return roh_ziel

    try:
        return _zuschneiden(roh_ziel, fertig)
    except Exception as fehler:  # noqa: BLE001
        # Ein Bild, das sich nicht zuschneiden lässt, ist besser als keines.
        # Die Netzwerke rechnen es dann selbst zurecht.
        raise BildFehler(
            f"Zuschneiden fehlgeschlagen ({fehler}); das ungeschnittene Bild "
            f"liegt unter {roh_ziel}"
        ) from fehler


def _zuschneiden(quelle: Path, ziel: Path) -> Path:
    from PIL import Image, ImageOps

    with Image.open(quelle) as bild:
        # Kameras schreiben die Drehung in die Exif-Angaben statt ins Bild.
        # Ohne diese Zeile liegen Hochkantfotos auf der Seite.
        bild = ImageOps.exif_transpose(bild)

        if bild.mode in ("RGBA", "LA", "P"):
            # JPEG kennt keine Transparenz. Ohne den weißen Grund werden
            # durchsichtige Stellen schwarz - bei freigestellten Produktfotos
            # das halbe Bild.
            grund = Image.new("RGB", bild.size, (255, 255, 255))
            bild = bild.convert("RGBA")
            grund.paste(bild, mask=bild.split()[-1])
            bild = grund
        elif bild.mode != "RGB":
            bild = bild.convert("RGB")

        # ImageOps.fit beschneidet auf das Seitenverhältnis, ohne zu stauchen.
        zugeschnitten = ImageOps.fit(
            bild, (BREITE, HOEHE), method=Image.LANCZOS, centering=(0.5, 0.5)
        )
        zugeschnitten.save(ziel, "JPEG", quality=88, optimize=True)

    return ziel


def masse(pfad: Path | str) -> tuple[int, int] | None:
    """Breite und Höhe – oder None, wenn Pillow fehlt."""
    if not pillow_da():
        return None
    from PIL import Image

    try:
        with Image.open(pfad) as bild:
            return bild.size
    except Exception:  # noqa: BLE001
        return None
