"""Write the formatted .docx (hand-built OOXML, no template) from model.json."""
import json, zipfile, os, sys, datetime, re
from xml.sax.saxutils import escape
from PIL import Image
from model import build, heb_num

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out.docx'

# ------------------------------------------------------------------ design constants (pt unless noted)
PAGE_W, PAGE_H = 595.32, 841.92
M_TOP, M_BOTTOM, M_SIDE = 90, 56, 54       # top margin leaves room for the running title + siman line
INK = '404040'
F_BODY, F_HEAD, F_NOTE = 'Times New Roman', 'Narkisim', 'Gisha'
BODY_SZ, NOTE_SZ, EMPH_SZ = 14, 11, 13
LINE_BODY = 19.4          # line pitch measured on the example
FRAME_H = 57.19
HDR_LINE_Y = 52           # top of the siman line in the header
HDR_TITLE_Y = 12          # running title row, pt from the top edge
HEAD_LINE = 46            # exact line height of the heading paragraph
SHORT_CHARS = 76          # questions up to this length (one line) are centred

EMU = 12700
tw = lambda pt: int(round(pt * 20))
emu = lambda pt: int(round(pt * EMU))

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

# ------------------------------------------------------------------ media registry
MEDIA = {}          # filename -> rId (same ids reused in every part for simplicity)
def media_id(fn):
    if fn not in MEDIA: MEDIA[fn] = 'rIdImg%d' % (len(MEDIA) + 1)
    return MEDIA[fn]

_docpr = [0]
def next_id():
    _docpr[0] += 1; return _docpr[0]

def px_pt(fn, width_pt=None, height_pt=None):
    w, h = Image.open('assets/' + fn).size
    if width_pt: return width_pt, width_pt * h / w
    return height_pt * w / h, height_pt

def pic_xml(fn, w_pt, h_pt, name):
    rid = media_id(fn); i = next_id()
    return ('<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            '<pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic>') % (i, name, rid, emu(w_pt), emu(h_pt)), i

def inline_pic(fn, w_pt, h_pt, name, descr=''):
    g, i = pic_xml(fn, w_pt, h_pt, name)
    return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="%d" cy="%d"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="%d" name="%s" descr="%s"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>%s</wp:inline></w:drawing></w:r>'
            ) % (emu(w_pt), emu(h_pt), i, name, escape(descr), g)

_rel = [250000000]
def anchor_pic(fn, w_pt, h_pt, name, *, x=None, y=None, h_rel='page', v_rel='page', h_align=None, behind=True, descr=''):
    g, i = pic_xml(fn, w_pt, h_pt, name)
    _rel[0] += 1
    ph = ('<wp:positionH relativeFrom="%s"><wp:align>%s</wp:align></wp:positionH>' % (h_rel, h_align)) if h_align else \
         ('<wp:positionH relativeFrom="%s"><wp:posOffset>%d</wp:posOffset></wp:positionH>' % (h_rel, emu(x)))
    pv = '<wp:positionV relativeFrom="%s"><wp:posOffset>%d</wp:posOffset></wp:positionV>' % (v_rel, emu(y))
    return ('<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="%d" behindDoc="%d" '
            'locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>%s%s<wp:extent cx="%d" cy="%d"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/><wp:docPr id="%d" name="%s" descr="%s"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>%s</wp:anchor></w:drawing></w:r>'
            ) % (_rel[0] - 250000000 + 100, 1 if behind else 0, ph, pv, emu(w_pt), emu(h_pt), i, name, escape(descr), g)

# ------------------------------------------------------------------ run / paragraph helpers
def rpr(font=F_BODY, sz=BODY_SZ, b=True, i=False, color=INK, u=False, scale=None, pos=None):
    x = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>' % (font, font, font, font)
    if b: x += '<w:b/><w:bCs/>'
    if i: x += '<w:i/><w:iCs/>'
    x += '<w:color w:val="%s"/>' % color
    if scale: x += '<w:w w:val="%d"/>' % scale
    if pos: x += '<w:position w:val="%d"/>' % int(pos * 2)
    x += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz * 2, sz * 2)
    if u: x += '<w:u w:val="single"/>'
    x += '<w:rtl/><w:lang w:bidi="he-IL"/>'
    return '<w:rPr>' + x + '</w:rPr>'

