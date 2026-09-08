# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **The installer no longer fails when run from the folder it installs into.**
  Copying the executable onto itself aborted the script before it could write
  the uninstall entry, leaving the app registered under its previous version.
  Both copies are now skipped when source and destination are the same file.
  The script lost its accidental double line spacing at the same time.

## [1.1.3] — 2026-09-09

### Fixed

- **Translation was slow to the point of looking frozen.** Every paragraph was
  sent as a separate request: forty paragraphs on a full-screen shot meant
  about forty seconds of a silent "Translating…". Everything now goes in one
  batched request — the same screenshot takes about two seconds.
- **Russian labels were being "translated" from English.** A block was sent for
  translation when Latin letters made up as little as 15 % of it, and Russian
  interface labels are full of Latin: JPEG, Ctrl, PNG, `%Y-%m-%d`, file paths.
  That turned «Качество JPEG» into «Формат JPEG». Now the foreign script has to
  make up at least 35 % of the letters, paths and URLs are excluded from the
  count, and a real foreign word is required.
- **Words were substituted between recognisers by context, not by shape.**
  `Manage` read as `Мападе` next to `connectors` is now corrected from the
  English engine, while `Сервис` next to `перевода` is left alone. Previously
  the first stayed broken and the second could be replaced with garbage.
- **Long words were clipped**: word wrap cannot break «фотографии», so the tail
  was cut off. The font size now accounts for width as well as height.
- **Font sizes jumped between neighbouring lines** (9 pt next to 11.5 pt in one
  menu) because recognised boxes differ in height depending on ascenders. Lines
  of a similar size now share one size.
- Translation can no longer hang: pressing the button again cancels it, a
  watchdog gives up after 45 seconds, and the worker is kept referenced so a
  finished job cannot be lost before it reports back.

## [1.1.2] — 2026-09-09

### Changed

- **The program can now capture its own windows.** Since 1.0.1 capturing was
  refused while a modal window such as Settings was open: the overlay would
  have covered the screen while the dialog kept all the input, which looked
  like a freeze. Instead of refusing, the overlay now takes the input over by
  becoming modal itself — the dialog stays visible and lands in the shot,
  while the mouse and <kbd>Esc</kbd> go to the overlay.
- Full-screen capture is no longer blocked by open dialogs at all: it draws no
  overlay, so there was nothing to protect against.

## [1.1.1] — 2026-09-09

### Fixed

- Mixed Russian/English text: short Latin words that the Russian recogniser
  turned into look-alike Cyrillic (`on` → `оп`, `car` → `саг`, `my` → `ту`)
  are now taken from the English engine. The substitution only happens when
  the case matches, because the English engine renders lowercase Cyrillic in
  capitals — that is how `сниму` used to become `CHVIMY`. Common Russian words
  spelled entirely with look-alike letters are protected by a stop list.

## [1.1.0] — 2026-09-09

### Added

- **Translation of the text on a shot.** A button in the tool panel (or
  <kbd>Ctrl</kbd>+<kbd>T</kbd>) recognises the text, translates it and draws
  it over the original on plates that match the background; pressing it again
  removes the layer. The translation is included in the saved file and in the
  clipboard copy.
- Recognition runs **offline** through the OCR engine built into Windows; only
  the recognised text is sent to the translation service, and only after an
  explicit confirmation.
- **Mixed Russian/English text** is handled: the Russian engine is used as the
  base because the English one cannot output Cyrillic at all, Latin words are
  taken from the English engine, and the translator is given the foreign
  language explicitly so that it does not return mixed text unchanged.
- Providers: Google (no key, default), DeepL and Azure Translator (API key in
  the settings). Source and target languages are configurable.
- Lines are grouped into paragraphs before translation, plates may grow to the
  right instead of shrinking the font, and background and text colours are
  sampled from the shot itself.

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
[1.1.3]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.3
[1.1.2]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.2
[1.1.1]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.1
[1.1.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.0
[1.0.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.0
