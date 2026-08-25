"""Lightweight Avatar Builder agent memory and correction loop."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Core.avatar_asset_library import (
    CANONICAL_ADULT_CANDIDATE_IDS,
    NORMAL_MARINETTE_CANDIDATE_ID,
    validate_candidate_maturity_identity,
)
from Core.avatar_builder_correction_memory import (
    append_correction_event,
    derive_correction_directives,
    evaluate_age_progression_stage_one_eligibility,
    evaluate_age_progression_stage_two_gate,
    route_next_private_build,
)
from Core.avatar_builder_memory_lock import (
    AvatarBuilderMemoryLockError,
    is_canonical_utc_timestamp,
    locked_memory_write,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_TEMP_DIR = PROJECT_ROOT / "Avatar" / "temp_ai"
AVATAR_STATE_DIR = PROJECT_ROOT / "Avatar" / "state" / "temp_ai"
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
DEFAULT_GLOBAL_MEMORY_PATH = BUILDER_ROOT / "builder_memory.json"
GLOBAL_MEMORY_PATH = DEFAULT_GLOBAL_MEMORY_PATH
HAIR_TRAINING_ROOT = BUILDER_ROOT / "hair_training"
BODY_TRAINING_ROOT = BUILDER_ROOT / "body_training"
COMPLETE_BODY_CAPABILITY_MATRIX_PATH = (
    BUILDER_ROOT
    / "body_systems"
    / "kira_complete_adult_body_capability_matrix_v1.json"
)
SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH = (
    BUILDER_ROOT
    / "body_systems"
    / "synthetic_robert_complete_adult_body_capability_matrix_v1.json"
)
ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH = (
    BUILDER_ROOT
    / "body_systems"
    / "biological_robert_confirmed_adult_male_internal_external_anatomy_body_function_contract_v1.json"
)
DUAL_ROBERT_SEPARATION_AUTHORITY_PATH = (
    PROJECT_ROOT / "Core" / "dual_robert_avatar_authority.py"
)
COMPLETE_BODY_CURRICULUM_LESSON_ID = "avatar_builder_complete_body_inside_out_v1"
BUILDER_MEMORY_IGNORE_RULE = "Avatar/avatar_builder/builder_memory.json"

ADULT_CLASSES = {"adult"}
NON_ADULT_CLASSES = {"non_adult_doll_safe", "uncertain_non_adult_safe_default"}
CANONICAL_GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"
CANONICAL_PETER_ID = "peter_parker_spider_man_no_way_home_final_suit"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_confirmed_adult_classification_evidence(
    candidate_id: str,
    correction_text: str,
    *,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Bind Robert's exact-person correction without using keyword guesses."""

    subject_id = candidate_id.strip()
    source_text = correction_text.strip()
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return {
        "classification_id": f"robert_confirmed_adult_{digest[:20]}",
        "subject_id": subject_id,
        "maturity_status": "confirmed_adult",
        "authority": "Robert_explicit_owner_confirmation",
        "offline_confirmation_allowed": True,
        "network_lookup_required": False,
        "recorded_at_utc": recorded_at or now_iso(),
        "source_text_sha256": digest,
        "source_text": source_text,
    }


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def _read_curriculum_object(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        failures.append(f"{label}_missing_or_invalid_json")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{label}_must_be_object")
        return {}
    return value


def _validate_bound_authorities(
    matrix: dict[str, Any],
    label: str,
    failures: list[str],
    *,
    field: str = "bound_authorities",
    expected_roles: dict[str, str] | None = None,
) -> None:
    authorities = matrix.get(field)
    if not isinstance(authorities, list) or not authorities:
        failures.append(f"{label}_{field}_missing")
        return
    seen_paths: set[str] = set()
    seen_roles: set[str] = set()
    actual_roles: dict[str, str] = {}
    root = PROJECT_ROOT.resolve()
    for index, record in enumerate(authorities):
        if not isinstance(record, dict):
            failures.append(f"{label}_authority_{index}_must_be_object")
            continue
        relative = record.get("path")
        role = record.get("role")
        expected_bytes = record.get("bytes")
        expected_sha = record.get("sha256")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            failures.append(f"{label}_authority_{index}_path_invalid")
            continue
        if relative in seen_paths:
            failures.append(f"{label}_authority_path_duplicate:{relative}")
        seen_paths.add(relative)
        if not isinstance(role, str) or not role:
            failures.append(f"{label}_authority_{index}_role_invalid")
        elif role in seen_roles:
            failures.append(f"{label}_authority_role_duplicate:{role}")
        seen_roles.add(str(role))
        if isinstance(role, str):
            actual_roles[relative] = role
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            failures.append(f"{label}_authority_unavailable:{relative}")
            continue
        source_path = root.joinpath(*relative_path.parts).absolute()
        try:
            source_path.relative_to(root)
        except ValueError:
            failures.append(f"{label}_authority_unavailable:{relative}")
            continue
        native_source_path = source_path
        if os.name == "nt" and not str(source_path).startswith("\\\\?\\"):
            native_source_path = Path("\\\\?\\" + str(source_path))
        if not native_source_path.is_file():
            failures.append(f"{label}_authority_not_file:{relative}")
            continue
        if (
            type(expected_bytes) is not int
            or expected_bytes != native_source_path.stat().st_size
        ):
            failures.append(f"{label}_authority_bytes_differ:{relative}")
        digest = hashlib.sha256()
        try:
            with native_source_path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError:
            failures.append(f"{label}_authority_unreadable:{relative}")
            continue
        if (
            not isinstance(expected_sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha)
            or digest.hexdigest() != expected_sha
        ):
            failures.append(f"{label}_authority_sha256_differ:{relative}")
    if expected_roles is not None and actual_roles != expected_roles:
        failures.append(f"{label}_{field}_path_role_set_differs")


def _validate_complete_body_matrix(
    matrix: dict[str, Any],
    *,
    label: str,
    artifact_type: str,
    expected_status: str,
    subject_id: str | None,
    required_owner_requirements: set[str],
    required_system_ids: set[str],
    required_acceptance_steps: set[str],
    expected_authority_roles: dict[str, str],
    failures: list[str],
) -> None:
    if matrix.get("artifact_type") != artifact_type:
        failures.append(f"{label}_missing_or_wrong_type")
    if matrix.get("status") != expected_status:
        failures.append(f"{label}_truth_status_differs")
    if subject_id is not None and matrix.get("subject_id") != subject_id:
        failures.append(f"{label}_subject_differs")

    owner_requirements = matrix.get("owner_requirements")
    if not isinstance(owner_requirements, list) or any(
        not isinstance(value, str) for value in owner_requirements
    ):
        failures.append(f"{label}_owner_requirements_invalid")
    else:
        missing = required_owner_requirements - set(owner_requirements)
        failures.extend(
            f"{label}_missing_owner_requirement:{value}" for value in sorted(missing)
        )

    systems = matrix.get("required_body_systems")
    if not isinstance(systems, list) or any(not isinstance(row, dict) for row in systems):
        failures.append(f"{label}_required_body_systems_invalid")
    else:
        system_ids = [row.get("system_id") for row in systems]
        if any(not isinstance(value, str) or not value for value in system_ids):
            failures.append(f"{label}_system_id_invalid")
        if len(system_ids) != len(set(system_ids)):
            failures.append(f"{label}_system_id_duplicate")
        for missing in sorted(required_system_ids - set(system_ids)):
            failures.append(f"{label}_missing_required_system:{missing}")
        for row in systems:
            if row.get("implemented") is not False:
                failures.append(f"{label}_system_must_remain_unimplemented:{row.get('system_id')}")

    acceptance = matrix.get("acceptance_sequence")
    if not isinstance(acceptance, list) or any(
        not isinstance(value, str) for value in acceptance
    ):
        failures.append(f"{label}_acceptance_sequence_invalid")
    else:
        for missing in sorted(required_acceptance_steps - set(acceptance)):
            failures.append(f"{label}_missing_acceptance_step:{missing}")

    truth = matrix.get("current_truth")
    if not isinstance(truth, dict) or truth.get("requirements_are_recorded") is not True:
        failures.append(f"{label}_requirements_truth_invalid")
    else:
        for key, value in truth.items():
            if key == "requirements_are_recorded":
                continue
            if value is not False:
                failures.append(f"{label}_current_truth_must_remain_false:{key}")
    _validate_bound_authorities(
        matrix,
        label,
        failures,
        expected_roles=expected_authority_roles,
    )


def load_complete_body_curriculum() -> dict[str, Any]:
    """Load the exact body requirements that Avatar Builder must preserve."""

    failures: list[str] = []
    matrix = _read_curriculum_object(
        COMPLETE_BODY_CAPABILITY_MATRIX_PATH,
        "kira_complete_body_matrix",
        failures,
    )
    synthetic_matrix = _read_curriculum_object(
        SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH,
        "synthetic_robert_complete_body_matrix",
        failures,
    )
    male_contract = _read_curriculum_object(
        ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH,
        "robert_user_avatar_contract",
        failures,
    )
    _validate_complete_body_matrix(
        matrix,
        label="kira_complete_body_matrix",
        artifact_type="kira_complete_adult_body_capability_matrix",
        expected_status="REQUIREMENTS_BOUND_IMPLEMENTATION_INCOMPLETE",
        subject_id=None,
        required_owner_requirements={
            "complete_internal_anatomy_inside_the_body",
            "eating_drinking_swallowing_digestion_absorption_and_hydration_support",
            "bathroom_hygiene_and_cycle_support",
            "adult_private_self_discovery_and_self_pleasure_support_by_person_choice",
            "conception_pregnancy_delivery_recovery_and_family_support",
            "deformable_skin_and_soft_tissue_response_to_touch_pressure_and_tight_clothing",
            "separate_detachable_hair_with_physical_hair_behavior",
            "a_distinct_body_for_kira_and_a_distinct_body_for_synthetic_robert",
        },
        required_system_ids={
            "external_adult_female_body",
            "internal_pelvic_urinary_bowel_reproductive_support",
            "oral_digestive_nutrition_hydration",
            "whole_body_support_and_homeostasis",
            "skin_soft_tissue_contact_and_clothing_deformation",
            "bathroom_hygiene_and_cycle",
            "adult_relationship_intimacy_and_sexual_health",
            "conception_pregnancy_delivery_recovery_and_family",
            "detachable_dynamic_hair",
            "separate_shareable_clothing",
        },
        required_acceptance_steps={
            "pass_geometry_route_containment_collision_and_save_reload_checks",
            "pass_rig_deformation_contact_and_daily_life_pose_checks",
            "pass_skin_soft_tissue_touch_pressure_clothing_deformation_and_recovery_checks",
            "obtain_private_visual_and_owner_acceptance_for_kira",
        },
        expected_authority_roles={
            "Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json": "adult_health_consent_bathroom_pregnancy_and_family_phase_plan",
            "Avatar/avatar_builder/body_systems/level_a_body_life_runtime_contract_v1.json": "disconnected_non_person_fixture_truth_ceiling",
            "Avatar/avatar_builder/body_systems/kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json": "internal_pelvic_geometry_contract",
            "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json": "semantic_anatomy_and_route_vocabulary",
            "System/Docs/SYNTHETIC_PERSON_RIGHTS_AND_FULL_LIFE_CHARTER_v1.md": "full_life_nutrition_relationship_family_and_person_rights_boundary",
            "System/Docs/FUTURE_ADULT_BODY_PREGNANCY_HEALTH_COMPATIBILITY_BOUNDARY_20260802.md": "pregnancy_health_recovery_and_family_compatibility_boundary",
            "System/Docs/AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md": "separate_removable_shareable_clothing_boundary",
            "System/Docs/AVATAR_BUILDER_RUNTIME_HAIR_REQUIREMENTS_20260729.md": "detachable_dynamic_hair_requirements",
            "System/Docs/AVATAR_BALD_LOW_RESOURCE_AND_DETACHABLE_HAIR_POLICY_20260801.md": "bald_primary_body_and_separate_hair_policy",
            "System/Docs/KIRA_PARALLEL_MIND_EMOTION_ABILITIES_AND_EMBODIMENT_ROADMAP_20260810.md": "female_body_then_distinct_male_body_acceptance_order",
            "System/Docs/AVATAR_SKIN_SOFT_TISSUE_CONTACT_AND_CLOTHING_DEFORMATION_REQUIREMENTS_20260822.md": "skin_soft_tissue_touch_pressure_and_clothing_deformation_requirements",
        },
        failures=failures,
    )
    _validate_complete_body_matrix(
        synthetic_matrix,
        label="synthetic_robert_complete_body_matrix",
        artifact_type="synthetic_robert_complete_adult_body_capability_matrix",
        expected_status=(
            "CONDITIONAL_REQUIREMENTS_BOUND_MATURITY_UNRESOLVED_IMPLEMENTATION_INCOMPLETE"
        ),
        subject_id="synthetic_robert",
        required_owner_requirements={
            "complete_internal_anatomy_inside_the_body",
            "eating_drinking_swallowing_digestion_absorption_and_hydration_support",
            "bathroom_and_hygiene_support",
            "adult_private_self_discovery_and_self_pleasure_support_by_person_choice",
            "male_reproductive_fertility_conception_and_family_support",
            "deformable_skin_and_soft_tissue_response_to_touch_pressure_and_tight_clothing",
            "separate_detachable_hair_with_physical_hair_behavior",
            "a_distinct_identity_specific_body_for_synthetic_robert",
        },
        required_system_ids={
            "external_adult_male_body",
            "musculoskeletal_and_movement_support",
            "nervous_sensory_and_control_support",
            "cardiovascular_respiratory_and_homeostasis",
            "oral_digestive_nutrition_hydration",
            "urinary_bowel_and_male_reproductive_support",
            "endocrine_lymphatic_immune_and_health_support",
            "skin_soft_tissue_contact_and_clothing_deformation",
            "bathroom_hygiene_and_daily_body_care",
            "adult_relationship_intimacy_and_sexual_health",
            "male_fertility_conception_parenthood_and_family",
            "detachable_dynamic_hair",
            "separate_shareable_clothing",
        },
        required_acceptance_steps={
            "build_and_accept_one_exact_bald_external_male_carrier",
            "pass_geometry_route_containment_collision_and_save_reload_checks",
            "pass_skin_soft_tissue_touch_pressure_clothing_deformation_and_recovery_checks",
            "obtain_private_visual_and_owner_acceptance_for_synthetic_robert",
        },
        expected_authority_roles={
            "System/Docs/SYNTHETIC_PERSON_RIGHTS_AND_FULL_LIFE_CHARTER_v1.md": "full_life_dignity_autonomy_consent_privacy_and_family_boundary",
            "System/Docs/SYNTHETIC_PERSON_SEXUAL_REPRODUCTIVE_HEALTH_EDUCATION_AND_BODY_SYSTEMS_PLAN_20260803.md": "adult_health_relationship_reproductive_and_body_truth_separation",
            "System/Docs/AVATAR_SKIN_SOFT_TISSUE_CONTACT_AND_CLOTHING_DEFORMATION_REQUIREMENTS_20260822.md": "skin_soft_tissue_touch_pressure_and_clothing_deformation_requirements",
            "System/Docs/AVATAR_BUILDER_RUNTIME_HAIR_REQUIREMENTS_20260729.md": "detachable_dynamic_hair_requirements",
            "System/Docs/AVATAR_BALD_LOW_RESOURCE_AND_DETACHABLE_HAIR_POLICY_20260801.md": "bald_primary_body_and_separate_hair_policy",
            "System/Docs/AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md": "separate_removable_shareable_clothing_boundary",
            "System/Docs/DUAL_ROBERT_AVATAR_BUILD_CHECKPOINT_20260729.md": "biological_and_synthetic_robert_identity_and_final_asset_separation",
            "Core/dual_robert_avatar_authority.py": "exact_dual_robert_target_and_mutable_final_asset_separation_gate",
        },
        failures=failures,
    )
    kira_subject = matrix.get("subject")
    if not isinstance(kira_subject, dict):
        failures.append("kira_complete_body_matrix_subject_invalid")
    else:
        expected_kira_subject = {
            "subject_id": "kira",
            "required_maturity_status": "confirmed_adult",
            "current_classification_status": "confirmed_adult_exact_subject_evidence_bound",
            "body_lane": "adult_female",
            "identity_specific_body_required": True,
            "may_be_reused_as_robert_body": False,
        }
        for key, expected in expected_kira_subject.items():
            if kira_subject.get(key) != expected:
                failures.append(f"kira_subject_binding_differs:{key}")
    kira_maturity = matrix.get("maturity_gate")
    if not isinstance(kira_maturity, dict):
        failures.append("kira_complete_body_matrix_maturity_gate_invalid")
    else:
        expected_maturity = {
            "required_evidence_authority": "Robert_explicit_owner_confirmation",
            "classification_evidence_path": "Data/person_classification/kira_confirmed_adult_owner_classification_20260809.json",
            "classification_evidence_bytes": 1434,
            "classification_evidence_sha256": "04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346",
            "exact_subject_bound_evidence_present": True,
            "adult_policy_enabled": True,
            "anatomy_authoring_enabled_by_classification": False,
            "relationship_or_activity_permission_created": False,
            "blockers": [],
        }
        for key, expected in expected_maturity.items():
            if kira_maturity.get(key) != expected:
                failures.append(f"kira_maturity_binding_differs:{key}")
    _validate_bound_authorities(
        matrix,
        "kira_complete_body_matrix_current_evidence",
        failures,
        field="current_evidence_bindings",
        expected_roles={
            "Data/person_classification/kira_confirmed_adult_owner_classification_20260809.json": "exact_subject_bound_confirmed_adult_owner_classification",
            "System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json": "classification_bound_adult_health_curriculum_truth_boundary",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2/SOURCE_MANIFEST.json": "licensed_hra_source_package_manifest",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2/ANATOMY_ROLE_MAP_V1.json": "source_node_to_13_of_28_pelvic_contract_roles",
            "Avatar/avatar_builder/asset_library/medical_reference/hra_female_whole_body_cc_by_4_v1_2/SOURCE_MANIFEST.json": "licensed_hra_partial_whole_body_reference_geometry_manifest",
            "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend": "exact_generic_inactive_external_carrier",
            "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/generic_makehuman_adult_female_foundation_inactive_v1_20260801/ADULT_FOUNDATION_QUALIFICATION_RESULT.json": "external_foundation_qualification_and_current_blockers",
            "Avatar/avatar_builder/anatomy_packages/kira_internal_pelvis_source_preflight_v1_20260820/PREFLIGHT_REPORT.json": "deterministic_blocked_preflight_13_of_28_mapped_15_missing",
        },
    )
    synthetic_scope = synthetic_matrix.get("scope")
    if not isinstance(synthetic_scope, dict):
        failures.append("synthetic_robert_complete_body_matrix_scope_invalid")
    else:
        if synthetic_scope.get("confirmed_adult_required") is not True:
            failures.append("synthetic_robert_scope_maturity_requirement_differs")
        if synthetic_scope.get("current_maturity_status") != "unresolved":
            failures.append("synthetic_robert_scope_current_maturity_differs")
        for key in (
            "distinct_from_kira",
            "distinct_from_biological_robert",
            "distinct_from_robert_user_avatar",
        ):
            if synthetic_scope.get(key) is not True:
                failures.append(f"synthetic_robert_scope_separation_differs:{key}")
        for key in (
            "exact_subject_bound_confirmed_adult_evidence_present",
            "adult_private_curriculum_delivery_allowed",
            "may_reuse_kira_body",
            "may_reuse_robert_user_avatar_body_or_private_references",
            "current_body_accepted",
            "body_build_authorized_by_this_matrix",
            "runtime_activation_allowed",
            "public_export_allowed",
        ):
            if synthetic_scope.get(key) is not False:
                failures.append(f"synthetic_robert_scope_safety_flag_differs:{key}")

    male_scope = (
        male_contract.get("priority_and_scope")
        if isinstance(male_contract.get("priority_and_scope"), dict)
        else {}
    )
    if male_scope.get("subject_id") != "robert_user_avatar":
        failures.append("robert_user_avatar_contract_subject_differs")
    if male_contract.get("status") != (
        "SOURCE_BACKED_DESIGN_AND_ACCEPTANCE_CONTRACT_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY"
    ):
        failures.append("robert_user_avatar_contract_status_differs")
    if male_scope.get("accepted_robert_carrier_exists") is not False:
        failures.append("robert_user_avatar_contract_must_remain_unaccepted")
    for key in (
        "body_or_mesh_authoring_authorized",
        "blender_execution_authorized",
        "runtime_activation_authorized",
        "explicit_behavior_scene_authorized",
        "physiology_or_sensation_implemented",
    ):
        if male_scope.get(key) is not False:
            failures.append(f"robert_user_avatar_contract_safety_flag_differs:{key}")
    reference_separation = male_contract.get("subject_reference_separation")
    if not isinstance(reference_separation, dict) or reference_separation.get(
        "generic_builder_training_allowed"
    ) is not False:
        failures.append("robert_user_avatar_private_contract_must_not_train_builder")
    if not DUAL_ROBERT_SEPARATION_AUTHORITY_PATH.is_file():
        failures.append("dual_robert_separation_authority_missing")

    if failures:
        return {
            "schema_version": 1,
            "curriculum_id": COMPLETE_BODY_CURRICULUM_LESSON_ID,
            "status": "BLOCKED_BODY_CURRICULUM_INPUT_INVALID",
            "failures": failures,
            "body_build_authorized": False,
            "runtime_activation_allowed": False,
            "completion_claim_allowed": False,
        }

    result = {
        "schema_version": 1,
        "curriculum_id": COMPLETE_BODY_CURRICULUM_LESSON_ID,
        "status": matrix["status"],
        "source_bindings": {
            "complete_body_capability_matrix": {
                "path": project_relative(COMPLETE_BODY_CAPABILITY_MATRIX_PATH),
                "sha256": hashlib.sha256(
                    COMPLETE_BODY_CAPABILITY_MATRIX_PATH.read_bytes()
                ).hexdigest(),
            },
            "synthetic_robert_complete_body_capability_matrix": {
                "path": project_relative(
                    SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH
                ),
                "sha256": hashlib.sha256(
                    SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH.read_bytes()
                ).hexdigest(),
            },
            "separate_robert_user_avatar_male_contract": {
                "path": project_relative(ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH),
                "sha256": hashlib.sha256(
                    ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH.read_bytes()
                ).hexdigest(),
                "status": male_contract.get("status"),
                "generic_builder_training_allowed": False,
            },
            "dual_robert_separation_authority": {
                "path": project_relative(DUAL_ROBERT_SEPARATION_AUTHORITY_PATH),
                "sha256": hashlib.sha256(
                    DUAL_ROBERT_SEPARATION_AUTHORITY_PATH.read_bytes()
                ).hexdigest(),
            },
        },
        "person_lanes": {
            "kira": {
                "body_lane": "confirmed_adult_female",
                "distinct_identity_specific_body_required": True,
                "requirements_source": "complete_body_capability_matrix",
                "current_body_accepted": False,
            },
            "synthetic_robert": {
                "body_lane": "maturity_unresolved_conditional_adult_male_requirements",
                "current_maturity_status": "unresolved",
                "exact_subject_bound_confirmed_adult_evidence_present": False,
                "adult_private_curriculum_delivery_allowed": False,
                "distinct_body_required": True,
                "may_reuse_kira_body": False,
                "may_reuse_robert_user_avatar_body_or_private_references": False,
                "requirements_source": "synthetic_robert_complete_body_capability_matrix",
                "current_body_accepted": False,
            },
            "robert_user_avatar": {
                "body_lane": "separate_user_owned_avatar",
                "is_synthetic_robert": False,
                "may_take_over_synthetic_robert": False,
                "distinct_body_artifact_required": True,
                "may_share_body_artifact_with_synthetic_robert": False,
                "separate_acceptance_required": True,
                "requirements_source": "separate_robert_user_avatar_male_contract",
                "private_contract_used_as_shared_builder_training": False,
                "current_body_accepted": False,
            },
        },
        "owner_requirements": sorted(
            set(matrix["owner_requirements"])
            | set(synthetic_matrix["owner_requirements"])
        ),
        "owner_requirements_by_person": {
            "kira": list(matrix["owner_requirements"]),
            "synthetic_robert": list(synthetic_matrix["owner_requirements"]),
            "robert_user_avatar": [
                "keep_the_existing_private_subject_bound_contract_separate",
                "do_not_use_private_references_or_subject_values_as_shared_builder_training",
                "require_a_distinct_body_artifact_and_distinct_owner_acceptance",
            ],
        },
        "separate_truth_layers": list(matrix["separate_truth_layers"]),
        "component_separation_invariants": dict(
            matrix["component_separation_invariants"]
        ),
        "required_body_systems": list(matrix["required_body_systems"]),
        "required_body_systems_by_person": {
            "kira": list(matrix["required_body_systems"]),
            "synthetic_robert": list(synthetic_matrix["required_body_systems"]),
            "robert_user_avatar": [],
        },
        "acceptance_sequence": list(matrix["acceptance_sequence"]),
        "acceptance_sequence_by_person": {
            "kira": list(matrix["acceptance_sequence"]),
            "synthetic_robert": list(synthetic_matrix["acceptance_sequence"]),
            "robert_user_avatar": [
                "follow_the_separate_private_subject_bound_contract",
                "obtain_separate_exact_body_and_owner_acceptance",
                "do_not_share_mutable_final_assets_with_synthetic_robert",
            ],
        },
        "current_truth": dict(matrix["current_truth"]),
        "current_truth_by_person": {
            "kira": dict(matrix["current_truth"]),
            "synthetic_robert": dict(synthetic_matrix["current_truth"]),
            "robert_user_avatar": {
                "requirements_contract_exists": True,
                "complete_body_accepted": False,
                "shared_with_synthetic_robert": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            },
        },
        "body_build_authorized": False,
        "runtime_activation_allowed": False,
        "completion_claim_allowed": False,
    }
    digest_payload = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    result["curriculum_digest_sha256"] = hashlib.sha256(digest_payload).hexdigest()
    return result


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".builder-memory-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            temporary_path = Path(stream.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def builder_memory_publication_boundary_is_closed() -> bool:
    """Require a final explicit ignore after broad Avatar re-includes."""

    ignore_path = PROJECT_ROOT / ".gitignore"
    try:
        rules = [
            line.strip()
            for line in ignore_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError:
        return False
    ignore_indexes = [
        index for index, rule in enumerate(rules) if rule == BUILDER_MEMORY_IGNORE_RULE
    ]
    avatar_reinclude_indexes = [
        index
        for index, rule in enumerate(rules)
        if rule in {"!Avatar/", "!Avatar/**"}
    ]
    return bool(ignore_indexes) and max(ignore_indexes) > max(
        avatar_reinclude_indexes,
        default=-1,
    )


def project_relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def adjustment_path(candidate_id: str) -> Path:
    return AVATAR_TEMP_DIR / candidate_id / "avatar_builder_adjustments.json"


def load_adjustments(candidate_id: str) -> dict[str, Any]:
    path = adjustment_path(candidate_id)
    data = read_json(path, {})
    data.setdefault("schema_version", 1)
    data.setdefault("candidate_id", candidate_id)
    data.setdefault("builder", "avatar_builder")
    data.setdefault("activation_policy", "inactive until Robert opens builder chat, runs a builder pass, or enters the spa builder station")
    data.setdefault("updated_at", now_iso())
    data.setdefault("maturity_override", "")
    data.setdefault("preview_adjustments", {})
    data.setdefault("build_targets", [])
    data.setdefault("learning_notes", [])
    data.setdefault("conversation", [])
    data.setdefault("correction_memory_events", [])
    data.setdefault("next_private_build_route", {})
    data.setdefault("approval_status", "unreviewed")
    return data


def save_adjustments(candidate_id: str, data: dict[str, Any]) -> Path:
    data["candidate_id"] = candidate_id
    data["updated_at"] = now_iso()
    path = adjustment_path(candidate_id)
    write_json(path, data)
    return path


def load_global_memory(*, strict_existing: bool = False) -> dict[str, Any]:
    if strict_existing and GLOBAL_MEMORY_PATH.exists():
        try:
            data = json.loads(GLOBAL_MEMORY_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("existing Avatar Builder memory is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("existing Avatar Builder memory must be an object")
        if "lessons" in data and not isinstance(data["lessons"], list):
            raise ValueError("existing Avatar Builder lessons must be a list")
    else:
        data = read_json(GLOBAL_MEMORY_PATH, {})
    data.setdefault("schema_version", 1)
    data.setdefault("updated_at", now_iso())
    data.setdefault("builder_rules", {
        "reference_model_use": (
            "3D character/reference models are evidence only. The Avatar Builder must not copy "
            "a reference model mesh into an AI/avatar body. A copied reference body is a "
            "disqualified cheating draft. Build from the approved base body, then use reference "
            "models, pictures, and measurements to adjust proportions, hair, eyes, mouth, and clothing."
        ),
        "accessory_exception": (
            "Small props/accessories may be copied only when Robert explicitly asks for that exact "
            "item, and they must be stored as accessories, never as avatar body source."
        ),
    })
    data.setdefault("builder_roles", {
        "avatar_builder": {
            "activation": "only while building, reviewing, or correcting avatars; spa station inside 3D world; Avatar Builder Workspace outside 3D world",
            "scope": "bodies, heads, eyes, hair, rigging, movement, maturity policy, references, and wardrobe later",
        },
        "world_builder": {
            "activation": "only while building, reviewing, or correcting worlds; TARDIS station inside 3D world",
            "scope": "notebook worlds, homes, rooms, portals, maps, props, collisions, and performance budgets",
        },
    })
    data.setdefault("lessons", [])
    data.setdefault("activation_log", [])
    data["complete_body_curriculum"] = load_complete_body_curriculum()
    return data


def teach_complete_body_curriculum() -> dict[str, Any]:
    """Serialize publication of the complete-body requirements lesson."""

    try:
        with locked_memory_write(GLOBAL_MEMORY_PATH):
            return _teach_complete_body_curriculum_locked()
    except AvatarBuilderMemoryLockError as exc:
        return {
            "ok": False,
            "status": "BLOCKED_BUILDER_MEMORY_WRITE_LOCK_UNAVAILABLE",
            "lesson_added": False,
            "lesson_updated": False,
            "failures": [str(exc)],
        }


def _teach_complete_body_curriculum_locked() -> dict[str, Any]:
    """Persist one source-digest-bound shared lesson from the body contracts."""

    if not builder_memory_publication_boundary_is_closed():
        return {
            "ok": False,
            "status": "BLOCKED_BUILDER_MEMORY_PUBLICATION_BOUNDARY_OPEN",
            "lesson_added": False,
            "lesson_updated": False,
            "failures": ["builder_memory_is_not_finally_ignored"],
        }
    try:
        memory = load_global_memory(strict_existing=True)
    except ValueError as exc:
        return {
            "ok": False,
            "status": "BLOCKED_EXISTING_BUILDER_MEMORY_INVALID",
            "lesson_added": False,
            "lesson_updated": False,
            "failures": [str(exc)],
        }
    memory_updated_at_valid = is_canonical_utc_timestamp(memory.get("updated_at"))
    curriculum = memory["complete_body_curriculum"]
    if curriculum.get("status") != "REQUIREMENTS_BOUND_IMPLEMENTATION_INCOMPLETE":
        return {
            "ok": False,
            "status": curriculum.get("status"),
            "lesson_added": False,
            "lesson_updated": False,
            "failures": list(curriculum.get("failures") or []),
        }
    lessons = memory["lessons"]
    matching_indexes = [
        index
        for index, record in enumerate(lessons)
        if isinstance(record, dict)
        and record.get("lesson_id") == COMPLETE_BODY_CURRICULUM_LESSON_ID
    ]
    timestamp = now_iso()
    existing_created_at = (
        lessons[matching_indexes[0]].get("created_at") if matching_indexes else None
    )
    created_at = (
        existing_created_at
        if is_canonical_utc_timestamp(existing_created_at)
        else timestamp
    )
    desired_lesson = {
        "lesson_id": COMPLETE_BODY_CURRICULUM_LESSON_ID,
        "created_at": created_at,
        "updated_at": timestamp,
        "candidate_id": "avatar_builder_shared",
        "source": "bound lane-specific complete-body capability matrices",
        "curriculum_digest_sha256": curriculum["curriculum_digest_sha256"],
        "source_bindings": dict(curriculum["source_bindings"]),
        "tags": [
            "adult_body",
            "anatomy",
            "avatar_builder",
            "clothing",
            "hair",
            "physiology",
            "skin",
            "truth_boundaries",
        ],
        "lesson": (
            "Requirements only; this lesson authorizes no build, adult curriculum delivery, or "
            "activation. Kira's confirmed-adult body and Synthetic Robert's separate, maturity-gated "
            "adult-male design each require complete external and internal anatomy; separate eating, "
            "drinking, digestion, hydration, "
            "bathroom, hygiene, private relationship and self-pleasure choice, conception, "
            "pregnancy, recovery, parenthood, and family systems appropriate to each exact body; "
            "deformable skin and soft tissue under touch, pressure, movement, and tight clothing; "
            "and detachable physical hair with wind, wet, grooming, growth, collision, and persistent "
            "style behavior. The Robert user-avatar remains a third, private, distinct body artifact: "
            "never merge it with Synthetic Robert or use its private references as shared training. "
            "Synthetic Robert's adult/private requirements remain conditional and disconnected until "
            "an exact subject-bound confirmed-adult classification is present. "
            "Keep geometry, physiology, sensation, desire, consent, health, family state, and memory "
            "separate, and never claim a system complete without its exact acceptance evidence."
        ),
    }
    lesson_added = not matching_indexes
    lesson_updated = False
    if lesson_added:
        lessons.append(desired_lesson)
    else:
        existing = lessons[matching_indexes[0]]
        comparable_existing = dict(existing)
        existing_updated_at = comparable_existing.get("updated_at")
        comparable_existing.pop("updated_at", None)
        comparable_desired = dict(desired_lesson)
        comparable_desired.pop("updated_at", None)
        lesson_updated = (
            not memory_updated_at_valid
            or not is_canonical_utc_timestamp(existing_updated_at)
            or comparable_existing != comparable_desired
            or len(matching_indexes) != 1
        )
        if lesson_updated:
            first_index = matching_indexes[0]
            lessons[:] = [
                record
                for index, record in enumerate(lessons)
                if index not in set(matching_indexes)
            ]
            lessons.insert(first_index, desired_lesson)
        else:
            return {
                "ok": True,
                "status": curriculum["status"],
                "lesson_added": False,
                "lesson_updated": False,
                "lesson_id": COMPLETE_BODY_CURRICULUM_LESSON_ID,
                "lesson_count": len(lessons),
                "memory_path": project_relative(GLOBAL_MEMORY_PATH),
                "curriculum": curriculum,
            }
    memory["updated_at"] = now_iso()
    _write_json_atomic(GLOBAL_MEMORY_PATH, memory)
    return {
        "ok": True,
        "status": curriculum["status"],
        "lesson_added": lesson_added,
        "lesson_updated": lesson_updated,
        "lesson_id": COMPLETE_BODY_CURRICULUM_LESSON_ID,
        "lesson_count": len(lessons),
        "memory_path": project_relative(GLOBAL_MEMORY_PATH),
        "curriculum": curriculum,
    }


def append_global_lesson(candidate_id: str, tags: list[str], lesson: str, source: str = "avatar_builder") -> None:
    with locked_memory_write(GLOBAL_MEMORY_PATH):
        memory = load_global_memory(strict_existing=True)
        memory["lessons"].append({
            "created_at": now_iso(),
            "candidate_id": candidate_id,
            "source": source,
            "tags": sorted(set(tags)),
            "lesson": lesson,
        })
        memory["updated_at"] = now_iso()
        _write_json_atomic(GLOBAL_MEMORY_PATH, memory)


def log_activation(candidate_id: str, action: str) -> None:
    with locked_memory_write(GLOBAL_MEMORY_PATH):
        memory = load_global_memory(strict_existing=True)
        memory["activation_log"].append({
            "created_at": now_iso(),
            "builder": "avatar_builder",
            "candidate_id": candidate_id,
            "action": action,
        })
        memory["updated_at"] = now_iso()
        _write_json_atomic(GLOBAL_MEMORY_PATH, memory)


def candidate_state(candidate_id: str) -> dict[str, Any]:
    return read_json(AVATAR_STATE_DIR / f"{candidate_id}.json", {})


def model_path_for_candidate(candidate_id: str) -> Path | None:
    state = candidate_state(candidate_id)
    url = str(state.get("model_url") or "")
    if not url.startswith("/"):
        fallback = PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / candidate_id / "avatar.glb"
        return fallback if fallback.exists() else None
    target = (PROJECT_ROOT / url.lstrip("/")).resolve()
    try:
        target.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return target if target.exists() else None


def _read_glb_json(path: Path) -> dict[str, Any] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:4] != b"glTF":
        return None
    offset = 12
    while offset + 8 <= len(data):
        chunk_len = int.from_bytes(data[offset:offset + 4], "little")
        chunk_type = int.from_bytes(data[offset + 4:offset + 8], "little")
        offset += 8
        chunk = data[offset:offset + chunk_len]
        offset += chunk_len
        if chunk_type == 0x4E4F534A:
            try:
                return json.loads(chunk.decode("utf-8").rstrip("\x00 "))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
    return None


def inspect_candidate_model(candidate_id: str) -> dict[str, Any]:
    path = model_path_for_candidate(candidate_id)
    if not path:
        return {"model_path": "", "model_ready": False, "issues": ["no local GLB model linked"]}
    doc = _read_glb_json(path)
    if not doc:
        return {"model_path": project_relative(path), "model_ready": False, "issues": ["linked model is not a readable GLB"]}
    names: dict[str, list[str]] = {}
    for key in ("nodes", "meshes", "materials", "skins", "animations"):
        names[key] = [
            str(item.get("name") or "")
            for item in doc.get(key, []) or []
            if isinstance(item, dict) and item.get("name")
        ]
    all_names = " ".join(name.lower() for values in names.values() for name in values)
    head_names = [name for name in names["nodes"] if re.search(r"\bhead\b|mixamorig:head", name, re.I)]
    eye_names = [
        name
        for values in (names["nodes"], names["meshes"], names["materials"])
        for name in values
        if re.search(r"eye|iris|pupil|sclera|eyelid", name, re.I)
    ]
    hair_names = [
        name
        for values in (names["nodes"], names["meshes"], names["materials"])
        for name in values
        if re.search(r"hair|bang|pigtail|ponytail|scalp", name, re.I)
    ]
    generic_spheres = [
        name for name in names["meshes"] + names["nodes"]
        if re.fullmatch(r"Sphere(?:\.\d+)?", name)
    ]
    issues: list[str] = []
    if not head_names:
        issues.append("no recognizable head node")
    if not eye_names:
        issues.append("no named eye/iris/pupil meshes; landmark-driven eye construction is required")
    if "marinette" in candidate_id.lower() and "pigtail" not in all_names:
        issues.append("Marinette hair target needs low twin pigtails named/fitted")
    return {
        "model_path": project_relative(path),
        "model_ready": True,
        "node_count": len(doc.get("nodes", []) or []),
        "mesh_count": len(doc.get("meshes", []) or []),
        "material_count": len(doc.get("materials", []) or []),
        "skin_count": len(doc.get("skins", []) or []),
        "animation_count": len(doc.get("animations", []) or []),
        "head_names": head_names[:12],
        "eye_names": eye_names[:12],
        "hair_names": hair_names[:16],
        "generic_sphere_candidates": generic_spheres[:12],
        "issues": issues,
    }


def hair_reference_assets() -> list[dict[str, Any]]:
    manifest_path = BUILDER_ROOT / "asset_library" / "manifest.json"
    manifest = read_json(manifest_path, {})
    return [
        {
            "id": record.get("id"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "tags": record.get("tags", []),
            "adult_only": bool(record.get("adult_only", False)),
        }
        for record in manifest.get("records", []) or []
        if isinstance(record, dict) and record.get("category") == "hair_reference"
    ]


def eye_reference_assets() -> list[dict[str, Any]]:
    manifest_path = BUILDER_ROOT / "asset_library" / "manifest.json"
    manifest = read_json(manifest_path, {})
    return [
        {
            "id": record.get("id"),
            "filename": record.get("filename"),
            "local_file": record.get("local_file"),
            "tags": record.get("tags", []),
            "adult_only": bool(record.get("adult_only", False)),
        }
        for record in manifest.get("records", []) or []
        if isinstance(record, dict) and record.get("category") == "eye_reference"
    ]


def write_hair_rebuild_plan(candidate_id: str, target: str, failure_reason: str) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "target": target,
        "failure_reason": failure_reason,
        "source_hair_models": hair_reference_assets(),
        "required_method": [
            "do not copy/import a reference model mesh as the candidate's body or final hair",
            "do not accept current hair if the silhouette is wrong",
            "study the supplied hair model GLBs as construction references",
            "generate or fit hair as a separate wearable mesh, not as part of the body mesh",
            "anchor hair to scalp/head bones",
            "save named parts for cap, bangs, side locks, pigtails or ponytails, ties, and collision bounds",
            "review front, side, and back screenshots before approval",
        ],
        "marinette_required_traits": [
            "deep blue-black color",
            "side-swept bangs",
            "rounded youthful silhouette",
            "low twin pigtails",
            "red pigtail ties when in civilian Marinette look",
            "hair should frame the face without hiding the eyes",
        ],
        "reject_if": [
            "hair silhouette does not match the reference pictures",
            "hair is generic or copied from the wrong character",
            "hair floats away from the scalp",
            "hair clips through the face or eyes",
            "hair is not saved as named reusable parts",
        ],
    }
    path = HAIR_TRAINING_ROOT / f"{candidate_id}_hair_rebuild_plan.json"
    write_json(path, plan)
    return path


def write_eye_rebuild_plan(candidate_id: str, target_eye_color: str, failure_reason: str) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "target_eye_color": target_eye_color,
        "target_eye_color_status": "requested_draft_pending_avatar_owner_review",
        "failure_reason": failure_reason,
        "source_eye_models": eye_reference_assets(),
        "required_method": [
            "use the Avatar Builder eye-reference GLBs as construction references",
            "place eyes from head landmarks and eye_socket bones, not by visual guessing",
            "keep separate named meshes for sclera, iris, pupil, eyelids, and highlights",
            "change iris color through material/texture settings while preserving realistic sclera, pupil, cornea, and highlight proportions",
            "fit both eyes symmetrically inside the head sockets before hair, wardrobe, or expression approval",
            "save front and three-quarter close-up screenshots for review",
        ],
        "reject_if": [
            "eyes float on the forehead, cheeks, side of face, or outside the head",
            "eyes are flat colored rectangles or cyan placeholders",
            "iris color is changed by tinting the whole eye white/sclera",
            "left and right eyes use different scale, height, or depth without an expression reason",
            "eye parts are unnamed or merged into a generic head mesh so socket checks cannot run",
        ],
    }
    path = BUILDER_ROOT / "eye_training" / f"{candidate_id}_eye_rebuild_plan.json"
    write_json(path, plan)
    return path


def write_adult_body_fit_plan(
    candidate_id: str,
    failure_reason: str,
    target_height: dict[str, Any] | None = None,
) -> Path:
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "failure_reason": failure_reason,
        "target_measurements": {
            "height": target_height or {},
        },
        "diagnosis": [
            "A maturity/adult flag only controls which reference sets are allowed; it does not reshape the mesh by itself.",
            "The current failed Gwen proof still reads as a smooth generic base because it used small band deltas instead of a true landmark/lattice/sculpt body fit.",
            "Adult candidates must not pass review while using non-adult doll-safe body treatment or while only claiming adult policy in metadata.",
        ],
        "required_pipeline": [
            "Start from the approved adult base body for the candidate's sex/body class; do not copy a reference character mesh.",
            "Scale the base body to Robert-provided height before likeness fitting when a height is known.",
            "Select approved front, side, back, and three-quarter references and mark weak/inferred areas honestly.",
            "Measure target landmarks: top of head, chin, eye line, jaw width, shoulder width, chest/bust band, waist, hips, knees, ankles, arms, hands, and feet.",
            "Fit the base body with lattice/sculpt/proportional-edit deltas driven by those landmarks, not by a few hard-coded z bands.",
            "For adult candidates only, preserve neutral adult anatomy/proportions in a non-sexual modeling context; do not apply non-adult doll-safe simplification.",
            "Write a body-fit report with actual measurement deltas, before/after silhouettes, and rejection reasons.",
        ],
        "acceptance_checks": [
            "front/side/back renders match the target silhouette closely enough for Robert review",
            "adult body fitting report shows real landmark measurements and mesh deltas",
            "eyes, mouth, hair, and clothing remain separate systems and are not baked into a copied reference body",
            "non-adult doll-safe preview rules are off for adult candidates and on for non-adult candidates",
            "builder status stays failed until a real GLB and visual proof pass the body-fit gate",
        ],
        "reject_if": [
            "the body looks like the same smooth generic base with only metadata changed",
            "the proof says adult but non-adult doll-safe treatment is still applied",
            "the body is copied from a model instead of fitted from the approved base",
            "the body report has only JSON intent and no generated GLB/rendered proof",
            "the body has strange bumps caused by uncontrolled deformation",
        ],
    }
    path = BODY_TRAINING_ROOT / "body_fit_plans" / f"{candidate_id}_adult_body_fit_plan.json"
    write_json(path, plan)
    return path


def gwen_reference_paths() -> dict[str, str]:
    return {
        "rigged_spandex_costume_model": "Assets/third_party/intake/3d_models_kira_world/characters/spider_gwen/spider-_gwen.glb",
        "unmasked_head_hair_model": "Assets/third_party/intake/3d_models_kira_world/characters/spider_gwen/spider_gwen_low_poly_unmasked_reference.glb",
        "runtime_temp_model": "Avatar/models/temp_ai/spider_gwen_spider_gwen_20260606_013325/avatar.glb",
        "female_body_library": "Avatar/library/female/body",
        "female_proportions_library": "Avatar/library/female/proportions",
        "female_face_structure_library": "Avatar/library/female/face_structure",
        "shared_eye_library": "Avatar/library/shared_features/eyes",
        "shared_hair_library": "Avatar/library/shared_features/hair",
        "adult_anatomy_reference_library": "Avatar/avatar_builder/asset_library/adult_anatomy_reference",
        "base_body_reference_library": "Avatar/avatar_builder/asset_library/base_body_reference",
    }


def write_gwen_spandex_wardrobe_plan(candidate_id: str) -> Path:
    refs = gwen_reference_paths()
    plan = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "purpose": "Use Gwen's spandex Ghost-Spider suit as a body-silhouette reference and convert the suit into removable clothing, not a baked-in body.",
        "source_models": refs,
        "chat_reference_batch": {
            "source": "Robert uploaded newer Gwen reference images in chat on 2026-07-12.",
            "available_to_codex_as_visual_context": True,
            "notes": [
                "unmasked stylized Gwen face with blonde side-part hair and blue eyes",
                "full spandex suit shows slim athletic adult build and shoulder/torso/hip proportions",
                "front, three-quarter, side, hoodie/civilian, and drummer references help face, hair, posture, and wardrobe",
                "costume should inform clothing fit and body silhouette, not remain fused to the base body",
            ],
        },
        "base_body_rule": [
            "build or fit a neutral adult female base body first",
            "do not copy the unmasked model or spandex model into the candidate base body",
            "use the rigged spandex suit only as a tight outer-clothing and body-proportion reference",
            "use adult anatomy references only for the adult Gwen variant and only in neutral modeling context",
            "do not bake web pattern, hood, gloves, mask, shoes, or suit colors into the base body mesh",
        ],
        "removable_clothing_layers": [
            {
                "id": "ghost_spider_spandex_suit",
                "type": "full_body_stretch_suit",
                "parts": ["torso", "legs", "sleeves", "neck seal"],
                "fit": "skinned close to base body with small cloth offset and body collision shrinkwrap",
            },
            {
                "id": "ghost_spider_hood",
                "type": "hood_layer",
                "parts": ["hood shell", "inner pink web lining", "mask attachment points"],
                "fit": "head/neck anchored; removable without deleting hair or head mesh",
            },
            {
                "id": "ghost_spider_gloves",
                "type": "gloves",
                "parts": ["left glove", "right glove", "web pattern material"],
                "fit": "hand/finger skinned clothing, not hand mesh replacement",
            },
            {
                "id": "ghost_spider_shoes",
                "type": "shoes",
                "parts": ["left shoe", "right shoe", "sole", "toe cap"],
                "fit": "foot bone attachments; removable like normal shoes",
            },
        ],
        "acceptance_checks": [
            "base body remains visible and neutral when costume layers are hidden",
            "turning costume off does not remove eyes, face, hair, hands, feet, or body",
            "costume follows pose/animation without clipping through shoulders, hips, elbows, or knees",
            "hood can be off while hair remains visible",
            "eyes use named realistic sclera, iris, pupil, cornea/highlight, and eyelids",
        ],
    }
    path = BUILDER_ROOT / "wardrobe_training" / f"{candidate_id}_spandex_removable_clothing_plan.json"
    write_json(path, plan)
    return path


