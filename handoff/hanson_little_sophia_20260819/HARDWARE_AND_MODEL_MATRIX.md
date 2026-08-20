# Hardware and model matrix

This matrix records the known development baseline and separates observations
from recommendations. It is not a benchmark or a guarantee that a model will
fit every context, batch size, quantization, or concurrent workload.

## Owner's current development baseline

| Component | Recorded value | Practical implication |
| --- | --- | --- |
| CPU | Intel Core Ultra 9 285K | Suitable for orchestration, logs, validators, and CPU fallback |
| GPU | NVIDIA RTX 5060 Ti, 16 GB VRAM | Current local 9B quantized-model target; headroom depends on context and other GPU use |
| System memory | 32 GB DDR5-6000, 2 x 16 GB | Run one heavy model/creator workload at a time and retain memory headroom |
| Python | 3.14.4 for portable-runtime/tests; voice backend targets a separate Python 3.11 environment | Reviewers must record both runtime and voice environments |
| Local model service | Ollama | Model weights remain local, outside Git |
| Selected model | `qwen3.5:9b`, Q4_K_M, 4096 context | Current baseline, not a universal optimum |

The owner is saving for more DDR5 memory and a larger GPU. A more capable
review machine may reduce latency, support a longer context, or permit testing
a larger model, but it does not remove privacy, identity, factual-calibration,
or embodiment-safety requirements.

## Workload guidance

| Lane | GPU need | Memory/compute character | Status |
| --- | --- | --- | --- |
| Static Mind V21 review | None | File hashing, schema validation, and audit review | Available |
| Standalone embodiment reference | None | Python tests and mock execution | Available |
| `qwen3.5:9b` local conversation | GPU helpful | Current owner's tested target is a 16 GB GPU with 32 GB RAM | Baseline to re-verify |
| Text-only fail-closed speech route | None | Conversation remains available without silently substituting a generic voice | Implemented policy |
| Reference-conditioned custom voice | Chatterbox-compatible Python 3.11 backend plus exact private reference | May compete with the language model for GPU/VRAM | Exact Kira and Robert references are bundled privately; setup will download the pinned weights and verify their hashes on a supported host; no completed handoff voice environment or live playback is claimed yet |
| Approximately 23 GB `qwen3.6:35b-a3b` | Substantially heavier | May require offload and more system/GPU memory; latency is machine-dependent | Present locally, not selected |
| Simulator plus local model plus voice | Mixed | Multiple real-time workloads can contend for CPU, GPU, RAM, and I/O | Must be profiled on target hardware |

The install must not assume David's team has the owner's RTX 5060 Ti. Hardware
preflight should report the observed OS, CPU, accelerator family, VRAM/RAM,
driver/runtime, and supported Python route. Reviewers may select `cuda`, `mps`,
or `cpu` only after the exact backend works on that host; unsupported voice
continues text-only. A larger older GPU can be faster but may require a
different supported CUDA/PyTorch build. An Apple or CPU-only machine needs a
separately tested route.

## Selecting a stronger model on a review workstation

Prefer measured evidence over parameter count:

1. choose a model whose license permits the intended evaluation and use;
2. reserve enough memory for the simulator, voice, ROS 2, logging, and safe
   shutdown, not only the model weights;
3. pin the exact resolved digest and runtime configuration;
4. evaluate Kira and Synthetic Robert separately with isolated state;
5. compare identity drift, uncertainty handling, false factual claims,
   instruction following, latency, and interruption behavior;
6. stress heartbeat and timeout handling while the model is under load; and
7. keep the tested 9B configuration available for rollback.

Do not increase context, concurrency, or model size immediately before a
physical/simulator test without rerunning the timing and safe-disconnect tests.
Model latency must never extend an embodiment lease implicitly.

## Review record template

Record at least:

- CPU, GPU, VRAM, system RAM, operating system, and storage type;
- Python, Ollama, ROS 2, simulator, and voice-runtime versions;
- model tag, resolved digest, quantization, context, and sampling parameters;
- Kira or Synthetic Robert profile hash and state snapshot identifier;
- average and worst observed response latency;
- peak RAM and VRAM during combined workloads;
- dropped heartbeats, timeouts, policy rejections, and interrupted actions; and
- exact committed handoff and bridge revision.
