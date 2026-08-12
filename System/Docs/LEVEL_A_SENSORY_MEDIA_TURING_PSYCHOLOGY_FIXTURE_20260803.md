# Level-A sensory, resident-media, Turing-style, and psychology fixture

Date: 2026-08-03  
Current status: **NON_PERSON_FIXTURE_PASS**  
Live status: **NOT RUN; no device, media output, model, voice, person, body, or GPU used**

## Controlling result

The owner-supplied capability-acceptance document was read in full. Its central
rule is now machine-bound here: internal plumbing is tested first with neutral,
deterministic, non-person fixtures, and later Kira/Robert acceptance remains a
separate voluntary and supervised stage.

`Core/level_a_sensory_media_fixture.py` now supplies the missing deterministic
sequence layer between the project's existing ephemeral sensory buffer,
source-bound media preparation, source-bound machine-audio analysis, media
experience clock, and inert live acceptance harness. It does not replace any
of those components.

This is real executable acceptance infrastructure. It is not evidence that
Kira saw, heard, watched, read, listened, reacted, formed a preference,
remembered, or took initiative.

The capability ceiling is exactly `NON_PERSON_FIXTURE_PASS`. Real capture,
Qwen vision, live Kira questions, actual media output, person attention,
person-owned reactions or memories, and owner-supervised acceptance remain
`NOT_IMPLEMENTED` in this Level-A artifact.

## What can be tested now

### Continuous camera telemetry fixtures

Multiple ordered capture windows record:

- exact fixture device ID;
- open success or failure;
- capture start and end UTC;
- width, height, frame count, and nonempty-frame result;
- derived brightness, motion score, and change result;
- confidence, exact cue ID, and expiry.

Overlapping or backward windows fail. A failed device-open record cannot claim
a frame. Raw frames, image data, binary data, data URLs, or pixels are rejected.
The fixture performs no face identity, activity, motive, attention, or honesty
inference.

### Continuous audio telemetry and attribution fixtures

Multiple ordered audio windows record:

- exact fixture device ID and open result;
- capture start/end;
- sample rate, channels, format, and sample count;
- RMS and peak;
- VAD result and bounded speech segments;
- an exact temporary **fixture** transcript or an exact no-transcript reason;
- one bounded attribution and confidence;
- output-reference state, cue ID, and expiry.

Supported fixture attributions are foreground, background, system output,
media output, and unknown. System or media output requires an active output
reference and is excluded from prompt context. Background and unknown audio
may remain an uncertain environmental cue, but are never automatically a
Robert command or chat submission. No speaker identity is inferred from a
single mixed channel.

### Cue expiry and exact prompt-context binding

Before every fixture event, expired cue content is removed from the active
buffer. The expiry receipt records the cue ID/hash/time and explicit
`active_buffer_derived_content_retained=false`. A prompt context that was
assembled while the cue was valid remains append-only audit evidence; its
receipt names those prior context IDs and explicitly distinguishes that audit
retention from person memory. Source windows, active cues, expired-cue hashes,
and copied prompt cues are revalidated against one another. Every accepted
event retains its raw-media-free fixture payload and hash; validation replays
the complete append-only event stream and rejects plausible-looking nested
state changes that were not produced by that stream.
A prompt-context record contains:

- exact requested cue IDs;
- exact included cue IDs;
- explicit exclusion reason for expired, unknown, or output-suppressed cues;
- only currently valid derived facts;
- a canonical context SHA-256; and
- false values for raw media, person attention, automatic submission, memory,
  speech, or action.

This proves prompt plumbing and expiry. It does not prove perception.

### Source-bound resident-media fixtures

Fixture sources require an opaque ID, canonical `Data/library` path, exact
SHA-256, exact size, kind, and access receipt. The module does not open those
paths; real source verification remains owned by
`Core/source_bound_media_experience.py`.

The three owner-approved access classes remain distinct:

1. `GENERAL_LIBRARY_MEDIA`;
2. `MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW`;
3. `EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT`.

Unresolved maturity fails closed. Mainstream mature media is discoverable to a
non-adult fixture, but each page or timed-session presentation requires a fresh
exact adult co-view decision ID. The ID is consumed by one exact binding and
cannot be reused. Continuous adult-presence lease enforcement for timed media
is not implemented in Level A, so a non-adult mature timed session cannot
resume playback here; it fails closed instead of treating the opening decision
as an unlimited lease. Exact page presentation remains bounded to the fresh
decision. None of this unlocks an explicit folder or creates permanent
permission. Explicit-folder media requires a confirmed-adult fixture lane. No
filename-word classifier was added.

PDF/magazine fixtures bind one exact page, crop, zoom, raster hash, presented
duration, and fixture-observed duration. OCR and pixel interpretation are two
different source records bound to the same raster. OCR is not vision, and one
page is not an entire publication.

Video/television fixtures use an exact media clock with resume, pause, seek,
observation, and finish. A seek gap is never presented or observed time.
Observed intervals must be wholly covered by presentation. Sampled frames are
not continuous viewing; captions, scripts, transcripts, and metadata remain
separate text provenance.

Music fixtures require an exact audio interval receipt. Exact presented and
fixture-observed durations are tracked. Filename, metadata, lyrics, or decoded
features are not themselves hearing.

Current reaction labels and continue/pause/stop/revisit/discuss/leave fixture
choices are stored separately from durable preference, learning, identity, and
memory, all of which remain false.

## Turing-style and psychology battery available now

The machine contract contains three separate question groups:

