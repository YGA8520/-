#!/usr/bin/env python3
"""Artwork of the internal title pages (siman dividers), written to assets/cover/divider-bg.jpg  (usage: python make_divider.py [out.jpg]).

Made from the client's empty cover (assets/cover/empty-cover.webp) but in black / white / grey / silver, as it sits inside the book:
  - page background: the cloud of the cover (frame and medallion taken out) stretched over the whole page, in grey - the brown smoke becomes dark grey smoke
  - the title medallion (rings, rules, flourishes, swash) shrunk and placed on the left of the page (silver swash, black ink)
  - below it the frame of the cover, shrunk by the same factor and made silver, with the cloud of the cover inside it; the siman is set in it (live text, engine.js)
The layout (millimetres on the 176 x 250 page) is read from config.json -> divider; engine.js places the live text with the same numbers."""
import os, sys, json
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import make_cover as mc

HERE = mc.HERE
PX = 2                                  # canvas pixels per artwork unit (the artwork is 1408 x 2000 = 176 x 250 mm, 8 units per mm)
PAGE_U = (1408, 2000)
FRAME_OUTER = (79, 56, 1329, 1947)      # outer edge of the frame (x0, y0, x1, y1) in artwork units
FRAME_INNER = (140, 112, 1266, 1876)
RING_C = (711.0, 749.0)                 # centre of the title medallion
FLEURON_TOP = (630, 538, 792, 580)      # the small flourishes of the medallion, above and below the title
FLEURON_BOTTOM = (630, 948, 792, 988)

SILVER_RAMP = [(0.00, (20, 20, 22)), (0.18, (62, 63, 67)), (0.38, (118, 120, 125)), (0.58, (170, 172, 177)),
               (0.78, (214, 216, 220)), (0.92, (242, 244, 247)), (1.00, (255, 255, 255))]            # the frame: dark steel .. bright silver
SWASH_SILVER_RAMP = [(0.00, (14, 14, 16)), (0.18, (52, 53, 57)), (0.38, (104, 106, 111)), (0.58, (166, 168, 173)),
                     (0.78, (222, 224, 228)), (0.92, (248, 249, 251)), (1.00, (255, 255, 255))]       # the swash: brilliant silver running into dark steel
FRAME_GRADE = dict(gamma=0.80, contrast=1.05, bright=0.06, sheen=0.10, waves=1.5, phase=0.12)         # grading of the frame: lighter than the gold of the cover, silver
SWASH = dict(gamma=0.90, contrast=1.10, bright=0.02)


def lum_of(a):
    return a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)


def fill_holes(a, hole, sigmas=(4, 8, 16, 32, 64)):
    """smooth fill of `hole` from the pixels around it (normalised convolution, small scales first)"""
    valid = (~hole).astype(np.float32)
    out = a.copy()
    todo = hole.copy()
    for s in sigmas:
        w = ndimage.gaussian_filter(valid, s)
        num = np.stack([ndimage.gaussian_filter(a[..., c] * valid, s) for c in range(3)], axis=-1)
        ok = todo & (w > 0.12)
        out[ok] = (num / np.maximum(w, 1e-4)[..., None])[ok]
        todo &= ~ok
    return out


def grey_cloud(a):
    """the cloud of the cover in grey: white stays white, the (coloured) smoke becomes dark grey like the brown palette makes it dark brown"""
    h, s, v = mc.rgb_to_hsv(a)
    g = v * (1 + (0.50 - 1) * np.clip(s * 3.0, 0, 1))
    return np.stack([g, g, g], axis=-1)


