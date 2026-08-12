# Blackwell persistent CPU-park candidate v6

Status: **inactive, static-only, child-owned IPC candidate pending a fresh
independent exact-byte audit**.

V6 is an append-only response to the rejected v5 design. It does not modify
or replace v2, v3, v4, v5, the accepted Blackwell Attempt 5 environment, the
sealed CPU Chatterbox fallback, Qwen, Kira's approved profile/reference, or
any production route.

## What changed

- A real persistent child process owns the backend, the exact model object,
  conditions, and generation. No callback, closure, Torch object, or model
  object crosses IPC.
- The parent uses finite JSONL messages, an exact creation-token digest,
  response identity checks, one bounded operation lock, and hard aggregate
  command deadlines.
- On Windows, the parent places the worker and descendants in an owned Job
  Object with kill-on-close and a 16 GiB aggregate job-memory ceiling. A
  timeout kills the job rather than leaving an unbounded Python thread.
- CPU park has exact-worker PID evidence, coherent RAM/commit/VRAM checks, a
  10 GiB parked RSS maximum, and an 8 GiB maximum parked-RSS delta.
- Exact Qwen ownership uses distinct owner/session/token hashes, an immutable
  90-second TTL, an 85-second aggregate stream deadline, 512 chunks, and
  65,536 UTF-8 bytes. Qwen is checked at every state commit and cleanup.
- The parent retains the provisional owned-Qwen token before IPC so a killed
  child can be recovered by an exact fresh-worker cleanup route.
- Model, backend, conditioning, generation, device, worker PID, approved
  prompt, WAV, and CUDA evidence are mutually bound. Mixed-device or replaced
  objects fail closed.
- A verified WAV is retained as immutable bytes in the same worker and handed
  out only by an opaque handle plus exact path, SHA-256, and generation ID.
  Later status checks require the path bytes to remain identical.

## Deliberate limits

- There is **no live adapter** in v6.
- Live execution, production routing, fallback routing, and playback are all
  disabled and unauthorized.
- The only runnable entry is a nonce-bound standard-library static fixture.
- The static fixture never imports or runs Torch, CUDA, Chatterbox, Ollama,
  Qwen, an audio device, person state, or Blender.
- V6 never routes to CPU synthesis, SAPI, a generic voice, a substitute
  reference, or Llama.
- The retained WAV contract says `playback_not_implemented`; no hearing or
  playback claim is made.

## Files

- `candidate_config.json`: exact immutable policy and prior-byte inventories.
- `persistent_worker.py`: child-owned state machine and evidence validation.
- `worker_entry.py`: fail-closed static JSONL entry point.
- `Core/blackwell_v6_process_boundary.py`: real process/job supervisor.
- `Core/persistent_blackwell_voice_integration_v6.py`: parent coordinator.
- `Testing/blackwell_v6_static_fixture_backend.py`: standard-library fake.
- `Testing/test_blackwell_persistent_voice_candidate_v6_hostile_static.py`:
  hostile tests for every reproduced v5 blocker and variations.

## Required next boundary

Seal all exact bytes in the v6 implementation checkpoint, then obtain a fresh
independent hostile static audit. No live RAM/GPU/Qwen/voice/playback or
owner-hearing run is authorized by the authored test suite or this README.
