#!/usr/bin/env python3
"""Moves the medallion (rings, rules, swashes, flourishes) of the grey inner title page up or down inside its background picture.

The picture is the cover (make_cover.py, palette silver) = the frame and the cloud + the medallion.  make_cover.build(..., no_medallion=True) makes the
same picture without the medallion, so the difference of the two is the medallion alone; it is shifted and added to the picture without it.
usage (module): shifted_background(jpeg_bytes_of_the_page_picture, dy_grid)   dy_grid in the 1408 x 2000 grid of the cover, positive = up.
Needs numpy, scipy, pillow (the files of assets/cover)."""
import io
import os
import tempfile
import numpy as np
from PIL import Image
import make_cover


def shifted_background(jpeg, dy_grid, palette='silver', quality=92):
    full = np.asarray(Image.open(io.BytesIO(jpeg)).convert('RGB')).astype(np.float32)
    scale = full.shape[1] / 1408.0
    with tempfile.TemporaryDirectory() as d:
        path = make_cover.build(palette, os.path.join(d, 'nomed.jpg'), no_medallion=True)
        clean = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    assert clean.shape == full.shape, (clean.shape, full.shape)
    x0, y0, x1, y1 = [int(round(v * scale)) for v in make_cover.MEDALLION_BOX]
    diff = np.zeros_like(full)
    diff[y0:y1, x0:x1] = full[y0:y1, x0:x1] - clean[y0:y1, x0:x1]         # the medallion alone
    dy = int(round(dy_grid * scale))
    moved = np.zeros_like(diff)
    if dy >= 0:
        moved[:diff.shape[0] - dy] = diff[dy:]
    else:
        moved[-dy:] = diff[:diff.shape[0] + dy]
    out = np.clip(clean + moved, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(out, 'RGB').save(buf, 'JPEG', quality=quality, subsampling=0, optimize=True)
    return buf.getvalue()
