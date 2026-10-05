"""Cut the design assets out of the example PDF into ready-to-place PNGs."""
import pymupdf, io
from PIL import Image

import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else 'example.pdf'
OUT = 'assets/'
doc = pymupdf.open(SRC)

def xobj(xref):
    pix = pymupdf.Pixmap(doc, xref)
    if pix.alpha: pix = pymupdf.Pixmap(pix, 0)
    if pix.n not in (1, 3):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    im = Image.frombytes('RGB' if pix.n == 3 else 'L', (pix.width, pix.height), pix.samples).convert('RGB')
    # soft mask
    for pg in doc:
        for info in pg.get_images(full=True):
            if info[0] == xref and info[1]:
                sm = pymupdf.Pixmap(doc, info[1])
                m = Image.frombytes('L', (sm.width, sm.height), sm.samples)
                if m.size != im.size: m = m.resize(im.size)
                im = im.convert('RGBA'); im.putalpha(m)
                return im
    return im.convert('RGBA')

def save(im, name): im.save(OUT + name, optimize=True); print(name, im.size)

PAGE_W, PAGE_H = 595.32, 841.92

# --- side borders: visible part is the left 34.06pt (of 231pt) of the strip image, scaled to 855.75pt tall
strip = xobj(293)                       # 176 x 652
vis_w = round(strip.width * 34.06 / 231.0)          # ~26 px
vis_h = round(strip.height * PAGE_H / 855.75)       # ~641 px
left_part = strip.crop((0, 2, vis_w, vis_h - 2))   # drop the 1px dark edge rows
big = left_part.resize((vis_w * 4, vis_h * 4), Image.LANCZOS)
save(big.rotate(180), 'border_left.png')      # left edge is the strip rotated 180deg
save(big, 'border_right.png')

# --- logo plaque (bottom part of the tall plaque image) and page-number badge (top part)
plaque = xobj(288)                      # 1298 x 2480 -> 242.36 x 463.06 pt
top_cut = round(plaque.height * 286.8 / 463.06)
def fade(im, k):            # the example draws these three at 50% opacity
    a = im.getchannel('A').point(lambda v: int(v * k)); im = im.copy(); im.putalpha(a); return im
save(fade(plaque.crop((0, top_cut, plaque.width, plaque.height)), 0.5), 'logo_plaque.png')   # 242.36 x 176.26 pt
badge_h = round(plaque.height * 47.98 / 465.06)
badge = plaque.crop((0, 0, plaque.width, badge_h))
save(fade(badge, 0.5), 'page_badge.png')                                              # 54.26 x 47.98 pt

save(fade(xobj(289), 0.5), 'logo_text.png')        # 148.83 x 141.4 pt
save(xobj(190), 'hdr_motto.png')        # 42.84 x 15 pt  ("ברצות ה'")

# --- title composite: flourishes + vector title, rasterised from page 1 at 600 dpi
pg = doc[0]
dpi = 600; z = dpi / 72
clip = pymupdf.Rect(96.0, 196.0, 497.5, 233.0)
pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip, alpha=False)
title = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
save(title, 'title_row.png')            # 401.5 x 37 pt

# --- siman frame (blank) : 196.46 x 57.19 pt ; build stretchable variants
frame = xobj(294)
save(frame, 'frame_std.png')
def stretch(im, factor, cap=170):
    """widen the frame keeping the end-caps undistorted"""
    w, h = im.size
    left, right, mid = im.crop((0, 0, cap, h)), im.crop((w - cap, 0, w, h)), im.crop((cap, 0, w - cap, h))
    new_mid = mid.resize((round(mid.width * factor), h), Image.LANCZOS)
    out = Image.new('RGBA', (cap * 2 + new_mid.width, h), (0, 0, 0, 0))
    out.paste(left, (0, 0)); out.paste(new_mid, (cap, 0)); out.paste(right, (cap + new_mid.width, 0))
    return out
PX_PER_PT = frame.width / 196.46
for name, wpt in (('frame_mid', 290.0), ('frame_wide', 400.0)):
    cap = 170
    factor = (wpt * PX_PER_PT - 2 * cap) / (frame.width - 2 * cap)
    save(stretch(frame, factor), name + '.png')

# --- end ornament: left half as-is, right half rotated 180deg (as in the PDF)
o_l, o_r = xobj(330), xobj(329).rotate(180)
orn = Image.new('RGBA', (o_l.width * 2, o_l.height), (0, 0, 0, 0))
orn.paste(o_l, (0, 0), o_l); orn.paste(o_r, (o_l.width, 0), o_r)
save(orn, 'end_ornament.png')           # 238.1 x 52.9 pt

# ---------------------------------------------------------------- derived assets (work from the PNGs above)
def derived():
    import json
    import numpy as np
    # (1) frames cut symmetrically around their VISIBLE box, so that the canvas centre is the visual centre of the frame
    PXPT = 2542 / 196.46
    info = {}
    for name in ('frame_std', 'frame_mid', 'frame_wide'):
        im = Image.open(OUT + name + '.png').convert('RGBA')
        al = np.array(im)[:, :, 3]
        ys, xs = np.where(al > 40)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = (x1 - x0) / 2 + 40, (y1 - y0) / 2 + 40
        box = (int(round(cx - hw)), int(round(cy - hh)), int(round(cx + hw)), int(round(cy + hh)))
        c = im.crop(box); c.save(OUT + name + '_t.png')
        info[name + '_t.png'] = dict(w=c.width / PXPT, h=c.height / PXPT, vis_w=(x1 - x0) / PXPT, vis_h=(y1 - y0) / PXPT)
    json.dump(info, open(OUT + 'frames.json', 'w'))
    # (2) header: right group ('ריתחא' + ornament) and left group (ornament + 'דאורייתא') cut from the title row
    src = Image.open(OUT + 'title_row.png').convert('RGB'); a = np.array(src.convert('L'))
    PX = 3346 / 401.5
    rows = (a[:, 20:3330] < 200).any(axis=1); ys = np.where(rows)[0]
    y0, y1 = max(0, ys.min() - 6), min(a.shape[0], ys.max() + 7)
    left = src.crop((20, y0, 1800, y1)); left.save(OUT + 'hdr_left.png')
    right = src.crop((1885, y0, 3330, y1)); right.save(OUT + 'hdr_right.png')
    tr = (a[:, 719:2634] < 200).any(axis=1); ty = np.where(tr)[0]
    H = (y1 - y0) / PX
    json.dump(dict(h_pt=H, w_left=left.width / PX, w_right=right.width / PX,
                   title_center_above_img_center=((y1 - ty.max()) + (y1 - ty.min())) / 2 / PX - H / 2), open(OUT + 'hdr_groups.json', 'w'))
    print('derived assets written')

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--derived':
    derived()
