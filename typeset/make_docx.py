#!/usr/bin/env python3
"""Editable Word version of the booklet.

usage: make_docx.py book.doc.json book.layout.json out.docx

Structure
  * one single-column section for every article title block (starts a new page), a 2-column continuous section for the
    text, a 1-column section around every table
  * every look is a named style (Hebrew names): paragraph styles for body / titles / headings, character styles for the
    bold first word ("מילה פותחת"), small citations, bold emphasis
  * real footnotes (lettered, restarting per article) with an ornamented separator, mirrored headers with the ornament
    rule, a TOC field, Hebrew page numbers
  * the framed "סימן" title is a picture anchored *behind the text*

Known limits of Word (vs. the PDF): footnotes sit inside the column instead of across both columns; the indented second
line and the centred last line of a paragraph cannot be expressed in Word paragraph formatting.
"""
import io, json, os, re, sys, zipfile
from xml.sax.saxutils import escape
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ORN = os.path.join(HERE, 'assets', 'ornaments')
MM_EMU = 36000
TW = 56.6929  # twips per mm

BODY_FONT, LEAD_FONT, DISPLAY_FONT = 'FrankRuehl', 'David', 'FrankRuehl'
BODY_PT, FOOT_PT, SMALL_PT, FOOT_SMALL_PT, LEAD_PT = 12, 10, 10, 8.5, 11.4

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

PAGE_W, PAGE_H = round(176 * TW), round(250 * TW)
M_TOP, M_BOT, M_SIDE = round(32 * TW), round(18.5 * TW), round(19.4 * TW)
TEXT_W = PAGE_W - 2 * M_SIDE
TEXT_W_MM = TEXT_W / TW
COL_GAP = round(7.1 * TW)

# ---- style ids (the visible names are Hebrew) ----
ST = dict(
    body='Body', title='ArticleTitle', part='ArticlePart', sub='SubHeading', siman='SimanTitle', author='ArticleAuthor',
    subtitle='ArticleSubtitle', table='TableText', tocTitle='TocTitle', coverTitle='CoverTitle', coverSub='CoverSubtitle',
    lead='LeadWord', small='SmallSource', bold='BodyBold', footSmall='FootSmall', footNum='FootNum',
)
NAME = {  # style id -> Hebrew display name
    'Body': 'גוף הטקסט', 'ArticleTitle': 'כותרת מאמר', 'ArticlePart': 'כותרת חלק', 'SubHeading': 'כותרת משנה',
    'SimanTitle': 'כותרת סימן', 'ArticleAuthor': 'שם המחבר', 'ArticleSubtitle': 'תת כותרת מאמר', 'TableText': 'טקסט טבלה',
    'TocTitle': 'כותרת תוכן עניינים', 'CoverTitle': 'כותרת שער', 'CoverSubtitle': 'תת כותרת שער',
    'LeadWord': 'מילה פותחת', 'SmallSource': 'מקור קטן', 'BodyBold': 'הדגשה בגוף', 'FootSmall': 'מקור קטן בהערה',
    'FootNum': 'מספר הערה בתחתית הערה',
}


def heb(n):
    L = [(400, 'ת'), (300, 'ש'), (200, 'ר'), (100, 'ק'), (90, 'צ'), (80, 'פ'), (70, 'ע'), (60, 'ס'), (50, 'נ'), (40, 'מ'), (30, 'ל'), (20, 'כ'), (10, 'י'), (9, 'ט'), (8, 'ח'), (7, 'ז'), (6, 'ו'), (5, 'ה'), (4, 'ד'), (3, 'ג'), (2, 'ב'), (1, 'א')]
    s = ''
    while n >= 100:
        v, c = next(x for x in L if 100 <= x[0] <= n)
        s += c; n -= v
    if n == 15: return s + 'טו'
    if n == 16: return s + 'טז'
    for v, c in L:
        if v >= 100: continue
        while n >= v:
            s += c; n -= v
    return s


# ---------------------------------------------------------------- runs
def fonts(f):
    return f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}" w:eastAsia="{f}"/>'


def sz(pt):
    v = round(pt * 2)
    return f'<w:sz w:val="{v}"/><w:szCs w:val="{v}"/>'


