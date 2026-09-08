"""Распознавание текста на снимке и перевод.

Распознавание — встроенным движком Windows (офлайн, без сторонних программ).
Перевод — через интернет: текст уходит на сервер переводчика, поэтому
функция включается пользователем явно.

Проверить модуль на картинке:
    py -m pyshot.translate путь_к_файлу.png [en] [ru]
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage

# распознавание требует пакетов winrt; без них функция просто недоступна
try:
    import winrt.windows.globalization as _globalization
    import winrt.windows.media.ocr as _ocr
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage import FileAccessMode, StorageFile

    OCR_AVAILABLE = True
except Exception:                                   # pragma: no cover
    OCR_AVAILABLE = False

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")

# Кириллические буквы, неотличимые по начертанию от латинских. Если слово
# целиком из них — вероятно, это латинское слово, прочитанное русским
# движком: «ту» вместо «my», «саг» вместо «car», «оп» вместо «on».
HOMOGLYPHS = set("аАвВеЕгГиИкКмМнНоОпПрРсСтТуУхХ")

# Настоящие русские слова, целиком состоящие из букв-двойников. Их подменять
# нельзя, иначе «нет» превратится в мусор, который английский движок увидел
# на том же месте.
RUSSIAN_WORDS = {
    "он", "она", "оно", "они", "нет", "как", "так", "там", "тут", "тот",
    "это", "эти", "все", "всё", "уже", "нас", "вас", "нам", "вам", "мне",
    "тем", "тот", "три", "сто", "раз", "мир", "рот", "сон", "кот", "нос",
    "рис", "сор", "тон", "рок", "мех", "век", "суп", "мост", "тест", "спорт",
    "март", "сорт", "торт", "метр", "мама", "папа", "рука", "нора", "вера",
    "мера", "пора", "парк", "карта", "марка", "и", "в", "к", "с", "у", "о",
    "а", "не", "на", "по", "от", "то", "но", "он", "их", "мы", "вы", "их",
}


def _case_shape(word: str) -> str:
    """Как написано слово: строчными, с заглавной, капсом или вперемешку."""
    letters = [c for c in word if c.isalpha()]
    if not letters:
        return "none"
    if word == word.lower():
        return "lower"
    if word == word.upper():
        return "upper"
    if word == word.capitalize():
        return "title"
    return "mixed"


def _case_matches(russian: str, latin: str) -> bool:
    """Регистр подмены должен совпасть с исходным.

    Английский движок, читая строчную кириллицу, выдаёт капс: «сниму»
    превращается в «CHVIMY», «нет» — в «HeT». Настоящая же подмена
    сохраняет вид слова: «ту» → «my», «саг» → «car».
    """
    shape = _case_shape(latin)
    if shape == "mixed" or shape == "none":
        return False
    return shape == _case_shape(russian)

# сколько блоков переводим за раз — защита от случайного снимка всего экрана
MAX_BLOCKS = 40
REQUEST_TIMEOUT = 12


@dataclass
class Line:
    """Строка, найденная распознавателем."""
    text: str
    rect: QRectF


@dataclass
class Block:
    """Абзац: несколько строк подряд, переводится целиком."""
    lines: list = field(default_factory=list)
    translation: str = ""

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines).strip()

    @property
    def rect(self) -> QRectF:
        rect = QRectF(self.lines[0].rect)
        for line in self.lines[1:]:
            rect = rect.united(line.rect)
        return rect

    @property
    def line_height(self) -> float:
        heights = [line.rect.height() for line in self.lines]
        return sum(heights) / len(heights) if heights else 0.0


# --------------------------------------------------------------------------
# распознавание
# --------------------------------------------------------------------------
def available_languages() -> list[str]:
    """Языки распознавания, установленные в Windows: ['en-US', 'ru']."""
    if not OCR_AVAILABLE:
        return []
    try:
        return [lang.language_tag
                for lang in _ocr.OcrEngine.available_recognizer_languages]
    except Exception:
        return []


def _engine(tag: str):
    try:
        return _ocr.OcrEngine.try_create_from_language(
            _globalization.Language(tag))
    except Exception:
        return None


async def _recognize_file(path: str, tag: str):
    engine = _engine(tag)
    if engine is None:
        return None
    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    return await engine.recognize_async(bitmap)


def _score(text: str, tag: str) -> int:
    """Насколько результат похож на выбранный язык."""
    if tag.startswith("ru"):
        return len(CYRILLIC.findall(text))
    return len(LATIN.findall(text))


def _words_of(result) -> list:
    """Слова с их прямоугольниками — из ответа распознавателя."""
    words = []
    for ocr_line in result.lines:
        for word in ocr_line.words:
            box = word.bounding_rect
            words.append((QRectF(box.x, box.y, box.width, box.height),
                          word.text))
    return words


def _same_place(first: QRectF, second: QRectF) -> bool:
    """Один ли это участок картинки: сравниваем по перекрытию."""
    overlap = first.intersected(second)
    if overlap.isEmpty():
        return False
    smaller = min(first.width() * first.height(),
                  second.width() * second.height()) or 1.0
    return (overlap.width() * overlap.height()) / smaller > 0.55


def _looks_latin(word: str) -> bool:
    """Слово из одних латинских букв — без цифр и мусора."""
    letters = [c for c in word if c.isalpha()]
    return bool(letters) and all(c in "abcdefghijklmnopqrstuvwxyz"
                                 "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in letters) \
        and all(c.isalpha() or c in "'-." for c in word)


def _mistaken_latin(word: str) -> bool:
    """Похоже, что латинское слово прочитано кириллицей: «ту» вместо «my»."""
    letters = [c for c in word if c.isalpha()]
    if not letters or not any(CYRILLIC.match(c) for c in letters):
        return False
    if word.strip(".,:;!?()[]\"'").lower() in RUSSIAN_WORDS:
        return False                    # настоящее русское слово, не трогаем
    return all(c in HOMOGLYPHS for c in letters)


def _is_latin_word(word: str) -> bool:
    """В слове нет ни одной кириллической буквы — значит оно латинское."""
    return bool(word) and not any(CYRILLIC.match(c) for c in word if c.isalpha())


def _merge_readings(base: list, latin: list) -> list:
    """Русское чтение — основа, но латинские слова берём у английского движка.

    Заменяем в двух случаях: слово-обманка целиком из букв-двойников
    («ту» вместо «my») и слово, где кириллицы нет вовсе — такое английский
    движок читает точнее («antjfreeze» против «antifreeze»).
    """
    merged = []
    for rect, text in base:
        if _mistaken_latin(text) or _is_latin_word(text):
            for other_rect, other_text in latin:
                if (_same_place(rect, other_rect) and _looks_latin(other_text)
                        and _case_matches(text, other_text)):
                    text = other_text
                    break
        merged.append((rect, text))
    return merged


def recognize(image: QImage, language: str = "auto") -> tuple[list, str]:
    """Возвращает (строки, выбранный язык). Координаты — в пикселях снимка."""
    if not OCR_AVAILABLE:
        raise RuntimeError("Распознавание недоступно: не установлены пакеты winrt")

    installed = available_languages()
    if not installed:
        raise RuntimeError("В Windows не установлен ни один язык распознавания")

    if language == "auto":
        candidates = installed
    else:
        candidates = [tag for tag in installed
                      if tag.lower().startswith(language.lower())] or installed

    handle, temp_path = tempfile.mkstemp(prefix="pyshot-ocr-", suffix=".png")
    os.close(handle)
    try:
        image.save(temp_path, "PNG")

        results = {}
        for tag in candidates:
            result = asyncio.run(_recognize_file(temp_path, tag))
            if result is not None:
                results[tag] = result
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    if not results:
        return [], candidates[0]

    # Основной движок выбираем не по количеству букв, а по алфавиту:
    # английский не умеет выводить кириллицу и превращает её в мусор,
    # русский же читает и латиницу — пусть с огрехами, но читает.
    russian = next((tag for tag in results if tag.startswith("ru")), None)
    english = next((tag for tag in results if not tag.startswith("ru")), None)

    if russian and len(CYRILLIC.findall(results[russian].text or "")) >= 3:
        best_tag = russian
    elif english:
        best_tag = english
    else:
        best_tag = next(iter(results))

    best = results[best_tag]
    fixes = {}
    if best_tag == russian and english:
        merged = _merge_readings(_words_of(best), _words_of(results[english]))
        fixes = {(round(rect.x()), round(rect.y())): text
                 for rect, text in merged}

    lines = []
    for ocr_line in best.lines:
        words = list(ocr_line.words)
        if not words:
            continue
        rect = None
        pieces = []
        for word in words:
            box = word.bounding_rect
            piece = QRectF(box.x, box.y, box.width, box.height)
            rect = piece if rect is None else rect.united(piece)
            pieces.append(fixes.get((round(box.x), round(box.y)), word.text))
        lines.append(Line(text=" ".join(pieces), rect=rect))
    return lines, best_tag


# --------------------------------------------------------------------------
# группировка строк в абзацы
# --------------------------------------------------------------------------
def group_lines(lines: list) -> list:
    """Соседние строки одного абзаца объединяем, чтобы перевод был связным."""
    if not lines:
        return []

    ordered = sorted(lines, key=lambda ln: (ln.rect.top(), ln.rect.left()))
    blocks = [Block(lines=[ordered[0]])]

    for line in ordered[1:]:
        previous = blocks[-1].lines[-1]
        gap = line.rect.top() - previous.rect.bottom()
        height = max(previous.rect.height(), line.rect.height())

        # горизонтальное перекрытие: строки одного абзаца стоят друг под другом
        left = max(previous.rect.left(), line.rect.left())
        right = min(previous.rect.right(), line.rect.right())
        overlap = max(0.0, right - left)
        narrower = min(previous.rect.width(), line.rect.width()) or 1.0

        # распознаватель отдаёт рамку по самим буквам, поэтому между строками
        # одного абзаца остаётся просвет порядка их высоты
        same_block = (gap < height * 1.6 and overlap > narrower * 0.35)
        if same_block:
            blocks[-1].lines.append(line)
        else:
            blocks.append(Block(lines=[line]))
    return blocks


# --------------------------------------------------------------------------
# перевод
# --------------------------------------------------------------------------
def translate_text(text: str, source: str, target: str,
                   provider: str = "google", key: str = "") -> str:
    """Переводит одну порцию текста. Бросает исключение при ошибке сети."""
    text = text.strip()
    if not text:
        return ""
    if provider == "deepl":
        return _translate_deepl(text, source, target, key)
    if provider == "azure":
        return _translate_azure(text, source, target, key)
    return _translate_google(text, source, target)


def _translate_google(text: str, source: str, target: str) -> str:
    url = ("https://translate.googleapis.com/translate_a/single"
           f"?client=gtx&sl={source or 'auto'}&tl={target}&dt=t&q="
           + urllib.parse.quote(text))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        data = json.load(response)
    return "".join(part[0] for part in data[0] if part and part[0])


def _translate_deepl(text: str, source: str, target: str, key: str) -> str:
    if not key:
        raise RuntimeError("Для DeepL нужен ключ API в настройках")
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    payload = {"text": text, "target_lang": target.upper()}
    if source and source != "auto":
        payload["source_lang"] = source.upper()
    request = urllib.request.Request(
        f"https://{host}/v2/translate",
        data=urllib.parse.urlencode(payload).encode(),
        headers={"Authorization": f"DeepL-Auth-Key {key}"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        data = json.load(response)
    return data["translations"][0]["text"]


def _translate_azure(text: str, source: str, target: str, key: str) -> str:
    if not key:
        raise RuntimeError("Для Azure нужен ключ API в настройках")
    key, _, region = key.partition("|")
    url = ("https://api.cognitive.microsofttranslator.com/translate"
           f"?api-version=3.0&to={target}")
    if source and source != "auto":
        url += f"&from={source}"
    headers = {"Ocp-Apim-Subscription-Key": key,
               "Content-Type": "application/json"}
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region
    request = urllib.request.Request(
        url, data=json.dumps([{"Text": text}]).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        data = json.load(response)
    return data[0]["translations"][0]["text"]


# --------------------------------------------------------------------------
# всё вместе
# --------------------------------------------------------------------------
def translate_image(image: QImage, source: str = "auto", target: str = "ru",
                    provider: str = "google", key: str = "") -> list:
    """Распознаёт снимок и переводит найденные абзацы."""
    lines, detected = recognize(image, source)
    blocks = group_lines(lines)[:MAX_BLOCKS]

    # Язык распознавания ничего не решает: в тексте может быть намешано
    # два алфавита. Смотрим на сам текст блока.
    #
    # Автоопределение здесь вредит: на смешанном тексте переводчик видит
    # кириллицу, объявляет его русским и возвращает без изменений. Поэтому
    # прямо указываем чужой для нас язык — тогда английское переводится,
    # а русское остаётся как было.
    if source == "auto":
        source = "en" if target.lower().startswith("ru") else "ru"
    else:
        source = source.split("-")[0]
    for block in blocks:
        if needs_translation(block.text, target):
            block.translation = translate_text(block.text, source, target,
                                               provider, key)
        else:
            block.translation = ""
    return blocks


def needs_translation(text: str, target: str) -> bool:
    """Есть ли в тексте слова на чужом для целевого языка алфавите."""
    cyrillic = len(CYRILLIC.findall(text))
    latin = len(LATIN.findall(text))
    if target.lower().startswith("ru"):
        foreign, native = latin, cyrillic
    else:
        foreign, native = cyrillic, latin
    if foreign < 3:
        return False
    return foreign >= max(3, (foreign + native) * 0.15)


# --------------------------------------------------------------------------
if __name__ == "__main__":                          # ручная проверка
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    path = Path(sys.argv[1])
    src = sys.argv[2] if len(sys.argv) > 2 else "auto"
    dst = sys.argv[3] if len(sys.argv) > 3 else "ru"

    print("языки распознавания:", ", ".join(available_languages()) or "нет")
    picture = QImage(str(path))
    if picture.isNull():
        print("не удалось открыть файл")
        raise SystemExit(1)
    print(f"картинка: {picture.width()}x{picture.height()}")

    found, language = recognize(picture, src)
    print(f"распознано строк: {len(found)}, язык: {language}\n")
    for block in group_lines(found):
        rect = block.rect
        print(f"[{int(rect.x()):>4},{int(rect.y()):>4} "
              f"{int(rect.width()):>4}x{int(rect.height()):>3}] {block.text}")
        if needs_translation(block.text, dst):
            foreign = "en" if dst.startswith("ru") else "ru"
            print(f"      -> {translate_text(block.text, foreign, dst)}")
        else:
            print("      (перевод не нужен — текст уже на целевом языке)")
