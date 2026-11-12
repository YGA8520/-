#!/usr/bin/env python3
"""Make repo-sized copies of Yanky's graphics (D:\\גרפיקה) for graphics-library/.

usage: python3 mirror.py SRC_ROOT DEST_ROOT [folder ...]
  SRC_ROOT  - local copy of D:\\גרפיקה (e.g. /mnt/user-data/uploads/גרפיקה)
  DEST_ROOT - graphics-library/ in the repo
  folder    - top-level folders to mirror (default: MIRRORED below)

Rules: long side capped at 3508px (A4 @300dpi). Photos -> JPG q85.
Anything with transparency -> PNG. BMP/GIF -> PNG. PSD, fonts, Office files are skipped
(the originals stay on the PC). Existing up-to-date copies are not rebuilt.
Writes DEST_ROOT/manifest.json (repo path -> source path, size, pixels).
"""
import sys, os, json
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

MIRRORED = ['מסגרות', 'תמונת מסגרת 1', 'רקעים מלכות', 'רקעים וכדומה', 'רקעים 2',
            'אלמנטים פונטייפ', 'אלמנטים', 'וילונות', 'איורים', 'רקעי פורמייקה ועץ']
IMG = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff')
MAX = 3508

def has_alpha(im):
    if im.mode in ('RGBA', 'LA'):
        return im.getchannel('A').getextrema()[0] < 255
    return im.mode == 'P' and 'transparency' in im.info

def convert(src, dst_dir):
    stem, ext = os.path.splitext(os.path.basename(src))
    ext = ext.lower()
    im = Image.open(src)
    im.load()
    alpha = has_alpha(im)
    as_png = alpha or ext in ('.png', '.gif', '.bmp')
    im = im.convert('RGBA' if as_png and alpha else 'RGB')
    if max(im.size) > MAX:
        im.thumbnail((MAX, MAX), Image.LANCZOS)
    out = os.path.join(dst_dir, stem + ('.png' if as_png else '.jpg'))
    if as_png:
        im.save(out, optimize=True)
    else:
        im.save(out, quality=85, optimize=True, progressive=True)
    return out, im.size, alpha

def main():
    src_root, dst_root = sys.argv[1], sys.argv[2]
    folders = sys.argv[3:] or MIRRORED
    man_path = os.path.join(dst_root, 'manifest.json')
    manifest = json.load(open(man_path, encoding='utf-8')) if os.path.exists(man_path) else {}
    for folder in folders:
        sd = os.path.join(src_root, folder)
        if not os.path.isdir(sd):
            print('missing', sd); continue
        for root, _, files in os.walk(sd):
            rel = os.path.relpath(root, src_root)
            for f in sorted(files):
                if not f.lower().endswith(IMG):
                    continue
                src = os.path.join(root, f)
                dd = os.path.join(dst_root, rel)
                os.makedirs(dd, exist_ok=True)
                key_src = os.path.join(rel, f).replace('/', '\\')
                prev = [k for k, v in manifest.items() if v['source'] == key_src]
                if prev and os.path.exists(os.path.join(dst_root, prev[0])) and \
                        manifest[prev[0]]['source_bytes'] == os.path.getsize(src):
                    continue
                try:
                    out, size, alpha = convert(src, dd)
                except Exception as e:
                    print('FAIL', src, e); continue
                rp = os.path.relpath(out, dst_root)
                manifest[rp] = {'source': key_src, 'source_bytes': os.path.getsize(src),
                                'px': list(size), 'transparent': alpha, 'bytes': os.path.getsize(out)}
                print(f'{rp}  {size[0]}x{size[1]}  {os.path.getsize(out)//1024}KB')
    json.dump(dict(sorted(manifest.items())), open(man_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
