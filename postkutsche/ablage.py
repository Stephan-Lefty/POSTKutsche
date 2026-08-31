"""Die Ablage: eine SQLite-Datei, in der alles steht.

Warum SQLite und nicht ein Ordner voller JSON-Dateien: Ein Kalender fragt
ständig nach »alle Beiträge zwischen zwei Zeitpunkten, aber nur von diesen
Projekten«. Das ist eine Datenbankfrage. Mit Dateien müsste man jedes Mal alles
lesen.

Zeiten stehen hier ausnahmslos als ISO-8601 in UTC. Anzeige und Eingabe
rechnen nach Europe/Berlin um – siehe `zeiten.py`. Wer Ortszeit in die
Datenbank schreibt, bekommt zweimal im Jahr eine Stunde geschenkt oder
gestohlen, und merkt es im Oktober.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

# Die Fassung des Schemas. Wird erhöht, sobald sich Tabellen ändern; `_wandeln`
# hebt bestehende Ablagen dann Schritt für Schritt an.
#
# 2 (2026-08-31): ein zweites Bild je Fassung, Spalte `bild_pfad2`.
SCHEMA_FASSUNG = 2

# Zustände eines Projekts.
PROJEKT_AKTIV = "aktiv"
PROJEKT_PAUSIERT = "pausiert"

# Zustände eines Beitrags. Der Beitrag ist die Klammer um mehrere Fassungen –
# eine je Netzwerk.
BEITRAG_ENTWURF = "entwurf"
# Claude hat etwas nicht entscheiden können und fragt. Solche Beiträge lassen
# sich nicht freigeben, bevor die Frage beantwortet ist – siehe `freigeben`.
BEITRAG_RUECKFRAGE = "rueckfrage"
BEITRAG_FREIGEGEBEN = "freigegeben"
BEITRAG_ERLEDIGT = "erledigt"
BEITRAG_VERWORFEN = "verworfen"

# Zustände einer einzelnen Fassung. `abgeholt` heißt: von Hand veröffentlicht,
# der Weg für Facebook und Instagram, solange Metas App-Prüfung nicht durch ist.
FASSUNG_OFFEN = "offen"
FASSUNG_GESENDET = "gesendet"
FASSUNG_ABGEHOLT = "abgeholt"
FASSUNG_GESCHEITERT = "gescheitert"

# Wie eine Fassung ihren Weg nach draußen findet.
VERSAND_SCHNITTSTELLE = "schnittstelle"
VERSAND_HAND = "hand"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projekte (
    id              INTEGER PRIMARY KEY,
    kennung         TEXT    NOT NULL UNIQUE,   -- kurz, klein, für die Kommandozeile
    name            TEXT    NOT NULL,          -- wie es im Kalender steht
    adresse         TEXT    NOT NULL,          -- https://…
    art             TEXT    NOT NULL,          -- wordpress | shopware | seitenkarte
    farbe           TEXT    NOT NULL,          -- #rrggbb, für die Kärtchen
    zustand         TEXT    NOT NULL DEFAULT 'aktiv',
    freigabe_noetig INTEGER NOT NULL DEFAULT 1,
    einstellungen   TEXT    NOT NULL DEFAULT '{}',  -- JSON, je nach Art verschieden
    angelegt        TEXT    NOT NULL,
    zuletzt_geholt  TEXT
);

-- Was auf den eigenen Seiten gefunden wurde: ein Blogbeitrag, ein Produkt.
-- Noch kein Beitrag für ein Netzwerk, nur der Anlass dafür.
CREATE TABLE IF NOT EXISTS inhalte (
    id              INTEGER PRIMARY KEY,
    projekt_id      INTEGER NOT NULL REFERENCES projekte(id) ON DELETE CASCADE,
    fremd_id        TEXT    NOT NULL,          -- WP-Beitragsnummer, Shopware-Id, sonst die Adresse
    titel           TEXT    NOT NULL,
    text            TEXT    NOT NULL DEFAULT '',
    adresse         TEXT    NOT NULL,
    bild_adresse    TEXT,
    veroeffentlicht TEXT,                      -- Datum laut Quelle, UTC
    gefunden        TEXT    NOT NULL,
    UNIQUE (projekt_id, fremd_id)
);

CREATE TABLE IF NOT EXISTS beitraege (
    id          INTEGER PRIMARY KEY,
    projekt_id  INTEGER NOT NULL REFERENCES projekte(id) ON DELETE CASCADE,
    inhalt_id   INTEGER          REFERENCES inhalte(id) ON DELETE SET NULL,
    geplant     TEXT    NOT NULL,              -- UTC
    zustand     TEXT    NOT NULL DEFAULT 'entwurf',
    notiz       TEXT    NOT NULL DEFAULT '',
    -- Woher dieser Beitrag stammt, wenn er die Wiederholung eines früheren ist.
    -- ON DELETE SET NULL: Wird der Urahn gelöscht, bleibt die Wiederholung
    -- stehen und verliert nur ihre Herkunft.
    wiederholung_von INTEGER     REFERENCES beitraege(id) ON DELETE SET NULL,
    angelegt    TEXT    NOT NULL,
    geaendert   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS beitraege_nach_zeit ON beitraege (geplant);

CREATE TABLE IF NOT EXISTS fassungen (
    id          INTEGER PRIMARY KEY,
    beitrag_id  INTEGER NOT NULL REFERENCES beitraege(id) ON DELETE CASCADE,
    netzwerk    TEXT    NOT NULL,              -- mastodon | linkedin | facebook | instagram
    text        TEXT    NOT NULL DEFAULT '',
    schlagworte TEXT    NOT NULL DEFAULT '',   -- durch Leerzeichen getrennt, ohne Raute
    bild_pfad   TEXT,                          -- zugeschnittenes Bild auf der Platte
    -- Das zweite Bild. Zwei Spalten statt einer eigenen Tabelle: Es sind
    -- genau zwei, die Reihenfolge ist damit ohne Sortierspalte eindeutig,
    -- und jede Lesestelle bleibt eine Abfrage ohne Verbund. Kommt einmal
    -- ein drittes dazu, ist die Tabelle fällig - dann weiß man auch, wie
    -- viele es werden.
    bild_pfad2  TEXT,
    versandart  TEXT    NOT NULL DEFAULT 'schnittstelle',
    zustand     TEXT    NOT NULL DEFAULT 'offen',
    -- Was Claude nicht entscheiden konnte. Steht hier drin, ist der Beitrag
    -- nicht freizugeben, bevor jemand geantwortet hat.
    rueckfrage  TEXT,
    -- Ob am Text von Hand gearbeitet wurde. Daran hängt die Warnung vor
    -- »neu schreiben lassen«: Handarbeit darf nicht stillschweigend
    -- überschrieben werden.
    von_hand    INTEGER NOT NULL DEFAULT 0,
    gesendet    TEXT,                          -- UTC
    fremd_adresse TEXT,                        -- Adresse des veröffentlichten Beitrags
    fehler      TEXT,
    UNIQUE (beitrag_id, netzwerk)
);

-- Ein Konto in einem Netzwerk. Geheimnisse stehen hier nicht: Token liegen im
-- Schlüsselbund, ersatzweise in ~/.config/postkutsche/zugaenge.json mit Rechten
-- 600. Hier steht nur, welches Konto gemeint ist und wie es erreicht wird.
CREATE TABLE IF NOT EXISTS konten (
    id            INTEGER PRIMARY KEY,
    netzwerk      TEXT    NOT NULL,
    kennung       TEXT    NOT NULL UNIQUE,
    anzeigename   TEXT    NOT NULL DEFAULT '',
    versandart    TEXT    NOT NULL DEFAULT 'schnittstelle',
    einstellungen TEXT    NOT NULL DEFAULT '{}',  -- JSON: Instanzadresse, Seiten-Id, …
    angelegt      TEXT    NOT NULL
);

-- Welches Projekt in welches Konto sendet. Ein Projekt kann in mehrere Konten,
-- ein Konto mehrere Projekte bedienen.
CREATE TABLE IF NOT EXISTS projekt_konten (
    projekt_id INTEGER NOT NULL REFERENCES projekte(id) ON DELETE CASCADE,
    konto_id   INTEGER NOT NULL REFERENCES konten(id) ON DELETE CASCADE,
    PRIMARY KEY (projekt_id, konto_id)
);

-- Was der Betreiber auf eine Rückfrage geantwortet hat. Ohne diese Tabelle
-- endet jede Antwort beim einzelnen Beitrag, und beim nächsten Produkt
-- derselben Art wird dasselbe wieder gefragt.
--
-- `adresse` unterscheidet die beiden Arten von Wissen. Leer heißt: gilt für
-- das ganze Projekt und geht bei jedem Entwurf mit. Steht eine Adresse drin,
-- gilt es nur für dieses eine Produkt. Der Unterschied ist der Kern der
-- Sache: »Die Lieferzeit gehört nicht in den Text« ist eine Grundsatzent-
-- scheidung, »diese Tür gibt es in 2000 und 2125 mm« ist eine Produktangabe.
-- Wer beides gleich behandelt, füttert Claude nach einem halben Jahr mit
-- dreißig Sonderfällen und bekommt schlechtere Texte statt bessere.
--
-- Leerer Text statt NULL, weil SQLite NULL-Werte in einem UNIQUE als
-- verschieden ansieht - mit NULL liesse sich dieselbe allgemeine Antwort
-- beliebig oft eintragen.
CREATE TABLE IF NOT EXISTS wissen (
    id         INTEGER PRIMARY KEY,
    projekt_id INTEGER NOT NULL REFERENCES projekte(id) ON DELETE CASCADE,
    adresse    TEXT    NOT NULL DEFAULT '',
    frage      TEXT    NOT NULL DEFAULT '',
    antwort    TEXT    NOT NULL,
    angelegt   TEXT    NOT NULL,
    UNIQUE (projekt_id, adresse, antwort)
);

CREATE TABLE IF NOT EXISTS schema_stand (
    fassung INTEGER NOT NULL
);
"""


