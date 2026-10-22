#!/usr/bin/env python3
"""Print-ready PDFs (B5, 3 mm bleed, crop marks) from FINISHED booklet PDFs - no layout engine needed, the pages are used as they are (vector stays vector).

  python make_print_booklets.py <src.pdf> <out_dir> <slug> <front_inside> <back_inside> [--text-src outlined.pdf] [--spine MM] [--spine-from old_spread.pdf]

The source is a whole booklet: page 1 = front cover, `front_inside` = the inside of the front cover, then the interior, `back_inside` = the inside of the back cover,
last page = back cover (1-based page numbers).  Writes
  <slug>_interior-print.pdf       the interior, padded with empty pages to a multiple of 4
  <slug>_cover-print.pdf          4 single sheets: front, inside of front, inside of back, back
  <slug>_cover-spread-print.pdf   2 flat sheets: outside (front | spine | back) and inside (inside-back | spine | inside-front); spine width is an ESTIMATE
Every sheet = trim + 10 mm round; TrimBox / BleedBox set; crop marks and centre marks (K only) and a slug line outside the bleed.
The bleed is made by mirroring the artwork over the edge (pages with a blank edge get none); the live pages are placed on top as vector.
With --text-src the pages are taken from a copy of the booklet whose text was converted to outlines (gs -dNoOutputFonts)."""
import os, sys, io, json, argparse
import numpy as np
from PIL import Image
from scipy import ndimage
import fitz

MM = 72 / 25.4
TW, TH = 176.0, 250.0
B, M = 3.0, 10.0
MARK_OFF, MARK_LEN, MARK_W = 4.0, 5.0, 0.25
SLUG_FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
DPI = 200


def pt(v):
    return v * MM


def line(page, x0, y0, x1, y1):
    page.draw_line(fitz.Point(pt(x0), pt(y0)), fitz.Point(pt(x1), pt(y1)), color=(0,), width=MARK_W)


def marks(page, x0, y0, x1, y1, folds=(), slug=None):
    o, ln = MARK_OFF, MARK_LEN
    for x, sx in ((x0, -1), (x1, 1)):
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, x + sx * o, y, x + sx * (o + ln), y)
            line(page, x, y + sy * o, x, y + sy * (o + ln))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for y, sy in ((y0, -1), (y1, 1)):
        line(page, cx, y + sy * o, cx, y + sy * (o + ln))
    for x, sx in ((x0, -1), (x1, 1)):
        line(page, x + sx * o, cy, x + sx * (o + ln), cy)
    for fx in folds:
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, fx, y + sy * o, fx, y + sy * (o + ln))
    if slug:
        page.insert_text(fitz.Point(pt(x0 + 14), pt(y1 + o + ln - 1.2)), slug, fontsize=5, fontfile=SLUG_FONT, fontname='slugbk', color=(0,))


def set_boxes(page, x0, y0, x1, y1):
    page.set_trimbox(fitz.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))
    page.set_bleedbox(fitz.Rect(pt(x0 - B), pt(y0 - B), pt(x1 + B), pt(y1 + B)))
    page.set_artbox(fitz.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))


def white_insets(a, maxpx=4):
    """leading / trailing rows and columns that are completely white (a sliver left by the export, e.g. the artwork ending 0.2 mm short of the page edge)"""
    def run(lines):
        k = 0
        while k < maxpx and k < len(lines) and lines[k].min() >= 252:
            k += 1
        return k
    return run(a.min(axis=(1, 2))), run(a.min(axis=(1, 2))[::-1]), run(a.min(axis=(0, 2))), run(a.min(axis=(0, 2))[::-1])   # top, bottom, left, right


def padded_render(src, i):
    """the page rendered at DPI, without a white sliver at the edges, padded by the bleed with mirrored pixels -> (array, pixels per mm, pad px, (top, bottom, left, right) sliver in px)"""
    ppm = DPI / 25.4
    pix = src[i].get_pixmap(dpi=DPI, alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    t, bt, l, r = white_insets(a)
    a = a[t:a.shape[0] - bt, l:a.shape[1] - r]
    pad = int(round(B * ppm))
    return np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='reflect'), ppm, pad, (t, bt, l, r)


