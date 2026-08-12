# Blackwell voice V15 consumed static-control failure diagnosis

Date: 2026-08-11

Status: `CONSUMED_FAILED_BEFORE_OUTPUT_RESERVATION_DO_NOT_RERUN_V15`

## Observed one-shot result

The different fresh review accepted V15 only for one bounded disconnected
static-control validation. Root transcribed the exact accepted audit and
sidecar, rechecked the sealed package, and invoked the no-argument native V15
control image exactly once. It returned exit code `4`.

Both fixed output paths were absent before the call and remain absent:

- `RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/RUN_EVIDENCE.jsonl`
- `RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/STATIC_CONTROL_OUTCOME.receipt.bin`

The accepted one-shot authority is consumed regardless of success. V15 must
not be invoked again.

## Exact static cause

The failure is deterministic and occurs in native stage 10, before output
reservation. The sealed manifest is valid JSON, 4,557 bytes, SHA-256
`f3d451041796c2bfbdf5dbe52f3a485b227f67b01af051e9e95c35b40549d932`,
with 21 unique exact subjects and zero hash drift.

The V15 verifier does not parse those subject rows as JSON. Its
`seal_exact_row` function constructs textual tokens in the form
`"path": "..."`, `"bytes": ...`, and `"sha256": "..."`. The sealed manifest
stores every subject row in compact canonical form: `"path":"..."`,
`"bytes":...`, and `"sha256":"..."`.

An independent read-only count over all 21 parsed subjects found:

- spaced `"path": "..."` tokens: 0 total, with count 0 for every subject;
- compact `"path":"..."` tokens: 21 total, with count 1 for every subject.

The two sentinel path strings inside `seal_contract_exact` have the same
mismatch: both spaced tokens occur zero times and both compact tokens occur
once. The six pretty-printed top-level metadata tokens occur once, so the
first deterministic rejection is the compact object-path sentinel. Even if
that sentinel were bypassed, the first `seal_exact_row` call would reject for
the same format assumption.

Therefore the invocation stopped before `stage = 20`, before `CreateFileW`
for either output, and before private Python loading. It did not call a model,
GPU, Torch, CUDA, Chatterbox, synthesis, audio, playback, latency measurement,
person state, network, body, Blender, or Sarah path.

## Preserved audit truth

The different V15 review remains a valid static finding. Exact review hashes:

- `INDEPENDENT_AUDIT.tsv`: 920 bytes, SHA-256
  `38f1ac1902d7547fe161204d7fd61d3aa493e971108133bbbd9a6b61844af128`;
- `INDEPENDENT_AUDIT.sha256`: 65 bytes, file SHA-256
  `effe3c23d7e2c5b7f65a07fd225ec84b87d01e668728a2f61678a6bc9382ad5f`;
- `AUDIT_DECISION.json`: 6,899 bytes, SHA-256
  `c525ab16cfad6c6c25f2cbbb8d48a02ec57bdef55832821dc761db731ac80ffe`;
- `REVIEW_PROBES.md`: 9,787 bytes, SHA-256
  `082e5fda87136eefd02e5913aca0b89d165eee8da138a1156cf6a49cef5393f8`;
- review `CHECKPOINT.md`: 5,280 bytes, SHA-256
  `5e6a0799da297b962e9bb9dc9973bcc14d8cce252a0f4e9ccf438e13084f2822`.

Those records prove only that V15 closes the four V14 static-control defects
and was acceptable for the single disconnected check. They do not prove that
the check completed, that Python ran, or that voice latency improved.

## Append-only successor boundary

Preserve all V15 author, seal, audit, and consumed-failure bytes. Continue only
as V16. V16 must parse and validate the manifest structurally with an exact,
duplicate-rejecting canonical JSON grammar or bind one exact canonical byte
encoding; it must not depend on whitespace-sensitive substring searches. Its
author suite must reproduce V15's compact-manifest rejection, accept the exact
intended V16 encoding, reject duplicate keys/paths and scalar aliases, verify
every row and the exact row set, remain disconnected/default-off, and receive
a different fresh audit before any one-shot invocation.

No V15 rerun is authorized.
