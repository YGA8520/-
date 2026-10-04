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
    # darker brown + a brighter, warmer gold (olive / grey casts of the old gilding pulled towards one golden hue, shadows and highlights kept)
    'brown':    dict(t1=26, s1=2.30, v1=0.52, name='חום כהה וזהב בוהק',
                     gold=dict(gamma=1.06, contrast=1.04, bright=0.0, sheen=0.17, waves=1.5, phase=0.12)),
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


# gold ramp (luminance -> colour): dark bronze .. rich gold .. bright highlight.  Applied to the whole gilded frame and to the swash,
# so no hue of the old artwork (greens, reds, olive) can stain the gold
GOLD_RAMP = [(0.00, (22, 12, 4)), (0.20, (68, 42, 10)), (0.40, (122, 82, 18)), (0.60, (168, 122, 32)),
             (0.78, (204, 158, 54)), (0.92, (230, 194, 98)), (1.00, (244, 222, 148))]
RING_RECT = ((79, 56, 1329, 1947), (140, 112, 1266, 1876))        # outer / inner rectangle of the frame band, in the 1408 x 2000 artwork
RING_CIRCLES = ((711.0, 749.0, 329.0), (711.0, 749.0, 342.0))      # the two thin rings of the title medallion
SWASH_BOX = (285, 560, 640, 800)                                  # the left swash (curl) next to the title


def gold_ramp(lum):
    xs = [x for x, _ in GOLD_RAMP]
    out = np.zeros(lum.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(lum, xs, [col[c] / 255.0 for _, col in GOLD_RAMP])
    return out


def gold_masks(img):
    """soft masks on the original-size artwork: `frame` = the whole gilded frame (band + ornaments), `swash` = the left swash of the title"""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    H, W = h.shape
    yy, xx = np.mgrid[0:H, 0:W]
    (ox0, oy0, ox1, oy1), (ix0, iy0, ix1, iy1) = RING_RECT
    ring = (xx >= ox0) & (xx <= ox1) & (yy >= oy0) & (yy <= oy1) & ~((xx >= ix0) & (xx <= ix1) & (yy >= iy0) & (yy <= iy1))
    # ornaments reaching into the glow: gold-coloured pixels near the frame, closed so that pearls / shadows inside them are included
    near = (xx > ox0 - 4) & (xx < ox1 + 4) & (yy > oy0 - 4) & (yy < oy1 + 4)
    core = (h >= 25) & (h <= 68) & (s > 0.26) & (v > 0.22) & near
    m = Image.fromarray((core * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.MinFilter(9))
    orn = np.asarray(m) > 127
    frame = (ring | orn).astype(np.uint8) * 255
    frame = np.asarray(Image.fromarray(frame).filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32) / 255.0
    # the swash: everything dark / coloured inside its box, except the thin rings and anything right of the title rule
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    x0, y0, x1, y1 = SWASH_BOX
    dark = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1) & (lum < 0.93)
    box = dark.copy()
    for cx, cy, r in RING_CIRCLES:
        box &= np.abs(np.hypot(xx - cx, yy - cy) - r) > 2.6
    from scipy import ndimage
    box |= ndimage.binary_opening(dark, structure=np.ones((7, 7)))      # thick strokes keep the pixels where a thin ring crosses them                                      # drop dust specks, bridge the gaps where the thin rings cross the strokes
    lab, n = ndimage.label(box, structure=np.ones((3, 3)))
    sizes = ndimage.sum(box, lab, range(1, n + 1))
    box = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz >= 150])
    sw = Image.fromarray((box * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    return frame, np.asarray(sw).astype(np.float32) / 255.0


def recolor(img, p, masks):
    """frame + swash: pure gold from the luminance of the artwork; everything else a single-hue brown tone (t1); red corner panels inside
    the frame band are part of the frame, hence gold as well"""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    frame, swash = [np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC)).astype(np.float32) / 255.0 for m in masks]
    g = p['gold']
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lg = np.clip(0.5 + (np.power(np.clip(lum, 0, 1), g['gamma']) - 0.5) * g['contrast'] + g['bright'], 0, 1)
    if g.get('sheen'):          # slow diagonal waves of light and shade over the gilding (metal, not a flat colour)
        Hh, Ww = lg.shape
        yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
        tt = (xx / Ww * 0.62 + yy / Hh * 0.38) * g.get('waves', 1.5) + g.get('phase', 0.12)
        lg = np.clip(lg * (1 - g['sheen'] + 2 * g['sheen'] * (0.5 + 0.5 * np.cos(2 * np.pi * tt))), 0, 1)
    rgb_gold = gold_ramp(lg)
    tone = hsv_to_rgb(np.full_like(h, p['t1']), np.clip(s * p['s1'], 0, 1), np.clip(v * (1 + (p['v1'] - 1) * np.clip(s * 3.0, 0, 1)), 0, 1))     # white stays white
    w = np.clip(np.maximum(frame, swash), 0, 1)[..., None]
    out = w * rgb_gold + (1 - w) * tone
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def recolor_hue(img, p, masks):
    """gold frame keeps its colour; red corners -> t2; everything else (green / teal background, glow, speckles) becomes a single-hue t1 tone.
    The three versions are mixed in RGB (mixing hues would give magenta / green fringes)."""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    gold, red = [np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC)).astype(np.float32) / 255.0 for m in masks]
    red = red * (1 - gold * 0.85)
    gold = gold * (1 - red)
    rest = np.clip(1 - gold - red, 0, 1)
    tone = lambda t, sf, vf: hsv_to_rgb(np.full_like(h, t), np.clip(s * sf, 0, 1), np.clip(v * (1 + (vf - 1) * np.clip(s * 3.0, 0, 1)), 0, 1))     # white stays white
    g = p.get('gold')
    if g:                       # brighter, more golden gilding
        gh = np.where((h > 14) & (h < 80), g['hue'] + (np.clip(h, 20, 72) - 46) * g['spread'], h)
        gs = np.clip(s * g['sat'] + g['sat_add'] * np.clip(s * 4, 0, 1), 0, 1)
        gv = np.clip(0.5 + (np.power(v, g['gamma']) - 0.5) * g['contrast'] + g['bright'], 0, 1)
        rgb_gold = hsv_to_rgb(gh, gs, gv)
    else:
        rgb_gold = rgb
    if g:                       # reddish speckles inside the gilded area become the corner tone instead of staying crimson
        rs = np.maximum(smooth(h, 318, 338), 1 - smooth(h, 12, 22)) * smooth(s, 0.28, 0.5)
        rgb_gold = rgb_gold * (1 - rs[..., None]) + tone(p['t2'], p['s2'], p['v2']) * rs[..., None]
    out = gold[..., None] * rgb_gold + red[..., None] * tone(p['t2'], p['s2'], p['v2']) + rest[..., None] * tone(p['t1'], p['s1'], p['v1'])
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def build(palette='navy', out=None, scale=2):
    img = Image.open(SRC).convert('RGB')
    p = PALETTES[palette]
    masks = (gold_masks(img) if p.get('gold') else frame_masks(img)) if p else None
    img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))
    if p:
        img = (recolor if p.get('gold') else recolor_hue)(img, p, masks)
    out = out or os.path.join(HERE, 'assets', 'cover', 'cover-bg.jpg')
    img.save(out, quality=92, subsampling=0, optimize=True)
    return out


if __name__ == '__main__':
    import json
    pal = sys.argv[1] if len(sys.argv) > 1 else (json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8')).get('cover') or {}).get('palette', 'navy')
    print('cover background:', build(pal, sys.argv[2] if len(sys.argv) > 2 else None), pal)
