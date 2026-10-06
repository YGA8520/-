"""Cover, inner title page, credits page, part dividers, table of contents, back cover.

Two themes of the same design:  'dark'  = navy / gold (outer cover, back cover)
                                'light' = white / navy / gold (inner title page, credits, dividers, contents) - prints cheaper
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa: E402,F403

SIMAN_RING = ['ד', 'ח', 'מו', 'מז', 'מח', 'מט', 'נ', 'נא', 'נב', 'נג', 'נד', 'נה',
              'סא', 'סב', 'סג', 'סד', 'סה', 'סו', 'סט', 'ע', 'עא', 'עג', 'צב', 'קב']

PAGE_CSS = f'''
{font_face_css('../assets/fonts')}
@page {{ size: 210mm 297mm; margin: 0 }}
html,body {{ margin:0; padding:0; background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
.pg {{ width:210mm; height:297mm; position:relative; overflow:hidden; break-after:page; page-break-after:always; }}
.pg:last-child {{ break-after:auto; page-break-after:auto; }}
.pg > svg {{ position:absolute; left:0; top:0; width:210mm; height:297mm; display:block; }}
svg text {{ font-family:'Frank','David',serif; direction:rtl; }}
.layer {{ position:absolute; inset:0; }}
'''


def doc(pages, title, extra_css=''):
    body = ''.join(pages)
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{PAGE_CSS}{extra_css}</style></head><body>{body}</body></html>')


def svg_page(inner, dark=True, cls='pg'):
    return f'<div class="{cls}"><svg viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg">{inner}</svg></div>'


# --------------------------------------------------------------------------------------------
def defs(theme='dark'):
    gl = ('#6E4F17', '#B88F34', '#E3C46C', '#A57B28', '#6E4F17')   # gold on white: darker so it prints
    return f'''
<defs>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{GOLD_D}"/><stop offset=".22" stop-color="#D9B75F"/>
    <stop offset=".45" stop-color="#F4E4A8"/><stop offset=".68" stop-color="#C79E40"/><stop offset="1" stop-color="{GOLD_D}"/>
  </linearGradient>
  <linearGradient id="goldv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#F1DC96"/><stop offset=".5" stop-color="#C99F41"/><stop offset="1" stop-color="#8C6A27"/>
  </linearGradient>
  <linearGradient id="goldh" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{GOLD_D}"/><stop offset=".5" stop-color="#F0DB93"/><stop offset="1" stop-color="{GOLD_D}"/>
  </linearGradient>
  <linearGradient id="goldL" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{gl[0]}"/><stop offset=".3" stop-color="{gl[1]}"/><stop offset=".5" stop-color="{gl[2]}"/><stop offset=".72" stop-color="{gl[3]}"/><stop offset="1" stop-color="{gl[4]}"/>
  </linearGradient>
  <linearGradient id="goldLv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#D2AC52"/><stop offset=".55" stop-color="#A87F2C"/><stop offset="1" stop-color="#6E4F17"/>
  </linearGradient>
  <linearGradient id="goldLh" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#8C6A27"/><stop offset=".5" stop-color="#C9A24B"/><stop offset="1" stop-color="#8C6A27"/>
  </linearGradient>
  <linearGradient id="navyv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B4A80"/><stop offset="1" stop-color="#0E1A2B"/></linearGradient>
  <radialGradient id="bgd" cx=".5" cy=".36" r=".85">
    <stop offset="0" stop-color="#21396A"/><stop offset=".45" stop-color="#14264A"/><stop offset="1" stop-color="#070F1E"/>
  </radialGradient>
  <radialGradient id="disc" cx=".5" cy=".42" r=".7"><stop offset="0" stop-color="#27447C"/><stop offset="1" stop-color="#0F1E3A"/></radialGradient>
  <radialGradient id="discL" cx=".5" cy=".42" r=".7"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#F3ECDA"/></radialGradient>
  <linearGradient id="ribbon" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7A5A1F"/><stop offset=".18" stop-color="#D3AE55"/><stop offset=".5" stop-color="#F3E3A6"/>
    <stop offset=".82" stop-color="#C79E40"/><stop offset="1" stop-color="#6F5019"/>
  </linearGradient>
  <linearGradient id="ribbonL" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#8A6A2A"/><stop offset=".25" stop-color="#C9A24B"/><stop offset=".5" stop-color="#E6CD85"/>
    <stop offset=".8" stop-color="#B98F36"/><stop offset="1" stop-color="#7A5A1F"/>
  </linearGradient>
  <linearGradient id="fadeV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
  <mask id="fadeMask"><rect x="0" y="150" width="210" height="147" fill="url(#fadeV)"/></mask>
  <radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset=".6" stop-color="#4E78C4" stop-opacity=".30"/><stop offset="1" stop-color="#4E78C4" stop-opacity="0"/></radialGradient>
  <pattern id="grainP" width="40" height="40" patternUnits="userSpaceOnUse"><image href="../assets/img/grain.png" width="40" height="40"/></pattern>
  <radialGradient id="shadow" cx=".5" cy=".5" r=".5"><stop offset=".78" stop-color="#000" stop-opacity=".34"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
</defs>'''


class T:
    """theme tokens"""
    def __init__(self, theme):
        d = theme == 'dark'
        self.dark = d
        self.gold = 'url(#gold)' if d else 'url(#goldL)'
        self.goldv = 'url(#goldv)' if d else 'url(#goldLv)'
        self.goldh = 'url(#goldh)' if d else 'url(#goldLh)'
        self.disc = 'url(#disc)' if d else 'url(#discL)'
        self.text = IVORY if d else NAVY
        self.text2 = '#C9BFA6' if d else '#4a5568'
        self.ringtxt = '#F2E2A6' if d else '#14264A'
        self.ribbon = 'url(#ribbon)' if d else 'url(#ribbonL)'
        self.logo = '../assets/img/logo-light.png' if d else '../assets/img/logo.png'
        self.line_op = .17 if d else .5


def frame(t, x0=9, y0=9, x1=201, y1=288, r=7, inner=3.2, w=0.55, dots=True):
    stroke = t.gold

    def path(a, b, c, d, rr):
        return (f'M{a+rr},{b} H{c-rr} A{rr},{rr} 0 0 0 {c},{b+rr} V{d-rr} A{rr},{rr} 0 0 0 {c-rr},{d} '
                f'H{a+rr} A{rr},{rr} 0 0 0 {a},{d-rr} V{b+rr} A{rr},{rr} 0 0 0 {a+rr},{b} Z')
    s = f'<path d="{path(x0, y0, x1, y1, r)}" fill="none" stroke="{stroke}" stroke-width="{w}"/>'
    s += f'<path d="{path(x0 + inner, y0 + inner, x1 - inner, y1 - inner, r - 1.2)}" fill="none" stroke="{stroke}" stroke-width="{w * .45}"/>'
    if dots:
        for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            s += f'<circle cx="{cx}" cy="{cy}" r="1.5" fill="{stroke}"/><circle cx="{cx}" cy="{cy}" r="3" fill="none" stroke="{stroke}" stroke-width=".3"/>'
        for (cx, cy) in (((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)):
            s += f'<path d="M{cx-3},{cy} L{cx},{cy-3} L{cx+3},{cy} L{cx},{cy+3} Z" fill="{stroke}"/>'
    return s


def rule_with_diamond(t, cx, y, half, gap=5, sw=.35, d=1.7):
    st = t.goldh
    return (f'<line x1="{cx-half}" y1="{y}" x2="{cx-gap}" y2="{y}" stroke="{st}" stroke-width="{sw}"/>'
            f'<line x1="{cx+gap}" y1="{y}" x2="{cx+half}" y2="{y}" stroke="{st}" stroke-width="{sw}"/>'
            f'<path d="M{cx-d},{y} L{cx},{y-d} L{cx+d},{y} L{cx},{y+d} Z" fill="{st}"/>'
            f'<circle cx="{cx-gap-1.6}" cy="{y}" r=".55" fill="{st}"/><circle cx="{cx+gap+1.6}" cy="{y}" r=".55" fill="{st}"/>')


def ribbon(t, x, w=12, y0=-2, y1=150, notch=9):
    xl, xr = x - w / 2, x + w / 2
    return f'''
<path d="M{xl},{y0} L{xr},{y0} L{xr},{y1} L{x},{y1-notch} L{xl},{y1} Z" fill="{t.ribbon}"/>
<path d="M{xl+1.3},{y0} L{xl+1.3},{y1-1.2} M{xr-1.3},{y0} L{xr-1.3},{y1-1.2}" stroke="#7A5A1F" stroke-width=".25" opacity=".7"/>
<path d="M{xl+2.4},{y0} L{xl+2.4},{y1-2.6} M{xr-2.4},{y0} L{xr-2.4},{y1-2.6}" stroke="#fff6d6" stroke-width=".18" stroke-dasharray=".9 .9" opacity=".75"/>
<path d="M{xl},{y0} L{xl},{y1} M{xr},{y0} L{xr},{y1}" stroke="#5A4010" stroke-width=".2" opacity=".5"/>'''


def medallion(t, cx, cy, R=46, ring=SIMAN_RING, center_char='ס', center_size=62, ticks=True, ring_letters=True, glow=True):
    gold = t.gold
    parts = []
    if t.dark and glow:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{R+7}" fill="url(#glow)"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{R+4.2}" fill="url(#shadow)"/>')
    if ticks:
        rt0 = R + 3.2
        for i in range(120):
            a = math.radians(i * 3)
            ln = 2.0 if i % 5 == 0 else 1.0
            x0, y0 = cx + rt0 * math.cos(a), cy - rt0 * math.sin(a)
            x1, y1 = cx + (rt0 + ln) * math.cos(a), cy - (rt0 + ln) * math.sin(a)
            parts.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{gold}" stroke-width="{.34 if i % 5 == 0 else .2}"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{t.disc}" stroke="{gold}" stroke-width="1.3"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{R-2.1}" fill="none" stroke="{gold}" stroke-width=".3"/>')
    r_in = R - 12.6
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_in}" fill="none" stroke="{gold}" stroke-width=".6"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r_in-1.8}" fill="none" stroke="{gold}" stroke-width=".25"/>')
    if ring_letters:
        n = len(ring)
        half = n // 2
        rt = R - 8.2
        step = 180 / half
        for i, s in enumerate(ring):
            top = i < half
            k = i if top else i - half
            a_deg = step / 2 + k * step if top else 360 - step / 2 - k * step
            a = math.radians(a_deg)
            if top:
                r_base = rt - 1.6
                rot = 90 - a_deg
            else:
                r_base = rt + 1.6
                rot = 270 - a_deg
            x, y = cx + r_base * math.cos(a), cy - r_base * math.sin(a)
            parts.append(f'<text transform="translate({x:.2f} {y:.2f}) rotate({rot:.2f})" text-anchor="middle" font-family="Suez" font-size="4.6" fill="{t.ringtxt}" style="direction:rtl">{s}</text>')
        for k in range(half + 1):
            for base in (0, 180):
                a = math.radians(base + k * step)
                x, y = cx + rt * math.cos(a), cy - rt * math.sin(a)
                parts.append(f'<path d="M{x-.75:.2f},{y:.2f} L{x:.2f},{y-.75:.2f} L{x+.75:.2f},{y:.2f} L{x:.2f},{y+.75:.2f} Z" fill="{gold}"/>')
    ty = cy + center_size * 0.255
    if t.dark:
        parts.append(f'<text x="{cx}" y="{ty:.2f}" text-anchor="middle" font-family="Suez" font-size="{center_size}" fill="#000" opacity=".35" transform="translate(.5 .7)" style="direction:rtl">{center_char}</text>')
    parts.append(f'<text x="{cx}" y="{ty:.2f}" text-anchor="middle" font-family="Suez" font-size="{center_size}" fill="{t.goldv}" style="direction:rtl">{center_char}</text>')
    return '\n'.join(parts)


def small_seal(t, cx, cy, R, char, size):
    """compact version of the medallion (ticks + one letter) for credits / dividers"""
    gold = t.gold
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{t.disc}" stroke="{gold}" stroke-width="{max(.5, R*.04):.2f}"/>',
             f'<circle cx="{cx}" cy="{cy}" r="{R*.89:.2f}" fill="none" stroke="{gold}" stroke-width=".25"/>']
    for i in range(60):
        a = math.radians(i * 6)
        ln = R * (.09 if i % 5 == 0 else .05)
        r0 = R * .74
        parts.append(f'<line x1="{cx + r0*math.cos(a):.2f}" y1="{cy - r0*math.sin(a):.2f}" x2="{cx + (r0+ln)*math.cos(a):.2f}" y2="{cy - (r0+ln)*math.sin(a):.2f}" stroke="{gold}" stroke-width="{.25 if i % 5 == 0 else .15}"/>')
    parts.append(f'<text x="{cx}" y="{cy + size*.255:.2f}" text-anchor="middle" font-family="Suez" font-size="{size}" fill="{t.goldv}" style="direction:rtl">{char}</text>')
    return ''.join(parts)


# --------------------------------------------------------------------------------------------
def cover(theme='dark'):
    t = T(theme)
    cx = 105
    b = [defs()]
    if t.dark:
        b.append('<rect width="210" height="297" fill="url(#bgd)"/>')
    else:
        b.append('<rect width="210" height="297" fill="#fff"/>')
    lines = ''.join(f'<line x1="14" y1="{y}" x2="196" y2="{y}" stroke="{"#D9B75F" if t.dark else "#C9A24B"}" stroke-opacity="{t.line_op * (1 if t.dark else .55)}" stroke-width=".18"/>' for y in range(152, 284, 7))
    b.append(f'<g mask="url(#fadeMask)">{lines}</g>')
    if t.dark:
        b.append('<rect width="210" height="297" fill="url(#grainP)" opacity=".55"/>')
    b.append(frame(t))
    b.append(f'<text x="178" y="26" text-anchor="end" font-family="Frank" font-weight="500" font-size="4.4" fill="{t.text}" opacity=".8">בס״ד</text>')
    b.append(medallion(t, cx, 93, 46))
    b.append(ribbon(t, 166, 12, -2, 146))
    b.append(f'<text x="{cx}" y="170" text-anchor="middle" font-family="Suez" font-size="14" letter-spacing="2.4" fill="{t.goldh}">מבחני</text>')
    if t.dark:
        b.append(f'<text x="{cx+.45}" y="206.6" text-anchor="middle" font-family="Suez" font-size="40" fill="#000" opacity=".38">הסימנים</text>')
        b.append(f'<text x="{cx}" y="206" text-anchor="middle" font-family="Suez" font-size="40" fill="{t.gold}">הסימנים</text>')
    else:
        b.append(f'<text x="{cx}" y="206" text-anchor="middle" font-family="Suez" font-size="40" fill="url(#navyv)">הסימנים</text>')
    b.append(rule_with_diamond(t, cx, 216, 47))
    b.append(f'<text x="{cx}" y="227" text-anchor="middle" font-family="Frank" font-weight="500" font-size="5.5" fill="{t.text}">מבחנים ודפי חבורה בהלכות ברכות, קריאת שמע ותפילה</text>')
    b.append(f'<text x="{cx}" y="235" text-anchor="middle" font-family="Heebo" font-weight="600" font-size="3.3" letter-spacing=".9" fill="{t.goldh}">אורח חיים  ·  סימנים ד – קח</text>')
    b.append(f'<image href="{t.logo}" x="{cx-17}" y="245" width="34" height="31.9"/>')
    return svg_page('\n'.join(b))


CREDITS_CSS = '''
.cr{position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;text-align:center;color:#14264a}
.cr .t1{font-family:'Suez',serif;font-size:21pt;line-height:1;color:#14264a}
.cr .sub{font-family:'Frank',serif;font-weight:500;font-size:10.5pt;color:#4a5568;margin-top:1.6mm}
.cr .body{font-family:'Frank',serif;font-weight:500;font-size:11.6pt;line-height:1.5;color:#14264a}
.cr .body b{font-weight:900}
.cr .small{font-family:'Heebo',sans-serif;font-weight:600;font-size:9pt;color:#a8802f;letter-spacing:.04em}
.cr .num{font-family:'Heebo',sans-serif;font-weight:800;font-size:13.5pt;direction:ltr;unicode-bidi:isolate;letter-spacing:.04em;color:#14264a}
.cr .mail{font-family:'Heebo',sans-serif;font-weight:600;font-size:10.4pt;direction:ltr;unicode-bidi:isolate;color:#14264a}
.cr .q{font-family:'Suez',serif;font-size:14.5pt;color:#14264a;line-height:1.2}
.cr .gap{flex:0 0 auto}
.cr svg.sep{width:56mm;height:4mm;display:block}
'''


def sep_svg():
    return ('<svg class="sep" viewBox="0 0 56 4" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="#8C6A27"/><stop offset=".5" stop-color="#C9A24B"/><stop offset="1" stop-color="#8C6A27"/></linearGradient></defs>'
            '<line x1="0" y1="2" x2="22" y2="2" stroke="url(#sg)" stroke-width=".3"/><line x1="34" y1="2" x2="56" y2="2" stroke="url(#sg)" stroke-width=".3"/>'
            '<path d="M28,.2 L29.8,2 L28,3.8 L26.2,2 Z" fill="#A8802F"/><circle cx="24.4" cy="2" r=".5" fill="#A8802F"/><circle cx="31.6" cy="2" r=".5" fill="#A8802F"/></svg>')


def credits():
    t = T('light')
    bg = defs() + '<rect width="210" height="297" fill="#fff"/>' + frame(t)
    bg += f'<text x="178" y="26" text-anchor="end" font-family="Frank" font-weight="500" font-size="4.4" fill="{t.text}" opacity=".8">בס״ד</text>'
    bg += small_seal(t, 105, 52, 18.5, 'ס', 25)
    sep = sep_svg()
    html = f'''
<div class="pg"><svg viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg">{bg}</svg>
<div class="cr">
  <div class="gap" style="height:78mm"></div>
  <div class="t1">מבחני הסימנים</div>
  <div class="sub">קובץ מבחנים בהלכות ברכות, קריאת שמע ותפילה</div>
  <div class="gap" style="height:6mm"></div>{sep}<div class="gap" style="height:5.4mm"></div>
  <div class="body">החומר נערך ונלקט<br>ע״י ארגון <b>׳ברומו של עולם׳</b><br>לחיזוק רוממות התפילה</div>
  <div class="gap" style="height:3mm"></div>
  <div class="mail">b613515@gmail.com</div><div class="mail" style="margin-top:.4mm">052-7616296</div>
  <div class="gap" style="height:5mm"></div>{sep}<div class="gap" style="height:4.4mm"></div>
  <div class="body">קו בית הוראה לשאלות<br>בהלכות תפילה וברכות:</div>
  <div class="num" style="margin-top:1mm">0772150094</div>
  <div class="gap" style="height:4.6mm"></div>{sep}<div class="gap" style="height:4.2mm"></div>
  <div class="body">לשמיעת השיעורים והשיחות:</div>
  <div class="num" style="margin-top:1mm">0733718376</div>
  <div class="gap" style="height:4.6mm"></div>{sep}<div class="gap" style="height:3.6mm"></div>
  <div class="small">לתרומות</div>
  <img src="../assets/img/nedarim.png" style="width:15.5mm;margin-top:1.4mm"><div class="body" style="font-size:10.4pt;margin-top:1mm">בלשונית - ׳ברומו של עולם׳</div>
  <div class="gap" style="height:5mm"></div>{sep}<div class="gap" style="height:3.4mm"></div>
  <div class="q">״שגיאות מי יבין״</div>
  <div class="body" style="font-size:10.8pt;margin-top:.6mm">כל הערה או הארה תתקבל בברכה</div>
  <div style="flex:1"></div>
  <img src="../assets/img/logo.png" style="width:25mm;margin-bottom:19mm">
</div></div>'''
    return html


def divider(part, units, pages=None, compact=False):
    """part divider page (light)"""
    t = T('light')
    bg = defs() + '<rect width="210" height="297" fill="#fff"/>' + frame(t)
    bg += f'<text x="178" y="26" text-anchor="end" font-family="Frank" font-weight="500" font-size="4.4" fill="{t.text}" opacity=".8">בס״ד</text>'
    if compact:
        bg += medallion(t, 105, 74, 33, ring=SIMAN_RING, center_char=part['letter'], center_size=42, ring_letters=False)
    else:
        bg += medallion(t, 105, 98, 46, ring=SIMAN_RING, center_char=part['letter'], center_size=58)
    return bg


DIV_CSS = '''
.dv{position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;text-align:center}
.dv>*{flex-shrink:0}
.dv .pk{font-family:'Heebo',sans-serif;font-weight:800;font-size:10pt;letter-spacing:.5em;color:#a8802f;margin-bottom:2.6mm;padding-right:.5em}
.dv .pt{font-family:'Suez',serif;font-size:29pt;line-height:1.1;color:#14264a;max-width:150mm}
.dv .ps{font-family:'Frank',serif;font-weight:500;font-size:13pt;color:#5d6471;margin-top:2mm}
.dv .list{width:132mm;margin-top:5mm}
.dv .list.two{width:166mm;display:grid;grid-template-columns:1fr 1fr;column-gap:9mm;margin-top:3mm}
.dv .li{display:flex;align-items:baseline;gap:2mm;font-family:'Frank',serif;font-weight:500;font-size:11pt;line-height:1.35;margin:0 0 1.7mm;color:#16181d;text-align:right}
.dv .list.two .li{font-size:9.6pt;margin:0 0 1.5mm}
.dv .li .k{font-family:'Heebo',sans-serif;font-weight:600;font-size:7.8pt;letter-spacing:.06em;color:#a8802f;flex:0 0 auto}
.dv .list.two .li .k{font-size:6.6pt}
.dv .li .d{flex:1;border-bottom:.3mm dotted #b9ad8c;transform:translateY(-1mm);min-width:4mm}
.dv .li .n{font-family:'Suez',serif;font-size:11pt;color:#14264a;flex:0 0 auto}
.dv .li .tt{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;max-width:48mm}
'''


def divider_page(part, units, pn):
    """full page; units = list of dict(kicker,title,sub,page)"""
    compact = len(units) > 9
    bg = divider(part, units, compact=compact)
    rows = ''.join(f'<div class="li"><span class="tt">{u["title"]}{(" – " + u["sub"]) if u.get("sub") and len(u["sub"]) < 24 else ""}</span><span class="k">{u["kicker"]}</span><span class="d"></span><span class="n">{u["page"]}</span></div>' for u in units)
    top = 118 if compact else 157
    cls = 'list two' if compact else 'list'
    return f'''<div class="pg"><svg viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg">{bg}</svg>
<div class="dv"><div style="height:{top}mm"></div>
<div class="pk"><span style="font-size:2.4px;color:#fff;letter-spacing:0;direction:ltr;unicode-bidi:isolate;font-family:Arial">__MARK__</span>חלק {part["letter"]}׳</div>
<div class="pt">{part["name"]}</div><div class="ps">{part["sub"]}</div>
<div style="margin-top:5mm">{sep_svg()}</div>
<div class="{cls}">{rows}</div></div></div>'''


def back_cover():
    t = T('dark')
    b = [defs(), '<rect width="210" height="297" fill="url(#bgd)"/>',
         '<rect width="210" height="297" fill="url(#grainP)" opacity=".55"/>']
    lines = ''.join(f'<line x1="14" y1="{y}" x2="196" y2="{y}" stroke="#D9B75F" stroke-opacity=".10" stroke-width=".18"/>' for y in range(40, 284, 7))
    b.append(f'<g>{lines}</g>')
    b.append(frame(t))
    b.append(medallion(t, 105, 120, 30, center_size=40, ring_letters=False))
    b.append(rule_with_diamond(t, 105, 172, 40))
    b.append(f'<image href="{t.logo}" x="{105-21}" y="181" width="42" height="39.4"/>')
    return svg_page('\n'.join(b))


# --------------------------------------------------------------------------------------------
TOC_CSS = '''
@page { size:210mm 297mm; margin:25mm 21mm 22mm 21mm }
html{background:#fff}
body{margin:0;padding:0;background:transparent;direction:rtl;font-family:'Frank',serif;font-weight:500;color:#16181d}
.frame{position:fixed;left:-21mm;top:-25mm;width:210mm;height:297mm;z-index:-1}
.tt{text-align:center;margin:0 0 1mm}
.tt .a{font-family:'Suez',serif;font-size:27pt;color:#14264a;line-height:1.1}
.tt .b{font-family:'Heebo',sans-serif;font-weight:600;font-size:8.8pt;letter-spacing:.2em;color:#a8802f;margin-top:1.2mm}
.ph{display:flex;align-items:center;gap:3.4mm;margin:6.4mm 0 2.4mm;break-after:avoid}
.ph .sl{flex:0 0 11mm;width:11mm;height:11mm}
.ph .sl svg{width:11mm;height:11mm;display:block}
.ph .pn{font-family:'Suez',serif;font-size:14.5pt;color:#14264a;line-height:1.1}
.ph .pr{font-family:'Frank',serif;font-size:10pt;color:#5d6471;margin-top:.4mm}
.ph .ln{flex:1;border-top:.3mm solid #c9a24b;margin-top:2mm}
.row{display:flex;align-items:baseline;gap:2.2mm;margin:0 0 1.45mm;font-size:10.6pt;line-height:1.3;break-inside:avoid}
.row .k{flex:0 0 27mm;font-family:'Heebo',sans-serif;font-weight:600;font-size:7.4pt;letter-spacing:.05em;color:#a8802f}
.row .t{flex:0 1 auto}
.row .t i{font-style:normal;color:#5d6471;font-size:9.4pt}
.row .d{flex:1;border-bottom:.3mm dotted #b9ad8c;transform:translateY(-1mm);min-width:6mm}
.row .n{font-family:'Suez',serif;font-size:10.6pt;color:#14264a;min-width:9mm;text-align:left}
.row .sc{flex:0 0 11mm;height:5.2mm;border:.25mm solid #b9ad8c;border-radius:1.4mm;align-self:center}
.row .sc.no{border:0}
.legend{margin-top:5mm;text-align:center;font-family:'Heebo',sans-serif;font-weight:600;font-size:7.6pt;color:#8b91a0;letter-spacing:.06em}
'''


def toc_html(parts, units, pages, hnum):
    t = T('light')
    out = ['<div class="tt"><div class="a">תוכן העניינים</div><div class="b">ויומן ציונים</div></div>']
    for p in parts:
        us = [u for u in units if u['part'] == p['id']]
        if not us:
            continue
        seal = (f'<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">{defs()}{small_seal(t, 10, 10, 9.4, p["letter"], 10)}</svg>')
        out.append(f'<div class="ph"><div class="sl">{seal}</div><div><div class="pn">{p["name"]}</div><div class="pr">{p["sub"]}</div></div><div class="ln"></div></div>')
        for u in us:
            subtxt = (u.get('sub') or '')
            if u['kind'] == 'chavura':
                subtxt = subtxt.split(' ·')[0]
            sub = f' <i>· {subtxt}</i>' if subtxt and len(subtxt) < 46 else ''
            kick = {'חבורה בהלכות קריאת שמע': 'חבורה', 'חבורה בהלכות תפילה': 'חבורה', 'דף שאלות ותשובות': 'שאלות ותשובות'}.get(u['kicker'], u['kicker'])
            sc = '<span class="sc"></span>' if u['kind'] in ('exam', 'chavura') else '<span class="sc no"></span>'
            out.append(f'<div class="row"><span class="k">{kick}</span><span class="t">{u["title"]}{sub}</span><span class="d"></span><span class="n">{hnum(pages[u["id"]])}</span>{sc}</div>')
    out.append('<div class="legend">הריבוע שבקצה כל מבחן – למילוי הציון</div>')
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>תוכן העניינים</title><style>{font_face_css("../assets/fonts")}{TOC_CSS}</style></head><body>{"".join(out)}</body></html>')


def frame_page():
    """transparent page with only the frame (merged under the contents pages)"""
    t = T('light')
    return svg_page(defs() + frame(t))
