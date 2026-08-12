"""Fail-closed reusable-method promotion for the existing Avatar Builder.

Robert-private avatar experiments are evidence, not reusable templates.  A
method becomes selectable only when all of the following are independently
true:

* an exact, hash-bound Biological Robert static-foundation approval record
  exists and records Robert's own owner decision;
* a separate, independent, non-private generalization proof binds the exact
  generic method definition;
* the method definition, implementation binding, and generalization proof
  contain no private paths, identity measurements, Robert-specific
  coordinates/deltas, or private anatomy observations.

Rejected submissions may be archived by fingerprint and failure code.  Their
raw payload is never copied into the reusable registry, and archive entries are
never selectable.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


POLICY_PATH = Path(
    "Avatar/avatar_builder/policies/reusable_method_promotion_gate_v1.json"
)
REGISTRY_PATH = Path(
    "Avatar/avatar_builder/tooling/reusable_method_registry_v1.json"
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,95}$")

PRIVATE_PATH_MARKERS = (
    "c:/users/robmc",
    "/users/robmc",
    "desktop/reference",
    "desktop/robert",
    "private_owner_review",
    "protected_reference",
    "owner_reference",
    "requests/private",
    ".codex/attachments",
)
PRIVATE_VALUE_MARKERS = (
    "biological robert",
    "synthetic robert",
    "robert-specific",
    "robert specific",
    "protected photo",
    "private photo",
    "nude photo",
    "authorized adult anatomy reference",
)
IDENTITY_MEASUREMENT_KEYS = (
    "identity_measurement",
    "subject_measurement",
    "body_measurement",
    "height_cm",
    "height_m",
    "weight_kg",
    "waist_cm",
    "chest_cm",
    "hip_cm",
    "inseam_cm",
    "shoulder_width",
    "head_width",
    "face_landmark",
    "body_landmark",
    "likeness_measurement",
)
PERSON_COORDINATE_KEYS = (
    "coordinate",
    "coordinates",
    "vertex_indices",
    "face_indices",
    "root_positions",
    "root_coordinates",
    "vertex_delta",
    "vertex_deltas",
    "morph_delta",
    "morph_deltas",
    "person_specific_delta",
    "exact_delta",
)
ANATOMY_OBSERVATION_KEYS = (
    "anatomy_observation",
    "anatomy_observations",
    "anatomical_observation",
    "private_anatomy",
    "protected_anatomy",
    "pelvis_observation",
    "body_observation",
    "anatomy_notes",
)
REQUIRED_GENERALIZATION_RESULTS = (
    "topology",
    "visual_quality",
    "deformation_readiness",
    "private_data_exclusion",
    "runtime_nonmutation",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_digest(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _project_file(project_root: Path, raw: Any) -> Path | None:
    text = _text(raw)
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    lexical = project_root
    for part in candidate.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            return None
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(project_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _binding(
    project_root: Path,
    raw: Any,
    label: str,
    failures: list[str],
) -> tuple[Path | None, str]:
    if not isinstance(raw, Mapping):
        failures.append(f"{label}_binding_missing")
        return None, ""
    expected = _text(raw.get("sha256")).lower()
    if not _valid_digest(expected):
        failures.append(f"{label}_sha256_invalid")
    path = _project_file(project_root, raw.get("path"))
    if path is None:
        failures.append(f"{label}_path_invalid")
        return None, expected
    if _valid_digest(expected) and _sha256(path) != expected:
        failures.append(f"{label}_sha256_mismatch")
    return path, expected


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def private_payload_findings(value: Any) -> list[str]:
    """Return fail-closed findings without echoing sensitive values."""

    findings: list[str] = []

    def visit(current: Any, path: tuple[str, ...]) -> None:
        if isinstance(current, Mapping):
            for raw_key, child in current.items():
                key = _normalized(raw_key)
                key_path = ".".join((*path, key))
                if any(marker in key for marker in IDENTITY_MEASUREMENT_KEYS):
                    findings.append(
                        f"private_identity_measurement_key:{key_path}"
                    )
                if any(marker in key for marker in PERSON_COORDINATE_KEYS):
                    findings.append(
                        f"person_specific_coordinate_or_delta_key:{key_path}"
                    )
                if any(marker in key for marker in ANATOMY_OBSERVATION_KEYS):
                    findings.append(
                        f"private_anatomy_observation_key:{key_path}"
                    )
                visit(child, (*path, key))
            return
        if isinstance(current, (list, tuple)):
            for index, child in enumerate(current):
                visit(child, (*path, str(index)))
            return
        if not isinstance(current, str):
            return
        lowered = current.replace("\\", "/").lower()
        field = ".".join(path) or "root"
        if any(marker in lowered for marker in PRIVATE_PATH_MARKERS):
            findings.append(f"private_path_value:{field}")
        if any(marker in lowered for marker in PRIVATE_VALUE_MARKERS):
            findings.append(f"private_identity_or_observation_value:{field}")
        # A reusable definition should be deidentified.  "Robert" may appear
        # in the separate owner-approval record, never in the reusable payload
        # or non-private generalization proof.
        if re.search(r"\brobert\b", lowered):
            findings.append(f"person_specific_identity_value:{field}")

    visit(value, ())
    return _dedupe(findings)


def _owner_foundation_record(
    project_root: Path,
    binding: Any,
    failures: list[str],
) -> tuple[dict[str, Any], str]:
    path, digest = _binding(
        project_root,
        binding,
        "owner_foundation_record",
        failures,
    )
    if path is None:
        return {}, digest
    try:
        record = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("owner_foundation_record_unreadable")
        return {}, digest
    if record.get("schema_version") != 1:
        failures.append("owner_foundation_record_schema_invalid")
    if (
        _normalized(record.get("artifact_type"))
        != "biological_robert_static_foundation_owner_approval"
    ):
        failures.append("owner_foundation_record_type_invalid")
    if _normalized(record.get("status")) != "owner_approved_exact_foundation":
        failures.append("owner_foundation_status_not_approved")
    if _normalized(record.get("owner_authority_id")) != "real_robert":
        failures.append("owner_foundation_authority_invalid")
    if (
        _normalized(record.get("decision"))
        != "approve_biological_robert_static_foundation"
    ):
        failures.append("owner_foundation_decision_invalid")
    if _normalized(record.get("subject_id")) != "biological_robert":
        failures.append("owner_foundation_subject_invalid")
    if not _text(record.get("approved_at")):
        failures.append("owner_foundation_approval_time_missing")
    if record.get("private_source_paths_embedded") is not False:
        failures.append("owner_foundation_record_must_omit_private_paths")
    if record.get("movement_approved") is not False:
        failures.append("owner_foundation_must_not_imply_movement_approval")
    if record.get("runtime_activation_allowed") is not False:
        failures.append("owner_foundation_must_not_allow_runtime")
    _binding(
        project_root,
        record.get("foundation_artifact"),
        "owner_foundation_artifact",
        failures,
    )
    _binding(
        project_root,
        record.get("owner_review_manifest"),
        "owner_foundation_review_manifest",
        failures,
    )
    return record, digest


def _generalization_proof(
    project_root: Path,
    binding: Any,
    *,
    method_id: str,
    method_version: str,
    definition_sha256: str,
    minimum_subjects: int,
    failures: list[str],
) -> tuple[dict[str, Any], str]:
    path, digest = _binding(
        project_root,
        binding,
        "generalization_proof",
        failures,
    )
    if path is None:
        return {}, digest
    try:
        proof = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        failures.append("generalization_proof_unreadable")
        return {}, digest
    failures.extend(private_payload_findings(proof))
    if proof.get("schema_version") != 1:
        failures.append("generalization_proof_schema_invalid")
    if (
        _normalized(proof.get("artifact_type"))
        != "avatar_builder_reusable_method_generalization_proof"
    ):
        failures.append("generalization_proof_type_invalid")
    if _normalized(proof.get("status")) != "passed":
        failures.append("generalization_proof_status_not_passed")
    if _normalized(proof.get("method_id")) != method_id:
        failures.append("generalization_method_id_mismatch")
    if _text(proof.get("method_version")) != method_version:
        failures.append("generalization_method_version_mismatch")
    if _text(proof.get("method_definition_sha256")).lower() != definition_sha256:
        failures.append("generalization_definition_sha256_mismatch")
    author_id = _normalized(proof.get("method_author_id"))
    evaluator = proof.get("independent_evaluator")
    if not isinstance(evaluator, Mapping):
        failures.append("generalization_independent_evaluator_missing")
        evaluator = {}
    evaluator_id = _normalized(evaluator.get("id"))
    if (
        _normalized(evaluator.get("role"))
        != "independent_non_private_generalization_validator"
    ):
        failures.append("generalization_evaluator_role_invalid")
    if not evaluator_id:
        failures.append("generalization_evaluator_id_missing")
    if author_id and evaluator_id == author_id:
        failures.append("generalization_evaluator_not_independent")
    if not _text(proof.get("evaluated_at")):
        failures.append("generalization_evaluation_time_missing")

    fixtures = proof.get("fixtures")
    if not isinstance(fixtures, list):
        failures.append("generalization_fixtures_missing")
        fixtures = []
    fixture_ids: set[str] = set()
    for index, fixture in enumerate(fixtures):
        prefix = f"generalization_fixture_{index}"
        if not isinstance(fixture, Mapping):
            failures.append(f"{prefix}_invalid")
            continue
        fixture_id = _normalized(fixture.get("fixture_id"))
        if not fixture_id:
            failures.append(f"{prefix}_id_missing")
        fixture_ids.add(fixture_id)
        if (
            _normalized(fixture.get("identity_source_class"))
            != "non_private_synthetic_fixture"
        ):
            failures.append(f"{prefix}_identity_source_not_non_private")
        if fixture.get("private_data_used") is not False:
            failures.append(f"{prefix}_private_data_not_excluded")
        if fixture.get("person_specific_source_used") is not False:
            failures.append(f"{prefix}_person_specific_source_not_excluded")
        _binding(
            project_root,
            fixture.get("evidence"),
            f"{prefix}_evidence",
            failures,
        )
    if len(fixture_ids) < minimum_subjects:
        failures.append("generalization_distinct_fixture_count_too_low")

    results = proof.get("results")
    if not isinstance(results, Mapping):
        failures.append("generalization_results_missing")
        results = {}
    for result in REQUIRED_GENERALIZATION_RESULTS:
        if results.get(result) is not True:
            failures.append(f"generalization_result_not_passed:{result}")
    if proof.get("runtime_mutation_performed") is not False:
        failures.append("generalization_runtime_mutation_must_be_false")
    if proof.get("runtime_activation_allowed") is not False:
        failures.append("generalization_runtime_activation_must_be_false")
    if proof.get("public_export_allowed") is not False:
        failures.append("generalization_public_export_must_be_false")
    return proof, digest


def evaluate_reusable_method_promotion(
    project_root: Path,
    proposal: Mapping[str, Any] | None,
    *,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    """Evaluate one proposal without mutating the registry."""

    root = Path(project_root).resolve(strict=True)
    data = proposal if isinstance(proposal, Mapping) else {}
    failures: list[str] = []
    try:
        policy = _read_json(root / policy_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        policy = {}
        failures.append("reusable_method_policy_unreadable")
    if policy.get("schema_version") != 1:
        failures.append("reusable_method_policy_schema_invalid")
    if data.get("schema_version") != 1:
        failures.append("promotion_request_schema_invalid")
    if (
        _normalized(data.get("submission_type"))
        != "avatar_builder_reusable_method_promotion_request"
    ):
        failures.append("promotion_request_type_invalid")

    definition = data.get("method_definition")
    if not isinstance(definition, Mapping):
        failures.append("method_definition_missing")
        definition = {}
    failures.extend(private_payload_findings(definition))
    method_id = _normalized(definition.get("method_id"))
    method_version = _text(definition.get("method_version"))
    if not SAFE_ID_RE.fullmatch(method_id):
        failures.append("method_id_invalid")
    if not method_version:
        failures.append("method_version_missing")
    if (
        _normalized(definition.get("method_scope"))
        != "generic_avatar_builder_method"
    ):
        failures.append("method_scope_not_generic")
    if definition.get("person_specific") is not False:
        failures.append("method_person_specific_must_be_false")
    if definition.get("private_training_data_used") is not False:
        failures.append("method_private_training_data_not_excluded")
    definition_sha256 = canonical_sha256(definition)
    if not definition_sha256:
        failures.append("method_definition_not_canonical_json")

    implementation_path, implementation_sha256 = _binding(
        root,
        definition.get("implementation"),
        "method_implementation",
        failures,
    )
    allowed_root_text = _text(
        policy.get(
            "allowed_implementation_root",
            "Avatar/avatar_builder/tooling/reusable_methods",
        )
    )
    allowed_root = (root / allowed_root_text).resolve()
    if implementation_path is not None:
        try:
            implementation_path.relative_to(allowed_root)
        except ValueError:
            failures.append("method_implementation_outside_generic_root")
        try:
            implementation_relative = implementation_path.relative_to(root)
        except ValueError:
            implementation_relative = implementation_path
        if any(
            marker in str(implementation_relative).replace("\\", "/").lower()
            for marker in (*PRIVATE_PATH_MARKERS, "robert")
        ):
            failures.append("method_implementation_path_is_person_specific")
        try:
            implementation_text = implementation_path.read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeError):
            failures.append("method_implementation_text_unreadable")
        else:
            failures.extend(
                private_payload_findings(
                    {"implementation_text": implementation_text}
                )
            )

    _record, owner_record_sha256 = _owner_foundation_record(
        root,
        data.get("owner_approved_foundation_record"),
        failures,
    )
    _proof, generalization_sha256 = _generalization_proof(
        root,
        data.get("generalization_proof"),
        method_id=method_id,
        method_version=method_version,
        definition_sha256=definition_sha256,
        minimum_subjects=max(
            1,
            int(policy.get("minimum_distinct_non_private_fixtures", 2)),
        ),
        failures=failures,
    )
    if data.get("runtime_mutation_requested") is not False:
        failures.append("promotion_request_runtime_mutation_must_be_false")
    if data.get("public_export_requested") is not False:
        failures.append("promotion_request_public_export_must_be_false")

    failures = _dedupe(failures)
    passed = not failures
    return {
        "schema_version": 1,
        "gate": "avatar_builder_reusable_method_promotion_v1",
        "status": (
            "promotion_eligible_not_yet_registered"
            if passed
            else "promotion_blocked"
        ),
        "promotion_allowed": passed,
        "selectable": False,
        "method_id": method_id,
        "method_version": method_version,
        "method_definition_sha256": definition_sha256,
        "implementation_sha256": implementation_sha256,
        "owner_foundation_record_sha256": owner_record_sha256,
        "generalization_proof_sha256": generalization_sha256,
        "failures": failures,
        "raw_private_payload_retained": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "A passing evaluation is still not selectable until the exact safe "
            "summary is explicitly written to the reusable registry."
        ),
    }


def load_registry(
    project_root: Path,
    *,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    return _read_json(root / registry_path)


def evaluate_reusable_method_selection(
    project_root: Path,
    method_id: Any,
    *,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    """Return pass only for a promoted, selectable, non-revoked method."""

    selected = _normalized(method_id)
    if not selected:
        return {
            "gate_id": "reusable_method_selection",
            "status": "not_requested",
            "passed": True,
            "method_id": "",
            "failures": [],
        }
    failures: list[str] = []
    try:
        registry = load_registry(project_root, registry_path=registry_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        registry = {}
        failures.append("reusable_method_registry_unreadable")
    entries = registry.get("selectable_methods")
    if not isinstance(entries, list):
        failures.append("reusable_method_registry_entries_invalid")
        entries = []
    matching = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and _normalized(entry.get("method_id")) == selected
    ]
    if len(matching) != 1:
        failures.append("reusable_method_not_selectable")
        entry: Mapping[str, Any] = {}
    else:
        entry = matching[0]
        if _normalized(entry.get("status")) != "promoted_reusable":
            failures.append("reusable_method_status_not_promoted")
        if entry.get("selectable") is not True:
            failures.append("reusable_method_selectable_flag_not_true")
        if entry.get("revoked") is not False:
            failures.append("reusable_method_revoked_or_revocation_missing")
        for field in (
            "method_definition_sha256",
            "implementation_sha256",
            "owner_foundation_record_sha256",
            "generalization_proof_sha256",
        ):
            if not _valid_digest(entry.get(field)):
                failures.append(f"reusable_method_{field}_invalid")
    failures = _dedupe(failures)
    return {
        "gate_id": "reusable_method_selection",
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "method_id": selected,
        "failures": failures,
    }


def promoted_registry_entry(
    proposal: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    *,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    """Build a safe summary; refuse to promote a failed or altered proposal."""

    if evaluation.get("promotion_allowed") is not True:
        raise ValueError("promotion evaluation did not pass")
    definition = proposal.get("method_definition")
    if not isinstance(definition, Mapping):
        raise ValueError("method definition missing")
    if private_payload_findings(definition):
        raise ValueError("method definition contains private/person-specific data")
    digest = canonical_sha256(definition)
    if digest != _text(evaluation.get("method_definition_sha256")).lower():
        raise ValueError("method definition changed after evaluation")
    return {
        "method_id": _normalized(evaluation.get("method_id")),
        "method_version": _text(evaluation.get("method_version")),
        "status": "PROMOTED_REUSABLE",
        "selectable": True,
        "revoked": False,
        "promoted_at": promoted_at
        or datetime.now(timezone.utc).isoformat(),
        "method_definition_sha256": digest,
        "implementation_sha256": _text(
            evaluation.get("implementation_sha256")
        ).lower(),
        "owner_foundation_record_sha256": _text(
            evaluation.get("owner_foundation_record_sha256")
        ).lower(),
        "generalization_proof_sha256": _text(
            evaluation.get("generalization_proof_sha256")
        ).lower(),
        "raw_payload_stored": False,
        "private_data_stored": False,
        "runtime_activation_allowed": False,
    }


def archived_rejection_entry(
    proposal: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any],
    *,
    archived_at: str | None = None,
) -> dict[str, Any]:
    """Archive only a fingerprint and failure codes, never the raw payload."""

    data = proposal if isinstance(proposal, Mapping) else {}
    fingerprint = canonical_sha256(data)
    findings = private_payload_findings(data)
    definition = data.get("method_definition")
    method_id = ""
    if isinstance(definition, Mapping) and not private_payload_findings(
        definition
    ):
        candidate = _normalized(definition.get("method_id"))
        if SAFE_ID_RE.fullmatch(candidate):
            method_id = candidate
    return {
        "archive_id": f"rejected_{fingerprint[:20] or 'invalid_payload'}",
        "method_id": method_id,
        "method_fingerprint_sha256": fingerprint,
        "status": "REJECTED_ARCHIVED_NOT_SELECTABLE",
        "selectable": False,
        "archived_at": archived_at
        or datetime.now(timezone.utc).isoformat(),
        "failure_codes": _dedupe(
            [
                _text(value)
                for value in evaluation.get("failures", [])
                if _text(value)
            ]
        ),
        "private_payload_detected": bool(findings),
        "raw_payload_stored": False,
        "private_data_stored": False,
        "evidence_retention": "PRIVATE EVIDENCE REMAINS OUTSIDE THIS REGISTRY",
    }


def registry_with_promoted_method(
    registry: Mapping[str, Any],
    proposal: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    *,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    updated = deepcopy(dict(registry))
    entries = updated.setdefault("selectable_methods", [])
    if not isinstance(entries, list):
        raise ValueError("registry selectable_methods must be a list")
    entry = promoted_registry_entry(
        proposal,
        evaluation,
        promoted_at=promoted_at,
    )
    if any(
        isinstance(existing, Mapping)
        and _normalized(existing.get("method_id")) == entry["method_id"]
        for existing in entries
    ):
        raise ValueError("method id already exists in reusable registry")
    entries.append(entry)
    return updated


def registry_with_archived_rejection(
    registry: Mapping[str, Any],
    proposal: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any],
    *,
    archived_at: str | None = None,
) -> dict[str, Any]:
    updated = deepcopy(dict(registry))
    archive = updated.setdefault("rejected_method_archive", [])
    if not isinstance(archive, list):
        raise ValueError("registry rejected_method_archive must be a list")
    archive.append(
        archived_rejection_entry(
            proposal,
            evaluation,
            archived_at=archived_at,
        )
    )
    return updated


__all__ = [
    "POLICY_PATH",
    "REGISTRY_PATH",
    "archived_rejection_entry",
    "canonical_sha256",
    "evaluate_reusable_method_promotion",
    "evaluate_reusable_method_selection",
    "load_registry",
    "private_payload_findings",
    "promoted_registry_entry",
    "registry_with_archived_rejection",
    "registry_with_promoted_method",
]
