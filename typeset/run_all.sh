#!/bin/sh
# full pipeline:  sources -> content model -> composed ornaments -> PDF -> Word
# usage: ./run_all.sh   (SRC_DIR=/path/to/docx/files)
set -e
cd "$(dirname "$0")"
mkdir -p out
python3 book.py book.doc.json
python3 tint_ornaments.py
python3 compose_ornaments.py
node build.js book.doc.json out/book.pdf
python3 compose_ornaments.py out/book.layout.json
python3 make_docx.py book.doc.json out/book.layout.json out/book.docx