def run(text, rstyle=None, bold=False, direct=''):
    """a run that takes its look from a named character style (no direct formatting unless asked)."""
    if not text:
        return ''
    pr = ''
    if rstyle:
        pr += f'<w:rStyle w:val="{rstyle}"/>'
    if bold:
        pr += '<w:b/><w:bCs/>'
    pr += direct
    pr = f'<w:rPr>{pr}</w:rPr>' if pr else ''
    return f'<w:r>{pr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def styled_run(text, st):
    """st: n | b | sm | smb | ld (as in the content model)"""
    if st == 'ld': return run(text, ST['lead'])
    if st == 'b': return run(text, ST['bold'])
    if st == 'sm': return run(text, ST['small'])
    if st == 'smb': return run(text, ST['small'], bold=True)
    return run(text)


# ---------------------------------------------------------------- media
class Media:
    def __init__(self):
        self.files, self.rels = {}, {}

    def add(self, name, data=None):
        if name not in self.files:
            if data is None:
                p = os.path.join(ORN, name)
                data = open(p, 'rb').read()
            self.files[name] = data
            w, h = Image.open(io.BytesIO(data)).size
            self.rels[name] = (f'rIdImg{len(self.rels) + 1}', (w, h))
        return self.rels[name]

    def flipped(self, name, flip):
        fname = name.replace('/', '_').replace('.png', f'-flip{flip}.png')
        if fname not in self.files:
            im = Image.open(os.path.join(ORN, name))
            im = im.transpose(Image.FLIP_TOP_BOTTOM if flip == 'v' else Image.FLIP_LEFT_RIGHT)
            b = io.BytesIO(); im.save(b, 'PNG')
            self.add(fname, b.getvalue())
        return fname


MEDIA = Media()
_ids = [100]


def _graphic(name, rid, cx, cy, i):
    return (f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{i}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic>')


def picture(name, width_mm, flip=None, raise_pt=None):
    """inline picture"""
    if flip:
        name = MEDIA.flipped(name, flip)
    rid, (w, h) = MEDIA.add(name)
    cx = round(width_mm * MM_EMU); cy = round(cx * h / w)
    _ids[0] += 1; i = _ids[0]
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{i}" name="Ornament {i}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'{_graphic(os.path.basename(name), rid, cx, cy, i)}</wp:inline></w:drawing></w:r>')


