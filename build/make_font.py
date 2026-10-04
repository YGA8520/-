#!/usr/bin/env python3
"""Build the Nusach Hebrew font family (static TTF, several weights).

    python3 build/make_font.py [Regular Bold ...]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

import glyphlib as gl
from glyphlib import Metrics, finish, sweep
from letters import LETTERS
import extras

FAMILY = "Nusach"
VERSION = "1.000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

# name, wght, nib long side, nib short side, nib angle, corner rounding, dot radius
WEIGHTS = [
    Metrics("Light", 300, 78, 27, 68, 4, 34),
    Metrics("Regular", 400, 108, 38, 68, 5, 40),
    Metrics("Medium", 500, 126, 49, 68, 6, 45),
    Metrics("Bold", 700, 148, 66, 68, 7, 52),
    Metrics("Black", 900, 172, 88, 68, 8, 60),
]


def glyph_geometry(m, paths, shapes):
    from shapely.geometry import box
    from shapely.ops import unary_union
    nib = m.nib()
    parts = []
    for p in paths:
        if isinstance(p, dict):
            g = gl.sweep_var(p, nib)
        elif isinstance(p, tuple):
            pts, (y0, y1) = p
            g = sweep(gl.densify(pts, 5.0), nib).intersection(box(-gl.INF, y0, gl.INF, y1))
        else:
            g = sweep(gl.densify(p, 5.0), nib)
        parts.append(g)
    parts += shapes
    return finish(unary_union(parts), m.rnd)


class Glyph:
    def __init__(self, name, unicode, geom, adv, anchors=None, is_mark=False):
        self.name, self.unicode, self.geom, self.adv = name, unicode, geom, adv
        self.anchors = anchors or {}
        self.is_mark = is_mark
        self.mark_class = None


def positioned(m, name, unicode, paths, shapes, lsb, rsb, anchor_fn=None):
    g = glyph_geometry(m, paths, shapes)
    minx, miny, maxx, maxy = g.bounds
    extra = max(0.0, (m.V - 67) * 0.22)      # heavier weights breathe a little more
    lsb, rsb = lsb + extra, rsb + extra
    from shapely import affinity
    g = affinity.translate(g, xoff=lsb - minx)
    adv = round((maxx - minx) + lsb + rsb)
    anchors = anchor_fn(m, g, adv) if anchor_fn else {}
    return Glyph(name, unicode, g, adv, anchors)


def collect(m):
    glyphs = []
    for name, (fn, uni, lsb, rsb) in LETTERS.items():
        paths, shapes = fn(m)
        glyphs.append(positioned(m, name, uni, paths, shapes, lsb, rsb, extras.letter_anchors(name)))
    glyphs += extras.collect_extras(m, positioned, glyph_geometry, Glyph)
    glyphs += digraphs(glyphs)
    return glyphs


def digraphs(glyphs):
    """Yiddish ligature letters װ ױ ײ built from vav / yod."""
    from shapely import affinity
    from shapely.ops import unary_union
    by = {g.name: g for g in glyphs}
    out = []
    for name, uni, first, second in (("vavvav", 0x05F0, "vav", "vav"),
                                     ("vavyod", 0x05F1, "vav", "yod"),
                                     ("yodyod", 0x05F2, "yod", "yod")):
        a, b = by[first], by[second]        # a is the right-hand letter in RTL
        tight = 28
        shift = b.adv - tight
        geom = unary_union([b.geom, affinity.translate(a.geom, xoff=shift)])
        out.append(Glyph(name, uni, geom, round(shift + a.adv),
                         {"bot": (shift / 2 + a.adv / 2, -52), "holam": (shift / 2 + a.adv / 2, 660 + 52),
                          "mid": (shift / 2 + a.adv / 2, 300)}))
    return out


def build(m):
    glyphs = collect(m)
    order = [".notdef", "space", "nbspace"] + [g.name for g in glyphs]
    # de-duplicate (extras may reuse names)
    seen, glyph_order = set(), []
    for n in order:
        if n not in seen:
            seen.add(n)
            glyph_order.append(n)

    fb = FontBuilder(gl.UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)

    cmap = {0x20: "space", 0xA0: "nbspace"}
    for g in glyphs:
        if g.unicode:
            cmap[g.unicode] = g.name
    fb.setupCharacterMap(cmap)

    pens, metrics = {}, {}
    # .notdef: simple frame
    from shapely.geometry import box
    nd = box(60, 0, 440, 660).difference(box(60 + m.V, m.H, 440 - m.V, 660 - m.H))
    pen = TTGlyphPen(None)
    gl.draw_to_pen(nd, pen)
    pens[".notdef"] = pen.glyph()
    metrics[".notdef"] = (500, 60)
    for n, adv in (("space", 260), ("nbspace", 260)):
        pens[n] = TTGlyphPen(None).glyph()
        metrics[n] = (adv, 0)
    for g in glyphs:
        pen = TTGlyphPen(None)
        gl.draw_to_pen(g.geom, pen)
        pens[g.name] = pen.glyph()
        minx = g.geom.bounds[0] if not g.geom.is_empty else 0
        metrics[g.name] = (g.adv if not g.is_mark else 0, round(minx))
    fb.setupGlyf(pens)
    fb.setupHorizontalMetrics(metrics)

    style = m.name
    is_bold = style == "Bold"
    ribbi = style in ("Regular", "Bold")
    family_legacy = FAMILY if ribbi else f"{FAMILY} {style}"
    sub_legacy = style if ribbi else "Regular"
    names = {
        "copyright": "Original design. Free to use, including commercial use.",
        "familyName": family_legacy,
        "styleName": sub_legacy,
        "uniqueFontIdentifier": f"{FAMILY}-{style};{VERSION}",
        "fullName": f"{FAMILY} {style}",
        "version": f"Version {VERSION}",
        "psName": f"{FAMILY}-{style}",
        "typographicFamily": FAMILY,
        "typographicSubfamily": style,
    }
    fb.setupNameTable(names)
    he_style = {"Light": "קל", "Regular": "רגיל", "Medium": "בינוני", "Bold": "מודגש", "Black": "שחור"}[style]
    nt = fb.font["name"]
    HE = 0x040D
    nt.setName("נוסח" if ribbi else f"נוסח {he_style}", 1, 3, 1, HE)
    nt.setName(he_style if ribbi else "רגיל", 2, 3, 1, HE)
    nt.setName(f"נוסח {he_style}", 4, 3, 1, HE)
    nt.setName("נוסח", 16, 3, 1, HE)
    nt.setName(he_style, 17, 3, 1, HE)
    fb.setupOS2(
        version=4,
        sTypoAscender=950, sTypoDescender=-350, sTypoLineGap=0,
        usWinAscent=1150, usWinDescent=450,
        sxHeight=gl.TOP, sCapHeight=gl.TOP,
        usWeightClass=m.wght, usWidthClass=5,
        fsType=0, achVendID="NSCH",
        fsSelection=(0x20 if is_bold else 0x40 if style == "Regular" else 0) | 0x80,
        ulUnicodeRange1=0, ulUnicodeRange2=0, ulUnicodeRange3=0, ulUnicodeRange4=0,
        ulCodePageRange1=(1 << 5) | 1, ulCodePageRange2=0,
    )
    fb.setupHorizontalHeader(ascent=950, descent=-350, lineGap=0)
    fb.setupPost(isFixedPitch=0, underlinePosition=-120, underlineThickness=round(m.H * 0.6))
    fb.font["head"].macStyle = 0x1 if is_bold else 0
    r = fb.font["OS/2"]
    r.ulUnicodeRange1 |= (1 << 0)            # Basic Latin (punctuation / digits)
    r.ulUnicodeRange1 |= (1 << 11)           # Hebrew

    fea = extras.feature_code(glyphs)
    tmp = fb.font
    addOpenTypeFeaturesFromString(tmp, fea)
    # unhinted outlines: ask rasterisers to smooth at every size
    from fontTools.ttLib import newTable
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000F}
    tmp["gasp"] = gasp

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{FAMILY}-{style}.ttf")
    tmp.save(path)
    return path


def main():
    wanted = set(sys.argv[1:])
    for m in WEIGHTS:
        if wanted and m.name not in wanted:
            continue
        p = build(m)
        print("built", p, f"(V={m.V:.0f}, H={m.H:.0f})")


if __name__ == "__main__":
    main()