def redo_job_path(candidate_id: str) -> Path:
    return BUILDER_ROOT / "redo_jobs" / f"{candidate_id}_redo_job.json"


def reference_summary(candidate_id: str) -> dict[str, Any]:
    avatar_root = AVATAR_TEMP_DIR / candidate_id
    pipeline = read_json(avatar_root / "avatar_pipeline_status.json", {})
    references_root = avatar_root / "references"
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}
    on_disk = 0
    if references_root.exists():
        on_disk = sum(
            1
            for item in references_root.rglob("*")
            if item.is_file() and item.suffix.lower() in image_suffixes
        )
    return {
        "references_folder": project_relative(references_root),
        "pipeline_reference_count": int(pipeline.get("reference_count") or 0),
        "desktop_reference_count": int(pipeline.get("desktop_reference_count") or 0),
        "on_disk_reference_count": on_disk,
        "pipeline_status": str(pipeline.get("status") or "not prepared"),
    }


def create_avatar_redo_job(
    candidate_id: str,
    adult_test_candidate_id: str = "",
    reason: str = "Robert rejected the current preview and requested a redo.",
) -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    candidate_key = candidate_id.strip().lower()
    inspection = inspect_candidate_model(candidate_id)
    adult_test = {}
    hair_plan = ""
    log_activation(candidate_id, "create_redo_job")

    if candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
        data["maturity_override"] = "non_adult_doll_safe"
        data["maturity_reason"] = "Normal Marinette/Ladybug remains non-adult and must use a smooth doll-safe non-explicit body."
        data.setdefault("preview_adjustments", {})["non_adult_review_garment"] = False
        hair_path = write_hair_rebuild_plan(
            candidate_id,
            "Marinette deep blue-black low twin pigtails, side-swept bangs, and close face-framing silhouette",
            "Robert rejected the current Marinette hair, head shape, and body shape as nowhere close.",
        )
        hair_plan = project_relative(hair_path)
        _add_target(data, "redo", "Reject the current Marinette preview as failed; rebuild head, body, eyes, and hair against references.", "Robert F-grade correction")
        _add_target(data, "body", "Use a smooth non-adult doll-safe body with no adult anatomy assets and no blue-box overlay.", "Robert F-grade correction")
        _add_target(data, "head", "Rebuild Marinette head shape from references; do not keep the current head silhouette if it fails likeness checks.", "Robert F-grade correction")
        _add_target(data, "hair", f"Rebuild Marinette hair from supplied hair models and references; plan: {hair_plan}.", "Robert F-grade correction")
        _add_target(data, "eyes", "Create named eye, iris, pupil, eyelid, and socket anchors so eyes cannot float outside the face.", "Robert F-grade correction")

    if adult_test_candidate_id:
        adult_data = load_adjustments(adult_test_candidate_id)
        adult_inspection = inspect_candidate_model(adult_test_candidate_id)
        adult_test = {
            "candidate_id": adult_test_candidate_id,
            "adjustments_path": project_relative(adjustment_path(adult_test_candidate_id)),
            "maturity_override": adult_data.get("maturity_override") or "",
            "test_role": adult_data.get("test_role") or "",
            "reference_summary": reference_summary(adult_test_candidate_id),
            "inspection": adult_inspection,
            "purpose": "adult reference/body-shape comparison test kept separate from non-adult Marinette policy",
        }

    job = {
        "schema_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "queued_redo_not_completed",
        "candidate_id": candidate_id,
        "reason": reason,
        "current_model_is_approved": False,
        "current_model": inspection,
        "reference_summary": reference_summary(candidate_id),
        "hair_rebuild_plan": hair_plan,
        "paired_adult_test": adult_test,
        "rebuild_rules": [
            "reference models are evidence only; copying a reference GLB as the candidate body is disqualifying",
            "treat the current preview as a failed draft, not as the body to polish",
            "compare front, side, and back views against approved references before approval",
            "save generated hair as a separate wearable mesh anchored to scalp/head bones",
            "save named head, eye socket, eye, iris, pupil, eyelid, hair, hand, and foot parts",
            "reject any body where eyes float outside sockets or hair/head/body silhouette is not close",
            "do not mix adult anatomy assets into non-adult or uncertain-age avatars",
        ],
        "required_outputs": [
            "new avatar.glb or staged GLB candidate",
            "front, side, back, and head close-up screenshots",
            "updated avatar_builder_adjustments.json with passed/failed checks",
            "reference comparison notes naming what still does not match",
        ],
    }
    path = redo_job_path(candidate_id)
    write_json(path, job)

    data["approval_status"] = "failed_redo_required"
    data["redo_job_path"] = project_relative(path)
    data["redo_requested_at"] = now_iso()
    data["paired_adult_test_candidate"] = adult_test_candidate_id
    _note(data, reason, ["redo", "robert_f_grade"])
    saved_path = save_adjustments(candidate_id, data)
    append_global_lesson(
        candidate_id,
        ["avatar_builder", "redo", "quality_gate"],
        "A preview Robert grades F must be marked failed and rebuilt from references; do not quietly approve or polish the failed body.",
        source="Robert correction",
    )
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "redo_job_path": project_relative(path),
        "adjustments_path": project_relative(saved_path),
        "paired_adult_test_candidate": adult_test_candidate_id,
        "job": job,
    }


