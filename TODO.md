[Deutsch](TODO.md) | [English](TODO.en.md) | [Übersicht](README.md) | [Änderungsprotokoll](CHANGELOG.md)

# TODO

Laufende Liste offener Punkte. Oben steht, was noch offen ist. Erledigtes wird
nicht gelöscht, sondern nach unten verschoben – mit dem Datum, an dem es fertig
wurde.

## Offen

### Als Nächstes

- **Quellen anbinden.** WordPress über `/wp-json/wp/v2/posts?_embed`, Shopware 6
  über die Store-API, altbau.example über `sitemap.xml` und `og:`-Auslesen. Je Quelle
  ein Test gegen eine aufgezeichnete Antwort, kein Netz im Test.
- **Claude anbinden.** `claude -p` mit festem Ausgabeformat, Anweisungen je
  Netzwerk. Test gegen einen vorgetäuschten Aufruf.
- **Weboberfläche.** Kalender in Monats- und Wochenansicht, links die
  Projektspalte zum Ein- und Ausblenden, Kärtchen in Projektfarbe mit
  Netzwerk-Streifen, Ziehen verschiebt den Termin.
- **Mastodon.** Das erste Netzwerk, das ganz durchläuft – vom Blogbeitrag bis
  zum veröffentlichten Post. Sofort nutzbar, kein Prüfverfahren.
- **Handbetrieb für Facebook und Instagram.** Übergabe-Ansicht mit Text zum
  Kopieren (unausgezeichnet, ohne Markdown-Zeichen), Bild auf 4:5 zum
  Herunterladen, Knopf »von Hand veröffentlicht«.

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

- **Zugangsschlüssel für die beiden Shopware-Shops.** Je Verkaufskanal einer.
- **Reicht der Handbetrieb?** Wenn ja, entfällt Metas Prüfung ganz.
- **Öffentliches oder privates Repository?** Bei privat kosten Actions-Minuten
  Geld; der Workflow steht deshalb schon in der Sparfassung.

## Erledigt

- **Gerüst** (2026-08-28): Ablage, Kommandozeile, die fünf Projekte,
  Zeitrechnung, Netzwerkverzeichnis, Sendezeiten, Wiederholungen. 109 Tests.
- **Quellen geprüft** (2026-08-28): Welche Seite welche Schnittstelle hat, steht
  im [Änderungsprotokoll](CHANGELOG.md).
