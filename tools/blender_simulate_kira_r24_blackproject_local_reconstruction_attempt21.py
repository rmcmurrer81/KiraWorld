"""Hash-bound Attempt 21 exact-boundary segmentation recovery derivation.

The wrapper preserves Attempts 15 through 20 and all evidence. It derives the
sealed Attempt 20 source, adds only a fail-closed recovery for a geometrically
proven collinear shortcut across consecutive exact boundary vertices, corrects
current-attempt labels, and retains no-save execution. Blender is not imported
when this wrapper is inspected by the static regression suite.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT21_CONFIG.json"
)
ATTEMPT20_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
)
ATTEMPT19_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
)
ATTEMPT18_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
EXPECTED_CONFIG_SHA256 = (
    "3b18774959fa164cead68a1e44255c062a5a1372bb9b910893c6e573ed2a982b"
)
EXPECTED_ATTEMPT20_WORKER_SHA256 = (
    "2837320b72dd637716b0433f6a91750e44c3460f89b57962eb3b8fb35b2afebc"
)


def load_attempt20_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt21_sealed_attempt20_provider", ATTEMPT20_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 21 could not load the sealed Attempt 20 provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 21 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 21 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 21 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 21 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 21 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_21"
        or overlay.get("status") != "STATIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 21 overlay identity drifted")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "generic_hole_fill_allowed",
        "coordinate_add_remove_merge_or_move_allowed",
        "geometry_changes_beyond_exact_boundary_segmentation_recovery_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 21 scope is not bounded and no-save")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt20_worker"]["sha256"] != EXPECTED_ATTEMPT20_WORKER_SHA256:
        raise RuntimeError("Attempt 21 provider constant and binding disagree")
    preserved = overlay["preserved_attempt20_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 20 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 20 preserved package byte total drifted")
    return verified


def load_attempt21_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt20_module()
    base_config_path = project_path(overlay["bindings"]["attempt20_config"]["path"])
    merged = provider.load_attempt20_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 20 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = (
        "kira.avatar.r24.blackproject_local_reconstruction_attempt21.config.v1"
    )
    merged["attempt_id"] = "attempt_21"
    merged["output"] = copy.deepcopy(overlay["output"])
    merged["replacement"].update(
        copy.deepcopy(overlay["boundary_recovery_parameters"])
    )
    merged["attempt21_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt21_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt21_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt21_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt21_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    for location in ("replacement", "hard_gates"):
        if float(merged[location]["minimum_new_triangle_angle_degrees"]) != float(
            unchanged["minimum_new_triangle_angle_degrees"]
        ):
            raise RuntimeError(f"Attempt 21 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 21 minimum-area gate drifted")
    return merged


BOUNDARY_RECOVERY_HELPERS = r'''
def cdt_edge_state(
    faces: Sequence[Sequence[int]],
) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], list[int]]]:
    counts: dict[tuple[int, int], int] = {}
    linked: dict[tuple[int, int], list[int]] = {}
    for face_index, raw_face in enumerate(faces):
        face = [int(value) for value in raw_face]
        if len(face) != 3 or len(set(face)) != 3:
            raise RuntimeError("boundary recovery received an invalid triangle")
        for first, second in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((first, second)))
            counts[edge] = counts.get(edge, 0) + 1
            linked.setdefault(edge, []).append(face_index)
    if any(value not in (1, 2) for value in counts.values()):
        raise RuntimeError("boundary recovery received nonmanifold edge incidence")
    return counts, linked


def exact_boundary_edges(
    boundary_output: Mapping[int, int], boundary_count: int
) -> set[tuple[int, int]]:
    if set(int(value) for value in boundary_output) != set(range(boundary_count)):
        raise RuntimeError("boundary recovery source mapping is incomplete")
    outputs = [int(boundary_output[index]) for index in range(boundary_count)]
    if len(set(outputs)) != boundary_count:
        raise RuntimeError("boundary recovery source mapping is not one-to-one")
    return {
        tuple(sorted((outputs[index], outputs[(index + 1) % boundary_count])))
        for index in range(boundary_count)
    }


def boundary_source_chain(
    start: int, end: int, step: int, boundary_count: int
) -> list[int]:
    result = [int(start)]
    current = int(start)
    for _ in range(boundary_count):
        if current == int(end):
            return result
        current = (current + step) % boundary_count
        result.append(current)
    raise RuntimeError("boundary recovery chain did not terminate")


def proven_collinear_boundary_chain(
    chord: tuple[int, int],
    coordinates: Sequence[Vector],
    boundary_output: Mapping[int, int],
    boundary_count: int,
    missing: set[tuple[int, int]],
    point_tolerance: float,
    area_tolerance: float,
) -> tuple[list[int], list[int]] | None:
    output_to_source = {
        int(output): int(source) for source, output in boundary_output.items()
    }
    if chord[0] not in output_to_source or chord[1] not in output_to_source:
        return None
    first_source = output_to_source[chord[0]]
    second_source = output_to_source[chord[1]]
    candidates: list[tuple[list[int], list[int]]] = []
    for step in (1, -1):
        sources = boundary_source_chain(
            first_source, second_source, step, boundary_count
        )
        if len(sources) <= 2:
            continue
        outputs = [int(boundary_output[source]) for source in sources]
        chain_edges = {
            tuple(sorted((first, second)))
            for first, second in zip(outputs, outputs[1:])
        }
        if not chain_edges.issubset(missing):
            continue
        start = coordinates[outputs[0]]
        end = coordinates[outputs[-1]]
        delta_x = float(end.x - start.x)
        delta_y = float(end.y - start.y)
        chord_squared = delta_x * delta_x + delta_y * delta_y
        chord_length = math.sqrt(chord_squared)
        if chord_length <= point_tolerance:
            continue
        previous_projection = 0.0
        ordered = True
        for output in outputs[1:-1]:
            point = coordinates[output]
            if abs(orient2d(start, end, point)) > area_tolerance:
                ordered = False
                break
            projection = (
                float(point.x - start.x) * delta_x
                + float(point.y - start.y) * delta_y
            ) / chord_squared
            minimum_step = point_tolerance / chord_length
            if not (
                projection > previous_projection + minimum_step
                and projection < 1.0 - minimum_step
            ):
                ordered = False
                break
            previous_projection = projection
        if not ordered:
            continue
        segment_lengths = [
            (coordinates[first] - coordinates[second]).length
            for first, second in zip(outputs, outputs[1:])
        ]
        if any(value <= point_tolerance for value in segment_lengths):
            continue
        if abs(sum(segment_lengths) - chord_length) > point_tolerance * len(outputs):
            continue
        candidates.append((outputs, sources))
    if len(candidates) > 1:
        raise RuntimeError("boundary recovery found an ambiguous collinear chain")
    return candidates[0] if candidates else None


def restore_exact_boundary_segmentation(
    coordinates: Sequence[Vector],
    faces: Sequence[Sequence[int]],
    boundary_output: Mapping[int, int],
    boundary_count: int,
    boundary: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> tuple[list[list[int]], dict[str, Any]]:
    tolerances = cdt_tolerances(boundary, epsilon, config)
    point_tolerance = tolerances["point_tolerance_m"]
    area_tolerance = tolerances["twice_area_tolerance_m2"]
    coordinate_snapshot = [
        (float(value.x), float(value.y)) for value in coordinates
    ]
    restored = [list(map(int, face)) for face in faces]
    constrained = exact_boundary_edges(boundary_output, boundary_count)
    boundary_outputs = {int(value) for value in boundary_output.values()}
    recoveries: list[dict[str, Any]] = []

    for _ in range(boundary_count + 1):
        edge_counts, edge_faces = cdt_edge_state(restored)
        open_edges = {edge for edge, count in edge_counts.items() if count == 1}
        if open_edges == constrained:
            if coordinate_snapshot != [
                (float(value.x), float(value.y)) for value in coordinates
            ]:
                raise RuntimeError("boundary recovery changed a coordinate")
            return restored, {
                "recovery_count": len(recoveries),
                "restored_boundary_segment_count": sum(
                    int(value["restored_segment_count"]) for value in recoveries
                ),
                "recoveries": recoveries,
                "coordinate_count_before": len(coordinate_snapshot),
                "coordinate_count_after": len(coordinates),
                "coordinates_unchanged": True,
                "exact_boundary_restored": True,
                **tolerances,
            }

        mismatch_before = len(open_edges.symmetric_difference(constrained))
        missing = constrained - open_edges
        extra = sorted(open_edges - constrained)
        applied = False
        for chord in extra:
            chain = proven_collinear_boundary_chain(
                chord,
                coordinates,
                boundary_output,
                boundary_count,
                missing,
                point_tolerance,
                area_tolerance,
            )
            if chain is None:
                continue
            linked = edge_faces.get(chord, [])
            if len(linked) != 1:
                raise RuntimeError(
                    "boundary recovery shortcut does not have one incident triangle"
                )
            face_index = linked[0]
            original = restored[face_index]
            apex_values = [value for value in original if value not in chord]
            if len(apex_values) != 1 or apex_values[0] in boundary_outputs:
                raise RuntimeError(
                    "boundary recovery shortcut lacks one unchanged interior apex"
                )
            apex = apex_values[0]
            original_area = orient2d(
                coordinates[original[0]],
                coordinates[original[1]],
                coordinates[original[2]],
            )
            if abs(original_area) <= area_tolerance:
                raise RuntimeError("boundary recovery source triangle is degenerate")
            outputs, sources = chain
            fan: list[list[int]] = []
            for first, second in zip(outputs, outputs[1:]):
                if (coordinates[first] - coordinates[second]).length <= point_tolerance:
                    raise RuntimeError("boundary recovery fan has coincident boundary points")
                if (coordinates[first] - coordinates[apex]).length <= point_tolerance:
                    raise RuntimeError("boundary recovery fan apex is coincident")
                if (coordinates[second] - coordinates[apex]).length <= point_tolerance:
                    raise RuntimeError("boundary recovery fan apex is coincident")
                signed = orient2d(
                    coordinates[first], coordinates[second], coordinates[apex]
                )
                if abs(signed) <= area_tolerance:
                    raise RuntimeError("boundary recovery fan contains a zero-area triangle")
                candidate = [first, second, apex]
                if signed * original_area < 0.0:
                    candidate = [second, first, apex]
                fan.append(candidate)
            trial = restored[:face_index] + fan + restored[face_index + 1 :]
            keys = [tuple(sorted(face)) for face in trial]
            if len(set(keys)) != len(keys):
                raise RuntimeError("boundary recovery created a duplicate triangle")
            trial_counts, _trial_faces = cdt_edge_state(trial)
            trial_open = {
                edge for edge, count in trial_counts.items() if count == 1
            }
            mismatch_after = len(trial_open.symmetric_difference(constrained))
            if mismatch_after >= mismatch_before:
                raise RuntimeError("boundary recovery did not reduce exact-boundary mismatch")
            restored = trial
            recoveries.append(
                {
                    "shortcut_output_edge": [int(chord[0]), int(chord[1])],
                    "boundary_source_chain": [int(value) for value in sources],
                    "boundary_output_chain": [int(value) for value in outputs],
                    "restored_segment_count": len(outputs) - 1,
                    "replacement_triangle_count": len(fan),
                    "mismatch_before": mismatch_before,
                    "mismatch_after": mismatch_after,
                }
            )
            applied = True
            break
        if not applied:
            raise RuntimeError(
                "exact boundary segmentation recovery found no unique collinear boundary shortcut"
            )
    raise RuntimeError("exact boundary segmentation recovery exceeded bounded iterations")
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 21 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def derive_attempt21_source(source20: str) -> str:
    source = source20
    source = exact_replace(
        source,
        "def validate_cdt_disk(\n",
        BOUNDARY_RECOVERY_HELPERS + "\n\ndef validate_cdt_disk(\n",
        "insert exact-boundary segmentation recovery helpers",
    )
    source = exact_replace(
        source,
        "    disk_topology = validate_cdt_disk(faces, boundary_output, boundary_count)\n"
        "    return {\n",
        "    faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation(\n"
        "        coordinates,\n"
        "        faces,\n"
        "        boundary_output,\n"
        "        boundary_count,\n"
        "        boundary,\n"
        "        epsilon,\n"
        "        config,\n"
        "    )\n"
        "    disk_topology = validate_cdt_disk(faces, boundary_output, boundary_count)\n"
        "    return {\n",
        "recover exact boundary before unchanged disk validation",
    )
    source = exact_replace(
        source,
        '        "cdt_sanitation": cdt_sanitation,\n'
        '        "disk_topology": disk_topology,\n',
        '        "cdt_sanitation": cdt_sanitation,\n'
        '        "boundary_segmentation_recovery": boundary_segmentation_recovery,\n'
        '        "disk_topology": disk_topology,\n',
        "return boundary recovery diagnostics",
    )
    source = exact_replace(
        source,
        '        "cdt_face_sanitation": cdt["cdt_sanitation"],\n'
        '        "cdt_disk_topology": cdt["disk_topology"],\n',
        '        "cdt_face_sanitation": cdt["cdt_sanitation"],\n'
        '        "cdt_boundary_segmentation_recovery": cdt[\n'
        '            "boundary_segmentation_recovery"\n'
        '        ],\n'
        '        "cdt_disk_topology": cdt["disk_topology"],\n',
        "surface boundary recovery evidence",
    )
    source = exact_replace(
        source,
        "    config = load_attempt20_config(config_path)\n",
        "    config = load_attempt21_config(config_path)\n",
        "Attempt 21 config loader",
    )
    for old, new in (
        ("attempt_20", "attempt_21"),
        ("attempt20", "attempt21"),
        ("Attempt 20", "Attempt 21"),
        ("ATTEMPT20", "ATTEMPT21"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 20 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(
        token in source
        for token in ("ATTEMPT20", "attempt_20", "attempt20", "Attempt 20")
    ):
        raise RuntimeError("Attempt 21 derived source retained a stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    required = {
        "restore_exact_boundary_segmentation",
        "proven_collinear_boundary_chain",
        "validate_cdt_disk",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 21 boundary recovery helpers were not inserted")
    return source


def materialize_attempt20_source(provider: Any) -> str:
    provider19 = provider.load_attempt19_module()
    source19 = provider19.derive_attempt19_source(
        ATTEMPT18_WORKER.read_text(encoding="utf-8")
    )
    return provider.derive_attempt20_source(source19)


def main() -> None:
    if sha256_file(ATTEMPT20_WORKER) != EXPECTED_ATTEMPT20_WORKER_SHA256:
        raise RuntimeError("Attempt 20 worker changed before Attempt 21 derivation")
    provider = load_attempt20_module()
    attempt20_before = ATTEMPT20_WORKER.read_bytes()
    attempt19_before = ATTEMPT19_WORKER.read_bytes()
    attempt18_before = ATTEMPT18_WORKER.read_bytes()
    source20 = materialize_attempt20_source(provider)
    source21 = derive_attempt21_source(source20)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt21_config": load_attempt21_config,
    }
    try:
        exec(
            compile(
                source21,
                str(Path(__file__).resolve()) + "::derived",
                "exec",
            ),
            namespace,
            namespace,
        )
    finally:
        if ATTEMPT20_WORKER.read_bytes() != attempt20_before:
            raise RuntimeError("Attempt 20 worker changed during Attempt 21 execution")
        if ATTEMPT19_WORKER.read_bytes() != attempt19_before:
            raise RuntimeError("Attempt 19 worker changed during Attempt 21 execution")
        if ATTEMPT18_WORKER.read_bytes() != attempt18_before:
            raise RuntimeError("Attempt 18 worker changed during Attempt 21 execution")


if __name__ == "__main__":
    main()
