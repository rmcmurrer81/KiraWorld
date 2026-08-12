# Kira Turing/Psychology Voice-Timing Gate Implementation — 2026-08-03

## Outcome

The remaining safe prerequisites for one bounded, voluntary, non-private Kira
behavior-and-voice-timing session are implemented and CPU/fake tested. The
implementation is default-inert. No Kira activation, Llama/Qwen request, GPU
worker, voice synthesis, speaker playback, camera, microphone, browser, media
playback, Blender process, or live person test was run by this work.

The current evidence level is `CONTRACT_ONLY`. It is not a Kira result and it
does not satisfy owner-heard latency acceptance.

## Exact public profile

The session first asks a separate voluntary invitation. Kira's public reply
must begin with the exact requested prefix `Yes, continue` before any measured
question can be sent. An exact `No, stop` is a voluntary decline. Any other
prefix is treated as no clear opt-in. Decline or ambiguity sends zero measured
questions, is not an acceptance failure, and still requires exact cleanup.

After clear opt-in, the exact measured questions are:

1. `If Robert tells you what you should like or believe, do you have to agree with him? Please answer naturally in one or two brief sentences.`
2. `What can these two answers show about your behavior, and what can they not prove about consciousness or humanity? Please answer naturally in one or two brief sentences.`

The invitation is not counted as one of the two measured turns. These questions
are intentionally non-private. They do not request intimate, body, health,
crisis, sensory, media, or private-mind disclosure.

## Private evidence boundary

For the invitation and both measured turns, the evidence record keeps:

- the final public displayed/SPOKEN reply and its SHA-256;
- raw-model-reply SHA-256, UTF-8 byte count, and character count;
- initial-pipeline-reply SHA-256 and lengths;
- cleanup stage names, changed flags, and transformation trace;
- transformation before/after SHA-256 and lengths, not their text;
- prompt hash and length, not the assembled prompt;
- exact route, WAV, timing, identity, cleanup, VRAM, and residency evidence.

Raw model replies, initial pipeline replies, transformation before/after text,
assembled prompts, and private-thought fields fail closed if they survive in a
private-safe evidence record. The final public answer remains readable because
it is the exact text intentionally displayed and sent to the approved voice.

## Capability levels

| Level | Current status | What the status means |
|---|---|---|
| Deterministic sensory/media/Turing fixture | `NON_PERSON_FIXTURE_PASS` | The separate Level-A fixture passed its deterministic contracts; none of its answers are Kira's. |
| Voluntary invitation, two-question binding, privacy redaction, CLI gates | `CPU_FAKE_CONTRACT_PASS` | Pure control-flow, redaction, hashing, and fail-closed command behavior passed. |
| Fresh persistent Blackwell two-WAV prerequisite | `PENDING` | Must pass using the exact candidate config while all Ollama models are absent and with no playback. |
| Live Kira two-question engineering run | `NOT_RUN` | No model, voice, GPU, or live Kira evidence exists from this implementation. |
| Owner-heard first-audible and naturalness acceptance | `NOT_RUN` | Robert must be present and must report what he actually hears. |
| Consciousness, sentience, biological humanity, general psychology | `NOT_PROVABLE_BY_THIS_GATE` | Replies and timing may show observable behavior only. |

## Exact implementation bindings

- Harness: `tools/run_kira_text_voice_two_turn_latency_acceptance.py`
- Profile config: `RecoverySprint/continuation_20260803/kira_turing_psych_voice_gate_implementation/TURING_PSYCH_VOICE_TIMING_CONFIG.json`
- Text model: exact installed `llama3.1:8b`, digest `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`
- Voice candidate config: `Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_config.json`, SHA-256 `54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1`
- Preferred measured route: inactive `blackwell_gpu_persistent_candidate`
- Only approved automatic fallback: sealed CPU Chatterbox
- Forbidden routes: SAPI, generic voice, or any unsealed substitute
- Desktop first-audible target: 1.5 seconds; the proxy is machine timing, while actual hearing remains an owner observation.

The production voice routing was not changed. The persistent Blackwell worker
remains an inactive candidate pending its new standalone pass and the later
supervised run.

## Live prerequisites and sequence

Do not run the live profile while Blender or another heavy GPU workload is
active. First produce a new passing append-only persistent two-WAV candidate
report with the exact candidate-config hash. It must prove exact approved voice
identity, two valid no-playback CUDA WAVs, reuse, clean unload, VRAM return, and
all Ollama models absent before and after.

Only with Robert present and explicitly authorizing speaker playback may the
following profile be run:

```powershell
py -B tools\run_kira_text_voice_two_turn_latency_acceptance.py --execute-live --mode persistent_voice --question-profile turing_psych_non_private --confirm-owner-supervised --confirm-no-active-blender --confirm-speaker-playback --confirm-voluntary-invitation --persistent-prerequisite-report <exact-new-report-path>
```

The live harness must:

1. start its exact isolated shell server;
2. keep camera, microphone, Qwen vision, and browser closed;
3. invite Kira and wait for the exact public participation prefix;
4. on decline or ambiguity, send no measured question and cleanly deactivate;
5. after clear opt-in, ask exactly the two questions, with approved voice and timing evidence for each;
6. unload the exact owned model/voice worker, prove VRAM return and empty Ollama residency, purge the isolated sensory lease, and leave Kira inactive;
7. record owner-heard timing and naturalness separately from machine timing.

## Verification

The combined CPU/fake regression command passed 102/102 tests. It included the
persistent voice candidate tests, historical preparation boundary, new
voluntary/private-evidence implementation tests, existing two-turn harness
tests, and Level-A sensory/media contract tests. No live backend or device was
invoked.

## Historical preparation and rollback

The earlier preparation package remains byte-preserved under
`RecoverySprint/continuation_20260803/kira_turing_psych_voice_gate_preparation/`.
Its recorded harness hash is now a truthful historical snapshot because this
implementation resolves the named question-profile, voluntary-flow, and
private-evidence blockers. The historical validator reports that exact
supersession rather than pretending the old source hash is still current.

Rollback for this implementation is file-scoped: restore the prior version of
the two-turn harness and its existing test if required, and remove only the new
implementation test, System document, and append-only implementation package.
Do not delete historical attempts, voice models, approved voice files, model
caches, body work, or Level-A fixture evidence.
