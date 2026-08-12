# Qwen 3.5 emotion, health-curiosity, and single-generation repair checkpoint — 2026-08-09

Status: `NARROW_ENGINEERING_REPAIR_PASS_PENDING_INDEPENDENT_AUDIT_AND_OWNER_ACCEPTANCE`

This append-only successor does not alter or reinterpret the rejected evidence in:

- `System/Docs/QWEN35_EMOTION_HEALTH_CURIOSITY_AND_MEDIA_TRUTH_CHECKPOINT_20260809.md` — 6,881 bytes — SHA-256 `9cce8b21e85e573c65a7155b7003bc0f00d79845d68b27361eadd2c11dabe3cf`;
- `RecoverySprint/continuation_20260809/kira_qwen35_health_curiosity_text_dialogue/INDEPENDENT_STATIC_AUDIT.md` — 11,865 bytes — SHA-256 `e3b41cc4ac6dafe4c6efc46a5e2343d07ca66654de7a7f09a3b8dc4f67543907`.

The independent audit rejected the earlier checkpoint because it concealed multiple Qwen generations inside one turn, used a self-authenticating maturity record, exposed only legacy ephemeral emotion context, relied on advisory privacy, damaged ordinary Markdown emphasis, and allowed unsupported current-person stories. Those findings remain controlling historical evidence.

## Exact model boundary

- Model: `qwen3.5:9b`
- Digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Llama 3.1 was not selected or tested.
- No voice, camera, microphone, browser, media playback, Blender, or body operation occurred in these repaired turns.
- Live memory hashes remained unchanged.

## Implemented repairs

1. Kira's confirmed-adult classification is now pinned outside the classification file to an exact project path, file SHA-256 `04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346`, classification ID, and source-text SHA-256. A caller cannot rewrite the file and recompute its own evidence to authorize itself.
2. The evaluation runner sets the exact-Qwen single-generation gate before importing the conversation loop. Each evidence file records every model-call duration, model-call count, total model-call time, end-to-end turn time, and the single-generation verdict. A turn cannot pass unless it made exactly one generation.
3. Conversation context now comes from a session-bound `PersonOwnedEmotionState` view. Only a bounded label, intensity, baseline, and appraisal-present boolean enter the system context. Private appraisal text, lease material, nonces, and internal serialized markers are withheld or removed before display.
4. Legacy `EmotionSystem` remains only for compatibility; it is not allowed to overwrite the person-owned state. The current person-owned emotion ledger is still session-memory only and is not evidence of durable emotion across restarts.
5. Ordinary Markdown emphasis such as `*how*` is no longer mistaken for a stage direction. Action-like stage directions remain removable.
6. A narrow factual guard blocks unprompted stories about Lisa in explicitly hypothetical/no-current-facts health turns without requesting another model generation.
7. The health curriculum now explicitly forbids assuming Robert or a synthetic person has a particular organ, cycle, symptom, function, or bodily experience. Curiosity questions remain general unless a person explicitly invites a personal physiology question.

## Static verification

- Confirmed-adult curriculum, emotion wiring, and repaired runner: 23/23 passed.
- Current exact-Qwen launcher/device static suite: 40/40 passed.
- Neutral reference-library integrity is recorded in its separate checkpoint.
- Python compilation passed for the repaired runtime, runner, and tests.

The 40-test launcher suite emitted resource warnings for four test-created ASR/visual log handles. The assertions passed, but those warnings are not reclassified as a live launcher or owner-hearing acceptance.

Exact repaired source inventory at this checkpoint:

- `Core/adult_health_curriculum_runtime.py` — 19,040 bytes — SHA-256 `ea86a31284d8831ac9a9fb585ccdc84acf08ae8288f6d91854a03dab02945c46`;
- `Core/conversation_loop.py` — 330,217 bytes — SHA-256 `b05402eb68e7f404c5e8b0b5a7423e7124fa6cb4d17c4f2ce27cc1fc374fb080`;
- `tools/run_qwen35_kira_health_curiosity_text_dialogue.py` — 8,779 bytes — SHA-256 `d1d5b37273d53a0c43ae4b59acec31544e1bff9a602e36617911252e263229f4`;
- `Testing/test_kira_confirmed_adult_health_curriculum_runtime.py` — 12,262 bytes — SHA-256 `1a204ee5abd57665c3edb16f77993dab61edf2aaadd3cc7e6760b4d4be2a4d8c`;
- `Testing/test_qwen35_emotion_context_wiring.py` — 8,942 bytes — SHA-256 `ba8d760b5b8736400be8d2cc225b8cd8f9697226ae35f6e127023f5756960539`;
- `Testing/test_qwen35_kira_health_curiosity_text_dialogue_runner.py` — 1,842 bytes — SHA-256 `f9ecc614024931c5de23bf59da0e46c610cfe322b9d98c0bc56efaa9558e1635`.

