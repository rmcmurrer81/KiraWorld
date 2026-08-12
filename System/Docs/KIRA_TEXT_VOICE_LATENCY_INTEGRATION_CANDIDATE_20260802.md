# Kira Text + Voice latency integration candidate — 2026-08-02

## 2026-08-03 bounded candidate revision — newest truth

The statement below that the persistent candidate remained byte-for-byte
unchanged was true for the original 2026-08-02 integration checkpoint and is
now historical. Attempts 01–03 remain immutable evidence bound to the old
worker/config hashes.

After the separate exact full-load diagnostic passed in `11.346943` seconds
but original persistent Attempt 03 timed out after `939.012301` seconds, one
narrow inactive-candidate revision removed repeating background external GPU
process queries during load. Host-RAM sampling remains in the background;
external `nvidia-smi` is boundary-only; Torch allocator and CUDA output tensors
remain the actual GPU proofs.

Current revised inactive candidate:

- `persistent_worker.py` —
  `5b36fc085ae5e536da27f079ec70cd2e26c842b266c3002079c56f875b5716a3`;
- `candidate_config.json` —
  `54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1`.

The candidate is still default-off, private, unpromoted, and not a latency
pass. Production remains the approved one-shot Blackwell route with sealed CPU
as its only automatic fallback. A new standalone two-WAV GPU acceptance bound
to the revised config must pass before the prepared two-turn owner-hearing
harness can run. Static/fake-backend verification: `169 tests`, `OK`.

Current package:
`RecoverySprint/continuation_20260803/kira_text_voice_latency_bounded_repair_preparation/`.

## Status

`IMPLEMENTED_DEFAULT_OFF_PENDING_LIVE_GPU_AND_CORESIDENCY_ACCEPTANCE`

This is an integration candidate, not a production promotion and not a latency
pass. No GPU model, audio device, camera, microphone, or live owner
conversation was run while preparing it. The normal flags remain unset, so the
current one-shot approved Blackwell route and sealed CPU fallback remain
unchanged at runtime.

The pre-existing sealed persistent candidate remains byte-for-byte unchanged:

- `candidate_contract.py` — `89decf08ed3502b6e771d3940867d5f7c2f31bb2f4fc0e515083dc15fbf850fe`
- `candidate_client.py` — `66b62c958c764344138e8c79f1cec4b63a6ba74a9e3ee0a77f777503a835dfe1`
- `persistent_worker.py` — `aa67d6eb7be12ddc61e1fcdf57715cfbe6f26ac966a996d7bab7304e7415b060`
- `candidate_config.json` — `a96278400a675a8e8dc38c38087659de52e2b8b0d2bcc345118a64177b0899d0`

## Persistent approved-voice integration

`Core/persistent_blackwell_voice_integration.py` is a standard-library parent
adapter around the unchanged candidate client. It is gated by the exact,
default-false environment flag:

`KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE=1`

When and only when that flag is explicitly set, the Kira shell:

1. assigns one opaque owner to the current Kira voice-session generation;
2. starts and prewarms one exact child created by the sealed candidate client;
3. reuses that worker and its approved reference conditioning for subsequent
   public `SPOKEN` chunks in the same session;
4. rechecks the approved profile/reference hashes and Qwen absence before load
   and every accepted CUDA generation;
5. requires public-channel/text hash binding, no playback in the worker, no
   generic/SAPI/internal fallback, a readable WAV, CUDA output tensors, and a
   persistent CUDA allocation;
6. moves the already validated, unique staging WAV to the caller's
   project-owned absent target and validates its hash again;
7. unloads and closes only the exact `Popen` child owned by that session on
   deactivation, safe-close, final server cleanup, failure, or process exit.

