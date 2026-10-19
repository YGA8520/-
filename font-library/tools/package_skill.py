#!/usr/bin/env python3
"""Zip my-fonts/ into dist/my-fonts.zip, ready for Settings > Capabilities > Skills."""
import os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, 'my-fonts')
OUT = os.path.join(ROOT, 'dist', 'my-fonts.zip')
for need in ('SKILL.md', 'catalog.json', 'FONTS.md'):
    if not os.path.exists(os.path.join(SKILL, need)):
        sys.exit('missing %s - run tools/build_catalog.py first' % need)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
n = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for dp, _, files in os.walk(SKILL):
        for f in sorted(files):
            if f == '.gitkeep' or f.endswith('.pyc'):
                continue
            p = os.path.join(dp, f)
            z.write(p, os.path.join('my-fonts', os.path.relpath(p, SKILL)))   # the folder name is the skill name
            n += 1
mb = os.path.getsize(OUT) / 1e6
print('wrote %s  (%d files, %.1f MB)' % (os.path.relpath(OUT, ROOT), n, mb))
if mb > 25:
    print('! large archive: split into several skills (e.g. hebrew-display, hebrew-text, latin) if the upload is refused')
