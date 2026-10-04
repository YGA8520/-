# פלפולא דאורייתא – typesetting pipeline

Turns the source `.docx` files into (1) a print-quality **PDF** (B5, two columns, own typesetting engine running in Chromium)
and (2) an editable **Word** file with real styles. Everything is driven by `config.json`; no code change is needed for fonts.

## Run
```
pip install python-docx lxml pillow
npm install playwright && npx playwright install chromium      # Node >= 18
SRC_DIR=/path/to/folder/with/the/original/docx   python run_all.py     # (Windows PowerShell: $env:SRC_DIR="C:\path"; python run_all.py)
```
* `book.py` finds every source by its original file name (table in `src_names.json`; `f17` = the big compilation) – just point `SRC_DIR` at the folder.
* outputs: `out/book.pdf`, `out/book.docx`, `out/book.layout.json` (page numbers, titles, stats). `make_notes.py` writes the list of source-text irregularities (PDF + Word).
* `build.js` prints two self-checks: **word check** (every source token appears exactly once in the PDF – must say `differences 0`) and **hanging indent** (must say `misaligned 0`, `column-top 0`).

## Pipeline
`ingest.py` (docx → runs/footnotes) → `parse_docx.py` (normalise runs, quotes, small citations) → `book.py` (split compilation by its ToC, add the single-article files, dedupe, headings, siman dividers, `book.doc.json`)
→ `tint_ornaments.py` + `compose_ornaments.py` (grey ornaments, header rule, frames) → `build.js` + `engine.js` + `template.html` (layout + PDF) → `make_docx.py` (Word).

## Fonts (config.json)
* `fonts`: role → CSS family: `body` (text, footnotes), `lead` (bold first word, sub-headings, footnote title), `display` (article titles, dividers, ToC).
* A font **installed on the computer** can be used by just writing its family name in `fonts` (no files needed when this runs locally). Otherwise add the files to `assets/fonts/` and list them in `fontFaces` (see the existing entries; give regular + bold).
* `wordFonts`: the names Word should use (must be installed on the Word machine; Windows built-ins `FrankRuehl`, `David` today).
* After changing fonts run `python run_all.py` and read the numbers: page count and `loose lines` change with font metrics.

## Design decisions (cumulative, from the client)
* B5 176×250 mm, margins 19.4 mm, two columns; body 12/17 pt; columns aligned top and bottom (vertical justification by stretching paragraph gaps, then leading; never ragged).
* Every paragraph: first word bold in the *lead* font; **only line 2 is indented, exactly to where the regular text of line 1 starts** (line 2 may never open a column – no indent artefacts at column tops); last line centred; one blank line between paragraphs.
* Footnotes: Hebrew letters, continuous per article, one per line, full width under a plain double-line separator with the title "הערות וציונים".
* Article title inside the framed ornament; **no** siman label per article – instead a divider page wherever the siman changes (also in the ToC). Ornaments grey with slight transparency; end-of-article ornament flipped down; mirrored running header with an ornament rule; Hebrew page numbers; ToC; cover (placeholder until the client sends the cover file).
* Authors: add שליט״א to names; "סימן ד בקצרה" = מכלל האברכים. Articles of the flyer scan are not included.
* Word: styles with Hebrew names, separate character style for the bold first word, frame picture behind the text. Word cannot express "only line 2 indented" / centred last line (known limit).
* Text fixes applied automatically: spaces before , . ; : removed (ellipsis untouched). Unbalanced brackets are **not** corrected (listed in `source-notes`).

## Open items
* Cover page: the client will send a file with the cover text.
* "דין כוונת הברכות": the compilation version (= also `f01`) is used; `f04` is a divergent, earlier-style draft of the names part (see chat/notes). 
* More articles may be added later: add a source file (`EXTRA` in `book.py`).
