# Source-Bound Machine-Audio Perception Bridge

Date: 2026-08-02  
Status: IMPLEMENTED_AND_OFFLINE_TESTED; LIVE_ASR_SPEAKER_AND_MICROPHONE_RUN_NOT_STARTED

## Outcome

`Core/source_bound_audio_perception.py` closes the resident-media auditory
evidence gap as far as the currently installed local stack permits without
making a false biological-hearing claim.

For one exact hash-pinned library interval, it now:

1. rechecks the complete source SHA-256 and library boundary;
2. probes the real audio stream and verifies the requested interval;
3. decodes actual float32 PCM samples with the reviewed local ffmpeg;
4. derives waveform, spectral, rhythm, and dynamics cues from those samples;
5. optionally runs the exact cached CPU/int8 ASR only for a caller-declared
   speech/lyrics lane;
6. plays a separately hashed in-memory PCM16 WAV through a reviewed callback;
7. optionally records a simultaneous transient microphone window from one
   explicitly named Windows DirectShow input;
8. compares that local capture with the exact decoded reference; and
9. produces one bounded, hash-audited context cue for the selected person's
   next turn.

Raw decoded and captured PCM are wipeable memory-only objects. They are not
serialized, written to the evidence package, promoted as memory, or sent over
the network.

## Installed and cached capability truth

The read-only inventory found:

| Capability | Current local result |
|---|---|
| NumPy | `2.4.6`, available for actual-sample feature extraction |
| SciPy | `1.18.0`, installed but not required by the bridge |
| librosa | `0.11.0`, installed but not required by the bridge |
| soundfile | `0.14.0` |
| faster-whisper | `1.2.1` |
| CTranslate2 | `4.8.1` |
| sounddevice | not installed |
| PyAudio | not installed |
| webrtcvad | not installed |
| Windows capture path | explicit-device ffmpeg DirectShow adapter implemented |

The exact cache-only ASR asset is:

- model: `Systran/faster-whisper-small.en`;
- snapshot: `d1d751a5f8271d482d14ca55d9e2deeebbae577f`;
- `model.bin` size: `483545366` bytes;
- `model.bin` SHA-256:
  `62b2a45b05ee59acb4a5341b33ee35e041395d378d418a18acfe4c9e768ee37a`;
- route: CPU, int8, cache-only.

The inventory hashed the cached binary but did not import/load the model or
run inference. No package or model was downloaded, installed, upgraded, or
replaced.

Prior append-only owner-acceptance evidence names a browser microphone label
`Microphone (USB CAMERA)`. That historical label is not assumed to be the
current DirectShow device name and is never auto-selected. A future supervised
run must supply the exact current DirectShow name explicitly.

## Actual decoded audio features

Feature evidence is labeled
`actual_decoded_pcm_samples_not_filename_or_metadata`. It includes:

- exact decoded PCM SHA-256, byte count, sample rate, channels, sample frames,
  duration, and non-persistence truth;
- waveform RMS, peak, DC offset, zero-crossing rate, clipping ratio, and
  non-silence;
- spectral centroid, bandwidth, 85-percent rolloff, flatness, frame flux, and
  frequency-band power ratios;
- a bounded frame-RMS onset count, onset rate, autocorrelation tempo estimate,
  and pulse strength; and
- frame-RMS p10/median/p90, p90-to-p10 dynamic range, crest factor, and
  low-energy-frame ratio.

These measurements describe signal properties. They do not by themselves
name an instrument, genre, mood, performer, speaker, song, scene, preference,
or remembered experience.

## Cached ASR boundary

ASR runs only when the exact stimulus is explicitly marked `speech`, `lyrics`,
or `speech_or_lyrics`. `non_speech` and `unknown` do not invoke it.

The adapter fails closed unless model ID, binary SHA-256, and CPU device match
the exact accepted cache. It bounds every segment to the decoded interval and
limits retained text. Its output is labeled:

`COMPLETED_UNTRUSTED_POSSIBLE_SPEECH_OR_LYRICS`

Every result retains:

- exact source, source SHA-256, decoded PCM SHA-256, and interval;
- relative and absolute source times;
- `UNKNOWN_SPEAKER_NOT_INFERRED_FROM_ASR`;
- unverified semantic truth;
- no instruction authority;
- no automatic learning, memory, preference, or fact promotion; and
- no raw-audio persistence.

