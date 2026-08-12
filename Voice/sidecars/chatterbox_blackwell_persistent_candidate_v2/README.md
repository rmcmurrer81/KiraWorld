# Inactive persistent Blackwell Kira voice candidate v2

Status: `INACTIVE_PRIVATE_CANDIDATE_NOT_PRODUCTION`

This append-only directory contains the request-gated revision of the bounded
persistent eager-CUDA Chatterbox experiment. The v1 directory and Attempts
01-06 remain the preserved source and evidence for the reproduced Windows
inherited-stdin/Torch-import stall.
It is not referenced by `Core/voice_output.py` or by
`Voice/sidecars/kira_approved_voice_routing.json`. The accepted production
preference remains the one-shot `blackwell_gpu` route, and the unchanged sealed
CPU Chatterbox sidecar remains its only automatic fallback. This candidate has
no fallback code and cannot invoke SAPI or a generic voice.

## Why this candidate exists

The accepted one-shot worker loads Chatterbox and recomputes Kira's approved
reference conditioning for every reply. This host instead proposes:

1. start one private inherited-pipe process in an unloaded state;
2. prove Qwen absent;
3. load the exact existing Blackwell environment once;
4. hash the exact approved Kira profile/reference again;
5. call `prepare_conditionals()` once;
6. make multiple bounded `model.generate(text)` calls without an
   `audio_prompt_path`, reusing the approved conditionals;
7. explicitly unload and measure Torch allocation release;
8. close only the exact child process owned by the client.

No file in the approved Blackwell or CPU sidecar directories is modified.

## Fail-closed boundaries

- Importing the contract, controller, or worker does not import Torch,
  Chatterbox, NumPy, SoundFile, or an audio device.
- The controller defaults to `allow_gpu_model_load=False`.
- A GPU load requires both the controller opt-in and a separate restricted
  child-environment value.
- The child receives an explicit allowlist of Windows environment values, not
  a copy of the parent environment.
- Transport is inherited stdin/stdout only and every request requires the
  per-process random nonce and a non-replayed UUID.
- The reader queues one request and then waits. It cannot begin another
  inherited-pipe `readline` until the main thread has written and flushed that
  request's final response. Terminal paths stop and release the parked reader
  without authorizing another read.
- Only `public_spoken_only` is accepted. Private/factual channel markers,
  oversized text, path escapes, overwrites, playback requests, and fallback
  requests fail closed.
- Worker, client, contract, interpreter, dependency evidence, installed
  Chatterbox source, dialogue helpers, production routing, sealed CPU worker,
  profile, and reference are hash-bound.
- Qwen absence is proved without changing model state before model loading and
  immediately before every bounded generation attempt.
- At most 64 transport requests, 32 chunks per synthesis, and three generation
  attempts per chunk are allowed. The model unloads after 600 idle seconds and
  the process ends after 3,600 seconds.
- Playback is always outside the worker. This candidate never opens an audio
  output device.

## Phase telemetry

Load evidence separates restricted-environment validation, runtime package
metadata, identity hashing, Qwen residency, each heavy import, CUDA contract,
CUDA preparation, `from_pretrained`, `prepare_conditionals`, synchronization,
warnings, Torch allocation, process RAM, system RAM, and total VRAM sampling.

Each synthesis separates identity/environment checks, chunking, per-attempt
Qwen checks, model generation, CUDA-to-host transfer, signal validation, PCM
postprocessing, partial WAV writing, partial validation, atomic promotion,
final validation/hash, resource peaks, and complete lifecycle counters.

Unload evidence separates Python object/GC release from CUDA cache release and
records allocated/reserved bytes before, after, and returned.

## No-model verification

This is safe to run while the candidate remains inactive:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest -v Testing.test_blackwell_persistent_voice_candidate_v2
```

The fresh-process checks start only the Python control protocol. They prove
that Torch was not imported, no model was loaded, no WAV was generated, and no
playback occurred. Host-only fakes prove the reader gate, response-flush order,
malformed/wrong-nonce recovery, EOF, shutdown, and request-limit behavior.

## Required next bounded import-only proof

No v2 Torch/GPU acceptance command is authorized by this implementation step.
Do not point the v1 acceptance harness at v2. The next proof must use a new
append-only, independently reviewed harness bound to the exact v2 config and
source hashes. It must send one load-shaped request through the real inherited
pipe, prove the reader is parked at its request-completion gate, import only
Torch under a 120-second child hard bound, and report prohibited CUDA/model/
audio/routing outcomes as `UNKNOWN` unless directly observed. Only a passing
import-only proof may authorize a later, separately bounded inactive GPU/model
acceptance. Neither proof promotes this candidate.

## Cache management

Controlled compiler/temp cache root:

`RecoverySprint/runtime_cache/blackwell_chatterbox_persistent_candidate`

The acceptance records its size before and after. No cache is deleted
automatically. Treat 10 GiB as the documented review threshold: if the root
exceeds that size, stop and ask Robert before any cleanup. Cleanup must target
only that exact resolved candidate cache root. It must never touch Kira's
approved reference, the Hugging Face model cache, the accepted Blackwell
environment, or the sealed CPU environment.

## Rollback

Because the candidate is disconnected, rollback consists only of withdrawing
this v2 directory, its focused test file, and any future append-only v2 evidence
after first preserving their hashes. The v1 directory and Attempts 01-06 must
remain untouched. No production routing or voice rollback is required.
