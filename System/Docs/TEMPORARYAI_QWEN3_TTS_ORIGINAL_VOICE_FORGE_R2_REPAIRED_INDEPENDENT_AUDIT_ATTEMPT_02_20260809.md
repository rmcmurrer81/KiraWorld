# TemporaryAI Qwen3-TTS Original Voice Forge R2 — Repaired Independent Hostile Audit Attempt 02

Date: 2026-08-09  
Audit type: fresh independent hostile static audit plus isolated adversarial mock probes  
Execution boundary: no model load, model inference, voice generation, playback, package installation, download, or network access was performed

## Verdict

`REJECT_FOR_BOUNDED_REAL_EXECUTION`

The repaired R2 harness is materially stronger than the previously rejected revision, and its ordinary unit suite passes, but it still cannot prove the exact artifact and provenance claims needed for a bounded real execution. Four independently reproduced acceptance-critical gaps remain:

1. the saved runtime-clone prompt is never reloaded and is not the prompt used for synthesis;
2. accepted WAV artifacts can change after evaluator inspection without detection by either worker finalization or parent acceptance;
3. an installed distribution can be omitted from the distribution list and mislabeled as loose files while the verifier reports that all transitive distributions were declared;
4. a metadata-only wheel with no importable Torch package payload can satisfy the exact-wheel check, and the wheel archive is not cryptographically bound to the installed Torch/Torchaudio files.

This is a rejection of the current acceptance proof, not a finding that Qwen3-TTS, CUDA, Blackwell, or the proposed voice itself fails. No real environment or generated voice was exercised in this audit. The harness manifest remains correctly frozen at `IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT` with `execution_allowed: false`; this audit does not change that status.

## Exact frozen scope

The harness manifest lists 23 sealed files. Every listed path, byte count, and SHA-256 was independently recomputed before this report and matched the manifest. The principal frozen files were:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json` | 6,884 | `8ae41050fcb5cef73d6dfc65a60a97302b0e8d7278f1dd40cc1cc9908233bab1` |
| `Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json` | 3,633 | `8cc507aaa6737a8d61920242f3c6e9cd3b0ac4670aa90cbc3a728f3cac88c69f` |
| `Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json` | 154 | `089a88f4ddcf96a2c557d3d3200d095f6dfe9198add90997736963389dff940a` |
| `Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json` | 433 | `6348031cbbc8205d03d44dbdbef1fdf3d2ae984e8a7027347d4fdee11a5a1853` |
| `tools/qwen3_tts_original_voice_forge_worker_v2.py` | 163,093 | `b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py` | 48,980 | `88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py` | 98,392 | `7bc62d1ca1976354bbca7d838c1c0c6f0af3fcb9860508f91ff756122f285972` |
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json` | 5,557 | `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_HARNESS_R2_CHECKPOINT_20260809.md` | 10,672 | `c48444632f3af96d064ef01bfacb21cbdbd644415e66fae7e5ce1c399e056310` |

The earlier independent audit was also preserved unchanged:

- `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_INDEPENDENT_AUDIT_20260809.md`
- 17,870 bytes
- SHA-256 `cc77ae5f8b2d068b4133e259a7141bc9d3c5485ec1bc546a32f6ce44ef3b0639`

The current environment registry/corpus files are deliberately empty or pending, so a real execution is unavailable independently of this rejection.

## Verification performed

The frozen unit suite was run without bytecode writes:

`py -B -m unittest Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2 -v`

Result: `60/60 PASS` in 2.631 seconds.

Those tests were treated as untrusted evidence. Additional probes used only temporary directories, synthetic metadata/audio, and fake runtime/evaluator objects. They did not import or invoke the official Qwen3-TTS model, Torch CUDA inference, an ASR model, or a voice model.

## Blocker 1 — persisted prompt is not reloaded or used

### Source path

- Worker lines 2768–2770 create a prompt in memory, serialize it to `runtime_clone_prompt.pt`, and then pass the original in-memory `prompt` object to `generate_clone()`.
- `OfficialRuntimeV2.serialize_prompt()` at lines 2347–2350 only calls `torch.save()` into a byte buffer.
- The runtime protocol exposes no corresponding prompt-deserialization/reload operation.
- The profile at line 2843 records only the saved file's hash after synthesis.

