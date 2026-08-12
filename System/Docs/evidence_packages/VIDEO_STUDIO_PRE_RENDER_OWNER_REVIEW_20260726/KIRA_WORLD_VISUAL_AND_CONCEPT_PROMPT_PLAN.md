# Kira World visual plan and proposed concept prompts

## Evidence-first visual plan

| Chapter | Current evidence and motion | Asset class / gate |
|---|---|---|
| Opening / Kira World | Real Home World movement capture to be recorded in one continuous take; project map animates only verified modules | `runtime_evidence`; screen recording must be selected by Robert |
| Home World | `C:\Users\robmc\Kira\_tmp_home_world_latest_runtime_verify\screenshots\01_initial.png`, `02_reading_with_book.png`, `03_capture_flag_practice.png`, `04_run_practice.png`; 6–8s pan/zoom each; verified-room map | `runtime_evidence`; exact capture dates visible |
| Kira | `C:\Users\robmc\Kira\Data\world_tests\kira_socket_eye_v3_3_20260722\fresh_validation_ephemeral_20260723_0554\center.png`, `look_left.png`, `look_right.png`, `look_up.png`, `look_down.png`; five-frame comparison | `runtime_evidence`; do not imply whole-avatar completion |
| Lisa | Current Lisa artifact search and owner selection required; no substitution | `missing_runtime_evidence`; blocks chapter approval, not filled by concept |
| TemporaryAI | Redacted audit excerpts plus three-channel spoken/private/runtime animation | `documentary_evidence`; no candidate/person media |
| World Builder | Record actual workspace edit, reload, and result; before/after split | `runtime_evidence`; source capture pending |
| Avatar Builder | Current surface-trial and eye evidence; clothing failure before/after held on same pose | `runtime_evidence`; no flattering-only selection |
| Video Studio | `CONCEPT_WORKFLOW_UI.png`; select real evidence then prompt slot; show controls | `runtime_evidence` of Studio |
| Completed / failed / limits | Animated evidence timeline populated from manifests and rejected-package status | `documentary_evidence`; failed state preserved |
| Future | Show prompt cards in live Studio until Robert approves generation | `generated_concept` prompts only; images generated: zero |

## Proposed prompt slots

The full exact text is stored in the live project’s
`assets.concept_image_slots`. Summary:

1. `concept-home-world-lived-future` — a coherent lived-in future Home World
   with Kira and Lisa; not a collage.
2. `concept-temporary-ai-gated-workflow` — owner-scoped request, rights check,
   owner approval, build, inactive-until-invited.
3. `concept-integrated-creative-studio` — connected World Builder, Avatar
   Builder, and Video Studio workspace.
4. `concept-avatar-clothing-goal` — layered garment fit, collision, drape,
   pose-stress, and owner review.

Every prompt reserves the lower 12 percent for Video Studio to bake in the
exact permanent label `CONCEPT — NOT CURRENT FUNCTIONALITY`. The provider is
not trusted to draw the disclosure; the Studio composites it into returned
pixels and hashes that labeled file.

## Decision lifecycle

`prompt_proposed → prompt_approved → generated_awaiting_review → approved → locked`

Alternate states `prompt_edited`, `rejected`, `replace_requested`, and
`generation_failed` are non-renderable. Editing a prompt resets prompt approval.
Regeneration is blocked while locked. A returned image is copied beneath
`visual_candidates/generated_concepts/<slot>/`, and its provider, model, exact
prompt, UTC date, purpose, project-relative path, and SHA-256 are retained.
