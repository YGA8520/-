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
* `build.js` prints three self-checks: **word check** (every source token appears exactly once in the PDF – must say `differences 0`), **hanging indent** (must say `misaligned 0`, `column-top 0`) and **vertical overflow** (must say `0`). A full build of the ~600-page booklet takes about 4 minutes.

## Pipeline
`ingest.py` (docx → runs/footnotes) → `parse_docx.py` (normalise runs, quotes, small citations) → `book.py` (split compilation by its ToC, add the single-article files, dedupe, headings, siman dividers, `book.doc.json`)
→ `tint_ornaments.py` + `compose_ornaments.py` (grey ornaments, header rule, frames) → `build.js` + `engine.js` + `template.html` (layout + PDF) → `make_docx.py` (Word).

## Additional חבורות (folder "חבורות")
`new_articles.py` holds the manifest of every article taken from the second batch (title, author, siman / se'if, number of header lines to drop, source file);
`book.py` merges them with the first batch and orders everything by siman, then se'if (existing articles first). Folder: `$HAVUROT_DIR` (default `./src/חבורות`).
`make_report.py` writes the integration report (what was added, what was skipped as a duplicate, which version was chosen, what was assumed); `compile_split.py` splits an old-style compilation ("חוברת מתוקנת").
Duplicates are decided on the text (6-word shingles), never by file name. `python new_articles.py` lists every new article with its heading count.

## Fonts (config.json)
Current set (all can be changed in `config.json`; the previous set is in `config.frank-david.json`):
`body` Frank Ruhl Libre · `lead` Keter YG (bold first word, sub-headings) · `display` Stam Ashkenaz CLM (calligraphic titles; Frank Ruhl Libre supplies the geresh/gershayim it lacks via `unicode-range`) ·
`notes` Frank Ruhl Libre weight 300 · `author` Shofar. Word needs these installed: Frank Ruhl Libre, Frank Ruhl Libre Light, Keter YG, Stam Ashkenaz CLM, Shofar (Culmus fonts are GPL with the font-embedding exception, see `assets/fonts/CULMUS-LICENSE.txt`).
`fontWeights` sets the weight of the display / lead roles (400 for a single-weight calligraphic face).
* `fonts`: role → CSS family: `body` (running text), `lead` (bold first word, sub-headings, footnote title, page numbers), `display` (article titles, dividers, ToC, book name in the header), `notes` (footnote text; set `type.foot.weight` e.g. 300 for a light cut), `author` (author name under the title and in the ToC). `notes`/`author` default to `body`/`lead`.
* A font **installed on the computer** can be used by just writing its family name in `fonts` (no files needed when this runs locally). Otherwise add the files to `assets/fonts/` and list them in `fontFaces` (see the existing entries; give regular + bold).
* `wordFonts`: the names Word should use for the same five roles (must be installed on the Word machine; Windows built-ins `FrankRuehl`, `David` today).
* Do **not** commit font files that are not under a free licence (Windows fonts such as David/Miriam/Narkisim are Microsoft's): use them by installed family name only; the PDF embeds the glyphs it needs.
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
* Cover page: the client will send a file with the cover text (placeholder cover meanwhile).
* "דין כוונת הברכות": the compilation version (= also `f01`) is used; `f04` is a divergent, earlier-style draft of the names part (see chat/notes). 
* More articles may be added later: add a source file (`EXTRA` in `book.py`).
