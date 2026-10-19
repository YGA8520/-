#!/usr/bin/env python3
"""Cuts a small booklet out of the finished full booklet PDF (vector pages are copied, nothing is rasterised) - the original is not touched.

usage: python extract_booklet.py booklet.pdf out.pdf [--title beinyan|plain]

Used for the memorial booklet: the cover pages (cover, inner title page, credits, back cover) + the two articles of R. Moshe Zada (the opening
"החובה להתאמץ בדור אחרון" and the one that stands as "הזכרת השם" in the full booklet). No dividers, no table of contents.
  --title beinyan  (default)  the second article is retitled "בעניין הזכרת השם" and the line "קונטרס" under its title is removed
  --title plain               the second article keeps its title block exactly as it is: "הזכרת השם" with the line "קונטרס"

What is done to the pages (the PDF comes out of Chromium; the fonts of the title and the header are Type 3 fonts that carry the whole alphabet, so new
text is set with the same glyphs at the advances of the font - nothing is substituted):
  * layout: front pages, an empty page 5 (the first article keeps its even page), the first article on 6-8, the second article follows at once, on page 9
    (odd), two empty pages and the back cover (48 pages, a multiple of 4). The running head is mirrored (number at the outer edge, the group "name of the
    booklet + title / author" at the other side), the page body is symmetric (equal margins), so the pages of the second article, which moved from even
    to odd and back, only get their head mirrored: the number, the booklet name and the bullet change sides and the author / the title change places
  * page numbers: printed number = physical page - 4 (alef = physical page 5, as in the full booklet), re-set on every article page
  * title page of the second article (--title beinyan): new title in the same frame (the frame has a minimum width and the longer title still fits),
    the line "קונטרס" removed; the body text is NOT reflowed (every column keeps its place), so the extra line is shared between the three gaps of the head
    block (header-frame, frame-author, author-text) instead of staying as one hole
  * memorial cover pages (--algebra FONT.ttf): on the cover (page 1) and on the grey inner title page (page 3) the title "פלפולא דאורייתא" is replaced by
    the new name (two lines, outlines of the original display font EFT Algebra, same gold / grey fill), the two curved lines (the quotation round
    the circle and "חבורות ● שיעורים ..." under it) are removed, the subtitle is replaced (outlines of Lulav CLM Bold); the logo stays
  * credits page: one more line (typesetting credit); the whole column moves up a little to keep the margins
Needs: pip install pikepdf fonttools"""
import argparse
import os
from decimal import Decimal
import pikepdf
from pikepdf import Name, Operator, String, ContentStreamInstruction as CSI
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

# source page numbers (1 = cover) of the full booklet
FRONT = [1, 2, 3, 4]                  # cover, empty page inside the cover, inner title page, credits
ART1 = (20, 22)                       # "החובה להתאמץ בדור אחרון" (Moshe Zada)
ART2 = (84, 120)                      # "הזכרת השם" (Moshe Zada)
BACK = 634
SRC_AUTHOR, SRC_TITLE1, SRC_TITLE2 = 84, 21, 85    # pages whose running head carries the author (even) / the titles (odd)
OLD_TITLE, NEW_TITLE = 'הזכרת השם', 'בעניין הזכרת השם'
NUM_OFFSET = 4                        # printed number = physical page - 4
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
LULAV = os.path.join(HERE, 'assets', 'fonts', 'LulavCLM-Bold.otf')
COVER_TITLE = ('הזכרת', 'השם')                      # line 1 (right), line 2 (left)
COVER_TITLE_SIZE = 190.0
COVER_LINES = dict(y1=708.0, y2=878.0, right1=1119.66, left2=346.5)      # baselines and the edges of the two lines of the original title
COVER_SUB = ('בעניין הכוונה בהזכרת שם השם', 'ושמות שאינם נמחקים')
CREDIT_TEXT, CREDIT_PHONE = 'עימוד ועיצוב י.א. - ', '0534185035'
CREDIT_SHIFT, CREDIT_GAP = 18.0, 36.0              # css px: the column moves up, the new line sits this far under the last one


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
    """a font file as a source of outlines: text is drawn as filled paths (the fill, a colour or the gold / grey pattern, is the one in force)"""
    def __init__(self, path):
        self.f = TTFont(path)
        self.cmap, self.gs, self.upem = self.f.getBestCmap(), self.f.getGlyphSet(), self.f['head'].unitsPerEm

    def width(self, text, size):
        return sum(self.f['hmtx'][self.cmap[ord(c)]][0] for c in text) * size / self.upem

    def ops(self, text, size, x, y):
        """text (logical order) with its left edge at x and its baseline at y of the page's flipped coordinate system"""
        out, sc = [], size / self.upem
        for c in reversed(text):
            g = self.cmap[ord(c)]
            pen = PdfPen(self.gs)
            self.gs[g].draw(pen)
            if pen.ops:
                out += [CSI([], Operator('q')), CSI([Decimal(f'{sc:.6f}'), 0, 0, Decimal(f'{-sc:.6f}'), Decimal(f'{x:.3f}'), Decimal(f'{y:.3f}')], Operator('cm'))]
                out += pen.ops + [CSI([], Operator('f')), CSI([], Operator('Q'))]
            x += self.f['hmtx'][g][0] * sc
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


