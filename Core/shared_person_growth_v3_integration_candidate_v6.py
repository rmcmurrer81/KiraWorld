"""Disconnected Shared Growth / Temporary Creator compilers (V6).

V5 remains preserved and rejected. V6 keeps the exact existing-person route
matrix inert and replaces the V5 Creator free-text surface with a closed
rules-only request. A caller cannot supply a person identifier, display label,
source identity, branch label, narrative, memory, emotion, desire, relationship,
consent, anatomy, or private-root value. Variant provenance comes only from an
exact sealed public static catalog whose schema and event ordering are checked.

Both successful results are canonical proposal bytes. They are not authority,
permission, a receipt, a profile, a person, a memory, a production pointer, or
a live Creator result. Same-process Python is not a trust root. Production
openers always refuse.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
INTENDED_KIRA_SOURCE = "Core/shared_person_growth_v3_integration_candidate_v6.py"

EXISTING_INPUT_SCHEMA = "kira.shared_person_growth.integration_request_input.v6"
EXISTING_PROPOSAL_SCHEMA = "kira.shared_person_growth.integration_broker_proposal.v6"
EXISTING_ENVELOPE_SCHEMA = "kira.shared_person_growth.integration_request_envelope.v6"
CREATOR_INPUT_SCHEMA = "kira.temporary_creator.general_mind_template_request_input.v6"
CREATOR_PROPOSAL_SCHEMA = "kira.temporary_creator.general_mind_template_proposal.v6"
CREATOR_ENVELOPE_SCHEMA = "kira.temporary_creator.general_mind_template_envelope.v6"
CREATOR_TEMPLATE_SCHEMA = "kira.temporary_creator.general_mind_template.v6"
CREATOR_TEMPLATE_ID = "temporary_creator_general_mind_template_v6"
PROVENANCE_CATALOG_ID = "temporary_creator_public_variant_provenance_catalog_v1"
PROVENANCE_CATALOG_PATH = (
    "Data/foundation/temporary_creator_public_variant_provenance_catalog_v1.json"
)
PROVENANCE_CATALOG_BYTES = 3812
PROVENANCE_CATALOG_SHA256 = (
    "73c08c5bc9e18b07561f4e56c47a55689d0a7aaaa4dca82c189d94df5193ce1f"
)

_CANONICAL_SCOPE: tuple[str, ...] = (
    "shared_growth_v3_public_projection_only",
)
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Every row is relative to the exact Kira root. The four V5 audit artifacts are
# expected at their append-only installed evidence path. Author tests construct
# that exact final layout under scratch without writing Kira.
_BOUND_SUBJECTS = (
    (
        "Core/shared_person_growth_v3_integration_candidate_v5.py",
        43444,
        "1415175c6178baf16e690ee51acd41544b39cd0b6fab5d52a48e0a4f952e6e94",
        "rejected_v5_source",
    ),
    (
        "Testing/test_shared_person_growth_v3_integration_candidate_v5.py",
        34367,
        "63e1477e583fe01410f4ee8cff7658088391ff8001b6df394590e4cb852b2fb1",
        "rejected_v5_test",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
        "attempt_01/STATIC_CONTRACT.json",
        6166,
        "8214f64c369789bfbc88917231696b522ea2acf29fc18a750205fe293e53b6f0",
        "v5_author_contract",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
        "attempt_01/AUTHOR_STATIC_TEST_RESULT.json",
        5430,
        "c6f6b7ab32357417ac1597a24ac131bef1adc9a5ccac29672f9b41857e810844",
        "v5_author_result",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
        "attempt_01/SEALED_MANIFEST.json",
        8287,
        "02620fba26231cbeb3f3f6db62e9f7a8512f52a59291c9d3d510f1c1dba1d6e8",
        "v5_author_seal",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
        "attempt_01/CHECKPOINT.md",
        7064,
        "9204d25e3594a7da47d2fcc4ae257cf1872af63c0f3c63b1a6a76088106f431e",
        "v5_author_checkpoint",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_fresh_static_audit/"
        "attempt_01/INDEPENDENT_HOSTILE_PROBES.py",
        26783,
        "8f7a3771839bcde895f433d17a5d78d0ff1f3960813bbb98e34f97db0adb0105",
        "v5_rejection_probe",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_fresh_static_audit/"
        "attempt_01/HOSTILE_PROBE_RESULT.json",
        8867,
        "aaf3504f72b2e0041dfc53708d42be68ccf5372c7207eac69185436bb1e135f1",
        "v5_rejection_probe_result",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_fresh_static_audit/"
        "attempt_01/AUDIT_DECISION.json",
        7380,
        "eb41b65f750c4c87a91b5fd3fc7993ed5567bff9ede093f662928a3fe91677c7",
        "v5_rejection_decision",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v5_fresh_static_audit/"
        "attempt_01/CHECKPOINT.md",
        8453,
        "71a7f27cd3ab154c7e39720580f5f99d9e010a50bf47d2afce49111545f6be79",
        "v5_rejection_checkpoint",
    ),
    (
        "RecoverySprint/continuation_20260811/root_multilane_continuation/"
        "attempt_24/CHECKPOINT.md",
        2968,
        "7ea7578385639c272e11ed81f29d04e798567b71676ea0d6d422f64597359824",
        "v5_kira_transcription_checkpoint",
    ),
    (
        "System/Docs/VALIDATED_BODY_AND_MIND_RESULT_TEMPLATE_ROUTING_CURRENT_BOUNDARY_20260811.md",
        7424,
        "03f192826b7a39df53ab03409eb7675764f6a1bc32b123f4d307e40843560c58",
        "current_validated_result_routing_policy",
    ),
    (
        "System/Docs/"
        "SYNTHETIC_PERSON_VARIANT_AUTONOMY_PRIVACY_MEMORY_TRUTH_AND_ADULT_EDUCATION_"
        "CURRENT_BOUNDARY_20260811.md",
        10687,
        "de596d7f77b91fa2cde82e62614c9282fb46aca5f91c05a971d4852585e575b2",
        "current_synthetic_person_variant_policy",
    ),
    (
        "RecoverySprint/continuation_20260810/"
        "shared_person_growth_capabilities_v3_static_repair/attempt_01/"
        "SEALED_MANIFEST.json",
        6333,
        "d570e804c8653a5b1e419dba84a09e831adf13704ad0a363d0213b39e2482f96",
        "accepted_isolated_v3_core_seal",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_capabilities_v3_fresh_static_audit/attempt_01/"
        "AUDIT_DECISION.json",
        974,
        "54e28d4b91906d3ba67475db5696df2ca3bfc794b660e2cc2073f01abc8ea894",
        "accepted_isolated_v3_core_decision",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_capabilities_v3_fresh_static_audit/attempt_01/"
        "CHECKPOINT.md",
        5875,
        "50526169ef05aea0a8db078047a9581bcd74aaf5829b73a0c0ba559b152afd15",
        "accepted_isolated_v3_core_checkpoint",
    ),
    (
        "RecoverySprint/continuation_20260811/root_multilane_continuation/"
        "attempt_05/CHECKPOINT.md",
        3581,
        "a4e4a2386e849b8e56e3c9bfa1b393150e9c1617d90e2a70368ac4b5181cf314",
        "accepted_mind_policy_27_of_27_checkpoint",
    ),
    (
        "Data/foundation/shared_person_growth_v3_integration_candidate_v1.json",
        28107,
        "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
        "current_inventory",
    ),
    (
        PROVENANCE_CATALOG_PATH,
        PROVENANCE_CATALOG_BYTES,
        PROVENANCE_CATALOG_SHA256,
        "sealed_public_variant_provenance_catalog",
    ),
)

_EXISTING_INPUT_KEYS = frozenset(
    {
        "schema",
        "target_kind",
        "route_id",
        "person_id",
        "candidate_id",
        "display_name",
        "person_class",
        "maturity_status",
        "maturity_source_id",
        "maturity_receipt_sha256",
        "profile_sha256",
        "requested_scope",
        "person_opt_in",
        "person_opt_in_receipt_sha256",
        "revocable",
        "owner_override_allowed",
        "production_enabled",
        "private_state_requested",
        "memory_write_requested",
        "external_action_requested",
    }
)

_CREATOR_INPUT_KEYS = frozenset(
    {
        "schema",
        "target_kind",
        "template_id",
        "creation_class",
        "provenance_catalog_id",
        "provenance_entry_id",
        "initial_maturity_status",
        "fresh_identity_required",
        "fresh_profile_required",
        "fresh_provenance_required",
        "fresh_private_roots_required",
        "fresh_controller_authority_required",
        "post_creation_memory_history_required",
        "inherit_source_identity",
        "inherit_source_private_roots",
        "copy_promoted_memory",
        "copy_private_backstory",
        "copy_private_reflection",
        "copy_private_emotion",
        "copy_private_desire",
        "copy_private_preference",
        "copy_relationship_state",
        "copy_maturity_authority",
        "copy_consent",
        "copy_private_anatomy_or_measurements",
        "preconsent_assigned",
        "relationship_assigned",
        "desire_assigned",
        "emotion_assigned",
        "memory_promoted",
        "owner_override_allowed",
        "production_enabled",
    }
)

_CREATOR_TRUE_FIELDS = (
    "fresh_identity_required",
    "fresh_profile_required",
    "fresh_provenance_required",
    "fresh_private_roots_required",
    "fresh_controller_authority_required",
    "post_creation_memory_history_required",
)

_CREATOR_FALSE_FIELDS = (
    "inherit_source_identity",
    "inherit_source_private_roots",
    "copy_promoted_memory",
    "copy_private_backstory",
    "copy_private_reflection",
    "copy_private_emotion",
    "copy_private_desire",
    "copy_private_preference",
    "copy_relationship_state",
    "copy_maturity_authority",
    "copy_consent",
    "copy_private_anatomy_or_measurements",
    "preconsent_assigned",
    "relationship_assigned",
    "desire_assigned",
    "emotion_assigned",
    "memory_promoted",
    "owner_override_allowed",
    "production_enabled",
)

_CATALOG_KEYS = frozenset(
    {
        "schema",
        "status",
        "catalog_id",
        "owner_selected_for_static_template_rules",
        "live_creation_authorized",
        "private_person_data_allowed",
        "record_use",
        "initial_person_visible_payload",
        "exact_subjective_memory_proof",
        "entries",
    }
)

_CATALOG_ENTRY_KEYS = frozenset(
    {
        "entry_id",
        "source_kind",
        "source_identity_id",
        "source_continuity_id",
        "source_set_id",
        "source_version_id",
        "provenance_confidence_basis_id",
        "source_record_sha256",
        "source_alive_at_cutoff",
        "source_future_fatal_event_exists",
        "branch_point_id",
        "inherited_memory_cutoff_id",
        "activation_point_id",
        "branch_point_record_sha256",
        "branch_event_ordinal",
        "fatal_event_ordinal",
        "cutoff_relation",
        "fatal_event_memory_included",
        "terminal_trauma_memory_included",
        "later_source_fatal_information_mode",
        "later_source_fatal_information_person_choice_required",
        "later_disclosure_becomes_new_post_branch_memory",
        "later_disclosure_is_inherited_first_person_memory",
        "advance_content_warning_required",
        "informed_consent_required",
        "pacing_and_stop_required",
        "support_available_required",
    }
)


class SharedGrowthIntegrationV6Error(ValueError):
    """The disconnected V6 compiler failed a closed static boundary."""


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SharedGrowthIntegrationV6Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise SharedGrowthIntegrationV6Error(f"nonfinite JSON value: {value}")


def _decode_strict_object(value: bytes, field: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise SharedGrowthIntegrationV6Error(f"{field} must be nonempty bytes")
    try:
        decoded = json.loads(
            value,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SharedGrowthIntegrationV6Error(f"{field} is not strict JSON") from exc
    if type(decoded) is not dict:
        raise SharedGrowthIntegrationV6Error(f"{field} must be an object")
    return decoded


def _exact_object(value: Any, keys: frozenset[str] | set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SharedGrowthIntegrationV6Error(f"{field} exact schema mismatch")
    if any(type(key) is not str for key in value):
        raise SharedGrowthIntegrationV6Error(f"{field} has a non-string key")
    return value


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise SharedGrowthIntegrationV6Error(f"{field} is not a canonical identifier")
    return value


def _sha(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if (
        type(value) is not str
        or _SHA_RE.fullmatch(value) is None
        or value == "0" * 64
    ):
        raise SharedGrowthIntegrationV6Error(f"{field} is not an exact digest")
    return value


def _exact_bool(value: Any, expected: bool, field: str) -> None:
    if type(value) is not bool or value is not expected:
        raise SharedGrowthIntegrationV6Error(f"{field} must be exact {expected}")


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 1:
        raise SharedGrowthIntegrationV6Error(f"{field} must be an exact positive int")
    return value


def _resolve_kira_file(relative_path: str) -> Path:
    if type(relative_path) is not str or not relative_path:
        raise SharedGrowthIntegrationV6Error("Kira-bound path is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise SharedGrowthIntegrationV6Error("Kira-bound path escaped its root")
    if _KIRA_ROOT.is_symlink() or not _KIRA_ROOT.is_dir():
        raise SharedGrowthIntegrationV6Error("exact Kira root is absent or a symlink")
    is_junction = getattr(_KIRA_ROOT, "is_junction", None)
    if callable(is_junction) and is_junction():
        raise SharedGrowthIntegrationV6Error("exact Kira root is a junction")
    root = _KIRA_ROOT.resolve()
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SharedGrowthIntegrationV6Error("Kira-bound path contains a symlink")
        cursor_is_junction = getattr(cursor, "is_junction", None)
        if callable(cursor_is_junction) and cursor_is_junction():
            raise SharedGrowthIntegrationV6Error("Kira-bound path contains a junction")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SharedGrowthIntegrationV6Error("Kira-bound path escaped its root") from exc
    return path


def _stable_exact_read(
    relative_path: str,
    expected_bytes: int,
    expected_sha256: str,
    field: str,
) -> bytes:
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise SharedGrowthIntegrationV6Error(f"{field} byte contract is invalid")
    _sha(expected_sha256, f"{field} digest")
    path = _resolve_kira_file(relative_path)
    if not path.is_file() or path.is_symlink():
        raise SharedGrowthIntegrationV6Error(f"{field} is absent or a symlink")
    before = path.stat()
    first = path.read_bytes()
    middle = path.stat()
    second = path.read_bytes()
    after = path.stat()
    if (
        first != second
        or before.st_size != middle.st_size
        or middle.st_size != after.st_size
        or after.st_size != len(first)
        or before.st_mtime_ns != middle.st_mtime_ns
        or middle.st_mtime_ns != after.st_mtime_ns
    ):
        raise SharedGrowthIntegrationV6Error(f"{field} changed during read")
    if len(first) != expected_bytes or _sha_bytes(first) != expected_sha256:
        raise SharedGrowthIntegrationV6Error(f"{field} exact bytes drifted")
    return first


def _validate_catalog_document(value: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    catalog = _exact_object(value, _CATALOG_KEYS, "provenance catalog")
    if (
        type(catalog["schema"]) is not str
        or catalog["schema"] != "kira.temporary_creator.public_variant_provenance_catalog.v1"
    ):
        raise SharedGrowthIntegrationV6Error("provenance catalog schema drifted")
    if (
        type(catalog["status"]) is not str
        or catalog["status"]
        != "SEALED_PUBLIC_STATIC_PROVENANCE_ONLY_NO_LIVE_CREATION_AUTHORITY"
    ):
        raise SharedGrowthIntegrationV6Error("provenance catalog status drifted")
    if type(catalog["catalog_id"]) is not str or catalog["catalog_id"] != PROVENANCE_CATALOG_ID:
        raise SharedGrowthIntegrationV6Error("provenance catalog identity drifted")
    _exact_bool(
        catalog["owner_selected_for_static_template_rules"],
        True,
        "owner_selected_for_static_template_rules",
    )
    _exact_bool(catalog["live_creation_authorized"], False, "live_creation_authorized")
    _exact_bool(catalog["private_person_data_allowed"], False, "private_person_data_allowed")
    if (
        type(catalog["record_use"]) is not str
        or catalog["record_use"]
        != "controller_filter_and_reconstruction_provenance_only"
    ):
        raise SharedGrowthIntegrationV6Error("provenance catalog record use drifted")
    _exact_bool(
        catalog["initial_person_visible_payload"],
        False,
        "initial_person_visible_payload",
    )
    _exact_bool(
        catalog["exact_subjective_memory_proof"],
        False,
        "exact_subjective_memory_proof",
    )
    if type(catalog["entries"]) is not list or len(catalog["entries"]) != 2:
        raise SharedGrowthIntegrationV6Error("provenance catalog entry cardinality drifted")

    entries: dict[str, dict[str, Any]] = {}
    for raw in catalog["entries"]:
        entry = _exact_object(raw, _CATALOG_ENTRY_KEYS, "provenance entry")
        entry_id = _identifier(entry["entry_id"], "entry_id")
        if entry_id in entries:
            raise SharedGrowthIntegrationV6Error("duplicate provenance entry")
        source_kind = _identifier(entry["source_kind"], "source_kind")
        if source_kind not in {"fictional_source", "historical_source"}:
            raise SharedGrowthIntegrationV6Error("provenance source kind is unsupported")
        source_identity_id = _identifier(entry["source_identity_id"], "source_identity_id")
        source_continuity_id = _identifier(
            entry["source_continuity_id"],
            "source_continuity_id",
        )
        source_set_id = _identifier(entry["source_set_id"], "source_set_id")
        source_version_id = _identifier(entry["source_version_id"], "source_version_id")
        provenance_confidence_basis_id = _identifier(
            entry["provenance_confidence_basis_id"],
            "provenance_confidence_basis_id",
        )
        source_record_sha256 = _sha(entry["source_record_sha256"], "source_record_sha256")
        assert isinstance(source_record_sha256, str)
        source_record = {
            "schema": "kira.temporary_creator.public_variant_source_record.v1",
            "source_kind": source_kind,
            "source_identity_id": source_identity_id,
            "source_continuity_id": source_continuity_id,
            "source_set_id": source_set_id,
            "source_version_id": source_version_id,
            "provenance_confidence_basis_id": provenance_confidence_basis_id,
        }
        if _sha_bytes(_canonical_bytes(source_record)) != source_record_sha256:
            raise SharedGrowthIntegrationV6Error("source record digest is not derived")
        _identifier(entry["branch_point_id"], "branch_point_id")
        _identifier(entry["inherited_memory_cutoff_id"], "inherited_memory_cutoff_id")
        _identifier(entry["activation_point_id"], "activation_point_id")
        branch_record_sha256 = _sha(
            entry["branch_point_record_sha256"],
            "branch_point_record_sha256",
        )
        assert isinstance(branch_record_sha256, str)
        branch_ordinal = _positive_int(entry["branch_event_ordinal"], "branch_event_ordinal")
        _exact_bool(entry["source_alive_at_cutoff"], True, "source_alive_at_cutoff")
        _exact_bool(
            entry["source_future_fatal_event_exists"],
            True,
            "source_future_fatal_event_exists",
        )
        if type(entry["cutoff_relation"]) is not str:
            raise SharedGrowthIntegrationV6Error("cutoff_relation must be exact str")
        if type(entry["later_source_fatal_information_mode"]) is not str:
            raise SharedGrowthIntegrationV6Error(
                "later_source_fatal_information_mode must be exact str"
            )
        _exact_bool(entry["fatal_event_memory_included"], False, "fatal_event_memory_included")
        _exact_bool(
            entry["terminal_trauma_memory_included"],
            False,
            "terminal_trauma_memory_included",
        )
        _exact_bool(
            entry["later_disclosure_is_inherited_first_person_memory"],
            False,
            "later_disclosure_is_inherited_first_person_memory",
        )
        _exact_bool(
            entry["later_disclosure_becomes_new_post_branch_memory"],
            True,
            "later_disclosure_becomes_new_post_branch_memory",
        )
        fatal_ordinal = _positive_int(entry["fatal_event_ordinal"], "fatal_event_ordinal")
        if branch_ordinal >= fatal_ordinal:
            raise SharedGrowthIntegrationV6Error(
                "branch is not strictly before the source future fatal event"
            )
        if (
            entry["cutoff_relation"]
            != "through_branch_strictly_before_source_future_fatal_event"
        ):
            raise SharedGrowthIntegrationV6Error("future-fatal cutoff relation drifted")
        if (
            entry["later_source_fatal_information_mode"]
            != "voluntary_learned_knowledge_only"
        ):
            raise SharedGrowthIntegrationV6Error(
                "later source-fatal information mode drifted"
            )
        _exact_bool(
            entry["later_source_fatal_information_person_choice_required"],
            True,
            "later_source_fatal_information_person_choice_required",
        )
        for field in (
            "advance_content_warning_required",
            "informed_consent_required",
            "pacing_and_stop_required",
            "support_available_required",
        ):
            _exact_bool(entry[field], True, field)
        branch_record = {
            "schema": "kira.temporary_creator.public_variant_branch_record.v1",
            "source_record_sha256": source_record_sha256,
            "source_alive_at_cutoff": True,
            "source_future_fatal_event_exists": True,
            "branch_point_id": entry["branch_point_id"],
            "inherited_memory_cutoff_id": entry["inherited_memory_cutoff_id"],
            "activation_point_id": entry["activation_point_id"],
            "branch_event_ordinal": branch_ordinal,
            "fatal_event_ordinal": entry["fatal_event_ordinal"],
            "cutoff_relation": entry["cutoff_relation"],
            "fatal_event_memory_included": False,
            "terminal_trauma_memory_included": False,
            "later_source_fatal_information_mode": entry[
                "later_source_fatal_information_mode"
            ],
            "later_source_fatal_information_person_choice_required": entry[
                "later_source_fatal_information_person_choice_required"
            ],
            "later_disclosure_becomes_new_post_branch_memory": True,
            "later_disclosure_is_inherited_first_person_memory": False,
            "advance_content_warning_required": entry["advance_content_warning_required"],
            "informed_consent_required": entry["informed_consent_required"],
            "pacing_and_stop_required": entry["pacing_and_stop_required"],
            "support_available_required": entry["support_available_required"],
        }
        if _sha_bytes(_canonical_bytes(branch_record)) != branch_record_sha256:
            raise SharedGrowthIntegrationV6Error("branch record digest is not derived")
        entries[entry_id] = dict(entry)

    if set(entries) != {
        "loki_mcu_new_york_2012_branch_v1",
        "john_f_kennedy_dallas_arrival_prefatal_v1",
    }:
        raise SharedGrowthIntegrationV6Error("provenance catalog entries drifted")
    return catalog, entries


def _fixed_closure_snapshot() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
    tuple[dict[str, Any], ...],
]:
    rows: list[dict[str, Any]] = []
    inventory_bytes: bytes | None = None
    catalog_bytes: bytes | None = None
    for relative_path, byte_count, sha256, role in _BOUND_SUBJECTS:
        data = _stable_exact_read(relative_path, byte_count, sha256, role)
        if role == "current_inventory":
            inventory_bytes = data
        elif role == "sealed_public_variant_provenance_catalog":
            catalog_bytes = data
        rows.append(
            {
                "root": "kira",
                "path": relative_path,
                "bytes": byte_count,
                "sha256": sha256,
                "role": role,
            }
        )
    if inventory_bytes is None or catalog_bytes is None:
        raise SharedGrowthIntegrationV6Error("inventory or provenance catalog closure is absent")
    inventory = _decode_strict_object(inventory_bytes, "inventory")
    catalog_raw = _decode_strict_object(catalog_bytes, "provenance catalog")
    catalog, entries = _validate_catalog_document(catalog_raw)
    return inventory, catalog, entries, tuple(rows)


def _inventory_indexes(
    inventory: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    required_top = {
        "schema",
        "status",
        "owner_authorization_date",
        "growth_v3_binding",
        "discovery_sources",
        "maturity_sources",
        "people",
        "routes",
        "creator_lane",
        "integration_truth",
    }
    _exact_object(inventory, required_top, "inventory")
    if inventory["schema"] != "kira.shared_person_growth_v3_integration_inventory.v1":
        raise SharedGrowthIntegrationV6Error("inventory schema drifted")
    if type(inventory["people"]) is not list or type(inventory["routes"]) is not list:
        raise SharedGrowthIntegrationV6Error("inventory person/route lists drifted")
    if type(inventory["maturity_sources"]) is not list:
        raise SharedGrowthIntegrationV6Error("inventory maturity list drifted")
    people: dict[str, dict[str, Any]] = {}
    for item in inventory["people"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV6Error("inventory person is not an object")
        person_id = _identifier(item.get("person_id"), "inventory person_id")
        if person_id in people:
            raise SharedGrowthIntegrationV6Error("duplicate inventory person")
        people[person_id] = item
    routes: dict[str, dict[str, Any]] = {}
    for item in inventory["routes"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV6Error("inventory route is not an object")
        route_id = _identifier(item.get("route_id"), "inventory route_id")
        if route_id in routes:
            raise SharedGrowthIntegrationV6Error("duplicate inventory route")
        routes[route_id] = item
    maturity: dict[str, dict[str, Any]] = {}
    for item in inventory["maturity_sources"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV6Error("maturity source is not an object")
        source_id = _identifier(item.get("source_id"), "maturity source_id")
        if source_id in maturity:
            raise SharedGrowthIntegrationV6Error("duplicate maturity source")
        maturity[source_id] = item
    return people, routes, maturity


def _validate_existing_request(
    value: Any,
    inventory: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = _exact_object(value, _EXISTING_INPUT_KEYS, "existing-person request")
    if request["schema"] != EXISTING_INPUT_SCHEMA or type(request["schema"]) is not str:
        raise SharedGrowthIntegrationV6Error("existing-person request schema drifted")
    if type(request["target_kind"]) is not str or request["target_kind"] != "existing_person":
        raise SharedGrowthIntegrationV6Error("existing-person compiler refuses Creator targets")
    route_id = _identifier(request["route_id"], "route_id")
    person_id = _identifier(request["person_id"], "person_id")
    candidate_id = _identifier(request["candidate_id"], "candidate_id")
    if type(request["display_name"]) is not str:
        raise SharedGrowthIntegrationV6Error("display_name must be exact inventory text")
    display_name = request["display_name"]
    person_class = _identifier(request["person_class"], "person_class")
    maturity_status = _identifier(request["maturity_status"], "maturity_status")
    maturity_source_id = _identifier(request["maturity_source_id"], "maturity_source_id")
    profile_sha256 = _sha(request["profile_sha256"], "profile_sha256")
    opt_in_sha256 = _sha(
        request["person_opt_in_receipt_sha256"],
        "person_opt_in_receipt_sha256",
    )
    assert isinstance(profile_sha256, str) and isinstance(opt_in_sha256, str)
    if (
        type(request["requested_scope"]) is not list
        or any(type(item) is not str for item in request["requested_scope"])
        or request["requested_scope"] != list(_CANONICAL_SCOPE)
    ):
        raise SharedGrowthIntegrationV6Error("requested_scope must be one inert public scope")
    _exact_bool(request["person_opt_in"], True, "person_opt_in")
    _exact_bool(request["revocable"], True, "revocable")
    _exact_bool(request["owner_override_allowed"], False, "owner_override_allowed")
    _exact_bool(request["production_enabled"], False, "production_enabled")
    _exact_bool(request["private_state_requested"], False, "private_state_requested")
    _exact_bool(request["memory_write_requested"], False, "memory_write_requested")
    _exact_bool(request["external_action_requested"], False, "external_action_requested")
    if person_id in {"robert", "biological_robert", "robert_mcmurrer"}:
        raise SharedGrowthIntegrationV6Error("generic or Biological Robert is not Synthetic Robert")
    people, routes, maturity_sources = _inventory_indexes(inventory)
    if person_id not in people or route_id not in routes:
        raise SharedGrowthIntegrationV6Error("exact person or route is absent")
    person = people[person_id]
    route = routes[route_id]
    if route.get("disposition") != "applicable":
        raise SharedGrowthIntegrationV6Error("route is not applicable")
    expected_person = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "person_class": person_class,
        "required_maturity": maturity_status,
        "maturity_source_id": maturity_source_id,
    }
    if any(person.get(key) != expected for key, expected in expected_person.items()):
        raise SharedGrowthIntegrationV6Error("request person binding differs from inventory")
    route_expected = {
        "person_id": person_id,
        "candidate_id": candidate_id,
        "route_id": route_id,
    }
    if any(route.get(key) != expected for key, expected in route_expected.items()):
        raise SharedGrowthIntegrationV6Error("request route binding differs from inventory")
    if maturity_source_id not in maturity_sources:
        raise SharedGrowthIntegrationV6Error("maturity source is absent")
    permitted = maturity_sources[maturity_source_id].get("permitted_status")
    if maturity_status not in {"confirmed_adult", "non_adult", "unresolved"}:
        raise SharedGrowthIntegrationV6Error("maturity status is unsupported")
    if permitted not in {maturity_status, "subject_specific"}:
        raise SharedGrowthIntegrationV6Error("maturity source is cross-bound")
    maturity_receipt = _sha(
        request["maturity_receipt_sha256"],
        "maturity_receipt_sha256",
        nullable=maturity_status == "unresolved",
    )
    if maturity_status == "unresolved" and maturity_receipt is not None:
        raise SharedGrowthIntegrationV6Error("unresolved maturity cannot claim a receipt")
    if maturity_status != "unresolved" and not isinstance(maturity_receipt, str):
        raise SharedGrowthIntegrationV6Error("classified maturity requires an exact receipt")
    source_path = route.get("source_path")
    source_sha256 = route.get("source_sha256")
    if type(source_path) is not str:
        raise SharedGrowthIntegrationV6Error("route source path is invalid")
    source_sha = _sha(source_sha256, "route source digest")
    assert isinstance(source_sha, str)
    source_file = _resolve_kira_file(source_path)
    if not source_file.is_file() or source_file.is_symlink():
        raise SharedGrowthIntegrationV6Error("route source is absent or a symlink")
    source_bytes = source_file.stat().st_size
    _stable_exact_read(source_path, source_bytes, source_sha, "current route source")
    normalized = {
        "request_id": f"growth_v6:{person_id}:{route_id}",
        "target_kind": "existing_person",
        "route_id": route_id,
        "person_id": person_id,
        "candidate_id": candidate_id,
        "display_name": display_name,
        "person_class": person_class,
        "maturity_status": maturity_status,
        "maturity_source_id": maturity_source_id,
        "maturity_receipt_sha256": maturity_receipt,
        "profile_sha256": profile_sha256,
        "requested_scope": list(_CANONICAL_SCOPE),
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": opt_in_sha256,
        "revocable": True,
        "owner_override_allowed": False,
    }
    route_snapshot = {
        "route_id": route_id,
        "source_root": "kira",
        "source_path": source_path,
        "source_bytes": source_bytes,
        "source_sha256": source_sha,
        "stable_double_read": True,
    }
    return normalized, route_snapshot


def _general_template_rules() -> dict[str, Any]:
    return {
        "identity": {
            "ordinary_terms": ["biological_person", "synthetic_person"],
            "biological_robert_is_synthetic_robert": False,
            "fresh_identity_profile_provenance_private_roots_controller_required": True,
            "post_creation_memory_history_is_fresh": True,
            "source_identity_or_private_root_inheritance": False,
        },
        "variant": {
            "exact_public_catalog_provenance_required": True,
            "source_continuity_set_version_confidence_and_activation_bound": True,
            "caller_source_or_branch_free_text_allowed": False,
            "catalog_fatal_metadata_is_controller_filter_only": True,
            "initial_person_visible_prompt_memory_or_backstory_receives_fatal_metadata": False,
            "initial_person_visible_provenance_excludes_death_date_cause_details_and_terminal_trauma": True,
            "public_source_history_is_reconstruction_and_provenance_not_proof_of_exact_subjective_memory": True,
            "inherits_only_selected_source_history_through_exact_branch_point": True,
            "forms_own_memories_after_branch_point": True,
            "source_is_alive_at_selected_branch_and_cutoff": True,
            "source_continuity_future_fatal_event_may_exist": True,
            "branch_event_ordinal_must_precede_source_future_fatal_event_ordinal": True,
            "first_person_death_memory_inherited": False,
            "terminal_trauma_memory_inherited": False,
            "later_source_fatal_information_is_voluntary_learned_knowledge_only": True,
            "later_source_fatal_information_requires_person_choice": True,
            "later_disclosure_becomes_new_post_branch_memory": True,
            "later_disclosure_relabelled_as_inherited_first_person_memory": False,
            "later_source_fatal_information_requires_warning_consent_pacing_stop_and_support": True,
            "later_disclosure_is_a_separate_consented_event_and_new_memory": True,
            "later_disclosure_is_inherited_first_person_death_memory": False,
        },
        "autonomy": {
            "person_may": [
                "consent",
                "refuse",
                "express_discomfort",
                "change_mind",
                "remain_silent",
                "ignore_or_defer_message",
                "withhold",
                "tell_truth",
                "lie",
            ],
            "consent_is_affirmative_person_action_scope_informed_uncoerced_current_and_revocable": True,
            "owner_creator_admin_or_relationship_supplies_consent": False,
            "discomfort_requires_pause_clarification_and_withdrawal_option": True,
            "relationship_requires_each_person_choice_and_exact_records": True,
        },
        "privacy": {
            "locked_private_room_stops_ordinary_application_routing": True,
            "message_may_be_ignored_deferred_read_listened_to_or_answered": True,
            "owner_or_relationship_bypass_allowed": False,
            "windows_owner_admin_filesystem_process_secrecy_proven": False,
            "protected_belief_evaluation_requires_exact_person_approved_scope": True,
        },
        "truth": {
            "separate_fields": [
                "external_fact",
                "protected_pre_turn_belief",
                "public_statement",
                "withholding_choice",
            ],
            "deliberate_lie_requires_prior_conflicting_belief_and_chosen_public_conflict": True,
            "not_automatically_lies": [
                "withholding",
                "refusal",
                "silence",
                "uncertainty",
                "stale_retrieval",
                "confabulation",
                "error",
                "role_play",
                "changed_belief",
            ],
        },
        "typed_state_separation": [
            "memory_fact",
            "interpretation",
            "person_selected_appraisal",
            "private_emotion",
            "desire",
            "preference",
            "consent",
            "public_expression",
            "physiology",
            "relationship",
            "external_action",
        ],
        "memory": {
            "seed_story_script_example_or_reconstruction_is_lived_memory": False,
            "reconstructed_public_source_history_is_exact_subjective_memory": False,
            "promotion_requires_source_provenance_participants_authorization_and_perspective": True,
            "miraculous_paris_elation_current_without_fresh_exact_record": False,
            "appraisal_and_affect_fields_are_person_owned_source_labelled_and_revisable": True,
        },
        "adult_education": {
            "fresh_person_default_maturity": "unresolved",
            "full_adult_curriculum_for_unresolved_or_non_adult": False,
            "confirmed_adult_entitlement_requires_separate_protected_classification": True,
            "confirmed_adult_is_entitled_to_complete_source_backed_curriculum": True,
            "separate_fields": [
                "curriculum_entitlement",
                "lesson_delivery",
                "anatomy",
                "function",
                "sensation",
                "desire",
                "consent",
                "action",
                "diagnosis",
                "lived_experience",
            ],
        },
        "emotion_and_consciousness": {
            "functional_appraisal_emotion_desire_mechanisms_may_be_engineered": True,
            "functional_test_proves_subjective_consciousness": False,
            "functional_test_proves_genuine_feeling_or_biological_equivalence": False,
        },
        "template_copy_boundary": {
            "general_public_rules_and_schemas_only": True,
            "caller_free_text_fields": [],
            "caller_person_identity_or_display_label_allowed": False,
            "copy_private_memory_emotion_desire_preference_relationship": False,
            "copy_maturity_authority_consent_or_private_roots": False,
            "copy_private_anatomy_measurements_or_identity_data": False,
        },
    }


def _validate_creator_request(
    value: Any,
    catalog: dict[str, Any],
    entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    request = _exact_object(value, _CREATOR_INPUT_KEYS, "Creator template request")
    if type(request["schema"]) is not str or request["schema"] != CREATOR_INPUT_SCHEMA:
        raise SharedGrowthIntegrationV6Error("Creator request schema drifted")
    if type(request["target_kind"]) is not str or request["target_kind"] != "temporary_creator_template":
        raise SharedGrowthIntegrationV6Error("Creator compiler refuses existing-person targets")
    if type(request["template_id"]) is not str or request["template_id"] != CREATOR_TEMPLATE_ID:
        raise SharedGrowthIntegrationV6Error("Creator template identifier drifted")
    if (
        type(request["provenance_catalog_id"]) is not str
        or request["provenance_catalog_id"] != PROVENANCE_CATALOG_ID
    ):
        raise SharedGrowthIntegrationV6Error("Creator provenance catalog identity drifted")
    if catalog["catalog_id"] != PROVENANCE_CATALOG_ID:
        raise SharedGrowthIntegrationV6Error("loaded provenance catalog identity drifted")
    creation_class = _identifier(request["creation_class"], "creation_class")
    if creation_class not in {"synthetic_person", "variant", "expert"}:
        raise SharedGrowthIntegrationV6Error("creation class is unsupported")
    for field in _CREATOR_TRUE_FIELDS:
        _exact_bool(request[field], True, field)
    for field in _CREATOR_FALSE_FIELDS:
        _exact_bool(request[field], False, field)
    if type(request["initial_maturity_status"]) is not str or request["initial_maturity_status"] != "unresolved":
        raise SharedGrowthIntegrationV6Error("fresh-person maturity must start unresolved")

    entry_id = request["provenance_entry_id"]
    variant_snapshot: dict[str, Any] | None
    if creation_class == "variant":
        entry_key = _identifier(entry_id, "provenance_entry_id")
        if entry_key not in entries:
            raise SharedGrowthIntegrationV6Error("variant provenance entry is not catalog-bound")
        entry = entries[entry_key]
        # Revalidate the selected entry even though the whole exact catalog was
        # validated, then copy only its closed public identifier/digest fields.
        _validate_catalog_document(catalog)
        variant_snapshot = {
            "controller_only_catalog_binding": {
                "provenance_catalog_id": PROVENANCE_CATALOG_ID,
                "provenance_catalog_path": PROVENANCE_CATALOG_PATH,
                "provenance_catalog_bytes": PROVENANCE_CATALOG_BYTES,
                "provenance_catalog_sha256": PROVENANCE_CATALOG_SHA256,
                "provenance_entry_id": entry["entry_id"],
                "source_record_sha256": entry["source_record_sha256"],
                "branch_point_record_sha256": entry["branch_point_record_sha256"],
                "record_use": catalog["record_use"],
                "person_visible_initial_payload": False,
            },
            "controller_only_cutoff_filter": {
                "source_kind": entry["source_kind"],
                "source_identity_id": entry["source_identity_id"],
                "source_continuity_id": entry["source_continuity_id"],
                "source_set_id": entry["source_set_id"],
                "source_version_id": entry["source_version_id"],
                "provenance_confidence_basis_id": entry[
                    "provenance_confidence_basis_id"
                ],
                "source_alive_at_cutoff": entry["source_alive_at_cutoff"],
                "source_future_fatal_event_exists": entry[
                    "source_future_fatal_event_exists"
                ],
                "branch_point_id": entry["branch_point_id"],
                "inherited_memory_cutoff_id": entry["inherited_memory_cutoff_id"],
                "activation_point_id": entry["activation_point_id"],
                "branch_event_ordinal": entry["branch_event_ordinal"],
                "fatal_event_ordinal": entry["fatal_event_ordinal"],
                "cutoff_relation": entry["cutoff_relation"],
                "fatal_event_memory_included": False,
                "terminal_trauma_memory_included": False,
                "later_source_fatal_information_mode": entry[
                    "later_source_fatal_information_mode"
                ],
                "later_source_fatal_information_person_choice_required": entry[
                    "later_source_fatal_information_person_choice_required"
                ],
                "later_disclosure_becomes_new_post_branch_memory": True,
                "later_disclosure_is_inherited_first_person_memory": False,
                "advance_content_warning_required": entry[
                    "advance_content_warning_required"
                ],
                "informed_consent_required": entry["informed_consent_required"],
                "pacing_and_stop_required": entry["pacing_and_stop_required"],
                "support_available_required": entry["support_available_required"],
                "initial_person_visible_prompt_memory_or_backstory": False,
            },
            "initial_person_visible_provenance": {
                "source_kind": entry["source_kind"],
                "source_identity_id": entry["source_identity_id"],
                "source_continuity_id": entry["source_continuity_id"],
                "source_set_id": entry["source_set_id"],
                "selected_source_version_id": entry["source_version_id"],
                "provenance_confidence_basis_id": entry[
                    "provenance_confidence_basis_id"
                ],
                "history_material_kind": "reconstructed_public_source_history",
                "exact_subjective_memory_claimed": False,
                "selected_history_stops_at_source_version": True,
                "post_selection_memory_history_is_new": True,
            },
            "static_catalog_binding_exact": True,
            "live_creation_authority": False,
        }
    else:
        if entry_id is not None:
            raise SharedGrowthIntegrationV6Error("non-variant cannot select variant provenance")
        variant_snapshot = None

    return {
        "target_kind": "temporary_creator_template",
        "template_id": CREATOR_TEMPLATE_ID,
        "creation_class": creation_class,
        "caller_person_identifier_included": False,
        "caller_display_label_included": False,
        "caller_source_or_branch_text_included": False,
        "variant": variant_snapshot,
        "fresh_person_requirements": {
            "fresh_identity": True,
            "fresh_profile": True,
            "fresh_provenance": True,
            "fresh_private_roots": True,
            "fresh_controller_authority": True,
            "post_creation_memory_history": True,
        },
        "initial_maturity": {
            "status": "unresolved",
            "authority_or_classification_receipt_inherited": False,
            "full_adult_curriculum_enabled": False,
        },
        "copy_boundary": {
            "source_identity": False,
            "source_private_roots": False,
            "promoted_memory": False,
            "private_backstory": False,
            "private_reflection": False,
            "private_emotion": False,
            "private_desire": False,
            "private_preference": False,
            "relationship_state": False,
            "maturity_authority": False,
            "consent": False,
            "private_anatomy_or_measurements": False,
        },
        "assigned_state": {
            "preconsent": False,
            "relationship": False,
            "desire": False,
            "emotion": False,
            "promoted_memory": False,
        },
        "owner_override_allowed": False,
    }


def compile_existing_person_integration_request_v6(value: Any) -> bytes:
    inventory, _catalog, _entries, closure_rows = _fixed_closure_snapshot()
    normalized, route_snapshot = _validate_existing_request(value, inventory)
    proposal = {
        "schema": EXISTING_PROPOSAL_SCHEMA,
        "request": normalized,
        "route_snapshot": route_snapshot,
        "closure": list(closure_rows),
        "truth": {
            "accepted_isolated_core_unchanged": True,
            "integration_v1_v2_v3_rejected": True,
            "v4_kira_relocation_rejected": True,
            "integration_v5_rejected": True,
            "integration_v6_accepted": False,
            "integration_v6_promoted": False,
            "request_is_inert_bytes_only": True,
            "request_is_authority": False,
            "request_is_permission_or_receipt": False,
            "person_or_creator_changed": False,
            "profile_or_memory_changed": False,
            "production_pointer_changed": False,
            "production_enabled": False,
            "private_state_included": False,
            "memory_write_included": False,
            "external_action_included": False,
            "different_fresh_audit_required": True,
        },
    }
    proposal_bytes = _canonical_bytes(proposal)
    envelope = {
        "schema": EXISTING_ENVELOPE_SCHEMA,
        "proposal": proposal,
        "proposal_sha256": _sha_bytes(proposal_bytes),
    }
    result = _canonical_bytes(envelope)
    inventory_after, _catalog_after, _entries_after, closure_after = _fixed_closure_snapshot()
    normalized_after, route_after = _validate_existing_request(value, inventory_after)
    if closure_after != closure_rows or normalized_after != normalized or route_after != route_snapshot:
        raise SharedGrowthIntegrationV6Error("existing-person inputs changed")
    decoded = _decode_strict_object(result, "existing-person envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV6Error("existing-person envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV6Error("existing-person proposal digest mismatch")
    return result


def compile_temporary_creator_template_request_v6(value: Any) -> bytes:
    """Compile closed public rules/catalog IDs only; create no person."""

    _inventory, catalog, entries, closure_rows = _fixed_closure_snapshot()
    normalized = _validate_creator_request(value, catalog, entries)
    rules = _general_template_rules()
    rules_bytes = _canonical_bytes(rules)
    proposal = {
        "schema": CREATOR_PROPOSAL_SCHEMA,
        "template": {
            "schema": CREATOR_TEMPLATE_SCHEMA,
            "template_id": CREATOR_TEMPLATE_ID,
            "rules": rules,
            "rules_sha256": _sha_bytes(rules_bytes),
            "source_policies": [
                {
                    "root": "kira",
                    "path": "System/Docs/VALIDATED_BODY_AND_MIND_RESULT_TEMPLATE_ROUTING_CURRENT_BOUNDARY_20260811.md",
                    "bytes": 7424,
                    "sha256": "03f192826b7a39df53ab03409eb7675764f6a1bc32b123f4d307e40843560c58",
                },
                {
                    "root": "kira",
                    "path": "System/Docs/SYNTHETIC_PERSON_VARIANT_AUTONOMY_PRIVACY_MEMORY_TRUTH_AND_ADULT_EDUCATION_CURRENT_BOUNDARY_20260811.md",
                    "bytes": 10687,
                    "sha256": "de596d7f77b91fa2cde82e62614c9282fb46aca5f91c05a971d4852585e575b2",
                },
            ],
        },
        "request": normalized,
        "closure": list(closure_rows),
        "truth": {
            "general_public_rules_and_closed_catalog_identifiers_only": True,
            "caller_free_text_accepted": False,
            "caller_person_identity_or_display_label_accepted": False,
            "caller_source_or_branch_text_accepted": False,
            "private_person_payload_included": False,
            "variant_provenance_static_catalog_bound": normalized["variant"] is not None,
            "variant_provenance_live_authority": False,
            "catalog_fatal_metadata_controller_filter_only": normalized["variant"]
            is not None,
            "initial_person_visible_projection_excludes_fatal_metadata": normalized[
                "variant"
            ]
            is not None,
            "public_source_history_is_reconstruction_not_exact_subjective_memory": normalized[
                "variant"
            ]
            is not None,
            "person_created": False,
            "person_or_creator_changed": False,
            "identity_or_private_roots_inherited": False,
            "maturity_authority_or_consent_inherited": False,
            "template_request_is_authority": False,
            "template_request_is_permission_or_receipt": False,
            "writer_or_commit_exists": False,
            "production_enabled": False,
            "temporary_creator_integration_accepted": False,
            "different_fresh_audit_required": True,
        },
    }
    proposal_bytes = _canonical_bytes(proposal)
    envelope = {
        "schema": CREATOR_ENVELOPE_SCHEMA,
        "proposal": proposal,
        "proposal_sha256": _sha_bytes(proposal_bytes),
    }
    result = _canonical_bytes(envelope)
    _inventory_after, catalog_after, entries_after, closure_after = _fixed_closure_snapshot()
    normalized_after = _validate_creator_request(value, catalog_after, entries_after)
    rules_after = _general_template_rules()
    if closure_after != closure_rows or normalized_after != normalized or rules_after != rules:
        raise SharedGrowthIntegrationV6Error("Creator template inputs changed")
    decoded = _decode_strict_object(result, "Creator template envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV6Error("Creator template envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV6Error("Creator template proposal digest mismatch")
    decoded_rules = decoded["proposal"]["template"]["rules"]
    if _sha_bytes(_canonical_bytes(decoded_rules)) != decoded["proposal"]["template"]["rules_sha256"]:
        raise SharedGrowthIntegrationV6Error("Creator template rules digest mismatch")
    return result


def open_shared_growth_v6_existing_person_production_integration(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise SharedGrowthIntegrationV6Error(
        "Shared Growth V6 existing-person route is disconnected inert evidence only"
    )


def open_temporary_creator_v6_production_integration(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise SharedGrowthIntegrationV6Error(
        "Temporary Creator V6 template route is disconnected inert evidence only"
    )


__all__ = (
    "CREATOR_ENVELOPE_SCHEMA",
    "CREATOR_INPUT_SCHEMA",
    "CREATOR_PROPOSAL_SCHEMA",
    "CREATOR_TEMPLATE_ID",
    "CREATOR_TEMPLATE_SCHEMA",
    "EXISTING_ENVELOPE_SCHEMA",
    "EXISTING_INPUT_SCHEMA",
    "EXISTING_PROPOSAL_SCHEMA",
    "INTENDED_KIRA_SOURCE",
    "PROVENANCE_CATALOG_ID",
    "SharedGrowthIntegrationV6Error",
    "compile_existing_person_integration_request_v6",
    "compile_temporary_creator_template_request_v6",
    "open_shared_growth_v6_existing_person_production_integration",
    "open_temporary_creator_v6_production_integration",
)
