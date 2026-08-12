#!/usr/bin/env python3
"""Execution-inert R24 intrinsic E* external-surface author operation.

The module is deliberately *not* an execution controller and is not bound to
any rejected R4 package.  Importing it does not import Blender, open a file,
create a datablock, run an operator, or write anything.  A later, separately
sealed one-shot controller may call :func:`author_external_surface_r24` only
after it has already opened and authenticated the exact R19 source.

The operation is transactional:

* build a deterministic replacement plan from the supplied exact context;
* stage a body-mesh copy and one detached (zero-collection) proof object;
* validate the stage before swapping the body mesh;
* compare the complete protected/outside ledger after the swap; and
* either finalize in memory or restore the original mesh and remove every
  staged datablock.

This module never saves, renders, exports, links the proof object, activates a
body, assigns a person, publishes, or creates an attempt/output directory.
Its result is authoring evidence for a future fresh-reopen evaluator, never an
acceptance result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Protocol, Sequence


SCHEMA = "kira.avatar.r24.intrinsic_estar_author_operation.v1"
PLAN_SCHEMA = "kira.avatar.r24.intrinsic_estar_author_plan.v1"
BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
BODY_MESH_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface_Mesh"
RIG_OBJECT_NAME = "Kira_R19_BlackProject_Native_188_Rig"
MATERIAL_NAME = "R19_WarmTexture_Genitalia_Attempt06_BoundedSurfaceResponse"
PROOF_OBJECT_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch"
PROOF_MESH_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch_Mesh"
EXPECTED_SOURCE_FACE_COUNT = 1436
EXPECTED_ESTAR_FACE_COUNT = 161
EXPECTED_OUTSIDE_FACE_COUNT = 1275
EXPECTED_BOUNDARY_COUNT = 41
MAXIMUM_NEW_INTERIOR_VERTICES = 160
MINIMUM_ANGLE_DEGREES = 12.0
MINIMUM_AREA_M2 = 1.0e-10
MAXIMUM_WORLD_DISPLACEMENT_M = 0.012
EXPECTED_R19_SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
EXPECTED_SOURCE_MESH_CONTEXT_SHA256 = "7719c03bd9f3a89ebe2beed730648b6327d4a25c01b5f38f1f25537918331614"
EXPECTED_BONE_NAMES_SHA256 = "cfc6fd9c970a7b78c640bd7f153750cb7d5fd33b019ec7e51bf5b7134059cf47"
_POSITION_KEY_DIGITS = 6
_GEOMETRY_EPSILON = 1.0e-12


class R24AuthorOperationError(RuntimeError):
    """Fail-closed base error for the in-memory author operation."""


class R24AuthorGeometryGateError(R24AuthorOperationError):
    """The deterministic proposal is not safe to stage or commit."""


class R24AuthorAtomicityError(R24AuthorOperationError):
    """A failed transaction could not reproduce its protected snapshot."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _vector(value: Sequence[object], size: int, label: str) -> tuple[float, ...]:
    if len(value) != size:
        raise R24AuthorOperationError(f"{label} must contain {size} values")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise R24AuthorOperationError(f"{label} is not finite")
    return result


def _sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Sequence[float], value: float) -> tuple[float, float, float]:
    return (a[0] * value, a[1] * value, a[2] * value)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(a: Sequence[float]) -> float:
    return math.sqrt(max(0.0, _dot(a, a)))


def _unit(a: Sequence[float]) -> tuple[float, float, float]:
    length = _length(a)
    if length <= _GEOMETRY_EPSILON:
        return (0.0, 0.0, 0.0)
    return _scale(a, 1.0 / length)


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return _length(_sub(a, b))


