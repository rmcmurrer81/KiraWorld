"""Build a diagnostic-only V18-to-clean-head surface-fit alignment.

This does not create an owner-review avatar candidate.  It aligns the
preferred V15/V18 head direction to the clean connected MakeHuman foundation
using stable anatomical landmarks, renders solid/wire diagnostics, and records
correspondence error before any displacement field is allowed to touch the
clean topology.

Run with Blender 5.1:

    blender --background --python \
      tools/blender_build_robert_v18_face_surface_fit_diagnostic.py
"""

from __future__ import annotations

from collections import deque
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "biological_static_likeness_v25_r7_makehuman_cc0_private_fit"
)
CLEAN_BLEND = SOURCE_DIR / "MAKEHUMAN_CC0_PARAMETRIC_MALE_FOUNDATION.blend"
V18_BLEND = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "biological_static_likeness_v18_from_v15"
    / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V18_FROM_V15.blend"
)
OUT = SOURCE_DIR / "face_surface_fit_diagnostic_v8"
REPORT_PATH = OUT / "V18_CLEAN_HEAD_LANDMARK_ALIGNMENT_REPORT.json"
DIAGNOSTIC_BLEND = OUT / "V18_LOCALIZED_WARP_DIAGNOSTIC_ONLY.blend"
STATUS = "DIAGNOSTIC_ONLY_NOT_OWNER_CANDIDATE"
FACE_CUTOFF_Z = 6.45
V8_LOCAL_FEATURE_TARGETS: tuple[
    tuple[str, float, str, str], ...
] = (
    (
        "eyes/l-eye-scale-incr.target",
        0.04,
        "left_eye_aperture",
        "bounded opening of the naturally hooded left eye",
    ),
    (
        "eyes/r-eye-scale-incr.target",
        0.04,
        "right_eye_aperture",
        "bounded opening of the naturally hooded right eye",
    ),
    (
        "eyes/l-eye-height1-incr.target",
        0.16,
        "left_eye_aperture",
        "left outer aperture height",
    ),
    (
        "eyes/l-eye-height2-incr.target",
        0.16,
        "left_eye_aperture",
        "left central aperture height",
    ),
    (
        "eyes/l-eye-height3-incr.target",
        0.16,
        "left_eye_aperture",
        "left inner aperture height",
    ),
    (
        "eyes/r-eye-height1-incr.target",
        0.16,
        "right_eye_aperture",
        "right outer aperture height",
    ),
    (
        "eyes/r-eye-height2-incr.target",
        0.16,
        "right_eye_aperture",
        "right central aperture height",
    ),
    (
        "eyes/r-eye-height3-incr.target",
        0.16,
        "right_eye_aperture",
        "right inner aperture height",
    ),
    (
        "eyes/l-eye-eyefold-down.target",
        0.02,
        "left_brow_lid_contour",
        "retain a low natural upper-lid fold",
    ),
    (
        "eyes/r-eye-eyefold-down.target",
        0.02,
        "right_brow_lid_contour",
        "retain a low natural upper-lid fold",
    ),
    (
        "eyes/l-eye-bag-incr.target",
        0.03,
        "left_brow_lid_contour",
        "adult lower-eye structure",
    ),
    (
        "eyes/r-eye-bag-incr.target",
        0.03,
        "right_brow_lid_contour",
        "adult lower-eye structure",
    ),
    (
        "eyebrows/eyebrows-trans-down.target",
        0.015,
        "brow_contour",
        "Robert's comparatively low horizontal brow placement",
    ),
    (
        "eyebrows/eyebrows-angle-down.target",
        0.012,
        "brow_contour",
        "bounded outer-brow contour",
    ),
    (
        "nose/nose-scale-depth-decr.target",
        0.035,
        "nose_profile",
        "moderate rather than sharp profile projection",
    ),
    (
        "nose/nose-point-width-incr.target",
        0.025,
        "nose_front",
        "rounded nasal tip",
    ),
    (
        "nose/nose-nostrils-width-incr.target",
        0.02,
        "nose_front",
        "bounded nostril-base width",
    ),
    (
        "cheek/l-cheek-volume-decr.target",
        0.04,
        "left_cheek_distribution",
        "redistribute left cheek fullness without global thinning",
    ),
    (
        "cheek/r-cheek-volume-decr.target",
        0.04,
        "right_cheek_distribution",
        "redistribute right cheek fullness without global thinning",
    ),
    (
        "chin/chin-width-incr.target",
        0.05,
        "chin_lower_face",
        "broader rounded chin",
    ),
    (
        "chin/chin-height-decr.target",
        0.04,
        "chin_lower_face",
        "avoid a long pointed lower face",
    ),
    (
        "chin/chin-prominent-decr.target",
        0.025,
        "chin_lower_face",
        "bounded profile recession",
    ),
    (
        "neck/neck-scale-horiz-decr.target",
        0.01,
        "upper_neck_transition",
        "small upper-neck transition refinement",
    ),
)


def load_personalizer():
    path = ROOT / "tools" / "blender_personalize_biological_robert_makehuman_v25.py"
    spec = importlib.util.spec_from_file_location("robert_v25_personalizer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load personalizer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P = load_personalizer()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def world_points(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def material_vertex_indices(
    obj: bpy.types.Object, material_names: set[str]
) -> set[int]:
    wanted = {
        index
        for index, material in enumerate(obj.data.materials)
        if material is not None and material.name in material_names
    }
    indices: set[int] = set()
    for polygon in obj.data.polygons:
        if polygon.material_index in wanted:
            indices.update(polygon.vertices)
    return indices


def restricted_components(
    obj: bpy.types.Object, indices: set[int]
) -> list[list[int]]:
    adjacency: dict[int, set[int]] = {index: set() for index in indices}
    for edge in obj.data.edges:
        left, right = edge.vertices
        if left in indices and right in indices:
            adjacency[left].add(right)
            adjacency[right].add(left)
    unseen = set(indices)
    components: list[list[int]] = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        component = [seed]
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
                    component.append(other)
        components.append(component)
    components.sort(key=len, reverse=True)
    return components


def component_centers(
    obj: bpy.types.Object, material_names: set[str]
) -> list[tuple[int, Vector]]:
    points = world_points(obj)
    components = restricted_components(
        obj, material_vertex_indices(obj, material_names)
    )
    rows: list[tuple[int, Vector]] = []
    for component in components:
        if not component:
            continue
        center = sum((points[index] for index in component), Vector()) / len(
            component
        )
        rows.append((len(component), center))
    return rows


def primary_skin_geometry(
    obj: bpy.types.Object,
) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    points = world_points(obj)
    # V18's historical joined mesh retained material slots but not reliable
    # per-polygon material assignment across every face. Its topology report
    # establishes that the largest connected component is the primary skin.
    # Select that component directly rather than silently dropping the head.
    components = restricted_components(
        obj, set(range(len(obj.data.vertices)))
    )
    if not components:
        raise RuntimeError("V18 reference contains no connected components")
    primary_skin = set(components[0])
    faces: list[tuple[int, int, int]] = []
    for polygon in obj.data.polygons:
        vertices = list(polygon.vertices)
        if not vertices or not all(index in primary_skin for index in vertices):
            continue
        if len(vertices) < 3:
            continue
        for index in range(1, len(vertices) - 1):
            faces.append((vertices[0], vertices[index], vertices[index + 1]))
    if not faces:
        raise RuntimeError("V18 reference primary skin contains no faces")
    print(
        "REFERENCE_COMPONENTS",
        len(components),
        [len(component) for component in components[:8]],
        "primary_faces",
        len(faces),
    )
    return points, faces


def average_top(points: list[Vector], *, count: int = 24) -> Vector:
    selected = sorted(points, key=lambda point: point.z, reverse=True)[:count]
    return sum(selected, Vector()) / len(selected)


def average_extreme(
    points: list[Vector],
    *,
    axis: int,
    reverse: bool,
    count: int,
) -> Vector:
    selected = sorted(
        points, key=lambda point: point[axis], reverse=reverse
    )[:count]
    return sum(selected, Vector()) / len(selected)


def nearest_to_goal(
    points: list[Vector],
    goal: Vector,
    *,
    x_weight: float = 1.0,
    y_weight: float = 0.30,
    z_weight: float = 1.0,
) -> Vector:
    return min(
        points,
        key=lambda point: (
            ((point.x - goal.x) * x_weight) ** 2
            + ((point.y - goal.y) * y_weight) ** 2
            + ((point.z - goal.z) * z_weight) ** 2
        ),
    )


