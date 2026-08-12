"""Narrow shading completion for R24 geometry Attempt 02.

The R19 patch's source UV island is incompatible with the torso texture.  This
keeps the same cross-boundary geometry repair, preserves the torso texture and
material outside the bounded region, and masks only the incompatible island
with a feathered vertex-color sample derived from the exact surrounding torso
texture.  No Blend is saved.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_broad_inplace_surface as base  # noqa: E402
from tools import blender_simulate_kira_r24_cross_boundary_fairing as fair  # noqa: E402
from tools import blender_simulate_kira_r24_attempt02_uv_repair as uvfix  # noqa: E402


SOURCE = base.SOURCE
SOURCE_SHA256 = base.SOURCE_SHA256
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_simulation/attempt_02_surface_shading_repair_retry_01"
)
VARIANT = dict(fair.VARIANTS[0])
VARIANT["id"] = "a_cross_boundary_fairing_feathered_surface_shading"
ATTRIBUTE = "R24_FeatheredSurfaceColor"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sample_image(image: bpy.types.Image, uv: Vector) -> tuple[float, float, float, float]:
    width, height = map(int, image.size)
    if width <= 0 or height <= 0:
        raise RuntimeError("torso base-color image has no pixels")
    x = min(width - 1, max(0, int((float(uv.x) % 1.0) * width)))
    y = min(height - 1, max(0, int((float(uv.y) % 1.0) * height)))
    offset = (y * width + x) * 4
    pixels = image.pixels
    return tuple(float(pixels[offset + axis]) for axis in range(4))


def exact_boundary_texture_mean(
    body: bpy.types.Object, patch_faces: set[int]
) -> tuple[tuple[float, float, float, float], dict[str, object]]:
    mesh = body.data
    uv_layer = mesh.uv_layers.active
    material = body.material_slots[0].material
    if uv_layer is None or material is None or material.node_tree is None:
        raise RuntimeError("exact torso UV/material authority is absent")
    image_node = material.node_tree.nodes.get("Image Texture")
    if image_node is None or image_node.image is None:
        raise RuntimeError("exact torso base-color image is absent")
    patch_vertices = {
        int(vertex) for face in patch_faces for vertex in mesh.polygons[face].vertices
    }
    torso_uvs: dict[int, list[Vector]] = defaultdict(list)
    for polygon in mesh.polygons:
        if int(polygon.index) in patch_faces:
            continue
        for loop_index in polygon.loop_indices:
            vertex = int(mesh.loops[loop_index].vertex_index)
            if vertex in patch_vertices:
                torso_uvs[vertex].append(uv_layer.data[loop_index].uv.copy())
    samples = [
        sample_image(image_node.image, uvfix.average(values))
        for _vertex, values in sorted(torso_uvs.items())
        if values
    ]
    if len(samples) < 20:
        raise RuntimeError(f"too few exact torso-side boundary texture samples: {len(samples)}")
    mean = tuple(sum(sample[axis] for sample in samples) / len(samples) for axis in range(4))
    return mean, {
        "image_name": image_node.image.name,
        "image_size": list(map(int, image_node.image.size)),
        "image_colorspace": image_node.image.colorspace_settings.name,
        "torso_side_sample_count": len(samples),
        "raw_linear_rgba_mean": list(mean),
    }


def tissue_mix(u: float, v: float) -> float:
    value = 0.0
    value = max(value, 0.42 * base.gaussian(u, v, -0.24, -0.02, 0.20, 0.48))
    value = max(value, 0.40 * base.gaussian(u, v, 0.25, -0.02, 0.20, 0.48))
    value = max(value, 0.30 * base.gaussian(u, v, 0.00, 0.01, 0.15, 0.34))
    value = max(value, 0.24 * base.gaussian(u, v, 0.00, 0.29, 0.16, 0.13))
    return min(0.42, value)


def install_feathered_surface_shading(
    body: bpy.types.Object,
    patch_faces: set[int],
    raw_skin: tuple[float, float, float, float],
    exterior_rings: int,
) -> dict[str, object]:
    mesh = body.data
    _neighbors, _edge_faces, face_neighbors, vertex_faces = fair.mesh_adjacency(mesh)
    face_distances = {int(face): 0 for face in patch_faces}
    queue = list(sorted(patch_faces))
    cursor = 0
    while cursor < len(queue):
        current = queue[cursor]
        cursor += 1
        if face_distances[current] >= exterior_rings:
            continue
        for neighbor in face_neighbors[current]:
            if neighbor not in face_distances:
                face_distances[neighbor] = face_distances[current] + 1
                queue.append(neighbor)
    region_faces = set(face_distances)
    attribute = mesh.color_attributes.get(ATTRIBUTE)
    if attribute is not None:
        mesh.color_attributes.remove(attribute)
    attribute = mesh.color_attributes.new(name=ATTRIBUTE, type="FLOAT_COLOR", domain="POINT")
    alpha_values = []
    tissue_values = []
    for vertex in mesh.vertices:
        incident = vertex_faces[int(vertex.index)]
        relevant = [face_distances[face] for face in incident if face in region_faces]
        if not relevant:
            attribute.data[int(vertex.index)].color = (*raw_skin[:3], 0.0)
            continue
        distance = min(relevant)
        if distance == 0:
            alpha = 0.98
        else:
            alpha = 0.90 * base.smoothstep((exterior_rings - distance) / exterior_rings)
        world = body.matrix_world @ vertex.co
        u, v, _w = base.local_chart(world)
        tissue = tissue_mix(u, v) * fair.feature_window(u, v)
        # Keep variation bounded and natural: slightly redder/darker internal
        # tissue without painting a cavity or making the whole region one hue.
        color = (
            raw_skin[0] * (1.0 - 0.18 * tissue) + 0.055 * tissue,
            raw_skin[1] * (1.0 - 0.34 * tissue) + 0.012 * tissue,
            raw_skin[2] * (1.0 - 0.30 * tissue) + 0.018 * tissue,
            alpha,
        )
        attribute.data[int(vertex.index)].color = color
        alpha_values.append(alpha)
        tissue_values.append(tissue)

    material = body.material_slots[0].material
    if material is None or material.node_tree is None:
        raise RuntimeError("torso material node tree is absent")
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    image_node = nodes.get("Image Texture")
    warm = nodes.get("R19_Bounded_Warm_Texture_Tint")
    if image_node is None or warm is None:
        raise RuntimeError("exact R19 torso base-color chain drifted")
    existing = next(
        (
            link
            for link in list(links)
            if link.to_node == warm and link.to_socket.name == "Color1"
        ),
        None,
    )
    if existing is None or existing.from_node != image_node:
        raise RuntimeError("exact image-to-warm-tint link drifted")
    links.remove(existing)
    vertex_color = nodes.new("ShaderNodeVertexColor")
    vertex_color.name = "R24_BoundedSurfaceColorAttribute"
    vertex_color.label = "R24 bounded pelvic surface color; feathered to exact torso"
    vertex_color.layer_name = ATTRIBUTE
    blend = nodes.new("ShaderNodeMixRGB")
    blend.name = "R24_BoundedSurfaceColorBlend"
    blend.blend_type = "MIX"
    blend.use_clamp = False
    links.new(image_node.outputs["Color"], blend.inputs["Color1"])
    links.new(vertex_color.outputs["Color"], blend.inputs["Color2"])
    links.new(vertex_color.outputs["Alpha"], blend.inputs[0])
    links.new(blend.outputs["Color"], warm.inputs["Color1"])
    return {
        "attribute": ATTRIBUTE,
        "domain": "POINT",
        "region_faces": len(region_faces),
        "region_vertices": len({v for face in region_faces for v in mesh.polygons[face].vertices}),
        "minimum_nonzero_alpha": min(alpha_values, default=0.0),
        "maximum_alpha": max(alpha_values, default=0.0),
        "maximum_tissue_mix": max(tissue_values, default=0.0),
        "original_torso_texture_retained": True,
        "original_warm_tint_retained": True,
        "outside_bounded_attribute_alpha_zero": True,
        "material_slot_count_changed": False,
    }


def main() -> None:
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if OUTPUT.exists():
        raise RuntimeError("append-only shading repair output already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(base.BODY_NAME)
    rig = bpy.data.objects.get(base.RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or rig is absent")
    base.clear_pose(rig)
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == base.PATCH_MATERIAL_INDEX
    }
    raw_skin, texture_sampling = exact_boundary_texture_mean(body, patch_faces)
    shaping = fair.fair_and_shape(body, VARIANT)
    uv_repair = uvfix.repair_patch_uv(body, patch_faces)
    shading = install_feathered_surface_shading(
        body, patch_faces, raw_skin, int(VARIANT["exterior_face_rings"])
    )
    subdivision = base.apply_simple_subdivision(body)
    body["r24_patch_uses_torso"] = True
    modifier = body.modifiers.new("R24_Attempt02Shading_RenderContinuity", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = int(VARIANT["catmull_render_levels"])
    modifier.render_levels = int(VARIANT["catmull_render_levels"])
    variant_dir = OUTPUT / str(VARIANT["id"])
    variant_dir.mkdir()
    rendered = base.render_variant(body, variant_dir)
    report = {
        "schema": "kira.avatar.r24_attempt02_surface_shading_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SAVE_VISUAL_SIMULATION_REQUIRES_REVIEW_AND_POSE_GATES",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "source_unchanged": sha256(SOURCE) == SOURCE_SHA256,
        "same_geometry_repair_as_attempt_02": True,
        "narrow_additional_defect": "incompatible inherited patch texture island",
        "texture_sampling": texture_sampling,
        "shaping": shaping,
        "uv_repair": uv_repair,
        "shading": shading,
        "subdivision": subdivision,
        "rendered": rendered,
        "operations": {
            "blend_saved": False,
            "runtime_or_person_state_changed": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External visual/deformation simulation only; no internal route, physiology, "
            "elimination, reproduction, pregnancy, sensation, or owner approval is claimed."
        ),
    }
    (OUTPUT / "SIMULATION_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
