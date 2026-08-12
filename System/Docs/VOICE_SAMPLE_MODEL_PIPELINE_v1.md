# Voice Sample And Local Model Pipeline v1

> **Current TemporaryAI authority notice (2026-07-16):** Start online discovery with the metadata-only lane in `TEMP_AI_AUTOMATIC_VOICE_DISCOVERY_v1.md`. Its no-download rule is stage-scoped, not a blanket ban. For a user-authorized file already under `Data/library`, use the explicit short-range and human-reviewed lane in `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md`. Private-local reference preparation does not by itself grant public release, an official-voice claim, model training, voice assignment, or activation.

## Purpose

This pipeline collects voice evidence, separates possible speech, requires Robert to identify clean target-only clips, and prepares one reviewed reference WAV for a future local voice model.

It does not automatically decide who is speaking. Episodes and online compilations can contain narrators, music, sound effects, and several characters.

## Start Here

Open `Start_Voice_Reference_Control_Center.bat`, or open Kira Main Control Center and choose **Voice Reference Control Center** under Media / OCR.

## Local Episode Workflow

1. Enter the target name, stable id, and exact version/dub/form.
2. Choose a local episode or recording.
3. Add a matching PDF/text script when available. Script cue counts help review but do not provide timestamps.
4. Select the truthful authorization status.
5. Click **Build Local Candidate Clip Pack**.
6. Click **Review Last Pack** and listen to every useful clip.
7. Approve only clean target-only speech. Reject another speaker, mixed speakers, or noisy/music-heavy clips.
8. Click **Save Review**.

## Online Video Workflow

Paste the URL in the online field.

- **Save Existing Online Style Reference** links previously collected metadata, captions, broad speech metrics, movement notes, and thumbnail evidence. It does not download audio.
- **Download Online Candidate Audio** downloads the source audio and creates unreviewed speech candidates. This still does not identify or approve the target speaker.

Online and local sources use the same review panel after candidate extraction.

## Model Preparation

A pack becomes eligible only when:

- its authorization status is `owned`, `licensed`, `authorized`, or `self_recorded`;
- at least 20 seconds of target-only speech is approved;
- rejected speakers/music are excluded.

Then run:

```powershell
py tools\prepare_voice_model_reference.py "Voice\reference_packs\TARGET\PACK_ID"
```

This creates `model_input/approved_reference.wav` and `model_input/voice_model_request.json` inside the pack. It never uses the raw episode or mixed online source directly.

## Current Model Backend Status

Collection, FFmpeg extraction, script inventory, online metadata/captions, clip review, and model-reference preparation are implemented.

The actual neural voice backend is not installed yet. The current machine has Python 3.14 only; common CUDA voice-cloning backends generally require a separate Python 3.10 or 3.11 environment plus PyTorch, audio dependencies, and model weights. Until that environment is deliberately installed and tested, live output continues to use the existing Windows voice fallback.

2026-07-06 update: this older backend warning is now partly historical. `python tools\check_voice_pipeline.py` reports the RTX 5060 Ti, PyTorch CUDA, FFmpeg, yt-dlp, Chatterbox TTS, and soundfile are available. The backend can be used only after the source pack has clean reviewed target-only clips and an approved reference WAV. Do not skip speaker review or treat mixed YouTube/episode audio as model-ready.

## Completed Tests On 2026-06-19

### Ladybug

- Source: local `Miraculous Ladybug` episode 1x05, *Mr. Pigeon*.
- Matching script: attached and parsed, 33 pages with 85 Ladybug name mentions.
- Candidate speech clips: 223.
- Pack: `Voice/reference_packs/ladybug/ladybug_miraculous_ladybug_s01e05_mr_pigeon_20260619_184235`.
- State: candidate audio collected; target-speaker review pending.

### Kara Zor-El

