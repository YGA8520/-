"""The title of the colour page (בס״ד + 'הכוונות קודם / תפילת שמונה עשרה' in Taamim) as a PDF of its own.

python make_title_asset.py approved-final.pdf title-taamim.pdf

The Taamim font file is the client's and is not always at hand. The title is the same in every version of the page,
so it is taken once from an approved final-size PDF (3-גודל-סופי-8x11.pdf of any version, PLAIN): the images of the
page (the background) are removed and only the cartouche (x 20 - 60 mm, y 1.5 - 17.5 mm) is kept, i.e. the vector
text of בס״ד and of the title. The page keeps the size and the coordinates of the Chromium page, so make_versions.py
lays it 1:1 over a page rendered with #notitle (title and בס״ד hidden).
"""
import sys
import pymupdf

MM = 72 / 25.4
CLIP = pymupdf.Rect(20 * MM, 1.5 * MM, 60 * MM, 17.5 * MM)

def main(src, dst):
    doc = pymupdf.open(src)
    pg = doc[0]
    for img in pg.get_images(full=True):
        pg.delete_image(img[0])
    doc = pymupdf.open('pdf', doc.tobytes(garbage=3))   # show_pdf_page reads the saved state of the source
    pg = doc[0]
    out = pymupdf.open()
    op = out.new_page(width=pg.rect.width, height=pg.rect.height)
    # show_pdf_page(clip=) draws nothing once the images are gone, so the whole page is shown and a clip path
    # (PDF coordinates, origin at the foot) is written in front of it
    op.show_pdf_page(op.rect, doc, 0)
    x, y, w, h = CLIP.x0, op.rect.height - CLIP.y1, CLIP.width, CLIP.height
    xref = op.get_contents()[0]
    out.update_stream(xref, b'q %.3f %.3f %.3f %.3f re W n\n' % (x, y, w, h) + out.xref_stream(xref) + b'\nQ')
    out.save(dst, garbage=4, deflate=True)
    print('title asset', dst, '%.2f x %.2f mm' % (pg.rect.width / MM, pg.rect.height / MM))

if __name__ == '__main__':
    main(*sys.argv[1:3])
