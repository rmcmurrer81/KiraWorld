#!/usr/bin/env python3
"""Validate the separately bound 2026-08-18 Mind/Body future matrices.

The accepted/base artifacts are read-only inputs.  The pinned builder is copied
to an isolated temporary directory and run twice: once to rebuild both matrices
and once to prove append-only idempotence.  No workspace artifact is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ValidationError(RuntimeError):
    """Raised when any successor-matrix validation check fails."""


@dataclass(frozen=True)
class FileIdentity:
    byte_count: int
    sha256: str


BUILDER_PATH = "tools/build_mind_body_future_matrices_20260818.py"
MIND_SOURCE_PATH = "outputs/MIND_V21_IMPLEMENTATION_TRACEABILITY_WORKSHEET_20260818.json"
INTAKE_SOURCE_PATH = "outputs/BODY_FACE_STATION_INTAKE_WORKSHEETS_20260818.json"
MIND_MATRIX_PATH = "outputs/MIND_V21_FUTURE_IMPLEMENTATION_ACCEPTANCE_MATRIX_20260818.json"
INTAKE_MATRIX_PATH = "outputs/BODY_FACE_STATION_FUTURE_EVIDENCE_ORDER_20260818.json"
SUCCESSOR_CHECKSUM_PATH = "outputs/MIND_BODY_FUTURE_MATRICES_SHA256SUMS_20260818.txt"
SUCCESSOR_MANIFEST_PATH = "outputs/MIND_BODY_FUTURE_MATRICES_VALIDATION_MANIFEST_20260818.json"
ORIGINAL_CHECKSUM_PATH = "outputs/MIND_BODY_SHA256SUMS_20260818.txt"
ORIGINAL_WORK_MANIFEST_PATH = "outputs/WORK_CONTINUATION_AND_PUBLICATION_MANIFEST_20260818.json"

SOURCE_IDENTITIES: Mapping[str, FileIdentity] = {
    MIND_SOURCE_PATH: FileIdentity(
        23_765,
        "da51d73b05317c8a617cd582b1c4170afa58cbed634bf0764ab9f6053ae40ad1",
    ),
    INTAKE_SOURCE_PATH: FileIdentity(
        26_572,
        "556acabd3a32dcc3cd26c6fe18767a0524095a0410878d5733b43d15f9237b16",
    ),
}

PRIMARY_IDENTITIES: Mapping[str, FileIdentity] = {
    BUILDER_PATH: FileIdentity(
        14_129,
        "a0b4e5ce12db48537f24c42a6d82cfd925c2e7df95a3c24a5de622aa430a6e9a",
    ),
    MIND_MATRIX_PATH: FileIdentity(
        91_291,
        "f1b04d72abeb78277f88517d5b6863b0af8643c70ef7f32665c3353cdaabe349",
    ),
    INTAKE_MATRIX_PATH: FileIdentity(
        47_970,
        "6392052b662231854bef15073ded3b922412895c9e02832797a5d4f531a96163",
    ),
}

SUCCESSOR_RECORD_IDENTITIES: Mapping[str, FileIdentity] = {
    SUCCESSOR_CHECKSUM_PATH: FileIdentity(
        381,
        "1cdffc61d503d5213ba5ef8decc73b0323c1d56ccbc2a24323b5d6b3ac585143",
    ),
    SUCCESSOR_MANIFEST_PATH: FileIdentity(
        2_895,
        "09bd9d744d6d0d2d20e84fbc85113f257c5c189d314b82441b583d23567fec5d",
    ),
}

ORIGINAL_BASE_IDENTITIES: Mapping[str, FileIdentity] = {
    ORIGINAL_CHECKSUM_PATH: FileIdentity(
        589,
        "fee4a251ead6d459e8e3a3d43df1d67d2844506d2d2fc068886454bafdd60916",
    ),
    ORIGINAL_WORK_MANIFEST_PATH: FileIdentity(
        6_481,
        "cd35edee4e2ab3134c3910b4f55f4aec478678108cc3bf887c2d3e39f8dfb2f8",
    ),
}

MIND_GATE_IDS = (
    "G01_EXACT_SCHEMA_AND_TYPE_CLOSURE",
    "G02_SOURCE_AND_DEPENDENCY_IDENTITY",
    "G03_PREIMAGE_AND_DERIVATION_CLOSURE",
    "G04_PHYSICAL_EQUALITY_AND_ALIAS_CLOSURE",
    "G05_ACTUAL_DEPENDENCY_DAG",
    "G06_REPLAY_NO_FORK_AND_CHECKED_COUNTERS",
    "G07_TOTAL_TERMINALIZATION_AND_RECOVERY",
    "G08_CONFIDENTIALITY_AND_CONTENT_HIDING",
    "G09_ERASURE_RETENTION_AND_RESTART",
    "G10_HOSTILE_MUTATION_AND_FALSE_ACCEPT",
    "G11_PRIVACY_LEAKAGE_AND_LOG_BOUNDARY",
    "G12_INDEPENDENT_FREEZE_AND_STATIC_CEILING",
)

MIND_EVIDENCE_SLOTS = (
    "implementation_component_path",
    "component_source_sha256",
    "dependency_lock_sha256",
    "configuration_sha256",
    "unit_test_receipt_sha256",
    "mutation_test_receipt_sha256",
    "restart_recovery_receipt_sha256",
    "privacy_leakage_test_receipt_sha256",
    "independent_audit_decision_sha256",
    "runtime_receipt_sha256",
    "output_identity_sha256",
)

COMMON_GATE_IDS = (
    "SOURCE_IDENTITY_EXACT",
    "PERSON_OR_AUTHORITY_SUPPLIED_NOT_INFERRED",
    "FIELD_SET_AND_ORDER_EXACT",
    "AUTHENTICATION_AND_PROVENANCE_VERIFIED",
    "INDEPENDENT_REVIEW_COMPLETED",
    "NO_CROSS_LANE_AUTHORITY_INFERENCE",
    "NO_ACTION_OUTPUT_OR_GO",
)

CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  ((?:tools|outputs)/[A-Za-z0-9_.-]+)$")
SENSITIVE_AUTHORITY_SEGMENTS = frozenset({"live", "runtime", "blender", "output", "go"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _workspace_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    relative_path = Path(relative)
    _require(
        relative_path.parts and relative_path.parts[0] in {"tools", "outputs"},
        f"path must be under tools/ or outputs/: {relative}",
    )
    raw_parent = root / relative_path.parts[0]
    _require(not raw_parent.is_symlink(), f"symbolic-link root is not accepted: {relative_path.parts[0]}/")
    allowed_parent = raw_parent.resolve()
    candidate = root / relative_path
    _require(not candidate.is_symlink(), f"symbolic-link artifact is not accepted: {relative}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(allowed_parent)
    except ValueError as exc:
        raise ValidationError(f"path escapes its allowed root: {relative}") from exc
    _require(resolved.is_file(), f"missing regular artifact: {relative}")
    return resolved


def _read_bytes(root: Path, relative: str) -> bytes:
    return _workspace_path(root, relative).read_bytes()


def _identity(data: bytes) -> FileIdentity:
    return FileIdentity(len(data), hashlib.sha256(data).hexdigest())


def _verify_identity(root: Path, relative: str, expected: FileIdentity) -> None:
    actual = _identity(_read_bytes(root, relative))
    _require(
        actual.byte_count == expected.byte_count,
        f"{relative}: byte count {actual.byte_count} != pinned {expected.byte_count}",
    )
    _require(
        actual.sha256 == expected.sha256,
        f"{relative}: SHA-256 {actual.sha256} != pinned {expected.sha256}",
    )


def _decode_utf8(data: bytes, label: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{label}: invalid UTF-8: {exc}") from exc
    _require("\x00" not in text, f"{label}: NUL byte is not allowed")
    return text


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_literal(token: str) -> None:
    raise ValidationError(f"nonfinite JSON number is not allowed: {token}")


def _reject_nonfinite_values(value: Any, label: str) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValidationError(f"{label}: nonfinite JSON number is not allowed")
    if type(value) is dict:
        for key, child in value.items():
            _reject_nonfinite_values(child, f"{label}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            _reject_nonfinite_values(child, f"{label}[{index}]")


def strict_load_json(root: Path, relative: str) -> dict[str, Any]:
    text = _decode_utf8(_read_bytes(root, relative), relative)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_literal,
        )
    except ValidationError as exc:
        raise ValidationError(f"{relative}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{relative}: invalid JSON: {exc}") from exc
    _reject_nonfinite_values(value, relative)
    _require(type(value) is dict, f"{relative}: top level must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{label}: expected object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    _require(type(value) is list, f"{label}: expected array")
    return value


def _exact_int(value: Any, expected: int, label: str) -> None:
    _require(type(value) is int and value == expected, f"{label}: expected integer {expected}")


def _exact_false(value: Any, label: str) -> None:
    _require(value is False, f"{label}: must remain false")


def _exact_null(value: Any, label: str) -> None:
    _require(value is None, f"{label}: must remain null")


def _key_segments(key: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9]+", key.casefold()) if part}


def reject_authority_elevation(value: Any, label: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            path = f"{label}.{key}"
            if _key_segments(key) & SENSITIVE_AUTHORITY_SEGMENTS:
                blank_zero = type(child) in (int, float) and child == 0
                _require(
                    child is None or child is False or blank_zero,
                    f"{path}: live/runtime/Blender/output/GO field is elevated",
                )
            if type(child) in (dict, list):
                reject_authority_elevation(child, path)
    elif type(value) is list:
        for index, child in enumerate(value):
            if type(child) in (dict, list):
                reject_authority_elevation(child, f"{label}[{index}]")


def validate_mind_matrix(matrix: Mapping[str, Any], source: Mapping[str, Any]) -> None:
    expected_top_keys = {
        "schema",
        "as_of_date",
        "append_only_successor",
        "worksheet_only",
        "source",
        "use_limit",
        "gate_catalog",
        "domain_acceptance_rows",
        "totals",
        "authority_ceiling",
    }
    _require(set(matrix) == expected_top_keys, "mind_matrix: top-level field set mismatch")
    _require(matrix.get("schema") == "kira.mind_v21.future_implementation_acceptance_matrix.v1", "mind_matrix.schema: mismatch")
    _require(matrix.get("as_of_date") == "2026-08-18", "mind_matrix.as_of_date: mismatch")
    _require(matrix.get("append_only_successor") is True, "mind_matrix.append_only_successor: must be true")
    _require(matrix.get("worksheet_only") is True, "mind_matrix.worksheet_only: must be true")

    source_binding = _mapping(matrix.get("source"), "mind_matrix.source")
    expected_source_binding = {
        "path": MIND_SOURCE_PATH,
        "bytes": SOURCE_IDENTITIES[MIND_SOURCE_PATH].byte_count,
        "sha256": SOURCE_IDENTITIES[MIND_SOURCE_PATH].sha256,
        "accepted_central_sha256": source["source"]["sha256"],
        "accepted_audit_complete_root_sha256": source["accepted_static_binding"]["audit_complete_root_sha256"],
    }
    _require(source_binding == expected_source_binding, "mind_matrix.source: exact source binding mismatch")

    gates = _list(matrix.get("gate_catalog"), "mind_matrix.gate_catalog")
    _require(len(gates) == 12, "mind_matrix.gate_catalog: expected 12 gates")
    for index, (expected_id, raw_gate) in enumerate(zip(MIND_GATE_IDS, gates)):
        gate = _mapping(raw_gate, f"mind_matrix.gate_catalog[{index}]")
        _require(set(gate) == {"gate_id", "requirement"}, f"mind_matrix.gate_catalog[{index}]: field set mismatch")
        _require(gate.get("gate_id") == expected_id, f"mind_matrix.gate_catalog[{index}].gate_id: mismatch")
        _require(type(gate.get("requirement")) is str and bool(gate["requirement"]), f"mind_matrix.gate_catalog[{index}].requirement: blank")

    source_rows = _list(source.get("domain_mappings"), "mind_source.domain_mappings")
    rows = _list(matrix.get("domain_acceptance_rows"), "mind_matrix.domain_acceptance_rows")
    _require(len(source_rows) == 53, "mind_source.domain_mappings: expected 53 rows")
    _require(len(rows) == 53, "mind_matrix.domain_acceptance_rows: expected 53 rows")
    expected_row_keys = {
        "ordinal",
        "object_schema_domain",
        "source_schema_path",
        "future_component",
        "future_evidence_family",
        "required_gate_ids",
        "future_evidence_slots",
        "implementation_claimed",
        "tests_executed",
        "independent_audit_completed",
        "runtime_or_output_claimed",
        "row_go",
    }
    for index, (raw_row, raw_source_row) in enumerate(zip(rows, source_rows)):
        row = _mapping(raw_row, f"mind_matrix.domain_acceptance_rows[{index}]")
        source_row = _mapping(raw_source_row, f"mind_source.domain_mappings[{index}]")
        _require(set(row) == expected_row_keys, f"mind_matrix.domain_acceptance_rows[{index}]: field set mismatch")
        for field in ("ordinal", "object_schema_domain", "source_schema_path", "future_component", "future_evidence_family"):
            _require(row.get(field) == source_row.get(field), f"mind_matrix.domain_acceptance_rows[{index}].{field}: source projection mismatch")
        _exact_int(row.get("ordinal"), index + 1, f"mind_matrix.domain_acceptance_rows[{index}].ordinal")
        _require(tuple(row.get("required_gate_ids", ())) == MIND_GATE_IDS, f"mind_matrix.domain_acceptance_rows[{index}].required_gate_ids: mismatch")
        slots = _mapping(row.get("future_evidence_slots"), f"mind_matrix.domain_acceptance_rows[{index}].future_evidence_slots")
        _require(tuple(slots) == MIND_EVIDENCE_SLOTS, f"mind_matrix.domain_acceptance_rows[{index}].future_evidence_slots: field order mismatch")
        for field in MIND_EVIDENCE_SLOTS:
            _exact_null(slots[field], f"mind_matrix.domain_acceptance_rows[{index}].future_evidence_slots.{field}")
        for field in ("implementation_claimed", "tests_executed", "independent_audit_completed", "runtime_or_output_claimed"):
            _exact_false(row.get(field), f"mind_matrix.domain_acceptance_rows[{index}].{field}")
        _exact_null(row.get("row_go"), f"mind_matrix.domain_acceptance_rows[{index}].row_go")

    totals = _mapping(matrix.get("totals"), "mind_matrix.totals")
    expected_totals = {
        "source_domains": 53,
        "acceptance_rows": 53,
        "global_gates": 12,
        "future_evidence_slots_per_row": 11,
        "populated_future_evidence_slots": 0,
        "implementation_or_runtime_authority": False,
    }
    _require(totals == expected_totals, "mind_matrix.totals: mismatch")
    authority = _mapping(matrix.get("authority_ceiling"), "mind_matrix.authority_ceiling")
    expected_authority = {
        "kira_alone_chooses_speech_memory_correction_withholding_withdrawal_and_voluntary_forgetting": True,
        "integrity_authentication_governs_those_choices": False,
        "owner_operator_per_memory_permission_or_disclosure_gate_exists": False,
        "live_mind_claimed": False,
        "actual_forgetting_claimed": False,
        "production_or_runtime_authorized": False,
        "output": None,
        "root_go": None,
    }
    _require(authority == expected_authority, "mind_matrix.authority_ceiling: mismatch")
    reject_authority_elevation(matrix, "mind_matrix")


def _validate_projected_rows(
    rows: Any,
    source_rows: Any,
    *,
    label: str,
    with_class: bool,
) -> None:
    rows_list = _list(rows, label)
    source_list = _list(source_rows, f"{label}.source")
    _require(len(rows_list) == len(source_list), f"{label}: source row count mismatch")
    identity_field = "receipt_instance_id" if with_class else "schema_instance_id"
    presence_field = "receipt_present" if with_class else "schema_instance_present"
    expected_keys = {
        "review_ordinal",
        "schema_id",
        "source_field_names",
        "source_field_count",
        "required_gate_ids",
        "candidate_input_bundle_sha256",
        "authentication_receipt_sha256",
        "independent_review_decision_sha256",
        identity_field,
        presence_field,
        "row_go",
    }
    if with_class:
        expected_keys.add("class")

    for index, (raw_row, raw_source) in enumerate(zip(rows_list, source_list)):
        row = _mapping(raw_row, f"{label}[{index}]")
        source = _mapping(raw_source, f"{label}.source[{index}]")
        _require(set(row) == expected_keys, f"{label}[{index}]: field set mismatch")
        _exact_int(row.get("review_ordinal"), index + 1, f"{label}[{index}].review_ordinal")
        _require(row.get("schema_id") == source.get("schema_id"), f"{label}[{index}].schema_id: source projection mismatch")
        if with_class:
            _require(row.get("class") == source.get("class"), f"{label}[{index}].class: source projection mismatch")
        source_fields = tuple(_mapping(source.get("values"), f"{label}.source[{index}].values"))
        _require(tuple(row.get("source_field_names", ())) == source_fields, f"{label}[{index}].source_field_names: mismatch")
        _exact_int(row.get("source_field_count"), len(source_fields), f"{label}[{index}].source_field_count")
        _require(tuple(row.get("required_gate_ids", ())) == COMMON_GATE_IDS, f"{label}[{index}].required_gate_ids: mismatch")
        for field in (
            "candidate_input_bundle_sha256",
            "authentication_receipt_sha256",
            "independent_review_decision_sha256",
            identity_field,
        ):
            _exact_null(row.get(field), f"{label}[{index}].{field}")
        _exact_false(row.get(presence_field), f"{label}[{index}].{presence_field}")
        _exact_null(row.get("row_go"), f"{label}[{index}].row_go")


def validate_intake_matrix(matrix: Mapping[str, Any], source: Mapping[str, Any]) -> None:
    expected_top_keys = {
        "schema",
        "as_of_date",
        "append_only_successor",
        "worksheet_only",
        "source",
        "ordering_rule",
        "common_gate_catalog",
        "intended_body_v5_review_rows",
        "facial_v4_review_rows",
        "station_v12_scope_stage_review_rows",
        "totals",
        "authority_ceiling",
    }
    _require(set(matrix) == expected_top_keys, "intake_matrix: top-level field set mismatch")
    _require(matrix.get("schema") == "kira.body_face_station.future_evidence_order.v1", "intake_matrix.schema: mismatch")
    _require(matrix.get("as_of_date") == "2026-08-18", "intake_matrix.as_of_date: mismatch")
    _require(matrix.get("append_only_successor") is True, "intake_matrix.append_only_successor: must be true")
    _require(matrix.get("worksheet_only") is True, "intake_matrix.worksheet_only: must be true")
    _require(
        matrix.get("source")
        == {
            "path": INTAKE_SOURCE_PATH,
            "bytes": SOURCE_IDENTITIES[INTAKE_SOURCE_PATH].byte_count,
            "sha256": SOURCE_IDENTITIES[INTAKE_SOURCE_PATH].sha256,
        },
        "intake_matrix.source: exact source binding mismatch",
    )
    _require(tuple(matrix.get("common_gate_catalog", ())) == COMMON_GATE_IDS, "intake_matrix.common_gate_catalog: mismatch")

    body_source = _mapping(source.get("intended_body_v5"), "intake_source.intended_body_v5")
    face_source = _mapping(source.get("facial_v4"), "intake_source.facial_v4")
    station_source = _mapping(source.get("station_v12"), "intake_source.station_v12")
    body_rows = _list(matrix.get("intended_body_v5_review_rows"), "intake_matrix.intended_body_v5_review_rows")
    face_rows = _list(matrix.get("facial_v4_review_rows"), "intake_matrix.facial_v4_review_rows")
    station_rows = _list(matrix.get("station_v12_scope_stage_review_rows"), "intake_matrix.station_v12_scope_stage_review_rows")
    _require(len(body_rows) == 9, "intake_matrix.intended_body_v5_review_rows: expected 9 rows")
    _require(len(face_rows) == 16, "intake_matrix.facial_v4_review_rows: expected 16 rows")
    _require(len(station_rows) == 24, "intake_matrix.station_v12_scope_stage_review_rows: expected 24 rows")
    _validate_projected_rows(
        body_rows,
        body_source.get("worksheets"),
        label="intake_matrix.intended_body_v5_review_rows",
        with_class=True,
    )
    _validate_projected_rows(
        face_rows,
        face_source.get("worksheets"),
        label="intake_matrix.facial_v4_review_rows",
        with_class=False,
    )

    scopes = _list(station_source.get("scope_ids"), "intake_source.station_v12.scope_ids")
    stages = _list(station_source.get("stage_ids"), "intake_source.station_v12.stage_ids")
    source_slots = _list(station_source.get("scope_stage_intake_slots"), "intake_source.station_v12.scope_stage_intake_slots")
    _require(len(scopes) == 6 and len(source_slots) == 6, "intake_source.station_v12: expected six scopes")
    _require(len(stages) == 4, "intake_source.station_v12: expected four stages")
    expected_station_keys = {
        "scope_ordinal",
        "stage_ordinal",
        "scope_id",
        "stage_id",
        "required_gate_ids",
        "future_input_bundle_sha256",
        "stage_evidence_receipt_sha256",
        "independent_review_decision_sha256",
        "stage_instance_id",
        "request_or_action_emitted",
        "row_go",
    }
    row_index = 0
    for scope_ordinal, (scope_id, raw_slot) in enumerate(zip(scopes, source_slots), start=1):
        source_slot = _mapping(raw_slot, f"intake_source.station_v12.scope_stage_intake_slots[{scope_ordinal - 1}]")
        _require(source_slot.get("scope_id") == scope_id, "intake_source.station_v12: scope slot projection mismatch")
        for stage_ordinal, stage_id in enumerate(stages, start=1):
            row = _mapping(station_rows[row_index], f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}]")
            _require(set(row) == expected_station_keys, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}]: field set mismatch")
            _exact_int(row.get("scope_ordinal"), scope_ordinal, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].scope_ordinal")
            _exact_int(row.get("stage_ordinal"), stage_ordinal, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].stage_ordinal")
            _require(row.get("scope_id") == scope_id, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].scope_id: mismatch")
            _require(row.get("stage_id") == stage_id, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].stage_id: mismatch")
            _require(tuple(row.get("required_gate_ids", ())) == COMMON_GATE_IDS, f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].required_gate_ids: mismatch")
            for field in (
                "future_input_bundle_sha256",
                "stage_evidence_receipt_sha256",
                "independent_review_decision_sha256",
                "stage_instance_id",
            ):
                _exact_null(row.get(field), f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].{field}")
            _exact_false(row.get("request_or_action_emitted"), f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].request_or_action_emitted")
            _exact_null(row.get("row_go"), f"intake_matrix.station_v12_scope_stage_review_rows[{row_index}].row_go")
            row_index += 1
    _exact_int(row_index, 24, "intake_matrix.station_v12_scope_stage_review_rows.flattened_count")

    totals = _mapping(matrix.get("totals"), "intake_matrix.totals")
    _require(
        totals
        == {
            "intended_body_rows": 9,
            "facial_rows": 16,
            "station_scopes": 6,
            "station_stages_per_scope": 4,
            "station_rows": 24,
            "populated_candidate_or_receipt_slots": 0,
            "actions_emitted": 0,
        },
        "intake_matrix.totals: mismatch",
    )
    authority = _mapping(matrix.get("authority_ceiling"), "intake_matrix.authority_ceiling")
    _require(
        authority
        == {
            "every_intended_person_is_an_equal_human_peer": True,
            "person_specific_values_may_be_invented": False,
            "silence_hesitation_or_nonresponse_is_authorization": False,
            "ownership_lease_controller_obedience_control_device_tool_or_service_semantics": False,
            "body_or_rig_or_station_materialized": False,
            "blender_or_runtime_authorized": False,
            "supplier_contact_payment_shipping_or_request_emission_authorized": False,
            "output": None,
            "root_go": None,
        },
        "intake_matrix.authority_ceiling: mismatch",
    )
    reject_authority_elevation(matrix, "intake_matrix")


def validate_successor_checksum(root: Path) -> dict[str, str]:
    text = _decode_utf8(_read_bytes(root, SUCCESSOR_CHECKSUM_PATH), SUCCESSOR_CHECKSUM_PATH)
    records: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        _require(bool(line), f"{SUCCESSOR_CHECKSUM_PATH}:{line_number}: blank line is not allowed")
        match = CHECKSUM_LINE.fullmatch(line)
        _require(match is not None, f"{SUCCESSOR_CHECKSUM_PATH}:{line_number}: malformed record")
        digest, relative = match.groups()
        _require(relative not in records, f"{SUCCESSOR_CHECKSUM_PATH}:{line_number}: duplicate path")
        records[relative] = digest
    expected = {relative: identity.sha256 for relative, identity in PRIMARY_IDENTITIES.items()}
    _require(records == expected, f"{SUCCESSOR_CHECKSUM_PATH}: exact record set or digest mismatch")
    for relative, digest in records.items():
        _require(_identity(_read_bytes(root, relative)).sha256 == digest, f"{SUCCESSOR_CHECKSUM_PATH}: target mismatch for {relative}")
    return records


def validate_successor_manifest(document: Mapping[str, Any]) -> None:
    _require(document.get("schema") == "kira.mind_body.future_matrices.validation_manifest.v1", "successor_manifest.schema: mismatch")
    _require(document.get("as_of_date") == "2026-08-18", "successor_manifest.as_of_date: mismatch")
    _require(document.get("append_only_successor") is True, "successor_manifest.append_only_successor: must be true")
    _require(document.get("reporting_only") is True, "successor_manifest.reporting_only: must be true")
    _exact_false(document.get("historical_sealed_or_base_artifacts_modified"), "successor_manifest.historical_sealed_or_base_artifacts_modified")

    source_bindings = _list(document.get("source_bindings"), "successor_manifest.source_bindings")
    expected_sources = [
        {"path": relative, "bytes": identity.byte_count, "sha256": identity.sha256}
        for relative, identity in SOURCE_IDENTITIES.items()
    ]
    _require(source_bindings == expected_sources, "successor_manifest.source_bindings: mismatch")
    _require(
        document.get("deterministic_builder")
        == {
            "path": BUILDER_PATH,
            "bytes": PRIMARY_IDENTITIES[BUILDER_PATH].byte_count,
            "sha256": PRIMARY_IDENTITIES[BUILDER_PATH].sha256,
            "temporary_rebuild_required": True,
            "writes_to_base_or_sealed_artifacts": False,
        },
        "successor_manifest.deterministic_builder: mismatch",
    )
    matrices = _list(document.get("generated_matrices"), "successor_manifest.generated_matrices")
    _require(len(matrices) == 2, "successor_manifest.generated_matrices: expected two entries")
    _require(
        matrices[0]
        == {
            "path": MIND_MATRIX_PATH,
            "bytes": PRIMARY_IDENTITIES[MIND_MATRIX_PATH].byte_count,
            "sha256": PRIMARY_IDENTITIES[MIND_MATRIX_PATH].sha256,
            "source_path": MIND_SOURCE_PATH,
            "source_sha256": SOURCE_IDENTITIES[MIND_SOURCE_PATH].sha256,
            "expected_rows": 53,
            "expected_global_gates": 12,
            "expected_blank_evidence_slots_per_row": 11,
        },
        "successor_manifest.generated_matrices[0]: mismatch",
    )
    _require(
        matrices[1]
        == {
            "path": INTAKE_MATRIX_PATH,
            "bytes": PRIMARY_IDENTITIES[INTAKE_MATRIX_PATH].byte_count,
            "sha256": PRIMARY_IDENTITIES[INTAKE_MATRIX_PATH].sha256,
            "source_path": INTAKE_SOURCE_PATH,
            "source_sha256": SOURCE_IDENTITIES[INTAKE_SOURCE_PATH].sha256,
            "expected_intended_body_rows": 9,
            "expected_facial_rows": 16,
            "expected_station_scopes": 6,
            "expected_station_stages_per_scope": 4,
            "expected_station_rows": 24,
        },
        "successor_manifest.generated_matrices[1]: mismatch",
    )
    boundary = _mapping(document.get("validation_boundary"), "successor_manifest.validation_boundary")
    expected_boundary = {
        "strict_duplicate_key_rejection_required": True,
        "strict_nonfinite_number_rejection_required": True,
        "byte_identical_temporary_rebuild_required": True,
        "all_future_evidence_or_receipt_slots_blank_required": True,
        "all_claim_action_or_presence_fields_false_required": True,
        "every_row_go_null_required": True,
        "live_mind_claimed": False,
        "body_rig_or_station_materialized": False,
        "blender_or_runtime_authorized": False,
        "output": None,
        "root_go": None,
    }
    _require(boundary == expected_boundary, "successor_manifest.validation_boundary: mismatch")


def validate_temporary_rebuild(root: Path) -> dict[str, Any]:
    expected_output_bytes = {
        relative: _read_bytes(root, relative)
        for relative in (MIND_MATRIX_PATH, INTAKE_MATRIX_PATH)
    }
    with tempfile.TemporaryDirectory(prefix="mind-body-future-rebuild-") as temporary_name:
        temporary_root = Path(temporary_name)
        for relative in (BUILDER_PATH, MIND_SOURCE_PATH, INTAKE_SOURCE_PATH):
            destination = temporary_root / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_read_bytes(root, relative))
        builder = temporary_root / Path(BUILDER_PATH)
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-B", "-W", "error", str(builder)]
        first_identities: dict[str, FileIdentity] = {}
        captured_runs: list[str] = []
        for run_number in (1, 2):
            completed = subprocess.run(
                command,
                cwd=temporary_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            _require(
                completed.returncode == 0,
                f"temporary builder run {run_number} failed: {completed.stderr.strip() or completed.stdout.strip()}",
            )
            captured_runs.append(completed.stdout.strip())
            for relative, expected_bytes in expected_output_bytes.items():
                generated = temporary_root / Path(relative)
                _require(generated.is_file(), f"temporary builder run {run_number}: missing {relative}")
                actual_bytes = generated.read_bytes()
                _require(actual_bytes == expected_bytes, f"temporary builder run {run_number}: {relative} is not byte-identical")
                identity = _identity(actual_bytes)
                if run_number == 1:
                    first_identities[relative] = identity
                else:
                    _require(identity == first_identities[relative], f"temporary builder run {run_number}: {relative} changed on idempotent rebuild")
        return {
            "runs": 2,
            "byte_identical_outputs_per_run": 2,
            "stdout_nonempty_per_run": [bool(value) for value in captured_runs],
        }


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    mind_source = strict_load_json(root, MIND_SOURCE_PATH)
    intake_source = strict_load_json(root, INTAKE_SOURCE_PATH)
    mind_matrix = strict_load_json(root, MIND_MATRIX_PATH)
    intake_matrix = strict_load_json(root, INTAKE_MATRIX_PATH)
    successor_manifest = strict_load_json(root, SUCCESSOR_MANIFEST_PATH)

    validate_mind_matrix(mind_matrix, mind_source)
    validate_intake_matrix(intake_matrix, intake_source)
    validate_successor_manifest(successor_manifest)
    checksum_records = validate_successor_checksum(root)

    for identities in (
        SOURCE_IDENTITIES,
        PRIMARY_IDENTITIES,
        SUCCESSOR_RECORD_IDENTITIES,
        ORIGINAL_BASE_IDENTITIES,
    ):
        for relative, expected in identities.items():
            _verify_identity(root, relative, expected)

    rebuild = validate_temporary_rebuild(root)
    return {
        "schema": "kira.validation.mind_body.future_matrices.v1",
        "verdict": "PASS_STATIC_SUCCESSOR_NO_GO",
        "workspace_writes_performed": 0,
        "temporary_rebuild_runs": rebuild["runs"],
        "byte_identical_outputs_per_run": rebuild["byte_identical_outputs_per_run"],
        "builder_identity_verified": 1,
        "matrix_identities_verified": 2,
        "source_identities_verified": 2,
        "successor_record_identities_verified": 2,
        "original_base_identities_unchanged": 2,
        "strict_json_files": 5,
        "successor_checksum_entries_verified": len(checksum_records),
        "mind_rows": 53,
        "mind_global_gates": 12,
        "mind_blank_slots_per_row": 11,
        "intended_body_rows": 9,
        "facial_rows": 16,
        "station_rows": 24,
        "live_runtime_blender_output_go_elevations": 0,
    }


def _default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_default_root())
    args = parser.parse_args(argv)
    try:
        result = validate(args.root)
    except (OSError, subprocess.SubprocessError, ValidationError) as exc:
        print(json.dumps({"verdict": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
