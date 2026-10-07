"""Re-creation of the reference cover (assets/ref/cover-ref.png, 387 x 510 px) at print resolution.

The reference is low resolution, so its ornaments are *traced*: the shapes are extracted from it
(warm / bright relief against the dark recess, the brown engraving against the parchment), cleaned,
mirrored and re-rendered as crisp embossed metal at 11 px per mm.  Nothing of the reference's own
pixels is placed into the result.

Coordinates: `u, v` are reference pixels (the reference is 387 px wide = 210 mm, so 1 px = .5426 mm).
The A4 canvas is 547 reference rows high (the reference has 510): the extra rows are inserted in the
quiet middle of the side bands and under the title panel.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.deps'))
from art import CACHE  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REF_PATH = os.path.join(ROOT, 'assets', 'ref', 'cover-ref.png')

K = 6                      # canvas pixels per reference pixel  (2322 x 3284 for A4)
RW, RH = 387, 510
CW, CH = RW * K, int(round(297 / 210 * RW * K))      # canvas size: 2322 x 3284
MM = 210 / RW              # mm per reference pixel
PPM = K / MM               # canvas px per mm  (11.06)
EXTRA = CH / K - RH        # rows inserted (about 37)
UC = RW / 2                # axis of symmetry (u = 193.5)

# vertical mapping of the *side bands*: rows 250..330 are a plain line, which is stretched
SEG_A, SEG_B = 250, 330


def v_side(v):
    """reference row -> canvas row (in reference px) for the side bands"""
    v = np.asarray(v, float)
    return np.where(v < SEG_A, v, np.where(v > SEG_B, v + EXTRA, SEG_A + (v - SEG_A) * (SEG_B + EXTRA - SEG_A) / (SEG_B - SEG_A)))


_ref = None


def ref_img():
    global _ref
    if _ref is None:
        _ref = Image.open(REF_PATH).convert('RGB')
    return _ref


def ref_big(S):
    im = ref_img()
    return np.asarray(im.resize((RW * S, RH * S), Image.BICUBIC)).astype(float)


def poly_mask(poly, S, w=RW, h=RH):
    im = Image.new('L', (w * S, h * S), 0)
    ImageDraw.Draw(im).polygon([(float(x) * S, float(y) * S) for x, y in poly], fill=255)
    return np.asarray(im) > 127


def relief_mask(S=12):
    """warm, bright relief that is not part of a smooth region  (bool, RH*S x RW*S)"""
    a = ref_big(S)
    L = a.mean(2)
    warm = a[..., 0] - a[..., 2]
    cand = (warm > 22) & (L > 70)
    hp = np.abs(L - ndi.gaussian_filter(L, 2.2 * S))
    smooth = hp < 5
    bgr = ndi.binary_opening(cand & smooth, structure=np.ones((int(2.5 * S), int(2.5 * S))))
    bgr = ndi.binary_dilation(bgr, iterations=int(1.2 * S))
    orn = cand & ~bgr
    orn = ndi.binary_opening(orn, structure=np.ones((3, 3)))
    return orn


def smooth_mask(m, sigma, thr=.5):
    return ndi.gaussian_filter(m.astype(float), sigma) > thr


def to_canvas_left(mask_S, S, vmap=True):
    """take a reference-space mask (S px per ref px) -> canvas float mask (K px per ref px), side-band mapping applied"""
    h, w = mask_S.shape
    img = Image.fromarray((mask_S * 255).astype('uint8'))
    out = Image.new('L', (CW, CH), 0)
    # slice into horizontal strips and place each at its mapped row
    strips = [(0, SEG_A), (SEG_A, SEG_B), (SEG_B, RH)]
    for a, b in strips:
        strip = img.crop((0, int(a * S), w, int(b * S)))
        if a == SEG_A:
            new_h = int(round((SEG_B + EXTRA - SEG_A) * K))
            y_to = int(round(SEG_A * K))
        elif a == 0:
            new_h = int(round(SEG_A * K))
            y_to = 0
        else:
            new_h = int(round((RH - SEG_B) * K))
            y_to = int(round((SEG_B + EXTRA) * K))
        strip = strip.resize((RW * K, new_h), Image.LANCZOS)
        out.paste(strip, (0, y_to))
    return np.asarray(out, dtype=float) / 255


# ------------------------------------------------------------------------------------------------
# tracing
KEEP_LEFT = [(28, 36), (89, 36), (89, 98), (84, 110), (76, 122), (67, 133), (62, 142), (58, 152), (58, 166), (61, 186), (54, 200),
             (52, 215), (50, 215), (50, 395), (57, 395), (59, 410), (62, 425), (66, 434), (71, 446), (77, 460), (79, 472),
             (82, 478), (100, 484), (125, 494), (150, 501), (158, 512), (28, 512)]


def trace_left_relief(S=8):
    """left ornament band (gold relief) as a bool mask in reference space (S px per reference px)"""
    a = ref_big(S)
    L = a.mean(2)
    warm = a[..., 0] - a[..., 2]
    cand = (warm > 22) & (L > 70)
    hp = np.abs(L - ndi.gaussian_filter(L, 1.0 * S))
    sm = (hp < 5) & cand
    bgr = ndi.binary_opening(sm, structure=np.ones((int(3.0 * S), int(3.0 * S))))
    bgr = ndi.binary_dilation(bgr, iterations=int(1.0 * S))
    orn = cand & ~bgr & poly_mask(KEEP_LEFT, S)
    orn = ndi.binary_opening(orn, structure=np.ones((3, 3)))
    return smooth_mask(orn, S * .45)


def trace_top_arcs(S=8):
    """the two dim C-shaped arcs next to the panel rim (top of the band): looser thresholds, small box"""
    a = ref_big(S)
    L = a.mean(2)
    warm = a[..., 0] - a[..., 2]
    m = (warm > 12) & (L > 48)
    box = poly_mask([(64, 38), (87.5, 38), (87.5, 90), (64, 90)], S)
    m = m & box
    m = ndi.binary_opening(m, structure=np.ones((3, 3)))
    return smooth_mask(m, S * .45)


def trace_panel_left(S=8):
    """blue title panel, left half (u < 193.5), reference space (S px per px)"""
    a = ref_big(S)
    r, b, L = a[..., 0], a[..., 2], a.mean(2)
    blue = ((b - r) > 10) & (L < 175)
    box = np.zeros_like(blue)
    box[:, 94 * S:int(UC * S)] = True
    pm = ndi.binary_fill_holes(blue & box)
    pm = ndi.binary_opening(pm, structure=np.ones((int(1.6 * S) | 1, int(1.6 * S) | 1)))
    pm = ndi.binary_closing(pm, structure=np.ones((5, 5)))
    lab, n = ndi.label(pm)
    if n > 1:                                   # keep the main body only
        sizes = ndi.sum(pm, lab, range(1, n + 1))
        pm = lab == (1 + int(np.argmax(sizes)))
    pm = smooth_mask(pm, S * .6)
    # exactly straight where the reference is straight
    pm[:int(256 * S), :int(98.5 * S)] = False
    pm[:int(256 * S), int(98.5 * S):int(UC * S)] = True
    return pm


# panel outline: points measured on the reference, fitted with smoothing splines (three runs, corners kept sharp)
_PANEL_A = [(98.5, 250.6), (98.5, 255.4), (100.3, 258.4), (101.5, 262.0), (102.7, 265.5), (104.4, 268.6), (107.6, 270.3), (111.3, 271.4), (114.7, 272.9),
            (118.2, 274.1), (120.9, 276.2), (124.3, 277.6), (128.9, 277.8), (133.4, 278.0), (137.1, 279.2)]
_PANEL_B = [(137.1, 279.2), (137.5, 283.5), (138.1, 287.8), (139.2, 291.4), (139.8, 295.6), (141.8, 298.6)]
_PANEL_C = [(141.8, 298.6), (143.9, 301.2), (146.8, 303.1), (150.3, 304.4), (154.1, 305.5), (158.0, 306.3), (161.7, 307.4), (165.4, 308.5), (168.8, 309.9),
            (172.0, 311.5), (175.2, 313.1), (178.4, 314.7), (181.2, 316.6), (184.1, 318.6), (186.7, 320.8), (189.0, 323.2), (191.1, 325.9), (193.5, 330.6)]


def _spline(pts, n, smooth):
    from scipy.interpolate import splprep, splev
    p = np.array(pts, float)
    tck, _ = splprep([p[:, 0], p[:, 1]], s=smooth, k=3 if len(p) > 5 else 2)
    t = np.linspace(0, 1, n)
    x, y = splev(t, tck)
    x[0], y[0], x[-1], y[-1] = p[0, 0], p[0, 1], p[-1, 0], p[-1, 1]
    return np.stack([x, y], 1)


def panel_polygon(top=-6, half=True):
    """outline of the blue panel in reference px: left half (top .. tip), or the whole closed polygon"""
    A = _spline(_PANEL_A, 80, 1.2)
    B = _spline(_PANEL_B, 20, .4)
    C = _spline(_PANEL_C, 90, 1.2)
    left = np.vstack([[(98.5, top)], A, B[1:], C[1:]])
    if half:
        return left
    right = left[::-1].copy()
    right[:, 0] = RW - right[:, 0]
    return np.vstack([left, right])


def panel_mask_canvas(ss=3):
    poly = panel_polygon(half=False)
    im = Image.new('L', (CW * ss // 2, CH * ss // 2), 0)       # drawn at half canvas x ss, then resized (keeps memory sane)
    ImageDraw.Draw(im).polygon([(x * K * ss / 2, y * K * ss / 2) for x, y in poly], fill=255)
    im = im.resize((CW, CH), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


def trace_tip_relief(S=8):
    """tan relief of the panel rim + the engraved scrolls under the tip, left half (the brown / tan pixels)"""
    a = ref_big(S)
    L = a.mean(2)
    warm = a[..., 0] - a[..., 2]
    m = (L < 155) & (warm > 32)
    box = poly_mask([(84, 150), (UC, 150), (UC, 346), (84, 346)], S)
    m = m & box
    m = ndi.binary_opening(m, structure=np.ones((3, 3)))
    return smooth_mask(m, S * .5)


# ------------------------------------------------------------------------------------------------
# canvas helpers
def half_to_canvas(m, S, mirror=True, side=False):
    """left-half mask in reference space (S px/px, RH rows) -> canvas mask (CH x CW). side=True: apply the side-band row mapping"""
    if side:
        left = to_canvas_left(m.astype(float), S)
    else:
        img = Image.fromarray((m.astype(float) * 255).astype('uint8'))
        img = img.resize((RW * K, RH * K), Image.LANCZOS)
        left = np.zeros((CH, CW))
        left[:RH * K] = np.asarray(img, float) / 255
    if not mirror:
        return left
    return np.maximum(left, left[:, ::-1])


# ------------------------------------------------------------------------------------------------
# rendering
import art  # noqa: E402
from art import emboss, bevel_relief, ramp, fbm  # noqa: E402

REF_GOLD = [(0, (26, 16, 8)), (.14, (74, 52, 26)), (.3, (128, 98, 56)), (.48, (176, 148, 98)), (.62, (208, 184, 132)), (.78, (230, 212, 166)),
            (.92, (246, 238, 208)), (1, (254, 251, 236))]
TANGOLD = [(0, (58, 36, 14)), (.3, (134, 96, 46)), (.55, (184, 146, 82)), (.8, (224, 192, 124)), (1, (248, 228, 176))]
IVORY2 = [(0, (122, 92, 52)), (.3, (194, 168, 110)), (.58, (230, 214, 170)), (.82, (246, 237, 207)), (1, (254, 251, 238))]
PARCH = [(0, (30, 18, 7)), (1.5, (78, 50, 20)), (4, (146, 108, 52)), (8, (200, 166, 100)), (13, (230, 212, 160)), (20, (246, 239, 212)), (26, (248, 244, 218))]


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mottle(h, w, seed, stops, big=360, mid=60, mix=.35, grain=3.0):
    """cloudy / mottled blue (computed at half size, then enlarged)"""
    rng = np.random.default_rng(seed)
    hh, ww = h // 2, w // 2
    base = fbm(hh, ww, big / 2, 6, .55, rng)
    base = art.warp(base, big * .12, big / 3, rng)
    fine = fbm(hh, ww, mid / 2, 4, .55, rng)
    v = (1 - mix) * base + mix * fine
    v = (v - v.min()) / (v.max() - v.min())
    v = np.clip((v - .5) * 1.35 + .5, 0, 1)
    col = ramp(v, stops)
    img = Image.fromarray(np.clip(col, 0, 255).astype('uint8')).resize((w, h), Image.BICUBIC)
    col = np.asarray(img).astype(float)
    col += ((rng.random((h, w)) - .5) * grain)[..., None]
    return col


def comp(base, rgba, x=0, y=0):
    """alpha composite RGBA uint8 (h,w,4) on float base at integer px offset"""
    h, w = rgba.shape[:2]
    a = rgba[..., 3:].astype(float) / 255
    base[y:y + h, x:x + w] = base[y:y + h, x:x + w] * (1 - a) + rgba[..., :3] * a


MASK_CACHE = os.path.join(CACHE, 'refmasks.npz')


def crisp(m, sigma=1.25, soft=.6):
    """round the pixel noise of a traced mask, then re-anti-alias the edge"""
    b = ndi.gaussian_filter(m.astype(np.float32), sigma) > .5
    return ndi.gaussian_filter(b.astype(np.float32), soft)


def parchment_tex(h, w, seed, tint=.5):
    """cream paper: constant warm ivory + the thin veins of the marble + a whisper of low-frequency tone (no blotches)"""
    tex = art.cream_marble(w // 2, h // 2, seed=seed, tint=tint).astype(np.float32)
    low = ndi.gaussian_filter(tex, (30, 30, 0))
    detail = tex - low
    rng = np.random.default_rng(seed + 1)
    soft = ndi.zoom(rng.random((6, 5)), (h / 2 / 6 + 1, w / 2 / 5 + 1), order=3)[:h // 2, :w // 2].astype(np.float32)
    soft = (soft - soft.mean()) / (soft.std() + 1e-6) * 1.6
    base = np.array([248, 243, 216], np.float32)
    out = base + detail * 1.1 + soft[..., None]
    out = np.asarray(Image.fromarray(np.clip(out, 0, 255).astype('uint8')).resize((w, h), Image.BICUBIC)).astype(np.float32)
    return out + ((np.random.default_rng(seed + 2).random((h, w)) - .5) * 3)[..., None]


def get_masks(S=8, force=False):
    """traced masks on the canvas (uint8 0..255): side ornaments (both sides), panel, tip engraving"""
    if os.path.exists(MASK_CACHE) and not force:
        z = np.load(MASK_CACHE)
        return {k: z[k].astype(np.float32) / 255 for k in z.files}
    side_half = trace_left_relief(S) | trace_top_arcs(S)
    m = dict(side=crisp(half_to_canvas(side_half, S, side=True)),
             panel=panel_mask_canvas(),
             tip=crisp(half_to_canvas(trace_tip_relief(S), S)))
    np.savez_compressed(MASK_CACHE, **{k: (v * 255).astype('uint8') for k, v in m.items()})
    return {k: v.astype(np.float32) for k, v in m.items()}


def rim_masks(m_panel, vv):
    """procedural rim: a bar beside the panel at the top that widens into the carved band round the ogee"""
    d_out = ndi.distance_transform_edt(m_panel < .5).astype(np.float32) / K          # ref px outside the panel
    t = smoothstep(vv, 195, 250)
    gap = 4.6 * (1 - t)
    wd = 10.0 - gap
    band = ((d_out > gap) & (d_out <= gap + wd)).astype(np.float32)
    band = ndi.gaussian_filter(band, .45 * K / 2)
    return band, d_out


def build_cover_bg(name='ref-cover-bg', S=8, quality=92, crop=None):
    import time
    t0 = time.time()

    def lap(msg):
        print(f'  {msg} {time.time() - t0:.0f}s', flush=True)

    uu = ((np.arange(CW) + .5) / K).astype(np.float32)[None, :]
    vv = ((np.arange(CH) + .5) / K).astype(np.float32)[:, None]
    M = get_masks(S)
    m_side, m_panel, m_tip = M['side'], M['panel'], M['tip']
    lap('masks')

    # ---- background blue (darker than the panel, like the reference)
    bg = mottle(CH, CW, 3, [(0, (14, 24, 38)), (.45, (24, 40, 58)), (.8, (34, 56, 80)), (1, (48, 76, 106))], big=800, mid=120, mix=.42)
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    r = np.hypot((xx - CW / 2) / (CW / 2), (yy - CH / 2) / (CH / 2))
    bg *= (1 - .28 * np.clip(r - .5, 0, 1) ** 1.3)[..., None]
    del yy, xx, r
    lap('bg')

    # ---- parchment bowl
    cream = parchment_tex(CH, CW, 5).astype(float)
    d_side = np.minimum(uu - 43, RW - 43 - uu)
    d_bot = (RH + EXTRA - 3) - vv
    d_top = (vv - 92) / 6.5
    e = np.minimum(np.minimum(d_side, d_bot * 1.15), d_top)
    e = np.clip(e, -2, 60)
    pos = [p for p, _ in PARCH]
    cols = np.array([c for _, c in PARCH], float)
    glow = np.stack([np.interp(e, pos, cols[:, k]) for k in range(3)], -1)
    g = 1 - smoothstep(e, 6, 26)
    parch = cream * (1 - g[..., None]) + glow * g[..., None]
    bowl = ((uu >= 43) & (uu <= RW - 43) & (vv >= 44) & (vv <= RH + EXTRA - 3)).astype(np.float32)
    bowl = ndi.gaussian_filter(bowl, K * 1.6) * smoothstep(vv, 58, 96)
    base = bg * (1 - bowl[..., None]) + parch * bowl[..., None]
    del cream, glow, parch
    lap('parchment')

    # ---- panel
    pan = mottle(CH, CW, 11, [(0, (36, 62, 94)), (.4, (54, 88, 126)), (.75, (68, 108, 148)), (1, (90, 132, 172))], big=700, mid=110, mix=.4)
    dist_in = ndi.distance_transform_edt(m_panel > .5).astype(np.float32) / K
    edge_f = .5 + .5 * smoothstep(dist_in, 0, 18)
    low_f = 1 - .6 * smoothstep(vv, 225, 332)
    pan *= (edge_f * low_f)[..., None]
    mp = ndi.gaussian_filter(m_panel, .6)
    base = base * (1 - mp[..., None]) + pan * mp[..., None]
    del pan, dist_in, edge_f, low_f
    lap('panel')

    # ---- recess (dark halo behind the scrollwork)
    halo = np.clip(ndi.gaussian_filter(m_side, 3.4 * K) * 3.4, 0, 1) ** .9
    base = base * (1 - halo[..., None] * .92) + np.array([12, 9, 8.]) * (halo[..., None] * .92)
    lap('recess')

    # ---- rim round the panel + engraved scrolls
    np.save(os.path.join(CACHE, 'ref-base.npy'), np.clip(base, 0, 255).astype('uint8'))
    return finish_cover(base, m_side, m_panel, m_tip, vv, name, quality, lap)


def finish_cover(base, m_side, m_panel, m_tip, vv, name, quality, lap, crop=None):
    """rim, engraving and the side ornaments on top of the prepared base. crop=(x0,y0,x1,y1) in canvas px renders only that window"""
    if crop:
        x0, y0, x1, y1 = crop
        base = base[y0:y1, x0:x1].astype(float)
        m_side, m_panel, m_tip, vv = m_side[y0:y1, x0:x1], m_panel[y0:y1, x0:x1], m_tip[y0:y1, x0:x1], vv[y0:y1]
    d_out = ndi.distance_transform_edt(m_panel < .5).astype(np.float32) / K          # ref px outside the panel
    t_ = smoothstep(vv, 195, 250)
    bar = ((d_out > 4.6) & (d_out <= 9.9)).astype(np.float32)
    inner = ((d_out > 4.6 * (1 - t_) + .05) & (d_out <= 4.75)).astype(np.float32) * (t_ > .02)
    bar = ndi.gaussian_filter(bar, .5 * K / 2)
    inner = ndi.gaussian_filter(inner, .5 * K / 2)
    scroll = (m_tip > .5) & (d_out > 12.0) & (vv > 262)
    scroll = ndi.gaussian_filter(scroll.astype(np.float32), .5)
    rgba = bevel_relief(inner, PPM, bevel_mm=.3, dome_mm=.6, colors=IVORY2, shadow=.35, ambient=.64, shadow_rgb=(48, 32, 12), spec=.2)
    comp(base, rgba)
    rgba = bevel_relief(bar, PPM, bevel_mm=.38, dome_mm=.7, colors=TANGOLD, shadow=.55, ambient=.58, shadow_rgb=(40, 24, 8), spec=.3)
    comp(base, rgba)
    # thin golden-orange line where the ivory meets the panel
    edge = ((d_out > .02) & (d_out < .75)).astype(np.float32) * (t_ > .3)
    edge = ndi.gaussian_filter(edge, .6) * .7
    base = base * (1 - edge[..., None]) + np.array([214, 160, 58.]) * edge[..., None]
    # engraved scrolls: dark brown grooves with a light lip on the lower-right edge
    sh = ndi.shift(scroll, (.42 * PPM, .32 * PPM), order=1)
    hl = np.clip(sh - scroll, 0, 1) * .9
    base = base * (1 - hl[..., None]) + np.array([255, 250, 236.]) * hl[..., None]
    ink = np.clip(ndi.gaussian_filter(scroll, .45), 0, 1) * .85
    base = base * (1 - ink[..., None]) + np.array([138, 100, 50.]) * ink[..., None]
    lap('rim')

    # ---- side ornaments
    rgba = bevel_relief(m_side, PPM, bevel_mm=.42, dome_mm=.8, colors=REF_GOLD, shadow=.6, ambient=.58)
    comp(base, rgba)
    lap('sides')

    out = np.clip(base, 0, 255).astype('uint8')
    if crop:
        return out
    Image.fromarray(out).save(os.path.join(CACHE, name + '.png'))
    Image.fromarray(out).save(os.path.join(CACHE, name + '.jpg'), quality=quality, subsampling=0)
    lap('saved')
    return out


def render_crop(box, **kw):
    """quick preview of the ornaments in a window (canvas px) using the cached base"""
    M = get_masks()
    base = np.load(os.path.join(CACHE, 'ref-base.npy'))
    vv = ((np.arange(CH) + .5) / K).astype(np.float32)[:, None]
    return finish_cover(base, M['side'], M['panel'], M['tip'], vv, 'crop', 90, lambda m: None, crop=box)


def _scaled(m, f):
    img = Image.fromarray((np.clip(m, 0, 1) * 255).astype('uint8'))
    img = img.resize((max(1, int(img.width * f)), max(1, int(img.height * f))), Image.LANCZOS)
    return np.asarray(img, np.float32) / 255


def build_frame_ref(name='ref-frame', f=.58, x_mm=5.0, y_mm=5.0, quality=92):
    """interior pages: cream page, thin gold line down both sides, the traced clusters (scaled) in the four corners"""
    import time
    t0 = time.time()
    M = get_masks()
    side = M['side']
    top = _scaled(side[int(40 * K):int(220 * K), int(35 * K):int(90 * K)], f)
    bot = _scaled(side[int((376 + EXTRA) * K):CH, int(35 * K):int(160 * K)], f)
    page = np.zeros((CH, CW), np.float32)
    px, py = int(x_mm * PPM), int(y_mm * PPM)
    # left
    page[py:py + top.shape[0], px:px + top.shape[1]] = np.maximum(page[py:py + top.shape[0], px:px + top.shape[1]], top)
    by = CH - py - bot.shape[0]
    page[by:by + bot.shape[0], px:px + bot.shape[1]] = np.maximum(page[by:by + bot.shape[0], px:px + bot.shape[1]], bot)
    # the thin line between the clusters (same cross-section as the traced line)
    lx0 = px + int((37.8 - 35) * K * f)
    lw = max(2, int(2.4 * K * f))
    page[py + top.shape[0] - 4:by + 4, lx0:lx0 + lw] = 1
    page = np.maximum(page, page[:, ::-1])
    page = crisp(page, .8, .5)
    lap = lambda m: print(f'  {m} {time.time() - t0:.0f}s', flush=True)

    cream = parchment_tex(CH, CW, 21).astype(float)
    uu = ((np.arange(CW) + .5) / PPM).astype(np.float32)[None, :]
    vv = ((np.arange(CH) + .5) / PPM).astype(np.float32)[:, None]
    e = np.minimum(np.minimum(uu, 210 - uu), np.minimum(vv, 297 - vv))
    stops = [(0, (196, 160, 98)), (3, (222, 196, 138)), (7, (240, 226, 184)), (12, (248, 241, 212)), (18, (250, 246, 224))]
    pos = [q for q, _ in stops]
    cols = np.array([c for _, c in stops], float)
    glow = np.stack([np.interp(e, pos, cols[:, k]) for k in range(3)], -1)
    g = 1 - smoothstep(e, 5, 16)
    base = cream * (1 - g[..., None]) + glow * g[..., None]
    halo = np.clip(ndi.gaussian_filter(page, 1.6 * K) * 1.7, 0, 1)
    base = base * (1 - halo[..., None] * .55) + np.array([60, 36, 12.]) * (halo[..., None] * .55)
    rgba = bevel_relief(page, PPM, bevel_mm=.3, dome_mm=.55, colors=REF_GOLD, shadow=.5, ambient=.58, shadow_off_mm=(.25, .35))
    comp(base, rgba)
    out = np.clip(base, 0, 255).astype('uint8')
    Image.fromarray(out).save(os.path.join(CACHE, name + '.png'))
    Image.fromarray(out).save(os.path.join(CACHE, name + '.jpg'), quality=quality, subsampling=0)
    lap('saved')
    return out


def build_small_ref():
    """ring (blue disc in an ivory-gold ring), rule and separator with beads - same metal as the clusters"""
    # ---- ring, 24 mm square, 30 px/mm
    ppm, Sz = 30, 24
    n = Sz * ppm
    c = n / 2
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    rr = np.hypot(xx - c + .5, yy - c + .5) / ppm

    def band(r0, r1):
        return np.clip(np.minimum((rr - r0) * ppm + .5, (r1 - rr) * ppm + .5), 0, 1)

    disc = np.clip((8.5 - rr) * ppm + .5, 0, 1)
    tex = mottle(n, n, 4, [(0, (30, 52, 80)), (.5, (50, 84, 120)), (1, (78, 118, 158))], big=260, mid=60, mix=.4, grain=2)
    tex *= (.55 + .45 * smoothstep(8.5 - rr, 0, 3.2))[..., None]
    out = np.zeros((n, n, 4), np.float32)
    out[..., :3] = tex
    out[..., 3] = disc * 255
    for r0, r1, bev in ((8.55, 10.25, .34), (7.85, 8.15, .12), (10.75, 11.1, .12), (11.45, 11.75, .1)):
        g = bevel_relief(band(r0, r1), ppm, bevel_mm=bev, dome_mm=.6, colors=REF_GOLD, shadow=.45, ambient=.6, shadow_off_mm=(.2, .28), shadow_blur_mm=.25)
        a_ = g[..., 3:].astype(np.float32) / 255
        out[..., :3] = out[..., :3] * (1 - a_) + g[..., :3] * a_
        out[..., 3:] = np.maximum(out[..., 3:], g[..., 3:])
    Image.fromarray(np.clip(out, 0, 255).astype('uint8'), 'RGBA').save(os.path.join(CACHE, 'ring.png'))

    # ---- rule / separator
    for name, w_mm, gap in (('rule', 171, 11.0), ('sep', 56, 9.0)):
        p_ = 20
        W_, H_ = int(w_mm * p_), int(9 * p_)
        m = np.zeros((H_, W_), np.float32)
        cy = H_ / 2
        yy2, xx2 = np.mgrid[0:H_, 0:W_].astype(np.float32)
        xm = (xx2 - W_ / 2) / p_
        ym = (yy2 - cy) / p_
        ln = (np.abs(xm) > gap / 2 + 3.4) & (np.abs(ym) < .24)
        taper = np.clip((w_mm / 2 - np.abs(xm)) / (w_mm * .22), 0, 1)
        m = np.maximum(m, ln * (np.abs(ym) < .24 * (.35 + .65 * taper)))
        m = np.maximum(m, ((np.abs(xm) > gap / 2 + 1.1) & (np.abs(xm) < gap / 2 + 3.0) & (np.abs(ym) < .13)).astype(np.float32))
        # lozenge in the middle
        m = np.maximum(m, ((np.abs(xm) / 1.9 + np.abs(ym) / 1.9) < 1).astype(np.float32))
        # beads either side
        for d in (2.8, 4.3, 5.6):
            m = np.maximum(m, ((np.hypot(np.abs(xm) - d, ym) < .42 - .06 * (d - 2.8))).astype(np.float32))
        m = ndi.gaussian_filter(m, .5)
        g = bevel_relief(np.pad(m, ((int(1 * p_), int(1 * p_)), (0, 0))), p_, bevel_mm=.16, dome_mm=.3, colors=REF_GOLD, shadow=.4, ambient=.6,
                         shadow_off_mm=(.15, .22), shadow_blur_mm=.2)
        Image.fromarray(g, 'RGBA').save(os.path.join(CACHE, name + '.png'))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('cover', 'all'):
        build_cover_bg()
    if what in ('frame', 'all'):
        build_frame_ref()
    if what in ('small', 'all'):
        build_small_ref()
