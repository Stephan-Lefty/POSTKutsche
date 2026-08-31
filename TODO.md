[Deutsch](TODO.md) | [English](TODO.en.md) | [Übersicht](README.md) | [Änderungsprotokoll](CHANGELOG.md)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes wird
nicht gelöscht, sondern nach unten verschoben – mit dem Datum, an dem es fertig
wurde.

## Offen

### Als Nächstes

- **Die erste Woche mit dem neuen Seitenlesen planen.** Seit dem 2026-08-28
  wird der Fließtext der Produktseite gelesen statt nur der `og:description`,
  und Umleitungen werden verfolgt. Damit sollten deutlich weniger Rückfragen
  entstehen – nachsehen, ob das eintritt, und sonst die Anweisung in
  `denker/vorlagen.py` nachschärfen.
- **Die Seitenkarte des ersten Shops ist veraltet.** Stichprobe vom
  2026-08-28: von zwölf Produktadressen führte keine unverändert zum Ziel,
  zehn landeten auf einer Kategorieübersicht oder der Fehlerseite. Sie werden
  jetzt übersprungen, aber damit schrumpft der Vorrat auf etwa ein Fünftel.
  Klären, ob sich die Seitenkarte neu erzeugen lässt. Seit dem 2026-08-31
  gemessen: 115 der 158 Kategorien in der Karte gibt es nicht mehr, und
  umgekehrt verlinkt die Seite 30 Kategorien, die in der Karte fehlen – die
  fehlen damit auch im Planungsfenster.
- **Die Produktzahlen im Planungsfenster stimmen nicht.** Sie werden aus der
  Seitenkarte gezählt, und die ist veraltet: »Schallschutztüren« meldet zwölf,
  die Seite zeigt eines. Richtig zählen hieße ein Abruf je Kategorie – das
  geht erst, wenn die Zahlen nicht mehr beim Öffnen des Formulars gebraucht
  werden.
- **Die drei Bereiche stehen in der Kategorienliste.** »Türen Shop« meldet
  1646 Produkte und liefert keines: Es ist eine Übersichtsseite, die nur auf
  Unterkategorien verweist. Wer sie ankreuzt, plant eine leere Woche –
  `kampagnenlauf.py` sagt das immerhin dazu.
- **Die Kategorien der beiden Shops nachschärfen.** Angebunden sind je zwei.
  Im Sortiment stehen außerdem »Zubehör« beim einen und »Dichtungen und
  Ersatzteile« sowie »Montagewerkzeug« beim anderen. Nachtragen heißt: eine
  Zeile mehr unter `kategorien` in `~/.config/postkutsche/projekte.json`.
- **Kategorien mit mehr als einer Seite.** Gelesen wird die erste Seite der
  Kategorie. Bei zwölf Produkten fällt das nicht auf; bei einer Kategorie mit
  achtzig bleibt der Rest ungesehen. Die Folgeseiten hängen bei Shopware an
  `?p=2`.
- **Die Uhrzeit im Kalender ändern können.** Ziehen verschiebt bisher nur den
  Tag; die Uhrzeit lässt sich nur über die Vorschläge aus `sendezeiten.py`
  setzen.
- **Beiträge in der Oberfläche löschen können.** Bisher geht das nur über die
  Datenbank.
- **»Von Hand veröffentlicht« bei Mastodon ausblenden.** Der Knopf gehört zum
  Handbetrieb für Facebook und Instagram und verwirrt, wo automatisch gesendet
  wird.

### Danach

- **LinkedIn.** Eigenes Profil, `w_member_social`. Token läuft nach 60 Tagen ab;
  die Erneuerung muss von selbst geschehen und darf nicht am Wochenende
  scheitern, an dem sie fällig wird.
- **Bilder.** Zuschnitt auf 4:5 (1080×1350) mit Pillow. Ohne Pillow das
  unveränderte Bild von der Website nehmen.
- **Ablageort für Instagram-Bilder.** Instagram nimmt keine Datei entgegen –
  Meta lädt das Bild selbst von einer öffentlichen Adresse. Zugeschnittene
  Bilder brauchen also einen Platz im Netz (SFTP auf eigenen Webspace), oder es
  wird das unveränderte Bild von der eigenen Seite genommen.
- **Zeitplan.** systemd-Benutzer-Timer, der alle fünf Minuten Fälliges sendet.
  War der Rechner aus, muss der Beitrag beim nächsten Start rausgehen – mit
  einem Vermerk über die Verspätung, nicht stillschweigend.
- **Resonanz messen.** Die Sendezeiten in `sendezeiten.py` sind Schätzungen aus
  Branchenauswertungen. Sobald genug eigene Beiträge draußen sind: Reaktionen
  einsammeln und die Vorschläge durch die eigenen Zahlen ersetzen.
- **Warnung vor Dubletten.** Wer einen Beitrag wiederholt, sollte sehen, wie
  ähnlich der neue Text dem alten ist. Facebook und Instagram drosseln
  Wortgleiches.
- **Facebook und Instagram über die Schnittstelle.** Erst wenn sich im Betrieb
  zeigt, dass der Handbetrieb nicht reicht. Metas App-Prüfung dauert zwei bis
  vier Wochen je Einreichung.

### Fragen, die im Betrieb zu klären sind

- **Reicht der Handbetrieb?** Wenn ja, entfällt Metas Prüfung ganz.
- **Öffentliches oder privates Repository?** Bei privat kosten Actions-Minuten
  Geld; der Workflow steht deshalb schon in der Sparfassung.

## Erledigt

- **Gerüst** (2026-08-28): Ablage, Kommandozeile, die fünf Projekte,
  Zeitrechnung, Netzwerkverzeichnis, Sendezeiten, Wiederholungen. 109 Tests.
- **Quellen geprüft** (2026-08-28): Welche Seite welche Schnittstelle hat, steht
  im [Änderungsprotokoll](CHANGELOG.md).
- **Die beiden Shopware-Shops angebunden** (2026-08-31): über die Seitenkarte,
  ohne Zugangsschlüssel. Sie stehen jetzt als Art »seitenkarte« und sind unter
  »Woche planen« wählbar; ihre Kategorien stehen in der Projektdatei, weil die
  Seitenkarte bei Shopware nicht verrät, was in einer Kategorie liegt.
- **Tote Kategorien aussortiert** (2026-08-31): Das Planungsfenster bot
  Kategorien an, die es nicht mehr gibt – »Passivhaustüren« zum Beispiel.
  Abgeglichen wird jetzt mit der Navigation der Seite; von 158 Kategorien
  bleiben 43, und was wegfällt, steht als Hinweis über der Liste.
