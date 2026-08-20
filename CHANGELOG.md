# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-08-20

First public release.

### Added

- **Area capture** with a frozen full-screen overlay: drag a rectangle, move it,
  resize it by eight handles, live pixel-size readout, crosshair guides.
- **Window capture** — the window under the cursor is highlighted at full
  brightness and captured with a single click. Bounds come from
  `DWMWA_EXTENDED_FRAME_BOUNDS`, cloaked and click-through windows are skipped.
- **Full-screen capture** straight to a file.
- **macOS-style timer**: the previously used frame is restored for adjustment,
  the overlay closes before the countdown, and the shot is taken over the live
  screen after 3, 5 or 10 seconds — or immediately when the timer is off.
- **Annotation tools** — pencil, line, arrow, rectangle, marker, text — with a
  12-colour palette, a custom colour picker, line width 1–20 and undo/redo.
- **Saving** as PNG or JPEG with adjustable quality, `strftime` filename
  templates, automatic name de-duplication, clipboard copy, optional folder
  opening and tray notifications.
- **Configurable global hotkeys** via the Win32 `RegisterHotKey` API, recorded
  by pressing the desired combination; failures are reported instead of being
  swallowed.
- **Settings window** covering language, output, hotkeys, timer and autostart;
  the "Start with Windows" checkbox manages the `HKCU\...\Run` entry itself.
- **Russian and English interface**, switchable at runtime; the tray menu is
  rebuilt on the spot.
- **ICC profile tagging** of saved files with the display profile, so a
  screenshot looks exactly like the screen; `sRGB` and `none` are available as
  alternatives.
- **High-DPI and multi-monitor support** — screens are composed by real geometry
  and saved at full device resolution.
- Tray icon, toolbar icons and the application `.ico` generated in code; no
  binary art assets in the repository.
- Offscreen test suite (`tests/test_pyshot.py`) and a GitHub Actions workflow
  that runs it and builds `PyShot.exe`.
- **Installer** (`Установить PyShot.bat` → `tools/install.ps1`): installs to
  `C:\Program Files\PyShot` for all users, elevating once through UAC; adds a
  Start menu shortcut, registers an uninstall entry in Settings → Apps, migrates
  an older per-user copy together with the autostart entry, and launches the
  program non-elevated. `-PerUser` installs to `%LOCALAPPDATA%\Programs\PyShot`
  without elevation. `tools/uninstall.ps1` removes everything except the user's
  settings and screenshots.

[1.0.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.0
