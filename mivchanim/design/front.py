"""Cover, inner title page, credits page, part dividers, table of contents, back cover.

Style: dark blue marbled ground, cream marble parchment, a tall blue panel with a beveled gold rim and embossed
gold scrollwork (the artwork is built by gen_art.py); every letter is live text on top of the artwork.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa: E402,F403

PAGE_CSS = f'''
{font_face_css('../assets/fonts')}
@page {{ size: 210mm 297mm; margin: 0 }}
html,body {{ margin:0; padding:0; background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
.pg {{ width:210mm; height:297mm; position:relative; overflow:hidden; break-after:page; page-break-after:always; }}
.pg:last-child {{ break-after:auto; page-break-after:auto; }}
.pg > svg {{ position:absolute; left:0; top:0; width:210mm; height:297mm; display:block; }}
.pg > img.bg {{ position:absolute; left:0; top:0; width:210mm; height:297mm; display:block; }}
svg text {{ font-family:'Frank','David',serif; direction:rtl; }}
'''

NAVY_T = '#1c2e52'
CREAM = '#F6EBC8'
GOLD_T = '#E4C97F'
BROWN = '#8a6420'


def doc(pages, title, extra_css=''):
    body = ''.join(pages)
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{PAGE_CSS}{extra_css}</style></head><body>{body}</body></html>')


def svg_defs():
    return f'''<defs>
  <linearGradient id="cream" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF8E1"/><stop offset=".55" stop-color="{CREAM}"/><stop offset="1" stop-color="#DCC58C"/></linearGradient>
  <linearGradient id="navyg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A4A86"/><stop offset=".5" stop-color="#14264a"/><stop offset="1" stop-color="#0B1630"/></linearGradient>
  <linearGradient id="goldt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8C6A27"/><stop offset=".4" stop-color="#C9A24B"/><stop offset=".6" stop-color="#E9D08A"/><stop offset="1" stop-color="#8C6A27"/></linearGradient>
</defs>'''


def t_cream(x, y, txt, size, family='Suez', weight=400, ls=0, anchor='middle', shadow=True, extra=''):
    """cream letters with a soft dark shadow (title on the blue panel); the shadow is stacked copies, no SVG filter"""
    base = f'text-anchor="{anchor}" font-family="{family}" font-weight="{weight}" font-size="{size}" letter-spacing="{ls}" {extra}'
    out = ''
    if shadow:
        for dx, dy, op in ((1.5, 2.0, .10), (1.0, 1.4, .16), (.6, .85, .26), (.3, .45, .38)):
            out += f'<text x="{x + dx}" y="{y + dy}" {base} fill="#050e1a" opacity="{op}">{txt}</text>'
    out += f'<text x="{x}" y="{y}" {base} fill="#FBF3D8">{txt}</text>'
    return out


def t_brown(x, y, txt, size, family='Frank', weight=500, ls=0, anchor='middle', fill='#4a3318', extra=''):
    base = f'text-anchor="{anchor}" font-family="{family}" font-weight="{weight}" font-size="{size}" letter-spacing="{ls}" {extra}'
    return (f'<text x="{x + .2}" y="{y + .3}" {base} fill="#fff" opacity=".45">{txt}</text>'
            f'<text x="{x}" y="{y}" {base} fill="{fill}">{txt}</text>')


def t_navy(x, y, txt, size, family='Suez', weight=400, ls=0, anchor='middle', fill='url(#navyg)', extra=''):
    base = f'text-anchor="{anchor}" font-family="{family}" font-weight="{weight}" font-size="{size}" letter-spacing="{ls}" {extra}'
    return (f'<text x="{x + .25}" y="{y + .4}" {base} fill="#fff" opacity=".55">{txt}</text>'
            f'<text x="{x}" y="{y}" {base} fill="{fill}">{txt}</text>')


def img(href, cx, y, w, h=None):
    h_attr = f' height="{h}"' if h else ''
    return f'<image href="{href}" x="{cx - w / 2}" y="{y}" width="{w}"{h_attr}/>'


def page(bg, inner, cls='pg'):
    return (f'<div class="{cls}"><img class="bg" src="art/{bg}"/>'
            f'<svg viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg">{svg_defs()}{inner}</svg></div>')


# --------------------------------------------------------------------------------------------
def cover():
    cx = 105
    b = []
    b.append(t_cream(cx, 66, 'ארגון ׳ברומו של עולם׳', 6.2, 'Frank', 500, 1.4, shadow=True))
    b.append(t_cream(cx, 101, 'מבחני', 25, 'Suez'))
    b.append(t_cream(cx, 131, 'הסימנים', 31, 'Suez'))
    # parchment
    b.append(t_brown(cx, 224, 'מבחנים ודפי חבורה', 6.6, 'Frank', 500))
    b.append(t_brown(cx, 233.5, 'בהלכות ברכות, קריאת שמע ותפילה', 8, 'Frank', 900))
    b.append(t_brown(cx, 242.5, 'אורח חיים  ·  סימנים ד – קח', 5.4, 'Frank', 500, .3))
    b.append(f'<image href="../assets/img/logo.png" x="{cx - 12}" y="252" width="24" height="22.5"/>')
    return page('ref-cover-bg.jpg', ''.join(b))


def inner_title():
    cx = 105
    b = []
    b.append(t_brown(cx, 34, 'בס״ד', 5, 'Frank', 500))
    b.append(t_navy(cx, 104, 'מבחני', 24, 'Suez', fill=NAVY_T))
    b.append(t_navy(cx, 138, 'הסימנים', 36, 'Suez', fill=NAVY_T))
    b.append(img('art/rule.png', cx, 146, 120))
    b.append(t_brown(cx, 192, 'מבחנים ודפי חבורה בהלכות ברכות,', 7.2, 'Frank', 500))
    b.append(t_brown(cx, 201.5, 'קריאת שמע ותפילה', 7.2, 'Frank', 500))
    b.append(t_brown(cx, 213, 'אורח חיים  ·  סימנים ד – קח', 4.6, 'Frank', 500, .5, fill=BROWN))
    b.append(f'<image href="../assets/img/logo.png" x="{cx - 12.5}" y="233" width="25" height="23.5"/>')
    b.append(t_navy(cx, 268.5, 'ברומו של עולם', 6.4, 'Suez', fill=NAVY_T))
    return page('ref-frame.jpg', ''.join(b))


CREDITS_CSS = '''
.cr{position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;text-align:center;color:#2b2218}
.cr .t1{font-family:'Suez',serif;font-size:22pt;line-height:1;color:#1c2e52;text-shadow:.25mm .35mm 0 rgba(255,255,255,.6)}
.cr .sub{font-family:'Frank',serif;font-weight:500;font-size:10.5pt;color:#5c4a30;margin-top:1.6mm}
.cr .body{font-family:'Frank',serif;font-weight:500;font-size:11.6pt;line-height:1.5;color:#2b2218}
.cr .body b{font-weight:900;color:#1c2e52}
.cr .small{font-family:'Heebo',sans-serif;font-weight:600;font-size:9pt;color:#8a6420;letter-spacing:.04em}
.cr .num{font-family:'Heebo',sans-serif;font-weight:800;font-size:13.5pt;direction:ltr;unicode-bidi:isolate;letter-spacing:.04em;color:#1c2e52}
.cr .mail{font-family:'Heebo',sans-serif;font-weight:600;font-size:10.4pt;direction:ltr;unicode-bidi:isolate;color:#2b2218}
.cr .q{font-family:'Suez',serif;font-size:14.5pt;color:#1c2e52;line-height:1.2}
.cr .gap{flex:0 0 auto}
.cr img.sep{width:46mm;height:5.8mm;display:block;margin:-.8mm 0}
'''


def sep():
    return '<img class="sep" src="art/sep.png">'


def credits():
    html = f'''
<div class="pg"><img class="bg" src="art/ref-frame.jpg"/>
<div class="ringseal" style="left:{105 - 17}mm;top:22mm"><img src="art/ring.png"><span>ס</span></div>
<div class="cr">
  <div class="gap" style="height:68mm"></div>
  <div class="t1">מבחני הסימנים</div>
  <div class="sub">קובץ מבחנים בהלכות ברכות, קריאת שמע ותפילה</div>
  <div class="gap" style="height:5mm"></div>{sep()}<div class="gap" style="height:4.2mm"></div>
  <div class="body">החומר נערך ונלקט<br>ע״י ארגון <b>׳ברומו של עולם׳</b><br>לחיזוק רוממות התפילה</div>
  <div class="gap" style="height:3mm"></div>
  <div class="mail">b613515@gmail.com</div><div class="mail" style="margin-top:.4mm">052-7616296</div>
  <div class="gap" style="height:3.6mm"></div>{sep()}<div class="gap" style="height:3.4mm"></div>
  <div class="body">קו בית הוראה לשאלות<br>בהלכות תפילה וברכות:</div>
  <div class="num" style="margin-top:1mm">0772150094</div>
  <div class="gap" style="height:3.4mm"></div>{sep()}<div class="gap" style="height:3mm"></div>
  <div class="body">לשמיעת השיעורים והשיחות:</div>
  <div class="num" style="margin-top:1mm">0733718376</div>
  <div class="gap" style="height:3.4mm"></div>{sep()}<div class="gap" style="height:2.6mm"></div>
  <div class="small">לתרומות</div>
  <img src="../assets/img/nedarim.png" style="width:15.5mm;margin-top:1.4mm"><div class="body" style="font-size:10.4pt;margin-top:1mm">בלשונית - ׳ברומו של עולם׳</div>
  <div class="gap" style="height:3.6mm"></div>{sep()}<div class="gap" style="height:2.4mm"></div>
  <div class="q">״שגיאות מי יבין״</div>
  <div class="body" style="font-size:10.8pt;margin-top:.6mm">כל הערה או הארה תתקבל בברכה</div>
  <div style="flex:1"></div>
  <img src="../assets/img/logo.png" style="width:21mm;margin-bottom:21mm">
</div></div>'''
    return html


# --------------------------------------------------------------------------------------------
RING_CSS = '''
.ringseal{position:absolute;width:34mm;height:34mm}
.ringseal img{position:absolute;inset:0;width:34mm;height:34mm}
.ringseal span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Suez',serif;font-size:32pt;line-height:1;color:#FBF3D8;
  text-shadow:.3mm .45mm 0 rgba(4,16,31,.6);padding-bottom:1mm}
'''

DIV_CSS = RING_CSS + '''
.dv{position:absolute;left:0;right:0;top:0;bottom:0}
.dv>*{flex-shrink:0}
.dv .ringseal{left:calc(105mm - 17mm);top:28mm;width:34mm;height:34mm}
.dv .ringseal img{width:34mm;height:34mm}
.dv .ringseal span{font-size:32pt}
.dv .ptx{position:absolute;left:58mm;width:94mm;top:70mm;text-align:center;color:#FBF3D8}
.dv .pk{font-family:'Heebo',sans-serif;font-weight:800;font-size:10pt;letter-spacing:.42em;color:#E9D8A0;padding-right:.42em;text-shadow:.2mm .3mm 0 rgba(4,16,31,.6)}
.dv .pt{font-family:'Suez',serif;font-size:30pt;line-height:1.1;margin-top:3mm;color:#FBF3D8;text-shadow:.3mm .45mm .4mm rgba(4,16,31,.55)}
.dv .pt.long{font-size:26pt}
.dv .ps{font-family:'Frank',serif;font-weight:500;font-size:13pt;margin-top:3mm;color:#E8DDB8;text-shadow:.2mm .3mm .3mm rgba(4,16,31,.6)}
.dv .list{position:absolute;left:40mm;right:40mm;top:196mm}
.dv .list.two{left:33mm;right:33mm;display:grid;grid-template-columns:1fr 1fr;column-gap:9mm;top:192mm}
.dv .li{display:flex;align-items:baseline;gap:2mm;font-family:'Frank',serif;font-weight:500;font-size:12pt;line-height:1.35;margin:0 0 3.2mm;color:#2b2218;text-align:right}
.dv .list.two .li{font-size:9.4pt;margin:0 0 .8mm}
.dv .li .k{font-family:'Heebo',sans-serif;font-weight:600;font-size:7.8pt;letter-spacing:.06em;color:#8a6420;flex:0 0 auto}
.dv .list.two .li .k{font-size:6.4pt}
.dv .li .d{flex:1;border-bottom:.3mm dotted #a8956a;transform:translateY(-1mm);min-width:4mm}
.dv .li .n{font-family:'Suez',serif;font-size:12pt;color:#1c2e52;flex:0 0 auto}
.dv .list.two .li .n{font-size:10pt}
.dv .li .tt{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;max-width:70mm}
.dv .list.two .li .tt{max-width:46mm}
'''


def divider_page(part, units, pn):
    """full page; units = list of dict(kicker,title,sub,page)"""
    compact = len(units) > 9
    rows = ''.join(f'<div class="li"><span class="tt">{u["title"]}{(" – " + u["sub"]) if u.get("sub") and len(u["sub"]) < 24 else ""}</span><span class="k">{u["kicker"]}</span><span class="d"></span><span class="n">{u["page"]}</span></div>' for u in units)
    cls = 'list two' if compact else 'list'
    long_ = ' long' if len(part['name']) > 22 else ''
    return f'''<div class="pg"><img class="bg" src="art/ref-cover-bg.jpg"/>
<div class="dv">
  <div class="ringseal"><img src="art/ring.png"><span>{part["letter"]}</span></div>
  <div class="ptx"><span style="font-size:2.4px;color:#04101F;letter-spacing:0;direction:ltr;unicode-bidi:isolate;font-family:Arial">__MARK__</span>
    <div class="pk">חלק {part["letter"]}׳</div><div class="pt{long_}">{part["name"]}</div><div class="ps">{part["sub"]}</div></div>
  <div class="{cls}">{rows}</div>
</div></div>'''


def back_cover():
    cx = 105
    b = []
    b.append(f'<image href="../assets/img/logo-light.png" x="{cx - 21}" y="48" width="42" height="39.4"/>')
    b.append(t_cream(cx, 112, 'ברומו של עולם', 16, 'Suez'))
    b.append(t_cream(cx, 126, 'לחיזוק רוממות התפילה', 7, 'Frank', 500, .4, shadow=True))
    b.append(t_brown(cx, 226, 'מבחני הסימנים', 9, 'Suez', 400, fill='#1c2e52'))
    b.append(img('art/sep.png', cx, 230, 46))
    b.append(t_brown(cx, 246, 'b613515@gmail.com', 5.2, 'Heebo', 600, .3))
    b.append(t_brown(cx, 254, '052-7616296', 5.2, 'Heebo', 600, .6))
    return page('ref-cover-bg.jpg', ''.join(b))


# --------------------------------------------------------------------------------------------
TOC_CSS = '''
@page { size:210mm 297mm; margin:30mm 29mm 34mm 29mm }
html{background:transparent}
body{margin:0;padding:0;background:transparent;direction:rtl;font-family:'Frank',serif;font-weight:500;color:#2b2218}
.tt{text-align:center;margin:0 0 1mm}
.tt .a{font-family:'Suez',serif;font-size:27pt;color:#1c2e52;line-height:1.1;text-shadow:.25mm .35mm 0 rgba(255,255,255,.6)}
.tt .b{font-family:'Heebo',sans-serif;font-weight:600;font-size:8.8pt;letter-spacing:.2em;color:#8a6420;margin-top:1.2mm}
.tt img{width:44mm;height:5.6mm;display:block;margin:.6mm auto 0}
.ph{display:flex;align-items:center;gap:3.4mm;margin:6.4mm 0 2.4mm;break-after:avoid}
.ph .sl{flex:0 0 11mm;width:11mm;height:11mm;position:relative}
.ph .sl img{position:absolute;left:-.6mm;top:-.6mm;width:12.2mm;height:12.2mm}
.ph .sl span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Suez',serif;font-size:14pt;color:#FBF3D8;line-height:1;text-shadow:.15mm .25mm 0 rgba(4,16,31,.6);padding-bottom:.3mm}
.ph .pn{font-family:'Suez',serif;font-size:14.5pt;color:#1c2e52;line-height:1.1}
.ph .pr{font-family:'Frank',serif;font-size:10pt;color:#5c4a30;margin-top:.4mm}
.ph .ln{flex:1;height:1.1mm;margin-top:2mm;border-top:.35mm solid #b98f36;border-bottom:.12mm solid #d9bd78}
.row{display:flex;align-items:baseline;gap:2.2mm;margin:0 0 1.45mm;font-size:10.6pt;line-height:1.3;break-inside:avoid}
.row .k{flex:0 0 26mm;font-family:'Heebo',sans-serif;font-weight:600;font-size:7.4pt;letter-spacing:.05em;color:#8a6420}
.row .t{flex:0 1 auto}
.row .t i{font-style:normal;color:#5c4a30;font-size:9.4pt}
.row .d{flex:1;border-bottom:.3mm dotted #a8956a;transform:translateY(-1mm);min-width:6mm}
.row .n{font-family:'Suez',serif;font-size:10.6pt;color:#1c2e52;min-width:9mm;text-align:left}
.row .sc{flex:0 0 11mm;height:5.2mm;border:.3mm solid #a8802f;border-radius:1.4mm;align-self:center;background:rgba(255,255,255,.35)}
.row .sc.no{border:0;background:none}
.legend{margin-top:5mm;text-align:center;font-family:'Heebo',sans-serif;font-weight:600;font-size:7.6pt;color:#7a6a45;letter-spacing:.06em}
'''


def toc_html(parts, units, pages, hnum):
    out = ['<div class="tt"><div class="a">תוכן העניינים</div><div class="b">ויומן ציונים</div><img src="art/sep.png"></div>']
    for p in parts:
        us = [u for u in units if u['part'] == p['id']]
        if not us:
            continue
        seal = f'<img src="art/ring.png"><span>{p["letter"]}</span>'
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
    """page with only the frame (merged under the contents pages / used for notes and blanks)"""
    return '<div class="pg"><img class="bg" src="art/ref-frame.jpg"/></div>'
