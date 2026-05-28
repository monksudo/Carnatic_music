#!/usr/bin/env bash
# Build the static Studio site for Vercel / Pages.
#
# Mirrors the GH Pages workflow logic:
#   studio/studio/web/*      -> _site/
#   studio/studio/library/*  -> _site/library/
# Plus a 30-line health page so the deployment root says something useful.

set -euo pipefail

WEB_DIR="studio/studio/web"
LIB_DIR="studio/studio/library"
OUT="_site"

rm -rf "$OUT"
mkdir -p "$OUT/library/svg"

# All web assets — HTML, CSS, JS, the js/ module dir.
cp -r "$WEB_DIR"/. "$OUT"/

# Library: index.json + every committed SVG.
if [ -f "$LIB_DIR/index.json" ]; then
  cp "$LIB_DIR/index.json" "$OUT/library/index.json"
fi
if [ -d "$LIB_DIR/svg" ]; then
  cp -r "$LIB_DIR/svg/." "$OUT/library/svg/"
fi

# Carnatic music page tagged-along, in case it's useful.
if [ -f index.html ]; then
  cp index.html "$OUT/carnatic.html"
fi

# Don't deploy the dev_serve helper — it's only for local use.
rm -f "$OUT/dev_serve.py"

# Strip stray python caches if any got copied.
find "$OUT" -type d -name "__pycache__" -exec rm -rf {} +
find "$OUT" -type f -name "*.pyc" -delete

echo "built site:"
find "$OUT" -maxdepth 2 -type f | sort
echo "total files: $(find "$OUT" -type f | wc -l)"
