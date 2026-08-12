"""Fail-closed body-policy checks for executable avatar model builders.

The central policy validator works on maturity metadata plus selected asset
records. Blender scripts historically bypassed that boundary by importing
hard-coded files directly. This adapter resolves exact file identities and
their recorded lineage before any Blender import, export, staging, or runtime
replacement is allowed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from Core.avatar_asset_library import infer_avatar_maturity_policy, validate_avatar_body_policy


class BodyPolicyGateError(RuntimeError):
    """Raised before model mutation when body-policy evidence is not safe."""


class RuntimeActivationApprovalError(RuntimeError):
    """Raised before a staged model can replace a live runtime model."""

    def __init__(self, validation: dict[str, Any]):
        self.validation = validation
        failures = validation.get("failures") or ["runtime_activation_approval_failed"]
        super().__init__("Runtime activation blocked: " + ", ".join(str(item) for item in failures))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _candidate_profile(project_root: Path, candidate_id: str) -> dict[str, Any]:
    profile = _read_json(
        project_root
        / "TemporaryAI"
        / "candidates"
        / candidate_id
        / "temporary_ai_profile.json"
    )
    if not profile:
        avatar_profile = _read_json(
            project_root / "Avatar" / "temp_ai" / candidate_id / "avatar_profile.json"
        )
        profile = {
            "candidate_id": candidate_id,
            "display_name": avatar_profile.get("display_name") or candidate_id,
            "visual_identity": avatar_profile.get("visual_profile") or {},
        }
    adjustments = _read_json(
        project_root / "Avatar" / "temp_ai" / candidate_id / "avatar_builder_adjustments.json"
    )
    override = str(adjustments.get("maturity_override") or "")
    if override:
        profile = dict(profile)
        age_review = {
            "maturity_class_override": override,
            "reason": adjustments.get("maturity_reason") or "Persisted Avatar Builder policy.",
            "source": "avatar_builder_adjustments.json",
        }
        exact_classification = adjustments.get(
            "confirmed_adult_classification_evidence"
        )
        if isinstance(exact_classification, dict):
            age_review["confirmed_adult_classification_evidence"] = dict(
                exact_classification
            )
        if adjustments.get("resident_adult_anatomy_choice_recorded") is True:
            age_review["resident_adult_anatomy_choice_recorded"] = True
        if adjustments.get("age_progression_presentation_label") == (
            "adult_aged_up_variant"
        ):
            age_review["age_progression_presentation_label"] = (
                "adult_aged_up_variant"
            )
        if isinstance(adjustments.get("age_progression_contract"), dict):
            age_review["age_progression_contract"] = dict(
                adjustments["age_progression_contract"]
            )
        profile["age_review"] = age_review
    return profile


def _library_records(project_root: Path) -> list[dict[str, Any]]:
    manifest = _read_json(
        project_root / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json"
    )
    records = manifest.get("records")
    return [dict(item) for item in records if isinstance(item, dict)] if isinstance(records, list) else []


def _catalogued_record_for_path(
    path: Path,
    records_by_hash: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    digest = _sha256(path)
    record = records_by_hash.get(digest)
    if not record:
        return None
    result = dict(record)
    result["selected_file"] = str(path)
    result["selected_sha256"] = digest
    # Treat either catalog flag as authoritative. This closes the gap where a
    # record says non-adult use is denied but omits the redundant adult_only flag.
    if result.get("allowed_for_non_adult") is False:
        result["adult_only"] = True
    return result


def _lineage_paths(project_root: Path, manifests: Iterable[str | Path]) -> list[Path]:
    keys = {"source_body", "base_body_source", "source_base", "required_source_model"}
    paths: list[Path] = []
    for manifest_value in manifests:
        manifest_path = _resolve(project_root, manifest_value)
        data = _read_json(manifest_path)
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value:
                paths.append(_resolve(project_root, value))
    return paths


def evaluate_body_policy(
    *,
    project_root: Path,
    candidate_id: str,
    body_treatment: str,
    selected_asset_paths: Iterable[str | Path] = (),
    provenance_manifests: Iterable[str | Path] = (),
    declared_asset_records: Iterable[dict[str, Any]] = (),
    expected_maturity_classes: Iterable[str] = (),
    required_asset_sha256: str = "",
    require_asset_evidence: bool = True,
) -> dict[str, Any]:
    """Evaluate exact asset and lineage evidence without changing any state."""
    project_root = project_root.resolve()
    maturity_policy = infer_avatar_maturity_policy(
        candidate_id,
        _candidate_profile(project_root, candidate_id),
    )
    library_records = _library_records(project_root)
    records_by_hash = {
        str(record.get("sha256") or "").lower(): record
        for record in library_records
        if record.get("sha256")
    }
    selected_paths = [_resolve(project_root, value) for value in selected_asset_paths]
    lineage_paths = _lineage_paths(project_root, provenance_manifests)
    missing_paths = [str(path) for path in selected_paths if not path.is_file()]
    selected_records: list[dict[str, Any]] = [dict(item) for item in declared_asset_records]
    catalogued_paths: list[str] = []
    for path in [*selected_paths, *lineage_paths]:
        record = _catalogued_record_for_path(path, records_by_hash)
        if record:
            selected_records.append(record)
            catalogued_paths.append(str(path))

    deduplicated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in selected_records:
        if record.get("allowed_for_non_adult") is False:
            record["adult_only"] = True
        identity = str(
            record.get("sha256")
            or record.get("selected_sha256")
            or record.get("id")
            or record.get("filename")
            or id(record)
        ).lower()
        if identity in seen:
            continue
        seen.add(identity)
        deduplicated.append(record)

    validation = validate_avatar_body_policy(
        maturity_policy,
        body_treatment=body_treatment,
        selected_assets=deduplicated,
    )
    failures = list(validation.get("failures") or [])
    expected = {str(item) for item in expected_maturity_classes if str(item)}
    maturity_class = str(maturity_policy.get("maturity_class") or "")
    if expected and maturity_class not in expected:
        failures.append("candidate_maturity_does_not_match_builder_contract")
    if missing_paths:
        failures.append("selected_body_asset_missing")
    if require_asset_evidence and not deduplicated:
        failures.append("selected_body_asset_has_no_catalogued_or_declared_policy_evidence")
    reference_only_assets = [
        str(record.get("id") or record.get("filename") or "unnamed_reference")
        for record in deduplicated
        if bool(record.get("reference_only"))
        or record.get("copy_as_avatar_body_allowed") is False
    ]
    if reference_only_assets:
        failures.append("reference_only_asset_cannot_be_used_as_candidate_body")
    actual_selected_hashes = [_sha256(path) for path in selected_paths if path.is_file()]
    required_hash = required_asset_sha256.strip().lower()
    if required_hash and (not actual_selected_hashes or actual_selected_hashes[0] != required_hash):
        failures.append("selected_body_asset_does_not_match_required_exact_identity")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "maturity_class": maturity_class,
        "body_treatment": body_treatment,
        "selected_asset_paths": [str(path) for path in selected_paths],
        "selected_asset_sha256": actual_selected_hashes,
        "lineage_paths": [str(path) for path in lineage_paths],
        "catalogued_lineage_paths": catalogued_paths,
        "selected_asset_records": deduplicated,
        "reference_only_assets": reference_only_assets,
        "missing_paths": missing_paths,
        "central_validation": validation,
        "status": "failed" if failures else "passed",
        "failures": failures,
    }


def enforce_body_policy(**kwargs: Any) -> dict[str, Any]:
    """Return passed evidence or raise before a model can be imported/written."""
    result = evaluate_body_policy(**kwargs)
    if result["status"] != "passed":
        raise BodyPolicyGateError(
            f"Avatar body policy blocked {result['candidate_id']}: "
            + ", ".join(result["failures"])
        )
    return result


def enforce_marinette_live_body_policy(
    project_root: Path,
    body_path: Path,
    *,
    provenance_manifests: Iterable[str | Path] = (),
) -> dict[str, Any]:
    """Gate legacy scripts that modify normal Marinette's current body."""
    manifests = list(provenance_manifests) or [
        project_root
        / "Avatar"
        / "models"
        / "temp_ai"
        / "ladybug_marinette_expanded_smoke"
        / "avatar_body_base_rebuild_v1.json"
    ]
    return enforce_body_policy(
        project_root=project_root,
        candidate_id="ladybug_marinette_expanded_smoke",
        body_treatment="non_adult_doll_safe",
        selected_asset_paths=[body_path],
        provenance_manifests=manifests,
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=True,
    )


