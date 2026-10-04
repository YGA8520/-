"""Hebrew letter skeletons - calligraphic version.

Each function receives the pen metrics `m` and returns (paths, shapes).
 * paths  - centre-lines swept with the broad nib (W(...) = variable-width strokes)
 * shapes - explicitly drawn wedges: the hooked flag at the left end of a top bar, the
            flared spur at the foot of every stem and the pointed tails of bottom bars
x is relative (the glyph is moved to its side bearing afterwards), y up, baseline 0.
"""
from glyphlib import (TOP as T, LAMED_TOP, DESC, INF, S, W, arc, bez, join, lerp, line, plen, polyfrom, reach)

GAP = 140     # gap between a top bar and a detached leg (he, qof)


def _w(m, w0):
    """Heavier weights get a little wider."""
    return w0 + (m.V - 65) * 0.9


def _tc(m):
    return T - m.hh


# ----------------------------------------------------------------- explicit wedges
def FLAG(m, x0, drop=54, run=74):
    """Hooked left end of a top bar whose centre-line starts at x0.  It continues the slanted
    pen cut of the bar down into a pointed hook with a concave inner edge."""
    H = m.H
    lobe = m.hv + 6
    A = (x0 + 8, T - 2)
    B = (x0 - lobe - 6, T - H - drop)
    C = (x0 + run, T - H + 6)
    return polyfrom(bez(A, (x0 - lobe * 0.9, T - 34), (x0 - lobe - 14, T - H + 8), B, 16),
                    bez(B, (x0 - lobe + 12, T - H - drop + 24), (x0 + 16, T - H - 2), C, 14),
                    [(x0 + run, T - 30)])


def FOOT(m, x, ys, spur=100):
    """Flared, pointed foot at the bottom of a stem centred on x (sweeps to the left).

    The polygon starts inside the stem, so the stem's own edge flows into the flare."""
    ex = m.hv * 1.10
    top_y = ys + 150
    tip = (x - ex - spur, 34)
    pts_r = [(x + ex * 0.80, top_y), (x + ex, ys + 40), (x + ex, 22), (x + ex - 14, 0)]
    bottom = bez(pts_r[-1], (x - ex * 0.1, -3), (x - ex - spur * 0.55, 4), tip, 14)
    top = bez(tip, (x - ex - spur * 0.42, 50), (x - ex * 0.90, top_y - 120), (x - ex * 0.80, top_y), 20)
    return polyfrom(pts_r, bottom, top)


def TAIL(m, xb, L=72):
    """Pointed spur at the left end of a bottom bar whose centre-line starts at xb."""
    H = m.H
    tip = (xb - L, 32)
    top = bez((xb + 50, H), (xb + 6, H - 2), (xb - L * 0.55, H * 0.62), tip, 14)
    bottom = bez(tip, (xb - L * 0.45, 8), (xb - 8, 0), (xb + 50, 0), 10)
    return polyfrom(top, bottom)


def HEEL(m, x):
    """Small pointed heel at the bottom-right of bet (x = outer right edge)."""
    H = m.H
    return polyfrom([(x - 30, H), (x - 6, H * 0.8)],
                    bez((x - 6, H * 0.8), (x + 20, H * 0.62), (x + 40, 30), (x + 48, 12), 10),
                    [(x + 20, 0), (x - 30, 0)])


STEM_FOOT_Y = 0.20 * T


def _prof(L):
    return [(0, 1.0), (min(90.0, L * 0.25), 0.90), (L * 0.96, 1.10)]


def flat_top(m, pts):
    """Prepend a point so that a stroke starting at the top gets a flat cut at y = T."""
    ext = reach(list(pts[:2]), ys=T + m.hh)[0]
    return [ext] + list(pts)


def stem(m, x, ytop, ys=STEM_FOOT_Y, spur=100, tip=False):
    """Free-standing stem: thin below its head, swelling into a flared foot."""
    p = line((x, ytop), (x, ys + 60))
    L = plen(p)
    st = W(p, prof=_prof(L), s_len=90 if tip else 0, s_k=0.32 if tip else 1.0)
    return [st], [FOOT(m, x, ys, spur)]


