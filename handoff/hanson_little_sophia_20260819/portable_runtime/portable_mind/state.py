from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


BOUNDARY_NOTICE = (
    "Functional software appraisal variables only; not a clinical assessment, "
    "biological feeling, consciousness signal, or evidence of personhood."
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return round(max(minimum, min(maximum, value)), 4)


@dataclass(frozen=True)
class AppraisalState:
    """Transparent control variables used to vary conversational presentation."""

    valence: float = 0.0
    arousal: float = 0.25
    engagement: float = 0.5
    confidence: float = 0.5

    def as_record(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "AppraisalState":
        return cls(
            valence=_clamp(float(value.get("valence", 0.0)), -1.0, 1.0),
            arousal=_clamp(float(value.get("arousal", 0.25)), 0.0, 1.0),
            engagement=_clamp(float(value.get("engagement", 0.5)), 0.0, 1.0),
            confidence=_clamp(float(value.get("confidence", 0.5)), 0.0, 1.0),
        )

    @classmethod
    def replay(cls, records: Iterable[dict[str, Any]]) -> "AppraisalState":
        state = cls()
        for record in records:
            after = record.get("after")
            if isinstance(after, dict):
                state = cls.from_mapping(after)
        return state


POSITIVE = {"good", "great", "glad", "happy", "thanks", "thank", "love", "helpful"}
NEGATIVE = {"bad", "sad", "angry", "upset", "hurt", "wrong", "afraid", "fear"}
UNCERTAIN = {"maybe", "perhaps", "uncertain", "unsure", "guess", "might"}


def appraise_ephemeral_input(text: str, prior: AppraisalState) -> AppraisalState:
    """Update state from an input without retaining the input itself."""

    words = {token.strip(".,!?;:\"'()[]{}").lower() for token in text.split()}
    positive = len(words & POSITIVE)
    negative = len(words & NEGATIVE)
    uncertain = len(words & UNCERTAIN)
    punctuation_energy = min(3, text.count("!") + text.count("?"))
    directional_valence = (positive - negative) * 0.12
    return AppraisalState(
        valence=_clamp(prior.valence * 0.78 + directional_valence, -1.0, 1.0),
        arousal=_clamp(prior.arousal * 0.78 + punctuation_energy * 0.045, 0.0, 1.0),
        engagement=_clamp(prior.engagement * 0.85 + (0.12 if text.strip() else 0.0), 0.0, 1.0),
        confidence=_clamp(prior.confidence * 0.9 - uncertain * 0.04 + 0.025, 0.0, 1.0),
    )


def expression_for(state: AppraisalState) -> str:
    if state.valence > 0.3:
        return "gentle_smile"
    if state.valence < -0.3:
        return "concerned_attentive"
    if state.arousal > 0.65:
        return "alert_attentive"
    return "neutral_attentive"
