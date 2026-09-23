# Consumer044: loading lifecycle and embedded image admission

This isolated successor fixes concrete issues reproduced in experimental043.
It changes `app.mjs` and `package_loader.mjs`, plus one shared
`scene_disposal.mjs` helper. It does not install anything or alter saved worlds,
current previews, the physics/navigation controller, or canonical World code.

The source audit and CPU reproductions found:

1. The package picker stayed enabled during an import, while its handler ignored
   another selection. The visible file selection could then disagree with the
   loaded package. The picker is now disabled for that request and reenabled on
   success/failure. Start cannot bypass loading through a programmatic event.
2. An import completing after pagehide could create a new renderer on the closed
   page. A generation marker now rejects late results. Back-forward restoration
   starts a fresh paused selection, and an old promise cannot replace the fresh
   scene or unlock its pending request. Resources from discarded scenes and
   rejected bindings are released, including shared ImageBitmaps once each.
3. `!buffer.uri` accepted empty/null URI properties even though Three interprets
   a defined buffer URI as a fetch source. Buffers/images must now have **no URI
   property**. Embedded data continues to be the only resource path.
4. Compressed file bounds did not constrain PNG dimensions or aggregate decoded
   pixels. PNG views/headers are now inspected inside the actual BIN range before
   image decoding. The declared recipe allows at most 128 embedded noninterlaced
   8-bit RGBA PNG references, 2048px per dimension and 32 megapixels in aggregate.
   Duplicate references count toward that conservative budget. The unchanged
   sample has 67 images / 17,104,896 pixels, with 512×512 or 768×256 dimensions.

These are consistency and resource-admission checks for the existing authored
PNG-only recipe, **not a general hostile-file sandbox** or arbitrary glTF reader.
PNG header admission does not validate all PNG chunks/CRCs; the installed decoder
still performs full format decoding. Manifest hashes do not authenticate a
publisher. Unsupported recipes or larger legitimate textures need deliberate
compatibility review rather than silent acceptance.

## Evidence

- `BASELINE-UI-REPRO.json`, `BASELINE-GLB-REPRO.json` and
  `BASELINE-PNG-REPRO.json` reproduce the original admission/lifecycle defects.
- `UI-LIFECYCLE-PASS-2.json`: eight scenarios execute the actual app event
  handlers with fake DOM and renderer dependencies. They cover pending selection,
  late completion, repeated Start, Escape, switching, failed load/recovery and
  back-forward reset. This is **not** native/browser visual or input approval.
- `GLB-ADMISSION-FINAL.json`: five explicit URI cases reject before import.
- `PNG-ADMISSION-FINAL.json`: twenty malformed/range/dimension/count cases,
  including truncated/bad IHDR, unsafe integer offsets, zero/maximum dimensions,
  aggregate accounting and duplicate references. No malicious image is decoded.
- `DISPOSAL-FINAL.json`: shared resources release once; the actual loader catch
  releases a decoded scene after a rejected binding. Parser/scene are test doubles.
- `SESSION-RESET-PASS.json`: independent sessions and reload start at the entry
  with every door closed; metadata is unchanged. No new reset UI was added.
- `RUNTIME-REGRESSION-PASS.json`: the existing twenty collision, paired-door,
  walking and file-integrity checks pass with unchanged runtime code.
- `ACTUAL-IMPORT-PASS.json`: the unchanged real GLB still decodes 67 textures,
  imports 565 meshes and binds all 134 colliders / six doors. Closed/half/open
  physical leaf bounds and fixed frames remain consistent.
- `CHECK-RESULT.json`: actual CPU import took 0.389 seconds / about 178.3 MiB
  sampled process-family RSS. All 116 protected originals, five installed files,
  frozen043 source closure and the derived package were preserved.

## Reproduction and limits

`candidate` is self-contained for a later authorized manual preview using its
existing `serve.py`; no server/browser was started in this task. Its interface,
motion controller and saved package are preserved from043. Visual review,
ordinary input usability, other exported fixtures and owner approval remain
pending. No native game engine, VR, pressure simulation or realism claim is added.

Run the focused tests from this directory with Node:

```
node test_glb_admission.mjs candidate fixed fresh-uri-result.json
node test_png_admission.mjs candidate fixed fresh-png-result.json
node --experimental-vm-modules test_ui_lifecycle.mjs candidate fixed fresh-ui-result.json
node --experimental-vm-modules test_disposal.mjs candidate fresh-cleanup-result.json
node test_session_reset.mjs candidate fresh-session-result.json
node candidate/test_runtime.mjs fresh-runtime-result.json
```

The VM modules flag is needed only by headless audit tests, not the browser
application. Test outputs require fresh paths to preserve history. The real
importer test accepts an explicit existing pinned @napi-rs/canvas decoder; no
native binaries, fonts or source-world geometry are redistributed. Local staging
and preservation scripts are historical helpers whose public copies redact local
paths. This task used no UI input, GPU/model, native engine download or Git write.

Earlier intermediate receipts are retained. `DISPOSAL-PASS.json` used the imprecise
field name `files_authenticated_by_existing_manifest_checks`; the final receipt
correctly reports hash binding verification and no publisher authentication.
