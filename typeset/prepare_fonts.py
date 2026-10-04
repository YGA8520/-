#!/usr/bin/env python3
"""Prepare the client's proprietary fonts for the browser engine (the originals are never committed):

  Drogolin (DROG.TTF / DROGB_0.TTF)  an old Hebrew font whose letters sit at the cp1255 code points (0xE0..0xFA) of a symbol cmap;
                                     DrogolinU-*.ttf = a copy with a Unicode cmap (U+05D0..U+05EA -> the same glyphs)
  FrankRuehl DP (FRANK.OTF / ...)    draws U+05F3 / U+05F4 empty (its ASCII ' and " are the geresh / gershayim);
                                     FrankRuehlDP-Q-*.otf = a copy that maps U+05F3 / U+05F4 onto those two glyphs
  Ashcnz (ASHCNZ.TTF / ASHCNZB.TTF) same legacy encoding as Drogolin: AshcnzU-*.ttf
  Asher, Livorna                     used as is

usage: python prepare_fonts.py <folder with the original font files>   (the names are matched by the family name inside the files)
"""
import glob, os, shutil, sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts')


def info(path):
    t = TTFont(path)
    n = t['name']
    return (n.getDebugName(16) or n.getDebugName(1)), (n.getDebugName(17) or n.getDebugName(2)), t


def drogolin_unicode(t, dst):
    base = t['cmap'].tables[0].cmap
    uni = {}
    for i in range(0x5d0, 0x5eb):
        g = base.get(0xF000 + 0xE0 + (i - 0x5d0)) or base.get(0xE0 + (i - 0x5d0))
        assert g, hex(i)
        uni[i] = g
    for c in range(0x20, 0x7f):
        g = base.get(0xF000 + c)
        if g:
            uni[c] = g
    st = CmapSubtable.newSubtable(4)
    st.platformID, st.platEncID, st.language, st.cmap = 3, 1, 0, uni
    t['cmap'].tables = [st]
    t.save(dst)


def frank_quotes(t, dst):
    for st in t['cmap'].tables:
        if st.isUnicode():
            st.cmap[0x5f3], st.cmap[0x5f4] = 'quotesingle', 'quotedbl'
    t.save(dst)


if __name__ == '__main__':
    src = sys.argv[1]
    for f in glob.glob(os.path.join(src, '*')):
        if not f.lower().endswith(('.ttf', '.otf')):
            continue
        fam, sub, t = info(f)
        kind = 'Bold' if 'Bold' in (sub or '') else 'Regular'
        if fam in ('Drogolin', 'Ashcnz'):                    # both: legacy cp1255-encoded fonts of the same maker
            drogolin_unicode(t, os.path.join(OUT, f'{fam}U-{kind}.ttf')); print(fam, kind)
        elif fam == 'FrankRuehl DP':
            shutil.copy(f, os.path.join(OUT, f'FrankRuehlDP-{kind}.otf'))
            frank_quotes(TTFont(f), os.path.join(OUT, f'FrankRuehlDP-Q-{kind}.otf')); print('FrankRuehl DP', kind)
        elif fam == 'Asher':
            shutil.copy(f, os.path.join(OUT, f'Asher-{kind}.ttf')); print('Asher', kind)
        elif fam == 'Livorna':
            shutil.copy(f, os.path.join(OUT, 'Livorna-Regular.ttf')); print('Livorna')