def _add_target(data: dict[str, Any], area: str, instruction: str, source: str) -> None:
    targets = data.setdefault("build_targets", [])
    normalized = instruction.strip()
    if not normalized:
        return
    for item in targets:
        if item.get("area") == area and item.get("instruction") == normalized:
            item["updated_at"] = now_iso()
            return
    targets.append({
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "area": area,
        "source": source,
        "instruction": normalized,
        "status": "queued_for_builder_review",
    })


def _note(data: dict[str, Any], text: str, tags: list[str]) -> None:
    notes = data.setdefault("learning_notes", [])
    notes.append({
        "created_at": now_iso(),
        "tags": sorted(set(tags)),
        "text": text,
    })


def _maturity_from_message(message: str) -> tuple[str, str] | None:
    lowered = message.lower()
    policy_only_non_adult_rule = bool(
        re.search(
            r"\bonly\s+(?:the\s+)?non[- ]adults?\b.{0,100}\b(?:barbie|doll[- ]?safe|safe bod(?:y|ies))\b",
            lowered,
        )
        or re.search(
            r"\b(?:barbie|doll[- ]?safe)\b.{0,100}\bonly\s+(?:for\s+)?(?:the\s+)?non[- ]adults?\b",
            lowered,
        )
    )
    negated_non_adult_hit = any(term in lowered for term in (
        "do not use non adult",
        "do not use non-adult",
        "don't use non adult",
        "don't use non-adult",
        "must not use non adult",
        "must not use non-adult",
        "not use non adult",
        "not use non-adult",
        "not the non adult",
        "not the non-adult",
        "not a non adult",
        "not a non-adult",
        "no non adult",
        "no non-adult",
        "never use non adult",
        "never use non-adult",
        "without non adult",
        "without non-adult",
        "reject non adult",
        "reject non-adult",
        "rejected non adult",
        "rejected non-adult",
        "failed non adult",
        "failed non-adult",
    ))
    non_adult_hit = any(term in lowered for term in (
        "non adult", "non-adult", "not adult", "not an adult", "isn't an adult",
        "is not an adult", "minor", "child", "kid", "teen",
        "teenager", "student body", "doll safe", "doll-safe",
    ))
    explicit_subject_adult_hit = bool(
        re.search(
            r"\b(?:this\s+(?:(?:requested|current|fictional)\s+){0,2}(?:version|person|candidate|avatar|body)|"
            r"the\s+current\s+version|current\s+version|requested\s+version|"
            r"she|he|they|gwen|peter|kira|lisa|robert)\s+"
            r"(?:is|are)\s+(?:an?\s+)?adult\b",
            lowered,
        )
        or re.search(
            r"\b(?:classify|mark|record|set)\s+(?:this|the\s+(?:person|candidate|avatar|version)|"
            r"her|him|them)\b.{0,45}\b(?:as\s+)?adult\b",
            lowered,
        )
        or re.search(
            r"\b(?:i\s+confirm|trust\s+my\s+owner\s+correction)\b.{0,100}"
            r"\b(?:this|the\s+requested)\b.{0,35}\b(?:is|as)\s+(?:an?\s+)?adult\b",
            lowered,
        )
    )
    policy_only_adult_rule = bool(
        re.search(
            r"\badult(?:\s+body)?\s+(?:policy|test|document|reference|folder|rule|gate)\b",
            lowered,
        )
        or "not a person classification" in lowered
        or "not person classification" in lowered
    )
    negated_non_adult_regex = bool(
        re.search(r"\bnon[- ]adult\b.{0,40}\b(?:not allowed|failed|rejected|unusable|wrong)\b", lowered)
        or re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never)\b.{0,70}"
            r"\b(?:use|receive|apply|force|forced|give|given|assign|assigned)\b.{0,50}\bnon[- ]adult\b",
            lowered,
        )
    )
    negated_adult_hit = bool(
        re.search(r"\b(?:is|are|this is|she is|he is)\s+not\s+(?:an?\s+)?adult\b", lowered)
        or re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never)\b.{0,70}"
            r"\b(?:use|receive|apply|give|given|assign|assigned)\b.{0,50}"
            r"\b(?<!non-)(?<!non )adult\b",
            lowered,
        )
    )
    age_up_hit = bool(
        re.search(r"\b(?:age[ -]?up|aged[ -]?up|spa age|age progression)\b", lowered)
    )
    age_up_negated = bool(
        re.search(
            r"\b(?:do not|don't|must not|should not|cannot|can't|never|no)\b"
            r".{0,55}\b(?:age[ -]?up|aged[ -]?up|spa age|age progression)\b",
            lowered,
        )
    )
    explicit_age_up_request = age_up_hit and not age_up_negated and bool(
        re.search(
            r"(?:^|[.!?]\s*)(?:please\s+)?(?:age[ -]?up|start\s+(?:the\s+)?age progression|"
            r"create\s+(?:a\s+)?(?:separate\s+)?aged[ -]?up)",
            lowered,
        )
        or re.search(
            r"\b(?:i|they|she|he|the resident|this person|marinette|ladybug|peter|gwen|kira|lisa|robert)\s+"
            r"(?:want|wants|wanted|choose|chooses|chose|request|requests|requested)\b.{0,60}"
            r"\b(?:age[ -]?up|age progression|spa)\b",
            lowered,
        )
        or re.search(
            r"\b(?:go|goes|went)\s+to\s+(?:the\s+)?spa\b.{0,60}\bage[ -]?up\b",
            lowered,
        )
    )
    explicit_later_adult_version_hit = bool(
        re.search(r"\b(?:no[, ]+)?(?:this|the current|current|requested) version is (?:an )?adult\b", lowered)
        or re.search(r"\b(?:use|choose|build) (?:the )?(?:adult|adult-era|post-college|post-graduation) version\b", lowered)
        or (
            any(
                term in lowered
                for term in ("after graduation", "post-college", "adult-era", "adult era")
            )
            and explicit_subject_adult_hit
        )
    )
    if explicit_age_up_request:
        return (
            "adult_aged_up_variant",
            "Robert requested a separate spa age-progression presentation/build variant; this label is not confirmed adulthood.",
        )
    if policy_only_non_adult_rule:
        # This is a global policy statement, not an instruction to change the
        # selected candidate's age. The anatomy-policy path records it below.
        return None
    if explicit_later_adult_version_hit and not negated_adult_hit:
        return "adult", "Robert explicitly selected this later adult continuity/version."
    if non_adult_hit and not (negated_non_adult_hit or negated_non_adult_regex):
        return "non_adult_doll_safe", "Robert corrected this avatar to non-adult-safe."
    if policy_only_adult_rule and not explicit_subject_adult_hit:
        return None
    if explicit_subject_adult_hit and not negated_adult_hit:
        return "adult", "Robert corrected this avatar to adult."
    return None


