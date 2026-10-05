#!/usr/bin/env python3
"""Full pipeline (works on Windows / macOS / Linux):  sources -> content model -> ornaments -> PDF -> Word.

usage:  python run_all.py            (SRC_DIR=<folder with the source .docx files>, default ./src)
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
os.makedirs('out', exist_ok=True)
PY = sys.executable
STEPS = [
    [PY, 'book.py', 'book.doc.json'],
    [PY, 'tint_ornaments.py'],
    [PY, 'compose_ornaments.py'],
    [PY, 'make_cover.py'],
    ['node', 'build.js', 'book.doc.json', os.path.join('out', 'book.pdf')],
    [PY, 'compose_ornaments.py', os.path.join('out', 'book.layout.json')],
    [PY, 'make_docx.py', 'book.doc.json', os.path.join('out', 'book.layout.json'), os.path.join('out', 'book.docx')],
    [PY, 'make_print.py'],
]
for cmd in STEPS:
    print('>>', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)
print('done: out/book.pdf  out/book.docx  out/print/*.pdf (for the printing house)')
