"""Transactional garment inventory shared by World Builder and Avatar Builder.

The ledger is intentionally small and renderer-independent.  A pending action
does not remove the world item or create an avatar copy.  Ownership changes only
after the matching physical evidence gate passes, in one revision-checked
commit.  Consequently cancellation, refusal, suspension, and crash recovery
all leave the last committed item placement intact.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Iterable
from uuid import uuid4

from Core.garment_contracts import (
    AVATAR_STATES,
    ContractError,
    GarmentDefinition,
    GarmentInstance,
    GarmentState,
    MaturityClass,
    OwnerScope,
    SHA256_RE,
    owner_scope_for_state,
)
from Core.garment_evidence import (
    EvidenceDecision,
    compute_decision_sha256,
    evaluate_garment_transition,
)


class LedgerError(RuntimeError):
    """Base class for garment-ledger failures."""


class DuplicateInstanceError(LedgerError):
    """Raised when a persistent item id would be registered twice."""


class CompatibilityError(LedgerError):
    """Raised when exact asset/body/rig compatibility is not established."""


class TransitionError(LedgerError):
    """Raised when a transaction is illegal, stale, or in the wrong status."""


JOURNAL_GENESIS_SHA256 = hashlib.sha256(
    b"kira.garment.transaction-journal.v1"
).hexdigest()


def _canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LedgerError("journal data is not canonical JSON") from exc
    return hashlib.sha256(payload).hexdigest()


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUSPENDED = "suspended"
    COMMITTED = "committed"
    CANCELLED = "cancelled"
    REFUSED = "refused"
    RECOVERED_ROLLBACK = "recovered_rollback"


ACTIVE_TRANSACTION_STATUSES = frozenset({TransactionStatus.PENDING, TransactionStatus.SUSPENDED})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expected_location(definition: GarmentDefinition, state: GarmentState) -> str:
    role_by_state = {
        GarmentState.HANGING_ON_HOOK: "world_wall_hook",
        GarmentState.GRASPED_FROM_HOOK: "hand_grip",
        GarmentState.RIGHT_SLEEVE_THREADED: "right_sleeve_portal",
        GarmentState.LEFT_SLEEVE_THREADED: "left_sleeve_portal",
        GarmentState.BOTH_SLEEVES_THREADED: "garment_shoulders",
        GarmentState.WORN_OPEN: "body_shoulders",
        GarmentState.WORN_TIED: "body_waist",
        GarmentState.HELD_AFTER_REMOVAL: "hand_grip",
        GarmentState.PLACED_ON_BED: "bed_surface",
        GarmentState.THROWN_IN_FLIGHT: "bed_surface",
        GarmentState.SETTLED_ON_BED: "bed_surface",
    }
    return definition.anchor_for_role(role_by_state[state]).anchor_id


@dataclass(slots=True)
class GarmentTransaction:
    transaction_id: str
    item_instance_id: str
    affordance_id: str
    actor_id: str
    from_state: GarmentState
    target_state: GarmentState
    from_owner_scope: OwnerScope
    from_owner_id: str
    target_owner_scope: OwnerScope
    target_owner_id: str
    from_location_anchor_id: str
    target_location_anchor_id: str
    expected_revision: int
    asset_sha256: str
    body_sha256: str
    rig_sha256: str
    subject_id: str
    body_owner_subject_id: str
    maturity_class: MaturityClass
    consent_record_id: str
    consent_revocable: bool
    privacy_active: bool
    privacy_observers_allowed: bool
    privacy_log_scope: str
    privacy_raw_visual_recording: bool
    last_evidence_trace_sha256: str = ""
    last_evidence_context_sha256: str = ""
    last_decision_sha256: str = ""
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    resolution_reason: str = ""
    last_evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "item_instance_id": self.item_instance_id,
            "affordance_id": self.affordance_id,
            "actor_id": self.actor_id,
            "from_state": self.from_state.value,
            "target_state": self.target_state.value,
            "from_owner_scope": self.from_owner_scope.value,
            "from_owner_id": self.from_owner_id,
            "target_owner_scope": self.target_owner_scope.value,
            "target_owner_id": self.target_owner_id,
            "from_location_anchor_id": self.from_location_anchor_id,
            "target_location_anchor_id": self.target_location_anchor_id,
            "expected_revision": self.expected_revision,
            "asset_sha256": self.asset_sha256,
            "body_sha256": self.body_sha256,
            "rig_sha256": self.rig_sha256,
            "subject_id": self.subject_id,
            "body_owner_subject_id": self.body_owner_subject_id,
            "maturity_class": self.maturity_class.value,
            "consent_record_id": self.consent_record_id,
            "consent_revocable": self.consent_revocable,
            "privacy_active": self.privacy_active,
            "privacy_observers_allowed": self.privacy_observers_allowed,
            "privacy_log_scope": self.privacy_log_scope,
            "privacy_raw_visual_recording": self.privacy_raw_visual_recording,
            "last_evidence_trace_sha256": self.last_evidence_trace_sha256,
            "last_evidence_context_sha256": self.last_evidence_context_sha256,
            "last_decision_sha256": self.last_decision_sha256,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolution_reason": self.resolution_reason,
            "last_evidence": deepcopy(self.last_evidence),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GarmentTransaction":
        return cls(
            transaction_id=str(value.get("transaction_id", "")),
            item_instance_id=str(value.get("item_instance_id", "")),
            affordance_id=str(value.get("affordance_id", "")),
            actor_id=str(value.get("actor_id", "")),
            from_state=GarmentState(value.get("from_state")),
            target_state=GarmentState(value.get("target_state")),
            from_owner_scope=OwnerScope(value.get("from_owner_scope")),
            from_owner_id=str(value.get("from_owner_id", "")),
            target_owner_scope=OwnerScope(value.get("target_owner_scope")),
            target_owner_id=str(value.get("target_owner_id", "")),
            from_location_anchor_id=str(value.get("from_location_anchor_id", "")),
            target_location_anchor_id=str(value.get("target_location_anchor_id", "")),
            expected_revision=value.get("expected_revision", -1),
            asset_sha256=str(value.get("asset_sha256", "")),
            body_sha256=str(value.get("body_sha256", "")),
            rig_sha256=str(value.get("rig_sha256", "")),
            subject_id=str(value.get("subject_id", "")),
            body_owner_subject_id=str(value.get("body_owner_subject_id", "")),
            maturity_class=MaturityClass(value.get("maturity_class")),
            consent_record_id=str(value.get("consent_record_id", "")),
            consent_revocable=value.get("consent_revocable") is True,
            privacy_active=value.get("privacy_active") is True,
            privacy_observers_allowed=value.get("privacy_observers_allowed") is True,
            privacy_log_scope=str(value.get("privacy_log_scope", "")),
            privacy_raw_visual_recording=value.get("privacy_raw_visual_recording") is True,
            last_evidence_trace_sha256=str(value.get("last_evidence_trace_sha256", "")),
            last_evidence_context_sha256=str(value.get("last_evidence_context_sha256", "")),
            last_decision_sha256=str(value.get("last_decision_sha256", "")),
            status=TransactionStatus(value.get("status")),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            resolution_reason=str(value.get("resolution_reason", "")),
            last_evidence=deepcopy(value.get("last_evidence")) if isinstance(value.get("last_evidence"), dict) else None,
        )


class GarmentLedger:
    """Single-source-of-truth inventory with optimistic revision checks."""

    def __init__(self, definitions: Iterable[GarmentDefinition]) -> None:
        self._definitions: dict[str, GarmentDefinition] = {}
        self._instances: dict[str, GarmentInstance] = {}
        self._transactions: dict[str, GarmentTransaction] = {}
        self._journal: list[dict[str, Any]] = []
        for definition in definitions:
            if definition.garment_type_id in self._definitions:
                raise ContractError(f"duplicate garment definition: {definition.garment_type_id}")
            self._definitions[definition.garment_type_id] = definition
        if not self._definitions:
            raise ContractError("ledger requires at least one garment definition")

    def _append_journal(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict) or not str(event.get("event", "")).strip():
            raise LedgerError("journal event must be a named object")
        reserved = {"sequence", "previous_entry_sha256", "entry_sha256"}
        if reserved & set(event):
            raise LedgerError("journal caller supplied reserved chain fields")
        entry = deepcopy(event)
        entry["sequence"] = len(self._journal)
        entry["previous_entry_sha256"] = (
            self._journal[-1]["entry_sha256"]
            if self._journal
            else JOURNAL_GENESIS_SHA256
        )
        entry["entry_sha256"] = _canonical_sha256(entry)
        self._journal.append(entry)

    def _journal_binding(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "algorithm": "sha256",
            "genesis_sha256": JOURNAL_GENESIS_SHA256,
            "entry_count": len(self._journal),
            "head_sha256": (
                self._journal[-1]["entry_sha256"]
                if self._journal
                else JOURNAL_GENESIS_SHA256
            ),
        }

    @staticmethod
    def _validate_journal(
        journal: Any,
        binding: Any,
    ) -> None:
        if not isinstance(journal, list) or not isinstance(binding, dict):
            raise LedgerError("snapshot journal and binding are required")
        if (
            binding.get("schema_version") != 1
            or binding.get("algorithm") != "sha256"
            or binding.get("genesis_sha256") != JOURNAL_GENESIS_SHA256
        ):
            raise LedgerError("snapshot journal binding metadata is invalid")
        entry_count = binding.get("entry_count")
        if (
            isinstance(entry_count, bool)
            or not isinstance(entry_count, int)
            or entry_count != len(journal)
        ):
            raise LedgerError("snapshot journal count binding does not match")

        previous = JOURNAL_GENESIS_SHA256
        for sequence, raw in enumerate(journal):
            if not isinstance(raw, dict):
                raise LedgerError("snapshot journal entry is malformed")
            entry = deepcopy(raw)
            entry_hash = entry.pop("entry_sha256", "")
            if entry.get("sequence") != sequence:
                raise LedgerError("snapshot journal sequence was deleted or reordered")
            if entry.get("previous_entry_sha256") != previous:
                raise LedgerError("snapshot journal previous-hash chain is broken")
            if not isinstance(entry_hash, str) or not SHA256_RE.fullmatch(entry_hash):
                raise LedgerError("snapshot journal entry hash is malformed")
            if _canonical_sha256(entry) != entry_hash:
                raise LedgerError("snapshot journal entry content was tampered")
            previous = entry_hash

        if binding.get("head_sha256") != previous:
            raise LedgerError("snapshot journal head binding does not match")

    def register_instance(self, instance: GarmentInstance) -> None:
        """Register exactly one authoritative instance; duplicate ids fail closed."""

        if instance.item_instance_id in self._instances:
            raise DuplicateInstanceError(f"duplicate item_instance_id: {instance.item_instance_id}")
        definition = self._definition_for(instance)
        if (
            definition.compatible_subject_id == "unassigned_subject"
            or definition.maturity_class is MaturityClass.UNASSIGNED_BLOCKED
        ):
            raise CompatibilityError("staged garment definition has no approved subject/maturity binding")
        if (
            instance.assigned_subject_id != definition.compatible_subject_id
            or instance.body_owner_subject_id != definition.compatible_subject_id
        ):
            raise CompatibilityError("garment instance subject/body ownership mismatch")
        if instance.maturity_class is not definition.maturity_class:
            raise CompatibilityError("garment instance maturity policy mismatch")
        expected_location = _expected_location(definition, instance.state)
        if instance.location_anchor_id != expected_location:
            raise ContractError(
                f"state {instance.state.value} requires location anchor {expected_location}"
            )
        stored = GarmentInstance.from_dict(instance.to_dict())
        self._instances[stored.item_instance_id] = stored
        self._append_journal(
            {
                "event": "registered",
                "at": _now(),
                "item_instance_id": stored.item_instance_id,
                "subject_id": stored.assigned_subject_id,
                "maturity_class": stored.maturity_class.value,
                "revision": stored.revision,
            }
        )
        self.assert_invariants()

    def instance(self, item_instance_id: str) -> GarmentInstance:
        """Return a detached read model; callers cannot mutate ledger state directly."""

        return GarmentInstance.from_dict(self._instance_ref(item_instance_id).to_dict())

    def _instance_ref(self, item_instance_id: str) -> GarmentInstance:
        try:
            return self._instances[item_instance_id]
        except KeyError as exc:
            raise LedgerError(f"unknown item instance: {item_instance_id}") from exc

    def transaction(self, transaction_id: str) -> GarmentTransaction:
        """Return a detached transaction read model."""

        return GarmentTransaction.from_dict(self._transaction_ref(transaction_id).to_dict())

    def _transaction_ref(self, transaction_id: str) -> GarmentTransaction:
        try:
            return self._transactions[transaction_id]
        except KeyError as exc:
            raise TransitionError(f"unknown transaction: {transaction_id}") from exc

    def _definition_for(self, instance: GarmentInstance) -> GarmentDefinition:
        try:
            return self._definitions[instance.garment_type_id]
        except KeyError as exc:
            raise ContractError(
                f"no definition for garment type {instance.garment_type_id}"
            ) from exc

    def _active_transaction_for(self, item_instance_id: str) -> GarmentTransaction | None:
        matches = [
            transaction
            for transaction in self._transactions.values()
            if transaction.item_instance_id == item_instance_id
            and transaction.status in ACTIVE_TRANSACTION_STATUSES
        ]
        if len(matches) > 1:
            raise TransitionError(f"multiple active transactions for {item_instance_id}")
        return matches[0] if matches else None

    def begin_transition(
        self,
        item_instance_id: str,
        affordance_id: str,
        *,
        actor_id: str,
        expected_revision: int,
        asset_sha256: str,
        body_sha256: str = "",
        rig_sha256: str = "",
        subject_id: str = "",
        body_owner_subject_id: str = "",
        maturity_class: MaturityClass | str = MaturityClass.UNASSIGNED_BLOCKED,
        consent: dict[str, Any] | None = None,
        privacy: dict[str, Any] | None = None,
        target_world_id: str | None = None,
        transaction_id: str | None = None,
    ) -> GarmentTransaction:
        """Prepare a transition without changing inventory or ownership."""

        instance = self._instance_ref(item_instance_id)
        definition = self._definition_for(instance)
        if self._active_transaction_for(item_instance_id):
            raise TransitionError(f"item {item_instance_id} already has an active transaction")
        if not actor_id.strip():
            raise TransitionError("actor_id is required")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise TransitionError("expected_revision must be an integer, not a flag")
        if expected_revision != instance.revision:
            raise TransitionError(
                f"stale revision {expected_revision}; current revision is {instance.revision}"
            )
        affordance = definition.affordance(affordance_id)
        if instance.state not in affordance.from_states:
            raise TransitionError(
                f"{affordance_id} is illegal from {instance.state.value}"
            )
        if asset_sha256 != definition.asset_sha256:
            raise CompatibilityError("garment asset hash mismatch")
        try:
            maturity = maturity_class if isinstance(maturity_class, MaturityClass) else MaturityClass(maturity_class)
        except ValueError as exc:
            raise CompatibilityError("unknown maturity policy") from exc
        if subject_id != definition.compatible_subject_id:
            raise CompatibilityError("garment subject mismatch")
        if body_owner_subject_id != definition.compatible_subject_id:
            raise CompatibilityError("body owner does not match garment subject")
        if maturity is not definition.maturity_class:
            raise CompatibilityError("garment maturity policy mismatch")
        if (
            instance.assigned_subject_id != subject_id
            or instance.body_owner_subject_id != body_owner_subject_id
            or instance.maturity_class is not maturity
        ):
            raise CompatibilityError("instance subject/body/maturity binding mismatch")

        target_scope = owner_scope_for_state(affordance.target_state)
        body_participates = instance.state in AVATAR_STATES or affordance.target_state in AVATAR_STATES
        consent = consent if isinstance(consent, dict) else {}
        privacy = privacy if isinstance(privacy, dict) else {}
        consent_record_id = str(consent.get("consent_record_id", "")).strip()
        if body_participates:
            if body_sha256 != definition.compatible_body_sha256:
                raise CompatibilityError("body hash mismatch")
            if rig_sha256 != definition.compatible_rig_sha256:
                raise CompatibilityError("rig hash mismatch")
            if str(consent.get("subject_id", "")).strip() != subject_id:
                raise TransitionError("consent belongs to the wrong subject")
            if str(consent.get("decision", "")).strip().lower() != "consented":
                raise TransitionError("subject consent is required before a garment step")
            if not consent_record_id:
                raise TransitionError("consent record identity is required")
            if consent.get("revocable") is not True:
                raise TransitionError("garment consent must remain revocable")
            if consent.get("refusal_active") is not False:
                raise TransitionError("active or unknown refusal state blocks the garment step")
            if str(privacy.get("subject_id", "")).strip() != subject_id:
                raise TransitionError("privacy state belongs to the wrong subject")
            if privacy.get("active") is not True:
                raise TransitionError("private wardrobe mode must be active")
            if privacy.get("observers_allowed") is not False:
                raise TransitionError("private wardrobe mode must exclude observers")
            if str(privacy.get("log_scope", "")).strip().lower() not in {"metadata_only", "evidence_only"}:
                raise TransitionError("privacy logging must be metadata/evidence only")
            if privacy.get("raw_visual_recording") is not False:
                raise TransitionError("raw wardrobe imagery may not be retained")

        if instance.owner_scope is OwnerScope.AVATAR and instance.owner_id != actor_id:
            raise TransitionError("only the current avatar owner may manipulate a worn/held garment")

        if target_scope is OwnerScope.AVATAR:
            target_owner_id = actor_id
        else:
            target_owner_id = target_world_id or (
                instance.owner_id if instance.owner_scope is OwnerScope.WORLD else ""
            )
            if not target_owner_id.strip():
                raise TransitionError("target_world_id is required for avatar-to-world transfer")

        tx_id = transaction_id or f"garment_tx_{uuid4().hex}"
        if not tx_id.strip() or tx_id in self._transactions:
            raise TransitionError(f"transaction id is empty or already exists: {tx_id!r}")

        transaction = GarmentTransaction(
            transaction_id=tx_id,
            item_instance_id=item_instance_id,
            affordance_id=affordance_id,
            actor_id=actor_id,
            from_state=instance.state,
            target_state=affordance.target_state,
            from_owner_scope=instance.owner_scope,
            from_owner_id=instance.owner_id,
            target_owner_scope=target_scope,
            target_owner_id=target_owner_id,
            from_location_anchor_id=instance.location_anchor_id,
            target_location_anchor_id=_expected_location(definition, affordance.target_state),
            expected_revision=instance.revision,
            asset_sha256=asset_sha256,
            body_sha256=body_sha256,
            rig_sha256=rig_sha256,
            subject_id=subject_id,
            body_owner_subject_id=body_owner_subject_id,
            maturity_class=maturity,
            consent_record_id=consent_record_id,
            consent_revocable=consent.get("revocable") is True,
            privacy_active=privacy.get("active") is True,
            privacy_observers_allowed=privacy.get("observers_allowed") is True,
            privacy_log_scope=str(privacy.get("log_scope", "")).strip().lower(),
            privacy_raw_visual_recording=privacy.get("raw_visual_recording") is True,
        )
        self._transactions[tx_id] = transaction
        self._append_journal(
            {
                "event": "transition_begun",
                "at": transaction.created_at,
                "transaction_id": tx_id,
                "item_instance_id": item_instance_id,
                "subject_id": subject_id,
                "maturity_class": maturity.value,
                "consent_record_id": consent_record_id,
                "from_state": instance.state.value,
                "target_state": affordance.target_state.value,
            }
        )
        self.assert_invariants()
        return GarmentTransaction.from_dict(transaction.to_dict())

    def commit_transition(
        self,
        transaction_id: str,
        evidence: dict[str, Any],
    ) -> EvidenceDecision:
        """Evaluate and atomically commit; blocked evidence leaves state untouched."""

        transaction = self._transaction_ref(transaction_id)
        if transaction.status is not TransactionStatus.PENDING:
            raise TransitionError(
                f"transaction {transaction_id} is {transaction.status.value}, not pending"
            )
        instance = self._instance_ref(transaction.item_instance_id)
        self._require_checkpoint(instance, transaction)
        definition = self._definition_for(instance)
        affordance = definition.affordance(transaction.affordance_id)
        decision = evaluate_garment_transition(
            definition,
            affordance,
            evidence,
            transaction_id=transaction.transaction_id,
            item_instance_id=transaction.item_instance_id,
            consent_record_id=transaction.consent_record_id,
        )
        transaction.last_evidence = deepcopy(decision.to_dict())
        transaction.last_evidence_trace_sha256 = decision.raw_trace_sha256
        transaction.last_evidence_context_sha256 = decision.evidence_context_sha256
        transaction.last_decision_sha256 = decision.decision_sha256
        transaction.updated_at = _now()
        self._append_journal(
            {
                "event": "evidence_evaluated",
                "at": transaction.updated_at,
                "transaction_id": transaction_id,
                "item_instance_id": transaction.item_instance_id,
                "raw_trace_sha256": decision.raw_trace_sha256,
                "evidence_context_sha256": decision.evidence_context_sha256,
                "decision_sha256": decision.decision_sha256,
                "status": decision.status,
                "reasons": list(decision.reasons),
            }
        )
        if not decision.passed:
            return decision

        previous = instance.to_dict()
        try:
            instance.state = transaction.target_state
            instance.owner_scope = transaction.target_owner_scope
            instance.owner_id = transaction.target_owner_id
            instance.location_anchor_id = transaction.target_location_anchor_id
            instance.revision += 1
            transaction.status = TransactionStatus.COMMITTED
            transaction.resolution_reason = "physical evidence gate passed"
            transaction.updated_at = _now()
            self.assert_invariants()
        except Exception:
            restored = GarmentInstance.from_dict(previous)
            self._instances[instance.item_instance_id] = restored
            transaction.status = TransactionStatus.PENDING
            transaction.resolution_reason = ""
            raise

        self._append_journal(
            {
                "event": "transition_committed",
                "at": transaction.updated_at,
                "transaction_id": transaction_id,
                "item_instance_id": instance.item_instance_id,
                "state": instance.state.value,
                "owner_scope": instance.owner_scope.value,
                "owner_id": instance.owner_id,
                "revision": instance.revision,
                "raw_trace_sha256": decision.raw_trace_sha256,
                "evidence_context_sha256": decision.evidence_context_sha256,
                "decision_sha256": decision.decision_sha256,
            }
        )
        return decision

    def suspend_transition(self, transaction_id: str, reason: str) -> None:
        transaction = self._transaction_ref(transaction_id)
        if transaction.status is not TransactionStatus.PENDING:
            raise TransitionError("only a pending transaction can be suspended")
        if not reason.strip():
            raise TransitionError("suspension reason is required")
        transaction.status = TransactionStatus.SUSPENDED
        transaction.resolution_reason = reason.strip()
        transaction.updated_at = _now()
        self.assert_invariants()

    def resume_transition(self, transaction_id: str) -> None:
        transaction = self._transaction_ref(transaction_id)
        if transaction.status is not TransactionStatus.SUSPENDED:
            raise TransitionError("only a suspended transaction can be resumed")
        self._require_checkpoint(self._instance_ref(transaction.item_instance_id), transaction)
        transaction.status = TransactionStatus.PENDING
        transaction.resolution_reason = ""
        transaction.updated_at = _now()
        self.assert_invariants()

    def cancel_transition(self, transaction_id: str, reason: str) -> None:
        self._close_without_commit(transaction_id, TransactionStatus.CANCELLED, reason)

    def refuse_transition(self, transaction_id: str, reason: str) -> None:
        """Record an autonomous refusal without treating it as mechanical failure."""

        self._close_without_commit(transaction_id, TransactionStatus.REFUSED, reason)

    def _close_without_commit(
        self,
        transaction_id: str,
        status: TransactionStatus,
        reason: str,
    ) -> None:
        transaction = self._transaction_ref(transaction_id)
        if transaction.status not in ACTIVE_TRANSACTION_STATUSES:
            raise TransitionError("only a pending/suspended transaction can be closed")
        if not reason.strip():
            raise TransitionError("resolution reason is required")
        self._require_checkpoint(self._instance_ref(transaction.item_instance_id), transaction)
        transaction.status = status
        transaction.resolution_reason = reason.strip()
        transaction.updated_at = _now()
        self._append_journal(
            {
                "event": f"transition_{status.value}",
                "at": transaction.updated_at,
                "transaction_id": transaction_id,
                "item_instance_id": transaction.item_instance_id,
                "reason": transaction.resolution_reason,
            }
        )
        self.assert_invariants()

    def _require_checkpoint(
        self,
        instance: GarmentInstance,
        transaction: GarmentTransaction,
    ) -> None:
        if (
            instance.revision != transaction.expected_revision
            or instance.state is not transaction.from_state
            or instance.owner_scope is not transaction.from_owner_scope
            or instance.owner_id != transaction.from_owner_id
            or instance.location_anchor_id != transaction.from_location_anchor_id
        ):
            raise TransitionError("transaction checkpoint is stale; refusing partial transfer")

    def recover_after_crash(self) -> int:
        """Rollback incomplete intents to the already-committed inventory checkpoint."""

        recovered = 0
        for transaction in self._transactions.values():
            if transaction.status not in ACTIVE_TRANSACTION_STATUSES:
                continue
            self._require_checkpoint(self._instance_ref(transaction.item_instance_id), transaction)
            transaction.status = TransactionStatus.RECOVERED_ROLLBACK
            transaction.resolution_reason = "incomplete transition rolled back after crash"
            transaction.updated_at = _now()
            recovered += 1
            self._append_journal(
                {
                    "event": "transition_recovered_rollback",
                    "at": transaction.updated_at,
                    "transaction_id": transaction.transaction_id,
                    "item_instance_id": transaction.item_instance_id,
                }
            )
        self.assert_invariants()
        return recovered

    def inventory_views(self) -> dict[str, list[dict[str, Any]]]:
        """Return disjoint projections; each item appears in exactly one view."""

        views: dict[str, list[dict[str, Any]]] = {"world": [], "avatar": []}
        for instance in self._instances.values():
            views[instance.owner_scope.value].append(instance.to_dict())
        for values in views.values():
            values.sort(key=lambda item: item["item_instance_id"])
        return views

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "instances": [
                self._instances[key].to_dict() for key in sorted(self._instances)
            ],
            "transactions": [
                self._transactions[key].to_dict() for key in sorted(self._transactions)
            ],
            "journal": deepcopy(self._journal),
            "journal_binding": self._journal_binding(),
        }

    @classmethod
    def from_snapshot(
        cls,
        definitions: Iterable[GarmentDefinition],
        snapshot: dict[str, Any],
        *,
        recover_incomplete: bool = True,
    ) -> "GarmentLedger":
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 2:
            raise LedgerError("unsupported or malformed garment ledger snapshot")
        ledger = cls(definitions)
        instances = snapshot.get("instances")
        transactions = snapshot.get("transactions")
        if not isinstance(instances, list) or not isinstance(transactions, list):
            raise LedgerError("snapshot instances and transactions must be lists")
        for raw in instances:
            if not isinstance(raw, dict):
                raise LedgerError("malformed instance snapshot")
            instance = GarmentInstance.from_dict(raw)
            if instance.item_instance_id in ledger._instances:
                raise DuplicateInstanceError(
                    f"duplicate item in snapshot: {instance.item_instance_id}"
                )
            ledger._definition_for(instance)
            ledger._instances[instance.item_instance_id] = instance
        for raw in transactions:
            if not isinstance(raw, dict):
                raise LedgerError("malformed transaction snapshot")
            transaction = GarmentTransaction.from_dict(raw)
            if not transaction.transaction_id or transaction.transaction_id in ledger._transactions:
                raise TransitionError("empty or duplicate transaction id in snapshot")
            ledger._transactions[transaction.transaction_id] = transaction
        ledger._validate_journal(
            snapshot.get("journal"),
            snapshot.get("journal_binding"),
        )
        ledger._journal = deepcopy(snapshot["journal"])
        ledger.assert_invariants()
        if recover_incomplete:
            ledger.recover_after_crash()
        return ledger

    def assert_invariants(self) -> None:
        self._validate_journal(self._journal, self._journal_binding())
        active_by_item: dict[str, int] = {}
        for item_id, instance in self._instances.items():
            if item_id != instance.item_instance_id:
                raise LedgerError("inventory key and persistent item id disagree")
            definition = self._definition_for(instance)
            if (
                definition.compatible_subject_id == "unassigned_subject"
                or definition.maturity_class is MaturityClass.UNASSIGNED_BLOCKED
            ):
                raise LedgerError("runtime inventory uses an unassigned staged definition")
            if (
                instance.assigned_subject_id != definition.compatible_subject_id
                or instance.body_owner_subject_id != definition.compatible_subject_id
                or instance.maturity_class is not definition.maturity_class
            ):
                raise LedgerError("inventory subject/body/maturity binding is incompatible")
            if instance.owner_scope is not owner_scope_for_state(instance.state):
                raise LedgerError("garment owner scope conflicts with garment state")
            if instance.location_anchor_id != _expected_location(definition, instance.state):
                raise LedgerError("garment location anchor conflicts with garment state")
        for transaction_id, transaction in self._transactions.items():
            if transaction_id != transaction.transaction_id or not transaction_id.strip():
                raise LedgerError("transaction key and persistent transaction id disagree")
            if transaction.item_instance_id not in self._instances:
                raise LedgerError("transaction references an unknown item")
            instance = self._instances[transaction.item_instance_id]
            definition = self._definition_for(instance)
            try:
                affordance = definition.affordance(transaction.affordance_id)
            except ContractError as exc:
                raise LedgerError("transaction references an unknown affordance") from exc
            if transaction.from_state not in affordance.from_states:
                raise LedgerError("transaction source state is illegal for its affordance")
            if transaction.target_state is not affordance.target_state:
                raise LedgerError("transaction target state is illegal for its affordance")
            if transaction.from_owner_scope is not owner_scope_for_state(transaction.from_state):
                raise LedgerError("transaction source ownership conflicts with source state")
            if transaction.target_owner_scope is not owner_scope_for_state(transaction.target_state):
                raise LedgerError("transaction target ownership conflicts with target state")
            if transaction.from_location_anchor_id != _expected_location(definition, transaction.from_state):
                raise LedgerError("transaction source anchor conflicts with source state")
            if transaction.target_location_anchor_id != _expected_location(definition, transaction.target_state):
                raise LedgerError("transaction target anchor conflicts with target state")
            if transaction.asset_sha256 != definition.asset_sha256:
                raise LedgerError("transaction garment asset hash is incompatible")
            if (
                transaction.subject_id != definition.compatible_subject_id
                or transaction.body_owner_subject_id != definition.compatible_subject_id
                or transaction.maturity_class is not definition.maturity_class
            ):
                raise LedgerError("transaction subject/body/maturity binding is incompatible")
            body_participates = (
                transaction.from_state in AVATAR_STATES
                or transaction.target_state in AVATAR_STATES
            )
            if body_participates and (
                transaction.body_sha256 != definition.compatible_body_sha256
                or transaction.rig_sha256 != definition.compatible_rig_sha256
            ):
                raise LedgerError("transaction body/rig hashes are incompatible")
            if body_participates and (
                not transaction.consent_record_id
                or transaction.consent_revocable is not True
                or transaction.privacy_active is not True
                or transaction.privacy_observers_allowed is not False
                or transaction.privacy_log_scope not in {"metadata_only", "evidence_only"}
                or transaction.privacy_raw_visual_recording is not False
            ):
                raise LedgerError("transaction consent/privacy contract is incompatible")
            if transaction.last_evidence is not None:
                if transaction.last_evidence_trace_sha256 and not SHA256_RE.fullmatch(transaction.last_evidence_trace_sha256):
                    raise LedgerError("transaction evidence trace hash is malformed")
                if transaction.last_evidence.get("raw_trace_sha256") != transaction.last_evidence_trace_sha256:
                    raise LedgerError("transaction evidence decision is not bound to its raw trace hash")
                if transaction.last_evidence.get("passed") is True and not transaction.last_evidence_trace_sha256:
                    raise LedgerError("passing evidence has no preserved raw trace hash")
                if not SHA256_RE.fullmatch(transaction.last_evidence_context_sha256):
                    raise LedgerError("transaction complete evidence-context hash is malformed")
                if not SHA256_RE.fullmatch(transaction.last_decision_sha256):
                    raise LedgerError("transaction decision hash is malformed")
                if transaction.last_evidence.get("evidence_context_sha256") != transaction.last_evidence_context_sha256:
                    raise LedgerError("transaction decision is not bound to its evidence context")
                if transaction.last_evidence.get("decision_sha256") != transaction.last_decision_sha256:
                    raise LedgerError("transaction decision hash binding disagrees")
                passed = transaction.last_evidence.get("passed")
                reasons = transaction.last_evidence.get("reasons")
                if not isinstance(passed, bool) or not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
                    raise LedgerError("transaction evidence result is malformed")
                if transaction.last_evidence.get("status") != ("passed" if passed else "blocked"):
                    raise LedgerError("transaction evidence status conflicts with its result")
                if (
                    transaction.last_evidence.get("transaction_id") != transaction.transaction_id
                    or transaction.last_evidence.get("item_instance_id") != transaction.item_instance_id
                    or transaction.last_evidence.get("evidence_gate") != affordance.evidence_gate
                ):
                    raise LedgerError("transaction evidence decision identity is incompatible")
                expected_decision_hash = compute_decision_sha256(
                    transaction_id=transaction.transaction_id,
                    item_instance_id=transaction.item_instance_id,
                    evidence_gate=affordance.evidence_gate,
                    raw_trace_sha256=transaction.last_evidence_trace_sha256,
                    evidence_context_sha256=transaction.last_evidence_context_sha256,
                    passed=passed,
                    reasons=reasons,
                )
                if expected_decision_hash != transaction.last_decision_sha256:
                    raise LedgerError("transaction evidence/result decision hash was tampered")
            if (
                isinstance(transaction.expected_revision, bool)
                or not isinstance(transaction.expected_revision, int)
                or transaction.expected_revision < 0
            ):
                raise LedgerError("transaction revision checkpoint is malformed")
            if not transaction.actor_id.strip() or not transaction.from_owner_id.strip() or not transaction.target_owner_id.strip():
                raise LedgerError("transaction actor and owners must be non-empty")
            if transaction.from_owner_scope is OwnerScope.AVATAR and transaction.from_owner_id != transaction.actor_id:
                raise LedgerError("transaction actor does not own the source avatar garment")
            if transaction.target_owner_scope is OwnerScope.AVATAR and transaction.target_owner_id != transaction.actor_id:
                raise LedgerError("transaction actor does not own the target avatar garment")
            if transaction.status in ACTIVE_TRANSACTION_STATUSES:
                active_by_item[transaction.item_instance_id] = (
                    active_by_item.get(transaction.item_instance_id, 0) + 1
                )
                self._require_checkpoint(
                    self._instances[transaction.item_instance_id], transaction
                )
        duplicates = [item_id for item_id, count in active_by_item.items() if count > 1]
        if duplicates:
            raise LedgerError(f"multiple active transactions for items: {duplicates}")
