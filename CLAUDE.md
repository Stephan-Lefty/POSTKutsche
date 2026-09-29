# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-09-29)

686 Tests. Neu sind zwei wöchentliche Formate mit eigener Grafik: »Produkt
der Woche« aus einem Shoplink, »Tipp der Woche« aus einem Thema. Beide sind
im Kalender als Menüpunkt eingehängt, beide erzeugen Text *und* Bild, und
beide laufen echt durch – am 2026-09-29 sind der erste Produktbeitrag und der
erste Tipp entstanden und die Webseite dazu ist online.

**Drei neue Module.** `grafik.py` zeichnet mit HTML und CSS, ausgegeben von
Firefox im Kopflosbetrieb. `wochenformat.py` hält den Ablauf zusammen: lesen,
schreiben lassen, zeichnen, in den Kalender. `tippseite.py` schreibt die
Seite `Tipp-der-Woche.html` fort.

**Ein Gerüst, zwei Füllungen.** Beide Formate teilen Logofeld, Fotospalte,
Kastenspalte, Aufruf, Merkmalszeile und Kontakt – das ist der Zweck, nicht
Sparsamkeit: Wer sie nebeneinander sieht, soll denselben Absender erkennen.
Der Rahmen steht deshalb *einmal* in `grafik._seite`. Zwei Vorlagen driften
auseinander, sobald an einer etwas geändert wird.

**Was aus der Seite kommt und was aus dem Modell.** Der Preis kommt
ausschließlich aus `itemprop="price"`, nie aus dem Fließtext: Auf einer
echten Produktseite stand dort 1.329 €, gehörend zu einem Artikel aus dem
Empfehlungsschieber daneben – das Produkt kostete 959 €. Fehlt die
Auszeichnung, entsteht **kein** Beitrag; hier wird abgebrochen statt geraten,
denn eine Anzeige mit falschem Preis ist schlimmer als keine Anzeige. Ebenso
fest: Ersparnis (gerechnet), Angebotsende (`zeiten.wochenschluss`, Montag bis
Sonntag) und die Blockfarben des Tipps. Wer die Farbe erfinden lässt, bekommt
jede Woche eine andere und verliert genau den Wiedererkennungswert, für den
das Gerüst gebaut ist.

**Drei Fehler, die erst der echte Lauf zeigte** – alle drei hätten sich
wöchentlich wiederholt:

- **Instagram fragte nach einem Bild**, obwohl die Grafik aus denselben
  Feldern gerade erst entsteht. Die Grundregel ist im Regelfall richtig, hier
  falsch, und eine offene Rückfrage sperrt die Freigabe. Steht jetzt als
  `vorlagen.BILD_ENTSTEHT` in beiden Wochenanweisungen.
- **Der Tipp brach auf einem fehlenden Schlüssel »farbe« ab.** Die Tests
  davor liefen alle mit abgeschaltetem Browser und erzeugten die Seite nie –
  deshalb gibt es jetzt `test_grafik.py`, das die Seite wirklich baut.
- **Der Preis stand dunkel auf dunkel.** Die Preisbox liegt in der weißen
  Karte und erbte deren Schrift. Sieht man nur, wenn man rendert.

**Firefox ist Kür.** Fehlt er, entsteht der Beitrag trotzdem, nur ohne Bild
und mit einer Meldung. Zwei Eigenheiten, die Zeit gekostet haben: Ein
laufender Firefox blockiert `--screenshot` (»is already running«) – jeder
Lauf bekommt deshalb ein eigenes Profil in einem Wegwerfordner. Und
`--screenshot` löst beim `load`-Ereignis aus: Was das Bild braucht, muss
lokal neben der HTML liegen, sonst knipst es in eine halbfertige Seite.

**Die Hausschrift ist DejaVu Sans Condensed**, Rückfall Nimbus Sans Narrow.
Nicht die schönste, aber die einzige, die überall liegt – eine Schrift, die
nachinstalliert werden muss, macht die Ausgabe auf einem anderen Rechner und
in der CI kaputt. Sie läuft breiter als andere: Beim Umstellen lief prompt
alles ineinander, beide Layouts sind auf sie hin durchgerechnet.

**`marken.json` hält das Auftreten nach außen** – Logo, Rufnummer,
Mailadresse, Kurzvorstellung, Adresse der Tipp-Seite. Unter
`~/.config/postkutsche/`, nicht im Repository: Ein Logo ist eine eingetragene
Marke, eine Rufnummer ein Kontaktdatum, und die Versionsgeschichte vergisst
nichts. Mehrere Projekte teilen sich einen Auftritt über
`{"wie": "anderekennung"}` statt über Kopien, die auseinanderlaufen.

