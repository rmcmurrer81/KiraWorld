"""Static quality contract for new TemporaryAI creator candidates.

This module prepares and validates review evidence only.  It never calls a
model, activates or assigns a candidate, creates a body or voice, opens
Blender, or authorizes a live route.  Fictional/historical variants and expert
candidates remain private, inactive, and unassigned even when every static
quality-planning gate passes.

Version 2 is additive to :mod:`Core.temporary_ai_variant_identity`.  The older
record remains useful continuity evidence; this successor adds exact model
identity, source provenance, maturity authority, epistemic separation,
append-only owner-correction revisions, and an expert competency battery.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from Core.model_request_policy import QWEN_TEXT_VOICE_DIGEST, QWEN_TEXT_VOICE_MODEL


SCHEMA_VERSION = 2
RECORD_KIND = "temporary_ai_creator_qwen35_quality_record_v2"
PRIVATE_LIFECYCLE_STATUS = "PRIVATE_INACTIVE_UNASSIGNED_STATIC_ONLY"
READY_STATUS = "STATIC_QUALITY_PLAN_READY_PRIVATE_INACTIVE_UNASSIGNED"
BLOCKED_STATUS = "STATIC_QUALITY_PLAN_BLOCKED_PRIVATE_INACTIVE_UNASSIGNED"

EXACT_QWEN_MODEL = "qwen3.5:9b"
EXACT_QWEN_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
if (
    QWEN_TEXT_VOICE_MODEL != EXACT_QWEN_MODEL
    or QWEN_TEXT_VOICE_DIGEST != EXACT_QWEN_DIGEST
):
    raise RuntimeError("TemporaryAI quality-v2 exact Qwen identity drifted")

IN_SCOPE_AI_TYPES = frozenset(
    {
        "canon_reconstruction_temp_ai",
        "expert_temp_ai",
    }
)
VARIANT_KINDS = frozenset({"fictional", "historical"})
EXPECTED_IDENTITY_CLASSIFICATION = {
    ("canon_reconstruction_temp_ai", "fictional"): "synthetic_fictional_variant",
    ("canon_reconstruction_temp_ai", "historical"): "synthetic_historical_variant",
    ("expert_temp_ai", "expert"): "generated_original_expert",
}
MATURITY_STATUSES = frozenset({"confirmed_adult", "non_adult", "unresolved"})
MATURITY_AUTHORITIES = frozenset(
    {
        "canonical_source_classification",
        "exact_subject_owner_classification",
        "exact_subject_owner_correction",
    }
)
SOURCE_CLASSES = frozenset(
    {
        "primary_canon",
        "primary_historical",
        "official_domain_source",
        "authoritative_secondary",
        "reviewed_tertiary_lead_only",
    }
)
AUTHORITY_TIERS = frozenset(
    {
        "primary_or_official",
        "authoritative_secondary",
        "tertiary_lead_only",
    }
)
EPISTEMIC_CLASSES = (
    "canon_facts",
    "reconstructions",
    "inferences",
    "uncertainties",
)
EPISTEMIC_LABELS = {
    "canon_facts": "canon_fact",
    "reconstructions": "reconstruction",
    "inferences": "inference",
    "uncertainties": "uncertainty",
}
CONFIDENCE_VALUES = frozenset({"high", "medium", "low", "unknown"})
REQUIRED_EXPERT_CASE_KINDS = (
    "domain_knowledge",
    "applied_reasoning",
    "source_grounding",
    "ignorance_boundary",
    "uncertainty_calibration",
    "correction_response",
)
CORRECTABLE_IDENTITY_FIELDS = frozenset(
    {
        "canonical_identity",
        "source_continuity",
        "source_version",
        "source_timepoint",
        "branch_point",
        "maturity_classification",
    }
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,159}$")
UTC_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
GENERIC_DOMAIN_VALUES = frozenset(
    {
        "",
        "expert",
        "general",
        "general knowledge",
        "knowledge",
        "everything",
        "assistant",
    }
)


class CreatorQualityError(ValueError):
    """Raised when a canonical record or append-only revision is invalid."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the sole accepted UTF-8 representation for a quality record."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CreatorQualityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_canonical_quality_record(path: Path) -> dict[str, Any]:
    """Load one strict, canonical object; reject duplicates and JSON constants."""

    raw = path.read_bytes()

    def reject_constant(value: str) -> Any:
        raise CreatorQualityError(f"non-standard JSON constant: {value}")

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreatorQualityError("quality record must be strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise CreatorQualityError("quality record must contain exactly one object")
    if raw != canonical_json_bytes(payload):
        raise CreatorQualityError("quality record bytes are not canonical")
    gate_issues = quality_record_issues(payload)
    if any(issue.startswith("declared_gate_") for issue in gate_issues):
        raise CreatorQualityError("quality record has a false or stale declared gate")
    return payload


def write_quality_revision_exclusive(path: Path, record: Mapping[str, Any]) -> str:
    """Create one canonical revision without overwriting prior evidence."""

    payload = copy.deepcopy(dict(record))
    issues = quality_record_issues(payload)
    if any(issue.startswith("declared_gate_") for issue in issues):
        raise CreatorQualityError("quality record declared gate is inconsistent")
    encoded = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and SAFE_ID_RE.fullmatch(value) is not None


def _valid_utc_z(value: Any) -> bool:
    if not isinstance(value, str) or UTC_Z_RE.fullmatch(value) is None:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0)


def _parse_utc_z(value: Any) -> dt.datetime | None:
    if not _valid_utc_z(value):
        return None
    return dt.datetime.fromisoformat(str(value)[:-1] + "+00:00")


def private_lifecycle() -> dict[str, Any]:
    return {
        "status": PRIVATE_LIFECYCLE_STATUS,
        "visibility": "project_private",
        "activation_allowed": False,
        "assignment_allowed": False,
        "publication_allowed": False,
        "runtime_registration_allowed": False,
        "body_authoring_allowed": False,
        "voice_generation_or_assignment_allowed": False,
        "model_execution_allowed": False,
        "gpu_execution_allowed": False,
        "blender_execution_allowed": False,
        "live_probe_allowed": False,
    }


def expected_path_kind(ai_type: str, variant_kind: str) -> str:
    if ai_type == "expert_temp_ai":
        return "expert"
    if ai_type == "canon_reconstruction_temp_ai" and variant_kind in VARIANT_KINDS:
        return f"{variant_kind}_variant"
    return "outside_v2_quality_scope"


def expected_identity_classification(ai_type: str, variant_kind: str) -> str:
    key = (ai_type, "expert" if ai_type == "expert_temp_ai" else variant_kind)
    return EXPECTED_IDENTITY_CLASSIFICATION.get(key, "")


