"""Keyboard layouts for btkbd-split.py (key translation) and btkbd-keymap.py (the matching additions to the X key map).

The X server of Maemo 5 has ONE key map for all keyboards (changing it for the external keyboard changes the built-in keypad too), so the layout of an
external keyboard is made in user space: the splitter turns the key codes of the external keyboard into other Linux key codes before X sees them.
Keys whose symbols exist in the built-in map (letters, Enter, Tab, arrows...) pass through; for the characters that do not exist there (Czech letters,
AltGr characters) the splitter sends spare key codes (SPARE_BASE ...), and btkbd-keymap.py gives these codes their symbols in the X key map: purely an
addition, nothing the built-in keypad uses is changed.
"""
KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_RIGHTSHIFT, KEY_RIGHTCTRL, KEY_RIGHTALT, KEY_CAPSLOCK = 29, 42, 54, 97, 100, 58
LETTERS = set(range(16, 26)) | set(range(30, 39)) | set(range(44, 51))         # Q..P, A..L, Z..M (Linux key codes)
SPARE_BASE = 183                                                               # KEY_F13 .. : not used by the built-in keypad (X key code = Linux code + 8)

LAYOUTS = {}

# Czech QWERTZ: Linux key code -> (symbol, symbol with Shift)
CZ_PLAIN = {
    41: ("semicolon", "degree"), 2: ("plus", "1"), 3: ("ecaron", "2"), 4: ("scaron", "3"), 5: ("ccaron", "4"), 6: ("rcaron", "5"),
    7: ("zcaron", "6"), 8: ("yacute", "7"), 9: ("aacute", "8"), 10: ("iacute", "9"), 11: ("eacute", "0"), 12: ("equal", "percent"),
    13: ("dead_acute", "dead_caron"), 26: ("uacute", "slash"), 27: ("parenright", "parenleft"), 39: ("uring", "quotedbl"),
    40: ("section", "exclam"), 43: ("dead_diaeresis", "apostrophe"), 51: ("comma", "question"), 52: ("period", "colon"),
    53: ("minus", "underscore"), 86: ("backslash", "bar"),
}
# with AltGr (the same symbol on all levels)
CZ_ALTGR = {
    2: "asciitilde", 3: "dead_caron", 4: "asciicircum", 5: "dead_breve", 6: "degree", 7: "dead_ogonek", 8: "grave", 9: "dead_abovedot",
    10: "dead_acute", 11: "dead_doubleacute", 12: "dead_diaeresis", 13: "dead_cedilla", 16: "backslash", 17: "bar", 18: "EuroSign",
    33: "bracketleft", 34: "bracketright", 45: "numbersign", 46: "ampersand", 47: "at", 48: "braceleft", 49: "braceright", 51: "less",
    52: "greater", 53: "asterisk", 26: "bracketleft", 27: "bracketright", 39: "dollar", 31: "dstroke", 32: "Dstroke", 37: "lstroke", 38: "Lstroke",
}
LAYOUTS["cz"] = {"plain": CZ_PLAIN, "altgr": CZ_ALTGR, "swap_yz": True}
LAYOUTS["us"] = {"plain": {}, "altgr": {}, "swap_yz": False}


def spare_codes(layout):
    """{(key, kind): spare Linux key code} with kind "pl" (plain/Shift pair) or "ag" (AltGr), numbered in a fixed order."""
    lay = LAYOUTS[layout]
    out, n = {}, SPARE_BASE
    for code in sorted(lay["plain"]):
        out[(code, "pl")] = n; n += 1
    for code in sorted(lay["altgr"]):
        out[(code, "ag")] = n; n += 1
    return out


def spare_symbols(layout):
    """{spare Linux key code: (type, [symbols])} for the X key map."""
    lay, res = LAYOUTS[layout], {}
    for (code, kind), n in spare_codes(layout).items():
        if kind == "pl":
            res[n] = ("TWO_LEVEL", list(lay["plain"][code]))
        else:
            res[n] = ("FOUR_LEVEL", [lay["altgr"][code]] * 4)
    return res
