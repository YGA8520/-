#!/usr/bin/env python3
"""Editable Word version of the booklet.

usage: make_docx.py book.doc.json book.layout.json out.docx

Real Word structure: one section per article title block, a 2-column continuous section for the text,
a 1-column section around every table, real footnotes (lettered, restarting per article, ornamented separator),
mirrored headers (even/odd), a TOC field and Hebrew page numbers.

Known limits of Word (vs. the PDF): footnotes sit inside the column instead of across both columns; the indented
second line and the centred last line of a paragraph cannot be expressed in Word paragraph formatting.
"""
import json, os, re, sys, zipfile, io
from xml.sax.saxutils import escape
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ORN = os.path.join(HERE, 'assets', 'ornaments')
MM_EMU = 36000
TW = 56.6929  # twips per mm

BODY_FONT, LEAD_FONT, DISPLAY_FONT = 'FrankRuehl', 'David', 'FrankRuehl'
BODY_PT, FOOT_PT, SMALL_PT = 12, 10, 10

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

PAGE_W, PAGE_H = round(176 * TW), round(250 * TW)
M_TOP, M_BOT, M_SIDE = round(32 * TW), round(18.5 * TW), round(19.4 * TW)
TEXT_W = PAGE_W - 2 * M_SIDE
COL_GAP = round(7.1 * TW)


def heb(n):
    L = [(400, 'ת'), (300, 'ש'), (200, 'ר'), (100, 'ק'), (90, 'צ'), (80, 'פ'), (70, 'ע'), (60, 'ס'), (50, 'נ'), (40, 'מ'), (30, 'ל'), (20, 'כ'), (10, 'י'), (9, 'ט'), (8, 'ח'), (7, 'ז'), (6, 'ו'), (5, 'ה'), (4, 'ד'), (3, 'ג'), (2, 'ב'), (1, 'א')]
    s = ''
    while n >= 100:
        v, c = next(x for x in L if x[0] <= n and x[0] >= 100)
        s += c; n -= v
    if n == 15: return s + 'טו'
    if n == 16: return s + 'טז'
    for v, c in L:
        if v >= 100: continue
        while n >= v:
            s += c; n -= v
    return s


# ---------------------------------------------------------------- xml helpers
def rpr(font=BODY_FONT, size=BODY_PT, bold=False, extra=''):
    f = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>'
    b = '<w:b/><w:bCs/>' if bold else ''
    return f'<w:rPr>{f}{b}{extra}<w:sz w:val="{round(size * 2)}"/><w:szCs w:val="{round(size * 2)}"/><w:rtl/></w:rPr>'


def run(text, style='n', size_body=BODY_PT):
    if not text:
        return ''
    t = escape(text)
    if style == 'b':
        pr = rpr(BODY_FONT, size_body, True)
    elif style == 'sm':
        pr = rpr(BODY_FONT, SMALL_PT, False)
    elif style == 'smb':
        pr = rpr(BODY_FONT, SMALL_PT, True)
    elif style == 'ld':
        pr = rpr(LEAD_FONT, size_body * 0.95, True)
    else:
        pr = rpr(BODY_FONT, size_body, False)
    return f'<w:r>{pr}<w:t xml:space="preserve">{t}</w:t></w:r>'


class Media:
    def __init__(self):
        self.files = {}      # name -> bytes
        self.rels = {}       # name -> (rid, size px)
        self.n = 0

    def add(self, name, data=None):
        if name not in self.files:
            if data is None:
                data = open(os.path.join(ORN, name), 'rb').read()
            self.files[name] = data
            w, h = Image.open(io.BytesIO(data)).size
            self.rels[name] = (f'rIdImg{len(self.rels) + 1}', (w, h))
        return self.rels[name]

    def flipped(self, name, flip='v'):
        fname = name.replace('.png', f'-flip{flip}.png')
        if fname not in self.files:
            im = Image.open(os.path.join(ORN, name))
            im = im.transpose(Image.FLIP_TOP_BOTTOM if flip == 'v' else Image.FLIP_LEFT_RIGHT)
            b = io.BytesIO(); im.save(b, 'PNG')
            self.add(fname, b.getvalue())
        return fname


MEDIA = Media()
_pic_id = [100]


