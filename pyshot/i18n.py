"""Двуязычный интерфейс: русский и английский.

В коде остаются русские строки — они же служат ключами. Функция tr()
подменяет их английскими, когда выбран английский язык.
"""

from __future__ import annotations

_current = "ru"

EN = {
    # -- общее -------------------------------------------------------------
    "PyShot — скриншоты": "PyShot — screenshots",

    # -- меню в трее -------------------------------------------------------
    "Снимок области": "Capture area",
    "Весь экран": "Full screen",
    "Снимок по таймеру": "Timed capture",
    "Область с таймером — {n} сек": "Area with timer — {n} s",
    "Появится прошлая рамка: поправьте её и нажмите «Снять»":
        "The previous frame appears: adjust it and press “Capture”",
    "Заморозить экран через {n} сек и выбрать область":
        "Freeze the screen in {n} s, then pick an area",
    "Весь экран через {n} сек": "Full screen in {n} s",
    "Открыть папку скриншотов": "Open screenshots folder",
    "Настройки…": "Settings…",
    "Выход": "Quit",

    # -- уведомления -------------------------------------------------------
    "Горячие клавиши заняты": "Hotkeys are taken",
    "Не удалось назначить: {keys}": "Could not assign: {keys}",
    ".\nСочетание занято другой программой или самой Windows. "
    "Задайте другое в «Настройках»; снимки при этом работают "
    "из меню в трее.":
        ".\nThe shortcut is used by another program or by Windows itself. "
        "Set a different one in Settings; capturing still works "
        "from the tray menu.",
    "Скриншот сохранён": "Screenshot saved",
    "Скриншот скопирован": "Screenshot copied",
    "Изображение в буфере обмена, файл не сохранён":
        "The image is in the clipboard, no file was saved",

    # -- обратный отсчёт ---------------------------------------------------
    "снимок по таймеру": "timed capture",
    "снимок запомненной области": "capturing the saved area",
    "снимок выбранной области": "capturing the selected area",
    "снимок всего экрана": "capturing the whole screen",
    "потом выделите область": "then select an area",
    "клик — отмена": "click to cancel",

    # -- окно выделения ----------------------------------------------------
    "Кликните по окну — снимется оно целиком,\n"
    "либо выделите область мышью\n"
    "Ctrl+A — весь экран      Esc — отмена":
        "Click a window to capture it whole,\n"
        "or drag to select an area\n"
        "Ctrl+A — full screen      Esc — cancel",
    "Кликните по окну или выделите область — снимок {when}\n"
    "Ctrl+A — весь экран      Esc — отмена":
        "Click a window or select an area — the shot is taken {when}\n"
        "Ctrl+A — full screen      Esc — cancel",
    "сразу по кнопке «Снять»": "as soon as you press “Capture”",
    "через {n} сек после кнопки «Снять»":
        "{n} s after you press “Capture”",

    # -- панели инструментов ----------------------------------------------
    "Карандаш": "Pencil",
    "Линия": "Line",
    "Стрелка": "Arrow",
    "Прямоугольник": "Rectangle",
    "Маркер": "Marker",
    "Текст": "Text",
    "Цвет и толщина линии": "Colour and line width",
    "Отменить (Ctrl+Z)": "Undo (Ctrl+Z)",
    "Копировать в буфер (Ctrl+C)": "Copy to clipboard (Ctrl+C)",
    "Сохранить (Ctrl+S / Enter)": "Save (Ctrl+S / Enter)",
    "Закрыть (Esc)": "Close (Esc)",
    "Другой цвет…": "Other colour…",
    "Цвет инструмента": "Tool colour",
    "Толщина": "Width",
    "Через сколько секунд сделать снимок":
        "How many seconds before the shot",
    "Без таймера — снять сразу": "No timer — capture right away",
    "{n} секунды": "{n} seconds",
    "{n} секунд": "{n} seconds",
    "Таймер: нет": "Timer: off",
    "Таймер: {n} с": "Timer: {n} s",
    "Снять": "Capture",
    "Отмена (Esc)": "Cancel (Esc)",

    # -- настройки ---------------------------------------------------------
    "Настройки PyShot": "PyShot settings",
    "Сохранить": "Save",
    "Отмена": "Cancel",
    "Язык / Language": "Language / Язык",
    "Язык интерфейса:": "Interface language:",
    "Сохранение": "Saving",
    "Обзор…": "Browse…",
    "Папка для скриншотов:": "Screenshots folder:",
    "Формат файла:": "File format:",
    "Качество JPEG:": "JPEG quality:",
    "Шаблон имени:": "Name template:",
    "Шаблон даты в стиле strftime:\n"
    "%Y — год, %m — месяц, %d — день, %H:%M:%S — время":
        "Date template, strftime style:\n"
        "%Y — year, %m — month, %d — day, %H:%M:%S — time",
    "Например: screenshot_%Y-%m-%d_%H-%M-%S":
        "For example: screenshot_%Y-%m-%d_%H-%M-%S",
    "Копировать в буфер обмена при сохранении":
        "Copy to clipboard when saving",
    "Открывать папку после сохранения": "Open the folder after saving",
    "Показывать уведомление о сохранении": "Show a notification when saved",
    "Цвета в файле:": "Colours in the file:",
    "как на экране (профиль монитора)": "same as on screen (monitor profile)",
    "стандартный sRGB": "standard sRGB",
    "не указывать": "none",
    "Чем помечать цвета в файле.\n"
    "«Как на экране» — снимок выглядит точно так же, как монитор "
    "показывал оригинал.\n"
    "«sRGB» — привычный вариант для отправки другим людям.":
        "Which colour profile to tag the file with.\n"
        "“Same as on screen” — the shot looks exactly as the monitor "
        "showed the original.\n"
        "“sRGB” — the usual choice when sending files to other people.",
    "Горячие клавиши": "Hotkeys",
    "Снимок области:": "Capture area:",
    "Весь экран:": "Full screen:",
    "Снимок по таймеру:": "Timed capture:",
    "Кликните в поле и нажмите нужное сочетание. Backspace — очистить.":
        "Click the field and press the shortcut you want. "
        "Backspace clears it.",
    "нажмите сочетание…": "press a shortcut…",
    "Таймер и запуск": "Timer and startup",
    " сек": " s",
    "Задержка по умолчанию:": "Default delay:",
    "Показывать обратный отсчёт": "Show the countdown",
    "Запускать вместе с Windows": "Start with Windows",
    "Куда сохранять скриншоты": "Where to save screenshots",

    # -- файлы -------------------------------------------------------------
    "Сохранить скриншот": "Save screenshot",

    # -- запуск ------------------------------------------------------------
    "PyShot уже запущен — значок находится в области уведомлений "
    "(системном трее).":
        "PyShot is already running — look for its icon in the "
        "notification area (system tray).",
    "Системный трей недоступен, программа не может работать в фоне.":
        "The system tray is unavailable, the program cannot run in "
        "the background.",
}


def set_language(code: str) -> None:
    global _current
    _current = "en" if str(code).lower().startswith("en") else "ru"


def language() -> str:
    return _current


def tr(text: str) -> str:
    """Перевод строки. Неизвестные строки возвращаются как есть."""
    if _current == "en":
        return EN.get(text, text)
    return text
