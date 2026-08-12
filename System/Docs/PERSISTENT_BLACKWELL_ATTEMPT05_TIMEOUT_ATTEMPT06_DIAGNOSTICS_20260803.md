# Persistent Blackwell Attempt 05 timeout and Attempt 06 diagnostics - 2026-08-03

Status: **ATTEMPT 05 FAILED AND PRESERVED; ATTEMPT 06 PREPARED, NOT RUN**

## Attempt 05 result

The append-only Attempt 05 command began at approximately
`2026-08-03T22:20:39Z` and reached the outer shell limit after 900.476 seconds
with exit code 124. Three exact command-owned Python processes remained alive
but near-idle before timeout. Repeated GPU observations stayed around 1092-
1155 MiB and 1-7 percent, which does not prove candidate model residency. The
exact PIDs were absent after timeout cleanup. No WAV or final acceptance report
was created.

The client allows 60 seconds for worker startup/hello, then separately allows
900 seconds for a request. The load request's timer starts only after earlier
prechecks, hello, status, a Blender boundary, and the request pipe write. The
outer 900-second clock therefore expired before the later-starting internal
timer and cleanup could finish. The observed process chain supports the
inference that hello completed and load remained pending, but Attempt 05 had
no direct phase-start telemetry. It cannot identify whether the active phase
was backend import, `from_pretrained`, reference conditioning, CUDA
synchronization, or another exact load step.

Preserved evidence:

- `RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/attempt_05/ATTEMPT_05_TIMEOUT_FAILURE.json`
  - SHA-256 `3bdd7ff71e216d52798c846cb0f650391c6c4cfdfedd2a4c04a7bedb1bdd6d78`
- `RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/attempt_05/CHECKPOINT.md`
  - SHA-256 `2c092c8432c89fd7265b04b538a6e778749949a63efec71da541a8d58251d0cf`

## Narrow Attempt 06 diagnostic repair

The inactive candidate now emits request-bound `operation_phase_progress`
events when each load phase starts and finishes. The client validates those
events and durably appends them to `WORKER_PHASE_EVENTS.jsonl` inside the new
acceptance attempt. A started phase without its matching finished event is the
active hang boundary.

While a load request is active, a standard-library `faulthandler` watchdog
writes Python thread stacks to worker stderr every 120 seconds. The client
durably appends stderr to `WORKER_STDERR_FAULTHANDLER.log`. The watchdog is
always cancelled when load returns or raises.

The worker captures the original protocol stdout before model code can
temporarily redirect ordinary stdout to stderr. Phase JSON therefore remains
on the protocol stream even during `from_pretrained` and reference
conditioning.

The harness also creates `ATTEMPT_STARTED.json` exclusively immediately after
allocating a new append-only attempt directory and snapshots received events
and stderr before/after owned-child cleanup. Diagnostic files refuse overwrite.

The internal request timeout remains 900 seconds. Attempt 06 needs an outer
execution timeout of at least 1100 seconds so internal timeout, exact-child
cleanup, integrity hashing, and final report creation can complete.

## Unchanged safety and production truth

- The persistent candidate remains private, inactive, and outside production
  routing.
- Production Blackwell/CPU routes were not changed.
- The sealed CPU Chatterbox worker remains the only approved automatic
  fallback.
- SAPI, generic, and unsealed fallback remain forbidden.
- Torch, Torchaudio, Chatterbox, CUDA, Ollama/Qwen, Kira's profile/reference,
  and installed model files were not altered.
- No GPU/model load, synthesis, playback, Ollama, Kira, camera, microphone, or
  Blender run occurred during this repair.

## Static verification

- Focused candidate/integration tests: 28/28 passed.
- Broader relevant CPU/static regression: 209/209 passed.
- Eight changed Python/evidence scripts passed AST parsing.
- Eight changed/prepared JSON files parsed.
- The acceptance `--describe` path passed without launching a worker.
- The reverse patch reconstructs all eight pre-repair files at their exact
  hashes and passed `git apply --check`.

These are static/CPU results, not a GPU, voice, latency, or owner-hearing pass.

## Attempt 06 bindings and exact next command

Current candidate config SHA-256:

`8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57`

Exact command, prepared but not run:

```powershell
py -B tools\run_persistent_blackwell_voice_candidate_acceptance.py --run-gpu --confirm-no-active-blender --expected-candidate-config-sha256 8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57
```

The executor must provide an outer timeout of at least 1100 seconds and keep
all other heavy workloads inactive. The command should allocate append-only
`attempt_06`; this diagnostic repair did not pre-create that live attempt
directory.

The complete plan, rebound configurations, hashes, test evidence, and rollback
instructions are in:

`RecoverySprint/continuation_20260803/persistent_blackwell_attempt06_hang_diagnostics/attempt_01/CHECKPOINT.md`
