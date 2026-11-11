#!/bin/bash
# Draw the icons of bt-kbmouse with ImageMagick: icons/48.png and 64.png (a keyboard with a pointer arrow on a dark rounded square).
# The PNGs are committed; run this only to change the design.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p icons
W='#f2f2f2'
keys=()
for r in 0 1 2; do for c in 0 1 2 3 4 5 6; do keys+=(-draw "roundrectangle $((40+c*27)),$((82+r*22)) $((58+c*27)),$((96+r*22)) 3,3"); done; done
convert -size 256x256 xc:none -fill '#26323f' -draw 'roundrectangle 8,8 247,247 44,44' \
  -fill "$W" -draw 'roundrectangle 26,70 230,170 14,14' \
  -fill '#26323f' "${keys[@]}" \
  -fill '#3d9bd9' -draw 'roundrectangle 70,150 186,162 4,4' \
  -fill "$W" -stroke '#26323f' -strokewidth 5 -draw 'polygon 160,130 160,222 183,200 200,236 216,228 199,193 232,193' icons/256.png
for s in 64 48; do convert icons/256.png -resize ${s}x${s} icons/$s.png; done
rm icons/256.png
