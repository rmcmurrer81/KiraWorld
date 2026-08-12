# Kira R25 AFES V3r17 different fresh static audit

Date: 2026-08-11

Decision: `ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY`

Execution scope: at most one exact no-argument invocation from
`C:\Users\robmc\Kira`; any launch consumes the authority, regardless of
result.  No retry.

## Outcome

No deterministic static blocker was found.  V3r17 repairs the exact V3r16
outer-seal and audit-path defects without adding Python, controller, execution
contract, broker, process, AFES, Blender, body, save, render, or export scope.

The accepted command, not yet run by this audit, is:

```powershell
.\tools\native\kira_r25_afes_contract_lock_diagnostic_v3r17.exe
```

No arguments, wrapper script, pipeline, or redirection may be added.

## Independent verification

- V3r17 hostile static suite: `179/179` passed.
- Manifest rehash: 28/28 exact, zero mismatches (eight V3r17 subjects plus 20
  preserved V3r16/current-rejection subjects).
- Candidate checkpoint: 5,547 bytes, SHA-256
  `de11ae34d0a2c5b8a349da86e652c68694816a61789fe20e98233fe426694df9`.
- Static seal manifest: 9,009 bytes, SHA-256
  `17c13017c4de4af447e77abecca02d851e999cd1b098c78e32ea07b4768fbfc2`.
- Independent MSVC x64 rebuild passed `/W4 /WX /O2 /MT /guard:cf
  /std:c17`; the rebuilt PE was not run.
- Read-only PE inspection: PE32+ x64, CFG, high-entropy VA, ASLR, NX, no delay
  imports, imported DLLs exactly `bcrypt.dll` and `KERNEL32.dll`.
- Source inspection confirms no application call to Python, controller,
  process creation, AFES, or Blender. Generic CRT loader helpers remain in the
  static runtime imports and grant no application loader stage.
- Runtime outputs were absent when authority was issued.

## Canonical audit evidence

- `INDEPENDENT_AUDIT.tsv`: 1,119 bytes, SHA-256
  `076f5be60a618c97b1981bbcf4bd0653c9cdc153929aacce97d8e7b66fa99ec5`;
  LF-only, 14 lines, final LF, no CR.
- `INDEPENDENT_AUDIT.sha256`: 65 bytes, SHA-256
  `99f33b739b57c716021c632bb6e95004d823cce17b9fb881c9267ce5734de531`;
  exact audit digest plus LF.
- Auditor `codex_root_r25_afes_v3r17_fresh_auditor` differs from author
  `codex_r25_afes_v3r17_static_author_agent`.

## Absolute boundary

This acceptance authorizes only fixed-subject verification, reservation of the
two fixed diagnostic outputs, two read-only same-handle snapshots of the exact
V3r15 contract, durable terminal/readback evidence, and stop.  It is not a body
result and grants no authority for Python, controller evaluation, the plan
builder, AFES, Blender, mesh, anatomy, movement, save, render, production, or a
second invocation.
