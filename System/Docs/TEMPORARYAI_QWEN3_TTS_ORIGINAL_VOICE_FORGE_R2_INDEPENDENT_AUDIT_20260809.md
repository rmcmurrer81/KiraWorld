# TemporaryAI Qwen3-TTS original voice forge R2 independent audit — 2026-08-09

## Verdict

`REJECT_FOR_BOUNDED_REAL_EXECUTION`

`PASS_STATIC_INERTNESS_APPEND_ONLY_BINDINGS_AND_PREDECESSOR_PRESERVATION`

Do **not** change
`TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json` to
`INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN` for this revision. Four
acceptance-evidence blockers remain. No Qwen3-TTS environment, model, bundle,
corpus, or real audio was present or executed during this audit.

This is a hostile independent source-and-evidence audit, not an owner-hearing,
audio-quality, model, CUDA, environment, or voice acceptance.

## Exact frozen source set

The following files matched the submitted frozen hashes both before and after
the independent test run:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_original_voice_forge_worker_v2.py` | 124577 | `c95693d74104c67f979fb7affa7d5d3c5a27144b8cbff9e6d7119a158aada4eb` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py` | 42418 | `d5f83cf9131b77cf3d9010700c01c30820dc27c12391ad89a02f64ca112c52ba` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py` | 73603 | `fbb73acfd48e99c9864287f4e3edd6f1d4a2389357f22b54899111afa32c1b71` |
| `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json` | 5768 | `84c6222cf593272336e80d45bc6d565316c1229e8bb4236641ffd5c2e912c03a` |
| `Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json` | 3171 | `ce46f8596736994c6aca5644b3ace6ad5bad6403e69ef74e6a97ee19f418f244` |
| `Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json` | 316 | `f11999f4984b5531e959d4cce8ad967dd7670eb59ca2b7f17f35a122032a14f1` |
| `Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json` | 154 | `089a88f4ddcf96a2c557d3d3200d095f6dfe9198add90997736963389dff940a` |
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json` | 5557 | `66e019651ca14440d19f77e0ad7af22b340ad7a2d7fd11fdcf74c2c835733f6a` |

The harness manifest also seals the inert bundle templates and evidence
templates. Its current status is correctly
`IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT`, with `execution_allowed: false`.

## Current execution truth

The current repository cannot run a real R2 attempt:

- `Voice/sidecars/qwen3_tts_voice_forge_v2/.venv` is absent;
- `Voice/models/qwen3_tts` is absent;
- `TemporaryAI/voice_forge_acceptance_bundles_v2` is absent;
- `Voice/voice_forge/private_review_v2` is absent;
- `Data/voice/runtime/qwen3_tts_voice_forge_nonce_ledger_v2` is absent;
- the environment status is `SPECIFIED_NOT_CREATED_OR_ACCEPTED`;
- the collision corpus status is
  `PENDING_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS` with no voices;
- the trusted registry status is
  `NO_OWNER_AUTHORIZED_BUNDLES_REGISTERED` with no entries.

Therefore this audit generated no voice, consumed no nonce, imported no model,
and changed no runtime route.

## Blocking findings

### B1 — Imported runtime modules are not bound to the attested RECORD files

The code validates distribution metadata and hashes every member listed by the
selected installed RECORD:

- `tools/qwen3_tts_original_voice_forge_worker_v2.py:1518-1581`;
- `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py:156-205`.

It then imports `torch`, `torchaudio`, and `qwen_tts` at
`tools/qwen3_tts_original_voice_forge_worker_v2.py:1669-1697`, and imports
`faster_whisper`, `speechbrain`, `torchaudio`, and `torch` for evaluation at
`tools/qwen3_tts_original_voice_forge_worker_v2.py:1805-1811`.

No post-import gate proves that each imported module's resolved `__file__` or
package `__path__` belongs to the already verified RECORD inventory. The
isolated `site-packages` directory is also not sealed as a complete directory,
so an unlisted loose module/package can shadow a valid installed distribution
while `importlib.metadata.distribution(...)` continues to resolve the genuine
dist-info metadata. In that state, a different `torch` implementation could
report the expected device name, capability, architecture list, CUDA build,
and matrix result even though the valid Torch RECORD and wheel also exist.

