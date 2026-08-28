/* Der Kalender.
 *
 * Ohne Rahmenwerk: Es ist eine Seite mit einem Raster und einer Seitenleiste.
 * Was React hier lösen würde, löst hier ein Neuzeichnen des Monats - bei
 * dreißig Kärtchen merkt das niemand, und eine Abhängigkeit weniger ist eine
 * Abhängigkeit weniger.
 */

const stand = {
  jahr: null,
  monat: null,
  projekte: [],
  netzwerke: {},
  sichtbar: new Set(),   // Häkchen links - reine Ansichtssache
  offen: null,           // welcher Beitrag im Blatt steht
};

const $ = (auswahl) => document.querySelector(auswahl);

// -- Hilfen -----------------------------------------------------------------

async function hole(pfad, rumpf) {
  const antwort = await fetch(pfad, rumpf ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rumpf),
  } : undefined);
  const daten = await antwort.json();
  if (!antwort.ok) throw new Error(daten.fehler || `Fehler ${antwort.status}`);
  return daten;
}

let meldungsUhr;
function melden(text, schlecht = false) {
  const kasten = $("#meldung");
  kasten.textContent = text;
  kasten.classList.toggle("schlecht", schlecht);
  kasten.hidden = false;
  clearTimeout(meldungsUhr);
  // Fehler länger stehen lassen - man liest sie nicht im Vorbeigehen.
  meldungsUhr = setTimeout(() => (kasten.hidden = true), schlecht ? 8000 : 3000);
}

const ZEICHEN = { entwurf: "✎", rueckfrage: "?", freigegeben: "✓", erledigt: "↑" };

function zweistellig(n) { return String(n).padStart(2, "0"); }

/** Datum als YYYY-MM-DD in Ortszeit - ohne Umweg über UTC, sonst rutscht
 *  der Tag je nach Uhrzeit um eins. */
function tagesschluessel(d) {
  return `${d.getFullYear()}-${zweistellig(d.getMonth() + 1)}-${zweistellig(d.getDate())}`;
}

// -- Aufbau -----------------------------------------------------------------

async function anfangen() {
  const heute = new Date();
  stand.jahr = heute.getFullYear();
  stand.monat = heute.getMonth() + 1;

  const [projekte, netze] = await Promise.all([
    hole("/api/projekte"), hole("/api/netzwerke"),
  ]);
  stand.projekte = projekte;
  netze.forEach((n) => (stand.netzwerke[n.kennung] = n));
  projekte.forEach((p) => stand.sichtbar.add(p.kennung));

  spalteZeichnen();
  await monatLaden();

  $("#zurueck").onclick = () => blaettern(-1);
  $("#vor").onclick = () => blaettern(1);
  $("#heute").onclick = () => {
    const h = new Date();
    stand.jahr = h.getFullYear();
    stand.monat = h.getMonth() + 1;
    monatLaden();
  };
  $("#blatt-zu").onclick = blattSchliessen;
  $("#thema").onclick = themaWechseln;

  const gemerkt = localStorage.getItem("thema");
  if (gemerkt) document.documentElement.dataset.thema = gemerkt;
}

function themaWechseln() {
  const wurzel = document.documentElement;
  const neu = wurzel.dataset.thema === "dunkel" ? "hell" : "dunkel";
  wurzel.dataset.thema = neu;
  localStorage.setItem("thema", neu);
}

function blaettern(schritt) {
  stand.monat += schritt;
  if (stand.monat < 1) { stand.monat = 12; stand.jahr--; }
  if (stand.monat > 12) { stand.monat = 1; stand.jahr++; }
  monatLaden();
}

// -- Projektspalte ----------------------------------------------------------

function spalteZeichnen() {
  const liste = $("#projekte");
  liste.innerHTML = "";

  stand.projekte.forEach((p) => {
    const zeile = document.createElement("li");
    if (!p.aktiv) zeile.className = "pausiert";

    const feld = document.createElement("input");
    feld.type = "checkbox";
    feld.checked = stand.sichtbar.has(p.kennung);
    // Das Häkchen räumt nur die Ansicht auf. Ob ein Projekt läuft oder
    // pausiert ist, ist etwas anderes und steht am Pausenzeichen.
    feld.onchange = () => {
      feld.checked ? stand.sichtbar.add(p.kennung) : stand.sichtbar.delete(p.kennung);
      monatLaden();
    };

    const punkt = document.createElement("span");
    punkt.className = "punkt";
    punkt.style.background = p.farbe;

    const name = document.createElement("span");
    name.className = "name";
    name.textContent = p.name;

    const beschriftung = document.createElement("label");
    beschriftung.append(feld, punkt, name);
    zeile.append(beschriftung);

    if (!p.aktiv) {
      const pause = document.createElement("span");
      pause.textContent = "⏸";
      pause.title = "pausiert – wird nicht abgerufen und nicht gesendet";
      zeile.append(pause);
    }
    liste.append(zeile);
  });

  const marken = $("#netzwerke");
  marken.innerHTML = "";
  Object.values(stand.netzwerke).forEach((n) => {
    const punkt = document.createElement("li");
    punkt.textContent = n.kuerzel;
    punkt.style.borderColor = n.farbe;
    punkt.title = n.name;
    marken.append(punkt);
  });
}

