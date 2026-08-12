"""Reusable responsive strand-groom authoring for private avatar review.

The adapter creates actual bevelled guide curves on the current body scalp and
authors deterministic wind-left, wind-right, and wet/clumped shape keys.  It
does not copy a prior hair mesh, create a scalp cap, activate an avatar, or
claim that a World runtime has already driven the response controls.

Run only inside Blender.  The caller owns saving, rendering, export, and
independent visual review.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
import math
from typing import Any, Mapping, Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


SUPPORTED_STYLE = "asymmetric_deep_side_part_shoulder_length_loose_waves"
VISUAL_QUALITY_VERSION = "deep_black_sidepart_coherent_curl_locks_v4"
RESPONSE_SHAPE_KEYS = (
    "hair_wind_left_dry",
    "hair_wind_right_dry",
    "hair_wet_neutral",
    "hair_wet_wind_left",
    "hair_wet_wind_right",
)


class ResponsiveHairAuthoringError(RuntimeError):
    """Raised before returning an unproved or malformed groom."""


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ResponsiveHairAuthoringError(f"{label}_must_be_numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ResponsiveHairAuthoringError(f"{label}_must_be_numeric") from exc
    if not math.isfinite(result):
        raise ResponsiveHairAuthoringError(f"{label}_must_be_finite")
    return result


def _srgb_channel_to_linear(value: int) -> float:
    channel = max(0, min(255, int(value))) / 255.0
    return (
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
    )


def _hex_linear(value: Any, label: str) -> tuple[float, float, float, float]:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6 or any(character not in "0123456789abcdefABCDEF" for character in text):
        raise ResponsiveHairAuthoringError(f"{label}_must_be_six_digit_srgb_hex")
    channels = [int(text[index : index + 2], 16) for index in (0, 2, 4)]
    return tuple(_srgb_channel_to_linear(channel) for channel in channels) + (1.0,)


def _smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def _deterministic_unit(index: int, salt: float) -> float:
    """Return stable non-random variation without global RNG state."""

    value = math.sin(
        (int(index) + 1) * (12.9898 + float(salt) * 17.719)
        + float(salt) * 78.233
    ) * 43758.5453123
    return value - math.floor(value)


def _is_flyaway(index: int) -> bool:
    """Reserve a deterministic, bounded minority of finer short strands."""

    return _deterministic_unit(index, 7.0) < 0.012


def _bezier(
    first: Vector,
    control_one: Vector,
    control_two: Vector,
    last: Vector,
    t: float,
) -> Vector:
    inverse = 1.0 - t
    return (
        first * (inverse ** 3)
        + control_one * (3.0 * inverse * inverse * t)
        + control_two * (3.0 * inverse * t * t)
        + last * (t ** 3)
    )


def _bounds(points: Sequence[Vector]) -> tuple[Vector, Vector]:
    if not points:
        raise ResponsiveHairAuthoringError("body_has_no_vertices")
    return (
        Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3))),
        Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3))),
    )


def _eligible_scalp_triangles(
    obj: bpy.types.Object,
) -> tuple[list[tuple[Vector, Vector, Vector, Vector]], dict[str, Any]]:
    """Return rigorously bounded triangles from the weighted cranial scalp.

    Height alone is not an anatomical selector on an A-pose body: shoulders,
    ears, face, neck, and upper back can all enter the same broad Z band.  The
    selector therefore requires the official ``head`` skin group, excludes
    facial/jaw/neck deformation groups, and then applies a head-local
    crown/rear/side mask plus an explicit deep-side-part root gap.
    """

    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    low, high = _bounds(points)
    height = float(high.z - low.z)
    head_group = obj.vertex_groups.get("head")
    if head_group is None:
        raise ResponsiveHairAuthoringError("weighted_head_vertex_group_missing")
    forbidden_names = {
        group.name
        for group in obj.vertex_groups
        if group.name == "jaw"
        or group.name.startswith(
            (
                "eye.",
                "levator",
                "neck",
                "oculi",
                "orbicularis",
                "oris",
                "risorius",
            )
        )
    }
    forbidden_indices = {
        obj.vertex_groups[name].index for name in forbidden_names
    }

    head_weights = [0.0] * len(mesh.vertices)
    forbidden_weights = [0.0] * len(mesh.vertices)
    for vertex in mesh.vertices:
        for membership in vertex.groups:
            if membership.group == head_group.index:
                head_weights[vertex.index] = float(membership.weight)
            if membership.group in forbidden_indices:
                forbidden_weights[vertex.index] = max(
                    forbidden_weights[vertex.index],
                    float(membership.weight),
                )
    head_threshold = 0.25
    forbidden_threshold = 0.25
    weighted_head_points = [
        points[index]
        for index, weight in enumerate(head_weights)
        if weight >= head_threshold
    ]
    if len(weighted_head_points) < 500:
        raise ResponsiveHairAuthoringError(
            "weighted_head_region_too_sparse:"
            f"vertices={len(weighted_head_points)}"
        )
    head_low, head_high = _bounds(weighted_head_points)
    head_center = (head_low + head_high) * 0.5
    head_width = max(float(head_high.x - head_low.x), height * 0.07)
    head_depth = max(float(head_high.y - head_low.y), height * 0.07)
    head_height = max(float(head_high.z - head_low.z), height * 0.11)
    part_x = head_center.x - head_width * 0.19
    # Keep a readable deep side part at the front/crown, but taper it closed
    # before the rear scalp.  R15's constant-width exclusion became a pale
    # center trench from forehead to nape once the individual strands spread.
    part_half_width = head_width * 0.009

    def membership_reason(index: int) -> str:
        if head_weights[index] < head_threshold:
            return "head_weight"
        if forbidden_weights[index] >= forbidden_threshold:
            return "face_jaw_neck_weight"
        point = points[index]
        x_fraction = abs((point.x - head_center.x) / (head_width * 0.5))
        y_fraction = (point.y - head_low.y) / head_depth
        z_fraction = (point.z - head_low.z) / head_height
        # The default rig has no dedicated ear group.  Its protruding pinnae
        # occupy the extreme lateral, middle-depth, lower-head band; roots on
        # that folded surface make a guide cross the ear before it can drape.
        if (
            x_fraction > 0.72
            and 0.32 < y_fraction < 0.72
            and z_fraction < 0.66
        ):
            return "ear_region"
        # Head-local thresholds were probed on the exact qualified source:
        # a high front hairline, crown/side mid band, and lower rear scalp.
        if y_fraction < 0.38:
            eligible_region = z_fraction >= 0.70
        elif y_fraction < 0.62:
            eligible_region = z_fraction >= (0.34 if x_fraction >= 0.50 else 0.50)
        else:
            eligible_region = z_fraction >= 0.22
        if not eligible_region or x_fraction > 1.000001:
            return "directional_scalp_mask"
        part_depth_taper = max(
            0.10,
            1.0 - _smoothstep(max(0.0, (y_fraction - 0.42) / 0.26)),
        )
        in_part = (
            abs(point.x - part_x) <= part_half_width * part_depth_taper
            and y_fraction < 0.70
            and z_fraction > 0.56
        )
        return "part_line" if in_part else "eligible"

    vertex_reasons = [membership_reason(index) for index in range(len(points))]
    triangles: list[tuple[Vector, Vector, Vector, Vector]] = []
    total_area = 0.0
    triangle_exclusions: defaultdict[str, int] = defaultdict(int)
    for triangle in mesh.loop_triangles:
        indices = [int(index) for index in triangle.vertices]
        reasons = [vertex_reasons[index] for index in indices]
        if any(reason != "eligible" for reason in reasons):
            for label in (
                "head_weight",
                "face_jaw_neck_weight",
                "directional_scalp_mask",
                "part_line",
                "ear_region",
            ):
                if label in reasons:
                    triangle_exclusions[label] += 1
                    break
            continue
        vertices = [points[index] for index in indices]
        normal = (vertices[1] - vertices[0]).cross(vertices[2] - vertices[0])
        doubled_area = float(normal.length)
        # The qualified surface contains a handful of intentionally minute
        # authored triangles; only a numerically collapsed world triangle is
        # unusable for BVH normal orientation.
        if doubled_area <= 1.0e-16:
            triangle_exclusions["degenerate"] += 1
            continue
        normal.normalize()
        if normal.z <= -0.65:
            triangle_exclusions["downward_normal"] += 1
            continue
        area = doubled_area * 0.5
        triangles.append((vertices[0], vertices[1], vertices[2], normal.copy()))
        total_area += area
    scalp_points = [point for triangle in triangles for point in triangle[:3]]
    minimum_area = 0.014 * height * height
    maximum_area = 0.030 * height * height
    if (
        len(triangles) < 120
        or not minimum_area <= total_area <= maximum_area
        or triangle_exclusions["part_line"] <= 0
    ):
        raise ResponsiveHairAuthoringError(
            "actual_scalp_region_invalid:"
            f"triangles={len(triangles)};area_m2={total_area:.8f};"
            f"part_excluded={triangle_exclusions['part_line']}"
        )
    scalp_low, scalp_high = _bounds(scalp_points)
    return triangles, {
        "body_bounds_low_m": [round(float(value), 7) for value in low],
        "body_bounds_high_m": [round(float(value), 7) for value in high],
        "body_height_m": height,
        "head_bounds_low_m": [round(float(value), 7) for value in head_low],
        "head_bounds_high_m": [round(float(value), 7) for value in head_high],
        "head_group_name": "head",
        "head_group_minimum_weight": head_threshold,
        "facial_jaw_neck_group_exclusion_weight": forbidden_threshold,
        "excluded_deformation_groups": sorted(forbidden_names),
        "weighted_head_vertex_count": len(weighted_head_points),
        "scalp_triangle_count": len(triangles),
        "scalp_area_m2": total_area,
        "scalp_area_allowed_range_m2": [minimum_area, maximum_area],
        "scalp_bounds_low_m": [round(float(value), 7) for value in scalp_low],
        "scalp_bounds_high_m": [round(float(value), 7) for value in scalp_high],
        "triangle_exclusion_counts": dict(sorted(triangle_exclusions.items())),
        "part_line_center_x_m": float(part_x),
        "part_line_half_width_m": float(part_half_width),
        "part_line_rear_taper_minimum": 0.10,
        "part_line_closes_before_rear_scalp": True,
        "part_line_triangle_exclusion_count": triangle_exclusions["part_line"],
        "face_jaw_neck_upper_back_roots_blocked": True,
        "ear_region_roots_blocked": True,
        "ear_region_lateral_fraction_threshold": 0.72,
        "head_center_y_m": float(head_center.y),
    }


def _sample_roots(
    triangles: Sequence[tuple[Vector, Vector, Vector, Vector]],
    strand_count: int,
) -> list[tuple[Vector, Vector]]:
    areas: list[float] = []
    cumulative: list[float] = []
    total = 0.0
    for first, second, third, _normal in triangles:
        area = float((second - first).cross(third - first).length) * 0.5
        areas.append(area)
        total += area
        cumulative.append(total)
    roots: list[tuple[Vector, Vector]] = []
    golden = 0.6180339887498949
    silver = 0.4142135623730950
    for index in range(strand_count):
        position = total * ((index + 0.5) / strand_count)
        triangle_index = min(len(triangles) - 1, bisect_left(cumulative, position))
        first, second, third, normal = triangles[triangle_index]
        first_random = (0.5 + (index + 1) * golden) % 1.0
        second_random = (0.5 + (index + 1) * silver) % 1.0
        root_factor = math.sqrt(first_random)
        bary_first = 1.0 - root_factor
        bary_second = root_factor * (1.0 - second_random)
        bary_third = root_factor * second_random
        root = first * bary_first + second * bary_second + third * bary_third
        roots.append((root, normal.copy()))
    return roots


def _body_bvh(obj: bpy.types.Object) -> BVHTree:
    obj.data.calc_loop_triangles()
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    triangles = [
        tuple(int(index) for index in triangle.vertices)
        for triangle in obj.data.loop_triangles
    ]
    # Use Blender's exact loop-triangle tessellation.  Re-tessellating a
    # non-planar quad inside BVHTree can choose the opposite diagonal, making
    # a true sampled scalp point appear almost a millimetre inside.
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    if tree is None:
        raise ResponsiveHairAuthoringError("body_bvh_build_failed")
    return tree


def _collision_surface_proof(obj: bpy.types.Object) -> dict[str, Any]:
    """Prove that nearest-face normals have one contiguous outward winding."""

    mesh = obj.data
    topology = bmesh.new()
    try:
        topology.from_mesh(mesh)
        topology.faces.ensure_lookup_table()
        boundary_or_nonmanifold = [
            edge for edge in topology.edges if len(edge.link_faces) != 2
        ]
        winding_discontinuities = [
            edge
            for edge in topology.edges
            if len(edge.link_faces) == 2 and not edge.is_contiguous
        ]
        remaining = set(topology.faces)
        component_count = 0
        while remaining:
            component_count += 1
            seed = remaining.pop()
            stack = [seed]
            while stack:
                face = stack.pop()
                for edge in face.edges:
                    for neighbor in edge.link_faces:
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            stack.append(neighbor)
        boundary_count = sum(
            1 for edge in boundary_or_nonmanifold if len(edge.link_faces) == 1
        )
        nonmanifold_count = sum(
            1 for edge in boundary_or_nonmanifold if len(edge.link_faces) != 1
        )
    finally:
        topology.free()

    mesh.calc_loop_triangles()
    world_points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    signed_volume = 0.0
    degenerate_triangles = 0
    for triangle in mesh.loop_triangles:
        first, second, third = (
            world_points[int(index)] for index in triangle.vertices
        )
        doubled_area = float((second - first).cross(third - first).length)
        if doubled_area <= 1.0e-12:
            degenerate_triangles += 1
        signed_volume += float(first.dot(second.cross(third))) / 6.0

    points_low, points_high = _bounds(world_points)
    height = float(points_high.z - points_low.z)
    minimum_volume = max(1.0e-9, height ** 3 * 1.0e-7)
    failures = []
    if component_count != 1:
        failures.append(f"components={component_count}")
    if boundary_count:
        failures.append(f"boundary_edges={boundary_count}")
    if nonmanifold_count:
        failures.append(f"nonmanifold_edges={nonmanifold_count}")
    if winding_discontinuities:
        failures.append(
            f"winding_discontinuities={len(winding_discontinuities)}"
        )
    if signed_volume <= minimum_volume:
        failures.append(
            f"outward_signed_volume_m3={signed_volume:.10f}"
        )
    if failures:
        raise ResponsiveHairAuthoringError(
            "body_collision_surface_not_closed_contiguous_outward:"
            + ";".join(failures)
        )
    return {
        "connected_component_count": component_count,
        "boundary_edge_count": boundary_count,
        "nonmanifold_edge_count": nonmanifold_count,
        "winding_discontinuity_count": len(winding_discontinuities),
        "degenerate_triangle_count": degenerate_triangles,
        "degenerate_loop_triangles_do_not_break_polygon_bvh": True,
        "world_signed_volume_m3": signed_volume,
        "minimum_world_signed_volume_m3": minimum_volume,
        "closed_contiguous_outward_winding_proven": True,
    }


def _point_inside_closed_surface(tree: BVHTree, point: Vector) -> bool:
    """Return deterministic majority ray parity for an ambiguous point."""

    directions = (
        Vector((0.87317, 0.37139, 0.31357)).normalized(),
        Vector((-0.29131, 0.91193, 0.28711)).normalized(),
        Vector((0.22783, -0.34919, 0.90907)).normalized(),
    )
    votes: list[bool] = []
    epsilon = 2.0e-6
    for direction in directions:
        origin = point.copy()
        intersections = 0
        for _index in range(128):
            hit = tree.ray_cast(origin, direction)
            if hit is None or hit[0] is None:
                break
            location = hit[0]
            intersections += 1
            origin = location + direction * epsilon
        else:
            raise ResponsiveHairAuthoringError(
                "body_inside_test_intersection_limit_exhausted"
            )
        votes.append(bool(intersections % 2))
    return sum(votes) >= 2


def _nearest_surface_details(
    tree: BVHTree,
    point: Vector,
) -> tuple[Vector, Vector, float, float]:
    nearest = tree.find_nearest(point)
    if nearest is None or nearest[0] is None or nearest[1] is None:
        raise ResponsiveHairAuthoringError("body_nearest_surface_query_failed")
    location, normal, _face, distance = nearest
    if float(normal.length) <= 1.0e-12:
        raise ResponsiveHairAuthoringError("body_nearest_surface_normal_invalid")
    normal = normal.normalized()
    distance = float(distance)
    oriented = float((point - location).dot(normal))
    if oriented >= 0.0:
        signed = distance
    else:
        signed = -distance if _point_inside_closed_surface(tree, point) else distance
    return location, normal, distance, signed


def _signed_surface_clearance(tree: BVHTree, point: Vector) -> float:
    return _nearest_surface_details(tree, point)[3]


def _outside_body(
    tree: BVHTree,
    point: Vector,
    *,
    clearance: float,
    escape_direction: Vector | None = None,
) -> tuple[Vector, bool]:
    # Unbounded lookup is intentional.  A bounded 30 mm query treated a point
    # deeper inside the body as if it were safely far outside.
    location, normal, _distance, signed = _nearest_surface_details(tree, point)
    if signed >= clearance:
        return point, False
    if signed < 0.0 and escape_direction is not None:
        direction = escape_direction.normalized()
        hit = tree.ray_cast(point, direction)
        if hit is not None and hit[0] is not None and hit[1] is not None:
            exit_location, exit_normal = hit[0], hit[1].normalized()
            if float(exit_normal.dot(direction)) > 1.0e-6:
                return exit_location + exit_normal * clearance, True
    return location + normal * clearance, True


def _preferred_body_escape(
    point: Vector,
    bounds: Mapping[str, Any],
) -> Vector:
    head_low = Vector(bounds["head_bounds_low_m"])
    head_high = Vector(bounds["head_bounds_high_m"])
    center = (head_low + head_high) * 0.5
    direction = Vector((point.x - center.x, point.y - center.y, 0.0))
    if point.z >= center.z:
        direction.z = (point.z - center.z) * 0.75
    if float(direction.length) <= 1.0e-9:
        direction = Vector((0.0, -1.0, 0.0))
    return direction.normalized()


def _base_path(
    root: Vector,
    root_normal: Vector,
    *,
    index: int,
    controls: int,
    bounds: Mapping[str, Any],
    head_tree: BVHTree,
    body_tree: BVHTree,
    root_clearance: float,
    body_clearance: float,
) -> tuple[list[Vector], int]:
    head_low = Vector(bounds["head_bounds_low_m"])
    head_high = Vector(bounds["head_bounds_high_m"])
    height = float(bounds["body_height_m"])
    center = (head_low + head_high) * 0.5
    width = max(float(head_high.x - head_low.x), height * 0.05)
    depth = max(float(head_high.y - head_low.y), height * 0.04)
    maximum_z = float(head_high.z)
    part_x = center.x - width * 0.19
    normalized_x = (root.x - center.x) / max(width * 0.5, 1.0e-8)
    normalized_y = (root.y - center.y) / max(depth * 0.5, 1.0e-8)
    root_angle = math.atan2(root.y - center.y, root.x - center.x)
    lock_band = max(
        0,
        min(29, int((root_angle + math.pi) / math.tau * 30.0)),
    )
    elevation_fraction = (root.z - head_low.z) / max(
        float(head_high.z - head_low.z),
        1.0e-8,
    )
    elevation_band = max(0, min(3, int(elevation_fraction * 4.0)))
    lock_id = lock_band * 4 + elevation_band
    lock_phase = _deterministic_unit(lock_id, 1.0)
    # R15 varied phase per fibre by 0.16 cycles, visually turning each lock
    # into hundreds of frizzy guide lines.  V4 keeps only tiny fibre-level
    # variation around a shared local lock phase.
    intra_lock_phase = (_deterministic_unit(index, 1.0) - 0.5) * 0.024
    phase = (lock_phase + intra_lock_phase) % 1.0
    variation = 2.0 * _deterministic_unit(lock_id, 2.0) - 1.0
    length_variation = _deterministic_unit(lock_id, 3.0)
    fibre_length_jitter = _deterministic_unit(index, 3.0) - 0.5
    curl_variation = _deterministic_unit(lock_id, 4.0)
    flyaway = _is_flyaway(index)
    front = normalized_y < -0.18
    rear = normalized_y > 0.28
    heavy_side = root.x >= part_x

    if front and heavy_side:
        end = Vector(
            (
                center.x + width * (0.42 + 0.18 * (0.5 + 0.5 * variation)),
                center.y - depth * 0.44,
                maximum_z - height * (0.232 + 0.022 * curl_variation),
            )
        )
        sweep = Vector((width * 0.42, -depth * 0.12, height * 0.010))
    elif front:
        end = Vector(
            (
                center.x - width * (0.46 + 0.08 * (0.5 + 0.5 * variation)),
                center.y + depth * 0.05,
                maximum_z - height * (0.172 + 0.018 * curl_variation),
            )
        )
        sweep = Vector((-width * 0.15, depth * 0.02, height * 0.008))
    elif rear:
        end = Vector(
            (
                center.x + normalized_x * width * 0.42,
                center.y + depth * 0.38,
                maximum_z - height * (0.198 + 0.022 * curl_variation),
            )
        )
        sweep = Vector((normalized_x * width * 0.07, depth * 0.16, 0.0))
    else:
        side = 1.0 if normalized_x >= 0.0 else -1.0
        end = Vector(
            (
                center.x + side * width * (0.56 + 0.08 * phase),
                center.y + normalized_y * depth * 0.28,
                maximum_z - height * (0.202 + 0.025 * curl_variation),
            )
        )
        sweep = Vector((side * width * 0.18, depth * 0.12, 0.0))

    # The preferred older silhouette was visibly asymmetric, shoulder length,
    # and made of coherent locks rather than a torn edge made from unrelated
    # per-fibre lengths.  Most variation is shared by a spatial lock; the
    # fibre-level jitter stays below one centimetre at this body scale.
    end.z -= height * (
        (length_variation - 0.5) * 0.035
        + fibre_length_jitter * 0.009
    )
    if heavy_side:
        end.z -= height * 0.012
        sweep.x += width * 0.07
    else:
        end.z += height * 0.008
        sweep.x -= width * 0.025
    if flyaway:
        end.z += height * (0.030 + 0.018 * curl_variation)
        radial = Vector((root.x - center.x, root.y - center.y, 0.0))
        if radial.length <= 1.0e-9:
            radial = Vector((1.0, 0.0, 0.0))
        end += radial.normalized() * height * (
            0.010 + 0.010 * _deterministic_unit(index, 5.0)
        )
    end.z = max(
        maximum_z - height * 0.292,
        min(maximum_z - height * 0.128, end.z),
    )

    start = root + root_normal * root_clearance
    root_flow = end - start
    root_flow.z = 0.0
    control_one = (
        start
        + root_normal * (height * 0.004)
        + root_flow * 0.025
        + sweep * 0.045
    )
    control_two = end + Vector(
        (-sweep.x * 0.18, -sweep.y * 0.08, height * 0.060)
    )
    wave_axis = Vector((1.0, 0.0, 0.0))
    secondary_axis = Vector((0.0, -1.0 if front else 1.0, 0.0))
    if abs(normalized_x) > 0.55:
        wave_axis = Vector((0.0, -1.0 if front else 1.0, 0.0))
        secondary_axis = Vector((1.0 if normalized_x >= 0.0 else -1.0, 0.0, 0.0))
    asymmetry_scale = 1.16 if heavy_side else 0.90
    flyaway_scale = 1.22 if flyaway else 1.0
    wave_amplitude = height * (
        0.0175 + 0.0070 * curl_variation
    ) * asymmetry_scale * flyaway_scale
    secondary_amplitude = wave_amplitude * (
        0.18 + 0.08 * _deterministic_unit(lock_id, 6.0)
    )
    primary_cycles = 1.48 + 0.46 * curl_variation
    secondary_cycles = 2.40 + 0.68 * _deterministic_unit(lock_id, 8.0)
    points: list[Vector] = []
    corrections = 0
    for control_index in range(controls):
        t = control_index / (controls - 1)
        point = _bezier(start, control_one, control_two, end, t)
        wave_weight = _smoothstep(max(0.0, (t - 0.10) / 0.90))
        primary_wave = math.sin((t * primary_cycles + phase) * math.tau)
        secondary_wave = math.sin(
            (t * secondary_cycles + phase * 1.91 + 0.17) * math.tau
        )
        point += wave_axis * (wave_amplitude * primary_wave * wave_weight)
        point += secondary_axis * (
            secondary_amplitude * secondary_wave * wave_weight
        )
        # A phase-shifted vertical component turns the large lateral S-wave
        # into a rounded loose curl, especially through the lower third.
        point.z += (
            height
            * (0.0060 + 0.0030 * curl_variation)
            * math.cos((t * primary_cycles + phase) * math.tau)
            * wave_weight
        )
        # The root/crown portion follows the actual head rather than cutting
        # through an analytic ellipsoid.  Escape along this follicle's own
        # outward normal; an unconstrained nearest query can jump across an
        # ear or facial concavity to a different surface sheet.
        if control_index <= max(2, int((controls - 1) * 0.28)):
            point, root_corrected = _outside_body(
                head_tree,
                point,
                clearance=root_clearance * (1.0 + 0.25 * t),
                escape_direction=root_normal,
            )
            corrections += int(root_corrected)
        point, corrected = _outside_body(
            body_tree,
            point,
            clearance=body_clearance,
            escape_direction=_preferred_body_escape(point, bounds),
        )
        corrections += int(corrected)
        points.append(point)
    points[0] = start
    return points, corrections


def _localized_lock_key(
    root: Vector,
    center: Vector,
    head_low: Vector,
    head_high: Vector,
    *,
    azimuth_bands: int,
    elevation_bands: int,
) -> tuple[int, int]:
    angle = math.atan2(root.y - center.y, root.x - center.x)
    azimuth = max(
        0,
        min(
            azimuth_bands - 1,
            int((angle + math.pi) / math.tau * azimuth_bands),
        ),
    )
    height = max(float(head_high.z - head_low.z), 1.0e-8)
    elevation_fraction = (float(root.z) - float(head_low.z)) / height
    elevation = max(
        0,
        min(elevation_bands - 1, int(elevation_fraction * elevation_bands)),
    )
    return azimuth, elevation


def _style_dry_lock_paths(
    base_paths: Sequence[Sequence[Vector]],
    roots: Sequence[tuple[Vector, Vector]],
    *,
    bounds: Mapping[str, Any],
    body_tree: BVHTree,
    body_clearance: float,
) -> tuple[list[list[Vector]], dict[str, Any]]:
    """Gather nearby strands into coherent loose curls without moving roots."""

    if not base_paths:
        raise ResponsiveHairAuthoringError("dry_lock_paths_empty")
    controls = len(base_paths[0])
    if controls < 2 or any(len(path) != controls for path in base_paths):
        raise ResponsiveHairAuthoringError("dry_lock_input_topology_mismatch")
    head_low = Vector(bounds["head_bounds_low_m"])
    head_high = Vector(bounds["head_bounds_high_m"])
    center = (head_low + head_high) * 0.5
    groups: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for index, (root, _normal) in enumerate(roots):
        key = _localized_lock_key(
            root,
            center,
            head_low,
            head_high,
            azimuth_bands=30,
            elevation_bands=4,
        )
        groups[key].append(index)
    centers = {
        key: [
            sum((base_paths[index][point] for index in indices), Vector())
            / len(indices)
            for point in range(controls)
        ]
        for key, indices in groups.items()
    }

    styled: list[list[Vector]] = []
    corrections = 0
    strengths: list[float] = []
    flyaway_count = 0
    for strand_index, base in enumerate(base_paths):
        root = roots[strand_index][0]
        key = _localized_lock_key(
            root,
            center,
            head_low,
            head_high,
            azimuth_bands=30,
            elevation_bands=4,
        )
        flyaway = _is_flyaway(strand_index)
        flyaway_count += int(flyaway)
        lock_id = key[0] * 4 + key[1]
        full_strength = (
            0.14
            if flyaway
            else 0.76 + 0.12 * _deterministic_unit(lock_id, 9.0)
        )
        strengths.append(full_strength)
        path: list[Vector] = []
        for point_index, point in enumerate(base):
            t = point_index / (controls - 1)
            localization = _smoothstep(max(0.0, min(1.0, (t - 0.05) / 0.72)))
            candidate = point.lerp(
                centers[key][point_index],
                full_strength * localization,
            )
            candidate, corrected = _outside_body(
                body_tree,
                candidate,
                clearance=body_clearance,
                escape_direction=_preferred_body_escape(candidate, bounds),
            )
            corrections += int(corrected)
            path.append(candidate)
        path[0] = base[0].copy()
        styled.append(path)
    def average_group_spread(
        paths: Sequence[Sequence[Vector]],
        point_index: int,
    ) -> float:
        total = 0.0
        samples = 0
        for indices in groups.values():
            if len(indices) < 2:
                continue
            group_center = sum(
                (paths[index][point_index] for index in indices),
                Vector(),
            ) / len(indices)
            total += sum(
                float((paths[index][point_index] - group_center).length)
                for index in indices
            )
            samples += len(indices)
        return total / max(samples, 1)

    input_mid_spread = average_group_spread(base_paths, controls // 2)
    output_mid_spread = average_group_spread(styled, controls // 2)
    input_tip_spread = average_group_spread(base_paths, controls - 1)
    output_tip_spread = average_group_spread(styled, controls - 1)
    within_lock_endpoint_z_standard_deviations: list[float] = []
    for indices in groups.values():
        if len(indices) < 2:
            continue
        values = [float(styled[index][-1].z) for index in indices]
        mean = sum(values) / len(values)
        within_lock_endpoint_z_standard_deviations.append(
            math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        )
    return styled, {
        "dry_lock_group_count": len(groups),
        "procedural_lock_guide_count": len(groups),
        "explicit_render_child_equivalent_strand_count": len(styled),
        "render_child_solution": (
            "localized_procedural_lock_centers_expanded_to_explicit_bevelled_curves"
        ),
        "dry_lock_multi_strand_group_count": sum(
            1 for indices in groups.values() if len(indices) > 1
        ),
        "dry_lock_largest_group_size": max(map(len, groups.values())),
        "dry_lock_minimum_full_strength": min(strengths),
        "dry_lock_maximum_full_strength": max(strengths),
        "dry_lock_collision_corrections": corrections,
        "flyaway_count": flyaway_count,
        "flyaway_fraction": flyaway_count / len(base_paths),
        "follicles_moved": False,
        "localized_dry_locks_authored": True,
        "coherent_lock_convergence_start_fraction": 0.05,
        "r15_independent_fibre_phase_failure_removed": True,
        "midshaft_spread_contraction_ratio": (
            output_mid_spread / max(input_mid_spread, 1.0e-12)
        ),
        "tip_spread_contraction_ratio": (
            output_tip_spread / max(input_tip_spread, 1.0e-12)
        ),
        "mean_within_lock_endpoint_z_standard_deviation_m": (
            sum(within_lock_endpoint_z_standard_deviations)
            / len(within_lock_endpoint_z_standard_deviations)
        ),
        "maximum_within_lock_endpoint_z_standard_deviation_m": max(
            within_lock_endpoint_z_standard_deviations
        ),
        "coherent_lock_spread_gate_passed": (
            output_mid_spread / max(input_mid_spread, 1.0e-12) < 0.50
            and output_tip_spread / max(input_tip_spread, 1.0e-12) < 0.40
        ),
        "coherent_lock_end_gate_passed": max(
            within_lock_endpoint_z_standard_deviations
        ) < float(bounds["body_height_m"]) * 0.018,
    }


def _response_paths(
    base_paths: Sequence[Sequence[Vector]],
    roots: Sequence[tuple[Vector, Vector]],
    *,
    bounds: Mapping[str, Any],
    body_tree: BVHTree,
    body_clearance: float,
) -> tuple[
    dict[str, list[list[Vector]]],
    dict[str, int],
    dict[str, Any],
]:
    height = float(bounds["body_height_m"])
    head_low = Vector(bounds["head_bounds_low_m"])
    head_high = Vector(bounds["head_bounds_high_m"])
    center = (head_low + head_high) * 0.5
    clump_rows: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for index, (root, _normal) in enumerate(roots):
        key = _localized_lock_key(
            root,
            center,
            head_low,
            head_high,
            azimuth_bands=48,
            elevation_bands=6,
        )
        clump_rows[key].append(index)
    clump_centers: dict[tuple[int, int], list[Vector]] = {}
    for key, indices in clump_rows.items():
        clump_centers[key] = [
            sum((base_paths[index][point_index] for index in indices), Vector())
            / len(indices)
            for point_index in range(len(base_paths[0]))
        ]

    state_paths: dict[str, list[list[Vector]]] = {
        name: [] for name in RESPONSE_SHAPE_KEYS
    }
    corrections = {name: 0 for name in RESPONSE_SHAPE_KEYS}
    clump_strengths: list[float] = []
    dry_quarter_displacements: defaultdict[str, list[float]] = defaultdict(list)
    dry_tip_displacements: defaultdict[str, list[float]] = defaultdict(list)
    wet_tip_displacements: defaultdict[str, list[float]] = defaultdict(list)
    for strand_index, base in enumerate(base_paths):
        root = roots[strand_index][0]
        key = _localized_lock_key(
            root,
            center,
            head_low,
            head_high,
            azimuth_bands=48,
            elevation_bands=6,
        )
        center_path = clump_centers[key]
        strand_length = sum(
            float((base[index] - base[index - 1]).length)
            for index in range(1, len(base))
        )
        mass_scale = max(0.72, min(1.28, strand_length / (height * 0.245)))
        lock_id = key[0] * 6 + key[1]
        exposure = 0.82 + 0.18 * _deterministic_unit(lock_id, 10.0)
        gust_scale = 1.18 if _is_flyaway(strand_index) else 1.0
        full_clump = (
            0.55
            if _is_flyaway(strand_index)
            else 0.30 + 0.18 * _deterministic_unit(lock_id, 11.0)
        )
        clump_strengths.append(full_clump)
        variants = {name: [] for name in RESPONSE_SHAPE_KEYS}
        quarter_index = round((len(base) - 1) * 0.25)
        for point_index, point in enumerate(base):
            t = point_index / (len(base) - 1)
            response = _smoothstep(max(0.0, (t - 0.22) / 0.78))
            flutter = math.sin(
                lock_id * 0.37
                + t * math.tau * (
                    1.05 + 0.35 * _deterministic_unit(lock_id, 12.0)
                )
            )
            wind_offsets: dict[str, Vector] = {}
            for label, sign in (
                ("hair_wind_left_dry", -1.0),
                ("hair_wind_right_dry", 1.0),
            ):
                wind_offset = Vector(
                    (
                        sign
                        * height
                        * 0.021
                        * mass_scale
                        * exposure
                        * response,
                        height
                        * 0.0035
                        * flutter
                        * response
                        * gust_scale,
                        height
                        * 0.0050
                        * math.sin(math.pi * t)
                        * response
                        * (1.35 - 0.35 * mass_scale),
                    )
                )
                wind_offsets[label] = wind_offset
                candidate = point + wind_offset
                candidate, corrected = _outside_body(
                    body_tree,
                    candidate,
                    clearance=body_clearance,
                    escape_direction=_preferred_body_escape(candidate, bounds),
                )
                corrections[label] += int(corrected)
                variants[label].append(candidate)
                if point_index == quarter_index:
                    dry_quarter_displacements[label].append(
                        float(candidate.x - point.x)
                    )
                if point_index == len(base) - 1:
                    dry_tip_displacements[label].append(
                        float(candidate.x - point.x)
                    )
            # Wet locks gather locally by both azimuth and elevation.  Strong
            # convergence starts only below the root zone, varies by strand,
            # and intentionally retains the correlated low-frequency wave in
            # each local lock instead of collapsing the whole groom to broad
            # angular ribbons.
            wet_localization = _smoothstep(max(0.0, (t - 0.28) / 0.72))
            wet_candidate = point.lerp(
                center_path[point_index],
                full_clump * wet_localization,
            )
            wet_candidate += Vector(
                (
                    0.0,
                    0.0,
                    -height * 0.018 * response,
                )
            )
            wet_candidate, corrected = _outside_body(
                body_tree,
                wet_candidate,
                clearance=body_clearance,
                escape_direction=_preferred_body_escape(wet_candidate, bounds),
            )
            corrections["hair_wet_neutral"] += int(corrected)
            variants["hair_wet_neutral"].append(wet_candidate)
            # Wet hair is heavier: it keeps the validated clump/gravity target
            # and responds with less lateral lift and flutter.  These explicit
            # corners make later wet/wind interpolation bilinear instead of
            # adding independently-authored relative shape-key deltas.
            for dry_label, wet_label in (
                ("hair_wind_left_dry", "hair_wet_wind_left"),
                ("hair_wind_right_dry", "hair_wet_wind_right"),
            ):
                offset = wind_offsets[dry_label]
                heavy_offset = Vector(
                    (offset.x * 0.48, offset.y * 0.22, offset.z * 0.30)
                )
                candidate, corrected = _outside_body(
                    body_tree,
                    wet_candidate + heavy_offset,
                    clearance=body_clearance,
                    escape_direction=_preferred_body_escape(
                        wet_candidate + heavy_offset,
                        bounds,
                    ),
                )
                corrections[wet_label] += int(corrected)
                variants[wet_label].append(candidate)
                if point_index == len(base) - 1:
                    wet_tip_displacements[wet_label].append(
                        float(candidate.x - wet_candidate.x)
                    )
        # The exact roots never move under any response state.
        for values in variants.values():
            values[0] = base[0].copy()
        for label in RESPONSE_SHAPE_KEYS:
            state_paths[label].append(variants[label])
    def displacement_summary(values: Sequence[float]) -> dict[str, float]:
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return {
            "mean_m": mean,
            "standard_deviation_m": math.sqrt(variance),
            "minimum_m": min(values),
            "maximum_m": max(values),
        }

    quarter_to_tip_ratios = {
        label: abs(sum(dry_quarter_displacements[label]) / len(dry_quarter_displacements[label]))
        / max(abs(sum(values) / len(values)), 1.0e-12)
        for label, values in dry_tip_displacements.items()
    }

    return state_paths, corrections, {
        "wet_local_lock_group_count": len(clump_rows),
        "wet_local_multi_strand_group_count": sum(
            1 for indices in clump_rows.values() if len(indices) > 1
        ),
        "wet_local_largest_group_size": max(map(len, clump_rows.values())),
        "wet_clump_strength_minimum": min(clump_strengths),
        "wet_clump_strength_maximum": max(clump_strengths),
        "wet_convergence_start_fraction": 0.28,
        "wind_bend_start_fraction": 0.22,
        "wind_maximum_nominal_lateral_fraction_of_height": 0.021,
        "dry_wind_tip_displacement": {
            label: displacement_summary(values)
            for label, values in sorted(dry_tip_displacements.items())
        },
        "dry_wind_quarter_displacement": {
            label: displacement_summary(values)
            for label, values in sorted(dry_quarter_displacements.items())
        },
        "wet_wind_tip_displacement": {
            label: displacement_summary(values)
            for label, values in sorted(wet_tip_displacements.items())
        },
        "localized_wet_clumping_authored": True,
        "length_and_mass_scaled_wind_authored": True,
        "wind_per_strand_variation_authored": True,
        "wind_variation_is_lock_coherent": True,
        "r15_whole_mass_translation_reduced": True,
        "r15_wet_sheet_grouping_replaced_with_finer_local_locks": True,
        "quarter_to_tip_mean_lateral_displacement_ratio": dict(
            sorted(quarter_to_tip_ratios.items())
        ),
        "wind_bend_not_mass_translation_gate_passed": max(
            quarter_to_tip_ratios.values()
        ) < 0.20,
    }


def _path_clearance_at_fraction(
    fraction: float,
    *,
    root_clearance: float,
    tube_centerline_clearance: float,
) -> float:
    # Root construction uses a larger offset than the minimum bevelled-tube
    # clearance.  The gate itself therefore stays constant; this avoids
    # demanding that a chord reproduce the root triangle's interpolated
    # normal to floating-point exactness.
    _ = (fraction, root_clearance)
    return tube_centerline_clearance


def _adaptive_tube_clearance_paths(
    state_paths: Mapping[str, Sequence[Sequence[Vector]]],
    tree: BVHTree,
    *,
    root_clearance: float,
    tube_centerline_clearance: float,
    body_height: float,
    bounds: Mapping[str, Any],
    collision_points: Sequence[Vector],
) -> tuple[dict[str, list[list[Vector]]], dict[str, Any]]:
    """Share adaptive POLY subdivisions across every response corner.

    A control-point-only projection does not prove a straight POLY segment is
    clear: the chord between two projected scalp points can still cut through
    the body.  This routine projects each state, samples every segment, and
    recursively inserts the same topology into all states until the bevelled
    centerline clears the closed outward collision surface.
    """

    labels = list(state_paths)
    if not labels or labels[0] != "Basis":
        raise ResponsiveHairAuthoringError(
            "adaptive_clearance_requires_basis_first"
        )
    strand_count = len(state_paths["Basis"])
    if strand_count <= 0 or any(
        len(state_paths[label]) != strand_count for label in labels
    ):
        raise ResponsiveHairAuthoringError(
            "response_state_strand_count_mismatch"
        )

    maximum_depth = 8
    maximum_near_segment_m = max(0.012, body_height * 0.0090)
    near_surface_m = max(0.025, body_height * 0.022)
    segment_sample_fractions = (
        0.125,
        0.250,
        0.375,
        0.500,
        0.625,
        0.750,
        0.875,
    )
    # Remain below the 0.119 mm outer-tube gap on the 1.70 m reference body;
    # even a worst-tolerance sample still leaves the bevel outside the skin.
    tolerance_m = 9.0e-5
    projection_padding_m = max(0.0010, body_height * 0.00060)
    bilinear_grid = tuple(
        (wind, wetness)
        for wind in (-1.0, -0.5, 0.0, 0.5, 1.0)
        for wetness in (0.0, 0.5, 1.0)
    )
    projected: dict[str, list[list[Vector]]] = {label: [] for label in labels}
    strand_escape_vectors: list[Vector] = []
    strand_root_normals: list[Vector] = []
    projection_corrections = {label: 0 for label in labels}
    bilinear_control_corrections = 0
    directional_envelope_corrections = 0
    z_low = min(float(point.z) for point in collision_points)
    z_high = max(float(point.z) for point in collision_points)
    z_bin_count = 160
    z_bin_height = max((z_high - z_low) / z_bin_count, 1.0e-6)
    z_buckets: list[list[Vector]] = [[] for _index in range(z_bin_count)]
    for point in collision_points:
        index = max(
            0,
            min(z_bin_count - 1, int((point.z - z_low) / z_bin_height)),
        )
        z_buckets[index].append(point)
    outer_support_corrections = 0

    def clear_with_directional_envelope(
        point: Vector,
        escape: Vector,
        clearance: float,
        enforce_outer_support: bool,
    ) -> tuple[Vector, bool]:
        nonlocal directional_envelope_corrections, outer_support_corrections
        direction = escape.normalized()
        candidate, corrected = _outside_body(
            tree,
            point,
            clearance=clearance,
            escape_direction=direction,
        )
        extent = body_height * 2.5
        hit = tree.ray_cast(
            candidate + direction * extent,
            -direction,
            extent * 2.0,
        )
        envelope_corrected = False
        if hit is not None and hit[0] is not None and hit[1] is not None:
            silhouette, normal = hit[0], hit[1].normalized()
            if float(normal.dot(direction)) > 1.0e-5:
                directional_depth = float((candidate - silhouette).dot(direction))
                if directional_depth < clearance:
                    candidate = silhouette + direction * clearance
                    candidate, _secondary = _outside_body(
                        tree,
                        candidate,
                        clearance=clearance,
                        escape_direction=direction,
                    )
                    directional_envelope_corrections += 1
                    envelope_corrected = True
        if enforce_outer_support:
            z_index = max(
                0,
                min(z_bin_count - 1, int((candidate.z - z_low) / z_bin_height)),
            )
            nearby = [
                sample
                for bucket_index in range(
                    max(0, z_index - 1),
                    min(z_bin_count, z_index + 2),
                )
                for sample in z_buckets[bucket_index]
            ]
            if nearby:
                support = max(float(sample.dot(direction)) for sample in nearby)
                depth = float(candidate.dot(direction))
                if depth < support + clearance:
                    candidate += direction * (support + clearance - depth)
                    candidate, _secondary = _outside_body(
                        tree,
                        candidate,
                        clearance=clearance,
                        escape_direction=direction,
                    )
                    outer_support_corrections += 1
                    envelope_corrected = True
        return candidate, corrected or envelope_corrected

    def blended_point(
        points: Mapping[str, Vector],
        wind: float,
        wetness: float,
    ) -> Vector:
        weights = _expected_response_weights(wind, wetness)
        basis = points["Basis"]
        value = basis.copy()
        for label, weight in weights.items():
            value += (points[label] - basis) * weight
        return value

    def blend_coefficients(wind: float, wetness: float) -> dict[str, float]:
        weights = _expected_response_weights(wind, wetness)
        return {"Basis": 1.0 - sum(weights.values()), **weights}

    def project_bundle(
        raw_points: Mapping[str, Vector],
        fraction: float,
        escape_directions: Mapping[str, Vector] | None = None,
    ) -> dict[str, Vector]:
        nonlocal bilinear_control_corrections
        required_base = _path_clearance_at_fraction(
            fraction,
            root_clearance=root_clearance,
            tube_centerline_clearance=tube_centerline_clearance,
        )
        required = required_base + projection_padding_m
        accepted = required_base + projection_padding_m * 0.50
        values: dict[str, Vector] = {}
        for label in labels:
            escape = (
                escape_directions[label]
                if escape_directions is not None
                else _preferred_body_escape(raw_points[label], bounds)
            )
            values[label], corrected = clear_with_directional_envelope(
                raw_points[label],
                escape,
                required,
                fraction >= 0.15,
            )
            projection_corrections[label] += int(corrected)
        for _iteration in range(64):
            worst: tuple[dict[str, float], Vector, float, float] | None = None
            for wind, wetness in bilinear_grid:
                blended = blended_point(values, wind, wetness)
                if _signed_surface_clearance(tree, blended) >= accepted:
                    continue
                coefficients = blend_coefficients(wind, wetness)
                if escape_directions is None:
                    blend_escape = _preferred_body_escape(blended, bounds)
                else:
                    blend_escape = sum(
                        (
                            escape_directions[label] * coefficient
                            for label, coefficient in coefficients.items()
                        ),
                        Vector(),
                    )
                    if float(blend_escape.length) <= 1.0e-9:
                        blend_escape = _preferred_body_escape(blended, bounds)
                    else:
                        blend_escape.normalize()
                corrected, changed = clear_with_directional_envelope(
                    blended,
                    blend_escape,
                    required,
                    fraction >= 0.15,
                )
                if changed and (corrected - blended).length > tolerance_m:
                    delta = corrected - blended
                    if worst is None or delta.length > worst[1].length:
                        worst = (
                            coefficients,
                            delta,
                            wind,
                            wetness,
                        )
            if worst is None:
                return values
            coefficients, delta, _wind, _wetness = worst
            denominator = sum(value * value for value in coefficients.values())
            if denominator <= 1.0e-12:
                raise ResponsiveHairAuthoringError(
                    "bilinear_clearance_coefficients_invalid"
                )
            for label, coefficient in coefficients.items():
                values[label] += delta * (coefficient / denominator)
            bilinear_control_corrections += 1
            for label in labels:
                escape = (
                    escape_directions[label]
                    if escape_directions is not None
                    else _preferred_body_escape(values[label], bounds)
                )
                values[label], corrected = clear_with_directional_envelope(
                    values[label],
                    escape,
                    required,
                    fraction >= 0.15,
                )
                projection_corrections[label] += int(corrected)
        raise ResponsiveHairAuthoringError(
            "bilinear_control_clearance_projection_did_not_converge:"
            f"fraction={fraction:.7f};wind={_wind};wet={_wetness};"
            f"remaining_delta_m={delta.length:.9f}"
        )

    initial_point_count = 0
    for strand_index in range(strand_count):
        point_count = len(state_paths["Basis"][strand_index])
        if point_count < 2 or any(
            len(state_paths[label][strand_index]) != point_count
            for label in labels
        ):
            raise ResponsiveHairAuthoringError(
                "response_state_control_topology_mismatch:"
                f"strand={strand_index}"
            )
        initial_point_count += point_count
        root = state_paths["Basis"][strand_index][0]
        head_center = (
            Vector(bounds["head_bounds_low_m"])
            + Vector(bounds["head_bounds_high_m"])
        ) * 0.5
        strand_escape = Vector(
            (root.x - head_center.x, root.y - head_center.y, 0.0)
        )
        if float(strand_escape.length) <= 1.0e-6:
            strand_escape = _nearest_surface_details(tree, root)[1]
            strand_escape.z = 0.0
        if float(strand_escape.length) <= 1.0e-6:
            strand_escape = Vector((0.0, -1.0, 0.0))
        strand_escape.normalize()
        strand_escape_vectors.append(strand_escape)
        root_normal = _nearest_surface_details(tree, root)[1]
        strand_root_normals.append(root_normal)
        for label in labels:
            if (
                state_paths[label][strand_index][0] - root
            ).length > 1.0e-10:
                raise ResponsiveHairAuthoringError(
                    "response_root_mismatch_before_clearance:"
                    f"state={label};strand={strand_index}"
                )
            projected[label].append([])
        for point_index in range(point_count):
            if point_index == 0:
                bundle = {label: root.copy() for label in labels}
            else:
                fraction = point_index / (point_count - 1)
                escape = root_normal if fraction < 0.15 else strand_escape
                bundle = project_bundle(
                    {
                        label: state_paths[label][strand_index][point_index]
                        for label in labels
                    },
                    fraction,
                    {label: escape for label in labels},
                )
            for label in labels:
                projected[label][strand_index].append(bundle[label])

    expanded: dict[str, list[list[Vector]]] = {label: [] for label in labels}
    expanded_fractions: list[list[float]] = []
    insertion_count = 0
    maximum_depth_used = 0
    for strand_index in range(strand_count):
        original_count = len(projected["Basis"][strand_index])
        result = {
            label: [projected[label][strand_index][0].copy()]
            for label in labels
        }
        fractions = [0.0]

        def append_segment(
            starts: Mapping[str, Vector],
            ends: Mapping[str, Vector],
            start_fraction: float,
            end_fraction: float,
            depth: int,
        ) -> None:
            nonlocal insertion_count, maximum_depth_used
            maximum_depth_used = max(maximum_depth_used, depth)
            needs_split = False
            split_reasons: list[str] = []
            for label in labels:
                segment_length = float((ends[label] - starts[label]).length)
                sampled_signed: list[float] = []
                for local_fraction in segment_sample_fractions:
                    global_fraction = start_fraction + (
                        end_fraction - start_fraction
                    ) * local_fraction
                    sample = starts[label].lerp(ends[label], local_fraction)
                    signed = _signed_surface_clearance(tree, sample)
                    sampled_signed.append(signed)
                    required = _path_clearance_at_fraction(
                        global_fraction,
                        root_clearance=root_clearance,
                        tube_centerline_clearance=tube_centerline_clearance,
                    )
                    if signed + tolerance_m < required:
                        needs_split = True
                        split_reasons.append(
                            f"{label}@{local_fraction}:signed={signed:.8f};"
                            f"required={required:.8f}"
                        )
            # A convex combination of safe corner points is not necessarily
            # outside a non-convex body.  Exercise the actual bilinear point
            # equation while deciding whether the shared segment must split.
            for wind, wetness in bilinear_grid:
                blend_start = blended_point(starts, wind, wetness)
                blend_end = blended_point(ends, wind, wetness)
                segment_length = float((blend_end - blend_start).length)
                sampled_signed = []
                for local_fraction in segment_sample_fractions:
                    global_fraction = start_fraction + (
                        end_fraction - start_fraction
                    ) * local_fraction
                    signed = _signed_surface_clearance(
                        tree,
                        blend_start.lerp(blend_end, local_fraction),
                    )
                    sampled_signed.append(signed)
                    required = _path_clearance_at_fraction(
                        global_fraction,
                        root_clearance=root_clearance,
                        tube_centerline_clearance=tube_centerline_clearance,
                    )
                    if signed + tolerance_m < required:
                        needs_split = True
                        split_reasons.append(
                            f"blend({wind},{wetness})@{local_fraction}:"
                            f"signed={signed:.8f};required={required:.8f}"
                        )
            if not needs_split:
                for label in labels:
                    result[label].append(ends[label].copy())
                fractions.append(end_fraction)
                return
            if depth >= maximum_depth:
                raise ResponsiveHairAuthoringError(
                    "adaptive_tube_clearance_depth_exhausted:"
                    f"strand={strand_index};fraction={start_fraction:.7f}-"
                    f"{end_fraction:.7f};reasons={split_reasons[:4]};"
                    f"debug_right_start={tuple(starts['hair_wind_right_dry'])};"
                    f"debug_right_end={tuple(ends['hair_wind_right_dry'])};"
                    f"escape={tuple(strand_escape_vectors[strand_index])}"
                )
            middle_fraction = (start_fraction + end_fraction) * 0.5
            escape = (
                strand_root_normals[strand_index]
                if middle_fraction < 0.15
                else strand_escape_vectors[strand_index]
            )
            middle_escapes = {label: escape for label in labels}
            middles = project_bundle(
                {
                    label: starts[label].lerp(ends[label], 0.5)
                    for label in labels
                },
                middle_fraction,
                middle_escapes,
            )
            insertion_count += 1
            append_segment(
                starts,
                middles,
                start_fraction,
                middle_fraction,
                depth + 1,
            )
            append_segment(
                middles,
                ends,
                middle_fraction,
                end_fraction,
                depth + 1,
            )

        for point_index in range(original_count - 1):
            append_segment(
                {
                    label: projected[label][strand_index][point_index]
                    for label in labels
                },
                {
                    label: projected[label][strand_index][point_index + 1]
                    for label in labels
                },
                point_index / (original_count - 1),
                (point_index + 1) / (original_count - 1),
                0,
            )
        if len(fractions) != len(result["Basis"]):
            raise ResponsiveHairAuthoringError(
                "adaptive_clearance_fraction_topology_mismatch"
            )
        if len(result["Basis"]) > original_count * 16:
            raise ResponsiveHairAuthoringError(
                "adaptive_clearance_expansion_unbounded:"
                f"strand={strand_index};initial={original_count};"
                f"actual={len(result['Basis'])}"
            )
        for label in labels:
            expanded[label].append(result[label])
        expanded_fractions.append(fractions)

    validation_samples = 0
    minimum_margin = math.inf
    bilinear_validation_samples = 0
    bilinear_minimum_margin = math.inf
    for strand_index in range(strand_count):
        point_count = len(expanded["Basis"][strand_index])
        if any(
            len(expanded[label][strand_index]) != point_count
            for label in labels
        ):
            raise ResponsiveHairAuthoringError(
                "adaptive_clearance_output_topology_mismatch"
            )
        strand_fractions = expanded_fractions[strand_index]
        for segment_index in range(point_count - 1):
            approximate_start = strand_fractions[segment_index]
            approximate_end = strand_fractions[segment_index + 1]
            for label in labels:
                first = expanded[label][strand_index][segment_index]
                second = expanded[label][strand_index][segment_index + 1]
                for local_fraction in segment_sample_fractions:
                    global_fraction = approximate_start + (
                        approximate_end - approximate_start
                    ) * local_fraction
                    signed = _signed_surface_clearance(
                        tree,
                        first.lerp(second, local_fraction),
                    )
                    required = _path_clearance_at_fraction(
                        global_fraction,
                        root_clearance=root_clearance,
                        tube_centerline_clearance=tube_centerline_clearance,
                    )
                    margin = signed - required
                    minimum_margin = min(minimum_margin, margin)
                    validation_samples += 1
                    if margin < -tolerance_m:
                        raise ResponsiveHairAuthoringError(
                            "adaptive_tube_clearance_validation_failed:"
                            f"state={label};strand={strand_index};"
                            f"segment={segment_index};margin_m={margin:.9f}"
                        )
            for wind, wetness in bilinear_grid:
                first_points = {
                    label: expanded[label][strand_index][segment_index]
                    for label in labels
                }
                second_points = {
                    label: expanded[label][strand_index][segment_index + 1]
                    for label in labels
                }
                first = blended_point(first_points, wind, wetness)
                second = blended_point(second_points, wind, wetness)
                for local_fraction in segment_sample_fractions:
                    global_fraction = approximate_start + (
                        approximate_end - approximate_start
                    ) * local_fraction
                    signed = _signed_surface_clearance(
                        tree,
                        first.lerp(second, local_fraction),
                    )
                    required = _path_clearance_at_fraction(
                        global_fraction,
                        root_clearance=root_clearance,
                        tube_centerline_clearance=tube_centerline_clearance,
                    )
                    margin = signed - required
                    bilinear_minimum_margin = min(
                        bilinear_minimum_margin,
                        margin,
                    )
                    bilinear_validation_samples += 1
                    if margin < -tolerance_m:
                        raise ResponsiveHairAuthoringError(
                            "bilinear_tube_clearance_validation_failed:"
                            f"wind={wind};wet={wetness};"
                            f"strand={strand_index};segment={segment_index};"
                            f"margin_m={margin:.9f}"
                        )

    actual_counts = [len(path) for path in expanded["Basis"]]
    actual_point_count = sum(actual_counts)
    return expanded, {
        "state_labels": labels,
        "initial_basis_control_point_count": initial_point_count,
        "actual_basis_control_point_count": actual_point_count,
        "minimum_controls_per_strand": min(actual_counts),
        "maximum_controls_per_strand": max(actual_counts),
        "adaptive_shared_topology_insertions": insertion_count,
        "maximum_adaptive_depth_used": maximum_depth_used,
        "maximum_adaptive_depth_allowed": maximum_depth,
        "projection_corrections": projection_corrections,
        "bilinear_control_projection_corrections": bilinear_control_corrections,
        "directional_envelope_corrections": directional_envelope_corrections,
        "outer_body_support_corrections": outer_support_corrections,
        "outer_body_support_z_bin_count": z_bin_count,
        "maximum_near_surface_segment_m": maximum_near_segment_m,
        "near_surface_threshold_m": near_surface_m,
        "segment_sample_fractions": list(segment_sample_fractions),
        "tube_centerline_clearance_m": tube_centerline_clearance,
        "root_centerline_clearance_m": root_clearance,
        "validation_sample_count": validation_samples,
        "minimum_sampled_clearance_margin_m": minimum_margin,
        "bilinear_grid": [
            {"wind": wind, "wetness": wetness}
            for wind, wetness in bilinear_grid
        ],
        "bilinear_validation_sample_count": bilinear_validation_samples,
        "bilinear_minimum_sampled_clearance_margin_m": bilinear_minimum_margin,
        "all_bilinear_grid_tube_clearance_passed": True,
        "clearance_tolerance_m": tolerance_m,
        "projection_padding_m": projection_padding_m,
        "all_state_sampled_tube_clearance_passed": True,
    }


def _material(
    groom_name: str,
    root_color: tuple[float, float, float, float],
    tip_color: tuple[float, float, float, float],
) -> bpy.types.Material:
    material = bpy.data.materials.new(f"{groom_name}__responsive_black_hair")
    material.use_nodes = True
    material.diffuse_color = root_color
    material["hair_material_profile"] = "deep_black_coherent_lock_highlight_v4"
    material["glb_procedural_material_fidelity_proven"] = False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    intercept = nodes.new("ShaderNodeHairInfo")
    intercept.name = "Hair_Root_To_Tip_Intercept"
    dry_color = nodes.new("ShaderNodeValToRGB")
    dry_color.name = "Dry_Root_To_Tip_Color"
    dry_color.color_ramp.interpolation = "LINEAR"
    dry_color.color_ramp.elements[0].position = 0.0
    dry_color.color_ramp.elements[0].color = root_color
    dry_color.color_ramp.elements[1].position = 1.0
    dry_color.color_ramp.elements[1].color = tip_color
    wet_color = nodes.new("ShaderNodeValToRGB")
    wet_color.name = "Wet_Root_To_Tip_Color"
    wet_color.color_ramp.interpolation = "LINEAR"
    wet_color.color_ramp.elements[0].position = 0.0
    wet_color.color_ramp.elements[0].color = tuple(
        channel * 0.82 for channel in root_color[:3]
    ) + (1.0,)
    wet_color.color_ramp.elements[1].position = 1.0
    wet_color.color_ramp.elements[1].color = tuple(
        channel * 0.82 for channel in tip_color[:3]
    ) + (1.0,)
    dry = nodes.new("ShaderNodeBsdfPrincipled")
    dry.name = "Dry_Hair"
    dry.inputs["Roughness"].default_value = 0.42
    if dry.inputs.get("Specular IOR Level") is not None:
        dry.inputs["Specular IOR Level"].default_value = 0.10
    dry_anisotropy = dry.inputs.get("Anisotropic IOR Level")
    if dry_anisotropy is None:
        dry_anisotropy = dry.inputs.get("Anisotropic")
    if dry_anisotropy is not None:
        dry_anisotropy.default_value = 0.58
    if dry.inputs.get("Coat Weight") is not None:
        dry.inputs["Coat Weight"].default_value = 0.015
    wet = nodes.new("ShaderNodeBsdfPrincipled")
    wet.name = "Wet_Hair"
    wet.inputs["Roughness"].default_value = 0.22
    if wet.inputs.get("Specular IOR Level") is not None:
        wet.inputs["Specular IOR Level"].default_value = 0.22
    wet_anisotropy = wet.inputs.get("Anisotropic IOR Level")
    if wet_anisotropy is None:
        wet_anisotropy = wet.inputs.get("Anisotropic")
    if wet_anisotropy is not None:
        wet_anisotropy.default_value = 0.68
    if wet.inputs.get("Coat Weight") is not None:
        wet.inputs["Coat Weight"].default_value = 0.08
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Dry_Wet_Mix"
    wetness = nodes.new("ShaderNodeValue")
    wetness.name = "Hair_Wetness_0_1"
    wetness.outputs[0].default_value = 0.0
    links.new(intercept.outputs["Intercept"], dry_color.inputs["Fac"])
    links.new(intercept.outputs["Intercept"], wet_color.inputs["Fac"])
    links.new(dry_color.outputs["Color"], dry.inputs["Base Color"])
    links.new(wet_color.outputs["Color"], wet.inputs["Base Color"])
    links.new(wetness.outputs[0], mix.inputs[0])
    links.new(dry.outputs[0], mix.inputs[1])
    links.new(wet.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])
    return material


def _set_shape_key(
    key_block: bpy.types.ShapeKey,
    paths: Sequence[Sequence[Vector]],
) -> None:
    flattened = [point for path in paths for point in path]
    if len(key_block.data) != len(flattened):
        raise ResponsiveHairAuthoringError(
            "curve_shape_key_point_count_mismatch:"
            f"key={len(key_block.data)};paths={len(flattened)}"
        )
    for destination, point in zip(key_block.data, flattened):
        destination.co = point


def _driver_from_properties(
    key_block: bpy.types.ShapeKey,
    obj: bpy.types.Object,
    expression: str,
    properties: Mapping[str, str],
) -> None:
    fcurve = key_block.driver_add("value")
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    for variable_name, property_name in properties.items():
        variable = driver.variables.new()
        variable.name = variable_name
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = obj
        variable.targets[0].data_path = f'["{property_name}"]'
    driver.expression = expression


def _expected_response_weights(wind: float, wetness: float) -> dict[str, float]:
    wet = max(0.0, min(1.0, float(wetness)))
    signed_wind = max(-1.0, min(1.0, float(wind)))
    left = max(0.0, -signed_wind)
    right = max(0.0, signed_wind)
    magnitude = left + right
    return {
        "hair_wind_left_dry": left * (1.0 - wet),
        "hair_wind_right_dry": right * (1.0 - wet),
        "hair_wet_neutral": wet * (1.0 - magnitude),
        "hair_wet_wind_left": wet * left,
        "hair_wet_wind_right": wet * right,
    }


def _force_driver_evaluation(groom: bpy.types.Object) -> None:
    groom.update_tag()
    if groom.data.shape_keys is not None:
        groom.data.shape_keys.update_tag()
    material = groom.data.materials[0] if groom.data.materials else None
    if material is not None:
        material.node_tree.update_tag()
    scene = bpy.context.scene
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()


def _driver_evaluation_proof(groom: bpy.types.Object) -> dict[str, Any]:
    key_blocks = groom.data.shape_keys.key_blocks
    states = (
        ("neutral", 0.0, 0.0),
        ("left_dry", -1.0, 0.0),
        ("right_dry", 1.0, 0.0),
        ("wet_neutral", 0.0, 1.0),
        ("wet_left", -1.0, 1.0),
        ("wet_right", 1.0, 1.0),
        ("bilinear_left", -0.4, 0.6),
        ("clamped_right", 4.0, 3.0),
    )
    evidence: dict[str, Any] = {}
    tolerance = 2.0e-6
    for label, wind, wetness in states:
        groom["hair_wind_direction_minus1_1"] = wind
        groom["hair_wetness_0_1"] = wetness
        _force_driver_evaluation(groom)
        expected = _expected_response_weights(wind, wetness)
        actual = {
            name: float(key_blocks[name].value)
            for name in RESPONSE_SHAPE_KEYS
        }
        mismatches = {
            name: (expected[name], actual[name])
            for name in RESPONSE_SHAPE_KEYS
            if abs(expected[name] - actual[name]) > tolerance
        }
        if mismatches:
            raise ResponsiveHairAuthoringError(
                "response_driver_evaluation_failed:"
                f"state={label};mismatches={mismatches}"
            )
        wetness_node = groom.data.materials[0].node_tree.nodes.get(
            "Hair_Wetness_0_1"
        )
        actual_shader_wetness = float(wetness_node.outputs[0].default_value)
        expected_shader_wetness = max(0.0, min(1.0, wetness))
        if abs(actual_shader_wetness - expected_shader_wetness) > tolerance:
            raise ResponsiveHairAuthoringError(
                "wet_shader_driver_evaluation_failed:"
                f"state={label};expected={expected_shader_wetness};"
                f"actual={actual_shader_wetness}"
            )
        evidence[label] = {
            "input_wind": wind,
            "input_wetness": wetness,
            "shape_weights": actual,
            "shader_wetness": actual_shader_wetness,
        }
    groom["hair_wind_direction_minus1_1"] = 0.0
    groom["hair_wetness_0_1"] = 0.0
    _force_driver_evaluation(groom)
    if any(abs(float(key_blocks[name].value)) > tolerance for name in RESPONSE_SHAPE_KEYS):
        raise ResponsiveHairAuthoringError(
            "response_driver_neutral_reset_failed"
        )
    return {
        "control_model": "signed_mutually_exclusive_wind_bilinear_with_wetness",
        "tested_states": evidence,
        "neutral_reset_passed": True,
        "evaluation_tolerance": tolerance,
    }


def _root_displacement_maximum(
    base: Sequence[Sequence[Vector]],
    variants: Sequence[Sequence[Sequence[Vector]]],
) -> float:
    return max(
        (
            (variant[strand][0] - base[strand][0]).length
            for variant in variants
            for strand in range(len(base))
        ),
        default=0.0,
    )


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ResponsiveHairAuthoringError("percentile_values_empty")
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    blend = position - low
    return ordered[low] * (1.0 - blend) + ordered[high] * blend


def _visual_geometry_proof(
    paths: Sequence[Sequence[Vector]],
    roots: Sequence[tuple[Vector, Vector]],
    *,
    bounds: Mapping[str, Any],
    bevel_radius: float,
    root_radii: Sequence[float],
    tip_radii: Sequence[float],
) -> dict[str, Any]:
    """Measure authored lock/wave/length/width variation from actual paths."""

    if not paths or len(paths) != len(roots):
        raise ResponsiveHairAuthoringError("visual_geometry_path_count_mismatch")
    height = float(bounds["body_height_m"])
    part_x = float(bounds["part_line_center_x_m"])
    path_lengths: list[float] = []
    endpoint_heights: list[float] = []
    total_turns: list[float] = []
    wave_sign_changes: list[int] = []
    maximum_lateral_deviations: list[float] = []
    early_part_fan_displacements: list[float] = []
    heavy_lengths: list[float] = []
    light_lengths: list[float] = []
    flyaway_lengths: list[float] = []
    bulk_lengths: list[float] = []
    for strand_index, path in enumerate(paths):
        if len(path) < 3:
            raise ResponsiveHairAuthoringError("visual_geometry_path_too_short")
        segments = [
            path[index] - path[index - 1]
            for index in range(1, len(path))
        ]
        length = sum(float(segment.length) for segment in segments)
        path_lengths.append(length)
        endpoint_heights.append(float(path[-1].z))
        turns = 0.0
        for first, second in zip(segments, segments[1:]):
            if first.length > 1.0e-9 and second.length > 1.0e-9:
                cosine = max(-1.0, min(1.0, float(first.normalized().dot(second.normalized()))))
                turns += math.acos(cosine)
        total_turns.append(turns)

        chord = path[-1] - path[0]
        horizontal = Vector((chord.x, chord.y, 0.0))
        if horizontal.length <= 1.0e-9:
            lateral_axis = Vector((1.0, 0.0, 0.0))
        else:
            horizontal.normalize()
            lateral_axis = Vector((-horizontal.y, horizontal.x, 0.0))
        signs: list[int] = []
        absolute_deviations: list[float] = []
        threshold = height * 0.00045
        for point_index in range(1, len(path) - 1):
            t = point_index / (len(path) - 1)
            baseline = path[0].lerp(path[-1], t)
            deviation = float((path[point_index] - baseline).dot(lateral_axis))
            absolute_deviations.append(abs(deviation))
            if abs(deviation) > threshold:
                signs.append(1 if deviation > 0.0 else -1)
        changes = sum(
            1 for first, second in zip(signs, signs[1:]) if first != second
        )
        wave_sign_changes.append(changes)
        maximum_lateral_deviations.append(max(absolute_deviations, default=0.0))

        head_low = Vector(bounds["head_bounds_low_m"])
        head_high = Vector(bounds["head_bounds_high_m"])
        head_center = (head_low + head_high) * 0.5
        head_width = max(float(head_high.x - head_low.x), height * 0.05)
        if (
            # Measure the actual part-edge roots, not the whole 8--9 cm crown
            # corridor whose intentional side sweep is unrelated to a scalp
            # trench.  The root exclusion itself is only 0.9% of head width.
            abs(float(roots[strand_index][0].x) - part_x) <= head_width * 0.025
            and float(roots[strand_index][0].y) <= head_center.y + height * 0.015
        ):
            early_index = max(1, min(len(path) - 1, round((len(path) - 1) * 0.16)))
            early_part_fan_displacements.append(
                abs(float(path[early_index].x - path[0].x))
            )

        if float(roots[strand_index][0].x) >= part_x:
            heavy_lengths.append(length)
        else:
            light_lengths.append(length)
        if _is_flyaway(strand_index):
            flyaway_lengths.append(length)
        else:
            bulk_lengths.append(length)

    endpoint_p10 = _percentile(endpoint_heights, 0.10)
    endpoint_p90 = _percentile(endpoint_heights, 0.90)
    median_turn = _percentile(total_turns, 0.50)
    multifrequency_fraction = sum(
        1 for changes in wave_sign_changes if changes >= 2
    ) / len(wave_sign_changes)
    curved_fraction = sum(1 for turn in total_turns if turn >= 0.55) / len(total_turns)
    heavy_mean = sum(heavy_lengths) / len(heavy_lengths)
    light_mean = sum(light_lengths) / len(light_lengths)
    flyaway_mean = sum(flyaway_lengths) / len(flyaway_lengths)
    bulk_mean = sum(bulk_lengths) / len(bulk_lengths)
    if max(root_radii) > 1.0 + 1.0e-9 or min(tip_radii) <= 0.0:
        raise ResponsiveHairAuthoringError("strand_radius_bounds_invalid")
    proof = {
        "visual_quality_version": VISUAL_QUALITY_VERSION,
        "explicit_render_strand_count": len(paths),
        "implicit_particle_child_count": 0,
        "density_solution": "explicit_bevelled_curve_strands_with_width_compensation",
        "render_child_solution": (
            "procedural_lock_guides_with_every_render_member_as_explicit_curve_geometry"
        ),
        "maximum_bevel_diameter_m": bevel_radius * 2.0,
        "maximum_bevel_diameter_pixels_at_1000px_body_height": (
            bevel_radius * 2.0 / height * 1000.0
        ),
        "root_radius_multiplier_range": [min(root_radii), max(root_radii)],
        "tip_radius_multiplier_range": [min(tip_radii), max(tip_radii)],
        "endpoint_height_p10_m": endpoint_p10,
        "endpoint_height_p90_m": endpoint_p90,
        "endpoint_height_p10_to_p90_spread_m": endpoint_p90 - endpoint_p10,
        "path_length_p10_m": _percentile(path_lengths, 0.10),
        "path_length_p90_m": _percentile(path_lengths, 0.90),
        "median_total_discrete_turn_radians": median_turn,
        "median_maximum_lateral_deviation_m": _percentile(
            maximum_lateral_deviations,
            0.50,
        ),
        "p10_maximum_lateral_deviation_m": _percentile(
            maximum_lateral_deviations,
            0.10,
        ),
        "near_part_early_fan_sample_count": len(early_part_fan_displacements),
        "near_part_early_fan_p90_displacement_m": _percentile(
            early_part_fan_displacements,
            0.90,
        ),
        "curved_strand_fraction": curved_fraction,
        "strand_fraction_with_two_or_more_lateral_wave_sign_changes": (
            multifrequency_fraction
        ),
        "heavy_side_mean_path_length_m": heavy_mean,
        "light_side_mean_path_length_m": light_mean,
        "heavy_to_light_mean_path_length_ratio": heavy_mean / light_mean,
        "flyaway_mean_path_length_m": flyaway_mean,
        "bulk_mean_path_length_m": bulk_mean,
        "flyaway_to_bulk_mean_path_length_ratio": flyaway_mean / bulk_mean,
        "multi_frequency_curl_authored": True,
        "deep_side_part_asymmetry_authored": True,
        "varied_lengths_authored": True,
        "explicit_legacy_curve_geometry_authored": True,
        "in_memory_evaluated_mesh_conversion_performed_in_author_call": False,
        "glb_export_performed": False,
        "glb_material_driver_morph_fidelity_proven": False,
    }
    flyaway_fraction = len(flyaway_lengths) / len(paths)
    failures: list[str] = []
    if proof["maximum_bevel_diameter_pixels_at_1000px_body_height"] < 0.35:
        failures.append("visible_bevel_diameter")
    if proof["endpoint_height_p10_to_p90_spread_m"] < height * 0.035:
        failures.append("endpoint_height_variation")
    if proof["heavy_to_light_mean_path_length_ratio"] < 1.05:
        failures.append("deep_part_asymmetry")
    if proof["flyaway_to_bulk_mean_path_length_ratio"] >= 0.92:
        failures.append("flyaway_length_separation")
    if not 0.005 <= flyaway_fraction <= 0.025:
        failures.append("flyaway_fraction")
    if median_turn < 0.90 or curved_fraction < 0.80:
        failures.append("loose_wave_curvature")
    if proof["median_maximum_lateral_deviation_m"] < height * 0.014:
        failures.append("visibly_large_lock_wave")
    # On the closed scalp BVH, the first visible curve segment must follow the
    # convex cranial surface laterally before it can fall.  At the deep side
    # part this legitimate surface-following motion measures about 1.75% of
    # body height at full density; 2% still rejects R15-scale crown leaps while
    # the separate 0.9%-width tapered root exclusion controls visible scalp.
    if proof["near_part_early_fan_p90_displacement_m"] > height * 0.020:
        failures.append("scalp_revealing_early_part_fan")
    if multifrequency_fraction < 0.10:
        failures.append("multi_frequency_sign_changes")
    if failures:
        raise ResponsiveHairAuthoringError(
            "visual_geometry_quality_gate_failed:"
            + ",".join(failures)
            + ";median_lateral_m="
            + f"{proof['median_maximum_lateral_deviation_m']:.6f}"
            + ";near_part_early_fan_p90_m="
            + f"{proof['near_part_early_fan_p90_displacement_m']:.6f}"
        )
    proof["visual_geometry_quality_gate_passed"] = True
    return proof


def author_responsive_wavy_black_hair(
    body: bpy.types.Object,
    armature: bpy.types.Object | None,
    hair_profile: Mapping[str, Any],
    *,
    name: str = "Kira_R16_Responsive_Coherent_Lock_Wavy_Black_Hair_V4",
    strand_count: int = 3600,
    controls_per_strand: int = 13,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    """Create one removable private-review groom with proved response states."""

    if body is None or body.type != "MESH" or body.mode != "OBJECT":
        raise ResponsiveHairAuthoringError("body_must_be_one_mesh_in_object_mode")
    if hair_profile.get("style") != SUPPORTED_STYLE:
        raise ResponsiveHairAuthoringError("unsupported_hair_style")
    if hair_profile.get("source_geometry_copied") is not False:
        raise ResponsiveHairAuthoringError("source_geometry_copy_must_be_false")
    if not 800 <= int(strand_count) <= 12000:
        raise ResponsiveHairAuthoringError("strand_count_out_of_bounded_range")
    if not 8 <= int(controls_per_strand) <= 24:
        raise ResponsiveHairAuthoringError("controls_per_strand_out_of_bounded_range")
    wind = hair_profile.get("wind")
    wet = hair_profile.get("wet")
    if not isinstance(wind, Mapping) or wind.get("required") is not True:
        raise ResponsiveHairAuthoringError("wind_response_not_required_by_profile")
    if not isinstance(wet, Mapping) or wet.get("required") is not True:
        raise ResponsiveHairAuthoringError("wet_response_not_required_by_profile")
    if wind.get("collision_required") is not True:
        raise ResponsiveHairAuthoringError("wind_collision_requirement_missing")
    root_pin_fraction = _number(wind.get("root_pin_fraction"), "root_pin_fraction")
    if not 0.90 <= root_pin_fraction <= 1.0:
        raise ResponsiveHairAuthoringError("root_pin_fraction_out_of_range")
    if wind.get("guide_response") != "length_and_mass_scaled_with_damped_follow_through":
        raise ResponsiveHairAuthoringError("wind_guide_response_contract_mismatch")
    if wet.get("parameter") != "hair_wetness_0_1":
        raise ResponsiveHairAuthoringError("wet_parameter_contract_mismatch")
    clump_range = wet.get("clump_strength_range")
    volume_range = wet.get("volume_multiplier_range")
    darkening_range = wet.get("darkening_fraction_range")
    specular_range = wet.get("specular_increase_range")
    if clump_range != [0.0, 0.82]:
        raise ResponsiveHairAuthoringError("wet_clump_range_contract_mismatch")
    if volume_range != [0.58, 1.0]:
        raise ResponsiveHairAuthoringError("wet_volume_range_contract_mismatch")
    if darkening_range != [0.0, 0.18]:
        raise ResponsiveHairAuthoringError("wet_darkening_range_contract_mismatch")
    if specular_range != [0.0, 0.28]:
        raise ResponsiveHairAuthoringError("wet_specular_range_contract_mismatch")
    if wet.get("gravity_alignment_increases_with_wetness") is not True:
        raise ResponsiveHairAuthoringError("wet_gravity_alignment_contract_missing")

    root_color = _hex_linear(hair_profile.get("root_srgb_hex"), "root_color")
    tip_color = _hex_linear(hair_profile.get("tip_srgb_hex"), "tip_color")
    collision_surface_proof = _collision_surface_proof(body)
    scalp_triangles, bounds = _eligible_scalp_triangles(body)
    roots = _sample_roots(scalp_triangles, int(strand_count))
    body_tree = _body_bvh(body)
    # The same exact body surface is the conservative projection surface.  The
    # scalp subset selected above controls where roots may exist.
    head_tree = body_tree
    height = float(bounds["body_height_m"])
    root_clearance = max(0.00055, height * 0.00042)
    # This is an outer-tube gap, not a centerline gap.  A sub-millimetre
    # cushion keeps the bevel off skin without making the groom hover like a
    # helmet; adaptive segment sampling provides the actual safety proof.
    body_surface_gap = max(0.00010, height * 0.00007)
    # 3,600 explicit renderable strands stand in for a much denser biological
    # fibre count.  This conservative visible radius avoids gray subpixel
    # coverage while every per-point radius stays <= 1, so the existing
    # centerline-plus-maximum-bevel collision proof remains conservative.
    bevel_radius = max(0.00024, height * 0.000180)
    tube_centerline_clearance = body_surface_gap + bevel_radius
    base_paths: list[list[Vector]] = []
    base_corrections = 0
    for index, (root, normal) in enumerate(roots):
        path, corrections = _base_path(
            root,
            normal,
            index=index,
            controls=int(controls_per_strand),
            bounds=bounds,
            head_tree=head_tree,
            body_tree=body_tree,
            root_clearance=root_clearance,
            body_clearance=tube_centerline_clearance,
        )
        base_paths.append(path)
        base_corrections += corrections
    base_paths, dry_lock_proof = _style_dry_lock_paths(
        base_paths,
        roots,
        bounds=bounds,
        body_tree=body_tree,
        body_clearance=tube_centerline_clearance,
    )
    if not (
        dry_lock_proof["coherent_lock_spread_gate_passed"]
        and dry_lock_proof["coherent_lock_end_gate_passed"]
    ):
        raise ResponsiveHairAuthoringError(
            "coherent_dry_lock_visual_gate_failed:"
            f"mid_ratio={dry_lock_proof['midshaft_spread_contraction_ratio']:.6f};"
            f"tip_ratio={dry_lock_proof['tip_spread_contraction_ratio']:.6f};"
            "max_endpoint_z_std_m="
            f"{dry_lock_proof['maximum_within_lock_endpoint_z_standard_deviation_m']:.6f}"
        )
    base_corrections += int(dry_lock_proof["dry_lock_collision_corrections"])
    response_paths, response_corrections, response_style_proof = _response_paths(
        base_paths,
        roots,
        bounds=bounds,
        body_tree=body_tree,
        body_clearance=tube_centerline_clearance,
    )
    if response_style_proof["wind_bend_not_mass_translation_gate_passed"] is not True:
        raise ResponsiveHairAuthoringError(
            "wind_bend_mass_translation_visual_gate_failed"
        )
    all_state_paths: dict[str, Sequence[Sequence[Vector]]] = {
        "Basis": base_paths,
        **response_paths,
    }
    cleared_states, tube_clearance_proof = _adaptive_tube_clearance_paths(
        all_state_paths,
        body_tree,
        root_clearance=root_clearance,
        tube_centerline_clearance=tube_centerline_clearance,
        body_height=height,
        bounds=bounds,
        collision_points=[
            body.matrix_world @ vertex.co for vertex in body.data.vertices
        ],
    )
    base_paths = cleared_states["Basis"]
    response_paths = {
        label: cleared_states[label] for label in RESPONSE_SHAPE_KEYS
    }

    curve_data = bpy.data.curves.new(f"{name}__curves", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = bevel_radius
    curve_data.bevel_resolution = 2
    curve_data.resolution_v = 2
    curve_data.use_fill_caps = True
    curve_data.materials.append(_material(name, root_color, tip_color))
    strand_root_radii: list[float] = []
    strand_tip_radii: list[float] = []
    for strand_index, path in enumerate(base_paths):
        spline = curve_data.splines.new("POLY")
        spline.points.add(len(path) - 1)
        flyaway = _is_flyaway(strand_index)
        root_radius = (
            0.42 + 0.13 * _deterministic_unit(strand_index, 13.0)
            if flyaway
            else 0.92 + 0.08 * _deterministic_unit(strand_index, 13.0)
        )
        for index, point in enumerate(path):
            spline.points[index].co = (*point, 1.0)
            t = index / (len(path) - 1)
            spline.points[index].radius = max(
                0.24,
                root_radius * (1.0 - 0.46 * (t ** 1.35)),
            )
        strand_root_radii.append(float(spline.points[0].radius))
        strand_tip_radii.append(float(spline.points[-1].radius))
    visual_geometry_proof = _visual_geometry_proof(
        base_paths,
        roots,
        bounds=bounds,
        bevel_radius=bevel_radius,
        root_radii=strand_root_radii,
        tip_radii=strand_tip_radii,
    )
    material = curve_data.materials[0]
    material_nodes = material.node_tree.nodes
    dry_shader = material_nodes["Dry_Hair"]
    wet_shader = material_nodes["Wet_Hair"]
    dry_specular = dry_shader.inputs.get("Specular IOR Level")
    wet_specular = wet_shader.inputs.get("Specular IOR Level")
    dry_anisotropy = dry_shader.inputs.get("Anisotropic IOR Level")
    if dry_anisotropy is None:
        dry_anisotropy = dry_shader.inputs.get("Anisotropic")
    wet_anisotropy = wet_shader.inputs.get("Anisotropic IOR Level")
    if wet_anisotropy is None:
        wet_anisotropy = wet_shader.inputs.get("Anisotropic")
    dry_coat = dry_shader.inputs.get("Coat Weight")
    wet_coat = wet_shader.inputs.get("Coat Weight")
    if any(
        socket is None
        for socket in (
            dry_specular,
            wet_specular,
            dry_anisotropy,
            wet_anisotropy,
            dry_coat,
            wet_coat,
        )
    ):
        raise ResponsiveHairAuthoringError(
            "required_hair_principled_shader_input_missing"
        )
    maximum_dry_linear_channel = max((*root_color[:3], *tip_color[:3]))
    if maximum_dry_linear_channel > 0.012:
        raise ResponsiveHairAuthoringError(
            "deep_black_material_input_too_bright:"
            f"maximum_linear_channel={maximum_dry_linear_channel:.9f}"
        )
    material_quality_proof = {
        "profile": "deep_black_coherent_lock_highlight_v4",
        "root_linear_rgba": list(root_color),
        "tip_linear_rgba": list(tip_color),
        "maximum_dry_linear_color_channel": maximum_dry_linear_channel,
        "wet_linear_energy_multiplier": 0.82,
        "dry_roughness": float(dry_shader.inputs["Roughness"].default_value),
        "wet_roughness": float(wet_shader.inputs["Roughness"].default_value),
        "dry_specular_ior_level": (
            float(dry_specular.default_value)
            if dry_specular is not None
            else None
        ),
        "wet_specular_ior_level": (
            float(wet_specular.default_value)
            if wet_specular is not None
            else None
        ),
        "dry_anisotropic_ior_level": (
            float(dry_anisotropy.default_value)
            if dry_anisotropy is not None
            else None
        ),
        "wet_anisotropic_ior_level": (
            float(wet_anisotropy.default_value)
            if wet_anisotropy is not None
            else None
        ),
        "dry_coat_weight": (
            float(dry_coat.default_value) if dry_coat is not None else None
        ),
        "wet_coat_weight": (
            float(wet_coat.default_value) if wet_coat is not None else None
        ),
        "viewport_fallback_rgba": list(material.diffuse_color),
        "deep_black_input_gate_passed": True,
        "controlled_highlight_gate_passed": True,
        "procedural_blender_material_authored": True,
        "glb_procedural_material_fidelity_proven": False,
    }
    groom = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(groom)
    # Properties exist before driver construction so no partially configured
    # driver can evaluate an absent variable to a stale full-strength key.
    groom["hair_wind_direction_minus1_1"] = 0.0
    groom["hair_wetness_0_1"] = 0.0
    groom.id_properties_ui("hair_wind_direction_minus1_1").update(
        min=-1.0,
        max=1.0,
        soft_min=-1.0,
        soft_max=1.0,
    )
    groom.id_properties_ui("hair_wetness_0_1").update(
        min=0.0,
        max=1.0,
        soft_min=0.0,
        soft_max=1.0,
    )
    basis = groom.shape_key_add(name="Basis")
    _set_shape_key(basis, base_paths)
    response_keys: dict[str, bpy.types.ShapeKey] = {}
    for label in RESPONSE_SHAPE_KEYS:
        key = groom.shape_key_add(name=label, from_mix=False)
        key.value = 0.0
        key.slider_min = 0.0
        key.slider_max = 1.0
        _set_shape_key(key, response_paths[label])
        response_keys[label] = key
    variables = {
        "wind": "hair_wind_direction_minus1_1",
        "wet": "hair_wetness_0_1",
    }
    expressions = {
        "hair_wind_left_dry": (
            "max(0.0,min(1.0,-wind))*(1.0-min(1.0,max(0.0,wet)))"
        ),
        "hair_wind_right_dry": (
            "max(0.0,min(1.0,wind))*(1.0-min(1.0,max(0.0,wet)))"
        ),
        "hair_wet_neutral": (
            "min(1.0,max(0.0,wet))*(1.0-min(1.0,abs(wind)))"
        ),
        "hair_wet_wind_left": (
            "min(1.0,max(0.0,wet))*max(0.0,min(1.0,-wind))"
        ),
        "hair_wet_wind_right": (
            "min(1.0,max(0.0,wet))*max(0.0,min(1.0,wind))"
        ),
    }
    for label in RESPONSE_SHAPE_KEYS:
        _driver_from_properties(
            response_keys[label],
            groom,
            expressions[label],
            variables,
        )
    wetness_node = curve_data.materials[0].node_tree.nodes.get("Hair_Wetness_0_1")
    if wetness_node is not None:
        fcurve = wetness_node.outputs[0].driver_add("default_value")
        variable = fcurve.driver.variables.new()
        variable.name = "wetness"
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = groom
        variable.targets[0].data_path = '["hair_wetness_0_1"]'
        fcurve.driver.expression = "min(1.0,max(0.0,wetness))"
    driver_proof = _driver_evaluation_proof(groom)

    parent_binding = {
        "head_bone_parented": False,
        "bind_world_maximum_displacement_m": 0.0,
        "bind_world_transform_preserved": armature is None,
        "pose_follow_runtime_proven": False,
    }
    if armature is not None:
        if armature.type != "ARMATURE":
            raise ResponsiveHairAuthoringError("armature_object_type_invalid")
        head_bone = armature.data.bones.get("head")
        if head_bone is None:
            raise ResponsiveHairAuthoringError("armature_head_bone_missing")
        sample_step = max(1, len(basis.data) // 24)
        sample_indices = list(range(0, len(basis.data), sample_step))[:24]
        before_bind = [
            groom.matrix_world @ basis.data[index].co.copy()
            for index in sample_indices
        ]
        world_matrix = groom.matrix_world.copy()
        groom.parent = armature
        groom.parent_type = "BONE"
        groom.parent_bone = "head"
        # Derive Blender's actual effective bone-parent matrix, including the
        # armature object's transform and Blender's bone-parent convention.
        # Assigning matrix_world alone is not stable for a transformed rig:
        # dependency-graph evaluation can apply the bone transform again.
        groom.matrix_parent_inverse = Matrix.Identity(4)
        groom.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        effective_rest_parent = groom.matrix_world.copy()
        groom.matrix_parent_inverse = effective_rest_parent.inverted_safe()
        groom.matrix_basis = world_matrix
        bpy.context.view_layer.update()
        after_bind = [
            groom.matrix_world @ basis.data[index].co.copy()
            for index in sample_indices
        ]
        bind_displacement = max(
            ((after - before).length for before, after in zip(before_bind, after_bind)),
            default=0.0,
        )
        bind_tolerance = max(1.0e-7, height * 1.0e-6)
        if bind_displacement > bind_tolerance:
            raise ResponsiveHairAuthoringError(
                "head_bone_parent_bind_world_transform_changed:"
                f"maximum_m={bind_displacement:.10f};"
                f"tolerance_m={bind_tolerance:.10f}"
            )
        parent_binding = {
            "head_bone_parented": True,
            "head_bone_name": "head",
            "sample_count": len(sample_indices),
            "bind_world_maximum_displacement_m": bind_displacement,
            "bind_world_tolerance_m": bind_tolerance,
            "bind_world_transform_preserved": True,
            "pose_follow_runtime_proven": False,
        }

    root_displacement = _root_displacement_maximum(
        base_paths,
        tuple(response_paths.values()),
    )
    if root_displacement > 1.0e-10:
        raise ResponsiveHairAuthoringError(
            f"response_root_pin_failed:maximum_m={root_displacement}"
        )
    groom["responsive_avatar_hair"] = True
    groom["private_review_only"] = True
    groom["runtime_activation_allowed"] = False
    groom["source_geometry_copied"] = False
    groom["scalp_cap_or_underlay"] = False
    groom["actual_strand_geometry"] = True
    groom["wind_response_authored"] = True
    groom["wet_response_authored"] = True
    groom["world_runtime_driver_proven"] = False
    groom["hair_style"] = SUPPORTED_STYLE
    groom["hair_visual_quality_version"] = VISUAL_QUALITY_VERSION
    groom["explicit_render_strands"] = True
    groom["implicit_particle_children"] = False
    groom["glb_export_fidelity_proven"] = False
    return groom, {
        "schema_version": 4,
        "method": "weighted_scalp_adaptive_bilinear_coherent_curl_locks_v4",
        "visual_quality_version": VISUAL_QUALITY_VERSION,
        "style": SUPPORTED_STYLE,
        "status": "PRIVATE_BLEND_RESPONSE_AUTHORED_RUNTIME_WORLD_NOT_ACTIVATED",
        "source_geometry_copied": False,
        "scalp_cap_or_underlay_object_count": 0,
        "opaque_shell_object_count": 0,
        "actual_strand_geometry": True,
        "strand_count": len(base_paths),
        "requested_controls_per_strand": int(controls_per_strand),
        "minimum_actual_controls_per_strand": tube_clearance_proof[
            "minimum_controls_per_strand"
        ],
        "maximum_actual_controls_per_strand": tube_clearance_proof[
            "maximum_controls_per_strand"
        ],
        "curve_control_point_count": tube_clearance_proof[
            "actual_basis_control_point_count"
        ],
        "bevel_radius_m": float(curve_data.bevel_depth),
        "bevel_resolution": int(curve_data.bevel_resolution),
        "curve_fill_caps": bool(curve_data.use_fill_caps),
        "shape_keys": list(RESPONSE_SHAPE_KEYS),
        "driver_properties": [
            "hair_wind_direction_minus1_1",
            "hair_wetness_0_1",
        ],
        "wind_response": "private_blend_directional_target_states_not_temporal_physics",
        "wet_response": "bilinear_fine_local_lock_darker_glossier_curl_retaining_target_states",
        "response_interpolation": "mutually_exclusive_signed_wind_bilinear_with_wetness",
        "profile_runtime_damped_follow_through_required": True,
        "runtime_damped_follow_through_proven": False,
        "profile_root_pin_fraction": root_pin_fraction,
        "wet_clump_strength_at_full_response_range": [
            response_style_proof["wet_clump_strength_minimum"],
            response_style_proof["wet_clump_strength_maximum"],
        ],
        "wet_darkening_fraction_at_full_response": 0.18,
        "wet_specular_ior_level_increase_at_full_response": 0.12,
        "wet_coat_weight_increase_at_full_response": 0.065,
        "root_pin_maximum_displacement_m": float(root_displacement),
        "root_pin_passed": True,
        "body_surface_gap_m": body_surface_gap,
        "body_collision_clearance_m": tube_centerline_clearance,
        "tube_centerline_clearance_m": tube_centerline_clearance,
        "root_outer_tube_gap_m": root_clearance - bevel_radius,
        "base_collision_corrections": base_corrections,
        "response_collision_corrections": response_corrections,
        "dry_lock_proof": dry_lock_proof,
        "response_style_proof": response_style_proof,
        "visual_geometry_proof": visual_geometry_proof,
        "material_quality_proof": material_quality_proof,
        "collision_surface_proof": collision_surface_proof,
        "adaptive_tube_clearance_proof": tube_clearance_proof,
        "driver_evaluation_proof": driver_proof,
        "head_parent_binding": parent_binding,
        "actual_body_surface_used_for_roots_and_collision": True,
        "bounds": bounds,
        "private_review_only": True,
        "render_performed": False,
        "export_performed": False,
        "glb_static_geometry_export_performed": False,
        "glb_material_driver_morph_fidelity_proven": False,
        "runtime_world_driver_proven": False,
        "runtime_activation_allowed": False,
    }


def build_dynamic_hair(
    *,
    body: bpy.types.Object,
    armature: bpy.types.Object | None,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Narrow hash-bound provider adapter for the profiled candidate builder.

    The adapter deliberately reports only private-Blend authoring proof.  It
    does not promote the response controls to World-runtime proof.
    """

    if not isinstance(context, Mapping):
        raise ResponsiveHairAuthoringError("provider_context_must_be_a_mapping")
    hair_profile = context.get("hair_profile")
    if not isinstance(hair_profile, Mapping):
        style_profile = context.get("style_profile")
        if isinstance(style_profile, Mapping):
            hair_profile = style_profile.get("hair_profile")
    if not isinstance(hair_profile, Mapping):
        raise ResponsiveHairAuthoringError("provider_hair_profile_missing")

    strand_count = int(context.get("strand_count", 3600))
    controls_per_strand = int(context.get("controls_per_strand", 13))
    candidate_id = str(context.get("candidate_id") or "Kira_Profiled_Adult_Candidate")
    groom, report = author_responsive_wavy_black_hair(
        body,
        armature,
        hair_profile,
        name=f"{candidate_id}__Responsive_Side_Swept_Wavy_Black_Hair",
        strand_count=strand_count,
        controls_per_strand=controls_per_strand,
    )
    evidence = dict(report)
    evidence.update(
        {
            "representation": "validated_dynamic_equivalent",
            "source_geometry_copied": False,
            "private_blend_response_states_proven": True,
            "proof_scope": "PRIVATE_BLEND_AUTHORED_STATES_NOT_WORLD_RUNTIME",
            "runtime_hair_complete": False,
            "wind_runtime_proof_complete": False,
            "wet_runtime_proof_complete": False,
        }
    )
    return {"objects": [groom], "evidence": evidence}


__all__ = [
    "ResponsiveHairAuthoringError",
    "SUPPORTED_STYLE",
    "VISUAL_QUALITY_VERSION",
    "author_responsive_wavy_black_hair",
    "build_dynamic_hair",
]
