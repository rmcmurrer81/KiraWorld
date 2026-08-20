from __future__ import annotations

import sys
import copy
import math
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.policy import SafetyPolicy  # noqa: E402


POLICY_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "kira_hanson_bridge"
    / "config"
    / "safety_policy.yaml"
)


def base_payload() -> dict:
    return {
        "intent_id": "test-intent",
        "source_identity": "kira",
        "confidence": 0.9,
        "ttl_ms": 5000,
        "age_ms": 10,
        "evidence_ref": "test",
    }


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = SafetyPolicy.from_yaml(POLICY_PATH)

    def test_allows_wave(self) -> None:
        payload = {
            **base_payload(),
            "gesture": "wave",
            "intensity": 0.5,
            "speed": 0.4,
            "duration_ms": 2000,
        }
        self.assertTrue(self.policy.validate("gesture", payload).accepted)

    def test_rejects_unknown_gesture(self) -> None:
        payload = {
            **base_payload(),
            "gesture": "unbounded_spin",
            "intensity": 0.5,
            "speed": 0.4,
            "duration_ms": 2000,
        }
        result = self.policy.validate("gesture", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "GESTURE_NOT_ALLOWED")

    def test_rejects_stale_intent(self) -> None:
        payload = {
            **base_payload(),
            "age_ms": 6000,
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "STALE_INTENT")

    def test_rejects_out_of_range_gaze(self) -> None:
        payload = {
            **base_payload(),
            "target_frame": "world",
            "target": {"x": 100.0, "y": 0.0, "z": 1.0},
            "duration_ms": 2000,
        }
        result = self.policy.validate("gaze", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "GAZE_TARGET_OUT_OF_RANGE")

    def test_rejects_oversized_speech(self) -> None:
        payload = {
            **base_payload(),
            "text": "x" * 501,
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "SPEECH_TOO_LONG")

    def test_rejects_missing_timestamp_age(self) -> None:
        payload = {
            **base_payload(),
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        del payload["age_ms"]
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "MISSING_AGE")

    def test_rejects_excessively_future_timestamp(self) -> None:
        payload = {
            **base_payload(),
            "age_ms": -251,
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "FUTURE_INTENT")

    def test_allows_small_clock_skew_at_policy_boundary(self) -> None:
        payload = {
            **base_payload(),
            "age_ms": -250,
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        self.assertTrue(self.policy.validate("speech", payload).accepted)

    def test_rejects_unallowlisted_source_identity(self) -> None:
        payload = {
            **base_payload(),
            "source_identity": "arbitrary-publisher",
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "SOURCE_IDENTITY_NOT_ALLOWED")

    def test_rejects_invalid_intent_identifier(self) -> None:
        payload = {
            **base_payload(),
            "intent_id": "contains a space",
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_INTENT_ID")

    def test_rejects_unknown_top_level_field(self) -> None:
        payload = {
            **base_payload(),
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
            "joint_trajectory": [1, 2, 3],
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "UNKNOWN_FIELD")

    def test_rejects_extra_gaze_axis(self) -> None:
        payload = {
            **base_payload(),
            "target_frame": "world",
            "target": {"x": 0.5, "y": 0.0, "z": 1.0, "roll": 1.0},
            "duration_ms": 1000,
        }
        result = self.policy.validate("gaze", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_GAZE_TARGET")

    def test_rejects_gaze_header_frame_mismatch(self) -> None:
        payload = {
            **base_payload(),
            "header_frame_id": "camera",
            "target_frame": "world",
            "target": {"x": 0.5, "y": 0.0, "z": 1.0},
            "duration_ms": 1000,
        }
        result = self.policy.validate("gaze", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "GAZE_FRAME_MISMATCH")

    def test_rejects_nonfinite_values(self) -> None:
        payload = {
            **base_payload(),
            "expression": "attentive",
            "intensity": math.nan,
            "duration_ms": 1000,
        }
        result = self.policy.validate("expression", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_EXPRESSION_INTENSITY")

    def test_rejects_numeric_strings(self) -> None:
        payload = {
            **base_payload(),
            "confidence": "0.9",
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 1000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_CONFIDENCE")

    def test_rejects_oversized_evidence_reference(self) -> None:
        payload = {
            **base_payload(),
            "evidence_ref": "x" * 257,
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 2000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "EVIDENCE_REF_TOO_LONG")

    def test_rejects_malformed_policy_configuration(self) -> None:
        config = copy.deepcopy(self.policy.config)
        config["gesture"]["maximum_speed"] = float("inf")
        with self.assertRaises(ValueError):
            SafetyPolicy(config)

    def test_rejects_unknown_policy_key(self) -> None:
        config = copy.deepcopy(self.policy.config)
        config["common"]["allow_everything_typo"] = True
        with self.assertRaises(ValueError):
            SafetyPolicy(config)

    def test_rejects_allowlist_entries_above_idl_bound(self) -> None:
        config = copy.deepcopy(self.policy.config)
        config["gesture"]["allowed"] = ["x" * 65]
        with self.assertRaises(ValueError):
            SafetyPolicy(config)

    def test_rejects_unhashable_category_without_raising(self) -> None:
        result = self.policy.validate([], base_payload())
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "UNKNOWN_CATEGORY")

    def test_rejects_non_string_payload_key_without_raising(self) -> None:
        payload = {**base_payload(), 7: "unexpected", "text": "hello", "voice": "default"}
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_FIELD_NAME")

    def test_rejects_huge_integer_without_raising(self) -> None:
        payload = {
            **base_payload(),
            "confidence": 10**10000,
            "text": "hello",
            "voice": "default",
            "max_duration_ms": 1000,
        }
        result = self.policy.validate("speech", payload)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason_code, "INVALID_CONFIDENCE")

    def test_rejects_whitespace_padding_before_normalization(self) -> None:
        cases = [
            (
                "speech",
                {
                    **base_payload(),
                    "text": " " * 1000 + "hello",
                    "voice": "default",
                    "max_duration_ms": 1000,
                },
            ),
            (
                "speech",
                {
                    **base_payload(),
                    "text": "hello",
                    "voice": " " * 1000 + "default",
                    "max_duration_ms": 1000,
                },
            ),
            (
                "gesture",
                {
                    **base_payload(),
                    "gesture": " " * 1000 + "wave",
                    "intensity": 0.5,
                    "speed": 0.5,
                    "duration_ms": 1000,
                },
            ),
        ]
        for category, payload in cases:
            with self.subTest(category=category):
                self.assertFalse(self.policy.validate(category, payload).accepted)


if __name__ == "__main__":
    unittest.main()