- Source: official DC YouTube reference supplied by Robert: `https://www.youtube.com/watch?v=nHKVwDaBfss`.
- Saved evidence: metadata, English captions, thumbnail, and broad non-quoted speech metrics.
- Online candidate speech clips: 300.
- Style pack: `Voice/reference_packs/kara_zor_el/kara_zor_el_online_style_20260619_190551`.
- Audio pack: `Voice/reference_packs/kara_zor_el/kara_zor_el_online_source_20260619_191032`.
- State: candidate audio collected; target-speaker review pending.

## Important Quality Rule

More audio is not automatically better. Twenty to sixty seconds of clean, consistent target-only speech is more valuable than hundreds of mixed clips. Keep separate profiles for different actors, dubs, ages, forms, or interpretations.

## 2026-06-20 Mixed-Speaker Separation

Candidate packs can now be divided into acoustic review groups before Robert listens to every clip individually.

From the Voice Reference Control Center, choose **Separate Speakers In Last Pack**, then **Open Last Speaker Groups**, or run:

```powershell
py tools\separate_voice_speakers.py "Voice\reference_packs\TARGET\PACK_ID"
```

Outputs are written under:

```text
PACK_ID/speaker_separation/speakers/female_1/
PACK_ID/speaker_separation/speakers/male_1/
PACK_ID/speaker_separation/speakers/speaker_1/
PACK_ID/speaker_separation/speaker_separation_manifest.json
PACK_ID/speaker_separation/speaker_identity_hints.json
```

The automatic labels are acoustic review buckets, not verified identity or gender. A rough `female_1` label may be wrong. If a script, introduction, or Robert's listening review identifies someone, `speaker_identity_hints.json` can map clip ids or source time ranges to a reviewed name such as `clark_kent`. Running separation again then creates the named folder. This does not perform online biometric voice identification.

Real first-pass results:

```text
Ladybug local episode: 223 clips grouped into four review buckets.
Kara online source:    300 clips grouped into four review buckets.
```

Both remain unapproved for model use. Speaker grouping reduces review work; it does not replace target-speaker approval.

## Expressive Immediate Voice

The current Windows SAPI fallback now applies modest rate and volume changes for warm, excited, gentle, concerned, and neutral replies. This can make the audible approximation less flat. It is still not Ladybug's or Kara's own voice and does not replace the future reviewed neural voice backend.

## 2026-06-20 Speaker Audition Reels

The Voice Reference Control Center can now select an existing reference pack, build one short audition WAV per acoustic speaker group, and open the resulting folder. Use:

1. **Select Existing Reference Pack**
2. **Build Group Audition Reels**
3. **Open Last Audition Reels**
4. Listen to each WAV and identify only voices Robert can confidently recognize.
5. Add reviewed clip or time-range identities to `speaker_identity_hints.json`, rerun separation, and approve only clean target-only speech in the review panel.

Real audition reels are present under both packs:

```text
Voice/reference_packs/ladybug/ladybug_miraculous_ladybug_s01e05_mr_pigeon_20260619_184235/speaker_separation/review_reels
Voice/reference_packs/kara_zor_el/kara_zor_el_online_source_20260619_191032/speaker_separation/review_reels
```

These reels are a faster listening aid. Their `female_1`, `female_2`, `female_3`, and `male_1` labels remain unverified acoustic buckets and are not identity findings. No neural character voice is ready until target-speaker clips are reviewed and the separate compatible model environment is installed.

## 2026-07-16 TemporaryAI Discovery Front Door

For a new TemporaryAI, begin with metadata-only discovery before local/online audio intake:

```powershell
py tools\discover_temporary_ai_voice.py --candidate-id <candidate_id> --metadata-search
```

See `System/Docs/TEMP_AI_AUTOMATIC_VOICE_DISCOVERY_v1.md`.

Discovery separates character, variant, speaker, and performer; indexes exact URLs and model-card/license metadata; and applies living-performer consent gates. It downloads no media/model payload and cannot make a pack model-ready. Only after source identity, rights, consent, and intended use are reviewed should an explicitly authorized source enter the extraction/review workflow above.

An open code/weights license does not establish the voice dataset's rights or a named performer's consent. A generated result must not be labeled official or authentic without direct authority.
