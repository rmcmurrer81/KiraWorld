# Blackwell CPU-park candidate v8

V8 is an append-only, inactive successor to the accepted static v7 boundary.
It fills the two capabilities that v7 explicitly reported as absent: a real
adapter for the exact installed Qwen 3.5 / sealed Blackwell-v2 components, and
a bounded WAV playback consumer with separate owner-hearing telemetry.

## Status and non-claims

- `live_adapter_available=true` means the sealed implementation exists.
- `playback_implemented=true` means the sealed consumer exists.
- Neither path has been run or live-validated during v8 authoring.
- Production routing is unchanged and v8 cannot be selected as production.
- Live execution and playback remain unauthorized by this candidate.
- A different agent must audit the exact v8 seal and write the required audit
  authorization before the bounded engineering factory can be constructed.
- A second explicit per-run capability is then required. Importing any v8
  module is inert and does not satisfy either gate.

No Torch, CUDA, Chatterbox, Ollama/Qwen, audio, playback, person state, or
Blender operation is part of the authored static verification.

## Exact live adapter

The future gated worker is the same inherited v7 Job-owned process. It lazily
imports the exact sealed persistent-v2 `PersistentVoiceRuntime`, checks its
module and Python hashes, loads only the approved Kira profile/reference, and
exposes the real `t3`, `s3gen`, `ve`, and conditioning objects to the v8 state
engine. CPU synthesis, SAPI, generic voices, substitute references, Llama, and
internal fallback are all rejected.

Qwen access is loopback-only and closed to `/api/tags`, `/api/ps`,
`/api/generate`, and `/api/chat`. The adapter binds `qwen3.5:9b` to digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
uses strict finite bounded JSON, and retains v7's exact ownership, TTL,
aggregate deadline, stream, unload, and before/precommit/after residency gates.

## Device-transfer fingerprint truth

V7 correctly required complete parameter/buffer bytes, but its aggregate also
included every tensor object's Python identity. Real PyTorch device conversion
may replace registered buffer tensor objects while preserving their full
contents and schema. V8 therefore separates two truths:

1. The model generation binds a stable fingerprint containing every complete
   parameter and buffer byte string, name, kind, shape, dtype, length,
   gradient flag, and immutable top-level component object identity.
2. Tensor object identities are kept in a separate transfer manifest. They may
   change only at the exact owned CUDA-to-CPU or CPU-to-CUDA transition, with
   identical full content/schema and unchanged component objects. Each such
   change receives a generation-bound append-only transfer record.

An identity change outside a transfer, component replacement, content drift,
schema drift, conditioning drift, mixed device state, or before/after synthesis
fingerprint drift fails closed and cleans up.

## Playback and hearing truth

Playback consumes only the authoritative retained bytes from the same worker.
It rechecks the retained path and SHA-256, Qwen absence and exact model state,
writes one exclusive owned copy under the controlled runtime cache, and starts
the exact sealed Blackwell Python child. The child must inherit the worker's
non-breakaway kill-on-close Job. Its durable identity binds OS PID creation
time, exact executable path/hash/size, volume serial, and file index.

The playback child receives a restricted Windows environment plus a one-time
capability; it receives no v8 model-load or engineering capability. After WAV
structure and non-silence checks, it calls synchronous Windows `PlaySound` on
the already verified in-memory bytes (`SND_MEMORY | SND_SYNC`). This avoids a
filename time-of-check/time-of-use substitution. Start, end, error, route,
device, generation, fingerprint, exact memory SHA-256, child identity/Job, and
owned-copy deletion are bounded and checked. An unresponsive child is killed;
if it cannot be reaped, the worker exits so the parent closes the exact Job.

Successful API return never claims that Robert heard audio. A separate,
one-time, owner-bound acknowledgement may record `heard_complete`,
`heard_partial`, `heard_nothing`, or `uncertain` within the retained-artifact
lease and acknowledgement deadline. The evidence kind remains an explicit
owner report, never an automated hearing inference.

Normal cleanup deletes only the exact unchanged generated WAV under v7's owned
runtime output root. A mutated retained WAV is not silently deleted; it creates
cleanup debt and remains for explicit diagnosis. Approved reference/model
caches are never cleanup targets.

## Files and next boundary

`STATIC_SEAL_MANIFEST.json` covers the exact v8 config, this README, contract,
live adapter, state/playback wrapper, playback worker, worker entry, parent
integration, static fixture, and hostile suite. The future audit authorization
must point to that exact manifest and the runtime rehashes every listed file.

The author does not create the audit authorization. Assign a different agent
to rehash the seal, rerun and independently extend the static hostile probes,
and accept or reject. Even an accepted audit is static-only; it does not itself
authorize a live engineering run or production promotion.
