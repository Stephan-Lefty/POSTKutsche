"""Bilder für die Netzwerke: ein Gerüst, zwei Füllungen.

**Das Gerüst ist in beiden Formaten dasselbe, und das ist der Zweck.** Wer
»Tipp der Woche« und »Produkt der Woche« nebeneinander sieht, soll denselben
Absender erkennen, bevor er ein Wort gelesen hat: Logo oben rechts im weißen,
angeschrägten Feld, links die Fotospalte, darüber die Überschrift, rechts eine
Spalte mit goldgerahmten Kästen, unten links die Merkmalszeile mit dem
Aufruf, unten rechts der Kontakt. Deshalb steht der Rahmen hier *einmal*
(`_seite`) und nicht zweimal – zwei Vorlagen driften auseinander, sobald an
einer etwas geändert wird.

**Gezeichnet wird mit HTML und CSS, ausgegeben von Firefox.** Kein Pillow-
Layout, keine Zeichenbefehle: Ein Umbruch, der nicht passt, fällt beim Ansehen
auf und ist eine Zahl im Stilblatt, nicht eine Rechnung im Quelltext.

**Firefox ist Kür, nicht Pflicht.** Fehlt er, entsteht der Beitrag trotzdem –
nur ohne Bild und mit einer Meldung, die sagt warum. Das ist dieselbe Regel
wie bei Pillow und keyring: Der Kern muss ohne auskommen.

Zwei Dinge, die beim Bauen Zeit gekostet haben und nicht wieder aufzurollen
sind. Ein laufender Firefox blockiert `--screenshot` (»Firefox is already
running«) – deshalb bekommt jeder Lauf ein eigenes Profil in einem
Wegwerfordner. Und `--screenshot` löst beim `load`-Ereignis aus: Alles, was
das Bild braucht, muss lokal liegen, sonst knipst es in eine halbfertige
Seite.
"""

from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

#: Das Querformat für Mastodon, Facebook und LinkedIn.
BREITE, HOEHE = 1536, 1024

#: Instagram zeigt 4:5. Ein Zuschnitt aus der Mitte zerschnitte dieses
#: Layout, deshalb gibt es dafür eine eigene Anordnung – siehe `hochformat`.
BREITE_HOCH, HOEHE_HOCH = 1080, 1350

#: Wie lange auf Firefox gewartet wird. Ein Lauf dauert auf einem trägen
#: Rechner ein paar Sekunden; drei Minuten sind kein Maß, sondern eine Notbremse.
ZEITLIMIT = 180

BEFEHL = "firefox"

# -- Farben ----------------------------------------------------------------
#
# Die Grafiken tragen die Farben des Auftritts, nicht die der Oberfläche:
# Nachtblau als Grund, Gold als Signal. Sie stehen hier und nicht in
# `farben.py`, weil sie nur hier gelten - `farben.py` ist die Palette der
# *Programme*, und die soll sich nicht nach einem Kunden richten.

NACHT = "#12304e"        # Grund der Fläche
TIEFER = "#0a1d31"       # Kästen und Preisfeld
GOLD = "#efa32c"         # Rahmen, Balken, Haken
HELLGOLD = "#e9c072"     # das kursive »der«
PAPIER = "#f4f6f8"       # die weiße Karte
SCHRIFT_HELL = "#e6edf5"
SCHRIFT_TIEF = "#13293f"

#: Die Hausschrift. DejaVu Sans Condensed liegt auf praktisch jedem Linux,
#: Nimbus Sans Narrow ist der Rückfall. Eine Schrift, die nachinstalliert
#: werden muss, macht die Ausgabe auf einem anderen Rechner kaputt - und in
#: der CI erst recht, wo ohne Netz geprüft wird. Wer die Hausschrift der
#: Agentur hat, trägt sie unter »schrift« in `marken.json` ein; sie kommt dann
#: nach vorn, und DejaVu bleibt der Rückfall.
SCHRIFT = '"DejaVu Sans Condensed","Nimbus Sans Narrow",sans-serif'

#: So viele Merkmale trägt die Karte. Die Schriftgrößen sind darauf
#: ausgelegt; mehr läuft unten heraus. Wer den Text schreiben lässt, muss
#: das durchreichen - nicht die Grafik soll sich wehren, sondern der Text
#: soll passen.
MERKMALE = 4


