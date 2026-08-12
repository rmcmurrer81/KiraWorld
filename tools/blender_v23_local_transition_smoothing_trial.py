"""Create bounded topology-preserving V23 pubic-transition smoothing trials.

This is an engineering-only postprocess.  It deliberately leaves the main V23
builder untouched, opens the supplied R11 blend, moves only vertices in the
folded pubic transition plus a very small connected falloff, and writes one
clearly named trial blend and a machine-readable movement report.

The distal shaft/scrotal surfaces, face, eyes, hair, hands, and every vertex
outside the bounded anterior-pelvis region are position-locked.  No vertices,
edges, or faces are added or removed.

Usage:
    blender --background --python tools/blender_v23_local_transition_smoothing_trial.py \
      -- SOURCE.blend OUTPUT_DIRECTORY conservative

The last argument is either ``conservative`` or ``surface_fair``.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector


args = sys.argv[sys.argv.index("--") + 1 :]
if len(args) != 3:
    raise SystemExit(
        "expected SOURCE.blend OUTPUT_DIRECTORY conservative|surface_fair"
    )

SOURCE = Path(args[0]).resolve()
OUT = Path(args[1]).resolve()
MODE = args[2].strip().lower()
if MODE not in {"conservative", "surface_fair"}:
    raise SystemExit(f"unsupported smoothing mode: {MODE}")

OUT.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def group_weight(obj: bpy.types.Object, group_name: str, vertex_index: int) -> float:
    group = obj.vertex_groups.get(group_name)
    if group is None:
        return 0.0
    try:
        return float(group.weight(vertex_index))
    except RuntimeError:
        return 0.0


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def topology_signature(obj: bpy.types.Object) -> dict[str, object]:
    edge_pairs = sorted(
        tuple(sorted((int(edge.vertices[0]), int(edge.vertices[1]))))
        for edge in obj.data.edges
    )
    face_loops = sorted(
        tuple(sorted(int(index) for index in polygon.vertices))
        for polygon in obj.data.polygons
    )
    encoded = json.dumps(
        {"edges": edge_pairs, "faces": face_loops},
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "connectivity_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def weighted_fit(samples: list[tuple[float, float, float]]) -> list[float]:
    """Fit y = a + bz + cz^2 + dx^2 without a NumPy dependency."""

    # Gaussian elimination on the four-equation normal system.
    matrix = [[0.0 for _ in range(5)] for _ in range(4)]
    for x_value, z_value, y_value in samples:
        dz = z_value - 0.742
        terms = (1.0, dz, dz * dz, x_value * x_value)
        for row in range(4):
            for column in range(4):
                matrix[row][column] += terms[row] * terms[column]
            matrix[row][4] += terms[row] * y_value

    for pivot in range(4):
        best = max(range(pivot, 4), key=lambda row: abs(matrix[row][pivot]))
        matrix[pivot], matrix[best] = matrix[best], matrix[pivot]
        divisor = matrix[pivot][pivot]
        if abs(divisor) < 1.0e-12:
            raise RuntimeError("singular local pelvis surface fit")
        for column in range(pivot, 5):
            matrix[pivot][column] /= divisor
        for row in range(4):
            if row == pivot:
                continue
            factor = matrix[row][pivot]
            for column in range(pivot, 5):
                matrix[row][column] -= factor * matrix[pivot][column]
    return [matrix[row][4] for row in range(4)]


def fitted_y(coefficients: list[float], x_value: float, z_value: float) -> float:
    dz = z_value - 0.742
    return (
        coefficients[0]
        + coefficients[1] * dz
        + coefficients[2] * dz * dz
        + coefficients[3] * x_value * x_value
    )


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

body = next(
    (
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.data.attributes.get("V23_Surface_Class") is not None
    ),
    None,
)
if body is None:
    raise RuntimeError("no V23 body carrying V23_Surface_Class was found")

surface_class = body.data.attributes["V23_Surface_Class"]
transition_group_name = "V23_AUTHORED_PUBIC_TRANSITION"
shaft_group_name = "V23_AUTHORED_SHAFT_GLANS_SURFACE"
scrotal_group_name = "V23_AUTHORED_SCROTAL_ROOT_SURFACE"
if body.vertex_groups.get(transition_group_name) is None:
    raise RuntimeError("V23 transition vertex group is missing")

before_topology = topology_signature(body)
before_positions = [vertex.co.copy() for vertex in body.data.vertices]

neighbors: list[list[int]] = [[] for _ in body.data.vertices]
for edge in body.data.edges:
    first, second = (int(edge.vertices[0]), int(edge.vertices[1]))
    neighbors[first].append(second)
    neighbors[second].append(first)

# Distal authored anatomy is explicitly position-locked.  Only the actual
# transition/root envelope and a small adjacent body falloff can move.
protected: set[int] = set()
core_weights: dict[int, float] = {}
for vertex in body.data.vertices:
    index = vertex.index
    co = vertex.co
    class_value = float(surface_class.data[index].value)
    transition_weight = group_weight(body, transition_group_name, index)
    shaft_weight = group_weight(body, shaft_group_name, index)
    scrotal_weight = group_weight(body, scrotal_group_name, index)

    distal_authored = (
        (shaft_weight > 0.02 and (co.z < 0.706 or co.y < -0.180))
        or (scrotal_weight > 0.02 and co.z < 0.700)
    )
    outside_box = (
        abs(co.x) > 0.112
        or co.y > -0.030
        or co.y < -0.218
        or co.z < 0.665
        or co.z > 0.820
    )
    if distal_authored or outside_box:
        protected.add(index)
        continue

    # Core coverage follows the builder's transition group.  The explicit
    # class check catches interpolated subdivision vertices whose group weight
    # is numerically tiny but which visibly belong to the folded transition.
    class_gate = smoothstep((class_value - 2.35) / 0.55)
    group_gate = smoothstep(transition_weight)
    center_gate = smoothstep((0.112 - abs(co.x)) / 0.085)
    lower_gate = smoothstep((co.z - 0.665) / 0.030)
    upper_gate = smoothstep((0.820 - co.z) / 0.030)
    weight = max(class_gate * 0.82, group_gate) * center_gate * lower_gate * upper_gate
    if weight > 0.01:
        core_weights[index] = min(1.0, weight)

if not core_weights:
    raise RuntimeError("bounded transition selection is empty")

# Add at most two adjacent rings as a low-weight falloff.  This intentionally
# allows the recessed inherited boundary to relax instead of pinning the dark
# tunnel in place, but it cannot propagate through the pelvis or thighs.
weights = dict(core_weights)
frontier = set(core_weights)
for ring, multiplier in ((1, 0.20), (2, 0.07)):
    next_frontier: set[int] = set()
    for index in frontier:
        for neighbor in neighbors[index]:
            if neighbor in protected or neighbor in weights:
                continue
            co = body.data.vertices[neighbor].co
            if (
                abs(co.x) <= 0.125
                and -0.225 <= co.y <= -0.025
                and 0.655 <= co.z <= 0.830
            ):
                weights[neighbor] = multiplier
                next_frontier.add(neighbor)
    frontier = next_frontier

# The surface-fair trial additionally derives a neutral anterior-pelvis target
# from intact bilateral body samples.  No external anatomy or alternate body
# surface is copied.
surface_coefficients: list[float] | None = None
support_samples: list[tuple[float, float, float]] = []
if MODE == "surface_fair":
    for vertex in body.data.vertices:
        co = vertex.co
        index = vertex.index
        if index in weights:
            continue
        if (
            0.055 <= abs(co.x) <= 0.132
            and -0.215 <= co.y <= -0.040
            and 0.670 <= co.z <= 0.825
            and group_weight(body, shaft_group_name, index) <= 0.001
            and group_weight(body, scrotal_group_name, index) <= 0.001
        ):
            support_samples.append((float(co.x), float(co.z), float(co.y)))
    if len(support_samples) < 80:
        raise RuntimeError(
            f"insufficient intact bilateral support samples: {len(support_samples)}"
        )
    surface_coefficients = weighted_fit(support_samples)

if MODE == "conservative":
    iterations = 7
    strength = 0.38
    axis_scale = Vector((0.10, 1.00, 0.14))
    surface_pull = 0.0
else:
    iterations = 9
    strength = 0.46
    axis_scale = Vector((0.08, 1.00, 0.12))
    surface_pull = 0.24

per_iteration_max_delta: list[float] = []
for _iteration in range(iterations):
    old = [vertex.co.copy() for vertex in body.data.vertices]
    proposed: dict[int, Vector] = {}
    iteration_max = 0.0
    for index, weight in weights.items():
        linked = neighbors[index]
        if not linked:
            continue
        average = Vector((0.0, 0.0, 0.0))
        for neighbor in linked:
            average += old[neighbor]
        average /= len(linked)
        delta = average - old[index]
        delta = Vector(
            (
                delta.x * axis_scale.x,
                delta.y * axis_scale.y,
                delta.z * axis_scale.z,
            )
        )
        move = delta * (strength * weight)

        if surface_coefficients is not None:
            co = old[index]
            # Only the folded superior transition gets a surface pull.  The
            # root immediately beside the authored anatomy receives a tapered
            # fraction and distal surfaces receive none.
            superior_gate = smoothstep((co.z - 0.688) / 0.052)
            lateral_gate = smoothstep((0.108 - abs(co.x)) / 0.080)
            target = fitted_y(surface_coefficients, co.x, co.z)
            y_delta = max(-0.0040, min(0.0040, target - co.y))
            move.y += y_delta * surface_pull * weight * superior_gate * lateral_gate

        # Per-iteration displacement clamps prevent collapse even in the
        # stronger trial.
        move.x = max(-0.0007, min(0.0007, move.x))
        move.y = max(-0.0028, min(0.0028, move.y))
        move.z = max(-0.0008, min(0.0008, move.z))
        proposed[index] = old[index] + move
        iteration_max = max(iteration_max, move.length)

    for index, coordinate in proposed.items():
        body.data.vertices[index].co = coordinate
    body.data.update()
    per_iteration_max_delta.append(iteration_max)

# Smooth shading and current face normals are recomputed without changing
# connectivity.  No normal-only trick is used to conceal the surface.
for polygon in body.data.polygons:
    polygon.use_smooth = True
body.data.update(calc_edges=False)

after_topology = topology_signature(body)
if before_topology != after_topology:
    raise RuntimeError("topology changed during topology-preserving smoothing")

outside_changed = []
distal_changed = []
movement_lengths = []
for index, vertex in enumerate(body.data.vertices):
    movement = (vertex.co - before_positions[index]).length
    if movement > 1.0e-9:
        movement_lengths.append(movement)
    if index not in weights and movement > 1.0e-9:
        outside_changed.append((index, movement))
    if index in protected and movement > 1.0e-9:
        distal_changed.append((index, movement))
if outside_changed or distal_changed:
    raise RuntimeError(
        "bounded smoothing moved protected/outside vertices: "
        f"outside={len(outside_changed)} distal={len(distal_changed)}"
    )

trial_label = (
    "V23 R11 LOCAL LAPLACIAN CONSERVATIVE ENGINEERING TRIAL"
    if MODE == "conservative"
    else "V23 R11 LOCAL LAPLACIAN + SURFACE FAIR ENGINEERING TRIAL"
)
body["status"] = "ENGINEERING TRIAL — NOT AN OWNER-REVIEW CANDIDATE"
body["v23_postprocess_trial"] = trial_label
body["v23_postprocess_scope"] = (
    "folded pubic transition plus two-ring bounded falloff only"
)
body["v23_postprocess_topology_preserved"] = True
body["v23_postprocess_distal_authored_anatomy_preserved"] = True
body["v23_postprocess_source_blend"] = str(SOURCE)

blend_path = OUT / (
    "BIOLOGICAL_ROBERT_V23_R11_LOCAL_LAPLACIAN_CONSERVATIVE_TRIAL.blend"
    if MODE == "conservative"
    else "BIOLOGICAL_ROBERT_V23_R11_LOCAL_LAPLACIAN_SURFACE_FAIR_TRIAL.blend"
)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

report = {
    "schema": "kira.avatar.v23.local_transition_smoothing_trial.v1",
    "status": "ENGINEERING TRIAL — NOT AN OWNER-REVIEW CANDIDATE",
    "mode": MODE,
    "source_blend": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output_blend": str(blend_path),
    "output_sha256": sha256(blend_path),
    "scope": {
        "purpose": "test whether bounded smoothing removes the R11 tunnel/panel",
        "allowed": "folded pubic transition plus a two-ring local falloff",
        "locked": [
            "distal authored anatomy",
            "body outside bounded anterior-pelvis ROI",
            "face",
            "actual iris material",
            "hair",
            "hands",
        ],
        "topology_operations": "none",
    },
    "selection": {
        "core_vertices": len(core_weights),
        "weighted_vertices_total": len(weights),
        "protected_vertices": len(protected),
        "surface_fit_support_samples": len(support_samples),
    },
    "smoothing": {
        "iterations": iterations,
        "strength": strength,
        "axis_scale_xyz": list(axis_scale),
        "surface_pull": surface_pull,
        "surface_fit_coefficients": surface_coefficients,
        "per_iteration_max_delta_meters": per_iteration_max_delta,
    },
    "movement": {
        "moved_vertices": len(movement_lengths),
        "max_meters": max(movement_lengths, default=0.0),
        "mean_meters": statistics.fmean(movement_lengths)
        if movement_lengths
        else 0.0,
        "protected_vertices_moved": len(distal_changed),
        "outside_weighted_region_vertices_moved": len(outside_changed),
    },
    "topology_before": before_topology,
    "topology_after": after_topology,
    "topology_preserved": before_topology == after_topology,
    "visual_review_required": True,
}
(OUT / "LOCAL_TRANSITION_SMOOTHING_TRIAL_REPORT.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)
print(blend_path)
