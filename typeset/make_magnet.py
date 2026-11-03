#!/usr/bin/env python3
"""Magnet (portrait, A5 + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
usage: python3 make_magnet.py [out_dir]   -> magnet-shiurim.pdf (print, with bleed) + magnet-shiurim.png (preview, trimmed)
data: assets/magnet/zmanim-choref-5787.xlsx (the sheet that was sent by mail)"""
import os, sys, subprocess, html, openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output', 'magnet'))
FIRST = 'חיי שרה'

COLS = ['פרשת השבוע', 'תאריך', 'שיעור<br>מכיתה ג׳', 'שיעור<br>מכיתה ז׳', 'הכנה<br>לשבת', 'שיעור<br>לישיבה קטנה', 'הרב טוטיאן<br>א׳', 'הרב טוטיאן<br>ב׳']
FOOT = [('לתרומות', '', '079-969-7788'),
        ('קו ׳בית הוראה׳', 'לתפילה וברכות וזמני היום', '077.215.00.94'),
        ('קו קול הלשון', '', '073.371.83.76')]


def rows():
    ws = openpyxl.load_workbook(os.path.join(HERE, 'assets', 'magnet', 'zmanim-choref-5787.xlsx')).worksheets[0]
    data, on = [], False
    for r in ws.iter_rows(min_row=4, values_only=True):
        if not r[0]:
            continue
        name = str(r[0]).strip()
        on = on or name == FIRST
        if on:
            data.append([str(v).strip() if v is not None else '' for v in r[:8]])
    return data


def parasha(name):
    """'וישב - שבת חנוכה' -> name + the special shabbat in small gold letters"""
    name = name.replace('מקץ זאת - שבת חנוכה', 'מקץ - שבת חנוכה')
    if ' - ' in name:
        a, b = name.split(' - ', 1)
        return f'<b>{html.escape(a)}</b><span class="sp">{html.escape(b)}</span>'
    return f'<b>{html.escape(name)}</b>'


