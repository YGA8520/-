# Notes for Claude

## Fonts
The user's personal font library lives in `font-library/my-fonts/` (catalog: `font-library/my-fonts/FONTS.md`, usage rules: `font-library/my-fonts/SKILL.md`).
Before choosing typography for any output (HTML/PDF/DOCX/images), read the catalog and pick the font that fits each role; check Hebrew/niqqud/marks coverage first.
Do not commit the fonts listed in `.gitignore` (client-proprietary, local only).

## Graphics
The user's graphics library (frames, backgrounds, gold/royal elements, curtains, banners, wood) is mirrored in `graphics-library/` (compressed copies of `D:\גרפיקה` on his PC; see `graphics-library/README.md`).
Before any design work, read `graphics-library/catalog/my-graphics.md` (quick-pick table, quality and content rules), then the per-file catalogs in the same folder. Never use images showing women or girls.
When graphics are added, update all three: the PC catalog `D:\גרפיקה\_קטלוג`, the account skills (my-graphics*), and `graphics-library/` (run `tools/mirror.py`, update `catalog/`, commit and push).
