"""Read-only, fail-closed intake for third-party 3D teaching references.

The intake deliberately does *not* copy models into an avatar body, a live
world, or a runtime asset directory.  It inventories exact bytes, inspects
GLB/ZIP/USDZ structure without extracting archives, and produces separate
reference-only routes for Avatar Builder motion study and World Builder study.

Unknown or merely detected license text is never treated as reviewed reuse
authority.  A later human-reviewed, exact-hash license artifact is required
before geometry, materials, textures, or animation may be imported/retargeted.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
CHUNK_BYTES = 4 * 1024 * 1024
MAX_GLB_JSON_BYTES = 64 * 1024 * 1024
MAX_LICENSE_TEXT_BYTES = 256 * 1024

GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A

MODEL_SUFFIXES = {".glb", ".gltf", ".fbx", ".obj", ".blend", ".usdz"}
ARCHIVE_SUFFIXES = {".zip"}
LICENSE_NAME_RE = re.compile(
    r"(^|/)(licen[cs]e|copying|copyright|rights|attribution|readme)([._ -]|$)",
    re.IGNORECASE,
)

MOTION_NAME_TERMS = {
    "animation",
    "animated",
    "walkcycle",
    "walk",
    "dance",
    "gamer",
    "floating",
    "hand",
}
HUMANOID_TOKENS = {
    "hips",
    "hip",
    "pelvis",
    "spine",
    "chest",
    "scapula",
    "neck",
    "head",
    "shoulder",
    "arm",
    "upperarm",
    "forearm",
    "elbow",
    "wrist",
    "hand",
    "thigh",
    "leg",
    "knee",
    "ankle",
    "foot",
    "toe",
}
WORLD_MOTION_TERMS = {"ocean", "water", "waves", "windy", "flag"}
RESTRICTED_TERMS = {"pistol", "beretta", "gun", "weapon", "prison", "cage", "coffin"}
BRAND_OR_IP_TERMS = {
    "star",
    "trek",
    "picard",
    "buzz",
    "delorean",
    "red",
    "bull",
    "vive",
    "miku",
}

WORLD_CATEGORY_RULES: tuple[tuple[str, set[str]], ...] = (
    ("door_and_threshold_reference", {"door", "doors"}),
    ("room_and_architecture_reference", {"room", "interior", "cinema", "castle", "tunnel", "gallery", "hangar"}),
    ("furniture_and_prop_reference", {"chair", "box", "shelf", "machine", "microwave", "replicator", "items", "cans", "toy"}),
    ("environmental_motion_reference", WORLD_MOTION_TERMS),
    ("vehicle_and_scifi_reference", {"shuttlecraft", "delorean", "module", "starbase"}),
    ("collection_and_exhibit_reference", {"coffin", "ensemble", "cages"}),
)


class IntakeError(RuntimeError):
    """Raised when an intake cannot preserve its fail-closed contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if token}


