"""Resident-media V13 exact-type and completion precommit repair.

V12 remains frozen and independently rejected.  This append-only successor
keeps its catalog, owner-selection snapshot, external-authority receipt,
global receipt-ledger, and disconnected production boundaries.  V13 adds a
closed precommit layer that rejects scalar coercion at every identifier and
SHA-256 field and requires complete independent coverage for every exact
authoritative media role before V12 can consume output/decoder identities or
perform an anchor compare-and-swap.

The external interface exercised here is still only a static contract.  An
in-process test double is not an operating-system trust root.  The production
opener remains unconditionally disconnected and this module opens, decodes,
renders, plays, or presents no media.  It calls no model or device and creates
no seeing, hearing, enjoyment, learning, preference, or memory claim.
"""

from __future__ import annotations

import copy
import re
import threading
from collections.abc import Mapping
from typing import Any

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v12 as v12


class ResidentMediaV13Error(v12.ResidentMediaV12Error):
    """Raised when the disconnected V13 static contract fails closed."""


ProtectedExternalResidentMediaAuthorityV13 = (
    v12.ProtectedExternalResidentMediaAuthorityV12
)


_EXACT_TEXT_FIELDS = frozenset(
    {
        "schema",
        "status",
        "interface_mode",
        "purpose",
        "verifier_boundary",
        "media_kind",
        "source_relative_path",
        "relative_path",
        "derivative_role",
        "role",
        "presented_at_utc",
    }
)

_IDENTIFIER_LIST_FIELDS = frozenset(
    {
        "used_output_receipt_ids",
        "required_roles",
    }
)

_NULLABLE_SHA_FIELDS = frozenset(
    {
        "anchor_sha256",
        "expected_previous_anchor_sha256",
    }
)

_DECODER_SHA_FIELDS = frozenset(
    {
        "renderer_or_decoder_receipt_sha256",
        "renderer_or_decoder_receipt_sha256s",
        "used_renderer_or_decoder_receipt_sha256s",
    }
)


