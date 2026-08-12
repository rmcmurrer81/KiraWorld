"""Create Avatar Builder reference-pass preview drafts for Marinette and Gwen.

The generated GLBs are review drafts. They are exposed through
builder_preview_model_url and do not replace the active runtime avatar.glb.
"""

from __future__ import annotations

import json
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

MARINETTE_ID = "ladybug_marinette_expanded_smoke"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"

MARINETTE_SOURCE = PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_reference_light.glb"
MARINETTE_SECONDARY_REFS = [
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "marinette_pyjama_casual_reference_light.glb",
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "marinette" / "ladybug_rigged_reference_light.glb",
    PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / MARINETTE_ID / "avatar.glb",
]
GWEN_SOURCE = PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider_gwen_low_poly_unmasked_reference.glb"
GWEN_SECONDARY_REFS = [
    PROJECT_ROOT / "Assets" / "third_party" / "intake" / "3d_models_kira_world" / "characters" / "spider_gwen" / "spider-_gwen.glb",
    PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / GWEN_ID / "avatar.glb",
]
MARINETTE_SOURCE_SHA256 = "a38b85ebe66e5d10dfae81063dee809b6bd6360e97e823178a2eafe591e4bd51"
GWEN_SOURCE_SHA256 = "1c1e3ad16b712ad13ed2b69d2b6f1cb2b30f36e81a22b2f83ca273a18dbe612d"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def preview_url(path: Path) -> str:
    return "/" + rel(path)


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def validate_reference_body_copy(candidate_id: str, source: Path, source_sha256: str, maturity: str) -> dict:
    return enforce_body_policy(
        project_root=PROJECT_ROOT,
        candidate_id=candidate_id,
        body_treatment="non_adult_doll_safe" if maturity == "non_adult_doll_safe" else "neutral_adult_anatomy",
        selected_asset_paths=[source],
        declared_asset_records=[
            {
                "id": f"legacy_character_reference:{source_sha256[:12]}",
                "filename": source.name,
                "sha256": source_sha256,
                "reference_only": True,
                "copy_as_avatar_body_allowed": False,
            }
        ],
        expected_maturity_classes={maturity},
        required_asset_sha256=source_sha256,
        require_asset_evidence=True,
    )


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.55) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def scene_bounds() -> tuple[mathutils.Vector, mathutils.Vector]:
    points: list[mathutils.Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        return mathutils.Vector((0, 0, 0)), mathutils.Vector((0, 0, 0))
    low = mathutils.Vector(min(point[index] for point in points) for index in range(3))
    high = mathutils.Vector(max(point[index] for point in points) for index in range(3))
    return low, high


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


def add_anchor(name: str, location: tuple[float, float, float]) -> None:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = 0.02
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


def add_eye_pair(
    prefix: str,
    left: tuple[float, float, float],
    right: tuple[float, float, float],
    sclera_scale: tuple[float, float, float],
    iris_scale: tuple[float, float, float],
    pupil_scale: tuple[float, float, float],
    iris_color: tuple[float, float, float, float],
    forward_y_delta: float,
) -> list[str]:
    sclera_mat = make_material(f"{prefix}_warm_sclera_material", (0.92, 0.90, 0.84, 1.0), 0.42)
    iris_mat = make_material(f"{prefix}_realistic_blue_iris_material", iris_color, 0.35)
    pupil_mat = make_material(f"{prefix}_black_pupil_material", (0.005, 0.004, 0.004, 1.0), 0.25)
    highlight_mat = make_material(f"{prefix}_eye_highlight_material", (1.0, 1.0, 0.95, 1.0), 0.1)

    created: list[str] = []
    for side, base in (("left", left), ("right", right)):
        add_anchor(f"{prefix}_{side}_eye_socket_anchor", base)
        created.append(f"{prefix}_{side}_eye_socket_anchor")
        add_uv_ellipsoid(f"{prefix}_{side}_eye_sclera", base, sclera_scale, sclera_mat)
        created.append(f"{prefix}_{side}_eye_sclera")
        iris_loc = (base[0], base[1] + forward_y_delta, base[2])
        add_uv_ellipsoid(f"{prefix}_{side}_eye_iris_blue", iris_loc, iris_scale, iris_mat, segments=24)
        created.append(f"{prefix}_{side}_eye_iris_blue")
        pupil_loc = (base[0], base[1] + forward_y_delta * 1.6, base[2])
        add_uv_ellipsoid(f"{prefix}_{side}_eye_pupil_black", pupil_loc, pupil_scale, pupil_mat, segments=16)
        created.append(f"{prefix}_{side}_eye_pupil_black")
        highlight_loc = (base[0] - pupil_scale[0] * 0.45, base[1] + forward_y_delta * 1.9, base[2] + pupil_scale[2] * 0.6)
        add_uv_ellipsoid(f"{prefix}_{side}_eye_catchlight", highlight_loc, (pupil_scale[0] * 0.35, pupil_scale[1], pupil_scale[2] * 0.35), highlight_mat, segments=12)
        created.append(f"{prefix}_{side}_eye_catchlight")
    return created


def rename_marinette_parts() -> list[str]:
    renamed: list[str] = []
    hair_index = 0
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        mats = {mat.name for mat in obj.data.materials if mat}
        low, high = object_bounds(obj)
        if "LB100_c01_eyey__lenz2_SG1" in mats:
            obj.name = "marinette_reference_existing_eye_lens"
            obj.data.name = "marinette_reference_existing_eye_lens_mesh"
            renamed.append(obj.name)
        elif obj.name in {"Object_23", "Object_25", "Object_28"}:
            obj.name = f"marinette_reference_eye_support_{obj.name}"
            obj.data.name = f"{obj.name}_mesh"
            renamed.append(obj.name)
        elif high.z > 95 and (low.x < -30 or "default_64" in mats or "default_5" in mats):
            obj.name = f"marinette_reference_hair_low_pigtail_and_bangs_{hair_index}"
            obj.data.name = f"{obj.name}_mesh"
            hair_index += 1
            renamed.append(obj.name)
        elif high.z > 105 and low.x > -12 and high.x < 12:
            obj.name = f"marinette_reference_head_face_{obj.name}"
            obj.data.name = f"{obj.name}_mesh"
            renamed.append(obj.name)
    return renamed


def rename_gwen_parts() -> list[str]:
    renamed: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        mats = {mat.name for mat in obj.data.materials if mat}
        if "hairs" in mats:
            obj.name = "gwen_unmasked_blonde_asymmetric_side_part_hair"
            obj.data.name = "gwen_unmasked_blonde_asymmetric_side_part_hair_mesh"
            renamed.append(obj.name)
        elif "body" in mats:
            obj.name = "gwen_unmasked_adult_reference_body_head_face"
            obj.data.name = "gwen_unmasked_adult_reference_body_head_face_mesh"
            renamed.append(obj.name)
    return renamed


def object_bounds(obj: bpy.types.Object) -> tuple[mathutils.Vector, mathutils.Vector]:
    points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    low = mathutils.Vector(min(point[index] for point in points) for index in range(3))
    high = mathutils.Vector(max(point[index] for point in points) for index in range(3))
    return low, high


def remove_import_helpers() -> list[str]:
    removed: list[str] = []
    for obj in list(bpy.context.scene.objects):
        lowered = obj.name.lower()
        if lowered.startswith("icosphere") or lowered in {"sphere", "sphere.001", "sphere.002"}:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def export_scene(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_animations=False,
    )


def update_adjustments(candidate_id: str, output: Path, manifest: Path, note: str, extra: dict | None = None) -> None:
    adjustments_path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(adjustments_path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
    data["updated_at"] = now_iso()
    data["builder_preview_model_url"] = preview_url(output)
    data["builder_reference_pass_model"] = rel(output)
    data["latest_builder_reference_pass_manifest"] = rel(manifest)
    data["approval_status"] = "builder_reference_pass_ready_for_robert_review"
    data["active_runtime_model_not_replaced"] = True
    notes = data.setdefault("learning_notes", [])
    notes.append(
        {
            "created_at": now_iso(),
            "tags": ["avatar_builder", "reference_pass", "preview_draft", "robert_requested_rerun"],
            "text": note,
        }
    )
    if extra:
        data.update(extra)
    write_json(adjustments_path, data)


def write_manifest(candidate_id: str, output: Path, source: Path, refs: list[Path], actions: list[str], policy: dict) -> Path:
    manifest = output.with_suffix(".manifest.json")
    low, high = scene_bounds()
    data = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "pass_id": "avatar_builder_reference_pass_20260712",
        "generated_at": now_iso(),
        "output_model": rel(output),
        "source_model": rel(source),
        "reference_models": [rel(path) for path in refs if path.exists()],
        "runtime_model_replaced": False,
        "policy": policy,
        "actions": actions,
        "scene_bounds_after_normalize": {
            "low": list(low),
            "high": list(high),
        },
    }
    write_json(manifest, data)
    return manifest


def build_marinette() -> dict:
    validate_reference_body_copy(
        MARINETTE_ID,
        MARINETTE_SOURCE,
        MARINETTE_SOURCE_SHA256,
        "non_adult_doll_safe",
    )
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(MARINETTE_SOURCE))
    removed = remove_import_helpers()
    renamed = rename_marinette_parts()
    eyes = add_eye_pair(
        "marinette_named",
        left=(-2.9, -9.08, 119.72),
        right=(2.9, -9.08, 119.72),
        sclera_scale=(1.55, 0.16, 0.72),
        iris_scale=(0.52, 0.08, 0.52),
        pupil_scale=(0.18, 0.045, 0.18),
        iris_color=(0.10, 0.24, 0.56, 1.0),
        forward_y_delta=-0.18,
    )
    scale = normalize_scene(target_height=1.36)
    output = AVATAR_MODELS / MARINETTE_ID / "avatar_builder_reference_pass_20260712.glb"
    export_scene(output)
    manifest = write_manifest(
        MARINETTE_ID,
        output,
        MARINETTE_SOURCE,
        MARINETTE_SECONDARY_REFS,
        [
            "Imported the main Marinette 3D reference instead of the rejected primitive redo.",
            "Normalized the model to Avatar Builder preview scale.",
            "Added named socket anchors, sclera, blue iris, pupil, and catchlight meshes over the source eye area.",
            "Renamed likely hair/head/eye source parts so later automatic checks can find them.",
            f"Removed helper primitives: {removed}" if removed else "No helper primitives needed removal.",
            f"Applied normalization scale {scale:.6f}.",
        ],
        {
            "maturity": "non_adult_doll_safe",
            "adult_anatomy_assets_used": False,
            "runtime_avatar_glb_replaced": False,
            "builder_preview_only": True,
        },
    )
    update_adjustments(
        MARINETTE_ID,
        output,
        manifest,
        "Reran Marinette from the real Marinette reference GLB set, kept her non-adult doll-safe, and produced a separate builder preview with named eye/socket parts. The live runtime avatar.glb was not replaced.",
        {
            "maturity_override": "non_adult_doll_safe",
            "maturity_reason": "Normal Marinette/Ladybug remains non-adult; this reference pass uses non-explicit model references and blocks adult anatomy assets.",
            "marinette_reference_pass_sources": {
                "primary": rel(MARINETTE_SOURCE),
                "secondary": [rel(path) for path in MARINETTE_SECONDARY_REFS if path.exists()],
            },
        },
    )
    return {"candidate_id": MARINETTE_ID, "output": rel(output), "manifest": rel(manifest), "renamed": renamed, "eyes": eyes}