// -- Monatsraster -----------------------------------------------------------

async function monatLaden() {
  const frage = new URLSearchParams({ jahr: stand.jahr, monat: stand.monat });
  stand.projekte.forEach((p) => {
    if (stand.sichtbar.has(p.kennung)) frage.append("projekt", p.kennung);
  });

  let daten;
  try {
    daten = await hole(`/api/beitraege?${frage}`);
  } catch (fehler) {
    melden(fehler.message, true);
    return;
  }

  const monatsname = new Date(stand.jahr, stand.monat - 1, 1)
    .toLocaleDateString("de-DE", { month: "long", year: "numeric" });
  $("#monatstitel").textContent = monatsname;

  rasterZeichnen(daten.beitraege);
}

function rasterZeichnen(beitraege) {
  const raster = $("#raster");
  raster.innerHTML = "";

  const nachTag = new Map();
  beitraege.forEach((b) => {
    const schluessel = b.geplant_ort.slice(0, 10);
    if (!nachTag.has(schluessel)) nachTag.set(schluessel, []);
    nachTag.get(schluessel).push(b);
  });

  // Das Raster beginnt am Montag der Woche, in der der Erste liegt.
  const erster = new Date(stand.jahr, stand.monat - 1, 1);
  const anfang = new Date(erster);
  anfang.setDate(erster.getDate() - ((erster.getDay() + 6) % 7));

  const heute = tagesschluessel(new Date());

  for (let i = 0; i < 42; i++) {
    const tag = new Date(anfang);
    tag.setDate(anfang.getDate() + i);
    const schluessel = tagesschluessel(tag);
    const eigen = tag.getMonth() === stand.monat - 1;

    // Die sechste Woche nur zeichnen, wenn der Monat sie braucht.
    if (i >= 35 && !eigen) break;

    const kasten = document.createElement("div");
    kasten.className = "tag" + (eigen ? "" : " fremd") + (schluessel === heute ? " heute" : "");
    kasten.dataset.tag = schluessel;

    const zahl = document.createElement("span");
    zahl.className = "zahl";
    zahl.textContent = tag.getDate();
    kasten.append(zahl);

    (nachTag.get(schluessel) || [])
      .sort((a, b) => a.geplant.localeCompare(b.geplant))
      .forEach((b) => kasten.append(kaertchen(b)));

    ablegenErlauben(kasten);
    raster.append(kasten);
  }
}

function kaertchen(b) {
  const kasten = document.createElement("button");
  kasten.className = "kaertchen";
  kasten.draggable = true;
  kasten.dataset.id = b.id;

  // Ein Segment je Netzwerk. Ein Beitrag in drei Netzen bleibt ein Kärtchen.
  const streifen = document.createElement("div");
  streifen.className = "streifen";
  (b.netzwerke.length ? b.netzwerke : ["_"]).forEach((n) => {
    const teil = document.createElement("span");
    teil.style.background = stand.netzwerke[n]?.farbe || "var(--linie)";
    streifen.append(teil);
  });

  const kopf = document.createElement("div");
  kopf.className = "kopfzeile";
  const punkt = document.createElement("span");
  punkt.className = "punkt";
  punkt.style.background = b.farbe;
  const zeit = document.createElement("span");
  zeit.className = "zeit";
  zeit.textContent = `${b.geplant_ort.slice(11, 16)} · ${b.projekt_name}`;
  kopf.append(punkt, zeit);

  const titel = document.createElement("div");
  titel.className = "titel";
  titel.textContent = b.titel;

  const fuss = document.createElement("div");
  fuss.className = "fuss";
  b.netzwerke.forEach((n) => {
    const kuerzel = document.createElement("span");
    kuerzel.className = "kuerzel";
    kuerzel.textContent = stand.netzwerke[n]?.kuerzel || n.slice(0, 2).toUpperCase();
    kuerzel.style.borderColor = stand.netzwerke[n]?.farbe || "var(--linie)";
    fuss.append(kuerzel);
  });

  const zustand = document.createElement("span");
  if (b.rueckfragen > 0) {
    zustand.className = "zustand warnung";
    zustand.textContent = ZEICHEN.rueckfrage;
    zustand.title = `${b.rueckfragen} Rückfrage(n) offen – nicht freigebbar`;
  } else if (b.ohne_bild.length) {
    zustand.className = "zustand warnung";
    zustand.textContent = "⚠";
    zustand.title = `Kein Bild für: ${b.ohne_bild.join(", ")}`;
  } else if (b.zustand === "freigegeben") {
    zustand.className = "zustand gut";
    zustand.textContent = ZEICHEN.freigegeben;
    zustand.title = "freigegeben";
  } else {
    zustand.className = "zustand";
    zustand.textContent = ZEICHEN[b.zustand] || ZEICHEN.entwurf;
    zustand.title = b.zustand;
  }
  fuss.append(zustand);

  kasten.append(streifen, kopf, titel, fuss);
  kasten.onclick = () => blattOeffnen(b.id);
  kasten.ondragstart = (e) => {
    e.dataTransfer.setData("text/plain", String(b.id));
    kasten.classList.add("zieht");
  };
  kasten.ondragend = () => kasten.classList.remove("zieht");
  return kasten;
}

