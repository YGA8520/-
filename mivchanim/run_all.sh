#!/usr/bin/env bash
# Rebuild the booklet from src/all-tests.pdf
#   needs: python3 (pymupdf pypdf pillow numpy), poppler-utils, node + playwright with chromium
set -e
cd "$(dirname "$0")"
pip install pymupdf pypdf pillow numpy "python-bidi==0.4.2" --target .deps >/dev/null 2>&1 || true
python3 tools/extract.py        # source PDF -> work/lines.json  (logical text, geometry, styles)
python3 tools/parse_units.py    # + design/manifest.py -> work/units.json
python3 build.py                # -> output/mivchanei-hasimanim.pdf (+ output/front-pages)
python3 tools/verify.py         # fidelity: every source word is in the booklet
python3 make_report.py          # -> output/דוח-עריכה.pdf
