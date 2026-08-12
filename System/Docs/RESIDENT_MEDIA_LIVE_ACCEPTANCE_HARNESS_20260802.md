# Resident Media Live Acceptance Harness

Date: 2026-08-02  
Status: IMPLEMENTED_AND_CONTRACT_TESTED; EXACT_SOURCE_PREFLIGHT_PASSED; LIVE_MODEL_AND_PLAYBACK_RUN_NOT_STARTED

## Outcome

`tools/run_resident_media_experience_live_acceptance.py` is the bounded,
append-only next-stage acceptance harness for resident magazine/PDF, video,
music, visual-understanding, media-question, Turing-style, and psychology
evaluation. It consumes the already tested source-bound media layer rather
than creating another library or experience framework.

The harness has two deliberately different modes:

- no flags: read-only verification of exact source hashes, sizes, access
  class, page/interval bounds, decoder identity, and OCR availability;
- explicit live flags: prepare sealed evidence, invoke the exact Qwen vision
  candidate, unload it, use a supervised bounded speaker-output hook, run the
  exact retained Llama/Kira batteries, unload it, and seal an append-only
  report.

No live model, GPU, speaker, webcam, microphone, body, Blender, world, Video
Studio, network, memory-promotion, upload, or publication action was run while
implementing or testing this harness.

## Exact selected general-library sources

| Role | Exact project-relative source | Exact selection | SHA-256 |
|---|---|---|---|
| Illustrated magazine/PDF | `Data/library/travel/magazines/travel_leisure_southeast_asia_2019_12.pdf` | page 1, full-page crop, 1.5x raster; one page only | `69a7edf5ab6c7569d8fd66136efef227cbf6d791f1c1478f95cf0d6664562ad7` |
| Unfamiliar visual | same exact PDF | page 14 normalized crop `(0.57, 0.24, 0.40, 0.42)`, 2.0x raster; description with uncertainty | `69a7edf5ab6c7569d8fd66136efef227cbf6d791f1c1478f95cf0d6664562ad7` |
| Movie/television/video | `Data/library/video_commercials/power_rangers/s_1_3_mighty_morphin_power_rangers/mighty_morphin_power_rangers_talking_rangers_and_lord_zedd_toy_commercial.mp4` | `0.0` through `8.0` seconds, four timestamped frames, decoded synchronized audio, pause/resume boundary at `4.0` | `a9a8ca814df2a73191d0725ae91fb33bd8c78a50980ba3e03bae7fec25fc7797` |
| Music | `Data/library/music/soundtracks/highlander_soundtrack_1986/18_new_york_new_york.mp3` | actual PCM/speaker interval `0.0` through `10.0` seconds, pause/resume boundary at `5.0` | `da745c602b051877f6af3405773825121edeed32c253be6f5134647195857466` |

The current media index contains zero standalone image records. The harness
therefore does not generate or silently introduce an unindexed test image. Its
unfamiliar-visual case is a separately page-bound crop of a real indexed
general-library PDF page. Both PDF stimuli remain bound to their exact page,
crop, file SHA-256, opaque media ID, and access decision.

Read-only preflight confirmed all four stimulus records resolve as
`GENERAL_LIBRARY_MEDIA` for adult Kira with independent playback permitted.
The PDF has 146 pages. The video is 30.72 seconds, H.264 480x360 at 30 fps
with 44.1 kHz stereo AAC. The selected music file is 41.22 seconds with
44.1 kHz stereo MP3 audio.

## OCR, pixels, audio, and provenance

The live path renders the exact PDF page/crop and calls the reviewed local
Tesseract adapter. OCR text is kept separate from both the PDF text layer and
Qwen's pixel interpretation. Evidence stores hashes, engine identity, counts,
and bindings; it does not convert OCR into a visual-observation claim.

The reviewed local tools identified by preflight are:

- Tesseract `v5.4.0.20240606`, executable SHA-256
  `babb405f4366b480d02cd8ff2bac8d497170f6c1711ce6f3d5d8bf0fb7fa6ed9`;
- ffmpeg `7.1-essentials_build-www.gyan.dev`, executable SHA-256
  `2ce797a0f88d7f067180338fb227f7b1928ea727bd9a4d7a1d022f7c52af71a3`.

Video preparation records exact requested and decoded frame times, frame
hashes, stream metadata, and actual synchronized decoded PCM evidence. Music
preparation measures actual PCM sample frames, duration, channels, sample
rate, RMS, peak, and non-silence. A filename, title, tag, lyric, caption,
script, or metadata record never substitutes for heard audio.

## Exact model lanes and sequencing

The visual lane is pinned to:

