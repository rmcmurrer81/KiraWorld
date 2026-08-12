import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from pre_trip_readiness_check import build_pre_trip_report  # noqa: E402
from validate_pre_trip_desktop_pickup_checklist import validate_pre_trip_desktop_pickup_checklist  # noqa: E402


class PreTripDesktopPickupChecklistTests(unittest.TestCase):
    def test_checklist_validates(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_pre_trip_desktop_pickup_checklist(data), [])

    def test_report_not_blocked(self) -> None:
        report = build_pre_trip_report(PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json")
        self.assertFalse(report["blocked"])
        self.assertTrue(report["system_flags_safe"])

    def test_requires_backup_before_leaving(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json").read_text(encoding="utf-8"))
        data["before_leaving"]["required_confirmations"].remove("backup_manifest_created")
        errors = validate_pre_trip_desktop_pickup_checklist(data)
        self.assertIn("before_leaving.required_confirmations missing: backup_manifest_created", errors)

    def test_requires_cpu_socket_check(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json").read_text(encoding="utf-8"))
        data["hardware_pickup"]["cpu"]["socket_must_match_motherboard"] = False
        errors = validate_pre_trip_desktop_pickup_checklist(data)
        self.assertIn("hardware_pickup.cpu.socket_must_match_motherboard must be true.", errors)


if __name__ == "__main__":
    unittest.main()
