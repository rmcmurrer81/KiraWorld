# TemporaryAI Qwen3-TTS Original Voice Forge R8 repair boundary

Date: 2026-08-10

Status: `INERT_STATIC_GUARD_SUCCESSOR_ONLY`

R8 is a minimal append-only guard successor to the independently rejected R7
package. It preserves R1 through R7 and every R7 audit artifact byte-for-byte.
It does not add an R8 parent, worker, launcher, execution authorization,
authorization ledger, reservation, claim, acceptance, audio file, or private
review artifact.

The R8 execution-facing verifier is intentionally fail-closed after static
document validation because audited R8 parent/worker integration is absent.
No R8 synthesis can be authorized from this package. A later separately
authored integration would require its own exact-byte static audit before a
new owner-authorized one-use run could be considered.

No model, audio generation, audio playback, GPU, network, person, body,
Blender, parent, worker, launcher, or predecessor execution graph was run while
authoring R8. Only source compilation and inert standard-library tests over
synthetic dictionaries and disposable temporary files are permitted.

## Preserved rejected predecessor

- R7 payload manifest:
  `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json`,
  SHA-256
  `509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb`.
- R7 fresh independent rejection:
  `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_INDEPENDENT_AUDIT_20260810.md`,
  SHA-256
  `577fd3cf047fbaa0abddeea7dfb7f86602b6b94f97b9f43a724d77affc7ab966`.
- R7 remains rejected and unauthorized. R8 never reinterprets a R7 report as
  acceptance and never edits an R7 byte.

## Four bounded static repairs

### 1. Short-lived dual-clock authorization documents

An R8 authorization document must bind one exact future R8 payload and fresh
independent static audit. Its lifetime is a positive integer no greater than
900 seconds. UTC expiry must equal UTC issuance plus that exact TTL, and
monotonic expiry must equal monotonic issuance plus the same TTL in
nanoseconds. Audit completion may precede issuance by at most 24 hours.

Verification samples wall and monotonic time internally through the R8 system
clock authority. Both clocks must independently place the sample inside the
authorization interval, and the clock identity must match. Caller-supplied
wall time is not accepted by the verifier. This establishes local ordering and
freshness; it is not a claim that Windows or Python is tamper-proof.

The distributed example remains disabled. Even a structurally valid document
cannot authorize execution because R8 has no integrated parent or worker.

### 2. Complete CUDA allocated/reserved pairing

R8 extends the worker resource schema so every required CUDA observation has
both allocated and reserved bytes:

- baseline;
- voice-design load;
- voice-design generation;
- voice-design unload;
- base load;
- clone generation;
- final state; and
- Torch peak.

Every counter must be an exact nonnegative integer and reserved bytes must be
greater than or equal to allocated bytes at every sample. R7's positive GPU
activity, peak, and bounded-return checks are preserved through an exact
projection into the sealed R7 validator.

### 3. Monotonic elapsed-time coherence

R8 adds monotonic start/end nanoseconds to the RSS sampler and parent wall
observation. End must be later than start. The claimed elapsed seconds must be
finite, positive, and agree with the monotonic delta within a sealed 1 ms
tolerance. RSS UTC ordering must also agree with the monotonic interval within
a sealed 250 ms wall-clock tolerance. Sample count, interval, and elapsed time
must be physically compatible.

NaN, infinity, negative elapsed values, reversed clocks, equal clocks with a
positive duration, and contradictory durations fail closed.

### 4. Windows Job accounting physics

R8 requires every Windows Job/process/memory/I/O/log-size counter to be an
exact non-boolean integer in its physical range. PIDs are positive distinct
32-bit values. Process counts cannot be negative or exceed their containing
totals. Terminated-process count cannot exceed total-process count. Job peak
memory cannot be below process peak memory. Positive I/O bytes require at
least one corresponding I/O operation. Parent wall duration is bound to its
monotonic interval.

## Static-only integration truth

R8 contains only a guard, disabled template, immutable payload closure,
focused/hostile tests, and append-only evidence. It deliberately contains no
R8 parent or worker. Therefore:

- `execution_allowed=false`;
- `self_authorization_allowed=false`;
- `parent_worker_integration_present=false`;
- no run can be authorized;
- no R7 or earlier entry point may be relabeled as R8 integration; and
- a future integration must generate the added telemetry fields from real
  observations rather than inventing or deriving them after the fact.

## Rollback

No runtime rollback is required. Ignore R8 for execution and preserve its
static evidence append-only. Existing approved voice paths and all R1-R7
historical evidence remain unchanged.
