#!/usr/bin/env python3
"""Cuts a small booklet out of the finished full booklet PDF (vector pages are copied, nothing is rasterised) - the original is not touched.

usage: python extract_booklet.py booklet.pdf out.pdf [--title beinyan|plain] [--algebra EFT_Algebra.ttf] [--name NAME]\n           [--title-font MANTB.TTF --text-font frank.otf --text-bold bold.otf] [--haskama h.pdf] [--prospectus p.pdf]

Used for the memorial booklet: the cover pages + the two articles of R. Moshe Zada (the opening "החובה להתאמץ בדור אחרון" and the one that stands
as "הזכרת השם" in the full booklet). No dividers, no table of contents.
  --title beinyan  (default)  the second article is retitled "בעניין הזכרת השם" and the line "קונטרס" under its title is removed
  --title plain               the second article keeps its title block exactly as it is: "הזכרת השם" with the line "קונטרס"
  --display FONT              Dimdumim (legacy cp1255 encoding) for the title and the abbreviation of the memorial text page
  --name NAME                 replaces the booklet name in the running head (default: the name of the full booklet)
  --algebra FONT              the client's display font (not in git): switches the front pages to the memorial version, see below

What is done to the pages (the PDF comes out of Chromium; the fonts of the title and the header are Type 3 fonts that carry the whole alphabet, so new
text is set with the same glyphs at the advances of the font - nothing is substituted):
  * order (52 pages): 1 colour cover, 2 credits page, 3 grey inner title page, 4 memorial text page, 5 table of contents (generated: every article,\n    part heading and sub-heading with its page), 6 the haskama (title changed to the singular), 7-9 the first article, 10 empty, 11-47 the second,\n    48-50 empty, 51 the prospectus (inside of the back cover), 52 back cover. Earlier layout (48 pages): 4 empty, 5-7 the first article, 8 empty,
    9-45 the second one, 46-47 empty, 48 back cover (with --algebra page 4 carries the memorial text instead of staying empty). Every article begins on an odd page and the back cover is an even page, so empty pages fill the
    gaps. The running head is mirrored (number at the outer edge, the group "name of the booklet + title / author" at the other side), the page
    body is symmetric (equal margins), so the pages of both articles, which moved from even to odd and back, only get their head mirrored: the
    number, the booklet name and the bullet change sides and the author / the title change places
  * page numbers: printed number = physical page - 4 (alef = physical page 5, as in the full booklet), re-set on every article page
  * title page of the second article (--title beinyan): new title in the same frame (the frame has a minimum width and the longer title still fits),
    the line "קונטרס" removed; the body text is NOT reflowed (every column keeps its place), so the extra line is shared between the three gaps of the head
    block (header-frame, frame-author, author-text) instead of staying as one hole
  * memorial front pages (--algebra): the two curved lines round the circle of the covers (the quotation and "חבורות ● שיעורים ...") are removed; the
    subtitle of the colour cover becomes "בעניין הכוונה בהזכרת שם השם ושמות שאינם נמחקים" (centred on the page); on the grey inner title page the subtitle
    is replaced by the dedication (all in Lulav CLM Bold, centred on the page, the names larger and thickened), the logo is removed and the circle with its
    texts moves up (shift_medallion.py moves the medallion inside the background picture); the logo of the colour cover stays. The credits page gets the typesetting credit in a double
    rounded frame under its last line, the column moves up a little to keep the margins
Needs: pip install pikepdf fonttools numpy scipy pillow"""
import argparse
import os
import sys
from decimal import Decimal
import pikepdf
from pikepdf import Name, Operator, String, ContentStreamInstruction as CSI
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

# source page numbers (1 = cover) of the full booklet
FRONT = [1, 4, 3]                     # cover, credits (instead of the empty page inside the cover), inner title page
ART1 = (20, 22)                       # "החובה להתאמץ בדור אחרון" (Moshe Zada)
ART2 = (84, 120)                      # "הזכרת השם" (Moshe Zada)
BACK = 634
SRC_AUTHOR, SRC_TITLE1, SRC_TITLE2 = 84, 21, 85    # pages whose running head carries the author (even) / the titles (odd)
OLD_TITLE, NEW_TITLE = 'הזכרת השם', 'בעניין הזכרת השם'
NUM_OFFSET = 4                        # printed number = physical page - 4 (alef = physical page 5, as in the full booklet)
BANNER_SHARE = Decimal('22.9167')     # one third of the freed line (68.75 units) in the units of the 0.24 pt matrix of the page
PAGE_W_PX, MARGIN_PX = 665, 73.3125   # page width in css px, outer margin (19.4 mm)
# running head, css px (read from the full booklet): the group is [booklet name][gap + bullet][author / title text]; on an even page it starts at the
# inner margin (left), on an odd page it ends at the right edge; the number sits at the outer edge
HEAD_EDGE_LEFT, HEAD_EDGE_RIGHT = 73.3125, 591.855
GAP_NAME_BULLET, GAP_BULLET_TEXT = 7.0, 11.84     # name end -> bullet, bullet -> text start (even); mirrored on odd pages
BOOKLET_NAME = 'פלפולא דאורייתא'


def letter_code(ch):                  # Type 3 fonts of the booklet: code = 0xAF + (letter - alef)
    return 3 if ch == ' ' else 0xAF + ord(ch) - 0x05D0


