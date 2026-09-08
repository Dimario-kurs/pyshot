"""Тесты без графической оболочки: запускаются на offscreen-платформе Qt.

Запуск:  py tests/test_pyshot.py
Ничего не выводит на экран и не трогает настройки пользователя —
конфиг и папка сохранения подменяются на временные.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# вывод по-русски не должен падать на консоли с другой кодировкой
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="pyshot-tests-"))
os.environ["APPDATA"] = str(TMP)            # конфиг пишется во временную папку

from PySide6.QtCore import QPointF, QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pyshot import i18n, shapes as S, storage  # noqa: E402
from pyshot.config import Config  # noqa: E402
from pyshot.hotkeys import format_hotkey, parse_hotkey  # noqa: E402
from pyshot.overlay import DRAG_NEW, Overlay  # noqa: E402
from pyshot.panels import (ActionPanel, TimerPanel, ToolPanel,  # noqa: E402
                           color_icon, make_icon)
from pyshot.shapes import Shape  # noqa: E402

app = QApplication(sys.argv)
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        failures.append(f"{name}: {detail}")
        print(f"  FAIL {name} {detail}")


def sample_config() -> Config:
    cfg = Config()
    cfg["save_dir"] = str(TMP / "shots")
    cfg["filename_template"] = "test_%H-%M-%S"
    cfg["notify_on_save"] = False
    return cfg


def sample_image(width=800, height=600) -> QImage:
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor("#3060a0"))
    painter = QPainter(image)
    painter.fillRect(QRectF(100, 100, 300, 200), QColor("#ffcc00"))
    painter.end()
    return image


# --------------------------------------------------------------------------
print("\nгорячие клавиши")
for text, expected in (("Ctrl+4", True), ("Shift+PrintScreen", True),
                       ("Alt+F5", True), ("Ctrl+", False), ("абырвалг", False)):
    check(f"разбор {text!r}", (parse_hotkey(text) is not None) == expected)
check("обратное форматирование", format_hotkey(*parse_hotkey("Ctrl+Shift+S"))
      == "Ctrl+Shift+S")

# --------------------------------------------------------------------------
print("\nиконки и панели")
for name in [t for t, _ in ToolPanel.TOOLS] + ["undo", "copy", "save", "close"]:
    check(f"иконка {name}", not make_icon(name).isNull())
check("иконка цвета", not color_icon(QColor("#ff0000")).isNull())
check("набор инструментов",
      [t for t, _ in ToolPanel.TOOLS]
      == [S.PEN, S.LINE, S.ARROW, S.RECT, S.MARKER, S.TEXT])
check("набор действий",
      [a for a, _ in ActionPanel.ACTIONS] == ["copy", "save", "close"])
check("варианты таймера", TimerPanel.DELAYS == (0, 3, 5, 10))

# --------------------------------------------------------------------------
print("\nвыделение и экспорт")
cfg = sample_config()
overlay = Overlay(sample_image(), QRect(0, 0, 800, 600), 1.0, cfg)
overlay.resize(800, 600)
overlay.selection = QRectF(100, 100, 400, 300)
overlay.shapes = [
    Shape(S.RECT, QColor("#ff0000"), 4, QPointF(120, 120), QPointF(300, 260)),
    Shape(S.ARROW, QColor("#00ff00"), 5, QPointF(150, 350), QPointF(400, 180)),
    Shape(S.TEXT, QColor("#ffffff"), 3, QPointF(140, 140), text="тест",
          font_size=20),
]
result = overlay.render_result()
check("размер результата", result.size().width() == 400
      and result.size().height() == 300, str(result.size()))

hidpi = Overlay(sample_image(1200, 900), QRect(0, 0, 800, 600), 1.5, cfg)
hidpi.resize(800, 600)
hidpi.selection = QRectF(10, 10, 200, 100)
check("масштаб 1.5 — полное разрешение",
      hidpi.render_result().size().width() == 300)

check("маркер угла", overlay._handle_at(QPointF(100, 100)) == 0)
check("середина без маркера", overlay._handle_at(QPointF(300, 250)) == -1)

for rect in (QRectF(0, 0, 200, 150), QRectF(600, 450, 200, 150),
             QRectF(0, 0, 800, 600)):
    overlay.selection = rect
    overlay._place_panels()
    inside = all(0 <= panel.x() and 0 <= panel.y()
                 and panel.x() + panel.width() <= 801
                 and panel.y() + panel.height() <= 601
                 for panel in (overlay.tool_panel, overlay.action_panel))
    check(f"панели в пределах экрана {rect.topLeft().toPoint()}", inside)

# --------------------------------------------------------------------------
print("\nснимок окна по клику")
windows = Overlay(sample_image(), QRect(0, 0, 800, 600), 1.0, cfg,
                  windows=[QRectF(200, 150, 300, 200), QRectF(50, 50, 600, 400)])
windows.resize(800, 600)
check("верхнее окно под курсором",
      windows._window_at(QPointF(300, 250)) == QRectF(200, 150, 300, 200))
check("нижнее окно под курсором",
      windows._window_at(QPointF(80, 420)) == QRectF(50, 50, 600, 400))
check("пустое место", windows._window_at(QPointF(750, 550)) is None)

windows._cursor_pos = QPointF(300, 250)
windows._drag = DRAG_NEW
windows.selection = QRectF(QPointF(300, 250), QPointF(300, 250))


class _Click:
    def button(self):
        return Qt.LeftButton


windows.mouseReleaseEvent(_Click())
check("клик выделил окно целиком",
      windows.selection.normalized() == QRectF(200, 150, 300, 200))

# --------------------------------------------------------------------------
print("\nсохранение файлов")
first = storage.save_image(result.copy(), cfg)
second = storage.save_image(result.copy(), cfg)
check("файл сохранён", first is not None and first.exists())
check("имена не совпадают", first != second)

cfg["file_format"] = "jpg"
jpeg = storage.save_image(result.copy(), cfg)
check("jpeg сохранён", jpeg is not None and jpeg.suffix == ".jpg")
cfg["file_format"] = "png"

for mode, tagged in (("srgb", True), ("none", False)):
    cfg["color_profile"] = mode
    path = storage.save_image(result.copy(), cfg)
    raw = path.read_bytes()
    check(f"цветовой профиль «{mode}»", (b"iCCP" in raw) == tagged)
    check(f"пиксели не изменились ({mode})",
          QColor(QImage(str(path)).pixel(5, 5)) == QColor(result.pixel(5, 5)))

# --------------------------------------------------------------------------
print("\nдва языка")
CYR = re.compile(r"[А-Яа-яЁё]")
i18n.set_language("en")
english = [i18n.tr(t) for t in
           ("Снимок области", "Весь экран", "Настройки…", "Выход", "Снять",
            "Карандаш", "Сохранить", "Отмена")]
check("русские строки переведены", not any(CYR.search(t) for t in english),
      str(english))
check("подстановка чисел",
      i18n.tr("Область с таймером — {n} сек").format(n=5)
      == "Area with timer — 5 s")
i18n.set_language("ru")
check("возврат на русский", i18n.tr("Выход") == "Выход")

missing = [key for key in i18n.EN if not isinstance(i18n.EN[key], str)]
check("словарь перевода целый", not missing)

# --------------------------------------------------------------------------
print("\nтаймер с запомненной областью")
from pyshot.app import PyShotApp  # noqa: E402

pyshot = PyShotApp(app)
pyshot.cfg["save_dir"] = str(TMP / "timer")
pyshot.cfg["filename_template"] = "timer_%H-%M-%S"
pyshot.cfg["notify_on_save"] = False
pyshot.cfg["last_region"] = None
check("области ещё нет", pyshot.last_region() is None)

pyshot.overlay = overlay
overlay.selection = QRectF(60, 50, 420, 260)
pyshot._remember_region()
pyshot.overlay = None
check("область запомнена", pyshot.last_region() == QRect(60, 50, 420, 260))

# режим «сохранять сразу»
pyshot.cfg["timer_opens_editor"] = False
pyshot.capture_last_region()
saved = sorted((TMP / "timer").glob("*.png"))
check("снимок по таймеру сохранён", len(saved) == 1)
check("оверлей не открывался", pyshot.overlay is None)

# режим «открывать редактор»: рисование и выбор копировать/сохранить
pyshot.cfg["timer_opens_editor"] = True
pyshot.capture_last_region()
editor = pyshot.overlay
check("редактор после таймера открылся", editor is not None)
if editor is not None:
    check("рамка подставлена",
          editor.has_selection() and editor.tool_panel is not None)
    check("панель действий с копированием",
          [a for a, _ in editor.action_panel.ACTIONS] == ["copy", "save",
                                                          "close"])
    check("файл ещё не сохранён",
          len(sorted((TMP / "timer").glob("*.png"))) == 1)
    editor.close()
    app.processEvents()

pyshot.cfg["last_region"] = [99000, 99000, 300, 200]
pyshot.cfg["timer_opens_editor"] = False
pyshot.capture_last_region()
check("область вне экрана — просит выбрать заново", pyshot.overlay is not None)
if pyshot.overlay is not None:
    pyshot.overlay.close()
    app.processEvents()

# --------------------------------------------------------------------------
print("\nзащита от зависания при открытом окне")
from PySide6.QtWidgets import QDialog  # noqa: E402

modal = QDialog()
modal.setModal(True)
modal.open()                      # показываем, не блокируя тест
app.processEvents()
check("модальное окно замечено", pyshot.busy_with_dialog())
pyshot.overlay = None
pyshot.capture_region()
check("съёмка области не запускается", pyshot.overlay is None)
pyshot.capture_delayed(3, "last")
check("таймер не запускается", pyshot.overlay is None
      and pyshot.countdown is None)
modal.close()
app.processEvents()
check("после закрытия окна съёмка снова разрешена",
      not pyshot.busy_with_dialog())

# клик по значку в трее открывает настройки, а не съёмку
opened = []
pyshot.open_settings = lambda: opened.append(True)
from PySide6.QtWidgets import QSystemTrayIcon  # noqa: E402
pyshot._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
check("левый клик по значку открывает настройки", opened == [True])

pyshot.hotkeys.unregister_all()

# --------------------------------------------------------------------------
print("\nперевод: разбор строк и слой")
from pyshot import translate as tr_engine  # noqa: E402
from pyshot import translation_layer as tr_layer  # noqa: E402

def line(text, x, y, w, h):
    return tr_engine.Line(text=text, rect=QRectF(x, y, w, h))

# строки одного абзаца идут подряд и склеиваются
paragraph = [line("Today is my birthday.", 30, 40, 180, 18),
             line("Tomorrow I need to go to the store", 30, 70, 300, 18),
             line("and buy antifreeze.", 30, 100, 160, 18)]
blocks = tr_engine.group_lines(paragraph)
check("абзац склеен в один блок", len(blocks) == 1, f"блоков: {len(blocks)}")
check("текст блока собран целиком",
      blocks[0].text.endswith("and buy antifreeze."))

# далеко отстоящая строка — отдельный блок
separate = paragraph + [line("Footer note", 30, 400, 120, 18)]
blocks = tr_engine.group_lines(separate)
check("далёкая строка отделена", len(blocks) == 2, f"блоков: {len(blocks)}")

# строка в другой колонке тоже отдельно
columns = [line("Left column", 30, 40, 120, 18),
           line("Right column", 600, 44, 130, 18)]
check("соседняя колонка не приклеивается",
      len(tr_engine.group_lines(columns)) == 2)

check("пустой список не ломает разбор", tr_engine.group_lines([]) == [])

# --- слой: координаты, цвета, кегль ---------------------------------------
canvas = QImage(400, 200, QImage.Format_RGB32)
canvas.fill(QColor("#eef1f6"))
painter = QPainter(canvas)
painter.setPen(QColor("#202124"))
font = QFont("Segoe UI")
font.setPointSize(12)
painter.setFont(font)
painter.drawText(QRectF(20, 20, 360, 40), Qt.AlignLeft | Qt.AlignVCenter,
                 "Hello world")
painter.end()

background, foreground = tr_layer.estimate_colours(canvas, QRectF(22, 26, 90, 18))
check("цвет подложки взят из картинки",
      abs(background.red() - 238) < 12 and abs(background.blue() - 246) < 12,
      background.name())
check("цвет букв тёмный на светлом фоне",
      foreground.lightness() < background.lightness() - 60,
      f"{foreground.name()} на {background.name()}")

block = tr_engine.Block(lines=[line("Hello world", 22, 26, 90, 18)])
block.translation = "Привет, мир"
layer = tr_layer.build_layer(canvas, [block], scale=1.5,
                             origin=QPointF(100, 50))
check("слой построен", len(layer) == 1)
if layer:
    rect = layer[0].rect
    # 22/1.5 + 100 = 114.7 с поправкой на отступ подложки
    check("координаты пересчитаны с учётом масштаба и смещения",
          abs(rect.left() - (100 + 22 / 1.5 - tr_layer.PAD)) < 0.6,
          f"left={rect.left():.1f}")
    check("кегль в разумных пределах",
          tr_layer.MIN_FONT <= layer[0].font_size <= 20,
          str(layer[0].font_size))

# длинный текст ужимается, короткий — нет
big = tr_layer.fit_font_size("Коротко", QRectF(0, 0, 300, 40), 14)
small = tr_layer.fit_font_size("Очень длинная строка, которая никак не помещается "
                               "в отведённое ей место", QRectF(0, 0, 120, 20), 14)
check("длинный текст ужимается сильнее короткого", small < big,
      f"{small} против {big}")

# блок без перевода в слой не попадает
empty = tr_engine.Block(lines=[line("Hello", 22, 26, 40, 18)])
check("непереведённый блок пропускается",
      tr_layer.build_layer(canvas, [empty], 1.0, QPointF(0, 0)) == [])

# --------------------------------------------------------------------------
print()
if failures:
    print(f"ПРОВАЛЕНО проверок: {len(failures)}")
    for item in failures:
        print("   -", item)
    sys.exit(1)
print("все проверки пройдены")
sys.exit(0)
