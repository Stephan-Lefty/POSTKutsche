"""Was alle Quellen gemeinsam brauchen: holen, entziffern, aufräumen.

Bewusst `urllib` aus der Standardbibliothek und nicht `requests`. Es sind ein
paar Dutzend Anfragen am Tag gegen eine Handvoll bekannter Adressen – dafür
lohnt keine
Abhängigkeit, die in zwei Jahren eine andere Hauptfassung hat.
"""

from __future__ import annotations

import gzip
import html
import json
import re
import urllib.error
import urllib.request
from typing import Any

from .. import __version__

# Wer wir sind. Ein ehrliches Kennzeichen ist keine Höflichkeit, sondern
# Eigennutz: Wenn ein Abruf einem Serverbetreuer auffällt, soll er sehen,
# wer da klopft, statt einen anonymen Kratzer zu sperren.
KENNZEICHEN = f"POSTKutsche/{__version__} (+https://github.com/Stephan-Lefty/POSTKutsche)"

ZEITLIMIT = 30


class AbrufFehler(Exception):
    """Ein Abruf ging schief. Die Meldung ist für Menschen gedacht."""


def holen(adresse: str, kopfzeilen: dict[str, str] | None = None,
          daten: bytes | None = None) -> bytes:
    """Holt eine Adresse. `daten` macht daraus eine POST-Anfrage."""
    anfrage = urllib.request.Request(adresse, data=daten)
    anfrage.add_header("User-Agent", KENNZEICHEN)
    # Eine Seitenkarte kann leicht 800 kB groß sein. Ungepackt zu übertragen,
    # was der Server auch gepackt liefert, ist unhöflich.
    anfrage.add_header("Accept-Encoding", "gzip")
    for name, wert in (kopfzeilen or {}).items():
        anfrage.add_header(name, wert)

    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            roh = antwort.read()
            if antwort.headers.get("Content-Encoding") == "gzip":
                roh = gzip.decompress(roh)
            return roh
    except urllib.error.HTTPError as fehler:
        # Die häufigen Fälle beim Namen nennen. »HTTP Error 401« sagt einem
        # niemandem, was zu tun ist.
        if fehler.code == 401:
            raise AbrufFehler(
                f"{adresse} verlangt einen Zugangsschlüssel (401). Bei Shopware "
                "ist das der Zugangsschlüssel des Verkaufskanals."
            ) from fehler
        if fehler.code == 403:
            raise AbrufFehler(
                f"{adresse} weist uns ab (403). Möglicherweise sperrt eine "
                "Firewall oder ein Sicherheits-Plugin den Zugriff."
            ) from fehler
        if fehler.code == 404:
            raise AbrufFehler(f"{adresse} gibt es nicht (404).") from fehler
        raise AbrufFehler(f"{adresse} antwortet mit {fehler.code}.") from fehler
    except urllib.error.URLError as fehler:
        raise AbrufFehler(f"{adresse} nicht erreichbar: {fehler.reason}") from fehler


def json_holen(adresse: str, kopfzeilen: dict[str, str] | None = None,
               rumpf: dict[str, Any] | None = None) -> Any:
    """Holt eine Adresse und entziffert die Antwort als JSON."""
    daten = None
    kopf = dict(kopfzeilen or {})
    if rumpf is not None:
        daten = json.dumps(rumpf).encode("utf-8")
        kopf.setdefault("Content-Type", "application/json")

    roh = holen(adresse, kopf, daten)
    try:
        return json.loads(roh)
    except json.JSONDecodeError as fehler:
        anfang = roh[:120].decode("utf-8", "replace")
        raise AbrufFehler(
            f"{adresse} liefert kein JSON. Anfang der Antwort: {anfang!r}"
        ) from fehler


def kopfzeile_holen(adresse: str, name: str) -> str | None:
    """Eine einzelne Kopfzeile einer Antwort, ohne den Rumpf zu lesen.

    Für Auskünfte, die WordPress nur im Kopf gibt: Wie viele Beiträge es
    insgesamt sind, steht in `X-WP-Total` und in keinem Feld der Antwort. Die
    Zahl selbst zusammenzuzählen geht daneben, weil ein Beitrag in zwei
    Kategorien steht und dann doppelt zählt - bei Naturlust wären das 98
    statt 52.

    Fehlt die Kopfzeile oder antwortet die Seite nicht, kommt None zurück:
    Eine fehlende Zahl in der Anzeige ist ärgerlich, ein Abbruch wäre schlimmer.
    """
    anfrage = urllib.request.Request(adresse, method="HEAD")
    anfrage.add_header("User-Agent", KENNZEICHEN)
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            return antwort.headers.get(name)
    except (urllib.error.URLError, OSError):
        return None


