#!/usr/bin/env python3
"""Cover page of the Ritcha D'Oraita booklet = the cover of the previous booklet (output/cover.pdf) with its texts replaced.

What changes (everything else - background, medallion, "קונטרס", logo - is kept byte for byte):
  * title, first line: "פלפולא" -> "ריתחא" in EFT Algebra (fonts/EFT_ALGEBRA_OTS.TTF, the client's font, not in git).  The word is as wide as the
    straight double rule above it: the roof of the ת is stretched (only the roof, the strokes keep their thickness).
  * the curved text on top of the medallion (Keren, outside the rings): the quotation from the Yaaros Devash, no bullets at the ends,
    the source in brackets in a smaller size
  * the curved text inside the medallion at the bottom (Keren): שאלות • קושיות • נידונים • הלכה למעשה
  * the two lines under the medallion (Lulav CLM Bold): the new subtitle.
The Keren glyphs are the outlines embedded in the old cover (only the letters of the old texts); Keren has no ט, נ, comma and brackets
in that subset, they are taken from Miriam CLM Bold scaled to the height of Keren (assets/cover_fallback_glyphs.json) until the Keren
font itself is at hand.

usage: python3 make_cover_ritcha.py [src_cover.pdf] [out_cover.pdf]
"""
import io, json, math, os, re, sys
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'output', 'cover.pdf')
OUT = sys.argv[2] if len(sys.argv) > 2 else 'cover_176x250.pdf'
EFT = os.path.join(HERE, 'fonts', 'EFT_ALGEBRA_OTS.TTF')
LULAV = os.path.join(HERE, '..', '..', 'typeset', 'assets', 'fonts', 'LulavCLM-Bold.otf')
FALLBACK = os.path.join(HERE, 'assets', 'cover_fallback_glyphs.json')

# ---- geometry of the old cover (1408 x 2000 grid, config.json -> cover)
CX, CY = 711.0, 749.0                       # centre of the medallion
TITLE_SIZE, TITLE_Y = 165.0, 718.0          # first title line
RULE_L, RULE_R = 651.5, 1122.5              # the straight double rule above the title (measured on the background image)
INK_MARGIN = 9.0                            # the old first line stood 9 units inside the rule
TOP_R, TOP_CENTRE, TOP_SPAN = 356.0, 90.0, 124.0       # top arc: baseline radius, centre angle, free angular range (swash on the left, rule end on the right)
TOP_MAX = 40.0                              # size of the old text
BOT_R, BOT_CENTRE, BOT_SPAN = 317.0, -90.0, 110.0
BOT_SIZE = 30.3                             # the old text had to be shrunk to this size to fit
BRACKET_SCALE = 0.78                        # the bracketed source is set smaller
BULLET_SCALE = 0.70                         # bullets between the words of the bottom arc (old: 21.2 / 30.3)
ARC_RGB = '.4353 .3608 .2706'
LULAV_RGB = '.2235 .1725 .1255'
LULAV_X, LULAV_Y, LULAV_SIZE = 704.0, (1290.0, 1362.0), 42.0

TOP_TEXT = 'כי מטבע לימוד התורה והחכמה, שהיא כאש להוליד ריתחא דאורייתא (יערות דבש דרוש ו)'
BOT_ITEMS = ['שאלות', 'קושיות', 'נידונים', 'הלכה למעשה']
LINES = ['אוסף קושיות ונידונים בהלכות תפילה וברכות', 'שעלו בריתחא מאברכי הכולל']
WORD = 'ריתחא'


# ------------------------------------------------------------------ outlines
class PathPen(BasePen):
    """outline (y up, font units) -> list of ('m'|'l'|'c', coords) in 1000-unit em, y down (like the Type 3 glyphs of the PDF)"""
    def __init__(self, gs, upm):
        super().__init__(gs); self.k = 1000.0 / upm; self.contours = []; self.cur = None
    def pt(self, p): return (p[0] * self.k, -p[1] * self.k)
    def _moveTo(self, p): self.cur = [('m', self.pt(p))]
    def _lineTo(self, p): self.cur.append(('l', self.pt(p)))
    def _curveToOne(self, a, b, c): self.cur.append(('c', self.pt(a) + self.pt(b) + self.pt(c)))
    def _closePath(self): self.contours.append(self.cur); self.cur = None


