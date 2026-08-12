"""Append-only resident-media v11 controller authority/history repair.

The different fresh V10 audit rejected its caller-supplied authority boundary
and its underdetermined durable history.  V11 is a disconnected static
successor.  It accepts only an exact controller-issued capability instance,
binds the one sealed owner-selected catalog (including every derivative and
source-time identity) in an authenticated authorization, and commits complete
canonical V9 presentation evidence into a controller-MACed record chain.

This module contains a process-local static authority solely so the boundary
can be tested.  It is not an operating-system trust root and authorizes no live
media, model, device, person, memory, preference, body, or Blender activity.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import re
import secrets
import threading
from collections.abc import Mapping
from typing import Any, Final

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v10 as v10


MAX_GLOBAL_RECEIPTS: Final = 4096
MAX_GLOBAL_RECORDS: Final = 1024
OWNER_SELECTED_CATALOG_SHA256_V11: Final = (
    "009188de84a41dd7178e610eb55ccf84c384f251433dc933137830e103fa867e"
)
OWNER_SELECTION_RECEIPT_SHA256_V11: Final = hashlib.sha256(
    b"kira.resident_media.owner_selected_catalog.v11:"
    + OWNER_SELECTED_CATALOG_SHA256_V11.encode("ascii")
).hexdigest()
GENESIS_RECORD_SHA256_V11: Final = hashlib.sha256(
    b"kira.resident_media.presentation_record.genesis.v11"
).hexdigest()
GENESIS_ANCHOR_SHA256_V11: Final = hashlib.sha256(
    b"kira.resident_media.global_anchor.genesis.v11"
).hexdigest()
_CONTROLLER_ISSUER_KEY = secrets.token_bytes(32)
_CONTROLLER_ISSUER_TOKEN = object()
_ZERO_IDENTIFIER = re.compile(r"0+")


class ResidentMediaV11Error(v10.ResidentMediaV10Error):
    """Raised when V11 controller authority or chained history is not exact."""


def _canonical_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return v4.strict_json_loads(v4.canonical_json_bytes(dict(value)))


def _record_sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(v4.canonical_json_bytes(dict(value))).hexdigest()


def _nonzero_identifier(value: Any, field: str) -> str:
    text = v8._identifier(value, field)
    compact_zero = re.sub(r"[-{}]", "", text)
    if (
        _ZERO_IDENTIFIER.fullmatch(text)
        or _ZERO_IDENTIFIER.fullmatch(compact_zero)
        or text.casefold() in {"nil", "null", "none"}
    ):
        raise ResidentMediaV11Error(f"{field} cannot be a zero sentinel")
    return text


def _nonzero_sha(value: Any, field: str) -> str:
    digest = v8._sha(value, field)
    if digest == "0" * 64:
        raise ResidentMediaV11Error(f"{field} cannot be the zero digest")
    return digest


def _catalog_bindings(catalog: v4.StimulusCatalog) -> dict[str, Any]:
    if not isinstance(catalog, v4.StimulusCatalog):
        raise ResidentMediaV11Error("catalog must be a validated v4 catalog")
    if catalog.sha256 != OWNER_SELECTED_CATALOG_SHA256_V11:
        raise ResidentMediaV11Error("catalog is not the exact owner-selected V11 catalog")
    if v5.validate_authoritative_catalog(catalog) != OWNER_SELECTED_CATALOG_SHA256_V11:
        raise ResidentMediaV11Error("catalog source identity is not authoritative")
    record = catalog.as_record()
    if _record_sha(record) != OWNER_SELECTED_CATALOG_SHA256_V11:
        raise ResidentMediaV11Error("catalog canonical record changed")

    manifest_sha256s: list[str] = []
    source_time_sha256s: list[str] = []
    derivative_set_sha256s: list[str] = []
    derivative_identity_sha256s: list[list[str]] = []
    for ordinal in range(len(v4.STIMULUS_ORDER)):
        manifest = catalog.manifest(ordinal)
        manifest_sha256s.append(catalog.manifest_sha256(ordinal))
        source_time_sha256s.append(
            _record_sha(
                {
                    "stimulus_id": manifest["stimulus_id"],
                    "opaque_media_id": manifest["opaque_media_id"],
                    "media_kind": manifest["media_kind"],
                    "source_relative_path": manifest["source_relative_path"],
                    "source_byte_count": manifest["source_byte_count"],
                    "source_sha256": manifest["source_sha256"],
                    "coordinates": manifest["coordinates"],
                }
            )
        )
        derivatives = manifest["derivatives"]
        derivative_set_sha256s.append(
            hashlib.sha256(v4.canonical_json_bytes(derivatives)).hexdigest()
        )
        derivative_identity_sha256s.append(
            [_record_sha(derivative) for derivative in derivatives]
        )
    return {
        "catalog_record": _canonical_copy(record),
        "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
        "manifest_sha256s": manifest_sha256s,
        "source_time_identity_sha256s": source_time_sha256s,
        "derivative_set_sha256s": derivative_set_sha256s,
        "derivative_identity_sha256s": derivative_identity_sha256s,
    }


def _raw_v9_evidence(clean: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(clean, Mapping) or not set(v9._EVIDENCE_KEYS).issubset(clean):
        raise ResidentMediaV11Error("complete canonical presentation evidence is missing")
    return {key: copy.deepcopy(clean[key]) for key in v9._EVIDENCE_KEYS}


class ControllerProtectedAuthorityCapabilityV11(v8.ProtectedMonotonicAuthorityV8):
    """Exact controller-issued, process-local static authority capability.

    Construction is reserved to :func:`issue_controller_owned_static_authority_v11`.
    Subclass/equality substitution is prohibited and the authority, rather than
    its caller, signs authorizations, records, anchors, and CAS receipts.
    """

    __slots__ = (
        "_authorization",
        "_capability_id",
        "_catalog",
        "_identity",
        "_issuer_seal",
        "_key",
        "_lock",
        "_monotonic_floor",
        "_records",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("V11 controller authority capability cannot be subclassed")

    def __init__(
        self,
        issuer_token: object,
        catalog: v4.StimulusCatalog,
    ) -> None:
        if issuer_token is not _CONTROLLER_ISSUER_TOKEN:
            raise ResidentMediaV11Error("controller authority was not issued by V11")
        bindings = _catalog_bindings(catalog)
        self._key = secrets.token_bytes(32)
        self._identity = hashlib.sha256(
            b"kira.resident_media.controller_backend.v11:" + self._key
        ).hexdigest()
        self._capability_id = hashlib.sha256(
            b"kira.resident_media.controller_capability.v11:" + self._key
        ).hexdigest()
        self._catalog = v4.StimulusCatalog(
            bindings["catalog_record"]["manifests"]
        )
        authorization_core = {
            "schema": "kira.resident_media_catalog_authorization.v11",
            "status": "AUTHORIZED_FOR_DISCONNECTED_STATIC_GATE_ONLY",
            "owner_selection_receipt_sha256": OWNER_SELECTION_RECEIPT_SHA256_V11,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "protected_backend_identity_sha256": self._identity,
            "controller_capability_id": self._capability_id,
            **bindings,
        }
        self._authorization = dict(authorization_core)
        self._authorization["controller_authorization_mac_sha256"] = self._mac(
            "catalog_authorization", authorization_core
        )
        issuer_payload = {
            "schema": "kira.resident_media.controller_capability_issue.v11",
            "protected_backend_identity_sha256": self._identity,
            "controller_capability_id": self._capability_id,
            "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
        }
        self._issuer_seal = hmac.new(
            _CONTROLLER_ISSUER_KEY,
            v4.canonical_json_bytes(issuer_payload),
            hashlib.sha256,
        ).hexdigest()
        self._records: dict[tuple[str, str], dict[str, Any]] = {}
        self._monotonic_floor: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.RLock()

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    @property
    def controller_capability_id(self) -> str:
        return self._capability_id

    def _mac(self, label: str, value: Mapping[str, Any]) -> str:
        return hmac.new(
            self._key,
            label.encode("ascii") + b"\x00" + v4.canonical_json_bytes(dict(value)),
            hashlib.sha256,
        ).hexdigest()

    def _assert_controller_issued(self) -> None:
        payload = {
            "schema": "kira.resident_media.controller_capability_issue.v11",
            "protected_backend_identity_sha256": self._identity,
            "controller_capability_id": self._capability_id,
            "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
        }
        expected = hmac.new(
            _CONTROLLER_ISSUER_KEY,
            v4.canonical_json_bytes(payload),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(self._issuer_seal, expected):
            raise ResidentMediaV11Error("controller authority issuer seal changed")
        self._verify_catalog_authorization(self._authorization)

    def _verify_catalog_authorization(self, value: Mapping[str, Any]) -> None:
        expected_keys = {
            "schema",
            "status",
            "owner_selection_receipt_sha256",
            "authoritative_source_policy_sha256",
            "protected_backend_identity_sha256",
            "controller_capability_id",
            "catalog_record",
            "catalog_sha256",
            "manifest_sha256s",
            "source_time_identity_sha256s",
            "derivative_set_sha256s",
            "derivative_identity_sha256s",
            "controller_authorization_mac_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected_keys:
            raise ResidentMediaV11Error("controller catalog authorization shape changed")
        supplied = _canonical_copy(value)
        mac = supplied.pop("controller_authorization_mac_sha256")
        if not hmac.compare_digest(
            _nonzero_sha(mac, "controller authorization MAC"),
            self._mac("catalog_authorization", supplied),
        ):
            raise ResidentMediaV11Error("controller catalog authorization MAC changed")
        bindings = _catalog_bindings(
            v4.StimulusCatalog(supplied["catalog_record"]["manifests"])
        )
        expected = {
            "schema": "kira.resident_media_catalog_authorization.v11",
            "status": "AUTHORIZED_FOR_DISCONNECTED_STATIC_GATE_ONLY",
            "owner_selection_receipt_sha256": OWNER_SELECTION_RECEIPT_SHA256_V11,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "protected_backend_identity_sha256": self._identity,
            "controller_capability_id": self._capability_id,
            **bindings,
        }
        if supplied != expected:
            raise ResidentMediaV11Error("controller catalog authorization binding changed")

    def read_catalog_authorization_v11(
        self, catalog_sha256: str
    ) -> Mapping[str, Any] | None:
        self._assert_controller_issued()
        if _nonzero_sha(catalog_sha256, "catalog digest") != OWNER_SELECTED_CATALOG_SHA256_V11:
            return None
        return copy.deepcopy(self._authorization)

    def _verify_record_mac(self, record: Mapping[str, Any]) -> None:
        if "controller_record_mac_sha256" not in record:
            raise ResidentMediaV11Error("presentation record controller MAC is missing")
        core = _canonical_copy(record)
        mac = core.pop("controller_record_mac_sha256")
        if not hmac.compare_digest(
            _nonzero_sha(mac, "presentation record controller MAC"),
            self._mac("presentation_record", core),
        ):
            raise ResidentMediaV11Error("presentation record controller MAC changed")

    def _verify_anchor_mac(self, anchor: Mapping[str, Any]) -> None:
        if "controller_anchor_mac_sha256" not in anchor:
            raise ResidentMediaV11Error("global anchor controller MAC is missing")
        core = _canonical_copy(anchor)
        mac = core.pop("controller_anchor_mac_sha256")
        if not hmac.compare_digest(
            _nonzero_sha(mac, "global anchor controller MAC"),
            self._mac("global_anchor", core),
        ):
            raise ResidentMediaV11Error("global anchor controller MAC changed")

    def _verify_signed_anchor(self, value: Mapping[str, Any]) -> dict[str, Any]:
        self._verify_anchor_mac(value)
        clean = _canonical_copy(value)
        _validate_anchor_payload_v11(
            clean,
            catalog=self._catalog,
            authorization=self._authorization,
            backend_identity_sha256=self._identity,
            controller_capability_id=self._capability_id,
            require_controller_macs=True,
            verify_record_mac=self._verify_record_mac,
        )
        return clean

    def read_record(self, namespace: str, record_key: str) -> Mapping[str, Any] | None:
        if namespace != "global_receipts_v11":
            raise ResidentMediaV11Error("protected namespace is not allowed")
        key = _nonzero_identifier(record_key, "record key")
        with self._lock:
            self._assert_controller_issued()
            stored = self._records.get((namespace, key))
            if stored is None:
                return None
            clean = self._verify_signed_anchor(stored)
            floor = self._monotonic_floor.get((namespace, key))
            expected_floor = {
                "revision": clean["revision"],
                "generation": clean["generation"],
                "chain_head_sha256": clean["chain_head_sha256"],
                "signed_anchor_sha256": _record_sha(clean),
            }
            if floor != expected_floor:
                raise ResidentMediaV11Error("controller monotonic floor detected rollback")
            return copy.deepcopy(clean)

    def compare_and_swap_record(
        self,
        *,
        namespace: str,
        record_key: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if namespace != "global_receipts_v11":
            raise ResidentMediaV11Error("protected namespace is not allowed")
        key = _nonzero_identifier(record_key, "record key")
        if not isinstance(replacement, Mapping):
            raise ResidentMediaV11Error("protected replacement must be an object")
        with self._lock:
            self._assert_controller_issued()
            current_value = self._records.get((namespace, key))
            current = (
                self._verify_signed_anchor(current_value)
                if current_value is not None
                else None
            )
            if current is not None:
                floor = self._monotonic_floor.get((namespace, key))
                if floor is None or floor.get("signed_anchor_sha256") != _record_sha(current):
                    raise ResidentMediaV11Error("controller monotonic floor changed")
            current_sha = _record_sha(current) if current is not None else None
            if expected_record_sha256 is not None:
                expected_record_sha256 = _nonzero_sha(
                    expected_record_sha256, "expected protected record"
                )
            if current_sha != expected_record_sha256:
                raise ResidentMediaV11Error("protected V11 compare-and-swap mismatch")

            unsigned = _canonical_copy(replacement)
            if "controller_anchor_mac_sha256" in unsigned:
                raise ResidentMediaV11Error("caller cannot supply a controller anchor MAC")
            if current is None:
                if (
                    unsigned.get("revision") != 0
                    or unsigned.get("generation") != 0
                    or unsigned.get("presentation_records") != []
                    or unsigned.get("previous_anchor_sha256")
                    != GENESIS_ANCHOR_SHA256_V11
                    or unsigned.get("chain_head_sha256")
                    != GENESIS_RECORD_SHA256_V11
                ):
                    raise ResidentMediaV11Error("initial V11 anchor is not exact")
            else:
                if unsigned.get("revision") != current["revision"] + 1:
                    raise ResidentMediaV11Error("V11 anchor revision is not monotonic")
                if unsigned.get("generation") != current["generation"] + 1:
                    raise ResidentMediaV11Error("V11 anchor generation is not monotonic")
                if unsigned.get("previous_anchor_sha256") != current_sha:
                    raise ResidentMediaV11Error("V11 anchor prior-head binding changed")
                old_records = current["presentation_records"]
                new_records = unsigned.get("presentation_records")
                if (
                    not isinstance(new_records, list)
                    or len(new_records) != len(old_records) + 1
                    or new_records[:-1] != old_records
                ):
                    raise ResidentMediaV11Error("V11 history is not exact append-only")
                unsigned_record = _canonical_copy(new_records[-1])
                if "controller_record_mac_sha256" in unsigned_record:
                    raise ResidentMediaV11Error("caller cannot supply a controller record MAC")
                _validate_presentation_record_v11(
                    unsigned_record,
                    catalog=self._catalog,
                    person_id=key,
                    expected_revision=len(old_records) + 1,
                    expected_previous_record_sha256=(
                        old_records[-1]["record_sha256"]
                        if old_records
                        else GENESIS_RECORD_SHA256_V11
                    ),
                    authorization=self._authorization,
                    require_controller_mac=False,
                    verify_record_mac=None,
                )
                unsigned_record["controller_record_mac_sha256"] = self._mac(
                    "presentation_record", unsigned_record
                )
                unsigned["presentation_records"][-1] = unsigned_record
                unsigned["chain_head_sha256"] = unsigned_record["record_sha256"]

            signed = dict(unsigned)
            signed["controller_anchor_mac_sha256"] = self._mac(
                "global_anchor", unsigned
            )
            signed = self._verify_signed_anchor(signed)
            self._records[(namespace, key)] = copy.deepcopy(signed)
            self._monotonic_floor[(namespace, key)] = {
                "revision": signed["revision"],
                "generation": signed["generation"],
                "chain_head_sha256": signed["chain_head_sha256"],
                "signed_anchor_sha256": _record_sha(signed),
            }
            receipt_core = {
                "schema": "kira.controller_protected_cas_receipt.v11",
                "protected_backend_identity_sha256": self._identity,
                "controller_capability_id": self._capability_id,
                "namespace": namespace,
                "record_key": key,
                "expected_previous_record_sha256": expected_record_sha256,
                "replacement_record_sha256": _record_sha(signed),
                "committed_revision": signed["revision"],
                "committed_generation": signed["generation"],
                "committed_chain_head_sha256": signed["chain_head_sha256"],
                "atomic_compare_and_swap": True,
                "strictly_monotonic_revision": True,
                "rollback_floor_separate_from_record": True,
                "exact_post_commit_readback_required": True,
            }
            receipt = dict(receipt_core)
            receipt["controller_receipt_mac_sha256"] = self._mac(
                "cas_receipt", receipt_core
            )
            return receipt

    def verify_cas_receipt(self, receipt: Mapping[str, Any]) -> None:
        expected_keys = {
            "schema",
            "protected_backend_identity_sha256",
            "controller_capability_id",
            "namespace",
            "record_key",
            "expected_previous_record_sha256",
            "replacement_record_sha256",
            "committed_revision",
            "committed_generation",
            "committed_chain_head_sha256",
            "atomic_compare_and_swap",
            "strictly_monotonic_revision",
            "rollback_floor_separate_from_record",
            "exact_post_commit_readback_required",
            "controller_receipt_mac_sha256",
        }
        if not isinstance(receipt, Mapping) or set(receipt) != expected_keys:
            raise ResidentMediaV11Error("controller CAS receipt shape changed")
        core = _canonical_copy(receipt)
        mac = core.pop("controller_receipt_mac_sha256")
        if not hmac.compare_digest(
            _nonzero_sha(mac, "controller receipt MAC"),
            self._mac("cas_receipt", core),
        ):
            raise ResidentMediaV11Error("controller CAS receipt MAC changed")


def issue_controller_owned_static_authority_v11(
    catalog: v4.StimulusCatalog,
) -> ControllerProtectedAuthorityCapabilityV11:
    """Issue the exact process-local capability for the sealed catalog only."""

    _catalog_bindings(catalog)
    return ControllerProtectedAuthorityCapabilityV11(
        _CONTROLLER_ISSUER_TOKEN, catalog
    )


class ProtectedMonotonicBackendV11:
    """Exact adapter accepting only a controller-issued V11 capability."""

    __slots__ = ("_authority", "_capability_id", "_identity")

    def __init__(self, authority: ControllerProtectedAuthorityCapabilityV11) -> None:
        if type(authority) is not ControllerProtectedAuthorityCapabilityV11:
            raise ResidentMediaV11Error(
                "exact controller-owned V11 authority capability is required"
            )
        authority._assert_controller_issued()
        self._authority = authority
        self._identity = _nonzero_sha(
            authority.backend_identity_sha256, "protected backend identity"
        )
        self._capability_id = _nonzero_identifier(
            authority.controller_capability_id, "controller capability id"
        )

    @property
    def backend_identity_sha256(self) -> str:
        return self._identity

    @property
    def controller_capability_id(self) -> str:
        return self._capability_id

    def read_catalog_authorization(
        self, catalog_sha256: str
    ) -> Mapping[str, Any] | None:
        return self._authority.read_catalog_authorization_v11(catalog_sha256)

    def read_global_receipt_anchor(self, person_id: str) -> Mapping[str, Any] | None:
        return self._authority.read_record(
            "global_receipts_v11", _nonzero_identifier(person_id, "person id")
        )

    def compare_and_swap_global_receipt_anchor(
        self,
        person_id: str,
        expected_record_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        receipt = self._authority.compare_and_swap_record(
            namespace="global_receipts_v11",
            record_key=_nonzero_identifier(person_id, "person id"),
            expected_record_sha256=expected_record_sha256,
            replacement=replacement,
        )
        self._authority.verify_cas_receipt(receipt)
        return receipt


def _validate_presentation_record_v11(
    record: Mapping[str, Any],
    *,
    catalog: v4.StimulusCatalog,
    person_id: str,
    expected_revision: int,
    expected_previous_record_sha256: str,
    authorization: Mapping[str, Any],
    require_controller_mac: bool,
    verify_record_mac: Any,
) -> dict[str, Any]:
    unsigned_keys = {
        "schema",
        "record_revision",
        "previous_record_sha256",
        "session_id",
        "person_id",
        "stimulus_id",
        "ordinal",
        "source_manifest_sha256",
        "source_time_identity_sha256",
        "derivative_set_sha256",
        "consumed_start_permit_sha256",
        "output_receipt_id",
        "renderer_or_decoder_receipt_sha256s",
        "presentation_evidence",
        "presentation_evidence_sha256",
        "record_sha256",
    }
    expected_keys = set(unsigned_keys)
    if require_controller_mac:
        expected_keys.add("controller_record_mac_sha256")
    if not isinstance(record, Mapping) or set(record) != expected_keys:
        raise ResidentMediaV11Error("V11 presentation record shape changed")
    clean = _canonical_copy(record)
    if require_controller_mac:
        if verify_record_mac is None:
            raise ResidentMediaV11Error("controller record verifier is missing")
        verify_record_mac(clean)
    if clean["schema"] != "kira.resident_media.presentation_record.v11":
        raise ResidentMediaV11Error("V11 presentation record schema changed")
    if clean["record_revision"] != expected_revision:
        raise ResidentMediaV11Error("presentation record revision changed")
    if clean["previous_record_sha256"] != expected_previous_record_sha256:
        raise ResidentMediaV11Error("presentation record chain link changed")
    _nonzero_sha(clean["previous_record_sha256"], "previous presentation record")
    session_id = _nonzero_identifier(clean["session_id"], "record session id")
    expected_person = _nonzero_identifier(person_id, "record person id")
    if clean["person_id"] != expected_person:
        raise ResidentMediaV11Error("presentation record person binding changed")
    _nonzero_identifier(clean["person_id"], "record person id")
    ordinal = clean["ordinal"]
    if isinstance(ordinal, bool) or not isinstance(ordinal, int):
        raise ResidentMediaV11Error("presentation record ordinal is invalid")
    manifest = catalog.manifest(ordinal)
    if clean["stimulus_id"] != manifest["stimulus_id"]:
        raise ResidentMediaV11Error("presentation record stimulus changed")
    if clean["source_manifest_sha256"] != authorization["manifest_sha256s"][ordinal]:
        raise ResidentMediaV11Error("presentation record source manifest changed")
    if clean["source_time_identity_sha256"] != authorization[
        "source_time_identity_sha256s"
    ][ordinal]:
        raise ResidentMediaV11Error("presentation record source-time binding changed")
    if clean["derivative_set_sha256"] != authorization[
        "derivative_set_sha256s"
    ][ordinal]:
        raise ResidentMediaV11Error("presentation record derivative-set binding changed")
    _nonzero_sha(clean["source_manifest_sha256"], "record source manifest")
    _nonzero_sha(clean["source_time_identity_sha256"], "record source-time identity")
    _nonzero_sha(clean["derivative_set_sha256"], "record derivative set")
    permit = _nonzero_sha(
        clean["consumed_start_permit_sha256"], "record consumed start permit"
    )
    output_id = _nonzero_identifier(clean["output_receipt_id"], "record output receipt")
    decoder_receipts = clean["renderer_or_decoder_receipt_sha256s"]
    if not isinstance(decoder_receipts, list) or not decoder_receipts:
        raise ResidentMediaV11Error("record decoder receipts are missing")
    for receipt in decoder_receipts:
        _nonzero_sha(receipt, "record renderer/decoder receipt")

    raw = _raw_v9_evidence(clean["presentation_evidence"])
    validated = v9.validate_presentation_evidence_v9(
        raw,
        session_id=session_id,
        person_id=expected_person,
        expected_manifest=manifest,
        consumed_start_permit_sha256=permit,
    )
    if validated != clean["presentation_evidence"]:
        raise ResidentMediaV11Error("complete canonical presentation evidence changed")
    if clean["presentation_evidence_sha256"] != _record_sha(validated):
        raise ResidentMediaV11Error("presentation evidence digest changed")
    if (
        output_id != validated["output_receipt_id"]
        or decoder_receipts
        != validated["renderer_or_decoder_receipt_sha256s"]
        or clean["source_manifest_sha256"]
        != validated["source_manifest_sha256"]
        or clean["stimulus_id"] != validated["stimulus_id"]
        or ordinal != validated["ordinal"]
        or permit != validated["consumed_start_permit_sha256"]
    ):
        raise ResidentMediaV11Error("presentation record/evidence projection changed")

    hash_core = {key: clean[key] for key in unsigned_keys if key != "record_sha256"}
    if clean["record_sha256"] != _record_sha(hash_core):
        raise ResidentMediaV11Error("presentation record digest changed")
    _nonzero_sha(clean["record_sha256"], "presentation record digest")
    return clean


def _validate_anchor_payload_v11(
    value: Mapping[str, Any],
    *,
    catalog: v4.StimulusCatalog,
    authorization: Mapping[str, Any],
    backend_identity_sha256: str,
    controller_capability_id: str,
    require_controller_macs: bool,
    verify_record_mac: Any,
) -> None:
    unsigned_keys = {
        "schema",
        "person_id",
        "generation",
        "revision",
        "previous_anchor_sha256",
        "chain_head_sha256",
        "catalog_sha256",
        "catalog_authorization_sha256",
        "owner_selection_receipt_sha256",
        "authoritative_source_policy_sha256",
        "protected_backend_identity_sha256",
        "controller_capability_id",
        "used_output_receipt_ids",
        "used_renderer_or_decoder_receipt_sha256s",
        "presentation_records",
        "global_across_sessions",
        "controller_authenticated_history",
        "live_execution_allowed",
    }
    expected_keys = set(unsigned_keys)
    if require_controller_macs:
        expected_keys.add("controller_anchor_mac_sha256")
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise ResidentMediaV11Error("V11 global anchor shape changed")
    fixed = {
        "schema": "kira.resident_media_global_receipt_ledger.v11",
        "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
        "catalog_authorization_sha256": _record_sha(authorization),
        "owner_selection_receipt_sha256": OWNER_SELECTION_RECEIPT_SHA256_V11,
        "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
        "protected_backend_identity_sha256": backend_identity_sha256,
        "controller_capability_id": controller_capability_id,
        "global_across_sessions": True,
        "controller_authenticated_history": True,
        "live_execution_allowed": False,
    }
    if any(value.get(key) != expected for key, expected in fixed.items()):
        raise ResidentMediaV11Error("V11 global anchor fixed binding changed")
    person_id = _nonzero_identifier(value["person_id"], "anchor person id")
    generation = value["generation"]
    revision = value["revision"]
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or generation < 0
        or revision < 0
    ):
        raise ResidentMediaV11Error("V11 anchor generation/revision is invalid")
    _nonzero_sha(value["previous_anchor_sha256"], "previous anchor")
    _nonzero_sha(value["chain_head_sha256"], "record chain head")
    output_ids = value["used_output_receipt_ids"]
    decoder_receipts = value["used_renderer_or_decoder_receipt_sha256s"]
    records = value["presentation_records"]
    if not isinstance(output_ids, list) or len(output_ids) > MAX_GLOBAL_RECEIPTS:
        raise ResidentMediaV11Error("V11 output receipt history is invalid")
    if len(set(output_ids)) != len(output_ids):
        raise ResidentMediaV11Error("V11 output receipt replay is present")
    for item in output_ids:
        _nonzero_identifier(item, "global output receipt id")
    if not isinstance(decoder_receipts, list) or len(decoder_receipts) > MAX_GLOBAL_RECEIPTS:
        raise ResidentMediaV11Error("V11 decoder receipt history is invalid")
    if len(set(decoder_receipts)) != len(decoder_receipts):
        raise ResidentMediaV11Error("V11 decoder receipt replay is present")
    for item in decoder_receipts:
        _nonzero_sha(item, "global renderer/decoder receipt")
    if not isinstance(records, list) or len(records) > MAX_GLOBAL_RECORDS:
        raise ResidentMediaV11Error("V11 presentation history is invalid")

    derived_outputs: list[str] = []
    derived_decoders: list[str] = []
    previous = GENESIS_RECORD_SHA256_V11
    for index, record in enumerate(records, start=1):
        clean = _validate_presentation_record_v11(
            record,
            catalog=catalog,
            person_id=person_id,
            expected_revision=index,
            expected_previous_record_sha256=previous,
            authorization=authorization,
            require_controller_mac=require_controller_macs,
            verify_record_mac=verify_record_mac,
        )
        previous = clean["record_sha256"]
        derived_outputs.append(clean["output_receipt_id"])
        derived_decoders.extend(clean["renderer_or_decoder_receipt_sha256s"])
    if generation != len(records) or revision != len(records):
        raise ResidentMediaV11Error("V11 generation/revision/history changed")
    expected_head = previous if records else GENESIS_RECORD_SHA256_V11
    if value["chain_head_sha256"] != expected_head:
        raise ResidentMediaV11Error("V11 record chain head changed")
    if output_ids != derived_outputs:
        raise ResidentMediaV11Error("V11 output receipt history changed")
    if decoder_receipts != derived_decoders:
        raise ResidentMediaV11Error("V11 decoder receipt history changed")


class ProtectedGlobalPresentationReceiptLedgerV11:
    """Validate exact V9 evidence and durably consume global receipts."""

    def __init__(
        self,
        *,
        person_id: str,
        catalog: v4.StimulusCatalog,
        protected_backend: ProtectedMonotonicBackendV11,
    ) -> None:
        if type(protected_backend) is not ProtectedMonotonicBackendV11:
            raise ResidentMediaV11Error("exact V11 protected backend is required")
        self.person_id = _nonzero_identifier(person_id, "person id")
        self.backend = protected_backend
        self._lock = threading.RLock()
        bindings = _catalog_bindings(catalog)
        self._catalog_record = bindings["catalog_record"]
        self._catalog = v4.StimulusCatalog(self._catalog_record["manifests"])
        authorization = self.backend.read_catalog_authorization(
            OWNER_SELECTED_CATALOG_SHA256_V11
        )
        if not isinstance(authorization, Mapping):
            raise ResidentMediaV11Error("controller catalog authorization is missing")
        self._catalog_authorization = _canonical_copy(authorization)
        if self._catalog_authorization.get("catalog_record") != self._catalog_record:
            raise ResidentMediaV11Error("authorized catalog record changed")
        self._catalog_authorization_sha256 = _record_sha(
            self._catalog_authorization
        )

        existing = self.backend.read_global_receipt_anchor(self.person_id)
        if existing is None:
            initial = self._build_unsigned_anchor(
                generation=0,
                revision=0,
                previous_anchor_sha256=GENESIS_ANCHOR_SHA256_V11,
                chain_head_sha256=GENESIS_RECORD_SHA256_V11,
                output_ids=[],
                decoder_receipts=[],
                records=[],
            )
            self._anchor = self._cas(None, initial)
        else:
            self._anchor = _canonical_copy(existing)
            self._validate_anchor(self._anchor)

    @classmethod
    def open(cls, **kwargs: Any) -> "ProtectedGlobalPresentationReceiptLedgerV11":
        return cls(**kwargs)

    def _fresh_catalog_and_authorization(self) -> v4.StimulusCatalog:
        snapshot = v4.StimulusCatalog(
            _canonical_copy(self._catalog_record)["manifests"]
        )
        bindings = _catalog_bindings(snapshot)
        if bindings["catalog_record"] != self._catalog_record:
            raise ResidentMediaV11Error("frozen owner-selected catalog changed")
        authorization = self.backend.read_catalog_authorization(snapshot.sha256)
        if not isinstance(authorization, Mapping):
            raise ResidentMediaV11Error("controller catalog authorization disappeared")
        if _canonical_copy(authorization) != self._catalog_authorization:
            raise ResidentMediaV11Error("controller catalog authorization changed")
        return snapshot

    def _build_unsigned_anchor(
        self,
        *,
        generation: int,
        revision: int,
        previous_anchor_sha256: str,
        chain_head_sha256: str,
        output_ids: list[str],
        decoder_receipts: list[str],
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_global_receipt_ledger.v11",
            "person_id": self.person_id,
            "generation": generation,
            "revision": revision,
            "previous_anchor_sha256": previous_anchor_sha256,
            "chain_head_sha256": chain_head_sha256,
            "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
            "catalog_authorization_sha256": self._catalog_authorization_sha256,
            "owner_selection_receipt_sha256": OWNER_SELECTION_RECEIPT_SHA256_V11,
            "authoritative_source_policy_sha256": v5.AUTHORITATIVE_SOURCE_POLICY_SHA256,
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "controller_capability_id": self.backend.controller_capability_id,
            "used_output_receipt_ids": list(output_ids),
            "used_renderer_or_decoder_receipt_sha256s": list(decoder_receipts),
            "presentation_records": copy.deepcopy(records),
            "global_across_sessions": True,
            "controller_authenticated_history": True,
            "live_execution_allowed": False,
        }

    def _validate_anchor(self, value: Mapping[str, Any]) -> None:
        _validate_anchor_payload_v11(
            value,
            catalog=self._catalog,
            authorization=self._catalog_authorization,
            backend_identity_sha256=self.backend.backend_identity_sha256,
            controller_capability_id=self.backend.controller_capability_id,
            require_controller_macs=True,
            verify_record_mac=self.backend._authority._verify_record_mac,
        )

    def _cas(
        self,
        previous: Mapping[str, Any] | None,
        replacement: Mapping[str, Any],
    ) -> dict[str, Any]:
        previous_sha = _record_sha(previous) if previous is not None else None
        receipt = self.backend.compare_and_swap_global_receipt_anchor(
            self.person_id, previous_sha, replacement
        )
        reopened = self.backend.read_global_receipt_anchor(self.person_id)
        if not isinstance(reopened, Mapping):
            raise ResidentMediaV11Error("controller V11 anchor did not read back")
        clean = _canonical_copy(reopened)
        self._validate_anchor(clean)
        expected_receipt = {
            "schema": "kira.controller_protected_cas_receipt.v11",
            "protected_backend_identity_sha256": self.backend.backend_identity_sha256,
            "controller_capability_id": self.backend.controller_capability_id,
            "namespace": "global_receipts_v11",
            "record_key": self.person_id,
            "expected_previous_record_sha256": previous_sha,
            "replacement_record_sha256": _record_sha(clean),
            "committed_revision": clean["revision"],
            "committed_generation": clean["generation"],
            "committed_chain_head_sha256": clean["chain_head_sha256"],
            "atomic_compare_and_swap": True,
            "strictly_monotonic_revision": True,
            "rollback_floor_separate_from_record": True,
            "exact_post_commit_readback_required": True,
        }
        receipt_core = _canonical_copy(receipt)
        receipt_core.pop("controller_receipt_mac_sha256")
        if receipt_core != expected_receipt:
            raise ResidentMediaV11Error("controller V11 CAS receipt changed")
        return clean

    def _assert_synced(self) -> None:
        reopened = self.backend.read_global_receipt_anchor(self.person_id)
        if not isinstance(reopened, Mapping) or _canonical_copy(reopened) != self._anchor:
            raise ResidentMediaV11Error("controller V11 anchor changed or rolled back")
        self._validate_anchor(self._anchor)

    def validate_and_consume(
        self,
        value: Mapping[str, Any],
        *,
        session_id: str,
        expected_manifest: Mapping[str, Any],
        consumed_start_permit_sha256: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._assert_synced()
            catalog = self._fresh_catalog_and_authorization()
            session_id = _nonzero_identifier(session_id, "session id")
            permit = _nonzero_sha(
                consumed_start_permit_sha256, "consumed start permit"
            )
            if not isinstance(value, Mapping) or value.get("session_id") != session_id:
                raise ResidentMediaV11Error("presentation session binding changed")
            ordinal = value.get("ordinal")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                raise ResidentMediaV11Error("presentation ordinal is invalid")
            manifest = catalog.manifest(ordinal)
            if _canonical_copy(expected_manifest) != manifest:
                raise ResidentMediaV11Error("caller expected manifest is not owner selected")
            clean = v9.validate_presentation_evidence_v9(
                value,
                session_id=session_id,
                person_id=self.person_id,
                expected_manifest=manifest,
                consumed_start_permit_sha256=permit,
            )
            _nonzero_identifier(clean["output_receipt_id"], "output receipt id")
            _nonzero_identifier(clean["output_surface_id"], "output surface id")
            for receipt in clean["renderer_or_decoder_receipt_sha256s"]:
                _nonzero_sha(receipt, "renderer/decoder receipt")

            output_ids = list(self._anchor["used_output_receipt_ids"])
            decoder_receipts = list(
                self._anchor["used_renderer_or_decoder_receipt_sha256s"]
            )
            if clean["output_receipt_id"] in output_ids:
                raise ResidentMediaV11Error("output receipt was already consumed globally")
            if any(item in decoder_receipts for item in clean["renderer_or_decoder_receipt_sha256s"]):
                raise ResidentMediaV11Error("renderer/decoder receipt was already consumed globally")
            records = copy.deepcopy(self._anchor["presentation_records"])
            if (
                len(output_ids) + 1 > MAX_GLOBAL_RECEIPTS
                or len(decoder_receipts)
                + len(clean["renderer_or_decoder_receipt_sha256s"])
                > MAX_GLOBAL_RECEIPTS
                or len(records) + 1 > MAX_GLOBAL_RECORDS
            ):
                raise ResidentMediaV11Error("V11 global ledger capacity exceeded")

            revision = self._anchor["revision"] + 1
            previous_record_sha = (
                records[-1]["record_sha256"]
                if records
                else GENESIS_RECORD_SHA256_V11
            )
            record_core = {
                "schema": "kira.resident_media.presentation_record.v11",
                "record_revision": revision,
                "previous_record_sha256": previous_record_sha,
                "session_id": session_id,
                "person_id": self.person_id,
                "stimulus_id": clean["stimulus_id"],
                "ordinal": clean["ordinal"],
                "source_manifest_sha256": clean["source_manifest_sha256"],
                "source_time_identity_sha256": self._catalog_authorization[
                    "source_time_identity_sha256s"
                ][ordinal],
                "derivative_set_sha256": self._catalog_authorization[
                    "derivative_set_sha256s"
                ][ordinal],
                "consumed_start_permit_sha256": permit,
                "output_receipt_id": clean["output_receipt_id"],
                "renderer_or_decoder_receipt_sha256s": clean[
                    "renderer_or_decoder_receipt_sha256s"
                ],
                "presentation_evidence": copy.deepcopy(clean),
                "presentation_evidence_sha256": _record_sha(clean),
            }
            record = dict(record_core)
            record["record_sha256"] = _record_sha(record_core)
            records.append(record)
            output_ids.append(clean["output_receipt_id"])
            decoder_receipts.extend(clean["renderer_or_decoder_receipt_sha256s"])
            replacement = self._build_unsigned_anchor(
                generation=self._anchor["generation"] + 1,
                revision=revision,
                previous_anchor_sha256=_record_sha(self._anchor),
                chain_head_sha256=record["record_sha256"],
                output_ids=output_ids,
                decoder_receipts=decoder_receipts,
                records=records,
            )
            committed = self._cas(self._anchor, replacement)
            self._anchor = committed
            return clean

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._assert_synced()
            self._fresh_catalog_and_authorization()
            return {
                "schema": "kira.resident_media_global_receipt_snapshot.v11",
                "person_id": self.person_id,
                "generation": self._anchor["generation"],
                "revision": self._anchor["revision"],
                "chain_head_sha256": self._anchor["chain_head_sha256"],
                "catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
                "used_output_receipt_count": len(
                    self._anchor["used_output_receipt_ids"]
                ),
                "used_renderer_or_decoder_receipt_count": len(
                    self._anchor["used_renderer_or_decoder_receipt_sha256s"]
                ),
                "presentation_record_count": len(
                    self._anchor["presentation_records"]
                ),
                "controller_owned_authority": True,
                "complete_authenticated_history": True,
                "global_across_sessions": True,
                "live_execution_allowed": False,
            }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_static_summary.v11",
        "status": "DISCONNECTED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        "exact_controller_issued_capability_required": True,
        "caller_authority_substitution_rejected": True,
        "exact_owner_selected_catalog_sha256": OWNER_SELECTED_CATALOG_SHA256_V11,
        "every_derivative_and_source_time_identity_authenticated": True,
        "complete_canonical_presentation_evidence_retained": True,
        "controller_maced_record_chain": True,
        "monotonic_revision_floor_and_cas_readback": True,
        "global_cross_session_receipt_one_use": True,
        "zero_sentinel_identifiers_rejected": True,
        "v9_per_required_role_validation_reused": True,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_or_remembered_claimed": False,
    }


__all__ = [
    "ControllerProtectedAuthorityCapabilityV11",
    "OWNER_SELECTED_CATALOG_SHA256_V11",
    "ProtectedGlobalPresentationReceiptLedgerV11",
    "ProtectedMonotonicBackendV11",
    "ResidentMediaV11Error",
    "issue_controller_owned_static_authority_v11",
    "static_contract_summary",
]
