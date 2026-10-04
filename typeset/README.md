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
Current set (all can be changed in `config.json`; earlier sets: `config.drogolin.json`, `config.keter-stam.json`, `config.frank-david.json`):
`body` FrankRuehl DP · `lead` Livorna (bold first word and sub-headings; Livorna has only a regular cut, so the engine / Word thicken it) ·
`display` Ashkenazy Regular (article titles, dividers, ToC heading, cover; a single-weight face, so display weight 400) · `toc` HadasaNew (ToC entries, group lines and page numbers) · `notes` Asher (footnotes, their title and letters; size 9.4 / 13.8 pt) · `author` Shofar.
The client's proprietary fonts are **not in git**; `prepare_fonts.py <folder with the original files>` builds what the engine needs from them:
Ashcnz (like Drogolin) is an old cp1255-encoded font (a Unicode copy `AshcnzU-*.ttf` is made), FrankRuehl DP draws U+05F3/U+05F4 empty (copy `FrankRuehlDP-Q-*.otf` maps them onto its own ' and " glyphs), Asher / Livorna are used as is.
(`config.ashcnz.json` keeps the earlier Ashcnz setup. Its composite family "Ashcnz Title" (Ashcnz letters + FrankRuehl DP for everything else) must NOT let the FrankRuehl face cover U+05D0-05EA: when unicode-ranges overlap, the face declared last wins and the titles silently fall back to FrankRuehl. Check with `pdffonts out/book.pdf` (Ashcnz-Normal must be listed) or `DUMP_FONTS=1 node build.js ...`.)
In Word the text uses plain ASCII ' and " instead of ׳ ״ (`wordAsciiQuotes`, not in the footnotes: Asher draws them) and × √ are set in Arial (`wordFallbackChars`) because FrankRuehl DP draws them empty.
Word needs these installed: FrankRuehl DP, Livorna, Ashcnz, Asher, Shofar.
`fontWeights` sets the weight of the display / lead roles. Titles are centred in the frame by the ink of their letters (`inkShiftPx` in `engine.js`), not by the line box of the font.
`header.shift` (mm) raises the running head and its rule, `endOrnament.gap` (lines) sets the space above the end ornament. Free fonts (Culmus Keter YG / Stam Ashkenaz / Shofar, Frank Ruhl Libre) stay in `assets/fonts` (`CULMUS-LICENSE.txt`).

## Design decisions (cumulative, from the client)
* B5 176×250 mm, margins 19.4 mm, two columns; body 12/17 pt; columns aligned top and bottom (vertical justification by stretching paragraph gaps, then leading; never ragged).
* No stray lines: never a single line of a paragraph at the top or foot of a column, and the last (centred) line of a paragraph never holds a single word (`build.js` checks this and must report 0). Page-break rules are in `engine.js` (`allowedBreak`, `paginateArticle`).
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

Order and titles: inside every siman the חבורות are ordered מרדכי פוטש, דוד פוטש, משה זאדה, then everybody else (`LEADERS` / `author_rank` in book.py, which also fixes the printed title of the three: נשיא הכולל הגאון ר׳ … / ראש הכולל הרב ר׳ …). The two opening articles get their own title page "פתיחות". A bold line that is really a sentence of the text (starts with ו / הנה / אמנם …, or 30+ words) is set as an ordinary paragraph, not a sub-heading (`is_sentence_heading`). The table of contents has a running head, siman bands with an ornament, titles broken by the engine so the dotted leader sits on the last line, and an end ornament; in Word the siman title is outline level 1 and the article title level 2 (TOC1 = band, TOC2 = entry).
