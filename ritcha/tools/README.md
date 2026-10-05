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
