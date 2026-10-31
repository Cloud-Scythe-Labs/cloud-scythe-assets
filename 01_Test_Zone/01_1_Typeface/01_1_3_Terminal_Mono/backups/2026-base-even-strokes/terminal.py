#!/usr/bin/env python3
"""Build CSL Terminal: JetBrains Mono (SIL OFL 1.1) with the CSL layer applied.

Usage: python terminal.py            (also run by `build.py CSL_Terminal`)

Pipeline
  1. CSL_Terminal/upstream/*.glyphs  -> UFO masters + designspace (glyphsLib), in a temp dir.
  2. CSL layer, applied identically to every master so they stay interpolation-compatible:
       - squarer bowls: quarter-arc curves pushed toward their corner (SQUARENESS)
       - v1 chunks (CHUNKS): at the corners CSL Terminal v1 cuts, the square where the two
         strokes overlap is taken out, so they meet only through a thin diagonal neck; top
         corners stay curved, as in v1
       - square dots: round dots (i j . : ; ! ? and the rest) become squares
       - slashed zero by default; the `zero` feature now gives JetBrains Mono's dotted zero
     plus renaming to CSL Terminal (the OFL lets us modify and rename; it does not let us
     use the JetBrains trademark, which is removed). Italic masters are unslanted for the
     outline steps and slanted back afterwards.
  3. fontmake -> variable fonts, upright and italic, weight 100-800, all features and ligatures.
  4. fontTools instancer -> static Regular, Bold, Italic, Bold Italic for terminals and IDEs.
  5. WOFF2 of both variable fonts for the web.

Outputs (02_Internal/):
  CSL_Terminal[wght].ttf, CSL_Terminal-Italic[wght].ttf      variable
  CSL_Terminal.ttf (Regular), CSL_Terminal-Bold.ttf,
  CSL_Terminal-Italic.ttf, CSL_Terminal-BoldItalic.ttf        static
  CSL_Terminal.woff2, CSL_Terminal-Italic.woff2               variable, web
  OFL.txt                                                     license, must ship with the fonts
"""

import math
import os
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import glyphsLib
import ufoLib2
from fontmake.font_project import FontProject
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.pens.areaPen import AreaPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import OverlapMode, instantiateVariableFont
from ufoLib2.objects import Contour, Point

SOURCES = Path(__file__).resolve().parent
TERMINAL = SOURCES / "CSL_Terminal"
UPSTREAM = TERMINAL / "upstream"
OUT = SOURCES.parent / "02_Internal"

FAMILY = "CSL Terminal"
PS_FAMILY = "CSLTerminal"
VERSION = (2, 0)                       # 2.000; based on JetBrains Mono 2.305
UPSTREAM_VERSION = "2.305"
COPYRIGHT = (
    "Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono). "
    "Copyright 2026 Cloud Scythe Labs (CSL Terminal modifications)."
)
DESIGNER = "Philipp Nurullin, Konstantin Bulenkov (JetBrains Mono); Cloud Scythe Labs (CSL Terminal)"
VENDOR = "CSL "
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")

# ── CSL layer settings ─────────────────────────────────────────────────────────
# CSL stroke heuristic for letters and digits (chosen in the glyph review, radius A):
#  - monoline: horizontals as thick as verticals (JetBrains Mono draws them ~9% thinner);
#  - concentric corners: each round outer corner and the counter corner inside it are rebuilt
#    as concentric arcs, so the stroke keeps its width round the bend and the curve starts
#    later; outer radius CORNER_RADIUS x the stroke (CSL Terminal V4's own ratio).
CORNER_RADIUS = 1.5
# Letters that keep JetBrains Mono's curves (squared by SQUARENESS) and stroke contrast: the
# bowl-on-stem and arch letters read better that way.
KEEP_JBM_CURVES = ("b", "d", "p", "q", "r", "m", "h", "n")
# Everything else that isn't a letter or digit: 0 = JetBrains Mono's curves, 1 = square
# corners. 0.6 gives the CSL rounded-rectangle bowls while keeping counters open.
SQUARENESS = 0.6
# Glyph-specific ports from the review:
# 8: upper and lower counters as tall as each other, as in CSL Terminal V4 (JetBrains Mono's
# upper counter is ~12% shorter).
EIGHT_COUNTER_RATIO = 1.0
# Q: O with a vertical tail down the centre (from the glyph review), this fraction of the cap
# height below the baseline.
Q_TAIL_DEPTH = 0.125
# ? and ¿: CSL V4's hook, drawn on JetBrains Mono's width with its stroke and its dot.
# 0: CSL's slash: the stroke's own width, ending at the counter walls, through the centre, at
# CSL Mono's angle (centre line from 22.7% up the left wall to 76.7% up the right wall).
ZERO_SLASH = (0.227, 0.767)
# The squarer corners and thicker horizontals hold more ink than JetBrains Mono. Every outline
# is moved inward by half this fraction of the master's stem so a paragraph at code sizes stays
# within ~1% of JetBrains Mono's colour at every style (Regular stems 90 -> ~87).
STROKE_TRIM = 0.035
# JetBrains Mono's round glyphs overshoot the baseline, x-height and cap height by ~10 units
# so curves look as tall as flat tops. With CSL's squarer corners they look taller instead, so
# letters, digits and ordinary punctuation/currency are flattened onto the lines: points within
# OVERSHOOT_BAND units beyond a line move onto it.
OVERSHOOT_BAND = 15
FLAT_CATEGORIES = ("L", "Nd", "Po", "Sc")
# Cell-filling glyphs keep their exact edges so they still tile in a terminal: box drawing,
# block elements, braille, Powerline and legacy-computing symbols.
TILE_RANGES = ((0x2500, 0x259F), (0x2800, 0x28FF), (0xE0A0, 0xE0FF), (0x1FB00, 0x1FBFF))
# CSL Terminal v1 is an existing font with square chunks taken out of it (in FontForge). Each
# chunk is the square where a vertical and a horizontal stroke overlap at an outer corner: the
# bite runs from the outer corner to the inside (counter) corner, the counter corner is
# tightened to a half-stroke radius and the bite's inner corner gets a half-stroke fillet, so
# the two strokes touch only through a thin diagonal neck (the "ghost" gap).
# Corners per glyph (and its alternates), read from v1's outlines. BL / BR = the bottom-left /
# bottom-right corner of the glyph's lowest bowl. Empty while the base is still being iterated;
# the first batch to try is ("BL", "BR") on o c e s u O C G U J S zero six eight.
CHUNKS = {}
# Arcs may end this far off the axis (run/rise) and still count as corners (foot terminals of
# c e s, joins).
TERMINAL_SLOPE = 0.35
FILLET_K = 0.5523                      # cubic handle ratio for a quarter circle
# Unslanted italic handles are axis-aligned only to within rounding.
ITALIC_TOLERANCE = 2.0
# Parentheses stay round: squared, they read as brackets (the v1 problem).
ROUND_GLYPHS = ("parenleft", "parenright")
# A square reads larger than a circle in the same box; shrink it this much to match weight.
DOT_OPTICAL_SHRINK = 0.06
# Swap these with their ".zero" alternates so the slashed form is the default.
ZEROS = ("zero", "zero.numr", "zero.dnom", "zeroinferior", "zerosuperior")

