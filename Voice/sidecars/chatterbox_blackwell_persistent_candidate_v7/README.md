# Blackwell persistent CPU-park candidate v7

Status: **inactive, static-only, child-owned IPC candidate pending a fresh
independent exact-byte audit**.

V7 is an append-only response to the fresh audit that rejected v6. It does not
modify or replace v2, v3, v4, v5, v6 or their audits, the accepted Blackwell
Attempt 5 environment, the
sealed CPU Chatterbox fallback, Qwen, Kira's approved profile/reference, or
any production route.

## What changed

- A real persistent child process owns the backend, the exact model object,
  conditions, and generation. No callback, closure, Torch object, or model
  object crosses IPC.
- Both JSON directions use strict finite parsing/serialization, reject
  `NaN`/infinities and duplicate keys, and retain exact closed schemas.
- On Windows, the child is created suspended. The parent creates the owned
  kill-on-close Job, assigns the suspended child, queries proof of assignment
  and the 16 GiB aggregate job-memory limit, binds durable process/executable
  identity to the retained process handle, and only then resumes the one
  initial thread. A hostile pre-ready descendant proves there is no startup
  escape window.
- Stdin uses one non-daemon bounded writer. Its native thread is tracked;
  deadline cancellation uses `CancelSynchronousIo`, kills the exact Job, and
  requires the writer thread to exit before returning failure.
- CPU park has exact-worker PID evidence, coherent RAM/commit/VRAM checks, a
  10 GiB parked RSS maximum, and an 8 GiB maximum parked-RSS delta.
- Exact Qwen ownership uses distinct owner/session/token hashes, an immutable
  90-second TTL, an 85-second aggregate stream deadline, 512 chunks, and
  65,536 UTF-8 bytes. Qwen is checked at every state commit and cleanup.
- The parent retains the provisional owned-Qwen token before IPC so a killed
  child can be recovered by an exact fresh-worker cleanup route.
- Every parameter and buffer of `t3`, `s3gen`, and `ve` receives a complete
  content SHA-256 plus immutable metadata. The aggregate component fingerprint
  is included in the model generation and checked before/after transitions and
  synthesis. Model, backend, conditioning, generation, device, worker PID,
  approved prompt, WAV, and CUDA evidence remain mutually bound.
- A verified WAV is retained as immutable bytes in the same worker and handed
  out only by an opaque handle plus exact path, SHA-256, and generation ID.
  Later status checks require the path bytes to remain identical.

## Deliberate limits

- There is **no live adapter** in v7.
- Live execution, production routing, fallback routing, and playback are all
  disabled and unauthorized.
- The only runnable entry is a nonce-bound standard-library static fixture.
- The static fixture never imports or runs Torch, CUDA, Chatterbox, Ollama,
  Qwen, an audio device, person state, or Blender.
- V7 never routes to CPU synthesis, SAPI, a generic voice, a substitute
  reference, or Llama.
- The retained WAV contract says `playback_not_implemented`; no hearing or
  playback claim is made.

## Files

- `candidate_config.json`: exact immutable policy and prior-byte inventories.
- `persistent_worker.py`: child-owned state machine and evidence validation.
- `worker_entry.py`: fail-closed static JSONL entry point.
- `Core/blackwell_v7_process_boundary.py`: real process/job supervisor.
- `Core/persistent_blackwell_voice_integration_v7.py`: parent coordinator.
- `Testing/blackwell_v7_static_fixture_backend.py`: standard-library fake.
- `Testing/test_blackwell_persistent_voice_candidate_v7_hostile_static.py`:
  hostile tests for the v6 blockers plus all inherited reliability boundaries.

## Required next boundary

Seal all exact bytes in the v7 implementation checkpoint, then obtain a fresh
independent hostile static audit. No live RAM/GPU/Qwen/voice/playback or
owner-hearing run is authorized by the authored test suite or this README.
