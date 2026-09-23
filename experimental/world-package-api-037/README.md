# Experimental saved-layout package API037

This isolated candidate adds `export_saved_layout_package` and an **Export 3D
package (experimental)** action to the existing native World Builder. It has not
been installed or run in the native UI.22 lightweight tests pass with the worker
mocked; no new real GLB export has been run while Video Studio owns its long render.

The API captures the explicitly selected saved job and its already-open preview
binding. Without an open preview it checks only that job's saved pointer. It never
chooses the globally most recent job. Selecting another project during export
does not substitute that other project. The action asks for a destination parent,
creates a new timestamped package folder and exposes an explicit Open export
folder action after success. Closing the workspace while its export is active
is held until the worker finishes, so the owned worker is not abandoned.

Recipe recognition requires the exact tested current viewer/controller/Three
pins and authored habitat roles. A separate geometry validation allowlist makes
the current limit explicit: only the previously verified Original Mars geometry
may export. An unrelated recipe returns unsupported_recipe; a recognized but
unvalidated layout returns unsupported_layout. An older saved renderer returns
unsupported_preview with an instruction to Open current preview first. The export
itself never refreshes a preview, rebuilds research or queues a model.

The copied036 mesh builder generates corrected034 metadata directly from verified
geometry and the exact authored plan/controller. The existing importer checks run
before output is marked ready. Local runtime, font and producer files are pinned.
Missing/different dependencies return a clear state without downloading anything.
Outputs never overwrite an existing folder or write inside saved world/research/
preview roots. Sources and pins are rechecked after the worker; a changed source or
failed worker leaves an incomplete marker and no ready manifest.

The detailed input/output/capability contract is in
`candidate/tools/world_builder_engine/layout_package_contract.json`. This is a
3D asset with door/collider metadata; game-engine collision and interaction,
working science equipment, pressure simulation and VR runtime remain unimplemented.
It does not improve the procedural scene's realism or imply owner visual approval.

Before installation: root schedules an actual saved Mars export through this API,
checks its source preservation/importer report and inspects the native button.
Until those checks pass, the install plan remains held. Current testing covers
selected-job identity, stale/different previews, missing/tampered bindings,
unsupported recipe/layout, missing/changed dependencies, unchanged source files,
no-overwrite, concurrent source/pointer changes, worker failure, duplicate/cancelled
UI requests and execution of the actual native callback methods without a window.