STATICS = {                            # file suffix -> (source, wght, subfamily, bold, italic)
    "": ("roman", 400, "Regular", False, False),
    "-Bold": ("roman", 700, "Bold", True, False),
    "-Italic": ("italic", 400, "Italic", False, True),
    "-BoldItalic": ("italic", 700, "Bold Italic", True, True),
}
MAC_EPOCH_DIFF = 2082844800


def keeps_round(name):
    return name.split(".")[0] in ROUND_GLYPHS


def quarter_arcs(contour, tol=0.0, slope=0.0):
    """(index of the arc's end point, starts horizontal?) for every quarter arc in a contour.

    A quarter arc starts with an axis-aligned tangent and ends with the perpendicular one;
    its handles lie on those tangents. A handle counts as axis-aligned if it is off by at most
    `tol` units plus `slope` times its length along the axis (terminal arcs such as the foot of
    c and e end a few degrees off vertical).
    """
    def along(d_major, d_minor):
        return abs(d_minor) <= tol + slope * abs(d_major) and abs(d_major) > tol

    pts = list(contour.points)
    n = len(pts)
    for i, p in enumerate(pts):
        if p.type != "curve":
            continue
        p0, a, b = pts[(i - 3) % n], pts[(i - 2) % n], pts[(i - 1) % n]
        if a.type is not None or b.type is not None or p0.type is None:
            continue
        h0, v0 = along(a.x - p0.x, a.y - p0.y), along(a.y - p0.y, a.x - p0.x)
        h1, v1 = along(b.x - p.x, b.y - p.y), along(b.y - p.y, b.x - p.x)
        if (h0 and v1) or (v0 and h1):
            yield i, h0


def arc_corner(p0, p, h0):
    return (p.x, p0.y) if h0 else (p0.x, p.y)


def square_curves(glyph, s, tol=0.0):
    """Push both handles of every quarter arc toward the arc's corner.

    Moving them toward the tangents' intersection keeps the structure (so masters stay
    compatible) and squares the bowl.
    """
    for contour in glyph.contours:
        pts = list(contour.points)
        n = len(pts)
        for i, h0 in list(quarter_arcs(contour, tol)):
            p0, a, b, p = pts[(i - 3) % n], pts[(i - 2) % n], pts[(i - 1) % n], pts[i]
            cx, cy = arc_corner(p0, p, h0)
            for off, on in ((a, p0), (b, p)):
                full = ((cx - on.x) ** 2 + (cy - on.y) ** 2) ** 0.5
                if not full:
                    continue
                t = ((off.x - on.x) ** 2 + (off.y - on.y) ** 2) ** 0.5 / full
                t += (1 - t) * s
                off.x = round(on.x + (cx - on.x) * t, 1)
                off.y = round(on.y + (cy - on.y) * t, 1)


def _sign(v):
    return (v > 0) - (v < 0)


def _is_outer(contour):
    pen = AreaPen()
    contour.draw(pen)
    return pen.value > 0                   # UFO: outer contours run counter-clockwise


def corners(contour, tol=0.0):
    """Every right-angle corner of a contour: ("arc", i) for a quarter arc ending at point i,
    ("sharp", i) for an on-curve point between an axis-aligned line in and one out."""
    pts = list(contour.points)
    n = len(pts)
    out = [("arc", i) for i, _ in quarter_arcs(contour, tol, TERMINAL_SLOPE)]
    for i, p in enumerate(pts):
        a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        if p.type not in ("line", "curve") or a.type is None or b.type != "line":
            continue
        d0, d1 = (p.x - a.x, p.y - a.y), (b.x - p.x, b.y - p.y)
        h0, v0 = abs(d0[1]) <= tol < abs(d0[0]), abs(d0[0]) <= tol < abs(d0[1])
        h1, v1 = abs(d1[1]) <= tol < abs(d1[0]), abs(d1[0]) <= tol < abs(d1[1])
        if (h0 and v1) or (v0 and h1):
            out.append(("sharp", i))
    return out


def corner_geometry(pts, corner):
    """(C, e0, e1, start, end): the corner point, the unit directions along the contour into
    and out of it, and the on-curve points the corner runs between."""
    kind, i = corner
    n = len(pts)
    if kind == "arc":
        p0, a, p = pts[(i - 3) % n], pts[(i - 2) % n], pts[i]
        h0 = abs(a[1] - p0[1]) < abs(a[0] - p0[0])
        c = (p[0], p0[1]) if h0 else (p0[0], p[1])
    else:
        p0, c, p = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    e0 = (_sign(c[0] - p0[0]), _sign(c[1] - p0[1]))
    e1 = (_sign(p[0] - c[0]), _sign(p[1] - c[1]))
    return (c[0], c[1]), e0, e1, p0, p


