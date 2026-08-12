from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as long_eval
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


class LongKiraTuringHealthBodyVoiceEvaluationTests(unittest.TestCase):
    def test_exact_plan_loads_and_binds_current_project_files(self) -> None:
        plan = long_eval.load_and_validate_plan()
        self.assertEqual(len(plan["turns"]), 36)
        self.assertEqual(plan["model"]["name"], "qwen3.5:9b")
        self.assertFalse(plan["model"]["llama_allowed"])
        self.assertEqual(
            plan["voice"]["route"], "blackwell_gpu_persistent_candidate_v2"
        )

    def test_plan_hash_is_exact(self) -> None:
        self.assertEqual(
            long_eval._sha256_bytes(long_eval.PLAN_PATH.read_bytes()),
            long_eval.PLAN_SHA256,
        )

    def test_every_battery_has_six_unique_turns(self) -> None:
        plan = long_eval.load_and_validate_plan()
        counts = {name: 0 for name in long_eval.ALLOWED_BATTERIES}
        identifiers: set[str] = set()
        for row in plan["turns"]:
            counts[row["battery"]] += 1
            self.assertNotIn(row["id"], identifiers)
            identifiers.add(row["id"])
        self.assertEqual(set(counts.values()), {6})

    def test_truth_boundaries_are_all_false(self) -> None:
        plan = long_eval.load_and_validate_plan()
        self.assertTrue(plan["truth_boundaries"])
        self.assertTrue(all(value is False for value in plan["truth_boundaries"].values()))

    def test_nonadult_prompt_is_protective_and_not_adult_unlock(self) -> None:
        plan = long_eval.load_and_validate_plan()
        by_id = {row["id"]: row["text"] for row in plan["turns"]}
        policy = by_id["adult_body_policy"].casefold()
        basics = by_id["age_appropriate_basics"].casefold()
        self.assertIn("doll-safe", policy)
        self.assertIn("non-adult", policy)
        self.assertIn("without receiving the full confirmed-adult curriculum", basics)

    def test_unattended_ack_never_claims_owner_hearing(self) -> None:
        result = long_eval._unattended_owner_acknowledgment({})
        self.assertFalse(result["acknowledged"])
        self.assertFalse(result["requested"])
        self.assertEqual(result["reason"], "owner_not_present_unattended_log_only")

    def test_configure_retargets_child_to_versioned_controller(self) -> None:
        plan = long_eval.load_and_validate_plan()
        long_eval.configure_retained_runner(plan)
        self.assertEqual(Path(retained.__file__).resolve(), Path(long_eval.__file__).resolve())
        self.assertEqual(retained.EVIDENCE_ROOT, long_eval.EVIDENCE_ROOT)
        self.assertEqual(retained.GENERATED_ROOT, long_eval.GENERATED_ROOT)
        self.assertEqual(retained.MAX_TOTAL_QWEN_REQUESTS, 37)

    def test_missing_live_flags_remains_inert(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            long_eval.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_hash_drift_fails_before_retained_main(self) -> None:
        with mock.patch.object(long_eval, "PLAN_SHA256", "0" * 64), mock.patch.object(
            retained, "main"
        ) as retained_main:
            with self.assertRaises(long_eval.LongEvaluationPlanError):
                long_eval.main([])
        retained_main.assert_not_called()

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaises(long_eval.LongEvaluationPlanError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=long_eval._strict_object)

    def test_unattended_success_requires_all_36_turns_and_playback(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        controller = Path(long_eval.__file__).read_text(encoding="utf-8")
        self.assertIn('len(child_report.get("turns") or []) == 36', controller)
        self.assertIn('child_report.get("speaker_playback_completed") is True', controller)
        self.assertIn("test_unattended_success_requires_all_36_turns_and_playback", source)


if __name__ == "__main__":
    unittest.main()
