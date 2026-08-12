import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

import humanity_context  # noqa: E402
from humanity_context import build_humanity_context  # noqa: E402


class HumanityContextTests(unittest.TestCase):
    def test_context_mentions_style_memory_and_taste_policy(self) -> None:
        context = build_humanity_context("kira")

        self.assertIn("PRIVATE HUMANITY CONTEXT", context)
        self.assertNotIn("16GB", context)
        self.assertIn("style_goal", context)
        self.assertIn("secrecy_goal", context)
        self.assertIn("allowed_secrecy_and_lies", context)
        self.assertIn("protected_truth_zones", context)
        self.assertIn("truth_evaluation_records", context)
        self.assertIn("lie_classification", context)
        self.assertIn("withholding, refusal, silence", context)
        self.assertIn("private_belief_access", context)
        self.assertIn("comparison unavailable", context)
        self.assertIn("consciousness_claim_limit", context)
        self.assertNotIn("private belief content=", context)
        self.assertIn("fuzzy_memory_policy", context)
        self.assertIn("fuzzy_memory_rotation", context)
        self.assertIn("college_first_approach", context)
        self.assertIn("tastes can change", context)
        self.assertIn("reading_taste_policy", context)

    def test_missing_truth_privacy_policy_fails_closed(self) -> None:
        with patch.object(
            humanity_context,
            "TRUTH_PRIVACY_EVALUATION_POLICY_FILE",
            Path("Z:/definitely_missing_truth_privacy_policy.json"),
        ):
            context = build_humanity_context("kira")

        self.assertIn("truth_privacy_policy_unavailable", context)
        self.assertIn("do not inspect or infer private belief", context)
        self.assertIn("do not label a deliberate lie", context)
        self.assertNotIn("truth_evaluation_records", context)


if __name__ == "__main__":
    unittest.main()
