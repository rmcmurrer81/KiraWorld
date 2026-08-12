"""
Validate notebook world request JSON files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "request_id",
    "request_type",
    "title",
    "requested_by",
    "trigger",
    "subject",
    "source_collection_plan",
    "world_plan",
    "visibility_scope",
    "autonomy_level_required",
    "status",
}

VALID_REQUESTED_BY = {"robert", "kira", "lisa", "kira_lisa"}
VALID_VISIBILITY = {"private_only", "share_with_robert", "public_export_candidate", "approved_public"}
VALID_AUTONOMY = {"manual_only", "request_mode", "approved_autonomy", "mature_autonomy"}
VALID_STATUS = {"draft", "approved", "building", "active", "archived"}
VALID_PRIVATE_NPC_POLICY = {"none", "generic", "source_inspired", "temporary_ai_allowed"}
VALID_V2_SUBJECT_CATEGORIES = {
    "real_place",
    "real_historic_place",
    "fictional_or_original_place",
    "fictional_place",
    "memory_place",
    "original_idea",
    "hybrid",
}
VALID_TRUTH_LABELS = {
    "blueprint_confirmed",
    "photo_confirmed",
    "video_confirmed",
    "map_confirmed",
    "manual_note_confirmed",
    "inferred_from_sources",
    "style_fill",
    "unknown",
    "blocked_private",
}
VALID_GATE_STATUSES = {"not_run", "blocked", "failed", "passed"}
_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def _normalized_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and ":" not in path.parts[0]
        and all(part not in {"", ".", ".."} for part in path.parts)
        and path.as_posix() == value
    )


def _expect_bool(container: dict[str, Any], key: str, expected: bool, errors: list[str], prefix: str) -> None:
    if container.get(key) is not expected:
        errors.append(f"{prefix}.{key} must be {str(expected).lower()}.")


def _validate_zone_list(world_plan: dict[str, Any], key: str, errors: list[str]) -> set[str]:
    value = world_plan.get(key)
    if not isinstance(value, list):
        errors.append(f"world_plan.{key} must be a list.")
        return set()
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"world_plan.{key} must contain only non-empty strings.")
    normalized = [item.strip().casefold() for item in value if isinstance(item, str) and item.strip()]
    if len(normalized) != len(set(normalized)):
        errors.append(f"world_plan.{key} must not contain duplicate zones.")
    return set(normalized)


def _validate_v2(data: dict[str, Any], subject: dict[str, Any], source_plan: dict[str, Any], world_plan: dict[str, Any], errors: list[str]) -> None:
    request_id = str(data.get("request_id") or "")
    if not _ID_RE.fullmatch(request_id) or not request_id.startswith("notebook_world_"):
        errors.append("schema v2 request_id must be a normalized notebook_world_* identifier.")
    if data.get("status") != "draft":
        errors.append("schema v2 request generation is draft-only; promotion requires a separate approval artifact.")
    if data.get("visibility_scope") == "approved_public":
        errors.append("schema v2 requests cannot self-declare approved_public visibility.")

    trigger = _expect_object(data, "trigger", errors)
    if trigger:
        for key in ("source", "summary", "created_at"):
            if not isinstance(trigger.get(key), str) or not trigger[key].strip():
                errors.append(f"trigger.{key} is required for schema v2.")

    if subject:
        if subject.get("category") not in VALID_V2_SUBJECT_CATEGORIES:
            errors.append("subject.category is not a supported schema v2 category.")
        _expect_bool(subject, "private_use_allowed", True, errors, "subject")
        _expect_bool(subject, "public_export_requires_review", True, errors, "subject")

    if source_plan:
        allowed = source_plan.get("allowed_source_types")
        if isinstance(allowed, list):
            allowed_strings = [item for item in allowed if isinstance(item, str) and item.strip()]
            if not allowed or len(allowed_strings) != len(allowed):
                errors.append("source_collection_plan.allowed_source_types must contain non-empty strings.")
            if len(allowed_strings) != len(set(allowed_strings)):
                errors.append("source_collection_plan.allowed_source_types must not contain duplicates.")
        _expect_bool(source_plan, "requires_robert_approval_now", True, errors, "source_collection_plan")
        _expect_bool(source_plan, "auto_collection_allowed_later", False, errors, "source_collection_plan")
        if source_plan.get("download_policy") != "record_source_leads_first_download_only_after_review":
            errors.append("schema v2 source download policy must remain review-gated.")
        if not _normalized_relative_path(source_plan.get("source_tasks_path")):
            errors.append("source_collection_plan.source_tasks_path must be a normalized project-relative path.")

    if world_plan:
        world_id = str(world_plan.get("notebook_world_id") or "")
        if not _ID_RE.fullmatch(world_id) or not world_id.endswith("_notebook_world"):
            errors.append("world_plan.notebook_world_id must be a normalized *_notebook_world identifier.")
        if not isinstance(world_plan.get("notebook_world_title"), str) or not world_plan["notebook_world_title"].strip():
            errors.append("world_plan.notebook_world_title is required for schema v2.")
        zone_sets = {
            key: _validate_zone_list(world_plan, key, errors)
            for key in ("confirmed_zones", "inferred_zones", "unknown_zones")
        }
        if zone_sets["confirmed_zones"] & zone_sets["inferred_zones"]:
            errors.append("A zone cannot be both confirmed and inferred.")
        if zone_sets["confirmed_zones"] & zone_sets["unknown_zones"]:
            errors.append("A zone cannot be both confirmed and unknown.")
        if zone_sets["inferred_zones"] & zone_sets["unknown_zones"]:
            errors.append("A zone cannot be both inferred and unknown.")
        truth_labels = world_plan.get("truth_labels")
        truth_label_set = {
            item for item in truth_labels if isinstance(item, str)
        } if isinstance(truth_labels, list) else set()
        if not isinstance(truth_labels, list) or len(truth_label_set) != len(truth_labels) or not VALID_TRUTH_LABELS.issubset(truth_label_set):
            errors.append("schema v2 world_plan.truth_labels must include every required uncertainty label.")
        for key in (
            "placement_path",
            "scene_plan_path",
            "blueprint_preview_path",
            "tardis_review_stage_path",
            "quality_gate_path",
            "resource_isolation_gate_path",
        ):
            if not _normalized_relative_path(world_plan.get(key)):
                errors.append(f"world_plan.{key} must be a normalized project-relative path.")

    creation_mode = _expect_object(data, "creation_mode", errors)
    valid_creation_modes = {
        "saved_world",
        "blank_world",
        "memory_reconstruction",
        "source_reconstruction",
        "original_creation",
    }
    if creation_mode:
        if creation_mode.get("mode") not in valid_creation_modes:
            errors.append("creation_mode.mode is invalid.")
        if not isinstance(creation_mode.get("starts_from_blank"), bool):
            errors.append("creation_mode.starts_from_blank must be a boolean.")
        if creation_mode.get("mode") == "original_creation" and creation_mode.get("starts_from_blank") is not True:
            errors.append("Original creation must explicitly start from a blank world.")
    gateway = _expect_object(data, "access_gateway", errors)
    if gateway:
        if gateway.get("gateway_id") != "tardis_notebook_world_gateway":
            errors.append("schema v2 notebook worlds must use the TARDIS notebook gateway.")
        if gateway.get("entry_location") != "outside_protected_home_world":
            errors.append("access_gateway.entry_location must remain outside_protected_home_world.")
        if gateway.get("selection_method") != "interior_console":
            errors.append("access_gateway.selection_method must be interior_console.")

    approval = _expect_object(data, "approval_workflow", errors)
    if approval:
        _expect_bool(approval, "auto_place_in_existing_world", False, errors, "approval_workflow")
        _expect_bool(approval, "robert_approval_required_before_commit", True, errors, "approval_workflow")
        if approval.get("current_stage") != "draft_request_only":
            errors.append("approval_workflow.current_stage must be draft_request_only.")
        previews = approval.get("required_previews_before_approval")
        if not isinstance(previews, list) or len(previews) < 3:
            errors.append("approval_workflow requires blueprint, isolated, and walkable previews.")

    isolation = _expect_object(data, "isolation_policy", errors)
    if isolation:
        if isolation.get("world_class") != "separate_notebook_world":
            errors.append("isolation_policy.world_class must be separate_notebook_world.")
        for key in (
            "home_world_import_requested",
            "home_world_mutation_allowed",
            "strip_mall_mutation_allowed",
            "co_load_with_home_world",
            "co_load_with_other_notebook_worlds",
        ):
            _expect_bool(isolation, key, False, errors, "isolation_policy")
        if isolation.get("runtime_load_policy") != "one_notebook_world_at_a_time":
            errors.append("isolation_policy.runtime_load_policy must be one_notebook_world_at_a_time.")
        _expect_bool(
            isolation,
            "collection_members_are_logical_not_co_loaded",
            True,
            errors,
            "isolation_policy",
        )

    resource = _expect_object(data, "resource_policy", errors)
    if resource:
        if not _normalized_relative_path(resource.get("hardware_profile")):
            errors.append("resource_policy.hardware_profile must be a normalized project-relative path.")
        if resource.get("current_decision") != "request_paperwork_only_no_runtime":
            errors.append("schema v2 requests must begin as paperwork-only with no runtime.")
        for key in ("loads_kira_mind", "loads_kira_body", "loads_voice", "loads_ollama", "loads_second_person"):
            _expect_bool(resource, key, False, errors, "resource_policy")
        if resource.get("future_preview_policy") != "isolated_preview_only_one_heavy_workload_at_a_time":
            errors.append("resource_policy.future_preview_policy must require one isolated heavy workload at a time.")

    gates = _expect_object(data, "quality_gates", errors)
    if gates:
        required_gates = {
            "source_evidence",
            "scale_and_placement",
            "doors_routes_and_collision",
            "visual_realism",
            "runtime_route",
            "pinned_deployment",
            "explicit_robert_approval",
        }
        missing_gates = required_gates - set(gates)
        if missing_gates:
            errors.append(f"quality_gates is missing: {', '.join(sorted(missing_gates))}")
        for key in required_gates & set(gates):
            if gates.get(key) not in VALID_GATE_STATUSES:
                errors.append(f"quality_gates.{key} has an invalid status.")
        if any(gates.get(key) == "passed" for key in required_gates):
            errors.append("A new schema v2 draft cannot pre-claim passed quality gates.")


def _expect_object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object.")
        return {}
    return value


def validate_notebook_world_request(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_version = data.get("schema_version", 1)
    if isinstance(schema_version, bool) or schema_version not in {1, 2}:
        errors.append("schema_version must be 1 or 2.")
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if data.get("request_type") != "notebook_world":
        errors.append("request_type must be notebook_world.")
    if data.get("requested_by") not in VALID_REQUESTED_BY:
        errors.append(f"requested_by must be one of: {', '.join(sorted(VALID_REQUESTED_BY))}")
    if data.get("visibility_scope") not in VALID_VISIBILITY:
        errors.append(f"visibility_scope must be one of: {', '.join(sorted(VALID_VISIBILITY))}")
    if data.get("autonomy_level_required") not in VALID_AUTONOMY:
        errors.append(f"autonomy_level_required must be one of: {', '.join(sorted(VALID_AUTONOMY))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")
    if not data.get("request_id"):
        errors.append("request_id is required.")
    if not data.get("title"):
        errors.append("title is required.")

    subject = _expect_object(data, "subject", errors)
    if subject and not subject.get("name"):
        errors.append("subject.name is required.")

    source_plan = _expect_object(data, "source_collection_plan", errors)
    if source_plan:
        if not isinstance(source_plan.get("allowed_source_types"), list):
            errors.append("source_collection_plan.allowed_source_types must be a list.")
        if source_plan.get("requires_robert_approval_now") is not True:
            if data.get("autonomy_level_required") != "mature_autonomy":
                errors.append("source collection must require Robert approval before mature autonomy.")

    world_plan = _expect_object(data, "world_plan", errors)
    if world_plan:
        if world_plan.get("npc_policy") not in VALID_PRIVATE_NPC_POLICY:
            errors.append(f"world_plan.npc_policy must be one of: {', '.join(sorted(VALID_PRIVATE_NPC_POLICY))}")
        for key in ("confirmed_zones", "inferred_zones", "unknown_zones"):
            if not isinstance(world_plan.get(key), list):
                errors.append(f"world_plan.{key} must be a list.")

    if data.get("visibility_scope") == "approved_public" and data.get("autonomy_level_required") != "mature_autonomy":
        errors.append("approved_public notebook worlds require mature_autonomy.")

    if schema_version == 2:
        _validate_v2(data, subject, source_plan, world_plan, errors)

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a notebook world request JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_notebook_world_request(data)
    if errors:
        print(f"{path} is not ready for approval:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally ready for review.")


if __name__ == "__main__":
    main()
