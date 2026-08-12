# TemporaryAI Qwen3-TTS original voice forge R3 checkpoint - 2026-08-09

Status:
`R3_STATIC_REPAIR_SEALED_FRESH_INDEPENDENT_AUDIT_REQUIRED_REAL_EXECUTION_BLOCKED`

## Outcome

An append-only R3 successor closes, in source and hostile mocked tests, exactly
the four acceptance-proof gaps reproduced by the Attempt 02 independent audit.
Every R2 source, manifest, checkpoint, and audit remains byte-for-byte intact.

R3 is intentionally inert. No environment was created, no dependency or wheel
was installed, no model or evaluator was imported or loaded, no inference or
voice generation ran, no network request or playback occurred, and no current
voice, Chatterbox environment, route, handoff, or runtime was changed.

The R3 manifest remains:

- status: `IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT`;
- `execution_allowed: false`;
- exact inventory: 14/14 files verified;
- real execution unavailable until a fresh independent hostile audit accepts
  this exact revision and every separate environment/bundle/corpus gate exists.

## Four bounded repairs

### 1. Exact persisted prompt is the generation input

The R3 runtime proxy now:

1. reopens the exact append-only `original_design_reference.wav` and constructs
   the clone prompt from that saved reference rather than the preceding
   in-memory waveform;
2. records a deterministic semantic hash of the created prompt;
3. serializes the prompt, then requires the exact flushed
   `runtime_clone_prompt.pt` byte count and SHA-256;
4. deserializes only those exact persisted bytes through the approved runtime;
5. compares created and reloaded semantic hashes;
6. ignores the caller's original in-memory prompt for synthesis; and
7. passes only the reloaded prompt object to final clone generation.

Corrupt bytes, parseable substituted bytes, semantic drift, saved-reference
drift, or a runtime without a prompt-deserialization operation fail before a
clone can be accepted.

### 2. Evaluators cannot silently change accepted audio

Both final WAVs are sealed as readable, non-silent, uncompressed mono PCM16
artifacts with exact attempt-relative path, bytes, SHA-256, sample rate, frame
count, duration, and RMS.

The R3 evaluator proxy reopens and revalidates both WAVs immediately before and
after every public evaluator operation. It repeats the check before worker
acceptance, after writing the private R3 profile, after writing the R3 worker
manifest, and immediately before returning. After clean worker exit, the R3
parent independently resolves only paths inside the exact attempt directory,
reopens the prompt and both WAVs, repeats structural/hash verification twice,
and only then appends parent acceptance.

Evaluator-side mutation and post-worker/pre-parent mutation are both hostile
regressions and fail closed to text plus silence only.

### 3. Every installed distribution is independently enumerated

R3 recursively enumerates every actual `.dist-info` metadata root in the exact
isolated `site-packages` tree. Each root must be a direct installed root with a
unique METADATA identity and RECORD. The discovered canonical name/version,
metadata root, RECORD path, and RECORD hash must reconcile one-to-one with both
the declared manifest and independently verified distribution evidence.

Every file under each `.dist-info` root must identify that distribution as an
owner and must not be labeled loose. Legacy `.egg-info`, nested metadata,
omitted distributions, duplicate identities, and dist-info files relabeled as
loose fail. The same guard is installed in both parent preflight and worker
pre/post execution provenance.

### 4. Exact Torch wheels are bound to installed executable code

For both Torch and Torchaudio, R3 requires:

- exact wheel path, filename, bytes, SHA-256, METADATA name/version, complete
  archive RECORD, and `cp311-cp311-win_amd64` WHEEL tag;
- non-purelib Windows payload;
- the real import package root and `__init__.py`;
- at least one compiled `.pyd` member under that real package root;
- exact byte/hash equality for every wheel RECORD member and its corresponding
  installed RECORD file;
- an installed RECORD at the exact wheel RECORD path; and
- every installer-generated difference to be explicitly listed with path,
  bytes, hash, and a bounded reason.

Metadata-only wheels, wrong-root payloads, same-name/version archives whose
installed code differs, and undeclared installer differences all fail.
Parent preflight establishes this binding before a worker is started; the
worker repeats it before any model load and after execution provenance.

