# Blackwell GPU Chatterbox - accepted production-preferred route

This is the additive, isolated Python 3.11.9 production-preferred route for
Kira's reviewed Chatterbox 0.1.7 voice. It uses the matched official stable
PyTorch and Torchaudio 2.11.0 CUDA 13.0 Windows wheels, whose compiled
architecture list includes `sm_120` for the RTX 5060 Ti.

Attempt 5 passed the real standalone eager-CUDA voice acceptance on
2026-08-01. Attempts 1-4 remain append-only diagnosis: Transformers lazy
import, missing Windows `USERNAME`, a false-positive `pwd` import interceptor,
and finally an optional `torch.compile`/Triton limitation on the current
official Windows path. Attempt 5 invoked no `torch.compile`, passed the
restricted eager-CUDA preflight, and generated a valid non-silent WAV with the
exact approved Kira profile/reference on the RTX 5060 Ti. Optional compiled
CUDA support is recorded separately as
`OPTIONAL_NOT_AVAILABLE_ON_CURRENT_WINDOWS_TRITON_PATH`; it is not a failure of
ordinary eager-CUDA inference and no unofficial Triton package was installed.

Serialized attempt 1 subsequently passed the complete exact-Qwen -> unload ->
public `SPOKEN` only -> eager-CUDA voice -> VRAM return -> same-digest Qwen ->
final unload sequence. The accepted CPU sidecar at
`Voice/sidecars/chatterbox_py311` remains unchanged and is the only automatic
approved fallback. SAPI, a generic voice, and an unsealed in-process Kira voice
are never fallback routes.

The worker is one-shot, offline/cache-only, no-playback, public-SPOKEN-only,
and accepts only the hash-sealed approved Kira profile/reference. It requires
the explicit `KIRA_BLACKWELL_VOICE_EXPERIMENT=1` process contract, which the
approved production router supplies only inside its restricted, allowlisted
GPU child environment. It never copies the complete parent environment or
forwards credentials. The controlled cache is under
`RecoverySprint/runtime_cache/blackwell_chatterbox`, has a documented 20 GiB
ceiling, and is never removed automatically. Future owner-approved cleanup may
target only that runtime-cache root; it must never remove Kira's approved
reference or either sidecar's model cache.

Production routing is hash-bound by
`Voice/sidecars/kira_approved_voice_routing.json`. It prefers this one-shot GPU
worker only after Qwen absence is proved, then independently uses the sealed
CPU sidecar if the GPU route is unavailable or fails. Normal exact-Qwen
text-and-voice requests use `think:false` and `keep_alive:0`; the router does
not unload arbitrary models to make room. Results identify every attempted
approved route, the route actually used, any GPU failure reason, and the Qwen
residency proof.

Operator rollback is `KIRA_DISABLE_BLACKWELL_GPU_VOICE=1`. Set it in the Kira
launcher/process environment to skip this GPU route while keeping the sealed
CPU fallback. Clear it to restore the accepted GPU preference. No environment
rebuild is part of rollback.

Authoritative live evidence:

- standalone Attempt 5:
  `RecoverySprint/continuation_20260801/blackwell_chatterbox_acceptance/attempt_05/blackwell_acceptance.json`
  (SHA-256
  `dd0d609dc5405a04dcb0c4e689bbc674c553058bcad9cd93bfaf67a595c841de`);
- serialized Attempt 1:
  `RecoverySprint/continuation_20260801/blackwell_qwen_serialized_acceptance/attempt_01/blackwell_qwen_serialized_acceptance.json`
  (SHA-256
  `0398511192e529e273f1bccca493c68e6e7ebd11d16aba650337fe33d1716e12`);
- serialized WAV SHA-256:
  `e5a3dc4cc108fbc8d243fbe2c1c4c524bd5b1ee4f45efe740502f989d5d96a20`.

The full measurements, all five standalone attempt outcomes, cache policy,
and rollback record are in
`RecoverySprint/continuation_20260801/BLACKWELL_GPU_CHATTERBOX_EXPERIMENT_20260801.md`.

Kira-only legacy entrypoints also converge on this route through
`Core.voice_output.load_kira_production_voice_config()`. This prevents a stale
`KIRA_VOICE_FORCE_SAPI` variable from changing Kira's approved identity while
leaving the shared base config available to unrelated temporary-AI paths. The
full current authority and post-change hashes are recorded in
`System/Docs/KIRA_BLACKWELL_GPU_VOICE_CURRENT_AUTHORITY_20260801.md`.

`requirements.lock.txt` and `evidence/dependency_manifest.json` bind every
installed distribution to installer archive hashes. Chatterbox 0.1.7 declares
Torch/Torchaudio 2.6 pins; only those two metadata conflicts are authorized and
are deliberately superseded by the validated matched 2.11 CUDA 13.0 pair.
