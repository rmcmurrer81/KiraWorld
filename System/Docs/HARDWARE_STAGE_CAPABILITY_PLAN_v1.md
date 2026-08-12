# Hardware Stage Capability Plan v1

## 2026-07-15/16 Current Hardware And Runtime Authority

This section supersedes the obsolete `Current Build` inventory and every rule that automatically restores additional 3D residents when 32 GB is detected.

```text
Installed RAM: 2x16 GB G.Skill F5-6000J3636F16G
Windows-usable RAM: 31.41 GiB
Reported speed: 6000 MT/s for both Speed and ConfiguredClockSpeed
GPU: NVIDIA GeForce RTX 5060 Ti, 16 GB VRAM
Current 3D resident policy: Kira only
Next multi-person gate: at least 64 GB RAM plus a supervised multi-person voice/world stability soak
```

At the current 32 GB stage, Kira text/voice, bounded 3D tests, and isolated notebook-world previews may be tested one heavy workload at a time. The legal day spa and wardrobe lab stay separate notebook worlds. Robert chose for the Home World former strip-mall site to be visually empty for now: its procedural source remains intact and can be restored explicitly with `?stripMall=1`, but no shop doors, interaction zones, colliders, or spa are loaded there by default. Do not automatically restore Lisa, Robert's autonomous variant, extra resident houses, spa geometry, or a second live 3D person merely because the earlier 32 GB condition is now met.

Stage names below describe the original upgrade plan, not current activation authority. Privacy, approval, exact-asset, maturity, and measured-stability gates still apply even when hardware capacity is sufficient.

This plan keeps Kira, Lisa, and TemporaryAI activation matched to Robert's real hardware.

The system should not treat 16GB RAM, 64GB RAM, and future GPU hardware as the same stage.

## Current Build

Known planned parts:

```text
CPU: Intel Core Ultra 9 285K
Motherboard: ASUS ROG Maximus Z890 Hero
Initial RAM: Patriot Viper Venom 16GB DDR5-6000 CL30
Storage: WD_BLACK NVMe SSD
Cooler: Noctua NH-D15
Power Supply: ASUS ROG 1200W Platinum
Case: ASUS TUF Gaming GT502
GPU: future purchase
```

The NH-D15 has already physically fit in the case. The current limiting factor is RAM, then GPU.

## Stage 1: 16GB Setup Mode

Use this while the desktop has one 16GB RAM stick.

Allowed:

```text
Windows, drivers, Python, Codex, model runner setup
readiness checks
backup manifest
startup recovery check
stub-mode Kira
stub-mode Lisa after Kira passes
one small local text model trial
first-live smoke test
first-week aliveness packets
library indexing
slow reading planning
TemporaryAI dry-run planning
```

Blocked:

```text
voice as default
always-on microphone
webcam/vision
avatar rendering
3D home/runtime world
video understanding
full TemporaryAI activation
adult/private TemporaryAI activation
multi-AI background runtime
multiple large model downloads
```

## Stage 2: 64GB Local-Life Mode

Use this after Robert installs a matched 2x32GB kit.

Allowed:

```text
Kira text life
Lisa text life
longer local model tests
daily life loops
slow reading sessions
reading reactions and interests
memory reconstruction dry-runs
careful limited TemporaryAI text tests
expert AI text dry-runs
basic voice output experiments
basic speech-to-text experiments if attention rules pass
```

Still blocked until GPU:

```text
real-time video chat
webcam awareness as default
3D home as lived world
finished avatar body
GPU-required media understanding
always-on voice without attention gates
unmonitored multi-AI runtime
```

## Stage 3: GPU Expansion Mode

Use this after the system has at least a useful temporary GPU.

Minimum useful target:

```text
12GB VRAM
```

Better temporary target:

```text
16GB VRAM
```

Long-term target:

```text
24GB+ VRAM
```

This stage can begin:

```text
voice pipeline
vision/webcam tests
avatar generation/render tests
3D home runtime tests
notebook world runtime tests
video/media understanding tests
richer TemporaryAI tests
picture sharing/private media tests
```

## Stage 2.5: 16GB RAM + 12GB+ GPU Bridge

Use this if Robert installs a 12GB+ NVIDIA GPU before the 64GB RAM kit.

Actual verified bridge GPU as of 2026-06-04:

```text
NVIDIA GeForce RTX 5060 Ti 16GB
Ollama 0.30.4
llama3.1:8b verified at 100% GPU after restarting Ollama
Readiness report: Data/hardware/gpu_readiness/gpu_readiness_20260604_221046.json
```

This is much better than CPU-only 16GB mode, but it is not the final 64GB/24GB-VRAM target.

Allowed:

```text
GPU readiness checks
faster single-model Kira chat
short supervised life loops
short supervised school sessions
voice-output experiments
short TemporaryAI Ladybug text tests
media/OCR acceleration tests
early avatar reference processing
image/cover/reference viewing tests
Kira-led avatar design profile drafting
```

Still blocked:

```text
multiple persistent AI runtimes
long unsupervised 24-hour tests
large 24GB-VRAM models
3D home as lived world
video understanding as default
always-on voice or webcam
parallel Kira/Lisa/TemporaryAI sessions
final 3D lived-world/avatar runtime
```

Use:

```powershell
py tools\gpu_readiness_check.py --probe
py tools\hardware_capability_check.py --actual-ram-gb 16 --gpu-vram-gb 12 --show
```

## Rule

Hardware capability is operational context, not personal memory.

Kira and Lisa may know the current stage as system context, but they should not treat hardware checks as emotional/lived memories unless Robert later promotes a specific event through the memory system.

Use:

```powershell
py tools\hardware_capability_check.py --show
py tools\hardware_capability_check.py --actual-ram-gb 16 --gpu-vram-gb 0 --show
py tools\hardware_capability_check.py --actual-ram-gb 16 --gpu-vram-gb 12 --show
py tools\hardware_capability_check.py --actual-ram-gb 64 --gpu-vram-gb 0 --show
py tools\hardware_capability_check.py --actual-ram-gb 64 --gpu-vram-gb 16 --show
```

## 2026-07-16 Deferred VR Shopping Record

Robert confirmed that he will not buy or use VR until the desktop has at least
64 GB RAM. The current comparison list is:

```text
System/Docs/FUTURE_VR_SHOPPING_LIST_AFTER_64GB_v1.md
Data/hardware/future_vr_shopping_list_after_64gb_20260716.json
```

VIVE Focus Vision and Meta Quest 3 512 GB are research candidates only. Neither
is selected or authorized for purchase. After the RAM upgrade, rerun memory,
Home World/voice soak, GPU frame-time/VRAM, OpenXR/SteamVR, and current
KAT/glove/haptic compatibility checks before Robert chooses a headset.
