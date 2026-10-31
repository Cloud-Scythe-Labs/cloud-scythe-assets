// Nocturne: review chrome, glide scroll, tour, back to top, scroll reveal, fog, embedded screens.
// Switch groups read ?<key>=, then localStorage, then the default, and set data-<key> on <html>.
const GROUPS = [
  { key: "theme", label: "THEME", values: ["ps2", "ps1", "ps5"] },
];
const root = document.documentElement;
const params = new URLSearchParams(location.search);
const embedded = params.has("embed");   // page shown inside another page's .n-screen
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
if (embedded) root.dataset.embed = "";

// ── Review bar ────────────────────────────────────────────────────────────────
const bar = document.createElement("nav");
bar.className = "n-review";
bar.setAttribute("aria-label", "Review options");
const toggle = document.createElement("button");
toggle.type = "button";
toggle.textContent = "REVIEW";
toggle.addEventListener("click", () => setOpen(bar.dataset.open !== "true"));
bar.append(toggle);
function setOpen(open) {
  bar.dataset.open = String(open);
  toggle.setAttribute("aria-expanded", String(open));
  localStorage.setItem("n-review-open", String(open));
}
setOpen(localStorage.getItem("n-review-open") !== "false");

for (const group of GROUPS) {
  const row = document.createElement("div");
  row.setAttribute("role", "group");
  row.setAttribute("aria-label", group.label);
  const label = document.createElement("span");
  label.textContent = group.label;
  row.append(label);
  const buttons = group.values.map((value) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = value.toUpperCase();
    b.addEventListener("click", () => apply(value));
    row.append(b);
    return b;
  });
  function apply(value) {
    root.dataset[group.key] = value;
    if (!embedded) localStorage.setItem(`n-${group.key}`, value);
    buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(group.values[i] === value)));
    // Keep embedded screens on the same setting.
    document.querySelectorAll(".n-screen iframe").forEach((f) => {
      const doc = f.contentDocument;
      if (doc) doc.documentElement.dataset[group.key] = value;
    });
  }
  const pick = [params.get(group.key), localStorage.getItem(`n-${group.key}`)].find((v) => group.values.includes(v));
  apply(pick ?? group.values[0]);
  bar.append(row);
}

// ── Glide scroll ──────────────────────────────────────────────────────────────
// The browser's smooth scroll is quick and not tunable. Glide moves at a calm cruising speed
// with a sine ease, so it never whips through the middle of a long trip.
const GLIDE_SPEED = 820;        // px per second, average over the trip
const GLIDE_MIN = 900;          // ms, short hops still drift in
const GLIDE_MAX = 3600;         // ms, long trips don't drag
let glideRun = 0;

// Resolves true when it arrives, false if cancelled by the user or another glide.
function glideTo(targetY) {
  const max = document.documentElement.scrollHeight - innerHeight;
  const endY = Math.max(0, Math.min(targetY, max));
  const startY = scrollY;
  const dist = endY - startY;
  const run = ++glideRun;
  if (reduceMotion.matches || Math.abs(dist) < 2) {
    scrollTo(0, endY);
    return Promise.resolve(true);
  }
  // Average speed = GLIDE_SPEED; the sine ease peaks at π/2 × that (≈ 1290 px/s), never a whip.
  const time = Math.min(Math.max((Math.abs(dist) / GLIDE_SPEED) * 1000, GLIDE_MIN), GLIDE_MAX);
  const ease = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
  const t0 = performance.now();
  return new Promise((resolve) => {
    const step = (now) => {
      if (run !== glideRun) return resolve(false);
      const t = Math.min((now - t0) / time, 1);
      scrollTo(0, startY + dist * ease(t));
      if (t < 1) requestAnimationFrame(step);
      else resolve(true);
    };
    requestAnimationFrame(step);
  });
}
function cancelGlide() { glideRun++; }

function elementY(el) {
  const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
  return el.getBoundingClientRect().top + scrollY - margin;
}
function glideToElement(el) {
  if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
  el.focus({ preventScroll: true });
  return glideTo(elementY(el));
}
// Tour framing: land each stop with its heading just under the sticky header — the same place
// an in-page link lands (scroll-margin-top) — clamped to what the page can actually scroll to.
function stopY(el) {
  const max = document.documentElement.scrollHeight - innerHeight;
  return Math.max(0, Math.min(elementY(el), max));
}
// Stops whose landing spot matches the previous one (e.g. the footer when the page has already
// hit bottom) would be a dead stop; drop them so every stop moves.
function tourStops() {
  const stops = [];
  let last = -Infinity;
  for (const el of document.querySelectorAll("[data-stop]")) {
    const y = stopY(el);
    if (y - last < 48) continue;
    stops.push(el);
    last = y;
  }
  return stops;
}

// ── Tour ──────────────────────────────────────────────────────────────────────
// Glides through every [data-stop] in document order, dwelling on each, and ends on the last one.
// New sections join the tour by adding data-stop. Any user input ends it early.
const TOUR_DWELL = 3800;        // ms on each stop
let tour = null;                // { stops, ui }

function tourUI() {
  const el = document.createElement("div");
  el.className = "n-tourbar";
  el.setAttribute("role", "status");
  el.innerHTML = '<span class="n-status s-progress n-status--live">TOUR</span>'
    + '<span class="n-tourbar__count"></span>'
    + '<span class="n-tourbar__dwell" aria-hidden="true"><i></i></span>'
    + '<button type="button" class="n-tourbar__stop">STOP <span aria-hidden="true">■</span></button>';
  el.querySelector("button").addEventListener("click", stopTour);
  document.body.append(el);
  requestAnimationFrame(() => el.classList.add("is-shown"));
  return el;
}

