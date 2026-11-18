/* ===========================================================================
   EDEN GROVE — THE PROPERTY GALLERY

   Takes the gallery a property page already has and gives it three things it
   did not: rooms that open and close, a contact sheet instead of a wall of
   large frames, and a viewer that opens a rendering at full size.

   PROGRESSIVE. The markup on the page does not change. Every .p-shot is
   still an anchor to the full image, so with this file missing, blocked or
   broken the gallery is exactly what it was: rooms, frames, and a click that
   opens the picture. Everything below is an upgrade applied on top.

   WHY THE THUMBNAILS CROP AND THE FULL VIEW DOES NOT. On the page the frames
   are one size and one shape, because a contact sheet that changes shape
   every row is not a contact sheet, it is the problem it was meant to solve.
   Nothing is lost by it: the viewer shows the whole frame, uncropped, on the
   ground it was designed against.
   ======================================================================== */
(function () {
  "use strict";

  var sheet = document.querySelector('section[aria-labelledby="gal-h"]');
  if (!sheet) return;
  var groups = sheet.querySelectorAll(".p-gal");
  if (!groups.length) return;

  var EASE = "cubic-bezier(.22,.61,.36,1)";
  var less = matchMedia("(prefers-reduced-motion:reduce)");

  /* ---- styles ------------------------------------------------------------ */
  var css = [
    /* the room header becomes the control */
    ".p-gal__head{cursor:pointer;-webkit-user-select:none;user-select:none}",
    ".p-gal__head:focus-visible{outline:1px solid var(--brass);outline-offset:.5rem}",
    /* THE CHEVRON IS A SPAN, AND EVERY RULE FOR IT GOES THROUGH .p-gal__head.
       The head already styles its own <i> as the rule line — .p-gal__head i —
       and that outranks a bare class, so an <i> chevron was being handed
       flex:1;height:1px and stretched into a 500px bar, which, rotated 45
       degrees, drew a diagonal line across the page for every room. */
    ".p-gal__head .p-gal__count{font-size:.58rem;letter-spacing:.24em;color:var(--t3);flex:0 0 auto}",
    ".p-gal__head .p-gal__chev{flex:0 0 auto;width:.5rem;height:.5rem;margin-left:.1rem;",
      "background:none;border-right:1px solid var(--t2);border-bottom:1px solid var(--t2);",
      "transform:rotate(45deg) translate(-.1rem,-.1rem);transition:transform .4s " + EASE + "}",
    ".p-gal__head[aria-expanded=true] .p-gal__chev{transform:rotate(-135deg) translate(-.1rem,-.1rem)}",

    /* opens on rows rather than a guessed height, so a longer room cannot clip */
    ".p-gal__panel{display:grid;grid-template-rows:0fr;transition:grid-template-rows .55s " + EASE + "}",
    ".p-gal__panel[data-on]{grid-template-rows:1fr}",
    ".p-gal__panel > div{overflow:hidden}",

    /* the contact sheet */
    ".p-gal__sheet{display:grid;gap:clamp(.4rem,.8vw,.7rem);padding-top:1.1rem;",
      "grid-template-columns:repeat(auto-fill,minmax(17rem,1fr))}",
    ".p-gal__sheet .p-shot{aspect-ratio:4/3;cursor:zoom-in}",
    "@media (max-width:1100px){.p-gal__sheet{grid-template-columns:repeat(auto-fill,minmax(13rem,1fr))}}","@media (max-width:620px){.p-gal__sheet{grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr))}}",

    /* ---- the viewer ---- */
    ".p-lb{position:fixed;inset:0;z-index:9500;display:grid;place-items:center;",
      "background:rgba(8,10,7,.93);opacity:0;transition:opacity .4s " + EASE + "}",
    ".p-lb[hidden]{display:none}",
    ".p-lb[data-on]{opacity:1}",
    ".p-lb__img{max-width:min(94vw,112rem);max-height:86vh;width:auto;height:auto;",
      "display:block;background:#1b1f19}",
    ".p-lb__cap{position:absolute;left:0;right:0;bottom:clamp(1rem,3vh,2rem);",
      "text-align:center;font-family:var(--ui);font-weight:300;font-size:.72rem;",
      "letter-spacing:.2em;text-indent:.2em;text-transform:uppercase;color:var(--t2);",
      "padding:0 4rem}",
    ".p-lb__n{display:block;margin-top:.5rem;font-size:.6rem;color:var(--t3)}",
    ".p-lb__btn{position:absolute;top:50%;transform:translateY(-50%);width:3.4rem;height:3.4rem;",
      "display:grid;place-items:center;background:none;border:0;cursor:pointer;",
      "color:var(--t2);transition:color .3s " + EASE + "}",
    ".p-lb__btn:hover,.p-lb__btn:focus-visible{color:#fff;outline:none}",
    ".p-lb__btn svg{width:.8rem;height:.8rem;stroke:currentColor;stroke-width:1.3;fill:none}",
    ".p-lb__prev{left:clamp(.3rem,2vw,1.6rem)}",
    ".p-lb__next{right:clamp(.3rem,2vw,1.6rem)}",
    ".p-lb__x{position:absolute;top:clamp(.3rem,2vh,1rem);right:clamp(.3rem,2vw,1.6rem);",
      "width:3.4rem;height:3.4rem;display:grid;place-items:center;background:none;border:0;",
      "cursor:pointer;color:var(--t2);transition:color .3s " + EASE + "}",
    ".p-lb__x:hover,.p-lb__x:focus-visible{color:#fff;outline:none}",
    ".p-lb__x svg{width:.78rem;height:.78rem;stroke:currentColor;stroke-width:1.3;fill:none}",
    "@media (max-width:620px){",
      ".p-lb__img{max-width:96vw;max-height:72vh}",
      ".p-lb__btn{top:auto;bottom:clamp(.6rem,2vh,1.2rem);transform:none}",
    "}",
    "@media (prefers-reduced-motion:reduce){",
      ".p-gal__panel,.p-lb,.p-gal__head .p-gal__chev{transition:none}",
    "}"
  ].join("");
  var s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);

  /* ---- rebuild each room as a sheet inside a panel ----------------------- */
  var all = [];                                   // every shot, in page order

  Array.prototype.forEach.call(groups, function (group, gi) {
    var head  = group.querySelector(".p-gal__head");
    var rows  = group.querySelectorAll(".p-gal__row");
    if (!head || !rows.length) return;

    var shots = group.querySelectorAll(".p-shot");
    var sheetEl = document.createElement("div");
    sheetEl.className = "p-gal__sheet";
    Array.prototype.forEach.call(shots, function (a) {
      a.dataset.i = all.length;
      all.push({ href: a.getAttribute("href"), alt: (a.querySelector("img") || {}).alt || "" });
      sheetEl.appendChild(a);                     // moves it, keeps the node
    });
    Array.prototype.forEach.call(rows, function (r) { r.remove(); });

    var inner = document.createElement("div");
    inner.appendChild(sheetEl);
    var panel = document.createElement("div");
    panel.className = "p-gal__panel";
    panel.id = "gal-panel-" + gi;
    panel.appendChild(inner);
    group.appendChild(panel);

    // the head becomes a real control, keeping the rule that was already in it
    var label = head.querySelector("span");
    var count = document.createElement("span");
    count.className = "p-gal__count";
    count.textContent = shots.length;
    var chev = document.createElement("span");
    chev.className = "p-gal__chev";
    chev.setAttribute("aria-hidden", "true");
    head.appendChild(count);
    head.appendChild(chev);
    head.setAttribute("role", "button");
    head.setAttribute("tabindex", "0");
    head.setAttribute("aria-controls", panel.id);

    // THE FIRST ROOM IS OPEN. A gallery that is entirely shut on arrival asks
    // somebody to guess what is behind it; one room open says what the rest are.
    var open = gi === 0;
    function set(v) {
      open = v;
      head.setAttribute("aria-expanded", String(open));
      if (open) panel.setAttribute("data-on", ""); else panel.removeAttribute("data-on");
    }
    set(open);
    head.addEventListener("click", function () { set(!open); });
    head.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); set(!open); }
    });
  });

  if (!all.length) return;

  /* ---- the viewer -------------------------------------------------------- */
  var lb = document.createElement("div");
  lb.className = "p-lb";
  lb.hidden = true;
  lb.setAttribute("role", "dialog");
  lb.setAttribute("aria-modal", "true");
  lb.setAttribute("aria-label", "Gallery");
  lb.innerHTML =
    '<img class="p-lb__img" alt="">' +
    '<p class="p-lb__cap"></p>' +
    '<button class="p-lb__x" type="button" aria-label="Close">' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1 1l10 10M11 1L1 11"/></svg></button>' +
    '<button class="p-lb__btn p-lb__prev" type="button" aria-label="Previous">' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M8 1L3 6l5 5"/></svg></button>' +
    '<button class="p-lb__btn p-lb__next" type="button" aria-label="Next">' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4 1l5 5-5 5"/></svg></button>';
  document.body.appendChild(lb);

  var img  = lb.querySelector(".p-lb__img");
  var cap  = lb.querySelector(".p-lb__cap");
  var at   = 0;
  var from = null;

  function go(i) {
    at = (i % all.length + all.length) % all.length;
    img.src = all[at].href;
    img.alt = all[at].alt;
    cap.innerHTML = all[at].alt
      ? all[at].alt + '<span class="p-lb__n">' + (at + 1) + " of " + all.length + "</span>"
      : '<span class="p-lb__n">' + (at + 1) + " of " + all.length + "</span>";
    // keep the next one warm so a click does not wait on the network
    var n = new Image(); n.src = all[(at + 1) % all.length].href;
  }

  function openAt(i) {
    from = document.activeElement;
    go(i);
    lb.hidden = false;
    document.documentElement.style.overflow = "hidden";
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { lb.setAttribute("data-on", ""); });
    });
    lb.querySelector(".p-lb__x").focus({ preventScroll: true });
    document.addEventListener("keydown", onKey, true);
  }

  function close() {
    lb.removeAttribute("data-on");
    document.documentElement.style.overflow = "";
    document.removeEventListener("keydown", onKey, true);
    var done = function () { lb.hidden = true; img.removeAttribute("src"); };
    if (less.matches) done(); else setTimeout(done, 420);
    if (from && from.focus) from.focus({ preventScroll: true });
  }

  function onKey(e) {
    if (e.key === "Escape")     { e.preventDefault(); close(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(at + 1); }
    else if (e.key === "ArrowLeft")  { e.preventDefault(); go(at - 1); }
    else if (e.key === "Tab") {
      // three controls, and Tab stays among them
      var able = lb.querySelectorAll("button");
      var first = able[0], last = able[able.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  sheet.addEventListener("click", function (e) {
    var a = e.target.closest(".p-shot");
    if (!a || !a.dataset.i) { if (a) openAt(0); else return; }
    if (a) { e.preventDefault(); openAt(+a.dataset.i); }
  });

  lb.addEventListener("click", function (e) {
    if (e.target.closest(".p-lb__x")) return close();
    if (e.target.closest(".p-lb__prev")) return go(at - 1);
    if (e.target.closest(".p-lb__next")) return go(at + 1);
    if (e.target === lb) close();                 // the ground, not the picture
  });

  /* a swipe on a phone, without a library */
  var x0 = null;
  lb.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 48) go(at + (dx < 0 ? 1 : -1));
    x0 = null;
  }, { passive: true });
})();
