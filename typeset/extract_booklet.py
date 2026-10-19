#!/usr/bin/env python3
"""Cuts a small booklet out of the finished full booklet PDF (vector pages are copied, nothing is rasterised) - the original is not touched.

usage: python extract_booklet.py booklet.pdf out.pdf

Used for the memorial booklet: the cover pages (cover, inner title page, credits, back cover) + the two articles of R. Moshe Zada (the opening
"החובה להתאמץ בדור אחרון" and the one that stands as "הזכרת השם" in the full booklet, here retitled "בעניין כוונת השם" without the line "קונטרס").
No dividers, no table of contents.

What is done to the pages (the PDF comes out of Chromium; the fonts of the title and the header are Type 3 fonts that carry the whole alphabet, so new
text is set with the same glyphs at the advances of the font - nothing is substituted):
  * parity: the pages keep their physical parity (a mirrored running head: number at the outer edge), so an article that began on an even page
    still begins on an even page; white pages are inserted where a divider / the table of contents used to be
  * page numbers: printed number = physical page - 4 (alef = physical page 5, as in the full booklet), re-set on every article page
  * running head of the odd pages of the second article: "הזכרת השם" -> "בעניין כוונת השם" (the group is right-aligned, so the new title grows to the left)
  * title page of the second article: new title in the same frame (the frame has a minimum width and the longer title still fits), the line
    "קונטרס" removed; the body text is NOT reflowed (every column keeps its place), so the extra line is shared between the three gaps of the head
    block (header-frame, frame-author, author-text) instead of staying as one hole
Needs: pip install pikepdf"""
import sys
from decimal import Decimal
import pikepdf
from pikepdf import Name, Operator, String, ContentStreamInstruction as CSI

# source page numbers (1 = cover) of the full booklet
FRONT = [1, 2, 3, 4]                  # cover, empty page inside the cover, inner title page, credits
ART1 = (20, 22)                       # "החובה להתאמץ בדור אחרון" (Moshe Zada, the opening articles' second)
ART2 = (84, 120)                      # "הזכרת השם" (Moshe Zada) -> "בעניין כוונת השם"
BACK = 634
OLD_TITLE, NEW_TITLE = 'הזכרת השם', 'בעניין כוונת השם'
NUM_OFFSET = 4                        # printed number = physical page - 4
BANNER_SHARE = Decimal('22.9167')     # one third of the freed line (68.75 units) in the units of the 0.24 pt matrix of the page
PAGE_W_PX, MARGIN_PX = 665, 73.3125   # page width in css px, outer margin (19.4 mm)


def letter_code(ch):                  # Type 3 fonts of the booklet: code = 0xAF + (letter - alef)
    return 0xAF + ord(ch) - 0x05D0


