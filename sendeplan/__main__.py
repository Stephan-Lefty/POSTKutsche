"""Die Kommandozeile von Sendeplan.

Alles, was die Oberfläche kann, geht auch hier – das ist Absicht. Ein Werkzeug,
das man nur anklicken kann, lässt sich nicht in einen Zeitplan hängen und nicht
prüfen, wenn etwas klemmt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, erstbestueckung, netzwerke, zeiten
from .ablage import (
    PROJEKT_AKTIV,
    PROJEKT_PAUSIERT,
    Ablage,
    standard_pfad,
)


def main(argv: list[str] | None = None) -> int:
    zerleger = _zerleger()
    args = zerleger.parse_args(argv)
    if not getattr(args, "handlung", None):
        zerleger.print_help()
        return 1
    with Ablage(args.ablage) as ablage:
        return int(args.handlung(ablage, args) or 0)


def _zerleger() -> argparse.ArgumentParser:
    zerleger = argparse.ArgumentParser(
        prog="sendeplan",
        description="Redaktionskalender für Blogs, Shops und soziale Netzwerke.",
    )
    zerleger.add_argument("--fassung", action="version", version=f"Sendeplan {__version__}")
    zerleger.add_argument(
        "--ablage",
        type=Path,
        default=None,
        help=f"Pfad zur Datenbank (Vorgabe: {standard_pfad()})",
    )
    unter = zerleger.add_subparsers(dest="befehl")

    einrichten = unter.add_parser(
        "einrichten", help="Ablage anlegen und die fünf Projekte eintragen"
    )
    einrichten.set_defaults(handlung=_einrichten)

    # -- projekt ----------------------------------------------------------
    projekt = unter.add_parser("projekt", help="Projekte anzeigen und verwalten")
    projekt_unter = projekt.add_subparsers(dest="projekt_befehl")
    projekt.set_defaults(handlung=lambda a, g: _projekt_liste(a, g))

    liste = projekt_unter.add_parser("liste", help="alle Projekte anzeigen")
    liste.set_defaults(handlung=_projekt_liste)

    neu = projekt_unter.add_parser("neu", help="ein Projekt hinzufügen")
    neu.add_argument("kennung", help="kurz und klein, etwa »zweitblog«")
    neu.add_argument("name", help="wie es im Kalender steht")
    neu.add_argument("adresse", help="https://…")
    neu.add_argument(
        "--art",
        choices=("wordpress", "shopware", "seitenkarte"),
        required=True,
        help="woher die Inhalte kommen",
    )
    neu.add_argument("--farbe", default="#6b7280", help="#rrggbb für die Kärtchen")
    neu.add_argument(
        "--ohne-freigabe",
        action="store_true",
        help="Beiträge dieses Projekts gehen ohne Rückfrage raus",
    )
    neu.set_defaults(handlung=_projekt_neu)

    for befehl, zustand, hilfe in (
        ("pausieren", PROJEKT_PAUSIERT, "nicht mehr abrufen, nichts mehr senden"),
        ("starten", PROJEKT_AKTIV, "wieder abrufen und senden"),
    ):
        p = projekt_unter.add_parser(befehl, help=hilfe)
        p.add_argument("kennung")
        p.set_defaults(handlung=_projekt_zustand, zustand=zustand)

    weg = projekt_unter.add_parser(
        "loeschen", help="Projekt samt Inhalten und Beiträgen entfernen"
    )
    weg.add_argument("kennung")
    weg.add_argument(
        "--wirklich",
        action="store_true",
        help="ohne diesen Schalter passiert nichts",
    )
    weg.set_defaults(handlung=_projekt_loeschen)

    # -- plan -------------------------------------------------------------
    plan = unter.add_parser("plan", help="geplante Beiträge anzeigen")
    plan.add_argument("--monat", help="etwa 2026-09; Vorgabe ist der laufende Monat")
    plan.add_argument(
        "--projekt",
        action="append",
        dest="projekte",
        help="nur diese Projekte; mehrfach angebbar",
    )
    plan.set_defaults(handlung=_plan)

    # -- netzwerke --------------------------------------------------------
    netze = unter.add_parser("netzwerke", help="Netzwerke, Farben und Grenzen zeigen")
    netze.set_defaults(handlung=_netzwerke)

    return zerleger


# -- Handlungen ------------------------------------------------------------


def _einrichten(ablage: Ablage, args: argparse.Namespace) -> int:
    kennungen = erstbestueckung.einrichten(ablage)
    print(f"Ablage: {ablage.pfad}")
    print(f"{len(kennungen)} Projekte eingetragen: {', '.join(kennungen)}")
    print()
    print("Weiter mit »sendeplan projekt liste«.")
    return 0


def _projekt_liste(ablage: Ablage, args: argparse.Namespace) -> int:
    projekte = ablage.projekte()
    if not projekte:
        print("Noch keine Projekte. »sendeplan einrichten« legt die ersten fünf an.")
        return 0
    breite = max(len(p.kennung) for p in projekte)
    for p in projekte:
        zeichen = "●" if p.aktiv else "○"
        stand = "aktiv" if p.aktiv else "pausiert"
        geholt = zeiten.lesbar(p.zuletzt_geholt) if p.zuletzt_geholt else "noch nie"
        print(
            f"{zeichen} {p.kennung.ljust(breite)}  {p.name}"
            f"\n  {p.art} · {p.adresse}"
            f"\n  {stand} · Freigabe {'nötig' if p.freigabe_noetig else 'nicht nötig'}"
            f" · geholt: {geholt}"
        )
    return 0


def _projekt_neu(ablage: Ablage, args: argparse.Namespace) -> int:
    einstellungen: dict[str, str] = {}
    adresse = args.adresse.rstrip("/")
    if args.art == "wordpress":
        einstellungen["rest"] = f"{adresse}/wp-json/wp/v2"
    elif args.art == "shopware":
        einstellungen["store_api"] = f"{adresse}/store-api"
    else:
        einstellungen["seitenkarte"] = f"{adresse}/sitemap.xml"

    projekt = ablage.projekt_anlegen(
        kennung=args.kennung,
        name=args.name,
        adresse=adresse,
        art=args.art,
        farbe=args.farbe,
        freigabe_noetig=not args.ohne_freigabe,
        einstellungen=einstellungen,
    )
    print(f"Projekt »{projekt.name}« ({projekt.kennung}) angelegt.")
    for schluessel, wert in projekt.einstellungen.items():
        print(f"  {schluessel}: {wert}")
    if args.art == "shopware":
        print()
        print("Für Shopware fehlt noch der Zugangsschlüssel des Verkaufskanals.")
    return 0


def _projekt_zustand(ablage: Ablage, args: argparse.Namespace) -> int:
    if not ablage.projekt_zustand(args.kennung, args.zustand):
        print(f"Kein Projekt mit der Kennung »{args.kennung}«.", file=sys.stderr)
        return 1
    if args.zustand == PROJEKT_PAUSIERT:
        print(
            f"»{args.kennung}« pausiert. Es wird nichts mehr geholt und nichts "
            "gesendet; die geplanten Beiträge bleiben stehen."
        )
    else:
        print(f"»{args.kennung}« läuft wieder.")
    return 0


def _projekt_loeschen(ablage: Ablage, args: argparse.Namespace) -> int:
    if not args.wirklich:
        print(
            f"Das würde »{args.kennung}« samt allen Inhalten und geplanten "
            "Beiträgen entfernen.\n"
            "Meistens ist Pausieren gemeint: sendeplan projekt pausieren "
            f"{args.kennung}\n"
            f"Wenn es wirklich weg soll: --wirklich anhängen.",
            file=sys.stderr,
        )
        return 1
    if not ablage.projekt_loeschen(args.kennung):
        print(f"Kein Projekt mit der Kennung »{args.kennung}«.", file=sys.stderr)
        return 1
    print(f"»{args.kennung}« gelöscht.")
    return 0


def _plan(ablage: Ablage, args: argparse.Namespace) -> int:
    from datetime import datetime

    if args.monat:
        try:
            jahr, monat = (int(t) for t in args.monat.split("-", 1))
        except ValueError:
            print("Monat bitte als 2026-09 angeben.", file=sys.stderr)
            return 1
    else:
        heute = datetime.now(zeiten.ORTSZONE)
        jahr, monat = heute.year, heute.month

    von, bis = zeiten.monatsgrenzen(jahr, monat)
    zeilen = ablage.beitraege_im_zeitraum(von, bis, args.projekte)
    if not zeilen:
        print(f"Nichts geplant für {monat:02d}/{jahr}.")
        return 0

    print(f"Sendeplan {monat:02d}/{jahr}\n")
    for zeile in zeilen:
        fassungen = ablage.fassungen(int(zeile["id"]))
        kuerzel = " ".join(
            netzwerke.netzwerk(f["netzwerk"]).kuerzel for f in fassungen
        ) or "—"
        titel = zeile["inhalt_titel"] or zeile["notiz"] or "(ohne Titel)"
        print(
            f"{zeiten.lesbar(zeile['geplant'])}  [{zeile['projekt_kennung']}] "
            f"{titel}\n    {kuerzel} · {zeile['zustand']}"
        )
    return 0


def _netzwerke(ablage: Ablage, args: argparse.Namespace) -> int:
    for netz in netzwerke.alle():
        print(f"{netz.kuerzel}  {netz.name.ljust(10)} {netz.farbe}")
        print(
            f"    Ziel {netz.zeichen_ziel} Zeichen (Grenze {netz.zeichen_max}), "
            f"bis {netz.schlagworte_max} Schlagwörter, Bild {netz.bild_format}"
            f"{' (Pflicht)' if netz.bild_pflicht else ''}"
        )
        print(f"    {netz.hinweis}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
