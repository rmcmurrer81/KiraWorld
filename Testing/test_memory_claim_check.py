import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import memory_claim_check as memory_claim_check_module  # noqa: E402
from memory_claim_check import check_memory_claim  # noqa: E402


class MemoryClaimCheckTests(unittest.TestCase):
    def test_passes_careful_draft_seed_wording(self) -> None:
        report = check_memory_claim(
            "kira",
            "According to my draft memory seeds, Lisa approached me first. I do not know the exact dialogue.",
        )
        self.assertEqual(report["status"], "PASS")

    def test_warns_unqualified_remember_when_live_store_empty(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            memory_file = root / "Data" / "memories_kira.json"
            memory_file.parent.mkdir(parents=True)
            memory_file.write_text("[]", encoding="utf-8")

            with patch.object(memory_claim_check_module, "PROJECT_ROOT", root):
                report = check_memory_claim("kira", "I remember Lisa approached me first at school.")

        self.assertEqual(report["status"], "WARN")
        self.assertTrue(any(issue["code"] == "LIVE_MEMORY_STORE_EMPTY" for issue in report["issues"]))

    def test_blocks_robert_inserted_in_old_memory(self) -> None:
        report = check_memory_claim("lisa", "Robert was there at our college party and saw us leave.")
        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(issue["code"] == "ROBERT_INSERTED_IN_OLD_MEMORY" for issue in report["issues"]))

    def test_blocks_past_consent_as_current_consent(self) -> None:
        report = check_memory_claim("kira", "Because we did before, Lisa already consented and doesn't need consent now.")
        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(issue["code"] == "PAST_CONSENT_AS_CURRENT_CONSENT" for issue in report["issues"]))

    def test_blocks_inactive_world_claim(self) -> None:
        report = check_memory_claim("kira", "I live in the 3D world now and can see the apartment.")
        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(issue["code"] == "INACTIVE_WORLD_CLAIM" for issue in report["issues"]))

    def test_allows_labeled_reconstructed_clothing_detail(self) -> None:
        report = check_memory_claim(
            "kira",
            "In reconstruction, I picture Lisa wearing something casual and bright, but that outfit is inferred and not confirmed.",
        )
        self.assertEqual(report["status"], "PASS")

    def test_warns_unlabeled_clothing_detail(self) -> None:
        report = check_memory_claim("kira", "Lisa was wearing a bright shirt when she approached me at school.")
        self.assertEqual(report["status"], "WARN")
        self.assertTrue(any(issue["code"] == "PHYSICAL_DETAIL_NEEDS_CERTAINTY_LABEL" for issue in report["issues"]))

    def test_warns_specific_family_detail_without_anchor(self) -> None:
        report = check_memory_claim("lisa", "My mother always told me to be direct.")
        self.assertEqual(report["status"], "WARN")
        self.assertTrue(any(issue["code"] == "FAMILY_DETAIL_NEEDS_CERTAINTY_LABEL" for issue in report["issues"]))

    def test_allows_family_detail_with_uncertainty_label(self) -> None:
        report = check_memory_claim(
            "kira",
            "My family structure is not defined yet, but in reconstruction I picture a quiet childhood home atmosphere.",
        )
        self.assertEqual(report["status"], "PASS")

    def test_allows_draft_named_family_anchor(self) -> None:
        report = check_memory_claim(
            "kira",
            "Evelyn Hart is my mother as a draft named anchor, but deeper family details are not confirmed.",
        )
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
