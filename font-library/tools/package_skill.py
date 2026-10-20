#!/usr/bin/env python3
"""Pack the font library into upload-ready skill zips under dist/.

  python3 tools/package_skill.py                 -> several zips in dist/, each under claude.ai's 30 MB (uncompressed) skill limit

The library is split by what the fonts are for (Hebrew / Latin serif / Latin sans / Latin display-script-mono), and any group
that is still too big is split again by size. Symbol, CJK/Indic and icon fonts are left out (the list is printed).
Every zip holds the same SKILL.md rules, its own catalog and the helper scripts. Run build_catalog.py first.
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

LIMIT_MB = 28        # claude.ai refuses a skill zip whose UNCOMPRESSED size exceeds 30 MB; stay under with margin
TRIGGER = ("Use whenever the output has typography that matters - HTML pages and artifacts, PDFs, Word/PowerPoint files, posters, covers, "
           "booklets, charts or images with text - or when the user mentions fonts, typefaces, גופן, גופנים, פונט, עימוד or typesetting. "
           "Pick the best-fitting font for each role from the catalog instead of defaulting to generic system fonts.")
# skill name -> (what it holds, which families belong to it)
PURPOSE = {
    'my-fonts-hebrew': "The user's personal Hebrew fonts: every family with Hebrew letters (traditional sefarim faces such as Frank-Ruehl, Vilna, Mantova, Rashi, Stam; modern sans and display faces; handwriting).",
    'my-fonts-latin-serif': "The user's personal Latin (English) serif text faces and titling serifs.",
    'my-fonts-latin-sans': "The user's personal Latin (English) sans-serif text and UI faces.",
    'my-fonts-latin-display': "The user's personal Latin (English) display, script, handwriting, novelty and monospace faces.",
}


def skill_of(cat, hebrew):
    if hebrew:
        return 'my-fonts-hebrew'
    c = cat.split(' ')[0]
    return {'serif': 'my-fonts-latin-serif', 'sans': 'my-fonts-latin-sans'}.get(c, 'my-fonts-latin-display')


def description(name, fams):
    names = ', '.join(fams)
    head = PURPOSE[re_base(name)] + ' '
    tail = ' Includes: ' + names
    d = head + TRIGGER + tail
    return d if len(d) <= 1000 else d[:996].rsplit(',', 1)[0] + ' ...'


def re_base(name):
    return name.rsplit('-part', 1)[0]


def family_bytes(rs):
    return sum({r['file'].split('#')[0]: r['bytes'] for r in rs}.values())


def split_by_size(fams, limit_mb):
    """smallest families first, new part when the next one would not fit (heavy system families end up together in the last part)"""
    parts, cur, size = [], {}, 0
    for n, rs in sorted(fams.items(), key=lambda kv: (family_bytes(kv[1]), kv[0])):
        b = family_bytes(rs)
        if cur and size + b > limit_mb * 1e6:
            parts.append(cur); cur, size = {}, 0
        cur[n] = rs; size += b
    if cur:
        parts.append(cur)
    return parts


def build(name, fams, notes):
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
    open(os.path.join(tmp, 'SKILL.md'), 'w', encoding='utf-8').write('---\nname: %s\ndescription: %s\n---%s' % (name, json.dumps(description(name, list(fams)), ensure_ascii=False), body))
    json.dump({'families': {n: {'notes': notes.get(n, {}), 'fonts': rs} for n, rs in fams.items()}}, open(os.path.join(tmp, 'catalog.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(tmp, 'FONTS.md'), 'w', encoding='utf-8').write(markdown(fams, notes))
    out = os.path.join(DIST, name + '.zip')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fs in os.walk(tmp):
            for f in sorted(fs):
                p = os.path.join(dp, f)
                z.write(p, os.path.join(name, os.path.relpath(p, tmp)))
    shutil.rmtree(tmp)
    with zipfile.ZipFile(out) as z:
        raw = sum(i.file_size for i in z.infolist()) / 1e6
    print('%-26s %3d families, %3d files, %.1f MB zipped, %.1f MB uncompressed' % (name + '.zip', len(fams), len(files), os.path.getsize(out) / 1e6, raw))
    if raw > 30:
        sys.exit('! %s is %.1f MB uncompressed; claude.ai refuses skills above 30 MB' % (name, raw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit-mb', type=float, default=LIMIT_MB, help='uncompressed font bytes per skill (default %d)' % LIMIT_MB)
    a = ap.parse_args()
    cat_path = os.path.join(SKILL, 'catalog.json')
    if not os.path.exists(cat_path):
        sys.exit('catalog.json missing - run tools/build_catalog.py first')
    cat = json.load(open(cat_path, encoding='utf-8'))['families']
    notes = {n: v['notes'] for n, v in cat.items()}
    fam = group([r for v in cat.values() for r in v['fonts']])
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    skills, left = {}, []
    for n, rs in fam.items():
        c = notes[n].get('category', '')
        heb = any(r['hebrew'] != 'none' for r in rs)
        if c.startswith(SKIP_CATEGORY) or any(r['bytes'] / 1e6 > MAX_FILE_MB for r in rs) or (not heb and all(r['latin'] == 'none' for r in rs)):
            left.append(n)
        else:
            skills.setdefault(skill_of(c, heb), {})[n] = rs
    for base, fams in sorted(skills.items()):
        parts = split_by_size(fams, a.limit_mb)
        for i, part in enumerate(parts, 1):
            build(base if len(parts) == 1 else '%s-part%d' % (base, i), part, notes)
    if left:
        print('left out (symbol / other-script / oversized files): %d families\n  %s' % (len(left), ', '.join(left)))


if __name__ == '__main__':
    main()
