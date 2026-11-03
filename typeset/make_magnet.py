#!/usr/bin/env python3
"""Magnet (portrait, A5 + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
Style taken from the logo of Ohel Yissachar: cream ground with a faint gold leaf pattern, black cartouche frame with a gold line,
gold-foil title, gold ornaments (the embossed ornaments of the booklet, tinted gold).
usage: python3 make_magnet.py [out_dir]   -> magnet-shiurim-print.pdf (with bleed), magnet-shiurim.pdf / .png (trimmed)
data: assets/magnet/zmanim-choref-5787.xlsx (the sheet that was sent by mail)"""
import os, sys, subprocess, html, openpyxl
import numpy as np
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

# gold ramp (dark -> light), the colours of the gold letters of the logo
RAMP = np.array([[92, 58, 14], [150, 104, 34], [205, 160, 72], [238, 206, 122], [252, 238, 180]], float)


def gold(name):
    """the grey embossed ornament -> the same relief in gold (its grey value picks the place on the gold ramp)"""
    dst = os.path.join(MAG, f'gold-{name}.png')
    a = np.asarray(Image.open(os.path.join(HERE, 'assets', 'ornaments', name + '.png')).convert('RGBA')).astype(float)
    t = np.clip((a[..., :3].mean(-1) - 100) / 125, 0, 1) * (len(RAMP) - 1)
    i = np.minimum(t.astype(int), len(RAMP) - 2)
    f = (t - i)[..., None]
    rgb = RAMP[i] * (1 - f) + RAMP[i + 1] * f
    Image.fromarray(np.dstack([rgb, a[..., 3]]).astype(np.uint8), 'RGBA').save(dst, optimize=True)
    return dst


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


# a cartouche: rectangle whose corners are cut inward by a quarter circle (the shape of the frame of the logo)
def cartouche(x, y, w, h, r):
    return (f'M{x + r},{y} H{x + w - r} A{r},{r} 0 0 0 {x + w},{y + r} V{y + h - r} A{r},{r} 0 0 0 {x + w - r},{y + h} '
            f'H{x + r} A{r},{r} 0 0 0 {x},{y + h - r} V{y + r} A{r},{r} 0 0 0 {x + r},{y} Z')