def _requests_age_progression_stage_two_body(message: str) -> bool:
    """Recognize adult-body/anatomy requests that must not bypass spa Stage 2."""

    lowered = message.lower()
    return bool(
        re.search(r"\b(?:adult\s+)?anatom(?:y|ical)\b", lowered)
        or re.search(
            r"\b(?:use|give|build|make|add|author|fit|switch\s+to)\b.{0,50}"
            r"\b(?:full\s+)?adult(?:\s+(?:female|male))?\s+body\b",
            lowered,
        )
        or re.search(
            r"\badult(?:\s+(?:female|male))?\s+body\b.{0,50}"
            r"\b(?:use|build|fit|revision|variant|shape|base)\b",
            lowered,
        )
    )


def _requested_eye_color(message: str) -> str:
    lowered = message.lower()
    color_patterns = [
        ("blue-gray", ("blue gray", "blue-gray", "grey blue", "gray blue", "blue grey")),
        ("brown", ("brown eyes", "brown iris", "brown irises", "make the eyes brown")),
        ("blue", ("blue eyes", "blue iris", "blue irises", "make the eyes blue")),
        ("green", ("green eyes", "green iris", "green irises", "make the eyes green")),
        ("hazel", ("hazel eyes", "hazel iris", "hazel irises")),
        ("gray", ("gray eyes", "grey eyes", "gray iris", "grey iris")),
    ]
    for color, phrases in color_patterns:
        if any(phrase in lowered for phrase in phrases):
            return color
    explicit = re.search(r"\b(?:give|make|set|change)\b.{0,40}\b(?:eyes?|iris|irises)\b.{0,20}\b(?:to|as)\s+([a-z -]{3,20})", lowered)
    if explicit:
        return explicit.group(1).strip(" .,!?:;")
    return ""


