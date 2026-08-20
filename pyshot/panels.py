"""Панели инструментов поверх выделения + иконки, нарисованные кодом.

Оформление и набор кнопок повторяют Lightshot: светлая панель, тёмные
иконки; справа — инструменты рисования, снизу — копировать/сохранить/закрыть.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPainterPath,
                           QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QButtonGroup, QColorDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QMenu, QPushButton,
                               QSlider, QToolButton, QVBoxLayout, QWidget)

from . import shapes as S
from .i18n import tr

ICON_SIZE = 22
FG = QColor("#3c3c3c")          # цвет иконок

PALETTE = [
    "#ff3b30", "#ff9500", "#ffcc00", "#34c759",
    "#00c7be", "#007aff", "#5856d6", "#af52de",
    "#ffffff", "#8e8e93", "#3a3a3c", "#000000",
]

PANEL_QSS = """
QFrame#panel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #fdfdfd, stop:1 #e6e6e6);
    border: 1px solid #8f8f8f;
    border-radius: 3px;
}
QFrame#sep { background: #cdcdcd; max-height: 1px; min-height: 1px;
             border: none; margin: 2px 3px; }
QFrame#vsep { background: #cdcdcd; max-width: 1px; min-width: 1px;
              border: none; margin: 3px 2px; }
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px;
}
QToolButton:hover   { background: #cfe4fa; border-color: #7fb0e0; }
QToolButton:pressed { background: #aecdf0; border-color: #5d95cf; }
QToolButton:checked { background: #bcd9f7; border-color: #5d95cf; }
"""


# --------------------------------------------------------------------------
# иконки
# --------------------------------------------------------------------------
def _pixmap(draw_fn) -> QPixmap:
    pm = QPixmap(ICON_SIZE, ICON_SIZE)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    draw_fn(painter)
    painter.end()
    return pm


def _stroke(painter: QPainter, width: float = 1.8) -> None:
    pen = QPen(FG, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)


def _fill(painter: QPainter) -> None:
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(FG))


def make_icon(name: str) -> QIcon:
    def draw(p: QPainter):
        if name == S.PEN:
            # карандаш: корпус + остриё
            _fill(p)
            p.drawPolygon(QPolygonF([QPointF(7, 15), QPointF(15.5, 4.5),
                                     QPointF(18, 6.5), QPointF(9.5, 17)]))
            p.drawPolygon(QPolygonF([QPointF(9.5, 17), QPointF(5, 19),
                                     QPointF(7, 15)]))
        elif name == S.LINE:
            _stroke(p, 1.9)
            p.drawLine(QPointF(4.5, 17.5), QPointF(17.5, 4.5))
        elif name == S.ARROW:
            _stroke(p, 1.9)
            p.drawLine(QPointF(4.5, 17.5), QPointF(15.5, 6.5))
            _fill(p)
            p.drawPolygon(QPolygonF([QPointF(18.5, 3.5), QPointF(10.5, 5.2),
                                     QPointF(16.8, 11.5)]))
        elif name == S.RECT:
            _stroke(p, 1.8)
            p.drawRect(QRectF(3.5, 6.5, 15, 10))
        elif name == S.MARKER:
            # маркер: широкое перо + след
            _fill(p)
            p.drawPolygon(QPolygonF([QPointF(9, 12.5), QPointF(15.5, 4),
                                     QPointF(18.5, 6.5), QPointF(12, 15)]))
            p.drawPolygon(QPolygonF([QPointF(12, 15), QPointF(6.5, 16.5),
                                     QPointF(9, 12.5)]))
            pen = QPen(FG, 2.2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(4.5, 19.5), QPointF(14, 19.5))
        elif name == S.TEXT:
            f = QFont()
            f.setPointSize(14)
            p.setFont(f)
            p.setPen(QPen(FG))
            p.drawText(QRectF(0, 0, ICON_SIZE, ICON_SIZE), Qt.AlignCenter, "T")
        elif name == "undo":
            _stroke(p, 2.0)
            path = QPainterPath(QPointF(5, 9))
            path.cubicTo(QPointF(13, 4), QPointF(19, 8), QPointF(15.5, 17))
            p.drawPath(path)
            _fill(p)
            p.drawPolygon(QPolygonF([QPointF(3, 10.5), QPointF(10, 6.5),
                                     QPointF(9.5, 13.5)]))
        elif name == "copy":
            _stroke(p, 1.7)
            p.drawRect(QRectF(4, 3.5, 10, 12))
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(QRectF(8, 7.5, 10, 12))
        elif name == "save":
            # дискета
            _stroke(p, 1.7)
            p.drawRect(QRectF(3.5, 3.5, 15, 15))
            p.setBrush(QBrush(FG))
            p.drawRect(QRectF(7, 3.5, 8, 6))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(6, 12, 10, 6.5))
        elif name == "close":
            _stroke(p, 2.2)
            p.drawLine(QPointF(5, 5), QPointF(17, 17))
            p.drawLine(QPointF(17, 5), QPointF(5, 17))

    return QIcon(_pixmap(draw))


def color_icon(color: QColor) -> QIcon:
    """Квадрат текущего цвета с уголком, как в Lightshot."""
    def draw(p: QPainter):
        p.setPen(QPen(QColor("#5a5a5a"), 1))
        p.setBrush(QBrush(QColor(color)))
        p.drawRect(QRectF(2.5, 2.5, 17, 17))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#2b2b2b")))
        p.drawPolygon(QPolygonF([QPointF(20, 15), QPointF(20, 20),
                                 QPointF(15, 20)]))

    return QIcon(_pixmap(draw))


def _button(icon_name: str, tooltip: str, checkable: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setIcon(make_icon(icon_name))
    btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setCursor(Qt.ArrowCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    return btn


def _separator(horizontal: bool = True) -> QFrame:
    line = QFrame()
    line.setObjectName("sep" if horizontal else "vsep")
    line.setFrameShape(QFrame.NoFrame)
    return line


# --------------------------------------------------------------------------
# всплывающее окно: палитра + толщина линии
# --------------------------------------------------------------------------
class ColorPopup(QWidget):
    colorPicked = Signal(QColor)
    widthPicked = Signal(int)

    def __init__(self, color: QColor, width: int, parent=None) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint)
        self.setStyleSheet(PANEL_QSS + """
            QLabel { color: #303030; }
            QPushButton { border: 1px solid #9a9a9a; border-radius: 3px; }
            QPushButton:hover { border: 2px solid #2f6fed; }
            QPushButton#more { color: #303030; background: #f0f0f0;
                               padding: 4px; }
            QPushButton#more:hover { background: #e2ecfb; }
        """)
        frame = QFrame(self)
        frame.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        box = QVBoxLayout(frame)
        box.setContentsMargins(8, 8, 8, 8)
        box.setSpacing(6)

        grid = QGridLayout()
        grid.setSpacing(4)
        for index, hex_color in enumerate(PALETTE):
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background-color: {hex_color};")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _=False, c=hex_color: self._pick(QColor(c)))
            grid.addWidget(btn, index // 4, index % 4)
        box.addLayout(grid)

        more = QPushButton(tr("Другой цвет…"))
        more.setObjectName("more")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(self._pick_custom)
        box.addWidget(more)

        box.addWidget(_separator())

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(str(width))
        self._label.setFixedWidth(18)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 20)
        slider.setValue(int(width))
        slider.setFixedWidth(110)
        slider.valueChanged.connect(self._width_changed)
        row.addWidget(QLabel(tr("Толщина")))
        row.addWidget(slider)
        row.addWidget(self._label)
        box.addLayout(row)

    def _pick(self, color: QColor) -> None:
        self.colorPicked.emit(color)
        self.close()

    def _pick_custom(self) -> None:
        self.close()
        color = QColorDialog.getColor(parent=None,
                                      title=tr("Цвет инструмента"))
        if color.isValid():
            self.colorPicked.emit(color)

    def _width_changed(self, value: int) -> None:
        self._label.setText(str(value))
        self.widthPicked.emit(int(value))


# --------------------------------------------------------------------------
# панели
# --------------------------------------------------------------------------
class ToolPanel(QWidget):
    """Вертикальная панель: инструменты, цвет, отмена."""

    toolChanged = Signal(str)
    colorChanged = Signal(QColor)
    widthChanged = Signal(int)
    undoRequested = Signal()

    TOOLS = [
        (S.PEN, "Карандаш"),
        (S.LINE, "Линия"),
        (S.ARROW, "Стрелка"),
        (S.RECT, "Прямоугольник"),
        (S.MARKER, "Маркер"),
        (S.TEXT, "Текст"),
    ]   # подписи переводятся при создании кнопок

    def __init__(self, color: QColor, width: int, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(PANEL_QSS)
        self._color = QColor(color)
        self._width = int(width)

        frame = QFrame(self)
        frame.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        box = QVBoxLayout(frame)
        box.setContentsMargins(3, 3, 3, 3)
        box.setSpacing(1)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}
        for index, (tool, title) in enumerate(self.TOOLS):
            btn = _button(tool, tr(title), checkable=True)
            btn.clicked.connect(lambda _=False, t=tool: self._toggle(t))
            self._group.addButton(btn)
            box.addWidget(btn)
            self._buttons[tool] = btn
            if index < len(self.TOOLS) - 1:
                box.addWidget(_separator())

        box.addWidget(_separator())
        self._color_btn = _button(S.PEN, tr("Цвет и толщина линии"))
        self._color_btn.setIcon(color_icon(self._color))
        self._color_btn.clicked.connect(self._open_color)
        box.addWidget(self._color_btn)

        box.addWidget(_separator())
        undo_btn = _button("undo", tr("Отменить (Ctrl+Z)"))
        undo_btn.clicked.connect(self.undoRequested.emit)
        box.addWidget(undo_btn)

        self.adjustSize()

    # -- поведение ---------------------------------------------------------
    def _toggle(self, tool: str) -> None:
        btn = self._buttons[tool]
        if not btn.isChecked():
            self._group.setExclusive(False)
            btn.setChecked(False)
            self._group.setExclusive(True)
            self.toolChanged.emit("")
        else:
            self.toolChanged.emit(tool)

    def clear_tool(self) -> None:
        self._group.setExclusive(False)
        for btn in self._buttons.values():
            btn.setChecked(False)
        self._group.setExclusive(True)
        self.toolChanged.emit("")

    def _open_color(self) -> None:
        popup = ColorPopup(self._color, self._width, self)
        popup.colorPicked.connect(self._set_color)
        popup.widthPicked.connect(self._set_width)
        popup.adjustSize()
        popup.move(self._popup_pos(self._color_btn, popup.width()))
        popup.show()

    def _set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self._color_btn.setIcon(color_icon(self._color))
        self.colorChanged.emit(self._color)

    def _set_width(self, value: int) -> None:
        self._width = int(value)
        self.widthChanged.emit(self._width)

    def _popup_pos(self, button: QToolButton, popup_width: int) -> QPoint:
        pos = button.mapToGlobal(QPoint(button.width() + 6, 0))
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen and pos.x() + popup_width > screen.right():
            pos = button.mapToGlobal(QPoint(-popup_width - 6, 0))
        return pos


class ActionPanel(QWidget):
    """Горизонтальная панель под выделением: копировать, сохранить, закрыть."""

    actionTriggered = Signal(str)

    ACTIONS = [
        ("copy", "Копировать в буфер (Ctrl+C)"),
        ("save", "Сохранить (Ctrl+S / Enter)"),
        ("close", "Закрыть (Esc)"),
    ]   # подписи переводятся при создании кнопок

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(PANEL_QSS)

        frame = QFrame(self)
        frame.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        row = QHBoxLayout(frame)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(1)
        for index, (name, tooltip) in enumerate(self.ACTIONS):
            btn = _button(name, tr(tooltip))
            btn.clicked.connect(lambda _=False, n=name:
                                self.actionTriggered.emit(n))
            row.addWidget(btn)
            if index < len(self.ACTIONS) - 1:
                row.addWidget(_separator(horizontal=False))
        self.adjustSize()


class TimerPanel(QWidget):
    """Панель режима таймера: выбор задержки, «Снять», «Закрыть»."""

    shoot = Signal()
    delayChanged = Signal(int)
    closeRequested = Signal()

    DELAYS = (0, 3, 5, 10)

    def __init__(self, seconds: int, parent=None) -> None:
        super().__init__(parent)
        self._seconds = int(seconds)
        self.setStyleSheet(PANEL_QSS + """
            QToolButton#delay { color: #303030; padding: 5px 10px; }
            QPushButton#shoot {
                background: #2f8bf0; color: white; border: 1px solid #1f6fd0;
                border-radius: 4px; padding: 6px 18px; font-weight: bold;
            }
            QPushButton#shoot:hover  { background: #4a9cf5; }
            QPushButton#shoot:pressed{ background: #1f6fd0; }
        """)

        frame = QFrame(self)
        frame.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        row = QHBoxLayout(frame)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(4)

        self._delay_btn = QToolButton()
        self._delay_btn.setObjectName("delay")
        self._delay_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._delay_btn.setPopupMode(QToolButton.InstantPopup)
        self._delay_btn.setCursor(Qt.ArrowCursor)
        self._delay_btn.setFocusPolicy(Qt.NoFocus)
        self._delay_btn.setToolTip(tr("Через сколько секунд сделать снимок"))
        menu = QMenu(self._delay_btn)
        for value in self.DELAYS:
            if value == 0:
                title = tr("Без таймера — снять сразу")
            elif value < 5:
                title = tr("{n} секунды").format(n=value)
            else:
                title = tr("{n} секунд").format(n=value)
            act = menu.addAction(title)
            act.triggered.connect(lambda _=False, v=value: self._set_delay(v))
        self._delay_btn.setMenu(menu)
        row.addWidget(self._delay_btn)

        row.addWidget(_separator(horizontal=False))

        self._shoot_btn = QPushButton(tr("Снять"))
        self._shoot_btn.setObjectName("shoot")
        self._shoot_btn.setCursor(Qt.PointingHandCursor)
        self._shoot_btn.setFocusPolicy(Qt.NoFocus)
        self._shoot_btn.clicked.connect(self.shoot.emit)
        row.addWidget(self._shoot_btn)

        close_btn = _button("close", tr("Отмена (Esc)"))
        close_btn.clicked.connect(self.closeRequested.emit)
        row.addWidget(close_btn)

        self._update_text()
        self.adjustSize()

    def _set_delay(self, seconds: int) -> None:
        self._seconds = max(0, int(seconds))
        self._update_text()
        self.adjustSize()
        self.delayChanged.emit(self._seconds)

    def seconds(self) -> int:
        return self._seconds

    def _update_text(self) -> None:
        self._delay_btn.setText(
            tr("Таймер: нет") if self._seconds == 0
            else tr("Таймер: {n} с").format(n=self._seconds))
