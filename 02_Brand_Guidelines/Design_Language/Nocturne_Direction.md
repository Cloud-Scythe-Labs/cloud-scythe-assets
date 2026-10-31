# Nocturne — proposed direction (round 3)

Status: **proposal for review.** If accepted it replaces the color, surface, status and layout rules in `CSL_Design_Language.md` §2 and §5 and the PDF's equivalents. Brand marks, fonts, the ticker and the type roles stay as they are.

Mockups: `01_Test_Zone/01_5_Mockups/nocturne/` (`home.html`, `app.html`, `system.html`). Implementation: `nocturne/nocturne.css`. Round-2 screenshots for comparison: `01_Test_Zone/01_5_Mockups/_archive/round2/`.

## Why

Feedback on round 2: too playful. Target feel: **fast, dark, intimidating, ethereal, exciting** — the PS2 era (boot screen, memory-card menu, fog, cold light).

What made round 2 playful, and the fix:

| Round 2 (v1.0.2 rules) | Effect | Nocturne |
|---|---|---|
| Saturated pastel status colors (chroma ≈ 0.16–0.20) as filled pills | Toy-like, candy | Muted hues (chroma ≈ 0.08), shown as a lit 8px square with a faint glow beside a label; color fill only on destructive confirm |
| Everything inside rounded 10px boxes, uniform card grids | Clunky, "widget" layout | Hairline structure, asymmetric 12-column grid, generous void; a container only where content needs one |
| Neutral grays, flat black | Static, generic | Cold-tinted near-blacks, one luminous accent (ether blue), drifting fog, film grain, faint scanlines |
| 10px rounded corners | Soft, friendly | 2px corners: straight edges read as speed and precision |
| Equal-weight buttons, chips everywhere | Busy | One primary per region, tertiary text links with arrows, HUD micro-labels carry structure |
| No motion beyond the ticker | Inert | Snap-in / drift-out easing, speed-sweep hovers, blur-to-sharp reveals, live status pulse |

## Palette

Neutrals carry a faint cold tint (OKLCH hue ≈ 268, chroma ≤ 0.02).

| Token | PS2 (default) | PS1 "fog" | PS5 "white-out" | Role |
|---|---|---|---|---|
| `--void` | `#000000` | `#1B1E25` | `#DFE2E9` | Page |
| `--abyss` | `#07080B` | `#20242C` | `#E6E9EF` | Full-bleed bands |
| `--surface` | `#0D0F14` | `#272B35` | `#ECEEF3` | Panels, code |
| `--raise` | `#141720` | `#30353F` | `#F4F5F8` | Hover, selected rows |
| `--line` | `#262B38` | `#3B414E` | `#C9CDD6` | Hairlines (decorative) |
| `--line-strong` | `#5D667D` | `#7A8297` | `#727A8C` | Form-control boundaries (≥ 3:1) |
| `--fg` | `#E3E6EC` | `#E3E6EC` | `#07080B` | Text, marks |
| `--fg-dim` | `#9097A6` | `#A3A9B6` | `#4B5262` | Secondary text |
| `--fg-faint` | `#4A5060` | `#555C6C` | `#B4B9C4` | Decorative type only |
| `--ether` | `#B4C4FF` | `#C3D0FF` | `#3C55C8` | Focus, active, glow source, HUD indices |
| `--fog` | `#2B3A7A` | `#3D4A80` | `#FFFFFF` | Atmosphere gradients |

Measured on each theme's `--surface`: `--fg` 11.3–17.3:1, `--fg-dim` 6.0–6.7:1, `--ether` 5.4–11.2:1, `--line-strong` 3.3–3.7:1. This **lifts the v1.0.2 ban on secondary text**: `--fg-dim` passes AA in every theme and gives the hierarchy that the two-color rule couldn't.

### Status (muted)

| Meaning | Dark context | v1.0.2 dark | Light context (PS5) | v1.0.2 light |
|---|---|---|---|---|
| Critical — red | `#D8625C` | `#EF4B46` | `#A43B38` | `#E03631` |
| Warning — orange | `#D59466` | `#F5863D` | `#9D5C36` | `#EA642D` |
| Caution — yellow | `#D7CC8B` | `#F4E854` | `#807636` | `#D3C439` |
| Success — green | `#78BFA6` | `#0ED6A2` | `#35775D` | `#0FBD7D` |
| Neutral — blue | `#79A6D1` | `#63A7E8` | `#416593` | `#4784D8` |
| Progress — purple | `#9F84BF` | `#BE63E3` | `#6B4E8B` | `#A046D2` |
| Notify — pink | `#CD94B3` | `#EA78C8` | `#8D5375` | `#D956AD` |

Status hues against each theme's `--surface`: PS2 5.3–11.8:1, PS1 4.5–9.2:1, PS5 4.0–5.9:1 — all clear the 3:1 non-text minimum, most clear 4.5:1. Red keeps more chroma so critical still cuts through. This fixes v1.0.2's sub-3:1 light-context yellow, green, orange and pink (OPEN-3). Text on a PS5 status fill is Faded White (3.7–5.5:1; in practice only the destructive button, red at 5.2:1).

## Shape, structure, type

- Corner radius 2px everywhere (`--r`). No blobs.
- Structure from hairlines (`--line`), spacing and the grid, not from boxes. Translucent `.n-panel` (blurred, top hairline) only when a container is needed.
- HUD micro-labels: 10px CSL Mono (1 device px per font pixel), uppercase, `--fg-dim`, with an index in `--ether` (`01`, `P.02`). They replace eyebrows, chips and most section titles.
- Titles: huge one-line Display (132–176px) or Mono when they wrap. Body JetBrains Mono at 15px in `--fg-dim`; `--fg` only for emphasis.
- Status: `.n-status` (lit square + label) and `.n-meter` (2px bar with glow).

