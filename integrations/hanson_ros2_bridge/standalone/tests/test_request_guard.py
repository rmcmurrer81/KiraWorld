from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.request_guard import RequestGuard  # noqa: E402


class RequestGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = RequestGuard(maximum_entries=2)
        self.payload = {"intent_id": "one", "value": 1}

    def test_new_request_dispatches(self) -> None:
        result = self.guard.assess("gesture", self.payload)
        self.assertTrue(result.should_dispatch)
        self.assertEqual(result.reason_code, "NEW_REQUEST")

    def test_identical_duplicate_is_suppressed(self) -> None:
        self.guard.assess("gesture", self.payload)
        result = self.guard.assess("gesture", dict(self.payload))
        self.assertFalse(result.should_dispatch)
        self.assertEqual(result.reason_code, "DUPLICATE_SUPPRESSED")

    def test_receipt_local_age_change_does_not_turn_replay_into_conflict(self) -> None:
        first = {**self.payload, "age_ms": 10}
        replayed_later = {**self.payload, "age_ms": 110}
        self.guard.assess("gesture", first)
        result = self.guard.assess("gesture", replayed_later)
        self.assertFalse(result.should_dispatch)
        self.assertEqual(result.reason_code, "DUPLICATE_SUPPRESSED")

    def test_conflicting_reuse_is_rejected(self) -> None:
        self.guard.assess("gesture", self.payload)
        result = self.guard.assess("gesture", {"intent_id": "one", "value": 2})
        self.assertFalse(result.should_dispatch)
        self.assertEqual(result.reason_code, "INTENT_ID_REUSE_CONFLICT")

    def test_category_is_part_of_digest(self) -> None:
        self.guard.assess("gesture", self.payload)
        result = self.guard.assess("speech", self.payload)
        self.assertEqual(result.reason_code, "INTENT_ID_REUSE_CONFLICT")

    def test_cache_is_bounded(self) -> None:
        self.guard.assess("gesture", {"intent_id": "one", "value": 1})
        self.guard.assess("gesture", {"intent_id": "two", "value": 2})
        self.guard.assess("gesture", {"intent_id": "three", "value": 3})
        result = self.guard.assess("gesture", {"intent_id": "one", "value": 1})
        self.assertTrue(result.should_dispatch)

    def test_invalid_cache_bound_refuses_startup(self) -> None:
        with self.assertRaises(ValueError):
            RequestGuard(maximum_entries=0)


if __name__ == "__main__":
    unittest.main()
