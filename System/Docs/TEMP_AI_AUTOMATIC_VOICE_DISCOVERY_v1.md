# TemporaryAI Automatic Voice Discovery v1

> **Stage-boundary update (2026-07-16):** This document's no-download rule applies to automatic online metadata discovery. It is not a blanket prohibition on the TemporaryAI creator. A user-authorized file already under `Data/library` can enter the separate short-range, human-reviewed private-local lane in `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md`. That lane still does not itself train/clone, assign, activate, publish, or grant an official-voice claim.

## Purpose

This is the provenance and discovery front door for TemporaryAI voices. It can search and index:

- candidate recordings and official character clips;
- archival recording leads for historical people;
- synthetic voice/model-card candidates;
- exact URLs, catalog metadata, performer credits, and rights/consent status.

Discovery does not download video, audio, captions, thumbnails, datasets, or model weights. It does not extract clips, clone a voice, synthesize speech, assign a voice, or activate a TemporaryAI.

Implementation:

```text
Core/temp_ai_voice_discovery.py
tools/discover_temporary_ai_voice.py
tools/process_temp_ai_voice_discovery_queue.py
Testing/test_temp_ai_voice_discovery.py
Testing/test_temp_ai_voice_discovery_queue.py
```

Each new candidate created through either TemporaryAI builder now receives:

```text
TemporaryAI/candidates/<candidate_id>/voice_discovery_request.json
```

The network search is deliberately not automatic during candidate creation. This keeps candidate creation responsive and testable. Run it explicitly with the TemporaryAI Control Center button **Find Voice Sources (Metadata Only)** or:

```powershell
py tools\discover_temporary_ai_voice.py --candidate-id <candidate_id> --metadata-search
```

The index is written to:

```text
TemporaryAI/candidates/<candidate_id>/voice_discovery_index.json
```

The optional `--output` remains confined to that candidate folder and may name
only `voice_discovery_index.json` or a versioned
`voice_discovery_index_<label>.json`. It rejects symlink destinations and
cannot overwrite candidate inputs, profiles, activation plans, discovery
requests, or other reserved candidate metadata.

The command-line candidate builder also has an explicit combined option:

```powershell
py tools\create_temporary_ai_candidate.py ... --discover-voice-metadata
```

Without that switch it creates the queued request but performs no network search.

### Bounded automatic queue

One explicit start can now process pending candidates without a separate command for each one:

```powershell
Process_TemporaryAI_Voice_Discovery_Queue.bat
# or
py tools\process_temp_ai_voice_discovery_queue.py --max-candidates 3
```

This is a bounded one-shot worker, not an always-on crawler. The default batch is three candidates and the hard cap is ten. It uses an exclusive process lock, validates each request inside its candidate folder, binds results to the exact request hash, rechecks the request after provider calls, and writes only the candidate's fixed `voice_discovery_index.json`. Current complete or partial metadata-search indexes are skipped unless an operator explicitly supplies `--refresh`.

Use `--dry-run` to see the selected batch without any provider call. The queue inherits the same metadata-only implementation, so it has no route for downloading media/model payloads, extracting audio, cloning/synthesizing/assigning a voice, or activating a candidate.

## Identity Model

Voice evidence must not collapse these four records:

```text
character -> variant/version -> speaker role -> performer
```

Examples:

- Character: Beth Smith
- Variant: ordinary/Home Beth
- Speaker: Home Beth in the main English television version
- Performer: Sarah Chalke

Home Beth and Space Beth are different character variants/speaker labels but share the same credited performer. They can therefore have the same base performer timbre. The system keeps their speaker labels separate so that dialogue, emotional delivery, chronology, and characterization evidence are not assigned to the wrong Beth. It does not claim that they use two unrelated human voices.

Different performers, dubs, ages, adaptations, and recasts require separate performer records and usually separate voice profiles.

## Metadata Providers

The first backend supports:

