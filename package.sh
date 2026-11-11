#!/bin/bash
# Package bt-kbmouse as a .deb for Maemo 5: make -C apps/bt-kbmouse deb
# Output: /project/build/deb/bt-kbmouse_<VERSION>-<REV>_armel.deb
# The package installs an upstart job (/etc/event.d/bt-kbmouse): the service starts with the X server.
set -euo pipefail
PROJ=/project
. "$PROJ/scripts/debpack.sh"

PKG=bt-kbmouse
VERSION="${VERSION:-0.1}"
STAGE="$PROJ/build/deb/stage-$PKG"
HERE="$PROJ/apps/bt-kbmouse"

rm -rf "$STAGE"
mkdir -p "$STAGE/opt/$PKG" "$STAGE/usr/bin" "$STAGE/usr/share/applications/hildon" "$STAGE/etc/event.d" "$STAGE/DEBIAN"
for f in bt-kbmouse bt-kbmouse-daemon btkbd-split.py btkbd-keymap.py btkbd-cursor.py btkbd-accel.py; do
    install -m 755 "$HERE/$f" "$STAGE/opt/$PKG/$f"
done
install -m 644 "$HERE/bt_kbmouse_conf.py" "$HERE/btkbd_layout.py" "$STAGE/opt/$PKG/"
install -m 644 "$HERE/bt-kbmouse.upstart" "$STAGE/etc/event.d/bt-kbmouse"
for sz in 48 64; do
    mkdir -p "$STAGE/usr/share/icons/hicolor/${sz}x${sz}/apps"
    install -m 644 "$HERE/icons/$sz.png" "$STAGE/usr/share/icons/hicolor/${sz}x${sz}/apps/$PKG.png"
done
ln -s ../../opt/$PKG/bt-kbmouse "$STAGE/usr/bin/bt-kbmouse"
cat > "$STAGE/usr/share/applications/hildon/$PKG.desktop" <<'EOT'
[Desktop Entry]
Encoding=UTF-8
Version=1.0
Type=Application
Name=Keyboard and mouse
Icon=bt-kbmouse
Exec=/usr/bin/bt-kbmouse
X-Osso-Type=application/x-executable
EOT
cat > "$STAGE/DEBIAN/postinst" <<'EOT'
#!/bin/sh
# Start the service now (a restart if an older one runs); a failure here must not break the installation.
case "$1" in configure)
    initctl stop bt-kbmouse >/dev/null 2>&1 || true
    initctl start bt-kbmouse >/dev/null 2>&1 || true ;;
esac
exit 0
EOT
cat > "$STAGE/DEBIAN/prerm" <<'EOT'
#!/bin/sh
case "$1" in remove|upgrade) initctl stop bt-kbmouse >/dev/null 2>&1 || true ;; esac
exit 0
EOT
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm"

SECTION=user/system
DEPENDS="python3.11, python3-hildonlite (>= 0.4.0), xserver-xorg-input-evdev-mouse"
DISPLAY_NAME="Keyboard and mouse"
SHORT_DESC="Bluetooth keyboard and TrackPoint: layout, pointer, scrolling and settings"
LONG_DESC="Makes a Bluetooth keyboard with a TrackPoint (ThinkPad) usable: Shift, Caps Lock and AltGr, the Czech or US layout, a visible mouse pointer with
adjustable speed, scrolling with the middle button, clicks. A service starts with the X server and takes over the keyboard when it connects; the application
sets the speed, the layout and the pointer. Pair the keyboard first (see DOC/bluetooth-keyboard.md). Needs the patched evdev driver
xserver-xorg-input-evdev-mouse (extras-testing)."
debpack_build
