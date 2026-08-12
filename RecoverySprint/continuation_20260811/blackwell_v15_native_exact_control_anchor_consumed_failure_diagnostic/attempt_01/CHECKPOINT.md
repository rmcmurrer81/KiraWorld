# Blackwell voice V15 consumed stage-10 failure diagnostic

Recorded UTC: `2026-08-11T17:34:17.2150043Z`

Status: `CONSUMED_FAILURE_DO_NOT_RERUN_V15`

The exact accepted V15 native executable was invoked once by root, returned
exit code `4`, and created neither `RUN_EVIDENCE.jsonl` nor
`STATIC_CONTROL_OUTCOME.receipt.bin`. Success or failure consumed its only
authority. V15 must never be invoked again.

This diagnosis was read-only. It did not invoke V15, the Python candidate, a
model, GPU, synthesis, audio, playback, or latency measurement, and it did not
edit Kira.

## Exact cause

The failure is deterministic at V15's stage-10 seal grammar, before output.
The 4,557-byte sealed manifest stores all 21 subject objects in compact form:

`{"path":"...","bytes":N,"sha256":"..."}`

V15 `seal_contract_exact` instead searches for the spaced object/build path
fragments `"path": "..."`. Both counts are zero; the corresponding compact
fragments each occur exactly once. V15 `seal_exact_row` repeats the same defect
for every binding by independently searching for spaced `path`, `bytes`, and
`sha256` fragments. All 21 spaced path fragments are absent, while all 21
complete compact rows occur exactly once.

Therefore `seal_contract_exact` necessarily returns false at lines 1219-1227.
`wmain` branches to cleanup from lines 1335-1338 while the coarse stage remains
`10`; stage `20` and output creation at lines 1356-1362 are unreachable. Even
if the object/build sentinel were removed, every old `seal_exact_row` call
would still fail.

The exact V15 native source is 70,512 bytes, SHA-256
`5563fb180e3295f2258ea02c89c4a7c54e8a729da73ea0f0c76ab6d3e557c951`.
The exact V15 seal remains 4,557 bytes, SHA-256
`f3d451041796c2bfbdf5dbe52f3a485b227f67b01af051e9e95c35b40549d932`;
all `21/21` subjects still rehash exactly with `21/21` unique paths.

## Append-only boundary

Preserve every V15 source, binary, seal, audit, and accepted-then-consumed
authority byte. A successor must use a new V16 identity and new one-shot audit.
It must match a complete exact compact manifest row rather than independent
whitespace-sensitive fragments, reject duplicates and field splicing, and
prove the compact format against the generated PostSeal manifest with hostile
mutations before any different review.
