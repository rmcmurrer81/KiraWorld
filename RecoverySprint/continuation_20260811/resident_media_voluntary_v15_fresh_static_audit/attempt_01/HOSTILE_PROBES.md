# Resident-media V15 fresh independent hostile probes

Date: 2026-08-11

Reviewer: `codex_root_resident_media_v15_fresh_independent_validator`

Verdict: `ACCEPT_STATIC_NO_COMMIT_ONLY`

## Exact closure

The V15 seal was parsed independently. Its five current subjects, preserved V14 seal, and three preserved V14 rejection artifacts formed nine unique rows. All nine paths matched their exact byte counts and SHA-256 digests before testing and again afterward. The seal itself was 3,156 bytes with SHA-256 `9ca92ea13cff61cd0681abd9aae6244071eaac6bfb3e97e2bfab6034d447148b`.

## Preserved negative control

The V14 stale-digest exploit was reproduced on a disposable in-memory V14 validator: ordinary method-closure traversal reached `_SnapshotStateV14`; its retained `StimulusCatalog._manifests` was changed while the cached catalog digest stayed unchanged; V14 then emitted a plan whose catalog contents and reported digest disagreed. No sealed predecessor bytes or external state changed.

## V15 independent probes

- Constructed V15 only from canonical caller-supplied snapshot bytes and an exact digest. The authority test double's state was unchanged before and after construction, validation, and refusal probes.
- Traversed ordinary Python methods, closures, cells, containers, weak dictionaries, tuple/list/set values, and object slots reachable from the V15 validation method. No `StimulusCatalog`, `_SnapshotStateV14`, weak-key state registry, authority instance, adapter instance, ledger instance, anchor, receipt history, CAS callable, or commit capability was reachable.
- Validated a complete three-role video evidence example. The return value was an exact built-in tuple of length two: immutable canonical JSON bytes plus a lowercase SHA-256 equal to a fresh digest of those exact bytes.
- A byte change with the original digest was refused. Attempted mutation of the built-in tuple class was refused by Python. Decoding returned a fresh mapping rather than mutable state retained inside the envelope.
- The emitted record declared `commit_attempted=false` and `durable_record_created=false`; the exact record method raised the required `no commit surface` error.
- The production status remained disconnected. The candidate expressly reports that caller snapshot bytes are not protected-authority truth, the static plan is not a durable record, and Python class methods are not claimed non-substitutable.
- Focused tests passed 20/20. The preserved V3-through-V15 suite passed 230/230. Both Python sources compiled strictly in memory.

## Acceptance boundary

This acceptance is intentionally narrow. V15 is an inert, disconnected no-commit component that can package a self-consistent static validation result. A separately protected external/native broker would still need its own exact authority, consent, anti-rollback, commit, and readback review before any durable or production use. Arbitrary same-process Python code can fabricate ordinary Python data, so no consumer may treat a V15 tuple as protected authority merely because it came from this module.

No media file was opened, decoded, rendered, played, or presented. No model, network, camera, microphone, GPU, audio device, person, memory, preference, relationship, body, Blender, or Sarah state was used or changed.
