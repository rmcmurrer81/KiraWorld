# World060 public backup review — author re-review

Reviewed September 26, 2026 for **public experimental backup only**. No blocker was found for backing up the exact reviewed payload under `experimental/world-door-hardware-candidate-060/`. This is not installation, visual, owner, export-runtime, or finished VR approval.

The reviewer authored candidate060 earlier in this task. This is a fresh re-review of the frozen package, not an independent-author assessment. The parent separately reported reading the full source delta; that independent review is not replaced by this note.

## Integrity and scope

- Rehashed all **104** frozen payload files and all **104** public-manifest entries, including byte lengths and path containment. There are no mismatches, missing files, or path escapes.
- Recomputed the entire five-file diff from the preserved preimages and candidate bytes. It matches `SOURCE.diff` exactly. No sixth source file differs.
- Rechecked all **17** package producer file pins. The exporter controller pin matches the candidate controller. The public closure retains Three.js's license.
- Verified the manifest links: delivery to frozen/public manifests, frozen to public manifest, and frozen to the local preservation inventory. The latter inventory is deliberately not in the public payload.
- Read the complete five-file diff, relevant controller/metadata context, README, result receipts, staging/patch scripts and test-contract source. No staging, patching, rendering, installation, model, UI, or publication command was run during this review.

Frozen delivery SHA-256: `8af1c3cdd357b4989fa55db34b07d9bfa0d3da60af334c3f26253e23a26fcdfc`.

Frozen manifest SHA-256: `cbbc4a547647dab32a6d0574cd080ff9d8e2f2c65f6af26c00d07acbd3c195d7`.

Public manifest SHA-256: `639be7e162b492ba8d34fbcf4fd6bc286b8ff1f740c6fdcdaf16bb495bca5269`.

Machine-readable checks are in the new `AUTHOR-BACKUP-REVIEW-CHECKS.json`. Neither new review file is part of the original frozen set; preserve that distinction when backing them up.

## Five-file source review

1. **Preview walk controller:** the leaf/frame geometry and hinge poses remain unchanged. Four distinct local boxes cover the panels and the two handle/mount groups. Their transforms use the same hinge rotation as the leaf. This avoids making the entire leaf as deep as its handles. The sweep allowance includes hardware depth while retaining the leaf's far radial limit where it dominates. Door collision checks are batched at 128 parts, preserving the existing navigation bound and allowing all 24 supported doors to be represented. The second batch is checked rather than truncated.
2. **Package walk controller:** repeats the same collision changes and adds frozen local hardware definitions for metadata. The preview and package implementations agree on dimensions and transformations; this does not remove the maintenance risk of having two controller copies.
3. **Scene metadata:** validates exactly four hardware definitions, expected ordering, names, centers and sizes, and attaches their kinematic collider descriptions to the existing leaf node. It does not supply a game-engine collision adapter or persist door state. The metadata's explicit capability/limitation fields continue to deny finished VR, pressure simulation and owner realism approval.
4. **Producer pins:** only the two actually changed package source entries are refreshed. Other source and external dependency pins remain unchanged. External hashes are references; no external runtime binaries, fonts or model weights are added to the public package.
5. **Layout exporter:** only the preview-controller source hash is changed. This intentionally prevents an old056 preview from silently claiming newly corrected060 collision behavior. It requires a future exact preview; no new preview or GLB exists in this candidate.

The conservative collision boxes are a bounded correction, not rigid-body physics. Existing room dressing is not rewritten. Candidate059's room-plan work remains separate and must be merged deliberately with these pins before any combined install.

## Public exclusions and publication instructions

Publish by the explicit public file allowlist, **not by recursively copying the candidate directory**. The 104 entries consist of source/preimages, synthetic fixtures, implementation/reproduction scripts, bounded historical test evidence and documentation. There is no raw owner world file, model-weight file, media file, database or credential file in that set. A high-confidence credential-pattern scan of all public text found no hits; this is an additional check, not a proof that arbitrary secrets are impossible.

`OWNER-PRESERVATION.local.json` must remain local. It contains the owner-file preservation inventory and is not needed to distribute source. The frozen manifest includes its digest, but not its private contents.

The three original receipt files `DELIVERY.json`, `FROZEN-MANIFEST.json` and `PUBLIC-BACKUP-MANIFEST.json` sit outside the self-referential public file list. They may be added explicitly as package evidence, preserving their hashes. This new author review and its checks may also be included explicitly as later evidence. Do not add unrelated new files merely because they share the directory.

The backed-up `stage.py` and `patch_candidate.py` are development reconstruction scripts, not installers. They are not commands to execute on the reader's live world. The local contract test depends on intentionally excluded owner inventory and a machine-specific saved preview; the README and dependency file identify that constraint. The portable CPU hardware test additionally depends on the separately preserved059 room-plan source. This is a source/evidence backup, not a self-contained installed product or an assurance that every development command runs on another computer unchanged.

## Claims review

The README correctly treats 321,108 as assertions across CPU checks, not independent tests or visual judgments. Its 540 pose samples are five layouts, two controller consumers, six doors and nine poses. The original 12 collision cases become 24 checks across two consumers; the counts are consistent rather than separate bug totals.

The README correctly distinguishes the saved056 preview's historical verification from the mocked exact060 admission boundary. It does not claim a generated060 preview, portable GLB validation, native walk-through, owner acceptance, pressure simulation or full VR support. `CONTRACT-RESULT.json` explicitly discloses the mocked boundary and un-rehashed external dependencies.

The 116 owner-file and 42 canonical-file preservation statements are results of the recorded candidate construction/checks. This review verifies their bound receipts; it does not claim a fresh owner-state audit beyond that evidence or authorize replacing any owner file. The current installed World056 remains outside this backup's write scope.

The `history/OVERBROAD-SWEEP-*` files preserve a superseded variant that moved plaques. The README explicitly rejects it as the delivered candidate. Keep that history clearly labeled; do not promote its output over the final hashes.

Remaining steps before any later installation are unchanged: independent source signoff, deliberate059+060 integration and source/export binding verification, a new exact preview where required, and native inspection once computer interaction is permitted. This public-backup review does not complete those steps.
