#!/usr/bin/env python3
"""Where CSL Terminal V4 takes chunks out, and whether CSL Terminal v2's base is ready there.

A V4 chunk is a concave half-pixel fillet on an outer contour; its removed square sits at a
corner tagged B/M/T (bottom, middle, top of the glyph) and L/R. v2 is ready for a chunk at a
corner if that corner is a rebuilt CSL corner pair (outer corner + counter corner, even stroke).
Writes chunks.json. Run inside `nix develop` (imports terminal.py).
"""
import json
import sys
from pathlib import Path

import ufoLib2
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "03_Branding_Assets/03_02_Typefaces/00_Sources"))
import terminal as T  # noqa: E402

V4 = HERE.parent / "CSL4_TERMINAL_0011.ttf"
MARGIN = 120                                # V4 units from the top/bottom that count as B/T

# Readability tiers (judgement, see the review page): which chunks to try first.
TIERS = {
    "first": "o c e s u O C S U 0",
    "after": "G J D B Q 5 6 8 3 ? g j",
    "base work first": "b d p q h m n r R 2 9",
}


def v4_chunks(font, ch):
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    name = cmap[ord(ch)]
    rec = RecordingPen()
    gs[name].draw(rec)
    bounds = BoundsPen(gs)
    gs[name].draw(bounds)
    x0, y0, x1, y1 = bounds.bounds
    contours, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            contours.append(cur)
            cur = []
    tags = set()
    for ops in contours:
        area = AreaPen()
        for op, args in ops:
            getattr(area, op)(*args)
        if area.value >= 0:                 # TrueType outer contours are clockwise
            continue
        pos = None
        for op, args in ops:
            if op == "qCurveTo" and pos is not None:
                s, e = pos, args[-1]
                if 35 <= abs(e[0] - s[0]) <= 60 and 35 <= abs(e[1] - s[1]) <= 60:
                    ix, iy = (e[0], s[1]) if abs(args[0][1] - s[1]) < 1 else (s[0], e[1])
                    for sx in (-1, 1):
                        for sy in (-1, 1):
                            pen = PointInsidePen(None, (ix + sx * 30, iy + sy * 30))
                            for o, a in ops:
                                getattr(pen, o)(*a)
                            if pen.getResult() or (ix - (x0 + x1) / 2) * sx <= 0:
                                continue
                            yq = iy + sy * 50
                            v = "B" if yq < y0 + MARGIN else "T" if yq > y1 - MARGIN else "M"
                            tags.add(v + ("L" if sx < 0 else "R"))
            if args:
                pos = args[-1]
    return sorted(tags)


def v2_pairs(ufo, glyph):
    if not T.csl_strokes(ufo, glyph) or not glyph.contours:
        return None
    pts = [p for c in glyph.contours for p in c]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    xy = [[(p.x, p.y) for p in c.points] for c in glyph.contours]
    tags = set()
    for (ci, i), _ in T.plan_corners(glyph, ufo.info.postscriptStemSnapV[0]):
        c = T.corner_geometry(xy[ci], ("arc", i))[0]
        v = "B" if c[1] < y0 + MARGIN * 0.9 else "T" if c[1] > y1 - MARGIN * 0.9 else "M"
        tags.add(v + ("L" if c[0] < (x0 + x1) / 2 else "R"))
    return sorted(tags)


def main():
    v4 = TTFont(V4)
    master = REPO / "03_Branding_Assets/03_02_Typefaces/00_Sources/CSL_Terminal/upstream/JetBrainsMono.glyphs"
    tmp = Path("/tmp/csl-chunk-readiness")
    tmp.mkdir(exist_ok=True)
    import glyphsLib
    glyphsLib.build_masters(str(master), str(tmp))
    ufo = ufoLib2.Font.open(tmp / "JetBrainsMono-Regular.ufo")
    T.base_edits(ufo, ufo.info.postscriptStemSnapV[0])
    by_char = {chr(u): g for g in ufo for u in g.unicodes}
    tier_of = {c: t for t, chars in TIERS.items() for c in chars.split()}
    out = []
    for g in json.loads((HERE / "glyphs.json").read_text()):
        ch = g["char"]
        chunks = v4_chunks(v4, ch)
        if not chunks or ch not in by_char:
            continue
        glyph = by_char[ch]
        if not glyph.contours and glyph.components:
            glyph = ufo[glyph.components[0].baseGlyph]
        pairs = v2_pairs(ufo, glyph)
        ready = [t for t in chunks if pairs and t in pairs]
        out.append({"char": ch, "code": g["code"], "v4": chunks, "v2_corners": pairs,
                    "ready": ready, "missing": [t for t in chunks if t not in ready],
                    "tier": tier_of.get(ch, "skip")})
    (HERE / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for r in out:
        print(f"{r['char']}  V4 {r['v4']}  ready {r['ready']}  missing {r['missing']}  -> {r['tier']}")


if __name__ == "__main__":
    main()
