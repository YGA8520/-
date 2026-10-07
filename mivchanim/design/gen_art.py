"""Builds the raster artwork of the booklet (blue marble + cream parchment + embossed gold).

    python3 design/gen_art.py [cover|divider|back|frame|small|all]

Outputs in build/art:
  cover-bg.jpg     front cover (title is live text on top)
  divider-bg.jpg   part divider (same silhouette as the cover, shorter title panel)
  back-bg.jpg      back cover
  page-frame.jpg   cream marble page with a gold frame (inner title / credits / contents / notes)
  ring.png         gold ring + blue disc (unit seals, page numbers)
  rule.png         gold rule with a fleuron (unit heads)
  sep.png          short gold separator (credits)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.deps'))
import art  # noqa: E402
from art import CACHE, emboss, bez, GOLD  # noqa: E402
from gold import gold  # noqa: E402

PPM = 10           # px per mm for the full-page artwork (254 dpi)
W_MM, H_MM = 210, 297


# ------------------------------------------------------------------ helpers
def over(base, rgba, x_mm, y_mm, ppm=PPM):
    """alpha-composite an RGBA uint8 array on the float RGB base at (x_mm, y_mm)"""
    x, y = int(round(x_mm * ppm)), int(round(y_mm * ppm))
    h, w = rgba.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, base.shape[1]), min(y + h, base.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(float)
    a = sub[..., 3:] / 255
    base[y0:y1, x0:x1] = base[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a


def full_mask(poly_mm, ppm=PPM, ss=2, w=W_MM, h=H_MM):
    im = Image.new('L', (int(w * ppm * ss), int(h * ppm * ss)), 0)
    d = ImageDraw.Draw(im)
    d.polygon([(x * ppm * ss, y * ppm * ss) for x, y in poly_mm], fill=255)
    return np.asarray(im.resize((int(w * ppm), int(h * ppm)), Image.LANCZOS), dtype=float) / 255


def stroke_mask(poly_mm, width_mm, ppm=PPM, ss=2, closed=True, w=W_MM, h=H_MM):
    im = Image.new('L', (int(w * ppm * ss), int(h * ppm * ss)), 0)
    d = ImageDraw.Draw(im)
    pts = [(x * ppm * ss, y * ppm * ss) for x, y in poly_mm]
    if closed:
        pts.append(pts[0])
    d.line(pts, fill=255, width=max(1, int(width_mm * ppm * ss)), joint='curve')
    r = width_mm * ppm * ss / 2
    for (x, y) in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return np.asarray(im.resize((int(w * ppm), int(h * ppm)), Image.LANCZOS), dtype=float) / 255


def panel_outline(cx=105, half=41, top=-6, shoulder=118, tip=176, n=80):
    """the arched title panel: straight sides, convex lower shoulders, concave ogee to a point (mm polygon, left->right)"""
    k = (tip - shoulder) / 58.0
    L = np.vstack([
        [(cx - half, top)],
        bez((cx - half, top), (cx - half, shoulder * .6), (cx - half, shoulder * .85), (cx - half, shoulder), 20),
        bez((cx - half, shoulder), (cx - half, shoulder + 14 * k), (cx - half + 7, shoulder + 21 * k), (cx - half + 15, shoulder + 27 * k), n),
        bez((cx - half + 15, shoulder + 27 * k), (cx - half + 25, shoulder + 35 * k), (cx - 6, shoulder + 40 * k), (cx, tip), n),
    ])
    R = L[::-1].copy()
    R[:, 0] = 2 * cx - R[:, 0]
    return np.vstack([L, R])


def silhouette(cx=105, top_half=50, shoulder_y=84, half=94, bottom=286, r=9):
    """parchment outline: narrow tower at the top that flares out in concave shoulders to the full width"""
    pts = [(cx - top_half, -6), (cx - top_half, shoulder_y - 16)]
    pts += list(bez((cx - top_half, shoulder_y - 16), (cx - top_half, shoulder_y + 4), (cx - half + 16, shoulder_y - 4), (cx - half, shoulder_y + 14), 40))
    pts += [(cx - half, bottom - r)]
    pts += list(bez((cx - half, bottom - r), (cx - half, bottom), (cx - half + r, bottom), (cx - half + r * 1.6, bottom), 14))
    L = np.array(pts)
    R = L[::-1].copy()
    R[:, 0] = 2 * cx - R[:, 0]
    return np.vstack([L, R])


def round_rect(x0, y0, x1, y1, r, n=14):
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for a in np.linspace(a0, a0 + 90, n):
            pts.append((cx + r * np.cos(np.radians(a)), cy + r * np.sin(np.radians(a))))
    return np.array(pts)


def inset_poly(poly, d):
    """crude inward offset: move every vertex towards the centroid line-normal by d (works for these convex-ish shapes)"""
    p = np.asarray(poly, float)
    c = p.mean(0)
    v = p - c
    n = np.hypot(v[:, 0], v[:, 1]) + 1e-9
    return p - v / n[:, None] * d


def drop_shadow(mask, ppm=PPM, off=(1.2, 1.8), blur=1.6, strength=.55):
    sh = ndi.gaussian_filter(mask, blur * ppm)
    sh = ndi.shift(sh, (off[1] * ppm, off[0] * ppm), order=1)
    return sh * strength


def finish(base, name):
    out = np.clip(base, 0, 255).astype('uint8')
    Image.fromarray(out).save(os.path.join(CACHE, name + '.png'))
    Image.fromarray(out).save(os.path.join(CACHE, name + '.jpg'), quality=90, subsampling=0)
    return out


def put(base, name, w_mm, cx=None, x=None, y=0, **kw):
    g = gold(name, w_mm, PPM, **kw)
    wmm = g.shape[1] / PPM
    over(base, g, (cx - wmm / 2) if cx is not None else x, y)
    return g.shape[1] / PPM, g.shape[0] / PPM


def rim(base, poly, width, height=.7, shadow=.5, closed=True):
    over(base, emboss(stroke_mask(poly, width, closed=closed), PPM, height_mm=height, shadow=shadow), 0, 0)


# ------------------------------------------------------------------ the parchment scene (cover / dividers)
def parchment_scene(panel_shoulder, panel_tip, sil_shoulder, seed=3, flourish_w=128):
    W, H = int(W_MM * PPM), int(H_MM * PPM)
    base = art.blue_marble(W, H, seed=seed).astype(float)
    sil = silhouette(shoulder_y=sil_shoulder)
    pan = panel_outline(shoulder=panel_shoulder, tip=panel_tip)
    m_sil, m_pan = full_mask(sil), full_mask(pan)

    base *= (1 - drop_shadow(m_sil, strength=.6))[..., None]
    cream = art.cream_marble(W, H, seed=5).astype(float)
    inner = ndi.gaussian_filter(m_sil, 1.8 * PPM)
    cream *= (.84 + .16 * inner)[..., None]
    base = base * (1 - m_sil[..., None]) + cream * m_sil[..., None]

    panel_tex = art.blue_panel(W, H, seed=11).astype(float)
    base *= (1 - drop_shadow(m_pan, off=(.4, .9), blur=1.0, strength=.5) * (1 - m_pan))[..., None]
    base = base * (1 - m_pan[..., None]) + panel_tex * m_pan[..., None]
    inner_p = 1 - ndi.gaussian_filter(m_pan, 1.2 * PPM)
    base *= (1 - .45 * inner_p * m_pan)[..., None]

    # gold rims
    rim(base, pan, 2.0, .7, .5)
    pan_in = pan.copy()
    pan_in[:, 0] = 105 + (pan_in[:, 0] - 105) * (1 - 4.0 / 41)
    pan_in[:, 1] = np.where(pan_in[:, 1] < 0, pan_in[:, 1], pan_in[:, 1] - 3.6 * np.clip((pan_in[:, 1] - (panel_shoulder + 22)) / 36, 0, 1))
    rim(base, pan_in, .55, .3, .3)
    rim(base, sil, 2.4, .8, .55)
    sil_in = sil.copy()
    sil_in[:, 0] = 105 + (sil_in[:, 0] - 105) * (1 - 4.6 / 94)
    sil_in[:, 1] = np.where((sil_in[:, 1] > 0) & (sil_in[:, 1] < 280), sil_in[:, 1], np.where(sil_in[:, 1] >= 280, sil_in[:, 1] - 4.4, sil_in[:, 1]))
    rim(base, sil_in, .55, .3, .3)

    # corners of the parchment
    cy0 = sil_shoulder + 18.6
    put(base, 'corner.png', 36, x=13.2, y=cy0)
    put(base, 'corner.png', 36, x=210 - 13.2 - 36 - 3.2, y=cy0, flip_x=True)
    put(base, 'corner.png', 36, x=13.2, y=244, flip_y=True)
    put(base, 'corner.png', 36, x=210 - 13.2 - 36 - 3.2, y=244, flip_x=True, flip_y=True)
    # floral strips up the two sides of the tower
    strip = min(62, sil_shoulder - 20)
    put(base, 'flower-strip.png', strip, x=56.6, y=-6, rot=90)
    put(base, 'flower-strip.png', strip, x=142.6, y=-6, rot=270)
    # under the tip of the panel
    put(base, 'flourish-wide-1.png', flourish_w, cx=105, y=panel_tip - 5.5)
    return base


def build_cover():
    base = parchment_scene(118, 176, 84)
    # bottom of the parchment: little fleuron between the two lower corners
    put(base, 'fleuron-small.png', 30, cx=105, y=266.5, flip_y=True)
    return finish(base, 'cover-bg')


def build_divider():
    base = parchment_scene(86, 130, 58, seed=7, flourish_w=98)
    put(base, 'fleuron-small.png', 30, cx=105, y=266.5, flip_y=True)
    return finish(base, 'divider-bg')


# ------------------------------------------------------------------ back cover
def plaque_outline(cx=105, cy=148, half=60, top=46, bottom=250, n=70):
    """ogee-pointed plaque (pointed top and bottom, straight sides)"""
    k = 58 / 58.0
    up = []
    y_sh = top + 52
    up += list(bez((cx, top), (cx - 6, top + 25), (cx - half + 25, y_sh - 20), (cx - half + 12, y_sh - 8), n))
    up += list(bez((cx - half + 12, y_sh - 8), (cx - half + 5, y_sh - 2), (cx - half, y_sh + 4), (cx - half, y_sh + 18), 30))
    L = np.array(up)
    # mirror vertically for the bottom half
    B = L[::-1].copy()
    B[:, 1] = (top + bottom) - B[:, 1]
    left = np.vstack([L, B])                  # top tip ... down the left side ... bottom tip
    R = left[::-1].copy()
    R[:, 0] = 2 * cx - R[:, 0]
    return np.vstack([left, R])


def build_back():
    W, H = int(W_MM * PPM), int(H_MM * PPM)
    base = art.blue_marble(W, H, seed=9).astype(float)
    pl = plaque_outline()
    m = full_mask(pl)
    base *= (1 - drop_shadow(m, strength=.6))[..., None]
    cream = art.cream_marble(W, H, seed=8).astype(float)
    inner = ndi.gaussian_filter(m, 1.8 * PPM)
    cream *= (.86 + .14 * inner)[..., None]
    base = base * (1 - m[..., None]) + cream * m[..., None]
    rim(base, pl, 2.4, .8, .55)
    pl_in = inset_poly(pl, 4.4)
    rim(base, pl_in, .55, .3, .3)
    put(base, 'flourish-wide-1.png', 78, cx=105, y=84)
    put(base, 'fleuron-small.png', 28, cx=105, y=212, flip_y=True)
    # fleurons in the four corners of the page, on the blue
    put(base, 'corner.png', 26, x=10, y=10, colors=GOLD)
    put(base, 'corner.png', 26, x=210 - 10 - 26 - 3.2, y=10, flip_x=True)
    put(base, 'corner.png', 26, x=10, y=297 - 10 - 26 - 3.2, flip_y=True)
    put(base, 'corner.png', 26, x=210 - 10 - 26 - 3.2, y=297 - 10 - 26 - 3.2, flip_x=True, flip_y=True)
    return finish(base, 'back-bg')


# ------------------------------------------------------------------ cream page with frame
def build_frame(corner=28, name='page-frame'):
    W, H = int(W_MM * PPM), int(H_MM * PPM)
    base = art.cream_marble(W, H, seed=21).astype(float)
    fr = round_rect(8, 8, 202, 289, 8)
    m = full_mask(fr)
    inner = ndi.gaussian_filter(m, 2.2 * PPM)
    outside = 1 - m
    base *= (1 - .06 * outside - .05 * (1 - inner) * m)[..., None]
    rim(base, fr, 1.9, .7, .5)
    fr2 = round_rect(12.2, 12.2, 197.8, 284.8, 5)
    rim(base, fr2, .5, .3, .3)
    s = corner
    put(base, 'corner.png', s, x=13.6, y=13.6)
    put(base, 'corner.png', s, x=210 - 13.6 - s - 2.5, y=13.6, flip_x=True)
    put(base, 'corner.png', s, x=13.6, y=297 - 13.6 - s - 2.5, flip_y=True)
    put(base, 'corner.png', s, x=210 - 13.6 - s - 2.5, y=297 - 13.6 - s - 2.5, flip_x=True, flip_y=True)
    return finish(base, name)


# ------------------------------------------------------------------ small pieces
def build_small():
    for name, src, w, p in (('flourish', 'flourish-wide-1.png', 110, 14), ('flourish2', 'flourish-wide-2.png', 80, 14),
                            ('fleuron', 'fleuron-small.png', 24, 20), ('corner-sm', 'corner.png', 16, 20)):
        Image.fromarray(gold(src, w, p)).save(os.path.join(CACHE, name + '.png'))
    # ring + blue disc  (seal / page number), 30 px per mm, 24 mm
    ppm, S = 30, 24
    c = S / 2
    cv_disc = Image.new('L', (S * ppm, S * ppm), 0)
    ImageDraw.Draw(cv_disc).ellipse([(c - 8.4) * ppm, (c - 8.4) * ppm, (c + 8.4) * ppm, (c + 8.4) * ppm], fill=255)
    disc = np.asarray(cv_disc.resize((S * ppm, S * ppm), Image.LANCZOS), float) / 255
    tex = art.blue_panel(S * ppm, S * ppm, seed=4).astype(float)
    tex *= (1 - .5 * np.clip(1 - ndi.gaussian_filter(disc, .5 * ppm), 0, 1))[..., None]
    out = np.zeros((S * ppm, S * ppm, 4))
    out[..., :3] = tex
    out[..., 3] = disc * 255
    # gold rings
    def ring(r_out, w):
        im = Image.new('L', (S * ppm * 2, S * ppm * 2), 0)
        d = ImageDraw.Draw(im)
        k = ppm * 2
        d.ellipse([(c - r_out) * k, (c - r_out) * k, (c + r_out) * k, (c + r_out) * k], fill=255)
        d.ellipse([(c - r_out + w) * k, (c - r_out + w) * k, (c + r_out - w) * k, (c + r_out - w) * k], fill=0)
        return np.asarray(im.resize((S * ppm, S * ppm), Image.LANCZOS), float) / 255
    for r, w, hgt in ((9.8, 1.5, .7), (8.0, .35, .25), (11.0, .35, .25)):
        g = emboss(ring(r, w), ppm, height_mm=hgt, shadow=.5)
        a = g[..., 3:] / 255
        out[..., :3] = out[..., :3] * (1 - a) + g[..., :3] * a
        out[..., 3:] = np.maximum(out[..., 3:], g[..., 3:])
    Image.fromarray(np.clip(out, 0, 255).astype('uint8'), 'RGBA').save(os.path.join(CACHE, 'ring.png'))

    # rule with fleuron (171 x 7 mm, 20 px per mm)
    for name, w_mm, gap in (('rule', 171, 17), ('sep', 56, 15)):
        p = 20
        h_mm = 8
        W, Hh = int(w_mm * p), int(h_mm * p)
        m = np.zeros((Hh, W))
        cy = Hh // 2
        t = int(.38 * p)
        for yy in (cy - int(.55 * p), cy + int(.55 * p)):
            pass
        half_gap = int(gap / 2 * p)
        m[cy - t // 2:cy + t // 2 + 1, :W // 2 - half_gap] = 1
        m[cy - t // 2:cy + t // 2 + 1, W // 2 + half_gap:] = 1
        # tapered ends
        fade = np.linspace(0, 1, int(18 * p)) ** .8
        m[:, :len(fade)] *= fade[None]
        m[:, -len(fade):] *= fade[::-1][None]
        g = emboss(np.pad(m, ((int(1.2 * p), int(1.2 * p)), (0, 0))), p, height_mm=.35, shadow=.35)
        fl = gold('fleuron-small.png', 11.5 if name == 'rule' else 10.5, p, height_mm=.45, pad_mm=.5)
        img = Image.fromarray(g, 'RGBA')
        f = Image.fromarray(fl, 'RGBA')
        img.alpha_composite(f, (img.width // 2 - f.width // 2, img.height // 2 - f.height // 2 - int(.2 * p)))
        img.save(os.path.join(CACHE, name + '.png'))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for key, fn in (('cover', build_cover), ('divider', build_divider), ('back', build_back), ('frame', build_frame), ('toc', lambda: build_frame(18, 'toc-frame')), ('small', build_small)):
        if what in (key, 'all'):
            fn()
            print(key, 'done')
