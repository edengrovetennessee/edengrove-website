/* ===========================================================================
   The neighborhoods map.

   Mapbox when it can, the drawing when it cannot. Eden Grove is on the capped
   free tier - 5,000 map loads a month and a hard stop - so every path through
   here ends with something on screen. The svg in the page is what paints
   first; this file lays a real map over it and hides it, or leaves it alone
   and quietly fills in the detail layers it was shipped without.

   Reasons the fallback runs, all of them real: no WebGL, an ad blocker that
   eats api.mapbox.com, the month's loads spent, a token that has been
   rotated, or a phone on a dead connection.
   ======================================================================== */
(() => {
  "use strict";

  const TOKEN = "pk.eyJ1IjoiZWRlbmdyb3ZldGVhbSIsImEiOiJjbXdlMGpwMnkwMWYxMnhvbXliOWYxdHEwIn0.g7WnzK2C4Dhwh-4BV0xFzw";

  const mp   = document.querySelector(".mp");
  const host = document.getElementById("mp-gl");
  const svg  = document.querySelector(".mp__svg");
  const data = JSON.parse(document.getElementById("mp-data").textContent);
  if (!mp || !host || !svg) return;

  /* ---- the fallback -----------------------------------------------------
     The page ships with county outlines and water only. If we end up here
     the rest is worth having, so fetch it - but the map is already legible
     without it, so a failed fetch changes nothing. */
  let fellBack = false;
  function fallback(why) {
    if (fellBack) return;
    fellBack = true;
    host.remove();
    mp.classList.add("is-flat");
    if (window.console) console.info("[map] drawn fallback:", why);
    fetch("data/map-basemap.json")
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => {
        const land = svg.querySelector(".mp__land");
        if (!land) return;
        const ns = "http://www.w3.org/2000/svg";
        // The page ships with water and county lines; these five slot in
        // around them. Order matters and insertBefore(firstChild) reverses
        // it, which buried the interstates under the city-limit polygons -
        // so the group is rebuilt in the order a printed map draws: ground
        // up, quiet to loud.
        const want = ["mp__place", "mp__warea", "mp__wline", "mp__local",
                      "mp__sec", "mp__prim", "mp__county"];
        const have = {};
        [...land.children].forEach(c => { have[c.getAttribute("class")] = c; });
        ({ place: "mp__place", waterline: "mp__wline", local: "mp__local",
           secondary: "mp__sec", primary: "mp__prim" }, 0);
        [["place","mp__place"],["waterline","mp__wline"],["local","mp__local"],
         ["secondary","mp__sec"],["primary","mp__prim"]].forEach(([k, c]) => {
          if (!d.layers[k] || have[c]) return;
          const p = document.createElementNS(ns, "path");
          p.setAttribute("class", c);
          p.setAttribute("d", d.layers[k]);
          have[c] = p;
        });
        want.forEach(c => { if (have[c]) land.appendChild(have[c]); });
      })
      .catch(() => { /* the skeleton is enough */ });
  }

  if (!window.mapboxgl)            return fallback("mapbox-gl did not load");
  if (!mapboxgl.supported())       return fallback("no webgl");
  if (!TOKEN.startsWith("pk."))    return fallback("no token");

  /* ---- the map ---------------------------------------------------------- */
  mapboxgl.accessToken = TOKEN;
  const FIT = { padding: { top: 64, bottom: 64, left: 48, right: 48 }, duration: 0 };
  let map;
  try {
    map = new mapboxgl.Map({
      container: host,
      style: "mapbox://styles/mapbox/dark-v11",
      bounds: data.frames.Williamson.bounds,
      fitBoundsOptions: FIT,
      cooperativeGestures: true,   // a two-finger drag, so the page still scrolls
      attributionControl: true
    });
  } catch (e) { return fallback("map would not construct: " + e.message); }

  // Anything that goes wrong before the first paint means no map. A 401 is a
  // dead token, a 429 is the month's 5,000 loads gone.
  let painted = false;
  map.on("error", e => {
    const s = e && e.error && e.error.status;
    if (!painted) fallback("mapbox error" + (s ? " " + s : ""));
  });
  // Belt and braces: if nothing has painted in eight seconds, stop waiting.
  const giveUp = setTimeout(() => { if (!painted) fallback("timed out"); }, 8000);

  map.on("load", () => {
    painted = true;
    clearTimeout(giveUp);
    recolour();
    addPins();
    mp.classList.add("is-live");
    host.removeAttribute("aria-hidden");
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
  });

  /* ---- the palette ------------------------------------------------------
     Mapbox Dark is a fine map and the wrong colour. Rather than keep a style
     in Mapbox Studio that nobody here can edit, the layers are recoloured in
     place against the same tokens the rest of the site uses. Layer ids are
     from the published dark-v11 style; a missing one is skipped rather than
     thrown, because Mapbox revises the style and a rename must not take the
     map down with it. */
  const INK = "#14170F", WATER = "#19242E", CREEK = "#2E4150";
  const PAINT = [
    ["land",                "background-color", INK],
    ["national-park",       "fill-color",       "#1A2016"],
    ["landuse",             "fill-color",       "#181C13"],
    ["water",               "fill-color",       WATER],
    ["waterway",            "line-color",       CREEK],
    ["building",            "fill-color",       "#1C2017"],
    ["land-structure-polygon", "fill-color",    "#1C2017"],
    ["road-simple",         "line-color",       "rgba(244,241,236,.20)"],
    ["road-pedestrian",     "line-color",       "rgba(244,241,236,.10)"],
    ["road-path",           "line-color",       "rgba(244,241,236,.10)"],
    ["road-rail",           "line-color",       "rgba(167,148,124,.26)"],
    ["bridge-simple",       "line-color",       "rgba(244,241,236,.22)"],
    ["bridge-case-simple",  "line-color",       INK],
    ["tunnel-simple",       "line-color",       "rgba(244,241,236,.12)"],
    ["admin-0-boundary",    "line-color",       "rgba(167,148,124,.42)"],
    ["admin-1-boundary",    "line-color",       "rgba(167,148,124,.34)"],
    ["admin-1-boundary-bg", "line-color",       "rgba(0,0,0,0)"],
    ["admin-0-boundary-bg", "line-color",       "rgba(0,0,0,0)"],
  ];
  const TEXT = ["road-label-simple", "waterway-label", "natural-line-label",
                "natural-point-label", "water-line-label", "water-point-label",
                "poi-label", "airport-label", "settlement-subdivision-label",
                "settlement-minor-label", "settlement-major-label", "state-label"];

  function recolour() {
    PAINT.forEach(([id, prop, val]) => {
      if (map.getLayer(id)) { try { map.setPaintProperty(id, prop, val); } catch (e) {} }
    });
    TEXT.forEach(id => {
      if (!map.getLayer(id)) return;
      try {
        map.setPaintProperty(id, "text-color", "rgba(244,241,236,.78)");
        map.setPaintProperty(id, "text-halo-color", "rgba(20,23,15,.92)");
        map.setPaintProperty(id, "text-halo-width", 1.4);
      } catch (e) {}
    });
    // A point of interest every fifty yards is noise on a map about places.
    // settlement-subdivision-label goes too: it draws Belle Meade, Forest
    // Hills, Green Hills - the exact names we have a pin for - at the exact
    // point we put the pin, so the dot lands in the middle of the word.
    ["poi-label", "airport-label", "settlement-subdivision-label"].forEach(id => {
      if (map.getLayer(id)) { try { map.setLayoutProperty(id, "visibility", "none"); } catch (e) {} }
    });
    // Towns keep their names, pushed clear of the dot rather than under it.
    ["settlement-minor-label", "settlement-major-label"].forEach(id => {
      if (!map.getLayer(id)) return;
      try {
        map.setLayoutProperty(id, "text-offset", [0, 1.35]);
        map.setLayoutProperty(id, "text-anchor", "top");
      } catch (e) {}
    });
  }

  /* ---- the pins ---------------------------------------------------------
     Real anchors, not canvas symbols, so they tab, they take a keyboard
     return, and the browser shows the destination on hover like any other
     link on the site. */
  function addPins() {
    data.pins.forEach(p => {
      const a = document.createElement("a");
      a.className = "mk mk--" + p.kind;
      a.href = p.href;
      const many = p.count > 1;
      a.setAttribute("aria-label",
        p.kind === "listing"
          ? (many ? `${p.label}, ${p.count} listings` : `${p.label}, Eden Grove listing`)
          : `${p.label}, ${p.kind === "community" ? "luxury community" : "neighborhood"}`);

      // Three marks, each saying what the thing is: a pin is a place, a
      // gate is a gated community, the bonsai is one of ours.
      // A dot and a ring are centred on their point; a tree stands on it.
      const ART = {
        neighborhood: ["#eg-area", "0 0 24 24",      "center"],
        community:    ["#eg-comm", "0 0 24 24",      "center"],
        listing:      ["#eg-tree", "0 0 2536 1788",  "bottom"],
      }[p.kind];
      const dot = document.createElement("span");
      dot.className = "mk__dot";
      if (ART) {
        const NS = "http://www.w3.org/2000/svg";
        const s = document.createElementNS(NS, "svg");
        s.setAttribute("viewBox", ART[1]);
        s.setAttribute("aria-hidden", "true");
        const u = document.createElementNS(NS, "use");
        u.setAttribute("href", ART[0]);
        s.appendChild(u); dot.appendChild(s);
        if (p.kind === "listing" && many) dot.classList.add("mk__dot--many");
      }
      const lbl = document.createElement("span");
      lbl.className = "mk__lbl";
      lbl.textContent = many ? `${p.label} · ${p.count}` : p.label;

      a.append(dot, lbl);
      new mapboxgl.Marker({ element: a, anchor: (ART && ART[2]) || "center" })
        .setLngLat([p.lon, p.lat]).addTo(map);
    });
  }

  /* ---- the county switcher ---------------------------------------------- */
  document.querySelectorAll(".mp__county__b").forEach(b => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".mp__county__b")
        .forEach(o => o.classList.toggle("is-on", o === b));
      const f = data.frames[b.dataset.county];
      if (!f || !painted) return;
      map.fitBounds(f.bounds, { ...FIT, duration: 900 });
    });
  });
})();
