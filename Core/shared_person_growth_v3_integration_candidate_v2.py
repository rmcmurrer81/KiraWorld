"""Append-only Shared Growth V3 integration successor (V2, static only).

The V1 integration candidate was rejected because its public adapter retained
an inspectable identity, secret, V3 controller, and controller identity, and
because route-source hashes were checked only at construction.  V2 preserves
V1 as rejected evidence and narrows the boundary:

* the adapter stores no issuer, controller, identity, secret, capability,
  callback, receipt ledger, or authority object;
* an external authority callback is supplied separately for each operation
  and is never retained by the adapter;
* the public production opener remains unconditionally disconnected;
* the inventory and exact route source are freshly reloaded, double-read, and
  rehashed at issue, stage, final commit, and final readback gates;
* external one-use envelopes/tickets/receipts bind every gate and the output
  readback, while the Python adapter truthfully remains only a static protocol
  client rather than an OS trust root.

This module can write only default-off static attachments under an explicitly
provided staging root.  It cannot promote a profile, edit a registry or
person, invoke Temporary Creator, or enable a live capability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import secrets
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from Core import shared_person_growth_v3_integration_candidate_v1 as v1


_SIGNED_RESPONSE_DOMAIN = b"KIRA_SHARED_GROWTH_V3_INTEGRATION_V2_RESPONSE\x00"


class GrowthIntegrationV2Error(v1.GrowthIntegrationError):
    """V2 external-authority or source-gate contract failed closed."""


class GrowthIntegrationV2AuthorityError(v1.GrowthIntegrationAuthorityError):
    """The separately supplied external authority response was not exact."""


class GrowthIntegrationV2RecoveryRequired(v1.GrowthIntegrationRecoveryRequired):
    """A failed post-write transaction could not prove external rollback."""


class ExternalGrowthIntegrationAuthorityV2(Protocol):
    """Per-operation callback contract; implementing it is not OS attestation."""

    def __call__(self, request_bytes: bytes) -> bytes: ...


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


def _sha_mapping(value: Mapping[str, Any]) -> str:
    return _sha_bytes(_canonical_bytes(value))


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GrowthIntegrationV2Error(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def _decode_canonical_object(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise GrowthIntegrationV2AuthorityError(
            f"{field} must be nonempty canonical bytes"
        )
    try:
        decoded = json.loads(value, object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthIntegrationV2AuthorityError(f"{field} is not strict JSON") from exc
    if type(decoded) is not dict or _canonical_bytes(decoded) != value:
        raise GrowthIntegrationV2AuthorityError(
            f"{field} is not an exact canonical object"
        )
    return decoded


def _exact(value: Any, keys: set[str], field: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise GrowthIntegrationV2Error(f"{field} exact schema mismatch")
    return value


def _identifier(value: Any, field: str) -> str:
    return v1._identifier(value, field)


def _sha(value: Any, field: str) -> str:
    result = v1._sha(value, field)
    assert isinstance(result, str)
    return result


def _stable_bound_file_snapshot(
    *,
    project_root: Path,
    relative_path: str,
    expected_sha256: str,
    route_id: str,
    gate: str,
    inventory_sha256: str,
    inventory_byte_count: int,
) -> dict[str, Any]:
    relative = v1._relative_path(relative_path, "route source path")
    assert isinstance(relative, str)
    path = (project_root / relative).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise GrowthIntegrationV2Error("route source escaped the project") from exc
    if not path.is_file() or path.is_symlink():
        raise GrowthIntegrationV2Error("route source is absent or a symlink")
    before = path.stat()
    first = path.read_bytes()
    middle = path.stat()
    second = path.read_bytes()
    after = path.stat()
    stable = (
        first == second
        and before.st_size == middle.st_size == after.st_size == len(first)
        and before.st_mtime_ns == middle.st_mtime_ns == after.st_mtime_ns
    )
    if not stable:
        raise GrowthIntegrationV2Error("route source changed during stable snapshot")
    observed_sha256 = _sha_bytes(first)
    if observed_sha256 != expected_sha256:
        raise GrowthIntegrationV2Error(
            f"route source hash drifted at {gate}: {relative}"
        )
    core = {
        "schema": "kira.shared_person_growth.route_source_gate.v2",
        "gate": gate,
        "route_id": route_id,
        "source_path": relative,
        "expected_sha256": expected_sha256,
        "observed_sha256": observed_sha256,
        "source_byte_count": len(first),
        "inventory_sha256": inventory_sha256,
        "inventory_byte_count": inventory_byte_count,
        "stable_double_read": True,
        "source_matches_inventory": True,
        "production_pointer_changed": False,
    }
    result = dict(core)
    result["snapshot_sha256"] = _sha_mapping(core)
    return result


def _validate_source_snapshot(
    value: Any,
    *,
    expected_gate: str,
    field: str,
) -> dict[str, Any]:
    keys = {
        "schema",
        "gate",
        "route_id",
        "source_path",
        "expected_sha256",
        "observed_sha256",
        "source_byte_count",
        "inventory_sha256",
        "inventory_byte_count",
        "stable_double_read",
        "source_matches_inventory",
        "production_pointer_changed",
        "snapshot_sha256",
    }
    snapshot = _exact(value, keys, field)
    fixed = {
        "schema": "kira.shared_person_growth.route_source_gate.v2",
        "gate": expected_gate,
        "stable_double_read": True,
        "source_matches_inventory": True,
        "production_pointer_changed": False,
    }
    if any(snapshot.get(key) != expected for key, expected in fixed.items()):
        raise GrowthIntegrationV2AuthorityError(f"{field} truth binding changed")
    _identifier(snapshot["route_id"], f"{field} route id")
    v1._relative_path(snapshot["source_path"], f"{field} source path")
    _sha(snapshot["expected_sha256"], f"{field} expected digest")
    _sha(snapshot["observed_sha256"], f"{field} observed digest")
    _sha(snapshot["inventory_sha256"], f"{field} inventory digest")
    if (
        type(snapshot["source_byte_count"]) is not int
        or snapshot["source_byte_count"] < 1
        or type(snapshot["inventory_byte_count"]) is not int
        or snapshot["inventory_byte_count"] < 1
    ):
        raise GrowthIntegrationV2AuthorityError(f"{field} byte count changed")
    unsigned = copy.deepcopy(dict(snapshot))
    digest = unsigned.pop("snapshot_sha256")
    if _sha(digest, f"{field} snapshot digest") != _sha_mapping(unsigned):
        raise GrowthIntegrationV2AuthorityError(f"{field} digest changed")
    return copy.deepcopy(dict(snapshot))


class _ControllerProjection:
    """Public controller labels only; never a controller or authority handle."""

    __slots__ = ("controller_id", "controller_identity_sha256")

    def __init__(self, controller_id: str, controller_identity_sha256: str) -> None:
        self.controller_id = _identifier(controller_id, "controller id")
        self.controller_identity_sha256 = _sha(
            controller_identity_sha256, "controller identity"
        )


def _validate_authority_binding(
    value: Mapping[str, Any],
    *,
    expected_verification_key_sha256: str,
) -> dict[str, Any]:
    keys = {
        "schema",
        "authority_instance_id",
        "authority_epoch_sha256",
        "authority_verification_key_sha256",
        "controller_id",
        "controller_identity_sha256",
        "protected_external_callback_required",
        "callback_retained_by_adapter",
        "python_adapter_is_trust_root",
        "production_enabled",
    }
    binding = _exact(value, keys, "external authority binding")
    fixed = {
        "schema": "kira.shared_person_growth.external_authority_binding.v2",
        "protected_external_callback_required": True,
        "callback_retained_by_adapter": False,
        "python_adapter_is_trust_root": False,
        "production_enabled": False,
    }
    if any(binding.get(key) is not expected if type(expected) is bool else binding.get(key) != expected for key, expected in fixed.items()):
        raise GrowthIntegrationV2AuthorityError("external authority truth binding changed")
    _identifier(binding["authority_instance_id"], "authority instance id")
    _sha(binding["authority_epoch_sha256"], "authority epoch")
    if (
        _sha(
            binding["authority_verification_key_sha256"],
            "authority verification key digest",
        )
        != expected_verification_key_sha256
    ):
        raise GrowthIntegrationV2AuthorityError(
            "external authority verification key cross-binding"
        )
    _identifier(binding["controller_id"], "controller id")
    _sha(binding["controller_identity_sha256"], "controller identity")
    return copy.deepcopy(dict(binding))


def _validate_external_public_attachment(
    value: Mapping[str, Any],
    *,
    inventory: Mapping[str, Any],
    inventory_sha256: str,
    authority_binding: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _ControllerProjection(
        authority_binding["controller_id"],
        authority_binding["controller_identity_sha256"],
    )
    checked = v1.validate_public_attachment(
        value,
        inventory=inventory,
        inventory_digest=inventory_sha256,
        authority_controller=projection,  # type: ignore[arg-type]
    )
    if checked["integration_truth"]["production_pointer_changed"] is not False:
        raise GrowthIntegrationV2Error("attachment changed a production pointer")
    return checked


def _call_external(
    callback: ExternalGrowthIntegrationAuthorityV2,
    request: Mapping[str, Any],
    *,
    authority_public_key: Ed25519PublicKey,
    authority_verification_key_sha256: str,
    expected_schema: str,
    response_keys: set[str],
    field: str,
) -> dict[str, Any]:
    if not callable(callback):
        raise GrowthIntegrationV2AuthorityError(
            "separately supplied external authority callback is required"
        )
    challenged_request = copy.deepcopy(dict(request))
    challenged_request["authority_challenge_hex"] = secrets.token_hex(32)
    request_bytes = _canonical_bytes(challenged_request)
    try:
        response_bytes = callback(request_bytes)
    except Exception as exc:
        raise GrowthIntegrationV2AuthorityError(
            f"external authority callback failed at {field}"
        ) from exc
    response = _decode_canonical_object(response_bytes, field)
    _exact(
        response,
        response_keys
        | {
            "request_sha256",
            "response_sha256",
            "authority_signature_hex",
        },
        field,
    )
    if response.get("schema") != expected_schema:
        raise GrowthIntegrationV2AuthorityError(f"{field} schema changed")
    if response.get("request_sha256") != _sha_bytes(request_bytes):
        raise GrowthIntegrationV2AuthorityError(f"{field} request cross-binding")
    unsigned = copy.deepcopy(response)
    signature_hex = unsigned.pop("authority_signature_hex")
    response_sha256 = unsigned.pop("response_sha256")
    if _sha(response_sha256, f"{field} response digest") != _sha_mapping(unsigned):
        raise GrowthIntegrationV2AuthorityError(f"{field} response digest changed")
    if type(signature_hex) is not str or len(signature_hex) != 128:
        raise GrowthIntegrationV2AuthorityError(f"{field} signature format changed")
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise GrowthIntegrationV2AuthorityError(
            f"{field} signature is not hexadecimal"
        ) from exc
    try:
        authority_public_key.verify(
            signature,
            _SIGNED_RESPONSE_DOMAIN + _canonical_bytes(unsigned),
        )
    except InvalidSignature as exc:
        raise GrowthIntegrationV2AuthorityError(
            f"{field} external authority signature failed"
        ) from exc
    if (
        _sha_bytes(
            authority_public_key.public_bytes_raw()
        )
        != authority_verification_key_sha256
    ):
        raise GrowthIntegrationV2AuthorityError(
            f"{field} authority verifier identity drifted"
        )
    if response.get("static_only") is not True or response.get("production_enabled") is not False:
        raise GrowthIntegrationV2AuthorityError(f"{field} production truth changed")
    return response


def _validate_ticket(
    value: Mapping[str, Any],
    *,
    schema: str,
    kind: str,
    authority_binding: Mapping[str, Any],
    inventory_sha256: str,
    attachment_sha256: str,
    prior_sha256: str | None,
) -> dict[str, Any]:
    keys = {
        "schema",
        "ticket_kind",
        "ticket_id",
        "authority_binding_sha256",
        "inventory_sha256",
        "attachment_sha256",
        "prior_ticket_sha256",
        "source_gate_snapshot_sha256",
        "output_sha256",
        "single_use",
        "static_only",
        "production_enabled",
        "opaque_authority_authenticator_sha256",
        "ticket_sha256",
    }
    ticket = _exact(value, keys, f"{kind} ticket")
    fixed = {
        "schema": schema,
        "ticket_kind": kind,
        "authority_binding_sha256": _sha_mapping(authority_binding),
        "inventory_sha256": inventory_sha256,
        "attachment_sha256": attachment_sha256,
        "prior_ticket_sha256": prior_sha256,
        "single_use": True,
        "static_only": True,
        "production_enabled": False,
    }
    if any(ticket.get(key) != expected for key, expected in fixed.items()):
        raise GrowthIntegrationV2AuthorityError(f"{kind} ticket binding changed")
    _identifier(ticket["ticket_id"], f"{kind} ticket id")
    _sha(ticket["source_gate_snapshot_sha256"], f"{kind} source gate")
    if ticket["output_sha256"] is not None:
        _sha(ticket["output_sha256"], f"{kind} output digest")
    _sha(
        ticket["opaque_authority_authenticator_sha256"],
        f"{kind} opaque authenticator",
    )
    unsigned = copy.deepcopy(dict(ticket))
    digest = unsigned.pop("ticket_sha256")
    if _sha(digest, f"{kind} ticket digest") != _sha_mapping(unsigned):
        raise GrowthIntegrationV2AuthorityError(f"{kind} ticket digest changed")
    return copy.deepcopy(dict(ticket))


class SharedGrowthV3ExternalAuthorityAdapterV2:
    """Inspectable public adapter with no retained issuance authority."""

    __slots__ = (
        "_authority_public_key",
        "_authority_verification_key_sha256",
        "_inventory",
        "_inventory_path",
        "_inventory_sha256",
        "_project_root",
        "_staging_root",
        "_lock",
    )

    def __init__(
        self,
        *,
        staging_root: Path,
        authority_public_key_raw: bytes,
        inventory_path: Path = v1.INVENTORY_PATH,
        project_root: Path = v1.PROJECT_ROOT,
    ) -> None:
        if not isinstance(staging_root, Path):
            raise GrowthIntegrationV2Error("staging_root must be pathlib.Path")
        if type(authority_public_key_raw) is not bytes or len(authority_public_key_raw) != 32:
            raise GrowthIntegrationV2AuthorityError(
                "exact 32-byte Ed25519 authority public key is required"
            )
        try:
            self._authority_public_key = Ed25519PublicKey.from_public_bytes(
                authority_public_key_raw
            )
        except ValueError as exc:
            raise GrowthIntegrationV2AuthorityError(
                "authority public verification key is invalid"
            ) from exc
        self._authority_verification_key_sha256 = _sha_bytes(authority_public_key_raw)
        self._project_root = project_root.resolve()
        self._inventory_path = inventory_path.resolve()
        self._inventory = v1.load_integration_inventory(
            self._inventory_path,
            project_root=self._project_root,
            verify_current_routes=True,
        )
        self._inventory_sha256 = _sha_bytes(self._inventory_path.read_bytes())
        self._staging_root = staging_root.resolve()
        self._staging_root.mkdir(parents=True, exist_ok=True)
        if self._staging_root.is_symlink():
            raise GrowthIntegrationV2Error("staging_root must not be a symlink")
        self._lock = threading.RLock()

    @property
    def inventory_digest(self) -> str:
        return self._inventory_sha256

    def _fresh_route(self, route_id: str, gate: str) -> tuple[dict[str, Any], dict[str, Any]]:
        route_id = _identifier(route_id, "route id")
        inventory_bytes = self._inventory_path.read_bytes()
        if _sha_bytes(inventory_bytes) != self._inventory_sha256:
            raise GrowthIntegrationV2Error(f"inventory changed at {gate}")
        fresh = v1.load_integration_inventory(
            self._inventory_path,
            project_root=self._project_root,
            verify_current_routes=True,
        )
        if not v1._typed_equal(fresh, self._inventory):
            raise GrowthIntegrationV2Error(f"inventory content changed at {gate}")
        routes = {item["route_id"]: item for item in fresh["routes"]}
        if route_id == fresh["creator_lane"]["route_id"]:
            route = {
                "route_id": route_id,
                "route_kind": "temporary_creator_new_person",
                "source_path": fresh["growth_v3_binding"]["creator_path"],
                "source_sha256": fresh["growth_v3_binding"]["creator_sha256"],
                "disposition": "applicable",
            }
        else:
            route = routes.get(route_id)
            if not isinstance(route, Mapping) or route.get("disposition") != "applicable":
                raise GrowthIntegrationV2AuthorityError(
                    "route is absent, denied, or not applicable"
                )
            route = copy.deepcopy(dict(route))
        snapshot = _stable_bound_file_snapshot(
            project_root=self._project_root,
            relative_path=route["source_path"],
            expected_sha256=route["source_sha256"],
            route_id=route_id,
            gate=gate,
            inventory_sha256=self._inventory_sha256,
            inventory_byte_count=len(inventory_bytes),
        )
        return route, snapshot

    @staticmethod
    def _same_source(first: Mapping[str, Any], second: Mapping[str, Any], field: str) -> None:
        stable_keys = {
            "route_id",
            "source_path",
            "expected_sha256",
            "observed_sha256",
            "source_byte_count",
            "inventory_sha256",
            "inventory_byte_count",
        }
        if any(first.get(key) != second.get(key) for key in stable_keys):
            raise GrowthIntegrationV2Error(f"route source changed across {field}")

    def _issue(
        self,
        *,
        authority_callback: ExternalGrowthIntegrationAuthorityV2,
        operation_id: str,
        route_id: str,
        payload_kind: str,
        payload: Mapping[str, Any],
    ) -> bytes:
        with self._lock:
            operation_id = _identifier(operation_id, "issue operation id")
            route_id = _identifier(route_id, "route id")
            _route, issue_pre = self._fresh_route(route_id, "ISSUE_PRE_AUTHORITY")
            request = {
                "schema": "kira.shared_person_growth.external_issue_request.v2",
                "action": "ISSUE_STATIC_MIGRATION_ENVELOPE",
                "operation_id": operation_id,
                "route_id": route_id,
                "payload_kind": payload_kind,
                "payload": copy.deepcopy(dict(payload)),
                "inventory_sha256": self._inventory_sha256,
                "source_gate_snapshot": issue_pre,
                "adapter_retains_callback": False,
                "static_only": True,
                "production_enabled": False,
            }
            response = _call_external(
                authority_callback,
                request,
                authority_public_key=self._authority_public_key,
                authority_verification_key_sha256=(
                    self._authority_verification_key_sha256
                ),
                expected_schema="kira.shared_person_growth.external_issue_response.v2",
                response_keys={
                    "schema",
                    "authority_binding",
                    "envelope",
                    "static_only",
                    "production_enabled",
                },
                field="external issue response",
            )
            authority_binding = _validate_authority_binding(
                response["authority_binding"],
                expected_verification_key_sha256=(
                    self._authority_verification_key_sha256
                ),
            )
            envelope_keys = {
                "schema",
                "envelope_id",
                "operation_id",
                "route_id",
                "inventory_sha256",
                "authority_binding",
                "issue_source_gate_snapshot",
                "attachment",
                "attachment_sha256",
                "single_use",
                "static_only",
                "production_enabled",
                "opaque_authority_authenticator_sha256",
                "envelope_sha256",
            }
            envelope = _exact(response["envelope"], envelope_keys, "migration envelope")
            if envelope["schema"] != "kira.shared_person_growth.migration_envelope.v2":
                raise GrowthIntegrationV2AuthorityError("migration envelope schema changed")
            fixed = {
                "operation_id": operation_id,
                "route_id": route_id,
                "inventory_sha256": self._inventory_sha256,
                "authority_binding": authority_binding,
                "issue_source_gate_snapshot": issue_pre,
                "single_use": True,
                "static_only": True,
                "production_enabled": False,
            }
            if any(envelope.get(key) != expected for key, expected in fixed.items()):
                raise GrowthIntegrationV2AuthorityError("migration envelope binding changed")
            _identifier(envelope["envelope_id"], "migration envelope id")
            _sha(
                envelope["opaque_authority_authenticator_sha256"],
                "migration envelope authenticator",
            )
            attachment = _validate_external_public_attachment(
                envelope["attachment"],
                inventory=self._inventory,
                inventory_sha256=self._inventory_sha256,
                authority_binding=authority_binding,
            )
            if (
                envelope["attachment_sha256"] != attachment["attachment_sha256"]
                or attachment["route_binding"]["route_id"] != route_id
                or attachment["source_binding"]["route_source_sha256"]
                != issue_pre["observed_sha256"]
            ):
                raise GrowthIntegrationV2AuthorityError(
                    "migration envelope attachment/source binding changed"
                )
            unsigned = copy.deepcopy(dict(envelope))
            digest = unsigned.pop("envelope_sha256")
            if _sha(digest, "migration envelope digest") != _sha_mapping(unsigned):
                raise GrowthIntegrationV2AuthorityError("migration envelope digest changed")
            _route, issue_post = self._fresh_route(route_id, "ISSUE_POST_AUTHORITY")
            self._same_source(issue_pre, issue_post, "issue authority callback")
            return _canonical_bytes(envelope)

    def issue_existing_person_migration(
        self,
        *,
        authority_callback: ExternalGrowthIntegrationAuthorityV2,
        operation_id: str,
        route_id: str,
        profile: Mapping[str, Any],
    ) -> bytes:
        return self._issue(
            authority_callback=authority_callback,
            operation_id=operation_id,
            route_id=route_id,
            payload_kind="EXISTING_PERSON_V3_PROFILE",
            payload=profile,
        )

    def issue_creator_migration(
        self,
        *,
        authority_callback: ExternalGrowthIntegrationAuthorityV2,
        operation_id: str,
        creator_bundle: Mapping[str, Any],
    ) -> bytes:
        return self._issue(
            authority_callback=authority_callback,
            operation_id=operation_id,
            route_id="creator:new_person",
            payload_kind="TEMPORARY_CREATOR_V3_BUNDLE",
            payload=creator_bundle,
        )

    def _parse_envelope(self, value: bytes) -> dict[str, Any]:
        envelope = _decode_canonical_object(value, "migration envelope")
        envelope_keys = {
            "schema",
            "envelope_id",
            "operation_id",
            "route_id",
            "inventory_sha256",
            "authority_binding",
            "issue_source_gate_snapshot",
            "attachment",
            "attachment_sha256",
            "single_use",
            "static_only",
            "production_enabled",
            "opaque_authority_authenticator_sha256",
            "envelope_sha256",
        }
        _exact(envelope, envelope_keys, "migration envelope")
        fixed = {
            "schema": "kira.shared_person_growth.migration_envelope.v2",
            "inventory_sha256": self._inventory_sha256,
            "single_use": True,
            "static_only": True,
            "production_enabled": False,
        }
        if any(envelope.get(key) != expected for key, expected in fixed.items()):
            raise GrowthIntegrationV2AuthorityError("migration envelope truth changed")
        _identifier(envelope["envelope_id"], "migration envelope id")
        _identifier(envelope["operation_id"], "migration envelope operation id")
        route_id = _identifier(envelope["route_id"], "migration envelope route id")
        issue_snapshot = _validate_source_snapshot(
            envelope["issue_source_gate_snapshot"],
            expected_gate="ISSUE_PRE_AUTHORITY",
            field="migration envelope issue source snapshot",
        )
        if (
            issue_snapshot["route_id"] != route_id
            or issue_snapshot["inventory_sha256"] != self._inventory_sha256
        ):
            raise GrowthIntegrationV2AuthorityError(
                "migration envelope issue source cross-binding"
            )
        _sha(
            envelope["opaque_authority_authenticator_sha256"],
            "migration envelope authenticator",
        )
        authority_binding = _validate_authority_binding(
            envelope.get("authority_binding"),
            expected_verification_key_sha256=(
                self._authority_verification_key_sha256
            ),
        )
        attachment = _validate_external_public_attachment(
            envelope.get("attachment"),
            inventory=self._inventory,
            inventory_sha256=self._inventory_sha256,
            authority_binding=authority_binding,
        )
        if (
            envelope.get("attachment_sha256") != attachment["attachment_sha256"]
            or attachment["route_binding"]["route_id"] != route_id
            or attachment["source_binding"]["route_source_sha256"]
            != issue_snapshot["observed_sha256"]
        ):
            raise GrowthIntegrationV2AuthorityError(
                "envelope attachment/source binding changed"
            )
        unsigned = copy.deepcopy(envelope)
        digest = unsigned.pop("envelope_sha256", None)
        if _sha(digest, "migration envelope digest") != _sha_mapping(unsigned):
            raise GrowthIntegrationV2AuthorityError("migration envelope digest changed")
        return envelope

    def stage_receipt(
        self,
        *,
        authority_callback: ExternalGrowthIntegrationAuthorityV2,
        receipt_envelope: bytes,
        operation_id: str,
    ) -> Path:
        with self._lock:
            operation_id = _identifier(operation_id, "stage operation id")
            envelope = self._parse_envelope(receipt_envelope)
            route_id = _identifier(envelope["route_id"], "route id")
            attachment = copy.deepcopy(envelope["attachment"])
            authority_binding = _validate_authority_binding(
                envelope["authority_binding"],
                expected_verification_key_sha256=(
                    self._authority_verification_key_sha256
                ),
            )
            _route, stage_pre = self._fresh_route(route_id, "STAGE_PRE_AUTHORITY")
            self._same_source(
                envelope["issue_source_gate_snapshot"], stage_pre, "issue to stage"
            )
            stage_request = {
                "schema": "kira.shared_person_growth.external_stage_request.v2",
                "action": "AUTHORIZE_STATIC_STAGE",
                "operation_id": operation_id,
                "envelope": envelope,
                "envelope_sha256": _sha_bytes(receipt_envelope),
                "stage_source_gate_snapshot": stage_pre,
                "static_only": True,
                "production_enabled": False,
            }
            stage_response = _call_external(
                authority_callback,
                stage_request,
                authority_public_key=self._authority_public_key,
                authority_verification_key_sha256=(
                    self._authority_verification_key_sha256
                ),
                expected_schema="kira.shared_person_growth.external_stage_response.v2",
                response_keys={
                    "schema",
                    "authority_binding",
                    "stage_ticket",
                    "static_only",
                    "production_enabled",
                },
                field="external stage response",
            )
            if _validate_authority_binding(
                stage_response["authority_binding"],
                expected_verification_key_sha256=(
                    self._authority_verification_key_sha256
                ),
            ) != authority_binding:
                raise GrowthIntegrationV2AuthorityError("stage authority cross-binding")
            stage_ticket = _validate_ticket(
                stage_response["stage_ticket"],
                schema="kira.shared_person_growth.stage_ticket.v2",
                kind="STAGE",
                authority_binding=authority_binding,
                inventory_sha256=self._inventory_sha256,
                attachment_sha256=attachment["attachment_sha256"],
                prior_sha256=envelope["envelope_sha256"],
            )
            if stage_ticket["source_gate_snapshot_sha256"] != stage_pre["snapshot_sha256"]:
                raise GrowthIntegrationV2AuthorityError("stage ticket source binding changed")
            if stage_ticket["output_sha256"] is not None:
                raise GrowthIntegrationV2AuthorityError("stage ticket prematurely binds output")
            _route, stage_post = self._fresh_route(route_id, "STAGE_POST_AUTHORITY")
            self._same_source(stage_pre, stage_post, "stage authority callback")

            profile_id = _identifier(
                attachment["profile_binding"]["profile_id"], "profile id"
            )
            output = self._staging_root / f"{profile_id}.shared_growth_integration_v2.json"
            if output.parent.resolve() != self._staging_root or output.is_symlink():
                raise GrowthIntegrationV2Error("staged output escaped exact root")
            text = json.dumps(
                attachment, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2
            ) + "\n"
            encoded = text.encode("utf-8")
            created = False
            commit_receipt: dict[str, Any] | None = None
            try:
                fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created = True
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
                if output.read_bytes() != encoded:
                    raise GrowthIntegrationV2Error("staged output exact readback failed")

                _route, commit_pre = self._fresh_route(route_id, "FINAL_COMMIT_PRE_AUTHORITY")
                self._same_source(stage_post, commit_pre, "stage to final commit")
                commit_request = {
                    "schema": "kira.shared_person_growth.external_commit_request.v2",
                    "action": "COMMIT_STATIC_STAGE",
                    "operation_id": f"commit:{operation_id}",
                    "stage_ticket": stage_ticket,
                    "attachment_sha256": attachment["attachment_sha256"],
                    "output_name": output.name,
                    "output_sha256": _sha_bytes(encoded),
                    "commit_source_gate_snapshot": commit_pre,
                    "static_only": True,
                    "production_enabled": False,
                }
                try:
                    commit_response = _call_external(
                        authority_callback,
                        commit_request,
                        authority_public_key=self._authority_public_key,
                        authority_verification_key_sha256=(
                            self._authority_verification_key_sha256
                        ),
                        expected_schema=(
                            "kira.shared_person_growth.external_commit_response.v2"
                        ),
                        response_keys={
                            "schema",
                            "authority_binding",
                            "commit_receipt",
                            "static_only",
                            "production_enabled",
                        },
                        field="external final commit response",
                    )
                except BaseException as commit_call_exc:
                    query_request = {
                        "schema": (
                            "kira.shared_person_growth.external_commit_status_request.v2"
                        ),
                        "action": "QUERY_STATIC_COMMIT_STATUS",
                        "operation_id": f"commit_status:{operation_id}",
                        "stage_ticket": stage_ticket,
                        "attachment_sha256": attachment["attachment_sha256"],
                        "output_name": output.name,
                        "output_sha256": _sha_bytes(encoded),
                        "commit_source_gate_snapshot": commit_pre,
                        "static_only": True,
                        "production_enabled": False,
                    }
                    try:
                        query_response = _call_external(
                            authority_callback,
                            query_request,
                            authority_public_key=self._authority_public_key,
                            authority_verification_key_sha256=(
                                self._authority_verification_key_sha256
                            ),
                            expected_schema=(
                                "kira.shared_person_growth."
                                "external_commit_status_response.v2"
                            ),
                            response_keys={
                                "schema",
                                "authority_binding",
                                "commit_state",
                                "commit_receipt",
                                "static_only",
                                "production_enabled",
                            },
                            field="external commit status recovery response",
                        )
                    except BaseException as query_exc:
                        raise GrowthIntegrationV2RecoveryRequired(
                            "external commit outcome is indeterminate"
                        ) from query_exc
                    if _validate_authority_binding(
                        query_response["authority_binding"],
                        expected_verification_key_sha256=(
                            self._authority_verification_key_sha256
                        ),
                    ) != authority_binding:
                        raise GrowthIntegrationV2RecoveryRequired(
                            "commit status authority cross-binding"
                        )
                    if query_response["commit_state"] == "COMMITTED":
                        if type(query_response["commit_receipt"]) is not dict:
                            raise GrowthIntegrationV2RecoveryRequired(
                                "committed status omitted exact receipt"
                            )
                        commit_response = {
                            "authority_binding": query_response["authority_binding"],
                            "commit_receipt": query_response["commit_receipt"],
                        }
                    elif query_response["commit_state"] == "NOT_COMMITTED":
                        if query_response["commit_receipt"] is not None:
                            raise GrowthIntegrationV2RecoveryRequired(
                                "not-committed status included a receipt"
                            )
                        raise commit_call_exc
                    else:
                        raise GrowthIntegrationV2RecoveryRequired(
                            "external commit status was not closed"
                        )
                if _validate_authority_binding(
                    commit_response["authority_binding"],
                    expected_verification_key_sha256=(
                        self._authority_verification_key_sha256
                    ),
                ) != authority_binding:
                    raise GrowthIntegrationV2AuthorityError("commit authority cross-binding")
                commit_receipt = _validate_ticket(
                    commit_response["commit_receipt"],
                    schema="kira.shared_person_growth.commit_receipt.v2",
                    kind="COMMIT",
                    authority_binding=authority_binding,
                    inventory_sha256=self._inventory_sha256,
                    attachment_sha256=attachment["attachment_sha256"],
                    prior_sha256=stage_ticket["ticket_sha256"],
                )
                if (
                    commit_receipt["source_gate_snapshot_sha256"]
                    != commit_pre["snapshot_sha256"]
                    or commit_receipt["output_sha256"] != _sha_bytes(encoded)
                ):
                    raise GrowthIntegrationV2AuthorityError(
                        "commit receipt source/output binding changed"
                    )
                _route, commit_post = self._fresh_route(route_id, "FINAL_COMMIT_POST_AUTHORITY")
                self._same_source(commit_pre, commit_post, "final commit callback")
                if output.read_bytes() != encoded:
                    raise GrowthIntegrationV2Error("post-commit output readback changed")

                _route, readback_pre = self._fresh_route(route_id, "FINAL_READBACK_PRE_AUTHORITY")
                self._same_source(commit_post, readback_pre, "commit to final readback")
                readback_request = {
                    "schema": "kira.shared_person_growth.external_readback_request.v2",
                    "action": "FINALIZE_STATIC_READBACK",
                    "operation_id": f"readback:{operation_id}",
                    "commit_receipt": commit_receipt,
                    "attachment_sha256": attachment["attachment_sha256"],
                    "output_name": output.name,
                    "output_sha256": _sha_bytes(output.read_bytes()),
                    "readback_source_gate_snapshot": readback_pre,
                    "static_only": True,
                    "production_enabled": False,
                }
                readback_response = _call_external(
                    authority_callback,
                    readback_request,
                    authority_public_key=self._authority_public_key,
                    authority_verification_key_sha256=(
                        self._authority_verification_key_sha256
                    ),
                    expected_schema="kira.shared_person_growth.external_readback_response.v2",
                    response_keys={
                        "schema",
                        "authority_binding",
                        "final_receipt",
                        "static_only",
                        "production_enabled",
                    },
                    field="external final readback response",
                )
                if _validate_authority_binding(
                    readback_response["authority_binding"],
                    expected_verification_key_sha256=(
                        self._authority_verification_key_sha256
                    ),
                ) != authority_binding:
                    raise GrowthIntegrationV2AuthorityError("readback authority cross-binding")
                final_receipt = _validate_ticket(
                    readback_response["final_receipt"],
                    schema="kira.shared_person_growth.final_readback_receipt.v2",
                    kind="FINAL_READBACK",
                    authority_binding=authority_binding,
                    inventory_sha256=self._inventory_sha256,
                    attachment_sha256=attachment["attachment_sha256"],
                    prior_sha256=commit_receipt["ticket_sha256"],
                )
                if (
                    final_receipt["source_gate_snapshot_sha256"]
                    != readback_pre["snapshot_sha256"]
                    or final_receipt["output_sha256"] != _sha_bytes(encoded)
                ):
                    raise GrowthIntegrationV2AuthorityError(
                        "final readback receipt source/output binding changed"
                    )
                _route, readback_post = self._fresh_route(
                    route_id, "FINAL_READBACK_POST_AUTHORITY"
                )
                self._same_source(readback_pre, readback_post, "final readback callback")
                if output.read_bytes() != encoded:
                    raise GrowthIntegrationV2Error("final output readback changed")
            except BaseException as exc:
                cleanup_exc: BaseException | None = None
                if created and output.exists():
                    if output.is_symlink():
                        cleanup_exc = GrowthIntegrationV2RecoveryRequired(
                            "staged output became a symlink during cleanup"
                        )
                    else:
                        try:
                            output.unlink()
                        except BaseException as unlink_exc:
                            cleanup_exc = unlink_exc
                output_absent = not output.exists() and not output.is_symlink()
                if commit_receipt is not None:
                    rollback_request = {
                        "schema": "kira.shared_person_growth.external_rollback_request.v2",
                        "action": "ROLLBACK_FAILED_STATIC_STAGE",
                        "operation_id": f"rollback:{operation_id}",
                        "commit_receipt": commit_receipt,
                        "output_name": output.name,
                        "output_absent": output_absent,
                        "static_only": True,
                        "production_enabled": False,
                    }
                    try:
                        rollback = _call_external(
                            authority_callback,
                            rollback_request,
                            authority_public_key=self._authority_public_key,
                            authority_verification_key_sha256=(
                                self._authority_verification_key_sha256
                            ),
                            expected_schema="kira.shared_person_growth.external_rollback_response.v2",
                            response_keys={
                                "schema",
                                "authority_binding",
                                "rollback_confirmed",
                                "output_absent",
                                "production_pointer_changed",
                                "static_only",
                                "production_enabled",
                            },
                            field="external rollback response",
                        )
                        if (
                            _validate_authority_binding(
                                rollback["authority_binding"],
                                expected_verification_key_sha256=(
                                    self._authority_verification_key_sha256
                                ),
                            )
                            != authority_binding
                            or rollback["rollback_confirmed"] is not True
                            or rollback["output_absent"] is not True
                            or rollback["production_pointer_changed"] is not False
                            or output.exists()
                            or output.is_symlink()
                        ):
                            raise GrowthIntegrationV2RecoveryRequired(
                                "external rollback truth changed"
                            )
                    except BaseException as rollback_exc:
                        raise GrowthIntegrationV2RecoveryRequired(
                            "stage failed after commit and external rollback was not proven"
                        ) from rollback_exc
                if cleanup_exc is not None or output.exists() or output.is_symlink():
                    raise GrowthIntegrationV2RecoveryRequired(
                        "exact staged output cleanup could not be proven"
                    ) from cleanup_exc
                raise exc
            return output

    def public_state(self) -> dict[str, Any]:
        return {
            "schema": "kira.shared_person_growth_v3_integration_adapter_state.v2",
            "status": "DISCONNECTED_STATIC_EXTERNAL_AUTHORITY_PROTOCOL_ONLY",
            "inventory_sha256": self._inventory_sha256,
            "authority_callback_retained": False,
            "authority_secret_retained": False,
            "authority_private_signing_key_retained": False,
            "authority_public_verification_key_retained": True,
            "authority_verification_key_sha256": (
                self._authority_verification_key_sha256
            ),
            "signed_response_and_fresh_challenge_required": True,
            "controller_retained": False,
            "controller_identity_retained": False,
            "adapter_identity_capability_present": False,
            "production_pointer_changed": False,
            "live_enabled": False,
        }


def open_production_shared_growth_v3_integration_v2(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise GrowthIntegrationV2AuthorityError(
        "Shared Growth V3 integration V2 production opener is disconnected; "
        "no protected external issuance authority integration exists"
    )


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.shared_person_growth_v3_integration_static_summary.v2",
        "status": "STATIC_SUCCESSOR_PENDING_DIFFERENT_FRESH_AUDIT",
        "v1_rejection_preserved": True,
        "adapter_retains_authority_or_secret": False,
        "adapter_retains_public_verifier_only": True,
        "ed25519_signed_response_required": True,
        "fresh_per_call_challenge_and_request_binding_required": True,
        "external_callback_supplied_per_operation": True,
        "external_callback_is_os_trust_root_claimed": False,
        "route_source_rehashed_at_issue": True,
        "route_source_rehashed_at_stage": True,
        "route_source_rehashed_at_final_commit": True,
        "route_source_rehashed_at_final_readback": True,
        "production_opener_disconnected": True,
        "production_pointer_changed": False,
        "live_enabled": False,
    }


__all__ = [
    "ExternalGrowthIntegrationAuthorityV2",
    "GrowthIntegrationV2AuthorityError",
    "GrowthIntegrationV2Error",
    "GrowthIntegrationV2RecoveryRequired",
    "SharedGrowthV3ExternalAuthorityAdapterV2",
    "open_production_shared_growth_v3_integration_v2",
    "static_contract_summary",
]