def edge_is_blank(a, pad):
    r = max(2, int(0.5 * DPI / 25.4))
    ins = a[pad:-pad, pad:-pad]
    ring = np.concatenate([ins[:r].reshape(-1, 3), ins[-r:].reshape(-1, 3), ins[:, :r].reshape(-1, 3), ins[:, -r:].reshape(-1, 3)])
    return (ring.min(1) >= 250).all()


def jpg(arr):
    b = io.BytesIO()
    Image.fromarray(arr).save(b, format='JPEG', quality=92, subsampling=0)
    return b.getvalue()


def bleed_strips(page, a, pad, ppm, x, y, sides=('t', 'b', 'l', 'r'), inner=None):
    """put the mirrored bleed (the ring outside the trim at x, y mm, running 0.25 mm under the live page so that no hairline shows) on the sheet; the live page goes on top afterwards"""
    h, w = a.shape[0] - 2 * pad, a.shape[1] - 2 * pad
    k = 2                                                    # px of overlap
    o = k / ppm
    if 't' in sides:
        page.insert_image(fitz.Rect(pt(x - B), pt(y - B), pt(x + TW + B), pt(y + o)), stream=jpg(a[:pad + k, :]), keep_proportion=False)
    if 'b' in sides:
        page.insert_image(fitz.Rect(pt(x - B), pt(y + TH - o), pt(x + TW + B), pt(y + TH + B)), stream=jpg(a[pad + h - k:, :]), keep_proportion=False)
    if 'l' in sides:
        page.insert_image(fitz.Rect(pt(x - B), pt(y), pt(x + o), pt(y + TH)), stream=jpg(a[pad:pad + h, :pad + k]), keep_proportion=False)
    if 'r' in sides:
        page.insert_image(fitz.Rect(pt(x + TW - o), pt(y), pt(x + TW + B), pt(y + TH)), stream=jpg(a[pad:pad + h, pad + w - k:]), keep_proportion=False)
    if inner == 'r':                                         # towards the spine (no bleed there)
        page.insert_image(fitz.Rect(pt(x + TW - o), pt(y), pt(x + TW), pt(y + TH)), stream=jpg(a[pad:pad + h, pad + w - k:pad + w]), keep_proportion=False)
    if inner == 'l':
        page.insert_image(fitz.Rect(pt(x), pt(y), pt(x + o), pt(y + TH)), stream=jpg(a[pad:pad + h, pad:pad + k]), keep_proportion=False)