def picture(name, width_mm, flip=None):
    if flip:
        name = MEDIA.flipped(name, flip)
    rid, (w, h) = MEDIA.add(name)
    cx = round(width_mm * MM_EMU); cy = round(cx * h / w)
    _pic_id[0] += 1
    i = _pic_id[0]
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{i}" name="Ornament {i}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{i}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def para(content, style=None, jc=None, keep=False, spacing=None, sect=''):
    """pPr children in schema order: pStyle, keepNext, bidi, spacing, jc, sectPr."""
    ppr = ''
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if keep:
        ppr += '<w:keepNext/>'
    ppr += '<w:bidi/>'
    if spacing:
        ppr += spacing
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    ppr += sect
    return f'<w:p><w:pPr>{ppr}</w:pPr>{content}</w:p>'


# ---------------------------------------------------------------- sections
def sectpr(kind='continuous', cols=1, header_ids=None, footnote_restart=False, start_page=None, last=False):
    h = ''
    if header_ids:
        h += f'<w:headerReference w:type="default" r:id="{header_ids[0]}"/><w:headerReference w:type="even" r:id="{header_ids[1]}"/>'
    fn = '<w:footnotePr><w:numFmt w:val="hebrew1"/>' + ('<w:numRestart w:val="eachSect"/>' if footnote_restart else '') + '</w:footnotePr>'
    pg = f'<w:pgNumType w:fmt="hebrew1"' + (f' w:start="{start_page}"' if start_page else '') + '/>'
    c = (f'<w:cols w:num="2" w:space="{COL_GAP}" w:equalWidth="1"/>' if cols == 2 else '<w:cols w:space="708"/>')
    return (f'<w:sectPr>{h}{fn}<w:type w:val="{kind}"/><w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
            f'<w:pgMar w:top="{M_TOP}" w:right="{M_SIDE}" w:bottom="{M_BOT}" w:left="{M_SIDE}" w:header="{round(17 * TW)}" w:footer="{round(8 * TW)}" w:gutter="0"/>'
            f'{pg}{c}<w:bidi/></w:sectPr>')


def header_xml(book, chap, even):
    num = ('<w:r>' + rpr(LEAD_FONT, 13, True) + '<w:fldChar w:fldCharType="begin"/></w:r><w:r>' + rpr(LEAD_FONT, 13, True) +
           '<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r>' + rpr(LEAD_FONT, 13, True) + '<w:fldChar w:fldCharType="separate"/></w:r>'
           '<w:r>' + rpr(LEAD_FONT, 13, True) + '<w:t>1</w:t></w:r><w:r>' + rpr(LEAD_FONT, 13, True) + '<w:fldChar w:fldCharType="end"/></w:r>')
    b = f'<w:r>{rpr(DISPLAY_FONT, 15, True)}<w:t xml:space="preserve">{escape(book)}</w:t></w:r>'
    dot = f'<w:r>{rpr(BODY_FONT, 6, False)}<w:t xml:space="preserve">  ●  </w:t></w:r>'
    c = f'<w:r>{rpr(BODY_FONT, 10, False)}<w:t xml:space="preserve">{escape(chap)}</w:t></w:r>'
    narrow = round(TEXT_W * 0.12)
    w1, w2 = (narrow, TEXT_W - narrow) if even else (TEXT_W - narrow, narrow)   # first cell = right-hand cell
    bot = '<w:tcBorders><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders>'
    # bidiVisual table: first cell is the right-hand one
    if even:   # right-hand page: number at the outer (right) edge, book name at the inner (left) edge
        c1, j1 = num, 'left'       # in a bidi paragraph "left" = start = right edge
        c2, j2 = c + dot + b, 'right'
    else:      # left-hand page: book name at the inner (right) edge, number at the outer (left) edge
        c1, j1 = b + dot + c, 'left'
        c2, j2 = num, 'right'
    def cell(content, jc, w):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{bot}<w:vAlign w:val="bottom"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi/><w:jc w:val="{jc}"/></w:pPr>{content}</w:p></w:tc>')
    tbl = (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid><w:gridCol w:w="{w1}"/><w:gridCol w:w="{w2}"/></w:tblGrid>'
           f'<w:tr>{cell(c1, j1, w1)}{cell(c2, j2, w2)}</w:tr></w:tbl>')
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {NS}>{tbl}<w:p><w:pPr><w:pStyle w:val="Header"/><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p></w:hdr>'


