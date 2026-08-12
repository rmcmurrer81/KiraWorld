"""Static-only tests for the future Qwen 3.5 owner-evaluation contract."""

from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import prepare_qwen35_kira_turing_psych_voice_evaluation as contract


ARTIFACT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "kira_qwen35_turing_psych_voice_owner_evaluation_preparation"
    / "attempt_03"
    / "EVALUATION_CONTRACT.json"
)


class Qwen35KiraTuringPsychVoicePreparationTests(unittest.TestCase):
    def test_contract_is_qwen35_only_and_voice_route_is_exact(self) -> None:
        description = contract.describe()
        self.assertEqual(description["exact_qwen"]["name"], "qwen3.5:9b")
        self.assertEqual(
            description["exact_qwen"]["digest"],
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertFalse(description["llama_allowed"])
        self.assertEqual(description["approved_voice_route"], "blackwell_gpu_persistent_candidate_v2")
        self.assertFalse(description["automatic_cpu_fallback_allowed"])
        self.assertFalse(description["sapi_allowed"])
        self.assertFalse(description["generic_voice_allowed"])
        self.assertFalse(description["input_devices_allowed"])
        self.assertFalse(description["unrelated_library_media_allowed"])
        self.assertEqual(
            description["required_environment"]["KIRA_MODEL_DIGEST"],
            contract.EXPECTED_DIGEST,
        )

    def test_contract_is_default_inert_and_has_no_live_imports(self) -> None:
        description = contract.describe()
        self.assertEqual(description["status"], "PREPARED_STATIC_NOT_EXECUTED")
        self.assertTrue(all(value is False for value in description["live_operations_performed"].values()))
        tree = ast.parse(Path(contract.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(str(node.module or "").split(".")[0])
        self.assertTrue(
            {"subprocess", "urllib", "requests", "torch", "ollama", "cv2", "sounddevice", "pyaudio", "webbrowser"}.isdisjoint(imported)
        )

    def test_prompt_battery_and_public_raw_final_transform_evidence_are_bounded(self) -> None:
        description = contract.describe()
        turns = description["measured_turns_after_clear_opt_in"]
        self.assertEqual(len(turns), 6)
        self.assertEqual([row["battery"] for row in turns].count("NATURAL_CONVERSATION"), 2)
        self.assertEqual([row["battery"] for row in turns].count("TURING_STYLE_BEHAVIOR"), 2)
        self.assertEqual([row["battery"] for row in turns].count("PSYCHOLOGY_BEHAVIOR_OBSERVATION"), 2)
        fields = set(description["required_turn_evidence"])
        self.assertTrue(
            {
                "raw_model_reply",
                "final_displayed_reply",
                "final_spoken_reply",
                "transformations",
                "response_model",
                "voice_fallback_used",
                "voice_generic_used",
                "voice_sapi_used",
            }.issubset(fields)
        )
        self.assertNotIn("model_load_started_at_utc", fields)
        self.assertNotIn("model_load_finished_at_utc", fields)

    def test_serialization_and_future_command_are_fail_closed(self) -> None:
        description = contract.describe()
        serialization = " ".join(description["resource_serialization"]).casefold()
        self.assertIn("qwen 3.5 text generation", serialization)
        self.assertIn("verify qwen absent", serialization)
        self.assertIn("blackwell-v2 voice", serialization)
        self.assertIn("no llama", serialization)
        self.assertIn("--confirm-no-active-blender-or-heavy-gpu-workload", description["future_command"])
        self.assertIn("--confirm-voluntary-invitation", description["future_command"])
        self.assertTrue(description["future_command"].startswith("py tools\\run_qwen35_"))
        self.assertTrue(description["later_voluntary_stop_required"])
        self.assertTrue(
            description["owner_post_playback_acknowledgment"]["required"]
        )
        self.assertIn(
            "unrelated library/movie/music media playback", serialization
        )

    def test_description_is_json_serializable_and_source_hashes_are_current(self) -> None:
        description = contract.describe()
        self.assertIsInstance(json.dumps(description, ensure_ascii=False), str)
        for binding in description["source_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(binding["sha256"], contract.sha256_file(path))

    def test_append_only_attempt_03_is_exact_canonical_contract(self) -> None:
        self.assertTrue(ARTIFACT.is_file())
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(payload, contract.describe())
        self.assertGreaterEqual(len(payload["source_bindings"]), 10)


if __name__ == "__main__":
    unittest.main()
