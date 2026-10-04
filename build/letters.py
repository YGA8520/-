"""Hebrew letter skeletons.

Each function receives the pen metrics `m` and returns (paths, shapes):
  paths  - centre-line polylines (or S(...) strokes with flat ends) swept with the nib
  shapes - extra filled shapely polygons (dots, serifs ...)
All x/y are in font units, y up, baseline = 0.
"""
from glyphlib import (TOP as T, LAMED_TOP, DESC, S, arc, bez, join, lerp, line, reach)

OV = 54      # overhang of a top bar past the stem (dalet, he, het, tav)
GAP = 84     # gap between a top bar and a detached leg (he, qof)


def _w(m, w0):
    """Heavier weights get a little wider."""
    return w0 + (m.V - 62) * 1.1


def _tc(m):
    return T - m.hh


# ----------------------------------------------------------------- helpers
def hb(m, x0, x1, ytop):
    y = ytop - m.hh
    return [(x0 + m.hv, y), (x1 - m.hv, y)]


def vb(m, xl, ytop, ybot):
    """Vertical stem with flat top and flat foot; xl = outer left edge."""
    x = xl + m.hv
    return S([(x, ytop - m.hh), (x, ybot + m.hh)], ymin=ybot, ymax=ytop, e0=m.H, e1=m.H)


def c_shape(m, x0, xr, r1, r2):
    tc, bc = _tc(m), m.hh
    return join(line((x0, tc), (xr - r1, tc)),
                arc(xr - r1, tc - r1, r1, r1, 90, 0),
                line((xr, tc - r1), (xr, bc + r2)),
                arc(xr - r2, bc + r2, r2, r2, 0, -90),
                line((xr - r2, bc), (x0, bc)))


def shoulder(m, x0, xr, r, ybot):
    """Top bar + rounded shoulder + stem down to outer y = ybot (flat foot)."""
    tc = _tc(m)
    path = join(line((x0, tc), (xr - r, tc)),
                arc(xr - r, tc - r, r, r, 90, 0),
                line((xr, tc - r), (xr, ybot + m.hh)))
    return S(path, ymin=ybot, e1=m.H)


# ----------------------------------------------------------------- letters
def alef(m):
    W = _w(m, 600)
    hv, hh = m.hv, m.hh
    x0, x1 = hv + 36, W - hv - 36
    d0, d1 = (x0, T), (x1, 0)
    D = lambda t: lerp(d0, d1, t)
    xr = W - hv - 4
    xl = hv + 4
    jr, jl = D(0.56), D(0.42)
    right = S(join(line((xr, T - hh), (xr, 0.64 * T)),
                   bez((xr, 0.64 * T), (xr, 0.50 * T), (jr[0] + 46, jr[1] + 36), jr)),
              ymax=T, e0=m.H)
    left = S(join(line((xl, hh), (xl, 0.34 * T)),
                  bez((xl, 0.34 * T), (xl, 0.48 * T), (jl[0] - 46, jl[1] - 36), jl)),
             ymin=0, e0=m.H)
    return [S(reach([d0, d1], ys=T + hh, ye=-hh), ymin=0, ymax=T), right, left], []


def bet(m):
    W = _w(m, 560)
    xr = W - m.hv
    return [c_shape(m, m.hv, xr, 96, 18),
            line((xr, m.hh), (xr + 26, m.hh))], []


def gimel(m):
    W = _w(m, 520)
    xr = W - m.hv
    tc = _tc(m)
    x0 = 120 + m.hv
    body = S(join(line((x0, tc), (xr - 100, tc)),
                  arc(xr - 100, tc - 100, 100, 100, 90, 0),
                  line((xr, tc - 100), (xr, m.hh))), ymin=0, e1=m.H)
    leg = join(bez((xr, 0.50 * T), (xr - 70, 0.36 * T), (150, 0.20 * T), (92 + m.hv, m.hh + 10)),
               line((92 + m.hv, m.hh), (170, m.hh)))
    return [body, leg], []


