# Resident-media V13 independent hostile probes

Recorded UTC: `2026-08-11T10:13:47.3992896Z`

Verdict: `REJECT`

## Exact preservation and positive checks

- V13 seal closure: `10/10` exact before and after review, zero drift.
- V13 seal: 2,777 bytes, SHA-256
  `6860f7e1c0acb6ae50f704a2ed1291af76054d1ef0da90081b82e2e99298d852`.
- V13 core: 18,064 bytes, SHA-256
  `202588befbce062d8e50626902c8efb0513aceb73426caba8cd320872db8c492`.
- V13 test: 25,643 bytes, SHA-256
  `614e78231c0bf63b9a5e8abe276202856375bb1c80773391b69355281b97748e`.
- Preserved V12 seal: 1,411 bytes, SHA-256
  `7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66`.
- Preserved V12 rejection checkpoint: 6,289 bytes, SHA-256
  `cdafe2169a6580b2586366bc2c6e0774f5f802f30ee76be0573d4dd89b54eb30`.
- Strict in-memory compile: `2/2` pass.
- Focused V13 suite: `15/15` pass.
- Preserved V3–V13 suite: `191/191` pass.
- Untouched-path probes with missing page, video-frame, video-audio, or
  video-caption roles, and probes with false/zero completion values, all
  refused at revision 0 with exact authority state unchanged.

## Blocking probe 1 — exposed rejected inner commit surface

The public V13 object exposes its V12 ledger through `ledger._inner` (assigned
in the V13 core near line 333). Calling the inner V12
`validate_and_record_static_evidence` directly with all caption segments
removed and both completion flags false succeeded. The rejected inner ledger
committed a record and advanced revision `0 -> 1`; the result retained
`caption_complete=false`.

No monkeypatch or file change was required. V13's outer checks therefore do not
protect the actual commit point from ordinary access through the returned
object.

## Blocking probe 2 — runtime code and preflight are not bound

V13 normally imports mutable V4, V9, and V12 modules and calls mutable module
globals at runtime. Ordinary rebinding of `v13._preflight_complete_evidence`
allowed the public V13 ledger method to commit a one-millisecond-incomplete
audio record with `audio_complete=false`, advancing revision `0 -> 1`.

There is no exact self-module/package or function/class/member/code/default/
global/closure precommit and post-readback identity anchor.

## Blocking probe 3 — exact-type walker can be replaced

Ordinary rebinding of only `v13._require_exact_string_types` to a no-op allowed
the public V13 method to commit:

- `output_receipt_id=true`;
- `output_surface_id=true`;
- a 64-digit JSON integer decoder digest.

Accepted evidence retained a boolean surface and integer digest while ledger
receipt history contained a string digest. This reproduces V12's scalar alias
across the claimed V13 boundary.

## Scope

No live media, model, device, person, audio, video, body, Blender, Sarah, or
production route ran or changed. These probes were static/disconnected. A V14
successor must repair append-only and receive another different review.
