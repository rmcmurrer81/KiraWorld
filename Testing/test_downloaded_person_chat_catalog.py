from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from Core.downloaded_person_chat_catalog import (
    AUTHORITATIVE_USER_AVATAR_BOUNDARY,
    FIXED_PERSON_ROUTES,
    SYNTHETIC_ROBERT_SEPARATION,
    TEMPORARY_AI_CUSTOM_VOICE_BINDINGS,
    bind_review_and_voice_route,
    discover_downloaded_person_routes,
    exact_candidate_voice_binding,
)
from tools.downloaded_person_chat_launcher import build_launch_spec, choose_route


class DownloadedPersonChatCatalogTests(unittest.TestCase):
    def test_catalog_lists_fixed_people_and_every_checked_in_candidate(self) -> None:
        routes = discover_downloaded_person_routes(ROOT)
        ids = {route.person_id for route in routes}
        candidate_ids = {
            path.name
            for path in (ROOT / "TemporaryAI" / "candidates").iterdir()
            if path.is_dir() and (path / "temporary_ai_profile.json").is_file()
        }

        self.assertTrue({"kira", "synthetic_robert", "lisa"}.issubset(ids))
        self.assertTrue(candidate_ids.issubset(ids))
        self.assertEqual(len(routes), len(candidate_ids) + 3)

    def test_synthetic_robert_is_only_a_portable_persistent_person(self) -> None:
        routes = discover_downloaded_person_routes(ROOT)
        robert = choose_route(routes, "synthetic_robert")

        self.assertEqual(robert.identity_class, "portable_persistent_person")
        self.assertEqual(robert.chat_mode, "portable_persistent_runtime")
        self.assertNotIn("TemporaryAI/candidates", robert.launcher)
        self.assertIn("Synthetic Robert Text and Voice Chat.cmd", robert.launcher)

    def test_old_body_takeover_concept_is_explicitly_abandoned(self) -> None:
        boundary = SYNTHETIC_ROBERT_SEPARATION
        self.assertEqual(boundary["old_13th_floor_body_takeover_concept"], "abandoned")
        self.assertEqual(
            boundary["user_login_presence"],
            "separate_user_avatar_with_distinct_body_session_and_identity",
        )
        for prohibited in (
            "body_takeover",
            "identity_merge",
            "memory_transfer",
            "voice_substitution",
            "body_sharing",
        ):
            self.assertIn(prohibited, boundary["prohibited"])
        self.assertEqual(
            boundary["authoritative_boundary_doc"],
            AUTHORITATIVE_USER_AVATAR_BOUNDARY,
        )
        doc = (ROOT / AUTHORITATIVE_USER_AVATAR_BOUNDARY).read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "originally explored a `13th Floor` takeover. That option is rejected",
            doc,
        )
        self.assertIn("Human Robert uses a separate user-controlled body", doc)
        self.assertIn("autonomous Robert keeps a separate autonomous body", doc)

    def test_custom_voice_routes_are_exact_candidate_id_bindings(self) -> None:
        self.assertEqual(len(TEMPORARY_AI_CUSTOM_VOICE_BINDINGS), 4)
        for candidate_id, expected in TEMPORARY_AI_CUSTOM_VOICE_BINDINGS.items():
            with self.subTest(candidate_id=candidate_id):
                binding = exact_candidate_voice_binding(candidate_id)
                self.assertIsNotNone(binding)
                self.assertEqual(binding["candidate_id"], candidate_id)
                self.assertEqual(binding["expected_voice_id"], expected["expected_voice_id"])
                profile_path = ROOT / binding["voice_profile_path"]
                self.assertTrue(profile_path.is_file())
                self.assertEqual(
                    hashlib.sha256(profile_path.read_bytes()).hexdigest(),
                    binding["expected_profile_sha256"],
                )
                self.assertFalse(binding["authentic_voice_claim_allowed"])
                if binding["profile_bounded_custom_voice_allowed"]:
                    reference = ROOT / binding["approved_reference_path"]
                    self.assertEqual(
                        hashlib.sha256(reference.read_bytes()).hexdigest(),
                        binding["approved_reference_sha256"],
                    )
                    self.assertIn("exact reviewed reference pack", binding["review_label"])
                    self.assertIn("synthesized new speech", binding["review_label"])
        self.assertIsNone(exact_candidate_voice_binding("same_display_name_is_not_an_id"))

    def test_profile_bounded_route_disables_custom_voice_but_allows_labelled_os_voice(self) -> None:
        candidate_id = "h_h_holmes_h_h_holmes_20260605_221432"
        candidate = {
            "candidate_id": candidate_id,
            "profile": {"candidate_id": candidate_id, "display_name": "H. H. Holmes"},
        }
        bound = bind_review_and_voice_route(
            candidate,
            review_mode="profile_bounded_draft",
            full_source_reason="needs_clarification",
        )

        decision = bound["text_route_decision"]
        self.assertTrue(decision["allowed"])
        self.assertTrue(decision["profile_bounded_label_required"])
        self.assertFalse(decision["custom_voice_output_allowed"])
        self.assertTrue(decision["generic_os_voice_output_allowed"])
        self.assertFalse(decision["error_or_exception_text_may_reach_tts"])
        self.assertEqual(bound["voice_route_binding"]["candidate_id"], candidate_id)

    def test_only_three_exact_bounded_candidates_authorize_custom_reconstruction(self) -> None:
        custom_ids = {
            candidate_id
            for candidate_id, row in TEMPORARY_AI_CUSTOM_VOICE_BINDINGS.items()
            if row["profile_bounded_custom_voice_allowed"] is True
        }
        self.assertEqual(
            custom_ids,
            {
                "kathryn_merteuil_kathryn_merteuil_20260605_213017",
                "ladybug_marinette_expanded_smoke",
                "peter_parker_spider_man_no_way_home_final_suit",
            },
        )
        for candidate_id in custom_ids:
            bound = bind_review_and_voice_route(
                {
                    "candidate_id": candidate_id,
                    "profile": {"candidate_id": candidate_id},
                },
                review_mode="profile_bounded_draft",
            )
            self.assertTrue(bound["text_route_decision"]["custom_voice_output_allowed"])
            self.assertTrue(bound["text_route_decision"]["profile_bounded_label_required"])

    def test_launcher_specs_are_checkout_relative_and_exact_candidate_is_passed(self) -> None:
        routes = discover_downloaded_person_routes(ROOT)
        temp_route = choose_route(
            routes, "h_h_holmes_h_h_holmes_20260605_221432"
        )
        command, cwd, env = build_launch_spec(
            temp_route,
            project_root=ROOT,
            environment={"COMSPEC": "cmd.exe"},
        )

        self.assertEqual(cwd, ROOT.resolve())
        self.assertEqual(command[:4], ["cmd.exe", "/d", "/c", "call"])
        self.assertEqual(
            env["TEMP_AI_INITIAL_CANDIDATE_ID"], temp_route.candidate_id
        )
        self.assertTrue(Path(command[-1]).is_file())
        launcher_text = (ROOT / "Start_Downloaded_People_Chat.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn('cd /d "%~dp0"', launcher_text)
        self.assertNotIn("C:\\Users\\robmc\\Kira", launcher_text)

    def test_fixed_launchers_exist(self) -> None:
        for route in FIXED_PERSON_ROUTES:
            with self.subTest(person_id=route.person_id):
                self.assertTrue((ROOT / route.launcher).is_file())


if __name__ == "__main__":
    unittest.main()
