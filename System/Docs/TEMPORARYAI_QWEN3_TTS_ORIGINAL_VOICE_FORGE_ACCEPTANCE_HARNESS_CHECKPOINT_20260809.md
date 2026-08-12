# TemporaryAI Qwen3-TTS original voice forge acceptance harness checkpoint — 2026-08-09

Status:
`INERT_FAIL_CLOSED_HARNESS_IMPLEMENTED_AND_MOCK_ACCEPTED_REAL_MODEL_EXECUTION_NOT_RUN`

## Outcome

The next bounded implementation step for the TemporaryAI original expert voice
forge is complete. The creator's eligible `expert_temp_ai` and
`generated_original_temp_ai` queue metadata now points to one isolated,
hash-bound acceptance launcher and worker. The implementation follows the
official Qwen3-TTS Voice Design then Clone sequence:

1. `Qwen3TTSModel.from_pretrained` loads the exact local 1.7B VoiceDesign
   directory using ordinary eager CUDA, `torch.bfloat16`, and SDPA;
2. `generate_voice_design` creates the exact trait-described reference text;
3. VoiceDesign unloads and VRAM return is measured before another model loads;
4. `Qwen3TTSModel.from_pretrained` loads the exact local 0.6B Base directory;
5. `create_voice_clone_prompt` creates the reusable exact local prompt;
6. `generate_voice_clone` produces the exact test text;
7. Base unloads and final VRAM return is measured.

The official API reference is the QwenLM/Qwen3-TTS README section “Voice
Design then Clone”:
https://github.com/QwenLM/Qwen3-TTS#voice-design-then-clone

No Qwen3-TTS model, dependency, environment, or model weight was downloaded,
installed, imported, loaded, or run during this task. No Chatterbox file,
environment, model, cache, profile, reference, or route was changed.

## Inert execution boundary

The launcher and worker do nothing without all explicit execution gates:

- `--execute`;
- exact contract SHA-256;
- exact job SHA-256;
- exact worker SHA-256;
- exact environment-spec SHA-256;
- explicit private/unreviewed acknowledgement;
- explicit no-download acknowledgement.

A future real run additionally requires the exact isolated interpreter at
`Voice/sidecars/qwen3_tts_voice_forge/.venv/Scripts/python.exe`, an environment
spec changed through separate review to `ACCEPTED_READY_FOR_BOUNDED_OFFLINE_RUN`,
and pinned accepted official Windows Blackwell Torch and Torchaudio wheels.
The current environment spec deliberately remains
`SPECIFIED_NOT_CREATED_OR_INSTALLED`; Torch and Torchaudio remain pending.

The restricted child environment sets Hugging Face and Transformers offline,
uses exact local model directories, disables user-site packages, requires
`CUDA_VISIBLE_DEVICES=0`, and does not copy the complete parent environment.
The runtime never invokes `torch.compile`, Triton, or FlashAttention and never
uses a model repository ID as an executable path.

## Identity, privacy, and failure behavior

This harness accepts only
`ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE` jobs with an
`original_trait_description` identity basis. It rejects both an explicit
named-real-person flag and common imitation language such as “sound exactly
like.” An authorized human-donor reference is a different future harness and
is not accepted here.

Every output is candidate-bound, private, append-only, inactive, unassigned,
unpublished, and unuploaded under:

`Voice/voice_forge/private_review/<candidate_id>/attempt_NN/`

Any missing path, hash drift, incomplete model inventory, identity mismatch,
unreadable/silent WAV, missing CUDA allocation, telemetry failure, unload
failure, or process failure records
`FAILED_TEXT_PLUS_SILENCE_ONLY`. Generic voice, SAPI, another person's voice,
or a current-route change is forbidden.

The worker writes only mono PCM16 WAV evidence and validates duration, sample
rate, peak, and RMS. It records exact design-traits, reference-text, and
test-text hashes; exact model manifest revisions/hashes; reference, clone
prompt, test WAV, profile, and manifest hashes; model-load, design, prompt,
clone, unload, and process timing; peak process RAM; baseline/peak/intermediate/
final CUDA allocated and reserved bytes; serial lifecycle events; and owner
hearing status. A worker engineering pass remains
`OWNER_HEARING_PENDING` and cannot assign a voice.

## Watermark truth

