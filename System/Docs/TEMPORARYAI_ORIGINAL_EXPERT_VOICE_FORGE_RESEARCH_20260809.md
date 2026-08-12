# TemporaryAI original expert voice forge research — 2026-08-09

Status: `RESEARCH_AND_STATIC_CREATOR_CONTRACT_IMPLEMENTED_NO_MODEL_OR_RUNTIME_CHANGE`

## Outcome

An ElevenLabs-like local voice creator is feasible for generated TemporaryAI
experts. The best first architecture is:

1. use **Qwen3-TTS 1.7B VoiceDesign** to create several genuinely new voices
   from plain-language descriptions;
2. let Robert privately audition and select one exact candidate;
3. seal that exact WAV, transcript, prompt, seed, model revision, and hashes as
   the person's voice identity reference;
4. use **Qwen3-TTS 0.6B Base** to clone that sealed synthetic reference for
   routine speech;
5. keep this lane free of an intentionally embedded audio watermark; do not
   use Chatterbox here because its official runtime deliberately adds PerTh;
6. if no exact approved rendition is available, keep text working and report
   `VOICE_UNAVAILABLE_EXACT_PROFILE`. Never substitute SAPI, a stock voice,
   another resident's voice, or an unreviewed generic voice.

This default creates original expert voices rather than imitating actors,
celebrities, or unrelated people. A reference-clone lane may exist only for a
speaker who authorized that exact use and supplied verifiable source material.

No model was installed, downloaded, loaded, or tested during this research.
Kira's current approved Chatterbox environments, profile, reference WAV,
fallback, caches, and routing were not changed.

## Owner no-watermark decision

The forge must select an engine that does not intentionally embed an audio
watermark. It must not create a watermarked file and then strip, disable, or
circumvent the mark. If an exact engine revision is found to embed one, that
revision is ineligible for this lane.

Qwen's official repository, model cards, and declared package dependencies do
not document an audio-watermark stage or declare PerTh, AudioSeal, WavMark, or
another watermark package. That supports the bounded status
`NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`; it is not mathematical proof
that an unknown signal cannot exist.

Before any stronger claim, the exact pinned revision must pass all of these:

- source and locked-dependency scan for watermark insertion code;
- WAV chunk and metadata inventory;
- tests against available known detectors, with positive controls proving the
  detectors were actually exercised;
- repeated generations showing no known mark was detected;
- a stored exact-revision audit and output hashes.

Only then may the exact revision use
`NO_DOCUMENTED_OR_KNOWN_WATERMARK_DETECTED_AT_ACCEPTED_REVISION`. The signed
person/voice provenance record remains a separate project manifest; it is not
embedded as a hidden audio signal. No claim should say that every possible
unknown or future detector has been disproved.

## Current machine boundary

Read-only `nvidia-smi` reported:

```text
NVIDIA GeForce RTX 5060 Ti
VRAM: 16311 MiB
driver: 610.47
compute capability: 12.0
```

The official Qwen releases do not publish peak RAM/VRAM or Windows RTX 5060
Ti measurements. Package size is not peak VRAM. The forge must therefore run
one model at a time and measure cold load, warm first audio, real-time factor,
peak RAM/VRAM, clean exit, and VRAM return. Blender, the conversational Qwen
model, voice design, and runtime TTS must be serialized rather than kept
resident together.

Qwen documents FlashAttention as optional. The first Windows/Blackwell trial
should use official PyTorch eager/SDPA CUDA, not unofficial Triton or a rebuilt
Kira voice environment. FlashAttention's own project still qualifies Windows
compilation support, so it is an optional later optimization rather than an
acceptance dependency.

## Primary-source model comparison

