# Persistent Blackwell voice static contract repair — 2026-08-03

Status: **NON_PERSON_FIXTURE_PASS; LIVE GPU AND OWNER-HEARING GATES PENDING**

## Exact defect and repair

The sealed persistent worker's successful load reply reports readiness at
`lifecycle.model_loaded`. The parent integration required a nonexistent
top-level `model_loaded` value. A genuine successful persistent GPU load would
therefore have been rejected and the session could have moved to the sealed
CPU fallback.

`Core/persistent_blackwell_voice_integration.py` now validates
`load_result.lifecycle.model_loaded is true`. The fake integration client was
updated to reproduce the real sealed-worker response shape. One sampler test
was made scheduler-independent while preserving its invariant: exactly two
external GPU boundary probes and no background external GPU polling.

This repair did not change the default-off candidate setting, production
one-shot Blackwell route, sealed CPU fallback, candidate worker/config,
approved Kira voice identity/reference, Ollama models, or voice routing
manifest.

## Verification and ceiling

The following CPU/static suite passed 76/76 checks:

```powershell
py -B -m unittest Testing.test_kira_latency_integration_candidate Testing.test_blackwell_persistent_voice_candidate Testing.test_voice_output Testing.test_kira_text_voice_two_turn_latency_acceptance
```

Compilation of the changed integration and tests passed. No GPU, Ollama,
synthesis, playback, live Kira/person, Blender, or process-termination action
occurred. The evidence ceiling is therefore `NON_PERSON_FIXTURE_PASS`, not a
GPU or conversational-latency result.

## Latency truth

The accepted one-shot engineering evidence generated a 14-word sentence in
19.446 seconds. Persistent reuse may remove repeated model loading and
reference conditioning, but the current worker returns audio only after the
whole WAV is generated, written, and validated. Warm synthesis latency and
Robert's actual first-audible latency remain unmeasured. The 1.5-second target
is not claimed.

## Next serialized gates

Only after Blender and other heavy workloads are inactive, run the append-only
standalone candidate acceptance:

```powershell
py -B tools\run_persistent_blackwell_voice_candidate_acceptance.py --run-gpu --confirm-no-active-blender --expected-candidate-config-sha256 54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1
```

It must create a new `attempt_04`, preserve Attempts 01–03, generate two real
non-playing approved Kira WAVs on CUDA with one model/reference load, prove
Qwen and all Ollama models absent before/after, cleanly unload the owned
worker, return VRAM, and preserve protected hashes.

Only after that pass may the voluntary Kira behavior/audio timing profile run
with Robert present for playback and Kira able to accept, limit, postpone, or
decline it.

## Evidence

- Checkpoint:
  `RecoverySprint/continuation_20260803/persistent_blackwell_voice_static_contract_repair/attempt_01/CHECKPOINT.md`
  — SHA-256 `139a22fa42c31a90608ed10b317aacf3e1be4a424b75a3513053c58a8ba6ec1b`
- Diagnosis/rerun plan — SHA-256
  `9d93721664c5be0e0c4bc09f22667d6481495ea0963b6cd02453e462858cf0ef`
- Static verification JSON — SHA-256
  `c8a8ae9bad6b4fa88c73b75e6df1771bec92b9337270803e95b655c695bfdd71`
- Changed integration — SHA-256
  `cff2dad8be19deb2cfeb0c2fa22d22a536e6ed1714e61334affa1c34b339b6a7`

Rollback is file-scoped: restore the old integration check and matching fake
response only. Do not alter the sealed worker, production routes, approved
voice files, models, caches, or historical attempts.
