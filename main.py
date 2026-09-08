"""Точка входа PyShot.

Запуск без консоли:  pythonw main.py   (или файл «Скриншотер.bat»)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QSharedMemory  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon  # noqa: E402

from pyshot.app import PyShotApp  # noqa: E402
from pyshot.config import APP_TITLE, Config  # noqa: E402
from pyshot.i18n import set_language, tr  # noqa: E402


def selftest() -> int:
    """Отчёт о состоянии программы: PyShot.exe --selftest.

    Пишет файл в папку временных файлов и открывает его. Нужен, когда
    что-то не работает и надо понять, чего не хватает.
    """
    import platform
    import tempfile
    from datetime import datetime

    from pyshot import __version__
    from pyshot.config import Config, config_path

    lines = [f"PyShot {__version__} — самопроверка",
             datetime.now().strftime("%d.%m.%Y %H:%M"),
             f"Windows: {platform.platform()}",
             f"Python: {sys.version.split()[0]}",
             f"собранный exe: {'да' if getattr(sys, 'frozen', False) else 'нет'}",
             f"программа: {sys.executable}",
             f"настройки: {config_path()}", ""]

    try:
        from pyshot import translate

        lines.append(f"распознавание текста доступно: "
                     f"{'да' if translate.OCR_AVAILABLE else 'нет'}")
        languages = translate.available_languages()
        lines.append(f"языки распознавания: {', '.join(languages) or 'нет'}")
        if not languages:
            lines.append("  установите языковой пакет: Параметры → "
                         "Время и язык → Язык и регион")
    except Exception as error:
        lines.append(f"распознавание не работает: {error}")

    try:
        cfg = Config()
        lines.append(f"перевод разрешён: "
                     f"{'да' if cfg['translate_enabled'] else 'нет'}")
        lines.append(f"сервис перевода: {cfg['translate_provider']}")
    except Exception as error:
        lines.append(f"настройки не читаются: {error}")

    report = Path(tempfile.gettempdir()) / "pyshot-selftest.txt"
    report.write_text("\n".join(lines), encoding="utf-8")
    try:
        os.startfile(str(report))                   # noqa: S606
    except Exception:
        pass
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    app = QApplication(sys.argv)
    set_language(Config()["language"])
    app.setApplicationName("PyShot")
    app.setApplicationDisplayName(tr(APP_TITLE))
    app.setQuitOnLastWindowClosed(False)

    # только один экземпляр
    lock = QSharedMemory("PyShot_single_instance_v1")
    if not lock.create(1):
        QMessageBox.information(
            None, tr(APP_TITLE),
            tr("PyShot уже запущен — значок находится в области "
               "уведомлений (системном трее)."))
        return 0

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None, tr(APP_TITLE),
            tr("Системный трей недоступен, программа не может работать "
               "в фоне."))
        return 1

    pyshot = PyShotApp(app)
    app.setProperty("_pyshot_keepalive", True)
    globals()["_instances"] = (pyshot, lock)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
