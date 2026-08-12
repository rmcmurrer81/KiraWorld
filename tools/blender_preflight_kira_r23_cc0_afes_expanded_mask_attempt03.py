#!/usr/bin/env python3
"""R23 read-only preflight Attempt 03 with one world-extent addendum.

This wrapper changes exactly one in-memory config leaf from 0.38 m to 0.40 m,
then calls the sealed base preflight unchanged.  It adds a read-only locality
audit to a successful report.  It never authors geometry, saves a Blend,
renders, exports, changes runtime state, or creates a candidate.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as base  # noqa: E402


DEFAULT_ADDENDUM = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt03_preparation/"
    "KIRA_R23_ATTEMPT03_WORLD_EXTENT_ADDENDUM.json"
)
ALLOWED_OUTPUT = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_03"
)


class Attempt03Error(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--addendum", default=DEFAULT_ADDENDUM.as_posix())
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise Attempt03Error(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt03Error(f"path escaped project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_binding(name: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(binding["path"]))
    if not path.is_file():
        raise Attempt03Error(f"missing {name}: {relative(path)}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise Attempt03Error(
            f"{name} binding mismatch: size={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def leaf_differences(left: Any, right: Any, prefix: str = "") -> list[dict[str, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(set(left).union(right)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                result.append({"path": path, "before": left.get(key), "after": right.get(key)})
            else:
                result.extend(leaf_differences(left[key], right[key], path))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if left == right:
            return []
        return [{"path": prefix, "before": left, "after": right}]
    if left != right:
        return [{"path": prefix, "before": left, "after": right}]
    return []


def run_base_with_selected_mask_capture(
    config: Mapping[str, Any], config_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    captured: dict[str, Any] = {}
    expanded_code = base.expanded_mask_record.__code__

    def local_trace(frame, event, _arg):
        if event == "return" and frame.f_code is expanded_code:
            captured.update(dict(frame.f_locals))
        return local_trace

    def global_trace(frame, _event, _arg):
        if frame.f_code is expanded_code:
            return local_trace
        return None

    previous_trace = sys.gettrace()
    sys.settrace(global_trace)
    try:
        report = base.preflight(config, config_path)
    finally:
        sys.settrace(previous_trace)
    return report, captured


def dominant_group_locality_proof(
    body: bpy.types.Object,
    selected_faces: set[int],
    allowed_chart_faces: set[int],
    report: Mapping[str, Any],
    addendum: Mapping[str, Any],
) -> dict[str, Any]:
    faces = base.faces_of(body)
    selected_vertices = {
        int(vertex)
        for face_index in selected_faces
        for vertex in faces[int(face_index)]
    }
    group_names = {int(group.index): group.name for group in body.vertex_groups}
    dominant_counts: Counter[str] = Counter()
    positive_counts: Counter[str] = Counter()
    maximum_positive_weight: dict[str, float] = {}
    for index in selected_vertices:
        positive = sorted(
            [
                (float(item.weight), group_names[int(item.group)])
                for item in body.data.vertices[index].groups
                if float(item.weight) > 0.0
            ],
            reverse=True,
        )
        if positive:
            dominant_counts[positive[0][1]] += 1
        for weight, name in positive:
            positive_counts[name] += 1
            maximum_positive_weight[name] = max(
                maximum_positive_weight.get(name, 0.0), weight
            )

    policy = addendum["locality_proof"]
    hip_groups = set(policy["forbidden_dominant_hip_groups"])
    upper_groups = set(policy["forbidden_dominant_upper_abdomen_groups"])
    distal_groups = set(policy["forbidden_dominant_distal_leg_groups"])
    tokens = tuple(policy["forbidden_dominant_distal_leg_name_tokens"])
    distal_groups.update(
        name for name in group_names.values() if any(token in name for token in tokens)
    )
    proximal_groups = set(
        policy["permitted_but_must_be_counted_proximal_thigh_transition_groups"]
    )
    forbidden = hip_groups.union(upper_groups).union(distal_groups)
    forbidden_dominant_counts = {
        name: dominant_counts.get(name, 0) for name in sorted(forbidden)
    }
    proximal_dominant_counts = {
        name: dominant_counts.get(name, 0) for name in sorted(proximal_groups)
    }
    proximal_positive_counts = {
        name: {
            "vertex_count": positive_counts.get(name, 0),
            "maximum_weight": maximum_positive_weight.get(name, 0.0),
        }
        for name in sorted(proximal_groups)
    }
    selected = report["expanded_r19_mask"]
    topology = selected["selected_topology"]
    selected_attempt = selected["attempts"][-1]
    checks = {
        "selected_faces_subset_of_bounded_chart": selected_faces.issubset(
            allowed_chart_faces
        ),
        "selected_face_hash_exact": (
            base.canonical_index_sha256(selected_faces)
            == addendum["expected_selection"]["face_index_sha256"]
        ),
        "one_component": topology["component_count"] == 1,
        "one_boundary_cycle": topology["boundary_cycle_count"] == 1,
        "euler_disk": topology["euler_characteristic"] == 1
        and topology["is_one_disk"] is True,
        "no_dominant_hip_escape": not any(
            dominant_counts.get(name, 0) for name in hip_groups
        ),
        "no_dominant_upper_abdomen_escape": not any(
            dominant_counts.get(name, 0) for name in upper_groups
        ),
        "no_dominant_distal_leg_escape": not any(
            dominant_counts.get(name, 0) for name in distal_groups
        ),
        "no_unexpected_dominant_group": not selected_attempt[
            "unexpected_dominant_rig_groups"
        ],
    }
    return {
        "definition": policy,
        "selected_face_count": len(selected_faces),
        "selected_vertex_count": len(selected_vertices),
        "selected_face_index_sha256": base.canonical_index_sha256(selected_faces),
        "allowed_chart_face_count": len(allowed_chart_faces),
        "allowed_chart_face_index_sha256": base.canonical_index_sha256(
            allowed_chart_faces
        ),
        "selected_bounds_world_m": selected_attempt["bounds_world_m"],
        "selected_world_extent_m": selected_attempt["world_extent_m"],
        "selected_lateral_half_extent_m": selected_attempt[
            "lateral_half_extent_m"
        ],
        "all_dominant_group_vertex_counts": dict(sorted(dominant_counts.items())),
        "forbidden_dominant_group_vertex_counts": forbidden_dominant_counts,
        "permitted_proximal_thigh_transition_dominant_vertex_counts": (
            proximal_dominant_counts
        ),
        "permitted_proximal_thigh_transition_positive_influence": (
            proximal_positive_counts
        ),
        "checks": checks,
        "passed": all(checks.values()),
    }


def output_directory(addendum: Mapping[str, Any]) -> Path:
    directory = project_path(str(addendum["output"]["directory"]))
    if directory != project_path(ALLOWED_OUTPUT):
        raise Attempt03Error("Attempt 03 output path is not exact")
    if directory.exists():
        raise FileExistsError(
            f"append-only Attempt 03 output already exists: {relative(directory)}"
        )
    return directory


def main() -> int:
    args = arguments()
    addendum_path = project_path(args.addendum)
    addendum = read_json(addendum_path)
    if addendum.get("schema") != (
        "kira.avatar.r23_cc0_afes_preflight_attempt03_world_extent_addendum.v1"
    ):
        raise Attempt03Error("wrong Attempt 03 addendum schema")

    verified_bindings = {
        name: verify_binding(name, addendum[name])
        for name in (
            "base_worker",
            "base_config",
            "source_blend",
            "qualified_cc0_foundation",
        )
    }
    verified_bindings["preserved_attempts"] = [
        verify_binding(row["attempt_id"], row)
        for row in addendum["preserved_attempts"]
    ]
    if Path(base.__file__).resolve() != project_path(addendum["base_worker"]["path"]):
        raise Attempt03Error("imported base worker path is not exact")

    base_config_path = project_path(addendum["base_config"]["path"])
    sealed_config = read_json(base_config_path)
    config = deepcopy(sealed_config)
    contract = addendum["contract_addendum"]
    old_value = config["alignment_and_mask"][
        "maximum_expanded_mask_world_extent_m"
    ]
    if old_value != contract["old_value_m"]:
        raise Attempt03Error("sealed old world-extent value drifted")
    config["alignment_and_mask"]["maximum_expanded_mask_world_extent_m"] = (
        contract["new_value_m"]
    )
    differences = leaf_differences(sealed_config, config)
    expected_difference = [
        {
            "path": contract["exact_config_leaf"],
            "before": contract["old_value_m"],
            "after": contract["new_value_m"],
        }
    ]
    if differences != expected_difference:
        raise Attempt03Error(f"Attempt 03 config diff is not exact: {differences}")

    directory = output_directory(addendum)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        report, captured = run_base_with_selected_mask_capture(
            config, base_config_path
        )
        selected_faces = {int(value) for value in captured.get("chosen", set())}
        allowed_faces = {int(value) for value in captured.get("allowed", set())}
        if not selected_faces or not allowed_faces:
            raise Attempt03Error("selected mask trace capture was incomplete")
        selected = report["expanded_r19_mask"]
        expected = addendum["expected_selection"]
        selection_checks = {
            "smallest_passing_ring_exact": (
                selected["selected_exterior_rings"]
                == expected["smallest_passing_exterior_rings"]
            ),
            "face_count_exact": (
                selected["selected_topology"]["face_count"]
                == expected["face_count"]
            ),
            "face_hash_exact": (
                selected["selected_face_index_sha256"]
                == expected["face_index_sha256"]
            ),
            "outer_seam_count_exact": (
                selected["selected_topology"]["boundary_cycle_lengths"] == [
                    expected["ordered_outer_seam_vertices"]
                ]
            ),
            "world_extent_matches_attempt02": abs(
                selected["attempts"][-1]["world_extent_m"]
                - expected["world_extent_m"]
            )
            <= 1.0e-12,
            "world_extent_within_addendum": (
                selected["attempts"][-1]["world_extent_m"]
                <= expected["maximum_allowed_world_extent_m"]
            ),
            "all_selection_gates_pass": all(
                selected["attempts"][-1]["gates"].values()
            ),
        }
        if not all(selection_checks.values()):
            raise Attempt03Error(
                f"deterministic selected mask contract failed: {selection_checks}"
            )
        body = bpy.data.objects[config["r19_contract"]["body_object"]]
        locality = dominant_group_locality_proof(
            body, selected_faces, allowed_faces, report, addendum
        )
        if not locality["passed"]:
            raise Attempt03Error(
                f"selected mask locality proof failed: {locality['checks']}"
            )
        report["artifact_kind"] = (
            "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_ATTEMPT03"
        )
        report["attempt_id"] = "attempt_03"
        report["contract_addendum"] = {
            "path": relative(addendum_path),
            "sha256": sha256_file(addendum_path),
            "exact_leaf_differences": differences,
            "all_other_config_leaves_unchanged": True,
            "base_config_sha256": sha256_file(base_config_path),
        }
        report["attempt_03_wrapper"] = {
            "path": relative(Path(__file__)),
            "sha256": sha256_file(Path(__file__)),
            "verified_bindings": verified_bindings,
        }
        report["deterministic_selection_checks"] = selection_checks
        report["explicit_locality_escape_proof"] = locality
        report["status"] = "PREFLIGHT_PASS_AUTHORING_NOT_STARTED"
        filename = str(addendum["output"]["pass_file"])
        result = 0
    except Exception as exc:
        source_path = project_path(addendum["source_blend"]["path"])
        report = {
            "schema_version": 1,
            "artifact_kind": (
                "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_"
                "ATTEMPT03_FAILURE"
            ),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PREFLIGHT_NO_GO_NO_CANDIDATE",
            "attempt_id": "attempt_03",
            "contract_addendum": {
                "path": relative(addendum_path),
                "sha256": sha256_file(addendum_path),
                "exact_leaf_differences": differences,
                "all_other_config_leaves_unchanged": differences
                == expected_difference,
            },
            "verified_bindings": verified_bindings,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "source_blend": {
                "path": relative(source_path),
                "sha256_after": sha256_file(source_path),
                "expected_sha256": addendum["source_blend"]["sha256"],
            },
            "operations": {
                "mesh_mutation_performed": False,
                "candidate_created": False,
                "blend_written": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "reference_only_asset_loaded": False,
            },
        }
        filename = str(addendum["output"]["failure_file"])
        result = 2

    evidence_path = directory / filename
    if evidence_path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {relative(evidence_path)}")
    evidence_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "evidence": relative(evidence_path),
                "sha256": sha256_file(evidence_path),
                "candidate_created": False,
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())