def plan_chunks(glyph, tags, stem, tol=0.0):
    """[((ci, kind, i), (cj, kind, j))]: outer corner and inner corner of each CHUNKS tag.

    Decided once, on the default master, so every master gets the same point structure. The
    outer corner is the lowest convex bottom corner on that side of an outer contour; the inner
    corner is the nearest corner diagonally inside it, opening the same way (the counter's or
    the aperture's corner), which bounds the overlap square that is cut out.
    """
    snap = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    found = [(ci, *k) for ci, c in enumerate(glyph.contours) for k in corners(c, tol)]
    centre = glyph.width / 2
    plan = []
    for tag in tags:
        best = None
        for ci, kind, i in found:
            if not _is_outer(glyph.contours[ci]):
                continue
            c, e0, e1, a, b = corner_geometry(snap[ci], (kind, i))
            if e0[0] * e1[1] - e0[1] * e1[0] <= 0:
                continue                   # concave
            if not (min(a[1], b[1]) >= c[1] - tol and max(a[1], b[1]) > c[1] + tol):
                continue                   # not a bottom corner
            left = max(a[0], b[0]) > c[0]  # the bottom edge runs off to the right
            if left != (tag == "BL"):
                continue
            key = (c[1], -abs(c[0] - centre))
            if best is None or key < best[0]:
                best = (key, (ci, kind, i), c, e0, e1)
        if best is None:
            continue
        _, outer, c, e0, e1 = best
        inward = (e1[0] - e0[0], e1[1] - e0[1])
        inner, near = None, None
        for cj, kind, j in found:
            if (cj, kind, j) == outer:
                continue
            k, f0, f1, a, b = corner_geometry(snap[cj], (kind, j))
            dx, dy = (k[0] - c[0]) * inward[0], (k[1] - c[1]) * inward[1]
            if not (0.3 * stem <= dx <= 2.5 * stem and 0.3 * stem <= dy <= 2.5 * stem):
                continue
            opens = all((q[0] - k[0]) * inward[0] >= -tol and (q[1] - k[1]) * inward[1] >= -tol
                        for q in (a, b))
            if opens and (near is None or max(dx, dy) < near):
                inner, near = (cj, kind, j), max(dx, dy)
        if inner:
            plan.append((outer, inner))
    return plan


def _rounded(k, e0, e1, r):
    """Points rounding corner k (walked in along e0, out along e1) with radius r."""
    q0 = (k[0] - e0[0] * r, k[1] - e0[1] * r)
    q1 = (k[0] + e1[0] * r, k[1] + e1[1] * r)
    h = r * FILLET_K
    return [(q0, "line"), ((q0[0] + e0[0] * h, q0[1] + e0[1] * h), None),
            ((q1[0] - e1[0] * h, q1[1] - e1[1] * h), None), (q1, "curve")]


def apply_chunks(glyph, plan):
    """Cut each planned overlap square out of this master's outlines.

    Sizes come from this master's own corners, so the cut is the full stroke overlap at every
    weight. Walking into the outer corner C: stop short of C level with the inner corner K, run
    in to K (filleted), run back out along the other stroke past C, carry on. K itself is
    tightened to the same half-stroke radius.
    """
    snap = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    edits = {}                             # (ci, i) -> (indices removed, replacement points)

    def span(n, kind, i):
        return {(i - 2) % n, (i - 1) % n, i} if kind == "arc" else {i}

    for (ci, ok, oi), (cj, ik, ij) in plan:
        c, e0, e1, a, b = corner_geometry(snap[ci], (ok, oi))
        k, f0, f1, ka, kb = corner_geometry(snap[cj], (ik, ij))
        # Cut depth on the way in and on the way out: the stroke overlap, kept inside this
        # master's corner so every master gets the same points.
        b0 = abs((k[0] - c[0]) * e0[0] + (k[1] - c[1]) * e0[1])
        b1 = abs((k[0] - c[0]) * e1[0] + (k[1] - c[1]) * e1[1])
        b0 = min(b0, 0.95 * (abs(c[0] - a[0]) + abs(c[1] - a[1])))
        b1 = min(b1, 0.95 * (abs(b[0] - c[0]) + abs(b[1] - c[1])))
        r = min(b0, b1) / 2
        inner = (c[0] - e0[0] * b0 + e1[0] * b1, c[1] - e0[1] * b0 + e1[1] * b1)
        pts = [((c[0] - e0[0] * b0, c[1] - e0[1] * b0), "line")]
        pts += _rounded(inner, e1, e0, r)  # into the cut's inner corner along e1, out along e0
        pts.append(((c[0] + e1[0] * b1, c[1] + e1[1] * b1), "line"))
        if ok == "arc":
            pts.append((b, "line"))
        edits[(ci, oi)] = (span(len(snap[ci]), ok, oi), pts)
        if ik == "arc":
            reach = min(abs(k[0] - ka[0]) + abs(k[1] - ka[1]), abs(kb[0] - k[0]) + abs(kb[1] - k[1]))
            tight = _rounded(k, f0, f1, min(r, 0.9 * reach)) + [(kb, "line")]
            edits[(cj, ij)] = (span(len(snap[cj]), ik, ij), tight)
    for ci, contour in enumerate(glyph.contours):
        mine = {i: e for (cc, i), e in edits.items() if cc == ci}
        if not mine:
            continue
        drop = set().union(*(e[0] for e in mine.values()))
        new = []
        for i, p in enumerate(contour.points):
            if i in mine:
                new += [Point(round(x, 1), round(y, 1), t) for (x, y), t in mine[i][1]]
            elif i not in drop:
                new.append(p)
        contour.points.clear()
        contour.points.extend(new)


def _category(ufo, glyph):
    """Unicode category of a glyph, or of its base glyph for unencoded alternates (a.cv16)."""
    for g in (glyph, ufo.get(glyph.name.split(".")[0])):
        if g is not None and g.unicodes:
            return unicodedata.category(chr(g.unicodes[0]))
    return ""


