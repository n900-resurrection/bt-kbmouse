#!/opt/python3/bin/python3
"""List or set X input device properties on the phone (run ON THE PHONE as user with DISPLAY=:0; X input extension 1.x, libXi 1.2):
    btkbd-accel.py list  NAME-PART                    properties of the device(s) whose name contains NAME-PART
    btkbd-accel.py set   NAME-PART PROPERTY INT...    set an integer property, e.g.  set "(pointer)" "Device Accel Profile" 2
    btkbd-accel.py setf  NAME-PART PROPERTY FLOAT...  set a float property, e.g.  setf "(pointer)" "Device Accel Constant Deceleration" 8
Why: the X server of Maemo 5 moves a relative device far too fast (measured: 6 to 16 pixels per count at 100 to 300 counts/s), so the pointer of a
TrackPoint hits the screen edge at once. "Device Accel Constant Deceleration" divides the motion. See DOC/mouse.md.
"""
import ctypes, sys

V, C = ctypes.c_void_p, ctypes.c_ulong
x = ctypes.CDLL("libX11.so.6")
xi = ctypes.CDLL("libXi.so.6")
x.XOpenDisplay.restype = V
x.XInternAtom.restype = C
x.XInternAtom.argtypes = [V, ctypes.c_char_p, ctypes.c_int]
x.XGetAtomName.restype = ctypes.c_char_p
x.XGetAtomName.argtypes = [V, C]


class DeviceInfo(ctypes.Structure):     # XDeviceInfo
    _fields_ = [("id", C), ("type", C), ("name", ctypes.c_char_p), ("num_classes", ctypes.c_int), ("use", ctypes.c_int), ("inputclassinfo", V)]


xi.XListInputDevices.restype = ctypes.POINTER(DeviceInfo)
xi.XListInputDevices.argtypes = [V, ctypes.POINTER(ctypes.c_int)]
xi.XOpenDevice.restype = V
xi.XOpenDevice.argtypes = [V, C]
xi.XListDeviceProperties.restype = ctypes.POINTER(C)
xi.XListDeviceProperties.argtypes = [V, V, ctypes.POINTER(ctypes.c_int)]
xi.XGetDeviceProperty.argtypes = [V, V, C, ctypes.c_long, ctypes.c_long, ctypes.c_int, C, ctypes.POINTER(C), ctypes.POINTER(ctypes.c_int),
                                  ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]
xi.XChangeDeviceProperty.argtypes = [V, V, C, C, ctypes.c_int, ctypes.c_int, V, ctypes.c_int]


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("list", "set", "setf"):
        sys.exit(__doc__)
    d = x.XOpenDisplay(None)
    if not d:
        sys.exit("cannot open the display (DISPLAY=:0 as the user)")
    n = ctypes.c_int()
    devs = xi.XListInputDevices(V(d), ctypes.byref(n))
    found = [devs[i] for i in range(n.value) if devs[i].name and sys.argv[2].lower() in devs[i].name.decode().lower()]
    if not found:
        sys.exit("no input device with %r in its name; present: %s" % (sys.argv[2], ", ".join(devs[i].name.decode() for i in range(n.value))))
    for info in found:
        dev = xi.XOpenDevice(V(d), info.id)
        print("device %d: %s" % (info.id, info.name.decode()))
        if sys.argv[1] == "list":
            cnt = ctypes.c_int()
            props = xi.XListDeviceProperties(V(d), V(dev), ctypes.byref(cnt))
            for i in range(cnt.value):
                atype, fmt, nitems, after = C(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong()
                data = ctypes.POINTER(ctypes.c_ubyte)()
                xi.XGetDeviceProperty(V(d), V(dev), props[i], 0, 16, 0, C(0), ctypes.byref(atype), ctypes.byref(fmt), ctypes.byref(nitems), ctypes.byref(after), ctypes.byref(data))
                vals = []
                if fmt.value == 32 and atype.value and x.XGetAtomName(V(d), atype.value) == b"INTEGER":
                    arr = ctypes.cast(data, ctypes.POINTER(ctypes.c_int))
                    vals = [arr[k] for k in range(min(nitems.value, 8))]
                elif fmt.value == 32 and atype.value and x.XGetAtomName(V(d), atype.value) == b"FLOAT":
                    arr = ctypes.cast(data, ctypes.POINTER(ctypes.c_float))
                    vals = [round(arr[k], 3) for k in range(min(nitems.value, 8))]
                print("  %s  type=%s format=%d n=%d %s" % (x.XGetAtomName(V(d), props[i]).decode(), x.XGetAtomName(V(d), atype.value).decode() if atype.value else "-", fmt.value, nitems.value, vals or ""))
        else:
            name = sys.argv[3]
            if sys.argv[1] == "set":
                vals = [int(v) for v in sys.argv[4:]]
                arr, typ = (ctypes.c_int * len(vals))(*vals), b"INTEGER"
            else:
                vals = [float(v) for v in sys.argv[4:]]
                arr, typ = (ctypes.c_float * len(vals))(*vals), b"FLOAT"
            xi.XChangeDeviceProperty(V(d), V(dev), x.XInternAtom(V(d), name.encode(), 0), x.XInternAtom(V(d), typ, 0), 32, 0, ctypes.cast(arr, V), len(vals))
            print("  %s = %s" % (name, vals))
    x.XSync(V(d), 0)


if __name__ == "__main__":
    main()