def bar_stem(m, x0, xr, R, spur=100, ys=STEM_FOOT_Y):
    """Flagged top bar, big rounded shoulder, stem and flared foot."""
    tc = _tc(m)
    bar = join(line((x0, tc), (xr - R, tc)), arc(xr - R, tc - R, R, R, 90, 0, 28))
    sp = line((xr, tc - R), (xr, ys + 60))
    L = plen(sp)
    return [W(bar), W(sp, prof=_prof(L))], [FLAG(m, x0), FOOT(m, xr, ys, spur)]


def cat(*parts):
    paths, shapes = [], []
    for p, s in parts:
        paths += p
        shapes += s
    return paths, shapes


# ----------------------------------------------------------------- letters
def resh(m):
    w = _w(m, 350)
    return bar_stem(m, 0, w, 132)


def dalet(m):
    w = _w(m, 380)
    tc = _tc(m)
    st = stem(m, w - 78, tc)
    return [W(line((0, tc), (w, tc)))] + st[0], [FLAG(m, 0)] + st[1]


def he(m):
    w = _w(m, 410)
    return cat(bar_stem(m, 0, w, 124), stem(m, 74, T - m.H - GAP, tip=True))


def het(m):
    w = _w(m, 410)
    return cat(bar_stem(m, 0, w, 124, spur=96), stem(m, 40, _tc(m), spur=34))


def tav(m):
    w = _w(m, 470)
    return cat(bar_stem(m, 40, w, 124, spur=80), stem(m, 120, _tc(m), spur=215))


def vav(m):
    tc = _tc(m)
    head = W(line((-46, tc), (0, tc)))
    p = bez((0, tc), (8, tc - 90), (6, 0.30 * T), (-24, m.hh + 12), 24)
    return [head, W(p, e_len=200, e_k=0.30)], [FLAG(m, -46, 42, 54)]


def zayin(m):
    tc = _tc(m)
    bar = W(line((0, tc), (200, tc)))
    st = W(join(line((130, tc), (124, 0.34 * T)), bez((124, 0.34 * T), (120, 0.2 * T), (112, 0.12 * T), (96, m.hh + 12), 18)),
           e_len=210, e_k=0.16)
    return [bar, st], [FLAG(m, 0, 44, 60)]


def tet(m):
    w = _w(m, 400)
    tc = _tc(m)
    cy = 0.40 * T
    ry = cy - m.hh
    rx = w / 2
    cx = w / 2
    body = join(line((0, tc), (0, cy)),
                arc(cx, cy, rx, ry, 180, 360, 40),
                line((w, cy), (w, tc - 190)),
                bez((w, tc - 190), (w, tc - 80), (w - 40, tc - 4), (w - 128, tc - 6), 20))
    return [W(body, e_len=120, e_k=0.26)], [FLAG(m, 0, 40, 56)]


def yod(m):
    tc = _tc(m)
    p = join(line((0, tc), (58, tc)),
             bez((58, tc), (112, tc + 2), (128, tc - 40), (116, tc - 94), 18),
             bez((116, tc - 94), (108, tc - 170), (100, 0.54 * T), (84, 0.42 * T), 18))
    return [W(p, e_len=170, e_k=0.2)], [FLAG(m, 0, 40, 56)]


def kaf(m):
    w = _w(m, 420)
    tc, bc = _tc(m), m.hh
    R1, R2 = 140, 150
    p = join(line((0, tc), (w - R1, tc)),
             arc(w - R1, tc - R1, R1, R1, 90, 0, 28),
             bez((w, tc - R1), (w - 12, 0.5 * T), (w - 12, 0.5 * T), (w, bc + R2), 24),
             arc(w - R2, bc + R2, R2, R2, 0, -90, 28),
             line((w - R2, bc), (96, bc)))
    return [W(p)], [FLAG(m, 0), TAIL(m, 96)]


def kaf_final(m):
    w = _w(m, 370)
    tc = _tc(m)
    R = 140
    p = join(line((0, tc), (w - R, tc)),
             arc(w - R, tc - R, R, R, 90, 0, 28),
             bez((w, tc - R), (w, 0.30 * T), (w - 6, 0.0), (w - 32, DESC + 24), 28))
    return [W(p, e_len=200, e_k=0.30)], [FLAG(m, 0)]


