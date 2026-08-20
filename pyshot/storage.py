"""Сохранение, копирование и печать готового скриншота."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtGui import QColorSpace, QGuiApplication, QImage
from PySide6.QtWidgets import QFileDialog

from .i18n import tr


_monitor_cs: list = []


def monitor_color_space():
    """ICC-профиль, назначенный монитору в Windows (кэшируется)."""
    if _monitor_cs:
        return _monitor_cs[0]

    space = None
    if sys.platform == "win32":
        try:
            import ctypes

            gdi32, user32 = ctypes.windll.gdi32, ctypes.windll.user32
            hdc = user32.GetDC(0)
            size = ctypes.c_uint32(1024)
            buf = ctypes.create_unicode_buffer(1024)
            ok = gdi32.GetICMProfileW(hdc, ctypes.byref(size), buf)
            user32.ReleaseDC(0, hdc)
            if ok and buf.value:
                candidate = QColorSpace.fromIccProfile(
                    Path(buf.value).read_bytes())
                if candidate.isValid():
                    space = candidate
        except Exception:
            space = None

    _monitor_cs.append(space)
    return space


def apply_color_profile(image: QImage, cfg) -> QImage:
    """Проставляет цветовой профиль. Пиксели не меняются — только метка."""
    mode = str(cfg["color_profile"]).lower()
    if mode == "none":
        return image
    if mode == "srgb":
        image.setColorSpace(QColorSpace(QColorSpace.SRgb))
        return image
    space = monitor_color_space()
    if space is not None:
        image.setColorSpace(space)
    return image


def target_dir(cfg) -> Path:
    path = Path(str(cfg["save_dir"]).strip() or ".").expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        path = Path.home() / "Pictures"
        path.mkdir(parents=True, exist_ok=True)
    return path


def build_path(cfg) -> Path:
    directory = target_dir(cfg)
    ext = "jpg" if str(cfg["file_format"]).lower() in ("jpg", "jpeg") else "png"
    try:
        stem = time.strftime(str(cfg["filename_template"]))
    except Exception:
        stem = time.strftime("screenshot_%Y-%m-%d_%H-%M-%S")
    stem = "".join(ch for ch in stem if ch not in '\\/:*?"<>|') or "screenshot"

    path = directory / f"{stem}.{ext}"
    index = 1
    while path.exists():
        path = directory / f"{stem}_{index}.{ext}"
        index += 1
    return path


def save_image(image: QImage, cfg, ask: bool = False, parent=None) -> Path | None:
    """Сохраняет изображение. Возвращает путь или None, если отменено."""
    path = build_path(cfg)
    if ask:
        chosen, _ = QFileDialog.getSaveFileName(
            parent, tr("Сохранить скриншот"), str(path),
            "PNG (*.png);;JPEG (*.jpg *.jpeg)")
        if not chosen:
            return None
        path = Path(chosen)

    image = apply_color_profile(image, cfg)
    ext = path.suffix.lower().lstrip(".") or "png"
    if ext in ("jpg", "jpeg"):
        ok = image.save(str(path), "JPEG", int(cfg["jpg_quality"]))
    else:
        ok = image.save(str(path), "PNG")
    if not ok:
        return None

    if cfg["copy_to_clipboard_on_save"]:
        copy_image(image)
    if cfg["open_folder_after_save"]:
        reveal(path)
    return path


def copy_image(image: QImage) -> None:
    QGuiApplication.clipboard().setImage(image)


def reveal(path: Path) -> None:
    """Открывает проводник с выделенным файлом."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception:
        pass


def open_dir(path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass
