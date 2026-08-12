# Blackwell voice V16 different fresh static review probes

Recorded UTC: `2026-08-11T18:24:01.7062503Z`

Decision: `REJECT_STATIC_NO_EXECUTION_AUTHORITY`

The exact V16 closure is intact, but the exact compiled parser does not meet
its structural/canonical, duplicate-rejecting, wrong-total-row contract.
`DO_NOT_RUN_V16`. V15 remains consumed and `DO_NOT_RERUN_V15`.

## Boundary honored

- Kira was read only. All compiler, analyzer, and harness outputs were created
  under `Documents/Codex/2026-08-11/c/work/voice_v16_audit`.
- Neither the sealed V16 executable nor the consumed V15 executable was run.
- Python was not invoked. The author PowerShell suite was not run because it
  shells to `py -c`; equivalent JSON/closure checks were performed with
  PowerShell/.NET under this audit's no-Python boundary.
- No model, GPU, Torch, CUDA, Chatterbox, synthesis, audio, playback, latency,
  network, process, person-state, body, Blender, or production route ran.
- V16 `RUN_EVIDENCE.jsonl` and `STATIC_CONTROL_OUTCOME.receipt.bin` remained
  absent before and after review.

## Controlling truth and exact author package

The reviewer read the current truth supersession registry, current test
execution boundary, handoff, V16 native contract, author package, runtime
checkpoint, author build results, and 41-row seal. The current boundary says
that only a new structural/canonical duplicate-rejecting V16 repair with a new
seal and different audit could precede at most one bounded disconnected
static-control validation. It grants no model/audio/latency authority.

Author identities rechecked:

- seal: 9,065 bytes,
  `b02ecdace1727a5ab9e8dba9a580932fe886e9ae05561f5241b1fbbffc21acd4`;
- V16 source: 76,837 bytes,
  `080b88e35f29062c9212574a60b1a52ade2770547065ef82eea6538568b69a8e`;
- header: 3,896 bytes,
  `62fdcc185dc11f1c489edf9a59f0c74ed9687377a0d934f91be3bd0315b0387b`;
- sealed executable: 182,784 bytes,
  `dc688ea754a9003654f1981f670f20cc3109166326a33233a88a1712a34f80f0`.

All 41 subjects rehashed exact before and after review, with 41 unique paths,
41 exact compact complete rows, zero mismatches, and closure-table aggregate
`25e17ef12188944d23615cdf6fd4118d9433cb88270052cef0eca13c23ad9b7a`.
The per-row evidence is `CLOSURE_REHASH.tsv`.

## Independent V15 failure reproduction

The 4,557-byte V15 seal contains 21 subjects. For each subject, the old spaced
path token count is zero while the compact path token and exact compact
complete-row counts are one. Totals:

- old spaced path matches: `0/21`;
- compact path matches: `21/21`;
- exact compact complete rows: `21/21`;
- object spaced/compact: `0/1`;
- build spaced/compact: `0/1`.

This independently confirms the consumed V15 stage-10 whitespace mismatch.
It does not validate V16.

## Independent native build and PE inspection

The exact Kira V16 source was rebuilt in isolated scratch with MSVC x64
19.50.35730 using `/W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE
/std:c17 /I C:/Python314/include`. Build exit was zero with zero diagnostics.

- independent object: 115,366 bytes,
  `d786f6d22c79da23546b5f82aefa7ba45c77bb4728b9927534a68f2a092f1017`;
- independent executable: 182,784 bytes,
  `6391cb758590ca6188534c9d14be22a8de79c42cca438e85af3e6488ef391a9e`.

Independent `/analyze /W4 /WX /c` also exited zero with zero diagnostics:

- analyzer object: 69,918 bytes,
  `4aba77f2488c456cab3d9a1c1dec50188216bead9ffa561386b8482568c07904`;
- empty 59-byte analyzer report,
  `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`.

Both independent and sealed binaries inspect as x64 PE32+, High Entropy VA,
ASLR/Dynamic Base, NX, CFG, CF-instrumented with FID table, and `0x33` Guard CF
functions. The only dependent DLLs are `bcrypt.dll` and `KERNEL32.dll`.
There is no static Python, process-shell, audio, or network import.

These clean build facts do not override semantic parser failures.

## Exact compiled parser harness

The harness source renames V16's `wmain` before including the exact sealed C
source. Its own `wmain` calls only `canonical_relative_path`,
`seal_exact_row`, and `seal_contract_exact` on in-memory strings and a
read-only copy of the current seal. The candidate entrypoint is unreachable
and was not invoked.

- harness source:
  `34afd7f31184e68b8ba51c52492830633ecce4724787ac8ce1cef5cc8c2e780c`;
- harness executable: 181,760 bytes,
  `4c63d64619cd28a5e144ea91d2c574b2526d817787f798afa0e5951c4c1e6e92`.

Expected refusals that passed include missing rows, duplicate exact compact
rows, required-row whitespace and case mutations, wrong bytes, wrong/uppercase
digest, leading-zero decimal bytes, path-only/bytes-only/digest-only decoys,
cross-row splicing, backslashes, empty segments, interior dot segments, and a
NUL-bearing seal.

Four expected-refusal assertions failed:

1. `canonical_relative_path` accepts terminal `tools/.` and `tools/..` paths.
2. `seal_contract_exact` accepts the current seal plus a trailing non-NUL
   byte, proving it does not validate a complete JSON document.
3. A valid JSON mutation containing 42 subjects is accepted when the added
   subject is a whitespace-formatted logical duplicate of the V16 source row.
4. In that mutation, `seal_exact_row` continues to accept the original compact
   source row once, so the combined gate misses the duplicate.

The valid bypass mutation independently parses as:

- actual subjects: `42`;
- unique paths: `41`;
- declared `sealed_subject_count`: `41`;
- compact `{"path":"` prefixes: `41`;
- exact compact source rows: `1`;
- logical source-path occurrences: `2`.

This directly contradicts the contract's whitespace-mutated-row,
duplicate-complete-row, wrong-total-row, canonical-path, and structural-match
refusals. The author test only models token counts in PowerShell; it never
executes the exact C parser functions and therefore misses the bypass.

## Additional provenance defects

The V16 source also retains three stale V15 identities:

- binary receipt magic strings are `KIRA_BLACKWELL_V15_RESERVATION` and
  `KIRA_BLACKWELL_V15_TERMINAL` even though the paths and JSONL schemas are V16;
- `verify_audit_handles` assigns V15 relative-path strings to V16 audit paths;
- the V16 seal binding label says `complete V15 static seal`.

The latter two strings are not consulted by current handle verification, so
they are not presented as a bypass. They are exact provenance defects that a
successor must remove. The V15 receipt magic would make any future V16 outcome
record version-ambiguous and must be corrected before a run.

## Required append-only repair

Preserve V16 unchanged. V17 must use a bounded whole-document parser or an
equivalently exact grammar; require exactly the actual expected unique subject
rows; reject any malformed structure, trailing bytes, extra row, duplicate
logical path, whitespace variant, or extra field; validate path segments one
by one including terminal/bare `.` and `..`; and use exact V17 audit, seal, and
binary receipt provenance. Its hostile suite must execute the exact compiled
parser and preserve every V16 bypass above as a negative test. It needs a new
seal and another different fresh audit.

No execution, synthesis, playback, or latency authority follows from this
review.
