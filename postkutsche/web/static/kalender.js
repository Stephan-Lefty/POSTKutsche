/* Der Kalender.
 *
 * Ohne Rahmenwerk: Es ist eine Seite mit einem Raster und einer Seitenleiste.
 * Was React hier lösen würde, löst hier ein Neuzeichnen des Monats - bei
 * dreißig Kärtchen merkt das niemand, und eine Abhängigkeit weniger ist eine
 * Abhängigkeit weniger.
 */

const stand = {
  ersteWoche: null,      // Montag der obersten sichtbaren Woche
  letzteWoche: null,     // Montag der untersten
  projekte: [],
  netzwerke: {},
  palette: [],           // vorgeschlagene Projektfarben
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

  const [projekte, netze, palette] = await Promise.all([
    hole("/api/projekte"), hole("/api/netzwerke"), hole("/api/projektfarben"),
  ]);
  stand.palette = palette;
  stand.projekte = projekte;
  netze.forEach((n) => (stand.netzwerke[n.kennung] = n));
  projekte.forEach((p) => stand.sichtbar.add(p.kennung));

  spalteZeichnen();
  await monatLaden();

  $("#heute").onclick = () => {
    monatLaden();
    $("#rollbereich").scrollTop = 0;
  };
  rollenBeobachten();
  $("#blatt-zu").onclick = blattSchliessen;
  $("#thema").onclick = themaWechseln;

  const gemerkt = localStorage.getItem("thema");
  if (gemerkt) document.documentElement.dataset.thema = gemerkt;

  try {
    kampagneVorbereiten();
  } catch (fehler) {
    // Ein Fehler in der Wochenplanung darf den Kalender nicht mitreißen.
    melden(`Wochenplanung nicht verfügbar: ${fehler.message}`, true);
  }
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
  /* Kampagnen brauchen Kategorien, und die kommen bisher nur aus einer
     Seitenkarte. Gesperrte Einträge sagen aber nicht, warum sie gesperrt
     sind - wer nur »HaBeFa.de« sieht, hält die anderen Projekte für
     verschwunden. Deshalb steht der Grund jetzt dabei. */
  const GRUND = {
    shopware: "Kategorien noch nicht angebunden",
    wordpress: "Blog - Beiträge kommen von selbst, keine Kampagne",
  };
  stand.projekte.forEach((p) => {
    const eintrag = document.createElement("option");
    eintrag.value = p.kennung;
    eintrag.textContent = p.art === "seitenkarte"
      ? p.name
      : `${p.name} - ${GRUND[p.art] || "keine Kategorien"}`;
    if (p.art !== "seitenkarte") eintrag.disabled = true;
    auswahl.append(eintrag);
  });
  auswahl.onchange = kategorienLaden;

  // Montag bis Freitag vorbelegt. Für das Handwerk ist das die Regel; das
  // Wochenende ist wählbar, weil der Samstagvormittag für Bauherren eine
  // gute Zeit ist - da plant, wer werktags auf der Baustelle steht.
  const tage = $("#k-tage");
  tage.innerHTML = "";
  ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"].forEach((name, nummer) => {
    const feld = document.createElement("input");
    feld.type = "checkbox";
    feld.value = nummer;
    feld.checked = nummer < 5;
    const beschriftung = document.createElement("label");
    beschriftung.append(document.createTextNode(name), feld);
    tage.append(beschriftung);
  });

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

  // Escape schließt auch dann, wenn sonst nichts mehr reagiert. Am
  // 2026-08-28 hing die Maske, weil eine gescheiterte Kategorienabfrage die
  // Einrichtung abbrach - und damit auch die Zuweisung des Abbrechen-Knopfs.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("#kampagne").hidden) $("#kampagne").hidden = true;
  });

  // Ohne await und ohne Abbruch: Ob die Kategorien laden, darf nicht
  // darüber entscheiden, ob die Knöpfe funktionieren.
  kategorienLaden().catch((fehler) => melden(fehler.message, true));
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
  try {
    bereicheFuellen();
    kategorienZeichnen();
  } catch (fehler) {
    liste.innerHTML =
      `<p class="schlagworte">Kategorien nicht darstellbar: ${fehler.message}</p>`;
  }
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

  if (bericht.weggeraeumt?.length) {
    const hinweis = document.createElement("p");
    hinweis.className = "schlagworte";
    hinweis.textContent =
      `${bericht.weggeraeumt.length} verfallene Entwürfe wurden entfernt – ` +
      "Vorschläge, deren Termin ohne Freigabe verstrichen ist.";
    kasten.append(hinweis);
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

/** Fragt, was mit kürzlich beworbenen Produkten geschehen soll.
 *
 * Drei Möglichkeiten statt der zwei, die ein confirm() hergibt: »trotzdem«,
 * »andere nehmen« oder abbrechen. Gibt die Wahl zurück oder null.
 */
function wiederholungWaehlen(wiederholungen) {
  return new Promise((antworten) => {
    const huelle = document.createElement("div");
    huelle.className = "ueberlagerung";

    const kasten = document.createElement("div");
    kasten.className = "kasten";
    kasten.style.maxWidth = "460px";

    const titel = document.createElement("h2");
    titel.textContent = wiederholungen.length === 1
      ? "Ein Produkt war schon dran"
      : `${wiederholungen.length} Produkte waren schon dran`;
    kasten.append(titel);

    const erklaerung = document.createElement("p");
    erklaerung.className = "schlagworte";
    erklaerung.textContent = "In den letzten vier Wochen bereits beworben:";
    kasten.append(erklaerung);

    const liste = document.createElement("div");
    liste.className = "bericht";
    wiederholungen.forEach((w) => {
      const zeile = document.createElement("div");
      zeile.className = "berichtzeile";
      const titeltext = w.titel.length > 46 ? w.titel.slice(0, 46) + "…" : w.titel;
      zeile.textContent = `${titeltext}  –  ${w.lesbar}`;
      liste.append(zeile);
    });
    kasten.append(liste);

    const knoepfe = document.createElement("div");
    knoepfe.className = "knoepfe";

    const fertig = (wahl) => { huelle.remove(); antworten(wahl); };

    const andere = document.createElement("button");
    andere.type = "button";
    andere.className = "knopf";
    andere.textContent = "Andere Produkte nehmen";
    andere.onclick = () => fertig("ersetzen");

    const trotzdem = document.createElement("button");
    trotzdem.type = "button";
    trotzdem.className = "knopf leise";
    trotzdem.textContent = "Trotzdem einplanen";
    trotzdem.onclick = () => fertig("trotzdem");

    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "knopf leise";
    weg.textContent = "Abbrechen";
    weg.onclick = () => fertig(null);

    knoepfe.append(andere, trotzdem, weg);
    kasten.append(knoepfe);
    huelle.append(kasten);
    document.body.append(huelle);
    andere.focus();
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

  const tage = [...$("#k-tage").querySelectorAll("input:checked")]
    .map((f) => Number(f.value));
  if (!tage.length) return melden("Wähle mindestens einen Wochentag.", true);

  // Erlaubnis erst hier erfragen, nicht beim Laden der Seite: Wer den Lauf
  // startet, wird die Benachrichtigung gleich brauchen.
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }

  const knopf = $("#k-los");
  knopf.disabled = true;
  $("#k-bericht").hidden = true;
  const jeTag = Number($("#k-jetag").value);
  const anzahlTage = $("#k-tage").querySelectorAll("input:checked").length;
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
    // Einmal zusammenstellen: Der Auftrag wird womöglich zweimal gebraucht -
    // einmal zum Prüfen, einmal zum Ausführen. Zweimal aufgeschrieben wiche
    // er irgendwann voneinander ab.
    const auftrag = {
      projekt: $("#k-projekt").value,
      thema: $("#k-thema").value,
      kalenderwoche: Number($("#k-woche").value),
      jahr: Number($("#k-jahr").value),
      kategorien,
      netzwerke: netze,
      je_tag: jeTag,
      tage,
      hersteller: $("#k-hersteller").value.split(",").map((h) => h.trim()).filter(Boolean),
    };
    let bericht = await hole("/api/kampagne", { ...auftrag, bestaetigt: false });

    // Waren Produkte in den letzten vier Wochen schon dran, wird gefragt -
    // mit drei Möglichkeiten. »Abbrechen« hieße sonst »gar nichts«, obwohl
    // meistens gemeint ist: nimm eben andere.
    if (bericht.rueckfrage) {
      const wahl = await wiederholungWaehlen(bericht.wiederholungen);
      if (!wahl) {
        $("#k-stand").textContent = "Abgebrochen – nichts angelegt.";
        return;
      }

      // Bei einer Wiederholung wird immer neu formuliert - ohne Rückfrage.
      // Es gibt keinen Fall, in dem wortgleich besser wäre: Facebook und
      // Instagram halten solche Beiträge zurück, und bei Mastodon liest sie
      // niemand zweimal.
      $("#k-stand").textContent = wahl === "ersetzen"
        ? "Andere Produkte werden gesucht …"
        : "Entwürfe entstehen …";
      bericht = await hole("/api/kampagne", {
        ...auftrag, bestaetigt: true, wiederholungen: wahl,
      });
    }

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

    // Der Punkt ist ein Knopf: Ein Klick öffnet die Farbwahl. Er sitzt
    // außerhalb der Beschriftung, sonst schaltete jeder Klick zugleich das
    // Häkchen um.
    const punkt = document.createElement("button");
    punkt.className = "punkt punktknopf";
    punkt.style.background = p.farbe;
    punkt.title = `Farbe von ${p.name} ändern`;
    punkt.setAttribute("aria-label", `Farbe von ${p.name} ändern`);
    punkt.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      farbwahlOeffnen(p, punkt);
    };

    const name = document.createElement("span");
    name.className = "name";
    name.textContent = p.name;

    const beschriftung = document.createElement("label");
    beschriftung.append(feld, name);
    zeile.append(punkt, beschriftung);

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
    const zeile = document.createElement("li");
    // Kürzel und Name nebeneinander: Das Kürzel steht so auch in den
    // Kärtchen, der Name sagt, wofür es steht. Links ist Platz dafür.
    const kuerzel = document.createElement("span");
    kuerzel.className = "kuerzel";
    kuerzel.textContent = n.kuerzel;
    kuerzel.style.borderColor = n.farbe;
    kuerzel.style.color = n.farbe;

    const name = document.createElement("span");
    name.textContent = n.name;

    zeile.style.borderColor = n.farbe;
    zeile.append(kuerzel, name);
    marken.append(zeile);
  });
}