def lamed(m):
    w = _w(m, 360)
    tc = _tc(m)
    R = 120
    asc = W(bez((18, LAMED_TOP - 6), (8, T + 120), (-2, T + 20), (-4, tc - 24), 24), s_len=150, s_k=0.20)
    body = join(line((-4, tc - 6), (20, tc)),
                line((20, tc), (w - R, tc)),
                arc(w - R, tc - R, R, R, 90, 0, 28),
                line((w, tc - R), (w, 0.46 * T)),
                bez((w, 0.46 * T), (w, 0.20 * T), (w - 90, 0.10 * T), (w - 170, m.hh + 10), 24))
    return [asc, W(body, e_len=130, e_k=0.2)], []


def mem(m):
    w = _w(m, 440)
    tc, bc = _tc(m), m.hh
    R1, R2 = 130, 130
    xs = 74
    main = join(line((xs, tc), (w - R1, tc)),
                arc(w - R1, tc - R1, R1, R1, 90, 0, 28),
                bez((w, tc - R1), (w - 12, 0.5 * T), (w - 12, 0.5 * T), (w, bc + R2), 24),
                arc(w - R2, bc + R2, R2, R2, 0, -90, 28),
                line((w - R2, bc), (214, bc)))
    leg_p = bez((xs + 4, tc), (xs - 4, 0.55 * T), (xs - 16, 0.34 * T), (xs - 22, STEM_FOOT_Y + 60), 24)
    L = plen(leg_p)
    return [W(main), W(leg_p, prof=_prof(L))], [FLAG(m, xs, 46, 56), FOOT(m, xs - 22, STEM_FOOT_Y, 66),
                                                 TAIL(m, 214, 56)]


def mem_final(m):
    w = _w(m, 440)
    tc, bc = _tc(m), m.hh
    R = 140
    box = join(line((0, tc), (w - R, tc)),
               arc(w - R, tc - R, R, R, 90, 0, 28),
               line((w, tc - R), (w, bc)),
               line((w, bc), (0, bc)),
               line((0, bc), (0, tc)))
    return [W(box)], [FLAG(m, 0, 46, 60)]


def nun(m):
    w = _w(m, 380)
    tc, bc = _tc(m), m.hh
    R1, R2 = 120, 130
    k = m.V - 65
    xt = 158 + k * 1.1                     # the top bar starts well inside the letter
    xb = 70 - k * 0.2
    p = join(line((xt, tc), (w - R1, tc)),
             arc(w - R1, tc - R1, R1, R1, 90, 0, 28),
             line((w, tc - R1), (w, bc + R2)),
             arc(w - R2, bc + R2, R2, R2, 0, -90, 28),
             line((w - R2, bc), (xb, bc)),
             bez((xb, bc), (xb - 40, bc), (xb - 62, bc + 26), (xb - 58, 0.32 * T), 22))
    return [W(p, e_len=130, e_k=0.34)], [FLAG(m, xt, 30, 56)]


def nun_final(m):
    tc = _tc(m)
    head = W(line((-46, tc), (0, tc)))
    p = bez((0, tc), (8, tc - 90), (6, 0.30 * T), (-10, DESC + 40), 24)
    return [head, W(p, e_len=210, e_k=0.30)], [FLAG(m, -46, 42, 54)]


def samekh(m):
    import math
    w = _w(m, 410)
    tc, bc = _tc(m), m.hh
    cx, cy = w / 2, T / 2
    rx, ry = w / 2, (tc - bc) / 2
    pts = []
    n = 2.9
    for i in range(0, 76):
        a = math.radians(105 + i * 360 / 72)
        c, s = math.cos(a), math.sin(a)
        pts.append((cx + rx * (abs(c) ** (2 / n)) * (1 if c >= 0 else -1),
                    cy + ry * (abs(s) ** (2 / n)) * (1 if s >= 0 else -1)))
    return [W(pts)], []


def ayin(m):
    w = _w(m, 450)
    tc, bc = _tc(m), m.hh
    lp = bez((0, tc), (20, 0.62 * T), (60, 0.32 * T), (100, bc + 16), 22)
    left = W(flat_top(m, lp), clip=(-INF, T))
    bowl = join(bez((84, bc + 10), (150, bc - 4), (w - 10, bc + 14), (w, 0.50 * T), 22), line((w, 0.50 * T), (w, tc)))
    return [left, W(bowl, e_len=0)], []


