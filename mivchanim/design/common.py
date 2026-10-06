"""Design tokens and helpers shared by the cover, the inner pages and the body."""
import math
import os
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FONT_DIR = os.path.join(ROOT, 'assets', 'fonts')

# ---- colours (navy / gold taken from the organisation's logo) ----
NAVY = '#0E1A2B'
NAVY_2 = '#17294A'
NAVY_3 = '#223A63'
INK = '#141414'
GOLD_D = '#8C6A27'
GOLD_M = '#C9A24B'
GOLD_L = '#EBD28A'
IVORY = '#F6EEDB'
PAPER = '#FBF8F0'
RULE = '#C9BFA6'

# (family, weight) -> woff2 base name
FONTS = {
    'Frank': ('frank-ruhl-libre', [400, 500, 700, 900]),
    'Heebo': ('heebo', [400, 600, 800]),
    'Suez': ('suez-one', [400]),
}
HE_RANGE = 'U+0307-0308,U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F'
LA_RANGE = ('U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,'
            'U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD')


def font_face_css(rel='../assets/fonts'):
    out = []
    for fam, (base, weights) in FONTS.items():
        for w in weights:
            for sub, rng in (('hebrew', HE_RANGE), ('latin', LA_RANGE)):
                out.append(
                    "@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:block;"
                    "src:url('%s/%s-%s-%d-normal.woff2') format('woff2');unicode-range:%s;}" % (fam, w, rel, base, sub, w, rng))
    return '\n'.join(out)


# ---- measuring (for hand-placed curved text) ----
_TTF = {
    'Suez': os.path.join(ROOT, '..', 'typeset', 'assets', 'fonts', 'SuezOne-Regular.ttf'),
    'Frank': os.path.join(ROOT, '..', 'typeset', 'assets', 'fonts', 'FrankRuhlLibre.ttf'),
    'David': os.path.join(ROOT, '..', 'typeset', 'assets', 'fonts', 'DavidLibre-Regular.ttf'),
}
_cache = {}


def adv(ch, fam, size=100):
    key = (fam, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(_TTF[fam], size)
    return _cache[key].getlength(ch) / size  # em


def text_width_em(text, fam, spacing_em=0.0):
    return sum(adv(c, fam) + spacing_em for c in text) - spacing_em


def arc_text(text, cx, cy, r, fam, size, spacing_em=0.0, fill='currentColor', top=True, center_deg=90, extra=''):
    """Hebrew text laid out on a circle, one <text> per glyph, reading order preserved.

    top=True: text on the upper part of the ring, reading right->left (counter-clockwise),
              glyph tops pointing outward.
    top=False: text on the lower part, reading right->left too (clockwise as seen on screen),
               glyph tops pointing towards the centre (so it is readable, not upside down).
    r is the baseline radius.  center_deg = angle (degrees, math convention, 0 = right, 90 = top) of the text middle.
    """
    widths = [(adv(c, fam) + spacing_em) * size for c in text]
    total = sum(widths) - spacing_em * size
    out = []
    pos = 0.0
    for c, w in zip(text, widths):
        mid = pos + (w - spacing_em * size) / 2 - total / 2  # arc length offset from the middle, reading direction
        ang_off = mid / r  # radians
        if top:
            a = math.radians(center_deg) - ang_off  # reading right->left == angle increasing... see below
        else:
            a = math.radians(center_deg) + ang_off
        # reading right->left on top means angle increases (counter-clockwise)
        if top:
            a = math.radians(center_deg) + ang_off
        x = cx + r * math.cos(a)
        y = cy - r * math.sin(a)
        if top:
            rot = 90 - math.degrees(a)  # glyph up points outwards
        else:
            rot = 270 - math.degrees(a)  # glyph up points to the centre
        if c != ' ':
            out.append('<text x="0" y="0" transform="translate(%.3f %.3f) rotate(%.3f)" text-anchor="middle" '
                       'font-size="%.3f" fill="%s" %s>%s</text>' % (x, y, rot, size, fill, extra, c))
        pos += w
    return '\n'.join(out)


_HE_UNITS = [(400, 'ת'), (300, 'ש'), (200, 'ר'), (100, 'ק'), (90, 'צ'), (80, 'פ'), (70, 'ע'), (60, 'ס'), (50, 'נ'),
             (40, 'מ'), (30, 'ל'), (20, 'כ'), (10, 'י'), (9, 'ט'), (8, 'ח'), (7, 'ז'), (6, 'ו'), (5, 'ה'), (4, 'ד'),
             (3, 'ג'), (2, 'ב'), (1, 'א')]


def hebrew_num(n, quotes=True):
    """1 -> א׳, 15 -> ט״ו, 102 -> ק״ב"""
    s = ''
    for v, ch in _HE_UNITS:
        while n >= v:
            s += ch
            n -= v
    s = s.replace('יה', 'טו').replace('יו', 'טז')
    if not quotes:
        return s
    if len(s) == 1:
        return s + '׳'
    return s[:-1] + '״' + s[-1]
