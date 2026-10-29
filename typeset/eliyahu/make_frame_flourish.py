"""Side flourish for the title of the colour page, cut out of the border frame of the client's reference design.

python make_frame_flourish.py ref.jpg out.png [debug.png]

The piece is the acanthus leaf that sweeps to the right from the lower left corner of the border. It lies over
the bars of the frame and over the marble, so it is cut out with GrabCut (colour models of leaf and background
plus the edges between them), started from hand-placed regions read off a gridded enlargement of the reference:
ellipses over the body of the leaf (probable / sure leaf), the marble above it, the bars to its right and the rows
under it (sure background). The leaf keeps its own shading; it is enlarged 4x for print, given a soft edge, and
its root (left, where it grows out of the corner) fades out.
"""
import sys
import numpy as np, cv2

X0, Y0, X1, Y1 = 76, 1896, 170, 1980     # working box in the 1414 x 2000 reference
U = 4
FADE = 13                               # px of the reference over which the root fades in

def P(x, y):                            # reference coordinates -> enlarged crop
    return int((x - X0) * U), int((y - Y0) * U)

def main(src, dst, dbg=None):
    ref = cv2.imread(src)
    crop = cv2.resize(ref[Y0:Y1, X0:X1], None, fx=U, fy=U, interpolation=cv2.INTER_CUBIC)
    h, w = crop.shape[:2]
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    cv2.ellipse(mask, P(118, 1932), (34 * U, 16 * U), -12, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.ellipse(mask, P(130, 1952), (22 * U, 9 * U), 0, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.ellipse(mask, P(115, 1932), (22 * U, 7 * U), -15, 0, 360, cv2.GC_FGD, -1)
    mask[:P(0, 1906)[1], :] = cv2.GC_BGD
    mask[:, P(162, 0)[0]:] = cv2.GC_BGD
    mask[P(0, 1974)[1]:, :] = cv2.GC_BGD
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(crop, mask, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.float32)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5)))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9)))
    a = cv2.GaussianBlur(fg, (0, 0), 1.6)
    ramp = np.clip(np.arange(w) / (FADE * U), 0, 1); a *= (ramp * ramp * (3 - 2 * ramp))[None, :]
    ys, xs = np.where(a > 0.02)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    out = np.dstack([crop, (a * 255).astype(np.uint8)])[sl]
    cv2.imwrite(dst, out)
    print('flourish', out.shape[1], 'x', out.shape[0])
    if dbg:
        al = out[..., 3:4] / 255.0
        cv2.imwrite(dbg, (out[..., :3] * al + np.array((232, 246, 251)) * (1 - al)).astype(np.uint8))

if __name__ == '__main__':
    main(*sys.argv[1:4])
