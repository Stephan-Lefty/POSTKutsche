"""Die Kommandozeile von POSTKutsche.

Alles, was die Oberfläche kann, geht auch hier – das ist Absicht. Ein Werkzeug,
das man nur anklicken kann, lässt sich nicht in einen Zeitplan hängen und nicht
prüfen, wenn etwas klemmt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, denker, erstbestueckung, netzwerke, zeiten
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
        prog="postkutsche",
        description="Redaktionskalender für Blogs, Shops und soziale Netzwerke.",
    )
    zerleger.add_argument("--fassung", action="version", version=f"POSTKutsche {__version__}")
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

    # -- entwerfen --------------------------------------------------------
    entw = unter.add_parser(
        "entwerfen", help="neue Inhalte holen und Entwürfe schreiben lassen"
    )
    entw.add_argument("--projekt", required=True, help="Kennung des Projekts")
    entw.add_argument(
        "--netzwerk", action="append", dest="netzwerke",
        help="für welches Netzwerk; mehrfach angebbar. Vorgabe: mastodon",
    )
    entw.add_argument("--anzahl", type=int, default=1, help="wie viele Entwürfe")
    entw.add_argument(
        "--auch-bekannte", action="store_true",
        help="auch aus Inhalten entwerfen, die schon bekannt sind",
    )
    entw.set_defaults(handlung=_entwerfen)

    # -- konto ------------------------------------------------------------
    konto = unter.add_parser("konto", help="Konten der Netzwerke einrichten")
    konto_unter = konto.add_subparsers(dest="konto_befehl")
    konto.set_defaults(handlung=lambda a, g: _konto_liste(a, g))

    kl = konto_unter.add_parser("liste", help="eingerichtete Konten zeigen")
    kl.set_defaults(handlung=_konto_liste)

    kn = konto_unter.add_parser("neu", help="ein Konto anlegen")
    kn.add_argument("netzwerk", choices=[n.kennung for n in netzwerke.alle()])
    kn.add_argument("kennung", help="kurzer Name, etwa »mastodon-privat«")
    kn.add_argument("--instanz", help="bei Mastodon die Serveradresse")
    kn.add_argument("--projekt", action="append", dest="projekte",
                    help="Projekt zuordnen; mehrfach angebbar")
    kn.set_defaults(handlung=_konto_neu)

    kt = konto_unter.add_parser("token", help="Zugangstoken hinterlegen")
    kt.add_argument("kennung")
    kt.set_defaults(handlung=_konto_token)

    kp = konto_unter.add_parser("pruefen", help="Zugang prüfen, ohne zu senden")
    kp.add_argument("kennung")
    kp.set_defaults(handlung=_konto_pruefen)

    # -- senden -----------------------------------------------------------
    snd = unter.add_parser("senden", help="fällige Beiträge veröffentlichen")
    snd.add_argument("--probelauf", action="store_true",
                     help="nur zeigen, was rausginge")
    snd.set_defaults(handlung=_senden)

    # -- kalender ---------------------------------------------------------
    kal = unter.add_parser("kalender", help="den Kalender im Browser öffnen")
    kal.add_argument("--port", type=int, default=8770)
    kal.add_argument("--nicht-oeffnen", action="store_true",
                     help="Dienst starten, aber keinen Browser öffnen")
    kal.set_defaults(handlung=_kalender)

    # -- dienst -----------------------------------------------------------
    dst = unter.add_parser(
        "dienst", help="im Hintergrund laufen lassen (systemd)"
    )
    dst_unter = dst.add_subparsers(dest="dienst_befehl")
    dst.set_defaults(handlung=lambda a, g: _dienst_stand(a, g))

    de = dst_unter.add_parser("einrichten", help="Kalender und Sendetimer anlegen")
    de.add_argument("--port", type=int, default=8770)
    de.set_defaults(handlung=_dienst_einrichten)

    ds = dst_unter.add_parser("stand", help="läuft es?")
    ds.set_defaults(handlung=_dienst_stand)

    dv = dst_unter.add_parser(
        "menueeintrag", help="POSTKutsche ins Anwendungsmenü legen"
    )
    dv.add_argument("--port", type=int, default=8770)
    dv.set_defaults(handlung=_dienst_verknuepfung)

    dx = dst_unter.add_parser("entfernen", help="Dienste anhalten und löschen")
    dx.set_defaults(handlung=_dienst_entfernen)

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
    print("Weiter mit »postkutsche projekt liste«.")
    return 0


def _projekt_liste(ablage: Ablage, args: argparse.Namespace) -> int:
    projekte = ablage.projekte()
    if not projekte:
        print("Noch keine Projekte. »postkutsche einrichten« legt die ersten fünf an.")
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
            "Meistens ist Pausieren gemeint: postkutsche projekt pausieren "
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

    print(f"POSTKutsche {monat:02d}/{jahr}\n")
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


def _entwerfen(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import entwerfen as entwerfen_modul

    netze = args.netzwerke or [netzwerke.MASTODON]
    for netz in netze:
        try:
            netzwerke.netzwerk(netz)
        except ValueError as fehler:
            print(fehler, file=sys.stderr)
            return 1

    try:
        angelegt = entwerfen_modul.entwerfen(
            ablage, args.projekt, netze, args.anzahl, args.auch_bekannte
        )
    except (entwerfen_modul.EntwurfFehler, denker.ClaudeFehler,
            denker.ClaudeFehlt, denker.AntwortFehler) as fehler:
        print(f"\n{fehler}", file=sys.stderr)
        return 1

    if angelegt:
        print(f"\n{len(angelegt)} Entwurf/Entwürfe angelegt. "
              "Ansehen mit »postkutsche plan«.")
    return 0


def _konto_liste(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import versand, zugaenge

    zeilen = ablage.konten()
    if not zeilen:
        print("Noch keine Konten. Anlegen mit »postkutsche konto neu«.")
        return 0
    for zeile in zeilen:
        hat = "Token vorhanden" if zugaenge.vorhanden(zeile["kennung"]) else "kein Token"
        print(f"{zeile['netzwerk']:<10} {zeile['kennung']:<22} {hat}")
        for name, wert in json.loads(zeile["einstellungen"] or "{}").items():
            print(f"           {name}: {wert}")
    warnung = zugaenge.rechte_warnung()
    if warnung:
        print(f"\n{warnung}", file=sys.stderr)
    return 0


def _konto_neu(ablage: Ablage, args: argparse.Namespace) -> int:
    einstellungen = {}
    if args.netzwerk == netzwerke.MASTODON:
        if not args.instanz:
            print("Bei Mastodon fehlt --instanz, etwa "
                  "--instanz https://meine-instanz.example", file=sys.stderr)
            return 1
        einstellungen["instanz"] = args.instanz.rstrip("/")

    nummer = ablage.konto_anlegen(args.netzwerk, args.kennung,
                                  einstellungen=einstellungen)
    for kennung in args.projekte or []:
        projekt = ablage.projekt(kennung)
        if projekt is None:
            print(f"Kein Projekt »{kennung}« – übersprungen.", file=sys.stderr)
            continue
        ablage.konto_zuordnen(projekt.id, nummer)

    print(f"Konto »{args.kennung}« für {args.netzwerk} angelegt.")
    print(f"Jetzt das Token hinterlegen: postkutsche konto token {args.kennung}")
    return 0


def _konto_token(ablage: Ablage, args: argparse.Namespace) -> int:
    import getpass
    from . import zugaenge

    # getpass, damit das Token nicht im Klartext auf dem Schirm steht - und
    # nicht in der Verlaufsdatei der Shell landet.
    token = getpass.getpass(f"Token für »{args.kennung}« (Eingabe bleibt unsichtbar): ")
    if not token.strip():
        print("Nichts eingegeben, nichts gespeichert.", file=sys.stderr)
        return 1
    ort = zugaenge.setzen(args.kennung, token.strip())
    print(f"Hinterlegt in: {ort}")
    return 0


def _konto_pruefen(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import versand, zugaenge
    from .netzwerke import mastodon

    zeile = next((z for z in ablage.konten() if z["kennung"] == args.kennung), None)
    if zeile is None:
        print(f"Kein Konto »{args.kennung}«.", file=sys.stderr)
        return 1
    if zeile["netzwerk"] != netzwerke.MASTODON:
        print(f"Prüfen ist bisher nur für Mastodon gebaut.", file=sys.stderr)
        return 1

    einstellungen = json.loads(zeile["einstellungen"] or "{}")
    try:
        konto = mastodon.pruefen(einstellungen["instanz"],
                                 zugaenge.holen(args.kennung))
    except (mastodon.MastodonFehler, zugaenge.KeinZugang) as fehler:
        print(fehler, file=sys.stderr)
        return 1

    print(f"Angemeldet als @{konto['name']} ({konto['anzeigename']})")
    print(f"{konto['beitraege']} Beiträge bisher")
    grenze = mastodon.zeichengrenze(einstellungen["instanz"])
    print(f"Zeichengrenze dieser Instanz: {grenze}")
    return 0


def _senden(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import versand

    konten = versand.konten_lesen(ablage)
    gut, schlecht = versand.senden(ablage, konten, probelauf=args.probelauf)
    if not args.probelauf:
        # Danach, nicht davor: Erst wird gesendet, was fällig ist, dann
        # weggeräumt, was verfallen ist.
        versand.aufraeumen(ablage)
    if gut or schlecht:
        wort = "würden rausgehen" if args.probelauf else "gesendet"
        print(f"\n{gut} {wort}, {schlecht} gescheitert.")
    return 1 if schlecht else 0


def _dienst_einrichten(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import dienste

    try:
        return dienste.einrichten(args.port)
    except RuntimeError as fehler:
        print(fehler, file=sys.stderr)
        return 1


def _dienst_verknuepfung(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import dienste

    return dienste.verknuepfung(args.port)


def _dienst_stand(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import dienste

    return dienste.stand()


def _dienst_entfernen(ablage: Ablage, args: argparse.Namespace) -> int:
    from . import dienste

    return dienste.entfernen()


def _kalender(ablage: Ablage, args: argparse.Namespace) -> int:
    from .web import dienst

    # Der Dienst öffnet die Ablage je Anfrage selbst; die hier geöffnete
    # wird nicht gebraucht und würde sonst über Fäden hinweg benutzt -
    # SQLite-Verbindungen sind nicht dafür gemacht.
    pfad = ablage.pfad
    ablage.schliessen()
    dienst.starten(pfad, args.port, not args.nicht_oeffnen)
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