def dalet(m):
    W = _w(m, 540)
    return [hb(m, 0, W, T), vb(m, W - OV - m.V, T, 0)], []


def he(m):
    W = _w(m, 560)
    return [hb(m, 0, W, T),
            vb(m, W - OV - m.V, T, 0),
            vb(m, 46, T - m.H - GAP, 0)], []


def vav(m):
    xl = 62
    return [vb(m, xl, T, 0), hb(m, 0, xl + m.V, T)], []


def zayin(m):
    W = _w(m, 360)
    xl = (W - m.V) / 2 + 24
    return [hb(m, 0, W, T), vb(m, xl, T, 0)], []


def het(m):
    W = _w(m, 560)
    return [hb(m, 0, W, T), vb(m, 0, T, 0), vb(m, W - OV - m.V, T, 0)], []


def tet(m):
    W = _w(m, 560)
    xr = W - m.hv
    xl = m.hv
    cy = 0.40 * T
    ry = cy - m.hh
    rx = (xr - xl) / 2
    cx = (xr + xl) / 2
    tc = _tc(m)
    body = join(line((xl, tc), (xl, cy)),
                arc(cx, cy, rx, ry, 180, 360, 40),
                line((xr, cy), (xr, tc - 150)),
                bez((xr, tc - 150), (xr, tc - 60), (xr - 50, tc - 10), (xr - 130, tc - 2)))
    return [S(body, ymax=T, e0=m.H)], []


def yod(m):
    W = _w(m, 200)
    xr = W - m.hv
    tc = _tc(m)
    ybot = 0.40 * T
    body = join(line((m.hv, tc), (xr - 56, tc)),
                arc(xr - 56, tc - 56, 56, 56, 90, 0, 16),
                line((xr, tc - 56), (xr, ybot + m.hh)))
    return [S(body, ymin=ybot, e1=m.H)], []


def kaf(m):
    W = _w(m, 520)
    return [c_shape(m, m.hv, W - m.hv, 112, 122)], []


def kaf_final(m):
    W = _w(m, 480)
    return [shoulder(m, m.hv, W - m.hv, 118, DESC)], []


def lamed(m):
    W = _w(m, 500)
    xr = W - m.hv
    tc = _tc(m)
    xa = m.hv + 6
    asc = S([(xa, LAMED_TOP - m.hh), (xa, tc)], ymax=LAMED_TOP, e0=m.H)
    body = join(line((xa, tc), (xr - 110, tc)),
                arc(xr - 110, tc - 110, 110, 110, 90, 0),
                line((xr, tc - 110), (xr, 0.50 * T)),
                bez((xr, 0.50 * T), (xr, 0.28 * T), (xr - 90, 0.20 * T), (xr - 150, 0.15 * T)),
                line((xr - 150, 0.15 * T), (xr - 150, m.hh)))
    return [asc, S(body, ymin=0, e1=m.H)], []


def mem(m):
    W = _w(m, 600)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xs = m.hv + 62                        # top of the left stem
    main = join(line((xs, tc), (xr - 110, tc)),
                arc(xr - 110, tc - 110, 110, 110, 90, 0),
                line((xr, tc - 110), (xr, bc + 120)),
                arc(xr - 120, bc + 120, 120, 120, 0, -90),
                line((xr - 120, bc), (262, bc)))
    leg = S([(xs, tc), (m.hv + 34, bc)], ymin=0, e1=m.H)
    return [main, leg], []


def mem_final(m):
    W = _w(m, 560)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    box = join(line((m.hv, tc), (xr - 120, tc)),
               arc(xr - 120, tc - 120, 120, 120, 90, 0),
               line((xr, tc - 120), (xr, bc)),
               line((xr, bc), (m.hv, bc)),
               line((m.hv, bc), (m.hv, tc)))
    return [box], []


