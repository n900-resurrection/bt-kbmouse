# bt-kbmouse

Makes a Bluetooth keyboard with a TrackPoint (ThinkPad) usable on the Nokia N900 (Maemo 5): Shift, Caps Lock and AltGr work, the Czech or US layout,
a visible mouse pointer with adjustable speed, scrolling with the middle button and clicks. Python 3 + [hildonlite](https://github.com/n900-resurrection/hildonlite).

- **Service** `bt-kbmouse-daemon` (root, upstart job `/etc/event.d/bt-kbmouse`, starts with the X server): watches the input devices and, when the keyboard connects,
  starts the splitter `btkbd-split.py` and sets the key map, the pointer speed and the cursor in the X session of the user. Starts everything again after a reconnect.
- **Settings** `bt-kbmouse` (GUI): layout, pointer speed, scrolling speed and direction, pointer visibility and size. Writes `/home/user/.bt-kbmouse.conf`;
  the service applies a change within a few seconds. The service writes its state to `/tmp/bt-kbmouse.status`.
- **Tools** (also usable by hand): `btkbd-split.py` (splits a combined keyboard + pointer device through uinput, translates the keys, emulates scrolling),
  `btkbd_layout.py` (layouts), `btkbd-keymap.py` (adds the extra keys to the X key map), `btkbd-cursor.py` (shows or hides the pointer), `btkbd-accel.py` (X device properties).

The reasons behind the design (the X server of Maemo 5 mishandles relative devices and ignores most mouse buttons; the pointer is hidden by a transparent cursor theme) are in
`DOC/bluetooth-keyboard.md` and `DOC/mouse.md` of the [N900 repository](https://github.com/elPytel/N900). Pairing: `scripts/bt-keyboard/bt-keyboard.sh pair`.

Needs the patched evdev driver `xserver-xorg-input-evdev-mouse` (extras-testing; without it the buttons of a mouse do not work) and `python3-hildonlite` >= 0.4.0.

## Build

Inside the N900 repository (uses `mk/app.mk`): `make -C apps/bt-kbmouse deb`, install with `make -C apps/bt-kbmouse install`. `make-icon.sh` draws the icons.

## License

MIT, see [LICENSE](LICENSE).
