# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-08-31)

417 Tests. Die Kette läuft ganz durch: Quelle findet ein Produkt, Claude
schreibt die Fassungen, der Kalender zeigt sie, Mastodon sendet, Facebook und
Instagram gehen über den Handbetrieb. Ein Beitrag ist echt erschienen.

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

**Als Nächstes:** eine Woche planen und nachsehen, ob die Rückfragen weniger
werden. Bleiben sie hoch, liegt es an der Anweisung in `denker/vorlagen.py`,
nicht mehr an der Quelle.

**Entschieden am 2026-08-28, umgesetzt am 2026-08-31:** Die beiden
Shopware-Shops kommen über die Seitenkarte, nicht über die Store-API. Die
Kategorieseiten liefern Produktverweise und `og:`-Angaben, ein
Zugangsschlüssel wird nicht gebraucht. `quellen/shopware.py` gibt es deshalb
nicht und soll es vorerst nicht geben. Die Art `shopware` bleibt in der
Kommandozeile wählbar, führt aber ins Leere – die Meldungen sagen jetzt, dass
`seitenkarte` der Weg ist.

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
| `konfiguration.py` | liest die eigenen Seiten und Hersteller, die nicht ins Repo dürfen |
| `kampagnen.py` | Thema, Kalenderwoche, Kategorien, Herstellerfilter |
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