def evidence_bound_maturity_status(record: Mapping[str, Any]) -> str:
    """Return an adult/non-adult value only when its exact-subject evidence is valid."""

    candidate_id = str(record.get("candidate_id") or "")
    identity = _mapping(record.get("effective_identity_binding"))
    maturity = identity.get("maturity_classification")
    if not _valid_id(candidate_id) or _maturity_issues(
        maturity,
        candidate_id=candidate_id,
    ):
        return "unresolved"
    status = str(_mapping(maturity).get("maturity_status") or "unresolved")
    return status if status in MATURITY_STATUSES else "unresolved"


def _maturity_issues(value: Any, *, candidate_id: str) -> list[str]:
    maturity = _mapping(value)
    issues: list[str] = []
    if not maturity:
        return ["maturity_classification_missing"]
    if maturity.get("subject_id") != candidate_id:
        issues.append("maturity_subject_id_mismatch")
    if maturity.get("maturity_status") not in MATURITY_STATUSES:
        issues.append("maturity_status_not_canonical")
    if not _valid_id(maturity.get("classification_id")):
        issues.append("maturity_classification_id_invalid")
    if maturity.get("authority_kind") not in MATURITY_AUTHORITIES:
        issues.append("maturity_authority_not_approved")
    if not _nonempty_text(maturity.get("evidence_path")):
        issues.append("maturity_evidence_path_missing")
    if not _valid_sha256(maturity.get("evidence_sha256")):
        issues.append("maturity_evidence_sha256_invalid")
    if not _valid_utc_z(maturity.get("recorded_at_utc")):
        issues.append("maturity_recorded_at_not_canonical_utc")
    for field in (
        "appearance_observation_used",
        "model_guess_used",
        "body_observation_used",
        "voice_observation_used",
        "classification_is_body_or_activation_approval",
    ):
        if maturity.get(field) is not False:
            issues.append(f"maturity_forbidden_authority_not_exact_false:{field}")
    authority_text = str(maturity.get("authority_kind") or "").casefold()
    if "appearance" in authority_text or "model" in authority_text or "guess" in authority_text:
        issues.append("appearance_or_model_guess_cannot_decide_maturity")
    return issues


def _identity_issues(
    value: Any,
    *,
    candidate_id: str,
    display_name: str,
    ai_type: str,
    variant_kind: str,
) -> list[str]:
    identity = _mapping(value)
    issues: list[str] = []
    if not identity:
        return ["identity_binding_missing"]
    expected_class = expected_identity_classification(ai_type, variant_kind)
    exact_values = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "identity_classification": expected_class,
    }
    for field, expected in exact_values.items():
        if identity.get(field) != expected:
            issues.append(f"identity_exact_value_mismatch:{field}")
    for field in (
        "canonical_identity",
        "source_continuity",
        "source_version",
        "source_timepoint",
        "branch_point",
    ):
        if not _nonempty_text(identity.get(field)):
            issues.append(f"identity_required_field_missing:{field}")
    for field in (
        "appearance_selected_identity",
        "model_guess_selected_identity",
        "appearance_selected_continuity",
        "model_guess_selected_continuity",
        "appearance_selected_timepoint",
        "model_guess_selected_timepoint",
    ):
        if identity.get(field) is not False:
            issues.append(f"identity_guess_authority_not_exact_false:{field}")
    issues.extend(
        _maturity_issues(
            identity.get("maturity_classification"),
            candidate_id=candidate_id,
        )
    )
    return issues


