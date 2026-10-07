"""Embossed-gold versions of the organisation's black ornament masters (typeset/assets/ornaments/_black)."""
import os

import numpy as np
from PIL import Image

import art
from art import emboss, GOLD, IVORY

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'typeset', 'assets', 'ornaments', '_black'))
if not os.path.isdir(SRC):                                   # vendored copy
    SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'ornaments'))


def gold(name, w_mm, ppm=10, flip_x=False, flip_y=False, rot=0, colors=GOLD, pad_mm=1.6, **kw):
    """returns an RGBA uint8 array: the ornament `name`, w_mm wide, as relief metal (with shadow)"""
    a = Image.open(os.path.join(SRC, name)).convert('RGBA').split()[3]
    w = int(w_mm * ppm)                                   # w_mm = length of the horizontal master (before rotation)
    a = a.resize((w, int(a.height * w / a.width)), Image.LANCZOS)
    if flip_x:
        a = a.transpose(Image.FLIP_LEFT_RIGHT)
    if flip_y:
        a = a.transpose(Image.FLIP_TOP_BOTTOM)
    if rot:
        a = a.transpose({90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}[rot])
    m = np.pad(np.asarray(a, float) / 255, int(pad_mm * ppm))
    kw.setdefault('height_mm', .8)
    return emboss(m, ppm, colors=colors, **kw)


def size_mm(rgba, ppm=10):
    return rgba.shape[1] / ppm, rgba.shape[0] / ppm
