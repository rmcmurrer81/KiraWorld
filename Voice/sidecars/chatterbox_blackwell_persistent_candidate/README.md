# Inactive persistent Blackwell Kira voice candidate

Status: `INACTIVE_PRIVATE_CANDIDATE_NOT_PRODUCTION`

This directory contains a bounded persistent eager-CUDA Chatterbox experiment.
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
py -B -m unittest -v Testing.test_blackwell_persistent_voice_candidate
```

The fresh-process checks start only the Python control protocol. They prove
that Torch was not imported, no model was loaded, no WAV was generated, and no
playback occurred. The model-reuse test uses an in-memory fake backend.

## Later bounded GPU acceptance command

Do not run this while Blender or any body render is active. The harness itself
also checks Blender at every GPU boundary and refuses rather than stopping it.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\run_persistent_blackwell_voice_candidate_acceptance.py --run-gpu --confirm-no-active-blender --expected-candidate-config-sha256 54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1
```

The exact candidate-config hash is an operator binding, not a convenience
default. The run also fails closed unless Blender and every Ollama-resident
model are absent; it does not unload or terminate either one.

The harness creates a new append-only `attempt_XX`, generates two non-playing
WAVs using the exact nine-word Attempt 01 sentence, proves one model load and
one reference-conditioning operation, explicitly unloads, verifies allocation
return and clean child exit, and hashes protected files before/after. Even an
engineering pass remains pending an owner-heard acceptance and does not promote
the candidate.

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
this candidate directory, its test file, its acceptance harness, and its
append-only candidate evidence after first preserving their hashes. No
production routing or voice rollback is required.
