#!/usr/bin/env python3
"""Cover page of the Ritcha D'Oraita booklet = the cover of the previous booklet (output/cover.pdf) with the title text replaced.

The title of the old cover is live text in EFT Algebra (client font, not in the repo); the PDF carries a subset of it with the letters of
"פלפולא דאורייתא".  Every letter of "ריתחא" is in that subset except ח, which is drawn here from the font's own strokes
(the roof and right stem of ד + a second stem of the same shape on the left).  Everything else on the page (background, medallion,
arcs, subtitle lines, logo) is kept byte for byte.  The gradient of the first title line (edge colour -> core colour -> edge colour)
is stretched over the new, shorter line.

usage: python3 make_cover_ritcha.py [src_cover.pdf] [out_cover.pdf]
"""
import io, re, sys, os
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'output', 'cover.pdf')
OUT = sys.argv[2] if len(sys.argv) > 2 else 'cover_176x250.pdf'

TITLE_FONT_XREF = 8          # the EFTAlgebra subset that carries the title ("פלפולא דאורייתא"), see the page resources of the old cover
PATTERN_XREF = 7             # gradient of the first title line
SIZE = 165.0                 # font size of the title in the 1408-grid of the cover (config.json -> cover.geometry.title.size)
BASE_Y = 718.0               # baseline of the first title line
CENTRE_X = 888.5             # centre of the first title line (cover.geometry.title.x1)
WORD = 'ריתחא'               # the new first line


class PdfPen(BasePen):
    """glyph outline -> PDF path operators in the (flipped) coordinate system of the cover grid"""
    def __init__(self, glyphset, x0, y0, s):
        super().__init__(glyphset); self.x0, self.y0, self.s = x0, y0, s; self.ops = []
    def p(self, pt): return '%.3f %.3f' % (self.x0 + pt[0] * self.s, self.y0 - pt[1] * self.s)
    def _moveTo(self, pt): self.ops.append(self.p(pt) + ' m')
    def _lineTo(self, pt): self.ops.append(self.p(pt) + ' l')
    def _curveToOne(self, a, b, c): self.ops.append('%s %s %s c' % (self.p(a), self.p(b), self.p(c)))
    def _closePath(self): self.ops.append('h')


def het_contours(gs):
    """ח built from ד: its roof (with the small flicks at both ends) and right stem are kept, the left stem is a copy of the right one
    (a stem with its pointed foot) that starts under the left end of the roof."""
    rec = RecordingPen(); gs['uni05D3'].draw(rec)
    dx = 100 - 336                                    # the right stem's left edge is at x=336 -> the new stem's left edge at x=100
    stem = [('moveTo', ((395 + dx, 400),)), ('lineTo', ((395 + dx, 334),)), ('lineTo', ((395 + dx, 274),)), ('lineTo', ((393 + dx, 89),)),
            ('qCurveTo', tuple((x + dx, y) for x, y in ((393, 65), (381, 31), (365, 8), (346, -7), (339, -11)))),
            ('lineTo', ((336 + dx, 299),)), ('lineTo', ((336 + dx, 400),)), ('closePath', ())]
    return rec.value + stem


def draw(gs, name, x0, y0, s, contours=None):
    pen = PdfPen(gs, x0, y0, s)
    if contours is None:
        gs[name].draw(pen)
    else:
        from fontTools.pens.basePen import decomposeQuadraticSegment
        for op, args in contours:
            if op == 'moveTo': pen.moveTo(*args)
            elif op == 'lineTo': pen.lineTo(*args)
            elif op == 'qCurveTo': pen.qCurveTo(*args)
            elif op == 'closePath': pen.closePath()
    return pen.ops


def main():
    doc = fitz.open(SRC)
    page = doc[0]
    assert abs(page.rect.width - 498.96) < 0.1
    name, ext, typ, buf = doc.extract_font(TITLE_FONT_XREF)
    font = TTFont(io.BytesIO(buf)); gs = font.getGlyphSet(); hm = font['hmtx']
    glyph = {'א': 'uni05D0', 'ת': 'uni05EA', 'י': 'uni05D9', 'ר': 'uni05E8', 'ח': 'uni05D7'}
    adv = {c: hm[g][0] if c != 'ח' else hm['uni05D3'][0] for c, g in glyph.items()}
    visual = WORD[::-1]                                # left to right on the page
    total = sum(adv[c] for c in visual) * SIZE / 1000.0
    xs = CENTRE_X - total / 2; xe = CENTRE_X + total / 2
    ops = []; x = xs
    for c in visual:
        if c == 'ח': ops += draw(gs, None, x, BASE_Y, SIZE / 1000.0, het_contours(gs))
        else:        ops += draw(gs, glyph[c], x, BASE_Y, SIZE / 1000.0)
        x += adv[c] * SIZE / 1000.0
    new_block = '/Pattern CS/Pattern cs/P7 SCN/P7 scn\n' + '\n'.join(ops) + '\nf\n'

    xref = page.get_contents()[0]
    s = doc.xref_stream(xref).decode('latin-1')
    # the first title line = the first text block that uses F8 (up to its ET), preceded by the pattern selection
    m = re.search(r'/Pattern CS/Pattern cs/P7 SCN/P7 scn\nBT\n/ReversedChars BMC\n/F8 165 Tf\n.*?\nEMC\nET\n', s, re.S)
    assert m, 'title block not found'
    s = s[:m.start()] + new_block + s[m.end():]
    doc.update_stream(xref, s.encode('latin-1'))
    doc.xref_set_key(PATTERN_XREF, 'Shading/Coords', '[%.2f 0 %.2f 0]' % (xs, xe))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT, garbage=3, deflate=True)
    print('wrote', OUT, 'line 1: x %.1f .. %.1f' % (xs, xe))


if __name__ == '__main__':
    main()
