#!/usr/bin/env python3
"""Artwork of the internal title pages (siman dividers), written to assets/cover/divider-bg.jpg  (usage: python make_divider.py [out.jpg]).

Made from the client's empty cover (assets/cover/empty-cover.webp) but in black / white / grey / silver, as it sits inside the book:
  - page background: the cloud of the cover (frame and medallion taken out) stretched over the whole page, in grey - the brown smoke becomes dark grey smoke
  - top: a landscape frame, silver, assembled from the corners and rails of the cover frame, whose left part is outside the page; inside it the title block of the
    medallion (rules, swash, flourishes - without the rings and the curved texts), set on paper with a soft smoke edge
  - bottom: the same kind of frame rising from the bottom edge of the page up to a third of the page, fading out upwards; the siman is set in it (live text, engine.js)
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
CORNER = 335                            # the corner blocks (ornaments + rails) of the cover frame, in artwork units
RAIL_T = 62                             # thickness of the rails of the frame

SILVER_RAMP = mc.SILVER_RAMP                         # the frame: dark steel .. bright silver
SWASH_SILVER_RAMP = mc.SILVER_SWASH_RAMP                # the swash: brilliant silver running into dark steel
FRAME_GRADE = mc.PALETTES['soft']['gold']               # the grading of the frame and of the swash: those of the soft palette (the dividers are its black-and-white version)
SWASH = mc.PALETTES['soft']['swash']


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
    """the cloud of the cover in grey: the tone of the soft palette (what the cover has) converted to luminance, so that the grey pages are its black-and-white version"""
    P = mc.PALETTES['soft']
    h, s, v = mc.rgb_to_hsv(a)
    tone = mc.hsv_to_rgb(np.full_like(h, P['t1']), np.clip(s * P['s1'], 0, 1), np.clip(v * (1 + (P['v1'] - 1) * np.clip(s * 3.0, 0, 1)), 0, 1))
    g = np.clip(tone @ np.array([0.299, 0.587, 0.114], dtype=np.float32), 0, 1)
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


def clip_box(shape, x, y, w, h):
    """(canvas slice, sprite slice) of a w x h sprite at (x, y) on a canvas, cut where it leaves the canvas; None if nothing is left"""
    H, W = shape[:2]
    cx0, cy0, cx1, cy1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    return (slice(cy0, cy1), slice(cx0, cx1)), (slice(cy0 - y, cy1 - y), slice(cx0 - x, cx1 - x))


def up2(arr, resample=Image.LANCZOS):
    """float array (H, W) or (H, W, 3) -> twice the size"""
    im = to_img(arr) if arr.ndim == 3 else Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'L')
    im = im.resize((im.width * 2, im.height * 2), resample)
    return np.asarray(im).astype(np.float32) / 255.0


def piece2(a, frame, box):
    """a piece of the cover frame at twice the size: (luminance, alpha)"""
    x0, y0, x1, y1 = box
    rgb = np.asarray(to_img(a[y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))).astype(np.float32) / 255.0
    return lum_of(rgb), np.clip(up2(frame[y0:y1, x0:x1], Image.BICUBIC), 0, 1)


def stretch(arr, w, h):
    return np.asarray(Image.fromarray(arr.astype(np.float32), 'F').resize((w, h), Image.BILINEAR))


def orn_piece(a, frame, kind):
    """a vertical ornament of the cover frame, at twice the size: 'scroll' = the acanthus scroll that hangs from the top-left corner along the rail (without the horizontal
    part of the corner), 'curl' = the curl in the middle of the left rail.  Returns (luminance, alpha); the pieces include the rail they sit on and fade in and out over 24
    units, so that neighbouring pieces overlap without a seam (the ornaments of the cover frame cast their shadow on the rail)."""
    box = (79, 112, 211, 412) if kind == 'scroll' else (79, 585, 205, 690)
    l, m = piece2(a, frame, box)
    m = m.copy()
    if kind == 'scroll':
        m[:50, 146:] = 0                                                   # what belongs to the horizontal part of the corner (leaf and tendril right of the bead)
        m[:72, 196:] = 0
        m[480:, 165:] = 0                                                  # a speck
    n = 2 * 24
    ramp = np.ones(m.shape[0], np.float32)
    ramp[:n] = np.arange(n) / n
    ramp[-n:] = np.minimum(ramp[-n:], np.arange(n)[::-1] / n)
    rail = 2 * (141 - box[0])                                              # columns of the rail itself
    if kind == 'scroll':
        m[:, :rail] *= ramp[:, None]                                       # (the bead at the top of the scroll stays)
    else:
        m = m * ramp[:, None]
    return l, m


def assemble_metal(a, frame, Wb, Hb, orns=()):
    """a frame of any size (Wb x Hb artwork units, at twice the size): the four corner blocks of the cover frame, the rails made of its straight left rail.
    Returns (luminance, alpha)."""
    C, T = CORNER, RAIL_T
    ox0, oy0, ox1, oy1 = FRAME_OUTER[0], FRAME_OUTER[1], FRAME_OUTER[2] + 1, FRAME_OUTER[3] + 1
    assert Wb >= 2 * C and Hb >= 2 * C, (Wb, Hb)
    lum = np.zeros((2 * Hb, 2 * Wb), np.float32)
    al = np.zeros_like(lum)

    def over(l, m, x, y):
        h, w = l.shape
        y0, y1, x0, x1 = max(y, 0), min(y + h, lum.shape[0]), max(x, 0), min(x + w, lum.shape[1])        # what leaves the frame is cut
        if y1 <= y0 or x1 <= x0:
            return
        l, m = l[y0 - y:y1 - y, x0 - x:x1 - x], m[y0 - y:y1 - y, x0 - x:x1 - x]
        x, y = x0, y0
        h, w = l.shape
        sl = (slice(y, y + h), slice(x, x + w))
        na = m + al[sl] * (1 - m)
        lum[sl] = (l * m + lum[sl] * al[sl] * (1 - m)) / np.maximum(na, 1e-4)
        al[sl] = na
    lv, lh = Hb - 2 * C, Wb - 2 * C
    F = 40                                                                              # rails run F units under the corner blocks, which fade out over them (no seam)
    # every rail is stretched from a straight, ornament-free stretch of the same rail of the cover next to its corners (so that the light matches)
    for box, (w, h, x, y) in (((500, oy0, 606, oy0 + T), (lh + 2 * F, T, C - F, 0)), ((410, oy1 - T, 600, oy1), (lh + 2 * F, T, C - F, Hb - T)),
                              ((ox0, 440, ox0 + T, 586), (T, lv + 2 * F, 0, C - F)), ((ox1 - T, 405, ox1, 586), (T, lv + 2 * F, Wb - T, C - F))):
        rl, ra = piece2(a, frame, box)
        over(stretch(rl, 2 * w, 2 * h), stretch(ra, 2 * w, 2 * h), 2 * x, 2 * y)
    for kind, y, flip in orns:                                                           # ornaments of the cover along both rails: y = top of the piece (frame units)
        ol, om = orn_piece(a, frame, kind)
        if y < C or y + ol.shape[0] / 2 > Hb - C:                                         # keep clear of the corner blocks (outside the page)
            continue
        if flip:
            ol, om = ol[::-1], om[::-1]
        over(ol, om, 0, int(round(2 * y)))                                               # left rail
        over(ol[:, ::-1], om[:, ::-1], 2 * Wb - ol.shape[1], int(round(2 * y)))            # right rail (mirrored)
    ramp = np.clip((np.arange(2 * C) - 2 * (C - F)) / (2 * F), 0, 1)                    # 0 .. 1 over the last F units towards the inside of a corner block
    for (bx, by), (x, y), (fx, fy) in (((ox0, oy0), (0, 0), (False, False)), ((ox1 - C, oy0), (Wb - C, 0), (True, False)),
                                       ((ox0, oy1 - C), (0, Hb - C), (False, True)), ((ox1 - C, oy1 - C), (Wb - C, Hb - C), (True, True))):
        l, m = piece2(a, frame, (bx, by, bx + C, by + C))
        rx = ramp[::-1] if fx else ramp                                                  # distance to the rail seam along x (the seam of the horizontal rails)
        ry = ramp[::-1] if fy else ramp
        rows = slice(2 * (C - T), 2 * C) if fy else slice(0, 2 * T)                      # the band of the horizontal rail inside the block
        cols = slice(2 * (C - T), 2 * C) if fx else slice(0, 2 * T)                      # the band of the vertical rail inside the block
        m = m.copy()
        m[rows, :] *= (1 - rx)[None, :]
        m[:, cols] *= (1 - ry)[:, None]
        over(l, m, 2 * x, 2 * y)
    return lum, al


def smoke(shape, rect, tpx, depth, strength, seed):
    """soft dark smoke inside a frame (rect = x, y, w, h in px, tpx = thickness of its rails): strongest at the rails, with an irregular edge like the cloud of the cover"""
    H, W = shape
    rng = np.random.default_rng(seed)
    n = np.zeros((H // 8 + 1, W // 8 + 1), np.float32)
    for sg, wt in ((14, 1.0), (6, 0.6), (3, 0.35)):
        g = ndimage.gaussian_filter(rng.standard_normal(n.shape).astype(np.float32), sg)
        n += wt * g / g.std()
    n = ndimage.zoom(n, 8, order=1)[:H, :W]
    n = np.clip(0.5 + n / 5.0, 0, 1)
    D = depth * (0.55 + 0.9 * n)
    x, y, w, h = rect
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    keep = np.ones((H, W), np.float32)
    for d in (xx - (x + tpx), (x + w - tpx) - xx, yy - (y + tpx), (y + h - tpx) - yy):
        keep *= 1 - strength * np.clip(1 - d / D, 0, 1) ** 1.6
    return 1 - keep


def draw_frame(page, bg, a, frame, geom, L, seed, fade_x=None, lighten=None, orns=()):
    """one silver frame on the page: geom = (x, y, w, h, fade) in canvas px (x may be negative and the frame may leave the page below: what is outside is cut),
    fade = fraction of the height over which the frame fades in from its top edge; fade_x = (x0, x1) in px: opaque left of x0, gone right of x1;
    lighten = (H, W) mask 0..1 where the rails and the smoke are lightened (something stands over them)"""
    H, W = page.shape[:2]
    x, y, w, h, fade = geom
    fs = L['scale']
    Wb, Hb = int(round(w / (2 * fs))), int(round(h / (2 * fs)))
    lum, al = assemble_metal(a, frame, Wb, Hb, orns)
    rgb = silver(None, lum, SILVER_RAMP, FRAME_GRADE, True)
    metal = np.asarray(to_img(rgb).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
    malpha = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
    fy = np.ones(H, np.float32)                                           # vertical fade of the whole frame (rails, ornaments and paper)
    if fade:
        t = np.clip((np.arange(H) - y) / (fade * h), 0, 1)
        fy = t * t * (3 - 2 * t)
    fxv = np.ones(W, np.float32)                                          # horizontal fade of the whole frame
    if fade_x:
        t = np.clip((np.arange(W) - fade_x[0]) / float(fade_x[1] - fade_x[0]), 0, 1)
        fxv = 1 - t * t * (3 - 2 * t)
    fy = fy[:, None] * fxv[None, :]
    foot = np.zeros((H, W), np.float32)
    box = clip_box(foot.shape, x, y, w, h)
    foot[box[0]] = 1.0
    A = foot * fy ** 2 if not fade_x else foot * fy                        # the paper fades quicker than the rails, so that no edge of it shows where the frame is gone
    sh = ndimage.gaussian_filter(np.roll(np.roll(foot, 9, axis=0), 7, axis=1), 10)                 # a soft shadow so that the frame stands on the page
    page *= (1 - L.get('shadow', 0.30) * sh * fy)[..., None]
    tpx = RAIL_T * 2 * fs
    hz = L.get('halo', {})
    halo = smoke((H, W), (x, y, w, h), tpx, hz.get('depth', 150) * 2 * fs, hz.get('strength', 0.6), seed)
    if lighten is not None:
        halo = halo * (1 - lighten)
    paper = (1 - (1 - bg) * L.get('paper', 0.35)) * (1 - halo)[..., None]
    page[:] = page * (1 - A[..., None]) + paper * A[..., None]
    am = np.zeros((H, W), np.float32)
    cm = np.zeros((H, W, 3), np.float32)
    am[box[0]] = malpha[box[1]]
    cm[box[0]] = metal[box[1]]
    if lighten is not None:
        am = am * (1 - L.get('lighten', {}).get('alpha', 0.92) * lighten)
    Am = (am * fy)[..., None]
    page[:] = page * (1 - Am) + cm * Am


def build(out=None, layout=None, kind='divider'):
    """kind 'divider': pillars + medallion + flourishes (siman divider); kind 'credits': the pillars alone (the credits page puts its text between them)"""
    cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8'))
    variant = kind                                                        # (the loops below reuse the name `kind`)
    L = dict(layout or cfg['divider'])
    if variant == 'credits':
        L.update((cfg.get('credits') or {}).get('layout') or {})
    cache = os.environ.get('DIVIDER_CACHE')
    if cache and os.path.exists(cache):                                   # development: the slow steps below are kept in a pickle
        import pickle
        clean, a, elem, frame, swash = pickle.load(open(cache, 'rb'))
    else:
        src = Image.open(mc.SRC).convert('RGB')
        clean, a, elem = mc.frame_only(src)                               # the cover without the medallion
        frame, swash = mc.gold_masks(src)                                 # soft masks: the gilded frame, the swash of the medallion
        if cache:
            import pickle
            pickle.dump((clean.astype(np.float32), a.astype(np.float32), elem, frame.astype(np.float32), swash.astype(np.float32)), open(cache, 'wb'))
    frame = np.clip(frame, 0, 1).astype(np.float32)
    swash = np.clip(swash, 0, 1).astype(np.float32)
    W, H = PAGE_U[0] * PX, PAGE_U[1] * PX
    MM = 8 * PX                                                           # canvas px per mm

    # ---- page background: the cloud inside the frame, ornaments filled in, stretched over the page
    hole = ndimage.binary_dilation(frame > 0.01, structure=np.ones((3, 3)), iterations=5)
    cloud = fill_holes(clean, hole)
    cloud = np.stack([ndimage.gaussian_filter(cloud[..., c], 1.6) for c in range(3)], axis=-1)       # the cloud of the cover carries block noise of its jpeg: smooth it before it is stretched
    ix0, iy0, ix1, iy1 = FRAME_INNER
    padx, pady = 60, 40                                                   # keeps the curls of the side ornaments out of the page
    crop = cloud[iy0 + pady:iy1 - pady, ix0 + padx:ix1 - padx]
    bg = Image.fromarray((np.clip(grey_cloud(crop), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
    bg = np.asarray(bg).astype(np.float32) / 255.0
    flat = np.stack([ndimage.gaussian_filter(bg[..., c], 14) for c in range(3)], axis=-1)           # the near-white parts of the cloud keep faint ghosts of the old artwork: flatten them
    w = np.clip((flat - 0.86) / 0.08, 0, 1)
    bg = bg * (1 - w) + flat * w
    bg = 1 - (1 - bg) * L.get('edge', 1.0)                                # lighter smoke at the edges of the page (less heavy)
    page = bg.copy()

    # ---- the two pillars: the rails of a frame centred under the title, running over the whole height of the page (its top and bottom are outside the page), with no fade;
    # the title block stands over them and the pillars are lightened where they meet
    fs = L['scale']
    ms = L['medal']['scale']
    lcx = L['axis']                                                       # mm: the axis of the pillars; the circle and the siman are centred on it
    P = L['pillars']
    lt = L['lighten']
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.hypot(xx - L['medal']['cx'] * MM, yy - L['medal']['cy'] * MM)                          # a soft round zone around the medallion
    tt = np.clip((dd - lt['r'] * MM) / (lt['feather'] * MM), 0, 1)
    lighten = 1 - tt * tt * (3 - 2 * tt)
    del xx, yy, dd, tt
    pw = int(round(P['w'] * MM))
    ph = int(round((PAGE_U[1] / 8 + 2 * P['bleed']) * MM))
    og = L['ornaments']                                                   # the ornaments of the cover frame along the whole length of the pillars
    u = lambda mm_: (mm_ + P['bleed']) * 8 / fs                            # page mm -> units of the frame (top of the frame = -bleed)
    sc, cu = 300 * fs / 8, 105 * fs / 8                                    # mm: height of the scroll and of the curl
    cycle = [('scroll', False, sc), ('curl', False, cu), ('scroll', True, sc), ('curl', True, cu)]       # scroll hanging down, curl, scroll rising, curl
    pieces, y, i = [], og['anchor'], 0
    while y < PAGE_U[1] / 8 + P['bleed']:                                  # from the anchor downwards ...
        kind, flip, h = cycle[i % 4]
        pieces.append((kind, u(y), flip)); y += h + og['gap']; i += 1
    y, i = og['anchor'], -1
    while y > -P['bleed']:                                                 # ... and upwards
        kind, flip, h = cycle[i % 4]
        y -= h + og['gap']; pieces.append((kind, u(y), flip)); i -= 1
    draw_frame(page, bg, a, frame, (int(round(lcx * MM)) - pw // 2, -int(round(P['bleed'] * MM)), pw, ph, 0), L, 2, lighten=(None if variant == 'credits' else lighten), orns=pieces)
    if variant == 'credits':                                                  # nothing stands over the pillars on the credits page
        out = out or os.path.join(HERE, 'assets', 'cover', 'credits-bg.jpg')
        to_img(page).save(out, quality=92, subsampling=0, optimize=True)
        return out

    # ---- the title block of the medallion: black ink (multiplied onto the page, without the rings) + silver swash
    bx0, by0m, bx1, by1m = mc.MEDALLION_BOX
    ink = np.where(elem[..., None], np.clip(a / np.maximum(clean, 1e-3), 0, 1), 1.0)
    ink_full = np.clip(lum_of(ink), 0, 1)
    yy, xx = np.mgrid[0:ink_full.shape[0], 0:ink_full.shape[1]].astype(np.float32)
    r = np.hypot(xx - RING_C[0], yy - RING_C[1])
    ring = ndimage.binary_dilation((np.abs(r - 329) <= 3.2) | (np.abs(r - 342) <= 3.2), iterations=1)
    inkmask = ink_full < 0.85
    rules = np.zeros(ink_full.shape, bool)                                # the straight rules next to the title keep their pixels where a ring crosses them
    for (ya, yb, xa, xb, pa, pb) in ((585, 625, 660, 1000, 640, 1130), (900, 940, 380, 900, 350, 940)):
        cnt = inkmask[ya:yb, xa:xb].sum(1)
        for k in np.where(cnt > 0.5 * (xb - xa))[0]:
            rules[ya + k - 1:ya + k + 2, pa:pb] = True
    protect = rules | ndimage.binary_opening(inkmask, structure=np.ones((5, 5))) | (swash > 0.3)
    if not L['medal'].get('rings', True):
        ink_full = np.where(ring & ~protect, 1.0, ink_full)               # the rings are gone, the rest of the medallion stays
    if not L['medal'].get('rings', True):
        lab, n = ndimage.label(ink_full < 0.85, structure=np.ones((3, 3)))     # bits of the rings that are left over
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        small = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz < 90]) & ~protect
        ink_full = np.where(ndimage.binary_dilation(small, iterations=2), 1.0, ink_full)
    ink_l = ink_full[by0m:by1m, bx0:bx1] ** L['medal'].get('ink', 1.0)
    sw = swash[by0m:by1m, bx0:bx1]
    sw_rgb = silver(None, lum_of(a[by0m:by1m, bx0:bx1]), SWASH_SILVER_RAMP, SWASH)
    bw, bh2 = int(round((bx1 - bx0) * ms * PX)), int(round((by1m - by0m) * ms * PX))
    rs = lambda im: np.asarray(im.resize((bw, bh2), Image.LANCZOS)).astype(np.float32) / 255.0
    ink_s = rs(Image.fromarray((ink_l * 255).astype(np.uint8)))
    sw_s = rs(Image.fromarray((sw * 255).astype(np.uint8)))
    rgb_s = rs(to_img(sw_rgb))
    mx = int(round(L['medal']['cx'] * MM + (bx0 - RING_C[0]) * ms * PX))
    my = int(round(L['medal']['cy'] * MM + (by0m - RING_C[1]) * ms * PX))
    box = clip_box(page.shape, mx, my, bw, bh2)
    reg = page[box[0]] * ink_s[box[1]][..., None]
    page[box[0]] = reg * (1 - sw_s[box[1]][..., None]) + rgb_s[box[1]] * sw_s[box[1]][..., None]

    # ---- the two small flourishes of the medallion (above / below the title), set again above and below the siman
    fl, lb = L.get('fleurons'), L.get('label')
    if fl and lb:
        for key, (ux0, uy0, ux1, uy1) in (('top', FLEURON_TOP), ('bottom', FLEURON_BOTTOM)):
            piece = np.clip(lum_of(np.where(elem[..., None], np.clip(a / np.maximum(clean, 1e-3), 0, 1), 1.0)[uy0:uy1, ux0:ux1]), 0, 1)
            k = fl['scale']
            pw2, ph2 = int(round((ux1 - ux0) * k * PX)), int(round((uy1 - uy0) * k * PX))
            ps = np.asarray(Image.fromarray((piece * 255).astype(np.uint8)).resize((pw2, ph2), Image.LANCZOS)).astype(np.float32) / 255.0
            qx = int(round((lcx * 8 - (ux1 - ux0) * k / 2) * PX))
            qy = int(round((lb['cy'] * 8 + fl[key] - (uy1 - uy0) * k / 2) * PX))
            box = clip_box(page.shape, qx, qy, pw2, ph2)
            if box:
                page[box[0]] *= ps[box[1]][..., None]
    out = out or os.path.join(HERE, 'assets', 'cover', 'divider-bg.jpg')
    to_img(page).save(out, quality=92, subsampling=0, optimize=True)
    return out


def make_assets():
    """the logo of the organisation in grey (the inner pages have no colour) and the small flourish of the medallion as a picture with alpha (the separator of the credits page)"""
    logo = Image.open(os.path.join(HERE, 'assets', 'cover', 'logo.png')).convert('RGBA')
    g = np.asarray(logo).astype(np.float32) / 255.0
    lum = np.clip(g[..., :3] @ np.array([0.299, 0.587, 0.114], dtype=np.float32), 0, 1)
    lum = np.clip((lum - 0.10) * 1.12, 0, 1) ** 0.9                          # a little contrast: the navy becomes near black, the gold a mid grey
    out = np.stack([lum, lum, lum, g[..., 3]], axis=-1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(HERE, 'assets', 'cover', 'logo-grey.png'), optimize=True)
    src = Image.open(mc.SRC).convert('RGB')
    clean, a, elem = mc.frame_only(src)
    ux0, uy0, ux1, uy1 = FLEURON_TOP
    ink = np.clip(lum_of(np.where(elem[..., None], np.clip(a / np.maximum(clean, 1e-3), 0, 1), 1.0)[uy0:uy1, ux0:ux1]), 0, 1)
    al = Image.fromarray(((1 - ink) * 255).astype(np.uint8)).resize(((ux1 - ux0) * 4, (uy1 - uy0) * 4), Image.LANCZOS)
    fl = Image.new('RGBA', al.size, (36, 36, 38, 0))
    fl.putalpha(al)
    fl.save(os.path.join(HERE, 'assets', 'cover', 'fleuron-sep.png'), optimize=True)
    return 'logo-grey.png, fleuron-sep.png'


if __name__ == '__main__':
    print('divider background:', build(sys.argv[1] if len(sys.argv) > 1 else None))