def pe(m):
    w = _w(m, 420)
    tc, bc = _tc(m), m.hh
    R1, R2 = 130, 120
    p = join(line((0, tc), (w - R1, tc)),
             arc(w - R1, tc - R1, R1, R1, 90, 0, 28),
             line((w, tc - R1), (w, bc + R2)),
             arc(w - R2, bc + R2, R2, R2, 0, -90, 28),
             line((w - R2, bc), (76, bc)))
    curl = join(line((6, tc - 30), (6, 0.60 * T)),
                bez((6, 0.60 * T), (6, 0.43 * T), (70, 0.36 * T), (w - 120, 0.36 * T), 22))
    return [W(p), W(curl, e_len=120, e_k=0.5)], [FLAG(m, 0), TAIL(m, 76)]


def pe_final(m):
    w = _w(m, 420)
    tc = _tc(m)
    R = 130
    p = join(line((0, tc), (w - R, tc)),
             arc(w - R, tc - R, R, R, 90, 0, 28),
             bez((w, tc - R), (w, 0.30 * T), (w - 6, 0.0), (w - 32, DESC + 24), 28))
    bowl = join(line((6, tc - 30), (6, 0.54 * T)),
                bez((6, 0.54 * T), (6, 0.30 * T), (w - 150, 0.18 * T), (w, 0.18 * T), 24))
    return [W(p, e_len=200, e_k=0.30), W(bowl)], [FLAG(m, 0)]


def tsadi(m):
    w = _w(m, 440)
    tc, bc = _tc(m), m.hh
    dp = bez((0, tc), (80, 0.62 * T), (210, 0.34 * T), (w - 70, bc + 14), 24)
    diag = W(flat_top(m, dp), clip=(-INF, T))
    arm = join(line((w - 20, tc), (w - 24, 0.68 * T)),
               bez((w - 24, 0.68 * T), (w - 26, 0.52 * T), (w - 100, 0.50 * T), (w - 170, 0.42 * T), 22))
    base = line((w - 200, bc), (w - 40, bc))
    return [diag, W(arm, s_len=70, s_k=0.34), W(base)], [TAIL(m, w - 200, 52)]


def tsadi_final(m):
    w = _w(m, 440)
    tc = _tc(m)
    xj = w * 0.56
    dp = bez((0, tc), (70, 0.62 * T), (xj - 50, 0.36 * T), (xj, 0.28 * T), 22)
    diag = W(flat_top(m, dp), clip=(-INF, T))
    st = W(join(line((xj, 0.34 * T), (xj + 2, 0.0)), bez((xj + 2, 0.0), (xj, DESC + 90), (xj - 6, DESC + 40), (xj - 18, DESC + 20), 20)),
           e_len=220, e_k=0.30)
    arm = W(join(line((w - 20, tc), (w - 24, 0.68 * T)),
                 bez((w - 24, 0.68 * T), (w - 26, 0.50 * T), (xj + 80, 0.40 * T), (xj + 8, 0.32 * T), 22)),
            s_len=70, s_k=0.34)
    return [diag, st, arm], []


def qof(m):
    w = _w(m, 410)
    tc = _tc(m)
    R = 130
    top = join(line((0, tc), (w - R, tc)),
               arc(w - R, tc - R, R, R, 90, 0, 28),
               line((w, tc - R), (w, 0.50 * T)),
               bez((w, 0.50 * T), (w, 0.38 * T), (w - 50, 0.30 * T), (w - 150, 0.28 * T), 22))
    leg = join(line((52, T - m.H - GAP), (52, 0.10 * T)), bez((52, 0.10 * T), (52, DESC + 120), (46, DESC + 70), (32, DESC + 16), 20))
    return [W(top, e_len=130, e_k=0.3), W(leg, s_len=80, s_k=0.34, e_len=220, e_k=0.30)], [FLAG(m, 0)]


def shin(m):
    w = _w(m, 540)
    tc, bc = _tc(m), m.hh
    R = 130
    xm = w * 0.50
    left = join(line((0, tc), (0, bc + R)),
                arc(R, bc + R, R, R, 180, 270, 24),
                line((R, bc), (w - R, bc)),
                arc(w - R, bc + R, R, R, 270, 360, 24),
                line((w, bc + R), (w, tc)))
    mid = join(line((xm, tc), (xm, 0.42 * T)),
               bez((xm, 0.42 * T), (xm, 0.24 * T), (xm - 40, 0.12 * T), (xm - 86, bc + 6), 20))
    return [W(left, s_len=70, s_k=0.40, e_len=70, e_k=0.40), W(mid, s_len=70, s_k=0.40)], []