def empty_header():
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {NS}><w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi/></w:pPr></w:p></w:hdr>'


# ---------------------------------------------------------------- content -> runs
ENUM = re.compile(r"^(?:\(?[א-ת]{1,3}[׳'.):]+|\d{1,3}[.)])$")


def split_lead(runs):
    """flatten runs and mark the lead-in (first word, or enumerator + word, or existing short bold start)."""
    segs = []
    for r in runs:
        if 'fn' in r:
            segs.append(('fn', r['fn'], None))
        else:
            st = 'smb' if (r.get('sm') and r.get('b')) else 'sm' if r.get('sm') else 'b' if r.get('b') else 'n'
            segs.append(('t', r['t'], st))
    text = ''.join(s[1] for s in segs if s[0] == 't')
    m = re.match(r'\s*(\S+)(\s+)(\S+)?', text)
    if not m:
        return [(a, b, c, False) for a, b, c in segs]
    first = m.group(1)
    lead_end = m.end(1)
    if ENUM.match(first) and m.group(3):
        lead_end = m.end(3)
    # existing bold start (up to 3 words)
    bold_len = 0
    for a, b, c in segs:
        if a == 't' and c in ('b', 'smb'):
            bold_len += len(b)
        elif a == 't':
            break
    if bold_len and len(text[:bold_len].split()) <= 3:
        lead_end = max(lead_end, len(text[:bold_len].rstrip()))
    out, pos = [], 0
    for a, b, c in segs:
        if a == 'fn':
            out.append((a, b, c, pos <= lead_end))
            continue
        e = pos + len(b)
        if e <= lead_end:
            out.append(('t', b, c, True))
        elif pos >= lead_end:
            out.append(('t', b, c, False))
        else:
            k = lead_end - pos
            out.append(('t', b[:k], c, True)); out.append(('t', b[k:], c, False))
        pos = e
    return out


class Doc:
    def __init__(self):
        self.footnotes = []     # xml strings
        self.fn_n = 0
        self.body = []

    def footnote_ref(self, runs):
        self.fn_n += 1
        n = self.fn_n
        paras = ''.join(run(r['t'], 'sm' if r.get('sm') else 'n', FOOT_PT) for r in runs if 'fn' not in r)
        # footnote text is a little smaller than body text
        paras = paras.replace(f'w:val="{BODY_PT * 2}"', f'w:val="{FOOT_PT * 2}"')
        self.footnotes.append(
            f'<w:footnote w:id="{n}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/><w:bidi/><w:jc w:val="both"/></w:pPr>'
            f'<w:r><w:rPr><w:rStyle w:val="FootnoteNum"/></w:rPr><w:footnoteRef/></w:r><w:r>{rpr(BODY_FONT, FOOT_PT)}<w:t xml:space="preserve">. </w:t></w:r>{paras}</w:p></w:footnote>')
        return f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="{n}"/></w:r>'


def runs_xml(doc, art, runs, lead=True, base_style=None):
    out = ''
    if lead:
        parts = split_lead(runs)
    else:
        parts = [(('fn', r['fn'], None, False) if 'fn' in r else ('t', r['t'], ('smb' if (r.get('sm') and r.get('b')) else 'sm' if r.get('sm') else 'b' if r.get('b') else 'n'), False)) for r in runs]
    for kind, val, st, is_lead in parts:
        if kind == 'fn':
            src = art['footnotes'].get(val)
            if src:
                out += doc.footnote_ref(src)
        else:
            out += run(val, 'ld' if (is_lead and st in ('n', 'b')) else st)
    return out


def table_xml(art, b):
    ncol = max(len(r) for r in b['rows'])
    total = round(TEXT_W * 0.94)
    grid = ''.join(f'<w:gridCol w:w="{total // ncol}"/>' for _ in range(ncol))
    bd = ''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="000000"/>' for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    rows = ''
    for ri, row in enumerate(b['rows']):
        cells = ''
        for cell in row:
            txt = ''.join(run(r['t'], 'b' if (ri == 0 or r.get('b')) else 'n', FOOT_PT).replace(f'w:val="{BODY_PT * 2}"', f'w:val="{FOOT_PT * 2}"') for r in cell if 'fn' not in r)
            cells += f'<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="TableText"/><w:bidi/><w:jc w:val="center"/></w:pPr>{txt}</w:p></w:tc>'
        rows += f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cells}</w:tr>'
    return (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{bd}</w:tblBorders>'
            f'<w:tblCellMar><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{rows}</w:tbl>')


