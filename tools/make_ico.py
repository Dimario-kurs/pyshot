"""Собирает assets/PyShot.ico из иконки приложения.

Запуск:  py tools/make_ico.py
Иконка рисуется кодом (pyshot/app.py), внешних картинок в проекте нет.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# вывод по-русски не должен падать на консоли с другой кодировкой
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


from PySide6.QtCore import QBuffer, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

SIZES = (16, 20, 24, 32, 48, 64, 128, 256)


def dib_entry(image: QImage) -> bytes:
    """Классический BMP-вариант записи: понимают все версии Windows."""
    image = image.convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()

    header = struct.pack("<IiiHHIIiiII", 40, width, height * 2, 1, 32, 0,
                         0, 0, 0, 0, 0)

    pixels = bytearray()
    for y in range(height - 1, -1, -1):          # BMP хранит строки снизу вверх
        for x in range(width):
            argb = image.pixel(x, y)
            a = (argb >> 24) & 0xFF
            r = (argb >> 16) & 0xFF
            g = (argb >> 8) & 0xFF
            b = argb & 0xFF
            pixels += bytes((b, g, r, a))

    mask_row = ((width + 31) // 32) * 4          # маска прозрачности, нули
    mask = bytes(mask_row * height)
    return header + bytes(pixels) + mask


def png_entry(image: QImage) -> bytes:
    """Для 256×256 хранить PNG компактнее (поддержка с Windows Vista)."""
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def build(target: Path) -> None:
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    from pyshot.app import tray_icon

    icon = tray_icon()
    entries = []
    for size in SIZES:
        image = icon.pixmap(size, size).toImage()
        if image.isNull():
            continue
        data = png_entry(image) if size >= 256 else dib_entry(image)
        entries.append((size, data))

    offset = 6 + 16 * len(entries)
    directory = struct.pack("<HHH", 0, 1, len(entries))
    body = b""
    for size, data in entries:
        dimension = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", dimension, dimension, 0, 0,
                                 1, 32, len(data), offset)
        body += data
        offset += len(data)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(directory + body)
    print(f"{target} — {len(entries)} размеров, {target.stat().st_size} байт")


if __name__ == "__main__":
    build(ROOT / "assets" / "PyShot.ico")
