# Original components engineering preview

This self-contained preview builds an authored rigid bed frame and opens a saved
bedding study. It does not generate or place a complete world. The full World
Builder research and layout pipeline is outside this package.

Requirements: Python with Tk, Node.js on PATH for the small contact checks, and a
browser with WebGL for viewing. Third-party Three.js 0.180.0 files and their MIT
license are included under `third_party/three`. Their exact hashes are checked;
the preview does not download libraries or use a resident user's library path.

From the repository root:

```text
python -B Testing/qualify_bedding.py
python -B tools/world_components_preview.py
```

Choose **Build / reuse saved frame**, select that frame, and choose **Inspect
bedding on selected frame**. Bedding supports the 1.00 × 2.00 m and 1.60 × 2.10 m
frame presets. The standalone launcher disables optional world binding because
it has no selected world. It preserves the ordinary native controls and their
owned preview-server cleanup.

New generated files stay in this checkout's `Data/world_original_components`
and `Data/world_bedding_studies` folders. Saved manifests bind exact source and
asset paths. Relocating the checkout works before building; this is not an
archive/restore feature for moving existing bound studies. Preserve prior
studies and make a new revision after changing sources.

After a source update, historical or invalid frame manifests remain visible as
held rows with a reason. They cannot be opened or used to build bedding through
these controls. Verified current frames remain usable beside them; selecting a
held row never migrates or deletes its files. Build a new revision when needed.

The qualification is only thirteen contact smoke checks. It is not full physical
validation, a visual pass or a realistic-fabric claim. Discrete contacts have no
continuous collision or self-collision. Dense release instability and false
upper-surface contacts below the mattress remain unresolved. Experimental
World013 response changes are not included. The shipped four physics modules
are byte-identical to the installed engineering version.

The candidate has been checked through relocated temporary-state saves/reuse,
native-module imports and exact loopback HTTP assets, with tamper/missing-vendor
rejection. No Tk window or browser was opened during these checks, so visible
native controls and continuous playback still need a separate review.
