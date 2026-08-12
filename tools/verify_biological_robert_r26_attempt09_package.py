#!/usr/bin/env python3
"""Independently verify the bounded Robert R26 Attempt 09 package.

This verifier has no Blender dependency and never edits the candidate.  It
checks the append-only package, exact implementation bindings, all-20 nail
evidence, private/inactive scope, bald-runtime boundary, and the one-candidate
limit recorded by the sealed Attempt 09 run request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_REQUEST = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_bounded_run"
    / "attempt_09"
    / "authoring_run"
    / "RUN_REQUEST.json"
)
CANDIDATE_ID = "BIOLOGICAL_ROBERT_R26_BALD_OWNER_REVIEW"
SUCCESS_STATUS = (
    "PRIVATE_INACTIVE_COMPLETE_OWNER_REVIEW_CANDIDATE_"
    "AWAITING_ROBERT_VISUAL_DECISION"
)
EXPECTED_NAIL_IDS = tuple(
    f"{kind}_{digit}_{side}"
    for side in ("L", "R")
    for kind in ("fingernail", "toenail")
    for digit in range(1, 6)
)


class Attempt09VerificationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(raw: str | Path) -> Path:
    path = Path(raw)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt09VerificationError(f"path escapes project: {resolved}") from exc
    return resolved


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Attempt09VerificationError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise Attempt09VerificationError(f"JSON root is not an object: {path}")
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Attempt09VerificationError(message)


def verify_bound_file(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = project_path(str(binding.get("path", "")))
    require(path.is_file(), f"bound {label} is absent: {path}")
    actual_hash = sha256_file(path)
    actual_bytes = path.stat().st_size
    require(
        actual_hash == str(binding.get("sha256", "")).lower(),
        f"bound {label} hash differs",
    )
    require(actual_bytes == int(binding.get("bytes", -1)), f"bound {label} size differs")
    return {
        "path": project_relative(path),
        "sha256": actual_hash,
        "bytes": actual_bytes,
    }


def verify_manifest(candidate: Path) -> dict[str, Any]:
    path = candidate / "PACKAGE_MANIFEST.json"
    require(path.is_file(), "candidate PACKAGE_MANIFEST.json is absent")
    payload = read_json(path)
    require(
        payload.get("schema") == "kira.avatar.private_owner_review_package_manifest.v1",
        "candidate manifest schema differs",
    )
    require(payload.get("candidate_id") == CANDIDATE_ID, "manifest candidate ID differs")
    require(payload.get("append_only") is True, "manifest is not append-only")
    require(payload.get("private") is True, "manifest is not private")
    require(payload.get("inactive") is True, "manifest is not inactive")
    require(payload.get("owner_approved") is False, "manifest claims owner approval")
    rows = payload.get("files")
    require(isinstance(rows, list), "manifest files inventory is absent")
    listed = {str(row["path"]): row for row in rows}
    require(len(listed) == len(rows), "manifest contains duplicate paths")
    actual = {
        item.relative_to(candidate).as_posix()
        for item in candidate.rglob("*")
        if item.is_file() and item != path
    }
    require(set(listed) == actual, "manifest inventory differs from candidate filesystem")
    for relative, row in sorted(listed.items()):
        item = candidate / Path(relative)
        require(item.stat().st_size == int(row["bytes"]), f"manifest size differs: {relative}")
        require(
            sha256_file(item) == str(row["sha256"]).lower(),
            f"manifest hash differs: {relative}",
        )
    require(
        int(payload.get("file_count_excluding_manifest", -1)) == len(rows),
        "manifest file count differs",
    )
    for required_name in (
        "BIOLOGICAL_ROBERT_R26_BALD_OWNER_REVIEW.blend",
        "BUILD_EVIDENCE.json",
        "OWNER_REVIEW_README.md",
        "ROLLBACK.md",
        "CHECKPOINT.md",
    ):
        require(required_name in listed, f"required candidate artifact absent: {required_name}")
    return {
        "path": project_relative(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "file_count_excluding_manifest": len(rows),
        "inventory_exact": True,
        "all_hashes_and_sizes_exact": True,
    }


def verify_nails(report: Mapping[str, Any]) -> dict[str, Any]:
    require(
        report.get("method") == "avatar_weight_constrained_evaluated_nail_projection_v1",
        "candidate did not use the weight-constrained nail method",
    )
    rows = report.get("records")
    require(isinstance(rows, list) and len(rows) == 20, "nail record count is not twenty")
    actual_ids = tuple(str(row.get("nail_id", "")) for row in rows)
    require(actual_ids == EXPECTED_NAIL_IDS, "nail inventory or declared order differs")
    require(len(set(actual_ids)) == 20, "nail inventory contains duplicate IDs")
    first_hit_rejections = 0
    for row in rows:
        nail_id = str(row["nail_id"])
        binding = row.get("footprint_binding", {})
        selection = row.get("selection", {})
        shell = row.get("final_evaluated_complete_shell_gate", {})
        attachment = row.get("attachment", {})
        require(binding.get("passed") is True, f"strict footprint failed: {nail_id}")
        require(selection.get("passed") is True, f"surface selection failed: {nail_id}")
        require(
            selection.get("every_sample_matches_declared_digit") is True,
            f"declared-digit footprint drifted: {nail_id}",
        )
        require(
            selection.get("every_sample_uses_one_connected_region") is True,
            f"connected-region footprint drifted: {nail_id}",
        )
        require(shell.get("passed") is True, f"complete evaluated shell failed: {nail_id}")
        shell_gates = shell.get("gates")
        require(
            isinstance(shell_gates, dict) and shell_gates and all(shell_gates.values()),
            f"evaluated shell subgate failed: {nail_id}",
        )
        require(
            int(shell.get("exact_genuine_triangle_pair_count", -1)) == 0,
            f"rest shell penetrates the body: {nail_id}",
        )
        require(row.get("automatic_bone_remap_performed") is False, f"bone remap occurred: {nail_id}")
        require(
            row.get("declared_terminal_bone") == row.get("bone") == attachment.get("bone"),
            f"terminal bone differs: {nail_id}",
        )
        for gate in (
            "parent_is_exact_armature",
            "armature_modifier_targets_exact_rig",
            "every_vertex_has_unit_terminal_bone_weight",
        ):
            require(attachment.get(gate) is True, f"attachment gate failed: {nail_id}: {gate}")
        first_hit_rejections += int(
            selection.get("neighboring_or_occluding_first_hit_rejected_count", 0)
        )
    gates = report.get("gates")
    require(isinstance(gates, dict) and gates and all(gates.values()), "all-20 nail aggregate gate failed")
    return {
        "method": report["method"],
        "record_count": len(rows),
        "inventory_exact": True,
        "strict_declared_digit_footprints_all_20": True,
        "complete_evaluated_shells_all_20": True,
        "zero_rest_shell_penetrations_all_20": True,
        "exact_terminal_bone_attachments_all_20": True,
        "automatic_bone_remap_performed": False,
        "neighboring_or_occluding_first_hit_rejected_count": first_hit_rejections,
    }


def verify_package(run_request_path: Path) -> dict[str, Any]:
    request = read_json(run_request_path)
    require(
        request.get("schema") == "kira.avatar.biological_robert_r26_bounded_run_request.v2",
        "Attempt 09 run-request schema differs",
    )
    require(request.get("candidate_id") == CANDIDATE_ID, "run-request candidate ID differs")
    require(
        request.get("status") == "PREPARED_NOT_RUN_EXACTLY_ONE_ATTEMPT_09_AUTHORING_INVOCATION",
        "run request is not the sealed pre-run Attempt 09 request",
    )
    maximum = int(request.get("maximum_candidate_count", 0))
    require(maximum == 1, "run request does not enforce one candidate")
    bindings = request.get("bindings")
    require(isinstance(bindings, dict), "run-request bindings are absent")
    verified_bindings = {
        name: verify_bound_file(bindings[name], name)
        for name in ("worker", "config", "release", "nail_adapter", "nail_contract")
    }
    candidate = project_path(str(request.get("candidate_output_path", "")))
    require(candidate.is_dir(), f"candidate directory is absent: {candidate}")
    candidate_matches = sorted(
        item
        for item in candidate.parent.iterdir()
        if item.is_dir() and item.name.startswith(candidate.name)
    )
    require(
        len(candidate_matches) <= maximum and candidate_matches == [candidate],
        "candidate count exceeds the exact one-candidate boundary",
    )
    manifest = verify_manifest(candidate)
    evidence_path = candidate / "BUILD_EVIDENCE.json"
    evidence = read_json(evidence_path)
    require(evidence.get("candidate_id") == CANDIDATE_ID, "evidence candidate ID differs")
    require(evidence.get("status") == SUCCESS_STATUS, "candidate success status differs")
    scope = evidence.get("scope", {})
    for key, value in {
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_exported": False,
        "activated": False,
        "clothing_included": False,
        "scalp_hair_dependency_present": False,
        "confirmed_adult": True,
        "body_class": "adult_male",
        "owner_approved": False,
    }.items():
        require(scope.get(key) == value, f"candidate scope differs: {key}")
    implementation = evidence.get("implementation_binding", {})
    for key in ("worker", "config"):
        require(
            implementation.get(key) == verified_bindings[key],
            f"evidence implementation binding differs: {key}",
        )
    release_record = evidence.get("durable_post_kira_release", {})
    require(
        release_record.get("path") == verified_bindings["release"]["path"]
        and release_record.get("sha256") == verified_bindings["release"]["sha256"],
        "evidence release binding differs",
    )
    require(evidence.get("protected_inputs_unchanged") is True, "protected inputs changed")
    nails = verify_nails(evidence.get("natural_nails", {}))
    mandatory = evidence.get("mandatory_exact_audits")
    require(isinstance(mandatory, dict) and mandatory and all(mandatory.values()), "mandatory audit failed")
    for key in (
        "all_twenty_nails_strict_declared_digit_footprint",
        "all_twenty_nails_complete_evaluated_shell",
        "all_twenty_nails_exact_terminal_bone_attachment",
        "zero_body_nail_cross_intersections_in_every_pose",
        "scalp_hair_object_dependency_absent",
        "private_inactive_unassigned_unpublished_flags",
    ):
        require(mandatory.get(key) is True, f"required mandatory audit absent or false: {key}")
    pose_reports = evidence.get("pose_geometry_audits")
    require(isinstance(pose_reports, dict) and pose_reports, "pose audits are absent")
    for pose_name, row in pose_reports.items():
        require(row.get("passed") is True, f"pose audit failed: {pose_name}")
        exact = row.get("exact_body_nail_intersections", {})
        require(
            int(exact.get("total_exact_genuine_triangle_pair_count", -1)) == 0,
            f"pose body/nail intersection failed: {pose_name}",
        )
    bald = evidence.get("bald_low_resource_contract", {})
    require(int(bald.get("scalp_hair_runtime_dependency_count", -1)) == 0, "scalp hair dependency exists")
    for key in (
        "forbidden_scalp_hair_objects",
        "particle_hair_settings",
        "hair_curve_data",
        "forbidden_scalp_hair_materials",
        "forbidden_scalp_hair_images",
    ):
        require(bald.get(key) == [], f"bald-runtime inventory differs: {key}")
    require(evidence.get("object_scope", {}).get("passed") is True, "object scope audit failed")
    require(
        evidence.get("private_review_renders", {}).get("required_inventory_exact") is True,
        "private review render inventory differs",
    )
    blend_path = candidate / "BIOLOGICAL_ROBERT_R26_BALD_OWNER_REVIEW.blend"
    blend_record = evidence.get("artifacts", {}).get("blend", {})
    require(blend_record.get("package_relative_path") == blend_path.name, "blend path differs")
    require(blend_record.get("sha256") == sha256_file(blend_path), "blend hash differs")
    require(int(blend_record.get("bytes", -1)) == blend_path.stat().st_size, "blend size differs")
    return {
        "schema": "kira.avatar.biological_robert_r26_attempt09_independent_verification.v1",
        "status": "PASSED_PRIVATE_INACTIVE_SINGLE_CANDIDATE_AWAITING_OWNER_REVIEW",
        "verified_utc": utc_now(),
        "run_request": {
            "path": project_relative(run_request_path),
            "sha256": sha256_file(run_request_path),
            "bytes": run_request_path.stat().st_size,
        },
        "candidate": {
            "path": project_relative(candidate),
            "candidate_count": len(candidate_matches),
            "maximum_candidate_count": maximum,
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_eligible": False,
            "owner_approved": False,
            "scalp_hair_dependency_present": False,
        },
        "bindings": verified_bindings,
        "manifest": manifest,
        "nails": nails,
        "pose_audit_count": len(pose_reports),
        "all_pose_geometry_gates_passed": True,
        "owner_visual_acceptance_claimed": False,
    }


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-request", default=str(DEFAULT_RUN_REQUEST))
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    run_request = project_path(args.run_request)
    require(run_request.is_file(), f"run request is absent: {run_request}")
    result = verify_package(run_request)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = project_path(args.output)
        require(not output.exists(), f"append-only verification output exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
