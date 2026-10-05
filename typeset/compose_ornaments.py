#!/usr/bin/env python3
"""Prepares the ornaments that must fit a given size, from the (tinted) ornament set. Only plain line sections are
stretched; the ornamental parts are never distorted.

  prepare()          header-rule.png   running-header rule (curl ends + centre flourish, lines stretched to the text width)
                     frame-capL/capR/mid.png   the three slices of the frame ornament (the PDF engine assembles them in the DOM)
                     fn-lines.png      the plain double line used on both sides of "הערות וציונים"
  word_frames(layout) frame PNGs composed to the exact size of every article title / divider (for the Word file)

usage: compose_ornaments.py            (prepare)
       compose_ornaments.py layout.json (prepare + Word frames, uses the sizes the PDF engine computed)
"""
import json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'ornaments')
OUT = os.path.join(SRC, 'composed')
DPI = 600
PX_MM = DPI / 25.4
TEXT_W_MM = 176 - 19.4 * 2
HEADER_RULE_H_MM = 5.0
FN_LINES_H_MM = 1.9
FRAME_CAP_L = 440          # native px of frame.png (3304 x 995): caps are x<440 and x>2880
FRAME_CAP_R = 2880
FRAME_MID = (900, 1500)    # a plain stretch of the double lines


def load(name):
    return Image.open(os.path.join(SRC, name + '.png')).convert('RGBA')


def header_rule(width_mm=TEXT_W_MM, height_mm=HEADER_RULE_H_MM):
    im = load('divider-long')                      # 2913 x 277
    s = height_mm * PX_MM / im.height
    H, W = round(im.height * s), round(width_mm * PX_MM)
    sc = lambda part: part.resize((max(1, round(part.width * s)), H), Image.LANCZOS)
    capL, center, capR = sc(im.crop((0, 0, 140, im.height))), sc(im.crop((1050, 0, 1830, im.height))), sc(im.crop((2740, 0, im.width, im.height)))
    line = im.crop((300, 0, 900, im.height)).resize((600, H), Image.LANCZOS)
    rest = W - capL.width - center.width - capR.width
    wl = rest // 2
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    x = 0
    out.alpha_composite(capL, (x, 0)); x += capL.width
    out.alpha_composite(line.resize((wl, H), Image.BILINEAR), (x, 0)); x += wl
    out.alpha_composite(center, (x, 0)); x += center.width
    out.alpha_composite(line.resize((rest - wl, H), Image.BILINEAR), (x, 0)); x += rest - wl
    out.alpha_composite(capR, (x, 0))
    return out


def frame_slices():
    im = load('frame')
    return im.crop((0, 0, FRAME_CAP_L, im.height)), im.crop((FRAME_CAP_R, 0, im.width, im.height)), im.crop((FRAME_MID[0], 0, FRAME_MID[1], im.height))


def frame_png(width_mm, height_mm, cloud=False):
    """frame ornament of exactly width x height (mm): caps keep their shape, the middle line section is stretched.  cloud: the faint cloud of aged paper behind the title
    (assets/ornaments/title-cloud.png, if the antique ornament set made it) goes under the frame, as the PDF engine draws it."""
    capL, capR, mid = frame_slices()
    H = round(height_mm * PX_MM)
    s = H / capL.height
    W = round(width_mm * PX_MM)
    cl = capL.resize((max(1, round(capL.width * s)), H), Image.LANCZOS)
    cr = capR.resize((max(1, round(capR.width * s)), H), Image.LANCZOS)
    rest = max(1, W - cl.width - cr.width)
    out = Image.new('RGBA', (cl.width + rest + cr.width, H), (0, 0, 0, 0))
    cpath = os.path.join(SRC, 'title-cloud.png')
    if cloud and os.path.exists(cpath):
        x0, x1 = round(cl.width * 0.45), out.width - round(cr.width * 0.45)             # the same box as in the engine: 45 % of the caps in from both ends, 6 % beyond top and bottom
        ch = round(H * 1.12)
        c = Image.open(cpath).convert('RGBA').resize((max(1, x1 - x0), ch), Image.LANCZOS)
        top = round(H * 0.06)
        out.alpha_composite(c.crop((0, top, c.width, top + H)), (x0, 0))
    out.alpha_composite(cl, (0, 0))
    out.alpha_composite(mid.resize((rest, H), Image.BILINEAR), (cl.width, 0))
    out.alpha_composite(cr, (cl.width + rest, 0))
    return out


def fn_lines(width_mm=60, height_mm=FN_LINES_H_MM):
    """the plain double line of line-scroll (the curled end is left out)"""
    im = load('line-scroll').crop((520, 62, 1800, 148))
    return im.resize((round(width_mm * PX_MM), round(height_mm * PX_MM)), Image.LANCZOS)


def prepare():
    os.makedirs(OUT, exist_ok=True)
    header_rule().save(os.path.join(OUT, 'header-rule.png'), optimize=True)
    capL, capR, mid = frame_slices()
    capL.save(os.path.join(OUT, 'frame-capL.png'), optimize=True)
    capR.save(os.path.join(OUT, 'frame-capR.png'), optimize=True)
    mid.save(os.path.join(OUT, 'frame-mid.png'), optimize=True)
    fn_lines().save(os.path.join(OUT, 'fn-lines.png'), optimize=True)
    print('composed: header rule, frame slices, footnote lines')


def word_frames(layout_path):
    lay = json.load(open(layout_path))
    n = 0
    for key, boxes in (('titleBoxes', lay.get('titleBoxes', {})), ('dividerBoxes', lay.get('dividerBoxes', {}))):
        for k, b in boxes.items():
            name = f'{key[:-5]}-{k}.png'
            frame_png(b['wmm'], b['hmm'], cloud=(key == 'titleBoxes')).save(os.path.join(OUT, name), optimize=True)
            b['png'] = name
            n += 1
    json.dump(lay, open(layout_path, 'w'), ensure_ascii=False, indent=1)
    print('composed %d Word frames' % n)


if __name__ == '__main__':
    prepare()
    if len(sys.argv) > 1:
        word_frames(sys.argv[1])
