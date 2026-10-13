#!/usr/bin/env python3
"""The frame of the haskama pages (assets/haskamot/frame-<name>.png, transparent): the frame of the cover stretched so far up and down that its top and bottom are outside the page -
only the two side rails with the ornaments of the cover frame are seen, close to the edges of the page; no background, no smoke.
usage: python make_haskama_frame.py [silver]      (needs the masks: DIVIDER_CACHE pickle of make_divider, default out/dvtest/cache.pkl; made if it does not exist)"""
import os, sys, pickle
import numpy as np
from PIL import Image
import make_cover as mc
import make_divider as md

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'assets', 'haskamot')
CACHE = os.environ.get('DIVIDER_CACHE') or os.path.join(HERE, 'out', 'dvtest', 'cache.pkl')

SCALE = 0.62                        # size of the frame relative to the cover (the same as the dividers)
EDGE_MM = 3.2                       # outer edge of a rail to the edge of the page
PAGE = (176.0, 250.0)
PXMM = 16                           # pixels per mm of the output (2816 x 4000)
GRADE = dict(gamma=0.66, contrast=0.94, bright=0.11, sheen=0.07, waves=1.5, phase=0.12)       # lighter than the dividers (soft palette: gamma .80, bright .04)
ORN = dict(anchor=60.0, gap=-2.0)    # mm: the chain of the ornaments starts here and runs both ways


def load():
    if os.path.exists(CACHE):
        clean, a, elem, frame, swash = pickle.load(open(CACHE, 'rb'))
    else:
        src = Image.open(mc.SRC).convert('RGB')
        clean, a, elem = mc.frame_only(src)
        frame, swash = mc.gold_masks(src)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        pickle.dump((clean.astype(np.float32), a.astype(np.float32), elem, frame.astype(np.float32), swash.astype(np.float32)), open(CACHE, 'wb'))
    return a, np.clip(frame, 0, 1).astype(np.float32)


def build(name='silver', grade=GRADE):
    a, frame = load()
    C = md.CORNER
    Wb = 2 * C + 30                                         # a narrow frame: its two rails are the two rails of the page (the empty middle is cut out)
    top_off = 30.0                                          # mm of frame above the page: the corner blocks (about 26 mm) stay outside
    Hmm = PAGE[1] + 2 * top_off
    Hb = int(round(Hmm * 8 / SCALE))
    u = lambda mm_: (mm_ + top_off) * 8 / SCALE             # page mm -> frame units
    sc, cu = 300 * SCALE / 8, 105 * SCALE / 8
    cycle = [('scroll', False, sc), ('curl', False, cu), ('scroll', True, sc), ('curl', True, cu)]
    pieces, y, i = [], ORN['anchor'], 0
    while y < PAGE[1] + top_off:
        kind, flip, h = cycle[i % 4]
        pieces.append((kind, u(y), flip)); y += h + ORN['gap']; i += 1
    y, i = ORN['anchor'], -1
    while y > -top_off:
        kind, flip, h = cycle[i % 4]
        y -= h + ORN['gap']; pieces.append((kind, u(y), flip)); i -= 1
    lum, al = md.assemble_metal(a, frame, Wb, Hb, pieces, match=True)
    rgb = md.silver(None, lum, md.SILVER_RAMP, grade, True)
    # rails: left (units 0 .. R) and right (Wb - R .. Wb), 2 pixels per unit
    R = 150
    k = SCALE / 8 * PXMM                                    # output px per unit of the frame
    outw, outh = int(PAGE[0] * PXMM), int(PAGE[1] * PXMM)
    canvas = np.zeros((outh, outw, 4), np.float32)
    ry0 = -top_off * PXMM
    for side in ('L', 'R'):
        x0u, x1u = (0, R) if side == 'L' else (Wb - R, Wb)
        sub_rgb = rgb[:, 2 * x0u:2 * x1u]
        sub_al = al[:, 2 * x0u:2 * x1u]
        w_out, h_out = int(round(R * k)), int(round(Hb * k))
        im_rgb = np.asarray(Image.fromarray((np.clip(sub_rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').resize((w_out, h_out), Image.LANCZOS)).astype(np.float32) / 255
        im_al = np.asarray(Image.fromarray((np.clip(sub_al, 0, 1) * 255 + 0.5).astype(np.uint8), 'L').resize((w_out, h_out), Image.LANCZOS)).astype(np.float32) / 255
        px = int(round(EDGE_MM * PXMM)) if side == 'L' else outw - int(round(EDGE_MM * PXMM)) - w_out
        py = int(round(ry0))
        ys0, ys1 = max(0, py), min(outh, py + h_out)
        canvas[ys0:ys1, px:px + w_out, :3] = im_rgb[ys0 - py:ys1 - py]
        canvas[ys0:ys1, px:px + w_out, 3] = im_al[ys0 - py:ys1 - py]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f'frame-{name}.png')
    Image.fromarray((np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(path, optimize=True)
    return path


if __name__ == '__main__':
    for n in (sys.argv[1:] or ['silver']):
        print('haskama frame:', build(n))
