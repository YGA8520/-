#!/usr/bin/env python3
"""Sanity checks for the built fonts."""
import glob
import os
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HEBREW = list(range(0x05D0, 0x05EB))
NIQQUD = list(range(0x05B0, 0x05BE)) + [0x05BF, 0x05C1, 0x05C2, 0x05C7, 0x05BC]
PUNCT = [ord(c) for c in " .,:;!?-()[]{}/\"'+=*0123456789"] + [0x05BE, 0x05C3, 0x05F3, 0x05F4, 0x2013, 0x2014,
                                                               0x2018, 0x2019, 0x201C, 0x201D, 0xAB, 0xBB, 0x2026]
problems = 0


def bad(path, msg):
    global problems
    problems += 1
    print(f"  ! {os.path.basename(path)}: {msg}")


for path in sorted(glob.glob(os.path.join(ROOT, "fonts", "*.ttf"))):
    f = TTFont(path)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    name = f["name"].getDebugName(4)
    print(f"{name}: {len(f.getGlyphOrder())} glyphs, wght {f['OS/2'].usWeightClass}")
    for cp in HEBREW + NIQQUD + PUNCT:
        if cp not in cmap:
            bad(path, f"missing U+{cp:04X}")
    glyf = f["glyf"]
    hmtx = f["hmtx"]
    for gname in f.getGlyphOrder():
        g = glyf[gname]
        bp = BoundsPen(gs)
        gs[gname].draw(bp)
        if g.numberOfContours > 0:
            xmin, ymin, xmax, ymax = bp.bounds
            if ymin < -420 or ymax > 1150:
                bad(path, f"{gname} vertical overflow {ymin}..{ymax}")
            if hmtx[gname][0] == 0 and gname not in [n for n in f.getGlyphOrder() if f['GDEF'].table.GlyphClassDef.classDefs.get(n) == 3]:
                bad(path, f"{gname} has outlines but zero advance")
            if g.numberOfContours < 0:
                bad(path, f"{gname} composite")
            coords = g.coordinates
            if len(coords) > 900:
                bad(path, f"{gname} has {len(coords)} points")
    # letters must have a sensible advance
    for cp in HEBREW:
        adv = hmtx[cmap[cp]][0]
        if not 150 < adv < 1000:
            bad(path, f"U+{cp:04X} advance {adv}")
    if "GPOS" not in f or "GDEF" not in f:
        bad(path, "missing GPOS/GDEF")
    for tag in ("cmap", "glyf", "head", "hhea", "hmtx", "maxp", "name", "OS/2", "post", "gasp", "loca"):
        if tag not in f:
            bad(path, f"missing table {tag}")

print("OK" if not problems else f"{problems} problem(s)")
sys.exit(1 if problems else 0)
