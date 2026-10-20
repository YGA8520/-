#!/usr/bin/env python3
"""Print-ready PDFs of the memorial booklet (extract_booklet.py output, 48 pages) for the printing house.  usage: python make_print_booklet.py booklet.pdf out_dir [spine_mm] [--a5] [--plain]   (--plain: only the inside, exactly the trim size, no bleed, no marks)   (--a5: every page scaled to 148 x 210 mm, bleed 3 mm, as before)

  zada-interior-print.pdf         the inside: from the inner title page (page 3) to the last page before the inside of the back cover (page 46) = 44 pages, a multiple of 4,
                                  black only (DeviceGray), every page with 3 mm bleed, crop marks, centre marks and a slug line outside the bleed
  zada-cover-outside-print.pdf    front | spine | back as one sheet (Hebrew: the spine is on the right of the front cover), colour (RGB), bleed, crop and fold marks
  zada-cover-inside-print.pdf     the inside of the cover: inside of the back (empty) | spine | inside of the front (the credits page), for a cover printed on both sides
  zada-cover-pages-print.pdf      front and back cover as two separate sheets
  print-preflight.txt, print-notes.txt

The artwork of the covers, of the inner title page and of the credits page goes to the edge, so the bleed is made by mirroring the picture over the edge (the live text never
reaches the edge).  The pictures are taken from the PDF itself (page 3 has a changed background).   Needs pymupdf, numpy, pillow."""
import io
import zlib
import os
import sys
import numpy as np
import pymupdf
import outline_type3
from PIL import Image

MM = 72 / 25.4
SRC_W = 176.0                                          # width of the booklet pages (B5) in mm
TW, TH, B, M, MARK_OFF, MARK_LEN, MARK_W = 176.0, 250.0, 3.0, 10.0, 4.0, 5.0, 0.25
FORMAT = 'B5'
FORMATS = {'B5': (176.0, 250.0), 'A5': (148.0, 210.0)}      # the pages are scaled to the trim size (the proportions of B5 and A5 differ by 0.1 %)
SLUG_FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
pt = lambda v: v * MM


def page_picture(doc, i):
    """the full-page picture of a page (the biggest image): decoded, with B mm mirrored over every edge; returns (PIL image, pixels per mm of the trim)"""
    best = max(doc[i].get_images(), key=lambda im: im[2] * im[3])
    im = Image.open(io.BytesIO(doc.extract_image(best[0])['image'])).convert('RGB')
    ppm = im.width / SRC_W
    pad = int(round(B / (TW / SRC_W) * ppm))                      # the bleed is B mm on the sheet = B / scale mm of the picture
    return Image.fromarray(np.pad(np.asarray(im), ((pad, pad), (pad, pad), (0, 0)), mode='reflect')), ppm


