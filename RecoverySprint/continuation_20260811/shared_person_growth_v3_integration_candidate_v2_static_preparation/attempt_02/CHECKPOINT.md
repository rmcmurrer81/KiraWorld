# Shared Growth V3 integration V2 — append-only static seal

Completed: `2026-08-11T07:59:17.028Z`

Status: `SEALED_DISCONNECTED_STATIC_SUCCESSOR_PENDING_DIFFERENT_FRESH_AUDIT`

This is the completed append-only seal for the unfinished V2 material recovered
from the prior task. `attempt_01` remains preserved as pre-seal history; its
author result predates the final source/test bytes and is not the controlling
evidence. This `attempt_02` binds the current exact bytes.

## Outcome

The accepted isolated Shared Growth V3 core remains unchanged at
`ACCEPT_STATIC_ONLY`. The rejected V1 integration candidate and its different
fresh audit remain exact. V2 is only a disconnected static successor and gives
no capability to Kira, Lisa, any other person, or the Temporary Creator.

V2 narrows the two V1 rejection findings:

- the public adapter retains no controller, controller identity, secret,
  authority identity, or authority callback; a callback is supplied separately
  for each static protocol operation and is never described as an OS trust root;
- exact route/inventory sources are stable-double-read, rehashed, and rebound at
  issue, stage, final commit, and final readback, including pre/post-callback
  snapshots and rollback/removal after detected drift.

The production opener remains unconditionally fail-closed. The only output is
an explicit caller-provided non-production staging file created exclusively and
read back exactly. No production pointer or current person profile is changed.

## Sealed subjects

| Path | Bytes | SHA-256 |
|---|---:|---|
| `Core/shared_person_growth_v3_integration_candidate_v2.py` | 50,230 | `1b29379c36e13295f2119e67cb88574958fb2115828c75ce2d5427a08e6bcc42` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v2.py` | 33,997 | `17a211c67061427e2718ad579bd0f743578815f1d4426b9d568a1131b7c17caf` |
| `attempt_01/STATIC_CONTRACT.json` | 2,086 | `3b7b40b1d12fff1a7137be121ac1dfe6525f06599b8669db50454e1cd0df9f36` |
| `attempt_02/AUTHOR_STATIC_TEST_RESULT.json` | 3,407 | `9f53499124a5e8916042ffd207b3663c89b3d7502d9b2938d34def2469b633e8` |
| `attempt_02/SEALED_MANIFEST.json` | 4,146 | `0ec609dc63b6d440f35c9ec3969b15972c5032bd71c7b89e0595f57b54df6820` |

The manifest rehashed 14 candidate, evidence, rejected-predecessor, accepted
V3-core, and current-runtime rows with zero mismatch.

## Verification

- In-memory strict compile: 2/2.
- Focused V2 hostile suite: 40 passed, 3 subtests passed.
- Preserved Shared Growth V1/V2/V3 and integration-V1 regression: 70 passed,
  13 subtests passed.
- Current Qwen owner-runnable and remaining-route compatibility: 20 passed,
  173 subtests passed.
- Combined unique result: 130 passed, 189 subtests passed.

The focused cases include same-process V1 authority-introspection regression,
missing/substitute callback refusal, production-opener refusal, source drift at
every transaction phase, callback-time mutation, exact rollback/removal,
one-use envelope replay, fresh-request challenge replay, Kira public-only
staging, and Temporary Creator unresolved/doll-safe/default-off projection.

## Exact identity distinctions

The preserved inventory retains 24 unique people and 36 exact routes, including
the denied misspelled Sarah state alias. Synthetic Robert remains distinct from
Biological Robert, and no Biological Robert growth profile exists. Maturity is
not inferred from names or folders. Confirmed-adult eligibility never implies
curriculum completion, anatomy, sensation, desire, consent, action, memory, or
lived experience.

## Scope truth

No Kira, Lisa, resident, expert, generated person, Temporary Creator, model,
memory, emotion, initiative, body, media, voice, audio, GPU, Blender, or Sarah
route ran or changed. No rollout or promotion is accepted. No Python callback
is claimed to be a protected external authority.

## Required next step

A different fresh exact-byte hostile auditor must validate all 14 sealed rows,
repeat the V1 introspection and route-source TOCTOU attacks, probe callback and
response substitution/replay, and verify production/person routes remain
unchanged. It may issue only a static integration-candidate verdict. Even a
static acceptance cannot promote V2 or give upgrades to anyone.