def hebrew_number(n):
    ones, tens = 'אבגדהוזחט', 'יכלמנסעפצ'
    if n in (15, 16):
        return 'טו' if n == 15 else 'טז'
    assert 1 <= n < 100
    return (tens[n // 10 - 1] if n >= 10 else '') + (ones[n % 10 - 1] if n % 10 else '')


def visual(text):
    return [letter_code(c) for c in reversed(text)]


def decode(codes):
    """logical text of a run of codes (the codes are stored in visual order, left to right)"""
    return ''.join(' ' if c == 3 else chr(0x05D0 + c - 0xAF) if c and 0xAF <= c <= 0xC9 else '?' for c in reversed(codes))


def advances(font, codes, size):
    w = [float(x) for x in font.Widths]
    return [w[c] * size / 2048 for c in codes]


def text_block(font_name, size, x, y, codes, font):
    """BT .. ET in the form Chromium writes it: first glyph by Tj, every next one after a Td by the advance of the previous glyph."""
    ops = [CSI([], Operator('BT')), CSI([Name('/ReversedChars')], Operator('BMC')),
           CSI([Name(font_name), Decimal(str(size))], Operator('Tf')),
           CSI([1, 0, 0, -1, Decimal(f'{x:.7f}'), y], Operator('Tm'))]
    adv = advances(font, codes, size)
    for i, c in enumerate(codes):
        if i:
            ops.append(CSI([Decimal(f'{adv[i - 1]:.7f}'), 0], Operator('Td')))
        ops.append(CSI([String(bytes([c]))], Operator('Tj')))
    ops += [CSI([], Operator('EMC')), CSI([], Operator('ET'))]
    return ops


def split_blocks(ops):
    """every BT..ET block: start, end, font name, size, x, y of its Tm and the one-byte codes it shows"""
    out, i = [], 0
    while i < len(ops):
        if str(ops[i].operator) == 'BT':
            j = i
            while str(ops[j].operator) != 'ET':
                j += 1
            font = size = tm = None
            codes = []
            for op in ops[i:j + 1]:
                o = str(op.operator)
                if o == 'Tf':
                    font, size = str(op.operands[0]), float(op.operands[1])
                elif o == 'Tm':
                    tm = [float(x) for x in op.operands]
                elif o == 'Tj':
                    s = bytes(op.operands[0])
                    codes += list(s) if len(s) == 1 else [None]
            out.append(dict(start=i, end=j, font=font, size=size, x=tm and tm[4], y=tm and tm[5], codes=codes))
            i = j
        i += 1
    return out


def set_tm_x(ops, blk, x):
    for k in range(blk['start'], blk['end'] + 1):
        if str(ops[k].operator) == 'Tm':
            t = list(ops[k].operands)
            t[4] = Decimal(f'{x:.5f}')
            ops[k] = CSI(t, Operator('Tm'))


def head_blocks(ops):
    blocks = split_blocks(ops)
    first = lambda f, s: next(b for b in blocks if b['font'] == f and abs(b['size'] - s) < 0.01)
    return first('/F40', 20), first('/F41', 13.33), first('/F40', 17.33), first('/F42', 8)


def head_text(page, ops):
    """the codes of the author / title text of the running head of a source page"""
    return head_blocks(ops)[1]['codes']


def rebuild_header(page, ops, odd, num_text, text_codes, name=BOOKLET_NAME):
    """running head of the page as it has to be on an odd / even page: number at the outer edge, the booklet name and the bullet at the other
    side, the author or the title text (text_codes) next to the bullet; the glyphs are the ones of the page's own fonts"""
    pal, txt, num, bul = head_blocks(ops)
    f40, f41 = page.Resources.Font['/F40'], page.Resources.Font['/F41']
    ncodes = visual(num_text)
    nw = sum(advances(f40, ncodes, 17.33))
    nx = MARGIN_PX if odd else PAGE_W_PX - MARGIN_PX - nw                  # the outer edge is the left one on an odd page
    pcodes = visual(name)
    pw = sum(advances(f40, pcodes, 20))
    tw = sum(advances(f41, text_codes, 13.33))
    if odd:                                                                # the group is right-aligned
        px = HEAD_EDGE_RIGHT - pw
        bx = px - GAP_BULLET_TEXT
        tx = bx - GAP_NAME_BULLET - tw
    else:
        px = HEAD_EDGE_LEFT
        bx = px + pw + GAP_NAME_BULLET
        tx = bx + GAP_BULLET_TEXT
    set_tm_x(ops, bul, bx)
    edits = [(num['start'], num['end'], text_block('/F40', 17.33, nx, num['y'], ncodes, f40)),
             (pal['start'], pal['end'], text_block('/F40', 20, px, pal['y'], pcodes, f40)),
             (txt['start'], txt['end'], text_block('/F41', 13.33, tx, txt['y'], text_codes, f41))]
    for s, e, new in sorted(edits, reverse=True):
        ops[s:e + 1] = new
    return ops


def title_page(page, ops):
    """new title in the frame, 'קונטרס' removed, the freed line shared between the gaps of the head block"""
    f47 = page.Resources.Font['/F47']
    blocks = split_blocks(ops)
    old = next(b for b in blocks if b['font'] == '/F47' and abs(b['size'] - 22) < 0.01)
    assert decode(old['codes']) == OLD_TITLE
    centre = old['x'] + sum(advances(f47, old['codes'], 22)) / 2
    ncodes = visual(NEW_TITLE)
    nw = sum(advances(f47, ncodes, 22))
    dy = float(BANNER_SHARE) / 3.125                               # Tm units
    kon = next(b for b in blocks if b['font'] == '/F41' and abs(b['size'] - 14.66) < 0.01 and decode(b['codes']) == 'קונטרס')
    aut = next(b for b in blocks if b['font'] == '/F80')
    # images of the frame (cloud, left cap, middle, right cap) move down by one share; the title with them
    for k, x in enumerate(ops):
        o = x.operands
        if str(x.operator) == 'cm' and len(o) == 6 and float(o[3]) < 0 and float(o[0]) > 60 and 150 < -float(o[3]) < 200 and float(o[0]) != 1621.875:
            ops[k] = CSI([o[0], o[1], o[2], o[3], o[4], Decimal(str(float(o[5]) + float(BANNER_SHARE)))], Operator('cm'))
    # author line: two shares
    for k in range(aut['start'], aut['end'] + 1):
        if str(ops[k].operator) == 'Tm':
            t = list(ops[k].operands)
            t[5] = Decimal(str(float(t[5]) + 2 * dy))
            ops[k] = CSI(t, Operator('Tm'))
    edits = [(old['start'], old['end'], text_block('/F47', 22, centre - nw / 2, old['y'] + dy, ncodes, f47)),
             (kon['start'], kon['end'], [])]
    for s, e, new in sorted(edits, reverse=True):
        ops[s:e + 1] = new
    return ops


# ------------------------------------------------------------------------------------------------ cover pages and credits
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LULAV = os.path.join(HERE, 'assets', 'fonts', 'LulavCLM-Bold.otf')
COVER_SUB = ('בעניין הכוונה בהזכרת שם השם', 'ושמות שאינם נמחקים')
# the dedication of the grey inner title page, all in Lulav: (text, size, step from the previous line, extra weight) - the grid of the cover is 1408 x 2000
DEDICATION = [
    ('יו״ל במלאות שבעה לעלותו לשמי רום בחטף', 29, 0, 0),
    ('של ינוקא דבי רב עלם חמודות', 29, 40, 0),
    ('הילד אליהו בן הדסה חיה עזריאל ז״ל', 54, 82, 1.3),
    ('רוכב בערבות שש ושמח בבא אליו נפש נקי וצדיק', 29, 60, 0),
    ('בן יבלחט״א ידידינו העומד לימינינו', 29, 54, 0),
    ('הרה״ג ר׳ חיים מאיר שליט״א', 44, 64, 1.2),
    ('זכות התורה תעמוד לו ולעילוי נשמתו ובעדן תהיה מנוחתו', 26, 68, 0),
    ('עד יקוצו וירננו שוכני עפר בב״א', 26, 36, 0),
]
# the page of the memorial text (the empty page 4 behind the grey inner title page): title, name, a verse, two paragraphs, the abbreviation
MEMORIAL_TITLE, MEMORIAL_NAME = 'לעילוי נשמת', 'הילד אליהו ז״ל'
MEMORIAL_VERSE, MEMORIAL_CITE = 'ה׳ נתן וה׳ לקח, יהי שם ה׳ מבורך', 'איוב א, כא'
MEMORIAL_PARAS = [
    'קונטרס זה נערך ונלקט לעילוי נשמתו הטהורה של הילד הרך אליהו ז״ל, שנקטף בעודו בראשית חייו ועלתה נשמתו לשמי מרום. '
    'יהי רצון שכל דבר תורה הנלמד בו, וכל ברכה ותפילה שתיאמר מתוך כוונה, יעלו לזכותו ויהיו לו לעילוי נשמה.',
    'תהא נשמתו צרורה בצרור החיים, ו״בלע המות לנצח ומחה ה׳ אלקים דמעה מעל כל פנים״ (ישעיה כה, ח). '
    'המקום ינחם את הוריו ואת כל בני משפחתו בתוך שאר אבלי ציון וירושלים, ולא ידעו עוד צער.',
]
MEMORIAL_END = 'ת.נ.צ.ב.ה'
MEMORIAL_W, MEMORIAL_SIZE, MEMORIAL_LEAD = 800.0, 36.0, 62.0                           # text column (grid units), size, line step
DEDICATION_MAXW = 720.0                            # widest line (a line is shrunk to fit)
DEDICATION_BAND = (850.0, 1790.0)                  # the block is centred vertically between the circle (after it moved up) and the inner edge of the frame
GRID_CX = 705.5                                    # the middle of the page in the grid of the cover (the page is 2078.125 units wide, cm 1.47636, offset -2.49)
MEDALLION_UP = 150.0                               # the circle of the inner title page moves up by this much (grid units)
CREDIT_LABEL, CREDIT_PHONE = 'עימוד ועיצוב: י. א. - ', '0534185035'
CREDIT_SHIFT, CREDIT_GAP, CREDIT_BOX = 24.0, 40.0, dict(padx=11.0, up=19.0, down=11.0, r=7.0, inset=2.6)   # css px


MIRROR = {'(': ')', ')': '(', '[': ']', ']': '['}


class PdfPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.ops = []

    @staticmethod
    def _n(v):
        return Decimal(f'{v:.2f}')

    def _moveTo(self, p):
        self.ops.append(CSI([self._n(p[0]), self._n(p[1])], Operator('m')))

    def _lineTo(self, p):
        self.ops.append(CSI([self._n(p[0]), self._n(p[1])], Operator('l')))

    def _curveToOne(self, a, b, c):
        self.ops.append(CSI([self._n(v) for v in (*a, *b, *c)], Operator('c')))

    def _closePath(self):
        self.ops.append(CSI([], Operator('h')))


class Outline:
    """font files as a source of outlines: text is drawn as filled paths (the fill, a colour or a pattern, is the one in force); a character the first
    font does not have (Lulav has no geresh / gershayim) is taken from the next font of the list"""
    def __init__(self, *paths):
        self.faces = []
        for p in paths:
            f = p if isinstance(p, TTFont) else TTFont(p)
            self.faces.append((f, f.getBestCmap(), f.getGlyphSet(), f['head'].unitsPerEm))

    def _face(self, ch):
        for f, cmap, gs, upem in self.faces:
            if ord(ch) in cmap:
                return f, cmap[ord(ch)], gs, upem
        raise KeyError(ch)

    def width(self, text, size):
        return sum(self._face(c)[0]['hmtx'][self._face(c)[1]][0] / self._face(c)[3] for c in text) * size

    def ops(self, text, size, x, y, weight=0.0):
        """text (logical order) with its left edge at x and its baseline at y of the page's flipped coordinate system; weight > 0 thickens the letters
        (an outline of that width, in the units of the page, in the stroke colour that is in force)"""
        out = []
        for c in reversed(text):
            f, g, gs, upem = self._face(MIRROR.get(c, c))             # brackets are mirrored in a right-to-left run
            sc = size / upem
            pen = PdfPen(gs)
            gs[g].draw(pen)
            if pen.ops:
                out += [CSI([], Operator('q')), CSI([Decimal(f'{sc:.6f}'), 0, 0, Decimal(f'{-sc:.6f}'), Decimal(f'{x:.3f}'), Decimal(f'{y:.3f}')], Operator('cm'))]
                if weight:
                    out += [CSI([Decimal(f'{weight / sc:.2f}')], Operator('w')), CSI([1], Operator('j'))]
                out += pen.ops + [CSI([], Operator('B' if weight else 'f')), CSI([], Operator('Q'))]
            x += f['hmtx'][g][0] * sc
        return out


def curved_groups(ops, fonts):
    """(first, last) of every q..Q group that shows text in one of the given fonts (the curved lines: one glyph per group)"""
    out, i = [], 0
    while i < len(ops):
        if str(ops[i].operator) == 'q':
            depth, j, hit = 1, i + 1, False
            while depth:
                o = str(ops[j].operator)
                depth += (o == 'q') - (o == 'Q')
                hit |= o == 'Tf' and str(ops[j].operands[0]) in fonts
                j += 1
            if hit and j - i < 40:
                out.append((i, j - 1))
                i = j
            else:
                i += 1                                             # an enclosing group: look inside it
        else:
            i += 1
    return out


def memorial_cover(page, ops, curved, subtitle, algebra):
    """no curved lines round the circle; the subtitle (two lines under the circle) is replaced: on the colour cover by the new subtitle, on the grey
    inner title page (subtitle=None) by the dedication; there also the logo is removed and the circle moves up"""
    lulav = Outline(LULAV, algebra)
    blocks = split_blocks(ops)
    subs = [b for b in blocks if abs(b['size'] - 42) < 0.01]
    assert len(subs) == 2
    edits = [(a, b, []) for a, b in curved_groups(ops, curved)]
    if subtitle:
        for old, text in zip(subs, subtitle):                       # centred on the page
            edits.append((old['start'], old['end'], lulav.ops(text, 42, GRID_CX - lulav.width(text, 42) / 2, old['y'])))
    else:
        total = sum(step for _, _, step, _ in DEDICATION)
        y = (DEDICATION_BAND[0] + DEDICATION_BAND[1]) / 2 - total / 2 + DEDICATION[0][1] * 0.35
        new = []
        for text, size, step, weight in DEDICATION:
            y += step
            size = min(size, size * DEDICATION_MAXW / lulav.width(text, size))
            new += lulav.ops(text, size, GRID_CX - lulav.width(text, size) / 2, y, weight)
        edits.append((subs[0]['start'], subs[0]['end'], new))
        edits.append((subs[1]['start'], subs[1]['end'], []))
        for b in blocks:                                            # the live texts of the medallion (kontres, the title) go up with the circle
            if abs(b['size'] - 56.45) < 0.01 or abs(b['size'] - 165) < 0.01:
                for k in range(b['start'], b['end'] + 1):
                    if str(ops[k].operator) == 'Tm':
                        t = list(ops[k].operands)
                        t[5] = Decimal(f'{float(t[5]) - MEDALLION_UP:.3f}')
                        ops[k] = CSI(t, Operator('Tm'))
        for k, op in enumerate(ops):                                # the logo: the last group q cm Do Q with the big image
            if str(op.operator) == 'cm' and len(op.operands) == 6 and 400 < float(op.operands[0]) < 500 and str(ops[k + 2].operator) in ('gs', 'rg', 'Do'):
                last = next(j for j in range(k, len(ops)) if str(ops[j].operator) == 'Q')
                edits.append((k - 1, last, []))
    for a, b, new in sorted(edits, key=lambda e: -e[0]):
        ops[a:b + 1] = new
    return ops


def move_medallion(pdf, page):
    """the picture of the page (the medallion in it), the gradient of the title: all up by MEDALLION_UP"""
    import shift_medallion
    img = page.Resources.XObject['/X19']
    img.write(shift_medallion.shifted_background(img.read_raw_bytes(), MEDALLION_UP), filter=Name.DCTDecode)
    for pat in page.Resources.Pattern.values():
        m = [float(v) for v in pat.Matrix]
        m[5] += MEDALLION_UP * 0.35432571                           # the page is 708.96 pt = 2000 grid units high
        pat.Matrix = pikepdf.Array([Decimal(f'{v:.8f}') for v in m])


def wrap(text, outline, size, width):
    """greedy line breaking; a last line of one word takes the word before it down"""
    words, lines, cur = [], [], []
    for w in text.split():                                          # 'ז״ל' stays with the name before it
        if words and w.startswith('ז״ל'):
            words[-1] += ' ' + w
        else:
            words.append(w)
    for w in words:
        if cur and outline.width(' '.join(cur + [w]), size) > width:
            lines.append(cur)
            cur = []
        cur.append(w)
    lines.append(cur)
    if len(lines) > 1 and len(lines[-1]) == 1 and len(lines[-2]) > 2:
        lines[-1].insert(0, lines[-2].pop())
    return [' '.join(l) for l in lines]


def frank_font(path):
    """FrankRuehl DP draws U+05F3 / U+05F4 empty: its ASCII ' and " are the geresh / gershayim (see prepare_fonts.py)"""
    t = TTFont(path)
    for st in t['cmap'].tables:
        if st.isUnicode():
            st.cmap[0x5F3], st.cmap[0x5F4] = 'quotesingle', 'quotedbl'
    return t


def parse_path(d):
    """'M x,y L x,y C x,y x,y x,y Z' (absolute) -> path operators"""
    tok, out, i = d.replace(',', ' ').split(), [], 0
    names = {'M': ('m', 2), 'L': ('l', 2), 'C': ('c', 6)}
    while i < len(tok):
        c = tok[i]
        i += 1
        if c == 'Z':
            out.append(CSI([], Operator('h')))
            continue
        op, n = names[c]
        out.append(CSI([Decimal(t) for t in tok[i:i + n]], Operator(op)))
        i += n
    return out


def ellipse(cx, cy, rx, ry):
    k = 0.5523
    f = lambda *v: ' '.join(f'{t:.2f}' for t in v)
    return (f'M {f(cx + rx, cy)} C {f(cx + rx, cy + k * ry, cx + k * rx, cy + ry, cx, cy + ry)} C {f(cx - k * rx, cy + ry, cx - rx, cy + k * ry, cx - rx, cy)} '
            f'C {f(cx - rx, cy - k * ry, cx - k * rx, cy - ry, cx, cy - ry)} C {f(cx + k * rx, cy - ry, cx + rx, cy - k * ry, cx + rx, cy)} Z')


def candle(cx, top, height):
    """a memorial candle (a flame with fine rays, a wick, a candle with wax drips, a plate): vector drawing in greys, 266 units high in its own system"""
    import math
    sc = height / 266.0
    ops = [CSI([], Operator('q')), CSI([Decimal(f'{sc:.5f}'), 0, 0, Decimal(f'{sc:.5f}'), Decimal(f'{cx:.2f}'), Decimal(f'{top:.2f}')], Operator('cm')),
           CSI([1], Operator('J')), CSI([1], Operator('j'))]
    def draw(d, fill=None, stroke=None, width=1.0):
        nonlocal ops
        if fill is not None:
            ops.append(CSI([Decimal(str(fill))], Operator('g')))
        if stroke is not None:
            ops += [CSI([Decimal(str(stroke))], Operator('G')), CSI([Decimal(str(width))], Operator('w'))]
        ops += parse_path(d) if isinstance(d, str) else d
        ops.append(CSI([], Operator('B' if fill is not None and stroke is not None else ('f' if fill is not None else 'S'))))
    for ang in (-78, -54, -30, 30, 54, 78):                           # rays round the flame, finest strokes
        r1, r2, a = 54, 66 if abs(ang) < 60 else 62, math.radians(ang)
        draw(f'M {r1 * math.sin(a):.2f} {50 - r1 * math.cos(a):.2f} L {r2 * math.sin(a):.2f} {50 - r2 * math.cos(a):.2f}', None, 0.45, 1.3)
    draw('M 0 0 C 10 20 31 40 27 62 C 25 74 14 81 0 81 C -14 81 -25 74 -27 62 C -31 40 -10 20 0 0 Z', 0.17, 0.12, 1.2)       # the flame
    draw('M 0 36 C 6 47 14 55 11 66 C 10 72 5 76 0 76 C -5 76 -10 72 -11 66 C -14 55 -6 47 0 36 Z', 0.94)
    draw('M 0 80 L 0 101', None, 0.15, 3.0)                              # the wick
    draw('M -23 109 C -23 102 23 102 23 109 L 23 252 L -23 252 Z', 0.9, 0.2, 1.8)                                      # the candle
    draw(ellipse(0, 109, 23, 6), 0.8, 0.2, 1.4)                                                                        # the pool of wax
    draw('M -23 109 C -23 130 -15 136 -15 120 L -15 109 Z', 0.95, 0.2, 1.2)                                            # drips
    draw('M 8 109 C 8 128 15 132 15 116 L 15 109 Z', 0.95, 0.2, 1.2)
    draw('M -13 138 L -13 238', None, 1.0, 4.0)                                                                        # a highlight on the candle
    draw('M -45 252 L 45 252 L 53 266 L -53 266 Z', 0.8, 0.2, 1.8)                                                     # the plate
    ops += [CSI([], Operator('Q'))]
    return ops


def memorial_page(pdf, fleuron, algebra, like, fonts):
    """the page of the memorial text: a candle, the title, the name, a verse, two paragraphs, the abbreviation, a flourish.  fonts = the title font (Mantova
    bold), the text font and its bold (FrankRuehl DP); lulav / algebra are not used here (they are the fonts of the front pages)"""
    title_f, text_f, bold_f = Outline(fonts['title']), Outline(frank_font(fonts['text'])), Outline(frank_font(fonts['bold']))
    cx, items, y = GRID_CX, [], 0.0                                 # items: (outline, text, size, y, weight); y is relative, shifted at the end
    def put(o, text, size, step, weight=0.0):
        nonlocal y
        y += step
        items.append((o, text, size, y, weight))
    put(title_f, MEMORIAL_TITLE, 96, 0)
    put(title_f, MEMORIAL_NAME, 60, 100)
    put(bold_f, MEMORIAL_VERSE, 42, 150)
    put(text_f, MEMORIAL_CITE, 25, 46)
    y += 10
    for para in MEMORIAL_PARAS:
        lines = wrap(para, text_f, MEMORIAL_SIZE, MEMORIAL_W)
        for i, line in enumerate(lines):
            put(text_f, line, MEMORIAL_SIZE, MEMORIAL_LEAD if i else MEMORIAL_LEAD + 30)
    put(title_f, MEMORIAL_END, 64, 118)
    can_h, flo_w, flo_h, gap = 340.0, 430.0, 430.0 * 168 / 648, 100.0
    height = can_h + 118 + (items[-1][3] - items[0][3]) + 70 + gap + flo_h
    top = 1000.0 - height / 2                                       # the block is centred vertically
    base = top + can_h + 118 - items[0][3]
    ops = [CSI([], Operator('q')), CSI([Decimal('0.35432571'), 0, 0, Decimal('-0.35432571'), 0, Decimal('708.96')], Operator('cm')),
           CSI([Decimal('0.1098')], Operator('g')), CSI([Decimal('0.1098')], Operator('G'))]
    ops += candle(cx, top, can_h)
    ops += [CSI([Decimal('0.1098')], Operator('g')), CSI([Decimal('0.1098')], Operator('G'))]
    for o, text, size, yy, weight in items:
        size = min(size, size * 900.0 / o.width(text, size))
        ops += o.ops(text, size, cx - o.width(text, size) / 2, base + yy, weight)
    y_fl = base + items[-1][3] + 70 + gap
    ops += [CSI([], Operator('q')), CSI([Decimal(f'{flo_w:.2f}'), 0, 0, Decimal(f'{flo_h:.2f}'), Decimal(f'{cx - flo_w / 2:.2f}'), Decimal(f'{y_fl:.2f}')], Operator('cm')),
            CSI([Name('/X34')], Operator('Do')), CSI([], Operator('Q')), CSI([], Operator('Q'))]
    return pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=Name.Page, MediaBox=like.MediaBox, Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary({'/X34': fleuron})),
        Contents=pdf.make_stream(pikepdf.unparse_content_stream(ops)))))


