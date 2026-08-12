"""Two-distinct-subject release gate for Avatar Builder batch authoring.

The evaluator is read-only.  It cannot render, generate, queue, activate,
replace, or publish an avatar.  A legacy one-body positive proof is only a
per-subject qualification input.  Batch authoring becomes eligible only when
two different canonical subject IDs have exact, content-addressed proof,
domain-evidence, and owner-review artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import hashlib
import json

from Core.avatar_positive_proof_gate import (
    BACKLOG_PATH,
    REGISTRY_PATH,
    downstream_candidate_order,
    evaluate_positive_proof,
)


POLICY_PATH = Path("Avatar/avatar_builder/policies/two_subject_autobuild_gate_v2.json")

MANDATORY_COMPONENTS = ("body", "eyes", "hair", "clothing", "rig")
MANDATORY_DOMAINS = (
    "topology",
    "rig_and_deformation",
    "skin_integrity",
    "ground_contact",
    "object_contact",
    "clothed_visual_quality",
)
MANDATORY_GATES_BY_DOMAIN = {
    "topology": ("topology_lane_correct",),
    "rig_and_deformation": (
        "stable_rig",
        "walk_sit_reach_deformation",
        "face_controls",
        "walk_stop_turn",
        "sit_stand_lie_rise",
    ),
    "skin_integrity": ("skin_material_and_deformation_integrity",),
    "ground_contact": ("feet_and_ground_contact",),
    "object_contact": ("prop_contact",),
    "clothed_visual_quality": (
        "visual_likeness_reviewed",
        "clothed_visual_integrity",
        "visible_realistic_eyes",
        "separate_clothing_integrity",
        "privacy_review",
        "owner_visual_approval",
    ),
}
MANDATORY_OWNER_FLAGS = (
    "reviewed_clothed",
    "reviewed_in_motion",
    "reviewed_full_body",
    "reviewed_face_and_eyes",
    "reviewed_skin_and_deformation",
    "reviewed_ground_contact",
    "reviewed_object_contact",
    "counts_toward_two_subject_gate",
    "allow_batch_authoring_after_two_distinct_qualified_subjects",
)
OWNER_AUTHORITY_ID = "real_robert"
OWNER_DECISION = "approve_body_for_two_subject_autobuild_qualification"
IMMUTABLE_ROOTS = {
    "subject_proofs": "Avatar/avatar_builder/autobuild_two_subject/immutable/subject_proofs",
    "owner_reviews": "Avatar/avatar_builder/autobuild_two_subject/immutable/owner_reviews",
    "domain_evidence": "Avatar/avatar_builder/autobuild_two_subject/immutable/domain_evidence",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_digest(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path.name}")
    return data


def _project_file(project_root: Path, raw: Any) -> Path | None:
    """Resolve a regular project file while rejecting traversal and symlinks."""

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


def _immutable_root(project_root: Path, raw: Any) -> Path | None:
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
    return resolved if resolved.is_dir() else None


def _binding_file(
    project_root: Path,
    binding: Any,
    label: str,
    failures: list[str],
    *,
    immutable_root: Path | None = None,
    content_addressed_json: bool = False,
) -> tuple[Path | None, str]:
    if not isinstance(binding, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    expected = _text(binding.get("sha256")).lower()
    if not _is_digest(expected):
        failures.append(f"{label}_sha256_invalid")
    path = _project_file(project_root, binding.get("path"))
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, expected
    if immutable_root is not None:
        try:
            path.relative_to(immutable_root)
        except ValueError:
            failures.append(f"{label}_outside_immutable_root")
    if content_addressed_json and path.name.lower() != f"{expected}.json":
        failures.append(f"{label}_not_content_addressed")
    if _is_digest(expected) and _sha256(path) != expected:
        failures.append(f"{label}_sha256_mismatch")
    return path, expected


def _domain_artifact_valid(
    project_root: Path,
    artifact: Mapping[str, Any],
    *,
    domain: str,
    candidate_id: str,
    subject_id: str,
    build_id: str,
    component_hashes: Mapping[str, str],
    required_components: list[str],
    failures: list[str],
) -> None:
    prefix = f"domain_{domain}"
    if artifact.get("schema_version") != 1:
        failures.append(f"{prefix}_schema_invalid")
    if _text(artifact.get("artifact_type")) != "avatar_body_domain_proof":
        failures.append(f"{prefix}_artifact_type_invalid")
    if _text(artifact.get("domain")) != domain:
        failures.append(f"{prefix}_name_mismatch")
    if _text(artifact.get("candidate_id")) != candidate_id:
        failures.append(f"{prefix}_candidate_mismatch")
    if _text(artifact.get("subject_id")) != subject_id:
        failures.append(f"{prefix}_subject_mismatch")
    if _text(artifact.get("build_id")) != build_id:
        failures.append(f"{prefix}_build_mismatch")
    if _text(artifact.get("decision")) != "pass":
        failures.append(f"{prefix}_decision_not_pass")
    if artifact.get("exact_build_observed") is not True:
        failures.append(f"{prefix}_exact_build_not_observed")
    if artifact.get("review_complete") is not True:
        failures.append(f"{prefix}_review_incomplete")
    if artifact.get("runtime_activation_allowed") is not False:
        failures.append(f"{prefix}_runtime_activation_must_be_false")
    if artifact.get("public_export_allowed") is not False:
        failures.append(f"{prefix}_public_export_must_be_false")

    bound_hashes = artifact.get("component_sha256")
    if not isinstance(bound_hashes, Mapping):
        failures.append(f"{prefix}_component_hashes_missing")
    else:
        for component in required_components:
            expected = _text(component_hashes.get(component)).lower()
            if _text(bound_hashes.get(component)).lower() != expected:
                failures.append(f"{prefix}_component_hash_mismatch:{component}")

    retained = artifact.get("retained_evidence")
    if not isinstance(retained, list) or not retained:
        failures.append(f"{prefix}_retained_evidence_missing")
        return
    if len(retained) > 64:
        failures.append(f"{prefix}_retained_evidence_too_many")
        return
    for index, binding in enumerate(retained):
        _binding_file(
            project_root,
            binding,
            f"{prefix}_retained_{index}",
            failures,
        )


def _owner_review_valid(
    review: Mapping[str, Any],
    *,
    candidate_id: str,
    subject_id: str,
    build_id: str,
    component_hashes: Mapping[str, str],
    domain_hashes: Mapping[str, str],
    failures: list[str],
) -> None:
    if review.get("schema_version") != 2:
        failures.append("owner_review_schema_invalid")
    if _text(review.get("artifact_type")) != "immutable_owner_body_review":
        failures.append("owner_review_artifact_type_invalid")
    if _text(review.get("owner_authority_id")) != OWNER_AUTHORITY_ID:
        failures.append("owner_review_authority_mismatch")
    if _text(review.get("decision")) != OWNER_DECISION:
        failures.append("owner_review_decision_mismatch")
    if _text(review.get("candidate_id")) != candidate_id:
        failures.append("owner_review_candidate_mismatch")
    if _text(review.get("subject_id")) != subject_id:
        failures.append("owner_review_subject_mismatch")
    if _text(review.get("build_id")) != build_id:
        failures.append("owner_review_build_mismatch")
    for name in MANDATORY_OWNER_FLAGS:
        if review.get(name) is not True:
            failures.append(f"owner_review_flag_not_true:{name}")
    if review.get("release_downstream_autobuild_by_itself") is not False:
        failures.append("owner_review_cannot_release_by_itself")
    if review.get("runtime_activation_allowed") is not False:
        failures.append("owner_review_runtime_activation_must_be_false")
    if review.get("public_export_allowed") is not False:
        failures.append("owner_review_public_export_must_be_false")

    reviewed_components = review.get("component_sha256")
    if not isinstance(reviewed_components, Mapping):
        failures.append("owner_review_component_hashes_missing")
    else:
        for name, digest in component_hashes.items():
            if _text(reviewed_components.get(name)).lower() != digest:
                failures.append(f"owner_review_component_hash_mismatch:{name}")
    reviewed_domains = review.get("domain_evidence_sha256")
    if not isinstance(reviewed_domains, Mapping):
        failures.append("owner_review_domain_hashes_missing")
    else:
        for name, digest in domain_hashes.items():
            if _text(reviewed_domains.get(name)).lower() != digest:
                failures.append(f"owner_review_domain_hash_mismatch:{name}")


def evaluate_two_subject_autobuild_gate(project_root: Path) -> dict[str, Any]:
    """Evaluate the configured two-subject gate without mutating project state."""

    root = Path(project_root).resolve(strict=True)
    policy_path = root / POLICY_PATH
    registry_path = root / REGISTRY_PATH
    backlog_path = root / BACKLOG_PATH
    failures: list[str] = []
    try:
        policy = _read_json(policy_path)
        registry = _read_json(registry_path)
        backlog = _read_json(backlog_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {
            "status": "locked_two_subject_gate_configuration_invalid",
            "batch_auto_authoring_allowed": False,
            "queue_created": False,
            "failures": ["gate_configuration_unreadable"],
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }

    if policy.get("schema_version") != 2:
        failures.append("two_subject_policy_schema_invalid")
    if _text(policy.get("owner_authority_id")) != OWNER_AUTHORITY_ID:
        failures.append("policy_owner_authority_id_invalid")
    if _text(policy.get("required_owner_decision")) != OWNER_DECISION:
        failures.append("policy_required_owner_decision_invalid")
    required_subjects = int(policy.get("minimum_distinct_canonical_subjects", 0) or 0)
    if required_subjects != 2:
        failures.append("minimum_distinct_canonical_subjects_must_equal_two")
    maximum_enrolled = int(policy.get("maximum_enrolled_qualifications", 0) or 0)
    if maximum_enrolled < 2 or maximum_enrolled > 32:
        failures.append("maximum_enrolled_qualifications_out_of_bounds")
    if int(policy.get("maximum_concurrent_downstream_builds", 0) or 0) != 1:
        failures.append("maximum_concurrent_downstream_builds_must_equal_one")
    for key in (
        "runtime_activation_allowed",
        "live_body_replacement_allowed",
        "public_export_allowed",
        "queue_creation_allowed_by_evaluator",
    ):
        if policy.get(key) is not False:
            failures.append(f"policy_{key}_must_be_false")

    registry_sha = _sha256(registry_path)
    if _text(backlog.get("candidate_identity_registry_sha256")).lower() != registry_sha:
        failures.append("backlog_registry_sha256_mismatch")
    canonical_subjects = {
        _text(item.get("canonical_candidate_id")): _text(item.get("subject_id"))
        for item in registry.get("candidates", [])
        if isinstance(item, Mapping)
        and _text(item.get("canonical_candidate_id"))
        and _text(item.get("subject_id"))
    }

    roots = policy.get("immutable_roots")
    if not isinstance(roots, Mapping):
        failures.append("immutable_roots_missing")
        roots = {}
    if {key: _text(roots.get(key)) for key in IMMUTABLE_ROOTS} != IMMUTABLE_ROOTS:
        failures.append("immutable_roots_do_not_match_code_authority")
    proof_root = _immutable_root(root, IMMUTABLE_ROOTS["subject_proofs"])
    review_root = _immutable_root(root, IMMUTABLE_ROOTS["owner_reviews"])
    evidence_root = _immutable_root(root, IMMUTABLE_ROOTS["domain_evidence"])
    if proof_root is None:
        failures.append("subject_proof_immutable_root_invalid")
    if review_root is None:
        failures.append("owner_review_immutable_root_invalid")
    if evidence_root is None:
        failures.append("domain_evidence_immutable_root_invalid")

    configured_components = tuple(_text(x) for x in policy.get("required_component_artifacts", []))
    configured_domains = tuple(_text(x) for x in policy.get("required_evidence_domains", []))
    required_components = list(MANDATORY_COMPONENTS)
    required_domains = list(MANDATORY_DOMAINS)
    if configured_components != MANDATORY_COMPONENTS:
        failures.append("required_component_artifacts_do_not_match_code_authority")
    if configured_domains != MANDATORY_DOMAINS:
        failures.append("required_evidence_domains_do_not_match_code_authority")
    legacy_by_domain = policy.get("required_legacy_gates_by_domain")
    if not isinstance(legacy_by_domain, Mapping):
        failures.append("required_legacy_gates_by_domain_missing")
        legacy_by_domain = {}
    elif set(required_domains) != set(legacy_by_domain):
        failures.append("required_legacy_gate_domain_set_mismatch")
    else:
        for domain, mandatory in MANDATORY_GATES_BY_DOMAIN.items():
            configured = legacy_by_domain.get(domain)
            if not isinstance(configured, list) or tuple(_text(x) for x in configured) != mandatory:
                failures.append(f"required_legacy_gates_do_not_match_code_authority:{domain}")
    configured_owner_flags = tuple(_text(x) for x in policy.get("required_owner_review_flags", []))
    if configured_owner_flags != MANDATORY_OWNER_FLAGS:
        failures.append("required_owner_review_flags_do_not_match_code_authority")

    bindings = policy.get("qualification_bindings")
    if not isinstance(bindings, list):
        failures.append("qualification_bindings_invalid")
        bindings = []
    if maximum_enrolled and len(bindings) > maximum_enrolled:
        failures.append("qualification_bindings_exceed_bound")

    qualifications: list[dict[str, str]] = []
    seen_proof_hashes: set[str] = set()
    for index, binding in enumerate(bindings):
        local_failures: list[str] = []
        proof_path, proof_hash = _binding_file(
            root,
            binding,
            f"qualification_{index}",
            local_failures,
            immutable_root=proof_root,
            content_addressed_json=True,
        )
        if proof_hash in seen_proof_hashes:
            local_failures.append("qualification_proof_duplicate")
        if proof_hash:
            seen_proof_hashes.add(proof_hash)
        if proof_path is None or local_failures:
            failures.extend(local_failures)
            continue
        try:
            proof = _read_json(proof_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            failures.append(f"qualification_{index}_unreadable")
            continue

        legacy = evaluate_positive_proof(root, proof_path)
        if legacy.get("subject_qualification_ready") is not True:
            for item in legacy.get("failures", []) or ["legacy_subject_proof_failed"]:
                local_failures.append(f"qualification_{index}:{_text(item)}")

        candidate_id = _text(proof.get("candidate_id"))
        subject_id = _text(proof.get("subject_id"))
        build_id = _text(proof.get("build_id"))
        if canonical_subjects.get(candidate_id) != subject_id:
            local_failures.append(f"qualification_{index}:canonical_subject_mismatch")
        if _text(proof.get("candidate_identity_registry_sha256")).lower() != registry_sha:
            local_failures.append(f"qualification_{index}:registry_sha256_mismatch")

        components = proof.get("components")
        component_hashes: dict[str, str] = {}
        if not isinstance(components, Mapping):
            local_failures.append(f"qualification_{index}:components_missing")
            components = {}
        for component in required_components:
            _path, digest = _binding_file(
                root,
                components.get(component),
                f"qualification_{index}_component_{component}",
                local_failures,
            )
            component_hashes[component] = digest

        gates = proof.get("gates")
        if not isinstance(gates, Mapping):
            gates = {}
        for domain in required_domains:
            for name in MANDATORY_GATES_BY_DOMAIN[domain]:
                if gates.get(name) is not True:
                    local_failures.append(
                        f"qualification_{index}:legacy_gate_not_passed:{domain}:{name}"
                    )

        evidence = proof.get("evidence")
        if not isinstance(evidence, Mapping):
            local_failures.append(f"qualification_{index}:domain_evidence_missing")
            evidence = {}
        domain_hashes: dict[str, str] = {}
        for domain in required_domains:
            evidence_path, evidence_hash = _binding_file(
                root,
                evidence.get(domain),
                f"qualification_{index}_domain_{domain}",
                local_failures,
                immutable_root=evidence_root,
                content_addressed_json=True,
            )
            domain_hashes[domain] = evidence_hash
            if evidence_path is None:
                continue
            try:
                domain_artifact = _read_json(evidence_path)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                local_failures.append(f"qualification_{index}_domain_{domain}_unreadable")
                continue
            _domain_artifact_valid(
                root,
                domain_artifact,
                domain=domain,
                candidate_id=candidate_id,
                subject_id=subject_id,
                build_id=build_id,
                component_hashes=component_hashes,
                required_components=required_components,
                failures=local_failures,
            )

        review_path, review_hash = _binding_file(
            root,
            proof.get("owner_approval"),
            f"qualification_{index}_owner_review",
            local_failures,
            immutable_root=review_root,
            content_addressed_json=True,
        )
        if review_path is not None:
            try:
                review = _read_json(review_path)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                local_failures.append(f"qualification_{index}_owner_review_unreadable")
            else:
                _owner_review_valid(
                    review,
                    candidate_id=candidate_id,
                    subject_id=subject_id,
                    build_id=build_id,
                    component_hashes=component_hashes,
                    domain_hashes=domain_hashes,
                    failures=local_failures,
                )

        if proof.get("runtime_activation_allowed") is not False:
            local_failures.append(f"qualification_{index}:runtime_activation_must_be_false")
        if proof.get("public_export_allowed") is not False:
            local_failures.append(f"qualification_{index}:public_export_must_be_false")

        if local_failures:
            failures.extend(local_failures)
            continue
        qualifications.append(
            {
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "build_id": build_id,
                "body_sha256": component_hashes.get("body", ""),
                "positive_proof_sha256": proof_hash,
                "owner_review_sha256": review_hash,
            }
        )

    candidate_ids = [item["candidate_id"] for item in qualifications]
    subject_ids = [item["subject_id"] for item in qualifications]
    if len(candidate_ids) != len(set(candidate_ids)):
        failures.append("qualified_canonical_candidate_ids_not_distinct")
    body_hashes = [item["body_sha256"] for item in qualifications]
    if len(body_hashes) != len(set(body_hashes)):
        failures.append("qualified_subjects_share_same_body_artifact")
    distinct_subjects = len(set(subject_ids))
    if distinct_subjects < required_subjects:
        failures.append(f"insufficient_distinct_qualified_subjects:{distinct_subjects}/{required_subjects}")

    failures = list(dict.fromkeys(failures))
    allowed = not failures and distinct_subjects >= required_subjects
    if allowed:
        status = "two_subject_gate_passed_batch_authoring_eligible_not_queued"
    elif bindings and any(not item.startswith("insufficient_distinct") for item in failures):
        status = "locked_two_subject_qualification_invalid"
    else:
        status = "locked_awaiting_two_distinct_owner_approved_bodies"
    return {
        "schema_version": 2,
        "status": status,
        "batch_auto_authoring_allowed": allowed,
        "qualified_body_count": len(qualifications),
        "distinct_canonical_subject_count": distinct_subjects,
        "minimum_distinct_canonical_subjects": required_subjects,
        "qualifications": qualifications,
        "failures": failures,
        "maximum_concurrent_downstream_builds": 1,
        "queue_created": False,
        "body_created": False,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "public_export_allowed": False,
        "registry_sha256": registry_sha,
        "policy_sha256": _sha256(policy_path),
    }


def build_two_subject_autobuild_dry_run_plan(
    project_root: Path,
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a non-mutating, one-at-a-time schedule after the gate passes."""

    if evaluation.get("batch_auto_authoring_allowed") is not True:
        raise ValueError("two distinct canonical subject proofs have not released batch authoring")
    root = Path(project_root).resolve(strict=True)
    registry = _read_json(root / REGISTRY_PATH)
    backlog = _read_json(root / BACKLOG_PATH)
    candidate_subjects = {
        _text(item.get("canonical_candidate_id")): _text(item.get("subject_id"))
        for item in registry.get("candidates", [])
        if isinstance(item, Mapping)
    }
    qualified_subjects = {
        _text(item.get("subject_id"))
        for item in evaluation.get("qualifications", [])
        if isinstance(item, Mapping)
    }
    candidate_order: list[str] = []
    skipped_unregistered: list[str] = []
    for candidate_id in downstream_candidate_order(backlog):
        if candidate_id not in candidate_subjects:
            skipped_unregistered.append(candidate_id)
            continue
        if candidate_subjects[candidate_id] in qualified_subjects:
            continue
        candidate_order.append(candidate_id)
    return {
        "schema_version": 2,
        "status": "dry_run_one_at_a_time_authoring_schedule_not_queued",
        "gate_policy_sha256": _text(evaluation.get("policy_sha256")),
        "qualified_subject_ids": sorted(qualified_subjects),
        "maximum_concurrent_body_builds": 1,
        "candidate_order": candidate_order,
        "skipped_unregistered_or_alias_only": skipped_unregistered,
        "queue_created": False,
        "body_created": False,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "This is a dry-run authoring order only. Every downstream candidate "
            "still needs its own canonical identity/maturity, source, topology, "
            "rig, skin, contact, clothing, privacy, and owner-review gates."
        ),
    }
