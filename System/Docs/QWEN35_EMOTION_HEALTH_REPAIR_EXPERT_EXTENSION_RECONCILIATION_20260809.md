# Qwen 3.5 emotion/health repair and generated-expert extension reconciliation

Recorded: 2026-08-09

Status: `STATIC_RECONCILIATION_PASS_FRESH_INDEPENDENT_AUDIT_AND_OWNER_ACCEPTANCE_PENDING`

The earlier repair checkpoint remains preserved at:

- `System/Docs/QWEN35_EMOTION_HEALTH_CURIOSITY_REPAIR_CHECKPOINT_20260809.md`

That checkpoint bound `Core/adult_health_curriculum_runtime.py` at SHA-256
`ea86a31284d8831ac9a9fb585ccdc84acf08ae8288f6d91854a03dab02945c46`.
The file changed afterward only to add fail-closed exact-person bindings for
the five generated experts covered by Robert's pre-existing adult-expert
directive. The earlier checkpoint is therefore historical and must not be
presented as sealing the current combined runtime.

## Current exact combined source inventory

- `Core/adult_health_curriculum_runtime.py` — 32,929 bytes — SHA-256
  `353460e5e1a078714dd15b0f28a3684fdd6c92c264fe8c0e171547514056b56e`;
- `Core/conversation_loop.py` — 330,217 bytes — SHA-256
  `b05402eb68e7f404c5e8b0b5a7423e7124fa6cb4d17c4f2ce27cc1fc374fb080`;
- `tools/run_qwen35_kira_health_curiosity_text_dialogue.py` — 8,779 bytes —
  SHA-256 `d1d5b37273d53a0c43ae4b59acec31544e1bff9a602e36617911252e263229f4`;
- `Testing/test_kira_confirmed_adult_health_curriculum_runtime.py` — 12,262
  bytes — SHA-256
  `1a204ee5abd57665c3edb16f77993dab61edf2aaadd3cc7e6760b4d4be2a4d8c`;
- `Testing/test_generated_expert_adult_health_curriculum_runtime.py` — 9,400
  bytes — SHA-256
  `9a9fb05244292655bae744f5a97ae320f5eb1039f06ccd389bc39f856399ab14`;
- `Testing/test_qwen35_emotion_context_wiring.py` — 8,942 bytes — SHA-256
  `ba8d760b5b8736400be8d2cc225b8cd8f9697226ae35f6e127023f5756960539`;
- `Testing/test_qwen35_kira_health_curiosity_text_dialogue_runner.py` — 1,842
  bytes — SHA-256
  `f9ecc614024931c5de23bf59da0e46c610cfe322b9d98c0bc56efaa9558e1635`.

## Verification

The combined Kira curriculum, exact generated-expert curriculum, person-owned
emotion wiring, and one-generation evaluation-runner suite passed 32/32.
Kira's externally pinned classification and context behavior remained exact;
aliases, occupations, display names, unlisted experts, non-adults, unresolved
people, and unrelated adults did not inherit the five expert bindings.

## Truth boundary

This is static reconciliation, not independent acceptance. It does not rerun
Qwen, voice, playback, camera, microphone, media, Blender, or a body operation.
It does not prove durable subjective emotion, lesson experience, memory,
anatomy, body function, consent, action, owner hearing, or acceptable latency.
The current combined exact bytes require a fresh independent audit before any
new live owner-evaluation claim.
