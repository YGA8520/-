"""Stroke / broad-nib helpers used to draw the Nusach Hebrew glyphs.

Every glyph is described as a set of centre-line paths.  A path is "swept" with a
flat, rotated rectangular nib (like a reed pen) and the swept areas are unioned
into clean, overlap-free outlines.  Changing the nib size gives the weights.
"""
import math

from shapely import affinity
from shapely.geometry import MultiPoint, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# ---------------------------------------------------------------- vertical metrics
UPM = 1000
TOP = 660          # flat top of the letters
LAMED_TOP = 905    # ascender of lamed
DESC = -245        # bottom of final letters (ך ן ף ץ)
XMID = 330         # visual middle used for bars / anchors


class Metrics:
    """Pen description for one weight."""

    def __init__(self, name, wght, a, b, angle, rnd, dots):
        self.name = name
        self.wght = wght
        self.a = a              # long side of the nib
        self.b = b              # short side of the nib
        self.angle = angle      # angle of the long side from horizontal (degrees)
        self.rnd = rnd          # corner rounding radius
        self.dots = dots        # radius of round dots (niqqud etc.)
        minx, miny, maxx, maxy = self.nib().bounds
        self.V = maxx - minx    # thickness of a vertical stem (real nib extent)
        self.H = maxy - miny    # thickness of a horizontal bar
        self.hv = self.V / 2
        self.hh = self.H / 2

    def nib(self):
        n = box(-self.a / 2, -self.b / 2, self.a / 2, self.b / 2)
        # a pen with softly rounded corners gives smoother curves than a razor-sharp one
        r = self.b * 0.42
        n = n.buffer(-r, join_style=1, resolution=6).buffer(r, join_style=1, resolution=6)
        return affinity.rotate(n, self.angle, origin=(0, 0))


# ---------------------------------------------------------------- path helpers
def lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def bez(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def arc(cx, cy, rx, ry, a0, a1, n=28):
    """Elliptical arc, angles in degrees (counter-clockwise, 0 = +x)."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def join(*paths):
    out = []
    for p in paths:
        p = list(p)
        if out and p and abs(out[-1][0] - p[0][0]) < 1e-6 and abs(out[-1][1] - p[0][1]) < 1e-6:
            p = p[1:]
        out.extend(p)
    return out


def line(*pts):
    return list(pts)


def densify(path, step=10.0):
    out = [path[0]]
    for p, q in zip(path, path[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        k = max(1, int(d // step))
        for i in range(1, k + 1):
            out.append(lerp(p, q, i / k))
    return out


# ---------------------------------------------------------------- geometry
def sweep(path, nib):
    """Minkowski sum of a polyline with a convex nib polygon."""
    nx = list(nib.exterior.coords)[:-1]
    pts = path if len(path) > 1 else path + path
    parts = []
    for p, q in zip(pts, pts[1:]):
        cloud = [(x + p[0], y + p[1]) for x, y in nx] + [(x + q[0], y + q[1]) for x, y in nx]
        parts.append(MultiPoint(cloud).convex_hull)
    return unary_union(parts)


def disc(cx, cy, r, n=40):
    return Polygon([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
                    for i in range(n)])


def poly(*pts):
    return Polygon(pts)


def diamond(cx, cy, rx, ry):
    return Polygon([(cx - rx, cy), (cx, cy + ry), (cx + rx, cy), (cx, cy - ry)])


def finish(geom, rnd, simplify=0.7):
    """Soften corners a little (printed-type feel) and clean the outline."""
    if rnd > 0:
        geom = geom.buffer(rnd, join_style=1, resolution=8).buffer(-2 * rnd, join_style=1, resolution=8) \
                   .buffer(rnd, join_style=1, resolution=8)
    geom = geom.simplify(simplify, preserve_topology=True)
    return geom


def polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in geom.geoms if g.geom_type == "Polygon"]


def draw_to_pen(geom, pen, dx=0.0):
    """Emit geometry to a fontTools pen: outer rings clockwise, holes counter-clockwise."""
    for pg in polygons(geom):
        pg = orient(pg, sign=-1.0)
        for ring in [pg.exterior] + list(pg.interiors):
            pts = list(ring.coords)[:-1]
            if len(pts) < 3:
                continue
            pen.moveTo((round(pts[0][0] + dx), round(pts[0][1])))
            for x, y in pts[1:]:
                pen.lineTo((round(x + dx), round(y)))
            pen.closePath()


# ---------------------------------------------------------------- strokes with flat ends
INF = 10 ** 6


def _extend(p, q, d):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy) or 1.0
    return (q[0] + dx / n * d, q[1] + dy / n * d)


def S(path, ymin=None, ymax=None, e0=0.0, e1=0.0):
    """A stroke whose ends are extended and then cut flat at ymin / ymax."""
    pts = list(path)
    if e0:
        pts.insert(0, _extend(pts[1], pts[0], e0))
    if e1:
        pts.append(_extend(pts[-2], pts[-1], e1))
    return (pts, (-INF if ymin is None else ymin, INF if ymax is None else ymax))


def _reach(p, q, y):
    """Extend p->q beyond q until the line reaches height y."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    if abs(dy) < 1e-9:
        return q
    t = (y - q[1]) / dy
    if t <= 0:
        return q
    return (q[0] + dx * t, y)


def reach(path, ys=None, ye=None):
    """Extend the first / last segment of a path until it reaches height ys / ye."""
    pts = list(path)
    if ys is not None:
        pts.insert(0, _reach(pts[1], pts[0], ys))
    if ye is not None:
        pts.append(_reach(pts[-2], pts[-1], ye))
    return pts
