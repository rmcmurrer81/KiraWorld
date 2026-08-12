"""Fail-closed per-subject positive-proof validation for Avatar Builder.

This module does not build or activate an avatar.  It verifies one exact,
clothed, embodied positive-proof bundle.  A single subject can no longer
release downstream batch authoring: batch release is owned exclusively by
``Core.avatar_two_subject_autobuild_gate`` and requires two distinct canonical
subjects.  A schema pass or a model existing on disk is deliberately
insufficient.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import hashlib
import json


POLICY_PATH = Path("Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json")
REGISTRY_PATH = Path("Avatar/avatar_builder/policies/candidate_identity_variant_registry.json")
BACKLOG_PATH = Path("Avatar/avatar_builder/authoring_backlogs/body_authoring_backlog_after_positive_proof_20260716.json")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path.name}")
    return data


def _project_file(project_root: Path, raw: Any) -> Path | None:
    text = _text(raw)
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    lexical = project_root
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            return None
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _verify_binding(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
) -> tuple[Path | None, str]:
    if not isinstance(binding, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    path = _project_file(project_root, binding.get("path"))
    expected = _text(binding.get("sha256")).lower()
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, expected
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        failures.append(f"{label}_sha256_invalid")
        return path, expected
    if _sha256(path) != expected:
        failures.append(f"{label}_sha256_mismatch")
    return path, expected


def evaluate_positive_proof(
    project_root: Path,
    proof_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    policy = _read_json(root / POLICY_PATH)
    registry_path = root / REGISTRY_PATH
    backlog_path = root / BACKLOG_PATH
    registry = _read_json(registry_path)
    backlog = _read_json(backlog_path)

    configured = _text(policy.get("current_proof_path"))
    selected_path = proof_path or (Path(configured) if configured else None)
    if selected_path is None:
        return {
            "status": "locked_no_positive_proof",
            "release_allowed": False,
            "failures": ["positive_proof_path_missing"],
            "maximum_concurrent_downstream_builds": int(
                policy.get("maximum_concurrent_downstream_builds", 1)
            ),
        }
    if selected_path.is_absolute():
        try:
            # Keep the lexical path intact so _project_file can reject a
            # symlink in any parent component before resolution.
            selected_path = selected_path.absolute().relative_to(root)
        except (OSError, ValueError):
            return {
                "status": "locked_invalid_positive_proof",
                "release_allowed": False,
                "failures": ["positive_proof_path_outside_project"],
            }
    proof_file = _project_file(root, selected_path)
    if proof_file is None:
        return {
            "status": "locked_invalid_positive_proof",
            "release_allowed": False,
            "failures": ["positive_proof_path_invalid"],
        }
    try:
        proof = _read_json(proof_file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {
            "status": "locked_invalid_positive_proof",
            "release_allowed": False,
            "failures": ["positive_proof_unreadable"],
        }

    failures: list[str] = []
    if proof.get("schema_version") != 1:
        failures.append("positive_proof_schema_version_invalid")
    if _text(proof.get("status")) != "owner_approved_positive_proof":
        failures.append("positive_proof_status_not_owner_approved")
    candidate_id = _text(proof.get("candidate_id"))
    build_id = _text(proof.get("build_id"))
    if not candidate_id:
        failures.append("candidate_id_missing")
    if not build_id:
        failures.append("build_id_missing")

    registry_sha = _sha256(registry_path)
    if _text(proof.get("candidate_identity_registry_sha256")).lower() != registry_sha:
        failures.append("positive_proof_registry_sha256_mismatch")
    if _text(backlog.get("candidate_identity_registry_sha256")).lower() != registry_sha:
        failures.append("backlog_registry_sha256_mismatch")

    registered_subjects = {
        _text(item.get("canonical_candidate_id")): _text(item.get("subject_id"))
        for item in registry.get("candidates", [])
        if isinstance(item, Mapping) and _text(item.get("canonical_candidate_id"))
    }
    registered_ids = set(registered_subjects)
    if candidate_id not in registered_ids:
        failures.append("candidate_not_in_identity_registry")
    subject_id = _text(proof.get("subject_id"))
    if not subject_id:
        failures.append("subject_id_missing")
    elif registered_subjects.get(candidate_id) != subject_id:
        failures.append("positive_proof_subject_mismatch")

    components = proof.get("components")
    if not isinstance(components, Mapping):
        failures.append("components_missing")
        components = {}
    component_hashes: dict[str, str] = {}
    for component in policy.get("required_component_artifacts", []):
        name = _text(component)
        _path, digest = _verify_binding(
            root,
            components.get(name),
            f"component_{name}",
            failures,
        )
        component_hashes[name] = digest

    gates = proof.get("gates")
    if not isinstance(gates, Mapping):
        failures.append("gates_missing")
        gates = {}
    for gate in policy.get("required_gates", []):
        name = _text(gate)
        if gates.get(name) is not True:
            failures.append(f"gate_not_passed:{name}")

    approval_path, _approval_hash = _verify_binding(
        root,
        proof.get("owner_approval"),
        "owner_approval",
        failures,
    )
    if approval_path is not None:
        try:
            approval = _read_json(approval_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            failures.append("owner_approval_unreadable")
            approval = {}
        if _text(approval.get("owner_authority_id")) != _text(policy.get("owner_authority_id")):
            failures.append("owner_authority_id_mismatch")
        if _text(approval.get("decision")) != _text(policy.get("required_owner_decision")):
            failures.append("owner_decision_mismatch")
        if _text(approval.get("candidate_id")) != candidate_id:
            failures.append("owner_approval_candidate_mismatch")
        if _text(approval.get("subject_id")) != subject_id:
            failures.append("owner_approval_subject_mismatch")
        if _text(approval.get("build_id")) != build_id:
            failures.append("owner_approval_build_mismatch")
        if approval.get("reviewed_in_motion") is not True:
            failures.append("owner_approval_motion_review_missing")
        if approval.get("reviewed_clothed") is not True:
            failures.append("owner_approval_clothed_review_missing")
        if approval.get("counts_toward_two_subject_gate") is not True:
            failures.append("owner_approval_two_subject_qualification_not_true")
        if approval.get("release_downstream_autobuild") is not False:
            failures.append("one_subject_owner_approval_must_not_release_autobuild")
        approved_hashes = approval.get("component_sha256")
        if not isinstance(approved_hashes, Mapping):
            failures.append("owner_approval_component_hashes_missing")
        else:
            for name, digest in component_hashes.items():
                if _text(approved_hashes.get(name)).lower() != digest:
                    failures.append(f"owner_approval_component_hash_mismatch:{name}")

    if proof.get("runtime_activation_allowed") is not False:
        failures.append("positive_proof_runtime_activation_must_be_false")
    if proof.get("public_export_allowed") is not False:
        failures.append("positive_proof_public_export_must_be_false")
    if policy.get("runtime_activation_allowed") is not False:
        failures.append("policy_runtime_activation_must_be_false")
    if int(policy.get("maximum_concurrent_downstream_builds", 0)) != 1:
        failures.append("maximum_concurrency_must_equal_one")

    if failures:
        return {
            "status": "locked_positive_proof_failed",
            "release_allowed": False,
            "subject_qualification_ready": False,
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "build_id": build_id,
            "failures": failures,
            "maximum_concurrent_downstream_builds": 1,
        }
    return {
        "status": "positive_proof_passed_subject_qualification_only",
        "release_allowed": False,
        "subject_qualification_ready": True,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "build_id": build_id,
        "registry_sha256": registry_sha,
        "positive_proof_sha256": _sha256(proof_file),
        "owner_approval_sha256": _approval_hash,
        "maximum_concurrent_downstream_builds": 1,
        "batch_gate_required": "avatar_two_distinct_subject_autobuild_gate_v2",
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "failures": [],
    }


def downstream_candidate_order(backlog: Mapping[str, Any]) -> list[str]:
    ordered: list[str] = []
    for section in (
        "next_owner_reviewed_likeness_builds",
        "later_adult_canon_or_historical_builds",
        "adult_generated_experts_need_owner_design_sheets",
        "separate_non_adult_test_after_gwen",
    ):
        for item in backlog.get(section, []) or []:
            candidate_id = _text(item.get("candidate_id")) if isinstance(item, Mapping) else _text(item)
            if candidate_id and candidate_id not in ordered:
                ordered.append(candidate_id)
    return ordered


def build_downstream_release_plan(project_root: Path, evaluation: Mapping[str, Any]) -> dict[str, Any]:
    del project_root, evaluation
    raise ValueError(
        "a one-subject positive proof cannot release batch authoring; "
        "use Core.avatar_two_subject_autobuild_gate after two distinct "
        "canonical subjects qualify"
    )
