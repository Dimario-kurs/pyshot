"""Точка входа PyShot.

Запуск без консоли:  pythonw main.py   (или файл «Скриншотер.bat»)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QSharedMemory  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon  # noqa: E402

from pyshot.app import PyShotApp  # noqa: E402
from pyshot.config import APP_TITLE, Config  # noqa: E402
from pyshot.i18n import set_language, tr  # noqa: E402


def main() -> int:
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
