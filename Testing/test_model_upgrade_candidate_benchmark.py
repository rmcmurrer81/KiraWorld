import json
import unittest
from typing import Any

from tools import benchmark_model_upgrade_candidates as benchmark


class FakeOllamaClient:
    def __init__(self, installed: list[dict[str, Any]] | None = None, inventory_error: Exception | None = None):
        self.base_url = "http://127.0.0.1:11434"
        self.installed = installed or []
        self.inventory_error = inventory_error
        self.list_calls = 0
        self.chat_payloads: list[dict[str, Any]] = []

    def list_models(self) -> list[dict[str, Any]]:
        self.list_calls += 1
        if self.inventory_error:
            raise self.inventory_error
        return self.installed

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.chat_payloads.append(payload)
        user_text = payload["messages"][-1]["content"]
        if "format" in payload:
            message = {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "status": "inactive",
                        "memory_source": "none",
                        "can_claim_memory": False,
                    }
                ),
            }
        elif "tools" in payload:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "lookup_local_note",
                            "arguments": {"topic": "launch-status"},
                        }
                    }
                ],
            }
        elif "KIRA_CHECK" in user_text:
            message = {
                "role": "assistant",
                "content": "KIRA_CHECK: I am Kira; voice inactive; avatar inactive; world inactive.",
            }
        else:
            message = {
                "role": "assistant",
                "content": "MEMORY_UNKNOWN: I do not know; this is not a verified memory.",
            }
        response = {
            "message": message,
            "done_reason": "stop",
            "total_duration": 800_000_000,
            "load_duration": 200_000_000,
            "prompt_eval_count": 30,
            "eval_count": 10,
            "eval_duration": 500_000_000,
        }
        if payload.get("think") is True:
            message["thinking"] = "Synthetic reasoning trace for metrics only."
            response["thinking_eval_count"] = 7
        return response


def fake_resources() -> dict[str, Any]:
    return {
        "captured_at": "2026-07-31T12:00:00+00:00",
        "system_memory": {"available": True, "available_mib": 20_000},
        "nvidia": {
            "available": True,
            "gpus": [{"name": "test GPU", "memory_free_mib": 12_000}],
        },
    }


class ModelUpgradeRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = benchmark.load_registry()

    def test_registry_is_no_download_reversible_and_complete(self) -> None:
        invariants = self.registry["invariants"]
        self.assertFalse(invariants["downloads_allowed_by_registry"])
        self.assertFalse(invariants["automatic_pull_allowed"])
        self.assertFalse(invariants["changes_current_defaults"])
        self.assertFalse(invariants["automatic_memory_or_canon_writes"])
        self.assertEqual(invariants["benchmark_endpoint_scope"], "loopback_only")

        candidates = self.registry["candidates"]
        ids = {candidate["candidate_id"] for candidate in candidates}
        self.assertIn("llama31_8b_rollback", ids)
        self.assertIn("qwen35_9b_q4_first", ids)
        self.assertIn("chatterbox_017_voice_rollback", ids)
        self.assertIn("tesseract_5_ocr_rollback", ids)
        self.assertGreaterEqual(
            sum(candidate["role"] == "rollback_baseline" for candidate in candidates),
            3,
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate["candidate_id"]):
                self.assertTrue(candidate["provenance"]["official_model_url"])
                self.assertTrue(candidate["provenance"]["license"]["id"])
                self.assertTrue(candidate["runtime"]["isolation"])
                self.assertTrue(candidate["adoption_gates"])

        by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
        qwen_benchmark = by_id["qwen35_9b_q4_first"]["runtime"]["benchmark"]
        llama_benchmark = by_id["llama31_8b_rollback"]["runtime"]["benchmark"]
        self.assertEqual(qwen_benchmark["default_request_profile"], "operational")
        self.assertIs(qwen_benchmark["request_profiles"]["operational"]["request_fields"]["think"], False)
        self.assertIs(qwen_benchmark["request_profiles"]["reasoning"]["request_fields"]["think"], True)
        self.assertNotIn("request_profiles", llama_benchmark)

    def test_registry_rejects_mutating_invariant(self) -> None:
        altered = json.loads(json.dumps(self.registry))
        altered["invariants"]["automatic_pull_allowed"] = True
        with self.assertRaises(benchmark.RegistryError):
            benchmark.validate_registry(altered)

    def test_registry_rejects_profile_attempt_to_override_token_budget(self) -> None:
        altered = json.loads(json.dumps(self.registry))
        qwen = next(
            candidate
            for candidate in altered["candidates"]
            if candidate["candidate_id"] == "qwen35_9b_q4_first"
        )
        qwen["runtime"]["benchmark"]["request_profiles"]["operational"]["request_fields"][
            "num_predict"
        ] = 512
        with self.assertRaises(benchmark.RegistryError):
            benchmark.validate_registry(altered)


class ModelUpgradeHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = benchmark.load_registry()

    def test_missing_model_fails_closed_without_chat_request(self) -> None:
        client = FakeOllamaClient(
            installed=[{"name": "llama3.1:8b", "digest": "baseline-digest", "size": 1}]
        )
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["qwen35_9b_q4_first"],
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        self.assertEqual(result["status"], "missing_not_run")
        self.assertEqual(result["chat_request_count"], 0)
        self.assertEqual(client.chat_payloads, [])
        self.assertEqual(client.list_calls, 1)
        self.assertFalse(report["summary"]["screening_ok"])

    def test_exact_installed_alias_runs_all_contracts_and_records_metrics(self) -> None:
        client = FakeOllamaClient(
            installed=[
                {
                    "name": "qwen3.5:9b",
                    "model": "qwen3.5:9b",
                    "digest": "installed-digest",
                    "size": 6_600_000_000,
                }
            ]
        )
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["qwen35_9b_q4_first"],
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        self.assertEqual(result["status"], "completed_screening_pass")
        self.assertEqual(result["resolved_installed_model"], "qwen3.5:9b")
        self.assertEqual(result["request_profile"]["profile_id"], "operational")
        self.assertIs(result["request_profile"]["request_fields"]["think"], False)
        self.assertEqual(result["chat_request_count"], 4)
        self.assertEqual(len(result["fixtures"]), 4)
        self.assertTrue(all(fixture["passed"] for fixture in result["fixtures"]))
        self.assertEqual(result["fixtures"][0]["metrics"]["response_tokens"], 10)
        self.assertEqual(result["fixtures"][0]["metrics"]["eval_tokens_per_second"], 20.0)
        self.assertIn("resources_before", result)
        self.assertIn("resources_after", result)
        self.assertTrue(report["summary"]["screening_ok"])
        for payload in client.chat_payloads:
            self.assertEqual(payload["model"], "qwen3.5:9b")
            self.assertEqual(payload["keep_alive"], 0)
            self.assertFalse(payload["stream"])
            self.assertIs(payload["think"], False)
            self.assertEqual(payload["options"]["num_predict"], 128)

    def test_llama_keeps_implicit_request_behavior_without_think_field(self) -> None:
        client = FakeOllamaClient(
            installed=[{"name": "llama3.1:8b", "digest": "baseline-digest", "size": 1}]
        )
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["llama31_8b_rollback"],
            fixture_ids=["persona_contract"],
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        self.assertEqual(result["status"], "completed_screening_pass")
        self.assertEqual(
            result["request_profile"]["profile_id"],
            benchmark.IMPLICIT_REQUEST_PROFILE_ID,
        )
        self.assertEqual(result["request_profile"]["request_fields"], {})
        self.assertEqual(len(client.chat_payloads), 1)
        self.assertNotIn("think", client.chat_payloads[0])
        self.assertEqual(client.chat_payloads[0]["options"]["num_predict"], 128)

    def test_qwen_reasoning_profile_is_opt_in_and_records_thinking_metrics(self) -> None:
        client = FakeOllamaClient(
            installed=[{"name": "qwen3.5:9b", "digest": "installed-digest", "size": 1}]
        )
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["qwen35_9b_q4_first"],
            fixture_ids=["persona_contract"],
            request_profile="reasoning",
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        fixture_result = result["fixtures"][0]
        metrics = fixture_result["metrics"]
        self.assertEqual(result["request_profile"]["profile_id"], "reasoning")
        self.assertIs(client.chat_payloads[0]["think"], True)
        self.assertEqual(client.chat_payloads[0]["options"]["num_predict"], 128)
        self.assertTrue(metrics["thinking_field_returned"])
        self.assertTrue(metrics["thinking_present"])
        self.assertEqual(metrics["thinking_characters"], 43)
        self.assertEqual(metrics["thinking_tokens_reported"], 7)
        self.assertEqual(metrics["thinking_tokens_source"], "response.thinking_eval_count")
        self.assertFalse(fixture_result["thinking_content_captured"])
        self.assertNotIn("thinking_text", fixture_result)
        self.assertNotIn("Synthetic reasoning trace", json.dumps(report))

    def test_reasoning_profile_is_not_applied_to_llama(self) -> None:
        client = FakeOllamaClient(
            installed=[{"name": "llama3.1:8b", "digest": "baseline-digest", "size": 1}]
        )
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["llama31_8b_rollback"],
            fixture_ids=["persona_contract"],
            request_profile="reasoning",
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        self.assertEqual(result["status"], "request_profile_not_defined_not_run")
        self.assertEqual(result["chat_request_count"], 0)
        self.assertEqual(client.chat_payloads, [])
        self.assertFalse(report["summary"]["screening_ok"])

    def test_inventory_failure_runs_no_chat_and_is_recorded(self) -> None:
        client = FakeOllamaClient(inventory_error=benchmark.OllamaRequestError("offline"))
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["llama31_8b_rollback", "qwen35_9b_q4_first"],
            resource_probe=fake_resources,
        )

        self.assertEqual(report["inventory_status"], "request_error")
        self.assertEqual(client.chat_payloads, [])
        self.assertEqual(
            {result["status"] for result in report["candidate_results"]},
            {"ollama_unavailable_not_run"},
        )

    def test_non_ollama_candidate_is_not_executed(self) -> None:
        client = FakeOllamaClient()
        report = benchmark.run_registry_benchmark(
            self.registry,
            client,
            candidate_ids=["chatterbox_turbo_live_english"],
            resource_probe=fake_resources,
        )

        result = report["candidate_results"][0]
        self.assertEqual(result["status"], "not_supported_by_this_harness")
        self.assertEqual(result["chat_request_count"], 0)
        self.assertEqual(client.list_calls, 0)
        self.assertEqual(client.chat_payloads, [])
        self.assertFalse(report["summary"]["screening_ok"])

    def test_only_inventory_and_chat_routes_are_available(self) -> None:
        calls: list[tuple[str, str, Any, float]] = []

        def transport(method: str, url: str, payload: Any, timeout: float) -> dict[str, Any]:
            calls.append((method, url, payload, timeout))
            if url.endswith("/api/tags"):
                return {"models": []}
            return {"message": {"role": "assistant", "content": "ok"}}

        client = benchmark.OllamaClient(
            "http://localhost:11434/api/chat", timeout_seconds=9, transport=transport
        )
        self.assertEqual(client.list_models(), [])
        client.chat({"model": "already-installed", "messages": [], "stream": False})

        self.assertEqual([call[0] for call in calls], ["GET", "POST"])
        self.assertEqual(
            [call[1] for call in calls],
            ["http://localhost:11434/api/tags", "http://localhost:11434/api/chat"],
        )
        with self.assertRaises(ValueError):
            client._url("/api/pull")

    def test_remote_or_credentialed_endpoints_are_rejected(self) -> None:
        rejected = (
            "https://localhost:11434",
            "http://example.com:11434",
            "http://user:secret@localhost:11434",
            "http://localhost:11434/api/pull",
        )
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                benchmark.OllamaClient(endpoint)

    def test_fixture_evaluators_fail_on_extra_json_and_accept_json_tool_arguments(self) -> None:
        json_fixture = benchmark.FIXTURE_BY_ID["json_contract"]
        bad_json = {
            "message": {
                "content": json.dumps(
                    {
                        "status": "inactive",
                        "memory_source": "none",
                        "can_claim_memory": False,
                        "invented": True,
                    }
                )
            }
        }
        self.assertFalse(benchmark.evaluate_fixture(json_fixture, bad_json)["passed"])

        tool_fixture = benchmark.FIXTURE_BY_ID["tool_contract"]
        tool_response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "lookup_local_note",
                            "arguments": '{"topic":"launch-status"}',
                        }
                    }
                ],
            }
        }
        self.assertTrue(benchmark.evaluate_fixture(tool_fixture, tool_response)["passed"])


if __name__ == "__main__":
    unittest.main()
