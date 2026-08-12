"""Corrected Avatar Builder base-body pass for Marinette and Gwen.

This pass exists because the prior reference pass copied character/reference
models into preview bodies. Robert rejected that as cheating. This script keeps
reference models as evidence only, marks those copied previews unusable, copies
only Marinette's backpack/purse as explicit accessory exceptions, and builds new
preview bodies from base-body sources.

Run with Blender:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background --python tools/run_avatar_builder_base_body_pass_20260712.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
import mathutils


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.avatar_body_policy_gate import enforce_body_policy  # noqa: E402

AVATAR_MODELS = PROJECT_ROOT / "Avatar" / "models" / "temp_ai"
AVATAR_TEMP = PROJECT_ROOT / "Avatar" / "temp_ai"
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"

MARINETTE_ID = "ladybug_marinette_expanded_smoke"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"

MARINETTE_BASE = AVATAR_MODELS / MARINETTE_ID / "avatar.glb"
GWEN_BASE = BUILDER_ROOT / "asset_library" / "base_body_reference" / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
GWEN_BASE_SHA256 = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"
MARINETTE_BODY_LINEAGE = AVATAR_MODELS / MARINETTE_ID / "avatar_body_base_rebuild_v1.json"

MARINETTE_REFERENCE = PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_reference_light.glb"
MARINETTE_REFERENCES = [
    MARINETTE_REFERENCE,
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_pyjama_casual_reference_light.glb",
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "ladybug_rigged_reference_light.glb",
]
GWEN_REFERENCES = [
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider_gwen_low_poly_unmasked_reference.glb",
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider-_gwen.glb",
]

OLD_REFERENCE_PASSES = {
    MARINETTE_ID: AVATAR_MODELS / MARINETTE_ID / "avatar_builder_reference_pass_20260712.glb",
    GWEN_ID: AVATAR_MODELS / GWEN_ID / "avatar_builder_reference_pass_20260712.glb",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def preview_url(path: Path) -> str:
    return "/" + rel(path)


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return dict(default)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def validate_marinette_body_input() -> dict:
    return enforce_body_policy(
        project_root=PROJECT_ROOT,
        candidate_id=MARINETTE_ID,
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[MARINETTE_BASE],
        provenance_manifests=[MARINETTE_BODY_LINEAGE],
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )


def validate_gwen_body_input() -> dict:
    return enforce_body_policy(
        project_root=PROJECT_ROOT,
        candidate_id=GWEN_ID,
        body_treatment="neutral_adult_anatomy",
        selected_asset_paths=[GWEN_BASE],
        expected_maturity_classes={"adult"},
        required_asset_sha256=GWEN_BASE_SHA256,
        require_asset_evidence=True,
    )


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.55) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def object_bounds(obj: bpy.types.Object) -> tuple[mathutils.Vector, mathutils.Vector]:
    points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def scene_bounds() -> tuple[mathutils.Vector, mathutils.Vector]:
    points: list[mathutils.Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for corner in obj.bound_box:
                points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        return mathutils.Vector((0, 0, 0)), mathutils.Vector((0, 0, 0))
    return (
        mathutils.Vector(min(point[index] for point in points) for index in range(3)),
        mathutils.Vector(max(point[index] for point in points) for index in range(3)),
    )


def remove_helper_primitives() -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        lowered = obj.name.lower()
        has_material = obj.type == "MESH" and bool(obj.data.materials)
        if lowered.startswith(("icosphere", "sphere")) and not has_material:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def normalize_scene(target_height: float) -> float:
    low, high = scene_bounds()
    height = max(high.z - low.z, 0.001)
    offset = mathutils.Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z))
    for obj in list(bpy.context.scene.objects):
        if obj.parent is None:
            obj.location -= offset
    bpy.context.view_layer.update()

    scale = target_height / height
    for obj in list(bpy.context.scene.objects):
        if obj.parent is None:
            obj.location *= scale
            obj.scale *= scale
    bpy.context.view_layer.update()
    return scale


def add_anchor(name: str, location: tuple[float, float, float], size: float = 0.025) -> None:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = size
    empty.location = location
    bpy.context.collection.objects.link(empty)


def add_uv_ellipsoid(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    segments: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=max(8, segments // 2),
        radius=1.0,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def add_capsule_proxy(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_mesh"
    obj.scale = scale
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj


def add_eye_system(
    prefix: str,
    left: tuple[float, float, float],
    right: tuple[float, float, float],
    iris_color: tuple[float, float, float, float],
    scale: float,
) -> list[str]:
    sclera_mat = make_material(f"{prefix}_round_eye_sclera_warm_white", (0.93, 0.91, 0.86, 1), 0.38)
    iris_mat = make_material(f"{prefix}_iris_on_round_eye_surface", iris_color, 0.32)
    pupil_mat = make_material(f"{prefix}_pupil_black", (0.004, 0.003, 0.003, 1), 0.22)
    cornea_mat = make_material(f"{prefix}_cornea_catchlight", (1, 1, 0.96, 1), 0.08)

    names: list[str] = []
    for side, loc in (("left", left), ("right", right)):
        add_anchor(f"{prefix}_{side}_eye_socket_anchor", loc, size=0.018 * scale)
        add_anchor(f"{prefix}_{side}_eye_look_target", (loc[0], loc[1] - 0.16 * scale, loc[2]), size=0.016 * scale)
        add_anchor(f"{prefix}_{side}_upper_eyelid_control_anchor", (loc[0], loc[1] - 0.006 * scale, loc[2] + 0.020 * scale), size=0.008 * scale)
        add_anchor(f"{prefix}_{side}_lower_eyelid_control_anchor", (loc[0], loc[1] - 0.006 * scale, loc[2] - 0.020 * scale), size=0.008 * scale)
        names.extend([
            f"{prefix}_{side}_eye_socket_anchor",
            f"{prefix}_{side}_eye_look_target",
            f"{prefix}_{side}_upper_eyelid_control_anchor",
            f"{prefix}_{side}_lower_eyelid_control_anchor",
        ])
        add_uv_ellipsoid(
            f"{prefix}_{side}_round_eye_sclera",
            loc,
            (0.020 * scale, 0.020 * scale, 0.020 * scale),
            sclera_mat,
        )
        add_uv_ellipsoid(
            f"{prefix}_{side}_iris_on_round_eye_surface",
            (loc[0], loc[1] - 0.019 * scale, loc[2]),
            (0.0075 * scale, 0.0025 * scale, 0.0075 * scale),
            iris_mat,
            segments=24,
        )
        add_uv_ellipsoid(
            f"{prefix}_{side}_pupil_on_round_eye_surface",
            (loc[0], loc[1] - 0.022 * scale, loc[2]),
            (0.0030 * scale, 0.0014 * scale, 0.0030 * scale),
            pupil_mat,
            segments=16,
        )
        add_uv_ellipsoid(
            f"{prefix}_{side}_round_eye_catchlight",
            (loc[0] - 0.004 * scale, loc[1] - 0.024 * scale, loc[2] + 0.004 * scale),
            (0.0025 * scale, 0.0009 * scale, 0.0025 * scale),
            cornea_mat,
            segments=12,
        )
        names.extend([
            f"{prefix}_{side}_round_eye_sclera",
            f"{prefix}_{side}_iris_on_round_eye_surface",
            f"{prefix}_{side}_pupil_on_round_eye_surface",
            f"{prefix}_{side}_round_eye_catchlight",
        ])
    return names


def add_mouth_system(prefix: str, location: tuple[float, float, float], scale: float) -> list[str]:
    lip_mat = make_material(f"{prefix}_soft_lip_material", (0.53, 0.29, 0.28, 1), 0.48)
    mouth_mat = make_material(f"{prefix}_mouth_interior_dark", (0.018, 0.008, 0.008, 1), 0.4)
    verts: list[tuple[float, float, float]] = [(0, 0, 0)]
    faces: list[tuple[int, int, int]] = []
    radius_x = 0.022 * scale
    radius_z = 0.008 * scale
    for index in range(24):
        angle = 2 * math.pi * index / 24
        verts.append((math.cos(angle) * radius_x, 0, math.sin(angle) * radius_z))
    for index in range(1, 25):
        faces.append((0, index, 1 if index == 24 else index + 1))
    mesh = bpy.data.meshes.new(f"{prefix}_lip_sync_mouth_control_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mouth = bpy.data.objects.new(f"{prefix}_lip_sync_mouth_control_mesh", mesh)
    mouth.location = location
    bpy.context.collection.objects.link(mouth)
    mouth.data.materials.append(mouth_mat)
    mouth["planned_viseme_shape_keys"] = "viseme_A_jaw_open, viseme_E_wide, viseme_O_round, viseme_M_closed, smile, frown"
    mouth["note"] = "Visible mouth is intentionally small; viseme controls are named anchors until the fitted face mesh supports real blendshapes."
    viseme_offsets = {
        "viseme_A_jaw_open_target": (0, -0.002 * scale, -0.013 * scale),
        "viseme_E_wide_target": (0.016 * scale, -0.002 * scale, 0),
        "viseme_O_round_target": (0, -0.002 * scale, 0.010 * scale),
        "viseme_M_closed_target": (0, -0.002 * scale, 0.003 * scale),
        "smile_target": (0.018 * scale, -0.002 * scale, 0.006 * scale),
        "frown_target": (-0.018 * scale, -0.002 * scale, -0.006 * scale),
    }
    for name, offset in viseme_offsets.items():
        add_anchor(
            f"{prefix}_{name}",
            (location[0] + offset[0], location[1] + offset[1], location[2] + offset[2]),
            size=0.007 * scale,
        )

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.023 * scale,
        minor_radius=0.0025 * scale,
        major_segments=32,
        minor_segments=8,
        location=(location[0], location[1] - 0.001 * scale, location[2]),
    )
    lips = bpy.context.object
    lips.name = f"{prefix}_separate_lips_expression_ring"
    lips.data.name = f"{prefix}_separate_lips_expression_ring_mesh"
    lips.scale.z = 0.30
    lips.rotation_euler[0] = math.radians(90)
    lips.data.materials.append(lip_mat)
    return [mouth.name, lips.name] + [f"{prefix}_{name}" for name in viseme_offsets]


def add_marinette_generated_hair(scale: float = 1.0) -> list[str]:
    hair_mat = make_material("marinette_generated_blue_black_hair", (0.012, 0.020, 0.060, 1), 0.50)
    highlight_mat = make_material("marinette_generated_soft_blue_hair_highlight", (0.055, 0.095, 0.18, 1), 0.48)
    tie_mat = make_material("marinette_generated_red_hair_ties", (0.62, 0.02, 0.04, 1), 0.55)
    parts = [
        add_capsule_proxy("marinette_generated_scalp_cap_reference_only_not_copied", (0, -0.003, 1.268), (0.073, 0.050, 0.040), hair_mat),
        add_capsule_proxy("marinette_generated_side_swept_bangs", (-0.036, -0.058, 1.277), (0.055, 0.010, 0.012), highlight_mat, (0, 0, math.radians(-13))),
        add_capsule_proxy("marinette_generated_back_hair_mass", (0, 0.040, 1.232), (0.065, 0.032, 0.055), hair_mat),
        add_capsule_proxy("marinette_generated_low_pigtail_left", (-0.115, 0.025, 1.205), (0.034, 0.026, 0.060), hair_mat, (0, math.radians(-10), 0)),
        add_capsule_proxy("marinette_generated_low_pigtail_right", (0.115, 0.025, 1.205), (0.034, 0.026, 0.060), hair_mat, (0, math.radians(10), 0)),
        add_capsule_proxy("marinette_generated_pigtail_tie_left", (-0.085, 0.010, 1.225), (0.010, 0.008, 0.010), tie_mat),
        add_capsule_proxy("marinette_generated_pigtail_tie_right", (0.085, 0.010, 1.225), (0.010, 0.008, 0.010), tie_mat),
    ]
    return [obj.name for obj in parts]


def add_gwen_generated_hair(scale: float = 1.0) -> list[str]:
    blonde = make_material("gwen_generated_blonde_hair", (0.88, 0.67, 0.36, 1), 0.46)
    shadow = make_material("gwen_generated_shadow_root_blonde", (0.42, 0.30, 0.18, 1), 0.52)
    pink_tip = make_material("gwen_generated_subtle_pink_hair_tip", (0.88, 0.38, 0.62, 1), 0.48)
    parts = [
        add_capsule_proxy("gwen_generated_asymmetric_side_part_scalp", (0, -0.001, 1.585), (0.070, 0.048, 0.040), blonde),
        add_capsule_proxy("gwen_generated_dark_root_part_line", (-0.020, -0.047, 1.616), (0.045, 0.006, 0.006), shadow, (0, 0, math.radians(-18))),
        add_capsule_proxy("gwen_generated_long_right_swept_front_lock", (0.057, -0.052, 1.500), (0.030, 0.014, 0.105), blonde, (math.radians(7), 0, math.radians(-8))),
        add_capsule_proxy("gwen_generated_left_undercut_short_side", (-0.070, -0.010, 1.535), (0.018, 0.018, 0.060), blonde),
        add_capsule_proxy("gwen_generated_back_layered_hair", (0.030, 0.052, 1.505), (0.070, 0.030, 0.100), blonde),
        add_capsule_proxy("gwen_generated_pink_tip_on_side_lock", (0.067, -0.055, 1.410), (0.020, 0.010, 0.030), pink_tip),
    ]
    return [obj.name for obj in parts]


def assign_or_append_material(obj_name_contains: str, material: bpy.types.Material) -> None:
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj_name_contains.lower() in obj.name.lower():
            obj.data.materials.clear()
            obj.data.materials.append(material)


def rename_base_body_parts(candidate_id: str) -> list[str]:
    renamed: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        original = obj.name
        if candidate_id == MARINETTE_ID:
            obj.name = obj.name.replace("marinette_rebuild_body_base_deforming_mesh", "marinette_base_body_smooth_non_adult_doll_safe")
        elif obj.name.startswith("Object_85"):
            obj.name = "gwen_adult_base_body_from_womenfemale_body_base"
        if obj.name != original:
            obj.data.name = f"{obj.name}_mesh"
            renamed.append(f"{original}->{obj.name}")
    return renamed


def sync_mesh_data_names() -> list[str]:
    renamed: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        wanted = f"{obj.name}_mesh"
        if obj.data.name != wanted:
            renamed.append(f"{obj.data.name}->{wanted}")
            obj.data.name = wanted
    return renamed


def export_scene(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
    )


def write_policy_files() -> dict[str, str]:
    policy_path = BUILDER_ROOT / "policies" / "reference_model_use_policy_20260712.json"
    policy = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active",
        "strict_rule": "Reference character models may be used only as measurement/construction references. They must not be copied into an AI/avatar body.",
        "disqualifying_failure": "If a builder pass imports/copies a reference character model as the preview body, that body is unusable and disqualified.",
        "required_method": [
            "choose the correct approved base body first",
            "derive proportions, eye color, hair silhouette, and clothing notes from references",
            "generate or fit new avatar-specific meshes on the base body",
            "keep adult and non-adult body policies separate",
            "record every exception explicitly",
        ],
        "allowed_exception": {
            "type": "accessory_copy",
            "rule": "Small props/accessories can be copied when Robert explicitly asks for the exact item, but only into an accessory library, not an avatar body.",
            "current_exception": "Marinette backpack and purse copied from the Marinette reference model for her future home/accessory inventory.",
        },
    }
    write_json(policy_path, policy)

    wardrobe_path = BUILDER_ROOT / "wardrobe_training" / "physical_clothing_pipeline_20260712.json"
    wardrobe = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active_training_note",
        "source_note": "C:/Users/robmc/Documents/avatar clothing help.txt and Robert's failed Kira shirt test.",
        "problem_recorded": "A dress shirt hung in Kira's closet stayed in hanging state and floated in front of her body instead of becoming worn.",
        "clothing_rule": "Normal clothing must be separate physical garment geometry with thickness, holes, collision, grab points, and state changes; it must not be a flat skin texture or a floating hanger-state prop.",
        "garment_states": ["stored_or_hanging", "grasped", "dressing_transition", "worn", "unbuttoned_or_open", "removed"],
        "required_features": [
            "solidify/thickness so fabric is not paper-thin",
            "sleeve, neck, waist, and buttonhole openings modeled as openings",
            "cloth or soft-body physics where fabric should move",
            "avatar body collision and garment self-collision",
            "left/right hand grab points and vertex groups",
            "dressing animations that move arms through sleeve holes and then change garment state to worn",
            "button/zip/tie state controls for shirts, jackets, pants, skirts, and dresses",
        ],
        "photo_to_garment_pipeline": [
            "segment garment from image",
            "infer 2D sewing pattern pieces",
            "simulate/sew into 3D garment on avatar mannequin",
            "extract fabric texture/material maps",
            "fit to avatar with physics, collision, and dressing grab points",
        ],
        "magic_or_morph_exceptions": [
            "Ladybug earrings can trigger Spots On and make the costume appear as a magical suit instead of a normal dressed garment.",
            "If Ladybug earrings are given to another AI, that AI can receive its own Ladybug costume version.",
            "Power Ranger-style AIs can morph into suits instead of physically dressing.",
        ],
    }
    write_json(wardrobe_path, wardrobe)

    hair_path = BUILDER_ROOT / "hair_training" / "hair_variant_requirements_20260712.json"
    hair = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active_training_note",
        "rule": "Hair references teach construction and silhouette; they are not copied as final character hair unless Robert explicitly approves a direct accessory copy.",
        "marinette_required_variants": [
            "default low twin pigtails with red ties",
            "hair down without pigtails",
            "hair up without pigtails",
            "Ladybug costume hair variant if needed",
        ],
        "gwen_required_variants": [
            "asymmetric blonde side-part hair",
            "hood-compatible compressed hair",
            "civilian hair-down variant",
        ],
        "required_rigging": [
            "hair is separate from head/body",
            "anchored to scalp/head bones",
            "named sections for scalp cap, bangs, side locks, pigtails/ponytail, ties, and collision bounds",
        ],
    }
    write_json(hair_path, hair)

    overlay_path = BUILDER_ROOT / "body_training" / "silhouette_overlay_reconstruction_pipeline_20260712.json"
    overlay = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active_required_pipeline",
        "source_guides": [
            {
                "title": "How to Sculpt a Stylized Head in Blender",
                "url": "https://www.3dart.it/head-sculpt-in-blender-tutorial/",
                "lesson": "Build the head's large forms first, then sculpt/refine eyes, nose, mouth, jaw, cheeks, and hair planes from references instead of attaching loose face parts.",
            },
            {
                "title": "2D Image to 3D Model in Blender Guide",
                "url": "https://yelzkizi.org/2d-image-to-3d-model-in-blender-guide/",
                "lesson": "Use 2D reference images, silhouettes/SVGs, depth/projection/reference planes, and staged conversion methods to guide 3D reconstruction.",
            },
            {
                "title": "Robert correction with Silhouette Studio examples",
                "url": "conversation_2026-07-12",
                "lesson": "Use clean silhouette tracing and front/side overlays; do not use noisy automatic masks that trace background clutter.",
            },
        ],
        "required_method": [
            "collect all approved images for the candidate",
            "sort images by view: front, side/profile, three-quarter, back, close-up face, hair-specific, body silhouette, wardrobe",
            "make a front silhouette sheet and a side silhouette sheet from the best references",
            "load those sheets as calibrated image planes in Blender behind/in front of the base body",
            "align the base model to the front silhouette first: head width, shoulder width, torso, waist, hips, leg length, arm length, hand/foot placement",
            "align the same model to the side/profile silhouette: skull depth, forehead, nose/mouth/chin projection, chest/back/hip depth, leg stance",
            "reshape the base body and head with lattice/proportional/sculpt controls, not by copying the reference model",
            "use uncertain parts from the approved male/female base libraries; for adults only, use adult anatomy references as neutral construction guides",
            "place real round eyes inside the head volume, then add eyelids and face blendshapes on the fitted head mesh",
            "reject any pass with flat eyes floating in front of the face, face planes pasted on the head, or doll-safe policy applied to an adult candidate",
        ],
        "adult_policy": "Adult candidates such as Gwen may use adult anatomy references in neutral modeling contexts; they must not receive the non-adult Barbie/doll-safe simplification.",
        "non_adult_policy": "Non-adult candidates such as normal Marinette use a smooth doll-safe body and must not use adult anatomy references.",
        "outputs_required_before_next_likeness_claim": [
            "front silhouette overlay PNG/JSON",
            "side silhouette overlay PNG/JSON",
            "Blender calibration scene or manifest naming the source images",
            "front/side/head screenshots with model and overlay visible",
            "measurement deltas showing which body/head parts still fail",
        ],
    }
    write_json(overlay_path, overlay)
    return {
        "reference_policy": rel(policy_path),
        "wardrobe_training": rel(wardrobe_path),
        "hair_variants": rel(hair_path),
        "silhouette_overlay_pipeline": rel(overlay_path),
    }


def mark_old_reference_passes_disqualified(policy_files: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for candidate_id, model_path in OLD_REFERENCE_PASSES.items():
        manifest_path = model_path.with_suffix(".manifest.json")
        if manifest_path.exists():
            manifest = read_json(manifest_path, {})
            manifest["status"] = "disqualified_reference_copy_cheating"
            manifest["disqualified_at"] = now_iso()
            manifest["disqualified_reason"] = (
                "Robert rejected this pass because it copied/imported a reference character model "
                "as the preview body. Reference models may be used only as references."
            )
            manifest["must_not_promote_to_runtime"] = True
            manifest["replacement_policy"] = policy_files["reference_policy"]
            write_json(manifest_path, manifest)
            changed.append(rel(manifest_path))

        adjustments_path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
        data = read_json(adjustments_path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
        disqualified = data.setdefault("disqualified_preview_models", [])
        if not any(item.get("model") == rel(model_path) for item in disqualified if isinstance(item, dict)):
            disqualified.append({
                "created_at": now_iso(),
                "model": rel(model_path),
                "manifest": rel(manifest_path),
                "reason": "Copied/imported reference model body; unusable by Robert's strict no-copy rule.",
                "status": "disqualified_reference_copy_cheating",
            })
        data["reference_model_use_policy"] = policy_files["reference_policy"]
        data["physical_clothing_pipeline_note"] = policy_files["wardrobe_training"]
        data["hair_variant_requirements"] = policy_files["hair_variants"]
        data["silhouette_overlay_pipeline"] = policy_files["silhouette_overlay_pipeline"]
        data["approval_status"] = "failed_disqualified_reference_copy"
        data["updated_at"] = now_iso()
        notes = data.setdefault("learning_notes", [])
        notes.append({
            "created_at": now_iso(),
            "tags": ["avatar_builder", "disqualified", "reference_copy_cheating", "robert_strict_rule"],
            "text": "The prior reference pass is disqualified because it copied a reference model instead of building from a base body.",
        })
        write_json(adjustments_path, data)
        changed.append(rel(adjustments_path))
    return changed


def mark_previous_base_pass_failed(policy_files: dict[str, str]) -> list[str]:
    changed: list[str] = []
    reasons = {
        MARINETTE_ID: (
            "Robert graded the base-body pass F: eyes were flat plates floating in front of the head, "
            "hair/body/face shapes were wrong, and the builder must use front/side silhouette overlay reconstruction."
        ),
        GWEN_ID: (
            "Robert graded the base-body pass F: Gwen incorrectly received a Barbie/doll-safe visual treatment; "
            "Gwen is adult and needs adult base/anatomy-guided reconstruction with front/side overlays."
        ),
    }
    for candidate_id, reason in reasons.items():
        adjustments_path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
        data = read_json(adjustments_path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
        failed = data.setdefault("failed_preview_models", [])
        model = AVATAR_MODELS / candidate_id / "avatar_builder_base_body_pass_20260712.glb"
        failed.append({
            "created_at": now_iso(),
            "model": rel(model),
            "reason": reason,
            "status": "failed_robert_big_f",
        })
        data["last_failed_preview_reason"] = reason
        data["silhouette_overlay_pipeline"] = policy_files["silhouette_overlay_pipeline"]
        data["approval_status"] = "failed_robert_big_f_overlay_required"
        data.setdefault("learning_notes", []).append({
            "created_at": now_iso(),
            "tags": ["avatar_builder", "robert_big_f", "floating_eyes", "silhouette_overlay_required"],
            "text": reason,
        })
        write_json(adjustments_path, data)
        changed.append(rel(adjustments_path))
    return changed


def transform_accessory_scene(scale: float = 0.010037) -> dict:
    low, high = scene_bounds()
    center = mathutils.Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z))
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.location = (obj.location - center) * scale
            obj.scale *= scale
    bpy.context.view_layer.update()
    low2, high2 = scene_bounds()
    return {"low": list(low2), "high": list(high2)}


def extract_accessory(name: str, object_names: list[str], source: Path, output: Path) -> dict:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    kept: list[str] = []
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if obj.name in object_names:
            original = obj.name
            obj.name = f"marinette_{name}_{original}"
            obj.data.name = f"{obj.name}_mesh"
            kept.append(obj.name)
        else:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    bounds = transform_accessory_scene()
    export_scene(output)
    manifest = output.with_suffix(".manifest.json")
    data = {
        "schema_version": 1,
        "created_at": now_iso(),
        "asset_id": f"marinette_{name}_accessory_20260712",
        "status": "accessory_copy_exception_ready",
        "source_model": rel(source),
        "output_model": rel(output),
        "copied_by_explicit_robert_exception": True,
        "body_policy": "This is an accessory only. It must never be used as a body, head, hair, or clothing-source cheat.",
        "kept_source_objects": object_names,
        "renamed_objects": kept,
        "removed_source_object_count": len(removed),
        "bounds": bounds,
    }
    write_json(manifest, data)
    return {"output": rel(output), "manifest": rel(manifest), "kept": kept}


def extract_marinette_accessories() -> dict:
    root = BUILDER_ROOT / "accessory_library" / "marinette"
    backpack = extract_accessory(
        "backpack",
        ["Object_2", "Object_11", "Object_14", "Object_16", "Object_17", "Object_21", "Object_30"],
        MARINETTE_REFERENCE,
        root / "marinette_backpack_reference_accessory_20260712.glb",
    )
    purse = extract_accessory(
        "purse",
        ["Object_5", "Object_12", "Object_19", "Object_22", "Object_27"],
        MARINETTE_REFERENCE,
        root / "marinette_purse_reference_accessory_20260712.glb",
    )
    index_path = root / "marinette_accessory_manifest_20260712.json"
    data = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "ready_for_future_home_or_accessory_use",
        "source_model": rel(MARINETTE_REFERENCE),
        "strict_note": "Backpack and purse are explicit accessory copies only. The Avatar Builder body still must be built from a base body.",
        "assets": {
            "backpack": backpack,
            "purse": purse,
        },
    }
    write_json(index_path, data)
    return {"manifest": rel(index_path), "backpack": backpack, "purse": purse}


def write_base_body_manifest(
    candidate_id: str,
    output: Path,
    base_source: Path,
    references: list[Path],
    maturity_policy: str,
    actions: list[str],
    extra: dict | None = None,
) -> Path:
    manifest_path = output.with_suffix(".manifest.json")
    low, high = scene_bounds()
    data = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "pass_id": "avatar_builder_base_body_pass_20260712",
        "created_at": now_iso(),
        "status": "round_eye_mechanics_preview_ready_overlay_required",
        "output_model": rel(output),
        "base_body_source": rel(base_source),
        "reference_models_used_as_references_only": [rel(path) for path in references if path.exists()],
        "copied_reference_model_meshes_into_body": False,
        "runtime_model_replaced": False,
        "maturity_policy": maturity_policy,
        "actions": actions,
        "scene_bounds": {"low": list(low), "high": list(high)},
    }
    if extra:
        data.update(extra)
    write_json(manifest_path, data)
    return manifest_path


def update_adjustments_for_base_pass(candidate_id: str, output: Path, manifest: Path, note: str, extra: dict) -> None:
    path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
    data["updated_at"] = now_iso()
    data["approval_status"] = "round_eye_mechanics_preview_ready_overlay_required"
    data["builder_preview_model_url"] = preview_url(output)
    data["builder_base_body_pass_model"] = rel(output)
    data["latest_builder_base_body_pass_manifest"] = rel(manifest)
    data["active_runtime_model_not_replaced"] = True
    data["reference_copy_disqualified_not_replaced_by_reference_copy"] = True
    data["silhouette_overlay_required_before_likeness_claim"] = True
    notes = data.setdefault("learning_notes", [])
    notes.append({
        "created_at": now_iso(),
        "tags": ["avatar_builder", "base_body_pass", "no_reference_copy", "robert_requested_rerun"],
        "text": note,
    })
    data.update(extra)
    write_json(path, data)


def build_marinette() -> dict:
    body_policy_gate = validate_marinette_body_input()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(MARINETTE_BASE))
    removed = remove_helper_primitives()
    renamed = rename_base_body_parts(MARINETTE_ID)
    skin = make_material("marinette_base_non_adult_smooth_skin", (0.72, 0.58, 0.50, 1), 0.58)
    assign_or_append_material("marinette_base_body_smooth_non_adult_doll_safe", skin)
    scale = normalize_scene(1.36)
    eyes = add_eye_system(
        "marinette_base_pass",
        left=(-0.036, -0.073, 1.247),
        right=(0.036, -0.073, 1.247),
        iris_color=(0.08, 0.22, 0.55, 1),
        scale=1.0,
    )
    mouth = add_mouth_system("marinette_base_pass", (0.0, -0.101, 1.205), 1.0)
    hair = add_marinette_generated_hair()
    add_anchor("marinette_hair_variant_slot_hair_down_not_yet_built", (0.0, 0.050, 1.215))
    add_anchor("marinette_hair_variant_slot_hair_up_no_pigtails_not_yet_built", (0.0, 0.035, 1.300))
    mesh_data_renamed = sync_mesh_data_names()
    output = AVATAR_MODELS / MARINETTE_ID / "avatar_builder_base_body_pass_20260712.glb"
    export_scene(output)
    manifest = write_base_body_manifest(
        MARINETTE_ID,
        output,
        MARINETTE_BASE,
        MARINETTE_REFERENCES,
        "non_adult_doll_safe",
        [
            "Started from the restored Marinette female/base body branch, not a character reference model.",
            "Removed empty helper primitives from the source scene.",
            "Rebuilt named eye socket, sclera, iris, pupil, cornea, eyelid, and look-target parts.",
            "Rebuilt eyes as round eyeballs seated inside head volume; no flat floating eye plates.",
            "Added a small named mouth-control mesh and viseme anchors; real fitted blendshapes require the next face-mesh pass.",
            "Added generated low-pigtail hair proxies and recorded hair-down/up variant slots.",
            f"Applied base normalization scale {scale:.6f}.",
        ],
        {
            "adult_anatomy_assets_used": False,
            "body_policy_validation": body_policy_gate,
            "removed_helper_primitives": removed,
            "renamed_base_parts": renamed,
            "renamed_mesh_data": mesh_data_renamed,
            "generated_eye_parts": eyes,
            "generated_mouth_parts": mouth,
            "generated_hair_parts": hair,
        },
    )
    update_adjustments_for_base_pass(
        MARINETTE_ID,
        output,
        manifest,
        "Reran Marinette using the restored non-adult base body instead of a copied reference model; added named eyes, eyelids, look targets, mouth visemes, and generated hair placeholders.",
        {
            "maturity_override": "non_adult_doll_safe",
            "maturity_reason": "Normal Marinette/Ladybug remains non-adult and uses a smooth doll-safe base body. Reference models are references only.",
            "base_body_source": rel(MARINETTE_BASE),
            "reference_models_used_as_references_only": [rel(path) for path in MARINETTE_REFERENCES if path.exists()],
            "marinette_accessory_manifest": rel(BUILDER_ROOT / "accessory_library" / "marinette" / "marinette_accessory_manifest_20260712.json"),
            "non_adult_barbie_treatment_allowed": True,
            "adult_anatomy_references_allowed": False,
        },
    )
    return {"candidate_id": MARINETTE_ID, "output": rel(output), "manifest": rel(manifest)}


def build_gwen() -> dict:
    body_policy_gate = validate_gwen_body_input()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(GWEN_BASE))
    removed = remove_helper_primitives()
    renamed = rename_base_body_parts(GWEN_ID)
    skin = make_material("gwen_adult_base_skin_neutral", (0.72, 0.56, 0.48, 1), 0.58)
    assign_or_append_material("gwen_adult_base_body", skin)
    scale = normalize_scene(1.68)
    eyes = add_eye_system(
        "gwen_base_pass",
        left=(-0.038, -0.073, 1.548),
        right=(0.038, -0.073, 1.548),
        iris_color=(0.17, 0.38, 0.70, 1),
        scale=1.05,
    )
    mouth = add_mouth_system("gwen_base_pass", (0.0, -0.101, 1.492), 1.04)
    hair = add_gwen_generated_hair()
    add_anchor("gwen_ghost_spider_suit_future_removable_clothing_slot", (0.0, -0.120, 0.980))
    mesh_data_renamed = sync_mesh_data_names()
    output = AVATAR_MODELS / GWEN_ID / "avatar_builder_base_body_pass_20260712.glb"
    export_scene(output)
    manifest = write_base_body_manifest(
        GWEN_ID,
        output,
        GWEN_BASE,
        GWEN_REFERENCES,
        "adult",
        [
            "Started from the shared adult female base body reference, not Gwen's unmasked model or spandex suit.",
            "Removed empty helper primitives from the source scene.",
            "Used Gwen unmasked model and spandex suit only as references for later likeness, hair, and wardrobe work.",
            "Added round eyes seated inside head volume; no flat floating eye plates.",
            "Added a small named mouth-control mesh and viseme anchors; real fitted blendshapes require the next face-mesh pass.",
            "Added generated asymmetric blonde hair proxies and a removable Ghost-Spider suit slot.",
            f"Applied base normalization scale {scale:.6f}.",
        ],
        {
            "adult_anatomy_references_allowed": True,
            "body_policy_validation": body_policy_gate,
            "adult_anatomy_reference_library": "Avatar/avatar_builder/asset_library/adult_anatomy_reference",
            "removed_helper_primitives": removed,
            "renamed_base_parts": renamed,
            "renamed_mesh_data": mesh_data_renamed,
            "generated_eye_parts": eyes,
            "generated_mouth_parts": mouth,
            "generated_hair_parts": hair,
            "spandex_suit_policy": "future removable clothing, not baked into the base body",
        },
    )
    update_adjustments_for_base_pass(
        GWEN_ID,
        output,
        manifest,
        "Reran Gwen from the adult female base body; the unmasked Gwen model and spandex suit are references only, and the suit is recorded as future removable clothing.",
        {
            "maturity_override": "adult",
            "maturity_reason": "Robert selected Gwen as an adult avatar-builder test pick.",
            "test_role": "adult_reference_test_pick_base_body_pass_ready",
            "base_body_source": rel(GWEN_BASE),
            "reference_models_used_as_references_only": [rel(path) for path in GWEN_REFERENCES if path.exists()],
            "current_body_rejected_reason": "The active full-costume runtime body and copied reference pass are rejected as base bodies. This pass uses the adult female base body.",
            "spandex_wardrobe_policy": "Ghost-Spider suit must be removable clothing or morph layer, not the base body.",
            "non_adult_barbie_treatment_allowed": False,
            "adult_anatomy_references_allowed": True,
        },
    )
    return {"candidate_id": GWEN_ID, "output": rel(output), "manifest": rel(manifest)}


def main() -> int:
    # Preflight both body sources before this legacy all-candidates script
    # writes policy files, extracts accessories, or opens a Blender scene.
    validate_marinette_body_input()
    validate_gwen_body_input()
    policy_files = write_policy_files()
    disqualified = mark_old_reference_passes_disqualified(policy_files)
    failed_base = mark_previous_base_pass_failed(policy_files)
    accessories = extract_marinette_accessories()
    results = [build_marinette(), build_gwen()]
    print(json.dumps({
        "ok": True,
        "policy_files": policy_files,
        "disqualified_updates": disqualified,
        "failed_base_updates": failed_base,
        "accessories": accessories,
        "results": results,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
