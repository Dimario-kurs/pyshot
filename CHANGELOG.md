# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.2] — 2026-08-24

### Changed

- **Reworked the application icon.** Same identity — a blue tile, white capture
  corners and a red lens dot — but redrawn: a softer squircle, a diagonal
  gradient with a light sheen along the top, thinner corner strokes with more
  breathing room, and a smaller dot with a soft glow. The sheen, the inner
  outline and the glow are skipped below 32 px so the tray icon stays crisp at
  16 px. The same drawing feeds the tray, the window icons and the `.ico`.

## [1.0.1] — 2026-08-20

### Fixed

- **The screen could lock up.** Pressing a capture hotkey while the modal
  settings window was open put the overlay on top of everything while the
  dialog kept all input, so neither the mouse nor <kbd>Esc</kbd> reached it.
  Captures are now skipped while a modal window is open, and the window that
  blocks them is brought to the front instead.

### Changed

- **Left-clicking the tray icon opens Settings** instead of starting a capture.
  Capturing stays on the hotkeys and the right-click menu — the old behaviour
  surprised people who just wanted to open the program.
- **A timed capture now opens the editor** — the same window as a regular
  capture, with the drawing tools and the copy / save / close buttons, instead
  of silently writing a file. The old behaviour is one checkbox away:
  *Settings → Timer and startup → «After a timed capture open the editor»*.

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

[1.0.2]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.2
[1.0.1]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.1
[1.0.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.0
