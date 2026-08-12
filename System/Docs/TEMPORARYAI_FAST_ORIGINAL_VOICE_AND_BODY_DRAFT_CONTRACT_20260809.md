# TemporaryAI fast original voice and body draft contract

Date: 2026-08-09

Status: **static creator integration implemented; no model, voice, Blender, or
body-template execution was run by this change.**

Machine contract:
`TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json`

## Owner-facing result

Creating an `expert_temp_ai` or `generated_original_temp_ai` now also writes an
immediate private fast-build queue for an original voice and body draft. The
truthful initial status is:

`AUTO_DRAFT_PRIVATE_INACTIVE_UNASSIGNED`

Validation is separately recorded as:

`ASYNC_VALIDATION_QUEUED_NOT_RUN`

This makes the draft immediate without falsely describing a generated voice or
completed body. Canon reconstructions, historical-person provenance, and
memory-relative candidates remain on their existing separate lanes.

## Original offline voice lane

The proposed local sequence is deliberately bounded to one heavy GPU model at
a time:

1. Qwen3-TTS 1.7B VoiceDesign creates an original synthetic voice from reviewed
   text traits; it does not clone a named real person or existing resident.
2. The VoiceDesign model unloads and VRAM release is verified.
3. Qwen3-TTS 0.6B Base derives and validates the exact smaller offline runtime
   profile from that original reference.
4. The Base model unloads and VRAM release is verified.

After the models are locally installed and cached, normal synthesis is intended
to run offline. Installation, Blackwell/Windows acceptance, generated-audio
acceptance, and owner hearing approval have not yet occurred.

The precise initial watermark truth is:

`NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`

This means only that the reviewed Qwen3-TTS upstream documentation did not
document an intentional audio watermark. It is **not** a detector-backed claim
that no watermark-like signal is present. A stronger status requires pinned
official source and license records, dependency/model hashes, a representative
generated-audio detector corpus, and owner hearing acceptance.

Chatterbox is excluded from this no-watermark lane because its official runtime
includes PerTh watermarking. Nothing in this contract removes, disables,
evades, or conceals a watermark. If the exact approved voice is unavailable or
mismatched, the person keeps text and produces silence; a generic voice or
another person's voice is never substituted.

## Parallel body lane

The body draft is queued alongside voice validation but may instantiate only
from a future sealed template plus bounded precomputed parameters. It may not
use unbounded freeform body generation in the fast lane.

The template selector is fail-closed:

- `confirmed_adult` -> `CONFIRMED_ADULT_SEALED_TEMPLATE`
- `non_adult` -> `DOLL_SAFE_NON_ANATOMICAL_SEALED_TEMPLATE`
- `unresolved` -> `DOLL_SAFE_NON_ANATOMICAL_SEALED_TEMPLATE`

Adulthood is never inferred. Until qualifying sealed templates actually exist,
the body remains a template-blocked draft and the creator cannot call it a
completed high-quality body.

Scalp hair is a detached, separately versioned module. Adding, removing, or
changing hair must not regenerate the accepted face, body, rig, weights, skin,
or movement. Hair attachment remains subject to its own runtime acceptance.

## Acceptance boundary

Neither lane activates or assigns a person, loads a body into a world, publishes
or uploads an artifact, or alters Kira's approved voice/body assets. Body
acceptance later requires a sealed template hash/version, maturity-route proof,
structural/nonintersection checks, movement/contact checks, private multiview
renders, and Robert's visual decision.

The creator CLI accepts an explicit `--confirmed-maturity` value. Omitting it
means `unresolved` and therefore doll-safe non-anatomical routing. The existing
`--no-avatar` option remains an explicit opt-out: the body plan is still
recorded, but its execution status says it was not queued.

## Static verification

Focused tests verify:

- both eligible original lanes receive the automatic voice/body draft;
- canon and memory-relative lanes do not receive it;
- the exact Qwen sequence and qualified watermark status;
- Chatterbox exclusion without removal/circumvention;
- text-plus-silence mismatch behavior;
- explicit-adult versus fail-closed doll-safe body routing;
- detached hair and zero activation/assignment/publication claims;
- truthful template-blocked and asynchronous-validation states.

