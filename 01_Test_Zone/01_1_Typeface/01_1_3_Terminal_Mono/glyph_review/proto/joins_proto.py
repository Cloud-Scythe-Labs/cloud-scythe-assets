"""Prototype (Regular only): even joins and full-weight diagonals on top of the current build.

1. Joins: JetBrains Mono springs arches and bowls from the stem through a thin neck with a
   small ink trap (the curve meets the stem edge part-way down, then a 3-point notch). The join
   curve is straightened so the bar runs flush into the stem, the notch collapses onto it, and
   the counter corner beside it is tightened to half a stroke: the stroke keeps its width
   through the join (CSL's construction).
2. Diagonals: every diagonal edge whose stroke is thinner than the stem moves outward by half
   the difference; points are solved against both neighbouring edges, so baselines, stems and
   bars stay put.
usage: joins_proto.py OUT.ttf FAMILY
"""
import math
import sys

import ufoLib2
from ufo2ft import compileTTF
from ufoLib2.objects import Point

sys.path.insert(0, "/home/eureka/Code/CloudScytheLabs/cloud-scythe-assets/03_Branding_Assets/03_02_Typefaces/00_Sources")
import terminal as T

OUT, FAMILY = sys.argv[1], sys.argv[2]
f = ufoLib2.Font.open("/tmp/csl/jbm-ufo/JetBrainsMono-Regular.ufo")
STEM = f.info.postscriptStemSnapV[0]
JOIN_LETTERS = set("bdpqrnhmagu")


def find_traps(contour):
    """(curve end index, notch indices, stem x, bar y) for each JetBrains Mono ink trap."""
    pts = list(contour.points)
    n = len(pts)
    out = []
    for i in range(n):
        p1, p2, p3 = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        if p1.type != "curve" or p2.type != "line" or p3.type != "line":
            continue
        if abs(p1.x - p3.x) > 3 or not 5 < abs(p2.x - p1.x) < 35 or abs(p2.y - p3.y) > 1:
            continue
        # the curve ending at p1 starts at the bar's end: horizontal tangent there
        p0 = pts[(i - 3) % n]
        out.append(("end", i, [(i + 1) % n, (i + 2) % n], p1.x, p0.y))
    for i in range(n):
        p1, p2, p3 = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        if p1.type != "line" or p2.type != "line" or p3.type != "line":
            continue
        if abs(p1.x - p3.x) > 3 or not 5 < abs(p2.x - p1.x) < 35 or abs(p1.y - p2.y) > 1:
            continue
        nxt = pts[(i + 3) % n]
        if nxt.type is not None:
            continue                        # p3 must start a curve
        end = pts[(i + 5) % n]
        out.append(("start", (i + 2) % n, [i, (i + 1) % n], p3.x, end.y))
    return out


def fix_joins(glyph):
    for c in glyph.contours:
        pts = list(c.points)
        n = len(pts)
        for kind, i, notch, sx, bar_y in find_traps(c):
            if kind == "end":               # curve p0 -> h1 -> h2 -> p1 ends on the stem
                p0, h1, h2, p1 = pts[(i - 3) % n], pts[(i - 2) % n], pts[(i - 1) % n], pts[i]
                p1.x, p1.y = sx, bar_y
                h1.x, h1.y = p0.x + (sx - p0.x) / 3, bar_y
                h2.x, h2.y = p0.x + 2 * (sx - p0.x) / 3, bar_y
                for j in notch:
                    pts[j].x, pts[j].y = sx, bar_y
            else:                           # curve p3 -> h1 -> h2 -> end starts on the stem
                p3, h1, h2, end = pts[i], pts[(i + 1) % n], pts[(i + 2) % n], pts[(i + 3) % n]
                p3.x, p3.y = sx, bar_y
                h1.x, h1.y = sx + (end.x - sx) / 3, bar_y
                h2.x, h2.y = sx + 2 * (end.x - sx) / 3, bar_y
                for j in notch:
                    pts[j].x, pts[j].y = sx, bar_y
        # tighten counter corners that sit on the stem edge (x of a trap), within a stroke
    xs = {round(t[3]) for c in glyph.contours for t in find_traps(c)}
    return xs


def tighten_stem_corners(glyph, stem_xs, r):
    """Counter arcs whose corner lies on a stem edge get radius r (CSL's tight inner corner)."""
    if not stem_xs:
        return
    for ci, c in enumerate(glyph.contours):
        xy = [(p.x, p.y) for p in c.points]
        n = len(xy)
        edits = {}
        for kind, i in T.corners(c):
            if kind != "arc":
                continue
            k, e0, e1, a, b = T.corner_geometry(xy, ("arc", i))
            if not any(abs(k[0] - sx) < 3 for sx in stem_xs):
                continue
            if e0[0] * e1[1] - e0[1] * e1[0] > 0 and T._is_outer(c):
                continue                    # convex outer corner: not a counter corner
            ri = min(r, 0.95 * (abs(k[0] - a[0]) + abs(k[1] - a[1])))
            ro = min(r, 0.95 * (abs(b[0] - k[0]) + abs(b[1] - k[1])))
            edits[i] = T._arc(k, e0, e1, ri, ro) + [(b, "line")]
        if not edits:
            continue
        drop = {(i - d) % n for i in edits for d in (1, 2)}
        new = []
        for i, p in enumerate(c.points):
            if i in edits:
                new += [Point(round(x, 2), round(y, 2), t) for (x, y), t in edits[i]]
            elif i not in drop:
                new.append(p)
        c.points.clear()
        c.points.extend(new)