**Die Tipp-Seite trägt ihre eigene Pflegeanleitung im Kopf**, und die ist die
Spezifikation: aktuellen Tipp ersetzen, bisherigen ins Archiv, Titel,
Beschreibung und beide Datumsangaben nachziehen, fünf Wochen stehen lassen.
Gearbeitet wird mit Textersatz an benannten Marken, nicht mit einem Parser –
ein Parser formatiert Stellen um, die niemand angefasst hat, und danach sieht
man im Vergleich nicht mehr, was sich wirklich geändert hat. Das
auskommentierte Muster im Archiv wird ausgelassen; es sieht einem Eintrag zum
Verwechseln ähnlich. Wird innerhalb derselben Woche nachgebessert, wird
ersetzt statt archiviert, sonst steht dieselbe KW zweimal auf der Seite.

**Das Archiv zeigt die Grafiken der Vorwochen als Kacheln**, nicht
Kurzfassungen: Die Grafik trägt den Tipp schon, sie noch einmal in Worte zu
fassen hieße, dasselbe zweimal zu pflegen. Damit bleibt ein alter Tipp
lesbar, ohne dass Unterseiten entstehen, die niemand mehr durchsieht.

**Hochgeladen wird von Hand**, wie bei Facebook und Instagram. Die fertige
Seite und die Grafiken liegen im Wochenordner; die Meldung nennt Zielpfad und
Rechner. Eine blaue Leiste im Kalender prüft die Seite im Netz und meldet
sich, solange dort eine ältere Kalenderwoche steht – das deckt beides ab, den
fehlenden Tipp und die nicht hochgeladene Datei.

**POSTKutsche passt auf einen Stick** (`uebergabe.py`, `postkutsche umziehen`,
`werkzeuge/postkutsche-tragbar.sh`). `POSTKUTSCHE_ORDNER` legt Ablage,
Einstellungen und Dokumente unter ein Dach; das Startskript setzt die
Variable auf seinen eigenen Fundort, damit der Einhängepfad gleich sein
kann. Auf dem Datenträger liegt alles unter `POSTKutsche/`, damit er für
anderes brauchbar bleibt – und daran wird er auch erkannt, nicht an seinem
Namen.

**Keine Synchronisation, eine Übergabe.** Zwei SQLite-Dateien lassen sich
nicht zusammenführen; wer an zwei Orten arbeitet, verliert eine Seite. Also
ist zu jedem Zeitpunkt genau ein Ort der gültige, die Oberfläche sagt
welcher, und ein Überschreiben neuerer Arbeit fragt nach. Innerhalb von zwei
Minuten gelten zwei Stände als gleich – sonst meldete die Zeile direkt nach
dem Kopieren, die Zielseite sei neuer.

Drei Dinge, die beim Bauen schiefgingen und nicht wieder aufzurollen sind:
In der Ablage stehen **absolute Bildpfade**, die nach einem Umzug ins Leere
zeigen – `bilder.wiederfinden` sucht dann den Dateinamen im aktuellen
Ordner. Die **Feldcodes der Desktop-Norm** (`%k`) werden in Anführungszeichen
nicht ersetzt, ein Doppelklick tat deshalb gar nichts; der Pfad steht jetzt
fest und wird bei jedem Start nachgezogen. Und **das Programm wandert nicht
mit** – nur die Daten. Wo der Quelltext liegt, steht in `programm.txt`.

**Die Wochen im Kalender sind Klappfächer.** Offen ist nur die laufende;
kommende werden beim Scrollen nachgeladen und wären sonst ebenfalls offen,
womit die aufgeklappte Woche wieder schrumpfte. Die Zellenhöhe rechnet mit
`--offene-wochen`, das JavaScript setzt sie. Damit bleiben die Titel
vollständig: Wer Platz braucht, klappt zu, statt dass Text wegfällt.

**Offen:** Das Archiv ist ungetestet im Betrieb – die erste Kachel entsteht
erst mit KW 41. Der Merksatz kam bisher von Hand; ab dem nächsten Tipp
verlangt ihn die Anweisung. Und die Projektpalette ist mit sieben Projekten
aufgebraucht: `tipp-woche` und `produkt-woche` liegen farblich nah am
HaBeFa-Shop.

## Hier war Schluss (Stand 2026-09-28)

