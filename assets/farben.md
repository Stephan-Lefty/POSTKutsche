# Farben

Die gemeinsame Palette für alle Programme. Sie stammt aus MailBurg und gilt
seit 2026-08-28 als Vorgabe – Abweichungen nur, wenn ausdrücklich etwas
anderes gesagt wird.

Diese Datei ist zum Weiterreichen gedacht: Sie liegt in jedem Repository gleich
und ist die Antwort auf »welches Blau war das noch?«. Die maschinenlesbaren
Werte stehen in [`postkutsche/farben.py`](../postkutsche/farben.py), damit
Oberfläche und Bilder nicht jeweils eigene Zahlen führen.

## Blau – die Leitfarbe

| Name | Wert | Wofür |
|---|---|---|
| `BLAU_HELL` | `#0e8af6` | oberes Ende des Verlaufs im Icon |
| `BLAU` | `#1668e3` | die Leitfarbe. Flächen, Knöpfe, Hervorhebungen |
| `BLAU_TIEF` | `#0047a7` | unteres Ende des Verlaufs im Icon |
| `BLAU_DUNKEL` | `#0d3a8a` | Ränder und Schatten auf blauem Grund |
| `BLAU_NACHT` | `#0d2141` | Hintergründe im dunklen Thema |
| `BLAU_LEUCHT` | `#6cb6ff` | Verweise auf dunklem Grund. Auf hellem zu blass |

Der Verlauf im Icon geht von `BLAU_HELL` oben nach `BLAU_TIEF` unten, senkrecht
über die volle Höhe.

## Grau – alles andere

| Name | Wert | Wofür |
|---|---|---|
| `GRAU_PAPIER` | `#f7f9fc` | Seitenhintergrund im hellen Thema |
| `GRAU_HELL` | `#d6dde8` | Linien, Trenner, Rahmen |
| `GRAU_MITTE` | `#97a1ad` | zurückgenommener Text auf **dunklem** Grund |
| `GRAU_LEISE` | `#667080` | dasselbe auf **hellem** Grund |
| `GRAU` | `#5b6672` | Fließtext auf hellem Grund |
| `GRAU_DUNKEL` | `#3a4048` | Überschriften |
| `GRAU_KOHLE` | `#2b323c` | Flächen im dunklen Thema |
| `GRAU_NACHT` | `#20262f` | Seitenhintergrund im dunklen Thema |
| `WEISS` | `#ffffff` | Zeichnungen auf Blau, Flächen im hellen Thema |

Zwei Töne für dieselbe Aufgabe, weil einer nicht reicht: `GRAU_MITTE` kommt auf
hellem Grund nur auf 2,48 Kontrast und verfehlt damit sogar die 3,0, die WCAG
für große Schrift verlangt. Das sieht man einem Farbwert nicht an – es fiel
erst auf, als `tests/test_farben.py` es nachgerechnet hat.

## Signalfarben

Sparsam. Sie sagen »hier ist etwas passiert«, und das verliert seine Wirkung,
wenn sie zur Dekoration werden.

| Name | Wert | Wofür |
|---|---|---|
| `ROT` | `#c62828` | Fehler, Gescheitertes |
| `ROT_HELL` | `#ef9a9a` | dasselbe auf dunklem Grund |
| `GRUEN` | `#2e7d32` | Erledigtes, Gesendetes |
| `GRUEN_HELL` | `#81c784` | dasselbe auf dunklem Grund |

## Was nicht in dieser Palette steht

**Projektfarben.** Jedes Projekt im Kalender hat eine eigene Farbe, damit man
seine Kärtchen auf einen Blick trennen kann. Die dürfen und sollen ausbrechen –
eine Palette aus sechs Blautönen wäre für diesen Zweck unbrauchbar. Sie stehen
je Projekt in der Ablage.

**Netzwerkfarben.** Mastodon, LinkedIn, Facebook und Instagram bringen ihre
Markenfarben mit; die kann man nicht ersetzen, ohne sie unkenntlich zu machen.
Sie stehen in `postkutsche/netzwerke/__init__.py`, mit einer Ausnahme, die dort
begründet ist: LinkedIn steht im dunkleren Petrolblau, weil es sonst neben
Facebook nicht zu unterscheiden wäre.

## Eine Anmerkung zum Icon

Das Icon selbst hat einen flachen Grund in `#015ee9` statt des Verlaufs – es
wurde außerhalb dieser Palette erzeugt und liegt damit knapp neben `BLAU`
(`#1668e3`). Der Unterschied ist mit bloßem Auge nicht zu sehen, solange beide
nicht direkt aneinanderstoßen. Wer das Icon einmal neu zeichnen lässt, nimmt
`BLAU`.