def family_id(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    if stem.startswith("sci_fi_girl_v"):
        return "sci_fi_girl_v_02_walkcycle_test"
    return stem or "unnamed_reference"


def _safe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        return False
    parts = normalized.split("/")
    if parts and parts[-1] == "":  # Normal archive directory marker.
        parts.pop()
    return bool(parts) and all(part not in {"..", "", "."} for part in parts)


def _classify_detected_license(texts: Iterable[str]) -> dict[str, Any]:
    combined = "\n".join(texts).lower()
    detected: list[str] = []
    patterns = (
        ("cc_by_nc_sa", ("cc by-nc-sa", "creative commons attribution-noncommercial-sharealike")),
        ("cc_by_nc", ("cc by-nc", "creative commons attribution-noncommercial")),
        ("cc_by_sa", ("cc by-sa", "creative commons attribution-sharealike")),
        ("cc_by", ("cc by", "creative commons attribution")),
        ("cc0", ("cc0", "public domain dedication")),
        ("all_rights_reserved", ("all rights reserved",)),
        ("sketchfab_standard", ("sketchfab standard license",)),
    )
    for label, needles in patterns:
        if any(needle in combined for needle in needles):
            detected.append(label)
    return {
        "status": "license_claim_detected_unreviewed" if detected else "unknown_rights",
        "detected_claims": detected,
        "reviewed_reuse_authority": False,
        "geometry_import_allowed": False,
        "animation_retarget_allowed": False,
        "texture_or_material_import_allowed": False,
        "reason": (
            "License-like text was detected but is not an exact-hash human-reviewed authority artifact."
            if detected
            else "No reviewed license authority was supplied with this intake."
        ),
    }


def inspect_archive(path: Path, *, kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": kind,
        "status": "unreadable_archive",
        "entry_count": 0,
        "uncompressed_bytes": 0,
        "compressed_bytes": 0,
        "extensions": {},
        "model_entries": [],
        "license_or_readme_entries": [],
        "unsafe_entry_names": [],
        "encrypted_entries": 0,
        "maximum_compression_ratio": 0.0,
        "archive_risk_flags": [],
        "license": _classify_detected_license([]),
    }
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            result["entry_count"] = len(infos)
            extension_counts: Counter[str] = Counter()
            license_texts: list[str] = []
            model_entries: list[dict[str, Any]] = []
            license_entries: list[dict[str, Any]] = []
            max_ratio = 0.0
            for info in infos:
                suffix = Path(info.filename).suffix.lower() or "[none]"
                extension_counts[suffix] += 1
                result["uncompressed_bytes"] += int(info.file_size)
                result["compressed_bytes"] += int(info.compress_size)
                if not _safe_archive_name(info.filename):
                    result["unsafe_entry_names"].append(info.filename)
                if info.flag_bits & 0x1:
                    result["encrypted_entries"] += 1
                ratio = float(info.file_size) / max(1, int(info.compress_size))
                max_ratio = max(max_ratio, ratio)
                if suffix in MODEL_SUFFIXES or suffix in ARCHIVE_SUFFIXES:
                    model_entries.append(
                        {
                            "name": info.filename,
                            "size_bytes": int(info.file_size),
                            "compressed_bytes": int(info.compress_size),
                        }
                    )
                if LICENSE_NAME_RE.search(info.filename) and not info.is_dir():
                    entry = {
                        "name": info.filename,
                        "size_bytes": int(info.file_size),
                        "sha256": None,
                        "text_read": False,
                    }
                    if not (info.flag_bits & 0x1) and info.file_size <= MAX_LICENSE_TEXT_BYTES:
                        raw = archive.read(info)
                        entry["sha256"] = hashlib.sha256(raw).hexdigest()
                        try:
                            text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            try:
                                text = raw.decode("cp1252")
                            except UnicodeDecodeError:
                                text = ""
                        if text:
                            license_texts.append(text)
                            entry["text_read"] = True
                    license_entries.append(entry)
            result["extensions"] = dict(sorted(extension_counts.items()))
            result["model_entries"] = model_entries
            result["license_or_readme_entries"] = license_entries
            result["maximum_compression_ratio"] = round(max_ratio, 3)
            if result["unsafe_entry_names"]:
                result["archive_risk_flags"].append("unsafe_path_entry")
            if result["encrypted_entries"]:
                result["archive_risk_flags"].append("encrypted_entry")
            if max_ratio > 200.0:
                result["archive_risk_flags"].append("extreme_compression_ratio")
            result["license"] = _classify_detected_license(license_texts)
            result["status"] = "valid_archive_metadata_only"
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _read_glb_json(path: Path) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
    failures: list[str] = []
    header: dict[str, Any] = {}
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            raw_header = handle.read(12)
            if len(raw_header) != 12:
                return None, ["truncated_glb_header"], header
            magic, version, declared_length = struct.unpack("<4sII", raw_header)
            header = {
                "magic": magic.decode("ascii", errors="replace"),
                "version": int(version),
                "declared_length": int(declared_length),
                "actual_length": int(size),
            }
            if magic != GLB_MAGIC:
                failures.append("invalid_glb_magic")
            if version != 2:
                failures.append("glb_version_must_be_2")
            if declared_length != size:
                failures.append("glb_declared_length_mismatch")
            chunk_header = handle.read(8)
            if len(chunk_header) != 8:
                failures.append("missing_glb_json_chunk")
                return None, failures, header
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            header["json_chunk_length"] = int(chunk_length)
            if chunk_type != GLB_JSON_CHUNK:
                failures.append("first_glb_chunk_not_json")
                return None, failures, header
            if chunk_length > MAX_GLB_JSON_BYTES:
                failures.append("glb_json_chunk_too_large")
                return None, failures, header
            raw_json = handle.read(chunk_length)
            if len(raw_json) != chunk_length:
                failures.append("truncated_glb_json_chunk")
                return None, failures, header
        document = json.loads(raw_json.decode("utf-8").rstrip(" \t\r\n\x00"))
        if not isinstance(document, dict):
            failures.append("glb_json_root_not_object")
            return None, failures, header
        return document, failures, header
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, struct.error) as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
        return None, failures, header