The same in-memory reference waveform is also passed to `create_prompt()`; the just-written PCM16 `original_design_reference.wav` is not reopened and used to construct the persisted prompt.

### Hostile probe

A fake runtime returned the literal non-Torch bytes `NOT_A_VALID_TORCH_PROMPT_ARTIFACT` from `serialize_prompt()` while keeping the in-memory prompt usable by the fake generator. The worker still returned:

`ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT`

Therefore, the acceptance can succeed even when `runtime_clone_prompt.pt` is corrupt and unusable. The current evidence proves that bytes were saved and hashed; it does not prove that a reusable voice prompt can be loaded or that the clone was generated from that artifact.

### Required repair

After append-only creation and flush, reload the exact prompt artifact through the approved runtime under the still-verified exact base-model snapshot. Use only that reloaded object for clone synthesis. Construct the prompt from the exact reloaded saved reference WAV, or explicitly bind and verify the conversion if a different canonical input is intended. Add a test in which corrupt or substituted prompt bytes fail before clone output can be accepted.

## Blocker 2 — accepted output WAVs remain mutable after evaluation

### Source path

- `validate_audio_acceptance()` calls `validate_embedding_input_artifact()` with `source_wav_path=None` at worker lines 1432–1439. It checks evaluator-reported hashes but does not independently reopen the exact output path at that point.
- After evaluator evidence is returned, the worker does not perform a final independent reopen, PCM validation, and SHA-256 verification of both WAV files immediately before writing the profile/manifest.
- Parent acceptance at runner lines 873–904 reads and trusts worker manifest/profile statuses, then hashes those JSON files. It does not reopen or independently validate the prompt and WAV artifacts named inside them.

### Hostile probe

A fake evaluator first returned otherwise acceptable evidence for each valid generated WAV, then replaced that WAV on disk before returning control. The complete worker execution still reported engineering acceptance.

For the reference WAV:

- hash sealed into the candidate profile: `347df9ec9a60313264d11b791541a351c3f03fd3d86b72d9fb883d958e849b52`
- actual final file hash: `f977ae639bd4cd42eb76df73528c50e52fb20f003c90a5ad1d27804c8f162872`

For the clone test WAV:

- hash sealed into the candidate profile: `f859c9aaa87205598eb85dbf8e8fce54dbbf7739c2a57ed469ac991427253da1`
- actual final file hash: `f977ae639bd4cd42eb76df73528c50e52fb20f003c90a5ad1d27804c8f162872`

This is an artifact TOCTOU failure. The accepted profile can describe different audio than the files ultimately retained.

### Required repair

Immediately before worker manifest/profile finalization, independently reopen both exact WAV paths and the prompt path, validate format/content again, and recompute their hashes. Bind those final hashes into the manifest. The parent must independently resolve only paths inside the exact attempt directory, reopen the named artifacts, repeat the required structural/hash checks, and reject any mismatch. Add evaluator-side mutation and post-worker/pre-parent mutation tests.

## Blocker 3 — installed distributions can be hidden as loose files

### Source path

- Worker lines 1889–1899 and runner lines 256–266 compare the inventory manifest's distribution rows only with the distribution evidence supplied by the environment specification.
- Neither verifier independently enumerates actual installed `.dist-info`/`.egg-info` metadata roots (or equivalent `importlib.metadata` distributions) under the attested site-packages tree and reconciles them one-to-one with the declared distribution list.
- The recursive exact-file inventory detects extra files, but the inventory author controls whether those files are labeled as distribution-owned or `loose_unowned_file`.

### Hostile probe

An isolated site-packages fixture added:

- `omitteddep.py`
- `omitteddep-1.0.dist-info/METADATA`
- `omitteddep-1.0.dist-info/RECORD`

All three files were declared with exact hashes in the complete file inventory, but with empty owner-distribution lists and `loose_unowned_file: true`. `omitteddep` was omitted from the distribution rows and from spec-derived distribution evidence. Verification succeeded and returned:

`all_transitive_distributions_declared: true`

The boolean is therefore not independently established.

### Required repair

Independently enumerate every installed distribution metadata root from the exact site-packages tree, reject distribution metadata classified as loose, parse each RECORD, require one-to-one ownership/reconciliation, and repeat this before and after execution. Add a hostile test for an omitted `.dist-info` directory whose files are otherwise fully hashed.