def picture_behind(name, width_mm):
    """picture anchored to the paragraph, centred on the text column, position = behind the text (wrapNone, behindDoc)"""
    rid, (w, h) = MEDIA.add(name)
    cx = round(width_mm * MM_EMU); cy = round(cx * h / w)
    _ids[0] += 1; i = _ids[0]
    return (f'<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="{251650000 + i}" '
            f'behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
            f'<wp:positionH relativeFrom="margin"><wp:align>center</wp:align></wp:positionH>'
            f'<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{i}" name="מסגרת סימן {i}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'{_graphic(os.path.basename(name), rid, cx, cy, i)}</wp:anchor></w:drawing></w:r>')


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


# ---------------------------------------------------------------- sections / headers
def sectpr(kind='continuous', cols=1, header_ids=None, footnote_restart=False, start_page=None):
    h = ''
    if header_ids:
        h += f'<w:headerReference w:type="default" r:id="{header_ids[0]}"/><w:headerReference w:type="even" r:id="{header_ids[1]}"/>'
    fn = '<w:footnotePr><w:numFmt w:val="hebrew1"/>' + ('<w:numRestart w:val="eachSect"/>' if footnote_restart else '') + '</w:footnotePr>'
    pg = '<w:pgNumType w:fmt="hebrew1"' + (f' w:start="{start_page}"' if start_page else '') + '/>'
    c = (f'<w:cols w:num="2" w:space="{COL_GAP}" w:equalWidth="1"/>' if cols == 2 else '<w:cols w:space="708"/>')
    return (f'<w:sectPr>{h}{fn}<w:type w:val="{kind}"/><w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
            f'<w:pgMar w:top="{M_TOP}" w:right="{M_SIDE}" w:bottom="{M_BOT}" w:left="{M_SIDE}" w:header="{round(17 * TW)}" w:footer="{round(8 * TW)}" w:gutter="0"/>'
            f'{pg}{c}<w:bidi/></w:sectPr>')


def header_xml(book, chap, even):
    fld = lambda t: f'<w:r><w:rPr><w:rStyle w:val="{ST["lead"]}"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>{t}</w:r>'
    num = (fld('<w:fldChar w:fldCharType="begin"/>') + fld('<w:instrText xml:space="preserve"> PAGE </w:instrText>') +
           fld('<w:fldChar w:fldCharType="separate"/>') + fld('<w:t>1</w:t>') + fld('<w:fldChar w:fldCharType="end"/>'))
    b = f'<w:r><w:rPr>{fonts(DISPLAY_FONT)}<w:b/><w:bCs/>{sz(15)}</w:rPr><w:t xml:space="preserve">{escape(book)}</w:t></w:r>'
    dot = f'<w:r><w:rPr>{sz(6)}</w:rPr><w:t xml:space="preserve">  ●  </w:t></w:r>'
    c = f'<w:r><w:rPr>{sz(10)}</w:rPr><w:t xml:space="preserve">{escape(chap)}</w:t></w:r>'
    narrow = round(TEXT_W * 0.12)
    w1, w2 = (narrow, TEXT_W - narrow) if even else (TEXT_W - narrow, narrow)   # first cell = right-hand cell
    if even:   # right-hand page: number at the outer (right) edge, book name at the inner (left) edge
        c1, j1, c2, j2 = num, 'left', c + dot + b, 'right'      # in a bidi paragraph "left" = start = right edge
    else:      # left-hand page: book name at the inner (right) edge, number at the outer (left) edge
        c1, j1, c2, j2 = b + dot + c, 'left', num, 'right'
    def cell(content, jc, w):
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="bottom"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi/><w:jc w:val="{jc}"/></w:pPr>{content}</w:p></w:tc>')
    tbl = (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid><w:gridCol w:w="{w1}"/><w:gridCol w:w="{w2}"/></w:tblGrid>'
           f'<w:tr>{cell(c1, j1, w1)}{cell(c2, j2, w2)}</w:tr></w:tbl>')
    # the rule under the header is the ornament (composed to the text width), not a plain line
    rule = para(picture('composed/header-rule.png', TEXT_W_MM), 'Header', 'center', spacing='<w:spacing w:before="40" w:after="0" w:line="240" w:lineRule="auto"/>')
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {NS}>{tbl}{rule}</w:hdr>'


def empty_header():
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {NS}><w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi/></w:pPr></w:p></w:hdr>'


# ---------------------------------------------------------------- content -> runs
ENUM = re.compile(r"^(?:\(?[א-ת]{1,3}[׳'.):]+|\d{1,3}[.)])$")


def split_lead(runs):
    """flatten runs and mark the lead-in (first word, or enumerator + word, or an existing short bold start)."""
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
    lead_end = m.end(1)
    if ENUM.match(m.group(1)) and m.group(3):
        lead_end = m.end(3)
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
            out.append((a, b, c, pos <= lead_end)); continue
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
        self.footnotes, self.fn_n = [], 0

    def footnote_ref(self, runs):
        self.fn_n += 1
        n = self.fn_n
        body = ''.join(run(r['t'], ST['footSmall'] if r.get('sm') else None) for r in runs if 'fn' not in r)
        self.footnotes.append(
            f'<w:footnote w:id="{n}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/><w:bidi/><w:jc w:val="both"/></w:pPr>'
            f'<w:r><w:rPr><w:rStyle w:val="{ST["footNum"]}"/></w:rPr><w:footnoteRef/></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r>{body}</w:p></w:footnote>')
        return f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="{n}"/></w:r>'


def runs_xml(doc, art, runs, lead=True):
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
            out += styled_run(val, 'ld' if (is_lead and st in ('n', 'b')) else st)
    return out


def heading_runs(doc, art, runs):
    """heading text: the paragraph style carries the look, runs stay plain (footnote refs kept)"""
    out = ''
    for r in runs:
        if 'fn' in r:
            src = art['footnotes'].get(r['fn'])
            if src:
                out += doc.footnote_ref(src)
        else:
            out += run(r['t'])
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
            txt = ''.join(run(r['t'], bold=(ri == 0 or bool(r.get('b')))) for r in cell if 'fn' not in r)
            cells += f'<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="{ST["table"]}"/><w:bidi/><w:jc w:val="center"/></w:pPr>{txt}</w:p></w:tc>'
        rows += f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cells}</w:tr>'
    return (f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{bd}</w:tblBorders>'
            f'<w:tblCellMar><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{rows}</w:tbl>')