def inspect_glb(path: Path) -> dict[str, Any]:
    document, failures, header = _read_glb_json(path)
    result: dict[str, Any] = {
        "kind": "glb",
        "status": "invalid_glb" if failures else "valid_glb2",
        "header": header,
        "failures": failures,
    }
    if not document:
        return result

    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    meshes = document.get("meshes") if isinstance(document.get("meshes"), list) else []
    skins = document.get("skins") if isinstance(document.get("skins"), list) else []
    animations = document.get("animations") if isinstance(document.get("animations"), list) else []
    accessors = document.get("accessors") if isinstance(document.get("accessors"), list) else []

    def accessor(index: Any) -> dict[str, Any]:
        if isinstance(index, int) and 0 <= index < len(accessors) and isinstance(accessors[index], dict):
            return accessors[index]
        return {}

    mesh_node_skin: dict[int, int] = {}
    for node in nodes:
        if isinstance(node, dict) and isinstance(node.get("mesh"), int) and isinstance(node.get("skin"), int):
            mesh_node_skin[int(node["mesh"])] = int(node["skin"])

    primitive_count = 0
    skinned_primitive_count = 0
    vertex_count = 0
    index_count = 0
    morph_target_count = 0
    primitive_modes: Counter[str] = Counter()
    for mesh_index, mesh in enumerate(meshes):
        primitives = mesh.get("primitives") if isinstance(mesh, dict) and isinstance(mesh.get("primitives"), list) else []
        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            primitive_count += 1
            attributes = primitive.get("attributes") if isinstance(primitive.get("attributes"), dict) else {}
            position = accessor(attributes.get("POSITION"))
            vertex_count += int(position.get("count") or 0)
            indices = accessor(primitive.get("indices"))
            index_count += int(indices.get("count") or 0)
            targets = primitive.get("targets") if isinstance(primitive.get("targets"), list) else []
            morph_target_count += len(targets)
            primitive_modes[str(primitive.get("mode", 4))] += 1
            if (
                mesh_index in mesh_node_skin
                and "JOINTS_0" in attributes
                and "WEIGHTS_0" in attributes
            ):
                skinned_primitive_count += 1

    joint_indices: set[int] = set()
    skin_joint_counts: list[int] = []
    for skin in skins:
        joints = skin.get("joints") if isinstance(skin, dict) and isinstance(skin.get("joints"), list) else []
        clean = [value for value in joints if isinstance(value, int) and 0 <= value < len(nodes)]
        joint_indices.update(clean)
        skin_joint_counts.append(len(clean))

    node_names = [str(node.get("name") or "") for node in nodes if isinstance(node, dict)]
    joint_names = [
        str(nodes[index].get("name") or "")
        for index in sorted(joint_indices)
        if isinstance(nodes[index], dict)
    ]
    normalized_joint_tokens = set().union(*(_tokens(name) for name in joint_names)) if joint_names else set()
    humanoid_hits = sorted(
        token for token in HUMANOID_TOKENS if any(token in candidate for candidate in normalized_joint_tokens)
    )

    animation_summaries: list[dict[str, Any]] = []
    for animation_index, animation in enumerate(animations):
        if not isinstance(animation, dict):
            continue
        samplers = animation.get("samplers") if isinstance(animation.get("samplers"), list) else []
        channels = animation.get("channels") if isinstance(animation.get("channels"), list) else []
        duration = 0.0
        for sampler in samplers:
            if not isinstance(sampler, dict):
                continue
            timing = accessor(sampler.get("input"))
            minimum = timing.get("min") if isinstance(timing.get("min"), list) else []
            maximum = timing.get("max") if isinstance(timing.get("max"), list) else []
            if minimum and maximum:
                try:
                    duration = max(duration, float(maximum[0]) - float(minimum[0]))
                except (TypeError, ValueError):
                    pass
        paths: Counter[str] = Counter()
        targets: list[str] = []
        for channel in channels:
            target = channel.get("target") if isinstance(channel, dict) and isinstance(channel.get("target"), dict) else {}
            path_name = str(target.get("path") or "unknown")
            paths[path_name] += 1
            node_index = target.get("node")
            if isinstance(node_index, int) and 0 <= node_index < len(nodes) and isinstance(nodes[node_index], dict):
                targets.append(str(nodes[node_index].get("name") or f"node_{node_index}"))
        animation_summaries.append(
            {
                "index": animation_index,
                "name": str(animation.get("name") or f"animation_{animation_index}"),
                "duration_seconds": round(duration, 6),
                "channel_count": len(channels),
                "sampler_count": len(samplers),
                "target_paths": dict(sorted(paths.items())),
                "target_nodes_sample": sorted(set(targets))[:32],
            }
        )

    asset = document.get("asset") if isinstance(document.get("asset"), dict) else {}
    result.update(
        {
            "asset_version": asset.get("version"),
            "generator": asset.get("generator"),
            "extensions_used": sorted(str(value) for value in (document.get("extensionsUsed") or [])),
            "extensions_required": sorted(str(value) for value in (document.get("extensionsRequired") or [])),
            "counts": {
                "scenes": len(document.get("scenes") or []),
                "nodes": len(nodes),
                "meshes": len(meshes),
                "primitives": primitive_count,
                "skinned_primitives": skinned_primitive_count,
                "materials": len(document.get("materials") or []),
                "textures": len(document.get("textures") or []),
                "images": len(document.get("images") or []),
                "skins": len(skins),
                "joints_unique": len(joint_indices),
                "animations": len(animations),
                "morph_targets": morph_target_count,
                "vertices_sum": vertex_count,
                "indices_sum": index_count,
                "cameras": len(document.get("cameras") or []),
            },
            "skin_joint_counts": skin_joint_counts,
            "humanoid_joint_role_hits": humanoid_hits,
            "likely_humanoid_rig": len(humanoid_hits) >= 5,
            "node_names_sample": node_names[:64],
            "joint_names_sample": joint_names[:96],
            "primitive_modes": dict(sorted(primitive_modes.items())),
            "animations": animation_summaries,
        }
    )
    return result


