import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from hardware_intake_check import build_hardware_intake_report  # noqa: E402
from validate_hardware_intake_rest_gate import validate_hardware_intake_rest_gate  # noqa: E402


GATE_PATH = PROJECT_ROOT / "Data" / "launch" / "hardware_intake_rest_gate.json"


class HardwareIntakeRestGateTests(unittest.TestCase):
    def test_gate_validates(self) -> None:
        data = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_hardware_intake_rest_gate(data), [])

    def test_report_blocks_assembly_until_rest(self) -> None:
        report = build_hardware_intake_report(GATE_PATH)
        self.assertFalse(report["blocked"])
        self.assertTrue(report["assembly_blocked_until_rest_gate_passes"])
        self.assertEqual(report["cpu_socket_required"], "LGA1851")
        self.assertEqual(report["ram_required_type"], "DDR5")
        self.assertTrue(report["ram_can_wait"])

    def test_requires_tired_build_blocker(self) -> None:
        data = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        data["rest_before_build_gate"]["assembly_blocked_until_rest_gate_passes"] = False
        errors = validate_hardware_intake_rest_gate(data)
        self.assertIn("rest_before_build_gate.assembly_blocked_until_rest_gate_passes must be true.", errors)

    def test_requires_ram_can_wait(self) -> None:
        data = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        data["post_purchase_compatibility_check"]["ram"]["build_can_wait_if_ram_not_obtained"] = False
        errors = validate_hardware_intake_rest_gate(data)
        self.assertIn("post_purchase_compatibility_check.ram.build_can_wait_if_ram_not_obtained must be true.", errors)


if __name__ == "__main__":
    unittest.main()