def run(text, **kw):
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr(**kw), escape(text))

def body_runs(runs, base):
    """model runs -> w:r xml. base: dict of rpr kwargs for normal text; emphasised bold text becomes Gisha bold (as in the example)"""
    out = ''
    for text, f in runs:
        kw = dict(base)
        if f.get('e'): kw.update(font=F_NOTE, sz=EMPH_SZ, b=True)
        if f.get('u'): kw['u'] = True
        out += run(text, **kw)
    return out

def para(style, inner, *, keep_next=False, keep_lines=False, before=None, after=None, jc=None, line=None, rule=None, ind=None, extra_ppr='', page_break=False):
    p = '<w:pStyle w:val="%s"/>' % style
    if keep_next: p += '<w:keepNext/>'
    if keep_lines: p += '<w:keepLines/>'
    if page_break: p += '<w:pageBreakBefore/>'
    p += '<w:bidi/>'
    if before is not None or after is not None or line is not None:
        p += '<w:spacing'
        if before is not None: p += ' w:before="%d"' % tw(before)
        if after is not None: p += ' w:after="%d"' % tw(after)
        if line is not None: p += ' w:line="%d" w:lineRule="%s"' % (tw(line), rule or 'exact')
        p += '/>'
    if ind: p += ind
    if jc: p += '<w:jc w:val="%s"/>' % jc
    p += extra_ppr
    return '<w:p><w:pPr>%s</w:pPr>%s</w:p>' % (p, inner)

