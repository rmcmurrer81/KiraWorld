from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from .backends import REFLECTION_FORBIDDEN
from .records import canonical_json, stable_event_id, utc_now
from .runtime import ConversationRuntime
from .strict_json import load_path_strict


EXPORT_SCHEMA = "portable-mind-reviewed-continuity-v1"
SEED_SCHEMA = "portable-mind-reviewed-seed-v1"
ALLOWED_CHANNELS = frozenset({"spoken", "reflection", "facts"})
SENSITIVE_PATTERNS = (
    ("email", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    ("api_key", re.compile(r"(?i)\b(?:api[_ -]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("ssn", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    ("payment_card", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    (
        "street_address",
        re.compile(
            r"(?i)\b\d{1,6}\s+(?:[A-Z0-9.'-]+\s+){1,5}(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\b"
        ),
    ),
)
MEMORY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$")
MEMORY_KIND_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
SOURCE_CLASS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")


class TransferError(ValueError):
    pass


def _sanitize_text(text: str) -> tuple[str, list[str]]:
    cleaned = text.replace("\x00", "").replace("\r", " ").replace("\n", " ")
    findings: list[str] = []
    for label, pattern in SENSITIVE_PATTERNS:
        cleaned, count = pattern.subn(f"[REDACTED_{label.upper()}]", cleaned)
        if count:
            findings.extend([label] * count)
    cleaned = " ".join(cleaned.split())[:4000]
    return cleaned, findings


def _sanitize_value(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, list):
        result: list[Any] = []
        findings: list[str] = []
        for item in value:
            clean, item_findings = _sanitize_value(item)
            result.append(clean)
            findings.extend(item_findings)
        return result, findings
    if isinstance(value, dict):
        result_dict: dict[str, Any] = {}
        findings = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TransferError("continuity object keys must be strings")
            clean_key, key_findings = _sanitize_text(key)
            if not clean_key or len(clean_key) > 200:
                raise TransferError("continuity object key is empty or too long")
            if clean_key in result_dict:
                raise TransferError("continuity key normalization produced a duplicate key")
            clean, item_findings = _sanitize_value(item)
            result_dict[clean_key] = clean
            findings.extend(key_findings)
            findings.extend(item_findings)
        return result_dict, findings
    if value is None or isinstance(value, (bool, int, float)):
        return value, []
    raise TransferError("unsupported value in continuity record")


def _public_record(channel: str, record: dict[str, Any]) -> dict[str, Any]:
    base = {
        "channel": channel,
        "event_id": record["event_id"],
        "timestamp": record.get("timestamp"),
        "loop_id": record.get("loop_id"),
    }
    if channel == "spoken":
        base["text"] = record.get("text", "")
    elif channel == "reflection":
        reflection = str(record.get("reflection", ""))
        if any(marker in reflection.lower() for marker in REFLECTION_FORBIDDEN):
            raise TransferError("reflection contains a forbidden reasoning marker")
        base["reflection"] = reflection
        base["disclosure"] = record.get("disclosure", "")
    elif channel == "facts":
        base.update(
            {
                "claim": record.get("claim", ""),
                "source": record.get("source", "unknown"),
                "uncertainty": record.get("uncertainty", "high"),
                "status": record.get("status", "model_claim_not_verified_truth"),
                "reviewed_by": record.get("reviewed_by"),
                "supersedes_event_ids": list(record.get("supersedes_event_ids", [])),
            }
        )
    else:
        raise TransferError("channel is not exportable")
    return base


def export_reviewed_continuity(
    runtime: ConversationRuntime,
    selections: dict[str, list[str]],
    *,
    reviewer: str,
    confirmed_reviewed: bool,
    filename: str,
) -> Path:
    if not confirmed_reviewed:
        raise TransferError("explicit --confirm-reviewed approval is required")
    reviewer_clean, reviewer_findings = _sanitize_text(" ".join(str(reviewer).split())[:120])
    if not reviewer_clean:
        raise TransferError("a reviewer label is required")
    if reviewer_findings:
        raise TransferError("reviewer label contains sensitive data; use a non-identifying label")
    if not selections or set(selections) - ALLOWED_CHANNELS:
        raise TransferError("select one or more spoken, reflection, or facts records")
    items: list[dict[str, Any]] = []
    all_findings: list[str] = []
    for channel in sorted(selections):
        records = {record["event_id"]: record for record in runtime.channel(channel).records()}
        for event_id in selections[channel]:
            if event_id not in records:
                raise TransferError(f"selected record not found in {channel}: {event_id}")
            public = _public_record(channel, records[event_id])
            clean, findings = _sanitize_value(public)
            clean["automated_redaction_pass_completed"] = True
            clean["automated_redactions"] = sorted(set(findings))
            items.append(clean)
            all_findings.extend(findings)
    body = {
        "schema": EXPORT_SCHEMA,
        "profile_id": runtime.profile_id,
        "source_branch_id": runtime.branch_id,
        "created_at": utc_now(),
        "review": {
            "confirmed": True,
            "reviewer": reviewer_clean,
            "warning": "Automated redaction is limited; the reviewer is responsible for distribution approval.",
        },
        "privacy": {
            "raw_user_input_included": False,
            "chain_of_thought_included": False,
            "automated_redaction_categories": sorted(set(all_findings)),
        },
        "functional_appraisal_state": runtime.functional_state().as_record(),
        "items": items,
    }
    digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    document = {**body, "content_sha256": digest}
    destination = runtime.sandbox.export_path(filename)
    temporary = destination.with_name(destination.name + f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def import_reviewed_continuity(
    runtime: ConversationRuntime,
    *,
    filename: str,
    approve_import: bool,
) -> int:
    if not approve_import:
        raise TransferError("explicit --approve-import approval is required")
    source = runtime.sandbox.import_path(filename)
    try:
        document = load_path_strict(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise TransferError("reviewed import is missing or invalid JSON") from exc
    if not isinstance(document, dict) or document.get("schema") != EXPORT_SCHEMA:
        raise TransferError("unsupported continuity export schema")
    if document.get("profile_id") != runtime.profile_id:
        raise TransferError("cross-profile import is blocked to preserve identity isolation")
    source_branch_id = document.get("source_branch_id")
    if not isinstance(source_branch_id, str) or not re.fullmatch(r"[0-9a-f]{32}", source_branch_id):
        raise TransferError("continuity export source branch ID is missing or invalid")
    if (document.get("review") or {}).get("confirmed") is not True:
        raise TransferError("export does not contain a confirmed review")
    supplied_digest = document.get("content_sha256")
    body = {key: value for key, value in document.items() if key != "content_sha256"}
    expected_digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if supplied_digest != expected_digest:
        raise TransferError("continuity export digest mismatch")
    privacy = document.get("privacy") or {}
    if privacy.get("raw_user_input_included") is not False or privacy.get("chain_of_thought_included") is not False:
        raise TransferError("continuity export privacy declaration is unsafe")
    items = document.get("items")
    if not isinstance(items, list):
        raise TransferError("continuity export contains no item list")
    prepared_records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("automated_redaction_pass_completed") is not True:
            raise TransferError("continuity item did not complete the automated redaction pass")
        clean, findings = _sanitize_value(item)
        if findings:
            raise TransferError("continuity item still contains a sensitive pattern")
        prepared_records.append({
            "schema_version": 1,
            "event_id": stable_event_id("reviewed-import", runtime.profile_id, expected_digest, str(index)),
            "timestamp": utc_now(),
            "profile_id": runtime.profile_id,
            "branch_id": runtime.branch_id,
            "source_branch_id": source_branch_id,
            "source_digest": expected_digest,
            "source_item_index": index,
            "item": clean,
            "status": "explicitly_reviewed_sanitized_continuity",
        })
    imported = 0
    with runtime.mutation_guard():
        for record in prepared_records:
            if runtime.reviewed_imports.append_once(record):
                imported += 1
    return imported


def import_reviewed_seed(
    runtime: ConversationRuntime,
    *,
    filename: str,
    approve_import: bool,
) -> int:
    """Import a separately prepared, identity-bound reviewed seed.

    Unlike the export path, seed import does not auto-redact. Any recognized
    sensitive pattern makes the whole seed fail closed so the source can be
    corrected and reviewed again.
    """

    if not approve_import:
        raise TransferError("explicit --approve-import approval is required")
    source = runtime.sandbox.import_path(filename)
    try:
        document = load_path_strict(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise TransferError("reviewed seed is missing or invalid JSON") from exc
    if not isinstance(document, dict) or document.get("schema") != SEED_SCHEMA:
        raise TransferError("unsupported reviewed seed schema")
    if document.get("profile_id") != runtime.profile_id:
        raise TransferError("reviewed seed profile does not match the target identity")
    review = document.get("review") or {}
    if review.get("confirmed") is not True or review.get("scope") != "public_safe_or_explicitly_authorized":
        raise TransferError("reviewed seed lacks required approval provenance")
    privacy = document.get("privacy") or {}
    if privacy.get("raw_private_data_included") is not False or privacy.get("chain_of_thought_included") is not False:
        raise TransferError("reviewed seed privacy declaration is unsafe")
    supplied_digest = document.get("content_sha256")
    body = {key: value for key, value in document.items() if key != "content_sha256"}
    expected_digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if supplied_digest != expected_digest:
        raise TransferError("reviewed seed digest mismatch")
    items = document.get("items")
    if not isinstance(items, list) or not (1 <= len(items) <= 100):
        raise TransferError("reviewed seed must contain 1 to 100 items")
    prepared_records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("kind") not in {"continuity_note", "factual_claim"}:
            raise TransferError("reviewed seed item kind is invalid")
        clean, findings = _sanitize_value(item)
        if findings:
            raise TransferError(
                "reviewed seed contains recognized sensitive data and must be corrected/re-reviewed: "
                + ", ".join(sorted(set(findings)))
            )
        prepared_records.append({
            "schema_version": 1,
            "event_id": stable_event_id("reviewed-seed", runtime.profile_id, expected_digest, str(index)),
            "timestamp": utc_now(),
            "profile_id": runtime.profile_id,
            "branch_id": runtime.branch_id,
            "source_digest": expected_digest,
            "source_item_index": index,
            "item": clean,
            "status": "explicitly_reviewed_identity_bound_seed",
        })
    imported = 0
    with runtime.mutation_guard():
        for record in prepared_records:
            if runtime.reviewed_imports.append_once(record):
                imported += 1
    return imported


def import_hanson_review_seed(
    runtime: ConversationRuntime,
    *,
    filename: str,
    approve_import: bool,
) -> int:
    """Strictly convert the named-private-reviewer KiraWorld seed format."""

    if not approve_import:
        raise TransferError("explicit --approve-import approval is required")
    source = runtime.sandbox.import_path(filename)
    try:
        document = load_path_strict(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise TransferError("Hanson reviewed seed is missing or invalid JSON") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise TransferError("unsupported Hanson reviewed seed schema")
    person_id = document.get("person_id")
    if person_id != runtime.profile_id or person_id not in {"kira", "synthetic_robert"}:
        raise TransferError("Hanson reviewed seed identity mismatch")
    expected_top_level = {
        "kira": {
            "schema_version",
            "export_id",
            "person_id",
            "effective_through_date",
            "share_class",
            "disclosure_basis",
            "raw_private_logs_included",
            "hidden_chain_of_thought_included",
            "fanfic_test_material_included",
            "identity",
            "reviewed_memories",
            "continuity_start",
            "excluded_records",
        },
        "synthetic_robert": {
            "schema_version",
            "export_id",
            "person_id",
            "effective_through_date",
            "share_class",
            "raw_biography_included",
            "raw_private_logs_included",
            "hidden_chain_of_thought_included",
            "identity",
            "reviewed_memories",
            "continuity_start",
        },
    }[person_id]
    if set(document) != expected_top_level:
        raise TransferError("Hanson reviewed seed top-level schema mismatch")
    expected_export = re.compile(rf"^{re.escape(person_id)}_private_hanson_review_seed_\d{{8}}$")
    if not expected_export.fullmatch(str(document.get("export_id", ""))):
        raise TransferError("Hanson reviewed seed export identifier mismatch")
    if document.get("share_class") != "named_private_reviewers":
        raise TransferError("Hanson reviewed seed is not restricted to named private reviewers")
    if document.get("raw_private_logs_included") is not False:
        raise TransferError("raw private logs are forbidden")
    if document.get("hidden_chain_of_thought_included") is not False:
        raise TransferError("hidden chain-of-thought is forbidden")
    if person_id == "kira":
        if document.get("disclosure_basis") != "project_owner_direct_instruction":
            raise TransferError("Kira seed disclosure basis mismatch")
        if document.get("fanfic_test_material_included") is not False:
            raise TransferError("fanfic test material is forbidden")
    elif document.get("raw_biography_included") is not False:
        raise TransferError("raw human biography is forbidden")
    identity = document.get("identity")
    continuity = document.get("continuity_start")
    memories = document.get("reviewed_memories")
    if not isinstance(identity, dict) or not isinstance(continuity, dict):
        raise TransferError("Hanson reviewed identity/continuity boundary is invalid")
    if not isinstance(memories, list) or not (1 <= len(memories) <= 50):
        raise TransferError("Hanson reviewed seed must contain 1 to 50 reviewed memories")
    allowed_memory_keys = {
        "memory_id",
        "kind",
        "summary",
        "facts",
        "forbidden_inferences",
        "forbidden_surface_phrases",
        "required_response_concepts",
        "source_class",
        "source_content_included",
    }
    converted: list[dict[str, Any]] = [
        {
            "kind": "identity_and_continuity_boundary",
            "identity": identity,
            "continuity_start": continuity,
            "effective_through_date": document.get("effective_through_date"),
            "share_class": "named_private_reviewers",
        }
    ]
    for memory in memories:
        if not isinstance(memory, dict) or set(memory) - allowed_memory_keys:
            raise TransferError("Hanson reviewed memory schema mismatch")
        memory_id = memory.get("memory_id")
        memory_kind = memory.get("kind")
        summary = memory.get("summary")
        source_class = memory.get("source_class", "reviewed_named_private_seed")
        source_content_included = memory.get("source_content_included", False)
        if (
            not isinstance(memory_id, str)
            or not MEMORY_ID_PATTERN.fullmatch(memory_id)
            or not isinstance(memory_kind, str)
            or not MEMORY_KIND_PATTERN.fullmatch(memory_kind)
            or not isinstance(summary, str)
            or not summary.strip()
            or len(summary) > 2000
            or not isinstance(source_class, str)
            or not SOURCE_CLASS_PATTERN.fullmatch(source_class)
            or not isinstance(source_content_included, bool)
        ):
            raise TransferError("Hanson reviewed memory is missing required content")
        if (
            not isinstance(memory.get("facts"), list)
            or not (1 <= len(memory["facts"]) <= 50)
            or not all(
                isinstance(item, str) and item.strip() and len(item) <= 2000
                for item in memory["facts"]
            )
        ):
            raise TransferError("Hanson reviewed memory facts are invalid")
        forbidden = memory.get("forbidden_inferences", [])
        if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
            raise TransferError("Hanson reviewed forbidden-inference list is invalid")
        forbidden_surface = memory.get("forbidden_surface_phrases", [])
        if not isinstance(forbidden_surface, list) or not all(
            isinstance(item, str) and item.strip() and len(item) <= 160
            for item in forbidden_surface
        ):
            raise TransferError("Hanson reviewed forbidden-surface list is invalid")
        response_concepts = memory.get("required_response_concepts", [])
        if not isinstance(response_concepts, list) or len(response_concepts) > 8:
            raise TransferError("Hanson reviewed response-concept contracts are invalid")
        normalized_contracts: list[dict[str, Any]] = []
        for contract in response_concepts:
            required_contract_keys = {
                "when_query_contains_any",
                "required_concept_groups",
                "require_first_person",
            }
            allowed_contract_keys = required_contract_keys | {"missing_concept_policy"}
            if (
                not isinstance(contract, dict)
                or not required_contract_keys.issubset(contract)
                or set(contract) - allowed_contract_keys
            ):
                raise TransferError("Hanson reviewed response-concept contract schema is invalid")
            triggers = contract.get("when_query_contains_any")
            groups = contract.get("required_concept_groups")
            if (
                not isinstance(triggers, list)
                or not (1 <= len(triggers) <= 12)
                or not all(isinstance(term, str) and term.strip() and len(term) <= 80 for term in triggers)
                or not isinstance(groups, list)
                or not (1 <= len(groups) <= 12)
                or not all(
                    isinstance(group, list)
                    and 1 <= len(group) <= 12
                    and all(isinstance(term, str) and term.strip() and len(term) <= 220 for term in group)
                    for group in groups
                )
                or not isinstance(contract.get("require_first_person"), bool)
                or contract.get("missing_concept_policy", "hard") not in {"hard", "advisory"}
            ):
                raise TransferError("Hanson reviewed response-concept contract values are invalid")
            normalized_contracts.append(
                {
                    "when_query_contains_any": list(triggers),
                    "required_concept_groups": [list(group) for group in groups],
                    "require_first_person": contract["require_first_person"],
                    "missing_concept_policy": contract.get("missing_concept_policy", "hard"),
                }
            )
        converted.append(
            {
                "kind": "reviewed_memory_summary",
                "memory_id": memory_id,
                "memory_kind": memory_kind,
                "summary": summary,
                "facts": list(memory["facts"]),
                "forbidden_inferences": list(forbidden),
                "forbidden_surface_phrases": list(forbidden_surface),
                "required_response_concepts": normalized_contracts,
                "source_class": source_class,
                "source_content_included": source_content_included,
            }
        )
    clean, findings = _sanitize_value(converted)
    if findings:
        raise TransferError(
            "Hanson reviewed seed contains recognized sensitive data and must be re-reviewed: "
            + ", ".join(sorted(set(findings)))
        )
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    prepared_records: list[dict[str, Any]] = []
    for index, item in enumerate(clean):
        prepared_records.append({
            "schema_version": 1,
            "event_id": stable_event_id("hanson-reviewed-seed", person_id, source_digest, str(index)),
            "timestamp": utc_now(),
            "profile_id": person_id,
            "branch_id": runtime.branch_id,
            "source_digest": source_digest,
            "source_export_id": document["export_id"],
            "source_item_index": index,
            "item": item,
            "status": "converted_named_private_reviewed_seed",
        })
    imported = 0
    with runtime.mutation_guard():
        for record in prepared_records:
            if runtime.reviewed_imports.append_once(record):
                imported += 1
    return imported
