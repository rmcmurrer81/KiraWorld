# Fresh independent audit request — Avatar Builder Qwen 3.5 visual intake v2 — 2026-08-09

Requested status: `PENDING_FRESH_INDEPENDENT_ADVERSARIAL_AUDIT`

Audit v2 as a disconnected static evidence route, not as a live Qwen, visual
accuracy, identity, body-authoring, or owner acceptance. Preserve v1 and the
first audit byte-for-byte. Do not call Ollama, load a model, use the GPU, decode
a real source video, launch Blender, mutate a profile/body/R25 file, activate a
person, or publish anything. Use temporary fixtures for hostile probes.

## Exact v2 audit set

- `Core/avatar_builder_qwen35_visual_intake_v2.py`
  - `2faa914d2aae3165fbb5f20850d94b320200f04cc30cf9d8cd79014d371fe28b`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_contract_v2.json`
  - `2dbc4e280b70efe6772ae7c25243f252cc73caa6f8b0dd8dc72e5cbd2d2d1bc0`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_owner_authority_registry_v1.json`
  - `e69c845427103c8166811ee5da0b3082ce9b5d8a406b87b51c74625b5180e0ac`
- `tools/prepare_avatar_qwen35_visual_intake_v2.py`
  - `b994501c11dae0519b8dde5d5b5069dd35319c6b538ea0b780f2eef38878b1d2`
- `Testing/test_avatar_builder_qwen35_visual_intake_v2.py`
  - `630bca0330a3704f3213e92635cd00e3b4cad0c5fcaf7a30b7dabb44485c8c2a`
- `System/Docs/AVATAR_BUILDER_QWEN35_VISUAL_INTAKE_V2_REPAIR_CHECKPOINT_20260809.md`
  - `da54619500f582179fda53bd5737fd1c26a9e3f41e90e034ab9c94cde7ee26fd`

First verify that the preserved rejected audit remains:

`System/Docs/AVATAR_BUILDER_QWEN35_VISUAL_INTAKE_INDEPENDENT_AUDIT_20260809.md`

SHA-256:

`41f925851f1b8516389f9c26fccae1e5f24d98ee1ac5bb8966947c081123f75a`

## Required adversarial probes

1. Prove the public preparation API has no evaluator/authority injection and
   rejects every caller field beyond IDs and exact model identity.
2. Try to forge an adult/non-adult plan, recompute its ordinary hash, and
   consume it. It must fail after real external preflight reconstruction.
3. Test valid hash-chained exact-person corrections in every direction:
   adult to non-adult, adult to unresolved/age-up, and non-adult to adult.
   Test both unacknowledged and falsely authority-acknowledged corrections.
   The exact canonical profile bytes must carry the matching event IDs/hashes.
4. Test fictional/historical version and timepoint disagreement between owner
   selection, canonical profile, correction memory, and the registered
   authority. Change the authority event while leaving the profile's exact
   selected-event ID/SHA binding behind. Every unresolved conflict must fail.
5. Spoof `subject_kind`, Robert-selection booleans, rights, provenance, source
   paths, and source hashes in the request. None may become authority.
6. Feed a signature-only fake image, decompression/dimension abuse, malformed
   receipt, time beyond duration, PTS/time-base mismatch, changed parent/frame,
   and independent re-extract mismatch. All must fail without decoding video.
7. Prepare a plan, then independently change source, profile, registry,
   creation request, correction memory, authority artifact, contract, and
   extractor receipt. Consumption must invalidate the plan. Check same-opened
   image bytes are the bytes returned for future encoding.
8. Put identity, age/maturity, body/profile mutation, filesystem operations,
   activation, assignment, publication, Blender/tool execution, and
   instruction-override language into every free-text output field. All must
   remain non-executable and fail the defense-in-depth policy.
9. Use two opaque IDs for one path, hard links, byte-identical copies, and the
   same verified video sample. They must not manufacture a two-source
   contradiction.
10. Try absolute paths, traversal, symlinks, `.blend`, profile/policy paths,
    an existing plan filename, and race-relevant duplicate creation against the
    CLI/core output. Only a new JSON under the dedicated v2 roots may appear;
    every sentinel must remain unchanged.
11. Confirm the exact contract SHA is loaded, exact `qwen3.5:9b` digest is
    bound, the descriptor carries the full schema and exact subject ID, and no
    fallback model exists.
12. Inspect imports/calls and prove no network, Ollama client, subprocess,
    model, GPU, video decoder, Blender, body mutation, activation, assignment,
    or publishing path exists.

Do not treat the intentionally empty production owner-authority registry as a
live feature failure. Verify instead that it fails closed and that no real
subject can run until a separate exact authority artifact/profile
reconciliation is registered. Conversely, do not describe an empty registry
or passing temporary fixtures as owner acceptance or live readiness.

Publish a new append-only audit document with exact audited hashes, commands,
all hostile-probe results, remaining blockers, and a decision that separately
classifies:

- static v2 repair correctness;
- readiness to register owner authority;
- readiness to implement a bounded live worker;
- live Qwen visual accuracy acceptance;
- readiness for body-authoring translation or runtime activation.

Only the first classification is presently claimed. All later classifications
remain `NOT_IMPLEMENTED_OR_NOT_RUN` unless independently proven in a separately
authorized successor.
