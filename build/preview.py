#!/usr/bin/env python3
"""Render sample text with real shaping using headless Chromium.

    python3 build/preview.py out.png [Weight] [html-file-to-use-instead]
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

SAMPLE = """
<div class="row big">אבגדהוזחטיכךלמםנןסעפףצץקרשת</div>
<div class="row big">בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ</div>
<div class="row">שִׁימוּ לֵב: שֹׂרָה וְשָׂרָה, אֱמֶת וְחֶסֶד, וַיֹּאמֶר, שׁוּרוּק וְקֻבּוּץ</div>
<div class="row">0123456789 · שלום, עולם! מה נשמע? (בסדר) [כן] «ציטוט» "מרכאות" – מקף־מקף 12:30 ‘א’ “ב”</div>
<div class="row">כָּל אֶחָד וְאֶחָד מֵהֶם הִגִּיעַ לְכָאן בַּזְּמַן, וְהַכֹּל הָיָה מוּכָן לַחֲגִיגָה הַגְּדוֹלָה בַּחֲצֵר.</div>
"""

CSS = """
@font-face { font-family: N; src: url('file://%(font)s'); }
body { margin: 0; background: #fff; padding: 20px 30px; width: 1500px; }
.row { font-family: N; direction: rtl; font-size: 54px; line-height: 1.5; color: #111; }
.big { font-size: 86px; }
"""


async def main():
    out = sys.argv[1]
    style = sys.argv[2] if len(sys.argv) > 2 else "Regular"
    html_file = sys.argv[3] if len(sys.argv) > 3 else None
    font = os.path.join(ROOT, "fonts", f"Nusach-{style}.ttf")
    if html_file:
        body = open(html_file, encoding="utf-8").read()
    else:
        body = SAMPLE
    html = f"<html><head><meta charset='utf-8'><style>{CSS % {'font': font}}</style></head><body>{body}</body></html>"
    path = out + ".html"
    open(path, "w", encoding="utf-8").write(html)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1560, "height": 800})
        await pg.goto("file://" + path)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=out, full_page=True)
        await b.close()
    print(out)


asyncio.run(main())
