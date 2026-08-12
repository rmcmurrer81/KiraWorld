from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"

# This deliberately enumerates current owner-runnable Kira surfaces.
# RecoverySprint, checkpoints, backups, and legacy_reference remain evidence
# and are not scanned or rewritten.
OWNER_LAUNCHERS = (
    "Start_Kira_Text_Voice_Chat.bat",
    "Start_Kira_World_Shell.bat",
    "Start_Kira_Chat_Control_Center.bat",
    "Start_Kira_Voice_Chat.bat",
)
OWNER_DIRECT_TOOLS = (
    "tools/kira_chat_control_center.py",
    "tools/gpu_readiness_check.py",
)
OWNER_SCHOOL_LIFE_LAUNCHERS = (
    "Activate_Kira_And_Lisa.bat",
    "Start_Kira_Miraculous_Continuity_Class.bat",
    "Start_Kira_PreRAM_Micro_School_Test.bat",
    "Start_Kira_Relationship_Empathy_Class.bat",
    "Start_Kira_School_Control_Center.bat",
    "start_kira_school_v2_9hour.bat",
    "Start_Kira_Supervised_6hour_Life_Test.bat",
    "Start_Kira_Supervised_9hour_School_Day.bat",
)
OWNER_SCHOOL_LIFE_DIRECT_TOOLS = (
    "tools/run_kira_life_day.py",
    "tools/run_kira_miraculous_continuity_class.py",
    "tools/run_kira_relationship_empathy_class.py",
    "tools/run_kira_school_session.py",
    "tools/run_kira_school_v2.py",
)
OWNER_OTHER_PERSON_LAUNCHERS = (
    "Start_Kira_Main_Control_Center.bat",
    "Start_Kira_Creative_Writing_Class.bat",
    "Start_Kira_Enhancement_Roadmap_Class.bat",
    "Start_Kira_Memory_Lanes_Class_Then_Direct_Chat.bat",
    "Start_Kira_Relaxed_Conversation_Class.bat",
    "Start_Kira_Robert_Weekly_Meeting_Audio.bat",
    "Start_Lisa_Chat.bat",
    "Start_Lisa_Supervised_6hour_Life_Test.bat",
    "Start_TemporaryAI_Live_Chat.bat",
    "Start_TemporaryAI_Live_Chat_GUI.bat",
    "Start_TemporaryAI_Life_Loop.bat",
    "Start_TemporaryAI_Control_Center.bat",
)
OWNER_OTHER_PERSON_DIRECT_TOOLS = (
    "tools/run_kira_enhancement_roadmap_class.py",
    "tools/run_kira_memory_lanes_class.py",
    "tools/run_kira_codex_memory_lanes_followup.py",
    "tools/run_kira_relaxed_conversation_class.py",
    "tools/run_kira_robert_weekly_meeting_audio_20260715.py",
    "tools/run_kira_turing_psych_eval.py",
    "tools/temporary_ai_live_chat.py",
)
OWNER_AUXILIARY_MODEL_LAUNCHERS = (
    "Start_Advanced_AI_Probe.bat",
    "Start_Kira_Avatar_Design_Intake_Chat.bat",
    "Start_Kira_PreRAM_Quick_School_Test.bat",
    "Start_TemporaryAI_Candidate_Probe.bat",
    "Start_TemporaryAI_Project_Loop.bat",
)
OWNER_AUXILIARY_MODEL_DIRECT_TOOLS = (
    "tools/run_advanced_ai_probe.py",
    "tools/run_kira_avatar_design_intake_chat.py",
    "tools/run_temporary_ai_candidate_probe.py",
    "tools/run_kira_robert_intro_dialogue_20260714.py",
)
PRESERVED_INACTIVE_LLAMA_HARNESSES = (
    "tools/run_kira_text_voice_bounded_owner_acceptance.py",
    "tools/run_kira_text_voice_two_turn_latency_acceptance.py",
    "tools/validate_kira_turing_psych_voice_gate_preparation.py",
)
EXPLICITLY_OUT_OF_SCOPE_PREFIXES = (
    "RecoverySprint/",
    "legacy_reference/",
    "System/Backups/",
)


class _JsonResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self, _size: int = -1) -> bytes:
        return self._raw


