# Local Voice Workshop v1 — inactive evidence workflow

Status: implemented as an **inactive, fail-closed evidence workflow**. It is
not a voice generator, capture tool, player, trainer, profile creator, route
switcher, or default activator.

## What this safely adds

The workshop provides one generalized path for a specifically named synthetic
person or approved expert voice:

1. bind an exact `person_id`, `profile_id`, source WAV path, source SHA-256,
   speaker identity, permission record, rights, and provenance;
2. inspect supplied WAVs without playing them;
3. append human reviews of single contiguous 6–10 second candidate clips;
4. deterministically select one clean master without concatenating recordings;
5. create a hash-bound request for an external Chatterbox 0.1.7 preview;
6. inspect and record externally produced preview WAVs without playing them;
7. record Robert's exact approval of that exact preview hash;
8. create—but never apply—a promotion proposal only after separately sealed
   GPU-preferred and same-identity CPU-fallback receipts exist;
9. record a separate exact promotion approval;
10. create—but never apply—a cross-version rollback proposal pointing to two
    exact previously approved promotion records; and
11. verify every immutable record against an append-only hash chain.

All version data stays below:

```text
Voice/workshop/<person_id>/<profile_id>/<version_id>/
```

The implementation also accepts another layout below `Voice/workshop`, but the
three-ID layout above is the owner-facing convention.

## Hard boundaries

`Core/local_voice_workshop.py` and `tools/local_voice_workshop.py` do not:

- record or extract audio;
- create, concatenate, alter, generate, or play a WAV;
- import or load Torch, Chatterbox, CUDA, or another speech model;
- create a person/profile or infer permission;
- train or fine-tune a voice;
- create Lisa or expert profiles;
- alter Kira's accepted reference, sealed receipts, routes, or defaults;
- allow generic voice or SAPI fallback;
- apply a promotion or rollback; or
- update a current/default pointer.

This work does not claim ElevenLabs feature parity. It supplies the missing
local governance and evidence boundary around an existing instant-reference
voice-cloning capability. A separate, supervised synthesis harness must earn
its own acceptance evidence.

## Permission and rights gate

Initialization fails closed unless the permission record contains:

- the exact target `person_id` and `profile_id`;
- a `speaker_id` exactly equal to the target `person_id`;
- exact source path and SHA-256;
- source ID, recording kind, language, origin, recorder/publisher, and chain of
  custody;
- confirmed speaker consent;
- confirmed recording rights and possession/processing rights;
- confirmed voice-conditioning rights;
- confirmation that conditioning is private/local;
- confirmation that named-person private/local synthesis is permitted;
- a named confirming authority, exact confirmation text, and timezone-aware
  timestamp; and
- `revoked: false`.

Public distribution and commercial use are independent optional rights. The
validator records whether both were granted but never infers them from private
local permission.

## Clean-master rule

Candidate creation happens outside the workshop. Each submitted candidate must
bind:

- the exact source path and source SHA-256;
- one finite, ordered source interval;
- `derivation_method: single_contiguous_clip_no_concatenation`;
- a candidate WAV whose duration matches that interval within 50 ms; and
- a human review of source context, target identity, target-only speech,
  overlap, music, effects, background noise, reverb, stability, and transcript.

The technical gate requires mono uncompressed PCM16 at 24 kHz or above, a
non-silent signal, bounded clipping/silence/DC offset, review-range peak/RMS,
and a duration from 6.0 through 10.0 seconds. Selection uses:

```text
min(abs(duration-8), clipping, silence, abs(rms+22), abs(peak+6), sha256)
```

Only the latest review for each candidate hash controls eligibility. A later
rejection removes that candidate from later selections. No long concatenation
is possible in this workflow.

## Preview boundary

A preview request is a receipt for work another bounded harness may perform.
It requires:

- exact selection, profile, reference, and config hashes;
- `chatterbox-tts` version `0.1.7`;
- 1–20 public `SPOKEN` phrases of at most 400 characters;
- playback disabled;
- automatic activation disabled; and
- generic/SAPI fallback disabled.

The result recorder accepts exactly one hash-bound WAV for each requested
phrase, only beneath that version's `preview_audio` folder. It verifies signal
quality and route identity. It does not generate or play those files.

## Promotion and fallback truth

An inactive promotion proposal requires all of the following:

- an accepted clean-master selection;
- an external preview result;
- Robert's exact hash-bound preview approval;
- an exact profile file;
- a separately accepted CUDA receipt for the preferred route;
- a separately accepted CPU receipt whose role is
  `same_identity_automatic_fallback_only`;
- the same exact person, profile, version, profile hash, and reference hash on
  both routes; and
- public-`SPOKEN`-only, offline-cache-only, no-playback, no-generic, and no-SAPI
  evidence on both routes.

If neither sealed route works, the proposed policy is text-only with voice
unavailable. It never substitutes a different voice.

The proposal cannot activate itself. Robert must separately submit the exact
sentence:

```text
I approve this exact inactive promotion proposal.
```

Even that receipt performs no runtime change. A future, separately authorized
runtime integration must verify the approved hashes again before any switch.

## Rollback and versioning

Every version is a new immutable directory with an optional
`parent_version_id`. Files are written exclusively and history is appended as
a SHA-256 chain. Editing a prior record makes verification fail.

A rollback proposal may reference an exact approved promotion from an earlier
version of the same person/profile. It also binds the exact approved current
proposal. The target must differ. Creating or approving the rollback performs
no switch. The exact rollback approval sentence is:

```text
I approve this exact inactive rollback proposal.
```

## Owner CLI

Run from the project root:

```powershell
py tools\local_voice_workshop.py inspect-wav --wav Voice/workshop_inputs/source.wav --purpose source
py tools\local_voice_workshop.py validate-permission --request-json request_permission.json
py tools\local_voice_workshop.py init-version --version-dir Voice/workshop/person/profile/v001 --request-json init.json
py tools\local_voice_workshop.py append-review --version-dir Voice/workshop/person/profile/v001 --request-json review.json
py tools\local_voice_workshop.py select-master --version-dir Voice/workshop/person/profile/v001 --request-json selection.json
py tools\local_voice_workshop.py create-preview-request --version-dir Voice/workshop/person/profile/v001 --request-json preview_request.json
py tools\local_voice_workshop.py record-preview-result --version-dir Voice/workshop/person/profile/v001 --request-json preview_result.json
py tools\local_voice_workshop.py approve --version-dir Voice/workshop/person/profile/v001 --request-json approval.json
py tools\local_voice_workshop.py propose-promotion --version-dir Voice/workshop/person/profile/v001 --request-json promotion.json
py tools\local_voice_workshop.py propose-rollback --version-dir Voice/workshop/person/profile/v002 --request-json rollback.json
py tools\local_voice_workshop.py verify --version-dir Voice/workshop/person/profile/v001
```

Every mutating command writes an immutable record and returns its path and
SHA-256. There are deliberately no `generate`, `play`, `activate`, `apply`, or
`set-default` commands.

## Machine contract

The machine-readable record schema is:

```text
System/Schemas/local_voice_workshop_v1.schema.json
```

The implementation tests use only temporary synthetic PCM fixtures and never
load a model or play audio:

```powershell
py -m unittest Testing.test_local_voice_workshop
```