def hebrew_number(n):
    ones, tens = 'אבגדהוזחט', 'יכלמנסעפצ'
    if n in (15, 16):
        return 'טו' if n == 15 else 'טז'
    assert 1 <= n < 100
    return (tens[n // 10 - 1] if n >= 10 else '') + (ones[n % 10 - 1] if n % 10 else '')


def decode(codes):
    """logical text of a run of codes (the codes are stored in visual order, left to right)"""
    return ''.join(' ' if c == 3 else chr(0x05D0 + c - 0xAF) if 0xAF <= c <= 0xC9 else '?' for c in reversed(codes))


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
    """(start, end, font name, size, x, y, codes) of every BT..ET block that shows Type 3 glyphs one byte at a time"""
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


def retitle_header(pdf, page, ops, odd, num_text, old_title=None, new_title=None):
    """renumbers the page and (odd pages) swaps the title of the running head; returns the new instruction list"""
    fonts = page.Resources.Font
    blocks = split_blocks(ops)
    edits = []
    num = next(b for b in blocks if b['font'] == '/F40' and abs(b['size'] - 17.33) < 0.01)
    f40 = fonts['/F40']
    old_end = num['x'] + sum(advances(f40, num['codes'], 17.33))
    codes = [letter_code(c) for c in reversed(num_text)]          # visual order = left to right
    width = sum(advances(f40, codes, 17.33))
    if odd:
        x = num['x']                                               # outer edge is the left one
    else:
        assert abs(old_end - (PAGE_W_PX - MARGIN_PX)) < 0.3, old_end
        x = old_end - width                                        # outer edge is the right one
    edits.append((num['start'], num['end'], text_block('/F40', 17.33, x, num['y'], codes, f40)))
    if odd and old_title:
        f41 = fonts['/F41']
        tb = next(b for b in blocks if b['font'] == '/F41' and abs(b['size'] - 13.33) < 0.01 and decode(b['codes']) == old_title)
        end = tb['x'] + sum(advances(f41, tb['codes'], 13.33))
        ncodes = [3 if c == ' ' else letter_code(c) for c in reversed(new_title)]
        nw = sum(advances(f41, ncodes, 13.33))
        edits.append((tb['start'], tb['end'], text_block('/F41', 13.33, end - nw, tb['y'], ncodes, f41)))
    for s, e, new in sorted(edits, reverse=True):
        ops[s:e + 1] = new
    return ops


def title_page(pdf, page, ops):
    """new title in the frame, 'קונטרס' removed, the freed line shared between the gaps of the head block"""
    f47 = page.Resources.Font['/F47']
    blocks = split_blocks(ops)
    old = next(b for b in blocks if b['font'] == '/F47' and abs(b['size'] - 22) < 0.01)
    assert decode(old['codes']) == OLD_TITLE
    centre = old['x'] + sum(advances(f47, old['codes'], 22)) / 2
    ncodes = [3 if c == ' ' else letter_code(c) for c in reversed(NEW_TITLE)]
    nw = sum(advances(f47, ncodes, 22))
    dy = float(BANNER_SHARE) / 3.125                               # Tm units
    kon = next(b for b in blocks if b['font'] == '/F41' and abs(b['size'] - 14.66) < 0.01 and decode(b['codes']) == 'קונטרס')
    aut = next(b for b in blocks if b['font'] == '/F80')
    # images of the frame (cloud, left cap, middle, right cap) move down by one share; the title with them
    for k, (o, op) in enumerate((x.operands, str(x.operator)) for x in ops):
        if op == 'cm' and len(o) == 6 and float(o[3]) < 0 and float(o[0]) > 60 and 150 < -float(o[3]) < 200 and float(o[0]) != 1621.875:
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


def build(src, out):
    pdf = pikepdf.open(src)
    P = pdf.pages
    plan = [('keep', n) for n in FRONT] + [('blank', None)] + [('art', n) for n in range(ART1[0], ART1[1] + 1)] + [('blank', None)] + \
           [('art', n) for n in range(ART2[0], ART2[1] + 1)] + [('blank', None), ('keep', BACK)]
    assert len(plan) % 4 == 0, len(plan)
    pages, blank_src = [], P[FRONT[1] - 1]
    for new_no, (kind, n) in enumerate(plan, 1):
        if kind == 'blank':
            pg = pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
                Type=Name.Page, MediaBox=blank_src.MediaBox, Resources=pikepdf.Dictionary(), Contents=pdf.make_stream(b''))))
            pages.append(pg)
            continue
        pg = P[n - 1]
        if kind == 'art':
            assert new_no % 2 == n % 2, 'parity of page %d would change' % n
            ops = list(pikepdf.parse_content_stream(pg))
            num = hebrew_number(new_no - NUM_OFFSET)
            retitle = ART2[0] <= n <= ART2[1]
            ops = retitle_header(pdf, pg, ops, new_no % 2 == 1, num, OLD_TITLE if retitle and new_no % 2 == 1 else None, NEW_TITLE)
            if n == ART2[0]:
                ops = title_page(pdf, pg, ops)
            pg.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
        pages.append(pg)
    keep = [p.obj for p in pages]
    del P[:]
    for p in keep:
        P.append(pikepdf.Page(p))
    pdf.save(out, linearize=False, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    print(f'{out}: {len(keep)} pages')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
