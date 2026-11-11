#!/opt/python3/bin/python3
"""Add the spare key codes of a layout (btkbd_layout.py) to the X key map of the phone (run ON THE PHONE as user, inside the Hildon session):
    btkbd-keymap.py [--layout cz|us] [--device NAME-PART]
Only keys that the built-in keypad does not use are added (key codes 191 ... of the layout); everything else stays as it is. Key repeat is switched on
for the core keyboard and the external one (hold Backspace). Nothing is stored on disk: run it again after X restarts."""
import argparse, ctypes, os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btkbd_layout as L


def x_device(part):
    x = ctypes.CDLL("libX11.so.6")
    xi = ctypes.CDLL("libXi.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    d = x.XOpenDisplay(None)
    if not d:
        raise SystemExit("no X display (run as user in the Hildon session: DISPLAY=:0)")
    xi.XListInputDevices.restype = ctypes.c_void_p
    n = ctypes.c_int()
    lst = xi.XListInputDevices(ctypes.c_void_p(d), ctypes.byref(n))
    found = []
    for i in range(n.value):
        id_, _t, name, _nc, use, _c = struct.unpack("<IIIiiI", ctypes.string_at(lst + 24 * i, 24))
        name = ctypes.string_at(name).decode("utf-8", "replace")
        if use == 3 and "omap_twl4030keypad" not in name and part.lower() in name.lower():
            found.append((id_, name))
    return d, x, found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--layout", choices=sorted(L.LAYOUTS), default="cz")
    ap.add_argument("--device", default="(keys)", help="part of the name of the external keyboard device (default: the (keys) device made by btkbd-split.py)")
    a = ap.parse_args()
    d, x, found = x_device(a.device)
    if not found:
        raise SystemExit("no keyboard device with %r in its name (is btkbd-split.py running?)" % a.device)
    dev, name = found[0]
    print("keyboard: %s (X device %d), layout %s" % (name, dev, a.layout))
    env = dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":0"))
    subprocess.run(["xkbcomp", "-i", str(dev), env["DISPLAY"], "/tmp/btkbd-map.xkb"], check=True, env=env, stderr=subprocess.DEVNULL)
    text = open("/tmp/btkbd-map.xkb").read()
    text = text.replace("LockControls(controls=)", "NoAction()")      # the xkbcomp of the phone writes some controls without a name and cannot read its own dump
    names = {int(n): k for k, n in re.findall(r"<([A-Za-z0-9+-]+)>\s*=\s*(\d+);", text.split("xkb_types")[0])}
    add = []
    for lin, (typ, syms) in L.spare_symbols(a.layout).items():
        key = names.get(lin + 8)
        if key is None:
            print("warning: X key code %d has no name in the key map, skipped" % (lin + 8))
            continue
        text = re.sub(r"\n[ \t]*key\s+<%s>\s*\{.*?\};" % re.escape(key), "", text, flags=re.S)
        add.append('    key <%s> { type="%s", symbols[Group1]=[ %s ] };' % (key, typ, ", ".join(syms)))
    m = re.search(r'xkb_symbols\s+"[^"]*"\s*\{', text)
    text = text[:m.end()] + "\n" + "\n".join(add) + "\n" + text[m.end():]
    open("/tmp/btkbd-map-new.xkb", "w").write(text)
    r = subprocess.run(["xkbcomp", "-i", str(dev), "/tmp/btkbd-map-new.xkb", env["DISPLAY"]], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("xkbcomp failed:\n" + r.stderr[-1500:])
    # key repeat: XKB controls of the device and of the core keyboard (the X server repeats the keys of the core one), 400 ms delay, 25 repeats a second
    x.XkbSetAutoRepeatRate.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    x.XkbChangeEnabledControls.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    for target in (dev, 0x100):
        x.XkbChangeEnabledControls(ctypes.c_void_p(d), target, 1, 1)
        x.XkbSetAutoRepeatRate(ctypes.c_void_p(d), target, 400, 40)
    x.XFlush(ctypes.c_void_p(d))
    os.remove("/tmp/btkbd-map.xkb"); os.remove("/tmp/btkbd-map-new.xkb")
    print("done: %d spare keys added" % len(add))


if __name__ == "__main__":
    main()
