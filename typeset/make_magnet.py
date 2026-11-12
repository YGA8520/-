#!/usr/bin/env python3
"""Magnet (A5 portrait + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Vayetze.
Laid on the brushed-gold background page that was sent (cleaned by make_magnet_bg.py, without the corner flourishes).
Classic poster setting: logos at the top, calligraphic title (Shmulik CLM) with a light halo and a shadow, the table on a light glass panel with a
white rounded border (as the box of the background page), a day row over the times (Friday ivory, Shabbat Kodesh gold, the columns tinted the same),
Shabbat Mevarchim marked under the parasha, David Libre for the times, Motzaei Shabbat on a light plate, the phone lines
(white on a dark plate) beside the large Shabbat still life (shabbat-still.png) at the bottom right.
usage: python3 make_magnet.py [out_dir]   -> magnet-shiurim-print.pdf (with bleed), magnet-shiurim.pdf / .png (trimmed)
data: assets/magnet/zmanim-choref-5787.xlsx (the sheet that was sent by mail)"""
import os, sys, subprocess, html, openpyxl
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output', 'magnet'))
MAG = os.path.join(HERE, 'assets', 'magnet')
FIRST = 'ויצא'                                   # Chayei Sarah and Toldot are past: the table starts from Vayetze
RENAME = {'מקץ זאת - שבת חנוכה': 'מקץ - זאת חנוכה'}
# Shabbat Mevarchim in the range of the table (the Shabbat in the week before Rosh Chodesh; checked with pyluach for 5787):
# Tevet, Shevat, Adar I, Adar II, Nisan
MEVARCHIM = {'כ״ה בכסלו', 'כ״ג בטבת', 'כ״ט בשבט', 'כ״ז באדר א׳', 'כ״ה באדר ב׳'}

COLS = ['פרשת השבוע', 'תאריך', 'שיעור<br>מכיתה ג׳', 'שיעור<br>מכיתה ז׳', 'הכנה<br>לשבת', 'שיעור<br>לישיבה קטנה', 'הרב טוטיאן<br>א׳', 'הרב טוטיאן<br>ב׳']
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


def parasha(name, date):
    """the parasha and, beside it in small letters one under the other, what is special about the Shabbat
    (Chanukah, Shekalim..., Shabbat Mevarchim): every row keeps the height of one line"""
    name = RENAME.get(name, name)
    tags = []
    if ' - ' in name:
        name, b = name.split(' - ', 1)
        tags.append(b)
    if date in MEVARCHIM:
        tags.append('שבת מברכים')
    sub = f'<span class="sp">{"".join(f"<i>{html.escape(t)}</i>" for t in tags)}</span>' if tags else ''
    return f'<div class="pw"><b>{html.escape(name)}</b>{sub}</div>'


