# Kira camera-to-text-to-voice latency static finding

Date: 2026-08-11  
Status: current scoped engineering finding; runtime cause remains unmeasured  
Authority: test-design and append-only repair input only

## What the current route actually does

Camera ON by itself starts a 640x360 preview and a low-rate sample every 5,000
milliseconds. Each sample is drawn to a canvas, encoded as JPEG at quality
0.72, and sent to the loopback visual sidecar. That sidecar derives only
bounded CPU-local cues such as frame size, brightness, coarse face count, and
motion. The low-rate path does not call Qwen vision.

The explicit `Look Now` path is materially different. It uses the same still
for both the bounded local cue reducer and `/api/sensory/qwen-look`. The server
then holds the chat-reply and voice-output locks for the complete transient
Qwen vision load, inference, and unload sequence. The vision bridge requires
empty Ollama residency and requests `keep_alive=0`.

Normal Text + Voice generation separately requires the exact Qwen 3.5 9B
model and also forces `keep_alive=0` so Qwen is absent before Blackwell voice
may use the GPU. Therefore the current explicit camera-question sequence can
be:

1. capture and JPEG encode;
2. load Qwen for vision;
3. run vision inference;
4. unload Qwen;
5. wait for the chat lock;
6. load Qwen again for the text reply;
7. generate and unload Qwen again;
8. load or reuse the approved Blackwell voice route and synthesize audio.

This serial double Qwen load/inference boundary is a strong static explanation
for Robert's observed larger delay when he asks what Kira sees. It is not yet
a measured causal verdict.

## Required matched evaluation

The future bounded evaluator must counterbalance at least four matched pairs:

- camera OFF, ordinary conversation;
- camera ON with preview/low-rate CPU cues only;
- camera ON plus one explicit `Look Now` still and sensory question;
- camera ON plus a follow-up turn after the one-still cue is consumed.

Every trial must record exact monotonic timestamps for camera start, preview
ready, frame capture, draw, JPEG completion, upload, local cue completion,
vision lock wait, vision model load/start/first output/complete/unload, chat
lock wait, text model load/first token/complete/unload, displayed text, voice
queue entry, voice model ready, synthesis completion, playback onset, and
playback completion. It must also record prompt bytes, response length, queue
depth, Qwen residency, GPU/VRAM state, CPU utilization, and whether a prior
voice job or frame was in flight.

Camera OFF/ON pairs must use the same prompt family, state, history size,
generation limits, and voice route. The test must separately evaluate normal
turn-taking, two consecutive remarks without waiting, interruption/barge-in,
and unclear/partial interruption. No cue may force speech, consent, action, or
memory.

## Candidate optimization boundary

The highest-value candidate is one bounded multimodal Qwen request that
combines the current still and Robert's sensory question into the same normal
conversation generation, then unloads Qwen once before voice. This could
remove one complete load/inference/unload cycle while retaining a single
public response and the existing Qwen-absence-before-voice rule.

Secondary candidates are pausing low-rate capture while chat or voice is
active, measuring a smaller still resolution only if scene adequacy remains
proven, and moving JPEG encoding off the UI thread. None is authorized for the
live route by this document. Each requires append-only implementation, static
tests, a different review, matched live evidence, and rollback.

## Truth boundary

No camera, Qwen model, GPU, microphone, synthesis, speaker, or person session
was invoked for this finding. No latency improvement is claimed. It is derived
from exact current source flow and is now a required input to the long
evaluation and voice telemetry successors.
