from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Core.shared_person_media_access import SharedPersonMediaAccessError
from tools import kira_world_shell_server as shell


ROOT = Path(__file__).resolve().parents[1]


class OptionalMediaCleanCheckoutTest(unittest.TestCase):
    def make_indexless_policy(
        self, temporary_directory: str
    ) -> shell._LazyOptionalMediaAccessPolicy:
        project_root = Path(temporary_directory)
        config_dir = project_root / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "shared_person_media_access.json").write_bytes(
            (ROOT / "config/shared_person_media_access.json").read_bytes()
        )
        self.assertFalse((project_root / "Data/indexes/media_library_index.json").exists())
        return shell._LazyOptionalMediaAccessPolicy(project_root)

    def test_missing_optional_index_is_lazy_and_fails_media_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            policy = self.make_indexless_policy(temporary_directory)
            self.assertFalse(policy._attempted)

            self.assertFalse(policy.available())
            self.assertTrue(policy._attempted)
            self.assertEqual(policy.maturity_lane("kira"), "unavailable")
            self.assertIn("media_library_index.json", policy.unavailable_reason)
            with self.assertRaisesRegex(
                SharedPersonMediaAccessError,
                "optional local index is absent or invalid",
            ):
                policy.search("kira", "anything")

    def test_indexless_media_does_not_hide_downloaded_chat_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            policy = self.make_indexless_policy(temporary_directory)
            with (
                patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
                patch.object(shell, "PRE_RAM_KIRA_ONLY_MODE", False),
            ):
                candidate_ids = {item["id"] for item in shell.list_candidates()}

            self.assertFalse(policy.available())
            self.assertTrue(
                {
                    "kira",
                    "lisa",
                    "h_h_holmes_h_h_holmes_20260605_221432",
                    "kathryn_merteuil_kathryn_merteuil_20260605_213017",
                    "ladybug_marinette_expanded_smoke",
                    "peter_parker_spider_man_no_way_home_final_suit",
                }.issubset(candidate_ids)
            )


if __name__ == "__main__":
    unittest.main()
