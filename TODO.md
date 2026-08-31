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
  Klären, ob sich die Seitenkarte neu erzeugen lässt. Für die Kategorienliste
  spielt sie seit dem 2026-08-31 keine Rolle mehr – dort zählt die
  Navigation –, für die Produktadressen aber schon: 115 der 158 Kategorien in
  der Karte gibt es nicht mehr, und sie verschweigt 57, die es gibt.
- **Beiwerk in der Kategorienliste, das noch niemand benannt hat.** Draußen
  sind Konfiguratoren und Abholgebiete. Beim Durchsehen der 116 fielen
  außerdem auf: »Angebote« und »Angebote und Abholware« (Sammelbecken statt
  Sortiment) sowie zwei Kategorien, deren Beschriftung auf der Seite kaputt
  kodiert ist. Nichts davon auf Verdacht entfernt – wenn es stört, ein Wort
  genügt.
- **Nachschlag aus der Seitenkarte für magere Kategorien?** Von dem, was nur
  die Karte kennt und die Navigation nicht verlinkt, leben gemessen elf
  Prozent – zu wenig, um sie allgemein heranzuziehen. Eine Kategorie war die
  Ausnahme: In `t30-1_brandschutztueren_aluminium_576` leben alle fünf. Wenn
  sich das häuft, wäre ein Nachschlag für zu kleine Kategorien zu überlegen –
  aber erst, wenn es beim Planen auffällt.
- **Gelerntes nachschärfen, wenn es sich einspielt.** Offen ist, ob zwölf
  Einträge je Anweisung reichen und ob die neuesten die richtigen sind. Wenn
  eine Antwort zurückgenommen werden muss, geht das bisher nur durch
  Streichen und neu Beantworten – Bearbeiten gibt es nicht.
- **Die Uhrzeit im Kalender ändern können.** Ziehen verschiebt bisher nur den
  Tag; die Uhrzeit lässt sich nur über die Vorschläge aus `sendezeiten.py`
  setzen.
- **Beiträge in der Oberfläche löschen können.** Bisher geht das nur über die
  Datenbank.
- **»Von Hand veröffentlicht« bei Mastodon ausblenden.** Der Knopf gehört zum
  Handbetrieb für Facebook und Instagram und verwirrt, wo automatisch gesendet
  wird.
- **Ein drittes Bild.** Zwei stecken in zwei Spalten; beim dritten ist eine
  eigene Tabelle fällig, dann mit Sortierspalte. Vorher wäre es geraten, wie
  viele es werden.
- **Das zweite Bild auch über die Schnittstelle.** Mastodon nähme vier,
  unser Sender gibt eines mit. Bis dahin bleibt das zweite dem Handbetrieb
  vorbehalten – die Oberfläche sagt es, aber schön ist es nicht.

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
- **Der Bestand kommt aus der Navigation** (2026-08-31): Erst war sie nur ein
  Filter über der Seitenkarte, und angeboten wurde die Schnittmenge – 17
  Kategorien, während der Shop 116 führt. Jetzt ist die Navigation die
  Quelle, gelesen bis in die dritte Ebene, mit mitgezählten Produkten und
  zwölf Stunden Zwischenspeicher.
- **Antworten auf Rückfragen als Projektwissen** (2026-08-31): Beim Antworten
  sagt ein Schalter, ob die Auskunft allgemein gilt oder nur für dieses
  Produkt. Allgemeines geht in jeden weiteren Entwurf mit, Produktwissen nur
  zu seiner Adresse. Anzusehen und zu streichen unter »Gelerntes«.
- **Bilder mit Ablageort, zwei je Beitrag** (2026-08-31): Der Dienst legt sie
  unter `~/Dokumente/POSTKutsche/<jahr>-KW<woche>/<projekt>/` ab, weil der
  Browser den Downloadordner bestimmt und eine Webseite daran nichts ändern
  kann. Eine Fassung trägt jetzt zwei Bilder, beide auf 4:5 zugeschnitten.
- **Kategorien mit mehr als einer Seite** (2026-08-31): Drei von 119 haben
  eine zweite, zusammen zwölf Produkte – alle drei standen vorher bei genau
  30. Gefolgt wird nur, was die Seite selbst verlinkt; »?page=2« zu raten
  geht schief, weil eine Seite, die es nicht gibt, selten mit 404 antwortet.
- **Abbrechen bricht ab** (2026-08-31): Bisher schloss der Knopf nur das
  Fenster – der Lauf lief im Dienst weiter, legte Beiträge an und hielt die
  Sperre. Gemessen: nach dem Anhalten mitten im Lauf standen fünf Beiträge in
  der Ablage und fünf von zehn Produkten galten als beworben. Jetzt hält der
  Lauf zwischen zwei Produkten an und nimmt zurück, was er angelegt hat.
