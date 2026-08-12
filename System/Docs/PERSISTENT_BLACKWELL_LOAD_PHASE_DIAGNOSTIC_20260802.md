# Persistent Blackwell load-phase diagnostic — prepared, inactive

## 2026-08-03 execution result and bounded follow-up — newest truth

The `full_load` diagnostic is no longer merely prepared. Append-only
`attempt_02` passed without synthesis or playback in `11.346943` seconds. It
loaded the exact cached model, prepared Kira's exact approved reference, then
released the model; post-cleanup Torch allocation/reservation were
`9,884,160` / `27,262,976` bytes. Its report is SHA-256
`257a064de409511a508446d36d588849911d30c473aedb64c56cca6e1c96dd30`.

The next original persistent acceptance, Attempt 03, is separately preserved
unchanged at SHA-256
`6af0455ec75c9f444cca57ebb53edb23f7d03646c9850c319ee59ee6414517e0`.
It timed out in `client.load()` after `939.012301` seconds and did not pass.

The inactive worker has now received one narrow, default-off revision: its
background thread samples host RAM only, while external `nvidia-smi` runs at
operation start/stop boundaries. This removes the repeating 250-ms external
process differential while retaining Torch allocator and CUDA output-tensor
proofs. The repair has `169` passing CPU-only/fake-backend tests but no new GPU
claim. A new append-only standalone acceptance is still required.

See
`RecoverySprint/continuation_20260803/kira_text_voice_latency_bounded_repair_preparation/LATENCY_DIAGNOSIS_AND_BOUNDED_REPAIR.md`.

The original prepared-diagnostic record below remains historical evidence.

Date: 2026-08-02  
Status: `PREPARED_INACTIVE_NOT_EXECUTED`  
Candidate: `kira_chatterbox_blackwell_persistent_eager_cuda_candidate_v1`  
Production preference: unchanged one-shot `blackwell_gpu` eager-CUDA route  
Automatic fallback: unchanged sealed CPU Chatterbox route only

## Decision

Persistent-candidate Attempt 02 is preserved as a failed, inactive experiment.
Its 888.583143-second wall time cannot truthfully be assigned to Torch import,
Transformers import, Chatterbox import, local Hugging Face cache resolution,
weight deserialization, model construction, CUDA transfer, or reference
conditioning. The existing worker records phase completion only in the final
`load` response; it emits no progress while `load()` is blocked. The exact
owned worker was later stopped and returned `4294967295` with no stderr, so its
report contains no escaping Python exception from the blocked phase.

No production file, candidate file, package, environment, model cache, approved
voice file, or prior attempt was changed to prepare this diagnostic.

## Preserved evidence and exact boundary

- Attempt 01 report SHA-256:
  `7272dc7da369569d077f88972d491aa84071582c42b798040e6106c7c98ec76b`
- Attempt 02 report SHA-256:
  `0bbf02d021c6217a7fbeca79e4f809bf640789215c61c14b2a9b675a9d67d115`
- Attempt 02 worker handshake: 0.1502512 seconds.
- Attempt 02 status transport: 0.0001538 seconds.
- Last confirmed boundary: `before_model_load`.
- Lifecycle at the stall: model not loaded, load count 0, conditioning count 0.
- Controlled persistent cache before and after: zero bytes.
- No CUDA allocation, WAV, synthesis, playback, or fallback occurred.
- Protected files matched before and after.

Therefore the exact classification remains:

`PERSISTENT_ATTEMPT_02_STALLED_INSIDE_UNINSTRUMENTED_CLIENT_LOAD_PHASE`

and not a claimed Torch, CUDA, cache, or Chatterbox failure.

## Read-only source finding

The candidate starts `ResourceSampler` immediately before its backend imports.
That sampler requests a new `nvidia-smi.exe` process every 0.25 seconds. Over
888.583143 seconds, the theoretical upper bound is roughly 3,554 launches,
although the failed attempt did not preserve an actual sample count. This is a
plausible source of load contention and an important confounder, but it is not
proven to be the cause.

The diagnostic deliberately has no repeating GPU/process sampler. This makes
the model-load timing attributable to the named load phases and avoids adding
thousands of external process launches during large weight reads.

## Exact local cache finding

The exact offline cache revision is present:

`5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18`

Required files total 3,191,966,992 bytes:

