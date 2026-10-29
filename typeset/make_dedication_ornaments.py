"""Gold ornaments for the dedication page: the grey ornaments of the booklet re-coloured to the champagne gold of the cover frame (the luminance is mapped
dark bronze -> gold -> light champagne, the transparency is kept).   python make_dedication_ornaments.py  ->  assets/dedication/*-gold.png"""
import os
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = {'divider-fleuron': 'ornaments/divider-fleuron.png', 'flourish-wide-1': 'ornaments/flourish-wide-1.png',
       'fleuron-corner': 'ornaments/fleuron-corner.png', 'fleuron-sep': 'cover/fleuron-sep.png', 'line-scroll': 'ornaments/line-scroll.png'}
for name, rel in SRC.items():
    im = Image.open(os.path.join(HERE, 'assets', rel)).convert('RGBA')
    lum = ImageOps.autocontrast(im.convert('L'), cutoff=1)
    gold = ImageOps.colorize(lum, black='#5a4220', mid='#b8913f', white='#f3e3b4', midpoint=110).convert('RGBA')
    gold.putalpha(im.getchannel('A'))
    out = os.path.join(HERE, 'assets', 'dedication', name + '-gold.png')
    gold.save(out)
    print(out, gold.size)