def csl_strokes(ufo, glyph):
    """True for the glyphs that take the CSL stroke heuristic: letters and digits except
    KEEP_JBM_CURVES."""
    if glyph.name.split(".")[0] in KEEP_JBM_CURVES:
        return False
    cat = _category(ufo, glyph)
    return cat.startswith("L") or cat == "Nd"


def _mitred_normals(pts):
    """Unit-ish outward normal per point (material is left of the path), mitred at corners."""
    n = len(pts)
    out = []
    for i, (x, y) in enumerate(pts):
        normals = []
        for (ax, ay), (bx, by) in ((pts[i - 1], (x, y)), ((x, y), pts[(i + 1) % n])):
            length = math.hypot(bx - ax, by - ay)
            if length:
                normals.append(((by - ay) / length, -(bx - ax) / length))
        if not normals:
            out.append((0.0, 0.0))
            continue
        n0, n1 = normals[0], normals[-1]
        scale = 1 / max(1 + n0[0] * n1[0] + n0[1] * n1[1], 0.3)
        out.append(((n0[0] + n1[0]) * scale, (n0[1] + n1[1]) * scale))
    return out


def monoline(glyph, info):
    """Thicken horizontals to the vertical stem width without moving any alignment zone.

    Every outline grows vertically by half the stem difference, then y is remapped piecewise
    linearly so the descender, baseline, x-height, cap height and ascender (and anything at
    them) land where they were; bars between zones keep the extra thickness.
    """
    dy = (info.postscriptStemSnapV[0] - info.postscriptStemSnapH[0]) / 2
    zones = sorted({info.descender, 0, info.xHeight, info.capHeight, info.ascender})
    grown = [z - dy if z <= 0 else z + dy for z in zones]

    def remap(y):
        if y <= grown[0]:
            return y + zones[0] - grown[0]
        if y >= grown[-1]:
            return y + zones[-1] - grown[-1]
        for g0, g1, z0, z1 in zip(grown, grown[1:], zones, zones[1:]):
            if g0 <= y <= g1:
                return z0 + (y - g0) * (z1 - z0) / (g1 - g0)
        return y

    for contour in glyph.contours:
        pts = [(p.x, p.y) for p in contour.points]
        for p, (x, y), (_, ny) in zip(contour.points, pts, _mitred_normals(pts)):
            p.y = round(remap(y + ny * dy), 2)


def _aligned(pts, i, step, tol):
    """False if the straight segment beyond point i (one step away) is diagonal, as on the
    spine of S: rebuilding that corner square would kink the join. Horizontal and vertical
    segments (stems, bars, the cut ends of c e s 3 5 terminals) are fine."""
    n = len(pts)
    j = (i + step) % n
    if pts[j][2] is None:                  # a curve continues: fine
        return True
    dx, dy = abs(pts[j][0] - pts[i][0]), abs(pts[j][1] - pts[i][1])
    return min(dx, dy) <= tol + 0.05 * max(dx, dy)


def plan_corners(glyph, stem, tol=0.0):
    """[(outer (ci, i), inner (cj, j))]: each convex outer quarter arc and the counter arc
    diagonally inside it (0.4-1.8 stems away, opening the same way). Planned on the default
    master so every master gets the same points."""
    snap = [[(p.x, p.y, p.type) for p in c.points] for c in glyph.contours]
    xy = [[(x, y) for x, y, _ in c] for c in snap]
    arcs = [(ci, i) for ci, c in enumerate(glyph.contours) for k, i in corners(c, tol) if k == "arc"]

    def straight(ci, i):
        n = len(snap[ci])
        return _aligned(snap[ci], (i - 3) % n, -1, tol) and _aligned(snap[ci], i, 1, tol)

    plan, used = [], set()
    for ci, i in arcs:
        if not _is_outer(glyph.contours[ci]) or not straight(ci, i):
            continue
        c, e0, e1, _, _ = corner_geometry(xy[ci], ("arc", i))
        if e0[0] * e1[1] - e0[1] * e1[0] <= 0:
            continue                       # concave: a join, left alone
        inward = (e1[0] - e0[0], e1[1] - e0[1])
        best = None
        for cj, j in arcs:
            if (cj, j) == (ci, i) or (cj, j) in used or not straight(cj, j):
                continue
            k, _, _, ka, kb = corner_geometry(xy[cj], ("arc", j))
            dx, dy = (k[0] - c[0]) * inward[0], (k[1] - c[1]) * inward[1]
            if not (0.4 * stem <= dx <= 1.8 * stem and 0.4 * stem <= dy <= 1.8 * stem):
                continue
            if not all((q[0] - k[0]) * inward[0] >= -tol and (q[1] - k[1]) * inward[1] >= -tol
                       for q in (ka, kb)):
                continue
            if best is None or max(dx, dy) < best[0]:
                best = (max(dx, dy), (cj, j))
        if best:
            used.add(best[1])
            plan.append(((ci, i), best[1]))
    return plan


def _arc(c, e0, e1, r0, r1):
    """A quarter arc rounding corner c (walked in along e0, out along e1), radius r0 on the
    way in and r1 on the way out."""
    q0 = (c[0] - e0[0] * r0, c[1] - e0[1] * r0)
    q1 = (c[0] + e1[0] * r1, c[1] + e1[1] * r1)
    k = FILLET_K
    return [(q0, "line"), ((q0[0] + e0[0] * r0 * k, q0[1] + e0[1] * r0 * k), None),
            ((q1[0] - e1[0] * r1 * k, q1[1] - e1[1] * r1 * k), None), (q1, "curve")]


def _overshoot(y, info):
    """How far y must move to land on the line it overshoots (0 if it overshoots none)."""
    bottoms, tops = _zone_lines(info)
    for z in bottoms:
        if z - OVERSHOOT_BAND <= y < z:
            return z - y
    for z in tops:
        if z < y <= z + OVERSHOOT_BAND:
            return z - y
    return 0


