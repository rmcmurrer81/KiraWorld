from __future__ import annotations

import copy
import inspect
import json
import unittest
from pathlib import Path
from unittest import mock

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v4 as v4
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


class LongKiraTuringHealthBodyVoiceEvaluationV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        names = (
            "__file__",
            "HARNESS_ID",
            "EVIDENCE_ROOT",
            "GENERATED_ROOT",
            "PREPARATION_ARTIFACT",
            "MAX_TOTAL_QWEN_REQUESTS",
            "CHILD_WATCHDOG_SECONDS",
            "PARENT_TIMEOUT_SECONDS",
            "canonical_preparation_bytes",
            "load_preparation_contract",
            "preparation_contract_issues",
            "final_run_contract_issues",
            "REQUIRED_PUBLIC_FLAGS",
            "collect_post_playback_owner_acknowledgment",
            "heavy_workload_preflight",
        )
        snapshot = {name: getattr(retained, name) for name in names}
        turns = retained.prepared.EVALUATION_TURNS
        invitation = retained.prepared.VOLUNTARY_PUBLIC_INVITATION

        def restore() -> None:
            for name, value in snapshot.items():
                setattr(retained, name, value)
            retained.prepared.EVALUATION_TURNS = turns
            retained.prepared.VOLUNTARY_PUBLIC_INVITATION = invitation

        self.addCleanup(restore)

    @staticmethod
    def _clean_inventory(*names: str) -> dict:
        normalized = sorted(set(name.casefold() for name in names))
        return {
            "schema_version": 1,
            "method": v4.PROCESS_INVENTORY_METHOD,
            "succeeded": True,
            "snapshot_created": True,
            "first_entry_succeeded": True,
            "terminal_no_more_files": True,
            "snapshot_closed": True,
            "process_names": normalized,
            "process_count": len(normalized),
            "error_type": "",
            "win32_error": 0,
            "arbitrary_process_handle_opened": False,
        }

    @staticmethod
    def _clean_gpu(utilization: float = 7.0) -> dict:
        return {
            "query_succeeded": True,
            "rows": [{"index": 0, "utilization_percent": utilization}],
        }

    def _load_and_configure(self, *, unattended: bool = True):
        execution, v3_execution, effective = v4.load_and_validate_v4_contract()
        v4.configure_retained_runner_v4(
            execution,
            v3_execution,
            effective,
            unattended=unattended,
        )
        return execution, effective

    def test_v4_contract_preserves_exact_v3_content_and_cap(self) -> None:
        execution, _, effective = v4.load_and_validate_v4_contract()
        self.assertEqual(execution["schema_version"], 4)
        self.assertEqual(len(effective["turns"]), 35)
        self.assertEqual(effective["model"]["maximum_generations"], 36)
        self.assertEqual(effective["model"]["name"], "qwen3.5:9b")
        self.assertFalse(effective["model"]["llama_allowed"])
        self.assertEqual(
            effective["voice"]["route"],
            "blackwell_gpu_persistent_candidate_v2",
        )
        self.assertEqual(effective["voice"]["device"], "cuda")
        self.assertFalse(effective["voice"]["cpu_fallback_allowed"])
        self.assertFalse(effective["voice"]["sapi_allowed"])
        self.assertFalse(effective["voice"]["generic_voice_allowed"])

    def test_v3_consumed_evidence_is_exact_and_no_retry(self) -> None:
        execution, _, _ = v4.load_and_validate_v4_contract()
        predecessor = execution["predecessor"]
        self.assertTrue(predecessor["v3_attempt_01_consumed_no_retry"])
        self.assertEqual(
            {path.name for path in v4.V3_ATTEMPT.iterdir() if path.is_file()},
            {row["name"] for row in predecessor["v3_attempt_files"]},
        )
        self.assertTrue(
            (v4.V3_ATTEMPT / "CHILD_AUTHORIZATION_CONSUMED.json").is_file()
        )
        self.assertTrue((v4.V3_ATTEMPT / "FINAL_REPORT.json").is_file())
        self.assertTrue(v4.V3_GENERATED.is_dir())
        self.assertEqual(list(v4.V3_GENERATED.iterdir()), [])

    def test_v3_final_report_binds_exact_tasklist_only_failure(self) -> None:
        final = json.loads(
            (v4.V3_ATTEMPT / "FINAL_REPORT.json").read_text(encoding="utf-8")
        )
        self.assertEqual(final["status"], "EVALUATION_FAIL_PRESERVED")
        self.assertEqual(final["turns"], [])
        self.assertFalse(final["speaker_playback_completed"])
        preflight = final["heavy_workload_preflight"]
        self.assertFalse(preflight["passed"])
        self.assertEqual(preflight["process_error"], "tasklist_exit_1")
        self.assertEqual(preflight["prohibited_active_processes"], [])
        self.assertEqual(preflight["high_gpu_rows"], [])
        self.assertTrue(preflight["gpu"]["query_succeeded"])

    def test_actual_toolhelp_inventory_satisfies_exact_contract(self) -> None:
        result = v4.win32_toolhelp32_process_inventory()
        self.assertEqual(v4.process_inventory_contract_issues(result), [])
        self.assertTrue(result["succeeded"])
        self.assertGreater(result["process_count"], 0)
        self.assertFalse(result["arbitrary_process_handle_opened"])
        self.assertEqual(result["process_names"], sorted(set(result["process_names"])))
        source = inspect.getsource(v4.win32_toolhelp32_process_inventory)
        self.assertNotIn("tasklist", source.casefold())
        self.assertNotIn("openprocess", source.casefold())

    def test_clean_toolhelp_and_clean_gpu_pass(self) -> None:
        result = v4.heavy_workload_preflight_v4(
            inventory_provider=lambda: self._clean_inventory(
                "system.exe", "python.exe", "explorer.exe"
            ),
            gpu_provider=lambda: self._clean_gpu(7),
        )
        self.assertTrue(result["passed"])
        self.assertFalse(result["tasklist_used"])
        self.assertEqual(result["prohibited_active_processes"], [])
        self.assertEqual(result["process_inventory_issues"], [])

    def test_each_exact_prohibited_process_fails_closed(self) -> None:
        for name in sorted(v4.PROHIBITED_PROCESS_NAMES):
            with self.subTest(name=name):
                result = v4.heavy_workload_preflight_v4(
                    inventory_provider=lambda name=name: self._clean_inventory(
                        "system.exe", name
                    ),
                    gpu_provider=lambda: self._clean_gpu(7),
                )
                self.assertFalse(result["passed"])
                self.assertEqual(result["prohibited_active_processes"], [name])

    def test_similar_but_not_exact_names_do_not_create_false_detection(self) -> None:
        result = v4.heavy_workload_preflight_v4(
            inventory_provider=lambda: self._clean_inventory(
                "myblender.exe", "blender", "ffmpeg-helper.exe", "notffmpeg.exe"
            ),
            gpu_provider=lambda: self._clean_gpu(7),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["prohibited_active_processes"], [])

    def test_every_inventory_proof_field_fails_closed_when_false(self) -> None:
        for key in (
            "succeeded",
            "snapshot_created",
            "first_entry_succeeded",
            "terminal_no_more_files",
            "snapshot_closed",
        ):
            with self.subTest(key=key):
                inventory = self._clean_inventory("system.exe")
                inventory[key] = False
                result = v4.heavy_workload_preflight_v4(
                    inventory_provider=lambda inventory=inventory: inventory,
                    gpu_provider=lambda: self._clean_gpu(7),
                )
                self.assertFalse(result["passed"])
                self.assertTrue(result["process_inventory_issues"])

    def test_inventory_error_arbitrary_handle_or_provider_exception_fails_closed(self) -> None:
        cases = []
        with_error = self._clean_inventory("system.exe")
        with_error["error_type"] = "Process32NextW"
        with_error["win32_error"] = 5
        cases.append(with_error)
        with_handle = self._clean_inventory("system.exe")
        with_handle["arbitrary_process_handle_opened"] = True
        cases.append(with_handle)
        for inventory in cases:
            with self.subTest(inventory=inventory):
                result = v4.heavy_workload_preflight_v4(
                    inventory_provider=lambda inventory=inventory: inventory,
                    gpu_provider=lambda: self._clean_gpu(7),
                )
                self.assertFalse(result["passed"])
        result = v4.heavy_workload_preflight_v4(
            inventory_provider=mock.Mock(side_effect=PermissionError("denied")),
            gpu_provider=lambda: self._clean_gpu(7),
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["process_inventory_exception"], "PermissionError")

    def test_malformed_names_count_order_duplicate_and_keys_fail_closed(self) -> None:
        cases = []
        missing_names = self._clean_inventory("system.exe")
        missing_names["process_names"] = []
        missing_names["process_count"] = 0
        cases.append(missing_names)
        uppercase = self._clean_inventory("system.exe")
        uppercase["process_names"] = ["SYSTEM.EXE"]
        cases.append(uppercase)
        path_name = self._clean_inventory("system.exe")
        path_name["process_names"] = ["c:\\windows\\system.exe"]
        cases.append(path_name)
        duplicate = self._clean_inventory("system.exe")
        duplicate["process_names"] = ["system.exe", "system.exe"]
        duplicate["process_count"] = 2
        cases.append(duplicate)
        wrong_order = self._clean_inventory("a.exe", "b.exe")
        wrong_order["process_names"] = ["b.exe", "a.exe"]
        cases.append(wrong_order)
        wrong_count = self._clean_inventory("system.exe")
        wrong_count["process_count"] = 2
        cases.append(wrong_count)
        extra_key = self._clean_inventory("system.exe")
        extra_key["unexpected"] = True
        cases.append(extra_key)
        for inventory in cases:
            with self.subTest(inventory=inventory):
                result = v4.heavy_workload_preflight_v4(
                    inventory_provider=lambda inventory=inventory: inventory,
                    gpu_provider=lambda: self._clean_gpu(7),
                )
                self.assertFalse(result["passed"])
                self.assertTrue(result["process_inventory_issues"])

    def test_gpu_query_failure_provider_exception_and_over_35_fail_closed(self) -> None:
        inventory = lambda: self._clean_inventory("system.exe")
        query_failure = v4.heavy_workload_preflight_v4(
            inventory_provider=inventory,
            gpu_provider=lambda: {"query_succeeded": False, "rows": []},
        )
        self.assertFalse(query_failure["passed"])
        provider_failure = v4.heavy_workload_preflight_v4(
            inventory_provider=inventory,
            gpu_provider=mock.Mock(side_effect=OSError("gpu unavailable")),
        )
        self.assertFalse(provider_failure["passed"])
        self.assertEqual(provider_failure["gpu_exception"], "OSError")
        high = v4.heavy_workload_preflight_v4(
            inventory_provider=inventory,
            gpu_provider=lambda: self._clean_gpu(35.01),
        )
        self.assertFalse(high["passed"])
        self.assertEqual(len(high["high_gpu_rows"]), 1)
        boundary = v4.heavy_workload_preflight_v4(
            inventory_provider=inventory,
            gpu_provider=lambda: self._clean_gpu(35.0),
        )
        self.assertTrue(boundary["passed"])

    def test_v4_configuration_replaces_only_preflight_and_roots(self) -> None:
        _, effective = self._load_and_configure()
        self.assertIs(retained.heavy_workload_preflight, v4.heavy_workload_preflight_v4)
        self.assertIs(retained.final_run_contract_issues, v3.v3_final_run_contract_issues)
        self.assertEqual(retained.MAX_TOTAL_QWEN_REQUESTS, 36)
        self.assertEqual(len(retained.prepared.EVALUATION_TURNS), 35)
        self.assertEqual(retained.EVIDENCE_ROOT, v4.EVIDENCE_ROOT)
        self.assertEqual(retained.GENERATED_ROOT, v4.GENERATED_ROOT)
        self.assertEqual(
            [row["id"] for row in retained.prepared.EVALUATION_TURNS],
            [row["id"] for row in effective["turns"]],
        )
        self.assertIn(v3.UNATTENDED_AUTHORIZATION_FLAG, retained.REQUIRED_PUBLIC_FLAGS)
        self.assertNotIn(v3.LEGACY_SUPERVISION_FLAG, retained.REQUIRED_PUBLIC_FLAGS)
        acknowledgment = retained.collect_post_playback_owner_acknowledgment({})
        self.assertFalse(acknowledgment["requested"])
        self.assertFalse(acknowledgment["acknowledged"])
        self.assertFalse(acknowledgment["physical_supervision_claimed"])

    def test_only_new_v4_attempt_01_is_permitted(self) -> None:
        v4.validate_attempt_binding([])
        v4.validate_attempt_binding(["--attempt-label", "attempt_01"])
        with self.assertRaises(v4.LongEvaluationV4Error):
            v4.validate_attempt_binding(["--attempt-label", "attempt_02"])
        with self.assertRaises(v4.LongEvaluationV4Error):
            v4.validate_attempt_binding(
                [
                    "--child-run",
                    "--attempt-path",
                    str(v4.EVIDENCE_ROOT / "attempt_02"),
                    "--generated-path",
                    str(v4.GENERATED_ROOT / "attempt_02"),
                ]
            )

    def test_v4_roots_absent_and_v3_roots_remain_consumed(self) -> None:
        self.assertFalse((v4.EVIDENCE_ROOT / v4.ONLY_ATTEMPT_LABEL).exists())
        self.assertFalse((v4.GENERATED_ROOT / v4.ONLY_ATTEMPT_LABEL).exists())
        self.assertTrue(v4.V3_ATTEMPT.exists())
        self.assertTrue(v4.V3_GENERATED.exists())

    def test_unattended_missing_authorization_is_inert(self) -> None:
        with mock.patch.object(retained, "main") as retained_main:
            with self.assertRaises(v3.LongEvaluationV3Error):
                v4.main([v3.UNATTENDED_MARKER])
        retained_main.assert_not_called()

    def test_truthful_command_forwards_no_supervision_claim(self) -> None:
        incoming = [
            v3.UNATTENDED_MARKER,
            "--execute-live",
            "--attempt-label",
            "attempt_01",
            "--confirm-exact-qwen35",
            "--confirm-voluntary-invitation",
            "--confirm-speaker-playback",
            "--confirm-no-active-blender-or-heavy-gpu-workload",
            "--confirm-approved-blackwell-v2-route",
            v3.UNATTENDED_AUTHORIZATION_FLAG,
        ]
        with mock.patch.object(retained, "main", return_value=1) as retained_main:
            result = v4.main(incoming)
        self.assertEqual(result, 1)
        forwarded = retained_main.call_args.args[0]
        self.assertNotIn(v3.UNATTENDED_MARKER, forwarded)
        self.assertNotIn(v3.LEGACY_SUPERVISION_FLAG, forwarded)
        self.assertIn(v3.UNATTENDED_AUTHORIZATION_FLAG, forwarded)

    def test_duplicate_v4_json_key_is_rejected(self) -> None:
        with self.assertRaises(v4.LongEvaluationV4Error):
            json.loads('{"a":1,"a":2}', object_pairs_hook=v4._strict_object)

    def test_outer_result_requires_exact35_and_never_claims_owner_hearing(self) -> None:
        source = Path(v4.__file__).read_text(encoding="utf-8")
        self.assertIn('final.get("owner_post_playback_acknowledged") is False', source)
        self.assertIn('wrapper.get("process_gate_passed") is True', source)
        self.assertIn('len(turns) == 35', source)
        self.assertIn('"physical_owner_supervision_claimed": False', source)
        self.assertIn('"owner_hearing_acknowledged": False', source)


if __name__ == "__main__":
    unittest.main()
