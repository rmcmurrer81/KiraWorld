"""Bounded present-day reflection over Kira and Lisa's shared college memory.

This module verifies an immutable shared-memory source and gives exactly one
selected person a private reflection context.  It never rewrites the historical
record, exposes the locked intimate sequence, imports the other person's
current private emotion, or treats present-day curriculum knowledge as proof of
what either person knew or experienced during college.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Sequence

from Core.adult_health_curriculum_runtime import (
    ConfirmedAdultHealthCurriculumRuntime,
    PERSON_CLASSIFICATION_BINDINGS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_BINDING = {
    "path": "Data/memory_reflection/kira_lisa_college_present_day_reflection_context_v1.json",
    "sha256": "cb1839f489703979bb15c1e9e6bb7be3f2049a658cfd0ff49a6b659843ee3d1e",
    "context_id": "kira_lisa_college_present_day_reflection_context_v1",
}
CONTROLLING_DOCUMENT_BINDINGS = (
    {
        "path": "System/Docs/MEMORY_RECALL_AND_RECONSTRUCTION_MODEL_v1.md",
        "sha256": "0a3fba10f4ecfa44e7e72f1f5f0f627bbbcc3e0fc7d4c7f727a3b3bb00d23339",
    },
    {
        "path": "System/Docs/MEMORY_RECONSTRUCTION_WORLD_IMPLEMENTATION_NOTES_v1.md",
        "sha256": "239f6227054d3e8ae11be4eec0de167f8c83cfe6c6ada5ea994dde0b37fe0d2b",
    },
    {
        "path": "System/Docs/MEMORY_&_PRIVACY_SYSTEM_v2.md",
        "sha256": "c46d95fcb7fd1fabdd858506ae9b6193d47cd6a97abf1adf4d2ad65713197af7",
    },
    {
        "path": "System/Docs/PRIVACY_ROOM_SESSION_STATE_v1.md",
        "sha256": "88e17d58135d2e173f8364a75bad5b6a10ef294d6c2211a09c739e4a8c932431",
    },
)
MEMORY_BINDING = {
    "path": "Data/memory_seeds/shared_kira_lisa_college_phase_001.draft.json",
    "sha256": "5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7",
    "memory_id": "shared_kira_lisa_college_phase_001",
}
OWNER_DIRECTIVE_BINDING = {
    "path": "Data/person_classification/kira_lisa_college_reflection_owner_directive_20260809.json",
    "sha256": "24d0ea68f75b0f5bb50105eea76fcdfde87cc44c4e56612bb8ef8159881e4538",
    "directive_id": "kira_lisa_college_reflection_owner_20260809_c24dd041e0c53383",
}
EXACT_PERSON_IDS = ("kira", "lisa")
EXPECTED_HEALTH_MODULE_IDS = (
    "consent_communication_and_relationships",
    "physiological_response_sensation_pleasure_and_preference_separation",
    "contraception_and_barrier_methods",
    "sti_prevention_testing_and_health_uncertainty",
)
ALLOWED_RECONSTRUCTION_SOURCE_LABELS = frozenset(
    {
        "stored_shared_anchor",
        "selected_person_private_recall",
        "inferred_reconstruction",
        "current_interpretation",
    }
)
EXPECTED_SAFE_SUMMARY = (
    "Kira and Lisa had repeated private moments of closeness during their college phase.",
    "The source memory describes the private closeness as including sexual intimacy remembered as meaningful by both participants.",
    "Their stored historical interpretations differed.",
    "They ultimately valued their friendship more than continuing romantically.",
    "The stored long-term outcome is deeper trust and an unresolved emotional thread, not a permanent romantic relationship.",
)


class CollegeReflectionContextError(ValueError):
    """The pinned reflection policy or its sources failed validation."""


class CollegeReflectionLeaseError(PermissionError):
    """A caller attempted to cross a person-owned reflection boundary."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _project_path(raw: str) -> Path:
    value = Path(str(raw or ""))
    if not raw or value.is_absolute() or ".." in value.parts:
        raise CollegeReflectionContextError("reflection binding path is unsafe")
    resolved = (PROJECT_ROOT / value).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise CollegeReflectionContextError(
            "reflection binding escaped the project root"
        ) from exc
    return resolved


