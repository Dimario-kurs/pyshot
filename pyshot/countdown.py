"""Обратный отсчёт перед снимком по таймеру (как в macOS «Снимок экрана»)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .i18n import tr


class Countdown(QWidget):
    finished = Signal()
    cancelled = Signal()

    WIDTH = 190
    HEIGHT = 96

    def __init__(self, seconds: int, note: str = "снимок по таймеру") -> None:
        super().__init__(None)
        self._note = note
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint |
                            Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._left = max(1, int(seconds))
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        screen = QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else None
        if area:
            self.move(area.center().x() - self.WIDTH // 2, area.top() + 60)
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

        box = QRectF(0, 0, self.WIDTH, self.HEIGHT)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(QColor(24, 24, 26, 225))
        painter.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        font = QFont()
        font.setPointSize(30)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(QRectF(0, 6, self.WIDTH, 56), Qt.AlignCenter,
                         str(self._left))

        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255, 190)))
        painter.drawText(QRectF(0, 58, self.WIDTH, 32), Qt.AlignCenter,
                         f"{self._note}\n" + tr("клик — отмена"))