def glyph_codes(font):
    """character -> code of a Type 3 font of the booklet (from its ToUnicode)"""
    import re
    s, m = font.ToUnicode.read_bytes().decode(), {}
    for blk in re.findall(r'beginbfchar(.*?)endbfchar', s, re.S):
        for a, b in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            m[chr(int(b[:4], 16))] = int(a, 16)
    for blk in re.findall(r'beginbfrange(.*?)endbfrange', s, re.S):
        for a, b, c in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            for i in range(int(a, 16), int(b, 16) + 1):
                m[chr(int(c[:4], 16) + i - int(a, 16))] = i
    return m


def rounded_rect(x0, y0, x1, y1, r):
    k = r * 0.5523
    d = lambda v: Decimal(f'{v:.3f}')
    seg = lambda op, *v: CSI([d(t) for t in v], Operator(op))
    return [seg('m', x0 + r, y0), seg('l', x1 - r, y0), seg('c', x1 - r + k, y0, x1, y0 + r - k, x1, y0 + r), seg('l', x1, y1 - r),
            seg('c', x1, y1 - r + k, x1 - r + k, y1, x1 - r, y1), seg('l', x0 + r, y1), seg('c', x0 + r - k, y1, x0, y1 - r + k, x0, y1 - r),
            seg('l', x0, y0 + r), seg('c', x0, y0 + r - k, x0 + r - k, y0, x0 + r, y0), CSI([], Operator('h'))]


