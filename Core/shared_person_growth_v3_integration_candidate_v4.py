"""Disconnected Shared Growth V3 integration-request compiler (V4).

The accepted isolated Shared Growth V3 core remains static-only.  Integration
V1, V2, and V3 remain rejected. This append-only successor retains the absence
of every verifier, callback, controller, staging, commit, rollback, cleanup,
and person-state mutation capability from the Python surface. It can only compile an exact
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


_AUTHOR_ROOT = Path(__file__).resolve().parents[1]
_KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
_V3_REJECTION_ROOT = _AUTHOR_ROOT.parent / "growth_v3_quality_review"

INPUT_SCHEMA = "kira.shared_person_growth.integration_request_input.v4"
PROPOSAL_SCHEMA = "kira.shared_person_growth.integration_broker_proposal.v4"
ENVELOPE_SCHEMA = "kira.shared_person_growth.integration_request_envelope.v4"

# Private and immutable. Every accepted input and returned proposal receives a
# newly created list derived from this exact tuple.
_CANONICAL_SCOPE: tuple[str, ...] = (
    "shared_growth_v3_public_projection_only",
)

_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

_PREDECESSOR_SUBJECTS = (
    (
        "kira",
        "Core/shared_person_growth_v3_integration_candidate_v3.py",
        20715,
        "dcbde9ca1a6fedc43dc70625e3ac747839e8d60875a421fde09b44b2f8ff52c6",
        "rejected_v3_candidate_source",
    ),
    (
        "kira",
        "Testing/test_shared_person_growth_v3_integration_candidate_v3.py",
        19755,
        "f2cc4b23947ff00f717d7619b42265fbe6b54fbfb972d88d7d9f324f1471083b",
        "rejected_v3_candidate_test",
    ),
    (
        "kira",
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v3_static_preparation/"
        "attempt_01/STATIC_CONTRACT.json",
        3247,
        "48c6fd29994894a2551ae01fcef4b43055a4781b6139d1161f27305cf7db65dd",
        "rejected_v3_static_contract",
    ),
    (
        "kira",
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v3_static_preparation/"
        "attempt_01/AUTHOR_STATIC_TEST_RESULT.json",
        2193,
        "189bc4332bf63bc661a65951be4501ec51358d7cb3ed10654eef704ae050dc71",
        "rejected_v3_author_result",
    ),
    (
        "kira",
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v3_static_preparation/"
        "attempt_01/SEALED_MANIFEST.json",
        4092,
        "8c042caded327d3ad3d52f59a51b299bc27cfff51a70d9b7e4b56f97b766fa57",
        "rejected_v3_seal",
    ),
    (
        "kira",
        "RecoverySprint/continuation_20260811/"
        "shared_person_growth_v3_integration_candidate_v3_static_preparation/"
        "attempt_01/CHECKPOINT.md",
        3974,
        "75cab078fabafc04238b57a3b47d2c70f7282dba2fdaeee7b62e705b395d87de",
        "rejected_v3_author_checkpoint",
    ),
    (
        "v3_rejection",
        "AUDIT_DECISION.json",
        6132,
        "ef80b3a5b0e75b213df7048e19a2753f0618b2983831a09c88eff8b2a099288a",
        "v3_rejection_decision",
    ),
    (
        "v3_rejection",
        "REVIEW_PROBES.md",
        9071,
        "f3121b3082eb49942403d80b126ddcb03a4c1f0631ee0c8b9d0bef60605c791c",
        "v3_rejection_probes",
    ),
    (
        "v3_rejection",
        "CHECKPOINT.md",
        2708,
        "e68c8e74e2590248c1c5a05473e840e7a1c7f8f662c28337d1938befd49c95a6",
        "v3_rejection_checkpoint",
    ),
)

_CURRENT_INVENTORY_SUBJECT = (
    "kira",
    "Data/foundation/shared_person_growth_v3_integration_candidate_v1.json",
    28107,
    "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
    "current_inventory",
)

_INPUT_KEYS = frozenset({
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
})


class SharedGrowthIntegrationV4Error(ValueError):
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
            raise SharedGrowthIntegrationV4Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise SharedGrowthIntegrationV4Error(f"nonfinite JSON value: {value}")


def _decode_strict_object(value: bytes, field: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise SharedGrowthIntegrationV4Error(f"{field} must be nonempty bytes")
    try:
        decoded = json.loads(
            value,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SharedGrowthIntegrationV4Error(f"{field} is not strict JSON") from exc
    if type(decoded) is not dict:
        raise SharedGrowthIntegrationV4Error(f"{field} must be an object")
    return decoded


def _exact_object(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SharedGrowthIntegrationV4Error(f"{field} exact schema mismatch")
    if any(type(key) is not str for key in value):
        raise SharedGrowthIntegrationV4Error(f"{field} has a non-string key")
    return value


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise SharedGrowthIntegrationV4Error(f"{field} is not canonical")
    return value


def _text(value: Any, field: str, maximum: int = 256) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise SharedGrowthIntegrationV4Error(f"{field} must be exact nonempty text")
    if len(value.encode("utf-8")) > maximum:
        raise SharedGrowthIntegrationV4Error(f"{field} exceeds {maximum} bytes")
    return value


def _sha(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if (
        type(value) is not str
        or _SHA_RE.fullmatch(value) is None
        or value == "0" * 64
    ):
        raise SharedGrowthIntegrationV4Error(f"{field} is not an exact digest")
    return value


def _exact_bool(value: Any, expected: bool, field: str) -> None:
    if type(value) is not bool or value is not expected:
        raise SharedGrowthIntegrationV4Error(f"{field} must be exact {expected}")


def _bound_root(root_id: str) -> Path:
    if type(root_id) is not str:
        raise SharedGrowthIntegrationV4Error("bound root identifier is invalid")
    if root_id == "kira":
        root = _KIRA_ROOT
    elif root_id == "v3_rejection":
        root = _V3_REJECTION_ROOT
    else:
        raise SharedGrowthIntegrationV4Error("bound root identifier is unknown")
    if root.is_symlink() or not root.is_dir():
        raise SharedGrowthIntegrationV4Error("bound root is absent or a symlink")
    return root.resolve()


def _resolve_bound_file(root_id: str, relative_path: str) -> Path:
    if type(relative_path) is not str or not relative_path:
        raise SharedGrowthIntegrationV4Error("bound path is invalid")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise SharedGrowthIntegrationV4Error("bound path escaped its root")
    root = _bound_root(root_id)
    unresolved = root / relative
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SharedGrowthIntegrationV4Error("bound path contains a symlink")
    path = unresolved.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SharedGrowthIntegrationV4Error("bound path escaped its root") from exc
    return path


def _stable_exact_read(
    root_id: str,
    relative_path: str,
    expected_bytes: int,
    expected_sha256: str,
    field: str,
) -> bytes:
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise SharedGrowthIntegrationV4Error(f"{field} byte contract is invalid")
    _sha(expected_sha256, f"{field} digest")
    path = _resolve_bound_file(root_id, relative_path)
    if not path.is_file() or path.is_symlink():
        raise SharedGrowthIntegrationV4Error(f"{field} is absent or a symlink")
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
        raise SharedGrowthIntegrationV4Error(f"{field} changed during read")
    if len(first) != expected_bytes or _sha_bytes(first) != expected_sha256:
        raise SharedGrowthIntegrationV4Error(f"{field} exact bytes drifted")
    return first


def _fixed_closure_snapshot() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    rows: list[dict[str, Any]] = []
    for root_id, relative_path, byte_count, sha256, role in _PREDECESSOR_SUBJECTS:
        _stable_exact_read(root_id, relative_path, byte_count, sha256, role)
        rows.append(
            {
                "root": root_id,
                "path": relative_path,
                "bytes": byte_count,
                "sha256": sha256,
                "role": role,
            }
        )
    root_id, relative_path, byte_count, sha256, role = _CURRENT_INVENTORY_SUBJECT
    inventory_bytes = _stable_exact_read(
        root_id,
        relative_path,
        byte_count,
        sha256,
        role,
    )
    rows.append(
        {
            "root": root_id,
            "path": relative_path,
            "bytes": byte_count,
            "sha256": sha256,
            "role": role,
        }
    )
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
        raise SharedGrowthIntegrationV4Error("inventory schema drifted")
    if type(inventory["people"]) is not list or type(inventory["routes"]) is not list:
        raise SharedGrowthIntegrationV4Error("inventory person/route lists drifted")
    if type(inventory["maturity_sources"]) is not list:
        raise SharedGrowthIntegrationV4Error("inventory maturity list drifted")

    people: dict[str, dict[str, Any]] = {}
    for item in inventory["people"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV4Error("inventory person is not an object")
        person_id = _identifier(item.get("person_id"), "inventory person_id")
        if person_id in people:
            raise SharedGrowthIntegrationV4Error("duplicate inventory person")
        people[person_id] = item

    routes: dict[str, dict[str, Any]] = {}
    for item in inventory["routes"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV4Error("inventory route is not an object")
        route_id = _identifier(item.get("route_id"), "inventory route_id")
        if route_id in routes:
            raise SharedGrowthIntegrationV4Error("duplicate inventory route")
        routes[route_id] = item

    maturity: dict[str, dict[str, Any]] = {}
    for item in inventory["maturity_sources"]:
        if type(item) is not dict:
            raise SharedGrowthIntegrationV4Error("maturity source is not an object")
        source_id = _identifier(item.get("source_id"), "maturity source_id")
        if source_id in maturity:
            raise SharedGrowthIntegrationV4Error("duplicate maturity source")
        maturity[source_id] = item
    return people, routes, maturity


def _validate_request(value: Any, inventory: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    request = _exact_object(value, _INPUT_KEYS, "request")
    if type(request["schema"]) is not str or request["schema"] != INPUT_SCHEMA:
        raise SharedGrowthIntegrationV4Error("request schema drifted")
    if (
        type(request["target_kind"]) is not str
        or request["target_kind"] != "existing_person"
    ):
        raise SharedGrowthIntegrationV4Error(
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

    exact_scope = list(_CANONICAL_SCOPE)
    if (
        type(request["requested_scope"]) is not list
        or any(type(item) is not str for item in request["requested_scope"])
        or request["requested_scope"] != exact_scope
    ):
        raise SharedGrowthIntegrationV4Error("requested_scope must be the one inert public scope")
    _exact_bool(request["person_opt_in"], True, "person_opt_in")
    _exact_bool(request["revocable"], True, "revocable")
    _exact_bool(request["owner_override_allowed"], False, "owner_override_allowed")
    _exact_bool(request["production_enabled"], False, "production_enabled")
    _exact_bool(request["private_state_requested"], False, "private_state_requested")
    _exact_bool(request["memory_write_requested"], False, "memory_write_requested")
    _exact_bool(request["external_action_requested"], False, "external_action_requested")

    if person_id in {"robert", "biological_robert", "robert_mcmurrer"}:
        raise SharedGrowthIntegrationV4Error("generic or Biological Robert is not Synthetic Robert")

    people, routes, maturity_sources = _inventory_indexes(inventory)
    if person_id not in people or route_id not in routes:
        raise SharedGrowthIntegrationV4Error("exact person or route is absent")
    person = people[person_id]
    route = routes[route_id]
    if route.get("disposition") != "applicable":
        raise SharedGrowthIntegrationV4Error("route is not applicable")
    expected_person = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "person_class": person_class,
        "required_maturity": maturity_status,
        "maturity_source_id": maturity_source_id,
    }
    if any(person.get(key) != expected for key, expected in expected_person.items()):
        raise SharedGrowthIntegrationV4Error("request person binding differs from inventory")
    route_expected = {
        "person_id": person_id,
        "candidate_id": candidate_id,
        "route_id": route_id,
    }
    if any(route.get(key) != expected for key, expected in route_expected.items()):
        raise SharedGrowthIntegrationV4Error("request route binding differs from inventory")
    if maturity_source_id not in maturity_sources:
        raise SharedGrowthIntegrationV4Error("maturity source is absent")
    maturity_source = maturity_sources[maturity_source_id]
    permitted = maturity_source.get("permitted_status")
    if maturity_status not in {"confirmed_adult", "non_adult", "unresolved"}:
        raise SharedGrowthIntegrationV4Error("maturity status is unsupported")
    if permitted not in {maturity_status, "subject_specific"}:
        raise SharedGrowthIntegrationV4Error("maturity source is cross-bound")
    maturity_receipt = _sha(
        request["maturity_receipt_sha256"],
        "maturity_receipt_sha256",
        nullable=maturity_status == "unresolved",
    )
    if maturity_status == "unresolved" and maturity_receipt is not None:
        raise SharedGrowthIntegrationV4Error("unresolved maturity cannot claim a receipt")
    if maturity_status != "unresolved" and not isinstance(maturity_receipt, str):
        raise SharedGrowthIntegrationV4Error("classified maturity requires an exact receipt")

    source_path = route.get("source_path")
    source_sha256 = route.get("source_sha256")
    if type(source_path) is not str:
        raise SharedGrowthIntegrationV4Error("route source path is invalid")
    source_sha = _sha(source_sha256, "route source digest")
    assert isinstance(source_sha, str)
    source_file = _resolve_bound_file("kira", source_path)
    if not source_file.is_file() or source_file.is_symlink():
        raise SharedGrowthIntegrationV4Error("route source is absent or a symlink")
    source_bytes = source_file.stat().st_size
    _stable_exact_read("kira", source_path, source_bytes, source_sha, "current route source")

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


def compile_disconnected_integration_request_v4(value: Any) -> bytes:
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
            "integration_v3_rejected": True,
            "integration_v4_accepted": False,
            "integration_v4_promoted": False,
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
        raise SharedGrowthIntegrationV4Error("authority inputs changed during construction")
    decoded = _decode_strict_object(result, "compiled envelope")
    if _canonical_bytes(decoded) != result:
        raise SharedGrowthIntegrationV4Error("compiled envelope is not canonical")
    if _sha_bytes(_canonical_bytes(decoded["proposal"])) != decoded["proposal_sha256"]:
        raise SharedGrowthIntegrationV4Error("compiled proposal digest mismatch")
    return result


def open_shared_growth_v4_production_integration(*_args: Any, **_kwargs: Any) -> None:
    """Production integration is intentionally absent and always refuses."""

    raise SharedGrowthIntegrationV4Error(
        "Shared Growth integration V4 is disconnected inert-byte evidence only"
    )


__all__ = (
    "ENVELOPE_SCHEMA",
    "INPUT_SCHEMA",
    "PROPOSAL_SCHEMA",
    "SharedGrowthIntegrationV4Error",
    "compile_disconnected_integration_request_v4",
    "open_shared_growth_v4_production_integration",
)
