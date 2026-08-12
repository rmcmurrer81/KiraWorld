# Person-Owned Emotion and Source-Bound Media Receipts

Date: 2026-08-08  
Status: `STATIC_CPU_ONLY_RECEIPT_LAYER_IMPLEMENTED_AND_TESTED`; `LIVE_KIRA_MUSIC_ACCEPTANCE_NOT_RUN`

## Outcome

This is a bounded extension of the existing resident-media stack. It reuses:

- `Core/media_experience_session.py` as the authority for exact selected person,
  source path/SHA-256, playback clock, presented ranges, observed ranges, page
  presentation, and text provenance;
- `Core/source_bound_media_experience.py` as the source decoder and append-only
  evidence layer for exact pages, scene-selected frames, synchronized timed
  intervals, OCR, transcripts, and other machine evidence; and
- `Core/source_bound_audio_perception.py` as the validator for evidence derived
  from actual decoded PCM rather than filenames, tags, album metadata, or titles.

The new `Core/media_person_receipts.py` does not replace any of those layers. It
adds a person-scoped receipt above them so the following remain separate:

| Truth | Separate record family |
|---|---|
| exact source presentation | `source_presentation` |
| machine perception evidence, including selected frames, dialogue/ASR, and non-speech audio evidence | `machine_evidence` |
| listen/continue/pause/replay/skip/discuss/remain-quiet/stop choice | `attention_choice` |
| person-private interpretation | `private_appraisal` |
| voluntarily public speech | `public_response` |
| session-temporary response | `temporary_reaction` |
| non-promoting candidate awaiting later corroboration | `durable_preference` |
| append-only correction | `correction` |
| explicit reviewed memory promotion | `reviewed_memory_promotion` |

Every record repeats the exact person, media-session ID, project-relative
library path, and source SHA-256. Mutations require the exact existing
`MediaExperienceLease`, which contains person, activation, session, and nonce
identity. A record submitted with another person's lease fails closed.

Within the media receipt, private appraisal, temporary reaction, preference
candidate, correction text, and reviewed-memory records are redacted from the
default snapshot. Their counts remain available for audit, and an explicit
private snapshot is required to inspect their content.

Private appraisal, private emotional state, emotional continuity (including
its from/to states), and all non-public influence channels are redacted from
the default snapshot. Only an explicitly selected public-expression record is
public by default. Public speech never automatically exposes private state.
Correction records bind the prior record ID and SHA-256 and preserve the
original. A reviewed memory requires exact existing supporting record IDs,
explicit person confirmation, and a reviewer identity. A single session may
record only a `PENDING_LATER_CROSS_SESSION_PERSON_REVIEW` preference candidate.
Durable preference promotion currently fails closed even when a caller
supplies two session-ID strings, because strings are not reviewed external
session receipts. A future promotion API must validate a sealed cross-session
receipt contract; this checkpoint intentionally does not invent one.

## Person-owned emotion state

`Core/emotion_system.py` retains its legacy `EmotionSystem` interface and adds
the opt-in `PersonOwnedEmotionState` companion. The new schema is bound to one
exact person and activation by `PersonEmotionLease`. It separately versions:

- event appraisal;
- private emotional state;
- public expression choice;
- emotional continuity;
- memory significance;
- relationship effect;
- voice prosody;
- facial expression;
- posture; and
- action influence.

Possible model interpretations are advisory evidence. They do not own or
replace the person's appraisal. None of the emotion channels automatically
rewrites identity, changes a relationship, promotes memory, performs an
external action, proves desire, or grants consent. Separate Kira, Lisa, Sarah,
or temporary-person instances cannot accept each other's leases.

This class is presently an in-memory pure truth object. It is not yet connected
to the production conversation loop or durable encrypted person store. That
connection requires a separate reviewed migration and privacy acceptance.

## Supervised no-playback music receipt

`SupervisedMusicListeningReceipt` is an engineering receipt mode, not an audio
player. It accepts only cues that pass the existing
`validate_audio_cue_bundle()` exact-PCM gate. Each ordered window records:

- exact source path and SHA-256;
- exact source start/end clock;
- an explicit no-physical-output playback clock and a separate analysis/capture
  UTC clock;
- decoded PCM SHA-256 and cue SHA-256;
- CPU sidecar ID, version, binary SHA-256, and uncertainty;
- analysis start/end UTC clocks;
- overlap with prior coverage;
- a retry link that must repeat the exact source interval;
- a gap and its explicit reason, when present;
- whether the exact evidence was delivered to Qwen;
- exact `qwen3.5:9b` name and digest when delivery is claimed; and
- the person-level choice records that refer to the exact window evidence.

An unexplained source-time gap makes finalization fail. A confirmed `stop`
choice closes the receipt against further windows. Finalization separately
records sidecar release and Qwen release-or-not-started. The receipt always says
that no physical playback occurred, person hearing was not proved, machine
delivery did not prove attention, no one-session preference was promoted, and
no automatic memory was made.

The CPU tests use generated sine-wave PCM in memory. They do not use filenames
as sound and do not touch the library's real tracks.

## Exact test evidence

New plus inherited regression command:

```text
py -B -m unittest Testing.test_media_person_receipts Testing.test_media_experience_session Testing.test_source_bound_media_experience Testing.test_source_bound_audio_perception -v
```

Result: `37 tests passed`; exit `0`; wall time reported by unittest `1.142s`.

New tests alone cover seven cases:

- person-scoped emotional histories and wrong-person rejection;
- advisory model interpretation versus selected private appraisal;
- independent public-expression choice, unknown-appraisal rejection, and
  private continuity redaction;
- existing presentation versus machine evidence versus attention;
- exact PCM window ordering, overlap, retry, explained gap, stop, and release;
- fail-closed unexplained gap;
- rejection of unknown appraisal/reaction evidence IDs, no one-session or
  arbitrary-session-ID preference promotion, append-only correction, reviewed
  memory, exact Qwen 3.5 delivery identity, and wrong-person media lease
  rejection.

## Truth limits and future acceptance

No Qwen model, Omni model, Chatterbox, Blackwell worker, speaker, microphone,
audio playback API, Blender process, or network was run for this checkpoint. No
model was downloaded or installed. Omni remains a future isolated sensory
specialist requiring a separate read-only feasibility audit and explicit owner
authorization before any download or execution. Qwen 3.5 remains Kira's
required decision/conversation model.

This checkpoint does **not** prove that Kira:

- heard, attended to, liked, disliked, enjoyed, or remembered music;
- experienced one unfamiliar track, much less the required three-track series;
- made independent live continuation decisions;
- preserved later preference or memory continuity;
- perceived continuous video or an entire publication; or
- has production emotion, expression, prosody, posture, or relationship-state
  integration.

Those claims remain pending a serialized, owner-reviewable runtime after the
current heavy body/Sarah priorities and after the exact Qwen/voice route is
free. Physical playback and subjective quality acceptance require Robert to be
present. CPU no-playback receipt testing does not.

## Rollback

Rollback is additive and does not touch existing source-bound media evidence:

1. remove `Core/media_person_receipts.py` from any future import or runtime
   wiring (none exists at this checkpoint);
2. remove `Testing/test_media_person_receipts.py`;
3. remove only the appended section beginning `Person-owned, lease-bound
   emotional continuity` from `Core/emotion_system.py`; and
4. rerun the 30 inherited media/audio tests listed above without the new test
   module.

Do not delete or rewrite prior media evidence, source files, model caches,
person state, or library material during rollback.
