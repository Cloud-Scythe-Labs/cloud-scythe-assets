# CSL typeface sources

Sources for the Cloud Scythe Labs fonts, plus the scripts that compile them into the release
binaries in `../01_Branding/` and `../02_Internal/`.

| Source | Output | Outlines |
| --- | --- | --- |
| `CSL_Display.ufo` | `01_Branding/CSL_Display.{otf,woff2}` | cubic (CFF) |
| `CSL_Mono.ufo` | `01_Branding/CSL_Mono.{otf,woff2}` | cubic (CFF) |
| `CSL_Dot_Display.ufo` | `01_Branding/CSL_Dot_Display.{otf,woff2}` | cubic (CFF) |
| `CSL_Dot_Mono.ufo` | `01_Branding/CSL_Dot_Mono.{otf,woff2}` | cubic (CFF) |
| `CSL_Terminal/upstream/*.glyphs` + `terminal.py` | `02_Internal/CSL_Terminal*` (see [CSL Terminal](#csl-terminal)) | quadratic (TrueType), variable |

The binaries are build outputs: edit the sources, never the `.otf`/`.ttf`/`.woff2` files.

## Editing the branding fonts

- **FontForge**: File → Open → select the `.ufo` folder. Write it back with
  File → Generate Fonts… → format *Unified Font Object (UFO3)* to the same path
  (File → Save would create an `.sfd` instead).
- **Fontra** (`fontra filesystem 03_Branding_Assets/03_02_Typefaces/00_Sources`):
  edits the UFO in place.
- **Glyphs 3**: File → Open the `.ufo`; save keeps it as UFO.

Contour direction follows the UFO convention (outer contours counter-clockwise).
After editing, normalize so diffs stay small:

```sh
ufonormalizer -a -m 03_Branding_Assets/03_02_Typefaces/00_Sources/CSL_Display.ufo
```

### Grid

Glyphs are drawn on a 100-unit pixel grid (stems and dots are 100 units; half
steps of 50 occur). Branding fonts round corners with a ~5-unit radius, so
points such as 105/395 and fractional handles (e.g. 2.333) are expected; do not
round them.

| Font | UPM | Ascender | Descender | Cap height | x-height | Advance |
| --- | --- | --- | --- | --- | --- | --- |
| CSL Display | 1100 | 900 | −200 | 700 | 500 | proportional (200–700) |
| CSL Mono | 1000 | 800 | −200 | 700 | 500 | 600 (fixed) |
| CSL Dot Display | 1100 | 900 | −200 | 700 | 500 | proportional (200–700) |
| CSL Dot Mono | 1000 | 800 | −200 | 700 | 500 | 600 (fixed) |

hhea, OS/2 typo and OS/2 win metrics are all set to the ascender/descender
above with a line gap of 0.

## CSL Terminal

CSL Terminal is a modified **JetBrains Mono** (SIL Open Font License 1.1). The upstream sources are
vendored unmodified in `CSL_Terminal/upstream/` (commit and version in `UPSTREAM.txt`); `terminal.py`
applies the CSL layer at build time to every master, so the masters stay interpolation-compatible:

| CSL layer | Where | Setting |
| --- | --- | --- |
| Weight axis | `prepare` | glyphsLib inverts JetBrains Mono's axis mappings (Bold came out at design 740 instead of 634, ~18% heavier); the map and STAT labels are swapped back so every weight, including the Bold statics, has JetBrains Mono's stem thickness. Heights and widths are JetBrains Mono's |
| CSL strokes | `monoline`, `plan_corners`, `apply_corners`, `_close_waist` | all letters and digits: horizontals thickened to the vertical stem width with every alignment zone kept in place. Except `KEEP_JBM_CURVES` (b d p q r m h n, whose free corners keep JetBrains Mono's curves), each round outer corner is rebuilt with the counter corner inside it as concentric arcs, outer radius `CORNER_RADIUS = 1.5` × the stroke (CSL Terminal V4's ratio; 6 and 9 take 2.0, `CORNER_RADIUS_BY_GLYPH`, as their bowls read pinched at 1.5), so the stroke keeps its width round the bend and the curve starts later. Counter corners offset from their outer corner (the waist of 8 and B) take the inner radius, `CORNER_RADIUS − 1` strokes, straight from the stroke, as CSL draws them. Counter corners with no outer corner opposite, in `LONE_COUNTER_CORNERS` (R's bowl above the leg; 6 and 9 where the stroke meets the bowl), start from that radius and grow until the stroke round the corner is as wide as the strokes it joins. Where the two bowls of 8 and B meet, the outer corners take `WAIST_RADIUS` = 1.0 and the outline runs straight from one bowl's corner to the other's, so the notch between the bowls stays shallow instead of a hairline slit into the waist. Corners next to a diagonal (the spine of S) are left alone. Pairs are planned on the Regular master |
| Even joins | `plan_joins`, `apply_joins`, `plan_stem_corners`, `apply_stem_corners` | `JOIN_LETTERS` (b d p q r n h m a g u): JetBrains Mono springs arches and bowls from the stem through a thin neck with a small ink-trap notch; the join curve becomes a bar running flush into the stem, the notch collapses, and the counter corner on that stem edge is tightened to `CORNER_RADIUS − 1` strokes, so the stroke keeps its width through the join |
| Full-weight diagonals | `full_weight_diagonals` | letters and digits: a diagonal stroke thinner than the stem, measured from the middle of each edge to the stroke's other side (ink-trap facets don't count), is widened to it (both edges move out; points are solved against both neighbouring edges so baselines, stems and bars stay put), but never so far that a counter beside it gets narrower than `MIN_COUNTER` stems (M). w and W (`THIN_DIAGONALS`), whose four strokes share one cell, take `THIN_WEIGHT = 0.85` stems instead, all four strokes alike (JetBrains Mono draws their outer strokes heavier than the inner ones) |
| Knee bends | `plan_knees`, `apply_knees` | `KNEE_GLYPHS` only (v V w W X y Y k K A, the letters CSL Terminal V4 draws with knees, plus R's leg to match A's; x, the digits and y's tail on the descender keep straight diagonals, as in V4): where a single diagonal stroke ends flat on the baseline, x-height or cap height, the outer edge ends where JetBrains Mono had it, pulled in to no wider than T's bar (V4's letters all span one width; at the cell edge a vertical end crowded the T or I beside it; w W keep their width), and turns vertical one final stroke width from the line, so the end is a square, running straight from its far end to the bend. Every point of the stroke's inner edge (the crotch of X Y v y, A's crossbar and counter apex, K's arm) slides along its other edge onto the line one stroke in, parallel to the new outer edge, and the stub is one stroke wide, so the whole stroke keeps one width along the diagonal, round the mitred elbow and down the stub (modelled on V4's k). Vertices where two strokes meet (the feet of v and W: edges that spread apart going away from the line) keep their point |
| Clean crotches | `plan_crotches`, `close_crotches`, `_inked` | letters and digits: where two diagonal edges meet in a crotch that opens onto a counter (the crossing of x and X, the fork of v y Y, the inside of w W A M), JetBrains Mono cuts a small ink-trap notch; widening the diagonals deepened it into a visible gap, and in w W it left needle-thin slivers. The notch's points are removed and the two edges meet in a sharp corner. In `BAR_CROTCHES` (6 9) the same is done where the diagonal stroke meets the bowl's bar, whose notch read as a dent beside the counter's rounder corner. Tapered ends (ʹ ʺ) and rounded outer corners are told apart by where the ink is, and left alone |
| Squarer bowls | `square_curves` | everything else: quarter-arc handles pushed toward their corner, `SQUARENESS = 0.6` (0 = JetBrains Mono, 1 = square); parentheses excluded (`ROUND_GLYPHS`) |
| Weight | `trim_strokes`, `restore_zones` | stroke widths start from JetBrains Mono's at every weight; the even strokes, joins and diagonals then hold ~7–9% more ink, so every outline is moved inward by `STROKE_TRIM / 2` × the master's stem (7%: Regular stems 84, Bold 117), judged by eye in kitty against JetBrains Mono; a paragraph at 15 pt is within ~2% of JetBrains Mono's darkness. Ink that sat on a line is put back on it. Box drawing, blocks, braille, Powerline and legacy-computing glyphs (`TILE_RANGES`) keep their exact edges so they still tile |
| Flat lines | `apply_corners`, `flatten_overshoot` | JetBrains Mono's round glyphs overshoot the lines by ~10 units, which made squarer rounds (o O 0 S) look taller than flats (x H 1). For the CSL-stroke corners, the overshooting edge and the counter edge behind it move onto the line before the corner is rebuilt, so the bar keeps its thickness and the corner its full radius; anything else in letters, digits and ordinary punctuation and currency (`FLAT_CATEGORIES`) within `OVERSHOOT_BAND` of a line is put on it. Every one tops out at exactly 550 / 730 and sits on 0, descenders at −180 |
| Glyph ports | `base_edits` | from the glyph review against CSL Terminal V4: 8's counters equal height (`EIGHT_COUNTER_RATIO`); Q is O with a stroke-wide vertical tail down the centre (`Q_TAIL_DEPTH`); R's leg leaves the bowl `R_LEG_SHIFT` stems further right, so it stands steeper instead of starting under the stem; ? and ¿ are CSL V4's hook (`QUESTION`) on JetBrains Mono's width, stroke and square dot, ¿ turned and set to JetBrains Mono's ¿ depth; the slashed 0 takes CSL Mono's slash (`ZERO_SLASH`): stroke-thick, ending in the stems, through the centre |
| v1 chunks | `plan_chunks`, `apply_chunks` | not applied yet (`CHUNKS` is empty while the base is iterated). CSL Terminal v1 is a font with square chunks cut out; at each corner listed in `CHUNKS` the square where the two strokes overlap is removed, from the outer corner to the counter's corner, with a half-stroke fillet in the cut and the counter corner tightened to the same radius. Corners are matched on the Regular master; sizes come from each master's own strokes |
| Square dots | `find_dots`, `square_dot` | round dots detected in the Regular master become squares, `DOT_OPTICAL_SHRINK = 0.06`; rings with a counter (å, °) are left round |
| Slashed zero | `slashed_zero_default` | `zero` and its numr/dnom/inferior/superior forms swap with their `.zero` alternates |
| Monospace guard | `prepare` | every master takes the Regular master's advance widths (upstream's ExtraBold gives NULL/uniFEFF a 510 width, which made interpolated Bold non-monospaced to fontconfig and kitty) |
| Italics | `slant` | italic masters are unslanted (`italicAngle`) before the outline steps and slanted back after, so bowls, bites and dots apply to italics too; handles count as axis-aligned within `ITALIC_TOLERANCE` |
| Naming | `rename` | family CSL Terminal, JetBrains trademark removed, both copyrights kept |

Change the look by editing those constants or adding steps to `prepare()`; never edit the upstream
files. To update JetBrains Mono, replace the files in `upstream/` with a newer release and update
`UPSTREAM.txt` and `UPSTREAM_VERSION`.

Outputs in `02_Internal/`:

| File | Use |
| --- | --- |
| `CSL_Terminal[wght].ttf`, `CSL_Terminal-Italic[wght].ttf` | variable, weight 100–800 (Thin … ExtraBold named instances) |
| `CSL_Terminal.ttf` (Regular), `-Bold`, `-Italic`, `-BoldItalic` `.ttf` | static, for terminals and IDEs that want a style-linked family |
| `CSL_Terminal.woff2`, `CSL_Terminal-Italic.woff2` | variable, web (`csl-tokens.css` declares `font-weight: 100 800`) |
| `OFL.txt` | the license; must ship alongside the font files |

Coverage is JetBrains Mono's: ~1,750 glyphs, 1,372 mapped characters (Latin, Greek, Cyrillic,
box drawing, block elements, Powerline), all coding ligatures (`calt`, on by default) and the
`cv01`–`cv20`, `ss01`–`ss20` and `zero` features.

**License.** As a JetBrains Mono derivative, CSL Terminal must stay under the OFL: it can be bundled
with, embedded in and sold with software, but not sold on its own, and `OFL.txt` must accompany it.
The OFL covers the fonts only, not documents or products made with them.

## Building

Toolchain: `nix develop` at the repo root (Python + ufo2ft/fontmake/glyphsLib/fontTools,
Pillow, ufonormalizer, FontForge), or a venv:

```sh
python3 -m venv .venv && .venv/bin/pip install -r 03_Branding_Assets/03_02_Typefaces/00_Sources/requirements.txt
make fonts PYTHON=.venv/bin/python
```

From the repo root:

| Command | Result |
| --- | --- |
| `make fonts` | builds every font into `01_Branding/` and `02_Internal/` (~20 s, most of it CSL Terminal) |
| `make proof` | renders `00_Sources/proofs/<font>.png` (ignored by git) from the built fonts |
| `make serve` | serves the repo root at http://localhost:8000 without caching, for HTML that loads the fonts |

`python3 build.py CSL_Mono` / `python3 proof.py CSL_Mono` handle a single font.

Builds are reproducible: `head.modified` is `$SOURCE_DATE_EPOCH` if set,
otherwise the `head.created` date from the sources, so unchanged sources
give byte-identical binaries with the same toolchain. The Nix shell unsets the `SOURCE_DATE_EPOCH`
that `mkShell` exports so Nix and venv builds match.

Build details (see `build.py`, `terminal.py`):

- CFF fonts keep fractional coordinates (`roundTolerance=0`) and skip ufo2ft's
  charstring specializer, which would merge collinear points; the OTF is then
  subroutinized with compreffor. The WOFF2 keeps plain charstrings (smaller after Brotli).
- CSL Terminal: glyphsLib → UFO masters → CSL layer → fontmake variable TTF → fontTools instancer
  for the statics (overlaps removed).
- No hinting is generated for any font (JetBrains Mono's own releases are autohinted).

## Naming

Branding fonts: all naming lives in each UFO's `fontinfo.plist`. `build.py` writes nameID 4 from
`postscriptFullName` (ufo2ft would otherwise use the typographic names).

| Font | nameID 1 | 2 | 16 | 17 | 4 | 6 | Version |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CSL_Display | CSL Display | Regular | Cloud Scythe Labs | Display | CSL Display | CSL-Display | 1.100 |
| CSL_Mono | CSL Mono | Regular | Cloud Scythe Labs | Mono | CSL Mono | CSL-Mono | 1.100 |
| CSL_Dot_Display | CSL Dot Display | Regular | Cloud Scythe Labs | Dot Display | CSL Dot Display | CSL-DotDisplay | 1.100 |
| CSL_Dot_Mono | CSL Dot Mono | Regular | Cloud Scythe Labs | Dot Mono | CSL Dot Mono | CSL-DotMono | 1.100 |
| CSL_Terminal | CSL Terminal | Regular / Bold / Italic / Bold Italic | — | — | CSL Terminal Regular … | CSLTerminal-Regular … | 2.000 |

Branding fonts: designer Chris Gallagher (Misery Take Me), vendor ID `MSRY`; bump `versionMinor` in
fontinfo for each release. CSL Terminal: naming and version are constants at the top of
`terminal.py`, vendor ID `CSL `. File names (`CSL_*.otf/ttf/woff2`) are fixed: web pages reference
them directly.

## Known gaps

Branding fonts:

- Glyph coverage: ASCII, part of Latin-1 and arrows U+2190–2199 (195 glyphs).
  No accented letters beyond that.
- No kerning and no OpenType features (no GSUB/GPOS).
- Display/Dot Display use UPM 1100 while Mono/Dot Mono use UPM 1000, so at the
  same CSS `font-size` Display renders at ~91% of Mono's size.
- Control-character glyphs (`uni0000`–`uni001F`, `uni007F`–`uni009F`) are empty,
  as are `ordfeminine` and `ordmasculine` (all fonts) and `dieresis` (Dot fonts).

CSL Terminal:

- Unhinted (see Build details); Windows ClearType renders it softer than JetBrains Mono's hinted release.
- No Nerd Font icon set; Powerline coverage is JetBrains Mono's 7 glyphs.
