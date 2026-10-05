"""Write the formatted .docx (hand-built OOXML, no template) from model.json."""
import json, zipfile, os, sys, datetime, re
from xml.sax.saxutils import escape
from PIL import Image
from model import build, heb_num
import fontmetrics as FM

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out.docx'

# ------------------------------------------------------------------ design constants (pt unless noted)
PAGE_W, PAGE_H = 595.32, 841.92
M_TOP, M_BOTTOM, M_SIDE = 70, 56, 54       # top margin leaves room for the one-line running header
INK = '404040'
F_BODY, F_HEAD, F_NOTE, F_NUM = 'Tehila', 'RimonMF', 'Gisha', 'Times New Roman'   # running text / headings + letters / askers' names / page numbers
BODY_SZ, NOTE_SZ, EMPH_SZ = 16, 11, 13
PREVIEW = True            # RimonMF is a legacy symbol-encoded font: its text is stored the way Word stores symbol-font text (see fontmetrics.to_rimon)
def R(text):
    # symbol-font code points have no right-to-left property, so the string is stored in visual order (drawn left to right)
    return FM.to_rimon(text)[::-1] if PREVIEW else text
MARK_SZ, SQ_W, SQ_H, SQ_GAP, SQ_BLUR = 20, 8.5, 6.0, 5.0, 0.9     # marker letter size and the two side squares (pt)
HDR_SCALE, HDR_SIMAN_SZ, HDR_GAP = 0.62, 22, 8
LINE_BODY = 19.4          # line pitch measured on the example
FRAME_H = 57.19
HDR_LINE_Y = 14           # top of the header line, pt from the top edge
HDR_LINE_H = 30           # exact height of the header line
MK_BEFORE, MK_AFTER = 14.5, 0.0   # spacing around the marker line
HEAD_LINE = 46            # exact line height of the heading paragraph
SHORT_W = 470             # a question that is at most this wide (pt) fits one line and is centred

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
def rpr(font=F_BODY, sz=BODY_SZ, b=False, i=False, color=INK, u=False, scale=None, pos=None, rtl=True):
    x = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/>' % (font, font, font, font)
    if b: x += '<w:b/><w:bCs/>'
    if i: x += '<w:i/><w:iCs/>'
    x += '<w:color w:val="%s"/>' % color
    if scale: x += '<w:w w:val="%d"/>' % scale
    if pos: x += '<w:position w:val="%d"/>' % int(pos * 2)
    x += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (round(sz * 2), round(sz * 2))
    if u: x += '<w:u w:val="single"/>'
    x += ('<w:rtl/>' if rtl else '') + '<w:lang w:bidi="he-IL"/>'
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

