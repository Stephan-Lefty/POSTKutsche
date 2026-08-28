"""POSTKutsche im Hintergrund laufen lassen.

Zwei systemd-Einheiten für den Benutzer, kein root, keine Systemdateien:

- **postkutsche-kalender.service** – der Kalender. Läuft dauerhaft, startet
  beim Anmelden. Danach genügt ein Lesezeichen im Browser; kein Terminal, das
  offen bleiben muss.
- **postkutsche-senden.timer** – schickt alle fünf Minuten, was fällig ist.

**Warum Benutzereinheiten und nicht systemweit:** Sie brauchen kein
Administratorkennwort, laufen unter dem eigenen Konto und finden damit den
Schlüsselbund und die eigene Konfiguration. Eine systemweite Einheit liefe als
anderer Benutzer und käme an nichts davon heran.

**Ein Haken, den man kennen muss:** Benutzerdienste enden beim Abmelden,
sofern »lingering« nicht eingeschaltet ist. Für den Kalender ist das richtig
so - wer nicht angemeldet ist, schaut auch nicht hinein. Für den Sendetimer
ist es unerwünscht: Ein Beitrag um 6:30 Uhr geht sonst erst raus, wenn sich
jemand anmeldet. `einrichten()` sagt das ausdrücklich und nennt den Befehl.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

KALENDER = "postkutsche-kalender.service"
SENDEN_DIENST = "postkutsche-senden.service"
SENDEN_TIMER = "postkutsche-senden.timer"


def ordner() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def verfuegbar() -> bool:
    return shutil.which("systemctl") is not None and os.name == "posix"


def _befehl() -> str:
    """Wie POSTKutsche aufzurufen ist – aus der laufenden Umgebung abgeleitet.

    `sys.executable` statt schlicht »python«: In einer virtuellen Umgebung
    zeigt das auf den richtigen Deuter, und systemd hat keinen aktivierten
    Pfad.
    """
    return f"{sys.executable} -m postkutsche"


def _wurzel() -> Path:
    """Das Verzeichnis, aus dem POSTKutsche läuft.

    Wird als WorkingDirectory in die Einheit geschrieben. Ohne das scheitert
    der Dienst mit »No module named postkutsche«, sobald das Paket nicht mit
    pip installiert ist, sondern nur im Projektordner liegt - und genau so
    läuft es hier. Aufgefallen beim ersten Start als Dienst: Er versuchte es
    48-mal, bevor jemand ins Protokoll sah.
    """
    return Path(__file__).resolve().parent.parent


def einheiten(port: int = 8770) -> dict[str, str]:
    ruf = _befehl()
    wurzel = _wurzel()
    return {
        KALENDER: f"""[Unit]
Description=POSTKutsche – Kalender
Documentation=https://github.com/Stephan-Lefty/POSTKutsche
After=network.target

[Service]
Type=simple
WorkingDirectory={wurzel}
Environment=PYTHONPATH={wurzel}
ExecStart={ruf} kalender --port {port} --nicht-oeffnen
Restart=on-failure
RestartSec=10
# Nicht endlos neu starten: Ein Dienst, der 48-mal scheitert, hat ein
# Problem, das kein weiterer Versuch löst - er soll aufgeben und es sichtbar
# machen.
StartLimitBurst=5
StartLimitIntervalSec=300

[Install]
WantedBy=default.target
""",
        SENDEN_DIENST: f"""[Unit]
Description=POSTKutsche – fällige Beiträge senden
Documentation=https://github.com/Stephan-Lefty/POSTKutsche

[Service]
Type=oneshot
WorkingDirectory={wurzel}
Environment=PYTHONPATH={wurzel}
ExecStart={ruf} senden
""",
        SENDEN_TIMER: """[Unit]
Description=POSTKutsche – alle fünf Minuten nachsehen, was fällig ist

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
# Verpasstes nachholen: War der Rechner aus, geht der Beitrag beim nächsten
# Start raus. POSTKutsche vermerkt die Verspätung, statt sie zu verschweigen.
Persistent=true

