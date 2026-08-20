from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason_code: str
    detail: str

    @classmethod
    def allow(cls, detail: str = "Request is within the configured bounds.") -> "ValidationResult":
        return cls(True, "ACCEPTED", detail)

    @classmethod
    def reject(cls, reason_code: str, detail: str) -> "ValidationResult":
        return cls(False, reason_code, detail)


class SafetyPolicy:
    """Pure-Python validator for bounded social intentions.

    This class does not import ROS, which lets the policy be unit-tested and
    reviewed independently from the transport and simulator implementation.
    """

    SUPPORTED_CATEGORIES = {"speech", "gaze", "expression", "gesture"}
    COMMON_FIELDS = {
        "intent_id",
        "source_identity",
        "confidence",
        "ttl_ms",
        "age_ms",
        "evidence_ref",
        "header_frame_id",
    }
    CATEGORY_FIELDS = {
        "speech": {"text", "voice", "max_duration_ms"},
        "gaze": {"target_frame", "target", "duration_ms"},
        "expression": {"expression", "intensity", "duration_ms"},
        "gesture": {"gesture", "intensity", "speed", "duration_ms"},
    }
    SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")

    def __init__(self, config: Mapping[str, Any]):
        self.config = dict(config)
        self.common = dict(self.config.get("common", {}))
        self._validate_configuration()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SafetyPolicy":
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        if not isinstance(raw, Mapping):
            raise ValueError("Safety policy root must be a mapping.")
        return cls(raw)

    def validate(self, category: str, payload: Mapping[str, Any]) -> ValidationResult:
        if not isinstance(category, str) or category not in self.SUPPORTED_CATEGORIES:
            return ValidationResult.reject("UNKNOWN_CATEGORY", f"Unsupported category: {category}")

        if not isinstance(payload, Mapping):
            return ValidationResult.reject("INVALID_PAYLOAD", "Payload must be a mapping.")

        if any(not isinstance(key, str) for key in payload):
            return ValidationResult.reject(
                "INVALID_FIELD_NAME", "Payload field names must be strings."
            )

        allowed_fields = self.COMMON_FIELDS | self.CATEGORY_FIELDS[category]
        if len(payload) > len(allowed_fields):
            return ValidationResult.reject(
                "UNKNOWN_FIELD", "Payload contains fields outside the bounded contract."
            )
        unknown_fields = sorted(set(payload) - allowed_fields)
        if unknown_fields:
            return ValidationResult.reject(
                "UNKNOWN_FIELD",
                f"Payload contains fields outside the bounded contract: {', '.join(unknown_fields)}.",
            )

        common_result = self._validate_common(payload)
        if not common_result.accepted:
            return common_result

        validator = getattr(self, f"_validate_{category}")
        return validator(payload)

    def _validate_configuration(self) -> None:
        allowed_root = {"common", "evidence", "speech", "gaze", "expression", "gesture"}
        unknown_root = set(self.config) - allowed_root
        if unknown_root:
            raise ValueError(f"Unknown safety-policy sections: {', '.join(sorted(unknown_root))}.")

        allowed_section_keys = {
            "common": {
                "minimum_confidence",
                "maximum_ttl_ms",
                "maximum_future_skew_ms",
                "maximum_identifier_chars",
                "maximum_evidence_ref_chars",
                "reject_stale",
                "allowed_source_identities",
                "replay_cache_entries",
            },
            "evidence": {
                "include_speech_text",
                "include_evidence_ref",
                "include_gaze_coordinates",
            },
            "speech": {"maximum_chars", "maximum_duration_ms", "allowed_voices"},
            "gaze": {"allowed_frames", "maximum_abs_coordinate_m", "maximum_duration_ms"},
            "expression": {"allowed", "maximum_intensity", "maximum_duration_ms"},
            "gesture": {"allowed", "maximum_intensity", "maximum_speed", "maximum_duration_ms"},
        }
        for section, allowed_keys in allowed_section_keys.items():
            value = self.config.get(section, {})
            if not isinstance(value, Mapping):
                raise ValueError(f"Safety-policy section '{section}' must be a mapping.")
            unknown = set(value) - allowed_keys
            if unknown:
                raise ValueError(
                    f"Unknown keys in safety-policy section '{section}': {', '.join(sorted(unknown))}."
                )

        minimum_confidence = self.common.get("minimum_confidence", 0.0)
        if not self._finite_number(minimum_confidence) or not 0.0 <= float(minimum_confidence) <= 1.0:
            raise ValueError("common.minimum_confidence must be finite and between 0 and 1.")
        self._require_positive_int("common.maximum_ttl_ms", self.common.get("maximum_ttl_ms", 30000))
        self._require_nonnegative_int(
            "common.maximum_future_skew_ms", self.common.get("maximum_future_skew_ms", 250)
        )
        self._require_positive_int(
            "common.maximum_identifier_chars", self.common.get("maximum_identifier_chars", 128)
        )
        if int(self.common.get("maximum_identifier_chars", 128)) > 128:
            raise ValueError("common.maximum_identifier_chars cannot exceed the ROS IDL bound of 128.")
        self._require_nonnegative_int(
            "common.maximum_evidence_ref_chars", self.common.get("maximum_evidence_ref_chars", 256)
        )
        if int(self.common.get("maximum_evidence_ref_chars", 256)) > 256:
            raise ValueError("common.maximum_evidence_ref_chars cannot exceed the ROS IDL bound of 256.")
        self._require_positive_int(
            "common.replay_cache_entries", self.common.get("replay_cache_entries", 2048)
        )
        if not isinstance(self.common.get("reject_stale", True), bool):
            raise ValueError("common.reject_stale must be boolean.")

        sources = self.common.get("allowed_source_identities")
        self._require_string_allowlist(
            "common.allowed_source_identities",
            sources,
            maximum_chars=int(self.common.get("maximum_identifier_chars", 128)),
        )
        for source in sources:
            if not self.SAFE_IDENTIFIER.fullmatch(source):
                raise ValueError("common.allowed_source_identities contains an invalid identifier.")

        evidence = dict(self.config.get("evidence", {}))
        for key, value in evidence.items():
            if not isinstance(value, bool):
                raise ValueError(f"evidence.{key} must be boolean.")

        speech = dict(self.config.get("speech", {}))
        self._require_positive_int("speech.maximum_chars", speech.get("maximum_chars", 500))
        if int(speech.get("maximum_chars", 500)) > 500:
            raise ValueError("speech.maximum_chars cannot exceed the ROS IDL bound of 500.")
        self._require_positive_int(
            "speech.maximum_duration_ms", speech.get("maximum_duration_ms", 20000)
        )
        self._require_string_allowlist(
            "speech.allowed_voices", speech.get("allowed_voices"), maximum_chars=64
        )

        gaze = dict(self.config.get("gaze", {}))
        self._require_string_allowlist(
            "gaze.allowed_frames", gaze.get("allowed_frames"), maximum_chars=64
        )
        coordinate = gaze.get("maximum_abs_coordinate_m", 5.0)
        if not self._finite_number(coordinate) or float(coordinate) <= 0:
            raise ValueError("gaze.maximum_abs_coordinate_m must be finite and positive.")
        self._require_positive_int(
            "gaze.maximum_duration_ms", gaze.get("maximum_duration_ms", 10000)
        )

        expression = dict(self.config.get("expression", {}))
        self._require_string_allowlist(
            "expression.allowed", expression.get("allowed"), maximum_chars=64
        )
        self._require_unit_interval(
            "expression.maximum_intensity", expression.get("maximum_intensity", 1.0)
        )
        self._require_positive_int(
            "expression.maximum_duration_ms", expression.get("maximum_duration_ms", 10000)
        )

        gesture = dict(self.config.get("gesture", {}))
        self._require_string_allowlist(
            "gesture.allowed", gesture.get("allowed"), maximum_chars=64
        )
        self._require_unit_interval(
            "gesture.maximum_intensity", gesture.get("maximum_intensity", 1.0)
        )
        self._require_unit_interval("gesture.maximum_speed", gesture.get("maximum_speed", 1.0))
        self._require_positive_int(
            "gesture.maximum_duration_ms", gesture.get("maximum_duration_ms", 10000)
        )

    @staticmethod
    def _require_positive_int(name: str, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")

    @staticmethod
    def _require_nonnegative_int(name: str, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer.")

    @classmethod
    def _require_unit_interval(cls, name: str, value: Any) -> None:
        if not cls._finite_number(value) or not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be finite and between 0 and 1.")

    @staticmethod
    def _require_string_allowlist(
        name: str, value: Any, *, maximum_chars: int
    ) -> None:
        if (
            not isinstance(value, list)
            or not value
            or len(value) > 256
            or any(not isinstance(item, str) or not item for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError(f"{name} must be a nonempty list of unique nonempty strings.")
        if any(len(item) > maximum_chars for item in value):
            raise ValueError(
                f"{name} entries cannot exceed the ROS IDL bound of {maximum_chars} characters."
            )

    def _validate_common(self, payload: Mapping[str, Any]) -> ValidationResult:
        intent_id = payload.get("intent_id")
        if not isinstance(intent_id, str) or not intent_id:
            return ValidationResult.reject("MISSING_INTENT_ID", "intent_id is required.")
        maximum_identifier_chars = int(self.common.get("maximum_identifier_chars", 128))
        if len(intent_id) > maximum_identifier_chars or not self.SAFE_IDENTIFIER.fullmatch(intent_id):
            return ValidationResult.reject(
                "INVALID_INTENT_ID",
                "intent_id must use the bounded ASCII identifier format.",
            )

        source_identity = payload.get("source_identity")
        if not isinstance(source_identity, str) or not source_identity:
            return ValidationResult.reject("MISSING_SOURCE_IDENTITY", "source_identity is required.")
        if len(source_identity) > maximum_identifier_chars or not self.SAFE_IDENTIFIER.fullmatch(source_identity):
            return ValidationResult.reject(
                "INVALID_SOURCE_IDENTITY",
                "source_identity must use the bounded ASCII identifier format.",
            )
        allowed_sources = self.common.get("allowed_source_identities", [])
        if not isinstance(allowed_sources, list) or source_identity not in allowed_sources:
            return ValidationResult.reject(
                "SOURCE_IDENTITY_NOT_ALLOWED",
                f"source_identity '{source_identity}' is not allowlisted.",
            )

        evidence_ref = payload.get("evidence_ref", "")
        if not isinstance(evidence_ref, str):
            return ValidationResult.reject("INVALID_EVIDENCE_REF", "evidence_ref must be a string.")
        maximum_evidence_ref_chars = int(self.common.get("maximum_evidence_ref_chars", 256))
        if len(evidence_ref) > maximum_evidence_ref_chars:
            return ValidationResult.reject(
                "EVIDENCE_REF_TOO_LONG",
                f"evidence_ref exceeds {maximum_evidence_ref_chars} characters.",
            )
        if self.CONTROL_CHARACTER.search(evidence_ref):
            return ValidationResult.reject(
                "INVALID_EVIDENCE_REF", "evidence_ref cannot contain control characters."
            )

        header_frame_id = payload.get("header_frame_id", "")
        if (
            not isinstance(header_frame_id, str)
            or len(header_frame_id) > 64
            or self.CONTROL_CHARACTER.search(header_frame_id)
        ):
            return ValidationResult.reject(
                "INVALID_HEADER_FRAME",
                "header_frame_id must be a string no longer than 64 characters.",
            )

        confidence = payload.get("confidence")
        if not self._finite_number(confidence) or not 0.0 <= float(confidence) <= 1.0:
            return ValidationResult.reject("INVALID_CONFIDENCE", "confidence must be between 0.0 and 1.0.")

        minimum_confidence = float(self.common.get("minimum_confidence", 0.0))
        if float(confidence) < minimum_confidence:
            return ValidationResult.reject(
                "CONFIDENCE_BELOW_POLICY",
                f"confidence is below the configured minimum of {minimum_confidence}.",
            )

        ttl_ms = payload.get("ttl_ms")
        maximum_ttl = int(self.common.get("maximum_ttl_ms", 30000))
        if not isinstance(ttl_ms, int) or isinstance(ttl_ms, bool) or ttl_ms <= 0:
            return ValidationResult.reject("INVALID_TTL", "ttl_ms must be a positive integer.")
        if ttl_ms > maximum_ttl:
            return ValidationResult.reject("TTL_EXCEEDS_POLICY", f"ttl_ms exceeds {maximum_ttl} ms.")

        if "age_ms" not in payload:
            return ValidationResult.reject("MISSING_AGE", "age_ms is required and must come from a valid timestamp.")
        age_ms = payload.get("age_ms")
        if not self._finite_number(age_ms):
            return ValidationResult.reject("INVALID_AGE", "age_ms must be a finite number.")
        maximum_future_skew = int(self.common.get("maximum_future_skew_ms", 250))
        if float(age_ms) < -maximum_future_skew:
            return ValidationResult.reject(
                "FUTURE_INTENT",
                f"intention timestamp is more than {maximum_future_skew} ms in the future.",
            )
        if bool(self.common.get("reject_stale", True)) and float(age_ms) > ttl_ms:
            return ValidationResult.reject(
                "STALE_INTENT",
                f"intention age {float(age_ms):.0f} ms exceeds ttl_ms {ttl_ms}.",
            )

        return ValidationResult.allow()

    def _validate_speech(self, payload: Mapping[str, Any]) -> ValidationResult:
        config = dict(self.config.get("speech", {}))
        raw_text = payload.get("text")
        if not isinstance(raw_text, str):
            return ValidationResult.reject("INVALID_SPEECH", "Speech text must be a string.")
        maximum_chars = int(config.get("maximum_chars", 500))
        if len(raw_text) > maximum_chars:
            return ValidationResult.reject(
                "SPEECH_TOO_LONG",
                f"Speech has {len(raw_text)} characters; policy allows {maximum_chars}.",
            )
        text = raw_text.strip()
        if not text:
            return ValidationResult.reject("EMPTY_SPEECH", "Speech text cannot be empty.")
        if text != raw_text:
            return ValidationResult.reject(
                "NONCANONICAL_SPEECH",
                "Speech text cannot have leading or trailing whitespace.",
            )

        raw_voice = payload.get("voice", "default")
        if not isinstance(raw_voice, str):
            return ValidationResult.reject("INVALID_VOICE", "voice must be a string.")
        if len(raw_voice) > 64:
            return ValidationResult.reject("INVALID_VOICE", "voice exceeds 64 characters.")
        voice = raw_voice.strip()
        if not voice or voice != raw_voice:
            return ValidationResult.reject(
                "INVALID_VOICE", "voice must be a nonempty canonical allowlisted value."
            )
        allowed_voices = set(config.get("allowed_voices", ["default"]))
        if voice not in allowed_voices:
            return ValidationResult.reject("VOICE_NOT_ALLOWED", f"Voice '{voice}' is not allowlisted.")

        return self._validate_duration(
            payload.get("max_duration_ms"),
            int(config.get("maximum_duration_ms", 20000)),
            "SPEECH_DURATION",
        )

    def _validate_gaze(self, payload: Mapping[str, Any]) -> ValidationResult:
        config = dict(self.config.get("gaze", {}))
        raw_frame = payload.get("target_frame")
        if not isinstance(raw_frame, str):
            return ValidationResult.reject("INVALID_GAZE_FRAME", "target_frame must be a string.")
        if len(raw_frame) > 64:
            return ValidationResult.reject(
                "INVALID_GAZE_FRAME", "target_frame exceeds 64 characters."
            )
        frame = raw_frame.strip()
        if not frame or frame != raw_frame:
            return ValidationResult.reject(
                "INVALID_GAZE_FRAME", "target_frame must be a nonempty canonical value."
            )
        header_frame = payload.get("header_frame_id", "")
        if header_frame and header_frame != frame:
            return ValidationResult.reject(
                "GAZE_FRAME_MISMATCH",
                "header.frame_id and target_frame must match when both are present.",
            )
        allowed_frames = set(config.get("allowed_frames", ["world"]))
        if frame not in allowed_frames:
            return ValidationResult.reject("GAZE_FRAME_NOT_ALLOWED", f"Frame '{frame}' is not allowlisted.")

        target = payload.get("target")
        if not isinstance(target, Mapping):
            return ValidationResult.reject("INVALID_GAZE_TARGET", "target must contain x, y, and z.")
        if len(target) != 3 or set(target) != {"x", "y", "z"}:
            return ValidationResult.reject(
                "INVALID_GAZE_TARGET",
                "target must contain exactly x, y, and z.",
            )

        maximum_coordinate = float(config.get("maximum_abs_coordinate_m", 5.0))
        for axis in ("x", "y", "z"):
            value = target.get(axis)
            if not self._finite_number(value):
                return ValidationResult.reject("INVALID_GAZE_TARGET", f"target.{axis} must be finite.")
            if abs(float(value)) > maximum_coordinate:
                return ValidationResult.reject(
                    "GAZE_TARGET_OUT_OF_RANGE",
                    f"target.{axis} exceeds ±{maximum_coordinate} m.",
                )

        return self._validate_duration(
            payload.get("duration_ms"),
            int(config.get("maximum_duration_ms", 10000)),
            "GAZE_DURATION",
        )

    def _validate_expression(self, payload: Mapping[str, Any]) -> ValidationResult:
        config = dict(self.config.get("expression", {}))
        raw_expression = payload.get("expression")
        if not isinstance(raw_expression, str):
            return ValidationResult.reject("INVALID_EXPRESSION", "expression must be a string.")
        if len(raw_expression) > 64:
            return ValidationResult.reject(
                "INVALID_EXPRESSION", "expression exceeds 64 characters."
            )
        expression = raw_expression.strip()
        if not expression or expression != raw_expression:
            return ValidationResult.reject(
                "INVALID_EXPRESSION", "expression must be a nonempty canonical value."
            )
        allowed = set(config.get("allowed", []))
        if expression not in allowed:
            return ValidationResult.reject(
                "EXPRESSION_NOT_ALLOWED",
                f"Expression '{expression}' is not allowlisted.",
            )

        intensity_result = self._validate_bounded_float(
            payload.get("intensity"),
            0.0,
            float(config.get("maximum_intensity", 1.0)),
            "EXPRESSION_INTENSITY",
        )
        if not intensity_result.accepted:
            return intensity_result

        return self._validate_duration(
            payload.get("duration_ms"),
            int(config.get("maximum_duration_ms", 10000)),
            "EXPRESSION_DURATION",
        )

    def _validate_gesture(self, payload: Mapping[str, Any]) -> ValidationResult:
        config = dict(self.config.get("gesture", {}))
        raw_gesture = payload.get("gesture")
        if not isinstance(raw_gesture, str):
            return ValidationResult.reject("INVALID_GESTURE", "gesture must be a string.")
        if len(raw_gesture) > 64:
            return ValidationResult.reject(
                "INVALID_GESTURE", "gesture exceeds 64 characters."
            )
        gesture = raw_gesture.strip()
        if not gesture or gesture != raw_gesture:
            return ValidationResult.reject(
                "INVALID_GESTURE", "gesture must be a nonempty canonical value."
            )
        allowed = set(config.get("allowed", []))
        if gesture not in allowed:
            return ValidationResult.reject(
                "GESTURE_NOT_ALLOWED",
                f"Gesture '{gesture}' is not allowlisted.",
            )

        intensity_result = self._validate_bounded_float(
            payload.get("intensity"),
            0.0,
            float(config.get("maximum_intensity", 1.0)),
            "GESTURE_INTENSITY",
        )
        if not intensity_result.accepted:
            return intensity_result

        speed_result = self._validate_bounded_float(
            payload.get("speed"),
            0.0,
            float(config.get("maximum_speed", 1.0)),
            "GESTURE_SPEED",
        )
        if not speed_result.accepted:
            return speed_result

        return self._validate_duration(
            payload.get("duration_ms"),
            int(config.get("maximum_duration_ms", 10000)),
            "GESTURE_DURATION",
        )

    @staticmethod
    def _finite_number(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return isfinite(float(value))
        except (OverflowError, ValueError):
            return False

    @classmethod
    def _validate_bounded_float(
        cls,
        value: Any,
        minimum: float,
        maximum: float,
        code_prefix: str,
    ) -> ValidationResult:
        if not cls._finite_number(value):
            return ValidationResult.reject(f"INVALID_{code_prefix}", f"{code_prefix.lower()} must be finite.")
        numeric = float(value)
        if not minimum <= numeric <= maximum:
            return ValidationResult.reject(
                f"{code_prefix}_OUT_OF_RANGE",
                f"{code_prefix.lower()} must be between {minimum} and {maximum}.",
            )
        return ValidationResult.allow()

    @staticmethod
    def _validate_duration(value: Any, maximum_ms: int, code_prefix: str) -> ValidationResult:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return ValidationResult.reject(f"INVALID_{code_prefix}", "Duration must be a positive integer.")
        if value > maximum_ms:
            return ValidationResult.reject(
                f"{code_prefix}_EXCEEDS_POLICY",
                f"Duration {value} ms exceeds policy maximum {maximum_ms} ms.",
            )
        return ValidationResult.allow()
