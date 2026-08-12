from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "TemporaryAI"
    / "candidates"
    / "h_h_holmes_h_h_holmes_20260605_221432"
    / "qwen3_tts_original_voice_design_evaluation_request_v2.json"
)


class HHHolmesOriginalVoiceDesignRequestV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request = json.loads(REQUEST.read_text(encoding="utf-8"))

    def test_request_is_queued_and_cannot_execute(self) -> None:
        self.assertEqual(
            self.request["status"],
            "QUEUED_BLOCKED_BY_REJECTED_VOICE_FORGE_ACCEPTANCE",
        )
        self.assertFalse(self.request["execution_allowed"])

    def test_historical_voice_is_original_and_not_claimed_authentic(self) -> None:
        target = self.request["target"]
        self.assertEqual(
            target["voice_kind"],
            "original_synthetic_historically_plausible_reconstruction",
        )
        self.assertFalse(target["authentic_voice_claim_allowed"])
        self.assertFalse(target["voice_clone_requested"])

    def test_sources_bind_region_education_and_period_without_biometrics(self) -> None:
        factors = {item["factor"]: item for item in self.request["source_ranked_factors"]}
        self.assertEqual(set(factors), {"birthplace_and_early_region", "education", "later_public_context"})
        self.assertTrue(all(item["source"].startswith("https://") for item in factors.values()))
        forbidden = " ".join(self.request["design_brief"]["forbidden_inferences"]).lower()
        self.assertIn("photographs", forbidden)
        self.assertIn("dramatizations", forbidden)
        self.assertIn("historically exact accent", forbidden)

    def test_no_generic_sapi_or_absolute_watermark_claim(self) -> None:
        engine = self.request["planned_engine"]
        self.assertFalse(engine["generic_or_sapi_substitution_allowed"])
        self.assertFalse(engine["absolute_watermark_free_claim_allowed"])
        self.assertFalse(engine["network_during_acceptance_allowed"])

    def test_followup_voice_is_separate_and_never_auto_assigned(self) -> None:
        followup = self.request["followup_comparison"]
        self.assertIn("generated expert", followup["target"])
        self.assertFalse(followup["automatic_assignment_allowed"])


if __name__ == "__main__":
    unittest.main()
