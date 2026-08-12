"""Resident-media V12 protected-external-authority contract.

V11 was rejected because a same-process caller could read its module-resident
issuer token and rebind ``Final`` catalog globals.  V12 deliberately does not
attempt to turn Python module privacy into an operating-system trust root.
There is no issuer token, signing key, owner-selected catalog digest, mutable
authority registry, or production connection in this module.

The only executable path here is a disconnected static contract harness.  It
accepts no caller catalog.  Instead, it asks an injected external-authority
interface for canonical immutable bytes describing the exact owner-selected
catalog and every source-time/derivative binding.  Every snapshot read, anchor
read, and compare-and-swap response must carry a one-use receipt that the
external interface verifies and consumes.  The harness then retains V9's exact
per-role presentation validation and global cross-session output/decoder
receipt history.

An in-process test double can demonstrate this protocol but cannot authorize
production.  ``open_production_resident_media_v12`` always fails closed until
a separately reviewed protected authority and production integration exist.
No live media, model, device, person, memory, preference, body, or Blender
activity is authorized by this module.
"""

from __future__ import annotations

import copy
import hashlib
import re
import threading
from collections.abc import Mapping
from typing import Any, Protocol

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v5 as v5
from Core import resident_media_voluntary_gate_v8 as v8
from Core import resident_media_voluntary_gate_v9 as v9


class ResidentMediaV12Error(v9.ResidentMediaV9Error):
    """Raised when the V12 external-authority contract fails closed."""


class ProtectedExternalResidentMediaAuthorityV12(Protocol):
    """Interface a future protected authority must implement.

    Merely implementing this Python protocol is not proof of protection.  The
    public production opener does not accept an implementation.  These methods
    exist so a disconnected static harness can prove the byte-level contract
    a later native/service authority must satisfy.
    """

    def describe_contract_v12(self) -> bytes: ...

    def read_owner_selected_snapshot_v12(self, request_bytes: bytes) -> bytes: ...

    def read_global_anchor_v12(self, request_bytes: bytes) -> bytes: ...

    def compare_and_swap_global_anchor_v12(self, request_bytes: bytes) -> bytes: ...

    def consume_and_verify_receipt_v12(
        self, receipt_bytes: bytes, expected_context_sha256: str
    ) -> bytes: ...


def _canonical_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    return v4.strict_json_loads(v4.canonical_json_bytes(dict(value)))


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return v4.canonical_json_bytes(dict(value))


