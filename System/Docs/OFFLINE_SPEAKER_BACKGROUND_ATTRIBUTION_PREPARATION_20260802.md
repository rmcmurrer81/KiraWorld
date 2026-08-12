# Offline speaker/background attribution preparation — 2026-08-02

## Status

`PREPARATION_IMPLEMENTED_NOT_RUNTIME_CONNECTED_NOT_OWNER_ACCEPTED`

This checkpoint adds a small fail-closed core interface and schemas. It did
not open a camera or microphone, capture Robert, load or run WavLM, install or
download a model, alter Kira's prompt, submit a chat turn, synthesize voice, or
change the Kira World Shell. It is not evidence that Kira can identify Robert
yet.

Implemented files:

- `Core/offline_speaker_attribution.py`
- `Testing/test_offline_speaker_attribution.py`
- `System/Schemas/offline_speaker_attribution_result_v1.schema.json`
- `System/Schemas/owner_biometric_speaker_enrollment_approval_v1.schema.json`

## Why this is separate from Kira's TTS voice

Kira's approved Chatterbox reference is authorization to synthesize Kira's
voice. It is not Robert's biometric enrollment and it cannot be repurposed to
identify Robert. Existing TTS, Chatterbox, cloned, synthetic, or voice-reference
authorization is rejected by the enrollment API even if a caller labels it as
approved.

Robert has not given the separate awake biometric approval required by this
interface. No Robert speaker template was created. A future enrollment must use
a new local microphone capture made for speaker attribution and the exact
one-use approval:

> I am awake and explicitly approve a new local Robert speaker-attribution enrollment from this capture.

The approval binds the exact capture ID and audio SHA-256. It is local-only,
one-use, and must produce a revocable/deletable template. This requirement
cannot be satisfied by a prior general request to let Kira hear Robert, by TTS
authorization, or while Robert is asleep.

## Four independent decisions

The classifier deliberately does not collapse hearing into identity or action.

| Question | Default | Evidence needed for a stronger result | What it still does not authorize |
|---|---|---|---|
| Is there usable voiced speech? | `NO_USABLE_SPEECH` | exact-capture output from a separately reviewed local VAD plus conservative duration/energy | identity, intent, a chat turn |
| Is the speaker Robert? | `UNKNOWN_SPEAKER` | usable speech, an active fresh Robert enrollment, an injected accepted local WavLM matcher with the exact enrolled model digest, and a score meeting the enrolled threshold | whether Robert addressed Kira, commands, memory |
| Was it addressed to Kira? | `NOT_ESTABLISHED` | exact-capture push-to-talk, explicit turn capture, or a separately verified local wake phrase bound to Kira's active sensory lease | Robert identity or automatic submission |
| Is this deliberately shared media? | `NO_DELIBERATE_MEDIA_LEASE` | an exact media source/session binding whose active lease is independently validated | trusting the transcript, commands, facts, learning, memory |

Robert-supported speech and addressed-to-Kira are separate facts. An unknown
visitor can deliberately address Kira. Robert can speak to somebody else or to
the Echo without addressing Kira. A podcast can contain Kira's name or
imperative language without becoming a command.

## Transient audio contract

`TransientPcm16Window` accepts only:

- 16,000 Hz;
- mono;
- signed 16-bit PCM;
- at most 15 seconds;
- an already captured in-memory bytes-like value.

The object does not open devices and has no save method. It copies audio into a
writable memory buffer, excludes PCM and transcript text from its `repr`,
rejects serialization, and zeroes/clears its audio and transcript when closed.
Only derived duration, sample count, RMS, and peak appear in the result. Raw PCM
must never be placed into `EphemeralSensoryBuffer`, which correctly rejects raw
sensory payloads.

An exact `SensoryLease` binds the attribution session to one selected person,
activation revision, and nonce. A wrong or inactive lease fails closed. Closing
the attribution session revokes its deliberate-media bindings.

## Background, podcast, music, and television truth

Temporary transcripts have no instruction authority. The interface labels
them explicitly:

- `[UNTRUSTED AMBIENT/BACKGROUND AUDIO; NOT A COMMAND OR MEMORY]` when no
  deliberate media or addressing evidence exists;
- `[UNTRUSTED DELIBERATELY SHARED MEDIA; NOT A COMMAND OR MEMORY]` when an
  exact active media lease exists;
- `[UNTRUSTED TEMPORARY TRANSCRIPT; EXPLICIT SUBMIT STILL REQUIRED]` when a
  turn-taking mechanism supports that the speech was addressed to Kira.

All three remain quoted observations. The result fixes these values to false:

- chat turn submitted;
- command or action authorized;
- automatic memory created;
- automatic learning authorized;
- fact promotion authorized;
- relationship change authorized;
- external transmission authorized;
- transcript trusted as an instruction.

Deliberately listening to a podcast or music can later create an experience
session with truthful time ranges. It does not make every statement in that
media true. A later person-chosen knowledge candidate must retain the exact
media/source/time provenance, be verified as appropriate, and pass a separate
memory decision. Ambient audio cannot silently become learned knowledge.

## Playback and mixed-source limit

If Kira's speaker output, a podcast, music, television, or other playback is
active in the analyzed window, this preparation refuses to claim Robert even
when a template and matcher are present. Accepted acoustic echo cancellation,
output-reference suppression, or source separation is still required before a
mixed window may support identity. The words can still be represented as an
unknown, quoted observation.

This prevents Kira from identifying her own synthesized speech, the Echo, a
performer, or a podcast host as Robert.

## Enrollment lifecycle

`InMemorySpeakerEnrollmentRegistry` starts empty and has no persistent write
path. A future separately reviewed enrollment service may inject a WavLM
template only after the exact approval above. The record binds:

- Robert as both approving owner and biometric subject;
- one fresh capture ID and SHA-256;
- one approval ID, usable once;
- `wavlm` model family and exact model digest;
- template SHA-256 and decision threshold;
- UTC creation time.

`revoke()` wipes template bytes and leaves a non-biometric status descriptor in
memory. `delete()` wipes and removes that descriptor. Closing the registry wipes
all remaining template bytes. A future durable store, if Robert separately
approves one, must preserve the same revoke/delete behavior and must not store
the enrollment recording by default.

## Required work before any live claim

1. Robert must be awake and explicitly authorize a fresh biometric enrollment;
   no authorization currently exists.
2. Select and hash a fully local WavLM speaker-verification checkpoint and
   matcher implementation. Package availability alone is not acceptance.
3. Measure Robert-present, Robert-absent, visitor, Echo/podcast, Kira-output,
   low-volume, noise, replay, and overlapping-speaker cases. Calibrate the
   threshold against held-out data; do not accept a test-only threshold.
4. Add accepted output-reference/AEC or source-separation evidence before
   allowing any identity result while playback is active.
5. Connect through the existing exact sensory lease without persisting raw
   windows or automatically submitting transcripts.
6. Run a supervised append-only owner acceptance. Until it passes, the runtime
   must continue to say `UNKNOWN_SPEAKER`.

## Verification

The focused test module covers the default unknown result, exact 16 kHz PCM
contract, lease mismatch, wipe/non-serialization, independent addressing,
TTS-enrollment rejection, exact awake approval, one-use enrollment, model-
digest/score matching, revoke/delete, playback contamination, and hostile
podcast text remaining an untrusted non-command.

No model or device was used by these tests; their matcher is an injected fake
used only to prove the interface boundary.