function wait(ms, run) {
  return new Promise((resolve) => {
    const t0 = performance.now();
    const tick = (now) => {
      if (run !== glideRun) return resolve(false);
      if (now - t0 >= ms) return resolve(true);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

async function startTour() {
  const stops = tourStops();
  if (!stops.length || tour) return;
  tour = { stops, ui: tourUI() };
  document.querySelectorAll("[data-tour-toggle]").forEach((b) => b.setAttribute("aria-pressed", "true"));
  const count = tour.ui.querySelector(".n-tourbar__count");
  const dwell = tour.ui.querySelector(".n-tourbar__dwell i");
  // Start at the next stop below the current view, so the first move happens right away.
  // Already past the last stop? Start over from the top.
  let i = stops.findIndex((s) => stopY(s) > scrollY + 4);
  if (i < 0) i = 0;
  for (; i < stops.length; i++) {
    if (!tour) return;
    count.textContent = `${String(i + 1).padStart(2, "0")} / ${String(stops.length).padStart(2, "0")}`;
    dwell.style.transition = "none";
    dwell.style.width = "0";
    const arrived = await glideTo(stopY(stops[i]));
    if (!arrived || !tour) return stopTour();
    if (i === stops.length - 1) break;      // arrived at the end: the tour is over
    const run = glideRun;
    requestAnimationFrame(() => {
      dwell.style.transition = `width ${TOUR_DWELL}ms linear`;
      dwell.style.width = "100%";
    });
    if (!(await wait(TOUR_DWELL, run))) return stopTour();
  }
  stopTour();
}

function stopTour() {
  if (!tour) return;
  const { ui } = tour;
  tour = null;
  cancelGlide();
  document.querySelectorAll("[data-tour-toggle]").forEach((b) => b.setAttribute("aria-pressed", "false"));
  ui.classList.remove("is-shown");
  setTimeout(() => ui.remove(), 400);
}

// Manual input takes control back: cancels a glide and ends the tour.
const userTakesOver = (e) => {
  if (e.target.closest?.("[data-tour-toggle], .n-tourbar, .n-review")) return;
  cancelGlide();
  stopTour();
};
addEventListener("wheel", userTakesOver, { passive: true });
addEventListener("touchstart", userTakesOver, { passive: true });
addEventListener("keydown", userTakesOver);
addEventListener("pointerdown", userTakesOver);

document.addEventListener("click", (e) => {
  const toggleBtn = e.target.closest("[data-tour-toggle]");
  if (toggleBtn) {
    tour ? stopTour() : startTour();
    return;
  }
  const a = e.target.closest('a[href^="#"]');
  if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
  const id = decodeURIComponent(a.getAttribute("href").slice(1));
  if (id === "" || id === "top") {
    e.preventDefault();
    glideTo(0);
    history.replaceState(null, "", location.pathname + location.search);
    return;
  }
  const target = document.getElementById(id);
  if (!target) return;
  e.preventDefault();
  glideToElement(target);
  history.replaceState(null, "", `#${id}`);
});

// ── Page setup ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (!embedded) document.body.append(bar);

  // Fog banks: separate layers so they animate on the compositor (see .n-fog in nocturne.css).
  document.querySelectorAll(".n-atmos").forEach((atmos) => {
    if (atmos.querySelector(".n-fog")) return;
    for (const k of ["a", "b", "c"]) {
      const fog = document.createElement("i");
      fog.className = `n-fog n-fog-${k}`;
      atmos.append(fog);
    }
  });

  // Back to top: appears after one screen of scrolling; its bottom edge shows page progress.
  const scrollable = document.documentElement.scrollHeight > innerHeight * 1.5;
  if (!embedded && scrollable) {
    const top = document.createElement("button");
    top.type = "button";
    top.className = "n-top";
    top.setAttribute("aria-label", "Back to top");
    top.innerHTML = 'TOP <span class="n-arrow" aria-hidden="true">↑</span>';
    top.addEventListener("click", () => {
      glideTo(0);
      document.querySelector("a, button")?.focus({ preventScroll: true });
    });
    document.body.append(top);
    let queued = false;
    const update = () => {
      queued = false;
      const max = document.documentElement.scrollHeight - innerHeight;
      top.style.setProperty("--p", String(max > 0 ? scrollY / max : 0));
      top.classList.toggle("is-shown", scrollY > innerHeight * 0.9);
    };
    addEventListener("scroll", () => {
      if (!queued) { queued = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  // Embedded screens: scale the 1440×900 page to the frame and sync settings once loaded.
  const screens = document.querySelectorAll(".n-screen");
  const ro = new ResizeObserver((entries) => {
    for (const e of entries) e.target.style.setProperty("--scale", String(e.contentRect.width / 1440));
  });
  screens.forEach((s) => {
    ro.observe(s);
    const f = s.querySelector("iframe");
    f?.addEventListener("load", () => {
      for (const g of GROUPS) f.contentDocument.documentElement.dataset[g.key] = root.dataset[g.key];
    });
  });

  // Scroll reveal.
  const items = document.querySelectorAll("[data-reveal]");
  if (!("IntersectionObserver" in window) || params.has("static")) {
    items.forEach((el) => el.classList.add("is-in"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      }
    }
  }, { rootMargin: "0px 0px -8% 0px" });
  items.forEach((el) => io.observe(el));
});
