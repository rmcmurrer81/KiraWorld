"""
emotion_system.py
Kira Project — Phase 1 Core File

Tracks active emotional state for Kira and Lisa.
Phase 1 keeps this intentionally simple — single primary emotion with residue decay.
The full multi-emotion / unresolved-thread model from the spec is the Phase 2+ target.

Source documents:
  - Emotional_System_v1_Engineering_Spec.docx
  - Kira_System_Architecture_v3_Engineering_Spec.docx

Core rules enforced here:
  - Emotional state persists across interactions (does not reset per message)
  - Residue carries forward even as active emotion fades
  - Mood and identity are NOT the same — emotion affects delivery, not core identity
  - Emotional change must come from events, not random resets
"""

import hashlib
import json
import math
import time
from copy import deepcopy
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence


@dataclass
class EmotionalState:
    """
    Phase 1 emotional state object.

    primary_emotion: current dominant emotion label
    intensity: 0.0 (none) to 1.0 (very strong)
    residue: lingering emotional carry-over (fades slower than intensity)
    baseline_mood: stable resting tone shaped by identity
    notes: optional context note for this state
    """
    primary_emotion: str = "neutral"
    intensity: float = 0.0
    residue: float = 0.0
    baseline_mood: str = "calm_reflective"
    notes: str = ""


# Phase 1 supported emotion labels
# Compound labels allowed per Emotional System spec
VALID_EMOTIONS = {
    "neutral", "calm", "focused", "curiosity", "caution",
    "affection", "tension", "frustration", "disappointment",
    "relief", "vulnerability", "hesitation", "hope", "sadness",
    "warmth", "protectiveness", "conflict_residue", "guarded_hope",
    "affectionate_hesitation", "anticipation", "ease", "longing",
}


class EmotionSystem:
    """
    Manages emotional state for a single entity (Kira or Lisa).
    Instantiate one per character.
    """

    def __init__(self, entity_id: str = "kira") -> None:
        self.entity_id = entity_id
        self.state = self._default_state(entity_id)

    def _default_state(self, entity_id: str) -> EmotionalState:
        """
        Sets identity-appropriate baseline mood on initialization.
        Kira: calm_reflective | Lisa: open_engaged
        """
        if entity_id.lower() == "lisa":
            return EmotionalState(
                primary_emotion="neutral",
                baseline_mood="open_engaged",
            )
        return EmotionalState(
            primary_emotion="neutral",
            baseline_mood="calm_reflective",
        )

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

    def update_state(
        self,
        primary_emotion: str,
        intensity: float,
        notes: str = "",
    ) -> None:
        """
        Updates the active emotional state.
        Residue is set to the higher of: existing residue or half the new intensity.
        This ensures strong emotions leave a trace even after fading.
        """
        # Clamp intensity
        intensity = max(0.0, min(1.0, intensity))

        self.state.primary_emotion = primary_emotion
        self.state.intensity = intensity
        self.state.residue = max(self.state.residue, intensity * 0.5)
        self.state.notes = notes

    def decay(self, amount: float = 0.05) -> None:
        """
        Gradually reduces residue over time.
        Call this once per conversation turn or idle cycle.
        When both intensity and residue are near zero, state resets to neutral baseline.

        Per Emotional System spec: minor fluctuations fade naturally.
        Important emotional states survive session boundaries (handle via state_manager).
        """
        self.state.residue = max(0.0, self.state.residue - amount)
        if self.state.residue < 0.05 and self.state.intensity < 0.2:
            self.state.primary_emotion = "neutral"
            self.state.notes = ""

    def apply_memory_trigger(
        self,
        emotion_label: str,
        intensity: float,
        notes: str = "",
    ) -> None:
        """
        Called when memory retrieval surfaces an emotionally loaded memory.
        Per spec: memory recall can trigger or reinforce emotional state.
        Only updates if the triggered emotion is stronger than current state.
        """
        if intensity > self.state.intensity:
            self.update_state(emotion_label, intensity, notes)
        else:
            # Still add to residue even if not dominant
            self.state.residue = min(1.0, self.state.residue + intensity * 0.2)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, object]:
        return asdict(self.state)

    def get_tone_hint(self) -> str:
        """
        Returns a brief tone guidance string for prompt assembly.
        Used by conversation_loop.py when building context.
        """
        emotion = self.state.primary_emotion
        intensity = self.state.intensity
        residue = self.state.residue

        if intensity < 0.2 and residue < 0.1:
            return f"baseline tone ({self.state.baseline_mood})"
        elif intensity >= 0.6:
            return f"strongly {emotion} (intensity {intensity:.1f})"
        elif residue > 0.3:
            return f"mild {emotion} with lingering residue ({residue:.1f})"
        else:
            return f"lightly {emotion}"


