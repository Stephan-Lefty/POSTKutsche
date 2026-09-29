#!/bin/sh
# POSTKutsche aus einem einzigen Ordner starten - vom Stick oder von einer
# externen Platte.
#
# Das Skript setzt POSTKUTSCHE_ORDNER auf das Verzeichnis, in dem es selbst
# liegt. Damit ist gleich, ob der Stick unter /media/name/STICK oder unter
# /run/media/name/1234-5678 auftaucht: Die Pfade richten sich nach dem
# Fundort, nicht nach einer Einstellung, die man am Zweitrechner nachziehen
# müsste.
#
# Darunter entstehen drei Ordner:
#   einstellungen/  projekte.json, marken.json, denker.json, Logos
#   ablage/         postkutsche.db, bilder/, bestand/
#   dokumente/      die fertigen Grafiken, Texte und HTML-Dateien
#
# Was NICHT mitwandert: Python, Firefox und die Claude-Kommandozeile. Die
# müssen auf dem anderen Rechner vorhanden sein. POSTKutsche selbst kommt
# aus dem Repository - ein »git clone« genügt.
#
# **Die Zugangsdaten liegen hier im Klartext.** Einen Schlüsselbund gibt es
# auf einem Stick nicht, also landen Mastodon-Zugang und Claude-Jahreszugang
# in einstellungen/zugaenge.json. Auf einem FAT-formatierten Stick sind
# Dateirechte wirkungslos: Wer den Stick findet, hat die Zugänge. Wer das
# nicht will, formatiert den Stick verschlüsselt (LUKS, VeraCrypt) oder
# lässt die Zugänge weg und trägt sie am Zweitrechner neu ein.

set -eu

HIER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export POSTKUTSCHE_ORDNER="$HIER"

mkdir -p "$HIER/einstellungen" "$HIER/ablage" "$HIER/dokumente"

# Ohne Python geht nichts, und die Meldung soll das sagen statt
# »command not found«.
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 ist auf diesem Rechner nicht installiert." >&2
    echo "POSTKutsche braucht es; die Daten auf dem Stick bleiben unberührt." >&2
    exit 1
fi

echo "POSTKutsche läuft aus: $HIER"
exec python3 -m postkutsche "$@"
