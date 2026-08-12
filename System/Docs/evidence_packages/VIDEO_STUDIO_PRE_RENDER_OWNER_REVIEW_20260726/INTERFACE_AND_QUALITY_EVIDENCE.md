# Interface and quality-system evidence

## Live interface

Screenshot:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260726_113809_kira_world_pre_render_owner_review_prompt_and_storyboard_plan_v2_kira_world_pre_re\review\CONCEPT_WORKFLOW_UI.png`

It shows:

- real-runtime rows separated from generated-concept prompt rows;
- selected prompt, purpose, source state, and permanent truth label;
- Approve Prompt, Approve, Reject, Replace, Edit, Lock, Regenerate, Preview;
- Editor Chat instruction for replacing the complete prompt;
- provider pending and no image generated.

Live project status:

`review\PRE_RENDER_CONCEPT_PROMPT_STATUS.json` records provider connected
`false`, images generated `0`, four slots, all `prompt_proposed`.

## Implementation

- `kira_video_studio/concept_image_workflow.py` owns the exact-prompt approval,
  session-only approved-provider registry, permanent disclosure compositing,
  project copy, metadata, SHA-256, and render eligibility.
- `kira_video_studio/project_service.py` exposes audited propose, edit, review,
  generate, and render-gate actions.
- `kira_video_studio/ui.py` displays prompts in the live storyboard and routes
  concept decisions separately from ordinary clips.
- `tests/test_concept_image_workflow.py` proves a provider is not called before
  prompt approval, returned pixels are labeled and hashed, approval is required
  for render, rejection excludes the image, and Editor Chat edits reset approval.

## Audio failure and repair evidence

Rejected X-Men logs:

- `review\REJECTED_audio_full_decode.log` — full audio decode reproduces AAC
  errors and stops around the short audio stream.
- `review\REJECTED_video_full_decode.log` — video decodes to approximately
  20:45.

Cause: incompatible segment audio properties were concatenated with stream
copy. Robert narration was 24 kHz mono while source sections were 44.1 kHz
stereo.

Repair:

- every segment is now AAC 192 kb/s, 48 kHz, stereo;
- final audio is re-encoded rather than copied across incompatible AAC headers;
- `quality_validator.py` independently decodes both streams to EOF, checks
  duration parity, decode errors, silence, repeated source IDs, and missing
  narration.

Verification on 2026-07-26: `python -m unittest discover -s tests -p
'test_*.py'` ran 153 tests in 15.601 seconds: `OK`.

No full replacement video has been rendered. Quality checks passing on code or
fixtures is not owner acceptance of a production.
