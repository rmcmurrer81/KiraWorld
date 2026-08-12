# Root multilane continuation checkpoint — persistent-v2 first-waveform refinement

Recorded UTC: `2026-08-12T01:33:33.291Z`

## Result

The ordinary Blackwell persistent-v2 voice path now applies a bounded second
split only when the normal splitter leaves one oversized waveform. It selects
a natural first phrase between 44 and 72 characters, preserves every word in
order, and leaves the remainder at least 32 characters. One-shot, persistent
v1, SAPI, and already-multi-chunk behavior are unchanged.

This is a local code-and-test improvement. It is not a measured latency pass,
not proof of calibrated speaker onset, and not proof of Robert-heard timing.
The latest complete captures show that per-turn Chatterbox reload remains the
dominant fixed delay; a later matched live run must measure the actual effect.

## Exact changed subjects

- `tools/kira_world_shell_server.py`: 607951 bytes, SHA-256
  `2ea2e54391877d06d540d59c59714de9e435c38f5dd45edccc1a0f349a859876`.
- `Testing/test_kira_world_dialogue_audio_continuity.py`: 17297 bytes,
  SHA-256
  `85664af91064435f592ce6e6177833e09e3ba3eaee0c0e2727aa9e45c222fde0`.

Strict in-memory compilation passed. The cache-free focused/broader voice and
shell suite passed `56/56` plus `4` subtests in `6.79 s`:

- dialogue audio continuity;
- shell messages;
- text/voice device capture; and
- Qwen 3.5 Blackwell-v2 resource serialization.

## Boundary

No model, GPU, synthesis, playback, camera, microphone, private state, person,
body, Blender, media, Sarah, network, or production route ran. Existing voice
captures remain labelled displayed-text-to-first-playback-API-proxy, not true
audible onset. Status remains `LATENCY_FAIL_PENDING_MATCHED_MEASUREMENT`.
