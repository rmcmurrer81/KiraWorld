from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from Core.portable_os_voice import OSVoiceRoute
from tools.temporary_ai_live_chat_gui import (
    TemporaryAILiveChatGUI,
    candidate_voice_output_decision,
    initial_candidate_index,
    load_candidate_for_review_chat,
)


FULL_SOURCE_CANDIDATES = {
    "emily_carter_ai_and_computer_programming_expert_20260605_220651",
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
    "sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
}

PROFILE_BOUNDED_CANDIDATES = {
    "h_h_holmes_h_h_holmes_20260605_221432",
    "jessica_hale_robotics_engineer_20260611_041314",
    "kathryn_merteuil_kathryn_merteuil_20260605_213017",
    "ladybug_marinette_expanded_smoke",
    "peter_parker_spider_man_no_way_home_final_suit",
    "ryan_hale_quantum_mechanics_expert_20260608_200749",
}

CUSTOM_BOUNDED_VOICE_CANDIDATES = {
    "kathryn_merteuil_kathryn_merteuil_20260605_213017",
    "ladybug_marinette_expanded_smoke",
    "peter_parker_spider_man_no_way_home_final_suit",
}


class DownloadedPersonChatGUIRoutesTests(unittest.TestCase):
    def test_every_checked_in_candidate_has_an_honest_review_text_route(self) -> None:
        actual_ids = {
            path.name
            for path in (ROOT / "TemporaryAI" / "candidates").iterdir()
            if path.is_dir() and (path / "temporary_ai_profile.json").is_file()
        }
        expected_ids = FULL_SOURCE_CANDIDATES | PROFILE_BOUNDED_CANDIDATES
        self.assertTrue(expected_ids.issubset(actual_ids))
        for candidate_id in sorted(actual_ids):
            with self.subTest(candidate_id=candidate_id):
                candidate = load_candidate_for_review_chat(candidate_id)
                expected = None
                if candidate_id in FULL_SOURCE_CANDIDATES:
                    expected = "full_source_grounded_review"
                elif candidate_id in PROFILE_BOUNDED_CANDIDATES:
                    expected = "profile_bounded_draft"
                if expected is not None:
                    self.assertEqual(candidate["review_mode"], expected)
                self.assertIn(
                    candidate["review_mode"],
                    {"full_source_grounded_review", "profile_bounded_draft"},
                )
                decision = candidate["text_route_decision"]
                self.assertTrue(decision["allowed"])
                self.assertFalse(decision["error_or_exception_text_may_reach_tts"])
                if candidate["review_mode"] == "profile_bounded_draft":
                    self.assertTrue(decision["profile_bounded_label_required"])
                    self.assertEqual(
                        decision["custom_voice_output_allowed"],
                        candidate_id in CUSTOM_BOUNDED_VOICE_CANDIDATES,
                    )

    def test_custom_pack_is_first_then_mocked_os_fallback_without_playback(self) -> None:
        route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Installed Test Voice",
            "",
            "test_route",
        )
        all_ids = sorted(
            path.name
            for path in (ROOT / "TemporaryAI" / "candidates").iterdir()
            if path.is_dir() and (path / "temporary_ai_profile.json").is_file()
        )
        with patch(
            "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
            return_value=route,
        ) as discover:
            for candidate_id in all_ids:
                with self.subTest(candidate_id=candidate_id):
                    candidate = load_candidate_for_review_chat(candidate_id)
                    decision = candidate_voice_output_decision(candidate, ROOT)
                    self.assertTrue(decision["allowed"], decision.get("reason"))
                    expected_route = (
                        "custom_voice_pack"
                        if candidate_id in CUSTOM_BOUNDED_VOICE_CANDIDATES
                        else "os_voice_fallback"
                    )
                    self.assertEqual(decision["route_kind"], expected_route)
                    if expected_route == "custom_voice_pack":
                        self.assertFalse(decision["authentic_voice_claim"])
                        self.assertIn("exact reviewed reference pack", decision["profile_label"])
                        self.assertIn("synthesized new speech", decision["profile_label"])
        self.assertEqual(discover.call_count, len(all_ids))

    def test_initial_candidate_selector_accepts_exact_id_only(self) -> None:
        paths = [
            ROOT / "TemporaryAI" / "candidates" / candidate_id
            for candidate_id in sorted(PROFILE_BOUNDED_CANDIDATES)
        ]
        requested = "ladybug_marinette_expanded_smoke"
        selected = initial_candidate_index(paths, requested)

        self.assertIsNotNone(selected)
        self.assertEqual(paths[selected].name, requested)
        self.assertIsNone(initial_candidate_index(paths, "Ladybug"))
        self.assertIsNone(initial_candidate_index(paths, "../ladybug_marinette_expanded_smoke"))

    def test_unified_launcher_environment_selects_and_opens_exact_candidate(self) -> None:
        requested = "peter_parker_spider_man_no_way_home_final_suit"
        gui = object.__new__(TemporaryAILiveChatGUI)
        gui.candidate_paths = [
            ROOT / "TemporaryAI" / "candidates" / "h_h_holmes_h_h_holmes_20260605_221432",
            ROOT / "TemporaryAI" / "candidates" / requested,
        ]
        gui.candidate_list = Mock()
        gui.status = Mock()
        gui.root = Mock()
        gui.update_candidate_preview = Mock()
        gui.start_selected_chat = Mock()

        with patch.dict(os.environ, {"TEMP_AI_INITIAL_CANDIDATE_ID": requested}):
            selected = gui.apply_initial_candidate_selection_from_environment()

        self.assertTrue(selected)
        gui.candidate_list.selection_clear.assert_called_once_with(0, "end")
        gui.candidate_list.selection_set.assert_called_once_with(1)
        gui.candidate_list.see.assert_called_once_with(1)
        gui.update_candidate_preview.assert_called_once_with()
        gui.root.after.assert_called_once_with(0, gui.start_selected_chat)


if __name__ == "__main__":
    unittest.main()
