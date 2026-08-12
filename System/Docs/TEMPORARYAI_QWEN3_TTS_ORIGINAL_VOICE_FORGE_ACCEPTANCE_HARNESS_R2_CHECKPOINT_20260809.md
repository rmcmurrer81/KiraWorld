# TemporaryAI Qwen3-TTS original voice forge R2 checkpoint - 2026-08-09

Status:
`REPAIRED_STATIC_HARNESS_SEALED_FRESH_INDEPENDENT_AUDIT_REQUIRED_REAL_EXECUTION_BLOCKED`

## Outcome

An append-only, fail-closed R2 successor now specifies the bounded offline
TemporaryAI original-expert voice-forge acceptance path. It remains inert. No
Qwen3-TTS model, evaluator model, dependency, wheel, environment, or voice was
downloaded, installed, imported, loaded, or run. No current voice was changed.
No Chatterbox environment, model, reference, profile, cache, worker, or route
was modified.

The worker follows the official QwenLM/Qwen3-TTS Voice Design then Clone API:

1. `Qwen3TTSModel.from_pretrained` loads the exact private 1.7B VoiceDesign
   snapshot with eager CUDA, BF16, SDPA, and `local_files_only=True`;
2. `generate_voice_design` creates a trait-described original reference;
3. VoiceDesign unloads and VRAM return is verified;
4. `Qwen3TTSModel.from_pretrained` loads the exact private 0.6B Base snapshot;
5. `create_voice_clone_prompt` builds the reusable prompt from the designed
   `(waveform, sample_rate)` reference and its exact text;
6. `generate_voice_clone` creates the exact test text from that prompt;
7. Base unloads and final VRAM return is verified.

Official API source checked on 2026-08-09:
https://github.com/QwenLM/Qwen3-TTS/blob/main/README.md#voice-design-then-clone

The runtime does not invoke `torch.compile`, Triton, or FlashAttention. The
declared network boundary is truthfully limited to:
`OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL`.
It does not claim that network nonuse was technically proven.

## Fail-closed execution state

Real execution is currently impossible through the normal launcher because:

- the harness manifest remains `IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT`;
- the harness manifest has `execution_allowed: false`;
- the isolated environment is `SPECIFIED_NOT_CREATED_OR_ACCEPTED`;
- the exact Python, Torch, Torchaudio, CUDA wheel, evaluator, and full
  site-packages attestations are intentionally unset;
- the evaluation corpus is `PENDING_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS`;
- the trusted registry is `NO_OWNER_AUTHORIZED_BUNDLES_REGISTERED`.

The worker is inert without its explicit execution acknowledgement. The
launcher also requires the exact sealed harness, an eligible canonical
TemporaryAI candidate, exact profile and creation-request hashes, a sealed
owner authorization, an unused single-use nonce, exact queue binding, exact
model/evaluator/corpus/environment hashes, and a parent-reserved append-only
attempt directory.

Any failure preserves append-only evidence and returns only text plus silence.
Generic voice, SAPI, another person's voice, or a current-route change is
forbidden.

## Repaired hostile-audit boundaries

The first independent R2 audit is preserved unchanged at:

`System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_INDEPENDENT_AUDIT_20260809.md`

SHA-256:
`cc77ae5f8b2d068b4133e259a7141bc9d3c5485ec1bc546a32f6ce44ef3b0639`

Its verdict was `REJECT_FOR_BOUNDED_REAL_EXECUTION`. The sealed repair closes
the four reported blockers as follows, but a fresh independent hostile audit
must confirm them before the harness status can change.

1. Runtime provenance

   Every installed distribution is bound to its exact `.dist-info/RECORD`.
   Every RECORD member and the complete transitive/loose site-packages
   inventory is hash-checked before imports. Imported Torch, Torchaudio,
   Qwen-TTS, Transformers, Accelerate, Faster-Whisper, and SpeechBrain origins
   must be RECORD members. After synthesis and evaluation, the complete
   inventory is reverified and every loaded third-party submodule under the
   isolated site-packages root must resolve to an owning verified RECORD.

2. Sample-rate-safe speaker evidence

   Source sample rate, fixed 16 kHz speaker input rate, and deterministic
   `TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1` are bound into environment,
   corpus, and attempt evidence. Each normalized mono PCM16 WAV is append-only,
   hashed, reloaded, and then used as the exact speaker-embedding input. Both
   reference/clone and collision-corpus evidence must bind to those exact
   artifacts. Cross-rate and wrong-rate adversarial tests fail closed.

3. Watermark evidence truth

   The controlling built-in scan covers the complete declared site-packages
   inventory, its manifest, exact Torch/Torchaudio wheel evidence, runtime
   sources, private model/evaluator/corpus snapshots, and explicit binary and
   external-runtime exclusions. It explicitly records that the global bounded
   execution dependency inventory is not complete. Generation grants only:
   `NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`.
   A stronger status requires separate append-only detector evidence. No
   removal, stripping, disabling, evasion, concealment, or circumvention path
   exists.

