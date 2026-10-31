#!/usr/bin/env python3
"""Render a PNG proof of each built font into proofs/.

Usage: python proof.py [CSL_Display CSL_Terminal ...]   (default: all fonts)

Proofs the compiled binaries (run build.py first): a header with naming and
metrics, a waterfall of sample text, and a grid of every glyph in glyph order
with its name and codepoint. Cells show the advance box, baseline, x-height
and cap-height.
"""

import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from build import FONTS, SOURCES, TYPEFACES

OUT = SOURCES / "proofs"

SAMPLES = [
    "The quick brown fox jumps over the lazy dog.",
    "SPHINX OF BLACK QUARTZ, JUDGE MY VOW! 0123456789",
    "{}[]()<>/\\|@#$%^&*_+-=~`'\";:,.?  ←↑→↓",
]
WATERFALL = [12, 16, 24, 32, 48, 72]

COLUMNS = 16
GLYPH_PX = 72  # pixels per em in the glyph grid
CELL_W = 112
MARGIN = 40
LABEL_H = 34

INK = (0, 0, 0)
PAPER = (255, 255, 255)
GUIDE = (205, 215, 235)
BOX = (235, 235, 235)
NOTE = (110, 110, 110)
UNENCODED = 0xE000  # private-use codepoint, unmapped in all CSL fonts -> renders .notdef


def load_font(path, size):
    # BASIC layout maps each character straight through the cmap, so control
    # characters and unshaped glyphs render as-is.
    return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.BASIC)


def draw_glyph(img, font, ch, x, baseline):
    mask, (ox, oy) = font.getmask2(ch, "L", anchor="ls")
    if mask.size[0] and mask.size[1]:
        img.paste(INK, (int(x) + ox, int(baseline) + oy), Image.Image()._new(mask))


def proof(stem):
    folder, fmt = FONTS[stem]
    path = TYPEFACES / folder / f"{stem}.{fmt}"
    tt = TTFont(path)
    upm = tt["head"].unitsPerEm
    hhea, os2 = tt["hhea"], tt["OS/2"]
    cmap = tt.getBestCmap()
    if UNENCODED in cmap:
        sys.exit(f"{stem}: U+{UNENCODED:04X} is mapped; pick another codepoint for .notdef")
    charOf = {}
    for cp, name in sorted(cmap.items()):
        charOf.setdefault(name, chr(cp))
    charOf.setdefault(".notdef", chr(UNENCODED))
    order = tt.getGlyphOrder()
    advance = tt["hmtx"].metrics

    scale = GLYPH_PX / upm
    glyph_h = round((hhea.ascent - hhea.descent) * scale)
    cell_h = glyph_h + LABEL_H
    rows = -(-len(order) // COLUMNS)
    width = MARGIN * 2 + COLUMNS * CELL_W

    label = ImageFont.load_default(13)
    small = ImageFont.load_default(11)
    title = ImageFont.load_default(22)
    sample_fonts = {size: load_font(path, size) for size in WATERFALL}
    sample_rows = [(size, text) for size in WATERFALL for text in SAMPLES[:1]] + [
        (32, text) for text in SAMPLES[1:]
    ]
    waterfall_h = sum(round(s * (hhea.ascent - hhea.descent) / upm) + 8 for s, _ in sample_rows)
    header_h = 90
    height = MARGIN * 2 + header_h + waterfall_h + 30 + rows * cell_h

    img = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(img)

    # header
    name = tt["name"]
    y = MARGIN
    draw.text((MARGIN, y), f"{name.getDebugName(4)}  ({name.getDebugName(6)})", font=title, fill=INK)
    y += 32
    draw.text((MARGIN, y), (
        f"{name.getDebugName(5)} · family '{name.getDebugName(1)}' / '{name.getDebugName(2)}' · "
        f"typographic '{name.getDebugName(16)}' / '{name.getDebugName(17)}' · {path.name}"
    ), font=label, fill=NOTE)
    y += 20
    draw.text((MARGIN, y), (
        f"UPM {upm} · ascender {hhea.ascent} · descender {hhea.descent} · lineGap {hhea.lineGap} · "
        f"capHeight {os2.sCapHeight} · xHeight {os2.sxHeight} · {len(order)} glyphs · "
        f"{'monospaced' if tt['post'].isFixedPitch else 'proportional'}"
    ), font=label, fill=NOTE)
    y = MARGIN + header_h

    # waterfall
    for size, text in sample_rows:
        line_h = round(size * (hhea.ascent - hhea.descent) / upm)
        baseline = y + round(size * hhea.ascent / upm)
        draw.text((MARGIN, baseline), f"{size}", font=small, fill=NOTE, anchor="ls")
        draw.text((MARGIN + 36, baseline), text, font=sample_fonts[size], fill=INK, anchor="ls")
        y += line_h + 8
    y += 30

    # glyph grid
    glyph_font = load_font(path, GLYPH_PX)
    guides = [0, os2.sxHeight, os2.sCapHeight]
    for i, glyph in enumerate(order):
        cx = MARGIN + (i % COLUMNS) * CELL_W
        cy = y + (i // COLUMNS) * cell_h
        baseline = cy + round(hhea.ascent * scale)
        adv = advance[glyph][0] * scale
        x0 = cx + (CELL_W - adv) / 2
        draw.rectangle([cx, cy, cx + CELL_W - 1, cy + cell_h - 1], outline=BOX)
        draw.rectangle([x0, cy + 4, x0 + adv, cy + glyph_h], fill=(248, 248, 248))
        for g in guides:
            gy = baseline - round(g * scale)
            draw.line([cx + 4, gy, cx + CELL_W - 5, gy], fill=GUIDE)
        ch = charOf.get(glyph)
        if ch is None:
            draw.text((cx + CELL_W / 2, baseline), "unencoded", font=small, fill=NOTE, anchor="ms")
        else:
            draw_glyph(img, glyph_font, ch, x0, baseline)
        code = f"U+{ord(ch):04X}" if ch and glyph != ".notdef" else "unencoded"
        draw.text((cx + 4, cy + glyph_h + 3), glyph[:17], font=label, fill=INK)
        draw.text((cx + 4, cy + glyph_h + 18), code, font=small, fill=NOTE)

    OUT.mkdir(exist_ok=True)
    out = OUT / f"{stem}.png"
    img.save(out, optimize=True)
    print(f"{stem}: {out.relative_to(SOURCES)}")


def main(argv):
    stems = argv or list(FONTS)
    unknown = [s for s in stems if s not in FONTS]
    if unknown:
        sys.exit(f"unknown font(s): {', '.join(unknown)}; choose from {', '.join(FONTS)}")
    for stem in stems:
        proof(stem)


if __name__ == "__main__":
    main(sys.argv[1:])