def alef(m):
    w = _w(m, 480)
    tc, bc = _tc(m), m.hh
    d0, d1 = (30, tc - 4), (w - 40, bc + 4)
    D = lambda t: lerp(d0, d1, t)
    jr, jl = D(0.56), D(0.42)
    diag = W([d0, d1], s_len=70, s_k=0.5, e_len=70, e_k=0.5)
    right = join(line((w - 8, tc), (w - 8, 0.64 * T)),
                 bez((w - 8, 0.64 * T), (w - 8, 0.50 * T), (jr[0] + 54, jr[1] + 40), jr, 22))
    left = join(line((6, bc + 10), (6, 0.34 * T)),
                bez((6, 0.34 * T), (6, 0.48 * T), (jl[0] - 54, jl[1] - 40), jl, 22))
    return [diag, W(right, s_len=80, s_k=0.38), W(left, s_len=80, s_k=0.38)], []


def bet(m):
    w = _w(m, 420)
    tc, bc = _tc(m), m.hh
    R = 112
    p = join(line((0, tc), (w - R, tc)),
             arc(w - R, tc - R, R, R, 90, 0, 28),
             line((w, tc - R), (w, bc)),
             line((w, bc), (76, bc)))
    return [W(p)], [FLAG(m, 0), TAIL(m, 76), HEEL(m, w + m.hv)]


def gimel(m):
    w = _w(m, 340)
    tc = _tc(m)
    R = 110
    x0 = 56
    bar = join(line((x0, tc), (w - R, tc)), arc(w - R, tc - R, R, R, 90, 0, 28))
    sp = line((w, tc - R), (w, STEM_FOOT_Y + 60))
    L = plen(sp)
    leg = join(bez((w - 4, 0.50 * T), (w - 60, 0.36 * T), (96, 0.24 * T), (36, m.hh + 12), 24))
    return [W(bar), W(sp, prof=_prof(L)), W(leg, e_len=110, e_k=0.22)], [FLAG(m, x0), FOOT(m, w, STEM_FOOT_Y, 84)]


# name -> (function, unicode, lsb, rsb)
LETTERS = {
    "alef": (alef, 0x05D0, 40, 40),
    "bet": (bet, 0x05D1, 42, 40),
    "gimel": (gimel, 0x05D2, 44, 44),
    "dalet": (dalet, 0x05D3, 44, 44),
    "he": (he, 0x05D4, 44, 44),
    "vav": (vav, 0x05D5, 52, 52),
    "zayin": (zayin, 0x05D6, 50, 50),
    "het": (het, 0x05D7, 44, 44),
    "tet": (tet, 0x05D8, 44, 44),
    "yod": (yod, 0x05D9, 52, 52),
    "kaf_final": (kaf_final, 0x05DA, 44, 44),
    "kaf": (kaf, 0x05DB, 44, 44),
    "lamed": (lamed, 0x05DC, 44, 44),
    "mem_final": (mem_final, 0x05DD, 44, 44),
    "mem": (mem, 0x05DE, 44, 44),
    "nun_final": (nun_final, 0x05DF, 52, 52),
    "nun": (nun, 0x05E0, 44, 44),
    "samekh": (samekh, 0x05E1, 44, 44),
    "ayin": (ayin, 0x05E2, 42, 42),
    "pe_final": (pe_final, 0x05E3, 44, 44),
    "pe": (pe, 0x05E4, 44, 44),
    "tsadi_final": (tsadi_final, 0x05E5, 44, 44),
    "tsadi": (tsadi, 0x05E6, 42, 42),
    "qof": (qof, 0x05E7, 44, 44),
    "resh": (resh, 0x05E8, 44, 44),
    "shin": (shin, 0x05E9, 44, 44),
    "tav": (tav, 0x05EA, 44, 44),
}

# kept for extras.py (digits / punctuation still use bars and stems)
OV = 54


def hb(m, x0, x1, ytop):
    y = ytop - m.hh
    return [(x0 + m.hv, y), (x1 - m.hv, y)]


def vb(m, xl, ytop, ybot):
    x = xl + m.hv
    return S([(x, ytop - m.hh), (x, ybot + m.hh)], ymin=ybot, ymax=ytop, e0=m.H, e1=m.H)
