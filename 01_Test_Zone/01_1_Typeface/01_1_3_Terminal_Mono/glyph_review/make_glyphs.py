#!/usr/bin/env python3
"""Write glyphs.json for the glyph review page: every character the designer's CSL Terminal V4
draws, with how differently it is shaped in CSL Terminal v2 (modified JetBrains Mono).

shape_diff compares the two glyphs after scaling each to its own ink box (so CSL's lower
x-height and wider letters don't count), size_diff compares them as typeset at the same em.
Both are 1 - IoU of the rendered ink, 0 = identical, 1 = no overlap.

Usage (repo root): python 01_Test_Zone/01_1_Typeface/01_1_3_Terminal_Mono/glyph_review/make_glyphs.py
"""
import json
import unicodedata
from pathlib import Path

import numpy as np
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CSL = HERE.parent / "CSL4_TERMINAL_0011.ttf"
OURS = REPO / "03_Branding_Assets/03_02_Typefaces/02_Internal/CSL_Terminal.ttf"
SIZE = 400
BOX = 200


def mask(font, ch):
    im = Image.new("L", (SIZE, int(SIZE * 1.6)))
    ImageDraw.Draw(im).text((0, int(SIZE * 1.2)), ch, font=font, fill=255, anchor="ls")
    return np.asarray(im) > 127


def boxed(m):
    ys, xs = np.nonzero(m)
    if not len(xs):
        return np.zeros((BOX, BOX), bool)
    crop = Image.fromarray(m[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype("uint8") * 255)
    return np.asarray(crop.resize((BOX, BOX), Image.BILINEAR)) > 127


def diff(a, b):
    union = (a | b).sum()
    return round(1 - (a & b).sum() / union, 3) if union else 0.0


def category(ch):
    cat = unicodedata.category(ch)
    if cat == "Ll":
        return "lowercase"
    if cat == "Lu":
        return "uppercase"
    if cat == "Nd":
        return "digits"
    if cat.startswith("P"):
        return "punctuation"
    return "symbols"


def main():
    csl = TTFont(CSL)
    cmap, gs = csl.getBestCmap(), csl.getGlyphSet()
    fc, fo = ImageFont.truetype(str(CSL), SIZE), ImageFont.truetype(str(OURS), SIZE)
    ours = TTFont(OURS).getBestCmap()
    out = []
    for u in sorted(cmap):
        pen = BoundsPen(gs)
        gs[cmap[u]].draw(pen)
        ch = chr(u)
        if not pen.bounds or u not in ours or ch.isspace():
            continue
        a, b = mask(fc, ch), mask(fo, ch)
        out.append({
            "char": ch,
            "code": f"U+{u:04X}",
            "name": unicodedata.name(ch, "").title(),
            "category": category(ch),
            "shape_diff": diff(boxed(a), boxed(b)),
            "size_diff": diff(a, b),
        })
    (HERE / "glyphs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} glyphs -> {HERE / 'glyphs.json'}")


if __name__ == "__main__":
    main()
