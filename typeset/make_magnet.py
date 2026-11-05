#!/usr/bin/env python3
"""Magnet (portrait, A5 + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
Open, quiet typography: warm white paper, one thin gold line as frame, no ornaments; the table has only hairlines
(a slightly darker one where the month changes), the labels in gold, the Motzaei Shabbat shiur as a short centred line.
usage: python3 make_magnet.py [out_dir]   -> magnet-shiurim-print.pdf (with bleed), magnet-shiurim.pdf / .png (trimmed)
data: assets/magnet/zmanim-choref-5787.xlsx (the sheet that was sent by mail)"""
import os, sys, subprocess, html, openpyxl
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output', 'magnet'))
MAG = os.path.join(HERE, 'assets', 'magnet')
FIRST = 'חיי שרה'
RENAME = {'מקץ זאת - שבת חנוכה': 'מקץ - זאת חנוכה'}

COLS = ['פרשת השבוע', 'תאריך', 'שיעור<br>מכיתה ג׳', 'שיעור<br>מכיתה ז׳', 'הכנה<br>לשבת', 'שיעור<br>לישיבה קטנה', 'הרב טוטיאן<br>א׳', 'הרב טוטיאן<br>ב׳']
FOOT = [('לתרומות', '079-969-7788'),
        ('קו ׳בית הוראה׳ <small>לתפילה וברכות וזמני היום</small>', '077.215.00.94'),
        ('קו קול הלשון', '073.371.83.76')]

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
    tr, prev = [], None
    for r in data:
        month = r[1].split(' ', 1)[1].replace(' תשפ״ז', '')
        cls = ' class="m"' if prev and month != prev else ''
        prev = month
        tr.append(f'<tr{cls}><td class="p">{parasha(r[0])}</td><td class="d">{html.escape(r[1].replace(" תשפ״ז", ""))}</td>'
                  + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>')
    tr = ''.join(tr)
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div></div>' for a, n in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Bold.ttf");font-weight:700}}
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Medium.ttf");font-weight:500}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#211e1a;--gold:#a8823a;--grey:#6f675b;--hair:#e6dcc6}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:David,serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#fdfbf6}}
.fr{{position:absolute;inset:8.5mm;border:.3mm solid var(--gold)}}
.in{{position:absolute;left:15mm;right:15mm;top:14mm;bottom:13.5mm;display:flex;flex-direction:column}}
header{{position:relative;height:31mm}}
header img{{position:absolute;top:0}}
header img.oy{{right:-1mm;height:25mm}}
header img.bo{{left:0;height:19.5mm;top:2.5mm}}
.ttl{{text-align:center;padding-top:3.5mm}}
.ttl h1{{font-family:Keter;font-weight:700;font-size:27pt;line-height:1;color:var(--ink)}}
.ttl .yr{{margin-top:2.4mm;font-family:Frank;font-weight:600;font-size:12pt;color:var(--gold);letter-spacing:2.2pt}}
.ttl .sb{{margin-top:1.2mm;font-family:Frank;font-weight:400;font-size:7.4pt;color:var(--grey);letter-spacing:.3pt}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
col.c-p{{width:24%}} col.c-d{{width:16%}}
thead th{{font-family:Frank;font-weight:700;font-size:6.9pt;line-height:1.15;color:var(--gold);padding:0 .3mm 1.6mm;vertical-align:bottom;
  border-bottom:.45mm solid var(--ink)}}
thead th.p{{text-align:right;padding-right:.5mm}}
tbody td{{height:4.8mm;font-size:9.4pt;text-align:center;vertical-align:middle;border-bottom:.15mm solid var(--hair);white-space:nowrap}}
tbody tr.m td{{border-top:.35mm solid #c2a96f}}
tbody tr:last-child td{{border-bottom:.3mm solid var(--ink)}}
td.p{{text-align:right;padding-right:.5mm;font-family:Frank;font-weight:700;font-size:9.2pt}}
td.p .sp{{font-weight:500;font-size:6.9pt;color:var(--gold)}}
td.d{{font-family:Frank;font-weight:400;font-size:7.9pt;color:var(--grey)}}
td.t{{font-weight:700;font-variant-numeric:tabular-nums}}
.mot{{margin-top:5.5mm;text-align:center}}
.mot .k{{font-family:Frank;font-weight:600;font-size:7.6pt;color:var(--gold);letter-spacing:1.6pt}}
.mot .s{{margin-top:.6mm;font-family:Keter;font-weight:700;font-size:13pt}}
.mot .s b{{font-family:David;font-weight:700;font-size:13pt;margin-right:1.2mm}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;padding-top:2.4mm;border-top:.15mm solid #cdb98a}}
.c{{text-align:center;flex:1}}
.c + .c{{border-right:.15mm solid var(--hair)}}
.cl{{font-family:Frank;font-weight:600;font-size:7pt;color:var(--gold)}}
.cl small{{display:block;font-weight:400;font-size:6pt;color:var(--grey);margin-top:-.2mm}}
.cn{{font-family:David;font-weight:700;font-size:10.5pt;letter-spacing:.4pt;margin-top:.4mm}}
</style></head><body><div class="page"><div class="fr"></div>
<div class="in">
<header><img class="oy" src="file://{MAG}/ohel-yissachar.png"><img class="bo" src="file://{HERE}/assets/cover/logo.png">
<div class="ttl"><h1>זמני השיעורים</h1><div class="yr">חורף תשפ״ז</div><div class="sb">לשבתות קודש, מפרשת חיי שרה</div></div></header>
<table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr>{''.join(f'<th class="{"p" if i == 0 else ""}">{c}</th>' for i, c in enumerate(COLS))}</tr></thead><tbody>{tr}</tbody></table>
<div class="mot"><div class="k">במוצאי שבת קודש</div><div class="s">שיעור לכיתה ח׳ בשעה <b>20:15</b></div></div>
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
