"""Print sheet for the colour page (sticker paper): crop marks and PDF boxes around the page with bleed.

python make_print_sheet.py page-bleed.pdf out-print.pdf [bleed_mm] [margin_mm]

In: the page rendered with bleed (BLEED=3 node build.js ...), (80 + 2b) x (110 + 2b) mm.
Out: a sheet of trim + 2 x margin (default 10 mm round) with the page in the middle, corner crop marks in black
(0.25 pt, 5 mm long, starting 4 mm from the trim, so they stay outside the 3 mm bleed - the convention of
make_print.py), TrimBox = the finished 80 x 110 mm page, BleedBox = trim + bleed. The bleed PDF itself gets the
same TrimBox / BleedBox, for a printer that wants the file without marks.
"""
import sys
import pymupdf

MM = 72 / 25.4
TW, TH = 80.0, 110.0
OFFSET, LENGTH, WIDTH = 4.0, 5.0, 0.25

def main(src, dst, bleed=3.0, margin=10.0):
    b, m = float(bleed), float(margin)
    page_src = pymupdf.open(src)
    # boxes on the bleed file
    pg = page_src[0]
    pg.set_trimbox(pymupdf.Rect(b * MM, b * MM, (b + TW) * MM, (b + TH) * MM))
    pg.set_bleedbox(pg.mediabox)
    page_src.saveIncr() if page_src.can_save_incrementally() else page_src.save(src + '.tmp')
    sheet = pymupdf.open()
    W, H = TW + 2 * m, TH + 2 * m
    sp = sheet.new_page(width=W * MM, height=H * MM)
    # Chromium rounds the size of the page up a little; the page starts at the top left, so exactly
    # (80 + 2b) x (110 + 2b) mm from there is taken - placed 1:1, no scaling
    clip = pymupdf.Rect(0, 0, (TW + 2 * b) * MM, (TH + 2 * b) * MM)
    sp.show_pdf_page(pymupdf.Rect((m - b) * MM, (m - b) * MM, (m + TW + b) * MM, (m + TH + b) * MM), page_src, 0, clip=clip)
    x0, y0, x1, y1 = m, m, m + TW, m + TH
    sh = sp.new_shape()
    for (x, y, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x0, y1, -1, 1), (x1, y1, 1, 1)):
        sh.draw_line(((x + sx * OFFSET) * MM, y * MM), ((x + sx * (OFFSET + LENGTH)) * MM, y * MM))   # horizontal mark on the trim line
        sh.draw_line((x * MM, (y + sy * OFFSET) * MM), (x * MM, (y + sy * (OFFSET + LENGTH)) * MM))   # vertical mark
    sh.finish(color=(0, 0, 0), width=WIDTH)
    sh.commit()
    sp.set_trimbox(pymupdf.Rect(x0 * MM, y0 * MM, x1 * MM, y1 * MM))
    sp.set_bleedbox(pymupdf.Rect((x0 - b) * MM, (y0 - b) * MM, (x1 + b) * MM, (y1 + b) * MM))
    sheet.save(dst, garbage=3, deflate=True)
    print('sheet %.0f x %.0f mm, trim %.0f x %.0f mm, bleed %.0f mm' % (W, H, TW, TH, b))

if __name__ == '__main__':
    main(*sys.argv[1:5])
