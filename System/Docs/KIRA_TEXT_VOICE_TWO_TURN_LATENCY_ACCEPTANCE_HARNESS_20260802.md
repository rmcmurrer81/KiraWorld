# Kira Text + Voice two-turn latency acceptance harness — 2026-08-02

## Current status

`IMPLEMENTED_DEFAULT_INERT_NO_LIVE_RUN`

The new harness is:

`Tools/run_kira_text_voice_two_turn_latency_acceptance.py`

It prepares the missing normal-route acceptance for two supervised public
Kira turns. Preparing and testing the harness did **not** start Ollama, load
Llama, load Chatterbox, use CUDA, play audio, open a browser, open the webcam,
open the microphone, activate Kira, or change a production default.

Running the tool with no live flag, or with `--describe`, prints its contract
and exits. A live run is impossible unless all three separate confirmations
are also supplied:

- `--confirm-owner-supervised`;
- `--confirm-no-active-blender`; and
- `--confirm-speaker-playback`.

The live runner starts the same server command as the normal Kira Text + Voice
launcher, with an attempt-owned isolated runtime directory and no browser. It
uses the real `/api/activate`, `/api/chat`, asynchronous approved voice,
playback, `/api/deactivate`, and `/api/safe-close` paths. It never asks the
camera or microphone sidecars to capture a device.

## Exact model and turns

Every mode is bound to:

- model: `llama3.1:8b`;
- digest:
  `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`;
- exactly two fixed public questions;
- exact private model-call audit, raw reply, cleanup transformations, prompt
  hash, final public reply, and per-call Ollama timing;
- no Qwen text route and no sensory cue.

The two questions are deliberately ordinary, short owner conversation. They
do not ask for vision or hearing and therefore cannot create a false sensory
acceptance.

## Candidate modes

The modes are process-local environment candidates. None is a saved default.

| Mode | Persistent Blackwell | Llama keep-alive | Buffered first-content timing |
|---|---:|---:|---:|
| `one_shot_baseline` | no | no | no |
| `persistent_voice` | yes | no | no |
| `persistent_voice_llama_keep_alive` | yes | yes | no |
| `persistent_voice_llama_keep_alive_buffered` | yes | yes | yes |

The keep-alive value is explicitly bounded from `5s` through `10m`. Buffered
timing never displays, voices, or persists an unvalidated fragment. It records
the first nonempty content-chunk time and still withholds the complete text
until all existing reply validation and cleanup finishes.

Persistent modes require a passing, append-only standalone persistent-worker
acceptance report. The harness validates that report's hash, exact artifact
kind, successful two-WAV CUDA gates, Qwen absence, explicit unload, returned
Torch allocation, clean owned-worker exit, no playback, no fallback, and
unchanged protected files. It also binds the report to the current candidate
configuration hash.

## Voice fail-closed contract

Before a live run, the harness independently rehashes the approved profile,
reference WAV, Blackwell config/worker, sealed CPU config/worker, and approved
routing file. It accepts only this routing policy:

1. `blackwell_gpu` preferred; and
2. `sealed_cpu` as the sole automatic fallback.

The session candidate expects
`blackwell_gpu_persistent_candidate` for every successful synthesis chunk. It
requires CUDA, real GPU allocation, no CPU synthesis, session-owned lifecycle,
and persistent-worker reuse. If that candidate fails and the existing router
uses the exact sealed CPU route, the harness records the fallback as approved
and safe but marks the latency candidate failed. Any SAPI, generic, unknown,
unsealed, or malformed route fails immediately.

No live test in this package deliberately forces the GPU to fail. The sealed
CPU route is not synthesized merely to demonstrate fallback; its exact sealed
artifacts and sole-fallback policy are hash-verified without creating another
voice job.

## Exact evidence captured later

Each live mode creates a new, never-reused directory under:

`RecoverySprint/continuation_20260802/kira_text_voice_two_turn_latency_acceptance/<mode>/attempt_NN`

The report records:

- exact selected person, activation surface, model name/digest, prompts,
  replies, and transformations;
- server readiness, activation, and persistent prewarm time;
- request-to-text, first buffered content when enabled, synthesis, first
  playback-call proxy, playback, complete-voice, queue, and per-phase timing;
- exact approved route and route attempts for every chunk;
- every newly generated WAV's project-relative path, SHA-256, PCM properties,
  duration, and non-silence gate;
- benchmark-file path/hash and monotonic event order;
- low-frequency whole-GPU VRAM/utilization samples labeled by phase, sidecar
  peak metrics, baseline, peak, final use, and bounded return evidence;
- exact Llama residency after each turn and exact-model-only unload;
- deactivation, sensory purge, exact owned-server exit, closed ports, owned
  persistent-worker clean exit, and final empty Ollama state;
- before/after hashes for Kira identity, memory, profile, approved reference,
  voice routing/workers, persistent candidate, and model policy files; and
- before/after memory-promotion directory manifests.

The automatic first-playback event is explicitly labeled a playback API proxy.
It is compared with the existing desktop target of `1.5` seconds for
diagnosis, but it is not mislabeled as the moment Robert heard audio. The live
report leaves `owner_heard_latency_acceptance=false` until a separate calibrated
or owner-observed first-audible measurement exists.

## Exact first live commands — not run during implementation

First run the already existing standalone worker acceptance. On the current
append-only tree its first report will be `attempt_01`:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\run_persistent_blackwell_voice_candidate_acceptance.py --run-gpu --confirm-no-active-blender --expected-candidate-config-sha256 54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1
```

The exact current candidate-config hash is required. The prerequisite now also
proves that every Ollama model is absent before and after the two non-playing
WAVs; it never unloads another workload to make the test pass.

Only if that report passes, run the normal-route two-turn candidate while
Robert is present and expects two audible replies:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\run_kira_text_voice_two_turn_latency_acceptance.py --execute-live --confirm-owner-supervised --confirm-no-active-blender --confirm-speaker-playback --mode persistent_voice --persistent-prerequisite-report RecoverySprint\continuation_20260802\persistent_blackwell_voice_candidate_acceptance\attempt_01\PERSISTENT_BLACKWELL_ACCEPTANCE.json
```

The safer first run leaves Llama's existing per-turn `keep_alive: 0` behavior
unchanged and tests only persistent voice integration. The two co-residency
modes are separate later comparisons, not automatic follow-ons. A live result
does not promote any mode or edit a launcher.

## No-live verification

The implementation is covered by fake/local contract tests for inert CLI
behavior, explicit live confirmations, all environment modes, exact model
audit, routing hashes, append-only prerequisite binding, benchmark chronology,
persistent reuse, sealed CPU-only fallback, SAPI/generic rejection, WAV
validation, VRAM summary/return, residency, exact-model-only unload, clean
owned-worker release, and append-only attempt allocation.

## Rollback

Because the package changes no production default, operational rollback is to
leave all candidate flags unset. If an authorized live attempt is active, end
it through its normal deactivation/safe-close path first so only its exact
owned worker is released. Preserve any attempt evidence append-only.

Removing the new runner, its test, this note, and its implementation-evidence
folder restores the source tree to the prior state. No model, voice profile,
reference WAV, sealed sidecar, launcher, shell server, memory, or Video Studio
file needs restoration.
