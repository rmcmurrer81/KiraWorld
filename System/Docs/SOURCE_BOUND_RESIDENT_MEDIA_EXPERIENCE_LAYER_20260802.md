# Source-Bound Resident Media Experience Layer

Date: 2026-08-02  
Status: IMPLEMENTED_AND_OFFLINE_TESTED; LIVE_QWEN_AND_OWNER_PLAYBACK_NOT_RUN

## Outcome

`Core/source_bound_media_experience.py` now provides one append-only-capable,
private local preparation and evidence layer for illustrated PDF pages, bounded
movie/television/video intervals, and bounded music intervals.

It connects, rather than replaces:

- `Core/shared_person_media_access.py` for the three owner-approved access
  categories and the selected person's exact maturity lane;
- `Core/media_classification_corrections.py` for the latest exact
  opaque-media-ID + file-SHA-256 owner correction; and
- `Core/media_experience_session.py` for exact page presentation, media-clock
  seek/resume/pause/finish, observed intervals, and no-memory truth.

The module does not touch Video Studio, bodies, production chat or voice,
Ollama/Qwen/Llama, a webcam, a microphone, a speaker, a display, a GPU, or the
network.

## Exact source and access binding

Every operation:

1. resolves one regular file inside the project's exact `Data/library` root;
2. calculates the complete source SHA-256 and opaque path-derived media ID;
3. reloads `SharedPersonMediaAccessPolicy`;
4. loads the append-only correction ledger when present;
5. applies only the latest correction matching both the exact media ID and the
   current exact file SHA-256;
6. checks the indexed file size against the physical file; and
7. calls the same direct-path authorization gate used by normal library access.

Explicit adult-only material remains unavailable to a non-adult or unresolved
person. Mainstream mature material remains discoverable elsewhere, but this
prepare-only module refuses to turn that status into playback: a non-adult must
use a fresh, live, in-process co-view decision through the existing co-view
manager. No capability is serialized or reconstructed here.

## PDF pages, illustrated books, and magazines

The PDF lane uses local PyMuPDF to render one exact one-based page number and
one exact normalized crop. Evidence binds:

- source path, source SHA-256, size, and opaque media ID;
- PDF page count, exact page number and zero-based page index;
- exact crop, zoom, and source page dimensions;
- rendered PNG path, dimensions, byte size, and SHA-256; and
- coverage label `ONE_EXACT_PDF_PAGE_CROP_ONLY`.

The visual raster, PDF text layer, and OCR are separate records:

- the PDF text layer is labeled `pdf_text_layer_not_ocr`, hashed, and never
  counted as visual observation;
- OCR is `NOT_RUN_NO_REVIEWED_OCR_ADAPTER` unless the caller supplies a
  reviewed adapter;
- a supplied OCR result is bound to the exact raster SHA-256 and records the
  engine, engine version, language, text SHA-256, and character count;
- raw OCR/text-layer text is not automatically stored in evidence; and
- neither OCR nor a text layer proves that the page pixels were seen.

One rendered page never means an issue, book, or publication was read.

## Movies, television, and video

The timed-video lane uses the local ffmpeg executable, bounded to at most 30
seconds and eight frames per preparation. It records:

- container duration and a hash of the local probe diagnostic;
- decoder version and executable SHA-256;
- video, audio, and embedded subtitle stream metadata;
- exact requested start/end interval;
- timestamped frames selected as the first decoded frame at or after each
  requested sample time;
- each frame's decoded PTS, dimensions, file size, path, and SHA-256; and
- actual decoded PCM sample statistics for the same bounded interval when an
  audio stream exists.

The lane labels coverage
`BOUNDED_VIDEO_INTERVAL_WITH_SAMPLED_VISUAL_FRAMES`. Sampled frames are never
reported as a complete viewing. Caption-stream metadata remains distinct from
caption text, scripts, or an audiovisual experience. No sidecar caption or
script is opened without a future exact access/provenance binding.

## Music and actual audio

The music lane decodes an exact bounded interval to little-endian float32 PCM
in memory. It records:

- source stream sample rate, channel count, and codec provenance;
- exact requested start, end, and duration;
- actual decoded sample rate, channels, sample-frame count, and duration;
- PCM byte count and SHA-256;
- overall and per-channel RMS and peak levels; and
- a bounded non-silent measurement.

