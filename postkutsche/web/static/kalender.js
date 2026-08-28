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

const EMOJIS = ["👉", "✅", "⚠️", "💡", "🔧", "🏠", "🚪", "📍", "📅", "🕐",
  "📷", "🌿", "☀️", "❄️", "🔥", "👀", "✨", "❤️", "🙌", "📢"];

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

  kampagneVorbereiten();
}

// -- Wochenplanung ----------------------------------------------------------

/** Die Kalenderwoche eines Datums nach ISO 8601.
 *
 * Nicht selbst zählen: Die erste Woche ist die mit dem ersten Donnerstag,
 * weshalb der 1. Januar mitunter in KW 52 des Vorjahres liegt. */
function kalenderwoche(d) {
  const hilfe = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  hilfe.setUTCDate(hilfe.getUTCDate() + 4 - (hilfe.getUTCDay() || 7));
  const jahresanfang = new Date(Date.UTC(hilfe.getUTCFullYear(), 0, 1));
  return {
    woche: Math.ceil(((hilfe - jahresanfang) / 86400000 + 1) / 7),
    jahr: hilfe.getUTCFullYear(),
  };
}

let kategorienAlle = [];

function kampagneVorbereiten() {
  const kasten = $("#kampagne");
  $("#kampagne-auf").onclick = () => {
    // Vorschlag: die kommende Woche. Für diese Woche zu planen geht auch,
    // dann liegen die ersten Termine aber schon in der Vergangenheit.
    const naechste = new Date();
    naechste.setDate(naechste.getDate() + 7);
    const kw = kalenderwoche(naechste);
    $("#k-woche").value = kw.woche;
    $("#k-jahr").value = kw.jahr;
    kasten.hidden = false;
  };
  $("#k-zu").onclick = () => (kasten.hidden = true);
  kasten.onclick = (e) => { if (e.target === kasten) kasten.hidden = true; };

  const auswahl = $("#k-projekt");
  auswahl.innerHTML = "";
  stand.projekte.forEach((p) => {
    const eintrag = document.createElement("option");
    eintrag.value = p.kennung;
    eintrag.textContent = p.name;
    if (p.art !== "seitenkarte") eintrag.disabled = true;
    auswahl.append(eintrag);
  });
  auswahl.onchange = kategorienLaden;

  const netze = $("#k-netze");
  netze.innerHTML = "";
  Object.values(stand.netzwerke).forEach((n) => {
    const feld = document.createElement("input");
    feld.type = "checkbox";
    feld.value = n.kennung;
    feld.checked = n.kennung === "facebook";
    const beschriftung = document.createElement("label");
    beschriftung.style.borderColor = n.farbe;
    beschriftung.append(feld, document.createTextNode(n.name));
    netze.append(beschriftung);
  });

  $("#k-suche").oninput = kategorienZeichnen;
  $("#k-bereich").onchange = kategorienZeichnen;
  $("#kampagne-form").onsubmit = kampagneAbschicken;
  kategorienLaden();
}

async function kategorienLaden() {
  const liste = $("#k-kategorien");
  liste.innerHTML = '<p class="schlagworte">Kategorien werden geholt …</p>';
  try {
    kategorienAlle = await hole(`/api/kategorien?projekt=${$("#k-projekt").value}`);
  } catch (fehler) {
    kategorienAlle = [];
    liste.innerHTML = `<p class="schlagworte">${fehler.message}</p>`;
    return;
  }
  bereicheFuellen();
  kategorienZeichnen();
}

/** Die obersten Zweige des Shops zur Auswahl – Türen, Garagentore, Zubehör.
 *
 * Ein Shop mit 158 Kategorien in einer Liste ist unbenutzbar; wer bei den
 * Türen anfangen will, soll nicht an Werkzeugen vorbeiscrollen.
 */
function bereicheFuellen() {
  const auswahl = $("#k-bereich");
  const bereiche = new Map();
  kategorienAlle.forEach((k) => {
    const erster = String(k.pfad).split("/")[0];
    bereiche.set(erster, (bereiche.get(erster) || 0) + (k.produkte > 0 ? 1 : 0));
  });

  auswahl.innerHTML = '<option value="">alle Bereiche</option>';
  [...bereiche.entries()].sort().forEach(([pfad, anzahl]) => {
    if (!anzahl) return;
    const eintrag = document.createElement("option");
    eintrag.value = pfad;
    // »shop-tueren« zu »Türen«: Das Wort »shop« steht in jedem Zweig und
    // trägt nichts bei.
    eintrag.textContent =
      `${pfad.replace(/^shop-/, "").replace(/^./, (c) => c.toUpperCase())
             .replace("tueren", "Türen").replace("zubehoer", "Zubehör")} (${anzahl})`;
    auswahl.append(eintrag);
  });
}