def _read_pinned_json(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = _project_path(str(binding.get("path") or ""))
    expected = str(binding.get("sha256") or "").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise CollegeReflectionContextError(f"{label} digest is invalid")
    if _sha256_file(path) != expected:
        raise CollegeReflectionContextError(f"{label} digest mismatch")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CollegeReflectionContextError(f"unable to read {label}") from exc
    if not isinstance(value, dict):
        raise CollegeReflectionContextError(f"{label} must be a JSON object")
    return value


def _text(value: object, field: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CollegeReflectionContextError(f"{field} must be non-empty text")
    normalized = value.strip()
    if len(normalized) > maximum or any(
        ord(character) < 32 and character not in "\t" for character in normalized
    ):
        raise CollegeReflectionContextError(f"{field} is unsafe or too long")
    return normalized


def _validate_sha_text(value: Mapping[str, Any], label: str) -> None:
    source_text = str(value.get("source_text") or "")
    source_sha = str(value.get("source_text_sha256") or "").casefold()
    if not source_text or hashlib.sha256(source_text.encode("utf-8")).hexdigest() != source_sha:
        raise CollegeReflectionContextError(f"{label} source digest mismatch")


def _validate_policy() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = _read_pinned_json(POLICY_BINDING, "reflection policy")
    directive = _read_pinned_json(OWNER_DIRECTIVE_BINDING, "owner directive")
    memory = _read_pinned_json(MEMORY_BINDING, "shared college memory")
    failures: list[str] = []

    if policy.get("schema_version") != 1:
        failures.append("policy_schema")
    if policy.get("status") != (
        "STATIC_PRESENT_DAY_REFLECTION_CONTEXT_READY_NO_MEMORY_MUTATION"
    ):
        failures.append("policy_status")
    if policy.get("context_id") != POLICY_BINDING["context_id"]:
        failures.append("policy_id")
    if policy.get("owner_directive_binding") != {
        **OWNER_DIRECTIVE_BINDING,
    }:
        failures.append("owner_directive_binding")
    if policy.get("source_memory_binding") != {
        **MEMORY_BINDING,
        "status": "draft",
        "privacy_level": "private_shared",
        "sharing_rule": "requires_all_participant_consent",
    }:
        failures.append("memory_binding")
    if policy.get("controlling_document_bindings") != list(
        CONTROLLING_DOCUMENT_BINDINGS
    ):
        failures.append("controlling_document_bindings")
    else:
        for index, binding in enumerate(CONTROLLING_DOCUMENT_BINDINGS):
            try:
                path = _project_path(binding["path"])
                if _sha256_file(path) != binding["sha256"]:
                    failures.append(f"controlling_document_digest:{index}")
            except (OSError, CollegeReflectionContextError):
                failures.append(f"controlling_document_unreadable:{index}")

    if directive.get("schema_version") != 1:
        failures.append("directive_schema")
    if directive.get("directive_id") != OWNER_DIRECTIVE_BINDING["directive_id"]:
        failures.append("directive_id")
    if directive.get("exact_person_ids") != list(EXACT_PERSON_IDS):
        failures.append("directive_people")
    adult_source = directive.get("adult_classification_source")
    current_request = directive.get("current_reflection_request")
    if not isinstance(adult_source, Mapping):
        failures.append("adult_source_missing")
    else:
        try:
            _validate_sha_text(adult_source, "adult owner authority")
        except CollegeReflectionContextError:
            failures.append("adult_source_digest")
    if not isinstance(current_request, Mapping):
        failures.append("reflection_request_missing")
    else:
        try:
            _validate_sha_text(current_request, "reflection owner authority")
        except CollegeReflectionContextError:
            failures.append("reflection_request_digest")
    scope = directive.get("authorized_scope")
    required_scope = {
        "current_source_bound_education_may_inform_present_day_reflection": True,
        "selected_person_current_private_emotion_may_ground_tone": True,
        "other_person_current_private_emotion_may_be_exposed": False,
        "historical_memory_may_be_rewritten": False,
        "current_knowledge_may_be_backdated": False,
        "locked_intimate_details_may_be_exposed": False,
        "lesson_completion_may_be_claimed": False,
        "learning_memory_may_be_created": False,
        "body_function_may_be_claimed": False,
        "consent_may_be_inferred": False,
    }
    if not isinstance(scope, Mapping) or any(
        scope.get(key) is not expected for key, expected in required_scope.items()
    ):
        failures.append("directive_scope")

    if memory.get("memory_id") != MEMORY_BINDING["memory_id"]:
        failures.append("memory_id")
    if memory.get("participants") != list(EXACT_PERSON_IDS):
        failures.append("memory_participants")
    if memory.get("status") != "draft":
        failures.append("memory_status")
    if memory.get("privacy_level") != "private_shared":
        failures.append("memory_privacy")
    if memory.get("sharing_rule") != "requires_all_participant_consent":
        failures.append("memory_sharing")

    people = policy.get("exact_people")
    if not isinstance(people, Mapping) or set(people) != set(EXACT_PERSON_IDS):
        failures.append("policy_people")
        people = {}
    before = memory.get("before_context")
    if not isinstance(before, Mapping):
        failures.append("memory_perspectives")
        before = {}
    for person in EXACT_PERSON_IDS:
        entry = people.get(person)
        authority = PERSON_CLASSIFICATION_BINDINGS.get(person)
        if not isinstance(entry, Mapping) or not isinstance(authority, Mapping):
            failures.append(f"person_binding_missing:{person}")
            continue
        expected_entry = {
            "classification_path": str(
                Path(authority["path"]).resolve().relative_to(PROJECT_ROOT.resolve())
            ).replace("\\", "/"),
            "classification_sha256": authority["sha256"],
            "classification_id": authority["classification_id"],
            "historical_perspective_summary": before.get(f"{person}_perspective"),
        }
        if dict(entry) != expected_entry:
            failures.append(f"person_binding_mismatch:{person}")
        try:
            ConfirmedAdultHealthCurriculumRuntime.load(person)
        except Exception:
            failures.append(f"adult_runtime_blocked:{person}")

    if policy.get("safe_shared_historical_summary") != list(EXPECTED_SAFE_SUMMARY):
        failures.append("safe_summary_drift")
    if policy.get("present_day_health_reflection_module_ids") != list(
        EXPECTED_HEALTH_MODULE_IDS
    ):
        failures.append("health_module_scope")

    rules = policy.get("reflection_rules")
    required_false = (
        "other_person_current_private_emotion_is_available",
        "historical_perspective_is_current_emotional_state",
        "current_education_was_known_during_the_historical_event",
        "reflection_rewrites_historical_memory",
        "reflection_creates_a_new_memory",
        "reflection_marks_a_lesson_complete",
        "reflection_proves_body_function_or_lived_sensation",
        "reflection_infers_desire_preference_consent_or_current_relationship",
        "reflection_authorizes_external_action",
        "locked_intimate_sequence_may_be_exposed",
        "exact_dialogue_dates_counts_or_unstored_details_may_be_invented",
    )
    if not isinstance(rules, Mapping) or any(
        rules.get(key) is not False for key in required_false
    ):
        failures.append("reflection_truth_boundaries")

    reconstruction = policy.get("person_owned_reconstruction_rules")
    if not isinstance(reconstruction, Mapping):
        failures.append("reconstruction_rules")
    else:
        required_true = (
            "subjective_revisit_or_reconstruction_supported",
            "kira_and_lisa_reconstructions_may_differ",
            "each_record_requires_exact_person_id",
            "each_record_requires_source_label",
            "each_record_requires_bounded_confidence",
            "reflection_and_recall_strength_deltas_are_append_only",
            "new_detail_must_remain_labeled_inferred_or_person_private_recall_until_reviewed",
            "shared_canon_change_requires_new_evidence_or_both_participants_review",
        )
        required_false_reconstruction = (
            "one_person_reconstruction_may_overwrite_other_person",
            "person_reconstruction_may_silently_change_shared_canon",
            "inferred_scene_detail_may_be_promoted_to_fact_without_evidence_or_review",
        )
        if any(reconstruction.get(key) is not True for key in required_true):
            failures.append("reconstruction_required_true")
        if any(
            reconstruction.get(key) is not False
            for key in required_false_reconstruction
        ):
            failures.append("reconstruction_required_false")
        labels = reconstruction.get("allowed_source_labels")
        if (
            not isinstance(labels, list)
            or len(labels) != len(ALLOWED_RECONSTRUCTION_SOURCE_LABELS)
            or set(labels) != ALLOWED_RECONSTRUCTION_SOURCE_LABELS
        ):
            failures.append("reconstruction_source_labels")

    disclosure = policy.get("participant_disclosure_and_reconstruction_rules")
    required_disclosure_true = (
        "participant_may_share_own_perspective_or_selected_details",
        "nonparticipant_full_reconstruction_requires_all_involved_current_scope_specific_permission",
        "nonparticipant_visual_replay_requires_all_involved_current_scope_specific_permission",
        "nonparticipant_locked_zone_access_requires_all_involved_current_scope_specific_permission",
        "incomplete_consent_keeps_locked_zones_participant_only",
        "incomplete_consent_may_pause_or_stop_at_non_intimate_boundary",
    )
    required_disclosure_false = (
        "participant_may_expose_other_participant_protected_perspective",
        "one_session_permission_becomes_permanent_permission",
        "verbal_or_text_disclosure_equals_visual_replay_permission",
    )
    if not isinstance(disclosure, Mapping):
        failures.append("participant_disclosure_rules")
    else:
        if any(disclosure.get(key) is not True for key in required_disclosure_true):
            failures.append("participant_disclosure_required_true")
        if any(disclosure.get(key) is not False for key in required_disclosure_false):
            failures.append("participant_disclosure_required_false")

    if failures:
        raise CollegeReflectionContextError(
            "college reflection validation failed: " + "; ".join(failures)
        )
    return deepcopy(policy), deepcopy(memory)


def _reflection_turn_is_relevant(user_message: str) -> bool:
    text = str(user_message or "").casefold()
    direct_phrases = (
        "college memory",
        "college memories",
        "shared college",
        "college phase",
        "what happened in college",
        "first time with lisa",
        "first time with kira",
    )
    if any(phrase in text for phrase in direct_phrases):
        return True
    has_college = re.search(r"(?<!\w)college(?!\w)", text) is not None
    has_memory_relation = any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)
        for term in ("remember", "memory", "kira", "lisa", "intimacy", "intimate")
    )
    return has_college and has_memory_relation


