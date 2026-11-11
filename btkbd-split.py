#!/opt/python3/bin/python3
"""Split a combined keyboard+pointer input device into two devices and give the keyboard a layout (run ON THE PHONE as root):
    btkbd-split.py [--layout cz|us|none] [--pointer rel|abs] [--speed N] [--scroll-step N] [--scroll-invert] [NAME-PART]        (NAME-PART default "Keyboard")
    Middle button + TrackPoint scrolls (--scroll-step counts per wheel notch, default 5).
    --pointer abs: the pointer device is absolute and touchscreen-like (position integrated here, --speed pixels per count, default 1.5); see DOC/mouse.md

Why: the X server of Maemo 5 (1.6.99) does not pass the modifier state (Shift, Ctrl, Caps Lock) of a device that is both keyboard and pointer (ThinkPad
Bluetooth keyboards with a TrackPoint) to the core keyboard, so applications never see Shift. A pure keyboard device works like the built-in keypad.
The script takes the device exclusively (EVIOCGRAB) and passes its events on to two uinput devices: "<name> (keys)" gets the keys, "<name> (pointer)"
the pointer buttons and relative axes. The keys are translated on the way (btkbd_layout.py: Czech QWERTZ, AltGr characters, Caps Lock, right Shift/Ctrl).
It runs until the device disappears (the keyboard disconnects); bt-keyboard.sh starts it again after reconnecting.
"""
import fcntl, os, select, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btkbd_layout as L

EV_SYN, EV_KEY, EV_REL, EV_ABS, EV_MSC, EV_REP = 0, 1, 2, 3, 4, 0x14
REL_X, REL_Y, REL_HWHEEL, REL_WHEEL, ABS_X, ABS_Y = 0, 1, 6, 8, 0, 1
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT, UI_SET_ABSBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x40045566, 0x40045567, 0x5501, 0x5502
SCREEN_W, SCREEN_H = 800, 480
ABS_PRESSURE, BTN_TOUCH, BTN_LEFT, BTN_RIGHT, BTN_MIDDLE = 0x18, 0x14a, 0x110, 0x111, 0x112
RAW_MAX = 4095
# The absolute pointer pretends to be a touchscreen (HAL then gives it the calibration of the touchscreen and the X evdev driver treats it as one).
# Mapping measured on the phone on 2026-11-11 (raw value -> pixel): x = 0.2195*raw - 39.5, y = 516.5 - 0.1445*raw.
RAW_X = lambda px: (px + 39.5) / 0.2195
RAW_Y = lambda py: (516.5 - py) / 0.1445
EVIOCGRAB = 0x40044590


def find_device(part):
    """(name, /dev/input/eventN) of the first input device whose name contains `part` and that has both keys and relative axes... or just keys."""
    name = handlers = None
    for line in open("/proc/bus/input/devices"):
        if line.startswith("N: Name="):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("H: Handlers=") and name and part.lower() in name.lower() and "(keys)" not in name and "(pointer)" not in name:
            for h in line.split():
                if h.startswith("event"):
                    return name, "/dev/input/" + h
    return None, None


def evbits(fd, ev, nbytes=96):
    buf = bytearray(nbytes)
    fcntl.ioctl(fd, (2 << 30) | (nbytes << 16) | (0x45 << 8) | (0x20 + ev), buf)
    return [i * 8 + b for i in range(nbytes) for b in range(8) if buf[i] >> b & 1]


def make_uinput(name, evs, keys, rels, abs_max=None):
    fd = os.open("/dev/input/uinput", os.O_WRONLY)
    for ev in evs:
        fcntl.ioctl(fd, UI_SET_EVBIT, ev)
    for k in keys:
        fcntl.ioctl(fd, UI_SET_KEYBIT, k)
    for r in rels:
        fcntl.ioctl(fd, UI_SET_RELBIT, r)
    absmax = [0] * 64
    for code, mx in (abs_max or {}).items():
        fcntl.ioctl(fd, UI_SET_ABSBIT, code)
        absmax[code] = mx
    # struct uinput_user_dev: name[80], input_id (bustype, vendor, product, version), ff_effects_max, absmax/absmin/absfuzz/absflat[64]
    os.write(fd, struct.pack("80sHHHHi" + "i" * 256, name.encode()[:79], 5, 1, 1, 1, 0, *(absmax + [0] * 192)))
    fcntl.ioctl(fd, UI_DEV_CREATE)
    return fd


