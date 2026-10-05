#!/usr/bin/env python3
"""Front matter and back cover of the previous booklet put around the rendered text pages of the Ritcha booklet:

    cover (make_cover_ritcha.py)  |  credits page (output/credits.jpg)  |  the text pages  |  [empty page]  |  back cover (output/back-cover.pdf)

All three artworks are 176 x 250 mm; they are stretched to the page size of the booklet (A4, the proportions differ by 0.5 %, not visible).
Neither the cover, the credits page nor the back cover is numbered: the page numbers of the text pages still start with א on the first text page.
The back cover has to be an odd page: when it would come out as an even page an empty page is put in front of it.

usage: python3 assemble_pdf.py cover.pdf credits.jpg body.pdf back.pdf out_booklet.pdf out_cover_a4.pdf"""
import sys
import pymupdf as fitz

cover_src, credits_img, body_src, back_src, out_booklet, out_cover = sys.argv[1:7]

body = fitz.open(body_src)
R = body[0].rect                                           # exactly the page size of the booklet


def pdf_page(path):
    d = fitz.open(); p = d.new_page(width=R.width, height=R.height)
    p.show_pdf_page(p.rect, fitz.open(path), 0, keep_proportion=False)
    return d


cover = pdf_page(cover_src)
cover.set_metadata({'title': 'ריתחא דאורייתא – עמוד שער'})
cover.save(out_cover, garbage=3, deflate=True)

credits = fitz.open(); cp = credits.new_page(width=R.width, height=R.height)
cp.insert_image(cp.rect, filename=credits_img, keep_proportion=False)

book = fitz.open()
book.insert_pdf(cover)
book.insert_pdf(credits)
book.insert_pdf(body)
blank = ''
if (book.page_count + 1) % 2 == 0:                          # the back cover would be an even page
    book.new_page(width=R.width, height=R.height); blank = ' (+ empty page before the back cover)'
book.insert_pdf(pdf_page(back_src))
md = dict(body.metadata or {}); md['title'] = 'ריתחא דאורייתא'
book.set_metadata(md)
book.save(out_booklet, garbage=3, deflate=True)
print('pages: %d%s, back cover = page %d' % (book.page_count, blank, book.page_count))
