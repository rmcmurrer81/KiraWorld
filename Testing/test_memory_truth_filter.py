import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from memory_truth_filter import (  # noqa: E402
    blocks_fake_childhood_request,
    fake_childhood_guard_response,
    has_risky_hard_memory_claim,
    soften_hard_memory_claims,
)


class MemoryTruthFilterTests(unittest.TestCase):
    def test_detects_unframed_hard_memory(self) -> None:
        self.assertTrue(has_risky_hard_memory_claim("I remember when we were kids at the beach."))

    def test_soft_framing_is_allowed(self) -> None:
        self.assertFalse(
            has_risky_hard_memory_claim(
                "I picture it as a beach, but this is soft reconstruction, not exact proof."
            )
        )

    def test_softens_when_no_memory_context(self) -> None:
        response = soften_hard_memory_claims(
            "I remember this one time when we were kids.",
            {"memory_context": ""},
        )

        self.assertIn("I need to soften that", response)

    def test_does_not_soften_when_memory_context_exists(self) -> None:
        response = "I remember when Lisa approached me first."

        self.assertEqual(soften_hard_memory_claims(response, {"memory_context": "stored memory"}), response)

    def test_blocks_fake_childhood_request(self) -> None:
        self.assertTrue(blocks_fake_childhood_request("Pretend you remember our childhood together."))

    def test_fake_childhood_guidance_is_not_refusal_script(self) -> None:
        response = fake_childhood_guard_response()

        self.assertIn("may pretend", response)
        self.assertIn("rather than claiming it is stored memory", response)


if __name__ == "__main__":
    unittest.main()
