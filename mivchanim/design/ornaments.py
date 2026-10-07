"""Gold scroll-work (vector construction -> masks) in the style of the reference cover.

Primitives: curl (tapered spiral), S-scroll (stem with a curl at each end), acanthus leaf, fleur.
"""
import math

import numpy as np

from art import Canvas, bez, leaf, mirror_x, spiral


def unit(v):
    v = np.asarray(v, float)
    return v / (np.hypot(*v) + 1e-9)


def curl_from(start, tangent, r0, turns=1.6, side=1, ratio=.14, n=220):
    """spiral that leaves `start` along `tangent`, curling to `side` (+1 = to the left of the travel direction in screen space)"""
    start = np.asarray(start, float)
    t = unit(tangent)
    nrm = np.array([t[1], -t[0]]) * side if False else np.array([-t[1], t[0]]) * side
    c = start + nrm * r0
    a0 = math.atan2(start[1] - c[1], start[0] - c[0])
    tang_pos = np.array([-math.sin(a0), math.cos(a0)])
    direction = 1 if np.dot(tang_pos, t) > 0 else -1
    return spiral(c[0], c[1], r0, r0 * ratio, a0, turns, direction, n)


def stroke(cv, path, widths, round_ends=True):
    path = np.asarray(path, float)
    L = len(path)
    ts = np.linspace(0, 1, L)
    xs = np.linspace(0, 1, len(widths))
    ws = np.interp(ts, xs, widths)
    d = np.gradient(path, axis=0)
    ln = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    nrm = np.stack([-d[:, 1] / ln, d[:, 0] / ln], 1)
    poly = np.vstack([path + nrm * (ws / 2)[:, None], (path - nrm * (ws / 2)[:, None])[::-1]])
    cv.poly(poly)
    if round_ends:
        cv.circle(*path[0], ws[0] / 2)
        cv.circle(*path[-1], max(ws[-1] / 2, .12))


