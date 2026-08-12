from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
HARNESS = ROOT / "tools" / "run_persistent_blackwell_voice_candidate_acceptance.py"

if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

_spec = importlib.util.spec_from_file_location(
    "persistent_blackwell_blender_readiness_probe_for_test",
    HARNESS,
)
assert _spec is not None and _spec.loader is not None
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


def completed(*, returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["powershell.exe"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class PersistentBlackwellBlenderReadinessProbeTests(unittest.TestCase):
    def test_no_process_is_a_successful_inactive_read_only_query(self) -> None:
        payload = json.dumps({"processes": []})
        with patch.object(
            harness.subprocess,
            "run",
            return_value=completed(returncode=0, stdout=payload),
        ) as run:
            evidence = harness.blender_process_evidence()

        self.assertTrue(evidence["query_succeeded"])
        self.assertFalse(evidence["active"])
        self.assertEqual(evidence["matches"], [])
        self.assertFalse(evidence["process_state_changed"])
        command = run.call_args.args[0]
        command_text = " ".join(command)
        self.assertIn("Get-Process -Name blender", command_text)
        for forbidden in ("tasklist", "Get-CimInstance", "Get-WmiObject", "Stop-Process", "taskkill"):
            self.assertNotIn(forbidden.casefold(), command_text.casefold())

    def test_active_process_is_reported_with_exact_pid_and_name(self) -> None:
        payload = json.dumps(
            {
                "processes": [
                    {"pid": 4108, "process_name": "blender"},
                    {"pid": 8240, "process_name": "Blender"},
                ]
            }
        )
        with patch.object(
            harness.subprocess,
            "run",
            return_value=completed(returncode=0, stdout=payload),
        ):
            evidence = harness.blender_process_evidence()

        self.assertTrue(evidence["query_succeeded"])
        self.assertTrue(evidence["active"])
        self.assertEqual(
            evidence["matches"],
            [
                {"pid": 4108, "process_name": "blender"},
                {"pid": 8240, "process_name": "Blender"},
            ],
        )
        self.assertFalse(evidence["process_state_changed"])

    def test_nonzero_and_parse_failures_fail_closed(self) -> None:
        cases = (
            completed(returncode=1, stderr="Access denied"),
            completed(returncode=0, stdout="not-json"),
            completed(returncode=0, stdout=json.dumps({"processes": "malformed"})),
        )
        for result in cases:
            with self.subTest(returncode=result.returncode, stdout=result.stdout):
                with patch.object(harness.subprocess, "run", return_value=result):
                    evidence = harness.blender_process_evidence()
                self.assertFalse(evidence["query_succeeded"])
                self.assertIsNone(evidence["active"])
                self.assertEqual(evidence["matches"], [])
                self.assertFalse(evidence["process_state_changed"])

    def test_required_gate_passes_only_a_proven_inactive_result(self) -> None:
        with patch.object(
            harness,
            "blender_process_evidence",
            return_value={
                "query_succeeded": True,
                "active": False,
                "matches": [],
                "process_state_changed": False,
            },
        ):
            evidence = harness.require_no_active_blender("focused_test")
        self.assertEqual(evidence["boundary"], "focused_test")

        blocked_cases = (
            {
                "query_succeeded": True,
                "active": True,
                "matches": [{"pid": 4108, "process_name": "blender"}],
                "process_state_changed": False,
            },
            {
                "query_succeeded": False,
                "active": None,
                "matches": [],
                "process_state_changed": False,
            },
        )
        for probe_result in blocked_cases:
            with self.subTest(probe_result=probe_result):
                with patch.object(
                    harness,
                    "blender_process_evidence",
                    return_value=dict(probe_result),
                ):
                    with self.assertRaises(RuntimeError):
                        harness.require_no_active_blender("focused_test")

    def test_probe_source_has_no_process_mutation_or_legacy_enumerator(self) -> None:
        source = inspect.getsource(harness.blender_process_evidence).casefold()
        self.assertIn("get-process -name blender", source)
        for forbidden in (
            "tasklist",
            "get-ciminstance",
            "get-wmiobject",
            "stop-process",
            "taskkill",
            "terminateprocess",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
