# Root multilane continuation - attempt 63

Timestamp: `2026-08-11T20:51:24-04:00`

## Camera-on conversation contention reduction

The text/voice shell now emits a local `kira-chat-busy` event whenever the
ordinary chat pipeline enters or leaves its text-generation/voice-synthesis
request. The device controller tracks that exact local Boolean. While chat is
busy, its recurring low-rate camera timer returns before canvas draw and JPEG
encoding, just as it already did while a visual/Qwen request was in flight.

This removes recurring preview-side CPU/JPEG work from the latency-critical
text-to-voice interval. Explicit owner `Look Now` behavior is unchanged. The
camera still starts off, recognition remains off, no raw frame is retained,
and person-bound sensory gates remain exact.

Verification:

- device capture suite: 13/13 passed;
- device JavaScript `node --check`: passed;
- shell-server strict Python compile: passed;
- the test proves the busy gate precedes both `drawImage` and
  `canvasJpegBlob`, and that `setChatBusy` emits the local event.

Exact changed files:

- `tools/kira_text_voice_devices.js`: 42,052 bytes, SHA-256
  `d3fec274ec6be310476e08576937e8699b738de4042430bf583d19bd90081479`;
- `tools/kira_world_shell_server.py`: 606,814 bytes, SHA-256
  `97db41f7cbde3f2180ff86a61eb7911554d962bfc3976d4fd9b308dd91320d60`;
- `Testing/test_kira_text_voice_device_capture.py`: 19,819 bytes, SHA-256
  `76f93dd1552fb32b288c32e412b466ef4a317ef358c70c7e065cde39020d120d`.

This is a verified code-level competing-work reduction, not a live timing or
latency-pass claim. No model, GPU, camera capture, microphone, synthesis,
audio playback, person/private state, body/Blender, production, or Sarah path
was invoked by this change.
