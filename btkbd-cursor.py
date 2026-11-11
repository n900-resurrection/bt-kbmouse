#!/opt/python3/bin/python3
"""Show or hide the mouse pointer on the N900 (run ON THE PHONE as user, DISPLAY=:0):
    btkbd-cursor.py show [SCALE]    white arrow with a black outline on the root window (SCALE 1..4, default 1)
    btkbd-cursor.py hide     back to the 1x1 empty cursor of Maemo
Maemo hides the pointer: every cursor of the theme in /usr/share/icons/default/cursors is a link to a transparent image (see DOC/mouse.md).
The arrow is drawn here and set with XDefineCursor on the root window, which windows without their own cursor inherit. Nothing is installed or changed on disk.
"""
import ctypes, sys

V = ctypes.c_void_p
x = ctypes.CDLL("libX11.so.6")
xc = ctypes.CDLL("libXcursor.so.1")
x.XOpenDisplay.restype = V
x.XDefaultRootWindow.restype = ctypes.c_ulong
x.XDefaultRootWindow.argtypes = [V]
x.XDefineCursor.argtypes = [V, ctypes.c_ulong, ctypes.c_ulong]
x.XUndefineCursor.argtypes = [V, ctypes.c_ulong]
x.XSync.argtypes = [V, ctypes.c_int]


class Image(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint), ("size", ctypes.c_uint), ("width", ctypes.c_uint), ("height", ctypes.c_uint),
                ("xhot", ctypes.c_uint), ("yhot", ctypes.c_uint), ("delay", ctypes.c_uint), ("pixels", ctypes.POINTER(ctypes.c_uint))]


xc.XcursorImageCreate.restype = ctypes.POINTER(Image)
xc.XcursorImageCreate.argtypes = [ctypes.c_int, ctypes.c_int]
xc.XcursorImageLoadCursor.restype = ctypes.c_ulong
xc.XcursorImageLoadCursor.argtypes = [V, ctypes.POINTER(Image)]

# Classic arrow: B = black outline, W = white fill. Scaled by an integer factor (default 1; the display is 800x480 on 3.5 inches, 2 is too big).
ARROW = ["B...........",
         "BB..........",
         "BWB.........",
         "BWWB........",
         "BWWWB.......",
         "BWWWWB......",
         "BWWWWWB.....",
         "BWWWWWWB....",
         "BWWWWWWWB...",
         "BWWWWWWWWB..",
         "BWWWWWWWWWB.",
         "BWWWWWBBBBBB",
         "BWWBWWB.....",
         "BWB.BWWB....",
         "BB..BWWB....",
         "B....BWWB...",
         ".....BWWB...",
         "......BB...."]


def arrow_cursor(d, scale):
    n = max(len(ARROW), len(ARROW[0])) * scale + 2
    img = xc.XcursorImageCreate(n, n).contents
    for i in range(n * n):
        img.pixels[i] = 0
    for yy, row in enumerate(ARROW):
        for xx, ch in enumerate(row):
            if ch == ".":
                continue
            px = 0xffffffff if ch == "W" else 0xff000000
            for dy in range(scale):
                for dx in range(scale):
                    img.pixels[(yy * scale + dy) * n + xx * scale + dx] = px
    img.xhot = img.yhot = 0
    return xc.XcursorImageLoadCursor(V(d), ctypes.pointer(img))


def main():
    if len(sys.argv) not in (2, 3) or sys.argv[1] not in ("show", "hide"):
        sys.exit(__doc__)
    scale = int(sys.argv[2]) if len(sys.argv) == 3 else 1
    d = x.XOpenDisplay(None)
    if not d:
        sys.exit("cannot open the display (DISPLAY=:0 as the user)")
    root = x.XDefaultRootWindow(V(d))
    if sys.argv[1] == "show":
        x.XDefineCursor(V(d), root, arrow_cursor(d, scale))
    else:
        x.XUndefineCursor(V(d), root)
    x.XSync(V(d), 0)


if __name__ == "__main__":
    main()
