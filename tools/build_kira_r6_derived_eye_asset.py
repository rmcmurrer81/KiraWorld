"""Build an inactive R6-specific derivative of Kira's staged brown-eye asset.

This script is intentionally an authoring-only Blender entry point.  It reads
the exact staged v3.2 eye GLB, changes only a copied scene, and exports a new
GLB to a separate review directory.  It never overwrites the source eye GLB,
the exact R6 body, a Home World public asset, or a runtime binding.

The R6 head aperture audit proved that the authored socket centres are already
correct.  The remaining failure is volumetric: moving the full 17.2 mm globes
far enough forward for both three-quarter views makes them protrude through the
temples.  The derived candidate therefore keeps the socket hierarchy and gaze/
blink controls, advances only each existing eye pivot, and reduces the copied
sclera globe's transverse/depth envelope.  Iris, limbus, pupil, and cornea stay
on the same existing pivot and remain independently controllable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_EYE = (
    ROOT
    / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
R6_BODY = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r6_derived_eye_rig"
    / "review_20260721"
)
EXPECTED_SOURCE_EYE_SHA256 = (
    "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413"
)
EXPECTED_R6_BODY_SHA256 = (
    "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--candidate-id", default="r6_eye_sclera075_depth070_forward080")
    parser.add_argument("--pivot-forward-mm", type=float, default=8.0)
    parser.add_argument("--sclera-xz-scale", type=float, default=0.75)
    parser.add_argument("--sclera-depth-scale", type=float, default=0.70)
    parser.add_argument("--iris-scale", type=float, default=1.0)
    parser.add_argument("--cornea-xz-scale", type=float, default=1.0)
    parser.add_argument("--cornea-depth-scale", type=float, default=0.70)
    return parser.parse_args(values)


def object_record(obj: bpy.types.Object) -> dict[str, object]:
    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "location": [float(value) for value in obj.location],
        "rotation_euler": [float(value) for value in obj.rotation_euler],
        "scale": [float(value) for value in obj.scale],
        "vertices": len(obj.data.vertices) if obj.type == "MESH" else None,
        "shape_keys": (
            list(obj.data.shape_keys.key_blocks.keys())
            if obj.type == "MESH" and obj.data.shape_keys
            else []
        ),
    }


def require_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Required staged-eye node is missing: {name}")
    return obj


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_glb = output_dir / f"{args.candidate_id}.glb"
    manifest_path = output_dir / f"{args.candidate_id}.manifest.json"

    source_hash_before = sha256(SOURCE_EYE)
    r6_hash_before = sha256(R6_BODY)
    if source_hash_before != EXPECTED_SOURCE_EYE_SHA256:
        raise RuntimeError("Exact staged brown-eye source hash changed; refusing derivation.")
    if r6_hash_before != EXPECTED_R6_BODY_SHA256:
        raise RuntimeError("Exact R6 body hash changed; refusing derivation.")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_EYE))
    bpy.context.view_layer.update()

    before = {
        obj.name: object_record(obj)
        for obj in bpy.context.scene.objects
        if obj.name.startswith("Kira")
    }

    # Blender native face-forward is -Y.  glTF conversion maps this to the
    # runtime pivot's +Z, which the prior fixed-camera probe proved is outward.
    pivot_forward_metres = args.pivot_forward_mm / 1000.0
    for side in ("Left", "Right"):
        pivot = require_object(f"Kira{side}EyePivot")
        pivot.location.y -= pivot_forward_metres

        sclera = require_object(f"Kira{side}Sclera")
        sclera.scale.x *= args.sclera_xz_scale
        sclera.scale.z *= args.sclera_xz_scale
        sclera.scale.y *= args.sclera_depth_scale

        for suffix in ("Iris", "LimbalRing", "Pupil"):
            component = require_object(f"Kira{side}{suffix}")
            component.scale.x *= args.iris_scale
            component.scale.z *= args.iris_scale

        cornea = require_object(f"Kira{side}Cornea")
        cornea.scale.x *= args.cornea_xz_scale
        cornea.scale.z *= args.cornea_xz_scale
        cornea.scale.y *= args.cornea_depth_scale

    # Preserve the exact node name because the existing runtime structural
    # contract finds this copied component by name.  Inactive/derived status
    # is carried in extras and the separate output path, never by renaming a
    # contract node.
    root = require_object("KiraBrownEyeRig_v3_2")
    root["source_asset_sha256"] = source_hash_before
    root["target_body_sha256"] = r6_hash_before
    root["candidate_id"] = args.candidate_id
    root["inactive_review_only"] = True
    root["not_live_bound"] = True
    root["r6_pivot_forward_mm"] = args.pivot_forward_mm
    root["r6_sclera_xz_scale"] = args.sclera_xz_scale
    root["r6_sclera_depth_scale"] = args.sclera_depth_scale
    root["r6_iris_scale"] = args.iris_scale
    root["r6_cornea_xz_scale"] = args.cornea_xz_scale
    root["r6_cornea_depth_scale"] = args.cornea_depth_scale

    after = {
        obj.name: object_record(obj)
        for obj in bpy.context.scene.objects
        if obj.name.startswith("Kira")
    }

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(output_glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
        export_apply=False,
        export_extras=True,
    )

    source_hash_after = sha256(SOURCE_EYE)
    r6_hash_after = sha256(R6_BODY)
    manifest = {
        "schema_version": 1,
        "kind": "inactive_r6_specific_derived_eye_asset_no_binding_no_activation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": args.candidate_id,
        "status": "inactive_fixed_camera_review_required",
        "source_eye": {
            "path": str(SOURCE_EYE.relative_to(ROOT)).replace("\\", "/"),
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "unchanged": source_hash_before == source_hash_after == EXPECTED_SOURCE_EYE_SHA256,
        },
        "target_r6_body": {
            "path": str(R6_BODY.relative_to(ROOT)).replace("\\", "/"),
            "sha256_before": r6_hash_before,
            "sha256_after": r6_hash_after,
            "unchanged": r6_hash_before == r6_hash_after == EXPECTED_R6_BODY_SHA256,
        },
        "derived_glb": {
            "path": str(output_glb.relative_to(ROOT)).replace("\\", "/"),
            "bytes": output_glb.stat().st_size,
            "sha256": sha256(output_glb),
        },
        "parameters": {
            "pivot_forward_mm": args.pivot_forward_mm,
            "sclera_xz_scale": args.sclera_xz_scale,
            "sclera_depth_scale": args.sclera_depth_scale,
            "iris_scale": args.iris_scale,
            "cornea_xz_scale": args.cornea_xz_scale,
            "cornea_depth_scale": args.cornea_depth_scale,
        },
        "preserved_contract": {
            "socket_node_names": ["KiraLeftEyeSocket", "KiraRightEyeSocket"],
            "pivot_node_names": ["KiraLeftEyePivot", "KiraRightEyePivot"],
            "existing_blink_nodes": [
                "KiraLeftUpperLid",
                "KiraLeftLowerLid",
                "KiraRightUpperLid",
                "KiraRightLowerLid",
            ],
            "no_second_eye_pair": True,
            "no_head_geometry_change": True,
            "no_runtime_binding_change": True,
            "no_person_activation": True,
        },
        "before": before,
        "after": after,
        "limits": [
            "This candidate is a copied asset and is not loaded by the live runtime.",
            "Automated structural checks cannot prove natural visual fit.",
            "Promotion remains blocked unless fixed front, both three-quarter views, blink, gaze, and protrusion review all pass.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "derived_glb": str(output_glb),
        "derived_sha256": manifest["derived_glb"]["sha256"],
        "manifest": str(manifest_path),
        "source_unchanged": manifest["source_eye"]["unchanged"],
        "r6_unchanged": manifest["target_r6_body"]["unchanged"],
    }, indent=2))


if __name__ == "__main__":
    main()
