#!/usr/bin/env python3
"""The ornaments of the booklet in the antique silver style of the cover and the dividers.

The black masters (assets/ornaments/_black) are the silhouettes; each one is turned into embossed silver - a soft bevel lit from the top left, a dark rim, a slow
sheen like the frame of the cover - with exactly the same size and alpha, so nothing in the layout moves (PDF and Word use them as they use the grey ones).

usage: python antique_ornaments.py [dst_dir]      (default assets/ornaments_antique; tint_ornaments.py writes the plain grey ones)"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'ornaments', '_black')

# luminance -> silver (the same steel / silver ramp as the frame of the dividers, a little darker so that it holds on white paper)
RAMP = [(0.00, (16, 16, 18)), (0.20, (58, 59, 63)), (0.40, (104, 106, 111)), (0.60, (152, 154, 159)),
        (0.78, (196, 198, 203)), (0.92, (228, 230, 234)), (1.00, (248, 249, 251))]
LIGHT = (-0.7, -0.7)            # direction of the light (towards the light source): top left
BASE = 0.55                     # mean luminance of the metal
BEVEL = 0.40                    # strength of the bevel
SHEEN = 0.10                    # slow bands of light and shade over the metal
RIM = 0.60                      # strength of the dark rim


def ramp(lum):
    xs = [x for x, _ in RAMP]
    return np.stack([np.interp(lum, xs, [c[k] / 255.0 for _, c in RAMP]) for k in range(3)], axis=-1)


def antique(im, bevel=BEVEL, sheen=SHEEN, rim=RIM, scale=1.0):
    """im: black RGBA silhouette -> silver RGBA (same size, same alpha).  scale > 1 makes the bevel wider."""
    a = np.asarray(im.convert('RGBA'))[..., 3].astype(np.float32) / 255.0
    solid = a > 0.5
    dt = ndimage.distance_transform_edt(solid)
    t = float(np.percentile(dt[solid], 80)) if solid.any() else 2.0                      # typical half thickness of a stroke, px
    h = ndimage.gaussian_filter(a, max(1.5, 0.45 * t * scale))                            # height of the metal
    gy, gx = np.gradient(h)
    gmax = float(np.percentile(np.hypot(gx, gy)[solid], 99)) + 1e-6
    shade = np.clip(-(gx * LIGHT[0] + gy * LIGHT[1]) / gmax * -1.0, -1.2, 1.2)             # > 0 where the slope faces the light
    lum = BASE + bevel * shade + 0.10 * (h - 0.5)
    H, W = a.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wave = 0.5 + 0.5 * np.cos(2 * np.pi * ((xx / W * 0.62 + yy / H * 0.38) * 1.5 + 0.12))
    lum = lum * (1 - sheen + 2 * sheen * wave)
    r = max(2, int(round(0.22 * t)))
    edge = solid & ~ndimage.binary_erosion(solid, iterations=r)                             # a thin dark rim round every stroke
    edge = ndimage.gaussian_filter(edge.astype(np.float32), 0.8)
    lum = lum * (1 - rim * edge) + 0.12 * rim * edge
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = ramp(np.clip(lum, 0, 1))
    out[..., 3] = a
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')


def main(dst=None, **kw):
    dst = dst or os.path.join(HERE, 'assets', 'ornaments_antique')
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.png'):
            antique(Image.open(os.path.join(SRC, f)), **kw).save(os.path.join(dst, f), optimize=True)
            n += 1
    print('antique silver', n, 'ornaments ->', dst)
    return dst


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