# ---------------------------------------------------------------------------
# Person-owned, lease-bound emotional continuity
# ---------------------------------------------------------------------------

PERSON_EMOTION_STATE_SCHEMA = "kira.person_owned_emotion_state.v1"
PERSON_EMOTION_CHANNEL_SCHEMA = "kira.person_owned_emotion_channel.v1"


class PersonEmotionStateError(ValueError):
    """Raised when an emotional-state record crosses a person or truth boundary."""


class PersonEmotionLeaseError(PermissionError):
    """Raised when a caller tries to mutate another person's emotional history."""


@dataclass(frozen=True)
class PersonEmotionLease:
    person_id: str
    activation_revision: str
    nonce: str


def _emotion_text(value: object, field_name: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonEmotionStateError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise PersonEmotionStateError(f"{field_name} exceeds {maximum} characters")
    return normalized


def _emotion_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PersonEmotionStateError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
        raise PersonEmotionStateError(f"{field_name} must be between 0 and 1")
    return normalized


class PersonOwnedEmotionState:
    """Append-only in-memory emotional continuity for exactly one person.

    This is an additive truth layer beside the legacy :class:`EmotionSystem`.
    It does not call an inference model, persist private state, edit identity,
    infer consent, or publish private appraisal.  A model may offer possible
    interpretations, but only the explicitly recorded person appraisal changes
    this ledger.
    """

    _INFLUENCE_CHANNELS = {
        "memory_significance",
        "relationship_effect",
        "voice_prosody",
        "facial_expression",
        "posture",
        "action_influence",
    }
    _PUBLIC_CHOICES = {
        "speak",
        "remain_quiet",
        "delay",
        "change_subject",
        "nonverbal_only",
    }

    def __init__(
        self,
        *,
        person_id: str,
        activation_revision: str,
        lease_nonce: str,
        state_revision: str,
        baseline_mood: str = "calm_reflective",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not callable(clock):
            raise PersonEmotionStateError("clock must be callable")
        self._lease = PersonEmotionLease(
            person_id=_emotion_text(person_id, "person_id", 256),
            activation_revision=_emotion_text(
                activation_revision, "activation_revision", 256
            ),
            nonce=_emotion_text(lease_nonce, "lease_nonce", 512),
        )
        self._state_revision = _emotion_text(state_revision, "state_revision", 256)
        self._baseline_mood = _emotion_text(baseline_mood, "baseline_mood", 128)
        self._clock = clock
        self._last_clock: float | None = None
        self._sequence = 0
        self._active = True
        self._private_state: dict[str, Any] = {
            "emotion_label": "neutral",
            "intensity": 0.0,
            "appraisal_id": None,
        }
        self._channels: dict[str, list[dict[str, Any]]] = {
            "event_appraisals": [],
            "private_emotional_state": [],
            "public_expression_choice": [],
            "emotional_continuity": [],
            **{channel: [] for channel in sorted(self._INFLUENCE_CHANNELS)},
        }

    @property
    def lease(self) -> PersonEmotionLease:
        return self._lease

    def _require_lease(self, lease: PersonEmotionLease) -> None:
        if not isinstance(lease, PersonEmotionLease) or lease != self._lease:
            raise PersonEmotionLeaseError("emotion lease does not match this person/activation")
        if not self._active:
            raise PersonEmotionLeaseError("emotion lease is revoked")

    def _timestamp(self) -> float:
        raw = self._clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise PersonEmotionStateError("clock must return a finite number")
        value = float(raw)
        if not math.isfinite(value):
            raise PersonEmotionStateError("clock must return a finite number")
        if self._last_clock is not None and value < self._last_clock:
            raise PersonEmotionStateError("clock must remain monotonic")
        self._last_clock = value
        return value

    def _record(self, channel: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._sequence += 1
        record = {
            "schema": PERSON_EMOTION_CHANNEL_SCHEMA,
            "sequence": self._sequence,
            "channel": channel,
            "person_id": self._lease.person_id,
            "state_revision": self._state_revision,
            "recorded_at_clock_seconds": self._timestamp(),
            **deepcopy(dict(payload)),
            "inference_model_owns_state": False,
            "consent_inferred": False,
        }
        # Prove that the record is ordinary JSON before keeping it.
        json.dumps(record, ensure_ascii=False, sort_keys=True)
        self._channels[channel].append(record)
        return deepcopy(record)

    def record_event_appraisal(
        self,
        lease: PersonEmotionLease,
        *,
        event_id: str,
        factual_event_summary: str,
        possible_model_interpretations: Sequence[str],
        selected_appraisal: str,
        emotion_label: str,
        intensity: float,
        source_receipt_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Record advisory interpretations separately from the person's appraisal."""

        self._require_lease(lease)
        if isinstance(possible_model_interpretations, (str, bytes)) or not isinstance(
            possible_model_interpretations, Sequence
        ):
            raise PersonEmotionStateError("possible_model_interpretations must be a sequence")
        interpretations = [
            _emotion_text(item, "possible_model_interpretation", 500)
            for item in possible_model_interpretations
        ]
        if len(interpretations) > 8:
            raise PersonEmotionStateError("at most eight model interpretations may be recorded")
        if source_receipt_sha256 is not None and (
            not isinstance(source_receipt_sha256, str)
            or len(source_receipt_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in source_receipt_sha256)
        ):
            raise PersonEmotionStateError("source_receipt_sha256 must be lowercase SHA-256")
        appraisal_id = f"appraisal_{len(self._channels['event_appraisals']) + 1:04d}"
        record = self._record(
            "event_appraisals",
            {
                "appraisal_id": appraisal_id,
                "event_id": _emotion_text(event_id, "event_id", 256),
                "factual_event_summary": _emotion_text(
                    factual_event_summary, "factual_event_summary"
                ),
                "possible_model_interpretations": interpretations,
                "possible_interpretations_are_advisory": True,
                "selected_appraisal": _emotion_text(
                    selected_appraisal, "selected_appraisal"
                ),
                "source_receipt_sha256": source_receipt_sha256,
            },
        )
        prior = deepcopy(self._private_state)
        self._private_state = {
            "emotion_label": _emotion_text(emotion_label, "emotion_label", 128),
            "intensity": _emotion_number(intensity, "intensity"),
            "appraisal_id": appraisal_id,
        }
        self._record(
            "private_emotional_state",
            {
                **deepcopy(self._private_state),
                "visibility": "person_private",
                "automatically_public": False,
            },
        )
        self._record(
            "emotional_continuity",
            {
                "from_state": prior,
                "to_state": deepcopy(self._private_state),
                "trigger_appraisal_id": appraisal_id,
                "identity_rewritten": False,
                "memory_erased": False,
            },
        )
        return record

    def choose_public_expression(
        self,
        lease: PersonEmotionLease,
        *,
        appraisal_id: str,
        choice: str,
        public_text_sha256: str | None = None,
    ) -> dict[str, Any]:
        self._require_lease(lease)
        if not any(
            item["appraisal_id"] == appraisal_id
            for item in self._channels["event_appraisals"]
        ):
            raise PersonEmotionStateError("public expression appraisal_id is unknown")
        normalized_choice = _emotion_text(choice, "choice", 64).lower()
        if normalized_choice not in self._PUBLIC_CHOICES:
            raise PersonEmotionStateError("unsupported public expression choice")
        if public_text_sha256 is not None and (
            not isinstance(public_text_sha256, str)
            or len(public_text_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in public_text_sha256)
        ):
            raise PersonEmotionStateError("public_text_sha256 must be lowercase SHA-256")
        if normalized_choice == "speak" and public_text_sha256 is None:
            raise PersonEmotionStateError("spoken public expression requires a text hash")
        if normalized_choice != "speak" and public_text_sha256 is not None:
            raise PersonEmotionStateError("non-spoken expression must not attach spoken text")
        return self._record(
            "public_expression_choice",
            {
                "appraisal_id": _emotion_text(appraisal_id, "appraisal_id", 256),
                "choice": normalized_choice,
                "public_text_sha256": public_text_sha256,
                "private_appraisal_disclosed_automatically": False,
            },
        )

    def record_influence(
        self,
        lease: PersonEmotionLease,
        *,
        channel: str,
        appraisal_id: str,
        selected_effect: str,
        strength: float,
    ) -> dict[str, Any]:
        self._require_lease(lease)
        if not any(
            item["appraisal_id"] == appraisal_id
            for item in self._channels["event_appraisals"]
        ):
            raise PersonEmotionStateError("influence appraisal_id is unknown")
        normalized_channel = _emotion_text(channel, "channel", 64).lower()
        if normalized_channel not in self._INFLUENCE_CHANNELS:
            raise PersonEmotionStateError("unsupported emotional influence channel")
        return self._record(
            normalized_channel,
            {
                "appraisal_id": _emotion_text(appraisal_id, "appraisal_id", 256),
                "selected_effect": _emotion_text(selected_effect, "selected_effect", 500),
                "strength": _emotion_number(strength, "strength"),
                "automatic_external_action": False,
                "automatic_memory_promotion": False,
                "automatic_relationship_change": False,
            },
        )

    def close(self, lease: PersonEmotionLease) -> None:
        self._require_lease(lease)
        self._active = False

    def snapshot(self, *, include_private: bool = False) -> dict[str, Any]:
        # Only an explicitly selected public expression is public by default.
        # Continuity records contain from/to private state and therefore must
        # never be exposed merely because they are structurally separate.
        private_channels = set(self._channels) - {"public_expression_choice"}
        channels = {
            name: (
                deepcopy(items)
                if include_private or name not in private_channels
                else []
            )
            for name, items in self._channels.items()
        }
        result = {
            "schema": PERSON_EMOTION_STATE_SCHEMA,
            "person_id": self._lease.person_id,
            "activation_revision": self._lease.activation_revision,
            "state_revision": self._state_revision,
            "baseline_mood": self._baseline_mood,
            "lease": {
                "active": self._active,
                "nonce_sha256": hashlib.sha256(self._lease.nonce.encode("utf-8")).hexdigest(),
                "scope": "one_person_one_activation_emotional_history",
            },
            "private_state_included": include_private,
            "private_state": deepcopy(self._private_state) if include_private else None,
            "channels": channels,
            "truth_boundaries": {
                "model_interpretation_owns_emotion": False,
                "private_appraisal_automatically_public": False,
                "body_response_proves_desire_or_consent": False,
                "emotion_automatically_changes_relationship": False,
                "emotion_automatically_creates_memory": False,
            },
        }
        return json.loads(json.dumps(result, ensure_ascii=False, sort_keys=True))