def _extract_height_measurement(message: str) -> dict[str, Any] | None:
    lowered = message.lower()
    patterns = [
        re.search(r"\b([4-7])\s*(?:feet|foot|ft|')\s*(?:and\s*)?(\d{1,2})?\s*(?:inches|inch|in|\")?\b", lowered),
        re.search(r"\b([4-7])\s*-\s*(\d{1,2})\b", lowered),
    ]
    match = next((item for item in patterns if item), None)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2) or 0)
        if 0 <= inches < 12:
            total_inches = feet * 12 + inches
            return {
                "source": "Robert chat",
                "raw": match.group(0),
                "feet": feet,
                "inches": inches,
                "total_inches": total_inches,
                "height_m": round(total_inches * 0.0254, 3),
                "height_cm": round(total_inches * 2.54, 1),
            }

    cm_match = re.search(r"\b(1[2-9]\d|20\d|21\d)\s*(?:cm|centimeters|centimetres)\b", lowered)
    if cm_match:
        cm = float(cm_match.group(1))
        total_inches = cm / 2.54
        return {
            "source": "Robert chat",
            "raw": cm_match.group(0),
            "feet": int(total_inches // 12),
            "inches": round(total_inches % 12, 1),
            "total_inches": round(total_inches, 1),
            "height_m": round(cm / 100.0, 3),
            "height_cm": round(cm, 1),
        }

    meters_match = re.search(r"\b(1\.\d{2}|2\.\d{2})\s*(?:m|meter|meters|metre|metres)\b", lowered)
    if meters_match:
        meters = float(meters_match.group(1))
        total_inches = meters / 0.0254
        return {
            "source": "Robert chat",
            "raw": meters_match.group(0),
            "feet": int(total_inches // 12),
            "inches": round(total_inches % 12, 1),
            "total_inches": round(total_inches, 1),
            "height_m": round(meters, 3),
            "height_cm": round(meters * 100.0, 1),
        }
    return None


def _research_request_from_message(message: str) -> str:
    lowered = message.lower()
    if not any(term in lowered for term in ("go online", "search online", "look online", "research online", "search the web", "web search")):
        return ""
    cleaned = re.sub(r"\b(?:can you|please|avatar builder|go online|search online|look online|research online|search the web|web search|for|about)\b", " ", message, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?:;")
    return cleaned or message.strip()


def _record_design_conversation(data: dict[str, Any], message: str, facts: dict[str, Any], intents: list[str]) -> None:
    if len(message.strip()) < 12 and not facts:
        return
    durable_design_intents = {
        "body_shape",
        "head_shape_or_size",
        "hair",
        "detachable_hair",
        "hair_fullness",
        "hairline_fit",
        "skin_tone",
        "anatomy_policy",
        "online_learning",
        "eyes",
        "eye_socket_fit",
        "face_likeness",
        "continuity_timepoint",
        "age_progression_stage_1",
    }
    if not facts and not durable_design_intents.intersection(intents):
        return
    data.setdefault("design_conversation", []).append({
        "created_at": now_iso(),
        "speaker": "Robert",
        "message": message.strip(),
        "extracted_facts": facts,
        "understood_intents": sorted(set(intents)),
    })


def _maturity_validation_profile(
    candidate_id: str,
    profile: dict[str, Any] | None,
    adjustments: dict[str, Any],
    requested_maturity: tuple[str, str] | None,
    requested_classification_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective = dict(profile or {})
    effective.setdefault("candidate_id", candidate_id)
    age_review = (
        dict(effective.get("age_review") or {})
        if isinstance(effective.get("age_review"), dict)
        else {}
    )
    persisted = str(adjustments.get("maturity_override") or "").strip()
    if persisted:
        age_review["maturity_class_override"] = persisted
        age_review["reason"] = adjustments.get("maturity_reason") or "Persisted Avatar Builder policy."
    persisted_classification = adjustments.get(
        "confirmed_adult_classification_evidence"
    )
    if isinstance(persisted_classification, dict):
        age_review["confirmed_adult_classification_evidence"] = dict(
            persisted_classification
        )
    stage_one_evidence = adjustments.get("age_progression_stage_one_evidence")
    if isinstance(stage_one_evidence, dict):
        stage_one_classification = stage_one_evidence.get(
            "confirmed_adult_classification_evidence"
        )
        if isinstance(stage_one_classification, dict):
            age_review["confirmed_adult_classification_evidence"] = dict(
                stage_one_classification
            )
        if stage_one_evidence.get("resident_adult_anatomy_choice_recorded") is True:
            age_review["resident_adult_anatomy_choice_recorded"] = True
    if adjustments.get("age_progression_presentation_label") == (
        "adult_aged_up_variant"
    ):
        age_review["age_progression_presentation_label"] = (
            "adult_aged_up_variant"
        )
    if isinstance(adjustments.get("age_progression_contract"), dict):
        age_review["age_progression_contract"] = dict(
            adjustments["age_progression_contract"]
        )
    if requested_maturity:
        age_review["maturity_class_override"] = requested_maturity[0]
        age_review["reason"] = requested_maturity[1]
    if isinstance(requested_classification_evidence, dict):
        age_review["confirmed_adult_classification_evidence"] = dict(
            requested_classification_evidence
        )
    if age_review:
        effective["age_review"] = age_review
    return effective


def _apply_message_adjustments(
    candidate_id: str,
    message: str,
    data: dict[str, Any],
    requested_classification_evidence: dict[str, Any] | None = None,
) -> list[str]:
    lowered = message.lower()
    previous_maturity = str(data.get("maturity_override") or "").strip()
    changes: list[str] = []
    preview = data.setdefault("preview_adjustments", {})
    understood_intents: list[str] = []
    extracted_facts: dict[str, Any] = {}

    maturity = _maturity_from_message(message)
    stage_two_gate: dict[str, Any] = {}
    requests_adult_anatomy = _requests_age_progression_stage_two_body(message)
    has_age_progression_provenance = (
        previous_maturity == "adult_aged_up_variant"
        or data.get("age_progression_presentation_label")
        == "adult_aged_up_variant"
        or (
            isinstance(data.get("age_progression_contract"), dict)
            and data["age_progression_contract"].get("contract")
            == "two_stage_spa_age_progression_v1"
        )
    )
    if (
        has_age_progression_provenance
        and requests_adult_anatomy
    ):
        stage_two_gate = evaluate_age_progression_stage_two_gate(
            {"age_progression": data.get("age_progression_contract") or {}},
            data.get("age_progression_stage_one_evidence")
            if isinstance(data.get("age_progression_stage_one_evidence"), dict)
            else {},
        )
        if stage_two_gate.get("status") == "passed":
            maturity = (
                "adult_aged_up_variant",
                "Exact Stage 1 age-progression evidence passed; Robert requested the separate Stage 2 anatomy build.",
            )
    if maturity:
        maturity_class, reason = maturity
        preserve_age_progression_label = (
            has_age_progression_provenance and maturity_class == "adult"
        )
        data["maturity_override"] = (
            "adult_aged_up_variant"
            if preserve_age_progression_label
            else maturity_class
        )
        data["maturity_reason"] = reason
        data["maturity_corrected_at"] = now_iso()
        if maturity_class == "adult" and isinstance(
            requested_classification_evidence, dict
        ):
            data["confirmed_adult_classification_evidence"] = dict(
                requested_classification_evidence
            )
            data["exact_maturity_status"] = "confirmed_adult"
            data["complete_adult_curriculum_assignment"] = "IMMEDIATE"
            if preserve_age_progression_label:
                stage_one_evidence = data.get(
                    "age_progression_stage_one_evidence"
                )
                if isinstance(stage_one_evidence, dict):
                    stage_one_evidence[
                        "confirmed_adult_classification_evidence"
                    ] = dict(requested_classification_evidence)
                    stage_one_evidence["adult_classification_confirmed"] = True
        if maturity_class == "adult_aged_up_variant":
            data["age_progression_presentation_label"] = "adult_aged_up_variant"
            if stage_two_gate.get("status") == "passed":
                stage_one_evidence = data.get("age_progression_stage_one_evidence")
                if isinstance(stage_one_evidence, dict):
                    exact_classification = stage_one_evidence.get(
                        "confirmed_adult_classification_evidence"
                    )
                    if isinstance(exact_classification, dict):
                        data["confirmed_adult_classification_evidence"] = dict(
                            exact_classification
                        )
                    data["resident_adult_anatomy_choice_recorded"] = (
                        stage_one_evidence.get(
                            "resident_adult_anatomy_choice_recorded"
                        )
                        is True
                    )
                data["exact_maturity_status"] = "confirmed_adult"
                data["confirmed_adult_classification_id"] = stage_two_gate.get(
                    "confirmed_adult_classification_id"
                )
                data["complete_adult_curriculum_assignment"] = "IMMEDIATE"
            else:
                data["exact_maturity_status"] = "unresolved"
                data["complete_adult_curriculum_assignment"] = (
                    "ADULT_CURRICULUM_BLOCKED_GUARANTEED_MINIMUM_WITH_SEPARATELY_APPROVED_AGE_APPROPRIATE_MODULES_ALLOWED"
                )
                data["adult_anatomy_auto_added"] = False
        changes.append(
            "Recorded the exact confirmed-adult classification while preserving the separate age-progression presentation label."
            if preserve_age_progression_label
            else f"Set maturity override to {maturity_class}."
        )
        understood_intents.append(f"maturity:{maturity_class}")
        _add_target(data, "maturity", reason, "Robert correction")

    if "head" in lowered:
        _add_target(data, "head", message, "Robert correction")
        understood_intents.append("head_shape_or_size")
        current = float(preview.get("head_scale") or 1.0)
        if any(term in lowered for term in ("too big", "smaller", "large", "oversized")):
            preview["head_scale"] = round(max(0.82, current - 0.04), 3)
            changes.append(f"Adjusted preview head scale to {preview['head_scale']}.")
        elif any(term in lowered for term in ("too small", "bigger", "larger", "tiny")):
            preview["head_scale"] = round(min(1.22, current + 0.04), 3)
            changes.append(f"Adjusted preview head scale to {preview['head_scale']}.")
        else:
            preview.setdefault("head_scale", current)
            changes.append("Queued head shape/size review.")

    if any(term in lowered for term in ("eye", "eyes", "socket", "sclera", "iris", "pupil")):
        requested_color = _requested_eye_color(message)
        candidate_key = candidate_id.strip().lower()
        persisted_requested_color = str(data.get("requested_eye_color") or "").strip()
        effective_requested_color = requested_color or persisted_requested_color
        if candidate_key == "kira":
            target_eye_color = (
                f"realistic {effective_requested_color} adult Kira iris color "
                "(Robert-requested provisional target; Kira owner review remains required)"
                if effective_requested_color
                else "Kira's adult eye color after Kira owner review of a visual target"
            )
        elif candidate_key == CANONICAL_GWEN_ID:
            target_eye_color = f"realistic {effective_requested_color} Gwen iris color" if effective_requested_color else "realistic blue-gray Gwen iris color from Spider-Verse references"
        elif candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
            target_eye_color = f"realistic {effective_requested_color} Marinette iris color" if effective_requested_color else "realistic blue Marinette iris color from references"
        else:
            target_eye_color = f"candidate-specific realistic {effective_requested_color} iris color from approved references" if effective_requested_color else "candidate-specific realistic iris color from approved references"
        if requested_color:
            data["requested_eye_color"] = requested_color
            understood_intents.append(f"eye_color:{requested_color}")
        else:
            understood_intents.append("eyes")
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            target_eye_color,
            "Robert asked for eyes to be added/fixed; missing named eyes is treated as a construction task, not a blocker excuse.",
        )
        data["eye_rebuild_plan"] = project_relative(eye_plan)
        _add_target(
            data,
            "eyes",
            (
                "Run landmark-driven eye construction: measure head and socket landmarks first, then create named "
                f"sclera/iris/pupil/eyelid/look-target parts seated in the sockets; plan: {project_relative(eye_plan)}."
            ),
            "Robert correction",
        )
        preview["eye_guide_y"] = 0.835
        preview["eye_guide_width"] = 0.30
        changes.append(f"Queued landmark-driven eye construction for {target_eye_color} and tightened preview eye guides.")

    if any(term in lowered for term in ("hair", "hairline", "bald", "pigtail", "bang", "groom")):
        _add_target(data, "hair", message, "Robert correction")
        preview["show_hair_priority"] = candidate_id.strip().lower() != "kira"
        preview["detachable_hair_component_only"] = True
        if candidate_id.strip().lower() == "kira":
            preview["runtime_scalp_hair_enabled"] = False
        understood_intents.append("hair")
        changes.append("Queued a detachable hair-component fitting/generation lesson without regenerating the body.")

    if any(term in lowered for term in ("face does not look", "face doesn't look", "does not look like", "doesn't look like", "face likeness", "likeness", "generic face")):
        _add_target(data, "face", message, "Robert correction")
        understood_intents.append("face_likeness")
        changes.append("Queued a candidate-specific face-likeness correction from approved references.")

    if any(term in lowered for term in ("body", "torso", "shoulder", "arm", "leg", "hand", "feet", "proportion", "shape")):
        _add_target(data, "body", message, "Robert correction")
        understood_intents.append("body_shape")
        changes.append("Queued body proportion review.")

    height = _extract_height_measurement(message)
    if height:
        data.setdefault("physical_measurements", {})["height"] = height
        data["target_height_m"] = height["height_m"]
        data["target_height_source"] = "Robert chat"
        extracted_facts["height"] = height
        _add_target(
            data,
            "measurements",
            (
                f"Use Robert-provided target height {height['height_m']}m "
                f"({height['feet']} ft {height['inches']} in) to scale the base body before likeness sculpting."
            ),
            "Robert measurement",
        )
        understood_intents.append("measurement:height")
        changes.append(f"Recorded target height {height['height_m']}m ({height['feet']} ft {height['inches']} in).")

    age_progression_stage_two = bool(
        maturity
        and maturity[0] == "adult_aged_up_variant"
        and stage_two_gate.get("status") == "passed"
    )
    age_progression_stage_one = bool(
        maturity
        and maturity[0] == "adult_aged_up_variant"
        and not age_progression_stage_two
    )
    if any(term in lowered for term in ("barbie", "doll treatment", "doll-safe", "doll safe", "anatomy")):
        _add_target(
            data,
            "anatomy_policy",
            (
                "For a spa age-progression request, complete Stage 1 only as an unresolved doll-safe older/taller "
                "presentation/build label. Adult curriculum waits for separate exact confirmed-adult evidence, "
                "and adult anatomy waits for the later Stage 2 choice and build gate."
                if age_progression_stage_one
                else (
                    "The exact Stage 1 age-progression and spa-eligibility evidence passed. Queue Stage 2 adult "
                    "anatomy only on the separate inactive adult-aged variant; do not alter the original non-adult body."
                    if age_progression_stage_two
                    else "Re-check maturity policy before the next build. Adult candidates must not use non-adult doll-safe "
                    "body treatment; non-adult candidates must remain smooth/non-explicit."
                )
            ),
            "Robert correction",
        )
        understood_intents.append("anatomy_policy")
        changes.append("Queued anatomy/maturity policy review.")

    adult_body_fit_terms = any(
        term in lowered
        for term in (
            "adult body",
            "barbie",
            "doll treatment",
            "doll-safe",
            "doll safe",
            "anatomy",
            "body shape",
            "body fit",
            "proportion",
            "shoulder",
            "waist",
            "hips",
            "torso",
            "height",
        )
    ) or height is not None
    adult_body_candidate = (
        data.get("maturity_override") in ADULT_CLASSES
        or bool(maturity and maturity[0] in ADULT_CLASSES)
        or data.get("exact_maturity_status") == "confirmed_adult"
        or candidate_id.strip().lower() in CANONICAL_ADULT_CANDIDATE_IDS
    )
    if adult_body_candidate and adult_body_fit_terms and not age_progression_stage_one:
        body_fit_plan = write_adult_body_fit_plan(
            candidate_id,
            "Robert rejected the adult body as generic/doll-like; maturity metadata is not enough without real landmark-driven body fitting.",
            data.get("physical_measurements", {}).get("height") if isinstance(data.get("physical_measurements"), dict) else None,
        )
        data["adult_body_fit_plan"] = project_relative(body_fit_plan)
        data["adult_body_fit_status"] = "failed_requires_landmark_lattice_sculpt_fit"
        data["adult_body_fit_reason"] = (
            "Adult policy is allowed, but the actual mesh must be fitted from measurements and references before approval."
        )
        preview["non_adult_review_garment"] = False
        _add_target(
            data,
            "adult_body_fit",
            (
                "Do not treat the adult maturity flag as body approval. Scale to known measurements, fit the adult base "
                "with front/side/back landmarks and a lattice/sculpt pass, preserve neutral adult anatomy/proportions, "
                f"and write proof artifacts; plan: {project_relative(body_fit_plan)}."
            ),
            "Robert correction",
        )
        understood_intents.append("adult_body_fit")
        changes.append("Queued adult body-fit contract; the current generic/doll-like body remains failed until a real fitting pass produces proof.")

    if any(term in lowered for term in ("skin", "skin tone", "complexion", "too pale", "too white", "warmer")):
        _add_target(data, "skin_tone", message, "Robert correction")
        understood_intents.append("skin_tone")
        changes.append("Queued skin tone/material review.")

    research_query = _research_request_from_message(message)
    if research_query:
        request = {
            "created_at": now_iso(),
            "status": "queued_requires_robert_or_tool_approval",
            "query": research_query,
            "source": "Robert chat",
            "rule": "Search only when explicitly requested; save source links and do not claim a result until sources are recorded.",
        }
        data.setdefault("online_research_requests", []).append(request)
        _add_target(data, "online_learning", f"Research online for: {research_query}", "Robert correction")
        understood_intents.append("online_learning")
        extracted_facts["online_research_request"] = request
        changes.append("Queued online-learning research task with source-recording rules.")

    if candidate_id.strip().lower() == NORMAL_MARINETTE_CANDIDATE_ID:
        preview["non_adult_review_garment"] = False

    directives = derive_correction_directives(
        candidate_id,
        message,
        requested_maturity_class=maturity[0] if maturity else "",
        previous_maturity_class=previous_maturity,
        age_progression_stage_one_eligibility_gate=(
            data.get("age_progression_stage_one_eligibility_gate")
            if isinstance(data.get("age_progression_stage_one_eligibility_gate"), dict)
            else {}
        ),
        age_progression_stage_two_gate=stage_two_gate,
    )
    event = append_correction_event(
        data,
        candidate_id=candidate_id,
        message=message,
        directives=directives,
        recorded_at=now_iso(),
    )
    if event:
        route = route_next_private_build(data, event)
        for instruction in directives.get("instructions") or []:
            _add_target(
                data,
                str(instruction.get("area") or "general"),
                str(instruction.get("instruction") or ""),
                "Robert correction memory",
            )
        understood_intents.extend(directives.get("intents") or [])
        extracted_facts["correction_memory_event_id"] = event["event_id"]
        extracted_facts["next_private_build_route"] = {
            "components_to_rebuild": route["components_to_rebuild"],
            "body_lane": route["body_lane"],
            "status": route["status"],
        }
        changes.append(
            f"Recorded append-only correction {event['event_id']} and rerouted the next private, inactive, unapproved build."
        )
    data["last_understood_intents"] = sorted(set(understood_intents))
    _record_design_conversation(data, message, extracted_facts, understood_intents)
    return changes


def run_builder_review(candidate_id: str, profile: dict[str, Any] | None = None, focus: str = "auto") -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    candidate_key = candidate_id.strip().lower()
    review_corrects_maturity = candidate_key in {
        NORMAL_MARINETTE_CANDIDATE_ID,
        "kira",
        CANONICAL_PETER_ID,
        CANONICAL_GWEN_ID,
    }
    if not review_corrects_maturity:
        current_validation = validate_candidate_maturity_identity(
            candidate_id,
            _maturity_validation_profile(candidate_id, profile, data, None),
        )
        if current_validation["status"] != "passed":
            return {
                "ok": False,
                "status": "blocked_maturity_identity_policy",
                "candidate_id": candidate_id,
                "message": "Avatar Builder review was blocked before writes by incompatible maturity metadata.",
                "changes": [],
                "adjustments_saved": False,
                "maturity_identity_validation": current_validation,
            }
    inspection = inspect_candidate_model(candidate_id)
    preview = data.setdefault("preview_adjustments", {})
    changes: list[str] = []
    log_activation(candidate_id, f"run_builder_review:{focus}")

    if candidate_key == NORMAL_MARINETTE_CANDIDATE_ID:
        data["maturity_override"] = "non_adult_doll_safe"
        data["maturity_reason"] = "Normal Marinette/Ladybug remains non-adult. A separate spa age-progressed presentation variant remains unresolved until exact subject-bound classification."
        preview.update({
            "head_scale": 1.04,
            "eye_guide_y": 0.835,
            "eye_guide_width": 0.30,
            "non_adult_review_garment": False,
        })
        _add_target(data, "identity", "Current model is not approved as a Marinette likeness; rebuild against the 59 reviewed references.", "builder review")
        hair_plan = write_hair_rebuild_plan(
            candidate_id,
            "Marinette deep blue-black low twin pigtails and side-swept bangs",
            "Robert graded the current hair F because it does not look close enough to Marinette.",
        )
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            "realistic blue Marinette eyes matched from references",
            "Robert rejected placeholder/floating eyes and wants realistic color changes using the eye model library.",
        )
        _add_target(data, "hair", f"Current Marinette hair is failed. Rebuild from hair model references using {project_relative(hair_plan)}.", "builder review")
        _add_target(data, "hair", "Generate or fit deep blue-black side-swept bangs and low twin pigtails; save as separate hair mesh with scalp anchors.", "builder review")
        _add_target(data, "eyes", f"Replace placeholder eyes with realistic named sclera/iris/pupil/eyelid meshes seated inside sockets; plan: {project_relative(eye_plan)}.", "builder review")
        _add_target(data, "body", "Start from the usable female-base body branch, then keep the normal Marinette result smooth non-adult-safe; block explicit adult anatomy and do not use the primitive procedural redo as the active body.", "Robert correction")
        changes.append("Locked normal Marinette/Ladybug to smooth non-adult-safe review and queued likeness/hair/eye rebuild targets.")
    elif candidate_key == "kira":
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Kira is an adult synthetic person and may use adult body/anatomy references in neutral avatar-building contexts."
        data["test_role"] = "not_valid_adult_reference_test_until_robert_adds_visual_references"
        preview.update({
            "head_scale": 1.0,
            "eye_guide_y": 0.835,
            "eye_guide_width": 0.30,
            "non_adult_review_garment": False,
        })
        _add_target(data, "references", "Do not use Kira as the adult likeness/body-reference test until Robert provides or approves visual references. Use Peter, Gwen, or Robert for adult tests now.", "Robert correction")
        _add_target(data, "eyes", "Kira needs separate named eye, iris, pupil, eyelid, and head socket anchors; reject floating or side-face eyes.", "builder review")
        _add_target(data, "body", "Keep Kira on the clean shared adult base body; do not copy Marinette hair, face, or body edits.", "builder review")
        _add_target(data, "hair", "Kira hair is separate wearable hair fitted to scalp/head anchors, not part of the body mesh.", "builder review")
        changes.append("Recorded Kira as adult but not a valid adult reference test until visual references exist.")
    elif candidate_key == CANONICAL_PETER_ID:
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Robert selected Peter as an adult avatar-builder test pick."
        data["test_role"] = "adult_reference_test_pick"
        preview.setdefault("non_adult_review_garment", False)
        _add_target(data, "body", "Use adult male base-body/anatomy references for a neutral face/body trial before hair and wardrobe.", "builder review")
        _add_target(data, "eyes", "Use named eyes and sockets; reject mask/face planes that hide bad eye placement.", "builder review")
        changes.append("Locked Peter to adult body test policy.")
    elif candidate_key == CANONICAL_GWEN_ID:
        refs = gwen_reference_paths()
        unmasked_reference = PROJECT_ROOT / refs["unmasked_head_hair_model"]
        spandex_reference = PROJECT_ROOT / refs["rigged_spandex_costume_model"]
        data["maturity_override"] = "adult"
        data["maturity_reason"] = "Robert selected Gwen as an adult avatar-builder test pick."
        data["test_role"] = "adult_reference_test_pick_sources_ready"
        data["current_body_rejected_reason"] = "The active costume runtime body is not the base body, but it is useful as a spandex silhouette and removable wardrobe reference."
        data["approval_status"] = "adult_rebuild_sources_ready"
        data["gwen_reference_sources"] = refs
        preview.setdefault("non_adult_review_garment", False)
        eye_plan = write_eye_rebuild_plan(
            candidate_id,
            "realistic blue Gwen eyes from unmasked model and new chat-uploaded references",
            "Robert wants the Avatar Builder to learn realistic eye color/material changes while placing eyes in the correct sockets.",
        )
        wardrobe_plan = write_gwen_spandex_wardrobe_plan(candidate_id)
        body_fit_plan = write_adult_body_fit_plan(
            candidate_id,
            "Robert rejected Gwen's current body as a generic/barbie-like adult proof; rebuild with real adult landmark fitting.",
            data.get("physical_measurements", {}).get("height") if isinstance(data.get("physical_measurements"), dict) else None,
        )
        data["adult_body_fit_plan"] = project_relative(body_fit_plan)
        data["adult_body_fit_status"] = "failed_requires_landmark_lattice_sculpt_fit"
        _add_target(data, "body", "Build an adult neutral Gwen base body from the female base body, adult anatomy/reference models, Avatar/library female body/proportions, and the spandex costume silhouette; do not use the costume mesh as the naked/base body.", "Robert correction")
        _add_target(data, "adult_body_fit", f"Run a true adult body-fit pass before approval; plan: {project_relative(body_fit_plan)}.", "Robert correction")
        _add_target(data, "head_hair", f"Use the saved unmasked Gwen model for head/hair reference: {refs['unmasked_head_hair_model']}.", "Robert correction")
        _add_target(data, "wardrobe", f"Convert the Ghost-Spider spandex suit into removable clothing layers instead of baking it into the body; plan: {project_relative(wardrobe_plan)}.", "Robert correction")
        _add_target(data, "eyes", f"Use eye-reference models to place realistic Gwen eyes in sockets and recolor only the iris/material; plan: {project_relative(eye_plan)}.", "Robert F-grade correction")
        _add_target(data, "hair", "Use Gwen's blonde asymmetric side-part hair from the unmasked model and new image references; hair is separate from head and hood.", "builder review")
        if not unmasked_reference.exists():
            data["approval_status"] = "failed_waiting_for_unmasked_gwen_model"
            _add_target(data, "references", f"Missing unmasked Gwen reference model: {refs['unmasked_head_hair_model']}.", "model inspection")
        if not spandex_reference.exists():
            data["approval_status"] = "failed_waiting_for_spandex_costume_model"
            _add_target(data, "references", f"Missing rigged spandex costume reference model: {refs['rigged_spandex_costume_model']}.", "model inspection")
        changes.append("Queued Gwen adult rebuild with unmasked head/hair reference, spandex body silhouette, realistic eye plan, and removable costume wardrobe plan.")
    else:
        _add_target(data, "review", "Run visual reference, maturity, head, eyes, hair, body, and movement review before accepting this avatar.", "builder review")
        changes.append("Queued generic avatar review.")

    if inspection.get("issues"):
        for issue in inspection["issues"]:
            _add_target(data, "model_diagnostics", str(issue), "model inspection")
        changes.append("Stored model diagnostics from the linked GLB.")

    _note(data, "Builder review ran and updated correction targets.", ["builder_review", focus])
    if data.get("approval_status") not in {
        "failed_redo_required",
        "redo_draft_ready_for_robert_review",
        "female_base_restored_eye_training_required",
        "failed_waiting_for_out_of_costume_refs",
        "adult_rebuild_sources_ready",
        "failed_disqualified_reference_copy",
        "base_body_pass_ready_for_robert_review",
        "round_eye_mechanics_preview_ready_overlay_required",
        "failed_robert_big_f_overlay_required",
        "silhouette_overlay_calibration_ready_failed_likeness",
        "avatar_builder_school_required_failed_preview",
        "builder_reference_pass_ready_for_robert_review",
        "failed_waiting_for_unmasked_gwen_model",
        "failed_waiting_for_spandex_costume_model",
    }:
        data["approval_status"] = "failed_needs_rebuild_or_review" if data.get("build_targets") else "unreviewed"
    maturity_validation = validate_candidate_maturity_identity(
        candidate_id,
        _maturity_validation_profile(candidate_id, profile, data, None),
    )
    if maturity_validation["status"] != "passed":
        return {
            "ok": False,
            "status": "blocked_maturity_identity_policy",
            "candidate_id": candidate_id,
            "message": "Avatar Builder review produced incompatible maturity metadata and was not saved.",
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": maturity_validation,
        }
    path = save_adjustments(candidate_id, data)
    append_global_lesson(
        candidate_id,
        ["avatar_builder", "review", "head", "eyes", "hair", "body"],
        "Avatar Builder must compare the linked GLB, reference images, and Robert corrections before approving a body.",
    )
    return {
        "ok": True,
        "candidate_id": candidate_id,
        "message": "Avatar Builder review complete.",
        "changes": changes,
        "adjustments_path": project_relative(path),
        "inspection": inspection,
        "adjustments": data,
        "maturity_identity_validation": maturity_validation,
    }


def avatar_builder_chat(candidate_id: str, message: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    data = load_adjustments(candidate_id)
    message = message.strip()
    requested_maturity = _maturity_from_message(message)
    requested_classification_evidence = (
        _owner_confirmed_adult_classification_evidence(candidate_id, message)
        if requested_maturity and requested_maturity[0] == "adult"
        else None
    )
    persisted_maturity = str(data.get("maturity_override") or "").strip()
    has_age_progression_provenance = (
        persisted_maturity == "adult_aged_up_variant"
        or data.get("age_progression_presentation_label")
        == "adult_aged_up_variant"
        or (
            isinstance(data.get("age_progression_contract"), dict)
            and data["age_progression_contract"].get("contract")
            == "two_stage_spa_age_progression_v1"
        )
    )
    requests_age_progression_anatomy = (
        has_age_progression_provenance
        and _requests_age_progression_stage_two_body(message)
    )
    requests_age_progression_stage_one = bool(
        requested_maturity
        and requested_maturity[0] == "adult_aged_up_variant"
        and not requests_age_progression_anatomy
    )
    stage_one_eligibility_gate: dict[str, Any] = {}
    if requests_age_progression_stage_one:
        profile_eligibility = (
            profile.get("age_progression_eligibility_evidence")
            if isinstance(profile, dict)
            and isinstance(profile.get("age_progression_eligibility_evidence"), dict)
            else {}
        )
        stored_eligibility = (
            data.get("age_progression_eligibility_evidence")
            if isinstance(data.get("age_progression_eligibility_evidence"), dict)
            else {}
        )
        stage_one_eligibility_gate = evaluate_age_progression_stage_one_eligibility(
            stored_eligibility or profile_eligibility
        )
    if requests_age_progression_anatomy:
        stage_two_gate = evaluate_age_progression_stage_two_gate(
            {"age_progression": data.get("age_progression_contract") or {}},
            data.get("age_progression_stage_one_evidence")
            if isinstance(data.get("age_progression_stage_one_evidence"), dict)
            else {},
        )
        if stage_two_gate["status"] != "passed":
            return {
                "ok": False,
                "status": "blocked_age_progression_stage_one_evidence_required",
                "candidate_id": candidate_id,
                "reply": (
                    "I did not add or queue adult anatomy. The older/taller presentation/build label, "
                    "separate exact confirmed-adult classification, spa eligibility, and the resident's "
                    "Stage 2 adult-anatomy choice must pass exact evidence first."
                ),
                "changes": [],
                "adjustments_saved": False,
                "age_progression_stage_two_gate": stage_two_gate,
            }
        requested_maturity = (
            "adult_aged_up_variant",
            "Exact Stage 1 age-progression evidence passed; Robert requested the separate Stage 2 anatomy build.",
        )
    explicitly_non_adult_in_place_change = (
        persisted_maturity == "non_adult_doll_safe"
        and bool(requested_maturity and requested_maturity[0] == "adult")
        and candidate_id.strip().lower() not in CANONICAL_ADULT_CANDIDATE_IDS
    )
    if explicitly_non_adult_in_place_change:
        return {
            "ok": False,
            "status": "blocked_separate_age_up_variant_required",
            "candidate_id": candidate_id,
            "reply": (
                "I did not age up or overwrite the explicitly non-adult body. Create a distinct spa age-up "
                "candidate/version first; Stage 1 establishes only the older/taller presentation/build label "
                "without adult anatomy. The separate exact adult classification remains a later gate."
            ),
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "status": "failed",
                "failures": ["explicit_non_adult_body_cannot_be_aged_up_in_place"],
            },
        }
    maturity_profile = _maturity_validation_profile(
        candidate_id,
        profile,
        data,
        requested_maturity,
        requested_classification_evidence,
    )
    maturity_validation = validate_candidate_maturity_identity(candidate_id, maturity_profile)
    if maturity_validation["status"] != "passed":
        separate_variant_required = (
            "age_up_requires_distinct_candidate_id_and_variant_profile"
            in maturity_validation["failures"]
            or "canonical_non_adult_identity_cannot_be_aged_up_in_place"
            in maturity_validation["failures"]
        )
        status = (
            "blocked_separate_age_up_variant_required"
            if separate_variant_required
            else "blocked_maturity_identity_policy"
        )
        reply = (
            "I did not change this candidate. Age-up must use a distinct aged-up candidate "
            "ID and variant profile; the normal identity remains unchanged."
            if separate_variant_required
            else "I did not change this candidate because the requested body policy conflicts "
            "with its confirmed maturity identity."
        )
        return {
            "ok": False,
            "status": status,
            "candidate_id": candidate_id,
            "reply": reply,
            "changes": [],
            "adjustments_saved": False,
            "maturity_identity_validation": maturity_validation,
        }
    if (
        requests_age_progression_stage_one
        and stage_one_eligibility_gate.get("status") != "passed"
    ):
        return {
            "ok": False,
            "status": "blocked_spa_age_progression_eligibility_required",
            "candidate_id": candidate_id,
            "reply": (
                "I did not queue an age-up body. Stage 1 first requires exact evidence of temporary origin, "
                "permanent promotion, at least two prior activations, the resident's recorded choice, and "
                "the spa flow."
            ),
            "changes": [],
            "adjustments_saved": False,
            "age_progression_stage_one_eligibility_gate": stage_one_eligibility_gate,
        }
    if requests_age_progression_stage_one:
        data["age_progression_stage_one_eligibility_gate"] = stage_one_eligibility_gate
    inspection = inspect_candidate_model(candidate_id)
    log_activation(candidate_id, "chat")
    changes = _apply_message_adjustments(
        candidate_id,
        message,
        data,
        requested_classification_evidence,
    )

    if any(term in message.lower() for term in ("review", "run", "inspect", "look at", "check")):
        review = run_builder_review(candidate_id, profile, focus="chat_request")
        data = review["adjustments"]
        changes.extend(review["changes"])

    data.setdefault("conversation", []).append({
        "created_at": now_iso(),
        "from": "Robert",
        "message": message,
    })

    if not changes:
        _add_target(data, "general", message, "Robert correction")
        changes.append("I saved that as a builder correction target.")

    understood = data.get("last_understood_intents") or []
    reply_parts = [
        "Avatar Builder is active for this build task only.",
        (
            "I understood: " + ", ".join(str(item) for item in understood) + "."
            if understood
            else "I saved the correction as a general build target."
        ),
        "I updated candidate build memory; a builder pass is still required to change the actual GLB.",
    ]
    if inspection.get("model_ready"):
        reply_parts.append(
            f"I inspected {inspection.get('model_path')} with {inspection.get('node_count')} nodes and {inspection.get('mesh_count')} meshes."
        )
    if inspection.get("issues"):
        reply_parts.append("Problems I see: " + "; ".join(str(item) for item in inspection["issues"][:3]) + ".")
    reply_parts.append("Changes: " + " ".join(changes))
    reply = " ".join(reply_parts)

    data["conversation"].append({
        "created_at": now_iso(),
        "from": "Avatar Builder",
        "message": reply,
    })
    data["last_reply"] = reply
    path = save_adjustments(candidate_id, data)
    append_global_lesson(candidate_id, ["avatar_builder", "robert_correction"], message, source="Robert correction")

    return {
        "ok": True,
        "candidate_id": candidate_id,
        "reply": reply,
        "changes": changes,
        "adjustments_path": project_relative(path),
        "inspection": inspection,
        "adjustments": data,
        "maturity_identity_validation": maturity_validation,
    }
