"""Слой перевода поверх снимка: подложки с переведённым текстом.

Google в своём переводчике стирает исходные буквы нейросетью и дорисовывает
фон. Такой модели у нас нет, поэтому идём проще: на скриншотах фон под
текстом почти всегда однотонный — закрашиваем прямоугольник его же цветом
и пишем перевод сверху. Цвета подложки и букв берём из самой картинки.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter

MIN_FONT = 6.0
PAD = 3.0


@dataclass
class TranslatedBlock:
    """Готовый к отрисовке абзац: координаты уже в системе оверлея."""
    rect: QRectF
    text: str
    background: QColor
    foreground: QColor
    font_size: float
    inline: bool = False        # вставка внутри чужой строки


# --------------------------------------------------------------------------
# цвета берём из самой картинки
# --------------------------------------------------------------------------
def _samples(image: QImage, rect: QRectF, limit: int = 900) -> list:
    """Равномерная выборка пикселей внутри прямоугольника."""
    left, top = max(0, int(rect.left())), max(0, int(rect.top()))
    right = min(image.width() - 1, int(rect.right()))
    bottom = min(image.height() - 1, int(rect.bottom()))
    if right <= left or bottom <= top:
        return []

    width, height = right - left, bottom - top
    step = max(1, int(((width * height) / limit) ** 0.5))
    colours = []
    for y in range(top, bottom + 1, step):
        for x in range(left, right + 1, step):
            colours.append(QColor(image.pixel(x, y)))
    return colours


def _median_colour(colours: list) -> QColor:
    if not colours:
        return QColor("#ffffff")
    reds = sorted(c.red() for c in colours)
    greens = sorted(c.green() for c in colours)
    blues = sorted(c.blue() for c in colours)
    middle = len(colours) // 2
    return QColor(reds[middle], greens[middle], blues[middle])


def _distance(a: QColor, b: QColor) -> float:
    return ((a.red() - b.red()) ** 2 + (a.green() - b.green()) ** 2
            + (a.blue() - b.blue()) ** 2) ** 0.5


def estimate_colours(image: QImage, rect: QRectF) -> tuple:
    """Возвращает (цвет фона, цвет букв) для области с текстом."""
    # фон ищем в рамке вокруг текста: там букв заведомо нет
    outer = rect.adjusted(-rect.height() * 0.4, -rect.height() * 0.35,
                          rect.height() * 0.4, rect.height() * 0.35)
    inside = _samples(image, rect)

    # берём пиксели рамки: те, что лежат вне прямоугольника текста
    ring = []
    left, top = max(0, int(outer.left())), max(0, int(outer.top()))
    right = min(image.width() - 1, int(outer.right()))
    bottom = min(image.height() - 1, int(outer.bottom()))
    step = max(1, int(((max(1, right - left) * max(1, bottom - top)) / 700) ** 0.5))
    for y in range(top, bottom + 1, step):
        for x in range(left, right + 1, step):
            if not rect.contains(QPointF(x, y)):
                ring.append(QColor(image.pixel(x, y)))

    background = _median_colour(ring or inside)

    # буквы — самые далёкие от фона пиксели внутри рамки текста
    if inside:
        # сглаженные края букв дают промежуточные оттенки, поэтому берём
        # медиану небольшой доли самых контрастных пикселей
        inside.sort(key=lambda c: _distance(c, background), reverse=True)
        foreground = _median_colour(inside[:max(1, len(inside) // 20)])
    else:
        foreground = QColor("#000000")

    # если контраст вышел никакой — берём чёрный или белый по яркости фона
    if _distance(foreground, background) < 60:
        light = background.lightness() > 128
        foreground = QColor("#101010") if light else QColor("#f5f5f5")
    return background, foreground


# --------------------------------------------------------------------------
# подбор размера шрифта
# --------------------------------------------------------------------------
def fit_font_size(text: str, rect: QRectF, start: float) -> float:
    """Наибольший размер, при котором перевод влезает в прямоугольник.

    Ширину проверяем отдельно: перенос по словам не разрывает длинное слово
    вроде «фотографии», и оно вылезает за подложку, а лишнее обрезается.
    """
    width = rect.width() - PAD * 2
    size = max(MIN_FONT, start)
    font = QFont()
    while size > MIN_FONT:
        font.setPointSizeF(size)
        metrics = QFontMetricsF(font)
        needed = metrics.boundingRect(QRectF(0, 0, width, 10000),
                                      Qt.TextWordWrap, text)
        if needed.height() <= rect.height() - PAD and needed.width() <= width:
            return size
        size -= 0.5
    return MIN_FONT


# --------------------------------------------------------------------------
# сборка и отрисовка
# --------------------------------------------------------------------------
def build_layer(image: QImage, blocks: list, scale: float,
                origin: QPointF, right_edge: float | None = None) -> list:
    """Переводит координаты распознавания в координаты оверлея.

    image  — вырезанная область в пикселях снимка (та же, что уходила в OCR);
    scale  — множитель HiDPI: пиксели снимка = логические × scale;
    origin — левый верхний угол выделения в координатах оверлея.
    """
    layer = []
    if right_edge is None:
        right_edge = origin.x() + image.width() / scale
    for block in blocks:
        if not block.translation:
            continue
        source = block.rect
        background, foreground = estimate_colours(image, source)

        rect = QRectF(origin.x() + source.left() / scale,
                      origin.y() + source.top() / scale,
                      source.width() / scale, source.height() / scale)
        # Распознаватель даёт рамку по самим буквам, без места под выносные
        # элементы, а шрифт эту высоту требует. Не добавив запас, мы бы
        # мельчили кегль там, где текст на самом деле помещается.
        air = (block.line_height / scale) * 0.2
        rect = rect.adjusted(-PAD, -PAD - air, PAD, PAD + air)

        # исходный кегль прикидываем по высоте строки
        start = max(MIN_FONT, (block.line_height / scale) * 0.78)
        size = fit_font_size(block.translation, rect, start)

        # Перевод на русский длиннее оригинала: прежде чем мельчить шрифт,
        # пробуем расширить подложку вправо. Вставке внутри чужой строки
        # разбегаться некуда — справа стоит соседнее слово, и закрасить его
        # нельзя, поэтому ей достаётся только небольшой запас.
        inline = getattr(block, "inline", False)
        if size < start * 0.9:
            limit = rect.width() * 0.9
            free = getattr(block, "room", -1.0)
            if inline and free >= 0:
                limit = free / scale - PAD     # ровно до соседнего слова
            room = min(right_edge - rect.right() - 4, limit)
            if room > 10:
                rect.setWidth(rect.width() + room)
                size = fit_font_size(block.translation, rect, start)

        # если даже минимальный кегль не влез — растим подложку вниз
        font = QFont()
        font.setPointSizeF(size)
        needed = QFontMetricsF(font).boundingRect(
            QRectF(0, 0, rect.width() - PAD * 2, 10000),
            Qt.TextWordWrap, block.translation)
        if needed.height() > rect.height():
            # вставка не имеет права накрыть строку снизу
            grown = needed.height() + PAD * 2
            rect.setHeight(min(grown, rect.height() * 1.7) if inline else grown)

        layer.append(TranslatedBlock(rect=rect, text=block.translation,
                                     background=background,
                                     foreground=foreground, font_size=size,
                                     inline=inline))
    return _even_out_sizes(layer)


def _even_out_sizes(layer: list) -> list:
    """Строки одного размера должны и в переводе выглядеть одинаково.

    Иначе в меню соседние пункты получают кегль 9 и 11.5 — вроде мелочь,
    а выглядит неряшливо. Внутри группы близких по высоте строк берём
    наименьший подошедший размер: так влезут все.
    """
    # Высота рамки от строки к строке гуляет: у «Google Drive» есть хвост
    # буквы g, у «Add folder» нет. Поэтому сравниваем не абсолютные высоты,
    # а отношение к типичной: всё в пределах полутора раз — один размер.
    if not layer:
        return layer

    import math

    heights = sorted(block.rect.height() for block in layer)
    typical = heights[len(heights) // 2] or 1.0

    groups = {}
    for block in layer:
        if block.inline:
            continue                          # вставку равнять не с чем
        ratio = max(0.1, block.rect.height() / typical)
        key = round(math.log(ratio, 1.5))
        groups.setdefault(key, []).append(block)

    for blocks in groups.values():
        if len(blocks) < 2:
            continue
        smallest = min(block.font_size for block in blocks)
        for block in blocks:
            if block.font_size != smallest:
                block.font_size = smallest
                font = QFont()
                font.setPointSizeF(smallest)
                needed = QFontMetricsF(font).boundingRect(
                    QRectF(0, 0, block.rect.width() - PAD * 2, 10000),
                    Qt.TextWordWrap, block.text)
                if needed.height() > block.rect.height():
                    block.rect.setHeight(needed.height() + PAD * 2)
    return layer


def draw_layer(painter: QPainter, layer: list) -> None:
    """Рисует подложки с переводом. Вызывается из paintEvent оверлея."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    for block in layer:
        painter.setPen(Qt.NoPen)
        painter.setBrush(block.background)
        painter.drawRoundedRect(block.rect, 3, 3)

        font = QFont()
        font.setPointSizeF(block.font_size)
        painter.setFont(font)
        painter.setPen(block.foreground)
        painter.drawText(block.rect.adjusted(PAD, 0, -PAD, 0),
                         Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                         block.text)
    painter.restore()
