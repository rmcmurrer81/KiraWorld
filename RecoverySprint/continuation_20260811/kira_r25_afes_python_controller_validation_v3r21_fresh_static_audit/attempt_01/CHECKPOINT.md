# Kira R25 AFES Python/controller validation V3r21 different fresh audit

Recorded UTC: `2026-08-11T11:25:21.2216976Z`

Decision:
`ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_V3R21_ONLY`

Reviewer: `/root/body_v3r21_contract_test`

Auditor ID: `body_v3r21_fresh_auditor`

Evidence transcription: `/root` transcribed the different reviewer's exact
canonical audit and reported findings because the reviewer's child sandbox
could not write under Kira. The reviewer authored no sealed V3r21 subject.

## Independent result

- all 91 seal rows existed, were unique, and rehashed with zero drift;
- V3r21 author checkpoint rehashed exactly: 5,445 bytes, SHA-256
  `c888e083f5bc35c92e149281c774b78aa31761b18554421bcc35651c40d03bc8`;
- independent strict x64 `/W4 /WX /O2 /MT /guard:cf /std:c17` rebuild passed;
- independent MSVC `/analyze` passed with zero diagnostics and no suppression;
- sealed and rebuilt PE checks passed: x64 PE32+, high-entropy VA, ASLR, NX,
  CFG/CF instrumentation/FID table, imports only `bcrypt.dll` and
  `KERNEL32.dll`;
- V3r20's two C6385 negative controls reproduced exactly: source line 851
  copied 34 bytes from a 32-byte object and line 894 copied 31 bytes from a
  29-byte object;
- V3r21 safe-copy/analyzer/authority/unload/boundary probes passed 37/37;
- canonical audit grammar passed and 11/11 hostile mutations were refused;
- the author's PostSeal suite passed. PreSeal correctly refused because the
  seal already existed during independent review;
- the candidate was not invoked during review.

The runtime truth is precise: the native program binds its runtime fixed,
retained, authority-contract, and audit subjects. The different reviewer and
PostSeal test externally rehashed the complete 91-row seal. The native program
does not claim to rehash all 91 rows itself.

## Exact audit artifacts

| File | Bytes | SHA-256 |
|---|---:|---|
| `INDEPENDENT_AUDIT.tsv` | 6,259 | `235e13793ed4112c9dfaa7173125b31712cb84323d46224932f5fda135f69fd5` |
| `INDEPENDENT_AUDIT.sha256` | 65 | `5b12a7534239ac1bba7174cc4f2c44cf3ad63a3a8ba555fffe0d260988d34773` |
| `AUDIT_DECISION.json` | 2,263 | `e02ad4252df2338b05fdbeec5bf2e7d719b45beb103f5a25d10a81d901380355` |
| `HOSTILE_STATIC_PROBES.txt` | 2,825 | `95e1bfd37cf036ee552f046d3ad49ebd88b6369aad0d1614d69ea007f3c8de4f` |

## Exact one-shot boundary

At most one no-argument invocation of the exact sealed V3r21 executable is
authorized. Any invocation, including any early failure, consumes the
authority. It may perform only the granular V3r15 contract and isolated
Python/controller-definition validation described by the sealed candidate. It
must stop before `_build_execution_plan`, bootstrap, broker/process launch,
AFES, Blender, body mutation, save, render, or export.

This acceptance proves no body, external or internal anatomy, physiology,
movement, activation, owner acceptance, or production feature. No such result
is claimed.
