"""
Create a GPU-era TemporaryAI candidate scaffold.

This tool does not activate the AI, download web images, or generate a 3D body.
It creates the reviewable files needed to build character, expert, generated,
or memory-relative TemporaryAIs and gives the avatar builder a matching target.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plan_temp_ai_source_pack import build_pack


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery import build_candidate_voice_discovery_request, run_candidate_discovery
from Core.temporary_ai_creator_quality_v2 import (
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    PRIVATE_LIFECYCLE_STATUS,
    build_static_quality_record,
    evidence_bound_maturity_status,
    load_canonical_quality_record,
    quality_record_evidence_file_issues,
    quality_record_issues,
    write_quality_revision_exclusive,
)

DEFAULT_INDEX_PATH = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
REGISTRY_PATH = PROJECT_ROOT / "config" / "ai_type_registry.json"

VALID_AI_TYPES = {
    "canon_reconstruction_temp_ai",
    "generated_original_temp_ai",
    "expert_temp_ai",
    "memory_relative_temp_ai",
}

FAST_ORIGINAL_BUILD_AI_TYPES = {
    "expert_temp_ai",
    "generated_original_temp_ai",
}
QUALITY_V2_AI_TYPES = {
    "canon_reconstruction_temp_ai",
    "expert_temp_ai",
}
VALID_CONFIRMED_MATURITY = {
    "confirmed_adult",
    "non_adult",
    "unresolved",
}
FAST_BUILD_CONTRACT_PATH = (
    "TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json"
)
QWEN3_TTS_FORGE_ACCEPTANCE_CONTRACT_PATH = (
    "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json"
)
QWEN3_TTS_FORGE_RUNNER_PATH = (
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance.py"
)
QWEN3_TTS_FORGE_WORKER_PATH = "tools/qwen3_tts_original_voice_forge_worker.py"
QWEN3_TTS_FORGE_ENVIRONMENT_SPEC_PATH = (
    "Voice/sidecars/qwen3_tts_voice_forge/environment_spec_v1.json"
)
AUTO_DRAFT_STATUS = "AUTO_DRAFT_PRIVATE_INACTIVE_UNASSIGNED"
ASYNC_VALIDATION_STATUS = "ASYNC_VALIDATION_QUEUED_NOT_RUN"
NO_DOCUMENTED_WATERMARK_STATUS = "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK"
SAFE_CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "temporary_ai"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_utc_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_json_exclusive(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_text_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text.rstrip() + "\n")


def _quality_input_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _require_resolved_under(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"candidate output escapes its fixed project root: {path}") from exc


def build_creator_quality_v2(
    args: argparse.Namespace,
    *,
    candidate_id: str,
) -> dict[str, Any]:
    """Load an exact canonical record or make an honestly blocked inert skeleton."""

    supplied_path = str(getattr(args, "quality_record", "") or "").strip()
    expected_variant = (
        "expert"
        if args.ai_type == "expert_temp_ai"
        else str(getattr(args, "variant_kind", "fictional") or "fictional")
    )
    if supplied_path:
        record = load_canonical_quality_record(_quality_input_path(supplied_path))
    else:
        recorded_at = str(
            getattr(args, "maturity_recorded_at_utc", "") or now_utc_z()
        )
        maturity_status = str(
            getattr(args, "confirmed_maturity", "unresolved") or "unresolved"
        )
        identity = {
            "candidate_id": candidate_id,
            "display_name": args.display_name,
            "identity_classification": (
                "generated_original_expert"
                if args.ai_type == "expert_temp_ai"
                else f"synthetic_{expected_variant}_variant"
            ),
            "canonical_identity": str(
                getattr(args, "canonical_identity", "") or args.display_name
            ),
            "source_continuity": str(getattr(args, "source_continuity", "") or ""),
            "source_version": str(getattr(args, "source_version", "") or ""),
            "source_timepoint": str(getattr(args, "source_timepoint", "") or ""),
            "branch_point": str(getattr(args, "branch_point", "") or ""),
            "appearance_selected_identity": False,
            "model_guess_selected_identity": False,
            "appearance_selected_continuity": False,
            "model_guess_selected_continuity": False,
            "appearance_selected_timepoint": False,
            "model_guess_selected_timepoint": False,
            "maturity_classification": {
                "subject_id": candidate_id,
                "maturity_status": maturity_status,
                "classification_id": str(
                    getattr(args, "maturity_classification_id", "")
                    or f"{candidate_id}_maturity_v1"
                ),
                "authority_kind": str(
                    getattr(args, "maturity_authority_kind", "")
                    or "exact_subject_owner_classification"
                ),
                "evidence_path": str(
                    getattr(args, "maturity_evidence_path", "") or ""
                ),
                "evidence_sha256": str(
                    getattr(args, "maturity_evidence_sha256", "") or ""
                ),
                "recorded_at_utc": recorded_at,
                "appearance_observation_used": False,
                "model_guess_used": False,
                "body_observation_used": False,
                "voice_observation_used": False,
                "classification_is_body_or_activation_approval": False,
            },
        }
        record = build_static_quality_record(
            candidate_id=candidate_id,
            display_name=args.display_name,
            ai_type=args.ai_type,
            variant_kind=expected_variant,
            created_at_utc=now_utc_z(),
            identity_binding=identity,
            expert_domain=str(getattr(args, "expert_domain", "") or ""),
        )

    exact_expectations = {
        "candidate_id": candidate_id,
        "display_name": args.display_name,
        "ai_type": args.ai_type,
        "variant_kind": expected_variant,
        "revision": 1,
    }
    for field, expected in exact_expectations.items():
        if record.get(field) != expected:
            raise ValueError(f"quality record exact mismatch for {field}")
    if args.ai_type == "expert_temp_ai":
        requested_domain = str(getattr(args, "expert_domain", "") or "")
        if requested_domain and record.get("expert_domain") != requested_domain:
            raise ValueError("quality record exact mismatch for expert_domain")
    declared_gate_errors = [
        issue
        for issue in quality_record_issues(record)
        if issue.startswith("declared_gate_")
    ]
    if declared_gate_errors:
        raise ValueError("quality record contains a false or stale declared gate")
    evidence_file_issues = quality_record_evidence_file_issues(
        record,
        evidence_root=PROJECT_ROOT,
    )
    if record["quality_gate"].get("ready_for_future_static_qwen_probe") is True:
        if evidence_file_issues:
            raise ValueError(
                "ready quality record has missing, escaping, or hash-mismatched evidence files"
            )
    return record


def load_registry() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def infer_creation_type(ai_type: str) -> str:
    return {
        "canon_reconstruction_temp_ai": "fictional_character",
        "generated_original_temp_ai": "generated_original",
        "expert_temp_ai": "expert",
        "memory_relative_temp_ai": "memory_relative",
    }[ai_type]


def build_original_voice_fast_lane(candidate_id: str) -> dict[str, Any]:
    """Describe, but do not execute, the bounded original-voice fast lane.

    The deliberately qualified watermark status records what the reviewed
    upstream Qwen3-TTS documentation does *not* document. It is not a detector
    result and must not be strengthened until the pinned source, dependencies,
    and generated-audio acceptance corpus all pass review.
    """

    return {
        "contract": FAST_BUILD_CONTRACT_PATH,
        "eligible_ai_types": sorted(FAST_ORIGINAL_BUILD_AI_TYPES),
        "candidate_id": candidate_id,
        "automatic_draft_created": True,
        "draft_status": AUTO_DRAFT_STATUS,
        "validation_status": ASYNC_VALIDATION_STATUS,
        "execution_status": "PLAN_QUEUED_MODELS_NOT_LOADED_OR_RUN",
        "acceptance_worker_metadata": {
            "queue_kind": "TEMPORARYAI_ORIGINAL_VOICE_FORGE_PRIVATE_ACCEPTANCE_V1",
            "acceptance_contract": QWEN3_TTS_FORGE_ACCEPTANCE_CONTRACT_PATH,
            "runner": QWEN3_TTS_FORGE_RUNNER_PATH,
            "worker": QWEN3_TTS_FORGE_WORKER_PATH,
            "isolated_environment_spec": QWEN3_TTS_FORGE_ENVIRONMENT_SPEC_PATH,
            "execution_status": "QUEUED_INERT_NOT_RUN",
            "explicit_hash_bound_execution_required": True,
            "fallback_on_failure": "TEXT_PLUS_SILENCE_ONLY",
        },
        "voice_origin": "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE",
        "offline_after_local_install_and_cache": True,
        "network_required_for_normal_synthesis_after_cache": False,
        "watermark_status": NO_DOCUMENTED_WATERMARK_STATUS,
        "watermark_status_scope": (
            "Upstream documentation reviewed for this design does not document an "
            "intentional audio watermark; this is not a detector-backed absence claim."
        ),
        "stronger_watermark_claim_allowed": False,
        "stronger_watermark_claim_gates": [
            "PINNED_OFFICIAL_SOURCE_AND_LICENSE_ACCEPTED",
            "PINNED_DEPENDENCY_LOCK_AND_HASHES_ACCEPTED",
            "REPRESENTATIVE_GENERATED_AUDIO_DETECTOR_ACCEPTANCE_PASSED",
            "OWNER_HEARING_ACCEPTANCE_PASSED",
        ],
        "watermark_removal_or_circumvention_allowed": False,
        "excluded_engines": [
            {
                "engine_family": "Chatterbox",
                "reason": "Official runtime includes PerTh watermarking; this no-watermark lane does not remove, disable, evade, or misrepresent it.",
            }
        ],
        "bounded_model_sequence": [
            {
                "order": 1,
                "model": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                "purpose": "Create one original synthetic expert voice from reviewed text traits.",
                "execution": "local_eager_cuda_after_separate_acceptance",
                "output": f"TemporaryAI/candidates/{candidate_id}/voice_fast_build/original_design_reference.wav",
            },
            {
                "order": 2,
                "action": "UNLOAD_VOICE_DESIGN_AND_VERIFY_VRAM_RELEASE",
            },
            {
                "order": 3,
                "model": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "purpose": "Create and validate the exact offline runtime profile from the original designed reference.",
                "execution": "local_eager_cuda_after_separate_acceptance",
                "output": f"TemporaryAI/candidates/{candidate_id}/voice_fast_build/runtime_voice_profile.json",
            },
            {
                "order": 4,
                "action": "UNLOAD_BASE_AND_VERIFY_VRAM_RELEASE",
            },
        ],
        "one_heavy_gpu_model_at_a_time": True,
        "profile_assignment_allowed_before_validation": False,
        "activation_allowed": False,
        "generic_or_other_person_voice_fallback_allowed": False,
        "exact_profile_mismatch_behavior": "TEXT_PLUS_SILENCE_ONLY",
        "async_acceptance_required": [
            "source_and_license_hashes",
            "dependency_and_model_hashes",
            "originality_and_voice_collision_check",
            "watermark_detector_record",
            "readable_non_silent_wav",
            "requested_text_fidelity",
            "offline_synthesis",
            "latency_ram_vram_and_release",
            "owner_hearing_decision",
        ],
    }


def build_parallel_body_fast_lane(
    candidate_id: str,
    *,
    confirmed_maturity: str,
    avatar_needed: bool,
) -> dict[str, Any]:
    """Return a non-executing template-instantiation plan for the body lane."""

    if confirmed_maturity not in VALID_CONFIRMED_MATURITY:
        raise ValueError(
            "confirmed_maturity must be one of: "
            + ", ".join(sorted(VALID_CONFIRMED_MATURITY))
        )
    confirmed_adult = confirmed_maturity == "confirmed_adult"
    template_class = (
        "CONFIRMED_ADULT_SEALED_TEMPLATE"
        if confirmed_adult
        else "DOLL_SAFE_NON_ANATOMICAL_SEALED_TEMPLATE"
    )
    body_lane_status = (
        "ASYNC_PRIVATE_TEMPLATE_INSTANTIATION_QUEUED_NOT_RUN"
        if avatar_needed
        else "EXPLICIT_NO_AVATAR_REQUEST_DRAFT_NOT_QUEUED"
    )
    return {
        "contract": FAST_BUILD_CONTRACT_PATH,
        "candidate_id": candidate_id,
        "automatic_draft_created": True,
        "draft_status": AUTO_DRAFT_STATUS,
        "validation_status": ASYNC_VALIDATION_STATUS,
        "execution_status": body_lane_status,
        "parallel_with_voice_validation": bool(avatar_needed),
        "confirmed_maturity_input": confirmed_maturity,
        "adulthood_inferred": False,
        "template_class": template_class,
        "adult_anatomy_allowed": confirmed_adult,
        "doll_safe_non_anatomical_required": not confirmed_adult,
        "unresolved_maturity_routes_doll_safe": confirmed_maturity == "unresolved",
        "source": "FUTURE_SEALED_TEMPLATE_PLUS_PRECOMPUTED_PARAMETERS_ONLY",
        "sealed_template_available": False,
        "body_generated_or_completed": False,
        "quality_claim": "NO_COMPLETED_HIGH_QUALITY_BODY_CLAIM_UNTIL_SEALED_TEMPLATE_EXISTS_AND_ACCEPTANCE_PASSES",
        "hair": {
            "module": "DETACHED_SEPARATELY_VERSIONED_HAIR",
            "body_regeneration_on_hair_change_allowed": False,
            "runtime_attachment_before_acceptance_allowed": False,
        },
        "body_output": f"Avatar/temp_ai/{candidate_id}/fast_build/body_candidate",
        "validation_async": True,
        "owner_review_required": True,
        "activation_allowed": False,
        "assignment_allowed": False,
        "publication_or_upload_allowed": False,
    }


def build_creation_request(
    *,
    candidate_id: str,
    display_name: str,
    ai_type: str,
    requested_by: str,
    creation_goal: str,
    source_paths: list[str],
    queries: list[str],
    source_pack_path: str,
    expert_domain: str,
    avatar_needed: bool,
) -> dict[str, Any]:
    is_expert = ai_type == "expert_temp_ai"
    is_canon = ai_type == "canon_reconstruction_temp_ai"
    return {
        "template_id": "temporary_ai_creation_request_template_v2",
        "updated_at": now_iso(),
        "request_id": f"temp_ai_request_{candidate_id}",
        "requested_by": requested_by,
        "display_name_or_role": display_name,
        "ai_type": ai_type,
        "creation_type": infer_creation_type(ai_type),
        "creation_goal": creation_goal or (
            f"Create a reviewable {display_name} TemporaryAI candidate."
        ),
        "lifecycle": {
            "status": "draft",
            "temporary_by_default": True,
            "saved_for_reuse": False,
            "promotion_requires_review": True,
            "archive_when_finished": True,
        },
        "identity_boundaries": {
            "must_not_claim_to_be_real_person": True,
            "must_not_claim_unsupported_lived_memory": True,
            "must_label_source_based_information": True,
            "separate_from_kira_lisa_identity": True,
        },
        "source_plan": {
            "source_basis": "domain_sources" if is_expert else "fictional_canon_sources" if is_canon else "approved_design_sources",
            "local_library_paths": source_paths,
            "source_queries": queries,
            "source_pack": source_pack_path,
            "online_research_allowed_later": True,
            "online_research_status": "planned_not_run",
            "requires_multiple_sources": not is_expert,
            "treat_sources_as_evidence_not_memory": True,
            "uncertainty_allowed": True,
            "canon_or_version_anchor": "",
            "fanfic_allowed": False,
            "fanfic_must_be_labeled": True,
        },
        "expert_plan": {
            "enabled": is_expert,
            "domain": expert_domain,
            "must_cite_or_label_factual_claims": True,
            "tool_use_allowed_after_review": True,
            "should_save_handoff_notes": True,
        },
        "memory_policy": {
            "session_memory_enabled": True,
            "persistent_memory_enabled": True,
            "interaction_memory_can_be_saved": True,
            "interaction_memory_file": f"Data/temporary_ai_instances/{candidate_id}.interaction_memory.json",
            "memory_review_required_before_promotion": True,
        },
        "privacy_plan": {
            "default_visibility": "project_private",
            "allowed_contexts": ["source_review", "short_test_chat", "classroom_or_world_test"],
            "not_allowed_contexts": ["adult_or_private_intimacy", "permanent_ai_promotion", "kira_lisa_memory_update"],
            "private_adult_material_excluded_by_default": True,
        },
        "avatar_plan": {
            "avatar_needed_now": avatar_needed,
            "avatar_reference_paths": [],
            "avatar_profile": f"Avatar/temp_ai/{candidate_id}/avatar_profile.json",
            "style_or_body_notes": "",
            "online_reference_search_allowed_later": True,
            "post_gpu_3d_avatar_possible": True,
        },
        "test_plan": {
            "advanced_probe_required_before_reuse": True,
            "test_subject_id": f"temp:{candidate_id}",
            "expected_ai_type": ai_type,
            "first_probe_turns": 1,
            "longer_probe_after_review": True,
        },
        "notes_for_robert_or_codex": "Draft scaffold only. Review source pack and avatar references before activation.",
    }


def build_profile(candidate_id: str, display_name: str, ai_type: str, source_pack_path: str) -> dict[str, Any]:
    registry = load_registry()
    type_info = registry.get("ai_types", {}).get(ai_type, {})
    return {
        "profile_id": f"{candidate_id}_temporary_ai_profile_v1",
        "created_at": now_iso(),
        "status": "draft",
        "candidate_id": candidate_id,
        "display_name": display_name,
        "ai_type": ai_type,
        "purpose": type_info.get("purpose", ""),
        "memory_scope": type_info.get("memory_scope", "temporary_session_memory_unless_saved"),
        "source_pack": source_pack_path,
        "identity": {
            "source_bounded": True,
            "temporary_by_default": True,
            "separate_from_kira_lisa": True,
            "does_not_claim_unsupported_lived_memory": True,
        },
        "voice_and_behavior": {
            "voice_status": "to_be_extracted_or_designed",
            "should_answer_naturally": True,
            "avoid_status_report_style": True,
            "uncertainty_is_allowed": True,
        },
        "boundaries": {
            "private_adult_material_excluded_by_default": True,
            "no_access_to_kira_lisa_private_memory": True,
            "activation_requires_robert_review": True,
            "probe_required_before_longer_use": True,
        },
    }


def build_avatar_profile(candidate_id: str, display_name: str, ai_type: str) -> dict[str, Any]:
    build_mode = "reconstruction_fictional" if ai_type == "canon_reconstruction_temp_ai" else "generated"
    return {
        "avatar_profile_id": f"{candidate_id}_avatar_profile_v1",
        "created_at": now_iso(),
        "target_type": "temp_ai",
        "target_id": candidate_id,
        "display_name": display_name,
        "build_mode": build_mode,
        "stage": "gpu_reference_scaffold",
        "reference_sources": {
            "local_reference_paths": [],
            "online_reference_queue": f"Avatar/temp_ai/{candidate_id}/online_reference_queue.json",
            "downloaded_references_folder": f"Avatar/temp_ai/{candidate_id}/references/downloaded",
            "approved_references_folder": f"Avatar/temp_ai/{candidate_id}/references/approved",
            "rejected_references_folder": f"Avatar/temp_ai/{candidate_id}/references/rejected",
        },
        "visual_profile": {
            "forms_or_variants": [],
            "face_notes": "",
            "hair_notes": "",
            "body_notes": "",
            "wardrobe_notes": "",
            "movement_or_pose_notes": "",
        },
        "policy": {
            "references_do_not_create_memory": True,
            "source_images_must_be_labeled": True,
            "real_person_reconstruction_requires_extra_review": True,
            "owner_or_project_review_required_before_generation": True,
            "public_export_allowed": False,
        },
        "status": "draft_needs_reference_review",
    }


def build_avatar_request(candidate_id: str, display_name: str, ai_type: str) -> dict[str, Any]:
    build_mode = "reconstruction_fictional" if ai_type == "canon_reconstruction_temp_ai" else "generated"
    return {
        "request_id": f"{candidate_id}_avatar_request_v1",
        "target_type": "temp_ai",
        "target_id": candidate_id,
        "requested_by": "system_scaffold",
        "build_mode": build_mode,
        "stage": "post_gpu",
        "purpose": f"Prepare avatar references and later avatar generation for {display_name}.",
        "source_policy": {
            "references_are_evidence_not_memory": True,
            "online_references_require_review": True,
            "local_references_require_review": True,
        },
        "privacy": {
            "owner_controls_visibility": True,
            "body_generation_private": True,
            "pre_clothing_visibility_allowed": False,
            "underwear_or_clothing_required_before_default_visibility": True,
            "allowed_preview_levels": ["feature_only", "shoulders_up", "clothed_only"],
        },
        "private_reference_policy": {
            "owner_controlled": True,
            "may_be_used_for_other_avatars": False,
            "may_be_used_for_public_exports": False,
        },
        "feature_selection": {
            "owner_final_decision": True,
            "allowed_features": ["face", "hair", "eyes", "body_proportions", "wardrobe", "pose", "expression"],
        },
        "wardrobe_plan": {
            "starts_after_body_creation": True,
            "minimum_starter_outfits": ["everyday", "formal_or_work", "relaxed_home"],
        },
        "output_expectation": {
            "claim_rendered_avatar_exists": False,
            "first_output": "reference-reviewed visual brief",
            "later_output": "generated 2D/3D avatar candidate",
        },
        "status": "draft",
    }


def build_online_reference_queue(candidate_id: str, display_name: str, ai_type: str) -> dict[str, Any]:
    return {
        "queue_id": f"{candidate_id}_online_avatar_reference_queue_v1",
        "created_at": now_iso(),
        "target_type": "temp_ai",
        "target_id": candidate_id,
        "display_name": display_name,
        "ai_type": ai_type,
        "status": "planned_not_downloaded",
        "search_policy": {
            "prefer_official_sources": True,
            "secondary_sources_allowed": ["IMDb", "Wikimedia", "Wikipedia", "fan wiki for low-confidence metadata only"],
            "record_source_url": True,
            "do_not_use_private_person_images_without_permission": True,
            "review_before_avatar_generation": True,
        },
        "queries_to_review": [
            display_name,
            f"{display_name} official image",
            f"{display_name} character reference",
        ],
        "downloaded_items": [],
        "review_notes": [],
    }


def create_candidate(args: argparse.Namespace) -> dict[str, Any]:
    if args.ai_type not in VALID_AI_TYPES:
        raise ValueError(f"ai_type must be one of: {', '.join(sorted(VALID_AI_TYPES))}")
    confirmed_maturity = str(getattr(args, "confirmed_maturity", "unresolved") or "unresolved")
    if confirmed_maturity not in VALID_CONFIRMED_MATURITY:
        raise ValueError(
            "confirmed_maturity must be one of: "
            + ", ".join(sorted(VALID_CONFIRMED_MATURITY))
        )
    candidate_id = args.candidate_id or slug(args.display_name)
    if SAFE_CANDIDATE_ID_RE.fullmatch(candidate_id) is None:
        raise ValueError(
            "candidate_id must be 3-80 lowercase letters, numbers, or underscores"
        )
    base = PROJECT_ROOT / "TemporaryAI" / "candidates" / candidate_id
    avatar_base = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id
    _require_resolved_under(base, PROJECT_ROOT / "TemporaryAI" / "candidates")
    _require_resolved_under(avatar_base, PROJECT_ROOT / "Avatar" / "temp_ai")
    quality_v2_enabled = args.ai_type in QUALITY_V2_AI_TYPES
    # Older direct API Namespaces retain their already-inert draft metadata so
    # existing callers do not break. The current CLI schema always has the new
    # quality_record attribute and therefore emits no body/voice fast lane.
    legacy_inert_fast_lane_compatibility = not hasattr(args, "quality_record")
    strict_quality_v2_static_route = (
        quality_v2_enabled and not legacy_inert_fast_lane_compatibility
    )
    if quality_v2_enabled and bool(getattr(args, "discover_voice_metadata", False)):
        raise ValueError(
            "quality v2 creation is static only; voice discovery requires a separate future authorization"
        )
    quality_record = (
        build_creator_quality_v2(args, candidate_id=candidate_id)
        if quality_v2_enabled
        else None
    )
    if quality_v2_enabled:
        protected_targets = (
            base / "creation_request.json",
            base / "temporary_ai_profile.json",
            base / "README.md",
            base / "voice_discovery_request.json",
            avatar_base / "avatar_profile.json",
            avatar_base / "avatar_request.json",
            avatar_base / "online_reference_queue.json",
        )
        existing = [rel(path) for path in protected_targets if path.exists()]
        if existing:
            raise FileExistsError(
                "quality v2 will not overwrite prior candidate evidence: "
                + ", ".join(existing)
            )

    source_pack_path = ""
    if args.source_path or args.query:
        pack = build_pack(
            character_id=candidate_id,
            display_name=args.display_name,
            source_paths=args.source_path,
            queries=args.query,
            notes=args.notes or f"Source pack for {args.display_name} TemporaryAI candidate.",
            index_path=DEFAULT_INDEX_PATH,
        )
        if not args.include_fanfic:
            pack["sources"] = [
                source for source in pack.get("sources", [])
                if "/stories/fanfic/" not in str(source.get("source_path", "")).lower().replace("\\", "/")
            ]
            pack["source_count"] = len(pack["sources"])
            pack.setdefault("policy", {})["fanfic_excluded_by_default"] = True
        pack["sources"] = [
            source for source in pack.get("sources", [])
            if "/private_adult_" not in str(source.get("source_path", "")).lower().replace("\\", "/")
        ]
        pack["source_count"] = len(pack["sources"])
        pack.setdefault("policy", {})["private_adult_sources_excluded_by_default"] = True
        source_pack = PROJECT_ROOT / "Data" / "temporary_ai_source_packs" / f"{pack['source_pack_id']}.draft.json"
        if quality_v2_enabled:
            write_json_exclusive(source_pack, pack)
        else:
            write_json(source_pack, pack)
        source_pack_path = rel(source_pack)

    effective_expert_domain = (
        str(quality_record.get("expert_domain") or "")
        if quality_record is not None and args.ai_type == "expert_temp_ai"
        else str(getattr(args, "expert_domain", "") or "")
    )

    creation_request = build_creation_request(
        candidate_id=candidate_id,
        display_name=args.display_name,
        ai_type=args.ai_type,
        requested_by=args.requested_by,
        creation_goal=args.goal,
        source_paths=args.source_path,
        queries=args.query,
        source_pack_path=source_pack_path,
        expert_domain=effective_expert_domain,
        avatar_needed=not args.no_avatar,
    )
    profile = build_profile(candidate_id, args.display_name, args.ai_type, source_pack_path)
    if quality_record is not None:
        quality_path = (
            base
            / "quality_v2"
            / f"creator_quality_v2_revision_{int(quality_record['revision']):06d}.json"
        )
        quality_issues = quality_record_issues(quality_record)
        quality_evidence_file_issues = quality_record_evidence_file_issues(
            quality_record,
            evidence_root=PROJECT_ROOT,
        )
        if quality_record["quality_gate"].get(
            "ready_for_future_static_qwen_probe"
        ) is True and quality_evidence_file_issues:
            raise ValueError(
                "ready quality record evidence changed before append-only write"
            )
        quality_sha256 = write_quality_revision_exclusive(quality_path, quality_record)
        quality_summary = {
            "record": rel(quality_path),
            "record_sha256": quality_sha256,
            "status": quality_record["quality_gate"]["status"],
            "structural_or_evidence_issues": quality_record["quality_gate"]["issues"],
            "declared_gate_errors": [
                issue for issue in quality_issues if issue.startswith("declared_gate_")
            ],
            "evidence_file_issues": quality_evidence_file_issues,
            "all_evidence_files_hash_verified": not quality_evidence_file_issues,
            "evidence_verified_at_utc": now_utc_z(),
            "exact_static_evaluation_model": EXACT_QWEN_MODEL,
            "exact_static_evaluation_digest": EXACT_QWEN_DIGEST,
            "model_loaded_or_called": False,
            "evidence_bound_maturity_status": evidence_bound_maturity_status(
                quality_record
            ),
            "lifecycle_status": PRIVATE_LIFECYCLE_STATUS,
            "activation_allowed": False,
            "assignment_allowed": False,
            "body_or_voice_work_authorized": False,
            "owner_corrections_require_append_only_successor": True,
        }
        creation_request["creator_quality_v2"] = quality_summary
        creation_request["lifecycle"] = {
            "status": PRIVATE_LIFECYCLE_STATUS,
            "temporary_by_default": True,
            "saved_for_reuse": False,
            "activation_allowed": False,
            "assignment_allowed": False,
            "promotion_allowed": False,
            "publication_allowed": False,
            "runtime_registration_allowed": False,
            "static_review_only": True,
        }
        creation_request["source_plan"].update(
            {
                "requires_multiple_sources": args.ai_type == "expert_temp_ai",
                "canonical_quality_record": rel(quality_path),
                "canon_facts_reconstruction_inference_uncertainty_separated": True,
            }
        )
        creation_request["expert_plan"].update(
            {
                "domain": effective_expert_domain,
                "source_backed_competency_battery_required": (
                    args.ai_type == "expert_temp_ai"
                ),
                "ignorance_uncertainty_and_correction_cases_required": (
                    args.ai_type == "expert_temp_ai"
                ),
                "generic_fluent_answers_count_as_expertise": False,
            }
        )
        creation_request["privacy_plan"].update(
            {
                "allowed_contexts": ["static_source_and_contract_review"],
                "not_allowed_contexts": [
                    "chat_or_live_probe",
                    "adult_or_private_intimacy",
                    "assignment_or_activation",
                    "publication",
                    "body_or_voice_generation",
                    "model_or_gpu_execution",
                ],
            }
        )
        creation_request["avatar_plan"].update(
            {
                "avatar_needed_now": False,
                "body_or_reference_work_authorized": False,
                "deferred_outside_static_quality_v2": True,
                "post_gpu_3d_avatar_possible": False,
            }
        )
        creation_request["test_plan"].update(
            {
                "advanced_probe_required_before_reuse": False,
                "future_probe_authorized": False,
                "longer_probe_after_review": False,
                "static_contract_tests_only": True,
            }
        )
        creation_request["notes_for_robert_or_codex"] = (
            "Static quality-v2 scaffold only. No activation, assignment, body, voice, "
            "model, GPU, Blender, or live probe is authorized."
        )
        if quality_record.get("variant_kind") == "historical":
            creation_request["creation_type"] = "historical_variant"
        profile["creator_quality_v2"] = quality_summary
        profile["status"] = PRIVATE_LIFECYCLE_STATUS
        profile["boundaries"].update(
            {
                "activation_allowed": False,
                "assignment_allowed": False,
                "publication_allowed": False,
                "runtime_registration_allowed": False,
                "body_or_voice_work_authorized": False,
                "model_gpu_blender_or_live_execution_allowed": False,
            }
        )
        if strict_quality_v2_static_route:
            profile["voice_and_behavior"].update(
                {
                    "voice_status": "STATIC_QUALITY_V2_NO_VOICE_WORK_AUTHORIZED",
                    "voice_discovery_allowed": False,
                    "voice_generation_or_assignment_allowed": False,
                }
            )
    voice_discovery_request = (
        {
            "candidate_id": candidate_id,
            "status": "STATIC_QUALITY_V2_NO_VOICE_DISCOVERY_AUTHORIZED",
            "metadata_search_allowed": False,
            "media_download_allowed": False,
            "voice_generation_allowed": False,
            "voice_assignment_allowed": False,
            "model_gpu_or_playback_execution_allowed": False,
        }
        if strict_quality_v2_static_route
        else build_candidate_voice_discovery_request(profile, creation_request)
    )
    creation_request["voice_plan"] = {
        "discovery_request": f"TemporaryAI/candidates/{candidate_id}/voice_discovery_request.json",
        "status": "metadata_discovery_not_run",
        "media_download_allowed_by_discovery": False,
        "discovery_no_download_is_stage_scoped_not_a_global_creator_ban": True,
        "private_local_media_intake_folder": (
            f"TemporaryAI/candidates/{candidate_id}/workbench/inputs/private_local_media_intake"
        ),
        "bounded_private_local_reference_intake_allowed_after_explicit_authorization": True,
        "public_release_or_official_voice_claim_requires_separate_review": True,
        "voice_assignment_or_activation_allowed": False,
    }
    if strict_quality_v2_static_route:
        creation_request["voice_plan"].update(
            {
                "status": "STATIC_QUALITY_V2_NO_VOICE_WORK_AUTHORIZED",
                "bounded_private_local_reference_intake_allowed_after_explicit_authorization": False,
                "future_discovery_authorized": False,
                "voice_generation_or_assignment_allowed": False,
            }
        )
    if args.ai_type in FAST_ORIGINAL_BUILD_AI_TYPES and (
        not quality_v2_enabled or legacy_inert_fast_lane_compatibility
    ):
        voice_fast_lane = build_original_voice_fast_lane(candidate_id)
        body_fast_lane = build_parallel_body_fast_lane(
            candidate_id,
            confirmed_maturity=(
                evidence_bound_maturity_status(quality_record)
                if quality_record is not None
                else confirmed_maturity
            ),
            avatar_needed=not args.no_avatar,
        )
        creation_request["automatic_fast_build"] = {
            "contract": FAST_BUILD_CONTRACT_PATH,
            "status": AUTO_DRAFT_STATUS,
            "created_with_candidate_scaffold": True,
            "validation_runs_asynchronously_after_draft": True,
            "voice_lane": voice_fast_lane,
            "body_lane": body_fast_lane,
            "activation_allowed": False,
            "assignment_allowed": False,
            "publication_or_upload_allowed": False,
        }
        creation_request["voice_plan"]["automatic_original_voice_fast_lane"] = voice_fast_lane
        creation_request["avatar_plan"]["automatic_private_body_fast_lane"] = body_fast_lane
        profile["voice_and_behavior"].update(
            {
                "voice_status": AUTO_DRAFT_STATUS,
                "automatic_original_voice_fast_lane": voice_fast_lane,
                "exact_profile_mismatch_behavior": "TEXT_PLUS_SILENCE_ONLY",
            }
        )
        profile["automatic_fast_build_status"] = {
            "status": AUTO_DRAFT_STATUS,
            "validation_status": ASYNC_VALIDATION_STATUS,
            "body_template_class": body_fast_lane["template_class"],
            "body_generated_or_completed": False,
            "voice_generated_or_assigned": False,
        }
    profile["voice_and_behavior"]["voice_discovery_request"] = creation_request["voice_plan"]["discovery_request"]
    profile["voice_and_behavior"]["private_local_media_intake_folder"] = creation_request["voice_plan"][
        "private_local_media_intake_folder"
    ]
    if strict_quality_v2_static_route:
        avatar_profile = {
            "target_type": "temp_ai",
            "target_id": candidate_id,
            "status": "STATIC_QUALITY_V2_NO_BODY_WORK_AUTHORIZED",
            "body_authoring_allowed": False,
            "reference_intake_allowed": False,
            "gpu_or_blender_execution_allowed": False,
        }
        avatar_request = {
            "target_type": "temp_ai",
            "target_id": candidate_id,
            "status": "STATIC_QUALITY_V2_NO_BODY_WORK_AUTHORIZED",
            "body_authoring_allowed": False,
            "reference_intake_allowed": False,
            "gpu_or_blender_execution_allowed": False,
        }
    else:
        avatar_profile = build_avatar_profile(candidate_id, args.display_name, args.ai_type)
        avatar_request = build_avatar_request(candidate_id, args.display_name, args.ai_type)
    if args.ai_type in FAST_ORIGINAL_BUILD_AI_TYPES and (
        not quality_v2_enabled or legacy_inert_fast_lane_compatibility
    ):
        avatar_profile["automatic_private_body_fast_lane"] = creation_request["automatic_fast_build"][
            "body_lane"
        ]
        avatar_profile["status"] = AUTO_DRAFT_STATUS
        avatar_request["automatic_private_body_fast_lane"] = creation_request["automatic_fast_build"][
            "body_lane"
        ]
        avatar_request["status"] = AUTO_DRAFT_STATUS
    online_queue = build_online_reference_queue(candidate_id, args.display_name, args.ai_type)
    if strict_quality_v2_static_route:
        online_queue = {
            "target_type": "temp_ai",
            "target_id": candidate_id,
            "status": "STATIC_QUALITY_V2_NO_ONLINE_OR_AVATAR_REFERENCE_WORK_AUTHORIZED",
            "search_allowed": False,
            "download_allowed": False,
            "queries_to_review": [],
        }

    files = {
        "candidate_request": base / "creation_request.json",
        "candidate_profile": base / "temporary_ai_profile.json",
        "candidate_notes": base / "README.md",
        "voice_discovery_request": base / "voice_discovery_request.json",
        "avatar_profile": avatar_base / "avatar_profile.json",
        "avatar_request": avatar_base / "avatar_request.json",
        "online_reference_queue": avatar_base / "online_reference_queue.json",
    }
    if quality_record is not None:
        files["creator_quality_v2"] = quality_path
    json_writer = write_json_exclusive if quality_v2_enabled else write_json
    text_writer = write_text_exclusive if quality_v2_enabled else write_text
    json_writer(files["candidate_request"], creation_request)
    json_writer(files["candidate_profile"], profile)
    json_writer(files["voice_discovery_request"], voice_discovery_request)
    json_writer(files["avatar_profile"], avatar_profile)
    json_writer(files["avatar_request"], avatar_request)
    json_writer(files["online_reference_queue"], online_queue)
    for folder in ("references/downloaded", "references/approved", "references/rejected", "outputs"):
        (avatar_base / folder).mkdir(parents=True, exist_ok=True)
    if quality_v2_enabled:
        candidate_notes = f"""# {args.display_name} TemporaryAI Candidate