/** Kleine Farbwahl neben dem Projektpunkt.
 *
 * Die Palette hält Abstand zu den Netzwerkfarben - aber sie ist ein
 * Vorschlag, keine Vorschrift. Wer eine eigene Farbe will, nimmt den
 * Farbwähler daneben; gewarnt wird, nicht verboten.
 */
function farbwahlOeffnen(projekt, ankerknopf) {
  document.querySelector(".farbwahl")?.remove();

  const kasten = document.createElement("div");
  kasten.className = "farbwahl";

  const titel = document.createElement("div");
  titel.className = "farbwahl-titel";
  titel.textContent = projekt.name;
  kasten.append(titel);

  const raster = document.createElement("div");
  raster.className = "farbwahl-raster";
  stand.palette.forEach((eintrag) => {
    const knopf = document.createElement("button");
    knopf.className = "farbtupfer";
    knopf.style.background = eintrag.farbe;
    knopf.title = eintrag.farbe;
    if (eintrag.farbe === projekt.farbe) knopf.classList.add("gewaehlt");
    knopf.onclick = () => farbeSetzen(projekt, eintrag.farbe, kasten);
    raster.append(knopf);
  });
  kasten.append(raster);

  const eigene = document.createElement("label");
  eigene.className = "farbwahl-eigene";
  const feld = document.createElement("input");
  feld.type = "color";
  feld.value = projekt.farbe;
  feld.onchange = () => farbeSetzen(projekt, feld.value, kasten);
  eigene.append(document.createTextNode("eigene Farbe"), feld);
  kasten.append(eigene);

  ankerknopf.parentElement.append(kasten);

  // Klick daneben schließt. Erst im nächsten Durchlauf anmelden, sonst
  // fängt dieser Handler noch den Klick ab, der das Fenster geöffnet hat.
  setTimeout(() => {
    const zu = (e) => {
      if (!kasten.contains(e.target)) {
        kasten.remove();
        document.removeEventListener("click", zu);
      }
    };
    document.addEventListener("click", zu);
  }, 0);
}