def text_holen(adresse: str) -> str:
    """Holt eine Seite als Text. Fällt bei krummer Kodierung nicht um."""
    return holen(adresse).decode("utf-8", "replace")


def text_und_ziel(adresse: str) -> tuple[str, str]:
    """Wie `text_holen`, gibt aber auch zurück, wo man tatsächlich gelandet ist.

    **Wer umleitet, sagt damit etwas.** Ein alter Shop, dessen Seitenkarte seit
    Jahren nicht gepflegt wurde, schickt abgekündigte Produktadressen auf die
    Kategorieübersicht - manchmal sogar auf eine andere Kategorie, als der
    Adressname verspricht. Wer nur den Inhalt liest und die Endadresse
    wegwirft, hält dann eine Übersichtsseite für ein Produkt und bewirbt unter
    dem Namen einer Stahltür einen Text über Holztüren. Am 2026-08-28 an
    echten Adressen beobachtet: von zwölf Stichproben führte keine einzige
    unverändert zum Ziel.
    """
    anfrage = urllib.request.Request(adresse)
    anfrage.add_header("User-Agent", KENNZEICHEN)
    anfrage.add_header("Accept-Encoding", "gzip")
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            roh = antwort.read()
            if antwort.headers.get("Content-Encoding") == "gzip":
                roh = gzip.decompress(roh)
            return roh.decode("utf-8", "replace"), antwort.url
    except urllib.error.HTTPError as fehler:
        raise AbrufFehler(f"{adresse} antwortet mit {fehler.code}.") from fehler
    except urllib.error.URLError as fehler:
        raise AbrufFehler(f"{adresse} nicht erreichbar: {fehler.reason}") from fehler


# -- HTML aufräumen --------------------------------------------------------

_SKRIPTE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
_ABSATZENDE = re.compile(r"</(p|div|h[1-6]|li|tr|blockquote)>", re.IGNORECASE)
_UMBRUCH = re.compile(r"<br\s*/?>", re.IGNORECASE)
_MARKE = re.compile(r"<[^>]+>")
_LEERZEILEN = re.compile(r"\n{3,}")


def entmarken(roh: str) -> str:
    """Macht aus HTML lesbaren Fließtext.

    Kein vollwertiger Umwandler, und das ist Absicht: Der Text geht an Claude,
    der daraus ohnehin etwas Neues schreibt. Was zählt, ist, dass Absätze
    Absätze bleiben – ein Blogbeitrag ohne Umbrüche wird zu einer Textwurst,
    und die Zusammenfassung daraus wird schlechter.
    """
    text = _SKRIPTE.sub(" ", roh)
    text = _UMBRUCH.sub("\n", text)
    text = _ABSATZENDE.sub("\n\n", text)
    text = _MARKE.sub("", text)
    text = html.unescape(text)
    # Geschütztes Leerzeichen sieht aus wie ein Leerzeichen und ist keins.
    text = text.replace("\xa0", " ")
    zeilen = [zeile.strip() for zeile in text.splitlines()]
    return _LEERZEILEN.sub("\n\n", "\n".join(zeilen)).strip()


_OG = re.compile(
    r"""<meta[^>]+(?:property|name)\s*=\s*["']og:(\w+)["'][^>]*"""
    r"""content\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)
_OG_UMGEKEHRT = re.compile(
    r"""<meta[^>]+content\s*=\s*["']([^"']*)["'][^>]*"""
    r"""(?:property|name)\s*=\s*["']og:(\w+)["']""",
    re.IGNORECASE,
)


def og_angaben(roh: str) -> dict[str, str]:
    """Liest die og:-Angaben aus einer Seite.

    Beide Reihenfolgen werden erkannt – manche Seiten schreiben `content` vor
    `property` – ältere Seitenvorlagen tun das regelmäßig.
    """
    gefunden: dict[str, str] = {}
    for name, wert in _OG.findall(roh):
        gefunden.setdefault(name.lower(), html.unescape(wert).strip())
    for wert, name in _OG_UMGEKEHRT.findall(roh):
        gefunden.setdefault(name.lower(), html.unescape(wert).strip())
    return gefunden


_BILD = re.compile(r"""<img[^>]+src\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def erstes_bild(roh: str) -> str | None:
    """Das erste Bild in einem HTML-Text.

    Der Rückfall für Seiten ohne gepflegtes Beitragsbild. Es gibt Blogs, die bei
    keinem einzigen Beitrag eines gesetzt haben, obwohl in jedem Beitrag eines
    im Text steht.
    """
    for treffer in _BILD.findall(roh):
        adresse = html.unescape(treffer).strip()
        # WordPress liefert Adressen in JSON mit maskierten Schrägstrichen.
        adresse = adresse.replace("\\/", "/")
        if adresse.startswith(("http://", "https://")):
            return adresse
    return None