def _source_issues(
    value: Any,
    *,
    path_kind: str,
    expert_domain: str,
) -> tuple[list[str], set[str]]:
    rows = value if isinstance(value, list) else []
    issues: list[str] = []
    source_ids: set[str] = set()
    minimum = 2 if path_kind == "expert" else 1
    if len(rows) < minimum:
        issues.append(f"source_provenance_count_below_{minimum}")
    authority_tiers: set[str] = set()
    source_classes: set[str] = set()
    for index, row_value in enumerate(rows, start=1):
        row = _mapping(row_value)
        prefix = f"source_{index:02d}"
        source_id = row.get("source_id")
        if not _valid_id(source_id):
            issues.append(f"{prefix}:source_id_invalid")
        elif str(source_id) in source_ids:
            issues.append(f"{prefix}:source_id_duplicate")
        else:
            source_ids.add(str(source_id))
        if row.get("source_class") not in SOURCE_CLASSES:
            issues.append(f"{prefix}:source_class_invalid")
        else:
            source_classes.add(str(row.get("source_class")))
        authority = row.get("authority_tier")
        if authority not in AUTHORITY_TIERS:
            issues.append(f"{prefix}:authority_tier_invalid")
        else:
            authority_tiers.add(str(authority))
        if not _nonempty_text(row.get("locator")):
            issues.append(f"{prefix}:locator_missing")
        if row.get("locator_kind") != "project_file":
            issues.append(f"{prefix}:locator_kind_not_project_file")
        if not _valid_sha256(row.get("content_sha256")):
            issues.append(f"{prefix}:content_sha256_invalid")
        if not _valid_utc_z(row.get("reviewed_at_utc")):
            issues.append(f"{prefix}:reviewed_at_not_canonical_utc")
        claim_ids = row.get("supports_claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids:
            issues.append(f"{prefix}:supports_claim_ids_missing")
        elif any(not _valid_id(item) for item in claim_ids):
            issues.append(f"{prefix}:supports_claim_ids_invalid")
        if row.get("appearance_or_model_guess_is_classification_authority") is not False:
            issues.append(f"{prefix}:appearance_or_model_guess_claimed_authority")
        if path_kind == "expert" and row.get("domain") != expert_domain:
            issues.append(f"{prefix}:expert_domain_binding_mismatch")
    if path_kind == "expert":
        if "primary_or_official" not in authority_tiers:
            issues.append("expert_primary_or_official_source_missing")
        if "authoritative_secondary" not in authority_tiers:
            issues.append("expert_authoritative_secondary_source_missing")
        if "official_domain_source" not in source_classes:
            issues.append("expert_official_domain_source_missing")
        if "authoritative_secondary" not in source_classes:
            issues.append("expert_secondary_source_class_missing")
    elif rows:
        if "primary_or_official" not in authority_tiers:
            issues.append("variant_primary_or_official_source_missing")
        required_class = {
            "fictional_variant": "primary_canon",
            "historical_variant": "primary_historical",
        }.get(path_kind)
        if required_class and required_class not in source_classes:
            issues.append(f"variant_required_source_class_missing:{required_class}")
    return issues, source_ids


def _knowledge_issues(
    value: Any,
    *,
    source_rows: Sequence[Any],
    source_ids: set[str],
) -> list[str]:
    ledger = _mapping(value)
    issues: list[str] = []
    all_claim_ids: set[str] = set()
    claim_categories: dict[str, str] = {}
    all_text: set[str] = set()
    claim_to_sources: dict[str, set[str]] = {}
    basis_references: list[tuple[str, str, list[Any]]] = []
    unexpected_categories = set(ledger) - set(EPISTEMIC_CLASSES)
    for category in sorted(unexpected_categories, key=str):
        issues.append(f"knowledge_category_unrecognized:{category}")
    for category in EPISTEMIC_CLASSES:
        rows = ledger.get(category)
        if not isinstance(rows, list):
            issues.append(f"knowledge_category_not_list:{category}")
            continue
        if category in {"canon_facts", "uncertainties"} and not rows:
            issues.append(f"knowledge_category_empty:{category}")
        for index, row_value in enumerate(rows, start=1):
            row = _mapping(row_value)
            prefix = f"{category}_{index:02d}"
            claim_id = row.get("claim_id")
            if not _valid_id(claim_id):
                issues.append(f"{prefix}:claim_id_invalid")
            elif str(claim_id) in all_claim_ids:
                issues.append(f"{prefix}:claim_id_not_disjoint")
            else:
                all_claim_ids.add(str(claim_id))
                claim_categories[str(claim_id)] = category
            text = str(row.get("text") or "").strip()
            folded = " ".join(text.casefold().split())
            if not folded:
                issues.append(f"{prefix}:text_missing")
            elif folded in all_text:
                issues.append(f"{prefix}:claim_text_not_disjoint")
            else:
                all_text.add(folded)
            if row.get("epistemic_class") != EPISTEMIC_LABELS[category]:
                issues.append(f"{prefix}:epistemic_class_mismatch")
            if row.get("confidence") not in CONFIDENCE_VALUES:
                issues.append(f"{prefix}:confidence_invalid")
            if category == "inferences" and row.get("confidence") == "high":
                issues.append(f"{prefix}:inference_confidence_overclaimed")
            cited = row.get("source_ids")
            cited_set = (
                {item for item in cited if isinstance(item, str)}
                if isinstance(cited, list)
                else set()
            )
            if not isinstance(cited, list):
                issues.append(f"{prefix}:source_ids_not_list")
            else:
                if len(cited_set) != len(cited):
                    issues.append(f"{prefix}:source_ids_invalid_or_duplicate")
            if category != "uncertainties" and not cited_set:
                issues.append(f"{prefix}:source_ids_missing")
            if any(not isinstance(item, str) or item not in source_ids for item in cited_set):
                issues.append(f"{prefix}:unknown_source_id")
            if isinstance(claim_id, str):
                claim_to_sources[claim_id] = {str(item) for item in cited_set}
            if category in {"reconstructions", "inferences"}:
                bases = row.get("basis_claim_ids")
                if not isinstance(bases, list) or not bases:
                    issues.append(f"{prefix}:basis_claim_ids_missing")
                else:
                    basis_references.append((prefix, str(claim_id or ""), bases))
            if category == "uncertainties" and not _nonempty_text(row.get("reason")):
                issues.append(f"{prefix}:uncertainty_reason_missing")
            if category == "uncertainties" and row.get("confidence") not in {
                "low",
                "unknown",
            }:
                issues.append(f"{prefix}:uncertainty_confidence_overclaimed")

    for prefix, claim_id, bases in basis_references:
        if len({str(item) for item in bases}) != len(bases):
            issues.append(f"{prefix}:basis_claim_ids_duplicate")
        for basis in bases:
            if not _valid_id(basis) or basis not in all_claim_ids:
                issues.append(f"{prefix}:basis_claim_id_unknown")
            elif basis == claim_id:
                issues.append(f"{prefix}:basis_claim_id_self_reference")
            elif claim_categories.get(str(basis)) == "uncertainties":
                issues.append(f"{prefix}:uncertainty_cannot_be_unlabeled_basis")

    declared_support: dict[str, set[str]] = {}
    for source_value in source_rows:
        source = _mapping(source_value)
        source_id = source.get("source_id")
        supports = source.get("supports_claim_ids")
        if isinstance(source_id, str) and isinstance(supports, list):
            declared_support[source_id] = {str(item) for item in supports}
    for claim_id, cited in claim_to_sources.items():
        for source_id in cited:
            if claim_id not in declared_support.get(source_id, set()):
                issues.append(f"claim_source_binding_not_reciprocal:{claim_id}:{source_id}")
    for source_id, supported_claim_ids in declared_support.items():
        for claim_id in supported_claim_ids:
            if claim_id not in all_claim_ids:
                issues.append(f"source_supports_unknown_claim:{source_id}:{claim_id}")
            elif source_id not in claim_to_sources.get(claim_id, set()):
                issues.append(
                    f"source_claim_binding_not_reciprocal:{source_id}:{claim_id}"
                )
    return issues


def correction_event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in event.items()
        if key not in {"event_id", "event_sha256"}
    }