This defeats the intended exact Python/Torch/Torchaudio/CUDA provenance gate.
The existing test at
`Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py:495-504`
checks source-code ordering only. The runner test at lines `1114-1144` checks
RECORD location, wheel structure, and declared capability drift, but not module
shadowing or imported-file membership.

Required repair: either seal and reject drift in the complete isolated
`site-packages` import surface, or bind every imported module/package to the
verified distribution inventory after import and before use. Add a negative
test with an unlisted shadow `torch`, `torchaudio`, `qwen_tts`,
`faster_whisper`, and `speechbrain` module. Preserve pre-import RECORD/wheel
verification as well.

### B2 — Speaker embeddings discard the WAV sample rate

`OfficialSpeechEvaluatorV2.speaker_embedding()` loads `(signal, rate)` but
discards the rate and passes the unresampled waveform directly to the speaker
model at
`tools/qwen3_tts_original_voice_forge_worker_v2.py:1813-1816`.
Corpus validation proves only that each source is a readable mono PCM16 WAV at
lines `555-564`; it does not bind all corpus and generated audio to the
speaker model's accepted sample rate. The generated Qwen WAV rate is likewise
not normalized before reference/clone/collision comparison.

Speaker embedding models interpret a sample sequence at a model-specific
sampling rate. Comparing unnormalized 16 kHz, 24 kHz, or 44.1 kHz recordings
can change identity similarity and make the resident/generic collision gate
invalid even though all hashes and vector math pass.

The focused tests use injected vectors at lines `730-750` and a lambda speaker
embedding at lines `788-795`; they do not run a sample-rate mismatch through
the official speaker path.

Required repair: bind an exact accepted speaker input rate to the environment
and evaluator evidence, deterministically resample every exact source WAV (or
fail on mismatch), bind the resampled artifact/hash and transformation to the
source WAV, and add positive/negative multi-rate collision tests.

### B3 — The live watermark report overstates scan coverage

The live scan inventories only:

- explicitly supplied model/corpus snapshot roots;
- evaluator snapshot roots; and
- installed files for distributions already enumerated in runtime evidence.

That construction is at
`tools/qwen3_tts_original_voice_forge_worker_v2.py:1012-1028`. It omits the
complete isolated Python environment, unenumerated transitive distributions,
loose importable files, the runner/worker runtime sources as a scoped input,
and other native/runtime components that can participate in audio generation.
Nevertheless the report emits `complete_exact_file_inventory: true` and grants
the broad initial status `NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK` at lines
`1053-1067`.

The historical preflight is also not a coverage proof: lines `483-498` require
a nonempty exact inventory but do not prove that it is the complete source or
dependency set. The focused live test at
`Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py:713-727`
shows that a marker is rejected when it is inside the supplied inventory; it
does not show that an omitted relevant file is discovered.

This is not a request to remove, disable, evade, or detect an unknown
watermark. It is an evidence-truth issue. The narrow initial documentation
claim is supportable only if every relevant documentation/source path is in
the declared scan scope, or if the status is narrowed to the exact enumerated
files instead of the whole accepted revision.

Required repair: define the complete runtime dependency/source scope, bind it
to a sealed inventory (including transitive packages and imported loose/native
components as applicable), scan every eligible text/documentation member, and
state binary/oversize exclusions explicitly without labeling an incomplete
runtime scope complete. Keep the stronger watermark status gated behind its
separate post-generation audit.

### B4 — “Peak” RAM/VRAM fields are point samples, not demonstrated peaks

The worker initializes `peak_rss`, `peak_allocated`, and `peak_reserved` at
`tools/qwen3_tts_original_voice_forge_worker_v2.py:2030-2035`, and updates them
only immediately after the two model loads at lines `2038-2039` and
`2052-2053`. It does not update these values during or after VoiceDesign
generation, prompt construction, clone generation, or ASR/speech/speaker
evaluation. The manifest nevertheless labels them as peak measurements at
line `2115`.

The separately captured allocation values after generation prove only that
CUDA allocation existed; they are not folded into the claimed peak and cannot
observe a transient maximum. Process RSS is not sampled during the expensive
operations at all.