def credits_box(page, ops):
    """the typesetting credit in a double rounded frame under the last line of the credits page; the column (texts and flourishes) moves up first"""
    f32, f33 = page.Resources.Font['/F32'], page.Resources.Font['/F33']
    blocks = split_blocks(ops)
    centres = []
    for b in blocks:                                               # the axis of the column = the centre of its centred lines
        if b['codes'] and None not in b['codes'] and b['font'] in ('/F32', '/F33'):
            centres.append(b['x'] + sum(advances(page.Resources.Font[b['font']], b['codes'], b['size'])) / 2)
    centres.sort()
    axis = centres[len(centres) // 2]
    last = max(blocks, key=lambda b: b['y'])
    for k, op in enumerate(ops):                                   # shift up: images are placed by cm (units of the 0.24 pt matrix), texts by Tm
        if str(op.operator) == 'cm' and len(op.operands) == 6 and 100 < float(op.operands[0]) < 1000 and k > 35:
            t = list(op.operands)
            t[5] = Decimal(f'{float(t[5]) - CREDIT_SHIFT * 3.125:.4f}')
            ops[k] = CSI(t, Operator('cm'))
        elif str(op.operator) == 'Tm':
            t = list(op.operands)
            t[5] = Decimal(f'{float(t[5]) - CREDIT_SHIFT:.4f}')
            ops[k] = CSI(t, Operator('Tm'))
    y = last['y'] - CREDIT_SHIFT + CREDIT_GAP
    size = 14.66
    c32, c33 = glyph_codes(f32), glyph_codes(f33)
    hebrew = [c32[c] for c in reversed(CREDIT_LABEL)]              # visual order, left to right: number, " - ", the Hebrew (reversed)
    number = [c33[c] for c in CREDIT_PHONE]
    w_h = sum(advances(f32, hebrew, size))
    w_n = sum(advances(f33, number, size))
    x0 = axis - (w_h + w_n) / 2
    B = CREDIT_BOX
    x_a, x_b, y_a, y_b = x0 - B['padx'], x0 + w_h + w_n + B['padx'], y - B['up'], y + B['down']
    frame = [CSI([], Operator('q')), CSI([Decimal('0.9')], Operator('w'))] + rounded_rect(x_a, y_a, x_b, y_b, B['r']) + [CSI([], Operator('S'))]
    i = B['inset']
    frame += [CSI([Decimal('0.4')], Operator('w'))] + rounded_rect(x_a + i, y_a + i, x_b - i, y_b - i, B['r'] - i / 2) + [CSI([], Operator('S')), CSI([], Operator('Q'))]
    new = frame + text_block('/F33', size, x0, y, number, f33) + text_block('/F32', size, x0 + w_n, y, hebrew, f32)
    end = max(k for k, op in enumerate(ops) if str(op.operator) == 'ET')
    ops[end + 1:end + 1] = new                                     # inside the group of the last line (same stroke / fill colour, same matrix)
    return ops


# ------------------------------------------------------------------------------------------------ table of contents, haskama, prospectus
TOC_TITLE_BANDS = ('הסכמה', 'חבורות')
HASKAMA_LINE = 'הסכמת הגאונים מרנן ורבנן גדולי ישראל שליט״א'
TOC_FIRST_Y, TOC_NEXT_Y, TOC_BOTTOM = 240.0, 128.0, 872.0        # css px: the first band / the first line of a continuation page / the lowest baseline
TOC_STEP = dict(article=41.0, haskama=31.0, part=26.0, sub=21.0)  # distance from the baseline of an entry to the baseline of the next one
HASKAMA_OLD, HASKAMA_NEW = 'הסכמות', 'הסכמה'


def book_headings(pdf, first, last):
    """the part headings (Ashkenazy 19.33: 'ענף א') and the sub-headings (Livorna 15.33) of the pages first..last of the full booklet:
    [(page, kind, text)], 'part' = the heading with its title; consecutive lines of one heading are joined"""
    import collections
    found = []
    for pn in range(first, last + 1):
        pg = pdf.pages[pn - 1]
        ops = list(pikepdf.parse_content_stream(pg))
        inv = {k: {c: ch for ch, c in glyph_codes(v).items()} for k, v in (pg.Resources.get('/Font') or {}).items() if v.get('/Subtype') == '/Type3'}
        groups = collections.defaultdict(list)
        for b in split_blocks(ops):
            if not b['codes'] or None in b['codes']:
                continue
            kind = 'part' if b['font'] == '/F47' and abs(b['size'] - 19.33) < 0.02 else 'sub' if b['font'] == '/F40' and abs(b['size'] - 15.33) < 0.02 else None
            if kind:
                groups[(kind, b['y'])].append((b['x'], ''.join(inv[b['font']].get(c, '?') for c in reversed(b['codes']))))
        for (kind, y), items in sorted(groups.items(), key=lambda kv: kv[0][1]):
            found.append((pn, kind, y, ''.join(t for x, t in sorted(items, key=lambda i: -i[0]))))
    out = []
    for pn, kind, y, text in found:
        text = text.strip().rstrip(':').strip()
        if kind == 'sub' and out and out[-1][0] == pn and abs(y - out[-1][2]) < 30:
            prev = out[-1]                                          # the title of a part heading / the second line of a heading
            out[-1] = (pn, prev[1], y, prev[3] + (' – ' if prev[1] == 'part' and ' – ' not in prev[3] else ' ') + text)
        else:
            out.append((pn, kind, y, text))
    return [(pn, kind, text) for pn, kind, y, text in out]


def toc_items(pdf, art1, art2, author):
    """the entries of the table of contents in order: (kind, text, source page); kinds: band, haskama, article, part, sub"""
    items = [('band', TOC_TITLE_BANDS[0], None), ('haskama', HASKAMA_LINE, 'haskama'), ('band', TOC_TITLE_BANDS[1], None),
             ('article', 'החובה להתאמץ בדור אחרון', art1[0]), ('article', NEW_TITLE if author else OLD_TITLE, art2[0])]
    for pn, kind, text in book_headings(pdf, art2[0], art2[1]):
        items.append((kind, text, pn))
    return items


def toc_layout(items):
    """pagination of the entries: [[(item, baseline or band top)]], css px"""
    pages, cur, y = [], [], TOC_FIRST_Y
    first = True
    for it in items:
        kind = it[0]
        need = 52 if kind == 'band' else 40
        if y + need > TOC_BOTTOM and cur:
            pages.append(cur)
            cur, y, first = [], TOC_NEXT_Y, False
        if kind == 'band':
            top = y if (not cur or y == TOC_FIRST_Y) else y + 2
            cur.append((it, top))
            y = top + 52
        else:
            cur.append((it, y))
            y += TOC_STEP[kind]
    pages.append(cur)
    return pages


def toc_pages(pdf, base, layout, printed, first_no):
    """the pages of the table of contents (a copy of the old one in the Type 3 fonts of the booklet); printed(src) -> Hebrew numeral of a source page"""
    orig = list(pikepdf.parse_content_stream(base))
    fonts = base.Resources.Font
    f50, f51 = fonts['/F50'], fonts['/F51']
    c50, c51 = glyph_codes(f50), glyph_codes(f51)
    blocks = split_blocks(orig)
    t_art = next(b for b in blocks if b['font'] == '/F51' and abs(b['size'] - 16) < 0.01)
    right = t_art['x'] + sum(advances(f51, t_art['codes'], 16))                     # the right edge of the entries
    t_band = next(b for b in blocks if b['font'] == '/F50' and abs(b['size'] - 18) < 0.01)
    right_band = t_band['x'] + sum(advances(f50, t_band['codes'], 18))
    auth = [b for b in blocks if b['font'] == '/F52'][1]                                   # the second author line of the old table of contents: Zada
    auth_ops = orig[auth['start']:auth['end'] + 1]
    i45 = next(k for k, x in enumerate(orig) if str(x.operator) == 'Do' and str(x.operands[0]) == '/X45')
    i48 = next(k for k, x in enumerate(orig) if str(x.operator) == 'Do' and str(x.operands[0]) == '/X48')
    title_ops = orig[i45 - 5:i48 + 2]
    head_codes = head_text(base, orig)
    shift = 11812.5 / 3.125                                                              # the text coordinates of this page group are css px + 3780
    group = lambda: [CSI([], Operator('q')), CSI([Decimal('3.125'), 0, 0, Decimal('3.125'), Decimal('-2.4902344'), Decimal('-11812.5')], Operator('cm')),
                     CSI([0], Operator('G')), CSI([0], Operator('g')), CSI([Name('/G3')], Operator('gs'))]
    def codes(cmap, text):
        return [cmap[MIRROR.get(c, c)] for c in reversed(text)]
    def put(ops, font_name, font, cmap, size, text, x_right, y):
        cs = codes(cmap, text)
        w = sum(advances(font, cs, size))
        ops += text_block(font_name, size, x_right - w, y + shift, cs, font)
        return x_right - w
    pages = []
    for pi, page_items in enumerate(layout):
        no = first_no + pi
        ops = rebuild_header(base, list(orig), no % 2 == 1, hebrew_number(no - NUM_OFFSET), head_codes)
        k43 = next(k for k, x in enumerate(ops) if str(x.operator) == 'Do' and str(x.operands[0]) == '/X43')
        out = ops[:k43 + 2]
        if pi == 0:
            out += title_ops
        out += group()
        for (kind, text, src), y in page_items:
            if kind == 'band':
                top = y + shift
                out += [CSI([Decimal('0.902')], Operator('g')), CSI([73, Decimal(f'{top:.2f}'), 519, 31], Operator('re')), CSI([], Operator('f')),
                        CSI([0], Operator('g')), CSI([73, Decimal(f'{top:.2f}'), 519, 1], Operator('re')), CSI([], Operator('f')),
                        CSI([73, Decimal(f'{top + 30:.2f}'), 519, 1], Operator('re')), CSI([], Operator('f'))]
                put(out, '/F50', f50, c50, 18, text, right_band, y + 21)
                continue
            size, ind = {'article': (16, 0), 'haskama': (15, 0), 'part': (14.66, 18), 'sub': (13.33, 38)}[kind]
            x_left = put(out, '/F51', f51, c51, size, text, right - ind, y)
            num = printed(src)
            ncs = codes(c50, num)
            nw = sum(advances(f50, ncs, 14.66))
            out += text_block('/F50', 14.66, 73.3125, y + 2 + shift, ncs, f50)
            out += [CSI([], Operator('q')), CSI([1], Operator('w')), CSI([[1, 1], 0], Operator('d')), CSI([0], Operator('G')),
                    CSI([Decimal(f'{73.3125 + nw + 7:.2f}'), Decimal(f'{y + 1.5 + shift:.2f}')], Operator('m')),
                    CSI([Decimal(f'{x_left - 6:.2f}'), Decimal(f'{y + 1.5 + shift:.2f}')], Operator('l')), CSI([], Operator('S')), CSI([], Operator('Q'))]
            if kind == 'article':
                out += [CSI([Decimal('0.1333')], Operator('g'))]
                blk = list(auth_ops)
                for k, ins in enumerate(blk):
                    if str(ins.operator) == 'Tm':
                        t = list(ins.operands)
                        t[5] = Decimal(f'{y + 17 + shift:.2f}')
                        blk[k] = CSI(t, Operator('Tm'))
                out += blk + [CSI([0], Operator('g'))]
        out.append(CSI([], Operator('Q')))
        pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
            Type=Name.Page, MediaBox=base.MediaBox, Resources=base.Resources, Contents=pdf.make_stream(pikepdf.unparse_content_stream(out))))))
    return pages


