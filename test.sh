TEST_NAME=bt-kbmouse
need_pkg bt-kbmouse
ok in-path sh -c 'command -v bt-kbmouse'
ok upstart-job sh -c 'test -s /etc/event.d/bt-kbmouse'
ok patched-evdev sh -c 'dpkg -l xserver-xorg-input-evdev-mouse | grep -q "^ii"'
ok hildonlite-new sh -c '/opt/python3/bin/python3 -c "import hildonlite; hildonlite.Scale, hildonlite.CheckButton"'
ok config-module sh -c 'cd /opt/bt-kbmouse && /opt/python3/bin/python3 -c "import bt_kbmouse_conf as c; d=c.load(\"/nonexistent\"); assert c.decel(d)==3.0 and c.scroll_step(d)==5"'
ok service-running sh -c 'initctl status bt-kbmouse | grep -q "(start) running"'
ok status-file sh -c 'grep -q "^state=" /tmp/bt-kbmouse.status'
# The behaviour with a keyboard (pointer, scrolling, layout) was checked by hand; see DOC/bluetooth-keyboard.md and DOC/mouse.md.
summary
