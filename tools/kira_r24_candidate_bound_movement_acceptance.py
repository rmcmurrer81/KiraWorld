#!/usr/bin/env python3
"""Static, fail-closed validator for future Kira R24 movement evidence.

This module never imports Blender, starts a process, authors an action, opens a
device, or changes runtime state.  It validates a prepared contract, an exact
future candidate release, and (when supplied) an append-only geometry/rig
evidence record.  The maximum result it can produce without an owner decision
is BODY_HOOKS_VERIFIED; it cannot establish biological or lived function.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / (
    "Avatar/movement_library/"
    "kira_r24_candidate_bound_movement_acceptance_contract_v1.json"
)

CONTRACT_SCHEMA = "kira.avatar.r24_candidate_bound_movement_acceptance.v1"
RELEASE_SCHEMA = "kira.avatar.r24_movement_candidate_release.v1"
EVIDENCE_SCHEMA = "kira.avatar.r24_candidate_bound_movement_evidence.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_SCENARIO_IDS = {
    "neutral_relaxed_standing",
    "left_knee_bend",
    "right_knee_bend",
    "bilateral_knee_bend",
    "seated_supported_contact",
    "supine_lie_down_and_rise",
    "side_lying_left_right_and_rise",
    "arm_and_hand_reach_envelope",
    "walk_readiness",
    "jog_readiness",
    "run_readiness",
    "book_reach_grasp_contact",
    "tablet_reach_grasp_contact",
    "phone_reach_grasp_contact",
    "door_push_handle_contact",
    "door_pull_handle_contact",
    "handwashing_motion_envelope",
    "shower_motion_envelope",
    "bath_motion_envelope",
    "speech_mouth_lipsync_hooks",
}

REQUIRED_GROUPS = {
    "POSTURE_AND_DEFORMATION",
    "POSTURE_AND_CONTACT",
    "UPPER_BODY_READINESS",
    "LOCOMOTION_READINESS",
    "PROP_CONTACT_ENVELOPE",
    "FIXTURE_CONTACT_ENVELOPE",
    "HYGIENE_MOTION_ENVELOPE",
    "ORAL_ARTICULATION_HOOKS",
}


class AcceptanceError(ValueError):
    """Raised when any exact binding, safety boundary, or gate is absent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"expected a JSON object: {path}")
    return value


def _sha(value: Any, label: str) -> str:
    normalized = str(value).lower()
    _require(bool(SHA256_RE.fullmatch(normalized)), f"invalid SHA-256: {label}")
    return normalized


def _project_file(project_root: Path, value: Any, label: str) -> Path:
    text = str(value)
    supplied = Path(text)
    _require(text != "", f"empty project-relative path: {label}")
    _require(not supplied.is_absolute(), f"absolute path forbidden: {label}")
    _require(".." not in supplied.parts, f"parent traversal forbidden: {label}")
    resolved = (project_root / supplied).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise AcceptanceError(f"path escaped project root: {label}") from exc
    _require(resolved.is_file(), f"required file is missing: {label}: {text}")
    return resolved