def haskama_page(page):
    """the page of the haskama as it was sent, with the title 'הסכמות' changed to 'הסכמה' (centred where the old title was centred)"""
    form = page.Resources.XObject['/X41']
    ops = list(pikepdf.parse_content_stream(form))
    f8 = form.Resources.Font['/F8']
    cmap = glyph_codes(f8)
    inv = {c: ch for ch, c in cmap.items()}
    for b in split_blocks(ops):
        if b['font'] == '/F8' and b['codes'] and None not in b['codes'] and ''.join(inv.get(c, '?') for c in reversed(b['codes'])) == HASKAMA_OLD:
            ncodes = [cmap[c] for c in reversed(HASKAMA_NEW)]
            centre = b['x'] + sum(advances(f8, b['codes'], b['size'])) / 2
            x = centre - sum(advances(f8, ncodes, b['size'])) / 2
            ops[b['start']:b['end'] + 1] = text_block('/F8', b['size'], x, b['y'], ncodes, f8)
            form.write(pikepdf.unparse_content_stream(ops))
            return page
    raise ValueError('the title of the haskama was not found')


def import_page(pdf, path, keep):
    """a one-page PDF appended to pdf; returns the page (the source stays open in keep until pdf is saved)"""
    other = pikepdf.open(path)
    keep.append(other)
    pdf.pages.append(other.pages[0])
    return pdf.pages[-1]


