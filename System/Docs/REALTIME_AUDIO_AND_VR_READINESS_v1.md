# Real-Time Audio and VR Readiness v2

## Current decision

Kira's current CPU Chatterbox path is not approved as real-time or VR-ready. The prior readiness artifact contains a 12.197-second non-playing model prewarm and complete voice jobs lasting about 27.8 to 61.9 seconds. Those values are useful diagnostics, but they are not timestamped request-to-first-audible measurements.

The later closed `2026-07-16 22:20-22:27 UTC` shell session adds three complete
CPU voice jobs of `45.707`, `29.505`, and `117.031` seconds. File timing and
PCM duration imply nine old sequential-chunk gaps from `6.196` to `15.979`
seconds (median `10.950`). The shell now prewarms a persisted active session,
rebalances tiny chunks, and overlaps one synthesis producer with one ordered
synchronous playback consumer. That is a structural latency repair only: no
post-repair voice was played or instrumented, so readiness remains unchanged.

The old observation is schema v1 and is intentionally rejected as `blocked_evidence_contract_invalid`. Its Kira reference is also pending human speaker, rights, and owner-authority review. It is not authorized voice evidence.

The machine may continue one-person, supervised desktop 3D testing. Do not add a second live 3D person or activate VR based on prewarm or idle memory alone.

## What "almost right away" means

Every readiness run measures the whole audible path:

```text
Robert finishes speaking or submits a message
-> dialogue response begins
-> first authorized-voice audio is synthesized
-> buffer starts playback
-> Robert hears the first word
```

Project acceptance targets:

- desktop-live p95 first audible speech: at most 1.5 seconds;
- immersive-VR p95 first audible speech: at most 750 ms;
- immersive-VR p95 continuation gap: at most 180 ms;
- immersive-VR p95 interruption to silence: at most 150 ms;
- exact word coverage, zero dropped replies, one consistent authorized voice, working audio-only controls, and measured RAM/VRAM headroom with 3D active.

These are project targets, not claims about the current engine or universal perception thresholds.

## Artifact-bound evidence contract

### Supervised shell event capture added 2026-07-16

The standard Kira World Shell launcher now enables a diagnostic recorder at
`Data/voice/realtime_audio_readiness/live_capture/`. The browser records a
server-monotonic submit marker before its body-snapshot request and 180 ms
wait. The correlated backend timeline then records text-ready, every chunk's
synthesis start/end and playback-call start/end, first-playback proxy,
completion/interruption, public expected/synthesized/playback-proxy word lists,
and RAM/process snapshots. GPU sampling is deferred to completion so
`nvidia-smi` is not inserted into the first-audio path.

Only separated public word tokens enter this recorder. Robert's prompt, raw
reply, private mind, and truth channel do not. Automatic
`playback_proxy_public_words` prove only that the corresponding synchronous
playback calls succeeded; they are not acoustic transcription.

`first_playback_proxy` is the instant immediately before the Windows playback
API call. It is explicitly labeled
`playback_api_call_start_not_owner_observed_audible`. True first audible,
audible word correctness, and true acoustic silence remain owner-observed (or
future calibrated hardware-loopback measurements), so their automatic fields
remain null. These JSONL events are diagnostic inputs, not automatically valid
schema-v2 readiness evidence. See
`Data/codex_reports/20260716_kira_voice_benchmark_instrumentation.md`.

The evaluator never accepts a dictionary of aggregate numbers as proof. Schema v2 requires five distinct, project-confined, exact-path/SHA-256/byte bindings:

```text
raw per-request samples
runtime configuration
instrumented collector bytes
voice authorization artifact
exact voice artifact
```

The raw artifact records monotonic request/first-audio timestamps, continuation gaps, interruption/silence timestamps, expected and observed word tokens, drop/control/model-ready states, RAM/VRAM headroom, and voice consistency for every sample. The evaluator recomputes p95, rates, minima, and drop counts. Non-finite values and percentages outside 0-100 are rejected.

