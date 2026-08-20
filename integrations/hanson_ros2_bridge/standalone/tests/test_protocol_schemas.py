from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from standalone.schema_tools import schema_validator, strict_format_checker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = PROJECT_ROOT / "protocol_v0_2"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def validator(name: str) -> Draft202012Validator:
    return schema_validator(load_schema(name))


def sample_intention(category: str = "speech") -> dict:
    payloads = {
        "speech": {"text": "hello", "voice": "default", "max_duration_ms": 1000},
        "gaze": {
            "target_frame": "world",
            "target": {"x": 0.2, "y": 0.0, "z": 1.0},
            "duration_ms": 1000,
        },
        "expression": {"expression": "attentive", "intensity": 0.5, "duration_ms": 1000},
        "gesture": {"gesture": "wave", "intensity": 0.5, "speed": 0.5, "duration_ms": 1000},
    }
    return {
        "protocol_version": "0.2-proposal",
        "session_id": "session-1",
        "body_id": "little-sophia-simulator",
        "source_identity": "kira",
        "intent_id": f"intent-{category}",
        "sequence": 1,
        "category": category,
        "issued_at_utc": "2026-08-18T12:00:01Z",
        "ttl_ms": 5000,
        "payload": payloads[category],
        "decision_scope": "physical_execution_only",
    }


class ProtocolSchemaTests(unittest.TestCase):
    def test_required_date_time_checker_is_installed(self) -> None:
        checker = strict_format_checker()
        self.assertTrue(checker.conforms("2026-08-18T12:00:00Z", "date-time"))
        self.assertFalse(checker.conforms("not-a-date", "date-time"))

    def test_all_schemas_are_valid_draft_2020_12(self) -> None:
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json")):
            with self.subTest(path=path.name):
                Draft202012Validator.check_schema(load_schema(path.name))

    def test_session_and_intention_samples_validate(self) -> None:
        session = {
            "protocol_version": "0.2-proposal",
            "session_id": "session-1",
            "body_id": "little-sophia-simulator",
            "source_identity": "kira",
            "capabilities": ["speech", "gaze", "expression", "gesture"],
            "opened_at_utc": "2026-08-18T12:00:00Z",
            "expires_at_utc": "2026-08-18T12:10:00Z",
            "session_ttl_ms": 600000,
            "heartbeat_timeout_ms": 3000,
            "decision_scope": "physical_execution_only",
        }
        validator("session.schema.json").validate(session)
        for category in ("speech", "gaze", "expression", "gesture"):
            with self.subTest(category=category):
                validator("intention-envelope.schema.json").validate(
                    sample_intention(category)
                )

    def test_unknown_and_low_level_fields_fail_closed(self) -> None:
        intention = sample_intention("gesture")
        intention["joint_trajectory"] = [1, 2, 3]
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

        intention = sample_intention("gesture")
        intention["payload"]["joint_trajectory"] = [1, 2, 3]
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

        intention = sample_intention("speech")
        intention["payload"]["blob"] = "x" * 1_000_000
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

    def test_category_and_payload_shape_cannot_be_mixed(self) -> None:
        intention = sample_intention("speech")
        intention["payload"] = sample_intention("gesture")["payload"]
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

    def test_formats_and_control_free_identifiers_are_enforced(self) -> None:
        intention = sample_intention("speech")
        intention["issued_at_utc"] = "not-a-date"
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

        intention = sample_intention("speech")
        intention["session_id"] = "session\nforged"
        with self.assertRaises(ValidationError):
            validator("intention-envelope.schema.json").validate(intention)

    def test_execution_terminal_flag_matches_lifecycle_state(self) -> None:
        event = {
            "protocol_version": "0.2-proposal",
            "session_id": "session-1",
            "body_id": "little-sophia-simulator",
            "intent_id": "intent-1",
            "intent_sequence": 1,
            "status_sequence": 1,
            "category": "speech",
            "state": "COMPLETED",
            "terminal": True,
            "reason_code": "PHYSICAL_EXECUTION_COMPLETED",
            "executor": "deterministic-mock",
            "recorded_at_utc": "2026-08-18T12:00:02Z",
            "decision_scope": "physical_execution_only",
        }
        event_validator = validator("execution-event.schema.json")
        event_validator.validate(event)
        event["terminal"] = False
        with self.assertRaises(ValidationError):
            event_validator.validate(event)
        event["state"] = "STARTED"
        event["terminal"] = True
        with self.assertRaises(ValidationError):
            event_validator.validate(event)


if __name__ == "__main__":
    unittest.main()
