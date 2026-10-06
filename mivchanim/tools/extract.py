#!/usr/bin/env python3
"""Extract logical-order Hebrew text + geometry + inline style from the source PDF.

The source PDF was exported from Word (RTL) and later edited in PDF-XChange, so the
character order in the content stream is not logical and stray space characters
sit at odd positions.  We therefore:
  * take every glyph with its position (PyMuPDF rawdict),
  * group glyphs into visual lines by baseline, split a line into cells at wide gaps,
  * ignore the stream's space glyphs and re-create spaces from the gaps,
  * convert the visual (left-to-right) sequence into logical order with the
    Unicode bidi algorithm (python-bidi 0.4.2 internals, so every glyph keeps its index
    and therefore its style),
and write one JSON file with lines: text runs (text, bold, italic, underline, size),
bbox, baseline, font.
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '.deps'))
import pymupdf  # noqa: E402
from bidi import algorithm as B  # noqa: E402

SRC = os.path.join(HERE, '..', 'src', 'all-tests.pdf')
OUT = os.path.join(HERE, '..', 'work', 'lines.json')


def visual_to_logical(chars):
    """chars: list of dicts with 'c' in visual (left->right) order. Returns chars in logical order."""
    text = ''.join(ch['c'] for ch in chars)
    storage = B.get_empty_storage()
    storage['base_level'] = 1
    storage['base_dir'] = 'R'
    B.get_embedding_levels(text, storage, False, False)
    for i, e in enumerate(storage['chars']):
        e['idx'] = i
    B.explicit_embed_and_overrides(storage, False)
    B.resolve_weak_types(storage, False)
    B.resolve_neutral_types(storage, False)
    B.resolve_implicit_levels(storage, False)
    B.reorder_resolved_levels(storage, False)
    # no mirroring: the PDF keeps logical bracket codes (mirrored glyphs are chosen by the font)
    out = []
    for e in storage['chars']:
        ch = dict(chars[e['idx']])
        ch['c'] = e['ch']
        out.append(ch)
    # reorder_resolved_levels produces the *display* order of a logical string; we fed it a
    # visual string, so what we get is the logical order of the original text.
    return out


def page_underlines(page):
    """horizontal thin rects / lines -> list of (x0, x1, y)"""
    res = []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                p1, p2 = it[1], it[2]
                if abs(p1.y - p2.y) < 0.6 and abs(p1.x - p2.x) > 6:
                    res.append((min(p1.x, p2.x), max(p1.x, p2.x), p1.y, d.get('width') or 1))
            elif it[0] == 're':
                r = it[1]
                if r.height < 1.6 and r.width > 6:
                    res.append((r.x0, r.x1, (r.y0 + r.y1) / 2, r.height))
    return res


def extract_page(page):
    rd = page.get_text('rawdict', flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_PRESERVE_LIGATURES)
    glyphs = []
    for b in rd['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            for s in l['spans']:
                font = s['font']
                bold = 'Bold' in font or 'bold' in font or bool(s['flags'] & 16)
                ital = bool(s['flags'] & 2)
                for c in s['chars']:
                    x0, y0, x1, y1 = c['bbox']
                    glyphs.append(dict(c=c['c'], x0=x0, x1=x1, y0=y0, y1=y1, base=c['origin'][1],
                                       size=s['size'], font=font, bold=bold, ital=ital, sp=c['c'].isspace()))
    ul = page_underlines(page)
    for g in glyphs:
        g['ul'] = any(u[0] - 1 <= (g['x0'] + g['x1']) / 2 <= u[1] + 1 and g['base'] - 1 <= u[2] <= g['base'] + 4.5 for u in ul)
    # group by baseline
    glyphs.sort(key=lambda g: g['base'])
    lines = []
    for g in glyphs:
        if lines and abs(g['base'] - lines[-1]['base']) <= max(2.2, 0.28 * g['size']):
            L = lines[-1]
            L['g'].append(g)
            L['base'] = sum(x['base'] for x in L['g']) / len(L['g'])
        else:
            lines.append(dict(base=g['base'], g=[g]))
    out = []
    for L in lines:
        spaces = [(g['x0'] + g['x1']) / 2 for g in L['g'] if g['sp']]
        gs = sorted([g for g in L['g'] if not g['sp']], key=lambda g: (g['x0'] + g['x1']) / 2)
        if not gs:
            continue
        # split into cells at wide gaps
        cells, cur = [], [gs[0]]
        for a, b in zip(gs, gs[1:]):
            gap = b['x0'] - a['x1']
            if gap > max(22.0, 2.2 * a['size']):
                cells.append(cur)
                cur = []
            cur.append(b)
        cells.append(cur)
        for cell in cells:
            seq = []
            prev = None
            gaps = [b['x0'] - a['x1'] for a, b in zip(cell, cell[1:])]
            # fonts whose glyph boxes overlap (e.g. Keren): gaps are meaningless, trust the stream's spaces
            trust_spaces = bool(gaps) and sum(1 for x in gaps if x < -2.0) / len(gaps) > 0.25
            for g in cell:
                if prev is not None:
                    gap = g['x0'] - prev['x1']
                    sz = min(g['size'], prev['size'])
                    cxa, cxb = (prev['x0'] + prev['x1']) / 2, (g['x0'] + g['x1']) / 2
                    if (not trust_spaces and gap > 0.17 * sz) or (trust_spaces and any(cxa < sx < cxb for sx in spaces)):
                        seq.append(dict(c=' ', bold=prev['bold'] and g['bold'], ital=False, ul=prev['ul'] and g['ul'],
                                        size=sz, x0=prev['x1'], x1=g['x0'], y0=g['y0'], y1=g['y1'], base=g['base'], font=g['font']))
                seq.append(g)
                prev = g
            logical = visual_to_logical(seq)
            runs = []
            for ch in logical:
                key = (ch['bold'], ch['ital'], ch['ul'], round(ch['size'] * 2) / 2)
                if runs and runs[-1]['k'] == key:
                    runs[-1]['t'] += ch['c']
                else:
                    runs.append(dict(k=key, t=ch['c']))
            x0 = min(g['x0'] for g in cell)
            x1 = max(g['x1'] for g in cell)
            y0 = min(g['y0'] for g in cell)
            y1 = max(g['y1'] for g in cell)
            fonts = {}
            for g in cell:
                fonts[g['font']] = fonts.get(g['font'], 0) + 1
            out.append(dict(
                x0=round(x0, 1), x1=round(x1, 1), y0=round(y0, 1), y1=round(y1, 1), base=round(L['base'], 1),
                font=max(fonts, key=fonts.get),
                runs=[dict(t=r['t'], b=r['k'][0], i=r['k'][1], u=r['k'][2], s=r['k'][3]) for r in runs]))
    out.sort(key=lambda l: (round(l['base'] / 2.5), -l['x1']))
    return out


def main():
    doc = pymupdf.open(SRC)
    pages = []
    for i, page in enumerate(doc):
        pages.append(dict(n=i + 1, w=page.rect.width, h=page.rect.height, lines=extract_page(page)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf8') as f:
        json.dump(pages, f, ensure_ascii=False)
    print('pages', len(pages), 'lines', sum(len(p['lines']) for p in pages))


if __name__ == '__main__':
    main()
