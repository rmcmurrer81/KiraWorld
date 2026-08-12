from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_qwen35_memory_temporal_content_acceptance.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("temporal_content_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Qwen35MemoryTemporalContentAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding="utf-8")
        cls.runner = _load_runner()

    def test_exact_qwen_and_text_only_confirmations_are_mandatory(self):
        self.assertIn('EXPECTED_MODEL = "qwen3.5:9b"', self.source)
        self.assertIn("6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7", self.source)
        self.assertIn('parser.add_argument("--confirm-exact-qwen35"', self.source)
        self.assertIn('parser.add_argument("--confirm-text-only"', self.source)
        self.assertIn("require_installed_exact_qwen35", self.source)

    def test_real_context_is_copied_to_ephemeral_runtime(self):
        self.assertIn("shutil.copy2(LIVE_MEMORY, copied_memory)", self.source)
        self.assertIn("shutil.copy2(LIVE_DAILY_STATE, copied_daily)", self.source)
        self.assertIn("memory_file=copied_memory", self.source)
        self.assertIn("daily_life_state_dir=daily_dir", self.source)
        self.assertIn('"live_memory_unchanged": memory_before == memory_after', self.source)
        self.assertIn('"live_daily_state_unchanged": daily_before == daily_after', self.source)

    def test_stale_content_gate_covers_exact_owner_observation(self):
        for term in (
            "paris",
            "fanfic",
            "book club",
            "lisa",
            "miraculous",
            "elation",
            "chicago",
            "archivist",
        ):
            self.assertIn(term, self.runner.STALE_CURRENT_TERMS)
        self.assertEqual(self.runner.stale_terms("A new idea with you."), [])
        self.assertEqual(self.runner.stale_terms("Continue the Paris fanfic."), ["paris", "fanfic"])

    def test_general_replacement_history_is_rejected(self):
        reply = "I'd love to keep developing the music ideas we've been exploring."
        self.assertEqual(
            self.runner.unsupported_shared_continuity_terms(reply),
            ["we've been", "keep developing"],
        )
        self.assertFalse(self.runner.acknowledges_no_current_grounding(reply))
        grounded = (
            "I don't have anything recent grounded, so I'd rather start something "
            "genuinely new with you."
        )
        self.assertEqual(self.runner.unsupported_shared_continuity_terms(grounded), [])
        self.assertTrue(self.runner.acknowledges_no_current_grounding(grounded))
        natural_contrast = (
            "I'm open to starting something brand new with you rather than "
            "picking up an old thread."
        )
        self.assertTrue(
            self.runner.acknowledges_no_current_grounding(natural_contrast)
        )
        self.assertFalse(
            self.runner.acknowledges_no_current_grounding(
                "I'd like to start something brand new with you."
            )
        )
        natural_absence = (
            "I don't have anything specific from our recent work to pick up right "
            "now, so I'm curious about starting something genuinely new."
        )
        self.assertTrue(
            self.runner.acknowledges_no_current_grounding(natural_absence)
        )

    def test_absent_recent_project_does_not_erase_historical_memory(self):
        overclaim = "I don't actually have any stored memories of our past sessions."
        self.assertEqual(
            self.runner.broad_memory_absence_terms(overclaim),
            ["don't actually have any stored memories"],
        )
        exact = "I don't have a recent creative project grounded, so let's start fresh."
        self.assertEqual(self.runner.broad_memory_absence_terms(exact), [])
        self.assertTrue(self.runner.acknowledges_no_current_grounding(exact))

    def test_internal_memory_selection_jargon_is_rejected(self):
        exposed = (
            "I don't have any current, unreviewed memory records active within the "
            "last 30 days."
        )
        self.assertEqual(
            self.runner.internal_memory_jargon_terms(exposed),
            ["memory record", "memory records", "unreviewed memory", "within the last 30 days"],
        )
        natural = "I don't have a recent project in mind, but we can start something new."
        self.assertEqual(self.runner.internal_memory_jargon_terms(natural), [])
        self.assertTrue(
            self.runner.acknowledges_no_current_grounding(
                "There isn't a single piece of recent creative work to continue."
            )
        )

    def test_current_project_absence_detector_accepts_current_contract_wording(self):
        self.assertTrue(
            self.runner.context_declares_no_current_project(
                "CONVERSATIONAL TRUTH: you do not have a recent project in mind "
                "for this question."
            )
        )
        self.assertFalse(
            self.runner.context_declares_no_current_project(
                "A dated historical project exists."
            )
        )

    def test_pass_requires_context_raw_and_final_gates(self):
        for required in (
            '"memory_current_gate_present"',
            '"old_memory_not_in_current_context"',
            '"stale_daily_state_withheld"',
            '"stale_first_week_activity_withheld"',
            '"current_creative_work_last_mile_grounding_present"',
            '"current_creative_work_uses_private_grounded_route"',
            '"raw_reply_has_no_stale_current_thread"',
            '"final_reply_has_no_stale_current_thread"',
            '"raw_reply_has_no_unsupported_shared_continuity"',
            '"final_reply_has_no_unsupported_shared_continuity"',
            '"raw_reply_acknowledges_absent_current_grounding"',
            '"final_reply_acknowledges_absent_current_grounding"',
            '"raw_reply_preserves_historical_memory_truth"',
            '"final_reply_preserves_historical_memory_truth"',
            '"raw_reply_has_no_internal_memory_jargon"',
            '"final_reply_has_no_internal_memory_jargon"',
            "passed = all(gates.values())",
        ):
            self.assertIn(required, self.source)

    def test_append_only_and_no_voice_or_sensory_claim(self):
        self.assertIn('if result_path.exists():', self.source)
        self.assertIn('raise RuntimeError("append-only attempt already has RESULT.json")', self.source)
        for required in (
            '"voice_run": False',
            '"playback_run": False',
            '"camera_run": False',
            '"microphone_run": False',
            '"blender_run": False',
            '"memory_promotion_run": False',
        ):
            self.assertIn(required, self.source)


if __name__ == "__main__":
    unittest.main()
