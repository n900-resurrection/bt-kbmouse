#!/bin/bash
# Pure Python: only check the syntax of the scripts.
set -euo pipefail
for f in bt-kbmouse bt-kbmouse-daemon bt_kbmouse_conf.py btkbd-split.py btkbd_layout.py btkbd-keymap.py btkbd-cursor.py btkbd-accel.py; do
    python3 -I -c "import ast,sys; ast.parse(open('/project/apps/bt-kbmouse/$f').read())"
done
echo "bt-kbmouse: syntax ok"