def gray_shadings(src, dst):
    """one-colour printing: the gradient fills (the title of the inner title page, DeviceRGB shadings with grey values) become DeviceGray and the neutral
    rg / RG colours become g / G (the pictures are grey already)"""
    import pikepdf
    pdf = pikepdf.open(src)
    lum = lambda c: round(0.299 * float(c[0]) + 0.587 * float(c[1]) + 0.114 * float(c[2]), 4)
    def gray_patterns(res, seen, depth=0):                           # the RGB shadings of this resource dictionary and of the forms inside it
        for pat in ((res or {}).get('/Pattern') or {}).values():
            if pat.objgen in seen:
                continue
            seen.add(pat.objgen)
            sh = pat.get('/Shading')
            if sh is None or str(sh.get('/ColorSpace')) != '/DeviceRGB':
                continue
            fn = sh.Function
            for f in (list(fn.Functions) if '/Functions' in fn else [fn]):
                f.C0, f.C1 = pikepdf.Array([lum(f.C0)]), pikepdf.Array([lum(f.C1)])
            if '/Encode' in fn:
                fn.Encode = pikepdf.Array([0, 1] * len(list(fn.Functions)))
            sh.ColorSpace = pikepdf.Name.DeviceGray
        for x in ((res or {}).get('/XObject') or {}).values():
            if x.get('/Subtype') == '/Form' and depth < 4 and x.objgen not in seen:
                seen.add(x.objgen)
                gray_patterns(x.get('/Resources'), seen, depth + 1)
    seen = set()
    for page in pdf.pages:
        gray_patterns(page.Resources, seen)
        ops, changed = list(pikepdf.parse_content_stream(page)), False
        for k, ins in enumerate(ops):                                # the colour operators: neutral rg / RG (r = g = b) become g / G
            if str(ins.operator) in ('rg', 'RG'):
                v = [float(x) for x in ins.operands]
                ops[k] = pikepdf.ContentStreamInstruction([lum(v)], pikepdf.Operator('g' if str(ins.operator) == 'rg' else 'G'))
                changed = True
        if changed:
            page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
    done = set()
    def gray_images(res, depth=0):                                   # RGB pictures (the facsimile of the haskama) become DeviceGray
        for _, x in ((res or {}).get('/XObject') or {}).items():
            if x.objgen in done:
                continue
            done.add(x.objgen)
            if x.get('/Subtype') == '/Image':
                cs = x.get('/ColorSpace')
                rgb = str(cs) == '/DeviceRGB' or (isinstance(cs, pikepdf.Array) and str(cs[0]) == '/ICCBased' and int(cs[1].get('/N', 0)) == 3)
                if rgb:
                    im = pikepdf.PdfImage(x).as_pil_image().convert('L')
                    for k in ('/DecodeParms', '/Filter', '/ColorSpace', '/Decode'):
                        if k in x:
                            del x[k]
                    x.write(zlib.compress(im.tobytes()), filter=pikepdf.Name.FlateDecode)
                    x.ColorSpace, x.BitsPerComponent = pikepdf.Name.DeviceGray, 8
            elif x.get('/Subtype') == '/Form' and depth < 4:
                gray_images(x.get('/Resources'), depth + 1)
    for page in pdf.pages:
        gray_images(page.Resources)
    pdf.save(dst)


def line(page, x0, y0, x1, y1):
    page.draw_line(pymupdf.Point(pt(x0), pt(y0)), pymupdf.Point(pt(x1), pt(y1)), color=(0,), width=MARK_W)


def marks(page, x0, y0, x1, y1, folds=(), slug=None):
    for x, sx in ((x0, -1), (x1, 1)):
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, x + sx * MARK_OFF, y, x + sx * (MARK_OFF + MARK_LEN), y)
            line(page, x, y + sy * MARK_OFF, x, y + sy * (MARK_OFF + MARK_LEN))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for y, sy in ((y0, -1), (y1, 1)):
        line(page, cx, y + sy * MARK_OFF, cx, y + sy * (MARK_OFF + MARK_LEN))
    for x, sx in ((x0, -1), (x1, 1)):
        line(page, x + sx * MARK_OFF, cy, x + sx * (MARK_OFF + MARK_LEN), cy)
    for fx in folds:
        for y, sy in ((y0, -1), (y1, 1)):
            line(page, fx, y + sy * MARK_OFF, fx, y + sy * (MARK_OFF + MARK_LEN))
    if slug:
        page.insert_text(pymupdf.Point(pt(x0 + 14), pt(y1 + MARK_OFF + MARK_LEN - 1.2)), slug, fontsize=5, fontfile=SLUG_FONT, fontname='slug', color=(0,))


def boxes(page, x0, y0, x1, y1):
    page.set_trimbox(pymupdf.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))
    page.set_bleedbox(pymupdf.Rect(pt(x0 - B), pt(y0 - B), pt(x1 + B), pt(y1 + B)))
    page.set_artbox(pymupdf.Rect(pt(x0), pt(y0), pt(x1), pt(y1)))


