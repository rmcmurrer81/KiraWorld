"""Fail-closed, one-body unlock for private Avatar Builder staging plans.

This module deliberately does not author, queue, run, approve, activate,
replace, export, or release anything.  One exact inactive body must first pass
``avatar_single_body_quality_gate``.  A success can produce only a dry-run,
serial list of private reference-audit and candidate-preparation jobs.

The authoritative two-distinct-subject autobuild gate remains unchanged and
is still required for any broader batch-authoring eligibility.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_positive_proof_gate import (
    BACKLOG_PATH,
    REGISTRY_PATH,
    downstream_candidate_order,
)
from Core.avatar_single_body_quality_gate import evaluate_two_pass_body_quality


POLICY_PATH = Path(
    "Avatar/avatar_builder/policies/one_body_private_staging_planner_v1.json"
)
AUTHORITATIVE_BATCH_GATE = (
    "Avatar/avatar_builder/policies/two_subject_autobuild_gate_v2.json"
)
ALLOWED_PRIVATE_JOB_TYPES = (
    "private_reference_audit",
    "private_candidate_preparation",
)
ELIGIBLE_MATURITY_LANES: dict[str, dict[str, Any]] = {
    "adult": {
        "topology_lane": "confirmed_adult_topology",
        "adult_anatomy_allowed": True,
    },
    "non_adult_doll_safe": {
        "topology_lane": "non_adult_doll_safe_topology",
        "adult_anatomy_allowed": False,
    },
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("json_root_not_object")
    return value


def _project_file(project_root: Path, raw: Any) -> Path | None:
    """Resolve a regular project file while rejecting traversal and symlinks."""

    text = _text(raw)
    if not text:
        return None
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    lexical = project_root
    for part in relative.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            return None
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _policy_failures(policy: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if policy.get("schema_version") != 1:
        failures.append("private_staging_policy_schema_invalid")
    if _text(policy.get("policy_id")) != "avatar_one_body_private_staging_planner_v1":
        failures.append("private_staging_policy_id_invalid")
    if _text(policy.get("unlock_gate")) != "single_body_two_pass_quality_v1":
        failures.append("private_staging_unlock_gate_invalid")
    if _text(policy.get("required_unlock_status")) != "two_pass_quality_passed":
        failures.append("private_staging_unlock_status_invalid")
    if int(policy.get("maximum_concurrent_private_jobs", 0) or 0) != 1:
        failures.append("maximum_concurrent_private_jobs_must_equal_one")
    configured_jobs = tuple(_text(value) for value in policy.get("allowed_private_job_types", []))
    if configured_jobs != ALLOWED_PRIVATE_JOB_TYPES:
        failures.append("private_staging_job_allowlist_invalid")
    if policy.get("eligible_maturity_lanes") != ELIGIBLE_MATURITY_LANES:
        failures.append("private_staging_maturity_policy_invalid")
    if policy.get("unresolved_maturity_is_eligible") is not False:
        failures.append("unresolved_maturity_must_remain_ineligible")
    for key in (
        "queue_creation_allowed_by_evaluator",
        "automatic_execution_allowed_by_planner",
        "owner_approval_inferred",
        "runtime_activation_allowed",
        "live_body_replacement_allowed",
        "public_export_allowed",
        "release_allowed",
    ):
        if policy.get(key) is not False:
            failures.append(f"private_staging_policy_{key}_must_be_false")
    if _text(policy.get("authoritative_batch_gate")) != AUTHORITATIVE_BATCH_GATE:
        failures.append("authoritative_batch_gate_path_changed")
    if policy.get("authoritative_batch_gate_unchanged") is not True:
        failures.append("authoritative_batch_gate_not_preserved")
    return failures


def evaluate_private_staging_unlock(
    project_root: Path,
    manifest_path: str | Path,
    review_path: str | Path,
) -> dict[str, Any]:
    """Evaluate one exact manifest/review pair without creating a queue."""

    root = Path(project_root).resolve(strict=True)
    failures: list[str] = []
    policy_path = root / POLICY_PATH
    registry_path = root / REGISTRY_PATH
    backlog_path = root / BACKLOG_PATH

    manifest_file = _project_file(root, manifest_path)
    review_file = _project_file(root, review_path)
    if manifest_file is None:
        failures.append("single_body_manifest_path_invalid")
    if review_file is None:
        failures.append("single_body_visual_review_path_invalid")

    try:
        policy = _read_json(policy_path)
        registry = _read_json(registry_path)
        backlog = _read_json(backlog_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        policy, registry, backlog = {}, {}, {}
        failures.append("private_staging_configuration_unreadable")
    failures.extend(_policy_failures(policy))

    registry_sha = _sha256(registry_path) if registry_path.is_file() else ""
    backlog_sha = _sha256(backlog_path) if backlog_path.is_file() else ""
    if _text(backlog.get("candidate_identity_registry_sha256")).lower() != registry_sha:
        failures.append("private_staging_backlog_registry_sha256_mismatch")

    quality: dict[str, Any]
    if manifest_file is None or review_file is None:
        quality = {
            "gate": "single_body_two_pass_quality_v1",
            "status": "not_evaluated_invalid_binding",
            "passed": False,
            "candidate_id": "",
            "candidate_sha256": "",
        }
    else:
        try:
            manifest = _read_json(manifest_file)
            review = _read_json(review_file)
            quality = evaluate_two_pass_body_quality(root, manifest, review)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            quality = {
                "gate": "single_body_two_pass_quality_v1",
                "status": "not_evaluated_invalid_json",
                "passed": False,
                "candidate_id": "",
                "candidate_sha256": "",
            }
            failures.append("single_body_quality_inputs_unreadable")

    if quality.get("gate") != "single_body_two_pass_quality_v1":
        failures.append("single_body_quality_gate_identity_invalid")
    if quality.get("passed") is not True:
        failures.append("no_exact_candidate_has_passed_single_body_two_pass_quality")
    if quality.get("status") != "two_pass_quality_passed":
        failures.append("single_body_two_pass_quality_status_not_passed")
    candidate_sha = _text(quality.get("candidate_sha256")).lower()
    if quality.get("passed") is True and not SHA256_RE.fullmatch(candidate_sha):
        failures.append("single_body_quality_candidate_sha256_invalid")
    if quality.get("authoritative_batch_gate_unchanged") != (
        "avatar_two_distinct_subject_autobuild_gate_v2"
    ):
        failures.append("single_body_quality_did_not_preserve_batch_gate")

    failures = list(dict.fromkeys(failures))
    eligible = not failures and quality.get("passed") is True
    quality_summary = {
        "gate": _text(quality.get("gate")),
        "status": _text(quality.get("status")),
        "passed": quality.get("passed") is True,
        "candidate_id": _text(quality.get("candidate_id")),
        "candidate_sha256": candidate_sha,
        "subject_id": _text(
            quality.get("objective", {}).get("subject_id")
            if isinstance(quality.get("objective"), Mapping)
            else ""
        ),
        "objective_status": _text(
            quality.get("objective", {}).get("status")
            if isinstance(quality.get("objective"), Mapping)
            else ""
        ),
        "rendered_visual_status": _text(
            quality.get("rendered_visual", {}).get("status")
            if isinstance(quality.get("rendered_visual"), Mapping)
            else ""
        ),
        "objective_failures": list(
            quality.get("objective", {}).get("failures", [])
            if isinstance(quality.get("objective"), Mapping)
            else []
        ),
        "rendered_visual_failures": list(
            quality.get("rendered_visual", {}).get("failures", [])
            if isinstance(quality.get("rendered_visual"), Mapping)
            else []
        ),
    }
    return {
        "schema_version": 1,
        "planner": "avatar_one_body_private_staging_planner_v1",
        "status": (
            "eligible_for_private_serial_staging_plan_not_queued"
            if eligible
            else "locked_awaiting_one_exact_two_pass_body"
        ),
        "private_serial_staging_plan_allowed": eligible,
        "quality": quality_summary,
        "bindings": {
            "manifest": {
                "path": _text(manifest_path),
                "sha256": _sha256(manifest_file) if manifest_file else "",
            },
            "rendered_visual_review": {
                "path": _text(review_path),
                "sha256": _sha256(review_file) if review_file else "",
            },
            "candidate_identity_registry": {
                "path": REGISTRY_PATH.as_posix(),
                "sha256": registry_sha,
            },
            "authoring_backlog": {
                "path": BACKLOG_PATH.as_posix(),
                "sha256": backlog_sha,
            },
            "planner_policy": {
                "path": POLICY_PATH.as_posix(),
                "sha256": _sha256(policy_path) if policy_path.is_file() else "",
            },
        },
        "failures": failures,
        "maximum_concurrent_private_jobs": 1,
        "allowed_private_job_types": list(ALLOWED_PRIVATE_JOB_TYPES),
        "queue_created": False,
        "automatic_execution_started": False,
        "owner_approval_inferred": False,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "public_export_allowed": False,
        "release_allowed": False,
        "automatic_multi_profile_queue_allowed": False,
        "authoritative_batch_gate": AUTHORITATIVE_BATCH_GATE,
        "authoritative_batch_gate_unchanged": True,
        "truth_note": (
            "This evaluator can unlock only a dry-run, private, serial staging plan. "
            "It never creates or executes a queue and never approves, activates, replaces, "
            "exports, or releases a body."
        ),
    }


def _version_is_resolved(entry: Mapping[str, Any]) -> bool:
    version = entry.get("version_policy")
    if not isinstance(version, Mapping) or version.get("required") is not True:
        return True
    binding = version.get("binding")
    if not isinstance(binding, Mapping):
        return False
    expected = _text(binding.get("expected"))
    accepted = binding.get("accepted_values")
    return bool(expected or (isinstance(accepted, list) and accepted))


def build_private_staging_dry_run_plan(
    project_root: Path,
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a content-anchored serial plan; do not queue or execute it."""

    if evaluation.get("private_serial_staging_plan_allowed") is not True:
        raise ValueError("one exact candidate has not passed the two-pass quality gate")
    if evaluation.get("authoritative_batch_gate_unchanged") is not True:
        raise ValueError("authoritative two-subject batch gate was not preserved")

    root = Path(project_root).resolve(strict=True)
    registry_path = root / REGISTRY_PATH
    backlog_path = root / BACKLOG_PATH
    bindings = evaluation.get("bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("staging unlock bindings are missing")
    registry_binding = bindings.get("candidate_identity_registry")
    backlog_binding = bindings.get("authoring_backlog")
    if not isinstance(registry_binding, Mapping) or not isinstance(backlog_binding, Mapping):
        raise ValueError("staging registry/backlog bindings are missing")
    if _text(registry_binding.get("sha256")).lower() != _sha256(registry_path):
        raise ValueError("candidate identity registry changed after unlock evaluation")
    if _text(backlog_binding.get("sha256")).lower() != _sha256(backlog_path):
        raise ValueError("authoring backlog changed after unlock evaluation")

    registry = _read_json(registry_path)
    backlog = _read_json(backlog_path)
    entries = {
        _text(item.get("canonical_candidate_id")): item
        for item in registry.get("candidates", [])
        if isinstance(item, Mapping) and _text(item.get("canonical_candidate_id"))
    }
    passed_subject = _text(evaluation.get("quality", {}).get("subject_id"))
    if not passed_subject:
        # Older gate summaries identify the exact candidate but do not need to
        # expose a subject ID. Exact downstream identity still comes only from
        # the registry below.
        passed_subject = ""
    skipped: list[dict[str, str]] = []
    jobs: list[dict[str, Any]] = []
    previous_job_id = ""
    sequence = 0
    for candidate_id in downstream_candidate_order(backlog):
        entry = entries.get(candidate_id)
        if entry is None:
            skipped.append({
                "candidate_id": candidate_id,
                "reason": "not_in_exact_candidate_identity_registry",
            })
            continue
        subject_id = _text(entry.get("subject_id"))
        if passed_subject and subject_id == passed_subject:
            skipped.append({"candidate_id": candidate_id, "reason": "unlock_subject_already_passed"})
            continue
        maturity = entry.get("maturity_policy")
        lane = _normalized(maturity.get("lane")) if isinstance(maturity, Mapping) else ""
        route = ELIGIBLE_MATURITY_LANES.get(lane)
        if route is None:
            skipped.append({
                "candidate_id": candidate_id,
                "reason": "maturity_unresolved_or_not_staging_eligible",
            })
            continue
        if not _version_is_resolved(entry):
            skipped.append({
                "candidate_id": candidate_id,
                "reason": "required_identity_version_unresolved",
            })
            continue

        common = {
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "maturity_lane": lane,
            "topology_lane": route["topology_lane"],
            "adult_anatomy_allowed": route["adult_anatomy_allowed"],
            "identity_registry_sha256": _sha256(registry_path),
            "authoring_backlog_sha256": _sha256(backlog_path),
            "unlock_candidate_sha256": _text(
                evaluation.get("quality", {}).get("candidate_sha256")
            ).lower(),
            "privacy_scope": "private_avatar_builder_staging_only",
            "state": "dry_run_planned_not_queued",
            "runtime_activation_allowed": False,
            "live_body_replacement_allowed": False,
            "public_export_allowed": False,
            "owner_approval_inferred": False,
        }
        for job_type in ALLOWED_PRIVATE_JOB_TYPES:
            sequence += 1
            job_id = f"private-stage-{sequence:04d}-{candidate_id}-{job_type}"
            job = dict(common)
            job.update(
                {
                    "sequence": sequence,
                    "job_id": job_id,
                    "job_type": job_type,
                    "depends_on": [previous_job_id] if previous_job_id else [],
                }
            )
            jobs.append(job)
            previous_job_id = job_id

    if any(job.get("job_type") not in ALLOWED_PRIVATE_JOB_TYPES for job in jobs):
        raise ValueError("private staging plan contains a non-allowlisted job")
    return {
        "schema_version": 1,
        "status": "dry_run_private_serial_staging_plan_not_queued",
        "unlock_candidate_id": _text(evaluation.get("quality", {}).get("candidate_id")),
        "unlock_candidate_sha256": _text(
            evaluation.get("quality", {}).get("candidate_sha256")
        ).lower(),
        "maximum_concurrent_private_jobs": 1,
        "allowed_private_job_types": list(ALLOWED_PRIVATE_JOB_TYPES),
        "jobs": jobs,
        "skipped": skipped,
        "queue_created": False,
        "automatic_execution_started": False,
        "body_created": False,
        "owner_approval_inferred": False,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "public_export_allowed": False,
        "release_allowed": False,
        "automatic_multi_profile_queue_allowed": False,
        "authoritative_batch_gate": AUTHORITATIVE_BATCH_GATE,
        "authoritative_batch_gate_unchanged": True,
        "truth_note": (
            "This is a dry-run dependency chain, not a queue. A separate private worker "
            "may consume only one allowlisted job at a time after an exact one-body pass; "
            "every produced candidate remains inactive and unapproved."
        ),
    }


__all__ = [
    "ALLOWED_PRIVATE_JOB_TYPES",
    "AUTHORITATIVE_BATCH_GATE",
    "ELIGIBLE_MATURITY_LANES",
    "POLICY_PATH",
    "build_private_staging_dry_run_plan",
    "evaluate_private_staging_unlock",
]
