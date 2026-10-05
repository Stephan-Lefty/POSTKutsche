[Deutsch](CHANGELOG.md) | [Übersicht](README.md) | [TODO](TODO.md)

# Änderungsprotokoll

Alle nennenswerten Änderungen an POSTKutsche stehen hier.

Das Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionsnummern folgen [Semantic Versioning](https://semver.org/lang/de/).

## [Unveröffentlicht]

### Hinzugefügt

- **Das Tipp-Archiv bekommt eigene Seiten** (2026-10-05). Jeder ablaufende
  Tipp wird zu einer eigenen Seite unter `/tipp-archiv/` – mit eigenem Titel,
  eigener Beschreibung und eigenem Canonical. Daneben entsteht eine
  chronologische Übersicht, in der nichts gelöscht wird. Unten auf der
  Tipp-Seite stehen weiterhin die jüngsten Wochen, jetzt zweispaltig und mit
  zwei Sätzen Anriss; darunter führt ein Verweis ins Archiv.

  Den Reiter am linken Seitenrand erbt die Archivseite aus der Übersicht, die
  ohnehin abgerufen wird. Nachgebaut wird er nicht: Farben, Haltepunkte und
  Text gehören zum Auftritt, nicht ins Programm.

  Die Kurzfassung für den Anriss wird aus der `meta description` der Seite
  zurückgelesen. Wenn ein Tipp abläuft, sind die Daten, aus denen er entstand,
  längst weg – sie dort abzuholen ist der einzige Weg ohne doppelte Pflege.

### Behoben

- **Erfundene Dienstleistungen** (2026-10-05). Die Anweisung verbot zwar
  Versprechen zu Verfügbarkeit und Eignung, sagte aber nichts dazu, ob der
  Absender montiert, Aufmaß nimmt oder vor Ort kommt. Beim ersten Betreiber -
  einem reinen Versandhandel - stand prompt »wir bauen ein, nehmen Aufmaß« im
  Text. Wo Selbermachen aufhört, heißt es jetzt »eine Fachfirma«, nicht
  »wir«. Weil beide Längengrenzen der Anweisung eng sind, wurde die Regel mit
  der verwandten zusammengezogen statt angebaut.

- **Die Grafik im Tipp stand links statt mittig** (2026-10-05). `img-responsive`
  setzt `display:block`, und auf einem Blockelement wirkt das `text-center`
  des Absatzes nicht mehr. An der fertigen Seite gemessen: 15 px Rand links,
  515 px rechts. Es fehlte `center-block` daneben.

### Geändert

- **Firefox steht jetzt in den Voraussetzungen** (2026-10-05). Ohne ihn
  entstehen keine Wochengrafiken – das stand bisher nur in den Notizen zum
  Quelltext, nicht dort, wo jemand nachsieht, der POSTKutsche einrichtet.
  Die beiden Wochenformate fehlten überhaupt in der Übersicht; sie sind
  nachgetragen, deutsch wie englisch.

- **Aus Archivkacheln werden Archivseiten** (2026-10-05). Bisher öffnete ein
  Archiveintrag die Grafik der Woche in einem neuen Reiter, und nach fünf
  Wochen verschwand der Tipp. Das war sparsam zu pflegen und für Google
  wertlos: Was nicht mehr da ist, kann nicht gefunden werden. Der Einwand
  gegen Unterseiten – »die niemand mehr durchsieht« – ist erledigt, weil die
  Seiten jetzt von selbst entstehen.

  Der Schnellzugriff auf der Tipp-Seite fasst noch vier statt fünf Wochen.
  Wer herausfällt, bleibt im Archiv stehen. Das Vorschaubild sitzt neben dem
  Anriss statt darüber: Die Grafiken sind querformatig und nähmen sonst halbe
  Seitenbreite ein.

- **Tipp und Produkt der Woche** (2026-09-29). Zwei wöchentliche Formate, die
  aus einer einzigen Eingabe Text *und* Grafik liefern: beim Produkt aus einem
  Verweis in den Shop, beim Tipp aus einem Thema. Die Grafik entsteht im
  Hausstil, quer für Facebook und LinkedIn, hoch für Instagram – Instagram
  bekommt eine eigene Anordnung statt eines Mittenzuschnitts, der genau die
  Preisbox wegschnitte. Beide Formate teilen dasselbe Gerüst, damit man den
  Absender erkennt, bevor man ein Wort liest.
- **Der Tipp der Woche schreibt die Webseite fort** (2026-09-29). Aus
  demselben Lauf entsteht eine fertige HTML-Datei: der Tipp ausführlich, die
  Grafik anklickbar im Text, ein Merksatz, passende Artikel als Kästchen mit
  Bild. Der bisherige Tipp wandert als Kachel ins Archiv – die Grafik trägt
  ihn schon in Kurzform, sie noch einmal in Worte zu fassen hieße, dasselbe
  zweimal zu pflegen. Von jeder Grafik entsteht eine verkleinerte Fassung
  (gemessen: 380 kB werden zu 50 kB); gezeigt wird die kleine, ein Klick
  öffnet die große. Hochgeladen wird von Hand, und der Hinweis danach nennt
  Zielpfad und Rechner.
- **Ein Alternativtext zu jeder Grafik.** Die ganze Aussage steckt im Bild;
  wer einen Vorleser benutzt, bekäme sonst nichts. Er entsteht aus denselben
  Feldern wie das Bild und kostet deshalb nichts extra.
- **Preise aus dem Auszeichnungsfeld** (`itemprop="price"`), nie aus dem
  Fließtext. Gemessen an einer echten Produktseite: Dort stand im Fließtext
  ein Preis von 1.329 €, der zu einem Artikel aus der Empfehlungsliste
  daneben gehörte, während das Produkt 959 € kostete. Fehlt die Auszeichnung,
  entsteht kein Beitrag – eine Anzeige mit falschem Preis ist schlimmer als
  keine Anzeige.
- **Das Angebotsende wird gerechnet, nicht getippt.** Ein Angebot der Woche
  läuft Montag bis Sonntag; `zeiten.wochenschluss` liefert den Sonntag 23:59
  der jeweiligen Woche, auch über die Zeitumstellung hinweg.
- **`marken.json` für den Auftritt nach außen.** Logo, Rufnummer, Mailadresse
  und die Kurzvorstellung stehen unter `~/.config/postkutsche/`, nicht im
  Repository – ein Logo ist eine eingetragene Marke, eine Rufnummer ein
  Kontaktdatum, und die Versionsgeschichte vergisst nichts. Mehrere Projekte
  teilen sich einen Auftritt über `{"wie": "anderekennung"}`.


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
- **Die Wochenplanung kann auch Blogs.** Bisher stand im Planungsfenster
  »Blog – Beiträge kommen von selbst, keine Kampagne«, und die beiden
  WordPress-Projekte waren gesperrt. Das stimmte für neue Beiträge, half aber
  niemandem, der einen halbjährigen Text noch einmal aufgreifen wollte. Jetzt
  liefert WordPress seine Kategorien selbst – ein Abruf statt einer Erhebung
  über hundert Seiten –, und daraus wird eine Woche geplant wie bei einem
  Shop. Ein Beitrag, der in zwei gewählten Kategorien steht, kommt trotzdem
  nur einmal vor.
- **Ein Blogbeitrag wird anders beworben als eine Tür.** Claude bekommt dafür
  eigene Regeln: Der Beitrag ist das Ziel, nicht die Ware; erzähl nicht alles,
  sonst nimmt sich der Text den eigenen Anlass; und nenne einen Beitrag vom
  März nicht »neu« – das Erscheinungsdatum steht jetzt in der Anweisung. Dazu
  die Ansage, dass ein gekürzter Quelltext keine Rückfrage wert ist.
- **Zu lange Blogbeiträge werden gekürzt, aber nur an Absatzgrenzen.**
  Gemessen: bis 15.200 Zeichen, im Mittel 5.600. Für einen Beitrag mit 500
  Zeichen bringt der Rest nichts und macht die Anweisung teuer. Mitten im Wort
  abzuschneiden wäre schlimmer als zu kürzen – das hat schon einmal reihenweise
  Rückfragen erzeugt.
- **Die Anzahl in der Auswahl zählt, was planbar ist.** Bei einem
  zweisprachigen Blog zählt WordPress die englischen Fassungen mit: DialOS
  meldete 16 Beiträge, planbar sind acht. Wer daraufhin zwei Beiträge am Tag
  einplant, bekommt eine halb leere Woche und erfährt den Grund nicht. Wo ein
  Sprachfilter eingetragen ist, wird deshalb nachgezählt.
- **Vier Wege zum Text statt einem.** Bisher hing alles an `claude -p`: kein
  Claude Code, kein Beitrag. Jetzt stehen daneben jeder Dienst in der
  OpenAI-Form (Ollama auf dem eigenen Rechner, LM Studio, OpenRouter,
  DeepSeek, ChatGPT – ein Modul für alle, sie unterscheiden sich in Adresse,
  Modell und Schlüssel, nicht in der Anfrage), die Anthropic-Schnittstelle
  mit eigenem Schlüssel für Maschinen ohne Claude Code, und »von Hand«.
  **Einstellbar je Projekt**, damit der eine Blog von Hand geschrieben wird,
  während der Shop weiterläuft. Eingerichtet wird das mit `postkutsche
  denker`; Schlüssel gehen den Weg, den die Token schon gehen – Schlüsselbund,
  ersatzweise 600er-Datei, nie in die Datenbank.
- **Ohne Fremdpakete, auch hier.** Weder `anthropic` noch `openai` noch
  `requests`: `urllib` kann POST mit JSON. Was die beiden Schnittstellen
  gemeinsam haben, steht in `denker/netz.py` – samt Übersetzung der
  Fehlercodes in Sätze, die weiterhelfen. »Der Zugangsschlüssel wurde nicht
  angenommen (401)« sagt mehr als »HTTP Error 401«.
- **Von Hand heißt nicht leer.** Titel und Anriss stehen im Entwurf, gekürzt
  an Satzgrenzen auf das, was das Netzwerk zulässt. Ein Gerüst schreibt sich
  leichter um als ein leeres Feld.
- **Einen Beitrag selbst in den Kalender stellen.** Bisher entstand ein
  Beitrag nur aus einem abgerufenen Inhalt oder aus der Wochenplanung – für
  Betriebsferien, einen Dank oder einen Termin gab es keinen Weg hinein.
  »Beitrag von Hand« sagt vorher dazu, wer den Text schreiben wird. Klemmt
  der Dienst, entsteht der Beitrag trotzdem: Der Termin ist das Wichtigere,
  der Text lässt sich tippen.
- **Eine Bedienungs- und eine Installationsanleitung**, beide zweisprachig
  unter `docs/`. Die Bedienung zeigt fünf Bilder der Oberfläche; die
  Installation geht den Weg von der leeren Maschine bis zum laufenden
  Zeitgeber, mit allem, was bisher nur im Quelltext stand – Claude anbinden,
  Mastodon-Rechte, systemd, Ablageorte. In der linken Spalte steht jetzt ein
  Verweis auf die Anleitung: Wer nicht weiterkommt, sucht im Programm.
- **Die Bilder der Anleitung entstehen per Skript**
  (`werkzeuge/anleitungsbilder.py`). Von Hand geschossene Bildschirmfotos
  veralten mit der ersten Änderung, und niemand weiß später, welcher
  Ausschnitt in welcher Größe gezeigt wurde. Aufgenommen wird eine eigens
  angelegte Ablage mit erfundenen Projekten – **die eigene Ablage kommt nicht
  ins Bild**, dafür zeigt `POSTKUTSCHE_CONFIG` beim Aufnehmen auf einen leeren
  Ordner. Das Planungsfenster bekommt seine Kategorien von einer Kulisse, die
  WordPress spielt; ein Bild, das »nicht erreichbar« zeigt, wäre als Anleitung
  wertlos.
- **Ausgeblendete Projekte bleiben ausgeblendet.** Wer nur an Naturlust
  arbeitet, blendet die vier anderen aus – und hatte sie nach dem nächsten
  Neuladen alle wieder vor sich. Gemerkt werden die *ausgeblendeten*
  Projekte, nicht die sichtbaren: Ein Projekt, das später dazukommt, soll
  sichtbar sein und nicht heimlich fehlen, weil es in der alten Liste nicht
  stand. Die Merkliste liegt im Browser, gilt also je Rechner und Browser.
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

- **Eine abgelaufene Claude-Anmeldung sah aus wie ein Programmfehler.**
  Scheitert `claude -p`, bleibt die Fehlerausgabe leer und der Grund steht am
  Ende eines langen Hüllobjekts auf der normalen Ausgabe. Weitergereicht und
  auf 300 Zeichen gekürzt wurde davon genau der nutzlose Anfang – die
  Oberfläche zeigte eine Wand aus Zählerständen, alle auf null. Der Grund wird
  jetzt zuerst ausgepackt. Und erkannt wird die abgelaufene Anmeldung auch,
  wenn sie sich »Failed to authenticate: OAuth session expired« nennt und das
  Wort »login« gar nicht enthält – bisher wurde nur danach gesucht.
- **Beim Start wird nachgesehen, ob der Denker antwortet.** Bisher fiel eine
  abgelaufene Anmeldung erst mitten in einer Wochenplanung auf. Jetzt steht
  beim Hochfahren auf der Konsole, wer schreibt und ob er antwortet, und in
  der Oberfläche erscheint eine rote Leiste unter dem Kopf, solange er es
  nicht tut – samt Abhilfe. Geprüft wird nebenher: Der Kalender soll aufgehen
  und nicht warten, und ohne Denker kann man ihn lesen, freigeben und senden.
  Der Prüfstand hält eine Viertelstunde, damit nicht jeder Seitenaufruf eine
  Anfrage kostet. »Noch nicht geprüft« wird dabei streng von »geht nicht«
  unterschieden – eine Warnung, die sich Sekunden später selbst widerruft,
  lernt man zu übersehen.
- **Die Startmeldungen kamen unter systemd nie an.** `print()` puffert
  blockweise, sobald die Ausgabe nicht an einem Terminal hängt; bei vier
  Zeilen heißt das: Im Journal steht nichts. Aufgefallen beim Nachsehen der
  neuen Startmeldung, die genau deshalb fehlte.
- **Auf einer frisch gestarteten Maschine sperrte ein toter Kampagnenlauf.**
  Ein Lauf ohne Zeitstempel sollte als tot gelten; gerechnet wurde aber mit
  einer Null, und `time.monotonic()` zählt ab dem Hochfahren. Nach Wochen
  Laufzeit ergab das »tot«, zwölf Sekunden nach dem Start »läuft« – »Woche
  planen« wäre dann bis zu zehn Minuten gesperrt gewesen. Aufgefallen ist es
  nicht hier, sondern in der CI, wo jeder Läufer frisch hochfährt.
- **Claude Code nimmt jetzt auch einen hinterlegten Zugang.** Bisher hing der
  Weg `kommando` allein an der Anmeldung auf der Maschine – und die läuft ab.
  Für einen Dienst, hinter dem niemand sitzt, war das untauglich: Alle paar
  Tage von Hand anmelden geht unter systemd nicht. `claude setup-token` legt
  einen Zugang an, der ein Jahr gilt; `postkutsche denker schluessel kommando`
  legt ihn in den Schlüsselbund, ersatzweise nach `zugaenge.json` mit Rechten
  600 – dieselbe Ablage wie für die Netzwerke, also nicht in die Datenbank und
  nicht in die systemd-Einheit. Weitergereicht wird er über die Umgebung des
  Kindprozesses, nicht über die Befehlszeile: Was dort steht, liest jeder mit
  `ps`. Ohne hinterlegten Zugang gilt weiter die Anmeldung auf der Maschine.
- **»denker pruefen« meldete »Antwortet«, ohne gefragt zu haben.** Für den Weg
  `kommando` sah die Prüfung nur nach, ob `claude` im Suchpfad liegt. Eine
  abgelaufene Anmeldung sieht man der Datei nicht an, also ging der Lauf los
  und scheiterte beim ersten Text. Jetzt stellt auch dieser Weg eine winzige
  Anfrage, so wie `offen` und `anthropisch` es schon taten.
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
