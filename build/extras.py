"""Digits, punctuation, niqqud marks and the OpenType feature code."""
import math

from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

from glyphlib import (TOP as T, DESC, S, arc, bez, diamond, join, line, sweep, densify, finish)
from letters import hb, vb, _w

GAP_BELOW = 52     # distance of niqqud below the baseline
GAP_ABOVE = 52     # distance of marks above the letter top


# =====================================================================  anchors
def letter_anchors(name):
    narrow_top = {"vav", "zayin", "yod", "nun_final"}

    def fn(m, g, adv):
        x0, y0, x1, y1 = g.bounds
        w = x1 - x0
        cx = (x0 + x1) / 2
        a = {
            "bot": (cx, -GAP_BELOW),
            "bot_l": (x0 + 0.26 * w, -GAP_BELOW),
            "holam": (x0 + 0.22 * w, T + GAP_ABOVE),
            "mid": (cx, 0.46 * T),
            "top": (cx, T + GAP_ABOVE),
        }
        if name in narrow_top:
            a["holam"] = (cx, T + GAP_ABOVE)
        if name == "nun_final":
            a["bot"] = (cx, DESC - GAP_BELOW + 30)
            a["bot_l"] = (cx - 70, -GAP_BELOW)
        if name in ("kaf_final", "pe_final", "tsadi_final"):
            a["bot"] = (x0 + 0.38 * w, -GAP_BELOW)
        if name == "qof":
            a["bot"] = (x0 + 0.62 * w, -GAP_BELOW)
        if name == "yod":
            a["bot"] = (cx, 0.40 * T - GAP_BELOW + 14)
        if name == "lamed":
            a["holam"] = (x0 + 0.72 * w, T + GAP_ABOVE)
            a["top"] = (x0 + 0.72 * w, T + GAP_ABOVE)
            a["mid"] = (x0 + 0.62 * w, 0.58 * T)
        if name in ("vav",):
            a["mid"] = (x1 - m.V - 58, 0.50 * T)
        if name == "shin":
            a["shin_r"] = (x1 - m.V / 2, T + GAP_ABOVE)
            a["shin_l"] = (x0 + m.V / 2, T + GAP_ABOVE)
            a["holam"] = (x0 + 0.52 * w, T + GAP_ABOVE)
        return a
    return fn


# =====================================================================  helpers
def _dot(m, cx, cy, k=1.0):
    r = m.dots * k
    return diamond(cx, cy, r * 1.32, r * 1.52)


def _snib(m, s):
    return affinity.scale(m.nib(), s, s, origin=(0, 0))


def _sw(m, pts, s=1.0):
    return sweep(densify(pts, 8.0), _snib(m, s))