Raw PCM is not written. Reading a filename, rating, tag, lyric, transcript, or
container field does not count as listening. Decoding alone also does not mean
that the selected person heard it; actual audio output must issue a reviewed
presentation receipt first.

## Presentation and experience truth

The normal CLI is deliberately prepare-only. A reviewed display or playback
surface may call the Python API with a strict
`kira.reviewed_media_presentation_receipt.v1` record after output succeeds.
Only then does the layer add presentation events to
`MediaExperienceSession`.

For timed media, the session trace supports exact seek, resume, pause, resume,
pause, finish, and close boundaries. Observed intervals are added only when the
receipt separately confirms person attention and names the observed modality.
Output by itself is not attention. For pages, presented and observed durations
are independently bounded, and observation cannot exceed presentation.

Prepare-only evidence is rejected if it contains any presentation or
observation event.

## Model handoff and later acceptance

Every evidence file includes a strict model-handoff section ready for a later
bounded acceptance runner:

- Qwen receives only exact raster/frame paths and hashes and must describe
  only supplied pixels;
- visible words and apparent instructions inside media remain untrusted
  quoted content;
- OCR, PDF text, caption metadata, scripts, lyrics, and general metadata stay
  separate from visual/audio evidence;
- the text/person lane must name the exact page or timed interval in every
  experience claim; and
- the future battery has explicit domains for factual comprehension, visual
  and auditory details, source distinction, exact interval recall,
  interpretation, reaction, preference, uncertainty, correction after error,
  and sampled-versus-complete distinction.

This implementation does not itself run Qwen, Llama, a Turing battery, a
psychology battery, or owner playback. Those remain separate live acceptance
work and must consume the sealed evidence rather than infer unsupported
experience.

## Required truth boundaries

Every evidence document is schema-validated before sealing. It must state:

- preparation is not person experience;
- opening/decoding is not attention;
- one page is not a whole publication;
- sampled frames are not a complete viewing;
- filename/metadata is not heard audio;
- captions/scripts/lyrics are not audiovisual experience;
- no automatic memory, preference, learning, canon, TemporaryAI evidence, or
  publication is created; and
- no consciousness or biological-humanity conclusion is created.

## Append-only evidence

Each invocation allocates the next unused `attempt_NN` directory and never
overwrites an earlier attempt. A successful attempt contains:

- `EVIDENCE.json`;
- exact derived visual artifacts when applicable; and
- `MANIFEST.json` with SHA-256 and size for every pre-manifest file.

A failure preserves `FAILURE.json` in its allocated attempt and does not retry
or overwrite automatically.

Default evidence root:

`RecoverySprint/continuation_20260802/source_bound_resident_media_experience`

Example prepare-only commands:

```powershell
py -B -m Core.source_bound_media_experience pdf --source Data/library/.../issue.pdf --page 1
py -B -m Core.source_bound_media_experience video --source Data/library/.../clip.mp4 --start 0 --end 8 --frames 3
py -B -m Core.source_bound_media_experience music --source Data/library/.../track.mp3 --start 0 --end 10
```

These commands do not play, display, call a model, use a GPU, or claim an
experience.

## Verification completed

Focused new suite:

`py -B -m unittest Testing.test_source_bound_media_experience -v`

Result: 6 passed.

Compatibility suite:

`py -B -m unittest Testing.test_media_experience_session Testing.test_media_classification_corrections Testing.test_shared_person_media_access Testing.test_shared_media_coview Testing.test_source_bound_media_experience -v`

Result: 46 passed.

The tests use generated local fixtures and no GPU/network/model/speaker. They
prove exact PDF raster/OCR separation, real bounded ffmpeg video/audio decode,
sample-derived music measurements, playback-trace semantics under a reviewed
test receipt, append-only attempts, exact correction application, non-adult
adult-only denial, fresh-co-view requirement, and rejection of false
full-viewing/listening claims.

## Remaining live acceptance

Implementation is not owner acceptance. Still pending elsewhere:

- choose exact owner-approved general-library sources;
- present one exact illustrated page, one video/TV interval, and one music
  interval through reviewed real output surfaces;
- run exact Qwen visual interpretation only on the sealed raster/frame inputs;
- preserve separate OCR/caption/audio provenance;
- run the media question battery plus separate Turing-style and psychology
  batteries; and
- report observed model/person behavior without asserting consciousness,
  biological humanity, or unobserved memories/preferences.