601 Tests. Die Kette läuft ganz durch: Quelle findet ein Produkt, ein Modell
schreibt die Fassungen, der Kalender zeigt sie, Mastodon sendet, Facebook und
Instagram gehen über den Handbetrieb. Ein Beitrag ist echt erschienen.

**Am 2026-09-28: Ein ganzer Tag an einer Meldung.** Die Oberfläche zeigte bei
einer Rückfrage eine Wand aus Zählerständen, alle null. Dahinter steckte eine
abgelaufene Claude-Anmeldung – aber die Meldung sagte es nicht: Scheitert
`claude -p`, bleibt die Fehlerausgabe leer, der Grund steht am Ende eines
langen Hüllobjekts auf der *normalen* Ausgabe, und die Kürzung auf 300 Zeichen
traf genau ihn. Drei Dinge daraus, die man nicht wieder aufrollen muss:

- **Die Anmeldung der Claude-Anwendung ist nicht die der Kommandozeile.**
  `claude auth status` fragen, nicht vermuten. `claude auth login` meldet an,
  `claude setup-token` legt einen Zugang für ein Jahr an – der gehört in den
  Schlüsselbund (`postkutsche denker schluessel kommando`), nicht in die
  systemd-Einheit. Er geht als `CLAUDE_CODE_OAUTH_TOKEN` über die Umgebung
  des Kindprozesses; auf der Befehlszeile läse ihn jeder mit `ps`.
- **`erreichbar` heißt antworten, nicht installiert sein.** Für `kommando`
  wurde nur der Suchpfad abgesucht – einer Datei sieht man die abgelaufene
  Anmeldung nicht an. Jetzt stellt auch dieser Weg eine winzige Anfrage, wie
  `offen` und `anthropisch` es längst taten.
- **Beim Start wird nachgesehen**, nebenher und mit einem Prüfstand, der eine
  Viertelstunde hält. Antwortet niemand, steht es auf der Konsole und als
  rote Leiste unter dem Kopf. »Noch nicht geprüft« ist streng von »geht
  nicht« getrennt: Eine Warnung, die sich Sekunden später selbst widerruft,
  lernt man zu übersehen.

**Zwei Fehler, die nur zufällig am selben Tag auffielen.** `time.monotonic()`
zählt ab dem Hochfahren: Ein Kampagnenlauf ohne Zeitstempel galt deshalb auf
einer frisch gestarteten Maschine als »läuft« und sperrte »Woche planen« bis
zu zehn Minuten. Lokal war der Test grün, weil dieser Rechner lange läuft –
rot wurde er erst in der CI. Und `print()` puffert blockweise, sobald die
Ausgabe kein Terminal ist; unter systemd stand im Journal nichts. Beides
behoben, beides mit einem Test, der nicht vom Rechner abhängt.

**Am 2026-08-31 angebunden:** Die beiden Shopware-Shops stehen jetzt als Art
`seitenkarte` und sind unter »Woche planen« wählbar. Ihre Kategorien stehen
unter `kategorien` in `~/.config/postkutsche/projekte.json`, weil die
Seitenkarte bei Shopware nicht verrät, was in einer Kategorie liegt.
Dabei aufgefallen: Über der Produktliste stehen Schieber mit Empfehlungen aus
dem ganzen Shop. Eine Kategorie mit drei Produkten meldete elf, und weil die
Schieber oben stehen, wären genau die falschen in der Kampagne gelandet.
Gelesen wird deshalb erst ab dem Baustein `cms-element-product-listing`.

**Am letzten Abend gefunden und behoben:** Claude bekam von einer Produktseite
nur die `og:description` zu lesen – 172 Zeichen Werbung, während daneben 2.800
Zeichen Fachtext standen. Daher kamen die vielen Rückfragen. Und die
Seitenkarte des ersten Shops ist veraltet: von zwölf Adressen führte keine
unverändert zum Ziel, eine als »Stahltür« benannte landete auf der Übersicht
für Holztüren.

**Die Navigation ist die Quelle, nicht der Filter.** Für die Kategorienliste
des Planungsfensters ist die Seitenkarte des ersten Shops unbrauchbar: Sie
verschweigt 57 Kategorien, die es gibt, und führt 115, die es nicht mehr gibt
(»Passivhaustüren«, angeblich 40 Produkte). Erst wurde sie deshalb gegen die
Navigation *geprüft* – das war zu wenig, denn wer zwei Quellen schneidet,
bekommt das Schlechteste aus beiden: 17 Kategorien statt 116. Gelesen wird
jetzt allein, was die Seite selbst verlinkt. Sie ist der Rückfall, wenn die
Seite schweigt.

