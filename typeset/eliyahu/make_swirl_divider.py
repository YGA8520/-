"""Divider for the colour page made from the swirl that flanks the title of the client's reference design.

python make_swirl_divider.py ref.jpg out.png

The right swirl of the reference (x 932-1014, y 62-110) is cut out, its alpha is taken from the distance to the
parchment colour, enlarged 10x and sharpened into a clean edge (smoothstep on the enlarged alpha); the colour is
the flat gold of the swirl. The divider = the swirl mirrored | small diamond | the swirl, as the two swirls
face each other around the title of the reference.
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

def main(src, dst):
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
    print('divider', W, 'x', h, 'gold BGR', gold.astype(int))

if __name__ == '__main__':
    main(*sys.argv[1:3])