function kategorienZeichnen() {
  const liste = $("#k-kategorien");
  const suche = $("#k-suche").value.trim().toLowerCase();
  const gewaehlt = new Set(
    [...liste.querySelectorAll("input:checked")].map((f) => f.value)
  );
  liste.innerHTML = "";

  // Kategorien ohne Produkte sind Übersichtsseiten - sie anzubieten führt
  // nur zu leeren Kampagnen.
  const bereich = $("#k-bereich").value;
  const treffer = kategorienAlle.filter(
    (k) => k.produkte > 0
      && (!bereich || String(k.pfad).startsWith(bereich))
      && (!suche || k.name.toLowerCase().includes(suche))
  );
  if (!treffer.length) {
    liste.innerHTML = '<p class="schlagworte">Nichts gefunden.</p>';
    return;
  }

  treffer.forEach((k) => {
    const feld = document.createElement("input");
    feld.type = "checkbox";
    feld.value = k.adresse;
    feld.checked = gewaehlt.has(k.adresse);

    const beschriftung = document.createElement("label");
    // Die Gliederung des Shops beibehalten: Einrückung nach Tiefe.
    beschriftung.style.paddingLeft = `${(k.tiefe - 1) * 14}px`;
    const anzahl = document.createElement("span");
    anzahl.className = "anzahl";
    // Was schon dran war, steht dahinter - damit man beim Planen der
    // nächsten Woche nicht dieselbe Kategorie zweimal erwischt.
    anzahl.textContent = k.zuletzt ? `${k.produkte} · ${k.zuletzt}` : `${k.produkte}`;
    if (k.zuletzt) {
      anzahl.classList.add("gelaufen");
      anzahl.title = `Zuletzt bespielt: ${k.zuletzt}`;
    }
    beschriftung.append(feld, document.createTextNode(k.name), anzahl);
    liste.append(beschriftung);
  });
}

/** Zeigt an, was aus dem Lauf geworden ist – und bleibt stehen. */
function berichtZeigen(bericht) {
  const kasten = $("#k-bericht");
  kasten.innerHTML = "";
  kasten.hidden = false;

  const kopf = document.createElement("h3");
  kopf.textContent = bericht.anzahl === 1
    ? "1 Entwurf angelegt"
    : `${bericht.anzahl} Entwürfe angelegt`;
  kasten.append(kopf);

  bericht.angelegt.forEach((e) => {
    const zeile = document.createElement("div");
    zeile.className = "berichtzeile";
    const zeichen = e.rueckfragen ? "?" : (e.bild ? "✓" : "⚠");
    const titel = e.titel.length > 52 ? e.titel.slice(0, 52) + "…" : e.titel;
    zeile.textContent = `${zeichen}  ${e.lesbar}  ${titel}`;
    if (e.rueckfragen) zeile.title = "Rückfrage offen – nicht freigebbar";
    else if (!e.bild) zeile.title = "ohne Bild";
    kasten.append(zeile);
  });

  if (bericht.gescheitert.length) {
    const kopf2 = document.createElement("h3");
    kopf2.textContent = `${bericht.gescheitert.length} gescheitert`;
    kasten.append(kopf2);
    bericht.gescheitert.forEach((g) => {
      const zeile = document.createElement("div");
      zeile.className = "berichtzeile schlecht";
      zeile.textContent = `✗  ${g.titel.slice(0, 40)} – ${g.grund.slice(0, 60)}`;
      kasten.append(zeile);
    });
  }

  if (bericht.nicht_zugeordnet.length) {
    const hinweis = document.createElement("p");
    hinweis.className = "schlagworte";
    hinweis.textContent =
      `${bericht.nicht_zugeordnet.length} Produkte ließen sich keinem ` +
      "Hersteller zuordnen und wurden übergangen.";
    kasten.append(hinweis);
  }
  if (bericht.hinweis) {
    const hinweis = document.createElement("p");
    hinweis.className = "frage";
    hinweis.textContent = bericht.hinweis;
    kasten.append(hinweis);
  }

  const fertig = document.createElement("button");
  fertig.type = "button";
  fertig.className = "knopf";
  fertig.textContent = "Zum Kalender";
  fertig.onclick = () => {
    $("#kampagne").hidden = true;
    kasten.hidden = true;
  };
  kasten.append(fertig);
}

