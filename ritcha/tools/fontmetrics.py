"""Glyph metrics of the supplied fonts (Tehila, RimonMF, Gisha) – used for centring and for choosing frame widths."""
import os, re
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FILES = {'tehila': 'TEHILAREGULAR.TTF', 'rimon': 'RIMON.TTF', 'gisha': 'GISHA.TTF', 'gishabd': 'GISHABD.TTF'}
_cache = {}

def font(key):
    if key not in _cache:
        fn = [f for f in os.listdir(D) if f.upper().endswith(FILES[key])][0]
        t = TTFont(os.path.join(D, fn))
        _cache[key] = t
    return _cache[key]

def to_rimon(text):
    """RimonMF is a legacy font: the Hebrew letters live at the cp1255 positions of its symbol map (U+F0E0..F0FA).
    Used only for the LibreOffice preview; Word gets ordinary Hebrew text."""
    out = []
    for ch in text:
        if 0x5D0 <= ord(ch) <= 0x5EA: out.append(chr(0xF000 + ch.encode('cp1255')[0]))
        else: out.append(ch)
    return ''.join(out)

def _cmap(key):
    t = font(key)
    if key == 'rimon': return t['cmap'].tables[2].cmap
    return t.getBestCmap()

def text_width(text, key, size):
    t = font(key); cm = _cmap(key); hm = t['hmtx']; upm = t['head'].unitsPerEm
    if key == 'rimon': text = to_rimon(text)
    w = 0
    for ch in text:
        g = cm.get(ord(ch))
        if g: w += hm[g][0]
    return w * size / upm

def rimon_ink(letters):
    """vertical ink range (units/1000 em) and horizontal overhangs of a string of Hebrew letters set in RimonMF.
    returns dict(ymin, ymax, left_off, right_off) – left_off/right_off: distance (em/1000) from the edge of the advance box
    to the ink on the visual left / right side (right-to-left text: first letter is on the right)."""
    t = font('rimon'); cm = _cmap('rimon'); hm = t['hmtx']; gs = t.getGlyphSet()
    ymin, ymax = 10 ** 6, -10 ** 6
    info = []
    for ch in letters:
        g = cm[ord(to_rimon(ch))]
        bp = BoundsPen(gs); gs[g].draw(bp)
        x0, y0, x1, y1 = bp.bounds
        ymin = min(ymin, y0); ymax = max(ymax, y1)
        info.append((x0, x1, hm[g][0]))
    first, last = info[0], info[-1]               # first letter = visual right
    return dict(ymin=ymin, ymax=ymax, left_off=last[0], right_off=first[2] - first[1])
