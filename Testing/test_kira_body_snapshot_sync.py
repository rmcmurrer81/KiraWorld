from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import kira_world_shell_server as shell


class KiraBodySnapshotSyncTests(unittest.TestCase):
    def test_avatar_position_echoes_exact_request_and_persists_core_state(self) -> None:
        state = dict(shell.DEFAULT_STATE)
        state["active_candidate"] = "kira"
        state["last_avatar_positions"] = {}
        replies: list[tuple[int, dict]] = []
        handler = object.__new__(shell.Handler)
        handler.path = "/api/avatar-position"
        handler._body = lambda: {
            "candidate": "kira",
            "location": "home",
            "world": "home_world",
            "position": {"x": 1.25, "y": 0.05, "z": -3.5},
            "action": "idle",
            "supportState": {"id": "outside_ground", "supported": True},
            "snapshotRequestId": "body-test-17",
            "snapshotSequence": 17,
            "capturedAtMonotonicSeconds": 42.75,
            "telemetryErrors": {},
        }
        handler._json = lambda status, payload: replies.append((status, payload))

        with (
            patch.object(shell, "load_state", return_value=state),
            patch.object(shell, "save_state") as save_state,
            patch.object(shell, "maybe_log_avatar_runtime_snapshot") as log_snapshot,
        ):
            handler.do_POST()

        self.assertEqual(
            replies,
            [(200, {"ok": True, "saved": True, "request_id": "body-test-17"})],
        )
        saved = state["last_avatar_positions"]["kira"]
        self.assertEqual(saved["snapshotRequestId"], "body-test-17")
        self.assertEqual(saved["snapshotSequence"], 17)
        self.assertEqual(saved["position"], {"x": 1.25, "y": 0.05, "z": -3.5})
        self.assertEqual(saved["telemetryErrors"], {})
        save_state.assert_called_once_with(state)
        log_snapshot.assert_called_once()

    def test_invalid_or_inactive_snapshot_never_counts_as_saved(self) -> None:
        for active, candidate, expected_reason in (
            ("", "kira", "not_active_candidate"),
            ("kira", "elsa", "not_active_candidate"),
            ("kira", "kira", "invalid_position"),
        ):
            with self.subTest(active=active, candidate=candidate):
                state = dict(shell.DEFAULT_STATE)
                state["active_candidate"] = active
                replies: list[tuple[int, dict]] = []
                handler = object.__new__(shell.Handler)
                handler.path = "/api/avatar-position"
                handler._body = lambda candidate=candidate: {
                    "candidate": candidate,
                    "snapshotRequestId": "must-not-ack",
                    "position": {"x": None, "y": 0, "z": 0},
                }
                handler._json = lambda status, payload: replies.append((status, payload))
                with (
                    patch.object(shell, "load_state", return_value=state),
                    patch.object(shell, "save_state"),
                    patch.object(shell, "append_jsonl"),
                ):
                    handler.do_POST()
                self.assertEqual(replies[0][0], 200)
                self.assertFalse(replies[0][1]["saved"])
                self.assertEqual(replies[0][1]["reason"], expected_reason)
                self.assertEqual(replies[0][1]["request_id"], "must-not-ack")

    def test_shell_waits_for_correlated_saved_acknowledgement(self) -> None:
        page = shell.html_shell().decode("utf-8")
        self.assertIn("acknowledgedAvatarSnapshotRequests", page)
        self.assertIn("requestAvatarSnapshotNow(true)", page)
        self.assertIn("if (!result.saved) return", page)
        self.assertIn("result.request_id || snapshot.snapshotRequestId", page)
        self.assertNotIn("lastAvatarSnapshotAckAt >= requestedAt", page)


if __name__ == "__main__":
    unittest.main()
