from __future__ import annotations

import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.avatar_body_policy_gate import enforce_body_policy  # noqa: E402

SOURCE_BODY = ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "avatar_builder_references" / "womenfemale_body_base_rigged.glb"
REFERENCE_MODELS = [
    ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_reference_light.glb",
    ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_pyjama_casual_reference_light.glb",
    ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "ladybug_rigged_reference_light.glb",
]
MODEL_DIR = ROOT / "Avatar" / "models" / "temp_ai" / "ladybug_marinette_expanded_smoke"
AVATAR = MODEL_DIR / "avatar.glb"
STAGED = MODEL_DIR / "avatar_rebuild_single_body_no_head_graft_v3_20260706.glb"
MANIFEST = MODEL_DIR / "avatar_body_base_rebuild_v1.json"
REFERENCE_HEAD_MODEL = ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_pyjama_casual_reference_light.glb"
CANDIDATE_ID = "ladybug_marinette_expanded_smoke"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name: str, color: tuple[float, float, float, float], roughness: float = 0.55, metallic: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
    return mat


def scene_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector, Vector]:
    lows: list[Vector] = []
    highs: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        lows.append(Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners))))
        highs.append(Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners))))
    low = Vector((min(v.x for v in lows), min(v.y for v in lows), min(v.z for v in lows)))
    high = Vector((max(v.x for v in highs), max(v.y for v in highs), max(v.z for v in highs)))
    return low, high, high - low


