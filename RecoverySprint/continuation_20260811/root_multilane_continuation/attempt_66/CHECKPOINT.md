# Root multilane continuation checkpoint — attempt 66

Recorded UTC: `2026-08-12T01:05:45.8726077Z`

## Camera/Qwen routing metadata reconciliation

The voice-pipeline camera contention guard from attempt 65 remains intact:
recurring low-rate samples return before canvas draw/JPEG while either ordinary
chat generation or the existing voice pipeline is active, and explicit
`Look Now` remains unchanged.

One stale configuration key still claimed that Llama was the normal text
default. That old key has been removed. The exact current metadata now states
`qwen3_5_9b_remains_normal_text_default: true` and retains the exact model
`qwen3.5:9b` with digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
This is metadata/test reconciliation; it does not switch or invoke a model.

Exact current files:

- `tools/kira_text_voice_devices.js`: 42,231 bytes, SHA-256
  `3ab2ce307ccf3a27ee1b4932406fbeaae4495c2c030189caed2d51b3d619aefe`.
- `tools/kira_world_shell_server.py`: 607,036 bytes, SHA-256
  `68edc7c34a0d0edaf1033b7bf7fecdcabb39ae6c6d678fbe13de224a14992810`.
- `config/kira_text_voice_device_capture.json`: 4,478 bytes, SHA-256
  `7cd38e8c1ce3e3359cf4bcf2a71cad8cec0af7b38504d9f8607a3f70f4bbff13`.
- `Testing/test_kira_text_voice_device_capture.py`: 20,855 bytes, SHA-256
  `008960e9e0cc743f9075b909a7a9b54dadc4299d41277cbb6f402a30da8a7e9b`.

Focused device tests pass `13/13`; JavaScript syntax and shell-server strict
Python compilation pass. No camera, Qwen, voice, audio, playback, identity,
memory, or network operation ran. No measured latency improvement is claimed.

