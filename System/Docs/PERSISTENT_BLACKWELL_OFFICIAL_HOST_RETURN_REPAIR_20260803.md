# Persistent Blackwell official host-return repair - 2026-08-03

Status: **STATIC/CPU VERIFICATION PASS; CANDIDATE OFF; LIVE GPU GATES PENDING**

## Defect and source-backed correction

The installed, unchanged `chatterbox-tts` 0.1.7 implementation performs its
public return conversion in `ChatterboxTTS.generate()` by moving the generated
waveform to CPU before converting it to NumPy and then returning a new Torch
tensor. Therefore, a correct eager-CUDA synthesis can return a CPU tensor to
the host. Requiring the public output tensor itself to remain on CUDA rejects
the official package's real contract and does not prove where model inference
ran.

The exact installed source remains unchanged:

- `Voice/sidecars/chatterbox_blackwell_gpu/.venv/Lib/site-packages/chatterbox/tts.py`
- SHA-256: `7896787bc17e20eafcd1dce7b8a4a6ea3a6478baab771c60d63e9e81f5564195`
- package: `chatterbox-tts==0.1.7`

The inactive persistent candidate now accepts that official CPU host-return
tensor only after normal signal/WAV validation. It records both truths
explicitly:

- `accepted_output_tensors_host_cpu = true`
- `accepted_output_tensors_cuda = false`

The host-return truth is never counted as eager-CUDA execution evidence.

## Mandatory eager-CUDA proof

The candidate still fails closed unless all applicable proof is present:

1. The model device and the `t3`, `s3gen`, and `ve` modules' parameters and
   buffers are on CUDA.
2. CUDA synchronization succeeds around model preparation and generation.
3. Persistent model allocation is at least 256 MiB.
4. Peak allocated VRAM during each accepted generation attempt is greater
   than that attempt's baseline allocation.
5. No unsupported-architecture, no-kernel-image, or other rejected runtime
   warning occurs.
6. Qwen absence is proven before load and before every generation attempt.
7. The returned host tensor, approved identity/reference bindings, written
   WAV, and audio-signal checks pass.

The worker removes an output promoted before a late proof failure. Retries do
not hide an earlier failed attempt: every generation attempt that contributes
to an accepted result must carry the required proof.

## Scope and production truth

This is an inactive-candidate repair. It did not:

- run the GPU candidate, synthesize or play audio, launch Kira, contact
  Ollama, or start Blender;
- change Torch, Torchaudio, Chatterbox, CUDA, installed model files, or the
  approved Kira profile/reference;
- enable the persistent candidate or change normal production routing;
- change the sealed CPU Chatterbox fallback;
- permit SAPI, a generic voice, or an unsealed fallback.

The 1.5-second conversational target is not claimed. Actual persistent warm
synthesis and owner-heard timing remain live acceptance questions.

## Static verification

Focused candidate/integration tests passed 22/22. The broader relevant
CPU/static regression passed 203/203. Python AST parsing passed for the ten
implementation/test Python files, and JSON parsing passed for the seven
changed/rebound JSON files. The acceptance harness `--describe` path passed.

No result above is a GPU, voice-quality, owner-hearing, or latency pass.

## Next serialized command (not run)

There are four preserved historical candidate attempts. When no Blender,
Ollama, Kira, audio, or other heavy workload is active, the next append-only
run is Attempt 05:

```powershell
py -B tools\run_persistent_blackwell_voice_candidate_acceptance.py --run-gpu --confirm-no-active-blender --expected-candidate-config-sha256 8dd427116d4299c957080702d2838fbb554ed9d785c3c39e1915f212f73da232
```

Only a passing standalone Attempt 05 may unlock the newly rebound two-turn
owner-hearing/Turing configurations. Production promotion still requires the
separate bounded live and owner-heard gates.

## Evidence and rollback

The append-only checkpoint is:

`RecoverySprint/continuation_20260803/persistent_blackwell_official_host_return_repair/attempt_01/CHECKPOINT.md`

Rollback evidence is under that checkpoint's `rollback/` directory:

- `BEFORE_HASHES.json` records exact pre-repair hashes and sizes.
- `candidate_config.before.json` is the complete previous candidate config,
  SHA-256 `54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1`.
- `REVERSE_PATCH.diff` is a verified reversible unified diff for all eleven
  changed source/config/test files.
- `build_reverse_patch.py --verify-only` reconstructs and hashes every prior
  source in memory before emitting the reverse diff.

The reverse patch passed `git apply --check`. Apply it from the project root
only when an explicit rollback is wanted, then compare restored files against
`BEFORE_HASHES.json`. Append-only evidence should remain historical evidence.