class Qwen35OwnerRunnableRoutesStaticTests(unittest.TestCase):
    def test_owner_launchers_pin_exact_qwen_digest_and_forbid_llama(self) -> None:
        for relative_path in OWNER_LAUNCHERS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertIn(f'set "KIRA_MODEL_NAME={QWEN_MODEL}"', source)
                self.assertIn(f'set "KIRA_MODEL_DIGEST={QWEN_DIGEST}"', source)
                self.assertIn(
                    'set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"', source
                )
                self.assertIn(
                    'set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"',
                    source,
                )
                self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", source)

    def test_owner_direct_tool_defaults_pin_exact_qwen_and_forbid_llama(self) -> None:
        for relative_path in OWNER_DIRECT_TOOLS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertTrue(
                    QWEN_MODEL in source or "QWEN_TEXT_VOICE_MODEL" in source
                )
                self.assertIn(QWEN_DIGEST, source)
                self.assertNotIn("llama3.1:8b", source)

    def test_school_and_life_launchers_pin_qwen_digest_and_disable_llama_candidates(self) -> None:
        for relative_path in OWNER_SCHOOL_LIFE_LAUNCHERS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertIn("KIRA_MODEL_NAME=qwen3.5:9b", source)
                self.assertIn(f"KIRA_MODEL_DIGEST={QWEN_DIGEST}", source)
                self.assertIn("KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0", source)
                self.assertIn(
                    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0",
                    source,
                )
                self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", source)
                self.assertNotIn("--model llama3.1:8b", source)

    def test_school_and_life_direct_tool_defaults_use_qwen_not_llama(self) -> None:
        for relative_path in OWNER_SCHOOL_LIFE_DIRECT_TOOLS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertIn(QWEN_MODEL, source)
                self.assertNotIn("llama3.1:8b", source)

    def test_other_current_person_launchers_pin_qwen_digest_and_disable_llama_candidates(self) -> None:
        for relative_path in OWNER_OTHER_PERSON_LAUNCHERS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertIn("KIRA_MODEL_NAME=qwen3.5:9b", source)
                self.assertIn(f"KIRA_MODEL_DIGEST={QWEN_DIGEST}", source)
                self.assertIn("KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0", source)
                self.assertIn("KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0", source)
                self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", source)

    def test_other_current_person_direct_tool_defaults_use_qwen_not_llama(self) -> None:
        for relative_path in OWNER_OTHER_PERSON_DIRECT_TOOLS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertTrue(
                    QWEN_MODEL in source or "QWEN_TEXT_VOICE_MODEL" in source
                )
                self.assertNotIn("llama3.1:8b", source)

    def test_auxiliary_owner_model_launchers_pin_exact_qwen_and_disable_llama(self) -> None:
        for relative_path in OWNER_AUXILIARY_MODEL_LAUNCHERS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertIn(f"KIRA_MODEL_NAME={QWEN_MODEL}", source)
                self.assertIn(f"KIRA_MODEL_DIGEST={QWEN_DIGEST}", source)
                self.assertIn("KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0", source)
                self.assertIn(
                    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0",
                    source,
                )
                self.assertNotIn("llama3.1:8b", source)

    def test_auxiliary_direct_tools_use_qwen_policy_and_no_llama_default(self) -> None:
        for relative_path in OWNER_AUXILIARY_MODEL_DIRECT_TOOLS:
            with self.subTest(relative_path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8-sig")
                self.assertTrue(
                    QWEN_MODEL in source or "QWEN_TEXT_VOICE_MODEL" in source
                )
                self.assertTrue(
                    QWEN_DIGEST in source or "QWEN_TEXT_VOICE_DIGEST" in source
                )
                self.assertNotIn("llama3.1:8b", source)

    def test_active_runtime_manifest_pins_qwen_and_retains_llama_only_as_inactive_rollback(self) -> None:
        manifest = json.loads((ROOT / "config" / "model_runtime.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(manifest["status"], "active_exact_qwen35_text_voice")
        self.assertEqual(manifest["default_backend"], "ollama")
        self.assertEqual(manifest["ollama"]["default_model"], QWEN_MODEL)
        self.assertEqual(manifest["ollama"]["default_digest"], QWEN_DIGEST)
        evaluation = manifest["desktop_model_evaluation"]
        self.assertEqual(evaluation["production_model"], QWEN_MODEL)
        self.assertEqual(evaluation["production_digest"], QWEN_DIGEST)
        rollback = evaluation["dormant_installed_rollback"]
        self.assertEqual(rollback["model"], "llama3.1:8b")
        self.assertIn("not_selected_not_tested_not_automatic_fallback", rollback["status"])

        registry = json.loads(
            (ROOT / "config" / "model_upgrade_candidate_registry.json").read_text(
                encoding="utf-8-sig"
            )
        )
        llama = next(
            item
            for item in registry["candidates"]
            if item["candidate_id"] == "llama31_8b_rollback"
        )
        self.assertEqual(llama["role"], "dormant_installed_rollback")
        self.assertEqual(
            llama["disposition"],
            "preserve_installed_exclude_from_current_execution",
        )
        self.assertFalse(llama["runtime"]["benchmark"]["default_probe"])

    def test_normal_text_voice_launcher_enables_the_selected_blackwell_gpu_route(self) -> None:
        source = (ROOT / "Start_Kira_Text_Voice_Chat.bat").read_text(encoding="utf-8-sig")
        self.assertIn('set "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2=1"', source)
        self.assertIn('set "KIRA_DISABLE_BLACKWELL_GPU_VOICE=0"', source)
        self.assertIn('set "KIRA_VOICE_FORCE_SAPI=0"', source)

    def test_scan_scope_is_explicit_and_does_not_rewrite_archival_evidence(self) -> None:
        self.assertEqual(len(OWNER_LAUNCHERS), len(set(OWNER_LAUNCHERS)))
        self.assertEqual(len(OWNER_DIRECT_TOOLS), len(set(OWNER_DIRECT_TOOLS)))
        self.assertEqual(
            len(OWNER_SCHOOL_LIFE_LAUNCHERS),
            len(set(OWNER_SCHOOL_LIFE_LAUNCHERS)),
        )
        self.assertEqual(
            len(OWNER_SCHOOL_LIFE_DIRECT_TOOLS),
            len(set(OWNER_SCHOOL_LIFE_DIRECT_TOOLS)),
        )
        self.assertEqual(len(OWNER_OTHER_PERSON_LAUNCHERS), len(set(OWNER_OTHER_PERSON_LAUNCHERS)))
        self.assertEqual(len(OWNER_OTHER_PERSON_DIRECT_TOOLS), len(set(OWNER_OTHER_PERSON_DIRECT_TOOLS)))
        self.assertEqual(
            len(OWNER_AUXILIARY_MODEL_LAUNCHERS),
            len(set(OWNER_AUXILIARY_MODEL_LAUNCHERS)),
        )
        self.assertEqual(
            len(OWNER_AUXILIARY_MODEL_DIRECT_TOOLS),
            len(set(OWNER_AUXILIARY_MODEL_DIRECT_TOOLS)),
        )
        self.assertIn("RecoverySprint/", EXPLICITLY_OUT_OF_SCOPE_PREFIXES)
        for relative_path in (
            *OWNER_LAUNCHERS,
            *OWNER_DIRECT_TOOLS,
            *OWNER_SCHOOL_LIFE_LAUNCHERS,
            *OWNER_SCHOOL_LIFE_DIRECT_TOOLS,
            *OWNER_OTHER_PERSON_LAUNCHERS,
            *OWNER_OTHER_PERSON_DIRECT_TOOLS,
            *OWNER_AUXILIARY_MODEL_LAUNCHERS,
            *OWNER_AUXILIARY_MODEL_DIRECT_TOOLS,
        ):
            normalized = relative_path.replace("\\", "/")
            self.assertFalse(
                any(normalized.startswith(prefix) for prefix in EXPLICITLY_OUT_OF_SCOPE_PREFIXES)
            )

    def test_only_explicit_historical_harnesses_retain_llama_in_current_tools(self) -> None:
        preserved = {path.replace("\\", "/") for path in PRESERVED_INACTIVE_LLAMA_HARNESSES}
        observed: set[str] = set()
        for path in (ROOT / "tools").iterdir():
            if path.suffix.casefold() not in {".py", ".ps1"}:
                continue
            relative = path.relative_to(ROOT).as_posix()
            source = path.read_text(encoding="utf-8-sig", errors="replace")
            if "llama3.1:8b" in source:
                observed.add(relative)
        self.assertTrue(observed.issubset(preserved), observed - preserved)
        for relative_path in PRESERVED_INACTIVE_LLAMA_HARNESSES:
            self.assertTrue((ROOT / relative_path).is_file())

        root_launchers = "\n".join(
            path.read_text(encoding="utf-8-sig", errors="replace")
            for path in ROOT.glob("*.bat")
        )
        for relative_path in PRESERVED_INACTIVE_LLAMA_HARNESSES:
            self.assertNotIn(Path(relative_path).name, root_launchers)

    def test_qwen_ordinary_request_policy_is_non_thinking_and_releases_residency(self) -> None:
        from Core.model_request_policy import ordinary_model_request_fields

        self.assertEqual(
            ordinary_model_request_fields(QWEN_MODEL, keep_alive=0),
            {"think": False, "keep_alive": 0},
        )

    def test_gpu_readiness_identity_and_probe_are_exact_non_thinking_mock_only(self) -> None:
        from tools import gpu_readiness_check as readiness

        tags = _JsonResponse(
            {
                "models": [
                    {
                        "name": QWEN_MODEL,
                        "model": QWEN_MODEL,
                        "digest": QWEN_DIGEST,
                    }
                ]
            }
        )
        with patch.object(readiness.urllib.request, "urlopen", return_value=tags):
            identity = readiness.check_exact_ollama_model_identity(timeout=1)
        self.assertTrue(identity["ok"], identity)
        self.assertEqual(identity["observed_digest"], QWEN_DIGEST)

        reply = _JsonResponse(
            {
                "model": QWEN_MODEL,
                "message": {"role": "assistant", "content": "Kira GPU probe OK"},
                "done": True,
            }
        )
        with patch.object(readiness.urllib.request, "urlopen", return_value=reply) as mocked:
            result = readiness.run_ollama_probe(QWEN_MODEL, timeout=1)
        self.assertTrue(result["ok"], result)
        self.assertIs(result["think"], False)
        self.assertEqual(result["keep_alive"], 0)
        request = mocked.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], QWEN_MODEL)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], 0)
        self.assertFalse(payload["stream"])

        with patch.object(readiness.urllib.request, "urlopen") as forbidden_network:
            blocked = readiness.run_ollama_probe("not-current-model:8b", timeout=1)
        self.assertFalse(blocked["ok"])
        forbidden_network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
