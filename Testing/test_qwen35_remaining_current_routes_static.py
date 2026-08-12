from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"


class Qwen35RemainingCurrentRoutesStaticTests(unittest.TestCase):
    def test_central_authority_pins_qwen_and_rejects_mismatch(self) -> None:
        from Core.model_request_policy import (
            pin_exact_qwen35_environment,
            require_exact_qwen35_selection,
        )

        self.assertEqual(
            require_exact_qwen35_selection(QWEN_MODEL, QWEN_DIGEST),
            (QWEN_MODEL, QWEN_DIGEST),
        )
        for model, digest in (("", QWEN_DIGEST), (QWEN_MODEL, ""), ("other:1b", QWEN_DIGEST)):
            with self.subTest(model=model, digest=digest), self.assertRaises(RuntimeError):
                require_exact_qwen35_selection(model, digest)

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(pin_exact_qwen35_environment(), (QWEN_MODEL, QWEN_DIGEST))
        with patch.dict(
            os.environ,
            {"KIRA_MODEL_NAME": "other:1b", "KIRA_MODEL_DIGEST": QWEN_DIGEST},
            clear=True,
        ), self.assertRaises(RuntimeError):
            pin_exact_qwen35_environment()

    def test_current_direct_person_tools_have_no_llama_selection(self) -> None:
        current_routes = (
            "tools/create_kira_inner_life_journal_entry.py",
            "tools/run_kira_codex_direct_everyday_chat.py",
            "tools/run_kira_codex_direct_custom_chat.py",
            "tools/run_kira_chicago_holmes_repair_class.py",
            "tools/run_kira_chicago_archivist_class.py",
            "tools/run_kira_idle_study_loop.py",
            "tools/run_kira_humanity_class.py",
            "tools/run_kira_communication_empathy_class.py",
            "tools/run_kira_avatar_design_intake_chat.py",
            "tools/run_lisa_codex_memory_privacy_review_chat.py",
            "tools/run_kira_lisa_slumber_party.py",
            "tools/run_kira_lisa_sex_talk_club.py",
            "tools/run_kira_lisa_mature_book_club.py",
            "tools/run_advanced_ai_probe.py",
            "tools/run_temporary_ai_candidate_probe.py",
            "tools/run_kira_codex_life_test_debrief_chat.py",
            "tools/run_kira_codex_future_upgrades_chat.py",
            "tools/run_robert_presence_ai_turing_psych_eval.py",
            "tools/run_kira_robert_intro_dialogue_20260714.py",
            "tools/kira_spa_resource_smoke.py",
            "tools/run_qwen_webcam_microphone_live_acceptance.py",
            "tools/run_resident_media_experience_live_acceptance.py",
        )
        for relative in current_routes:
            with self.subTest(relative=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("llama3.1:8b", source.casefold())
                self.assertTrue(
                    QWEN_MODEL in source or "QWEN_TEXT_VOICE_MODEL" in source or "QWEN_VISION_MODEL" in source
                )
                self.assertTrue(
                    QWEN_DIGEST in source
                    or "QWEN_TEXT_VOICE_DIGEST" in source
                    or "QWEN_VISION_DIGEST" in source
                )

    def test_all_root_owner_launchers_have_no_llama_model_selection(self) -> None:
        for path in ROOT.glob("*.bat"):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8", errors="ignore").casefold()
                self.assertNotIn("kira_model_name=llama3.1:8b", source)
                self.assertNotIn("--model llama3.1:8b", source)

    def test_current_live_sensory_and_media_harnesses_use_qwen_text(self) -> None:
        webcam = (ROOT / "tools/run_qwen_webcam_microphone_live_acceptance.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("TEXT_MODEL = QWEN_VISION_MODEL", webcam)
        self.assertIn('"KIRA_MODEL_DIGEST": TEXT_DIGEST', webcam)
        self.assertIn('"two_exact_qwen_text_turns"', webcam)

        media = (ROOT / "tools/run_resident_media_experience_live_acceptance.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("EXACT_TEXT_MODEL = EXACT_QWEN_MODEL", media)
        self.assertIn('os.environ["KIRA_MODEL_DIGEST"] = EXACT_TEXT_DIGEST', media)
        self.assertIn('"exact_qwen_text_used"', media)

    def test_dormant_rollback_cannot_be_selected_by_benchmark(self) -> None:
        from tools.benchmark_model_upgrade_candidates import RegistryError, _selected_candidates

        registry = json.loads(
            (ROOT / "config/model_upgrade_candidate_registry.json").read_text(encoding="utf-8")
        )
        with self.assertRaisesRegex(RegistryError, "forbids executing dormant rollback"):
            _selected_candidates(registry, ["llama31_8b_rollback"])
        selected = _selected_candidates(registry, ["qwen35_9b_q4_first"])
        self.assertEqual([item["candidate_id"] for item in selected], ["qwen35_9b_q4_first"])

    def test_runtime_scope_includes_every_current_person_lane(self) -> None:
        runtime = json.loads((ROOT / "config/model_runtime.json").read_text(encoding="utf-8"))
        evaluation = runtime["desktop_model_evaluation"]
        self.assertEqual(evaluation["production_model"], QWEN_MODEL)
        self.assertEqual(evaluation["production_digest"], QWEN_DIGEST)
        joined = "\n".join(evaluation["production_scope"])
        for marker in ("current Kira", "current Lisa", "current TemporaryAI", "current Robert"):
            self.assertIn(marker, joined)
        excluded = "\n".join(evaluation["excluded_production_scope"])
        self.assertNotIn("\nLisa\n", "\n" + excluded + "\n")
        self.assertNotIn("\nTemporaryAI\n", "\n" + excluded + "\n")


if __name__ == "__main__":
    unittest.main()