def place(sheet, picture, src, i, x, y, tmp):
    """a page at (x, y) mm of the sheet: its picture with the bleed underneath, the page itself (vector) on top"""
    if picture is not None:
        path = os.path.join(tmp, f'bleed-{i}-{x:g}.jpg')
        picture.save(path, quality=94, subsampling=0, optimize=True)
        sheet.insert_image(pymupdf.Rect(pt(x - B), pt(y - B), pt(x + TW + B), pt(y + TH + B)), filename=path)
    sheet.show_pdf_page(pymupdf.Rect(pt(x), pt(y), pt(x + TW), pt(y + TH)), src, i)           # scaled to the trim size


def build(booklet, out, spine=None, fmt='B5'):
    global TW, TH, FORMAT
    TW, TH = FORMATS[fmt]
    FORMAT = fmt
    import tempfile
    os.makedirs(out, exist_ok=True)
    text_booklet = booklet                                         # the original keeps the text (page numbers of the notes)
    booklet = os.path.join(tempfile.mkdtemp(), 'outlined.pdf')
    outline_type3.outline(text_booklet, booklet)                   # no Type 3 fonts in the print files (some viewers draw them as dots)
    src = pymupdf.open(booklet)
    n = src.page_count
    front, inside_front, inside_back, back = 0, 1, n - 2, n - 1
    interior = list(range(2, n - 2))
    assert len(interior) % 4 == 0, len(interior)
    spine = spine if spine is not None else round(len(interior) / 2 * 0.10 * 2) / 2          # 0.1 mm per leaf (80 g/m2 uncoated paper), to 0.5 mm
    W, H = TW + 2 * M, TH + 2 * M
    total = len(interior)
    with tempfile.TemporaryDirectory() as tmp:
        # ---- the inside, black only
        gray_src = os.path.join(tmp, 'gray-src.pdf')
        gray_shadings(booklet, gray_src)
        gray = pymupdf.open(gray_src)
        for i in interior:
            gray[i].recolor(1)
        doc = pymupdf.open()
        for k, i in enumerate(interior, 1):
            pg = doc.new_page(width=pt(W), height=pt(H))
            big = max((im[2] * im[3] for im in gray[i].get_images()), default=0) >= 2816 * 4000 * 0.9 and len(gray[i].get_text().strip()) < 400
            pic = page_picture(gray, i)[0].convert('L') if big else None            # the pages with a full-page background (the inner title page)
            place(pg, pic, gray, i, M, M, tmp)
            marks(pg, M, M, M + TW, M + TH, (0,), f'Pilpula Daoraita memorial - inside - page {k} of {total} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm - black only')
            boxes(pg, M, M, M + TW, M + TH)
        doc.set_metadata({'title': 'Pilpula Daoraita memorial - inside (print)', 'subject': f'{total} pages, trim {TW:g} x {TH:g} mm, bleed {B:g} mm, DeviceGray'})
        inside = os.path.join(out, 'zada-interior-print.pdf')
        doc.save(inside, garbage=3, deflate=True)
        doc.close(); gray.close()

        # ---- the outside of the cover (colour): front | spine | back
        SW = 2 * M + 2 * TW + spine
        fp, ppm = page_picture(src, front)
        bp, _ = page_picture(src, back)
        sheet = pymupdf.open()
        pg = sheet.new_page(width=pt(SW), height=pt(H))
        fx, bx = M, M + TW + spine
        scale = TW / SRC_W
        pad = int(round(B / scale * ppm))
        fa, ba = np.asarray(fp).astype(np.float32), np.asarray(bp).astype(np.float32)
        strip = int(round(1.5 / scale * ppm))
        from scipy import ndimage
        left = ndimage.gaussian_filter1d(fa[:, fa.shape[1] - pad - strip: fa.shape[1] - pad].mean(axis=1), 6, axis=0)
        right = ndimage.gaussian_filter1d(ba[:, pad: pad + strip].mean(axis=1), 6, axis=0)
        sw_px = max(2, int(round(spine / scale * ppm)))
        t = np.linspace(0, 1, sw_px, dtype=np.float32)[None, :, None]
        spine_path = os.path.join(tmp, 'spine.jpg')
        Image.fromarray(np.clip(left[:, None, :] * (1 - t) + right[:, None, :] * t, 0, 255).astype(np.uint8)).save(spine_path, quality=94, subsampling=0)
        pg.insert_image(pymupdf.Rect(pt(fx + TW), pt(M - B), pt(bx), pt(M + TH + B)), filename=spine_path)
        place(pg, fp, src, front, fx, M, tmp)
        place(pg, bp, src, back, bx, M, tmp)
        marks(pg, M, M, SW - M, M + TH, (fx + TW, bx), f'Pilpula Daoraita memorial - cover, outside - spine {spine:g} mm (estimate) - trim {2 * TW + spine:g} x {TH:g} mm - bleed {B:g} mm')
        pg.set_trimbox(pymupdf.Rect(pt(M), pt(M), pt(SW - M), pt(M + TH)))
        pg.set_bleedbox(pymupdf.Rect(pt(M - B), pt(M - B), pt(SW - M + B), pt(M + TH + B)))
        sheet.set_metadata({'title': 'Pilpula Daoraita memorial - cover outside (print)', 'subject': f'front | spine {spine:g} mm | back, bleed {B:g} mm, RGB'})
        outside = os.path.join(out, 'zada-cover-outside-print.pdf')
        sheet.save(outside, garbage=3, deflate=True)
        sheet.close()

        # ---- the inside of the cover: inside of the back | spine | inside of the front (the credits page)
        sheet = pymupdf.open()
        pg = sheet.new_page(width=pt(SW), height=pt(H))
        cp, _ = page_picture(src, inside_front)
        place(pg, cp, src, inside_front, bx, M, tmp)                  # the sheet is turned over: the front is now on the right, the back on the left
        place(pg, None, src, inside_back, fx, M, tmp)
        marks(pg, M, M, SW - M, M + TH, (fx + TW, bx), f'Pilpula Daoraita memorial - cover, inside - spine {spine:g} mm (estimate) - trim {2 * TW + spine:g} x {TH:g} mm - bleed {B:g} mm')
        pg.set_trimbox(pymupdf.Rect(pt(M), pt(M), pt(SW - M), pt(M + TH)))
        pg.set_bleedbox(pymupdf.Rect(pt(M - B), pt(M - B), pt(SW - M + B), pt(M + TH + B)))
        sheet.set_metadata({'title': 'Pilpula Daoraita memorial - cover inside (print)'})
        inner = os.path.join(out, 'zada-cover-inside-print.pdf')
        sheet.save(inner, garbage=3, deflate=True)
        sheet.close()

        # ---- front and back as separate sheets
        two = pymupdf.open()
        for i, nm, pic in ((front, 'front cover', fp), (back, 'back cover', bp)):
            pg = two.new_page(width=pt(W), height=pt(H))
            place(pg, pic, src, i, M, M, tmp)
            marks(pg, M, M, M + TW, M + TH, (), f'Pilpula Daoraita memorial - {nm} - trim {TW:g} x {TH:g} mm - bleed {B:g} mm')
            boxes(pg, M, M, M + TW, M + TH)
        two.set_metadata({'title': 'Pilpula Daoraita memorial - front and back cover (print)'})
        pages = os.path.join(out, 'zada-cover-pages-print.pdf')
        two.save(pages, garbage=3, deflate=True)
        two.close()
    a1, a2, toc = article_pages(text_booklet, interior)
    report(out, [inside, outside, inner, pages], total, spine, a1, a2, toc)
    src.close()


