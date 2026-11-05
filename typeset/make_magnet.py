#!/usr/bin/env python3
"""Magnet (portrait, A5 + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
Layout after the sketch that was sent: title on the right (Frank Ruhl Libre Black, the year in gold), the two logos on the left,
navy header row, light warm zebra rows, Motzaei Shabbat shiur on a sand band, the three phone lines below. Text in IBM Plex Sans Hebrew.
usage: python3 make_magnet.py [out_dir]   -> magnet-shiurim-print.pdf (with bleed), magnet-shiurim.pdf / .png (trimmed)
data: assets/magnet/zmanim-choref-5787.xlsx (the sheet that was sent by mail)"""
import os, sys, subprocess, html, openpyxl
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output', 'magnet'))
MAG = os.path.join(HERE, 'assets', 'magnet')
FIRST = 'חיי שרה'
RENAME = {'מקץ זאת - שבת חנוכה': 'מקץ - זאת חנוכה'}

COLS = ['פרשת השבוע', 'תאריך עברי', 'שיעור<br>מכיתה ג׳', 'שיעור<br>מכיתה ז׳', 'הכנה<br>לשבת', 'שיעור<br>לישיבה קטנה', 'הרב טוטיאן<br>א׳', 'הרב טוטיאן<br>ב׳']
FOOT = [('קו ׳בית הוראה׳', '077.215.00.94', 'לתפילה וברכות וזמני היום'),
        ('קו קול הלשון', '073.371.83.76', 'להאזנה לשיעורים'),
        ('לתרומות', '079-969-7788', '')]

def rows():
    ws = openpyxl.load_workbook(os.path.join(MAG, 'zmanim-choref-5787.xlsx')).worksheets[0]
    data, on = [], False
    for r in ws.iter_rows(min_row=4, values_only=True):
        if not r[0]:
            continue
        on = on or str(r[0]).strip() == FIRST
        if on:
            data.append([str(v).strip() if v is not None else '' for v in r[:8]])
    return data


def parasha(name):
    name = RENAME.get(name, name)
    if ' - ' in name:
        a, b = name.split(' - ', 1)
        return f'{html.escape(a)}<span class="sp"> · {html.escape(b)}</span>'
    return html.escape(name)


