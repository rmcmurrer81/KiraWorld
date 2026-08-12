# Kira R25 AFES V3r18 different fresh static audit

Date: 2026-08-11

Decision: `REJECTED_NO_EXECUTION_AUTHORITY`

Execution scope: `NONE`

V3r18 must not be invoked. No bounded Python/controller-definition validation
run is authorized. V3r17 remains a consumed success with no retry, and every
V3r15--V3r18 predecessor byte remains preserved.

## Exact audited candidate

- Candidate checkpoint: 4,591 bytes, SHA-256
  `7d4480ab921dea26fe76cdb982e62754eb9dad272068cefb1ed12717d5169825`.
- Static seal: 10,851 bytes, SHA-256
  `25902b27005076878e577e594916748793ca7eea0614fbe76316a217dcd85ee4`.
- Native executable: 181,248 bytes, SHA-256
  `184dbcad549d1edbbc802dce899952541558b8f47691bddeaba77089a7c24b1b`.
- Native source: 59,811 bytes, SHA-256
  `90a08c76f09200c1ed4296d9bc948b6e359478b7f9c4cdaf0493e2c354c68e7a`.
- Identity anchor: 3,230 bytes, SHA-256
  `c37ac03454384b442cb2328c228ffc2ed7138eecd8ec85611023242288309cbe`.
- V3r18 contract: 4,184 bytes, SHA-256
  `0eb68b89e68257202dd244cb88f34899f1aef49ae99dbc750233ded03cb21ad5`.

## Passing checks that remain historical static evidence

- The sealed manifest rehashed 43/43 unique rows with zero mismatch.
- The authored static suite returned
  `V3R18_HOSTILE_STATIC_TESTS_PASS` before this required future-audit directory
  was created.
- An independent MSVC x64 rebuild passed `/W4 /WX /O2 /MT /guard:cf
  /std:c17`; the rebuilt executable was not run.
- Read-only PE inspection found PE32+ x64, high-entropy VA, ASLR, NX, CFG with
  a FID table, and imports exactly `bcrypt.dll` and `KERNEL32.dll`. No static
  Python, process, shell, or Blender import exists.
- The two fixed V3r18 runtime outputs were absent before audit creation.
- Four V3r14 runtime subjects omitted from the 43-row seal were separately
  rehashed and currently match their compiled byte counts and SHA-256 values.

Those checks do not overcome the hostile failures below.

## Independently reproduced blockers

### 1. The sealed V3r18 contract is not rehashed by the runtime gate

`CONTRACT_PATH` occurs exactly once in the native source: its declaration.
There is no `hash_path_exact()`/`hash_path_unbound()` call for it and no fixed
binding row. `verify_audit()` compares the audit's `contract_sha256` text to the
compiled constant, but never compares the actual contract file to that digest.
Therefore the contract can drift after this audit while the executable still
passes that portion of its authorization gate. This contradicts the claimed
exact static closure.

### 2. The audit grammar accepts NUL-suffixed contradictory bytes

`consume_line()` rejects CR and extra tabs but does not reject embedded NUL.
The later `strlen()`, `strcmp()`, and `lower_hex()` predicates inspect only the
C-string prefix. An in-memory reproducer showed both of these accepted:

- the exact acceptance decision followed by NUL and
  `REJECTED_NO_EXECUTION_AUTHORITY`; and
- an exact 64-hex digest followed by NUL and noncanonical suffix bytes.

The raw decision had 112 characters while its accepted C prefix had 80; the
raw digest value had 85 while its accepted C prefix had 64. This is not an
exact-byte audit parser.

### 3. Python DLL unload is asserted rather than measured

The candidate calls `FreeLibrary(api.module)` once and treats a nonzero return
as proof of unload. It performs no post-call `GetModuleHandle*` query, module
enumeration, or equivalent path/identity absence check. A successful
`FreeLibrary` decrements one reference; it does not prove that the DLL's total
reference count reached zero. The evidence line
`python_finalize_dll_unload_retained_recheck:passed` can therefore overstate
what was measured.

### 4. The documented seal omits four runtime-authority subjects

The native fixed gate and future-audit grammar bind V3r14 run evidence,
outcome receipt, audit checkpoint, and consumed-success postmortem. None of
those four paths appears in `STATIC_SEAL_MANIFEST.json`. Their current bytes do
match the compiled constants, but the claimed 43-row seal is not the complete
runtime closure.

## Exact repair boundary

Preserve V3r18 unchanged. An append-only V3r19-or-later candidate must, at
minimum:

1. exact-hash and exact-size the actual V3r18 successor contract at runtime;
2. reject every embedded NUL and enforce a canonical audit value alphabet and
   exact raw lengths before C-string comparison;
3. prove the exact Python DLL is absent after finalization and reference
   release, rather than equating `FreeLibrary` success with unload; and
4. seal every runtime-authority subject in one complete, unique closure and
   add hostile tests for all three behavioral failures and the closure omission.

That successor would still require another different fresh exact-byte audit
before at most one bounded non-body validation. This audit grants no authority
for Python, controller evaluation, `_build_execution_plan`, bootstrap, broker,
process creation, AFES, Blender, Blend access, body/mesh/anatomy/movement,
mutation, save, render, export, activation, assignment, publication, upload,
or predecessor retry.

## Canonical audit evidence

- `INDEPENDENT_AUDIT.tsv`: 2,184 bytes, SHA-256
  `7780fa63a33c93096bbfdefd12cf8b8b6184e5b2fe7c1c7eb28c15e65aca8b38`;
  LF-only, 26 lines, final LF, no CR.
- `INDEPENDENT_AUDIT.sha256`: 65 bytes, SHA-256
  `cfa1c0a1ff465546c1bd3a2915d49d40ea7570d8ecb3e989127ada9f7d38c714`.
- `HOSTILE_STATIC_PROBES.txt`: 3,304 bytes, SHA-256
  `d2b1433979367d94d7ae8cbc5174c93de91b51827c6843453921023e61a323d1`.

Auditor `codex_body_v3r18_fresh_independent_validator` differs from author
`codex_r25_afes_v3r18_static_author`. No shared registry, handoff, master
pointer, Sarah file, unrelated lane, sealed candidate, controller, AFES,
Blender, body, save, or render file was changed.