def font_glyph(font, ch, warp=None):
    gs = font.getGlyphSet(); cm = font.getBestCmap(); upm = font['head'].unitsPerEm; name = cm[ord(ch)]
    if warp:
        rec = RecordingPen(); gs[name].draw(rec)
        pen = PathPen(gs, upm)
        for op, args in rec.value:
            args = tuple(warp(x, y) for x, y in args)
            if op == 'moveTo': pen.moveTo(*args)
            elif op == 'lineTo': pen.lineTo(*args)
            elif op == 'qCurveTo': pen.qCurveTo(*args)
            elif op == 'closePath': pen.closePath()
    else:
        pen = PathPen(gs, upm); gs[name].draw(pen)
    return dict(contours=pen.contours, adv=font['hmtx'][name][0] * 1000.0 / upm)


def keren_glyphs(doc, font_xref=11):
    """the outlines of the Keren subset embedded in the old cover (Type 3 char procs), by Unicode"""
    obj = doc.xref_object(font_xref, compressed=False)
    procs = {m.group(1): int(m.group(2)) for m in re.finditer(r'/g([0-9A-F]+) (\d+) 0 R', obj)}
    codes = {}
    for a, b, u in ((0x5F, 0x64, 0x5D0), (0x68, 0x6D, 0x5D9), (0x70, 0x71, 0x5E1), (0x76, 0x79, 0x5E7)):
        for c in range(a, b + 1): codes[c] = u + c - a
    codes[0x66] = 0x5D7; codes[0x73] = 0x5E4; codes[0x03] = 0x20
    out = {}
    for c, u in codes.items():
        if '%X' % c not in procs: continue
        lines = doc.xref_stream(procs['%X' % c]).decode('latin-1').split('\n')
        adv = float(lines[0].split()[0]); contours = []; cur = None
        for line in lines[1:]:
            p = line.split()
            if not p: continue
            if p[-1] == 'm':
                if cur: contours.append(cur)
                cur = [('m', (float(p[0]), float(p[1])))]
            elif p[-1] == 'l': cur.append(('l', (float(p[0]), float(p[1]))))
            elif p[-1] == 'c': cur.append(('c', tuple(float(v) for v in p[:6])))
        if cur: contours.append(cur)
        out[chr(u)] = dict(contours=contours, adv=adv)
    for ch, g in json.load(open(FALLBACK, encoding='utf8')).items():        # ט נ , ( ) from Miriam CLM Bold
        out[ch] = dict(adv=g['adv'], contours=[[(op, tuple(a)) for op, a in c] for c in g['contours']])
    return out


def fmt(v): return ('%.3f' % v).rstrip('0').rstrip('.') if '.' in ('%.3f' % v) else '%.3f' % v


def path_ops(contours, tf):
    """tf maps a glyph point (x, y) to page-grid coordinates"""
    ops = []
    for c in contours:
        for op, a in c:
            if op in ('m', 'l'):
                x, y = tf(a[0], a[1]); ops.append('%s %s %s' % (fmt(x), fmt(y), op))
            else:
                p = [tf(a[i], a[i + 1]) for i in (0, 2, 4)]
                ops.append(' '.join('%s %s' % (fmt(x), fmt(y)) for x, y in p) + ' c')
        ops.append('h')
    return ops + ['f']


# ------------------------------------------------------------------ title, first line
def smooth(x, a, b):
    t = min(1.0, max(0.0, (x - a) / float(b - a))); return t * t * (3 - 2 * t)


def stretch_tav(delta):
    """stretch the roof of the ת by delta font units.  The roof (y > 334) is cut at x ~ 260 and its right part, with the hook at its end,
    moves right; the diagonal and the foot (y < 300) stay as they are."""
    def warp(x, y):
        w = max(smooth(x, 410, 430), smooth(y, 300, 335) * smooth(x, 220, 300))
        return (x + delta * w, y)
    return warp


