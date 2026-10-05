#!/usr/bin/env python3
"""Print-ready PDFs for the printing house, made from the finished booklet (out/book.pdf + out/book.layout.json).  usage: python make_print.py [out_dir]

  <out_dir>/pilpula-interior-print.pdf    the inside of the book: from the inner title page to the last page, padded with empty pages to a multiple of 4,
                                          black only (DeviceGray), every page with 3 mm bleed, crop marks, centre marks and a slug line outside the bleed;
                                          TrimBox = the finished page, BleedBox = trim + bleed, MediaBox = trim + 10 mm round
  <out_dir>/pilpula-cover-spread-print.pdf  the outside of the cover as one sheet: front | spine | back (Hebrew: the spine is on the right of the front cover), with bleed,
                                          crop marks and fold marks; the width of the spine is estimated from the number of pages (see print.spineMm)
  <out_dir>/pilpula-cover-pages-print.pdf   the same front and back cover as two separate sheets (for a printer that wants them apart)
  <out_dir>/print-preflight.txt           what was made and what the printing house has to confirm

The artwork of the cover, the inner pages and the dividers goes to the edge of the page, so the bleed is made by mirroring the artwork over the edge (the live text never
reaches the edge).  Settings: config.json -> print."""
import os, sys, json, math
import numpy as np
from PIL import Image
from scipy import ndimage
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 72 / 25.4
CFG = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf8'))
P = dict(bleed=3.0, margin=10.0, markOffset=4.0, markLen=5.0, markWidth=0.25, padMultiple=4, bulkMm=0.10, spineMm=None, spineDirection='down', spineFont='assets/fonts/Ashkenazy-Regular.ttf',
         spineTitle='פלפולא דאורייתא', slug=True)
P.update(CFG.get('print') or {})
TW, TH = CFG['page']['w'], CFG['page']['h']
B, M = P['bleed'], P['margin']
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'print')
os.makedirs(os.path.join(OUT, 'bleed'), exist_ok=True)
SLUG_FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'


def pt(v):
    return v * MM


def bled(rel, gray):
    """the artwork with `bleed` mm mirrored over every edge (jpeg in <out>/bleed); returns (path, pixels per mm, pad px)"""
    name = os.path.splitext(os.path.basename(rel))[0] + ('-gray' if gray else '') + '-bleed.jpg'
    dst = os.path.join(OUT, 'bleed', name)
    im = Image.open(os.path.join(HERE, rel)).convert('RGB')
    ppm = im.width / TW
    pad = int(round(B * ppm))
    if not os.path.exists(dst):
        a = np.asarray(im)
        a = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='reflect')
        out = Image.fromarray(a)
        if gray:
            out = out.convert('L')
        out.save(dst, quality=94, subsampling=0, optimize=True)
    return dst, ppm, pad


def line(page, x0, y0, x1, y1, col):
    page.draw_line(fitz.Point(pt(x0), pt(y0)), fitz.Point(pt(x1), pt(y1)), color=col, width=P['markWidth'])


def marks(page, W, H, x0, y0, x1, y1, col, folds=(), slug=None):
    """crop marks at the corners of the trim rectangle (x0, y0, x1, y1) of the sheet W x H (mm), centre marks, fold marks and a slug line, all outside the bleed"""
    o, ln = P['markOffset'], P['markLen']
    for x, sx in ((x0, -1), (x1, 1)):
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, x + sx * o, y, x + sx * (o + ln), y, col)                        # horizontal mark
            line(page, x, y + sy * o, x, y + sy * (o + ln), col)                        # vertical mark
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for y, sy in ((y0, -1), (y1, 1)):
        line(page, cx, y + sy * o, cx, y + sy * (o + ln), col)                          # centre marks
    for x, sx in ((x0, -1), (x1, 1)):
        line(page, x + sx * o, cy, x + sx * (o + ln), cy, col)
    for fx in folds:                                                                    # fold marks of the spine
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, fx, y + sy * o, fx, y + sy * (o + ln), col)
    if slug and P['slug']:
        page.insert_text(fitz.Point(pt(x0 + 14), pt(y1 + o + ln - 1.2)), slug, fontsize=5, fontfile=SLUG_FONT, fontname='slug', color=col)


def set_boxes(page, W, H, x0, y0, x1, y1):
    page.set_trimbox(fitz.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))
    page.set_bleedbox(fitz.Rect(pt(x0 - B), pt(y0 - B), pt(x1 + B), pt(y1 + B)))
    page.set_artbox(fitz.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))


def new_sheet(doc, W, H):
    return doc.new_page(width=pt(W), height=pt(H))


