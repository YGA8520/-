#!/usr/bin/env python3
"""Assemble the booklet:  work/units.json -> output/mivchanei-hasimanim.pdf

  cover | inner title | credits | contents | (notes) | body (dividers + units, running head + page numbers) | (notes) | back cover
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'design'))
sys.path.insert(0, os.path.join(ROOT, '.deps'))
import front  # noqa: E402
import body  # noqa: E402
from common import hebrew_num  # noqa: E402
from manifest import PARTS  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

B = os.path.join(ROOT, 'build')
OUT = os.path.join(ROOT, 'output')
os.makedirs(B, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def render(jobs):
    p = os.path.join(B, 'jobs.json')
    json.dump(jobs, open(p, 'w'))
    subprocess.run(['node', os.path.join(ROOT, 'tools', 'render.js'), p], check=True, cwd=ROOT)


def markers(pdf):
    import pymupdf
    d = pymupdf.open(pdf)
    found = {}
    for i, pg in enumerate(d):
        for m in re.finditer(r'MK([A-Za-z0-9]+)MK', pg.get_text()):
            found.setdefault(m.group(1), i + 1)
    return found, len(d)


def hn(n, quotes=True):
    return hebrew_num(n, quotes)


def num_label(n):
    """page number for the footer: א  ב  ... י״ב  (no geresh on single letters)"""
    s = hebrew_num(n, True)
    return s[:-1] if len(s) == 2 and s.endswith('׳') else s


def running_head(u):
    k = u['kicker']
    if u['kind'] == 'chavura':
        return k + ' · ' + (u.get('sub') or '').split(' ·')[0]
    if u['kind'] in ('key', 'sheet') and u['title'].startswith('הלכות'):
        return k + ' · ' + u['title']
    return k + ' · ' + u['title']


def notes_page():
    lines = ''.join('<i></i>' for _ in range(22))
    return ('<div class="pg notes"><img class="bg" src="art/ref-frame.jpg"/><div class="nt">הערות</div><div class="nl">' + lines + '</div></div>')


NOTES_CSS = '''
.notes .nt{position:absolute;top:30mm;left:0;right:0;text-align:center;font-family:'Suez',serif;font-size:22pt;color:#14264a}
.notes .nt:after{content:'';display:block;height:.35mm;background:linear-gradient(90deg,transparent,#b98f36,transparent);margin:2mm auto 0;width:70mm}
.notes .nl{position:absolute;top:52mm;left:28mm;right:28mm}
.notes .nl i{display:block;height:9.2mm;border-bottom:.28mm solid #b9a97e}
'''


def main():
    units = json.load(open(os.path.join(ROOT, 'work', 'units.json'), encoding='utf8'))
    umap = {u['id']: u for u in units}
    parts = [p for p in PARTS if any(u['part'] == p['id'] for u in units)]

    # ---------------- pass A: body with placeholder dividers ----------------
    def divider_html(part, pages_map):
        us = [dict(kicker=u['kicker'], title=u['title'], sub=u.get('sub'), page=hn(pages_map.get(u['id'], 1)))
              for u in units if u['part'] == part['id']]
        return front.divider_page(part, us, 1)

    dh = {p['id']: divider_html(p, {}) for p in parts}
    open(os.path.join(B, 'body.html'), 'w', encoding='utf8').write(body.build_body(units, parts, dh))
    render([dict(html='build/body.html', pdf='build/body.pdf')])
    mk, n_pages = markers(os.path.join(B, 'body.pdf'))
    # ---------------- pass B: real page numbers in the dividers ----------------
    pages_map = {u['id']: mk[u['id']] for u in units}
    dh = {p['id']: divider_html(p, pages_map) for p in parts}
    open(os.path.join(B, 'body.html'), 'w', encoding='utf8').write(body.build_body(units, parts, dh))
    render([dict(html='build/body.html', pdf='build/body.pdf')])
    mk2, n_pages = markers(os.path.join(B, 'body.pdf'))
    assert mk2 == mk, 'pagination changed between passes'
    print('body pages', n_pages)

    # ---------------- contents ----------------
    toc = front.toc_html(parts, units, pages_map, lambda n: hn(n))
    open(os.path.join(B, 'toc.html'), 'w', encoding='utf8').write(toc)
    render([dict(html='build/toc.html', pdf='build/toc.pdf')])
    k = len(PdfReader(os.path.join(B, 'toc.pdf')).pages)
    blank = 0 if (k % 2 == 1) else 1          # body page 1 must be an odd (left-hand) physical page: 4 + k + blank odd
    front_n = 3 + k + blank
    total = front_n + n_pages + 1
    pad = (-total) % 4
    print('toc pages', k, 'blank', blank, 'pad', pad, 'total', total + pad)

    # ---------------- cover, inner title, credits, notes, back cover ----------------
    npages = [notes_page()]
    fr = front.doc([front.cover(), front.inner_title(), front.credits(), front.back_cover()] + npages + [front.frame_page()], 'front',
                   front.CREDITS_CSS + front.RING_CSS + NOTES_CSS)
    open(os.path.join(B, 'front.html'), 'w', encoding='utf8').write(fr)

    # ---------------- running head + page numbers overlay ----------------
    page_unit = {}
    first_pages = set()
    divider_pages = set()
    order = sorted([(pg, name) for name, pg in mk.items()])
    for idx, (pg, name) in enumerate(order):
        nxt = order[idx + 1][0] if idx + 1 < len(order) else n_pages + 1
        for q in range(pg, nxt):
            page_unit[q] = name
        if name.startswith('part'):
            divider_pages.add(pg)
        else:
            first_pages.add(pg)
    ov = []
    for i in range(1, n_pages + 1):
        name = page_unit.get(i)
        if name is None or name.startswith('part'):
            ov.append('<div class="op"></div>')
            continue
        u = umap[name]
        odd = i % 2 == 1
        left, right = (17, 22) if odd else (22, 17)
        head = ''
        if i not in first_pages:
            head = (f'<div class="hd" style="left:{left}mm;right:{right}mm"><span class="r"><b></b>{running_head(u)}</span>'
                    f'<span class="l">מבחני הסימנים</span></div>')
        foot = (f'<div class="ft" style="left:{left}mm;right:{right}mm"><span class="fl"></span><span class="fn">'
                f'<img src="art/ring.png"><span>{num_label(i)}</span></span><span class="fl e"></span></div>')
        ov.append(f'<div class="op">{head}{foot}</div>')
    ocss = '''
@page{size:210mm 297mm;margin:0}
html,body{margin:0;padding:0;background:transparent}
.op{width:210mm;height:297mm;position:relative;break-after:page;overflow:hidden}
.hd{position:absolute;top:12.2mm;display:flex;justify-content:space-between;align-items:center;padding-bottom:1.8mm;
    border-bottom:.45mm solid transparent;border-image:linear-gradient(90deg,#8c6a27,#d9bd78 50%,#8c6a27) 1;
    font-family:'Heebo',sans-serif;font-weight:600;font-size:7.8pt;letter-spacing:.06em;color:#6d7384;direction:rtl}
.hd .r b{display:inline-block;width:1.7mm;height:1.7mm;background:linear-gradient(135deg,#f0dc9a,#a8802f);transform:rotate(45deg);margin-left:2mm;vertical-align:.1mm}
.hd .l{font-family:'Suez',serif;font-weight:400;font-size:9pt;letter-spacing:.02em;color:#14264a;opacity:.8}
.ft{position:absolute;bottom:7.2mm;display:flex;justify-content:center;align-items:center;gap:2.6mm;direction:rtl}
.ft .fl{flex:0 0 28mm;height:.5mm;background:linear-gradient(90deg,transparent,#b98f36 60%,#8c6a27)}
.ft .fl.e{transform:scaleX(-1)}
.ft .fn{position:relative;width:11.4mm;height:11.4mm;flex:0 0 11.4mm}
.ft .fn img{position:absolute;left:-.1mm;top:-.1mm;width:11.7mm;height:11.7mm}
.ft .fn span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Suez',serif;font-size:9.6pt;color:#F6EBC8;line-height:1;
   text-shadow:.15mm .25mm 0 rgba(4,16,31,.65);padding-bottom:.2mm}
'''
    oh = f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>{body.font_face_css("../assets/fonts")}{ocss}</style></head><body>{"".join(ov)}</body></html>'
    open(os.path.join(B, 'overlay.html'), 'w', encoding='utf8').write(oh)

    render([dict(html='build/front.html', pdf='build/front.pdf'), dict(html='build/overlay.html', pdf='build/overlay.pdf')])

    # ---------------- merge ----------------
    fr_r = PdfReader(os.path.join(B, 'front.pdf'))
    toc_r = PdfReader(os.path.join(B, 'toc.pdf'))
    body_r = PdfReader(os.path.join(B, 'body.pdf'))
    ov_r = PdfReader(os.path.join(B, 'overlay.pdf'))
    w = PdfWriter()
    # front: 0 cover 1 inner 2 credits 3 back 4 notes 5 frame (under the contents)
    w.add_page(fr_r.pages[0])
    w.add_page(fr_r.pages[1])
    w.add_page(fr_r.pages[2])
    toc_start = len(w.pages)
    for p in toc_r.pages:
        p.merge_page(fr_r.pages[5], over=False)
        w.add_page(p)
        w.pages[-1].compress_content_streams()
    for _ in range(blank):
        w.add_page(fr_r.pages[4])
    body_start = len(w.pages)
    for i, p in enumerate(body_r.pages):
        p.merge_page(ov_r.pages[i])
        w.add_page(p)
        w.pages[-1].compress_content_streams()
    for _ in range(pad):
        w.add_page(fr_r.pages[4])
    w.add_page(fr_r.pages[3])

    # outline
    w.add_outline_item('שער', 0)
    w.add_outline_item('תוכן העניינים', toc_start)
    for p in parts:
        first = min(mk['part' + p['id']], *[mk[u['id']] for u in units if u['part'] == p['id']])
        par = w.add_outline_item(f"חלק {p['letter']}׳ – {p['name']}", body_start + first - 1)
        for u in units:
            if u['part'] == p['id']:
                w.add_outline_item(f"{u['kicker']} – {u['title']}", body_start + mk[u['id']] - 1, parent=par)
    w.add_metadata({'/Title': 'מבחני הסימנים', '/Author': 'ברומו של עולם', '/Subject': 'קובץ מבחנים בהלכות ברכות, קריאת שמע ותפילה'})
    w.page_mode = '/UseOutlines'
    try:
        w.compress_identical_objects()
    except Exception as e:
        print('compress skipped', e)
    out = os.path.join(OUT, 'mivchanei-hasimanim.pdf')
    with open(out, 'wb') as f:
        w.write(f)
    print('written', out, len(w.pages), 'pages')
    # the special pages as separate files
    fp = os.path.join(OUT, 'front-pages')
    os.makedirs(fp, exist_ok=True)
    final = PdfReader(out)
    for name, idx in (('cover', 0), ('inner-title', 1), ('credits', 2), ('back-cover', len(final.pages) - 1)):
        ww = PdfWriter()
        ww.add_page(final.pages[idx])
        with open(os.path.join(fp, name + '.pdf'), 'wb') as f:
            ww.write(f)
        subprocess.run(['pdftoppm', '-r', '130', '-png', '-singlefile', '-f', str(idx + 1), '-l', str(idx + 1), out, os.path.join(fp, name)], check=True)
    json.dump(dict(pages_map=pages_map, body_start=body_start, toc=k, blank=blank, pad=pad, total=len(w.pages)),
              open(os.path.join(B, 'layout.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