def build(src, out, title='beinyan', name=BOOKLET_NAME, algebra=None, fonts=None, haskama=None, prospectus=None):
    pdf = pikepdf.open(src)
    P = pdf.pages
    keep_open = []
    parse = lambda n: list(pikepdf.parse_content_stream(P[n - 1]))
    author = head_text(P[SRC_AUTHOR - 1], parse(SRC_AUTHOR))
    title1 = head_text(P[SRC_TITLE1 - 1], parse(SRC_TITLE1))
    title2 = head_text(P[SRC_TITLE2 - 1], parse(SRC_TITLE2))
    assert decode(title2) == OLD_TITLE
    if title == 'beinyan':
        title2 = visual(NEW_TITLE)
    has_pg = haskama_page(import_page(pdf, haskama, keep_open)) if haskama else None
    pro_pg = import_page(pdf, prospectus, keep_open) if prospectus else None
    items = toc_items(pdf, ART1, ART2, title == 'beinyan') if fonts else None
    layout = toc_layout(items) if items else []
    # every article begins on an odd page, the back cover is an even page, the number of pages is a multiple of 4; the page before the back cover is the
    # inside of the cover (the prospectus); empty pages fill the gaps
    plan = [('keep', k) for k in FRONT] + ([('memorial', None)] if fonts else []) + [('toc', i) for i in range(len(layout))] + ([('haskama', None)] if haskama else [])
    for n in [n for n in range(ART1[0], ART1[1] + 1)] + [n for n in range(ART2[0], ART2[1] + 1)]:
        if n in (ART1[0], ART2[0]) and len(plan) % 2 == 1:
            plan.append(('blank', None))
        plan.append(('art', n))
    while (len(plan) + 2) % 4:
        plan.append(('blank', None))
    plan += [('prospectus', None) if prospectus else ('blank', None), ('keep', BACK)]
    assert len(plan) % 4 == 0 and all(len(plan[:i]) % 2 == 0 for i, (k, n) in enumerate(plan) if k == 'art' and n in (ART1[0], ART2[0])), 'parity'
    new_of = {n: i + 1 for i, (k, n) in enumerate(plan) if k == 'art'}                     # source page -> page of the booklet
    haskama_no = next((i + 1 for i, (k, n) in enumerate(plan) if k == 'haskama'), None)
    printed = lambda s: hebrew_number((haskama_no if s == 'haskama' else new_of[s]) - NUM_OFFSET)
    pages, blank_src = [], P[FRONT[1] - 1]
    for new_no, (kind, n) in enumerate(plan, 1):
        if kind == 'memorial':
            pages.append(memorial_page(pdf, P[3].Resources.XObject['/X34'], algebra, blank_src, fonts))
            continue
        if kind == 'toc':
            pages.append(None)                                         # filled in below, when the numbers of all pages are known
            continue
        if kind == 'haskama':
            pages.append(has_pg)
            continue
        if kind == 'prospectus':
            pages.append(pro_pg)
            continue
        if kind == 'blank':
            pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
                Type=Name.Page, MediaBox=blank_src.MediaBox, Resources=pikepdf.Dictionary(), Contents=pdf.make_stream(b'')))))
            continue
        pg = P[n - 1]
        if kind == 'keep' and algebra and n in (1, 3, 4):
            ops = list(pikepdf.parse_content_stream(pg))
            ops = credits_box(pg, ops) if n == 4 else memorial_cover(
                pg, ops, {'/F10', '/F11'} if n == 1 else {'/F24', '/F25'}, COVER_SUB if n == 1 else None, algebra)
            pg.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
            if n == 3:
                move_medallion(pdf, pg)
        if kind == 'art':
            odd = new_no % 2 == 1
            t = (title1 if ART1[0] <= n <= ART1[1] else title2) if odd else author
            ops = rebuild_header(pg, parse(n), odd, hebrew_number(new_no - NUM_OFFSET), t, name)
            if n == ART2[0] and title == 'beinyan':
                ops = title_page(pg, ops)
            pg.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
        pages.append(pg)
    first_toc = next((i + 1 for i, (k, n) in enumerate(plan) if k == 'toc'), None)
    if first_toc:
        toc = toc_pages(pdf, P[4], layout, printed, first_toc)
        pages = [toc[plan[i][1]] if plan[i][0] == 'toc' else p for i, p in enumerate(pages)]
    keep = [p.obj for p in pages]
    del P[:]
    for p in keep:
        P.append(pikepdf.Page(p))
    pdf.save(out, linearize=False, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    print(f'{out}: {len(keep)} pages; plan: ' + ' '.join(f'{i + 1}{k[0]}' for i, (k, n) in enumerate(plan)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('booklet'), ap.add_argument('out')
    ap.add_argument('--title', choices=['beinyan', 'plain'], default='beinyan')
    ap.add_argument('--algebra', help='EFT Algebra font file (the client\'s): switches the front pages to the memorial version')
    ap.add_argument('--title-font', help='Hebrew display font (Guttman Mantova Bold) for the memorial text page')
    ap.add_argument('--text-font', help='FrankRuehl DP regular for the memorial text page')
    ap.add_argument('--text-bold', help='FrankRuehl DP bold for the memorial text page')
    ap.add_argument('--haskama', help='one-page PDF of the haskama (its title is changed to the singular)')
    ap.add_argument('--prospectus', help='one-page PDF for the inside of the back cover')
    ap.add_argument('--name', default=BOOKLET_NAME, help='name of the booklet in the running head')
    a = ap.parse_args()
    fonts = dict(title=a.title_font, text=a.text_font, bold=a.text_bold) if a.title_font else None
    build(a.booklet, a.out, a.title, a.name, a.algebra, fonts, a.haskama, a.prospectus)
