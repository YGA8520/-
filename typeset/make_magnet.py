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
    """the parasha, and under it in small letters what is special about the Shabbat (Chanukah, Shekalim..., Shabbat Mevarchim)"""
    name = RENAME.get(name, name)
    tags = []
    if ' - ' in name:
        name, b = name.split(' - ', 1)
        tags.append(b)
    if date in MEVARCHIM:
        tags.append('שבת מברכים')
    sub = f'<span class="sp">{" · ".join(html.escape(t) for t in tags)}</span>' if tags else ''
    return f'<b>{html.escape(name)}</b>{sub}'


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
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Shmulik;src:url("file://{fonts}/ShmulikCLM.ttf")}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#17120c;--brown:#5b3c14;--gold:#e2c27a;--line:rgba(91,60,20,.26);--plate:#2a1c0b}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:Frank,serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#e9d9a8 url("file://{MAG}/bg-gold.jpg") 0 0/100% 100% no-repeat}}
.bsd{{position:absolute;top:7mm;right:12mm;font-weight:500;font-size:7pt;color:var(--brown)}}
.logos{{position:absolute;top:7.3mm;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:7mm}}
.logos img.oy{{height:20mm;filter:drop-shadow(0 .4mm .5mm rgba(60,35,5,.35))}}
.logos img.bo{{height:15.5mm}}
.ttl{{position:absolute;top:27.2mm;left:0;right:0;text-align:center}}
.ttl h1{{font-family:Shmulik;font-weight:400;font-size:35pt;line-height:1.05;color:#1a120a;
  text-shadow:0 0 1.2mm rgba(255,250,232,.95),0 0 3mm rgba(255,244,214,.9),0 0 6mm rgba(255,238,200,.7),.6mm .9mm 1.1mm rgba(55,32,6,.55)}}
.ttl .yr{{margin-top:-.8mm;font-family:Shmulik;font-size:15.5pt;color:#6b3a0e;
  text-shadow:0 0 1mm rgba(255,250,232,.95),0 0 2.6mm rgba(255,244,214,.85),.4mm .6mm .8mm rgba(55,32,6,.45)}}
.tbl{{position:absolute;top:47mm;left:11mm;right:11mm;border:.55mm solid #fff;border-radius:3mm;overflow:hidden;
  background:rgba(255,252,240,.42);box-shadow:0 .4mm 1.2mm rgba(70,45,10,.18)}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
col.c-p{{width:22%}} col.c-d{{width:14%}}
thead th{{color:#3a260c;font-weight:700;font-size:7.1pt;line-height:1.08;padding:1.1mm .1mm;vertical-align:middle}}
thead tr.lb th{{background:linear-gradient(180deg,#fdf6e4,#ecd9a8);border-bottom:.45mm solid #b48a3c}}
thead th.p{{text-align:right;padding-right:2mm}}
/* the day row: Friday (ivory) and Shabbat Kodesh (gold) */
thead tr.dy th{{font-size:9pt;font-weight:800;padding:.7mm 0 .6mm;letter-spacing:.3pt}}
thead tr.dy th.fr{{background:#fffaf0;color:#5b3c14}}
thead tr.dy th.sh{{background:linear-gradient(180deg,#e8cd8a,#d4ae5f);color:#2a1a06;border-right:.6mm solid #fff}}
thead tr.dy th.e{{background:linear-gradient(180deg,#fdf6e4,#f6ead0)}}
thead tr.lb th.fr{{background:linear-gradient(180deg,#fffdf6,#f3e8cc)}}
thead tr.lb th.sh{{background:linear-gradient(180deg,#f4e3b6,#e2c47f)}}
thead tr.lb th.g, td.g{{border-right:.6mm solid #fff}}
tbody td{{height:5.2mm;line-height:1;padding:0 .2mm;text-align:center;vertical-align:middle;white-space:nowrap;border-top:.15mm solid var(--line)}}
td.fr{{background:rgba(255,255,255,.32)}}
td.sh{{background:rgba(214,176,96,.26)}}
tbody tr:nth-child(even) td.p, tbody tr:nth-child(even) td.d{{background:rgba(255,255,255,.3)}}
tbody tr:nth-child(even) td.fr{{background:rgba(255,255,255,.55)}}
tbody tr:nth-child(even) td.sh{{background:rgba(214,176,96,.4)}}
td.p{{text-align:right;padding-right:2mm;line-height:.86}}
td.p b{{display:block;font-weight:800;font-size:10.4pt;line-height:.82}}
td.p .sp{{display:block;font-weight:600;font-size:5.9pt;line-height:.88;color:#7a4a12;margin-top:.3mm}}
td.d{{font-weight:500;font-size:8.6pt;color:#3d2c14}}
td.t{{font-family:David;font-weight:700;font-size:11.6pt;letter-spacing:.1pt}}
.mot{{position:absolute;top:180mm;left:12mm;right:46mm;height:8.6mm;background:linear-gradient(180deg,#fffaf0,#f1e2bb);border-radius:4.75mm;color:var(--ink);
  display:flex;align-items:center;justify-content:center;gap:2.4mm;box-shadow:0 .4mm 1mm rgba(60,35,5,.25);border:.45mm solid #b48a3c}}
.mot .k{{color:var(--brown);font-weight:700;font-size:9.6pt}}
.mot .s{{font-weight:800;font-size:10.8pt}}
.mot .tm{{font-family:David;font-weight:700;font-size:13pt;color:#7a2c10}}
.mot i{{width:.3mm;height:4.2mm;background:#c4a463}}
/* the phone lines: white numbers on a dark plate */
.foot{{position:absolute;top:191.4mm;left:12mm;right:46mm;height:17mm;display:flex;align-items:center;background:linear-gradient(180deg,#3a2810,var(--plate));
  border-radius:3mm;border:.45mm solid #b48a3c;box-shadow:0 .4mm 1mm rgba(60,35,5,.3)}}
.c{{flex:1;text-align:center}}
.c + .c{{border-right:.2mm solid rgba(226,194,122,.45)}}
.cl{{font-weight:700;font-size:7.6pt;color:var(--gold)}}
.cn{{font-family:David;font-weight:700;font-size:11.4pt;letter-spacing:.3pt;line-height:1.2;color:#fff}}
.cs{{font-weight:500;font-size:5.7pt;color:#e9dcc0;min-height:2.2mm}}
.still{{position:absolute;right:5mm;bottom:4.5mm;width:40mm;filter:drop-shadow(-.4mm -.2mm .8mm rgba(60,35,5,.25))}}
</style></head><body><div class="page">
<div class="bsd">בס״ד</div>
<div class="logos"><img class="oy" src="file://{MAG}/ohel-yissachar.png"><img class="bo" src="file://{HERE}/assets/cover/logo.png"></div>
<div class="ttl"><h1>זמני השיעורים</h1><div class="yr">חורף תשפ״ז</div></div>
<div class="tbl"><table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr class="dy"><th class="e" colspan="2"></th><th class="fr" colspan="3">יום שישי</th><th class="sh" colspan="3">שבת קודש</th></tr>
<tr class="lb">{''.join(f'<th class="{"p" if i == 0 else ("fr" if 2 <= i < 5 else ("sh" if i >= 5 else ""))}{" g" if i == 5 else ""}">{c}</th>' for i, c in enumerate(COLS))}</tr></thead><tbody>{tr}</tbody></table></div>
<div class="mot"><span class="k">מוצאי שבת קודש</span><i></i><span class="s">שיעור לכיתה ח׳</span><i></i><span class="tm">20:15</span></div>
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
