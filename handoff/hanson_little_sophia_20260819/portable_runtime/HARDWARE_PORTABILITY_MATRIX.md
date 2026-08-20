# Hardware and model portability matrix

These are planning envelopes, not performance guarantees. Run the included verification/evaluation on each target machine before calling a route ready.

| Route | Minimum practical starting point | Preferred | What changes on stronger hardware | Current validation boundary |
|---|---|---|---|---|
| Deterministic stub + storage/tests | Python 3.11, 4 GB RAM, <1 GB free disk | Any current x64/ARM64 computer | Little benefit; this route is for deterministic checks | Fully exercised by the unit suite; not the conversational LLM |
| Ollama `qwen3.5:9b` text | Roughly 12–16 GB available RAM if CPU/offload is needed; model occupies about 6.6 GB locally | 16 GB VRAM and 32 GB system RAM or better | More GPU memory can keep more layers/context on GPU and improve latency | Exact tag must report digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`; measure target-machine throughput |
| Larger Ollama model | Depends on quantization; often >24 GB combined available memory | 24–48+ GB VRAM and 64+ GB RAM | A stronger model may improve reasoning/calibration but must use matched regression tests | No larger model is selected by this package; identity does not change merely because the model changes |
| Pinned Chatterbox 0.1.7 CPU | Python 3.11, several GB free disk for exact weights, substantial free RAM | Modern high-clock CPU, 32 GB RAM | Faster CPU reduces synthesis delay | Interface/model hashes verified; no live synthesis/listening acceptance was performed in this delivery run; use `--voice-device cpu` |
| Pinned Chatterbox CUDA | Python 3.11 and a PyTorch 2.6-compatible NVIDIA GPU | Supported NVIDIA GPU with enough VRAM and a matched CUDA/PyTorch build | GPU can reduce synthesis latency | The builder’s newer GPU architecture is not supported by the pinned Torch/CUDA route, so force CPU unless the target is independently validated; select with `--voice-device cuda` only when supported |
| Apple Silicon neural voice | Python 3.11, supported PyTorch/MPS stack | Recent M-series Mac with ample unified memory | MPS may accelerate synthesis | Best-effort interface only; not validated here |
| Append-only continuity | Tens of MB initially | SSD with backups and monitored growth | More storage permits longer local history | JSONL grows without automatic compaction; back up and apply retention policy |
| Private voice packs | ~12 MB for the two current references plus generated/cache data | Encrypted/private SSD | More storage does not expand consent scope | Private named-review-team use only; Kira speaker purity remains pending human review |
| High-level embodiment | Text/state runtime only; no hardware driver requirement | Separate simulator/safety bridge machine | Stronger body computer may host a complete software deployment copy | This package emits non-executing speech/gaze/expression/gesture intentions only; it has no motor/joint control |

## Python selection

Install Python 3.11 before setting up the combined text + Chatterbox route. The current host’s registered `py` launcher exposed Python 3.14, so the delivery does not claim a locally completed 3.11 neural-voice environment. Windows launchers prefer `.venv-voice\Scripts\python.exe`, then `py -3.11`. Linux/macOS launchers prefer `.venv-voice/bin/python`, then `python3.11`.

The global Python can run standard-library text tests, but that does not prove Chatterbox compatibility. `--voice-device auto` chooses CUDA when Torch reports it available; use the explicit `cpu`, `cuda`, or `mps` override when automatic selection is unsuitable.

## Disk planning

- Ollama `qwen3.5:9b`: approximately 6.6 GB in the current local installation.
- Pinned Chatterbox files: several GB; the two largest files are roughly 1.06 GB and 2.13 GB.
- Voice references: Kira and Robert private handoff assets are small relative to model weights.
- `local_data`: unbounded append-only growth unless the operator archives reviewed exports and applies a local retention plan.

Do not place private references, logs, or generated audio in a public repository to save local disk space.

## Switching to more capable hardware

1. Copy code and an explicitly reviewed continuity export/seed—not the entire raw `local_data` directory.
2. Install the exact model tag and record its full digest.
3. Install Python 3.11. The direct Chatterbox wheel and five model files are hash-pinned; transitive/platform dependencies are not fully hash-locked, although Chatterbox/Torch/Torchaudio versions are checked at runtime.
4. Run `voice-env-check` before synthesis.
5. Bootstrap only the private, authorized packs for the named team.
6. Run unit tests and a fresh isolated behavioral evaluation.
7. Compare results with the prior machine before promoting the route.

A copied deployment can host the same software profile and reviewed continuity, but this is software/state migration, not literal consciousness transfer or proof of life.
