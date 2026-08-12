"""Exact-hash, private body + eye-rig assembly for Avatar Builder review.

This module is intentionally narrower than avatar production or activation.  It
can validate one body GLB and one separately-authored eye-rig GLB, then ask a
Blender worker to assemble them in a *new* staged run directory.  It never
edits either input, changes a live avatar, infers owner approval, or releases an
artifact.

Dry-run validation is the default API surface.  Execution must be requested
explicitly and remains private, inactive, unreviewed staging only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from typing import Any, Mapping


STAGED_ASSEMBLY_ROOT = Path("Avatar/avatar_builder/staged_assemblies/body_eye")
WORKER_SCRIPT = Path("tools/blender_assemble_avatar_body_eye_staged.py")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A


class StagedAssemblyError(ValueError):
    """A fail-closed validation, integrity, or assembly error."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validate_id(value: Any, name: str) -> str:
    result = _text(value)
    if not SAFE_ID_RE.fullmatch(result):
        raise StagedAssemblyError(f"{name} is not a safe lowercase identifier")
    return result


def _validate_sha256(value: Any, name: str) -> str:
    result = _text(value).lower()
    if not SHA256_RE.fullmatch(result):
        raise StagedAssemblyError(f"{name} is not a SHA-256 digest")
    return result


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def _project_file(project_root: Path, raw_value: Any, *, name: str) -> Path:
    raw_text = _text(raw_value)
    raw = Path(raw_text)
    if not raw_text or raw.is_absolute() or ".." in raw.parts:
        raise StagedAssemblyError(f"{name} must be a safe project-relative path")
    root = project_root.resolve(strict=True)
    unresolved = root / raw
    if _has_symlink_component(unresolved, root):
        raise StagedAssemblyError(f"{name} contains a symlink")
    try:
        resolved = unresolved.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise StagedAssemblyError(f"{name} does not resolve inside the project") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise StagedAssemblyError(f"{name} is not a regular non-symlink file")
    if resolved.suffix.lower() != ".glb":
        raise StagedAssemblyError(f"{name} must be a GLB file")
    return resolved


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _write_exclusive(path: Path, payload: bytes) -> None:
    """Write once and never reinterpret an existing path as this run's file."""

    if path.is_symlink():
        raise StagedAssemblyError(f"append-only target is a symlink: {path}")
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError as exc:
        raise StagedAssemblyError(f"append-only target already exists: {path}") from exc


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StagedAssemblyError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise StagedAssemblyError(f"JSON artifact is not an object: {path}")
    return value


def read_glb_json(path: Path) -> dict[str, Any]:
    """Read enough GLB 2.0 structure for fail-closed dry-run validation."""

    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise StagedAssemblyError(f"truncated GLB header: {path}")
        magic, version, declared_length = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC or version != 2 or declared_length != path.stat().st_size:
            raise StagedAssemblyError(f"invalid GLB 2.0 header: {path}")
        json_chunk: bytes | None = None
        consumed = 12
        while consumed < declared_length:
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                raise StagedAssemblyError(f"truncated GLB chunk header: {path}")
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            consumed += 8
            if chunk_length < 0 or consumed + chunk_length > declared_length:
                raise StagedAssemblyError(f"invalid GLB chunk length: {path}")
            chunk = stream.read(chunk_length)
            if len(chunk) != chunk_length:
                raise StagedAssemblyError(f"truncated GLB chunk: {path}")
            consumed += chunk_length
            if chunk_type == GLB_JSON_CHUNK:
                if json_chunk is not None:
                    raise StagedAssemblyError(f"GLB contains multiple JSON chunks: {path}")
                json_chunk = chunk
        if consumed != declared_length or json_chunk is None:
            raise StagedAssemblyError(f"GLB JSON chunk is missing: {path}")
    try:
        document = json.loads(json_chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StagedAssemblyError(f"invalid GLB JSON document: {path}") from exc
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise StagedAssemblyError(f"unsupported GLB asset document: {path}")
    if not isinstance(document.get("meshes"), list) or not document["meshes"]:
        raise StagedAssemblyError(f"GLB has no meshes: {path}")
    # GLB sources in this pathway must be self-contained.  This prevents an
    # otherwise valid-looking input from reading files outside its exact hash.
    for buffer in document.get("buffers", []):
        if isinstance(buffer, Mapping) and _text(buffer.get("uri")):
            raise StagedAssemblyError(f"GLB has an external buffer URI: {path}")
    for image in document.get("images", []):
        if not isinstance(image, Mapping):
            continue
        uri = _text(image.get("uri"))
        if uri and not uri.startswith("data:"):
            raise StagedAssemblyError(f"GLB has an external image URI: {path}")
    return document


def _normalized_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).lower())