# =====================================================================  digits
def _digits(m):
    hv, hh = m.hv, m.hh
    tc, bc = T - hh, hh
    out = {}

    def ell(cx, cy, rx, ry, a0=0, a1=360):
        return arc(cx, cy, rx, ry, a0, a1, 48)

    W = _w(m, 470)
    rx, cx = W / 2 - hv, W / 2
    out["zero"] = ([ell(cx, T / 2, rx, (tc - bc) / 2)], [], 50, 50)

    W = _w(m, 300)
    xs = W - hv - 40
    out["one"] = ([S([(xs, tc), (xs, bc)], ymin=0, ymax=T, e0=m.H, e1=m.H),
                   S([(xs, tc), (hv + 8, tc - 150)], ymax=T, e0=m.H * 0.3)], [], 50, 50)

    W = _w(m, 440)
    rx, cx = W / 2 - hv, W / 2
    ry = (tc - bc) * 0.27
    out["two"] = ([join(arc(cx, tc - ry, rx, ry, 158, -38, 36),
                        line((cx + rx * math.cos(math.radians(-38)), tc - ry + ry * math.sin(math.radians(-38))),
                             (hv, bc)),
                        line((hv, bc), (W - hv, bc)))], [], 50, 50)

    W = _w(m, 440)
    rx, cx = W / 2 - hv, W / 2
    ry = (tc - bc) / 4
    out["three"] = ([join(arc(cx, tc - ry, rx, ry, 152, -90, 36), arc(cx, bc + ry, rx, ry, 90, -152, 36))],
                    [], 50, 50)

    W = _w(m, 480)
    xs = W * 0.68
    yb = 0.30 * T
    out["four"] = ([S([(xs, tc), (xs, bc)], ymin=0, ymax=T, e0=m.H, e1=m.H),
                    join(line((xs - 20, tc), (hv, yb)), line((hv, yb), (W - hv, yb)))], [], 50, 50)

    W = _w(m, 440)
    rx, cx = W / 2 - hv, W / 2
    ry = (tc - bc) * 0.29
    a_start = math.radians(18)
    b0 = (cx + rx * math.cos(a_start), bc + ry + ry * math.sin(a_start))
    out["five"] = ([join(line((W - hv, tc), (hv + 34, tc)), line((hv + 34, tc), (hv + 20, 0.52 * T)),
                         bez((hv + 20, 0.52 * T), (hv + 90, 0.64 * T), (W - hv - 4, 0.62 * T), b0),
                         arc(cx, bc + ry, rx, ry, 18, -150, 36))], [], 50, 50)

    W = _w(m, 450)
    rx, cx = W / 2 - hv, W / 2
    ry = (tc - bc) * 0.30
    loop = ell(cx, bc + ry, rx, ry)
    stem = bez((W - hv - 30, tc - 30), (cx, tc + 10), (hv + 4, 0.62 * T), (hv, bc + ry))
    out["six"] = ([loop, stem], [], 50, 50)
    out["_six_w"] = W

    W = _w(m, 440)
    out["seven"] = ([line((hv, tc), (W - hv, tc)),
                     S([(W - hv - 6, tc), (W * 0.36, bc)], ymin=0, ymax=T, e0=m.H * 0.3, e1=m.H)], [], 50, 50)

    W = _w(m, 460)
    rx, cx = W / 2 - hv, W / 2
    ryu = (tc - bc) * 0.22
    ryl = (tc - bc) * 0.28
    out["eight"] = ([ell(cx, tc - ryu, rx * 0.86, ryu), ell(cx, bc + ryl, rx, ryl)], [], 50, 50)
    return out


def _rotate_paths(paths, W):
    return [[(W - x, T - y) for x, y in p] for p in paths]


