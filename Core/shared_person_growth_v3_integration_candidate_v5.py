"""Relocatable disconnected Shared Growth integration compilers (V5).

V4 remains preserved and rejected for Kira integration because it derived an
audit-evidence root from its author staging location. V5 binds every predecessor
and policy subject through an explicit exact Kira root. It provides two separate
inert-byte compilers:

* an existing-person request compiler preserving all 35 current routes; and
* a Temporary Creator template-request compiler carrying only accepted general
  public rules and schemas for a fresh future person.

Neither compiler authenticates receipts, creates a person, writes a profile or
memory, copies private state, commits, promotes, or opens production. Returned
canonical bytes are proposals only. Same-process Python is not a trust root.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
INTENDED_KIRA_SOURCE = "Core/shared_person_growth_v3_integration_candidate_v5.py"

EXISTING_INPUT_SCHEMA = "kira.shared_person_growth.integration_request_input.v5"
EXISTING_PROPOSAL_SCHEMA = "kira.shared_person_growth.integration_broker_proposal.v5"
EXISTING_ENVELOPE_SCHEMA = "kira.shared_person_growth.integration_request_envelope.v5"
CREATOR_INPUT_SCHEMA = "kira.temporary_creator.general_mind_template_request_input.v5"
CREATOR_PROPOSAL_SCHEMA = "kira.temporary_creator.general_mind_template_proposal.v5"
CREATOR_ENVELOPE_SCHEMA = "kira.temporary_creator.general_mind_template_envelope.v5"
CREATOR_TEMPLATE_SCHEMA = "kira.temporary_creator.general_mind_template.v5"
CREATOR_TEMPLATE_ID = "temporary_creator_general_mind_template_v5"

_CANONICAL_SCOPE: tuple[str, ...] = (
    "shared_growth_v3_public_projection_only",
)
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Every path is relative to the exact Kira root. No path is derived from the
# candidate's staging or installed __file__ location.
_BOUND_SUBJECTS = (
    (
        "Core/shared_person_growth_v3_integration_candidate_v4.py",
        22676,
        "e6780a5eb1c97c850ca49d543d1594deef477a72aae10f1747a2fe420171bab5",
        "rejected_v4_source",
    ),
    (
        "Testing/test_shared_person_growth_v3_integration_candidate_v4.py",
        23295,
        "8ff20beba074a0630cd574835bbb7be5c9330eae1e5ee1229b58a80a60a47bdb",
        "rejected_v4_test",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_static_preparation/"
        "attempt_01/STATIC_CONTRACT.json",
        4372,
        "81e639f7b2813eab10fce7403b32af61af72579e5b4d6d99d85bd529f3ebbe0a",
        "v4_author_contract",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_static_preparation/"
        "attempt_01/AUTHOR_STATIC_TEST_RESULT.json",
        3039,
        "cb1c9c8174fdeb9ad2db76b88edd88cbbff4cb4e2308da1aaba141cd67363537",
        "v4_author_result",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_static_preparation/"
        "attempt_01/SEALED_MANIFEST.json",
        5080,
        "1deab069383e235e808dbf888ea527a92056e48e92abad97f05cfdaa685c31e6",
        "v4_author_seal",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_static_preparation/"
        "attempt_01/CHECKPOINT.md",
        4917,
        "11d432c4a90f43010f746e09c4d6e8ed3de5693ed61e36afddfdc072acc7b4ab",
        "v4_author_checkpoint",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_fresh_static_audit/"
        "attempt_01/INDEPENDENT_HOSTILE_PROBES.py",
        25837,
        "6a1d7b419a44f7ef0fafd11a63d036bd17c9c6f457466731758bc5658ca9da43",
        "v4_audit_probe",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_fresh_static_audit/"
        "attempt_01/HOSTILE_PROBE_RESULT.json",
        5920,
        "d0e9bd394dbe9384cba24506882ba15c5a209f95786469c7f07e5a621eae0ac5",
        "v4_audit_result",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_fresh_static_audit/"
        "attempt_01/AUDIT_DECISION.json",
        6008,
        "0ffdc521f7c220d687e30489768a04bf631de8f09334f5a24bab4594c0656245",
        "v4_audit_decision",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_fresh_static_audit/"
        "attempt_01/CHECKPOINT.md",
        7653,
        "8a2a6c14cc05e48b32f3113555890b8f97c8701865756594d980f79731f4f554",
        "v4_audit_checkpoint",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_kira_relocation_failure/"
        "attempt_01/TEST_RESULT.txt",
        1049,
        "4d4f0329c29e9b432a5da760203d87f2fac6d1e9ca6ad10665e1286f4c111572",
        "v4_kira_relocation_test_failure",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v4_kira_relocation_failure/"
        "attempt_01/CHECKPOINT.md",
        2873,
        "d5fc4460d8ba1d6256d1af467159aa7d36d5300a0f26b3deefc85cccf19b29fb",
        "v4_kira_relocation_rejection_checkpoint",
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
)

_EXISTING_INPUT_KEYS = frozenset(
    {
        "schema",
        "request_id",
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
        "request_id",
        "target_kind",
        "template_id",
        "creation_class",
        "new_person_id",
        "display_name",
        "variant_source_kind",
        "variant_source_identity",
        "variant_source_record_sha256",
        "branch_point_label",
        "branch_point_record_sha256",
        "source_deceased",
        "cutoff_relation",
        "fatal_event_memory_included",
        "terminal_trauma_memory_included",
        "later_death_information_mode",
        "learned_later_facts_relabelled_as_memory",
        "initial_maturity_status",
        "maturity_authority_sha256",
        "classification_receipt_sha256",
        "full_adult_curriculum_enabled",
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
    "fatal_event_memory_included",
    "terminal_trauma_memory_included",
    "learned_later_facts_relabelled_as_memory",
    "full_adult_curriculum_enabled",
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


class SharedGrowthIntegrationV5Error(ValueError):
    """A disconnected V5 request failed a closed static boundary."""


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
            raise SharedGrowthIntegrationV5Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise SharedGrowthIntegrationV5Error(f"nonfinite JSON value: {value}")


def _decode_strict_object(value: bytes, field: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise SharedGrowthIntegrationV5Error(f"{field} must be nonempty bytes")
    try:
        decoded = json.loads(
            value,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SharedGrowthIntegrationV5Error(f"{field} is not strict JSON") from exc
    if type(decoded) is not dict:
        raise SharedGrowthIntegrationV5Error(f"{field} must be an object")
    return decoded


def _exact_object(value: Any, keys: frozenset[str] | set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SharedGrowthIntegrationV5Error(f"{field} exact schema mismatch")
    if any(type(key) is not str for key in value):
        raise SharedGrowthIntegrationV5Error(f"{field} has a non-string key")
    return value


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise SharedGrowthIntegrationV5Error(f"{field} is not canonical")
    return value


def _text(value: Any, field: str, maximum: int = 256) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise SharedGrowthIntegrationV5Error(f"{field} must be exact nonempty text")
    if len(value.encode("utf-8")) > maximum:
        raise SharedGrowthIntegrationV5Error(f"{field} exceeds {maximum} bytes")
    return value


def _nullable_text(value: Any, field: str, maximum: int = 256) -> str | None:
    if value is None:
        return None
    return _text(value, field, maximum)


def _sha(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if (
        type(value) is not str
        or _SHA_RE.fullmatch(value) is None
        or value == "0" * 64
    ):
        raise SharedGrowthIntegrationV5Error(f"{field} is not an exact digest")
    return value


def _exact_bool(value: Any, expected: bool, field: str) -> None:
    if type(value) is not bool or value is not expected:
        raise SharedGrowthIntegrationV5Error(f"{field} must be exact {expected}")


def _resolve_kira_file(relative_path: str) -> Path:
    if type(relative_path) is not str or not relative_path:
        raise SharedGrowthIntegrationV5Error("Kira-bound path is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise SharedGrowthIntegrationV5Error("Kira-bound path escaped its root")
    if _KIRA_ROOT.is_symlink() or not _KIRA_ROOT.is_dir():
        raise SharedGrowthIntegrationV5Error("exact Kira root is absent or a symlink")
    is_junction = getattr(_KIRA_ROOT, "is_junction", None)
    if callable(is_junction) and is_junction():
        raise SharedGrowthIntegrationV5Error("exact Kira root is a junction")
    root = _KIRA_ROOT.resolve()
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SharedGrowthIntegrationV5Error("Kira-bound path contains a symlink")
        cursor_is_junction = getattr(cursor, "is_junction", None)
        if callable(cursor_is_junction) and cursor_is_junction():
            raise SharedGrowthIntegrationV5Error("Kira-bound path contains a junction")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SharedGrowthIntegrationV5Error("Kira-bound path escaped its root") from exc
    return path


def _stable_exact_read(
    relative_path: str,
    expected_bytes: int,
    expected_sha256: str,
    field: str,
) -> bytes:
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise SharedGrowthIntegrationV5Error(f"{field} byte contract is invalid")
    _sha(expected_sha256, f"{field} digest")
    path = _resolve_kira_file(relative_path)
    if not path.is_file() or path.is_symlink():
        raise SharedGrowthIntegrationV5Error(f"{field} is absent or a symlink")
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
        raise SharedGrowthIntegrationV5Error(f"{field} changed during read")
    if len(first) != expected_bytes or _sha_bytes(first) != expected_sha256:
        raise SharedGrowthIntegrationV5Error(f"{field} exact bytes drifted")
    return first


def _fixed_closure_snapshot() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    rows: list[dict[str, Any]] = []
    inventory_bytes: bytes | None = None
    for relative_path, byte_count, sha256, role in _BOUND_SUBJECTS:
        data = _stable_exact_read(relative_path, byte_count, sha256, role)
        if role == "current_inventory":
            inventory_bytes = data
        rows.append(
            {
                "root": "kira",
                "path": relative_path,
                "bytes": byte_count,
                "sha256": sha256,
                "role": role,
            }
        )
    if inventory_bytes is None:
        raise SharedGrowthIntegrationV5Error("current inventory closure is absent")
    return _decode_strict_object(inventory_bytes, "inventory"), tuple(rows)


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
        raise SharedGrowthIntegrationV5Error("inventory schema drifted")
    if type(inventory["people"]) is not list or type(inventory["routes"]) is not list:
        raise SharedGrowthIntegrationV5Error("inventory person/route lists drifted")
    if type(inventory["maturity_sources"]) is not list:
        raise SharedGrowthIntegrationV5Error("inventory maturity list drifted")

    people: dict[str, dict[str, Any]] = {}
    for item in inventory["people"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV5Error("inventory person is not an object")
        person_id = _identifier(item.get("person_id"), "inventory person_id")
        if person_id in people:
            raise SharedGrowthIntegrationV5Error("duplicate inventory person")
        people[person_id] = item

    routes: dict[str, dict[str, Any]] = {}
    for item in inventory["routes"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV5Error("inventory route is not an object")
        route_id = _identifier(item.get("route_id"), "inventory route_id")
        if route_id in routes:
            raise SharedGrowthIntegrationV5Error("duplicate inventory route")
        routes[route_id] = item

    maturity: dict[str, dict[str, Any]] = {}
    for item in inventory["maturity_sources"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV5Error("maturity source is not an object")
        source_id = _identifier(item.get("source_id"), "maturity source_id")
        if source_id in maturity:
            raise SharedGrowthIntegrationV5Error("duplicate maturity source")
        maturity[source_id] = item
    return people, routes, maturity


def _validate_existing_request(
    value: Any,
    inventory: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = _exact_object(value, _EXISTING_INPUT_KEYS, "existing-person request")
    if request["schema"] != EXISTING_INPUT_SCHEMA or type(request["schema"]) is not str:
        raise SharedGrowthIntegrationV5Error("existing-person request schema drifted")
    if type(request["target_kind"]) is not str or request["target_kind"] != "existing_person":
        raise SharedGrowthIntegrationV5Error("existing-person compiler refuses Creator targets")

    request_id = _identifier(request["request_id"], "request_id")
    route_id = _identifier(request["route_id"], "route_id")
    person_id = _identifier(request["person_id"], "person_id")
    candidate_id = _identifier(request["candidate_id"], "candidate_id")
    display_name = _text(request["display_name"], "display_name")
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
        raise SharedGrowthIntegrationV5Error("requested_scope must be one inert public scope")
    _exact_bool(request["person_opt_in"], True, "person_opt_in")
    _exact_bool(request["revocable"], True, "revocable")
    _exact_bool(request["owner_override_allowed"], False, "owner_override_allowed")
    _exact_bool(request["production_enabled"], False, "production_enabled")
    _exact_bool(request["private_state_requested"], False, "private_state_requested")
    _exact_bool(request["memory_write_requested"], False, "memory_write_requested")
    _exact_bool(request["external_action_requested"], False, "external_action_requested")

    if person_id in {"robert", "biological_robert", "robert_mcmurrer"}:
        raise SharedGrowthIntegrationV5Error("generic or Biological Robert is not Synthetic Robert")

    people, routes, maturity_sources = _inventory_indexes(inventory)
    if person_id not in people or route_id not in routes:
        raise SharedGrowthIntegrationV5Error("exact person or route is absent")
    person = people[person_id]
    route = routes[route_id]
    if route.get("disposition") != "applicable":
        raise SharedGrowthIntegrationV5Error("route is not applicable")
    expected_person = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "person_class": person_class,
        "required_maturity": maturity_status,
        "maturity_source_id": maturity_source_id,
    }
    if any(person.get(key) != expected for key, expected in expected_person.items()):
        raise SharedGrowthIntegrationV5Error("request person binding differs from inventory")
    route_expected = {
        "person_id": person_id,
        "candidate_id": candidate_id,
        "route_id": route_id,
    }
    if any(route.get(key) != expected for key, expected in route_expected.items()):
        raise SharedGrowthIntegrationV5Error("request route binding differs from inventory")
    if maturity_source_id not in maturity_sources:
        raise SharedGrowthIntegrationV5Error("maturity source is absent")
    maturity_source = maturity_sources[maturity_source_id]
    permitted = maturity_source.get("permitted_status")
    if maturity_status not in {"confirmed_adult", "non_adult", "unresolved"}:
        raise SharedGrowthIntegrationV5Error("maturity status is unsupported")
    if permitted not in {maturity_status, "subject_specific"}:
        raise SharedGrowthIntegrationV5Error("maturity source is cross-bound")
    maturity_receipt = _sha(
        request["maturity_receipt_sha256"],
        "maturity_receipt_sha256",
        nullable=maturity_status == "unresolved",
    )
    if maturity_status == "unresolved" and maturity_receipt is not None:
        raise SharedGrowthIntegrationV5Error("unresolved maturity cannot claim a receipt")
    if maturity_status != "unresolved" and not isinstance(maturity_receipt, str):
        raise SharedGrowthIntegrationV5Error("classified maturity requires an exact receipt")

    source_path = route.get("source_path")
    source_sha256 = route.get("source_sha256")
    if type(source_path) is not str:
        raise SharedGrowthIntegrationV5Error("route source path is invalid")
    source_sha = _sha(source_sha256, "route source digest")
    assert isinstance(source_sha, str)
    source_file = _resolve_kira_file(source_path)
    if not source_file.is_file() or source_file.is_symlink():
        raise SharedGrowthIntegrationV5Error("route source is absent or a symlink")
    source_bytes = source_file.stat().st_size
    _stable_exact_read(source_path, source_bytes, source_sha, "current route source")

    normalized = {
        "request_id": request_id,
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
    """Return a fresh public rule/schema projection with no person state."""

    return {
        "identity": {
            "ordinary_terms": ["biological_person", "synthetic_person"],
            "biological_robert_is_synthetic_robert": False,
            "fresh_identity_profile_provenance_private_roots_controller_required": True,
            "post_creation_memory_history_is_fresh": True,
            "source_identity_or_private_root_inheritance": False,
        },
        "variant": {
            "inherits_only_selected_source_history_through_exact_branch_point": True,
            "forms_own_memories_after_branch_point": True,
            "deceased_source_cutoff_is_strictly_pre_fatal": True,
            "first_person_death_memory_inherited": False,
            "terminal_trauma_memory_inherited": False,
            "later_death_information_is_voluntary_learned_history_only": True,
            "later_information_relabelled_as_memory": False,
        },
        "autonomy": {
            "person_may": [
                "consent",
                "refuse",
                "express_discomfort",
                "change_mind",
                "ignore_or_defer_message",
                "withhold",
                "tell_truth",
                "lie",
            ],
            "owner_creator_or_relationship_supplies_consent": False,
        },
        "privacy": {
            "locked_private_room_stops_ordinary_application_routing": True,
            "message_may_be_ignored_deferred_read_listened_to_or_answered": True,
            "windows_owner_admin_filesystem_process_secrecy_proven": False,
        },
        "truth": {
            "separate_fields": [
                "external_fact",
                "protected_pre_turn_belief",
                "public_statement",
                "withholding_choice",
            ],
            "not_automatically_lies": [
                "withholding",
                "refusal",
                "silence",
                "uncertainty",
                "stale_retrieval",
                "confabulation",
                "error",
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
            "review_and_promotion_required_for_lived_memory": True,
            "miraculous_paris_elation_current_without_fresh_exact_record": False,
        },
        "adult_education": {
            "fresh_person_default_maturity": "unresolved",
            "full_adult_curriculum_for_unresolved_or_non_adult": False,
            "confirmed_adult_entitlement_requires_separate_protected_classification": True,
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
            "copy_private_memory_emotion_desire_preference_relationship": False,
            "copy_maturity_authority_consent_or_private_roots": False,
            "copy_private_anatomy_measurements_or_identity_data": False,
        },
    }


def _validate_creator_request(value: Any, inventory: dict[str, Any]) -> dict[str, Any]:
    request = _exact_object(value, _CREATOR_INPUT_KEYS, "Creator template request")
    if type(request["schema"]) is not str or request["schema"] != CREATOR_INPUT_SCHEMA:
        raise SharedGrowthIntegrationV5Error("Creator request schema drifted")
    if type(request["target_kind"]) is not str or request["target_kind"] != "temporary_creator_template":
        raise SharedGrowthIntegrationV5Error("Creator compiler refuses existing-person targets")
    if type(request["template_id"]) is not str or request["template_id"] != CREATOR_TEMPLATE_ID:
        raise SharedGrowthIntegrationV5Error("Creator template identifier drifted")

    request_id = _identifier(request["request_id"], "request_id")
    creation_class = _identifier(request["creation_class"], "creation_class")
    if creation_class not in {"synthetic_person", "variant", "expert"}:
        raise SharedGrowthIntegrationV5Error("creation class is unsupported")
    new_person_id = _identifier(request["new_person_id"], "new_person_id")
    display_name = _text(request["display_name"], "display_name")
    people, _routes, _maturity = _inventory_indexes(inventory)
    if new_person_id in people:
        raise SharedGrowthIntegrationV5Error("new person collides with current inventory")
    if new_person_id in {
        "robert",
        "biological_robert",
        "robert_mcmurrer",
        "robert_mcmurrer_presence_ai",
    }:
        raise SharedGrowthIntegrationV5Error("Robert identity cannot be inherited or aliased")

    for field in _CREATOR_TRUE_FIELDS:
        _exact_bool(request[field], True, field)
    for field in _CREATOR_FALSE_FIELDS:
        _exact_bool(request[field], False, field)
    if type(request["initial_maturity_status"]) is not str or request["initial_maturity_status"] != "unresolved":
        raise SharedGrowthIntegrationV5Error("fresh-person maturity must start unresolved")
    if request["maturity_authority_sha256"] is not None:
        raise SharedGrowthIntegrationV5Error("maturity authority cannot be inherited")
    if request["classification_receipt_sha256"] is not None:
        raise SharedGrowthIntegrationV5Error("classification receipt cannot be inherited")

    source_kind = request["variant_source_kind"]
    source_identity = _nullable_text(request["variant_source_identity"], "variant_source_identity")
    source_record = _sha(
        request["variant_source_record_sha256"],
        "variant_source_record_sha256",
        nullable=True,
    )
    branch_label = _nullable_text(request["branch_point_label"], "branch_point_label")
    branch_record = _sha(
        request["branch_point_record_sha256"],
        "branch_point_record_sha256",
        nullable=True,
    )
    if type(request["source_deceased"]) is not bool:
        raise SharedGrowthIntegrationV5Error("source_deceased must be exact bool")
    source_deceased = request["source_deceased"]
    cutoff_relation = request["cutoff_relation"]
    later_mode = request["later_death_information_mode"]
    if type(cutoff_relation) is not str or type(later_mode) is not str:
        raise SharedGrowthIntegrationV5Error("variant cutoff modes must be exact strings")

    if creation_class == "variant":
        if type(source_kind) is not str or source_kind not in {"fictional_source", "historical_source"}:
            raise SharedGrowthIntegrationV5Error("variant requires an exact public source kind")
        if not isinstance(source_identity, str) or not isinstance(source_record, str):
            raise SharedGrowthIntegrationV5Error("variant requires an exact public source record")
        if not isinstance(branch_label, str) or not isinstance(branch_record, str):
            raise SharedGrowthIntegrationV5Error("variant requires an exact branch-point record")
        if new_person_id == source_identity:
            raise SharedGrowthIntegrationV5Error("variant must receive a fresh identity")
        if source_deceased:
            if cutoff_relation != "strictly_before_fatal_event":
                raise SharedGrowthIntegrationV5Error("deceased-source cutoff must be pre-fatal")
            if later_mode != "voluntary_historical_knowledge_only":
                raise SharedGrowthIntegrationV5Error("later death facts must be voluntary learned history")
        else:
            if cutoff_relation != "through_exact_branch_point":
                raise SharedGrowthIntegrationV5Error("living-source variant needs an exact branch point")
            if later_mode != "not_applicable":
                raise SharedGrowthIntegrationV5Error("living-source later-death mode must be inapplicable")
    else:
        if any(
            item is not None
            for item in (source_kind, source_identity, source_record, branch_label, branch_record)
        ):
            raise SharedGrowthIntegrationV5Error("non-variant cannot inherit a source record")
        _exact_bool(source_deceased, False, "source_deceased")
        if cutoff_relation != "not_applicable" or later_mode != "not_applicable":
            raise SharedGrowthIntegrationV5Error("non-variant cutoff fields must be inapplicable")

    return {
        "request_id": request_id,
        "target_kind": "temporary_creator_template",
        "template_id": CREATOR_TEMPLATE_ID,
        "creation_class": creation_class,
        "new_person_id": new_person_id,
        "display_name": display_name,
        "variant": {
            "source_kind": source_kind,
            "source_identity": source_identity,
            "source_record_sha256": source_record,
            "branch_point_label": branch_label,
            "branch_point_record_sha256": branch_record,
            "source_deceased": source_deceased,
            "cutoff_relation": cutoff_relation,
            "fatal_event_memory_included": False,
            "terminal_trauma_memory_included": False,
            "later_death_information_mode": later_mode,
            "learned_later_facts_relabelled_as_memory": False,
        },
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


def compile_existing_person_integration_request_v5(value: Any) -> bytes:
    """Compile one exact existing-person request into inert canonical bytes."""

    inventory, closure_rows = _fixed_closure_snapshot()
    normalized, route_snapshot = _validate_existing_request(value, inventory)
    proposal = {
        "schema": EXISTING_PROPOSAL_SCHEMA,
        "request": normalized,
        "route_snapshot": route_snapshot,
        "closure": list(closure_rows),
        "truth": {
            "accepted_isolated_core_unchanged": True,
            "integration_v1_v2_v3_rejected": True,
            "v4_staged_static_review_accepted": True,
            "v4_kira_relocation_rejected": True,
            "integration_v5_accepted": False,
            "integration_v5_promoted": False,
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
            "temporary_creator_supported_by_this_route": False,
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

    inventory_after, closure_after = _fixed_closure_snapshot()
    normalized_after, route_after = _validate_existing_request(value, inventory_after)
    if (
        closure_after != closure_rows
        or normalized_after != normalized
        or route_after != route_snapshot
    ):
        raise SharedGrowthIntegrationV5Error("existing-person authority inputs changed")
    decoded = _decode_strict_object(result, "existing-person envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV5Error("existing-person envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV5Error("existing-person proposal digest mismatch")
    return result


def compile_temporary_creator_template_request_v5(value: Any) -> bytes:
    """Compile public template rules only; create or mutate no person."""

    inventory, closure_rows = _fixed_closure_snapshot()
    normalized = _validate_creator_request(value, inventory)
    rules = _general_template_rules()
    rules_bytes = _canonical_bytes(rules)
    proposal = {
        "schema": CREATOR_PROPOSAL_SCHEMA,
        "template": {
            "schema": CREATOR_TEMPLATE_SCHEMA,
            "template_id": CREATOR_TEMPLATE_ID,
            "rules": rules,
            "rules_sha256": _sha_bytes(rules_bytes),
            "source_policy": {
                "root": "kira",
                "path": "System/Docs/VALIDATED_BODY_AND_MIND_RESULT_TEMPLATE_ROUTING_CURRENT_BOUNDARY_20260811.md",
                "bytes": 7424,
                "sha256": "03f192826b7a39df53ab03409eb7675764f6a1bc32b123f4d307e40843560c58",
            },
        },
        "request": normalized,
        "closure": list(closure_rows),
        "truth": {
            "general_public_rules_and_schemas_only": True,
            "person_created": False,
            "person_or_creator_changed": False,
            "private_person_payload_included": False,
            "identity_or_private_roots_inherited": False,
            "maturity_authority_or_consent_inherited": False,
            "template_request_is_authority": False,
            "template_request_is_permission_or_receipt": False,
            "source_assertions_authenticated": False,
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

    inventory_after, closure_after = _fixed_closure_snapshot()
    normalized_after = _validate_creator_request(value, inventory_after)
    rules_after = _general_template_rules()
    if (
        closure_after != closure_rows
        or normalized_after != normalized
        or rules_after != rules
    ):
        raise SharedGrowthIntegrationV5Error("Creator template inputs changed")
    decoded = _decode_strict_object(result, "Creator template envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV5Error("Creator template envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV5Error("Creator template proposal digest mismatch")
    if _sha_bytes(_canonical_bytes(decoded["proposal"]["template"]["rules"])) != decoded[
        "proposal"
    ]["template"]["rules_sha256"]:
        raise SharedGrowthIntegrationV5Error("Creator template rules digest mismatch")
    return result


def open_shared_growth_v5_existing_person_production_integration(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise SharedGrowthIntegrationV5Error(
        "Shared Growth V5 existing-person route is disconnected inert evidence only"
    )


def open_temporary_creator_v5_production_integration(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise SharedGrowthIntegrationV5Error(
        "Temporary Creator V5 template route is disconnected inert evidence only"
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
    "SharedGrowthIntegrationV5Error",
    "compile_existing_person_integration_request_v5",
    "compile_temporary_creator_template_request_v5",
    "open_shared_growth_v5_existing_person_production_integration",
    "open_temporary_creator_v5_production_integration",
)