def memorial_cover(page, ops, algebra, curved):
    """new name, no curved lines, new subtitle (page 1 = colour cover, page 3 = grey inner title page: same structure)"""
    lulav = Outline(LULAV)
    blocks = split_blocks(ops)
    titles = [b for b in blocks if abs(b['size'] - 165) < 0.01]
    subs = [b for b in blocks if abs(b['size'] - 42) < 0.01]
    assert len(titles) == 2 and len(subs) == 2
    edits = [(a, b, []) for a, b in curved_groups(ops, curved)]
    L = COVER_LINES
    w1 = algebra.width(COVER_TITLE[0], COVER_TITLE_SIZE)
    edits.append((titles[0]['start'], titles[0]['end'], algebra.ops(COVER_TITLE[0], COVER_TITLE_SIZE, L['right1'] - w1, L['y1'])))
    edits.append((titles[1]['start'], titles[1]['end'], algebra.ops(COVER_TITLE[1], COVER_TITLE_SIZE, L['left2'], L['y2'])))
    fonts = page.Resources.Font
    for old, text in zip(subs, COVER_SUB):                          # centred where the old line was centred
        w_old = sum(advances(fonts[old['font']], old['codes'], 42))
        centre = old['x'] + w_old / 2
        edits.append((old['start'], old['end'], lulav.ops(text, 42, centre - lulav.width(text, 42) / 2, old['y'])))
    for a, b, new in sorted(edits, key=lambda e: -e[0]):
        ops[a:b + 1] = new
    return ops


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


def credits_line(page, ops):
    """the typesetting credit under the last line of the credits page; the column (texts and flourishes) moves up first"""
    f32, f33 = page.Resources.Font['/F32'], page.Resources.Font['/F33']
    blocks = split_blocks(ops)
    centres = []
    for b in blocks:                                               # the axis of the column = the centre of its centred lines
        if b['codes'] and None not in b['codes'] and b['font'] in ('/F32', '/F33'):
            centres.append(b['x'] + sum(advances(page.Resources.Font[b['font']], b['codes'], b['size'])) / 2)
    centres.sort()
    axis = centres[len(centres) // 2]
    last = max(blocks, key=lambda b: b['y'])
    for k, op in enumerate(ops):                                   # shift up: images are placed by cm (units of 0.24 pt matrix), texts by Tm
        if str(op.operator) == 'cm' and len(op.operands) == 6 and float(op.operands[0]) > 100 and k > 35 and float(op.operands[0]) < 1000:
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
    hebrew = [c32[c] for c in reversed(CREDIT_TEXT)]               # visual order, left to right: number, " - ", the Hebrew (reversed)
    number = [c33[c] for c in CREDIT_PHONE]
    w_h = sum(advances(f32, hebrew, size))
    w_n = sum(advances(f33, number, size))
    x0 = axis - (w_h + w_n) / 2
    new = text_block('/F33', size, x0, y, number, f33) + text_block('/F32', size, x0 + w_n, y, hebrew, f32)
    end = max(k for k, op in enumerate(ops) if str(op.operator) == 'ET')
    ops[end + 1:end + 1] = new                                     # inside the group of the last line (same fill, same matrix)
    return ops


def build(src, out, title='beinyan', name=BOOKLET_NAME, algebra=None):
    pdf = pikepdf.open(src)
    P = pdf.pages
    parse = lambda n: list(pikepdf.parse_content_stream(P[n - 1]))
    author = head_text(P[SRC_AUTHOR - 1], parse(SRC_AUTHOR))
    title1 = head_text(P[SRC_TITLE1 - 1], parse(SRC_TITLE1))
    title2 = head_text(P[SRC_TITLE2 - 1], parse(SRC_TITLE2))
    assert decode(title2) == OLD_TITLE
    if title == 'beinyan':
        title2 = visual(NEW_TITLE)
    plan = [('keep', n) for n in FRONT] + [('blank', None)] + [('art', n) for n in range(ART1[0], ART1[1] + 1)] + \
           [('art', n) for n in range(ART2[0], ART2[1] + 1)] + [('blank', None)] * 2 + [('keep', BACK)]
    assert len(plan) % 4 == 0, len(plan)
    pages, blank_src = [], P[FRONT[1] - 1]
    for new_no, (kind, n) in enumerate(plan, 1):
        if kind == 'blank':
            pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
                Type=Name.Page, MediaBox=blank_src.MediaBox, Resources=pikepdf.Dictionary(), Contents=pdf.make_stream(b'')))))
            continue
        pg = P[n - 1]
        if kind == 'keep' and algebra and n in (1, 3, 4):
            ops = list(pikepdf.parse_content_stream(pg))
            ops = credits_line(pg, ops) if n == 4 else memorial_cover(pg, ops, algebra, {'/F10', '/F11'} if n == 1 else {'/F24', '/F25'})
            pg.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
        if kind == 'art':
            odd = new_no % 2 == 1
            t = (title1 if ART1[0] <= n <= ART1[1] else title2) if odd else author
            ops = rebuild_header(pg, parse(n), odd, hebrew_number(new_no - NUM_OFFSET), t, name)
            if n == ART2[0] and title == 'beinyan':
                ops = title_page(pg, ops)
            pg.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
        pages.append(pg)
    keep = [p.obj for p in pages]
    del P[:]
    for p in keep:
        P.append(pikepdf.Page(p))
    pdf.save(out, linearize=False, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    print(f'{out}: {len(keep)} pages')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('booklet'), ap.add_argument('out')
    ap.add_argument('--title', choices=['beinyan', 'plain'], default='beinyan')
    ap.add_argument('--algebra', help='EFT Algebra font file: switches the cover pages and the credits page to the memorial version')
    ap.add_argument('--name', default=BOOKLET_NAME, help='name of the booklet in the running head')
    a = ap.parse_args()
    build(a.booklet, a.out, a.title, a.name, Outline(a.algebra) if a.algebra else None)
