"""Static V3 repair of shared person growth primitives.

V3 is append-only and deliberately disconnected.  It replaces textual
controller identity with an exact controller-owned capability, authenticates
nonempty evidence content, binds receipts to exact scope and event intent,
uses durable CAS snapshots with explicit recovery debt, enforces exact JSON
types, and requires controller-attested fresh private roots.  It does not call
a model, write person memory, infer maturity, grant consent, activate a person,
execute an external action, or copy another person's private state.

Bounded initiative remains DESIGN_ONLY and is not implemented by this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "Data" / "foundation" / "shared_person_growth_capabilities_v3.json"
PROFILE_SCHEMA = "kira.shared_person_growth_profile.v3"
EVENT_SCHEMA = "kira.shared_person_growth_event.v3"
CREATOR_ATTACHMENT_SCHEMA = "kira.temporary_creator_growth_attachment.v3"
CONTROLLER_ENTRY_SCHEMA = "kira.shared_person_growth_controller_entry.v3"
EVIDENCE_RECEIPT_SCHEMA = "kira.shared_person_growth_evidence_receipt.v3"
MATURITY_RECEIPT_SCHEMA = "kira.shared_person_growth_maturity_receipt.v3"
RECOVERY_DEBT_SCHEMA = "kira.shared_person_growth_recovery_debt.v3"
ROLLOUT_STAGES = (
    "DESIGN_ONLY",
    "STATIC_CANDIDATE",
    "STATIC_AUDITED",
    "BOUNDED_LIVE_ACCEPTED",
    "SHARED_PERSON_ENABLED",
)
MATURITY_STATUSES = frozenset({"confirmed_adult", "non_adult", "unresolved"})
CLASSIFIED_MATURITY_STATUSES = frozenset({"confirmed_adult", "non_adult"})
PRIVACY_CLASSES = frozenset(
    {"public_shared", "person_private", "multi_person_private", "maturity_restricted"}
)
SOURCE_KINDS = frozenset(
    {
        "owner_statement",
        "reviewed_memory",
        "sensory_receipt",
        "media_receipt",
        "tool_receipt",
        "correction_receipt",
        "classification_receipt",
    }
)
EVIDENCE_PURPOSES = frozenset(
    {"present_source", "learning_review", "maturity_classification_source"}
)
CONTRADICTION_STATES = frozenset(
    {"not_checked", "no_conflict_found", "possible_conflict", "blocked_conflict"}
)
REVIEW_DECISIONS = frozenset({"accept_for_separate_memory_review", "reject", "defer"})
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_RELATIVE_ROOT_RE = re.compile(r"^Data/person_private/[a-f0-9]{32}/[a-z_]+$")
_HANDLE_CONSTRUCTION_KEY = object()


class GrowthCapabilityError(ValueError):
    """Raised when a V3 static growth record crosses a closed boundary."""


class GrowthAuthorityError(PermissionError):
    """Raised when protected controller authority is missing or mismatched."""


class GrowthLeaseError(PermissionError):
    """Raised when the exact controller-owned active lease is not presented."""


class GrowthReplayError(GrowthCapabilityError):
    """Raised when an operation, receipt, event, or session binding is replayed."""


class GrowthRecoveryDebtError(GrowthCapabilityError):
    """Raised when durable state is uncertain and explicit recovery is required."""


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_mapping(value: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _lower_sha(value: Any, field_name: str, *, nonzero: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise GrowthCapabilityError(f"{field_name} must be lowercase SHA-256")
    if nonzero and value == "0" * 64:
        raise GrowthCapabilityError(f"{field_name} must not be the zero SHA-256 sentinel")
    return value


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise GrowthCapabilityError(f"{field_name} must be a canonical identifier")
    return value


def _text(value: Any, field_name: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GrowthCapabilityError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > maximum:
        raise GrowthCapabilityError(f"{field_name} exceeds {maximum} UTF-8 bytes")
    return normalized


def _unit(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GrowthCapabilityError(f"{field_name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise GrowthCapabilityError(f"{field_name} must be from 0 to 1")
    return result


def _utc(value: Any, field_name: str) -> datetime:
    text = _text(value, field_name, 64)
    if not text.endswith("Z"):
        raise GrowthCapabilityError(f"{field_name} must be canonical UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise GrowthCapabilityError(f"{field_name} must be valid UTC") from exc
    if parsed.tzinfo != timezone.utc:
        raise GrowthCapabilityError(f"{field_name} must be UTC")
    return parsed


def _exact_keys(value: Any, expected: set[str], field_name: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise GrowthCapabilityError(f"{field_name} must be an exact JSON object")
    actual = set(value.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise GrowthCapabilityError(
            f"{field_name} schema mismatch; missing={missing!r} unknown={unknown!r}"
        )
    if any(not isinstance(key, str) for key in value):
        raise GrowthCapabilityError(f"{field_name} keys must be strings")
    return value


def _exact_bool_map(value: Any, expected: Mapping[str, bool], field_name: str) -> None:
    checked = _exact_keys(value, set(expected), field_name)
    if any(checked[key] is not expected_value for key, expected_value in expected.items()):
        raise GrowthCapabilityError(f"{field_name} closed truth values drifted")


def _typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _typed_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _typed_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GrowthCapabilityError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


_EXPECTED_CAPABILITIES = {
    "present_source_grounding": {
        "stage": "STATIC_CANDIDATE",
        "implemented_by_core": True,
        "live_enabled": False,
        "may_become_memory_automatically": False,
    },
    "learning_proposals": {
        "stage": "STATIC_CANDIDATE",
        "implemented_by_core": True,
        "live_enabled": False,
        "may_write_promoted_memory": False,
    },
    "causal_emotion_continuity": {
        "stage": "STATIC_CANDIDATE",
        "implemented_by_core": True,
        "live_enabled": False,
        "model_owns_emotion": False,
    },
    "bounded_initiative": {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
        "may_execute_external_action": False,
    },
    "vision_and_hearing": {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
    },
    "resident_media_experience": {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
    },
    "body_control": {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
    },
    "external_practical_adapters": {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
    },
}

_EXPECTED_AUTHORITY_CONTRACT = {
    "controller_owned_identity_handles": True,
    "controller_identity_exact_instance_bound": True,
    "authority_secret_required_for_issuance_and_session_open": True,
    "authority_secret_exact_32_bytes": True,
    "authority_secret_high_entropy_structure_required": True,
    "authority_secret_never_serialized": True,
    "exact_person_profile_candidate_binding": True,
    "authenticated_nonempty_source_content_required": True,
    "exact_receipt_session_event_binding": True,
    "single_use_receipts_durable_cas": True,
    "durable_cas_readback_recovery_debt": True,
    "replay_rejected": True,
    "disconnected_fails_closed": True,
}

_EXPECTED_EXACT_SCHEMA_CONTRACT = {
    "unknown_policy_fields_rejected": True,
    "unknown_profile_fields_rejected": True,
    "unknown_attachment_fields_rejected": True,
    "unknown_creator_bundle_fields_rejected": True,
    "truth_boundary_values_closed": True,
    "bool_int_substitution_rejected": True,
    "private_payload_copy_fields_rejected": True,
    "private_root_alias_rejected": True,
    "transitive_private_payload_rejected": True,
}

_EXPECTED_NEVER_INHERITED = [
    "identity",
    "memories",
    "backstory",
    "private_emotion_state",
    "preferences",
    "relationships",
    "permissions",
    "maturity_classification",
    "adult_curriculum_entitlement",
    "body_or_anatomy_selection",
    "sensory_or_media_experience",
    "capability_lease",
    "acceptance_receipt",
]

_EXPECTED_TRUTH_SEPARATION = [
    "factual_event",
    "possible_interpretation",
    "person_selected_appraisal",
    "private_emotion",
    "physiological_response",
    "private_desire",
    "preference",
    "consent",
    "public_expression",
    "external_action",
    "health_state",
    "durable_memory",
]


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_strict_json_object)
    except GrowthCapabilityError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthCapabilityError("V3 growth policy is not valid UTF-8 JSON") from exc
    top = _exact_keys(
        value,
        {
            "schema",
            "status",
            "owner_authorization_date",
            "rollout_order",
            "capabilities",
            "authority_contract",
            "exact_schema_contract",
            "never_inherited_from_another_person",
            "fresh_person_requirements",
            "maturity_rules",
            "truth_separation",
            "temporary_creator",
        },
        "policy",
    )
    if top["schema"] != "kira.shared_person_growth_capabilities_policy.v3":
        raise GrowthCapabilityError("V3 growth policy schema mismatch")
    if top["status"] != "STATIC_REPAIR_CANDIDATE_PENDING_DIFFERENT_AUDIT":
        raise GrowthCapabilityError("V3 policy status drifted")
    if top["owner_authorization_date"] != "2026-08-10":
        raise GrowthCapabilityError("V3 policy authorization date drifted")
    if top["rollout_order"] != list(ROLLOUT_STAGES):
        raise GrowthCapabilityError("V3 rollout order drifted")
    if not _typed_equal(top["capabilities"], _EXPECTED_CAPABILITIES):
        raise GrowthCapabilityError("V3 capability catalog or implementation truth drifted")
    _exact_bool_map(top["authority_contract"], _EXPECTED_AUTHORITY_CONTRACT, "authority_contract")
    _exact_bool_map(
        top["exact_schema_contract"],
        _EXPECTED_EXACT_SCHEMA_CONTRACT,
        "exact_schema_contract",
    )
    never = top["never_inherited_from_another_person"]
    if not _typed_equal(never, _EXPECTED_NEVER_INHERITED):
        raise GrowthCapabilityError("never-inherited catalog drifted")
    _exact_bool_map(
        top["fresh_person_requirements"],
        {
            "new_opaque_person_id": True,
            "new_profile_id": True,
            "new_private_state_roots": True,
            "new_controller_attested_private_roots": True,
            "new_provenance_chain": True,
            "new_controller_owned_lease_per_activation": True,
            "unknown_maturity_fails_closed": True,
            "unaccepted_features_default_off": True,
        },
        "fresh_person_requirements",
    )
    maturity = _exact_keys(
        top["maturity_rules"],
        {
            "recognized_statuses",
            "public_builder_default",
            "classified_status_requires_protected_authority_receipt",
            "confirmed_adult_curriculum_eligible",
            "adult_curriculum_delivery_is_separate_truth",
            "adult_status_does_not_add_anatomy",
            "adult_status_does_not_grant_consent",
            "non_adult_full_adult_curriculum",
            "unresolved_full_adult_curriculum",
            "non_adult_or_unresolved_body_default",
        },
        "maturity_rules",
    )
    expected_maturity = {
        "recognized_statuses": ["confirmed_adult", "non_adult", "unresolved"],
        "public_builder_default": "unresolved",
        "classified_status_requires_protected_authority_receipt": True,
        "confirmed_adult_curriculum_eligible": True,
        "adult_curriculum_delivery_is_separate_truth": True,
        "adult_status_does_not_add_anatomy": True,
        "adult_status_does_not_grant_consent": True,
        "non_adult_full_adult_curriculum": False,
        "unresolved_full_adult_curriculum": False,
        "non_adult_or_unresolved_body_default": "doll_safe_non_anatomical",
    }
    if not _typed_equal(dict(maturity), expected_maturity):
        raise GrowthCapabilityError("maturity rules drifted")
    separation = top["truth_separation"]
    if not _typed_equal(separation, _EXPECTED_TRUTH_SEPARATION):
        raise GrowthCapabilityError("truth separation catalog drifted")
    _exact_bool_map(
        top["temporary_creator"],
        {
            "must_emit_fresh_profile": True,
            "must_not_copy_person_private_data": True,
            "must_bind_exact_candidate_and_person": True,
            "must_leave_live_activation_false": True,
            "must_preserve_source_provenance": True,
            "default_maturity_is_unresolved": True,
            "classified_creation_requires_connected_protected_authority": True,
            "connected_controller_required_for_all_validation_and_write": True,
            "rollback_exact_output_on_readback_failure": True,
        },
        "temporary_creator",
    )
    return deepcopy(dict(top))


def policy_sha256(path: Path = POLICY_PATH) -> str:
    load_policy(path)
    return _sha256_bytes(path.read_bytes())


class _IdentityHandle:
    __slots__ = ()

    def __new__(cls, key: object | None = None) -> "_IdentityHandle":
        if key is not _HANDLE_CONSTRUCTION_KEY:
            raise TypeError("protected handles are controller-owned and cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("protected handles cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("protected handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("protected handles cannot be serialized")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} opaque>"


class GrowthLeaseHandle(_IdentityHandle):
    """Opaque identity-only active-session capability."""


class ControllerIdentityHandle(_IdentityHandle):
    """Opaque exact-instance controller authority capability."""


class EvidenceReceiptHandle(_IdentityHandle):
    """Opaque identity-only, single-use evidence capability."""


class MaturityAuthorityHandle(_IdentityHandle):
    """Opaque identity-only, single-use maturity authority capability."""


class FreshProfileRootsHandle(_IdentityHandle):
    """Opaque single-use attestation for newly issued private roots."""


_LEDGER_SNAPSHOT_SCHEMA = "kira.shared_person_growth_durable_ledger_snapshot.v3"


class _DurableCASLedger:
    """File-backed CAS ledger whose uncertain writes create durable recovery debt."""

    def __init__(self, ledger_id: str, state_path: Path) -> None:
        self._ledger_id = _identifier(ledger_id, "ledger_id")
        if not isinstance(state_path, Path):
            raise GrowthCapabilityError("state_path must be a pathlib.Path")
        self._state_path = state_path.resolve()
        self._debt_path = self._state_path.with_name(self._state_path.name + ".debt.json")
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[dict[str, Any]] = []
        self._operation_ids: set[str] = set()
        self._debt: dict[str, Any] | None = None
        if self._state_path.exists():
            snapshot = self._read_snapshot_path(self._state_path)
            self._records = deepcopy(snapshot["records"])
            self._operation_ids = {row["operation_id"] for row in self._records}
        else:
            initial = self._snapshot([])
            created = False
            try:
                with self._state_path.open("xb") as stream:
                    created = True
                    stream.write(_canonical_json_bytes(initial))
                    stream.flush()
                    os.fsync(stream.fileno())
                if self._read_snapshot_path(self._state_path) != initial:
                    raise GrowthCapabilityError("initial durable ledger readback mismatch")
            except Exception:
                if created and self._state_path.exists():
                    self._state_path.unlink()
                raise
        if self._debt_path.exists():
            self._debt = self._read_debt()

    @property
    def revision(self) -> int:
        return len(self._records)

    @property
    def head_sha256(self) -> str:
        return self._records[-1]["entry_sha256"] if self._records else "0" * 64

    @property
    def has_recovery_debt(self) -> bool:
        return self._debt is not None

    def recovery_debt_snapshot(self) -> dict[str, Any] | None:
        return deepcopy(self._debt)

    def _require_clear(self) -> None:
        if self._debt is not None:
            raise GrowthRecoveryDebtError(
                "durable ledger has unresolved recovery debt; no state is accepted"
            )

    def _snapshot(self, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": _LEDGER_SNAPSHOT_SCHEMA,
            "ledger_id": self._ledger_id,
            "records": deepcopy(list(records)),
        }
        body["snapshot_sha256"] = _sha256_mapping(body)
        return body

    def _read_snapshot_path(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_bytes(), object_pairs_hook=_strict_json_object)
        except GrowthCapabilityError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GrowthCapabilityError("durable ledger snapshot is unreadable") from exc
        snapshot = _exact_keys(
            value,
            {"schema", "ledger_id", "records", "snapshot_sha256"},
            "durable_ledger_snapshot",
        )
        if snapshot["schema"] != _LEDGER_SNAPSHOT_SCHEMA:
            raise GrowthCapabilityError("durable ledger snapshot schema drifted")
        if snapshot["ledger_id"] != self._ledger_id:
            raise GrowthCapabilityError("durable ledger snapshot identity drifted")
        if type(snapshot["records"]) is not list:
            raise GrowthCapabilityError("durable ledger records must be an exact list")
        digest = _lower_sha(snapshot["snapshot_sha256"], "snapshot_sha256", nonzero=True)
        unsigned = deepcopy(dict(snapshot))
        unsigned.pop("snapshot_sha256")
        if _sha256_mapping(unsigned) != digest:
            raise GrowthCapabilityError("durable ledger snapshot digest mismatch")
        self._verify_records(snapshot["records"])
        return deepcopy(dict(snapshot))

    def _verify_records(self, records: Sequence[Mapping[str, Any]]) -> None:
        previous = "0" * 64
        operations: set[str] = set()
        for index, raw in enumerate(records, start=1):
            entry = _exact_keys(
                raw,
                {
                    "schema",
                    "ledger_id",
                    "revision",
                    "operation_id",
                    "kind",
                    "binding_sha256",
                    "previous_entry_sha256",
                    "entry_sha256",
                },
                "durable_ledger_entry",
            )
            if entry["schema"] != CONTROLLER_ENTRY_SCHEMA:
                raise GrowthCapabilityError("durable ledger entry schema drifted")
            if entry["ledger_id"] != self._ledger_id:
                raise GrowthCapabilityError("durable ledger entry identity drifted")
            if type(entry["revision"]) is not int or entry["revision"] != index:
                raise GrowthCapabilityError("durable ledger revision drifted")
            if entry["previous_entry_sha256"] != previous:
                raise GrowthCapabilityError("durable ledger chain drifted")
            operation = _identifier(entry["operation_id"], "operation_id")
            if operation in operations:
                raise GrowthReplayError("durable ledger contains replayed operation")
            operations.add(operation)
            _identifier(entry["kind"], "ledger_kind")
            _lower_sha(entry["binding_sha256"], "binding_sha256", nonzero=True)
            digest = _lower_sha(entry["entry_sha256"], "entry_sha256", nonzero=True)
            unsigned = deepcopy(dict(entry))
            unsigned.pop("entry_sha256")
            if _sha256_mapping(unsigned) != digest:
                raise GrowthCapabilityError("durable ledger entry digest mismatch")
            previous = digest

    def _debt_value(
        self,
        *,
        operation_id: str,
        phase: str,
        accepted_revision_before: int,
        candidate_snapshot_sha256: str,
        error_type: str,
    ) -> dict[str, Any]:
        debt: dict[str, Any] = {
            "schema": RECOVERY_DEBT_SCHEMA,
            "ledger_id": self._ledger_id,
            "operation_id": _identifier(operation_id, "operation_id"),
            "phase": _identifier(phase, "recovery_phase"),
            "accepted_revision_before": accepted_revision_before,
            "candidate_snapshot_sha256": _lower_sha(
                candidate_snapshot_sha256,
                "candidate_snapshot_sha256",
                nonzero=True,
            ),
            "error_type": _identifier(error_type.lower(), "error_type"),
            "accepted_state": False,
            "explicit_recovery_required": True,
        }
        debt["debt_sha256"] = _sha256_mapping(debt)
        return debt

    def _read_debt(self) -> dict[str, Any]:
        try:
            value = json.loads(
                self._debt_path.read_bytes(), object_pairs_hook=_strict_json_object
            )
        except GrowthCapabilityError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GrowthRecoveryDebtError("recovery debt is unreadable") from exc
        debt = _exact_keys(
            value,
            {
                "schema",
                "ledger_id",
                "operation_id",
                "phase",
                "accepted_revision_before",
                "candidate_snapshot_sha256",
                "error_type",
                "accepted_state",
                "explicit_recovery_required",
                "debt_sha256",
            },
            "recovery_debt",
        )
        if debt["schema"] != RECOVERY_DEBT_SCHEMA or debt["ledger_id"] != self._ledger_id:
            raise GrowthRecoveryDebtError("recovery debt identity drifted")
        if type(debt["accepted_revision_before"]) is not int:
            raise GrowthRecoveryDebtError("recovery debt revision type drifted")
        if debt["accepted_state"] is not False or debt["explicit_recovery_required"] is not True:
            raise GrowthRecoveryDebtError("recovery debt truth drifted")
        digest = _lower_sha(debt["debt_sha256"], "debt_sha256", nonzero=True)
        unsigned = deepcopy(dict(debt))
        unsigned.pop("debt_sha256")
        if _sha256_mapping(unsigned) != digest:
            raise GrowthRecoveryDebtError("recovery debt digest mismatch")
        return deepcopy(dict(debt))

    def _persist_debt(self, debt: Mapping[str, Any]) -> None:
        if self._debt_path.exists():
            existing = self._read_debt()
            self._debt = existing
            return
        temp = self._debt_path.with_name(self._debt_path.name + ".next")
        created = False
        try:
            with temp.open("xb") as stream:
                created = True
                stream.write(_canonical_json_bytes(debt))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self._debt_path)
            readback = self._read_debt()
            if readback != dict(debt):
                raise GrowthRecoveryDebtError("recovery debt readback mismatch")
            self._debt = readback
        finally:
            if created and temp.exists():
                temp.unlink()

    def mark_external_recovery_debt(
        self,
        *,
        operation_id: str,
        phase: str,
        error_type: str,
    ) -> dict[str, Any]:
        snapshot = self._read_snapshot_path(self._state_path)
        if (
            not self._records
            or self._records[-1]["operation_id"] != operation_id
            or snapshot != self._snapshot(self._records)
        ):
            raise GrowthRecoveryDebtError(
                "external recovery debt does not bind the exact durable commit"
            )
        debt = self._debt_value(
            operation_id=operation_id,
            phase=phase,
            accepted_revision_before=self.revision - 1,
            candidate_snapshot_sha256=snapshot["snapshot_sha256"],
            error_type=error_type,
        )
        self._persist_debt(debt)
        return deepcopy(debt)

    def append_cas(
        self,
        *,
        expected_revision: int,
        operation_id: str,
        kind: str,
        binding_sha256: str,
    ) -> dict[str, Any]:
        self._require_clear()
        if type(expected_revision) is not int:
            raise GrowthCapabilityError("expected_revision must be an integer")
        if expected_revision != self.revision:
            raise GrowthReplayError("protected ledger compare-and-swap revision mismatch")
        operation_id = _identifier(operation_id, "operation_id")
        if operation_id in self._operation_ids:
            raise GrowthReplayError("protected ledger operation_id was already used")
        binding_sha256 = _lower_sha(binding_sha256, "binding_sha256", nonzero=True)
        entry = {
            "schema": CONTROLLER_ENTRY_SCHEMA,
            "ledger_id": self._ledger_id,
            "revision": expected_revision + 1,
            "operation_id": operation_id,
            "kind": _identifier(kind, "ledger_kind"),
            "binding_sha256": binding_sha256,
            "previous_entry_sha256": self.head_sha256,
        }
        entry["entry_sha256"] = _sha256_mapping(entry)
        candidate_records = [*deepcopy(self._records), entry]
        candidate = self._snapshot(candidate_records)
        candidate_path = self._state_path.with_name(
            self._state_path.name + f".next.{entry['entry_sha256'][:16]}"
        )
        phase = "candidate_write"
        created = False
        try:
            with candidate_path.open("xb") as stream:
                created = True
                stream.write(_canonical_json_bytes(candidate))
                stream.flush()
                os.fsync(stream.fileno())
            phase = "candidate_readback"
            if self._read_snapshot_path(candidate_path) != candidate:
                raise GrowthCapabilityError("candidate durable ledger readback mismatch")
            phase = "replace"
            os.replace(candidate_path, self._state_path)
            phase = "post_replace_readback"
            if self._read_snapshot_path(self._state_path) != candidate:
                raise GrowthCapabilityError("durable ledger post-replace readback mismatch")
        except Exception as exc:
            if created and candidate_path.exists():
                candidate_path.unlink()
            debt = self._debt_value(
                operation_id=operation_id,
                phase=phase,
                accepted_revision_before=self.revision,
                candidate_snapshot_sha256=candidate["snapshot_sha256"],
                error_type=type(exc).__name__,
            )
            self._persist_debt(debt)
            raise GrowthRecoveryDebtError(
                "durable CAS/readback is uncertain; explicit recovery debt recorded"
            ) from exc
        self._records = candidate_records
        self._operation_ids.add(operation_id)
        return deepcopy(entry)

    def readback_head(self) -> dict[str, Any]:
        self._require_clear()
        snapshot = self._read_snapshot_path(self._state_path)
        if snapshot != self._snapshot(self._records):
            raise GrowthRecoveryDebtError("durable ledger disk/readback state is uncertain")
        if not self._records:
            return {
                "ledger_id": self._ledger_id,
                "revision": 0,
                "entry_sha256": "0" * 64,
            }
        return deepcopy(self._records[-1])

    def verify_chain(self) -> None:
        self._require_clear()
        self._verify_records(self._records)
        if self._read_snapshot_path(self._state_path) != self._snapshot(self._records):
            raise GrowthRecoveryDebtError("durable ledger verification readback mismatch")

    def resolve_recovery_debt(self) -> dict[str, Any]:
        if self._debt is None:
            return {"recovery_required": False, "action": "none"}
        debt = self._read_debt()
        snapshot = self._read_snapshot_path(self._state_path)
        disk_records = snapshot["records"]
        before = debt["accepted_revision_before"]
        if len(disk_records) == before:
            action = "candidate_not_committed"
        elif (
            len(disk_records) == before + 1
            and disk_records[-1]["operation_id"] == debt["operation_id"]
            and snapshot["snapshot_sha256"] == debt["candidate_snapshot_sha256"]
        ):
            self._records = deepcopy(disk_records)
            self._operation_ids = {row["operation_id"] for row in self._records}
            action = "commit_recovered_after_explicit_readback"
        else:
            raise GrowthRecoveryDebtError("recovery debt cannot be resolved exactly")
        self._debt_path.unlink()
        self._debt = None
        return {
            "recovery_required": False,
            "action": action,
            "accepted_revision": self.revision,
            "accepted_head_sha256": self.head_sha256,
        }


class ProtectedGrowthController:
    """Exact-capability authority with durable CAS and no serialized secret."""

    def __init__(
        self,
        *,
        controller_id: str,
        authority_secret: bytes,
        ledger_root: Path,
    ) -> None:
        self.__controller_id = _identifier(controller_id, "controller_id")
        self._validate_secret(authority_secret)
        if not isinstance(ledger_root, Path):
            raise GrowthCapabilityError("ledger_root must be a pathlib.Path")
        self.__ledger_root = ledger_root.resolve()
        self.__ledger_root.mkdir(parents=True, exist_ok=True)
        self.__authority_secret = bytes(authority_secret)
        self.__identity = ControllerIdentityHandle(_HANDLE_CONSTRUCTION_KEY)
        identity_entropy = secrets.token_bytes(32)
        if type(identity_entropy) is not bytes or len(identity_entropy) != 32:
            raise GrowthAuthorityError("OS identity entropy must be exactly 32 bytes")
        self.__controller_identity_sha256 = _sha256_bytes(
            b"controller-identity-v3\x00"
            + self.__controller_id.encode("utf-8")
            + b"\x00"
            + identity_entropy
        )
        self.__lock = threading.RLock()
        authority_path = self.__ledger_root / (
            f"authority-{self.__controller_identity_sha256}.json"
        )
        self.__authority_ledger = _DurableCASLedger(
            f"authority:{self.__controller_identity_sha256[:48]}", authority_path
        )
        self.__evidence: dict[EvidenceReceiptHandle, dict[str, Any]] = {}
        self.__evidence_by_digest: dict[str, EvidenceReceiptHandle] = {}
        self.__maturity: dict[MaturityAuthorityHandle, dict[str, Any]] = {}
        self.__maturity_by_digest: dict[str, MaturityAuthorityHandle] = {}
        self.__fresh_roots: dict[FreshProfileRootsHandle, dict[str, Any]] = {}
        self.__private_root_owners: dict[str, str] = {}
        self.__profiles: dict[str, dict[str, Any]] = {}
        self.__sessions: dict[GrowthLeaseHandle, dict[str, Any]] = {}
        self.__session_bindings: set[str] = set()
        self.__rebegin_required = False

    @staticmethod
    def _validate_secret(value: Any) -> None:
        if type(value) is not bytes or len(value) != 32:
            raise GrowthAuthorityError("authority_secret must be exact bytes of length 32")
        if 0 in value or len(set(value)) < 16:
            raise GrowthAuthorityError(
                "authority_secret must contain 32 nonzero bytes and at least 16 distinct values"
            )

    @property
    def controller_id(self) -> str:
        return self.__controller_id

    @property
    def identity(self) -> ControllerIdentityHandle:
        return self.__identity

    @property
    def controller_identity_sha256(self) -> str:
        return self.__controller_identity_sha256

    def __copy__(self) -> None:
        raise TypeError("protected controllers cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("protected controllers cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("protected controllers cannot be serialized")

    def _authenticate(
        self,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
    ) -> None:
        if authority_identity is not self.__identity:
            raise GrowthAuthorityError("exact controller identity capability mismatch")
        self._validate_secret(authority_secret)
        if not hmac.compare_digest(authority_secret, self.__authority_secret):
            raise GrowthAuthorityError("protected controller authority secret mismatch")

    def _authenticator(self, value: Mapping[str, Any]) -> str:
        return hmac.new(
            self.__authority_secret,
            b"shared-person-growth-v3\x00" + _canonical_json_bytes(value),
            hashlib.sha256,
        ).hexdigest()

    def _authority_append(
        self, *, operation_id: str, kind: str, binding: Mapping[str, Any]
    ) -> dict[str, Any]:
        if self.__rebegin_required:
            raise GrowthRecoveryDebtError(
                "controller requires a controlled re-begin after recovered authority commit"
            )
        return self.__authority_ledger.append_cas(
            expected_revision=self.__authority_ledger.revision,
            operation_id=operation_id,
            kind=kind,
            binding_sha256=_sha256_mapping(binding),
        )

    def _maturity_scope_sha256(
        self, *, person_id: str, candidate_id: str, profile_id: str
    ) -> str:
        return _sha256_mapping(
            {
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": person_id,
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "scope": "maturity_authority_without_live_session",
            }
        )

    def issue_fresh_profile_roots(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
        operation_id: str,
        person_id: str,
        candidate_id: str,
        profile_id: str,
    ) -> FreshProfileRootsHandle:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            person_id = _identifier(person_id, "person_id")
            candidate_id = _identifier(candidate_id, "candidate_id")
            profile_id = _identifier(profile_id, "profile_id")
            entropy = secrets.token_bytes(32)
            if type(entropy) is not bytes or len(entropy) != 32:
                raise GrowthAuthorityError("OS root entropy must be exactly 32 bytes")
            token = hmac.new(
                self.__authority_secret,
                b"fresh-private-roots-v3\x00"
                + self.__controller_identity_sha256.encode("ascii")
                + b"\x00"
                + person_id.encode("utf-8")
                + b"\x00"
                + candidate_id.encode("utf-8")
                + b"\x00"
                + profile_id.encode("utf-8")
                + b"\x00"
                + entropy,
                hashlib.sha256,
            ).hexdigest()[:32]
            roots = {
                "present_context": f"Data/person_private/{token}/present_context",
                "learning_proposals": f"Data/person_private/{token}/learning_proposals",
                "emotion": f"Data/person_private/{token}/emotion",
                "initiative": f"Data/person_private/{token}/initiative",
                "memory_review": f"Data/person_private/{token}/memory_review",
            }
            if any(root in self.__private_root_owners for root in roots.values()):
                raise GrowthReplayError("fresh private roots alias an existing profile")
            attestation_body = {
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": person_id,
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "private_roots_sha256": _sha256_mapping(roots),
                "issue_operation_id": _identifier(operation_id, "operation_id"),
            }
            attestation_sha256 = self._authenticator(attestation_body)
            record = {
                **attestation_body,
                "roots": roots,
                "fresh_root_attestation_sha256": attestation_sha256,
                "consumed": False,
                "consumed_by_profile_sha256": None,
            }
            self._authority_append(
                operation_id=operation_id,
                kind="fresh_roots_issue",
                binding={
                    **attestation_body,
                    "fresh_root_attestation_sha256": attestation_sha256,
                },
            )
            handle = FreshProfileRootsHandle(_HANDLE_CONSTRUCTION_KEY)
            self.__fresh_roots[handle] = record
            return handle

    def _peek_fresh_roots(
        self,
        handle: FreshProfileRootsHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
    ) -> dict[str, Any]:
        if type(handle) is not FreshProfileRootsHandle or handle not in self.__fresh_roots:
            raise GrowthAuthorityError("fresh-root handle is not owned by this controller")
        record = self.__fresh_roots[handle]
        if record["consumed"]:
            raise GrowthReplayError("fresh-root authority was already consumed")
        for field, expected in {
            "person_id": _identifier(person_id, "person_id"),
            "candidate_id": _identifier(candidate_id, "candidate_id"),
            "profile_id": _identifier(profile_id, "profile_id"),
        }.items():
            if record[field] != expected:
                raise GrowthAuthorityError("fresh-root exact binding mismatch")
        return deepcopy(record)

    def issue_evidence_receipt(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
        operation_id: str,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        purpose: str,
        source_kind: str,
        source_content: bytes,
        source_revision: str,
        event_binding_id: str,
        session: "PersonGrowthSession | None" = None,
        lease: GrowthLeaseHandle | None = None,
    ) -> EvidenceReceiptHandle:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            person_id = _identifier(person_id, "person_id")
            candidate_id = _identifier(candidate_id, "candidate_id")
            profile_id = _identifier(profile_id, "profile_id")
            event_binding_id = _identifier(event_binding_id, "event_binding_id")
            if purpose not in EVIDENCE_PURPOSES:
                raise GrowthCapabilityError("evidence purpose is unsupported")
            if source_kind not in SOURCE_KINDS:
                raise GrowthCapabilityError("source_kind is unsupported")
            if type(source_content) is not bytes or not source_content:
                raise GrowthCapabilityError("source_content must be exact nonempty bytes")
            if len(source_content) > 8 * 1024 * 1024:
                raise GrowthCapabilityError("source_content exceeds the bounded receipt limit")
            if purpose == "maturity_classification_source":
                if session is not None or lease is not None:
                    raise GrowthAuthorityError("maturity evidence must use its authority scope")
                if source_kind != "classification_receipt":
                    raise GrowthAuthorityError(
                        "maturity evidence requires source_kind=classification_receipt"
                    )
                session_binding_sha256 = self._maturity_scope_sha256(
                    person_id=person_id,
                    candidate_id=candidate_id,
                    profile_id=profile_id,
                )
            else:
                if session is None or lease is None:
                    raise GrowthAuthorityError("session evidence requires exact session and lease")
                active = self._require_session(session=session, lease=lease)
                for field, expected in {
                    "person_id": person_id,
                    "candidate_id": candidate_id,
                    "profile_id": profile_id,
                }.items():
                    if active[field] != expected:
                        raise GrowthAuthorityError("evidence person/profile/session mismatch")
                session_binding_sha256 = active["session_binding_sha256"]
            body: dict[str, Any] = {
                "schema": EVIDENCE_RECEIPT_SCHEMA,
                "controller_id": self.controller_id,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": person_id,
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "purpose": purpose,
                "source_kind": source_kind,
                "source_content_sha256": _sha256_bytes(source_content),
                "source_content_bytes": len(source_content),
                "source_revision": _identifier(source_revision, "source_revision"),
                "session_binding_sha256": session_binding_sha256,
                "event_binding_id": event_binding_id,
                "issue_operation_id": _identifier(operation_id, "operation_id"),
                "single_use": True,
                "content_was_present_at_issue": True,
            }
            body["source_authenticator_sha256"] = self._authenticator(body)
            body["receipt_sha256"] = _sha256_mapping(body)
            self._authority_append(
                operation_id=operation_id,
                kind="evidence_issue",
                binding=body,
            )
            handle = EvidenceReceiptHandle(_HANDLE_CONSTRUCTION_KEY)
            stored = deepcopy(body)
            stored["consumed"] = False
            stored["consumed_by"] = None
            self.__evidence[handle] = stored
            self.__evidence_by_digest[body["receipt_sha256"]] = handle
            return handle

    def _peek_evidence(
        self,
        handle: EvidenceReceiptHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        purpose: str,
        source_kind: str,
        session_binding_sha256: str,
        event_binding_id: str,
    ) -> dict[str, Any]:
        if type(handle) is not EvidenceReceiptHandle or handle not in self.__evidence:
            raise GrowthAuthorityError("evidence handle is not owned by this controller")
        record = self.__evidence[handle]
        if record["consumed"]:
            raise GrowthReplayError("evidence receipt was already consumed")
        expected = {
            "person_id": _identifier(person_id, "person_id"),
            "candidate_id": _identifier(candidate_id, "candidate_id"),
            "profile_id": _identifier(profile_id, "profile_id"),
            "purpose": purpose,
            "source_kind": source_kind,
            "session_binding_sha256": _lower_sha(
                session_binding_sha256, "session_binding_sha256", nonzero=True
            ),
            "event_binding_id": _identifier(event_binding_id, "event_binding_id"),
        }
        if any(record[field] != value for field, value in expected.items()):
            raise GrowthAuthorityError("evidence receipt exact scope/event binding mismatch")
        public = {
            key: deepcopy(value)
            for key, value in record.items()
            if key not in {"consumed", "consumed_by"}
        }
        unsigned_auth = deepcopy(public)
        receipt_sha = unsigned_auth.pop("receipt_sha256")
        authenticator = unsigned_auth.pop("source_authenticator_sha256")
        if self._authenticator(unsigned_auth) != authenticator:
            raise GrowthAuthorityError("evidence content authenticator mismatch")
        rebuilt = {**unsigned_auth, "source_authenticator_sha256": authenticator}
        if _sha256_mapping(rebuilt) != receipt_sha:
            raise GrowthAuthorityError("evidence receipt digest mismatch")
        return public

    def _consume_evidence(
        self,
        handle: EvidenceReceiptHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        purpose: str,
        source_kind: str,
        session_binding_sha256: str,
        event_binding_id: str,
        use_operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._peek_evidence(
                handle,
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
                purpose=purpose,
                source_kind=source_kind,
                session_binding_sha256=session_binding_sha256,
                event_binding_id=event_binding_id,
            )
            use_operation_id = _identifier(use_operation_id, "use_operation_id")
            self._authority_append(
                operation_id=use_operation_id,
                kind="evidence_consume",
                binding={
                    "receipt_sha256": record["receipt_sha256"],
                    "controller_identity_sha256": self.__controller_identity_sha256,
                    "person_id": record["person_id"],
                    "candidate_id": record["candidate_id"],
                    "profile_id": record["profile_id"],
                    "purpose": record["purpose"],
                    "source_kind": record["source_kind"],
                    "session_binding_sha256": record["session_binding_sha256"],
                    "event_binding_id": record["event_binding_id"],
                    "use_operation_id": use_operation_id,
                },
            )
            stored = self.__evidence[handle]
            stored["consumed"] = True
            stored["consumed_by"] = use_operation_id
            return record

    def issue_maturity_classification(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
        operation_id: str,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        status: str,
        source_evidence: EvidenceReceiptHandle,
        classification_revision: str,
    ) -> MaturityAuthorityHandle:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            if status not in CLASSIFIED_MATURITY_STATUSES:
                raise GrowthCapabilityError("protected maturity status must be classified")
            operation_id = _identifier(operation_id, "operation_id")
            classification_revision = _identifier(
                classification_revision, "classification_revision"
            )
            person_id = _identifier(person_id, "person_id")
            candidate_id = _identifier(candidate_id, "candidate_id")
            profile_id = _identifier(profile_id, "profile_id")
            scope = self._maturity_scope_sha256(
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
            )
            source = self._peek_evidence(
                source_evidence,
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
                purpose="maturity_classification_source",
                source_kind="classification_receipt",
                session_binding_sha256=scope,
                event_binding_id=classification_revision,
            )
            body: dict[str, Any] = {
                "schema": MATURITY_RECEIPT_SCHEMA,
                "controller_id": self.controller_id,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": person_id,
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "status": status,
                "source_evidence_receipt_sha256": source["receipt_sha256"],
                "source_kind": source["source_kind"],
                "source_content_sha256": source["source_content_sha256"],
                "source_content_bytes": source["source_content_bytes"],
                "source_session_binding_sha256": source[
                    "session_binding_sha256"
                ],
                "source_event_binding_id": source["event_binding_id"],
                "classification_revision": classification_revision,
                "issue_operation_id": operation_id,
                "single_use_profile_binding": True,
                "classification_inferred_by_module": False,
            }
            body["authority_authenticator_sha256"] = self._authenticator(body)
            body["receipt_sha256"] = _sha256_mapping(body)
            self._authority_append(
                operation_id=operation_id,
                kind="maturity_issue_and_evidence_consume",
                binding={
                    "maturity_receipt": body,
                    "consumed_source_receipt_sha256": source["receipt_sha256"],
                    "consumed_source_kind": source["source_kind"],
                    "consumed_source_session_binding_sha256": source[
                        "session_binding_sha256"
                    ],
                    "consumed_source_event_binding_id": source["event_binding_id"],
                    "single_durable_cas": True,
                },
            )
            source_stored = self.__evidence[source_evidence]
            source_stored["consumed"] = True
            source_stored["consumed_by"] = operation_id
            handle = MaturityAuthorityHandle(_HANDLE_CONSTRUCTION_KEY)
            stored = deepcopy(body)
            stored["consumed"] = False
            stored["consumed_by_profile_sha256"] = None
            self.__maturity[handle] = stored
            self.__maturity_by_digest[body["receipt_sha256"]] = handle
            return handle

    def _peek_maturity(
        self,
        handle: MaturityAuthorityHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
    ) -> dict[str, Any]:
        if type(handle) is not MaturityAuthorityHandle or handle not in self.__maturity:
            raise GrowthAuthorityError("maturity handle is not owned by this controller")
        record = self.__maturity[handle]
        if record["consumed"]:
            raise GrowthReplayError("maturity authority receipt was already consumed")
        for field, value in {
            "person_id": _identifier(person_id, "person_id"),
            "candidate_id": _identifier(candidate_id, "candidate_id"),
            "profile_id": _identifier(profile_id, "profile_id"),
        }.items():
            if record[field] != value:
                raise GrowthAuthorityError("maturity authority exact binding mismatch")
        return {
            key: deepcopy(value)
            for key, value in record.items()
            if key not in {"consumed", "consumed_by_profile_sha256"}
        }

    def _register_profile(
        self,
        profile: Mapping[str, Any],
        *,
        fresh_root_handle: FreshProfileRootsHandle,
        maturity_handle: MaturityAuthorityHandle | None,
    ) -> None:
        with self.__lock:
            fingerprint = _lower_sha(
                profile.get("profile_fingerprint_sha256"),
                "profile_fingerprint_sha256",
                nonzero=True,
            )
            if fingerprint in self.__profiles:
                raise GrowthReplayError("profile fingerprint was already registered")
            binding = profile["person_binding"]
            roots = self._peek_fresh_roots(
                fresh_root_handle,
                person_id=binding["person_id"],
                candidate_id=binding["candidate_id"],
                profile_id=profile["profile_id"],
            )
            if profile["private_state_roots"] != roots["roots"]:
                raise GrowthAuthorityError("profile private roots do not match fresh attestation")
            if (
                profile["authority_binding"]["fresh_root_attestation_sha256"]
                != roots["fresh_root_attestation_sha256"]
            ):
                raise GrowthAuthorityError("profile fresh-root attestation mismatch")
            for root in roots["roots"].values():
                if root in self.__private_root_owners:
                    raise GrowthReplayError("profile aliases an existing private root")
            maturity = profile["maturity"]
            maturity_record: dict[str, Any] | None = None
            if maturity_handle is None:
                if (
                    maturity["status"] != "unresolved"
                    or maturity["classification_receipt_sha256"] is not None
                ):
                    raise GrowthAuthorityError("classified profile lacks protected maturity handle")
            else:
                maturity_record = self._peek_maturity(
                    maturity_handle,
                    person_id=binding["person_id"],
                    candidate_id=binding["candidate_id"],
                    profile_id=profile["profile_id"],
                )
                if (
                    maturity["status"] != maturity_record["status"]
                    or maturity["classification_receipt_sha256"]
                    != maturity_record["receipt_sha256"]
                ):
                    raise GrowthAuthorityError("profile maturity receipt binding mismatch")
            register_binding = {
                "profile_fingerprint_sha256": fingerprint,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": profile["profile_id"],
                "private_roots_sha256": _sha256_mapping(profile["private_state_roots"]),
                "fresh_root_attestation_sha256": roots[
                    "fresh_root_attestation_sha256"
                ],
                "maturity_receipt_sha256": (
                    maturity_record["receipt_sha256"] if maturity_record else None
                ),
            }
            self._authority_append(
                operation_id=f"profile-register:{profile['profile_id']}",
                kind="profile_register_and_consume_authorities",
                binding=register_binding,
            )
            root_stored = self.__fresh_roots[fresh_root_handle]
            root_stored["consumed"] = True
            root_stored["consumed_by_profile_sha256"] = fingerprint
            for root in roots["roots"].values():
                self.__private_root_owners[root] = fingerprint
            if maturity_handle is not None:
                maturity_stored = self.__maturity[maturity_handle]
                maturity_stored["consumed"] = True
                maturity_stored["consumed_by_profile_sha256"] = fingerprint
            self.__profiles[fingerprint] = {
                **register_binding,
                "maturity_status": maturity["status"],
            }

    def _verify_registered_profile(self, profile: Mapping[str, Any]) -> None:
        with self.__lock:
            fingerprint = profile["profile_fingerprint_sha256"]
            registered = self.__profiles.get(fingerprint)
            if registered is None:
                raise GrowthAuthorityError("profile is not registered to this exact controller")
            binding = profile["person_binding"]
            expected = {
                "profile_fingerprint_sha256": fingerprint,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": profile["profile_id"],
                "private_roots_sha256": _sha256_mapping(profile["private_state_roots"]),
                "fresh_root_attestation_sha256": profile["authority_binding"][
                    "fresh_root_attestation_sha256"
                ],
                "maturity_receipt_sha256": profile["maturity"][
                    "classification_receipt_sha256"
                ],
                "maturity_status": profile["maturity"]["status"],
            }
            if registered != expected:
                raise GrowthAuthorityError("registered profile exact binding mismatch")
            for root in profile["private_state_roots"].values():
                if self.__private_root_owners.get(root) != fingerprint:
                    raise GrowthAuthorityError("registered profile private-root owner mismatch")

    def open_session(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
        profile: Mapping[str, Any],
        activation_revision: str,
        session_open_operation_id: str,
        clock: Callable[[], float],
        max_events: int = 128,
    ) -> "PersonGrowthSession":
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            checked = validate_capability_profile(
                profile,
                authority_controller=self,
                authority_identity=authority_identity,
            )
            activation_revision = _identifier(activation_revision, "activation_revision")
            session_open_operation_id = _identifier(
                session_open_operation_id, "session_open_operation_id"
            )
            if not callable(clock):
                raise GrowthCapabilityError("clock must be callable")
            if type(max_events) is not int or not 1 <= max_events <= 512:
                raise GrowthCapabilityError("max_events must be an integer from 1 to 512")
            nonce = secrets.token_bytes(32)
            if type(nonce) is not bytes or len(nonce) != 32:
                raise GrowthAuthorityError("OS session entropy must be exactly 32 bytes")
            session_nonce_sha256 = _sha256_bytes(nonce)
            binding = checked["person_binding"]
            session_binding = {
                "controller_id": self.controller_id,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": checked["profile_id"],
                "profile_fingerprint_sha256": checked["profile_fingerprint_sha256"],
                "activation_revision": activation_revision,
                "session_nonce_sha256": session_nonce_sha256,
            }
            session_binding_sha256 = _sha256_mapping(session_binding)
            if session_binding_sha256 in self.__session_bindings:
                raise GrowthReplayError("exact session binding was already opened")
            lease = GrowthLeaseHandle(_HANDLE_CONSTRUCTION_KEY)
            session_path = self.__ledger_root / (
                f"session-{session_binding_sha256}.json"
            )
            session_ledger = _DurableCASLedger(
                f"session:{session_binding_sha256[:48]}", session_path
            )
            self._authority_append(
                operation_id=session_open_operation_id,
                kind="session_open",
                binding=session_binding,
            )
            session = PersonGrowthSession(
                _construction_key=_HANDLE_CONSTRUCTION_KEY,
                controller=self,
                lease=lease,
                profile=checked,
                activation_revision=activation_revision,
                session_nonce_sha256=session_nonce_sha256,
                session_binding_sha256=session_binding_sha256,
                clock=clock,
                max_events=max_events,
            )
            self.__sessions[lease] = {
                "session": session,
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": checked["profile_id"],
                "profile_fingerprint_sha256": checked["profile_fingerprint_sha256"],
                "activation_revision": activation_revision,
                "session_binding_sha256": session_binding_sha256,
                "ledger": session_ledger,
                "active": True,
            }
            self.__session_bindings.add(session_binding_sha256)
            return session

    def _require_session(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
    ) -> dict[str, Any]:
        if type(lease) is not GrowthLeaseHandle or lease not in self.__sessions:
            raise GrowthLeaseError("lease is not owned by this controller")
        record = self.__sessions[lease]
        if record["session"] is not session or record["active"] is not True:
            raise GrowthLeaseError("lease does not bind the exact active session instance")
        return record

    def _commit_session_event(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        expected_revision: int,
        operation_id: str,
        kind: str,
        event_sha256: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            ledger: _DurableCASLedger = record["ledger"]
            return ledger.append_cas(
                expected_revision=expected_revision,
                operation_id=operation_id,
                kind=kind,
                binding_sha256=_lower_sha(event_sha256, "event_sha256", nonzero=True),
            )

    def _session_readback(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            ledger: _DurableCASLedger = record["ledger"]
            return ledger.readback_head()

    def _peek_session_evidence(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        handle: EvidenceReceiptHandle,
        purpose: str,
        source_kind: str,
        event_binding_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            return self._peek_evidence(
                handle,
                person_id=record["person_id"],
                candidate_id=record["candidate_id"],
                profile_id=record["profile_id"],
                purpose=purpose,
                source_kind=source_kind,
                session_binding_sha256=record["session_binding_sha256"],
                event_binding_id=event_binding_id,
            )

    def _consume_session_evidence(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        handle: EvidenceReceiptHandle,
        purpose: str,
        source_kind: str,
        event_binding_id: str,
        use_operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            return self._consume_evidence(
                handle,
                person_id=record["person_id"],
                candidate_id=record["candidate_id"],
                profile_id=record["profile_id"],
                purpose=purpose,
                source_kind=source_kind,
                session_binding_sha256=record["session_binding_sha256"],
                event_binding_id=event_binding_id,
                use_operation_id=use_operation_id,
            )

    def _mark_session_transaction_debt(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        operation_id: str,
        event_sha256: str,
        error_type: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            ledger: _DurableCASLedger = record["ledger"]
            return ledger.mark_external_recovery_debt(
                operation_id=operation_id,
                phase="event_committed_receipt_consume_uncertain",
                error_type=error_type,
            )

    def _close_session(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        close_operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            record = self._require_session(session=session, lease=lease)
            ledger: _DurableCASLedger = record["ledger"]
            ledger.verify_chain()
            self._authority_append(
                operation_id=_identifier(close_operation_id, "close_operation_id"),
                kind="session_close",
                binding={
                    "session_binding_sha256": record["session_binding_sha256"],
                    "session_revision": ledger.revision,
                    "session_head_sha256": ledger.head_sha256,
                },
            )
            record["active"] = False
            return {
                "session_revision": ledger.revision,
                "session_head_sha256": ledger.head_sha256,
            }

    def protected_recovery_debt_snapshot(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
    ) -> dict[str, Any]:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            return {
                "authority": self.__authority_ledger.recovery_debt_snapshot(),
                "sessions": [
                    {
                        "session_binding_sha256": row["session_binding_sha256"],
                        "debt": row["ledger"].recovery_debt_snapshot(),
                    }
                    for row in self.__sessions.values()
                    if row["ledger"].has_recovery_debt
                ],
                "accepted_state_from_debt": False,
            }

    def recover_durable_state(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
        session: "PersonGrowthSession | None" = None,
        lease: GrowthLeaseHandle | None = None,
    ) -> dict[str, Any]:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            authority_result = self.__authority_ledger.resolve_recovery_debt()
            if authority_result.get("action") == "commit_recovered_after_explicit_readback":
                self.__rebegin_required = True
            session_result: dict[str, Any] | None = None
            if session is not None or lease is not None:
                if session is None or lease is None:
                    raise GrowthLeaseError("recovery requires both exact session and lease")
                record = self._require_session(session=session, lease=lease)
                session_result = record["ledger"].resolve_recovery_debt()
                if session_result.get("action") == "commit_recovered_after_explicit_readback":
                    record["active"] = False
                    session._quarantine_after_recovery()
            return {
                "authority": authority_result,
                "session": session_result,
                "explicit_recovery_performed": True,
            }

    def protected_audit_snapshot(
        self,
        *,
        authority_identity: ControllerIdentityHandle,
        authority_secret: bytes,
    ) -> dict[str, Any]:
        with self.__lock:
            self._authenticate(authority_identity, authority_secret)
            self.__authority_ledger.verify_chain()
            for record in self.__sessions.values():
                record["ledger"].verify_chain()
            return {
                "schema": "kira.shared_person_growth_controller_snapshot.v3",
                "controller_id": self.controller_id,
                "controller_identity_sha256": self.__controller_identity_sha256,
                "authority_revision": self.__authority_ledger.revision,
                "authority_head_sha256": self.__authority_ledger.head_sha256,
                "registered_profile_count": len(self.__profiles),
                "issued_evidence_count": len(self.__evidence),
                "issued_maturity_count": len(self.__maturity),
                "issued_fresh_root_count": len(self.__fresh_roots),
                "session_count": len(self.__sessions),
                "active_session_count": sum(
                    1 for record in self.__sessions.values() if record["active"]
                ),
                "authority_secret_serialized": False,
                "controlled_rebegin_required": self.__rebegin_required,
                "private_payload_exposed": False,
                "durable_memory_connected": False,
                "external_actions_connected": False,
            }


_PROFILE_KEYS = {
    "schema",
    "profile_id",
    "person_binding",
    "policy",
    "authority_binding",
    "maturity",
    "private_state_roots",
    "capabilities",
    "truth_boundaries",
    "inheritance",
    "runtime",
    "profile_fingerprint_sha256",
}
_PERSON_BINDING_KEYS = {
    "person_id",
    "candidate_id",
    "person_and_candidate_are_distinct_bindings",
    "owner_or_name_equivalence_grants_nothing",
}
_POLICY_BINDING_KEYS = {"path", "sha256", "stage"}
_AUTHORITY_BINDING_KEYS = {
    "controller_id",
    "controller_identity_sha256",
    "fresh_root_attestation_sha256",
    "exact_controller_identity_capability_required",
    "controller_registration_required_for_activation",
    "plain_digest_is_not_authority",
}
_MATURITY_KEYS = {
    "status",
    "classification_receipt_sha256",
    "classification_controller_id",
    "classification_controller_identity_sha256",
    "classification_inferred_by_this_module",
    "full_adult_curriculum_eligible",
    "full_adult_curriculum_delivered",
    "adult_anatomy_added",
    "consent_granted",
    "default_body_lane",
}
_ROOT_KEYS = {
    "present_context",
    "learning_proposals",
    "emotion",
    "initiative",
    "memory_review",
}
_TRUTH_BOUNDARIES = {
    "model_output_is_advisory": True,
    "present_context_is_not_memory": True,
    "learning_proposal_is_not_promoted_memory": True,
    "private_emotion_is_not_public_speech": True,
    "body_response_is_not_desire_or_consent": True,
    "permission_is_not_relationship_or_preference": True,
    "opening_media_is_not_experience": True,
}
_INHERITANCE_KEYS = {
    "shared_code_and_schema_only",
    "never_inherited",
    "source_person_id",
    "source_profile_id",
    "copied_private_records",
    "copied_capability_leases",
    "copied_acceptance_receipts",
}
_RUNTIME_FALSE = {
    "activated": False,
    "model_connected": False,
    "memory_writer_connected": False,
    "external_actions_connected": False,
    "sensory_devices_connected": False,
    "media_playback_connected": False,
    "body_control_connected": False,
}


def build_fresh_capability_profile(
    *,
    person_id: str,
    candidate_id: str,
    profile_id: str,
    authority_controller: ProtectedGrowthController,
    authority_identity: ControllerIdentityHandle,
    fresh_root_authority: FreshProfileRootsHandle,
    maturity_authority: MaturityAuthorityHandle | None = None,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    """Build one exact fresh profile; public default is always unresolved."""

    if type(authority_controller) is not ProtectedGrowthController:
        raise GrowthAuthorityError("a protected controller is required")
    if authority_identity is not authority_controller.identity:
        raise GrowthAuthorityError("exact controller identity capability is required")
    person_id = _identifier(person_id, "person_id")
    candidate_id = _identifier(candidate_id, "candidate_id")
    profile_id = _identifier(profile_id, "profile_id")
    policy = load_policy(policy_path)
    root_record = authority_controller._peek_fresh_roots(
        fresh_root_authority,
        person_id=person_id,
        candidate_id=candidate_id,
        profile_id=profile_id,
    )
    if maturity_authority is None:
        maturity_status = "unresolved"
        maturity_receipt_sha256: str | None = None
    else:
        maturity_record = authority_controller._peek_maturity(
            maturity_authority,
            person_id=person_id,
            candidate_id=candidate_id,
            profile_id=profile_id,
        )
        maturity_status = maturity_record["status"]
        maturity_receipt_sha256 = maturity_record["receipt_sha256"]
    profile: dict[str, Any] = {
        "schema": PROFILE_SCHEMA,
        "profile_id": profile_id,
        "person_binding": {
            "person_id": person_id,
            "candidate_id": candidate_id,
            "person_and_candidate_are_distinct_bindings": True,
            "owner_or_name_equivalence_grants_nothing": True,
        },
        "policy": {
            "path": policy_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": policy_sha256(policy_path),
            "stage": "STATIC_CANDIDATE",
        },
        "authority_binding": {
            "controller_id": authority_controller.controller_id,
            "controller_identity_sha256": (
                authority_controller.controller_identity_sha256
            ),
            "fresh_root_attestation_sha256": root_record[
                "fresh_root_attestation_sha256"
            ],
            "exact_controller_identity_capability_required": True,
            "controller_registration_required_for_activation": True,
            "plain_digest_is_not_authority": True,
        },
        "maturity": {
            "status": maturity_status,
            "classification_receipt_sha256": maturity_receipt_sha256,
            "classification_controller_id": (
                authority_controller.controller_id if maturity_receipt_sha256 else None
            ),
            "classification_controller_identity_sha256": (
                authority_controller.controller_identity_sha256
                if maturity_receipt_sha256
                else None
            ),
            "classification_inferred_by_this_module": False,
            "full_adult_curriculum_eligible": maturity_status == "confirmed_adult",
            "full_adult_curriculum_delivered": False,
            "adult_anatomy_added": False,
            "consent_granted": False,
            "default_body_lane": (
                "separately_selected_adult_body_pending"
                if maturity_status == "confirmed_adult"
                else "doll_safe_non_anatomical"
            ),
        },
        "private_state_roots": deepcopy(root_record["roots"]),
        "capabilities": deepcopy(policy["capabilities"]),
        "truth_boundaries": deepcopy(_TRUTH_BOUNDARIES),
        "inheritance": {
            "shared_code_and_schema_only": True,
            "never_inherited": list(policy["never_inherited_from_another_person"]),
            "source_person_id": None,
            "source_profile_id": None,
            "copied_private_records": 0,
            "copied_capability_leases": 0,
            "copied_acceptance_receipts": 0,
        },
        "runtime": deepcopy(_RUNTIME_FALSE),
    }
    profile["profile_fingerprint_sha256"] = _sha256_mapping(profile)
    _validate_capability_profile_structure(profile, policy_path=policy_path)
    authority_controller._register_profile(
        profile,
        fresh_root_handle=fresh_root_authority,
        maturity_handle=maturity_authority,
    )
    return validate_capability_profile(
        profile,
        policy_path=policy_path,
        authority_controller=authority_controller,
        authority_identity=authority_identity,
    )


def _validate_capability_profile_structure(
    profile: Mapping[str, Any], *, policy_path: Path = POLICY_PATH
) -> dict[str, Any]:
    value = _exact_keys(profile, _PROFILE_KEYS, "capability_profile")
    if value["schema"] != PROFILE_SCHEMA:
        raise GrowthCapabilityError("capability profile schema mismatch")
    profile_id = _identifier(value["profile_id"], "profile_id")
    person = _exact_keys(value["person_binding"], _PERSON_BINDING_KEYS, "person_binding")
    _identifier(person["person_id"], "person_id")
    _identifier(person["candidate_id"], "candidate_id")
    if person["person_and_candidate_are_distinct_bindings"] is not True:
        raise GrowthCapabilityError("person/candidate exact binding truth drifted")
    if person["owner_or_name_equivalence_grants_nothing"] is not True:
        raise GrowthCapabilityError("owner/name equivalence boundary drifted")
    policy = _exact_keys(value["policy"], _POLICY_BINDING_KEYS, "policy_binding")
    expected_policy_path = policy_path.relative_to(PROJECT_ROOT).as_posix()
    if policy["path"] != expected_policy_path:
        raise GrowthCapabilityError("policy path binding mismatch")
    if policy["sha256"] != policy_sha256(policy_path) or policy["stage"] != "STATIC_CANDIDATE":
        raise GrowthCapabilityError("policy hash or stage binding mismatch")
    authority = _exact_keys(
        value["authority_binding"], _AUTHORITY_BINDING_KEYS, "authority_binding"
    )
    _identifier(authority["controller_id"], "controller_id")
    _lower_sha(
        authority["controller_identity_sha256"],
        "controller_identity_sha256",
        nonzero=True,
    )
    _lower_sha(
        authority["fresh_root_attestation_sha256"],
        "fresh_root_attestation_sha256",
        nonzero=True,
    )
    if authority["exact_controller_identity_capability_required"] is not True:
        raise GrowthCapabilityError("exact controller identity boundary drifted")
    if authority["controller_registration_required_for_activation"] is not True:
        raise GrowthCapabilityError("controller registration boundary drifted")
    if authority["plain_digest_is_not_authority"] is not True:
        raise GrowthCapabilityError("plain-digest authority boundary drifted")
    maturity = _exact_keys(value["maturity"], _MATURITY_KEYS, "maturity")
    status = maturity["status"]
    if status not in MATURITY_STATUSES:
        raise GrowthCapabilityError("maturity status is unsupported")
    if maturity["classification_inferred_by_this_module"] is not False:
        raise GrowthCapabilityError("this module must not infer maturity")
    if maturity["full_adult_curriculum_eligible"] is not (status == "confirmed_adult"):
        raise GrowthCapabilityError("adult curriculum eligibility drifted")
    for field in (
        "full_adult_curriculum_delivered",
        "adult_anatomy_added",
        "consent_granted",
    ):
        if maturity[field] is not False:
            raise GrowthCapabilityError(f"{field} cannot be inferred or inherited")
    expected_lane = (
        "separately_selected_adult_body_pending"
        if status == "confirmed_adult"
        else "doll_safe_non_anatomical"
    )
    if maturity["default_body_lane"] != expected_lane:
        raise GrowthCapabilityError("maturity body lane drifted")
    if status == "unresolved":
        if maturity["classification_receipt_sha256"] is not None:
            raise GrowthCapabilityError("unresolved maturity must not claim a receipt")
        if maturity["classification_controller_id"] is not None:
            raise GrowthCapabilityError("unresolved maturity must not claim a classifier")
        if maturity["classification_controller_identity_sha256"] is not None:
            raise GrowthCapabilityError("unresolved maturity must not claim classifier identity")
    else:
        _lower_sha(
            maturity["classification_receipt_sha256"],
            "classification_receipt_sha256",
            nonzero=True,
        )
        if maturity["classification_controller_id"] != authority["controller_id"]:
            raise GrowthCapabilityError("maturity controller binding mismatch")
        if (
            maturity["classification_controller_identity_sha256"]
            != authority["controller_identity_sha256"]
        ):
            raise GrowthCapabilityError("maturity controller identity binding mismatch")
    roots = _exact_keys(value["private_state_roots"], _ROOT_KEYS, "private_state_roots")
    root_values = list(roots.values())
    if len(set(root_values)) != len(root_values):
        raise GrowthCapabilityError("private state roots must be distinct")
    prefixes: set[str] = set()
    for root in root_values:
        if not isinstance(root, str) or _RELATIVE_ROOT_RE.fullmatch(root) is None:
            raise GrowthCapabilityError("private state root is not canonical")
        prefixes.add(root.rsplit("/", 1)[0])
    if len(prefixes) != 1:
        raise GrowthCapabilityError("private state roots cross person namespaces")
    if not _typed_equal(value["capabilities"], load_policy(policy_path)["capabilities"]):
        raise GrowthCapabilityError("capability catalog drifted from policy")
    _exact_bool_map(value["truth_boundaries"], _TRUTH_BOUNDARIES, "truth_boundaries")
    inheritance = _exact_keys(
        value["inheritance"], _INHERITANCE_KEYS, "inheritance"
    )
    if inheritance["shared_code_and_schema_only"] is not True:
        raise GrowthCapabilityError("only code and schema may be shared")
    if not _typed_equal(
        inheritance["never_inherited"],
        load_policy(policy_path)["never_inherited_from_another_person"],
    ):
        raise GrowthCapabilityError("never-inherited catalog drifted")
    if inheritance["source_person_id"] is not None or inheritance["source_profile_id"] is not None:
        raise GrowthCapabilityError("fresh profile must not name a source person/profile")
    for field in (
        "copied_private_records",
        "copied_capability_leases",
        "copied_acceptance_receipts",
    ):
        if type(inheritance[field]) is not int or inheritance[field] != 0:
            raise GrowthCapabilityError("person-private inheritance is forbidden")
    _exact_bool_map(value["runtime"], _RUNTIME_FALSE, "runtime")
    fingerprint = _lower_sha(
        value["profile_fingerprint_sha256"],
        "profile_fingerprint_sha256",
        nonzero=True,
    )
    unsigned = deepcopy(dict(value))
    unsigned.pop("profile_fingerprint_sha256")
    if _sha256_mapping(unsigned) != fingerprint:
        raise GrowthCapabilityError("profile fingerprint mismatch")
    if profile_id != value["profile_id"]:
        raise GrowthCapabilityError("profile identity drifted")
    return deepcopy(dict(value))


def validate_capability_profile(
    profile: Mapping[str, Any],
    *,
    policy_path: Path = POLICY_PATH,
    authority_controller: ProtectedGrowthController | None = None,
    authority_identity: ControllerIdentityHandle | None = None,
) -> dict[str, Any]:
    checked = _validate_capability_profile_structure(profile, policy_path=policy_path)
    if type(authority_controller) is not ProtectedGrowthController:
        raise GrowthAuthorityError(
            "all V3 profile validation requires the exact protected controller"
        )
    if authority_identity is not authority_controller.identity:
        raise GrowthAuthorityError(
            "all V3 profile validation requires the exact identity capability"
        )
    authority = checked["authority_binding"]
    if authority_controller.controller_id != authority["controller_id"]:
        raise GrowthAuthorityError("profile controller label mismatch")
    if (
        authority_controller.controller_identity_sha256
        != authority["controller_identity_sha256"]
    ):
        raise GrowthAuthorityError("profile controller identity digest mismatch")
    authority_controller._verify_registered_profile(checked)
    return checked


class PersonGrowthSession:
    """Controller-constructed bounded memory-only session for one exact person."""

    def __init__(
        self,
        *,
        _construction_key: object,
        controller: ProtectedGrowthController,
        lease: GrowthLeaseHandle,
        profile: Mapping[str, Any],
        activation_revision: str,
        session_nonce_sha256: str,
        session_binding_sha256: str,
        clock: Callable[[], float],
        max_events: int,
    ) -> None:
        if _construction_key is not _HANDLE_CONSTRUCTION_KEY:
            raise GrowthAuthorityError("sessions must be constructed by the protected controller")
        self.__controller = controller
        self.__lease = lease
        self.__profile = deepcopy(dict(profile))
        self.__activation_revision = activation_revision
        self.__session_nonce_sha256 = session_nonce_sha256
        self.__session_binding_sha256 = session_binding_sha256
        self.__clock = clock
        self.__max_events = max_events
        self.__last_clock: float | None = None
        self.__events: list[dict[str, Any]] = []
        self.__present_ids: set[str] = set()
        self.__proposal_ids: set[str] = set()
        self.__reviewed_proposal_ids: set[str] = set()
        self.__emotion_ids: set[str] = set()
        self.__event_operation_ids: set[str] = set()
        self.__controller_revision = 0
        self.__active = True
        self.__lock = threading.RLock()

    @property
    def lease(self) -> GrowthLeaseHandle:
        return self.__lease

    @property
    def session_binding_sha256(self) -> str:
        return self.__session_binding_sha256

    def _require(self, lease: GrowthLeaseHandle) -> None:
        if lease is not self.__lease or self.__active is not True:
            raise GrowthLeaseError("lease is not the exact active session handle")
        self.__controller._require_session(session=self, lease=lease)

    def _quarantine_after_recovery(self) -> None:
        """Fail closed when durable event truth cannot reconstruct private payload."""
        self.__events.clear()
        self.__present_ids.clear()
        self.__proposal_ids.clear()
        self.__reviewed_proposal_ids.clear()
        self.__emotion_ids.clear()
        self.__event_operation_ids.clear()
        self.__active = False

    def _timestamp(self) -> float:
        raw = self.__clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise GrowthCapabilityError("clock must return a finite number")
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            raise GrowthCapabilityError("clock must return a nonnegative finite number")
        if self.__last_clock is not None and value < self.__last_clock:
            raise GrowthCapabilityError("clock must remain monotonic")
        self.__last_clock = value
        return value

    def _append(
        self,
        *,
        kind: str,
        operation_id: str,
        payload: Mapping[str, Any],
        defer_accept_until_receipt_consumed: bool = False,
    ) -> dict[str, Any]:
        if len(self.__events) >= self.__max_events:
            raise GrowthCapabilityError("growth session event limit reached")
        operation_id = _identifier(operation_id, "event_operation_id")
        if operation_id in self.__event_operation_ids:
            raise GrowthReplayError("session event operation_id was already used")
        body = {
            "schema": EVENT_SCHEMA,
            "sequence": len(self.__events) + 1,
            "kind": _identifier(kind, "event_kind"),
            "person_id": self.__profile["person_binding"]["person_id"],
            "candidate_id": self.__profile["person_binding"]["candidate_id"],
            "profile_id": self.__profile["profile_id"],
            "activation_revision": self.__activation_revision,
            "session_binding_sha256": self.__session_binding_sha256,
            "recorded_at_monotonic_seconds": self._timestamp(),
            "previous_event_sha256": (
                self.__events[-1]["event_sha256"] if self.__events else "0" * 64
            ),
            **deepcopy(dict(payload)),
            "model_generation_performed": False,
            "durable_memory_mutated": False,
            "external_action_executed": False,
        }
        event_sha256 = _sha256_mapping(body)
        commit = self.__controller._commit_session_event(
            session=self,
            lease=self.__lease,
            expected_revision=self.__controller_revision,
            operation_id=operation_id,
            kind=kind,
            event_sha256=event_sha256,
        )
        readback = self.__controller._session_readback(
            session=self,
            lease=self.__lease,
        )
        if readback != commit or readback["binding_sha256"] != event_sha256:
            raise GrowthCapabilityError("session controller readback mismatch")
        record = {
            **body,
            "event_sha256": event_sha256,
            "controller_commit_sha256": commit["entry_sha256"],
            "controller_revision": commit["revision"],
        }
        if not defer_accept_until_receipt_consumed:
            self._accept_committed_event(record, operation_id=operation_id)
        return deepcopy(record)

    def _accept_committed_event(
        self, record: Mapping[str, Any], *, operation_id: str
    ) -> None:
        if record["controller_revision"] != self.__controller_revision + 1:
            raise GrowthRecoveryDebtError("committed event revision cannot be accepted")
        self.__controller_revision = record["controller_revision"]
        self.__events.append(deepcopy(dict(record)))
        self.__event_operation_ids.add(operation_id)

    def record_present_fact(
        self,
        lease: GrowthLeaseHandle,
        *,
        present_event_id: str,
        factual_summary: str,
        source_kind: str,
        source_receipt: EvidenceReceiptHandle,
        observed_at_utc: str,
        expires_at_utc: str,
    ) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            present_event_id = _identifier(present_event_id, "present_event_id")
            if present_event_id in self.__present_ids:
                raise GrowthReplayError("present_event_id was already used")
            if source_kind not in SOURCE_KINDS:
                raise GrowthCapabilityError("source_kind is unsupported")
            observed = _utc(observed_at_utc, "observed_at_utc")
            expires = _utc(expires_at_utc, "expires_at_utc")
            if expires <= observed:
                raise GrowthCapabilityError("present fact expiry must follow observation")
            receipt = self.__controller._peek_session_evidence(
                session=self,
                lease=lease,
                handle=source_receipt,
                purpose="present_source",
                source_kind=source_kind,
                event_binding_id=present_event_id,
            )
            event = self._append(
                kind="present_fact",
                operation_id=f"present:{present_event_id}",
                payload={
                    "present_event_id": present_event_id,
                    "factual_summary": _text(factual_summary, "factual_summary"),
                    "source_kind": source_kind,
                    "source_receipt_sha256": receipt["receipt_sha256"],
                    "source_content_sha256": receipt["source_content_sha256"],
                    "source_content_bytes": receipt["source_content_bytes"],
                    "source_revision": receipt["source_revision"],
                    "observed_at_utc": observed_at_utc,
                    "expires_at_utc": expires_at_utc,
                    "present_context_only": True,
                    "memory_promotion_proposed": False,
                },
                defer_accept_until_receipt_consumed=True,
            )
            try:
                self.__controller._consume_session_evidence(
                    session=self,
                    lease=lease,
                    handle=source_receipt,
                    purpose="present_source",
                    source_kind=source_kind,
                    event_binding_id=present_event_id,
                    use_operation_id=f"evidence-use:present:{present_event_id}",
                )
            except Exception as exc:
                try:
                    self.__controller._mark_session_transaction_debt(
                        session=self,
                        lease=lease,
                        operation_id=f"present:{present_event_id}",
                        event_sha256=event["event_sha256"],
                        error_type=type(exc).__name__,
                    )
                finally:
                    raise GrowthRecoveryDebtError(
                        "present event committed but receipt consumption is uncertain"
                    ) from exc
            self._accept_committed_event(
                event, operation_id=f"present:{present_event_id}"
            )
            self.__present_ids.add(present_event_id)
            return event

    def propose_learning(
        self,
        lease: GrowthLeaseHandle,
        *,
        proposal_id: str,
        proposed_claim: str,
        source_present_event_ids: Sequence[str],
        privacy_class: str,
        contradiction_state: str,
    ) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            proposal_id = _identifier(proposal_id, "proposal_id")
            if proposal_id in self.__proposal_ids:
                raise GrowthReplayError("proposal_id was already used")
            if isinstance(source_present_event_ids, (str, bytes)) or not isinstance(
                source_present_event_ids, Sequence
            ):
                raise GrowthCapabilityError("source_present_event_ids must be a sequence")
            source_ids = tuple(
                _identifier(item, "source_present_event_id")
                for item in source_present_event_ids
            )
            if not source_ids or len(set(source_ids)) != len(source_ids):
                raise GrowthCapabilityError("learning proposal needs unique source events")
            if any(item not in self.__present_ids for item in source_ids):
                raise GrowthCapabilityError("learning proposal references an unknown present fact")
            if privacy_class not in PRIVACY_CLASSES:
                raise GrowthCapabilityError("privacy_class is unsupported")
            if contradiction_state not in CONTRADICTION_STATES:
                raise GrowthCapabilityError("contradiction_state is unsupported")
            event = self._append(
                kind="learning_proposal",
                operation_id=f"proposal:{proposal_id}",
                payload={
                    "proposal_id": proposal_id,
                    "proposed_claim": _text(proposed_claim, "proposed_claim"),
                    "source_present_event_ids": list(source_ids),
                    "privacy_class": privacy_class,
                    "contradiction_state": contradiction_state,
                    "proposal_state": "PROPOSED_NOT_MEMORY",
                    "promotion_requires_separate_person_owned_review": True,
                },
            )
            self.__proposal_ids.add(proposal_id)
            return event

    def review_learning_proposal(
        self,
        lease: GrowthLeaseHandle,
        *,
        review_event_id: str,
        proposal_id: str,
        decision: str,
        review_authority_receipt: EvidenceReceiptHandle,
        review_source_kind: str,
    ) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            review_event_id = _identifier(review_event_id, "review_event_id")
            proposal_id = _identifier(proposal_id, "proposal_id")
            if proposal_id not in self.__proposal_ids:
                raise GrowthCapabilityError("learning proposal is unknown")
            if proposal_id in self.__reviewed_proposal_ids:
                raise GrowthReplayError("learning proposal was already reviewed")
            if decision not in REVIEW_DECISIONS:
                raise GrowthCapabilityError("learning review decision is unsupported")
            if review_source_kind not in SOURCE_KINDS:
                raise GrowthCapabilityError("review_source_kind is unsupported")
            receipt = self.__controller._peek_session_evidence(
                session=self,
                lease=lease,
                handle=review_authority_receipt,
                purpose="learning_review",
                source_kind=review_source_kind,
                event_binding_id=review_event_id,
            )
            event = self._append(
                kind="learning_review",
                operation_id=f"review:{review_event_id}",
                payload={
                    "review_event_id": review_event_id,
                    "proposal_id": proposal_id,
                    "decision": decision,
                    "review_authority_receipt_sha256": receipt["receipt_sha256"],
                    "review_authority_content_sha256": receipt["source_content_sha256"],
                    "review_authority_content_bytes": receipt["source_content_bytes"],
                    "separate_memory_writer_still_required": (
                        decision == "accept_for_separate_memory_review"
                    ),
                    "memory_written_by_this_review": False,
                },
                defer_accept_until_receipt_consumed=True,
            )
            try:
                self.__controller._consume_session_evidence(
                    session=self,
                    lease=lease,
                    handle=review_authority_receipt,
                    purpose="learning_review",
                    source_kind=review_source_kind,
                    event_binding_id=review_event_id,
                    use_operation_id=f"evidence-use:review:{review_event_id}",
                )
            except Exception as exc:
                try:
                    self.__controller._mark_session_transaction_debt(
                        session=self,
                        lease=lease,
                        operation_id=f"review:{review_event_id}",
                        event_sha256=event["event_sha256"],
                        error_type=type(exc).__name__,
                    )
                finally:
                    raise GrowthRecoveryDebtError(
                        "review event committed but receipt consumption is uncertain"
                    ) from exc
            self._accept_committed_event(
                event, operation_id=f"review:{review_event_id}"
            )
            self.__reviewed_proposal_ids.add(proposal_id)
            return event

    def record_causal_emotion(
        self,
        lease: GrowthLeaseHandle,
        *,
        emotion_event_id: str,
        cause_present_event_ids: Sequence[str],
        possible_interpretations: Sequence[str],
        selected_appraisal: str,
        emotion_label: str,
        intensity: float,
        confidence: float,
        unresolved: bool,
    ) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            emotion_event_id = _identifier(emotion_event_id, "emotion_event_id")
            if emotion_event_id in self.__emotion_ids:
                raise GrowthReplayError("emotion_event_id was already used")
            if type(unresolved) is not bool:
                raise GrowthCapabilityError("unresolved must be boolean")
            if isinstance(cause_present_event_ids, (str, bytes)) or not isinstance(
                cause_present_event_ids, Sequence
            ):
                raise GrowthCapabilityError("cause_present_event_ids must be a sequence")
            cause_ids = tuple(
                _identifier(item, "cause_present_event_id")
                for item in cause_present_event_ids
            )
            if (
                not cause_ids
                or len(set(cause_ids)) != len(cause_ids)
                or any(item not in self.__present_ids for item in cause_ids)
            ):
                raise GrowthCapabilityError("causal emotion requires unique known present facts")
            if isinstance(possible_interpretations, (str, bytes)) or not isinstance(
                possible_interpretations, Sequence
            ):
                raise GrowthCapabilityError("possible_interpretations must be a sequence")
            interpretations = [
                _text(item, "possible_interpretation", 500)
                for item in possible_interpretations
            ]
            if not interpretations or len(interpretations) > 8:
                raise GrowthCapabilityError("causal emotion needs one to eight interpretations")
            event = self._append(
                kind="causal_emotion",
                operation_id=f"emotion:{emotion_event_id}",
                payload={
                    "emotion_event_id": emotion_event_id,
                    "cause_present_event_ids": list(cause_ids),
                    "possible_interpretations": interpretations,
                    "possible_interpretations_are_advisory": True,
                    "selected_appraisal": _text(selected_appraisal, "selected_appraisal"),
                    "emotion_label": _text(emotion_label, "emotion_label", 128),
                    "intensity": _unit(intensity, "intensity"),
                    "confidence": _unit(confidence, "confidence"),
                    "unresolved": unresolved,
                    "visibility": "person_private",
                    "public_expression_selected": False,
                    "physiological_response_recorded": False,
                    "private_desire_recorded": False,
                    "preference_recorded": False,
                    "consent_recorded": False,
                    "health_state_recorded": False,
                },
            )
            self.__emotion_ids.add(emotion_event_id)
            return event

    def public_snapshot(self, lease: GrowthLeaseHandle) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            readback = self.__controller._session_readback(session=self, lease=lease)
            return {
                "schema": "kira.shared_person_growth_public_snapshot.v3",
                "person_id": self.__profile["person_binding"]["person_id"],
                "profile_id": self.__profile["profile_id"],
                "event_count": len(self.__events),
                "head_event_sha256": (
                    self.__events[-1]["event_sha256"] if self.__events else "0" * 64
                ),
                "controller_revision": readback["revision"],
                "controller_head_sha256": readback["entry_sha256"],
                "private_payload_exposed": False,
                "memory_persisted": False,
                "external_action_executed": False,
                "storage": "bounded_memory_only_with_durable_digest_ledger",
            }

    def private_records(self, lease: GrowthLeaseHandle) -> list[dict[str, Any]]:
        with self.__lock:
            self._require(lease)
            return deepcopy(self.__events)

    def deactivate(
        self,
        lease: GrowthLeaseHandle,
        *,
        close_operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            self._require(lease)
            count = len(self.__events)
            close = self.__controller._close_session(
                session=self,
                lease=lease,
                close_operation_id=close_operation_id,
            )
            self.__events.clear()
            self.__present_ids.clear()
            self.__proposal_ids.clear()
            self.__reviewed_proposal_ids.clear()
            self.__emotion_ids.clear()
            self.__event_operation_ids.clear()
            self.__active = False
            return {
                "person_id": self.__profile["person_binding"]["person_id"],
                "purged_memory_only_event_count": count,
                "controller_revision_preserved": close["session_revision"],
                "controller_head_sha256": close["session_head_sha256"],
                "durable_memory_deleted": False,
                "identity_changed": False,
            }

    def __getstate__(self) -> None:
        raise TypeError("PersonGrowthSession is memory-only and not serializable")


_ATTACHMENT_KEYS = {
    "schema",
    "candidate_id",
    "display_name",
    "growth_profile",
    "creator_truth",
    "attachment_sha256",
}
_CREATOR_TRUTH = {
    "fresh_profile_created": True,
    "existing_person_profile_copied": False,
    "existing_person_private_data_read": False,
    "activation_allowed": False,
    "assignment_allowed": False,
    "model_or_device_called": False,
    "requires_separate_static_audit": True,
    "requires_bounded_live_acceptance_before_shared_enablement": True,
    "unknown_private_payload_allowed": False,
    "existing_private_roots_aliased": False,
    "transitive_private_payload_allowed": False,
    "connected_controller_validation_performed": True,
}


def build_temporary_creator_attachment(
    *,
    candidate_id: str,
    display_name: str,
    person_id: str,
    profile_id: str,
    authority_controller: ProtectedGrowthController,
    authority_identity: ControllerIdentityHandle,
    authority_secret: bytes,
    fresh_roots_operation_id: str,
    maturity_authority: MaturityAuthorityHandle | None = None,
) -> dict[str, Any]:
    candidate_id = _identifier(candidate_id, "candidate_id")
    fresh_roots = authority_controller.issue_fresh_profile_roots(
        authority_identity=authority_identity,
        authority_secret=authority_secret,
        operation_id=fresh_roots_operation_id,
        person_id=person_id,
        candidate_id=candidate_id,
        profile_id=profile_id,
    )
    profile = build_fresh_capability_profile(
        person_id=person_id,
        candidate_id=candidate_id,
        profile_id=profile_id,
        authority_controller=authority_controller,
        authority_identity=authority_identity,
        fresh_root_authority=fresh_roots,
        maturity_authority=maturity_authority,
    )
    attachment: dict[str, Any] = {
        "schema": CREATOR_ATTACHMENT_SCHEMA,
        "candidate_id": candidate_id,
        "display_name": _text(display_name, "display_name", 256),
        "growth_profile": profile,
        "creator_truth": deepcopy(_CREATOR_TRUTH),
    }
    attachment["attachment_sha256"] = _sha256_mapping(attachment)
    return validate_temporary_creator_attachment(
        attachment,
        authority_controller=authority_controller,
        authority_identity=authority_identity,
    )


def validate_temporary_creator_attachment(
    value: Mapping[str, Any],
    *,
    authority_controller: ProtectedGrowthController | None = None,
    authority_identity: ControllerIdentityHandle | None = None,
) -> dict[str, Any]:
    attachment = _exact_keys(value, _ATTACHMENT_KEYS, "creator_attachment")
    if attachment["schema"] != CREATOR_ATTACHMENT_SCHEMA:
        raise GrowthCapabilityError("creator attachment schema mismatch")
    candidate_id = _identifier(attachment["candidate_id"], "candidate_id")
    _text(attachment["display_name"], "display_name", 256)
    profile = validate_capability_profile(
        attachment["growth_profile"],
        authority_controller=authority_controller,
        authority_identity=authority_identity,
    )
    if profile["person_binding"]["candidate_id"] != candidate_id:
        raise GrowthCapabilityError("creator attachment candidate binding mismatch")
    _exact_bool_map(attachment["creator_truth"], _CREATOR_TRUTH, "creator_truth")
    digest = _lower_sha(
        attachment["attachment_sha256"],
        "attachment_sha256",
        nonzero=True,
    )
    unsigned = deepcopy(dict(attachment))
    unsigned.pop("attachment_sha256")
    if _sha256_mapping(unsigned) != digest:
        raise GrowthCapabilityError("creator attachment hash mismatch")
    return deepcopy(dict(attachment))


__all__ = [
    "POLICY_PATH",
    "MATURITY_STATUSES",
    "GrowthCapabilityError",
    "GrowthAuthorityError",
    "GrowthLeaseError",
    "GrowthReplayError",
    "GrowthRecoveryDebtError",
    "ControllerIdentityHandle",
    "GrowthLeaseHandle",
    "EvidenceReceiptHandle",
    "MaturityAuthorityHandle",
    "FreshProfileRootsHandle",
    "ProtectedGrowthController",
    "PersonGrowthSession",
    "load_policy",
    "policy_sha256",
    "build_fresh_capability_profile",
    "validate_capability_profile",
    "build_temporary_creator_attachment",
    "validate_temporary_creator_attachment",
]
