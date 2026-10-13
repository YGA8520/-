#!/usr/bin/env python3
"""Background of a haskama page (written to assets/haskamot/bg-<name>.jpg): the frame of the cover of the booklet (no medallion), the smoke of the cover along its inner edge,
and a light, quiet interior for the facsimile and the typed text.
usage: python make_haskama_bg.py [name ...]      name = silver (black / white / grey, default) | soft (the colours of the covers)"""
import os, sys
import numpy as np
from PIL import Image
import make_cover as mc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'assets', 'haskamot')
INNER = (140, 112, 1266, 1876)          # inner edge of the frame, artwork units (8 per mm)


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def build(name='silver', paper=0.975, keep=1.0):
    tmp = os.path.join(OUT, f'_raw-{name}.jpg')
    mc.build(name, tmp, no_medallion=True)
    img = np.asarray(Image.open(tmp).convert('RGB')).astype(np.float32) / 255.0
    os.remove(tmp)
    H, W = img.shape[:2]
    s = W / 1408.0
    x0, y0, x1, y1 = [v * s for v in INNER]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.minimum(np.minimum(xx - x0, x1 - xx), np.minimum(yy - y0, y1 - yy))          # distance to the inner edge of the frame (negative: on the frame)
    w = smooth((d - 40 * s) / (170 * s))                                                  # 0 on the frame and along its inner edge, 1 in the interior
    tint = np.array([1.0, 1.0, 1.0], np.float32) * paper
    if name != 'silver':
        tint = np.array([1.0, 0.985, 0.955], np.float32) * paper                           # a touch of warm paper in the colour version
    out = img * (1 - w[..., None] * keep) + tint[None, None, :] * (w[..., None] * keep)
    # a very faint remnant of the cloud inside, so that the paper is not flat
    out = out - (1 - img) * 0.10 * w[..., None]
    path = os.path.join(OUT, f'bg-{name}.jpg')
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(path, quality=93, subsampling=0, optimize=True)
    return path


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in (sys.argv[1:] or ['silver', 'soft']):
        print('haskama background:', build(n))
