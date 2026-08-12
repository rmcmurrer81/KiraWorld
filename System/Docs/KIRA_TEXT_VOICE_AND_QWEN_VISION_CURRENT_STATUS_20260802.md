# Kira Text, Voice, and Qwen Vision Current Status — 2026-08-02

## 2026-08-03 latency addendum — newest voice truth

Latest normal-server Attempt 07 proves exact `llama3.1:8b` plus the approved
one-shot Blackwell CUDA voice route on both turns, with no CPU fallback. It is
an engineering route pass, not a latency pass: text-ready was `5.501`–`6.295`
seconds and one-shot GPU synthesis was `14.215141`–`20.894460` seconds.

The inactive persistent candidate has a narrow default-off telemetry repair:
background external `nvidia-smi` polling during CUDA load was replaced with
operation-boundary snapshots. No production route changed, and no live GPU or
owner conversation was run for the repair. Its exact two-turn owner-hearing
configuration is prepared but fail-closed pending a new standalone two-WAV
persistent-worker pass. Do not enable or describe the persistent route as
accepted yet.

Full diagnosis, hashes, and rollback boundary:
`RecoverySprint/continuation_20260803/kira_text_voice_latency_bounded_repair_preparation/`.

## Current owner-facing routing truth

Normal Kira Text + Voice remains:

- text model: `llama3.1:8b`;
- exact Llama digest:
  `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`;
- preferred approved voice: Blackwell eager-CUDA Chatterbox;
- sole automatic approved fallback: sealed CPU Chatterbox;
- generic/SAPI fallback: not approved.

Qwen vision is now owner-authorized for two bounded visual paths: the separate
indexed-media first-look tool and the explicit `Look Now (one still)` webcam
bridge. It is **not** the normal Kira text model. The one-still bridge is not
continuous viewing and does not enable identity recognition, appearance
memory, personality/life-loop learning, body activation, Kira World visual
activation, or Video Studio.

The exact installed visual candidate is:

- model: `qwen3.5:9b`;
- digest:
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- locally reported capabilities: `completion`, `thinking`, `tools`, `vision`.

## Text and voice Series 05

The exact append-only Series 05 report is:

```text
RecoverySprint/continuation_20260802/followup_series_05/
  KIRA_MODEL_QUESTION_SERIES.json
```

SHA-256:
`29441db1927e55a2e3fc60dd71c719ee900d802686689ee230c4945800f43127`.

All four turns passed the bounded engineering gates, used the exact Llama
digest, generated one readable/non-silent Blackwell-GPU voice chunk, used no
CPU fallback, had no continuation gap, and left Kira inactive with ports and
Ollama clean. The voice self-check cache was a proven process-memory `hit` for
all four turns with key:

```text
73fdc285a3e3d2faaaf8b5db03aab94ff965cd02fd7538151c5e0778c37c1cc1
```

This is not an owner-latency pass. Text-ready times were `12.505`, `19.324`,
`6.300`, and `6.044` seconds. GPU synthesis times were `17.103`, `15.491`,
`15.785`, and `17.117` seconds. Request-to-complete-voice times were `35.941`,
`41.372`, `28.400`, and `29.462` seconds. First-audible time was represented
only by a playback API proxy; no owner-heard timestamp was captured.

The live series also retained a repeated “I'm here ... a little quiet” model
opening and made unnecessary extra model calls on the current-work question.
Narrow post-series repairs are covered by focused tests but have not been
retroactively promoted or live-accepted. Full detail is in:

```text
RecoverySprint/continuation_20260802/followup_series_05_owner_review/
  MODEL_QUALITY_AND_LATENCY_DIAGNOSIS.md
```

Owner-review note SHA-256:
`0b7337fbc130e7ca1a1d8a95a92aa281506ab77db5f4fcb2f9d87a7c0b5d49a0`.

## Qwen vision bounded live acceptance

The visual lane analyzed one exact indexed general-library item with two
transient frames inside an eight-second window. It made no full-watch,
identity, recognition, memory, learning, preference, or off-frame claim.

Source binding:

- path:
  `Data/library/video_commercials/power_rangers/s_1_3_mighty_morphin_power_rangers/mighty_morphin_power_rangers_talking_rangers_and_lord_zedd_toy_commercial.mp4`;
- source SHA-256:
  `a9a8ca814df2a73191d0725ae91fb33bd8c78a50980ba3e03bae7fec25fc7797`;
- opaque media ID:
  `69bbc23292971ea984c7167962bd7b9eccb0cc56ae6c9e28db0b3eb4d59e0bd0`;
- category: `GENERAL_LIBRARY_MEDIA`;
- viewer lane: `kira` / `adult`.

### Attempt 01 — preserved failed closed

```text
RecoverySprint/continuation_20260802/qwen_vision_media_first_look/
  attempt_20260802T084740_259441Z_53e486d2/
```

The exact model, digest, and reported vision capability passed preflight, but
the attempt stopped before frame extraction or model loading because system
`PATH` had no `ffmpeg`. Its exact blocker was:

```text
QwenVisionLaneError: ffmpeg is required for bounded timed video sampling.
```

Evidence hashes:

- JSON:
  `3c43e97ac6edc300d06d2ee84ce479abe891147e62aa84cc52524b9329b511ed`;
- Markdown:
  `55573f95b58d77644aefba9bee3d15dd73cc74a6b824e0bf447beb409a3409e4`.

No model remained resident.

### Narrow bundled-ffmpeg repair

