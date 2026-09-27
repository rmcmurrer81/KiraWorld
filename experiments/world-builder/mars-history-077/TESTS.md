# Portable inert checks

The seven copied test/support files are exact frozen077 bytes. They use a modern Node.js runtime with `node:test`, `node:vm` modules, `fetch`-compatible adapters and ES modules. They do not start a browser, renderer, model, service or real audio decoder. `ui_harness.mjs` evaluates the actual app, history host and library, with DOM/audio/WebGL doubles.

From this experiment's directory, create a fresh empty `results` directory, then run these commands serially:

```text
node --max-old-space-size=128 --test tests/library.test.mjs tests/test_queued_audio.mjs
node --max-old-space-size=128 --experimental-vm-modules tests/test_ui_lifecycle.mjs candidate fixed results/lifecycle.json
node --max-old-space-size=128 --experimental-vm-modules tests/test_crop_ui.mjs candidate results/crop.json
node --max-old-space-size=128 --experimental-vm-modules tests/test_history_integration.mjs candidate results/history.json
```

The three output JSON files must not already exist. This public subset comprises **57 cases**: 31 library/queued-audio, 8 app lifecycle, 5 crop controls and 13 history integration. It includes missing narration, exact habitat-role gating, held-key and pointer cleanup, native control arrows, focused Escape, late fetch cancellation, room exit/reentry, package replacement and page restoration.

The original local run had 71 passing checks under a bounded process supervisor. Its additional 14 package/door/navigation checks require private original exported packages and are deliberately omitted. The public commands reproduce the inert subset; the Node heap option is not a whole-process memory supervisor. Run under an appropriate local resource budget. No public result substitutes for actual browser, assistive-technology, audio or headset review.
