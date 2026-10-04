#!/usr/bin/env python3
"""Draws the default ornaments (title flourish top/bottom, end-of-article ornament). Replace by the user's SVG files when provided."""
import math, os
OUT = os.path.join(os.path.dirname(__file__), 'assets', 'ornaments')

# one half (right half of a 280x64 box, centre line x=140). Drawn pointing UP (flourish above the base line y=56).
HALF = """
<!-- main scroll (outer curl) -->
<path d="M140 55 C142 36 156 22 172 22 C186 22 192 34 185 41 C179 47 169 44 169 37 C169 32 175 30 178 33" />
<!-- inner scroll -->
<path d="M140 55 C140 44 148 36 157 37 C165 38 166 47 159 48 C154 49 152 44 156 43" />
<!-- leaf sweep rising from centre to the right -->
<path d="M141 54 C150 50 160 52 168 49 C178 45 184 49 196 50 C206 51 212 47 222 49 C232 51 238 55 252 54" />
<path d="M141 55 C152 55 162 57 172 55 C184 53 192 56 204 56 C216 56 226 54 240 56" />
<!-- small curl at the far end -->
<path d="M222 49 C226 43 234 43 235 48 C236 52 231 53 230 50" />
<!-- teardrop leaves -->
<path d="M176 22 C176 14 184 10 190 14 C186 16 182 18 176 22 Z" fill="currentColor"/>
<path d="M196 50 C199 44 206 42 211 45 C207 47 203 49 196 50 Z" fill="currentColor"/>
<path d="M160 36 C158 30 162 26 168 27 C165 30 163 33 160 36 Z" fill="currentColor"/>
<!-- dotted tail -->
<circle cx="246" cy="53.5" r="1.3" fill="currentColor" stroke="none"/>
<circle cx="252" cy="54.2" r="1.1" fill="currentColor" stroke="none"/>
<circle cx="258" cy="54.6" r="0.9" fill="currentColor" stroke="none"/>
<circle cx="263" cy="54.8" r="0.7" fill="currentColor" stroke="none"/>
<circle cx="214" cy="42" r="1.1" fill="currentColor" stroke="none"/>
<circle cx="219" cy="39.5" r="0.9" fill="currentColor" stroke="none"/>
<circle cx="186" cy="30" r="1.0" fill="currentColor" stroke="none"/>
"""

def svg(w, h, body, flip=False, cls=''):
    mirror = f'<g transform="translate({w},0) scale(-1,1)">{body}</g>'
    inner = f'<g>{body}</g>{mirror}'
    if flip:
        inner = f'<g transform="translate(0,{h}) scale(1,-1)">{inner}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" class="{cls}" '
            f'fill="none" stroke="currentColor" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>')

top = svg(280, 64, HALF)
bottom = svg(280, 64, HALF, flip=True)

# small end-of-article ornament: centred scroll without the long tails
END_HALF = """
<path d="M140 30 C141 18 150 10 160 10 C169 10 173 18 168 23 C164 27 157 25 157 20 C157 17 161 16 163 18" />
<path d="M141 31 C150 29 158 31 166 29 C174 27 180 30 190 30 C198 30 204 28 212 29" />
<path d="M141 31 C150 33 160 34 170 33 C180 32 188 34 198 33" />
<path d="M168 23 C170 15 178 12 183 15 C179 17 176 19 168 23 Z" fill="currentColor"/>
<circle cx="219" cy="29" r="1.2" fill="currentColor" stroke="none"/>
<circle cx="225" cy="29.3" r="1" fill="currentColor" stroke="none"/>
<circle cx="230" cy="29.4" r="0.8" fill="currentColor" stroke="none"/>
"""
end = svg(280, 40, END_HALF)

for name, s in (('top', top), ('bottom', bottom), ('end', end)):
    open(os.path.join(OUT, name + '.svg'), 'w').write(s)
print('ok')
