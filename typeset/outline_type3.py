#!/usr/bin/env python3
"""Turns the text in Type 3 fonts of a PDF into vector shapes (the glyphs become small form XObjects, one per glyph of a font, shared by all pages).

The booklet comes out of Chromium with its display / lead / note fonts as Type 3 fonts.  Some viewers (Adobe Acrobat in a printing house) draw such text as dots
when the file went through a conversion, so the print files do not depend on them: no Type 3 font is left on the pages, the other fonts (TrueType subsets)
stay as they are.  usage: python outline_type3.py in.pdf out.pdf"""
import sys
import pikepdf
from pikepdf import Name, Operator, ContentStreamInstruction as CSI

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mul(a, b):
    """a x b for 2D affine matrices (a, b, c, d, e, f), row vectors: first a, then b"""
    return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])


class Outliner:
    def __init__(self, pdf):
        self.pdf = pdf
        self.forms = {}
        self.count = 0

    def code_names(self, font):
        """code -> glyph name from the /Differences of the encoding"""
        names, code = {}, 0
        for item in font.Encoding.Differences:
            if isinstance(item, pikepdf.Name):
                names[code] = str(item)
                code += 1
            else:
                code = int(item)
        return names

    def glyph_form(self, font, code, cache):
        key = (font.objgen, code)
        if key not in self.forms:
            name = cache['names'].get(code)
            proc = font.CharProcs.get(name) if name else None
            if proc is None:
                self.forms[key] = None
            else:
                ops = [x for x in pikepdf.parse_content_stream(proc) if str(x.operator) not in ('d0', 'd1')]
                bb = [float(v) for v in font.FontBBox]
                x0, x1, y0, y1 = min(bb[0], bb[2]) - 200, max(bb[0], bb[2]) + 200, min(bb[1], bb[3]) - 200, max(bb[1], bb[3]) + 200
                form = self.pdf.make_stream(pikepdf.unparse_content_stream(ops))
                form.Type, form.Subtype, form.BBox = Name.XObject, Name.Form, pikepdf.Array([x0, y0, x1, y1])
                self.forms[key] = form
        return self.forms[key]

    def process(self, obj, resources, depth=0):
        """rewrites the content stream of a page / form; returns True when it changed"""
        fonts = (resources.get('/Font') if resources is not None else None) or {}
        ops = list(pikepdf.parse_content_stream(obj))
        out, changed = [], False
        i = 0
        xobj_names = {}
        font, size, tm, tlm, caches = None, 0.0, IDENT, IDENT, {}
        in_text, type3 = False, False
        pending = []                                                       # the instructions of a BT..ET block that shows Type 3 text
        while i < len(ops):
            ins = ops[i]
            op = str(ins.operator)
            if op == 'BT':
                in_text, pending = True, [ins]
                tm = tlm = IDENT
            elif in_text:
                pending.append(ins)
                if op == 'Tf':
                    fn = str(ins.operands[0])
                    size = float(ins.operands[1])
                    font = fonts.get(fn)
                    type3 = font is not None and str(font.get('/Subtype')) == '/Type3'
                    if type3 and fn not in caches:
                        caches[fn] = {'names': self.code_names(font)}
                elif op == 'Tm':
                    tm = tlm = tuple(float(v) for v in ins.operands)
                elif op == 'Td':
                    tlm = mul((1, 0, 0, 1, float(ins.operands[0]), float(ins.operands[1])), tlm)
                    tm = tlm
                elif op in ('Tj', 'TJ', "'", '"', 'T*', 'TD', 'Tc', 'Tw', 'Tz', 'TL', 'Ts', 'Tr') and type3:
                    if op == 'Tj':
                        fm = tuple(float(v) for v in font.FontMatrix)
                        widths = [float(w) for w in font.Widths]
                        first = int(font.get('/FirstChar', 0))
                        fn = next(k for k, v in fonts.items() if v.objgen == font.objgen)
                        for code in bytes(ins.operands[0]):
                            form = self.glyph_form(font, code, caches[fn])
                            if form is not None:
                                m = mul(mul(fm, (size, 0, 0, size, 0, 0)), tm)
                                xn = f'/Gl{font.objgen[0]}_{code}'
                                xobj_names[xn] = form
                                out += [CSI([], Operator('q')), CSI([round(v, 6) for v in m], Operator('cm')), CSI([Name(xn)], Operator('Do')), CSI([], Operator('Q'))]
                            adv = widths[code - first] * fm[0] * size
                            tm = mul((1, 0, 0, 1, adv, 0), tm)
                    else:
                        raise ValueError(f'unsupported text operator {op} with a Type 3 font')
                elif op == 'ET':
                    in_text = False
                    if not type3:
                        out += pending                                       # text in another font: kept as it is
                    else:
                        changed = True
                    pending = []
            else:
                out.append(ins)
                if op == 'Tf':
                    fn = str(ins.operands[0])
                    size, font = float(ins.operands[1]), fonts.get(fn)
                    type3 = font is not None and str(font.get('/Subtype')) == '/Type3'
                    if type3 and fn not in caches:
                        caches[fn] = {'names': self.code_names(font)}
                if op == 'Do' and depth < 4:
                    x = (resources.get('/XObject') or {}).get(str(ins.operands[0]))
                    if x is not None and x.get('/Subtype') == '/Form' and x.objgen not in self.seen:
                        self.seen.add(x.objgen)
                        self.process(x, x.get('/Resources') if x.get('/Resources') is not None else resources, depth + 1)
            i += 1
        if changed:
            data = pikepdf.unparse_content_stream(out)
            if isinstance(obj, pikepdf.Stream):
                obj.write(data)
            else:
                obj.Contents = self.pdf.make_stream(data)
            if resources.get('/XObject') is None:
                resources.XObject = pikepdf.Dictionary()
            for n, f in xobj_names.items():
                resources.XObject[n] = f
        fonts = resources.get('/Font') if resources is not None else None
        if fonts is not None:                                               # no text uses the Type 3 fonts any more
            for k in [k for k, v in fonts.items() if str(v.get('/Subtype')) == '/Type3']:
                del fonts[k]
        return changed

    def run(self):
        self.seen = set()
        for page in self.pdf.pages:
            self.process(page, page.Resources)
        return self.count


def outline(src, dst):
    pdf = pikepdf.open(src)
    Outliner(pdf).run()
    pdf.save(dst)


if __name__ == '__main__':
    outline(sys.argv[1], sys.argv[2])
