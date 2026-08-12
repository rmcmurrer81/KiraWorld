# Kira Text + Voice latency static analysis — 2026-08-02

## 2026-08-03 bounded repair preparation — newest truth

Status:
`STATIC_REPAIR_VERIFIED_DEFAULT_OFF_PENDING_SERIALIZED_GPU_ACCEPTANCE`.

Latest normal-server Attempt 07 used exact `llama3.1:8b` and the approved
one-shot Blackwell CUDA route for both turns, with no CPU fallback. Text-ready
was `6.295` and `5.501` seconds; cold Ollama model load accounted for about
`2.28` seconds per turn. One-shot Chatterbox synthesis was `20.894460` and
`14.215141` seconds. Queue/cleanup/voice handoff remained milliseconds. The
dominant current latency is therefore cold one-shot voice lifecycle; Llama
cold load is secondary.

The formerly prepared full-load diagnostic has now passed in `11.346943`
seconds: imports `4.0934293`, `from_pretrained` `4.5521123`, approved-reference
conditioning `1.3303728`, and cleanup `0.1388647` seconds. Original persistent
Attempt 03 is separately preserved as a `939.012301`-second `client.load()`
timeout.

The smallest evidence-supported differential was repaired only in the
inactive candidate: background host-RAM sampling remains, but external
`nvidia-smi` is now invoked only at operation boundaries instead of every 250
ms during CUDA load. Torch allocator/output-tensor evidence remains the actual
CUDA proof. The owner-hearing harness likewise uses named-boundary GPU
snapshots only.

No GPU, synthesis, playback, conversation, browser, camera, or microphone ran
for this static repair. `169` CPU-only/fake-backend tests pass. Production
routing remains one-shot Blackwell preferred with sealed CPU as its sole
automatic fallback. A new standalone persistent two-WAV acceptance must pass
before the exact prepared two-turn owner-hearing run may execute.

Current evidence and exact hashes:
`RecoverySprint/continuation_20260803/kira_text_voice_latency_bounded_repair_preparation/`.

The original 2026-08-02 analysis below remains historical context.

Status: diagnostic note only. Production remains on the accepted one-shot
Blackwell eager-CUDA route, with sealed CPU Chatterbox as its only automatic
fallback. SAPI, generic voice, unsealed voice, and arbitrary model unloading
remain forbidden. The approved Kira profile and reference remain unchanged.

The nine-word live turn spent `20.6367773` seconds in the parent-visible voice
synthesis call. Its worker reported `17.899` seconds internally, leaving
`2.7377773` seconds of aggregate parent/child boundary overhead. Attempt 01 did
not record finer worker phases or generation retry count, so no exact split
between imports, model load, CUDA transfer, approved-reference conditioning,
generation, WAV work, and cleanup is supported.

A later isolated `pre_cuda` phase diagnostic provides comparison evidence:
named phases totaled `8.0266503` seconds, including `8.0042399` seconds of
imports (Torch `2.4467018`, Transformers compatibility `4.1403313`, Perth
`1.0727397`, Chatterbox class `0.2850603`). This strongly supports eliminating
per-turn cold imports through a separately sealed persistent worker, but it is
not a retroactive subtraction from the original turn.

The safest next runtime action is the already-prepared `full_load` diagnostic,
which phase-times the exact offline weight load, CUDA transfer, approved Kira
reference conditioning, and cleanup without synthesis or playback. The
persistent candidate must remain default-off and unpromoted until that passes,
then passes a no-playback phase-timed synthesis and the existing supervised
two-turn owner-heard acceptance.

Detailed evidence bindings and recommendations are preserved in:

`RecoverySprint/continuation_20260802/voice_latency_static_analysis_preparation/REPORT.md`