def thicken_diagonals(glyph, s):
    """Move diagonal edges outward so each diagonal stroke is s thick."""
    for c_idx, c in enumerate(glyph.contours):
        pass
    # collect all line segments across contours
    segs = []
    for ci, c in enumerate(glyph.contours):
        pts = list(c.points)
        n = len(pts)
        for i, p in enumerate(pts):
            q = pts[(i + 1) % n]
            if p.type is None or q.type != "line":
                continue
            dx, dy = q.x - p.x, q.y - p.y
            L = math.hypot(dx, dy)
            if L < 1:
                continue
            ux, uy = dx / L, dy / L
            diag = min(abs(ux), abs(uy)) > 0.04
            segs.append({"ci": ci, "i": i, "j": (i + 1) % n, "p": (p.x, p.y), "q": (q.x, q.y),
                         "u": (ux, uy), "n": (uy, -ux), "diag": diag, "L": L, "delta": 0.0})
    for a in segs:
        if not a["diag"]:
            continue
        best = None
        for b in segs:
            if b is a or not b["diag"]:
                continue
            if a["u"][0] * b["u"][0] + a["u"][1] * b["u"][1] > -0.97:
                continue                    # not antiparallel
            # distance from b's midpoint to a's line, inward (against a's outward normal)
            mx, my = (b["p"][0] + b["q"][0]) / 2, (b["p"][1] + b["q"][1]) / 2
            d = -((mx - a["p"][0]) * a["n"][0] + (my - a["p"][1]) * a["n"][1])
            # overlap along a's direction
            t = (mx - a["p"][0]) * a["u"][0] + (my - a["p"][1]) * a["u"][1]
            if 0 < d < 2 * s and -2 * a["L"] < t < 3 * a["L"] and (best is None or d < best):
                best = d
        if best is not None and best < 0.97 * s:
            a["delta"] = (s - best) / 2
    moves = {}
    for ci, c in enumerate(glyph.contours):
        pts = list(c.points)
        n = len(pts)
        for i, p in enumerate(pts):
            if p.type is None:
                continue
            adj = [sg for sg in segs if sg["ci"] == ci and (sg["i"] == i or sg["j"] == i)]
            if not any(sg["delta"] for sg in adj):
                continue
            if len(adj) == 2:
                (a1, b1), (a2, b2) = adj[0]["n"], adj[1]["n"]
                det = a1 * b2 - a2 * b1
                if abs(det) > 0.2:
                    d1, d2 = adj[0]["delta"], adj[1]["delta"]
                    moves[(ci, i)] = ((d1 * b2 - d2 * b1) / det, (a1 * d2 - a2 * d1) / det)
                    continue
            sg = max(adj, key=lambda s_: s_["delta"])
            moves[(ci, i)] = (sg["n"][0] * sg["delta"], sg["n"][1] * sg["delta"])
    for (ci, i), (mx, my) in moves.items():
        p = glyph.contours[ci].points[i]
        p.x, p.y = round(p.x + mx, 2), round(p.y + my, 2)


# Build exactly like terminal.prepare does for one master, with the two new steps.
dots = [(n, i) for n, i in T.find_dots(f) if n not in ("question", "questiondown")]
T.KEEP_JBM_CURVES = ()                     # monoline for all letters, joins fixed below
T.base_edits(f, STEM)
keep = set("bdpqrmhn")
plans = {g.name: T.plan_corners(g, STEM) for g in f if T.csl_strokes(f, g) and g.name not in keep}
for g in f:
    base = g.name.split(".")[0]
    if base in JOIN_LETTERS:
        xs = fix_joins(g)
        tighten_stem_corners(g, xs, (T.CORNER_RADIUS - 1) * STEM)
    if g.name in plans:
        T.apply_corners(g, plans[g.name], STEM, f.info)
    elif not T.keeps_round(g.name):
        T.square_curves(g, T.SQUARENESS)
    cat = T._category(f, g)
    if cat.startswith("L") or cat == "Nd":
        thicken_diagonals(g, STEM)
for name, idx in dots:
    T.square_dot(f[name].contours[idx])
trim = T.STROKE_TRIM / 2 * STEM
for g in f:
    if T.tiles(f, g):
        continue
    if T._category(f, g).startswith(T.FLAT_CATEGORIES):
        T.flatten_overshoot(g, f.info)
    T.trim_strokes(g, trim)
    T.restore_zones(g, f.info, trim)
T.slashed_zero_default(f)
f.info.familyName = f.info.styleMapFamilyName = FAMILY
f.info.styleName = "Regular"
f.info.openTypeNamePreferredFamilyName = FAMILY
f.info.postscriptFontName = FAMILY.replace(" ", "") + "-Regular"
f.info.postscriptFullName = FAMILY + " Regular"
compileTTF(f, removeOverlaps=True).save(OUT)
print("built", OUT)