def underlay(page, rel, x, y, gray):
    path, ppm, pad = bled(rel, gray)
    page.insert_image(fitz.Rect(pt(x - B), pt(y - B), pt(x + TW + B), pt(y + TH + B)), filename=path)


def main():
    book = os.path.join(HERE, 'out', 'book.pdf')
    lay = json.load(open(os.path.join(HERE, 'out', 'book.layout.json')))
    kinds = lay['pageKinds']
    n = len(kinds)
    first = next(i for i, k in enumerate(kinds) if k['k'] == 'inner')
    back = next(i for i, k in enumerate(kinds) if k['k'] == 'back')
    front = next(i for i, k in enumerate(kinds) if k['k'] == 'cover')
    interior = list(range(first, back))
    pad = (-len(interior)) % int(P['padMultiple'])
    total = len(interior) + pad
    W, H = TW + 2 * M, TH + 2 * M

    # ---------------------------------------------------------------- the inside: black only
    gsrc = fitz.open(book)
    for i in interior:
        gsrc[i].recolor(1)                                             # every colour on the inside is a grey: the file is DeviceGray (one colour printing)
    doc = fitz.open()
    for k, i in enumerate(interior + [None] * pad, 1):
        pg = new_sheet(doc, W, H)
        if i is not None and kinds[i]['bg']:
            underlay(pg, kinds[i]['bg'], M, M, True)
        if i is not None:
            src_rect = gsrc[i].rect
            pg.show_pdf_page(fitz.Rect(pt(M), pt(M), pt(M) + src_rect.width, pt(M) + src_rect.height), gsrc, i)
        marks(pg, W, H, M, M, M + TW, M + TH, (0,), slug=f'Pilpula Daoraita - inside - page {k} of {total} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm - black only')
        set_boxes(pg, W, H, M, M, M + TW, M + TH)
    doc.set_metadata({'title': 'Pilpula Daoraita - inside (print)', 'subject': f'{total} pages, trim {TW:g} x {TH:g} mm, bleed {B:g} mm, DeviceGray', 'producer': 'make_print.py'})
    inside = os.path.join(OUT, 'pilpula-interior-print.pdf')
    doc.save(inside, garbage=3, deflate=True)
    doc.close(); gsrc.close()

    # ---------------------------------------------------------------- the cover (colour)
    csrc = fitz.open(book)
    spine = P['spineMm'] if P['spineMm'] else round(total / 2 * P['bulkMm'] * 2) / 2
    SW = 2 * M + 2 * TW + spine
    sheet = fitz.open()
    pg = new_sheet(sheet, SW, H)
    fx, bx = M, M + TW + spine                                           # Hebrew: the front on the left, the spine on its right, the back right of the spine
    fpath, ppm, pad_px = bled(kinds[front]['bg'], False)
    bpath, _, _ = bled(kinds[back]['bg'], False)
    pg.insert_image(fitz.Rect(pt(fx - B), pt(M - B), pt(fx + TW + B), pt(M + TH + B)), filename=fpath)
    pg.insert_image(fitz.Rect(pt(bx - B), pt(M - B), pt(bx + TW + B), pt(M + TH + B)), filename=bpath)
    # the spine: a gradient from the colour of the front's edge to the colour of the back's edge, row by row, so that both seams vanish
    fa = np.asarray(Image.open(fpath).convert('RGB')).astype(np.float32)
    ba = np.asarray(Image.open(bpath).convert('RGB')).astype(np.float32)
    strip = int(round(1.5 * ppm))
    left = fa[:, fa.shape[1] - pad_px - strip: fa.shape[1] - pad_px].mean(axis=1)
    right = ba[:, pad_px: pad_px + strip].mean(axis=1)
    left, right = ndimage.gaussian_filter1d(left, 6, axis=0), ndimage.gaussian_filter1d(right, 6, axis=0)
    sw_px = max(2, int(round(spine * ppm)))
    t = np.linspace(0, 1, sw_px, dtype=np.float32)[None, :, None]
    grad = left[:, None, :] * (1 - t) + right[:, None, :] * t
    spine_path = os.path.join(OUT, 'bleed', 'spine.jpg')
    Image.fromarray(np.clip(grad, 0, 255).astype(np.uint8)).save(spine_path, quality=94, subsampling=0)
    pg.insert_image(fitz.Rect(pt(fx + TW), pt(M - B), pt(bx), pt(M + TH + B)), filename=spine_path)
    pg.show_pdf_page(fitz.Rect(pt(fx), pt(M), pt(fx) + csrc[front].rect.width, pt(M) + csrc[front].rect.height), csrc, front)
    pg.show_pdf_page(fitz.Rect(pt(bx), pt(M), pt(bx) + csrc[back].rect.width, pt(M) + csrc[back].rect.height), csrc, back)
    if spine >= 12:                                                      # title along the spine (first letter at the top) and the logo at its foot
        font = fitz.Font(fontfile=os.path.join(HERE, P['spineFont']))
        title = P['spineTitle'][::-1]                                     # visual order for a left-to-right drawing routine
        fs = min(spine * 0.62 * MM * 0.9, 46)
        L = font.text_length(title, fontsize=fs)
        cxs = fx + TW + spine / 2
        logo_h = 0
        logo = os.path.join(HERE, CFG['cover']['logo']['image']) if CFG.get('cover', {}).get('logo') else None
        if logo and os.path.exists(logo):
            lw = min(spine - 8, 24.0)
            lh = lw * CFG['cover']['logo']['h'] / CFG['cover']['logo']['w']
            ly = M + TH - 16 - lh
            pg.insert_image(fitz.Rect(pt(cxs - lw / 2), pt(ly), pt(cxs + lw / 2), pt(ly + lh)), filename=logo)
            logo_h = lh + 16 + 8
        avail = TH - 30 - logo_h
        ytop = M + 18 + (avail - L / MM) / 2
        col = (0x4d / 255, 0x3c / 255, 0x2b / 255)
        rot = 90 if P['spineDirection'] == 'down' else 270
        base_x = cxs + (0.3 * fs / MM if rot == 90 else -0.3 * fs / MM)
        start_y = ytop + L / MM if rot == 90 else ytop
        pg.insert_text(fitz.Point(pt(base_x), pt(start_y)), title, fontsize=fs, fontfile=os.path.join(HERE, P['spineFont']), fontname='spine', color=col, rotate=rot)
    marks(pg, SW, H, M, M, SW - M, M + TH, (0, 0, 0), folds=(fx + TW, bx), slug=f'Pilpula Daoraita - cover spread - spine {spine:g} mm (estimate) - trim {2 * TW + spine:g} x {TH:g} mm - bleed {B:g} mm')
    pg.set_trimbox(fitz.Rect(pt(M), pt(M), pt(SW - M), pt(M + TH)))
    pg.set_bleedbox(fitz.Rect(pt(M - B), pt(M - B), pt(SW - M + B), pt(M + TH + B)))
    sheet.set_metadata({'title': 'Pilpula Daoraita - cover spread (print)', 'subject': f'front | spine {spine:g} mm | back, bleed {B:g} mm, RGB', 'producer': 'make_print.py'})
    cover_spread = os.path.join(OUT, 'pilpula-cover-spread-print.pdf')
    sheet.save(cover_spread, garbage=3, deflate=True)
    sheet.close()

    two = fitz.open()
    for idx, nm in ((front, 'front cover'), (back, 'back cover')):
        pg = new_sheet(two, W, H)
        underlay(pg, kinds[idx]['bg'], M, M, False)
        pg.show_pdf_page(fitz.Rect(pt(M), pt(M), pt(M) + csrc[idx].rect.width, pt(M) + csrc[idx].rect.height), csrc, idx)
        marks(pg, W, H, M, M, M + TW, M + TH, (0, 0, 0), slug=f'Pilpula Daoraita - {nm} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm')
        set_boxes(pg, W, H, M, M, M + TW, M + TH)
    two.set_metadata({'title': 'Pilpula Daoraita - front and back cover (print)', 'producer': 'make_print.py'})
    cover_pages = os.path.join(OUT, 'pilpula-cover-pages-print.pdf')
    two.save(cover_pages, garbage=3, deflate=True)
    two.close(); csrc.close()

    report(inside, cover_spread, cover_pages, total, pad, spine, len(interior))
    return inside, cover_spread, cover_pages


