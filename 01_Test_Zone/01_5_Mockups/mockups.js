// Review chrome: switches for the theme and for undecided surface treatments.
// Each group reads ?<group>=, then localStorage, then its default, and sets data-<group> on <html>.
const GROUPS = [
  { key: "theme", label: "THEME", values: ["ps2", "ps1", "ps5"] },
  { key: "panel", label: "PANEL", values: ["141414", "1c1c1c"] },
  { key: "radius", label: "RADIUS", values: ["10", "6"] },
  { key: "edge", label: "EDGE", values: ["none", "hairline"] },
];
const root = document.documentElement;
const params = new URLSearchParams(location.search);

const bar = document.createElement("nav");
bar.className = "review-bar";
bar.setAttribute("aria-label", "Review options");

// Collapsible so the bar never hides content while reviewing; state persists across pages.
const toggle = document.createElement("button");
toggle.type = "button";
toggle.className = "review-bar__toggle";
toggle.textContent = "REVIEW";
toggle.addEventListener("click", () => setOpen(bar.dataset.open !== "true"));
bar.append(toggle);

function setOpen(open) {
  bar.dataset.open = String(open);
  toggle.setAttribute("aria-expanded", String(open));
  localStorage.setItem("csl-review-open", String(open));
}
setOpen(localStorage.getItem("csl-review-open") !== "false");

for (const group of GROUPS) {
  const wrap = document.createElement("div");
  wrap.className = "review-bar__group";
  wrap.setAttribute("role", "group");
  wrap.setAttribute("aria-label", group.label);
  const label = document.createElement("span");
  label.textContent = group.label;
  wrap.append(label);

  const buttons = group.values.map((value) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = value.toUpperCase();
    b.addEventListener("click", () => apply(value));
    wrap.append(b);
    return b;
  });

  function apply(value) {
    root.dataset[group.key] = value;
    localStorage.setItem(`csl-${group.key}`, value);
    buttons.forEach((b, i) => b.setAttribute("aria-pressed", String(group.values[i] === value)));
  }

  const candidates = [params.get(group.key), localStorage.getItem(`csl-${group.key}`)];
  apply(candidates.find((v) => group.values.includes(v)) ?? group.values[0]);
  bar.append(wrap);
}

document.addEventListener("DOMContentLoaded", () => document.body.append(bar));
