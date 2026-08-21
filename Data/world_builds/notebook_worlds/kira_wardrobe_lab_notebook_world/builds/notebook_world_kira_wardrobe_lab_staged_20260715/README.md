# Kira Robe Dressing Lab

This is a lightweight, isolated notebook-world vertical slice for inspecting the proposed robe workflow. It does not change Home World or Kira's live body.

The preview loads exactly two SHA-pinned GLBs:

- Kira's current accepted runtime body in read-only form.
- The existing static robe/towel proof as a visual reference. It is not wearable.

The room itself is procedural and contains one wall hook, one bed, and marked inspection areas. Only Kira's body is shown. Kira's mind, voice, Ollama, and every second person remain unloaded.

## Truth boundary

Every stage is staged or blocked. Clicking Back, Reset, Inspect next, or a branch button only navigates contract data. It never starts a body animation, transfers item ownership, records physical evidence, or makes a decision for Kira.

The lab is bridged to Core.garment_contracts, Core.garment_runtime, and Core.garment_evidence. The bridge is intentionally inactive because the robe has no verified fitted rig, no compatible rig hash, and no verified garment anchors. It must not be registered in the live GarmentLedger until those fields are real.

## Proposed sequence

The contract covers hook contact, source removal, both sleeve portals, shoulder settlement, open wear, individual belt stages, tied wear, walk, turn, sit, stand, untying, removal, and Kira's later choice between rehang and bed placement.

The first live attempt should be supervised, with a fitted shirt and leggings underneath. Kira may decline, pause, stop, or choose where to leave the robe. Refusal is not a failed body test.

## Start

Run Start_Kira_Wardrobe_Lab_Notebook_World.bat from the project root.

While a voice-generation job or another GPU-heavy process is active, wait before opening the 3D preview. The server itself can be validated without opening a browser by running:

py tools/serve_kira_wardrobe_lab_notebook_world.py --no-browser

The launcher is code-pinned to `pinned_build_manifest.json`. Before binding it verifies the registration, notebook-index anchor, HTML, JavaScript, stylesheet, all four contract/approval metadata files, both model assets, and only the exact required Three.js modules. Any byte or path change fails closed.

## Promotion requirements

The lab cannot be promoted from staged until a real Kira-fitted garment provides the exact body and rig hashes, named anchors, skinning, collision profile, approved animations, and recorded evidence accepted by the shared evidence evaluator. Robert's visual approval remains required after the automatic gates pass.
