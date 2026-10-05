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
                     gold=dict(gamma=0.96, contrast=1.04, bright=0.03, sheen=0.12, waves=1.5, phase=0.12),
                                      swash=dict(gamma=0.90, contrast=1.10, bright=0.02)),
    # the inner title page: the same cover in black / white / grey / silver (no colour: the frame and the swash silver, everything else grey)
    'silver':   dict(t1=0, s1=0.0, v1=0.68, name='כסף', gold=dict(gamma=0.72, contrast=1.06, bright=0.08, sheen=0.10, waves=1.5, phase=0.12),
                     swash=dict(gamma=0.90, contrast=1.10, bright=0.02), frame_ramp='SILVER_RAMP', swash_ramp='SILVER_SWASH_RAMP'),
    # the back cover: gentle colours instead of the strong brown / bright gold of the front (frame only, no medallion)
    'soft':     dict(t1=32, s1=1.15, v1=0.80, name='חול ושמפניה עדין',
                     gold=dict(gamma=0.80, contrast=0.96, bright=0.04, sheen=0.08, waves=1.5, phase=0.12),
                     swash=dict(gamma=0.90, contrast=1.0, bright=0.02), frame_ramp='SOFT_GOLD_RAMP', swash_ramp='SOFT_SWASH_RAMP'),
    'soft-blue': dict(t1=212, s1=1.0, v1=0.80, name='אפור כחלחל וכסף עדין',
                     gold=dict(gamma=0.80, contrast=0.96, bright=0.04, sheen=0.08, waves=1.5, phase=0.12),
                     swash=dict(gamma=0.90, contrast=1.0, bright=0.02), frame_ramp='SOFT_SILVER_RAMP', swash_ramp='SOFT_SILVER_RAMP'),
    'soft-sage': dict(t1=95, s1=0.9, v1=0.80, name='ירקרק עדין ושמפניה',
                     gold=dict(gamma=0.80, contrast=0.96, bright=0.04, sheen=0.08, waves=1.5, phase=0.12),
                     swash=dict(gamma=0.90, contrast=1.0, bright=0.02), frame_ramp='SOFT_GOLD_RAMP', swash_ramp='SOFT_SWASH_RAMP'),
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
GOLD_RAMP = [(0.00, (46, 28, 8)), (0.20, (100, 66, 16)), (0.40, (152, 106, 26)), (0.60, (194, 144, 44)),
             (0.78, (226, 180, 70)), (0.92, (244, 210, 112)), (1.00, (252, 236, 162))]            # the frame: rich, not heavy
SWASH_RAMP = [(0.00, (26, 14, 4)), (0.18, (84, 52, 12)), (0.38, (150, 102, 22)), (0.58, (208, 158, 40)),
              (0.78, (244, 204, 84)), (0.92, (255, 236, 150)), (1.00, (255, 250, 222))]           # the swash: brilliant gold running into dark bronze
SILVER_RAMP = [(0.00, (20, 20, 22)), (0.18, (62, 63, 67)), (0.38, (118, 120, 125)), (0.58, (170, 172, 177)),
               (0.78, (214, 216, 220)), (0.92, (242, 244, 247)), (1.00, (255, 255, 255))]            # silver frame: dark steel .. bright silver
SILVER_SWASH_RAMP = [(0.00, (14, 14, 16)), (0.18, (52, 53, 57)), (0.38, (104, 106, 111)), (0.58, (166, 168, 173)),
                     (0.78, (222, 224, 228)), (0.92, (248, 249, 251)), (1.00, (255, 255, 255))]       # silver swash: brilliant silver running into dark steel
SOFT_GOLD_RAMP = [(0.00, (74, 62, 48)), (0.20, (122, 104, 80)), (0.40, (163, 142, 104)), (0.60, (197, 176, 136)),
                  (0.78, (221, 204, 168)), (0.92, (240, 228, 200)), (1.00, (251, 246, 230))]            # the back cover: a muted champagne gilding
