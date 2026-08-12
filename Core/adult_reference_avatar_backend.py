"""Fail-closed staging for licensed adult reference-model derivatives.

This module deliberately separates policy/provenance checks from Blender.  A
reference model may only reach the Blender worker when its exact hash, subject,
maturity, variant, and adaptation license are all bound in one request.  The
worker output is still review-only: this backend never writes a live-avatar
slot and never grants runtime activation.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from Core.avatar_body_topology import (
    _read_glb_document,
    evaluate_body_candidate_readiness,
    inspect_glb_topology,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ADULT_MATURITY = {"adult", "confirmed_adult", "adult_confirmed"}
SUPPORTED_ADAPTATION_LICENSES = {
    "cc-by-4-0": {
        "attribution_required": True,
        "share_alike_required": False,
    },
}
OUTPUT_CONTRACT = {
    "body_glb": ("_private_body.glb", ".glb"),
    "hair_glb": ("_separate_hair.glb", ".glb"),
    "eyes_glb": ("_separate_eyes.glb", ".glb"),
    "clothes_glb": ("_separate_clothes.glb", ".glb"),
    "clothed_review_glb": ("_clothed_review_assembly.glb", ".glb"),
    "build_evidence": ("adult_reference_build_evidence.json", ".json"),
    "rig_attestation": ("rig_mechanical_attestation.json", ".json"),
    "attribution": ("CC_BY_4_attribution.json", ".json"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _license_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-")


def _project_path(value: Any, *, project_root: Path) -> Path:
    raw = Path(_text(value))
    return (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()


def _relative(path: Path, *, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return "private_external_reference"


def _glb_joint_rest_signature(path: Path) -> tuple[str, int]:
    document, _, _ = _read_glb_document(path)
    nodes = document.get("nodes") if isinstance(document.get("nodes"), list) else []
    skins = document.get("skins") if isinstance(document.get("skins"), list) else []
    joint_indices = sorted(
        {
            index
            for skin in skins
            if isinstance(skin, dict) and isinstance(skin.get("joints"), list)
            for index in skin["joints"]
            if isinstance(index, int) and 0 <= index < len(nodes)
        }
    )
    parent_by_child: dict[int, int] = {}
    for parent_index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("children"), list):
            continue
        for child in node["children"]:
            if isinstance(child, int):
                parent_by_child[child] = parent_index
    records = []
    joint_set = set(joint_indices)
    for index in joint_indices:
        node = nodes[index] if isinstance(nodes[index], dict) else {}
        parent = parent_by_child.get(index)
        records.append(
            {
                "name": _text(node.get("name")),
                "parent_name": (
                    _text(nodes[parent].get("name"))
                    if parent in joint_set and isinstance(nodes[parent], dict)
                    else ""
                ),
                "matrix": node.get("matrix", []),
                "translation": node.get("translation", []),
                "rotation": node.get("rotation", []),
                "scale": node.get("scale", []),
            }
        )
    encoded = json.dumps(sorted(records, key=lambda item: item["name"]), separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), len(joint_indices)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _has_symlink_from(path: Path, stop: Path) -> bool:
    current = path.absolute()
    stop = stop.absolute()
    while True:
        if current.exists() and current.is_symlink():
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def _load_bound_json(
    binding: Mapping[str, Any] | None,
    *,
    project_root: Path,
    failures: list[str],
    failure_prefix: str,
    required_path: Path | None = None,
) -> tuple[dict[str, Any], Path | None]:
    if not isinstance(binding, Mapping):
        failures.append(f"{failure_prefix}_binding_required")
        return {}, None
    raw_path = Path(_text(binding.get("path")))
    digest = _text(binding.get("sha256")).lower()
    if raw_path.is_absolute() or ".." in raw_path.parts:
        failures.append(f"{failure_prefix}_path_must_be_safe_project_relative")
        return {}, None
    path = (project_root / raw_path).resolve()
    if required_path is not None and path != required_path.resolve():
        failures.append(f"{failure_prefix}_path_not_authorized")
    if not SHA256_RE.fullmatch(digest):
        failures.append(f"{failure_prefix}_valid_sha256_required")
    if not path.is_file() or path.is_symlink() or _has_symlink_from(path, project_root):
        failures.append(f"{failure_prefix}_artifact_missing_or_symlinked")
        return {}, path
    if sha256_file(path) != digest:
        failures.append(f"{failure_prefix}_sha256_mismatch")
        return {}, path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append(f"{failure_prefix}_invalid_json")
        return {}, path
    if not isinstance(value, dict):
        failures.append(f"{failure_prefix}_must_be_json_object")
        return {}, path
    return value, path


def validate_adult_reference_request_file(
    request_path: str | Path,
    request: Mapping[str, Any],
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> list[str]:
    root = Path(project_root).resolve()
    candidate_id = _text(request.get("candidate_id"))
    expected = root / "Avatar" / "temp_ai" / candidate_id / "adult_reference_derivative_request.json"
    path = Path(request_path)
    failures: list[str] = []
    if path.is_symlink() or _has_symlink_from(path, root):
        failures.append("request_file_or_parent_is_symlinked")
    try:
        if path.resolve() != expected.resolve():
            failures.append("request_file_must_be_in_exact_candidate_root")
    except OSError:
        failures.append("request_file_path_invalid")
    return failures


def validate_adult_reference_request(
    request: Mapping[str, Any],
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate exact authority, paths, identity, and policy before any write."""
    root = Path(project_root).resolve()
    failures: list[str] = []
    warnings: list[str] = []
    candidate_id = _text(request.get("candidate_id"))
    subject_id = _text(request.get("subject_id"))
    maturity = _normalized(request.get("maturity_class"))
    variant = _normalized(request.get("variant"))
    source = request.get("source") if isinstance(request.get("source"), Mapping) else {}
    attribution = source.get("attribution") if isinstance(source.get("attribution"), Mapping) else {}
    privacy = request.get("privacy") if isinstance(request.get("privacy"), Mapping) else {}
    plan = request.get("derivative_plan") if isinstance(request.get("derivative_plan"), Mapping) else {}
    evidence_bindings = (
        request.get("policy_evidence") if isinstance(request.get("policy_evidence"), Mapping) else {}
    )
    candidate_root = root / "Avatar" / "temp_ai" / candidate_id
    generated_root = candidate_root / "generated_body"

    if not SAFE_ID_RE.fullmatch(candidate_id):
        failures.append("candidate_id_is_not_safe")
    request_root = _text(request.get("project_root"))
    try:
        if Path(request_root).resolve() != root:
            failures.append("request_project_root_mismatch")
    except (OSError, RuntimeError, ValueError):
        failures.append("request_project_root_invalid")
    if not subject_id or _normalized(subject_id) in {"unknown", "generic"}:
        failures.append("exact_subject_id_required")
    if maturity not in ADULT_MATURITY:
        failures.append("adult_reference_backend_requires_confirmed_adult_subject")
    if not variant:
        failures.append("exact_variant_required")
    if _normalized(subject_id) == "beth_smith" and ("space_beth" in variant or variant == "space"):
        failures.append("ordinary_non_space_variant_required")
    excluded = {_normalized(item) for item in request.get("excluded_variants", []) if _text(item)}
    if "space_beth" not in excluded and _normalized(subject_id) == "beth_smith":
        failures.append("beth_request_must_explicitly_exclude_space_beth")
    if _normalized(request.get("target_type")) != "temporary_ai":
        failures.append("backend_currently_stages_temporary_ai_only")
    if request.get("runtime_activation_requested") is not False:
        failures.append("runtime_activation_must_be_explicitly_false")

    expected_hash = _text(source.get("expected_sha256")).lower()
    raw_source = Path(_text(source.get("path")))
    source_path: Path | None = None
    authorized_source_root = root / "Avatar" / "avatar_builder" / "asset_library" / "adult_anatomy_reference"
    if raw_source.is_absolute() or ".." in raw_source.parts:
        failures.append("source_path_must_be_safe_project_relative")
    else:
        source_path = (root / raw_source).resolve()
        if not _is_within(source_path, authorized_source_root):
            failures.append("source_path_outside_adult_reference_library")
    if not SHA256_RE.fullmatch(expected_hash):
        failures.append("valid_exact_source_sha256_required")
    if source_path is not None:
        if not source_path.is_file() or source_path.is_symlink() or _has_symlink_from(source_path, root):
            failures.append("source_artifact_missing_or_symlinked")
        elif source_path.suffix.lower() != ".glb":
            failures.append("source_artifact_must_be_glb")
        elif expected_hash != sha256_file(source_path):
            failures.append("source_sha256_mismatch")
    if source.get("reference_only") is not True:
        failures.append("source_must_remain_declared_reference_only")
    if source.get("copy_as_avatar_body_allowed") is not False:
        failures.append("direct_reference_body_copy_must_remain_forbidden")

    asset_manifest, _ = _load_bound_json(
        evidence_bindings.get("asset_library_manifest"),
        project_root=root,
        failures=failures,
        failure_prefix="asset_library_manifest",
        required_path=root / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json",
    )
    records = asset_manifest.get("records") if isinstance(asset_manifest.get("records"), list) else []
    indexed = [
        item
        for item in records
        if isinstance(item, dict)
        and _text(item.get("id")) == _text(source.get("asset_id"))
        and _text(item.get("sha256")).lower() == expected_hash
        and Path(_text(item.get("local_file"))).as_posix() == raw_source.as_posix()
    ]
    if len(indexed) != 1:
        failures.append("source_not_exactly_bound_in_asset_library")
    elif not (
        indexed[0].get("adult_only") is True
        and indexed[0].get("allowed_for_non_adult") is False
        and _normalized(indexed[0].get("category")) == "adult_anatomy_reference"
        and "never copy" in _text(indexed[0].get("usage_policy")).lower()
    ):
        failures.append("indexed_source_policy_not_adult_reference_only")

    reference_manifest_binding = evidence_bindings.get("reference_manifest")
    reference_manifest, reference_manifest_path = _load_bound_json(
        reference_manifest_binding,
        project_root=root,
        failures=failures,
        failure_prefix="reference_manifest",
    )
    reference_root = root / "Avatar" / "avatar_builder" / "reference_models"
    if reference_manifest_path is not None and not _is_within(reference_manifest_path, reference_root):
        failures.append("reference_manifest_outside_authorized_root")
    reference_models = reference_manifest.get("models") if isinstance(reference_manifest.get("models"), list) else []
    glb_records = [
        item for item in reference_models if isinstance(item, dict) and _text(item.get("sha256")).lower() == expected_hash
    ]
    if len(glb_records) != 1 or glb_records[0].get("reference_only") is not True or glb_records[0].get("copy_as_avatar_body_allowed") is not False:
        failures.append("reference_manifest_does_not_bind_source_policy")
    if _normalized((reference_manifest.get("maturity_policy") or {}).get("maturity_class")) not in ADULT_MATURITY:
        failures.append("reference_manifest_does_not_bind_adult_maturity")

    license_evidence, _ = _load_bound_json(
        evidence_bindings.get("license_evidence"),
        project_root=root,
        failures=failures,
        failure_prefix="license_evidence",
    )
    role_evidence, _ = _load_bound_json(
        evidence_bindings.get("source_role_map_evidence"),
        project_root=root,
        failures=failures,
        failure_prefix="source_role_map_evidence",
    )
    canon_profile, canon_profile_path = _load_bound_json(
        evidence_bindings.get("maturity_and_variant_profile"),
        project_root=root,
        failures=failures,
        failure_prefix="maturity_and_variant_profile",
    )
    source_brief, source_brief_path = _load_bound_json(
        evidence_bindings.get("avatar_source_brief"),
        project_root=root,
        failures=failures,
        failure_prefix="avatar_source_brief",
    )
    reliable_pack, _ = _load_bound_json(
        evidence_bindings.get("reliable_source_pack"),
        project_root=root,
        failures=failures,
        failure_prefix="reliable_source_pack",
        required_path=root / "TemporaryAI" / "candidates" / candidate_id / "reliable_source_pack.json",
    )
    if canon_profile_path is not None and not _is_within(canon_profile_path, candidate_root):
        failures.append("maturity_and_variant_profile_outside_candidate_root")
    if source_brief_path is not None and not _is_within(source_brief_path, candidate_root):
        failures.append("avatar_source_brief_outside_candidate_root")

    license_data = license_evidence.get("license") if isinstance(license_evidence.get("license"), Mapping) else {}
    license_id = _license_id(license_data.get("id"))
    if _text(license_evidence.get("source_glb_sha256")).lower() != expected_hash:
        failures.append("license_evidence_source_hash_mismatch")
    if license_id not in SUPPORTED_ADAPTATION_LICENSES or license_data.get("adaptation_allowed") is not True:
        failures.append("license_does_not_authorize_derivative")
    evidence_attribution = license_evidence.get("attribution") if isinstance(license_evidence.get("attribution"), Mapping) else {}
    for key in ("title", "author", "source_url"):
        if _text(attribution.get(key)) != _text(evidence_attribution.get(key)):
            failures.append(f"attribution_{key}_not_bound_to_license_evidence")
    if _text(attribution.get("license_url")) != _text(license_data.get("license_url")):
        failures.append("attribution_license_url_not_bound_to_license_evidence")
    archive_evidence = license_evidence.get("license_archive") if isinstance(license_evidence.get("license_archive"), Mapping) else {}
    license_archive_records = [
        item
        for item in reference_models
        if isinstance(item, dict) and _text(item.get("sha256")).lower() == _text(archive_evidence.get("sha256")).lower()
    ]
    if len(license_archive_records) != 1:
        failures.append("license_archive_not_bound_in_reference_manifest")
    else:
        archive_path = Path(_text(license_archive_records[0].get("source_file")))
        try:
            if sha256_file(archive_path) != _text(archive_evidence.get("sha256")).lower():
                failures.append("license_archive_sha256_mismatch")
            else:
                with zipfile.ZipFile(archive_path) as package:
                    member = package.read(_text(archive_evidence.get("member")))
                if hashlib.sha256(member).hexdigest() != _text(archive_evidence.get("member_sha256")).lower():
                    failures.append("license_member_sha256_mismatch")
        except (OSError, KeyError, zipfile.BadZipFile):
            failures.append("license_archive_or_member_unavailable")

    if _text(role_evidence.get("source_glb_sha256")).lower() != expected_hash:
        failures.append("source_role_map_glb_hash_mismatch")
    role_contract = role_evidence.get("glb_component_contract") if isinstance(role_evidence.get("glb_component_contract"), Mapping) else {}
    requested_counts = plan.get("expected_component_counts") if isinstance(plan.get("expected_component_counts"), Mapping) else {}
    count_map = {
        "discard": "discarded_outline_mesh_count",
        "body_surface": "body_and_head_surface_mesh_count",
        "hair": "hair_mesh_count",
        "eyes": "eye_mesh_count",
    }
    for request_key, evidence_key in count_map.items():
        if int(requested_counts.get(request_key, -1)) != int(role_contract.get(evidence_key, -2)):
            failures.append(f"source_role_count_{request_key}_mismatch")
    role_package = role_evidence.get("source_package") if isinstance(role_evidence.get("source_package"), Mapping) else {}
    role_archive_records = [
        item for item in reference_models if isinstance(item, dict) and _text(item.get("sha256")).lower() == _text(role_package.get("sha256")).lower()
    ]
    if len(role_archive_records) != 1:
        failures.append("role_source_archive_not_bound_in_reference_manifest")
    else:
        role_archive_path = Path(_text(role_archive_records[0].get("source_file")))
        try:
            if sha256_file(role_archive_path) != _text(role_package.get("sha256")).lower():
                failures.append("role_source_archive_sha256_mismatch")
            else:
                with zipfile.ZipFile(role_archive_path) as outer:
                    nested = outer.read(_text(role_package.get("nested_member")))
                if hashlib.sha256(nested).hexdigest() != _text(role_package.get("nested_member_sha256")).lower():
                    failures.append("role_nested_archive_sha256_mismatch")
                else:
                    with zipfile.ZipFile(io.BytesIO(nested)) as inner:
                        obj_bytes = inner.read(_text(role_package.get("obj_member")))
                        mtl_bytes = inner.read(_text(role_package.get("mtl_member")))
                    if hashlib.sha256(obj_bytes).hexdigest() != _text(role_package.get("obj_member_sha256")).lower():
                        failures.append("role_obj_member_sha256_mismatch")
                    if hashlib.sha256(mtl_bytes).hexdigest() != _text(role_package.get("mtl_member_sha256")).lower():
                        failures.append("role_mtl_member_sha256_mismatch")
        except (OSError, KeyError, zipfile.BadZipFile):
            failures.append("role_source_archive_or_member_unavailable")

    continuity = canon_profile.get("continuity") if isinstance(canon_profile.get("continuity"), Mapping) else {}
    canon_excluded = " ".join(_text(item).lower() for item in continuity.get("excluded", []))
    if _text(canon_profile.get("candidate_id")) != candidate_id:
        failures.append("maturity_profile_candidate_mismatch")
    if _normalized(canon_profile.get("maturity_class")) != maturity or maturity not in ADULT_MATURITY:
        failures.append("maturity_profile_does_not_bind_confirmed_adult")
    if _normalized(subject_id) == "beth_smith":
        if "home beth" not in _text(continuity.get("selected_form")).lower() or "space beth" not in canon_excluded:
            failures.append("maturity_profile_does_not_bind_ordinary_non_space_variant")
    elif _normalized(continuity.get("selected_form")) != variant:
        failures.append("maturity_profile_selected_form_variant_mismatch")
    target = source_brief.get("target") if isinstance(source_brief.get("target"), Mapping) else {}
    decision = source_brief.get("build_decision") if isinstance(source_brief.get("build_decision"), Mapping) else {}
    if _text(source_brief.get("candidate_id")) != candidate_id or _normalized(target.get("maturity_class")) != maturity:
        failures.append("avatar_source_brief_candidate_or_maturity_mismatch")
    if _normalized(subject_id) == "beth_smith":
        if "ordinary home beth" not in _text(target.get("form")).lower() or "space beth" not in " ".join(_text(item).lower() for item in target.get("explicitly_not", [])):
            failures.append("avatar_source_brief_variant_mismatch")
    elif _normalized(target.get("form")) != variant:
        failures.append("avatar_source_brief_variant_mismatch")
    if decision.get("body_candidate_may_be_staged_for_private_review_after_backend_validation") is not True or decision.get("runtime_activation_allowed") is not False:
        failures.append("avatar_source_brief_does_not_authorize_review_only_derivative")
    reliable_identity = _text(reliable_pack.get("candidate_id")) or _text(reliable_pack.get("pack_id"))
    if candidate_id not in reliable_identity:
        failures.append("reliable_source_pack_candidate_mismatch")

    if _normalized(plan.get("mode")) != "shape_preserving_licensed_rig_derivative":
        failures.append("approved_shape_preserving_derivative_mode_required")
    if plan.get("new_skinning_and_rig_required") is not True:
        failures.append("new_skinning_and_rig_must_be_required")
    if plan.get("discard_duplicate_outline_shells") is not True:
        failures.append("duplicate_reference_outline_shells_must_be_discarded")
    if plan.get("discard_all_source_materials_and_textures") is not True:
        failures.append("all_source_materials_and_textures_must_be_discarded")
    if plan.get("separate_body_clothes") is not True or plan.get("separate_body_hair_eyes_clothes") is not True:
        failures.append("body_hair_eyes_and_clothes_must_be_separate")
    if plan.get("preserve_source_surface_shape") is not True:
        failures.append("shape_preservation_must_be_explicit")
    if privacy.get("normal_review_route") != "clothed_only":
        failures.append("normal_review_route_must_be_clothed_only")
    if privacy.get("intimate_render_allowed") is not False:
        failures.append("intimate_render_must_be_forbidden")
    if privacy.get("public_export_allowed") is not False:
        failures.append("public_export_must_be_false")

    outputs = request.get("outputs") if isinstance(request.get("outputs"), Mapping) else {}
    if set(outputs) != set(OUTPUT_CONTRACT):
        failures.append("output_contract_keys_mismatch")
    output_paths: list[Path] = []
    for key, (required_ending, required_suffix) in OUTPUT_CONTRACT.items():
        raw = Path(_text(outputs.get(key)))
        if raw.is_absolute() or ".." in raw.parts:
            failures.append(f"output_{key}_must_be_safe_project_relative")
            continue
        resolved = (root / raw).resolve()
        output_paths.append(resolved)
        if resolved.parent != generated_root.resolve():
            failures.append(f"output_{key}_outside_exact_candidate_generated_root")
        if resolved.suffix.lower() != required_suffix or not resolved.name.endswith(required_ending):
            failures.append(f"output_{key}_filename_or_extension_invalid")
        if _has_symlink_from(resolved, root):
            failures.append(f"output_{key}_path_contains_symlink")
    if len(set(output_paths)) != len(output_paths):
        failures.append("output_paths_must_be_distinct")

    if request.get("request_complete_adult_anatomy") is True:
        warnings.append("adult_complete_topology_still_requires_private_exact_hash_review")
    if source_path is not None and source_path.is_file():
        source_summary = {
            "artifact_id": _text(source.get("asset_id")) or "licensed_adult_reference",
            "sha256": sha256_file(source_path),
            "size_bytes": source_path.stat().st_size,
            "path_disclosed": False,
        }
    else:
        source_summary = {
            "artifact_id": _text(source.get("asset_id")) or "licensed_adult_reference",
            "sha256": expected_hash if SHA256_RE.fullmatch(expected_hash) else "",
            "size_bytes": 0,
            "path_disclosed": False,
        }
    return {
        "schema_version": 2,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "maturity_class": maturity,
        "variant": variant,
        "status": "preflight_passed" if not failures else "blocked",
        "preflight_passed": not failures,
        "runtime_activation_allowed": False,
        "failures": list(dict.fromkeys(failures)),
        "warnings": list(dict.fromkeys(warnings)),
        "source": source_summary,
        "license": {
            "id": license_id,
            "adaptation_allowed": license_id in SUPPORTED_ADAPTATION_LICENSES and license_data.get("adaptation_allowed") is True,
            "attribution_required": True,
            "evidence_hash_bound": bool(license_evidence),
        },
        "authority": {
            "asset_manifest_bound": len(indexed) == 1,
            "reference_manifest_bound": len(glb_records) == 1,
            "maturity_profile_bound": bool(canon_profile),
            "ordinary_variant_brief_bound": bool(source_brief),
            "source_role_map_bound": bool(role_evidence),
        },
        "privacy": {
            "normal_review_route": "clothed_only",
            "render_created": False,
            "source_path_disclosed": False,
        },
    }


