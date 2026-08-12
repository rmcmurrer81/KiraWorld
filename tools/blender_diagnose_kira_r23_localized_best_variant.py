#!/usr/bin/env python3
"""No-save exact localization of the best R23 Attempt08 simulation variant."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DiagnosticError(RuntimeError):
    pass


def args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--execute-readonly-diagnostic", action="store_true")
    return parser.parse_args(raw)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise DiagnosticError(f"JSON root is not an object: {path}")
    return value


def binding(record: Mapping[str, Any], label: str) -> Path:
    path = project_path(record["path"])
    if not path.is_file() or path.is_symlink():
        raise DiagnosticError(f"{label} is absent or linked")
    if path.stat().st_size != int(record["bytes"]) or sha256_file(path) != record["sha256"]:
        raise DiagnosticError(f"{label} drifted")
    return path


def section(ordinal: int) -> str:
    if ordinal < 245:
        return "outer_91_to_154_zipper"
    if ordinal < 553:
        return "first_154_ring_bridge"
    if ordinal < 861:
        return "second_154_ring_bridge"
    return "mapped_cc0_donor_disk"


def region(local_index: int) -> str:
    if local_index < 91:
        return "target_seam"
    if local_index < 245:
        return "first_collar_ring"
    if local_index < 399:
        return "second_collar_ring"
    return "mapped_cc0_donor_disk"


def face_edges(face: Sequence[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((int(face[index]), int(face[(index + 1) % len(face)]))))
        for index in range(len(face))
    }


def weight_map(body: Any, vertex: int) -> dict[str, float]:
    return {
        body.vertex_groups[int(value.group)].name: float(value.weight)
        for value in body.data.vertices[int(vertex)].groups
        if float(value.weight) > 0.0
    }


def run(config_path: Path, execute: bool) -> int:
    if not execute:
        raise DiagnosticError("explicit --execute-readonly-diagnostic is required")
    config = read_json(config_path)
    paths = {name: binding(value, name) for name, value in config["bindings"].items()}
    if paths["worker"].resolve() != Path(__file__).resolve():
        raise DiagnosticError("configured worker differs from executing worker")
    out_dir = project_path(config["output"]["directory"])
    out_path = out_dir / config["output"]["filename"]
    if out_dir.exists():
        raise DiagnosticError("append-only diagnostic output already exists")
    source = paths["r19_source"]
    candidate = paths["attempt05_candidate"]
    before = {
        "source": {"bytes": source.stat().st_size, "sha256": sha256_file(source)},
        "candidate": {"bytes": candidate.stat().st_size, "sha256": sha256_file(candidate)},
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        import bmesh
        import bpy
        from tools import blender_author_kira_r23_cc0_afes_attempt01 as author
        from tools import blender_author_kira_r23_cc0_afes_attempt04_wrapper as attempt04
        from tools import blender_exact_mesh_intersections as exact_module
        from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight_module
        from tools import blender_simulate_kira_r23_localized_patch_repair as simulation
        from tools import blender_verify_kira_r23_postsave_fresh_reopen as verifier
        from tools import kira_r23_blender51_action_serializer as actions_module
        from tools import kira_r23_cc0_afes_preflight_core as topology
        from tools import kira_r23_localized_patch_repair_core as repair_core

        author_config = read_json(paths["author_config"])
        verification = read_json(paths["verification_config"])
        overlay = read_json(paths["attempt05_repair_overlay"])
        design = simulation.capture_design(
            author_config,
            verification,
            overlay,
            bpy,
            bmesh,
            author,
            attempt04,
            verifier,
            preflight_module,
            actions_module,
            exact_module,
            topology,
        )
        uv_fields, uv_evidence = simulation.build_uv_fields(design, repair_core)
        new_weights, weight_evidence = simulation.build_weight_field(design, repair_core)
        variant = config["variant"]
        positions, position_evidence = simulation.variant_positions(
            design,
            float(variant["outer_scale"]),
            float(variant["donor_scale"]),
            float(variant["clearance_m"]),
            repair_core,
        )
        donor = design["donor"]
        bpy.data.objects.remove(donor, do_unlink=True)
        body = design["body"]
        rig = design["rig"]
        source_mesh = body.data
        body.data = source_mesh.copy()
        attempt04.bind_attempt04_runtime(overlay)
        attempt04.RUNTIME["donor_memberships"] = design["donor_memberships"]
        prepared = dict(design["prepared"])
        prepared["positions_body_local"] = positions
        prepared["uv_fields"] = deepcopy(uv_fields)
        prepared["new_weights"] = deepcopy(new_weights)
        applied = attempt04.attempt04_apply_patch(
            body,
            rig,
            design["selected_faces"],
            design["target_cycle"],
            prepared,
            author_config,
        )
        patch_faces = {int(value) for value in applied["patch_face_indices"]}
        stable = attempt04.RUNTIME["final_stable_vertex_map"]["token_to_global"]
        local_to_global = {
            index: int(applied["target_seam_global_indices"][index])
            for index in range(len(design["target_cycle"]))
        }
        for index in range(len(design["target_cycle"]), len(positions)):
            local_to_global[index] = int(stable[attempt04.stable_patch_vertex(index)])
        global_to_local = {value: key for key, value in local_to_global.items()}
        canonical_ordinals = {
            tuple(sorted(local_to_global[int(value)] for value in face)): ordinal
            for ordinal, face in enumerate(prepared["faces"])
        }
        face_to_ordinal = {}
        for face_index in patch_faces:
            key = tuple(sorted(map(int, body.data.polygons[face_index].vertices)))
            if key not in canonical_ordinals:
                raise DiagnosticError("saved patch face lacks a creation ordinal")
            face_to_ordinal[face_index] = canonical_ordinals[key]
        if len(face_to_ordinal) != len(prepared["faces"]):
            raise DiagnosticError("creation-face mapping is incomplete")

        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
        exact = verifier.exact_intersections(body, bpy, bmesh, exact_module)
        exact_pairs = []
        section_counts: Counter[str] = Counter()
        for pair in exact["genuine_index_pairs"]:
            if not any(int(value) in patch_faces for value in pair):
                continue
            labels = []
            ordinals = []
            local_vertices = []
            for face_index in map(int, pair):
                if face_index in patch_faces:
                    ordinal = face_to_ordinal[face_index]
                    labels.append(section(ordinal))
                    ordinals.append(ordinal)
                    local_vertices.append(
                        sorted(global_to_local[int(value)] for value in body.data.polygons[face_index].vertices)
                    )
                else:
                    labels.append("retained_r19")
                    ordinals.append(None)
                    local_vertices.append(None)
            key = " + ".join(sorted(labels))
            section_counts[key] += 1
            exact_pairs.append(
                {
                    "faces": list(map(int, pair)),
                    "sections": labels,
                    "creation_ordinals": ordinals,
                    "local_vertices": local_vertices,
                }
            )

        faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
        edge_faces = topology.edge_face_map(faces)
        seam_edges = topology.boundary_edges_for_region(faces, patch_faces)
        seam_rows = []
        for edge in sorted(seam_edges):
            owners = edge_faces[edge]
            patch_owner = next(value for value in owners if value in patch_faces)
            retained_owner = next(value for value in owners if value not in patch_faces)
            dot = float(
                body.data.polygons[patch_owner].normal.dot(
                    body.data.polygons[retained_owner].normal
                )
            )
            if dot < 0.7:
                ordinal = face_to_ordinal[patch_owner]
                seam_rows.append(
                    {
                        "edge_global": list(edge),
                        "edge_local": [global_to_local[value] for value in edge],
                        "dot": dot,
                        "patch_face": patch_owner,
                        "patch_creation_ordinal": ordinal,
                        "patch_section": section(ordinal),
                        "patch_face_local_vertices": [
                            global_to_local[int(value)]
                            for value in body.data.polygons[patch_owner].vertices
                        ],
                        "retained_face": retained_owner,
                    }
                )

        patch_edges = {
            edge for face_index in patch_faces for edge in topology.face_edges(faces[face_index])
        }
        new_edges = patch_edges.difference(seam_edges)
        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
        neutral_points = verifier.evaluated_points(body, bpy)
        neutral_lengths = verifier.edge_lengths(neutral_points, new_edges)
        pose_rows = {}
        for pose in verification["poses"]:
            verifier.apply_pose(rig, pose["rotations_degrees"])
            bpy.context.view_layer.update()
            points = verifier.evaluated_points(body, bpy)
            current = verifier.edge_lengths(points, new_edges)
            ratios = sorted(
                (
                    current[edge] / neutral_lengths[edge],
                    edge,
                )
                for edge in new_edges
                if neutral_lengths[edge] > 1.0e-12
            )
            top = []
            for ratio, edge in reversed(ratios[-25:]):
                local = [global_to_local[value] for value in edge]
                top.append(
                    {
                        "ratio": ratio,
                        "edge_global": list(edge),
                        "edge_local": local,
                        "regions": [region(value) for value in local],
                        "neutral_length_m": neutral_lengths[edge],
                        "posed_length_m": current[edge],
                        "first_weights": weight_map(body, edge[0]),
                        "second_weights": weight_map(body, edge[1]),
                    }
                )
            pose_rows[pose["id"]] = {
                "maximum_new_patch_edge_stretch_ratio": ratios[-1][0] if ratios else 1.0,
                "top_25": top,
            }
        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
        after = {
            "source": {"bytes": source.stat().st_size, "sha256": sha256_file(source)},
            "candidate": {"bytes": candidate.stat().st_size, "sha256": sha256_file(candidate)},
        }
        if before != after:
            raise DiagnosticError("source or Attempt05 candidate changed")
        result = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_LOCALIZED_BEST_VARIANT_EXACT_DIAGNOSTIC",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "READ_ONLY_EXACT_LOCALIZATION_NOT_ACCEPTANCE",
            "variant": variant,
            "position_evidence": position_evidence,
            "uv_evidence": uv_evidence,
            "weight_evidence": weight_evidence,
            "mapping": {
                "local_to_global_sha256": canonical_sha256(sorted(local_to_global.items())),
                "face_to_ordinal_sha256": canonical_sha256(sorted(face_to_ordinal.items())),
                "vertex_count": len(local_to_global),
                "face_count": len(face_to_ordinal),
            },
            "neutral": {
                "whole_genuine_pair_count": len(exact["genuine_index_pairs"]),
                "patch_involving_pair_count": len(exact_pairs),
                "section_pair_counts": dict(sorted(section_counts.items())),
                "patch_involving_pairs": exact_pairs,
                "seam_normal_failure_count_at_0_7": len(seam_rows),
                "seam_normal_failures": seam_rows,
            },
            "new_patch_edge_pose_stretch": pose_rows,
            "immutability": {"before": before, "after": after, "unchanged": before == after},
            "operations": {
                "blend_saved": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_or_person_state_mutated": False
            },
            "truth_boundary": "External engineering localization only; not anatomy, movement, function, sensation, or owner acceptance."
        }
        with out_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps({"status": result["status"], "output": relative(out_path)}))
        return 0
    except Exception:
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_LOCALIZED_BEST_VARIANT_DIAGNOSTIC_FAILURE",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "exception_type": type(sys.exc_info()[1]).__name__,
            "exception": str(sys.exc_info()[1]),
            "traceback": traceback.format_exc(),
            "operations": {"blend_saved": False, "render_performed": False, "export_performed": False}
        }
        with (out_dir / "FAILURE_EVIDENCE.json").open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(failure, handle, indent=2, sort_keys=True)
            handle.write("\n")
        raise


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def main() -> int:
    parsed = args()
    return run(project_path(parsed.config), bool(parsed.execute_readonly_diagnostic))


if __name__ == "__main__":
    raise SystemExit(main())
