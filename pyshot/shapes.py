"""Фигуры, которые пользователь рисует поверх скриншота."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF

# идентификаторы инструментов
PEN = "pen"
LINE = "line"
ARROW = "arrow"
RECT = "rect"
ELLIPSE = "ellipse"
MARKER = "marker"
TEXT = "text"


@dataclass
class Shape:
    kind: str
    color: QColor
    width: int = 3
    p1: QPointF = field(default_factory=QPointF)
    p2: QPointF = field(default_factory=QPointF)
    points: list = field(default_factory=list)
    text: str = ""
    font_size: int = 18

    # -- геометрия ---------------------------------------------------------
    def rect(self) -> QRectF:
        return QRectF(self.p1, self.p2).normalized()

    # -- отрисовка ---------------------------------------------------------
    def draw(self, painter: QPainter) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self.kind == PEN:
            self._draw_pen(painter)
        elif self.kind == MARKER:
            self._draw_marker(painter)
        elif self.kind == LINE:
            painter.setPen(self._pen())
            painter.drawLine(self.p1, self.p2)
        elif self.kind == ARROW:
            self._draw_arrow(painter)
        elif self.kind == RECT:
            painter.setPen(self._pen())
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect())
        elif self.kind == ELLIPSE:
            painter.setPen(self._pen())
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.rect())
        elif self.kind == TEXT:
            self._draw_text(painter)

        painter.restore()

    def _pen(self, width: float | None = None, alpha: int | None = None) -> QPen:
        color = QColor(self.color)
        if alpha is not None:
            color.setAlpha(alpha)
        pen = QPen(color, float(self.width if width is None else width))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def _path(self) -> QPainterPath:
        path = QPainterPath()
        if not self.points:
            return path
        path.moveTo(self.points[0])
        if len(self.points) == 1:
            path.lineTo(self.points[0] + QPointF(0.01, 0.01))
        for point in self.points[1:]:
            path.lineTo(point)
        return path

    def _draw_pen(self, painter: QPainter) -> None:
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._path())

    def _draw_marker(self, painter: QPainter) -> None:
        # полупрозрачный «текстовыделитель»: плоский широкий штрих
        color = QColor(self.color)
        color.setAlpha(90)
        pen = QPen(color, float(self.width) * 4.0)
        pen.setCapStyle(Qt.FlatCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._path())

    def _draw_arrow(self, painter: QPainter) -> None:
        line = QLineF(self.p1, self.p2)
        if line.length() < 1:
            return
        head = max(9.0, float(self.width) * 4.0)
        head = min(head, line.length() * 0.6)
        angle = math.atan2(-line.dy(), line.dx())

        # ствол укорачиваем, чтобы не торчал из наконечника
        shaft_end = QPointF(
            self.p2.x() - math.cos(angle) * head * 0.7,
            self.p2.y() + math.sin(angle) * head * 0.7,
        )
        painter.setPen(self._pen())
        painter.drawLine(self.p1, shaft_end)

        wing = math.radians(26)
        left = QPointF(
            self.p2.x() - math.cos(angle - wing) * head,
            self.p2.y() + math.sin(angle - wing) * head,
        )
        right = QPointF(
            self.p2.x() - math.cos(angle + wing) * head,
            self.p2.y() + math.sin(angle + wing) * head,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(QPolygonF([self.p2, left, right]))

    def _draw_text(self, painter: QPainter) -> None:
        if not self.text:
            return
        font = QFont()
        font.setPointSizeF(float(self.font_size))
        painter.setFont(font)
        painter.setPen(QPen(QColor(self.color)))
        rect = QRectF(self.p1, QPointF(self.p1.x() + 4000, self.p1.y() + 4000))
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                         self.text)