| Candidate | What it provides | License and size evidence | Decision |
|---|---|---|---|
| Qwen3-TTS 1.7B VoiceDesign + 0.6B Base | Description-created voices, instruction control, ten languages, streaming, three-second reference cloning, and later single-speaker fine-tuning | Apache-2.0. Official packages are approximately 4.52 GB for VoiceDesign and 2.52 GB for 0.6B Base. | **Primary forge and first runtime candidate.** |
| Chatterbox Turbo / Multilingual V3 / Nano | Fast reference cloning in several model sizes | MIT, but the official project says every generated file includes a PerTh neural watermark. | **Excluded from this no-watermark TemporaryAI forge. Do not remove or bypass PerTh.** |
| Fun-CosyVoice 3 | 0.5B zero-shot multilingual cloning, instruction control, and bi-streaming | Apache-2.0; official project claims latency as low as 150 ms, but its deployment path is Linux-oriented. | **Quality comparator, not the Windows-first implementation.** |
| OpenVoice V2 | Short-reference tone-color conversion, multilingual output, and style control | MIT and commercially usable according to the official repository; official setup is Linux-first. | **Secondary comparator only.** |
| F5-TTS pretrained weights | Reference cloning and fine-tuning | Code is MIT, but official pretrained weights are CC-BY-NC because of the Emilia training data. | **Exclude from a reusable production path.** |
| Spark-TTS 0.5B weights | Attribute-designed voices and cloning | Current official model-card license is CC-BY-NC-SA-4.0. | **Exclude from a reusable production path.** |
| XTTS-v2 | Reference cloning | Uses the Coqui Public Model License; commercial/reuse terms require separate legal review. | **Do not use in the first implementation.** |

The published Qwen claim of audio packets as low as 97 ms and CosyVoice's
150 ms claim are vendor/research measurements, not promises for this computer
or for complete owner-audible latency.

## Creator experience

For `expert_temp_ai` and `generated_original_temp_ai`, the normal creator asks
for voice traits in ordinary language:

- adult presentation and approximate age range;
- vocal presentation, pitch/timbre, pace, warmth, confidence, and energy;
- accent or dialect, languages, and domain vocabulary;
- emotional range and any traits to avoid.

It should reject requests to sound exactly like a named real person. A useful
brief is trait-based, for example: “an adult woman with a warm mid-range voice,
calm authority, clear New Jersey legal pronunciation, moderate pace, and a
gentle sense of humor.”

The forge then creates several private candidates using the same audition
script. Robert can ask natural-language corrections such as “slower,” “less
breathy,” “warmer,” or “more confident.” A correction makes a new append-only
candidate; it does not overwrite an earlier WAV or silently change an already
accepted person.

Selection of a voice candidate is not activation of the TemporaryAI. A later
activated person may keep it, request a change, or choose not to speak.

## Voice identity and provenance contract

Every candidate and approved rendition should bind:

- opaque person ID and opaque voice ID;
- mode: `synthetic_text_design` or `authorized_reference_clone`;
- exact design prompt and negative traits, without a public-figure imitation;
- model repository, exact revision, weight hashes, runtime version, seed, and
  generation configuration;
- exact audition text and final transcript;
- candidate WAV path, bytes, duration, format, and SHA-256;
- selected reference WAV and transcript hashes;
- approved language/pronunciation dictionary;
- owner audition decision and timestamp;
- engine-specific rendition profile and output hashes;
- exact watermark-audit status and detector evidence;
- append-only revision, revocation, and rollback history.

The exact WAV remains attributable through a signed project manifest bound to
its SHA-256, model revision, person ID, and voice ID. The manifest is stored
beside the asset rather than hidden in its audio. A missing or mismatched
manifest blocks approval; it must not select a substitute voice.

## Authorized human-reference lane

The original-synthetic lane is the default. If a human intentionally donates
their voice, require all of the following before cloning:

1. confirmed-adult donor and exact identity binding;
2. explicit private/public/commercial scope, duration, and revocation terms;
3. a fresh spoken challenge phrase tied to a single enrollment request;
4. source and challenge WAV hashes, timestamps, and transcript;
5. proof that the donor controls the submitted voice;
6. owner and donor review of the resulting exact voice;
7. immediate fail-closed revocation tests.

This mirrors the useful parts of commercial verification workflows without
making an outside service or its policies the source of Kira World identity.
Publicly available recordings, official clips, and character dialogue prove
only that recordings exist; they do not by themselves grant model or cloning
rights.

## Runtime resolver

