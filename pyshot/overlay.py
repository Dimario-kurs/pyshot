"""Полноэкранный оверлей: выделение области + рисование поверх снимка."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QPainter,
                           QPen)
from PySide6.QtWidgets import QTextEdit, QWidget

from . import shapes as S
from .i18n import tr
from .panels import ActionPanel, TimerPanel, ToolPanel
from .shapes import Shape

HANDLE_SIZE = 8
HANDLE_GRAB = 10
MIN_SELECTION = 4

# режимы перетаскивания
DRAG_NONE = 0
DRAG_NEW = 1
DRAG_MOVE = 2
DRAG_RESIZE = 3
DRAG_DRAW = 4

# индексы маркеров: 0 nw, 1 n, 2 ne, 3 e, 4 se, 5 s, 6 sw, 7 w
HANDLE_CURSORS = [
    Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor,
    Qt.SizeHorCursor, Qt.SizeFDiagCursor, Qt.SizeVerCursor,
    Qt.SizeBDiagCursor, Qt.SizeHorCursor,
]


class _TextEditor(QTextEdit):
    """Поле ввода текста прямо на скриншоте."""

    committed = Signal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.committed.emit()
            return
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and event.modifiers() & Qt.ControlModifier):
            self.committed.emit()
            return
        super().keyPressEvent(event)


class Overlay(QWidget):
    """Окно на весь виртуальный рабочий стол с замороженным снимком."""

    saveRequested = Signal(QImage, bool)   # изображение, спрашивать ли путь
    copyRequested = Signal(QImage)
    shootRequested = Signal(int)           # режим таймера: снять через N секунд
    closed = Signal()

    def __init__(self, image: QImage, geometry: QRect, scale: float, cfg,
                 mode: str = "shot", delay: int = 3, windows=None) -> None:
        super().__init__(None)
        self.image = image
        self.scale_factor = float(scale)
        self.cfg = cfg
        self.mode = mode
        self.delay = max(0, int(delay))
        # прямоугольники окон (в координатах этого окна), сверху вниз
        self.windows = list(windows or [])

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint |
                            Qt.NoDropShadowWindowHint)
        self.setWindowTitle("PyShot")
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(geometry)

        # состояние выделения
        self.selection = QRectF()
        self._drag = DRAG_NONE
        self._drag_origin = QPointF()
        self._sel_origin = QRectF()
        self._handle = -1
        self._cursor_pos = QPointF(-1, -1)

        # состояние рисования
        self.tool = ""
        self.color = QColor(cfg["pen_color"])
        self.pen_width = int(cfg["pen_width"])
        self.font_size = int(cfg["font_size"])
        self.shapes: list[Shape] = []
        self._redo: list[Shape] = []
        self._current: Shape | None = None
        self._editor: _TextEditor | None = None

        # панели
        self.timer_mode = (mode == "timer")
        if self.timer_mode:
            # в режиме таймера рисовать нечего: кадр снимется позже
            self.tool_panel = None
            self.action_panel = TimerPanel(self.delay, self)
            self.action_panel.shoot.connect(self._shoot)
            self.action_panel.delayChanged.connect(self._set_delay)
            self.action_panel.closeRequested.connect(self.close)
        else:
            self.tool_panel = ToolPanel(self.color, self.pen_width, self)
            self.tool_panel.toolChanged.connect(self._set_tool)
            self.tool_panel.colorChanged.connect(self._set_color)
            self.tool_panel.widthChanged.connect(self._set_width)
            self.tool_panel.undoRequested.connect(self.undo)
            self.tool_panel.hide()

            self.action_panel = ActionPanel(self)
            self.action_panel.actionTriggered.connect(self._on_action)
        self.action_panel.hide()

    # ------------------------------------------------------------------ #
    # показ
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def set_selection_from_desktop(self, rect: QRect) -> None:
        """Ставит выделение по координатам рабочего стола (запомненная область)."""
        origin = self.geometry().topLeft()
        sel = QRectF(rect.x() - origin.x(), rect.y() - origin.y(),
                     rect.width(), rect.height())
        sel = sel.intersected(QRectF(self.rect()))
        if sel.width() >= MIN_SELECTION and sel.height() >= MIN_SELECTION:
            self.selection = sel
            self._show_panels()
            self.update()

    # -- режим таймера ------------------------------------------------------
    def _shoot(self) -> None:
        if self.has_selection():
            self.shootRequested.emit(self.delay)

    def _set_delay(self, seconds: int) -> None:
        self.delay = max(0, int(seconds))
        self.cfg["delay_seconds"] = self.delay
        self.cfg.save()
        self.update()

    def has_selection(self) -> bool:
        rect = self.selection.normalized()
        return rect.width() >= MIN_SELECTION and rect.height() >= MIN_SELECTION

    # ------------------------------------------------------------------ #
    # отрисовка
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawImage(QRectF(self.rect()), self.image,
                          QRectF(self.image.rect()))

        dim = QColor(0, 0, 0, 110)
        rect = self.selection.normalized()
        if self.has_selection():
            full = QRectF(self.rect())
            painter.fillRect(QRectF(full.left(), full.top(),
                                    full.width(), rect.top() - full.top()), dim)
            painter.fillRect(QRectF(full.left(), rect.bottom(),
                                    full.width(), full.bottom() - rect.bottom()), dim)
            painter.fillRect(QRectF(full.left(), rect.top(),
                                    rect.left() - full.left(), rect.height()), dim)
            painter.fillRect(QRectF(rect.right(), rect.top(),
                                    full.right() - rect.right(), rect.height()), dim)

            painter.save()
            painter.setClipRect(rect)
            for shape in self.shapes:
                shape.draw(painter)
            if self._current is not None:
                self._current.draw(painter)
            painter.restore()

            self._draw_frame(painter, rect)
            self._draw_size_badge(painter, rect)
        else:
            painter.fillRect(self.rect(), dim)
            hovered = (self._window_at(self._cursor_pos)
                       if self._drag == DRAG_NONE else None)
            if hovered is not None:
                self._draw_window_highlight(painter, hovered)
            else:
                self._draw_crosshair(painter)
            self._draw_hint(painter)

    def _window_at(self, pos: QPointF):
        """Верхнее окно под курсором (уже в координатах оверлея)."""
        if not self.windows or pos.x() < 0:
            return None
        for rect in self.windows:
            if rect.contains(pos):
                clipped = rect.intersected(QRectF(self.rect()))
                if (clipped.width() >= MIN_SELECTION
                        and clipped.height() >= MIN_SELECTION):
                    return clipped
        return None

    def _draw_window_highlight(self, painter: QPainter, rect: QRectF) -> None:
        """Окно под курсором показываем в полную яркость — как в macOS."""
        scale = self.scale_factor
        source = QRectF(rect.left() * scale, rect.top() * scale,
                        rect.width() * scale, rect.height() * scale)
        painter.drawImage(rect, self.image, source)
        painter.fillRect(rect, QColor(0, 122, 255, 28))
        painter.setPen(QPen(QColor("#00a2ff"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        self._draw_size_badge(painter, rect)

    def _draw_frame(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#00a2ff"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(-0.5, -0.5, 0.5, 0.5))

        if self._drag in (DRAG_NONE, DRAG_MOVE, DRAG_RESIZE):
            painter.setPen(QPen(QColor("#00a2ff"), 1))
            painter.setBrush(QColor("#ffffff"))
            for handle in self._handles(rect):
                painter.drawRect(handle)

    def _draw_size_badge(self, painter: QPainter, rect: QRectF) -> None:
        text = f"{int(round(rect.width() * self.scale_factor))} × " \
               f"{int(round(rect.height() * self.scale_factor))}"
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text) + 12
        height = metrics.height() + 6

        x = rect.left()
        y = rect.top() - height - 6
        if y < 0:
            y = rect.top() + 6
        x = max(0.0, min(x, self.width() - width))

        box = QRectF(x, y, width, height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(20, 20, 20, 210))
        painter.drawRoundedRect(box, 4, 4)
        painter.setPen(QPen(QColor("#f2f2f2")))
        painter.drawText(box, Qt.AlignCenter, text)

    def _draw_crosshair(self, painter: QPainter) -> None:
        if self._cursor_pos.x() < 0:
            return
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.drawLine(QPointF(0, self._cursor_pos.y()),
                         QPointF(self.width(), self._cursor_pos.y()))
        painter.drawLine(QPointF(self._cursor_pos.x(), 0),
                         QPointF(self._cursor_pos.x(), self.height()))

    def _draw_hint(self, painter: QPainter) -> None:
        screen = QGuiApplication.primaryScreen()
        area = screen.geometry().translated(-self.geometry().topLeft()) \
            if screen else self.rect()
        if self.timer_mode:
            when = (tr("сразу по кнопке «Снять»") if self.delay == 0
                    else tr("через {n} сек после кнопки «Снять»").format(
                        n=self.delay))
            text = tr("Кликните по окну или выделите область — снимок {when}\n"
                      "Ctrl+A — весь экран      Esc — отмена").format(when=when)
        else:
            text = tr("Кликните по окну — снимется оно целиком,\n"
                      "либо выделите область мышью\n"
                      "Ctrl+A — весь экран      Esc — отмена")
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        lines = text.split("\n")
        width = max(metrics.horizontalAdvance(line) for line in lines) + 32
        height = metrics.height() * len(lines) + 22

        box = QRectF(area.center().x() - width / 2,
                     area.center().y() - height / 2, width, height)
        # не даём подсказке уехать за край окна
        box.moveLeft(max(0.0, min(box.left(), self.width() - width)))
        box.moveTop(max(0.0, min(box.top(), self.height() - height)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(20, 20, 20, 190))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QPen(QColor("#f2f2f2")))
        painter.drawText(box, Qt.AlignCenter, text)

    # ------------------------------------------------------------------ #
    # маркеры выделения
    # ------------------------------------------------------------------ #
    def _handles(self, rect: QRectF) -> list[QRectF]:
        half = HANDLE_SIZE / 2
        cx, cy = rect.center().x(), rect.center().y()
        points = [
            (rect.left(), rect.top()), (cx, rect.top()), (rect.right(), rect.top()),
            (rect.right(), cy), (rect.right(), rect.bottom()),
            (cx, rect.bottom()), (rect.left(), rect.bottom()), (rect.left(), cy),
        ]
        return [QRectF(x - half, y - half, HANDLE_SIZE, HANDLE_SIZE)
                for x, y in points]

    def _handle_at(self, pos: QPointF) -> int:
        if not self.has_selection():
            return -1
        rect = self.selection.normalized()
        for index, handle in enumerate(self._handles(rect)):
            if handle.adjusted(-HANDLE_GRAB / 2, -HANDLE_GRAB / 2,
                               HANDLE_GRAB / 2, HANDLE_GRAB / 2).contains(pos):
                return index
        return -1

    def _resize_selection(self, index: int, pos: QPointF) -> None:
        rect = QRectF(self._sel_origin)
        left, top = rect.left(), rect.top()
        right, bottom = rect.right(), rect.bottom()
        if index in (0, 6, 7):
            left = pos.x()
        if index in (2, 3, 4):
            right = pos.x()
        if index in (0, 1, 2):
            top = pos.y()
        if index in (4, 5, 6):
            bottom = pos.y()
        self.selection = QRectF(QPointF(left, top),
                                QPointF(right, bottom)).normalized()

    # ------------------------------------------------------------------ #
    # мышь
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:
        pos = event.position()
        if event.button() == Qt.RightButton:
            self._on_right_click()
            return
        if event.button() != Qt.LeftButton:
            return

        if not self.timer_mode:
            self._commit_text()

        if self.has_selection():
            handle = self._handle_at(pos)
            rect = self.selection.normalized()
            if handle >= 0:
                self._drag = DRAG_RESIZE
                self._handle = handle
                self._sel_origin = rect
                self._hide_panels()
                return
            if rect.contains(pos):
                if self.tool == S.TEXT:
                    self._start_text(pos)
                    return
                if self.tool:
                    self._start_draw(pos)
                    return
                self._drag = DRAG_MOVE
                self._drag_origin = pos
                self._sel_origin = rect
                self._hide_panels()
                return

        # новое выделение
        if self.tool_panel is not None:
            self.tool_panel.clear_tool()
        self._drag = DRAG_NEW
        self._drag_origin = pos
        self.selection = QRectF(pos, pos)
        self.shapes.clear()
        self._redo.clear()
        self._hide_panels()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        self._cursor_pos = pos

        if self._drag == DRAG_NEW:
            self.selection = QRectF(self._drag_origin, pos).normalized()
        elif self._drag == DRAG_MOVE:
            delta = pos - self._drag_origin
            moved = self._sel_origin.translated(delta)
            # не выпускаем выделение за пределы экранов
            moved.moveLeft(max(0.0, min(moved.left(),
                                        self.width() - moved.width())))
            moved.moveTop(max(0.0, min(moved.top(),
                                       self.height() - moved.height())))
            self.selection = moved
        elif self._drag == DRAG_RESIZE:
            self._resize_selection(self._handle, pos)
        elif self._drag == DRAG_DRAW and self._current is not None:
            if self._current.kind in (S.PEN, S.MARKER):
                self._current.points.append(QPointF(pos))
            else:
                self._current.p2 = QPointF(pos)
        else:
            self._update_cursor(pos)

        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        if self._drag == DRAG_DRAW and self._current is not None:
            shape = self._current
            self._current = None
            keep = True
            if shape.kind in (S.LINE, S.ARROW, S.RECT, S.ELLIPSE):
                keep = (abs(shape.p2.x() - shape.p1.x()) > 2
                        or abs(shape.p2.y() - shape.p1.y()) > 2)
            if keep:
                self.shapes.append(shape)
                self._redo.clear()
        elif self._drag == DRAG_NEW and not self.has_selection():
            # клик без протяжки — снимаем окно под курсором
            window = self._window_at(self._cursor_pos)
            self.selection = QRectF(window) if window is not None else QRectF()

        self._drag = DRAG_NONE
        self._handle = -1
        self._show_panels()
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if (event.button() == Qt.LeftButton and self.has_selection()
                and not self.tool
                and self.selection.normalized().contains(event.position())):
            self._on_action("copy")

    def _on_right_click(self) -> None:
        if self._editor is not None:
            self._commit_text()
        elif self.tool and self.tool_panel is not None:
            self.tool_panel.clear_tool()
        elif self.has_selection():
            self.selection = QRectF()
            self.shapes.clear()
            self._redo.clear()
            self._hide_panels()
            self.update()
        else:
            self.close()

    def _update_cursor(self, pos: QPointF) -> None:
        handle = self._handle_at(pos)
        if handle >= 0:
            self.setCursor(HANDLE_CURSORS[handle])
        elif (self.has_selection()
              and self.selection.normalized().contains(pos)):
            self.setCursor(Qt.CrossCursor if self.tool else Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    # ------------------------------------------------------------------ #
    # рисование
    # ------------------------------------------------------------------ #
    def _start_draw(self, pos: QPointF) -> None:
        self._drag = DRAG_DRAW
        shape = Shape(kind=self.tool, color=QColor(self.color),
                      width=self.pen_width, p1=QPointF(pos), p2=QPointF(pos),
                      font_size=self.font_size)
        if shape.kind in (S.PEN, S.MARKER):
            shape.points = [QPointF(pos)]
        self._current = shape

    def _set_tool(self, tool: str) -> None:
        self._commit_text()
        self.tool = tool or ""
        self._update_cursor(self._cursor_pos)

    def _set_color(self, color: QColor) -> None:
        self.color = QColor(color)
        self.cfg["pen_color"] = self.color.name()
        if self._editor is not None:
            self._apply_editor_style()

    def _set_width(self, value: int) -> None:
        self.pen_width = int(value)
        self.cfg["pen_width"] = self.pen_width

    def undo(self) -> None:
        if self.shapes:
            self._redo.append(self.shapes.pop())
            self.update()

    def redo(self) -> None:
        if self._redo:
            self.shapes.append(self._redo.pop())
            self.update()

    # ------------------------------------------------------------------ #
    # текст
    # ------------------------------------------------------------------ #
    def _start_text(self, pos: QPointF) -> None:
        editor = _TextEditor(self)
        editor.setFrameStyle(0)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.document().setDocumentMargin(0)
        editor.setAcceptRichText(False)
        editor.committed.connect(self._commit_text)
        editor.textChanged.connect(self._fit_editor)
        self._editor = editor
        self._editor_pos = QPointF(pos)
        self._apply_editor_style()
        editor.move(QPoint(int(pos.x()), int(pos.y())))
        editor.resize(QSize(200, int(self.font_size * 2.2)))
        editor.show()
        editor.setFocus(Qt.OtherFocusReason)

    def _apply_editor_style(self) -> None:
        if self._editor is None:
            return
        font = QFont()
        font.setPointSizeF(float(self.font_size))
        self._editor.setFont(font)
        self._editor.setStyleSheet(
            f"background: rgba(0,0,0,60); color: {self.color.name()};"
            f"selection-background-color: rgba(255,255,255,80);")

    def _fit_editor(self) -> None:
        if self._editor is None:
            return
        doc = self._editor.document()
        doc.adjustSize()
        width = max(60, int(doc.idealWidth()) + 24)
        height = max(int(self.font_size * 2.0), int(doc.size().height()) + 8)
        self._editor.resize(QSize(width, height))

    def _commit_text(self) -> None:
        if self._editor is None:
            return
        text = self._editor.toPlainText().strip("\n")
        pos = QPointF(self._editor_pos)
        editor = self._editor
        self._editor = None
        editor.hide()
        editor.deleteLater()
        if text.strip():
            self.shapes.append(Shape(kind=S.TEXT, color=QColor(self.color),
                                     width=self.pen_width, p1=pos, text=text,
                                     font_size=self.font_size))
            self._redo.clear()
        self.setFocus(Qt.OtherFocusReason)
        self.update()

    # ------------------------------------------------------------------ #
    # панели
    # ------------------------------------------------------------------ #
    def _hide_panels(self) -> None:
        if self.tool_panel is not None:
            self.tool_panel.hide()
        self.action_panel.hide()

    def _show_panels(self) -> None:
        if not self.has_selection():
            self._hide_panels()
            return
        self._place_panels()
        if self.tool_panel is not None:
            self.tool_panel.show()
            self.tool_panel.raise_()
        self.action_panel.show()
        self.action_panel.raise_()

    def _place_panels(self) -> None:
        rect = self.selection.normalized().toRect()
        gap = 8

        if self.tool_panel is None:
            self._place_action_panel(rect, gap)
            return

        tw, th = self.tool_panel.width(), self.tool_panel.height()
        x = rect.right() + gap
        if x + tw > self.width():
            x = rect.left() - gap - tw
        if x < 0:
            x = max(0, min(self.width() - tw, rect.right() - tw - gap))
        y = rect.top()
        if y + th > self.height():
            y = self.height() - th
        self.tool_panel.move(int(max(0, x)), int(max(0, y)))
        self._place_action_panel(rect, gap)

    def _place_action_panel(self, rect, gap: int) -> None:
        aw, ah = self.action_panel.width(), self.action_panel.height()
        ax = rect.right() - aw
        ax = max(0, min(ax, self.width() - aw))
        ay = rect.bottom() + gap
        if ay + ah > self.height():
            ay = rect.top() - gap - ah
            if ay < 0:
                ay = max(0, rect.bottom() - ah - gap)
        self.action_panel.move(int(ax), int(ay))

    # ------------------------------------------------------------------ #
    # клавиатура и действия
    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event) -> None:
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)

        if key == Qt.Key_Escape:
            if self.tool and self.tool_panel is not None:
                self.tool_panel.clear_tool()
            elif self.has_selection():
                self.selection = QRectF()
                self.shapes.clear()
                self._hide_panels()
                self.update()
            else:
                self.close()
            return
        if ctrl and key == Qt.Key_A:
            self.selection = QRectF(self.rect())
            self._show_panels()
            self.update()
            return
        if self.timer_mode:
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._shoot()
            return
        if ctrl and key == Qt.Key_Z:
            self.redo() if shift else self.undo()
            return
        if ctrl and key == Qt.Key_Y:
            self.redo()
            return
        if ctrl and key == Qt.Key_C:
            self._on_action("copy")
            return
        if ctrl and key == Qt.Key_S:
            self._on_action("saveas" if shift else "save")
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._on_action("save")
            return
        super().keyPressEvent(event)

    def _on_action(self, name: str) -> None:
        if name == "undo":
            self.undo()
            return
        if name == "redo":
            self.redo()
            return
        if name == "close":
            self.close()
            return
        if not self.has_selection():
            return

        self._commit_text()
        image = self.render_result()
        # прячем оверлей до показа диалогов — иначе они окажутся под ним
        self.hide()
        if name == "copy":
            self.copyRequested.emit(image)
        elif name == "save":
            self.saveRequested.emit(image, False)
        elif name == "saveas":
            self.saveRequested.emit(image, True)
        self.close()

    # ------------------------------------------------------------------ #
    # результат
    # ------------------------------------------------------------------ #
    def render_result(self) -> QImage:
        rect = self.selection.normalized()
        scale = self.scale_factor
        src = QRectF(rect.left() * scale, rect.top() * scale,
                     rect.width() * scale, rect.height() * scale)
        out = QImage(max(1, int(round(src.width()))),
                     max(1, int(round(src.height()))), QImage.Format_RGB32)
        out.fill(Qt.black)

        painter = QPainter(out)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(QRectF(0, 0, out.width(), out.height()),
                          self.image, src)
        painter.scale(scale, scale)
        painter.translate(-rect.left(), -rect.top())
        painter.setClipRect(rect)
        for shape in self.shapes:
            shape.draw(painter)
        painter.end()
        return out

    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:
        if self._editor is not None:
            self._editor.deleteLater()
            self._editor = None
        self.closed.emit()
        super().closeEvent(event)