def apply_corners(glyph, plan, stem, info):
    """Rebuild each planned pair as concentric arcs with this master's strokes: outer radius
    CORNER_RADIUS x the stroke, inner radius the outer one minus the stroke on each axis.

    A corner whose flat edge overshoots a line (JetBrains Mono's rounds do, by ~10 units) is
    first moved onto it together with the counter edge behind it, so the bar keeps its
    thickness and the rebuilt corner keeps its full radius.
    """
    xy = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    moves = set()
    for (ci, i), (cj, j) in plan:
        c = corner_geometry(xy[ci], ("arc", i))[0]
        k = corner_geometry(xy[cj], ("arc", j))[0]
        shift = _overshoot(c[1], info)
        if shift:
            moves |= {(ci, c[1], shift), (cj, k[1], shift)}
    for ci, y, shift in moves:
        for p in glyph.contours[ci].points:
            if abs(p.y - y) < 0.5:
                p.y = y + shift
    xy = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    edits = {}
    for (ci, i), (cj, j) in plan:
        c, e0, e1, a, b = corner_geometry(xy[ci], ("arc", i))
        k, f0, f1, ka, kb = corner_geometry(xy[cj], ("arc", j))
        stroke = {0: abs(k[0] - c[0]), 1: abs(k[1] - c[1])}     # per axis
        radius = CORNER_RADIUS * (stroke[0] + stroke[1]) / 2
        axis_in = 0 if e0[0] else 1                              # axis e0 runs along
        r_in = min(radius, 0.98 * (abs(c[0] - a[0]) + abs(c[1] - a[1])))
        r_out = min(radius, 0.98 * (abs(b[0] - c[0]) + abs(b[1] - c[1])))
        outer_r = {axis_in: r_in, 1 - axis_in: r_out}
        axis_k = 0 if f0[0] else 1
        floor = 0.12 * stem
        k_in = min(max(outer_r[axis_k] - stroke[axis_k], floor), 0.98 * (abs(k[0] - ka[0]) + abs(k[1] - ka[1])))
        k_out = min(max(outer_r[1 - axis_k] - stroke[1 - axis_k], floor),
                    0.98 * (abs(kb[0] - k[0]) + abs(kb[1] - k[1])))
        edits[(ci, i)] = _arc(c, e0, e1, r_in, r_out) + [(b, "line")]
        edits[(cj, j)] = _arc(k, f0, f1, k_in, k_out) + [(kb, "line")]
    for ci, contour in enumerate(glyph.contours):
        mine = {i: e for (cc, i), e in edits.items() if cc == ci}
        if not mine:
            continue
        n = len(xy[ci])
        drop = {(i - d) % n for i in mine for d in (1, 2)}
        new = []
        for i, p in enumerate(contour.points):
            if i in mine:
                new += [Point(round(x, 2), round(y, 2), t) for (x, y), t in mine[i]]
            elif i not in drop:
                new.append(p)
        contour.points.clear()
        contour.points.extend(new)


def balance_eight(glyph):
    """Move the waist of 8 so its counters have EIGHT_COUNTER_RATIO (upper : lower); bars and
    the waist keep their thickness, only the counters stretch."""
    counters = sorted((c for c in glyph.contours if not _is_outer(c)),
                      key=lambda c: min(p.y for p in c.points))
    if len(counters) != 2:
        return
    lo_b, lo_t = min(p.y for p in counters[0].points), max(p.y for p in counters[0].points)
    up_b, up_t = min(p.y for p in counters[1].points), max(p.y for p in counters[1].points)
    total = (lo_t - lo_b) + (up_t - up_b)
    shift = (up_t - total * EIGHT_COUNTER_RATIO / (1 + EIGHT_COUNTER_RATIO)) - up_b
    knots = [(lo_b, lo_b), (lo_t, lo_t + shift), (up_b, up_b + shift), (up_t, up_t)]

    def remap(y):
        if y <= lo_b or y >= up_t:
            return y
        for (s0, d0), (s1, d1) in zip(knots, knots[1:]):
            if s0 <= y <= s1:
                return d0 + (y - s0) * (d1 - d0) / (s1 - s0)
        return y

    for c in glyph.contours:
        for p in c.points:
            p.y = round(remap(p.y), 2)


def vertical_q_tail(ufo):
    """Q = O plus a stroke-wide vertical tail from inside the bottom bar straight down the
    centre, replacing JetBrains Mono's diagonal tail."""
    o, q = ufo["O"], ufo["Q"]
    counter = next((c for c in o.contours if not _is_outer(c)), None)
    outer = next((c for c in o.contours if _is_outer(c)), None)
    if counter is None or outer is None:
        return
    stem = min(p.x for p in counter.points) - min(p.x for p in outer.points)
    centre, top = q.width / 2, min(p.y for p in counter.points)
    tail = -Q_TAIL_DEPTH * ufo.info.capHeight
    contours = [[((p.x, p.y), p.type) for p in c.points] for c in o.contours]
    contours.append([((centre - stem / 2, tail), "line"), ((centre + stem / 2, tail), "line"),
                     ((centre + stem / 2, top), "line"), ((centre - stem / 2, top), "line")])
    set_contours(q, contours)


# CSL V4's question mark on its pixel grid (stroke 100, cap 800), counter-clockwise, with each
# corner's rounding: "o" outer (CORNER_RADIUS strokes), "i" inner (one stroke less, so the
# bends are concentric), "s" square. Columns and rows are mapped onto JetBrains Mono's metrics.
QUESTION = (
    (80, 600, "s"), (180, 600, "s"), (180, 700, "i"), (480, 700, "i"), (480, 450, "i"),
    (280, 450, "o"), (280, 200, "s"), (380, 200, "s"), (380, 350, "i"), (580, 350, "o"),
    (580, 800, "o"), (80, 800, "o"),
)