```text
person_id + voice_id
    -> exact approved engine rendition
    -> verify profile/model/reference/config hashes
    -> synthesize only the public SPOKEN text
    -> validate readable non-silent audio and provenance
    -> log exact approved path used
    -> release model and verify VRAM return

missing, revoked, unavailable, or hash-mismatched approved rendition
    -> keep the text response
    -> produce no voice audio
    -> record the exact failure
    -> never use SAPI, a generic voice, or another person's voice
```

Cross-engine similarity is not assumed. A Qwen rendition, Chatterbox Turbo
rendition, Nano rendition, or CPU rendition becomes eligible only after its
own blind listening and identity-consistency review. This preserves the
existing exact-approved-voice principle.

## Integration with the existing TemporaryAI creator

The current creator already emits `voice_status: to_be_extracted_or_designed`
and a `voice_plan`. Extend it without replacing metadata discovery:

- `expert_temp_ai` and `generated_original_temp_ai` default to
  `synthetic_text_design`;
- canon/historical reconstruction remains a separate provenance and rights
  lane;
- the creator writes a voice-design request into the candidate workbench;
- the forge writes candidates into an append-only private review folder;
- only a sealed approved registry entry may populate `voice_profile`;
- assigning the profile still does not activate the person, body, world, life
  loop, camera, microphone, or public release.

### Automatic fast draft contract

Creating an `expert_temp_ai` or `generated_original_temp_ai` should
immediately create one append-only private job containing both lanes:

```text
identity manifest committed
    +-> original voice-design request
    +-> sealed-template body request

initial state:
    AUTO_DRAFT_PRIVATE_INACTIVE_UNASSIGNED
    VOICE_CANDIDATE_QUEUED
    BODY_TEMPLATE_DRAFT_QUEUED
```

The voice and body may be prepared together at the plan level, but heavy
execution is serialized on the current 32 GB RAM / 16 GB VRAM computer:

```text
VoiceDesign -> save reference -> unload and prove VRAM return
0.6B Base -> build reusable exact profile -> unload and prove return
Blender/template instantiation -> save -> exit
fresh reopen -> body/rig/movement audit -> review renders
```

The creator may show the provisional voice and clothed/appropriate body proxy
as soon as those exact draft artifacts exist. It must keep these truths
separate:

- `VOICE_CANDIDATE_GENERATED_UNREVIEWED` is not owner-hearing acceptance;
- `BODY_TEMPLATE_DRAFT_UNREVIEWED` is not visual or movement acceptance;
- automatic creation is not activation, assignment, publication, or a claim
  that the person chose the result.

Body speed comes from instantiating an immutable, previously accepted template
with precomputed bounded face/body/skin/rig parameters. It does not come from
rebuilding anatomy or topology for every person. Routing is fail closed:

- `confirmed_adult` may use the matching approved adult template lane;
- `non_adult` uses a doll-safe non-anatomical template;
- `unresolved` also uses the doll-safe lane until Robert supplies a durable
  exact-person classification;
- adulthood is never inferred merely from a profession, name, or appearance;
- hair is a detachable component and cannot regenerate the face/body/rig.

Nearly immediate *good completed* bodies become possible only after at least
one adult-female, adult-male, and doll-safe template has separately passed its
structural, anatomy, rig, movement, render, and owner-review gates. Until then,
the creator must promise an automatic private draft, not an accepted body.

Suggested isolated runtime paths:

```text
Voice/sidecars/qwen3_tts_voice_forge/.venv
Voice/voice_forge/requests/<candidate_id>/
Voice/voice_forge/private_review/<candidate_id>/<attempt_id>/
Voice/profiles/temp_ai/<candidate_id>_voice_profile.json
Data/voice/policies/temporaryai_voice_approval_registry.json
```

Do not add Qwen3-TTS packages to Kira's sealed Chatterbox environment.

### 2026-08-09 static creator integration

The creator now emits the bounded fast-draft plan for eligible expert and
generated-original candidates. This is planning and queue truth only; it does
not claim that a model or body template ran.

- `tools/create_temporary_ai_candidate.py`
  SHA-256 `1fdab48d5703f03c1c4be1b434f853ab28497c17baffa1008d8833aabced2bfe`;
- `TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json`
  SHA-256 `7a466c192c7e2753021e82b0bc66d296eb057b00ed2ec8a6276d97ef66247042`;