/** Eine Benachrichtigung des Systems, falls erlaubt.
 *
 * Wer den Lauf startet und dann in ein anderes Fenster wechselt, merkt sonst
 * nicht, dass er durch ist. Ohne Erlaubnis passiert schlicht nichts - danach
 * gefragt wird erst, wenn ein Lauf beginnt, nicht beim Öffnen der Seite.
 */
function benachrichtigen(bericht) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const text = bericht.gescheitert.length
    ? `${bericht.anzahl} angelegt, ${bericht.gescheitert.length} gescheitert`
    : `${bericht.anzahl} Entwürfe stehen im Kalender`;
  new Notification("POSTKutsche – Wochenplanung fertig", {
    body: text,
    icon: "/static/icon-64.png",
  });
}

async function kampagneAbschicken(e) {
  e.preventDefault();
  const kategorien = [...$("#k-kategorien").querySelectorAll("input:checked")]
    .map((f) => f.value);
  if (!kategorien.length) {
    return melden("Wähle mindestens eine Kategorie.", true);
  }
  const netze = [...$("#k-netze").querySelectorAll("input:checked")].map((f) => f.value);
  if (!netze.length) return melden("Wähle mindestens ein Netzwerk.", true);

  // Erlaubnis erst hier erfragen, nicht beim Laden der Seite: Wer den Lauf
  // startet, wird die Benachrichtigung gleich brauchen.
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }

  const knopf = $("#k-los");
  knopf.disabled = true;
  $("#k-bericht").hidden = true;
  const jeTag = Number($("#k-jetag").value);
  // Ehrlich sagen, wie lange es dauert: Je Beitrag ein Claude-Aufruf, und
  // der braucht seine halbe Minute. Ohne Hinweis hält man es für abgestürzt.
  $("#k-stand").textContent = "Produkte werden gesammelt …";
  $("#k-balken").hidden = false;
  $("#k-fuellung").style.width = "0%";

  // Alle zwei Sekunden nachfragen, wie weit es ist. Ein Ereignisstrom wäre
  // eleganter, aber für einen Lauf von wenigen Minuten ist Nachfragen
  // einfacher und geht auch dann, wenn die Verbindung kurz abreißt.
  const uhr = setInterval(async () => {
    try {
      const s = await hole("/api/lauf");
      if (!s.aktiv) return;
      const anteil = s.gesamt ? Math.round((s.getan / s.gesamt) * 100) : 0;
      $("#k-fuellung").style.width = `${anteil}%`;
      $("#k-stand").textContent = `${s.getan} von ${s.gesamt}: ${s.text}`;
    } catch { /* Zwischendurch mal keine Antwort ist kein Grund aufzuhören. */ }
  }, 2000);

  try {
    const bericht = await hole("/api/kampagne", {
      projekt: $("#k-projekt").value,
      thema: $("#k-thema").value,
      kalenderwoche: Number($("#k-woche").value),
      jahr: Number($("#k-jahr").value),
      kategorien,
      netzwerke: netze,
      je_tag: jeTag,
      hersteller: $("#k-hersteller").value.split(",").map((h) => h.trim()).filter(Boolean),
    });
    // Das Formular bleibt offen und zeigt, was entstanden ist. Ein Lauf
    // dauert Minuten - wer in der Zeit etwas anderes macht, soll das
    // Ergebnis noch vorfinden und nicht nur eine Meldung verpasst haben.
    berichtZeigen(bericht);
    benachrichtigen(bericht);
    monatLaden();
  } catch (fehler) {
    melden(fehler.message, true);
  } finally {
    clearInterval(uhr);
    knopf.disabled = false;
    $("#k-balken").hidden = true;
    $("#k-stand").textContent = "";
  }
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

  if (b.quelle) {
    // Der Verweis gehört sichtbar ins Blatt: Beim Einstellen von Hand braucht
    // man ihn zum Anklicken und zum Kopieren.
    const zeile = document.createElement("p");
    zeile.className = "quelle";
    const verweis = document.createElement("a");
    verweis.href = b.quelle;
    verweis.target = "_blank";
    verweis.rel = "noopener";
    verweis.textContent = b.quelle;
    const holen = document.createElement("button");
    holen.className = "klein";
    holen.textContent = "kopieren";
    holen.onclick = () => kopieren(b.quelle, "Verweis kopiert.");
    zeile.append(verweis, holen);
    inhalt.append(zeile);
  }

  b.fassungen.forEach((f) => inhalt.append(fassungsblock(id, f, b.quelle)));

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

