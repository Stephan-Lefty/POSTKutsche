[Deutsch](installation.md) | [English](installation.en.md) | [Übersicht](../README.md) | [Bedienung](bedienung.md) | [Änderungen](../CHANGELOG.md)

# Installation

Von der leeren Maschine bis zum laufenden Kalender. Wie man danach damit
arbeitet, steht in der [Bedienungsanleitung](bedienung.md).

Gerechnet ist mit Linux und einem Rechner, der einem selbst gehört – einem
Arbeitsplatz oder einem kleinen Server. Ein Mehrbenutzerbetrieb ist nicht
vorgesehen: POSTKutsche hat keine Anmeldung und hört nur auf `localhost`.

## Inhalt

- [Was gebraucht wird](#was-gebraucht-wird)
- [1. Programm installieren](#1-programm-installieren)
- [2. Ablage anlegen](#2-ablage-anlegen)
- [3. Die eigenen Seiten eintragen](#3-die-eigenen-seiten-eintragen)
- [4. Claude anbinden](#4-claude-anbinden)
- [5. Konten einrichten](#5-konten-einrichten)
- [6. Dauerbetrieb einrichten](#6-dauerbetrieb-einrichten)
- [Wohin was gelegt wird](#wohin-was-gelegt-wird)
- [Prüfen, ob alles steht](#prüfen-ob-alles-steht)
- [Wieder loswerden](#wieder-loswerden)

## Was gebraucht wird

**Python 3.11 oder neuer.** Mehr nicht – der Kern kommt ohne Fremdpakete aus.
Datenbank, Webdienst und alle Abrufe stecken in der Standardbibliothek. Das
ist Absicht: Ein Werkzeug, das man einmal einrichtet und dann jahrelang laufen
lässt, soll nicht an einer Bibliothek hängen, die es in zwei Jahren nicht
mehr gibt.

Zwei Dinge sind Kür und lassen sich nachrüsten:

| Paket | Wofür | Ohne es |
|---|---|---|
| Pillow | Bilder auf 4:5 zuschneiden | das unveränderte Bild von der Website wird genommen – es sieht auf dem Handy schlechter aus |
| keyring | Zugangstoken im Schlüsselbund | die Token landen in `~/.config/postkutsche/zugaenge.json` mit Rechten 600 |

Für das Schreiben der Texte wird **Claude Code** gebraucht (Schritt 4), für
den Dauerbetrieb **systemd** (Schritt 6). Beides ist nicht nötig, um sich das
Programm erst einmal anzusehen.

## 1. Programm installieren

```
git clone https://github.com/Stephan-Lefty/POSTKutsche.git
cd POSTKutsche
python -m venv .venv
source .venv/bin/activate
pip install -e ".[alles]"
```

`-e` heißt »editierbar«: Das Programm läuft aus dem Ordner, in dem es liegt.
Wer nur die Kürfunktionen einzeln will, nimmt `".[bilder]"` oder
`".[schluessel]"`; wer keine davon braucht, nur `pip install -e .`.

Danach gibt es den Befehl `postkutsche`:

```
postkutsche --fassung
```

## 2. Ablage anlegen

```
postkutsche einrichten
```

Das legt die Datenbank unter `~/.local/share/postkutsche/postkutsche.db` an
und trägt fünf Beispielprojekte ein – ein Blog, ein Shop, eine Seite ohne
Schnittstelle und so weiter, alle mit `.example`-Adressen. Damit lässt sich
die Oberfläche ansehen, ohne dass irgendwo etwas abgerufen wird.

Ein Blick in den Kalender, ohne dass schon etwas dauerhaft laufen muss:

```
postkutsche kalender
```

Der Browser geht auf `http://localhost:8770` auf. Mit `--nicht-oeffnen`
bleibt er zu, mit `--port` läuft der Dienst woanders.

## 3. Die eigenen Seiten eintragen

**Die eigenen Adressen stehen nicht im Repository.** Sie kommen nach
`~/.config/postkutsche/projekte.json`, und nur dorthin. Ein öffentliches
Repository ist durchsuchbar, wird geklont und landet in Suchmaschinen; wer
darin nachliest, welche Läden jemand betreibt und mit welchen Herstellern er
arbeitet, bekommt ein Bild, das so nirgends stehen sollte. Und was einmal in
der Versionsgeschichte stand, steht auch nach dem Löschen noch darin.

```json
[
  {
    "kennung": "meinblog",
    "name": "Mein Blog",
    "adresse": "https://meinblog.example",
    "art": "wordpress",
    "farbe": "#6bad08",
    "einstellungen": {
      "rest": "https://meinblog.example/wp-json/wp/v2",
      "zielgruppe": "verbraucher"
    }
  }
]
```

Drei Arten gibt es:

- **`wordpress`** – die REST-Schnittstelle unter `/wp-json/wp/v2/`. Sie ist
  bei den meisten Blogs offen und liefert Titel, Text, Beitragsbild,
  Kategorien und das Erscheinungsdatum.
- **`seitenkarte`** – für Seiten ohne jede Schnittstelle: `sitemap.xml` lesen,
  die Seite selbst auslesen, Bild aus `og:image`. Auch Shopware-Shops laufen
  so; ein Zugangsschlüssel wird dafür nicht gebraucht.
- **`shopware`** – die Store-API. Vorgesehen, aber nicht ausgebaut; nimm
  `seitenkarte`.

`zielgruppe` steuert die Terminvorschläge und ist eines von `handwerk`,
`verbraucher`, `betroffene` oder `gemischt`. Bei einem zweisprachigen Blog
gehört ein Sprachfilter dazu, sonst werden die fremdsprachigen Fassungen
mitgezählt und mitgeplant:

```json
"einstellungen": { "ausschliessen": ["/en/"] }
```

Wer Kampagnen nach Hersteller fahren will, legt daneben eine
`hersteller.json` an; wie sie aussieht, steht im
[README](../README.md#die-eigenen-seiten-eintragen).

Ein Projekt geht auch ohne Datei, direkt von der Kommandozeile:

```
postkutsche projekt neu meinblog "Mein Blog" https://meinblog.example --art wordpress
postkutsche projekt liste
```

## 4. Claude anbinden

Die Texte schreibt Claude, aufgerufen über die Kommandozeile – das nutzt ein
vorhandenes Abo, kostet nichts je Beitrag und braucht keinen Schlüssel, der
verwaltet werden will.

```
npm install -g @anthropic-ai/claude-code
claude
```

Beim ersten Start einmal `/login` eingeben und anmelden. Danach findet
POSTKutsche den Befehl von selbst. Fehlt er, sagt das Programm genau das und
nennt diese beiden Zeilen – es rät nicht und schreibt auch nichts Halbes.

Probe aufs Exempel, sobald ein Projekt eingetragen ist:

```
postkutsche entwerfen --projekt meinblog --anzahl 1
```

## 5. Konten einrichten

Ein Konto anlegen, hier Mastodon:

```
postkutsche konto neu mastodon mastodon-privat --instanz https://mastodon.example
postkutsche konto token mastodon-privat
postkutsche konto pruefen mastodon-privat
```

Das Token legst du auf deinem Mastodon-Server selbst an, als neue Anwendung
in deinen Kontoeinstellungen. Zwei Rechte genügen: `write:statuses`, und für
Bilder zusätzlich `write:media`. Mehr sollte man nicht vergeben – ein Token,
das nur schreiben darf, kann nichts ausplaudern.

Bei der Eingabe bleibt das Token unsichtbar und geht in den Schlüsselbund;
gibt es keinen, nach `~/.config/postkutsche/zugaenge.json` mit Rechten 600.
**In der Datenbank steht es nie.** Ein Test wacht darüber, dass die Tabelle
der Konten keine Spalte mit »token«, »passwort« oder »secret« bekommt.

`konto pruefen` fragt beim Netzwerk nach, ohne etwas zu senden.

Facebook und Instagram brauchen kein Konto: Sie laufen über den Handbetrieb,
siehe [Bedienung](bedienung.md#veröffentlichen).

## 6. Dauerbetrieb einrichten

```
postkutsche dienst einrichten
```

Das legt drei Einheiten in `~/.config/systemd/user/` an und startet sie:

| Einheit | Wofür |
|---|---|
| `postkutsche-kalender.service` | hält die Oberfläche auf `localhost:8770` am Laufen |
| `postkutsche-senden.service` | sendet, was fällig ist |
| `postkutsche-senden.timer` | stößt das alle fünf Minuten an |

Der Zeitgeber ist `Persistent=true`: War der Rechner zur Sendezeit aus, geht
der Beitrag beim nächsten Start raus statt gar nicht.

Damit das auch ohne angemeldete Sitzung läuft – auf einem Server, oder wenn
du dich abmeldest –, braucht es einmal:

```
sudo loginctl enable-linger $USER
```

Ein Eintrag im Anwendungsmenü, wenn gewünscht:

```
postkutsche dienst menueeintrag
```

## Wohin was gelegt wird

| Was | Wohin |
|---|---|
| Datenbank | `~/.local/share/postkutsche/postkutsche.db` |
| eigene Projekte | `~/.config/postkutsche/projekte.json` |
| eigene Hersteller | `~/.config/postkutsche/hersteller.json` |
| Token ohne Schlüsselbund | `~/.config/postkutsche/zugaenge.json` (600) |
| Zwischenspeicher, Bilder | `~/.local/share/postkutsche/` |
| abgelegte Bilder | `~/Dokumente/POSTKutsche/<Jahr>-KW<Woche>/<Projekt>/` |
| systemd-Einheiten | `~/.config/systemd/user/` |

Zwei Umgebungsvariablen verschieben das, wo es nötig ist:
`POSTKUTSCHE_CONFIG` für den Konfigurationsordner, `POSTKUTSCHE_DOKUMENTE`
für die Bildablage. Wie der Dokumentenordner heißt, wird sonst beim System
erfragt und nicht geraten – auf einem englischen System heißt er
»Documents«.

Die Datenbank lässt sich mit `--ablage` umlenken, etwa zum Ausprobieren:

```
postkutsche --ablage /tmp/probe.db einrichten
```

## Prüfen, ob alles steht

```
postkutsche dienst stand           # laufen Kalender und Zeitgeber?
postkutsche projekt liste          # sind die Projekte da?
postkutsche konto liste            # sind die Konten da?
postkutsche senden --probelauf     # was ginge jetzt raus?
python -m unittest discover -s tests
```

`--probelauf` sendet nichts, sondern zeigt nur, was fällig wäre. Die Tests
laufen ohne Netzzugriff: Die Quellen werden gegen aufgezeichnete Antworten
geprüft, die Claude-Anbindung gegen einen vorgetäuschten Aufruf.

## Wieder loswerden

```
postkutsche dienst entfernen
pip uninstall postkutsche
```

`dienst entfernen` hält die Einheiten an und löscht sie. Was du erarbeitet
hast, bleibt: Datenbank, Konfiguration und abgelegte Bilder stehen weiter in
den Ordnern oben und müssen von Hand weg, wenn sie weg sollen.
