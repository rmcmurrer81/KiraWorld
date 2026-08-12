# Kira R25 AFES V3r16 different fresh exact-byte hostile static audit

Date: 2026-08-11

Decision: `REJECT`

Execution authority: `NONE`

`ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY` is **not** issued.

## Outcome first

The V3r16 candidate is rejected without execution. The exact bytes presented
by the author checkpoint did not survive to this audit. Six sealed subjects
differ: native source, identity anchor, object, executable, build/static test
results, and the static seal manifest itself. The source and object also
changed length. Eight checkpoint byte/hash assertions fail.

The later inner manifest is internally consistent with the newer files, and
the authored static suite still passes `114/114`. Neither fact repairs the
earlier outer checkpoint seal or authorizes this different auditor to infer a
reseal. Exact-byte continuity is a prerequisite, not a test-suite preference.

A second independent blocker is the audit binding. The candidate hardcodes:

`RecoverySprint/continuation_20260810/kira_r25_afes_v3r16_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv`

This audit was explicitly required under:

`RecoverySprint/continuation_20260811/kira_r25_afes_contract_lock_diagnostic_v3r16_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv`

Evidence at the required path cannot satisfy the exact PE's audit gate. No
acceptance TSV or digest was created at the candidate's hardcoded path.

## Static positives that do not cure rejection

Independent source and PE inspection confirms that the current source has a
reservation-first order with two `CREATE_NEW`, write-through fixed outputs;
one read-only target handle with the broad diagnostic share mask; granular
first-failure gates; two same-handle snapshots; repeated path, file-ID, and
size checks; sealed target digest equality; flushed pending and terminal
evidence; two packed receipt records; exact readback and trailing-byte checks;
and fail-closed partial-write, reparse, path, share, and error handling.

The current source contains no Python/controller/AFES/Blender/body/process
stage. Read-only PE inspection found x64 PE32+, CFG, high-entropy VA, ASLR,
NX, no delay imports, only `bcrypt.dll` and `KERNEL32.dll` dependencies, and
no Python, Blender, `CreateProcess`, or `ShellExecute` name.

The current source independently compiles under strict MSVC settings into the
audit evidence directory. The compiled copy was not run. These results apply
only to current bytes and cannot promote them as the earlier sealed candidate.

## Evidence

- `HASH_VERIFICATION.md`: exact outer-seal/current comparison.
- `INDEPENDENT_HOSTILE_STATIC_TEST.ps1`: ordinary read-only/static hostile
  test source.
- `TEST_RESULTS.md`: authored and independent test counts.
- `COMPILE_AND_PE_RESULTS.md`: isolated compile and read-only PE findings.
- `INDEPENDENT_AUDIT.tsv` and `.sha256`: explicit rejection record at the
  required evidence path.
- `REVIEW_RESULT.json`: structured rejection.

## Safety boundary

The candidate executable was not run. The audit rebuild was not run. The
V3r15 target was not opened by either executable. No runtime evidence or
outcome receipt was created. No Python, controller, AFES, Blender, Blend,
body, mesh, anatomy, pose, movement, model, person, device, production pointer,
or production route was used or changed. V3r15 remains
`CONSUMED_FAILURE_NO_RETRY`; V3r16 receives no retry or run authority.

## Required next step

Preserve V3r16 and this rejection evidence unchanged. If work continues, use
an append-only successor with one coherent outer checkpoint/manifest closure,
an audit path matching the actual different-auditor evidence location, a new
exact-byte seal, and another different fresh static audit. Do not execute this
candidate.
