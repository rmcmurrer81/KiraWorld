# Deferred API-only workflow

Prepared commands below have not run. They do not open a window or start a server.
Root must first finish the active Studio render and coordinate available CPU/RAM.

1. If root wants the earlier037 baseline check, use its frozen `run_real_api.py`
   with the explicitly chosen saved job and existing verified manifest. This runs
   the old controller export and does not install037 or create a new preview.
   Its result cannot establish039's pairing extras/importer behavior.
2. Review039 `INSTALL-PLAN.json` and `RECOVERY-MAP.json`. Each existing target must
   still match `before_sha256`; each new target must still be absent. Preserve
   preimages. Install the exact23 candidate files as one reviewed change. Do not
   overwrite owner data or old preview directories. Existing targets are the
   workspace and native controller; exporter files are additions in this baseline.
3. After installation, run `python prepare_current_preview.py --job <explicit
   selected-job-directory> --receipt <new-local-work-receipt.json>`. It checks
   all installed039 hashes and the unchanged preview backend context, invokes
   `refresh_saved_preview` directly, verifies the new immutable controller pin,
   and checks116 protected originals and the saved pointer before/after. It
   creates/reuses only an immutable preview build. It opens no UI and performs no
   research or model work. The old preview remains verifiable.
4. Read that receipt. Pass its exact `current.manifest_path` and
   `current.manifest_sha256` to `python run_real_api.py --job <same-job>
   --manifest <new-manifest> --manifest-sha256 <new-digest> --output <new-export-dir>`.
   Use a new destination outside owner data. The CPU exporter/importer must pass
   geometry, textures, hinge samples, collider links and explicit pairing extras;
   then the Python gate validates pair associations independently before readiness.
   This real API export is pending, not established by the mocked tests.
5. Record technical results separately from visual/native usability. A later
   coordinated UI review must inspect the new door notice/sequence and selected-job
   export action. No UI interaction is authorized for this preparation turn.

Recovery: restore exact workspace/controller preimages only if current bytes still
match the installed candidate. Added exporter modules can remain unreferenced.
Preserve newly created preview/export directories, original worlds and all
historical receipts. Old immutable previews and036/037 evidence stay valid for
their original controller version; do not re-label them as sequenced039 output.