def _triangle_area(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    return 0.5 * _length(_cross(_sub(b, a), _sub(c, a)))


def _triangle_angles(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> tuple[float, float, float]:
    points = (a, b, c)
    result: list[float] = []
    for index in range(3):
        left = _sub(points[(index + 1) % 3], points[index])
        right = _sub(points[(index + 2) % 3], points[index])
        denominator = _length(left) * _length(right)
        if denominator <= _GEOMETRY_EPSILON:
            result.append(0.0)
            continue
        cosine = max(-1.0, min(1.0, _dot(left, right) / denominator))
        result.append(math.degrees(math.acos(cosine)))
    return tuple(result)  # type: ignore[return-value]


def _rotated_face(face: Sequence[int]) -> tuple[int, int, int]:
    values = tuple(int(item) for item in face)
    rotations = (values, values[1:] + values[:1], values[2:] + values[:2])
    return min(rotations)


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _edge_incidence(faces: Sequence[Sequence[int]]) -> dict[tuple[int, int], list[int]]:
    result: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(faces):
        if len(face) != 3 or len(set(face)) != 3:
            raise R24AuthorOperationError("replacement contains a malformed triangle")
        for offset, first in enumerate(face):
            key = _edge(int(first), int(face[(offset + 1) % 3]))
            result.setdefault(key, []).append(face_index)
    return result


def _topology_record(faces: Sequence[Sequence[int]]) -> dict[str, object]:
    incidence = _edge_incidence(faces)
    vertices = {int(value) for face in faces for value in face}
    boundary_edges = sorted(edge for edge, rows in incidence.items() if len(rows) == 1)
    invalid_edges = sorted(edge for edge, rows in incidence.items() if len(rows) not in {1, 2})
    adjacency: dict[int, set[int]] = {value: set() for value in vertices}
    for first, second in incidence:
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(vertices)
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current] & remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
    return {
        "vertex_count": len(vertices),
        "edge_count": len(incidence),
        "face_count": len(faces),
        "boundary_edge_count": len(boundary_edges),
        "boundary_edges": [list(edge) for edge in boundary_edges],
        "invalid_edge_count": len(invalid_edges),
        "connected_components": components,
        "euler_characteristic": len(vertices) - len(incidence) + len(faces),
    }


def _source_payload(context: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    source = context.get("source_mesh")
    domains = context.get("domains")
    contract = context.get("contract")
    if not isinstance(source, Mapping) or not isinstance(domains, Mapping) or not isinstance(contract, Mapping):
        raise R24AuthorOperationError("exact context is incomplete")
    required = {"faces", "positions", "normals", "texcoords", "joints", "weights", "morph_target_count"}
    if not required.issubset(source):
        raise R24AuthorOperationError("source mesh fields are incomplete")
    return source, domains, contract


def _validate_context(context: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    source, domains, contract = _source_payload(context)
    required = {"faces", "positions", "normals", "texcoords", "joints", "weights", "morph_target_count"}
    faces = source["faces"]
    positions = source["positions"]
    if not isinstance(faces, list) or len(faces) != EXPECTED_SOURCE_FACE_COUNT:
        raise R24AuthorOperationError("licensed source face count changed")
    if not isinstance(positions, list) or not positions:
        raise R24AuthorOperationError("licensed source vertices are absent")
    for field in ("normals", "texcoords", "joints", "weights"):
        if not isinstance(source[field], list) or len(source[field]) != len(positions):
            raise R24AuthorOperationError(f"licensed source {field} count changed")
    if source["morph_target_count"] != 0:
        raise R24AuthorOperationError("licensed patch unexpectedly has morph targets")
    source_identity = contract.get("exact_source")
    if not isinstance(source_identity, Mapping) or source_identity.get("preserved_target_blend_sha256") != EXPECTED_R19_SOURCE_SHA256:
        raise R24AuthorOperationError("exact R19 source identity changed")
    if canonical_sha256({field: source[field] for field in sorted(required)}) != EXPECTED_SOURCE_MESH_CONTEXT_SHA256:
        raise R24AuthorOperationError("exact licensed source-mesh context changed")
    bone_names = context.get("bone_names")
    if not isinstance(bone_names, list) or canonical_sha256(bone_names) != EXPECTED_BONE_NAMES_SHA256:
        raise R24AuthorOperationError("exact native bone-name inventory changed")
    estar = domains.get("estar")
    outside = domains.get("outside")
    boundary = domains.get("outer_cycle")
    if not isinstance(estar, (set, list, tuple)) or len(estar) != EXPECTED_ESTAR_FACE_COUNT:
        raise R24AuthorOperationError("E* face domain changed")
    if not isinstance(outside, (set, list, tuple)) or len(outside) != EXPECTED_OUTSIDE_FACE_COUNT:
        raise R24AuthorOperationError("outside-E* face domain changed")
    if set(int(value) for value in estar) & set(int(value) for value in outside):
        raise R24AuthorOperationError("E* and outside-E* domains overlap")
    if set(int(value) for value in estar) | set(int(value) for value in outside) != set(range(len(faces))):
        raise R24AuthorOperationError("E* partition is not complete")
    if not isinstance(boundary, (list, tuple)) or len(boundary) != EXPECTED_BOUNDARY_COUNT:
        raise R24AuthorOperationError("ordered E* boundary changed")
    exact_topology = contract.get("exact_topology")
    if not isinstance(exact_topology, Mapping) or list(boundary) != exact_topology.get("outer_boundary_cycle"):
        raise R24AuthorOperationError("contract and context boundary disagree")
    identity = contract.get("artifact_semantic_identity")
    required_names = identity.get("required_id_names") if isinstance(identity, Mapping) else None
    if not isinstance(required_names, Mapping) or MATERIAL_NAME not in required_names.get("MA", []):
        raise R24AuthorOperationError("required material semantic identity changed")
    return source, domains, contract


def _minimum_local_angle(faces: Sequence[Sequence[int]], positions: Sequence[Sequence[float]], selected: set[int] | None = None) -> float:
    values: list[float] = []
    for index, face in enumerate(faces):
        if selected is not None and index not in selected:
            continue
        values.extend(_triangle_angles(*(positions[int(value)] for value in face)))
    return min(values, default=0.0)


def _flip_improving_edges(
    source_faces: Sequence[Sequence[int]], positions: Sequence[Sequence[float]]
) -> tuple[list[tuple[int, int, int]], int]:
    """Deterministic 3-D Lawson-style flips without moving the fixed boundary."""

    faces = [_rotated_face(face) for face in source_faces]
    flip_count = 0
    seen = {tuple(sorted(_rotated_face(face) for face in faces))}
    for _pass in range(1024):
        incidence = _edge_incidence(faces)
        accepted = False
        for shared in sorted(edge for edge, rows in incidence.items() if len(rows) == 2):
            first_index, second_index = incidence[shared]
            first = faces[first_index]
            second = faces[second_index]
            opposite_first = next(value for value in first if value not in shared)
            opposite_second = next(value for value in second if value not in shared)
            if opposite_first == opposite_second:
                continue
            diagonal = _edge(opposite_first, opposite_second)
            if diagonal in incidence and diagonal != shared:
                continue
            old_angles = sorted(
                _triangle_angles(*(positions[value] for value in first))
                + _triangle_angles(*(positions[value] for value in second))
            )
            reference = _add(
                _cross(_sub(positions[first[1]], positions[first[0]]), _sub(positions[first[2]], positions[first[0]])),
                _cross(_sub(positions[second[1]], positions[second[0]]), _sub(positions[second[2]], positions[second[0]])),
            )
            candidate_a = (opposite_first, opposite_second, shared[0])
            candidate_b = (opposite_second, opposite_first, shared[1])
            candidate_normal = _add(
                _cross(_sub(positions[candidate_a[1]], positions[candidate_a[0]]), _sub(positions[candidate_a[2]], positions[candidate_a[0]])),
                _cross(_sub(positions[candidate_b[1]], positions[candidate_b[0]]), _sub(positions[candidate_b[2]], positions[candidate_b[0]])),
            )
            if _dot(reference, candidate_normal) < 0.0:
                candidate_a = (candidate_a[0], candidate_a[2], candidate_a[1])
                candidate_b = (candidate_b[0], candidate_b[2], candidate_b[1])
            new_angles = sorted(
                _triangle_angles(*(positions[value] for value in candidate_a))
                + _triangle_angles(*(positions[value] for value in candidate_b))
            )
            comparison = next(
                (
                    1 if new > old else -1
                    for old, new in zip(old_angles, new_angles, strict=True)
                    if abs(new - old) > 1.0e-9
                ),
                0,
            )
            if comparison <= 0:
                continue
            trial = list(faces)
            trial[first_index] = _rotated_face(candidate_a)
            trial[second_index] = _rotated_face(candidate_b)
            state = tuple(sorted(_rotated_face(face) for face in trial))
            if state in seen:
                continue
            faces = trial
            seen.add(state)
            flip_count += 1
            accepted = True
            break
        if not accepted:
            break
    return faces, flip_count


def _relax_interior(
    faces: Sequence[Sequence[int]],
    source_positions: Sequence[Sequence[float]],
    source_normals: Sequence[Sequence[float]],
    interior: set[int],
) -> list[tuple[float, float, float]]:
    """Bounded deterministic intrinsic relaxation; every interior point moves."""

    positions = [_vector(row, 3, "source position") for row in source_positions]
    neighbors: dict[int, set[int]] = {index: set() for index in interior}
    incident: dict[int, set[int]] = {index: set() for index in interior}
    for face_index, face in enumerate(faces):
        for value in face:
            if value in interior:
                incident[value].add(face_index)
                neighbors[value].update(int(other) for other in face if other != value)
    maximum_local_displacement = 0.01
    for vertex_index in sorted(interior):
        adjacent = sorted(neighbors[vertex_index])
        if not adjacent:
            raise R24AuthorOperationError("isolated E* interior vertex")
        centroid = _scale(
            tuple(sum(positions[index][axis] for index in adjacent) for axis in range(3)),
            1.0 / len(adjacent),
        )
        original = _vector(source_positions[vertex_index], 3, "source position")
        current = positions[vertex_index]
        old_minimum = _minimum_local_angle(faces, positions, incident[vertex_index])
        accepted = current
        for fraction in (0.08, 0.04, 0.02, 0.01):
            proposed = _add(current, _scale(_sub(centroid, current), fraction))
            displacement = _sub(proposed, original)
            length = _length(displacement)
            if length > maximum_local_displacement:
                proposed = _add(original, _scale(displacement, maximum_local_displacement / length))
            positions[vertex_index] = proposed
            if _minimum_local_angle(faces, positions, incident[vertex_index]) > old_minimum + 1.0e-9:
                accepted = proposed
                break
        positions[vertex_index] = accepted
        if _distance(accepted, original) <= 1.0e-9:
            direction = _unit(_vector(source_normals[vertex_index], 3, "source normal"))
            if direction == (0.0, 0.0, 0.0):
                axis = vertex_index % 3
                direction = tuple(1.0 if value == axis else 0.0 for value in range(3))  # type: ignore[assignment]
            positions[vertex_index] = _add(original, _scale(direction, 1.0e-6))
    return positions


def interpolate_source_payload(
    context: Mapping[str, object], source_face: int, barycentric: Sequence[float]
) -> dict[str, object]:
    """Pure reference implementation for UV, normal and native-weight transfer."""

    source, _, _ = _validate_context(context)
    bary = _vector(barycentric, 3, "barycentric binding")
    if abs(sum(bary) - 1.0) > 1.0e-9 or any(value < -1.0e-12 for value in bary):
        raise R24AuthorOperationError("barycentric binding is not normalized")
    face = source["faces"][int(source_face)]
    if not isinstance(face, list) or len(face) != 3:
        raise R24AuthorOperationError("source binding face is malformed")
    uv = [sum(bary[offset] * float(source["texcoords"][face[offset]][axis]) for offset in range(3)) for axis in range(2)]
    normal = _unit(
        tuple(sum(bary[offset] * float(source["normals"][face[offset]][axis]) for offset in range(3)) for axis in range(3))
    )
    weights: dict[int, float] = {}
    for offset, vertex_index in enumerate(face):
        for joint, weight in zip(source["joints"][vertex_index], source["weights"][vertex_index], strict=True):
            value = bary[offset] * float(weight)
            if value > 0.0:
                weights[int(joint)] = weights.get(int(joint), 0.0) + value
    total = sum(weights.values())
    if total <= 0.0:
        raise R24AuthorOperationError("interpolated native weights are empty")
    return {
        "uv": uv,
        "normal": list(normal),
        "joint_weights": [[joint, weights[joint] / total] for joint in sorted(weights)],
    }


@dataclass(frozen=True)
class AuthorPlan:
    schema: str
    complete_faces: tuple[tuple[int, int, int], ...]
    replacement_faces: tuple[tuple[int, int, int], ...]
    positions: tuple[tuple[float, float, float], ...]
    provenance: tuple[tuple[int, tuple[float, float, float], tuple[float, float, float]], ...]
    boundary_cycle: tuple[int, ...]
    interior_vertices: tuple[int, ...]
    outside_sha256: str
    replacement_sha256: str
    plan_sha256: str
    topology: Mapping[str, object]
    geometry: Mapping[str, object]
    material_name: str

    def evidence_record(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "complete_face_count": len(self.complete_faces),
            "replacement_face_count": len(self.replacement_faces),
            "outside_face_count": EXPECTED_OUTSIDE_FACE_COUNT,
            "boundary_vertex_count": len(self.boundary_cycle),
            "new_interior_vertex_count": len(self.interior_vertices),
            "outside_sha256": self.outside_sha256,
            "replacement_sha256": self.replacement_sha256,
            "plan_sha256": self.plan_sha256,
            "topology": dict(self.topology),
            "geometry": dict(self.geometry),
            "material_name": self.material_name,
        }


def build_author_plan(context: Mapping[str, object]) -> AuthorPlan:
    """Create a deterministic, side-effect-free E* retopology proposal."""

    source, domains, _contract = _validate_context(context)
    source_faces = [tuple(int(value) for value in row) for row in source["faces"]]
    positions = [_vector(row, 3, "source position") for row in source["positions"]]
    normals = [_vector(row, 3, "source normal") for row in source["normals"]]
    estar_indices = sorted(int(value) for value in domains["estar"])
    outside_indices = sorted(int(value) for value in domains["outside"])
    boundary = tuple(int(value) for value in domains["outer_cycle"])
    estar_vertices = {value for face_index in estar_indices for value in source_faces[face_index]}
    interior = estar_vertices - set(boundary)
    if len(interior) > MAXIMUM_NEW_INTERIOR_VERTICES:
        raise R24AuthorOperationError("E* interior vertex budget exceeded")
    source_estar = [source_faces[index] for index in estar_indices]
    replacement, flip_count = _flip_improving_edges(source_estar, positions)
    relaxed = _relax_interior(replacement, positions, normals, interior)
    replacement = sorted((_rotated_face(face) for face in replacement))
    topology = _topology_record(replacement)
    expected_boundary_edges = {_edge(boundary[index], boundary[(index + 1) % len(boundary)]) for index in range(len(boundary))}
    actual_boundary_edges = {tuple(row) for row in topology["boundary_edges"]}
    topology_passed = (
        topology["face_count"] == EXPECTED_ESTAR_FACE_COUNT
        and topology["boundary_edge_count"] == EXPECTED_BOUNDARY_COUNT
        and actual_boundary_edges == expected_boundary_edges
        and topology["invalid_edge_count"] == 0
        and topology["connected_components"] == 1
        and topology["euler_characteristic"] == 1
    )
    if not topology_passed:
        raise R24AuthorOperationError("deterministic E* replacement is not one exact manifold disk")
    complete = list(source_faces)
    for face_index, face in zip(estar_indices, replacement, strict=True):
        complete[face_index] = face
    incident_source: dict[int, tuple[int, int]] = {}
    for face_index in estar_indices:
        for offset, vertex_index in enumerate(source_faces[face_index]):
            incident_source.setdefault(vertex_index, (face_index, offset))
    provenance: list[tuple[int, tuple[float, float, float], tuple[float, float, float]]] = []
    for vertex_index, coordinate in enumerate(relaxed):
        if vertex_index not in estar_vertices:
            provenance.append((-1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
            continue
        source_face, offset = incident_source[vertex_index]
        bary = tuple(1.0 if index == offset else 0.0 for index in range(3))
        displacement = _sub(coordinate, positions[vertex_index])
        if vertex_index in boundary and _length(displacement) > 1.0e-12:
            raise R24AuthorOperationError("fixed E* boundary moved")
        if vertex_index in interior and _length(displacement) <= 1.0e-12:
            raise R24AuthorOperationError("source E* interior vertex was reused")
        provenance.append((source_face, bary, displacement))
    angles = [angle for face in replacement for angle in _triangle_angles(*(relaxed[value] for value in face))]
    areas_local = [_triangle_area(*(relaxed[value] for value in face)) for face in replacement]
    maximum_local_displacement = max(_distance(relaxed[index], positions[index]) for index in interior)
    geometry = {
        "edge_flip_count": flip_count,
        "minimum_triangle_angle_degrees_local": min(angles),
        "minimum_triangle_area_local2": min(areas_local),
        "maximum_local_displacement": maximum_local_displacement,
        "boundary_maximum_local_displacement": max(_distance(relaxed[index], positions[index]) for index in boundary),
        "minimum_angle_gate_degrees": MINIMUM_ANGLE_DEGREES,
        "minimum_area_gate_m2": MINIMUM_AREA_M2,
        "maximum_world_displacement_gate_m": MAXIMUM_WORLD_DISPLACEMENT_M,
        "world_metric_requires_open_body_transform": True,
    }
    outside_record = [
        {
            "face_index": index,
            "face": list(source_faces[index]),
            "corners": [
                {
                    "position": list(positions[vertex]),
                    "normal": list(normals[vertex]),
                    "uv": list(_vector(source["texcoords"][vertex], 2, "source uv")),
                    "joints": list(source["joints"][vertex]),
                    "weights": [float(value) for value in source["weights"][vertex]],
                }
                for vertex in source_faces[index]
            ],
        }
        for index in outside_indices
    ]
    replacement_record = {
        "faces": [list(face) for face in replacement],
        "positions": [list(relaxed[index]) for index in sorted(estar_vertices)],
        "provenance": [
            [index, provenance[index][0], list(provenance[index][1]), list(provenance[index][2])]
            for index in sorted(estar_vertices)
        ],
    }
    core = {
        "schema": PLAN_SCHEMA,
        "outside_sha256": canonical_sha256(outside_record),
        "replacement_sha256": canonical_sha256(replacement_record),
        "boundary": list(boundary),
        "interior": sorted(interior),
        "material": MATERIAL_NAME,
        "topology": topology,
        "geometry": geometry,
    }
    return AuthorPlan(
        schema=PLAN_SCHEMA,
        complete_faces=tuple(complete),
        replacement_faces=tuple(replacement),
        positions=tuple(relaxed),
        provenance=tuple(provenance),
        boundary_cycle=boundary,
        interior_vertices=tuple(sorted(interior)),
        outside_sha256=core["outside_sha256"],
        replacement_sha256=core["replacement_sha256"],
        plan_sha256=canonical_sha256(core),
        topology=topology,
        geometry=geometry,
        material_name=MATERIAL_NAME,
    )


class AuthorAdapter(Protocol):
    """Small transaction boundary used by Blender and by pure mock tests."""

    def protected_snapshot(self) -> str: ...
    def stage(self, plan: AuthorPlan) -> object: ...
    def inspect(self, stage: object, plan: AuthorPlan) -> Mapping[str, object]: ...
    def activate(self, stage: object) -> None: ...
    def finalize(self, stage: object) -> None: ...
    def rollback(self, stage: object | None) -> None: ...


def _validate_stage_inspection(value: Mapping[str, object], plan: AuthorPlan) -> None:
    required = {
        "plan_sha256": plan.plan_sha256,
        "outside_sha256": plan.outside_sha256,
        "proof_collection_link_count": 0,
        "proof_face_count": EXPECTED_SOURCE_FACE_COUNT,
        "replacement_face_count": EXPECTED_ESTAR_FACE_COUNT,
        "boundary_vertex_count": EXPECTED_BOUNDARY_COUNT,
        "new_interior_vertex_count": len(plan.interior_vertices),
        "material_name": MATERIAL_NAME,
        "body_staged_not_live": True,
        "save_performed": False,
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise R24AuthorOperationError(f"staged author inspection failed: {key}")


def _local_geometry_gate(plan: AuthorPlan) -> None:
    if float(plan.geometry["minimum_triangle_angle_degrees_local"]) < MINIMUM_ANGLE_DEGREES:
        raise R24AuthorGeometryGateError("proposal does not satisfy the 12-degree local quality gate")
    if float(plan.geometry["boundary_maximum_local_displacement"]) > 1.0e-10:
        raise R24AuthorGeometryGateError("proposal moved the exact boundary")


def _geometry_gate(plan: AuthorPlan, inspection: Mapping[str, object]) -> None:
    _local_geometry_gate(plan)
    world_displacement = inspection.get("maximum_world_displacement_m")
    world_area = inspection.get("minimum_world_triangle_area_m2")
    if not isinstance(world_displacement, (int, float)) or not math.isfinite(float(world_displacement)):
        raise R24AuthorGeometryGateError("stage did not measure world displacement")
    if not isinstance(world_area, (int, float)) or not math.isfinite(float(world_area)):
        raise R24AuthorGeometryGateError("stage did not measure world triangle area")
    if float(world_displacement) > MAXIMUM_WORLD_DISPLACEMENT_M + 1.0e-12:
        raise R24AuthorGeometryGateError("stage exceeded the world displacement cap")
    if float(world_area) < MINIMUM_AREA_M2:
        raise R24AuthorGeometryGateError("stage contains a sub-threshold triangle")


def _apply_plan_transaction(plan: AuthorPlan, adapter: AuthorAdapter) -> dict[str, object]:
    """Internal transaction, deliberately exposed to pure/mock regression tests."""

    _local_geometry_gate(plan)
    before = adapter.protected_snapshot()
    stage: object | None = None
    activated = False
    try:
        stage = adapter.stage(plan)
        inspection = adapter.inspect(stage, plan)
        _validate_stage_inspection(inspection, plan)
        _geometry_gate(plan, inspection)
        adapter.activate(stage)
        activated = True
        after = adapter.protected_snapshot()
        if after != before:
            raise R24AuthorOperationError("outside/protected state changed after staged activation")
        record = {
            "schema": SCHEMA,
            "status": "AUTHORED_IN_MEMORY_FRESH_R5_EVALUATION_REQUIRED_NOT_ACCEPTED",
            "plan": plan.evidence_record(),
            "stage": dict(inspection),
            "protected_snapshot_sha256": before,
            "authorized_mutated_objects": [BODY_OBJECT_NAME, PROOF_OBJECT_NAME],
            "proof_object_linked": False,
            "save_performed": False,
            "render_performed": False,
            "export_performed": False,
            "activation_performed": False,
            "assignment_performed": False,
            "publication_performed": False,
            "candidate_accepted": False,
        }
        record["evidence_sha256"] = canonical_sha256(record)
        adapter.finalize(stage)
        return record
    except BaseException:
        try:
            adapter.rollback(stage)
            restored = adapter.protected_snapshot()
        except BaseException as rollback_error:
            raise R24AuthorAtomicityError("author rollback raised before restoring protected state") from rollback_error
        if restored != before:
            raise R24AuthorAtomicityError("author rollback did not restore protected state")
        raise
    finally:
        del activated


def author_external_surface_r24(
    *,
    body: Any,
    context: Mapping[str, object],
    rig: Any | None = None,
    bpy_module: Any | None = None,
    adapter: AuthorAdapter | None = None,
) -> dict[str, object]:
    """Apply one bounded author operation to an already-open exact R19 body.

    ``adapter`` exists for deterministic pure/mock tests.  Production callers
    omit it; only then is Blender imported lazily.  The built-in proposal is
    required to satisfy every precommit geometry gate or the function raises
    before changing the live body.
    """

    plan = build_author_plan(context)
    if adapter is None:
        if bpy_module is None:
            import bpy as bpy_module  # type: ignore[import-not-found]
        if (
            body is None
            or getattr(body, "name", None) != BODY_OBJECT_NAME
            or getattr(body, "type", None) != "MESH"
            or getattr(getattr(body, "data", None), "name", None) != BODY_MESH_NAME
        ):
            raise R24AuthorOperationError("exact already-open R19 body was not supplied")
        if rig is None:
            rig = bpy_module.data.objects.get(RIG_OBJECT_NAME)
        adapter = _BlenderAuthorAdapter(bpy_module, body, rig, context)
    return _apply_plan_transaction(plan, adapter)


@dataclass
class _BlenderStage:
    body: Any
    original_mesh: Any
    staged_mesh: Any
    proof_object: Any
    proof_mesh: Any
    active: bool = False
    finalized: bool = False


class _BlenderAuthorAdapter:
    """Lazy Blender implementation; constructing it has no file I/O."""

    def __init__(self, bpy_module: Any, body: Any, rig: Any, context: Mapping[str, object]) -> None:
        self.bpy = bpy_module
        self.body = body
        self.rig = rig
        self.context = context
        if rig is None or getattr(rig, "name", None) != RIG_OBJECT_NAME or getattr(rig, "type", None) != "ARMATURE":
            raise R24AuthorOperationError("exact already-open R19 rig was not supplied")
        if bpy_module.data.objects.get(PROOF_OBJECT_NAME) is not None or bpy_module.data.meshes.get(PROOF_MESH_NAME) is not None:
            raise R24AuthorOperationError("proof identity already exists; append-only transaction is not fresh")

    @staticmethod
    def _position_key(value: Sequence[float]) -> tuple[float, float, float]:
        return tuple(round(float(item), _POSITION_KEY_DIGITS) for item in value)  # type: ignore[return-value]

    def _source_sets(self) -> tuple[set[tuple[float, float, float]], set[tuple[float, float, float]]]:
        source, domains, _ = _validate_context(self.context)
        source_faces = source["faces"]
        estar_vertices = {int(value) for index in domains["estar"] for value in source_faces[int(index)]}
        boundary = set(int(value) for value in domains["outer_cycle"])
        positions = source["positions"]
        return (
            {self._position_key(positions[index]) for index in estar_vertices},
            {self._position_key(positions[index]) for index in estar_vertices - boundary},
        )

    def _group_record(self, vertex: Any) -> list[list[object]]:
        rows = []
        for assignment in vertex.groups:
            rows.append([str(self.body.vertex_groups[int(assignment.group)].name), float(assignment.weight)])
        return sorted(rows)

    def protected_snapshot(self) -> str:
        mesh = self.body.data
        estar_keys, interior_keys = self._source_sets()
        vertex_keys = [self._position_key(vertex.co) for vertex in mesh.vertices]
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            raise R24AuthorOperationError("body has no active UV layer")
        vertices = [
            {
                "position": list(vertex.co),
                "normal": list(vertex.normal),
                "groups": self._group_record(vertex),
            }
            for vertex in mesh.vertices
            if vertex_keys[int(vertex.index)] not in interior_keys
        ]
        faces = []
        for polygon in mesh.polygons:
            keys = [vertex_keys[int(index)] for index in polygon.vertices]
            authorized = bool(keys) and all(key in estar_keys for key in keys) and any(key in interior_keys for key in keys)
            if authorized:
                continue
            faces.append(
                {
                    "vertices": [list(mesh.vertices[int(index)].co) for index in polygon.vertices],
                    "uv": [list(uv_layer.data[int(index)].uv) for index in polygon.loop_indices],
                    "material": int(polygon.material_index),
                    "smooth": bool(polygon.use_smooth),
                }
            )
        actions = []
        for action in sorted(self.bpy.data.actions, key=lambda item: str(item.name)):
            actions.append(
                [
                    str(action.name),
                    [
                        [
                            str(curve.data_path),
                            int(curve.array_index),
                            [[float(point.co.x), float(point.co.y), str(point.interpolation)] for point in curve.keyframe_points],
                        ]
                        for curve in sorted(action.fcurves, key=lambda item: (str(item.data_path), int(item.array_index)))
                    ],
                ]
            )
        rig = [
            [str(bone.name), str(bone.parent.name) if bone.parent else None, list(bone.head_local), list(bone.tail_local), [list(row) for row in bone.matrix_local]]
            for bone in sorted(self.rig.data.bones, key=lambda item: str(item.name))
        ]
        record = {
            "vertices": vertices,
            "faces": faces,
            "materials": [str(item.name) if item is not None else None for item in mesh.materials],
            "matrix_world": [list(row) for row in self.body.matrix_world],
            "vertex_group_names": [str(item.name) for item in self.body.vertex_groups],
            "modifiers": [[str(item.name), str(item.type), str(getattr(getattr(item, "object", None), "name", ""))] for item in self.body.modifiers],
            "rig": rig,
            "actions": actions,
        }
        return canonical_sha256(record)

    def _source_vertex_map(self, mesh: Any, source_indices: set[int]) -> dict[int, int]:
        source, _, _ = _validate_context(self.context)
        available: dict[tuple[float, float, float], list[int]] = {}
        for vertex in mesh.vertices:
            available.setdefault(self._position_key(vertex.co), []).append(int(vertex.index))
        result: dict[int, int] = {}
        for source_index in sorted(source_indices):
            key = self._position_key(source["positions"][source_index])
            candidates = available.get(key, [])
            if len(candidates) != 1:
                raise R24AuthorOperationError(f"exact source vertex {source_index} was not uniquely mapped in body")
            result[source_index] = candidates[0]
        return result

    def _stage_body_mesh(self, plan: AuthorPlan) -> Any:
        import bmesh  # type: ignore[import-not-found]

        source, domains, _ = _validate_context(self.context)
        mesh = self.body.data.copy()
        mesh.name = BODY_MESH_NAME + "__R24_STAGED_NOT_LIVE"
        original_normals = [tuple(float(value) for value in vertex.normal) for vertex in mesh.vertices]
        estar_vertices = {int(value) for index in domains["estar"] for value in source["faces"][int(index)]}
        source_to_body = self._source_vertex_map(mesh, estar_vertices)
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            face_by_key = {frozenset(int(vertex.index) for vertex in face.verts): face for face in bm.faces}
            doomed = []
            for face_index in domains["estar"]:
                key = frozenset(source_to_body[int(value)] for value in source["faces"][int(face_index)])
                face = face_by_key.get(key)
                if face is None:
                    raise R24AuthorOperationError("exact source E* face was not found in staged body")
                doomed.append(face)
            bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
            bm.verts.ensure_lookup_table()
            for source_index in plan.interior_vertices:
                bm.verts[source_to_body[source_index]].co = plan.positions[source_index]
            material_slot = next(
                (index for index, material in enumerate(mesh.materials) if material is not None and str(material.name) == MATERIAL_NAME),
                None,
            )
            if material_slot is None:
                raise R24AuthorOperationError("required body material slot is absent")
            uv_layer = bm.loops.layers.uv.active
            if uv_layer is None:
                raise R24AuthorOperationError("body BMesh has no active UV layer")
            for face_values in plan.replacement_faces:
                face = bm.faces.new(tuple(bm.verts[source_to_body[index]] for index in face_values))
                face.material_index = int(material_slot)
                face.smooth = True
                for loop, source_index in zip(face.loops, face_values, strict=True):
                    loop[uv_layer].uv = source["texcoords"][source_index]
            bm.to_mesh(mesh)
        except BaseException:
            self.bpy.data.meshes.remove(mesh)
            raise
        finally:
            bm.free()
        if len(mesh.vertices) != len(original_normals):
            self.bpy.data.meshes.remove(mesh)
            raise R24AuthorOperationError("staged body changed vertex count")
        try:
            mesh.normals_split_custom_set_from_vertices(original_normals)
        except (AttributeError, RuntimeError, ValueError) as exc:
            self.bpy.data.meshes.remove(mesh)
            raise R24AuthorOperationError("staged body could not preserve exact vertex normals") from exc
        mesh.update()
        return mesh

    def _stage_proof(self, plan: AuthorPlan) -> tuple[Any, Any]:
        source, _domains, _ = _validate_context(self.context)
        material = self.bpy.data.materials.get(MATERIAL_NAME)
        if material is None:
            raise R24AuthorOperationError("required material datablock is absent")
        mesh = self.bpy.data.meshes.new(PROOF_MESH_NAME)
        obj = None
        try:
            mesh.from_pydata(plan.positions, [], plan.complete_faces)
            mesh.materials.append(material)
            for polygon in mesh.polygons:
                polygon.material_index = 0
                polygon.use_smooth = True
            uv = mesh.uv_layers.new(name="UVMap")
            for polygon in mesh.polygons:
                for loop_index, source_index in zip(polygon.loop_indices, polygon.vertices, strict=True):
                    uv.data[int(loop_index)].uv = source["texcoords"][int(source_index)]
            mesh.normals_split_custom_set_from_vertices([tuple(value) for value in source["normals"]])
            source_face = mesh.attributes.new("r24_source_face", "INT", "POINT")
            barycentric = mesh.attributes.new("r24_barycentric", "FLOAT_VECTOR", "POINT")
            displacement = mesh.attributes.new("r24_displacement_local_m", "FLOAT_VECTOR", "POINT")
            for index, row in enumerate(plan.provenance):
                source_face.data[index].value = int(row[0])
                barycentric.data[index].vector = row[1]
                displacement.data[index].vector = row[2]
            mesh.update()
            obj = self.bpy.data.objects.new(PROOF_OBJECT_NAME, mesh)
            obj.matrix_world = self.body.matrix_world.copy()
            obj.hide_render = True
            obj.hide_viewport = True
            obj["private_review_only"] = True
            obj["inactive"] = True
            obj["unassigned"] = True
            obj["unpublished"] = True
            for name in self.context["bone_names"]:
                obj.vertex_groups.new(name=str(name))
            for vertex_index, (joints, weights) in enumerate(zip(source["joints"], source["weights"], strict=True)):
                for joint, weight in zip(joints, weights, strict=True):
                    if float(weight) > 0.0:
                        obj.vertex_groups[int(joint)].add([vertex_index], float(weight), "REPLACE")
            modifier = obj.modifiers.new("KIRA_R24_NATIVE_188_RIG", "ARMATURE")
            modifier.object = self.rig
            modifier.use_vertex_groups = True
            modifier.use_deform_preserve_volume = True
            if obj.users_collection:
                raise R24AuthorOperationError("proof object was unexpectedly linked")
            return obj, mesh
        except BaseException:
            if obj is not None:
                self.bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.name in self.bpy.data.meshes:
                self.bpy.data.meshes.remove(mesh)
            raise

    def stage(self, plan: AuthorPlan) -> _BlenderStage:
        staged_mesh = self._stage_body_mesh(plan)
        try:
            proof_object, proof_mesh = self._stage_proof(plan)
        except BaseException:
            self.bpy.data.meshes.remove(staged_mesh)
            raise
        return _BlenderStage(self.body, self.body.data, staged_mesh, proof_object, proof_mesh)

    def inspect(self, stage: _BlenderStage, plan: AuthorPlan) -> Mapping[str, object]:
        linear = self.body.matrix_world.to_3x3()
        maximum_world = max((linear @ stage.proof_mesh.attributes["r24_displacement_local_m"].data[index].vector).length for index in plan.interior_vertices)
        minimum_area = math.inf
        for face in plan.replacement_faces:
            points = [self.body.matrix_world @ stage.proof_mesh.vertices[index].co for index in face]
            minimum_area = min(minimum_area, _triangle_area(*(tuple(float(value) for value in point) for point in points)))
        return {
            "plan_sha256": plan.plan_sha256,
            "outside_sha256": plan.outside_sha256,
            "proof_collection_link_count": len(stage.proof_object.users_collection),
            "proof_face_count": len(stage.proof_mesh.polygons),
            "replacement_face_count": len(plan.replacement_faces),
            "boundary_vertex_count": len(plan.boundary_cycle),
            "new_interior_vertex_count": len(plan.interior_vertices),
            "material_name": MATERIAL_NAME,
            "body_staged_not_live": stage.body.data is stage.original_mesh,
            "maximum_world_displacement_m": float(maximum_world),
            "minimum_world_triangle_area_m2": float(minimum_area),
            "save_performed": False,
        }

    def activate(self, stage: _BlenderStage) -> None:
        if stage.body.data is not stage.original_mesh or stage.proof_object.users_collection:
            raise R24AuthorOperationError("stage changed before activation")
        stage.body.data = stage.staged_mesh
        stage.active = True

    def finalize(self, stage: _BlenderStage) -> None:
        if not stage.active or stage.body.data is not stage.staged_mesh or stage.proof_object.users_collection:
            raise R24AuthorOperationError("cannot finalize an inactive or linked stage")
        original_name = str(stage.original_mesh.name)
        stage.original_mesh.name = BODY_MESH_NAME + "__R24_RETIRED_IN_MEMORY"
        stage.staged_mesh.name = original_name
        self.bpy.data.meshes.remove(stage.original_mesh)
        stage.finalized = True

    def rollback(self, stage: _BlenderStage | None) -> None:
        if stage is None or stage.finalized:
            return
        if stage.active:
            stage.body.data = stage.original_mesh
            stage.active = False
        if stage.proof_object is not None and stage.proof_object.name in self.bpy.data.objects:
            self.bpy.data.objects.remove(stage.proof_object, do_unlink=True)
        if stage.proof_mesh is not None and stage.proof_mesh.name in self.bpy.data.meshes:
            self.bpy.data.meshes.remove(stage.proof_mesh)
        if stage.staged_mesh is not None and stage.staged_mesh.name in self.bpy.data.meshes:
            self.bpy.data.meshes.remove(stage.staged_mesh)


__all__ = [
    "AuthorAdapter",
    "AuthorPlan",
    "R24AuthorAtomicityError",
    "R24AuthorGeometryGateError",
    "R24AuthorOperationError",
    "author_external_surface_r24",
    "build_author_plan",
    "canonical_sha256",
    "interpolate_source_payload",
]
