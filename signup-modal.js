/* ===========================================================================
   EDEN GROVE — THE EMAIL INVITATION

   Asks once, quietly, after fifteen seconds of someone actually being here.

   One file, no dependencies. It writes its own styles and its own markup, so
   adding it to a page is a single script tag and removing it is deleting one.
   It posts to the same Worker the contact page and the 715 Davis sign-up use,
   which is origin locked, throttled, and already strips the honeypot.

   WHAT IT WILL NOT DO
     - fire while the tab is in the background. Fifteen seconds means fifteen
       seconds of the page being looked at, not fifteen seconds of it being
       open behind something else.
     - interrupt someone mid sentence. If a field anywhere on the page has
       focus when the timer is up, it waits until they are done.
     - ask twice. Thirty days after a dismissal, never again after a sign-up.
     - run at all for somebody who has asked for less motion and is on a page
       where the entrance would be the only thing moving: it still opens, it
       just does not animate.

   Storage can throw: private windows, blocked site data, a browser that has
   decided today is the day. Every read and write is wrapped, and the fallback
   is a variable that lasts the session, so the worst case is one ask per tab
   rather than a broken page.
   ======================================================================== */
(function () {
  "use strict";

  var DELAY_MS    = 15000;                               // visible time, not wall clock
  var SNOOZE_DAYS = 30;                                  // after a dismissal
  var KEY         = "eg.sub.v1";
  var ENDPOINT    = "https://dashboard.edengrovetennessee.com/__contact";

  /* ---- storage, defensively ---------------------------------------------- */
  var memory = null;                                     // the fallback when storage is gone
  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || "null") || memory; }
    catch (e) { return memory; }
  }
  function write(state) {
    memory = state;
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  var saved = read();
  if (saved) {
    if (saved.joined) return;                            // they are on the list already
    if (saved.until && Date.now() < saved.until) return; // dismissed, still inside the snooze
  }

  /* ---- the styles -------------------------------------------------------- */
  var css = [
    '.eg-sub{position:fixed;inset:0;z-index:9000;display:grid;place-items:center;',
      'padding:clamp(1.25rem,4vw,2.5rem);}',
    '.eg-sub[hidden]{display:none}',
    '.eg-sub__veil{position:absolute;inset:0;background:rgba(8,10,7,.42);',
      'opacity:0;transition:opacity .6s cubic-bezier(.22,.61,.36,1)}',
    '.eg-sub[data-on] .eg-sub__veil{opacity:1}',

    /* GLASS. The ground is translucent and the backdrop behind it is blurred,
       so the photograph the page is already showing becomes the card's
       material rather than being hidden by it. The hairline is brighter than
       the site's usual .12 because an edge is the only thing that tells you
       a pane of glass is there, and the inset highlight is the lit top lip
       of that pane. */
    '.eg-sub__card{position:relative;width:min(31rem,100%);box-sizing:border-box;',
      'background:rgba(20,23,15,.58);',
      '-webkit-backdrop-filter:blur(26px) saturate(135%);',
      'backdrop-filter:blur(26px) saturate(135%);',
      'border:1px solid rgba(244,241,236,.17);',
      'box-shadow:0 30px 80px rgba(0,0,0,.42),inset 0 1px 0 rgba(244,241,236,.10);',
      'padding:clamp(2.4rem,5vw,3.4rem) clamp(1.8rem,4vw,3rem) clamp(2rem,4vw,2.6rem);',
      'text-align:left;opacity:0;transform:translateY(14px);',
      'transition:opacity .7s cubic-bezier(.22,.61,.36,1),transform .7s cubic-bezier(.22,.61,.36,1)}',
    /* Without backdrop-filter there is no glass to be had, so it falls back
       to the solid panel every other framed thing on the site uses. */
    '@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){',
      '.eg-sub__card{background:#1B1F19}',
    '}',
    '.eg-sub[data-on] .eg-sub__card{opacity:1;transform:none}',

    /* The way out. Forty four square of target around a mark half that size. */
    '.eg-sub__x{position:absolute;top:.5rem;right:.5rem;width:2.75rem;height:2.75rem;',
      'display:grid;place-items:center;background:none;border:0;cursor:pointer;',
      'color:var(--t3,rgba(244,241,236,.45));transition:color .4s cubic-bezier(.22,.61,.36,1)}',
    '.eg-sub__x:hover,.eg-sub__x:focus-visible{color:var(--t1,#F4F1EC);outline:none}',
    '.eg-sub__x:focus-visible{box-shadow:0 0 0 1px var(--brass,#DACEB6)}',
    '.eg-sub__x svg{width:.72rem;height:.72rem;stroke:currentColor;stroke-width:1.2;fill:none}',

    '.eg-sub__eyebrow{margin:0;font-family:var(--ui,"Jost",Arial,sans-serif);font-weight:400;',
      'font-size:.6rem;letter-spacing:.3em;text-indent:.3em;text-transform:uppercase;',
      'color:var(--brass,#DACEB6)}',

    /* Cormorant for the one line that is allowed to be large. */
    '.eg-sub__h{margin:1.4rem 0 0;font-family:var(--display,"Cormorant Garamond",Georgia,serif);',
      'font-weight:300;font-size:clamp(1.9rem,1.3rem + 2.2vw,2.6rem);line-height:1.18;',
      'letter-spacing:.005em;color:var(--t1,#F4F1EC)}',
    '.eg-sub__h i{font-style:normal;display:block}',

    '.eg-sub__p{margin:1.1rem 0 0;font-family:var(--ui,"Jost",Arial,sans-serif);font-weight:300;',
      'font-size:.86rem;line-height:1.85;color:var(--t2,rgba(244,241,236,.72))}',

    '.eg-sub__rule{width:2.6rem;height:1px;background:var(--brass,#DACEB6);margin:1.6rem 0 0}',

    '.eg-sub__form{display:flex;flex-wrap:wrap;gap:.9rem;align-items:flex-end;margin:1.5rem 0 0}',
    '.eg-sub__form input[type=email]{flex:1 1 13rem;min-width:0;background:none;border:0;',
      'border-bottom:1px solid rgba(244,241,236,.22);color:#fff;',
      'font-family:var(--ui,"Jost",Arial,sans-serif);font-weight:300;font-size:.92rem;',
      'padding:.7rem .15rem;transition:border-color .4s cubic-bezier(.22,.61,.36,1)}',
    '.eg-sub__form input[type=email]::placeholder{color:var(--t3,rgba(244,241,236,.45))}',
    '.eg-sub__form input[type=email]:focus{outline:none;border-bottom-color:var(--brass,#DACEB6)}',
    '.eg-sub__form button{flex:0 0 auto;background:none;cursor:pointer;',
      'border:1px solid var(--t2,rgba(244,241,236,.72));color:var(--t1,#F4F1EC);',
      'font-family:var(--ui,"Jost",Arial,sans-serif);font-weight:400;font-size:.62rem;',
      'letter-spacing:.24em;text-indent:.24em;text-transform:uppercase;padding:.85rem 1.7rem;',
      'transition:background-color .4s cubic-bezier(.22,.61,.36,1),',
      'border-color .4s cubic-bezier(.22,.61,.36,1),color .4s cubic-bezier(.22,.61,.36,1)}',
    '.eg-sub__form button:hover:not(:disabled),.eg-sub__form button:focus-visible{',
      'background:var(--t1,#F4F1EC);border-color:var(--t1,#F4F1EC);color:#14170F;outline:none}',
    '.eg-sub__form button:disabled{opacity:.55;cursor:default}',

    '.eg-sub__note{margin:1rem 0 0;min-height:1.2em;font-family:var(--ui,"Jost",Arial,sans-serif);',
      'font-weight:300;font-size:.78rem;line-height:1.7;color:var(--t1,#F4F1EC);',
      'opacity:0;transition:opacity .4s cubic-bezier(.22,.61,.36,1)}',
    '.eg-sub__note[data-on]{opacity:1}',

    '.eg-sub__terms{margin:1.1rem 0 0;font-family:var(--ui,"Jost",Arial,sans-serif);font-weight:300;',
      'font-size:.7rem;line-height:1.8;color:var(--warm,#A7947C)}',
    '.eg-sub__terms a{color:inherit}',

    /* The honeypot, and the label the screen reader needs but nobody sees. */
    '.eg-sub__hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}',
    '.eg-sub__sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;',
      'clip:rect(0 0 0 0);white-space:nowrap;border:0}',

    /* On a phone it sits against the bottom, which is where a thumb is. */
    '@media (max-width:560px){',
      '.eg-sub{place-items:end center;padding:0}',
      '.eg-sub__card{width:100%;border-left:0;border-right:0;border-bottom:0;',
        'padding-bottom:calc(1.8rem + env(safe-area-inset-bottom,0px));',
        'transform:translateY(28px)}',
    '}',
    '@media (prefers-reduced-motion:reduce){',
      '.eg-sub__veil,.eg-sub__card,.eg-sub__note{transition:none}',
      '.eg-sub__card{transform:none}',
    '}'
  ].join("");

  /* ---- the markup -------------------------------------------------------- */
  var html =
    '<div class="eg-sub__veil" data-close></div>' +
    '<div class="eg-sub__card" role="dialog" aria-modal="true"' +
        ' aria-labelledby="eg-sub-h" aria-describedby="eg-sub-p">' +
      '<button class="eg-sub__x" type="button" aria-label="Close" data-close>' +
        '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1 1l10 10M11 1L1 11"/></svg>' +
      '</button>' +
      '<p class="eg-sub__eyebrow">By Email</p>' +
      '<h2 class="eg-sub__h" id="eg-sub-h"><i>One email,</i><i>once a week.</i></h2>' +
      '<p class="eg-sub__p" id="eg-sub-p">New listings, Private Exclusives and the builds in ' +
        'progress, sent as each one goes out. Nothing else.</p>' +
      '<div class="eg-sub__rule"></div>' +
      '<form class="eg-sub__form" novalidate>' +
        '<label class="eg-sub__sr" for="eg-sub-email">Email address</label>' +
        '<input id="eg-sub-email" name="email" type="email" placeholder="Enter your email"' +
              ' autocomplete="email" required>' +
        '<div class="eg-sub__hp" aria-hidden="true">' +
          '<label for="eg-sub-site">Website</label>' +
          '<input id="eg-sub-site" name="website" type="text" tabindex="-1" autocomplete="off">' +
        '</div>' +
        '<button type="submit">Follow</button>' +
      '</form>' +
      '<p class="eg-sub__note" role="status"></p>' +
      '<p class="eg-sub__terms">We will use it for these updates and nothing else. ' +
        'See our <a href="privacy.html">Privacy Policy</a> and <a href="terms.html">Terms</a>.</p>' +
    '</div>';

  /* ---- build it, but do not show it -------------------------------------- */
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var root = document.createElement("div");
  root.className = "eg-sub";
  root.hidden = true;
  root.innerHTML = html;
  document.body.appendChild(root);

  var card   = root.querySelector(".eg-sub__card");
  var form   = root.querySelector(".eg-sub__form");
  var email  = root.querySelector("#eg-sub-email");
  var button = form.querySelector("button");
  var note   = root.querySelector(".eg-sub__note");
  var opener = null;
  var open   = false;

  function say(msg) { note.textContent = msg; note.setAttribute("data-on", ""); }

  /* ---- opening and closing ----------------------------------------------- */
  function show() {
    if (open) return;
    open = true;
    opener = document.activeElement;
    root.hidden = false;
    document.documentElement.style.overflow = "hidden";
    // a frame, so the transition has a start state to move from
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { root.setAttribute("data-on", ""); });
    });
    email.focus({ preventScroll: true });
    document.addEventListener("keydown", onKey, true);
  }

  function hide(remember) {
    if (!open) return;
    open = false;
    root.removeAttribute("data-on");
    document.documentElement.style.overflow = "";
    document.removeEventListener("keydown", onKey, true);
    if (remember) write({ until: Date.now() + SNOOZE_DAYS * 864e5 });
    var done = function () { root.hidden = true; };
    // wait out the fade unless motion is off, in which case there is none
    if (matchMedia("(prefers-reduced-motion:reduce)").matches) done();
    else setTimeout(done, 650);
    if (opener && opener.focus) opener.focus({ preventScroll: true });
  }

  root.addEventListener("click", function (e) {
    if (e.target.closest("[data-close]")) hide(true);
  });

  /* Escape closes it, and Tab cannot leave it while it is open. */
  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); hide(true); return; }
    if (e.key !== "Tab") return;
    var able = card.querySelectorAll('a[href],button:not(:disabled),input:not([tabindex="-1"])');
    if (!able.length) return;
    var first = able[0], last = able[able.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* ---- the fifteen seconds ----------------------------------------------- */
  var spent = 0, since = null;

  function resume() { if (since === null) since = Date.now(); }
  function pause()  { if (since !== null) { spent += Date.now() - since; since = null; } }

  function elapsed() { return spent + (since === null ? 0 : Date.now() - since); }

  function tick() {
    if (open) return;
    if (document.hidden) { pause(); return; }
    resume();
    if (elapsed() < DELAY_MS) return;

    // somebody is typing somewhere else on the page: wait for them to finish
    var busy = document.activeElement;
    if (busy && /^(INPUT|TEXTAREA|SELECT)$/.test(busy.tagName) && !card.contains(busy)) return;

    clearInterval(timer);
    show();
  }

  var timer = setInterval(tick, 500);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) pause(); else resume();
  });
  resume();

  /* ---- the sign-up ------------------------------------------------------- */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var data = {};
    new FormData(form).forEach(function (v, k) { data[k] = v; });
    var address = String(data.email || "").trim();
    if (!address || address.indexOf("@") < 1) { say("Please add an email address."); return; }

    data.name    = "Website sign-up";
    data.topic   = "Weekly email";
    data.message = "Sign-up from the website invitation on " + location.pathname + ".";

    var was = button.textContent;
    button.disabled = true;
    button.textContent = "Sending";
    say("Sending…");

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(function (res) { return res.json().catch(function () { return {}; })
        .then(function (out) { return { ok: res.ok && out.ok, out: out }; }); })
      .then(function (r) {
        if (r.ok) {
          write({ joined: true });                       // never ask this person again
          form.reset();
          button.textContent = "Done";
          say("You are on the list. The next one comes to you.");
          setTimeout(function () { hide(false); }, 2200);
          return;
        }
        button.disabled = false;
        button.textContent = was;
        say((r.out && r.out.error) || "That did not go through. Please email " +
            "connect@edengrovetennessee.com and we will add you.");
      })
      .catch(function () {
        button.disabled = false;
        button.textContent = was;
        say("That did not go through. You may be offline, or you can email " +
            "connect@edengrovetennessee.com and we will add you.");
      });
  });
})();
