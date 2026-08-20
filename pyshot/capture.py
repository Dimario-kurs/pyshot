"""Снимок экрана: собирает все мониторы в одно изображение."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter


def virtual_geometry() -> QRect:
    """Прямоугольник, покрывающий все мониторы (в логических координатах)."""
    rect = QRect()
    for screen in QGuiApplication.screens():
        rect = rect.united(screen.geometry())
    return rect


def grab_screens() -> tuple[QImage, QRect, float]:
    """Возвращает (изображение, геометрия, масштаб).

    Изображение всегда с devicePixelRatio = 1: его размер равен
    геометрии, умноженной на масштаб. Так проще считать координаты.
    """
    screens = QGuiApplication.screens()
    geo = virtual_geometry()
    scale = max([s.devicePixelRatio() for s in screens] or [1.0])
    if scale <= 0:
        scale = 1.0

    image = QImage(max(1, int(round(geo.width() * scale))),
                   max(1, int(round(geo.height() * scale))),
                   QImage.Format_RGB32)
    image.fill(Qt.black)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    for screen in screens:
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            continue
        g = screen.geometry()
        target = QRectF((g.x() - geo.x()) * scale, (g.y() - geo.y()) * scale,
                        g.width() * scale, g.height() * scale)
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
    painter.end()

    return image, geo, scale