The default bounded status remains:

`NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`

The worker permits the stronger exact-revision status only when the job binds
explicit source/dependency scans, WAV inventory, named detectors with evidence
hashes, detector positive controls, repeated generated samples with no known
mark detected, and owner hearing acceptance:

`NO_DOCUMENTED_OR_KNOWN_WATERMARK_DETECTED_AT_ACCEPTED_REVISION`

It never claims that every unknown signal is absent. It contains no watermark
removal, disabling, evasion, concealment, or circumvention path.

## Exact implementation inventory

- `tools/create_temporary_ai_candidate.py`
  SHA-256 `1ed3be42609480b91e86530679222f99fa0728bf81279dd00b01050e874b11dc`
- `TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json`
  SHA-256 `8df20b6fbd8b5432a644ae46e8d034016107118fe1c64e10f63bd025b3e92450`
- `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json`
  SHA-256 `0698556f366400e4105fd85f8610e1cefcb2d28bf29456440496c44100865a4f`
- `Voice/sidecars/qwen3_tts_voice_forge/environment_spec_v1.json`
  SHA-256 `1c9691a669292dae7b402c584e29ad728a2f52af977d50a59b7591e11243f2ad`
- `Voice/sidecars/qwen3_tts_voice_forge/core_requirements_v1.txt`
  SHA-256 `36cf7fa94b6085cb27725d8ebc5d2d321fbded633bf5f74872cd93a7347bb1fd`
- `TemporaryAI/templates/qwen3_tts_original_voice_forge_job_v1.json`
  SHA-256 `cdc84bb985d2c2238cc4fdf69edea07e2e89ed74a2e3bc2d0f0704ccf1c79e08`
- `tools/qwen3_tts_original_voice_forge_worker.py`
  SHA-256 `0aa283d2eaa718c791b9db24205acc3e8332e1a65e3b333023a72d13fb421ece`
- `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance.py`
  SHA-256 `a2fa5ef58c95e37c50a336d60364cd56e06d150e030592c96914a0d0d33d1c85`
- `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance.py`
  SHA-256 `98742fb01702287c9e5b194195e2d021c16564926c90a8c53f85fb2803bee943`

## Verification

Focused Qwen3-TTS forge tests:

`py -B -m unittest -q Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance`

Result: `25/25 PASS`.

Combined focused forge, fast-draft creator, and existing TemporaryAI voice
discovery regression tests:

`py -B -m unittest -q Testing.test_temporary_ai_fast_voice_body_draft_contract Testing.test_temp_ai_voice_discovery Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance`

Result: `63/63 PASS`.

Python compilation passed for the creator, worker, runner, and focused test.
All four JSON artifacts parsed successfully. The touched files contain no
trailing whitespace.

The mock acceptance produced two real temporary PCM16 WAV files solely inside
an automatically deleted test sandbox. It proved the exact model lifecycle,
GPU allocation gate, RAM/VRAM telemetry, append-only refusal, profile/manifest
hashes, and readable/non-silent validation. A separately injected clone failure
preserved its traceback and proved text plus silence with no substitute voice.
It did not constitute model, audio-quality, detector, or owner-hearing
acceptance.

## Remaining bounded work

1. Select and pin an official Windows Torch/Torchaudio wheel pair with RTX
   5060 Ti / compute-capability 12.0 support in this new isolated environment.
2. Create the isolated environment without touching any Chatterbox sidecar.
3. Acquire and hash the exact official Qwen model revisions into the two local
   directories, then create complete file manifests.
4. Run one static source/dependency watermark audit before requesting the
   stronger status.
5. Prepare one trait-only expert job with exact text hashes.
6. Run one bounded private engineering attempt and preserve all evidence.
7. Obtain Robert's private hearing decision before any registry assignment.

## Rollback

No runtime rollback is needed because no runtime changed. To remove this static
step, delete only the new acceptance contract, isolated environment
specification directory, job template, worker, runner, focused test, and this
checkpoint; then remove only `acceptance_worker_metadata` and the four new
Qwen3-TTS forge path constants from `tools/create_temporary_ai_candidate.py`,
and remove only `voice_lane.acceptance_worker_metadata` from the fast-draft
contract. Do not alter any candidate, current voice, Chatterbox sidecar,
profile, model cache, or prior evidence.