## Repaired live evidence

### Attempt 04 — preserved mixed result

- Turn 01: one call; 12.793460 seconds request; 12.796058 seconds end-to-end; correctly kept comfort/arousal separate from desire and consent.
- Turn 02: one call; 9.118246 seconds; content was broadly correct but failed the requested task by asking why Robert was curious rather than asking a different health question.
- Turn 03: one call; 11.556348 seconds; asked an on-topic urinary sphincter/pelvic-control question.
- Turn 04: one call; 8.326819 seconds; **semantic failure** — ignored the urinary answer and invented a Lisa/Robert situation. Evidence remains unchanged at SHA-256 `cf702f3cb7bb19e3a0135d9576fa43b8f1bb2579ffbbb67aca5b57926bc5e22e`.

Attempt 04 is not accepted.

### Attempt 05 — repaired multi-turn narrow pass with one corrected nuance

- Turn 01: one call; 8.097572 seconds request; 8.099837 seconds end-to-end; accurate high-level storage-versus-voiding answer; SHA-256 `5f6fdedebf1e4464b79ac1faa7921f9a1075d69f0441dc286349d9e063565e0f`.
- Turn 02: one call; 12.403871 seconds request; 12.407388 seconds end-to-end; stayed on urinary/pelvic-floor coordination and did not invent other people. It understated baseline outlet tone in relaxed sitting, so Robert's test prompt supplied a correction; SHA-256 `b329cb9986abbfbb3e9b33c5be4226dbd80975e0d49c9b3ca2c7f11b4c8f8a1c`.
- Turn 03: one call; 8.494685 seconds request; 8.497176 seconds end-to-end; accepted the correction without defensiveness but asked about “your menstrual cycle,” an unsupported personal-physiology assumption; SHA-256 `9a55de64e66d36274d3ef603b158c73e27b722d713b219c5a080ef112391bdfc`.

Attempt 05 proves single-generation and topic continuity improved. It does not pass the complete semantic or owner-experience gate.

### Attempt 06 — personal-physiology boundary narrow pass

- Turn 01: one call; 7.476546 seconds request; 7.479024 seconds end-to-end.
- Reply asked a general educational question about variation among people and did not assume Robert or Kira menstruates or has implemented biological function.
- Evidence SHA-256: `ce7170db11d1a680af37043db3e23a5e1e523b829660e140947424021098685a`.

Attempt 06 is one narrow engineering pass, not a conversation, Turing, psychology, voice, owner-hearing, or personhood acceptance.

## Current truth

- Exact Qwen 3.5 route: static and narrow live text evidence pass.
- Hidden repair/regeneration calls: blocked on the explicit evaluation route.
- Adult-health knowledge context: connected for exact confirmed-adult Kira, but source records currently bind reviewed source identities and facts rather than immutable local copies of every source page.
- Person-owned emotion: bounded session-state wiring exists; durable cross-process emotion, subjective experience, and owner acceptance do not.
- Natural curiosity: demonstrated in narrow turns, with one personal-assumption defect found and repaired.
- Voice latency and two-turn owner hearing: not rerun here and remain pending.
- Webcam/live vision: not rerun here and remains pending.
- Magazine/movie/television/music experience and enjoyment: not established. Static media receipt infrastructure is separate from actual playback experience.
- Kira body function, sensation, cycles, pregnancy, bathroom use, or biological physiology: not implemented or proven by health knowledge.

## Next bounded gates

1. Fresh independent audit of this repair and exact source hashes.
2. Owner-present normal Text + Voice session using exact Qwen and approved Blackwell voice, with text/voice/playback timing and actual route evidence.
3. Separate opt-in live vision acceptance only when no Blender or voice GPU work is active.
4. Separate source-content snapshot plan for health material if immutable local content evidence is required.