def report(inside, spread, pages, total, pad, spine, n_int):
    lines = []
    for path in (inside, spread, pages):
        d = fitz.open(path)
        fonts, low = {}, 1e9
        spaces = set()
        for pno in range(d.page_count):
            for f in d.get_page_fonts(pno):
                fonts[f[3]] = f[1] != 'n/a' or f[2] == 'Type3'          # Type 3 fonts carry their outlines inside the file
            for info in d[pno].get_image_info(xrefs=True):
                w, h, bb = info['width'], info['height'], info['bbox']
                bw, bh = (bb[2] - bb[0]) / MM, (bb[3] - bb[1]) / MM
                if bw >= 30 and bh >= 30:                                 # the artwork and logos (thin ornaments and gradients are not judged by their pixels)
                    low = min(low, w / (bw / 25.4), h / (bh / 25.4))
                spaces.add(info.get('colorspace'))
        pg0 = d[0]
        lines.append(f'{os.path.basename(path)}: {d.page_count} page(s), sheet {pg0.rect.width / MM:.1f} x {pg0.rect.height / MM:.1f} mm, trim {pg0.trimbox.width / MM:.1f} x {pg0.trimbox.height / MM:.1f} mm, '
                     f'bleed box {pg0.bleedbox.width / MM:.1f} x {pg0.bleedbox.height / MM:.1f} mm, fonts {len(fonts)} (all embedded: {all(fonts.values())}), '
                     f'lowest artwork resolution {low:.0f} dpi, image colour spaces {sorted(str(s) for s in spaces)}, {os.path.getsize(path) / 1e6:.1f} MB')
        d.close()
    txt = '\n'.join(lines) + f'''

inside: {n_int} pages of the book + {pad} empty page(s) = {total} pages (a multiple of {P['padMultiple']}); it starts with the inner title page (an odd page) and ends with an empty / last page
cover: spine estimated {spine:g} mm = {total} pages / 2 x {P['bulkMm']:g} mm per leaf (80 g/m2 uncoated paper) - THE PRINTING HOUSE MUST CONFIRM THE SPINE FOR ITS PAPER AND BINDING
'''
    open(os.path.join(OUT, 'print-preflight.txt'), 'w', encoding='utf8').write(txt)
    nb = len(json.load(open(os.path.join(HERE, 'out', 'book.layout.json'))).get('blankPages', []))
    he = f"""פלפולא דאורייתא - קבצים לבית הדפוס

pilpula-interior-print.pdf - פנים החוברת
  * {total} עמודים ({n_int} עמודי החוברת + {pad} עמוד ריק בסוף, כדי שמספר העמודים יהיה כפולה של {P['padMultiple']}). הקובץ מתחיל בשער הפנימי (עמוד אי-זוגי) ומסתיים בעמוד ריק.
  * גודל החוברת לאחר חיתוך: {TW:g} x {TH:g} מ"מ (B5). שוליים לחיתוך (Bleed): {B:g} מ"מ מכל צד. גודל הגיליון בקובץ: {TW + 2 * M:g} x {TH + 2 * M:g} מ"מ.
  * סימני חיתוך בפינות, סימני אמצע בכל צד ושורת מידע (מספר עמוד) מחוץ לשוליים. הקופסאות TrimBox / BleedBox מוגדרות בקובץ.
  * שחור בלבד (DeviceGray) - הדפסה בצבע אחד. כל הגופנים מוטמעים (חלקם כקווי מתאר וקטוריים, Type 3).
  * הרקעים של השער הפנימי, הקרדיטים והחוצצים מורחבים לשוליים בהשתקפות של התמונה; הטקסט לא מגיע לקצה.

pilpula-cover-spread-print.pdf - הכריכה כיריעה אחת: שער קדמי | שדרה | שער אחורי (בעברית השדרה מימין לשער הקדמי)
  * גודל לאחר חיתוך: {2 * TW + spine:g} x {TH:g} מ"מ. עובי השדרה {spine:g} מ"מ הוא הערכה בלבד ({total} עמודים, 80 גרם, כריכה דבוקה) - יש לאשר מול בית הדפוס לפי הנייר והכריכה בפועל. אם העובי שונה: לשנות print.spineMm ב-config.json ולהריץ שוב.
  * סימני חיתוך וסימני קיפול של השדרה. הקובץ בצבע (RGB) - לא הומר ל-CMYK כי אין כאן פרופיל צבע של בית הדפוס; בית הדפוס צריך להמיר, או לשלוח לנו את הפרופיל שלו.
pilpula-cover-pages-print.pdf - אותם שני השערים כשני עמודים נפרדים (למקרה שבית הדפוס מעדיף כך).

מה לברר מול בית הדפוס לפני שליחה: סוג הכריכה (דבוקה / תפורה / חוט), נייר ומשקל לפנים ולכריכה (קובע את עובי השדרה), עובי השוליים לחיתוך הנדרש,
האם נדרש PDF/X (X-1a או X-4) ופרופיל צבע, והאם רוצים את הפנים עם סימני חיתוך או בלעדיהם, ואם העמודים הריקים (אחד אחרי השער החיצוני ו-{nb} לפני חוצצים שנפלו על עמוד זוגי) מתאימים להם.
"""
    open(os.path.join(OUT, 'print-notes.txt'), 'w', encoding='utf8').write(he)
    print(txt)


if __name__ == '__main__':
    main()
