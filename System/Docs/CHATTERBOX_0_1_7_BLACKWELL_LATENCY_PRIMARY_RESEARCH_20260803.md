# Chatterbox 0.1.7 / Blackwell latency research

Recorded: 2026-08-03T21:22:49Z  
Scope: read-only research and local static inspection. No model was run, installed, downloaded, replaced, or reconfigured.

## Outcome

The first repair should be a narrow correctness fix in the inactive persistent candidate, not a new model or an unofficial accelerator.

The exact installed Chatterbox 0.1.7 implementation completes synthesis by moving the generated waveform to CPU, converting it to NumPy, applying the PerTh watermark, and returning a newly created CPU tensor. The inactive persistent candidate nevertheless requires the returned tensor itself to report `device.type == "cuda"`. That condition can never be true for this official API. It rejects an otherwise valid GPU synthesis, retries it as many as three times, and can then time out. Actual CUDA use must instead be proven by the already collected device, allocation, peak-allocation, external-utilization, synchronization, and unsupported-architecture evidence.

This is separate from the genuine runtime latency of Chatterbox. Removing the false rejection prevents wasted repeated generations and allows the existing two-WAV persistent acceptance to measure the real steady-state time.

## Exact local evidence boundary

- Installed original implementation: `Voice/sidecars/chatterbox_blackwell_gpu/.venv/Lib/site-packages/chatterbox/tts.py`
  - SHA-256: `7896787bc17e20eafcd1dce7b8a4a6ea3a6478baab771c60d63e9e81f5564195`
  - `prepare_conditionals`: line 182
  - `torch.inference_mode`: line 245
  - CUDA result moved through `.cpu().numpy()`: line 270
  - new CPU tensor returned: line 272
- Inactive persistent worker: `Voice/sidecars/chatterbox_blackwell_persistent_candidate/persistent_worker.py`
  - SHA-256 at inspection: `5b36fc085ae5e536da27f079ec70cd2e26c842b266c3002079c56f875b5716a3`
  - prepares the approved reference once: line 338
  - calls the already conditioned model without an audio path: lines 458-466
  - records returned tensor device: line 495
  - wrongly requires the returned tensor to be CUDA: lines 502 and 636-641
  - permits up to three generation attempts per chunk: line 442
- Candidate configuration SHA-256: `54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1`
- Accepted one-shot GPU worker: `Voice/sidecars/chatterbox_blackwell_gpu/sidecar_worker.py`
  - SHA-256: `c7ac33170f5f5b85ef7df717a71bf468b2f37166bb5f70e6441bea8ed6d8da1e`
  - correctly proves GPU execution from CUDA peak allocation instead of the public output tensor device.
- Installed Turbo implementation: `Voice/sidecars/chatterbox_blackwell_gpu/.venv/Lib/site-packages/chatterbox/tts_turbo.py`
  - SHA-256: `19b531951f0ea68102327f379b2b9eb986d37d4a3eae30ef58716c7d61abf98e`
- The normal Chatterbox model is present in the local Hugging Face cache. No `ResembleAI/chatterbox-turbo` cache was present at inspection. No cache was changed.

## Primary-source findings

