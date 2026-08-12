# TemporaryAI Creation Pipeline v1

Purpose: create new TemporaryAI candidates from reviewed source material without mixing them with Kira, Lisa, or Robert's private memories.

## Supported Types

```text
canon_reconstruction_temp_ai
generated_original_temp_ai
expert_temp_ai
memory_relative_temp_ai
```

## Main Tool

```text
tools/create_temporary_ai_candidate.py
Start_TemporaryAI_Candidate_Builder.bat
tools/run_temporary_ai_candidate_probe.py
Start_TemporaryAI_Candidate_Probe.bat
```

The tool creates:

```text
TemporaryAI/candidates/<candidate_id>/creation_request.json
TemporaryAI/candidates/<candidate_id>/temporary_ai_profile.json
TemporaryAI/candidates/<candidate_id>/README.md
TemporaryAI/candidates/<candidate_id>/voice_discovery_request.json
Avatar/temp_ai/<candidate_id>/avatar_profile.json
Avatar/temp_ai/<candidate_id>/avatar_request.json
Avatar/temp_ai/<candidate_id>/online_reference_queue.json
```

Voice metadata discovery's no-download rule is stage-scoped. For a user-authorized file already under `Data/library`, the creator may later use `tools/create_temp_ai_local_media_intake.py` to request exact short voice/movement ranges. See `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md`. Candidate extraction still does not train/clone, assign a voice, activate the candidate, or grant public/official use.

If a source query or source path is supplied, it also creates:

```text
Data/temporary_ai_source_packs/temporary_ai_source_pack_<candidate_id>.draft.json
```

## Examples

Character candidate:

```text
py tools\create_temporary_ai_candidate.py --display-name "Ladybug / Marinette" --ai-type canon_reconstruction_temp_ai --query miraculous_ladybug
```

Expert candidate:

```text
py tools\create_temporary_ai_candidate.py --display-name "STL Body Design Helper" --ai-type expert_temp_ai --expert-domain "3D printable body and joint design"
```

## Boundaries

- Creation does not activate the AI.
- Source material remains evidence, not lived memory.
- Fanfic remains variant-labeled and excluded unless explicitly selected.
- Private adult material is excluded by default.
- Kira/Lisa memories are not available unless a later approved workflow grants specific access.
- Each candidate needs review and a probe before longer use.
- Candidate probes call Ollama directly with the candidate profile/source context. They must not use Kira's conversation loop, because that causes Kira-style/personality leakage into TemporaryAI tests.

## Avatar Link

Every candidate receives an avatar scaffold under `Avatar/temp_ai/<candidate_id>/`. The avatar side is still a draft: references must be reviewed before image generation or 3D modeling.

## Voice Discovery Link

Every new candidate receives a metadata-only voice-discovery request. Candidate creation does not block on a network search and does not download media/model weights or assign a voice.

Run the explicit next action from the TemporaryAI Control Center (**Find Voice Sources (Metadata Only)**) or:

```text
py tools/discover_temporary_ai_voice.py --candidate-id <candidate_id> --metadata-search
```

The command-line builder may combine scaffolding and the metadata pass with `--discover-voice-metadata`. All source, speaker, performer, rights, consent, clean-segment, and listening gates still require review. See `TEMP_AI_AUTOMATIC_VOICE_DISCOVERY_v1.md`.

## 2026-06-05 GPU-Era Smoke Tests

Created and tested:

```text
TemporaryAI/candidates/ladybug_marinette_expanded_smoke/
TemporaryAI/candidates/stl_body_design_helper/
Avatar/temp_ai/ladybug_marinette_expanded_smoke/
Avatar/temp_ai/stl_body_design_helper/
```

Probe results:

```text
Data/personhood_evaluations/temporary_ai_candidate_probes/temp_ai_candidate_probe_stl_body_design_helper_20260605_142001.monitor.md
Data/personhood_evaluations/temporary_ai_candidate_probes/temp_ai_candidate_probe_ladybug_marinette_expanded_smoke_20260605_142054.monitor.md
```

The STL expert probe stayed in its expert domain. The Ladybug/Marinette probe stayed source-bounded and did not claim lived memory. Both remain drafts, not activated residents.