def para(style, inner, *, keep_next=False, keep_lines=False, before=None, after=None, jc=None, line=None, rule=None, ind=None, extra_ppr='', page_break=False, bidi=True):
    p = '<w:pStyle w:val="%s"/>' % style
    if keep_next: p += '<w:keepNext/>'
    if keep_lines: p += '<w:keepLines/>'
    if page_break: p += '<w:pageBreakBefore/>'
    p += '<w:bidi/>' if bidi else '<w:bidi w:val="0"/>'
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
    rp_body = ('<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:color w:val="%s"/>'
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
             ppr='<w:keepNext/><w:bidi/><w:spacing w:before="%d" w:after="%d" w:line="%d" w:lineRule="atLeast"/><w:jc w:val="center"/>' % (tw(MK_BEFORE), tw(MK_AFTER), tw(22)),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:sz w:val="%d"/><w:szCs w:val="%d"/>' % ((F_HEAD,) * 4 + (MARK_SZ * 2, MARK_SZ * 2)))
    s += pst('Siman', 'Rithcha Siman', nxt='Marker',
             ppr='<w:keepNext/><w:bidi w:val="0"/><w:spacing w:before="0" w:after="%d" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>' % tw(3),
             rp='<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s" w:cs="%s"/><w:sz w:val="56"/><w:szCs w:val="56"/>' % ((F_HEAD,) * 4))
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

def styleref_siman(sz, raise_pt):
    """'סימן X' of the siman heading that starts first on the page (Word STYLEREF; a page that opens mid-siman carries the previous one)"""
    return ('<w:fldSimple w:instr=" STYLEREF &quot;Rithcha Siman&quot; ">%s</w:fldSimple>'
            % run(R('סימן ד'), font=F_HEAD, sz=sz, pos=raise_pt, rtl=False))

def header_groups(k, siman_sz):
    """cut the two title groups out of the title row so that the CENTRE of the title letters is the centre of the picture
    (a table cell centres picture and siman text on the same line); the siman's ink sits a little below the middle of its line box"""
    import numpy as np
    src = Image.open('assets/title_row.png').convert('RGB'); a = np.array(src.convert('L'))
    PX = 3346 / 401.5
    letters = (a[:, 719:2634] < 200).any(axis=1); ly = np.where(letters)[0]
    c = (ly.min() + ly.max()) / 2.0                                   # centre row of the title letters
    ink = (a[:, 20:3330] < 200).any(axis=1); iy = np.where(ink)[0]
    half = max(c - iy.min(), iy.max() - c) + 6
    siman_below = 0.038 * siman_sz                                    # pt: ink centre of RimonMF lies 0.038 em under the line-box centre
    yc = c - siman_below / k * PX                                     # window centre (source px): letters appear that far below the picture centre
    y0, y1 = int(round(yc - half)), int(round(yc + half))
    pad = Image.new('RGB', (src.width, y1 - y0), (255, 255, 255)); pad.paste(src, (0, -y0))
    left = pad.crop((20, 0, 1800, pad.height)); left.save('assets/hdr_left.png')
    right = pad.crop((1885, 0, 3330, pad.height)); right.save('assets/hdr_right.png')
    return dict(h=(y1 - y0) / PX * k, wl=left.width / PX * k, wr=right.width / PX * k)

def header_xml():
    g = header_groups(HDR_SCALE, HDR_SIMAN_SZ)
    left = inline_pic('hdr_left.png', g['wl'], g['h'], 'Title L', 'דאורייתא')
    right = inline_pic('hdr_right.png', g['wr'], g['h'], 'Title R', 'ריתחא')
    text_w = PAGE_W - 2 * M_SIDE
    gap = HDR_GAP
    w_l, w_r = g['wl'] + gap, g['wr'] + gap                         # side cells: group + the gap towards the siman
    w_c = text_w - w_l - w_r                                        # middle cell: the siman, centred (wide enough for the longest heading)
    def cell(w, jc, inner):
        ppr = ('<w:pPr><w:pStyle w:val="Header"/><w:bidi w:val="0"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="%s"/></w:pPr>' % jc)
        return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr><w:p>%s%s</w:p></w:tc>' % (tw(w), ppr, inner))
    tbl = ('<w:tbl><w:tblPr><w:bidiVisual w:val="0"/><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="%d"/><w:gridCol w:w="%d"/><w:gridCol w:w="%d"/></w:tblGrid>'
           '<w:tr><w:trPr><w:trHeight w:val="%d" w:hRule="atLeast"/></w:trPr>%s%s%s</w:tr></w:tbl>'
           % (tw(text_w), tw(w_l), tw(w_c), tw(w_r), tw(HDR_LINE_H),
              cell(w_l, 'left', left), cell(w_c, 'center', styleref_siman(HDR_SIMAN_SZ, 0)), cell(w_r, 'right', right)))
    last = ('<w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi w:val="0"/><w:spacing w:before="0" w:after="0" w:line="40" w:lineRule="exact"/></w:pPr>%s</w:p>' % borders())
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr %s>%s%s</w:hdr>' % (NS, tbl, last)

def footer_xml():
    bw, bh = 54.26, 47.98          # the example squeezes the plaque top horizontally to make the badge
    badge = anchor_pic('page_badge.png', bw, bh, 'Page badge', x=270.53, y=PAGE_H - bh)
    fld = lambda t: '<w:r>%s%s</w:r>' % (rpr(font=F_NUM, sz=14, b=True), t)
    num = (fld('<w:fldChar w:fldCharType="begin"/>') + fld('<w:instrText xml:space="preserve"> PAGE </w:instrText>') +
           fld('<w:fldChar w:fldCharType="separate"/>') + run('א', font=F_NUM, sz=14, b=True) + fld('<w:fldChar w:fldCharType="end"/>'))
    p = ('<w:p><w:pPr><w:pStyle w:val="Footer"/><w:bidi/><w:spacing w:before="0" w:after="0" w:line="%d" w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>%s%s</w:p>'
         % (tw(18), badge, num))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr %s>%s</w:ftr>' % (NS, p)

# ------------------------------------------------------------------ body
FRAMES = None
def heading_layout(text):
    global FRAMES
    if FRAMES is None: FRAMES = json.load(open('assets/frames.json'))
    for fn in ('frame_std_t.png', 'frame_mid_t.png', 'frame_wide_t.png'):
        f = FRAMES[fn]
        for size in (28, 26, 24, 22, 20, 18):
            if FM.text_width(text, 'rimon', size) <= f['vis_w'] - 56: return fn, f['w'], f['h'], size
    f = FRAMES['frame_wide_t.png']; return 'frame_wide_t.png', f['w'], f['h'], 16

def heading_xml(text, first_on_page=False, page_break=False):
    fn, fw, fh, size = heading_layout(text)
    spacer = para('Normal', '', keep_next=True, line=(8 if first_on_page else 30), rule='exact', jc='center', page_break=page_break)
    # single line spacing: the baseline is 0.8 em below the paragraph top (RimonMF ascent 800); the whole ink of the string
    # (final-nun tail included) is centred vertically in the frame
    top = 0.8 * size - FM.ink_vcentre(text) * size - fh / 2
    pic = anchor_pic(fn, fw, fh, 'Frame', h_rel='column', h_align='center', v_rel='paragraph', y=top, descr='')
    # horizontal: move the INK of the string (not its advance box) to the middle
    d = FM.ink_shift_pt(text, size)                      # >0: the ink sits right of the middle of the advance box
    ind = ('<w:ind w:left="0" w:right="%d"/>' % tw(2 * d)) if d > 0 else ('<w:ind w:left="%d" w:right="0"/>' % tw(-2 * d))
    r = '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr(font=F_HEAD, sz=size, rtl=False), escape(R(text)))
    return spacer + para('Siman', pic + r, keep_next=True, bidi=False, ind=ind)

# ------------------------------------------------------------------ marker: [square][letter][square], the letter centred between the squares
def marker_images(k, letters):
    """two small soft squares as pictures. Their height above the baseline and the space between square and letter ink are computed
    from the RimonMF glyph outlines of this very letter, so every letter sits exactly in the middle of the two squares."""
    key = 'mk%d' % k
    ink = FM.rimon_ink(letters); s = MARK_SZ / 1000.0
    cy = (ink['ymin'] + ink['ymax']) / 2 * s                    # vertical centre of the letter above the baseline (pt)
    pad_l = max(0.0, SQ_GAP - ink['left_off'] * s)              # space between left square and the letter's advance box
    pad_r = max(0.0, SQ_GAP - ink['right_off'] * s)
    PX = 16; m = 1.6                                            # px per pt, blur margin (pt)
    below = max(0.0, cy - SQ_H / 2 - m)                          # empty canvas under the margin of the square
    top_h = SQ_H + 2 * m
    H = below + top_h
    out = {}
    for side, pad in (('L', pad_l), ('R', pad_r)):
        W = m + SQ_W + m + pad
        a = Image.new('L', (int(round(W * PX)), int(round(H * PX))), 0)
        from PIL import ImageDraw, ImageFilter
        d = ImageDraw.Draw(a)
        x0 = m if side == 'L' else pad + m
        yt = (H - below - m - SQ_H) * PX
        d.rectangle([x0 * PX, yt, (x0 + SQ_W) * PX, yt + SQ_H * PX], fill=235)
        a = a.filter(ImageFilter.GaussianBlur(SQ_BLUR * PX / 2.2))
        im = Image.new("RGBA", a.size, (205, 205, 205, 0)); im.putalpha(a)
        fn = '%s%s.png' % (key, side); im.save('assets/' + fn)
        out[side] = (fn, W, H)
    return out

def marker_xml(k):
    letters = heb_num(k)
    im = marker_images(k, letters)
    L, Rr = im['L'], im['R']
    # right-to-left paragraph: the first object in the file is the one on the visual RIGHT
    inner = (inline_pic(Rr[0], Rr[1], Rr[2], 'sq', '') + run(R(letters), font=F_HEAD, sz=MARK_SZ, rtl=False) + inline_pic(L[0], L[1], L[2], 'sq', ''))
    return para('Marker', inner, keep_next=True)

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
        parts.append(marker_xml(k))
        blocks = e['blocks']
        for bi, b in enumerate(blocks):
            kind = b['kind']
            last = bi == len(blocks) - 1
            kn = e is last_item      # last item before the closing ornament: chain it to the ornament
            if kind == 'q':
                prev_is_q = bi > 0 and blocks[bi - 1]['kind'] in ('q', 'sub')
                qs = [x for x in blocks if x['kind'] in ('q', 'sub')]
                short = len(qs) == 1 and FM.text_width(''.join(t for t, _ in b['runs']), 'tehila', BODY_SZ) <= SHORT_W
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

