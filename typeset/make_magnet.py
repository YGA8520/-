#!/usr/bin/env python3
"""Magnet (A5 portrait + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
Fonts: Karantina Bold (title, Motzaei Shabbat band), Suez One (year, parashot, months, labels), Rubik (times and small text).
The table has a month strip on the right (vertical month names), only the day in the date column, navy rules at the month changes.
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


def stack(word):
    """month name as upright letters one under the other (a geresh stays with its letter, a space is a small gap)"""
    out = []
    for ch in word:
        if ch in '׳\'':
            out[-1] += '׳'
        elif ch == ' ':
            out.append('<em></em>')
        else:
            out.append(html.escape(ch))
    return ''.join(x if x.startswith('<em') else x + '<br>' for x in out)


def build():
    data = rows()
    months = []                                   # [month, [rows]] in order
    for r in data:
        day, month = r[1].replace(' תשפ״ז', '').split(' ', 1)
        month = month[1:] if month.startswith('ב') else month
        if not months or months[-1][0] != month:
            months.append([month, []])
        months[-1][1].append((day, r))
    tr = []
    for mi, (month, rs) in enumerate(months):
        for i, (day, r) in enumerate(rs):
            cls = ['first'] if i == 0 and mi else []
            label = stack(month) if len(rs) > 1 else html.escape(month)
            m = (f'<td class="mo{" v" if len(rs) > 1 else ""}" rowspan="{len(rs)}"><span>{label}</span></td>' if i == 0 else '')
            tr.append(f'<tr class="{" ".join(cls)}">{m}<td class="p">{parasha(r[0])}</td><td class="d">{html.escape(day)}</td>'
                      + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>')
    tr = ''.join(tr)
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div><div class="cs">{b}</div></div>' for a, n, b in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Karantina;src:url("file://{fonts}/Karantina-Bold.ttf");font-weight:700}}
@font-face{{font-family:Suez;src:url("file://{fonts}/SuezOne-Regular.ttf")}}
@font-face{{font-family:Rubik;src:url("file://{fonts}/Rubik-VF.ttf");font-weight:300 900}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--navy:#16213a;--gold:#b08436;--gold2:#d9b467;--grey:#77736c;--sand:#f5efe4;--hair:#e9e2d4}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:Rubik,sans-serif;color:var(--navy);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#fff}}
.in{{position:absolute;left:11.5mm;right:11.5mm;top:9.5mm;bottom:10mm;display:flex;flex-direction:column}}
header{{position:relative;display:flex;align-items:flex-start;justify-content:space-between;height:37mm}}
.bsd{{position:absolute;right:0;top:0;font-family:Rubik;font-weight:500;font-size:6.5pt;color:var(--grey)}}
.ttl{{padding-top:4.2mm}}
.ttl h1{{font-family:Karantina;font-weight:700;font-size:60pt;line-height:.72;color:var(--navy);letter-spacing:.2pt}}
.ttl .yr{{display:flex;align-items:center;gap:2.2mm;margin-top:3mm}}
.ttl .yr b{{font-family:Suez;font-weight:400;font-size:16pt;line-height:1;color:var(--gold)}}
.ttl .yr i{{width:13mm;height:.35mm;background:var(--gold)}}
.ttl .sb{{font-weight:400;font-size:7.4pt;color:var(--grey);margin-top:1.6mm;letter-spacing:.2pt}}
.logos{{display:flex;align-items:center;gap:3.2mm;padding-top:4mm}}
.logos img.oy{{height:25mm}}
.logos img.bo{{height:19mm}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
col.c-m{{width:7mm}} col.c-p{{width:27.5mm}} col.c-d{{width:11mm}}
thead th{{background:var(--navy);color:#fff;font-weight:500;font-size:6.6pt;line-height:1.15;padding:1.6mm .2mm;vertical-align:middle}}
thead th.p{{text-align:right;padding-right:1.8mm}}
thead th.g{{color:var(--gold2)}}
tbody td{{height:4.9mm;font-size:10pt;text-align:center;vertical-align:middle;white-space:nowrap;border-bottom:.15mm solid var(--hair)}}
tbody tr:nth-child(even) td:not(.mo){{background:#faf7f1}}
tbody tr.first td{{border-top:.35mm solid var(--navy)}}
tbody tr:last-child td{{border-bottom:.45mm solid var(--navy)}}
td.mo{{background:var(--sand);border-bottom:0;border-left:.35mm solid var(--navy);padding:0}}
td.mo span{{font-family:Suez;font-size:6.4pt;color:var(--gold);display:inline-block;white-space:nowrap}}
td.mo.v span{{font-size:8pt;line-height:1.02}} td.mo.v em{{display:block;height:1.2mm}}
td.p{{text-align:right;padding-right:1.8mm;font-family:Suez;font-size:9.6pt;line-height:1}}
td.p .sp{{font-family:Rubik;font-weight:500;font-size:5.9pt;color:var(--gold);margin-right:.8mm}}
td.d{{font-weight:400;font-size:8pt;color:var(--grey)}}
td.t{{font-weight:500;font-feature-settings:"tnum"}}
.mot{{margin-top:4.2mm;background:var(--navy);color:#fff;display:flex;align-items:center;padding:1.8mm 4.5mm 1.8mm 5mm}}
.mot .k{{font-family:Karantina;font-weight:700;font-size:21pt;line-height:.8;color:var(--gold2);margin-left:4mm}}
.mot .s{{font-family:Suez;font-size:12.5pt;flex:1}}
.mot .tm{{font-family:Karantina;font-weight:700;font-size:27pt;line-height:.8;letter-spacing:.5pt}}
.foot{{margin-top:auto;display:flex}}
.c{{flex:1;text-align:center}}
.c + .c{{border-right:.25mm solid var(--hair)}}
.cl{{font-family:Suez;font-size:8.4pt;color:var(--gold)}}
.cn{{font-weight:600;font-size:12.5pt;letter-spacing:.2pt;margin-top:.2mm;font-feature-settings:"tnum"}}
.cs{{font-size:6.2pt;color:var(--grey);margin-top:.1mm;min-height:2.6mm}}
</style></head><body><div class="page"><div class="in">
<header><div class="bsd">בס״ד</div>
<div class="ttl"><h1>זמני השיעורים</h1><div class="yr"><b>לחורף תשפ״ז</b><i></i></div><div class="sb">לשבתות קודש · מפרשת חיי שרה</div></div>
<div class="logos"><img class="oy" src="file://{MAG}/ohel-yissachar.png"><img class="bo" src="file://{HERE}/assets/cover/logo.png"></div></header>
<table><colgroup><col class="c-m"><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr><th></th><th class="p">פרשה</th><th>תאריך</th>{''.join(f'<th class="{"g" if i % 2 else ""}">{c}</th>' for i, c in enumerate(COLS[2:]))}</tr></thead><tbody>{tr}</tbody></table>
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