def authorize_adult_reference_worker_request(
    request_path: str | Path,
    *,
    project_root: str | Path = PROJECT_ROOT,
    expected_request_sha256: str | None = None,
) -> dict[str, Any]:
    """Load and fully authorize the exact request bytes used by a worker.

    The Blender worker calls this itself with a project root derived from the
    worker's installed path.  That makes direct worker invocation fail closed
    instead of trusting a caller-supplied ``project_root`` or output path.  The
    optional exact hash also closes the wrapper-to-worker request replacement
    window.
    """
    root = Path(project_root).resolve()
    raw_path = Path(request_path)
    request_file = raw_path.absolute() if raw_path.is_absolute() else (Path.cwd() / raw_path).absolute()
    try:
        request_bytes = request_file.read_bytes()
    except OSError as exc:
        raise ValueError(f"adult reference request is unavailable: {exc}") from exc
    request_sha256 = hashlib.sha256(request_bytes).hexdigest()
    if expected_request_sha256 is not None:
        expected = _text(expected_request_sha256).lower()
        if not SHA256_RE.fullmatch(expected):
            raise ValueError("worker expected request SHA256 is invalid")
        if request_sha256 != expected:
            raise ValueError("worker request SHA256 changed after wrapper preflight")
    try:
        request = json.loads(request_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("adult reference request is not valid UTF-8 JSON") from exc
    if not isinstance(request, dict):
        raise ValueError("adult reference request must be a JSON object")
    location_failures = validate_adult_reference_request_file(request_file, request, project_root=root)
    if location_failures:
        raise ValueError("adult reference request file rejected: " + ", ".join(location_failures))
    preflight = validate_adult_reference_request(request, project_root=root)
    if not preflight["preflight_passed"]:
        raise ValueError("adult reference request failed preflight: " + ", ".join(preflight["failures"]))
    return {
        "request": request,
        "request_path": request_file,
        "request_sha256": request_sha256,
        "preflight": preflight,
        "trusted_project_root": root,
    }


def validate_worker_evidence_request_binding(
    evidence: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    authorized_request_sha256: str,
) -> list[str]:
    """Bind worker evidence to the exact request identity authorized at finalization."""
    failures: list[str] = []
    bindings = evidence.get("artifact_bindings") if isinstance(evidence.get("artifact_bindings"), Mapping) else {}
    if _text(bindings.get("request_sha256")).lower() != _text(authorized_request_sha256).lower():
        failures.append("build_evidence_request_sha256_mismatch")
    for identity_key in ("candidate_id", "subject_id", "variant"):
        if _text(evidence.get(identity_key)) != _text(request.get(identity_key)):
            failures.append(f"build_evidence_{identity_key}_mismatch")
    return failures


def run_blender_worker(
    request_path: str | Path,
    *,
    blender_executable: str | Path,
    project_root: str | Path = PROJECT_ROOT,
    timeout_seconds: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run the deterministic worker after the caller has confirmed the life loop is stopped."""
    root = Path(project_root).resolve()
    authorization = authorize_adult_reference_worker_request(request_path, project_root=root)
    request_file = authorization["request_path"]
    request_sha256 = authorization["request_sha256"]
    worker = root / "tools" / "blender_build_adult_reference_candidate.py"
    command = [
        str(Path(blender_executable)),
        "--background",
        "--factory-startup",
        "--python",
        str(worker),
        "--",
        "--request",
        str(request_file),
        "--validated-request-sha256",
        request_sha256,
    ]
    return subprocess.run(
        command,
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )


def finalize_adult_reference_candidate(
    request_path: str | Path,
    *,
    project_root: str | Path = PROJECT_ROOT,
    anatomy_attestation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash/audit worker outputs and write a fail-closed private staging status."""
    root = Path(project_root).resolve()
    authorization = authorize_adult_reference_worker_request(request_path, project_root=root)
    request_file = authorization["request_path"]
    request = authorization["request"]
    request_hash = authorization["request_sha256"]
    preflight = authorization["preflight"]

    candidate_id = _text(request["candidate_id"])
    candidate_root = root / "Avatar" / "temp_ai" / candidate_id
    generated_root = candidate_root / "generated_body"
    output_spec = request.get("outputs") if isinstance(request.get("outputs"), Mapping) else {}
    body_path = _project_path(output_spec.get("body_glb"), project_root=root)
    hair_path = _project_path(output_spec.get("hair_glb"), project_root=root)
    eyes_path = _project_path(output_spec.get("eyes_glb"), project_root=root)
    clothes_path = _project_path(output_spec.get("clothes_glb"), project_root=root)
    review_path = _project_path(output_spec.get("clothed_review_glb"), project_root=root)
    evidence_path = _project_path(output_spec.get("build_evidence"), project_root=root)
    rig_path = _project_path(output_spec.get("rig_attestation"), project_root=root)
    attribution_path = _project_path(output_spec.get("attribution"), project_root=root)
    missing = [
        name
        for name, path in (
            ("body_glb", body_path),
            ("hair_glb", hair_path),
            ("eyes_glb", eyes_path),
            ("clothes_glb", clothes_path),
            ("clothed_review_glb", review_path),
            ("build_evidence", evidence_path),
            ("rig_attestation", rig_path),
            ("attribution", attribution_path),
        )
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("worker outputs missing: " + ", ".join(missing))

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    rig_attestation = json.loads(rig_path.read_text(encoding="utf-8"))
    attribution_record = json.loads(attribution_path.read_text(encoding="utf-8"))
    body_hash = sha256_file(body_path)
    hair_hash = sha256_file(hair_path)
    eyes_hash = sha256_file(eyes_path)
    clothes_hash = sha256_file(clothes_path)
    review_hash = sha256_file(review_path)
    attribution_hash = sha256_file(attribution_path)
    source_hash = preflight["source"]["sha256"]
    evidence_failures: list[str] = []
    component_hashes = {body_hash, hair_hash, eyes_hash, clothes_hash, review_hash}
    if len(component_hashes) != 5 or source_hash in component_hashes:
        evidence_failures.append("component_artifacts_not_distinct_from_each_other_or_source")
    bindings = evidence.get("artifact_bindings") if isinstance(evidence.get("artifact_bindings"), Mapping) else {}
    expected_bindings = {
        "source_sha256": source_hash,
        "body_sha256": body_hash,
        "hair_sha256": hair_hash,
        "eyes_sha256": eyes_hash,
        "clothes_sha256": clothes_hash,
        "clothed_review_sha256": review_hash,
        "attribution_sha256": attribution_hash,
    }
    for key, value in expected_bindings.items():
        if _text(bindings.get(key)).lower() != value:
            evidence_failures.append(f"build_evidence_{key}_mismatch")
    evidence_failures.extend(
        validate_worker_evidence_request_binding(
            evidence,
            request,
            authorized_request_sha256=request_hash,
        )
    )
    if evidence.get("source_surface_shape_preserved") is not True:
        evidence_failures.append("source_surface_shape_preservation_not_proven")
    if evidence.get("licensed_source_surface_incorporated") is not True:
        evidence_failures.append("licensed_source_surface_incorporation_not_disclosed")
    if evidence.get("new_body_surface_authored") is not False:
        evidence_failures.append("new_body_surface_authorship_must_not_be_claimed")
    if evidence.get("new_rig_and_skinning_authored") is not True:
        evidence_failures.append("new_rig_and_skinning_not_proven")
    if evidence.get("source_artifact_byte_copied") is not False:
        evidence_failures.append("source_artifact_byte_copy_not_excluded")
    if evidence.get("body_hair_eyes_and_clothes_are_separate_artifacts") is not True:
        evidence_failures.append("component_separation_not_proven")
    if evidence.get("source_materials_and_textures_exported") is not False:
        evidence_failures.append("source_material_or_texture_export_not_excluded")
    if evidence.get("space_beth_material_or_outfit_exported") is not False:
        evidence_failures.append("space_beth_material_or_outfit_not_excluded")
    if evidence.get("renders_created") is not False:
        evidence_failures.append("unexpected_render_was_created")
    policy_hashes = evidence.get("policy_evidence_sha256") if isinstance(evidence.get("policy_evidence_sha256"), Mapping) else {}
    for key, binding in request["policy_evidence"].items():
        if _text(policy_hashes.get(key)).lower() != _text(binding.get("sha256")).lower():
            evidence_failures.append(f"worker_policy_evidence_{key}_hash_mismatch")
    if (
        _text(attribution_record.get("candidate_id")) != candidate_id
        or _license_id(attribution_record.get("license_id")) != preflight["license"]["id"]
        or attribution_record.get("runtime_activation_allowed") is not False
    ):
        evidence_failures.append("attribution_artifact_identity_or_license_mismatch")

    component_paths = {
        "body": body_path,
        "hair": hair_path,
        "eyes": eyes_path,
        "clothes": clothes_path,
        "assembly": review_path,
    }
    component_audits = {
        name: inspect_glb_topology(path, artifact_id=f"{candidate_id}_{name}")
        for name, path in component_paths.items()
    }
    for name, audit in component_audits.items():
        if not audit.get("humanoid_rig_structurally_ready"):
            evidence_failures.append(f"{name}_component_not_structurally_skinned")
    exported_signatures: dict[str, str] = {}
    exported_joint_counts: dict[str, int] = {}
    try:
        for name, path in component_paths.items():
            signature, joint_count = _glb_joint_rest_signature(path)
            exported_signatures[name] = signature
            exported_joint_counts[name] = joint_count
    except Exception:
        evidence_failures.append("component_joint_signature_inspection_failed")
    if len(set(exported_signatures.values())) != 1 or len(set(exported_joint_counts.values())) != 1:
        evidence_failures.append("component_shared_rig_signature_mismatch")
    mesh_counts = {
        name: int((audit.get("topology_metrics") or {}).get("mesh_count") or 0)
        for name, audit in component_audits.items()
    }
    if not (
        mesh_counts.get("body") == 3
        and mesh_counts.get("hair") == 1
        and mesh_counts.get("eyes") == 1
        and mesh_counts.get("clothes") == 4
        and mesh_counts.get("assembly") == 9
    ):
        evidence_failures.append("component_mesh_separation_counts_mismatch")

    topology = inspect_glb_topology(
        body_path,
        artifact_id=f"{candidate_id}_private_body_candidate",
        anatomy_attestation=anatomy_attestation,
        rig_attestation=rig_attestation,
    )
    lineage = {
        "schema_version": 2,
        "candidate_sha256": body_hash,
        "subject_id": request["subject_id"],
        "lineage_reviewed": not evidence_failures,
        "lineage_review_scope": "automated_exact_hash_and_derivative_evidence_only",
        "owner_visual_approval": False,
        "new_subject_specific_mesh_authored": False,
        "new_body_surface_authored": False,
        "reference_mesh_copied_into_candidate": True,
        "licensed_source_surface_incorporated": True,
        "source_artifact_byte_copied": False,
        "new_rig_and_skinning_authored": evidence.get("new_rig_and_skinning_authored") is True,
        "selected_directly_from_reference_library": False,
        "licensed_shape_preserving_derivative": True,
        "source_surface_shape_preserved": evidence.get("source_surface_shape_preserved") is True,
        "body_and_clothes_are_separate_artifacts": evidence.get("body_hair_eyes_and_clothes_are_separate_artifacts") is True,
        "body_hair_eyes_and_clothes_are_separate_artifacts": True,
        "normal_review_route": "clothed_only",
        "license_id": preflight["license"]["id"],
        "source_sha256": source_hash,
        "hair_sha256": hair_hash,
        "eyes_sha256": eyes_hash,
        "clothes_sha256": clothes_hash,
        "clothed_review_sha256": review_hash,
        "attribution_sha256": attribution_hash,
        "shared_exported_rig_signature": next(iter(exported_signatures.values()), ""),
        "runtime_activation_allowed": False,
    }
    generic_new_mesh_readiness = evaluate_body_candidate_readiness(
        topology,
        subject_id=request["subject_id"],
        subject_maturity=request["maturity_class"],
        lineage=lineage,
        request_complete_adult_anatomy=request.get("request_complete_adult_anatomy") is True,
    )
    generic_new_mesh_readiness["applicability"] = "not_applicable_to_licensed_surface_review_lane"
    generic_new_mesh_readiness["purpose"] = (
        "Transparency-only generic gate for a newly authored subject-specific body surface; "
        "this candidate intentionally incorporates a disclosed licensed source surface."
    )
    generic_new_mesh_readiness["runtime_activation_allowed"] = False

    licensed_failures = list(evidence_failures)
    if (
        request.get("request_complete_adult_anatomy") is True
        and topology.get("anatomical_completeness_proven") is not True
    ):
        licensed_failures.append("complete_adult_anatomy_not_hash_attested")
    if topology.get("stable_working_rig_proven") is not True:
        licensed_failures.append("stable_motion_and_deformation_not_proven")
    licensed_failures.extend(
        [
            "heuristic_rig_placement_and_weights_not_visually_validated",
            "complete_walk_stop_turn_sit_rise_lie_rise_collision_test_set_missing",
            "foot_slide_self_intersection_and_garment_penetration_not_tested",
            "facial_blink_gaze_jaw_emotion_and_lip_sync_controls_missing",
            "owner_clothed_visual_approval_missing",
        ]
    )
    licensed_failures = list(dict.fromkeys(licensed_failures))
    licensed_readiness = {
        "schema_version": 1,
        "lane": "licensed_shape_preserving_derivative_review",
        "status": "blocked",
        "artifact_generation_succeeded": not evidence_failures,
        "review_stage_allowed": False,
        "runtime_activation_allowed": False,
        "failures": licensed_failures,
        "licensed_source_surface_incorporated": True,
        "new_body_surface_authored": False,
        "truth_note": (
            "License, attribution, exact source hash, source-role evidence, and shape-preserving "
            "derivative lineage can authorize private artifact generation. They do not prove "
            "adult anatomical completeness, stable visual deformation, speaking controls, or "
            "owner approval."
        ),
    }

    generated_root.mkdir(parents=True, exist_ok=True)
    safe_lineage = generated_root / "adult_reference_derivative_lineage.json"
    safe_lineage.write_text(json.dumps(lineage, indent=2), encoding="utf-8")
    topology_path = generated_root / "body_topology_audit.json"
    topology_path.write_text(json.dumps(topology, indent=2), encoding="utf-8")
    status = {
        "schema_version": 2,
        "candidate_id": candidate_id,
        "subject_id": request["subject_id"],
        "variant": request["variant"],
        "updated_at": now_iso(),
        "status": "artifact_generated_review_blocked",
        "artifact_generation_succeeded": not evidence_failures,
        "clothed_review_assembly_available": review_path.is_file(),
        "review_stage_allowed": False,
        "body_sha256": body_hash,
        "hair_sha256": hair_hash,
        "eyes_sha256": eyes_hash,
        "clothes_sha256": clothes_hash,
        "clothed_review_sha256": review_hash,
        "source_sha256": source_hash,
        "source_surface_shape_preserved": evidence.get("source_surface_shape_preserved") is True,
        "licensed_source_surface_incorporated": True,
        "new_body_surface_authored": False,
        "new_rig_and_skinning_authored": evidence.get("new_rig_and_skinning_authored") is True,
        "body_hair_eyes_and_clothes_are_separate_artifacts": True,
        "shared_exported_rig_signature": next(iter(exported_signatures.values()), ""),
        "shared_exported_joint_count": next(iter(exported_joint_counts.values()), 0),
        "normal_review_artifact": _relative(review_path, project_root=root),
        "normal_review_route": "clothed_only",
        "no_render_created": evidence.get("renders_created") is False,
        "anatomical_completeness_proven": topology.get("anatomical_completeness_proven") is True,
        "structural_humanoid_skinning_present": topology.get("humanoid_rig_structurally_ready") is True,
        "mechanical_rig_stability_proven": False,
        "visual_deformation_quality_proven": False,
        "speaking_avatar_controls_ready": False,
        "facial_morph_targets_present": False,
        "identity_likeness_owner_approved": False,
        "visual_review_required": True,
        "blocking_reasons": licensed_failures,
        "runtime_activation_allowed": False,
        "readiness": licensed_readiness,
        "generic_new_mesh_gate": generic_new_mesh_readiness,
        "artifacts": {
            "body": _relative(body_path, project_root=root),
            "hair": _relative(hair_path, project_root=root),
            "eyes": _relative(eyes_path, project_root=root),
            "clothes": _relative(clothes_path, project_root=root),
            "clothed_review": _relative(review_path, project_root=root),
            "topology_audit": _relative(topology_path, project_root=root),
            "lineage": _relative(safe_lineage, project_root=root),
            "rig_attestation": _relative(rig_path, project_root=root),
            "build_evidence": _relative(evidence_path, project_root=root),
            "attribution": _relative(attribution_path, project_root=root),
        },
        "truth_note": (
            "The exact licensed source surfaces are incorporated and separated into body, hair, "
            "eyes, and clothes; only the rig, weights, and ordinary clothing are newly authored. "
            "The rig is a bounding-box heuristic that passed finite/bounded smoke checks, not a "
            "stable, visually honest, or speaking-avatar rig. Adult-complete topology, likeness, "
            "visual deformation, and owner approval remain unproven. Nothing is activated."
        ),
    }
    status_path = candidate_root / "adult_reference_backend_status.json"
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


__all__ = [
    "authorize_adult_reference_worker_request",
    "finalize_adult_reference_candidate",
    "run_blender_worker",
    "sha256_file",
    "validate_adult_reference_request",
    "validate_adult_reference_request_file",
    "validate_worker_evidence_request_binding",
]
