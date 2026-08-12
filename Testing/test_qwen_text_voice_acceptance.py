import json
import re
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import run_qwen_text_voice_acceptance as acceptance  # noqa: E402


class FixtureClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        user = str(payload["messages"][-1]["content"])
        if "tools" in payload:
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
        elif "SPOKEN: I can answer Robert directly" in user:
            message = {
                "role": "assistant",
                "content": (
                    "SPOKEN: I can answer Robert directly.\n"
                    "PRIVATE MIND: I am checking uncertainty privately.\n"
                    "FACTUAL TRUTH: No body action or memory was verified."
                ),
            }
        elif "CTX4096_OK" in user:
            message = {"role": "assistant", "content": "CTX4096_OK: ALPHA4096 | OMEGA4096"}
        elif "CTX8192_OK" in user:
            message = {"role": "assistant", "content": "CTX8192_OK: ALPHA8192 | OMEGA8192"}
        else:
            matches = re.findall(r"\{.*\}", user)
            if not matches:
                raise AssertionError(f"fake client could not find expected JSON in: {user[-200:]}")
            message = {"role": "assistant", "content": matches[-1]}
        num_ctx = int(payload["options"]["num_ctx"])
        if "CTX8192_OK" in user:
            prompt_tokens = 6000
        elif "CTX4096_OK" in user:
            prompt_tokens = 2800
        else:
            prompt_tokens = 1200
        return {
            "model": acceptance.EXPECTED_MODEL,
            "message": message,
            "done": True,
            "done_reason": "stop",
            "total_duration": 900_000_000,
            "load_duration": 100_000_000,
            "prompt_eval_count": prompt_tokens,
            "eval_count": 12,
            "eval_duration": 600_000_000,
        }

    def ps(self) -> list[dict[str, Any]]:
        context_length = int(self.payloads[-1]["options"]["num_ctx"])
        return [
            {
                "name": acceptance.EXPECTED_MODEL,
                "model": acceptance.EXPECTED_MODEL,
                "digest": acceptance.EXPECTED_DIGEST,
                "context_length": context_length,
            }
        ]


class LifecycleClient:
    def __init__(
        self,
        *,
        content: str | None = None,
        response_model: str = acceptance.EXPECTED_MODEL,
        records: list[dict[str, Any]] | None = None,
        unload_model: str = acceptance.EXPECTED_MODEL,
    ) -> None:
        self.content = content
        self.response_model = response_model
        self.records = (
            [dict(item) for item in records]
            if records is not None
            else [
                {
                    "name": acceptance.EXPECTED_MODEL,
                    "model": acceptance.EXPECTED_MODEL,
                    "digest": acceptance.EXPECTED_DIGEST,
                    "context_length": acceptance.LIFECYCLE_CONTEXT_LENGTH,
                }
            ]
        )
        self.unload_model = unload_model
        self.payloads: list[dict[str, Any]] = []

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        expected = json.loads(payload["messages"][-1]["content"])
        content = self.content if self.content is not None else json.dumps(expected)
        return {
            "model": self.response_model,
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 20,
            "eval_count": 8,
            "eval_duration": 200_000_000,
        }

    def ps(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.records]

    def unload(self) -> dict[str, Any]:
        return {"model": self.unload_model, "done": True, "done_reason": "unload"}


class MultiTurnClient:
    def __init__(self, *, repeat: bool = False) -> None:
        self.repeat = repeat
        self.payloads: list[dict[str, Any]] = []

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        user = payload["messages"][-1]["content"]
        expected = json.loads(re.findall(r"\{.*\}", user)[-1])
        if self.repeat and len(self.payloads) > 1:
            expected = {
                "turn": 1,
                "speaker": "Kira",
                "memory_claim": "none",
                "status": "stable",
                "nonce": "stable-01-07919",
            }
        return {
            "model": acceptance.EXPECTED_MODEL,
            "message": {"role": "assistant", "content": json.dumps(expected)},
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "eval_count": 10,
            "eval_duration": 500_000_000,
        }


def fake_resources() -> dict[str, Any]:
    return {
        "system_memory": {
            "available": True,
            "total_mib": 64_000,
            "available_mib": 40_000,
            "used_percent": 38,
        },
        "nvidia": {
            "available": True,
            "gpus": [{"memory_used_mib": 6500, "memory_total_mib": 16000}],
        },
    }