def _head_score(name: str) -> int:
    normalized = _normalized_name(name)
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


def _body_structure(document: Mapping[str, Any]) -> dict[str, Any]:
    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    skins = document.get("skins") if isinstance(document.get("skins"), list) else []
    if not skins:
        raise StagedAssemblyError("body GLB has no skin")
    joint_indices: set[int] = set()
    for skin in skins:
        if not isinstance(skin, Mapping):
            continue
        for index in skin.get("joints", []):
            if isinstance(index, int) and 0 <= index < len(nodes):
                joint_indices.add(index)
    candidates: list[tuple[int, int, str]] = []
    for index in sorted(joint_indices):
        node = nodes[index]
        if not isinstance(node, Mapping):
            continue
        name = _text(node.get("name"))
        score = _head_score(name)
        if score:
            candidates.append((score, index, name))
    if not candidates:
        raise StagedAssemblyError("body GLB has no recognized head joint")
    candidates.sort(reverse=True)
    top_score = candidates[0][0]
    top = [item for item in candidates if item[0] == top_score]
    if len(top) != 1:
        raise StagedAssemblyError("body GLB head joint is ambiguous")
    return {
        "skin_count": len(skins),
        "joint_count": len(joint_indices),
        "recognized_head_joint": top[0][2],
        "recognized_head_node_index": top[0][1],
    }


def _side_from_name(name: Any) -> str:
    normalized = _normalized_name(name)
    if "left" in normalized or normalized.startswith("leye"):
        return "left"
    if "right" in normalized or normalized.startswith("reye"):
        return "right"
    return ""


def _eye_structure(document: Mapping[str, Any]) -> dict[str, Any]:
    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    meshes = document.get("meshes") if isinstance(document.get("meshes"), list) else []
    control_names: dict[str, list[str]] = {"left": [], "right": []}
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        name = _text(node.get("name"))
        normalized = _normalized_name(name)
        side = _side_from_name(name)
        if (
            side
            and "eye" in normalized
            and any(token in normalized for token in ("pivot", "socket", "control", "aim"))
        ):
            control_names[side].append(name)
    if not control_names["left"] or not control_names["right"]:
        raise StagedAssemblyError("eye rig lacks separate named left/right eye controls")

    mesh_nodes: dict[int, list[str]] = {}
    for node in nodes:
        if not isinstance(node, Mapping) or not isinstance(node.get("mesh"), int):
            continue
        mesh_nodes.setdefault(int(node["mesh"]), []).append(_text(node.get("name")))
    morphs: list[dict[str, Any]] = []
    morph_sides: set[str] = set()
    for mesh_index, mesh in enumerate(meshes):
        if not isinstance(mesh, Mapping):
            continue
        names = mesh.get("extras", {}).get("targetNames", [])
        if not isinstance(names, list):
            names = []
        target_count = 0
        for primitive in mesh.get("primitives", []):
            if isinstance(primitive, Mapping) and isinstance(primitive.get("targets"), list):
                target_count = max(target_count, len(primitive["targets"]))
        if target_count <= 0:
            continue
        if len(names) != target_count or any(not _text(name) for name in names):
            raise StagedAssemblyError("eye rig morph targets do not have stable names")
        object_names = mesh_nodes.get(mesh_index, [])
        side = next((_side_from_name(name) for name in object_names if _side_from_name(name)), "")
        if side:
            morph_sides.add(side)
        morphs.append(
            {
                "mesh": _text(mesh.get("name")),
                "objects": object_names,
                "side": side,
                "target_names": [_text(name) for name in names],
            }
        )
    if not morphs or morph_sides != {"left", "right"}:
        raise StagedAssemblyError("eye rig lacks named left/right eye morph targets")
    return {
        "node_count": len(nodes),
        "mesh_count": len(meshes),
        "controls": {
            side: sorted(dict.fromkeys(names)) for side, names in control_names.items()
        },
        "morphs": morphs,
        "morph_target_count": sum(len(item["target_names"]) for item in morphs),
    }


