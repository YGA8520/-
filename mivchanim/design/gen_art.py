"""Builds the raster artwork of the booklet (see refart.py for how the reference cover is re-created).

    python3 design/gen_art.py [cover|frame|small|all]

Outputs in build/art:
  ref-cover-bg.jpg   cover / part dividers / back cover (title panel, parchment, ornamented side bands)
  ref-frame.jpg      cream page with the corner ornaments (inner title, credits, contents, notes)
  ring.png rule.png sep.png   seal ring, rule with a lozenge, short separator
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refart  # noqa: E402

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('cover', 'all'):
        refart.build_cover_bg()
    if what in ('frame', 'all'):
        refart.build_frame_ref()
    if what in ('small', 'all'):
        refart.build_small_ref()
