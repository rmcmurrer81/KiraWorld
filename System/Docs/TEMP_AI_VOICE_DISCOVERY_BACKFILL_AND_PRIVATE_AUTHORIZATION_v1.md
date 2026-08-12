# TemporaryAI voice discovery backfill and private authorization v1

This pass covers every current candidate folder that contains a real
`temporary_ai_profile.json`. The two profile-less smoke artifact directories
are excluded. A missing `voice_discovery_request.json` is created with exclusive
create semantics; an existing request is validated and preserved, never
rewritten.

Run a no-write audit:

```powershell
python tools/backfill_temp_ai_voice_discovery_requests.py
```

Create only missing requests:

```powershell
python tools/backfill_temp_ai_voice_discovery_requests.py --apply
```

The backfill reports blank version/timepoint, fictional variant, performer, and
recording-source blockers. These are review blockers for later exact-voice work;
they do not prevent a metadata request from existing.

## Stage boundary

Voice discovery remains metadata-only. Every request must say that media
download, audio extraction, model download, and candidate activation are false.
The metadata providers themselves use skip-download flags.

That boundary applies only to discovery. It is not a blanket prohibition on the
TemporaryAI system. An already local, user-authorized source may later enter the
separate bounded private-local intake in `Core/temp_ai_local_media_intake.py`.
That lane binds exact source/request/artifact hashes and requires human review of
bounded target-only ranges.

## Robert's private authorization

`Voice/authorizations/robert_private_exact_temp_ai_voice_authorization_20260716.json`
records Robert's 2026-07-16 project instruction. It permits later private exact
voice-model preparation and candidate assignment only after a human confirms a
clean target-only character + variant + speaker clip and the performer identity
when applicable. Mixed or overlapping speakers are rejected.

The record does not approve any particular clip, make a voice public or
official, download media, extract audio, clone/train/prepare a model, assign a
voice, synthesize speech, or activate anyone. Those remain separate logged
future actions.
