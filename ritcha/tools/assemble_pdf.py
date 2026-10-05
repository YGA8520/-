#!/usr/bin/env python3
"""Front matter and back cover of the previous booklet put around the rendered text pages of the Ritcha booklet, everything in B5 (176 x 250 mm):

    cover (make_cover_ritcha.py)  |  credits page (output/credits.jpg)  |  the text pages  |  empty page  |  back cover (output/back-cover.pdf)

The cover, the credits page and the back cover are B5 artwork and are used as they are.  The text pages are designed and rendered on A4
(render.sh); here every page is scaled to B5 with everything on it - text, borders, header, page number - so the page count and the layout
are the same and only the size changes (x 0.838 across, x 0.842 down: the proportions of A4 and B5 differ by 0.5 %, not visible).
None of the pages around the text is numbered: the page numbers of the text pages still start with א on the first text page.

usage: python3 assemble_pdf.py cover.pdf credits.jpg body.pdf back.pdf out_booklet.pdf out_cover.pdf"""
import shutil
import sys
import pymupdf as fitz

cover_src, credits_img, body_src, back_src, out_booklet, out_cover = sys.argv[1:7]

W, H = 498.96, 708.96                                      # B5: 176 x 250 mm


def new_page(doc):
    return doc.new_page(width=W, height=H)


book = fitz.open()

cover = fitz.open(cover_src)
assert abs(cover[0].rect.width - W) < 0.1 and abs(cover[0].rect.height - H) < 0.1
book.insert_pdf(cover)

new_page(book).insert_image(fitz.Rect(0, 0, W, H), filename=credits_img, keep_proportion=False)      # credits page

body = fitz.open(body_src)
for n in range(body.page_count):                           # text pages: A4 -> B5
    new_page(book).show_pdf_page(fitz.Rect(0, 0, W, H), body, n, keep_proportion=False)

new_page(book)                                             # empty page in front of the back cover
back = fitz.open(back_src)
assert abs(back[0].rect.width - W) < 0.1 and abs(back[0].rect.height - H) < 0.1
book.insert_pdf(back)

md = dict(body.metadata or {}); md['title'] = 'ריתחא דאורייתא'
book.set_metadata(md)
book.save(out_booklet, garbage=3, deflate=True)
shutil.copyfile(cover_src, out_cover)
print('pages: %d (cover, credits, %d text pages, empty page, back cover), page size %.2f x %.2f pt' % (book.page_count, body.page_count, W, H))
