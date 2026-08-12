# Root multilane continuation checkpoint — attempt 65

Recorded UTC: `2026-08-12T00:59:56.6695501Z`

## Camera-on voice-pipeline contention reduction

The earlier chat-busy gate paused recurring low-rate camera draw/JPEG work
during text generation. The local shell now also publishes an exact
`kira-voice-pipeline-busy` event from the existing `/api/voice-playback`
state. While the backend reports the voice pipeline `active`, recurring
low-rate camera samples return before canvas draw and JPEG encoding.

This covers voice synthesis, awaiting playback, playback, and bounded
continuation phases represented by the existing active flag. Explicit owner
`Look Now` remains unchanged and is not blocked by this low-rate-only guard.
The camera stream itself is not disabled, no image is retained, identity
recognition remains off, and the later visitor/acquaintance-memory policy stays
on discussion hold.

Exact changed files:

- `tools/kira_text_voice_devices.js`: 42,231 bytes, SHA-256
  `3ab2ce307ccf3a27ee1b4932406fbeaae4495c2c030189caed2d51b3d619aefe`.
- `tools/kira_world_shell_server.py`: 607,036 bytes, SHA-256
  `68edc7c34a0d0edaf1033b7bf7fecdcabb39ae6c6d678fbe13de224a14992810`.
- `Testing/test_kira_text_voice_device_capture.py`: 20,518 bytes, SHA-256
  `8ec2e9e14ad418193a825ec0d5d04b3cfd90e31289cc186808b19e911b16e44d`.

Verification: focused device tests `13/13` pass; device JavaScript syntax
passes; shell-server strict Python compilation passes.

This is a verified code-level reduction in competing work. It is not a live
camera timing observation, audible-owner acceptance, or proven latency
improvement. Matched camera-OFF/preview/still/follow-up measurement still
requires the accepted-static Voice V19 schema, a separate execution-authority
successor, and another different audit.