def article_pages(booklet, interior):
    """pages (of the interior file) where the two articles begin and of the table of contents"""
    d = pymupdf.open(booklet)
    txt = [d[i].get_text() for i in interior]
    toc = next((k for k, t in enumerate(txt) if 'תוכן עניינים' in t), None)
    a1 = next(k for k, t in enumerate(txt) if 'החובה להתאמץ בדור אחרון' in t and k != toc)
    a2 = next(k for k, t in enumerate(txt) if t.count('בעניין הזכרת השם') >= 2 and k > a1 + 2)      # the title page: the title and the running head
    return a1 + 1, a2 + 1, (toc + 1 if toc is not None else None)


def build_plain(booklet, out, fmt='A5'):
    """only the inside, black only, every page exactly the trim size, no bleed, no marks, no slug: zada-interior-<fmt>.pdf"""
    global TW, TH, FORMAT
    TW, TH = FORMATS[fmt]
    FORMAT = fmt
    import tempfile
    os.makedirs(out, exist_ok=True)
    outlined = os.path.join(tempfile.mkdtemp(), 'outlined.pdf')
    outline_type3.outline(booklet, outlined)
    booklet = outlined
    n = pymupdf.open(booklet).page_count
    interior = list(range(2, n - 2))
    assert len(interior) % 4 == 0
    with tempfile.TemporaryDirectory() as tmp:
        gray_src = os.path.join(tmp, 'gray-src.pdf')
        gray_shadings(booklet, gray_src)
        gray = pymupdf.open(gray_src)
        for i in interior:
            gray[i].recolor(1)
        doc = pymupdf.open()
        for i in interior:
            pg = doc.new_page(width=pt(TW), height=pt(TH))
            pg.show_pdf_page(pg.rect, gray, i, keep_proportion=False)           # the proportions of B5 and A5 differ by 0.1 %
            pg.set_trimbox(pg.rect)
        doc.set_metadata({'title': f'Pilpula Daoraita memorial - inside ({fmt})', 'subject': f'{len(interior)} pages, {TW:g} x {TH:g} mm, DeviceGray, no bleed, no marks'})
        path = os.path.join(out, f'zada-interior-{fmt}.pdf')
        doc.save(path, garbage=3, deflate=True)
    print(f'{path}: {len(interior)} pages, {TW:g} x {TH:g} mm')


