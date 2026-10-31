"""Prototype: CSL stroke heuristic on letters and digits (Regular master only).

1. Monoline: horizontals as thick as verticals. Outlines are grown vertically by
   dy = (stemV - stemH) / 2, then remapped piecewise-linearly so baseline, x-height, cap height,
   ascender and descender land where they were.
2. Concentric corners: every outer quarter arc paired with the inner corner diagonally inside it
   is rebuilt as two concentric circular arcs: outer radius R = RADIUS x stroke, inner radius
   R - stroke on each axis (so the stroke keeps its width around the corner, no taper) and the
   curve starts later than JetBrains Mono's.

usage: mono_proto.py OUT.ttf RADIUS FAMILY [MONOLINE 0/1]
"""
import math
import sys
import unicodedata

import ufoLib2
from ufoLib2.objects import Point
from ufo2ft import compileTTF

sys.path.insert(0, "/home/eureka/Code/CloudScytheLabs/cloud-scythe-assets/03_Branding_Assets/03_02_Typefaces/00_Sources")
import terminal as T

OUT, RADIUS, FAMILY = sys.argv[1], float(sys.argv[2]), sys.argv[3]
MONO = len(sys.argv) < 5 or sys.argv[4] == "1"
f = ufoLib2.Font.open("/tmp/csl/jbm-ufo/JetBrainsMono-Regular.ufo")
info = f.info
SV, SH = info.postscriptStemSnapV[0], info.postscriptStemSnapH[0]
DY = (SV - SH) / 2 if MONO else 0
ZONES = sorted({info.descender, 0, info.xHeight, info.capHeight, info.ascender})


def category(g):
    for gg in (g, f.get(g.name.split(".")[0])):
        if gg is not None and gg.unicodes:
            return unicodedata.category(chr(gg.unicodes[0]))
    return ""


def remap(y):
    """Grown outline y -> y with every zone back in place (piecewise linear)."""
    src = [z - DY if z <= 0 else z + DY for z in ZONES]
    if y <= src[0]:
        return y + (ZONES[0] - src[0])
    if y >= src[-1]:
        return y + (ZONES[-1] - src[-1])
    for (s0, s1), (z0, z1) in zip(zip(src, src[1:]), zip(ZONES, ZONES[1:])):
        if s0 <= y <= s1:
            return z0 + (y - s0) * (z1 - z0) / (s1 - s0)
    return y


def grow_y(glyph, dy):
    """Move every point dy outward along the vertical part of its mitred normal."""
    for c in glyph.contours:
        pts = [(p.x, p.y) for p in c.points]
        n = len(pts)
        for idx, p in enumerate(c.points):
            x, y = pts[idx]
            normals = []
            for (ax, ay), (bx, by) in ((pts[idx - 1], (x, y)), ((x, y), pts[(idx + 1) % n])):
                L = math.hypot(bx - ax, by - ay)
                if L:
                    normals.append(((by - ay) / L, -(bx - ax) / L))   # right normal = outward
            if not normals:
                continue
            n0, n1 = normals[0], normals[-1]
            s = dy / max(1 + n0[0] * n1[0] + n0[1] * n1[1], 0.3)
            p.y = remap(y + (n0[1] + n1[1]) * s)