def derive_landmarks(
    skin_points: list[Vector],
    eye_centers: tuple[Vector, Vector],
) -> dict[str, Vector]:
    negative_eye, positive_eye = sorted(eye_centers, key=lambda point: point.x)
    eye_mid = (negative_eye + positive_eye) * 0.5
    iod = abs(positive_eye.x - negative_eye.x)
    if iod <= 1e-6:
        raise RuntimeError("invalid zero interocular distance")
    head = [
        point
        for point in skin_points
        if point.z >= eye_mid.z - iod * 2.25
        and abs(point.x - eye_mid.x) <= iod * 2.25
    ]
    if len(head) < 100:
        raise RuntimeError(f"head subset too small: {len(head)}")
    crown = average_top(
        [
            point
            for point in head
            if abs(point.x - eye_mid.x) <= iod * 0.65
        ]
    )
    central_face = [
        point
        for point in head
        if abs(point.x - eye_mid.x) <= iod * 0.22
        and eye_mid.z - iod * 1.05 <= point.z <= eye_mid.z - iod * 0.18
    ]
    nose_tip = average_extreme(
        central_face, axis=1, reverse=False, count=min(16, len(central_face))
    )
    nose_base_goal = Vector(
        (eye_mid.x, nose_tip.y, eye_mid.z - iod * 0.77)
    )
    nose_base = nearest_to_goal(
        [
            point
            for point in central_face
            if eye_mid.z - iod * 0.95 <= point.z <= eye_mid.z - iod * 0.58
        ],
        nose_base_goal,
        y_weight=0.18,
    )
    mouth_z = eye_mid.z - iod * 1.12
    mouth_front_y = nose_tip.y + iod * 0.18
    mouth_band = [
        point
        for point in head
        if abs(point.x - eye_mid.x) <= iod * 0.78
        and mouth_z - iod * 0.18 <= point.z <= mouth_z + iod * 0.18
    ]
    mouth_negative = nearest_to_goal(
        mouth_band,
        Vector((eye_mid.x - iod * 0.48, mouth_front_y, mouth_z)),
        y_weight=0.18,
    )
    mouth_positive = nearest_to_goal(
        mouth_band,
        Vector((eye_mid.x + iod * 0.48, mouth_front_y, mouth_z)),
        y_weight=0.18,
    )
    chin_band = [
        point
        for point in head
        if abs(point.x - eye_mid.x) <= iod * 0.48
        and eye_mid.z - iod * 2.05 <= point.z <= eye_mid.z - iod * 1.35
        and point.y <= eye_mid.y + iod * 0.55
    ]
    chin = average_extreme(
        chin_band, axis=2, reverse=False, count=min(24, len(chin_band))
    )
    jaw_z = eye_mid.z - iod * 1.55
    jaw_band = [
        point
        for point in head
        if jaw_z - iod * 0.20 <= point.z <= jaw_z + iod * 0.20
        and point.y <= eye_mid.y + iod * 0.70
    ]
    jaw_negative = average_extreme(
        jaw_band, axis=0, reverse=False, count=min(24, len(jaw_band))
    )
    jaw_positive = average_extreme(
        jaw_band, axis=0, reverse=True, count=min(24, len(jaw_band))
    )
    ear_band = [
        point
        for point in head
        if eye_mid.z - iod * 0.65 <= point.z <= eye_mid.z + iod * 0.45
    ]
    ear_negative = average_extreme(
        ear_band, axis=0, reverse=False, count=min(32, len(ear_band))
    )
    ear_positive = average_extreme(
        ear_band, axis=0, reverse=True, count=min(32, len(ear_band))
    )
    cheek_z = eye_mid.z - iod * 0.48
    cheek_front_y = nose_tip.y + iod * 0.34
    cheek_band = [
        point
        for point in head
        if eye_mid.z - iod * 0.72 <= point.z <= eye_mid.z - iod * 0.22
        and abs(point.x - eye_mid.x) <= iod * 1.25
    ]
    cheek_negative = nearest_to_goal(
        cheek_band,
        Vector((eye_mid.x - iod * 0.82, cheek_front_y, cheek_z)),
        y_weight=0.30,
    )
    cheek_positive = nearest_to_goal(
        cheek_band,
        Vector((eye_mid.x + iod * 0.82, cheek_front_y, cheek_z)),
        y_weight=0.30,
    )
    temple_z = eye_mid.z + iod * 0.38
    temple_band = [
        point
        for point in head
        if eye_mid.z + iod * 0.12 <= point.z <= eye_mid.z + iod * 0.68
    ]
    temple_negative = nearest_to_goal(
        temple_band,
        Vector((eye_mid.x - iod * 1.20, eye_mid.y + iod * 0.18, temple_z)),
        y_weight=0.25,
    )
    temple_positive = nearest_to_goal(
        temple_band,
        Vector((eye_mid.x + iod * 1.20, eye_mid.y + iod * 0.18, temple_z)),
        y_weight=0.25,
    )
    forehead_z = eye_mid.z + iod * 1.02
    forehead_band = [
        point
        for point in head
        if eye_mid.z + iod * 0.75 <= point.z <= eye_mid.z + iod * 1.28
        and abs(point.x - eye_mid.x) <= iod * 1.15
    ]
    forehead_negative = nearest_to_goal(
        forehead_band,
        Vector((eye_mid.x - iod * 0.58, eye_mid.y + iod * 0.20, forehead_z)),
        y_weight=0.22,
    )
    forehead_positive = nearest_to_goal(
        forehead_band,
        Vector((eye_mid.x + iod * 0.58, eye_mid.y + iod * 0.20, forehead_z)),
        y_weight=0.22,
    )
    upper_lip = nearest_to_goal(
        mouth_band,
        Vector((eye_mid.x, mouth_front_y, mouth_z + iod * 0.055)),
        y_weight=0.15,
    )
    lower_lip = nearest_to_goal(
        mouth_band,
        Vector((eye_mid.x, mouth_front_y, mouth_z - iod * 0.065)),
        y_weight=0.15,
    )
    return {
        "eye_negative_x": negative_eye,
        "eye_positive_x": positive_eye,
        "eye_midpoint": eye_mid,
        "crown": crown,
        "nose_tip": nose_tip,
        "nose_base": nose_base,
        "mouth_negative_x": mouth_negative,
        "mouth_positive_x": mouth_positive,
        "chin": chin,
        "jaw_negative_x": jaw_negative,
        "jaw_positive_x": jaw_positive,
        "ear_negative_x": ear_negative,
        "ear_positive_x": ear_positive,
        "cheekbone_negative_x": cheek_negative,
        "cheekbone_positive_x": cheek_positive,
        "temple_negative_x": temple_negative,
        "temple_positive_x": temple_positive,
        "forehead_negative_x": forehead_negative,
        "forehead_positive_x": forehead_positive,
        "upper_lip_center": upper_lip,
        "lower_lip_center": lower_lip,
    }


def head_depth(
    points: list[Vector], eye_mid: Vector, iod: float
) -> tuple[float, float, float]:
    band = [
        point
        for point in points
        if eye_mid.z - iod * 0.55 <= point.z <= eye_mid.z + iod * 0.55
        and abs(point.x - eye_mid.x) <= iod * 1.65
    ]
    minimum = min(point.y for point in band)
    maximum = max(point.y for point in band)
    return minimum, maximum, maximum - minimum


def diagonal_alignment(
    current: dict[str, Vector],
    reference: dict[str, Vector],
    current_skin: list[Vector],
    reference_skin: list[Vector],
) -> dict[str, object]:
    current_iod = abs(
        current["eye_positive_x"].x - current["eye_negative_x"].x
    )
    reference_iod = abs(
        reference["eye_positive_x"].x - reference["eye_negative_x"].x
    )
    scale_x = current_iod / reference_iod
    # Keep both eye centers exact, then solve one bounded vertical scale over
    # the stable crown/central-face/lower-face landmarks.  Crown-only scaling
    # aligned the skull top but left V18's nose, mouth, jaw, and chin roughly
    # 0.06-0.12 clean-head units too high.
    vertical_weights = {
        "crown": 2.0,
        "nose_tip": 1.5,
        "nose_base": 2.0,
        "mouth_negative_x": 2.0,
        "mouth_positive_x": 2.0,
        "upper_lip_center": 2.0,
        "lower_lip_center": 2.0,
        "chin": 3.0,
        "jaw_negative_x": 2.0,
        "jaw_positive_x": 2.0,
    }
    numerator = 0.0
    denominator = 0.0
    for name, weight in vertical_weights.items():
        reference_delta = (
            reference[name].z - reference["eye_midpoint"].z
        )
        current_delta = current[name].z - current["eye_midpoint"].z
        numerator += weight * reference_delta * current_delta
        denominator += weight * reference_delta * reference_delta
    if denominator <= 1e-12:
        raise RuntimeError("invalid vertical landmark scale denominator")
    scale_z = numerator / denominator
    _, _, current_depth = head_depth(
        current_skin, current["eye_midpoint"], current_iod
    )
    _, _, reference_depth = head_depth(
        reference_skin, reference["eye_midpoint"], reference_iod
    )
    scale_y = current_depth / reference_depth
    scales = Vector((scale_x, scale_y, scale_z))
    reference_anchor = reference["eye_midpoint"]
    current_anchor = current["eye_midpoint"]
    return {
        "scales": scales,
        "reference_anchor": reference_anchor,
        "current_anchor": current_anchor,
        "current_interocular_distance": current_iod,
        "reference_interocular_distance": reference_iod,
        "current_head_depth": current_depth,
        "reference_head_depth": reference_depth,
        "vertical_scale_landmark_weights": vertical_weights,
    }


def transform_point(point: Vector, alignment: dict[str, object]) -> Vector:
    scales: Vector = alignment["scales"]
    reference_anchor: Vector = alignment["reference_anchor"]
    current_anchor: Vector = alignment["current_anchor"]
    delta = point - reference_anchor
    return Vector(
        (
            current_anchor.x + delta.x * scales.x,
            current_anchor.y + delta.y * scales.y,
            current_anchor.z + delta.z * scales.z,
        )
    )


def vector_row(point: Vector) -> list[float]:
    return [float(point.x), float(point.y), float(point.z)]


