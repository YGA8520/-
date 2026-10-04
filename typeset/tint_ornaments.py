#!/usr/bin/env python3
"""All ornaments of the booklet are greyish with a very slight transparency.
Black masters live in assets/ornaments/_black ; this writes the tinted versions next to them (used by everything else).
Change GREY / OPACITY to restyle every ornament at once."""
import os
import numpy as np
from PIL import Image

GREY = (118, 118, 118)
OPACITY = 0.90

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'ornaments', '_black')
DST = os.path.join(HERE, 'assets', 'ornaments')


def tint(im, grey=GREY, opacity=OPACITY):
    a = np.array(im.convert('RGBA'))
    out = np.zeros_like(a)
    out[..., 0], out[..., 1], out[..., 2] = grey
    out[..., 3] = np.clip(a[..., 3].astype(float) * opacity, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def main():
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.png'):
            tint(Image.open(os.path.join(SRC, f))).save(os.path.join(DST, f), optimize=True)
    print('tinted', len([f for f in os.listdir(SRC) if f.endswith('.png')]), 'ornaments', GREY, OPACITY)


if __name__ == '__main__':
    main()