def build():
    data = rows()
    orn = {n: gold(n) for n in ['corner', 'frame', 'line-scroll', 'flourish-wide-2']}
    tr = ''.join(
        f'<tr><td class="p">{parasha(r[0])}</td><td class="d">{html.escape(r[1].replace(" תשפ״ז", ""))}</td>'
        + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>' for r in data)
    foot = '<i></i>'.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div></div>' for a, n in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    frame_svg = (f'<svg class="fr" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">'
                 f'<path d="{cartouche(6.2, 6.2, W - 12.4, H - 12.4, 9)}" fill="none" stroke="#1b1a19" stroke-width="2.4"/>'
                 f'<path d="{cartouche(4.6, 4.6, W - 9.2, H - 9.2, 10.6)}" fill="none" stroke="url(#g)" stroke-width=".55"/>'
                 f'<path d="{cartouche(7.9, 7.9, W - 15.8, H - 15.8, 7.3)}" fill="none" stroke="url(#g)" stroke-width=".45"/>'
                 '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f1d98c"/><stop offset=".3" stop-color="#b8892f"/>'
                 '<stop offset=".55" stop-color="#f4dd93"/><stop offset=".8" stop-color="#a77a28"/><stop offset="1" stop-color="#e9cd7c"/></linearGradient></defs></svg>')
    # faint leaf pattern of the logo (three-lobed sprig), offset rows
    leaf = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="34" viewBox="0 0 40 34"><g fill="#c9a861">'
            '<path id="l" d="M10 13c-1.6-2.4-1.3-5 0-7 1.3 2 1.6 4.6 0 7zM10 13c-.8-2.2-2.6-3.6-5-3.8.8 2.3 2.6 3.7 5 3.8zM10 13c.8-2.2 2.6-3.6 5-3.8-.8 2.3-2.6 3.7-5 3.8z"/>'
            '<use href="#l" x="20" y="17"/></g></svg>')
    import urllib.parse
    leaf_url = 'data:image/svg+xml,' + urllib.parse.quote(leaf)
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Stam;src:url("file://{fonts}/StamAshkenazCLM.ttf")}}
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Bold.ttf");font-weight:700}}
@font-face{{font-family:Keter;src:url("file://{fonts}/KeterYG-Medium.ttf");font-weight:500}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#1b1a19;--brown:#6b2a17;--goldt:#8d6420;--rule:#d8c58f;
  --foil:linear-gradient(178deg,#fbeaa8 0%,#e2bd62 22%,#a9781f 44%,#d9b25a 58%,#f7e3a0 72%,#b5852c 100%)}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:David,serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#fffdf7}}
.pat{{position:absolute;inset:0;background:url('{leaf_url}') 0 0/10.5mm auto;opacity:.33}}
.pat:after{{content:"";position:absolute;inset:0;background:radial-gradient(ellipse 70% 55% at 50% 50%,#fffdf7 30%,rgba(255,253,247,.55) 75%,rgba(255,253,247,0) 100%)}}
.fr{{position:absolute;left:0;top:0}}
.co{{position:absolute;width:12mm;height:12mm;background:url('file://{orn["corner"]}') 0 0/contain no-repeat}}
.co.a{{right:9.6mm;top:9.6mm;transform:scaleX(-1)}} .co.b{{left:9.6mm;top:9.6mm}}
.co.c{{right:9.6mm;bottom:9.6mm;transform:scale(-1,-1)}} .co.d{{left:9.6mm;bottom:9.6mm;transform:scaleY(-1)}}
.in{{position:absolute;left:12.5mm;right:12.5mm;top:12mm;bottom:12.5mm;display:flex;flex-direction:column}}
header{{position:relative;height:34.5mm;display:flex;align-items:flex-start;justify-content:space-between}}
header img.oy{{height:30mm;margin-top:1mm;filter:drop-shadow(0 .5mm .6mm rgba(60,40,10,.3))}}
header img.bo{{height:24mm;margin-top:3.5mm}}
.ttl{{position:absolute;left:0;right:0;top:3mm;text-align:center}}
.foil{{background:var(--foil);-webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(.25mm .35mm 0 var(--brown)) drop-shadow(0 .6mm .7mm rgba(70,40,10,.35))}}
.ttl h1{{font-family:Stam;font-weight:400;font-size:37pt;line-height:1.05}}
.ttl .yr{{display:flex;align-items:center;justify-content:center;gap:2mm;margin-top:.4mm}}
.ttl .yr span{{font-family:Keter;font-weight:700;font-size:15.5pt;color:var(--ink);letter-spacing:.6pt}}
.ttl .yr i{{display:block;width:15mm;height:2.6mm;background:url('file://{orn["line-scroll"]}') center/contain no-repeat}}
.ttl .yr i.l{{transform:scaleX(-1)}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:1mm}}
col.c-p{{width:26%}} col.c-d{{width:15.5%}}
thead th{{background:var(--ink);color:#ecd48e;font-family:Frank;font-weight:700;font-size:7.3pt;line-height:1.1;padding:1.25mm .3mm;vertical-align:middle}}
thead th + th{{border-right:.25mm solid #6b5a33}}
thead tr{{border-bottom:.6mm solid #b8892f}}
tbody td{{height:4.66mm;font-size:9.5pt;text-align:center;vertical-align:middle;border-bottom:.18mm solid var(--rule);white-space:nowrap}}
tbody td + td{{border-right:.18mm solid var(--rule)}}
tbody tr:nth-child(even) td{{background:rgba(232,214,160,.28)}}
tbody tr:last-child td{{border-bottom:.5mm solid var(--ink)}}
td.p{{text-align:right;padding-right:1.4mm;font-family:Frank;font-weight:800;font-size:9.4pt}}
td.p .sp{{font-weight:600;font-size:7pt;color:var(--goldt)}}
td.d{{font-family:Frank;font-weight:500;font-size:8pt;color:#4a4237}}
td.t{{font-weight:700;font-variant-numeric:tabular-nums}}
.mot{{position:relative;height:15.5mm;margin:3.2mm 7mm 1.5mm;background:url('file://{orn["frame"]}') center/100% 100% no-repeat;
  display:flex;flex-direction:column;align-items:center;justify-content:center}}
.mot .k{{font-family:Keter;font-weight:700;font-size:12.5pt;line-height:1.1}}
.mot .s{{font-family:Frank;font-weight:700;font-size:10pt;color:var(--ink)}}
.mot .s b{{font-family:David;font-size:12pt}}
.foot{{margin-top:auto;display:flex;align-items:stretch;justify-content:space-between;border-top:.5mm solid var(--ink);padding:1.8mm 9mm 0}}
.foot i{{width:.25mm;background:#b8892f;margin:.4mm 0}}
.c{{flex:1;text-align:center}}
.cl{{font-family:Frank;font-weight:700;font-size:7.6pt;color:var(--goldt)}}
.cl small{{display:block;font-weight:500;font-size:6.2pt;color:#5d5345;margin-top:-.4mm}}
.cn{{font-family:David;font-weight:700;font-size:11.5pt;letter-spacing:.35pt;margin-top:.2mm}}
</style></head><body><div class="page"><div class="pat"></div>{frame_svg}
<div class="co a"></div><div class="co b"></div><div class="co c"></div><div class="co d"></div>
<div class="in">
<header><img class="oy" src="file://{MAG}/ohel-yissachar.png"><img class="bo" src="file://{HERE}/assets/cover/logo.png">
<div class="ttl"><h1 class="foil">זמני השיעורים</h1><div class="yr"><i></i><span>חורף תשפ״ז</span><i class="l"></i></div></div></header>
<table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr>{''.join(f'<th>{c}</th>' for c in COLS)}</tr></thead><tbody>{tr}</tbody></table>
<div class="mot"><div class="k foil">במוצאי שבת קודש</div><div class="s">שיעור לכיתה ח׳ בשעה <b>20:15</b></div></div>
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