def landmark_error_rows(
    current: dict[str, Vector],
    aligned_reference: dict[str, Vector],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name in current:
        if name == "eye_midpoint":
            continue
        delta = aligned_reference[name] - current[name]
        rows.append(
            {
                "landmark": name,
                "current": vector_row(current[name]),
                "aligned_reference": vector_row(aligned_reference[name]),
                "delta": vector_row(delta),
                "distance": float(delta.length),
            }
        )
    return rows


def symmetric_control_goals(
    current: dict[str, Vector],
    aligned_reference: dict[str, Vector],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    confidences = {
        "eye_negative_x": 1.0,
        "eye_positive_x": 1.0,
        "crown": 0.70,
        "nose_tip": 0.85,
        "nose_base": 0.85,
        "mouth_negative_x": 0.90,
        "mouth_positive_x": 0.90,
        "upper_lip_center": 0.92,
        "lower_lip_center": 0.92,
        "chin": 0.85,
        "jaw_negative_x": 0.85,
        "jaw_positive_x": 0.85,
        "ear_negative_x": 0.18,
        "ear_positive_x": 0.18,
        "cheekbone_negative_x": 0.78,
        "cheekbone_positive_x": 0.78,
        "temple_negative_x": 0.75,
        "temple_positive_x": 0.75,
        "forehead_negative_x": 0.70,
        "forehead_positive_x": 0.70,
    }
    paired = [
        ("eye_negative_x", "eye_positive_x"),
        ("mouth_negative_x", "mouth_positive_x"),
        ("jaw_negative_x", "jaw_positive_x"),
        ("ear_negative_x", "ear_positive_x"),
        ("cheekbone_negative_x", "cheekbone_positive_x"),
        ("temple_negative_x", "temple_positive_x"),
        ("forehead_negative_x", "forehead_positive_x"),
    ]
    pair_names = {name for pair in paired for name in pair}
    rows: dict[str, dict[str, object]] = {}
    pair_report: list[dict[str, str]] = []
    for negative_name, positive_name in paired:
        negative_delta = (
            aligned_reference[negative_name] - current[negative_name]
        )
        positive_delta = (
            aligned_reference[positive_name] - current[positive_name]
        )
        outward_x = ((-negative_delta.x) + positive_delta.x) * 0.5
        common_y = (negative_delta.y + positive_delta.y) * 0.5
        common_z = (negative_delta.z + positive_delta.z) * 0.5
        if negative_name.startswith("ear_"):
            # Ear extrema are useful for head width and vertical seating, but
            # the earlier heuristic produced an implausible long depth vector.
            # Do not let an uncertain ear-depth sample pull the whole side of
            # the head forward or backward.
            common_y = 0.0
        negative_symmetric = Vector((-outward_x, common_y, common_z))
        positive_symmetric = Vector((outward_x, common_y, common_z))
        for name, delta in (
            (negative_name, negative_symmetric),
            (positive_name, positive_symmetric),
        ):
            confidence = confidences[name]
            applied_delta = delta * confidence
            rows[name] = {
                "name": name,
                "current": current[name].copy(),
                "raw_reference_goal": aligned_reference[name].copy(),
                "symmetric_delta": delta,
                "confidence": confidence,
                "applied_goal": current[name] + applied_delta,
            }
        pair_report.append(
            {
                "negative_x": negative_name,
                "positive_x": positive_name,
            }
        )
    for name, current_point in current.items():
        if name in pair_names or name == "eye_midpoint":
            continue
        delta = aligned_reference[name] - current_point
        # Central controls may not introduce an unexplained lateral identity
        # drift. Retain their measured depth/height goal only.
        delta.x = 0.0
        confidence = confidences.get(name, 0.55)
        rows[name] = {
            "name": name,
            "current": current_point.copy(),
            "raw_reference_goal": aligned_reference[name].copy(),
            "symmetric_delta": delta,
            "confidence": confidence,
            "applied_goal": current_point + delta * confidence,
        }
    ordered = [rows[name] for name in sorted(rows)]
    return ordered, pair_report


def point_signature(points: list[Vector]) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(
            f"{point.x:.7f},{point.y:.7f},{point.z:.7f}\n".encode("ascii")
        )
    return digest.hexdigest()


def apply_localized_rbf_warp(
    body: bpy.types.Object,
    controls: list[dict[str, object]],
    *,
    interocular_distance: float,
    radius_factor: float,
    maximum_displacement_factor: float,
    stage_name: str,
) -> dict[str, object]:
    control_points = np.array(
        [vector_row(row["current"]) for row in controls], dtype=np.float64
    )
    displacements = np.array(
        [
            vector_row(row["applied_goal"] - row["current"])
            for row in controls
        ],
        dtype=np.float64,
    )
    radius = interocular_distance * radius_factor
    pair_distances = np.linalg.norm(
        control_points[:, None, :] - control_points[None, :, :], axis=2
    )
    kernel_base = np.exp(-((pair_distances / radius) ** 2))
    regularization = 2.5e-4
    system_kernel = (
        kernel_base
        + np.eye(len(controls), dtype=np.float64) * regularization
    )
    coefficients = np.linalg.solve(system_kernel, displacements)

    lower_before = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_before = point_signature(lower_before)
    changed: list[int] = []
    lengths: list[float] = []
    maximum_allowed = interocular_distance * maximum_displacement_factor
    for vertex in body.data.vertices:
        if vertex.co.z < FACE_CUTOFF_Z:
            continue
        point = np.array(vector_row(vertex.co), dtype=np.float64)
        distances = np.linalg.norm(control_points - point[None, :], axis=1)
        basis = np.exp(-((distances / radius) ** 2))
        displacement = basis @ coefficients
        neck_t = min(
            1.0, max(0.0, (float(vertex.co.z) - FACE_CUTOFF_Z) / 0.72)
        )
        neck_weight = neck_t * neck_t * (3.0 - 2.0 * neck_t)
        displacement *= neck_weight
        length = float(np.linalg.norm(displacement))
        if length > maximum_allowed and length > 1e-12:
            displacement *= maximum_allowed / length
            length = maximum_allowed
        if length <= 1e-8:
            continue
        vertex.co += Vector(tuple(float(value) for value in displacement))
        changed.append(vertex.index)
        lengths.append(length)
    body.data.update()
    lower_after = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_after = point_signature(lower_after)
    lower_unchanged = (
        len(lower_before) == len(lower_after)
        and lower_signature_before == lower_signature_after
    )
    if not lower_unchanged:
        raise RuntimeError("localized face RBF altered frozen lower-body vertices")

    # Evaluate against the unregularized basis.  Using the solved system
    # matrix here previously made residuals appear effectively zero even when
    # the regularized field did not exactly reach the requested controls.
    control_predictions = kernel_base @ coefficients
    control_residuals = np.linalg.norm(
        control_predictions - displacements, axis=1
    )
    group = body.vertex_groups.new(name="Diagnostic_V18_Localized_Face_Warp")
    if changed:
        group.add(changed, 1.0, "REPLACE")
    return {
        "method": "regularized Gaussian RBF over symmetric local landmarks",
        "stage_name": stage_name,
        "radius": radius,
        "radius_factor_over_interocular_distance": radius_factor,
        "regularization": regularization,
        "maximum_allowed_displacement": maximum_allowed,
        "changed_vertices": len(changed),
        "maximum_vertex_displacement": max(lengths, default=0.0),
        "mean_vertex_displacement": (
            sum(lengths) / len(lengths) if lengths else 0.0
        ),
        "control_residuals": quantiles(
            [float(value) for value in control_residuals]
        ),
        "neck_freeze": {
            "cutoff_z": FACE_CUTOFF_Z,
            "smooth_falloff_distance": 0.72,
        },
        "lower_body_pelvis_anatomy_invariant": {
            "vertex_count": len(lower_before),
            "signature_before": lower_signature_before,
            "signature_after": lower_signature_after,
            "unchanged": lower_unchanged,
        },
    }


def mesh_vertex_adjacency(
    obj: bpy.types.Object,
) -> list[list[int]]:
    adjacency: list[set[int]] = [
        set() for _ in range(len(obj.data.vertices))
    ]
    for edge in obj.data.edges:
        left, right = edge.vertices
        adjacency[left].add(right)
        adjacency[right].add(left)
    return [sorted(row) for row in adjacency]


def apply_bounded_surface_relaxation(
    body: bpy.types.Object,
    bvh: BVHTree,
    *,
    eye_midpoint: Vector,
    interocular_distance: float,
    iterations: int = 2,
) -> dict[str, object]:
    """Relax the clean topology toward V18 without transplanting topology.

    The landmark RBF establishes stable identity correspondence first.  This
    second diagnostic stage reduces broad surface error while preserving
    feature cavities, fading smoothly through the upper neck, and rejecting
    distant or normal-incompatible nearest-surface matches.
    """

    adjacency = mesh_vertex_adjacency(body)
    minimum_relax_z = max(
        FACE_CUTOFF_Z,
        float(eye_midpoint.z - interocular_distance * 2.22),
    )
    maximum_nearest_distance = interocular_distance * 0.34
    maximum_step = interocular_distance * 0.035
    lower_before = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_before = point_signature(lower_before)
    iteration_reports: list[dict[str, object]] = []
    all_changed: set[int] = set()

    for iteration in range(iterations):
        body.data.update()
        desired: list[Vector] = [
            Vector() for _ in range(len(body.data.vertices))
        ]
        active: set[int] = set()
        rejected_distance = 0
        rejected_normal = 0
        rejected_feature_cavity = 0
        raw_lengths: list[float] = []
        for vertex in body.data.vertices:
            point = vertex.co
            if point.z < minimum_relax_z:
                continue
            nearest = bvh.find_nearest(point)
            if (
                nearest is None
                or nearest[0] is None
                or nearest[1] is None
                or nearest[3] is None
            ):
                continue
            location, reference_normal, _, distance = nearest
            if float(distance) > maximum_nearest_distance:
                rejected_distance += 1
                continue
            current_normal = vertex.normal.normalized()
            reference_normal = reference_normal.normalized()
            if current_normal.dot(reference_normal) < 0.18:
                rejected_normal += 1
                continue
            # Preserve deep eye sockets, nostrils, and the inner mouth.  The
            # outer skin in those bands was already placed by named controls.
            eye_band = (
                abs(point.z - eye_midpoint.z)
                <= interocular_distance * 0.34
                and abs(point.x) <= interocular_distance * 0.90
            )
            central_feature_band = (
                abs(point.x) <= interocular_distance * 0.62
                and eye_midpoint.z - interocular_distance * 1.42
                <= point.z
                <= eye_midpoint.z - interocular_distance * 0.28
            )
            ear_band = (
                abs(point.x) >= interocular_distance * 1.12
                and abs(point.z - eye_midpoint.z)
                <= interocular_distance * 0.82
            )
            if eye_band or central_feature_band or ear_band:
                rejected_feature_cavity += 1
                continue
            neck_t = min(
                1.0,
                max(
                    0.0,
                    (float(point.z) - minimum_relax_z)
                    / (interocular_distance * 0.85),
                ),
            )
            neck_weight = neck_t * neck_t * (3.0 - 2.0 * neck_t)
            displacement = (location - point) * neck_weight * 0.40
            length = displacement.length
            if length > maximum_step and length > 1e-12:
                displacement *= maximum_step / length
                length = maximum_step
            if length <= 1e-8:
                continue
            desired[vertex.index] = displacement
            active.add(vertex.index)
            raw_lengths.append(float(length))

        # One-ring smoothing prevents nearest-triangle faceting while
        # retaining 72% of each locally measured displacement.
        smoothed = [row.copy() for row in desired]
        for index in active:
            neighbors = adjacency[index]
            if not neighbors:
                continue
            neighbor_mean = sum(
                (desired[neighbor] for neighbor in neighbors),
                Vector(),
            ) / len(neighbors)
            smoothed[index] = desired[index] * 0.72 + neighbor_mean * 0.28

        applied_lengths: list[float] = []
        for index in active:
            displacement = smoothed[index]
            length = displacement.length
            if length <= 1e-8:
                continue
            body.data.vertices[index].co += displacement
            applied_lengths.append(float(length))
            all_changed.add(index)
        body.data.update()
        iteration_reports.append(
            {
                "iteration": iteration + 1,
                "active_vertices": len(active),
                "rejected_distant_correspondence": rejected_distance,
                "rejected_normal_incompatibility": rejected_normal,
                "rejected_feature_cavity": rejected_feature_cavity,
                "raw_step_lengths": quantiles(raw_lengths),
                "applied_step_lengths": quantiles(applied_lengths),
            }
        )

    lower_after = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_after = point_signature(lower_after)
    lower_unchanged = (
        len(lower_before) == len(lower_after)
        and lower_signature_before == lower_signature_after
    )
    if not lower_unchanged:
        raise RuntimeError(
            "surface relaxation altered frozen lower-body vertices"
        )
    group = body.vertex_groups.new(
        name="Diagnostic_V18_Bounded_Surface_Relaxation"
    )
    if all_changed:
        group.add(sorted(all_changed), 1.0, "REPLACE")
    return {
        "method": (
            "bounded nearest-surface relaxation after landmark RBF; "
            "topology-preserving diagnostic only"
        ),
        "iterations": iteration_reports,
        "minimum_relax_z": minimum_relax_z,
        "maximum_nearest_distance": maximum_nearest_distance,
        "maximum_step_per_iteration": maximum_step,
        "changed_vertices": len(all_changed),
        "lower_body_pelvis_anatomy_invariant": {
            "vertex_count": len(lower_before),
            "signature_before": lower_signature_before,
            "signature_after": lower_signature_after,
            "unchanged": lower_unchanged,
        },
    }


def deformation_quality(
    original: bpy.types.Object,
    deformed: bpy.types.Object,
    *,
    minimum_z: float,
) -> dict[str, object]:
    if len(original.data.vertices) != len(deformed.data.vertices):
        raise RuntimeError("deformation quality requires identical topology")
    flipped = 0
    near_zero = 0
    area_ratios: list[float] = []
    sampled_triangles = 0
    for polygon in original.data.polygons:
        indices = list(polygon.vertices)
        if len(indices) < 3:
            continue
        if max(original.data.vertices[index].co.z for index in indices) < minimum_z:
            continue
        for offset in range(1, len(indices) - 1):
            tri = (indices[0], indices[offset], indices[offset + 1])
            before = [
                original.data.vertices[index].co for index in tri
            ]
            after = [
                deformed.data.vertices[index].co for index in tri
            ]
            before_cross = (before[1] - before[0]).cross(
                before[2] - before[0]
            )
            after_cross = (after[1] - after[0]).cross(
                after[2] - after[0]
            )
            before_area = before_cross.length * 0.5
            after_area = after_cross.length * 0.5
            sampled_triangles += 1
            if before_area <= 1e-12:
                continue
            ratio = after_area / before_area
            area_ratios.append(float(ratio))
            if after_area <= 1e-10:
                near_zero += 1
            elif before_cross.dot(after_cross) < 0.0:
                flipped += 1
    return {
        "sampled_triangles": sampled_triangles,
        "flipped_triangle_count": flipped,
        "near_zero_area_triangle_count": near_zero,
        "triangle_area_ratio": quantiles(area_ratios),
        "topology_vertex_count_unchanged": (
            len(original.data.vertices) == len(deformed.data.vertices)
        ),
        "topology_polygon_count_unchanged": (
            len(original.data.polygons) == len(deformed.data.polygons)
        ),
    }


def gaussian_weight(value: float, center: float, sigma: float) -> float:
    if sigma <= 1e-12:
        return 0.0
    normalized = (value - center) / sigma
    return math.exp(-0.5 * normalized * normalized)


def face_shape_measurements(
    landmarks: dict[str, Vector],
    body: bpy.types.Object,
    *,
    interocular_distance: float,
) -> dict[str, float]:
    cheek_width = (
        landmarks["cheekbone_positive_x"].x
        - landmarks["cheekbone_negative_x"].x
    )
    jaw_width = (
        landmarks["jaw_positive_x"].x
        - landmarks["jaw_negative_x"].x
    )
    mouth_center = (
        landmarks["upper_lip_center"] + landmarks["lower_lip_center"]
    ) * 0.5
    cheek_y = (
        landmarks["cheekbone_positive_x"].y
        + landmarks["cheekbone_negative_x"].y
    ) * 0.5
    neck_band_minimum_z = (
        landmarks["chin"].z - interocular_distance * 0.20
    )
    neck_band_maximum_z = (
        landmarks["chin"].z - interocular_distance * 0.08
    )
    neck_band = [
        vertex.co
        for vertex in body.data.vertices
        if neck_band_minimum_z
        <= vertex.co.z
        <= neck_band_maximum_z
    ]
    neck_width = (
        max(point.x for point in neck_band)
        - min(point.x for point in neck_band)
        if neck_band
        else 0.0
    )
    return {
        "cheek_width": float(cheek_width),
        "jaw_width": float(jaw_width),
        "jaw_width_over_cheek_width": float(
            jaw_width / cheek_width if cheek_width else 0.0
        ),
        "lower_face_height_over_cheek_width": float(
            (mouth_center.z - landmarks["chin"].z) / cheek_width
            if cheek_width
            else 0.0
        ),
        "chin_recession_from_mouth_over_interocular_distance": float(
            (landmarks["chin"].y - mouth_center.y)
            / interocular_distance
        ),
        "cheek_y_minus_eye_y_over_interocular_distance": float(
            (cheek_y - landmarks["eye_midpoint"].y)
            / interocular_distance
        ),
        "upper_neck_width": float(neck_width),
        "upper_neck_measurement_minimum_z": float(
            neck_band_minimum_z
        ),
        "upper_neck_measurement_maximum_z": float(
            neck_band_maximum_z
        ),
        "upper_neck_width_over_cheek_width": float(
            neck_width / cheek_width if cheek_width else 0.0
        ),
    }


def apply_photo_ratio_anti_puffiness(
    body: bpy.types.Object,
    *,
    landmarks: dict[str, Vector],
    interocular_distance: float,
) -> dict[str, object]:
    """Apply one bounded owner-evidence corrective layer to mapped topology."""

    eye_mid = landmarks["eye_midpoint"]
    lower_before = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_before = point_signature(lower_before)
    changed: list[int] = []
    displacement_lengths: list[float] = []
    region_weight_sums = {
        "cheek_depth_and_width": 0.0,
        "jaw_width": 0.0,
        "chin_and_lower_face": 0.0,
        "upper_neck_transition": 0.0,
    }
    maximum_displacement = interocular_distance * 0.045
    for vertex in body.data.vertices:
        point = vertex.co
        if point.z < FACE_CUTOFF_Z:
            continue
        abs_x = abs(float(point.x))
        front_threshold = (
            eye_mid.y + interocular_distance * 0.62
        )
        front_weight = min(
            1.0,
            max(
                0.0,
                (front_threshold - float(point.y))
                / (interocular_distance * 0.62),
            ),
        )
        cheek_weight = (
            gaussian_weight(
                abs_x,
                interocular_distance * 0.72,
                interocular_distance * 0.30,
            )
            * gaussian_weight(
                float(point.z),
                eye_mid.z - interocular_distance * 0.55,
                interocular_distance * 0.42,
            )
            * front_weight
        )
        jaw_weight = (
            gaussian_weight(
                abs_x,
                interocular_distance * 0.72,
                interocular_distance * 0.36,
            )
            * gaussian_weight(
                float(point.z),
                eye_mid.z - interocular_distance * 1.47,
                interocular_distance * 0.36,
            )
            * front_weight
        )
        chin_weight = (
            gaussian_weight(
                abs_x,
                0.0,
                interocular_distance * 0.56,
            )
            * gaussian_weight(
                float(point.z),
                eye_mid.z - interocular_distance * 1.86,
                interocular_distance * 0.31,
            )
            * front_weight
        )
        neck_weight = (
            gaussian_weight(
                float(point.z),
                FACE_CUTOFF_Z + interocular_distance * 0.47,
                interocular_distance * 0.34,
            )
            * min(1.0, abs_x / (interocular_distance * 0.55))
        )
        sign_x = -1.0 if point.x < 0.0 else 1.0
        displacement = Vector(
            (
                -sign_x
                * abs_x
                * (
                    0.028 * cheek_weight
                    + 0.025 * jaw_weight
                    + 0.015 * neck_weight
                ),
                interocular_distance
                * (
                    0.018 * cheek_weight
                    + 0.012 * jaw_weight
                    + 0.014 * chin_weight
                ),
                interocular_distance * 0.008 * chin_weight,
            )
        )
        length = displacement.length
        if length > maximum_displacement and length > 1e-12:
            displacement *= maximum_displacement / length
            length = maximum_displacement
        if length <= 1e-8:
            continue
        vertex.co += displacement
        changed.append(vertex.index)
        displacement_lengths.append(float(length))
        region_weight_sums["cheek_depth_and_width"] += cheek_weight
        region_weight_sums["jaw_width"] += jaw_weight
        region_weight_sums["chin_and_lower_face"] += chin_weight
        region_weight_sums["upper_neck_transition"] += neck_weight
    body.data.update()
    lower_after = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_after = point_signature(lower_after)
    lower_unchanged = (
        len(lower_before) == len(lower_after)
        and lower_signature_before == lower_signature_after
    )
    if not lower_unchanged:
        raise RuntimeError(
            "photo-ratio anti-puffiness layer altered frozen lower body"
        )
    group = body.vertex_groups.new(
        name="Diagnostic_Photo_Ratio_Anti_Puffiness"
    )
    if changed:
        group.add(changed, 1.0, "REPLACE")
    return {
        "method": (
            "bounded bilateral regional correction over v5 mapped clean "
            "topology; owner-evidence diagnostic only"
        ),
        "changed_vertices": len(changed),
        "maximum_allowed_displacement": maximum_displacement,
        "displacement_lengths": quantiles(displacement_lengths),
        "region_weight_sums": region_weight_sums,
        "requested_direction": {
            "cheek_width_scale_at_full_weight": 0.972,
            "jaw_width_scale_at_full_weight": 0.975,
            "upper_neck_width_scale_at_full_weight": 0.985,
            "cheek_depth_shift_posterior_over_interocular_distance": 0.018,
            "jaw_depth_shift_posterior_over_interocular_distance": 0.012,
            "chin_depth_shift_posterior_over_interocular_distance": 0.014,
            "chin_vertical_shift_over_interocular_distance": 0.008,
        },
        "lower_body_pelvis_anatomy_invariant": {
            "vertex_count": len(lower_before),
            "signature_before": lower_signature_before,
            "signature_after": lower_signature_after,
            "unchanged": lower_unchanged,
        },
    }


def target_file_rows(path: Path) -> list[tuple[int, Vector]]:
    rows: list[tuple[int, Vector]] = []
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            fields = raw.split()
            if len(fields) != 4 or fields[0].startswith("#"):
                continue
            rows.append(
                (
                    int(fields[0]),
                    Vector(
                        (
                            float(fields[1]),
                            float(fields[2]),
                            float(fields[3]),
                        )
                    ),
                )
            )
    return rows


def apply_v8_local_feature_targets(
    body: bpy.types.Object,
    clean_foundation: bpy.types.Object,
    source_vertices: list[Vector],
) -> tuple[dict[str, object], dict[str, list[int]]]:
    """Replay artist-authored local MakeHuman targets on v7 topology.

    The clean foundation and final diagnostic share vertex order. Source
    indices are matched only against the unwarped clean head coordinates;
    the resulting local deltas are then applied to the same final-topology
    vertex indices. No global scale or reference topology is transferred.
    """

    target_root = P.MAKEHUMAN_BASE.parents[1] / "targets"
    aggregate_by_source: dict[int, Vector] = {}
    region_source_indices: dict[str, set[int]] = {}
    target_reports: list[dict[str, object]] = []
    for relative_path, weight, region, purpose in V8_LOCAL_FEATURE_TARGETS:
        path = target_root / relative_path
        if not path.is_file():
            raise RuntimeError(f"missing v8 feature target: {relative_path}")
        rows = target_file_rows(path)
        if not rows:
            raise RuntimeError(f"empty v8 feature target: {relative_path}")
        region_source_indices.setdefault(region, set())
        for source_index, raw_delta in rows:
            aggregate_by_source[source_index] = (
                aggregate_by_source.get(source_index, Vector())
                + raw_delta * weight
            )
            region_source_indices[region].add(source_index)
        target_reports.append(
            {
                "target": relative_path,
                "weight": weight,
                "region": region,
                "purpose": purpose,
                "source_sha256": sha256(path),
                "source_vertex_rows": len(rows),
            }
        )

    delta_maps: dict[
        int, dict[tuple[float, float, float], list[Vector]]
    ] = {5: {}, 4: {}}
    region_key_maps: dict[
        int, dict[str, set[tuple[float, float, float]]]
    ] = {
        5: {region: set() for region in region_source_indices},
        4: {region: set() for region in region_source_indices},
    }
    for source_index, source_delta in aggregate_by_source.items():
        source_point = P.blender_point(source_vertices[source_index])
        blender_delta = P.blender_point(source_delta)
        for digits in (5, 4):
            key = tuple(
                round(float(value), digits) for value in source_point
            )
            delta_maps[digits].setdefault(key, []).append(blender_delta)
    for region, source_indices in region_source_indices.items():
        for source_index in source_indices:
            source_point = P.blender_point(source_vertices[source_index])
            for digits in (5, 4):
                region_key_maps[digits][region].add(
                    tuple(
                        round(float(value), digits)
                        for value in source_point
                    )
                )
    averaged_delta_maps = {
        digits: {
            key: sum(values, Vector()) / len(values)
            for key, values in rows.items()
        }
        for digits, rows in delta_maps.items()
    }

    lower_before = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_before = point_signature(lower_before)
    matched_by_precision = {5: 0, 4: 0}
    region_indices: dict[str, set[int]] = {
        region: set() for region in region_source_indices
    }
    changed: list[int] = []
    displacement_lengths: list[float] = []
    maximum_allowed = 0.038
    for clean_vertex in clean_foundation.data.vertices:
        if clean_vertex.co.z < FACE_CUTOFF_Z:
            continue
        delta: Vector | None = None
        matched_digits: int | None = None
        matched_key: tuple[float, float, float] | None = None
        for digits in (5, 4):
            key = tuple(
                round(float(value), digits)
                for value in clean_vertex.co
            )
            delta = averaged_delta_maps[digits].get(key)
            if delta is not None:
                matched_digits = digits
                matched_key = key
                break
        if delta is None or matched_digits is None or matched_key is None:
            continue
        length = delta.length
        if length > maximum_allowed and length > 1e-12:
            delta = delta * (maximum_allowed / length)
            length = maximum_allowed
        if length <= 1e-9:
            continue
        body.data.vertices[clean_vertex.index].co += delta
        changed.append(clean_vertex.index)
        displacement_lengths.append(float(length))
        matched_by_precision[matched_digits] += 1
        for region in region_indices:
            if matched_key in region_key_maps[matched_digits][region]:
                region_indices[region].add(clean_vertex.index)
    body.data.update()
    if not changed:
        raise RuntimeError(
            "v8 local feature targets matched no clean-head vertices"
        )

    lower_after = [
        vertex.co.copy()
        for vertex in body.data.vertices
        if vertex.co.z < FACE_CUTOFF_Z
    ]
    lower_signature_after = point_signature(lower_after)
    lower_unchanged = (
        len(lower_before) == len(lower_after)
        and lower_signature_before == lower_signature_after
    )
    if not lower_unchanged:
        raise RuntimeError(
            "v8 local feature targets altered frozen lower body"
        )
    group = body.vertex_groups.new(
        name="Diagnostic_V8_Local_Robert_Feature_Fit"
    )
    group.add(changed, 1.0, "REPLACE")
    return (
        {
            "method": (
                "local artist-authored MakeHuman target deltas mapped by "
                "clean-foundation coordinates onto shared final topology"
            ),
            "global_scaling": False,
            "reference_topology_transplanted": False,
            "targets": target_reports,
            "matched_vertices": len(changed),
            "matched_by_precision": matched_by_precision,
            "maximum_allowed_displacement": maximum_allowed,
            "displacement_lengths": quantiles(displacement_lengths),
            "region_vertex_counts": {
                region: len(indices)
                for region, indices in region_indices.items()
            },
            "lower_body_pelvis_anatomy_invariant": {
                "vertex_count": len(lower_before),
                "signature_before": lower_signature_before,
                "signature_after": lower_signature_after,
                "unchanged": lower_unchanged,
            },
        },
        {
            region: sorted(indices)
            for region, indices in region_indices.items()
        },
    )


def bounded_region_measurement(
    body: bpy.types.Object,
    indices: list[int],
) -> dict[str, float]:
    points = [
        body.data.vertices[index].co
        for index in indices
        if 0 <= index < len(body.data.vertices)
    ]
    if not points:
        return {
            "vertex_count": 0,
            "x_span": 0.0,
            "y_span": 0.0,
            "z_span": 0.0,
            "frontmost_y": 0.0,
            "mean_z": 0.0,
        }
    return {
        "vertex_count": len(points),
        "x_span": float(
            max(point.x for point in points)
            - min(point.x for point in points)
        ),
        "y_span": float(
            max(point.y for point in points)
            - min(point.y for point in points)
        ),
        "z_span": float(
            max(point.z for point in points)
            - min(point.z for point in points)
        ),
        "frontmost_y": float(min(point.y for point in points)),
        "mean_z": float(sum(point.z for point in points) / len(points)),
    }


def v8_feature_measurements(
    body: bpy.types.Object,
    region_indices: dict[str, list[int]],
    *,
    landmarks: dict[str, Vector],
    interocular_distance: float,
) -> dict[str, object]:
    regions = {
        region: bounded_region_measurement(body, indices)
        for region, indices in region_indices.items()
    }
    left_eye = regions.get("left_eye_aperture", {})
    right_eye = regions.get("right_eye_aperture", {})
    nose_indices = sorted(
        set(region_indices.get("nose_front", []))
        | set(region_indices.get("nose_profile", []))
    )
    nose = bounded_region_measurement(body, nose_indices)
    brow_indices = region_indices.get("brow_contour", [])
    brow_points = [body.data.vertices[index].co for index in brow_indices]
    inner_brow = [
        point for point in brow_points if abs(point.x) <= interocular_distance * 0.72
    ]
    outer_brow = [
        point for point in brow_points if abs(point.x) > interocular_distance * 0.72
    ]
    brow_outer_minus_inner_z = (
        (
            sum(point.z for point in outer_brow) / len(outer_brow)
            - sum(point.z for point in inner_brow) / len(inner_brow)
        )
        if inner_brow and outer_brow
        else 0.0
    )
    shape = face_shape_measurements(
        landmarks,
        body,
        interocular_distance=interocular_distance,
    )
    return {
        "regions": regions,
        "derived": {
            "left_eye_target_region_z_over_x_span": (
                left_eye.get("z_span", 0.0)
                / left_eye.get("x_span", 1.0)
                if left_eye.get("x_span", 0.0)
                else 0.0
            ),
            "right_eye_target_region_z_over_x_span": (
                right_eye.get("z_span", 0.0)
                / right_eye.get("x_span", 1.0)
                if right_eye.get("x_span", 0.0)
                else 0.0
            ),
            "nose_target_region_width_over_cheek_landmark_span": (
                nose["x_span"] / shape["cheek_width"]
                if shape["cheek_width"]
                else 0.0
            ),
            "nose_front_projection_over_interocular_distance": (
                (landmarks["eye_midpoint"].y - nose["frontmost_y"])
                / interocular_distance
                if nose_indices
                else 0.0
            ),
            "brow_outer_minus_inner_z_over_interocular_distance": float(
                brow_outer_minus_inner_z / interocular_distance
            ),
            **shape,
        },
        "measurement_limit": (
            "Eye ratios measure the exact skin vertices affected by the "
            "artist-authored aperture targets; they are a repeatable proxy, "
            "not a claim that empty-socket pixels equal final visible-eye "
            "aperture. Final eye/iris approval remains blocked."
        ),
    }


def build_reference_head_mesh(
    reference_points: list[Vector],
    reference_faces: list[tuple[int, int, int]],
    alignment: dict[str, object],
    reference_eye_mid: Vector,
    reference_iod: float,
) -> tuple[bpy.types.Object, dict[str, object]]:
    keep = {
        index
        for index, point in enumerate(reference_points)
        if point.z >= reference_eye_mid.z - reference_iod * 2.25
    }
    cropped_faces = [
        face for face in reference_faces if all(index in keep for index in face)
    ]
    transformed = {
        index: transform_point(reference_points[index], alignment)
        for index in keep
    }
    maximum_edge = (
        float(alignment["current_interocular_distance"]) * 0.45
    )
    faces: list[tuple[int, int, int]] = []
    rejected_long_edge = 0
    maximum_observed_edge = 0.0
    for face in cropped_faces:
        edge_lengths = [
            (transformed[face[0]] - transformed[face[1]]).length,
            (transformed[face[1]] - transformed[face[2]]).length,
            (transformed[face[2]] - transformed[face[0]]).length,
        ]
        face_maximum = max(edge_lengths)
        maximum_observed_edge = max(maximum_observed_edge, face_maximum)
        if face_maximum > maximum_edge:
            rejected_long_edge += 1
            continue
        faces.append(face)
    print(
        "REFERENCE_HEAD_FILTER",
        "threshold",
        reference_eye_mid.z - reference_iod * 2.25,
        "kept_vertices",
        len(keep),
        "input_faces",
        len(reference_faces),
        "kept_faces",
        len(faces),
        "rejected_long_edge",
        rejected_long_edge,
        "maximum_observed_edge",
        maximum_observed_edge,
    )
    used = sorted({index for face in faces for index in face})
    remap = {old: new for new, old in enumerate(used)}
    vertices = [
        tuple(transformed[index])
        for index in used
    ]
    remapped_faces = [
        tuple(remap[index] for index in face) for face in faces
    ]
    mesh = bpy.data.meshes.new("V18_Aligned_Reference_Head_Mesh")
    mesh.from_pydata(vertices, [], remapped_faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("V18_Aligned_Reference_Head", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, {
        "crop_threshold_reference_z": (
            reference_eye_mid.z - reference_iod * 2.25
        ),
        "cropped_face_count_before_edge_filter": len(cropped_faces),
        "accepted_face_count": len(faces),
        "rejected_long_edge_face_count": rejected_long_edge,
        "maximum_allowed_transformed_edge_length": maximum_edge,
        "maximum_observed_transformed_edge_length": maximum_observed_edge,
    }


def create_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.5,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return material


def add_landmark_sphere(
    name: str,
    point: Vector,
    material: bpy.types.Material,
    radius: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=20, ring_count=10, radius=radius, location=point
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def add_error_line(
    name: str,
    start: Vector,
    end: Vector,
    material: bpy.types.Material,
    bevel_depth: float,
) -> bpy.types.Object:
    data = bpy.data.curves.new(f"{name}_Data", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (*start, 1.0)
    spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def setup_scene() -> tuple[bpy.types.Scene, bpy.types.Object]:
    scene = bpy.context.scene
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.035, 0.040, 0.050)
    scene.view_settings.look = "AgX - Medium Low Contrast"
    for name, energy, direction, angle in (
        ("DiagnosticFront", 2.2, (0.0, -1.0, 0.40), 0.45),
        ("DiagnosticLeft", 1.0, (-0.8, -0.3, 0.25), 0.55),
        ("DiagnosticRight", 0.8, (0.8, -0.25, 0.20), 0.55),
    ):
        light_data = bpy.data.lights.new(name, "SUN")
        light_data.energy = energy
        light_data.angle = angle
        light = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(light)
        light.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("FaceSurfaceFitDiagnosticCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("FaceSurfaceFitDiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def point_camera(camera: bpy.types.Object, location: Vector, target: Vector) -> None:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    *,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> None:
    point_camera(camera, location, target)
    camera.data.ortho_scale = ortho_scale
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def visibility(objects: list[bpy.types.Object], visible: bool) -> None:
    for obj in objects:
        obj.hide_render = not visible


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {"minimum": 0.0, "median": 0.0, "p95": 0.0, "maximum": 0.0}

    def q(frac: float) -> float:
        index = min(len(ordered) - 1, int(round((len(ordered) - 1) * frac)))
        return float(ordered[index])

    return {
        "minimum": float(ordered[0]),
        "median": q(0.50),
        "p95": q(0.95),
        "maximum": float(ordered[-1]),
        "mean": float(sum(ordered) / len(ordered)),
        "rms": float(math.sqrt(sum(value * value for value in ordered) / len(ordered))),
    }


def head_surface_distances(
    body: bpy.types.Object,
    bvh: BVHTree,
    *,
    minimum_z: float = FACE_CUTOFF_Z,
) -> list[float]:
    distances: list[float] = []
    for vertex in body.data.vertices:
        if vertex.co.z < minimum_z:
            continue
        nearest = bvh.find_nearest(vertex.co)
        if (
            nearest is not None
            and nearest[0] is not None
            and nearest[3] is not None
        ):
            distances.append(float(nearest[3]))
    return distances


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(CLEAN_BLEND))
    current_bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and "MakeHuman" in obj.name
    ]
    if len(current_bodies) != 1:
        raise RuntimeError(
            f"expected one clean MakeHuman body, found {[obj.name for obj in current_bodies]}"
        )
    current_body = current_bodies[0]
    current_body.name = "Clean_MakeHuman_Foundation_Diagnostic"
    current_points = world_points(current_body)
    current_head_points = [
        point for point in current_points if point.z >= FACE_CUTOFF_Z
    ]

    source_report = json.loads(P.SOURCE_REPORT.read_text(encoding="utf-8"))
    source_vertices, source_groups = P.parse_obj_groups(P.MAKEHUMAN_BASE)
    for row in source_report["targets"]:
        P.apply_target(source_vertices, Path(row["path"]), float(row["weight"]))
    current_eye_centers: list[Vector] = []
    for group_name in ("helper-r-eye", "helper-l-eye"):
        indices = sorted(
            {
                index
                for face in source_groups[group_name]
                for index in face
            }
        )
        center = sum(
            (P.blender_point(source_vertices[index]) for index in indices),
            Vector(),
        ) / len(indices)
        current_eye_centers.append(center)

    with bpy.data.libraries.load(str(V18_BLEND), link=False) as (
        data_from,
        data_to,
    ):
        candidates = [
            name
            for name in data_from.objects
            if name and "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V18" in name
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"expected one V18 body object, found {candidates}")
        data_to.objects = candidates
    reference_body = data_to.objects[0]
    bpy.context.collection.objects.link(reference_body)
    reference_body.name = "V18_Reference_Source_Diagnostic"
    reference_points, reference_faces = primary_skin_geometry(reference_body)
    iris_components = component_centers(reference_body, {"MBLab_Iris_V4"})
    if len(iris_components) < 2:
        iris_components = component_centers(
            reference_body, {"Mblab_human_eyes", "MBlab_human_eyes"}
        )
    reference_eye_centers = tuple(
        center
        for _, center in sorted(
            iris_components[:2], key=lambda row: row[1].x
        )
    )
    if len(reference_eye_centers) != 2:
        raise RuntimeError(
            f"could not identify two V18 eye centers: {iris_components[:5]}"
        )

    current_landmarks = derive_landmarks(
        current_head_points, tuple(current_eye_centers)
    )
    reference_landmarks = derive_landmarks(
        reference_points, reference_eye_centers
    )
    alignment = diagonal_alignment(
        current_landmarks,
        reference_landmarks,
        current_head_points,
        reference_points,
    )
    aligned_reference_landmarks = {
        name: transform_point(point, alignment)
        for name, point in reference_landmarks.items()
    }
    errors = landmark_error_rows(
        current_landmarks, aligned_reference_landmarks
    )

    reference_iod = alignment["reference_interocular_distance"]
    reference_head, reference_head_filter_report = build_reference_head_mesh(
        reference_points,
        reference_faces,
        alignment,
        reference_landmarks["eye_midpoint"],
        reference_iod,
    )
    if len(reference_head.data.vertices) == 0 or len(reference_head.data.polygons) == 0:
        raise RuntimeError(
            "aligned V18 reference head produced no renderable geometry"
        )
    reference_minimum, reference_maximum = P.object_bounds(reference_head)
    print(
        "ALIGNED_REFERENCE_HEAD",
        len(reference_head.data.vertices),
        len(reference_head.data.polygons),
        vector_row(reference_minimum),
        vector_row(reference_maximum),
    )
    reference_body.hide_render = True

    # Measure the unwarped clean-head distance, then apply a diagnostic-only
    # localized displacement field to a topology-preserving copy.
    bvh = BVHTree.FromPolygons(
        [vertex.co.copy() for vertex in reference_head.data.vertices],
        [tuple(polygon.vertices) for polygon in reference_head.data.polygons],
        all_triangles=True,
    )
    correspondence_distances_before = head_surface_distances(
        current_body, bvh
    )
    face_metric_minimum_z = (
        current_landmarks["chin"].z
        - alignment["current_interocular_distance"] * 0.18
    )
    face_correspondence_distances_before = head_surface_distances(
        current_body, bvh, minimum_z=face_metric_minimum_z
    )
    if not correspondence_distances_before:
        raise RuntimeError(
            "aligned V18 reference head produced no valid BVH correspondence samples"
        )
    controls, symmetry_pairs = symmetric_control_goals(
        current_landmarks, aligned_reference_landmarks
    )
    warped_body = current_body.copy()
    warped_body.data = current_body.data.copy()
    warped_body.name = "Clean_MakeHuman_Topology_Localized_V18_Warp_Diagnostic"
    bpy.context.collection.objects.link(warped_body)
    first_warp_report = apply_localized_rbf_warp(
        warped_body,
        controls,
        interocular_distance=alignment["current_interocular_distance"],
        radius_factor=0.70,
        maximum_displacement_factor=0.28,
        stage_name="coarse_symmetric_identity_direction",
    )
    interim_points = world_points(warped_body)
    interim_head_points = [
        point for point in interim_points if point.z >= FACE_CUTOFF_Z
    ]
    interim_landmarks = derive_landmarks(
        interim_head_points, tuple(current_eye_centers)
    )
    residual_controls, residual_symmetry_pairs = symmetric_control_goals(
        interim_landmarks, aligned_reference_landmarks
    )
    second_warp_report = apply_localized_rbf_warp(
        warped_body,
        residual_controls,
        interocular_distance=alignment["current_interocular_distance"],
        radius_factor=0.43,
        maximum_displacement_factor=0.16,
        stage_name="localized_residual_landmark_correction",
    )
    rbf_only_deformation_report = deformation_quality(
        current_body,
        warped_body,
        minimum_z=face_metric_minimum_z,
    )
    pre_relaxation_positions = [
        vertex.co.copy() for vertex in warped_body.data.vertices
    ]
    surface_relaxation_report = apply_bounded_surface_relaxation(
        warped_body,
        bvh,
        eye_midpoint=current_landmarks["eye_midpoint"],
        interocular_distance=alignment["current_interocular_distance"],
        iterations=1,
    )
    post_relaxation_deformation_report = deformation_quality(
        current_body,
        warped_body,
        minimum_z=face_metric_minimum_z,
    )
    relaxation_added_flips = (
        post_relaxation_deformation_report["flipped_triangle_count"]
        > rbf_only_deformation_report["flipped_triangle_count"]
    )
    relaxation_added_collapses = (
        post_relaxation_deformation_report[
            "near_zero_area_triangle_count"
        ]
        > rbf_only_deformation_report["near_zero_area_triangle_count"]
    )
    if relaxation_added_flips or relaxation_added_collapses:
        for vertex, position in zip(
            warped_body.data.vertices, pre_relaxation_positions
        ):
            vertex.co = position
        warped_body.data.update()
        surface_relaxation_report["accepted"] = False
        surface_relaxation_report["rolled_back"] = True
        surface_relaxation_report["rollback_reason"] = (
            "FAILED_TOPOLOGY_QUALITY__ADDED_FLIPPED_OR_COLLAPSED_TRIANGLES"
        )
        deformation_report = rbf_only_deformation_report
    else:
        surface_relaxation_report["accepted"] = True
        surface_relaxation_report["rolled_back"] = False
        surface_relaxation_report["rollback_reason"] = None
        deformation_report = post_relaxation_deformation_report
    mapped_baseline_body = warped_body.copy()
    mapped_baseline_body.data = warped_body.data.copy()
    mapped_baseline_body.name = (
        "V5_Clean_Topology_Mapped_Baseline_Diagnostic"
    )
    bpy.context.collection.objects.link(mapped_baseline_body)
    mapped_baseline_points = world_points(mapped_baseline_body)
    mapped_baseline_landmarks = derive_landmarks(
        [
            point
            for point in mapped_baseline_points
            if point.z >= FACE_CUTOFF_Z
        ],
        tuple(current_eye_centers),
    )
    photo_ratio_measurements_before = face_shape_measurements(
        mapped_baseline_landmarks,
        mapped_baseline_body,
        interocular_distance=alignment["current_interocular_distance"],
    )
    pre_photo_ratio_positions = [
        vertex.co.copy() for vertex in warped_body.data.vertices
    ]
    photo_ratio_report = apply_photo_ratio_anti_puffiness(
        warped_body,
        landmarks=mapped_baseline_landmarks,
        interocular_distance=alignment["current_interocular_distance"],
    )
    photo_ratio_deformation_report = deformation_quality(
        current_body,
        warped_body,
        minimum_z=face_metric_minimum_z,
    )
    photo_ratio_added_flips = (
        photo_ratio_deformation_report["flipped_triangle_count"]
        > deformation_report["flipped_triangle_count"]
    )
    photo_ratio_added_collapses = (
        photo_ratio_deformation_report["near_zero_area_triangle_count"]
        > deformation_report["near_zero_area_triangle_count"]
    )
    if photo_ratio_added_flips or photo_ratio_added_collapses:
        for vertex, position in zip(
            warped_body.data.vertices, pre_photo_ratio_positions
        ):
            vertex.co = position
        warped_body.data.update()
        photo_ratio_report["accepted"] = False
        photo_ratio_report["rolled_back"] = True
        photo_ratio_report["rollback_reason"] = (
            "FAILED_TOPOLOGY_QUALITY__ADDED_FLIPPED_OR_COLLAPSED_TRIANGLES"
        )
        final_deformation_report = deformation_report
    else:
        photo_ratio_report["accepted"] = True
        photo_ratio_report["rolled_back"] = False
        photo_ratio_report["rollback_reason"] = None
        final_deformation_report = photo_ratio_deformation_report
    v7_deformation_report = final_deformation_report
    v7_points = world_points(warped_body)
    v7_head_points = [
        point for point in v7_points if point.z >= FACE_CUTOFF_Z
    ]
    v7_landmarks = derive_landmarks(
        v7_head_points, tuple(current_eye_centers)
    )
    photo_ratio_measurements_after = face_shape_measurements(
        v7_landmarks,
        warped_body,
        interocular_distance=alignment["current_interocular_distance"],
    )
    v7_baseline_body = warped_body.copy()
    v7_baseline_body.data = warped_body.data.copy()
    v7_baseline_body.name = (
        "V7_Photo_Ratio_Baseline_Before_V8_Diagnostic"
    )
    bpy.context.collection.objects.link(v7_baseline_body)

    pre_v8_positions = [
        vertex.co.copy() for vertex in warped_body.data.vertices
    ]
    v8_local_feature_report, v8_region_indices = (
        apply_v8_local_feature_targets(
            warped_body,
            current_body,
            source_vertices,
        )
    )
    v8_trial_deformation_report = deformation_quality(
        current_body,
        warped_body,
        minimum_z=face_metric_minimum_z,
    )
    v8_added_flips = (
        v8_trial_deformation_report["flipped_triangle_count"]
        > v7_deformation_report["flipped_triangle_count"]
    )
    v8_added_collapses = (
        v8_trial_deformation_report["near_zero_area_triangle_count"]
        > v7_deformation_report["near_zero_area_triangle_count"]
    )
    if v8_added_flips or v8_added_collapses:
        for vertex, position in zip(
            warped_body.data.vertices, pre_v8_positions
        ):
            vertex.co = position
        warped_body.data.update()
        v8_local_feature_report["accepted"] = False
        v8_local_feature_report["rolled_back"] = True
        v8_local_feature_report["rollback_reason"] = (
            "FAILED_TOPOLOGY_QUALITY__ADDED_FLIPPED_OR_COLLAPSED_TRIANGLES"
        )
        final_deformation_report = v7_deformation_report
    else:
        v8_local_feature_report["accepted"] = True
        v8_local_feature_report["rolled_back"] = False
        v8_local_feature_report["rollback_reason"] = None
        final_deformation_report = v8_trial_deformation_report

    v8_feature_measurements_before = v8_feature_measurements(
        v7_baseline_body,
        v8_region_indices,
        landmarks=v7_landmarks,
        interocular_distance=alignment["current_interocular_distance"],
    )
    warped_points = world_points(warped_body)
    warped_head_points = [
        point for point in warped_points if point.z >= FACE_CUTOFF_Z
    ]
    warped_landmarks = derive_landmarks(
        warped_head_points, tuple(current_eye_centers)
    )
    v8_feature_measurements_after = v8_feature_measurements(
        warped_body,
        v8_region_indices,
        landmarks=warped_landmarks,
        interocular_distance=alignment["current_interocular_distance"],
    )
    v8_face_shape_measurements_after = face_shape_measurements(
        warped_landmarks,
        warped_body,
        interocular_distance=alignment["current_interocular_distance"],
    )
    warped_landmark_errors = landmark_error_rows(
        warped_landmarks, aligned_reference_landmarks
    )
    correspondence_distances_after = head_surface_distances(
        warped_body, bvh
    )
    face_correspondence_distances_after = head_surface_distances(
        warped_body, bvh, minimum_z=face_metric_minimum_z
    )
    if not correspondence_distances_after:
        raise RuntimeError("warped clean head produced no BVH correspondence samples")

    current_material = create_material(
        "Clean_Foundation_Solid_Gray", (0.50, 0.47, 0.43, 1.0), roughness=0.62
    )
    warped_material = create_material(
        "Warped_Clean_Topology_Solid_Warm_Gray",
        (0.46, 0.32, 0.24, 1.0),
        roughness=0.60,
    )
    mapped_baseline_material = create_material(
        "V5_Mapped_Baseline_Solid_Cool_Gray",
        (0.30, 0.38, 0.44, 1.0),
        roughness=0.62,
    )
    v7_baseline_material = create_material(
        "V7_Baseline_Before_V8_Solid_Blue_Gray",
        (0.28, 0.36, 0.54, 1.0),
        roughness=0.62,
    )
    reference_material = create_material(
        "V18_Aligned_Solid_Magenta", (0.52, 0.05, 0.18, 1.0), roughness=0.48
    )
    wire_material = create_material(
        "V18_Aligned_Wire_Cyan", (0.01, 0.72, 0.90, 1.0), roughness=0.35
    )
    current_body.data.materials.clear()
    current_body.data.materials.append(current_material)
    warped_body.data.materials.clear()
    warped_body.data.materials.append(warped_material)
    mapped_baseline_body.data.materials.clear()
    mapped_baseline_body.data.materials.append(mapped_baseline_material)
    v7_baseline_body.data.materials.clear()
    v7_baseline_body.data.materials.append(v7_baseline_material)
    reference_head.data.materials.append(reference_material)

    reference_wire = reference_head.copy()
    reference_wire.data = reference_head.data.copy()
    reference_wire.name = "V18_Aligned_Reference_Head_Wire"
    bpy.context.collection.objects.link(reference_wire)
    reference_wire.data.materials.clear()
    reference_wire.data.materials.append(wire_material)
    wire_modifier = reference_wire.modifiers.new("AlignmentWire", "WIREFRAME")
    wire_modifier.thickness = 0.004
    wire_modifier.offset = 1.0
    wire_modifier.use_replace = True

    warped_wire = warped_body.copy()
    warped_wire.data = warped_body.data.copy()
    warped_wire.name = "Warped_Clean_Topology_Wire_Diagnostic"
    bpy.context.collection.objects.link(warped_wire)
    warped_wire.data.materials.clear()
    warped_wire.data.materials.append(wire_material)
    warped_wire_modifier = warped_wire.modifiers.new(
        "WarpedTopologyWire", "WIREFRAME"
    )
    warped_wire_modifier.thickness = 0.005
    warped_wire_modifier.offset = 1.0
    warped_wire_modifier.use_replace = True

    current_landmark_material = create_material(
        "Current_Landmark_Yellow", (0.95, 0.55, 0.02, 1.0), roughness=0.38
    )
    reference_landmark_material = create_material(
        "Reference_Landmark_Cyan", (0.01, 0.75, 0.95, 1.0), roughness=0.32
    )
    error_material = create_material(
        "Landmark_Error_Red", (0.85, 0.02, 0.02, 1.0), roughness=0.35
    )
    warped_landmark_material = create_material(
        "Warped_Landmark_Green", (0.05, 0.82, 0.20, 1.0), roughness=0.34
    )
    iod = alignment["current_interocular_distance"]
    marker_radius = iod * 0.055
    landmark_objects: list[bpy.types.Object] = []
    for name, current_point in current_landmarks.items():
        if name == "eye_midpoint":
            continue
        reference_point = aligned_reference_landmarks[name]
        landmark_objects.append(
            add_landmark_sphere(
                f"Current_{name}",
                current_point,
                current_landmark_material,
                marker_radius,
            )
        )
        landmark_objects.append(
            add_landmark_sphere(
                f"Reference_{name}",
                reference_point,
                reference_landmark_material,
                marker_radius * 0.78,
            )
        )
        landmark_objects.append(
            add_error_line(
                f"Error_{name}",
                current_point,
                reference_point,
                error_material,
                marker_radius * 0.15,
            )
        )
    warped_landmark_objects: list[bpy.types.Object] = []
    for name, warped_point in warped_landmarks.items():
        if name == "eye_midpoint":
            continue
        reference_point = aligned_reference_landmarks[name]
        warped_landmark_objects.append(
            add_landmark_sphere(
                f"Warped_{name}",
                warped_point,
                warped_landmark_material,
                marker_radius,
            )
        )
        warped_landmark_objects.append(
            add_landmark_sphere(
                f"WarpedReference_{name}",
                reference_point,
                reference_landmark_material,
                marker_radius * 0.78,
            )
        )
        warped_landmark_objects.append(
            add_error_line(
                f"WarpedError_{name}",
                warped_point,
                reference_point,
                error_material,
                marker_radius * 0.13,
            )
        )

    scene, camera = setup_scene()
    target = current_landmarks["eye_midpoint"] + Vector((0.0, 0.0, -0.30))
    distance = iod * 9.2
    ortho_scale = iod * 5.25
    front_location = target + Vector((0.0, -distance, 0.0))
    three_quarter_location = target + Vector((-distance * 0.68, -distance * 0.68, 0.0))
    profile_location = target + Vector((-distance, 0.0, 0.0))

    solid_current_paths: dict[str, str] = {}
    solid_reference_paths: dict[str, str] = {}
    overlay_before_paths: dict[str, str] = {}
    mapped_baseline_paths: dict[str, str] = {}
    v7_baseline_paths: dict[str, str] = {}
    warped_solid_paths: dict[str, str] = {}
    warped_overlay_paths: dict[str, str] = {}
    reference_with_warped_wire_paths: dict[str, str] = {}
    all_diagnostic_objects = [
        current_body,
        mapped_baseline_body,
        v7_baseline_body,
        warped_body,
        reference_head,
        reference_wire,
        warped_wire,
        *landmark_objects,
        *warped_landmark_objects,
    ]
    for suffix, location in (
        ("front", front_location),
        ("left_three_quarter", three_quarter_location),
        ("left_profile", profile_location),
    ):
        visibility(all_diagnostic_objects, False)
        visibility([current_body], True)
        current_path = OUT / f"current_clean_solid_{suffix}.png"
        render(
            scene,
            camera,
            current_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        solid_current_paths[suffix] = str(current_path)

        visibility(all_diagnostic_objects, False)
        visibility([reference_head], True)
        reference_path = OUT / f"aligned_v18_solid_{suffix}.png"
        render(
            scene,
            camera,
            reference_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        solid_reference_paths[suffix] = str(reference_path)

        visibility(all_diagnostic_objects, False)
        visibility([current_body, reference_wire, *landmark_objects], True)
        overlay_path = OUT / f"current_solid_v18_wire_landmarks_{suffix}.png"
        render(
            scene,
            camera,
            overlay_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        overlay_before_paths[suffix] = str(overlay_path)

        visibility(all_diagnostic_objects, False)
        visibility([mapped_baseline_body], True)
        mapped_baseline_path = (
            OUT / f"v5_mapped_baseline_solid_{suffix}.png"
        )
        render(
            scene,
            camera,
            mapped_baseline_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        mapped_baseline_paths[suffix] = str(mapped_baseline_path)

        visibility(all_diagnostic_objects, False)
        visibility([v7_baseline_body], True)
        v7_baseline_path = (
            OUT / f"v7_geometry_before_v8_solid_{suffix}.png"
        )
        render(
            scene,
            camera,
            v7_baseline_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        v7_baseline_paths[suffix] = str(v7_baseline_path)

        visibility(all_diagnostic_objects, False)
        visibility([warped_body], True)
        warped_path = OUT / f"warped_clean_topology_solid_{suffix}.png"
        render(
            scene,
            camera,
            warped_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        warped_solid_paths[suffix] = str(warped_path)

        visibility(all_diagnostic_objects, False)
        visibility(
            [warped_body, reference_wire, *warped_landmark_objects], True
        )
        warped_overlay_path = (
            OUT / f"warped_solid_v18_wire_landmarks_{suffix}.png"
        )
        render(
            scene,
            camera,
            warped_overlay_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        warped_overlay_paths[suffix] = str(warped_overlay_path)

        visibility(all_diagnostic_objects, False)
        visibility([reference_head, warped_wire], True)
        reverse_overlay_path = (
            OUT / f"aligned_v18_solid_warped_clean_wire_{suffix}.png"
        )
        render(
            scene,
            camera,
            reverse_overlay_path,
            location=location,
            target=target,
            ortho_scale=ortho_scale,
        )
        reference_with_warped_wire_paths[suffix] = str(reverse_overlay_path)

    visibility(all_diagnostic_objects, True)
    bpy.ops.wm.save_as_mainfile(filepath=str(DIAGNOSTIC_BLEND))
    report = {
        "schema": "kira.avatar.face_surface_fit_diagnostic.v8",
        "status": STATUS,
        "owner_candidate": False,
        "owner_approved": False,
        "source_clean_foundation": {
            "path": str(CLEAN_BLEND),
            "sha256": sha256(CLEAN_BLEND),
            "topology_was_modified": False,
        },
        "source_preferred_reference": {
            "opaque_id": "PREFERRED_PRIOR_V18_FACE_SURFACE",
            "path": str(V18_BLEND),
            "sha256": sha256(V18_BLEND),
            "topology_or_material_transplanted": False,
            "role": "alignment surface only",
        },
        "aligned_reference_mesh": {
            "vertices": len(reference_head.data.vertices),
            "polygons": len(reference_head.data.polygons),
            "bounds_minimum": vector_row(reference_minimum),
            "bounds_maximum": vector_row(reference_maximum),
            "filter": reference_head_filter_report,
        },
        "face_cutoff_z": FACE_CUTOFF_Z,
        "alignment": {
            "type": (
                "axis-preserving eye/depth alignment with weighted "
                "eye-anchored vertical landmark scale"
            ),
            "scales": vector_row(alignment["scales"]),
            "reference_anchor": vector_row(alignment["reference_anchor"]),
            "current_anchor": vector_row(alignment["current_anchor"]),
            "current_interocular_distance": alignment[
                "current_interocular_distance"
            ],
            "reference_interocular_distance": alignment[
                "reference_interocular_distance"
            ],
            "current_head_depth": alignment["current_head_depth"],
            "reference_head_depth": alignment["reference_head_depth"],
            "vertical_scale_landmark_weights": alignment[
                "vertical_scale_landmark_weights"
            ],
        },
        "current_landmarks": {
            name: vector_row(point)
            for name, point in current_landmarks.items()
        },
        "reference_landmarks_before_alignment": {
            name: vector_row(point)
            for name, point in reference_landmarks.items()
        },
        "reference_landmarks_after_alignment": {
            name: vector_row(point)
            for name, point in aligned_reference_landmarks.items()
        },
        "landmark_errors": errors,
        "landmark_error_summary": quantiles(
            [float(row["distance"]) for row in errors]
        ),
        "current_head_to_aligned_reference_surface_before_warp": quantiles(
            correspondence_distances_before
        ),
        "current_face_to_aligned_reference_surface_before_warp": {
            "minimum_z": face_metric_minimum_z,
            **quantiles(face_correspondence_distances_before),
        },
        "localized_warp": {
            "topology_source": "clean MakeHuman foundation copy",
            "reference_topology_transplanted": False,
            "passes": [
                {
                    "symmetry_pairs": symmetry_pairs,
                    "controls": [
                        {
                            "name": row["name"],
                            "current": vector_row(row["current"]),
                            "raw_reference_goal": vector_row(
                                row["raw_reference_goal"]
                            ),
                            "symmetric_delta": vector_row(
                                row["symmetric_delta"]
                            ),
                            "confidence": row["confidence"],
                            "applied_goal": vector_row(row["applied_goal"]),
                        }
                        for row in controls
                    ],
                    "execution": first_warp_report,
                },
                {
                    "symmetry_pairs": residual_symmetry_pairs,
                    "controls": [
                        {
                            "name": row["name"],
                            "current": vector_row(row["current"]),
                            "raw_reference_goal": vector_row(
                                row["raw_reference_goal"]
                            ),
                            "symmetric_delta": vector_row(
                                row["symmetric_delta"]
                            ),
                            "confidence": row["confidence"],
                            "applied_goal": vector_row(row["applied_goal"]),
                        }
                        for row in residual_controls
                    ],
                    "execution": second_warp_report,
                },
            ],
            "surface_relaxation": surface_relaxation_report,
            "rbf_only_deformation_quality": rbf_only_deformation_report,
            "surface_relaxation_deformation_quality_before_rollback": (
                post_relaxation_deformation_report
            ),
            "mapped_v5_deformation_quality": deformation_report,
            "lower_body_pelvis_anatomy_invariant": (
                surface_relaxation_report[
                    "lower_body_pelvis_anatomy_invariant"
                ]
            ),
        },
        "photo_ratio_anti_puffiness": {
            "status": (
                "ACCEPTED_DIAGNOSTIC_LAYER"
                if photo_ratio_report["accepted"]
                else "REJECTED_AND_ROLLED_BACK"
            ),
            "mapped_v5_landmarks_before": {
                name: vector_row(point)
                for name, point in mapped_baseline_landmarks.items()
            },
            "measurements_before": photo_ratio_measurements_before,
            "measurements_after": photo_ratio_measurements_after,
            "execution": photo_ratio_report,
            "deformation_quality_before": deformation_report,
            "deformation_quality_after": v7_deformation_report,
            "lower_body_pelvis_anatomy_invariant": (
                photo_ratio_report[
                    "lower_body_pelvis_anatomy_invariant"
                ]
            ),
            "truth_limit": (
                "This is a bounded geometric correction informed by private "
                "front/profile evidence and the recorded ratio ranges. It is "
                "not calibrated photogrammetry, likeness approval, an eye "
                "review, hair review, or material review."
            ),
        },
        "v8_local_feature_fit": {
            "status": (
                "ACCEPTED_DIAGNOSTIC_LAYER"
                if v8_local_feature_report["accepted"]
                else "REJECTED_AND_ROLLED_BACK"
            ),
            "method": (
                "one bounded geometry-only pass that replays local "
                "artist-authored MakeHuman feature targets on the shared "
                "clean topology; no global thinning or scaling"
            ),
            "goals": [
                "natural eye aperture and low brow contour",
                "moderate rounded nose width and projection",
                "Robert-specific cheek-fullness distribution",
                "broad rounded jaw/chin and bounded neck transition",
            ],
            "measurements_before": v8_feature_measurements_before,
            "measurements_after": v8_feature_measurements_after,
            "final_face_shape_measurements": (
                v8_face_shape_measurements_after
            ),
            "execution": v8_local_feature_report,
            "deformation_quality_before": v7_deformation_report,
            "deformation_quality_trial_before_possible_rollback": (
                v8_trial_deformation_report
            ),
            "deformation_quality_after": final_deformation_report,
            "lower_body_pelvis_anatomy_invariant": (
                v8_local_feature_report[
                    "lower_body_pelvis_anatomy_invariant"
                ]
            ),
            "truth_limit": (
                "This remains an internal geometry diagnostic. Empty eye "
                "sockets, absent irises, absent hair, and diagnostic clay "
                "materials prevent owner likeness approval. The numerical "
                "target-region aperture proxy does not certify final visible "
                "eye openness or iris realism."
            ),
        },
        "warped_landmarks": {
            name: vector_row(point)
            for name, point in warped_landmarks.items()
        },
        "warped_landmark_errors": warped_landmark_errors,
        "warped_landmark_error_summary": quantiles(
            [float(row["distance"]) for row in warped_landmark_errors]
        ),
        "warped_head_to_aligned_reference_surface": quantiles(
            correspondence_distances_after
        ),
        "warped_face_to_aligned_reference_surface": {
            "minimum_z": face_metric_minimum_z,
            **quantiles(face_correspondence_distances_after),
        },
        "diagnostic_blend": {
            "path": str(DIAGNOSTIC_BLEND),
            "sha256": sha256(DIAGNOSTIC_BLEND),
            "owner_candidate": False,
        },
        "diagnostic_renders": {
            "current_solid": solid_current_paths,
            "aligned_reference_solid": solid_reference_paths,
            "before_wire_and_landmarks_overlay": overlay_before_paths,
            "v5_mapped_baseline_solid": mapped_baseline_paths,
            "v7_geometry_before_v8_solid": v7_baseline_paths,
            "warped_clean_topology_solid": warped_solid_paths,
            "warped_wire_and_landmarks_overlay": warped_overlay_paths,
            "aligned_reference_solid_with_warped_clean_wire": (
                reference_with_warped_wire_paths
            ),
        },
        "gates": {
            "correspondence_visually_credible": False,
            "eye_mouth_nose_alignment_visually_credible": False,
            "bounded_displacement_field_allowed": False,
            "reason": (
                "two-pass localized warp plus bounded surface relaxation is "
                "followed by one owner-evidence anti-puffiness layer and one "
                "bounded local-feature pass. This is "
                "diagnostic engineering evidence and must pass visual/error "
                "inspection before any owner candidate. Eyes, hair, and "
                "materials remain intentionally absent."
            ),
        },
        "scope_blocks": [
            "owner candidate",
            "hair restoration",
            "lower-body modification",
            "pelvis/anatomy modification",
            "movement",
            "runtime attachment",
            "activation",
            "Synthetic Robert duplication",
            "Kira",
            "clothing",
            "Kira World",
        ],
    }
    REPORT_PATH.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