class GrafikFehler(Exception):
    """Das Bild ließ sich nicht erzeugen. Die Meldung ist für Menschen."""


#: Wie eine Marke aussieht, die es noch nicht gibt. Steht hier als Form, nicht
#: als Inhalt: Die echten Angaben liegen in `~/.config/postkutsche/marken.json`,
#: siehe `konfiguration.marken_lesen`.
BEISPIEL_MARKE: dict[str, Any] = {
    "logo": None,
    "name": "Beispielhaus",
    "telefon": "030 - 000 000 00",
    "zeiten": "Mo.–Fr. 8:00–17:00 Uhr",
    "netz": "www.beispiel.example",
    "mail": "info@example.org",
    "ueber": [
        "Türen, Tore, Sicherheitstechnik",
        "Brandschutz von T30 bis T90",
        "Einbruchschutz RC2 bis RC4",
        "Beratung vom Fachmann",
    ],
}


def vorhanden() -> bool:
    """Ob Firefox im Suchpfad steht."""
    return shutil.which(BEFEHL) is not None


def nicht_da() -> str:
    """Was zu tun ist, wenn kein Browser da ist – ein Satz für Menschen."""
    return ("Für die Grafik wird Firefox gebraucht; er steht nicht im "
            "Suchpfad. Der Beitrag entsteht auch ohne – dann fehlt nur das "
            "Bild. Nachinstallieren: das Paket »firefox« der Distribution.")


# -- Das Gerüst ------------------------------------------------------------


def _kopf(marke: dict[str, Any]) -> str:
    """Das weiße, links angeschrägte Feld mit dem Logo.

    Ohne Logodatei bleibt der Name als Schriftzug stehen – eine Grafik ganz
    ohne Absender wäre schlimmer als eine ohne Bildmarke.
    """
    logo = marke.get("logo")
    if logo and Path(logo).exists():
        beschriftung = html.escape(str(marke.get("name") or ""))
        innen = (f'<img src="{Path(logo).name}" alt="{beschriftung}">')
    else:
        innen = f'<b>{html.escape(str(marke.get("name") or ""))}</b>'
    return f'<div class="logo">{innen}</div>'


def _kontakt(marke: dict[str, Any]) -> str:
    """Der Kontaktkasten unten rechts – in beiden Formaten gleich."""
    zeilen = ""
    if marke.get("netz"):
        zeilen += f'<div class="zeile">{_GLOBUS}{html.escape(marke["netz"])}</div>'
    if marke.get("mail"):
        zeilen += f'<div class="zeile">{_BRIEF}{html.escape(marke["mail"])}</div>'
    return f"""<div class="kontakt">
  <div class="kreis">{_HOERER}</div>
  <div>
    <b>FRAGEN? WIR BERATEN SIE GERNE!</b>
    <div class="nr">{html.escape(str(marke.get("telefon") or ""))}</div>
    <div class="zt">{html.escape(str(marke.get("zeiten") or ""))}</div>
    {zeilen}
  </div>
</div>"""


def _fuss(punkte: list[tuple[str, str, str]]) -> str:
    """Die Merkmalszeile unten links."""
    return '<div class="fuss">' + "".join(
        f'<div><svg viewBox="0 0 48 48">{bild}</svg>'
        f'<div><b>{html.escape(oben)}</b><br>{html.escape(unten)}</div></div>'
        for oben, unten, bild in punkte) + "</div>"


