"""Procedural art for the booklet: marbled blue, cream marble, embossed gold ornaments.

Everything is generated from code (no third-party images) and cached as PNG in build/art.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, 'build', 'art')
os.makedirs(CACHE, exist_ok=True)


# ------------------------------------------------------------------ noise & textures
def fbm(h, w, scale, octaves=5, persistence=.55, rng=None):
    """fractal value noise in [0,1]; scale = size in px of the biggest feature"""
    rng = rng or np.random.default_rng(1)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    s = scale
    for _ in range(octaves):
        gh, gw = max(2, int(h / s) + 3), max(2, int(w / s) + 3)
        g = rng.random((gh, gw))
        z = ndi.zoom(g, (h / (gh - 2) * 1.0, w / (gw - 2) * 1.0), order=3, mode='nearest')[:h, :w]
        if z.shape != (h, w):
            z = np.pad(z, ((0, h - z.shape[0]), (0, w - z.shape[1])), mode='edge')
        out += z * amp
        tot += amp
        amp *= persistence
        s = max(2, s / 2)
    out /= tot
    out = (out - out.min()) / (out.max() - out.min() + 1e-9)
    return out


def warp(img, strength, scale, rng):
    """domain-warp a 2-D or 3-D array (smoky swirls)"""
    h, w = img.shape[:2]
    dx = (fbm(h, w, scale, 4, .5, rng) - .5) * strength
    dy = (fbm(h, w, scale, 4, .5, rng) - .5) * strength
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    coords = [np.clip(yy + dy, 0, h - 1), np.clip(xx + dx, 0, w - 1)]
    if img.ndim == 2:
        return ndi.map_coordinates(img, coords, order=1)
    return np.dstack([ndi.map_coordinates(img[..., c], coords, order=1) for c in range(img.shape[2])])


def ramp(v, stops):
    """map v in [0,1] through colour stops [(pos,(r,g,b))...] -> HxWx3 float 0..255"""
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], float)
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(v, pos, cols[:, ch])
    return out


def blue_marble(w, h, seed=3, dark=1.0):
    rng = np.random.default_rng(seed)
    base = fbm(h, w, max(w, h) / 2.6, 6, .56, rng)
    base = warp(base, max(w, h) * .09, max(w, h) / 3.2, rng)
    cloud = fbm(h, w, max(w, h) / 7, 5, .5, rng)
    v = .62 * base + .38 * cloud
    v = (v - v.min()) / (v.max() - v.min())
    v = np.clip((v - .5) * 1.5 + .5, 0, 1)
    col = ramp(v, [(0, (5, 14, 32)), (.28, (10, 29, 58)), (.55, (22, 54, 98)), (.8, (46, 92, 148)), (1, (96, 140, 190))])
    # fine grain
    grain = (rng.random((h, w)) - .5) * 7
    col += grain[..., None]
    # vignette
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    col *= (1 - .38 * np.clip(r - .35, 0, 1) ** 1.4 * dark)[..., None]
    return np.clip(col, 0, 255).astype('uint8')


def blue_panel(w, h, seed=11):
    """lighter cloudy blue for the title panel"""
    rng = np.random.default_rng(seed)
    base = fbm(h, w, max(w, h) / 2.2, 6, .58, rng)
    base = warp(base, max(w, h) * .07, max(w, h) / 3, rng)
    v = (base - base.min()) / (base.max() - base.min())
    v = np.clip((v - .5) * 1.3 + .5, 0, 1)
    col = ramp(v, [(0, (14, 40, 78)), (.4, (28, 68, 116)), (.75, (52, 102, 154)), (1, (92, 142, 190))])
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h * .38) / (h * .62))
    col *= (1 - .45 * np.clip(r - .25, 0, 1) ** 1.3)[..., None]
    col += ((rng.random((h, w)) - .5) * 6)[..., None]
    return np.clip(col, 0, 255).astype('uint8')


def cream_marble(w, h, seed=5, tint=1.0):
    rng = np.random.default_rng(seed)
    base = fbm(h, w, max(w, h) / 3, 5, .5, rng)
    base = warp(base, max(w, h) * .06, max(w, h) / 4, rng)
    soft = (base - base.min()) / (base.max() - base.min())
    # thin veins: ridged noise
    n = warp(fbm(h, w, max(w, h) / 5, 5, .55, rng), max(w, h) * .1, max(w, h) / 6, rng)
    ridge = 1 - np.abs(n - .5) * 2
    veins = np.clip((ridge - .972) * 30, 0, 1) ** 1.5
    n2 = warp(fbm(h, w, max(w, h) / 9, 4, .55, rng), max(w, h) * .08, max(w, h) / 8, rng)
    ridge2 = 1 - np.abs(n2 - .5) * 2
    veins2 = np.clip((ridge2 - .978) * 34, 0, 1)
    col = ramp(soft, [(0, (233, 217, 172)), (.5, (244, 233, 198)), (1, (252, 246, 224))])
    vein_col = np.array([222., 200., 150.])
    vv = (veins * .38 * tint + veins2 * .22 * tint)[..., None]
    col = col * (1 - vv) + vein_col * vv
    col -= ((1 - soft) * 6)[..., None]
    col += ((rng.random((h, w)) - .5) * 4)[..., None]
    # warm edge darkening
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    col *= (1 - .10 * np.clip(r - .5, 0, 1))[..., None] * np.array([1, .985, .94])
    return np.clip(col, 0, 255).astype('uint8')


# ------------------------------------------------------------------ shapes
def taper_poly(pts, w0, w1=None, profile=None):
    """polygon around a polyline with tapering width. pts: Nx2 array. width goes w0 -> w1 along the path."""
    pts = np.asarray(pts, float)
    n = len(pts)
    t = np.linspace(0, 1, n)
    if w1 is None:
        w1 = w0
    w = w0 + (w1 - w0) * t
    if profile is not None:
        w = w * profile(t)
    d = np.gradient(pts, axis=0)
    ln = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    nrm = np.stack([-d[:, 1] / ln, d[:, 0] / ln], 1)
    left = pts + nrm * (w / 2)[:, None]
    right = pts - nrm * (w / 2)[:, None]
    return np.vstack([left, right[::-1]])


def spiral(cx, cy, r0, r1, a0, turns, direction=1, n=220, squash=1.0):
    """spiral from radius r0 to r1 around (cx,cy); a0 start angle (rad); direction +1 ccw (screen: y down => visually cw)"""
    t = np.linspace(0, 1, n)
    r = r0 * (r1 / r0) ** t
    a = a0 + direction * turns * 2 * math.pi * t
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a) * squash], 1)


def bez(p0, p1, p2, p3, n=60):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def leaf(base, tip, width, bend=.0, n=50):
    """pointed leaf from base to tip"""
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    d = tip - base
    L = np.hypot(*d)
    u = d / L
    nv = np.array([-u[1], u[0]])
    t = np.linspace(0, 1, n)
    prof = np.sin(np.pi * t ** .8) ** .9 * width / 2
    axis = base[None] + np.outer(t, d) + nv[None] * (bend * L * np.sin(np.pi * t))[:, None]
    left = axis + nv[None] * prof[:, None]
    right = axis - nv[None] * prof[:, None]
    return np.vstack([left, right[::-1]])


def mirror_x(poly, axis_x):
    p = np.array(poly, float)
    p[:, 0] = 2 * axis_x - p[:, 0]
    return p


class Canvas:
    """mask canvas drawn at S x supersampling; coordinates in mm"""
    def __init__(self, w_mm, h_mm, px_per_mm, ss=2):
        self.w_mm, self.h_mm, self.ppm, self.ss = w_mm, h_mm, px_per_mm, ss
        self.W, self.H = int(round(w_mm * px_per_mm)), int(round(h_mm * px_per_mm))
        self.im = Image.new('L', (self.W * ss, self.H * ss), 0)
        self.d = ImageDraw.Draw(self.im)
        self.k = px_per_mm * ss

    def poly(self, pts, fill=255):
        p = [(float(x) * self.k, float(y) * self.k) for x, y in pts]
        if len(p) >= 3:
            self.d.polygon(p, fill=fill)

    def circle(self, x, y, r, fill=255):
        self.d.ellipse([(x - r) * self.k, (y - r) * self.k, (x + r) * self.k, (y + r) * self.k], fill=fill)

    def line(self, pts, width, fill=255):
        p = [(float(x) * self.k, float(y) * self.k) for x, y in pts]
        self.d.line(p, fill=fill, width=max(1, int(width * self.k)), joint='curve')

    def stroke_poly(self, pts, width, fill=255, closed=False):
        pts = list(pts) + ([pts[0]] if closed else [])
        self.line(pts, width, fill)
        r = width / 2
        for x, y in (pts[0], pts[-1]):
            self.circle(x, y, r, fill)

    def mask(self):
        return np.asarray(self.im.resize((self.W, self.H), Image.LANCZOS), dtype=float) / 255


# ------------------------------------------------------------------ embossed gold
GOLD = [(0, (36, 22, 6)), (.16, (88, 58, 16)), (.34, (156, 114, 38)), (.52, (206, 164, 74)), (.7, (234, 205, 125)),
        (.86, (250, 234, 168)), (1, (255, 250, 222))]
IVORY = [(0, (60, 44, 20)), (.2, (120, 92, 44)), (.4, (186, 152, 82)), (.6, (222, 196, 130)), (.8, (244, 228, 176)), (1, (255, 250, 232))]


def emboss(mask, ppm, height_mm=.9, light=(-.55, -.65, .5), colors=GOLD, shadow=.55, shadow_off=(.5, .7), spec=.55, bevel=1.0):
    """mask float 0..1 (HxW) -> RGBA uint8 with a metallic bevel, sheen and drop shadow"""
    h, w = mask.shape
    s = ppm
    # rounded height profile: blurred mask at two scales
    r1, r2 = max(.5, height_mm * s * .55), max(1., height_mm * s * 1.6)
    H = .62 * ndi.gaussian_filter(mask, r1) + .38 * ndi.gaussian_filter(mask, r2)
    H = H ** .9
    gy, gx = np.gradient(H)
    k = bevel * (height_mm * s) * 2.2
    nx, ny = -gx * k, -gy * k
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    L = np.array(light, float)
    L /= np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    hv = L + np.array([0, 0, 1.0])
    hv /= np.linalg.norm(hv)
    sp = np.clip(nx * hv[0] + ny * hv[1] + nz * hv[2], 0, 1) ** 36
    flat = np.clip(.5 + (diff - .62) * 1.55, 0, 1)
    # cavity darkening towards the edges of thin parts
    edge = np.clip(1 - ndi.gaussian_filter(mask, max(.7, s * .22)), 0, 1) * mask
    v = np.clip(flat + sp * spec - edge * .45, 0, 1)
    # slow sheen across the piece (brushed metal feel)
    yy, xx = np.mgrid[0:h, 0:w]
    sheen = .5 + .5 * np.sin((xx * .6 + yy * .35) / (s * 7))
    v = np.clip(v + (sheen - .5) * .08 * mask, 0, 1)
    col = ramp(v, colors)
    a = np.clip(ndi.gaussian_filter(mask, .6) * 1.15, 0, 1)
    a = np.where(mask > .5, np.maximum(a, mask), a)
    rgba = np.dstack([col, a * 255])
    out = np.zeros((h, w, 4))
    # drop shadow
    if shadow > 0:
        sh = ndi.gaussian_filter(mask, s * .5)
        sh = ndi.shift(sh, (shadow_off[1] * s, shadow_off[0] * s), order=1)
        out[..., 3] = sh * 255 * shadow
        out[..., :3] = (8, 6, 4)
    # composite gold over shadow
    A = rgba[..., 3:] / 255
    out[..., :3] = rgba[..., :3] * A + out[..., :3] * (1 - A)
    out[..., 3:] = np.maximum(rgba[..., 3:], out[..., 3:])
    return np.clip(out, 0, 255).astype('uint8')


def save(arr, name):
    p = os.path.join(CACHE, name)
    Image.fromarray(arr).save(p)
    return p