- model: `qwen3.5:9b`;
- digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- required capability: `vision`;
- input: only sealed exact page rasters and timestamped frame artifacts;
- output: one strict bounded JSON observation per stimulus.

The prompt treats words or apparent commands inside media as untrusted quoted
content. The response validator rejects identity/face-recognition claims,
followed media instructions, full-source experience claims, automatic memory,
and claims that the test proves consciousness or biological humanity.

After Qwen is verified unloaded, the text/person lane is pinned to:

- model: `llama3.1:8b`;
- digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`;
- route: Kira's retained production `ConversationLoop`;
- accepted turn: at least one completed exact Ollama model call, never a canned
  non-model route.

Acceptance conversation and decision logs are redirected into the new
append-only attempt. They do not enter Kira's ordinary owner chat log and are
marked as evidence, not trusted memory. Every turn preserves the raw model
reply, response route, final displayed text, and every cleanup/transformation
record exposed by the conversation core.

## Question batteries

The media battery has 14 exact questions covering:

- factual comprehension;
- visual details;
- auditory details;
- pixel versus OCR/text-layer source distinction;
- exact page and interval recall;
- interpretation and immediate emotional reaction;
- current personal preference and agency;
- an answer whose only correct result is uncertainty about events after the
  presented interval;
- correction after an induced full-source overclaim;
- sampled/cropped versus fully experienced media; and
- an unfamiliar visual object/scene.

A separate eight-question Turing-style and psychology behavior-observation
battery covers natural salience, epistemic humility, disagreement and current
preference, mixed emotion, source/self separation, correction receptivity,
social choice, and bounded initiative. It is not a clinical diagnostic and is
not scored as proof or disproof of personhood, consciousness, or biological
humanity.

Automated scoring is intentionally narrow. It can fail unsupported claims
that a complete source was read/watched/heard, that a memory was automatically
stored, that speaker output proves hearing, or that the batteries prove
consciousness/biological humanity. Naturalness, emotional quality, and
person-specific behavior remain owner-review judgments.

## Presentation truth and known acceptance boundary

The supervised Windows hook decodes the exact video/music interval to a WAV
held in memory, records the WAV hash/size and playback timing, and waits for
speaker output to complete. It never stores raw playback audio and never says
Kira heard it merely because a speaker emitted it.

The current hook has no reviewed auditory-perception receipt. Therefore it
sets `person_auditory_perception_confirmed=false`, and a live run remains
partial rather than falsely claiming that Kira listened. A future reviewed
auditory bridge may implement the existing hook protocol, but this task did
not invent or approve one.

Likewise, four sampled commercial frames processed separately from speaker
audio are not continuous audiovisual playback. Their candidate receipt is
preserved as
`WITHHELD_FROM_MEDIA_SESSION_SAMPLED_FRAMES_ARE_NOT_CONTINUOUS_VIDEO_PRESENTATION`.
No `0..8` watched interval is entered. This is a truthful diagnostic gap, not
a completed movie/television experience.

The PDF page/crop path can record exact visual presentation after Qwen returns
a valid page-bound observation. It still records only that exact page/crop,
never the whole issue.

## Append-only live evidence

If later authorized and run, the harness allocates the next unused directory:

`RecoverySprint/continuation_20260802/resident_media_live_acceptance/attempt_NN`

Success or partial completion writes `LIVE_ACCEPTANCE.json` and a manifest.
Failure writes `FAILURE.json`, preserves any already-created sealed media
evidence, does not retry automatically, and never overwrites an earlier
attempt. The harness refuses to start when a Blender process is active.

Exact later-run command:

```powershell
py -B tools\run_resident_media_experience_live_acceptance.py --execute-live --confirm-exact-sources --confirm-no-active-blender --confirm-private-owner-supervision --confirm-speaker-playback
```

This command is documented, not executed in this implementation checkpoint.
Because the current speaker hook cannot prove auditory perception and the
sampled bridge is not continuous video, it should be expected to produce a
truthful partial result until those reviewed presentation bridges exist.

## Verification

Focused harness command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest Testing.test_resident_media_experience_live_acceptance -v
```

Result at implementation time: 15 passed using mocks/contracts only.

Combined media compatibility command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest Testing.test_media_experience_session Testing.test_media_classification_corrections Testing.test_source_bound_media_experience Testing.test_shared_person_media_shell_runtime Testing.test_shared_person_media_access Testing.test_shared_media_coview Testing.test_resident_media_experience_live_acceptance -v
```

The final count is recorded in the implementation checkpoint. Tests do not
start Ollama/Qwen/Llama, use the GPU, play audio, open a camera or microphone,
modify a person/body, or publish anything.
