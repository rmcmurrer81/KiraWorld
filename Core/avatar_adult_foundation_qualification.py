"""Read-only, fail-closed qualification for adult avatar foundations.

Adult maturity is an eligibility lane, not geometry proof.  This module keeps
three decisions separate:

* whether a source is eligible for the confirmed-adult female lane;
* whether its license and enrolled role permit foundation use; and
* whether exact-hash independent evidence proves complete connected topology.

The evaluator does not build, render, copy, stage, select, or activate a body.
Known registry blockers are evidence, not caller-overridable warnings.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping


POLICY_PATH = Path(
    "Avatar/avatar_builder/policies/adult_foundation_qualification_v1.json"
)
REGISTRY_PATH = Path(
    "Avatar/avatar_builder/policies/adult_foundation_registry_v1.json"
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,127}$")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _valid_digest(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value).lower()))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _io_path(path: Path) -> Path:
    """Return a Windows extended-length path without changing its identity."""

    absolute = os.path.abspath(path)
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return Path(absolute)
    if absolute.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + absolute[2:])
    return Path("\\\\?\\" + absolute)


def _is_link_or_junction(path: Path) -> bool:
    metadata = os.lstat(path)
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _project_file(project_root: Path, raw: Any) -> Path | None:
    value = _text(raw)
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root_text = os.path.abspath(project_root)
    candidate_text = os.path.abspath(os.path.join(root_text, *candidate.parts))
    try:
        if os.path.commonpath((root_text, candidate_text)) != root_text:
            return None
    except ValueError:
        return None
    lexical = Path(root_text)
    for part in candidate.parts:
        lexical = lexical / part
        try:
            linked_or_reparsed = _is_link_or_junction(_io_path(lexical))
        except OSError:
            return None
        if linked_or_reparsed:
            return None
    resolved = _io_path(Path(candidate_text))
    try:
        metadata = os.lstat(resolved)
    except OSError:
        return None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_nlink", 1) != 1
    ):
        return None
    return resolved


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _binding(
    project_root: Path,
    raw: Any,
    label: str,
    blockers: list[str],
) -> tuple[Path | None, str]:
    if not isinstance(raw, Mapping):
        blockers.append(f"{label}_binding_missing")
        return None, ""
    expected = _text(raw.get("sha256")).lower()
    if not _valid_digest(expected):
        blockers.append(f"{label}_sha256_invalid")
    path = _project_file(project_root, raw.get("path"))
    if path is None:
        blockers.append(f"{label}_path_invalid")
        return None, expected
    if _valid_digest(expected) and _sha256(path) != expected:
        blockers.append(f"{label}_sha256_mismatch")
    return path, expected


def _bound_json(
    project_root: Path,
    raw: Any,
    label: str,
    blockers: list[str],
) -> tuple[dict[str, Any], str]:
    path, digest = _binding(project_root, raw, label, blockers)
    if path is None:
        return {}, digest
    try:
        return _read_json(path), digest
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        blockers.append(f"{label}_unreadable")
        return {}, digest


def _load_policy(
    project_root: Path,
    policy_path: Path,
    blockers: list[str],
) -> dict[str, Any]:
    path = _project_file(project_root, policy_path.as_posix())
    if path is None:
        blockers.append("adult_foundation_policy_path_invalid")
        return {}
    try:
        policy = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        blockers.append("adult_foundation_policy_unreadable")
        return {}
    if policy.get("schema_version") != 1:
        blockers.append("adult_foundation_policy_schema_invalid")
    if (
        _normalized(policy.get("policy_id"))
        != "avatar_builder_adult_foundation_qualification_v1"
    ):
        blockers.append("adult_foundation_policy_id_invalid")
    if not isinstance(policy.get("required_topology_metrics"), Mapping):
        blockers.append("adult_foundation_policy_topology_metrics_invalid")
    roles = policy.get("allowed_foundation_roles")
    if not isinstance(roles, list) or not roles:
        blockers.append("adult_foundation_policy_allowed_roles_invalid")
    artifact_kinds = policy.get("allowed_artifact_kinds")
    if not isinstance(artifact_kinds, list) or not artifact_kinds:
        blockers.append("adult_foundation_policy_artifact_kinds_invalid")
    relationships = policy.get("required_adult_female_relationships")
    if not isinstance(relationships, list) or not relationships:
        blockers.append("adult_foundation_policy_relationships_invalid")
    assertions = policy.get("required_relationship_assertions")
    if not isinstance(assertions, list) or not assertions:
        blockers.append("adult_foundation_policy_assertions_invalid")
    negatives = policy.get("required_negative_findings")
    if not isinstance(negatives, Mapping) or not negatives:
        blockers.append("adult_foundation_policy_negative_findings_invalid")
    independent = policy.get("independent_evidence")
    if not isinstance(independent, Mapping):
        blockers.append("adult_foundation_policy_independent_evidence_invalid")
    return policy


def _load_registry(
    project_root: Path,
    registry_path: Path,
    policy_path: Path,
    blockers: list[str],
) -> dict[str, Any]:
    path = _project_file(project_root, registry_path.as_posix())
    if path is None:
        blockers.append("adult_foundation_registry_path_invalid")
        return {}
    try:
        registry = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        blockers.append("adult_foundation_registry_unreadable")
        return {}
    if registry.get("schema_version") != 1:
        blockers.append("adult_foundation_registry_schema_invalid")
    if (
        _normalized(registry.get("registry_id"))
        != "avatar_builder_adult_foundation_registry_v1"
    ):
        blockers.append("adult_foundation_registry_id_invalid")
    if _text(registry.get("policy")) != policy_path.as_posix():
        blockers.append("adult_foundation_registry_policy_mismatch")
    if not isinstance(registry.get("entries"), list):
        blockers.append("adult_foundation_registry_entries_invalid")
    return registry


def _registered_entry(
    registry: Mapping[str, Any],
    foundation_id: str,
    blockers: list[str],
) -> dict[str, Any]:
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return {}
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and _normalized(entry.get("foundation_id")) == foundation_id
    ]
    if not matches:
        blockers.append("foundation_not_registered")
        return {}
    if len(matches) != 1:
        blockers.append("foundation_registry_id_not_unique")
        return {}
    return dict(matches[0])


def _evaluate_adult_eligibility(
    entry: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[bool, list[str], str]:
    blockers: list[str] = []
    maturity = entry.get("maturity")
    if not isinstance(maturity, Mapping):
        blockers.append("adult_maturity_record_missing")
        maturity = {}
    required_status = _normalized(policy.get("required_maturity_status"))
    if _normalized(maturity.get("status")) != required_status:
        blockers.append("adult_maturity_not_confirmed")
    required_class = _normalized(policy.get("requested_body_class"))
    body_class = _normalized(maturity.get("body_class"))
    if body_class != required_class:
        blockers.append("adult_body_class_mismatch")
    return not blockers, blockers, body_class


def _valid_http_url(value: Any) -> bool:
    text = _text(value).lower()
    return text.startswith("https://") or text.startswith("http://")


def _evaluate_foundation_authority(
    project_root: Path,
    entry: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[bool, list[str], str, str]:
    blockers: list[str] = []
    _source_path, source_sha256 = _binding(
        project_root,
        entry.get("source_artifact"),
        "source_artifact",
        blockers,
    )

    artifact_kind = _normalized(entry.get("artifact_kind"))
    allowed_artifact_kinds = {
        _normalized(value)
        for value in policy.get("allowed_artifact_kinds", [])
    }
    if artifact_kind not in allowed_artifact_kinds:
        blockers.append(
            f"source_artifact_kind_not_allowed:{artifact_kind or 'missing'}"
        )
    source_configuration = entry.get("source_configuration_artifacts")
    if not isinstance(source_configuration, list):
        blockers.append("source_configuration_artifacts_invalid")
        source_configuration = []
    if (
        artifact_kind == "parametric_source_set"
        and policy.get("parametric_source_configuration_required") is True
        and not source_configuration
    ):
        blockers.append("parametric_source_configuration_missing")
    for index, configuration_binding in enumerate(source_configuration):
        _binding(
            project_root,
            configuration_binding,
            f"source_configuration_artifact_{index}",
            blockers,
        )

    provenance = entry.get("source_provenance")
    if not isinstance(provenance, Mapping):
        blockers.append("source_provenance_missing")
        provenance = {}
    if not _text(provenance.get("title")):
        blockers.append("source_title_missing")
    if not _text(provenance.get("author")):
        blockers.append("source_author_missing")
    if not _valid_http_url(provenance.get("source_url")):
        blockers.append("source_url_missing_or_invalid")

    role = _normalized(entry.get("foundation_role"))
    allowed_roles = {
        _normalized(value)
        for value in policy.get("allowed_foundation_roles", [])
    }
    if role not in allowed_roles:
        blockers.append(f"foundation_role_not_allowed:{role or 'missing'}")

    candidate_use = entry.get("candidate_use")
    if not isinstance(candidate_use, Mapping):
        blockers.append("candidate_use_authority_missing")
        candidate_use = {}
    if (
        candidate_use.get("new_surface_derivative_allowed") is not True
        and candidate_use.get("copy_as_candidate_body_allowed") is not True
    ):
        blockers.append("candidate_foundation_use_not_authorized")

    license_record = entry.get("license")
    if not isinstance(license_record, Mapping):
        blockers.append("license_record_missing")
        license_record = {}
    if not _text(license_record.get("id")):
        blockers.append("license_id_missing")
    if not _valid_http_url(license_record.get("url")):
        blockers.append("license_url_missing_or_invalid")
    if license_record.get("adaptation_allowed") is not True:
        blockers.append("license_adaptation_not_allowed")
    if license_record.get("foundation_use_allowed") is not True:
        blockers.append("license_foundation_use_not_allowed")
    _binding(
        project_root,
        license_record.get("evidence"),
        "license_evidence",
        blockers,
    )
    return not blockers, blockers, role, source_sha256


def _known_registry_blockers(
    project_root: Path,
    entry: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    findings = entry.get("known_blockers")
    if not isinstance(findings, list):
        blockers.append("registry_known_blockers_record_missing")
        return blockers
    for index, finding in enumerate(findings):
        label = f"known_blocker_{index}_evidence"
        if not isinstance(finding, Mapping):
            blockers.append(f"registry_known_blocker_record_invalid:{index}")
            continue
        code = _normalized(finding.get("code"))
        if not code:
            blockers.append(f"registry_known_blocker_code_missing:{index}")
        else:
            blockers.append(f"registry_known_blocker:{code}")
        _binding(project_root, finding.get("evidence"), label, blockers)
    return blockers


def _independent_reviewer(
    report: Mapping[str, Any],
    *,
    expected_role: str,
    label: str,
    blockers: list[str],
) -> None:
    reviewer = report.get("independent_reviewer")
    if not isinstance(reviewer, Mapping):
        blockers.append(f"{label}_independent_reviewer_missing")
        reviewer = {}
    reviewer_id = _normalized(reviewer.get("id"))
    author_id = _normalized(report.get("candidate_author_id"))
    if not reviewer_id:
        blockers.append(f"{label}_reviewer_id_missing")
    if _normalized(reviewer.get("role")) != expected_role:
        blockers.append(f"{label}_reviewer_role_invalid")
    if not author_id:
        blockers.append(f"{label}_candidate_author_id_missing")
    if reviewer_id and author_id and reviewer_id == author_id:
        blockers.append(f"{label}_reviewer_not_independent")
    if not _text(report.get("reviewed_at")):
        blockers.append(f"{label}_review_time_missing")


def _validate_topology_report(
    project_root: Path,
    binding: Any,
    *,
    source_sha256: str,
    body_class: str,
    policy: Mapping[str, Any],
) -> tuple[bool, list[str], str]:
    blockers: list[str] = []
    if not isinstance(binding, Mapping):
        blockers.append("independent_topology_evidence_missing")
        return False, blockers, ""
    report, digest = _bound_json(
        project_root,
        binding,
        "independent_topology_evidence",
        blockers,
    )
    independent = policy.get("independent_evidence")
    if not isinstance(independent, Mapping):
        independent = {}
    if report.get("schema_version") != 1:
        blockers.append("topology_report_schema_invalid")
    if _normalized(report.get("artifact_type")) != _normalized(
        independent.get("topology_artifact_type")
    ):
        blockers.append("topology_report_type_invalid")
    if _normalized(report.get("status")) != "passed" or report.get(
        "passed"
    ) is not True:
        blockers.append("topology_report_not_passed")
    report_artifact_sha256 = _text(report.get("artifact_sha256")).lower()
    if not _valid_digest(source_sha256):
        blockers.append("topology_source_sha256_invalid")
    if not _valid_digest(report_artifact_sha256):
        blockers.append("topology_report_artifact_sha256_invalid")
    if report_artifact_sha256 != source_sha256:
        blockers.append("topology_report_artifact_sha256_mismatch")
    required_body_class = _normalized(policy.get("requested_body_class"))
    if body_class != required_body_class:
        blockers.append("topology_candidate_body_class_invalid")
    if _normalized(report.get("body_class")) != body_class:
        blockers.append("topology_report_body_class_mismatch")
    if report.get("exact_artifact_sha256_verified") is not True:
        blockers.append("topology_report_exact_hash_not_verified")
    if report.get("complete_scan") is not True:
        blockers.append("topology_report_complete_scan_missing")
    _independent_reviewer(
        report,
        expected_role=_normalized(independent.get("topology_auditor_role")),
        label="topology_report",
        blockers=blockers,
    )
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        blockers.append("topology_report_metrics_missing")
        metrics = {}
    required_metrics = policy.get("required_topology_metrics")
    if not isinstance(required_metrics, Mapping):
        required_metrics = {}
    for name, expected in required_metrics.items():
        value = metrics.get(name)
        if isinstance(expected, bool) or not isinstance(expected, int):
            blockers.append(f"topology_policy_metric_invalid:{name}")
        elif isinstance(value, bool) or not isinstance(value, int):
            blockers.append(f"topology_metric_missing_or_invalid:{name}")
        elif value != expected:
            blockers.append(f"topology_metric_not_satisfied:{name}")
    return not blockers, blockers, digest


def _validate_relationship_report(
    project_root: Path,
    binding: Any,
    *,
    source_sha256: str,
    body_class: str,
    policy: Mapping[str, Any],
) -> tuple[bool, list[str], str, dict[str, bool]]:
    blockers: list[str] = []
    relationship_results: dict[str, bool] = {}
    if not isinstance(binding, Mapping):
        blockers.append("independent_relationship_evidence_missing")
        return False, blockers, "", relationship_results
    report, digest = _bound_json(
        project_root,
        binding,
        "independent_relationship_evidence",
        blockers,
    )
    independent = policy.get("independent_evidence")
    if not isinstance(independent, Mapping):
        independent = {}
    if report.get("schema_version") != 1:
        blockers.append("relationship_report_schema_invalid")
    if _normalized(report.get("artifact_type")) != _normalized(
        independent.get("relationship_artifact_type")
    ):
        blockers.append("relationship_report_type_invalid")
    if _normalized(report.get("status")) != "passed" or report.get(
        "passed"
    ) is not True:
        blockers.append("relationship_report_not_passed")
    report_artifact_sha256 = _text(report.get("artifact_sha256")).lower()
    if not _valid_digest(source_sha256):
        blockers.append("relationship_source_sha256_invalid")
    if not _valid_digest(report_artifact_sha256):
        blockers.append("relationship_report_artifact_sha256_invalid")
    if report_artifact_sha256 != source_sha256:
        blockers.append("relationship_report_artifact_sha256_mismatch")
    required_body_class = _normalized(policy.get("requested_body_class"))
    if body_class != required_body_class:
        blockers.append("relationship_candidate_body_class_invalid")
    if _normalized(report.get("body_class")) != body_class:
        blockers.append("relationship_report_body_class_mismatch")
    if report.get("exact_artifact_sha256_verified") is not True:
        blockers.append("relationship_report_exact_hash_not_verified")
    _independent_reviewer(
        report,
        expected_role=_normalized(
            independent.get("relationship_reviewer_role")
        ),
        label="relationship_report",
        blockers=blockers,
    )

    records = report.get("relationships")
    if not isinstance(records, Mapping):
        blockers.append("relationship_records_missing")
        records = {}
    required = policy.get("required_adult_female_relationships")
    if not isinstance(required, list):
        required = []
    assertions = policy.get("required_relationship_assertions")
    if not isinstance(assertions, list):
        assertions = []
    for raw_name in required:
        name = _normalized(raw_name)
        record = records.get(name)
        relationship_passed = isinstance(record, Mapping)
        if not isinstance(record, Mapping):
            blockers.append(f"relationship_record_missing:{name}")
            record = {}
        for raw_assertion in assertions:
            assertion = _normalized(raw_assertion)
            if record.get(assertion) is not True:
                blockers.append(f"relationship_not_proven:{name}:{assertion}")
                relationship_passed = False
        relationship_results[name] = relationship_passed

    negative_findings = report.get("negative_findings")
    if not isinstance(negative_findings, Mapping):
        blockers.append("relationship_negative_findings_missing")
        negative_findings = {}
    required_negative = policy.get("required_negative_findings")
    if not isinstance(required_negative, Mapping):
        required_negative = {}
    for raw_name, expected in required_negative.items():
        name = _normalized(raw_name)
        if negative_findings.get(name) is not expected:
            blockers.append(
                f"relationship_negative_finding_not_satisfied:{name}"
            )
    return not blockers, blockers, digest, relationship_results


def evaluate_adult_foundation_qualification(
    project_root: Path,
    foundation_id: Any,
    *,
    independent_evidence: Mapping[str, Any] | None = None,
    policy_path: Path = POLICY_PATH,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    """Evaluate one registered source without performing any mutation."""

    root = Path(project_root).resolve(strict=True)
    normalized_id = _normalized(foundation_id)
    global_blockers: list[str] = []
    if not SAFE_ID_RE.fullmatch(normalized_id):
        global_blockers.append("foundation_id_invalid")
    policy = _load_policy(root, policy_path, global_blockers)
    registry = _load_registry(
        root,
        registry_path,
        policy_path,
        global_blockers,
    )
    entry = _registered_entry(registry, normalized_id, global_blockers)

    adult_eligible, adult_blockers, body_class = (
        _evaluate_adult_eligibility(entry, policy)
        if entry
        else (False, ["adult_eligibility_not_evaluable"], "")
    )
    authority_ok, authority_blockers, role, source_sha256 = (
        _evaluate_foundation_authority(root, entry, policy)
        if entry
        else (
            False,
            ["foundation_authority_not_evaluable"],
            "",
            "",
        )
    )

    topology_blockers = (
        _known_registry_blockers(root, entry)
        if entry
        else ["complete_topology_not_evaluable"]
    )
    evidence = independent_evidence
    if not isinstance(evidence, Mapping) and entry:
        stored = entry.get("positive_independent_evidence")
        evidence = stored if isinstance(stored, Mapping) else {}
    if not isinstance(evidence, Mapping):
        evidence = {}

    topology_passed, topology_report_blockers, topology_digest = (
        _validate_topology_report(
            root,
            evidence.get("topology"),
            source_sha256=source_sha256,
            body_class=body_class,
            policy=policy,
        )
    )
    relationship_passed, relationship_blockers, relationship_digest, relationships = (
        _validate_relationship_report(
            root,
            evidence.get("relationships"),
            source_sha256=source_sha256,
            body_class=body_class,
            policy=policy,
        )
    )
    topology_blockers.extend(topology_report_blockers)
    topology_blockers.extend(relationship_blockers)
    topology_blockers = _dedupe(topology_blockers)
    complete_topology_proven = bool(
        entry
        and topology_passed
        and relationship_passed
        and not topology_blockers
    )

    global_blockers = _dedupe(global_blockers)
    adult_blockers = _dedupe(adult_blockers)
    authority_blockers = _dedupe(authority_blockers)
    all_blockers = _dedupe(
        global_blockers
        + adult_blockers
        + authority_blockers
        + topology_blockers
    )
    qualified = bool(
        not global_blockers
        and adult_eligible
        and authority_ok
        and complete_topology_proven
        and not all_blockers
    )
    return {
        "schema_version": 1,
        "gate": "avatar_builder_adult_foundation_qualification_v1",
        "foundation_id": normalized_id,
        "status": "qualified" if qualified else "blocked_not_qualified",
        "qualified_for_adult_foundation": qualified,
        "adult_eligible": adult_eligible,
        "complete_adult_topology_proven": complete_topology_proven,
        "adult_eligibility": {
            "eligible": adult_eligible,
            "body_class": body_class,
            "blockers": adult_blockers,
            "truth_note": (
                "Confirmed-adult eligibility is a maturity decision only."
            ),
        },
        "foundation_authority": {
            "authorized": authority_ok,
            "foundation_role": role,
            "source_artifact_sha256": source_sha256,
            "blockers": authority_blockers,
        },
        "complete_topology": {
            "proven": complete_topology_proven,
            "topology_report_sha256": topology_digest,
            "relationship_report_sha256": relationship_digest,
            "relationships": relationships,
            "blockers": topology_blockers,
        },
        "blockers": all_blockers,
        "build_performed": False,
        "render_performed": False,
        "runtime_mutation_performed": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "truth_note": (
            "A source qualifies only when maturity, licensed foundation role, "
            "and exact-hash independent complete-topology evidence all pass."
        ),
    }


def audit_registered_adult_foundations(
    project_root: Path,
    *,
    policy_path: Path = POLICY_PATH,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    """Return a read-only snapshot for every enrolled foundation source."""

    root = Path(project_root).resolve(strict=True)
    blockers: list[str] = []
    policy = _load_policy(root, policy_path, blockers)
    registry = _load_registry(
        root,
        registry_path,
        policy_path,
        blockers,
    )
    entries = registry.get("entries") if isinstance(registry, Mapping) else []
    ids = [
        _normalized(entry.get("foundation_id"))
        for entry in entries
        if isinstance(entry, Mapping)
    ] if isinstance(entries, list) else []
    results = [
        evaluate_adult_foundation_qualification(
            root,
            foundation_id,
            policy_path=policy_path,
            registry_path=registry_path,
        )
        for foundation_id in ids
    ]
    qualified_count = sum(
        result.get("qualified_for_adult_foundation") is True
        for result in results
    )
    return {
        "schema_version": 1,
        "audit": "avatar_builder_registered_adult_foundations_v1",
        "registry_id": _text(registry.get("registry_id")),
        "policy_id": _text(policy.get("policy_id")),
        "registered_count": len(results),
        "qualified_count": qualified_count,
        "status": "qualified_sources_present" if qualified_count else "no_qualified_sources",
        "blockers": _dedupe(blockers),
        "results": results,
        "build_performed": False,
        "render_performed": False,
        "runtime_mutation_performed": False,
    }


__all__ = [
    "POLICY_PATH",
    "REGISTRY_PATH",
    "audit_registered_adult_foundations",
    "evaluate_adult_foundation_qualification",
]