def _canonical_mapping_copy(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ResidentMediaV13Error(f"{label} must be an object")
    try:
        encoded = v4.canonical_json_bytes(dict(value))
        clean = v4.strict_json_loads(encoded)
    except Exception as exc:
        raise ResidentMediaV13Error(f"{label} is not strict canonical JSON") from exc
    if type(clean) is not dict:
        raise ResidentMediaV13Error(f"{label} must decode to an exact object")
    return clean


def _exact_identifier(value: Any, field: str) -> str:
    if type(value) is not str:
        raise ResidentMediaV13Error(f"{field} must be an exact string identifier")
    try:
        clean = v12._nonzero_identifier(value, field)
    except Exception as exc:
        raise ResidentMediaV13Error(str(exc)) from exc
    if clean != value:
        raise ResidentMediaV13Error(f"{field} must be an exact canonical identifier")
    return value


def _exact_sha256(
    value: Any,
    field: str,
    *,
    nullable: bool = False,
    reject_decimal_only: bool = False,
) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str:
        raise ResidentMediaV13Error(f"{field} must be an exact SHA-256 string")
    try:
        clean = v12._nonzero_sha(value, field)
    except Exception as exc:
        raise ResidentMediaV13Error(str(exc)) from exc
    if clean != value or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ResidentMediaV13Error(f"{field} must be exact lowercase SHA-256")
    if reject_decimal_only and value.isdecimal():
        raise ResidentMediaV13Error(
            f"{field} cannot be a numeric-only decoder digest"
        )
    return value


def _exact_sha_collection(value: Any, field: str, *, decoder: bool) -> None:
    if type(value) is not list:
        raise ResidentMediaV13Error(f"{field} must be an exact SHA-256 list")
    for index, item in enumerate(value):
        item_field = f"{field}[{index}]"
        if type(item) is list:
            _exact_sha_collection(item, item_field, decoder=decoder)
        else:
            _exact_sha256(
                item,
                item_field,
                reject_decimal_only=decoder,
            )


def _require_exact_string_types(value: Any, label: str) -> None:
    """Reject every identifier/digest coercion before inherited validation.

    This walk covers descriptor, snapshot/catalog, authority receipt,
    verification, anchor/history, record, evidence, and segment objects.  It
    intentionally validates by field semantics rather than by the current
    nesting location so a later nested occurrence cannot silently fall back to
    V8's historical ``str(value)`` behavior.
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise ResidentMediaV13Error(
                    f"{label} contains a non-string object key"
                )
            field = f"{label}.{key}"
            if key in _IDENTIFIER_LIST_FIELDS or key.endswith("_ids"):
                if type(item) is not list:
                    raise ResidentMediaV13Error(
                        f"{field} must be an exact identifier list"
                    )
                for index, identifier in enumerate(item):
                    _exact_identifier(identifier, f"{field}[{index}]")
            elif key.endswith("_id"):
                _exact_identifier(item, field)
            elif key.endswith("_sha256s"):
                _exact_sha_collection(
                    item,
                    field,
                    decoder=key in _DECODER_SHA_FIELDS,
                )
            elif key == "sha256" or key.endswith("_sha256"):
                _exact_sha256(
                    item,
                    field,
                    nullable=key in _NULLABLE_SHA_FIELDS,
                    reject_decimal_only=key in _DECODER_SHA_FIELDS,
                )
            elif key in _EXACT_TEXT_FIELDS:
                if type(item) is not str:
                    raise ResidentMediaV13Error(
                        f"{field} must be an exact string"
                    )
            else:
                _require_exact_string_types(item, field)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_exact_string_types(item, f"{label}[{index}]")
        return
    if isinstance(value, tuple):
        raise ResidentMediaV13Error(f"{label} must use canonical JSON arrays")


def _decode_checked_bytes(value: Any, label: str) -> bytes:
    try:
        clean = v12._decode_canonical_object(value, label)
    except Exception as exc:
        raise ResidentMediaV13Error(str(exc)) from exc
    _require_exact_string_types(clean, label)
    return value


class _ExactTypeAuthorityProxyV13:
    """Preserve the frozen V12 byte protocol while rejecting scalar aliases."""

    def __init__(self, authority: ProtectedExternalResidentMediaAuthorityV13) -> None:
        self._authority = authority

    def describe_contract_v12(self) -> bytes:
        try:
            value = self._authority.describe_contract_v12()
        except Exception as exc:
            raise ResidentMediaV13Error("external authority descriptor failed") from exc
        return _decode_checked_bytes(value, "V13 external authority descriptor")

    def read_owner_selected_snapshot_v12(self, request_bytes: bytes) -> bytes:
        _decode_checked_bytes(request_bytes, "V13 snapshot request")
        try:
            value = self._authority.read_owner_selected_snapshot_v12(request_bytes)
        except Exception as exc:
            raise ResidentMediaV13Error("external snapshot read failed") from exc
        return _decode_checked_bytes(value, "V13 snapshot response")

    def read_global_anchor_v12(self, request_bytes: bytes) -> bytes:
        _decode_checked_bytes(request_bytes, "V13 anchor read request")
        try:
            value = self._authority.read_global_anchor_v12(request_bytes)
        except Exception as exc:
            raise ResidentMediaV13Error("external anchor read failed") from exc
        return _decode_checked_bytes(value, "V13 anchor read response")

    def compare_and_swap_global_anchor_v12(self, request_bytes: bytes) -> bytes:
        _decode_checked_bytes(request_bytes, "V13 anchor CAS request")
        try:
            value = self._authority.compare_and_swap_global_anchor_v12(request_bytes)
        except Exception as exc:
            raise ResidentMediaV13Error("external anchor CAS failed") from exc
        return _decode_checked_bytes(value, "V13 anchor CAS response")

    def consume_and_verify_receipt_v12(
        self,
        receipt_bytes: bytes,
        expected_context_sha256: str,
    ) -> bytes:
        _decode_checked_bytes(receipt_bytes, "V13 authority receipt")
        _exact_sha256(expected_context_sha256, "V13 expected receipt context")
        try:
            value = self._authority.consume_and_verify_receipt_v12(
                receipt_bytes,
                expected_context_sha256,
            )
        except Exception as exc:
            raise ResidentMediaV13Error("external receipt verification failed") from exc
        return _decode_checked_bytes(value, "V13 receipt verification")


def _preflight_complete_evidence(
    value: Mapping[str, Any],
    *,
    session_id: str,
    person_id: str,
    expected_manifest: Mapping[str, Any],
    consumed_start_permit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    frozen_value = _canonical_mapping_copy(value, "V13 presentation evidence")
    frozen_manifest = _canonical_mapping_copy(
        expected_manifest,
        "V13 expected authoritative manifest",
    )
    _require_exact_string_types(frozen_value, "V13 presentation evidence")
    _require_exact_string_types(frozen_manifest, "V13 expected authoritative manifest")
    session = _exact_identifier(session_id, "V13 session id")
    person = _exact_identifier(person_id, "V13 person id")
    permit = _exact_sha256(
        consumed_start_permit_sha256,
        "V13 consumed start permit",
    )
    assert isinstance(permit, str)
    try:
        clean = v9.validate_presentation_evidence_v9(
            frozen_value,
            session_id=session,
            person_id=person,
            expected_manifest=frozen_manifest,
            consumed_start_permit_sha256=permit,
        )
        required_roles = tuple(v9._required_roles(frozen_manifest))
    except Exception as exc:
        raise ResidentMediaV13Error(str(exc)) from exc
    _require_exact_string_types(clean, "V13 validated presentation evidence")
    if clean.get("engineering_output_completed") is not True:
        raise ResidentMediaV13Error(
            "V13 refuses incomplete engineering output before receipt consumption"
        )
    if clean.get("presentation_complete_for_manifest") is not True:
        raise ResidentMediaV13Error(
            "V13 refuses incomplete manifest presentation before receipt consumption"
        )
    supplied_roles = clean.get("required_roles")
    if type(supplied_roles) is not list or supplied_roles != list(required_roles):
        raise ResidentMediaV13Error(
            "V13 authoritative required media-role set changed"
        )
    completeness = clean.get("complete_by_required_role")
    if type(completeness) is not dict or set(completeness) != set(required_roles):
        raise ResidentMediaV13Error(
            "V13 authoritative required media-role coverage is incomplete"
        )
    if any(completeness[role] is not True for role in required_roles):
        raise ResidentMediaV13Error(
            "V13 requires every authoritative media role complete before commit"
        )
    return frozen_value, frozen_manifest


class _DisconnectedStaticReceiptLedgerV13:
    """Default-off V13 wrapper around the exact frozen V12 ledger contract."""

    def __init__(
        self,
        *,
        person_id: str,
        external_authority: ProtectedExternalResidentMediaAuthorityV13,
    ) -> None:
        self.person_id = _exact_identifier(person_id, "V13 person id")
        self._lock = threading.RLock()
        self._authority_proxy = _ExactTypeAuthorityProxyV13(external_authority)
        try:
            self._inner = v12._DisconnectedStaticReceiptLedgerV12(
                person_id=self.person_id,
                external_authority=self._authority_proxy,
            )
        except Exception as exc:
            raise ResidentMediaV13Error(str(exc)) from exc

    def validate_and_record_static_evidence(
        self,
        value: Mapping[str, Any],
        *,
        session_id: str,
        expected_manifest: Mapping[str, Any],
        consumed_start_permit_sha256: str,
    ) -> dict[str, Any]:
        """Commit only complete exact-role static evidence; present no media."""

        with self._lock:
            frozen_value, frozen_manifest = _preflight_complete_evidence(
                value,
                session_id=session_id,
                person_id=self.person_id,
                expected_manifest=expected_manifest,
                consumed_start_permit_sha256=consumed_start_permit_sha256,
            )
            ordinal = frozen_value.get("ordinal")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                raise ResidentMediaV13Error("V13 presentation ordinal is invalid")
            try:
                authoritative_manifest = self._inner._catalog.manifest(ordinal)
            except Exception as exc:
                raise ResidentMediaV13Error("V13 authoritative manifest is missing") from exc
            if frozen_manifest != authoritative_manifest:
                raise ResidentMediaV13Error(
                    "V13 expected manifest is not the exact authoritative selection"
                )
            try:
                clean = self._inner.validate_and_record_static_evidence(
                    frozen_value,
                    session_id=_exact_identifier(session_id, "V13 session id"),
                    expected_manifest=frozen_manifest,
                    consumed_start_permit_sha256=_exact_sha256(
                        consumed_start_permit_sha256,
                        "V13 consumed start permit",
                    ),
                )
            except Exception as exc:
                raise ResidentMediaV13Error(str(exc)) from exc
            _require_exact_string_types(clean, "V13 committed presentation evidence")
            return copy.deepcopy(clean)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            try:
                clean = self._inner.snapshot()
            except Exception as exc:
                raise ResidentMediaV13Error(str(exc)) from exc
            clean["schema"] = "kira.resident_media_static_contract_snapshot.v13"
            clean["status"] = (
                "DISCONNECTED_STATIC_V13_EXACT_COMPLETE_CONTRACT_ONLY"
            )
            clean["exact_string_types_required_before_commit"] = True
            clean["all_authoritative_required_roles_complete_before_commit"] = True
            return clean


def _open_disconnected_static_contract_harness_v13(
    *,
    person_id: str,
    external_authority: ProtectedExternalResidentMediaAuthorityV13,
) -> _DisconnectedStaticReceiptLedgerV13:
    """Open only the disconnected static V13 contract harness."""

    return _DisconnectedStaticReceiptLedgerV13(
        person_id=person_id,
        external_authority=external_authority,
    )


def open_production_resident_media_v13(*args: Any, **kwargs: Any) -> None:
    """Fail closed: no protected external production integration exists."""

    del args, kwargs
    raise ResidentMediaV13Error(
        "V13 production resident-media opener is disconnected; no separately "
        "reviewed protected external authority integration exists"
    )


def production_connection_status_v13() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_production_connection_status.v13",
        "status": "DISCONNECTED_FAIL_CLOSED",
        "protected_external_authority_implementation_present": False,
        "production_opener_accepts_caller_authority": False,
        "production_opener_accepts_caller_catalog": False,
        "module_resident_issuer_secret_present": False,
        "module_global_owner_catalog_trusted": False,
        "python_process_is_trust_root": False,
        "live_execution_allowed": False,
    }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_static_summary.v13",
        "status": "SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        "v12_rejection_preserved": True,
        "caller_catalog_accepted": False,
        "external_authority_contract_retained": True,
        "owner_selection_catalog_and_receipt_binding_retained": True,
        "global_cross_session_output_and_decoder_receipt_one_use_retained": True,
        "consent_privacy_and_choice_predecessor_gates_retained": True,
        "identifier_and_sha256_exact_string_types_required": True,
        "numeric_only_decoder_sha256_refused": True,
        "all_authoritative_required_roles_complete_before_commit": True,
        "public_production_opener_disconnected": True,
        "static_test_double_is_production_authority": False,
        "python_process_is_trust_root": False,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_learned_or_remembered_claimed": False,
    }


__all__ = [
    "ProtectedExternalResidentMediaAuthorityV13",
    "ResidentMediaV13Error",
    "open_production_resident_media_v13",
    "production_connection_status_v13",
    "static_contract_summary",
]