## Append-only process and trust boundary

The parent reserves a private R3 `bundle_id/attempt_NN` directory before
preflight so all failures have an append-only destination. It verifies the R3
entry worker and the frozen R2 core as separate exact files. The worker repeats
that two-file binding from the parent reservation before invoking any frozen
core function. The R2 core is imported only after the parent and direct-worker
R3 audit gates verify the sealed manifest.

The restricted environment remains offline flags plus exact local paths. R3
does not claim process-level network denial or proven network nonuse.

## Exact sealed R3 files

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_voice_forge_r3_guards.py` | 33,123 | `869ee27a048d2c40b8f1433b1fb17abf94c538f32bf3e74ec68417a2f9b4045c` |
| `tools/qwen3_tts_original_voice_forge_worker_v3.py` | 17,134 | `dcf9803afe4c519f19ff2eb6fc677454eb5b33d0e0d62861cfefe689ac90b020` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py` | 17,858 | `f2aa4dca82bed34a88f46a4e8529829072f1aba0f56e61d12d1be522957eb53d` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v3.py` | 27,123 | `7bb2b518d11a2ab1e19213369fa07cb01815445dff284b2e5c2831203c07d7a8` |
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json` | 5,033 | `3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada` |

The R3 manifest's 14-file inventory was independently recomputed after sealing
and matched every listed path, byte count, and SHA-256.

## Preserved rejection evidence

Attempt 02 audit:

- path:
  `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_REPAIRED_INDEPENDENT_AUDIT_ATTEMPT_02_20260809.md`
- bytes: 14,481
- SHA-256:
  `304f28d06cd37e45693dd88206a7979cde5c8e7cf729c33cf9dc36e2e59bad00`
- preserved verdict: `REJECT_FOR_BOUNDED_REAL_EXECUTION`

Frozen R2 manifest:

- SHA-256:
  `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4`

Frozen R2 worker, runner, and focused test remain respectively:

- `b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c`
- `88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45`
- `7bc62d1ca1976354bbca7d838c1c0c6f0af3fcb9860508f91ff756122f285972`

## Verification

Compilation:

- `py_compile` passed for the R3 guard, worker, runner, and focused test.

Focused R3 hostile suite:

- `22/22 PASS`;
- no model/evaluator import, inference, download, installation, network, or
  playback occurred.

Combined R2 and R3 focused suites:

- `82/82 PASS`.

Related TemporaryAI suites including v1, v2, v3, profile, body-draft,
character, canon, probe-context, and variant-identity coverage:

- `151/151 PASS`.

Hostile R3 coverage explicitly includes:

- invalid persisted prompt bytes;
- parseable but semantically substituted prompt bytes;
- proof that the reloaded prompt, not the in-memory prompt, reached generation;
- evaluator mutation after otherwise acceptable evidence;
- mutation between worker and parent acceptance;
- silent replacement audio;
- omitted `.dist-info` files relabeled loose;
- declared dist-info metadata relabeled loose;
- complete one-to-one distribution inventory;
- metadata-only Torch wheel;
- wrong package-root payload;
- exact real-payload archive/install binding;
- same-name/version but different installed Torch code;
- undeclared installer-generated differences; and
- manifest/launcher/worker inertness plus R2/audit preservation.

## Remaining gates

R3 is not approved for a bounded run. The next action must be a fresh,
independent hostile audit of these exact hashes. That auditor must rerun the
four original Attempt 02 exploits, inspect the actual parent/worker path, and
issue an append-only verdict.

Even if the static R3 audit passes, real execution remains separately blocked
because the isolated environment is not created or accepted, the exact
Blackwell Torch/Torchaudio wheels and installed binding evidence do not exist,
the evaluator/corpus evidence is pending, and no owner-authorized sealed bundle
is registered. No audit verdict may silently populate those facts.

## Rollback

No runtime rollback is required because no runtime or current voice changed.
To decline R3, preserve this checkpoint, the R3 manifest, and all prior audit
evidence; leave `execution_allowed` false and the registry empty. Continue
using the pre-existing approved voice routes. Never delete or modify a sealed
Chatterbox environment, current voice profile, approved Kira reference, R2
evidence, or model cache as part of that decision.