def build_gwen() -> dict:
    validate_reference_body_copy(GWEN_ID, GWEN_SOURCE, GWEN_SOURCE_SHA256, "adult")
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(GWEN_SOURCE))
    removed = remove_import_helpers()
    renamed = rename_gwen_parts()
    scale = normalize_scene(target_height=1.68)
    # Gwen's imported model already has a painted/stylized face; these tiny named
    # eye parts give the builder socket/iris targets without replacing the face.
    eyes = add_eye_pair(
        "gwen_named",
        left=(-0.056, 0.004, 1.094),
        right=(0.008, 0.004, 1.094),
        sclera_scale=(0.010, 0.0010, 0.0044),
        iris_scale=(0.0032, 0.0006, 0.0032),
        pupil_scale=(0.0012, 0.00035, 0.0012),
        iris_color=(0.20, 0.42, 0.72, 1.0),
        forward_y_delta=-0.0012,
    )
    output = AVATAR_MODELS / GWEN_ID / "avatar_builder_reference_pass_20260712.glb"
    export_scene(output)
    manifest = write_manifest(
        GWEN_ID,
        output,
        GWEN_SOURCE,
        GWEN_SECONDARY_REFS,
        [
            "Imported Robert's saved unmasked Gwen model as the adult head/hair/body reference pass.",
            "Removed import helper primitives so the preview bounds are driven by the avatar, not a helper sphere.",
            "Added named socket anchors, sclera, blue iris, pupil, and catchlight meshes on the face side.",
            "Kept the spandex suit model as a silhouette and wardrobe reference, not as the base body.",
            f"Renamed source parts: {renamed}",
            f"Applied normalization scale {scale:.6f}.",
        ],
        {
            "maturity": "adult",
            "runtime_avatar_glb_replaced": False,
            "builder_preview_only": True,
            "spandex_suit_policy": "removable_clothing_reference_not_baked_base_body",
        },
    )
    update_adjustments(
        GWEN_ID,
        output,
        manifest,
        "Reran Gwen from the saved unmasked model with the spandex suit kept as wardrobe/silhouette reference. This is a builder preview draft; the live costume runtime avatar.glb was not replaced.",
        {
            "maturity_override": "adult",
            "maturity_reason": "Robert selected Gwen as an adult avatar-builder test pick.",
            "test_role": "adult_reference_test_pick_sources_ready",
            "current_body_rejected_reason": "The active costume runtime model remains rejected as a base body and is only a wardrobe/silhouette reference.",
            "gwen_reference_pass_sources": {
                "primary_unmasked_model": rel(GWEN_SOURCE),
                "secondary": [rel(path) for path in GWEN_SECONDARY_REFS if path.exists()],
            },
        },
    )
    return {"candidate_id": GWEN_ID, "output": rel(output), "manifest": rel(manifest), "renamed": renamed, "eyes": eyes}


def main() -> int:
    # This legacy pass copied complete character-reference meshes into preview
    # bodies. Keep it fail-closed even though its outputs were preview-only.
    validate_reference_body_copy(
        MARINETTE_ID,
        MARINETTE_SOURCE,
        MARINETTE_SOURCE_SHA256,
        "non_adult_doll_safe",
    )
    validate_reference_body_copy(GWEN_ID, GWEN_SOURCE, GWEN_SOURCE_SHA256, "adult")
    results = [build_marinette(), build_gwen()]
    print(json.dumps({"ok": True, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
