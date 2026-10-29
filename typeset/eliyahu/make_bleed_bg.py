"""Background with bleed for the print version of the colour page.

python make_bleed_bg.py bg-color.jpg bg-color-bleed.jpg [bleed_mm]

The page is 80 x 110 mm and bg-color.jpg (1414 x 2000) is stretched over it; the bleed (3 mm round) is made by
mirroring the artwork over the edge - only marble, the bars of the frame and its corners lie at the edge, so the
mirror is seamless - and has the same px per mm, so the bleed image covers (80 + 2b) x (110 + 2b) mm exactly.
"""
import sys
import cv2

W_MM, H_MM = 80.0, 110.0

def main(src, dst, bleed=3.0):
    img = cv2.imread(src); h, w = img.shape[:2]
    bx = round(w / W_MM * float(bleed)); by = round(h / H_MM * float(bleed))
    out = cv2.copyMakeBorder(img, by, by, bx, bx, cv2.BORDER_REFLECT)
    cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print('bleed image', out.shape[1], 'x', out.shape[0], 'pad', bx, by)

if __name__ == '__main__':
    main(*sys.argv[1:4])
