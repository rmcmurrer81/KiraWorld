# TemporaryAI Private-Local Voice And Movement Intake v1

## Outcome

TemporaryAI voice discovery and private-local media intake are now separate stages.

- `Core/temp_ai_voice_discovery.py` remains metadata-only. Its no-download rule applies to that discovery stage, not to the entire TemporaryAI creator.
- `Core/temp_ai_local_media_intake.py` may read a user-authorized file already under `Data/library` and extract only explicit short scene ranges.
- The local lane can prepare reviewed voice and movement evidence after the exact character, variant, speaker, and performer are confirmed.
- It does not train or clone a voice, assign a voice or movement profile, activate a TemporaryAI, publish media, or call a voice official.

Public release, commercial use, and official character/performer claims remain separate decisions from private local reference preparation.

## Why Beth, Kathryn, And Other Mixed Clips Need Review

A file title or cast list can identify the production but not a clean speaking turn. A scene can contain:

- two characters performed by one actor;
- another speaker off camera;
- overlapping dialogue;
- music, narration, or effects;
- reaction shots where the visible person is not the speaker;
- stunt doubles, stand-ins, cuts, or occlusion that make movement attribution unclear.

The intake identity record therefore keeps this chain separate:

```text
character -> variant/version -> speaker role -> performer
```

Diarization or acoustic grouping may help find recurring voices. It is never treated as the person's name. Human audiovisual review plus production credit/cast evidence provides the identity decision.

## Bounded Workflow

### 1. Inspect tool readiness

```powershell
py tools\create_temp_ai_local_media_intake.py --readiness-only
```

### 2. Locate short target scenes

Watch the local source and note exact start/end timecodes. Prefer 8–30 second scenes with one clearly visible target and clean solo speech. Reject scenes with overlapping speech, music, narration, or material sound effects for voice work.

Do not submit the entire movie or episode. Backend limits are:

- 1–45 seconds per range;
- at most 12 ranges per request;
- at most 180 seconds total per request.

If the candidate already declares several local leads, first generate the
read-only source-review order:

```powershell
py tools\audit_temp_ai_local_voice_sources.py --candidate-id CANDIDATE_ID
```

Review `clean_range_review_queue.json`. Its rank is only a suggested order for
human inspection; it never selects a source, speaker, performer, or acoustic
group. Every range list deliberately starts empty.

### 3. Create a request

Example only—replace the timecodes after Robert reviews the scene:

```powershell
py tools\create_temp_ai_local_media_intake.py `
  --candidate-id kathryn_merteuil_kathryn_merteuil_20260605_213017 `
  --source Data\library\movies\cruel_intentions\cruel_intentions.mp4 `
  --character "Kathryn Merteuil" `
  --variant "Cruel Intentions 1999 movie" `
  --speaker "Kathryn Merteuil 1999 movie English" `
  --performer "Sarah Michelle Gellar" `
  --evidence voice --evidence movement `
  --range 00:12:03-00:12:24 `
  --authorize-private-local-use `
  --authorized-by real_robert `
  --authorization-note "Private local reference preparation authorized"