- public video page/search metadata through `yt-dlp --skip-download`;
- Internet Archive catalog metadata through its JSON search API;
- Hugging Face model-card/catalog metadata through its public model API;
- exact user-provided seed URLs and manually reviewed rights evidence.

Every result records its exact URL, title, publisher/channel, provider, query, and available date/duration/license metadata. A search result is only a lead. Title matching is not speaker identification.

### Ranked review queue (2026-07-17)

The metadata index now writes `ranked_recording_review_queue`. Ranking is a
bounded review-order score, not a voice-selection score. It can reward:

- an exact reviewed official/rightsholder page or a pre-reviewed publisher
  registry match;
- target-character title terms;
- an exact binding to one selected continuity title;
- an official cast-credit binding from that title to the selected performer.

It lowers results with ambiguous/wrong identity terms and flags trailers,
teasers, interviews, behind-the-scenes material, songs, and young-character
variants because those often contain mixed speakers, music/effects, the
performer speaking as themself, or the wrong life stage.

Only an exact pre-reviewed publisher registry entry can enrich a provider
result. A platform badge is never silently promoted to recording rights. Every
rank record says `metadata_rank_only: true` and `auto_select_allowed: false`.

Each ranked recording now has four separate fail-closed cards:

1. `source_authority_gate`: exact publisher/page provenance;
2. `identity_evidence_gate`: selected title plus performer-credit binding;
3. `clean_segment_gate`: target-only character ranges, transcript or listening
   review, overlap/music/effects rejection, and at least 20 reviewed seconds;
   diarization remains grouping, not identity proof;
4. `technical_quality_gate`: sample rate, clipping, noise/reverb, consistency,
   and clean-speech review after authorized intake.

Rights/consent and listening approval remain additional gates. Passing title
and cast-credit binding does not prove that any second of a trailer is the
target speaker.

### Local-library source review bridge (2026-07-17)

When a request names owner-authorized files already under `Data/library`, the
discovery index now embeds a read-only `local_source_review_manifest`. The same
manifest and its human-facing queue can be refreshed with:

```powershell
py tools\audit_temp_ai_local_voice_sources.py --candidate-id CANDIDATE_ID
```

The command writes only these fixed candidate-folder artifacts:

```text
local_voice_source_evidence_manifest.json
clean_range_review_queue.json
```

It hashes each file, fails closed on a declared SHA-256 mismatch, and reads
container headers for duration and audio/video stream metadata. It does not
decode for listening, play media, extract audio, run diarization, identify an
acoustic group, run a voice model, synthesize speech, assign a voice, or
activate a candidate.

Local ranking answers only "which source should a human inspect first?" Every
clean-range list begins empty. A later human must identify exact target-only
ranges audiovisually, check production credits, and reject overlap, music,
narration, material effects, or the wrong character/life-stage. Diarization may
organize review groups but can never name Kathryn, Elsa, a performer, or any
other person automatically.

The provider command and API code contain no media/model download path. A request that enables `allow_media_download`, `allow_audio_extraction`, or `allow_model_download` is rejected.

### Exact online-source nomination and one-range owner review (2026-07-17)

The earlier hundreds-of-clips review window is no longer the only route for a
short source that Robert has already inspected. The bounded nominator accepts
an exact target/version/speaker/performer record, public video URLs, and exact
start/end times. It uses metadata to rank sources, penalizes song/music and
mixed-source titles, and records provenance without making a title or acoustic
cluster into an identity claim:

```powershell
py tools\auto_nominate_temp_ai_voice_sources.py `
  --candidate-id CANDIDATE_ID `
  --url EXACT_VIDEO_URL `
  --start-seconds EXACT_CLEAN_START `
  --owner-nominated-target-only `
  --metadata-search