def _haken(klasse: str = "hk") -> str:
    return (f'<svg class="{klasse}" viewBox="0 0 24 24">'
            f'<circle cx="12" cy="12" r="11" fill="{GOLD}"/>'
            f'<path d="M6.5 12.5l3.5 3.5 7.5-8" fill="none" stroke="{TIEFER}" '
            f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


_HOERER = ('<svg viewBox="0 0 32 32"><path d="M7 4h6l3 7-4 2c1.5 4 4 6.5 8 8l2-4 '
           '7 3v6c0 1.7-1.3 3-3 3C13 29 3 19 3 7c0-1.7 1.3-3 3-3z" '
           'fill="#14304d"/></svg>')
_GLOBUS = (f'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="none" '
           f'stroke="{GOLD}" stroke-width="2"/><path d="M2 12h20M12 2c3 3.4 3 '
           f'16.6 0 20M12 2c-3 3.4-3 16.6 0 20" fill="none" stroke="{GOLD}" '
           f'stroke-width="2"/></svg>')
_BRIEF = (f'<svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" '
          f'rx="2" fill="none" stroke="{GOLD}" stroke-width="2"/><path d="M3 7l9 '
          f'6 9-6" fill="none" stroke="{GOLD}" stroke-width="2" '
          f'stroke-linejoin="round"/></svg>')

#: Die vier Merkmale unter dem Aufruf. Sie sagen nichts über das einzelne
#: Stück - das ist Absicht: Sie sind Wiedererkennung, wie das Logo.
FUSS_PRODUKT = [
    ("SICHERE", "BESTELLUNG",
     '<path d="M24 4l16 6v14c0 12-8 18-16 21-8-3-16-9-16-21V10z" fill="none" '
     'stroke="#fff" stroke-width="3"/><path d="M16 24l6 6 11-12" fill="none" '
     'stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("SCHNELLE", "LIEFERUNG",
     '<path d="M3 13h24v16H3z" fill="none" stroke="#fff" stroke-width="3"/>'
     '<path d="M27 19h8l6 7v3h-14z" fill="none" stroke="#fff" stroke-width="3"/>'
     '<circle cx="13" cy="33" r="4" fill="none" stroke="#fff" stroke-width="3"/>'
     '<circle cx="33" cy="33" r="4" fill="none" stroke="#fff" stroke-width="3"/>'),
    ("TOP", "QUALITÄT",
     '<circle cx="24" cy="20" r="14" fill="none" stroke="#fff" stroke-width="3"/>'
     '<path d="M24 13l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4-3.9-3.8 '
     '5.4-.8z" fill="#fff"/><path d="M17 33l-3 11 10-5 10 5-3-11" fill="none" '
     'stroke="#fff" stroke-width="3" stroke-linejoin="round"/>'),
    ("KUNDENSERVICE", "FÜR SIE DA",
     '<path d="M8 28v-6a16 16 0 0132 0v6" fill="none" stroke="#fff" stroke-width="3"/>'
     '<rect x="4" y="26" width="9" height="13" rx="4" fill="none" stroke="#fff" '
     'stroke-width="3"/><rect x="35" y="26" width="9" height="13" rx="4" '
     'fill="none" stroke="#fff" stroke-width="3"/>'),
]

FUSS_TIPP = [FUSS_PRODUKT[2], FUSS_PRODUKT[1]]


def _gerüst_css() -> str:
    """Alles, was beide Formate teilen. Hier ändern heißt: beide ändern."""
    return f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{BREITE}px; height:{HOEHE}px; overflow:hidden; color:#fff;
  font-family:{SCHRIFT}; background:{NACHT}; position:relative; }}

/* Linke Fotospalte, nach rechts ins Dunkel auslaufend. */
.foto {{ position:absolute; inset:0 auto 0 0; width:400px; height:100%;
  object-fit:cover; object-position:50% 45%; }}
.blende {{ position:absolute; inset:0 auto 0 250px; width:200px;
  background:linear-gradient(90deg,{NACHT}00,{NACHT}cc 70%,{NACHT}); }}
.schleier {{ position:absolute; inset:0 auto 0 0; width:400px;
  background:linear-gradient(180deg,{TIEFER}22 0%,{TIEFER}30 40%,
    {TIEFER}55 72%,{TIEFER}88 100%); }}
.stempel {{ position:absolute; left:20px; top:300px; width:360px;
  text-align:center; }}
