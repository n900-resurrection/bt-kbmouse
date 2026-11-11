"""Settings of bt-kbmouse: one small INI file in the home directory of the user, written by the GUI and read by the service (as root).
The service watches the file, so a change takes effect within a few seconds."""
import configparser, os, tempfile

PATH = os.environ.get("BTKBMOUSE_CONF", "/home/user/.bt-kbmouse.conf")
STATUS = os.environ.get("BTKBMOUSE_STATUS", "/tmp/bt-kbmouse.status")          # written by the service, read by the GUI

DEFAULTS = {
    "enabled": "yes",           # the service takes over the keyboard
    "device": "ThinkPad",       # part of the name of the Bluetooth keyboard (as shown by /proc/bus/input/devices)
    "layout": "cz",             # cz, us or none (the keys as they are)
    "pointer_speed": "4",       # 1 (slow) .. 10 (fast)
    "scroll_speed": "4",        # 1 (slow) .. 10 (fast): middle button + TrackPoint
    "scroll_invert": "no",
    "cursor": "yes",            # show the mouse pointer (Maemo hides it)
    "cursor_size": "1",         # 1 .. 3
}
LAYOUTS = ("cz", "us", "none")


def load(path=PATH):
    cfg = dict(DEFAULTS)
    cp = configparser.ConfigParser()
    try:
        cp.read(path)
        cfg.update({k: v.strip() for k, v in cp["kbmouse"].items() if k in DEFAULTS})
    except (OSError, configparser.Error, KeyError):
        pass
    return cfg


def save(cfg, path=PATH):
    cp = configparser.ConfigParser()
    cp["kbmouse"] = {k: str(cfg.get(k, DEFAULTS[k])) for k in DEFAULTS}
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".bt-kbmouse-")
    with os.fdopen(fd, "w") as f:
        cp.write(f)
    os.replace(tmp, path)


def yes(cfg, key):
    return cfg.get(key, "no").lower() in ("yes", "true", "1", "on")


def number(cfg, key, low, high):
    try:
        v = int(float(cfg.get(key, DEFAULTS[key])))
    except ValueError:
        v = int(DEFAULTS[key])
    return max(low, min(high, v))


def decel(cfg):
    """Constant deceleration of the X pointer (see DOC/mouse.md): speed 4 gives 3.0 (the value found comfortable), 1 gives 12, 10 gives 1.2."""
    return round(12.0 / number(cfg, "pointer_speed", 1, 10), 2)


def scroll_step(cfg):
    """TrackPoint counts per wheel notch: speed 4 gives 5 counts, 10 gives 2."""
    return max(1, round(20.0 / number(cfg, "scroll_speed", 1, 10)))
