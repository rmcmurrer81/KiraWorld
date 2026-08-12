# Blackwell Voice V17 consumed static-control run checkpoint

Recorded UTC: `2026-08-11T22:40:02.0422955Z`

## Exact outcome

The single differently accepted, bounded, no-argument V17 disconnected static
control invocation was already performed once. It exited `4` and wrote a
durable failure completion. `DO_NOT_RERUN_V17`; every available authority was
consumed by this terminal outcome.

The evidence progression was exact:

1. `entry = entered`;
2. `audit_seal_retained_handles = passed`;
3. `outcome_reservation = passed`;
4. `terminal = failed_consumed_no_retry`.

The packed 700-byte receipt contains a 336-byte reservation and 364-byte
completion. Completion state is `3 = RECORD_FAILURE`; terminal stage is `50`;
Python finalization returned zero; `FreeLibrary` succeeded; old-module and
exact-path absence checks passed; eight modules were enumerated.

## Cause boundary

Stage 50 is assigned immediately before `PyObject_CallObject`, and the same
failure branch covers either a null call result or rejection by
`result_exact`. V17 then clears a pending Python error without recording its
type/message, and the receipt records no call-return/result-validation
substage. Therefore the exact cause is
`UNRESOLVED_WITH_CURRENT_TELEMETRY`.

The retained V15 validator name, callable name, source filename, and expected
V15 result schema are mutually consistent. Their age alone is not evidence
that a stale-name mismatch caused this failure. Do not upgrade that hypothesis
to current truth.

## Exact evidence

- `RUN_EVIDENCE_V17.jsonl`: 386 bytes, SHA-256
  `269d1eadda20ca6a8a3d6e1679f80d850e32b79146aa562e22765fb624bad32b`;
- `STATIC_CONTROL_OUTCOME_V17.receipt.bin`: 700 bytes, SHA-256
  `83c7b11b7c458bdcd5aa75308fe24f5ceae9f700de672eb01affd1f900ffa21d`;
- `RUN_OUTCOME_V17.json`: 2,586 bytes, SHA-256
  `2651db197caa103b33b7d16fb718707a81cb3a5f2c9906246b775d7a46357dea`.

## Truth and next boundary

No model, GPU, synthesis, audible audio, playback, speaker, camera, person
state, body, Blender, or latency path ran. V17 proves no latency improvement.

Preserve V17 and its terminal evidence. An append-only V18 may add durable
pre-call, call-return, result-shape/schema/value, and post-validation substages
plus bounded sanitized Python exception type/message telemetry. V18 must be
author-sealed, remain disconnected/default-off, receive a different fresh
review, and may not run without a later exact one-shot acceptance.
