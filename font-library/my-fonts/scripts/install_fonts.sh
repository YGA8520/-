#!/bin/sh
# Make the bundled fonts visible to the system (fontconfig) so LibreOffice / Chromium / Pillow / matplotlib can use them by family name.
# usage: sh install_fonts.sh        (safe to run repeatedly)
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${HOME:-/tmp}/.fonts/my-fonts"
mkdir -p "$DEST"
n=0
find "$HERE/fonts" -type f \( -iname '*.ttf' -o -iname '*.otf' -o -iname '*.ttc' \) | while read -r f; do
  cp -f "$f" "$DEST/"
done
n=$(find "$DEST" -type f | wc -l)
command -v fc-cache >/dev/null 2>&1 && fc-cache -f "$DEST" >/dev/null 2>&1 || echo "fc-cache not found; fonts copied but not indexed"
echo "installed $n font files into $DEST"