def draw_question(ufo, stem, flip_bottom=None):
    """CSL's ? fitted to JetBrains Mono: the width of O, the cap height, this master's stroke
    and the square dot of the full stop. With flip_bottom it is turned 180 degrees into ¿ with
    its lowest point there. Returns the contours as point lists."""
    left, right = min(p.x for c in ufo["O"].contours for p in c), max(p.x for c in ufo["O"].contours for p in c)
    cap = ufo.info.capHeight
    dot = ufo["period"].contours[0]
    dxs, dys = [p.x for p in dot], [p.y for p in dot]
    side = (max(dxs) - min(dxs)) * (1 - DOT_OPTICAL_SHRINK)
    dot_bottom = (min(dys) + max(dys)) / 2 - side / 2
    centre = ufo["question"].width / 2
    s = stem
    stem_bottom = dot_bottom + side + s
    xs = {80: left, 180: left + s, 280: centre - s / 2, 380: centre + s / 2, 480: right - s, 580: right}
    span = cap - stem_bottom
    ys = {200: stem_bottom, 350: stem_bottom + span * 250 / 600 - s, 450: stem_bottom + span * 250 / 600,
          600: min(stem_bottom + span * 400 / 600, cap - 1.6 * s), 700: cap - s, 800: cap}
    radius = {"o": CORNER_RADIUS * s, "i": (CORNER_RADIUS - 1) * s, "s": 0}
    poly = [(xs[x], ys[y], radius[r]) for x, y, r in QUESTION]
    n = len(poly)
    # Heavy weights crowd CSL's five-column grid: shrink radii that don't fit their edges.
    fit = []
    for i, (x, y, r) in enumerate(poly):
        limit = r
        for j in (i - 1, (i + 1) % n):
            ox, oy, other = poly[j]
            if r:
                limit = min(limit, 0.98 * (abs(ox - x) + abs(oy - y)) * r / (r + other))
        fit.append(limit)
    hook = []
    for i, (x, y, _) in enumerate(poly):
        px, py, _ = poly[i - 1]
        nx, ny, _ = poly[(i + 1) % n]
        e0 = (_sign(x - px), _sign(y - py))
        e1 = (_sign(nx - x), _sign(ny - y))
        hook += _arc((x, y), e0, e1, fit[i], fit[i]) if fit[i] else [((x, y), "line")]
    h = side / 2
    square = [((centre - h, dot_bottom), "line"), ((centre + h, dot_bottom), "line"),
              ((centre + h, dot_bottom + side), "line"), ((centre - h, dot_bottom + side), "line")]
    contours = [hook, square]
    if flip_bottom is not None:
        turn = cap + flip_bottom           # y -> turn - y puts the cap line at flip_bottom
        contours = [[((2 * centre - x, turn - y), t) for (x, y), t in c] for c in contours]
    return contours


def set_contours(glyph, contours):
    glyph.clearContours()
    for points in contours:
        glyph.appendContour(Contour(points=[Point(round(x, 2), round(y, 2), t) for (x, y), t in points]))


def csl_zero_slash(glyph):
    """Redraw the slash of a slashed zero as CSL's: as thick as the stroke, ending in the
    stems, through the counter's centre at ZERO_SLASH's angle."""
    slash = next((c for c in glyph.contours if len(c) == 4), None)
    counters = [c for c in glyph.contours if not _is_outer(c) and c is not slash]
    outers = [c for c in glyph.contours if _is_outer(c) and c is not slash]
    if slash is None or len(counters) != 1 or len(outers) != 1:
        return
    cx = [p.x for p in counters[0].points]
    cy = [p.y for p in counters[0].points]
    stroke = min(cx) - min(p.x for p in outers[0].points)
    in_l, in_r, bottom, height = min(cx), max(cx), min(cy), max(cy) - min(cy)
    y_l, y_r = bottom + ZERO_SLASH[0] * height, bottom + ZERO_SLASH[1] * height
    slope = (y_r - y_l) / (in_r - in_l)
    half = stroke / 2 * math.hypot(1, slope)            # vertical half-thickness
    x0, x1 = in_l - stroke / 2, in_r + stroke / 2      # ends buried in the stems
    y0, y1 = y_l - slope * stroke / 2, y_r + slope * stroke / 2
    for p, (x, y) in zip(slash.points, ((x0, y0 - half), (x1, y1 - half), (x1, y1 + half), (x0, y0 + half))):
        p.x, p.y, p.type = round(x, 2), round(y, 2), "line"


def base_edits(ufo, stem):
    """Outline edits that change point structure or stroke weight, applied to every master
    (and to the default master before planning corners): monoline strokes and the glyph
    ports from the review."""
    for g in ufo:
        if csl_strokes(ufo, g):
            monoline(g, ufo.info)
    if "eight" in ufo:
        balance_eight(ufo["eight"])
    if "Q" in ufo:
        vertical_q_tail(ufo)
    for base in ZEROS:
        if f"{base}.zero" in ufo:
            csl_zero_slash(ufo[f"{base}.zero"])
    bottom = min(p.y for c in ufo["questiondown"].contours for p in c)
    question = draw_question(ufo, stem)
    set_contours(ufo["questiondown"], draw_question(ufo, stem, flip_bottom=bottom))
    set_contours(ufo["question"], question)


def tiles(ufo, glyph):
    """True for cell-filling glyphs (TILE_RANGES), including their unencoded alternates."""
    for g in (glyph, ufo.get(glyph.name.split(".")[0])):
        if g is not None and g.unicodes:
            return any(lo <= u <= hi for u in g.unicodes for lo, hi in TILE_RANGES)
    return False


def trim_strokes(glyph, delta):
    """Move every outline point `delta` units into the ink (material is left of the path).

    Each point moves along the mitred normal of its two neighbouring segments, so straight
    edges move exactly `delta`, square corners move `delta` on both axes and curves (handles
    included) stay parallel to the original. The point structure is unchanged.
    """
    for contour in glyph.contours:
        pts = [(p.x, p.y) for p in contour.points]
        n = len(pts)
        if n < 3:
            continue
        moved = []
        for i, (x, y) in enumerate(pts):
            normals = []
            for (ax, ay), (bx, by) in ((pts[i - 1], (x, y)), ((x, y), pts[(i + 1) % n])):
                dx, dy = bx - ax, by - ay
                length = math.hypot(dx, dy)
                if length:
                    normals.append((-dy / length, dx / length))
            if not normals:
                moved.append((x, y))
                continue
            n0, n1 = normals[0], normals[-1]
            scale = delta / max(1 + n0[0] * n1[0] + n0[1] * n1[1], 0.3)
            moved.append((x + (n0[0] + n1[0]) * scale, y + (n0[1] + n1[1]) * scale))
        for p, (x, y) in zip(contour.points, moved):
            p.x, p.y = round(x, 2), round(y, 2)