async function farbeSetzen(projekt, farbe, kasten) {
  try {
    const antwort = await hole("/api/projektfarbe",
                               { projekt: projekt.kennung, farbe });
    projekt.farbe = antwort.farbe;
    kasten.remove();
    spalteZeichnen();
    monatLaden();
    melden(antwort.warnung || `Farbe von ${projekt.name} geändert.`,
           Boolean(antwort.warnung));
  } catch (fehler) {
    melden(fehler.message, true);
  }
}

// -- Rollende Wochenansicht -------------------------------------------------
//
// Statt eines Monatsrasters eine Liste von Wochen: die laufende und fünf
// weitere. Wer weiter blättert, lädt nach - nach oben in die Vergangenheit,
// nach unten in die Zukunft.
//
// Der Grund gegen das Monatsraster: Geplant wird über den Monatswechsel
// hinweg. Wer Ende August die KW 36 vorbereitet, sieht im Augustraster nur
// den 31. und muss blättern - ausgerechnet an der Stelle, an der er arbeitet.

const WOCHEN_SICHTBAR = 6;

/** Der Montag der Woche, in der ein Datum liegt. */
function montagVon(d) {
  const m = new Date(d);
  m.setDate(m.getDate() - ((m.getDay() + 6) % 7));
  m.setHours(0, 0, 0, 0);
  return m;
}

