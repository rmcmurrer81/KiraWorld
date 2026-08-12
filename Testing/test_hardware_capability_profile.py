import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from hardware_capability_check import build_hardware_capability_report, select_stage  # noqa: E402
from validate_hardware_capability_profile import validate_hardware_capability_profile  # noqa: E402


PROFILE_PATH = PROJECT_ROOT / "Data" / "launch" / "hardware_capability_profile.json"


class HardwareCapabilityProfileTests(unittest.TestCase):
    def test_profile_validates(self) -> None:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_hardware_capability_profile(data), [])

    def test_default_report_uses_current_32gb_gpu_bridge_stage(self) -> None:
        report = build_hardware_capability_report(PROFILE_PATH)
        self.assertFalse(report["blocked"])
        self.assertEqual(report["selected_stage"], "stage_16gb_gpu_bridge")
        self.assertIn("multiple_persistent_ai_runtime", report["blocked_work"])
        self.assertIn("early_avatar_reference_processing", report["allowed_work"])
        self.assertEqual(report["current_observed_ram"]["capacity_gb"], 32)
        self.assertEqual(report["current_observed_ram"]["configured_speed_mt_s"], 6000)
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        observed = data["known_build"]["current_observed_ram"]
        self.assertEqual(observed["capacity_gb"], 32)
        self.assertEqual(observed["configured_speed_mt_s"], 6000)

    def test_64gb_without_gpu_selects_local_life_stage(self) -> None:
        report = build_hardware_capability_report(PROFILE_PATH, actual_ram_gb=64, gpu_vram_gb=0)
        self.assertEqual(report["selected_stage"], "stage_64gb_local_life")
        self.assertIn("kira_text_life_sessions", report["allowed_work"])
        self.assertIn("webcam_based_awareness_as_default", report["blocked_work"])

    def test_64gb_with_gpu_selects_gpu_stage(self) -> None:
        report = build_hardware_capability_report(PROFILE_PATH, actual_ram_gb=64, gpu_vram_gb=16)
        self.assertEqual(report["selected_stage"], "stage_gpu_expansion")
        self.assertIn("voice_input_output_pipeline", report["allowed_work"])
        self.assertIn("unreviewed_internet_autonomy", report["blocked_work"])

    def test_gpu_stage_requires_enough_vram(self) -> None:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        stage = select_stage(data, actual_ram_gb=64, gpu_vram_gb=8)
        self.assertEqual(stage["stage_id"], "stage_64gb_local_life")

    def test_requires_16gb_stage_blocks_voice_and_temp_ai(self) -> None:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        setup = next(stage for stage in data["capability_stages"] if stage["stage_id"] == "stage_16gb_setup")
        setup["blocked_work"].remove("voice_conversation_as_default")
        errors = validate_hardware_capability_profile(data)
        self.assertIn("stage_16gb_setup.blocked_work missing: voice_conversation_as_default", errors)


if __name__ == "__main__":
    unittest.main()