**Auch die Produkte einer Kampagne kommen von der Kategorieseite**, nicht aus
der Karte – das war schon immer so, stand aber nirgends. Am 2026-08-31
nachgemessen, weil die Vermutung im Raum stand: Von 60 Adressen, die nur die
Karte kennt und die Navigation nicht verlinkt, leben **sieben**. Die Karte
zusätzlich heranzuziehen würde den Vorrat zu knapp der Hälfte mit toten
Adressen füllen, und jede kostet beim Planen einen Platz in der Woche –
`ausfuehren` wählt genau `anzahl` und sucht für ein gescheitertes keinen
Ersatz. Eine einzelne Kategorie (`t30-1_brandschutztueren_aluminium_576`)
sah anders aus: Dort leben alle fünf, die nur die Karte kennt. Sie ist die
Ausnahme, nicht die Regel. Für das Erkennen neuer Seiten
(`entwerfen.inhalte_holen`) bleibt die Karte die einzige Quelle, die etwas
über den ganzen Shop sagt.

**Eine Kategorie kann mehrere Seiten haben.** Drei von 119 haben eine zweite,
zusammen zwölf Produkte; alle drei standen vorher bei genau 30. Gefolgt wird
nur, was die Seite selbst verlinkt – »?page=2« zu raten geht schief, weil
eine Seite, die es nicht gibt, selten mit 404 antwortet.

**Der Shop ist dreistufig, obwohl seine Adressen flach sind.** Alles liegt
unter `/shop-<bereich>/<name>_<nummer>/`, die Gliederung hat aber Bereich,
Kategorie und Unterkategorie. Startseite plus die drei Bereichsseiten nennen
73 Kategorien; 16 der Kategorieseiten darunter verlinken 54 weitere, die
sonst nirgends stehen – darunter die T30-1-Zweige, in denen die Ware liegt.
Wer nur vier Seiten liest, übersieht zwei Drittel des Sortiments.

**Deshalb 132 Abrufe, acht gleichzeitig, und zwölf Stunden Zwischenspeicher**
in `~/.local/share/postkutsche/bestand/`. Einmal am Morgen zwanzig Sekunden
warten, danach geht das Formular sofort auf. Die Produktzahlen werden dabei
mitgezählt und nicht mehr aus der Karte übernommen – die behauptete für eine
Kategorie zwölf Produkte, wo eines stand.

**Konfiguratoren und Abholgebiete stehen nicht zur Auswahl.** Dahinter steht
kein Produkt, das man zeigen und verlinken könnte: ein Konfigurator ist ein
Formular, ein Abholgebiet ein Ort. Gefiltert wird auf das Wort, nicht auf den
Ortsnamen – »Garagentore Berlin« ist ein Sortiment und bleibt wählbar.

**Beantwortete Rückfragen kommen nicht wieder.** Wer antwortet, sagt mit einem
Schalter dazu, ob die Auskunft allgemein gilt oder nur für dieses Produkt.
Tabelle `wissen`, gebunden an Projekt und – bei Produktwissen – an eine
Adresse. Allgemeines geht in jeden Entwurf des Projekts, Produktwissen nur zu
seiner Adresse. Die Unterscheidung ist der Kern: Wer alles pauschal
mitschickt, füttert Claude nach einem halben Jahr mit dreißig Sonderfällen und
bekommt schlechtere Texte statt bessere. Angesehen und gestrichen wird unter
»Gelerntes« in der linken Spalte.

**Bilder liegen unter `~/Dokumente/POSTKutsche/<jahr>-KW<woche>/<projekt>/`.**
Wohin ein Download geht, entscheidet der Browser; also legt der Dienst die
Datei selbst hin – er läuft auf demselben Rechner. Die Woche steht vorn, weil
danach aufgeräumt wird. Wie der Dokumentenordner heißt, wird gefragt und nicht
geraten: `POSTKUTSCHE_DOKUMENTE`, `~/.config/user-dirs.dirs`, `xdg-user-dir`,
ein vorhandenes »Dokumente« oder »Documents«.

