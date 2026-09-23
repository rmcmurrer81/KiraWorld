# Experimental first-person package consumer043

This independent Three 0.180 consumer loads the actual exported GLB meshes and
embedded textures. It adds horizontal first-person movement, conservative wall,
equipment and leaf collision, bounded hinged doors, occupied-swing holds and
paired-airlock door sequencing. It needs no Kira research, original geometry,
equipment reconstruction or model runtime. The installed World workspace and
every saved preview are unchanged. This prototype is **not installed**.

No Godot, Unity or Unreal engine was found in PATH or the standard installation
locations inspected. This is a Three-based first-person prototype, not a native
game-engine adapter or VR build. The local inventory was scoped rather than a
scan of every drive. Blender is available only as a separate renderer.

## Package and controls

For a later authorized manual review, run `python serve.py` in this directory.
It prints a loopback-only URL and does not open a browser. Select exactly the five
files from `sample-package`, or a supported explicit World export: manifest.json,
scene.json, scene.glb, ROUNDTRIP.json and README.txt. No default/latest owner world
is accessed. Complete filename/count/size admission happens before any file read:
1 byte–16 MiB per file, 32 MiB total. Digests are checked before import; external
GLB resources and unsupported schema/controller versions are rejected. Manifest
hashes establish file consistency, not an authenticated publisher identity.

Start walking, then use WASD, arrow keys or drag to look, and E for a nearby door.
Escape, Pause, window blur and a hidden tab stop the animation. Walking is limited
to supported flat floors. Closed doors, fixed frames and conservative equipment
bounds block movement. Door leaves use the same rotation for the imported mesh
and its collision bounds. Airlock peers cannot open together, including pending
and held motion at zero angle. State is session-local and is never written back.

The package retains authored materials and textures. The consumer adds a disclosed
hemisphere fill and ACES exposure; identical preview lighting is not promised.
The ordinary input/browser controls have not been exercised. No browser, server,
native UI, WebGL renderer, GPU job or model was started during validation.

## Evidence

- `TEST-ADMISSION.json`: 12 tests, including huge final-file rejection before
  **any** earlier file is read.
- `TEST-RUNTIME-FINAL.json`: 20 package/runtime tests. Actual closed-door blocking,
  opening, crossing into the airlock, closing and then requesting the peer pass.
  Pending/held/open peers, reach, moving/swing occupation, walls, unsupported
  floor, tampering and unsupported metadata are checked.
- `TEST-IMPORT-003.json`: CPU GLTFLoader imports 565 meshes, 97 materials, 67
  embedded textures, 141 semantic nodes, 134 collider links and 6 actual hinges.
  Closed/half/open leaf world bounds match runtime collision; frames remain fixed.
  Changed hinge/owner/pair/parent associations are rejected.
- `TEST-REFERENCE-3.json`: 178 walking steps, 4 successful toggle intents and
  1,716 pose comparisons against the installed source controller. Maximum
  numerical difference is **zero**. Only this optional equivalence test reads the
  original source geometry. The consumer and shipped sample do not need it.
- `CHECK-RESULT-003.json`: final importer resource/preservation measurement.
  All 116 protected originals, five installed files, current preview and sample
  package are unchanged. The earlier successful run took 0.36 seconds and about
  179 MiB sampled process-family RSS.

Portable CPU tests: `node test_admission.mjs` and `node test_runtime.mjs`. The
optional real importer test is `node test_import.mjs <local-canvas-module>
<new-receipt.json>`; it uses the already installed pinned @napi-rs/canvas 0.1.100
decoder, performs no font rasterization and never downloads a dependency. The
Canvas native binary is not redistributed. Three code and its MIT license are
included. `run_checks.py` and `stage.py` are local staging/preservation records,
not portable setup/install commands; the public backup redacts their local paths.

## Scope and remaining review

The metadata/controller contract is bounded, and actual integration is proven
only on the installed042 derived Mars package. Other supported authored exports
need their own integration checks. This does not add stairs, jumping, gravity,
free-body physics, multiplayer, persistent sessions, pressure cycling, working
laboratory equipment, VR tracking/controllers or photorealistic rooms. Equipment
and ladders retain conservative collision boxes, so climbing/lying down remains
unimplemented. Visual review, normal browser input usability, comfort and owner
acceptance are pending. No claim of overall World Builder completion is made.

The first import attempt rejected equivalent JSON objects because my binder used
property order as equality. The corrected canonical comparison passed without
regenerating the package. Two reference-test attempts used wrong guessed corridor
ID/role assertions; the final test uses the already bound second door's room
membership. Those harness failures and prior code are retained in `history` and
the initial receipts. No source world or installed code changed during recovery.