function tageSpaeter(d, n) {
  const neu = new Date(d);
  neu.setDate(neu.getDate() + n);
  return neu;
}

async function monatLaden() {
  // Der Name bleibt, damit die übrigen Aufrufe nicht alle geändert werden
  // müssen - gemeint ist: den sichtbaren Bereich neu zeichnen.
  stand.ersteWoche = montagVon(new Date());
  stand.letzteWoche = tageSpaeter(stand.ersteWoche, (WOCHEN_SICHTBAR - 1) * 7);
  $("#raster").innerHTML = "";
  await bereichZeichnen(stand.ersteWoche, stand.letzteWoche, "unten");
  titelSetzen();
}

function titelSetzen() {
  const von = stand.ersteWoche;
  const bis = tageSpaeter(stand.letzteWoche, 6);
  const form = { day: "2-digit", month: "short" };
  $("#monatstitel").textContent =
    `${von.toLocaleDateString("de-DE", form)} – ${bis.toLocaleDateString("de-DE", { ...form, year: "numeric" })}`;
}

async function beitraegeHolen(von, bis) {
  const frage = new URLSearchParams({
    von: tagesschluessel(von),
    bis: tagesschluessel(tageSpaeter(bis, 7)),
  });
  stand.projekte.forEach((p) => {
    if (stand.sichtbar.has(p.kennung)) frage.append("projekt", p.kennung);
  });
  const daten = await hole(`/api/beitraege?${frage}`);
  return daten.beitraege;
}

let laedtGerade = false;

