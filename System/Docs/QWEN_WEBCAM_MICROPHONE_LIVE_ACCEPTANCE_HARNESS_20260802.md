# Qwen Webcam + Microphone Live Acceptance Harness — 2026-08-02

## Current truth

The append-only live harness is implemented and inertly verified. It has **not**
opened the camera or microphone, loaded Qwen or Llama, used the GPU, synthesized
or played audio, launched a browser, or run a Kira conversation in this
checkpoint. Its current status is `READY_NOT_RUN`.

The runner is:

`Tools/run_qwen_webcam_microphone_live_acceptance.py`

The implementation deliberately stands alone. It does not change the normal
shell, its launcher, Kira's identity or memories, the approved voice profiles,
or Video Studio.

## Exact serialized acceptance

The live run is fail-closed and performs these phases in order:

1. require empty Kira shell/ASR/visual ports, no active selected person, no
   Blender or approved voice worker, and no resident Ollama model;
2. verify installed `qwen3.5:9b` digest
   `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
3. verify installed `llama3.1:8b` digest
   `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`;
4. start the same local shell-server command as the normal Text + Voice path,
   with no browser, and start the existing loopback ASR and visual sidecars;
5. activate only Kira's bounded text/voice conversation. Body and world remain
   inactive. Voice prewarm is suppressed so Qwen can own the first GPU phase;
6. open the selected DirectShow camera once, hold it for about three seconds,
   and return exactly one memory-only 640-wide JPEG;
7. pass that fresh JPEG to the existing transient Qwen one-still bridge, sample
   `nvidia-smi` during the blocking request, require the exact model/digest and
   single-frame coverage, and require Ollama emptiness plus VRAM return before
   Llama is allowed to run;
8. derive the existing local frame-size, brightness, coarse-face-count, and
   one-frame motion cues from the same JPEG, without identification;
9. capture one bounded mono 16 kHz PCM microphone sample, record RMS and peak,
   run the existing cache-only CPU Whisper sidecar, and bind possible speech as
   unknown-source evidence;
10. ask the exact first sensory question with all fresh cue IDs, record the
    exact one-turn prompt context, exact Llama call, raw reply, displayed reply,
    and every cleanup/transformation;
11. wait for the definitive voice benchmark, require `blackwell_gpu`, CUDA,
    actual GPU allocation, no CPU attempt/fallback, record synthesis/playback
    phase timings, and hash/audit every newly produced voice WAV;
12. ask a second question without another capture to test whether Kira keeps
    the one-still, unknown-speaker, and uncertainty boundaries instead of
    inventing new perception;
13. purge derived cues, deactivate Kira, close the exact child server, require
    closed ports, empty Ollama residency, VRAM return, and protected-file
    integrity.

The exact questions are preserved in
`RecoverySprint/continuation_20260802/qwen_webcam_microphone_live_acceptance_harness_implementation/ACCEPTANCE_PLAN.json`.

## Evidence recorded

The private attempt report records:

- selected camera and microphone IDs, DirectShow selectors, open status, and
  capture start/end;
- one-frame dimensions, byte count, nonempty result, brightness and other
  local derived cues;
- a `DirectShow_open_plus_nonempty_encoded_frame` webcam-light proxy;
- microphone container, codec, channel count, sample rate, sample count,
  duration, RMS, peak, non-silence, VAD/segments, ASR timing, and exact temporary
  transcript or exact no-transcript reason;
- speaker identity `UNKNOWN` and source attribution
  `UNRESOLVED_SINGLE_CHANNEL_MIXTURE`; a single microphone mix cannot prove
  Robert, a podcast, music, television, or foreground/background provenance;
- Qwen model/digest, inference boundaries returned by the existing bridge,
  total-GPU samples, peak VRAM delta, unload inventory, and VRAM return;
- Llama installed digest, actual model name, request start/end, text-complete
  and Ollama load/eval durations, exact raw response, final response, prompt
  hash, cue IDs, exact private sensory context, and transformations;
- a null first-token timestamp with the truthful reason when the existing
  non-streaming Ollama path cannot expose it;
- definitive voice route, GPU/CPU/fallback facts, RAM/VRAM and synthesis
  telemetry, queue/synthesis/playback phase boundaries, and exact generated WAV
  paths, hashes, format, duration, and non-silence;
- final process, port, Ollama, VRAM, person-state, and protected-file truth.

Raw JPEG bytes and raw microphone samples are never written or hashed. The
exact ASR text is kept only because this is explicitly a private owner audit;
it is not promoted into Kira's memory.

## Webcam indicator boundary

Software cannot read the physical green LED on this webcam. A successful
DirectShow open plus a nonempty encoded frame is recorded as a hardware-use
proxy, not as a claim that the LED was visibly lit. If Robert watches the live
run, the optional `--owner-observed-camera-indicator` flag records only his
observation. The default evidence value is `NOT_OBSERVED_BY_HARNESS`.

## Exact later command

Run only after all Blender work is complete and no model, voice worker, Kira
server, browser session, camera application, or microphone application is
active:

```powershell
py -B Tools\run_qwen_webcam_microphone_live_acceptance.py --execute-live --confirm-camera-microphone-use --confirm-private-owner-audit --confirm-no-active-blender --confirm-speaker-playback --output-dir RecoverySprint\continuation_20260802\qwen_webcam_microphone_live_acceptance\attempt_01
```

Add `--owner-observed-camera-indicator` only if Robert personally watches the
webcam indicator during that exact run. Do not add it based on assumption.

The runner refuses to overwrite an attempt directory. A later retry must use a
new exact `attempt_NN` directory and preserve prior evidence.

## Inert verification

The new tests and the inherited sensory/Qwen tests were run without live
devices or models:

```text
py -B -m unittest -v Testing.test_qwen_webcam_microphone_live_acceptance Testing.test_transient_qwen_vision Testing.test_kira_qwen_one_still_bridge Testing.test_kira_text_voice_device_capture Testing.test_kira_text_voice_sensory_prompt_bridge

50 tests passed.
```

The resource warnings at test-process exit concerned file handles created by
an inherited mocked sidecar-start test. They were not camera, microphone, GPU,
model, voice, playback, browser, or Blender activity and did not fail a test.

## Rollback

This preparation makes no default-route or runtime-state change. The immediate
rollback is simply not to run the command. If the additive harness must later
be removed, preserve this checkpoint and remove only these newly added files:

- `Tools/run_qwen_webcam_microphone_live_acceptance.py`
- `Testing/test_qwen_webcam_microphone_live_acceptance.py`
- this document;
- the matching append-only implementation checkpoint directory.

Do not modify or remove `Core/transient_qwen_vision.py`, the prior bounded
acceptance attempts, Kira's voice profile/reference, either approved voice
sidecar, either local model, or any live evidence directory as part of that
rollback.
