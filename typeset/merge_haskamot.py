#!/usr/bin/env python3
"""Inserts the haskama pages (node haskamot_build.js -> haskamot-silver.pdf) into a finished booklet PDF without changing the parity of any other page.

usage: python merge_haskamot.py booklet.pdf haskamot.pdf out.pdf --after N [--order 2,1,3] [--pad after|before]

  --after N   the physical page (1 = the cover) after which the block is inserted
  --order     the order of the haskamot, by their number in haskamot.pdf (default: as they are in the file)
  --pad       the block must have an even number of pages, or every later page changes from odd to even and back; a white page is added
              after the haskamot (default) or before them

The pages that follow the block are only shifted by an even number of pages: odd stays odd, even stays even.  Nothing inside the pages is touched, so a number
printed on a page (and a table of contents with page numbers) is NOT updated - for a booklet whose numbers are part of its pages, either the numbers are
unchanged because the block takes the place of pages that are already blank, or the booklet has to be rebuilt from its source."""
import argparse
import pymupdf


def merge(booklet, haskamot, out, after, order=None, pad='after'):
    b, h = pymupdf.open(booklet), pymupdf.open(haskamot)
    order = order or list(range(1, len(h) + 1))
    assert all(1 <= i <= len(h) for i in order), 'order refers to a page that does not exist'
    assert 1 <= after <= len(b), 'after is outside the booklet'
    rect = b[0].rect
    n_blank = (len(order)) % 2                      # one white page when the number of haskamot is odd
    seq = ([None] * n_blank if pad == 'before' else []) + [i - 1 for i in order] + ([None] * n_blank if pad == 'after' else [])
    for k, src in enumerate(seq):
        pg = b.new_page(pno=after + k, width=rect.width, height=rect.height)
        if src is not None:
            pg.show_pdf_page(rect, h, src)          # the vector page, fitted to the page size of the booklet
    assert len(seq) % 2 == 0
    b.save(out, garbage=3, deflate=True)
    # proof: every page of the booklet keeps its parity
    o = pymupdf.open(booklet)
    shift = len(seq)
    bad = [p for p in range(after + 1, len(o) + 1) if (p + shift) % 2 != p % 2]
    n = pymupdf.open(out)
    print(f'booklet {len(o)} pages -> {len(n)} pages | block {len(seq)} pages after page {after} ({len(order)} haskamot + {n_blank} white) | '
          f'later pages shifted by {shift} (parity changed on {len(bad)} pages)')
    return len(bad)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('booklet'), ap.add_argument('haskamot'), ap.add_argument('out')
    ap.add_argument('--after', type=int, required=True)
    ap.add_argument('--order', default='')
    ap.add_argument('--pad', choices=['after', 'before'], default='after')
    a = ap.parse_args()
    raise SystemExit(1 if merge(a.booklet, a.haskamot, a.out, a.after, [int(x) for x in a.order.split(',')] if a.order else None, a.pad) else 0)
