# Kira Blackwell GPU Voice Current Authority — 2026-08-01

## Current production decision

Blackwell Chatterbox Attempt 5 is accepted and current. Normal Kira Text +
Voice production prefers the approved RTX 5060 Ti eager-CUDA sidecar. The
unchanged sealed CPU Chatterbox sidecar is the only automatic fallback.
Windows SAPI, a generic voice, and an unsealed in-process Kira voice are not
fallback routes.

The route order and identity bindings are fail-closed in
`Voice/sidecars/kira_approved_voice_routing.json` (SHA-256
`a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`):

1. `blackwell_gpu` — preferred, CUDA, exact approved profile/reference;
2. `sealed_cpu` — automatic approved fallback only, CPU with CUDA hidden.

GPU synthesis requires a read-only proof that promoted Qwen is absent. The
router does not unload arbitrary models. If Qwen absence cannot be proven, the
GPU route is skipped and the sealed CPU route is tried independently. Every
result identifies the attempted and actual approved route and records the GPU
failure reason. No route is permitted to substitute SAPI or a generic voice.

## Accepted evidence

Standalone Attempt 5 is `PASS`:

- report:
  `RecoverySprint/continuation_20260801/blackwell_chatterbox_acceptance/attempt_05/blackwell_acceptance.json`;
- report SHA-256:
  `dd0d609dc5405a04dcb0c4e689bbc674c553058bcad9cd93bfaf67a595c841de`;
- generated WAV SHA-256:
  `0f470a6651f78fd02bf12d10c5efc99699142a89923b60139187397299b34ce0`;
- approved profile SHA-256:
  `102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116`;
- approved reference SHA-256:
  `2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c`;
- device: NVIDIA GeForce RTX 5060 Ti, capability 12.0, `sm_120` present;
- Torch/Torchaudio: `2.11.0+cu130`; CUDA runtime: 13.0;
- eager CUDA generation: 19.446 seconds; worker wall time: 25.97 seconds;
- peak measured GPU use: 5,402 MiB total, 3,803 MiB above baseline;
- peak process RSS: 5,003 MiB; peak system RAM used: 18,490.9 MiB;
- WAV: mono 24 kHz, 16-bit, 4.36 seconds, readable and non-silent;
- worker exit code: 0; GPU process absent after exit; VRAM return passed;
- Qwen absent before and after synthesis;
- CPU sidecar and protected-file integrity passed.

Optional `torch.compile`/Triton acceleration remains
`OPTIONAL_NOT_AVAILABLE_ON_CURRENT_WINDOWS_TRITON_PATH`. It is not required by
ordinary eager-CUDA Chatterbox inference and was not invoked by Attempt 5.

The serialized exact-Qwen -> unload -> public SPOKEN -> GPU voice -> unload ->
same-digest Qwen sequence is also `PASS`:

- report:
  `RecoverySprint/continuation_20260801/blackwell_qwen_serialized_acceptance/attempt_01/blackwell_qwen_serialized_acceptance.json`;
- SHA-256:
  `0398511192e529e273f1bccca493c68e6e7ebd11d16aba650337fe33d1716e12`.

Attempts 1 through 5 remain append-only. A read-only post-change audit found 26
files across those five folders with aggregate manifest SHA-256
`205b1b8975ae379b71e9cc0c6843b55f01c05d4767bf14a3237a1fc41568dc51`.
No synthesis was rerun for this routing correction.

## Kira-only entrypoint correction

`Core.voice_output.load_kira_production_voice_config()` now applies Kira's
exact approved identity route after reading the historical base config. This
keeps base operator controls such as enabled/dry-run/playback while preventing
a stale `KIRA_VOICE_FORCE_SAPI` value from converting Kira into a SAPI voice.
The hash-bound router still performs the final artifact and evidence checks and
fails closed if they do not pass.

The following Kira-only entrypoints use that production loader:

- `voice_kira.py` / `Start_Kira_Voice_Chat.bat`;
- `tools/kira_chat_control_center.py`;
- the optional Kira-to-Robert voice path in `tools/run_kira_life_day.py`.

The normal `Start_Kira_Text_Voice_Chat.bat` path already resolves Kira through
the candidate voice profile in `tools/kira_world_shell_server.py`; it reaches
the same GPU-first router. The shared historical
`Voice/kira_voice_output_config.json` remains a base configuration so unrelated
temporary-AI voice behavior is not silently changed.

Post-change hashes:

- `Core/voice_output.py`:
  `50f5c7bdbc3e2c1f0667d7da3de2eb4e9553a1b69dc21a29e9129576a6f42caa`;
- `voice_kira.py`:
  `5ba3b1a76168a2e8e4cffebecc8509d25daaef7476a1486cc98007a61ad85934`;
- `tools/kira_chat_control_center.py`:
  `1c8f4036bb52282f43f0005216151e31b55d16ee2073284ce4717319d18e6aa4`;
- `tools/run_kira_life_day.py`:
  `125bcb7b91e185ffcfdf6fa9dde2a2b23f305321fa48aab248cda4e977d42263`;
- `Testing/test_voice_output.py`:
  `c64a216d9443fe730384796e9b782f13c985926999aeacc2dfe35b0f91f5484b`.

Focused non-synthesis regression passed 68/68:

```text
py -m unittest Testing.test_voice_output Testing.test_chatterbox_py311_sidecar Testing.test_blackwell_qwen_serialized_acceptance Testing.test_qwen_text_voice_acceptance
```

## Rollback and cache policy

The reversible GPU-route rollback is
`KIRA_DISABLE_BLACKWELL_GPU_VOICE=1`. This skips only the preferred GPU route
and retains the sealed CPU sidecar as the approved fallback. Clear the variable
to restore GPU preference. Do not rebuild either environment.

Controlled runtime cache root:
`RecoverySprint/runtime_cache/blackwell_chatterbox`. The read-only post-change
audit found 16 files totaling 41,243 bytes (0.039332 MiB). Inspect it again
with:

```powershell
Get-ChildItem -LiteralPath 'RecoverySprint\runtime_cache\blackwell_chatterbox' -Recurse -File | Measure-Object -Property Length -Sum
```

Cache cleanup is owner-invoked only. Never remove the approved reference WAV or
either model cache as part of runtime-cache cleanup.