def enforce_marinette_procedural_body_policy(project_root: Path) -> dict[str, Any]:
    """Gate a genuinely procedural doll-safe normal-Marinette build."""
    return enforce_body_policy(
        project_root=project_root,
        candidate_id="ladybug_marinette_expanded_smoke",
        body_treatment="non_adult_doll_safe",
        expected_maturity_classes={"non_adult_doll_safe"},
        require_asset_evidence=False,
    )


def evaluate_runtime_activation_approval(
    *,
    project_root: Path,
    candidate_id: str,
    staged_model: Path,
    approval_artifact: Path,
) -> dict[str, Any]:
    """Validate a separately authored approval against the exact staged bytes."""
    project_root = project_root.resolve()
    staged_model = _resolve(project_root, staged_model).resolve()
    approval_artifact = _resolve(project_root, approval_artifact).resolve()
    approval = _read_json(approval_artifact)
    failures: list[str] = []
    staged_sha256 = _sha256(staged_model) if staged_model.is_file() else ""
    recorded_model_value = str(approval.get("staged_model") or "")
    recorded_model = (
        _resolve(project_root, recorded_model_value).resolve()
        if recorded_model_value
        else None
    )
    recorded_sha256 = str(approval.get("staged_sha256") or "").strip().lower()

    if not staged_sha256:
        failures.append("staged_model_missing")
    if not approval_artifact.is_file() or not approval:
        failures.append("explicit_activation_approval_artifact_missing_or_invalid")
    if str(approval.get("candidate_id") or "") != candidate_id:
        failures.append("activation_approval_candidate_identity_mismatch")
    if approval.get("approval_status") != "approved_for_runtime_activation":
        failures.append("activation_approval_status_not_approved")
    if approval.get("runtime_activation_allowed") is not True:
        failures.append("runtime_activation_not_explicitly_allowed")
    if approval.get("approval_scope") != "replace_live_avatar_with_exact_staged_model":
        failures.append("activation_approval_scope_mismatch")
    if not str(approval.get("approved_by") or "").strip():
        failures.append("activation_approval_missing_approver")
    if not str(approval.get("approved_at") or "").strip():
        failures.append("activation_approval_missing_timestamp")
    if recorded_model != staged_model:
        failures.append("activation_approval_staged_model_path_mismatch")
    if not staged_sha256 or recorded_sha256 != staged_sha256:
        failures.append("activation_approval_staged_model_sha256_mismatch")

    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "approval_artifact": str(approval_artifact),
        "staged_model": str(staged_model),
        "staged_sha256": staged_sha256,
        "recorded_staged_sha256": recorded_sha256,
        "approved_by": str(approval.get("approved_by") or ""),
        "approved_at": str(approval.get("approved_at") or ""),
        "status": "failed" if failures else "passed",
        "failures": failures,
    }


