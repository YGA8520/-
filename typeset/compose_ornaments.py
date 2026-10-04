#!/usr/bin/env python3
"""Composes ornaments that must fit a given width, from the supplied ornament set (no distortion of the ornamental
parts: only the plain line sections are stretched).

  * header-rule.png      the running-header rule  (divider-long: curl ends + centre flourish, lines stretched)
  * label-frame-*.png    the framed ornament for the "סימן" label, one PNG per width needed

usage: compose_ornaments.py book.doc.json   -> writes assets/ornaments/composed/*.png, composed.json and
                                              adds `labelFrame` to every article of the doc json
"""
import json, os, sys, math
from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'ornaments')
OUT = os.path.join(SRC, 'composed')
DPI = 600
PX_MM = DPI / 25.4

TEXT_W_MM = 176 - 19.4 * 2          # page 176, margins 19.4
HEADER_RULE_H_MM = 5.0
FRAME_H_MM = 13.0
LABEL_PT = 13.0
LABEL_FONT = os.path.join(HERE, 'assets', 'fonts', 'DavidLibre-Bold.ttf')


def load(name):
    return Image.open(os.path.join(SRC, name + '.png')).convert('RGBA')


def hstretch(im, x0, x1, width, height=None):
    """take the (uniform) columns x0..x1 of `im` and stretch them horizontally to `width` px."""
    strip = im.crop((x0, 0, x1, im.height))
    if height:
        strip = strip.resize((strip.width, height), Image.LANCZOS)
    return strip.resize((max(1, width), strip.height), Image.BILINEAR)


def header_rule(width_mm=TEXT_W_MM, height_mm=HEADER_RULE_H_MM):
    im = load('divider-long')                      # 2913 x 277
    s = height_mm * PX_MM / im.height
    H = round(im.height * s)
    W = round(width_mm * PX_MM)
    def sc(part):
        return part.resize((max(1, round(part.width * s)), H), Image.LANCZOS)
    capL = sc(im.crop((0, 0, 140, im.height)))
    center = sc(im.crop((1050, 0, 1830, im.height)))
    capR = sc(im.crop((2740, 0, im.width, im.height)))
    line = im.crop((300, 0, 900, im.height)).resize((600, H), Image.LANCZOS)     # uniform line section, height scaled
    rest = W - capL.width - center.width - capR.width
    wl = rest // 2
    wr = rest - wl
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    x = 0
    out.alpha_composite(capL, (x, 0)); x += capL.width
    out.alpha_composite(line.resize((wl, H), Image.BILINEAR), (x, 0)); x += wl
    out.alpha_composite(center, (x, 0)); x += center.width
    out.alpha_composite(line.resize((wr, H), Image.BILINEAR), (x, 0)); x += wr
    out.alpha_composite(capR, (x, 0))
    return out


def label_text_mm(text):
    f = ImageFont.truetype(LABEL_FONT, round(LABEL_PT / 72 * DPI))
    return f.getlength(text) / PX_MM


def label_frame(width_mm, height_mm=FRAME_H_MM):
    im = load('frame')                             # 3304 x 995 : caps are x<440 and x>2880, the middle is plain double lines
    s = height_mm * PX_MM / im.height
    H = round(im.height * s)
    W = round(width_mm * PX_MM)
    def sc(part):
        return part.resize((max(1, round(part.width * s)), H), Image.LANCZOS)
    capL = sc(im.crop((0, 0, 440, im.height)))
    capR = sc(im.crop((2880, 0, im.width, im.height)))
    mid = im.crop((900, 0, 1500, im.height)).resize((600, H), Image.LANCZOS)
    rest = W - capL.width - capR.width
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    out.alpha_composite(capL, (0, 0))
    out.alpha_composite(mid.resize((max(1, rest), H), Image.BILINEAR), (capL.width, 0))
    out.alpha_composite(capR, (capL.width + max(1, rest), 0))
    return out, capL.width / PX_MM


def main(doc_path):
    os.makedirs(OUT, exist_ok=True)
    hr = header_rule()
    hr.save(os.path.join(OUT, 'header-rule.png'), optimize=True)
    info = {'header-rule': {'src': 'assets/ornaments/composed/header-rule.png', 'wmm': TEXT_W_MM, 'hmm': HEADER_RULE_H_MM}}
    doc = json.load(open(doc_path))
    frames = {}
    for a in doc['articles']:
        lab = a.get('label')
        if not lab:
            continue
        tw = label_text_mm(lab)
        _, cap = label_frame(60)
        w = tw + 2 * cap + 2 * 2.5               # text + both caps + a little air
        w = max(46.0, math.ceil(w / 2) * 2)      # bucket to 2mm, minimum 46mm
        key = f'label-frame-{int(w)}.png'
        if key not in frames:
            im, capmm = label_frame(w)
            im.save(os.path.join(OUT, key), optimize=True)
            frames[key] = {'src': 'assets/ornaments/composed/' + key, 'wmm': w, 'hmm': FRAME_H_MM, 'capmm': capmm}
        a['labelFrame'] = frames[key]
    info['frames'] = frames
    json.dump(info, open(os.path.join(OUT, 'composed.json'), 'w'), indent=1)
    json.dump(doc, open(doc_path, 'w'), ensure_ascii=False)
    print('composed: header rule + %d label frames (widths mm: %s)' % (len(frames), sorted(int(v['wmm']) for v in frames.values())))


if __name__ == '__main__':
    main(sys.argv[1])
