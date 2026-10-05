#!/usr/bin/env python3
"""Chromium rounds the page size of a pdf up (498.96 x 708.96 pt); this sets MediaBox / CropBox / TrimBox of every page of the given pdf files to exactly 176 x 250 mm
(the artwork is laid out from the top left corner, so the surplus is cut from the bottom and the right edge).   usage: python trim_pdf.py file.pdf [...]"""
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

W, H = 176 / 25.4 * 72, 250 / 25.4 * 72

for path in sys.argv[1:]:
    r = PdfReader(path)
    w = PdfWriter()
    for pg in r.pages:
        top = float(pg.mediabox.top)
        box = RectangleObject([0, top - H, W, top])
        for name in ('mediabox', 'cropbox', 'trimbox', 'bleedbox', 'artbox'):
            setattr(pg, name, box)
        w.add_page(pg)
    with open(path, 'wb') as f:
        w.write(f)