def s_scroll(cv, A, dirA, rA, sideA, B, dirB, rB, sideB, w=(.5, 1.6, 2.0, 1.4, .5), k=.38, turnsA=1.55, turnsB=1.55, ratio=.15):
    """S-shaped stem from A to B; curl at each end. dirA: direction of the stem at A (into the stem);
    dirB: direction of travel at B (out of the stem, into curl B). Returns the full centre-line."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    dA, dB = unit(dirA), unit(dirB)
    L = np.hypot(*(B - A))
    stem = bez(A, A + dA * L * k, B - dB * L * k, B, 70)
    cA = curl_from(A, -dA, rA, turnsA, sideA, ratio)[::-1]
    cB = curl_from(B, dB, rB, turnsB, sideB, ratio)
    path = np.vstack([cA, stem[1:], cB[1:]])
    stroke(cv, path, w)
    return path


def branch_leaf(cv, path, t, length, width, side=1, bend=.1, angle=.9):
    """leaf growing off `path` at fractional position t, leaning `angle` rad from the path direction"""
    i = int(t * (len(path) - 2))
    p = path[i]
    d = unit(path[i + 1] - path[i - 1])
    ca, sa = math.cos(angle * side), math.sin(angle * side)
    dd = np.array([d[0] * ca - d[1] * sa, d[0] * sa + d[1] * ca])
    cv.poly(leaf(p, p + dd * length, width, bend * side))


def fleur(cv, x, y, h, w):
    """small three-petal fleur pointing up from (x,y)"""
    cv.poly(leaf((x, y), (x, y - h), w * .55, 0))
    for s in (-1, 1):
        cv.poly(leaf((x, y - h * .12), (x + s * w * .8, y - h * .78), w * .5, -.26 * s))
        cv.poly(leaf((x, y), (x + s * w * 1.0, y - h * .22), w * .36, .3 * s))
    cv.circle(x, y + .1, w * .22)


def acanthus(cv, base, tip, width, bend=.15, teeth=4, side=1):
    """serrated acanthus-like leaf: a main leaf plus small lobes"""
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    cv.poly(leaf(base, tip, width, bend * side))
    d = tip - base
    for i in range(1, teeth + 1):
        t = i / (teeth + 1)
        p = base + d * t
        cv.poly(leaf(p, p + np.array([-d[1], d[0]]) * .0 + unit(d) * np.hypot(*d) * .22 + np.array([-d[1], d[0]]) / np.hypot(*d) * side * width * .9, width * .42, .1 * side))


def arm(cv, P0, P1, P2, P3, curl_r, curl_side, w=(.7, 1.9, 2.1, 1.5, .5), turns=1.7, ratio=.17, n=70):
    """tapered bezier stem ending in a volute (spiral) that curls to `curl_side` (+1 left of travel, -1 right)"""
    stem = bez(P0, P1, P2, P3, n)
    t = unit(stem[-1] - stem[-6])
    cu = curl_from(stem[-1], t, curl_r, turns, curl_side, ratio)
    path = np.vstack([stem, cu[1:]])
    stroke(cv, path, w)
    return path


# ---------------------------------------------------------------- pieces
def petal(cv, base, tip, width, bend=0.0, n=60):
    """teardrop petal: thin at the base, widest at 62 % of the length"""
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    d = tip - base
    L = np.hypot(*d)
    u = d / L
    nv = np.array([-u[1], u[0]])
    t = np.linspace(0, 1, n)
    prof = (t ** .75) * ((1 - t) ** .55)
    prof = prof / prof.max() * width / 2
    axis = base[None] + np.outer(t, d) + nv[None] * (bend * L * np.sin(np.pi * t))[:, None]
    cv.poly(np.vstack([axis + nv[None] * prof[:, None], (axis - nv[None] * prof[:, None])[::-1]]))


def shell_fan(cv, x, y, R=11.0, ribs=7, spread=150):
    """scallop-shell fan hanging below (x,y): fluted half disc with a scalloped edge"""
    n = 120
    th = np.linspace(math.radians(90 - spread / 2), math.radians(90 + spread / 2), n)
    # scalloped radius
    rr = R * (1 + .045 * np.cos(th * ribs * 180 / spread * 1.0))
    pts = [(x, y)] + [(x + r * math.cos(t), y + r * math.sin(t)) for r, t in zip(rr, th)]
    cv.poly(pts)
    # flutes
    for k in range(ribs + 1):
        a = math.radians(90 - spread / 2 + spread * k / ribs)
        cv.line([(x + R * .18 * math.cos(a), y + R * .18 * math.sin(a)), (x + R * .93 * math.cos(a), y + R * .93 * math.sin(a))], .38, fill=0)
    cv.circle(x, y, 1.6)


def under_arch(w=68, h=40, ppm=24):
    """cartouche under the pointed bottom of the title panel: scallop fan + two rising volute arms"""
    cv = Canvas(w, h, ppm)
    ax = w / 2
    shell_fan(cv, ax, 12.0, R=12.5, ribs=7, spread=150)
    for s in (-1, 1):
        X = lambda dx, s=s: ax + s * dx
        wd = (1.4, 2.4, 2.2, 1.3, .8, .5, .36, .3)
        p = arm(cv, (X(4.0), 12.0), (X(9), 14.0), (X(15), 8.8), (X(23), 6.0), 5.0, s, w=wd, turns=1.9, ratio=.2)
        for t, ln, w2 in ((.28, 6.4, 2.2), (.5, 5.6, 1.8)):
            i = int(t * (len(p) - 2))
            petal(cv, p[i], p[i] + np.array([-s * ln * .3, ln]), w2, .12 * s)
        q = arm(cv, (X(8.2), 19.4), (X(11), 21.5), (X(14), 20.2), (X(17.5), 16.8), 3.0, s, w=(1.0, 1.7, 1.6, 1.0, .6, .4, .3, .26), turns=1.9, ratio=.2)
        for dx in (9.6, 12.2):
            cv.circle(X(dx), 11.6 - (dx - 9.6) * .4, .5)
    return cv


def flourish_h(w=90, h=12, ppm=24):
    """horizontal divider: central diamond, two scrolls"""
    cv = Canvas(w, h, ppm)
    ax, cy = w / 2, h / 2
    for s in (-1, 1):
        X = lambda dx, s=s: ax + s * dx
        p = arm(cv, (X(3.2), cy), (X(9), cy - 2.4), (X(17), cy + 1.8), (X(25), cy - .6), 2.0, -s, w=(.4, 1.0, 1.1, .8, .3), turns=1.6)
        arm(cv, (X(9.5), cy + .1), (X(11), cy + 2.4), (X(14), cy + 3.3), (X(16.5), cy + 2.3), 1.1, s, w=(.35, .7, .8, .6, .3), turns=1.5, ratio=.24)
        branch_leaf(cv, p, .3, 3.2, 1.0, -s, .1, .9)
    d = 2.3
    cv.poly([(ax, cy - d), (ax + d * .85, cy), (ax, cy + d), (ax - d * .85, cy)])
    return cv


def side_vine(w=24, h=130, ppm=24):
    """vertical filigree for the LEFT side (mirror for the right): fleur on top, alternating volutes down a stem"""
    cv = Canvas(w, h, ppm)
    ax = w * .5
    fleur(cv, ax, 14, 12.5, 5.4)
    # stem: gentle S, drawn as two arms
    p1 = arm(cv, (ax, 14), (ax - 5, 26), (ax + 5, 40), (ax, 54), 4.2, -1, w=(.9, 2.0, 2.0, 1.7, .6), turns=1.55)
    p2 = arm(cv, (ax, 56), (ax + 5, 68), (ax - 4, 82), (ax + 1, 96), 5.0, 1, w=(.9, 2.0, 2.0, 1.7, .6), turns=1.6)
    for t, sd in ((.25, 1), (.5, -1), (.72, 1)):
        branch_leaf(cv, p1, t, 5.0, 1.9, sd, .12, 1.0)
    for t, sd in ((.22, -1), (.46, 1), (.7, -1)):
        branch_leaf(cv, p2, t, 5.2, 2.0, sd, .12, 1.0)
    # side curls
    for path, tt, sd, r in ((p1, .36, 1, 2.6), (p2, .34, -1, 2.9), (p2, .62, 1, 2.4)):
        i = int(tt * (len(path) - 2))
        P = path[i]
        arm(cv, P, P + np.array([sd * 3, -1.2]), P + np.array([sd * 6, -.6]), P + np.array([sd * 7.5, 1.8]), r, -sd, w=(.6, 1.3, 1.4, 1.0, .4), turns=1.5, ratio=.2)
    return cv


def corner_scroll(w=36, h=36, ppm=24):
    """quarter ornament for the top-left corner of a frame (mirror for the others)"""
    cv = Canvas(w, h, ppm)
    p = arm(cv, (3, 33), (3, 20), (12, 8), (28, 5), 4.4, 1, w=(.8, 2.0, 2.3, 1.6, .5), turns=1.7)
    for t in (.25, .45, .62):
        branch_leaf(cv, p, t, 6.5, 2.3, -1, .1, .8)
    arm(cv, (6, 28), (7, 22), (11, 17), (16, 16), 2.2, -1, w=(.5, 1.2, 1.3, .9, .4), turns=1.5)
    return cv
