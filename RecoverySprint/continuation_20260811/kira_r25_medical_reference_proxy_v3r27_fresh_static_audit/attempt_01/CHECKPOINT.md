# V3r27 different fresh independent audit checkpoint

Recorded UTC: `2026-08-11T23:32:35Z`

Auditor: `codex_r25_medical_reference_proxy_v3r27_independent_auditor`

Author: `codex_r25_medical_reference_proxy_v3r27_static_author`

## Exact verdict

`REJECTED_NO_EXECUTION_AUTHORITY`

Do not run V3r27. No 14-row acceptance TSV or digest sidecar was created.
This review did not invoke Blender, `bpy`, the candidate, V3r26, AFES, body,
save/reload/render, model, camera, voice, network, or Sarah. Kira remained
read-only; all audit artifacts are staged under Documents/Codex.

## Exact positive findings

- Installed author package: `11/11` exact before and after.
- Sealed subjects: `8/8`; canonical bytes: `799`; package root:
  `180db0c53f1c6144249a73c5304fd44c976945cb8b427d2370e9b15bb8ed4976`.
- Seal: 2,092 bytes, SHA-256
  `60d8153688a9b5163adcd5a0ab2983bf2ca96518d011bdeda309076aca2c5ef6`.
- Upstream closure: `24/24` exact: 10 V3r26 author, 6 different
  audit, 4 consumed-run, 3 anatomy-triage, and 1 root-triage rows.
- Installed cache-free PostSeal passes with 24 upstream, 7 licenses,
  24 components, 9 Stage-A rows, 136 bones, and 9 author mutants.
- Independent cache-free syntax passes `2/2`.
- All seven license-source hashes cross-check to the sealed triage TSV.
  CC BY-NC and unknown-license quarantines remain exact.
- All 136 skeleton identifiers remain unmapped; Stage A uses no rig/weights.
- No source import/export, network, subprocess, live-avatar, activation, or
  Sarah surface was found in the exact builder.

These positives remain static evidence only and do not outweigh the blockers.

## Blocking findings

### 1. Audit authority is replaceable rather than externally anchored

The candidate accepts any auditor string beginning `codex_` if a 14-row TSV
and its sibling digest agree. It embeds no expected audit SHA-256 or exact
auditor identity. `CHECKPOINT.md` is checked only for existence; its bytes are
never read or hashed.

An in-memory hostile probe generated a self-consistent audit for
`codex_forged_local_writer`; it passed. Another in-memory probe appended a
harmless comment to the script, regenerated the script seal row, package root,
seal bytes, audit TSV, and digest; the candidate-equivalent checks accepted
the modified closure. No Kira file was changed.

A trusted root rehash of predeclared audit bytes can block a mutation that
already exists. It does not become an in-process binding, and V3r27 holds no
stable audit/seal handles, so replacement between root rehash and candidate
read remains. This is blocking under the current one-shot path/object threat
model; it is not claimed to be a remote-security boundary.

### 2. Reload validation can accept a false proxy scene

`validate_proxy_scene()` checks only nine tagged component IDs, `MESH` type,
aggregate vertices `1..12000`, at most six materials, absence of armature/
action/image datablocks, and two false truth booleans.

The independent logic-equivalent hostile scene used nine one-vertex meshes,
all co-located, zero materials, and wrong attribution strings. It passed the
exact predicate. Locations, dimensions, per-object topology, relation gates,
non-overlap, material assignments/node values, attribution values, modifiers,
constraints, parents, libraries, external dependencies, and the complete
scene/data inventory are not validated after build or reload.

Therefore a later success could overclaim that the intended medical-reference
proxies were built, saved, and reloaded when the saved geometry/material truth
does not match the sealed plan.

### 3. Placement and view contract contradictions

The placement plan declares eight required Kira landmarks and says to fail
closed for missing landmarks, unaudited height, and unknown outer-shell
clearance. None of those eight landmarks is read by the builder; it uses only
hard-coded normalized priors. The package correctly denies an absolute Kira
fit, but the executable does not implement its declared fail-closed plan.

The plan defines positive Y as anatomical anterior. `front_clinical` places
the camera at `(0.0, -1.55, 0.10)`, which observes from the posterior side.
The render name is therefore wrong under the package's own coordinate frame.

### 4. Blender input and saved-file closure are not bounded

Background mode and the Kira working directory are checked. The script does
not bind the Blender executable/version, factory-empty startup, loaded input
file identity, disabled auto-execution state, or absence of external
libraries/dependencies. It deletes the objects in whatever background scene
was loaded and does not reject all surviving datablock families.

### 5. Output and render evidence are path-raceable and under-validated

Output absence is checked by path, then receipt/evidence/output creation and
later Blender writes occur without stable directory/file identities or
reparse-point checks. Blend and render files are not exclusively reserved;
save/render use overwrite behavior.

Each render passes on existence plus 1,024 bytes. PNG signature, decoded
640x640 dimensions, proxy visibility, nonblank content, distinct camera views,
and a final rehash of all outputs are absent. A path replacement or late file
mutation can separate success evidence from the files later reviewed.

### 6. Partial reservation and terminal states are not closed

The receipt is created first, but `reserved=True` is assigned only after the
whole reserve function returns. Failure after receipt creation but before
evidence/output completion gets no terminal-failure update. The failure path
writes no `RUN_OUTCOME.json`.

On success, `RUN_OUTCOME.json` is written before terminal-success evidence and
before the receipt is rewritten non-exclusively. A later error can leave a
success outcome beside a failure receipt. Authority would still be consumed,
but the promised terminal evidence would be partial or contradictory.

## Required append-only repair

Preserve V3r27. A V3r28 successor must, before another different audit:

1. bind an external exact audit identity and every audit artifact, then retain
   stable non-reparse path/object identities through reservation;
2. bind an exact factory-empty, autoexec-disabled Blender command and runtime;
3. validate every proxy's geometry, transform, placement relations, materials,
   attribution, modifiers/parents, and full saved/reloaded scene closure;
4. reconcile or implement the normalized landmark rules and correct the front
   camera axis;
5. exclusively reserve bounded outputs, decode/validate all four renders, and
   write a final immutable output manifest; and
6. use consistent append-only pending/success/failure terminal evidence that
   remains truthful after any partial failure.

V3r27 is not Kira's body and proves no anatomy, physiology, function,
materials/pigmentation, rig/deformation, hair, activation, or Avatar Builder
promotion.