async function bereichZeichnen(vonMontag, bisMontag, richtung) {
  if (laedtGerade) return;
  laedtGerade = true;
  const raster = $("#raster");

  let beitraege;
  try {
    beitraege = await beitraegeHolen(vonMontag, bisMontag);
  } catch (fehler) {
    melden(fehler.message, true);
    laedtGerade = false;
    return;
  }

  const nachTag = new Map();
  beitraege.forEach((b) => {
    const schluessel = b.geplant_ort.slice(0, 10);
    if (!nachTag.has(schluessel)) nachTag.set(schluessel, []);
    nachTag.get(schluessel).push(b);
  });

  const heute = tagesschluessel(new Date());
  const stuecke = document.createDocumentFragment();
  const wochen = Math.round((bisMontag - vonMontag) / 604800000) + 1;

  for (let w = 0; w < wochen; w++) {
    const montag = tageSpaeter(vonMontag, w * 7);
    const kw = kalenderwoche(montag);

    const kopf = document.createElement("div");
    kopf.className = "wochenkopf";
    const sonntag = tageSpaeter(montag, 6);
    kopf.textContent =
      `KW ${kw.woche} · ${montag.toLocaleDateString("de-DE", { day: "2-digit", month: "long" })}` +
      ` bis ${sonntag.toLocaleDateString("de-DE", { day: "2-digit", month: "long" })}`;
    if (kw.woche === kalenderwoche(new Date()).woche
        && kw.jahr === kalenderwoche(new Date()).jahr) {
      kopf.classList.add("jetzt");
      kopf.textContent += " · diese Woche";
    }
    stuecke.append(kopf);

    const kwFeld = document.createElement("div");
    kwFeld.className = "kw";
    kwFeld.textContent = kw.woche;
    stuecke.append(kwFeld);

    for (let i = 0; i < 7; i++) {
      const tag = tageSpaeter(montag, i);
      const schluessel = tagesschluessel(tag);
      const kasten = document.createElement("div");
      kasten.className = "tag" + (schluessel === heute ? " heute" : "");
      kasten.dataset.tag = schluessel;

      const zahl = document.createElement("span");
      zahl.className = "zahl";
      zahl.textContent = tag.getDate() === 1
        ? tag.toLocaleDateString("de-DE", { day: "numeric", month: "short" })
        : tag.getDate();
      kasten.append(zahl);

      (nachTag.get(schluessel) || [])
        .sort((a, b) => a.geplant.localeCompare(b.geplant))
        .forEach((b) => kasten.append(kaertchen(b)));

      ablegenErlauben(kasten);
      stuecke.append(kasten);
    }
  }

  const bereich = $("#rollbereich");
  if (richtung === "oben") {
    // Beim Nachladen nach oben rutscht der Inhalt weg. Die Rollposition wird
    // um die dazugekommene Höhe verschoben, sonst springt die Ansicht.
    const vorher = bereich.scrollHeight;
    raster.prepend(stuecke);
    bereich.scrollTop += bereich.scrollHeight - vorher;
  } else {
    raster.append(stuecke);
  }
  laedtGerade = false;
}

function rollenBeobachten() {
  const bereich = $("#rollbereich");
  bereich.onscroll = async () => {
    if (laedtGerade) return;
    const rest = bereich.scrollHeight - bereich.scrollTop - bereich.clientHeight;

    if (rest < 200) {
      const neuVon = tageSpaeter(stand.letzteWoche, 7);
      stand.letzteWoche = tageSpaeter(neuVon, 21);
      await bereichZeichnen(neuVon, stand.letzteWoche, "unten");
      titelSetzen();
    } else if (bereich.scrollTop < 200) {
      const neuBis = tageSpaeter(stand.ersteWoche, -7);
      stand.ersteWoche = tageSpaeter(neuBis, -21);
      await bereichZeichnen(stand.ersteWoche, neuBis, "oben");
      titelSetzen();
    }
  };
}