def _object_list_by_id(values: Any, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(values, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        _require(isinstance(value, dict), f"{label} entries must be objects")
        identifier = str(value.get("id", ""))
        _require(identifier != "" and identifier not in result, f"bad {label} id: {identifier}")
        result[identifier] = value
    return result


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    _require(contract.get("schema_version") == CONTRACT_SCHEMA, "unsupported contract schema")
    _require(
        contract.get("status") == "PREPARED_BLOCKED_PENDING_EXACT_COMPLETE_R24_CANDIDATE",
        "contract is not at its prepared fail-closed boundary",
    )
    _require(contract.get("capability_level") == "CONTRACT_ONLY", "capability overclaim")

    scope = contract.get("scope", {})
    _require(scope.get("execution_mode") == "STATIC_CPU_ONLY", "execution mode drifted")
    for key in (
        "blender_launch_authorized",
        "blend_creation_or_save_authorized",
        "body_or_rig_mutation_authorized",
        "runtime_activation_assignment_export_or_publication_authorized",
        "person_or_world_runtime_test_authorized",
    ):
        _require(scope.get(key) is False, f"unsafe scope enabled: {key}")

    prepared = contract.get("prepared_candidate_binding", {})
    for key in contract.get("release_contract", {}).get("required_exact_fields", []):
        _require(key in prepared, f"prepared binding field absent: {key}")
        _require(prepared[key] is None, f"prepared contract silently selected a candidate: {key}")

    scenarios = _object_list_by_id(contract.get("movement_scenarios"), "movement_scenarios")
    _require(set(scenarios) == REQUIRED_SCENARIO_IDS, "movement scenario inventory mismatch")
    groups = {str(value.get("group", "")) for value in scenarios.values()}
    _require(groups == REQUIRED_GROUPS, "movement scenario group inventory mismatch")
    for identifier, scenario in scenarios.items():
        measurements = scenario.get("required_measurements")
        _require(isinstance(measurements, list) and measurements, f"{identifier} has no measurements")
        _require(len(measurements) == len(set(map(str, measurements))), f"{identifier} duplicates measurements")
        boundary = str(scenario.get("future_semantic_or_world_requirement", ""))
        _require(boundary != "", f"{identifier} lacks its world/person truth boundary")

    gates = contract.get("common_geometry_rig_gates", {})
    for key in (
        "maximum_exact_nonadjacent_self_intersection_pairs_per_sample",
        "maximum_pose_induced_or_exposed_pair_count_per_sample",
        "maximum_body_nail_intersection_pair_count_per_sample",
        "maximum_unintended_body_prop_penetration_pair_count_per_sample",
    ):
        _require(gates.get(key) == 0, f"zero collision gate weakened: {key}")
    for key in (
        "fresh_reopen_required",
        "source_candidate_disk_hash_unchanged_before_after",
        "exact_body_geometry_uv_hash_before_after",
        "exact_positive_weight_hash_before_after",
        "exact_rig_rest_hash_before_after",
        "deformation_continuity_required",
        "neutral_start_and_return_required",
        "new_actions_must_remain_unassigned",
        "temporary_props_fixtures_cameras_and_collections_absent_after_reopen",
        "phase_bound_render_manifest_required",
        "owner_visual_review_required",
        "biological_function_claim_forbidden",
    ):
        _require(gates.get(key) is True, f"mandatory gate absent: {key}")

    evidence_schema = contract.get("scenario_evidence_schema", {})
    _require(evidence_schema.get("geometry_rig_status_must_equal") == "PASS", "pass status drifted")
    _require(
        evidence_schema.get("semantic_world_status_must_equal") == "NOT_EVALUATED_IN_BODY_GATE",
        "body gate may not claim world semantics",
    )
    _require(evidence_schema.get("biological_function_claimed_must_equal") is False, "function claim enabled")
    _require(int(evidence_schema.get("minimum_sample_count", 0)) >= 2, "sample minimum weakened")
    _require(int(evidence_schema.get("minimum_phase_bound_render_count", 0)) >= 2, "render minimum weakened")

    truth = contract.get("truth_boundaries", {})
    _require(
        truth.get("world_and_person_followup_state") == "NOT_IMPLEMENTED_OR_NOT_TESTED_BY_THIS_CONTRACT",
        "world/person follow-up state overclaimed",
    )
    forbidden_claims = " ".join(map(str, truth.get("geometry_rig_evidence_cannot_establish", []))).lower()
    for token in ("biological", "sensation", "consent", "actual eating", "intent", "speech comprehension"):
        _require(token in forbidden_claims, f"truth boundary missing: {token}")

    return {
        "status": contract["status"],
        "capability_level": contract["capability_level"],
        "scenario_count": len(scenarios),
        "groups": sorted(groups),
        "candidate_bound": False,
        "blender_authorized": False,
    }


def validate_reference_anchors(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    validate_contract(contract)
    records = contract.get("preserved_method_evidence")
    _require(isinstance(records, list) and len(records) >= 6, "preserved evidence inventory incomplete")
    checked = []
    for record in records:
        _require(isinstance(record, dict), "preserved evidence entry must be an object")
        path = _project_file(project_root, record.get("path"), "preserved method evidence")
        expected = _sha(record.get("sha256"), str(record.get("path")))
        actual = sha256_file(path)
        _require(actual == expected, f"preserved method evidence hash mismatch: {record.get('path')}")
        _require(str(record.get("disposition", "")) != "", "preserved evidence disposition absent")
        _require(str(record.get("lesson", "")) != "", "preserved evidence lesson absent")
        checked.append({"path": str(record["path"]), "sha256": actual})
    return checked


def _candidate_identity(release: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "candidate_id",
        "candidate_blend_sha256",
        "body_object",
        "body_geometry_uv_sha256",
        "body_positive_weight_assignment_sha256",
        "rig_object",
        "rig_rest_sha256",
        "rig_joint_count",
        "oral_component_bindings",
    )
    return {key: release[key] for key in keys}


def validate_release(
    contract: dict[str, Any],
    contract_path: Path,
    release: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    validate_contract(contract)
    rules = contract["release_contract"]
    _require(release.get("schema_version") == RELEASE_SCHEMA, "unsupported release schema")
    _require(
        release.get("authorization_scope") == rules["authorization_scope_must_equal"],
        "release is not static-validation-only",
    )
    _require(
        release.get("candidate_status") == rules["candidate_status_must_equal"],
        "release candidate status is unsafe or incomplete",
    )
    actual_contract_hash = sha256_file(contract_path)
    _require(
        _sha(release.get("contract_sha256"), "contract_sha256") == actual_contract_hash,
        "release is bound to a different contract",
    )

    for key in rules["required_exact_fields"]:
        _require(key in release and release[key] not in (None, "", []), f"release missing exact field: {key}")
    _require(str(release["candidate_id"]).startswith("KIRA_R24_"), "candidate ID is not R24")

    blend_hash = _sha(release["candidate_blend_sha256"], "candidate_blend_sha256")
    evidence_hash = _sha(release["candidate_build_evidence_sha256"], "candidate_build_evidence_sha256")
    blend_path = _project_file(project_root, release["candidate_blend"], "candidate_blend")
    build_path = _project_file(project_root, release["candidate_build_evidence"], "candidate_build_evidence")
    _require(sha256_file(blend_path) == blend_hash, "candidate Blend hash mismatch")
    _require(sha256_file(build_path) == evidence_hash, "candidate build-evidence hash mismatch")
    rejected = {_sha(value, "rejected candidate hash") for value in rules["rejected_candidate_hashes_must_not_be_released"]}
    _require(blend_hash not in rejected, "release selected a known rejected movement/body candidate")

    for key in ("body_geometry_uv_sha256", "body_positive_weight_assignment_sha256", "rig_rest_sha256"):
        _sha(release[key], key)
    _require(int(release["rig_joint_count"]) == int(rules["required_native_rig_joint_count"]), "native rig joint count mismatch")
    _require(str(release["body_object"]) != "", "body object absent")
    _require(str(release["rig_object"]) != "", "rig object absent")

    flags = release.get("candidate_flags")
    _require(isinstance(flags, dict), "candidate flags absent")
    for key, expected in rules["required_candidate_flags"].items():
        _require(flags.get(key) is expected, f"candidate flag mismatch: {key}")

    oral_values = release["oral_component_bindings"]
    _require(isinstance(oral_values, list), "oral component bindings must be a list")
    _require(len(oral_values) == len(rules["required_oral_roles"]), "oral binding count mismatch")
    oral_by_role: dict[str, dict[str, Any]] = {}
    for value in oral_values:
        _require(isinstance(value, dict), "oral binding must be an object")
        for key in rules["required_oral_binding_fields"]:
            _require(value.get(key) not in (None, ""), f"oral binding field absent: {key}")
        role = str(value["role"])
        _require(role not in oral_by_role, f"duplicate oral role: {role}")
        _sha(value["geometry_uv_sha256"], f"{role} geometry")
        _sha(value["positive_weight_assignment_sha256"], f"{role} weights")
        oral_by_role[role] = value
    _require(set(oral_by_role) == set(rules["required_oral_roles"]), "oral roles mismatch")
    _require(len({str(value["object"]) for value in oral_values}) == len(oral_values), "oral objects are not unique")

    return {
        "status": "EXACT_R24_CANDIDATE_BOUND_FOR_STATIC_VALIDATION_ONLY",
        "candidate_id": str(release["candidate_id"]),
        "candidate_blend": str(release["candidate_blend"]),
        "candidate_blend_sha256": blend_hash,
        "candidate_build_evidence": str(release["candidate_build_evidence"]),
        "candidate_build_evidence_sha256": evidence_hash,
        "identity": _candidate_identity(release),
        "blender_authorized": False,
        "runtime_authorized": False,
    }


def _require_exact_set(actual: Iterable[Any], expected: Iterable[Any], label: str) -> None:
    actual_list = [str(value) for value in actual]
    _require(len(actual_list) == len(set(actual_list)), f"{label} contains duplicates")
    _require(set(actual_list) == set(map(str, expected)), f"{label} inventory mismatch")


def validate_evidence(
    contract: dict[str, Any],
    contract_path: Path,
    release: dict[str, Any],
    evidence: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    bound = validate_release(contract, contract_path, release, project_root)
    _require(evidence.get("schema_version") == EVIDENCE_SCHEMA, "unsupported evidence schema")
    _require(
        _sha(evidence.get("contract_sha256"), "evidence contract_sha256") == sha256_file(contract_path),
        "evidence contract binding mismatch",
    )
    _require(evidence.get("candidate_binding") == bound["identity"], "evidence candidate identity mismatch")

    preservation = evidence.get("preservation")
    _require(isinstance(preservation, dict), "preservation evidence absent")
    exact_pairs = {
        "source_candidate_sha256_before": release["candidate_blend_sha256"],
        "source_candidate_sha256_after": release["candidate_blend_sha256"],
        "body_geometry_uv_sha256_before": release["body_geometry_uv_sha256"],
        "body_geometry_uv_sha256_after": release["body_geometry_uv_sha256"],
        "body_positive_weight_assignment_sha256_before": release["body_positive_weight_assignment_sha256"],
        "body_positive_weight_assignment_sha256_after": release["body_positive_weight_assignment_sha256"],
        "rig_rest_sha256_before": release["rig_rest_sha256"],
        "rig_rest_sha256_after": release["rig_rest_sha256"],
    }
    for key, expected in exact_pairs.items():
        _require(str(preservation.get(key)).lower() == str(expected).lower(), f"preservation mismatch: {key}")
    for key in (
        "fresh_reopen_verified",
        "source_candidate_unchanged",
        "new_actions_unassigned_after_reopen",
        "temporary_props_fixtures_cameras_and_collections_absent_after_reopen",
        "private",
        "inactive",
        "unpublished",
    ):
        _require(preservation.get(key) is True, f"preservation gate absent: {key}")
    for key in (
        "body_mesh_mutated",
        "rig_rest_mutated",
        "weight_assignments_mutated",
        "runtime_activation_assignment_export_or_publication_performed",
    ):
        _require(preservation.get(key) is False, f"forbidden mutation/action reported: {key}")

    scenario_contract = _object_list_by_id(contract["movement_scenarios"], "movement_scenarios")
    results = _object_list_by_id(evidence.get("scenario_results"), "scenario_results")
    _require(set(results) == REQUIRED_SCENARIO_IDS, "evidence scenario inventory mismatch")
    evidence_schema = contract["scenario_evidence_schema"]
    required_fields = set(map(str, evidence_schema["required_fields"]))
    render_ids: list[str] = []
    for identifier in sorted(REQUIRED_SCENARIO_IDS):
        result = results[identifier]
        _require(required_fields.issubset(result), f"{identifier} evidence fields incomplete")
        _require(result["geometry_rig_status"] == "PASS", f"{identifier} did not pass geometry/rig")
        _sha(result["action_or_probe_sha256"], f"{identifier} action/probe")
        _require(int(result["sample_count"]) >= int(evidence_schema["minimum_sample_count"]), f"{identifier} sample count too small")
        _require(result["neutral_return_verified"] is True, f"{identifier} lacks neutral return")
        for key in (
            "maximum_exact_nonadjacent_self_intersection_pairs",
            "maximum_pose_induced_or_exposed_pairs",
            "maximum_body_nail_intersection_pairs",
            "maximum_unintended_body_prop_penetration_pairs",
        ):
            _require(int(result[key]) == 0, f"{identifier} failed zero gate: {key}")
        _require(result["deformation_continuity_passed"] is True, f"{identifier} continuity failed")
        _require_exact_set(
            result["required_measurements_present"],
            scenario_contract[identifier]["required_measurements"],
            f"{identifier} measurements",
        )
        scenario_renders = result["phase_bound_render_ids"]
        _require(isinstance(scenario_renders, list), f"{identifier} render IDs must be a list")
        _require(
            len(scenario_renders) >= int(evidence_schema["minimum_phase_bound_render_count"]),
            f"{identifier} lacks phase-bound renders",
        )
        _require(len(scenario_renders) == len(set(map(str, scenario_renders))), f"{identifier} duplicates render IDs")
        render_ids.extend(map(str, scenario_renders))
        _require(
            result["semantic_world_status"] == "NOT_EVALUATED_IN_BODY_GATE",
            f"{identifier} improperly claimed world/person semantics",
        )
        _require(result["biological_function_claimed"] is False, f"{identifier} improperly claimed biological function")
    _require(len(render_ids) == len(set(render_ids)), "render IDs must be globally unique")

    _require(
        evidence.get("world_person_runtime_status") == "NOT_EVALUATED_IN_BODY_GATE",
        "world/person runtime was improperly folded into the body gate",
    )
    _require(evidence.get("world_interaction_results") == [], "world interaction results are forbidden here")
    _require(evidence.get("biological_function_claimed") is False, "evidence overclaims biological function")

    owner = evidence.get("owner_decision")
    _require(isinstance(owner, dict), "owner decision record absent")
    owner_status = owner.get("status")
    _require(owner_status in {"PENDING_NOT_APPROVED", "APPROVED", "REJECTED"}, "invalid owner status")
    if owner_status == "PENDING_NOT_APPROVED":
        _require(owner.get("path") is None and owner.get("sha256") is None, "pending owner state references a decision")
        capability = "BODY_HOOKS_VERIFIED"
        status = "GEOMETRY_RIG_PASS_PENDING_OWNER_REVIEW"
    else:
        decision_path = _project_file(project_root, owner.get("path"), "owner decision")
        decision_hash = _sha(owner.get("sha256"), "owner decision")
        _require(sha256_file(decision_path) == decision_hash, "owner decision hash mismatch")
        _require(
            str(owner.get("candidate_blend_sha256", "")).lower() == str(release["candidate_blend_sha256"]).lower(),
            "owner decision selected another candidate",
        )
        if owner_status == "APPROVED":
            capability = "OWNER_SUPERVISED_PASS"
            status = "OWNER_SUPERVISED_PASS_BODY_MOVEMENT_ONLY"
        else:
            capability = "BODY_HOOKS_VERIFIED"
            status = "OWNER_REJECTED_EXACT_MOVEMENT_PACKAGE"

    return {
        "status": status,
        "capability_level": capability,
        "candidate_id": release["candidate_id"],
        "candidate_blend_sha256": release["candidate_blend_sha256"],
        "scenario_count": len(results),
        "render_id_count": len(render_ids),
        "owner_decision": owner_status,
        "world_person_runtime_status": "NOT_EVALUATED_IN_BODY_GATE",
        "biological_function_claimed": False,
        "avatar_builder_method_promoted": False,
        "runtime_authorized": False,
    }


def describe(contract: dict[str, Any]) -> dict[str, Any]:
    summary = validate_contract(contract)
    summary["remaining_blockers"] = [
        "exact complete private inactive R24 candidate Blend and build-evidence hashes",
        "exact body geometry/UV and positive-weight hashes",
        "exact native rig rest hash and oral-component hashes",
        "Blender-generated phase, collision, support, contact, deformation, and render evidence",
        "fresh-reopen verification",
        "Robert's visual decision on the exact review package",
        "separate Person/World Runtime tests for real interactions, experience, speech, and biological claims",
    ]
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--verify-reference-anchors", action="store_true")
    parser.add_argument("--release", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)

    contract_path = args.contract.resolve()
    contract = load_json(contract_path)
    output: dict[str, Any] = {"contract": describe(contract)}
    if args.verify_reference_anchors:
        output["reference_anchors"] = validate_reference_anchors(contract, PROJECT_ROOT)
    if args.release is not None:
        release = load_json(args.release.resolve())
        output["release"] = validate_release(contract, contract_path, release, PROJECT_ROOT)
        if args.evidence is not None:
            evidence = load_json(args.evidence.resolve())
            output["evidence"] = validate_evidence(
                contract,
                contract_path,
                release,
                evidence,
                PROJECT_ROOT,
            )
    else:
        _require(args.evidence is None, "evidence cannot be validated without an exact release")
        _require(args.describe or args.verify_reference_anchors, "supply --describe, --verify-reference-anchors, or --release")

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
