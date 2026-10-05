# ריתחא דאורייתא – עיצוב אוטומטי

Turns a source `.docx` of Torah questions into the "ריתחא דאורייתא" design taken from the example PDF
(page border, logo, title, framed siman headings, lettered markers, page-number badge, end ornament).

```
pip install pillow pymupdf            # pymupdf only needed for make_assets.py
python3 make_assets.py example.pdf    # (optional) re-cut the graphics from the example PDF into ./assets
unzip source.docx word/document.xml -d src && cp src/word/document.xml input_document.xml
python3 build_docx.py out.docx        # writes the formatted Word file
python3 check_text.py out.docx        # word-by-word comparison with the source (nothing may go missing)
./render.sh out.docx render           # LibreOffice -> PDF preview
```

* `model.py` – reads the source and decides what is a siman heading / question / name / source line.
  The rules for this particular source are explicit paragraph ranges (the source mixes several layouts); a different source needs its own ranges.
* `build_docx.py` – writes the Word file (styles: Rithcha Siman / Marker / Question / Note / Source / Caption).
  Fonts named in the file: Times New Roman (body, bold), Narkisim (headings and letters, bold italic), Gisha (notes).
* Letters (א, ב, ג …) are typed text, restarted for every siman.