# ------------------------------------------------------------------ styles
def style_xml():
    def pst(sid, name, based='Normal', nxt=None, ppr='', rp='', default=False, ui=None):
        return ('<w:style w:type="paragraph" %sw:styleId="%s"><w:name w:val="%s"/>%s%s%s<w:qFormat/>'
                '<w:pPr>%s</w:pPr><w:rPr>%s</w:rPr></w:style>') % (
            'w:default="1" ' if default else '', sid, name,
            ('<w:basedOn w:val="%s"/>' % based) if based else '',
            ('<w:next w:val="%s"/>' % nxt) if nxt else '', '', ppr, rp)
    rp_body = ('<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:b/><w:bCs/><w:color w:val="%s"/>'
               '<w:sz w:val="%d"/><w:szCs w:val="%d"/><w:lang w:val="he-IL" w:eastAsia="he-IL" w:bidi="he-IL"/>'
               % (F_BODY, F_BODY, F_BODY, F_BODY, INK, BODY_SZ * 2, BODY_SZ * 2))
    s = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles %s>'
         '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>'
         '<w:sz w:val="%d"/><w:szCs w:val="%d"/><w:lang w:val="he-IL" w:eastAsia="he-IL" w:bidi="he-IL"/></w:rPr></w:rPrDefault>'
         '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
         ) % (NS, F_BODY, F_BODY, F_BODY, F_BODY, BODY_SZ * 2, BODY_SZ * 2)
    s += pst('Normal', 'Normal', based=None, default=True, ppr='<w:bidi/><w:spacing w:after="0" w:line="%d" w:lineRule="atLeast"/><w:jc w:val="both"/>' % tw(LINE_BODY), rp=rp_body)
    s += pst('Question', 'Rithcha Question', ppr='<w:widowControl/><w:bidi/><w:jc w:val="both"/>')
    s += pst('Marker', 'Rithcha Marker', nxt='Question',
             ppr='<w:keepNext/><w:bidi/><w:spacing w:before="%d" w:after="%d" w:line="%d" w:lineRule="atLeast"/><w:jc w:val="center"/>' % (tw(15.7), tw(1.3), tw(22)),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:b/><w:bCs/><w:i/><w:iCs/><w:sz w:val="34"/><w:szCs w:val="34"/>' % ((F_HEAD,) * 4))
    s += pst('Siman', 'Rithcha Siman', nxt='Marker',
             ppr='<w:keepNext/><w:bidi/><w:spacing w:before="0" w:after="0" w:line="%d" w:lineRule="exact"/><w:jc w:val="center"/>' % tw(HEAD_LINE),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:b/><w:bCs/><w:i/><w:iCs/><w:sz w:val="52"/><w:szCs w:val="52"/>' % ((F_HEAD,) * 4))
    s += pst('Caption', 'Rithcha Caption', nxt='Marker',
             ppr='<w:keepNext/><w:bidi/><w:spacing w:before="%d" w:after="0" w:line="%d" w:lineRule="atLeast"/><w:jc w:val="center"/>' % (tw(8), tw(17)),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/>' % ((F_NOTE,) * 4))
    s += pst('Note', 'Rithcha Note',
             ppr='<w:bidi/><w:spacing w:before="%d" w:after="0" w:line="%d" w:lineRule="atLeast"/><w:jc w:val="right"/>' % (tw(3), tw(15)),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:b w:val="0"/><w:bCs w:val="0"/><w:sz w:val="%d"/><w:szCs w:val="%d"/>' % ((F_NOTE,) * 4 + (NOTE_SZ * 2, NOTE_SZ * 2)))
    s += pst('Source', 'Rithcha Source', based='Note',
             ppr='<w:bidi/><w:spacing w:before="%d" w:after="0"/><w:jc w:val="both"/>' % tw(4))
    s += pst('Header', 'header', ppr='<w:bidi/><w:spacing w:line="240" w:lineRule="auto"/><w:jc w:val="left"/>', rp='<w:sz w:val="4"/><w:szCs w:val="4"/>')
    s += pst('Footer', 'footer', ppr='<w:bidi/><w:spacing w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>')
    s += '</w:styles>'
    return s

# ------------------------------------------------------------------ header / footer parts
def borders():
    w, h = 34.06, PAGE_H
    return (anchor_pic('border_left.png', w, h, 'Border L', x=0, y=0) +
            anchor_pic('border_right.png', w, h, 'Border R', x=PAGE_W - w, y=0))

def styleref_siman(sz=18):
    """'סימן X' of the siman heading that starts first on the page (Word STYLEREF; for pages that open mid-siman it carries over the last one)"""
    rp = lambda: rpr(font=F_HEAD, sz=sz, b=True, i=True)
    fc = lambda t: '<w:r>%s%s</w:r>' % (rp(), t)
    return (fc('<w:fldChar w:fldCharType="begin"/>') +
            fc('<w:instrText xml:space="preserve"> STYLEREF "Rithcha Siman" </w:instrText>') +
            fc('<w:fldChar w:fldCharType="separate"/>') + run('סימן ד', font=F_HEAD, sz=sz, b=True, i=True) +
            fc('<w:fldChar w:fldCharType="end"/>'))

def header_xml():
    tw_, th_ = px_pt('title_row.png', width_pt=401.5)
    title = anchor_pic('title_row.png', tw_, th_, 'Title', x=(PAGE_W - tw_) / 2, y=HDR_TITLE_Y, descr='ריתחא דאורייתא')
    sq = lambda: run('■', font='Arial', sz=11, b=False, color='C8C8C8', scale=130, pos=2.5)
    sp = lambda: run(' ', font=F_NOTE, sz=6, b=False)
    inner = borders() + title + sq() + sp() + styleref_siman() + sp() + sq()
    ppr = ('<w:pPr><w:pStyle w:val="Header"/><w:bidi/><w:spacing w:before="0" w:after="0" w:line="%d" w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>' % tw(22))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr %s><w:p>%s%s</w:p></w:hdr>' % (NS, ppr, inner)

def footer_xml():
    bw, bh = 54.26, 47.98          # the example squeezes the plaque top horizontally to make the badge
    badge = anchor_pic('page_badge.png', bw, bh, 'Page badge', x=270.53, y=PAGE_H - bh)
    fld = lambda t: '<w:r>%s%s</w:r>' % (rpr(font=F_HEAD, sz=15, b=True, i=True), t)
    num = (fld('<w:fldChar w:fldCharType="begin"/>') + fld('<w:instrText xml:space="preserve"> PAGE </w:instrText>') +
           fld('<w:fldChar w:fldCharType="separate"/>') + run('א', font=F_HEAD, sz=15, b=True, i=True) + fld('<w:fldChar w:fldCharType="end"/>'))
    p = ('<w:p><w:pPr><w:pStyle w:val="Footer"/><w:bidi/><w:spacing w:before="0" w:after="0" w:line="%d" w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>%s%s</w:p>'
         % (tw(18), badge, num))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr %s>%s</w:ftr>' % (NS, p)

# ------------------------------------------------------------------ body
def heading_xml(text, first_on_page=False, page_break=False):
    n = len(text)
    if n <= 9:   frame, fw, size = 'frame_std.png', 196.46, 28
    elif n <= 16: frame, fw, size = 'frame_mid.png', 290.0, 24
    else:        frame, fw, size = 'frame_wide.png', 400.0, 22
    fh = FRAME_H
    spacer = para('Normal', '', keep_next=True, line=(8 if first_on_page else 30), rule='exact', jc='center', page_break=page_break)
    pic = anchor_pic(frame, fw, fh, 'Frame', h_rel='column', h_align='center', v_rel='paragraph', y=(HEAD_LINE - fh) / 2 - 1.0, descr='')
    r = '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (
        rpr(font=F_HEAD, sz=size, b=True, i=True, pos=5), escape(text))
    return spacer + para('Siman', pic + r, keep_next=True)

def marker_xml(letter):
    sq = lambda: run('■', font='Arial', sz=11, b=False, color='C8C8C8', scale=130, pos=2.5)
    sp = lambda: run(' ', font=F_NOTE, sz=6, b=False)
    return para('Marker', sq() + sp() + run(letter, font=F_HEAD, sz=17, b=True, i=True) + sp() + sq(), keep_next=True)

PREFIX = re.compile(r'^\s*הלכה\s+ו?למעשה\s*:?\s*')
def drop_prefix(runs):
    """remove the 'הלכה למעשה:' label from the front of a question"""
    text = ''.join(t for t, _ in runs)
    m = PREFIX.match(text)
    if not m: return runs
    cut = m.end(); out = []
    for t, f in runs:
        if cut >= len(t): cut -= len(t); continue
        out.append((t[cut:], f)); cut = 0
    return out

def emit_section(parts, sec, first_on_page, last_item=None, page_break=False):
    text = ('סימן ' + sec['num']) if sec['num'] else sec['title']
    parts.append(heading_xml(text, first_on_page=first_on_page, page_break=page_break))
    k = 0
    for e in sec['entries']:
        if e['type'] != 'item': continue          # sub-headings / captions are not used
        k += 1
        parts.append(marker_xml(heb_num(k)))
        blocks = e['blocks']
        for bi, b in enumerate(blocks):
            kind = b['kind']
            last = bi == len(blocks) - 1
            kn = e is last_item      # last item before the closing ornament: chain it to the ornament
            if kind == 'q':
                prev_is_q = bi > 0 and blocks[bi - 1]['kind'] in ('q', 'sub')
                qs = [x for x in blocks if x['kind'] in ('q', 'sub')]
                short = len(qs) == 1 and len(''.join(t for t, _ in b['runs'])) <= SHORT_CHARS
                parts.append(para('Question', body_runs(b['runs'], {}), before=(5 if prev_is_q else None), jc=('center' if short else None),
                                  keep_next=kn or (not last and blocks[bi + 1]['kind'] == 'name') or False, keep_lines=kn))
            elif kind == 'sub':
                lab = run(b['label'] + '. ', font=F_NOTE, sz=EMPH_SZ, b=True)
                parts.append(para('Question', lab + body_runs(b['runs'], {}), before=5, keep_next=kn, keep_lines=kn))
            elif kind == 'src':
                parts.append(para('Source', body_runs(b['runs'], dict(font=F_NOTE, sz=NOTE_SZ, b=False)), keep_next=kn, keep_lines=kn))
            elif kind == 'name':
                runs = [('[', {})] + list(b['runs']) + [(']', {})]
                parts.append(para('Note', body_runs(runs, dict(font=F_NOTE, sz=NOTE_SZ, b=False)), keep_next=kn, keep_lines=kn))

def ornament_xml():
    ow, oh = px_pt('end_ornament.png', width_pt=238.1)
    return para('Normal', inline_pic('end_ornament.png', ow, oh, 'Ornament', ''), jc='center', before=30, line=None)

def build_body(part1, part2):
    """part1: the questions by siman (ends with the ornament); part2: 'הלכה למעשה' – starts on a new page"""
    parts = []
    last_item = [e for e in part1[-1]['entries'] if e['type'] == 'item'][-1]
    for i, sec in enumerate(part1):
        emit_section(parts, sec, first_on_page=(i == 0), last_item=last_item if sec is part1[-1] else None)
    parts.append(ornament_xml())
    for i, sec in enumerate(part2):
        emit_section(parts, sec, first_on_page=(i == 0), page_break=(i == 0))
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdHdr"/><w:footerReference w:type="default" r:id="rIdFtr"/>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" w:header="%d" w:footer="%d" w:gutter="0"/>'
            '<w:pgNumType w:fmt="hebrew1" w:start="1"/><w:cols w:space="708"/><w:bidi/><w:docGrid w:linePitch="360"/></w:sectPr>'
            % (tw(M_TOP), tw(M_SIDE), tw(M_BOTTOM), tw(M_SIDE), tw(HDR_LINE_Y), tw(6)))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document %s><w:body>%s%s</w:body></w:document>' % (NS, ''.join(parts), sect)

# ------------------------------------------------------------------ package
def package(part1, part2, out):
    body = build_body(part1, part2)
    hdr, ftr = header_xml(), footer_xml()
    rels_media = ''.join('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/%s"/>' % (rid, fn)
                         for fn, rid in MEDIA.items())
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
                    '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                 '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                 '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rIdSty" Type="%sstyles" Target="styles.xml"/><Relationship Id="rIdSet" Type="%ssettings" Target="settings.xml"/>'
                '<Relationship Id="rIdHdr" Type="%sheader" Target="header1.xml"/>'
                '<Relationship Id="rIdFtr" Type="%sfooter" Target="footer1.xml"/>%s</Relationships>') % (R, R, R, R, rels_media)
    part_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % rels_media
    settings = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings %s><w:zoom w:percent="100"/><w:defaultTabStop w:val="720"/>'
                '<w:characterSpacingControl w:val="doNotCompress"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
                '<w:themeFontLang w:val="en-US" w:bidi="he-IL"/><w:decimalSymbol w:val="."/><w:listSeparator w:val=","/></w:settings>') % NS
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>ריתחא דאורייתא</dc:title><dc:language>he-IL</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified></cp:coreProperties>') % (now, now)
    app = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Microsoft Office Word</Application></Properties>'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', root_rels)
        z.writestr('word/document.xml', body); z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/styles.xml', style_xml()); z.writestr('word/settings.xml', settings)
        z.writestr('word/header1.xml', hdr); z.writestr('word/footer1.xml', ftr)
        for n in ('header1', 'footer1'):
            z.writestr('word/_rels/%s.xml.rels' % n, part_rels)
        for fn in MEDIA: z.write('assets/' + fn, 'word/media/' + fn)
        z.writestr('docProps/core.xml', core); z.writestr('docProps/app.xml', app)

