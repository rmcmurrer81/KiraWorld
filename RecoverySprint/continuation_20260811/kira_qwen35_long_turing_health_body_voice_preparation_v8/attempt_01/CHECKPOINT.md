# Kira long Turing / health / body / voice V8 static checkpoint

Recorded UTC: `2026-08-11T06:20:20.3092387Z`

Status: `STATIC_SUCCESSOR_SEALED_PENDING_DIFFERENT_FRESH_AUDIT`

Live authority: `NONE`

V8 has not run a controller command, model, voice worker, audio, playback,
GPU, person, body, media, or Blender path.  Its output roots remain absent.

## Exact reason for V8

V7 correctly repaired all fifteen reproduced V6 validation findings, but its
fresh audit rejected the complete chain because frozen V1 binds
`tools/kira_world_shell_server.py` to the earlier SHA-256
`69594a9917b55dbca4992c12c357f79d81c0ccb7028ca8f2cc46e4f18789ecdd`.
The bounded fast-end repair intentionally changed that file to 606,696 bytes,
SHA-256
`72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4`.
V7's unfiltered chain therefore passed 151 and failed four static tests at the
same retained V1 project-binding gate.  No V7 live attempt occurred.

## Minimal compatibility repair

V8 preserves the V1 plan byte-for-byte and installs a scoped validator only
while loading the real nested V7--V1 contract.  It requires:

- the exact frozen V1 plan and its exact legacy shell-binding row;
- the exact current shell bytes/hash;
- the exact fast-end static test and checkpoint;
- exactly one substitution, for `tools/kira_world_shell_server.py` only;
- exact unchanged hashes for every one of the other nine V1 project bindings;
- restoration of the original V1 loader after each nested validation;
- the exact V7 package and V7 rejection evidence;
- all V7 semantic, terminal, strict-JSON, exact-dictionary, and finite-number
  repairs;
- exact Qwen 3.5 digest, 35 measured turns plus voluntary invitation/cap 36,
  Blackwell-v2 CUDA/no fallback, WAV/playback/cleanup, unattended-log-only,
  and no owner-hearing inference.

V8 does not alter a V1/V2/V3/V4/V5/V6/V7 historical byte and does not pretend
the new shell has the old hash.

## Sealed V8 subjects

| Path | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v8/attempt_01/EXECUTION_PLAN_V8.json` | 5,291 | `9e472f839a4ecae2d538db67244db23fb6d9cc4101b29d2d3b87f3e54d32d40e` |
| `tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8.py` | 21,310 | `9de8a194d325d922d81a57b8ad86d7bd83134493eeeabd6f3682d7ab041b5652` |
| `Testing/test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8.py` | 5,496 | `0279216471a304966c3549bab42d005a767493e180c12c95c3ac06c995d01c00` |
| `AUTHOR_STATIC_TEST_RESULT.json` | 910 | `49e8d50e0a184c0f390e7ec596eb4abf3697a4ce73dd0a5645d44f0f7191fea3` |
| `STATIC_SEAL_MANIFEST.json` | 1,068 | `6935090d0247d92833110084ab57775db34d60680b98ff0733a8fed5eb83daf2` |

## Verification

- V8 controller and test compile: pass.
- Actual V8 nested loader returns V8, V7, V6, V5 and the exact effective
  35-turn contract while restoring the original V1 loader afterward.
- Focused V8 plus preserved V7: `86 passed in 0.90s`.
- Tests reject wrong shell/evidence bytes or hashes, policy drift, any of the
  other nine V1 binding drifts, duplicate/non-finite JSON, wrong attempt paths,
  and pre-existing output roots.
- Scoped `git diff --check`: pass.

## Required next step

`DIFFERENT_FRESH_EXACT_BYTE_HOSTILE_STATIC_AUDIT_REQUIRED`

The different auditor must independently inspect the scoped loader replacement
and restoration, challenge a second substitution and loader/TOCTOU leakage,
rehash every V7/rejection and fast-end subject, execute the real nested static
loader, retain every V7 negative/positive control, and issue either an explicit
rejection or at most one owner-authorized unattended attempt.  No live command
may be formed or executed from this author checkpoint.
