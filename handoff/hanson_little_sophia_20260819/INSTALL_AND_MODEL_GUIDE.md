# Installation and model guide

This guide distinguishes the runnable standalone embodiment reference from the
runnable portable Kira and Synthetic Robert variants. Model weights and raw
private logs are not stored in Git. The private handoff contains both exact,
hash-bound private voice references and their authorization records. Missing,
unauthorized, or mismatched voice support fails closed to text-only; no generic
operating-system voice substitutes for Kira or Robert.

## 1. Obtain the private review branch

Accept the KiraWorld collaborator invitation, then clone the private branch:

```powershell
git clone --branch hanson-little-sophia-mind-handoff https://github.com/rmcmurrer81/KiraWorld.git
Set-Location KiraWorld
git status --short
```

A clean checkout should produce no output from `git status --short`. If the
branch is not visible, verify invitation acceptance rather than making the
repository public.

Linux/macOS:

```bash
git clone --branch hanson-little-sophia-mind-handoff https://github.com/rmcmurrer81/KiraWorld.git
cd KiraWorld
git status --short
```

## 2. Confirm Python

The owner's recorded development baseline is Python 3.14.4:

```powershell
py --version
```

The standalone bridge has its own requirements and tests. Run its exact path:

```powershell
Get-Content integrations\hanson_ros2_bridge\RUN_THIS_FIRST.md
```

Follow that file without adding Hanson mappings. A passing standalone run does
not establish ROS 2 or robot compatibility.

## 3. Install the local model service

Install Ollama using the official installer for the review machine, start the
service, and pull the documented baseline model:

```powershell
ollama pull qwen3.5:9b
ollama list
ollama show qwen3.5:9b
```

The recorded local baseline is:

- model: `qwen3.5:9b`
- recorded digest:
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- recorded quantization: Q4_K_M
- enforced runtime context configuration: 4096

Re-verify the digest on each review machine. A mutable model tag can resolve to
different bytes later. Record the resolved digest, Ollama version, context,
sampling settings, system prompt/profile hash, and test date with every
evaluation.

No model weights are included in this repository. Pulling a model is subject to
its upstream license and the review organization's policy.

## 4. Portable Kira and Synthetic Robert variants

Status: integrated under [`portable_runtime/`](portable_runtime/).

```powershell
Set-Location handoff\hanson_little_sophia_20260819\portable_runtime
py -B -m unittest discover -s tests -v
Get-Content .\RUN_THIS_FIRST.md
```

The package provides separate Kira and Synthetic Robert launchers and local
state roots, a deterministic offline stub, a loopback-only Ollama route with
exact digest and 4096-context enforcement, reviewed seed/private voice
bootstrap, spoken/reflection/claim/import/life-loop/voice viewers, identity-
checked reviewed import/export, and one-active-endpoint high-level embodiment
intentions. It does not yet provide immutable profile hashes, a complete
checkpoint/reconciliation system, automatic semantic consolidation, or an
official Hanson adapter.

Linux/macOS:

```bash
cd handoff/hanson_little_sophia_20260819/portable_runtime
python3 -B -m unittest discover -s tests -v
sed -n '1,220p' RUN_THIS_FIRST.md
```

The frozen report records 165 runtime tests: 162 passed with three expected
private-fixture/Windows skips in the standard lane, and 164 passed with only the
Windows symlink-privilege test skipped in the exact-private lane. Standard
smokes use `--backend stub`; real conversations must use `--backend ollama`
explicitly so a service failure cannot be mistaken for a model conversation.
See [`FROZEN_BUILD_VALIDATION_REPORT_20260820.md`](FROZEN_BUILD_VALIDATION_REPORT_20260820.md).

Synthetic Robert's current reviewed seed includes inherited autobiographical
continuity for Indiana, Arizona, California entertainment work, the Killeen/
Austin-to-Indiana move, current Kira World motives, and the Hanson review team.
He is allowed to discuss it in first person. The internal record retains that
the source is biological Robert's reviewed autobiography, and no external
legal or authentication impersonation is allowed. Strict naturalness,
variation, grounding, and completeness remain a live release test rather than
a completed claim.