def nun(m):
    W = _w(m, 470)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xt = 118 + m.hv                       # left end of the (shorter) top bar
    body = join(line((xt, tc), (xr - 100, tc)),
                arc(xr - 100, tc - 100, 100, 100, 90, 0),
                line((xr, tc - 100), (xr, bc + 100)),
                arc(xr - 100, bc + 100, 100, 100, 0, -90),
                line((xr - 100, bc), (m.hv, bc)))
    hook = S([(xt, tc), (xt, 0.46 * T + m.hh)], ymin=0.46 * T, ymax=T, e1=m.H)
    return [body, hook], []


def nun_final(m):
    xl = 62
    return [vb(m, xl, T, DESC), hb(m, 0, xl + m.V, T)], []


def samekh(m):
    W = _w(m, 540)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    r = 120
    box = join(line((m.hv + r, tc), (xr - r, tc)),
               arc(xr - r, tc - r, r, r, 90, 0),
               line((xr, tc - r), (xr, bc + r)),
               arc(xr - r, bc + r, r, r, 0, -90),
               line((xr - r, bc), (m.hv + r, bc)),
               arc(m.hv + r, bc + r, r, r, 270, 180),
               line((m.hv, bc + r), (m.hv, tc - r)),
               arc(m.hv + r, tc - r, r, r, 180, 90))
    return [box], []


def ayin(m):
    W = _w(m, 600)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xa = m.hv + 4
    xb = xa + 130
    left = S(reach([(xa + 24, T), (xb, bc + 14)], ys=T + m.hh), ymax=T)
    bowl = S(join(bez((xb - 20, bc + 6), (xb + 120, bc - 2), (xr - 20, bc + 10), (xr, 0.46 * T)),
                  line((xr, 0.46 * T), (xr, tc))), ymax=T, e1=m.H)
    return [left, bowl], []


def pe(m):
    W = _w(m, 540)
    xr = W - m.hv
    tc = _tc(m)
    body = c_shape(m, m.hv, xr, 110, 100)
    curl = join(line((m.hv, tc), (m.hv, 0.60 * T)),
                bez((m.hv, 0.60 * T), (m.hv, 0.43 * T), (m.hv + 60, 0.37 * T), (m.hv + 190, 0.37 * T)))
    return [body, curl], []


def pe_final(m):
    W = _w(m, 540)
    xr = W - m.hv
    tc = _tc(m)
    body = S(join(line((m.hv, tc), (xr - 110, tc)),
                  arc(xr - 110, tc - 110, 110, 110, 90, 0),
                  line((xr, tc - 110), (xr, DESC + m.hh))), ymin=DESC, e1=m.H)
    bowl = join(line((m.hv, tc), (m.hv, 0.52 * T)),
                bez((m.hv, 0.52 * T), (m.hv, 0.30 * T), (xr - 150, 0.17 * T), (xr, 0.17 * T)))
    return [body, bowl], []


def tsadi(m):
    hh_ = m.hh
    W = _w(m, 560)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xa = m.hv + 6
    xb = W - m.hv - 40
    diag = S(reach([(xa + 34, T), (xb - 34, 0)], ys=T + hh_, ye=-hh_), ymin=0, ymax=T)
    arm = S(join(line((xr - 4, tc), (xr - 4, 0.70 * T)),
                 bez((xr - 4, 0.70 * T), (xr - 4, 0.54 * T), (xr - 70, 0.50 * T), (xr - 120, 0.44 * T))),
            ymax=T, e0=m.H)
    base = line((xa + 10, bc), (xb + 30, bc))
    return [diag, arm, base], []