```

An exact first URL is no longer required. When this command is run with only
`--candidate-id`, it reads the candidate's character and performer identity,
derives a bounded `official non musical spoken dialogue scene` query, enables
metadata search, and produces a ranked nomination list. It still downloads no
media and approves no speaker. A deliberately supplied exact URL remains
pinned ahead of unverified search leads unless later exact-bound machine
evidence establishes a reason to reject it. This lets the TemporaryAI creator
look for a first source without asking Robert to operate a clip-by-clip box:

```powershell
py tools\auto_nominate_temp_ai_voice_sources.py --candidate-id CANDIDATE_ID
```

Files:

```text
Core/temp_ai_online_voice_nomination.py
tools/auto_nominate_temp_ai_voice_sources.py
Testing/test_temp_ai_online_voice_nomination.py
```

The normal nomination stage remains metadata-only. Optional exact-bound
machine evidence must carry the media SHA-256, analyzer/version, an
owner-approved target-face reference, target-face active-speaker coverage,
single-speaker/overlap measurements, and conservative audio-quality data. Any
missing or mismatched field fails closed.

When Robert has already reviewed one exact, <=45-second audiovisual range, a
hash-bound owner-attestation JSON plus the already-local source and exact-range
mono PCM WAV can produce one `automatic_voice_source_owner_range_review.json`.
The builder verifies exact URL/range bindings, local source and WAV hashes,
WAV duration, sample rate, clipping, active/silent frame ratios, and a
percentile SNR proxy. Robert's attestation supplies the target identity and
target-only speech decisions. A separate exact-bound contamination record can
flag music, tonal residue, material noise, or overlap. Machine contamination
evidence takes precedence over an accidental human `no_music` selection.

This one-range route can replace the hundreds-of-unrelated-clips box for that
exact owner-reviewed range. A clean range may become eligible for a later
private reference-pack build; a target-only range with contamination remains
useful candidate/reference evidence but is routed to separation or cleanup and
then QC first. It still does not train/clone, assign, synthesize, activate,
publish, or grant an official-voice claim. Face/active-speaker automation is
used only when the required analyzer and exact identity-reference binding
exist; otherwise the output says it was unavailable instead of inventing a
pass.

## Recording Candidate Gate

An official clip proves where the clip came from. It does not prove permission to train, clone, or market a performer's voice.

Every recording candidate starts with:

```text
metadata_only: true
media_downloaded: false
audio_extracted: false
eligible_for_voice_model_input_now: false
official_voice_claim_allowed: false
```

Before a discovered source can become a model/public-use source, reviewers must establish:

1. Exact source and provenance.
2. Target character/variant/speaker identity.
3. Performer credit.
4. Recording copyright and intended-use rights.
5. Voice-model/training/synthesis rights.
6. Living-performer consent when an exact or confusingly similar performer voice is sought.
7. Character, brand, and distribution permissions separately.

Public availability, an official uploader, a purchased episode, a model repository, or a model code license does not satisfy all of those conditions. This model/public-use list is not a ban on bounded private-local candidate extraction: `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md` accepts explicit Robert authorization plus exact source, range, identity, and clean-segment review, while leaving training/assignment/activation/public claims false.

## Clean Segment and Speaker Review

If later intake is authorized, the existing Voice Reference workflow remains mandatory:

```text
metadata discovery
-> explicit authorized media intake
-> speech segmentation
-> acoustic grouping/diarization as a review aid
-> transcript/credit/human speaker identification
-> reject overlaps, narrators, music, and effects
-> approve target-only segments
-> minimum 20 reviewed seconds
-> model-reference preparation
```

Diarization creates acoustic groups. It does not identify a person. Two character variants with one performer can fall into the same acoustic group; they still need correct variant labels. One performer using different delivery styles can also split across groups.

No model-reference file should be called target-ready until the target-only clips and authorization are reviewed.

## Living Performer And Public/Model Assignment Gate

For a living performer or real person, exact biometric replication requires both:

- explicit performer/person consent; and
- explicit rights covering the recording, dataset, model use, and intended output.

A third-party model claiming to imitate a living person remains blocked for assignment/public use when consent evidence is absent. A permissive model-weights license is not performer consent and may not establish the voice dataset's rights. This does not prevent the separate private-local lane from preparing identity-reviewed reference evidence under explicit project-owner authorization.

When those conditions are not met, a fictional reconstruction may use a licensed original voice selected for broad non-biometric traits such as:

- age presentation;
- pace and energy;
- clarity and register;
- broad accent family;
- emotional range;
- dry, warm, formal, guarded, energetic, or restrained delivery.

It must not be confusingly similar to the named performer and must be labeled internally as unofficial/non-imitative. It may never be advertised as the official character or actor voice.

## Synthetic Model Candidates

Model discovery indexes model-card metadata only. It separately records:

- code/weights license;
- whether voice/dataset rights are documented;
- whether a named identity is claimed;
- whether identity authorization is documented;
- whether the model is only eligible for technical license review.

The current backend does not auto-select any discovered model. Even an MIT, Apache, BSD, or CC BY model remains unavailable to the candidate until model-card, dataset/voice identity, technical, quality, and listening reviews pass.

Wrong-language, wrong-age, wrong-presentation, and unrelated search results can remain in the index as rejected/low-relevance leads; they are never silently promoted.

## Historical Person Lane

Historical discovery first looks for a verified recording. A result counts as verified only when the index has evidence for:

- the historical subject as speaker;
- an authentic original recording, not a reenactment, narrator, documentary, dramatization, or search-summary claim;
- a traceable archival object/provenance chain;
- rights that permit the planned technical use.

A catalog title or video titled with the person's name is not a verified recording.

If no verified recording is indexed, the backend emits:

```text
speculative_educational_voice_design_only_no_verified_recording_indexed
```

The design can use reviewed factors:

- date or era;
- age or age band at the selected timepoint;
- places and regional influences;
- education and profession;
- languages/dialects;
- documented health or direct voice descriptions.

Each factor keeps evidence URLs and confidence. Missing factors stay unknown. The system does not infer exact pitch, biometric timbre, cadence, accent, health, or psychology without evidence.

The fallback uses a licensed generic original voice and must say:

```text
speculative educational reconstruction; not the historical person's authentic voice
```

Artistic defaults are labeled as artistic defaults. The system never fabricates a recording, archive citation, quote, consent record, or voice trait.

### H. H. Holmes Example

The current H. H. Holmes index contains metadata leads but no verified Holmes recording. Documentary narrators, dramatizations, Sherlock Holmes results, and a supposed wax-cylinder claim are not authentic-voice evidence. His current lane is therefore a speculative educational design with unresolved factors, not an authentic Holmes voice.

Files:

```text
TemporaryAI/candidates/h_h_holmes_h_h_holmes_20260605_221432/voice_discovery_request.json
TemporaryAI/candidates/h_h_holmes_h_h_holmes_20260605_221432/voice_discovery_index.json
```

## Beth Example

The supplied official Adult Swim clip is indexed as a mixed Home-Beth/Space-Beth scene performed by the same credited performer. This supports the user's observation that they sound the same at the base-performer level. It is not clean Home-Beth-only delivery evidence, and official upload status does not establish voice-model rights or Sarah Chalke's consent.

The automatic metadata pass found additional recording leads and synthetic model-card leads without downloading any payload. None is assigned, model-ready, or activation-ready. Exact Beth reference candidates may now be prepared through the separate private-local bounded lane when a source is locally available and Robert authorizes exact ranges; Home Beth still requires target-only dialogue review because the supplied clip mixes Home Beth and Space Beth. Model assignment, activation, public release, and an official-voice claim remain separate.

Files:

```text
TemporaryAI/candidates/beth_smith_ordinary_temp_20260716/voice_discovery_request.json
TemporaryAI/candidates/beth_smith_ordinary_temp_20260716/voice_discovery_index.json
Avatar/temp_ai/beth_smith_ordinary_temp_20260716/beth_voice_plan.json
```

## Elsa Example

Elsa's old *Frozen Fever* 96-clip review pack is retired as the current source
path. Its highest WavLM similarities were dominated by sung or scored material,
so acoustic similarity alone is explicitly not accepted as a clean spoken-voice
decision. `Review_Elsa_Voice_Candidates.bat` no longer opens that clip window.

The one-click path now uses Walt Disney Animation Studios' official spoken
deleted scene `utAwhtPlx8c`, *Disney's Frozen - "The Dressing Room" Deleted
Scene*. Two bounded Elsa-only spoken ranges were selected: 40.12-43.72 seconds
and 54.86-58.16 seconds. Both passed the bounded signal-quality checks without
the basic contamination proxy flag. The builder reuses their hash-bound cached
analyses and concatenates the exact PCM frames into a deterministic 6.9-second,
mono 16 kHz evidence WAV.

This is clean bounded evidence, not a claim that a model has proved identity.
No voice model, synthesis, assignment, playback, or activation was created.
The local WavLM listener also compared it with two different official Disney
MENA deleted-scene ranges. *Secret Room* 75.15-82.85 seconds scored 0.963034,
and *A Place of Our Own* 87.05-90.75 seconds scored 0.957668. Both support
same-speaker consistency across independent recordings. Both also contain
tonal/music residue and remain cleanup/QC evidence rather than direct model
input. A later private listening/model-governance stage remains separate. The
launcher fails closed if either exact clean anchor range loses its quality,
contamination, location, or SHA-256 binding.

Files:

```text
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/voice_discovery_request.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/voice_discovery_index.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/local_voice_source_evidence_manifest.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/clean_range_review_queue.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/automatic_voice_source_nomination_request.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/automatic_voice_source_nominations.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/workbench/inputs/identity_reviews/elsa_automatic_official_voice_evidence.json
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/workbench/inputs/identity_reviews/elsa_official_dressing_room_evidence.wav
TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/workbench/inputs/identity_reviews/elsa_official_cross_source_speaker_consistency_20260717.json
```

## Relationship to Fast VR Speech

Discovery and provenance answer which voice may be used. They do not guarantee low latency. VR readiness separately requires a locally cached approved voice, warmed inference, streaming/chunk scheduling, interruption behavior, device tests, and measured time-to-first-audio. See `REALTIME_AUDIO_AND_VR_READINESS_v1.md` when that runtime work is evaluated.

## Explicit Bounded Online Analysis

Metadata nomination never silently downloads media. When the project owner has
explicitly authorized private analysis, the separate
`Core/temp_ai_online_media_analysis.py` stage may acquire only one named public
URL range of 2–45 seconds. It SHA-binds the acquired media, bounded review
video, mono 16 kHz PCM, and silence-bounded segments. It records signal quality
plus basic tonal, noise, and overlap proxies. All prepared segments remain
identity-unverified and disallowed as model input until later evidence passes.

The user-facing CLI is
`tools/acquire_temp_ai_online_voice_evidence.py`; the authority flag is
`--owner-authorized-private-analysis`. A failed provider request records a
failure artifact and changes no voice, identity, body, world, or runtime state.

## Current Limitations

- Source search and title ranking are metadata based. The separate local
  speaker-consistency stage listens to bounded WAVs, but it supports only a
  same-speaker consistency decision and cannot identify a person by itself.
- Provider coverage is limited to the implemented video, Internet Archive, Hugging Face, and seeded-URL metadata paths; commercial/closed voice catalogs and the whole web are not searched.
- Internet search results can be irrelevant or misleading.
- Model-card license fields can be incomplete or wrong.
- The backend does not inspect model weights or datasets.
- It does not resolve copyright, publicity, performer, union, contract, or character-IP questions automatically.
- It does not select a final voice.
- Nomination does not silently download or prepare media. Any acquisition and
  bounded-audio preparation must be an explicit, logged stage.
- It does not generate an audition or synthesized voice.
- It does not activate a TemporaryAI.
- The queue is intentionally operator-started and bounded; it is not a background service or unrestricted crawler.
- Human source, rights, identity, listening, and quality review remains required.
