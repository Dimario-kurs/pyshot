"""Список видимых окон Windows — чтобы подсвечивать то, на которое наведён курсор."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys

from PySide6.QtCore import QRect

GW_OWNER = 4
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
GWL_EXSTYLE = -20

MIN_SIDE = 40

# фон рабочего стола — не окно, подсвечивать его незачем
SKIP_CLASSES = {"Progman", "WorkerW", "Windows.UI.Core.CoreWindow.Ghost"}


class _RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


def _frame_rect(user32, dwmapi, hwnd) -> QRect | None:
    """Видимые границы окна: без невидимых полей изменения размера."""
    rect = _RECT()
    got = False
    if dwmapi is not None:
        res = dwmapi.DwmGetWindowAttribute(
            wt.HWND(hwnd), wt.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect), ctypes.sizeof(rect))
        got = (res == 0)
    if not got and not user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(rect)):
        return None

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width < MIN_SIDE or height < MIN_SIDE:
        return None
    return QRect(rect.left, rect.top, width, height)


def _is_cloaked(dwmapi, hwnd) -> bool:
    if dwmapi is None:
        return False
    value = wt.DWORD(0)
    res = dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), wt.DWORD(DWMWA_CLOAKED),
                                       ctypes.byref(value), ctypes.sizeof(value))
    return res == 0 and value.value != 0


def visible_windows() -> list[QRect]:
    """Прямоугольники окон в физических пикселях, сверху вниз по z-порядку."""
    if sys.platform != "win32":
        return []

    user32 = ctypes.windll.user32
    try:
        dwmapi = ctypes.windll.dwmapi
    except Exception:
        dwmapi = None

    result: list[QRect] = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(hwnd, _param):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if _is_cloaked(dwmapi, hwnd):
            return True

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in SKIP_CLASSES:
            return True

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # окна, сквозь которые проходят клики, снимать нечего
        if ex_style & WS_EX_TRANSPARENT:
            return True

        rect = _frame_rect(user32, dwmapi, hwnd)
        if rect is not None:
            result.append(rect)
        return True

    try:
        user32.EnumWindows(callback, 0)
    except Exception:
        return []
    return result


def virtual_origin():
    """Левый верхний угол виртуального рабочего стола в физических пикселях."""
    from PySide6.QtCore import QPoint

    if sys.platform != "win32":
        return QPoint(0, 0)
    user32 = ctypes.windll.user32
    return QPoint(user32.GetSystemMetrics(76), user32.GetSystemMetrics(77))
