"""Окно настроек."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from .hotkeys import parse_hotkey
from .i18n import tr

SPECIAL_KEYS = {
    Qt.Key_Print: "PrintScreen",
    Qt.Key_Insert: "Insert",
    Qt.Key_Delete: "Delete",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_PageUp: "PageUp",
    Qt.Key_PageDown: "PageDown",
    Qt.Key_Space: "Space",
    Qt.Key_Pause: "Pause",
    Qt.Key_ScrollLock: "ScrollLock",
}


class HotkeyEdit(QLineEdit):
    """Поле, которое запоминает нажатую комбинацию клавиш."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setReadOnly(True)
        self.setPlaceholderText(tr("нажмите сочетание…"))

    def keyPressEvent(self, event) -> None:
        self._handle(event)

    def keyReleaseEvent(self, event) -> None:
        # PrintScreen на Windows приходит только на отпускании
        if event.key() == Qt.Key_Print:
            self._handle(event)

    def _handle(self, event) -> None:
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta,
                   Qt.Key_unknown):
            return
        if key == Qt.Key_Backspace:
            self.clear()
            return

        mods = []
        if event.modifiers() & Qt.ControlModifier:
            mods.append("Ctrl")
        if event.modifiers() & Qt.AltModifier:
            mods.append("Alt")
        if event.modifiers() & Qt.ShiftModifier:
            mods.append("Shift")
        if event.modifiers() & Qt.MetaModifier:
            mods.append("Win")

        name = SPECIAL_KEYS.get(key) or QKeySequence(key).toString()
        if not name:
            return
        text = "+".join(mods + [name])
        if parse_hotkey(text):
            self.setText(text)


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(tr("Настройки PyShot"))
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_language())
        layout.addWidget(self._build_saving())
        layout.addWidget(self._build_hotkeys())
        layout.addWidget(self._build_timer())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("Сохранить"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("Отмена"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    def _build_language(self) -> QGroupBox:
        box = QGroupBox(tr("Язык / Language"))
        form = QFormLayout(box)

        self.lang_box = QComboBox()
        self.lang_box.addItem("Русский", "ru")
        self.lang_box.addItem("English", "en")
        index = self.lang_box.findData(str(self.cfg["language"]).lower())
        self.lang_box.setCurrentIndex(index if index >= 0 else 0)
        form.addRow(tr("Язык интерфейса:"), self.lang_box)
        return box

    def _build_saving(self) -> QGroupBox:
        box = QGroupBox(tr("Сохранение"))
        form = QFormLayout(box)

        self.dir_edit = QLineEdit(str(self.cfg["save_dir"]))
        browse = QPushButton(tr("Обзор…"))
        browse.clicked.connect(self._choose_dir)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.dir_edit)
        row.addWidget(browse)
        wrapper = QWidget()
        wrapper.setLayout(row)
        form.addRow(tr("Папка для скриншотов:"), wrapper)

        self.format_box = QComboBox()
        self.format_box.addItems(["png", "jpg"])
        self.format_box.setCurrentText(str(self.cfg["file_format"]).lower())
        form.addRow(tr("Формат файла:"), self.format_box)

        self.quality = QSpinBox()
        self.quality.setRange(30, 100)
        self.quality.setValue(int(self.cfg["jpg_quality"]))
        self.quality.setSuffix(" %")
        form.addRow(tr("Качество JPEG:"), self.quality)

        self.template = QLineEdit(str(self.cfg["filename_template"]))
        self.template.setToolTip(
            tr("Шаблон даты в стиле strftime:\n"
               "%Y — год, %m — месяц, %d — день, %H:%M:%S — время"))
        form.addRow(tr("Шаблон имени:"), self.template)

        hint = QLabel(tr("Например: screenshot_%Y-%m-%d_%H-%M-%S"))
        hint.setStyleSheet("color: gray;")
        form.addRow("", hint)

        self.copy_on_save = QCheckBox(
            tr("Копировать в буфер обмена при сохранении"))
        self.copy_on_save.setChecked(bool(self.cfg["copy_to_clipboard_on_save"]))
        form.addRow("", self.copy_on_save)

        self.open_folder = QCheckBox(tr("Открывать папку после сохранения"))
        self.open_folder.setChecked(bool(self.cfg["open_folder_after_save"]))
        form.addRow("", self.open_folder)

        self.notify = QCheckBox(tr("Показывать уведомление о сохранении"))
        self.notify.setChecked(bool(self.cfg["notify_on_save"]))
        form.addRow("", self.notify)

        self.profile_box = QComboBox()
        self.profile_box.addItem(tr("как на экране (профиль монитора)"),
                                 "monitor")
        self.profile_box.addItem(tr("стандартный sRGB"), "srgb")
        self.profile_box.addItem(tr("не указывать"), "none")
        current = str(self.cfg["color_profile"]).lower()
        index = self.profile_box.findData(current)
        self.profile_box.setCurrentIndex(index if index >= 0 else 0)
        self.profile_box.setToolTip(
            tr("Чем помечать цвета в файле.\n"
               "«Как на экране» — снимок выглядит точно так же, как монитор "
               "показывал оригинал.\n"
               "«sRGB» — привычный вариант для отправки другим людям."))
        form.addRow(tr("Цвета в файле:"), self.profile_box)
        return box

    def _build_hotkeys(self) -> QGroupBox:
        box = QGroupBox(tr("Горячие клавиши"))
        form = QFormLayout(box)
        self.hk_region = HotkeyEdit(str(self.cfg["hotkey_region"]))
        self.hk_full = HotkeyEdit(str(self.cfg["hotkey_fullscreen"]))
        self.hk_delay = HotkeyEdit(str(self.cfg["hotkey_delayed"]))
        form.addRow(tr("Снимок области:"), self.hk_region)
        form.addRow(tr("Весь экран:"), self.hk_full)
        form.addRow(tr("Снимок по таймеру:"), self.hk_delay)
        hint = QLabel(tr("Кликните в поле и нажмите нужное сочетание. "
                         "Backspace — очистить."))
        hint.setStyleSheet("color: gray;")
        hint.setWordWrap(True)
        form.addRow("", hint)
        return box

    def _build_timer(self) -> QGroupBox:
        box = QGroupBox(tr("Таймер и запуск"))
        form = QFormLayout(box)

        self.delay = QSpinBox()
        self.delay.setRange(1, 60)
        self.delay.setValue(max(1, int(self.cfg["delay_seconds"])))
        self.delay.setSuffix(tr(" сек"))
        form.addRow(tr("Задержка по умолчанию:"), self.delay)

        self.show_countdown = QCheckBox(tr("Показывать обратный отсчёт"))
        self.show_countdown.setChecked(bool(self.cfg["show_countdown"]))
        form.addRow("", self.show_countdown)

        self.autostart = QCheckBox(tr("Запускать вместе с Windows"))
        self.autostart.setChecked(bool(self.cfg["autostart"]))
        form.addRow("", self.autostart)
        return box

    # ------------------------------------------------------------------ #
    def _choose_dir(self) -> None:
        current = self.dir_edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self, tr("Куда сохранять скриншоты"), current)
        if chosen:
            self.dir_edit.setText(chosen)

    def accept(self) -> None:
        self.cfg.update({
            "language": self.lang_box.currentData(),
            "save_dir": self.dir_edit.text().strip(),
            "file_format": self.format_box.currentText(),
            "jpg_quality": self.quality.value(),
            "filename_template": self.template.text().strip()
                                 or "screenshot_%Y-%m-%d_%H-%M-%S",
            "copy_to_clipboard_on_save": self.copy_on_save.isChecked(),
            "open_folder_after_save": self.open_folder.isChecked(),
            "notify_on_save": self.notify.isChecked(),
            "color_profile": self.profile_box.currentData(),
            "hotkey_region": self.hk_region.text().strip(),
            "hotkey_fullscreen": self.hk_full.text().strip(),
            "hotkey_delayed": self.hk_delay.text().strip(),
            "delay_seconds": self.delay.value(),
            "show_countdown": self.show_countdown.isChecked(),
            "autostart": self.autostart.isChecked(),
        })
        self.cfg.save()
        self.cfg.apply_autostart()
        super().accept()
