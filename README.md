<div align="center">

# PyShot

**A screenshot tool for Windows: grab an area, a window with one click, or a timed shot — annotate and save.**

[![CI](https://github.com/Dimario-kurs/pyshot/actions/workflows/ci.yml/badge.svg)](https://github.com/Dimario-kurs/pyshot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**English** · [Русский](README.ru.md)

<img src="docs/editor.png" alt="PyShot selection overlay with the tool panel" width="820">

</div>

## What it does

- Capture an area, the window under the cursor (one click), or the whole screen.
- Timed capture: the program remembers your last frame and counts down over the
  live screen, so menus and tooltips stay open and land in the shot.
- Annotate on top: pencil, line, arrow, rectangle, marker, text, colour and
  width, undo.
- Save as PNG or JPEG, or copy to the clipboard.
- Translate the text on a shot — the **АЯ** button or <kbd>Ctrl</kbd>+<kbd>T</kbd>.
  Recognition runs offline through Windows; only the recognised text goes online,
  and only with your permission.
- Russian and English interface, switchable in the settings.

## Install

Download the archive from [Releases](../../releases), unpack it and run
**`Установить PyShot.bat`**. It installs to `C:\Program Files\PyShot`, adds a
Start menu shortcut and registers an uninstall entry.

To remove: *Settings → Apps → PyShot → Uninstall*. Your settings and screenshots
stay where they are.

From source:

```bash
python -m pip install -r requirements.txt
pythonw main.py
```

Needs Windows 10 or 11, Python 3.10+ and PySide6 — no other dependencies.

## Hotkeys

| Shortcut | Action |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>4</kbd> | area or window |
| <kbd>Ctrl</kbd>+<kbd>5</kbd> | whole screen |
| <kbd>Ctrl</kbd>+<kbd>6</kbd> | timed shot of the remembered frame |

All three are configurable. Inside the overlay: <kbd>Enter</kbd> saves,
<kbd>Ctrl</kbd>+<kbd>C</kbd> copies, <kbd>Ctrl</kbd>+<kbd>Z</kbd> undoes,
<kbd>Esc</kbd> closes.

Tray icon: left click opens the settings, right click opens the menu.

## Settings

Output folder (`Desktop\Скриншоты` by default), file format and quality,
filename template, hotkeys, language, timer delay, start with Windows,
translation options.

## Build and tests

```bash
python tests/test_pyshot.py     # tests
tools\build_exe.bat             # builds dist\PyShot.exe
```

## License

MIT — see [LICENSE](LICENSE).