def is_key_code(c):          # keyboard keys; BTN_MOUSE.. (0x110-0x11f) and the other BTN_ codes (0x100-0x15f) belong to the pointer
    return c < 0x100 or c >= 0x160


class Layout:
    """Key translation: feed() takes one input key event and returns the list of (code, value) events for the new keyboard device."""

    def __init__(self, name):
        self.lay = L.LAYOUTS.get(name) if name != "none" else None
        self.spare = L.spare_codes(name) if self.lay else {}
        self.shift = self.altgr = self.ctrl = 0                # physical modifiers held (counts)
        self.caps = False
        self.held = {}                                          # input code -> output codes, so that the release matches the press

    def out_codes(self):
        return {c for outs in self.held.values() for c in outs}

    def feed(self, code, value):
        if value == 2:                                          # kernel auto-repeat: the X server repeats keys itself
            return []
        if self.lay is None:
            return [(code, value)]
        if code == L.KEY_CAPSLOCK:                              # Caps Lock is handled here (the letters of the phone map ignore the X lock)
            if value == 1:
                self.caps = not self.caps
            return []
        if value == 0:
            return [(c, 0) for c in reversed(self.held.pop(code, [code]))]
        # press
        if code == L.KEY_RIGHTSHIFT: code_out = L.KEY_LEFTSHIFT
        elif code == L.KEY_RIGHTCTRL: code_out = L.KEY_LEFTCTRL
        else: code_out = code
        if code_out == L.KEY_LEFTSHIFT: self.shift += 1
        if code_out == L.KEY_LEFTCTRL: self.ctrl += 1
        if code == L.KEY_RIGHTALT: self.altgr += 1
        lay = self.lay
        key = code
        if lay["swap_yz"] and key in (21, 44):
            key = 65 - key                                      # Y (21) <-> Z (44)
        ctrl = self.ctrl > 0
        if not ctrl and self.altgr and (code, "ag") in self.spare:
            outs = [self.spare[(code, "ag")]]
        elif not ctrl and (code, "pl") in self.spare:
            outs = [self.spare[(code, "pl")]]
        elif key in L.LETTERS and not ctrl and self.caps:
            # Caps Lock flips the case: wrap the letter in a Shift press (or a Shift release when Shift is held)
            if self.shift > 0:
                self.held[code] = [key]
                return [(L.KEY_LEFTSHIFT, 0), (key, 1), (L.KEY_LEFTSHIFT, 1)]
            self.held[code] = [key]
            return [(L.KEY_LEFTSHIFT, 1), (key, 1), (L.KEY_LEFTSHIFT, 0)]
        else:
            outs = [code_out if code_out != code else key]
        self.held[code] = outs
        return [(c, 1) for c in outs]

    def modifier_release(self, code):
        if code in (L.KEY_LEFTSHIFT, L.KEY_RIGHTSHIFT): self.shift = max(0, self.shift - 1)
        if code in (L.KEY_LEFTCTRL, L.KEY_RIGHTCTRL): self.ctrl = max(0, self.ctrl - 1)
        if code == L.KEY_RIGHTALT: self.altgr = max(0, self.altgr - 1)


def emit(fd, typ, code, value):
    os.write(fd, struct.pack("<IIHHi", 0, 0, typ, code, value))


class AbsPointer:
    """Turns the relative motion of the TrackPoint into an absolute position in screen pixels and sends it as the coordinates of a touchscreen-like
    device. Why: the X server of Maemo 5 mishandles relative devices (the pointer ends in a corner and stays there, see DOC/mouse.md), but follows
    absolute coordinates of a touchscreen-like device, even without BTN_TOUCH. `speed` is pixels per count."""

    def __init__(self, fd, speed):
        self.fd, self.speed = fd, speed
        self.x, self.y = SCREEN_W / 2.0, SCREEN_H / 2.0
        self.dx = self.dy = 0
        self.send()

    def rel(self, code, value):
        if code == REL_X:
            self.dx += value
        elif code == REL_Y:
            self.dy += value

    def send(self):
        raw_x = min(RAW_MAX, max(0, int(RAW_X(self.x))))
        raw_y = min(RAW_MAX, max(0, int(RAW_Y(self.y))))
        emit(self.fd, EV_ABS, ABS_PRESSURE, 200)
        emit(self.fd, EV_ABS, ABS_X, raw_x)
        emit(self.fd, EV_ABS, ABS_Y, raw_y)
        emit(self.fd, EV_SYN, 0, 0)

    def flush(self):
        if self.dx or self.dy:
            self.x = min(SCREEN_W - 1.0, max(0.0, self.x + self.dx * self.speed))
            self.y = min(SCREEN_H - 1.0, max(0.0, self.y + self.dy * self.speed))
            self.dx = self.dy = 0
            self.send()


class ScrollEmu:
    """Scrolling with the middle button, as on ThinkPads: while the middle button is held, TrackPoint motion becomes wheel events (up/down
    and left/right) instead of cursor motion. The keyboard sends only plain motion plus the held button, and the X server of Maemo 5 has no wheel
    emulation of its own. A middle click without any motion is passed on as a click. `step` = counts per wheel notch."""

    def __init__(self, fd, step, invert=False):
        self.fd, self.step, self.invert = fd, step, invert
        self.mid = self.moved = False
        self.ax = self.ay = 0

    def event(self, ev, typ, code, value):
        """Handles one event of the pointer; returns True when it was consumed."""
        if typ == EV_KEY and code == BTN_MIDDLE:
            if value == 1:
                self.mid, self.moved, self.ax, self.ay = True, False, 0, 0
            elif value == 0:
                self.mid = False
                if not self.moved:               # a plain middle click
                    emit(self.fd, EV_KEY, BTN_MIDDLE, 1); emit(self.fd, EV_SYN, 0, 0)
                    emit(self.fd, EV_KEY, BTN_MIDDLE, 0); emit(self.fd, EV_SYN, 0, 0)
            return True                          # press, repeat and release are handled here
        if self.mid and typ == EV_REL and code in (REL_X, REL_Y):
            self.moved = True
            if code == REL_X:
                self.ax += value
            else:
                self.ay += value
            while abs(self.ay) >= self.step:
                emit(self.fd, EV_REL, REL_WHEEL, (-1 if self.ay > 0 else 1) * (-1 if self.invert else 1)); emit(self.fd, EV_SYN, 0, 0)
                self.ay -= self.step if self.ay > 0 else -self.step
            while abs(self.ax) >= self.step:
                emit(self.fd, EV_REL, REL_HWHEEL, (1 if self.ax > 0 else -1) * (-1 if self.invert else 1)); emit(self.fd, EV_SYN, 0, 0)
                self.ax -= self.step if self.ax > 0 else -self.step
            return True
        return False


class PointerLog:
    """--debug: once per second one line with the pointer events that came from the keyboard (counts, largest step, buttons), in /tmp/btkbd-pointer.log."""

    def __init__(self):
        self.f = open("/tmp/btkbd-pointer.log", "w")
        self.t = time.time()
        self.n = self.sx = self.sy = self.mx = self.my = 0
        self.btn = []

    def feed(self, typ, code, value):
        if typ == EV_REL and code in (REL_X, REL_Y):
            self.n += 1
            if code == REL_X:
                self.sx += value; self.mx = max(self.mx, abs(value))
            else:
                self.sy += value; self.my = max(self.my, abs(value))
        elif typ == EV_REL:
            self.btn.append("rel%d=%d" % (code, value))
        elif typ == EV_KEY and not is_key_code(code):
            self.btn.append("btn%x=%d" % (code, value))
        if time.time() - self.t >= 1 and (self.n or self.btn):
            self.f.write("%.0f events=%d sum=(%d,%d) max=(%d,%d) %s\n" % (time.time(), self.n, self.sx, self.sy, self.mx, self.my, " ".join(self.btn)))
            self.f.flush()
            self.t = time.time(); self.n = self.sx = self.sy = self.mx = self.my = 0; self.btn = []