1. Chatterbox 0.1.7 is the currently installed package release. PyPI records 0.1.7 and its 2026-03-26 release artifacts: [official PyPI project](https://pypi.org/project/chatterbox-tts/).
2. The official original implementation supports a reusable model object and explicit `prepare_conditionals()`. Supplying `audio_prompt_path` to every `generate()` call repeats reference loading, resampling, S3 reference embedding, speech-token conditioning, and voice-encoder embedding. Calling `prepare_conditionals()` once and then generating without `audio_prompt_path` reuses those conditionals: [official `tts.py`](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/tts.py).
3. `Conditionals.save()` and `Conditionals.load()` are official APIs in the same source. They make an exact-hash-bound cold-start conditioning cache technically possible; an in-memory conditioned model is still preferable for steady-state requests.
4. The official original `generate()` is non-streaming. It returns only after T3 token generation, S3 waveform generation, CPU conversion, and watermarking. It already uses `torch.inference_mode()`: [official `tts.py`](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/tts.py).
5. The original code hard-codes `max_new_tokens=1000` and labels use of a configured value as a TODO. It normally stops on EOS. Arbitrarily lowering this private cap is not a supported latency control and risks truncated speech: [official T3 implementation](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/models/t3/t3.py).
6. With the original model, positive CFG duplicates the text batch. Official guidance describes CFG and exaggeration as pacing/expressiveness controls, not latency controls. Changing them can change Kira's approved delivery and requires voice reacceptance: [official README](https://github.com/resemble-ai/chatterbox#original-chatterbox-tips).
7. Resemble describes Chatterbox-Turbo as its low-latency English voice-agent model: a streamlined 350M architecture with less compute and VRAM and a distilled speech-token-to-mel decoder. The installed 0.1.7 package contains `ChatterboxTurboTTS`, but Turbo is a different official checkpoint and the weights are not locally cached: [official Turbo model card](https://huggingface.co/ResembleAI/chatterbox-turbo), [official `tts_turbo.py`](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/tts_turbo.py).
8. Resemble now also lists a 110M Nano model for tight latency and memory budgets. It is not exposed by the exact installed 0.1.7 Turbo class, so adopting it would be a package/source plus model change, not a narrow repair: [official model zoo](https://github.com/resemble-ai/chatterbox#model-zoo).
9. PyTorch AMP can accelerate eligible inference operations with FP16 or BF16, but it is not guaranteed to be compatible with every model or custom operation. Chatterbox 0.1.7 exposes no supported dtype option. Any AMP trial must remain an isolated candidate with signal, identity, and owner-hearing comparison: [official PyTorch AMP reference](https://docs.pytorch.org/docs/stable/amp.html).
10. PyTorch can use TF32 for float32 matrix multiplications on Ampere-and-later NVIDIA GPUs. It may improve performance while reducing internal mantissa precision, so it is a bounded candidate setting, not a silent production default: [official matmul-precision API](https://docs.pytorch.org/docs/main/generated/torch.set_float32_matmul_precision.html), [official numerical-accuracy note](https://docs.pytorch.org/docs/stable/notes/numerical_accuracy.html#tensorfloat-32-tf32-on-nvidia-ampere-and-later-devices).
11. PyTorch SDPA automatically chooses among available CUDA attention backends when its input constraints permit. Forcing a backend can warn or fail when constraints are not met. Chatterbox 0.1.7 exposes no supported attention-backend switch: [official PyTorch SDPA reference](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html).
12. CUDA Graphs can reduce CPU launch overhead, but require graph-safe static shapes/control flow and retain long-lived buffers. Chatterbox token sampling has dynamic length, random sampling, EOS control flow, and changing text shapes. Whole-model capture is therefore not a narrow supported repair: [official PyTorch CUDA semantics](https://docs.pytorch.org/docs/main/notes/cuda.html#cuda-graphs).

## Recommendation matrix

| Priority | Option | Compatibility class | Expected value | Required proof before routing |
|---|---|---|---|---|
| P0 | Remove `returned waveform tensor must be CUDA`; retain real CUDA allocation/device/peak/utilization/warning gates | Narrow correctness repair; same environment, model, reference, and voice | Prevents guaranteed rejection and up to three wasted syntheses; enables truthful latency measurement | Static fake test where official-style CPU waveform plus proven CUDA allocation passes; absent CUDA allocation still fails; exact two-WAV acceptance; protected hashes |
| P1 | Keep one worker and one model loaded; prepare exact approved reference once; reuse both | Narrow; already designed in inactive candidate | Removes per-turn Python startup, imports, checkpoint load, CUDA model transfer, reference decode/resample/embedding | `model_load_count == 1`, `reference_conditioning_count == 1`, two distinct valid WAVs, no retries, exact hashes, VRAM accounting and clean unload |
| P2 | Load from the exact pinned local snapshot with official `from_local()` rather than resolving the hub cache on every cold load | Narrow implementation candidate; no weight change | Reduces cold-start lookup work and makes offline identity deterministic; no steady-state synthesis gain | Exact snapshot/file hashes; offline-only; output identity/signal equivalence; rollback |
| P3 | Optionally persist official `Conditionals.save()` output, bound to model-source, checkpoint, profile, reference-WAV, package, and conditioning-setting hashes | Narrow cold-start candidate; privacy-sensitive derived voice artifact | Avoids reference decoding and encoder work after a process restart; no gain once in-memory conditioning is already reused | Protected storage; fail closed on any hash mismatch; compare loaded vs freshly prepared conditionals; never substitute a generic condition |
| P4 | Measure a one-time post-load warm path, then report cold and steady-state timing separately | Narrow benchmark | Separates startup cost from actual conversational synthesis; may amortize lazy CUDA initialization | Approved public test text only, no playback unless Robert is present, exact phase telemetry, no hidden warm-up speech memory |
| P5 | Isolated `torch.set_float32_matmul_precision("high")` comparison | Compatible PyTorch candidate, but changes numerical execution | Possible Blackwell Tensor Core speedup without a new package | Same seed/text/reference; valid non-silent WAV; voice identity and owner-hearing comparison; no NaN/Inf or warnings; revert on no material benefit |
| P6 | Preserve full-WAV generation but remove redundant application-side copies/synchronizations only when profiling proves they are material | Narrow audio/control-plane candidate | Small improvement at most; official model already returns CPU audio after watermarking | Per-phase timestamps for model generation, host conversion, postprocess, WAV write, validation, queue, playback; unchanged PCM policy and hashes where applicable |
| M1 | New append-only Chatterbox-Turbo sidecar using the same approved reference | Official model/checkpoint change; weights must be acquired | Best official local model direction for English low-latency agents; smaller model and cheaper decoder | Separate cache and environment evidence; no overwrite; exact reference/profile hashes; standalone and serialized GPU tests; voice identity/perceptual approval; CPU Chatterbox fallback preserved |
| M2 | Chatterbox-Nano evaluation | Official package/source and model change | Smaller 110M option; strongest resource reduction, but potentially larger voice-quality/identity tradeoff | New inactive sidecar, full dependency/Blackwell acceptance, exact-reference voice evaluation, owner approval |
| M3 | FP16/BF16 autocast or explicit dtype conversion | Numerical/model-execution change | Possible speed/VRAM gain; unsupported by Chatterbox's public 0.1.7 API | Isolated only; operator compatibility, waveform quality, voice identity, timing, RAM/VRAM, and clean rollback |

## Not recommended or unsupported

- Do not install an unofficial Triton, FlashAttention, quantization, or streaming fork into the sealed Blackwell environment.
- Do not make `torch.compile` or Inductor mandatory. The accepted eager-CUDA path is the relevant baseline and the current Windows Triton path is unavailable.
- Do not call sentence splitting “streaming.” In the current worker every chunk is generated before the combined WAV is written, so smaller chunks cannot improve first audio and can add pauses and repeated overhead.
- Do not implement fork-derived sliced streaming as a production repair. It is absent from the official 0.1.7 API and requires separate seam, prosody, no-gap, cancellation, and identity acceptance.
- Do not force FlashAttention/SDPA. Allow PyTorch's supported automatic selection; collect the actual selected-path/warning evidence before considering an override.
- Do not lower the private 1000-token ceiling without an official supported interface and truncation tests.
- Do not treat CFG, exaggeration, temperature, top-p, min-p, or repetition penalty as free speed knobs. They affect sampling or delivery and can alter the approved voice experience.
- Do not substitute CPU, SAPI, Nano, Turbo, another speaker, or a generic voice silently.
- Do not interpret Resemble's sub-200ms hosted-service statement as a measured promise for the local open-source 0.1.7 Windows pipeline.

## Smallest next test sequence

1. Patch only the false returned-tensor-device gate and its static tests. Keep all actual GPU proof.
2. Rerun the existing append-only persistent two-WAV acceptance with no Blender or Ollama workload, no playback, and the exact candidate-config hash expected by the harness.
3. Require one load, one conditioning operation, two generations, zero retry, exact approved hashes, readable non-silent PCM16 WAVs, measured CUDA allocation, and clean unload/VRAM return.
4. Use the phase ledger to separate model load, reference conditioning, first generation, second generation, host/audio postprocess, file write, and validation. This establishes the real optimization target.
5. Only if steady-state synthesis remains too slow, run one bounded TF32 comparison. Keep default precision if the gain is not material or if identity/quality differs.
6. Evaluate Turbo later as a separate inactive model candidate; never overwrite or reinterpret the accepted original Chatterbox path.

## Truth boundary

This note identifies compatible experiments and one deterministic acceptance bug. It does not claim that persistent Chatterbox, TF32, Turbo, Nano, streaming, or improved owner-heard latency has passed. Text-model latency is a separate pipeline measurement and is not solved by any TTS-only change.
