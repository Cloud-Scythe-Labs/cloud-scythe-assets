#!/usr/bin/env python3
"""Compile the CSL fonts into release binaries.

Usage: python build.py [CSL_Display CSL_Terminal ...]   (default: all fonts)

The four branding fonts compile from their UFO sources (OTF + WOFF2). Naming and metrics come
from each UFO's fontinfo.plist. head.modified is taken from $SOURCE_DATE_EPOCH, or falls back to
head.created, so rebuilding unchanged sources yields byte-identical files.

CSL_Terminal is a modified JetBrains Mono, built by terminal.py from the vendored upstream
sources in CSL_Terminal/upstream (variable + static TTF, WOFF2).
"""

import io
import os
import sys
from pathlib import Path

import compreffor
import ufo2ft
import ufoLib2
from fontTools.ttLib import TTFont
from ufo2ft.constants import CFFOptimization

SOURCES = Path(__file__).resolve().parent
TYPEFACES = SOURCES.parent

# font -> (output folder, outline format of the file proof.py reads)
FONTS = {
    "CSL_Display": ("01_Branding", "otf"),
    "CSL_Mono": ("01_Branding", "otf"),
    "CSL_Dot_Display": ("01_Branding", "otf"),
    "CSL_Dot_Mono": ("01_Branding", "otf"),
    "CSL_Terminal": ("02_Internal", "ttf"),     # proofs the static Regular
}

MAC_EPOCH_DIFF = 2082844800  # seconds between 1904-01-01 and 1970-01-01


def compile_font(ufo):
    # roundTolerance=0 keeps the fractional corner-radius coordinates
    # (encoded as 16.16 fixed in the charstrings) instead of rounding them.
    # optimizeCFF=NONE: ufo2ft's specializer merges collinear lines and
    # drops lone-point contours, i.e. it changes the point structure.
    return ufo2ft.compileOTF(
        ufo,
        roundTolerance=0,
        optimizeCFF=CFFOptimization.NONE,
        useProductionNames=False,
    )


def subroutinize(font):
    # compreffor reuses the existing charstring tokens, so outlines stay
    # exact (cffsubr, ufo2ft's default, re-encodes fixed-point values lossily).
    buf = io.BytesIO()
    font.save(buf)
    font = TTFont(buf, recalcTimestamp=False)
    compreffor.compress(font)
    return font


def finalize(font, ufo):
    # ufo2ft derives nameID 4 from the typographic names
    # ("Cloud Scythe Labs Display"); the full name is the legacy family name.
    name = font["name"]
    for record in name.names:
        if record.nameID == 4:
            record.string = ufo.info.postscriptFullName

    head = font["head"]
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    head.modified = int(epoch) + MAC_EPOCH_DIFF if epoch else head.created
    font.recalcTimestamp = False


def build(stem):
    if stem == "CSL_Terminal":
        import terminal

        terminal.build()
        return
    folder, fmt = FONTS[stem]
    ufo = ufoLib2.Font.open(SOURCES / f"{stem}.ufo")
    font = compile_font(ufo)
    finalize(font, ufo)

    out = TYPEFACES / folder / stem
    out.parent.mkdir(parents=True, exist_ok=True)
    # WOFF2 keeps plain charstrings: Brotli compresses them better than subroutines.
    font.flavor = "woff2"
    font.save(out.with_suffix(".woff2"))
    font.flavor = None
    subroutinize(font).save(out.with_suffix(f".{fmt}"))
    print(f"{stem}: {out.relative_to(TYPEFACES)}.{{{fmt},woff2}}")


def main(argv):
    stems = argv or list(FONTS)
    unknown = [s for s in stems if s not in FONTS]
    if unknown:
        sys.exit(f"unknown font(s): {', '.join(unknown)}; choose from {', '.join(FONTS)}")
    for stem in stems:
        build(stem)


if __name__ == "__main__":
    main(sys.argv[1:])
