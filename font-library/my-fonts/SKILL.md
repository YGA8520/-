---
name: my-fonts
description: The user's personal font library (Hebrew and Latin typefaces, with files bundled in this skill). Use whenever the output has typography that matters - HTML pages and artifacts, PDFs, Word/PowerPoint files, posters, covers, booklets, charts or images with text - or when the user mentions fonts, typefaces, גופן, גופנים, פונט, עימוד or typesetting. Pick the best-fitting font for each role (title, body, quote, footnote, numbers) from the catalog instead of defaulting to generic system fonts.
---

# My fonts

The user supplied their own fonts so they can be used **everywhere, in any design or layout, chosen by what suits each place**. Choosing is your job: look at the catalog, decide per role, and say briefly which fonts you used.

## Files in this skill

| File | What it is |
|---|---|
| `FONTS.md` | The catalog: every family, its weights, Hebrew/niqqud/taamim/Latin coverage, category and what it is good for. **Read this first.** |
| `catalog.json` | Same data with exact file names, family names, weights and licence strings. |
| `fonts/` | The font files themselves. |
| `scripts/install_fonts.sh` | Installs the fonts for the system (fontconfig) - needed before rendering with LibreOffice, Pillow, matplotlib, Chromium by family name. |
| `scripts/font_face_css.py` | Prints `@font-face` CSS (relative URLs or embedded base64) for HTML pages and artifacts. |

If `FONTS.md` shows an empty table, the library has not been filled yet: say so, and fall back to normal font choices.

## How to choose

1. **Check coverage before anything else.** Hebrew text needs a family whose *Hebrew* column is ✔. Text with niqqud needs *Niqqud* ✔; Tanach/liturgical text with cantillation needs *Taamim* ✔. Text containing ״ ׳ ־ ₪ needs *Marks* ✔ (otherwise those glyphs silently fall back to another font and look wrong). Mixed Hebrew + English needs both Hebrew and Latin ✔, or two families paired deliberately.
2. **One role, one font.** Typically: display/title, body, secondary (notes, captions), numbers/data. Two to three families per piece is enough; pair a distinctive display face with a calm text face. Do not use more weights than the design needs.
3. **Respect the catalog notes.** `Good for` and `Avoid` are the user's own judgement; they override your taste.
4. **Match the text, not just the layout.** Long continuous reading: a text-grade face at 10-12pt+. Short headings, covers, posters: a display face. Small sizes and screens: avoid thin or calligraphic faces. Sacred texts / formal documents: stay with the user's traditional book faces rather than decorative ones.
5. **Use real weights/italics from the files.** If a family has no bold or italic, do not fake it with `font-weight`/`font-style` (browsers synthesize an ugly one) - use another family or a different weight that exists.
6. When unsure, render a quick specimen of 2-3 candidates with the actual text and look at it before deciding.

## Using the fonts per output type

- **HTML / artifact:** `python3 scripts/font_face_css.py --base64 "Family A" "Family B"` and paste the CSS into the page `<style>` (self-contained, works anywhere). Or without `--base64`, copy the needed files next to the page and publish them as supporting files / assets, keeping `--base` consistent. Always add a sensible fallback stack (`serif`/`sans-serif`) and `direction: rtl` for Hebrew blocks. Mind the 16 MB page limit when embedding.
- **PDF (via Chromium/Playwright, WeasyPrint, reportlab):** run `sh scripts/install_fonts.sh` once, then use the family name; fonts get embedded in the PDF automatically. Verify with `pdffonts out.pdf` that nothing fell back.
- **Images / charts (Pillow, matplotlib):** install first, or load the file path directly (`ImageFont.truetype(path, size)`); Pillow needs `libraqm` for correct RTL - otherwise reorder the Hebrew string yourself, or render through Chromium instead.
- **Word / PowerPoint (.docx/.pptx):** the file only stores the font *name*. The reader sees it correctly only if the font is installed on their machine, so: (a) tell the user which fonts must be installed to view it as designed, or (b) deliver a PDF alongside. Embedding into the file is possible only for some fonts and apps; do not promise it. Set both the Latin and the complex-script (Hebrew) font slots (`w:rFonts` `ascii`/`hAnsi` *and* `cs`; in pptx the `latin` and `cs` elements).
- **The claude.ai / desktop interface itself** cannot change its own UI font; this skill affects what you produce.

## Licences

Each file carries its licence string in `catalog.json`. Embedding in a PDF/web page or sending a font file to someone else are different permissions: when a licence looks restrictive or is empty and the output will be published or distributed, mention it to the user once instead of deciding silently. Never put fonts into a public repository or public page unless the user says their licence allows it.

## Maintaining the library (for the user's setup, not for every task)

New fonts: drop files into `fonts/`, then from the repository run `python3 font-library/tools/build_catalog.py` (regenerates `FONTS.md` and `catalog.json`), add the family's category/use to `font-library/notes.json`, and `python3 font-library/tools/package_skill.py` to get a fresh zip.
