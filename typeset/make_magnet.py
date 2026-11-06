#!/usr/bin/env python3
"""Magnet (A5 portrait + 3mm bleed): the times of the shabbat shiurim, winter 5787, from parashat Chayei Sarah.
Laid on the brushed-gold background page that was sent (cleaned by make_magnet_bg.py: corner flourishes and Shabbat still life kept).
Classic poster setting: logos at the top between the flourishes, calligraphic title (Shmulik CLM) with a light halo and a shadow, the table on a light glass panel with a
white rounded border (as the box of the background page), light cream header row, David Libre for the times,
Motzaei Shabbat on a light plate, the phone lines beside the large Shabbat still life (shabbat-still.png) at the bottom right.
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
        f'<tr><td class="p">{parasha(r[0])}</td><td class="d">{html.escape(r[1].replace(" תשפ״ז", ""))}</td>'
        + ''.join(f'<td class="t">{html.escape(v)}</td>' for v in r[2:8]) + '</tr>' for r in data)
    foot = ''.join(f'<div class="c"><div class="cl">{a}</div><div class="cn" dir="ltr">{n}</div><div class="cs">{b}</div></div>' for a, n, b in FOOT)
    fonts = os.path.join(HERE, 'assets', 'fonts')
    W, H = 154, 216
    page = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Shmulik;src:url("file://{fonts}/ShmulikCLM.ttf")}}
@font-face{{font-family:Frank;src:url("file://{fonts}/FrankRuhlLibre.ttf");font-weight:300 900}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Bold.ttf");font-weight:700}}
@font-face{{font-family:David;src:url("file://{fonts}/DavidLibre-Medium.ttf");font-weight:500}}
@page{{size:{W}mm {H}mm;margin:0}}
:root{{--ink:#17120c;--brown:#5b3c14;--gold:#e2c27a;--line:rgba(91,60,20,.28)}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}mm;height:{H}mm}}
body{{font-family:Frank,serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{position:relative;width:{W}mm;height:{H}mm;overflow:hidden;background:#e9d9a8 url("file://{MAG}/bg-gold.jpg") 0 0/100% 100% no-repeat}}
.bsd{{position:absolute;top:7mm;right:0;left:0;text-align:center;font-weight:500;font-size:7pt;color:var(--brown)}}
.logos{{position:absolute;top:9mm;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:7mm}}
.logos img.oy{{height:25mm;filter:drop-shadow(0 .4mm .5mm rgba(60,35,5,.35))}}
.logos img.bo{{height:19.5mm}}
.ttl{{position:absolute;top:35mm;left:0;right:0;text-align:center}}
.ttl h1{{font-family:Shmulik;font-weight:400;font-size:41pt;line-height:1.05;color:#1a120a;
  text-shadow:0 0 1.2mm rgba(255,250,232,.95),0 0 3mm rgba(255,244,214,.9),0 0 6mm rgba(255,238,200,.7),.6mm .9mm 1.1mm rgba(55,32,6,.55)}}
.ttl .yr{{margin-top:-.4mm;font-family:Shmulik;font-size:19pt;color:#6b3a0e;
  text-shadow:0 0 1mm rgba(255,250,232,.95),0 0 2.6mm rgba(255,244,214,.85),.4mm .6mm .8mm rgba(55,32,6,.45)}}
.tbl{{position:absolute;top:60.5mm;left:13.5mm;right:13.5mm;border:.55mm solid #fff;border-radius:3mm;overflow:hidden;
  background:rgba(255,252,240,.42);box-shadow:0 .4mm 1.2mm rgba(70,45,10,.18)}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
col.c-p{{width:21%}} col.c-d{{width:17%}}
thead th{{background:linear-gradient(180deg,#fdf6e4,#ecd9a8);color:#3a260c;border-bottom:.45mm solid #b48a3c;font-weight:700;font-size:7.1pt;line-height:1.12;padding:1.45mm .2mm;vertical-align:middle}}
thead th.p{{text-align:right;padding-right:2mm}}
tbody td{{height:4.2mm;line-height:1;padding:0 .2mm;font-size:9.6pt;text-align:center;vertical-align:middle;white-space:nowrap;border-top:.15mm solid var(--line)}}
tbody tr:nth-child(even) td{{background:rgba(255,255,255,.38)}}
td.p{{text-align:right;padding-right:2mm;font-weight:800;font-size:9.4pt}}
td.p .sp{{font-weight:600;font-size:6.6pt;color:var(--brown)}}
td.d{{font-weight:500;font-size:7.9pt;color:#3d2c14}}
td.t{{font-family:David;font-weight:700;font-size:10.2pt}}
.mot{{position:absolute;top:174.5mm;left:37mm;right:33mm;height:9.5mm;background:linear-gradient(180deg,#fffaf0,#f1e2bb);border-radius:4.75mm;color:var(--ink);
  display:flex;align-items:center;justify-content:center;gap:2.4mm;box-shadow:0 .4mm 1mm rgba(60,35,5,.25);border:.45mm solid #b48a3c}}
.mot .k{{color:var(--brown);font-weight:700;font-size:9.4pt}}
.mot .s{{font-weight:800;font-size:10.4pt}}
.mot .tm{{font-family:David;font-weight:700;font-size:12.5pt;color:#7a2c10}}
.mot i{{width:.3mm;height:4.2mm;background:#c4a463}}
.foot{{position:absolute;top:188mm;left:36mm;right:41mm;display:flex}}
.c{{flex:1;text-align:center}}
.still{{position:absolute;right:5mm;bottom:4.5mm;width:46mm;filter:drop-shadow(-.4mm -.2mm .8mm rgba(60,35,5,.25))}}
.c + .c{{border-right:.2mm solid var(--line)}}
.cl{{font-weight:700;font-size:7.4pt;color:var(--brown)}}
.cn{{font-family:David;font-weight:700;font-size:10.2pt;letter-spacing:.3pt;line-height:1.15}}
.cs{{font-weight:500;font-size:5.6pt;color:#4a3618}}
</style></head><body><div class="page">
<div class="bsd">בס״ד</div>
<div class="logos"><img class="oy" src="file://{MAG}/ohel-yissachar.png"><img class="bo" src="file://{HERE}/assets/cover/logo.png"></div>
<div class="ttl"><h1>זמני השיעורים</h1><div class="yr">חורף תשפ״ז</div></div>
<div class="tbl"><table><colgroup><col class="c-p"><col class="c-d">{'<col>' * 6}</colgroup>
<thead><tr>{''.join(f'<th class="{"p" if i == 0 else ""}">{c}</th>' for i, c in enumerate(COLS))}</tr></thead><tbody>{tr}</tbody></table></div>
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
