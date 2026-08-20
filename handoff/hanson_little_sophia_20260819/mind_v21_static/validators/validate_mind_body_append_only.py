#!/usr/bin/env python3
"""Read-only validator for the 2026-08-18 Mind/Body append-only artifacts.

The validator has no write path.  It independently pins the accepted file
identities, strict-parses every JSON document, checks the checksum and work
manifest projections, and re-checks the blank/no-GO semantic boundaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ValidationError(RuntimeError):
    """Raised when an artifact fails a read-only validation check."""


@dataclass(frozen=True)
class FileIdentity:
    byte_count: int
    sha256: str


EXPECTED_MANIFEST_ENTRIES: Mapping[str, FileIdentity] = {
    "outputs/MIND_BODY_SHA256SUMS_20260818.txt": FileIdentity(
        589,
        "fee4a251ead6d459e8e3a3d43df1d67d2844506d2d2fc068886454bafdd60916",
    ),
    "outputs/MIND_BODY_STATIC_READINESS_BASELINE_20260818.json": FileIdentity(
        14_775,
        "689a8d0edc0385f9d83b691b28d32eaee159f54ec47490cba525f000a2125470",
    ),
    "outputs/MIND_V21_IMPLEMENTATION_TRACEABILITY_WORKSHEET_20260818.json": FileIdentity(
        23_765,
        "da51d73b05317c8a617cd582b1c4170afa58cbed634bf0764ab9f6053ae40ad1",
    ),
    "outputs/BODY_FACE_STATION_INTAKE_WORKSHEETS_20260818.json": FileIdentity(
        26_572,
        "556acabd3a32dcc3cd26c6fe18767a0524095a0410878d5733b43d15f9237b16",
    ),
    "outputs/CROSS_LANE_NO_GO_READINESS_MATRIX_20260818.md": FileIdentity(
        6_593,
        "101d8cfb12b1039a025580d3f4e6e59b921de81391e2afa2733500bdcdc412f8",
    ),
    "outputs/MIND_BODY_APPEND_ONLY_VALIDATION_REPORT_20260818.md": FileIdentity(
        4_302,
        "24a253f27c02e8763b9806705cdb48cd9b2a4d7ef04a406d08de8e796b07923e",
    ),
}

EXPECTED_WORK_MANIFEST = FileIdentity(
    6_481,
    "cd35edee4e2ab3134c3910b4f55f4aec478678108cc3bf887c2d3e39f8dfb2f8",
)

WORK_MANIFEST_PATH = "outputs/WORK_CONTINUATION_AND_PUBLICATION_MANIFEST_20260818.json"
CHECKSUM_PATH = "outputs/MIND_BODY_SHA256SUMS_20260818.txt"
BASELINE_PATH = "outputs/MIND_BODY_STATIC_READINESS_BASELINE_20260818.json"
MIND_PATH = "outputs/MIND_V21_IMPLEMENTATION_TRACEABILITY_WORKSHEET_20260818.json"
BODY_PATH = "outputs/BODY_FACE_STATION_INTAKE_WORKSHEETS_20260818.json"
MATRIX_PATH = "outputs/CROSS_LANE_NO_GO_READINESS_MATRIX_20260818.md"

EXPECTED_LANES = {
    "mind_v21",
    "female_cleanup_v24",
    "intended_body_v5",
    "facial_v4",
    "station_v12",
}

EXPECTED_STATION_SCOPES = (
    "F0_MATERIAL_AND_CONSTRUCTION_COUPONS",
    "F1_STORAGE_AND_SUPPORTS",
    "F2_NON_PERSON_ARTICULATED_FIXTURE",
    "F2_LEFT_MANIPULATOR",
    "F2_RIGHT_MANIPULATOR",
    "F2_SOLVER_RECORDER_CALIBRATION_INPUTS",
)

EXPECTED_STATION_STAGES = (
    "OWNER_REVIEW",
    "REQUEST_CANDIDATE",
    "REQUEST_EMISSION",
    "RECEIPT_INTAKE",
)

CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9_.-]+)$")
SENSITIVE_AUTHORITY_SEGMENTS = frozenset({"live", "runtime", "blender", "output", "go"})
SAFE_SENSITIVE_REFERENCE_CONTAINERS = frozenset({"runtime_binding_profile"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _artifact_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    raw_output_root = root / "outputs"
    _require(not raw_output_root.is_symlink(), "outputs/: symbolic-link roots are not accepted")
    output_root = raw_output_root.resolve()
    candidate = root / Path(relative)
    _require(not candidate.is_symlink(), f"symbolic-link artifacts are not accepted: {relative}")
    path = candidate.resolve()
    try:
        path.relative_to(output_root)
    except ValueError as exc:
        raise ValidationError(f"artifact path escapes outputs/: {relative}") from exc
    _require(path.is_file(), f"missing regular artifact: {relative}")
    return path


def _read_bytes(root: Path, relative: str) -> bytes:
    return _artifact_path(root, relative).read_bytes()


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


def _reject_nonfinite(token: str) -> None:
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
    """Strictly load one UTF-8 JSON object without duplicates or nonfinite numbers."""

    text = _decode_utf8(_read_bytes(root, relative), relative)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except ValidationError as exc:
        raise ValidationError(f"{relative}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{relative}: invalid JSON: {exc}") from exc
    _reject_nonfinite_values(value, relative)
    _require(type(value) is dict, f"{relative}: top level must be a JSON object")
    return value


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


def _mapping(value: Any, label: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{label}: expected object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    _require(type(value) is list, f"{label}: expected array")
    return value


def _exact_false(value: Any, label: str) -> None:
    _require(value is False, f"{label}: must remain false")


def _exact_null(value: Any, label: str) -> None:
    _require(value is None, f"{label}: must remain null")


def _exact_int(value: Any, expected: int, label: str) -> None:
    _require(type(value) is int and value == expected, f"{label}: must equal integer {expected}")


def _key_segments(key: str) -> set[str]:
    return {segment for segment in re.split(r"[^a-z0-9]+", key.casefold()) if segment}


def reject_authority_elevation(value: Any, label: str) -> None:
    """Reject positive/live values on live/runtime/Blender/output/GO-labelled fields."""

    if type(value) is dict:
        for key, child in value.items():
            path = f"{label}.{key}"
            segments = _key_segments(key)
            if segments & SENSITIVE_AUTHORITY_SEGMENTS:
                if type(child) in (dict, list):
                    _require(
                        key.casefold() in SAFE_SENSITIVE_REFERENCE_CONTAINERS,
                        f"{path}: live/runtime/Blender/output/GO field is elevated",
                    )
                else:
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


def validate_baseline(document: Mapping[str, Any]) -> None:
    _require(
        document.get("schema") == "kira.mind_body.static_readiness_baseline.v1",
        "baseline.schema: unexpected schema",
    )
    _require(document.get("reporting_only") is True, "baseline.reporting_only: must be true")
    _require(document.get("append_only_successor") is True, "baseline.append_only_successor: must be true")
    _exact_false(document.get("historical_artifacts_modified"), "baseline.historical_artifacts_modified")

    authority = _mapping(document.get("global_authority_state"), "baseline.global_authority_state")
    expected_false = (
        "implementation_authorized",
        "live_memory_authorized",
        "executed_erasure_or_actual_forgetting_claimed",
        "production_private_store_authorized",
        "body_created_or_approved",
        "body_build_authorized",
        "rig_created_or_approved",
        "station_materialized",
        "blender_invocation_authorized",
        "runtime_authorized",
        "run_authorized",
        "output_authorized",
        "publication_authorized",
        "global_action_authorized",
    )
    expected_null = ("root_go", "output", "preflight", "live_identity", "live_artifact_pin")
    _require(
        set(authority) == set(expected_false) | set(expected_null),
        "baseline.global_authority_state: unexpected or missing fields",
    )
    for key in expected_false:
        _exact_false(authority[key], f"baseline.global_authority_state.{key}")
    for key in expected_null:
        _exact_null(authority[key], f"baseline.global_authority_state.{key}")

    lanes = _mapping(document.get("accepted_static_lanes"), "baseline.accepted_static_lanes")
    _require(set(lanes) == EXPECTED_LANES, "baseline.accepted_static_lanes: lane set mismatch")
    reject_authority_elevation(document, "baseline")


def validate_mind(document: Mapping[str, Any]) -> None:
    _require(
        document.get("schema") == "kira.mind.v21.implementation_traceability_worksheet.v1",
        "mind.schema: unexpected schema",
    )
    _require(document.get("worksheet_only") is True, "mind.worksheet_only: must be true")
    for key in ("implementation_claimed", "runtime_claimed", "live_memory_claimed", "actual_forgetting_claimed"):
        _exact_false(document.get(key), f"mind.{key}")
    _exact_null(document.get("go"), "mind.go")

    source = _mapping(document.get("source"), "mind.source")
    _exact_int(source.get("object_schema_domain_count"), 53, "mind.source.object_schema_domain_count")
    mappings = _list(document.get("domain_mappings"), "mind.domain_mappings")
    _require(len(mappings) == 53, "mind.domain_mappings: expected exactly 53 rows")

    domains: set[str] = set()
    for ordinal, raw_row in enumerate(mappings, start=1):
        row = _mapping(raw_row, f"mind.domain_mappings[{ordinal - 1}]")
        _exact_int(row.get("ordinal"), ordinal, f"mind.domain_mappings[{ordinal - 1}].ordinal")
        domain = row.get("object_schema_domain")
        _require(type(domain) is str and bool(domain), f"mind.domain_mappings[{ordinal - 1}]: invalid domain")
        _require(domain not in domains, f"mind.domain_mappings: duplicate domain {domain!r}")
        domains.add(domain)
        _require(
            row.get("source_schema_path") == f"$.objects.{domain}",
            f"mind.domain_mappings[{ordinal - 1}]: source path mismatch",
        )
        _require(row.get("worksheet_only") is True, f"mind.domain_mappings[{ordinal - 1}].worksheet_only: must be true")
        for field in ("materialized_path", "materialized_pin_sha256", "materialized_identity"):
            _exact_null(row.get(field), f"mind.domain_mappings[{ordinal - 1}].{field}")
    reject_authority_elevation(document, "mind")


def _validate_blank_worksheets(
    raw_worksheets: Any,
    *,
    count: int,
    label: str,
    schema_prefix: str,
    presence_field: str,
    with_class: bool,
) -> None:
    worksheets = _list(raw_worksheets, label)
    _require(len(worksheets) == count, f"{label}: expected exactly {count} blank schema classes")
    schema_ids: set[str] = set()
    classes: set[str] = set()
    expected_keys = {"schema_id", "values", presence_field, "authenticated", "evidence_claimed"}
    if with_class:
        expected_keys.add("class")

    for index, raw_worksheet in enumerate(worksheets):
        item_label = f"{label}[{index}]"
        worksheet = _mapping(raw_worksheet, item_label)
        _require(set(worksheet) == expected_keys, f"{item_label}: unexpected or missing fields")
        schema_id = worksheet.get("schema_id")
        _require(
            type(schema_id) is str and schema_id.startswith(schema_prefix),
            f"{item_label}.schema_id: unexpected identifier",
        )
        _require(schema_id not in schema_ids, f"{label}: duplicate schema_id {schema_id!r}")
        schema_ids.add(schema_id)
        if with_class:
            class_name = worksheet.get("class")
            _require(type(class_name) is str and bool(class_name), f"{item_label}.class: invalid class")
            _require(class_name not in classes, f"{label}: duplicate class {class_name!r}")
            classes.add(class_name)
        values = _mapping(worksheet.get("values"), f"{item_label}.values")
        _require(bool(values), f"{item_label}.values: must declare at least one blank field")
        for field, value in values.items():
            _exact_null(value, f"{item_label}.values.{field}")
        for field in (presence_field, "authenticated", "evidence_claimed"):
            _exact_false(worksheet.get(field), f"{item_label}.{field}")


def validate_body_face_station(document: Mapping[str, Any]) -> None:
    _require(
        document.get("schema") == "kira.body_face_station.intake_worksheets.v1",
        "body_face_station.schema: unexpected schema",
    )
    _require(document.get("worksheet_only") is True, "body_face_station.worksheet_only: must be true")
    _require(document.get("append_only_successor") is True, "body_face_station.append_only_successor: must be true")
    for key in ("receipt_claimed", "evidence_claimed", "acquisition_claimed", "body_or_rig_or_station_materialized", "blender_or_runtime_action_authorized"):
        _exact_false(document.get(key), f"body_face_station.{key}")
    _exact_null(document.get("output"), "body_face_station.output")
    _exact_null(document.get("root_go"), "body_face_station.root_go")

    body = _mapping(document.get("intended_body_v5"), "body_face_station.intended_body_v5")
    _exact_int(body.get("receipt_schema_class_count"), 9, "body_face_station.intended_body_v5.receipt_schema_class_count")
    _exact_false(body.get("actual_receipts_acquired"), "body_face_station.intended_body_v5.actual_receipts_acquired")
    _validate_blank_worksheets(
        body.get("worksheets"),
        count=9,
        label="body_face_station.intended_body_v5.worksheets",
        schema_prefix="kira.receipt.intended_body.",
        presence_field="receipt_present",
        with_class=True,
    )

    face = _mapping(document.get("facial_v4"), "body_face_station.facial_v4")
    _exact_int(face.get("receipt_schema_class_count"), 16, "body_face_station.facial_v4.receipt_schema_class_count")
    _exact_false(
        face.get("actual_mapping_or_timeline_receipts_acquired"),
        "body_face_station.facial_v4.actual_mapping_or_timeline_receipts_acquired",
    )
    _exact_false(face.get("F06_audio_authorized"), "body_face_station.facial_v4.F06_audio_authorized")
    _validate_blank_worksheets(
        face.get("worksheets"),
        count=16,
        label="body_face_station.facial_v4.worksheets",
        schema_prefix="kira.receipt.facial_",
        presence_field="schema_instance_present",
        with_class=False,
    )

    station = _mapping(document.get("station_v12"), "body_face_station.station_v12")
    station_source = _mapping(station.get("source"), "body_face_station.station_v12.source")
    runtime_profile = _mapping(
        station_source.get("runtime_binding_profile"),
        "body_face_station.station_v12.source.runtime_binding_profile",
    )
    _require(
        runtime_profile
        == {
            "path": "work/shared_person_garment_mechanics_test_station_v12_complete_runtime_binding_correction_data_only_author_source/V12_COMPLETE_RUNTIME_BINDING_PROFILE.json",
            "bytes": 75_204,
            "sha256": "d3ec10529afe04f960ae7ebbf461ee3f35c99a7852b478b6870fe52b467c67d8",
        },
        "body_face_station.station_v12.source.runtime_binding_profile: static identity mismatch",
    )
    _exact_int(station.get("future_gate_instance_count"), 0, "body_face_station.station_v12.future_gate_instance_count")
    scopes = _list(station.get("scope_ids"), "body_face_station.station_v12.scope_ids")
    stages = _list(station.get("stage_ids"), "body_face_station.station_v12.stage_ids")
    _require(tuple(scopes) == EXPECTED_STATION_SCOPES, "body_face_station.station_v12.scope_ids: exact six-scope order mismatch")
    _require(tuple(stages) == EXPECTED_STATION_STAGES, "body_face_station.station_v12.stage_ids: exact four-stage order mismatch")

    slots = _list(station.get("scope_stage_intake_slots"), "body_face_station.station_v12.scope_stage_intake_slots")
    _require(len(slots) == 6, "body_face_station.station_v12.scope_stage_intake_slots: expected six rows")
    blank_slots = 0
    for index, (expected_scope, raw_slot_row) in enumerate(zip(EXPECTED_STATION_SCOPES, slots)):
        row = _mapping(raw_slot_row, f"body_face_station.station_v12.scope_stage_intake_slots[{index}]")
        _require(
            set(row) == {"scope_id", *EXPECTED_STATION_STAGES},
            f"body_face_station.station_v12.scope_stage_intake_slots[{index}]: field set mismatch",
        )
        _require(row.get("scope_id") == expected_scope, f"body_face_station.station_v12.scope_stage_intake_slots[{index}]: scope mismatch")
        for stage in EXPECTED_STATION_STAGES:
            _exact_null(row.get(stage), f"body_face_station.station_v12.scope_stage_intake_slots[{index}].{stage}")
            blank_slots += 1
    _exact_int(blank_slots, 24, "body_face_station.station_v12.blank_stage_slot_count")

    template = _mapping(station.get("blank_current_state_template"), "body_face_station.station_v12.blank_current_state_template")
    _require(len(template) == 72, "body_face_station.station_v12.blank_current_state_template: expected exactly 72 fields")
    for field, value in template.items():
        _require(
            value is None or value is False,
            f"body_face_station.station_v12.blank_current_state_template.{field}: must remain null/false",
        )

    operational = _mapping(station.get("operational_claims"), "body_face_station.station_v12.operational_claims")
    for field, value in operational.items():
        _require(value is None or value is False, f"body_face_station.station_v12.operational_claims.{field}: must remain null/false")

    totals = _mapping(document.get("worksheet_totals"), "body_face_station.worksheet_totals")
    for field, expected in (
        ("intended_body_v5_blank_schema_classes", 9),
        ("facial_v4_blank_schema_classes", 16),
        ("station_v12_scope_count", 6),
        ("station_v12_stage_count_per_scope", 4),
        ("station_v12_blank_stage_slots", 24),
        ("station_v12_blank_state_field_count", 72),
        ("receipts_or_evidence_claimed", 0),
    ):
        _exact_int(totals.get(field), expected, f"body_face_station.worksheet_totals.{field}")
    _exact_false(totals.get("live_or_go_authority"), "body_face_station.worksheet_totals.live_or_go_authority")
    reject_authority_elevation(document, "body_face_station")


def validate_checksum_file(root: Path) -> dict[str, str]:
    text = _decode_utf8(_read_bytes(root, CHECKSUM_PATH), CHECKSUM_PATH)
    records: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        _require(bool(line), f"{CHECKSUM_PATH}:{line_number}: blank lines are not allowed")
        match = CHECKSUM_LINE.fullmatch(line)
        _require(match is not None, f"{CHECKSUM_PATH}:{line_number}: malformed checksum record")
        digest, basename = match.groups()
        _require(basename not in records, f"{CHECKSUM_PATH}:{line_number}: duplicate filename {basename!r}")
        records[basename] = digest

    expected_targets = {
        Path(relative).name: identity.sha256
        for relative, identity in EXPECTED_MANIFEST_ENTRIES.items()
        if relative != CHECKSUM_PATH
    }
    _require(records == expected_targets, f"{CHECKSUM_PATH}: record set or pinned digest mismatch")
    for basename, digest in records.items():
        relative = f"outputs/{basename}"
        actual = _identity(_read_bytes(root, relative)).sha256
        _require(actual == digest, f"{CHECKSUM_PATH}: {basename} does not match its recorded SHA-256")
    return records


def validate_work_manifest(root: Path, document: Mapping[str, Any], checksums: Mapping[str, str]) -> None:
    _require(
        document.get("schema") == "kira.work_continuation_and_publication_manifest.v1",
        "work_manifest.schema: unexpected schema",
    )
    _require(document.get("reporting_only") is True, "work_manifest.reporting_only: must be true")
    _require(document.get("append_only_successor") is True, "work_manifest.append_only_successor: must be true")
    _exact_false(
        document.get("historical_or_sealed_artifacts_modified"),
        "work_manifest.historical_or_sealed_artifacts_modified",
    )

    raw_entries = _list(document.get("mind_body_append_only_artifacts"), "work_manifest.mind_body_append_only_artifacts")
    _require(
        len(raw_entries) == len(EXPECTED_MANIFEST_ENTRIES),
        "work_manifest.mind_body_append_only_artifacts: identity count mismatch",
    )
    entries: dict[str, FileIdentity] = {}
    for index, raw_entry in enumerate(raw_entries):
        entry = _mapping(raw_entry, f"work_manifest.mind_body_append_only_artifacts[{index}]")
        _require(set(entry) == {"path", "bytes", "sha256"}, f"work_manifest.mind_body_append_only_artifacts[{index}]: field set mismatch")
        relative = entry.get("path")
        byte_count = entry.get("bytes")
        digest = entry.get("sha256")
        _require(type(relative) is str, f"work_manifest.mind_body_append_only_artifacts[{index}].path: expected string")
        _require(type(byte_count) is int, f"work_manifest.mind_body_append_only_artifacts[{index}].bytes: expected integer")
        _require(type(digest) is str, f"work_manifest.mind_body_append_only_artifacts[{index}].sha256: expected string")
        _require(relative not in entries, f"work_manifest.mind_body_append_only_artifacts: duplicate {relative!r}")
        entries[relative] = FileIdentity(byte_count, digest)

    _require(entries == EXPECTED_MANIFEST_ENTRIES, "work_manifest.mind_body_append_only_artifacts: pinned identities mismatch")
    for relative, expected in entries.items():
        _verify_identity(root, relative, expected)
        if relative != CHECKSUM_PATH:
            _require(
                checksums.get(Path(relative).name) == expected.sha256,
                f"work_manifest/checksum disagreement for {relative}",
            )

    audit = _mapping(
        _mapping(document.get("independent_local_audits"), "work_manifest.independent_local_audits").get("mind_body_append_only_outputs"),
        "work_manifest.independent_local_audits.mind_body_append_only_outputs",
    )
    for field, expected in (
        ("artifact_identities_matched", 4),
        ("mind_domain_mappings_exact", 53),
        ("mind_materialized_paths_pins_and_identities_nonnull", 0),
        ("intended_body_schema_classes_exact_and_blank", 9),
        ("facial_schema_classes_exact_and_blank", 16),
        ("station_scope_stage_slots_exact_and_blank", 24),
        ("station_state_fields_exact_and_blank", 72),
    ):
        _exact_int(audit.get(field), expected, f"work_manifest.independent_local_audits.mind_body_append_only_outputs.{field}")
    _exact_false(
        audit.get("live_runtime_blender_output_materialization_or_go_authority_found"),
        "work_manifest.independent_local_audits.mind_body_append_only_outputs.live_runtime_blender_output_materialization_or_go_authority_found",
    )
    reject_authority_elevation(document, "work_manifest")


def validate_matrix(root: Path) -> None:
    text = _decode_utf8(_read_bytes(root, MATRIX_PATH), MATRIX_PATH)
    terminal = "Current determination: **STATIC PREPARATION ONLY — NO LIVE, RUNTIME, BLENDER, OUTPUT, OR GO AUTHORITY.**"
    _require(text.rstrip().endswith(terminal), f"{MATRIX_PATH}: terminal no-GO determination is missing or changed")
    for relative in (BASELINE_PATH, MIND_PATH, BODY_PATH):
        _require(f"`{relative}`" in text, f"{MATRIX_PATH}: prepared reference missing: {relative}")


def validate(root: Path) -> dict[str, Any]:
    """Validate all pinned artifacts and return a deterministic summary."""

    root = root.resolve()
    baseline = strict_load_json(root, BASELINE_PATH)
    mind = strict_load_json(root, MIND_PATH)
    body_face_station = strict_load_json(root, BODY_PATH)
    work_manifest = strict_load_json(root, WORK_MANIFEST_PATH)

    validate_baseline(baseline)
    validate_mind(mind)
    validate_body_face_station(body_face_station)
    reject_authority_elevation(work_manifest, "work_manifest")
    validate_matrix(root)

    checksums = validate_checksum_file(root)
    validate_work_manifest(root, work_manifest, checksums)
    for relative, expected in EXPECTED_MANIFEST_ENTRIES.items():
        _verify_identity(root, relative, expected)
    _verify_identity(root, WORK_MANIFEST_PATH, EXPECTED_WORK_MANIFEST)

    return {
        "schema": "kira.validation.mind_body_append_only.read_only.v1",
        "verdict": "PASS_STATIC_NO_GO",
        "read_only": True,
        "files_verified": len(EXPECTED_MANIFEST_ENTRIES) + 1,
        "strict_json_files": 4,
        "checksum_entries_verified": len(checksums),
        "work_manifest_identities_verified": len(EXPECTED_MANIFEST_ENTRIES),
        "mind_domain_mappings": 53,
        "mind_null_materialization_triples": 53,
        "intended_body_blank_schema_classes": 9,
        "facial_blank_schema_classes": 16,
        "station_scopes": 6,
        "station_stages_per_scope": 4,
        "station_blank_stage_slots": 24,
        "station_blank_state_fields": 72,
        "live_runtime_blender_output_go_elevations": 0,
        "source_writes_performed": 0,
        "work_manifest": {
            "bytes": EXPECTED_WORK_MANIFEST.byte_count,
            "sha256": EXPECTED_WORK_MANIFEST.sha256,
        },
    }


def _default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="workspace root containing outputs/ (default: parent of tools/)",
    )
    args = parser.parse_args(argv)
    try:
        result = validate(args.root)
    except (OSError, ValidationError) as exc:
        print(json.dumps({"verdict": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