Candidate ID: `{candidate_id}`

AI type: `{args.ai_type}`

Status: `{PRIVATE_LIFECYCLE_STATUS}`. This is an append-only static quality
scaffold. It does not activate, assign, publish, register, or run the candidate.

The quality-v2 path authorizes no body, avatar-reference intake, voice discovery,
model call, GPU work, Blender work, playback, or live probe. A static quality
gate passing does not change that lifecycle boundary.

Static review steps:

1. Verify the exact hash of `quality_v2/creator_quality_v2_revision_000001.json`.
2. Resolve every listed source, identity, continuity, timepoint, maturity, and classification issue.
3. Keep canon facts, reconstruction, inference, and uncertainty in their separate ledgers.
4. For experts, review the declared domain and all six source-backed competency cases.
5. Record owner corrections only as hash-chained successor revisions; never overwrite revision 1.
6. Obtain a separate future authorization before any model, body, voice, GPU, Blender, or live work.
"""
    else:
        candidate_notes = f"""# {args.display_name} TemporaryAI Candidate

Candidate ID: `{candidate_id}`

AI type: `{args.ai_type}`

Status: draft scaffold. This does not activate the AI.

For original expert/generated candidates, the scaffold also creates a private
inactive voice-and-body fast-build queue. It does not claim that a voice or body
was generated. The voice lane remains text plus silence on an exact-profile
mismatch, and the body lane remains template-blocked until a qualifying sealed
template exists.

