"""Woher die Inhalte kommen.

Drei Wege, weil die eigenen Seiten selten auf demselben System laufen:

- `wordpress` – REST-Schnittstelle unter /wp-json/wp/v2/
- `shopware` – Store-API, braucht einen Zugangsschlüssel je Verkaufskanal
- `seitenkarte` – sitemap.xml lesen und die Seite auslesen; der Weg für alles,
  was keine Schnittstelle hat

Und zwei Betriebsarten:

- **Beobachten**: Was ist neu? Der Weg für die Blogs, wo ein neuer Beitrag von
  selbst ein Anlass ist.
- **Kampagne**: Ein Thema, eine Woche, ein paar Kategorien. Der Weg für die
  Shops, wo nichts »neu« ist, sondern ausgewählt wird. Siehe `kampagnen.py`.
"""

from __future__ import annotations

from . import abrufen, seitenkarte, wordpress
from .abrufen import AbrufFehler

__all__ = ["abrufen", "seitenkarte", "wordpress", "AbrufFehler", "ART_ZU_MODUL"]

#: Welche Projektart über welches Modul geholt wird.
ART_ZU_MODUL = {
    "wordpress": wordpress,
    "seitenkarte": seitenkarte,
}
