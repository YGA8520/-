"""Clean background for the colour version of the Eliyahu page, made from the client's reference design.

python clean_bg.py ref.jpg out.jpg [debug_dir]

* The picture (father and son, left side of the cartouche) is replaced by the mirrored right side of
  the cartouche - the cartouche is symmetric about the axis of the page - blended over a soft seam.
* The inside of the cartouche (title, subtitle, small text, the two swirls) is filled with the parchment
  itself: the parchment pixels outside the text are spread in by a normalised Gaussian blur, so the
  vignette of the parchment stays and no text is left.
* The vertical credit line on the left margin is covered by the mirrored right margin.
The text panel of the reference is left as it is: the page draws its own panel over it.
"""
import sys, os
import numpy as np, cv2

AXIS = 710                      # x of the axis of symmetry of the cartouche (px of the 1414 x 2000 reference)

def feather_mask(h, w, x0, y0, x1, y1, f):
    m = np.zeros((h, w), np.float32); m[y0:y1, x0:x1] = 1
    k = f * 2 + 1
    return cv2.GaussianBlur(m, (k, k), f / 2)

def mirror_patch(img, x0, y0, x1, y1, f, axis=AXIS):
    """replace img[y0:y1, x0:x1] by its mirror image about x = axis (soft edge of f px)"""
    h, w = img.shape[:2]
    mir = img.copy()
    xs = np.arange(w); src = np.clip(2 * axis - xs, 0, w - 1)
    mir[:, :] = img[:, src]
    m = feather_mask(h, w, x0, y0, x1, y1, f)[..., None]
    return (img * (1 - m) + mir * m).astype(np.uint8)

def fill_inside(img, poly, text_thr, grow):
    """fill the inside of a polygon with the parchment (normalised blur of the pixels that are not text)"""
    h, w = img.shape[:2]
    inside = np.zeros((h, w), np.uint8); cv2.fillPoly(inside, [np.array(poly, np.int32)], 1)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A = lab[..., 0], lab[..., 1]
    # text = darker than the parchment or clearly red / gold; grown so the anti-aliased edge goes too
    bg_L = cv2.GaussianBlur(L, (0, 0), 25)
    text = ((L < bg_L - text_thr) | (A > 140)).astype(np.uint8) & inside
    text = cv2.dilate(text, np.ones((grow, grow), np.uint8))
    good = (inside & (1 - text)).astype(np.float32)
    out = img.astype(np.float32)
    fill = np.zeros_like(out)
    for s in (6, 14, 30, 60):        # coarse-to-fine: small holes take the near colour, big ones the far
        num = cv2.GaussianBlur(out * good[..., None], (0, 0), s)
        den = cv2.GaussianBlur(good, (0, 0), s)[..., None]
        est = num / np.maximum(den, 1e-4)
        fill = np.where((den > 0.02) & (fill.sum(2, keepdims=True) == 0), est, fill)
    # the whole inside is replaced by a smooth version (no text remains), with fine grain from the
    # original parchment where it was not text
    smooth = cv2.GaussianBlur(fill, (0, 0), 3)
    res = np.where(good[..., None] > 0, out, smooth)
    res = cv2.GaussianBlur(res, (0, 0), 1.2) * 0.5 + res * 0.5
    # the parchment has almost no texture: a wide blur removes the last traces of the text and keeps the vignette
    res = cv2.GaussianBlur(res, (0, 0), 9)
    m = cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 2)[..., None]
    return (out * (1 - m) + res * m).clip(0, 255).astype(np.uint8), text

def main(src, dst, dbg=None):
    img = cv2.imread(src)
    h, w = img.shape[:2]
    # 1. the picture: lower left part of the cartouche and the marble under it
    img = mirror_patch(img, 270, 140, 640, 378, 14)
    # 2. the credit on the left margin
    img = mirror_patch(img, 22, 1480, 100, 1740, 10, axis=w // 2)
    # 3. inside of the cartouche (frame inner edge, read off the reference)
    poly = [(372, 28), (1048, 28), (1062, 60), (1062, 255), (1048, 282), (372, 282), (358, 255), (358, 60)]
    img, text = fill_inside(img, poly, 14, 9)
    cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if dbg:
        os.makedirs(dbg, exist_ok=True)
        cv2.imwrite(os.path.join(dbg, 'text-mask.png'), text * 255)
        cv2.imwrite(os.path.join(dbg, 'top.png'), img[:420])

if __name__ == '__main__':
    main(*sys.argv[1:4])