# ---------------------------------------------------------------- styles / settings / parts
def styles_xml():
    def pst(sid, name, ppr='', rpr_='', based='Normal', nxt=None, q=True):
        return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/>' + (f'<w:basedOn w:val="{based}"/>' if based else '') +
                (f'<w:next w:val="{nxt}"/>' if nxt else '') + ('<w:qFormat/>' if q else '') + f'<w:pPr>{ppr}</w:pPr><w:rPr>{rpr_}</w:rPr></w:style>')
    def fonts(f): return f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}" w:eastAsia="{f}"/>'
    s = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}>'
    s += (f'<w:docDefaults><w:rPrDefault><w:rPr>{fonts(BODY_FONT)}<w:sz w:val="{BODY_PT * 2}"/><w:szCs w:val="{BODY_PT * 2}"/>'
          f'<w:lang w:val="he-IL" w:eastAsia="he-IL" w:bidi="he-IL"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:bidi/><w:spacing w:after="0" w:line="340" w:lineRule="exact"/></w:pPr></w:pPrDefault></w:docDefaults>')
    s += '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    s += pst('Body', 'Body Text Sefer', '<w:widowControl/><w:bidi/><w:spacing w:after="340" w:line="340" w:lineRule="exact"/><w:jc w:val="both"/>')
    s += pst('Heading1', 'heading 1', '<w:keepNext/><w:bidi/><w:spacing w:before="120" w:after="120" w:line="400" w:lineRule="exact"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>',
             fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/><w:sz w:val="{17 * 2}"/><w:szCs w:val="{17 * 2}"/>', nxt='Body')
    s += pst('Heading2', 'heading 2', '<w:keepNext/><w:bidi/><w:spacing w:before="340" w:after="0" w:line="340" w:lineRule="exact"/><w:jc w:val="center"/><w:outlineLvl w:val="1"/>',
             fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/><w:sz w:val="{29}"/><w:szCs w:val="{29}"/>', nxt='Body')
    s += pst('Heading3', 'heading 3', '<w:keepNext/><w:bidi/><w:spacing w:before="340" w:after="0" w:line="340" w:lineRule="exact"/><w:jc w:val="center"/>',
             fonts(LEAD_FONT) + f'<w:b/><w:bCs/><w:sz w:val="{23}"/><w:szCs w:val="{23}"/>', nxt='Body')
    s += pst('ArtLabel', 'Article Label', '<w:bidi/><w:spacing w:before="0" w:after="80" w:line="260" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(DISPLAY_FONT) + '<w:b/><w:bCs/><w:sz w:val="22"/><w:szCs w:val="22"/>')
    s += pst('ArtAuthor', 'Article Author', '<w:bidi/><w:spacing w:before="80" w:after="280" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + '<w:b/><w:bCs/><w:sz w:val="23"/><w:szCs w:val="23"/>')
    s += pst('ArtSub', 'Article Subtitle', '<w:bidi/><w:spacing w:before="0" w:after="40" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + '<w:sz w:val="22"/><w:szCs w:val="22"/>')
    s += pst('FootnoteText', 'footnote text', f'<w:bidi/><w:spacing w:after="30" w:line="292" w:lineRule="exact"/><w:jc w:val="both"/>', fonts(BODY_FONT) + f'<w:sz w:val="{FOOT_PT * 2}"/><w:szCs w:val="{FOOT_PT * 2}"/>')
    s += pst('TableText', 'Table Text', '<w:bidi/><w:spacing w:after="0" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', f'<w:sz w:val="{FOOT_PT * 2}"/><w:szCs w:val="{FOOT_PT * 2}"/>')
    s += pst('Header', 'header', '<w:bidi/><w:spacing w:after="0" w:line="300" w:lineRule="exact"/>')
    s += pst('TOC1', 'toc 1', f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs><w:bidi/><w:spacing w:after="60" w:line="300" w:lineRule="exact"/>', f'<w:sz w:val="23"/><w:szCs w:val="23"/>')
    s += pst('TOCTitle', 'TOC Title', '<w:bidi/><w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/>', fonts(DISPLAY_FONT) + '<w:b/><w:bCs/><w:sz w:val="42"/><w:szCs w:val="42"/>')
    s += pst('CoverTitle', 'Cover Title', '<w:bidi/><w:spacing w:before="0" w:after="200" w:line="900" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(DISPLAY_FONT) + '<w:b/><w:bCs/><w:sz w:val="80"/><w:szCs w:val="80"/>')
    s += pst('CoverSub', 'Cover Subtitle', '<w:bidi/><w:spacing w:before="0" w:after="200" w:line="480" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + '<w:sz w:val="32"/><w:szCs w:val="32"/>')
    s += ('<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:b/><w:bCs/><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
          '<w:style w:type="character" w:styleId="FootnoteNum"><w:name w:val="footnote number"/><w:rPr><w:b/><w:bCs/></w:rPr></w:style>')
    return s + '</w:styles>'


def settings_xml():
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {NS}><w:evenAndOddHeaders/><w:updateFields w:val="true"/>'
            '<w:defaultTabStop w:val="720"/><w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
            '<w:themeFontLang w:val="he-IL" w:bidi="he-IL"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')


def footnotes_xml(doc, sep_title='הערות וציונים'):
    sep = (f'<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:bidi/><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
           f'{picture("line-scroll.png", 48, "h")}<w:r>{rpr(LEAD_FONT, 9.5, True)}<w:t xml:space="preserve">  {escape(sep_title)}  </w:t></w:r>{picture("line-scroll.png", 48)}</w:p></w:footnote>')
    cont = '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {NS}>{sep}{cont}{"".join(doc.footnotes)}</w:footnotes>'


# ---------------------------------------------------------------- build
def build(doc_json, layout_json, out):
    data = json.load(open(doc_json))
    lay = json.load(open(layout_json)) if layout_json and os.path.exists(layout_json) else None
    book = data['book']
    D = Doc()
    headers = []        # (name, xml)
    parts = []          # body xml
    def add_header(book_name, chap, tag):
        i = len(headers) // 2 + 1
        dn, en = f'header{tag}d.xml', f'header{tag}e.xml'
        headers.append((dn, header_xml(book_name, chap, False)))   # default = odd page (left-hand)
        headers.append((en, header_xml(book_name, chap, True)))    # even page (right-hand)
        return (f'rIdH{tag}d', f'rIdH{tag}e')
    empty_ids = ('rIdHEd', 'rIdHEe')
    headers.append(('headerEd.xml', empty_header())); headers.append(('headerEe.xml', empty_header()))

    # cover
    cover = (para('', spacing='<w:spacing w:before="2600" w:after="0" w:line="240" w:lineRule="auto"/>') +
             para(picture('flourish-wide-1.png', 70), jc='center') +
             para(run(book['name'], 'b', 40), 'CoverTitle', 'center') +
             (para(run(book.get('subtitle', ''), 'n', 16), 'CoverSub', 'center') if book.get('subtitle') else '') +
             para(picture('flourish-wide-1.png', 70, 'v'), jc='center', sect=sectpr('continuous', 1, empty_ids)))
    parts.append(cover)

    # table of contents (field with cached entries)
    toc_title = para(run('תוכן עניינים', 'b', 21), 'TOCTitle', 'center')
    entries = []
    n_toc = lay['tocPages'] if lay else 3
    pages = {t['title']: t['page'] for t in lay['toc']} if lay else {}
    for k, a in enumerate(data['articles']):
        pg = lay['toc'][k]['page'] if lay else k + 1
        entries.append((a['title'], pg))
    toc_paras = []
    for k, (title, pg) in enumerate(entries):
        pre = ''
        if k == 0:
            pre = (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-1" \\u </w:instrText></w:r>'
                   '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
        post = '<w:r><w:fldChar w:fldCharType="end"/></w:r>' if k == len(entries) - 1 else ''
        sect = sectpr('nextPage', 1, empty_ids) if k == len(entries) - 1 else ''
        body = f'{pre}<w:r><w:t xml:space="preserve">{escape(title)}</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>{heb(pg)}</w:t></w:r>{post}'
        toc_paras.append(para(body, 'TOC1', sect=sect))
    parts.append(toc_title + ''.join(toc_paras))

    first_art_section = True
    for ai, art in enumerate(data['articles']):
        hid = add_header(book['name'], art.get('shortTitle') or art['title'], f'A{ai}')
        # title block (single column, starts a new page)
        tb = ''
        if art.get('label'):
            tb += para(run(art['label'], 'b', 11), 'ArtLabel')
        tb += para(picture('flourish-wide-2.png', 32), jc='center', keep=True, spacing='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>')
        tb += para(run(art['title'], 'b', 17).replace(f'w:val="{BODY_PT * 2}"', 'w:val="34"'), 'Heading1')
        tb += para(picture('flourish-wide-2.png', 32, 'v'), jc='center', keep=True, spacing='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>')
        if art.get('subtitle'):
            tb += para(run(art['subtitle'], 'n', 11), 'ArtSub')
        sp = (len(data['articles']) and (lay['tocPages'] + 1 if (lay and first_art_section) else None))
        last_tb = para(run(art['author'], 'b', 11.5) if art.get('author') else '', 'ArtAuthor', sect=sectpr('nextPage', 1, hid, start_page=sp))
        first_art_section = False
        parts.append(tb + last_tb)
        # body: chunks of paragraphs, tables get their own single-column section
        chunk = []
        restart = True
        def flush(end=False):
            nonlocal chunk, restart
            if not chunk:
                return
            sect = sectpr('continuous', 2, None, footnote_restart=restart)
            restart = False
            # attach the section break to the last paragraph of the chunk
            last = chunk[-1]
            last = last.replace('</w:pPr>', sect + '</w:pPr>', 1)
            chunk[-1] = last
            parts.append(''.join(chunk))
            chunk = []
        for b in art['blocks']:
            if b['t'] == 'p':
                chunk.append(para(runs_xml(D, art, b['runs']), 'Body'))
            elif b['t'] == 'h2':
                chunk.append(para(run(b['runs'][0]['t'], 'b', 14.5).replace(f'w:val="{BODY_PT * 2}"', 'w:val="29"'), 'Heading2'))
            elif b['t'] == 'h3':
                chunk.append(para(runs_xml(D, art, b['runs'], lead=False).replace(f'w:val="{BODY_PT * 2}"', 'w:val="23"'), 'Heading3'))
            elif b['t'] == 'tbl':
                flush()
                parts.append(table_xml(art, b) + para('', spacing='<w:spacing w:before="0" w:after="0" w:line="40" w:lineRule="exact"/>', sect=sectpr('continuous', 1, None)))
        flush()
    # the final section properties live in the last paragraph's sectPr; Word also needs a body-level sectPr
    body_sect = sectpr('continuous', 2, None)
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{"".join(parts)}{body_sect}</w:body></w:document>'

    # relationships
    rels = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
            '<Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>']
    for name, rel in MEDIA.rels.items():
        rels.append(f'<Relationship Id="{rel[0]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>')
    for name, _ in headers:
        rid = 'rId' + name.replace('header', 'H').replace('.xml', '')
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="{name}"/>')
    doc_rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>'
    fn_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
               ''.join(f'<Relationship Id="{rel[0]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>' for name, rel in MEDIA.rels.items()) + '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>' +
          ''.join(f'<Override PartName="/word/{n}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>' for n, _ in headers) + '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    footnotes = footnotes_xml(D)
    # media referenced by footnotes were added while building the footnotes part -> rebuild rel lists
    fn_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
               ''.join(f'<Relationship Id="{rel[0]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>' for name, rel in MEDIA.rels.items()) + '</Relationships>')
    # (re-generate document rels including late-added media)
    rels = rels[:3]
    for name, rel in MEDIA.rels.items():
        rels.append(f'<Relationship Id="{rel[0]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>')
    for name, _ in headers:
        rid = 'rId' + name.replace('header', 'H').replace('.xml', '')
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="{name}"/>')
    doc_rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>'

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', root_rels)
        z.writestr('word/document.xml', document)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/_rels/footnotes.xml.rels', fn_rels)
        z.writestr('word/styles.xml', styles_xml())
        z.writestr('word/settings.xml', settings_xml())
        z.writestr('word/footnotes.xml', footnotes)
        for n, x in headers:
            z.writestr('word/' + n, x)
        for n, b in MEDIA.files.items():
            z.writestr('word/media/' + n, b)
    print('docx written', out, 'footnotes', D.fn_n, 'articles', len(data['articles']))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else 'out/book.docx')
