# Kira long Turing / health / body / voice V9 static checkpoint

Recorded UTC: `2026-08-11T07:13:36.1953121Z`

Status: `STATIC_SUCCESSOR_SEALED_PENDING_DIFFERENT_FRESH_AUDIT`

Live authority: `NONE`

V9 has not run a controller command, model, voice worker, audio, playback,
GPU, person, body, media, or Blender path. Its evidence and generated-audio
output roots remain absent. V8 and the different fresh V8 rejection evidence
remain byte-for-byte unchanged.

## Exact reason for V9

The different fresh V8 audit rejected V8 before any live attempt for two
independent fail-closed defects:

1. V8 validated the first occurrence of duplicate attempt/path flags while
   retained `argparse` consumed the last occurrence. A command validated as
   `attempt_01` could therefore select `attempt_02` at execution.
2. V8 temporarily replaced the process-global V1 loader without binding the
   pre-existing loader to the canonical original and without serialization.
   A pre-poisoned loader could be restored, and overlapping validations could
   expose or restore the wrong reviewed-shell lambda.

The audit decision was `REJECT`. It authorized no V8 retry. V9 binds all six
sealed V8 author subjects and all five V8 rejection-audit subjects exactly.

## Minimal V9 repair

V9 preserves V8 and every earlier candidate. It adds two bounded repairs.

### One canonical argument list

- Every occurrence of `--attempt-label`, `--attempt-path`,
  `--generated-path`, `--child-nonce`, and `--child-run` is counted before
  retained parsing.
- Duplicate singleton flags and every `--flag=value` critical form are
  rejected.
- Missing, empty, flag-shaped, control-character, NUL, and non-string values
  are rejected before retained parsing.
- Parent and child flag domains are separate.
- The parent is canonicalized to exactly one `--attempt-label attempt_01`.
- The child is canonicalized to exact V9 `attempt_01` evidence/generated
  paths and one lowercase 64-hex nonce, with no attempt label.
- Retained `argparse` is run against that exact canonical list and its parsed
  values are compared to the validated values.
- `main()` forwards that same list, only removing the private unattended mode
  marker which retained `argparse` does not define.
- `attempt_02` is rejected in parent and child probes before retained parsing.

### Closed V1 compatibility gate

- The exact imported V1 module object, `sys.modules` binding, package binding,
  source path, source bytes/hash, original loader object, code object,
  defaults, globals, metadata, V8 reviewed-shell loader/configurer, and every
  nested V7--V3 loader object are bound before use.
- A nonblocking lock rejects overlap and reentrancy rather than waiting on or
  sharing global state.
- The compatibility loader is active only in the owner thread for one bounded
  operation. Off-thread use and any captured use after the operation fail.
- Pre-existing hostile loader/module/package/nested-loader bindings fail
  closed.
- Success, operation failure, and in-call mutation restore the exact original
  V1 loader and release the lock; post-restoration identity is verified.
- V9 owns a full V8 validation projection and never calls V8's unsafe scoped
  loader. Only the real V7--V1 compatibility load and the retained V8
  configuration boundary enter the closed gate.

## Retained runtime and truth boundary

The real nested V9 -> V8 projection -> V7 -> V6 -> V5 -> V4 -> V3 ->
V1-compatible loader returns the exact ordered 35 measured turns and retains:

- one voluntary invitation and maximum 36 Qwen generations;
- exact `qwen3.5:9b` digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- Blackwell persistent candidate V2 on CUDA;
- no Llama, CPU fallback, SAPI, or generic voice;
- required WAV generation, physical speaker playback, bounded watchdogs, and
  terminal cleanup/worker-absence truth;
- all V7 stale-anchor, unsupported autobiographical/person-specific claim,
  adult-curriculum, no-pressure, response-is-not-consent, strict-schema,
  finite-number, exact-dictionary, and terminal-release repairs;
- unattended-log-only truth, no physical-supervision claim, no inferred owner
  hearing, and no automatic Turing/psychology acceptance.

## Sealed V9 subjects

| Path | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v9/attempt_01/EXECUTION_PLAN_V9.json` | 5,501 | `64186f2b837b275dde4820d5df83b1080ed46533d39ff7060006c1cbbcbbbd37` |
| `tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v9.py` | 30,125 | `2f4d49fd71c8e633e6a2a4392fe9678a56ebbdbc8e6e7c6ef2ccf8ae0e4fa20a` |
| `Testing/test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v9.py` | 20,282 | `3071f41f17fb7366be6500aeb64c1de72816b37030d02400d0dea11fafd98dac` |
| `AUTHOR_STATIC_TEST_RESULT.json` | 1,048 | `9e0fd25fd3161c6fb32f7047193a52bef504b5c3551f41a40106b24b9e9de580` |
| `STATIC_SEAL_MANIFEST.json` | 1,070 | `30eab562c50d2e1950c687e26518e64657b15c775cbde945f0df41299f7ecaa3` |

## Verification

- V9 controller and V9 test compile/import without bytecode writes: pass.
- Real nested V9 loader returns schemas 9, 8, 7, 6, and 5 plus the exact
  35-turn effective plan, then restores the canonical V1 loader: pass.
- V9-focused hostile suite: `72 passed in 1.94s`.
- V9 + preserved V8 + preserved V7 suite: `158 passed in 2.24s`.
- Tests reproduce both V8 audit findings and challenge duplicate flags,
  equals forms, missing/malformed values, exact parent/child consumption,
  `attempt_02`, pre-poisoning, reentrancy, concurrent overlap, off-thread
  access, captured-gate reuse, exception restoration, and in-call mutation.
- V9 and V8 output roots absent after all static checks: pass.

## Required next step

`DIFFERENT_FRESH_EXACT_BYTE_HOSTILE_STATIC_AUDIT_REQUIRED`

The different auditor must rehash the sealed subjects and all eleven preserved
V8/rejection subjects, independently reproduce both V8 failures, run the real
nested V9 loader, challenge every critical flag before retained parsing,
verify that the validated canonical list is the executed retained list, and
attack loader pre-poisoning, module/package binding, overlap, reentrancy,
off-thread access, captured-gate reuse, mutation, and restoration. It must
also retain all exact Qwen 3.5, turn/invitation, Blackwell CUDA/no-fallback,
playback, cleanup, semantic, unattended, and no-hearing controls.

No live command may be formed or executed from this author checkpoint. Only a
DIFFERENT fresh auditor may issue either `REJECT` or authorize at most one
append-only unattended `attempt_01`.