def silver(img_rgb, lum, ramp, gp, sheen=False):
    lg = np.clip(0.5 + (np.power(np.clip(lum, 0, 1), gp['gamma']) - 0.5) * gp['contrast'] + gp['bright'], 0, 1)
    if sheen:
        H, W = lg.shape
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        tt = (xx / W * 0.62 + yy / H * 0.38) * gp.get('waves', 1.5) + gp.get('phase', 0.12)
        lg = np.clip(lg * (1 - gp['sheen'] + 2 * gp['sheen'] * (0.5 + 0.5 * np.cos(2 * np.pi * tt))), 0, 1)
    return mc.gold_ramp(lg, ramp)


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def build(out=None, layout=None):
    cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8'))
    L = layout or cfg['divider']
    src = Image.open(mc.SRC).convert('RGB')
    clean, a, elem = mc.frame_only(src)                                   # the cover without the medallion
    frame, swash = mc.gold_masks(src)                                     # soft masks: the gilded frame, the swash of the medallion
    frame = np.clip(frame, 0, 1).astype(np.float32)
    swash = np.clip(swash, 0, 1).astype(np.float32)
    W, H = PAGE_U[0] * PX, PAGE_U[1] * PX

    # ---- page background: the cloud inside the frame, ornaments filled in, stretched over the page
    hole = ndimage.binary_dilation(frame > 0.01, structure=np.ones((3, 3)), iterations=5)
    cloud = fill_holes(clean, hole)
    cloud = np.stack([ndimage.gaussian_filter(cloud[..., c], 1.6) for c in range(3)], axis=-1)       # the cloud of the cover carries block noise of its jpeg: smooth it before it is stretched
    ix0, iy0, ix1, iy1 = FRAME_INNER
    padx, pady = 60, 40                                                   # keeps the curls of the side ornaments out of the page
    crop = cloud[iy0 + pady:iy1 - pady, ix0 + padx:ix1 - padx]
    bg = Image.fromarray((np.clip(grey_cloud(crop), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
    page = np.asarray(bg).astype(np.float32) / 255.0

    # ---- frame: grey cloud + silver gilding, cut out of the cover at its outer edge, shrunk and placed
    fs = L['frame']['scale']
    x0, y0, x1, y1 = FRAME_OUTER
    sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
    panel = grey_cloud(np.stack([ndimage.gaussian_filter(clean[..., c], 1.0)[sl] for c in range(3)], axis=-1))
    fa = frame[sl][..., None]
    fr = silver(None, lum_of(a[sl]), SILVER_RAMP, FRAME_GRADE, True)
    panel = panel * (1 - fa) + fr * fa
    pw, ph = int(round((x1 - x0 + 1) * fs * PX)), int(round((y1 - y0 + 1) * fs * PX))
    panel_img = to_img(panel).resize((pw, ph), Image.LANCZOS)
    fx = int(round((L['frame']['cx'] * 8 - (x1 - x0 + 1) * fs / 2) * PX))
    fy = int(round((L['frame']['cy'] * 8 - (y1 - y0 + 1) * fs / 2) * PX))
    # ring of the soft shadow under the frame: a little darkening so that the frame stands on the page
    pg_img = to_img(page)
    shadow = Image.new('L', (W, H), 0)
    shadow.paste(255, (fx + 4, fy + 6, fx + pw + 4, fy + ph + 6))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    sh = np.asarray(shadow).astype(np.float32)[..., None] / 255.0
    page = page * (1 - 0.30 * sh)
    pg_img = to_img(page)
    pg_img.paste(panel_img, (fx, fy))

    # ---- medallion: black ink (multiplied onto the page) + silver swash, shrunk and placed
    ms = L['medal']['scale']
    bx0, by0, bx1, by1 = mc.MEDALLION_BOX
    ink = np.where(elem[..., None], np.clip(a / np.maximum(clean, 1e-3), 0, 1), 1.0)[by0:by1, bx0:bx1]
    ink_l = np.clip(lum_of(ink), 0, 1) ** 1.25                              # a little heavier: the rings are hair lines and get thinner when shrunk
    sw = swash[by0:by1, bx0:bx1]
    sw_rgb = silver(None, lum_of(a[by0:by1, bx0:bx1]), SWASH_SILVER_RAMP, SWASH)
    bw, bh = int(round((bx1 - bx0) * ms * PX)), int(round((by1 - by0) * ms * PX))
    ink_s = np.asarray(Image.fromarray((ink_l * 255).astype(np.uint8)).resize((bw, bh), Image.LANCZOS)).astype(np.float32) / 255.0
    sw_s = np.asarray(Image.fromarray((sw * 255).astype(np.uint8)).resize((bw, bh), Image.LANCZOS)).astype(np.float32) / 255.0
    rgb_s = np.asarray(to_img(sw_rgb).resize((bw, bh), Image.LANCZOS)).astype(np.float32) / 255.0
    mx = int(round((L['medal']['cx'] * 8 + (bx0 - RING_C[0]) * ms) * PX))
    my = int(round((L['medal']['cy'] * 8 + (by0 - RING_C[1]) * ms) * PX))
    pg = np.asarray(pg_img).astype(np.float32) / 255.0
    reg = pg[my:my + bh, mx:mx + bw]
    reg = reg * ink_s[..., None]
    reg = reg * (1 - sw_s[..., None]) + rgb_s * sw_s[..., None]
    pg[my:my + bh, mx:mx + bw] = reg
    # the two small flourishes of the medallion (above / below the title), set again above and below the siman inside the frame
    fl = L.get('fleurons')
    if fl:
        for key, (ux0, uy0, ux1, uy1), flip in (('top', FLEURON_TOP, False), ('bottom', FLEURON_BOTTOM, False)):
            piece = np.clip(lum_of(np.where(elem[..., None], np.clip(a / np.maximum(clean, 1e-3), 0, 1), 1.0)[uy0:uy1, ux0:ux1]), 0, 1) ** 1.25
            k = fl['scale']
            pw2, ph2 = int(round((ux1 - ux0) * k * PX)), int(round((uy1 - uy0) * k * PX))
            ps = np.asarray(Image.fromarray((piece * 255).astype(np.uint8)).resize((pw2, ph2), Image.LANCZOS)).astype(np.float32) / 255.0
            cxp = L['frame']['cx'] * 8 + 0.0
            cyp = L['frame']['cy'] * 8 + fl[key]
            qx = int(round((cxp - (ux1 - ux0) * k / 2) * PX)); qy = int(round((cyp - (uy1 - uy0) * k / 2) * PX))
            pg[qy:qy + ph2, qx:qx + pw2] *= ps[..., None]
    final = to_img(pg)
    out = out or os.path.join(HERE, 'assets', 'cover', 'divider-bg.jpg')
    final.save(out, quality=92, subsampling=0, optimize=True)
    return out


if __name__ == '__main__':
    print('divider background:', build(sys.argv[1] if len(sys.argv) > 1 else None))
