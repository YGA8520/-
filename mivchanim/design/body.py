"""Body of the booklet: units (exam / answer sheet / chavura / sheet) -> HTML."""
import html
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa: E402,F403
from manifest import PARTS  # noqa: E402

PAGE_W, PAGE_H = 210, 297

CSS = r'''
:root{
  --ink:#16181d; --muted:#5d6471; --faint:#8b91a0;
  --navy:#14264a; --navy2:#223a63;
  --gold:#a8802f; --gold2:#c9a24b; --gold3:#e6d29a;
  --rule:#c9bfa6; --panel:#f6f2e7; --panel2:#efe8d6;
}
@page { size:210mm 297mm; margin:24mm 22mm 20mm 17mm; }
@page :right { margin:24mm 17mm 20mm 22mm; }
@page full { margin:0 }
.fullpage{page:full;width:210mm;height:297mm;position:relative;break-before:page;break-after:page;overflow:hidden}
.fullpage .pg{width:210mm;height:297mm;position:relative;overflow:hidden}
.fullpage .pg>svg{position:absolute;left:0;top:0;width:210mm;height:297mm;display:block}
.fullpage .pg>img.bg{position:absolute;left:0;top:0;width:210mm;height:297mm;display:block}
.fullpage svg text{font-family:'Frank','David',serif;direction:rtl}
html,body{margin:0;padding:0;background:#fff}
body{font-family:'Frank','David',serif;font-weight:500;font-size:12pt;line-height:1.6;color:var(--ink);
     font-feature-settings:"kern","liga";text-rendering:geometricPrecision;direction:rtl;
     -webkit-print-color-adjust:exact;print-color-adjust:exact;}
.marker{display:inline;white-space:nowrap;letter-spacing:0;font-weight:400;text-transform:none;font-size:2.4px;line-height:0;color:#fff;font-family:Arial,sans-serif;unicode-bidi:isolate;direction:ltr}
section.unit{break-before:page}
section.unit:first-child{break-before:auto}
.pagebreak{break-before:page}
b{font-weight:700}
.sm{font-size:.84em}
u{text-decoration:underline;text-decoration-thickness:.06em;text-underline-offset:.16em}

/* ---------- unit opener ---------- */
.uhead{display:flex;align-items:center;gap:6mm;margin:0 0 3mm}
.uhead .seal{flex:0 0 20mm;width:20mm;height:20mm}
.uhead .seal svg{width:20mm;height:20mm;display:block}
.uhead .tx{flex:1;min-width:0}
.uhead .kicker{font-family:'Heebo',sans-serif;font-weight:600;font-size:8.6pt;letter-spacing:.16em;color:var(--gold);line-height:1.2;margin-bottom:.6mm}
.uhead .title{font-family:'Suez',serif;font-size:25pt;line-height:1.12;color:var(--navy);margin:0}
.uhead .title.long{font-size:20pt}
.uhead .title.xlong{font-size:16.5pt;line-height:1.2}
.uhead .sub{font-family:'Frank',serif;font-weight:500;font-size:12pt;line-height:1.35;color:var(--muted);margin-top:1.2mm}
.uhead .org{font-family:'Heebo',sans-serif;font-weight:600;font-size:8.6pt;color:var(--gold);margin-top:1.2mm;letter-spacing:.03em}
.orn{height:4mm;margin:.4mm 0 3.4mm;position:relative}
.orn img{display:block;width:100%;height:auto;margin:-3.2mm 0}
.form{display:flex;align-items:flex-end;gap:7mm;margin:0 0 4.2mm;font-family:'Heebo',sans-serif;font-weight:600;font-size:10pt;color:var(--navy)}
.form .nm{flex:1;display:flex;align-items:flex-end;gap:2.5mm}
.form .nm i{flex:1;border-bottom:.35mm solid var(--navy2);height:5.8mm}
.form .sc{display:flex;align-items:flex-end;gap:2.5mm}
.form .sc i{display:block;width:18mm;height:9.4mm;border:.35mm solid var(--navy2);border-radius:2.2mm;position:relative}
.form .sc i:after{content:'';position:absolute;inset:1mm;border:.15mm solid var(--gold3);border-radius:1.4mm}

/* ---------- headings ---------- */
.h2{display:flex;align-items:center;gap:3.2mm;margin:5.4mm 0 3mm;break-after:avoid;break-inside:avoid}
.h2 .dia{flex:0 0 3.2mm;width:3.2mm;height:3.2mm;background:linear-gradient(135deg,#f0dc9a,#a8802f);transform:rotate(45deg);}
.h2 .t{font-family:'Suez',serif;font-size:15.5pt;line-height:1.1;color:var(--navy);white-space:nowrap}
.h2 .ln{flex:1;height:0;border-top:.3mm solid var(--gold2);position:relative}
.h2 .ln:after{content:'';position:absolute;right:0;left:0;top:.75mm;border-top:.12mm solid var(--gold3)}
.h3{display:flex;align-items:center;gap:2.4mm;margin:4.2mm 0 2mm;break-after:avoid;break-inside:avoid;
    font-family:'Heebo',sans-serif;font-weight:800;font-size:10.6pt;line-height:1.3;color:var(--navy)}
.h3:before{content:'';flex:0 0 2.2mm;width:2.2mm;height:2.2mm;background:var(--gold2);transform:rotate(45deg)}
.cap{font-family:'Heebo',sans-serif;font-weight:600;font-size:8.4pt;letter-spacing:.06em;color:var(--gold);margin:4.5mm 0 1mm;break-after:avoid}
.note{display:table;margin:2mm auto 3.4mm;padding:.8mm 4mm;border:.25mm solid var(--gold2);border-radius:5mm;
      font-family:'Heebo',sans-serif;font-weight:600;font-size:9.4pt;color:var(--gold);text-align:center}

/* ---------- questions ---------- */
.q{display:grid;grid-template-columns:8.4mm 1fr;column-gap:3.2mm;margin:0 0 3.5mm;break-inside:avoid}
.q .bd{box-sizing:border-box;width:8.7mm;height:8.7mm;border:.55mm solid transparent;border-radius:50%;display:flex;align-items:center;justify-content:center;
       font-family:'Frank',serif;font-weight:700;font-size:10.2pt;line-height:1;color:var(--navy);margin-top:.3mm;position:relative;background:linear-gradient(#fff,#fff) padding-box,linear-gradient(135deg,#f3e2a2 0%,#b98f36 38%,#e8cf80 62%,#8c6a27 100%) border-box}
.q .bd:after{content:'';position:absolute;inset:.45mm;border:.12mm solid var(--gold3);border-radius:50%}
.q .bd.dig{font-family:'Heebo',sans-serif;font-weight:800;font-size:9.4pt}
.q .bd.none{border-radius:2mm}
.q .bd.none:after{border-radius:1.2mm}
.q .bd.none svg{width:3.4mm;height:3.4mm}
.q .qb{min-width:0}
.q .qt{margin:0;font-size:12pt;line-height:1.6;text-align:right}
.q .qt+.qt,.q .qt+.subs,.q .subs+.qt{margin-top:1.6mm}
.q .kick{font-family:'Heebo',sans-serif;font-weight:800;font-size:9pt;color:var(--gold);margin-left:1.6mm;letter-spacing:.04em}
.q .subs{margin:1.4mm 0 0;padding:0;list-style:none}
.q .subs li{display:flex;gap:2mm;margin:0 0 .8mm}
.q .subs .sl{flex:0 0 auto;font-weight:700;color:var(--navy);font-family:'Heebo',sans-serif;font-size:9.6pt;padding-top:.5mm}
.alines{margin:1.4mm 0 0}
.sublines{margin:2mm 0 0}
.sl2{display:flex;align-items:flex-end;gap:2.4mm;height:9.4mm}
.sl2 span{font-family:'Heebo',sans-serif;font-weight:800;font-size:9.6pt;color:var(--navy);padding-bottom:.8mm}
.sl2 i{flex:1;border-bottom:.28mm solid var(--rule);height:8mm}
.alines i{display:block;height:6.9mm;border-bottom:.28mm solid var(--rule)}
.alines i:first-child{border-top:0}
.exam .q.nolines{margin-bottom:4.6mm}

/* ---------- answers ---------- */
.ans{background:var(--panel);border-right:1.1mm solid var(--gold2);border-radius:0 0 0 0;padding:2.8mm 4.6mm 3mm 4.2mm;margin:2.2mm 0 6mm;font-size:11pt;line-height:1.58}
.ans .ah{font-family:'Heebo',sans-serif;font-weight:800;font-size:8.8pt;letter-spacing:.08em;color:var(--gold);margin:0 0 1.2mm}
.ans p{margin:0 0 1.5mm}
.ans p:last-child{margin-bottom:0}
.ans p.subh{font-family:'Heebo',sans-serif;font-weight:800;font-size:9.6pt;color:#14264a;margin:2.4mm 0 1.2mm;break-after:avoid}
.chavura .q{margin-bottom:3.1mm}
.key .q{margin-bottom:0;break-after:avoid}
.key .ans{font-size:10.6pt;line-height:1.54;margin-bottom:5mm}
.ans .ah{break-after:avoid}
.ans p{orphans:2;widows:2}
.key .q+.ans{margin-top:2.4mm}
.key .q .qt{font-weight:500}

/* ---------- plain paragraphs, rules, closing ---------- */
p.p{margin:0 0 2.4mm;text-align:right}
.rules{border:.28mm solid var(--gold2);border-radius:2.4mm;padding:2.2mm 5mm 2.4mm;margin:2.4mm 0 3.6mm;break-inside:avoid;background:#fff}
.rules .rh{font-family:'Heebo',sans-serif;font-weight:800;font-size:9.6pt;color:var(--navy);margin-bottom:1.4mm}
.rules .ri{display:flex;gap:2.2mm;font-size:10.2pt;line-height:1.5;margin:0 0 .6mm}
.rules .ri .rl{flex:0 0 4.5mm;font-weight:700;color:var(--gold);font-family:'Heebo',sans-serif;font-size:9.4pt;padding-top:.3mm}
.close{display:flex;align-items:center;gap:4mm;margin:6mm 0 1mm;break-inside:avoid;break-before:avoid}
.close .ln{flex:1;border-top:.3mm solid var(--gold2)}
.close .t{font-family:'Suez',serif;font-size:15pt;color:var(--navy);white-space:nowrap}
.closenote{break-before:avoid;text-align:center;font-family:'Frank',serif;font-weight:500;color:var(--muted);font-size:10.4pt;margin:1.4mm 0}
.sheet .ans,.sheet p.p{font-size:10.4pt}
.sheet .q .qt{font-size:11pt;font-weight:500}
.sheet .q{margin-bottom:0}
.sheet .q+.ans{margin-top:2.2mm}

/* ---------- part dividers ---------- */
.div{break-before:page;break-after:page;height:247mm;position:relative}
'''


