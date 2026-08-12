"""No-save R24 Attempt 32 exact patch-append inventory diagnostic.

This worker is intentionally narrower than a reconstruction attempt.  It opens
the sealed R24 source in memory, requests only Object_23 from the preserved
patch Blend, verifies the exact seven-object/no-new-collections contract that
R21 Attempt 01 and R24 Attempts 16 and 18-27 already established, inventories
all newly loaded named datablocks, and exits without linking, cleanup, geometry
mutation, rendering, or saving a Blend.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import traceback
from typing import Any, Iterable, Mapping

try:  # The static suite must import this module without Blender installed.
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised by static import
    bpy = None  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_PATCH_APPEND_INVENTORY_ATTEMPT32_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "941facf7a0f984b87b3e30851553a7409c5ca895cc0afdf3fdb9de99c89cdfe9"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_project_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"path escapes project root: {relative}") from error
    return candidate


def exclusive_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def file_record(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
    }


def require_file_record(label: str, record: Mapping[str, object]) -> dict[str, object]:
    path = resolve_project_path(str(record["path"]))
    if not path.is_file():
        raise RuntimeError(f"bound file is absent: {label}: {path}")
    actual = file_record(path)
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"bound SHA-256 drifted: {label}")
    return actual


def verify_manifest(config_path: Path, config: Mapping[str, object]) -> dict[str, object]:
    expected_path = resolve_project_path(CONFIG_RELATIVE)
    if config_path.resolve() != expected_path:
        raise RuntimeError("Attempt 32 config path is not the exact recorded path")
    actual_config_hash = sha256_file(config_path)
    if actual_config_hash != EXPECTED_CONFIG_SHA256:
        raise RuntimeError("Attempt 32 config SHA-256 drifted")
    records: dict[str, object] = {
        "attempt32_config": file_record(config_path),
        "attempt32_proposal": require_file_record(
            "attempt32_proposal", config["proposal"]  # type: ignore[index]
        ),
    }
    bindings = config["bindings"]  # type: ignore[index]
    if not isinstance(bindings, Mapping):
        raise RuntimeError("Attempt 32 bindings are not a mapping")
    for label, record in bindings.items():
        if not isinstance(record, Mapping):
            raise RuntimeError(f"invalid bound record: {label}")
        records[str(label)] = require_file_record(str(label), record)
    return records


def validate_historical_contract(config: Mapping[str, object]) -> None:
    contract = config["historical_append_contract"]  # type: ignore[index]
    if not isinstance(contract, Mapping):
        raise RuntimeError("historical append contract is absent")
    names = list(contract["expected_appended_object_names"])  # type: ignore[arg-type]
    if len(names) != 7 or len(set(names)) != 7:
        raise RuntimeError("historical append contract is not exactly seven unique names")
    if canonical_sha256(names) != contract["expected_appended_object_names_sha256"]:
        raise RuntimeError("historical ordered object inventory hash drifted")
    dependencies = list(
        contract["dependency_object_names_removed_in_memory_only_by_future_reconstruction"]  # type: ignore[arg-type]
    )
    if len(dependencies) != 6 or "Object_23" in dependencies:
        raise RuntimeError("historical six-object dependency contract drifted")
    if sorted(dependencies + ["Object_23"]) != names:
        raise RuntimeError("historical dependency inventory does not partition seven objects")
    if canonical_sha256(dependencies) != contract["dependency_object_names_sha256"]:
        raise RuntimeError("historical dependency inventory hash drifted")
    expected_collections = list(contract["expected_new_collection_names"])  # type: ignore[arg-type]
    if expected_collections:
        raise RuntimeError("historical contract unexpectedly permits new collections")
    if canonical_sha256(expected_collections) != contract[
        "expected_new_collection_names_sha256"
    ]:
        raise RuntimeError("historical empty-collection inventory hash drifted")
    if contract["attempt32_cleanup_allowed"] is not False:
        raise RuntimeError("Attempt 32 cleanup must remain forbidden")


def validate_historical_evidence(config: Mapping[str, object]) -> None:
    authority = config["bound_historical_append_authority"]  # type: ignore[index]
    bindings = config["bindings"]  # type: ignore[index]
    if not isinstance(authority, Mapping) or not isinstance(bindings, Mapping):
        raise RuntimeError("historical authority binding is malformed")
    names = list(authority["binding_names"])  # type: ignore[arg-type]
    if len(names) != int(authority["file_count"]):
        raise RuntimeError("historical authority file count drifted")
    if sum(int(bindings[name]["bytes"]) for name in names) != int(
        authority["total_bytes"]
    ):
        raise RuntimeError("historical authority byte total drifted")
    expected_hash = authority["expected_ordered_object_names_sha256"]
    expected_status = authority["expected_status"]
    expected_attempts = list(authority["passing_inventory_attempts"])  # type: ignore[arg-type]
    if expected_attempts != [16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]:
        raise RuntimeError("historical passing-attempt sequence drifted")
    for attempt in expected_attempts:
        record = bindings[f"attempt{attempt}_append_inventory"]
        inventory = json.loads(
            resolve_project_path(str(record["path"])).read_text(encoding="utf-8")
        )
        if inventory["status"] != expected_status:
            raise RuntimeError(f"Attempt {attempt} append status drifted")
        if inventory["actual_appended_object_names_sha256"] != expected_hash:
            raise RuntimeError(f"Attempt {attempt} append object digest drifted")
        if inventory["actual_appended_object_names"] != inventory[
            "expected_appended_object_names"
        ]:
            raise RuntimeError(f"Attempt {attempt} append names drifted")
        if inventory["actual_new_collection_names"] != []:
            raise RuntimeError(f"Attempt {attempt} introduced a collection")
        if inventory["missing_object_names"] or inventory["extra_object_names"]:
            raise RuntimeError(f"Attempt {attempt} append inventory is incomplete")
        if any(
            inventory[field]
            for field in ("geometry_mutation_reached", "render_reached", "blend_saved")
        ):
            raise RuntimeError(f"Attempt {attempt} append evidence exceeded scope")


def validate_attempt31_failure(config: Mapping[str, object]) -> None:
    bindings = config["bindings"]  # type: ignore[index]
    contract = config["attempt31_failure_contract"]  # type: ignore[index]
    failure_record = bindings["attempt31_failure"]  # type: ignore[index]
    failure = json.loads(
        resolve_project_path(str(failure_record["path"])).read_text(encoding="utf-8")
    )
    if failure["error_type"] != contract["error_type"]:
        raise RuntimeError("Attempt 31 error type drifted")
    if failure["error"] != contract["error"]:
        raise RuntimeError("Attempt 31 exact failure text drifted")
    if failure["blend_saved"] or failure["runtime_changed"]:
        raise RuntimeError("Attempt 31 safe-failure truth drifted")
    external_path = resolve_project_path(str(contract["attempt31_external_integrity_path"]))
    if external_path.exists():
        raise RuntimeError("Attempt 31 external-integrity absence truth drifted")


def float_token(value: float) -> bytes:
    return struct.pack("!d", float(value))


def int_token(value: int) -> bytes:
    return struct.pack("!q", int(value))


def string_token(value: object) -> bytes:
    return (str(value) + "\0").encode("utf-8")


def sealed_body_digest(body: Any) -> dict[str, object]:
    if body.type != "MESH" or body.data is None:
        raise RuntimeError("sealed body is not a mesh")
    mesh = body.data
    digest = hashlib.sha256()
    for token in (body.name, body.type, mesh.name):
        digest.update(string_token(token))
    for row in body.matrix_world:
        for value in row:
            digest.update(float_token(value))
    digest.update(int_token(len(mesh.vertices)))
    digest.update(int_token(len(mesh.edges)))
    digest.update(int_token(len(mesh.polygons)))
    for vertex in mesh.vertices:
        digest.update(int_token(vertex.index))
        for value in vertex.co:
            digest.update(float_token(value))
    for edge in mesh.edges:
        digest.update(int_token(edge.index))
        digest.update(int_token(edge.vertices[0]))
        digest.update(int_token(edge.vertices[1]))
    for polygon in mesh.polygons:
        digest.update(int_token(polygon.index))
        digest.update(int_token(polygon.material_index))
        digest.update(int_token(1 if polygon.use_smooth else 0))
        digest.update(int_token(len(polygon.vertices)))
        for vertex_index in polygon.vertices:
            digest.update(int_token(vertex_index))
    material_names = [value.name if value else None for value in mesh.materials]
    modifier_signature = [
        {
            "name": value.name,
            "type": value.type,
            "object": getattr(getattr(value, "object", None), "name", None),
        }
        for value in body.modifiers
    ]
    digest.update(string_token(canonical_sha256(material_names)))
    digest.update(string_token(canonical_sha256(modifier_signature)))
    return {
        "object": body.name,
        "mesh": mesh.name,
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "polygon_count": len(mesh.polygons),
        "material_names": material_names,
        "modifier_signature": modifier_signature,
        "sha256": digest.hexdigest(),
    }


def pointer_set(values: Iterable[Any]) -> set[int]:
    return {int(value.as_pointer()) for value in values}


def snapshot_data_pointers(collection_names: Iterable[str]) -> dict[str, set[int]]:
    assert bpy is not None
    return {
        name: pointer_set(getattr(bpy.data, name))
        for name in collection_names
    }


def library_path(value: Any) -> str | None:
    library = getattr(value, "library", None)
    return str(library.filepath) if library is not None else None


def describe_object(value: Any) -> dict[str, object]:
    return {
        "pointer": int(value.as_pointer()),
        "name": value.name,
        "type": value.type,
        "data_name": getattr(getattr(value, "data", None), "name", None),
        "parent_name": getattr(getattr(value, "parent", None), "name", None),
        "library": library_path(value),
        "collection_names": sorted(collection.name for collection in value.users_collection),
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "object": getattr(getattr(modifier, "object", None), "name", None),
            }
            for modifier in value.modifiers
        ],
    }


def describe_data_block(value: Any) -> dict[str, object]:
    record: dict[str, object] = {
        "pointer": int(value.as_pointer()),
        "name": value.name,
        "rna_type": value.bl_rna.identifier,
        "library": library_path(value),
        "users": int(value.users),
    }
    if hasattr(value, "vertices"):
        record["vertex_count"] = len(value.vertices)
    if hasattr(value, "polygons"):
        record["polygon_count"] = len(value.polygons)
    return record


def new_data_inventory(
    before: Mapping[str, set[int]], collection_names: Iterable[str]
) -> dict[str, list[dict[str, object]]]:
    assert bpy is not None
    result: dict[str, list[dict[str, object]]] = {}
    for name in collection_names:
        values = [
            value
            for value in getattr(bpy.data, name)
            if int(value.as_pointer()) not in before[name]
        ]
        values.sort(key=lambda value: (value.name, int(value.as_pointer())))
        if name == "objects":
            result[name] = [describe_object(value) for value in values]
        else:
            result[name] = [describe_data_block(value) for value in values]
    return result


def returned_slot_record(index: int, value: Any) -> dict[str, object]:
    if value is None:
        return {"index": index, "is_none": True}
    return {
        "index": index,
        "is_none": False,
        "pointer": int(value.as_pointer()),
        "name": value.name,
        "type": value.type,
        "data_name": getattr(getattr(value, "data", None), "name", None),
    }


def require_exact_append_contract(
    config: Mapping[str, object], inventory: Mapping[str, object]
) -> None:
    contract = config["historical_append_contract"]  # type: ignore[index]
    requested = str(config["objects"]["requested_patch_object"])  # type: ignore[index]
    slots = list(inventory["returned_target_slots"])  # type: ignore[arg-type]
    if len(slots) != int(config["diagnostic_contract"]["requested_target_slot_count"]):  # type: ignore[index]
        raise RuntimeError("Attempt 32 returned target-slot count drifted")
    slot = slots[0]
    if (
        slot.get("is_none") is not False
        or slot.get("name") != requested
        or slot.get("type") != "MESH"
        or slot.get("data_name")
        != contract["requested_patch_signature"]["data_name"]
    ):
        raise RuntimeError("Attempt 32 returned target slot drifted")
    expected_names = list(contract["expected_appended_object_names"])  # type: ignore[arg-type]
    actual_names = list(inventory["actual_appended_object_names"])  # type: ignore[arg-type]
    if actual_names != expected_names:
        raise RuntimeError(
            "Attempt 32 exact seven-object append inventory drifted: "
            f"expected={expected_names!r}; actual={actual_names!r}"
        )
    if canonical_sha256(actual_names) != contract[
        "expected_appended_object_names_sha256"
    ]:
        raise RuntimeError("Attempt 32 actual ordered append digest drifted")
    actual_collections = list(inventory["actual_new_collection_names"])  # type: ignore[arg-type]
    if actual_collections != list(contract["expected_new_collection_names"]):  # type: ignore[arg-type]
        raise RuntimeError("Attempt 32 introduced unexpected collections")
    signatures = {
        value["name"]: value
        for value in inventory["new_named_data_blocks"]["objects"]  # type: ignore[index]
    }
    linked_names = sorted(
        str(value["name"])
        for value in inventory["new_named_data_blocks"]["objects"]  # type: ignore[index]
        if value["collection_names"]
    )
    if linked_names:
        raise RuntimeError(
            "Attempt 32 appended objects are linked to collections: "
            f"{linked_names!r}"
        )
    patch_expected = contract["requested_patch_signature"]
    patch = signatures.get(str(patch_expected["name"]))
    if patch is None:
        raise RuntimeError("Attempt 32 requested patch signature is absent")
    for key in ("name", "type", "data_name", "parent_name"):
        if patch[key] != patch_expected[key]:
            raise RuntimeError(f"Attempt 32 patch signature drifted: {key}")
    modifiers = patch["modifiers"]
    if len(modifiers) != 1:
        raise RuntimeError("Attempt 32 patch modifier count drifted")
    modifier = modifiers[0]
    if (
        modifier["name"] != patch_expected["armature_modifier_name"]
        or modifier["type"] != patch_expected["armature_modifier_type"]
        or modifier["object"] != patch_expected["armature_modifier_object"]
    ):
        raise RuntimeError("Attempt 32 patch armature modifier drifted")
    dependencies = sorted(name for name in actual_names if name != "Object_23")
    expected_dependencies = list(
        contract["dependency_object_names_removed_in_memory_only_by_future_reconstruction"]  # type: ignore[arg-type]
    )
    if dependencies != expected_dependencies:
        raise RuntimeError("Attempt 32 six-object dependency inventory drifted")


def diagnose(config_path: Path, config: Mapping[str, object]) -> None:
    if bpy is None:
        raise RuntimeError("Attempt 32 must run inside Blender")
    output_contract = config["output"]  # type: ignore[index]
    output = resolve_project_path(str(output_contract["root"]))
    if output.exists():
        raise RuntimeError(f"Attempt 32 refuses to overwrite output: {output}")

    validate_historical_contract(config)
    validate_historical_evidence(config)
    validate_attempt31_failure(config)
    verified_before = verify_manifest(config_path, config)

    output.mkdir(parents=True, exist_ok=False)
    phase = "write_attempt_started"
    partial: dict[str, object] = {}
    exclusive_write_json(
        output / str(output_contract["started"]),
        {
            "schema": "kira.avatar.r24.blackproject_attempt32.started.v1",
            "created_utc": utc_now(),
            "status": "STARTED_EXACT_APPEND_INVENTORY_ONLY",
            "config": file_record(config_path),
            "worker": file_record(Path(__file__).resolve()),
            "geometry_mutation_reached": False,
            "render_reached": False,
            "blend_saved": False,
            "runtime_changed": False,
        },
    )

    try:
        phase = "open_sealed_source_in_memory"
        source_blend = resolve_project_path(
            str(config["bindings"]["sealed_r24_source_blend"]["path"])  # type: ignore[index]
        )
        bpy.ops.wm.open_mainfile(filepath=str(source_blend), load_ui=False)
        body_name = str(config["objects"]["sealed_body"])  # type: ignore[index]
        body = bpy.data.objects.get(body_name)
        if body is None:
            raise RuntimeError("sealed R24 body is absent")
        body_before = sealed_body_digest(body)
        collection_names = list(config["data_collection_names"])  # type: ignore[arg-type]
        before_pointers = snapshot_data_pointers(collection_names)
        before_counts = {name: len(getattr(bpy.data, name)) for name in collection_names}

        phase = "request_object23_and_inventory_exact_hierarchy"
        patch_blend = resolve_project_path(
            str(config["bindings"]["preserved_patch_blend"]["path"])  # type: ignore[index]
        )
        requested = str(config["objects"]["requested_patch_object"])  # type: ignore[index]
        with bpy.data.libraries.load(str(patch_blend), link=False) as (source, target):
            source_library_object_names = sorted(str(name) for name in source.objects)
            if requested not in source.objects:
                raise RuntimeError("preserved patch library lacks Object_23")
            target.objects = [requested]
        returned_slots = [
            returned_slot_record(index, value)
            for index, value in enumerate(target.objects)
        ]

        new_blocks = new_data_inventory(before_pointers, collection_names)
        actual_names = [value["name"] for value in new_blocks["objects"]]
        actual_new_collections = [
            value["name"] for value in new_blocks["collections"]
        ]
        after_counts = {name: len(getattr(bpy.data, name)) for name in collection_names}
        attempt15_new_meshes = [
            value for value in new_blocks["objects"] if value["type"] == "MESH"
        ]
        append_observation: dict[str, object] = {
            "requested_object": requested,
            "source_library_object_names": source_library_object_names,
            "returned_target_slots": returned_slots,
            "expected_appended_object_names": config["historical_append_contract"][  # type: ignore[index]
                "expected_appended_object_names"
            ],
            "expected_appended_object_names_sha256": config[
                "historical_append_contract"  # type: ignore[index]
            ]["expected_appended_object_names_sha256"],
            "actual_appended_object_names": actual_names,
            "actual_appended_object_names_sha256": canonical_sha256(actual_names),
            "expected_new_collection_names": [],
            "actual_new_collection_names": actual_new_collections,
            "before_data_block_counts": before_counts,
            "after_data_block_counts": after_counts,
            "new_named_data_blocks": new_blocks,
            "obsolete_attempt15_singleton_predicate": {
                "new_object_count": len(new_blocks["objects"]),
                "new_mesh_count": len(attempt15_new_meshes),
                "exactly_one_new_mesh_passes": (
                    len(new_blocks["objects"]) == 1
                    and len(attempt15_new_meshes) == 1
                ),
            },
        }
        partial["append_observation"] = append_observation
        require_exact_append_contract(config, append_observation)

        phase = "verify_sealed_body_and_bound_files"
        body_after = sealed_body_digest(body)
        if body_after != body_before:
            raise RuntimeError("sealed body digest changed during append inventory")
        verified_after = verify_manifest(config_path, config)
        if verified_after != verified_before:
            raise RuntimeError("bound file inventory changed during append inventory")

        phase = "write_patch_append_inventory"
        exclusive_write_json(
            output / str(output_contract["diagnostic"]),
            {
                "schema": "kira.avatar.r24.blackproject_attempt32.patch_append_inventory.v1",
                "created_utc": utc_now(),
                "status": "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_NO_SAVE",
                "historical_authority": {
                    "passing_attempts": config["bound_historical_append_authority"][  # type: ignore[index]
                        "passing_inventory_attempts"
                    ],
                    "canonical_ordered_object_names_sha256": config[
                        "historical_append_contract"  # type: ignore[index]
                    ]["expected_appended_object_names_sha256"],
                    "next_reconstruction_direction": config[
                        "historical_append_contract"  # type: ignore[index]
                    ]["future_reconstruction_direction"],
                },
                "append_observation": append_observation,
                "sealed_body_before": body_before,
                "sealed_body_after": body_after,
                "sealed_body_pre_post_exact": True,
                "bound_files_before": verified_before,
                "bound_files_after": verified_after,
                "bound_files_pre_post_exact": True,
                "scene_link_reached": False,
                "dependency_cleanup_reached": False,
                "geometry_mutation_reached": False,
                "triangulation_reached": False,
                "reconstruction_reached": False,
                "graft_reached": False,
                "render_reached": False,
                "blend_saved": False,
                "runtime_changed": False,
            },
        )
    except Exception as error:
        failure = {
            "schema": "kira.avatar.r24.blackproject_attempt32.failure.v1",
            "created_utc": utc_now(),
            "status": "FAILED_CLOSED_NO_SAVE",
            "phase": phase,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "partial_observation": partial,
            "scene_link_reached": False,
            "dependency_cleanup_reached": False,
            "geometry_mutation_reached": False,
            "triangulation_reached": False,
            "reconstruction_reached": False,
            "graft_reached": False,
            "render_reached": False,
            "blend_saved": False,
            "runtime_changed": False,
        }
        failure_path = output / str(output_contract["failure"])
        if not failure_path.exists():
            exclusive_write_json(failure_path, failure)
        raise


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    diagnose(config_path, config)


if __name__ == "__main__":
    main()