def build():
    data = rows()
    tr = []
    for i, r in enumerate(data):
        date = r[1].replace(' תשפ״ז', '')
        special = ' - ' in r[0]
        tr.append(f'<tr class="{"sh" if special else ""}"><td class="p">{parasha(r[0])}</td><td class="d">{html.escape(date)}</td>'
                  + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>')
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div>' + (f'<div class="cs">{b}</div>' if b else '') +
                   f'<div class="cn" dir="ltr">{n}</div></div>' for a, b, n in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Bold.ttf");font-weight:700}}
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Medium.ttf");font-weight:500}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@page{{size:154mm 216mm;margin:0}}
:root{{--navy:#131c2e;--navy2:#22304a;--gold:#b48a3a;--gold2:#e6c878;--goldt:#9a7429;--cream:#fbf7ee;--line:#e4d6b4}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:154mm;height:216mm}}
body{{background:var(--cream);font-family:David,serif;color:var(--navy);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:154mm;height:216mm;overflow:hidden;
  background:radial-gradient(ellipse at 50% 0%,#fffdf8 0,var(--cream) 60%,#f4ecda 100%)}}
/* frame: a navy band at the bleed, a gold double line inside the trim */
.frame{{position:absolute;inset:3mm;border:2.2mm solid var(--navy)}}
.frame:before{{content:"";position:absolute;inset:0.9mm;border:0.45mm solid var(--gold)}}
.frame:after{{content:"";position:absolute;inset:1.8mm;border:0.15mm solid var(--gold)}}
.in{{position:absolute;left:9mm;right:9mm;top:8.5mm;bottom:8.5mm;display:flex;flex-direction:column}}
header{{display:flex;align-items:center;justify-content:space-between;height:33mm}}
header img.oy{{height:32mm}}
header img.bo{{height:27mm}}
.ttl{{flex:1;text-align:center}}
.ttl h1{{font-family:Keter;font-weight:700;font-size:31pt;line-height:1;color:var(--navy);letter-spacing:.3pt}}
.ttl .yr{{display:inline-block;margin-top:1.8mm;padding:.7mm 6mm 1mm;font-family:Keter;font-weight:700;font-size:15pt;color:#fff;
  background:linear-gradient(180deg,#d1ab5c,#a67c2e);border-radius:1mm;box-shadow:0 .3mm .6mm rgba(0,0,0,.25)}}
.ttl .sub{{margin-top:1.6mm;font-family:Frank;font-weight:600;font-size:8.6pt;color:var(--goldt)}}
.rule{{height:2.2mm;margin:1.2mm 0 1.6mm;background:
  linear-gradient(90deg,transparent,var(--gold) 15%,var(--gold) 85%,transparent) center/100% .35mm no-repeat}}
.rule{{position:relative}}
.rule:after{{content:"◆";position:absolute;left:50%;top:50%;transform:translate(-50%,-52%);font-size:6pt;color:var(--gold);background:var(--cream);padding:0 1.5mm}}
table{{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;border:.35mm solid var(--navy);border-radius:1.2mm;overflow:hidden;background:#fff}}
col.c-p{{width:25%}} col.c-d{{width:16%}}
thead th{{background:var(--navy);color:var(--gold2);font-family:Frank;font-weight:700;font-size:7.4pt;line-height:1.12;padding:1.3mm .4mm;vertical-align:middle;
  border-left:.2mm solid #34425e}}
thead th:last-child{{border-left:0}}
tbody td{{height:4.92mm;font-size:9.6pt;text-align:center;vertical-align:middle;border-top:.15mm solid var(--line);border-left:.15mm solid var(--line);white-space:nowrap}}
tbody td:last-child{{border-left:0}}
tbody tr:nth-child(even) td{{background:#f8f2e4}}
td.p{{text-align:right;padding-right:1.6mm;font-size:10pt}}
td.p b{{font-weight:700}}
td.p .sp{{font-family:Frank;font-weight:600;font-size:6.6pt;color:var(--goldt);margin-right:1.2mm}}
td.d{{font-family:Frank;font-weight:500;font-size:8.2pt;color:#3b465c}}
td.t{{font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:.15pt}}
tr.sh td.p b{{color:var(--navy)}}
.mot{{margin-top:2.4mm;display:flex;align-items:center;justify-content:center;gap:3mm;padding:1.7mm 3mm;border-radius:1.2mm;
  background:linear-gradient(180deg,var(--navy2),var(--navy));color:#fff;font-family:Frank;font-weight:700;font-size:10.5pt;border:.35mm solid var(--gold)}}
.mot .k{{font-family:Keter;font-size:12pt;color:var(--gold2)}}
.mot .tm{{font-family:David;font-size:13pt;color:var(--gold2);letter-spacing:.3pt}}
.mot .dot{{color:var(--gold)}}
.foot{{margin-top:auto;display:grid;grid-template-columns:1fr 1.35fr 1fr;gap:2mm}}
.c{{text-align:center;border:.3mm solid var(--gold);border-radius:1.2mm;padding:1.2mm 1mm 1.1mm;background:#fff}}
.cl{{font-family:Frank;font-weight:800;font-size:8.6pt;color:var(--navy)}}
.cs{{font-family:Frank;font-weight:500;font-size:6.4pt;color:var(--goldt);margin-top:-.2mm}}
.cn{{font-family:David;font-weight:700;font-size:11pt;color:var(--navy);letter-spacing:.4pt;margin-top:.3mm}}
</style></head><body><div class="page"><div class="frame"></div><div class="in">
<header><img class="oy" src="file://{HERE}/assets/magnet/ohel-yissachar.png">
<div class="ttl"><h1>זמני השיעורים</h1><div class="yr">חורף תשפ״ז</div><div class="sub">לשבתות קודש · מפרשת חיי שרה ועד שבת הגדול</div></div>
<img class="bo" src="file://{HERE}/assets/cover/logo.png"></header>
<div class="rule"></div>
<table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr>{''.join(f'<th>{c}</th>' for c in COLS)}</tr></thead><tbody>{''.join(tr)}</tbody></table>
<div class="mot"><span class="k">במוצאי שבת קודש</span><span class="dot">◆</span><span>שיעור לכיתה ח׳</span><span class="dot">◆</span><span>בשעה <span class="tm">20:15</span></span></div>
<div class="foot">{foot}</div>
</div></div></body></html>'''
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(HERE, '_magnet.html')
    open(src, 'w', encoding='utf-8').write(page)
    js = f'''let c;try{{c=require('playwright').chromium}}catch(e){{c=require('/opt/node22/lib/node_modules/playwright').chromium}}
(async()=>{{const b=await c.launch();const p=await b.newPage({{viewport:{{width:582,height:816}},deviceScaleFactor:300/96}});
await p.goto('file://{src}');await p.evaluate(()=>document.fonts.ready);
const o=await p.evaluate(()=>{{const t=document.querySelector('.in');return t.scrollHeight>t.clientHeight+1?'OVERFLOW '+t.scrollHeight+'>'+t.clientHeight:'fit'}});console.log(o);
await p.pdf({{path:'{OUT}/magnet-shiurim-print.pdf',width:'154mm',height:'216mm',printBackground:true}});
await p.screenshot({{path:'{OUT}/_full.png'}});await b.close()}})()'''
    subprocess.run(['node', '-e', js], check=True)
    from PIL import Image
    im = Image.open(f'{OUT}/_full.png').convert('RGB')
    px = im.width / 154
    trim = im.crop((round(3 * px), round(3 * px), round(151 * px), round(213 * px)))
    trim.save(f'{OUT}/magnet-shiurim.png', dpi=(300, 300))
    trim.save(f'{OUT}/magnet-shiurim.pdf', resolution=300)
    os.remove(f'{OUT}/_full.png')
    print(len(data), 'shabbatot ->', OUT)


if __name__ == '__main__':
    build()