def main():
    args = sys.argv[1:]
    pointer_mode, speed = "rel", 1.5
    dbg = None
    if "--debug" in args:
        args.remove("--debug"); dbg = PointerLog()
    if "--pointer" in args:
        i = args.index("--pointer"); pointer_mode = args[i + 1]; del args[i:i + 2]
    scroll_step, scroll_invert = 5, False
    if "--scroll-invert" in args:
        args.remove("--scroll-invert"); scroll_invert = True
    if "--scroll-step" in args:
        i = args.index("--scroll-step"); scroll_step = int(args[i + 1]); del args[i:i + 2]
    if "--speed" in args:
        i = args.index("--speed"); speed = float(args[i + 1]); del args[i:i + 2]
    layout = "cz"
    if "--layout" in args:
        i = args.index("--layout"); layout = args[i + 1]; del args[i:i + 2]
    part = args[0] if args else "Keyboard"
    name, path = find_device(part)
    if not path:
        sys.exit("no input device with %r in its name" % part)
    src = os.open(path, os.O_RDWR)
    keys_all = evbits(src, EV_KEY)
    try:
        rels = evbits(src, EV_REL, 2)
    except OSError:
        rels = []
    keys = [k for k in keys_all if is_key_code(k)]
    lay = Layout(layout)
    for extra in list(lay.spare.values()) + [L.KEY_LEFTSHIFT, L.KEY_LEFTCTRL]:
        if extra not in keys:
            keys.append(extra)
    btns = [k for k in keys_all if not is_key_code(k)]
    print("%s: %s, %d keys, %d buttons, %d relative axes" % (name, path, len(keys), len(btns), len(rels)), flush=True)
    kfd = make_uinput(name + " (keys)", [EV_KEY, EV_SYN, EV_MSC], keys, [])
    absptr = None
    scroll = None
    if not (btns or rels):
        pfd = None
    elif pointer_mode == "abs":
        # absolute, touchscreen-like pointer: motion is integrated into a position; the wheel is dropped (no relative axes in this device)
        pfd = make_uinput(name + " (pointer)", [EV_KEY, EV_ABS, EV_SYN], sorted(set(btns) | {BTN_LEFT, BTN_RIGHT, BTN_MIDDLE, BTN_TOUCH}), [],
                          {ABS_X: RAW_MAX, ABS_Y: RAW_MAX, ABS_PRESSURE: 255})
        absptr = AbsPointer(pfd, speed)
    else:
        pfd = make_uinput(name + " (pointer)", [EV_KEY, EV_REL, EV_SYN], btns, sorted(set(rels) | {REL_X, REL_Y, REL_HWHEEL, REL_WHEEL}))
        scroll = ScrollEmu(pfd, scroll_step, scroll_invert)
    fcntl.ioctl(src, EVIOCGRAB, 1)
    print("running: the original device is grabbed, the two new devices are created", flush=True)
    try:
        while True:
            select.select([src], [], [])
            try:
                data = os.read(src, 16 * 64)
            except OSError:
                break                                              # the device is gone
            if not data:
                break
            for i in range(0, len(data) - 15, 16):
                ev = data[i:i + 16]
                typ, code, value = struct.unpack_from("<HHi", ev, 8)
                if dbg is not None:
                    dbg.feed(typ, code, value)
                if typ == EV_KEY and is_key_code(code):
                    if value == 0:
                        lay.modifier_release(code)
                    for c, v in lay.feed(code, value):
                        emit(kfd, EV_KEY, c, v)
                        emit(kfd, EV_SYN, 0, 0)               # one event and a SYN per write: the uinput of kernel 2.6.28 takes exactly one event per write()
                elif absptr is not None:
                    if typ == EV_REL:
                        absptr.rel(code, value)
                    elif typ == EV_KEY:
                        # The X evdev driver takes only BTN_TOUCH as a click on a touchscreen-like device (measured: BTN_LEFT, BTN_RIGHT and
                        # BTN_MIDDLE are ignored), so the left button becomes BTN_TOUCH; the other buttons have no equivalent here.
                        absptr.flush()
                        if code == BTN_LEFT:
                            emit(pfd, EV_KEY, BTN_TOUCH, value)
                            emit(pfd, EV_SYN, 0, 0)
                    elif typ == EV_SYN:
                        absptr.flush()
                elif typ == EV_KEY or typ == EV_REL:
                    if pfd is not None and not (scroll is not None and scroll.event(ev, typ, code, value)):
                        os.write(pfd, ev)
                elif typ == EV_SYN and pfd is not None:
                    os.write(pfd, ev)
    finally:
        for fd in (kfd, pfd):
            if fd is not None:
                try: fcntl.ioctl(fd, UI_DEV_DESTROY)
                except OSError: pass
        print("device gone, stopped", flush=True)


if __name__ == "__main__":
    main()