def report(out, files, total, spine, a1=None, a2=None, toc=None):
    lines = []
    for path in files:
        d = pymupdf.open(path)
        fonts, low, spaces = {}, 1e9, set()
        for pno in range(d.page_count):
            for f in d.get_page_fonts(pno):
                fonts[f[3]] = f[1] != 'n/a' or f[2] == 'Type3'
            for info in d[pno].get_image_info(xrefs=True):
                w, h, bb = info['width'], info['height'], info['bbox']
                bw, bh = (bb[2] - bb[0]) / MM, (bb[3] - bb[1]) / MM
                if bw >= 30 and bh >= 30:
                    low = min(low, w / (bw / 25.4), h / (bh / 25.4))
                spaces.add(info.get('colorspace'))
        p0 = d[0]
        lines.append(f'{os.path.basename(path)}: {d.page_count} page(s), sheet {p0.rect.width / MM:.1f} x {p0.rect.height / MM:.1f} mm, trim {p0.trimbox.width / MM:.1f} x {p0.trimbox.height / MM:.1f} mm, '
                     f'bleed box {p0.bleedbox.width / MM:.1f} x {p0.bleedbox.height / MM:.1f} mm, fonts {len(fonts)} (all embedded: {all(fonts.values())}), '
                     f'lowest artwork resolution {low:.0f} dpi, image colour spaces {sorted(str(s) for s in spaces)}, {os.path.getsize(path) / 1e6:.1f} MB')
        d.close()
    open(os.path.join(out, 'print-preflight.txt'), 'w', encoding='utf8').write('\n'.join(lines) + f'\n\ninside: {total} pages (a multiple of 4)\nspine estimated {spine:g} mm\n')
    he = f"""פלפולא דאורייתא (קונטרס לעילוי נשמת) - קבצים לבית הדפוס

zada-interior-print.pdf - פנים החוברת
  * {total} עמודים (כפולה של 4). הקובץ מתחיל בשער הפנימי השחור-לבן (עמוד אי-זוגי) ומסתיים בעמוד הריק שלפני פנים הכריכה האחורית.
  * גודל החוברת לאחר חיתוך: {TW:g} x {TH:g} מ"מ ({FORMAT}, מוקטן באופן אחיד מ-B5). שוליים לחיתוך (Bleed): {B:g} מ"מ מכל צד. גודל הגיליון בקובץ: {TW + 2 * M:g} x {TH + 2 * M:g} מ"מ.
  * סימני חיתוך בפינות, סימני אמצע בכל צד ושורת מידע (מספר עמוד) מחוץ לשוליים. הקופסאות TrimBox / BleedBox מוגדרות בקובץ.
  * שחור בלבד (DeviceGray) - הדפסה בצבע אחד. כל הגופנים מוטמעים (חלקם כקווי מתאר וקטוריים).
  * הרקע של השער הפנימי מורחב לשוליים בהשתקפות של התמונה; הטקסט לא מגיע לקצה.
  * סדר העמודים בקובץ: 1 שער פנימי, 2 עמוד "לעילוי נשמת", {toc} תוכן עניינים, אחריו ההסכמה. כל חבורה מתחילה בעמוד אי-זוגי (שמאלי): החבורה הראשונה בעמוד {a1} בקובץ והשנייה בעמוד {a2} (עמוד ריק ביניהן נחוץ לשם כך). שלושת העמודים האחרונים בקובץ ריקים (השלמה לכפולה של 4).

zada-cover-outside-print.pdf - חוץ הכריכה כיריעה אחת: שער קדמי | שדרה | שער אחורי (בעברית השדרה מימין לשער הקדמי)
  * גודל לאחר חיתוך: {2 * TW + spine:g} x {TH:g} מ"מ. עובי השדרה {spine:g} מ"מ הוא הערכה בלבד (פנים של {total} עמודים, 80 גרם) - לחוברת מהודקת בסיכות השדרה כמעט אפסית; יש לאשר מול בית הדפוס לפי הנייר והכריכה בפועל.
  * סימני חיתוך וסימני קיפול של השדרה. הקובץ בצבע (RGB) - לא הומר ל-CMYK כי אין כאן פרופיל צבע של בית הדפוס; בית הדפוס צריך להמיר, או לשלוח את הפרופיל שלו.
zada-cover-inside-print.pdf - פנים הכריכה: פנים הכריכה האחורית (עמוד "גודל החיוב ללימוד הלכות תפילה") | שדרה | פנים הכריכה הקדמית (עמוד הקרדיטים). נחוץ אם הכריכה מודפסת משני צדיה; אם היא מודפסת מצד אחד בלבד, עמוד הקרדיטים ועמוד "גודל החיוב" ייפלו.
zada-cover-pages-print.pdf - הכריכה הקדמית והאחורית כשני עמודים נפרדים (למקרה שבית הדפוס מעדיף כך).

מה לברר מול בית הדפוס לפני שליחה: סוג הכריכה (מהודקת / דבוקה), נייר ומשקל לפנים ולכריכה (קובע את עובי השדרה), שוליים לחיתוך, האם נדרש PDF/X (X-1a או X-4) ופרופיל צבע,
האם רוצים את הפנים עם סימני חיתוך או בלעדיהם, והאם הכריכה מודפסת משני צדיה (אחרת עמוד הקרדיטים לא יודפס).
"""
    open(os.path.join(out, 'print-notes.txt'), 'w', encoding='utf8').write(he)
    print('\n'.join(lines))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    fmt = 'A5' if '--a5' in sys.argv else 'B5'
    if '--plain' in sys.argv:
        build_plain(args[0], args[1], fmt)
        raise SystemExit(0)
    build(args[0], args[1], float(args[2]) if len(args) > 2 else None, fmt)
