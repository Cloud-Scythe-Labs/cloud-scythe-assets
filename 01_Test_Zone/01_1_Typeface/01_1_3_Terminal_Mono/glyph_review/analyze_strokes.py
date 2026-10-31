#!/usr/bin/env python3
"""Stroke-width analysis of CSL Terminal v2 against CSL Terminal V4, for the chunking review.

For every character both fonts draw, at the same em: the ink is skeletonised and each skeleton
point gets the stroke width there (twice the distance to the nearest edge). Stroke ends and
joins are trimmed off (they are naturally thin / thick), so what is left reads the stroke
itself. Writes strokes.json (per glyph: median width, thinnest 5%, share of the stroke thinner
than 85% of the median = taper) and heat/<code>-{csl,v2}.png heatmaps (red = thinner, blue =
thicker than the glyph's median stroke).

Needs numpy, scipy, scikit-image, Pillow, fontTools.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from skimage.morphology import skeletonize

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
FONTS = {
    "csl": HERE.parent / "CSL4_TERMINAL_0011.ttf",
    "v2": REPO / "03_Branding_Assets/03_02_Typefaces/02_Internal/CSL_Terminal.ttf",
}
EM = 1000                                   # px per em: 1 px = 1 unit at UPM 1000
THIN, THICK = 0.85, 1.15


def mask(font, ch):
    im = Image.new("L", (int(EM * 0.8), int(EM * 1.4)))
    ImageDraw.Draw(im).text((int(EM * 0.1), int(EM * 1.05)), ch, font=font, fill=255, anchor="ls")
    return np.asarray(im) > 127


def analyse(m):
    if not m.any():
        return None, None
    dist = ndimage.distance_transform_edt(m)
    skel = skeletonize(m)
    # neighbours per skeleton pixel: 1 = end, >= 3 = join
    nb = ndimage.convolve(skel.astype(int), np.ones((3, 3), int), mode="constant") - 1
    ends = skel & (nb == 1)
    joins = skel & (nb >= 3)
    width = 2 * dist
    core = skel.copy()
    # drop the stretch of skeleton within one stroke width of an end or a join
    reach = np.median(width[skel]) if skel.any() else 1
    near = ndimage.binary_dilation(ends | joins, iterations=max(1, int(reach * 0.75)))
    core &= ~near
    w = width[core] if core.any() else width[skel]
    med = float(np.median(w))
    stats = {
        "median": round(med, 1),
        "p05": round(float(np.percentile(w, 5)), 1),
        "taper": round(float((w < THIN * med).mean()), 3),
        "bulge": round(float((w > THICK * med).mean()), 3),
    }
    # heatmap: each ink pixel takes the width of its nearest skeleton pixel
    _, (iy, ix) = ndimage.distance_transform_edt(~skel, return_indices=True)
    rel = width[iy, ix] / med
    img = np.zeros(m.shape + (3,), np.uint8)
    img[:] = (8, 9, 12)
    ok = m & (rel >= THIN) & (rel <= THICK)
    img[ok] = (226, 230, 238)
    t = np.clip((THIN - rel) / 0.35, 0, 1)
    thin = m & (rel < THIN)
    img[thin] = np.stack([np.full(thin.sum(), 255), (200 - 170 * t[thin]), (200 - 170 * t[thin])], -1).astype(np.uint8)
    k = np.clip((rel - THICK) / 0.5, 0, 1)
    thick = m & (rel > THICK)
    img[thick] = np.stack([(200 - 140 * k[thick]), (210 - 90 * k[thick]), np.full(thick.sum(), 255)], -1).astype(np.uint8)
    return stats, Image.fromarray(img)


def main():
    glyphs = json.loads((HERE / "glyphs.json").read_text())
    fonts = {k: ImageFont.truetype(str(p), EM) for k, p in FONTS.items()}
    (HERE / "heat").mkdir(exist_ok=True)
    out = []
    for g in glyphs:
        row = {"char": g["char"], "code": g["code"], "category": g["category"]}
        for key, font in fonts.items():
            stats, img = analyse(mask(font, g["char"]))
            row[key] = stats
            if img:
                img.resize((img.width // 4, img.height // 4), Image.LANCZOS).save(
                    HERE / "heat" / f"{g['code']}-{key}.png")
        out.append(row)
    (HERE / "strokes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} glyphs -> strokes.json, heat/")


if __name__ == "__main__":
    main()