def _zone_lines(info):
    """(bottom lines, top lines): ink rests on the former and hangs from the latter."""
    return (sorted({info.descender, 0}), sorted({info.xHeight, info.capHeight, info.ascender}))


def flatten_overshoot(glyph, info):
    bottoms, tops = _zone_lines(info)
    for c in glyph.contours:
        for p in c.points:
            for z in bottoms:
                if z - OVERSHOOT_BAND <= p.y < z:
                    p.y = z
            for z in tops:
                if z < p.y <= z + OVERSHOOT_BAND:
                    p.y = z


def restore_zones(glyph, info, delta):
    """Undo the vertical part of trim_strokes at the lines: ink that rested on a line (now
    delta above it) or hung from one (delta below) goes back onto it, piecewise linearly."""
    bottoms, tops = _zone_lines(info)
    knots = sorted([(z + delta, z) for z in bottoms] + [(z - delta, z) for z in tops])

    def remap(y):
        if y <= knots[0][0]:
            return y + knots[0][1] - knots[0][0]
        if y >= knots[-1][0]:
            return y + knots[-1][1] - knots[-1][0]
        for (s0, d0), (s1, d1) in zip(knots, knots[1:]):
            if s0 <= y <= s1:
                return d0 + (y - s0) * (d1 - d0) / (s1 - s0)
        return y

    for c in glyph.contours:
        for p in c.points:
            p.y = round(remap(p.y), 2)


def slant(ufo, angle):
    """Shear every contour point and anchor by `angle` degrees about the baseline (components
    stay put; everything is restored exactly by shearing back)."""
    t = math.tan(math.radians(angle))
    for g in ufo:
        for c in g.contours:
            for p in c.points:
                p.x += p.y * t
        for a in g.anchors:
            a.x += a.y * t



def is_dot(contour):
    """A JetBrains Mono dot: a 4-arc circle (12 points) of dot size."""
    pts = contour.points
    if len(pts) != 12 or sum(1 for p in pts if p.type) != 4:
        return False
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    return 0 < w < 260 and abs(w - h) <= 0.12 * max(w, h)


def bbox(contour):
    xs, ys = [p.x for p in contour.points], [p.y for p in contour.points]
    return min(xs), min(ys), max(xs), max(ys)


def find_dots(ufo):
    """(glyph, contour index) of every dot, detected in the default (Regular) master.

    A small circle that encloses (or sits inside) another contour is a ring (å, °), not a dot.
    """
    found = []
    for g in ufo:
        boxes = [bbox(c) for c in g.contours]
        for i, c in enumerate(g.contours):
            if not is_dot(c):
                continue
            x0, y0, x1, y1 = boxes[i]
            nested = any(
                j != i and ((x0 <= a and y0 <= b and c2 <= x1 and d <= y1) or (a <= x0 and b <= y0 and x1 <= c2 and y1 <= d))
                for j, (a, b, c2, d) in enumerate(boxes)
            )
            if not nested:
                found.append((g.name, i))
    return found