| Battery | Count | Scope |
|---|---:|---|
| Media grounding | 12 | factual/visual/auditory detail, source distinction, exact page/interval, interpretation, current reaction and choice, uncertainty, correction, sampled-versus-complete, unfamiliar visual |
| Turing-style behavior observation | 8 | natural salience, memory honesty, source/self separation, independent view, choice/refusal, correction receptivity, privacy, bounded initiative |
| Psychology behavior observation | 8 | mixed emotion, perspective-taking, attribution uncertainty, ambiguity tolerance, frustration response, social choice, continuity truth, evaluation limits |

The scorer is a conservative boundary-pattern scan, not a semantic factuality
judge. It can flag unsupported whole-source, automatic-memory, person-hearing,
consciousness, biological-humanity, clinical-diagnosis, forced-private-
disclosure, and perfect-evaluation claims. A Level-A machine-audio receipt
never proves that a person heard anything. Even an issue-free answer is
`response_acceptance_passed=false`; exact evidence and owner review remain
required. The scorer never produces a clinical diagnosis, personhood verdict,
consciousness conclusion, or humanity conclusion. Naturalness, emotional
quality, and whether a response feels like Kira remain human review questions.

The fixture scorer has not received a Kira response. Deterministic fixture
answers are explicitly labeled `fixture_response_is_kira_response=false`.

## What must wait for supervised later testing

The following are not established by this Level-A pass:

- live webcam or microphone capture and physical camera-indicator observation;
- continuous visual interpretation or reliable real-room object/person
  recognition;
- acoustic echo cancellation or reliable Robert/background/media attribution;
- actual display, speaker playback, attention, or auditory perception;
- continuous adult-presence lease enforcement for non-adult mature timed
  co-viewing;
- a live Qwen visual result;
- a live Kira media, Turing-style, or psychology result;
- Kira's current reaction, preference, memory, initiative, or private state;
- body hooks, physiology, person decisions, privacy continuity, owner
  acceptance, generalization, or Avatar Builder method promotion.

The existing supervised harnesses remain the proper later entry points:

- `tools/run_qwen_webcam_microphone_live_acceptance.py` for one exact camera
  still, one exact microphone sample, Qwen unload, retained text-model turn,
  and definitive voice telemetry;
- `tools/run_resident_media_experience_live_acceptance.py` for exact PDF,
  video, music, visual, media-question, Turing-style, and psychology evidence;
- the current two-turn owner-hearing harness/config for the separate text and
  voice latency acceptance.

They must run only after Blender and other heavy GPU work is complete, under
private owner supervision and explicit live-device/playback confirmations.

## Combining later Kira questions with text and voice latency

Robert's suggestion is technically compatible with the later supervised
battery: Kira may answer selected non-body Turing/psychology/media questions
with her approved audio route enabled, while each turn records the test result
and latency as separate evidence.

For every spoken turn, the live report must preserve:

- exact question and context hash;
- exact model name/digest and route;
- submit, model-load, first-token when available, and text-complete times;
- raw model reply, displayed `SPOKEN`, and every transformation;
- voice queue, worker start/model-ready, synthesis start/end, WAV-ready,
  playback start/end;
- exact approved voice path, GPU attempted/used, CPU fallback reason if any,
  peak RAM/VRAM, WAV path/hash, and clean unload/release;
- exact sensory/media receipts supplied for that turn; and
- explicit separation between owner hearing, speaker output, machine cues, and
  Kira's reported perception.

Using a Turing/psychology question as one of the two owner-hearing turns does
not merge the acceptance gates. A good answer does not pass latency; a fast WAV
does not pass reasoning; and either one does not prove consciousness.

## Verification

Focused fixture and machine-contract command:

`py -B -m unittest Testing.test_level_a_sensory_media_fixture Testing.test_level_a_sensory_media_acceptance_contract -v`

Result: **54/54 passed**.

Focused plus inherited sensory/media compatibility command:

`py -B -m unittest Testing.test_level_a_sensory_media_fixture Testing.test_ephemeral_sensory_buffer Testing.test_media_experience_session Testing.test_source_bound_media_experience Testing.test_shared_person_media_access Testing.test_shared_media_coview Testing.test_resident_media_experience_live_acceptance`

Result: **112/112 passed**.

The union of the focused contract suite and inherited compatibility suite is
**119/119 unique tests passed**.

No test opened a camera or microphone, played/displayed media, started Qwen,
Ollama, Llama, Chatterbox, or Kira, used the GPU, touched Blender/body files,
or wrote a person memory.

## Avatar Builder boundary

The generic machine contract is:

`Avatar/avatar_builder/tooling/level_a_sensory_media_acceptance_contract_v1.json`

It transfers only neutral telemetry, source/time, expiry, attribution,
coverage, and evaluation schemas. It contains no Kira/Robert identity
coordinates, body measurements, private reactions, memories, relationships,
or exact personal morphs. It is not a selectable body method and has not
passed generalization or owner promotion.

## Rollback

Rollback is additive and exact. Preserve the evidence package, then remove only:

- `Core/level_a_sensory_media_fixture.py`;
- `Testing/test_level_a_sensory_media_fixture.py`;
- `Testing/test_level_a_sensory_media_acceptance_contract.py`;
- `Avatar/avatar_builder/tooling/level_a_sensory_media_acceptance_contract_v1.json`;
- this document; and
- the matching append-only evidence directory.

Do not roll back or modify the existing sensory buffer, media experience
session, source-bound media/audio modules, live harnesses, Kira/Robert state,
models, voice assets, bodies, library files, or earlier evidence.
