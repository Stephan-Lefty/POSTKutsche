"""Womit ein frisch eingerichteter POSTKutsche anfängt.

**Hier stehen keine echten Adressen.** Die Beispiele benutzen `.example` –
eine Endung, die nach RFC 2606 für genau diesen Zweck reserviert ist und
niemandem gehören kann. Die eigenen Seiten stehen in
`~/.config/postkutsche/projekte.json` und werden von dort gelesen; wo keine
solche Datei liegt, kommen die Beispiele zum Zug.

Der Grund ist nicht Geheimniskrämerei: Ein öffentliches Repository ist
durchsuchbar und wird geklont, und was einmal in der Versionsgeschichte stand,
steht auch nach dem Löschen noch darin. Siehe `konfiguration.py`.

In beiden Fällen gilt: Das ist eine *Erstbestückung*, keine feste Liste.
Projekte werden in der Ablage geführt und lassen sich jederzeit ergänzen,
umbenennen, pausieren und löschen – über `postkutsche projekt` und über die
Oberfläche.
"""

from __future__ import annotations

from typing import Any

from . import farben, konfiguration

# Die Farben stammen aus farben.PROJEKTFARBEN - sie halten Abstand zu den
# Netzwerkfarben, damit man einen Projektpunkt nicht für eine Netzwerkmarke
# hält. Wer eine eigene wählt, prüft das mit farben.farbabstand nach.
#
# art:
#   wordpress   – REST-Schnittstelle unter /wp-json/wp/v2/
#   shopware    – Store-API, braucht einen Zugangsschlüssel je Verkaufskanal
#   seitenkarte – keine Schnittstelle, sitemap.xml lesen und die Seite auslesen
#
# zielgruppe steuert die Terminvorschläge, siehe sendezeiten.py.
BEISPIELE: list[dict[str, Any]] = [
    {
        "kennung": "blog",
        "name": "Mein Blog",
        "adresse": "https://blog.example",
        "art": "wordpress",
        "farbe": "#6bad08",
        "einstellungen": {
            "rest": "https://blog.example/wp-json/wp/v2",
            "zielgruppe": "verbraucher",
        },
    },
    {
        "kennung": "shop",
        "name": "Mein Shop",
        "adresse": "https://shop.example",
        "art": "shopware",
        "farbe": "#08ad19",
        "einstellungen": {
            "store_api": "https://shop.example/store-api",
            "zielgruppe": "handwerk",
        },
    },
    {
        "kennung": "altbau",
        "name": "Seite ohne Schnittstelle",
        "adresse": "https://altbau.example",
        "art": "seitenkarte",
        "farbe": "#8c4907",
        "einstellungen": {
            "seitenkarte": "https://altbau.example/sitemap.xml",
            "zielgruppe": "handwerk",
        },
    },
]


def projekte() -> list[dict[str, Any]]:
    """Die eigenen Projekte, sonst die Beispiele."""
    eigene = konfiguration.projekte_lesen()
    return eigene if eigene else BEISPIELE


def einrichten(ablage, nur_beispiele: bool = False) -> list[str]:  # type: ignore[no-untyped-def]
    """Legt die Erstbestückung an. Vorhandene Projekte werden aufgefrischt.

    Gibt die Kennungen zurück. Wer ein Projekt gelöscht hat und `einrichten`
    erneut aufruft, bekommt es wieder – das ist beabsichtigt und heißt: nicht
    löschen, sondern pausieren.
    """
    angelegt = []
    for eintrag in (BEISPIELE if nur_beispiele else projekte()):
        ablage.projekt_anlegen(
            kennung=eintrag["kennung"],
            name=eintrag["name"],
            adresse=eintrag["adresse"],
            art=eintrag["art"],
            # Ohne Angabe eine freie aus der Palette, statt für alle
            # dasselbe Grau.
            farbe=eintrag.get("farbe") or farben.freie_projektfarbe(
                [p.farbe for p in ablage.projekte()]
            ),
            freigabe_noetig=eintrag.get("freigabe_noetig", True),
            einstellungen=eintrag.get("einstellungen", {}),
        )
        angelegt.append(eintrag["kennung"])
    return angelegt


def aus_eigener_datei() -> bool:
    """Ob eigene Projekte gefunden wurden – für Meldungen an den Benutzer."""
    return bool(konfiguration.projekte_lesen())