def quick_blank(src, i):
    """cheap test at low resolution: is the 0.5 mm ring round the page plain white?"""
    pix = src[i].get_pixmap(dpi=60, alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    r = 2
    ring = np.concatenate([a[:r].reshape(-1, 3), a[-r:].reshape(-1, 3), a[:, :r].reshape(-1, 3), a[:, -r:].reshape(-1, 3)])
    return (ring.min(1) >= 250).all()


def put_page(page, src, i, x, y, sides=('t', 'b', 'l', 'r')):
    arr = None
    if not quick_blank(src, i):
        arr = padded_render(src, i)
        if edge_is_blank(arr[0], arr[2]):
            arr = None
    clip = None
    if arr:
        t, bt, l, r = arr[3]
        k = 72 / DPI
        pr = src[i].rect
        clip = fitz.Rect(pr.x0 + l * k, pr.y0 + t * k, pr.x1 - r * k, pr.y1 - bt * k)
    page.show_pdf_page(fitz.Rect(pt(x), pt(y), pt(x + TW), pt(y + TH)), src, i, clip=clip)
    if arr:                                                  # the bleed goes on top and runs 0.25 mm over the edge of the page: no hairline from the clipping of the page
        bleed_strips(page, arr[0], arr[2], arr[1], x, y, sides)
    return arr


def spine_strip(left_arr, right_arr, spine_mm, path):
    """a gradient between the right edge of the left page and the left edge of the right page, row by row, bleed included top and bottom"""
    la, ppm, pad = left_arr[:3]
    ra = right_arr[0]
    strip = int(round(1.5 * ppm))
    left = la[:, la.shape[1] - pad - strip: la.shape[1] - pad].astype(np.float32).mean(axis=1)
    right = ra[:, pad: pad + strip].astype(np.float32).mean(axis=1)
    if len(right) != len(left):                              # the two pages lost a different sliver: bring the rows to the same count
        src_y = np.linspace(0, 1, len(right)); dst_y = np.linspace(0, 1, len(left))
        right = np.stack([np.interp(dst_y, src_y, right[:, c]) for c in range(3)], axis=1)
    left, right = ndimage.gaussian_filter1d(left, 6, axis=0), ndimage.gaussian_filter1d(right, 6, axis=0)
    sw = max(2, int(round(spine_mm * ppm)))
    t = np.linspace(0, 1, sw, dtype=np.float32)[None, :, None]
    g = np.clip(left[:, None, :] * (1 - t) + right[:, None, :] * t, 0, 255).astype(np.uint8)
    Image.fromarray(g).save(path, quality=94, subsampling=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out'); ap.add_argument('slug')
    ap.add_argument('front_inside', type=int); ap.add_argument('back_inside', type=int)
    ap.add_argument('--text-src', default=None)
    ap.add_argument('--spine', type=float, default=None)
    ap.add_argument('--spine-from', default=None, help='a spread made earlier whose spine (artwork, title) is reused: pdf[,page]')
    ap.add_argument('--pad-multiple', type=int, default=4)
    ap.add_argument('--bulk', type=float, default=0.10, help='mm per leaf (80 g/m2 uncoated paper)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    work = fitz.open(a.text_src or a.src)                 # pages placed on the sheets (vector)
    ref = work                                            # pages rendered for the bleed
    n = work.page_count
    fi, bi = a.front_inside - 1, a.back_inside - 1
    interior = list(range(fi + 1, bi))
    pad = (-len(interior)) % a.pad_multiple
    total = len(interior) + pad
    W, H = TW + 2 * M, TH + 2 * M
    nice = a.slug.replace('-', ' ').title()

    # ------------------------------------------------------------------ interior
    doc = fitz.open()
    for k, i in enumerate(interior + [None] * pad, 1):
        pg = doc.new_page(width=pt(W), height=pt(H))
        if i is not None:
            put_page(pg, work, i, M, M)
        marks(pg, M, M, M + TW, M + TH, slug=f'{nice} - inside - page {k} of {total} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm')
        set_boxes(pg, M, M, M + TW, M + TH)
    doc.set_metadata({'title': f'{nice} - inside (print)', 'subject': f'{total} pages, trim {TW:g} x {TH:g} mm, bleed {B:g} mm', 'producer': 'make_print_booklets.py'})
    p_in = os.path.join(a.out, f'{a.slug}_interior-print.pdf')
    doc.save(p_in, garbage=3, deflate=True)
    doc.close()

    # ------------------------------------------------------------------ cover: 4 single sheets
    names = [(0, 'front cover (outside)'), (fi, 'front cover (inside)'), (bi, 'back cover (inside)'), (n - 1, 'back cover (outside)')]
    doc = fitz.open()
    arrs = {}
    for idx, nm in names:
        pg = doc.new_page(width=pt(W), height=pt(H))
        arrs[idx] = put_page(pg, work, idx, M, M)
        marks(pg, M, M, M + TW, M + TH, slug=f'{nice} - {nm} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm')
        set_boxes(pg, M, M, M + TW, M + TH)
    doc.set_metadata({'title': f'{nice} - cover, 4 sheets (print)', 'subject': 'front, inside front, inside back, back', 'producer': 'make_print_booklets.py'})
    p_cov = os.path.join(a.out, f'{a.slug}_cover-print.pdf')
    doc.save(p_cov, garbage=3, deflate=True)
    doc.close()

    # ------------------------------------------------------------------ cover: two flat sheets (front | spine | back  and  inside back | spine | inside front)
    spine = a.spine if a.spine else round(total / 2 * a.bulk * 2) / 2
    SW = 2 * M + 2 * TW + spine
    doc = fitz.open()
    old = None
    if a.spine_from:
        sp, _, pn = a.spine_from.partition(',')
        old = (fitz.open(sp), int(pn or 0))
    for sheet_no, (li, ri, label) in enumerate(((0, n - 1, 'outside: front | spine | back'), (bi, fi, 'inside: inside back | spine | inside front'))):
        pg = doc.new_page(width=pt(SW), height=pt(H))
        lx, rx = M, M + TW + spine
        la, ra = arrs[li], arrs[ri]
        la = la or padded_render(work, li)
        ra = ra or padded_render(work, ri)
        sp_path = os.path.join(a.out, f'.spine{sheet_no}.jpg')
        spine_strip(la, ra, spine, sp_path)
        pg.insert_image(fitz.Rect(pt(lx + TW), pt(M - B), pt(rx), pt(M + TH + B)), filename=sp_path, keep_proportion=False)
        os.remove(sp_path)
        for arr, x, pno in ((la, lx, li), (ra, rx, ri)):
            t, bt, l, r = arr[3]
            k, pr = 72 / DPI, work[pno].rect
            pg.show_pdf_page(fitz.Rect(pt(x), pt(M), pt(x + TW), pt(M + TH)), work, pno, clip=fitz.Rect(pr.x0 + l * k, pr.y0 + t * k, pr.x1 - r * k, pr.y1 - bt * k))
        if old and sheet_no == 0:                                                   # spine artwork of an earlier spread, same width
            od, opn = old
            pg.show_pdf_page(fitz.Rect(pt(lx + TW), pt(M - B), pt(rx), pt(M + TH + B)), od, opn, clip=fitz.Rect(pt(M + TW), pt(M - B), pt(M + TW + spine), pt(M + TH + B)))
        for (arr, x, sides) in ((la, lx, ('t', 'b', 'l', 'r')), (ra, rx, ('t', 'b', 'l', 'r'))):
            inner = 'r' if x == lx else 'l'                                         # the side towards the spine: only the 0.25 mm over the edge, the spine takes the rest
            bleed_strips(pg, arr[0], arr[2], arr[1], x, M, tuple(c for c in sides if c != inner), inner=inner)
        marks(pg, M, M, SW - M, M + TH, folds=(lx + TW, rx), slug=f'{nice} - cover spread, {label} - spine {spine:g} mm (estimate) - trim {2 * TW + spine:g} x {TH:g} mm - bleed {B:g} mm')
        pg.set_trimbox(fitz.Rect(pt(M), pt(M), pt(SW - M), pt(M + TH)))
        pg.set_bleedbox(fitz.Rect(pt(M - B), pt(M - B), pt(SW - M + B), pt(M + TH + B)))
    doc.set_metadata({'title': f'{nice} - cover spread, 2 sheets (print)', 'subject': f'outside and inside, spine {spine:g} mm', 'producer': 'make_print_booklets.py'})
    p_spr = os.path.join(a.out, f'{a.slug}_cover-spread-print.pdf')
    doc.save(p_spr, garbage=3, deflate=True)
    doc.close()
    json.dump({'interior': p_in, 'cover': p_cov, 'spread': p_spr, 'interior_pages': len(interior), 'pad': pad, 'total': total, 'spine': spine, 'source_pages': n},
              open(os.path.join(a.out, f'{a.slug}.json'), 'w'), ensure_ascii=False)
    print(a.slug, 'interior', len(interior), '+', pad, '| spine', spine)


if __name__ == '__main__':
    main()