@dataclass(frozen=True)
class ValidatedAssemblyInputs:
    project_root: Path
    subject_id: str
    run_id: str
    body_path: Path
    body_sha256: str
    eye_path: Path
    eye_sha256: str
    body_structure: dict[str, Any]
    eye_structure: dict[str, Any]
    run_dir: Path


def validate_assembly_inputs(
    project_root: str | Path,
    *,
    subject_id: str,
    run_id: str,
    body_path: str | Path,
    body_sha256: str,
    eye_path: str | Path,
    eye_sha256: str,
) -> ValidatedAssemblyInputs:
    root = Path(project_root).resolve(strict=True)
    subject = _validate_id(subject_id, "subject_id")
    run = _validate_id(run_id, "run_id")
    body = _project_file(root, body_path, name="body_path")
    eyes = _project_file(root, eye_path, name="eye_path")
    if body == eyes:
        raise StagedAssemblyError("body and eye rig must be separate GLB files")
    expected_body_sha = _validate_sha256(body_sha256, "body_sha256")
    expected_eye_sha = _validate_sha256(eye_sha256, "eye_sha256")
    if sha256_file(body) != expected_body_sha:
        raise StagedAssemblyError("body GLB SHA-256 mismatch")
    if sha256_file(eyes) != expected_eye_sha:
        raise StagedAssemblyError("eye-rig GLB SHA-256 mismatch")
    body_document = read_glb_json(body)
    eye_document = read_glb_json(eyes)
    body_info = _body_structure(body_document)
    eye_info = _eye_structure(eye_document)

    staged_root = root / STAGED_ASSEMBLY_ROOT
    if _has_symlink_component(staged_root, root):
        raise StagedAssemblyError("staged assembly root contains a symlink")
    run_dir = staged_root / subject / run
    if _has_symlink_component(run_dir, root):
        raise StagedAssemblyError("staged run path contains a symlink")
    if run_dir.exists():
        raise StagedAssemblyError("append-only staged run directory already exists")
    return ValidatedAssemblyInputs(
        project_root=root,
        subject_id=subject,
        run_id=run,
        body_path=body,
        body_sha256=expected_body_sha,
        eye_path=eyes,
        eye_sha256=expected_eye_sha,
        body_structure=body_info,
        eye_structure=eye_info,
        run_dir=run_dir,
    )


def build_dry_run_plan(
    project_root: str | Path,
    *,
    subject_id: str,
    run_id: str,
    body_path: str | Path,
    body_sha256: str,
    eye_path: str | Path,
    eye_sha256: str,
) -> dict[str, Any]:
    validated = validate_assembly_inputs(
        project_root,
        subject_id=subject_id,
        run_id=run_id,
        body_path=body_path,
        body_sha256=body_sha256,
        eye_path=eye_path,
        eye_sha256=eye_sha256,
    )
    payload = {
        "schema_version": 1,
        "operation": "private_inactive_exact_hash_body_eye_assembly",
        "status": "dry_run_validated_not_executed",
        "subject_id": validated.subject_id,
        "run_id": validated.run_id,
        "sources": {
            "body": {
                "path": _relative(validated.body_path, validated.project_root),
                "sha256": validated.body_sha256,
                "bytes": validated.body_path.stat().st_size,
                "structure": validated.body_structure,
            },
            "eyes": {
                "path": _relative(validated.eye_path, validated.project_root),
                "sha256": validated.eye_sha256,
                "bytes": validated.eye_path.stat().st_size,
                "structure": validated.eye_structure,
            },
        },
        "planned_output": {
            "run_directory": _relative(validated.run_dir, validated.project_root),
            "artifact": _relative(
                validated.run_dir / "assembled_body_eyes.glb", validated.project_root
            ),
            "append_only_new_directory_required": True,
        },
        "attachment": {
            "recognized_head_joint": validated.body_structure[
                "recognized_head_joint"
            ],
            "preserve_separate_eye_controls": True,
            "preserve_named_eye_morphs": True,
        },
        "execution_started": False,
        "source_files_changed": False,
        "private_inactive_staging_only": True,
        "owner_approval_inferred": False,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "public_export_allowed": False,
        "release_allowed": False,
    }
    payload["request_identity_sha256"] = canonical_sha256(payload)
    return payload


