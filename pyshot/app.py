"""Приложение в системном трее: горячие клавиши, меню, съёмка."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QAction, QBrush, QColor, QGuiApplication, QIcon,
                           QImage, QLinearGradient, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from . import storage
from .capture import grab_screens
from .config import APP_TITLE, Config
from .countdown import Countdown
from .hotkeys import HotkeyManager
from .i18n import set_language, tr
from .overlay import Overlay
from .settings_dialog import SettingsDialog
from .winlist import virtual_origin, visible_windows


def tray_icon() -> QIcon:
    """Иконка приложения: синяя плитка с уголками кадра и красной точкой.

    Одна и та же картинка используется в трее, в заголовках окон и в exe.
    """
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        s = size / 64.0

        # плитка
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#5b9dff"))
        gradient.setColorAt(1, QColor("#1b52c9"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(gradient))
        radius = 13 * s if size >= 32 else 3 * s
        p.drawRoundedRect(QRectF(1.5 * s, 1.5 * s, size - 3 * s, size - 3 * s),
                          radius, radius)

        # уголки кадра
        pen = QPen(QColor("#ffffff"), max(2.0, 5.5 * s))
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        margin = max(3.0, 15 * s)
        arm = max(3.5, 12 * s)
        near, far = margin, size - margin
        for x, y, dx, dy in ((near, near, 1, 1), (far, near, -1, 1),
                             (near, far, 1, -1), (far, far, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + arm * dx, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + arm * dy))

        # точка объектива
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#ff453a")))
        dot = max(1.8, 7 * s)
        p.drawEllipse(QPointF(size / 2, size / 2), dot, dot)
        p.end()
        icon.addPixmap(pm)
    return icon


class PyShotApp(QObject):
    def __init__(self, qapp: QApplication) -> None:
        super().__init__()
        self.qapp = qapp
        self.cfg = Config()
        set_language(self.cfg["language"])
        self.overlay: Overlay | None = None
        self.countdown: Countdown | None = None
        self.last_saved: Path | None = None

        self.icon = tray_icon()
        qapp.setWindowIcon(self.icon)

        # папка «Скриншоты» создаётся сразу при первом запуске
        storage.target_dir(self.cfg)

        # скрытое окно — приёмник сообщений WM_HOTKEY
        self._sink = QWidget()
        self._sink.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self._sink.resize(1, 1)
        self._sink.setAttribute(Qt.WA_DontShowOnScreen, True)
        self._sink.show()

        self.hotkeys = HotkeyManager(int(self._sink.winId()))
        self.hotkeys.triggered.connect(self._on_hotkey)
        qapp.installNativeEventFilter(self.hotkeys)

        self._build_tray()
        self.reload_hotkeys(notify_errors=True)

    # ------------------------------------------------------------------ #
    # трей
    # ------------------------------------------------------------------ #
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.messageClicked.connect(self._on_message_clicked)
        self._build_menu()
        self.tray.show()

    def _build_menu(self) -> None:
        """Меню в трее. Пересобирается заново при смене языка."""
        self.tray.setToolTip(tr(APP_TITLE))
        self.menu = QMenu()

        self.act_region = QAction(tr("Снимок области"), self)
        self.act_region.triggered.connect(self.capture_region)
        self.menu.addAction(self.act_region)

        self.act_full = QAction(tr("Весь экран"), self)
        self.act_full.triggered.connect(self.capture_fullscreen)
        self.menu.addAction(self.act_full)

        self.timer_menu = QMenu(tr("Снимок по таймеру"), self.menu)
        self.menu.addMenu(self.timer_menu)
        self._rebuild_timer_menu()

        self.menu.addSeparator()

        act_folder = QAction(tr("Открыть папку скриншотов"), self)
        act_folder.triggered.connect(
            lambda: storage.open_dir(storage.target_dir(self.cfg)))
        self.menu.addAction(act_folder)

        act_settings = QAction(tr("Настройки…"), self)
        act_settings.triggered.connect(self.open_settings)
        self.menu.addAction(act_settings)

        self.menu.addSeparator()
        act_quit = QAction(tr("Выход"), self)
        act_quit.triggered.connect(self.quit)
        self.menu.addAction(act_quit)

        self.tray.setContextMenu(self.menu)
        self._update_menu_labels()

    def _rebuild_timer_menu(self) -> None:
        self.timer_menu.clear()
        delay = int(self.cfg["delay_seconds"])
        delay = delay if delay > 0 else 3

        for seconds in (3, 5, 10):
            act = QAction(
                tr("Область с таймером — {n} сек").format(n=seconds), self)
            act.setToolTip(
                tr("Появится прошлая рамка: поправьте её и нажмите «Снять»"))
            act.triggered.connect(
                lambda _=False, s=seconds: self.capture_delayed(s, "last"))
            self.timer_menu.addAction(act)

        self.timer_menu.addSeparator()
        act_region = QAction(
            tr("Заморозить экран через {n} сек и выбрать область").format(
                n=delay), self)
        act_region.triggered.connect(
            lambda _=False, s=delay: self.capture_delayed(s, "region"))
        self.timer_menu.addAction(act_region)

        act_full = QAction(
            tr("Весь экран через {n} сек").format(n=delay), self)
        act_full.triggered.connect(
            lambda _=False, s=delay: self.capture_delayed(s, "full"))
        self.timer_menu.addAction(act_full)

    def _update_menu_labels(self) -> None:
        def label(base: str, hotkey: str) -> str:
            return f"{base}\t{hotkey}" if hotkey else base

        self.act_region.setText(label(tr("Снимок области"),
                                      str(self.cfg["hotkey_region"])))
        self.act_full.setText(label(tr("Весь экран"),
                                    str(self.cfg["hotkey_fullscreen"])))
        self.timer_menu.setTitle(
            label(tr("Снимок по таймеру"), str(self.cfg["hotkey_delayed"])))

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.capture_region()

    def _on_message_clicked(self) -> None:
        if self.last_saved and self.last_saved.exists():
            storage.reveal(self.last_saved)

    # ------------------------------------------------------------------ #
    # горячие клавиши
    # ------------------------------------------------------------------ #
    def reload_hotkeys(self, notify_errors: bool = False) -> None:
        self.hotkeys.unregister_all()
        failed = []
        pairs = [
            ("region", self.cfg["hotkey_region"]),
            ("fullscreen", self.cfg["hotkey_fullscreen"]),
            ("delayed", self.cfg["hotkey_delayed"]),
        ]
        for name, combo in pairs:
            if not combo:
                continue
            if not self.hotkeys.register(name, str(combo)):
                failed.append(str(combo))
        self._update_menu_labels()

        if failed and notify_errors:
            QTimer.singleShot(1200, lambda: self.tray.showMessage(
                tr("Горячие клавиши заняты"),
                tr("Не удалось назначить: {keys}").format(
                    keys=", ".join(failed)) +
                tr(".\nСочетание занято другой программой или самой Windows. "
                   "Задайте другое в «Настройках»; снимки при этом работают "
                   "из меню в трее."),
                QSystemTrayIcon.Warning, 9000))

    def _on_hotkey(self, name: str) -> None:
        if name == "region":
            self.capture_region()
        elif name == "fullscreen":
            self.capture_fullscreen()
        elif name == "delayed":
            self.capture_delayed(int(self.cfg["delay_seconds"]), "last")

    # ------------------------------------------------------------------ #
    # съёмка
    # ------------------------------------------------------------------ #
    def window_rects(self, scale: float) -> list:
        """Окна в координатах оверлея — для подсветки под курсором."""
        origin = virtual_origin()
        rects = []
        for rect in visible_windows():
            rects.append(QRectF((rect.x() - origin.x()) / scale,
                                (rect.y() - origin.y()) / scale,
                                rect.width() / scale, rect.height() / scale))
        return rects

    def capture_region(self) -> None:
        if self.overlay is not None:
            return
        image, geo, scale = grab_screens()
        windows = self.window_rects(scale)
        overlay = Overlay(image, geo, scale, self.cfg, windows=windows)
        overlay.saveRequested.connect(self._save)
        overlay.copyRequested.connect(self._copy)
        overlay.closed.connect(self._overlay_closed)
        self.overlay = overlay
        overlay.start()

    def capture_fullscreen(self) -> None:
        if self.overlay is not None:
            return
        image, _geo, _scale = grab_screens()
        self._save(image, False)

    def capture_delayed(self, seconds: int, mode: str = "region") -> None:
        """mode: last — рамка с таймером, region — выбор, full — весь экран."""
        if self.overlay is not None or self.countdown is not None:
            return

        if mode == "last":
            self.open_timer_overlay(seconds)
            return

        notes = {
            "last": tr("снимок запомненной области"),
            "full": tr("снимок всего экрана"),
            "region": tr("потом выделите область"),
        }

        if not self.cfg["show_countdown"]:
            QTimer.singleShot(max(1, int(seconds)) * 1000,
                              lambda: self._delayed_target(mode))
            return

        countdown = Countdown(seconds,
                              notes.get(mode, tr("снимок по таймеру")))
        countdown.finished.connect(lambda: self._countdown_done(mode))
        countdown.cancelled.connect(self._countdown_cancelled)
        self.countdown = countdown
        countdown.start()

    def _countdown_done(self, mode: str) -> None:
        self.countdown = None
        self._delayed_target(mode)

    def _countdown_cancelled(self) -> None:
        self.countdown = None

    def _delayed_target(self, mode: str) -> None:
        if mode == "full":
            self.capture_fullscreen()
        elif mode == "last":
            self.capture_last_region()
        else:
            self.capture_region()

    # -- режим таймера как в macOS -----------------------------------------
    def open_timer_overlay(self, seconds: int) -> None:
        """Показывает прошлую рамку: её можно поправить, дальше — «Снять»."""
        seconds = max(0, int(seconds))
        if int(self.cfg["delay_seconds"]) != seconds:
            self.cfg["delay_seconds"] = seconds
            self.cfg.save()
            self._rebuild_timer_menu()

        image, geo, scale = grab_screens()
        overlay = Overlay(image, geo, scale, self.cfg, mode="timer",
                          delay=seconds, windows=self.window_rects(scale))
        overlay.shootRequested.connect(self._start_timer_shot)
        overlay.closed.connect(self._overlay_closed)
        self.overlay = overlay

        rect = self.last_region()
        if rect is not None:
            overlay.set_selection_from_desktop(rect)
        overlay.start()

    def _start_timer_shot(self, seconds: int) -> None:
        """Запомнили область, убрали окно — и пошёл отсчёт по живому экрану."""
        self._remember_region()
        seconds = max(0, int(seconds))
        if self.overlay is not None:
            self.overlay.close()
        QTimer.singleShot(220, lambda: self._begin_countdown(seconds))

    def _begin_countdown(self, seconds: int) -> None:
        if seconds <= 0:
            # «Таймер: нет» — снимаем сразу, без отсчёта
            self.capture_last_region()
            return
        if not self.cfg["show_countdown"]:
            QTimer.singleShot(seconds * 1000, self.capture_last_region)
            return
        countdown = Countdown(seconds, tr("снимок выбранной области"))
        countdown.finished.connect(lambda: self._countdown_done("last"))
        countdown.cancelled.connect(self._countdown_cancelled)
        self.countdown = countdown
        countdown.start()

    # -- запомненная область ------------------------------------------------
    def last_region(self) -> QRect | None:
        """Последняя выделенная область в координатах рабочего стола."""
        value = self.cfg["last_region"]
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None
        try:
            rect = QRect(int(value[0]), int(value[1]),
                         int(value[2]), int(value[3]))
        except (TypeError, ValueError):
            return None
        return rect if rect.width() >= 4 and rect.height() >= 4 else None

    def _remember_region(self) -> None:
        overlay = self.overlay
        if overlay is None or not overlay.has_selection():
            return
        sel = overlay.selection.normalized()
        origin = overlay.geometry().topLeft()
        self.cfg["last_region"] = [int(round(origin.x() + sel.x())),
                                   int(round(origin.y() + sel.y())),
                                   int(round(sel.width())),
                                   int(round(sel.height()))]
        self.cfg.save()

    def capture_last_region(self) -> None:
        """Снимает запомненную область молча: ни оверлея, ни мыши."""
        rect = self.last_region()
        if rect is None:
            self.capture_region()
            return

        image, geo, scale = grab_screens()
        crop = QRect(int(round((rect.x() - geo.x()) * scale)),
                     int(round((rect.y() - geo.y()) * scale)),
                     int(round(rect.width() * scale)),
                     int(round(rect.height() * scale)))
        crop = crop.intersected(QRect(0, 0, image.width(), image.height()))
        if crop.width() < 2 or crop.height() < 2:
            # экраны переставили — просим выбрать область заново
            self.capture_region()
            return
        self._save(image.copy(crop), False)

    def _overlay_closed(self) -> None:
        overlay, self.overlay = self.overlay, None
        if overlay is not None:
            overlay.deleteLater()
        self.cfg.save()

    # ------------------------------------------------------------------ #
    # действия с изображением
    # ------------------------------------------------------------------ #
    def _save(self, image: QImage, ask: bool) -> None:
        self._remember_region()
        path = storage.save_image(image, self.cfg, ask=ask)
        if path is None:
            return
        self.last_saved = path
        if self.cfg["notify_on_save"]:
            self.tray.showMessage(tr("Скриншот сохранён"), str(path),
                                  self.icon, 3500)

    def _copy(self, image: QImage) -> None:
        self._remember_region()
        storage.copy_image(image)
        if self.cfg["notify_on_save"]:
            self.tray.showMessage(tr("Скриншот скопирован"),
                                  tr("Изображение в буфере обмена, файл не сохранён"),
                                  self.icon, 2500)

    # ------------------------------------------------------------------ #
    def open_settings(self) -> None:
        dialog = SettingsDialog(self.cfg)
        dialog.setWindowIcon(self.icon)
        if dialog.exec():
            set_language(self.cfg["language"])
            self._build_menu()          # меню перерисовываем на новом языке
            self.reload_hotkeys(notify_errors=True)

    def quit(self) -> None:
        self.hotkeys.unregister_all()
        self.cfg.save()
        self.tray.hide()
        self.qapp.quit()
