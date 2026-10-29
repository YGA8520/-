"""Divider for the colour page made from the swirl that flanks the title of the client's reference design.

python make_swirl_divider.py ref.jpg out.png [out.svg]

The right swirl of the reference (x 932-1014, y 62-110) is cut out, its alpha is taken from the distance to the
parchment colour, enlarged 10x and sharpened into a clean edge (smoothstep on the enlarged alpha); the colour is
the flat gold of the swirl. The divider = the swirl mirrored | small diamond | the swirl, as the two swirls
face each other around the title of the reference.
With out.svg the divider is also traced (potracer) into a vector path - one gold shape that every divider and
the ornament of the title use, so it prints sharp and at exactly the same size everywhere.
"""
import sys
import numpy as np, cv2

BOX = (932, 62, 1014, 110)
UP = 10

def swirl(ref):
    x0, y0, x1, y1 = BOX
    c = ref[y0:y1, x0:x1].astype(np.float32)
    paper = np.median(np.concatenate([c[:3].reshape(-1, 3), c[-3:].reshape(-1, 3)]), 0)
    d = np.linalg.norm(c - paper, axis=2)
    ink = c[d > np.percentile(d, 92)]
    gold = np.median(ink, 0)
    a = np.clip(d / np.linalg.norm(gold - paper), 0, 1)
    a = cv2.resize(a, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    a = cv2.GaussianBlur(a, (0, 0), UP * 0.6)
    t = np.clip((a - 0.38) / 0.24, 0, 1); a = t * t * (3 - 2 * t)          # clean edge
    ys, xs = np.where(a > 0.02)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return a, gold

def to_svg(alpha, gold_bgr, dst):
    import potrace
    bm = potrace.Bitmap(alpha > 0.5)
    path = bm.trace(turdsize=20, alphamax=1.0, opticurve=True, opttolerance=0.3)
    d = []
    h, w = alpha.shape
    for curve in path:
        sp = curve.start_point
        ends = [sp] + [seg.end_point for seg in curve.segments]
        if max(p.x for p in ends) - min(p.x for p in ends) >= w - 1 and max(p.y for p in ends) - min(p.y for p in ends) >= h - 1:
            continue                                   # potracer adds the frame of the bitmap: not part of the drawing
        d.append('M%.1f,%.1f' % (sp.x, sp.y))
        for seg in curve.segments:
            if seg.is_corner:
                d.append('L%.1f,%.1fL%.1f,%.1f' % (seg.c.x, seg.c.y, seg.end_point.x, seg.end_point.y))
            else:
                d.append('C%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (seg.c1.x, seg.c1.y, seg.c2.x, seg.c2.y, seg.end_point.x, seg.end_point.y))
        d.append('Z')
    h, w = alpha.shape
    b, g, r = (int(v) for v in gold_bgr)
    open(dst, 'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
                         '<path fill="#%02x%02x%02x" fill-rule="evenodd" d="%s"/></svg>\n' % (w, h, w, h, r, g, b, ''.join(d)))

def main(src, dst, svg=None):
    ref = cv2.imread(src)
    a, gold = swirl(ref)
    h, w = a.shape
    gap = int(w * 0.16); dia = int(h * 0.30)
    W = 2 * w + 2 * gap + dia
    alpha = np.zeros((h, W), np.float32)
    alpha[:, :w] = a[:, ::-1]                                 # left: mirrored
    alpha[:, W - w:] = a                                      # right: as in the reference
    cy, cx = h // 2 + int(h * 0.06), W // 2                   # small diamond, on the line of the swirl tails
    pts = np.array([(cx, cy - dia // 2), (cx + dia // 2, cy), (cx, cy + dia // 2), (cx - dia // 2, cy)], np.int32)
    m = np.zeros((h, W), np.uint8); cv2.fillPoly(m, [pts], 255, lineType=cv2.LINE_AA)
    alpha = np.maximum(alpha, m / 255.0)
    out = np.zeros((h, W, 4), np.uint8)
    out[..., :3] = gold.astype(np.uint8); out[..., 3] = (alpha * 255).astype(np.uint8)
    cv2.imwrite(dst, out)
    if svg: to_svg(alpha, gold, svg)
    print('divider', W, 'x', h, 'gold BGR', gold.astype(int))

if __name__ == '__main__':
    main(*sys.argv[1:4])