async function kopieren(text, meldungstext) {
  try {
    await navigator.clipboard.writeText(text);
    melden(meldungstext);
  } catch {
    // Ohne sicheren Kontext verweigert der Browser die Zwischenablage.
    const hilfsfeld = document.createElement("textarea");
    hilfsfeld.value = text;
    document.body.append(hilfsfeld);
    hilfsfeld.select();
    melden("Bitte mit Strg+C kopieren – der Text ist markiert.", true);
    setTimeout(() => hilfsfeld.remove(), 15000);
  }
}

/** Der fertige Beitrag, so wie er ins jeweilige Netzwerk gehört.
 *
 * Die Unterschiede sind nicht Geschmackssache: Bei Instagram ist ein Verweis
 * im Text nicht anklickbar, dort steht er nur als Hinweis. Bei Facebook und
 * LinkedIn gehört er ans Ende. Bei Mastodon darf danach nichts mehr kommen.
 */
function fertigerText(f, quelle) {
  const text = f.feld ? f.feld.value : f.text;
  const teile = [text];
  const netz = f.netzwerk;

  // Steht die Adresse schon im Text, wird sie nicht noch einmal angehängt.
  // Claude soll sie nicht mitschreiben, aber wer von Hand nachbessert, tut
  // es womöglich doch - und zwei Links im selben Beitrag sehen nach Pfusch
  // aus. Am 2026-08-28 in einem echten Facebook-Beitrag passiert.
  const schonDrin = quelle && text.includes(quelle);

  if (quelle && !schonDrin && netz !== "instagram") {
    teile.push("", quelle);
  }
  if (f.schlagworte) {
    teile.push("", f.schlagworte.split(" ").map((w) => `#${w}`).join(" "));
  }
  if (quelle && netz === "instagram" && !schonDrin) {
    teile.push("", "Verweis im Profil.");
  }
  return teile.join("\n");
}

function emojiLeiste(feld) {
  const leiste = document.createElement("div");
  leiste.className = "emojis";
  EMOJIS.forEach((zeichen) => {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.textContent = zeichen;
    knopf.title = `${zeichen} einfügen`;
    knopf.onclick = () => {
      // An der Schreibmarke einfügen, nicht am Ende - sonst muss man es
      // hinterher doch wieder verschieben.
      const stelle = feld.selectionStart ?? feld.value.length;
      feld.value = feld.value.slice(0, stelle) + zeichen + feld.value.slice(feld.selectionEnd ?? stelle);
      feld.focus();
      feld.selectionStart = feld.selectionEnd = stelle + zeichen.length;
      feld.dispatchEvent(new Event("input"));
    };
    leiste.append(knopf);
  });
  return leiste;
}

function fassungsblock(beitragId, f, quelle) {
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

  f.feld = feld;
  block.append(emojiLeiste(feld));

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
  const alles = document.createElement("button");
  alles.className = "knopf";
  alles.textContent = "Alles kopieren";
  alles.title = "Text, Verweis und Schlagwörter – fertig zum Einfügen";
  alles.onclick = () => kopieren(fertigerText(f, quelle),
                                 "Beitrag in der Zwischenablage.");

  const nurText = document.createElement("button");
  nurText.className = "knopf leise";
  nurText.textContent = "Nur Text";
  nurText.onclick = () => kopieren(feld.value, "Text kopiert.");

  knoepfe.append(alles, sichern, nurText);

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

  // Eigenes Bild einsetzen, wenn das gewählte nicht passt.
  const waehler = document.createElement("input");
  waehler.type = "file";
  waehler.accept = "image/*";
  waehler.hidden = true;
  waehler.onchange = () => {
    const datei = waehler.files[0];
    if (!datei) return;
    const leser = new FileReader();
    leser.onload = async () => {
      try {
        await hole("/api/bild", { fassung: f.id, daten: leser.result });
        melden("Bild ersetzt.");
        blattOeffnen(beitragId);
      } catch (fehler) {
        melden(fehler.message, true);
      }
    };
    leser.readAsDataURL(datei);
  };
  const tauschen = document.createElement("button");
  tauschen.className = "knopf leise";
  tauschen.textContent = f.bild ? "Bild ersetzen" : "Bild wählen";
  tauschen.onclick = () => waehler.click();
  knoepfe.append(tauschen, waehler);

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
