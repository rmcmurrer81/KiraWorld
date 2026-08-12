"""Disconnected Shared Growth V3 integration-request compiler (V3).

The accepted isolated Shared Growth V3 core remains static-only.  Integration
V1 and V2 remain rejected.  This append-only successor deliberately removes
every verifier, callback, controller, staging, commit, rollback, cleanup, and
person-state capability from the Python surface.  It can only compile an exact
existing-person request into inert canonical JSON bytes for a future,
separately protected broker that does not yet exist.

The returned bytes are not permission, a receipt, a profile, a promotion, or
person state.  Same-process Python substitution can fabricate inert bytes; no
current route is allowed to consume them.  The production opener therefore
always refuses.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_SCHEMA = "kira.shared_person_growth.integration_request_input.v3"
PROPOSAL_SCHEMA = "kira.shared_person_growth.integration_broker_proposal.v3"
ENVELOPE_SCHEMA = "kira.shared_person_growth.integration_request_envelope.v3"
REQUESTED_SCOPE = ["shared_growth_v3_public_projection_only"]

_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

_FIXED_SUBJECTS = (
    (
        "RecoverySprint/continuation_20260810/"
        "shared_person_growth_capabilities_v3_static_repair/attempt_01/"
        "SEALED_MANIFEST.json",
        6333,
        "d570e804c8653a5b1e419dba84a09e831adf13704ad0a363d0213b39e2482f96",
        "accepted_isolated_v3_seal",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_capabilities_v3_fresh_static_audit/attempt_01/"
        "CHECKPOINT.md",
        5875,
        "50526169ef05aea0a8db078047a9581bcd74aaf5829b73a0c0ba559b152afd15",
        "accepted_isolated_v3_audit_checkpoint",
    ),
    (
        "Data/foundation/shared_person_growth_v3_integration_candidate_v1.json",
        28107,
        "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
        "current_inventory",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v2_static_preparation/"
        "attempt_02/SEALED_MANIFEST.json",
        4146,
        "0ec609dc63b6d440f35c9ec3969b15972c5032bd71c7b89e0595f57b54df6820",
        "rejected_v2_seal",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/"
        "attempt_01/AUDIT_DECISION.json",
        3560,
        "68bb3190eadbde381f04621f0fcd834c18d5286ce43d329c3c2c7a7132c817db",
        "rejected_v2_decision",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/"
        "attempt_01/HOSTILE_PROBES.md",
        3255,
        "20549b40f565c64dc577339cb4401cd360b5a4ee7122031789b697fa937725c4",
        "rejected_v2_findings",
    ),
    (
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/"
        "attempt_01/CHECKPOINT.md",
        1657,
        "4bd30dea911e0ae2f7892a68138a41ab049319ef2c14cd8c83796b03ec4541b2",
        "rejected_v2_checkpoint",
    ),
)

_INPUT_KEYS = {
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


class SharedGrowthIntegrationV3Error(ValueError):
    """The disconnected request compiler failed closed."""


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
            raise SharedGrowthIntegrationV3Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise SharedGrowthIntegrationV3Error(f"nonfinite JSON value: {value}")


def _decode_strict_object(value: bytes, field: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise SharedGrowthIntegrationV3Error(f"{field} must be nonempty bytes")
    try:
        decoded = json.loads(
            value,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SharedGrowthIntegrationV3Error(f"{field} is not strict JSON") from exc
    if type(decoded) is not dict:
        raise SharedGrowthIntegrationV3Error(f"{field} must be an object")
    return decoded


def _exact_object(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SharedGrowthIntegrationV3Error(f"{field} exact schema mismatch")
    if any(type(key) is not str for key in value):
        raise SharedGrowthIntegrationV3Error(f"{field} has a non-string key")
    return value


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise SharedGrowthIntegrationV3Error(f"{field} is not canonical")
    return value


def _text(value: Any, field: str, maximum: int = 256) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise SharedGrowthIntegrationV3Error(f"{field} must be exact nonempty text")
    if len(value.encode("utf-8")) > maximum:
        raise SharedGrowthIntegrationV3Error(f"{field} exceeds {maximum} bytes")
    return value


def _sha(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if (
        type(value) is not str
        or _SHA_RE.fullmatch(value) is None
        or value == "0" * 64
    ):
        raise SharedGrowthIntegrationV3Error(f"{field} is not an exact digest")
    return value


def _exact_bool(value: Any, expected: bool, field: str) -> None:
    if type(value) is not bool or value is not expected:
        raise SharedGrowthIntegrationV3Error(f"{field} must be exact {expected}")


def _resolve_project_file(relative_path: str) -> Path:
    if type(relative_path) is not str or not relative_path:
        raise SharedGrowthIntegrationV3Error("bound path is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise SharedGrowthIntegrationV3Error("bound path escaped the project")
    root = PROJECT_ROOT.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SharedGrowthIntegrationV3Error("bound path escaped the project") from exc
    return path


def _stable_exact_read(
    relative_path: str,
    expected_bytes: int,
    expected_sha256: str,
    field: str,
) -> bytes:
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise SharedGrowthIntegrationV3Error(f"{field} byte contract is invalid")
    _sha(expected_sha256, f"{field} digest")
    path = _resolve_project_file(relative_path)
    if not path.is_file() or path.is_symlink():
        raise SharedGrowthIntegrationV3Error(f"{field} is absent or a symlink")
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
        raise SharedGrowthIntegrationV3Error(f"{field} changed during read")
    if len(first) != expected_bytes or _sha_bytes(first) != expected_sha256:
        raise SharedGrowthIntegrationV3Error(f"{field} exact bytes drifted")
    return first


def _fixed_closure_snapshot() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    rows: list[dict[str, Any]] = []
    inventory_bytes: bytes | None = None
    for relative_path, byte_count, sha256, role in _FIXED_SUBJECTS:
        content = _stable_exact_read(relative_path, byte_count, sha256, role)
        if role == "current_inventory":
            inventory_bytes = content
        rows.append(
            {
                "path": relative_path,
                "bytes": byte_count,
                "sha256": sha256,
                "role": role,
            }
        )
    if inventory_bytes is None:
        raise SharedGrowthIntegrationV3Error("inventory closure is incomplete")
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
        raise SharedGrowthIntegrationV3Error("inventory schema drifted")
    if type(inventory["people"]) is not list or type(inventory["routes"]) is not list:
        raise SharedGrowthIntegrationV3Error("inventory person/route lists drifted")
    if type(inventory["maturity_sources"]) is not list:
        raise SharedGrowthIntegrationV3Error("inventory maturity list drifted")

    people: dict[str, dict[str, Any]] = {}
    for item in inventory["people"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV3Error("inventory person is not an object")
        person_id = _identifier(item.get("person_id"), "inventory person_id")
        if person_id in people:
            raise SharedGrowthIntegrationV3Error("duplicate inventory person")
        people[person_id] = item

    routes: dict[str, dict[str, Any]] = {}
    for item in inventory["routes"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV3Error("inventory route is not an object")
        route_id = _identifier(item.get("route_id"), "inventory route_id")
        if route_id in routes:
            raise SharedGrowthIntegrationV3Error("duplicate inventory route")
        routes[route_id] = item

    maturity: dict[str, dict[str, Any]] = {}
    for item in inventory["maturity_sources"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV3Error("maturity source is not an object")
        source_id = _identifier(item.get("source_id"), "maturity source_id")
        if source_id in maturity:
            raise SharedGrowthIntegrationV3Error("duplicate maturity source")
        maturity[source_id] = item
    return people, routes, maturity


def _validate_request(value: Any, inventory: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    request = _exact_object(value, _INPUT_KEYS, "request")
    if type(request["schema"]) is not str or request["schema"] != INPUT_SCHEMA:
        raise SharedGrowthIntegrationV3Error("request schema drifted")
    if (
        type(request["target_kind"]) is not str
        or request["target_kind"] != "existing_person"
    ):
        raise SharedGrowthIntegrationV3Error(
            "only an inert existing-person proposal is supported; Creator remains disconnected"
        )

    request_id = _identifier(request["request_id"], "request_id")
    route_id = _identifier(request["route_id"], "route_id")
    person_id = _identifier(request["person_id"], "person_id")
    candidate_id = _identifier(request["candidate_id"], "candidate_id")
    display_name = _text(request["display_name"], "display_name")
    person_class = _identifier(request["person_class"], "person_class")
    maturity_status = _identifier(request["maturity_status"], "maturity_status")
    maturity_source_id = _identifier(
        request["maturity_source_id"], "maturity_source_id"
    )
    profile_sha256 = _sha(request["profile_sha256"], "profile_sha256")
    opt_in_sha256 = _sha(
        request["person_opt_in_receipt_sha256"],
        "person_opt_in_receipt_sha256",
    )
    assert isinstance(profile_sha256, str) and isinstance(opt_in_sha256, str)

    if (
        type(request["requested_scope"]) is not list
        or any(type(item) is not str for item in request["requested_scope"])
        or request["requested_scope"] != REQUESTED_SCOPE
    ):
        raise SharedGrowthIntegrationV3Error("requested_scope must be the one inert public scope")
    _exact_bool(request["person_opt_in"], True, "person_opt_in")
    _exact_bool(request["revocable"], True, "revocable")
    _exact_bool(request["owner_override_allowed"], False, "owner_override_allowed")
    _exact_bool(request["production_enabled"], False, "production_enabled")
    _exact_bool(request["private_state_requested"], False, "private_state_requested")
    _exact_bool(request["memory_write_requested"], False, "memory_write_requested")
    _exact_bool(request["external_action_requested"], False, "external_action_requested")

    if person_id in {"robert", "biological_robert", "robert_mcmurrer"}:
        raise SharedGrowthIntegrationV3Error("generic or Biological Robert is not Synthetic Robert")

    people, routes, maturity_sources = _inventory_indexes(inventory)
    if person_id not in people or route_id not in routes:
        raise SharedGrowthIntegrationV3Error("exact person or route is absent")
    person = people[person_id]
    route = routes[route_id]
    if route.get("disposition") != "applicable":
        raise SharedGrowthIntegrationV3Error("route is not applicable")
    expected_person = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "person_class": person_class,
        "required_maturity": maturity_status,
        "maturity_source_id": maturity_source_id,
    }
    if any(person.get(key) != expected for key, expected in expected_person.items()):
        raise SharedGrowthIntegrationV3Error("request person binding differs from inventory")
    route_expected = {
        "person_id": person_id,
        "candidate_id": candidate_id,
        "route_id": route_id,
    }
    if any(route.get(key) != expected for key, expected in route_expected.items()):
        raise SharedGrowthIntegrationV3Error("request route binding differs from inventory")
    if maturity_source_id not in maturity_sources:
        raise SharedGrowthIntegrationV3Error("maturity source is absent")
    maturity_source = maturity_sources[maturity_source_id]
    permitted = maturity_source.get("permitted_status")
    if maturity_status not in {"confirmed_adult", "non_adult", "unresolved"}:
        raise SharedGrowthIntegrationV3Error("maturity status is unsupported")
    if permitted != maturity_status and not (
        maturity_status == "non_adult" and permitted == "subject_specific"
    ):
        raise SharedGrowthIntegrationV3Error("maturity source is cross-bound")
    maturity_receipt = _sha(
        request["maturity_receipt_sha256"],
        "maturity_receipt_sha256",
        nullable=maturity_status == "unresolved",
    )
    if maturity_status == "unresolved" and maturity_receipt is not None:
        raise SharedGrowthIntegrationV3Error("unresolved maturity cannot claim a receipt")
    if maturity_status != "unresolved" and not isinstance(maturity_receipt, str):
        raise SharedGrowthIntegrationV3Error("classified maturity requires an exact receipt")

    source_path = route.get("source_path")
    source_sha256 = route.get("source_sha256")
    if type(source_path) is not str:
        raise SharedGrowthIntegrationV3Error("route source path is invalid")
    source_sha = _sha(source_sha256, "route source digest")
    assert isinstance(source_sha, str)
    source_file = _resolve_project_file(source_path)
    if not source_file.is_file() or source_file.is_symlink():
        raise SharedGrowthIntegrationV3Error("route source is absent or a symlink")
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
        "requested_scope": list(REQUESTED_SCOPE),
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": opt_in_sha256,
        "revocable": True,
        "owner_override_allowed": False,
    }
    route_snapshot = {
        "route_id": route_id,
        "source_path": source_path,
        "source_bytes": source_bytes,
        "source_sha256": source_sha,
        "stable_double_read": True,
    }
    return normalized, route_snapshot


def compile_disconnected_integration_request_v3(value: Any) -> bytes:
    """Return inert canonical proposal bytes; perform no write or state change."""

    inventory, closure_rows = _fixed_closure_snapshot()
    normalized, route_snapshot = _validate_request(value, inventory)
    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "request": normalized,
        "route_snapshot": route_snapshot,
        "closure": list(closure_rows),
        "truth": {
            "accepted_isolated_core_unchanged": True,
            "integration_v1_rejected": True,
            "integration_v2_rejected": True,
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
            "temporary_creator_supported": False,
            "protected_native_broker_exists": False,
            "different_fresh_audit_required": True,
        },
    }
    proposal_bytes = _canonical_bytes(proposal)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "proposal": proposal,
        "proposal_sha256": _sha_bytes(proposal_bytes),
    }
    result = _canonical_bytes(envelope)

    inventory_after, closure_after = _fixed_closure_snapshot()
    normalized_after, route_after = _validate_request(value, inventory_after)
    if (
        closure_after != closure_rows
        or normalized_after != normalized
        or route_after != route_snapshot
    ):
        raise SharedGrowthIntegrationV3Error("authority inputs changed during construction")
    decoded = _decode_strict_object(result, "compiled envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV3Error("compiled envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV3Error("compiled proposal digest mismatch")
    return result


def open_shared_growth_v3_production_integration(*_args: Any, **_kwargs: Any) -> None:
    """Production integration is intentionally absent and always refuses."""

    raise SharedGrowthIntegrationV3Error(
        "Shared Growth integration V3 is disconnected inert-byte evidence only"
    )


__all__ = [
    "ENVELOPE_SCHEMA",
    "INPUT_SCHEMA",
    "PROJECT_ROOT",
    "PROPOSAL_SCHEMA",
    "REQUESTED_SCOPE",
    "SharedGrowthIntegrationV3Error",
    "compile_disconnected_integration_request_v3",
    "open_shared_growth_v3_production_integration",
]