The sealed candidate's original output-root policy is not weakened. Temporary
candidate output is staged under:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/runtime_integration_staging`

No worker playback is permitted. The existing shell playback path remains the
only playback owner.

If the active persistent route fails, it must first prove that its exact child
closed. Only the sealed CPU sidecar is then an automatic fallback. The
one-shot GPU route is retained as rollback behavior when this feature is off
or no persistent shell session owns the request; it is not silently run after
an active persistent-worker failure.

## Shell lifecycle and telemetry

The normal activation, asynchronous prewarm, FIFO synthesis/playback,
deactivation, safe-close, and final server cleanup paths are connected. Logs
expose bounded machine facts such as lifecycle type, route, reuse, queue and
synthesis timings, GPU/CPU attempted state, actual approved path, and exact
owned-child cleanup. They do not copy public text, private text, tracebacks, or
arbitrary child output into route telemetry.

## One-call outer reply-repair budget

Each Kira shell request now owns one shared token across model-backed outer
repairs for an unrequested social tangent, cross-session repeated opener, and
settled-question loop. At most one of those stages may make one additional
model call. Later stages use deterministic, truth-bounded fallbacks. A natural
reply that needs no repair consumes no token. The existing primary model call
and the ConversationLoop's internal truth pipeline are not mislabeled as
outer repair calls.

The shell records only the count and stage names in
`kira_outer_reply_repair_budget`; it does not log repair prompts through that
event.

## Optional Llama latency candidate

The exact restored `llama3.1:8b` Text + Voice path has two additional
default-off controls:

- `KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=1`
- `KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=1`

The optional duration is set with
`KIRA_LLAMA_KEEP_ALIVE_CANDIDATE_DURATION`; invalid or out-of-range values use
`5m`, and accepted values are bounded from 5 seconds through 10 minutes. With
the keep-alive flag absent, the existing `keep_alive: 0` unload contract is
unchanged.

Buffered streaming records first response-event and first nonempty-content
timing. Fragments remain private in memory and are concatenated before the
model call returns. No partial, unvalidated fragment is displayed, voiced, or
written as the final reply. The existing cleanup/truth pipeline still receives
the complete response.

Keeping Llama resident while persistent Chatterbox owns the same GPU is not
accepted yet. Both optional text flags and the persistent voice flag must
remain off until a bounded live test proves VRAM headroom, route serialization,
latency improvement, clean unload, and exact voice identity.

## Verification

No-GPU focused and regression command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest Testing.test_kira_latency_integration_candidate Testing.test_voice_output Testing.test_blackwell_persistent_voice_candidate Testing.test_model_request_policy Testing.test_kira_private_acceptance_audit Testing.test_kira_dialogue_state_grounding Testing.test_kira_world_dialogue_audio_continuity Testing.test_kira_text_only_no_sensory_truth_gate Testing.test_kira_text_voice_sensory_prompt_bridge Testing.test_kira_world_latest_session_repairs
```

Result: `151 tests`, `OK`, no live GPU/audio/device operation.

## Required later acceptance before promotion

- confirm no active Blender process and serialize all GPU owners;
- run the existing persistent Blackwell live harness first;
- run fresh-process shell activation/prewarm, at least two real public replies,
  playback timing, deactivation, VRAM return, and safe-close;
- prove exact Kira profile/reference hashes and Qwen absence for every
  accepted generation;
- compare cold one-shot, warm persistent, and sealed CPU latency without
  treating playback-call time as owner-heard audio time;
- separately test Llama unloaded versus bounded keep-alive co-residency;
- do not enable a flag unless the exact tested combination passes.

## 2026-08-02 live persistent-candidate result

Two append-only attempts were made without playback or production promotion.

- Attempt 01 stopped before worker launch because the workspace-restricted
  process could not query `tasklist`; this is an environment-preflight
  failure, not a Chatterbox result.
- Attempt 02 used ordinary Windows process-query access. Its worker handshake
  completed in `0.1502512 s`, its unloaded status request in `0.0001538 s`,
  and all no-Blender boundaries passed. The worker then remained inside the
  explicit `load` request for `888.583143 s` without stderr, CUDA allocation,
  output audio, cache growth, or a response. Only the exact owned worker was
  stopped after its PID and command line were verified.

Attempt 02 evidence is
`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/attempt_02/PERSISTENT_BLACKWELL_ACCEPTANCE.json`,
SHA-256
`0bbf02d021c6217a7fbeca79e4f809bf640789215c61c14b2a9b675a9d67d115`.
The concurrent resource snapshot found `18.96 GB` physical RAM free,
`14,906 MiB` GPU memory free, `529.01 GB` disk free, and zero persistent
runtime-cache bytes. Resource exhaustion and a full cache are therefore not
the current explanation. The persistent candidate remains inactive,
unpromoted, and unsuitable for the normal chat route pending a separately
instrumented pre-CUDA load-phase diagnosis. The approved one-shot eager-CUDA
route and sealed CPU-only fallback remain unchanged.

## Operational rollback

Leave or restore all three enable flags to unset/false and restart the Kira
shell. That returns routing to the existing one-shot Blackwell preferred path
with sealed CPU automatic fallback; no model, profile, reference, or sealed
sidecar file needs to be restored. A running persistent candidate, if any,
must be ended through normal Kira deactivation or safe-close so its exact owned
child is unloaded and closed before restart.
