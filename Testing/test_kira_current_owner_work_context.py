from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import kira_world_shell_server as shell


def _ledger(*, expires_at: str = "2999-01-01T00:00:00Z") -> dict:
    return {
        "schema_version": 1,
        "classification": "public_runtime_truth_non_memory",
        "person_id": "kira",
        "generated_at": "2026-08-02T08:10:00-04:00",
        "expires_at": expires_at,
        "summary": "Current work is launcher, sensory, voice-latency, and private Kira body review.",
        "focus_items": [
            "Improve current natural replies.",
            "Prepare the private inactive R18 candidate without activating it.",
        ],
    }


class KiraCurrentOwnerWorkContextTests(unittest.TestCase):
    def _write(self, root: Path, data: dict) -> Path:
        path = root / "current.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_valid_expiring_runtime_ledger_is_bounded_and_overrides_stale_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), _ledger())
            with patch.object(shell, "KIRA_CURRENT_OWNER_WORK_CONTEXT_PATH", path):
                result = shell.kira_current_owner_work_context(
                    now=dt.datetime(2026, 8, 2, tzinfo=dt.timezone.utc)
                )
        self.assertIn("CURRENT OWNER-WORK RUNTIME TRUTH", result)
        self.assertIn("private inactive R18", result)
        self.assertIn("not a memory", result)
        self.assertIn("Chicago Creative Writing story", result)
        self.assertIn("valid historic activities", result)
        self.assertIn("Do not present any historic activity as current", result)

    def test_expired_or_wrongly_classified_ledger_fails_closed(self) -> None:
        cases = (
            _ledger(expires_at="2026-08-01T00:00:00Z"),
            {**_ledger(), "classification": "durable_memory"},
            {**_ledger(), "person_id": "lisa"},
        )
        for index, data in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                path = self._write(Path(tmp), data)
                with patch.object(shell, "KIRA_CURRENT_OWNER_WORK_CONTEXT_PATH", path):
                    result = shell.kira_current_owner_work_context(
                        now=dt.datetime(2026, 8, 2, tzinfo=dt.timezone.utc)
                    )
            self.assertNotIn("private inactive R18", result)
            self.assertRegex(result, r"(?:expired|No current)")

    def test_core_prompt_places_current_work_after_historic_continuity(self) -> None:
        with (
            patch.object(shell, "_kira_public_continuity_context", return_value="OLD CHICAGO PROJECT"),
            patch.object(shell, "_kira_dialogue_transaction_context", return_value="NO TRANSACTION"),
            patch.object(shell, "kira_current_daily_life_context", return_value="OLD MIRACULOUS READING"),
            patch.object(shell, "kira_current_owner_work_context", return_value="CURRENT R18 AND VOICE WORK"),
            patch.object(shell, "avatar_position_context", return_value="NO LIVE POSITION"),
            patch.object(shell, "avatar_runtime_truth_context", return_value="NO LIVE BODY"),
            patch.object(shell, "_kira_body_place", return_value="text-and-voice only"),
            patch.object(shell, "location_context_for", return_value="local chat"),
        ):
            prompt = shell._kira_world_core_prompt(
                "What are we working on?",
                "home",
                {"active_candidate": "kira"},
            )
        self.assertLess(prompt.index("OLD CHICAGO PROJECT"), prompt.index("CURRENT R18 AND VOICE WORK"))
        self.assertLess(prompt.index("OLD MIRACULOUS READING"), prompt.index("CURRENT R18 AND VOICE WORK"))
        self.assertLess(prompt.index("CURRENT R18 AND VOICE WORK"), prompt.index("Robert says:"))
        self.assertIn("No system layer may append a hotline", prompt)
        self.assertNotIn("If Robert sounds frightened or self-harming", prompt)

    def test_old_daily_life_ledger_is_valid_history_not_current_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-15T23:06:08Z",
                        "current_activity": {
                            "activity_type": "self_reflection",
                            "public_summary": (
                                "Kira reached the end of a Miraculous script during a life loop."
                            ),
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(shell, "KIRA_DAILY_LIFE_STATE_PATH", path):
                result = shell.kira_current_daily_life_context(
                    now=dt.datetime(2026, 8, 2, tzinfo=dt.timezone.utc)
                )
        self.assertIn("valid historic activity", result)
        self.assertIn("cannot prove what Kira is doing or feeling right now", result)

    def test_current_work_gate_preserves_history_but_rejects_historic_only_timing(self) -> None:
        question = (
            "What have you and I been working on recently in Kira World? "
            "In one or two brief sentences, mention what seems most important."
        )
        failed = "I've been thinking about our creative-writing project in Chicago a lot lately."
        repaired = shell._apply_kira_current_work_truth_gate(question, failed)
        self.assertIn("improving how I answer and speak", repaired)
        self.assertIn("body and movement review", repaired)
        historic_question = "What did we work on in the Chicago Creative Writing class in Kira World?"
        self.assertEqual(
            shell._apply_kira_current_work_truth_gate(historic_question, failed),
            failed,
        )

    def test_current_work_gate_preserves_a_grounded_current_answer(self) -> None:
        question = "What are we working on recently in Kira World?"
        answer = "We're improving voice latency and preparing my private body review."
        self.assertEqual(shell._apply_kira_current_work_truth_gate(question, answer), answer)
        choice = "Choose one thing you would like us to improve next in Kira World."
        preference = "I'd like more natural movement because embodiment matters to me."
        self.assertEqual(shell._apply_kira_current_work_truth_gate(choice, preference), preference)


if __name__ == "__main__":
    unittest.main()