# =====================================================================  punctuation
def _punct(m):
    hv, hh = m.hv, m.hh
    out = {}
    dd = m.dots

    def comma_tail(x, y):
        return _sw(m, [(x + 2, y - dd * 0.4), (x - 34, y - 112)], 0.9)

    # name: (unicode, paths, shapes, lsb, rsb, scaled-sweeps)
    out["period"] = (0x2E, [], [_dot(m, 0, dd * 1.52)], 58, 58)
    out["comma"] = (0x2C, [], [_dot(m, 0, dd * 1.52), comma_tail(0, dd * 1.52)], 58, 58)
    out["colon"] = (0x3A, [], [_dot(m, 0, dd * 1.52), _dot(m, 0, 0.44 * T)], 58, 58)
    out["semicolon"] = (0x3B, [], [_dot(m, 0, 0.44 * T), _dot(m, 0, dd * 1.52), comma_tail(0, dd * 1.52)], 58, 58)
    out["sofpasuq"] = (0x05C3, [], [_dot(m, 0, dd * 1.52), _dot(m, 0, 0.44 * T)], 58, 58)
    out["middot"] = (0xB7, [], [_dot(m, 0, 0.36 * T)], 58, 58)
    out["bullet"] = (0x2022, [], [affinity.scale(_dot(m, 0, 0.38 * T, 2.0), 1, 1)], 70, 70)
    out["ellipsis"] = (0x2026, [], [_dot(m, 0, dd * 1.52), _dot(m, 170, dd * 1.52), _dot(m, 340, dd * 1.52)], 58, 58)

    # exclamation / question
    yd = dd * 1.52
    out["exclam"] = (0x21, [S([(0, T - hh), (0, 0.27 * T + hh)], ymin=0.27 * T, ymax=T, e0=m.H, e1=m.H)],
                     [_dot(m, 0, yd)], 60, 60)
    rx = 150
    ry = 165
    cy = T - hh - ry
    a_end = -36
    ex = rx * math.cos(math.radians(a_end))
    ey = cy + ry * math.sin(math.radians(a_end))
    q = join(arc(0, cy, rx, ry, 160, a_end, 36), bez((ex, ey), (ex * 0.35, ey - 90), (0, 0.46 * T), (0, 0.30 * T)))
    out["question"] = (0x3F, [S(q, ymax=T, e0=0)], [_dot(m, 0, yd)], 60, 60)

    # dashes
    out["hyphen"] = (0x2D, [hb(m, 0, 230, 0.40 * T + hh)], [], 56, 56)
    out["endash"] = (0x2013, [hb(m, 0, 440, 0.40 * T + hh)], [], 30, 30)
    out["emdash"] = (0x2014, [hb(m, 0, 800, 0.40 * T + hh)], [], 30, 30)
    out["maqaf"] = (0x05BE, [hb(m, 0, 340, 0.60 * T + hh)], [], 30, 30)

    # quotes
    def tick(x, y0, y1, lean=26):
        return _sw(m, [(x + lean, y1), (x - lean * 0.2, y0)], 0.85)

    out["quotesingle"] = (0x27, [], [tick(0, T - 190, T - 8)], 60, 60)
    out["quotedbl"] = (0x22, [], [tick(0, T - 190, T - 8), tick(110, T - 190, T - 8)], 60, 60)
    out["geresh"] = (0x05F3, [], [tick(0, T - 220, T - 8)], 60, 60)
    out["gershayim"] = (0x05F4, [], [tick(0, T - 220, T - 8), tick(120, T - 220, T - 8)], 60, 60)

    def comma_at(x, y, flip=False):
        d = _dot(m, x, y)
        t = _sw(m, [(x + 2, y - dd * 0.4), (x - 32, y - 104)], 0.85)
        g = unary_union([d, t])
        if flip:
            g = affinity.rotate(g, 180, origin=(x, y - 40))
        return g

    out["quoteright"] = (0x2019, [], [comma_at(0, T - 150)], 60, 60)
    out["quoteleft"] = (0x2018, [], [comma_at(0, T - 150 - 20, True)], 60, 60)
    out["quotedblright"] = (0x201D, [], [comma_at(0, T - 150), comma_at(120, T - 150)], 60, 60)
    out["quotedblleft"] = (0x201C, [], [comma_at(0, T - 170, True), comma_at(120, T - 170, True)], 60, 60)
    out["quotedblbase"] = (0x201E, [], [comma_at(0, dd * 1.4 + 40), comma_at(120, dd * 1.4 + 40)], 60, 60)

    # brackets
    def bracket(side, kind):
        top, bot = T + 70 - hh, -150 + hh
        w = 150
        if kind == "paren":
            mid = (top + bot) / 2
            half = (top - bot) / 2
            if side == "l":
                pts = arc(w * 0.9, mid, w * 0.9, half, 118, 242, 36)
            else:
                pts = arc(0, mid, w * 0.9, half, 62, -62, 36)
            return [pts]
        if kind == "square":
            if side == "l":
                return [[(w, top), (hv, top), (hv, bot), (w, bot)]]
            return [[(0, top), (w - hv, top), (w - hv, bot), (0, bot)]]
        if kind == "curly":
            mid = (top + bot) / 2
            if side == "l":
                return [join(line((w, top), (w * 0.62, top - 10)),
                             bez((w * 0.62, top - 10), (w * 0.45, top - 40), (w * 0.45, mid + 130), (w * 0.4, mid + 90)),
                             line((w * 0.4, mid + 90), (w * 0.4, mid + 40)),
                             bez((w * 0.4, mid + 40), (w * 0.3, mid + 10), (w * 0.2, mid), (hv, mid)),
                             bez((hv, mid), (w * 0.2, mid), (w * 0.3, mid - 10), (w * 0.4, mid - 40)),
                             line((w * 0.4, mid - 40), (w * 0.4, mid - 90)),
                             bez((w * 0.4, mid - 90), (w * 0.45, mid - 130), (w * 0.45, bot + 40), (w * 0.62, bot + 10)),
                             line((w * 0.62, bot + 10), (w, bot)))]
            p = bracket("l", "curly")[0]
            return [[(w - x, y) for x, y in p]]

    for nm, uni, side, kind in (("parenleft", 0x28, "l", "paren"), ("parenright", 0x29, "r", "paren"),
                                ("bracketleft", 0x5B, "l", "square"), ("bracketright", 0x5D, "r", "square"),
                                ("braceleft", 0x7B, "l", "curly"), ("braceright", 0x7D, "r", "curly")):
        out[nm] = (uni, bracket(side, kind), [], 56, 56)

    out["slash"] = (0x2F, [S([(300, T + 40), (0, -90)], e0=0, e1=0)], [], 40, 40)
    out["plus"] = (0x2B, [hb(m, 0, 340, 0.42 * T + hh),
                          S([(170, 0.42 * T + 150), (170, 0.42 * T - 150)], e0=0, e1=0)], [], 60, 60)
    out["equal"] = (0x3D, [hb(m, 0, 340, 0.50 * T + hh), hb(m, 0, 340, 0.30 * T + hh)], [], 60, 60)
    out["asterisk"] = (0x2A, [S([(0, T - 40), (0, T - 240)], e0=0, e1=0),
                              S([(-90, T - 80), (90, T - 200)], e0=0, e1=0),
                              S([(90, T - 80), (-90, T - 200)], e0=0, e1=0)], [], 70, 70)

    def chevron(flip):
        pts = [(110, T * 0.64), (0, T * 0.40), (110, T * 0.16)]
        pts2 = [(x + 120, y) for x, y in pts]
        if flip:
            pts = [(230 - x, y) for x, y in pts]
            pts2 = [(230 - x, y) for x, y in pts2]
        return [pts, pts2]
    out["guillemotleft"] = (0xAB, [_pp(p) for p in chevron(False)], [], 50, 50)
    out["guillemotright"] = (0xBB, [_pp(p) for p in chevron(True)], [], 50, 50)

    # percent / shekel are drawn separately below
    return out


