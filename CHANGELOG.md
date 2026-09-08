# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.7] — 2026-09-09

### Fixed

- **Updating over a running copy failed.** The installer stopped the program
  and copied at once, but a frozen build hands its file back a moment later,
  so the copy died with «the file is in use by another process» — and the
  elevated window closed before anyone could read it. It now waits for the
  processes to end and retries the copy for about eight seconds, saying so if
  it still cannot.

## [1.1.6] — 2026-09-09

### Changed

- The «Translating…» notice lost its second line: the running dots already
  show that the program is working, and the explanation only added noise to
  the middle of the shot.

## [1.1.5] — 2026-09-09

### Changed

- **The countdown now belongs to the frame, not to the screen.** It used to sit
  at the top of the primary screen — far outside the area being captured, and
  on a second monitor out of sight altogether. It is now centred on the region
  that is about to be shot, the way macOS does it, and is kept inside the
  screen it lands on.
- **The countdown is sized to the frame.** A full-screen shot gets large
  digits, a small region gets small ones: the window is scaled so that the
  frame stays at least twice its size, between 0.45× and 3×.
- **It is now obvious that translation has started.** The «Translating» notice
  in the middle of the selection is larger, scaled to the size of the frame,
  and animates its dots — so a slow translation no longer looks like a freeze. It disappears by itself once the text is
  ready.

## [1.1.4] — 2026-09-09

### Changed

- **Translation now covers foreign fragments, not whole paragraphs.** On a page
  mixing Russian and English the plate used to be drawn over the entire
  paragraph, so its Russian half was replaced by a machine translation of
  itself: «ssylki i shablony `%Y-%m-%d` iz podschёta vybrosheny» came back
  mangled. Recognised words are now split into runs of consecutive foreign
  words, each run gets its own plate covering exactly its bounding box, and
  native words keep their original pixels.
- **Short inserts are left alone.** A fragment inside a native line has to hold
  at least six foreign letters, so `fork 7`, `Max` and `Opus 5` stay as they
  are; a line that is entirely foreign still translates from three letters up,
  because a standalone button label is worth translating.
- **File and project names are not translated.** A token with an underscore,
  an inner capital, an inner dot or a digit — `TractPart_Project`,
  `config.json`, `v1.1.3` — ends the run instead of joining it, so the name
  stays readable and the words on either side become separate fragments.

### Fixed

- **Separate labels are no longer glued into one paragraph.** Lines were merged
  when the gap between them was under 1.6 line heights, which swallowed whole
  menus; inside a real paragraph the gap is about half a line height, and that
  is now the limit.
- **A plate can no longer grow over the neighbouring word.** When the Russian
  translation is longer than the original, the plate is widened — but a
  fragment inside a line is only allowed to grow up to the next native word,
  and its height by 70 % at most.
- **The font is no longer needlessly small.** Recognised boxes fit the letters
  themselves, without room for ascenders and descenders, and the text was
  shrunk to that height; the plate now allows a fifth of the line height in
  air, and fragments are no longer forced to share a size with full lines.

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

[1.1.7]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.7
[1.1.6]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.6
[1.1.5]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.5
[1.1.4]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.4
[1.1.3]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.3
[1.1.2]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.2
[1.1.1]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.1
[1.1.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.1.0
[1.0.2]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.2
[1.0.1]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.1
[1.0.0]: https://github.com/Dimario-kurs/pyshot/releases/tag/v1.0.0