### Brand composition

The shipped CSL Lockup2 puts the emblem only ~10% of the emblem's height away from the logotype — narrower than the logotype's own word space — so it reads cramped at header sizes. Nocturne composes the emblem (`Rectangle_NoPadding`) and `Logotype2` from their separate files (`.n-brand`), keeping the shipped size relationship but opening the gap:

| Brand | Logotype height | Gap | Shipped lockup gap |
|---|---|---|---|
| CSL | 0.36 × emblem height (text = ring height, as shipped) | 0.42 × emblem height | ≈ 0.10 × |
| ReaCloud | 0.62 × emblem height | 0.50 × emblem height | ≈ 0.22 × |

Header: CSL emblem 48px tall (32px on phones). [PROPOSED — re-export the lockup SVGs with this spacing once approved]

### Hero emblem

The hero emblem is atmosphere, not a logo use: Duo2 ring in `--ether` at ~30% opacity, blade in `--fg` at ~14%, cropped top, right and bottom so it feels close, larger than the screen (`.n-bleed`). Size: `clamp(900px, min(150vh, 95vw), 2400px)`. Crop: 36% of the emblem's **own** width sits past the right edge at every window size (offset by `translate`, not by a percentage of the page), so fullscreen and small windows show the same crop. Phones: 160vw wide, half off-screen.

## Motion

- Easing `cubic-bezier(.16, 1, .3, 1)` (fast attack, long settle); 120 / 320 / 900 ms.
- Buttons: a fill sweeps in from the left on hover; arrows nudge 6px.
- Reveal: fade + 16px rise + 6px blur → sharp, staggered 60ms.
- Atmosphere: three fog banks drift on independent 29 / 37 / 53 s cycles and breathe on an 11 s pulse (density 100% → 55%), so the page never looks static. Each bank is its own layer moved only by `transform` and `opacity`, so the GPU animates it without repainting the page. Grain at 0.6 s steps; static scanlines. PS5 uses a cold blue haze (`#8EA0EC`) so the light theme has atmosphere too.
- Emblem materialises from blur, then floats (23 s) while the ring breathes (11 s, opacity only).
- **Performance rule:** never animate `filter` (glow, blur, drop-shadow) on large elements. Animating the hero ring's glow repainted a ~1400px layer every frame and halved the scroll frame rate (measured 31 ms → 17 ms per frame once removed). Glows stay static; motion uses `transform` and `opacity`.
- **Ticker kept as is** (rotated rows, Forza-like); slowed to a set speed and placed in a full-bleed abyss band.
- **Glide:** in-page links, the SCROLL ↓ cue and back-to-top glide on a sine ease at an average 820 px/s (peak ≈ 1290 px/s), 0.9 s minimum, 3.6 s maximum — unhurried but not slow, and never the browser's quick jump. Any wheel, touch, key or pointer input cancels it. Links land 96px below the top so the sticky header never covers the target.
- **Tour:** the hero's primary action is **TAKE THE TOUR ▶** (it replaced the ALTAIR / EXPLORE REACLOUD pair; the label flips to STOP TOUR ■ while running). It glides from the next stop below the view through every element marked `data-stop`, holds 3.8 s on each, and **ends on the last stop** (no loop); starting it from the bottom of the page begins again from the top. Each stop lands with its heading 96px from the top, just under the sticky header (the same spot an in-page link lands), so nothing is cut off. Put `data-stop` on a section's heading (or the section itself when it starts with content, like the ticker), not on a padded wrapper. Stops that would land where the previous one did — typically the footer once the page has hit bottom — are dropped, so every stop moves. A bar at the bottom shows `03 / 06`, a dwell progress line and STOP; any user input also stops it.
- **Back to top:** appears after ~one screen of scrolling, bottom-right; a 1px `--ether` line along its bottom edge fills with page progress.
- All of it off under `prefers-reduced-motion` (scrolls jump).

## Imagery

- Product shots show the **current UI**. The ReaCloud photo on the live site (`reacloud-hero.jpg`) still shows the old name `CLOUD_REAPER`; the mockups embed the live ReaCloud app mockup (`app.html?embed`) as the product shot instead, synced to the page theme (`.n-screen`). Replace with a real capture once the plug-in UI is final.
- Photos fade into the void on one side and are **muted color at 45% saturation** (`saturate(0.45)` with a light contrast/brightness lift; 55% on hover) — between black-and-white (too flat) and full color (too candy). [DECIDED]

## What stays

Emblem and logotype artwork (unchanged files; only the lockup spacing is proposed to change, see Brand composition), the ticker, the five CSL fonts and their roles, JetBrains Mono body, three themes, one primary per region, forward action on the right, status always labelled.

## Open for the user

- ~~Muted status palette vs v1.0.2~~ — **decided: Nocturne palette; v1.0.2 accents discarded** (the ACCENT review switch is removed).
- Accept `--fg-dim` secondary text (reverses the v1.0.2 two-color text rule).
- Ether blue as the single brand accent, or keep the brand strictly monochrome and drop ether.
- Atmosphere level: fog + grain + scanlines on marketing pages; toned down in the app.
- Brand composition spacing above; if approved, re-export lockups to match.