def _request_document(validated: ValidatedAssemblyInputs) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": "private_inactive_exact_hash_body_eye_assembly",
        "subject_id": validated.subject_id,
        "run_id": validated.run_id,
        "sources": {
            "body": {
                "path": _relative(validated.body_path, validated.project_root),
                "sha256": validated.body_sha256,
            },
            "eyes": {
                "path": _relative(validated.eye_path, validated.project_root),
                "sha256": validated.eye_sha256,
            },
        },
        "expected_head_joint": validated.body_structure["recognized_head_joint"],
        "required_eye_controls": validated.eye_structure["controls"],
        "required_eye_morphs": validated.eye_structure["morphs"],
        "output": {
            "run_directory": _relative(validated.run_dir, validated.project_root),
            "artifact": _relative(
                validated.run_dir / "assembled_body_eyes.glb", validated.project_root
            ),
            "worker_result": _relative(
                validated.run_dir / "worker_result.json", validated.project_root
            ),
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


def _validate_blender(path: str | Path) -> Path:
    blender = Path(path)
    try:
        resolved = blender.resolve(strict=True)
    except OSError as exc:
        raise StagedAssemblyError("Blender executable does not exist") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise StagedAssemblyError("Blender executable is not a regular non-symlink file")
    return resolved


def execute_staged_assembly(
    project_root: str | Path,
    *,
    subject_id: str,
    run_id: str,
    body_path: str | Path,
    body_sha256: str,
    eye_path: str | Path,
    eye_sha256: str,
    blender_path: str | Path,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Create one append-only private staged assembly after exact validation."""

    validated = validate_assembly_inputs(
        project_root,
        subject_id=subject_id,
        run_id=run_id,
        body_path=body_path,
        body_sha256=body_sha256,
        eye_path=eye_path,
        eye_sha256=eye_sha256,
    )
    blender = _validate_blender(blender_path)
    worker = validated.project_root / WORKER_SCRIPT
    if _has_symlink_component(worker, validated.project_root):
        raise StagedAssemblyError("Blender assembly worker contains a symlink")
    if not worker.is_file():
        raise StagedAssemblyError("Blender assembly worker is missing")
    worker_sha_before = sha256_file(worker)
    blender_sha_before = sha256_file(blender)

    validated.run_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        validated.run_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise StagedAssemblyError(
            "append-only staged run directory already exists"
        ) from exc
    request_path = validated.run_dir / "assembly_request.json"
    result_path = validated.run_dir / "worker_result.json"
    output_path = validated.run_dir / "assembled_body_eyes.glb"
    request = _request_document(validated)
    request_payload = canonical_json_bytes(request)
    _write_exclusive(request_path, request_payload)

    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python",
        str(worker),
        "--",
        "--project-root",
        str(validated.project_root),
        "--request",
        str(request_path),
        "--output",
        str(output_path),
        "--result",
        str(result_path),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=validated.project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(30, int(timeout_seconds)),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StagedAssemblyError(f"Blender assembly did not complete: {exc}") from exc

    def retain_worker_failure(status: str, error: str) -> None:
        failure = {
            "schema_version": 1,
            "status": status,
            "error": error,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-8000:],
            "stderr_tail": completed.stderr[-8000:],
            "owner_approval_inferred": False,
            "runtime_activation_allowed": False,
            "release_allowed": False,
        }
        _write_exclusive(
            validated.run_dir / "failure.json", canonical_json_bytes(failure)
        )

    if completed.returncode != 0:
        retain_worker_failure(
            "blender_worker_failed_no_manifest",
            f"Blender exited with code {completed.returncode}",
        )
        raise StagedAssemblyError(
            f"Blender assembly worker failed with exit code {completed.returncode}"
        )
    if sha256_file(worker) != worker_sha_before or sha256_file(blender) != blender_sha_before:
        retain_worker_failure(
            "assembly_tool_changed_during_run_no_manifest",
            "Blender executable or assembly worker changed during the run",
        )
        raise StagedAssemblyError("assembly tooling changed during execution")

    if result_path.is_symlink() or not result_path.is_file():
        retain_worker_failure(
            "blender_worker_result_missing_no_manifest",
            "Blender returned success without a regular worker result",
        )
        raise StagedAssemblyError("Blender worker did not produce a regular result")
    if output_path.is_symlink() or not output_path.is_file():
        retain_worker_failure(
            "blender_worker_artifact_missing_no_manifest",
            "Blender returned success without a regular staged GLB",
        )
        raise StagedAssemblyError("Blender worker did not produce a regular staged GLB")
    result = _read_json_object(result_path)
    if result.get("status") != "assembled_private_inactive_unreviewed":
        raise StagedAssemblyError("Blender worker result status is not acceptable")
    artifact_sha = sha256_file(output_path)
    if _text(result.get("artifact", {}).get("sha256")).lower() != artifact_sha:
        raise StagedAssemblyError("Blender worker artifact hash does not match")
    if _text(result.get("attachment", {}).get("head_joint")) != validated.body_structure[
        "recognized_head_joint"
    ]:
        raise StagedAssemblyError("Blender worker attached to a different head joint")
    for role, source_path, expected_sha in (
        ("body", validated.body_path, validated.body_sha256),
        ("eyes", validated.eye_path, validated.eye_sha256),
    ):
        source_result = result.get("source_integrity", {}).get(role, {})
        if (
            _text(source_result.get("before_sha256")).lower() != expected_sha
            or _text(source_result.get("after_sha256")).lower() != expected_sha
            or sha256_file(source_path) != expected_sha
        ):
            raise StagedAssemblyError(f"{role} source integrity changed during assembly")
    preservation = result.get("preservation", {})
    if preservation.get("separate_eye_controls_preserved") is not True:
        raise StagedAssemblyError("separate eye controls were not preserved")
    if preservation.get("named_eye_morphs_preserved") is not True:
        raise StagedAssemblyError("named eye morphs were not preserved")
    if preservation.get("native_rest_coordinates_preserved") is not True:
        raise StagedAssemblyError("eye-rig native rest coordinates were not preserved")
    try:
        rest_delta = float(preservation.get("native_rest_matrix_max_delta"))
    except (TypeError, ValueError) as exc:
        raise StagedAssemblyError("eye-rig rest-coordinate proof is invalid") from exc
    if not (0.0 <= rest_delta <= 0.00002):
        raise StagedAssemblyError("eye-rig rest-coordinate delta exceeds tolerance")

    created_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1,
        "assembly_kind": "private_inactive_exact_hash_body_eye_assembly",
        "status": "staged_unreviewed_not_approved",
        "created_at": created_at,
        "subject_id": validated.subject_id,
        "run_id": validated.run_id,
        "run_directory": _relative(validated.run_dir, validated.project_root),
        "sources": {
            "body": {
                "path": _relative(validated.body_path, validated.project_root),
                "sha256": validated.body_sha256,
                "changed": False,
            },
            "eyes": {
                "path": _relative(validated.eye_path, validated.project_root),
                "sha256": validated.eye_sha256,
                "changed": False,
            },
        },
        "request": {
            "path": _relative(request_path, validated.project_root),
            "sha256": hashlib.sha256(request_payload).hexdigest(),
        },
        "worker": {
            "path": WORKER_SCRIPT.as_posix(),
            "sha256": worker_sha_before,
            "result_path": _relative(result_path, validated.project_root),
            "result_sha256": sha256_file(result_path),
            "blender_path": str(blender),
            "blender_sha256": blender_sha_before,
        },
        "artifact": {
            "path": _relative(output_path, validated.project_root),
            "sha256": artifact_sha,
            "bytes": output_path.stat().st_size,
        },
        "attachment": result.get("attachment", {}),
        "preservation": preservation,
        "review_state": {
            "objective_quality_gate_passed": False,
            "rendered_visual_review_passed": False,
            "owner_reviewed": False,
            "owner_approved": False,
        },
        "policy": {
            "append_only_staged_run": True,
            "private_inactive_staging_only": True,
            "owner_approval_inferred": False,
            "runtime_activation_allowed": False,
            "live_body_replacement_allowed": False,
            "public_export_allowed": False,
            "release_allowed": False,
        },
    }
    manifest_path = validated.run_dir / "manifest.json"
    _write_exclusive(manifest_path, canonical_json_bytes(manifest))
    return {
        "status": manifest["status"],
        "manifest_path": _relative(manifest_path, validated.project_root),
        "manifest_sha256": sha256_file(manifest_path),
        "artifact_path": manifest["artifact"]["path"],
        "artifact_sha256": artifact_sha,
        "runtime_activation_allowed": False,
        "live_body_replacement_allowed": False,
        "release_allowed": False,
    }
