# Root multilane continuation checkpoint — attempt 25

Recorded UTC: `2026-08-11T18:44:18.4267061Z`

## Body diagnostic V3r24 independent acceptance, consumed failure, and exact cause

V3r24 received a different-review acceptance for exactly one no-argument
diagnostic `_build_execution_plan` validation. The review passed 273/273 seal
subjects, 10/10 author artifacts, strict build/analyze/PE/import checks, and
227 hostile probes. Exact acceptance evidence is preserved under
`RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_fresh_static_audit/attempt_01`.

After rechecking 273/273 seal rows, 10/10 author rows, exact audit TSV/sidecar,
and absent outputs, root invoked the exact sealed executable once with no
arguments from `C:\Users\robmc\Kira`. Exit code was 1. Authority is consumed:
`DO_NOT_RERUN_V3R24`.

Exact outputs:

| Subject | Bytes | SHA-256 |
|---|---:|---|
| `...v3r24_static_preparation/attempt_01/RUN_EVIDENCE.jsonl` | 1,450 | `310c8d16fdf433de22ecee9dc326c34fd8f1efcbbdc86ada382e7088e42745a7` |
| `...v3r24_static_preparation/attempt_01/EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin` | 1,320 | `2665dd31b2c561a728a3b14449b6d79e821494e9b5792682bc1399fd5edb5b34` |
| `...v3r24_fresh_static_audit/attempt_01/RUN_OUTCOME.json` | 4,426 | `850769324423d08278303a2aaae7bcff0e655bfb103b8b66ee47fe13211ca656` |
| `...v3r24_fresh_static_audit/attempt_01/POST_RUN_CHECKPOINT.md` | 3,498 | `9d42807fdb96f49da9c043ef18a1eae61f2a47b80afe0b849d54cbcdfd89cd9f` |

Telemetry is checkpoint 110, plan attempts/returns 0/0, operation
enters/returns 0/0, and exact exception `ValueError: unmarshallable object`.
Cleanup, unload/absence, fixed recheck, and all 15 contract gates passed. No
controller, plan, bootstrap, broker, process, AFES, Blender, body, save, render,
or export operation occurred.

The cause is now exact. V3r24 uses `marshal.dumps(code, 4)`, while the locked
Python 3.14.4 runtime reports `marshal.version == 5`. Python 3.14 code objects
contain constant `slice` objects. An exact-source read-only scan checked 20
embedded-validator code objects: format 4 failed four (`<module>`,
`_v3_strict`, `_v3_validate_controller`, `_v3_glue_object`) and format 5 passed
all 20. V3r25 is being authored append-only with a complete V3r24 consumed
closure and exact format-5 proof. This is a validator fingerprint defect, not
an anatomical or Blender result, and creates no Avatar Builder method.

## Voice V16 different-review rejection

V16 remains byte-exact (41/41 closure) and independently rebuilds cleanly, but
its different review is `REJECT_STATIC_NO_EXECUTION_AUTHORITY`.
`DO_NOT_RUN_V16`.

The compiled parser accepts a trailing non-JSON byte; accepts a 42-subject
manifest when the extra logical duplicate uses whitespace formatting; and
accepts terminal `.` path segments such as `tools/.` and `tools/...`. It also
retains stale V15 receipt/audit/seal provenance labels. V17 must parse the
whole document with exact count/uniqueness/path segments and V17 provenance,
then receive another different audit. Exact decision/checkpoint SHA-256 values
are `eb8cf761a7821df044a45f81062f7accc7832e2e3b8b993124b4dca63d0fd412`
and `090c1129aa4abb05be79b3d368ff4da72fcf5be2ee5e7681ffa39d706503ee4b`.
No model/GPU/synthesis/audio/playback/latency path ran; no improvement is
claimed.

## Camera and mixed-initiative evaluation boundary

The owner's camera and natural-conversation requirements are now recorded in
`System/Docs/KIRA_MIXED_INITIATIVE_CAMERA_VISION_AND_CONVERSATION_LATENCY_CURRENT_TEST_BOUNDARY_20260811.md`,
7,392 bytes, SHA-256
`2578af627ee69878085fcb795db79f3af867914d15851e9e9d9386f4941030a7`.

Later independently accepted tests may compare paired camera-off/on trials and
measure capture, image processing, vision, text, synthesis, and audio-onset
stages. They must also test mixed initiative, double messages, bounded Kira
follow-ups, optional quiet-interval greetings, barge-in, collision, pause/
cancel/resume, ordering, rate limits, and uncertainty. Camera use is limited
to declared windows; no biometric recognition, background surveillance, raw-
frame retention, or camera-off seeing claim is authorized. Functional boredom
or initiative is testable behavior, not proof of subjective emotion.

The policy is bound into the work-only V11 long-evaluation successor. No
camera, model, microphone, speaker, vision, synthesis, audio, or one-hour run
occurred in this checkpoint.