def _pp(p):
    return p


# =====================================================================  marks
def _marks(m):
    """Mark geometry in local coordinates.  Below-marks hang from y=0 downward, the
    anchor is at the top centre; above-marks sit on y=0, anchor at the bottom centre."""
    dd = m.dots
    hy = dd * 1.52          # half height of a dot
    out = {}

    def below(geoms):
        g = unary_union(geoms)
        minx, miny, maxx, maxy = g.bounds
        return affinity.translate(g, -(minx + maxx) / 2, -maxy)

    def above(geoms):
        g = unary_union(geoms)
        minx, miny, maxx, maxy = g.bounds
        return affinity.translate(g, -(minx + maxx) / 2, -miny)

    def bar(w, y):
        return _sw(m, [(-w / 2, y), (w / 2, y)], 0.80)

    sp = 2.5 * hy
    sheva = [_dot(m, 0, 0), _dot(m, 0, -sp)]
    out["sheva"] = (0x05B0, below(sheva), "below")
    out["hiriq"] = (0x05B4, below([_dot(m, 0, 0)]), "below")
    out["tsere"] = (0x05B5, below([_dot(m, -dd * 1.9, 0), _dot(m, dd * 1.9, 0)]), "below")
    seg = [_dot(m, -dd * 1.9, 0), _dot(m, dd * 1.9, 0), _dot(m, 0, -sp)]
    out["segol"] = (0x05B6, below(seg), "below")
    out["patah"] = (0x05B7, below([bar(dd * 4.2, 0)]), "below")
    stem = _sw(m, [(0, 0), (0, -dd * 3.4)], 0.80)
    out["qamats"] = (0x05B8, below([bar(dd * 4.2, 0), stem]), "below")
    out["qamatsqatan"] = (0x05C7, out["qamats"][1], "below")

    def hataf(v):
        g = unary_union([affinity.translate(sheva[0], -dd * 2.6, 0), affinity.translate(sheva[1], -dd * 2.6, 0)]
                        + [affinity.translate(x, dd * 2.6 + dd * 0.4, 0) for x in v])
        return below([g])
    out["hatafsegol"] = (0x05B1, hataf(seg), "below")
    out["hatafpatah"] = (0x05B2, hataf([bar(dd * 3.4, 0)]), "below")
    out["hatafqamats"] = (0x05B3, hataf([bar(dd * 3.4, 0), _sw(m, [(0, 0), (0, -dd * 3.0)], 0.80)]), "below")
    qub = [_dot(m, -dd * 1.9 + i * dd * 1.9, -i * dd * 1.9) for i in range(3)]
    out["qubuts"] = (0x05BB, below(qub), "below")

    hol = _dot(m, 0, 0)
    out["holam"] = (0x05B9, above([hol]), "holam")
    out["holamhaser"] = (0x05BA, out["holam"][1], "holam")
    out["dagesh"] = (0x05BC, affinity.translate(_dot(m, 0, 0), 0, 0), "mid")
    out["shindot"] = (0x05C1, above([_dot(m, 0, 0)]), "shin")
    out["sindot"] = (0x05C2, above([_dot(m, 0, 0)]), "sin")
    mt = _sw(m, [(0, 0), (0, -dd * 4.0)], 0.80)
    out["meteg"] = (0x05BD, below([mt]), "meteg")
    out["rafe"] = (0x05BF, above([bar(dd * 3.6, 0)]), "rafe")
    return out