def esc(t):
    return html.escape(t, quote=False)


def runs_html(runs):
    out = []
    for t, f in runs:
        s = esc(t)
        if 's' in f:
            s = f'<span class="sm">{s}</span>'
        if 'u' in f:
            s = f'<u>{s}</u>'
        if 'b' in f:
            s = f'<b>{s}</b>'
        out.append(s)
    return ''.join(out)


def seal_svg(text, uid):
    """round seal: the gold ring on a blue disc (art/ring.png) with cream letters"""
    t = text
    parts = ['<image href="art/ring.png" x="-3.7" y="-3.7" width="107.4" height="107.4"/>']

    def tx(x, y, size, s_):
        return (f'<text x="{x + .8}" y="{y + 1.2}" text-anchor="middle" font-family="Suez" font-size="{size}" fill="#04101F" opacity=".55" style="direction:rtl">{s_}</text>'
                f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Suez" font-size="{size}" fill="#F6EBC8" style="direction:rtl">{s_}</text>')
    if '–' in t:
        a_, b_ = t.split('–')
        size = 21 if max(len(a_), len(b_)) <= 2 else 17
        parts.append(tx(50, 50 - 3.5, size, a_))
        parts.append('<path d="M44,50 h12" stroke="#E4C97F" stroke-width="1.1"/>')
        parts.append(tx(50, 50 + size * .72 + 2.5, size, b_))
    else:
        size = 46 if len(t) == 1 else (34 if len(t) == 2 else 26)
        parts.append(tx(50, round(50 + size * .255, 1), size, t))
    return f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


ORN = '<img src="art/rule.png" alt="">'


def norm_close(t):
    t = re.sub(r'\s+', '', t)
    t = re.sub(r'!+', '!', t)
    if t.startswith('הצלחה'):
        t = 'ב' + t
    t = t.replace('בהצלחה', 'בהצלחה ', 1).strip() if 'רבה' in t or 'מרובה' in t else t
    t = re.sub(r'בהצלחה(רבה|מרובה)', r'בהצלחה \1', t)
    return t


def block_html(b, kind):
    t = b['t']
    if t == 'h2':
        return f'<div class="h2"><span class="dia"></span><span class="t">{runs_html(b["runs"])}</span><span class="ln"></span></div>'
    if t == 'h3':
        return f'<div class="h3">{runs_html(b["runs"])}</div>'
    if t == 'cap':
        return f'<div class="cap">{runs_html(b["runs"])}</div>'
    if t == 'note':
        return f'<div class="note">{runs_html(b["runs"])}</div>'
    if t == 'p':
        return f'<p class="p">{runs_html(b["runs"])}</p>'
    if t == 'q':
        lab = b.get('label')
        if lab:
            cls = 'bd dig' if lab.isdigit() else 'bd'
            badge = f'<div class="{cls}">{esc(lab)}</div>'
        else:
            badge = '<div class="bd none"><svg viewBox="0 0 10 10"><path d="M5 0 L10 5 L5 10 L0 5Z" fill="#c9a24b"/></svg></div>'
        kick = f'<span class="kick">{esc(b["kicker"])}:</span>' if b.get('kicker') else ''
        body = f'<p class="qt">{kick}{runs_html(b["runs"])}</p>'
        for m in b.get('more', []):
            body += f'<p class="qt">{runs_html(m)}</p>'
        if b.get('subs'):
            body += '<ul class="subs">' + ''.join(f'<li><span class="sl">{esc(s["label"])}</span><span>{runs_html(s["runs"])}</span></li>' for s in b['subs']) + '</ul>'
        n = b.get('n')
        lines = f'<div class="alines">{"<i></i>" * n}</div>' if n else ''
        if b.get('sublines'):
            lines = '<div class="sublines">' + ''.join(f'<div class="sl2"><span>{esc(l)}.</span><i></i></div>' for l in b['sublines']) + '</div>'
            n = 1
        return f'<div class="q{"" if n else " nolines"}">{badge}<div class="qb">{body}{lines}</div></div>'
    if t == 'ans':
        head = f'<div class="ah">{runs_html(b["head"])}</div>' if b.get('head') else '<div class="ah">תשובה</div>'
        paras = ''.join((f'<p class="subh">{runs_html(p["runs"])}</p>' if p.get('sub') else f'<p>{runs_html(p["runs"])}</p>') for p in b['paras'])
        return f'<div class="ans">{head}{paras}</div>'
    if t == 'lines':
        return f'<div class="alines" style="margin-bottom:5mm">{"<i></i>" * b["n"]}</div>'
    if t == 'close':
        return f'<div class="close"><span class="ln"></span><span class="t">{esc(norm_close(b["text"]))}</span><span class="ln"></span></div>'
    if t == 'closenote':
        return f'<div class="closenote">{runs_html(b["runs"])}</div>'
    return ''


def group_rules(blocks):
    """collect consecutive 'rule' blocks into one box"""
    out, cur = [], None
    for b in blocks:
        if b['t'] == 'h3' and re.match(r'^כללי המבחן', ''.join(t for t, f in b['runs'])):
            cur = dict(t='rules', head=b['runs'], items=[])
            out.append(cur)
            continue
        if b['t'] == 'rule' and cur is not None:
            cur['items'].append(b)
            continue
        cur = None if b['t'] != 'rule' else cur
        out.append(b)
    return out


def rules_html(b):
    items = ''.join(f'<div class="ri"><span class="rl">{esc(i["label"])}.</span><span>{runs_html(i["runs"])}</span></div>' for i in b['items'])
    return f'<div class="rules"><div class="rh">{runs_html(b["head"])}</div>{items}</div>'


def unit_html(u):
    kind = u['kind']
    title = u['title']
    cls = 'title' + (' xlong' if len(title) > 30 else (' long' if len(title) > 16 else ''))
    sub = f'<div class="sub">{esc(u["sub"])}</div>' if u.get('sub') else ''
    org = f'<div class="org">{esc(u["org"])}</div>' if u.get('org') else ''
    kick = f'<div class="kicker"><span class="marker" dir="ltr">MK{u["id"]}MK</span>{esc(u["kicker"])}</div>'
    form = ''
    if u.get('form') == 'שם':
        form = '<div class="form"><div class="nm"><span>שם:</span><i></i></div><div class="sc"><span>ציון:</span><i></i></div></div>'
    elif u.get('form') == 'הרב':
        form = '<div class="form"><div class="nm"><span>הרב:</span><i></i></div><div class="sc"><span>ציון:</span><i></i></div></div>'
    head = (f'<div class="uhead"><div class="seal">{seal_svg(u["seal"], u["id"])}</div>'
            f'<div class="tx">{kick}<h1 class="{cls}">{esc(title)}</h1>{sub}{org}</div></div><div class="orn">{ORN}</div>{form}')
    blocks = group_rules(u['blocks'])
    body = ''.join(rules_html(b) if b['t'] == 'rules' else block_html(b, kind) for b in blocks)
    return f'<section class="unit {kind}" id="{u["id"]}">{head}{body}</section>'


def part_divider_html(part, idx, units_in_part):
    """full page divider for a part (drawn like the cover: navy + gold)"""
    items = ''.join(f'<div class="di"><span class="dt">{esc(u["kicker"] + " · " + u["title"])}</span></div>' for u in units_in_part)
    return f'<section class="div" id="part-{part["id"]}"><span class="marker" dir="ltr">MKpart{part["id"]}MK</span></section>'


def build_body(units, parts, dividers_html=None):
    by_part = {}
    for u in units:
        by_part.setdefault(u['part'], []).append(u)
    out = []
    for p in parts:
        if dividers_html and p['id'] in dividers_html:
            out.append(f'<section class="fullpage" id="part-{p["id"]}">{dividers_html[p["id"]].replace("__MARK__", "MKpart" + p["id"] + "MK")}</section>')
        for u in by_part.get(p['id'], []):
            out.append(unit_html(u))
    from front import DIV_CSS
    css = font_face_css('../assets/fonts') + CSS + DIV_CSS
    return f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>מבחני הסימנים</title><style>{css}</style></head><body>{"".join(out)}</body></html>'


if __name__ == '__main__':
    units = json.load(open(os.path.join(ROOT, 'work', 'units.json'), encoding='utf8'))
    htmltxt = build_body(units, PARTS)
    open(os.path.join(ROOT, 'build', 'body.html'), 'w', encoding='utf8').write(htmltxt)
    print('ok', len(htmltxt))