def title_line(font):
    visual = WORD[::-1]                                  # left to right on the page
    s = TITLE_SIZE / 1000.0
    base = {c: font_glyph(font, c) for c in set(WORD)}
    def ink(ch):                                         # exact ink extent of a glyph (font units)
        bp = BoundsPen(font.getGlyphSet()); font.getGlyphSet()[font.getBestCmap()[ord(ch)]].draw(bp); return bp.bounds[0], bp.bounds[2]
    first, last = ink(visual[0])[0], ink(visual[-1])[1]
    natural = (sum(base[c]['adv'] for c in visual[:-1]) + last - first) * s
    target = (RULE_R - INK_MARGIN) - (RULE_L + INK_MARGIN)
    delta = (target - natural) / s
    glyphs = {c: base[c] for c in base}
    glyphs['ת'] = font_glyph(font, 'ת', stretch_tav(delta)); glyphs['ת']['adv'] = base['ת']['adv'] + delta
    ink_l = (RULE_L + INK_MARGIN); x0 = ink_l - first * s
    ops = []; x = x0
    for c in visual:
        ops += path_ops(glyphs[c]['contours'], lambda gx, gy, x=x: (x + gx * s, TITLE_Y + gy * s))
        x += glyphs[c]['adv'] * s
    return ops, ink_l, RULE_R - INK_MARGIN, delta


# ------------------------------------------------------------------ curved text
def arc_text(items, radius, centre, span, top, kfont):
    """items: [(glyph, size)] in visual order (left to right).  Each glyph is rotated to the tangent of the circle and stands on it with its
    middle (like SVG textPath, text-anchor middle).  top=True: the text runs clockwise on the outside of the circle, the letters stand outwards;
    top=False: it runs counter-clockwise, the letters stand towards the centre (bottom arc)."""
    total = sum(g['adv'] * sz / 1000.0 for g, sz in items)
    s0 = -total / 2.0
    ops = []
    for g, sz in items:
        w = g['adv'] * sz / 1000.0; mid = s0 + w / 2.0; s0 += w
        phi = math.radians(centre) + (-1 if top else 1) * mid / radius
        px, py = CX + radius * math.cos(phi), CY - radius * math.sin(phi)
        if top: tx, ty, ux, uy = math.sin(phi), math.cos(phi), math.cos(phi), -math.sin(phi)          # reading direction, "up" of the letters
        else:   tx, ty, ux, uy = -math.sin(phi), -math.cos(phi), -math.cos(phi), math.sin(phi)
        k = sz / 1000.0
        def tf(gx, gy, px=px, py=py, tx=tx, ty=ty, ux=ux, uy=uy, k=k, w=w):
            a = (gx * k - w / 2.0); b = -gy * k
            return (px + tx * a + ux * b, py + ty * a + uy * b)
        ops += path_ops(g['contours'], tf)
    return ops, total


def visual_items(text, K, size, bracket_size=None, bullet=None, bullet_size=0):
    """logical Hebrew string (RTL) -> glyphs in visual left-to-right order; brackets are mirrored; the part in brackets uses bracket_size"""
    mirror = {'(': ')', ')': '('}
    items = []; depth = 0
    for ch in text:
        if ch == '(': depth += 1
        sz = bracket_size if (depth and bracket_size) else size
        if ch == '•':
            items.append((bullet, bullet_size))
        else:
            items.append((K[mirror.get(ch, ch)], sz))
        if ch == ')': depth -= 1
    return items[::-1]


def fit(make, size_max, span, radius):
    """largest size (<= size_max) at which the text fits the angular range"""
    limit = math.radians(span) * radius
    lo, hi = 5.0, size_max
    if sum(g['adv'] * sz / 1000.0 for g, sz in make(hi)) <= limit: return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        if sum(g['adv'] * sz / 1000.0 for g, sz in make(mid)) <= limit: lo = mid
        else: hi = mid
    return lo


# ------------------------------------------------------------------ Lulav lines
def lulav_lines(font):
    gl = {}
    ops = []
    for line, y in zip(LINES, LULAV_Y):
        items = []
        for ch in line[::-1]:
            if ch not in gl: gl[ch] = font_glyph(font, ch)
            items.append(gl[ch])
        s = LULAV_SIZE / 1000.0
        width = sum(g['adv'] for g in items) * s
        x = LULAV_X - width / 2.0
        for g in items:
            ops += path_ops(g['contours'], lambda gx, gy, x=x, y=y: (x + gx * s, y + gy * s)); x += g['adv'] * s
    return ops