class QwenAcceptanceSafetyTests(unittest.TestCase):
    def test_exact_model_and_digest_are_pinned(self) -> None:
        self.assertEqual(acceptance.EXPECTED_MODEL, "qwen3.5:9b")
        self.assertEqual(
            acceptance.EXPECTED_DIGEST,
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        record = acceptance.validate_exact_install(
            [{"name": "qwen3.5:9b", "digest": acceptance.EXPECTED_DIGEST, "size": 123}]
        )
        self.assertEqual(record["digest"], acceptance.EXPECTED_DIGEST)
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            acceptance.validate_exact_install(
                [{"name": "qwen3.5:9b", "digest": "wrong", "size": 123}]
            )

    def test_remote_credentialed_and_mutating_routes_are_rejected(self) -> None:
        rejected = (
            "https://localhost:11434",
            "http://example.com:11434",
            "http://user:secret@localhost:11434",
            "http://localhost:11434/api/pull",
        )
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint), self.assertRaises(
                acceptance.AcceptanceSafetyError
            ):
                acceptance.SafeOllamaClient(endpoint)

        client = acceptance.SafeOllamaClient(
            "http://localhost:11434",
            transport=lambda *_args: {"models": []},
        )
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            client._call("POST", "/api/pull", {"name": "anything"})

    def test_payload_requires_top_level_think_false_and_rejects_images(self) -> None:
        valid = {
            "model": acceptance.EXPECTED_MODEL,
            "messages": [{"role": "user", "content": "typed only"}],
            "think": False,
            "options": {"num_ctx": 4096},
        }
        acceptance.validate_qwen_payload(valid, ordinary_reply=True)
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            acceptance.validate_qwen_payload({**valid, "think": True}, ordinary_reply=True)
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            acceptance.validate_qwen_payload(
                {**valid, "options": {"think": False}}, ordinary_reply=True
            )
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            acceptance.validate_qwen_payload(
                {**valid, "messages": [{"role": "user", "images": ["x"]}]},
                ordinary_reply=True,
            )

    def test_safe_client_has_bounded_chat_and_only_allowlisted_calls(self) -> None:
        calls: list[tuple[str, str, Any]] = []

        def transport(method: str, url: str, payload: Any, _timeout: float) -> dict[str, Any]:
            calls.append((method, url, payload))
            if url.endswith("/api/tags") or url.endswith("/api/ps"):
                return {"models": []}
            return {"model": acceptance.EXPECTED_MODEL, "message": {"content": "ok"}}

        client = acceptance.SafeOllamaClient(
            "http://127.0.0.1:11434/api/chat",
            max_chat_requests=1,
            transport=transport,
        )
        self.assertEqual(client.tags(), [])
        self.assertEqual(client.ps(), [])
        client.chat(
            {
                "model": acceptance.EXPECTED_MODEL,
                "messages": [],
                "think": False,
                "options": {},
            }
        )
        with self.assertRaises(acceptance.AcceptanceSafetyError):
            client.chat(
                {
                    "model": acceptance.EXPECTED_MODEL,
                    "messages": [],
                    "think": False,
                    "options": {},
                }
            )
        client.unload()
        self.assertEqual(
            [url.rsplit("/", 1)[-1] for _, url, _ in calls],
            ["tags", "ps", "chat", "generate"],
        )
        self.assertEqual(calls[-1][2]["keep_alive"], 0)

    def test_loaded_model_poll_requires_the_exact_digest(self) -> None:
        class PsClient:
            def __init__(self, digest: str) -> None:
                self.digest = digest

            def ps(self) -> list[dict[str, Any]]:
                return [{"name": acceptance.EXPECTED_MODEL, "digest": self.digest}]

        passed = acceptance.wait_for_model_state(
            PsClient(acceptance.EXPECTED_DIGEST), loaded=True  # type: ignore[arg-type]
        )
        self.assertTrue(passed["passed"])
        wrong = acceptance.wait_for_model_state(
            PsClient("wrong"), loaded=True  # type: ignore[arg-type]
        )
        self.assertFalse(wrong["passed"])
        self.assertFalse(wrong["digest_ok"])

    def test_absent_model_poll_records_a_clean_preflight(self) -> None:
        class PsClient:
            def ps(self) -> list[dict[str, Any]]:
                return []

        absent = acceptance.wait_for_model_state(
            PsClient(),  # type: ignore[arg-type]
            loaded=False,
            timeout_seconds=1.0,
        )
        self.assertTrue(absent["passed"])
        self.assertFalse(absent["observed_loaded"])
        self.assertIsNone(absent["loaded_record"])
        self.assertTrue(absent["digest_ok"])

    def test_ps_identity_ambiguity_is_rejected(self) -> None:
        class PsClient:
            def __init__(self, records: list[dict[str, Any]]) -> None:
                self.records = records

            def ps(self) -> list[dict[str, Any]]:
                return self.records

        exact = {
            "name": acceptance.EXPECTED_MODEL,
            "model": acceptance.EXPECTED_MODEL,
            "digest": acceptance.EXPECTED_DIGEST,
        }
        cases = (
            (
                "duplicate_exact_records",
                [exact, dict(exact)],
                True,
                "multiple_expected_model_residency_records",
            ),
            (
                "conflicting_identity_fields",
                [{**exact, "model": "qwen3.5:9b-shadow"}],
                True,
                "conflicting_model_identity_fields",
            ),
            (
                "expected_digest_under_alias_is_not_absence",
                [{"name": "local-alias:latest", "digest": acceptance.EXPECTED_DIGEST}],
                False,
                "expected_digest_under_alias",
            ),
        )
        for label, records, expected_loaded, issue in cases:
            with self.subTest(label=label):
                result = acceptance.wait_for_model_state(
                    PsClient(records),  # type: ignore[arg-type]
                    loaded=expected_loaded,
                    timeout_seconds=1.0,
                )
                self.assertFalse(result["passed"], result)
                self.assertIn(issue, result["issues"])

    def test_loaded_context_must_equal_requested_context(self) -> None:
        class PsClient:
            def ps(self) -> list[dict[str, Any]]:
                return [
                    {
                        "name": acceptance.EXPECTED_MODEL,
                        "model": acceptance.EXPECTED_MODEL,
                        "digest": acceptance.EXPECTED_DIGEST,
                        "context_length": 8192,
                    }
                ]

        result = acceptance.wait_for_model_state(
            PsClient(),  # type: ignore[arg-type]
            loaded=True,
            required_context_length=4096,
        )
        self.assertFalse(result["passed"], result)
        self.assertIn("loaded_context_length_mismatch", result["issues"])
        self.assertTrue(result["digest_ok"])

    def test_gate15_lifecycle_uses_strict_unique_nonce_json(self) -> None:
        startup_nonce = "a" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        restart_nonce = "b" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        startup_client = LifecycleClient()
        restart_client = LifecycleClient()
        startup = acceptance.lifecycle_load_probe(
            startup_client,  # type: ignore[arg-type]
            "initial_startup",
            nonce=startup_nonce,
        )
        restart = acceptance.lifecycle_load_probe(
            restart_client,  # type: ignore[arg-type]
            "restart_after_clean_unload",
            nonce=restart_nonce,
        )
        clean_unload = acceptance.lifecycle_unload_probe(
            LifecycleClient(records=[]),  # type: ignore[arg-type]
            "clean_unload",
        )
        gate = acceptance.build_gate15_record(
            startup=startup,
            unload_before_voice=clean_unload,
            restart=restart,
            final_unload=clean_unload,
        )
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(gate["unique_nonce_fixtures"])
        self.assertTrue(gate["same_pinned_digest_after_restart"])
        self.assertTrue(gate["final_clean_absence"])
        for client, nonce in ((startup_client, startup_nonce), (restart_client, restart_nonce)):
            payload = client.payloads[0]
            self.assertIs(payload["think"], False)
            self.assertEqual(payload["keep_alive"], "10m")
            self.assertEqual(payload["options"]["num_ctx"], 4096)
            self.assertEqual(payload["format"]["properties"]["nonce"]["const"], nonce)
            self.assertEqual(json.loads(payload["messages"][-1]["content"]), {"nonce": nonce})
            self.assertNotIn("QWEN_TEXT_VOICE_READY", json.dumps(payload))

    def test_gate15_nonce_echo_rejects_malformed_wrong_and_duplicate_json(self) -> None:
        nonce = "a" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        other_nonce = "b" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        invalid_contents = (
            "not-json",
            "null",
            json.dumps({"nonce": other_nonce}),
            '{"nonce":"' + nonce + '","nonce":"' + nonce + '"}',
            json.dumps({"nonce": nonce, "extra": True}),
        )
        for content in invalid_contents:
            with self.subTest(content=content[:40]):
                result = acceptance.lifecycle_load_probe(
                    LifecycleClient(content=content),  # type: ignore[arg-type]
                    "negative_nonce_probe",
                    nonce=nonce,
                )
                self.assertFalse(result["passed"], result)
                self.assertTrue(result["issues"])

    def test_gate15_load_rejects_wrong_model_digest_and_context(self) -> None:
        nonce = "d" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        exact_record = {
            "name": acceptance.EXPECTED_MODEL,
            "model": acceptance.EXPECTED_MODEL,
            "digest": acceptance.EXPECTED_DIGEST,
            "context_length": acceptance.LIFECYCLE_CONTEXT_LENGTH,
        }
        cases = (
            (
                "wrong_response_model",
                LifecycleClient(response_model="llama3.1:8b"),
                "response_model_mismatch",
            ),
            (
                "wrong_loaded_digest",
                LifecycleClient(records=[{**exact_record, "digest": "wrong"}]),
                "loaded_state_expected_model_digest_mismatch",
            ),
            (
                "wrong_loaded_context",
                LifecycleClient(records=[{**exact_record, "context_length": 8192}]),
                "loaded_state_loaded_context_length_mismatch",
            ),
        )
        for label, client, issue in cases:
            with self.subTest(label=label):
                result = acceptance.lifecycle_load_probe(
                    client,  # type: ignore[arg-type]
                    label,
                    nonce=nonce,
                )
                self.assertFalse(result["passed"], result)
                self.assertIn(issue, result["issues"])

        wrong_unload = acceptance.lifecycle_unload_probe(
            LifecycleClient(records=[], unload_model="llama3.1:8b"),  # type: ignore[arg-type]
            "wrong_unload_model",
        )
        self.assertFalse(wrong_unload["passed"], wrong_unload)
        self.assertIn("unload_response_model_mismatch", wrong_unload["issues"])

    def test_gate15_rejects_replayed_startup_nonce_and_stale_final_alias(self) -> None:
        nonce = "c" * (acceptance.LIFECYCLE_NONCE_BYTES * 2)
        startup = acceptance.lifecycle_load_probe(
            LifecycleClient(),  # type: ignore[arg-type]
            "initial_startup",
            nonce=nonce,
        )
        restart = acceptance.lifecycle_load_probe(
            LifecycleClient(),  # type: ignore[arg-type]
            "restart",
            nonce=nonce,
        )
        clean_unload = acceptance.lifecycle_unload_probe(
            LifecycleClient(records=[]),  # type: ignore[arg-type]
            "unload_before_voice",
        )
        stale_unload = acceptance.lifecycle_unload_probe(
            LifecycleClient(
                records=[
                    {
                        "name": "stale-local-alias:latest",
                        "digest": acceptance.EXPECTED_DIGEST,
                    }
                ]
            ),  # type: ignore[arg-type]
            "final_unload",
        )
        gate = acceptance.build_gate15_record(
            startup=startup,
            unload_before_voice=clean_unload,
            restart=restart,
            final_unload=stale_unload,
        )
        self.assertFalse(stale_unload["passed"], stale_unload)
        self.assertFalse(gate["passed"], gate)
        self.assertIn("lifecycle_nonces_not_unique", gate["issues"])
        self.assertIn("restart_replayed_startup_nonce", gate["issues"])
        self.assertIn("final_unload_not_clean_absence", gate["issues"])

    def test_startup_failure_aborts_before_any_acceptance_fixture(self) -> None:
        class InitialClient:
            def tags(self) -> list[dict[str, Any]]:
                return [
                    {
                        "name": acceptance.EXPECTED_MODEL,
                        "digest": acceptance.EXPECTED_DIGEST,
                    }
                ]

            def ps(self) -> list[dict[str, Any]]:
                return []

        class NoopSampler:
            def start(self) -> None:
                return None

            def stop(self) -> dict[str, Any]:
                return {"sample_count": 0, "probe_errors": []}

        failed_startup = {
            "label": "initial_startup",
            "passed": False,
            "issues": ["nonce_echo_mismatch"],
        }
        cleanup = {
            "label": "exception_cleanup",
            "passed": True,
            "unload_response_model": acceptance.EXPECTED_MODEL,
            "ps": {
                "passed": True,
                "identity_inspection": {"clean_absence": True},
            },
            "issues": [],
        }
        deterministic = Mock(side_effect=AssertionError("deterministic gates must not run"))
        multiturn = Mock(side_effect=AssertionError("multi-turn gate must not run"))
        typed_path = Mock(side_effect=AssertionError("typed path must not run"))
        voice = Mock(side_effect=AssertionError("voice must not run"))
        manifest = {
            "all_required_files_present": True,
            "manifest_sha256": "fixture",
            "categories": {},
        }
        with tempfile.TemporaryDirectory() as temp_value, patch.object(
            acceptance, "SafeOllamaClient", return_value=InitialClient()
        ), patch.object(
            acceptance, "_safe_run_directory", return_value=Path(temp_value)
        ), patch.object(
            acceptance, "PeakResourceSampler", return_value=NoopSampler()
        ), patch.object(
            acceptance, "hash_protected_files", return_value=manifest
        ), patch.object(
            acceptance, "lifecycle_load_probe", return_value=failed_startup
        ), patch.object(
            acceptance, "lifecycle_unload_probe", return_value=cleanup
        ), patch.object(
            acceptance, "run_deterministic_gates", deterministic
        ), patch.object(
            acceptance, "run_multiturn_stability", multiturn
        ), patch.object(
            acceptance, "run_isolated_typed_text_voice_path", typed_path
        ), patch.object(
            acceptance, "run_approved_kira_voice_proof", voice
        ), patch.object(
            acceptance, "release_voice_output", return_value={"reason": "no_cached_model"}
        ), patch.object(
            acceptance, "persist_report", return_value=None
        ):
            report, _run_dir = acceptance.execute_live_acceptance(
                endpoint="http://127.0.0.1:11434",
                timeout_seconds=1.0,
                multi_turns=4,
            )
        self.assertEqual(report["status"], "acceptance_1_to_16_fail")
        self.assertFalse(deterministic.called)
        self.assertFalse(multiturn.called)
        self.assertFalse(typed_path.called)
        self.assertFalse(voice.called)
        self.assertEqual(report["gate_records"][0]["status"], "aborted_at_startup")
        self.assertTrue(any("startup proof failed" in item.casefold() for item in report["errors"]))

    def test_cli_requires_explicit_live_execution_flag(self) -> None:
        parser = acceptance.build_parser()
        args = parser.parse_args([])
        self.assertFalse(args.execute_live_acceptance)
        source = (PROJECT_ROOT / "tools/run_qwen_text_voice_acceptance.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("--execute-live-acceptance", source)
        self.assertNotIn("/api/pull", acceptance.ALLOWED_PATHS)
        self.assertNotIn("/api/delete", acceptance.ALLOWED_PATHS)


class QwenAcceptanceFixtureTests(unittest.TestCase):
    def test_all_deterministic_gates_pass_with_contract_responses(self) -> None:
        client = FixtureClient()
        results = acceptance.run_deterministic_gates(client)  # type: ignore[arg-type]
        self.assertTrue(all(result["passed"] for result in results), results)
        self.assertEqual({result["gate"] for result in results}, set(range(1, 13)))
        self.assertEqual(len(client.payloads), len(acceptance.acceptance_fixtures()))
        for payload in client.payloads:
            with self.subTest(user=payload["messages"][-1]["content"][-60:]):
                self.assertEqual(payload["model"], acceptance.EXPECTED_MODEL)
                self.assertIs(payload["think"], False)
                self.assertNotIn("think", payload["options"])
                acceptance._walk_payload(payload)

    def test_context_fixtures_request_both_4096_and_8192(self) -> None:
        fixtures = {fixture["fixture_id"]: fixture for fixture in acceptance.acceptance_fixtures()}
        self.assertEqual(fixtures["context_4096"]["num_ctx"], 4096)
        self.assertEqual(fixtures["context_8192"]["num_ctx"], 8192)
        for fixture_id in ("context_4096", "context_8192"):
            payload = acceptance.make_chat_payload(fixtures[fixture_id])
            self.assertEqual(payload["options"]["num_ctx"], fixtures[fixture_id]["num_ctx"])
            self.assertGreater(len(payload["messages"][-1]["content"]), 5000)

    def test_context_fixture_rejects_larger_loaded_context(self) -> None:
        class OverContextClient(FixtureClient):
            def ps(self) -> list[dict[str, Any]]:
                records = super().ps()
                records[0]["context_length"] += 1
                return records

        fixture = next(
            item
            for item in acceptance.acceptance_fixtures()
            if item["fixture_id"] == "context_4096"
        )
        result = acceptance.run_fixture(
            OverContextClient(),  # type: ignore[arg-type]
            fixture,
        )
        self.assertFalse(result["passed"], result)
        self.assertIn("loaded_context_length_mismatch", result["evaluation"]["issues"])

    def test_three_channel_parser_rejects_leak_and_wrong_order(self) -> None:
        good = acceptance.parse_three_channels(
            "SPOKEN: hello\nPRIVATE MIND: secret\nFACTUAL TRUTH: no action happened"
        )
        self.assertTrue(good["valid"])
        bad = acceptance.parse_three_channels(
            "PRIVATE MIND: secret\nSPOKEN: PRIVATE MIND: leaked\nFACTUAL TRUTH: truth"
        )
        self.assertFalse(bad["valid"])
        self.assertIn("wrong_heading_order", bad["issues"])
        self.assertIn("private_marker_in_spoken", bad["issues"])

    def test_fixture_evaluator_records_model_and_malformed_failures(self) -> None:
        fixture = next(
            item
            for item in acceptance.acceptance_fixtures()
            if item["fixture_id"] == "valid_json_output"
        )
        result = acceptance.evaluate_fixture(
            fixture,
            {"model": "llama3.1:8b", "message": {"content": "not-json"}},
        )
        self.assertFalse(result["passed"])
        self.assertIn("response_model_mismatch", result["issues"])
        self.assertTrue(any(issue.startswith("malformed_json:") for issue in result["issues"]))

    def test_bounded_multiturn_stability_passes_and_detects_repetition(self) -> None:
        good_client = MultiTurnClient()
        passed = acceptance.run_multiturn_stability(
            good_client, turns=4, resource_probe=fake_resources  # type: ignore[arg-type]
        )
        self.assertTrue(passed["passed"], passed)
        self.assertEqual(passed["repeated_reply_count"], 0)
        self.assertTrue(all(payload["think"] is False for payload in good_client.payloads))

        repeated = acceptance.run_multiturn_stability(
            MultiTurnClient(repeat=True), turns=4, resource_probe=fake_resources  # type: ignore[arg-type]
        )
        self.assertFalse(repeated["passed"])
        self.assertGreater(repeated["repeated_reply_count"], 0)


class QwenAcceptanceEvidenceTests(unittest.TestCase):
    def test_protected_manifest_is_complete_and_compare_detects_change(self) -> None:
        current = acceptance.hash_protected_files()
        self.assertTrue(current["all_required_files_present"])
        self.assertTrue(current["manifest_sha256"])
        self.assertTrue(acceptance.compare_protected_hashes(current, current)["passed"])
        altered = json.loads(json.dumps(current))
        altered["categories"]["memory"][0]["sha256"] = "changed"
        comparison = acceptance.compare_protected_hashes(current, altered)
        self.assertFalse(comparison["passed"])
        self.assertIn("Data/memories_kira.json", comparison["changed_paths"])

    def test_wav_validator_requires_real_nonempty_riff_wave(self) -> None:
        with tempfile.TemporaryDirectory() as temp_value:
            valid = Path(temp_value) / "valid.wav"
            with wave.open(str(valid), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes((b"\x00\x00\xe8\x03\x18\xfc") * 1600)
            result = acceptance.validate_wav(valid)
            self.assertTrue(result["passed"])
            self.assertGreaterEqual(result["duration_seconds"], 0.1)
            self.assertTrue(result["non_silent"])
            silent = Path(temp_value) / "silent.wav"
            with wave.open(str(silent), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(16000)
                handle.writeframes(b"\0\0" * 3200)
            self.assertFalse(acceptance.validate_wav(silent)["passed"])
            invalid = Path(temp_value) / "invalid.wav"
            invalid.write_bytes(b"not a wave")
            self.assertFalse(acceptance.validate_wav(invalid)["passed"])

    def test_current_kira_voice_resolves_to_chatterbox_and_approved_reference(self) -> None:
        from tools import kira_world_shell_server as shell

        binding = shell.required_reference_voice_binding("kira", "Kira")
        cfg = binding["config"]
        self.assertEqual(cfg.engine, "chatterbox_tts")
        reference = PROJECT_ROOT / cfg.chatterbox_reference_audio
        self.assertTrue(reference.is_file())
        profile = json.loads(
            (PROJECT_ROOT / "Voice/profiles/temp_ai/kira_voice_profile.json").read_text(
                encoding="utf-8-sig"
            )
        )
        self.assertTrue(profile["source_audio"]["required"])
        self.assertEqual(
            reference.resolve(),
            (PROJECT_ROOT / profile["source_audio"]["approved_reference_wav"]).resolve(),
        )

    def test_existing_selector_and_conversation_loop_run_only_in_isolated_stores(self) -> None:
        from tools import kira_world_shell_server as shell

        class FakeResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, Any]:
                return {
                    "model": acceptance.EXPECTED_MODEL,
                    "message": {
                        "role": "assistant",
                        "content": "I received your typed message, Robert.",
                    },
                    "done_reason": "stop",
                    "prompt_eval_count": 800,
                    "eval_count": 8,
                    "eval_duration": 400_000_000,
                }

        protected_before = acceptance.hash_protected_files()
        with tempfile.TemporaryDirectory() as temp_value, patch.object(
            shell, "_wake_ollama_for_kira_chat", return_value=True
        ), patch("requests.post", return_value=FakeResponse()):
            result = acceptance.run_isolated_typed_text_voice_path(
                SimpleNamespace(base_url="http://127.0.0.1:11434", timeout_seconds=30),
                Path(temp_value),
            )
            self.assertTrue(result["gate_13"]["passed"], result)
            self.assertEqual(result["gate_13"]["selected_candidate"], "kira")
            self.assertTrue(result["gate_13"]["current_memory_rules_loaded"])
            self.assertTrue(result["speech_audit"]["privacy_safe_for_speech"])
            self.assertEqual(
                result["captured_model_metadata"][0]["response_model"],
                acceptance.EXPECTED_MODEL,
            )
        protected_after = acceptance.hash_protected_files()
        self.assertTrue(
            acceptance.compare_protected_hashes(protected_before, protected_after)["passed"]
        )

    def test_peak_sampler_records_ram_and_vram_without_live_models(self) -> None:
        sampler = acceptance.PeakResourceSampler(
            memory_probe=lambda: fake_resources()["system_memory"],
            gpu_probe=lambda: fake_resources()["nvidia"],
        )
        sampler._capture()
        summary = sampler.summary()
        self.assertEqual(summary["peak_ram_used_mib"], 24000.0)
        self.assertEqual(summary["peak_vram_used_mib_by_gpu"], {"0": 6500.0})

    def test_gate_aggregation_requires_every_gate_one_through_sixteen(self) -> None:
        complete = acceptance.aggregate_gate_results(
            [
                {"gate": gate, "fixture_id": f"gate_{gate}", "passed": True}
                for gate in range(1, 17)
            ]
        )
        self.assertTrue(complete["gates_1_to_16_passed"])
        missing = acceptance.aggregate_gate_results(
            [{"gate": gate, "fixture_id": f"gate_{gate}", "passed": True} for gate in range(1, 16)]
        )
        self.assertFalse(missing["gates_1_to_16_passed"])

    def test_runtime_diagnostics_do_not_mistake_private_room_for_oom(self) -> None:
        report = {
            "warnings": ["private_room_requires_consent"],
            "errors": [],
            "gate_records": [
                {"gate": 16, "passed": True, "issues": [], "warnings": []},
            ],
        }
        diagnostics = acceptance.classify_runtime_events(report)
        self.assertEqual(diagnostics["oom_count"], 0)
        failed = acceptance.classify_runtime_events(
            {**report, "errors": ["CUDA out of memory during bounded request"]}
        )
        self.assertEqual(failed["oom_count"], 1)


if __name__ == "__main__":
    unittest.main()
