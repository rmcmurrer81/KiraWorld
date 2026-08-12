# Blackwell persistent voice candidate v3

Status: **inactive static candidate pending fresh audit and bounded RAM/GPU
owner-hearing acceptance**.

This append-only package implements the v3 state and identity contract without
changing the sealed v2 package or the production voice route.  It has no
playback function, no generic/SAPI route, no CPU synthesis path, and no
internal fallback.  `candidate_config.json` keeps live execution disabled.

The state machine retains one exact approved Chatterbox object and its exact
approved-reference conditionals while moving the owned `t3`, `s3gen`, `ve`,
and condition tensors between CUDA and CPU.  It clears only the documented
derived CUDA resampler/mel/Hann caches.  Mixed devices, identity drift, Qwen
residency, insufficient RAM/VRAM headroom, transfer errors, and cancellation
debt fail closed to `UNLOADED`.

`Core/persistent_blackwell_voice_integration_v3.py` provides the separate,
default-off Qwen load-only/voice serialization boundary.  Load-only requests
have no prompt, messages, person context, chat event, memory event, or SPOKEN
event.  Only `qwen3.5:9b` at the exact sealed digest is allowed.

The static tests use fake tensors and fake Qwen/resource probes.  They do not
load Torch, Chatterbox, Ollama, the GPU, audio playback, camera/microphone,
Blender, or person state.  Passing those tests is not production promotion and
is not owner acceptance.