function kaertchen(b) {
  const kasten = document.createElement("button");
  kasten.className = "kaertchen";
  // Beim Nachladen werden alle Kärtchen neu gebaut. Ohne das hier verlöre
  // der gerade offene Beitrag seine Markierung, sobald man weiterscrollt.
  if (stand.offen === b.id) kasten.classList.add("offen");
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

/* Markiert das Kärtchen, dessen Beitrag gerade offen ist.
   Wird auch beim Zeichnen aufgerufen: Die Kärtchen werden bei jedem
   Nachladen neu erzeugt, eine einmal gesetzte Klasse wäre danach weg. */
function auswahlZeigen() {
  document.querySelectorAll(".kaertchen.offen")
    .forEach((k) => k.classList.remove("offen"));
  if (stand.offen === null || stand.offen === undefined) return;
  const kasten = document.querySelector(`.kaertchen[data-id="${stand.offen}"]`);
  if (kasten) kasten.classList.add("offen");
}

function blattSchliessen() {
  $("#blatt").hidden = true;
  stand.offen = null;
  auswahlZeigen();
}

async function blattOeffnen(id) {
  let b;
  try {
    b = await hole(`/api/beitrag/${id}`);
  } catch (fehler) {
    return melden(fehler.message, true);
  }
  stand.offen = id;
  auswahlZeigen();

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

  /* Freigeben heißt »darf raus«, nicht »ist raus«. Bis der Beitrag draußen
     ist, fehlen im Handbetrieb noch drei Schritte: kopieren, drüben
     einstellen, hier abhaken. Wer nur den Knopf sieht, hält das eine für das
     andere - deshalb sagt der Knopf jetzt, wo man steht, statt unverändert
     stehenzubleiben und sich beliebig oft drücken zu lassen. */
  if (b.zustand === "freigegeben" || b.zustand === "erledigt") {
    const stand_ = document.createElement("span");
    stand_.className = "schlagworte";
    stand_.textContent = b.zustand === "erledigt"
      ? "✓ erledigt - dieser Beitrag ist draußen"
      : "✓ freigegeben - fehlt noch: bei jedem Netzwerk einstellen und abhaken";
    knoepfe.append(stand_);
  } else {
    const frei = document.createElement("button");
    frei.className = "knopf";
    frei.textContent = "Freigeben";
    frei.onclick = async () => {
      try {
        await hole("/api/freigeben", { id });
        melden("Freigegeben. Zum Veröffentlichen noch kopieren und abhaken.");
        monatLaden();
        blattOeffnen(id);
      } catch (fehler) {
        melden(fehler.message, true);
      }
    };
    knoepfe.append(frei);
  }
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
    // Frage plus Antwortfeld. Ohne die Möglichkeit zu antworten bliebe nur,
    // den Text von Hand zu ergänzen - dann lernt niemand etwas, und beim
    // nächsten Produkt kommt dieselbe Frage wieder.
    const kasten = document.createElement("div");
    kasten.className = "frage";

    const frage = document.createElement("p");
    frage.className = "fragetext";
    frage.textContent = f.rueckfrage;
    kasten.append(frage);

    const feld = document.createElement("textarea");
    feld.className = "antwortfeld";
    feld.rows = 2;
    feld.placeholder = "Antwort … (Strg+Enter zum Absenden)";
    kasten.append(feld);

    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "knopf";
    knopf.textContent = "Antworten und nachbessern";
    const absenden = async () => {
      const antwort = feld.value.trim();
      if (!antwort) return melden("Ohne Antwort geht es nicht.", true);
      knopf.disabled = true;
      knopf.textContent = "Claude bessert nach …";
      try {
        const neu = await hole("/api/antwort", { fassung: f.id, antwort });
        melden(neu.rueckfrage
          ? "Nachgebessert – aber es ist noch eine Frage offen."
          : "Nachgebessert.", Boolean(neu.rueckfrage));
        blattOeffnen(beitragId);
        monatLaden();
      } catch (fehler) {
        melden(fehler.message, true);
        knopf.disabled = false;
        knopf.textContent = "Antworten und nachbessern";
      }
    };
    knopf.onclick = absenden;
    feld.onkeydown = (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) absenden();
    };
    kasten.append(knopf);
    block.append(kasten);
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
