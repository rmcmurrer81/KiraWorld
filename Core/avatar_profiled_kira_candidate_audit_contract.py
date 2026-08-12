"""Pure path/hash contract for profiled Kira candidate post-build audits.

The contract performs no Blender work and creates no files.  It confines a
candidate and its optional private GLB to one inactive private-owner-review
directory and confines append-only audit evidence to a new direct child of the
versioned RecoverySprint audit root.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Mapping


PRIVATE_ROOT = Path("Avatar/private_owner_review")
AUDIT_ROOT = Path(
    "RecoverySprint/continuation_20260801/profiled_kira_candidate_audits"
)
MAIN_EVIDENCE_NAME = "PROFILED_KIRA_CANDIDATE_POSTBUILD_AUDIT.json"
GLB_EVIDENCE_NAME = "PROFILED_KIRA_PRIVATE_GLB_FRESH_IMPORT_AUDIT.json"
CANDIDATE_RE = re.compile(r"^kira_profiled_adult_candidate_[a-z0-9_]{8,95}$")
ATTEMPT_RE = re.compile(
    r"^(kira_profiled_adult_candidate_[a-z0-9_]{8,95})"
    r"__audit_attempt_[a-z0-9_]{2,64}$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProfiledKiraCandidateAuditContractError(ValueError):
    """Raised when an audit path or exact hash is outside the safe contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory_glb_container(path: Path) -> dict[str, Any]:
    """Read a GLB 2.0 JSON chunk without importing or mutating its scene."""

    glb = Path(path)
    data = glb.read_bytes()
    if len(data) < 20:
        raise ProfiledKiraCandidateAuditContractError("glb_container_too_short")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise ProfiledKiraCandidateAuditContractError("glb_header_invalid")
    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ProfiledKiraCandidateAuditContractError("glb_chunk_header_truncated")
        length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        end = offset + int(length)
        if end > len(data):
            raise ProfiledKiraCandidateAuditContractError("glb_chunk_truncated")
        chunks.append((int(chunk_type), data[offset:end]))
        offset = end
    json_chunks = [payload for kind, payload in chunks if kind == 0x4E4F534A]
    if len(json_chunks) != 1:
        raise ProfiledKiraCandidateAuditContractError("glb_json_chunk_count_invalid")
    try:
        payload = json.loads(json_chunks[0].rstrip(b" \t\r\n\x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfiledKiraCandidateAuditContractError("glb_json_chunk_invalid") from exc
    if not isinstance(payload, Mapping):
        raise ProfiledKiraCandidateAuditContractError("glb_json_root_invalid")

    def records(name: str) -> list[Mapping[str, Any]]:
        value = payload.get(name, [])
        if not isinstance(value, list):
            raise ProfiledKiraCandidateAuditContractError(
                f"glb_json_array_invalid:{name}"
            )
        return [item if isinstance(item, Mapping) else {} for item in value]

    nodes = records("nodes")
    meshes = records("meshes")
    accessors = records("accessors")
    animations = records("animations")
    animation_records: list[dict[str, Any]] = []
    weight_channels: list[dict[str, Any]] = []
    for animation_index, animation in enumerate(animations):
        channels = animation.get("channels", [])
        samplers = animation.get("samplers", [])
        channels = channels if isinstance(channels, list) else []
        samplers = samplers if isinstance(samplers, list) else []
        paths: dict[str, int] = {}
        for channel_index, raw_channel in enumerate(channels):
            channel = raw_channel if isinstance(raw_channel, Mapping) else {}
            target = channel.get("target") if isinstance(channel.get("target"), Mapping) else {}
            path_name = str(target.get("path") or "")
            paths[path_name] = paths.get(path_name, 0) + 1
            if path_name != "weights":
                continue
            node_index = target.get("node")
            node = (
                nodes[int(node_index)]
                if isinstance(node_index, int) and 0 <= node_index < len(nodes)
                else {}
            )
            mesh_index = node.get("mesh")
            mesh = (
                meshes[int(mesh_index)]
                if isinstance(mesh_index, int) and 0 <= mesh_index < len(meshes)
                else {}
            )
            primitives = mesh.get("primitives", [])
            primitives = primitives if isinstance(primitives, list) else []
            target_counts = [
                len(primitive.get("targets", []))
                if isinstance(primitive, Mapping)
                and isinstance(primitive.get("targets", []), list)
                else 0
                for primitive in primitives
            ]
            sampler_index = channel.get("sampler")
            sampler = (
                samplers[int(sampler_index)]
                if isinstance(sampler_index, int) and 0 <= sampler_index < len(samplers)
                and isinstance(samplers[int(sampler_index)], Mapping)
                else {}
            )
            output_index = sampler.get("output")
            accessor = (
                accessors[int(output_index)]
                if isinstance(output_index, int) and 0 <= output_index < len(accessors)
                else {}
            )
            weight_channels.append(
                {
                    "animation_index": animation_index,
                    "animation_name": animation.get("name"),
                    "channel_index": channel_index,
                    "target_node_index": node_index,
                    "target_node_name": node.get("name"),
                    "target_mesh_index": mesh_index,
                    "target_mesh_name": mesh.get("name"),
                    "primitive_morph_target_counts": target_counts,
                    "mesh_default_weight_count": len(mesh.get("weights", []))
                    if isinstance(mesh.get("weights", []), list)
                    else 0,
                    "output_accessor_index": output_index,
                    "output_accessor_count": accessor.get("count"),
                    "output_accessor_type": accessor.get("type"),
                    "weight_channel_has_declared_morph_targets": any(
                        count > 0 for count in target_counts
                    ),
                }
            )
        animation_records.append(
            {
                "index": animation_index,
                "name": animation.get("name"),
                "channel_count": len(channels),
                "sampler_count": len(samplers),
                "target_path_counts": paths,
            }
        )
    result = {
        "schema_version": 1,
        "inventory": "glb_2_container_json_inventory_v1",
        "path": glb.name,
        "sha256": sha256_file(glb),
        "size_bytes": len(data),
        "declared_length_bytes": declared_length,
        "glb_version": version,
        "chunk_types": [f"0x{kind:08x}" for kind, _payload in chunks],
        "scene_count": len(records("scenes")),
        "node_count": len(nodes),
        "node_names": [node.get("name") for node in nodes],
        "mesh_count": len(meshes),
        "mesh_names": [mesh.get("name") for mesh in meshes],
        "skin_count": len(records("skins")),
        "skin_names": [record.get("name") for record in records("skins")],
        "material_count": len(records("materials")),
        "material_names": [record.get("name") for record in records("materials")],
        "animation_count": len(animations),
        "animations": animation_records,
        "weight_animation_channels": weight_channels,
        "weight_channel_count": len(weight_channels),
        "weight_channels_without_declared_morph_targets": sum(
            record["weight_channel_has_declared_morph_targets"] is not True
            for record in weight_channels
        ),
        "extensions_used": list(payload.get("extensionsUsed", []))
        if isinstance(payload.get("extensionsUsed", []), list)
        else [],
        "read_only": True,
        "fresh_import_survival_proven": False,
    }
    return result


def _text(value: Any) -> str:
    return str(value or "").strip()


def _project_file(
    project_root: Path,
    raw: Any,
    *,
    label: str,
    suffix: str,
) -> Path:
    root = Path(project_root).resolve(strict=True)
    relative = Path(_text(raw))
    if not _text(raw) or relative.is_absolute() or ".." in relative.parts:
        raise ProfiledKiraCandidateAuditContractError(f"{label}_path_unsafe")
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ProfiledKiraCandidateAuditContractError(
            f"{label}_path_escaped_project"
        ) from exc
    if not path.is_file() or path.suffix.lower() != suffix.lower():
        raise ProfiledKiraCandidateAuditContractError(f"{label}_file_invalid")
    return path


def _exact_hash(path: Path, raw: Any, label: str) -> str:
    expected = _text(raw).lower()
    if not SHA256_RE.fullmatch(expected):
        raise ProfiledKiraCandidateAuditContractError(f"{label}_sha256_invalid")
    actual = sha256_file(path)
    if actual != expected:
        raise ProfiledKiraCandidateAuditContractError(f"{label}_sha256_mismatch")
    return actual


def _candidate_directory(root: Path, blend: Path) -> tuple[Path, str]:
    private = (root / PRIVATE_ROOT).resolve(strict=True)
    candidate_dir = blend.parent.resolve(strict=True)
    if candidate_dir.parent != private:
        raise ProfiledKiraCandidateAuditContractError(
            "candidate_not_direct_private_owner_review_child"
        )
    candidate_id = candidate_dir.name
    if not CANDIDATE_RE.fullmatch(candidate_id):
        raise ProfiledKiraCandidateAuditContractError("candidate_id_invalid")
    if blend.name != f"{candidate_id}.blend":
        raise ProfiledKiraCandidateAuditContractError("candidate_blend_name_invalid")
    return candidate_dir, candidate_id


def _new_output_directory(
    root: Path,
    raw: Any,
    candidate_id: str,
) -> Path:
    relative = Path(_text(raw))
    if not _text(raw) or relative.is_absolute() or ".." in relative.parts:
        raise ProfiledKiraCandidateAuditContractError("audit_output_path_unsafe")
    if relative.parent.as_posix() != AUDIT_ROOT.as_posix():
        raise ProfiledKiraCandidateAuditContractError(
            "audit_output_not_direct_versioned_audit_child"
        )
    match = ATTEMPT_RE.fullmatch(relative.name)
    if match is None or match.group(1) != candidate_id:
        raise ProfiledKiraCandidateAuditContractError("audit_output_name_invalid")
    output = (root / relative).resolve()
    audit_root = (root / AUDIT_ROOT).resolve()
    try:
        audit_root.relative_to(root)
        output.relative_to(root)
    except ValueError as exc:
        raise ProfiledKiraCandidateAuditContractError(
            "audit_output_escaped_project"
        ) from exc
    if output.parent != audit_root:
        raise ProfiledKiraCandidateAuditContractError("audit_output_escaped_root")
    if output.exists():
        raise ProfiledKiraCandidateAuditContractError(
            "audit_output_exists_refuse_overwrite"
        )
    return output


def evaluate_postbuild_audit_preflight(
    project_root: Path,
    *,
    blend_path: Path | str,
    blend_sha256: str,
    build_evidence_sha256: str,
    output_dir: Path | str,
    optional_glb_path: Path | str | None = None,
    optional_glb_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate exact read-only inputs and one append-only output target."""

    root = Path(project_root).resolve(strict=True)
    blockers: list[str] = []
    resolved: dict[str, Any] = {}
    try:
        blend = _project_file(root, blend_path, label="candidate_blend", suffix=".blend")
        candidate_dir, candidate_id = _candidate_directory(root, blend)
        resolved["blend"] = {
            "path": blend.relative_to(root).as_posix(),
            "sha256": _exact_hash(blend, blend_sha256, "candidate_blend"),
        }
        build_evidence = candidate_dir / "BUILD_EVIDENCE.json"
        if not build_evidence.is_file():
            raise ProfiledKiraCandidateAuditContractError(
                "candidate_build_evidence_missing"
            )
        resolved["build_evidence"] = {
            "path": build_evidence.relative_to(root).as_posix(),
            "sha256": _exact_hash(
                build_evidence,
                build_evidence_sha256,
                "candidate_build_evidence",
            ),
        }
        glb_requested = optional_glb_path is not None or optional_glb_sha256 is not None
        if glb_requested:
            if optional_glb_path is None or optional_glb_sha256 is None:
                raise ProfiledKiraCandidateAuditContractError(
                    "optional_glb_path_and_sha256_required_together"
                )
            glb = _project_file(
                root,
                optional_glb_path,
                label="optional_private_glb",
                suffix=".glb",
            )
            if glb.parent.resolve() != candidate_dir:
                raise ProfiledKiraCandidateAuditContractError(
                    "optional_private_glb_not_in_candidate_directory"
                )
            if glb.name != f"{candidate_id}.private.glb":
                raise ProfiledKiraCandidateAuditContractError(
                    "optional_private_glb_name_invalid"
                )
            resolved["optional_private_glb"] = {
                "path": glb.relative_to(root).as_posix(),
                "sha256": _exact_hash(
                    glb,
                    optional_glb_sha256,
                    "optional_private_glb",
                ),
            }
        output = _new_output_directory(root, output_dir, candidate_id)
        resolved["output_directory"] = output.relative_to(root).as_posix()
        resolved["candidate_directory"] = candidate_dir.relative_to(root).as_posix()
        resolved["candidate_id"] = candidate_id
    except (OSError, ProfiledKiraCandidateAuditContractError) as exc:
        blockers.append(str(exc) or type(exc).__name__)
    return {
        "schema_version": 1,
        "preflight": "profiled_kira_candidate_postbuild_audit_v1",
        "ready": not blockers,
        "status": (
            "READY_FOR_FRESH_PROCESS_READ_ONLY_AUDIT"
            if not blockers
            else "BLOCKED_BEFORE_BLENDER_AUDIT"
        ),
        "resolved": resolved,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_mutation_allowed": False,
        "render_allowed": False,
        "save_allowed": False,
        "export_allowed": False,
        "activation_allowed": False,
    }


def evaluate_glb_append_preflight(
    project_root: Path,
    *,
    glb_path: Path | str,
    glb_sha256: str,
    audit_output_dir: Path | str,
    main_evidence_sha256: str,
) -> dict[str, Any]:
    """Validate the second clean-process GLB stage and its one new JSON file."""

    root = Path(project_root).resolve(strict=True)
    blockers: list[str] = []
    resolved: dict[str, Any] = {}
    try:
        glb = _project_file(root, glb_path, label="private_glb", suffix=".glb")
        candidate_dir = glb.parent.resolve(strict=True)
        candidate_id = candidate_dir.name
        if candidate_dir.parent != (root / PRIVATE_ROOT).resolve(strict=True):
            raise ProfiledKiraCandidateAuditContractError(
                "private_glb_not_in_private_candidate_directory"
            )
        if not CANDIDATE_RE.fullmatch(candidate_id):
            raise ProfiledKiraCandidateAuditContractError("candidate_id_invalid")
        if glb.name != f"{candidate_id}.private.glb":
            raise ProfiledKiraCandidateAuditContractError("private_glb_name_invalid")
        relative_output = Path(_text(audit_output_dir))
        if relative_output.is_absolute() or ".." in relative_output.parts:
            raise ProfiledKiraCandidateAuditContractError("audit_output_path_unsafe")
        if relative_output.parent.as_posix() != AUDIT_ROOT.as_posix():
            raise ProfiledKiraCandidateAuditContractError("audit_output_root_invalid")
        match = ATTEMPT_RE.fullmatch(relative_output.name)
        if match is None or match.group(1) != candidate_id:
            raise ProfiledKiraCandidateAuditContractError("audit_output_name_invalid")
        output = (root / relative_output).resolve(strict=True)
        audit_root = (root / AUDIT_ROOT).resolve(strict=True)
        try:
            audit_root.relative_to(root)
            output.relative_to(root)
        except ValueError as exc:
            raise ProfiledKiraCandidateAuditContractError(
                "audit_output_escaped_project"
            ) from exc
        if output.parent != audit_root:
            raise ProfiledKiraCandidateAuditContractError(
                "audit_output_not_direct_versioned_audit_child"
            )
        if not output.is_dir():
            raise ProfiledKiraCandidateAuditContractError("audit_output_missing")
        main = output / MAIN_EVIDENCE_NAME
        if not main.is_file():
            raise ProfiledKiraCandidateAuditContractError("main_audit_evidence_missing")
        fresh = output / GLB_EVIDENCE_NAME
        if fresh.exists():
            raise ProfiledKiraCandidateAuditContractError(
                "glb_audit_evidence_exists_refuse_overwrite"
            )
        resolved = {
            "candidate_id": candidate_id,
            "glb": {
                "path": glb.relative_to(root).as_posix(),
                "sha256": _exact_hash(glb, glb_sha256, "private_glb"),
            },
            "main_evidence": {
                "path": main.relative_to(root).as_posix(),
                "sha256": _exact_hash(
                    main,
                    main_evidence_sha256,
                    "main_audit_evidence",
                ),
            },
            "fresh_evidence_path": fresh.relative_to(root).as_posix(),
        }
    except (OSError, ProfiledKiraCandidateAuditContractError) as exc:
        blockers.append(str(exc) or type(exc).__name__)
    return {
        "schema_version": 1,
        "preflight": "profiled_kira_private_glb_fresh_import_audit_v1",
        "ready": not blockers,
        "status": (
            "READY_FOR_CLEAN_PROCESS_PRIVATE_GLB_IMPORT"
            if not blockers
            else "BLOCKED_BEFORE_PRIVATE_GLB_IMPORT"
        ),
        "resolved": resolved,
        "blockers": list(dict.fromkeys(blockers)),
        "runtime_qualification_allowed": False,
        "activation_allowed": False,
        "render_allowed": False,
        "save_allowed": False,
        "export_allowed": False,
    }


def verify_inputs_unchanged(
    project_root: Path,
    bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    blockers: list[str] = []
    after: dict[str, str] = {}
    for label, record in bindings.items():
        relative = Path(_text(record.get("path")))
        expected = _text(record.get("sha256")).lower()
        try:
            path = (root / relative).resolve(strict=True)
            path.relative_to(root)
            actual = sha256_file(path)
        except (OSError, ValueError):
            actual = ""
        after[str(label)] = actual
        if not SHA256_RE.fullmatch(expected) or actual != expected:
            blockers.append(f"input_changed_or_unavailable:{label}")
    return {
        "passed": not blockers,
        "after": after,
        "blockers": blockers,
    }


__all__ = [
    "ATTEMPT_RE",
    "AUDIT_ROOT",
    "CANDIDATE_RE",
    "GLB_EVIDENCE_NAME",
    "MAIN_EVIDENCE_NAME",
    "PRIVATE_ROOT",
    "ProfiledKiraCandidateAuditContractError",
    "evaluate_glb_append_preflight",
    "evaluate_postbuild_audit_preflight",
    "inventory_glb_container",
    "sha256_file",
    "verify_inputs_unchanged",
]