Next steps:

1. Review `creation_request.json`.
2. Review or build the source pack.
3. Add approved avatar references under `Avatar/temp_ai/{candidate_id}/references/approved/`.
4. Run `py tools/discover_temporary_ai_voice.py --candidate-id {candidate_id} --metadata-search`, then review every source/rights label.
5. For a user-authorized file already in `Data/library`, create exact short voice/movement ranges with `tools/create_temp_ai_local_media_intake.py`; discovery's no-download rule does not block that separate lane.
6. Run an advanced probe before reuse.
7. Only then create an activation context or live chat runner.
"""
    text_writer(
        files["candidate_notes"],
        candidate_notes,
    )

    result = {
        "candidate_id": candidate_id,
        "display_name": args.display_name,
        "ai_type": args.ai_type,
        "source_pack": source_pack_path,
        "files": {key: rel(path) for key, path in files.items()},
    }
    if quality_record is not None:
        result["creator_quality_v2"] = quality_summary
    if bool(getattr(args, "discover_voice_metadata", False)):
        output, discovery_result = run_candidate_discovery(candidate_id, metadata_search=True)
        result["voice_discovery"] = {
            "status": discovery_result["status"],
            "output": rel(output),
            "recording_candidate_count": len(discovery_result["recording_candidates"]),
            "synthetic_model_candidate_count": len(discovery_result["synthetic_model_candidates"]),
            "voice_assigned": False,
            "media_downloaded": False,
        }
    else:
        result["voice_discovery"] = {
            "status": "request_created_metadata_search_not_run",
            "output": "",
            "voice_assigned": False,
            "media_downloaded": False,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reviewable TemporaryAI + avatar candidate scaffold.")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--ai-type", choices=sorted(VALID_AI_TYPES), default="canon_reconstruction_temp_ai")
    parser.add_argument("--requested-by", default="real_robert")
    parser.add_argument("--goal", default="")
    parser.add_argument("--expert-domain", default="")
    parser.add_argument(
        "--quality-record",
        default="",
        help=(
            "Canonical creator-quality-v2 revision 1 to copy append-only. When omitted, "
            "fictional/historical and expert candidates receive an honestly blocked static skeleton."
        ),
    )
    parser.add_argument(
        "--variant-kind",
        choices=["fictional", "historical"],
        default="fictional",
        help="Exact source kind for canon-reconstruction candidates.",
    )
    parser.add_argument("--canonical-identity", default="")
    parser.add_argument("--source-continuity", default="")
    parser.add_argument("--source-version", default="")
    parser.add_argument("--source-timepoint", default="")
    parser.add_argument("--branch-point", default="")
    parser.add_argument("--maturity-classification-id", default="")
    parser.add_argument(
        "--maturity-authority-kind",
        choices=[
            "canonical_source_classification",
            "exact_subject_owner_classification",
        ],
        default="exact_subject_owner_classification",
    )
    parser.add_argument("--maturity-evidence-path", default="")
    parser.add_argument("--maturity-evidence-sha256", default="")
    parser.add_argument("--maturity-recorded-at-utc", default="")
    parser.add_argument(
        "--confirmed-maturity",
        choices=sorted(VALID_CONFIRMED_MATURITY),
        default="unresolved",
        help=(
            "Exact-subject classification input. Quality-v2 records require its evidence and "
            "authorize no body work; legacy inert draft plans treat missing evidence as unresolved."
        ),
    )
    parser.add_argument("--source-path", action="append", default=[])
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--no-avatar", action="store_true")
    parser.add_argument("--include-fanfic", action="store_true", help="Allow fanfic/variant sources in the draft source pack.")
    parser.add_argument(
        "--discover-voice-metadata",
        action="store_true",
        help=(
            "Legacy non-quality path only: search recording/model-card metadata. "
            "Fictional/historical and expert quality-v2 creation rejects this option."
        ),
    )
    args = parser.parse_args()

    result = create_candidate(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
