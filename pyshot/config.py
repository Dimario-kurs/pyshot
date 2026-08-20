"""Настройки приложения: загрузка/сохранение в %APPDATA%\\PyShot\\config.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "PyShot"
APP_TITLE = "PyShot — скриншоты"


def desktop_dir() -> Path:
    """Рабочий стол текущего пользователя (учитывает перенос в OneDrive)."""
    if sys.platform == "win32":
        try:
            import winreg

            key_path = (r"Software\Microsoft\Windows\CurrentVersion"
                        r"\Explorer\Shell Folders")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "Desktop")
            path = Path(os.path.expandvars(value))
            if path.exists():
                return path
        except Exception:
            pass
    return Path.home() / "Desktop"


DEFAULT_SAVE_DIR = str(desktop_dir() / "Скриншоты")
LEGACY_SAVE_DIRS = {
    str(Path.home() / "Pictures" / "PyShot"),
    str(Path.home() / "Pictures" / "PyShot").replace("\\", "/"),
}

DEFAULTS = {
    # язык интерфейса: ru | en
    "language": "ru",
    # куда и как сохранять
    "save_dir": DEFAULT_SAVE_DIR,
    "file_format": "png",                       # png | jpg
    "jpg_quality": 92,
    "filename_template": "screenshot_%Y-%m-%d_%H-%M-%S",
    "copy_to_clipboard_on_save": True,
    "open_folder_after_save": False,
    "notify_on_save": True,
    # чем помечать файл: monitor — профилем экрана (картинка выглядит
    # так же, как на мониторе), srgb — стандартным, none — ничем
    "color_profile": "monitor",
    # горячие клавиши
    "hotkey_region": "Ctrl+4",
    "hotkey_fullscreen": "Ctrl+5",
    "hotkey_delayed": "Ctrl+6",
    # съёмка по таймеру
    "delay_seconds": 3,
    "show_countdown": True,
    # инструменты рисования
    "pen_color": "#ff3b30",
    "pen_width": 3,
    "font_size": 18,
    # последняя выделенная область (для снимка по таймеру): [x, y, w, h]
    "last_region": None,
    # прочее
    "autostart": False,
}


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


class Config:
    """Словарь настроек с автосохранением на диск."""

    def __init__(self) -> None:
        self._data = dict(DEFAULTS)
        self.load()

    # -- доступ ------------------------------------------------------------
    def __getitem__(self, key: str):
        return self._data.get(key, DEFAULTS.get(key))

    def __setitem__(self, key: str, value) -> None:
        self._data[key] = value

    def get(self, key: str, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def update(self, values: dict) -> None:
        self._data.update(values)

    def as_dict(self) -> dict:
        return dict(self._data)

    # -- диск --------------------------------------------------------------
    def load(self) -> None:
        path = config_path()
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    # берём только известные ключи, остальное игнорируем
                    for key in DEFAULTS:
                        if key in data:
                            self._data[key] = data[key]
            # старая папка по умолчанию -> новая «Скриншоты» на рабочем столе
            if self._data.get("save_dir") in LEGACY_SAVE_DIRS:
                self._data["save_dir"] = DEFAULT_SAVE_DIR
        except Exception:
            # битый конфиг не должен ронять приложение
            pass

    def save(self) -> None:
        path = config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # -- автозапуск --------------------------------------------------------
    def apply_autostart(self) -> None:
        """Прописывает/убирает приложение в автозагрузке текущего пользователя."""
        if sys.platform != "win32":
            return
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as key:
                if self["autostart"]:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                                      autostart_command())
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except Exception:
            pass


def autostart_command() -> str:
    """Команда запуска без консольного окна."""
    if getattr(sys, "frozen", False):
        # собранный PyShot.exe запускает сам себя
        return f'"{Path(sys.executable)}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else exe
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{runner}" "{main_py}"'