The runtime configuration binds the run/profile, engine/version/device, 3D/XR/textless context, and exact voice hash. The collector attestation binds the collector's exact bytes and states that monotonic raw samples were written before evaluation; collector-supplied aggregates are forbidden.

Voice status and identity claim must be a compatible pair. The authorization artifact binds the subject, profile, voice bytes, rights gates, owner identity, and claim limits. Its exact hash and bindings must also appear in the code-hash-pinned owner registry:

```text
Data/voice/policies/realtime_voice_authorization_registry.json
```

That registry is currently empty/default-deny. A caller-written approval file cannot make a run ready.

## Evaluator behavior

```text
Core/realtime_audio_readiness.py
tools/evaluate_realtime_audio_readiness.py
Data/voice/realtime_audio_readiness/kira_cpu_chatterbox_baseline_20260716.json
```

Example:

```powershell
py tools/evaluate_realtime_audio_readiness.py `
  Data/voice/realtime_audio_readiness/kira_cpu_chatterbox_baseline_20260716.json `
  --profile desktop_live
```

Automation now receives exit code `2` unless the status is `ready`; no `--strict` reminder is required. `--allow-not-ready-exit-zero` exists only for explicit interactive inspection. Every printed/saved decision records the exact source-evidence path/SHA-256/bytes, run/profile, evaluation time, and evaluator core/tool hashes. Optional output is exclusive-create and limited to new JSON files below `Data/voice/realtime_audio_readiness/evaluations/`; it cannot overwrite the input or another project file.

## Target architecture

1. Keep the selected, authorized voice engine resident before conversation.
2. Generate a short natural first clause and begin playback without waiting for the whole paragraph.
3. Synthesize continuation clauses into a bounded FIFO/ring buffer while the first clause plays.
4. Keep dialogue, synthesis, file/network I/O, and playback off the render thread. A browser preview can later use an `AudioWorklet`; native VR can use the engine's real-time audio callback.
5. Cancel queued and playing audio on interruption without cutting ordinary uninterrupted sentences.
6. Use spatial position, earcons, and spoken status for message notifications, menus, errors, privacy boundaries, and emergency stop. Visible text may be an optional desktop mirror, never the only VR control.
7. Never switch to a different unapproved or identity-mismatched voice merely to make the first clause faster.

The bounded chunk-prefetch form of step 3 is now implemented for the shell,
including explicit incomplete-result reporting and synchronous ordered
playback. It is not a ring buffer and does not stream waveform samples.

The current Chatterbox API produces a complete chunk before playback. A future real-time path therefore needs measured GPU acceleration or a genuinely streaming authorized engine; smaller chunks, bounded prefetch, and prewarming alone are not proof.

## Voice discovery and historical reconstruction

TemporaryAI discovery may index candidate recordings and distinguish character, variant, speaker, and performer. Finding a clip proves that a recording exists; it does not grant permission to clone a living performer's voice.

When a verified historical recording exists, provenance and permitted use must remain attached. When none exists, the result is a clearly labeled `historically_informed_interpretation`: an educational design based on reviewed place, period, age, language, documented background, and recording-era constraints. It is never a recovered copy or exact voice match.

## VR and treadmill boundary

Build the future control layer around OpenXR rather than a single headset. Treat an omnidirectional treadmill as locomotion input with calibration, dead zone, recenter, seated/crouched states, watchdog, and physical emergency-stop tests. First VR tests should use a small empty/lightweight notebook scene. Add live Kira only after voice, frame-time, collision, privacy, and RAM/VRAM gates pass together.

Future human Robert and the autonomous Robert variant continue to use separate bodies; login never takes over the autonomous person's body.

## External design references

- OpenXR: `https://www.khronos.org/openxr/`
- KAT Walk C 2 Core support: `https://www.kat-vr.com/pages/support-detail?id=cf18dc66e98f49b68a8a6edf26eef8f3`
- AudioWorklet: `https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet`