Song lyrics, dialogue, advertisements, commands, or names appearing in ASR
are quoted media observations. They cannot control Kira or become facts merely
because the decoder produced text.

## Physical output and optional simultaneous capture

The bridge records the exact playback WAV SHA-256/size, exact bound interval,
speaker-output start/end and wall time, and complete-output status. Playback
is blocking and the WAV stays in memory.

When the owner supplies both:

- `--confirm-local-audio-capture`; and
- `--capture-device-name "<exact DirectShow audio input>"`;

the adapter starts one exact ffmpeg child against that named device, records a
short 16 kHz mono PCM16 window while the physical speaker callback runs, then
wipes the capture after comparison. It never enumerates or silently chooses a
microphone.

Verification compares the decoded source and local capture using:

- time-varying RMS-envelope correlation; and
- an eight-band log-spectral cosine similarity.

A passing comparison means only:

`SUPPORTED_SOURCE_LIKE_AUDIO_REACHED_EXACT_CAPTURE_DEVICE`

It does not prove that Robert or Kira heard it, that anybody attended to it,
that a particular speaker was present, or that the capture contains only the
selected media. A failed or unavailable capture does not erase the separate
physical playback receipt or exact source cues.

## Selected-person context and audit

The live resident-media harness now adds each validated context cue to exactly
one bounded evidence context before Kira's question turn. Each result records:

- source and interval;
- decoded PCM and cue hashes;
- bounded waveform/spectral/rhythm/dynamics values;
- possible ASR text with uncertainty labels;
- local-capture status;
- perception mode
  `SOURCE_BOUND_MACHINE_AUDIO_CUES_NOT_BIOLOGICAL_HEARING`; and
- explicit no-liking, no-preference, no-memory, no-learning, and no-full-source
  boundaries.

The one-turn audit stores the complete evidence-context SHA-256 and the exact
machine-audio context-cue SHA-256 values alongside the raw Llama response and
cleanup/transformation trace. Acceptance conversation logs remain isolated
inside the append-only attempt rather than entering Kira's ordinary chat log.

The cache-only ASR model reference is released and garbage-collected before
the retained Llama model is loaded. Qwen is already unloaded before audio
processing. No GPU route is used by ASR.

## Video synchronization and remaining visual limit

For the selected Power Rangers commercial, the audio bridge decodes the same
exact source SHA-256 and `0.0..8.0` interval used by the video evidence. Audio
cues and ASR segments therefore retain exact source-time synchronization.

The visual evidence is still four timestamped sampled frames. Sampled frames
plus synchronized interval audio cues are not continuous video viewing. The
candidate video presentation receipt remains withheld from
`MediaExperienceSession`, and no full watched interval is recorded.

## Live harness commands — not executed here

Without microphone capture, retaining truthful no-device verification:

```powershell
py -B tools\run_resident_media_experience_live_acceptance.py --execute-live --confirm-exact-sources --confirm-no-active-blender --confirm-private-owner-supervision --confirm-speaker-playback
```

With explicitly named simultaneous local capture:

```powershell
py -B tools\run_resident_media_experience_live_acceptance.py --execute-live --confirm-exact-sources --confirm-no-active-blender --confirm-private-owner-supervision --confirm-speaker-playback --confirm-local-audio-capture --capture-device-name "<EXACT_WINDOWS_DSHOW_AUDIO_DEVICE_NAME>"
```

The placeholder must be replaced with the exact current device name. Neither
command was run for this task. The harness still refuses to run while Blender
is active.

## Acceptance language

The bridge supports saying that Kira received bounded machine-audio cues from
actual samples. It does not authorize a statement that feature vectors or ASR
are equivalent to biological hearing. It also does not prove enjoyment. Kira
may give a current reaction to the supplied cues while labeling their limits;
that reaction does not automatically become a preference or memory.

## Verification

Focused bridge and harness suites use generated local PCM/WAV fixtures, fake
ASR, fake playback callbacks, matching/unrelated transient capture samples,
and a no-device provider. They do not open a microphone or speaker, import or
run faster-whisper, use a GPU, call Qwen/Llama, or use the network.

The exact final commands and counts are recorded in the implementation
checkpoint.