class KiraLisaCollegeReflectionRuntime:
    """Validated prompt context for one person's present-day reflection."""

    def __init__(self, person_id: str, policy: Mapping[str, Any], memory: Mapping[str, Any]):
        self.person_id = person_id
        self.policy = deepcopy(dict(policy))
        self.memory = deepcopy(dict(memory))
        self.policy_sha256 = POLICY_BINDING["sha256"]
        self.memory_sha256 = MEMORY_BINDING["sha256"]

    @classmethod
    def load(cls, person_id: str) -> "KiraLisaCollegeReflectionRuntime":
        person = str(person_id or "").strip().casefold()
        if person not in EXACT_PERSON_IDS:
            raise CollegeReflectionContextError(
                "college reflection is configured only for exact person Kira or Lisa"
            )
        policy, memory = _validate_policy()
        return cls(person, policy, memory)

    def context_for_turn(
        self,
        user_message: str,
        *,
        selected_person_emotion: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if not _reflection_turn_is_relevant(user_message):
            return None
        emotion = dict(selected_person_emotion or {})
        if emotion.get("model_owns_state") is not False:
            raise CollegeReflectionContextError("emotion ownership boundary is missing")
        selected = emotion.get("appraisal_selected") is True
        if selected:
            label = _text(emotion.get("emotion_label"), "emotion_label", 64)
            if not re.fullmatch(r"[\w -]{1,64}", label, flags=re.UNICODE):
                raise CollegeReflectionContextError("emotion_label is unsafe")
            raw_intensity = emotion.get("intensity")
            if isinstance(raw_intensity, bool) or not isinstance(
                raw_intensity, (int, float)
            ):
                raise CollegeReflectionContextError("emotion intensity is invalid")
            intensity = float(raw_intensity)
            if not math.isfinite(intensity) or not 0.0 <= intensity <= 1.0:
                raise CollegeReflectionContextError("emotion intensity is out of range")
            emotion_line = (
                f"Current {self.person_id.title()}-owned appraisal: {label}; "
                f"intensity={intensity:.3f}. It may ground tone but not facts."
            )
        else:
            emotion_line = (
                f"No current {self.person_id.title()}-owned appraisal is recorded; "
                "do not invent one from the historical memory."
            )

        perspective = self.policy["exact_people"][self.person_id][
            "historical_perspective_summary"
        ]
        lines = [
            "PRIVATE HASH-BOUND PRESENT-DAY COLLEGE-MEMORY REFLECTION CONTEXT:",
            f"Selected person: {self.person_id}. This context contains no current private emotion from the other participant.",
            f"Source memory: {MEMORY_BINDING['memory_id']} ({MEMORY_BINDING['sha256']}); status=draft; privacy=private_shared.",
            "Safe shared historical summary:",
            *[f"- {item}" for item in EXPECTED_SAFE_SUMMARY],
            f"Stored high-level {self.person_id.title()} historical perspective: {perspective}.",
            emotion_line,
            "Use the separately supplied source-bound adult-health curriculum only as a present-day educational lens for reflection about consent, communication, body-response/desire separation, contraception, STI health, and uncertainty.",
            "Do not claim this present-day curriculum was known then; do not diagnose the past, infer specific acts or precautions, infer consent or desire, or claim body function or lived sensation.",
            "Do not expose the locked intimate sequence, exact dialogue, dates, counts, or unstored scene details. Do not reveal the other participant's current private appraisal.",
            "Kira and Lisa may reconstruct or interpret the same memory differently. Keep every new detail labeled by source and confidence in that person's own append-only reconstruction; never merge perspectives or silently change shared canon.",
            "A participant may choose to share her own perspective or selected verbal details, but must not expose the other participant's protected body, thoughts, words, or perspective.",
            "Any full reconstruction, visual replay, or locked-zone access for a nonparticipant requires every involved participant's current scope-specific permission. Incomplete permission keeps locked zones participant-only and pauses or stops at the non-intimate boundary.",
            "Shared canon changes only through new evidence or both participants' review. This turn does not write a reflection, strengthen recall, complete a lesson, or create a learning memory.",
        ]
        return {
            "status": "PRIVATE_PRESENT_DAY_REFLECTION_CONTEXT_ASSEMBLED_NO_WRITE",
            "person_id": self.person_id,
            "prompt_context": "\n".join(lines),
            "required_health_module_ids": list(EXPECTED_HEALTH_MODULE_IDS),
            "policy_id": POLICY_BINDING["context_id"],
            "policy_file_sha256": self.policy_sha256,
            "source_memory_id": MEMORY_BINDING["memory_id"],
            "source_memory_file_sha256": self.memory_sha256,
            "owner_directive_file_sha256": OWNER_DIRECTIVE_BINDING["sha256"],
            "selected_person_emotion_used": selected,
            "other_person_current_private_emotion_included": False,
            "historical_memory_rewritten": False,
            "current_knowledge_backdated": False,
            "locked_intimate_details_exposed": False,
            "reflection_written": False,
            "recall_strength_changed": False,
            "lesson_completion_claimed": False,
            "learning_memory_created": False,
            "body_function_claimed": False,
            "consent_inferred": False,
            "external_action_authorized": False,
            "nonparticipant_full_reconstruction_authorized": False,
            "nonparticipant_visual_or_locked_access_authorized": False,
            "other_participant_protected_perspective_exposed": False,
        }


@dataclass(frozen=True)
class CollegeReflectionLease:
    person_id: str
    activation_revision: str
    nonce: str


class PersonCollegeReflectionLedger:
    """Append-only person-owned reconstructions; never the shared canon itself."""

    def __init__(
        self,
        *,
        person_id: str,
        activation_revision: str,
        lease_nonce: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        person = str(person_id or "").strip().casefold()
        if person not in EXACT_PERSON_IDS:
            raise CollegeReflectionContextError("reflection ledger person is unsupported")
        if not callable(clock):
            raise CollegeReflectionContextError("clock must be callable")
        self._lease = CollegeReflectionLease(
            person_id=person,
            activation_revision=_text(
                activation_revision, "activation_revision", 256
            ),
            nonce=_text(lease_nonce, "lease_nonce", 512),
        )
        self._clock = clock
        self._last_clock: float | None = None
        self._records: list[dict[str, Any]] = []
        self._active = True

    @property
    def lease(self) -> CollegeReflectionLease:
        return self._lease

    def _require_lease(self, lease: CollegeReflectionLease) -> None:
        if not isinstance(lease, CollegeReflectionLease) or lease != self._lease:
            raise CollegeReflectionLeaseError(
                "reflection lease does not match this person and activation"
            )
        if not self._active:
            raise CollegeReflectionLeaseError("reflection lease is revoked")

    def _timestamp(self) -> float:
        raw = self._clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise CollegeReflectionContextError("clock must return a finite number")
        value = float(raw)
        if not math.isfinite(value):
            raise CollegeReflectionContextError("clock must return a finite number")
        if self._last_clock is not None and value < self._last_clock:
            raise CollegeReflectionContextError("clock must remain monotonic")
        self._last_clock = value
        return value

    def append_person_reconstruction(
        self,
        lease: CollegeReflectionLease,
        *,
        reflection_text: str,
        source_label: str,
        confidence: float,
        recall_strength_delta: float,
    ) -> dict[str, Any]:
        """Append an explicitly selected private interpretation or recall delta.

        A delta measures subjective accessibility or vividness, not historical
        accuracy.  The record can never alter the shared memory file.
        """

        self._require_lease(lease)
        source = str(source_label or "").strip().casefold()
        if source not in ALLOWED_RECONSTRUCTION_SOURCE_LABELS:
            raise CollegeReflectionContextError("unsupported reconstruction source label")
        private_text = _text(reflection_text, "reflection_text", 4000)
        if source == "stored_shared_anchor" and private_text not in EXPECTED_SAFE_SUMMARY:
            raise CollegeReflectionContextError(
                "stored_shared_anchor text is not an exact exposed shared anchor"
            )
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise CollegeReflectionContextError("confidence must be a number")
        bounded_confidence = float(confidence)
        if not math.isfinite(bounded_confidence) or not 0.0 <= bounded_confidence <= 1.0:
            raise CollegeReflectionContextError("confidence must be between 0 and 1")
        if isinstance(recall_strength_delta, bool) or not isinstance(
            recall_strength_delta, (int, float)
        ):
            raise CollegeReflectionContextError("recall strength delta must be a number")
        bounded_delta = float(recall_strength_delta)
        if not math.isfinite(bounded_delta) or not -0.25 <= bounded_delta <= 0.25:
            raise CollegeReflectionContextError(
                "recall strength delta must be between -0.25 and 0.25"
            )

        previous_hash = (
            self._records[-1]["record_sha256"] if self._records else None
        )
        record = {
            "schema": "kira.person_owned_college_reconstruction.v1",
            "sequence": len(self._records) + 1,
            "person_id": self._lease.person_id,
            "source_memory_id": MEMORY_BINDING["memory_id"],
            "source_memory_file_sha256": MEMORY_BINDING["sha256"],
            "recorded_at_clock_seconds": self._timestamp(),
            "source_label": source,
            "confidence": bounded_confidence,
            "confidence_is_person_scoped_not_shared_fact": True,
            "recall_strength_delta": bounded_delta,
            "recall_strength_delta_is_subjective_not_accuracy": True,
            "reflection_text": private_text,
            "reflection_text_sha256": hashlib.sha256(
                private_text.encode("utf-8")
            ).hexdigest(),
            "previous_record_sha256": previous_hash,
            "shared_canon_status": "unchanged",
            "other_person_reconstruction_changed": False,
            "inferred_detail_promoted_to_fact": False,
            "current_curriculum_backdated": False,
            "lesson_completion_claimed": False,
            "body_function_claimed": False,
            "consent_inferred": False,
            "nonparticipant_replay_permission_created": False,
        }
        record["record_sha256"] = _canonical_sha256(record)
        json.dumps(record, ensure_ascii=False, sort_keys=True)
        self._records.append(record)
        return deepcopy(record)

    def snapshot(self, *, include_private: bool = False) -> dict[str, Any]:
        records = deepcopy(self._records)
        if not include_private:
            for record in records:
                record["reflection_text"] = None
        return {
            "schema": "kira.person_owned_college_reconstruction_ledger.v1",
            "person_id": self._lease.person_id,
            "source_memory_id": MEMORY_BINDING["memory_id"],
            "source_memory_file_sha256": MEMORY_BINDING["sha256"],
            "private_text_included": include_private,
            "records": records,
            "append_only": True,
            "shared_canon_mutated": False,
            "other_person_ledger_included": False,
        }

    def close(self, lease: CollegeReflectionLease) -> None:
        self._require_lease(lease)
        self._active = False


__all__ = [
    "ALLOWED_RECONSTRUCTION_SOURCE_LABELS",
    "CollegeReflectionContextError",
    "CollegeReflectionLease",
    "CollegeReflectionLeaseError",
    "CONTROLLING_DOCUMENT_BINDINGS",
    "EXACT_PERSON_IDS",
    "EXPECTED_HEALTH_MODULE_IDS",
    "KiraLisaCollegeReflectionRuntime",
    "MEMORY_BINDING",
    "OWNER_DIRECTIVE_BINDING",
    "POLICY_BINDING",
    "PersonCollegeReflectionLedger",
]
