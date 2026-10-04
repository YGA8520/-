#!/usr/bin/env python3
"""Render the specimen sheet (PNG + PDF) for the Nusach family with headless Chromium."""
import asyncio
import os

from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
STYLES = [("Light", "קל", 300), ("Regular", "רגיל", 400), ("Medium", "בינוני", 500),
          ("Bold", "מודגש", 700), ("Black", "שחור", 900)]

LETTERS = "אבגדהוזחטיכךלמםנןסעפףצץקרשת"
DIGITS = "0123456789"
PUNCT = ".,:;!?-־–—()[]«»׳״"
NIQQUD = "בְּ בֲּ בֱּ בֳּ בִּ בֵּ בֶּ בַּ בָּ בֹּ בֻּ שׁ שׂ"
VERSE = ("בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ. וְהָאָרֶץ הָיְתָה תֹהוּ וָבֹהוּ, "
         "וְחֹשֶׁךְ עַל־פְּנֵי תְהוֹם, וְרוּחַ אֱלֹהִים מְרַחֶפֶת עַל־פְּנֵי הַמָּיִם.")
PLAIN = ("כל אות היא מפגש בין קו עבה לקו דק, בין תנועת יד לבין סדר של דפוס. "
         "גופן טוב נשכח מהעין ונשאר בלב: הוא נותן למילים לדבר. "
         "בדקו אותו בכותרת גדולה, בגוף טקסט ארוך ובהערות שוליים קטנות — 0123456789.")


def css():
    out = []
    for s, _, w in STYLES:
        out.append(f"@font-face{{font-family:'Nusach {s}';src:url('file://{ROOT}/fonts/Nusach-{s}.ttf');}}")
    return "\n".join(out)


def html():
    rows = "".join(
        f"<div class='wrow'><div class='wname'><b>{he}</b><span>{s} · {w}</span></div>"
        f"<div class='wsample' style=\"font-family:'Nusach {s}'\">נוסח — סדרת אותיות עבריות</div></div>"
        for s, he, w in STYLES)
    glyph_blocks = "".join(
        f"<div class='gl' style=\"font-family:'Nusach {s}'\">{LETTERS}</div>" for s, _, _ in STYLES)
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
{css()}
:root {{ --ink:#1c1a17; --paper:#f7f2e8; --accent:#9a5b17; --mute:#6d655a; --line:#d9cfbd; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); width:1600px; padding:70px 90px 60px; font-family:'Nusach Regular', sans-serif; }}
.top {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid var(--ink); padding-bottom:26px; }}
.title {{ font-family:'Nusach Black'; font-size:210px; line-height:1; margin:0; }}
.sub {{ font-family:'Nusach Light'; font-size:44px; color:var(--mute); text-align:left; direction:rtl; line-height:1.3; }}
h2 {{ font-family:'Nusach Bold'; font-size:34px; color:var(--accent); margin:56px 0 18px; border-bottom:1px solid var(--line); padding-bottom:10px; }}
.wrow {{ display:flex; align-items:center; gap:30px; border-bottom:1px dotted var(--line); padding:6px 0; }}
.wname {{ width:190px; display:flex; flex-direction:column; font-size:26px; }}
.wname span {{ font:14px sans-serif; color:var(--mute); direction:ltr; text-align:right; }}
.wsample {{ font-size:78px; line-height:1.35; }}
.gl {{ font-size:66px; line-height:1.35; letter-spacing:.02em; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:60px; }}
.txt {{ font-size:30px; line-height:1.7; }}
.txt.small {{ font-size:21px; line-height:1.75; }}
.tag {{ font:13px sans-serif; color:var(--mute); direction:ltr; text-align:right; margin-bottom:4px; }}
.big {{ font-size:120px; line-height:1.4; }}
.foot {{ margin-top:50px; padding-top:18px; border-top:2px solid var(--ink); font-family:'Nusach Light'; font-size:24px; color:var(--mute); display:flex; justify-content:space-between; }}
</style></head><body>
<div class="top">
  <div class="sub">משפחת גופנים עבריים<br>חמישה משקלים · ניקוד · ספרות · פיסוק</div>
  <h1 class="title">נוסח</h1>
</div>

<h2>חמישה משקלים</h2>
{rows}

<h2>האלף־בית בכל המשקלים</h2>
{glyph_blocks}

<h2>ספרות, פיסוק וניקוד</h2>
<div class="cols">
  <div>
    <div class="tag">Regular</div>
    <div class="txt" style="font-family:'Nusach Regular';font-size:64px;line-height:1.5">{DIGITS}<br>{PUNCT}</div>
  </div>
  <div>
    <div class="tag">Bold — niqqud</div>
    <div class="txt" style="font-family:'Nusach Bold';font-size:64px;line-height:1.5">{NIQQUD}</div>
  </div>
</div>

<h2>כותרת וטקסט רץ</h2>
<div class="big" style="font-family:'Nusach Black'">בראשית ברא</div>
<div class="cols">
  <div>
    <div class="tag">Light 30</div><div class="txt" style="font-family:'Nusach Light'">{VERSE}</div>
    <div class="tag" style="margin-top:22px">Regular 21</div><div class="txt small" style="font-family:'Nusach Regular'">{PLAIN} {PLAIN}</div>
  </div>
  <div>
    <div class="tag">Medium 30</div><div class="txt" style="font-family:'Nusach Medium'">{PLAIN}</div>
    <div class="tag" style="margin-top:22px">Bold 21</div><div class="txt small" style="font-family:'Nusach Bold'">{PLAIN} {PLAIN}</div>
  </div>
</div>

<div class="foot"><span>נוסח · עיצוב מקורי</span><span>TTF · WOFF2</span></div>
</body></html>"""


async def main():
    outdir = os.path.join(ROOT, "specimen")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "specimen.html")
    open(path, "w", encoding="utf-8").write(html())
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1600, "height": 1000})
        await pg.goto("file://" + path)
        await pg.wait_for_timeout(800)
        h = await pg.evaluate("document.documentElement.scrollHeight")
        await pg.screenshot(path=os.path.join(outdir, "Nusach-specimen.png"), full_page=True)
        await pg.pdf(path=os.path.join(outdir, "Nusach-specimen.pdf"), width="1600px", height=f"{h + 2}px",
                     print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        await b.close()
    os.remove(path)
    print("specimen written to", outdir, "height", h)


asyncio.run(main())
