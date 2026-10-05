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
* `build_docx.py` – styles: Rithcha Siman / Marker / Question / Note / Source.  The page header (title + "■ סימן X ■") uses a STYLEREF field on style "Rithcha Siman".
* Fonts named in the file: Times New Roman (body), Narkisim (headings/letters), Gisha (notes).