def build():
    data = rows()
    tr = []
    for r in data:
        date = r[1].replace(' תשפ״ז', '')
        tr.append(f'<tr><td class="p">{parasha(r[0], date)}</td><td class="d">{html.escape(date)}</td>'
                  + ''.join(f'<td class="t {"fr" if i < 3 else "sh"}{" g" if i == 3 else ""}">{html.escape(v)}</td>' for i, v in enumerate(r[2:8])) + '</tr>')
    tr = ''.join(tr)
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div><div class="cs">{b}</div></div>' for a, n, b in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    wave = ('M0,9 C18,3 34,2 52,6 C72,10.5 92,12 112,7 C126,3.6 141,2.6 154,5.5 V40 H0 Z')
    hi = ('M0,9 C18,3 34,2 52,6 C72,10.5 92,12 112,7 C126,3.6 141,2.6 154,5.5')
    banner = (f'<svg class="ban" viewBox="0 0 154 40" width="154mm" height="40mm" preserveAspectRatio="none">'
              '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9b768"/><stop offset=".45" stop-color="#b98e3e"/>'
              '<stop offset="1" stop-color="#94692a"/></linearGradient>'
              '<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff6dc" stop-opacity=".2"/><stop offset=".5" stop-color="#fff6dc" stop-opacity=".9"/>'
              '<stop offset="1" stop-color="#fff6dc" stop-opacity=".25"/></linearGradient></defs>'
              f'<path d="{wave}" fill="url(#bg)"/>'
              f'<path d="{hi}" fill="none" stroke="url(#sh)" stroke-width=".9" transform="translate(0,1.6)"/>'
              f'<path d="{hi}" fill="none" stroke="#7d5820" stroke-width=".35" transform="translate(0,-.15)" opacity=".6"/></svg>')
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Shmulik;src:url("file://{fonts}/ShmulikCLM.ttf")}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#17120c;--brown:#5b3c14;--gold:#e2c27a;--line:rgba(91,60,20,.24)}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:Frank,serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#e9d9a8 url("file://{MAG}/bg-gold.jpg") 0 0/100% 100% no-repeat}}
.bsd{{position:absolute;top:6.2mm;right:11.5mm;font-weight:500;font-size:6.6pt;color:var(--brown)}}
/* header: the title in the middle, a logo on each side */
header{{position:absolute;top:8.5mm;left:10.5mm;right:10.5mm;height:25mm;display:flex;align-items:center;justify-content:space-between}}
header img.oy{{height:24mm;filter:drop-shadow(0 .4mm .5mm rgba(60,35,5,.35))}}
header img.bo{{height:19mm}}
.ttl{{text-align:center;flex:1}}
.ttl h1{{font-family:Shmulik;font-weight:400;font-size:36pt;line-height:1;color:#1a120a;white-space:nowrap;
  text-shadow:0 0 1.2mm rgba(255,250,232,.95),0 0 3mm rgba(255,244,214,.9),0 0 6mm rgba(255,238,200,.7),.6mm .9mm 1.1mm rgba(55,32,6,.55)}}
.ttl .yr{{margin-top:.6mm;font-family:Shmulik;font-size:16pt;line-height:1;color:#6b3a0e;
  text-shadow:0 0 1mm rgba(255,250,232,.95),0 0 2.6mm rgba(255,244,214,.85),.4mm .6mm .8mm rgba(55,32,6,.45)}}