.stempel svg {{ width:72px; height:72px; margin-bottom:6px; }}
.stempel .t {{ font-size:78px; line-height:.95; letter-spacing:1px;
  text-shadow:0 3px 12px #000000ff, 0 0 46px #000000ee; }}
.stempel .w {{ font-family:Georgia,serif; font-style:italic; font-size:40px;
  color:{HELLGOLD}; text-shadow:0 3px 12px #000000ff, 0 0 30px #000000dd; }}
.stempel .strich {{ width:150px; height:3px; background:{GOLD};
  margin:6px auto 0; }}

/* Das weiße Logofeld oben rechts. */
.logo {{ position:absolute; top:0; right:0; width:700px; height:128px;
  background:#fff; clip-path:polygon(92px 0,100% 0,100% 100%,0 100%);
  display:flex; align-items:center; padding:0 50px 0 132px; }}
.logo img {{ width:100%; height:auto; }}
.logo b {{ font-size:46px; color:{SCHRIFT_TIEF}; letter-spacing:-1px; }}

/* Überschrift und Vorspann, linksbündig im Inhaltsbereich. */
h1 {{ position:absolute; left:430px; top:156px; width:640px;
  text-shadow:0 5px 18px #00000055; }}
.vorspann {{ position:absolute; left:430px; width:640px; color:#dce6f1; }}

/* Die goldgerahmten Kästen der rechten Spalte. */
.kasten {{ position:absolute; right:40px; width:396px; border:2px solid {GOLD};
  border-radius:14px; background:{TIEFER}e6; padding:14px 16px 10px; }}
.kasten > b {{ display:block; font-size:18px; color:{GOLD}; margin-bottom:10px; }}
.kasten li {{ list-style:none; display:flex; gap:8px; align-items:flex-start;
  font-size:14.5px; line-height:1.34; margin-bottom:9px; color:{SCHRIFT_HELL}; }}
.kasten p {{ font-size:15px; line-height:1.38; color:{SCHRIFT_HELL}; }}
.hk {{ width:15px; height:15px; flex:none; margin-top:1px; }}

/* Aufruf, Merkmalszeile und Kontakt – unten, in beiden gleich. */
.cta {{ position:absolute; left:430px; height:72px; background:{GOLD};
  color:#14304d; display:flex; align-items:center; gap:18px; padding:0 26px; }}
.cta svg {{ width:44px; height:44px; flex:none; }}
.fuss {{ position:absolute; left:430px; bottom:34px; display:flex; gap:30px;
  align-items:center; }}
.fuss > div {{ display:flex; gap:11px; align-items:center; font-size:16px;
  line-height:1.22; }}
.fuss svg {{ width:36px; height:36px; flex:none; }}
.fuss b {{ font-size:17px; }}

.kontakt {{ position:absolute; right:40px; bottom:30px; width:396px;
  border:2px solid {GOLD}; border-radius:14px; background:{TIEFER}e6;
  padding:15px 20px 15px 17px; display:flex; gap:15px; align-items:center; }}
.kontakt .kreis {{ width:54px; height:54px; border-radius:50%; background:{GOLD};
  flex:none; display:flex; align-items:center; justify-content:center; }}
.kontakt .kreis svg {{ width:30px; height:30px; }}
.kontakt b {{ display:block; font-size:14.5px; color:{GOLD}; }}
.kontakt .nr {{ font-size:30px; line-height:1.14; }}
.kontakt .zt {{ font-size:15px; color:#dce6f1; margin-bottom:4px; }}
.kontakt .zeile {{ display:flex; gap:8px; align-items:center; font-size:15.5px;
  color:#eef3f8; margin-top:3px; }}
.kontakt .zeile svg {{ width:16px; height:16px; flex:none; }}
"""


def _stempel(wort: str) -> str:
    """Der Schriftzug auf dem Foto, etwa »TIPP der Woche«.

    Beim Produkt sagt die Überschrift selbst, um welches Format es sich
    handelt; beim Tipp steht dort das Thema, und die Kennzeichnung muss
    woandershin. Der Schatten ist kein Zierrat – auf einem hellen Foto wäre
    die Schrift sonst nicht zu lesen, und welches Foto kommt, weiß niemand.
    """
    return f"""<div class="stempel">
  <svg viewBox="0 0 48 48"><path d="M24 5a13 13 0 00-7 24v5h14v-5a13 13 0 00-7-24z"
    fill="none" stroke="{GOLD}" stroke-width="3"/><path d="M18 39h12M20 44h8"
    stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/></svg>
  <div class="t">{html.escape(wort)}</div>
  <div class="w">der Woche</div><div class="strich"></div>
</div>"""


def _seite(eigenes_css: str, koerper: str, foto: str | None,
           marke: dict[str, Any]) -> str:
    """Rahmen plus Füllung. Der einzige Ort, an dem eine Seite entsteht."""
    bild = f'<img class="foto" src="{Path(foto).name}" alt="">' if foto else \
        f'<div class="foto" style="background:{TIEFER}"></div>'
    return (f'<!doctype html><meta charset="utf-8"><style>{_gerüst_css()}'
            f'{eigenes_css}</style>\n{bild}\n<div class="blende"></div>\n'
            f'{_kopf(marke)}\n{koerper}\n{_kontakt(marke)}\n')


# -- Die beiden Füllungen --------------------------------------------------


def produkt_seite(daten: dict[str, Any], marke: dict[str, Any]) -> str:
    """»Produkt der Woche«: weiße Karte mit Merkmalen und Preis."""
    merkmale = "".join(f'<li>{_haken("gross")}<span>{html.escape(m)}</span></li>'
                       for m in daten["merkmale"][:MERKMALE])
    ueber = "".join(f'<li>{_haken()}<span>{html.escape(u)}</span></li>'
                    for u in (marke.get("ueber") or []))
    eigenes = f"""
h1 {{ font-size:104px; line-height:.94; letter-spacing:-2px; }}
h1 .der {{ font-family:Georgia,serif; font-style:italic; font-size:56px;
  color:{HELLGOLD}; margin:0 18px 0 0; display:inline-block;
  border-bottom:3px solid {HELLGOLD}; padding:0 4px 2px; }}
.balken {{ position:absolute; left:430px; top:386px; background:{GOLD};
  color:#14304d; font-size:30px; padding:9px 24px; }}
.vorspann {{ top:452px; font-size:31px; color:#eef3f8; }}
.kasten {{ top:156px; }}

.karte {{ position:absolute; left:430px; right:40px; top:498px; height:270px;
  overflow:hidden; background:{PAPIER}; border-radius:22px;
  color:{SCHRIFT_TIEF}; display:flex; gap:22px; padding:20px 24px; }}
.mitte {{ flex:1; min-width:0; }}
.mitte h2 {{ font-size:34px; font-weight:700; letter-spacing:-.5px;
  margin-bottom:17px; }}
.mitte li {{ list-style:none; display:flex; gap:10px; align-items:flex-start;
  font-size:21px; line-height:1.3; margin-bottom:12px; }}
.gross {{ width:22px; height:22px; flex:none; margin-top:2px; }}
/* Die Farbe muss hier stehen: Die Box liegt in der weißen Karte und erbte
   sonst deren dunkle Schrift - dunkel auf dunkel, der Preis unlesbar. */
.preis {{ width:300px; flex:none; background:{TIEFER}; color:#fff;
  border-radius:12px; text-align:center; padding-top:18px; overflow:hidden;
  display:flex; flex-direction:column; }}
.alt {{ font-size:25px; text-decoration:line-through; opacity:.85; }}
.ab {{ font-size:17px; letter-spacing:2px; opacity:.8; margin:3px 0 2px; }}
.neu {{ font-size:66px; line-height:1.05; font-weight:700; letter-spacing:-2px; }}
.sparen {{ background:{GOLD}; color:#14304d; font-size:20px; padding:13px 6px;
  margin-top:auto; line-height:1.25; }}
.cta {{ width:412px; top:846px; font-size:31px;
  clip-path:polygon(0 0,100% 0,calc(100% - 26px) 100%,0 100%); }}
.fuss {{ bottom:auto; top:778px; }}
.gueltig {{ position:absolute; left:430px; bottom:22px; font-size:17.5px;
  opacity:.9; }}
"""
    preis = ""
    if daten.get("preis_alt"):
        preis += f'<div class="alt">statt {html.escape(daten["preis_alt"])}</div>'
    preis += (f'<div class="ab">ab</div>'
              f'<div class="neu">{html.escape(daten["preis"])}</div>')
    if daten.get("ersparnis"):
        preis += (f'<div class="sparen">Sie sparen<br>'
                  f'{html.escape(daten["ersparnis"])}</div>')

    koerper = f"""<h1>PRODUKT<br><span class="der">der</span>WOCHE</h1>
<div class="balken">TOP QUALITÄT – TOP PREIS!</div>
<div class="vorspann">{html.escape(daten["unterzeile"])}</div>
<div class="kasten"><b>ÜBER {html.escape(str(marke.get("name") or ""))}</b>
  <ul>{ueber}</ul></div>
<div class="karte">
  <div class="mitte"><h2>{html.escape(daten["name"])}</h2><ul>{merkmale}</ul></div>
  <div class="preis">{preis}</div>
</div>
{_fuss(FUSS_PRODUKT)}
<div class="cta">{_WARENKORB} JETZT BESTELLEN!</div>
<div class="gueltig">{html.escape(daten["gueltig"])}</div>"""
    return _seite(eigenes, koerper, daten.get("bild"), marke)


def tipp_seite(daten: dict[str, Any], marke: dict[str, Any]) -> str:
    """»Tipp der Woche«: drei Blöcke, zwei Merkkästen."""
    bloecke = ""
    for b in daten["bloecke"]:
        punkte = "".join(f'<li>{_haken()}<span>{b_punkt}</span></li>'
                         for b_punkt in b["punkte"])
        kopf = html.escape(b["titel"]).replace("\n", "<br>")
        bloecke += (f'<div class="block" style="--ton:{b["farbe"]}">'
                    f'<div class="bkopf"><b>{kopf}</b>'
                    f'<i>{html.escape(b["unter"])}</i></div>'
                    f'<ul>{punkte}</ul></div>')
    beachten = "".join(f'<li>{_haken()}<span>{html.escape(p)}</span></li>'
                       for p in daten["beachten"])
    eigenes = f"""
h1 {{ font-size:46px; line-height:1.06; letter-spacing:-.5px; }}
h1 span {{ color:{GOLD}; }}
.vorspann {{ top:266px; font-size:19px; line-height:1.38; }}
.kasten.warum {{ top:156px; display:flex; gap:13px; }}
.kasten.warum svg {{ width:32px; height:32px; flex:none; }}
.kasten.beachten {{ top:346px; }}
.kasten.wissen {{ top:640px; }}

.bloecke {{ position:absolute; left:430px; top:346px; width:648px;
  display:flex; gap:12px; }}
.block {{ flex:1; background:#ffffff0d; border:1px solid #ffffff26;
  border-radius:14px; overflow:hidden; display:flex; flex-direction:column; }}
.bkopf {{ background:var(--ton); padding:12px 12px 11px; }}
.bkopf b {{ display:block; font-size:18.5px; line-height:1.1; }}
.bkopf i {{ display:block; font-style:normal; font-size:12.5px; opacity:.85;
  margin-top:4px; }}
.block ul {{ padding:12px 11px 14px; }}
.block li {{ list-style:none; display:flex; gap:7px; align-items:flex-start;
  font-size:13.5px; line-height:1.32; margin-bottom:9px; color:#e9eff6; }}
.cta {{ width:648px; top:846px; font-size:21px; border-radius:10px; }}
"""
    koerper = f"""<div class="schleier"></div>{_stempel("TIPP")}
<h1>{html.escape(daten["titel"])}<br>
  <span>{html.escape(daten["unterzeile"])}</span></h1>
<div class="vorspann">{html.escape(daten["vorspann"])}</div>
<div class="kasten warum">{_INFO}
  <div><b>WARUM GERADE JETZT?</b><p>{html.escape(daten["warum"])}</p></div></div>
<div class="bloecke">{bloecke}</div>
<div class="kasten beachten"><b>WICHTIG ZU BEACHTEN</b><ul>{beachten}</ul></div>
<div class="kasten wissen"><b>GUT ZU WISSEN</b>
  <p>{html.escape(daten["wissen"])}</p></div>
{_fuss(FUSS_TIPP)}
<div class="cta">{_SPRECHBLASE} {html.escape(daten["cta"])}</div>"""
    return _seite(eigenes, koerper, daten.get("bild"), marke)


_WARENKORB = ('<svg viewBox="0 0 48 48"><path d="M3 6h7l6 25h22l5-17H13" '
              'fill="none" stroke="#14304d" stroke-width="3.4" '
              'stroke-linejoin="round"/><circle cx="19" cy="40" r="4" '
              'fill="#14304d"/><circle cx="35" cy="40" r="4" fill="#14304d"/></svg>')
_SPRECHBLASE = ('<svg viewBox="0 0 48 48"><path d="M8 10h32v24H26l-9 8v-8H8z" '
                'fill="none" stroke="#14304d" stroke-width="3.4" '
                'stroke-linejoin="round"/><path d="M16 19h16M16 26h11" '
                'stroke="#14304d" stroke-width="3.4" stroke-linecap="round"/></svg>')
_INFO = (f'<svg viewBox="0 0 48 48"><circle cx="24" cy="24" r="21" fill="none" '
         f'stroke="{GOLD}" stroke-width="3"/><path d="M24 21v14" stroke="{GOLD}" '
         f'stroke-width="4" stroke-linecap="round"/><circle cx="24" cy="14" '
         f'r="2.6" fill="{GOLD}"/></svg>')


# -- Ausgeben --------------------------------------------------------------


def zeichnen(seite: str, ziel: Path, mitbringen: list[Path] | None = None) -> Path:
    """Die Seite als PNG ablegen und den Pfad zurückgeben.

    `mitbringen` sind Dateien, die die Seite braucht – Foto und Logo. Sie
    werden neben die HTML kopiert, weil `--screenshot` beim `load`-Ereignis
    auslöst: Was nicht sofort da ist, fehlt im Bild.
    """
    if not vorhanden():
        raise GrafikFehler(nicht_da())
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="postkutsche-grafik-") as ordner:
        arbeit = Path(ordner)
        for datei in mitbringen or []:
            if datei and Path(datei).exists():
                shutil.copy(datei, arbeit / Path(datei).name)
        quelle = arbeit / "seite.html"
        quelle.write_text(seite, encoding="utf-8")
        # Eigenes Profil: Ein bereits laufender Firefox lehnt den Aufruf sonst
        # mit »is already running« ab, und das Bild entsteht nie.
        profil = arbeit / "profil"
        profil.mkdir()
        befehl = [BEFEHL, "--headless", "--profile", str(profil),
                  f"--window-size={BREITE},{HOEHE}",
                  "--screenshot", str(ziel), quelle.as_uri()]
        try:
            lauf = subprocess.run(befehl, capture_output=True, text=True,
                                  timeout=ZEITLIMIT)
        except FileNotFoundError:
            raise GrafikFehler(nicht_da()) from None
        except subprocess.TimeoutExpired:
            raise GrafikFehler(
                f"Firefox hat nach {ZEITLIMIT} Sekunden kein Bild geliefert."
            ) from None
    if not ziel.exists():
        meldung = (lauf.stderr or lauf.stdout or "").strip()
        raise GrafikFehler(f"Firefox hat kein Bild geschrieben: {meldung[:300]}")
    return ziel


def alternativtext(art: str, daten: dict[str, Any]) -> str:
    """Was im Bild steht, als Satzfolge – für alle, die es nicht sehen.

    Die ganze Aussage steckt in der Grafik: Preis, Merkmale, der ganze Tipp.
    Wer einen Vorleser benutzt, bekäme davon nichts. Weil das Bild aus einem
    Datensatz entsteht, kostet die Beschreibung nichts extra – sie kommt aus
    denselben Feldern.
    """
    if art == "produkt":
        teile = [f"Produkt der Woche: {daten['name']}.", daten["unterzeile"]]
        teile += [m.rstrip(".") + "." for m in daten["merkmale"][:MERKMALE]]
        if daten.get("preis_alt"):
            teile.append(f"Preis {daten['preis']} statt {daten['preis_alt']}.")
        else:
            teile.append(f"Preis {daten['preis']}.")
        teile.append(daten["gueltig"] + ".")
        return " ".join(t.strip() for t in teile if t)
    teile = [f"Tipp der Woche: {daten['titel']} {daten['unterzeile']}.",
             daten["vorspann"]]
    for block in daten["bloecke"]:
        kopf = block["titel"].replace("\n", " ")
        punkte = " ".join(_ohne_auszeichnung(p) for p in block["punkte"])
        teile.append(f"{kopf}: {punkte}")
    teile.append("Wichtig zu beachten: " + " ".join(daten["beachten"]))
    teile.append(daten["wissen"])
    return " ".join(t.strip() for t in teile if t)


def _ohne_auszeichnung(text: str) -> str:
    """Die Punkte dürfen <b> enthalten; im Alternativtext stört das."""
    import re

    return re.sub(r"<[^>]+>", "", text)