[Install]
WantedBy=timers.target
""",
    }


def einrichten(port: int = 8770, melden=print) -> int:
    """Schreibt die Einheiten und startet sie."""
    if not verfuegbar():
        melden("systemd ist hier nicht verfügbar – auf diesem System geht das nicht.")
        return 1

    ziel = ordner()
    ziel.mkdir(parents=True, exist_ok=True)
    for name, inhalt in einheiten(port).items():
        (ziel / name).write_text(inhalt, encoding="utf-8")
        melden(f"geschrieben: {ziel / name}")

    _systemctl("daemon-reload")
    for name in (KALENDER, SENDEN_TIMER):
        _systemctl("enable", "--now", name)
        melden(f"gestartet: {name}")

    melden(f"\nDer Kalender läuft jetzt dauerhaft auf http://127.0.0.1:{port}/")
    melden("Diese Adresse als Lesezeichen anlegen – mehr braucht es nicht.")
    melden(
        "\nDamit auch gesendet wird, während du nicht angemeldet bist:\n"
        f"  sudo loginctl enable-linger {os.environ.get('USER', 'DEIN-BENUTZER')}\n"
        "Ohne das enden die Dienste beim Abmelden, und ein Beitrag um 6:30 Uhr\n"
        "geht erst raus, wenn du dich anmeldest."
    )
    return 0


def entfernen(melden=print) -> int:
    """Hält die Einheiten an und löscht sie."""
    if not verfuegbar():
        return 1
    for name in (KALENDER, SENDEN_TIMER):
        _systemctl("disable", "--now", name, still=True)
    for name in einheiten():
        datei = ordner() / name
        if datei.exists():
            datei.unlink()
            melden(f"entfernt: {datei}")
    _systemctl("daemon-reload")
    return 0


def verknuepfung(port: int = 8770, melden=print) -> int:
    """Legt einen Eintrag im Anwendungsmenü an.

    Er startet keinen Dienst, sondern öffnet nur die Adresse im Browser - der
    Kalender läuft ja im Hintergrund. Damit fühlt es sich an wie ein Programm,
    obwohl es eine Seite im Browser ist.

    Nach ~/.local/share, nicht nach /usr/share: kein Administratorkennwort,
    und es gilt nur für diesen Benutzer.
    """
    from . import __version__

    anwendungen = Path.home() / ".local" / "share" / "applications"
    anwendungen.mkdir(parents=True, exist_ok=True)

    # Das Icon in den Symbolordner legen, damit die Arbeitsumgebung es findet.
    # Ein Verweis auf eine Datei im Projektordner ginge auch, hinge dann aber
    # daran, dass niemand das Verzeichnis verschiebt.
    quelle = Path(__file__).parent.parent / "assets" / "icon-256.png"
    symbol = "postkutsche"
    if quelle.is_file():
        ziel = Path.home() / ".local/share/icons/hicolor/256x256/apps"
        ziel.mkdir(parents=True, exist_ok=True)
        (ziel / f"{symbol}.png").write_bytes(quelle.read_bytes())
        melden(f"Symbol: {ziel / f'{symbol}.png'}")

    datei = anwendungen / "postkutsche.desktop"
    datei.write_text(f"""[Desktop Entry]
Type=Application
Version=1.0
Name=POSTKutsche
GenericName=Redaktionskalender
Comment=Beiträge für Blogs, Shops und soziale Netzwerke planen
Exec=xdg-open http://127.0.0.1:{port}/
Icon={symbol}
Terminal=false
Categories=Office;Network;
Keywords=Kalender;Social;Beitrag;Mastodon;Facebook;Instagram;
StartupNotify=false
X-POSTKutsche-Version={__version__}
""", encoding="utf-8")
    datei.chmod(0o755)
    melden(f"Eintrag: {datei}")

    # Manche Arbeitsumgebungen merken neue Einträge erst nach einem Anstoß.
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(anwendungen)],
                       capture_output=True)

    melden("\nPOSTKutsche steht jetzt im Anwendungsmenü.")
    melden("Ein Klick öffnet den Kalender im Browser – kein Terminal nötig.")
    return 0


def stand(melden=print) -> int:
    """Zeigt, ob die Dienste laufen."""
    if not verfuegbar():
        melden("systemd ist hier nicht verfügbar.")
        return 1
    for name in (KALENDER, SENDEN_TIMER):
        if not (ordner() / name).exists():
            melden(f"{name:<32} nicht eingerichtet")
            continue
        lauf = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True,
        )
        melden(f"{name:<32} {lauf.stdout.strip() or 'unbekannt'}")
    return 0


def _systemctl(*teile: str, still: bool = False) -> None:
    lauf = subprocess.run(
        ["systemctl", "--user", *teile], capture_output=True, text=True
    )
    if lauf.returncode != 0 and not still:
        meldung = (lauf.stderr or lauf.stdout).strip()
        raise RuntimeError(f"systemctl {' '.join(teile)}: {meldung}")