4. Peak telemetry

   CUDA peaks use Torch's synchronized maximum allocated/reserved counters.
   RAM records the Windows OS process high-water mark and a separate 10 ms RSS
   sampler spanning generation and evaluation. Point observations are clearly
   labeled as observations and never as peaks.

## Acceptance gates retained

- exact original trait description; named-real-person imitation fails closed;
- real local ASR and exact requested-text fidelity;
- separate real speech classifier rather than an ASR no-speech proxy;
- multi-window pure-tone analysis from the actual PCM16 WAV;
- designed-reference-to-clone speaker similarity;
- recomputed exact-WAV collision checks against approved resident and known
  generic controls;
- readable, non-silent mono PCM16 WAVs;
- measurable GPU allocation, serialized one-heavy-model lifecycle, clean
  unload, and VRAM return;
- append-only private outputs, inactive/unassigned/unpublished state, exact
  profile/manifest hashes, owner hearing pending, and independent audit
  required.

## Exact sealed controlling files

- `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json`
  SHA-256 `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4`
- `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json`
  SHA-256 `8ae41050fcb5cef73d6dfc65a60a97302b0e8d7278f1dd40cc1cc9908233bab1`
- `Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json`
  SHA-256 `8cc507aaa6737a8d61920242f3c6e9cd3b0ac4670aa90cbc3a728f3cac88c69f`
- `Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json`
  SHA-256 `6348031cbbc8205d03d44dbdbef1fdf3d2ae984e8a7027347d4fdee11a5a1853`
- `Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json`
  SHA-256 `089a88f4ddcf96a2c557d3d3200d095f6dfe9198add90997736963389dff940a`
- `tools/qwen3_tts_original_voice_forge_worker_v2.py`
  SHA-256 `b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c`
- `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py`
  SHA-256 `88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45`
- `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py`
  SHA-256 `7bc62d1ca1976354bbca7d838c1c0c6f0af3fcb9860508f91ff756122f285972`

The harness manifest contains the exact byte sizes and SHA-256 hashes for all
23 controlling contract, environment, registry, corpus, worker, runner, test,
bundle-template, identity-evidence, and watermark-evidence files. Its complete
inventory was independently recomputed locally and matched exactly before this
checkpoint was written.

## Verification

Python compilation passed for:

- `tools/qwen3_tts_original_voice_forge_worker_v2.py`;
- `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py`;
- `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py`.

Focused R2 command:

`py -m unittest Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2`

Result: `60/60 PASS`.

Related TemporaryAI regression command covered the Elsa profile, R1 and R2
voice forge, fast voice/body draft, character validation/life, canon grounding,
candidate probe context, and variant identity suites.

Result: `129/129 PASS`.

The tests include hostile cases for forged authorization and nonce bindings,
named-person imitation, arbitrary analyzer/watermark assertions, empty or
drifting inventories, loose shadow modules, imported-module RECORD escape,
sample-rate/resampling mismatches, ASR drift, non-speech, actual pure tone,
non-finite evidence, generic/resident collision, source/corpus/model/evaluator
TOCTOU, stale tokens, process-start/post-worker evidence, transient RSS, exact
Windows peak RSS, Blackwell/CUDA gates, and text-plus-silence failure.

All model and audio activity in these tests used isolated mocks and temporary
PCM16 fixtures that were deleted with their test sandboxes. They are not model,
audio-quality, owner-hearing, or real-environment acceptance.

## Preservation

The complete R1 inventory and its checkpoint still match their previously
recorded hashes. The R1 checkpoint SHA-256 remains:

`a4f10dd5206f0a74aa2058fa48b886ca5f1a7c2b2f2f9a2e0b8415d2b36ae06c`

The prior R2 rejected audit is append-only and unchanged. No rejected evidence
was overwritten. Key sealed CPU/GPU Chatterbox configuration and worker hashes
were rechecked separately by the prior independent audit and were not edited by
this task.

## Remaining bounded work

1. Run a fresh independent hostile audit against the exact sealed hashes above.
2. Keep the harness blocked if that audit rejects any boundary.
3. In a separate authorized task, create and attest the new isolated
   environment without reusing or modifying any Chatterbox environment.
4. Pin accepted official Windows Blackwell Torch/Torchaudio wheels and every
   transitive installed distribution/RECORD plus the complete loose-file
   inventory.
5. Place and hash exact local Qwen and evaluator models; build the exact real
   collision corpus.
6. Register one sealed owner-authorized candidate/nonce only after all prior
   gates pass.
7. Run at most one parent-reserved private engineering attempt, then require
   another evidence review and Robert's private hearing decision before any
   assignment.

## Rollback

No runtime rollback is required because no runtime or current voice changed.
The R2 work is untracked, append-only static material. If Robert later rejects
the R2 proposal, preserve this checkpoint and the audit evidence, leave the R2
registry empty and environment unaccepted, and continue using the pre-existing
voice routes. Never delete or modify any Chatterbox environment, approved Kira
reference, current voice profile, or prior voice evidence as part of that
decision.
