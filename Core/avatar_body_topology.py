"""Privacy-safe, non-rendering evidence for staged avatar body candidates.

The inspector reads only the structural JSON stored in a binary glTF (GLB)
container.  It deliberately does not render, extract textures, disclose raw
node/material names, or claim that a filename proves adult anatomy.  Geometry,
rig stability, anatomical completeness, and subject-specific authorship are
separate claims with separate evidence gates.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Mapping


GLB_MAGIC = b"glTF"
GLB_VERSION = 2
JSON_CHUNK_TYPE = 0x4E4F534A
MAX_JSON_CHUNK_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

CORE_HUMANOID_ROLES = (
    "pelvis",
    "spine_or_chest",
    "neck",
    "head",
    "left_upper_arm",
    "left_lower_arm",
    "left_hand",
    "right_upper_arm",
    "right_lower_arm",
    "right_hand",
    "left_upper_leg",
    "left_lower_leg",
    "left_foot",
    "right_upper_leg",
    "right_lower_leg",
    "right_foot",
)

RIG_STABILITY_TESTS = (
    "weight_deformation",
    "shoulder_elbow_wrist",
    "hand_and_finger",
    "hip_knee_ankle",
    "seated_pose",
    "bed_pose",
    "locomotion",
)


class GlbInspectionError(ValueError):
    """Raised internally for a malformed or unsupported GLB container."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).lower())