# ---------------------------------------------------------------- styles / settings / parts
def styles_xml():
    def pst(sid, ppr='', rpr_='', based='Normal', nxt=None, name=None, builtin=False):
        nm = name or NAME[sid]
        return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{nm}"/>' + (f'<w:basedOn w:val="{based}"/>' if based else '') +
                (f'<w:next w:val="{nxt}"/>' if nxt else '') + '<w:qFormat/>' + f'<w:pPr>{ppr}</w:pPr><w:rPr>{rpr_}</w:rPr></w:style>')
    def cst(sid, rpr_, name=None):
        return f'<w:style w:type="character" w:styleId="{sid}"><w:name w:val="{name or NAME[sid]}"/><w:basedOn w:val="DefaultParagraphFont"/><w:qFormat/><w:rPr>{rpr_}</w:rPr></w:style>'
    s = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}>'
    s += (f'<w:docDefaults><w:rPrDefault><w:rPr>{fonts(BODY_FONT)}{sz(BODY_PT)}<w:lang w:val="he-IL" w:eastAsia="he-IL" w:bidi="he-IL"/></w:rPr></w:rPrDefault>'
          f'<w:pPrDefault><w:pPr><w:bidi/><w:spacing w:after="0" w:line="340" w:lineRule="exact"/></w:pPr></w:pPrDefault></w:docDefaults>')
    s += '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    s += '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>'
    # paragraph styles
    s += pst('Body', '<w:widowControl/><w:bidi/><w:spacing w:after="340" w:line="340" w:lineRule="exact"/><w:jc w:val="both"/>', '')
    s += pst('ArticleTitle', '<w:keepNext/><w:bidi/><w:spacing w:before="120" w:after="120" w:line="400" w:lineRule="exact"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>',
             fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/>{sz(17)}', nxt='Body')
    s += pst('ArticlePart', '<w:keepNext/><w:bidi/><w:spacing w:before="340" w:after="0" w:line="340" w:lineRule="exact"/><w:jc w:val="center"/><w:outlineLvl w:val="1"/>',
             fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/>{sz(14.5)}', nxt='Body')
    s += pst('SubHeading', '<w:keepNext/><w:bidi/><w:spacing w:before="340" w:after="0" w:line="340" w:lineRule="exact"/><w:jc w:val="center"/>',
             fonts(LEAD_FONT) + f'<w:b/><w:bCs/>{sz(11.5)}', nxt='Body')
    s += pst('SimanTitle', '<w:keepNext/><w:bidi/><w:spacing w:before="0" w:after="0" w:line="300" w:lineRule="exact"/><w:jc w:val="center"/>',
             fonts(LEAD_FONT) + f'<w:b/><w:bCs/>{sz(13)}')
    s += pst('ArticleAuthor', '<w:bidi/><w:spacing w:before="80" w:after="280" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + f'<w:b/><w:bCs/>{sz(11.5)}')
    s += pst('ArticleSubtitle', '<w:bidi/><w:spacing w:before="0" w:after="40" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + sz(11))
    s += pst('TableText', '<w:bidi/><w:spacing w:after="0" w:line="280" w:lineRule="exact"/><w:jc w:val="center"/>', sz(FOOT_PT))
    s += pst('TocTitle', '<w:bidi/><w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/>', fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/>{sz(21)}')
    s += pst('CoverTitle', '<w:bidi/><w:spacing w:before="0" w:after="200" w:line="900" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(DISPLAY_FONT) + f'<w:b/><w:bCs/>{sz(40)}')
    s += pst('CoverSubtitle', '<w:bidi/><w:spacing w:before="0" w:after="200" w:line="480" w:lineRule="exact"/><w:jc w:val="center"/>', fonts(LEAD_FONT) + sz(16))
    # built-in styles keep their English ids/names (Hebrew Word shows them in Hebrew by itself)
    s += pst('FootnoteText', '<w:bidi/><w:spacing w:after="30" w:line="292" w:lineRule="exact"/><w:jc w:val="both"/>', sz(FOOT_PT), name='footnote text')
    s += pst('Header', '<w:bidi/><w:spacing w:after="0" w:line="300" w:lineRule="exact"/>', '', name='header')
    s += pst('TOC1', f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs><w:bidi/><w:spacing w:after="60" w:line="300" w:lineRule="exact"/>', sz(11.5), name='toc 1')
    # character styles
    s += cst('LeadWord', fonts(LEAD_FONT) + f'<w:b/><w:bCs/>{sz(LEAD_PT)}')
    s += cst('SmallSource', sz(SMALL_PT))
    s += cst('BodyBold', '<w:b/><w:bCs/>')
    s += cst('FootSmall', sz(FOOT_SMALL_PT))
    s += cst('FootNum', '<w:b/><w:bCs/>')
    s += '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:basedOn w:val="DefaultParagraphFont"/><w:rPr><w:b/><w:bCs/><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
    return s + '</w:styles>'


def settings_xml():
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {NS}><w:evenAndOddHeaders/><w:updateFields w:val="true"/>'
            '<w:defaultTabStop w:val="720"/><w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
            '<w:themeFontLang w:val="he-IL" w:bidi="he-IL"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')


def footnotes_xml(doc, cfg, sep_title='הערות וציונים'):
    # the separator follows the proportions of its ornament: ornament width fixed, title size and gaps derive from its height
    FN = cfg.get('footnotes', {})
    orn_w = FN.get('ornamentW', 50)
    rid, (w, h) = MEDIA.add('line-scroll.png')
    orn_h = orn_w * h / w
    tsize = FN.get('titleRatio', 0.72) * orn_h / 0.352778
    gap = ' ' * 4
    line_c = 0.47                                           # the double line sits at 47% of the ornament height
    raise_hp = round(((1 - line_c) * orn_h - 0.33 * tsize * 0.352778) / 0.352778 * 2)   # raise the text onto the ornament lines (half-points)
    sep = (f'<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:bidi/><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
           f'{picture("line-scroll.png", orn_w, "h")}<w:r><w:rPr>{fonts(LEAD_FONT)}<w:b/><w:bCs/><w:position w:val="{raise_hp}"/>{sz(tsize)}</w:rPr>'
           f'<w:t xml:space="preserve">{gap}{escape(sep_title)}{gap}</w:t></w:r>{picture("line-scroll.png", orn_w)}</w:p></w:footnote>')
    cont = '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {NS}>{sep}{cont}{"".join(doc.footnotes)}</w:footnotes>'


# ---------------------------------------------------------------- build
def label_block(art):
    """the "סימן" title: text sits inside the framed ornament, which is a picture anchored behind the text"""
    lab = art['label']
    f = art.get('labelFrame')
    if not f:
        return para(run(lab), ST['siman'])
    name = os.path.basename(f['src'])
    MEDIA.add('composed/' + name)
    H = f['hmm'] * TW
    line = 300
    before = max(0, round((H - line) / 2))
    after = max(0, round(H - line - before))
    spacing = f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="exact"/>'
    return para(picture_behind('composed/' + name, f['wmm']) + run(lab), ST['siman'], 'center', keep=True, spacing=spacing)


def build(doc_json, layout_json, cfg_json, out):
    data = json.load(open(doc_json))
    lay = json.load(open(layout_json)) if layout_json and os.path.exists(layout_json) else None
    cfg = json.load(open(cfg_json)) if cfg_json and os.path.exists(cfg_json) else {}
    book = data['book']
    D = Doc()
    headers, parts = [], []

    def add_header(chap, tag):
        dn, en = f'header{tag}d.xml', f'header{tag}e.xml'
        headers.append((dn, header_xml(book['name'], chap, False)))     # default = odd page (left-hand)
        headers.append((en, header_xml(book['name'], chap, True)))      # even page (right-hand)
        return (f'rIdH{tag}d', f'rIdH{tag}e')
    empty_ids = ('rIdHEd', 'rIdHEe')
    headers.append(('headerEd.xml', empty_header())); headers.append(('headerEe.xml', empty_header()))

    # cover (placeholder until the real cover is supplied)
    parts.append(para('', spacing='<w:spacing w:before="2600" w:after="0" w:line="240" w:lineRule="auto"/>') +
                 para(picture('flourish-wide-1.png', 70), jc='center') +
                 para(run(book['name']), ST['coverTitle']) +
                 (para(run(book['subtitle']), ST['coverSub']) if book.get('subtitle') else '') +
                 para(picture('flourish-wide-1.png', 70, 'v'), jc='center', sect=sectpr('continuous', 1, empty_ids)))

    # table of contents: a real TOC field (outline level of the article-title style), with cached entries
    entries = [(a['title'], lay['toc'][k]['page'] if lay else k + 1) for k, a in enumerate(data['articles'])]
    toc = [para(run('תוכן עניינים'), ST['tocTitle'])]
    for k, (title, pg) in enumerate(entries):
        pre = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-1" \\u </w:instrText></w:r>'
               '<w:r><w:fldChar w:fldCharType="separate"/></w:r>') if k == 0 else ''
        post = '<w:r><w:fldChar w:fldCharType="end"/></w:r>' if k == len(entries) - 1 else ''
        sect = sectpr('nextPage', 1, empty_ids) if k == len(entries) - 1 else ''
        toc.append(para(f'{pre}<w:r><w:t xml:space="preserve">{escape(title)}</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>{heb(pg)}</w:t></w:r>{post}', 'TOC1', sect=sect))
    parts.append(''.join(toc))

    first = True
    for ai, art in enumerate(data['articles']):
        hid = add_header(art.get('shortTitle') or art['title'], f'A{ai}')
        tb = ''
        if art.get('label'):
            tb += label_block(art)
        tb += para(picture('flourish-wide-2.png', 32), jc='center', keep=True, spacing='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>')
        tb += para(run(art['title']), ST['title'])
        tb += para(picture('flourish-wide-2.png', 32, 'v'), jc='center', keep=True, spacing='<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>')
        if art.get('subtitle'):
            tb += para(run(art['subtitle']), ST['subtitle'])
        sp = (lay['tocPages'] + 1) if (lay and first) else None
        first = False
        parts.append(tb + para(run(art['author']) if art.get('author') else '', ST['author'], sect=sectpr('nextPage', 1, hid, start_page=sp)))
        chunk, restart = [], True

        def flush():
            nonlocal chunk, restart
            if not chunk:
                return
            sect = sectpr('continuous', 2, None, footnote_restart=restart)
            restart = False
            chunk[-1] = chunk[-1].replace('</w:pPr>', sect + '</w:pPr>', 1)     # the section break sits in the last paragraph of the chunk
            parts.append(''.join(chunk))
            chunk = []
        for b in art['blocks']:
            if b['t'] == 'p':
                chunk.append(para(runs_xml(D, art, b['runs']), ST['body']))
            elif b['t'] == 'h2':
                chunk.append(para(run(b['runs'][0]['t']), ST['part']))
            elif b['t'] == 'h3':
                chunk.append(para(heading_runs(D, art, b['runs']), ST['sub']))
            elif b['t'] == 'tbl':
                flush()
                parts.append(table_xml(art, b) + para('', spacing='<w:spacing w:before="0" w:after="0" w:line="40" w:lineRule="exact"/>', sect=sectpr('continuous', 1, None)))
        flush()
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{"".join(parts)}{sectpr("continuous", 2, None)}</w:body></w:document>'
    footnotes = footnotes_xml(D, cfg)          # adds the separator pictures to MEDIA

    def img_rels():
        return ''.join(f'<Relationship Id="{rel[0]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>' for name, rel in MEDIA.rels.items())
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    rels = [f'<Relationship Id="rIdStyles" Type="{R}/styles" Target="styles.xml"/>', f'<Relationship Id="rIdSettings" Type="{R}/settings" Target="settings.xml"/>',
            f'<Relationship Id="rIdFootnotes" Type="{R}/footnotes" Target="footnotes.xml"/>']
    for name, _ in headers:
        rels.append(f'<Relationship Id="rId{name.replace("header", "H").replace(".xml", "")}" Type="{R}/header" Target="{name}"/>')
    P = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    doc_rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {P}>{"".join(rels)}{img_rels()}</Relationships>'
    fn_rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {P}>{img_rels()}</Relationships>'
    hdr_rels = fn_rels
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>' +
          ''.join(f'<Override PartName="/word/{n}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>' for n, _ in headers) + '</Types>')
    root_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {P}>'
                 f'<Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
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
            z.writestr('word/_rels/' + n + '.rels', hdr_rels)
        for n, b in MEDIA.files.items():
            z.writestr('word/media/' + n, b)
    print('docx written', out, '| footnotes', D.fn_n, '| articles', len(data['articles']), '| images', len(MEDIA.files))


if __name__ == '__main__':
    a = sys.argv
    build(a[1], a[2] if len(a) > 2 else None, os.path.join(HERE, 'config.json'), a[3] if len(a) > 3 else 'out/book.docx')