class HandarbeitWuerdeVerloren(Exception):
    """Neu schreiben lassen würde einen von Hand bearbeiteten Text verwerfen.

    Kein Fehler im engeren Sinn, sondern eine Rückfrage: Die Oberfläche fängt
    das ab und fragt nach, statt zwanzig Minuten Feilarbeit stillschweigend
    wegzuwerfen.
    """


class RueckfrageOffen(Exception):
    """Der Beitrag lässt sich nicht freigeben, es sind Fragen offen."""


@dataclass(frozen=True)
class Projekt:
    """Ein Projekt, wie es aus der Ablage kommt."""

    id: int
    kennung: str
    name: str
    adresse: str
    art: str
    farbe: str
    zustand: str
    freigabe_noetig: bool
    einstellungen: dict[str, Any]
    angelegt: str
    zuletzt_geholt: str | None

    @property
    def aktiv(self) -> bool:
        return self.zustand == PROJEKT_AKTIV


def standard_pfad() -> Path:
    """Wo die Ablage liegt, wenn nichts anderes gesagt wird."""
    return Path.home() / ".local" / "share" / "postkutsche" / "postkutsche.db"


class Ablage:
    """Zugang zur SQLite-Datei. Als Kontextverwalter benutzbar."""

    def __init__(self, pfad: Path | str | None = None) -> None:
        self.pfad = Path(pfad) if pfad is not None else standard_pfad()
        if str(self.pfad) != ":memory:":
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.pfad))
        self.db.row_factory = sqlite3.Row
        # Ohne das setzt SQLite Fremdschlüssel nicht durch – ON DELETE CASCADE
        # wäre reine Zierde. Muss je Verbindung gesetzt werden.
        self.db.execute("PRAGMA foreign_keys = ON")
        self._anlegen()

    def __enter__(self) -> "Ablage":
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()

    def schliessen(self) -> None:
        self.db.close()

    # -- Aufbau ------------------------------------------------------------

    def _anlegen(self) -> None:
        self.db.executescript(SCHEMA)
        stand = self.db.execute("SELECT fassung FROM schema_stand").fetchone()
        if stand is None:
            self.db.execute("INSERT INTO schema_stand (fassung) VALUES (?)", (SCHEMA_FASSUNG,))
        else:
            self._wandeln(int(stand["fassung"]))
        self.db.commit()

    def _wandeln(self, von: int) -> None:
        """Hebt eine bestehende Ablage auf die aktuelle Schemafassung.

        `CREATE TABLE IF NOT EXISTS` legt neue Tabellen an, aber es fügt einer
        vorhandenen Tabelle keine Spalte hinzu. Genau dafür ist das hier da.

        Jeder Schritt muss für sich stehen und darf nichts wegwerfen: Wer die
        Ablage seit Wochen benutzt, hat darin Beiträge, die er nicht noch
        einmal schreiben lassen will.
        """
        if von < 2:
            # Ein zweites Bild je Fassung. ADD COLUMN hängt nur eine leere
            # Spalte an - die vorhandenen Bilder bleiben, wo sie sind.
            if "bild_pfad2" not in self._spalten("fassungen"):
                self.db.execute("ALTER TABLE fassungen ADD COLUMN bild_pfad2 TEXT")

        if von != SCHEMA_FASSUNG:
            self.db.execute("UPDATE schema_stand SET fassung = ?",
                            (SCHEMA_FASSUNG,))

    def _spalten(self, tabelle: str) -> set[str]:
        return {str(z["name"])
                for z in self.db.execute(f"PRAGMA table_info({tabelle})")}

    # -- Projekte ----------------------------------------------------------

    def projekt_anlegen(
        self,
        kennung: str,
        name: str,
        adresse: str,
        art: str,
        farbe: str = "#6b7280",
        freigabe_noetig: bool = True,
        einstellungen: dict[str, Any] | None = None,
        zustand: str = PROJEKT_AKTIV,
    ) -> Projekt:
        """Legt ein Projekt an. Gibt es die Kennung schon, wird sie ergänzt."""
        jetzt = _jetzt()
        self.db.execute(
            """
            INSERT INTO projekte (kennung, name, adresse, art, farbe, zustand,
                                  freigabe_noetig, einstellungen, angelegt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (kennung) DO UPDATE SET
                name = excluded.name,
                adresse = excluded.adresse,
                art = excluded.art,
                farbe = excluded.farbe,
                freigabe_noetig = excluded.freigabe_noetig,
                einstellungen = excluded.einstellungen
            """,
            (
                kennung,
                name,
                adresse,
                art,
                farbe,
                zustand,
                int(freigabe_noetig),
                json.dumps(einstellungen or {}, ensure_ascii=False),
                jetzt,
            ),
        )
        self.db.commit()
        projekt = self.projekt(kennung)
        assert projekt is not None  # gerade eingefügt
        return projekt

    def projekt(self, kennung: str) -> Projekt | None:
        zeile = self.db.execute(
            "SELECT * FROM projekte WHERE kennung = ?", (kennung,)
        ).fetchone()
        return _zu_projekt(zeile) if zeile else None

    def projekte(self, nur_aktive: bool = False) -> list[Projekt]:
        frage = "SELECT * FROM projekte"
        werte: tuple[Any, ...] = ()
        if nur_aktive:
            frage += " WHERE zustand = ?"
            werte = (PROJEKT_AKTIV,)
        frage += " ORDER BY name COLLATE NOCASE"
        return [_zu_projekt(z) for z in self.db.execute(frage, werte)]

    def projekt_zustand(self, kennung: str, zustand: str) -> bool:
        """Aktiviert oder pausiert ein Projekt. Gibt zurück, ob es das gab.

        Pausiert heißt: nicht mehr abrufen, nichts Neues entwerfen, nichts
        senden. Bestehende Beiträge bleiben stehen und werden weiter angezeigt –
        pausieren ist kein Löschen.
        """
        if zustand not in (PROJEKT_AKTIV, PROJEKT_PAUSIERT):
            raise ValueError(f"Unbekannter Zustand: {zustand!r}")
        cursor = self.db.execute(
            "UPDATE projekte SET zustand = ? WHERE kennung = ?", (zustand, kennung)
        )
        self.db.commit()
        return cursor.rowcount > 0

    def projekt_loeschen(self, kennung: str) -> bool:
        """Entfernt ein Projekt samt Inhalten und Beiträgen.

        Meistens ist Pausieren gemeint, nicht Löschen – deshalb ruft die
        Oberfläche das nur nach Rückfrage auf.
        """
        cursor = self.db.execute("DELETE FROM projekte WHERE kennung = ?", (kennung,))
        self.db.commit()
        return cursor.rowcount > 0

    def geholt_vermerken(self, projekt_id: int) -> None:
        self.db.execute(
            "UPDATE projekte SET zuletzt_geholt = ? WHERE id = ?", (_jetzt(), projekt_id)
        )
        self.db.commit()

    # -- Inhalte -----------------------------------------------------------

    def inhalt_merken(
        self,
        projekt_id: int,
        fremd_id: str,
        titel: str,
        adresse: str,
        text: str = "",
        bild_adresse: str | None = None,
        veroeffentlicht: str | None = None,
    ) -> tuple[int, bool]:
        """Merkt einen gefundenen Inhalt.

        Gibt (id, neu) zurück. `neu` ist wahr, wenn dieser Inhalt vorher nicht
        da war – daran hängt, ob ein Beitrag vorgeschlagen wird. Bekannte
        Inhalte werden aufgefrischt, aber nicht erneut vorgeschlagen; sonst
        stünde jeder nachträglich korrigierte Blogbeitrag wieder im Kalender.
        """
        vorhanden = self.db.execute(
            "SELECT id FROM inhalte WHERE projekt_id = ? AND fremd_id = ?",
            (projekt_id, fremd_id),
        ).fetchone()
        if vorhanden:
            self.db.execute(
                """UPDATE inhalte SET titel = ?, text = ?, adresse = ?,
                       bild_adresse = ?, veroeffentlicht = ? WHERE id = ?""",
                (titel, text, adresse, bild_adresse, veroeffentlicht, vorhanden["id"]),
            )
            self.db.commit()
            return int(vorhanden["id"]), False

        cursor = self.db.execute(
            """INSERT INTO inhalte (projekt_id, fremd_id, titel, text, adresse,
                                    bild_adresse, veroeffentlicht, gefunden)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (projekt_id, fremd_id, titel, text, adresse, bild_adresse,
             veroeffentlicht, _jetzt()),
        )
        self.db.commit()
        return int(cursor.lastrowid or 0), True

    def inhalte(self, projekt_id: int, grenze: int = 50) -> list[sqlite3.Row]:
        return list(
            self.db.execute(
                """SELECT * FROM inhalte WHERE projekt_id = ?
                   ORDER BY COALESCE(veroeffentlicht, gefunden) DESC LIMIT ?""",
                (projekt_id, grenze),
            )
        )

    # -- Beiträge ----------------------------------------------------------

    def beitrag_anlegen(
        self,
        projekt_id: int,
        geplant: str,
        inhalt_id: int | None = None,
        zustand: str = BEITRAG_ENTWURF,
        notiz: str = "",
        wiederholung_von: int | None = None,
    ) -> int:
        jetzt = _jetzt()
        cursor = self.db.execute(
            """INSERT INTO beitraege (projekt_id, inhalt_id, geplant, zustand,
                                      notiz, wiederholung_von, angelegt, geaendert)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (projekt_id, inhalt_id, geplant, zustand, notiz, wiederholung_von,
             jetzt, jetzt),
        )
        self.db.commit()
        return int(cursor.lastrowid or 0)

    def beitrag(self, beitrag_id: int) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM beitraege WHERE id = ?", (beitrag_id,)
        ).fetchone()

    def beitrag_wiederholen(
        self,
        beitrag_id: int,
        geplant: str,
        texte_uebernehmen: bool = True,
    ) -> int:
        """Stellt einen bereits veröffentlichten Beitrag noch einmal ein.

        Der alte Beitrag bleibt unangetastet mit seinem Sendedatum stehen; es
        entsteht ein neuer im Zustand Entwurf. Das ist wichtiger, als es
        aussieht: Nur so bleibt lesbar, dass und wann derselbe Inhalt schon
        einmal lief – und das braucht man. Facebook und Instagram drosseln
        wortgleiche Wiederholungen, der Text muss beim zweiten Mal also
        abgewandelt werden, und dafür muss man den ersten noch sehen.

        `texte_uebernehmen=False` legt nur die Hülle an, wenn Claude von vorn
        schreiben soll.
        """
        alt = self.beitrag(beitrag_id)
        if alt is None:
            raise ValueError(f"Kein Beitrag mit der Nummer {beitrag_id}.")

        neu = self.beitrag_anlegen(
            projekt_id=int(alt["projekt_id"]),
            geplant=geplant,
            inhalt_id=alt["inhalt_id"],
            zustand=BEITRAG_ENTWURF,
            notiz=alt["notiz"],
            # Die Kette zeigt immer auf den Urahn, nicht auf den Vorgänger.
            # Sonst müsste man sich für »die wievielte Runde ist das?« durch
            # eine beliebig lange Kette hangeln.
            wiederholung_von=alt["wiederholung_von"] or int(alt["id"]),
        )
        if texte_uebernehmen:
            for fassung in self.fassungen(beitrag_id):
                nummer = self.fassung_setzen(
                    neu,
                    fassung["netzwerk"],
                    fassung["text"],
                    fassung["schlagworte"],
                    fassung["bild_pfad"],
                    fassung["versandart"],
                )
                # Das zweite Bild wandert mit. Es war eine Handauswahl; wer
                # denselben Beitrag wiederholt, will sie nicht neu treffen.
                if fassung["bild_pfad2"]:
                    self.db.execute(
                        "UPDATE fassungen SET bild_pfad2 = ? WHERE id = ?",
                        (fassung["bild_pfad2"], nummer))
            self.db.commit()
        return neu

    def wiederholungen(self, beitrag_id: int) -> list[sqlite3.Row]:
        """Alle Runden desselben Beitrags, älteste zuerst – auch die Vorlage."""
        alt = self.beitrag(beitrag_id)
        if alt is None:
            return []
        urahn = alt["wiederholung_von"] or int(alt["id"])
        return list(
            self.db.execute(
                """SELECT * FROM beitraege
                   WHERE id = ? OR wiederholung_von = ?
                   ORDER BY geplant""",
                (urahn, urahn),
            )
        )

    def veroeffentlichte(
        self, projekt_kennungen: Iterable[str] | None = None, grenze: int = 100
    ) -> list[sqlite3.Row]:
        """Was schon draußen war – die Vorratskammer für Wiederholungen.

        Zählt auch, was von Hand eingestellt wurde: Für die Frage »was lief
        schon?« ist der Weg nach draußen gleichgültig.
        """
        frage = """
            SELECT b.*, p.kennung AS projekt_kennung, p.name AS projekt_name,
                   p.farbe AS projekt_farbe,
                   i.titel AS inhalt_titel, i.adresse AS inhalt_adresse,
                   MAX(f.gesendet) AS zuletzt_gesendet,
                   COUNT(f.id) AS anzahl_fassungen
            FROM beitraege b
            JOIN projekte p ON p.id = b.projekt_id
            LEFT JOIN inhalte i ON i.id = b.inhalt_id
            JOIN fassungen f ON f.beitrag_id = b.id
            WHERE f.zustand IN (?, ?)
        """
        werte: list[Any] = [FASSUNG_GESENDET, FASSUNG_ABGEHOLT]
        kennungen = list(projekt_kennungen) if projekt_kennungen is not None else None
        if kennungen is not None:
            if not kennungen:
                return []
            frage += f" AND p.kennung IN ({','.join('?' * len(kennungen))})"
            werte.extend(kennungen)
        frage += " GROUP BY b.id ORDER BY zuletzt_gesendet DESC LIMIT ?"
        werte.append(grenze)
        return list(self.db.execute(frage, werte))

    def beitrag_verschieben(self, beitrag_id: int, geplant: str) -> bool:
        """Setzt den Termin neu – das Ziehen im Kalender landet hier."""
        cursor = self.db.execute(
            "UPDATE beitraege SET geplant = ?, geaendert = ? WHERE id = ?",
            (geplant, _jetzt(), beitrag_id),
        )
        self.db.commit()
        return cursor.rowcount > 0

    def beitrag_zustand(self, beitrag_id: int, zustand: str) -> bool:
        cursor = self.db.execute(
            "UPDATE beitraege SET zustand = ?, geaendert = ? WHERE id = ?",
            (zustand, _jetzt(), beitrag_id),
        )
        self.db.commit()
        return cursor.rowcount > 0

    def beitraege_im_zeitraum(
        self,
        von: str,
        bis: str,
        projekt_kennungen: Iterable[str] | None = None,
    ) -> list[sqlite3.Row]:
        """Alles, was der Kalender für einen Ausschnitt braucht – in einer Frage.

        `projekt_kennungen` filtert die Ansicht. Das ist das Häkchen links und
        hat nichts damit zu tun, ob ein Projekt aktiv oder pausiert ist:
        Ausblenden ist Ansichtssache, Pausieren ist Betrieb.
        """
        frage = """
            SELECT b.*, p.kennung AS projekt_kennung, p.name AS projekt_name,
                   p.farbe AS projekt_farbe, p.zustand AS projekt_zustand,
                   i.titel AS inhalt_titel, i.adresse AS inhalt_adresse
            FROM beitraege b
            JOIN projekte p ON p.id = b.projekt_id
            LEFT JOIN inhalte i ON i.id = b.inhalt_id
            WHERE b.geplant >= ? AND b.geplant < ?
        """
        werte: list[Any] = [von, bis]
        kennungen = list(projekt_kennungen) if projekt_kennungen is not None else None
        if kennungen is not None:
            if not kennungen:
                return []
            frage += f" AND p.kennung IN ({','.join('?' * len(kennungen))})"
            werte.extend(kennungen)
        frage += " ORDER BY b.geplant"
        return list(self.db.execute(frage, werte))

    def faellige_beitraege(self, bis: str) -> list[sqlite3.Row]:
        """Freigegebene Beiträge aktiver Projekte, deren Zeit gekommen ist.

        Pausierte Projekte kommen hier nicht vor – das ist der Sinn des
        Pausierens.
        """
        return list(
            self.db.execute(
                """SELECT b.*, p.kennung AS projekt_kennung
                   FROM beitraege b
                   JOIN projekte p ON p.id = b.projekt_id
                   WHERE b.zustand = ? AND p.zustand = ? AND b.geplant <= ?
                   ORDER BY b.geplant""",
                (BEITRAG_FREIGEGEBEN, PROJEKT_AKTIV, bis),
            )
        )

    # -- Fassungen ---------------------------------------------------------

    def fassung_setzen(
        self,
        beitrag_id: int,
        netzwerk: str,
        text: str,
        schlagworte: str = "",
        bild_pfad: str | None = None,
        versandart: str = VERSAND_SCHNITTSTELLE,
        rueckfrage: str | None = None,
        handarbeit_ueberschreiben: bool = False,
    ) -> int:
        """Schreibt die Fassung für ein Netzwerk – neu oder überschrieben.

        Das ist der Weg, auf dem Claude schreibt. Zustand und Sendevermerk
        werden dabei zurückgesetzt: Ein neu geschriebener Text ist nicht mehr
        derselbe, der gesendet wurde.

        **Ein von Hand bearbeiteter Text wird nicht überschrieben.** Wer
        »neu schreiben lassen« drückt, nachdem er zwanzig Minuten an einem
        Satz gefeilt hat, meint das selten. Deshalb muss das ausdrücklich
        erlaubt werden; die Oberfläche fragt vorher nach.

        `rueckfrage` ist, was Claude nicht entscheiden konnte. Steht dort
        etwas, lässt sich der Beitrag nicht freigeben.
        """
        vorhanden = self.db.execute(
            "SELECT id, von_hand FROM fassungen WHERE beitrag_id = ? AND netzwerk = ?",
            (beitrag_id, netzwerk),
        ).fetchone()

        if vorhanden and vorhanden["von_hand"] and not handarbeit_ueberschreiben:
            raise HandarbeitWuerdeVerloren(
                f"Die Fassung für {netzwerk} wurde von Hand bearbeitet. "
                "Neu schreiben lassen würde diese Arbeit verwerfen."
            )

        self.db.execute(
            """
            INSERT INTO fassungen (beitrag_id, netzwerk, text, schlagworte,
                                   bild_pfad, versandart, zustand, rueckfrage,
                                   von_hand)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT (beitrag_id, netzwerk) DO UPDATE SET
                text = excluded.text,
                schlagworte = excluded.schlagworte,
                bild_pfad = excluded.bild_pfad,
                -- Das zweite Bild bleibt stehen. Es kommt nicht aus der
                -- Quelle, sondern wurde von Hand gewählt; neu schreiben
                -- lassen betrifft den Text, nicht die Bildauswahl.
                versandart = excluded.versandart,
                zustand = ?,
                rueckfrage = excluded.rueckfrage,
                von_hand = 0,
                gesendet = NULL,
                fremd_adresse = NULL,
                fehler = NULL
            """,
            (beitrag_id, netzwerk, text, schlagworte, bild_pfad, versandart,
             FASSUNG_OFFEN, rueckfrage, FASSUNG_OFFEN),
        )
        self.db.commit()
        self._beitrag_nachfuehren(beitrag_id)

        zeile = self.db.execute(
            "SELECT id FROM fassungen WHERE beitrag_id = ? AND netzwerk = ?",
            (beitrag_id, netzwerk),
        ).fetchone()
        return int(zeile["id"])

    def fassung_bearbeiten(
        self,
        fassung_id: int,
        text: str,
        schlagworte: str | None = None,
        bild_pfad: str | None = None,
        bild_pfad2: str | None = None,
    ) -> None:
        """Übernimmt, was von Hand geändert wurde.

        Merkt sich, dass hier gearbeitet wurde – daran hängt der Schutz in
        `fassung_setzen`. Eine offene Rückfrage gilt damit als erledigt: Wer
        den Text selbst in die Hand nimmt, hat sie beantwortet.
        """
        felder = ["text = ?", "von_hand = 1", "rueckfrage = NULL", "zustand = ?"]
        werte: list[Any] = [text, FASSUNG_OFFEN]
        if schlagworte is not None:
            felder.append("schlagworte = ?")
            werte.append(schlagworte)
        if bild_pfad is not None:
            felder.append("bild_pfad = ?")
            werte.append(bild_pfad)
        if bild_pfad2 is not None:
            felder.append("bild_pfad2 = ?")
            werte.append(bild_pfad2)
        werte.append(fassung_id)

        self.db.execute(
            f"UPDATE fassungen SET {', '.join(felder)} WHERE id = ?", werte
        )
        self.db.commit()

        zeile = self.db.execute(
            "SELECT beitrag_id FROM fassungen WHERE id = ?", (fassung_id,)
        ).fetchone()
        if zeile:
            self._beitrag_nachfuehren(int(zeile["beitrag_id"]))

    def rueckfragen(self, beitrag_id: int) -> list[sqlite3.Row]:
        """Die offenen Rückfragen zu einem Beitrag."""
        return list(
            self.db.execute(
                """SELECT * FROM fassungen
                   WHERE beitrag_id = ? AND rueckfrage IS NOT NULL
                     AND rueckfrage != ''
                   ORDER BY netzwerk""",
                (beitrag_id,),
            )
        )

    def freigeben(self, beitrag_id: int) -> None:
        """Gibt einen Beitrag zum Senden frei.

        Offene Rückfragen sind ein Hindernis, keine Warnung. Der ganze Sinn
        einer Rückfrage ist, dass sie beantwortet wird, bevor der Text
        rausgeht – wer sie übergehen kann, übergeht sie.
        """
        offen = self.rueckfragen(beitrag_id)
        if offen:
            fragen = "; ".join(f"{z['netzwerk']}: {z['rueckfrage']}" for z in offen)
            raise RueckfrageOffen(
                f"Zu diesem Beitrag sind {len(offen)} Fragen offen. {fragen}"
            )
        if not self.fassungen(beitrag_id):
            raise RueckfrageOffen(
                "Der Beitrag hat noch keinen Text – es gibt nichts freizugeben."
            )
        self.beitrag_zustand(beitrag_id, BEITRAG_FREIGEGEBEN)

    def _beitrag_nachfuehren(self, beitrag_id: int) -> None:
        """Hält den Zustand des Beitrags mit seinen Fassungen im Einklang.

        Nur zwischen Entwurf und Rückfrage – ein freigegebener oder erledigter
        Beitrag wird nicht angefasst.
        """
        beitrag = self.beitrag(beitrag_id)
        if beitrag is None or beitrag["zustand"] not in (
            BEITRAG_ENTWURF, BEITRAG_RUECKFRAGE
        ):
            return
        soll = BEITRAG_RUECKFRAGE if self.rueckfragen(beitrag_id) else BEITRAG_ENTWURF
        if beitrag["zustand"] != soll:
            self.beitrag_zustand(beitrag_id, soll)

    def fassungen(self, beitrag_id: int) -> list[sqlite3.Row]:
        return list(
            self.db.execute(
                "SELECT * FROM fassungen WHERE beitrag_id = ? ORDER BY netzwerk",
                (beitrag_id,),
            )
        )

    def fassung_vermerken(
        self,
        fassung_id: int,
        zustand: str,
        fremd_adresse: str | None = None,
        fehler: str | None = None,
    ) -> None:
        """Hält fest, wie es einer Fassung ergangen ist.

        `FASSUNG_ABGEHOLT` ist der Handbetrieb: Text kopiert, Bild geladen, bei
        Facebook oder Instagram selbst eingestellt. Für den Kalender zählt das
        wie gesendet, nur der Weg war ein anderer.
        """
        self.db.execute(
            """UPDATE fassungen SET zustand = ?, gesendet = ?, fremd_adresse = ?,
                   fehler = ? WHERE id = ?""",
            (
                zustand,
                _jetzt() if zustand in (FASSUNG_GESENDET, FASSUNG_ABGEHOLT) else None,
                fremd_adresse,
                fehler,
                fassung_id,
            ),
        )
        self.db.commit()
        self._beitrag_nachziehen(fassung_id)

    def _beitrag_nachziehen(self, fassung_id: int) -> None:
        """Setzt den Beitrag auf »erledigt«, sobald alle Fassungen draußen sind.

        Ohne das bleibt ein Beitrag für immer auf »freigegeben« stehen, auch
        wenn längst jede Fassung erschienen ist - und der Kalender fordert
        einen auf, etwas einzustellen, das man schon eingestellt hat.

        Erst wenn **alle** Fassungen durch sind: Ein Beitrag, der nach
        Mastodon und Facebook geht, ist nicht erledigt, weil das eine raus
        ist. Das Kärtchen steht für beides.
        """
        zeile = self.db.execute(
            "SELECT beitrag_id FROM fassungen WHERE id = ?", (fassung_id,)
        ).fetchone()
        if zeile is None:
            return
        beitrag_id = int(zeile["beitrag_id"])

        alle = self.fassungen(beitrag_id)
        if alle and all(f["zustand"] in (FASSUNG_GESENDET, FASSUNG_ABGEHOLT)
                        for f in alle):
            self.beitrag_zustand(beitrag_id, BEITRAG_ERLEDIGT)

    def beitrag_entfernen(self, beitrag_id: int) -> str:
        """Löscht einen Beitrag, der noch nicht draußen war.

        **Veröffentlichtes bleibt.** Ein Beitrag, der erschienen ist, ist ein
        Beleg - er lässt sich hier nicht wegräumen, auch nicht versehentlich.
        Wer ihn drüben löscht, tut das drüben; der Kalender hält fest, was
        war.

        Der Inhalt geht mit, wenn kein anderer Beitrag mehr an ihm hängt.
        Sonst gälte das Produkt vier Wochen lang als beworben, obwohl der
        Beitrag gelöscht wurde - und käme in der nächsten Wochenplanung nicht
        mehr vor, ohne dass jemand wüsste, warum.
        """
        zeile = self.beitrag(beitrag_id)
        if zeile is None:
            raise KeyError(f"Beitrag {beitrag_id} gibt es nicht.")

        draussen = [f for f in self.fassungen(beitrag_id)
                    if f["zustand"] in (FASSUNG_GESENDET, FASSUNG_ABGEHOLT)]
        if draussen:
            netze = ", ".join(sorted({f["netzwerk"] for f in draussen}))
            raise HandarbeitWuerdeVerloren(
                f"Dieser Beitrag ist bei {netze} erschienen und bleibt als "
                "Beleg stehen. Löschen lässt sich nur, was nie draußen war."
            )

        inhalt_id = zeile["inhalt_id"]
        titel = zeile["notiz"] or ""
        self.db.execute("DELETE FROM beitraege WHERE id = ?", (beitrag_id,))
        if inhalt_id is not None:
            uebrig = self.db.execute(
                "SELECT COUNT(*) FROM beitraege WHERE inhalt_id = ?", (inhalt_id,)
            ).fetchone()[0]
            if not uebrig:
                self.db.execute("DELETE FROM inhalte WHERE id = ?", (inhalt_id,))
        self.db.commit()
        return titel

    def verfallene(self, karenz_tage: int = 2) -> list[sqlite3.Row]:
        """Entwürfe, deren Termin vorbei ist und die nie veröffentlicht wurden.

        Wer auf einen Vorschlag nicht reagiert, hat entschieden - nur eben
        durch Nichtstun. Solche Beiträge im Kalender stehen zu lassen hat zwei
        Nachteile: Er füllt sich mit Dingen, die nie passiert sind, und die
        Vier-Wochen-Regel sperrt Produkte, die nie beworben wurden.

        Die Karenz von zwei Tagen ist Absicht: Wer am Montag krank ist, soll
        seine Dienstagsbeiträge am Mittwoch noch vorfinden.
        """
        grenze = zeiten_modul().schreiben(
            zeiten_modul().lesen(zeiten_modul().jetzt_utc())
            - __import__("datetime").timedelta(days=karenz_tage)
        )
        return list(self.db.execute(
            """SELECT b.*, p.name AS projekt_name, i.titel AS inhalt_titel
               FROM beitraege b
               JOIN projekte p ON p.id = b.projekt_id
               LEFT JOIN inhalte i ON i.id = b.inhalt_id
               WHERE b.geplant < ?
                 AND b.id NOT IN (
                     SELECT beitrag_id FROM fassungen WHERE zustand IN (?, ?)
                 )
               ORDER BY b.geplant""",
            (grenze, FASSUNG_GESENDET, FASSUNG_ABGEHOLT),
        ))

    def aufraeumen(self, karenz_tage: int = 2) -> list[str]:
        """Entfernt verfallene Entwürfe. Gibt zurück, was weggeräumt wurde.

        **Veröffentlichtes wird nie angefasst.** Ein Beitrag, der draußen war,
        ist ein Beleg - er bleibt, auch wenn er zehn Jahre alt ist.

        Der zugehörige Inhalt wird mitgelöscht, wenn er an keinem anderen
        Beitrag mehr hängt: Sonst gilt das Produkt weiter als »kürzlich
        beworben«, obwohl der Beitrag nie erschienen ist.
        """
        weg = []
        for zeile in self.verfallene(karenz_tage):
            titel = zeile["inhalt_titel"] or zeile["notiz"] or f"#{zeile['id']}"
            weg.append(f"{zeile['projekt_name']}: {titel[:60]}")
            inhalt_id = zeile["inhalt_id"]
            self.db.execute("DELETE FROM beitraege WHERE id = ?", (zeile["id"],))
            if inhalt_id is not None:
                uebrig = self.db.execute(
                    "SELECT COUNT(*) FROM beitraege WHERE inhalt_id = ?",
                    (inhalt_id,),
                ).fetchone()[0]
                if not uebrig:
                    self.db.execute("DELETE FROM inhalte WHERE id = ?", (inhalt_id,))
        self.db.commit()
        return weg

    def zuletzt_beworben(self, projekt_id: int,
                         adressen: list[str]) -> dict[str, str]:
        """Wann diese Produkte zuletzt im Kalender standen.

        Gibt Adresse → Zeitpunkt des jüngsten Beitrags zurück; Produkte ohne
        Eintrag fehlen im Ergebnis. Zählt auch Entwürfe: Ein Produkt, das für
        nächste Woche schon geplant ist, soll nicht ein zweites Mal
        eingeplant werden, nur weil der Beitrag noch nicht raus ist.
        """
        if not adressen:
            return {}
        platzhalter = ",".join("?" * len(adressen))
        zeilen = self.db.execute(
            f"""SELECT i.adresse, MAX(b.geplant) AS wann
                FROM beitraege b
                JOIN inhalte i ON i.id = b.inhalt_id
                WHERE b.projekt_id = ? AND i.adresse IN ({platzhalter})
                  AND b.zustand != ?
                GROUP BY i.adresse""",
            (projekt_id, *adressen, BEITRAG_VERWORFEN),
        )
        return {str(z["adresse"]): str(z["wann"]) for z in zeilen}

    def frueherer_text(self, projekt_id: int, adresse: str) -> dict[str, str]:
        """Womit dieses Produkt zuletzt beworben wurde, je Netzwerk.

        Wird gebraucht, wenn dasselbe Produkt erneut drankommt: Der neue Text
        soll anders klingen, und dafür muss Claude den alten kennen.
        """
        zeilen = self.db.execute(
            """SELECT f.netzwerk, f.text
               FROM fassungen f
               JOIN beitraege b ON b.id = f.beitrag_id
               JOIN inhalte i ON i.id = b.inhalt_id
               WHERE b.projekt_id = ? AND i.adresse = ?
               ORDER BY b.geplant DESC""",
            (projekt_id, adresse),
        )
        gefunden: dict[str, str] = {}
        for zeile in zeilen:
            # Nur den jüngsten je Netzwerk - die Reihenfolge sorgt dafür.
            gefunden.setdefault(str(zeile["netzwerk"]), str(zeile["text"]))
        return gefunden

    def kategorien_zuletzt(self, projekt_id: int) -> dict[str, str]:
        """Wann eine Kategorie zuletzt bespielt wurde, je Kategoriepfad.

        Ohne eigene Tabelle: Die Adresse eines Produkts enthält den Pfad
        seiner Kategorie, und der Beitrag hat seinen Termin. Daraus lässt
        sich ablesen, was schon dran war - und das ist genau die Frage beim
        Planen der nächsten Woche.

        Gibt Pfad → Zeitstempel des jüngsten Beitrags zurück.
        """
        zuletzt: dict[str, str] = {}
        zeilen = self.db.execute(
            """SELECT i.adresse, MAX(b.geplant) AS wann
               FROM beitraege b
               JOIN inhalte i ON i.id = b.inhalt_id
               WHERE b.projekt_id = ? AND i.adresse IS NOT NULL
               GROUP BY i.adresse""",
            (projekt_id,),
        )
        for zeile in zeilen:
            ordner = str(zeile["adresse"]).rsplit("/", 1)[0]
            wann = str(zeile["wann"])
            # Auch den übergeordneten Pfaden zurechnen - wer »Brandschutztüren«
            # gewählt hat, hat damit auch die Unterkategorien bespielt.
            while "/" in ordner and ordner.count("/") > 2:
                if wann > zuletzt.get(ordner, ""):
                    zuletzt[ordner] = wann
                ordner = ordner.rsplit("/", 1)[0]
        return zuletzt

    # -- Wissen aus Rückfragen ---------------------------------------------

    #: Wie viele Einträge höchstens in eine Anweisung gehen. Vierzig
    #: Sonderfälle machen keinen besseren Text, sondern einen, in dem der
    #: eigentliche Auftrag untergeht - und jeder Eintrag kostet bei jedem
    #: Entwurf aufs Neue. Zwölf sind genug für die Regeln, die wirklich
    #: allgemein gelten.
    WISSENSGRENZE = 12

    def wissen_merken(self, projekt_id: int, frage: str, antwort: str,
                      adresse: str = "") -> int | None:
        """Merkt sich eine Antwort. Gibt None, wenn sie schon dastand.

        Doppeltes bleibt draußen: Wer zweimal dasselbe antwortet, soll es
        nicht zweimal in der Anweisung wiederfinden. Verglichen wird die
        Antwort, nicht die Frage - dieselbe Auskunft kann auf zwei
        verschieden formulierte Fragen kommen.

        Leerzeichen werden dabei vereinheitlicht, sonst gilt derselbe Satz
        mit einem Zeilenumbruch mehr als etwas Neues.
        """
        antwort = " ".join(antwort.split())
        if not antwort:
            raise ValueError("Ohne Antwort gibt es nichts zu merken.")

        zeiger = self.db.execute(
            """INSERT INTO wissen (projekt_id, adresse, frage, antwort, angelegt)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (projekt_id, adresse, antwort) DO NOTHING""",
            (projekt_id, adresse or "", " ".join(frage.split()), antwort, _jetzt()),
        )
        self.db.commit()
        # lastrowid zeigt bei DO NOTHING auf die vorige Zeile; rowcount ist
        # das verlässliche Zeichen dafür, ob wirklich eingefügt wurde.
        return int(zeiger.lastrowid) if zeiger.rowcount else None

    def wissen(self, projekt_id: int, adresse: str | None = None,
               grenze: int | None = None) -> list[sqlite3.Row]:
        """Was zu diesem Projekt bekannt ist – allgemein und zur Adresse.

        Ohne `adresse` kommt nur das Allgemeine. Mit Adresse kommt beides,
        denn beim Wiederholen desselben Produkts zählt auch, was damals
        eigens dazu gesagt wurde.

        Das Allgemeine steht vorn: Es gilt immer, das Produktwissen nur
        heute. Innerhalb beider das Neueste zuerst - wer eine frühere
        Auskunft berichtigt hat, will die Berichtigung gelesen sehen und
        nicht das, was sie ersetzt.
        """
        zeilen = self.db.execute(
            """SELECT * FROM wissen
               WHERE projekt_id = ? AND (adresse = '' OR adresse = ?)
               ORDER BY adresse ASC, angelegt DESC, id DESC""",
            (projekt_id, adresse or ""),
        ).fetchall()
        grenze = self.WISSENSGRENZE if grenze is None else grenze
        return zeilen[:grenze] if grenze >= 0 else zeilen

    def wissen_alles(self, projekt_id: int) -> list[sqlite3.Row]:
        """Alles Gesammelte eines Projekts, für die Ansicht zum Aufräumen.

        Ungedeckelt und ohne Adressfilter: Eine Sammlung, die nur wächst und
        die niemand durchsehen kann, steht nach einem halben Jahr voller
        Sätze, die nicht mehr stimmen.
        """
        return self.db.execute(
            """SELECT * FROM wissen WHERE projekt_id = ?
               ORDER BY adresse ASC, angelegt DESC, id DESC""",
            (projekt_id,),
        ).fetchall()

    def wissen_streichen(self, wissen_id: int) -> bool:
        zeiger = self.db.execute("DELETE FROM wissen WHERE id = ?", (wissen_id,))
        self.db.commit()
        return zeiger.rowcount > 0

    # -- Konten ------------------------------------------------------------

    def konto_anlegen(
        self,
        netzwerk: str,
        kennung: str,
        anzeigename: str = "",
        versandart: str = VERSAND_SCHNITTSTELLE,
        einstellungen: dict[str, Any] | None = None,
    ) -> int:
        self.db.execute(
            """
            INSERT INTO konten (netzwerk, kennung, anzeigename, versandart,
                                einstellungen, angelegt)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (kennung) DO UPDATE SET
                netzwerk = excluded.netzwerk,
                anzeigename = excluded.anzeigename,
                versandart = excluded.versandart,
                einstellungen = excluded.einstellungen
            """,
            (netzwerk, kennung, anzeigename, versandart,
             json.dumps(einstellungen or {}, ensure_ascii=False), _jetzt()),
        )
        self.db.commit()
        zeile = self.db.execute(
            "SELECT id FROM konten WHERE kennung = ?", (kennung,)
        ).fetchone()
        return int(zeile["id"])

    def konten(self) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM konten ORDER BY netzwerk, kennung"))

    def konto_zuordnen(self, projekt_id: int, konto_id: int) -> None:
        self.db.execute(
            """INSERT INTO projekt_konten (projekt_id, konto_id) VALUES (?, ?)
               ON CONFLICT DO NOTHING""",
            (projekt_id, konto_id),
        )
        self.db.commit()

    def konten_von(self, projekt_id: int) -> list[sqlite3.Row]:
        return list(
            self.db.execute(
                """SELECT k.* FROM konten k
                   JOIN projekt_konten pk ON pk.konto_id = k.id
                   WHERE pk.projekt_id = ? ORDER BY k.netzwerk""",
                (projekt_id,),
            )
        )


def _zu_projekt(zeile: sqlite3.Row) -> Projekt:
    return Projekt(
        id=int(zeile["id"]),
        kennung=zeile["kennung"],
        name=zeile["name"],
        adresse=zeile["adresse"],
        art=zeile["art"],
        farbe=zeile["farbe"],
        zustand=zeile["zustand"],
        freigabe_noetig=bool(zeile["freigabe_noetig"]),
        einstellungen=json.loads(zeile["einstellungen"] or "{}"),
        angelegt=zeile["angelegt"],
        zuletzt_geholt=zeile["zuletzt_geholt"],
    )


def zeiten_modul():
    """Spät geladen, weil `zeiten` seinerseits nichts aus der Ablage braucht."""
    from . import zeiten

    return zeiten


def _jetzt() -> str:
    return zeiten_modul().jetzt_utc()