function ablegenErlauben(kasten) {
  kasten.ondragover = (e) => { e.preventDefault(); kasten.classList.add("ziel"); };
  kasten.ondragleave = () => kasten.classList.remove("ziel");
  kasten.ondrop = async (e) => {
    e.preventDefault();
    kasten.classList.remove("ziel");
    const id = Number(e.dataTransfer.getData("text/plain"));
    if (!id) return;

    // Die Uhrzeit bleibt, nur der Tag ändert sich - wer ein Kärtchen
    // verschiebt, will es an einem anderen Tag, nicht zu anderer Stunde.
    const alt = document.querySelector(`.kaertchen[data-id="${id}"] .zeit`);
    const uhrzeit = alt ? alt.textContent.slice(0, 5) : "12:00";
    try {
      const e2 = await hole("/api/verschieben", {
        id, geplant: `${kasten.dataset.tag} ${uhrzeit}`,
      });
      melden(`Verschoben auf ${e2.lesbar}`);
      monatLaden();
    } catch (fehler) {
      melden(fehler.message, true);
    }
  };
}

// -- Blatt ------------------------------------------------------------------

function blattSchliessen() {
  $("#blatt").hidden = true;
  stand.offen = null;
}

async function blattOeffnen(id) {
  let b;
  try {
    b = await hole(`/api/beitrag/${id}`);
  } catch (fehler) {
    return melden(fehler.message, true);
  }
  stand.offen = id;

  const kaertchenDaten = document.querySelector(`.kaertchen[data-id="${id}"] .titel`);
  $("#blatt-titel").textContent = kaertchenDaten ? kaertchenDaten.textContent : `Beitrag ${id}`;

  const inhalt = $("#blatt-inhalt");
  inhalt.innerHTML = "";

  const wann = document.createElement("p");
  wann.className = "schlagworte";
  wann.textContent = `Geplant: ${b.geplant_ort.slice(0, 16).replace("T", ", ")} · ${b.zustand}`;
  inhalt.append(wann);

  b.fassungen.forEach((f) => inhalt.append(fassungsblock(id, f)));

  const knoepfe = document.createElement("div");
  knoepfe.className = "knoepfe";
  const frei = document.createElement("button");
  frei.className = "knopf";
  frei.textContent = "Freigeben";
  frei.onclick = async () => {
    try {
      await hole("/api/freigeben", { id });
      melden("Freigegeben.");
      monatLaden();
      blattOeffnen(id);
    } catch (fehler) {
      melden(fehler.message, true);
    }
  };
  knoepfe.append(frei);
  inhalt.append(knoepfe);

  $("#blatt").hidden = false;
}