| File | Bytes |
|---|---:|
| `ve.safetensors` | 5,695,784 |
| `t3_cfg.safetensors` | 2,129,653,744 |
| `s3gen.safetensors` | 1,056,484,620 |
| `tokenizer.json` | 25,470 |
| `conds.pt` | 107,374 |

Preparation checked presence and size only. It intentionally did not perform a
new multi-gigabyte hash sweep. A later diagnostic resolves each file with
`local_files_only=True`; it cannot download or replace model content.

## Instrumentation added

`Tools/diagnose_persistent_blackwell_load_phases.py` binds the exact hashes of:

- Attempts 01 and 02;
- candidate config, contract, client, and worker;
- installed Chatterbox `tts.py`;
- production routing;
- production one-shot GPU worker;
- sealed CPU worker.

It refuses to execute if any bound hash changes. The child uses the candidate's
existing restricted environment constructor, offline variables, controlled
TEMP/TMP/compiler-cache paths, CUDA device restriction, session nonce, and
Qwen-absence gate.

The child emits append-only phase-start, two-second heartbeat, phase-end, error,
and terminal records for:

1. package metadata, identity hashes, and Qwen absence;
2. Torch, Torchaudio, Transformers compatibility classes, NumPy, SoundFile,
   Hugging Face, Safetensors, Librosa, Perth, and Chatterbox class imports;
3. local resolution of each of the five exact cache files;
4. CUDA contract/initialization;
5. the exact installed `from_pretrained` entry with a temporary, source-bound,
   instrumented equivalent of its `from_local` implementation;
6. each model constructor, weight read, state-dict application, and device
   transfer;
7. tokenizer and built-in-conditionals loading;
8. approved-reference `prepare_conditionals`;
9. object release, garbage collection, CUDA cache release, and synchronization.

The temporary instrumentation exists only in the isolated child process. It
does not edit installed Chatterbox source on disk. It never calls
`model.generate`, writes a WAV, opens an audio device, changes routing, invokes
a fallback, or promotes the candidate.

Each phase has a documented maximum. If a phase overruns, the parent preserves
the exact last phase/event/stderr evidence and stops only the exact child it
created. The overall bound is 1,800 seconds.

## Verification completed without model/GPU execution

Command run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest -v Testing.test_persistent_blackwell_load_phase_diagnostic
```

Result: 11/11 passed.

Static command run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\diagnose_persistent_blackwell_load_phases.py --static-self-check
```

Result: passed. This command imported no Torch/Chatterbox model stack and did
not initialize CUDA or load a model.

## Deferred exact diagnostic sequence

Do not run either command while Blender, a body render, Qwen, or another GPU
workload is active.

First, isolate imports and cache resolution without loading a model:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\diagnose_persistent_blackwell_load_phases.py --execute-diagnostic --confirm-no-active-blender --scope pre_cuda
```

Only if that completes and a later atomic boundary permits one heavy workload,
run the bounded load-only diagnostic:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\diagnose_persistent_blackwell_load_phases.py --execute-diagnostic --confirm-no-active-blender --scope full_load
```

Each invocation allocates a new append-only `attempt_XX` under:

`RecoverySprint/continuation_20260802/persistent_blackwell_load_phase_diagnostic`

The full-load command loads and then unloads the model and prepares the exact
approved reference, but it does not synthesize or play speech. Its result is a
diagnosis, not production acceptance or permission to promote the persistent
candidate.

## Interpretation and next repair boundary

- If `pre_cuda` stalls, repair only the exact import/cache boundary shown by
  the last heartbeat.
- If `pre_cuda` passes and a granular construction or weight-read phase stalls,
  investigate that exact component and disk/memory conditions; do not rebuild
  the environment.
- If a device transfer fails, preserve the exact CUDA traceback; do not change
  Torch or the approved model.
- If reference preparation alone is slow, profile that exact conditioning
  path and consider a separately validated persisted-conditioning artifact.
- If the diagnostic passes when the repeating sampler is absent, test the
  sampler hypothesis separately with sparse boundary-only measurements before
  proposing any candidate-worker change.

Until a later bounded engineering and owner-heard acceptance passes, the
persistent candidate remains inactive. The accepted one-shot eager-CUDA path
and sealed CPU fallback remain authoritative.
