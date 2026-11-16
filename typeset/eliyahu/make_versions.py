"""All dedication versions of the colour page (sticker 'הכוונות קודם תפילת שמונה עשרה'), print files and one zip.

python eliyahu/make_versions.py [out_dir] [zip_path]     (run from typeset/)

Per version (DED of page1-color.html, PLAIN title) a folder with
  1-להדפסה-עם-סימני-חיתוך.pdf   sheet with crop marks, 3 mm bleed, TrimBox / BleedBox (make_print_sheet.py)
  2-עם-בליד-בלי-סימנים.pdf      the page with 3 mm bleed, no marks: exactly 86 x 116 mm, TrimBox 80 x 110 mm
  3-גודל-סופי-8x11.pdf          the finished size without bleed or marks: exactly 80 x 110 mm
  4-תצוגה-מקדימה.png            preview at 600 dpi
The pages are rendered with #notitle and the title + בס״ד are laid over 1:1 from title-taamim.pdf (make_title_asset.py),
so the Taamim font file is not needed. Chromium makes the page a little larger than asked (80.09 x 110.07 mm); the
files are cut to the exact size from the top left, where the page starts.
"""
import os
import subprocess
import sys
import zipfile

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_print_sheet  # noqa: E402

MM = 72 / 25.4
TW, TH, BLEED = 80.0, 110.0, 3.0
VERSIONS = [
    ('eliyahu',   '1-לעילוי-נשמת-אליהו'),
    ('refua',     '2-לרפואת-אפרת-מרים-לידיה'),
    ('hatzlacha', '3-הוקדש-על-ידי-יוסף-גורג'),
    ('zivug',     '4-לזכות-הודיה'),
    ('none',      '5-ללא-הקדשה'),
    ('yosef',     '6-לרפואת-יוסף-בן-טווס'),
]
NAMES = ('1-להדפסה-עם-סימני-חיתוך.pdf', '2-עם-בליד-בלי-סימנים.pdf', '3-גודל-סופי-8x11.pdf', '4-תצוגה-מקדימה.png')


def render(tmp, ded, bleed):
    env = dict(os.environ, NOTITLE='1', PLAIN='1', DED=ded)
    env.pop('BLEED', None)
    if bleed:
        env['BLEED'] = str(bleed)
    r = subprocess.run(['node', os.path.join(HERE, 'build.js'), tmp, 'page1-color'], env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)
    print('  ', ded, 'bleed' if bleed else 'final', r.stdout.strip())
    return os.path.join(tmp, 'page1-color-plain-%s%s.pdf' % (ded, '-bleed' if bleed else ''))


def exact(src, w, h, off, title, dst, bleed=0.0):
    """the Chromium page cut to w x h mm from the top left, the title laid over at off mm (its place in this page)"""
    s = pymupdf.open(src)
    t = pymupdf.open(title)
    tw, th = t[0].rect.width, t[0].rect.height
    s[0].show_pdf_page(pymupdf.Rect(off * MM, off * MM, off * MM + tw, off * MM + th), t, 0)
    s = pymupdf.open('pdf', s.tobytes())
    out = pymupdf.open()
    pg = out.new_page(width=w * MM, height=h * MM)
    pg.show_pdf_page(pg.rect, s, 0, clip=pymupdf.Rect(0, 0, w * MM, h * MM))
    if bleed:
        pg.set_trimbox(pymupdf.Rect(bleed * MM, bleed * MM, (w - bleed) * MM, (h - bleed) * MM))
        pg.set_bleedbox(pg.mediabox)
    else:
        pg.set_trimbox(pg.mediabox)
    out.save(dst, garbage=3, deflate=True)


def main(out_dir='out/kavanot', zip_path=None):
    title = os.path.join(HERE, 'title-taamim.pdf')
    tmp = os.path.join(out_dir, '_render')
    os.makedirs(tmp, exist_ok=True)
    folders = []
    for ded, folder in VERSIONS:
        d = os.path.join(out_dir, folder)
        os.makedirs(d, exist_ok=True)
        f_print, f_bleed, f_final, f_png = (os.path.join(d, n) for n in NAMES)
        exact(render(tmp, ded, 0), TW, TH, 0.0, title, f_final)
        exact(render(tmp, ded, BLEED), TW + 2 * BLEED, TH + 2 * BLEED, BLEED, title, f_bleed, BLEED)
        make_print_sheet.main(f_bleed, f_print, BLEED, 10)
        pymupdf.open(f_final)[0].get_pixmap(dpi=600).save(f_png)
        folders.append(folder)
    if zip_path:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for folder in folders:
                for n in NAMES:
                    z.write(os.path.join(out_dir, folder, n), folder + '/' + n)
        print('zip', zip_path)


if __name__ == '__main__':
    main(*sys.argv[1:3])