def concentric(glyph):
    snap = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    found = [(ci, *k) for ci, c in enumerate(glyph.contours) for k in T.corners(c) if k[0] == "arc"]
    edits = {}
    used = set()
    for ci, kind, i in found:
        if not T._is_outer(glyph.contours[ci]):
            continue
        c, e0, e1, a, b = T.corner_geometry(snap[ci], (kind, i))
        if e0[0] * e1[1] - e0[1] * e1[0] <= 0:
            continue                                       # concave: a join, leave it
        inward = (e1[0] - e0[0], e1[1] - e0[1])
        best = None
        for cj, k2, j in found:
            if (cj, j) == (ci, i) or (cj, j) in used:
                continue
            k, f0, f1, ka, kb = T.corner_geometry(snap[cj], (k2, j))
            dx, dy = (k[0] - c[0]) * inward[0], (k[1] - c[1]) * inward[1]
            if not (0.4 * SV <= dx <= 1.8 * SV and 0.4 * SV <= dy <= 1.8 * SV):
                continue
            if not all((q[0] - k[0]) * inward[0] >= -1 and (q[1] - k[1]) * inward[1] >= -1 for q in (ka, kb)):
                continue
            if best is None or max(dx, dy) < best[0]:
                best = (max(dx, dy), (cj, j), k, f0, f1, ka, kb, dx, dy)
        reach0 = abs(c[0] - a[0]) + abs(c[1] - a[1])
        reach1 = abs(b[0] - c[0]) + abs(b[1] - c[1])
        if best is None:
            continue                                       # unpaired (terminal): leave
        _, key, k, f0, f1, ka, kb, sx, sy = best
        used.add(key)
        stroke = (sx + sy) / 2
        R = RADIUS * stroke
        # outer radii along e0's axis and e1's axis
        ax0 = 0 if e0[0] else 1                            # axis index of e0 (0 = x)
        R0 = min(R, 0.98 * reach0)
        R1 = min(R, 0.98 * reach1)
        st = {0: sx, 1: sy}
        # inner corner k: walked along f0 into it, f1 out; its radii = outer radius - stroke on that axis
        r_axis = {ax0: R0 - st[ax0], 1 - ax0: R1 - st[1 - ax0]}
        g0 = 0 if f0[0] else 1
        kreach0 = abs(k[0] - ka[0]) + abs(k[1] - ka[1])
        kreach1 = abs(kb[0] - k[0]) + abs(kb[1] - k[1])
        r0 = min(max(r_axis[g0], 0.12 * SV), 0.98 * kreach0)
        r1 = min(max(r_axis[1 - g0], 0.12 * SV), 0.98 * kreach1)
        edits[(ci, i)] = (arc_pts(c, e0, e1, R0, R1) + [(b, "line")])
        edits[key] = (arc_pts(k, f0, f1, r0, r1) + [(kb, "line")])
    for ci, contour in enumerate(glyph.contours):
        mine = {i: e for (cc, i), e in edits.items() if cc == ci}
        if not mine:
            continue
        n = len(snap[ci])
        drop = {(i - d) % n for i in mine for d in (1, 2)}
        new = []
        for i, p in enumerate(contour.points):
            if i in mine:
                new += [Point(round(x, 1), round(y, 1), t) for (x, y), t in mine[i]]
            elif i not in drop:
                new.append(p)
        contour.points.clear()
        contour.points.extend(new)


def arc_pts(c, e0, e1, r0, r1):
    q0 = (c[0] - e0[0] * r0, c[1] - e0[1] * r0)
    q1 = (c[0] + e1[0] * r1, c[1] + e1[1] * r1)
    k = T.FILLET_K
    return [(q0, "line"), ((q0[0] + e0[0] * r0 * k, q0[1] + e0[1] * r0 * k), None),
            ((q1[0] - e1[0] * r1 * k, q1[1] - e1[1] * r1 * k), None), (q1, "curve")]


dots = T.find_dots(f)
for g in f:
    if T.keeps_round(g.name):
        continue
    cat = category(g)
    letter = cat.startswith("L") or cat == "Nd"
    if letter and DY:
        grow_y(g, DY)
    if letter and RADIUS:
        concentric(g)
    else:
        T.square_curves(g, T.SQUARENESS)
for name, idx in dots:
    T.square_dot(f[name].contours[idx])
T.slashed_zero_default(f)
f.info.familyName = f.info.styleMapFamilyName = FAMILY
f.info.styleName = "Regular"
f.info.postscriptFontName = FAMILY.replace(" ", "") + "-Regular"
compileTTF(f, removeOverlaps=True).save(OUT)
print("built", OUT)
