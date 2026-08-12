from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools import audit_kira_world_session as audit
from tools.audit_kira_world_session import build_audit, select_session


def at(minute: int) -> str:
    return f"2026-07-16T02:{minute:02d}:00+00:00"


class KiraWorldSessionAuditTests(unittest.TestCase):
    def test_latest_activation_closes_at_matching_stop(self) -> None:
        life = [
            {"at": at(1), "event": "activate", "candidate": "kira"},
            {"at": at(2), "event": "presence_heartbeat", "candidate": "kira"},
            {"at": at(3), "event": "safe_stop_active_ai", "candidate": "kira"},
        ]
        session = select_session(life, now=datetime(2026, 7, 16, 3, tzinfo=timezone.utc))
        self.assertEqual(session["status"], "closed")
        self.assertEqual(session["start"].minute, 1)
        self.assertEqual(session["end"].minute, 3)

    def test_open_session_ends_at_audit_time(self) -> None:
        now = datetime(2026, 7, 16, 2, 10, tzinfo=timezone.utc)
        session = select_session([{"at": at(1), "event": "activate", "candidate": "kira"}], now=now)
        self.assertEqual(session["status"], "open_at_audit_time")
        self.assertEqual(session["end"], now)

    def test_report_separates_speech_from_body_truth(self) -> None:
        life = [
            {"at": at(1), "event": "activate", "candidate": "kira"},
            {
                "at": "2026-07-16T02:01:58+00:00",
                "event": "avatar_runtime_snapshot",
                "candidate": "kira",
                "place": {"summary": "outside"},
            },
            {
                "at": at(2),
                "event": "kira_private_body_truth_note",
                "candidate": "kira",
                "spoken_excerpt": "I am reading on the couch.",
                "body_place": "outside",
                "posture": "none reported",
                "held_prop": "none",
            },
            {"at": at(3), "event": "deactivate", "candidate": "kira"},
        ]
        chats = [
            {"at": at(2), "speaker": "Kira", "to": "Robert", "text": "I am reading on the couch."},
        ]
        session = select_session(life)
        report = build_audit(life, chats, {}, session, scan_artifacts=False)
        comparison = report["spoken_claim_runtime_comparisons"][0]
        self.assertEqual(comparison["runtime_body_place"], "outside")
        self.assertFalse(comparison["physical_action_proven_by_speech"])
        self.assertTrue(report["truth_contract"]["spoken_words_may_be_truthful_false_playful_flirtatious_boastful_or_evasive"])
        self.assertFalse(report["truth_contract"]["private_inner_mind_content_copied_to_report"])

    def test_stale_route_target_does_not_support_starbucks_arrival_claim(self) -> None:
        life = [
            {"at": "2026-07-16T03:21:06+00:00", "event": "activate", "candidate": "kira"},
            {
                "at": "2026-07-16T03:21:06.892470+00:00",
                "event": "avatar_runtime_snapshot",
                "candidate": "kira",
                "place": {"summary": "outside in the Home World ground area", "outside": True},
            },
            {
                "at": "2026-07-16T03:28:02.422915+00:00",
                "event": "kira_private_body_truth_note",
                "candidate": "kira",
                "spoken_excerpt": "I'm actually waiting outside near the Starbucks walkway right now.",
                "body_place": "outside in Home World, moving or waiting near the route toward Starbucks public entrance walk (outside)",
                "posture": "none reported",
                "held_prop": "none",
            },
            {"at": "2026-07-16T03:31:15+00:00", "event": "deactivate", "candidate": "kira"},
        ]
        state = {
            "last_avatar_positions": {
                "kira": {
                    "updated_at": "2026-07-16T03:21:21.891341+00:00",
                    "position": {"x": -1.261, "y": 0.05, "z": 26.27},
                    "action": "walk",
                    "place": {
                        "summary": "outside in Home World, moving or waiting near the route toward Starbucks public entrance walk",
                        "outside": True,
                    },
                    "autonomousIntent": "Starbucks public entrance walk",
                }
            }
        }
        session = select_session(life)
        report = build_audit(life, [], state, session, scan_artifacts=False)
        comparison = report["spoken_claim_runtime_comparisons"][0]

        self.assertEqual(comparison["classification"], "unsupported_by_fresh_runtime_evidence")
        self.assertFalse(comparison["runtime_snapshot_fresh"])
        self.assertAlmostEqual(comparison["runtime_snapshot_age_seconds"], 400.532, places=3)
        self.assertEqual(comparison["runtime_body_place"], "unknown (latest body telemetry is stale or unavailable)")
        self.assertEqual(comparison["historical_runtime_body_place"], "outside in Home World")
        self.assertEqual(comparison["runtime_navigation_destination"], "Starbucks public entrance walk")
        self.assertTrue(comparison["navigation_destination_is_not_arrival"])
        self.assertNotIn("moving or waiting near the route", comparison["runtime_body_place"])

        latest = report["latest_body_snapshot"]
        self.assertFalse(latest["fresh_at_session_end"])
        self.assertFalse(latest["current_runtime_truth_available"])
        self.assertIsNone(latest["place"])
        self.assertEqual(latest["historical_place"], "outside in Home World")

    def test_duplicate_legacy_body_notes_are_collapsed(self) -> None:
        life = [
            {"at": at(1), "event": "activate", "candidate": "kira"},
            {"at": "2026-07-16T02:02:00.100000+00:00", "event": "kira_private_body_truth_note", "candidate": "kira", "spoken_excerpt": "I am reading.", "body_place": "outside", "posture": "none", "held_prop": "none"},
            {"at": "2026-07-16T02:02:00.200000+00:00", "event": "kira_private_body_truth_note", "candidate": "kira", "spoken_excerpt": "I am reading.", "body_place": "outside", "posture": "none", "held_prop": "none"},
            {"at": at(3), "event": "deactivate", "candidate": "kira"},
        ]
        session = select_session(life)
        report = build_audit(life, [], {}, session, scan_artifacts=False)
        self.assertEqual(report["summary"]["body_truth_comparison_count"], 1)

    def test_private_life_and_workbench_paths_are_never_disclosed(self) -> None:
        self.assertTrue(audit.is_private_artifact_path(audit.ROOT / "Data/life_sessions/example.json"))
        self.assertTrue(audit.is_private_artifact_path(audit.ROOT / "Data/core_ai_workbenches/kira/draft.md"))
        self.assertFalse(audit.is_private_artifact_path(audit.ROOT / "Data/messages/kira_to_robert/message.json"))


if __name__ == "__main__":
    unittest.main()
