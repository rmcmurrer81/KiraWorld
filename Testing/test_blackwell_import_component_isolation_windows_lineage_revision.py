from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe_v3.py"
V2_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe_v2.py"
V2_SHA256 = "95d6a37c141b4ec7c425bc22a023e089ea91c0f041173d7940de2450d3750a0a"
MICRODIAGNOSTIC_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_import_component_isolation_attempt01_analysis"
    / "WINDOWS_VENV_REDIRECTOR_MICRODIAGNOSTIC.json"
)
MICRODIAGNOSTIC_SHA256 = "3606e8e42776db2a229569baee9169643f57e4cc4ac8af40098a44d6f43c7593"
FAILED_ATTEMPT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_component_isolation_v2"
    / "attempt_01"
)
FAILED_HASHES = {
    "ATTEMPT_STARTED.json": "ef4cc76a76214adcb50f274c1a3fb3d7a98e12699c15140fba39395723e7843b",
    "CHILD_STDERR.log": "ab90b715b96ffe1b2f519b6e02fe6a5142d8df6ea1f83e8f6ac34d31aa7f11c6",
    "COMPONENT_ISOLATION_V2_REPORT.json": "48a04f20ff55df89fafdb3373b19b091591884fb4f5fff3ea432008b07d49774",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load_module("blackwell_component_isolation_v3_lineage_test", TOOL_PATH)


class BlackwellImportComponentIsolationWindowsLineageRevisionTests(unittest.TestCase):
    def test_sealed_v2_and_redirector_evidence_are_exact(self) -> None:
        self.assertEqual(probe.sha256_file(V2_PATH), V2_SHA256)
        self.assertEqual(
            probe.sha256_file(MICRODIAGNOSTIC_PATH),
            MICRODIAGNOSTIC_SHA256,
        )

    def test_failed_attempt_01_remains_byte_exact(self) -> None:
        for name, expected in FAILED_HASHES.items():
            self.assertEqual(probe.sha256_file(FAILED_ATTEMPT / name), expected, name)

    def test_static_self_check_is_inert_and_passes(self) -> None:
        result = probe.static_self_check()
        self.assertTrue(result["passed"], result)
        for key in (
            "blackwell_runtime_started",
            "torch_imported",
            "cuda_api_invoked",
            "model_loaded",
            "audio_generated",
            "playback_performed",
            "ollama_invoked",
            "defender_queried",
            "defender_changed",
            "candidate_promoted",
            "production_routing_changed",
        ):
            self.assertIs(result[key], False, key)

    def test_current_controller_identity_is_live_and_exactly_queryable(self) -> None:
        identity = probe._windows_process_identity(os.getpid())
        self.assertTrue(identity["query_succeeded"], identity)
        self.assertEqual(identity["pid"], os.getpid())
        self.assertGreater(identity["creation_time_100ns"], 0)
        self.assertTrue(identity["image_path"])
        self.assertTrue(probe._same_process_identity(identity, identity))

    def test_direct_popen_child_is_accepted(self) -> None:
        result = probe.classify_windows_launch_lineage(
            controller_pid=100,
            popen_launch_pid=200,
            executing_child_pid=200,
            executing_child_parent_pid=100,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["lineage_kind"], "DIRECT_POPEN_CHILD")

    def test_confirmed_one_redirector_lineage_is_accepted(self) -> None:
        evidence = json.loads(MICRODIAGNOSTIC_PATH.read_text(encoding="utf-8"))
        result = probe.classify_windows_launch_lineage(
            controller_pid=evidence["observed_controller_powershell_pid"],
            popen_launch_pid=evidence["observed_redirector_pid"],
            executing_child_pid=evidence["observed_executing_python_pid"],
            executing_child_parent_pid=evidence["executing_python_os_getppid"],
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["lineage_kind"], "ONE_WINDOWS_VENV_REDIRECTOR")
        self.assertEqual(result["maximum_redirector_depth"], 1)

    def test_unrelated_spoofed_or_deeper_chain_is_rejected(self) -> None:
        cases = (
            dict(
                controller_pid=100,
                popen_launch_pid=999,
                executing_child_pid=300,
                executing_child_parent_pid=200,
            ),
            dict(
                controller_pid=100,
                popen_launch_pid=200,
                executing_child_pid=300,
                executing_child_parent_pid=999,
            ),
            dict(
                controller_pid=100,
                popen_launch_pid=200,
                executing_child_pid=400,
                executing_child_parent_pid=300,
            ),
        )
        for case in cases:
            result = probe.classify_windows_launch_lineage(**case)
            self.assertFalse(result["passed"], case)
            self.assertEqual(
                result["lineage_kind"],
                "UNRELATED_OR_UNBOUNDED_PROCESS_CHAIN",
            )

    def test_launch_binding_hmac_rejects_tampering(self) -> None:
        payload = {
            "schema_version": 1,
            "artifact_kind": "blackwell_import_component_isolation_v3_parent_launch_binding",
            "controller_process_identity": {"pid": 100, "creation_time_100ns": 5},
            "popen_launch_pid": 200,
        }
        signature = probe._launch_binding_hmac(payload, "n" * 48)
        payload["binding_hmac_sha256"] = signature
        self.assertEqual(probe._launch_binding_hmac(payload, "n" * 48), signature)
        payload["popen_launch_pid"] = 999
        self.assertNotEqual(probe._launch_binding_hmac(payload, "n" * 48), signature)

    def test_process_identity_rejects_pid_reuse_or_executable_spoof(self) -> None:
        expected = {
            "query_succeeded": True,
            "pid": 200,
            "creation_time_100ns": 50,
            "image_path": r"c:\\venv\\python.exe",
        }
        self.assertTrue(probe._same_process_identity(expected, dict(expected)))
        reused_pid = dict(expected, creation_time_100ns=51)
        wrong_executable = dict(expected, image_path=r"c:\\other\\python.exe")
        self.assertFalse(probe._same_process_identity(expected, reused_pid))
        self.assertFalse(probe._same_process_identity(expected, wrong_executable))

    def test_child_requires_signed_binding_before_dependency_or_torch(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        child = source[source.index("\ndef child_arm_v3") : source.index("\ndef _drain_stdout")]
        self.assertLess(
            child.index("_validate_child_authorization("),
            child.index("_load_rejected_dependency()"),
        )
        authorization = source[
            source.index("\ndef _validate_launch_binding") : source.index(
                "\ndef _emit_pipe_bundle_event"
            )
        ]
        for marker in (
            "binding_hmac_sha256",
            "controller_still_live_and_exact",
            "launch_process_still_live_and_exact",
            "bounded_launch_lineage",
            "popen_launch_pid",
            "same_attempt_directory",
            "child no-active-Blender gate failed",
        ):
            self.assertIn(marker, source)
        self.assertIn("_validate_launch_binding(", authorization)

    def test_success_requires_stable_launch_binding_artifact(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        run = source[source.index("\ndef run_one_arm_v3") : source.index("\ndef describe")]
        self.assertIn("launch_binding_artifact = stable_artifact", run)
        self.assertIn("and launch_binding_artifact is not None", run)
        self.assertIn('launch_binding_artifact.get("sha256") == launch_binding_hash', run)
        self.assertIn('"launch_binding_artifact": launch_binding_artifact', run)


if __name__ == "__main__":
    unittest.main()