SOFT_SWASH_RAMP = SOFT_GOLD_RAMP
SOFT_SILVER_RAMP = [(0.00, (58, 62, 70)), (0.20, (96, 102, 112)), (0.40, (138, 146, 158)), (0.60, (176, 184, 195)),
                    (0.78, (206, 213, 222)), (0.92, (233, 237, 243)), (1.00, (250, 251, 253))]          # a cool, gentle silver
RING_RECT = ((79, 56, 1329, 1947), (140, 112, 1266, 1876))        # outer / inner rectangle of the frame band, in the 1408 x 2000 artwork
RING_CIRCLES = ((711.0, 749.0, 329.0), (711.0, 749.0, 342.0))      # the two thin rings of the title medallion
SWASH_BOX = (285, 560, 640, 800)                                  # the left swash (curl) next to the title


def gold_ramp(lum, ramp=None):
    ramp = ramp or GOLD_RAMP
    xs = [x for x, _ in ramp]
    out = np.zeros(lum.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(lum, xs, [col[c] / 255.0 for _, col in ramp])
    return out


def gold_masks(img, dy=0):
    """soft masks on the original-size artwork: `frame` = the whole gilded frame (band + ornaments), `swash` = the left swash of the title"""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    h, s, v = rgb_to_hsv(rgb)
    H, W = h.shape
    yy, xx = np.mgrid[0:H, 0:W]
    (ox0, oy0, ox1, oy1), (ix0, iy0, ix1, iy1) = RING_RECT
    ring = (xx >= ox0) & (xx <= ox1) & (yy >= oy0) & (yy <= oy1) & ~((xx >= ix0) & (xx <= ix1) & (yy >= iy0) & (yy <= iy1))
    # ornaments reaching into the glow: every ornament is drawn with a continuous dark outline, so the glow is exactly the area that can be reached
    # from the middle of the page without crossing a dark pixel; what is not reachable close to the frame is ornament (silver rims and pearls included)
    from scipy import ndimage
    lum0 = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    dark = lum0 < 0.30
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    near = (xx < ox0 + 262) | (xx > ox1 - 262) | (yy < oy0 + 262) | (yy > oy1 - 262)
    zone = (xx > ox0 - 2) & (xx < ox1 + 2) & (yy > oy0 - 2) & (yy < oy1 + 2) & near
    zone &= ~((xx >= 925) & (xx <= 1170) & (yy >= 755 + dy) & (yy <= 860 + dy))      # the black ink flourish right of the title is not part of the frame
    zone &= ~((xx >= 1050) & (xx <= 1140) & (yy >= 590 + dy) & (yy <= 620 + dy))      # nor are the right ends of the two rules above the title

    def unreached(iters):       # what cannot be reached from the middle of the page without crossing a (widened) dark outline
        lab, _ = ndimage.label(~ndimage.binary_dilation(dark, structure=np.ones((3, 3)), iterations=iters), structure=cross)
        return (lab != lab[H // 2, W // 2]) & zone & ~ring
    sharp = unreached(1)        # exact silhouettes, but light blades without a closed outline leak (stay brown inside)
    safe = unreached(3)         # no leaks, but 3 px too fat
    # exact silhouette + what the fat version adds inside the ornament (leaked light blades): everything that is not glow-coloured (teal / pale neutral)
    glowish = ((h >= 80) & (h <= 240) & (s > 0.06)) | ((s < 0.14) & (v > 0.45))
    orn = sharp | (safe & ~sharp & ~glowish)
    orn = ndimage.binary_closing(orn, structure=np.ones((3, 3))) & zone & ~ring
    frame = (ring | orn).astype(np.uint8) * 255
    frame = np.asarray(Image.fromarray(frame).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.0
    # the swash: everything dark / coloured inside its box, except the thin rings and anything right of the title rule
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    x0, y0, x1, y1 = SWASH_BOX
    y0, y1 = y0 + dy, y1 + dy
    dark = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1) & (lum < 0.93)
    box = dark.copy()
    for cx, cy, r in RING_CIRCLES:
        box &= np.abs(np.hypot(xx - cx, yy - (cy + dy)) - r) > 2.6
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
    lum = np.clip(rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32), 0, 1)

    def graded(gp, sheen):
        lg = np.clip(0.5 + (np.power(lum, gp['gamma']) - 0.5) * gp['contrast'] + gp['bright'], 0, 1)
        if sheen:               # slow diagonal waves of light and shade over the gilding (metal, not a flat colour)
            Hh, Ww = lg.shape
            yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
            tt = (xx / Ww * 0.62 + yy / Hh * 0.38) * gp.get('waves', 1.5) + gp.get('phase', 0.12)
            lg = np.clip(lg * (1 - gp['sheen'] + 2 * gp['sheen'] * (0.5 + 0.5 * np.cos(2 * np.pi * tt))), 0, 1)
        return lg
    frame_rgb = gold_ramp(graded(g, True), globals()[p['frame_ramp']] if p.get('frame_ramp') else None)
    swash_rgb = gold_ramp(graded(p['swash'], False), globals()[p['swash_ramp']] if p.get('swash_ramp') else SWASH_RAMP)
    tone = hsv_to_rgb(np.full_like(h, p['t1']), np.clip(s * p['s1'], 0, 1), np.clip(v * (1 + (p['v1'] - 1) * np.clip(s * 3.0, 0, 1)), 0, 1))     # white stays white
    wf, ws = np.clip(frame, 0, 1)[..., None], np.clip(swash, 0, 1)[..., None]
    out = tone
    out = out * (1 - wf) + frame_rgb * wf
    out = out * (1 - ws) + swash_rgb * ws
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


MEDALLION_BOX = (270, 380, 1190, 1130)      # everything of the title medallion lives in this box of the empty cover


def frame_only(src):
    """the empty cover without the medallion (rings, rules, swashes, flourishes) - they are thin ink / thin metal on the cloud, filled in from the cloud around them"""
    from scipy import ndimage
    a = np.asarray(src.convert('RGB')).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    x0, y0, x1, y1 = MEDALLION_BOX
    box = np.zeros(lum.shape, dtype=bool)
    box[y0:y1, x0:x1] = True
    elem = ((lum < ndimage.gaussian_filter(lum, 10) - 0.07) | (lum < 0.6)) & box
    elem = ndimage.binary_dilation(elem, structure=np.ones((3, 3)), iterations=3)
    idx = ndimage.distance_transform_edt(elem, return_distances=False, return_indices=True)
    out = a[idx[0], idx[1]]
    for _ in range(80):
        sm = np.stack([ndimage.uniform_filter(out[..., c], size=9) for c in range(3)], axis=-1)
        out = np.where(elem[..., None], sm, a)
    return np.where(elem[..., None], out, a), a, elem


def build(palette='navy', out=None, scale=2, no_medallion=False):
    img = Image.open(SRC).convert('RGB')
    if no_medallion:                                            # the back cover: the frame and the cloud only
        clean, _, _ = frame_only(img)
        img = Image.fromarray((np.clip(clean, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
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
    cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8'))
    pal = sys.argv[1] if len(sys.argv) > 1 else (cfg.get('cover') or {}).get('palette', 'navy')
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print('cover background:', build(pal, out), pal)
    if len(sys.argv) <= 2 and cfg.get('backCover'):               # the back cover: the cover without the circle, in gentle colours, the logo of the organisation in the middle
        print('back cover background:', build(cfg['backCover'].get('palette', 'soft'), os.path.join(HERE, 'assets', 'cover', 'back-bg.jpg'), no_medallion=True))
    if len(sys.argv) <= 2 and cfg.get('innerCover'):              # the inner title page: the same cover in black / white / grey / silver
        print('inner cover background:', build('silver', os.path.join(HERE, 'assets', 'cover', 'inner-cover-bg.jpg')))
    if len(sys.argv) <= 2 and cfg.get('divider'):               # also the artwork of the internal title pages (siman dividers, grey / silver) and of the credits page
        import make_divider
        print('divider background:', make_divider.build())
        if cfg.get('credits'):
            print('credits background:', make_divider.build(kind='credits'))
        make_divider.make_assets()
