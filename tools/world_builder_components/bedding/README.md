# Experimental bedding contacts and portable preview

The portable authored-component preview includes its Python helpers, native
controls, local loopback asset servers and pinned Three.js dependency. See
[the launch and qualification instructions](../PORTABLE_PREVIEW.md).

This package builds a procedural rigid frame and a saved bedding study. It does
not generate or place a full world. The four physics modules retain their
existing engineering implementation: there is no new solver correction here.
Dense release instability, false upper-surface contacts below the mattress,
continuous collision and self-collision remain unresolved.

Run the scoped contact checks and disposable portability checks from the repo:

```text
python -B Testing/qualify_bedding.py
python -B Testing/test_world_portable_preview.py
```

The latter imports Tk but creates no window. It uses temporary generated
components and local HTTP servers, preserves repository/owner data, and checks
asset integrity, historical-row holds and cleanup. No browser render, dynamic
physics, realistic fabric or owner visual approval is established by these CPU
checks. Source-bound historical studies remain preserved and may be held after
a source change; build a fresh revision beside them.
