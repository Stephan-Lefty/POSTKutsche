[Deutsch](README.md) | [English](README.en.md) | [Änderungsprotokoll](CHANGELOG.md) | [TODO](TODO.md)

# Sendeplan

Ein Redaktionskalender für die eigenen Seiten und die sozialen Netzwerke.

Sendeplan sieht auf Ihren Blogs und in Ihren Shops nach, was es Neues gibt,
lässt Claude daraus für jedes Netzwerk eine eigene Fassung schreiben, legt sie
Ihnen im Kalender zur Ansicht vor – und veröffentlicht sie zu dem Zeitpunkt,
den Sie bestimmt haben. Für Facebook und Instagram, solange Metas Prüfung
aussteht, legt es Text und Bild fertig zum Kopieren bereit.

Entwickelt unter Arch Linux und Debian.

## Was es tut

**Es findet die Anlässe selbst.** WordPress über die REST-Schnittstelle,
Shopware 6 über die Store-API, Seiten ohne Schnittstelle über ihre Seitenkarte.
Ein neuer Blogbeitrag oder ein neues Produkt landet als Vorschlag im Kalender.

**Es schreibt je Netzwerk anders.** Ein Mastodon-Beitrag hat 500 Zeichen, ein
LinkedIn-Beitrag wird nach dem ersten Satz zugeklappt, bei Instagram ist kein
Verweis anklickbar. Dieselbe Meldung viermal einzufügen führt dazu, dass sie
dreimal nicht passt.

**Es kennt Ihre Leser.** Terminvorschläge richten sich nach Netzwerk und
Zielgruppe – und für das Handwerk nach dem Handwerk, nicht nach den Ratgebern:
Ein Dachdecker schaut um halb sieben aufs Handy, nicht um zehn.

**Es lässt nichts ungelesen raus.** Beiträge stehen als Entwurf im Kalender,
bis Sie sie freigeben. Je Projekt kann man das abschalten.

**Es kann wiederholen.** Ein Beitrag, der im Juni gut lief, lässt sich im
nächsten Juni erneut einstellen. Der alte bleibt mit seinem Datum stehen, der
neue ist ein Entwurf – Sie sehen also, was schon lief, und können es abwandeln.
Das müssen Sie auch: Facebook und Instagram drosseln wortgleiche Wiederholungen.

## Was es nicht tut

**Keine Videos.** Aus Bildern kleine Filme zu machen war der ursprüngliche
Plan und wurde am 2026-08-28 gestrichen. Es gibt Bilder, auf 4:5 beschnitten.

**Kein Anmelden mit Benutzername und Passwort.** Die Netzwerke lassen das nicht
zu und haben recht damit. Es braucht Zugangstoken, und die legen Sie selbst an.

**Kein Umgehen von Metas Prüfung.** Facebook und Instagram automatisch zu
bespielen setzt eine geprüfte Meta-App voraus. Bis dahin: Handbetrieb.

## Einrichten

```
git clone https://github.com/Stephan-Lefty/Sendeplan.git
cd Sendeplan
pip install -e .
sendeplan einrichten
```

Der Kern läuft ohne Fremdpakete. Zwei Dinge sind Kür:

```
pip install -e ".[bilder]"      # Bilder auf 4:5 beschneiden (Pillow)
pip install -e ".[schluessel]"  # Token im Schlüsselbund statt in einer Datei
pip install -e ".[alles]"       # beides
```

## Erste Schritte

```
sendeplan einrichten              # Ablage anlegen, Beispielprojekte eintragen
sendeplan projekt liste           # was da ist
sendeplan netzwerke               # Farben, Zeichengrenzen, Eigenheiten
sendeplan plan --monat 2026-09    # was ansteht
```

Projekte lassen sich jederzeit ergänzen:

```
sendeplan projekt neu meinblog "Mein Blog" https://meinblog.example --art wordpress
```

Und anhalten, ohne etwas zu verlieren:

```
sendeplan projekt pausieren meinblog   # nichts mehr holen, nichts mehr senden
sendeplan projekt starten meinblog     # weiter wie zuvor
```

Pausieren und Ausblenden sind zweierlei: Das Häkchen im Kalender räumt nur die
Ansicht auf, Pausieren hält den Betrieb an.

## Die eigenen Seiten eintragen

Im Repository stehen nur Beispiele unter `.example`. Die eigenen Seiten kommen
nach `~/.config/sendeplan/projekte.json` – dort und nirgends sonst:

```json
[
  {
    "kennung": "meinblog",
    "name": "Mein Blog",
    "adresse": "https://meinblog.example",
    "art": "wordpress",
    "farbe": "#16a34a",
    "einstellungen": {
      "rest": "https://meinblog.example/wp-json/wp/v2",
      "zielgruppe": "verbraucher",
      "ausschliessen": ["/en/"]
    }
  }
]
```

`ausschliessen` übergeht Adressen, die ein Bruchstück enthalten – nötig bei
zweisprachigen Seiten, die jeden Beitrag doppelt liefern. `zielgruppe` steuert
die Terminvorschläge und ist eines von `handwerk`, `verbraucher`, `betroffene`
oder `gemischt`.

Wer Kampagnen nach Hersteller fahren will, legt daneben eine
`hersteller.json` an:

```json
{
  "musterwerk": {
    "namen": ["musterwerk", "muster-werk"],
    "reihen": ["mw12", "mw40"]
  }
}
```

Unter `namen` stehen die Schreibvarianten, unter `reihen` die
Modellbezeichnungen – für Produkte, die den Hersteller nicht im Namen tragen.

Beide Dateien stehen in `.gitignore` und werden von einem Test bewacht.

## Wo die Zugangsdaten liegen

Im Schlüsselbund, wenn `keyring` da ist. Sonst in
`~/.config/sendeplan/zugaenge.json` mit Rechten `600`. In der Datenbank stehen
sie nicht, im Repository erst recht nicht – ein Test wacht darüber.

Was Sie je Netzwerk brauchen:

| Netzwerk | Aufwand | Was nötig ist |
|---|---|---|
| Mastodon | zwei Minuten | Zugangstoken aus den Kontoeinstellungen |
| LinkedIn (eigenes Profil) | eine halbe Stunde | eigene App, „Share on LinkedIn", `w_member_social`. Token läuft nach 60 Tagen ab und wird erneuert. |
| Facebook-Seite | Wochen | Meta-App mit geprüften Berechtigungen |
| Instagram | Wochen | dasselbe, dazu ein Business-Konto (nicht Creator) mit verknüpfter Facebook-Seite |

## Stand

Frühe Fassung. Was steht und was noch fehlt, steht im
[Änderungsprotokoll](CHANGELOG.md) und in der [Aufgabenliste](TODO.md).

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