function fassungsblock(beitragId, f) {
  const netz = stand.netzwerke[f.netzwerk] || {};
  const block = document.createElement("div");
  block.className = "fassung";

  const kopf = document.createElement("h3");
  const marke = document.createElement("span");
  marke.className = "kuerzel";
  marke.textContent = netz.kuerzel || f.netzwerk;
  marke.style.borderColor = netz.farbe || "var(--linie)";
  kopf.append(marke, document.createTextNode(netz.name || f.netzwerk));
  if (f.von_hand) {
    const merk = document.createElement("span");
    merk.className = "schlagworte";
    merk.textContent = "· von Hand bearbeitet";
    kopf.append(merk);
  }
  block.append(kopf);

  if (f.rueckfrage) {
    const frage = document.createElement("p");
    frage.className = "frage";
    frage.textContent = `Rückfrage: ${f.rueckfrage}`;
    block.append(frage);
  }

  if (f.bild) {
    // Das Bild gehört sichtbar dazu: Man gibt keinen Beitrag frei, dessen
    // Bild man nicht gesehen hat.
    const bild = document.createElement("img");
    bild.src = f.bild;
    bild.alt = "";
    bild.className = "vorschau";
    bild.loading = "lazy";
    block.append(bild);
  } else if (netz.bild_pflicht) {
    const fehlt = document.createElement("p");
    fehlt.className = "frage";
    fehlt.textContent = "Kein Bild – ohne Bild nimmt dieses Netzwerk nichts an.";
    block.append(fehlt);
  }

  const feld = document.createElement("textarea");
  feld.value = f.text;
  block.append(feld);

  const zaehler = document.createElement("div");
  zaehler.className = "zaehler";
  const zaehlen = () => {
    const n = feld.value.length;
    zaehler.textContent = `${n} von ${netz.zeichen_max} Zeichen`;
    zaehler.classList.toggle("zuviel", n > (netz.zeichen_max || 1e9));
  };
  feld.oninput = zaehlen;
  zaehlen();
  block.append(zaehler);

  if (f.schlagworte) {
    const worte = document.createElement("p");
    worte.className = "schlagworte";
    worte.textContent = f.schlagworte.split(" ").map((w) => `#${w}`).join(" ");
    block.append(worte);
  }

  const knoepfe = document.createElement("div");
  knoepfe.className = "knoepfe";

  const sichern = document.createElement("button");
  sichern.className = "knopf leise";
  sichern.textContent = "Übernehmen";
  sichern.onclick = async () => {
    try {
      await hole("/api/bearbeiten", { fassung: f.id, text: feld.value });
      melden("Übernommen.");
      blattOeffnen(beitragId);
      monatLaden();
    } catch (fehler) {
      melden(fehler.message, true);
    }
  };

  // Der Handbetrieb: Text kopieren, bei Facebook oder Instagram einstellen,
  // danach abhaken. Kein Markdown, keine Auszeichnung - genau der Text, der
  // dort hineingehört.
  const kopieren = document.createElement("button");
  kopieren.className = "knopf leise";
  kopieren.textContent = "Text kopieren";
  kopieren.onclick = async () => {
    const voll = f.schlagworte
      ? `${feld.value}\n\n${f.schlagworte.split(" ").map((w) => `#${w}`).join(" ")}`
      : feld.value;
    try {
      await navigator.clipboard.writeText(voll);
      melden("In die Zwischenablage kopiert.");
    } catch {
      // Ohne sicheren Kontext verweigert der Browser die Zwischenablage.
      feld.select();
      melden("Bitte mit Strg+C kopieren – der Text ist markiert.", true);
    }
  };

  knoepfe.append(sichern, kopieren);

  if (f.bild) {
    // Für den Handbetrieb: Bild auf die Platte holen, dann bei Facebook oder
    // Instagram hochladen.
    const holen = document.createElement("a");
    holen.className = "knopf leise";
    holen.href = f.bild;
    holen.download = `postkutsche-${f.netzwerk}-${f.id}.jpg`;
    holen.textContent = "Bild speichern";
    knoepfe.append(holen);
  }

  if (f.zustand !== "gesendet" && f.zustand !== "abgeholt") {
    const abhaken = document.createElement("button");
    abhaken.className = "knopf leise";
    abhaken.textContent = "Von Hand veröffentlicht";
    abhaken.onclick = async () => {
      try {
        await hole("/api/abgehakt", { fassung: f.id });
        melden("Als veröffentlicht vermerkt.");
        blattOeffnen(beitragId);
        monatLaden();
      } catch (fehler) {
        melden(fehler.message, true);
      }
    };
    knoepfe.append(abhaken);
  } else {
    const fertig = document.createElement("span");
    fertig.className = "schlagworte";
    fertig.textContent = f.zustand === "abgeholt" ? "✋ von Hand veröffentlicht" : "↑ gesendet";
    knoepfe.append(fertig);
  }

  block.append(knoepfe);
  return block;
}

anfangen().catch((fehler) => melden(`Start fehlgeschlagen: ${fehler.message}`, true));