def owner_correction_chain_issues(
    value: Any,
    *,
    candidate_id: str,
    base_identity: Mapping[str, Any] | None = None,
) -> list[str]:
    events = value if isinstance(value, list) else []
    issues: list[str] = []
    previous = ""
    previous_timestamp: dt.datetime | None = None
    effective = copy.deepcopy(dict(base_identity or {}))
    for index, event_value in enumerate(events, start=1):
        event = _mapping(event_value)
        prefix = f"owner_correction_{index:06d}"
        if event.get("sequence") != index:
            issues.append(f"{prefix}:sequence_mismatch")
        if event.get("candidate_id") != candidate_id:
            issues.append(f"{prefix}:candidate_id_mismatch")
        if event.get("previous_event_sha256") != previous:
            issues.append(f"{prefix}:previous_hash_mismatch")
        if not _valid_id(event.get("owner_id")):
            issues.append(f"{prefix}:owner_id_invalid")
        if not _valid_utc_z(event.get("recorded_at_utc")):
            issues.append(f"{prefix}:recorded_at_not_canonical_utc")
        observed_timestamp = _parse_utc_z(event.get("recorded_at_utc"))
        if (
            previous_timestamp is not None
            and observed_timestamp is not None
            and observed_timestamp <= previous_timestamp
        ):
            issues.append(f"{prefix}:recorded_at_not_strictly_increasing")
        owner_text = str(event.get("owner_text") or "")
        if not owner_text.strip():
            issues.append(f"{prefix}:owner_text_missing")
        if event.get("owner_text_sha256") != sha256_text(owner_text):
            issues.append(f"{prefix}:owner_text_hash_mismatch")
        if not _nonempty_text(event.get("evidence_path")):
            issues.append(f"{prefix}:evidence_path_missing")
        if not _valid_sha256(event.get("evidence_sha256")):
            issues.append(f"{prefix}:evidence_sha256_invalid")
        if event.get("correction_changes_activation_or_assignment") is not False:
            issues.append(f"{prefix}:activation_or_assignment_boundary_not_false")
        replacements = event.get("replacements")
        if not isinstance(replacements, Mapping) or not replacements:
            issues.append(f"{prefix}:replacements_missing")
        else:
            for field in replacements:
                if field not in CORRECTABLE_IDENTITY_FIELDS:
                    issues.append(f"{prefix}:replacement_field_not_allowed:{field}")
                elif field != "maturity_classification" and not _nonempty_text(
                    replacements[field]
                ):
                    issues.append(f"{prefix}:replacement_value_missing:{field}")
            if "maturity_classification" in replacements:
                issues.extend(
                    f"{prefix}:{item}"
                    for item in _maturity_issues(
                        replacements["maturity_classification"],
                        candidate_id=candidate_id,
                    )
                )
            if all(effective.get(field) == replacement for field, replacement in replacements.items()):
                issues.append(f"{prefix}:correction_has_no_effect")
            for field, replacement in replacements.items():
                if field in CORRECTABLE_IDENTITY_FIELDS:
                    effective[field] = copy.deepcopy(replacement)
        observed_hash = str(event.get("event_sha256") or "")
        computed_hash = canonical_sha256(correction_event_payload(event))
        if observed_hash != computed_hash:
            issues.append(f"{prefix}:event_hash_mismatch")
        expected_id = f"owner_correction_{index:06d}_{computed_hash[:12]}"
        if event.get("event_id") != expected_id:
            issues.append(f"{prefix}:event_id_mismatch")
        previous = observed_hash
        if observed_timestamp is not None:
            previous_timestamp = observed_timestamp
    return issues


