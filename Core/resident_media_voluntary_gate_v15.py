"""Resident-media V15 immutable no-commit validation boundary.

V12 and V13 remain preserved and rejected. V14 also remains preserved and is
rejected: its validator method closure exposed a WeakKeyDictionary containing
mutable ``_SnapshotStateV14`` objects. Each state retained a mutable V4
``StimulusCatalog``. Mutating ``catalog._manifests`` left the cached catalog
SHA-256 unchanged, so V14 could validate against changed manifest contents and
emit a stale catalog digest.

V15 retains no catalog object, mapping, list, WeakKeyDictionary, lock,
authority, adapter, ledger, receipt history, durable anchor, compare-and-swap
callable, or commit surface. A validator is an exact tuple subclass containing
only a private identity marker, an exact person identifier, immutable
canonical snapshot bytes, and their SHA-256. Every public operation decodes
and fully revalidates those bytes, constructs a fresh short-lived catalog,
derives the canonical catalog bytes and digest anew, and discards the catalog
before return. Ordinary closure/slot traversal therefore reaches no mutable
manifest store.

The static plan is returned as an exact built-in tuple envelope containing its
canonical JSON bytes and the SHA-256 derived from those exact bytes. Every
decode verifies the two immutable tuple items agree and returns a fresh decoded
copy. Because the result is an exact built-in tuple, no Python subclass member
can be replaced after return. This establishes an exact plan-byte/digest
invariant for a non-authoritative result. It does not
make Python an operating-system trust root and does not authenticate the
caller-supplied snapshot as protected-authority truth.

The V15 bootstrap binds the exact V15 source and invokes the already sealed V14
bootstrap, which in turn binds V14/V13/V12/V9/V4. The module opens, decodes,
renders, plays, or presents no media; calls no model, network, device, person,
or protected authority; changes no state; and creates no seeing, hearing,
enjoyment, learning, preference, relationship, memory, or consciousness claim.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v12 as v12
from Core import resident_media_voluntary_gate_v14 as v14


class ResidentMediaV15Error(v14.ResidentMediaV14Error):
    """Raised when the immutable V15 static validator fails closed."""


_ROOT = Path(__file__).resolve().parents[1]
_BINDING_PATH = (
    _ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "resident_media_voluntary_v15"
    / "attempt_01"
    / "EXECUTION_BINDING_V15.json"
)
_MISSING = object()
_STATE_SEAL = object()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_bytes(value: Any, label: str) -> bytes:
    try:
        raw = v4.canonical_json_bytes(value)
        clean = v4.strict_json_loads(raw)
    except Exception as exc:
        raise ResidentMediaV15Error(f"{label} is not strict canonical JSON") from exc
    if v4.canonical_json_bytes(clean) != raw:
        raise ResidentMediaV15Error(f"{label} canonical round trip changed")
    return raw


def _canonical_copy(value: Any, label: str) -> dict[str, Any]:
    try:
        clean = v14._canonical_mapping_copy(value, label)
        v14._require_exact_scalar_types(clean, label)
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc
    return clean


def _exact_identifier_v15(value: Any, label: str) -> str:
    try:
        return v14._exact_identifier(value, label)
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc


def _exact_sha256_v15(value: Any, label: str) -> str:
    try:
        clean = v14._exact_sha256(value, label)
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc
    assert isinstance(clean, str)
    return clean


def _exact_types_v15(value: Any, label: str) -> None:
    try:
        v14._require_exact_scalar_types(value, label)
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc


def _preflight_complete_evidence_v15(
    value: Mapping[str, Any],
    *,
    session_id: str,
    person_id: str,
    expected_manifest: Mapping[str, Any],
    consumed_start_permit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    try:
        return v14._preflight_complete_evidence_v14(
            value,
            session_id=session_id,
            person_id=person_id,
            expected_manifest=expected_manifest,
            consumed_start_permit_sha256=consumed_start_permit_sha256,
        )
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc


def decode_static_plan_envelope_v15(value: Any) -> dict[str, Any]:
    """Verify an exact immutable ``(canonical_bytes, sha256)`` result."""

    if type(value) is not tuple or len(value) != 2:
        raise ResidentMediaV15Error("V15 plan envelope must be an exact pair")
    raw, reported = value
    if (
        type(raw) is not bytes
        or not raw
        or type(reported) is not str
        or re.fullmatch(r"[0-9a-f]{64}", reported) is None
        or _sha256(raw) != reported
    ):
        raise ResidentMediaV15Error("V15 plan envelope byte/digest invariant changed")
    try:
        clean = v4.strict_json_loads(raw)
    except Exception as exc:
        raise ResidentMediaV15Error("V15 plan envelope is not strict JSON") from exc
    if type(clean) is not dict or _canonical_bytes(
        clean, "V15 plan envelope"
    ) != raw:
        raise ResidentMediaV15Error("V15 plan envelope canonical bytes changed")
    return clean


def _validate_snapshot_input_v15(
    owner_selected_snapshot_bytes: Any,
    expected_snapshot_sha256: Any,
) -> tuple[dict[str, Any], bytes, bytes, str]:
    """Validate static bytes and freshly derive their exact catalog binding."""

    try:
        snapshot, snapshot_bytes, catalog = v14._validate_snapshot_input_v14(
            owner_selected_snapshot_bytes,
            expected_snapshot_sha256,
        )
        catalog_record = catalog.as_record()
        catalog_bytes = _canonical_bytes(catalog_record, "V15 catalog record")
        catalog_sha256 = _sha256(catalog_bytes)
    except Exception as exc:
        raise ResidentMediaV15Error("V15 snapshot input is not self-consistent") from exc
    if snapshot.get("catalog_record") != catalog_record:
        raise ResidentMediaV15Error("V15 snapshot/catalog record binding changed")
    if snapshot.get("catalog_sha256") != catalog_sha256:
        raise ResidentMediaV15Error("V15 freshly derived catalog digest changed")
    if getattr(catalog, "sha256", _MISSING) != catalog_sha256:
        raise ResidentMediaV15Error("V15 fresh catalog cache disagrees with bytes")
    return snapshot, bytes(snapshot_bytes), catalog_bytes, catalog_sha256


def _decode_immutable_state_v15(
    instance: Any,
    validator_type: type,
) -> tuple[str, dict[str, Any], bytes, str]:
    """Revalidate immutable tuple state; retain no decoded mutable object."""

    if type(instance) is not validator_type or len(instance) != 4:
        raise ResidentMediaV15Error("V15 validator is not exact factory output")
    seal = tuple.__getitem__(instance, 0)
    person_id = tuple.__getitem__(instance, 1)
    snapshot_bytes = tuple.__getitem__(instance, 2)
    snapshot_sha256 = tuple.__getitem__(instance, 3)
    if seal is not _STATE_SEAL:
        raise ResidentMediaV15Error("V15 validator identity seal changed")
    try:
        person = _exact_identifier_v15(person_id, "V15 bound person id")
        expected = _exact_sha256_v15(snapshot_sha256, "V15 bound snapshot SHA-256")
    except Exception as exc:
        raise ResidentMediaV15Error(str(exc)) from exc
    if type(snapshot_bytes) is not bytes or not snapshot_bytes:
        raise ResidentMediaV15Error("V15 bound snapshot bytes changed")
    if _sha256(snapshot_bytes) != expected:
        raise ResidentMediaV15Error("V15 bound snapshot digest changed")
    snapshot, exact_bytes, catalog_bytes, catalog_sha256 = (
        _validate_snapshot_input_v15(snapshot_bytes, expected)
    )
    if exact_bytes != snapshot_bytes:
        raise ResidentMediaV15Error("V15 bound snapshot byte identity changed")
    if snapshot.get("catalog_sha256") != catalog_sha256:
        raise ResidentMediaV15Error("V15 snapshot/fresh catalog digest changed")
    return person, snapshot, catalog_bytes, catalog_sha256


def _load_execution_binding_v15(
) -> tuple[dict[str, Any], bytes, tuple[int, int, int, int]]:
    try:
        resolved = _BINDING_PATH.resolve(strict=True)
        before = resolved.stat()
        raw = resolved.read_bytes()
        after = resolved.stat()
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ResidentMediaV15Error("V15 execution binding is unavailable") from exc
    before_identity = (
        int(before.st_dev), int(before.st_ino), int(before.st_size),
        int(before.st_mtime_ns),
    )
    after_identity = (
        int(after.st_dev), int(after.st_ino), int(after.st_size),
        int(after.st_mtime_ns),
    )
    keys = {
        "schema", "candidate_id", "status", "modules",
        "v12_v13_and_v14_rejected", "immutable_byte_state_only",
        "v14_bootstrap_chain_required", "authority_protocol_calls_authorized",
        "durable_commit_authorized", "production_routing_authorized",
        "live_media_authorized", "person_state_authorized",
        "different_fresh_static_audit_required",
    }
    if before_identity != after_identity:
        raise ResidentMediaV15Error("V15 execution binding changed while read")
    if type(value) is not dict or set(value) != keys:
        raise ResidentMediaV15Error("V15 execution binding schema is not exact")
    if (
        value["schema"] != "kira.resident_media.voluntary_v15.execution_binding.v1"
        or value["candidate_id"] != "resident_media_voluntary_v15"
        or value["status"]
        != "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT"
        or value["v12_v13_and_v14_rejected"] is not True
        or value["immutable_byte_state_only"] is not True
        or value["v14_bootstrap_chain_required"] is not True
        or value["authority_protocol_calls_authorized"] is not False
        or value["durable_commit_authorized"] is not False
        or value["production_routing_authorized"] is not False
        or value["live_media_authorized"] is not False
        or value["person_state_authorized"] is not False
        or value["different_fresh_static_audit_required"] is not True
    ):
        raise ResidentMediaV15Error("V15 execution binding truth changed")
    modules = value["modules"]
    if type(modules) is not list or len(modules) != 1:
        raise ResidentMediaV15Error("V15 execution module closure is not exact")
    entry = modules[0]
    entry_keys = {
        "label", "module_name", "package_attribute", "relative_path",
        "bytes", "sha256",
    }
    if (
        type(entry) is not dict
        or set(entry) != entry_keys
        or entry["label"] != "v15"
        or entry["module_name"] != "Core.resident_media_voluntary_gate_v15"
        or entry["package_attribute"] != "resident_media_voluntary_gate_v15"
        or entry["relative_path"] != "Core/resident_media_voluntary_gate_v15.py"
        or type(entry["bytes"]) is not int
        or isinstance(entry["bytes"], bool)
        or entry["bytes"] <= 0
        or type(entry["sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
    ):
        raise ResidentMediaV15Error("V15 execution module entry changed")
    return value, raw, after_identity


class _BootstrapV15:
    __slots__ = (
        "binding", "binding_bytes", "binding_identity", "binding_path",
        "binding_sha256", "parent", "self_seal", "v14_bootstrap_id",
        "v14_bootstrap_type", "v14_verify_function", "v14_verify_code",
        "finalized",
    )

    def __init__(self) -> None:
        binding, raw, identity = _load_execution_binding_v15()
        parent = sys.modules.get("Core")
        module = sys.modules.get(__name__)
        if type(parent) is not types.ModuleType or type(module) is not types.ModuleType:
            raise ResidentMediaV15Error("V15 module/package identity is unavailable")
        entry = binding["modules"][0]
        if module.__name__ != entry["module_name"]:
            raise ResidentMediaV15Error("V15 module name binding changed")
        try:
            runtime_entry = dict(entry)
            runtime_entry["relative_path"] = str(
                (_ROOT / entry["relative_path"]).resolve(strict=True)
            )
            seal = v14._ModuleSealV14(
                label="v15",
                module=module,
                parent=parent,
                binding=runtime_entry,
                finalize=False,
            )
            predecessor = v14._BOOTSTRAP_V14
            predecessor_type = type(predecessor)
            predecessor_verify_function = predecessor_type.__dict__["verify"]
            predecessor_verify_function(predecessor)
        except Exception as exc:
            raise ResidentMediaV15Error("V15 predecessor seal is unavailable") from exc
        self.binding = binding
        self.binding_bytes = raw
        self.binding_identity = identity
        self.binding_path = str(_BINDING_PATH.resolve(strict=True))
        self.binding_sha256 = _sha256(raw)
        self.parent = parent
        self.self_seal = seal
        self.v14_bootstrap_id = id(predecessor)
        self.v14_bootstrap_type = predecessor_type
        self.v14_verify_function = predecessor_verify_function
        self.v14_verify_code = predecessor_verify_function.__code__
        self.finalized = False

    def finalize_self(self) -> None:
        if self.finalized:
            raise ResidentMediaV15Error("V15 bootstrap was already finalized")
        try:
            self.self_seal.finalize()
        except Exception as exc:
            raise ResidentMediaV15Error("V15 self seal could not finalize") from exc
        self.finalized = True

    def verify(self) -> None:
        if self.finalized is not True:
            raise ResidentMediaV15Error("V15 bootstrap is not finalized")
        current_predecessor = v14._BOOTSTRAP_V14
        if (
            type(current_predecessor) is not self.v14_bootstrap_type
            or id(current_predecessor) != self.v14_bootstrap_id
            or self.v14_bootstrap_type.__dict__.get("verify")
            is not self.v14_verify_function
            or self.v14_verify_function.__code__ is not self.v14_verify_code
        ):
            raise ResidentMediaV15Error("V15 predecessor verifier identity changed")
        try:
            self.v14_verify_function(current_predecessor)
            resolved = _BINDING_PATH.resolve(strict=True)
            before = resolved.stat()
            raw = resolved.read_bytes()
            after = resolved.stat()
        except Exception as exc:
            raise ResidentMediaV15Error("V15 sealed predecessor/binding changed") from exc
        before_identity = (
            int(before.st_dev), int(before.st_ino), int(before.st_size),
            int(before.st_mtime_ns),
        )
        after_identity = (
            int(after.st_dev), int(after.st_ino), int(after.st_size),
            int(after.st_mtime_ns),
        )
        if (
            str(resolved) != self.binding_path
            or before_identity != after_identity
            or after_identity != self.binding_identity
            or raw != self.binding_bytes
            or _sha256(raw) != self.binding_sha256
        ):
            raise ResidentMediaV15Error("V15 execution binding changed")
        try:
            self.self_seal.verify()
        except Exception as exc:
            raise ResidentMediaV15Error("V15 module execution seal changed") from exc


def _make_public_surface_v15(
    bootstrap: _BootstrapV15,
) -> tuple[type, types.FunctionType]:
    bootstrap_verify = bootstrap.verify
    bootstrap_verify_function = bootstrap_verify.__func__
    bootstrap_verify_code = bootstrap_verify_function.__code__
    validate_state = _decode_immutable_state_v15
    validate_snapshot = _validate_snapshot_input_v15
    canonical_copy = _canonical_copy
    canonical_bytes = _canonical_bytes
    preflight = _preflight_complete_evidence_v15
    exact_identifier = _exact_identifier_v15
    exact_sha = _exact_sha256_v15
    exact_types = _exact_types_v15
    record_sha = v12._record_sha
    digest_bytes = _sha256
    decode_envelope = decode_static_plan_envelope_v15
    state_seal = _STATE_SEAL
    error_type = ResidentMediaV15Error

    def guard() -> None:
        if (
            bootstrap_verify.__self__ is not bootstrap
            or bootstrap_verify.__func__ is not bootstrap_verify_function
            or bootstrap_verify_function.__code__ is not bootstrap_verify_code
        ):
            raise error_type("V15 bootstrap verifier identity changed")
        bootstrap_verify()

    class DisconnectedStaticValidatorV15(tuple):
        __slots__ = ()

        def __new__(cls, *args: Any, **kwargs: Any) -> Any:
            del cls, args, kwargs
            raise TypeError("V15 validators are factory-created only")

        def __copy__(self) -> Any:
            raise TypeError("V15 validator cannot be copied")

        def __deepcopy__(self, _memo: Any) -> Any:
            raise TypeError("V15 validator cannot be copied")

        def __reduce__(self) -> Any:
            raise TypeError("V15 validator cannot be serialized")

        def validate_static_evidence_plan(
            self,
            value: Mapping[str, Any],
            *,
            session_id: str,
            expected_manifest: Mapping[str, Any],
            consumed_start_permit_sha256: str,
        ) -> Any:
            """Return immutable canonical plan bytes; never consume or commit."""

            guard()
            person, snapshot, catalog_bytes, catalog_sha256 = validate_state(
                self, DisconnectedStaticValidatorV15
            )
            session = exact_identifier(session_id, "V15 session id")
            permit = exact_sha(
                consumed_start_permit_sha256, "V15 consumed start permit"
            )
            assert isinstance(permit, str)
            frozen_value = canonical_copy(value, "V15 presentation evidence")
            if frozen_value.get("session_id") != session:
                raise error_type("V15 presentation session binding changed")
            ordinal = frozen_value.get("ordinal")
            if isinstance(ordinal, bool) or not isinstance(ordinal, int):
                raise error_type("V15 presentation ordinal is invalid")
            manifests = snapshot["catalog_record"]["manifests"]
            if not 0 <= ordinal < len(manifests):
                raise error_type("V15 bound manifest is missing")
            authoritative_manifest = canonical_copy(
                manifests[ordinal], "V15 freshly decoded bound manifest"
            )
            if canonical_copy(
                expected_manifest, "V15 expected manifest"
            ) != authoritative_manifest:
                raise error_type(
                    "V15 expected manifest is not the immutable static snapshot"
                )
            clean, manifest, required_roles = preflight(
                frozen_value,
                session_id=session,
                person_id=person,
                expected_manifest=authoritative_manifest,
                consumed_start_permit_sha256=permit,
            )
            guard()
            person_again, snapshot_again, catalog_bytes_again, catalog_sha_again = (
                validate_state(self, DisconnectedStaticValidatorV15)
            )
            clean_again, manifest_again, roles_again = preflight(
                frozen_value,
                session_id=session,
                person_id=person_again,
                expected_manifest=canonical_copy(
                    snapshot_again["catalog_record"]["manifests"][ordinal],
                    "V15 repeated freshly decoded bound manifest",
                ),
                consumed_start_permit_sha256=permit,
            )
            if (
                person_again != person
                or snapshot_again != snapshot
                or catalog_bytes_again != catalog_bytes
                or catalog_sha_again != catalog_sha256
                or clean_again != clean
                or manifest_again != manifest
                or roles_again != required_roles
            ):
                raise error_type("V15 repeated immutable static validation changed")
            plan = {
                "schema": "kira.resident_media.no_commit_validation_plan.v15",
                "status": "VALIDATED_IMMUTABLE_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED",
                "person_id": person,
                "session_id": session,
                "ordinal": clean["ordinal"],
                "stimulus_id": clean["stimulus_id"],
                "owner_selection_snapshot_sha256": tuple.__getitem__(self, 3),
                "catalog_sha256": catalog_sha256,
                "source_manifest_sha256": clean["source_manifest_sha256"],
                "consumed_start_permit_sha256": permit,
                "presentation_evidence": copy.deepcopy(clean),
                "presentation_evidence_sha256": record_sha(clean),
                "required_roles": list(required_roles),
                "complete_by_required_role": copy.deepcopy(
                    clean["complete_by_required_role"]
                ),
                "plan_digest_is_derived_from_exact_envelope_bytes": True,
                "snapshot_input_authenticated_by_protected_authority": False,
                "authority_protocol_called": False,
                "receipt_consumed": False,
                "anchor_read": False,
                "commit_attempted": False,
                "durable_record_created": False,
                "protected_external_native_commit_broker_required": True,
                "live_execution_allowed": False,
                "person_saw_or_heard_claimed": False,
                "person_enjoyed_learned_preferred_or_remembered_claimed": False,
            }
            exact_types(plan, "V15 immutable no-commit validation plan")
            plan_bytes = canonical_bytes(plan, "V15 immutable no-commit plan")
            plan_sha256 = digest_bytes(plan_bytes)
            envelope = (plan_bytes, plan_sha256)
            if (
                type(envelope) is not tuple
                or envelope[0] != plan_bytes
                or envelope[1] != plan_sha256
                or decode_envelope(envelope) != plan
            ):
                raise error_type("V15 immutable plan envelope changed at creation")
            guard()
            final_person, final_snapshot, final_catalog_bytes, final_catalog_sha = (
                validate_state(self, DisconnectedStaticValidatorV15)
            )
            if (
                final_person != person
                or final_snapshot != snapshot
                or final_catalog_bytes != catalog_bytes
                or final_catalog_sha != catalog_sha256
            ):
                raise error_type("V15 immutable state changed before plan emission")
            if envelope[1] != digest_bytes(envelope[0]):
                raise error_type("V15 emitted plan byte/digest invariant changed")
            return envelope

        def validate_and_record_static_evidence(
            self,
            value: Mapping[str, Any],
            *,
            session_id: str,
            expected_manifest: Mapping[str, Any],
            consumed_start_permit_sha256: str,
        ) -> None:
            del value, session_id, expected_manifest, consumed_start_permit_sha256
            guard()
            validate_state(self, DisconnectedStaticValidatorV15)
            raise error_type(
                "V15 has no commit surface; use validate_static_evidence_plan only. "
                "A separately reviewed protected external/native broker is required."
            )

        def snapshot(self) -> dict[str, Any]:
            guard()
            person, _snapshot, _catalog_bytes, catalog_sha256 = validate_state(
                self, DisconnectedStaticValidatorV15
            )
            return {
                "schema": "kira.resident_media_static_validator_snapshot.v15",
                "status": "DISCONNECTED_IMMUTABLE_NO_COMMIT_STATIC_VALIDATOR_ONLY",
                "person_id": person,
                "owner_selection_snapshot_sha256": tuple.__getitem__(self, 3),
                "catalog_sha256": catalog_sha256,
                "immutable_tuple_state_only": True,
                "mutable_catalog_retained": False,
                "mutable_mapping_or_weak_registry_retained": False,
                "authority_retained": False,
                "adapter_retained": False,
                "ledger_retained": False,
                "anchor_retained": False,
                "commit_callable_retained": False,
                "authority_protocol_called": False,
                "durable_commit_authorized": False,
                "python_process_is_trust_root": False,
                "live_execution_allowed": False,
            }

    DisconnectedStaticValidatorV15.__name__ = "_DisconnectedStaticValidatorV15"
    DisconnectedStaticValidatorV15.__qualname__ = "_DisconnectedStaticValidatorV15"
    DisconnectedStaticValidatorV15.__module__ = __name__

    def open_harness(
        *,
        person_id: str,
        owner_selected_snapshot_bytes: bytes,
        expected_snapshot_sha256: str,
    ) -> Any:
        """Bind caller-supplied immutable bytes without calling an authority."""

        guard()
        try:
            person = exact_identifier(person_id, "V15 person id")
            _snapshot, snapshot_bytes, _catalog_bytes, _catalog_sha256 = (
                validate_snapshot(
                    owner_selected_snapshot_bytes, expected_snapshot_sha256
                )
            )
            snapshot_sha256 = digest_bytes(snapshot_bytes)
            instance = tuple.__new__(
                DisconnectedStaticValidatorV15,
                (state_seal, person, snapshot_bytes, snapshot_sha256),
            )
        except Exception as exc:
            if isinstance(exc, error_type):
                raise
            raise error_type("V15 immutable validator creation failed") from exc
        validate_state(instance, DisconnectedStaticValidatorV15)
        guard()
        return instance

    open_harness.__name__ = "_open_disconnected_static_validation_harness_v15"
    open_harness.__module__ = __name__
    return DisconnectedStaticValidatorV15, open_harness


_BOOTSTRAP_V15 = _BootstrapV15()
(
    _DisconnectedStaticValidatorV15,
    _open_disconnected_static_validation_harness_v15,
) = _make_public_surface_v15(_BOOTSTRAP_V15)


def open_production_resident_media_v15(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise ResidentMediaV15Error(
        "V15 production resident-media opener is disconnected and V15 contains "
        "no authority, anchor, record, or commit surface"
    )


def production_connection_status_v15() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_production_connection_status.v15",
        "status": "DISCONNECTED_IMMUTABLE_NO_COMMIT_SURFACE",
        "protected_external_authority_implementation_present": False,
        "protected_external_native_commit_broker_present": False,
        "authority_protocol_calls_authorized": False,
        "durable_commit_authorized": False,
        "production_opener_accepts_caller_authority": False,
        "production_opener_accepts_caller_catalog": False,
        "python_process_is_trust_root": False,
        "live_execution_allowed": False,
    }


def static_contract_summary() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_voluntary_gate_static_summary.v15",
        "status": "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        "v12_rejection_preserved": True,
        "v13_rejection_preserved": True,
        "v14_rejection_preserved": True,
        "v14_mutable_catalog_stale_digest_path_removed": True,
        "validator_retains_only_exact_immutable_tuple_scalars": True,
        "plan_envelope_is_exact_builtin_tuple_pair": True,
        "plan_envelope_retains_only_canonical_bytes_and_derived_sha256": True,
        "plan_digest_derived_from_envelope_bytes_before_emission": True,
        "returned_object_retains_authority_adapter_anchor_or_commit": False,
        "caller_snapshot_is_protected_authority_truth": False,
        "static_plan_is_durable_record": False,
        "authority_protocol_calls_authorized": False,
        "durable_commit_authorized": False,
        "protected_external_native_commit_broker_required": True,
        "v15_plus_v14_v13_v12_v9_v4_execution_bound": True,
        "python_class_methods_claimed_non_substitutable": False,
        "disconnected_static_only": True,
        "different_fresh_static_audit_required": True,
        "production_routing_authorized": False,
        "live_execution_allowed": False,
        "person_saw_or_heard_claimed": False,
        "person_enjoyed_learned_preferred_or_remembered_claimed": False,
    }


_BOOTSTRAP_V15.finalize_self()
