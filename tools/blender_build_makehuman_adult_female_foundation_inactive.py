"""Build an inactive MakeHuman-derived adult-female authoring workspace.

This is a thin wrapper around the generic continuous-surface method.  It uses
only the bundled CC0 MakeHuman hm08 ``body`` group, the enrolled official
female macro targets, and bundled default skin weights.  The male
``helper-genital`` group is never parsed.  No anatomy reference mesh is read.

The wrapper has no render, GLB export, runtime selection, roster assignment,
clothing, or publication path.  It refuses to run without an explicit
inactive-authoring acknowledgement and only saves a new, non-existing Blend
file beneath the dedicated inactive workspace directory.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_foundation_qualification import (
    REGISTRY_PATH,
    evaluate_adult_foundation_qualification,
)
from Core.avatar_adult_female_surface_authoring import (
    frame_from_mapping,
    parameters_from_mapping,
)
from tools.blender_author_adult_female_external_surface import (
    author_continuous_adult_female_surface,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


FOUNDATION_ID = "makehuman_hm08_female_macro_source"
INACTIVE_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "workspaces"
    / "inactive_adult_female_foundations"
)
MAKEHUMAN_DATA = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "makehuman_official"
    / "makehuman"
    / "data"
)
WEIGHTS_PATH = MAKEHUMAN_DATA / "rigs" / "default_weights.mhw"
SAFE_ID = re.compile(r"^[a-z][a-z0-9_]{2,95}$")
CANDIDATE_AUTHOR_ID = "avatar_foundation_authoring_pipeline_v1"
MANDATORY_DOWNSTREAM_POSE_GATE = (
    "Before any identity-specific Kira candidate may use this foundation, "
    "attach its intended armature and independently pass a pose-space "
    "pelvic-patch deformation audit; this generic foundation contains "
    "normalized weights but no armature and proves no posed behavior."
)


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument(
        "--acknowledge-inactive-authoring",
        action="store_true",
        help=(
            "Required acknowledgement that the result is an inactive, "
            "unqualified authoring workspace."
        ),
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(raw: Any, *, suffix: str | None = None) -> Path:
    value = str(raw or "").strip()
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError(f"unsafe project-relative path: {value!r}")
    path = (PROJECT_ROOT / candidate).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"path escaped project root: {value!r}") from exc
    if suffix is not None and path.suffix.lower() != suffix:
        raise RuntimeError(f"path must end in {suffix}: {value!r}")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    allowed = {
        "schema_version",
        "foundation_id",
        "candidate_id",
        "target_height_m",
        "frame",
        "parameters",
    }
    unexpected = sorted(set(payload).difference(allowed))
    if unexpected:
        raise RuntimeError(f"unknown config field(s): {', '.join(unexpected)}")
    if payload.get("schema_version") != 1:
        raise RuntimeError("config schema_version must be 1")
    if payload.get("foundation_id") != FOUNDATION_ID:
        raise RuntimeError(f"config foundation_id must be {FOUNDATION_ID}")
    candidate_id = str(payload.get("candidate_id") or "").strip()
    if not SAFE_ID.fullmatch(candidate_id):
        raise RuntimeError("candidate_id must be a generic lower_snake_case id")
    target_height = payload.get("target_height_m")
    if isinstance(target_height, bool):
        raise RuntimeError("target_height_m must be numeric")
    try:
        target_height = float(target_height)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("target_height_m must be numeric") from exc
    if not 1.35 <= target_height <= 2.05:
        raise RuntimeError("target_height_m must remain within [1.35, 2.05]")
    frame_from_mapping(payload.get("frame"))
    parameters_from_mapping(payload.get("parameters"))
    return payload


def _binding_path(binding: Mapping[str, Any], label: str) -> Path:
    if not isinstance(binding, Mapping):
        raise RuntimeError(f"{label} binding missing")
    path = _project_file(binding.get("path"))
    expected = str(binding.get("sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError(f"{label} sha256 invalid")
    if not path.is_file():
        raise RuntimeError(f"{label} file missing: {path}")
    if _sha256(path) != expected:
        raise RuntimeError(f"{label} sha256 mismatch: {path}")
    return path


def _foundation_source_bindings() -> tuple[
    Path,
    list[tuple[Path, float]],
    dict[str, Any],
]:
    registry = _read_json(PROJECT_ROOT / REGISTRY_PATH)
    matches = [
        entry
        for entry in registry.get("entries", [])
        if isinstance(entry, Mapping)
        and entry.get("foundation_id") == FOUNDATION_ID
    ]
    if len(matches) != 1:
        raise RuntimeError("MakeHuman female foundation registry entry not unique")
    entry = matches[0]
    if entry.get("artifact_kind") != "parametric_source_set":
        raise RuntimeError("MakeHuman foundation must be a parametric source set")
    base = _binding_path(entry.get("source_artifact"), "MakeHuman base")
    configurations = entry.get("source_configuration_artifacts")
    if not isinstance(configurations, list) or len(configurations) < 2:
        raise RuntimeError("MakeHuman female macro bindings are incomplete")
    targets: list[tuple[Path, float]] = []
    for index, binding in enumerate(configurations):
        path = _binding_path(binding, f"MakeHuman female macro {index}")
        raw_weight = binding.get("weight")
        if isinstance(raw_weight, bool):
            raise RuntimeError(f"MakeHuman female macro {index} weight invalid")
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"MakeHuman female macro {index} weight missing"
            ) from exc
        if not -1.0 <= weight <= 1.0 or abs(weight) <= 1.0e-8:
            raise RuntimeError(
                f"MakeHuman female macro {index} weight outside bounded range"
            )
        targets.append((path, weight))
    if any(path.suffix.lower() != ".target" for path, _weight in targets):
        raise RuntimeError("MakeHuman configuration contains a non-target file")
    return base, targets, dict(entry)


def _parse_body_group(path: Path) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append(Vector((float(x), float(y), float(z))))
            elif line.startswith("g "):
                group = line[2:].strip()
            elif group == "body" and line.startswith("f "):
                indices = []
                for token in line.split()[1:]:
                    value = int(token.split("/", 1)[0])
                    indices.append(value - 1 if value > 0 else len(vertices) + value)
                if len(indices) >= 3:
                    faces.append(tuple(indices))
    if not vertices or not faces:
        raise RuntimeError("MakeHuman base OBJ body group is empty")
    return vertices, faces


def _apply_target(vertices: list[Vector], path: Path, weight: float) -> int:
    changed = 0
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 4:
                continue
            index = int(fields[0])
            if not 0 <= index < len(vertices):
                raise RuntimeError(f"target vertex outside base mesh: {index}")
            vertices[index] += Vector(
                tuple(float(value) * weight for value in fields[1:4])
            )
            changed += 1
    return changed


def _compact_and_scale(
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    target_height_m: float,
) -> tuple[list[Vector], list[tuple[int, ...]], dict[int, int], dict[str, float]]:
    used = sorted({index for face in faces for index in face})
    old_to_new = {old: new for new, old in enumerate(used)}
    # MakeHuman is Y-up and faces +Z; Blender is Z-up and this workspace uses
    # -Y as the front/outward direction.
    compact = [
        Vector((vertices[index].x, -vertices[index].z, vertices[index].y))
        for index in used
    ]
    low_z = min(point.z for point in compact)
    high_z = max(point.z for point in compact)
    source_height = high_z - low_z
    if source_height <= 1.0e-8:
        raise RuntimeError("MakeHuman body has invalid source height")
    scale = target_height_m / source_height
    compact = [
        Vector((point.x * scale, point.y * scale, (point.z - low_z) * scale))
        for point in compact
    ]
    compact_faces = [tuple(old_to_new[index] for index in face) for face in faces]
    return compact, compact_faces, old_to_new, {
        "source_height_units": source_height,
        "target_height_m": target_height_m,
        "uniform_scale": scale,
        "source_floor_z": low_z,
    }


def _attach_normalized_default_weights(
    body: bpy.types.Object,
    old_to_new: Mapping[int, int],
) -> dict[str, Any]:
    weights_payload = _read_json(WEIGHTS_PATH)
    raw_groups = weights_payload.get("weights")
    if not isinstance(raw_groups, Mapping):
        raise RuntimeError("MakeHuman default weights payload is invalid")
    rows: list[dict[str, float]] = [defaultdict(float) for _ in body.data.vertices]
    for name, assignments in raw_groups.items():
        if not isinstance(assignments, list):
            continue
        for source_index, raw_weight in assignments:
            compact_index = old_to_new.get(int(source_index))
            weight = float(raw_weight)
            if compact_index is not None and weight > 1.0e-8:
                rows[compact_index][str(name)] += weight
    fallback = 0
    normalized: list[dict[str, float]] = []
    for row in rows:
        ordered = sorted(row.items(), key=lambda item: (-item[1], item[0]))[:4]
        total = sum(weight for _, weight in ordered)
        if total <= 1.0e-8:
            normalized.append({"root": 1.0})
            fallback += 1
        else:
            normalized.append({name: weight / total for name, weight in ordered})
    groups = {
        name: body.vertex_groups.new(name=name)
        for name in sorted({name for row in normalized for name in row})
    }
    assignments = 0
    for index, row in enumerate(normalized):
        for name, weight in row.items():
            groups[name].add([index], weight, "REPLACE")
            assignments += 1
    return {
        "path": WEIGHTS_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": _sha256(WEIGHTS_PATH),
        "license": str(weights_payload.get("license") or ""),
        "vertex_count": len(rows),
        "weighted_vertex_count": len(rows),
        "fallback_root_vertex_count": fallback,
        "group_count": len(groups),
        "assignment_count": assignments,
        "maximum_influences": 4,
        "weights_normalized": True,
    }


def _new_body(
    candidate_id: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{candidate_id}__primary_surface")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update(calc_edges=True)
    body = bpy.data.objects.new(f"{candidate_id}__primary_surface", mesh)
    bpy.context.collection.objects.link(body)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    body["primary_surface"] = True
    body["body_class"] = "adult_female"
    body["source_foundation_id"] = FOUNDATION_ID
    body["wrong_sex_helper_present"] = False
    body["wrong_sex_helper_excluded"] = True
    body["source_anatomy_geometry_copied"] = False
    body["private_inactive_authoring_only"] = True
    body["runtime_activation_allowed"] = False
    body["adult_foundation_qualified"] = False
    body["candidate_author_id"] = CANDIDATE_AUTHOR_ID
    body["generic_identity_neutral_foundation"] = True
    body["kira_styling_applied"] = False
    body["armature_present"] = False
    body["pose_space_pelvic_patch_deformation_audit_passed"] = False
    body["mandatory_downstream_pose_gate"] = MANDATORY_DOWNSTREAM_POSE_GATE
    return body


def main() -> None:
    args = _arguments()
    if not args.acknowledge_inactive_authoring:
        raise RuntimeError(
            "--acknowledge-inactive-authoring is required; this wrapper may "
            "only create an inactive, unqualified workspace"
        )
    config_path = _project_file(args.config, suffix=".json")
    if not config_path.is_file():
        raise RuntimeError(f"config does not exist: {config_path}")
    config = _load_config(config_path)
    output_path = _project_file(args.output_blend, suffix=".blend")
    try:
        output_path.relative_to(INACTIVE_OUTPUT_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(
            f"output must stay beneath {INACTIVE_OUTPUT_ROOT}"
        ) from exc
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output_path}")

    authority = evaluate_adult_foundation_qualification(
        PROJECT_ROOT,
        FOUNDATION_ID,
    )
    if not authority["adult_eligible"]:
        raise RuntimeError("MakeHuman source is not confirmed-adult eligible")
    if not authority["foundation_authority"]["authorized"]:
        raise RuntimeError("MakeHuman source lacks foundation-use authority")
    base_path, target_bindings, registry_entry = _foundation_source_bindings()
    vertices, faces = _parse_body_group(base_path)
    target_records = [
        {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(path),
            "weight": weight,
            "changed_vertices": _apply_target(vertices, path, weight),
        }
        for path, weight in target_bindings
    ]
    compact, compact_faces, old_to_new, transform = _compact_and_scale(
        vertices,
        faces,
        float(config["target_height_m"]),
    )

    for existing in list(bpy.data.objects):
        bpy.data.objects.remove(existing, do_unlink=True)
    body = _new_body(config["candidate_id"], compact, compact_faces)
    weights = _attach_normalized_default_weights(body, old_to_new)
    intersection_cleanup = repair_bounded_self_intersections(body)
    report = author_continuous_adult_female_surface(
        body,
        frame=frame_from_mapping(config["frame"]),
        parameters=parameters_from_mapping(config.get("parameters")),
        project_root=PROJECT_ROOT,
    )
    build_manifest = {
        "schema_version": 1,
        "builder": "makehuman_adult_female_foundation_inactive_v1",
        "status": "INACTIVE_UNQUALIFIED_AWAITING_INDEPENDENT_REVIEW",
        "candidate_id": config["candidate_id"],
        "candidate_author_id": CANDIDATE_AUTHOR_ID,
        "foundation_id": FOUNDATION_ID,
        "identity_scope": "generic_identity_neutral_adult_female_foundation",
        "kira_styling_applied": False,
        "clothing_applied": False,
        "foundation_registry_status": registry_entry.get("qualified"),
        "foundation_gate_qualified_before_authoring": authority[
            "qualified_for_adult_foundation"
        ],
        "foundation_gate_blockers_before_authoring": authority["blockers"],
        "base": {
            "path": base_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(base_path),
            "face_group": "body",
        },
        "female_macro_targets": target_records,
        "wrong_sex_helper_group_excluded": True,
        "source_anatomy_geometry_copied": False,
        "transform": transform,
        "skin_weights": weights,
        "bounded_source_intersection_cleanup": intersection_cleanup,
        "surface_authoring": report,
        "render_performed": False,
        "glb_export_performed": False,
        "runtime_mutation_performed": False,
        "runtime_activation_allowed": False,
        "adult_foundation_qualified": False,
        "armature_present": False,
        "pose_space_pelvic_patch_deformation_audit_performed": False,
        "pose_space_pelvic_patch_deformation_audit_passed": False,
        "mandatory_downstream_kira_candidate_gate": (
            MANDATORY_DOWNSTREAM_POSE_GATE
        ),
    }
    body["inactive_foundation_build_manifest_json"] = json.dumps(
        build_manifest,
        sort_keys=True,
        separators=(",", ":"),
    )
    bpy.context.scene["inactive_adult_foundation_candidate"] = True
    bpy.context.scene["runtime_activation_allowed"] = False
    bpy.context.scene["render_performed"] = False
    bpy.context.scene["glb_export_performed"] = False
    bpy.context.scene["generic_identity_neutral_foundation"] = True
    bpy.context.scene["kira_styling_applied"] = False
    bpy.context.scene["clothing_applied"] = False
    bpy.context.scene["armature_present"] = False
    bpy.context.scene["pose_space_pelvic_patch_deformation_audit_passed"] = False
    bpy.context.scene["mandatory_downstream_pose_gate"] = (
        MANDATORY_DOWNSTREAM_POSE_GATE
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
    print(
        json.dumps(
            {
                "build_manifest": build_manifest,
                "saved_blend": output_path.relative_to(PROJECT_ROOT).as_posix(),
                "saved_blend_sha256": _sha256(output_path),
                "saved_blend_mutated_after_hash": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
