#!/bin/bash
# usage: render.sh in.docx outdir
cd "$(dirname "$0")"
rm -rf "$2" && mkdir -p "$2"
timeout 280 soffice -env:UserInstallation=file:///tmp/claude-0/lo_profile --headless --convert-to pdf --outdir "$2" "$1" >/dev/null 2>&1
pdfinfo "$2"/*.pdf | grep Pages
