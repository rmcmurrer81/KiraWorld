# V3r31 single-blocker repair author checkpoint

Recorded UTC: `2026-08-12T04:00:00Z`

Author: `codex_r25_medical_reference_proxy_v3r31_two_stage_author`

Status: `STATIC_STAGE1_CANDIDATE_PENDING_DIFFERENT_AUDIT_A`

V3r31 is append-only scratch work. Nothing was written to Kira or ProgramData.
Neither native product, the materializer main, Blender, `bpy`, the worker,
audio, camera, a model service, save, reload, nor render was invoked.

The package preserves exact installed V3r30 evidence: 26/26 author artifacts
and 8/8 rejection artifacts. Its nested chain also rehashes 33/33 V3r29,
28/28 V3r28, and 17/17 V3r27 artifacts: 112/112 predecessor bindings total.
The V3r30 rejection remains controlling and is not rewritten as acceptance.

V3r31 addresses only `V3R30-A01-STAGING-DACL-HANDLE-ACCESS`:

- all seven staging-file handles request
  `GENERIC_READ|READ_CONTROL|WRITE_DAC` before `SetSecurityInfo`;
- the staging-directory handle requests
  `FILE_ADD_FILE|FILE_ADD_SUBDIRECTORY|FILE_READ_ATTRIBUTES|READ_CONTROL|WRITE_DAC|SYNCHRONIZE`;
- native reads back and compares canonical DACL
  `D:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x12019f;;;OW)` on all seven files and
  the directory before Blender;
- the cache-free test-owned Win32 transition probe reproduces
  `ERROR_ACCESS_DENIED` for both exact V3r30 masks, then proves successful
  DACL application and canonical readback for both exact V3r31 masks.

Preserved gates include handle-relative materialization consumption, stable
identities, single-link/non-reparse checks, no delete sharing, ProgramData
install authority, different Audit A and Audit B, all seven staging and eight
final handles retained through terminal success, and no execution authority.

Scope remains a nine-object normalized pelvic clinical-reference proxy. It is
not a body and proves no complete anatomy, physiology, functional organs,
sensation, rig, weights, activation, or Avatar Builder promotion. Downstream
policy remains: one shared person specification; evidence-based regional
anatomy/material variation; bald-first activation candidate; hair version
inactive pending the planned RAM upgrade.

The materialized and hard-disabled native sources pass `/W4 /WX`; both static
analyzer logs contain zero unsuppressed defects. The native products are
`DO_NOT_RUN` build evidence only. Final cache-free PreSeal and PostSeal results,
exact file inventory, seal root, PE inspection, and reproducible-build hashes
are recorded in the other frozen package artifacts.
