# Portable checks

Use an existing Node.js installation that supports ECMAScript modules and `vm.SourceTextModule`. No dependency download is required. From this experiment directory, create a new `results` directory and run:

```sh
node --max-old-space-size=128 --test tests/library.test.mjs tests/test_queued_audio.mjs
node --max-old-space-size=128 --experimental-vm-modules tests/test_ui_lifecycle.mjs candidate fixed results/lifecycle.json
node --max-old-space-size=128 --experimental-vm-modules tests/test_crop_ui.mjs candidate results/crop.json
node --max-old-space-size=128 --experimental-vm-modules tests/test_history_integration.mjs candidate results/history.json
node --max-old-space-size=128 --experimental-vm-modules --test tests/test_public_controls.mjs
```

The JSON output files must not already exist. These commands cover 65 cases: 31 library/audio-event cases, eight application lifecycle cases, five crop UI cases, 13 history integration cases and eight public timing/control cases. The runtime source and first seven test/support files are exact frozen bytes; `test_public_controls.mjs` is an additional portable test written for this backup.

The public timing tests execute the actual application or control helper with clearly synthetic runtime adapters. They test elapsed-time validity, cancellation, frame bounds, destination labels and bounded control dispatch. They do not prove collision geometry or actual GLB import. Those private-fixture checks and their raw receipts are excluded from the public snapshot. No test here generates audio, opens a browser, renders WebGL, starts a server or invokes a model.

The original080 suite executed 52 cases against its exact private package and application, with another 45 unchanged package/library cases retained through pinned parent evidence. This does not mean 97 fresh tests ran in080. Its independent review and revision-specific browser observations are summarized separately.

The Node heap option constrains the JavaScript heap, not whole-process memory. The local preparation used a separate bounded supervisor for execution and cleanup; that machine-specific runner and its raw process receipts are not public source. A browser test is still necessary for actual graphics, input devices and media. Narration files remain absent, and no headset or real audio test is claimed.