def inspect_file_structure(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".glb":
        return inspect_glb(path)
    if suffix == ".usdz":
        return inspect_archive(path, kind="usdz")
    if suffix == ".zip":
        return inspect_archive(path, kind="zip")
    if suffix in MODEL_SUFFIXES:
        return {
            "kind": suffix.lstrip("."),
            "status": "recorded_not_decoded",
            "reason": "This format requires a separate bounded parser or Blender review.",
        }
    return {"kind": "other", "status": "recorded_not_decoded"}


def classify_teaching_route(path: Path, structure: dict[str, Any]) -> dict[str, Any]:
    name_tokens = _tokens(path.stem)
    lower_name = path.stem.lower()
    counts = structure.get("counts") if isinstance(structure.get("counts"), dict) else {}
    animation_count = int(counts.get("animations") or 0)
    likely_humanoid = bool(structure.get("likely_humanoid_rig"))
    restricted = bool(name_tokens & RESTRICTED_TERMS)
    branded_or_ip = bool(name_tokens & BRAND_OR_IP_TERMS)

    lane = "unclassified_reference"
    teaching_uses: list[str] = []
    limitations: list[str] = []
    explicit_human_motion = bool(
        name_tokens & {"walkcycle", "walk", "dance", "gamer", "floating", "astronaut", "hand"}
        and animation_count
    )
    explicit_character_structure = bool(
        name_tokens & {"picard", "captain", "captains", "male", "female", "girl"}
        and (int(counts.get("skins") or 0) or int(counts.get("meshes") or 0))
    )

    if restricted:
        lane = "restricted_reference"
        teaching_uses = ["catalog_only", "manual_context_review"]
        limitations.append("not_part_of_daily_human_movement_baseline")
    elif animation_count and likely_humanoid:
        lane = "avatar_motion_reference"
        teaching_uses = ["motion_timing_study", "joint_path_study", "contact_hypothesis"]
    elif explicit_human_motion:
        lane = "avatar_motion_reference"
        teaching_uses = ["motion_timing_study", "pose_hypothesis", "visual_review_required"]
        if not likely_humanoid:
            limitations.append("not_confirmed_as_a_complete_humanoid_skin")
    elif name_tokens & MOTION_NAME_TERMS and likely_humanoid:
        lane = "avatar_motion_reference"
        teaching_uses = ["rig_structure_study", "pose_and_motion_hypothesis"]
    elif likely_humanoid or explicit_character_structure:
        lane = "avatar_structure_reference"
        teaching_uses = ["rig_hierarchy_study", "proportion_and_deformation_hypothesis"]
    elif name_tokens & WORLD_MOTION_TERMS or animation_count:
        lane = "world_builder_motion_reference"
        teaching_uses = ["environment_animation_timing_study", "shader_or_deformation_hypothesis"]
    else:
        for category, terms in WORLD_CATEGORY_RULES:
            if name_tokens & terms:
                lane = "world_builder_reference"
                teaching_uses = [category, "layout_or_interaction_hypothesis"]
                break

    if lane == "unclassified_reference" and path.suffix.lower() in MODEL_SUFFIXES | ARCHIVE_SUFFIXES:
        lane = "world_builder_reference"
        teaching_uses = ["manual_structure_study"]

    if "walkcycle" in lower_name or "walk_cycle" in lower_name:
        teaching_uses.extend(["walk_cycle", "arm_swing", "foot_contact", "cadence"])
    if "gamer" in lower_name:
        teaching_uses.extend(["seated_posture", "hand_to_keyboard_or_controller_reach"])
    if "hand" in lower_name:
        teaching_uses.extend(["hand_pose", "finger_articulation"])
    if "dance" in lower_name:
        teaching_uses.extend(["weight_shift", "whole_body_coordination"])
        limitations.append("stylized_motion_not_neutral_daily_baseline")
    if "floating" in lower_name or "astronaut" in lower_name:
        teaching_uses.extend(["zero_gravity_pose", "slow_body_drift"])
        limitations.append("not_grounded_locomotion")
    if branded_or_ip:
        limitations.append("brand_or_fictional_ip_reference_private_study_only")

    return {
        "lane": lane,
        "teaching_uses": sorted(set(teaching_uses)),
        "limitations": sorted(set(limitations)),
        "reference_only": True,
        "model_weight_training_authorized": False,
        "copy_into_builder_library_allowed": False,
        "copy_as_avatar_body_allowed": False,
        "runtime_world_import_allowed": False,
        "animation_retarget_allowed": False,
        "activation_allowed": False,
        "public_export_allowed": False,
    }


def collect_catalog_hashes(catalog_paths: Iterable[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = defaultdict(list)

    def walk(value: Any, label: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"sha256", "source_sha256", "asset_sha256"} and isinstance(child, str):
                    digest = child.lower()
                    if re.fullmatch(r"[0-9a-f]{64}", digest):
                        found[digest].append(label)
                else:
                    walk(child, label)
        elif isinstance(value, list):
            for child in value:
                walk(child, label)

    for path in catalog_paths:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        walk(payload, path.as_posix())
    return {key: sorted(set(value)) for key, value in found.items()}


@dataclass(frozen=True)
class IntakeOutputs:
    root: Path
    manifest: Path
    avatar_route: Path
    movement_route: Path
    world_route: Path
    blocked_route: Path


@dataclass(frozen=True)
class ConsumerRouteLinks:
    avatar: Path
    movement: Path
    world: Path


def default_catalog_paths(project_root: Path) -> list[Path]:
    paths = [project_root / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json"]
    paths.extend(sorted((project_root / "Avatar" / "avatar_builder" / "reference_models").glob("**/*.json")))
    return paths


def build_intake_manifest(
    source_root: Path,
    *,
    project_root: Path,
    catalog_paths: Iterable[Path] | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    project_root = project_root.resolve()
    if not source_root.is_dir():
        raise IntakeError(f"source root is not a directory: {source_root}")
    if source_root.is_symlink():
        raise IntakeError("source root symlink is not allowed")

    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    catalog_hashes = collect_catalog_hashes(catalog_paths or default_catalog_paths(project_root))
    records: list[dict[str, Any]] = []
    hashes: dict[str, list[str]] = defaultdict(list)
    family_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_bytes = 0
    latest_mtime_ns = 0
    for path in files:
        if path.is_symlink():
            raise IntakeError(f"source file symlink is not allowed: {path}")
        stat = path.stat()
        total_bytes += int(stat.st_size)
        latest_mtime_ns = max(latest_mtime_ns, int(stat.st_mtime_ns))
        digest = sha256_file(path)
        relative = path.relative_to(source_root).as_posix()
        structure = inspect_file_structure(path)
        route = classify_teaching_route(path, structure)
        license_record = structure.get("license") if isinstance(structure.get("license"), dict) else _classify_detected_license([])
        record = {
            "relative_path": relative,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "sha256": digest,
            "family_id": family_id(path),
            "structure": structure,
            "license": license_record,
            "route": route,
            "existing_catalog_matches": catalog_hashes.get(digest, []),
        }
        records.append(record)
        hashes[digest].append(relative)
        family_records[record["family_id"]].append(record)

    duplicate_sets = [
        {"sha256": digest, "paths": paths}
        for digest, paths in sorted(hashes.items())
        if len(paths) > 1
    ]
    families: list[dict[str, Any]] = []
    for identifier, members in sorted(family_records.items()):
        lanes = Counter(str(member["route"]["lane"]) for member in members)
        glb_members = [member for member in members if member["extension"] == ".glb"]

        def primary_score(member: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
            structure = member["structure"]
            counts = structure.get("counts") if isinstance(structure.get("counts"), dict) else {}
            return (
                1 if structure.get("status") == "valid_glb2" else 0,
                int(counts.get("animations") or 0),
                int(counts.get("joints_unique") or 0),
                int(counts.get("vertices_sum") or 0),
                -int(member["size_bytes"]),
                member["relative_path"],
            )

        primary = max(glb_members, key=primary_score) if glb_members else None
        families.append(
            {
                "family_id": identifier,
                "file_count": len(members),
                "lanes": dict(sorted(lanes.items())),
                "primary_glb_sha256": primary["sha256"] if primary else None,
                "primary_glb_relative_path": primary["relative_path"] if primary else None,
                "member_sha256": sorted({str(member["sha256"]) for member in members}),
                "license_gate": "blocked_pending_exact_reviewed_license",
                "reference_only": True,
                "activation_allowed": False,
            }
        )

    inventory_basis = [
        {"relative_path": record["relative_path"], "size_bytes": record["size_bytes"], "sha256": record["sha256"]}
        for record in records
    ]
    inventory_sha = hashlib.sha256(canonical_json_bytes(inventory_basis)).hexdigest()
    lane_counts = Counter(str(record["route"]["lane"]) for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_type": "reference_model_teaching_intake",
        "source_root": str(source_root),
        "source_folder_name": source_root.name,
        "source_latest_mtime_ns": latest_mtime_ns,
        "inventory_sha256": inventory_sha,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "unique_file_hashes": len(hashes),
        "duplicate_set_count": len(duplicate_sets),
        "family_count": len(families),
        "lane_counts": dict(sorted(lane_counts.items())),
        "authority": {
            "purpose": "private_reference_and_teaching_evidence_only",
            "original_files_modified": False,
            "files_copied": False,
            "model_weight_training_authorized": False,
            "avatar_body_creation_authorized": False,
            "avatar_or_person_activation_authorized": False,
            "world_runtime_import_authorized": False,
            "animation_retarget_authorized": False,
            "public_export_authorized": False,
            "license_rule": "Every exact source hash needs a separately reviewed reuse license before import or retargeting.",
            "avatar_rule": "A reference model may guide measurement, rig study, or motion hypotheses; its mesh is never a candidate body.",
            "world_rule": "Unknown-rights geometry is context-only and cannot satisfy the World Builder geometry evidence gate.",
            "motion_rule": "Animation can inform a draft motion lesson only; retargeting and promotion require license, source-rig mapping, contact proof, and owner review.",
        },
        "duplicates": duplicate_sets,
        "families": families,
        "files": records,
    }


def _route_payload(manifest: dict[str, Any], lanes: set[str], route_type: str) -> dict[str, Any]:
    selected = [
        {
            "relative_path": record["relative_path"],
            "sha256": record["sha256"],
            "family_id": record["family_id"],
            "route": record["route"],
            "structure": record["structure"],
            "license": record["license"],
        }
        for record in manifest["files"]
        if str(record["route"]["lane"]) in lanes
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "route_type": route_type,
        "source_inventory_sha256": manifest["inventory_sha256"],
        "source_folder_name": manifest["source_folder_name"],
        "entry_count": len(selected),
        "entries": selected,
        "teaching_evidence_only": True,
        "files_copied": False,
        "runtime_activation_allowed": False,
        "automatic_import_allowed": False,
        "automatic_retarget_allowed": False,
        "next_gate": "exact_hash_license_review_then_format_specific_visual_or_motion_review",
    }


def build_routes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    avatar = _route_payload(
        manifest,
        {"avatar_motion_reference", "avatar_structure_reference"},
        "avatar_builder_reference_only",
    )
    movement_entries = [
        entry for entry in avatar["entries"] if entry["route"]["lane"] == "avatar_motion_reference"
    ]
    movement = {
        **{key: value for key, value in avatar.items() if key != "entries"},
        "route_type": "movement_library_untrusted_draft_sources",
        "entry_count": len(movement_entries),
        "entries": movement_entries,
        "promotion_rule": (
            "No source animation is promoted or retargeted automatically. A licensed exact-hash source must be mapped "
            "to the foundation rig, then visibly pass body/contact/route/action-truth review as an untrusted draft."
        ),
    }
    world = _route_payload(
        manifest,
        {"world_builder_reference", "world_builder_motion_reference"},
        "world_builder_context_reference_only",
    )
    blocked = _route_payload(
        manifest,
        {"restricted_reference", "unclassified_reference"},
        "blocked_or_manual_review_reference",
    )
    return {"avatar": avatar, "movement": movement, "world": world, "blocked": blocked}


def _write_exact(path: Path, payload: dict[str, Any]) -> None:
    content = canonical_json_bytes(payload)
    if path.exists():
        if path.read_bytes() != content:
            raise IntakeError(f"immutable intake output differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def write_intake_outputs(manifest: dict[str, Any], *, project_root: Path) -> IntakeOutputs:
    manifest_content_sha256 = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    root = (
        project_root.resolve()
        / "Data"
        / "reference_model_intake"
        / str(manifest["source_folder_name"]).lower()
        / f"{str(manifest['inventory_sha256'])[:16]}_{manifest_content_sha256[:12]}"
    )
    routes = build_routes(manifest)
    outputs = IntakeOutputs(
        root=root,
        manifest=root / "manifest.json",
        avatar_route=root / "avatar_builder_reference_route.json",
        movement_route=root / "movement_reference_route.json",
        world_route=root / "world_builder_reference_route.json",
        blocked_route=root / "blocked_or_manual_review_route.json",
    )
    _write_exact(outputs.manifest, manifest)
    _write_exact(outputs.avatar_route, routes["avatar"])
    _write_exact(outputs.movement_route, routes["movement"])
    _write_exact(outputs.world_route, routes["world"])
    _write_exact(outputs.blocked_route, routes["blocked"])
    return outputs


def _project_relative(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def write_consumer_route_links(
    outputs: IntakeOutputs,
    manifest: dict[str, Any],
    *,
    project_root: Path,
) -> ConsumerRouteLinks:
    """Publish immutable pointers in each builder's reference-intake area."""

    project_root = project_root.resolve()
    route_id = outputs.root.name
    links = ConsumerRouteLinks(
        avatar=project_root / "Avatar" / "avatar_builder" / "reference_intake" / str(manifest["source_folder_name"]).lower() / route_id / "route_link.json",
        movement=project_root / "Avatar" / "movement_library" / "reference_intake" / str(manifest["source_folder_name"]).lower() / route_id / "route_link.json",
        world=project_root / "Data" / "world_builder" / "reference_intake" / str(manifest["source_folder_name"]).lower() / route_id / "route_link.json",
    )
    targets = (
        (links.avatar, outputs.avatar_route, "avatar_builder_reference_only"),
        (links.movement, outputs.movement_route, "movement_library_untrusted_draft_sources"),
        (links.world, outputs.world_route, "world_builder_context_reference_only"),
    )
    for link_path, route_path, route_type in targets:
        _write_exact(
            link_path,
            {
                "schema_version": SCHEMA_VERSION,
                "link_type": "immutable_reference_teaching_route",
                "route_type": route_type,
                "source_inventory_sha256": manifest["inventory_sha256"],
                "source_manifest": _project_relative(outputs.manifest, project_root),
                "source_manifest_sha256": sha256_file(outputs.manifest),
                "route_manifest": _project_relative(route_path, project_root),
                "route_manifest_sha256": sha256_file(route_path),
                "reference_only": True,
                "files_copied": False,
                "automatic_import_allowed": False,
                "runtime_activation_allowed": False,
            },
        )
    return links
