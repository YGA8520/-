#!/usr/bin/env python3
"""Print @font-face CSS for the bundled fonts, for HTML pages / artifacts.

  python3 font_face_css.py "Frank Ruhl Libre" "David Libre"            # url(...) relative to --base (default: fonts/)
  python3 font_face_css.py --base64 "Keter YG" > fonts.css              # self-contained: fonts embedded as data: URIs
  python3 font_face_css.py --list                                       # family names available

Without names: every family. woff2/woff/ttf/otf are all accepted by browsers; --base64 makes one file that needs no other assets
(mind the size: ~1.33x the font files, and artifacts are limited to 16MB).
"""
import argparse, base64, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FMT = {'.ttf': 'truetype', '.otf': 'opentype', '.woff': 'woff', '.woff2': 'woff2'}
MIME = {'.ttf': 'font/ttf', '.otf': 'font/otf', '.woff': 'font/woff', '.woff2': 'font/woff2'}

ap = argparse.ArgumentParser()
ap.add_argument('families', nargs='*')
ap.add_argument('--base', default='fonts/', help='URL prefix replacing "fonts/" in the generated src (ignored with --base64)')
ap.add_argument('--base64', action='store_true')
ap.add_argument('--list', action='store_true')
a = ap.parse_args()

cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))['families']
if a.list:
    print('\n'.join(cat)); sys.exit()
want = a.families or list(cat)
out = []
for fam in want:
    if fam not in cat:
        sys.exit('unknown family %r (see --list)' % fam)
    for f in cat[fam]['fonts']:
        rel = f['file'].split('#')[0]
        ext = os.path.splitext(rel)[1].lower()
        if ext not in FMT:
            print('/* skipped %s: .ttc collections cannot be used by @font-face */' % rel, file=sys.stderr); continue
        if a.base64:
            src = 'data:%s;base64,%s' % (MIME[ext], base64.b64encode(open(os.path.join(HERE, rel), 'rb').read()).decode())
        else:
            src = a.base.rstrip('/') + '/' + rel[len('fonts/'):]
        ax = f.get('variable_axes', {}).get('wght')
        weight = '%d %d' % (ax[0], ax[2]) if ax else f['weight']
        out.append('@font-face{font-family:"%s";src:url("%s") format("%s");font-weight:%s;font-style:%s;font-display:swap}' % (
            fam, src, FMT[ext], weight, 'italic' if f['italic'] else 'normal'))
print('\n'.join(out))
