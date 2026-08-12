# Kira Runtime Repair — Post-Change Evidence Package

Captured: 2026-07-22T23:01:12-04:00

This is a **post-change evidence snapshot**, not a pre-change rollback package.

The runtime files are untracked in the current worktree, and no trustworthy byte-for-byte copy of their immediate pre-change state was available when this package was made. Earlier SHA-256 observations are recorded below for provenance, but hashes alone cannot restore files. Do not describe this package as an exact rollback.

Kira was not activated for this work. The results are syntax, unit, deterministic-math, and static-source evidence only. They are not audible or visual proof of live behavior.

## Included payload

- `runtime/kira_world_shell_server.py`
- `runtime/main.js`
- `runtime/existing_mouth_lipsync.js`
- `verifier/verify_kira_movement_realism_r5.mjs`
- Seven focused changed test files under `tests/`

Dedicated eye assets and eye-specific test files are intentionally excluded. `runtime/main.js` is the exact current combined runtime file at capture time; it was copied without further editing.

## Exact behavior/change summary

### Person-owned body intent and routing

- Explicit Kira replies containing `sit`, `sitting`, `take/taking a seat`, or `have/having a seat`, together with `couch` or `sofa`, publish `sit_on_couch`.
- A request about walking/outside publishes `go_outside` only when Kira's own spoken reply affirmatively mentions walking, heading/going out, or stepping outside. A user request alone is insufficient.
- `go_outside`, `walk_outside`, `head_outside`, and `exit_home` dispatch to a self-chosen, collision-aware front-door route.
- The exit route uses interior threshold, doorway center, exterior threshold, and outside-walk waypoints; it does not teleport the body.

### Comfortable idle posture

- The calibrated arm evidence identifier is now `calibrated_bind_axis_joint_limited_swing_v10_relaxed_elbow_hand_asymmetry`.
- Left and right relaxed elbow/finger defaults intentionally differ slightly to reduce the symmetric mannequin stance while retaining joint limits and the already calibrated bind-axis behavior.

### Existing-mouth playback

- Lip motion still deforms only the existing connected lip island. It does not instantiate a second mouth mesh.
- The bounded speech target floor was raised so quiet speech is less likely to produce an imperceptibly small aperture; the existing hard safety cap remains in force.
- Runtime evidence now retains matched playback segments/frames, current playback frames, matched revision, completed playback frames, and peak mouth amount/opening. Counters advance only when actual active-avatar audio playback matches the current reply revision.
- This is speech-timed deformation evidence, not phoneme/viseme accuracy proof.

### Text-to-audio startup

- Approved Chatterbox replies may use a short first voice chunk (default target 72 characters, clamped to 48–96) at a natural boundary.
- Very short complete replies remain one chunk, and all spoken words are preserved in order.
- The approved Kira voice identity/model configuration was not changed.
- Static tests do not prove an audible latency reduction; live timing must be measured after relaunch.

### Verifier-only correction

- Required arm evidence changed from `calibrated_bind_axis_joint_limited_swing_v8` to `calibrated_bind_axis_joint_limited_swing_v10_relaxed_elbow_hand_asymmetry`.
- The couch assertion changed from the old `sit|sitting` check to the current explicit `sit/sitting/take-a-seat/have-a-seat` check plus a required `couch|sofa` target.

## Earlier observed hashes without rollback copies

- `tools/kira_world_shell_server.py`: `6224a5bbe146e77dab0044f16a6e898b86fe81eee65b86aa922efcbe2af872fb`
- `preview/src/main.js`: `bb1682a38f6cfbe715c7adb7e0f997ac205b7f77d321b84ece2dc60310421228`
- `preview/src/existing_mouth_lipsync.js`: `e5ea766bc6c817ffee5d33ea4fe0f6dbc01ba3d20f23ec38594fd6a29ba85d90`

These are provenance observations only. No claim is made that they identify a restorable or complete immediate pre-change set.

## Safe owner validation after relaunch

1. Close and relaunch the Kira World shell so the current server and browser bundle are loaded.
2. The owner may activate Kira once and ask whether she wants to sit on the couch or walk outside; she may refuse.
3. Confirm that an accepted action produces a real route rather than only spoken narration.
4. Observe the existing lips during actual voice playback and inspect the new matched-playback counters afterward.
5. Compare first-chunk synthesis timing in the voice log; do not infer improvement solely from this package.

