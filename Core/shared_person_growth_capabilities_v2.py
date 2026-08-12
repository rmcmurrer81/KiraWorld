"""Static V2 repair of shared person growth primitives.

V2 is append-only and deliberately disconnected.  It repairs the V1 audit
findings with controller-owned identity handles, secret-gated authority
issuance, exact person/profile/candidate receipt binding, nonzero protected
receipts, monotonic compare-and-swap/readback ledgers, closed schemas, and
explicit replay refusal.  It does not call a model, write durable memory,
infer maturity, grant consent, activate a person, execute an action, or copy
another person's private state.

Bounded initiative remains DESIGN_ONLY and is not implemented by this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "Data" / "foundation" / "shared_person_growth_capabilities_v2.json"
PROFILE_SCHEMA = "kira.shared_person_growth_profile.v2"
EVENT_SCHEMA = "kira.shared_person_growth_event.v2"
CREATOR_ATTACHMENT_SCHEMA = "kira.temporary_creator_growth_attachment.v2"
CONTROLLER_ENTRY_SCHEMA = "kira.shared_person_growth_controller_entry.v2"
EVIDENCE_RECEIPT_SCHEMA = "kira.shared_person_growth_evidence_receipt.v2"
MATURITY_RECEIPT_SCHEMA = "kira.shared_person_growth_maturity_receipt.v2"
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
    """Raised when a V2 static growth record crosses a closed boundary."""


class GrowthAuthorityError(PermissionError):
    """Raised when protected controller authority is missing or mismatched."""


class GrowthLeaseError(PermissionError):
    """Raised when the exact controller-owned active lease is not presented."""


class GrowthReplayError(GrowthCapabilityError):
    """Raised when an operation, receipt, event, or session binding is replayed."""


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
    if not isinstance(value, Mapping):
        raise GrowthCapabilityError(f"{field_name} must be an object")
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
    "authority_secret_required_for_issuance_and_session_open": True,
    "exact_person_profile_candidate_binding": True,
    "nonzero_receipt_artifact_required": True,
    "single_use_receipts": True,
    "monotonic_cas_readback_ledger": True,
    "replay_rejected": True,
    "disconnected_fails_closed": True,
}

_EXPECTED_EXACT_SCHEMA_CONTRACT = {
    "unknown_policy_fields_rejected": True,
    "unknown_profile_fields_rejected": True,
    "unknown_attachment_fields_rejected": True,
    "unknown_creator_bundle_fields_rejected": True,
    "truth_boundary_values_closed": True,
    "private_payload_copy_fields_rejected": True,
}


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_strict_json_object)
    except GrowthCapabilityError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthCapabilityError("V2 growth policy is not valid UTF-8 JSON") from exc
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
    if top["schema"] != "kira.shared_person_growth_capabilities_policy.v2":
        raise GrowthCapabilityError("V2 growth policy schema mismatch")
    if top["status"] != "STATIC_REPAIR_CANDIDATE_PENDING_DIFFERENT_AUDIT":
        raise GrowthCapabilityError("V2 policy status drifted")
    if top["owner_authorization_date"] != "2026-08-10":
        raise GrowthCapabilityError("V2 policy authorization date drifted")
    if top["rollout_order"] != list(ROLLOUT_STAGES):
        raise GrowthCapabilityError("V2 rollout order drifted")
    if not _typed_equal(top["capabilities"], _EXPECTED_CAPABILITIES):
        raise GrowthCapabilityError("V2 capability catalog or implementation truth drifted")
    _exact_bool_map(top["authority_contract"], _EXPECTED_AUTHORITY_CONTRACT, "authority_contract")
    _exact_bool_map(
        top["exact_schema_contract"],
        _EXPECTED_EXACT_SCHEMA_CONTRACT,
        "exact_schema_contract",
    )
    never = top["never_inherited_from_another_person"]
    if not isinstance(never, list) or not never or len(never) != len(set(never)):
        raise GrowthCapabilityError("never-inherited catalog must be a unique list")
    for item in never:
        _identifier(item, "never_inherited_item")
    _exact_bool_map(
        top["fresh_person_requirements"],
        {
            "new_opaque_person_id": True,
            "new_profile_id": True,
            "new_private_state_roots": True,
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
    if not isinstance(separation, list) or len(separation) != 12 or len(set(separation)) != 12:
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


class EvidenceReceiptHandle(_IdentityHandle):
    """Opaque identity-only, single-use evidence capability."""


class MaturityAuthorityHandle(_IdentityHandle):
    """Opaque identity-only, single-use maturity authority capability."""


class _ProtectedLedger:
    """In-memory digest-only monotonic CAS ledger with exact readback."""

    def __init__(self, ledger_id: str) -> None:
        self._ledger_id = _identifier(ledger_id, "ledger_id")
        self._records: list[dict[str, Any]] = []
        self._operation_ids: set[str] = set()

    @property
    def revision(self) -> int:
        return len(self._records)

    @property
    def head_sha256(self) -> str:
        return self._records[-1]["entry_sha256"] if self._records else "0" * 64

    def append_cas(
        self,
        *,
        expected_revision: int,
        operation_id: str,
        kind: str,
        binding_sha256: str,
    ) -> dict[str, Any]:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
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
        self._records.append(entry)
        self._operation_ids.add(operation_id)
        readback = self.readback_head()
        if readback != entry or readback["revision"] != expected_revision + 1:
            raise GrowthCapabilityError("protected ledger readback mismatch")
        return deepcopy(entry)

    def readback_head(self) -> dict[str, Any]:
        if not self._records:
            return {
                "ledger_id": self._ledger_id,
                "revision": 0,
                "entry_sha256": "0" * 64,
            }
        self.verify_chain()
        return deepcopy(self._records[-1])

    def verify_chain(self) -> None:
        previous = "0" * 64
        operations: set[str] = set()
        for index, raw in enumerate(self._records, start=1):
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
                "protected_ledger_entry",
            )
            if entry["schema"] != CONTROLLER_ENTRY_SCHEMA:
                raise GrowthCapabilityError("protected ledger schema drifted")
            if entry["ledger_id"] != self._ledger_id or entry["revision"] != index:
                raise GrowthCapabilityError("protected ledger identity or revision drifted")
            if entry["previous_entry_sha256"] != previous:
                raise GrowthCapabilityError("protected ledger chain drifted")
            operation = _identifier(entry["operation_id"], "operation_id")
            if operation in operations:
                raise GrowthReplayError("protected ledger contains replayed operation")
            operations.add(operation)
            _identifier(entry["kind"], "ledger_kind")
            _lower_sha(entry["binding_sha256"], "binding_sha256", nonzero=True)
            digest = _lower_sha(entry["entry_sha256"], "entry_sha256", nonzero=True)
            unsigned = dict(entry)
            unsigned.pop("entry_sha256")
            if _sha256_mapping(unsigned) != digest:
                raise GrowthCapabilityError("protected ledger entry digest mismatch")
            previous = digest


class ProtectedGrowthController:
    """Controller-owned authority, receipt, profile, lease, and replay boundary."""

    def __init__(self, *, controller_id: str, authority_secret: bytes) -> None:
        self.__controller_id = _identifier(controller_id, "controller_id")
        if not isinstance(authority_secret, bytes) or len(authority_secret) < 32:
            raise GrowthAuthorityError("authority_secret must contain at least 32 bytes")
        if not any(authority_secret):
            raise GrowthAuthorityError("authority_secret must not be all zero")
        self.__authority_secret = bytes(authority_secret)
        self.__lock = threading.RLock()
        self.__authority_ledger = _ProtectedLedger(f"authority:{self.controller_id}")
        self.__evidence: dict[EvidenceReceiptHandle, dict[str, Any]] = {}
        self.__evidence_by_digest: dict[str, EvidenceReceiptHandle] = {}
        self.__maturity: dict[MaturityAuthorityHandle, dict[str, Any]] = {}
        self.__maturity_by_digest: dict[str, MaturityAuthorityHandle] = {}
        self.__profiles: dict[str, dict[str, Any]] = {}
        self.__sessions: dict[GrowthLeaseHandle, dict[str, Any]] = {}
        self.__session_bindings: set[str] = set()

    @property
    def controller_id(self) -> str:
        return self.__controller_id

    def _authenticate(self, authority_secret: bytes) -> None:
        if not isinstance(authority_secret, bytes) or not hmac.compare_digest(
            authority_secret, self.__authority_secret
        ):
            raise GrowthAuthorityError("protected controller authority secret mismatch")

    def _authority_append(self, *, operation_id: str, kind: str, binding: Mapping[str, Any]) -> dict[str, Any]:
        return self.__authority_ledger.append_cas(
            expected_revision=self.__authority_ledger.revision,
            operation_id=operation_id,
            kind=kind,
            binding_sha256=_sha256_mapping(binding),
        )

    def issue_evidence_receipt(
        self,
        *,
        authority_secret: bytes,
        operation_id: str,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        purpose: str,
        source_kind: str,
        source_artifact_sha256: str,
        source_revision: str,
    ) -> EvidenceReceiptHandle:
        with self.__lock:
            self._authenticate(authority_secret)
            person_id = _identifier(person_id, "person_id")
            candidate_id = _identifier(candidate_id, "candidate_id")
            profile_id = _identifier(profile_id, "profile_id")
            if purpose not in EVIDENCE_PURPOSES:
                raise GrowthCapabilityError("evidence purpose is unsupported")
            if source_kind not in SOURCE_KINDS:
                raise GrowthCapabilityError("source_kind is unsupported")
            source_artifact_sha256 = _lower_sha(
                source_artifact_sha256, "source_artifact_sha256", nonzero=True
            )
            record = {
                "schema": EVIDENCE_RECEIPT_SCHEMA,
                "controller_id": self.controller_id,
                "person_id": person_id,
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "purpose": purpose,
                "source_kind": source_kind,
                "source_artifact_sha256": source_artifact_sha256,
                "source_revision": _identifier(source_revision, "source_revision"),
                "issue_operation_id": _identifier(operation_id, "operation_id"),
                "single_use": True,
            }
            record["receipt_sha256"] = _sha256_mapping(record)
            self._authority_append(
                operation_id=operation_id,
                kind="evidence_issue",
                binding=record,
            )
            handle = EvidenceReceiptHandle(_HANDLE_CONSTRUCTION_KEY)
            stored = deepcopy(record)
            stored["consumed"] = False
            stored["consumed_by"] = None
            self.__evidence[handle] = stored
            self.__evidence_by_digest[record["receipt_sha256"]] = handle
            return handle

    def _consume_evidence(
        self,
        handle: EvidenceReceiptHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
        purpose: str,
        source_kind: str | None,
        use_operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            if not isinstance(handle, EvidenceReceiptHandle) or handle not in self.__evidence:
                raise GrowthAuthorityError("evidence handle is not owned by this controller")
            record = self.__evidence[handle]
            if record["consumed"]:
                raise GrowthReplayError("evidence receipt was already consumed")
            expected = {
                "person_id": _identifier(person_id, "person_id"),
                "candidate_id": _identifier(candidate_id, "candidate_id"),
                "profile_id": _identifier(profile_id, "profile_id"),
                "purpose": purpose,
            }
            if any(record[field] != value for field, value in expected.items()):
                raise GrowthAuthorityError("evidence receipt exact binding mismatch")
            if source_kind is not None and record["source_kind"] != source_kind:
                raise GrowthAuthorityError("evidence receipt source kind mismatch")
            use_operation_id = _identifier(use_operation_id, "use_operation_id")
            self._authority_append(
                operation_id=use_operation_id,
                kind="evidence_consume",
                binding={
                    "receipt_sha256": record["receipt_sha256"],
                    "person_id": record["person_id"],
                    "candidate_id": record["candidate_id"],
                    "profile_id": record["profile_id"],
                    "purpose": record["purpose"],
                    "use_operation_id": use_operation_id,
                },
            )
            record["consumed"] = True
            record["consumed_by"] = use_operation_id
            return {
                key: deepcopy(value)
                for key, value in record.items()
                if key not in {"consumed", "consumed_by"}
            }

    def issue_maturity_classification(
        self,
        *,
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
            self._authenticate(authority_secret)
            if status not in CLASSIFIED_MATURITY_STATUSES:
                raise GrowthCapabilityError("protected maturity status must be classified")
            operation_id = _identifier(operation_id, "operation_id")
            source = self._consume_evidence(
                source_evidence,
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
                purpose="maturity_classification_source",
                source_kind=None,
                use_operation_id=f"{operation_id}:source",
            )
            record = {
                "schema": MATURITY_RECEIPT_SCHEMA,
                "controller_id": self.controller_id,
                "person_id": _identifier(person_id, "person_id"),
                "candidate_id": _identifier(candidate_id, "candidate_id"),
                "profile_id": _identifier(profile_id, "profile_id"),
                "status": status,
                "source_evidence_receipt_sha256": source["receipt_sha256"],
                "classification_revision": _identifier(
                    classification_revision, "classification_revision"
                ),
                "issue_operation_id": operation_id,
                "single_use_profile_binding": True,
                "classification_inferred_by_module": False,
            }
            record["receipt_sha256"] = _sha256_mapping(record)
            self._authority_append(
                operation_id=operation_id,
                kind="maturity_issue",
                binding=record,
            )
            handle = MaturityAuthorityHandle(_HANDLE_CONSTRUCTION_KEY)
            stored = deepcopy(record)
            stored["consumed"] = False
            stored["consumed_by_profile_sha256"] = None
            self.__maturity[handle] = stored
            self.__maturity_by_digest[record["receipt_sha256"]] = handle
            return handle

    def _peek_maturity(
        self,
        handle: MaturityAuthorityHandle,
        *,
        person_id: str,
        candidate_id: str,
        profile_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            if not isinstance(handle, MaturityAuthorityHandle) or handle not in self.__maturity:
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
            maturity = profile["maturity"]
            if maturity_handle is None:
                if maturity["status"] != "unresolved" or maturity["classification_receipt_sha256"] is not None:
                    raise GrowthAuthorityError("classified profile lacks protected maturity handle")
            else:
                record = self._peek_maturity(
                    maturity_handle,
                    person_id=binding["person_id"],
                    candidate_id=binding["candidate_id"],
                    profile_id=profile["profile_id"],
                )
                if maturity["status"] != record["status"] or maturity["classification_receipt_sha256"] != record["receipt_sha256"]:
                    raise GrowthAuthorityError("profile maturity receipt binding mismatch")
                self._authority_append(
                    operation_id=f"profile-bind:{profile['profile_id']}",
                    kind="maturity_consume",
                    binding={
                        "profile_fingerprint_sha256": fingerprint,
                        "maturity_receipt_sha256": record["receipt_sha256"],
                    },
                )
                stored = self.__maturity[maturity_handle]
                stored["consumed"] = True
                stored["consumed_by_profile_sha256"] = fingerprint
            self._authority_append(
                operation_id=f"profile-register:{profile['profile_id']}",
                kind="profile_register",
                binding={
                    "profile_fingerprint_sha256": fingerprint,
                    "person_id": binding["person_id"],
                    "candidate_id": binding["candidate_id"],
                    "profile_id": profile["profile_id"],
                },
            )
            self.__profiles[fingerprint] = {
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": profile["profile_id"],
                "maturity_status": maturity["status"],
                "maturity_receipt_sha256": maturity["classification_receipt_sha256"],
            }

    def _verify_registered_profile(self, profile: Mapping[str, Any]) -> None:
        with self.__lock:
            fingerprint = profile["profile_fingerprint_sha256"]
            registered = self.__profiles.get(fingerprint)
            if registered is None:
                raise GrowthAuthorityError("profile is not registered to this controller")
            binding = profile["person_binding"]
            expected = {
                "person_id": binding["person_id"],
                "candidate_id": binding["candidate_id"],
                "profile_id": profile["profile_id"],
                "maturity_status": profile["maturity"]["status"],
                "maturity_receipt_sha256": profile["maturity"]["classification_receipt_sha256"],
            }
            if registered != expected:
                raise GrowthAuthorityError("registered profile binding mismatch")
            receipt_digest = registered["maturity_receipt_sha256"]
            if receipt_digest is not None:
                handle = self.__maturity_by_digest.get(receipt_digest)
                if handle is None:
                    raise GrowthAuthorityError("classified profile receipt is absent")
                record = self.__maturity[handle]
                if not record["consumed"] or record["consumed_by_profile_sha256"] != fingerprint:
                    raise GrowthAuthorityError("classified profile receipt was not consumed exactly once")

    def open_session(
        self,
        *,
        authority_secret: bytes,
        profile: Mapping[str, Any],
        activation_revision: str,
        session_nonce_sha256: str,
        session_open_operation_id: str,
        clock: Callable[[], float],
        max_events: int = 128,
    ) -> "PersonGrowthSession":
        with self.__lock:
            self._authenticate(authority_secret)
            checked = validate_capability_profile(profile, authority_controller=self)
            activation_revision = _identifier(activation_revision, "activation_revision")
            session_nonce_sha256 = _lower_sha(
                session_nonce_sha256, "session_nonce_sha256", nonzero=True
            )
            session_open_operation_id = _identifier(
                session_open_operation_id, "session_open_operation_id"
            )
            if not callable(clock):
                raise GrowthCapabilityError("clock must be callable")
            if (
                isinstance(max_events, bool)
                or not isinstance(max_events, int)
                or not 1 <= max_events <= 512
            ):
                raise GrowthCapabilityError("max_events must be an integer from 1 to 512")
            binding = checked["person_binding"]
            session_binding = {
                "controller_id": self.controller_id,
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
            self._authority_append(
                operation_id=session_open_operation_id,
                kind="session_open",
                binding=session_binding,
            )
            lease = GrowthLeaseHandle(_HANDLE_CONSTRUCTION_KEY)
            session_ledger = _ProtectedLedger(
                f"session:{session_binding_sha256[:48]}"
            )
            session = PersonGrowthSession(
                _construction_key=_HANDLE_CONSTRUCTION_KEY,
                controller=self,
                lease=lease,
                profile=checked,
                activation_revision=activation_revision,
                session_nonce_sha256=session_nonce_sha256,
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
        with self.__lock:
            if not isinstance(lease, GrowthLeaseHandle) or lease not in self.__sessions:
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
            ledger: _ProtectedLedger = record["ledger"]
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
            ledger: _ProtectedLedger = record["ledger"]
            return ledger.readback_head()

    def _consume_session_evidence(
        self,
        *,
        session: "PersonGrowthSession",
        lease: GrowthLeaseHandle,
        handle: EvidenceReceiptHandle,
        purpose: str,
        source_kind: str | None,
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
                use_operation_id=use_operation_id,
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
            ledger: _ProtectedLedger = record["ledger"]
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

    def protected_audit_snapshot(self, *, authority_secret: bytes) -> dict[str, Any]:
        with self.__lock:
            self._authenticate(authority_secret)
            self.__authority_ledger.verify_chain()
            for record in self.__sessions.values():
                record["ledger"].verify_chain()
            return {
                "schema": "kira.shared_person_growth_controller_snapshot.v2",
                "controller_id": self.controller_id,
                "authority_revision": self.__authority_ledger.revision,
                "authority_head_sha256": self.__authority_ledger.head_sha256,
                "registered_profile_count": len(self.__profiles),
                "issued_evidence_count": len(self.__evidence),
                "issued_maturity_count": len(self.__maturity),
                "session_count": len(self.__sessions),
                "active_session_count": sum(
                    1 for record in self.__sessions.values() if record["active"]
                ),
                "private_payload_exposed": False,
                "durable_memory_connected": False,
                "external_actions_connected": False,
            }


def _private_root_token(person_id: str, profile_id: str, root_nonce_sha256: str) -> str:
    material = f"v2\n{person_id}\n{profile_id}\n{root_nonce_sha256}\n".encode("utf-8")
    return _sha256_bytes(material)[:32]


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
    "controller_registration_required_for_activation",
    "plain_digest_is_not_authority",
}
_MATURITY_KEYS = {
    "status",
    "classification_receipt_sha256",
    "classification_controller_id",
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
    root_nonce_sha256: str,
    authority_controller: ProtectedGrowthController,
    maturity_authority: MaturityAuthorityHandle | None = None,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    """Build one exact fresh profile; public default is always unresolved."""

    if not isinstance(authority_controller, ProtectedGrowthController):
        raise GrowthAuthorityError("a protected controller is required")
    person_id = _identifier(person_id, "person_id")
    candidate_id = _identifier(candidate_id, "candidate_id")
    profile_id = _identifier(profile_id, "profile_id")
    root_nonce_sha256 = _lower_sha(root_nonce_sha256, "root_nonce_sha256", nonzero=True)
    policy = load_policy(policy_path)
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
    root_token = _private_root_token(person_id, profile_id, root_nonce_sha256)
    prefix = f"Data/person_private/{root_token}"
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
            "controller_registration_required_for_activation": True,
            "plain_digest_is_not_authority": True,
        },
        "maturity": {
            "status": maturity_status,
            "classification_receipt_sha256": maturity_receipt_sha256,
            "classification_controller_id": (
                authority_controller.controller_id if maturity_receipt_sha256 else None
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
        "private_state_roots": {
            "present_context": f"{prefix}/present_context",
            "learning_proposals": f"{prefix}/learning_proposals",
            "emotion": f"{prefix}/emotion",
            "initiative": f"{prefix}/initiative",
            "memory_review": f"{prefix}/memory_review",
        },
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
        maturity_handle=maturity_authority,
    )
    return validate_capability_profile(
        profile,
        policy_path=policy_path,
        authority_controller=authority_controller,
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
    else:
        _lower_sha(
            maturity["classification_receipt_sha256"],
            "classification_receipt_sha256",
            nonzero=True,
        )
        if maturity["classification_controller_id"] != authority["controller_id"]:
            raise GrowthCapabilityError("maturity controller binding mismatch")
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
    if value["capabilities"] != load_policy(policy_path)["capabilities"]:
        raise GrowthCapabilityError("capability catalog drifted from policy")
    _exact_bool_map(value["truth_boundaries"], _TRUTH_BOUNDARIES, "truth_boundaries")
    inheritance = _exact_keys(
        value["inheritance"], _INHERITANCE_KEYS, "inheritance"
    )
    if inheritance["shared_code_and_schema_only"] is not True:
        raise GrowthCapabilityError("only code and schema may be shared")
    if inheritance["never_inherited"] != load_policy(policy_path)["never_inherited_from_another_person"]:
        raise GrowthCapabilityError("never-inherited catalog drifted")
    if inheritance["source_person_id"] is not None or inheritance["source_profile_id"] is not None:
        raise GrowthCapabilityError("fresh profile must not name a source person/profile")
    for field in (
        "copied_private_records",
        "copied_capability_leases",
        "copied_acceptance_receipts",
    ):
        if inheritance[field] != 0:
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
) -> dict[str, Any]:
    checked = _validate_capability_profile_structure(profile, policy_path=policy_path)
    authority_id = checked["authority_binding"]["controller_id"]
    classified = checked["maturity"]["status"] != "unresolved"
    if authority_controller is None:
        if classified:
            raise GrowthAuthorityError(
                "classified profile validation fails closed without its protected controller"
            )
        return checked
    if not isinstance(authority_controller, ProtectedGrowthController):
        raise GrowthAuthorityError("authority_controller is invalid")
    if authority_controller.controller_id != authority_id:
        raise GrowthAuthorityError("profile controller identity mismatch")
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

    def _require(self, lease: GrowthLeaseHandle) -> None:
        if lease is not self.__lease or self.__active is not True:
            raise GrowthLeaseError("lease is not the exact active session handle")
        self.__controller._require_session(session=self, lease=lease)

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
        self.__controller_revision = commit["revision"]
        record = {
            **body,
            "event_sha256": event_sha256,
            "controller_commit_sha256": commit["entry_sha256"],
            "controller_revision": commit["revision"],
        }
        self.__events.append(record)
        self.__event_operation_ids.add(operation_id)
        return deepcopy(record)

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
            receipt = self.__controller._consume_session_evidence(
                session=self,
                lease=lease,
                handle=source_receipt,
                purpose="present_source",
                source_kind=source_kind,
                use_operation_id=f"evidence-use:present:{present_event_id}",
            )
            event = self._append(
                kind="present_fact",
                operation_id=f"present:{present_event_id}",
                payload={
                    "present_event_id": present_event_id,
                    "factual_summary": _text(factual_summary, "factual_summary"),
                    "source_kind": source_kind,
                    "source_receipt_sha256": receipt["receipt_sha256"],
                    "source_artifact_sha256": receipt["source_artifact_sha256"],
                    "source_revision": receipt["source_revision"],
                    "observed_at_utc": observed_at_utc,
                    "expires_at_utc": expires_at_utc,
                    "present_context_only": True,
                    "memory_promotion_proposed": False,
                },
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
            receipt = self.__controller._consume_session_evidence(
                session=self,
                lease=lease,
                handle=review_authority_receipt,
                purpose="learning_review",
                source_kind=None,
                use_operation_id=f"evidence-use:review:{review_event_id}",
            )
            event = self._append(
                kind="learning_review",
                operation_id=f"review:{review_event_id}",
                payload={
                    "review_event_id": review_event_id,
                    "proposal_id": proposal_id,
                    "decision": decision,
                    "review_authority_receipt_sha256": receipt["receipt_sha256"],
                    "review_authority_artifact_sha256": receipt["source_artifact_sha256"],
                    "separate_memory_writer_still_required": (
                        decision == "accept_for_separate_memory_review"
                    ),
                    "memory_written_by_this_review": False,
                },
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
            if not isinstance(unresolved, bool):
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
                "schema": "kira.shared_person_growth_public_snapshot.v2",
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
                "storage": "bounded_memory_only_with_digest_ledger",
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
}


def build_temporary_creator_attachment(
    *,
    candidate_id: str,
    display_name: str,
    person_id: str,
    profile_id: str,
    root_nonce_sha256: str,
    authority_controller: ProtectedGrowthController,
    maturity_authority: MaturityAuthorityHandle | None = None,
) -> dict[str, Any]:
    candidate_id = _identifier(candidate_id, "candidate_id")
    profile = build_fresh_capability_profile(
        person_id=person_id,
        candidate_id=candidate_id,
        profile_id=profile_id,
        root_nonce_sha256=root_nonce_sha256,
        authority_controller=authority_controller,
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
    )


def validate_temporary_creator_attachment(
    value: Mapping[str, Any],
    *,
    authority_controller: ProtectedGrowthController | None = None,
) -> dict[str, Any]:
    attachment = _exact_keys(value, _ATTACHMENT_KEYS, "creator_attachment")
    if attachment["schema"] != CREATOR_ATTACHMENT_SCHEMA:
        raise GrowthCapabilityError("creator attachment schema mismatch")
    candidate_id = _identifier(attachment["candidate_id"], "candidate_id")
    _text(attachment["display_name"], "display_name", 256)
    profile = validate_capability_profile(
        attachment["growth_profile"],
        authority_controller=authority_controller,
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
    "GrowthLeaseHandle",
    "EvidenceReceiptHandle",
    "MaturityAuthorityHandle",
    "ProtectedGrowthController",
    "PersonGrowthSession",
    "load_policy",
    "policy_sha256",
    "build_fresh_capability_profile",
    "validate_capability_profile",
    "build_temporary_creator_attachment",
    "validate_temporary_creator_attachment",
]