The sampler now selects the already-installed `imageio-ffmpeg` executable when
system `ffmpeg`/`ffprobe` are unavailable. Nothing was installed or downloaded.
The repair changed only executable selection and bounded duration/sampling
support; it did not change the source, model, normal text route, access policy,
or evidence history.

Current implementation hashes:

- `tools/create_qwen_vision_media_first_look_note.py`:
  `b07da5f94852da7c066ac04f2bbb61e953f0a28c49997ea7ab0f2ff3fe097b1b`;
- `Testing/test_qwen_vision_media_first_look.py`:
  `d39ab643a1cee1ab248012294ab94abdd1aee6e1e61bc7278cd9092fea2bcfe2`;
- detailed lane document:
  `System/Docs/QWEN_VISION_MEDIA_FIRST_LOOK_LANE_20260802.md` at
  `f5a3737148c50a1d0a81793afeb67a57ed4f9a372e3a1af3c88261e1e61e8d95`.

### Attempt 02 — bounded engineering pass

```text
RecoverySprint/continuation_20260802/qwen_vision_media_first_look/
  attempt_20260802T084900_245992Z_2fe2bdbe/
```

Measured evidence-to-verified-unload time was `10.902595` seconds (about
`11.5` seconds for the command wrapper). The accepted scope was
`SAMPLED_VIDEO_FRAMES_ONLY`; `identity_status` was `NOT_EVALUATED`; visible
media text was treated as untrusted quoted content; no frame, frame path,
timestamp, or frame hash was retained; no automatic memory or learning write
occurred; and the exact Qwen model was absent from `/api/ps` after explicit
unload.

Evidence hashes:

- JSON:
  `e41bf1f26caaf7c7e6833754971cb8fdcb4860d77c1828b07d7b3615a7f3ea27`;
- Markdown:
  `79d9c797d459474d2e9888068bb4feff6f47b469bdf96c11f82d5ab181cbc5f7`.

The result correctly quoted `MIGHTY MORPHIN POWER RANGERS` and described a
dark, colorful title-card style. It likely mistook the central logo shape for
a large number `6`. Because raw frames were deliberately not retained, that
detail cannot be adjudicated from the evidence package. Attempt 02 is an
engineering/schema/unload pass, not a general semantic-accuracy, webcam,
person-recognition, identity-memory, full-media, or owner-experience pass.

The consolidated live record is:

```text
RecoverySprint/continuation_20260802/qwen_vision_media_first_look/
  LIVE_ACCEPTANCE_20260802.md
```

Its SHA-256 before this status note was authored was
`92bad25814de11aa0287c96526e562ddfbd13176844cbf0a054b237658fbab7a`.

## Verification

The following focused set passed after the Series 05 and Qwen repairs:

```text
69 tests passed

Testing.test_kira_historic_activity_timing
Testing.test_kira_requested_brevity
Testing.test_voice_output
Testing.test_voice_benchmark_capture
Testing.test_qwen_vision_media_first_look
```

These are unit/mock and contract tests. They do not create a new live Kira
conversation, open the webcam or microphone, run identity recognition, write
memory, or repeat Qwen Attempt 02.

## Rollback and protected boundaries

- The indexed-media Qwen lane remains opt-in. The explicit one-still bridge can
  be disabled without changing Llama, preview, microphone, or voice by setting
  `KIRA_ENABLE_QWEN_ONE_STILL=0` for the launcher process.
- If the bundled-ffmpeg repair regresses, revert only the executable/duration
  fallback and its focused tests. Preserve both append-only attempts.
- If the post-Series-05 reply repairs regress, revert only their narrow
  detector/transform changes. Preserve Series 01–05 evidence.
- If voice self-check cache invalidation regresses, revert only the
  process-memory cache. Do not modify either sealed Chatterbox worker, the
  approved voice profile/reference, or approved routing.
- Do not delete, redownload, alter, or promote Qwen or Llama as part of a
  rollback.
- Webcam capture, Robert recognition, identity enrollment, visual memory,
  automatic learning, normal Qwen text routing, body/world activation, and
  Video Studio remain outside this status.

## Explicit webcam one-still bridge

Robert explicitly authorized Qwen vision for Kira's visual look path. The
existing `Look Now (one still)` button now has an opt-in exact-Qwen bridge for
one fresh webcam still. Continuous/low-rate Qwen capture, identity
recognition, appearance memory, automatic learning, and normal Qwen text
routing remain disabled.

Implementation is fail-closed: exact model digest and `vision` capability,
HTTP loopback, current selected person plus sensory lease, empty Ollama
residency, Blender absence, chat/voice serialization, one complete JPEG, no
camera-byte/hash persistence, 45-second derived-cue expiry, untrusted screen
text, strict non-identifying output, and verified Qwen unload are mandatory.
Llama 3.1 8B remains the normal text model.

Only mocked tests and syntax/compilation checks ran while Blender was active;
no webcam or live Qwen call was made. The focused bridge suite passed `39`
tests; the broader related mock/contract suite passed `86` tests. Live webcam
owner acceptance remains pending.

Exact checkpoint:

```text
RecoverySprint/continuation_20260802/qwen_vision_explicit_webcam_one_still/
  CHECKPOINT.md
```

Checkpoint SHA-256:
`29ed92990c6a4b84ec576d456d20b56a19cd2a8bb53630f1adcf7908af662572`.

The checkpoint contains the exact changed-file hashes, `39`-test command,
deferred live procedure, fail-closed workload conditions, and component-scoped
rollback. The detailed design also remains in
`System/Docs/QWEN_VISION_MEDIA_FIRST_LOOK_LANE_20260802.md`.
