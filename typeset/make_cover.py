#!/usr/bin/env python3
"""Cover background: the client's empty cover (assets/cover/empty-cover.webp) re-coloured to one of the palettes below,
upscaled for print and written to assets/cover/cover-bg.jpg.   usage: python make_cover.py [palette] [out.jpg]"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'cover', 'empty-cover.webp')

# green / teal background -> t1 ; red corners -> t2 (hue in degrees); s / v = saturation / brightness factors; the gold frame keeps its colour
PALETTES = {
    'original': None,
    'navy':     dict(t1=222, s1=1.75, v1=0.78, t2=226, s2=1.00, v2=0.85, name='כחול מלכותי וזהב'),
    'burgundy': dict(t1=350, s1=1.70, v1=0.80, t2=356, s2=1.00, v2=0.80, name='בורדו וזהב'),
    'purple':   dict(t1=272, s1=1.70, v1=0.80, t2=290, s2=1.00, v2=0.80, name='סגול וזהב'),
    'sepia':    dict(t1=30,  s1=1.25, v1=0.86, t2=18,  s2=0.90, v2=0.75, name='חום וזהב'),
}


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    rc = nz & (mx == r); gc = nz & (mx == g) & ~rc; bc = nz & ~rc & ~gc
    h[rc] = ((g - b)[rc] / d[rc]) % 6
    h[gc] = (b - r)[gc] / d[gc] + 2
    h[bc] = (r - g)[bc] / d[bc] + 4
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    return h * 60.0, s, mx


def hsv_to_rgb(h, s, v):
    h = (h % 360) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,), dtype=np.float32)
    for k, (a, b, c) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        out[m, 0], out[m, 1], out[m, 2] = a[m], b[m], c[m]
    return out


def frame_masks(img):
    """masks (0..1, soft) found on the original-size artwork: `gold` = the gilded frame with its ornaments (kept as it is), `red` = the red corners"""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    H, W = h.shape
    yy, xx = np.mgrid[0:H, 0:W]
    inside = (xx > 70) & (xx < W - 70) & (yy > 45) & (yy < H - 45)              # inside the outer edge of the frame
    core = ((h >= 25) & (h <= 68) & (s > 0.26) & (v > 0.22) & inside)
    rail = (((xx >= 78) & (xx <= 104)) | ((xx >= W - 105) & (xx <= W - 78)) | ((yy >= 54) & (yy <= 80)) | ((yy >= H - 80) & (yy <= H - 54))) \
        & (xx >= 78) & (xx <= W - 78) & (yy >= 54) & (yy <= H - 54)                   # the plain outer rail of the frame (its highlights are nearly grey)
    core = core | rail
    m = Image.fromarray((core * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(9))      # close gaps (highlights, shadows inside the gilding)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    gold = np.asarray(m).astype(np.float32) / 255.0
    red = ((h > 300) | (h < 25)) & (s > 0.30) & (v > 0.10) & inside
    r = Image.fromarray((red * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.8))
    return gold, np.asarray(r).astype(np.float32) / 255.0


def recolor(img, p, masks):
    """gold frame keeps its colour; red corners -> t2; everything else (green / teal background, glow, speckles) becomes a single-hue t1 tone.
    The three versions are mixed in RGB (mixing hues would give magenta / green fringes)."""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    gold, red = [np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC)).astype(np.float32) / 255.0 for m in masks]
    red = red * (1 - gold * 0.85)
    gold = gold * (1 - red)
    rest = np.clip(1 - gold - red, 0, 1)
    tone = lambda t, sf, vf: hsv_to_rgb(np.full_like(h, t), np.clip(s * sf, 0, 1), np.clip(v * (1 + (vf - 1) * np.clip(s * 3.0, 0, 1)), 0, 1))     # white stays white
    out = gold[..., None] * rgb + red[..., None] * tone(p['t2'], p['s2'], p['v2']) + rest[..., None] * tone(p['t1'], p['s1'], p['v1'])
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def build(palette='navy', out=None, scale=2):
    img = Image.open(SRC).convert('RGB')
    p = PALETTES[palette]
    masks = frame_masks(img) if p else None
    img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))
    if p:
        img = recolor(img, p, masks)
    out = out or os.path.join(HERE, 'assets', 'cover', 'cover-bg.jpg')
    img.save(out, quality=92, subsampling=0, optimize=True)
    return out


if __name__ == '__main__':
    import json
    pal = sys.argv[1] if len(sys.argv) > 1 else (json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8')).get('cover') or {}).get('palette', 'navy')
    print('cover background:', build(pal, sys.argv[2] if len(sys.argv) > 2 else None), pal)