.tbl{{position:absolute;top:34.5mm;left:10.5mm;right:10.5mm;border:.55mm solid #fff;border-radius:3mm;overflow:hidden;
  background:rgba(255,252,240,.45);box-shadow:0 .4mm 1.2mm rgba(70,45,10,.18)}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
col.c-p{{width:26%}} col.c-d{{width:14.5%}}
thead th{{color:#3a260c;font-weight:700;font-size:7.3pt;line-height:1.08;padding:1.2mm .1mm;vertical-align:middle}}
thead tr.lb th{{background:linear-gradient(180deg,#fdf6e4,#efdfb4);border-bottom:.45mm solid #b48a3c}}
thead th.p{{text-align:right;padding-right:2.2mm}}
thead tr.dy th{{font-size:9.4pt;font-weight:800;padding:.8mm 0 .7mm;letter-spacing:.3pt}}
thead tr.dy th.e{{background:linear-gradient(180deg,#fdf6e4,#f5e8c8)}}
/* Friday: a soft wheat tone, Shabbat Kodesh: deeper gold; the step between them is gentle, with a thin gold rule */
thead tr.dy th.fr{{background:linear-gradient(180deg,#f3e2b4,#e9d39a);color:#4a300c}}
thead tr.dy th.sh{{background:linear-gradient(180deg,#e2c37c,#cfa655);color:#2a1a06}}
thead tr.lb th.fr{{background:linear-gradient(180deg,#f7ebc8,#ecd9a6)}}
thead tr.lb th.sh{{background:linear-gradient(180deg,#ecd49a,#ddbd76)}}
thead th.g, td.g{{border-right:.35mm solid #b48a3c}}
tbody td{{height:5.35mm;line-height:1;padding:0 .2mm;text-align:center;vertical-align:middle;white-space:nowrap;border-top:.15mm solid var(--line)}}
td.fr{{background:rgba(232,206,146,.30)}}
td.sh{{background:rgba(212,172,90,.34)}}
tbody tr:nth-child(even) td.p, tbody tr:nth-child(even) td.d{{background:rgba(255,255,255,.32)}}
tbody tr:nth-child(even) td.fr{{background:rgba(232,206,146,.46)}}
tbody tr:nth-child(even) td.sh{{background:rgba(212,172,90,.48)}}
td.p{{text-align:right;padding-right:2.2mm}}
.pw{{display:flex;align-items:center;gap:1.6mm}}
.pw b{{font-weight:800;font-size:10.6pt;line-height:1}}
.pw .sp{{display:flex;flex-direction:column;justify-content:center;font-weight:600;font-size:6pt;line-height:1.02;color:#7a4a12;
  border-right:.25mm solid rgba(122,74,18,.45);padding-right:1.1mm}}
.pw .sp i{{font-style:normal;display:block}}
td.d{{font-weight:500;font-size:8.6pt;color:#3d2c14}}
td.t{{font-family:David;font-weight:700;font-size:11.8pt;letter-spacing:.1pt}}
/* Motzaei Shabbat, between the table and the banner, beside the candles */
.mot{{position:absolute;top:169mm;left:58mm;right:10.5mm;height:8.8mm;background:linear-gradient(180deg,#fffaf0,#f1e2bb);border-radius:4.4mm;color:var(--ink);
  display:flex;align-items:center;justify-content:center;gap:2.4mm;box-shadow:0 .4mm 1mm rgba(60,35,5,.25);border:.45mm solid #b48a3c}}
.mot .k{{color:var(--brown);font-weight:700;font-size:9.6pt}}
.mot .s{{font-weight:800;font-size:10.8pt}}
.mot .tm{{font-family:David;font-weight:700;font-size:13pt;color:#7a2c10}}
.mot i{{width:.3mm;height:4.2mm;background:#c4a463}}
/* the wavy banner along the bottom, with the phone lines on it and the Shabbat still life standing on its left end */
.ban{{position:absolute;left:0;bottom:0;filter:drop-shadow(0 -.6mm 1mm rgba(70,45,10,.3))}}
.foot{{position:absolute;top:189.5mm;left:56mm;right:8mm;height:20mm;display:flex;align-items:center}}
.c{{flex:1;text-align:center;padding:0 .8mm}}
.c + .c{{border-right:.25mm solid rgba(255,246,220,.6)}}
.cl{{font-weight:800;font-size:8pt;color:#3a230a}}
.cn{{white-space:nowrap;font-family:David;font-weight:700;font-size:12pt;letter-spacing:.3pt;line-height:1.2;color:#fff;
  text-shadow:0 .25mm .5mm rgba(60,35,5,.7),0 0 1.2mm rgba(90,55,10,.5)}}
.cs{{font-weight:600;font-size:6pt;color:#3a230a;min-height:2.2mm}}
.still{{position:absolute;left:5mm;bottom:4.5mm;width:50mm;filter:drop-shadow(.4mm -.2mm .9mm rgba(60,35,5,.3))}}
</style></head><body><div class="page">
<div class="bsd">בס״ד</div>
<header><img class="oy" src="file://{MAG}/ohel-yissachar.png"><div class="ttl"><h1>זמני השיעורים</h1><div class="yr">חורף תשפ״ז</div></div>
<img class="bo" src="file://{HERE}/assets/cover/logo.png"></header>
<div class="tbl"><table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr class="dy"><th class="e" colspan="2"></th><th class="fr" colspan="3">יום שישי</th><th class="sh g" colspan="3">שבת קודש</th></tr>
<tr class="lb">{''.join(f'<th class="{"p" if i == 0 else ("fr" if 2 <= i < 5 else ("sh" if i >= 5 else ""))}{" g" if i == 5 else ""}">{c}</th>' for i, c in enumerate(COLS))}</tr></thead><tbody>{tr}</tbody></table></div>
<div class="mot"><span class="k">מוצאי שבת קודש</span><i></i><span class="s">שיעור לכיתה ח׳</span><i></i><span class="tm">20:15</span></div>
{banner}
<div class="foot">{foot}</div>
<img class="still" src="file://{MAG}/shabbat-still.png">
</div></body></html>'''
    os.makedirs(OUT, exist_ok=True)
    M, BL = 12, 3                                           # sheet margin around the bleed, bleed
    SW, SH = W + 2 * M, H + 2 * M
    off, ln = BL + 1.5, 6
    tx, ty = (M + BL, SW - M - BL), (M + BL, SH - M - BL)
    lines = [(x, ty[0] - off, x, ty[0] - off - ln) for x in tx] + [(x, ty[1] + off, x, ty[1] + off + ln) for x in tx] + \
            [(tx[0] - off, y, tx[0] - off - ln, y) for y in ty] + [(tx[1] + off, y, tx[1] + off + ln, y) for y in ty]
    svg = (f'<svg style="position:absolute;left:0;top:0" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">'
           + ''.join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#000" stroke-width="0.09"/>' for a, b, c, d in lines)
           + f'<text x="{tx[0] + 2}" y="{SH - M + 7}" font-family="Helvetica,Arial" font-size="2.1" fill="#000" direction="ltr">'
             f'magnet-shiurim  |  trim {W - 2 * BL} x {H - 2 * BL} mm (A5)  |  bleed {BL} mm</text></svg>')
    sheet = (page.replace(f'@page{{size:{W}mm {H}mm;margin:0}}', f'@page{{size:{SW}mm {SH}mm;margin:0}}')
                 .replace(f'html,body{{width:{W}mm;height:{H}mm}}', f'html,body{{width:{SW}mm;height:{SH}mm;background:#fff}}')
                 .replace('<body><div class="page">', f'<body>{svg}<div class="page" style="position:absolute;left:{M}mm;top:{M}mm">'))
    assert sheet != page
    open(os.path.join(HERE, '_magnet_marks.html'), 'w', encoding='utf-8').write(sheet)
    src = os.path.join(HERE, '_magnet.html')
    open(src, 'w', encoding='utf-8').write(page)
    js = f'''let c;try{{c=require('playwright').chromium}}catch(e){{c=require('/opt/node22/lib/node_modules/playwright').chromium}}
(async()=>{{const b=await c.launch();const p=await b.newPage({{viewport:{{width:582,height:816}},deviceScaleFactor:300/96}});
await p.goto('file://{src}');await p.evaluate(()=>document.fonts.ready);
console.log(await p.evaluate(()=>{{const r=e=>document.querySelector(e).getBoundingClientRect(),px=96/25.4;return 'table ends '+(r('.tbl').bottom/px).toFixed(1)+'mm, mot '+(r('.mot').top/px).toFixed(1)+'mm, foot '+(r('.foot').top/px).toFixed(1)+'-'+(r('.foot').bottom/px).toFixed(1)+'mm'}}));
await p.pdf({{path:'{OUT}/magnet-shiurim-print.pdf',width:'{W}mm',height:'{H}mm',printBackground:true}});
await p.screenshot({{path:'{OUT}/_full.png'}});
await p.goto('file://{HERE}/_magnet_marks.html');await p.evaluate(()=>document.fonts.ready);
await p.pdf({{path:'{OUT}/magnet-shiurim-print-marks.pdf',width:'{SW}mm',height:'{SH}mm',printBackground:true}});
await b.close()}})()'''
    subprocess.run(['node', '-e', js], check=True)
    im = Image.open(f'{OUT}/_full.png').convert('RGB')
    px = im.width / W
    trim = im.crop((round(3 * px), round(3 * px), round((W - 3) * px), round((H - 3) * px)))
    trim.save(f'{OUT}/magnet-shiurim.png', dpi=(300, 300))
    trim.save(f'{OUT}/magnet-shiurim.pdf', resolution=300)
    os.remove(f'{OUT}/_full.png')
    boxes(f'{OUT}/magnet-shiurim-print-marks.pdf', SW, SH, M, BL)
    print(len(data), 'shabbatot ->', OUT)


def boxes(path, SW, SH, M, BL):
    """TrimBox / BleedBox on the sheet with the crop marks (the content itself is drawn by the browser, not merged)"""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject
    mm = 72 / 25.4
    w = PdfWriter(clone_from=PdfReader(path))
    pg = w.pages[0]
    top = float(pg.mediabox.top)               # the browser rounds the sheet size a little: measure from the top left, as laid out
    box = lambda x0, y0, x1, y1: RectangleObject([x0 * mm, top - y1 * mm, x1 * mm, top - y0 * mm])
    pg.trimbox = box(M + BL, M + BL, SW - M - BL, SH - M - BL)
    pg.bleedbox = box(M, M, SW - M, SH - M)
    w.write(path)

if __name__ == '__main__':
    build()