**Eine Fassung trägt bis zu zwei Bilder** (`bild_pfad`, `bild_pfad2`). Zwei
Spalten und keine Tabelle: Bei genau zweien ist die Reihenfolge ohne
Sortierspalte eindeutig. Beim dritten wird die Tabelle fällig. Über die
Schnittstelle geht nur das erste raus – das zweite ist dem Handbetrieb
vorbehalten, und die Oberfläche sagt das. `SCHEMA_FASSUNG` steht seit dem
2026-08-31 auf 2; `_wandeln` hängt die Spalte an bestehende Ablagen an.

**Abbrechen heißt abbrechen und wegräumen.** Der Kampagnenlauf legt je Produkt
an und nicht am Ende in einem Zug – acht von zehn Beiträgen sind brauchbar,
ein Abbruch nach dem dritten wäre es nicht. Deshalb muss ein Abbruch
zurücknehmen, was schon dasteht: Sonst gälten die angefangenen Produkte vier
Wochen als beworben, obwohl nie etwas erschienen ist. Gefragt wird zwischen
den Produkten (`ausfuehren(..., abbrechen=…)`), weggeräumt über
`beitrag_entfernen` – mit derselben Regel wie überall, Veröffentlichtes
bleibt. Der Lauf-Zustand im Dienst trägt einen Zeitstempel: Was zehn Minuten
kein Lebenszeichen gibt, gilt als tot, denn eine Sperre, die niemand lösen
kann, ist schlimmer als zwei Läufe.

**Offen seit dem 2026-08-31:** Ob die Rückfragen seit dem vollständigen
Produkttext weniger geworden sind, ist nicht nachgemessen. Der Eindruck aus
einer geplanten Woche Ende September: Sie sind noch da, mehrere Kärtchen
tragen das »?«. Falls sich das bestätigt, liegt es an der Anweisung in
`denker/vorlagen.py` und nicht mehr an der Quelle – dort wurde 2026-08-31
schon nachgebessert.

**Entschieden am 2026-08-28, umgesetzt am 2026-08-31:** Die beiden
Shopware-Shops kommen über die Seitenkarte, nicht über die Store-API. Die
Kategorieseiten liefern Produktverweise und `og:`-Angaben, ein
Zugangsschlüssel wird nicht gebraucht. `quellen/shopware.py` gibt es deshalb
nicht und soll es vorerst nicht geben. Die Art `shopware` bleibt in der
Kommandozeile wählbar, führt aber ins Leere – die Meldungen sagen jetzt, dass
`seitenkarte` der Weg ist.

**Vier Wege zum Text, eine Schnittstelle** (2026-09-24). `denker.schreiben`
verzweigt nach `kommando` (claude -p), `offen` (alles in der OpenAI-Form),
`anthropisch` (Messages-API mit eigenem Schlüssel) und `hand` (kein Modell,
nur Titel und Anriss). Welcher gilt, entscheidet in dieser Reihenfolge:
`einstellungen.denker` des Projekts, `~/.config/postkutsche/denker.json`,
Vorgabe `kommando`. Die Aufrufer in `entwerfen.py` und `kampagnenlauf.py`
haben deshalb keine Verzweigung – sie reichen nur das Projekt durch.

Zwei Dinge, die beim Bauen Zeit gekostet haben und nicht wieder aufzurollen
sind: Die neueren Anthropic-Modelle lehnen `temperature` und `top_p` mit
einer 400 ab, und eine abgelehnte Anfrage kommt mit Statuscode 200 zurück –
`stop_reason` steht auf »refusal«, der Inhalt ist leer. Wer nur auf den Code
schaut, liest ins Leere.

**Ein Beitrag kann jetzt ohne Quelle entstehen.** `/api/beitrag/neu` legt
Inhalt, Beitrag und Fassungen in einem Zug an; die Adresse lautet dann
`hand:<zeitstempel>`, weil `inhalt_merken` eine eindeutige Kennung braucht –
sonst überschriebe die zweite Ankündigung mit gleichem Titel die erste. Die
Oberfläche blendet diese Ersatzadresse aus und hängt sie auch nicht an den
Text.

## Wie es zusammenhängt

```
Quelle findet Inhalt  →  Claude schreibt Fassungen  →  Kalender zeigt Entwurf
        │                        │                            │
   quellen/*.py            denker/*.py                    web/dienst.py
        │                        │                            │
        └────────────────  ablage.py (SQLite)  ───────────────┘
                                 │
                          netzwerke/*.py  →  raus, oder in die Übergabe
```