def activate_staged_model_if_approved(
    *,
    project_root: Path,
    candidate_id: str,
    staged_model: Path,
    live_model: Path,
    approval_artifact: Path,
    activation_requested: bool = False,
    backup_path: Path | None = None,
) -> dict[str, Any]:
    """Keep staged-only by default; copy only after exact approval validation."""
    project_root = project_root.resolve()
    staged_model = _resolve(project_root, staged_model).resolve()
    live_model = _resolve(project_root, live_model).resolve()
    approval_artifact = _resolve(project_root, approval_artifact).resolve()
    staged_sha256 = _sha256(staged_model) if staged_model.is_file() else ""
    if not activation_requested:
        return {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "status": "staged_review_only_not_activated",
            "activation_requested": False,
            "active_model_replaced": False,
            "runtime_activation_allowed": False,
            "staged_model": str(staged_model),
            "staged_sha256": staged_sha256,
            "approval_artifact": str(approval_artifact),
            "failures": [],
        }

    validation = evaluate_runtime_activation_approval(
        project_root=project_root,
        candidate_id=candidate_id,
        staged_model=staged_model,
        approval_artifact=approval_artifact,
    )
    validation["activation_requested"] = True
    validation["active_model_replaced"] = False
    validation["runtime_activation_allowed"] = validation["status"] == "passed"
    if validation["status"] != "passed":
        raise RuntimeActivationApprovalError(validation)

    if backup_path is not None and live_model.is_file():
        resolved_backup = _resolve(project_root, backup_path).resolve()
        resolved_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live_model, resolved_backup)
        validation["backup_model"] = str(resolved_backup)
    live_model.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged_model, live_model)
    live_sha256 = _sha256(live_model)
    if live_sha256 != validation["staged_sha256"]:
        raise RuntimeError("Runtime activation copy verification failed.")
    validation.update(
        {
            "status": "activated_after_explicit_exact_hash_approval",
            "active_model_replaced": True,
            "live_model": str(live_model),
            "live_sha256": live_sha256,
        }
    )
    return validation
