#!/usr/bin/env python3
"""Quick contact sheet of the Hebrew letters for one weight (PIL, no shaping)."""
import sys
from PIL import Image, ImageDraw, ImageFont

style = sys.argv[1] if len(sys.argv) > 1 else "Regular"
out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/letters_{style}.png"
path = f"/home/user/-/fonts/Nusach-{style}.ttf"
size = 210
f = ImageFont.truetype(path, size)
allletters = "אבגדהוזחטיכךלמםנןסעפףצץקרשת"
part = int(sys.argv[3]) if len(sys.argv) > 3 else 0
letters = allletters[part * 14:(part + 1) * 14]
cols = 7
rows = (len(letters) + cols - 1) // cols
cw, ch = 260, 360
im = Image.new("RGB", (cols * cw, rows * ch), "white")
d = ImageDraw.Draw(im)
for i, c in enumerate(letters):
    r, col = divmod(i, cols)
    x = (cols - 1 - col) * cw + 20
    y = r * ch + 20
    # baseline guide
    base = y + int(size * 0.95)
    d.line((x - 10, base + 0, x + cw - 30, base), fill=(220, 120, 120))
    d.text((x, y), c, font=f, fill="black", anchor="la")
im.save(out)
print(out)