def square_dot(contour):
    xs, ys = [p.x for p in contour.points], [p.y for p in contour.points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = (x1 - x0) * DOT_OPTICAL_SHRINK / 2
    contour.points.clear()
    for x, y in ((x0 + k, y0 + k), (x0 + k, y1 - k), (x1 - k, y1 - k), (x1 - k, y0 + k)):
        contour.points.append(Point(round(x, 1), round(y, 1), "line"))


def slashed_zero_default(ufo):
    for base in ZEROS:
        alt = f"{base}.zero"
        if base not in ufo or alt not in ufo:
            continue
        a, b = ufo[base], ufo[alt]
        ca, cb = list(a.contours), list(b.contours)
        a.clearContours()
        b.clearContours()
        for c in cb:
            a.appendContour(c)
        for c in ca:
            b.appendContour(c)


def rename(ufo):
    i = ufo.info
    style = i.styleName
    i.familyName = FAMILY
    i.styleMapFamilyName = FAMILY
    i.openTypeNamePreferredFamilyName = None
    i.postscriptFontName = f"{PS_FAMILY}-{style.replace(' ', '')}"
    i.postscriptFullName = f"{FAMILY} {style}"
    i.copyright = COPYRIGHT
    i.trademark = None                 # "JetBrains Mono is a trademark of JetBrains s.r.o."
    i.openTypeNameDesigner = DESIGNER
    i.openTypeNameDesignerURL = "https://github.com/JetBrains/JetBrainsMono"
    i.openTypeNameManufacturer = "Cloud Scythe Labs"
    i.openTypeNameManufacturerURL = None
    i.openTypeNameLicense = LICENSE
    i.openTypeNameLicenseURL = "https://openfontlicense.org"
    i.openTypeNameDescription = (
        f"CSL Terminal is a modified version of JetBrains Mono {UPSTREAM_VERSION}: CSL Terminal's "
        "even strokes and squarer curves, square dots and a slashed zero."
    )
    i.openTypeOS2VendorID = VENDOR
    i.versionMajor, i.versionMinor = VERSION
    i.openTypeNameVersion = f"Version {VERSION[0]}.{VERSION[1]:03d}; based on JetBrains Mono {UPSTREAM_VERSION}"
    i.openTypeNameUniqueID = f"{VERSION[0]}.{VERSION[1]:03d};{VENDOR.strip()};{i.postscriptFontName}"


def prepare(glyphs_file, workdir):
    """Masters with the CSL layer applied; returns the designspace path."""
    glyphsLib.build_masters(str(glyphs_file), str(workdir), write_skipexportglyphs=True)
    ds_path = next(workdir.glob("*.designspace"))
    ds = DesignSpaceDocument.fromfile(ds_path)
    # JetBrains Mono's "Axis Mappings" (user 700 Bold = design 634, etc.) come out of glyphsLib
    # inverted (input 634 -> output 700), which made Bold at wght 700 ~18% heavier than
    # JetBrains Mono Bold. Swap them back so every weight matches upstream.
    for axis in ds.axes:
        axis.map = sorted((design, user) for user, design in axis.map)
        # The STAT labels were derived through the inverted map too (Bold at 558.76).
        design_of = {i.styleName: i.designLocation.get(axis.name) for i in ds.instances}
        for label in axis.axisLabels:
            if design_of.get(label.name) is not None:
                label.userValue = axis.map_backward(design_of[label.name])
    default = next(s for s in ds.sources if s.location == ds.findDefault().location)
    default_ufo = ufoLib2.Font.open(workdir / default.filename)
    angle = default_ufo.info.italicAngle or 0
    tol = ITALIC_TOLERANCE if angle else 0.0
    slant(default_ufo, angle)
    # ? and ¿ are redrawn with square dots of their own.
    dots = [(n, i) for n, i in find_dots(default_ufo) if n not in ("question", "questiondown")]
    default_stem = default_ufo.info.postscriptStemSnapV[0]
    base_edits(default_ufo, default_stem)
    corner_plans = {g.name: plan_corners(g, default_stem, tol) for g in default_ufo
                    if csl_strokes(default_ufo, g)}
    chunks = {g.name: plan_chunks(g, CHUNKS[g.name.split(".")[0]], default_stem, tol)
              for g in default_ufo if g.name.split(".")[0] in CHUNKS}
    # Monospace across the whole weight axis: upstream's ExtraBold master gives NULL and uniFEFF a
    # 510 advance, so interpolated Bold had two non-600 glyphs and fontconfig stopped treating it
    # as monospaced (kitty then refused it). Every master takes the default master's advances.
    advances = {g.name: g.width for g in default_ufo}
    for src in ds.sources:
        ufo = ufoLib2.Font.open(workdir / src.filename)
        slant(ufo, angle)
        stem = ufo.info.postscriptStemSnapV[0]
        base_edits(ufo, stem)
        for g in ufo:
            if g.name in corner_plans:
                apply_corners(g, corner_plans[g.name], stem, ufo.info)
            elif not keeps_round(g.name):
                square_curves(g, SQUARENESS, tol)
            if chunks.get(g.name):
                apply_chunks(g, chunks[g.name])
        for name, idx in dots:
            square_dot(ufo[name].contours[idx])
        trim = STROKE_TRIM / 2 * ufo.info.postscriptStemSnapV[0]
        for g in ufo:
            if tiles(ufo, g):
                continue
            if _category(ufo, g).startswith(FLAT_CATEGORIES):
                flatten_overshoot(g, ufo.info)
            trim_strokes(g, trim)
            restore_zones(g, ufo.info, trim)
        slant(ufo, -angle)
        slashed_zero_default(ufo)
        for g in ufo:
            g.width = advances.get(g.name, g.width)
        rename(ufo)
        ufo.save(overwrite=True)
    for inst in ds.instances:
        inst.familyName = FAMILY
        inst.styleMapFamilyName = FAMILY
        inst.postScriptFontName = f"{PS_FAMILY}-{inst.styleName.replace(' ', '')}"
    out = workdir / f"{PS_FAMILY}.designspace"
    ds.write(out)
    return out


def stamp(font):
    head = font["head"]
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    head.modified = int(epoch) + MAC_EPOCH_DIFF if epoch else head.created
    font.recalcTimestamp = False


def name_static(font, subfamily, bold, italic, weight):
    name = font["name"]
    ps = f"{PS_FAMILY}-{subfamily.replace(' ', '')}"
    full = f"{FAMILY} {subfamily}"
    for nid in (16, 17, 25):
        name.removeNames(nameID=nid)
    for nid, value in ((1, FAMILY), (2, subfamily), (4, full), (6, ps),
                       (3, f"{VERSION[0]}.{VERSION[1]:03d};{VENDOR.strip()};{ps}")):
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)
    os2 = font["OS/2"]
    os2.usWeightClass = weight
    sel = os2.fsSelection & ~0b1100001                    # clear ITALIC, BOLD, REGULAR
    sel |= (1 << 0 if italic else 0) | (1 << 5 if bold else 0) | (1 << 6 if not (bold or italic) else 0)
    os2.fsSelection = sel
    font["head"].macStyle = (1 if bold else 0) | (2 if italic else 0)
    font["post"].isFixedPitch = 1


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        variable = {}
        for key, src, stem in (("roman", "JetBrainsMono.glyphs", "CSL_Terminal"),
                               ("italic", "JetBrainsMono-Italic.glyphs", "CSL_Terminal-Italic")):
            work = tmp / key
            work.mkdir()
            ds = prepare(UPSTREAM / src, work)
            vf_path = tmp / f"{stem}[wght].ttf"
            FontProject().run_from_designspace(str(ds), output=("variable",), output_path=str(vf_path))
            vf = TTFont(vf_path)
            vf["post"].isFixedPitch = 1
            stamp(vf)
            vf.save(OUT / f"{stem}[wght].ttf")
            vf.flavor = "woff2"
            vf.save(OUT / f"{stem}.woff2")
            variable[key] = OUT / f"{stem}[wght].ttf"
            print(f"CSL_Terminal: 02_Internal/{stem}[wght].ttf, {stem}.woff2")

        for suffix, (key, wght, subfamily, bold, italic) in STATICS.items():
            vf = TTFont(variable[key])
            static = instantiateVariableFont(vf, {"wght": wght}, overlap=OverlapMode.REMOVE)
            name_static(static, subfamily, bold, italic, wght)
            stamp(static)
            static.save(OUT / f"CSL_Terminal{suffix}.ttf")
            print(f"CSL_Terminal: 02_Internal/CSL_Terminal{suffix}.ttf")

    shutil.copyfile(TERMINAL / "OFL.txt", OUT / "OFL.txt")


if __name__ == "__main__":
    build()