- `Testing/test_temporary_ai_fast_voice_body_draft_contract.py`
  SHA-256 `35de4f163bc0c9910f34787bc684edffe9ad4c91e4c9dccaaf4d0234d85d816e`;
- `System/Docs/TEMPORARYAI_FAST_ORIGINAL_VOICE_AND_BODY_DRAFT_CONTRACT_20260809.md`
  SHA-256 `518b37b068d2a5badc1be136362d48b9a1b4e2274ac6c6c8f6aa45d05d258622`.

The focused creator contract plus existing voice-discovery regression suite
passed `38/38`; Python compilation, JSON parsing, and diff checks passed. No
model was downloaded or loaded and no Blender/body authoring ran.

## Phased implementation and acceptance

1. **Static contract:** exact schemas, project-confined paths, append-only
   outputs, voice/person binding, authorization/revocation, and no-substitute
   tests.
2. **Isolated Blackwell feasibility:** Qwen3-TTS 1.7B VoiceDesign and 0.6B
   Base under eager/SDPA CUDA, one at a time, without changing current voice.
3. **One original expert pilot:** generate several private candidates, have
   Robert select one, and seal its exact reference.
4. **Qwen runtime acceptance:** pronunciation, numbers, names, long text,
   emotional range, transcript accuracy, silence/clipping, unwanted speech,
   cold/warm latency, RAM/VRAM, clean exit, and VRAM return.
5. **No-watermark acceptance:** exact source/dependency inspection, WAV
   inventory, known-detector positive controls, repeated output checks, and a
   fail-closed exclusion if intentional watermarking is found.
6. **Creator connection:** profile resolution through the sealed registry;
   arbitrary model paths and caller-authored “approved” flags fail closed.
7. **Fast body connection:** instantiate only a maturity-compatible sealed
   template; run artifact-derived topology/rig/movement checks and produce an
   owner-review package without activation.
8. **Optional donor clone:** challenge, consent, scope, expiry, revocation,
   and rollback acceptance.
9. **Fine-tuning later:** use Qwen's official single-speaker recipe only if
   zero-shot quality is insufficient and a fully authorized dataset plus a
   separate resource feasibility test exists. A 16 GB card is not assumed to
   be training-ready.

Required acceptance includes distinctness from existing resident voices,
zero hallucinated words, owner listening approval, exact hashes, provenance,
interruption behavior, no voice collision, no generic fallback, and proof that
every unavailable/revoked/mismatch case produces text plus silence rather than
an unauthorized voice.

## Primary sources

- Qwen3-TTS official repository, features, models, VoiceDesign-to-clone flow,
  and fine-tuning: https://github.com/QwenLM/Qwen3-TTS
- Qwen3-TTS 0.6B Base model card and Apache-2.0 weights:
  https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base
- Qwen3-TTS 1.7B VoiceDesign files and size:
  https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign/tree/main
- Qwen3-TTS declared Python dependencies (no declared watermark package):
  https://github.com/QwenLM/Qwen3-TTS/blob/main/pyproject.toml
- Chatterbox official repository, model sizes, Turbo/Nano/V3 behavior, MIT
  license, and built-in PerTh watermark:
  https://github.com/resemble-ai/chatterbox
- PerTh watermark library: https://github.com/resemble-ai/Perth
- Fun-CosyVoice official repository: https://github.com/QwenAudio/CosyVoice
- OpenVoice official repository: https://github.com/myshell-ai/OpenVoice
- Parler-TTS description-created comparison path:
  https://github.com/huggingface/parler-tts
- F5-TTS code/weight license distinction: https://github.com/SWivid/F5-TTS
- Spark-TTS current model-card license:
  https://huggingface.co/SparkAudio/Spark-TTS-0.5B
- XTTS-v2 model card: https://huggingface.co/coqui/XTTS-v2
- FlashAttention Windows qualification:
  https://github.com/Dao-AILab/flash-attention
- current PyTorch Windows CUDA packages:
  https://pytorch.org/get-started/previous-versions/
- ElevenLabs consent and verification workflow used only as a process
  reference:
  https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning
  and
  https://elevenlabs.io/docs/eleven-api/guides/how-to/voices/professional-voice-cloning