```

The source path must resolve under `Data/library`. The request records its exact SHA-256, size, identity target, authorization scope, and bounded ranges.

### 4. Preview the queue

The queue is a bounded one-shot worker. Its default is dry-run and one request; the hard cap is three.

```powershell
py tools\process_temp_ai_local_media_intake_queue.py
```

Explicit extraction:

```powershell
py tools\process_temp_ai_local_media_intake_queue.py --execute --max-requests 1
```

Only the listed ranges are extracted. A voice range becomes mono 24 kHz PCM WAV. A movement range becomes a small 720p review MP4. Both remain unreviewed candidates.

### 5. Complete human review

Each pack contains `human_review.json`. For every approved voice segment, the reviewer must confirm:

- the target character and selected variant;
- the target speaker and credited performer;
- human audiovisual scene review;
- production credit or cast evidence;
- target-only speech;
- no overlap, music, narration, or material effects;
- stable character delivery;
- diarization/acoustic grouping used only as an aid, or explicitly unnecessary for a confirmed single-speaker segment.

For movement evidence, the reviewer must additionally confirm a visible target track, no material occlusion, and no cuts that confuse the motion. Movement is performance evidence, not a character's lived memory.

### 6. Promote only reviewed evidence

```powershell
py tools\promote_temp_ai_local_media_review.py "TemporaryAI\candidates\CANDIDATE\workbench\inputs\private_local_media_intake\packs\PACK_ID"
```

Promotion recomputes the request/source bindings and writes `reviewed_evidence_manifest.json`. Twenty reviewed voice seconds can make the pack suitable for a later model-reference preparation step. This command still performs no training, cloning, voice assignment, or activation.

## Cruel Intentions / Kathryn Status

The local library contains:

```text
Data/library/tv_shows/unaired_pilots/cruel_intentions_nbc_unaired_pilot_2016_sd.mp4
Data/library/movies/cruel_intentions/cruel_intentions.mp4
```

Read-only inspection found a 44:48.06 H.264/AAC pilot at 640x360 and
approximately 29.97 fps, plus a 1:37:25.80 H.264/AAC film at 1920x1040 and
approximately 23.98 fps. Both declared hashes match. FFmpeg is installed
through `imageio-ffmpeg` and can perform bounded extraction.

The 2016 pilot ranks first for adult-present Kathryn review; the 1999 film ranks
second as earlier same-performer character-delivery evidence. This is review
order, not automatic speaker selection. No short Kathryn time ranges have been
approved. A separate authorized pilot pass produced 400 unreviewed candidates
with zero approved; they are not voice evidence until a human uses the
time-aligned video context to confirm Kathryn-only clean dialogue. Before
promotion, Robert or another human reviewer must reject wrong speakers,
overlap, music/effects, and ambiguous off-camera speech.

The target binding for this source should be:

```text
character: Kathryn Merteuil
variant: Cruel Intentions (1999) movie
speaker: Kathryn Merteuil, 1999 English movie performance
performer: Sarah Michelle Gellar
```

The 2016 unaired television pilot remains a separate source pack and must never
be mixed into the 1999 extraction request. Robert has selected a clearly
labeled adult continuation whose present is the 2016-pilot period,
approximately 17 years after the film. A separate zero-range draft exists at:

```text
TemporaryAI/candidates/kathryn_merteuil_kathryn_merteuil_20260605_213017/workbench/inputs/private_local_media_intake/requests/kathryn_merteuil_cruel_intentions_2016_pilot_private_local_v1.json
```

It is the primary adult-present Sarah Michelle Gellar voice/movement source,
but no clips have been extracted. The 1999 film may later supply a separate
same-performer earlier-character supplement. *Cruel Intentions 2* uses Amy
Adams as Kathryn and is backstory evidence only; it is never Sarah Michelle
Gellar voice, likeness, or adult-present body evidence.

The current source evidence, empty human range queue, and unreviewed pilot pack
are:

```text
TemporaryAI/candidates/kathryn_merteuil_kathryn_merteuil_20260605_213017/local_voice_source_evidence_manifest.json
TemporaryAI/candidates/kathryn_merteuil_kathryn_merteuil_20260605_213017/clean_range_review_queue.json
Voice/reference_packs/kathryn_merteuil_kathryn_merteuil_20260605_213017/kathryn_merteuil_kathryn_merteuil_20260605_213017_cruel_intentions_nbc_unaired_pilot_2016_sd_20260717_035509/voice_reference_manifest.json
```

## Installed Tool Status On 2026-07-16

- FFmpeg: ready for exact bounded audio/video extraction.
- PyTorch and torchaudio: installed.
- librosa and soundfile: installed.
- Existing `Core/voice_speaker_separation.py`: available as a review-oriented acoustic grouping aid, not biometric identity.
- pyannote.audio: not installed in the active Python environment.
- OpenCV and MediaPipe: not installed in the active Python environment.

Movement intake therefore produces bounded review clips and human target-track evidence today. Automatic body-pose/motion tracking remains a later backend upgrade and must not be claimed as complete.

## Files

```text
Core/temp_ai_local_media_intake.py
Core/temp_ai_local_voice_source_review.py
tools/create_temp_ai_local_media_intake.py
tools/audit_temp_ai_local_voice_sources.py
tools/process_temp_ai_local_media_intake_queue.py
tools/promote_temp_ai_local_media_review.py
Testing/test_temp_ai_local_media_intake.py
Testing/test_temp_ai_local_voice_source_review.py
```