def _record_sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _bytes_sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decode_canonical_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not bytes or not value:
        raise ResidentMediaV12Error(f"{label} must be nonempty canonical bytes")
    try:
        decoded = v4.strict_json_loads(value)
    except Exception as exc:
        raise ResidentMediaV12Error(f"{label} is not strict JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ResidentMediaV12Error(f"{label} must decode to an object")
    clean = _canonical_copy(decoded)
    if _canonical_bytes(clean) != value:
        raise ResidentMediaV12Error(f"{label} is not canonical exact bytes")
    return clean


def _exact(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ResidentMediaV12Error(f"{label} shape changed")
    return value


def _nonzero_identifier(value: Any, field: str) -> str:
    text = v8._identifier(value, field)
    compact = re.sub(r"[-{}]", "", text)
    if (
        re.fullmatch(r"0+", text)
        or re.fullmatch(r"0+", compact)
        or text.casefold() in {"nil", "null", "none"}
    ):
        raise ResidentMediaV12Error(f"{field} cannot be a zero sentinel")
    return text


def _nonzero_sha(value: Any, field: str) -> str:
    digest = v8._sha(value, field)
    if digest == "0" * 64:
        raise ResidentMediaV12Error(f"{field} cannot be the zero digest")
    return digest


def _strict_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ResidentMediaV12Error(f"{field} must be a nonnegative integer")
    return value


def _strict_positive_int(value: Any, field: str) -> int:
    number = _strict_nonnegative_int(value, field)
    if number == 0:
        raise ResidentMediaV12Error(f"{field} must be positive")
    return number


def _genesis_record_sha() -> str:
    return hashlib.sha256(
        b"kira.resident_media.presentation_record.genesis.v12"
    ).hexdigest()


def _genesis_anchor_sha() -> str:
    return hashlib.sha256(
        b"kira.resident_media.global_anchor.genesis.v12"
    ).hexdigest()


def _raw_v9_evidence(clean: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(clean, Mapping) or not set(v9._EVIDENCE_KEYS).issubset(clean):
        raise ResidentMediaV12Error("complete canonical V9 evidence is missing")
    return {key: copy.deepcopy(clean[key]) for key in v9._EVIDENCE_KEYS}


def _catalog_bindings(catalog: v4.StimulusCatalog) -> dict[str, Any]:
    if not isinstance(catalog, v4.StimulusCatalog):
        raise ResidentMediaV12Error("snapshot catalog is not a validated v4 catalog")
    record = catalog.as_record()
    if _record_sha(record) != catalog.sha256:
        raise ResidentMediaV12Error("snapshot catalog canonical digest changed")
    try:
        authoritative_digest = v5.validate_authoritative_catalog(catalog)
    except Exception as exc:
        raise ResidentMediaV12Error(
            "snapshot catalog source identity is not authoritative"
        ) from exc
    if authoritative_digest != catalog.sha256:
        raise ResidentMediaV12Error("snapshot catalog source identity is not authoritative")

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
        derivative_set_sha256s.append(_bytes_sha(v4.canonical_json_bytes(derivatives)))
        derivative_identity_sha256s.append(
            [_record_sha(derivative) for derivative in derivatives]
        )
    return {
        "catalog_record": _canonical_copy(record),
        "catalog_sha256": catalog.sha256,
        "manifest_sha256s": manifest_sha256s,
        "source_time_identity_sha256s": source_time_sha256s,
        "derivative_set_sha256s": derivative_set_sha256s,
        "derivative_identity_sha256s": derivative_identity_sha256s,
    }


def _validate_owner_snapshot(
    value: Mapping[str, Any],
    *,
    authority_instance_id: str,
    authority_epoch_sha256: str,
) -> tuple[dict[str, Any], v4.StimulusCatalog]:
    keys = {
        "schema",
        "status",
        "authority_instance_id",
        "authority_epoch_sha256",
        "snapshot_id",
        "selection_revision",
        "owner_selection_receipt_id",
        "owner_selection_receipt_sha256",
        "authoritative_source_policy_sha256",
        "catalog_record",
        "catalog_sha256",
        "manifest_sha256s",
        "source_time_identity_sha256s",
        "derivative_set_sha256s",
        "derivative_identity_sha256s",
        "owner_selected",
        "immutable_exact_bytes",
        "caller_catalog_input_accepted",
        "live_execution_allowed",
    }
    _exact(value, keys, "owner-selected snapshot")
    clean = _canonical_copy(value)
    fixed = {
        "schema": "kira.resident_media.owner_selected_snapshot.v12",
        "status": "AUTHENTICATED_EXTERNAL_SELECTION_STATIC_CONTRACT_ONLY",
        "authority_instance_id": authority_instance_id,
        "authority_epoch_sha256": authority_epoch_sha256,
        "authoritative_source_policy_sha256": (
            "ece0785cb5bb315ea63ccb16a1643b0c22dfc65ee7bf25f41b336afebd0dc127"
        ),
        "owner_selected": True,
        "immutable_exact_bytes": True,
        "caller_catalog_input_accepted": False,
        "live_execution_allowed": False,
    }
    if any(clean.get(key) != expected for key, expected in fixed.items()):
        raise ResidentMediaV12Error("owner-selected snapshot fixed binding changed")
    _nonzero_identifier(clean["snapshot_id"], "snapshot id")
    _strict_positive_int(clean["selection_revision"], "selection revision")
    _nonzero_identifier(
        clean["owner_selection_receipt_id"], "owner selection receipt id"
    )
    _nonzero_sha(
        clean["owner_selection_receipt_sha256"], "owner selection receipt"
    )
    if not isinstance(clean["catalog_record"], Mapping) or set(
        clean["catalog_record"]
    ) != {"schema", "manifests"}:
        raise ResidentMediaV12Error("owner-selected catalog record shape changed")
    try:
        catalog = v4.StimulusCatalog(clean["catalog_record"]["manifests"])
        bindings = _catalog_bindings(catalog)
    except ResidentMediaV12Error:
        raise
    except Exception as exc:
        raise ResidentMediaV12Error("owner-selected snapshot catalog changed") from exc
    for key, expected in bindings.items():
        if clean.get(key) != expected:
            raise ResidentMediaV12Error(f"owner-selected snapshot {key} changed")
    return clean, catalog


class _ExternalAuthorityAdapterV12:
    """Static-only byte adapter for a future external protected authority."""

    def __init__(self, authority: ProtectedExternalResidentMediaAuthorityV12) -> None:
        required = (
            "describe_contract_v12",
            "read_owner_selected_snapshot_v12",
            "read_global_anchor_v12",
            "compare_and_swap_global_anchor_v12",
            "consume_and_verify_receipt_v12",
        )
        if authority is None or any(
            not callable(getattr(authority, name, None)) for name in required
        ):
            raise ResidentMediaV12Error(
                "protected external authority interface is incomplete"
            )
        self._authority = authority
        self._lock = threading.RLock()
        self._locally_consumed_receipt_ids: set[str] = set()
        self._locally_consumed_verification_ids: set[str] = set()
        try:
            descriptor_bytes = authority.describe_contract_v12()
        except Exception as exc:
            raise ResidentMediaV12Error("external authority descriptor failed") from exc
        descriptor = _decode_canonical_object(
            descriptor_bytes, "external authority descriptor"
        )
        keys = {
            "schema",
            "authority_interface_version",
            "authority_instance_id",
            "authority_epoch_sha256",
            "interface_mode",
            "caller_catalog_input_accepted",
            "immutable_snapshot_bytes",
            "atomic_monotonic_cas",
            "exact_readback_receipts",
            "global_one_use_receipts",
            "python_process_is_trust_root",
            "production_connection_active",
        }
        _exact(descriptor, keys, "external authority descriptor")
        if descriptor["schema"] != "kira.protected_external_media_authority.v12":
            raise ResidentMediaV12Error("external authority descriptor schema changed")
        if descriptor["authority_interface_version"] != 12:
            raise ResidentMediaV12Error("external authority interface version changed")
        if descriptor["interface_mode"] not in {
            "STATIC_TEST_DOUBLE",
            "PROTECTED_EXTERNAL_AUTHORITY",
        }:
            raise ResidentMediaV12Error("external authority interface mode is invalid")
        fixed_false = {
            "caller_catalog_input_accepted": False,
            "python_process_is_trust_root": False,
            "production_connection_active": False,
        }
        fixed_true = {
            "immutable_snapshot_bytes": True,
            "atomic_monotonic_cas": True,
            "exact_readback_receipts": True,
            "global_one_use_receipts": True,
        }
        if any(descriptor.get(k) is not v for k, v in fixed_false.items()) or any(
            descriptor.get(k) is not v for k, v in fixed_true.items()
        ):
            raise ResidentMediaV12Error("external authority descriptor truth changed")
        self.authority_instance_id = _nonzero_identifier(
            descriptor["authority_instance_id"], "authority instance id"
        )
        self.authority_epoch_sha256 = _nonzero_sha(
            descriptor["authority_epoch_sha256"], "authority epoch"
        )
        self.interface_mode = descriptor["interface_mode"]
        self._descriptor_bytes = descriptor_bytes
        snapshot, catalog, snapshot_bytes = self._read_snapshot()
        self._snapshot = snapshot
        self._catalog = catalog
        self._snapshot_bytes = snapshot_bytes
        self.snapshot_sha256 = _bytes_sha(snapshot_bytes)

    def _call_bytes(self, method_name: str, *args: Any, label: str) -> bytes:
        method = getattr(self._authority, method_name)
        try:
            result = method(*args)
        except Exception as exc:
            raise ResidentMediaV12Error(f"external authority {label} failed") from exc
        if type(result) is not bytes or not result:
            raise ResidentMediaV12Error(
                f"external authority {label} did not return exact bytes"
            )
        return result

    def _consume_response_receipt(
        self,
        *,
        response: Mapping[str, Any],
        response_core_keys: set[str],
        purpose: str,
        label: str,
    ) -> None:
        _exact(response, response_core_keys | {"authority_receipt"}, label)
        core = {key: copy.deepcopy(response[key]) for key in response_core_keys}
        context_sha = _record_sha(core)
        receipt = response["authority_receipt"]
        receipt_keys = {
            "schema",
            "receipt_id",
            "authority_instance_id",
            "authority_epoch_sha256",
            "purpose",
            "context_sha256",
            "authority_sequence",
            "prior_authority_receipt_sha256",
            "opaque_authenticator_sha256",
        }
        _exact(receipt, receipt_keys, "external authority receipt")
        if receipt["schema"] != "kira.protected_external_authority_receipt.v12":
            raise ResidentMediaV12Error("external authority receipt schema changed")
        receipt_id = _nonzero_identifier(receipt["receipt_id"], "authority receipt id")
        if receipt_id in self._locally_consumed_receipt_ids:
            raise ResidentMediaV12Error("authority receipt replayed in this adapter")
        fixed = {
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "purpose": purpose,
            "context_sha256": context_sha,
        }
        if any(receipt.get(key) != expected for key, expected in fixed.items()):
            raise ResidentMediaV12Error("external authority receipt binding changed")
        _strict_positive_int(receipt["authority_sequence"], "authority receipt sequence")
        _nonzero_sha(
            receipt["prior_authority_receipt_sha256"], "prior authority receipt"
        )
        _nonzero_sha(
            receipt["opaque_authenticator_sha256"], "opaque authority authenticator"
        )
        receipt_bytes = _canonical_bytes(receipt)
        verification_bytes = self._call_bytes(
            "consume_and_verify_receipt_v12",
            receipt_bytes,
            context_sha,
            label="receipt verification",
        )
        verification = _decode_canonical_object(
            verification_bytes, "external receipt verification"
        )
        verification_keys = {
            "schema",
            "authority_instance_id",
            "authority_epoch_sha256",
            "receipt_id",
            "receipt_sha256",
            "purpose",
            "context_sha256",
            "verification_receipt_id",
            "verification_sequence",
            "accepted",
            "globally_one_use",
            "consumed",
            "verifier_boundary",
        }
        _exact(verification, verification_keys, "external receipt verification")
        verification_id = _nonzero_identifier(
            verification["verification_receipt_id"], "verification receipt id"
        )
        if verification_id in self._locally_consumed_verification_ids:
            raise ResidentMediaV12Error("verification receipt replayed in this adapter")
        expected = {
            "schema": "kira.protected_external_receipt_verification.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "receipt_id": receipt_id,
            "receipt_sha256": _bytes_sha(receipt_bytes),
            "purpose": purpose,
            "context_sha256": context_sha,
            "accepted": True,
            "globally_one_use": True,
            "consumed": True,
            "verifier_boundary": "PROTECTED_EXTERNAL_AUTHORITY_INTERFACE",
        }
        if any(verification.get(key) != value for key, value in expected.items()):
            raise ResidentMediaV12Error("external receipt verification binding changed")
        _strict_positive_int(
            verification["verification_sequence"], "verification sequence"
        )
        self._locally_consumed_receipt_ids.add(receipt_id)
        self._locally_consumed_verification_ids.add(verification_id)

    def _read_snapshot(
        self,
    ) -> tuple[dict[str, Any], v4.StimulusCatalog, bytes]:
        request = {
            "schema": "kira.read_owner_selected_snapshot_request.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "caller_catalog_supplied": False,
            "static_contract_only": True,
            "live_execution_allowed": False,
        }
        response_bytes = self._call_bytes(
            "read_owner_selected_snapshot_v12",
            _canonical_bytes(request),
            label="snapshot read",
        )
        response = _decode_canonical_object(response_bytes, "snapshot read response")
        core_keys = {
            "schema",
            "authority_instance_id",
            "authority_epoch_sha256",
            "snapshot",
            "snapshot_sha256",
            "immutable_exact_bytes",
            "caller_catalog_input_accepted",
            "live_execution_allowed",
        }
        self._consume_response_receipt(
            response=response,
            response_core_keys=core_keys,
            purpose="OWNER_SELECTION_SNAPSHOT_READ",
            label="snapshot read response",
        )
        if response["schema"] != "kira.owner_selection_snapshot_read_response.v12":
            raise ResidentMediaV12Error("snapshot read response schema changed")
        if (
            response["authority_instance_id"] != self.authority_instance_id
            or response["authority_epoch_sha256"] != self.authority_epoch_sha256
            or response["immutable_exact_bytes"] is not True
            or response["caller_catalog_input_accepted"] is not False
            or response["live_execution_allowed"] is not False
        ):
            raise ResidentMediaV12Error("snapshot read response fixed binding changed")
        if not isinstance(response["snapshot"], Mapping):
            raise ResidentMediaV12Error("snapshot read response omitted snapshot")
        snapshot_bytes = _canonical_bytes(response["snapshot"])
        if response["snapshot_sha256"] != _bytes_sha(snapshot_bytes):
            raise ResidentMediaV12Error("snapshot read response digest changed")
        snapshot, catalog = _validate_owner_snapshot(
            response["snapshot"],
            authority_instance_id=self.authority_instance_id,
            authority_epoch_sha256=self.authority_epoch_sha256,
        )
        return snapshot, catalog, snapshot_bytes

    def assert_snapshot_unchanged(self) -> v4.StimulusCatalog:
        with self._lock:
            snapshot, catalog, snapshot_bytes = self._read_snapshot()
            if snapshot_bytes != self._snapshot_bytes or snapshot != self._snapshot:
                raise ResidentMediaV12Error(
                    "external owner-selected snapshot changed after binding"
                )
            return catalog

    @property
    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._snapshot)

    def read_anchor(self, person_id: str) -> dict[str, Any] | None:
        person = _nonzero_identifier(person_id, "person id")
        request = {
            "schema": "kira.read_global_anchor_request.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": self.snapshot_sha256,
            "person_id": person,
            "static_contract_only": True,
            "live_execution_allowed": False,
        }
        response_bytes = self._call_bytes(
            "read_global_anchor_v12",
            _canonical_bytes(request),
            label="anchor read",
        )
        response = _decode_canonical_object(response_bytes, "anchor read response")
        core_keys = {
            "schema",
            "authority_instance_id",
            "authority_epoch_sha256",
            "owner_selection_snapshot_sha256",
            "person_id",
            "anchor",
            "anchor_sha256",
            "exact_readback",
            "live_execution_allowed",
        }
        self._consume_response_receipt(
            response=response,
            response_core_keys=core_keys,
            purpose="GLOBAL_ANCHOR_READBACK",
            label="anchor read response",
        )
        fixed = {
            "schema": "kira.global_anchor_read_response.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": self.snapshot_sha256,
            "person_id": person,
            "exact_readback": True,
            "live_execution_allowed": False,
        }
        if any(response.get(key) != expected for key, expected in fixed.items()):
            raise ResidentMediaV12Error("anchor read response binding changed")
        if response["anchor"] is None:
            if response["anchor_sha256"] is not None:
                raise ResidentMediaV12Error("missing anchor has a digest")
            return None
        if not isinstance(response["anchor"], Mapping):
            raise ResidentMediaV12Error("anchor read response is invalid")
        clean = _canonical_copy(response["anchor"])
        if response["anchor_sha256"] != _record_sha(clean):
            raise ResidentMediaV12Error("anchor readback digest changed")
        return clean

    def compare_and_swap_anchor(
        self,
        *,
        person_id: str,
        expected_previous_anchor_sha256: str | None,
        replacement: Mapping[str, Any],
    ) -> dict[str, Any]:
        person = _nonzero_identifier(person_id, "person id")
        if expected_previous_anchor_sha256 is not None:
            expected_previous_anchor_sha256 = _nonzero_sha(
                expected_previous_anchor_sha256, "expected previous anchor"
            )
        replacement_clean = _canonical_copy(replacement)
        request = {
            "schema": "kira.compare_and_swap_global_anchor_request.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": self.snapshot_sha256,
            "person_id": person,
            "expected_previous_anchor_sha256": expected_previous_anchor_sha256,
            "replacement_anchor": replacement_clean,
            "replacement_anchor_sha256": _record_sha(replacement_clean),
            "append_only_required": True,
            "static_contract_only": True,
            "live_execution_allowed": False,
        }
        response_bytes = self._call_bytes(
            "compare_and_swap_global_anchor_v12",
            _canonical_bytes(request),
            label="anchor compare-and-swap",
        )
        response = _decode_canonical_object(response_bytes, "anchor CAS response")
        core_keys = {
            "schema",
            "authority_instance_id",
            "authority_epoch_sha256",
            "owner_selection_snapshot_sha256",
            "person_id",
            "expected_previous_anchor_sha256",
            "committed_anchor_sha256",
            "committed_revision",
            "committed_generation",
            "committed_chain_head_sha256",
            "atomic_compare_and_swap",
            "strictly_monotonic_revision",
            "global_receipt_one_use_enforced",
            "exact_post_commit_readback_required",
            "live_execution_allowed",
        }
        self._consume_response_receipt(
            response=response,
            response_core_keys=core_keys,
            purpose="GLOBAL_ANCHOR_COMPARE_AND_SWAP",
            label="anchor CAS response",
        )
        fixed = {
            "schema": "kira.global_anchor_cas_response.v12",
            "authority_instance_id": self.authority_instance_id,
            "authority_epoch_sha256": self.authority_epoch_sha256,
            "owner_selection_snapshot_sha256": self.snapshot_sha256,
            "person_id": person,
            "expected_previous_anchor_sha256": expected_previous_anchor_sha256,
            "committed_anchor_sha256": _record_sha(replacement_clean),
            "committed_revision": replacement_clean.get("revision"),
            "committed_generation": replacement_clean.get("generation"),
            "committed_chain_head_sha256": replacement_clean.get("chain_head_sha256"),
            "atomic_compare_and_swap": True,
            "strictly_monotonic_revision": True,
            "global_receipt_one_use_enforced": True,
            "exact_post_commit_readback_required": True,
            "live_execution_allowed": False,
        }
        if any(response.get(key) != expected for key, expected in fixed.items()):
            raise ResidentMediaV12Error("anchor CAS response binding changed")
        reopened = self.read_anchor(person)
        if reopened is None or reopened != replacement_clean:
            raise ResidentMediaV12Error("anchor CAS exact readback changed")
        return reopened


def _validate_presentation_record_v12(
    record: Mapping[str, Any],
    *,
    catalog: v4.StimulusCatalog,
    snapshot: Mapping[str, Any],
    person_id: str,
    expected_revision: int,
    expected_previous_record_sha256: str,
) -> dict[str, Any]:
    keys = {
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
    _exact(record, keys, "V12 presentation record")
    clean = _canonical_copy(record)
    if clean["schema"] != "kira.resident_media.presentation_record.v12":
        raise ResidentMediaV12Error("V12 presentation record schema changed")
    if clean["record_revision"] != expected_revision:
        raise ResidentMediaV12Error("presentation record revision changed")
    if clean["previous_record_sha256"] != expected_previous_record_sha256:
        raise ResidentMediaV12Error("presentation record chain link changed")
    _nonzero_sha(clean["previous_record_sha256"], "previous presentation record")
    session_id = _nonzero_identifier(clean["session_id"], "record session id")
    expected_person = _nonzero_identifier(person_id, "record person id")
    if clean["person_id"] != expected_person:
        raise ResidentMediaV12Error("presentation record person binding changed")
    ordinal = clean["ordinal"]
    if isinstance(ordinal, bool) or not isinstance(ordinal, int):
        raise ResidentMediaV12Error("presentation record ordinal is invalid")
    manifest = catalog.manifest(ordinal)
    expected = {
        "stimulus_id": manifest["stimulus_id"],
        "source_manifest_sha256": snapshot["manifest_sha256s"][ordinal],
        "source_time_identity_sha256": snapshot[
            "source_time_identity_sha256s"
        ][ordinal],
        "derivative_set_sha256": snapshot["derivative_set_sha256s"][ordinal],
    }
    if any(clean.get(key) != value for key, value in expected.items()):
        raise ResidentMediaV12Error("presentation record source projection changed")
    for key in (
        "source_manifest_sha256",
        "source_time_identity_sha256",
        "derivative_set_sha256",
    ):
        _nonzero_sha(clean[key], f"record {key}")
    permit = _nonzero_sha(
        clean["consumed_start_permit_sha256"], "record consumed start permit"
    )
    output_id = _nonzero_identifier(clean["output_receipt_id"], "record output receipt")
    decoder_receipts = clean["renderer_or_decoder_receipt_sha256s"]
    if not isinstance(decoder_receipts, list) or not decoder_receipts:
        raise ResidentMediaV12Error("record decoder receipts are missing")
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
        raise ResidentMediaV12Error("complete canonical presentation evidence changed")
    if clean["presentation_evidence_sha256"] != _record_sha(validated):
        raise ResidentMediaV12Error("presentation evidence digest changed")
    projection = {
        "output_receipt_id": validated["output_receipt_id"],
        "renderer_or_decoder_receipt_sha256s": validated[
            "renderer_or_decoder_receipt_sha256s"
        ],
        "source_manifest_sha256": validated["source_manifest_sha256"],
        "stimulus_id": validated["stimulus_id"],
        "ordinal": validated["ordinal"],
        "consumed_start_permit_sha256": validated[
            "consumed_start_permit_sha256"
        ],
    }
    if (
        output_id != projection["output_receipt_id"]
        or decoder_receipts != projection["renderer_or_decoder_receipt_sha256s"]
        or clean["source_manifest_sha256"] != projection["source_manifest_sha256"]
        or clean["stimulus_id"] != projection["stimulus_id"]
        or ordinal != projection["ordinal"]
        or permit != projection["consumed_start_permit_sha256"]
    ):
        raise ResidentMediaV12Error("presentation record/evidence projection changed")
    hash_core = {key: clean[key] for key in keys if key != "record_sha256"}
    if clean["record_sha256"] != _record_sha(hash_core):
        raise ResidentMediaV12Error("presentation record digest changed")
    _nonzero_sha(clean["record_sha256"], "presentation record digest")
    return clean


def _validate_anchor_v12(
    value: Mapping[str, Any],
    *,
    catalog: v4.StimulusCatalog,
    snapshot: Mapping[str, Any],
    snapshot_sha256: str,
    person_id: str,
    authority_instance_id: str,
    authority_epoch_sha256: str,
) -> dict[str, Any]:
    keys = {
        "schema",
        "person_id",
        "generation",
        "revision",
        "previous_anchor_sha256",
        "chain_head_sha256",
        "owner_selection_snapshot_sha256",
        "snapshot_id",
        "selection_revision",
        "owner_selection_receipt_id",
        "owner_selection_receipt_sha256",
        "catalog_sha256",
        "authoritative_source_policy_sha256",
        "authority_instance_id",
        "authority_epoch_sha256",
        "used_output_receipt_ids",
        "used_renderer_or_decoder_receipt_sha256s",
        "presentation_records",
        "global_across_sessions",
        "external_authority_read_authenticated",
        "exact_readback_required",
        "live_execution_allowed",
    }
    _exact(value, keys, "V12 global anchor")
    clean = _canonical_copy(value)
    fixed = {
        "schema": "kira.resident_media_global_receipt_ledger.v12",
        "person_id": _nonzero_identifier(person_id, "anchor person id"),
        "owner_selection_snapshot_sha256": snapshot_sha256,
        "snapshot_id": snapshot["snapshot_id"],
        "selection_revision": snapshot["selection_revision"],
        "owner_selection_receipt_id": snapshot["owner_selection_receipt_id"],
        "owner_selection_receipt_sha256": snapshot[
            "owner_selection_receipt_sha256"
        ],
        "catalog_sha256": snapshot["catalog_sha256"],
        "authoritative_source_policy_sha256": snapshot[
            "authoritative_source_policy_sha256"
        ],
        "authority_instance_id": authority_instance_id,
        "authority_epoch_sha256": authority_epoch_sha256,
        "global_across_sessions": True,
        "external_authority_read_authenticated": True,
        "exact_readback_required": True,
        "live_execution_allowed": False,
    }
    if any(clean.get(key) != expected for key, expected in fixed.items()):
        raise ResidentMediaV12Error("V12 global anchor fixed binding changed")
    generation = _strict_nonnegative_int(clean["generation"], "anchor generation")
    revision = _strict_nonnegative_int(clean["revision"], "anchor revision")
    _nonzero_sha(clean["previous_anchor_sha256"], "previous anchor")
    _nonzero_sha(clean["chain_head_sha256"], "record chain head")
    outputs = clean["used_output_receipt_ids"]
    decoders = clean["used_renderer_or_decoder_receipt_sha256s"]
    records = clean["presentation_records"]
    if not isinstance(outputs, list) or len(outputs) > 4096:
        raise ResidentMediaV12Error("V12 output receipt history is invalid")
    if len(set(outputs)) != len(outputs):
        raise ResidentMediaV12Error("V12 output receipt replay is present")
    for output in outputs:
        _nonzero_identifier(output, "global output receipt id")
    if not isinstance(decoders, list) or len(decoders) > 4096:
        raise ResidentMediaV12Error("V12 decoder receipt history is invalid")
    if len(set(decoders)) != len(decoders):
        raise ResidentMediaV12Error("V12 decoder receipt replay is present")
    for decoder in decoders:
        _nonzero_sha(decoder, "global renderer/decoder receipt")
    if not isinstance(records, list) or len(records) > 1024:
        raise ResidentMediaV12Error("V12 presentation history is invalid")
    derived_outputs: list[str] = []
    derived_decoders: list[str] = []
    previous = _genesis_record_sha()
    for index, record in enumerate(records, start=1):
        validated = _validate_presentation_record_v12(
            record,
            catalog=catalog,
            snapshot=snapshot,
            person_id=person_id,
            expected_revision=index,
            expected_previous_record_sha256=previous,
        )
        previous = validated["record_sha256"]
        derived_outputs.append(validated["output_receipt_id"])
        derived_decoders.extend(
            validated["renderer_or_decoder_receipt_sha256s"]
        )
    if generation != len(records) or revision != len(records):
        raise ResidentMediaV12Error("V12 generation/revision/history changed")
    expected_head = previous if records else _genesis_record_sha()
    if clean["chain_head_sha256"] != expected_head:
        raise ResidentMediaV12Error("V12 record chain head changed")
    if outputs != derived_outputs:
        raise ResidentMediaV12Error("V12 output receipt history changed")
    if decoders != derived_decoders:
        raise ResidentMediaV12Error("V12 decoder receipt history changed")
    return clean


class _DisconnectedStaticReceiptLedgerV12:
    """Static evidence ledger; never a live media presentation authority."""

    def __init__(
        self,
        *,
        person_id: str,
        external_authority: ProtectedExternalResidentMediaAuthorityV12,
    ) -> None:
        self.person_id = _nonzero_identifier(person_id, "person id")
        self._adapter = _ExternalAuthorityAdapterV12(external_authority)
        self._snapshot = self._adapter.snapshot
        self._snapshot_sha256 = self._adapter.snapshot_sha256
        self._catalog = v4.StimulusCatalog(
            self._snapshot["catalog_record"]["manifests"]
        )
        self._lock = threading.RLock()
        existing = self._adapter.read_anchor(self.person_id)
        if existing is None:
            initial = self._build_anchor(
                generation=0,
                revision=0,
                previous_anchor_sha256=_genesis_anchor_sha(),
                chain_head_sha256=_genesis_record_sha(),
                output_ids=[],
                decoder_receipts=[],
                records=[],
            )
            self._anchor = self._adapter.compare_and_swap_anchor(
                person_id=self.person_id,
                expected_previous_anchor_sha256=None,
                replacement=initial,
            )
        else:
            self._anchor = existing
        self._validate_anchor(self._anchor)

    def _build_anchor(
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
            "schema": "kira.resident_media_global_receipt_ledger.v12",
            "person_id": self.person_id,
            "generation": generation,
            "revision": revision,
            "previous_anchor_sha256": previous_anchor_sha256,
            "chain_head_sha256": chain_head_sha256,
            "owner_selection_snapshot_sha256": self._snapshot_sha256,
            "snapshot_id": self._snapshot["snapshot_id"],
            "selection_revision": self._snapshot["selection_revision"],
            "owner_selection_receipt_id": self._snapshot[
                "owner_selection_receipt_id"
            ],
            "owner_selection_receipt_sha256": self._snapshot[
                "owner_selection_receipt_sha256"
            ],
            "catalog_sha256": self._snapshot["catalog_sha256"],
            "authoritative_source_policy_sha256": self._snapshot[
                "authoritative_source_policy_sha256"
            ],
            "authority_instance_id": self._adapter.authority_instance_id,
            "authority_epoch_sha256": self._adapter.authority_epoch_sha256,
            "used_output_receipt_ids": list(output_ids),
            "used_renderer_or_decoder_receipt_sha256s": list(decoder_receipts),
            "presentation_records": copy.deepcopy(records),
            "global_across_sessions": True,
            "external_authority_read_authenticated": True,
            "exact_readback_required": True,
            "live_execution_allowed": False,
        }

    def _validate_anchor(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _validate_anchor_v12(
            value,
            catalog=self._catalog,
            snapshot=self._snapshot,
            snapshot_sha256=self._snapshot_sha256,
            person_id=self.person_id,
            authority_instance_id=self._adapter.authority_instance_id,
            authority_epoch_sha256=self._adapter.authority_epoch_sha256,
        )

    def _assert_synced(self) -> None:
        self._adapter.assert_snapshot_unchanged()
        reopened = self._adapter.read_anchor(self.person_id)
        if reopened is None or reopened != self._anchor:
            raise ResidentMediaV12Error("external authority anchor changed or rolled back")
        self._validate_anchor(reopened)

    def validate_and_record_static_evidence(
        self,
        value: Mapping[str, Any],
        *,
        session_id: str,
        expected_manifest: Mapping[str, Any],
        consumed_start_permit_sha256: str,
    ) -> dict[str, Any]:
        """Validate static evidence and consume receipts; present no media."""

        with self._lock:
            self._assert_synced()
            catalog = self._adapter.assert_snapshot_unchanged()
            session = _nonzero_identifier(session_id, "session id")
            permit = _nonzero_sha(
                consumed_start_permit_sha256, "consumed start permit"
            )
            if not isinstance(value, Mapping) or value.get("session_id") != session:
                raise ResidentMediaV12Error("presentation session binding changed")
            ordinal = value.get("ordinal")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                raise ResidentMediaV12Error("presentation ordinal is invalid")
            manifest = catalog.manifest(ordinal)
            if _canonical_copy(expected_manifest) != manifest:
                raise ResidentMediaV12Error(
                    "caller expected manifest is not the external owner selection"
                )
            clean = v9.validate_presentation_evidence_v9(
                value,
                session_id=session,
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
                raise ResidentMediaV12Error(
                    "output receipt was already consumed globally"
                )
            if any(
                item in decoder_receipts
                for item in clean["renderer_or_decoder_receipt_sha256s"]
            ):
                raise ResidentMediaV12Error(
                    "renderer/decoder receipt was already consumed globally"
                )
            records = copy.deepcopy(self._anchor["presentation_records"])
            if (
                len(output_ids) + 1 > 4096
                or len(decoder_receipts)
                + len(clean["renderer_or_decoder_receipt_sha256s"])
                > 4096
                or len(records) + 1 > 1024
            ):
                raise ResidentMediaV12Error("V12 global ledger capacity exceeded")
            revision = self._anchor["revision"] + 1
            previous_record_sha = (
                records[-1]["record_sha256"]
                if records
                else _genesis_record_sha()
            )
            record_core = {
                "schema": "kira.resident_media.presentation_record.v12",
                "record_revision": revision,
                "previous_record_sha256": previous_record_sha,
                "session_id": session,
                "person_id": self.person_id,
                "stimulus_id": clean["stimulus_id"],
                "ordinal": clean["ordinal"],
                "source_manifest_sha256": clean["source_manifest_sha256"],
                "source_time_identity_sha256": self._snapshot[
                    "source_time_identity_sha256s"
                ][ordinal],
                "derivative_set_sha256": self._snapshot[
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
            decoder_receipts.extend(
                clean["renderer_or_decoder_receipt_sha256s"]
            )
            replacement = self._build_anchor(
                generation=self._anchor["generation"] + 1,
                revision=revision,
                previous_anchor_sha256=_record_sha(self._anchor),
                chain_head_sha256=record["record_sha256"],
                output_ids=output_ids,
                decoder_receipts=decoder_receipts,
                records=records,
            )
            self._validate_anchor(replacement)
            committed = self._adapter.compare_and_swap_anchor(
                person_id=self.person_id,
                expected_previous_anchor_sha256=_record_sha(self._anchor),
                replacement=replacement,
            )
            self._validate_anchor(committed)
            self._anchor = committed
            return clean

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._assert_synced()
            return {
                "schema": "kira.resident_media_static_contract_snapshot.v12",
                "status": "DISCONNECTED_STATIC_EXTERNAL_AUTHORITY_CONTRACT_ONLY",
                "person_id": self.person_id,
                "generation": self._anchor["generation"],
                "revision": self._anchor["revision"],
                "chain_head_sha256": self._anchor["chain_head_sha256"],
                "owner_selection_snapshot_sha256": self._snapshot_sha256,
                "catalog_sha256": self._snapshot["catalog_sha256"],
                "used_output_receipt_count": len(
                    self._anchor["used_output_receipt_ids"]
                ),
                "used_renderer_or_decoder_receipt_count": len(
                    self._anchor["used_renderer_or_decoder_receipt_sha256s"]
                ),
                "presentation_record_count": len(
                    self._anchor["presentation_records"]
                ),
                "external_authority_interface_contract_exercised": True,
                "python_process_is_trust_root": False,
                "live_execution_allowed": False,
                "person_saw_or_heard_claimed": False,
                "person_enjoyed_or_remembered_claimed": False,
            }


def _open_disconnected_static_contract_harness_v12(
    *,
    person_id: str,
    external_authority: ProtectedExternalResidentMediaAuthorityV12,
) -> _DisconnectedStaticReceiptLedgerV12:
    """Open only the static protocol harness; never a production gate."""

    return _DisconnectedStaticReceiptLedgerV12(
        person_id=person_id,
        external_authority=external_authority,
    )


def open_production_resident_media_v12(*args: Any, **kwargs: Any) -> None:
    """Fail closed: no protected external production authority is connected."""

    del args, kwargs
    raise ResidentMediaV12Error(
        "V12 production resident-media opener is disconnected; a separately "
        "reviewed protected external authority integration does not exist"
    )


def production_connection_status_v12() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_production_connection_status.v12",
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
        "schema": "kira.resident_media_voluntary_gate_static_summary.v12",
        "status": "DISCONNECTED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        "module_resident_issuer_token_removed": True,
        "rebindable_final_catalog_globals_trusted": False,
        "caller_catalog_accepted": False,
        "external_authority_exact_immutable_snapshot_required": True,
        "external_snapshot_binds_selection_source_time_and_all_derivatives": True,
        "external_one_use_snapshot_read_cas_and_readback_receipts_required": True,
        "global_cross_session_output_and_decoder_receipt_one_use": True,
        "v9_exact_per_required_role_validation_retained": True,
        "complete_canonical_presentation_evidence_retained": True,
        "static_test_double_is_production_authority": False,
        "python_process_is_trust_root": False,
        "public_production_opener_disconnected": True,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_or_remembered_claimed": False,
    }


__all__ = [
    "ProtectedExternalResidentMediaAuthorityV12",
    "ResidentMediaV12Error",
    "open_production_resident_media_v12",
    "production_connection_status_v12",
    "static_contract_summary",
]