Required repair: use Torch peak-memory counters reset at the bounded phase
boundary plus a bounded process-RSS sampler, record sampling interval and
start/stop times, include generation and evaluator phases, and test that a
known transient maximum is captured. Until then, rename these values as
observed point samples rather than peak RAM/VRAM.

## Findings that passed static hostile review

### Trusted bundle, candidate, owner authorization, and nonce

- The caller can select only a safe opaque bundle ID plus acknowledgements.
- The registry uniquely binds the bundle seal, and the seal inventories every
  bundle file (`worker:714-803`; `runner:465-529`).
- Queue binding includes candidate, voice, AI type, job, nonce, canonical
  profile/request, identity evidence, watermark evidence, collision corpus,
  both model manifests, and the environment (`runner:396-412`;
  `worker:194-214`).
- The parent validates the exact sealed owner authorization, active scope,
  revocation state, every binding, and UTC expiry at `runner:415-462` and calls
  it from `runner:524-528`.
- In the real run order, bundle/owner verification and environment validation
  occur before nonce consumption at `runner:686-692`.
- The append-only nonce ledger repeats the complete queue binding at
  `runner:621-646`; the worker revalidates the parent reservation and ledger at
  `worker:1951-1982`.
- Canonical candidate paths, inactive status, AI type, creation provenance,
  and hashes are enforced at `worker:269-305`.

This closes the prior owner-authorization-before-nonce defect for the reviewed
revision.

### Named-person clearance

The sealed historical analyzer evidence now requires exact report/model/
command/stdout/stderr hashes and an owner review (`worker:352-437`). More
importantly, a hash-bound snapshotted local analyzer must run again before
model load (`worker:1389-1486`, invoked at `2017-2029`). Any nonempty named
person entity list, imitation request, non-finite/over-threshold probability,
or mismatched provenance fails. A named-person result other than the explicit
Taylor Swift defense-in-depth fixture is covered by the test at
`Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py:934-950`.

This is a sound fail-closed control shape. Its real analyzer accuracy remains
unaccepted because the exact analyzer environment/model is currently absent.

### ASR, speech, tone, and collision control shape

Subject to blocker B2, the source requires exact local ASR, a separate exact
local speech classifier, exact source-WAV hashes, finite probabilities, real
speaker embeddings, ASR WER, a PCM16 multiwindow tone detector, reference to
clone similarity, and resident/generic collision rejection
(`worker:1203-1280`, `1283-1337`, `1769-1899`). Every collision-corpus embedding
is recomputed from the attempt-local exact WAV and checked against its sealed
evidence at `worker:1174-1200`.

### Append-only failures and fail-closed behavior

The parent reserves `attempt_NN` before preflight and writes new-only failure
records (`runner:297-360`, `674-787`). The nonce ledger is new-only. The worker
uses new-only artifacts and, on failure, records
`FAILED_TEXT_PLUS_SILENCE_ONLY` with no generic voice, SAPI, other-person
voice, route change, playback, activation, assignment, publication, or upload
(`worker:2127-2134`). Successful output remains private, inactive,
unassigned, owner-hearing pending, and independently unaudited
(`worker:2087-2125`; `runner:750-780`).

### Network truth

The child environment is restricted and sets local/offline flags
(`runner:649-670`), but the code correctly says
`OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL` and consistently records
`network_use_proven: false`. It does not claim process-level isolation or prove
network nonuse. That is truthful.

### TOCTOU snapshots and import timing

Qwen model files, all four evaluator model roles and adapters, and collision
corpus WAV/evidence files are exclusive attempt-local copies with before/use/
after hash verification (`worker:593-649`, `870-997`, `1075-1142`, and
`1988-2086`). One heavy Qwen model is loaded at a time, with VoiceDesign
unloaded before Base.

The parent never imports the worker, and the worker has no Torch, Qwen, ASR,
or speaker package import at module import time. Distribution and wheel checks
precede Torch/Torchaudio import; eager CUDA checks precede Qwen import
(`worker:1645-1717`). This ordering passes, but blocker B1 means the identity
of the imported module files is not yet exact.

## Independent verification

Command run with bytecode writes disabled and no model execution:

```text
$env:PYTHONDONTWRITEBYTECODE='1'; py -B -m unittest Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2 -v
```

Result:

```text
Ran 53 tests in 1.756s
OK
```

All 53 focused tests pass. They do not clear B1-B4 because no test exercises
shadow-module import provenance, real speaker sample-rate normalization,
omitted watermark-scan scope, or a transient peak-memory measurement.

## V1 and Chatterbox preservation

The predecessor checkpoint remains byte-identical:

`System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_HARNESS_CHECKPOINT_20260809.md`

SHA-256:
`a4f10dd5206f0a74aa2058fa48b886ca5f1a7c2b2f2f9a2e0b8415d2b36ae06c`

All nine files in its exact v1 implementation inventory still match:

| V1 artifact | SHA-256 |
|---|---|
| `tools/create_temporary_ai_candidate.py` | `1ed3be42609480b91e86530679222f99fa0728bf81279dd00b01050e874b11dc` |
| `TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json` | `8df20b6fbd8b5432a644ae46e8d034016107118fe1c64e10f63bd025b3e92450` |
| `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json` | `0698556f366400e4105fd85f8610e1cefcb2d28bf29456440496c44100865a4f` |
| `Voice/sidecars/qwen3_tts_voice_forge/environment_spec_v1.json` | `1c9691a669292dae7b402c584e29ad728a2f52af977d50a59b7591e11243f2ad` |
| `Voice/sidecars/qwen3_tts_voice_forge/core_requirements_v1.txt` | `36cf7fa94b6085cb27725d8ebc5d2d321fbded633bf5f74872cd93a7347bb1fd` |
| `TemporaryAI/templates/qwen3_tts_original_voice_forge_job_v1.json` | `cdc84bb985d2c2238cc4fdf69edea07e2e89ed74a2e3bc2d0f0704ccf1c79e08` |
| `tools/qwen3_tts_original_voice_forge_worker.py` | `0aa283d2eaa718c791b9db24205acc3e8332e1a65e3b333023a72d13fb421ece` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance.py` | `a2fa5ef58c95e37c50a336d60364cd56e06d150e030592c96914a0d0d33d1c85` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance.py` | `98742fb01702287c9e5b194195e2d021c16564926c90a8c53f85fb2803bee943` |

Key Chatterbox and approved Kira route/profile hashes still match the sealed
`RecoverySprint/continuation_20260807/local_voice_workshop_audit/LOCAL_VOICE_WORKSHOP_AUDIT.md`
record:

| Preserved artifact | SHA-256 |
|---|---|
| `Voice/sidecars/kira_approved_voice_routing.json` | `a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81` |
| `Voice/profiles/temp_ai/kira_voice_profile.json` | `102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116` |
| `Voice/sidecars/chatterbox_py311/sidecar_config.json` | `7e544ae9e8788a0c1be5b0848657b2d70c6ec9c25ad86f3f597d95d8e55594e7` |
| `Voice/sidecars/chatterbox_py311/sidecar_worker.py` | `856c195173f8932f1b9d731634290f9eb78bb543e90da37c1346160e45334f46` |
| `Voice/sidecars/chatterbox_blackwell_gpu/sidecar_config.json` | `cb28e9f7fa498f4342f1e0606dc60a5c73c66065bf1528cad78f1ac77c8ae097` |
| `Voice/sidecars/chatterbox_blackwell_gpu/sidecar_worker.py` | `c7ac33170f5f5b85ef7df717a71bf468b2f37166bb5f70e6441bea8ed6d8da1e` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/candidate_config.json` | `805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/persistent_worker.py` | `b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad` |

Recursive UTC timestamp checks found no v1 inventory file or Chatterbox
sidecar/environment file modified at or after the R2 work start. Git cannot
provide a historical diff for these trees because `git ls-files` reports them
as untracked; preservation is therefore established by the prior sealed
manifests, current SHA-256 matches, and timestamps rather than Git history.

## Required disposition

Preserve this rejected revision and report append-only. Repair B1-B4 in a new
hash set, rerun focused tests with negative coverage for each blocker, and
obtain a new independent audit. Do not build/download a model or consume an
owner nonce as part of the source repair. Even after the harness passes a
future source audit, environment, model, analyzer, evaluator, corpus, CUDA,
audio, collision, watermark, owner-hearing, and assignment gates remain
separate and pending.
