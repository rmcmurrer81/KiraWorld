"""Blender worker for a private, inactive body + eye-rig staged assembly.

Run only through ``Core.avatar_body_eye_staged_assembly``.  The worker repeats
all exact-hash and path checks inside Blender, attaches imported eye-rig roots
to one recognized head bone without flattening their hierarchy, exports one
new GLB, and verifies the named left/right controls and morph targets in the
exported GLB before writing its result.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any, Mapping

import bpy  # type: ignore
from mathutils import Matrix, Quaternion, Vector  # type: ignore


GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
STAGED_ROOT = Path("Avatar/avatar_builder/staged_assemblies/body_eye")


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--result", required=True)
    return parser.parse_args(values)


def text(value: Any) -> str:
    return str(value or "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def inside_regular_file(path: Path, root: Path, *, name: str) -> Path:
    if has_symlink_component(path, root):
        raise RuntimeError(f"{name} contains a symlink")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"{name} is outside the project") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise RuntimeError(f"{name} is not a regular non-symlink file")
    return resolved


def project_source(root: Path, raw: Any, *, name: str) -> Path:
    raw_text = text(raw)
    relative = Path(raw_text)
    if not raw_text or relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"{name} is not a safe project-relative path")
    path = inside_regular_file(root / relative, root, name=name)
    if path.suffix.lower() != ".glb":
        raise RuntimeError(f"{name} is not a GLB")
    return path


def expected_sha(value: Any, name: str) -> str:
    digest = text(value).lower()
    if not SHA256_RE.fullmatch(digest):
        raise RuntimeError(f"{name} is not a SHA-256 digest")
    return digest


def read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if path.is_symlink():
        raise RuntimeError(f"result path is a symlink: {path}")
    with path.open("xb") as stream:
        stream.write(payload)


def read_glb_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise RuntimeError(f"truncated GLB: {path}")
        magic, version, declared = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC or version != 2 or declared != path.stat().st_size:
            raise RuntimeError(f"invalid GLB header: {path}")
        consumed = 12
        json_chunk = None
        while consumed < declared:
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                raise RuntimeError(f"truncated GLB chunk: {path}")
            length, kind = struct.unpack("<II", chunk_header)
            consumed += 8
            if consumed + length > declared:
                raise RuntimeError(f"invalid GLB chunk length: {path}")
            payload = stream.read(length)
            consumed += length
            if kind == GLB_JSON_CHUNK:
                if json_chunk is not None:
                    raise RuntimeError(f"multiple GLB JSON chunks: {path}")
                json_chunk = payload
        if consumed != declared or json_chunk is None:
            raise RuntimeError(f"missing GLB JSON chunk: {path}")
    value = json.loads(json_chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("asset", {}).get("version") != "2.0"
        or not isinstance(value.get("meshes"), list)
        or not value["meshes"]
    ):
        raise RuntimeError(f"GLB JSON structure is unsupported: {path}")
    for buffer in value.get("buffers", []):
        if isinstance(buffer, Mapping) and text(buffer.get("uri")):
            raise RuntimeError(f"GLB contains an external buffer URI: {path}")
    for image in value.get("images", []):
        if not isinstance(image, Mapping):
            continue
        uri = text(image.get("uri"))
        if uri and not uri.startswith("data:"):
            raise RuntimeError(f"GLB contains an external image URI: {path}")
    return value


def normalized_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", text(value).lower())


def head_score(name: str) -> int:
    normalized = normalized_name(name)
    if not normalized or "headtop" in normalized or normalized.endswith("headend"):
        return 0
    if normalized == "head":
        return 100
    if re.fullmatch(r"(?:mixamorig)?head\d*", normalized):
        return 90
    if re.search(r"head\d*$", normalized) and not any(
        token in normalized for token in ("forehead", "headwear", "headset")
    ):
        return 70
    return 0


def choose_armature_and_head(body_objects: list[Any], expected_name: str):
    matches = []
    for obj in body_objects:
        if obj.type != "ARMATURE":
            continue
        for bone in obj.data.bones:
            if bone.name == expected_name and head_score(bone.name):
                matches.append((obj, bone))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one recognized head joint named {expected_name!r}; found {len(matches)}"
        )
    return matches[0]


def side_from_name(value: Any) -> str:
    normalized = normalized_name(value)
    if "left" in normalized or normalized.startswith("leye"):
        return "left"
    if "right" in normalized or normalized.startswith("reye"):
        return "right"
    return ""


def eye_controls(eye_objects: list[Any]) -> dict[str, list[str]]:
    controls: dict[str, list[str]] = {"left": [], "right": []}
    for obj in eye_objects:
        normalized = normalized_name(obj.name)
        side = side_from_name(obj.name)
        if (
            side
            and "eye" in normalized
            and any(token in normalized for token in ("pivot", "socket", "control", "aim"))
        ):
            controls[side].append(obj.name)
    return {side: sorted(dict.fromkeys(names)) for side, names in controls.items()}


def eye_morphs(eye_objects: list[Any]) -> list[dict[str, Any]]:
    records = []
    for obj in eye_objects:
        if obj.type != "MESH" or not obj.data.shape_keys:
            continue
        names = [key.name for key in obj.data.shape_keys.key_blocks if key.name != "Basis"]
        if names:
            records.append(
                {"object": obj.name, "side": side_from_name(obj.name), "target_names": names}
            )
    return sorted(records, key=lambda item: item["object"])


def exported_morphs_by_object(document: Mapping[str, Any]) -> dict[str, Counter[str]]:
    """Return named morphs through the exact exported node -> mesh binding.

    Looking only at a file-wide target-name count could accidentally let a
    body morph with the same name hide a missing eyelid morph.  Per-object
    binding makes that substitution impossible.
    """

    meshes = document.get("meshes", [])
    output: dict[str, Counter[str]] = {}
    for node in document.get("nodes", []):
        if not isinstance(node, Mapping) or not isinstance(node.get("mesh"), int):
            continue
        mesh_index = int(node["mesh"])
        if not (0 <= mesh_index < len(meshes)) or not isinstance(meshes[mesh_index], Mapping):
            continue
        target_names = meshes[mesh_index].get("extras", {}).get("targetNames", [])
        if isinstance(target_names, list):
            output[text(node.get("name"))] = Counter(
                text(name) for name in target_names if text(name)
            )
    return output


def descendants(document: Mapping[str, Any], root_index: int) -> set[int]:
    nodes = document.get("nodes", [])
    visited: set[int] = set()
    pending = [root_index]
    while pending:
        index = pending.pop()
        if index in visited or not (0 <= index < len(nodes)):
            continue
        visited.add(index)
        node = nodes[index]
        if isinstance(node, Mapping):
            pending.extend(child for child in node.get("children", []) if isinstance(child, int))
    return visited


def node_local_matrix(node: Mapping[str, Any]) -> Matrix:
    values = node.get("matrix")
    if isinstance(values, list) and len(values) == 16:
        # glTF stores matrices column-major; mathutils accepts row tuples.
        return Matrix(
            tuple(
                tuple(float(values[column * 4 + row]) for column in range(4))
                for row in range(4)
            )
        )
    translation = node.get("translation", [0.0, 0.0, 0.0])
    rotation = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
    scale = node.get("scale", [1.0, 1.0, 1.0])
    translate_matrix = Matrix.Translation(Vector(tuple(float(value) for value in translation)))
    rotate_matrix = Quaternion(
        (
            float(rotation[3]),
            float(rotation[0]),
            float(rotation[1]),
            float(rotation[2]),
        )
    ).to_matrix().to_4x4()
    scale_matrix = Matrix.Diagonal(
        Vector((float(scale[0]), float(scale[1]), float(scale[2]), 1.0))
    )
    return translate_matrix @ rotate_matrix @ scale_matrix


def node_world_matrices(document: Mapping[str, Any]) -> list[Matrix]:
    nodes = document.get("nodes", [])
    parents: dict[int, int] = {}
    for parent_index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            continue
        for child in node.get("children", []):
            if not isinstance(child, int):
                continue
            if child in parents and parents[child] != parent_index:
                raise RuntimeError("GLB node has multiple parents")
            parents[child] = parent_index
    cache: dict[int, Matrix] = {}
    visiting: set[int] = set()

    def world(index: int) -> Matrix:
        if index in cache:
            return cache[index]
        if index in visiting:
            raise RuntimeError("GLB node hierarchy contains a cycle")
        visiting.add(index)
        node = nodes[index]
        if not isinstance(node, Mapping):
            raise RuntimeError("GLB node record is invalid")
        local = node_local_matrix(node)
        value = world(parents[index]) @ local if index in parents else local
        visiting.remove(index)
        cache[index] = value
        return value

    return [world(index) for index in range(len(nodes))]


def exact_named_world_matrix(
    document: Mapping[str, Any], matrices: list[Matrix], name: str
) -> Matrix:
    indices = [
        index
        for index, node in enumerate(document.get("nodes", []))
        if isinstance(node, Mapping) and text(node.get("name")) == name
    ]
    if len(indices) != 1:
        raise RuntimeError(f"GLB node {name!r} is missing or ambiguous")
    return matrices[indices[0]]


def matrix_max_delta(first: Matrix, second: Matrix) -> float:
    return max(
        abs(float(first[row][column]) - float(second[row][column]))
        for row in range(4)
        for column in range(4)
    )


def main() -> None:
    args = parse_args()
    root = Path(args.project_root).resolve(strict=True)
    request_path = inside_regular_file(Path(args.request), root, name="request")
    request = read_json_object(request_path)
    if request.get("schema_version") != 1 or request.get("operation") != (
        "private_inactive_exact_hash_body_eye_assembly"
    ):
        raise RuntimeError("assembly request identity is invalid")
    subject_id = text(request.get("subject_id"))
    run_id = text(request.get("run_id"))
    if not SAFE_ID_RE.fullmatch(subject_id) or not SAFE_ID_RE.fullmatch(run_id):
        raise RuntimeError("assembly request identifiers are invalid")
    run_dir = root / STAGED_ROOT / subject_id / run_id
    if request_path.parent.resolve() != run_dir.resolve():
        raise RuntimeError("request is not inside its exact staged run directory")
    output_path = Path(args.output)
    result_path = Path(args.result)
    if output_path != run_dir / "assembled_body_eyes.glb":
        raise RuntimeError("output path is not the exact staged artifact path")
    if result_path != run_dir / "worker_result.json":
        raise RuntimeError("result path is not the exact staged result path")
    if output_path.exists() or result_path.exists() or output_path.is_symlink() or result_path.is_symlink():
        raise RuntimeError("append-only worker output already exists")
    if has_symlink_component(run_dir, root):
        raise RuntimeError("staged run directory contains a symlink")

    request_output = request.get("output", {})
    if text(request_output.get("run_directory")) != STAGED_ROOT.joinpath(
        subject_id, run_id
    ).as_posix():
        raise RuntimeError("request run directory binding is invalid")
    if text(request_output.get("artifact")) != output_path.relative_to(root).as_posix():
        raise RuntimeError("request artifact binding is invalid")
    if text(request_output.get("worker_result")) != result_path.relative_to(root).as_posix():
        raise RuntimeError("request result binding is invalid")
    policy = request.get("policy", {})
    if policy.get("private_inactive_staging_only") is not True:
        raise RuntimeError("request is not private inactive staging")
    for flag in (
        "owner_approval_inferred",
        "runtime_activation_allowed",
        "live_body_replacement_allowed",
        "public_export_allowed",
        "release_allowed",
    ):
        if policy.get(flag) is not False:
            raise RuntimeError(f"request policy {flag} must be false")

    body_binding = request.get("sources", {}).get("body", {})
    eye_binding = request.get("sources", {}).get("eyes", {})
    body_path = project_source(root, body_binding.get("path"), name="body source")
    eyes_path = project_source(root, eye_binding.get("path"), name="eye source")
    if body_path == eyes_path:
        raise RuntimeError("body and eye sources are not separate")
    body_sha = expected_sha(body_binding.get("sha256"), "body SHA-256")
    eyes_sha = expected_sha(eye_binding.get("sha256"), "eye SHA-256")
    if sha256_file(body_path) != body_sha or sha256_file(eyes_path) != eyes_sha:
        raise RuntimeError("source hash mismatch before Blender import")
    # Repeat the self-contained GLB check inside the Blender process instead
    # of relying only on the outer orchestrator's preflight.
    read_glb_json(body_path)
    source_eye_document = read_glb_json(eyes_path)
    source_before = {"body": body_sha, "eyes": eyes_sha}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(body_path))
    body_objects = [obj for obj in bpy.data.objects if obj not in before]
    if not body_objects:
        raise RuntimeError("body import created no objects")
    expected_head = text(request.get("expected_head_joint"))
    armature, head_bone = choose_armature_and_head(body_objects, expected_head)

    before_eyes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(eyes_path))
    imported_eyes = [obj for obj in bpy.data.objects if obj not in before_eyes]
    if not imported_eyes:
        raise RuntimeError("eye-rig import created no objects")
    controls_before = eye_controls(imported_eyes)
    required_controls = request.get("required_eye_controls", {})
    for side in ("left", "right"):
        expected = sorted(text(name) for name in required_controls.get(side, []))
        if not expected or any(name not in controls_before[side] for name in expected):
            raise RuntimeError(f"required {side} eye controls were not imported")
    morphs_before = eye_morphs(imported_eyes)
    if {record["side"] for record in morphs_before} != {"left", "right"}:
        raise RuntimeError("named left/right eye morphs were not imported")
    expected_morph_count = sum(
        len(record.get("target_names", []))
        for record in request.get("required_eye_morphs", [])
        if isinstance(record, Mapping)
    )
    if sum(len(record["target_names"]) for record in morphs_before) != expected_morph_count:
        raise RuntimeError("imported eye morph count does not match the exact source")

    eye_set = set(imported_eyes)
    roots = [obj for obj in imported_eyes if obj.parent not in eye_set]
    if not roots:
        raise RuntimeError("eye rig has no attachable root")
    root_names = sorted(obj.name for obj in roots)
    # A bone child is emitted under the glTF joint hierarchy rather than under
    # the imported Blender armature object's origin.  The imported 3ec fixture
    # carries an 8.227 mm armature-origin translation; without compensation
    # that exact offset leaked into the exported eye root even though Blender's
    # matrix_world looked unchanged.  Pre-compensate only the armature origin
    # translation, then independently compare source/output world matrices
    # below.  That comparison keeps this fail-closed for other skeletons.
    armature_origin_offset_world = armature.matrix_world.translation.copy()
    for obj in roots:
        native_world = obj.matrix_world.copy()
        obj.parent = armature
        obj.parent_type = "BONE"
        obj.parent_bone = head_bone.name
        corrected_world = native_world.copy()
        corrected_world.translation = (
            corrected_world.translation - armature_origin_offset_world
        )
        obj.matrix_world = corrected_world
        obj["private_inactive_staging_only"] = True
        obj["body_source_sha256"] = body_sha
        obj["eye_source_sha256"] = eyes_sha
        obj["attached_to_head_joint"] = head_bone.name
    bpy.context.view_layer.update()

    controls_after_parent = eye_controls(imported_eyes)
    morphs_after_parent = eye_morphs(imported_eyes)
    if controls_after_parent != controls_before or morphs_after_parent != morphs_before:
        raise RuntimeError("eye controls or morphs changed during head attachment")
    if sha256_file(body_path) != body_sha or sha256_file(eyes_path) != eyes_sha:
        raise RuntimeError("source hash changed before export")

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = body_objects + imported_eyes
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_animations=True,
        export_morph=True,
        export_apply=False,
        export_extras=True,
    )
    if output_path.is_symlink() or not output_path.is_file():
        raise RuntimeError("Blender did not export a regular staged GLB")
    if sha256_file(body_path) != body_sha or sha256_file(eyes_path) != eyes_sha:
        raise RuntimeError("source hash changed during export")

    output_document = read_glb_json(output_path)
    output_nodes = output_document.get("nodes", [])
    names_to_indices: dict[str, list[int]] = {}
    for index, node in enumerate(output_nodes):
        if isinstance(node, Mapping):
            names_to_indices.setdefault(text(node.get("name")), []).append(index)
    for side in ("left", "right"):
        for name in controls_before[side]:
            if len(names_to_indices.get(name, [])) != 1:
                raise RuntimeError(f"exported GLB did not preserve eye control {name!r}")
    head_indices = names_to_indices.get(head_bone.name, [])
    if len(head_indices) != 1:
        raise RuntimeError("exported GLB head joint is missing or ambiguous")
    head_descendants = descendants(output_document, head_indices[0])
    for name in root_names:
        indices = names_to_indices.get(name, [])
        if len(indices) != 1 or indices[0] not in head_descendants:
            raise RuntimeError(f"eye-rig root {name!r} is not attached under the head joint")
    source_world = node_world_matrices(source_eye_document)
    output_world = node_world_matrices(output_document)
    rest_pose_deltas: dict[str, float] = {}
    coordinate_names = sorted(
        set(root_names + controls_before["left"] + controls_before["right"])
    )
    for name in coordinate_names:
        delta = matrix_max_delta(
            exact_named_world_matrix(source_eye_document, source_world, name),
            exact_named_world_matrix(output_document, output_world, name),
        )
        rest_pose_deltas[name] = delta
        if delta > 0.00002:
            raise RuntimeError(
                f"eye node {name!r} was double-transformed during head attachment (delta {delta})"
            )
    after_morphs = exported_morphs_by_object(output_document)
    for record in morphs_before:
        expected_targets = Counter(record["target_names"])
        if after_morphs.get(record["object"], Counter()) != expected_targets:
            raise RuntimeError(
                f"exported GLB did not preserve named morphs on {record['object']!r}"
            )

    result = {
        "schema_version": 1,
        "status": "assembled_private_inactive_unreviewed",
        "subject_id": subject_id,
        "run_id": run_id,
        "source_integrity": {
            "body": {"before_sha256": source_before["body"], "after_sha256": sha256_file(body_path)},
            "eyes": {"before_sha256": source_before["eyes"], "after_sha256": sha256_file(eyes_path)},
        },
        "attachment": {
            "armature": armature.name,
            "head_joint": head_bone.name,
            "eye_rig_roots": root_names,
            "bone_parenting_preserved_in_export": True,
            "blender_armature_origin_precompensation_m": [
                float(value) for value in armature_origin_offset_world
            ],
        },
        "preservation": {
            "separate_eye_controls_preserved": True,
            "named_eye_morphs_preserved": True,
            "native_rest_coordinates_preserved": True,
            "native_rest_matrix_max_delta": max(rest_pose_deltas.values(), default=0.0),
            "native_rest_matrix_delta_by_node": rest_pose_deltas,
            "controls": controls_before,
            "morphs": morphs_before,
        },
        "artifact": {
            "path": output_path.relative_to(root).as_posix(),
            "sha256": sha256_file(output_path),
            "bytes": output_path.stat().st_size,
        },
        "policy": {
            "private_inactive_staging_only": True,
            "owner_approval_inferred": False,
            "runtime_activation_allowed": False,
            "live_body_replacement_allowed": False,
            "public_export_allowed": False,
            "release_allowed": False,
        },
    }
    write_exclusive(result_path, result)
    print(json.dumps({"ok": True, "status": result["status"], "artifact": result["artifact"]}))


if __name__ == "__main__":
    main()
