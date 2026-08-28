# CLAUDE.md

Landkarte des Repositorys. Ergänzt [README.md](README.md) und
[TODO.md](TODO.md), wiederholt sie nicht.

## Hier war Schluss (Stand 2026-08-28)

Erster Tag. Das Gerüst steht, 109 Tests laufen, noch nichts ist mit dem Netz
verbunden. Als Nächstes kommen die Quellen (Etappe 2).

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
`~/.config/sendeplan/zugaenge.json` mit Rechten 600. `test_ablage.py` prüft,
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
| `erstbestueckung.py` | die fünf Projekte beim ersten Einrichten |
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