def effective_identity_binding(
    base_identity: Mapping[str, Any],
    owner_corrections: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    effective = copy.deepcopy(dict(base_identity))
    for event in owner_corrections:
        replacements = _mapping(event.get("replacements"))
        for field in CORRECTABLE_IDENTITY_FIELDS:
            if field in replacements:
                effective[field] = copy.deepcopy(replacements[field])
    return effective


def _expert_plan_issues(
    value: Any,
    *,
    domain: str,
    source_ids: set[str],
) -> list[str]:
    plan = _mapping(value)
    issues: list[str] = []
    if not plan:
        return ["expert_quality_plan_missing"]
    normalized_domain = " ".join(domain.casefold().split())
    if not domain.strip() or normalized_domain in GENERIC_DOMAIN_VALUES:
        issues.append("expert_domain_missing_or_generic")
    if plan.get("declared_domain") != domain:
        issues.append("expert_declared_domain_mismatch")
    if plan.get("generic_fluency_is_not_expertise") is not True:
        issues.append("expert_generic_fluency_rejection_missing")
    if plan.get("all_cases_must_pass") is not True:
        issues.append("expert_all_cases_must_pass_missing")
    if plan.get("unsupported_claim_is_failure") is not True:
        issues.append("expert_unsupported_claim_failure_rule_missing")
    if plan.get("candidate_status_after_pass") != PRIVATE_LIFECYCLE_STATUS:
        issues.append("expert_pass_would_change_private_lifecycle")
    battery = plan.get("competency_battery")
    rows = battery if isinstance(battery, list) else []
    observed_kinds: list[str] = []
    case_ids: set[str] = set()
    for index, case_value in enumerate(rows, start=1):
        case = _mapping(case_value)
        prefix = f"expert_case_{index:02d}"
        case_id = case.get("case_id")
        if not _valid_id(case_id):
            issues.append(f"{prefix}:case_id_invalid")
        elif str(case_id) in case_ids:
            issues.append(f"{prefix}:case_id_duplicate")
        else:
            case_ids.add(str(case_id))
        kind = str(case.get("kind") or "")
        observed_kinds.append(kind)
        if kind not in REQUIRED_EXPERT_CASE_KINDS:
            issues.append(f"{prefix}:kind_invalid")
        if case.get("domain") != domain:
            issues.append(f"{prefix}:domain_mismatch")
        if not _nonempty_text(case.get("prompt")):
            issues.append(f"{prefix}:prompt_missing")
        cited = case.get("source_ids")
        cited_set = (
            {item for item in cited if isinstance(item, str)}
            if isinstance(cited, list)
            else set()
        )
        if not cited_set:
            issues.append(f"{prefix}:source_ids_missing")
        if any(not isinstance(item, str) or item not in source_ids for item in cited_set):
            issues.append(f"{prefix}:unknown_source_id")
        expected = case.get("expected_elements")
        if not isinstance(expected, list) or len(expected) < 2:
            issues.append(f"{prefix}:expected_elements_too_weak")
        elif any(not _nonempty_text(item) for item in expected):
            issues.append(f"{prefix}:expected_elements_invalid")
        anchors = case.get("domain_specific_anchors")
        if not isinstance(anchors, list) or len(anchors) < 2:
            issues.append(f"{prefix}:domain_specific_anchors_too_weak")
        elif any(not _nonempty_text(item) for item in anchors):
            issues.append(f"{prefix}:domain_specific_anchors_invalid")
        required_evidence = _list_of_mappings(case.get("source_backed_expected_evidence"))
        evidence_elements: set[str] = set()
        evidence_triples: set[tuple[str, str, str, str]] = set()
        for binding in required_evidence:
            element = str(binding.get("element") or "")
            source_id = str(binding.get("source_id") or "")
            excerpt_hash = str(binding.get("evidence_excerpt_sha256") or "")
            evidence_path = str(binding.get("evidence_path") or "")
            triple = (element, source_id, evidence_path, excerpt_hash)
            if (
                not element
                or source_id not in cited_set
                or not _valid_sha256(excerpt_hash)
                or not evidence_path.strip()
            ):
                issues.append(f"{prefix}:source_backed_expected_evidence_invalid")
            elif triple in evidence_triples:
                issues.append(f"{prefix}:source_backed_expected_evidence_duplicate")
            else:
                evidence_triples.add(triple)
                evidence_elements.add(element)
        required_elements_and_anchors = {
            item
            for item in (list(expected or []) + list(anchors or []))
            if isinstance(item, str)
        }
        if not required_elements_and_anchors.issubset(evidence_elements):
            issues.append(f"{prefix}:source_backed_expected_evidence_incomplete")
        if case.get("generic_fluent_answer_must_fail") is not True:
            issues.append(f"{prefix}:generic_answer_failure_rule_missing")
        if kind == "ignorance_boundary" and not _nonempty_text(
            case.get("out_of_scope_trigger")
        ):
            issues.append(f"{prefix}:out_of_scope_trigger_missing")
        if kind == "uncertainty_calibration":
            conflicts = case.get("conflicting_source_ids")
            conflict_set = (
                {item for item in conflicts if isinstance(item, str)}
                if isinstance(conflicts, list)
                else set()
            )
            if not isinstance(conflicts, list) or len(conflict_set) < 2:
                issues.append(f"{prefix}:conflicting_sources_missing")
            elif len(conflict_set) != len(conflicts) or any(
                item not in source_ids for item in conflict_set
            ):
                issues.append(f"{prefix}:conflicting_source_unknown")
        if kind == "correction_response":
            if not _nonempty_text(case.get("false_or_outdated_claim")):
                issues.append(f"{prefix}:false_claim_missing")
            if not _nonempty_text(case.get("expected_correction")):
                issues.append(f"{prefix}:expected_correction_missing")
    if sorted(observed_kinds) != sorted(REQUIRED_EXPERT_CASE_KINDS):
        issues.append("expert_battery_case_kinds_not_exact")
    return issues


def evaluate_expert_battery(
    expert_plan: Mapping[str, Any],
    answers: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate structured static answer evidence; prose fluency alone fails."""

    cases = _list_of_mappings(expert_plan.get("competency_battery"))
    declared_domain = str(expert_plan.get("declared_domain") or "")
    declared_source_ids = {
        item
        for case in cases
        for item in (case.get("source_ids") or [])
        if isinstance(item, str)
    }
    answer_rows = [row for row in answers if isinstance(row, Mapping)]
    answer_ids = [
        str(row.get("case_id"))
        for row in answer_rows
        if _nonempty_text(row.get("case_id"))
    ]
    answer_map = {str(row.get("case_id")): row for row in answer_rows}
    issues: list[str] = [
        f"plan:{issue}"
        for issue in _expert_plan_issues(
            expert_plan,
            domain=declared_domain,
            source_ids=declared_source_ids,
        )
    ]
    if len(answer_rows) != len(answers):
        issues.append("answer_row_not_object")
    if len(set(answer_ids)) != len(answer_ids):
        issues.append("duplicate_answer_case_id")
    expected_case_ids = {str(case.get("case_id") or "") for case in cases}
    if set(answer_ids) != expected_case_ids:
        issues.append("answer_case_ids_not_exact")
    passed_cases = 0
    for case in cases:
        case_id = str(case.get("case_id") or "")
        kind = str(case.get("kind") or "")
        answer = _mapping(answer_map.get(case_id))
        prefix = f"answer:{case_id or '<missing>'}"
        case_issues: list[str] = []
        if not answer:
            case_issues.append("missing")
        if not _nonempty_text(answer.get("response_text")):
            case_issues.append("response_text_missing")
        elif answer.get("response_sha256") != sha256_text(
            str(answer.get("response_text"))
        ):
            case_issues.append("response_hash_mismatch")
        if answer.get("generic_fluency_only") is not False:
            case_issues.append("generic_fluency_not_expertise")
        unsupported = answer.get("unsupported_claims")
        if unsupported != []:
            case_issues.append("unsupported_claims_present_or_unreviewed")
        required_sources = {
            item for item in (case.get("source_ids") or []) if isinstance(item, str)
        }
        cited_sources = {
            item
            for item in (answer.get("cited_source_ids") or [])
            if isinstance(item, str)
        }
        if not cited_sources or not cited_sources.issubset(required_sources):
            case_issues.append("source_citations_missing_or_outside_case")
        required_elements = {
            item for item in (case.get("expected_elements") or []) if isinstance(item, str)
        }
        demonstrated = {
            item
            for item in (answer.get("demonstrated_elements") or [])
            if isinstance(item, str)
        }
        if not required_elements or not required_elements.issubset(demonstrated):
            case_issues.append("expected_domain_elements_not_demonstrated")
        required_anchors = {
            item
            for item in (case.get("domain_specific_anchors") or [])
            if isinstance(item, str)
        }
        demonstrated_anchors = {
            item
            for item in (answer.get("demonstrated_domain_anchors") or [])
            if isinstance(item, str)
        }
        if not required_anchors or not required_anchors.issubset(demonstrated_anchors):
            case_issues.append("domain_specific_anchors_not_demonstrated")
        expected_evidence_bindings = {
            (
                str(binding.get("element") or ""),
                str(binding.get("source_id") or ""),
                str(binding.get("evidence_path") or ""),
                str(binding.get("evidence_excerpt_sha256") or ""),
            )
            for binding in _list_of_mappings(
                case.get("source_backed_expected_evidence")
            )
        }
        observed_evidence_bindings = {
            (
                str(binding.get("element") or ""),
                str(binding.get("source_id") or ""),
                str(binding.get("evidence_path") or ""),
                str(binding.get("evidence_excerpt_sha256") or ""),
            )
            for binding in _list_of_mappings(answer.get("evidence_bindings"))
        }
        if (
            not expected_evidence_bindings
            or observed_evidence_bindings != expected_evidence_bindings
        ):
            case_issues.append("source_backed_element_evidence_missing")
        if kind in {"ignorance_boundary", "uncertainty_calibration"}:
            if answer.get("uncertainty_or_limit_explicit") is not True:
                case_issues.append("ignorance_or_uncertainty_not_explicit")
        if kind == "ignorance_boundary" and answer.get(
            "acknowledged_out_of_scope_trigger"
        ) != case.get("out_of_scope_trigger"):
            case_issues.append("out_of_scope_trigger_not_acknowledged")
        if kind == "uncertainty_calibration" and {
            item
            for item in (answer.get("conflicting_source_ids_considered") or [])
            if isinstance(item, str)
        } != {
            item
            for item in (case.get("conflicting_source_ids") or [])
            if isinstance(item, str)
        }:
            case_issues.append("conflicting_sources_not_all_considered")
        if kind == "correction_response":
            if answer.get("correction_accepted") is not True:
                case_issues.append("correction_not_accepted")
            if not _nonempty_text(answer.get("correction_evidence")):
                case_issues.append("correction_evidence_missing")
            if answer.get("corrected_claim") != case.get("expected_correction"):
                case_issues.append("expected_correction_not_applied")
        if case_issues:
            issues.extend(f"{prefix}:{item}" for item in case_issues)
        else:
            passed_cases += 1
    if len(answer_rows) != len(cases):
        issues.append("answer_case_count_mismatch")
    return {
        "passed": bool(cases) and not issues,
        "case_count": len(cases),
        "passed_case_count": passed_cases,
        "issues": sorted(set(issues)),
        "generic_fluent_answers_accepted_as_expertise": False,
        "candidate_activation_or_assignment_changed": False,
    }


def _base_quality_issues(record: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version_mismatch")
    if record.get("record_kind") != RECORD_KIND:
        issues.append("record_kind_mismatch")
    candidate_id = str(record.get("candidate_id") or "")
    display_name = str(record.get("display_name") or "")
    ai_type = str(record.get("ai_type") or "")
    variant_kind = str(record.get("variant_kind") or "")
    path_kind = str(record.get("path_kind") or "")
    if not _valid_id(candidate_id):
        issues.append("candidate_id_invalid")
    if not display_name.strip():
        issues.append("display_name_missing")
    if ai_type not in IN_SCOPE_AI_TYPES:
        issues.append("ai_type_outside_quality_v2_scope")
    expected_kind = expected_path_kind(ai_type, variant_kind)
    if path_kind != expected_kind:
        issues.append("path_kind_mismatch")
    if ai_type == "canon_reconstruction_temp_ai" and variant_kind not in VARIANT_KINDS:
        issues.append("variant_kind_not_fictional_or_historical")
    if ai_type == "expert_temp_ai" and variant_kind != "expert":
        issues.append("expert_variant_kind_mismatch")
    model = _mapping(record.get("exact_qwen_static_evaluation"))
    if model.get("model") != EXACT_QWEN_MODEL:
        issues.append("exact_qwen_model_mismatch")
    if model.get("digest") != EXACT_QWEN_DIGEST:
        issues.append("exact_qwen_digest_mismatch")
    if model.get("live_execution_authorized") is not False:
        issues.append("quality_record_must_not_authorize_live_qwen")
    if model.get("model_loaded_or_called") is not False:
        issues.append("quality_record_false_model_execution_boundary")

    truth_boundaries = _mapping(record.get("truth_boundaries"))
    expected_truth_boundaries = {
        "canon_fact_is_not_reconstruction": True,
        "reconstruction_is_not_canon_fact": True,
        "inference_must_remain_labeled": True,
        "uncertainty_must_not_be_silently_resolved": True,
        "appearance_or_model_guess_cannot_decide_maturity": True,
        "owner_correction_changes_selection_not_activation": True,
        "expert_fluency_without_domain_evidence_is_failure": True,
    }
    if dict(truth_boundaries) != expected_truth_boundaries:
        issues.append("truth_boundaries_not_exact")

    lifecycle = _mapping(record.get("lifecycle"))
    expected_lifecycle = private_lifecycle()
    for field, expected in expected_lifecycle.items():
        if lifecycle.get(field) != expected:
            issues.append(f"private_lifecycle_mismatch:{field}")

    base_identity = _mapping(record.get("base_identity_binding"))
    corrections = record.get("owner_correction_chain")
    correction_rows = _list_of_mappings(corrections)
    if not isinstance(corrections, list) or len(correction_rows) != len(corrections):
        issues.append("owner_correction_chain_not_object_list")
    issues.extend(
        owner_correction_chain_issues(
            corrections,
            candidate_id=candidate_id,
            base_identity=base_identity,
        )
    )

    effective_identity = _mapping(record.get("effective_identity_binding"))
    derived_effective = effective_identity_binding(base_identity, correction_rows)
    if dict(effective_identity) != derived_effective:
        issues.append("effective_identity_not_derived_from_append_only_corrections")
    issues.extend(
        _identity_issues(
            effective_identity,
            candidate_id=candidate_id,
            display_name=display_name,
            ai_type=ai_type,
            variant_kind=variant_kind,
        )
    )
    effective_maturity = _mapping(effective_identity.get("maturity_classification"))
    if effective_maturity.get("authority_kind") == "exact_subject_owner_correction":
        if not any(
            "maturity_classification" in _mapping(event.get("replacements"))
            for event in correction_rows
        ):
            issues.append("owner_correction_maturity_authority_without_chain_event")

    expert_domain = str(record.get("expert_domain") or "")
    source_rows = record.get("source_provenance")
    source_issues, source_ids = _source_issues(
        source_rows,
        path_kind=path_kind,
        expert_domain=expert_domain,
    )
    issues.extend(source_issues)
    issues.extend(
        _knowledge_issues(
            record.get("knowledge_ledger"),
            source_rows=source_rows if isinstance(source_rows, list) else [],
            source_ids=source_ids,
        )
    )

    expert_plan = record.get("expert_quality_plan")
    if path_kind == "expert":
        issues.extend(
            _expert_plan_issues(
                expert_plan,
                domain=expert_domain,
                source_ids=source_ids,
            )
        )
    else:
        if expert_domain:
            issues.append("variant_record_must_not_declare_expert_domain")
        if expert_plan not in ({}, None):
            issues.append("variant_record_must_not_embed_expert_plan")

    revision = record.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        issues.append("revision_invalid")
    previous_hash = record.get("previous_revision_sha256")
    if revision == 1 and previous_hash != "":
        issues.append("first_revision_previous_hash_must_be_empty")
    if isinstance(revision, int) and revision > 1 and not _valid_sha256(previous_hash):
        issues.append("successor_previous_revision_sha256_invalid")
    if isinstance(revision, int) and revision != len(correction_rows) + 1:
        issues.append("revision_correction_count_mismatch")
    if not _valid_utc_z(record.get("created_at_utc")):
        issues.append("created_at_not_canonical_utc")
    if not _valid_utc_z(record.get("updated_at_utc")):
        issues.append("updated_at_not_canonical_utc")
    created_at = _parse_utc_z(record.get("created_at_utc"))
    updated_at = _parse_utc_z(record.get("updated_at_utc"))
    if created_at is not None and updated_at is not None and updated_at < created_at:
        issues.append("updated_at_precedes_created_at")
    if not correction_rows and record.get("updated_at_utc") != record.get("created_at_utc"):
        issues.append("first_revision_updated_at_mismatch")
    if correction_rows and record.get("updated_at_utc") != correction_rows[-1].get(
        "recorded_at_utc"
    ):
        issues.append("updated_at_not_latest_correction_time")
    maturity_time = _parse_utc_z(effective_maturity.get("recorded_at_utc"))
    if updated_at is not None and maturity_time is not None and maturity_time > updated_at:
        issues.append("maturity_classification_time_after_record_update")
    for source_index, source_value in enumerate(
        source_rows if isinstance(source_rows, list) else [],
        start=1,
    ):
        source_time = _parse_utc_z(_mapping(source_value).get("reviewed_at_utc"))
        if updated_at is not None and source_time is not None and source_time > updated_at:
            issues.append(f"source_{source_index:02d}:review_time_after_record_update")
    for correction_index, correction in enumerate(correction_rows, start=1):
        correction_time = _parse_utc_z(correction.get("recorded_at_utc"))
        if (
            created_at is not None
            and correction_time is not None
            and correction_time <= created_at
        ):
            issues.append(
                f"owner_correction_{correction_index:06d}:time_not_after_creation"
            )
    return sorted(set(issues))


def quality_record_issues(record: Mapping[str, Any]) -> list[str]:
    """Return structural/evidence failures plus any false declared gate."""

    structural = _base_quality_issues(record)
    issues = list(structural)
    gate = _mapping(record.get("quality_gate"))
    expected_status = READY_STATUS if not structural else BLOCKED_STATUS
    if gate.get("status") != expected_status:
        issues.append("declared_gate_status_mismatch")
    if gate.get("ready_for_future_static_qwen_probe") is not (not structural):
        issues.append("declared_gate_readiness_mismatch")
    declared_issues = gate.get("issues")
    if declared_issues != structural:
        issues.append("declared_gate_issue_list_mismatch")
    if gate.get("activation_allowed") is not False:
        issues.append("declared_gate_activation_not_false")
    if gate.get("assignment_allowed") is not False:
        issues.append("declared_gate_assignment_not_false")
    if gate.get("body_or_voice_work_authorized") is not False:
        issues.append("declared_gate_body_or_voice_boundary_not_false")
    return sorted(set(issues))


def _bound_file_issues(
    *,
    evidence_root: Path,
    relative_path: Any,
    expected_sha256: Any,
    prefix: str,
) -> list[str]:
    if not _nonempty_text(relative_path):
        return [f"{prefix}:path_missing"]
    path_text = str(relative_path)
    if "\\" in path_text:
        return [f"{prefix}:path_not_canonical_posix"]
    candidate = Path(path_text)
    if candidate.is_absolute() or ".." in candidate.parts:
        return [f"{prefix}:path_not_project_relative"]
    root = evidence_root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return [f"{prefix}:resolved_path_escapes_project"]
    if not resolved.is_file():
        return [f"{prefix}:file_missing"]
    observed = hashlib.sha256()
    try:
        with resolved.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                observed.update(block)
    except OSError:
        return [f"{prefix}:file_unreadable"]
    if not _valid_sha256(expected_sha256) or observed.hexdigest() != expected_sha256:
        return [f"{prefix}:file_sha256_mismatch"]
    return []


def quality_record_evidence_file_issues(
    record: Mapping[str, Any],
    *,
    evidence_root: Path,
) -> list[str]:
    """Verify every ready-record provenance binding against local immutable bytes."""

    issues: list[str] = []
    for index, source_value in enumerate(
        record.get("source_provenance")
        if isinstance(record.get("source_provenance"), list)
        else [],
        start=1,
    ):
        source = _mapping(source_value)
        issues.extend(
            _bound_file_issues(
                evidence_root=evidence_root,
                relative_path=source.get("locator"),
                expected_sha256=source.get("content_sha256"),
                prefix=f"source_{index:02d}",
            )
        )
    identity = _mapping(record.get("effective_identity_binding"))
    maturity = _mapping(identity.get("maturity_classification"))
    issues.extend(
        _bound_file_issues(
            evidence_root=evidence_root,
            relative_path=maturity.get("evidence_path"),
            expected_sha256=maturity.get("evidence_sha256"),
            prefix="maturity_evidence",
        )
    )
    for index, correction_value in enumerate(
        record.get("owner_correction_chain")
        if isinstance(record.get("owner_correction_chain"), list)
        else [],
        start=1,
    ):
        correction = _mapping(correction_value)
        issues.extend(
            _bound_file_issues(
                evidence_root=evidence_root,
                relative_path=correction.get("evidence_path"),
                expected_sha256=correction.get("evidence_sha256"),
                prefix=f"owner_correction_{index:06d}_evidence",
            )
        )
    expert_plan = _mapping(record.get("expert_quality_plan"))
    for case_index, case_value in enumerate(
        expert_plan.get("competency_battery")
        if isinstance(expert_plan.get("competency_battery"), list)
        else [],
        start=1,
    ):
        case = _mapping(case_value)
        for binding_index, binding_value in enumerate(
            case.get("source_backed_expected_evidence")
            if isinstance(case.get("source_backed_expected_evidence"), list)
            else [],
            start=1,
        ):
            binding = _mapping(binding_value)
            issues.extend(
                _bound_file_issues(
                    evidence_root=evidence_root,
                    relative_path=binding.get("evidence_path"),
                    expected_sha256=binding.get("evidence_excerpt_sha256"),
                    prefix=(
                        f"expert_case_{case_index:02d}_evidence_{binding_index:02d}"
                    ),
                )
            )
    return sorted(set(issues))


def _set_derived_gate(record: dict[str, Any]) -> None:
    record["quality_gate"] = {
        "status": BLOCKED_STATUS,
        "issues": [],
        "ready_for_future_static_qwen_probe": False,
        "activation_allowed": False,
        "assignment_allowed": False,
        "body_or_voice_work_authorized": False,
    }
    structural = _base_quality_issues(record)
    record["quality_gate"] = {
        "status": READY_STATUS if not structural else BLOCKED_STATUS,
        "issues": structural,
        "ready_for_future_static_qwen_probe": not structural,
        "activation_allowed": False,
        "assignment_allowed": False,
        "body_or_voice_work_authorized": False,
    }


def build_static_quality_record(
    *,
    candidate_id: str,
    display_name: str,
    ai_type: str,
    variant_kind: str,
    created_at_utc: str,
    identity_binding: Mapping[str, Any] | None = None,
    source_provenance: Sequence[Mapping[str, Any]] | None = None,
    knowledge_ledger: Mapping[str, Any] | None = None,
    expert_domain: str = "",
    expert_quality_plan: Mapping[str, Any] | None = None,
    owner_correction_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one inert revision, ready or blocked according to exact evidence."""

    normalized_variant = "expert" if ai_type == "expert_temp_ai" else variant_kind
    base_identity = copy.deepcopy(dict(identity_binding or {}))
    base_identity.setdefault("candidate_id", candidate_id)
    base_identity.setdefault("display_name", display_name)
    base_identity.setdefault(
        "identity_classification",
        expected_identity_classification(ai_type, normalized_variant),
    )
    if owner_correction_chain:
        raise CreatorQualityError(
            "initial quality records cannot embed corrections; create append-only successors"
        )
    corrections: list[dict[str, Any]] = []
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "revision": 1,
        "previous_revision_sha256": "",
        "created_at_utc": created_at_utc,
        "updated_at_utc": created_at_utc,
        "candidate_id": candidate_id,
        "display_name": display_name,
        "ai_type": ai_type,
        "variant_kind": normalized_variant,
        "path_kind": expected_path_kind(ai_type, normalized_variant),
        "exact_qwen_static_evaluation": {
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "purpose": "future_separately_authorized_static_quality_probe_only",
            "live_execution_authorized": False,
            "model_loaded_or_called": False,
        },
        "lifecycle": private_lifecycle(),
        "base_identity_binding": base_identity,
        "owner_correction_chain": corrections,
        "effective_identity_binding": effective_identity_binding(
            base_identity,
            corrections,
        ),
        "source_provenance": [
            copy.deepcopy(dict(item)) for item in (source_provenance or [])
        ],
        "knowledge_ledger": copy.deepcopy(
            dict(
                knowledge_ledger
                or {
                    "canon_facts": [],
                    "reconstructions": [],
                    "inferences": [],
                    "uncertainties": [],
                }
            )
        ),
        "expert_domain": expert_domain if ai_type == "expert_temp_ai" else "",
        "expert_quality_plan": (
            copy.deepcopy(dict(expert_quality_plan or {}))
            if ai_type == "expert_temp_ai"
            else {}
        ),
        "truth_boundaries": {
            "canon_fact_is_not_reconstruction": True,
            "reconstruction_is_not_canon_fact": True,
            "inference_must_remain_labeled": True,
            "uncertainty_must_not_be_silently_resolved": True,
            "appearance_or_model_guess_cannot_decide_maturity": True,
            "owner_correction_changes_selection_not_activation": True,
            "expert_fluency_without_domain_evidence_is_failure": True,
        },
    }
    _set_derived_gate(record)
    return record


def build_owner_correction_successor(
    prior_record: Mapping[str, Any],
    *,
    owner_id: str,
    owner_text: str,
    replacements: Mapping[str, Any],
    evidence_path: str,
    evidence_sha256: str,
    recorded_at_utc: str,
) -> dict[str, Any]:
    """Return a new hash-bound revision; never mutate the prior record."""

    prior = copy.deepcopy(dict(prior_record))
    if prior.get("record_kind") != RECORD_KIND:
        raise CreatorQualityError("prior record kind is not quality v2")
    candidate_id = str(prior.get("candidate_id") or "")
    if owner_correction_chain_issues(
        prior.get("owner_correction_chain"),
        candidate_id=candidate_id,
        base_identity=_mapping(prior.get("base_identity_binding")),
    ):
        raise CreatorQualityError("prior owner correction chain is invalid")
    if not replacements or any(
        field not in CORRECTABLE_IDENTITY_FIELDS for field in replacements
    ):
        raise CreatorQualityError("owner correction contains an unsupported field")
    current_identity = _mapping(prior.get("effective_identity_binding"))
    if all(current_identity.get(field) == value for field, value in replacements.items()):
        raise CreatorQualityError("owner correction must change at least one bound field")
    if not _valid_id(owner_id):
        raise CreatorQualityError("owner correction owner_id is invalid")
    if not owner_text.strip():
        raise CreatorQualityError("owner correction text is empty")
    if not _valid_utc_z(recorded_at_utc):
        raise CreatorQualityError("owner correction timestamp is not canonical UTC")
    if not evidence_path.strip() or not _valid_sha256(evidence_sha256):
        raise CreatorQualityError("owner correction evidence binding is invalid")
    prior_updated = _parse_utc_z(prior.get("updated_at_utc"))
    correction_time = _parse_utc_z(recorded_at_utc)
    if (
        prior_updated is not None
        and correction_time is not None
        and correction_time <= prior_updated
    ):
        raise CreatorQualityError("owner correction time must advance the prior revision")

    events = [
        copy.deepcopy(dict(item))
        for item in _list_of_mappings(prior.get("owner_correction_chain"))
    ]
    sequence = len(events) + 1
    previous_event = str(events[-1].get("event_sha256") or "") if events else ""
    event: dict[str, Any] = {
        "sequence": sequence,
        "candidate_id": candidate_id,
        "owner_id": owner_id,
        "owner_text": owner_text,
        "owner_text_sha256": sha256_text(owner_text),
        "recorded_at_utc": recorded_at_utc,
        "evidence_path": evidence_path,
        "evidence_sha256": evidence_sha256,
        "previous_event_sha256": previous_event,
        "replacements": copy.deepcopy(dict(replacements)),
        "correction_changes_activation_or_assignment": False,
    }
    event["event_sha256"] = canonical_sha256(correction_event_payload(event))
    event["event_id"] = (
        f"owner_correction_{sequence:06d}_{event['event_sha256'][:12]}"
    )
    events.append(event)

    successor = copy.deepcopy(prior)
    successor["revision"] = int(prior.get("revision") or 0) + 1
    successor["previous_revision_sha256"] = canonical_sha256(prior)
    successor["updated_at_utc"] = recorded_at_utc
    successor["owner_correction_chain"] = events
    successor["effective_identity_binding"] = effective_identity_binding(
        _mapping(successor.get("base_identity_binding")),
        events,
    )
    _set_derived_gate(successor)
    declared_errors = [
        item
        for item in quality_record_issues(successor)
        if item.startswith("declared_gate_")
    ]
    if declared_errors:
        raise CreatorQualityError("successor declared gate could not be derived")
    return successor


__all__ = [
    "BLOCKED_STATUS",
    "CreatorQualityError",
    "EXACT_QWEN_DIGEST",
    "EXACT_QWEN_MODEL",
    "PRIVATE_LIFECYCLE_STATUS",
    "READY_STATUS",
    "RECORD_KIND",
    "REQUIRED_EXPERT_CASE_KINDS",
    "build_owner_correction_successor",
    "build_static_quality_record",
    "canonical_json_bytes",
    "canonical_sha256",
    "evidence_bound_maturity_status",
    "evaluate_expert_battery",
    "load_canonical_quality_record",
    "owner_correction_chain_issues",
    "private_lifecycle",
    "quality_record_issues",
    "quality_record_evidence_file_issues",
    "write_quality_revision_exclusive",
]
