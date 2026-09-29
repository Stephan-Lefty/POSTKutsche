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
# Darunter liegen drei Ordner:
#   einstellungen/  projekte.json, marken.json, denker.json, Logos
#   ablage/         postkutsche.db, bilder/, bestand/
#   dokumente/      die fertigen Grafiken, Texte und HTML-Dateien
#
# **Die Daten wandern mit, das Programm nicht.** Python, Firefox und die
# Claude-Kommandozeile müssen auf dem anderen Rechner vorhanden sein, und
# POSTKutsche selbst kommt aus dem Repository - ein »git clone« genügt. Wo
# es liegt, steht in programm.txt neben diesem Skript; fehlt die Datei,
# wird an den üblichen Stellen gesucht.
#
# **Die Zugangsdaten liegen hier im Klartext.** Einen Schlüsselbund gibt es
# auf einem Stick nicht, also landen Mastodon-Zugang und Claude-Jahreszugang
# in einstellungen/zugaenge.json. Auf einem FAT-formatierten Datenträger
# sind Dateirechte wirkungslos: Wer ihn findet, hat die Zugänge. Wer das
# nicht will, formatiert verschlüsselt (LUKS, VeraCrypt) oder lässt die
# Zugänge weg und trägt sie am Zweitrechner neu ein.

set -eu

HIER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export POSTKUTSCHE_ORDNER="$HIER"

mkdir -p "$HIER/einstellungen" "$HIER/ablage" "$HIER/dokumente"

# Beim Doppelklick schließt sich das Fenster, sobald das Skript endet -
# eine Fehlermeldung wäre dann nicht zu lesen. Deshalb bei einem Abbruch
# warten, bis jemand die Eingabetaste drückt.
abbruch() {
    echo >&2
    echo "$1" >&2
    echo >&2
    printf "Eingabetaste zum Schließen ... " >&2
    read -r _ 2>/dev/null || true
    exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
    abbruch "Python 3 ist auf diesem Rechner nicht installiert.
POSTKutsche braucht es; die Daten auf dem Datenträger bleiben unberührt."
fi

# Wo das Programm liegt. Die Daten wandern mit, der Quelltext nicht -
# er gehört ins Repository und nicht auf einen Stick, wo er beim
# nächsten »git pull« veraltet.
PROGRAMM=""
if [ -f "$HIER/programm.txt" ]; then
    PROGRAMM=$(head -n 1 "$HIER/programm.txt")
fi
if [ -z "$PROGRAMM" ] || [ ! -d "$PROGRAMM/postkutsche" ]; then
    for ORT in "$HOME/GitHub/POSTKutsche" "$HOME/POSTKutsche" \
               "$HOME/Projekte/POSTKutsche" "$HOME/git/POSTKutsche"; do
        if [ -d "$ORT/postkutsche" ]; then
            PROGRAMM="$ORT"
            break
        fi
    done
fi
if [ -z "$PROGRAMM" ] || [ ! -d "$PROGRAMM/postkutsche" ]; then
    # Vielleicht ist es ordentlich installiert - dann genügt der Import.
    if ! python3 -c "import postkutsche" >/dev/null 2>&1; then
        abbruch "POSTKutsche selbst wurde auf diesem Rechner nicht gefunden.
Die Daten liegen hier, das Programm nicht - es gehört ins Repository.

Entweder:
  git clone https://github.com/Stephan-Lefty/POSTKutsche.git
und dann den Pfad dorthin in diese Datei schreiben:
  $HIER/programm.txt"
    fi
else
    export PYTHONPATH="$PROGRAMM${PYTHONPATH:+:$PYTHONPATH}"
fi

# Die Verknüpfung trägt einen absoluten Pfad (die Feldcodes der
# Desktop-Norm greifen in Anführungszeichen nicht). Damit sie auch an
# einem Rechner stimmt, an dem der Datenträger anders eingehängt ist,
# wird sie bei jedem Start neu geschrieben.
START="$HIER/POSTKutsche starten.desktop"
cat > "$START" <<ENDE
[Desktop Entry]
Type=Application
Name=POSTKutsche starten
Comment=Kalender aus diesem Ordner öffnen
Exec="$HIER/$(basename -- "$0")" kalender
Path=$HIER
Icon=$HIER/.postkutsche.png
Terminal=true
ENDE
chmod 755 "$START" 2>/dev/null || true

echo "POSTKutsche läuft aus: $HIER"
[ -n "$PROGRAMM" ] && echo "Programm:              $PROGRAMM"
echo

# Kein exec: Bricht POSTKutsche ab, soll die Meldung lesbar bleiben.
python3 -m postkutsche "$@" || abbruch "POSTKutsche wurde beendet."