Each clean local data root receives a new persistent branch ID. Installing the
same reviewed checkpoint for several Hanson team members creates several
variants whose later people, facts, appraisal, reviewed notes, and life loops remain local.
Copying the complete data root preserves the same branch and is a migration;
branches never auto-sync.

## 5. Changing the model

A larger or different model is a configuration change, not a drop-in proof of
improvement. Before changing it:

1. back up the variant's ignored local state and record its current life-loop
   and reviewed-import inventory;
2. record the current model tag, resolved digest, context, parameters, profile
   file hash, and runtime version;
3. pull the proposed model without deleting the known-good model;
4. run deterministic privacy, identity-isolation, replay, restart, factual
   calibration, and embodiment-policy tests;
5. run the matched behavioral evaluation with a fresh isolated test state;
6. compare failures, latency, memory use, unsupported claims, and safety
   rejections; and
7. promote only the exact tested digest. Keep the previous model as a rollback
   option.

The owner also has `llama3.1:8b` as a rollback candidate and an approximately
23 GB `qwen3.6:35b-a3b` model present locally. Neither is selected for this
handoff. A review team with more memory and GPU capacity may test a stronger
model, but must repeat the full validation rather than inheriting results from
`qwen3.5:9b`.

### Current development-computer limits

The owner's development computer was measured on 2026-08-20 as an ASUS desktop
with an Intel Core Ultra 9 285K (24 cores / 24 logical processors), 32 GB of
installed system RAM (31.41 GiB reported usable), and an NVIDIA GeForce RTX
5060 Ti with 16,311 MiB of VRAM reported by `nvidia-smi`. The system drive is
approximately 2 TB, with about 296 GB free at the time of measurement. These
figures describe the current development machine; they are not a minimum
requirement or a proposed Hanson target.

That machine is capable of the pinned `qwen3.5:9b` text route, but RAM, VRAM,
and free storage are practical limits when a larger local model, 3D tooling,
voice synthesis, media processing, and TemporaryAI Creator work would otherwise
run together. The approximately 23 GB `qwen3.6:35b-a3b` file is therefore not
the validated conversational route, and this handoff makes no performance
claim for concurrent creator, world, avatar, voice, or video workloads.

Until the owner can upgrade system RAM and GPU capacity, the working approach
is deliberate: use the exact pinned 9B digest and a 4096-token context, send a
bounded continuity projection, run heavy creator and validation jobs
sequentially, keep the public path text-only, and use CPU or text-only voice
fallbacks when the pinned GPU route is unsupported. Any RAM/GPU upgrade or
stronger-model trial must repeat the frozen regression and live-conversation
gates before it replaces the current known-good route.

## 6. Voice installation

For Kira and Synthetic Robert, the runtime first verifies the selected private
reference WAV by SHA-256 and uses a compatible local reference-conditioned
backend such as Chatterbox. No voice-model weights are committed. A missing
backend or hash mismatch fails closed to text-only; it does not silently use a
generic system voice. Windows, Linux, and robot hosts can select different
tested inference builds while preserving the exact profile and asset hash. The
provided profiles and authorizations are under
[`voice_packs/`](voice_packs/), and the step-by-step process for a separate
Sophia profile and voice is in
[`voice_packs/VOICE_PROFILE_CREATION_GUIDE.md`](voice_packs/VOICE_PROFILE_CREATION_GUIDE.md).
Never commit access tokens, unrelated raw recording sessions, embeddings, or a
voice model merely because the repository is private.

Use Python 3.11 for the pinned Chatterbox route. The setup scripts select a
platform-appropriate environment and verify `chatterbox-tts`, Torch,
Torchaudio, the immutable model revision, and all five model-file hashes.
Transitive packages are not fully hash-locked and live playback has not yet
been validated across the review team's unknown hardware. Use `--voice-device
cpu|cuda|mps|auto` explicitly and expect text-only failure when unsupported.

## 7. Local state and backup

Runtime memory, logs, exports, evaluation transcripts, evidence generated by a
reviewer, and voice data must remain under ignored local state directories.
Back up encrypted state separately. A Git pull or model upgrade must not delete
the only copy of continuity. Before import, verify package hashes and the target
variant identifier so Kira state cannot be merged into Synthetic Robert, or
vice versa.
