# Changelog

## 1.1.7 — 2026-09-09

- The installer no longer fails when it updates a copy that is running.

## 1.1.6 — 2026-09-09

- The «Translating…» notice is shorter.

## 1.1.5 — 2026-09-09

- The countdown stands in the middle of the frame it is about to capture and is
  sized to it, instead of sitting at the top of the primary screen.
- It is clear that translation has started: the notice is larger and its dots
  animate.

## 1.1.4 — 2026-09-09

- Translation covers foreign fragments instead of whole paragraphs, so native
  words keep their original pixels.
- Short inserts and file or project names are left alone.
- Separate labels are no longer glued into one paragraph, and a plate can no
  longer grow over the neighbouring word.

## 1.1.3 — 2026-09-09

- Translation goes in one batched request: about two seconds instead of forty.
- Russian labels full of Latin (JPEG, Ctrl, file paths) are no longer
  "translated".
- Translation can no longer hang: pressing the button again cancels it and a
  watchdog gives up after 45 seconds.

## 1.1.2 — 2026-09-09

- The program can capture its own windows again.

## 1.1.1 — 2026-09-09

- Mixed Russian and English text is recognised more accurately.

## 1.1.0 — 2026-09-09

- Translation of the text on a shot: recognition runs offline through Windows,
  only the recognised text is sent out, and the layer can be removed with a
  second press. Google, DeepL and Azure are supported.

## 1.0.2 — 2026-08-24

- Reworked the application icon.

## 1.0.1 — 2026-08-20

- The screen could lock up when a capture started while the settings window was
  open.
- The tray icon opens the settings on a left click; a timed capture opens the
  editor.

## 1.0.0 — 2026-08-20

First public release: area, window and full-screen capture, a macOS-style
timer, annotation tools, PNG/JPEG output with filename templates, configurable
global hotkeys, a Russian and English interface, ICC profile tagging, HiDPI and
multi-monitor support, and an installer.
