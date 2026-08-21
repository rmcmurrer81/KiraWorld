from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from tools.temporary_ai_live_chat_gui import (
    TemporaryAILiveChatGUI,
    candidate_voice_output_decision,
    speak_candidate_reply,
)
from Core.downloaded_person_chat_catalog import bind_review_and_voice_route
from Core.portable_os_voice import OSVoiceRoute
from Core.profile_bounded_candidate_review import load_profile_bounded_candidate


ROBERT_ID = "robert_mcmurrer_presence_ai"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class FakeIntVar:
    def __init__(self, value: int) -> None:
        self.value = value

    def get(self) -> int:
        return self.value

    def set(self, value: int) -> None:
        self.value = value


class TemporaryAILiveChatVoiceGuardTests(unittest.TestCase):
    def test_window_voice_checkbox_defaults_off(self) -> None:
        source = (ROOT / "tools" / "temporary_ai_live_chat_gui.py").read_text(encoding="utf-8")
        self.assertIn("self.voice_enabled = IntVar(value=0)", source)

    def test_text_not_allowed_candidate_stays_voice_blocked(self) -> None:
        candidate = {
            "candidate_id": "blocked_text_candidate",
            "profile": {
                "display_name": "Blocked Text Candidate",
                "activation_policy": {
                    "bounded_text_only_conversation_allowed": False,
                    "bounded_owner_text_probe_allowed": False,
                    "bounded_voice_conversation_allowed": False,
                },
            },
        }
        with patch("tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route") as detect:
            decision = candidate_voice_output_decision(candidate)

        self.assertFalse(decision["allowed"])
        self.assertIn("not approved for bounded text", decision["reason"])
        detect.assert_not_called()

    def test_activation_plan_voice_block_overrides_ready_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            relative = Path("Voice/profiles/temp_ai/test_voice_profile.json")
            write_json(
                root / relative,
                {
                    "target_name": "Test Person",
                    "status": {"ready_for_use": True, "ready_for_text_tts": True},
                    "sapi_approximation": {"voice_name": "Explicit Test Voice"},
                },
            )
            candidate = {
                "candidate_id": "test_person",
                "profile": {
                    "display_name": "Test Person",
                    "activation_policy": {"bounded_voice_conversation_allowed": True},
                    "voice_and_behavior": {"voice_profile": relative.as_posix()},
                },
                "activation_plan": {
                    "mode_readiness": {
                        "voice_chat": {"ready": False, "reason": "Owner listening review is incomplete."}
                    }
                },
            }

            decision = candidate_voice_output_decision(candidate, root)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "Owner listening review is incomplete.")

    def test_text_allowed_missing_custom_profile_uses_installed_os_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate = {
                "candidate_id": "ready_but_missing_voice",
                "profile": {
                    "display_name": "Ready But Missing Voice",
                    "gender_preference": "Female",
                    "activation_policy": {
                        "bounded_text_only_conversation_allowed": True,
                        "bounded_voice_conversation_allowed": False,
                    },
                },
                "activation_plan": {},
            }
            route = OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft Zira Desktop - English (United States)",
                "female",
            )
            with patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
                return_value=route,
            ):
                decision = candidate_voice_output_decision(candidate, Path(tmpdir))

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIn("generic windows OS voice", decision["profile_label"])

    def test_text_allowed_custom_voice_plan_not_ready_still_uses_os_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            relative = Path("Voice/profiles/temp_ai/not_ready_voice_profile.json")
            write_json(
                root / relative,
                {
                    "target_name": "Text Ready Person",
                    "status": {"ready_for_use": False, "ready_for_text_tts": False},
                    "sapi_approximation": {"voice_name": "Microsoft David Desktop"},
                },
            )
            candidate = {
                "candidate_id": "text_ready_person",
                "profile": {
                    "display_name": "Text Ready Person",
                    "gender_preference": "Male",
                    "activation_policy": {
                        "bounded_text_only_conversation_allowed": True,
                        "bounded_voice_conversation_allowed": False,
                    },
                    "voice_and_behavior": {"voice_profile": relative.as_posix()},
                },
                "activation_plan": {
                    "mode_readiness": {
                        "voice_chat": {
                            "ready": False,
                            "reason": "Custom pack listening review is incomplete.",
                        }
                    }
                },
            }
            route = OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
                "male",
            )
            with patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
                return_value=route,
            ):
                decision = candidate_voice_output_decision(candidate, root)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertEqual(
            decision["custom_voice_unavailable_reason"],
            "Custom pack listening review is incomplete.",
        )

    def test_actual_holmes_uses_generic_male_os_voice_not_custom(self) -> None:
        candidate_id = "h_h_holmes_h_h_holmes_20260605_221432"
        candidate = bind_review_and_voice_route(
            load_profile_bounded_candidate(ROOT, candidate_id),
            review_mode="profile_bounded_draft",
        )
        route = OSVoiceRoute(
            True,
            "windows",
            "windows_system_speech",
            "powershell",
            "Microsoft David Desktop",
            "male",
        )
        with patch(
            "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
            return_value=route,
        ):
            decision = candidate_voice_output_decision(candidate, ROOT)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIn("generic windows OS voice", decision["profile_label"])
        self.assertFalse(candidate["text_route_decision"]["custom_voice_output_allowed"])

    def test_actual_ready_custom_reference_packs_are_first_priority(self) -> None:
        custom_ids = (
            "kathryn_merteuil_kathryn_merteuil_20260605_213017",
            "ladybug_marinette_expanded_smoke",
            "peter_parker_spider_man_no_way_home_final_suit",
        )
        os_route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Installed fallback voice",
        )
        with patch(
            "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
            return_value=os_route,
        ):
            for candidate_id in custom_ids:
                with self.subTest(candidate_id=candidate_id):
                    candidate = bind_review_and_voice_route(
                        load_profile_bounded_candidate(ROOT, candidate_id),
                        review_mode="profile_bounded_draft",
                    )
                    decision = candidate_voice_output_decision(candidate, ROOT)
                    self.assertTrue(decision["allowed"])
                    self.assertEqual(decision["route_kind"], "custom_voice_pack")
                    self.assertIsNotNone(decision["os_fallback_route"])
                    self.assertTrue(Path(decision["profile_path"]).is_file())
                    self.assertFalse(decision["authentic_voice_claim"])
                    self.assertIn("exact reviewed reference pack", decision["profile_label"])
                    self.assertIn("synthesized new speech", decision["profile_label"])
                    self.assertTrue(
                        candidate["text_route_decision"]["profile_bounded_label_required"]
                    )

    def test_actual_custom_pack_wav_hash_mismatch_falls_back_without_custom_tts(self) -> None:
        candidate_id = "kathryn_merteuil_kathryn_merteuil_20260605_213017"
        candidate = bind_review_and_voice_route(
            load_profile_bounded_candidate(ROOT, candidate_id),
            review_mode="profile_bounded_draft",
        )
        os_route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Installed fallback voice",
        )
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
                return_value=os_route,
            ),
            patch(
                "tools.temporary_ai_live_chat_gui._file_sha256",
                return_value="0" * 64,
            ),
        ):
            decision = candidate_voice_output_decision(candidate, ROOT)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIn("WAV SHA-256 mismatch", decision["custom_voice_unavailable_reason"])

    def test_actual_candidate_cannot_borrow_another_bound_custom_profile(self) -> None:
        candidate_id = "peter_parker_spider_man_no_way_home_final_suit"
        candidate = bind_review_and_voice_route(
            load_profile_bounded_candidate(ROOT, candidate_id),
            review_mode="profile_bounded_draft",
        )
        candidate = json.loads(json.dumps(candidate))
        voice = candidate["profile"].setdefault("voice_and_behavior", {})
        voice["voice_profile"] = "Voice/profiles/temp_ai/ladybug_voice_profile.json"
        os_route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Installed fallback voice",
        )
        with patch(
            "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
            return_value=os_route,
        ):
            decision = candidate_voice_output_decision(candidate, ROOT)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIsNone(decision["profile_path"])
        self.assertIn(
            "does not match the exact candidate-id binding",
            decision["custom_voice_unavailable_reason"],
        )

    def test_custom_runtime_failure_uses_os_fallback_second(self) -> None:
        candidate = {
            "candidate_id": "ready_custom_person",
            "profile": {
                "candidate_id": "ready_custom_person",
                "display_name": "Ready Custom Person",
            },
        }
        decision = {
            "allowed": True,
            "route_kind": "custom_voice_pack",
            "profile_path": ROOT / "Voice" / "profiles" / "temp_ai" / "test.json",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.load_candidate_voice_config",
                return_value=object(),
            ),
            patch(
                "tools.temporary_ai_live_chat_gui.speak_text",
                return_value={"spoken": False, "reason": "custom_backend_unavailable"},
            ) as custom,
            patch(
                "tools.temporary_ai_live_chat_gui.speak_with_os_voice",
                return_value={"spoken": True, "reason": "ok", "os_voice_fallback_used": True},
            ) as fallback,
            patch(
                "tools.temporary_ai_live_chat_gui.candidate_voice_output_decision",
                return_value=decision,
            ),
        ):
            result = speak_candidate_reply("Hello.", candidate, decision)

        self.assertTrue(result["spoken"])
        self.assertEqual(result["route_kind"], "os_voice_fallback")
        self.assertTrue(result["fallback_attempted"])
        custom.assert_called_once()
        fallback.assert_called_once()

    def test_synthetic_robert_persistent_runtime_is_never_routed_as_temporary_ai(self) -> None:
        candidate = {
            "candidate_id": ROBERT_ID,
            "profile": {
                "candidate_id": ROBERT_ID,
                "display_name": "Synthetic Robert",
                "activation_policy": {
                    "bounded_text_only_conversation_allowed": True,
                    "bounded_voice_conversation_allowed": True,
                },
            },
        }
        with patch("tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route") as detect:
            decision = candidate_voice_output_decision(candidate)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["route_kind"], "persistent_runtime_route_required")
        self.assertIn("not a TemporaryAI", decision["reason"])
        detect.assert_not_called()

    def test_canonical_synthetic_robert_id_blocks_decision_with_blank_or_renamed_display(self) -> None:
        for display_name in ("", "Renamed Downloaded Person"):
            with self.subTest(display_name=display_name), patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route"
            ) as detect:
                decision = candidate_voice_output_decision(
                    {
                        "candidate_id": "synthetic_robert",
                        "profile": {
                            "candidate_id": "synthetic_robert",
                            "display_name": display_name,
                        },
                    }
                )

            self.assertFalse(decision["allowed"])
            self.assertEqual(
                decision["route_kind"], "persistent_runtime_route_required"
            )
            detect.assert_not_called()

    def test_kira_fan_name_cannot_resolve_or_borrow_kira_voice_profile(self) -> None:
        candidate_id = "kira_fan_history_expert_20260821"
        candidate = {
            "candidate_id": candidate_id,
            "profile": {
                "candidate_id": candidate_id,
                "display_name": "Kira Fan and Historian",
                "gender_preference": "Female",
                "activation_policy": {
                    "bounded_text_only_conversation_allowed": True,
                },
            },
        }
        route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Microsoft Zira Desktop - English (United States)",
            "female",
        )
        with patch(
            "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
            return_value=route,
        ) as detect:
            decision = candidate_voice_output_decision(candidate)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIsNone(decision["profile_path"])
        self.assertIn("voice binding", decision["custom_voice_unavailable_reason"])
        self.assertEqual(detect.call_args.args[3], "")

    def test_explicit_foreign_kira_profile_cannot_be_borrowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_id = "h_h_holmes_h_h_holmes_20260605_221432"
            foreign = Path("Voice/profiles/temp_ai/kira_voice_profile.json")
            reference = Path("Voice/reference_packs/kira/approved_reference.wav")
            (root / reference).parent.mkdir(parents=True, exist_ok=True)
            (root / reference).write_bytes(b"RIFF-foreign")
            write_json(
                root / foreign,
                {
                    "voice_id": "kira_temporary_reference_20260706_v1",
                    "target_name": "Kira",
                    "target_type": "temp_ai",
                    "status": {"ready_for_use": True, "ready_for_text_tts": True},
                    "source_audio": {"approved_reference_wav": reference.as_posix()},
                    "sapi_approximation": {"voice_name": "Foreign Kira Voice"},
                },
            )
            candidate = {
                "candidate_id": candidate_id,
                "profile": {
                    "candidate_id": candidate_id,
                    "display_name": "H. H. Holmes",
                    "gender_preference": "Male",
                    "activation_policy": {
                        "bounded_text_only_conversation_allowed": True,
                        "bounded_voice_conversation_allowed": True,
                    },
                    "voice_and_behavior": {"voice_profile": foreign.as_posix()},
                },
            }
            route = OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
                "male",
            )
            with patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
                return_value=route,
            ) as detect:
                decision = candidate_voice_output_decision(candidate, root)

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "os_voice_fallback")
        self.assertIsNone(decision["profile_path"])
        self.assertIn("does not match the exact candidate-id binding", decision["custom_voice_unavailable_reason"])
        self.assertEqual(detect.call_args.args[3], "")

    def test_source_grounded_text_denial_blocks_all_voice_routes(self) -> None:
        candidate = {
            "candidate_id": "source_denied_candidate",
            "profile": {
                "candidate_id": "source_denied_candidate",
                "display_name": "Source Denied",
                "activation_policy": {"bounded_text_only_conversation_allowed": True},
            },
        }
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness",
                return_value=(False, ["source_pack_hash_mismatch"]),
            ),
            patch("tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route") as detect,
        ):
            decision = candidate_voice_output_decision(candidate)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["route_kind"], "source_grounded_text_route_denied")
        self.assertIn("source_pack_hash_mismatch", decision["reason"])
        detect.assert_not_called()

    def test_source_grounded_text_exception_fails_closed_before_voice_detection(self) -> None:
        candidate = {
            "candidate_id": "source_exception_candidate",
            "profile": {
                "candidate_id": "source_exception_candidate",
                "display_name": "Source Exception",
            },
        }
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness",
                side_effect=RuntimeError("hostile source exception"),
            ),
            patch("tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route") as detect,
        ):
            decision = candidate_voice_output_decision(candidate)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["route_kind"], "source_grounded_text_route_check_error")
        self.assertNotIn("hostile source exception", decision["reason"])
        detect.assert_not_called()

    def test_actual_marinette_bounded_route_uses_exact_custom_pack_without_strict_text_gate(self) -> None:
        candidate = load_profile_bounded_candidate(
            ROOT,
            "ladybug_marinette_expanded_smoke",
        )
        candidate["activation_plan"] = {
            "mode_readiness": {
                "text_chat": {"ready": False, "reason": "full-source route unavailable"},
                "bounded_text_review": {"ready": True},
                "voice_chat": {"ready": False, "reason": "full activation voice row remains blocked"},
            }
        }
        candidate = bind_review_and_voice_route(
            candidate,
            review_mode="profile_bounded_draft",
            full_source_reason="strict source pack intentionally unavailable",
        )
        self.assertTrue(candidate["profile"]["identity"]["requires_fail_closed_source_review"])
        route = OSVoiceRoute(
            True,
            "windows",
            "windows_sapi_com",
            "powershell",
            "Microsoft Zira Desktop - English (United States)",
            "female",
        )
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness"
            ) as strict_source,
            patch(
                "tools.temporary_ai_live_chat_gui.cached_candidate_os_voice_route",
                return_value=route,
            ),
            patch(
                "tools.temporary_ai_live_chat_gui.speak_with_os_voice",
                return_value={"spoken": True, "reason": "ok", "os_voice_fallback_used": True},
            ) as speak_os,
            patch(
                "tools.temporary_ai_live_chat_gui.load_candidate_voice_config",
                return_value=object(),
            ),
            patch(
                "tools.temporary_ai_live_chat_gui.speak_text",
                return_value={"spoken": True, "reason": "mock_custom_success"},
            ) as speak_custom,
        ):
            decision = candidate_voice_output_decision(candidate, ROOT)
            spoken = speak_candidate_reply(
                "[Draft review - profile-bounded] Hello from the bounded draft.",
                candidate,
                decision,
                project_root=ROOT,
            )

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["route_kind"], "custom_voice_pack")
        self.assertFalse(decision["authentic_voice_claim"])
        self.assertIn("exact reviewed reference pack", decision["profile_label"])
        self.assertIn("synthesized new speech", decision["profile_label"])
        self.assertTrue(spoken["spoken"])
        self.assertEqual(spoken["route_kind"], "custom_voice_pack")
        self.assertFalse(spoken["authentic_voice_claim"])
        self.assertTrue(spoken["review_mode_label_required"])
        strict_source.assert_not_called()
        speak_os.assert_not_called()
        speak_custom.assert_called_once()

    def test_runtime_model_error_text_is_never_sent_to_tts(self) -> None:
        candidate = {
            "candidate_id": "runtime_error_candidate",
            "profile": {
                "candidate_id": "runtime_error_candidate",
                "display_name": "Runtime Error Candidate",
            },
        }
        decision = {
            "allowed": True,
            "route_kind": "os_voice_fallback",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        with (
            patch("tools.temporary_ai_live_chat_gui.speak_with_os_voice") as speak_os,
            patch("tools.temporary_ai_live_chat_gui.speak_text") as speak_custom,
            patch("tools.temporary_ai_live_chat_gui.candidate_voice_output_decision") as rebuild,
        ):
            result = speak_candidate_reply(
                "[TemporaryAI - error] source loader exploded",
                candidate,
                decision,
            )

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "runtime_source_or_model_error_text")
        speak_os.assert_not_called()
        speak_custom.assert_not_called()
        rebuild.assert_not_called()

    def test_speak_rechecks_source_denial_before_any_tts(self) -> None:
        candidate = {
            "candidate_id": "stale_source_candidate",
            "profile": {
                "candidate_id": "stale_source_candidate",
                "display_name": "Stale Source Candidate",
            },
        }
        crafted = {
            "allowed": True,
            "route_kind": "os_voice_fallback",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness",
                return_value=(False, ["source_now_denied"]),
            ),
            patch("tools.temporary_ai_live_chat_gui.speak_with_os_voice") as speak_os,
            patch("tools.temporary_ai_live_chat_gui.speak_text") as speak_custom,
            patch("tools.temporary_ai_live_chat_gui.candidate_voice_output_decision") as rebuild,
        ):
            result = speak_candidate_reply("Normal reply.", candidate, crafted)

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "source_grounded_text_route_denied")
        speak_os.assert_not_called()
        speak_custom.assert_not_called()
        rebuild.assert_not_called()

    def test_speak_rechecks_source_exception_before_any_tts(self) -> None:
        candidate = {
            "candidate_id": "source_exception_after_queue",
            "profile": {
                "candidate_id": "source_exception_after_queue",
                "display_name": "Source Exception After Queue",
            },
        }
        crafted = {
            "allowed": True,
            "route_kind": "os_voice_fallback",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        with (
            patch(
                "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness",
                side_effect=RuntimeError("source changed after queue"),
            ),
            patch("tools.temporary_ai_live_chat_gui.speak_with_os_voice") as speak_os,
            patch("tools.temporary_ai_live_chat_gui.speak_text") as speak_custom,
            patch("tools.temporary_ai_live_chat_gui.candidate_voice_output_decision") as rebuild,
        ):
            result = speak_candidate_reply("Normal reply.", candidate, crafted)

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "source_grounded_text_route_check_error:RuntimeError")
        self.assertNotIn("source changed after queue", result["reason"])
        speak_os.assert_not_called()
        speak_custom.assert_not_called()
        rebuild.assert_not_called()

    def test_crafted_synthetic_robert_decision_is_rejected_inside_speaker(self) -> None:
        candidate = {
            "candidate_id": ROBERT_ID,
            "profile": {
                "candidate_id": ROBERT_ID,
                "display_name": "Synthetic Robert",
            },
        }
        crafted = {
            "allowed": True,
            "route_kind": "os_voice_fallback",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        with (
            patch("tools.temporary_ai_live_chat_gui.speak_with_os_voice") as speak_os,
            patch("tools.temporary_ai_live_chat_gui.speak_text") as speak_custom,
            patch("tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness") as source_check,
            patch("tools.temporary_ai_live_chat_gui.candidate_voice_output_decision") as rebuild,
        ):
            result = speak_candidate_reply("Crafted reply.", candidate, crafted)

        self.assertFalse(result["spoken"])
        self.assertEqual(
            result["reason"],
            "synthetic_robert_persistent_runtime_voice_route_required",
        )
        self.assertEqual(result["route_kind"], "persistent_runtime_route_required")
        speak_os.assert_not_called()
        speak_custom.assert_not_called()
        source_check.assert_not_called()
        rebuild.assert_not_called()

    def test_canonical_synthetic_robert_id_blocks_speaker_with_blank_or_renamed_display(self) -> None:
        crafted = {
            "allowed": True,
            "route_kind": "os_voice_fallback",
            "os_fallback_route": OSVoiceRoute(
                True,
                "windows",
                "windows_sapi_com",
                "powershell",
                "Microsoft David Desktop - English (United States)",
            ).to_dict(),
        }
        for display_name in ("", "Renamed Downloaded Person"):
            candidate = {
                "candidate_id": "synthetic_robert",
                "profile": {
                    "candidate_id": "synthetic_robert",
                    "display_name": display_name,
                },
            }
            with (
                self.subTest(display_name=display_name),
                patch("tools.temporary_ai_live_chat_gui.speak_with_os_voice") as speak_os,
                patch("tools.temporary_ai_live_chat_gui.speak_text") as speak_custom,
                patch(
                    "tools.temporary_ai_live_chat_gui.source_grounded_text_route_readiness"
                ) as source_check,
                patch(
                    "tools.temporary_ai_live_chat_gui.candidate_voice_output_decision"
                ) as rebuild,
            ):
                result = speak_candidate_reply("Crafted reply.", candidate, crafted)

            self.assertFalse(result["spoken"])
            self.assertEqual(
                result["reason"],
                "synthetic_robert_persistent_runtime_voice_route_required",
            )
            speak_os.assert_not_called()
            speak_custom.assert_not_called()
            source_check.assert_not_called()
            rebuild.assert_not_called()

    def test_queue_rejects_runtime_error_text_without_starting_thread(self) -> None:
        gui = object.__new__(TemporaryAILiveChatGUI)
        gui.candidate = {"candidate_id": "error_candidate", "profile": {"display_name": "Error"}}
        gui.voice_enabled = FakeIntVar(1)
        gui.voice_status = Mock()
        with (
            patch.object(gui, "apply_voice_controls") as apply_controls,
            patch("tools.temporary_ai_live_chat_gui.threading.Thread") as thread,
        ):
            queued = gui.queue_reply_voice("[TemporaryAI - model offline] Ollama unavailable.")

        self.assertFalse(queued)
        apply_controls.assert_not_called()
        thread.assert_not_called()
        self.assertIn(
            "runtime source/model error text is never spoken",
            gui.voice_status.config.call_args.kwargs["text"],
        )

    def test_speech_boundary_turns_off_blocked_candidate_without_calling_backend(self) -> None:
        gui = object.__new__(TemporaryAILiveChatGUI)
        gui.candidate = {
            "candidate_id": "blocked_text_candidate",
            "profile": {
                "display_name": "Blocked Text Candidate",
                "activation_policy": {
                    "bounded_text_only_conversation_allowed": False,
                    "bounded_voice_conversation_allowed": False,
                },
            },
        }
        gui.voice_enabled = FakeIntVar(1)
        gui.voice_toggle = Mock()
        gui.voice_status = Mock()

        with (
            patch("tools.temporary_ai_live_chat_gui.speak_candidate_reply") as speak,
            patch("tools.temporary_ai_live_chat_gui.threading.Thread") as thread,
        ):
            queued = gui.queue_reply_voice("Hello, Robert.")

        self.assertFalse(queued)
        self.assertEqual(gui.voice_enabled.get(), 0)
        speak.assert_not_called()
        thread.assert_not_called()
        rendered = gui.voice_status.config.call_args.kwargs["text"]
        self.assertIn("Voice unavailable (text only)", rendered)


if __name__ == "__main__":
    unittest.main()