def build():
    data = rows()
    tr = ''.join(
        f'<tr><td class="p">{parasha(r[0])}</td><td class="d">{html.escape(r[1])}</td>'
        + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>' for r in data)
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div><div class="cs">{b}</div></div>' for a, n, b in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    plex = ''.join(f'@font-face{{font-family:Plex;src:url("file://{fonts}/IBMPlexSansHebrew-{n}.ttf");font-weight:{w}}}\n'
                   for n, w in [('Regular', 400), ('Medium', 500), ('SemiBold', 600), ('Bold', 700)])
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
{plex}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#141d2b;--navy:#17233a;--gold:#a07a33;--grey:#6c6a66;--sand:#f3ece0;--zeb:#f7f4ee;--hair:#e7e1d6}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:Plex,sans-serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#fff}}
.in{{position:absolute;left:12mm;right:12mm;top:9mm;bottom:10mm;display:flex;flex-direction:column}}
.bsd{{font-family:Frank;font-weight:500;font-size:7pt;color:var(--grey);text-align:right;height:4mm}}
header{{display:flex;align-items:center;justify-content:space-between;padding-bottom:4mm;border-bottom:.25mm solid #cfc7b8}}
.ttl h1{{font-family:Frank;font-weight:900;font-size:30pt;line-height:.95;letter-spacing:-.2pt;color:var(--ink)}}
.ttl .yr{{font-family:Frank;font-weight:500;font-size:21pt;line-height:1.1;color:var(--gold);margin-top:.6mm}}
.ttl .sb{{font-family:Plex;font-weight:500;font-size:8pt;color:var(--grey);margin-top:2mm}}
.logos{{display:flex;align-items:center;gap:4mm}}
.logos img.oy{{height:24mm}}
.logos i{{width:.2mm;height:17mm;background:#d6cfc2}}
.logos img.bo{{height:19mm}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:4.5mm}}
col.c-p{{width:21%}} col.c-d{{width:19%}}
thead th{{background:var(--navy);color:#fff;font-family:Plex;font-weight:600;font-size:6.9pt;line-height:1.15;padding:1.5mm .3mm;vertical-align:middle}}
thead th.p{{text-align:right;padding-right:2mm}}
tbody td{{height:4.95mm;font-size:9.3pt;text-align:center;vertical-align:middle;white-space:nowrap;border-bottom:.12mm solid var(--hair)}}
tbody tr:nth-child(even) td{{background:var(--zeb)}}
td.p{{text-align:right;padding-right:2mm;font-family:Frank;font-weight:700;font-size:9.6pt;line-height:1}}
td.p .sp{{font-family:Plex;font-weight:500;font-size:6.4pt;color:var(--gold);margin-right:1mm}}
td.d{{font-weight:400;font-size:7.8pt;color:var(--grey)}}
td.t{{font-weight:500;font-feature-settings:"tnum"}}
.mot{{margin-top:4mm;background:var(--sand);display:flex;align-items:center;padding:2.4mm 4mm}}
.mot .k{{font-weight:600;font-size:8.5pt;color:var(--gold);padding-left:3.5mm;margin-left:3.5mm;border-left:.25mm solid #cdbf9f}}
.mot .s{{font-family:Frank;font-weight:700;font-size:13pt;flex:1}}
.mot .tm{{font-family:Frank;font-weight:900;font-size:17pt;line-height:1}}
.foot{{margin-top:auto;padding-top:3mm;display:flex}}
.c{{flex:1;text-align:center;padding:.5mm 0}}
.c + .c{{border-right:.2mm solid #d6cfc2}}
.cl{{font-family:Frank;font-weight:700;font-size:8.6pt}}
.cn{{font-weight:600;font-size:12pt;letter-spacing:.3pt;margin-top:.3mm;font-feature-settings:"tnum"}}
.cs{{font-size:6.4pt;color:var(--grey);margin-top:.2mm;min-height:2.6mm}}
</style></head><body><div class="page"><div class="in">
<div class="bsd">בס״ד</div>
<header><div class="ttl"><h1>זמני השיעורים</h1><div class="yr">לחורף תשפ״ז</div><div class="sb">לשבתות קודש · מפרשת חיי שרה</div></div>
<div class="logos"><img class="oy" src="file://{MAG}/ohel-yissachar.png"><i></i><img class="bo" src="file://{HERE}/assets/cover/logo.png"></div></header>
<table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr>{''.join(f'<th class="{"p" if i == 0 else ""}">{c}</th>' for i, c in enumerate(COLS))}</tr></thead><tbody>{tr}</tbody></table>
<div class="mot"><div class="k">מוצאי שבת</div><div class="s">שיעור לכיתה ח׳</div><div class="tm">20:15</div></div>
<div class="foot">{foot}</div>
</div></div></body></html>'''
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(HERE, '_magnet.html')
    open(src, 'w', encoding='utf-8').write(page)
    js = f'''let c;try{{c=require('playwright').chromium}}catch(e){{c=require('/opt/node22/lib/node_modules/playwright').chromium}}
(async()=>{{const b=await c.launch();const p=await b.newPage({{viewport:{{width:582,height:816}},deviceScaleFactor:300/96}});
await p.goto('file://{src}');await p.evaluate(()=>document.fonts.ready);
console.log(await p.evaluate(()=>{{const t=document.querySelector('.in');return t.scrollHeight>t.clientHeight+1?'OVERFLOW '+t.scrollHeight+'>'+t.clientHeight:'fit, spare '+(t.clientHeight-[...t.children].reduce((s,e)=>s+e.offsetHeight,0))+'px'}}));
await p.pdf({{path:'{OUT}/magnet-shiurim-print.pdf',width:'{W}mm',height:'{H}mm',printBackground:true}});
await p.screenshot({{path:'{OUT}/_full.png'}});await b.close()}})()'''
    subprocess.run(['node', '-e', js], check=True)
    im = Image.open(f'{OUT}/_full.png').convert('RGB')
    px = im.width / W
    trim = im.crop((round(3 * px), round(3 * px), round((W - 3) * px), round((H - 3) * px)))
    trim.save(f'{OUT}/magnet-shiurim.png', dpi=(300, 300))
    trim.save(f'{OUT}/magnet-shiurim.pdf', resolution=300)
    os.remove(f'{OUT}/_full.png')
    print(len(data), 'shabbatot ->', OUT)


if __name__ == '__main__':
    build()
