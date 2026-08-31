[Deutsch](CHANGELOG.md) | [Übersicht](README.md) | [TODO](TODO.md)

# Änderungsprotokoll

Alle nennenswerten Änderungen an POSTKutsche stehen hier.

Das Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionsnummern folgen [Semantic Versioning](https://semver.org/lang/de/).

## [Unveröffentlicht]

### Hinzugefügt

- **Das Gerüst.** SQLite-Ablage für Projekte, gefundene Inhalte, geplante
  Beiträge, Fassungen je Netzwerk und Konten. Kommandozeile zum Einrichten,
  Anzeigen, Anlegen, Pausieren und Löschen von Projekten.
- **Ein Beitrag, mehrere Netzwerke, ein Kärtchen.** Andere Redaktionsplaner
  zeigen denselben Beitrag je Netzwerk einmal an und zwingen einen dazu, die
  Uhrzeiten um eine Minute zu versetzen, damit sich die Kärtchen nicht
  überdecken. Hier hat ein Beitrag mehrere Fassungen und bleibt ein Eintrag.
- **Aktiv und pausiert** als Zustand eines Projekts, getrennt vom Ein- und
  Ausblenden im Kalender. Pausieren hält den Betrieb an und löscht nichts.
- **Zeitrechnung** in `zeiten.py`. In der Ablage steht UTC, angezeigt wird
  Europe/Berlin. Die Monatsgrenzen werden aus der Ortszeit gerechnet, sonst
  fehlte der erste Abend jedes Monats in der Ansicht.
- **Verzeichnis der Netzwerke** mit Farben, Kürzeln, Zeichengrenzen und
  Eigenheiten. LinkedIn steht im dunklen Petrolblau statt im Marken-Blau, weil
  es sonst an einem drei Pixel schmalen Rahmen nicht von Facebook zu
  unterscheiden wäre. Zusätzlich trägt jedes Kärtchen sein Kürzel – auf Farbe
  allein sollte man sich nie verlassen.
- **Sendezeiten** als Terminvorschläge je Netzwerk und Zielgruppe, jeder mit
  Begründung. Für das Handwerk bewusst gegen die gängigen Empfehlungen: halb
  sieben morgens und halb fünf nachmittags statt zehn bis zwölf, weil ein
  Dachdecker um zehn auf dem Dach ist.
- **Quellen** für WordPress (REST-Schnittstelle), Shopware 6 (Store-API) und
  Seiten ohne jede Schnittstelle (Seitenkarte plus Auslesen der Seite).
- **Shopware ohne Zugangsschlüssel.** Ein Shopware-Shop lässt sich auch als
  Seite ohne Schnittstelle lesen: Seitenkarte, Kategorieseiten, `og:`-Angaben.
  Eine einzige Funktion erkennt beide Shopformen; welche der beiden
  Erkennungsregeln gilt, entscheidet die Adresse der Kategorieseite. Weil
  Shopware Produkte flach ablegt und die Seitenkarte nicht verrät, was in
  einer Kategorie liegt, werden die gewünschten Kategorien in der
  Projektdatei genannt; ihre Produkte werden gezählt, indem die Seite gelesen
  wird. Gelesen wird erst ab der Produktliste – über ihr stehen Schieber mit
  Empfehlungen aus dem ganzen Shop, und eine Kategorie mit drei Produkten
  meldete sonst elf.
- **Kampagnen.** Ein Thema, eine Kalenderwoche, ein paar Kategorieadressen –
  daraus entstehen ein bis zwei Beiträge je Tag. Für Shops ist das der
  eigentliche Arbeitsweg: Dort ist kein Produkt »neu«, es wird ausgewählt.
  Wahlweise auf einen Hersteller eingeschränkt, quer durch alle Kategorien.
- **Abbrechen bricht ab und räumt weg.** Während eines Laufs heißt der Knopf
  »Planung abbrechen« und tut das auch: Der Lauf hält zwischen zwei Produkten
  an und nimmt zurück, was er schon angelegt hat. Sonst gälten die
  angefangenen Produkte vier Wochen als beworben, obwohl nie etwas erschienen
  ist. Gesagt wird es dazu – »abgebrochen, 3 Entwürfe entfernt« statt eines
  stillen Verschwindens. Bleibt ein Lauf doch einmal hängen, gilt er nach zehn
  Minuten ohne Lebenszeichen als tot und gibt die Sperre frei.
- **Der Bestand kommt aus der Navigation.** Eine Seitenkarte, die zehn Jahre
  nicht gepflegt wurde, nennt Kategorien, die es nicht mehr gibt, und
  verschweigt welche, die es gibt; wer eine tote ankreuzt, plant eine Woche
  über Ware, die niemand mehr kaufen kann. Zur Auswahl steht deshalb, was die
  Seite selbst verlinkt – bis in die dritte Ebene, denn dort liegt die Ware,
  und die Adressen verraten die Gliederung nicht. Die Produktzahlen werden
  beim Lesen mitgezählt statt aus der Karte übernommen, die Beschriftung aus
  der Navigation sticht den aus der Adresse abgeleiteten Namen, und das
  Ergebnis liegt zwölf Stunden bereit – ein Shop stellt sein Sortiment nicht
  stündlich um. Konfiguratoren und Abholgebiete bleiben draußen: Dahinter
  steht kein Produkt, das man zeigen und verlinken könnte. Und eine Kategorie
  darf mehrere Seiten haben – gefolgt wird nur, was sie selbst verlinkt, denn
  eine Seite, die es nicht gibt, antwortet selten mit 404.
- **Rückfragen.** Wo etwas unklar ist, entsteht kein fertiger Text, sondern
  eine Frage. Beiträge mit offenen Fragen lassen sich nicht freigeben.
- **Beantwortete Rückfragen kommen nicht wieder.** Wer antwortet, sagt mit
  einem Schalter dazu, ob die Auskunft allgemein gilt oder nur für dieses
  Produkt. Allgemeines geht in jeden weiteren Entwurf des Projekts,
  Produktwissen nur zu seiner Adresse – wer beides gleich behandelt, füttert
  Claude nach einem halben Jahr mit dreißig Sonderfällen. Gedeckelt auf
  zwölf Einträge, neueste zuerst, Doppeltes bleibt draußen. In der Anweisung
  steht ausdrücklich, dass dieses Wissen vom Betreiber stammt und nicht
  auszuschmücken ist. Anzusehen und zu streichen unter »Gelerntes« – eine
  Sammlung, die nur wächst und die niemand aufräumen kann, wird nach einem
  halben Jahr zur Last.
- **Bilder mit Ablageort.** Wohin ein Download geht, entscheidet der Browser –
  eine Webseite kann das nicht bestimmen. Also legt der Dienst die Bilder
  selbst unter `~/Dokumente/POSTKutsche/` ab, nach Kalenderwoche und Projekt
  geordnet, damit sich eine Woche in einem Handgriff wegräumen lässt. Wie der
  Dokumentenordner heißt, wird beim System erfragt und nicht geraten. Der
  Knopf zum Herunterladen bleibt daneben; das Ablegen kommt dazu.
- **Zwei Bilder je Beitrag.** Beide auf 4:5 zugeschnitten, in fester
  Reihenfolge – das erste ist, was in der Vorschau erscheint. Im Handbetrieb
  stehen sie einzeln benannt zum Herunterladen bereit. Über die
  Schnittstelle geht nur das erste raus, und die Oberfläche sagt das, statt
  das zweite stillschweigend fallenzulassen.
- **Schutz vor verlorener Handarbeit.** Ein von Hand bearbeiteter Text wird
  nicht überschrieben, wenn man »neu schreiben lassen« drückt – erst nach
  ausdrücklicher Bestätigung.
- **Wiederholungen.** Ein veröffentlichter Beitrag lässt sich erneut in den
  Kalender stellen. Der alte bleibt mit seinem Sendedatum stehen, der neue ist
  ein Entwurf mit übernommenen Texten; die Kette zeigt immer auf den Urahn, so
  dass die Zahl der Runden ohne Hangeln ablesbar ist.
- 435 Tests.

### Erscheinungsbild

- **Name.** Aus »Sendeplan« wurde **POSTKutsche** – geschrieben wie
  NEXTBookmarks und NEXTStatus, mit großem Wortanfang. Umbenannt wurden
  Repository, Python-Paket, Befehl, Konfigurationsordner und Doku.
- **Icon und Banner.** Eine Concord-Kutsche, weiß auf blau, in den Größen 16
  bis 512. Banner fürs README in hell und dunkel, je drei Breiten; erzeugt von
  `werkzeuge/banner.py`, damit die sechs Dateien nicht auseinanderlaufen.
- **Alle Größen zeigen dieselbe Kutsche.** Für 16 und 32 Pixel gab es
  zwischenzeitlich eine eigene, gröbere Zeichnung – bei Icons ist das der
  Normalfall, weil feine Formen dort zu einem Fleck werden. Verworfen: Die
  reduzierte Fassung zeigte eine *andere* Kutsche, und zwei Kutschen für ein
  Programm sind schlimmer als ein unscharfes Zeichen im Browser-Tab.
- **Gemeinsame Farbpalette** aus MailBurg, in `assets/farben.md` erklärt und in
  `postkutsche/farben.py` als Werte hinterlegt. Beide Dateien sind zum Kopieren
  in andere Projekte gedacht. `als_css()` erzeugt daraus die CSS-Variablen der
  Weboberfläche – eine zweite, von Hand gepflegte Liste wiche irgendwann ab.

### Behoben

- **Ein Farbton der übernommenen Palette war unlesbar.** `GRAU_MITTE`
  (`#97a1ad`) erreicht auf hellem Grund nur 2,48 Kontrast und verfehlt damit
  sogar die 3,0, die WCAG für große Schrift verlangt. Das sieht man einem
  Farbwert nicht an; aufgefallen ist es, weil `tests/test_farben.py` es
  nachrechnet. Für hellen Grund gibt es jetzt `GRAU_LEISE` (`#667080`, 4,75).

### Sicherheit

- **Keine echten Adressen im Repository.** Die eigenen Seiten, Artikeladressen
  und Hersteller stehen in `~/.config/postkutsche/`, nicht im Quelltext. Im
  Repository liegen nur Beispiele unter `.example` – eine Endung, die nach
  RFC 2606 für genau diesen Zweck reserviert ist. `test_keine_echten_adressen.py`
  prüft von der anderen Seite: Jede Adresse im Repository muss entweder unter
  `.example` liegen oder in einer kurzen, offenen Liste stehen.
- **Zugangstoken stehen nicht in der Datenbank.** Sie gehören in den
  Schlüsselbund, ersatzweise in eine Datei mit Rechten 600. Ein Test verbietet
  Spalten mit »token«, »passwort« oder »secret« in der Tabelle `konten`.

### Entschieden

- **Keine Videos** (2026-08-28). Aus Bildern kleine Filme zu machen war der
  ursprüngliche Wunsch. Gestrichen, bevor eine Zeile dafür geschrieben war.
- **Keine Preise in den Beiträgen** (2026-08-28). Ein Preis ändert sich, der
  Beitrag bleibt stehen – aus einem alten Beitrag würde sonst schnell der
  Vorwurf, mit falschen Preisen geworben zu haben.
- **Facebook und Instagram vorerst von Hand** (2026-08-28). Metas App-Prüfung
  dauert Wochen und ist ungewiss. Das Werkzeug legt Text und zugeschnittenes
  Bild fertig zum Kopieren bereit; ob die Schnittstelle später überhaupt
  gebraucht wird, entscheidet sich im Betrieb.
- **Claude über `claude -p`** statt über die Anthropic-API. Nutzt ein
  vorhandenes Abo, keine Kosten je Beitrag. Der API-Weg bleibt als zweiter
  Hintergrund hinter derselben Schnittstelle vorgesehen.
- **Weboberfläche statt Fensterprogramm.** Ein Kalender mit Ziehen und Ablegen
  ist im Browser einfacher sauber zu bauen, sieht auf Arch und Debian gleich
  aus und ist später vom Handy aus erreichbar.

### Was beim Anbinden echter Seiten auffiel

Diese Eigenheiten stehen als Kommentar an der Stelle im Quelltext, an der sie
zählen – hier zur Übersicht, weil sie mehr über fremde Systeme sagen als über
POSTKutsche:

- **Nicht jedes WordPress pflegt Beitragsbilder.** Es gibt Blogs, bei denen
  `featured_media` durchgehend 0 ist, obwohl jeder Beitrag ein Bild im Text und
  in `og:image` hat. Wer sich auf `wp:featuredmedia` verlässt, kann für solche
  Seiten nie auf Instagram veröffentlichen. Deshalb drei Stufen: Beitragsbild,
  erstes Bild im Text, `og:image`.
- **Zweisprachige Seiten liefern jeden Beitrag doppelt** – etwa deutsch und
  englisch unter `/en/`, auf die Sekunde gleich datiert. Ohne Filter stünde
  jeder Beitrag zweimal im Kalender und ginge zweimal raus.
- **`date_gmt` kommt ohne Zonenkennzeichen.** »2026-08-27T15:00:00« ist bereits
  UTC, sieht aber aus wie Ortszeit; wer das übersieht, verschiebt jeden Beitrag
  um ein bis zwei Stunden.
- **`lastmod` in Seitenkarten ist oft wertlos.** Es gibt Karten, in denen
  mehrere tausend Adressen dasselbe Datum tragen – das der letzten Umstellung,
  vor über zehn Jahren.
- **Instagram nimmt keine Bilddatei entgegen.** Meta lädt das Bild selbst von
  einer öffentlich erreichbaren Adresse. Zugeschnittene Bilder brauchen deshalb
  einen Platz im Netz; die anderen drei Netzwerke nehmen normale Uploads.
