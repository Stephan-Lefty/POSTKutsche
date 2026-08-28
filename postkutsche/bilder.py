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