def add_uv_sphere(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float], mat: bpy.types.Material, segments: int = 32, rings: int = 12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def add_cube(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float], mat: bpy.types.Material, rot: tuple[float, float, float] = (0, 0, 0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def add_cone(name: str, loc: tuple[float, float, float], radius1: float, radius2: float, depth: float, mat: bpy.types.Material, vertices: int = 32) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_cylinder_between(name: str, start: tuple[float, float, float], end: tuple[float, float, float], radius: float, mat: bpy.types.Material, vertices: int = 16) -> bpy.types.Object:
    a = Vector(start)
    b = Vector(end)
    mid = (a + b) * 0.5
    length = max(0.001, (b - a).length)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def find_bone_name(armature: bpy.types.Object, *needles: str) -> str:
    lowered = [needle.lower() for needle in needles]
    for bone in armature.data.bones:
        name = bone.name.lower()
        if all(needle in name for needle in lowered):
            return bone.name
    return ""


def bind_mesh_to_bone(obj: bpy.types.Object, armature: bpy.types.Object, bone_name: str) -> None:
    if not bone_name or obj.type != "MESH":
        return
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def remove_helper_meshes(imported: list[bpy.types.Object]) -> list[bpy.types.Object]:
    kept: list[bpy.types.Object] = []
    for obj in imported:
        if obj.type == "MESH" and (obj.name.lower().startswith("icosphere") or len(obj.data.vertices) <= 64):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        kept.append(obj)
    return kept


def remove_named_export_helpers() -> int:
    removed = 0
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH" and obj.name.lower().startswith("icosphere"):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def materialize_body_zones(body: bpy.types.Object, mats: dict[str, bpy.types.Material]) -> None:
    body.name = "marinette_rebuild_body_base_deforming_mesh"
    body.data.name = "marinette_rebuild_body_base_deforming_mesh_data"
    body.data.materials.clear()
    ordered = ["skin", "fitting_layer", "shoe", "hair"]
    for key in ordered:
        body.data.materials.append(mats[key])
    index = {key: i for i, key in enumerate(ordered)}

    vertices = body.data.vertices
    xs = [vertex.co.x for vertex in vertices]
    zs = [vertex.co.z for vertex in vertices]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    half_width = max(0.001, (max_x - min_x) * 0.5)
    center_x = (min_x + max_x) * 0.5
    height = max(0.001, max_z - min_z)
    paint_fitting_layer = False
    for poly in body.data.polygons:
        avg = Vector((0, 0, 0))
        for vertex_index in poly.vertices:
            avg += vertices[vertex_index].co
        avg /= max(1, len(poly.vertices))
        ax = abs(avg.x - center_x) / half_width
        h = (avg.z - min_z) / height
        if h < 0.07:
            mat_key = "shoe"
        elif h > 0.895 and (avg.y > -0.025 or h > 0.952):
            mat_key = "hair"
        elif paint_fitting_layer and 0.1 < h < 0.86 and ax < 0.72:
            mat_key = "fitting_layer"
        else:
            mat_key = "skin"
        poly.material_index = index[mat_key]
    body.data.update()


def remove_base_head_and_double_neck_faces(body: bpy.types.Object) -> int:
    mesh = body.data
    xs = [vertex.co.x for vertex in mesh.vertices]
    zs = [vertex.co.z for vertex in mesh.vertices]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    center_x = (min_x + max_x) * 0.5
    half_width = max(0.001, (max_x - min_x) * 0.5)
    height = max(0.001, max_z - min_z)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    doomed = []
    for face in bm.faces:
        avg = sum((vertex.co for vertex in face.verts), Vector((0, 0, 0))) / max(1, len(face.verts))
        h = (avg.z - min_z) / height
        ax = abs(avg.x - center_x) / half_width
        if h > 0.855 and ax < 0.5:
            doomed.append(face)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(doomed)


def object_world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return low, high, high - low


def selected_reference_head_mesh(obj: bpy.types.Object) -> bool:
    if obj.type != "MESH" or obj.name.lower().startswith("icosphere"):
        return False
    low, high, size = object_world_bounds(obj)
    center_x = (low.x + high.x) * 0.5
    center_y = (low.y + high.y) * 0.5
    if abs(center_x) > 20 or abs(center_y) > 14:
        return False
    if high.z < 112 or low.z < 101:
        return False
    if size.z < 0.2 or size.x > 38:
        return False
    return True


def fit_reference_objects_to_head(objects: list[bpy.types.Object]) -> None:
    low, high, size = scene_bounds(objects)
    center = (low + high) * 0.5
    target_center = Vector((0.0, -0.035, 1.122))
    scale = min(0.255 / max(size.x, 0.001), 0.205 / max(size.y, 0.001), 0.245 / max(size.z, 0.001))
    transform = Matrix.Translation(target_center) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
    for index, obj in enumerate(objects):
        obj.matrix_world = transform @ obj.matrix_world
        obj.name = f"marinette_reference_head_face_hair_{index:02d}_{obj.name}"
        for mat in obj.data.materials:
            if mat:
                mat.name = f"marinette_reference_{mat.name}"
        obj["kira_reference_import"] = "marinette_pyjama_head_face_hair"


def import_reference_head_face_hair() -> list[bpy.types.Object]:
    if not REFERENCE_HEAD_MODEL.exists():
        return []
    enforce_body_policy(
        project_root=ROOT,
        candidate_id=CANDIDATE_ID,
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[REFERENCE_HEAD_MODEL],
        declared_asset_records=[{
            "id": f"legacy_character_reference_head:{REFERENCE_HEAD_MODEL.name}",
            "filename": REFERENCE_HEAD_MODEL.name,
            "reference_only": True,
            "copy_as_avatar_body_allowed": False,
        }],
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(REFERENCE_HEAD_MODEL))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    selected = [obj for obj in imported if selected_reference_head_mesh(obj)]
    for obj in imported:
        if obj not in selected:
            bpy.data.objects.remove(obj, do_unlink=True)
    if not selected:
        return []
    for obj in selected:
        for modifier in list(obj.modifiers):
            if modifier.type == "ARMATURE":
                obj.modifiers.remove(modifier)
    fit_reference_objects_to_head(selected)
    return selected


def add_single_neck_bridge(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    bridge = add_cone(
        "marinette_single_reference_head_neck_bridge",
        (0.0, -0.012, 0.978),
        0.048,
        0.041,
        0.096,
        mats["skin"],
        36,
    )
    bridge["kira_avatar_rebuild"] = "single_neck_bridge_for_reference_head"
    return bridge


def add_marinette_single_body_face_hair(mats: dict[str, bpy.types.Material], armature: bpy.types.Object) -> list[bpy.types.Object]:
    added: list[bpy.types.Object] = []
    head_bone = find_bone_name(armature, "head")

    added.append(add_uv_sphere("marinette_single_body_side_swept_bangs", (-0.033, -0.091, 1.122), (0.038, 0.006, 0.009), mats["hair_hi"], 32, 8))
    added.append(add_uv_sphere("marinette_single_body_back_hair_mass", (0.0, 0.066, 1.082), (0.06, 0.017, 0.025), mats["hair"], 32, 10))
    for side, sx in [("L", -1), ("R", 1)]:
        added.append(add_uv_sphere(f"marinette_single_body_low_pigtail_volume.{side}", (0.116 * sx, 0.042, 1.045), (0.033, 0.023, 0.03), mats["hair"], 32, 10))
        added.append(add_uv_sphere(f"marinette_single_body_pigtail_tie_red.{side}", (0.096 * sx, 0.03, 1.055), (0.01, 0.008, 0.008), mats["accent_red"], 16, 8))
        added.append(add_cylinder_between(f"marinette_single_body_soft_side_lock.{side}", (0.058 * sx, -0.074, 1.106), (0.077 * sx, -0.058, 1.025), 0.0045, mats["hair_hi"], 10))

    # Face pieces are deliberately disabled on this pass. The last accessory eyes
    # and mouth floated in front of the face, so the rebuild must first keep a
    # clean single-body base before adding morph-capable blink/lip-sync parts.

    for obj in added:
        bind_mesh_to_bone(obj, armature, head_bone)
        obj["kira_avatar_rebuild"] = "single_body_head_bone_hair_accessory"

    return added


def lock_transforms_for_export(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        if obj.type != "MESH" or obj.parent_type == "BONE":
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)


def main() -> int:
    body_policy_gate = enforce_body_policy(
        project_root=ROOT,
        candidate_id=CANDIDATE_ID,
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[SOURCE_BODY],
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )
    if not SOURCE_BODY.exists():
        raise SystemExit(f"missing source body: {SOURCE_BODY}")

    clear_scene()
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_BODY))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    imported = remove_helper_meshes(imported)

    meshes = [obj for obj in imported if obj.type == "MESH"]
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if not meshes or not armatures:
        raise SystemExit("source body did not import with a mesh and armature")

    armature = armatures[0]
    armature.name = "Marinette_Rebuild_BaseBody_Mixamo_Rig_v1"
    body = max(meshes, key=lambda obj: len(obj.data.vertices))

    mats = {
        "skin": make_mat("marinette_rebuild_skin_even_tone", (0.83, 0.64, 0.56, 1), 0.58),
        "fitting_layer": make_mat("marinette_rebuild_neutral_fitting_layer", (0.28, 0.32, 0.38, 1), 0.66),
        "shoe": make_mat("marinette_rebuild_black_flats", (0.025, 0.024, 0.027, 1), 0.48),
        "hair": make_mat("marinette_rebuild_blue_black_hair", (0.004, 0.012, 0.055, 1), 0.42),
        "hair_hi": make_mat("marinette_rebuild_blue_hair_highlight", (0.028, 0.05, 0.16, 1), 0.36),
        "eye_white": make_mat("marinette_rebuild_eye_white", (0.92, 0.96, 1.0, 1), 0.32),
        "eye_blue": make_mat("marinette_rebuild_blue_iris", (0.12, 0.42, 0.68, 1), 0.28),
        "lip": make_mat("marinette_rebuild_soft_lip", (0.66, 0.27, 0.34, 1), 0.48),
        "accent_red": make_mat("marinette_rebuild_tie_accent_red", (0.72, 0.04, 0.08, 1), 0.5),
        "purse": make_mat("marinette_rebuild_purse_strap_dark", (0.025, 0.018, 0.016, 1), 0.56),
    }
    materialize_body_zones(body, mats)
    removed_base_head_faces = 0
    reference_head_meshes = 0
    added = add_marinette_single_body_face_hair(mats, armature)
    lock_transforms_for_export(added)
    removed_helpers = remove_named_export_helpers()

    for obj in bpy.context.scene.objects:
        obj["kira_avatar_rebuild"] = "marinette_body_base_v1"

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if AVATAR.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(AVATAR, MODEL_DIR / f"avatar_before_body_base_rebuild_v1_{stamp}.glb")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(STAGED),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_animations=True,
    )
    shutil.copy2(STAGED, AVATAR)

    low, high, size = scene_bounds([obj for obj in bpy.context.scene.objects if obj.type == "MESH"])
    MANIFEST.write_text(
        json.dumps(
            {
                "version": "marinette_single_body_no_head_graft_v4",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "active_model": str(AVATAR.relative_to(ROOT)).replace("\\", "/"),
                "staged_model": str(STAGED.relative_to(ROOT)).replace("\\", "/"),
                "source_body": str(SOURCE_BODY.relative_to(ROOT)).replace("\\", "/"),
                "body_policy_validation": body_policy_gate,
                "reference_models": [str(path.relative_to(ROOT)).replace("\\", "/") for path in REFERENCE_MODELS],
                "reference_head_model": str(REFERENCE_HEAD_MODEL.relative_to(ROOT)).replace("\\", "/"),
                "strategy": [
                    "Use the rigged womenfemale base body as the deforming body instead of a stitched proxy body.",
                    "Material-zone the one body mesh into one even skin tone plus temporary shoes/hair markers so knees and shoulders remain on one skeleton.",
                    "Keep the base body's own head attached to the same rig. Do not graft a head from another downloaded model.",
                    "Use the downloaded Marinette/Ladybug models as visual references only; keep hair markers but disable the floating accessory eyes/mouth until proper morph-capable face parts are authored.",
                    "Opt the active runtime into the generic Mixamo procedural gait driver through runtime bone detection.",
                ],
                "bounds": {
                    "min": [round(low.x, 5), round(low.y, 5), round(low.z, 5)],
                    "max": [round(high.x, 5), round(high.y, 5), round(high.z, 5)],
                    "size": [round(size.x, 5), round(size.y, 5), round(size.z, 5)],
                },
                "reference_head_meshes": reference_head_meshes,
                "removed_base_head_faces": removed_base_head_faces,
                "removed_export_helpers": removed_helpers,
                "notes_for_next_pass": [
                    "Build proper blink and mouth morph targets on the single body/head path instead of copying another model's head.",
                    "Add selectable hair variants as head-bone-bound wearable hair meshes: pigtails, hair down, and hair up.",
                    "Build separate wearable civilian/Ladybug clothing layers after the base gait is stable.",
                    "Do not re-enable the simple eye/mouth accessory spheres; they floated in front of the face and must be replaced by fitted morph targets.",
                    "Do not reintroduce a separate neck splice, imported reference-head graft, or runtime torso overlay on this rebuilt base.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
