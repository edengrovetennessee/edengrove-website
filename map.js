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
  // One frame, around everything. There were two - Williamson and Davidson,
  // on a switcher - until 13 Nov, when the cards above the map took over the
  // choosing and asking which county first became a question nobody arrives
  // with. Computed from the pins rather than written down, so adding a place
  // in Maury or Rutherford reframes the map instead of falling off it.
  const ALL = data.pins.reduce((b, p) => [
    [Math.min(b[0][0], p.lon), Math.min(b[0][1], p.lat)],
    [Math.max(b[1][0], p.lon), Math.max(b[1][1], p.lat)],
  ], [[180, 90], [-180, -90]]);
  let map;
  try {
    map = new mapboxgl.Map({
      container: host,
      style: "mapbox://styles/mapbox/dark-v11",
      bounds: ALL,
      fitBoundsOptions: FIT,
      // Ryan, 13 Nov: "they like can't actually interact with the map per
      // se." The map is an answer, not an instrument. No drag, no scroll
      // zoom, no double-click, no keyboard panning - the cards drive it and
      // nothing else does. It also means the map can never be left somewhere
      // confusing, and a thumb scrolling the page past it never gets caught.
      // The markers are ordinary DOM elements, so they still take a click.
      interactive: false,
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

    // The frame is as tall as the drawing - about 2,570px - until is-live
    // turns it into an 820px window. Mapbox defers its own resize work while
    // the map is below the fold, so the canvas stayed at the old height: the
    // visitor saw the top third of the fitted bounds, and every marker sat
    // hundreds of pixels below where its house is. Nothing errored and the
    // map looked plausible, which is why this survived a week.
    //
    // So resize on purpose rather than hoping, refit afterwards because the
    // first fitBounds was measured against the wrong box, and keep watching
    // the frame: it also changes height at the 620px breakpoint.
    requestAnimationFrame(() => {
      map.resize();
      map.fitBounds(ALL, FIT);
    });
    if (window.ResizeObserver) {
      let w = 0, hgt = 0;
      new ResizeObserver(es => {
        const r = es[0].contentRect;
        if (Math.abs(r.width - w) < 1 && Math.abs(r.height - hgt) < 1) return;
        w = r.width; hgt = r.height;
        map.resize();
      }).observe(host);
    }

    // No zoom buttons either: with the map locked they would be the one
    // thing on it that looks operable, and they are not.
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
      marks[p.href] = { p: p, el: a, show: card(a, p) };
      new mapboxgl.Marker({ element: a, anchor: (ART && ART[2]) || "center" })
        .setLngLat([p.lon, p.lat]).addTo(map);
    });
    wirePicker();
  }

  /* ---- the cards above the map ------------------------------------------
     Each one is an ordinary link to the place's own page, and that is what
     it does with no Javascript, no WebGL or no Mapbox. Only once the tiles
     are actually up do we take the click instead and fly there - so the
     fallback is never a row of cards that swallow a click and do nothing.

     Clicking a card does not open the page. It answers "where is this",
     which is the question the map exists for, and opens the mark's own card
     so the way in is sitting there. Two clicks to a page, and the second one
     is taken somewhere you have seen. */
  const marks = {};
  const ZOOM = { neighborhood: 12.6, community: 14, listing: 14.4 };

  function wirePicker() {
    const cards = [...document.querySelectorAll(".pick__c")];
    cards.forEach(c => {
      const key = c.dataset.pin;
      const m = marks[key];
      if (!m) return;                       // no mark, so leave it a plain link
      c.addEventListener("click", e => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;  // new tab
        e.preventDefault();
        cards.forEach(o => o.classList.toggle("is-on", o === c));
        map.flyTo({
          center: [m.p.lon, m.p.lat],
          zoom: ZOOM[m.p.kind] || 13,
          duration: reduced ? 0 : 1500,
          essential: true,
        });
        m.show();
        pulse(m.el);
        // The map is below the cards. Landing somewhere the visitor cannot
        // see is the same as not landing at all.
        const frame = document.querySelector(".mp__frame");
        if (frame) frame.scrollIntoView(
          { behavior: reduced ? "auto" : "smooth", block: "center" });
      });
    });
  }
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* A ring, twice, where the map just landed.
     Nothing on this map pulses on its own - a field of blinking dots was the
     first thing Ryan took off it. This is different: it fires once, on the
     mark you just asked for, and stops. It is the map answering, not the map
     waving. Off entirely under reduced motion, where the fly is instant and
     there is nothing to draw the eye away from anyway. */
  function pulse(el) {
    if (!el || reduced) return;
    el.querySelectorAll(".mk__ping").forEach(n => n.remove());
    const r = document.createElement("span");
    r.className = "mk__ping";
    r.setAttribute("aria-hidden", "true");
    el.appendChild(r);
    r.addEventListener("animationend", () => r.remove(), { once: true });
    setTimeout(() => r.remove(), 4000);   // belt and braces if the event is missed
  }


  /* ---- the card ---------------------------------------------------------
     A mark on a map does not look like a door. The label on hover said what
     the place was called and still gave no reason to believe a page was
     behind it. The card does: the photograph off that page, the name, and
     somewhere to go.

     Mouse and touch want different things. A cursor hovers to look and
     clicks to go, so the card opens on hover and the mark itself stays a
     plain link. A thumb has no hover, so the first tap opens the card and
     the button inside it navigates - nobody gets thrown onto a page they
     grazed with a 20px target.

     A pin with no photograph gets a card with no photograph. Five of the
     coming-soon listings have no picture of themselves and must not borrow
     one from somewhere else. */
  const KIND = { neighborhood: "Neighborhood", community: "Luxury Community",
                 listing: "Eden Grove Listing" };
  let open = null;
  const touch = window.matchMedia("(hover: none)").matches;

  function card(a, p) {
    // closeOnClick would be right if the card opened any other way. It
    // listens for a click on the map, and a marker element is a child of the
    // map's own canvas container - so on a phone the tap that opens the card
    // bubbles up and closes it again in the same millisecond. The card
    // appeared and vanished and the mark looked broken. We dismiss it
    // ourselves instead: the mark's handler stops the tap propagating, and a
    // tap anywhere else on the map closes whatever is open.
    const pop = new mapboxgl.Popup({
      closeButton: false, closeOnClick: false, offset: 18,
      maxWidth: "none", className: "mkpop",
    });
    const many = p.count > 1;
    const sub  = many ? p.count + " listings" : (KIND[p.kind] || "");
    const html =
      '<a class="mkpop__a" href="' + p.href + '">' +
      (p.img ? '<span class="mkpop__ph"><img src="media/thumb/' + p.img +
               '.webp" alt="" loading="lazy" decoding="async" width="560" height="370"></span>'
             // An empty band reads as an image that failed to load. The mark
             // in it says the photograph is not taken yet, which is true.
             : '<span class="mkpop__ph mkpop__ph--none">' +
               '<svg viewBox="0 0 2536 1788" aria-hidden="true"><use href="#eg-tree"/></svg>' +
               '</span>') +
      '<span class="mkpop__b">' +
        '<span class="mkpop__k">' + sub + '</span>' +
        '<span class="mkpop__n">' + p.label + '</span>' +
        '<span class="mkpop__go">' +
        (p.kind === "listing" ? (many ? "View listings" : "View property") : "Explore") +
        ' <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" stroke-width="1.4" ' +
        'aria-hidden="true"><path d="M2 1l3 3-3 3"/></svg></span>' +
      '</span></a>';

    const show = () => {
      if (open && open !== pop) open.remove();
      pop.setLngLat([p.lon, p.lat]).setHTML(html).addTo(map);
      open = pop;
    };
    const hide = () => { if (open === pop) { pop.remove(); open = null; } };
    // The cards above the map need to be able to open this one.
    const handle = show;

    if (touch) {
      // first tap previews, the card's own link goes
      a.addEventListener("click", e => {
        e.preventDefault();
        e.stopPropagation();   // or the map hears it and closes the card
        show();
      });
    } else {
      a.addEventListener("pointerenter", e => { if (e.pointerType !== "touch") show(); });
      a.addEventListener("focus", show);
      a.addEventListener("blur", hide);
      // Leaving the mark must not close a card the cursor is moving into.
      //
      // The subtle one: the card often opens UNDERNEATH the cursor, because
      // it is anchored to the point the cursor is already on. The browser
      // then fires pointerleave on the mark the instant it appears - the
      // pointer really has left the mark, it is over the card now - and a
      // naive timer closes the card the moment it opens. Worse, it never
      // fires pointerenter on the card either, because the pointer did not
      // move into it; the card arrived around a stationary pointer.
      //
      // So: ignore a leave whose relatedTarget is inside the card, and let
      // a pointermove anywhere over the card cancel a pending close.
      let t = null;
      const arm = () => { clearTimeout(t); t = setTimeout(hide, 260); };
      const keep = () => clearTimeout(t);
      a.addEventListener("pointerleave", e => {
        const el = pop.getElement();
        if (el && e.relatedTarget && el.contains(e.relatedTarget)) return;
        arm();
      });
      pop.on("open", () => {
        const el = pop.getElement();
        if (!el) return;
        el.addEventListener("pointerenter", keep);
        el.addEventListener("pointermove", keep);
        el.addEventListener("pointerleave", arm);
      });
    }
    return handle;
  }

})();
