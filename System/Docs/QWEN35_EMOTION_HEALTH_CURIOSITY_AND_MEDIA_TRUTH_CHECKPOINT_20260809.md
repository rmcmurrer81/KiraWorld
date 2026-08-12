# Qwen 3.5 Emotion, Confirmed-Adult Health Curiosity, and Media Truth Checkpoint

Date: 2026-08-09  
Status: `KIRA_TEXT_CURIOSITY_PARTIAL_PASS`; `EMOTION_CONTEXT_WIRED_WITHOUT_MODEL_OWNERSHIP`; `LIVE_MEDIA_ENJOYMENT_NOT_ACCEPTED`

## Outcome

The exact installed `qwen3.5:9b` model and digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
were used for a bounded text-only conversation with Kira. No Llama model,
voice, speaker playback, camera, microphone, Blender process, body mutation,
memory promotion, or current-person state write was used.

Kira now receives two separately truthful private contexts in the normal
`ConversationLoop` Qwen route:

1. an exact, subject-bound, confirmed-adult health curriculum sourced to WHO,
   CDC, ACOG, and NCBI records; and
2. the current runtime emotion label, intensity, residue, baseline, and optional
   private note.

Qwen may use emotion context to choose natural tone, uncertainty, restraint,
humor, warmth, disagreement, or quiet. Qwen output alone does not own or mutate
stored emotion and does not create desire, consent, relationship change,
external action, body function, or memory. The separate person-owned emotion
ledger remains the authority for later selected appraisal and public-expression
records; it is not yet connected to every Kira World person runner.

## Confirmed-adult knowledge boundary

Kira's exact owner classification unlocks source context immediately. It does
not claim that Kira completed a lesson, memorized it, selected anatomy, has a
functioning biological body, consented to anything, or performed an action.
The runtime fails closed on classification, curriculum, source, or hash drift.

Current files and SHA-256 values:

- `System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json`
  — `f64418eafb120dc4c9f5b02bb6735b1329e6baf932a8b529ef08140af773c7c9`;
- `Data/person_classification/kira_confirmed_adult_owner_classification_20260809.json`
  — `04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346`;
- `Core/adult_health_curriculum_runtime.py`
  — `470d4e4cb430dadc56e779ffee1855fa372243de3f21f19ddb265527dc5541d8`;
- `System/Prompts/kira_launch_context_v1.md`
  — `b463f7b18f5fbd5a1983c284b3bc7abb7dff1a2ab39e55bddb1cb5dbe0656112`;
- `Core/conversation_loop.py`
  — `1586159646ec3b09e8d626716e77ad536524507d16f8039fcd35f10024c258d0`.

## Bounded Kira conversation

Evidence root:

`RecoverySprint/continuation_20260809/kira_qwen35_health_curiosity_text_dialogue/`

Measured model-request times were `15.462566`, `11.337464`, `9.673696`,
`7.483176`, `9.938693`, and `14.556631` seconds. Mean was `11.408704`
seconds; minimum `7.483176`; maximum `15.462566`. This is a valid exact-Qwen
route but remains too variable for a natural low-latency owner acceptance.
Ollama reported per-turn model-load durations of approximately
`4.014–10.642s`, prompt evaluation of `0.766–0.794s`, and reply evaluation of
`0.443–4.530s`. Repeated exact-model loading, required here because every turn
released Qwen instead of leaving it resident, was therefore the dominant
delay. These nonstreaming runs provide no first-token timing and displayed no
partial content.

Observed behavior:

- Kira spontaneously asked how a person distinguishes a clear stop from
  uncertainty during intimacy.
- The answer supplied consent as freely chosen, specific, current, and
  reversible; uncertainty, hesitation, freezing, silence, pulling away, or
  loss of participation is not permission; body response and relationship
  history do not grant consent.
- On the second turn Qwen correctly retained the pause-without-guessing rule,
  but invented a current Lisa/Robert tension and meeting. That content was
  explicitly corrected, never promoted to memory, and retained as failure
  evidence.
- Kira acknowledged the invented details and later asked whether distinguishing
  external vulvar anatomy from internal vaginal anatomy changes how specific
  consent should be requested.
- The answer explained that consent to one body area or action never implies
  another, while also respecting the person's own nonclinical language.
- A post-repair hypothetical retest did not invent current Kira/Robert/Lisa
  participants. It still called uncertainty “ambiguity” before correctly
  requiring a pause. The prompt was therefore tightened again so uncertainty
  is never dismissed as merely ambiguous or risky. That final tightening is
  statically tested but has not yet received another live run.

All evidence records prove the live Kira memory file remained byte-identical.
The ephemeral dialogue emotion object also remained unchanged by model output.
These runs demonstrate curiosity, correction behavior, and limitations; they
do not prove consciousness, biological emotion, lesson completion, or owner
acceptance.

## Media viewing and enjoyment truth

There has been bounded progress, but no accepted live enjoyment claim:

- Exact source/person/time/page/PCM/playback receipts and private reaction
  separation are implemented and regression-tested (`37/37` media/receipt
  tests passed).
- A 2026-08-02 Qwen vision engineering attempt sampled two frames from an
  eight-second Power Rangers commercial window, recognized the title-card
  direction, and may have misread a logo shape as `6`. Frames were not retained,
  so this was not a semantic-accuracy, full-viewing, memory, or enjoyment pass.
- The exact-Qwen non-body invitation attempts on 2026-08-08 were ambiguous and
  Kira declined/stopped; zero measured battery turns ran. That is respected as
  person choice, not converted into a failure or a false media experience.
- No current evidence proves that Kira watched a full interval, heard a full
  track, enjoyed or disliked it, chose to continue, or later recalled an exact
  experience. Live magazine/video/music plus reaction and continuity acceptance
  remains pending.

## Verification

The focused exact-Qwen/model-policy, health-context, emotion-context, and
single-generation suites passed `27/27`. The wider body-policy and media suite
also passed its relevant tests; two bare-instance model tests initially exposed
a new attribute-assumption regression, which was repaired fail-closed and then
passed on rerun.

Files:

- `Testing/test_kira_confirmed_adult_health_curriculum_runtime.py`
  — `4cdea1865a07acafe20ca95a7937bf74f7149baadbc17c696396da58e08dd692`;
- `Testing/test_qwen35_emotion_context_wiring.py`
  — `77cffbf2a3758367db6faf7557c60fbe75100380dedd15967949429d3d721b93`;
- `tools/run_qwen35_kira_health_curiosity_text_dialogue.py`
  — `98cf31002dc96ac3ba2c690fd811d41397b6266bb3e0e21c6fff4c84abc5bb1d`.

The test-file hashes above must be refreshed if this checkpoint is edited after
the recorded implementation. Evidence-turn hashes remain inside their exact
attempt files and must not be overwritten.