Ein **Inhalt** ist, was auf der eigenen Seite gefunden wurde – ein Blogbeitrag,
ein Produkt. Ein **Beitrag** ist ein Termin im Kalender. Eine **Fassung** ist
der Text für ein Netzwerk. Ein Beitrag hat mehrere Fassungen und ist trotzdem
*ein* Kärtchen – das ist der Punkt, an dem Metas eigener Planer scheitert und
denselben Post zweimal anzeigt, um 15:00 und um 15:01.

## Regeln, die nicht verhandelbar sind

**Zeiten stehen in UTC, immer.** Umgerechnet wird ausschließlich in
`zeiten.py`. Sobald die Umrechnung an einer zweiten Stelle steht, weicht eine
davon am letzten Sonntag im Oktober ab.

**Zugangsdaten kommen nicht in die Datenbank.** Schlüsselbund, ersatzweise
`~/.config/postkutsche/zugaenge.json` mit Rechten 600. `test_ablage.py` prüft,
dass die Tabelle `konten` keine Spalte mit »token«, »passwort« oder »secret«
bekommt – wer das aus Bequemlichkeit ändert, fällt auf.

**Pausieren ist nicht Ausblenden.** Das Häkchen im Kalender filtert die
Ansicht (`beitraege_im_zeitraum`), der Zustand `pausiert` hält den Betrieb an
(`faellige_beitraege`). Zwei Tests halten das auseinander.

**Wiederholen heißt neu anlegen, nicht umdatieren.** Sonst geht die Historie
verloren, und man braucht sie: Facebook und Instagram drosseln wortgleiche
Wiederholungen, der Text muss beim zweiten Mal also abgewandelt werden.
Die Kette in `wiederholung_von` zeigt immer auf den Urahn, nie auf den Vorgänger.

**Der Kern kommt ohne Fremdpakete aus.** Datenbank, Webdienst und alle Abrufe
stecken in der Standardbibliothek. Pillow und keyring sind Kür und werden zur
Laufzeit geprüft.

**Keine echten Adressen im Repository.** Die eigenen Seiten und Hersteller
stehen in `~/.config/postkutsche/`. `test_keine_echten_adressen.py` prüft von
der anderen Seite: Jede Adresse muss unter `.example` liegen oder in einer
offenen Positivliste stehen. Ein Test, der bekannte echte Adressen sucht,
müsste sie ja selbst enthalten.

**Farbe trägt keine Bedeutung allein.** Jedes Netzwerk hat neben seiner Farbe
ein Kürzel, das im Kärtchen steht. Wer rot-grün-blind ist oder auf einem
schlecht eingestellten Bildschirm sitzt, muss es trotzdem lesen können.

## Wo was steht

| Datei | Wofür |
|---|---|
| `ablage.py` | SQLite, alle Tabellen und Abfragen |
| `zeiten.py` | UTC ↔ Europe/Berlin, Monats- und Wochengrenzen |
| `netzwerke/__init__.py` | Farben, Kürzel, Zeichengrenzen, Eigenheiten |
| `sendezeiten.py` | Terminvorschläge je Netzwerk und Zielgruppe, mit Begründung |
| `erstbestueckung.py` | Beispielprojekte; die eigenen kommen aus `~/.config/postkutsche/` |
| `konfiguration.py` | liest die eigenen Seiten, Hersteller und den Denker |
| `denker/netz.py` | POST mit JSON über urllib, Fehlercodes als Sätze |
| `denker/__init__.py` | die Weiche zwischen den vier Wegen, und `nicht_da` |
| `kampagnen.py` | Thema, Kalenderwoche, Kategorien, Herstellerfilter |
| `grafik.py` | ein Gerüst, zwei Füllungen, quer und hoch |
| `wochenformat.py` | Tipp und Produkt der Woche, von der Eingabe zum Beitrag |
| `tippseite.py` | schreibt `Tipp-der-Woche.html` fort |
| `uebergabe.py` | Arbeitsstand mitnehmen und zurückholen |
| `farben.py` | die gemeinsame Palette, auch für andere Projekte |
| `__main__.py` | Kommandozeile |

## Was bewusst nicht da ist

**Videos.** Am 2026-08-28 gestrichen, bevor eine Zeile dafür geschrieben war.

**Ein Weg um Metas App-Prüfung herum.** Facebook und Instagram laufen über den
Handbetrieb: Text zum Kopieren, Bild zum Herunterladen, danach abhaken.

## Tests

```
python -m unittest discover -s tests
```

Kein Netzzugriff in Tests. Quellen werden gegen aufgezeichnete Antworten
geprüft, die Claude-Anbindung gegen einen vorgetäuschten Aufruf.
