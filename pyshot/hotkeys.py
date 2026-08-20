"""Глобальные горячие клавиши через WinAPI RegisterHotKey.

Сообщение WM_HOTKEY перехватывается нативным фильтром событий Qt и
превращается в вызов python-колбэка в главном потоке.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
}

# Имя клавиши -> виртуальный код
VK_NAMES = {
    "printscreen": 0x2C, "prtscn": 0x2C, "prtsc": 0x2C, "snapshot": 0x2C,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22, "space": 0x20, "tab": 0x09,
    "backspace": 0x08, "enter": 0x0D, "return": 0x0D, "escape": 0x1B,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "pause": 0x13, "scrolllock": 0x91, "capslock": 0x14,
    "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
    "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
}
for _i in range(1, 25):
    VK_NAMES[f"f{_i}"] = 0x6F + _i
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    VK_NAMES[_c.lower()] = ord(_c)

# Обратная таблица для красивого отображения
VK_TO_NAME = {
    0x2C: "PrintScreen", 0x2D: "Insert", 0x2E: "Delete", 0x24: "Home",
    0x23: "End", 0x21: "PageUp", 0x22: "PageDown", 0x20: "Space",
    0x09: "Tab", 0x08: "Backspace", 0x0D: "Enter", 0x1B: "Escape",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x13: "Pause", 0x91: "ScrollLock", 0x14: "CapsLock",
}
for _i in range(1, 25):
    VK_TO_NAME[0x6F + _i] = f"F{_i}"


def parse_hotkey(text: str):
    """'Ctrl+Shift+S' -> (модификаторы, VK). Возвращает None, если не распознано."""
    if not text:
        return None
    mods = 0
    vk = None
    for raw in str(text).split("+"):
        part = raw.strip().lower()
        if not part:
            continue
        if part in MODIFIERS:
            mods |= MODIFIERS[part]
        elif part in VK_NAMES:
            vk = VK_NAMES[part]
        else:
            return None
    if vk is None:
        return None
    return mods, vk


def format_hotkey(mods: int, vk: int) -> str:
    parts = []
    if mods & MOD_CONTROL:
        parts.append("Ctrl")
    if mods & MOD_ALT:
        parts.append("Alt")
    if mods & MOD_SHIFT:
        parts.append("Shift")
    if mods & MOD_WIN:
        parts.append("Win")
    parts.append(VK_TO_NAME.get(vk, chr(vk) if 32 < vk < 127 else f"VK_{vk:02X}"))
    return "+".join(parts)


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd", wt.HWND),
        ("message", wt.UINT),
        ("wParam", wt.WPARAM),
        ("lParam", wt.LPARAM),
        ("time", wt.DWORD),
        ("pt_x", wt.LONG),
        ("pt_y", wt.LONG),
    ]


class HotkeyManager(QObject, QAbstractNativeEventFilter):
    """Регистрирует горячие клавиши и вызывает колбэки."""

    triggered = Signal(str)

    def __init__(self, hwnd: int, parent=None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._hwnd = int(hwnd)
        self._by_id: dict[int, str] = {}
        self._next_id = 0xB000
        self._user32 = ctypes.windll.user32

    # -- регистрация -------------------------------------------------------
    def register(self, name: str, hotkey_text: str) -> bool:
        parsed = parse_hotkey(hotkey_text)
        if not parsed:
            return False
        mods, vk = parsed
        hk_id = self._next_id
        self._next_id += 1
        ok = self._user32.RegisterHotKey(wt.HWND(self._hwnd), hk_id,
                                         mods | MOD_NOREPEAT, vk)
        if not ok:
            return False
        self._by_id[hk_id] = name
        return True

    def unregister_all(self) -> None:
        for hk_id in list(self._by_id):
            self._user32.UnregisterHotKey(wt.HWND(self._hwnd), hk_id)
        self._by_id.clear()

    # -- перехват сообщений ------------------------------------------------
    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(_MSG)).contents
        except Exception:
            return False, 0
        if msg.message == WM_HOTKEY:
            name = self._by_id.get(int(msg.wParam))
            if name:
                self.triggered.emit(name)
                return True, 0
        return False, 0
