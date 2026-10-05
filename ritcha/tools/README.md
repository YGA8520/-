# ריתחא דאורייתא – בניית החוברת

Builds the booklet (docx) from the original compilation + the additional files, de-duplicated and sorted by siman.

```
pip install pillow pymupdf python-docx
python3 make_assets.py example.pdf        # (optional) re-cut the graphics from the example PDF into ./assets
python3 make_booklet.py booklet.docx      # merge (merge.py) + write the Word file (build_docx.py)
python3 make_report.py report.docx        # Hebrew report: new questions, removed duplicates, open points
./render.sh booklet.docx out              # LibreOffice -> PDF preview
```

* `model.py` – reads the original compilation (`input_document.xml`).  `newsrc.py` – the questions of the additional files (`newfiles/`), file by file.
* `merge.py` – word-trigram similarity decides what is the same question; the printed-issue wording wins over the raw one (see `SUPERSEDE`).
* `build_docx.py` – styles: Rithcha Siman / Marker / Question / Note / Source.  The page header is one line: [ornament] ריתחא  ⟷  סימן X  ⟷  דאורייתא [ornament]; "סימן X" is a STYLEREF field on style "Rithcha Siman" in the middle cell of a 3-cell table.
  The siman heading text is centred in its frame by the glyph outlines of RimonMF (`fontmetrics.ink_shift_pt` horizontally, `fontmetrics.ink_vcentre` vertically); `measure_heads.py` checks the result on the rendered PDF.
* The deliverable is the PDF only (rendered with LibreOffice from the generated docx).
* Fonts: Tehila (running text), RimonMF (siman headings, question letters, siman in the page header), Gisha / Gisha Bold (askers' names, sources), Times New Roman (page numbers).
  The four supplied .TTF files go into `fonts/` (used for measuring glyphs; not in git).  RimonMF is a legacy symbol-encoded font: its text is written as U+F0E0..F0FA codes in visual order (`fontmetrics.to_rimon`), exactly like Wingdings text.
* Each question letter gets two small generated pictures (the squares) whose height and spacing are computed from the glyph outline of that letter (`marker_images`), so the letter is centred between them.

## Cover, credits page, back cover, B5
The whole booklet is B5 (176 x 250 mm). The text pages are rendered on A4 (`render.sh`, the layout of the example) and scaled to B5 in `assemble_pdf.py` with everything on them (text, borders, header, page number; x 0.838 across, x 0.842 down), so the layout and the page count are unchanged. The cover, the credits page and the back cover are B5 artwork of the previous booklet and are used as they are.

`make_cover_ritcha.py` takes the cover of the previous booklet (`../../output/cover.pdf`, soft palette) and replaces its texts; the background, medallion, "קונטרס" and the logo stay as they were:

* first title line "פלפולא" -> "ריתחא" in EFT Algebra (`fonts/EFT_ALGEBRA_OTS.TTF`, the client's font - git-ignored like the other supplied fonts). The word is as wide as the straight double rule above it: the roof of the ר is stretched (`stretch_resh`: the roof is made longer, the stem and the flick at the left end are not changed);
* the curved text on top (outside the rings): the quotation from the Yaaros Devash, no bullets at the ends, the source in brackets at 0.78 of the size; it has to fit between the swash on the left and the end of the rule on the right (124 degrees), so it is set smaller than the old text (23.7 instead of 40);
* the curved text at the bottom (inside the rings): שאלות • קושיות • נידונים • הלכה למעשה;
* both curved texts are set in Keren Normal (`fonts/KEREN.TTF`, git-ignored; the old cover used the same face; `fonts/KERENB_0.TTF` is the bold, not used) - a legacy font, its Hebrew letters are at the cp1255 positions of the symbol map;
* the two lines under the medallion (Lulav CLM Bold, `typeset/assets/fonts`).

`assemble_pdf.py` puts together cover | credits page (`../../output/credits.jpg`) | the text pages | an empty page | back cover (`../../output/back-cover.pdf`). None of them is numbered; the numbers of the text pages still start with א. Result: 66 pages, the back cover is page 66.

```
python3 make_cover_ritcha.py ../../output/cover.pdf cover_176x250.pdf
./render.sh booklet.docx rb                        # -> rb/booklet.pdf (the 62 text pages, A4)
python3 assemble_pdf.py cover_176x250.pdf ../../output/credits.jpg rb/booklet.pdf ../../output/back-cover.pdf ../ריתחא_דאורייתא_חוברת.pdf ../ריתחא_דאורייתא_עמוד_שער.pdf
```
