#!/usr/bin/env python3
"""Pack the font library into upload-ready skill zips under dist/.

  python3 tools/package_skill.py                 -> dist/my-fonts-hebrew.zip + dist/my-fonts-latin.zip
  python3 tools/package_skill.py --max-mb 30     -> warn when a zip is bigger than this (default 25)

A single zip of everything is usually too big to upload, so the library is split by what the fonts are for:
  my-fonts-hebrew  every family that has Hebrew letters (the ones you will actually pick for Hebrew work)
  my-fonts-latin   Latin-only text/display/script families (symbol, CJK/Indic and icon fonts are left out, see the list printed)
Both zips contain the same SKILL.md rules, their own catalog and the helper scripts. Run build_catalog.py first.
"""
import argparse, json, os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL = os.path.join(ROOT, 'my-fonts')
DIST = os.path.join(ROOT, 'dist')
sys.path.insert(0, HERE)
from build_catalog import markdown, group   # noqa: E402

SKIP_CATEGORY = ('symbols', 'other scripts')
MAX_FILE_MB = 6      # a single file this large is a CJK/emoji/icon font, not a design font

DESC = {
    'my-fonts-hebrew': "The user's personal Hebrew fonts (every family with Hebrew letters, plus bundled files; includes traditional sefarim faces such as Frank-Ruehl, Vilna, Mantova, Rashi, Stam, and modern sans/display faces). Use whenever the output contains Hebrew or typography matters - HTML pages and artifacts, PDFs, Word/PowerPoint files, posters, covers, booklets, charts or images with text - or when the user mentions fonts, typefaces, גופן, גופנים, פונט, עימוד or typesetting. Pick the best-fitting font for each role (title, body, quote, commentary, numbers) from the catalog instead of defaulting to generic system fonts.",
    'my-fonts-latin': "The user's personal Latin (English) fonts: serif and sans text faces, display, script, handwriting and monospace families, with files bundled. Use for English/Latin text in any designed output (HTML, artifacts, PDF, Word/PowerPoint, posters, invitations, images) or when pairing a Latin face with Hebrew text; for Hebrew itself see the my-fonts-hebrew skill. Pick the best-fitting font for each role from the catalog instead of defaulting to generic fonts.",
}


def build(name, fams, notes, max_mb):
    tmp = os.path.join(DIST, 'build', name)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    files = set()
    for rs in fams.values():
        files |= {r['file'].split('#')[0] for r in rs}
    for rel in sorted(files):
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(SKILL, rel), dst)
    shutil.copytree(os.path.join(SKILL, 'scripts'), os.path.join(tmp, 'scripts'))
    md = open(os.path.join(SKILL, 'SKILL.md'), encoding='utf-8').read()
    body = md.split('---', 2)[2]
    open(os.path.join(tmp, 'SKILL.md'), 'w', encoding='utf-8').write('---\nname: %s\ndescription: %s\n---%s' % (name, DESC[name], body))
    json.dump({'families': {n: {'notes': notes.get(n, {}), 'fonts': rs} for n, rs in fams.items()}}, open(os.path.join(tmp, 'catalog.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(tmp, 'FONTS.md'), 'w', encoding='utf-8').write(markdown(fams, notes))
    out = os.path.join(DIST, name + '.zip')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(tmp):
            for f in sorted(fs):
                p = os.path.join(dp, f)
                z.write(p, os.path.join(name, os.path.relpath(p, tmp)))
    shutil.rmtree(tmp)
    mb = os.path.getsize(out) / 1e6
    print('%-16s %3d families, %3d files, %.1f MB' % (name + '.zip', len(fams), len(files), mb))
    if mb > max_mb:
        print('  ! bigger than %d MB: split further if the upload is refused' % max_mb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-mb', type=float, default=25)
    a = ap.parse_args()
    cat_path = os.path.join(SKILL, 'catalog.json')
    if not os.path.exists(cat_path):
        sys.exit('catalog.json missing - run tools/build_catalog.py first')
    cat = json.load(open(cat_path, encoding='utf-8'))['families']
    notes = {n: v['notes'] for n, v in cat.items()}
    fam = group([r for v in cat.values() for r in v['fonts']])
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    heb, lat, left = {}, {}, []
    for n, rs in fam.items():
        c = notes[n].get('category', '')
        big = any(r['bytes'] / 1e6 > MAX_FILE_MB for r in rs)
        if any(r['hebrew'] != 'none' for r in rs) and not c.startswith(SKIP_CATEGORY):
            heb[n] = rs
        elif c.startswith(SKIP_CATEGORY) or big or all(r['latin'] == 'none' for r in rs):
            left.append(n)
        else:
            lat[n] = rs
    build('my-fonts-hebrew', heb, notes, a.max_mb)
    build('my-fonts-latin', lat, notes, a.max_mb)
    if left:
        print('left out (symbol / other-script / oversized files): %d families\n  %s' % (len(left), ', '.join(left)))


if __name__ == '__main__':
    main()
