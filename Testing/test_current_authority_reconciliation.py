from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
QWEN_BOUNDARY = ROOT / "System" / "Docs" / "QWEN35_REQUIRED_RUNTIME_BOUNDARY_20260803.md"
AUTHORITY_DOCS = (
    ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
    ROOT / "System" / "docs" / "README_MASTER_INDEX.md",
    ROOT / "System" / "docs" / "KIRA_WORLD_VIDEO_STUDIO_CONTINUATION_AND_MODEL_AUDIT_20260731.md",
    ROOT / "DESKTOP_UPGRADE_HANDOFF.md",
)

class CurrentAuthorityReconciliationTests(unittest.TestCase):
    def test_required_documents_have_read_first_markers_and_qwen_boundary_controls(self) -> None:
        for path in AUTHORITY_DOCS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertTrue(lines[0].startswith("#"))
                self.assertTrue(any("READ FIRST" in line for line in lines[:12]))

        boundary = QWEN_BOUNDARY.read_text(encoding="utf-8")
        self.assertIn("OWNER-CONTROLLING MODEL ROUTING DECISION", boundary)
        self.assertIn(f"model: `{QWEN_MODEL}`", boundary)
        self.assertIn(f"digest: `{QWEN_DIGEST}`", boundary)

    def test_current_model_config_pins_qwen_and_retains_llama_only_as_inactive_rollback(self) -> None:
        config = json.loads((ROOT / "config" / "model_runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(config["status"], "active_exact_qwen35_text_voice")
        self.assertEqual(config["ollama"]["default_model"], QWEN_MODEL)
        self.assertEqual(config["ollama"]["default_digest"], QWEN_DIGEST)
        self.assertEqual(config["gpu_bridge_12gb"]["default_model"], QWEN_MODEL)
        self.assertEqual(config["gpu_bridge_12gb"]["default_digest"], QWEN_DIGEST)
        evaluation = config["desktop_model_evaluation"]
        self.assertEqual(evaluation["status"], "QWEN3.5_9B_CURRENT_OWNER_RUNTIME_MODEL")
        self.assertEqual(evaluation["production_model"], QWEN_MODEL)
        self.assertEqual(evaluation["production_digest"], QWEN_DIGEST)
        self.assertEqual(evaluation["current_model"], QWEN_MODEL)
        self.assertEqual(evaluation["current_digest"], QWEN_DIGEST)
        self.assertEqual(
            evaluation["latest_screening"]["adoption_decision"],
            "promoted_after_full_text_voice_acceptance_and_owner_authorization",
        )
        self.assertTrue(evaluation["automatic_default_change"])
        self.assertFalse(evaluation["owner_review_required"])
        self.assertTrue(evaluation["promotion_authorized_by_owner"])
        self.assertTrue(evaluation["normal_use_authorized_by_owner"])
        rollback = evaluation["dormant_installed_rollback"]
        self.assertEqual(rollback["model"], "llama3.1:8b")
        self.assertIn("not_selected_not_tested_not_automatic_fallback", rollback["status"])
        self.assertTrue(all(value is False for value in evaluation["visual_input_policy"].values()))
        self.assertIn(
            "owner-frozen Video Studio implementations",
            evaluation["excluded_production_scope"],
        )
        self.assertTrue(any("current Lisa" in item for item in evaluation["production_scope"]))
        self.assertTrue(any("current TemporaryAI" in item for item in evaluation["production_scope"]))
        self.assertFalse(any(item == "Lisa" for item in evaluation["excluded_production_scope"]))
        self.assertFalse(any(item == "TemporaryAI" for item in evaluation["excluded_production_scope"]))

        boundary = QWEN_BOUNDARY.read_text(encoding="utf-8")
        self.assertIn(f"model: `{QWEN_MODEL}`", boundary)
        self.assertIn(f"digest: `{QWEN_DIGEST}`", boundary)
        self.assertIn("top-level `think: false`", boundary)
        self.assertIn("remains installed only as a dormant rollback asset", boundary)
        self.assertIn("do not invoke it, test it, route a person to it", boundary)

    def test_owner_runnable_kira_routes_use_exact_qwen_and_frozen_studio_stays_archival(self) -> None:
        required_bindings = {
            "Core/conversation_loop.py": 'os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL)',
            "Start_Kira_Text_Voice_Chat.bat": 'set "KIRA_MODEL_NAME=qwen3.5:9b"',
            "Start_Kira_World_Shell.bat": 'set "KIRA_MODEL_NAME=qwen3.5:9b"',
            "Start_Kira_Chat_Control_Center.bat": 'set "KIRA_MODEL_NAME=qwen3.5:9b"',
            "tools/kira_chat_control_center.py": 'QWEN_MODEL = "qwen3.5:9b"',
            "Start_Kira_Voice_Chat.bat": 'set "KIRA_MODEL_NAME=qwen3.5:9b"',
            "tools/gpu_readiness_check.py": 'DEFAULT_MODEL = "qwen3.5:9b"',
        }
        for relative_path, binding in required_bindings.items():
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(binding, source)

        for relative_path in (
            "Start_Kira_Text_Voice_Chat.bat",
            "Start_Kira_World_Shell.bat",
            "Start_Kira_Chat_Control_Center.bat",
            "Start_Kira_Voice_Chat.bat",
        ):
            launcher = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(f"KIRA_MODEL_DIGEST={QWEN_DIGEST}", launcher)
            self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", launcher)

        text_voice_launcher = (ROOT / "Start_Kira_Text_Voice_Chat.bat").read_text(encoding="utf-8")
        self.assertIn(
            "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2=1",
            text_voice_launcher,
        )

        main_hub = (ROOT / "Start_Kira_Main_Control_Center.bat").read_text(encoding="utf-8")
        self.assertIn('set "KIRA_MODEL_NAME=qwen3.5:9b"', main_hub)
        self.assertIn(f'KIRA_MODEL_DIGEST={QWEN_DIGEST}', main_hub)

        school_life_launchers = (
            "Activate_Kira_And_Lisa.bat",
            "Start_Kira_Miraculous_Continuity_Class.bat",
            "Start_Kira_PreRAM_Micro_School_Test.bat",
            "Start_Kira_Relationship_Empathy_Class.bat",
            "Start_Kira_School_Control_Center.bat",
            "start_kira_school_v2_9hour.bat",
            "Start_Kira_Supervised_6hour_Life_Test.bat",
            "Start_Kira_Supervised_9hour_School_Day.bat",
        )
        for relative_path in school_life_launchers:
            with self.subTest(school_life_relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("KIRA_MODEL_NAME=qwen3.5:9b", source)
                self.assertIn(f"KIRA_MODEL_DIGEST={QWEN_DIGEST}", source)
                self.assertIn("KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0", source)
                self.assertIn(
                    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0",
                    source,
                )
                self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", source)

        studio_settings = (
            ROOT
            / "VideoStudioDevelopment"
            / "alpha_2_0_0_working_20260730"
            / "kira_video_studio"
            / "settings.py"
        ).read_text(encoding="utf-8")
        self.assertIn('ollama_model: str = "llama3.1:8b"', studio_settings)


if __name__ == "__main__":
    unittest.main()