# =====================================================================  collection
def collect_extras(m, positioned, geometry, Glyph):
    glyphs = []

    d = _digits(m)
    sixw = d.pop("_six_w")
    names = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight"]
    for i, nm in enumerate(names):
        paths, shapes, lsb, rsb = d[nm]
        glyphs.append(positioned(m, nm, 0x30 + i, paths, shapes, lsb, rsb))
    # nine = six turned around
    paths, shapes, lsb, rsb = d["six"]
    glyphs.append(positioned(m, "nine", 0x39, _rotate_paths(paths, sixw), [], lsb, rsb))

    for nm, (uni, paths, shapes, lsb, rsb) in _punct(m).items():
        glyphs.append(positioned(m, nm, uni, paths, shapes, lsb, rsb))

    # Yiddish digraphs and a few composites are plain letter pairs
    for nm, uni, parts in (("vavvav", 0x05F0, ("vav", "vav")),):
        pass

    for nm, (uni, geom, cls) in _marks(m).items():
        g = Glyph(nm, uni, finish(geom, 0), 0, is_mark=True)
        g.mark_class = cls
        glyphs.append(g)

    # zero-width controls and spaces
    for nm, uni, adv in (("zwnj", 0x200C, 0), ("zwj", 0x200D, 0), ("lrm", 0x200E, 0), ("rlm", 0x200F, 0),
                         ("enspace", 0x2002, 500), ("emspace", 0x2003, 1000), ("thinspace", 0x2009, 160),
                         ("hairspace", 0x200A, 70), ("narrownbsp", 0x202F, 160)):
        glyphs.append(Glyph(nm, uni, Polygon(), adv))
    return glyphs


def feature_code(glyphs):
    bases = [g for g in glyphs if g.anchors and not g.is_mark]
    marks = [g for g in glyphs if g.is_mark]
    cls = {}
    for g in marks:
        cls.setdefault(g.mark_class, []).append(g.name)

    L = ["languagesystem DFLT dflt;", "languagesystem hebr dflt;", "languagesystem latn dflt;", ""]
    cname = {"below": "MC_below", "holam": "MC_holam", "mid": "MC_mid", "shin": "MC_shin",
             "sin": "MC_sin", "meteg": "MC_meteg", "rafe": "MC_rafe"}
    for c, names in cls.items():
        L.append(f"markClass [{' '.join(names)}] <anchor 0 0> @{cname[c]};")
    L.append("")
    L.append("feature mark {")
    spec = [("below", "bot", "MC_below"), ("holam", "holam", "MC_holam"), ("mid", "mid", "MC_mid"),
            ("shin", "shin_r", "MC_shin"), ("sin", "shin_l", "MC_sin"), ("meteg", "bot_l", "MC_meteg"),
            ("rafe", "top", "MC_rafe")]
    for c, anchor, mc in spec:
        if c not in cls:
            continue
        L.append(f"  lookup {mc}_L {{")
        for g in bases:
            if anchor in g.anchors:
                x, y = g.anchors[anchor]
                L.append(f"    pos base {g.name} <anchor {round(x)} {round(y)}> mark @{mc};")
        L.append(f"  }} {mc}_L;")
    L.append("} mark;")
    L.append("")
    allbase = [g.name for g in glyphs if not g.is_mark and g.unicode and g.adv > 0]
    L.append(f"@GDEF_Base = [{' '.join(allbase)}];")
    L.append(f"@GDEF_Mark = [{' '.join(g.name for g in marks)}];")
    L.append("table GDEF {")
    L.append("  GlyphClassDef @GDEF_Base, , @GDEF_Mark, ;")
    L.append("} GDEF;")
    return "\n".join(L) + "\n"
