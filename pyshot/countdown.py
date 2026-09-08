"""Обратный отсчёт перед снимком по таймеру (как в macOS «Снимок экрана»)."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QCursor, QFont, QGuiApplication, QPainter,
                           QPen)
from PySide6.QtWidgets import QWidget

from .i18n import tr


class Countdown(QWidget):
    finished = Signal()
    cancelled = Signal()

    # размер окошка при обычном снимке; под большую область оно растёт
    WIDTH = 190
    HEIGHT = 96
    MIN_SCALE = 0.45
    MAX_SCALE = 3.0

    def __init__(self, seconds: int, note: str = "снимок по таймеру",
                 target: QRect | None = None) -> None:
        super().__init__(None)
        self._note = note
        self._target = QRect(target) if target is not None else None
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint |
                            Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.PointingHandCursor)

        # Отсчёт принадлежит кадру, а не экрану: на снимке во весь экран цифры
        # крупные, на маленькой области — маленькие, иначе окошко закроет собой
        # всё, что человек собрался снять.
        self._scale = self._pick_scale(self._target)
        self._width = round(self.WIDTH * self._scale)
        self._height = round(self.HEIGHT * self._scale)
        self.setFixedSize(self._width, self._height)

        self._left = max(1, int(seconds))
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def _pick_scale(self, target: QRect | None) -> float:
        if target is None or target.width() < 4 or target.height() < 4:
            return 1.0
        # 2.2 и 2.4 — во сколько раз кадр должен быть больше окошка,
        # чтобы то не заслоняло собой снимаемое
        by_width = target.width() / (self.WIDTH * 2.2)
        by_height = target.height() / (self.HEIGHT * 2.4)
        return max(self.MIN_SCALE, min(self.MAX_SCALE, min(by_width, by_height)))

    def _place(self) -> None:
        """Ставим окошко в середину будущего кадра, а не в середину экрана."""
        if self._target is not None:
            centre = self._target.center()
        else:
            screen = (QGuiApplication.screenAt(QCursor.pos())
                      or QGuiApplication.primaryScreen())
            area = screen.availableGeometry() if screen else None
            if area is None:
                return
            centre = area.center()

        x = centre.x() - self._width // 2
        y = centre.y() - self._height // 2

        # за край экрана не выпускаем: иначе отсчёта попросту не видно
        screen = (QGuiApplication.screenAt(centre)
                  or QGuiApplication.primaryScreen())
        if screen is not None:
            area = screen.availableGeometry()
            x = max(area.left(), min(x, area.right() - self._width))
            y = max(area.top(), min(y, area.bottom() - self._height))
        self.move(x, y)

    def start(self) -> None:
        self._place()
        self.show()
        self.raise_()
        self._timer.start()

    def _tick(self) -> None:
        self._left -= 1
        if self._left <= 0:
            self._timer.stop()
            self.hide()
            # даём окну исчезнуть, только потом снимаем экран
            QTimer.singleShot(180, self.finished.emit)
            QTimer.singleShot(400, self.deleteLater)
            return
        self.update()

    def mousePressEvent(self, event) -> None:
        self._timer.stop()
        self.hide()
        self.cancelled.emit()
        self.deleteLater()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        k = self._scale

        box = QRectF(0, 0, self._width, self._height)
        painter.setPen(QPen(QColor(255, 255, 255, 60), max(1.0, k)))
        painter.setBrush(QColor(24, 24, 26, 225))
        painter.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5),
                                12 * k, 12 * k)

        font = QFont()
        font.setPointSizeF(max(9.0, 30 * k))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(QRectF(0, 6 * k, self._width, 56 * k), Qt.AlignCenter,
                         str(self._left))

        font.setPointSizeF(max(7.0, 9 * k))
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255, 190)))
        painter.drawText(QRectF(0, 58 * k, self._width, 32 * k), Qt.AlignCenter,
                         f"{self._note}\n" + tr("клик — отмена"))