def _valid_sha256(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_glb_document(path: Path) -> tuple[dict[str, Any], int, int]:
    """Read and validate the GLB envelope without loading its binary buffers."""
    actual_length = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise GlbInspectionError("truncated_glb_header")
        magic, version, declared_length = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC:
            raise GlbInspectionError("invalid_glb_magic")
        if version != GLB_VERSION:
            raise GlbInspectionError("unsupported_glb_version")
        if declared_length != actual_length:
            raise GlbInspectionError("declared_length_does_not_match_file")

        json_bytes: bytes | None = None
        cursor = 12
        chunk_index = 0
        while cursor < declared_length:
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                raise GlbInspectionError("truncated_chunk_header")
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            cursor += 8
            if chunk_length % 4:
                raise GlbInspectionError("chunk_length_is_not_four_byte_aligned")
            if chunk_index == 0 and chunk_type != JSON_CHUNK_TYPE:
                raise GlbInspectionError("first_chunk_is_not_json")
            if chunk_length > declared_length - cursor:
                raise GlbInspectionError("chunk_exceeds_declared_length")
            if chunk_type == JSON_CHUNK_TYPE and json_bytes is None:
                if chunk_length > MAX_JSON_CHUNK_BYTES:
                    raise GlbInspectionError("json_chunk_exceeds_safe_limit")
                json_bytes = stream.read(chunk_length)
                if len(json_bytes) != chunk_length:
                    raise GlbInspectionError("truncated_json_chunk")
            else:
                stream.seek(chunk_length, 1)
            cursor += chunk_length
            chunk_index += 1
        if cursor != declared_length:
            raise GlbInspectionError("invalid_chunk_alignment")
        if json_bytes is None:
            raise GlbInspectionError("missing_json_chunk")

    try:
        document = json.loads(json_bytes.rstrip(b" \t\r\n\x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GlbInspectionError("invalid_json_chunk") from exc
    if not isinstance(document, dict):
        raise GlbInspectionError("json_root_is_not_an_object")
    asset = document.get("asset")
    if not isinstance(asset, dict) or _text(asset.get("version")) != "2.0":
        raise GlbInspectionError("json_asset_version_is_not_2_0")
    return document, version, declared_length


def _list(document: Mapping[str, Any], key: str) -> list[Any]:
    value = document.get(key, [])
    return value if isinstance(value, list) else []


def _accessor_count(accessors: list[Any], index: Any) -> int | None:
    if not isinstance(index, int) or isinstance(index, bool):
        return None
    if index < 0 or index >= len(accessors):
        return None
    accessor = accessors[index]
    if not isinstance(accessor, dict):
        return None
    count = accessor.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return None
    return count


def _accessor_layout_valid(
    accessors: list[Any],
    index: Any,
    *,
    required_type: str,
    allowed_component_types: set[int] | None = None,
    integer_components_require_normalized: bool = False,
) -> bool:
    if not isinstance(index, int) or isinstance(index, bool):
        return False
    if index < 0 or index >= len(accessors):
        return False
    accessor = accessors[index]
    if not isinstance(accessor, dict) or accessor.get("type") != required_type:
        return False
    component_type = accessor.get("componentType")
    if allowed_component_types is not None and component_type not in allowed_component_types:
        return False
    if integer_components_require_normalized and component_type in {5121, 5123}:
        return accessor.get("normalized") is True
    return True


def _side_for_name(name: str) -> str:
    normalized = _normalized(name)
    compact = _compact(name)
    tokens = normalized.split("_") if normalized else []
    if "left" in compact or "lft" in compact or "l" in tokens:
        return "left"
    if "right" in compact or "rgt" in compact or "r" in tokens:
        return "right"

    sided_stems = (
        "upperarm",
        "shldr",
        "shoulder",
        "lowerarm",
        "forearm",
        "hand",
        "wrist",
        "upperleg",
        "lowerleg",
        "thigh",
        "shin",
        "calf",
        "foot",
        "ankle",
        "thumb",
        "index",
        "middle",
        "ring",
        "pinky",
        "little",
    )
    for stem in sided_stems:
        if compact.startswith("l" + stem) or compact.endswith(stem + "l"):
            return "left"
        if compact.startswith("r" + stem) or compact.endswith(stem + "r"):
            return "right"
    return ""


def _bone_roles(name: str) -> set[str]:
    """Map a raw joint name to non-sensitive canonical roles."""
    # Exporters commonly append duplicate-resolving digits (for example,
    # ``mixamorig:LeftArm_09``).  Those digits are not part of the anatomical
    # role and must not make an otherwise standard Mixamo chain disappear.
    compact = re.sub(r"\d+$", "", _compact(name))
    side = _side_for_name(name)
    roles: set[str] = set()
    if not side and any(stem in compact for stem in ("pelvis", "hips", "hipbone")):
        roles.add("pelvis")
    if "spine" in compact or "abdomen" in compact or "waist" in compact:
        roles.add("spine")
    if "chest" in compact or "ribcage" in compact or "thorax" in compact:
        roles.add("chest")
    if "neck" in compact:
        roles.add("neck")
    if "head" in compact or "skull" in compact:
        roles.add("head")
    if not side:
        return roles

    if any(
        stem in compact
        for stem in ("upperarm", "humerus", "shldrbend", "shldrtwist")
    ) or compact.endswith(
        ("leftarm", "rightarm", "larm", "rarm")
    ):
        roles.add(f"{side}_upper_arm")
    if any(stem in compact for stem in ("lowerarm", "forearm", "radius", "ulna")):
        roles.add(f"{side}_lower_arm")
    if any(stem in compact for stem in ("hand", "wrist")):
        roles.add(f"{side}_hand")
    if any(stem in compact for stem in ("upperleg", "upleg", "thigh", "femur")):
        roles.add(f"{side}_upper_leg")
    if any(stem in compact for stem in ("lowerleg", "shin", "calf", "tibia")):
        roles.add(f"{side}_lower_leg")
    # Mixamo-style LeftLeg/RightLeg is the lower leg, while LeftUpLeg is caught above.
    if compact.endswith(("leftleg", "rightleg", "lleg", "rleg")):
        roles.add(f"{side}_lower_leg")
    if any(stem in compact for stem in ("foot", "ankle")):
        roles.add(f"{side}_foot")
    return roles


def _finger_role(name: str) -> str:
    compact = _compact(name)
    side = _side_for_name(name)
    if not side:
        return ""
    for digit, stems in (
        ("thumb", ("thumb",)),
        ("index", ("index",)),
        ("middle", ("middle", "mid")),
        ("ring", ("ring",)),
        ("little", ("pinky", "little")),
    ):
        if any(stem in compact for stem in stems):
            return f"{side}_{digit}"
    return ""


def _attestation_base_valid(attestation: Mapping[str, Any] | None, digest: str) -> bool:
    if not isinstance(attestation, Mapping):
        return False
    status = _normalized(attestation.get("review_status"))
    return bool(
        _valid_sha256(attestation.get("artifact_sha256"))
        and _text(attestation.get("artifact_sha256")).lower() == digest
        and attestation.get("exact_artifact_hash_verified") is True
        and status in {"approved", "pass", "passed"}
        and _text(attestation.get("reviewed_by"))
        and _text(attestation.get("reviewed_at"))
    )


def _anatomy_attestation_valid(
    attestation: Mapping[str, Any] | None,
    digest: str,
) -> bool:
    return bool(
        _attestation_base_valid(attestation, digest)
        and attestation.get("confirmed_adult_subject") is True
        and attestation.get("complete_adult_topology_review_passed") is True
        and attestation.get("continuous_body_surface_review_passed") is True
        and attestation.get("private_review_completed") is True
        and attestation.get("intimate_review_render_retained") is False
    )


def _rig_attestation_valid(
    attestation: Mapping[str, Any] | None,
    digest: str,
) -> tuple[bool, list[str]]:
    results = attestation.get("test_results") if isinstance(attestation, Mapping) else None
    missing = [
        name
        for name in RIG_STABILITY_TESTS
        if not isinstance(results, Mapping) or _normalized(results.get(name)) != "passed"
    ]
    return _attestation_base_valid(attestation, digest) and not missing, missing


def inspect_glb_topology(
    path: str | Path,
    *,
    artifact_id: str = "private_candidate",
    anatomy_attestation: Mapping[str, Any] | None = None,
    rig_attestation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe structural report for one GLB artifact.

    ``path`` is intentionally never returned.  Raw node, mesh, material, and
    texture names are used only transiently to recognize canonical skeleton
    roles and are omitted from the report.
    """
    source = Path(path)
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": _text(artifact_id) or "private_candidate",
        "audit_mode": "non_rendering_glb_structure_only",
        "privacy": {
            "source_path_disclosed": False,
            "raw_node_or_material_names_disclosed": False,
            "textures_extracted": False,
            "preview_created": False,
        },
        "valid_glb": False,
        "inspection_error": "",
        "sha256": "",
        "size_bytes": 0,
        "topology_metrics": {},
        "canonical_rig_evidence": {},
        "humanoid_rig_structurally_ready": False,
        "stable_working_rig_proven": False,
        "anatomical_completeness_proven": False,
        "runtime_activation_allowed": False,
    }
    try:
        report["size_bytes"] = source.stat().st_size
        digest = _sha256_file(source)
        report["sha256"] = digest
        document, version, declared_length = _read_glb_document(source)
    except (OSError, GlbInspectionError) as exc:
        report["inspection_error"] = (
            str(exc) if isinstance(exc, GlbInspectionError) else "source_unavailable"
        )
        report["truth_note"] = "No topology or rig claim is allowed for an invalid/unavailable GLB."
        return report

    meshes = _list(document, "meshes")
    skins = _list(document, "skins")
    nodes = _list(document, "nodes")
    accessors = _list(document, "accessors")
    animations = _list(document, "animations")
    materials = _list(document, "materials")

    joint_indices: set[int] = set()
    joints_per_skin: list[int] = []
    invalid_joint_references = 0
    for skin in skins:
        joints = skin.get("joints", []) if isinstance(skin, dict) else []
        if not isinstance(joints, list):
            joints = []
        valid_for_skin = 0
        for index in joints:
            if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(nodes):
                joint_indices.add(index)
                valid_for_skin += 1
            else:
                invalid_joint_references += 1
        joints_per_skin.append(valid_for_skin)

    skinned_mesh_indices: set[int] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        mesh_index = node.get("mesh")
        skin_index = node.get("skin")
        if (
            isinstance(mesh_index, int)
            and not isinstance(mesh_index, bool)
            and 0 <= mesh_index < len(meshes)
            and isinstance(skin_index, int)
            and not isinstance(skin_index, bool)
            and 0 <= skin_index < len(skins)
        ):
            skinned_mesh_indices.add(mesh_index)

    primitive_count = 0
    position_vertex_count = 0
    triangle_count = 0
    morph_target_count = 0
    weighted_primitive_count = 0
    weighted_skinned_primitive_count = 0
    unweighted_skinned_primitive_count = 0
    invalid_accessor_references = 0
    invalid_attribute_layouts = 0
    triangle_element_remainders = 0
    for mesh_index, mesh in enumerate(meshes):
        primitives = mesh.get("primitives", []) if isinstance(mesh, dict) else []
        if not isinstance(primitives, list):
            continue
        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            primitive_count += 1
            attributes = primitive.get("attributes", {})
            if not isinstance(attributes, dict):
                attributes = {}
            position_index = attributes.get("POSITION")
            position_count = _accessor_count(accessors, position_index)
            if position_count is None:
                invalid_accessor_references += 1
                position_count = 0
            elif not _accessor_layout_valid(
                accessors,
                position_index,
                required_type="VEC3",
                allowed_component_types={5120, 5121, 5122, 5123, 5125, 5126},
            ):
                invalid_attribute_layouts += 1
            position_vertex_count += position_count
            mode = primitive.get("mode", 4)
            if mode == 4:
                indices = primitive.get("indices")
                element_count = (
                    _accessor_count(accessors, indices) if indices is not None else position_count
                )
                if element_count is None:
                    invalid_accessor_references += 1
                else:
                    triangle_count += element_count // 3
                    if element_count % 3:
                        triangle_element_remainders += 1
            targets = primitive.get("targets", [])
            if isinstance(targets, list):
                morph_target_count += len(targets)
            has_weight_keys = all(
                key in attributes for key in ("POSITION", "JOINTS_0", "WEIGHTS_0")
            )
            joint_count = (
                _accessor_count(accessors, attributes.get("JOINTS_0"))
                if "JOINTS_0" in attributes
                else None
            )
            weight_count = (
                _accessor_count(accessors, attributes.get("WEIGHTS_0"))
                if "WEIGHTS_0" in attributes
                else None
            )
            if "JOINTS_0" in attributes and joint_count is None:
                invalid_accessor_references += 1
            if "WEIGHTS_0" in attributes and weight_count is None:
                invalid_accessor_references += 1
            weight_layout_valid = bool(
                has_weight_keys
                and position_count > 0
                and joint_count == position_count
                and weight_count == position_count
                and _accessor_layout_valid(
                    accessors,
                    attributes.get("JOINTS_0"),
                    required_type="VEC4",
                    allowed_component_types={5121, 5123},
                )
                and _accessor_layout_valid(
                    accessors,
                    attributes.get("WEIGHTS_0"),
                    required_type="VEC4",
                    allowed_component_types={5121, 5123, 5126},
                    integer_components_require_normalized=True,
                )
            )
            if has_weight_keys and not weight_layout_valid:
                invalid_attribute_layouts += 1
            if weight_layout_valid:
                weighted_primitive_count += 1
                if mesh_index in skinned_mesh_indices:
                    weighted_skinned_primitive_count += 1
            elif mesh_index in skinned_mesh_indices:
                unweighted_skinned_primitive_count += 1

    canonical_roles: set[str] = set()
    finger_roles: set[str] = set()
    for index in joint_indices:
        node = nodes[index]
        if not isinstance(node, dict):
            continue
        name = _text(node.get("name"))
        canonical_roles.update(_bone_roles(name))
        finger_role = _finger_role(name)
        if finger_role:
            finger_roles.add(finger_role)
    core_covered = set(canonical_roles)
    if "spine" in canonical_roles or "chest" in canonical_roles:
        core_covered.add("spine_or_chest")
    missing_core_roles = [role for role in CORE_HUMANOID_ROLES if role not in core_covered]

    structural_ready = bool(
        meshes
        and skins
        and max(joints_per_skin, default=0) >= 15
        and weighted_skinned_primitive_count >= 1
        and unweighted_skinned_primitive_count == 0
        and not missing_core_roles
        and invalid_joint_references == 0
        and invalid_accessor_references == 0
        and invalid_attribute_layouts == 0
        and triangle_element_remainders == 0
    )
    rig_proven, missing_stability_tests = _rig_attestation_valid(rig_attestation, digest)
    rig_proven = bool(structural_ready and rig_proven)
    anatomy_proven = bool(
        primitive_count > 0 and _anatomy_attestation_valid(anatomy_attestation, digest)
    )

    report.update(
        {
            "valid_glb": True,
            "glb_version": version,
            "declared_length_bytes": declared_length,
            "topology_metrics": {
                "mesh_count": len(meshes),
                "primitive_count": primitive_count,
                "referenced_position_vertex_count": position_vertex_count,
                "indexed_or_sequential_triangle_count": triangle_count,
                "morph_target_count": morph_target_count,
                "skin_count": len(skins),
                "unique_joint_count": len(joint_indices),
                "maximum_joints_in_one_skin": max(joints_per_skin, default=0),
                "weighted_primitive_count": weighted_primitive_count,
                "weighted_skinned_primitive_count": weighted_skinned_primitive_count,
                "unweighted_skinned_primitive_count": unweighted_skinned_primitive_count,
                "animation_count": len(animations),
                "node_count": len(nodes),
                "material_count": len(materials),
                "invalid_joint_reference_count": invalid_joint_references,
                "invalid_accessor_reference_count": invalid_accessor_references,
                "invalid_attribute_layout_count": invalid_attribute_layouts,
                "triangle_element_remainder_count": triangle_element_remainders,
            },
            "canonical_rig_evidence": {
                "recognized_roles": sorted(canonical_roles),
                "missing_core_roles": missing_core_roles,
                "finger_chain_roles": sorted(finger_roles),
                "raw_names_disclosed": False,
            },
            "humanoid_rig_structurally_ready": structural_ready,
            "stable_working_rig_proven": rig_proven,
            "rig_stability_attestation": {
                "exact_sha256_bound": _attestation_base_valid(rig_attestation, digest),
                "missing_or_failed_tests": missing_stability_tests,
            },
            "anatomical_completeness_proven": anatomy_proven,
            "adult_anatomy_attestation": {
                "exact_sha256_bound": _attestation_base_valid(anatomy_attestation, digest),
                "private_review_gate_passed": anatomy_proven,
            },
            "truth_note": (
                "Static GLB structure can show meshes, weighted skinning, joints, and canonical "
                "rig roles. It cannot by itself prove likeness, deformation quality, anatomical "
                "completeness, stable motion, or permission to use the asset as a candidate body."
            ),
        }
    )
    return report


def evaluate_body_candidate_readiness(
    topology_report: Mapping[str, Any],
    *,
    subject_id: str,
    subject_maturity: str,
    lineage: Mapping[str, Any],
    request_complete_adult_anatomy: bool = False,
) -> dict[str, Any]:
    """Fail closed before a body artifact can be called a staged subject candidate."""
    failures: list[str] = []
    warnings: list[str] = []
    digest = _text(topology_report.get("sha256")).lower()
    lineage_digest = _text(lineage.get("candidate_sha256")).lower()
    maturity = _normalized(subject_maturity)

    if not topology_report.get("valid_glb"):
        failures.append("candidate_is_not_a_valid_glb")
    if not topology_report.get("humanoid_rig_structurally_ready"):
        failures.append("candidate_humanoid_rig_structure_not_ready")
    if not topology_report.get("stable_working_rig_proven"):
        failures.append("candidate_rig_motion_stability_not_hash_attested")
    if not _valid_sha256(digest) or digest != lineage_digest:
        failures.append("candidate_lineage_not_bound_to_exact_artifact_sha256")
    if _normalized(lineage.get("subject_id")) != _normalized(subject_id):
        failures.append("candidate_lineage_subject_mismatch")
    if lineage.get("lineage_reviewed") is not True:
        failures.append("candidate_lineage_not_reviewed")
    if lineage.get("new_subject_specific_mesh_authored") is not True:
        failures.append("subject_specific_mesh_authorship_not_proven")
    if lineage.get("reference_mesh_copied_into_candidate") is not False:
        failures.append("reference_mesh_copying_not_explicitly_excluded")
    if lineage.get("selected_directly_from_reference_library") is not False:
        failures.append("reference_library_asset_cannot_be_selected_as_candidate_body")
    if lineage.get("body_and_clothes_are_separate_artifacts") is not True:
        failures.append("body_and_clothes_separation_not_proven")
    if _normalized(lineage.get("normal_review_route")) != "clothed_only":
        failures.append("normal_review_route_must_be_clothed_only")
    if request_complete_adult_anatomy:
        if maturity not in {"adult", "confirmed_adult", "adult_confirmed"}:
            failures.append("complete_adult_anatomy_forbidden_for_subject_maturity")
        elif not topology_report.get("anatomical_completeness_proven"):
            failures.append("complete_adult_anatomy_not_hash_attested")
    if not request_complete_adult_anatomy and topology_report.get(
        "anatomical_completeness_proven"
    ):
        warnings.append("adult_anatomy_evidence_present_but_not_requested")

    staging_allowed = not failures
    return {
        "schema_version": 1,
        "subject_id": _text(subject_id),
        "subject_maturity": maturity,
        "candidate_sha256": digest,
        "status": "ready_for_private_clothed_stage" if staging_allowed else "blocked",
        "staging_allowed": staging_allowed,
        "runtime_activation_allowed": False,
        "failures": list(dict.fromkeys(failures)),
        "warnings": list(dict.fromkeys(warnings)),
        "privacy_contract": {
            "normal_review_route": "clothed_only",
            "source_photos_or_paths_in_report": False,
            "intimate_review_render_retained": False,
        },
        "truth_note": (
            "A passing result permits a private, clothed staging review only. Runtime "
            "activation and identity likeness still require separate owner approval."
        ),
    }
