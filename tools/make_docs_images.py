"""Пересобирает картинки для README (папка docs/).

Запуск:  py tools/make_docs_images.py
Сцены синтетические — на снимках нет ничего с реального рабочего стола.
"""

from __future__ import annotations

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


from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pyshot import shapes as S  # noqa: E402
from pyshot.config import Config  # noqa: E402
from pyshot.i18n import set_language  # noqa: E402
from pyshot.overlay import DRAG_NONE, Overlay  # noqa: E402
from pyshot.settings_dialog import SettingsDialog  # noqa: E402
from pyshot.shapes import Shape  # noqa: E402

DOCS = ROOT / "docs"
W, H = 1100, 700


def desktop(title: str) -> QImage:
    """Нарисованный «рабочий стол» — фон для демонстраций."""
    image = QImage(W, H, QImage.Format_RGB32)
    p = QPainter(image)
    p.fillRect(0, 0, W, H, QColor("#101826"))
    p.fillRect(0, 0, W, 46, QColor("#1d2a3d"))
    font = QFont("Segoe UI")
    font.setPointSize(12)
    p.setFont(font)
    p.setPen(QColor("#cfe0f5"))
    p.drawText(QRectF(20, 0, W - 40, 46), Qt.AlignVCenter, title)

    for index, colour in enumerate(("#2f6fed", "#34c759", "#ff9500")):
        x = 70 + index * 330
        p.fillRect(x, 130 + (index % 2) * 90, 260, 170, QColor(colour))
    p.setPen(QColor("#54637a"))
    p.drawText(QRectF(0, H - 60, W, 40), Qt.AlignCenter,
               "демонстрационный фон")
    p.end()
    return image


def save(widget, name: str) -> None:
    path = DOCS / name
    widget.grab().save(str(path))
    print(f"  {path.relative_to(ROOT)}")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    cfg = Config()
    shots = []

    # 1. редактор: выделение + инструменты + разметка
    editor = Overlay(desktop("Окно выделения и панели инструментов"),
                     QRect(0, 0, W, H), 1.0, cfg)
    editor.resize(W, H)
    editor.selection = QRectF(90, 100, 620, 430)
    editor.shapes = [
        Shape(S.RECT, QColor("#ff3b30"), 3, QPointF(140, 150), QPointF(420, 300)),
        Shape(S.ARROW, QColor("#ff3b30"), 4, QPointF(600, 470), QPointF(430, 310)),
        Shape(S.TEXT, QColor("#ff3b30"), 3, QPointF(150, 330),
              text="важное место", font_size=20),
        Shape(S.MARKER, QColor("#ffcc00"), 4,
              points=[QPointF(150, 420), QPointF(480, 420)]),
    ]
    editor._show_panels()
    editor.show()
    shots.append((editor, "editor.png"))

    # 2. подсветка окна под курсором
    window = Overlay(desktop("Подсветка окна под курсором"),
                     QRect(0, 0, W, H), 1.0, cfg,
                     windows=[QRectF(400, 220, 480, 300),
                              QRectF(60, 110, 560, 360)])
    window.resize(W, H)
    window._cursor_pos = QPointF(640, 370)
    window._drag = DRAG_NONE
    window.show()
    shots.append((window, "window-highlight.png"))

    # 3. режим таймера
    timer = Overlay(desktop("Съёмка по таймеру"), QRect(0, 0, W, H), 1.0, cfg,
                    mode="timer", delay=3)
    timer.resize(W, H)
    timer.set_selection_from_desktop(QRect(120, 120, 560, 380))
    timer.show()
    shots.append((timer, "timer.png"))

    # 4. настройки на двух языках
    # в документацию не должны попадать реальные пути и имя пользователя
    demo = {
        "save_dir": r"C:\Users\User\Desktop\Скриншоты",
        "filename_template": "screenshot_%Y-%m-%d_%H-%M-%S",
        "hotkey_region": "Ctrl+4",
        "hotkey_fullscreen": "Ctrl+5",
        "hotkey_delayed": "Ctrl+6",
        "delay_seconds": 3,
        "color_profile": "monitor",
    }

    set_language("ru")
    ru_cfg = Config()
    ru_cfg.update(demo)
    ru_cfg["language"] = "ru"
    ru = SettingsDialog(ru_cfg)
    ru.show()
    shots.append((ru, "settings-ru.png"))

    set_language("en")
    en_cfg = Config()
    en_cfg.update(demo)
    en_cfg["language"] = "en"
    en = SettingsDialog(en_cfg)
    en.show()
    shots.append((en, "settings-en.png"))

    def grab_all():
        print("сохраняю картинки:")
        for widget, name in shots:
            save(widget, name)
            widget.close()
        set_language("ru")
        app.quit()

    QTimer.singleShot(900, grab_all)
    app.exec()


if __name__ == "__main__":
    main()