def tsadi_final(m):
    W = _w(m, 560)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xa = m.hv + 6
    xj = W * 0.58
    diag = S(reach([(xa + 34, T), (xj, 0.30 * T)], ys=T + m.hh), ymax=T)
    stem = S([(xj, 0.34 * T), (xj, DESC + m.hh)], ymin=DESC, e1=m.H)
    arm = S(join(line((xr - 4, tc), (xr - 4, 0.70 * T)),
                 bez((xr - 4, 0.70 * T), (xr - 4, 0.50 * T), (xj + 80, 0.40 * T), (xj + 8, 0.32 * T))),
            ymax=T, e0=m.H)
    return [diag, stem, arm], []


def qof(m):
    W = _w(m, 560)
    xr = W - m.hv
    tc = _tc(m)
    top = join(line((m.hv, tc), (xr - 120, tc)),
               arc(xr - 120, tc - 120, 120, 120, 90, 0),
               line((xr, tc - 120), (xr, 0.52 * T)),
               bez((xr, 0.52 * T), (xr, 0.40 * T), (xr - 50, 0.32 * T), (xr - 140, 0.30 * T)))
    leg = vb(m, 22, T - m.H - GAP, DESC)
    return [top, leg], []


def resh(m):
    W = _w(m, 500)
    return [shoulder(m, m.hv, W - m.hv, 126, 0)], []


def shin(m):
    W = _w(m, 660)
    xr = W - m.hv
    tc, bc = _tc(m), m.hh
    xa = m.hv
    xm = W * 0.52
    r = 120
    left = S(join(line((xa, tc), (xa, bc + r)),
                  arc(xa + r, bc + r, r, r, 180, 270),
                  line((xa + r, bc), (xr - r, bc)),
                  arc(xr - r, bc + r, r, r, 270, 360),
                  line((xr, bc + r), (xr, tc))), ymax=T, e0=m.H, e1=m.H)
    mid = S(join(line((xm, tc), (xm, 0.40 * T)),
                 bez((xm, 0.40 * T), (xm, 0.24 * T), (xm - 40, 0.12 * T), (xm - 80, bc + 4))),
            ymax=T, e0=m.H)
    return [left, mid], []


def tav(m):
    W = _w(m, 640)
    foot = 96
    return [hb(m, foot, W, T),
            vb(m, foot, T, 0),
            vb(m, W - OV - m.V, T, 0),
            hb(m, 0, foot + m.V, m.H)], []


# name -> (function, unicode, lsb, rsb)
LETTERS = {
    "alef": (alef, 0x05D0, 44, 44),
    "bet": (bet, 0x05D1, 50, 46),
    "gimel": (gimel, 0x05D2, 50, 56),
    "dalet": (dalet, 0x05D3, 50, 50),
    "he": (he, 0x05D4, 50, 50),
    "vav": (vav, 0x05D5, 56, 56),
    "zayin": (zayin, 0x05D6, 56, 56),
    "het": (het, 0x05D7, 50, 50),
    "tet": (tet, 0x05D8, 50, 50),
    "yod": (yod, 0x05D9, 56, 56),
    "kaf_final": (kaf_final, 0x05DA, 50, 50),
    "kaf": (kaf, 0x05DB, 50, 50),
    "lamed": (lamed, 0x05DC, 50, 50),
    "mem_final": (mem_final, 0x05DD, 50, 50),
    "mem": (mem, 0x05DE, 50, 50),
    "nun_final": (nun_final, 0x05DF, 56, 56),
    "nun": (nun, 0x05E0, 50, 50),
    "samekh": (samekh, 0x05E1, 50, 50),
    "ayin": (ayin, 0x05E2, 46, 46),
    "pe_final": (pe_final, 0x05E3, 50, 50),
    "pe": (pe, 0x05E4, 50, 50),
    "tsadi_final": (tsadi_final, 0x05E5, 50, 50),
    "tsadi": (tsadi, 0x05E6, 46, 46),
    "qof": (qof, 0x05E7, 50, 50),
    "resh": (resh, 0x05E8, 50, 50),
    "shin": (shin, 0x05E9, 50, 50),
    "tav": (tav, 0x05EA, 50, 50),
}