# ------------------------------------------------------------------ main
def main():
    doc = fitz.open(SRC); page = doc[0]
    assert abs(page.rect.width - 498.96) < 0.1
    xref = page.get_contents()[0]
    s = doc.xref_stream(xref).decode('latin-1')

    # 1. first title line
    eft = TTFont(EFT)
    ops, ink_l, ink_r, delta = title_line(eft)
    m = re.search(r'/Pattern CS/Pattern cs/P7 SCN/P7 scn\nBT\n/ReversedChars BMC\n/F8 165 Tf\n.*?\nEMC\nET\n', s, re.S)
    assert m, 'title line not found'
    s = s[:m.start()] + '/Pattern CS/Pattern cs/P7 SCN/P7 scn\n' + '\n'.join(ops) + '\n' + s[m.end():]
    doc.xref_set_key(7, 'Shading/Coords', '[%.2f 0 %.2f 0]' % (ink_l, ink_r))

    # 2. the two curved lines: remove every glyph of the old ones, put the new ones where the first one stood
    K = keren_glyphs(doc)
    bullet = font_glyph(TTFont(io.BytesIO(doc.extract_font(10)[3])), '●')
    top = lambda sz: visual_items(TOP_TEXT, K, sz, sz * BRACKET_SCALE)
    bot_text = ' • '.join(BOT_ITEMS)
    bot = lambda sz: visual_items(bot_text, K, sz, None, bullet, sz * BULLET_SCALE)
    top_size = fit(top, TOP_MAX, TOP_SPAN, TOP_R); bot_size = fit(bot, BOT_SIZE, BOT_SPAN, BOT_R)
    top_ops, top_len = arc_text(top(top_size), TOP_R, TOP_CENTRE, TOP_SPAN, True, K)
    bot_ops, bot_len = arc_text(bot(bot_size), BOT_R, BOT_CENTRE, BOT_SPAN, False, K)
    arcs = ('q\n1.47635722 0 0 1.47635722 .63476563 .0099875713 cm\n%s RG %s rg\n/G3 gs\n%s\nQ\n'
            % (ARC_RGB, ARC_RGB, '\n'.join(top_ops + bot_ops)))
    pat = re.compile(r'q\n[-\d. ]+ cm\n[\d. ]+ RG [\d. ]+ rg\n/G3 gs\nBT\n/F1[01] [\d.]+ Tf\n1 0 0 -1 [-\d.]+ [-\d.]+ Tm\n<[0-9A-F]+> Tj\nET\nQ\n')
    found = list(pat.finditer(s)); assert len(found) == 77, len(found)
    first = found[0].start()
    s = pat.sub('', s)
    s = s[:first] + arcs + s[first:]

    # 3. the two lines under the medallion
    lulav = TTFont(LULAV)
    i = s.index('/F12 42 Tf'); a = s.rindex('q\n1.47635722 0 0 1.47635722', 0, i)
    b = s.index('\nQ\n', s.rindex('/F12 42 Tf')) + 3
    block = ('q\n1.47635722 0 0 1.47635722 .63476563 .0099875713 cm\n%s RG %s rg\n/G3 gs\n%s\nQ\n' % (LULAV_RGB, LULAV_RGB, '\n'.join(lulav_lines(lulav))))
    s = s[:a] + block + s[b:]

    doc.update_stream(xref, s.encode('latin-1'))
    doc.save(OUT, garbage=3, deflate=True)
    print('wrote', OUT)
    print('title line 1: ink %.1f .. %.1f, ת stretched by %.0f units' % (ink_l, ink_r, delta))
    print('top arc: size %.1f (old 40), length %.0f of %.0f; bottom arc: size %.1f, length %.0f of %.0f'
          % (top_size, top_len, math.radians(TOP_SPAN) * TOP_R, bot_size, bot_len, math.radians(BOT_SPAN) * BOT_R))


if __name__ == '__main__':
    main()
