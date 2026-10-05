#!/usr/bin/env python3
"""All ornaments of the booklet come from the black masters in assets/ornaments/_black ; this writes the versions that everything else uses next to them.
Default: embossed antique silver (antique_ornaments.py, the style of the cover and the dividers) + the faint title cloud.
`python tint_ornaments.py grey` writes the earlier flat grey ones instead (change GREY / OPACITY to restyle those)."""
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


def main(style='antique'):
    if style == 'antique':
        import antique_ornaments
        antique_ornaments.main(DST)
        return
    cloud = os.path.join(DST, 'title-cloud.png')
    if os.path.exists(cloud):
        os.remove(cloud)                                   # the grey set has no cloud behind the titles
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.png'):
            tint(Image.open(os.path.join(SRC, f))).save(os.path.join(DST, f), optimize=True)
    print('tinted', len([f for f in os.listdir(SRC) if f.endswith('.png')]), 'ornaments', GREY, OPACITY)


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else 'antique')
