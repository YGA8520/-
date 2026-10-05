#!/usr/bin/env python3
"""cover page (made by make_cover_ritcha.py, 176 x 250 mm) -> A4 (the proportions differ by 0.5 %, the stretch is not visible) and put
in front of the booklet.  The cover is not numbered: the page numbers of the booklet still start with א on the first text page.

usage: python3 assemble_pdf.py cover.pdf booklet_body.pdf out_booklet.pdf out_cover_a4.pdf"""
import sys
import pymupdf as fitz

cover_src, body_src, out_booklet, out_cover = sys.argv[1:5]
body = fitz.open(body_src)
A4 = body[0].rect                          # exactly the page size of the booklet

cover = fitz.open()
p = cover.new_page(width=A4.width, height=A4.height)
src = fitz.open(cover_src)
p.show_pdf_page(p.rect, src, 0, keep_proportion=False)
cover.set_metadata({'title': 'ריתחא דאורייתא – עמוד שער'})
cover.save(out_cover, garbage=3, deflate=True)

book = fitz.open()
book.insert_pdf(cover)
book.insert_pdf(body)
md = dict(body.metadata or {}); md['title'] = 'ריתחא דאורייתא'
book.set_metadata(md)
book.save(out_booklet, garbage=3, deflate=True)
print('pages:', book.page_count, '| cover', out_cover)