## Blocker 4 — wheel archive is not bound to installed Torch/Torchaudio

### Source path

- Worker `verify_wheel_archive()` at lines 1992–2050 and runner `verify_wheel_archive()` at lines 322–372 validate archive path/hash, filename name/version, internal METADATA, and internal RECORD completeness.
- They do not require an expected importable package root such as `torch/` or `torchaudio/`.
- They do not reconcile installed distribution RECORD members/hashes with corresponding members from the exact wheel archive.
- They do not establish that the attested installed code came from the attested wheel rather than from another archive/source with the same distribution name and version.

### Hostile probe

A syntactically valid archive named:

`torch-2.11.0+cu130-py3-none-win_amd64.whl`

contained only its `.dist-info/METADATA`, `.dist-info/WHEEL`, and `.dist-info/RECORD`; it contained no `torch/` package member. The verifier accepted it with two hashed members verified. This can satisfy the current exact-wheel evidence check while proving nothing about the installed executable Torch code.

CUDA capability and eager-operation gates can separately prove that some installed runtime works; they do not cryptographically bind that runtime to this wheel archive.

### Required repair

Validate compatible wheel tags and required package roots, and cryptographically reconcile installed Torch/Torchaudio RECORD members against the exact wheel's RECORD/member hashes. Explicitly enumerate and justify installer-generated differences such as bytecode or metadata additions rather than leaving the relationship implicit. Add metadata-only, wrong-package-payload, and same-name/version-different-code adversarial tests.

## Controls that passed this static audit

Subject to the four blockers above, the source contains meaningful fail-closed controls for:

- exact owner authorization, candidate/bundle/job/queue binding, single-use nonce consumption, and append-only nonce ledger creation;
- pre-worker and worker failure evidence, including distinct preflight and started/post-start failure handling;
- local identity analysis, snapshot binding, and named-person/imitation rejection;
- fixed Python/runtime declarations, environment location checks, Torch/Torchaudio versions, CUDA/Blackwell capability, `sm_120`, eager matrix execution, and unsupported-kernel rejection;
- pre/post model and evaluator snapshot verification and post-import module-origin/RECORD checks;
- real ASR invocation requirements, exact expected-text WER, separate speech probability, multiwindow pure-tone rejection, substitute-voice/collision checks, and independent evaluation-corpus use;
- deterministic conversion to and reload of 16 kHz mono PCM16 evaluator input before speaker embedding;
- Torch allocation/reservation peak counters, OS process peak working set, and bounded 10 ms telemetry sampling;
- Qwen unload ordering, VRAM-return gates, clean worker exit, and text-plus-silence-only failure semantics;
- private, inactive, unassigned, unpublished outputs pending owner hearing and independent audit.

### No-network truth

The code truthfully labels its boundary as offline flags plus local-path restrictions, not process-level network denial. `network_use_proven`/`network_nonuse_proven` remain false. This audit therefore does not treat absence of a process network sandbox as a hidden pass and does not claim network nonuse was proven.

### Watermark evidence scope

The repaired scanner covers declared runtime source, the full declared site-packages file inventory, model/evaluator/corpus snapshots, and exact declared Torch/Torchaudio wheels. It now retains explicit exclusions and does not set `complete_exact_file_inventory` true for the broader universe. Its accepted phrase is limited to `NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`, with stronger detection still pending a separate audit. This is an appropriately narrow documentation claim, not proof that generated audio has no watermark or steganographic signal.

### RAM/VRAM truth

The implementation now uses Torch CUDA peak allocation/reservation counters, Windows process high-water working set, and a 10 ms system/GPU sampler, with labels that distinguish the measurements. This static audit confirms the measurement code shape only; it records no real RAM, VRAM, timing, CUDA, or audio values because execution was prohibited.

## Re-audit boundary

Do not authorize bounded real voice-forge execution on this Attempt 02 verdict. Preserve all frozen R2 source and previous evidence. A subsequent append-only repair should change only the minimum necessary implementation/tests/checkpoint/manifest, then receive another independent audit that reruns these four exact hostile probes as well as every previously closed blocker.
