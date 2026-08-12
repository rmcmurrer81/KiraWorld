# Blackwell Voice V20 measured-latency successor (author static package)

Status: `AUTHOR_SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT`

This scratch-only package implements the smallest coherent V20 control/worker
candidate without giving it live execution authority. It does not replace,
copy into, import, call, or modify Kira's current persistent-v2 production
route. It contains no measured latency improvement and must not be described as
faster.

## What is implemented

`voice_v20_worker.py` is a direct append-only retained-generation state engine,
not a runtime monkeypatch of V8, V10, or production V2. Its only constructible
mode is an exact `AUTHOR_STATIC_MOCK_ONLY` fixture whose authority explicitly
says `execution_authorized: false`. The live factory always refuses.

The engine loads and conditions one exact mock generation once, fingerprints
all parameters, buffers, approved-reference condition tensors, model object,
and `t3`/`s3gen`/`ve` component objects, then enforces this sequence:

`UNLOADED -> LOADED_CUDA -> PARKED_CPU -> QWEN_OWNED -> PARKED_CPU -> LOADED_CUDA -> SYNTHESIZED -> PARKED_CPU`

The worker never invokes Qwen. It grants an external window only after the full
generation is CPU-resident, then requires an exact Qwen 3.5 model/digest,
keep-alive-zero, unload-complete, no-overlap receipt before the same generation
can return to CUDA. The author fixture creates no audio and performs no
playback. Complete transfer and transition ledgers bind the unchanged tensor
and conditioning bytes. Typed Win32 memory observations, strict resource
limits, finite deadlines, cancellation, cleanup debt, and fail-closed release
are direct code.

The worker binds the canonical control module, its source bytes, control
functions, backend object/class/module, exact bound methods, code, defaults,
keyword defaults, closures, recursively bound container contents, referenced
globals, and every worker control-method descriptor. This is the V20 author
repair for the V11 module-substitution and V12 callable/control-substitution
rejection classes; a different hostile reviewer still has to prove it.

`voice_v20_native_supervisor.c` is source-only. It implements stable same-handle
hash and identity bindings, reparse/hardlink/owner/DACL rejection, a one-use
`CREATE_NEW` no-sharing write-through ledger with same-handle terminal append,
restricted handle inheritance, suspended process creation, kill-on-close Job
assignment, a 16 GiB Job memory ceiling, membership/limit proof before one
resume, and deterministic cleanup. Its `wmain` always refuses with exit 125.
No linked candidate executable is part of this package.

`MATCHED_EXPERIMENT_SCHEMA.json` reproduces V19's accepted-static four camera
conditions, 51 monotonic timestamps, 42 metadata fields, 30 derived durations,
and 15 ordering rules. It adds park/restore boundaries, resource and transfer
identity, true audio-device first-sample timing, and optional owner-heard onset.
It requires at least four counterbalanced pairs per condition and improvement in
both median and worst case; one faster sample is not success.

The schema also records a downstream coordination requirement for the Temporary
Creator, Avatar Builder, and voice generator: one exact person-spec digest must
bind identity, source/variant, era/branch, maturity, body specification, and
voice provenance across all three. Recording-backed matches, auditioned
approximations, and generic fallbacks are distinct. If no source recording
exists, an auditioned or Windows voice must carry explicit uncertainty and may
not be called authentic; it remains replaceable later without silently changing
the person's identity or body specification. V20 does not implement or
integrate those builders.

## Author-only verification

The cache-free Python suite rehashes all 41 exact Kira lineage inputs and runs
only deterministic mocks and static source checks. The native source compiles
with MSVC x64 `/W4 /WX` and passes `/analyze /W4 /WX`. Incidental `.obj`,
`__pycache__`, and test caches are outside the seal and must not be copied.

No model, GPU, synthesis, playback, camera, microphone, person, network,
production route, body, Blender, or Sarah operation ran. Production V2 remains
unchanged. V8 and V9 consumed failures remain consumed; V11 and V12 remain
rejected; V19 remains accepted-static schema lineage only.

## Required continuation

The next action is a **different exact-byte fresh static audit** of
`STATIC_SEAL_MANIFEST.json`. Even if it passes, this package still cannot run.
A separate native controller hostile-validation package, a different review of
that package, a separate one-use execution package, and a different run-
authority audit are required before one owner-scoped matched experiment.
Only that experiment can accept or reject a real latency improvement.
