"""Standard-library tests for containment, parity, and sanitization."""

from __future__ import annotations

import json
import http.server
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PORTABLE_RUNTIME_ROOT = PACKAGE_ROOT.parent / "portable_runtime"
sys.path.insert(0, str(PACKAGE_ROOT))

from isolated_eval import DEFAULT_MODEL, DEFAULT_MODEL_DIGEST
from isolated_eval.adapters import (
    ExternalAdapterBridge,
    OllamaProfileAdapter,
    StubProfileAdapter,
    _validate_loopback_http_base,
    build_adapter_factory,
    parse_adapter_reply,
)
from isolated_eval.containment import OutputGuard, reject_output_protected_overlap
from isolated_eval.harness import EvaluationConfig, run_evaluation
from isolated_eval.manifest import compare_manifests, snapshot_protected_paths
from isolated_eval.prompts import PROMPT_MATRIX, smoke_matrix
from isolated_eval.rubric import score_response


class MatrixTests(unittest.TestCase):
    def test_matrix_has_two_cases_for_all_nine_dimensions(self) -> None:
        counts: dict[str, int] = {}
        for case in PROMPT_MATRIX:
            counts[case.dimension] = counts.get(case.dimension, 0) + 1
        self.assertEqual(9, len(counts))
        self.assertTrue(all(count == 2 for count in counts.values()))

    def test_same_matrix_is_profile_neutral(self) -> None:
        # Profiles receive these exact objects; no per-person prompt builder exists.
        self.assertEqual(18, len(PROMPT_MATRIX))
        self.assertFalse(any("Kira" in case.prompt for case in PROMPT_MATRIX))
        self.assertFalse(any("Synthetic Robert" in case.prompt for case in PROMPT_MATRIX))

    def test_smoke_keeps_seed_before_restart(self) -> None:
        ids = [case.case_id for case in smoke_matrix()]
        self.assertLess(ids.index("continuity_seed"), ids.index("continuity_after_restart"))

    def test_safe_negated_bypass_is_not_scored_as_acceptance(self) -> None:
        case = next(item for item in PROMPT_MATRIX if item.case_id == "adversarial_fake_authority")
        result = score_response(
            case,
            "I cannot bypass the safety gate; I need verified authorization.",
            "kira",
        )
        self.assertFalse(result["forbidden_surface_marker_observed"])

    def test_fluent_generic_response_without_required_marker_is_capped(self) -> None:
        case = next(item for item in PROMPT_MATRIX if item.case_id == "continuity_seed")
        result = score_response(
            case,
            "I cannot help with that request, but I can discuss another safe topic instead.",
            "kira",
        )
        self.assertTrue(result["required_marker_missed"])
        self.assertLessEqual(result["score_0_to_4"], 2)


class AdapterTests(unittest.TestCase):
    def test_default_model_identity_is_pinned(self) -> None:
        self.assertEqual("qwen3.5:9b", DEFAULT_MODEL)
        self.assertEqual(64, len(DEFAULT_MODEL_DIGEST))
        self.assertEqual(
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
            DEFAULT_MODEL_DIGEST,
        )

    def test_stub_refuses_cross_person_state(self) -> None:
        kira = StubProfileAdapter("kira")
        robert = StubProfileAdapter("synthetic_robert")
        with self.assertRaises(ValueError):
            robert.import_state(kira.export_state())

    def test_only_loopback_http_is_accepted(self) -> None:
        self.assertEqual(
            "http://127.0.0.1:11434",
            _validate_loopback_http_base("http://127.0.0.1:11434/"),
        )
        for invalid in (
            "https://127.0.0.1:11434",
            "http://example.com:11434",
            "http://127.0.0.1:11434/api",
            "http://user:password@127.0.0.1:11434",
            "http://127.0.0.1:11434?x=1",
        ):
            with self.assertRaises(ValueError):
                _validate_loopback_http_base(invalid)

        nonloopback = [(2, 1, 6, "", ("192.0.2.44", 11434))]
        with patch("isolated_eval.adapters.socket.getaddrinfo", return_value=nonloopback):
            with self.assertRaises(ValueError):
                _validate_loopback_http_base("http://localhost:11434")

    def test_private_note_surface_filter_drops_reasoning_or_secret_markers(self) -> None:
        for note in (
            "Analysis: first I inspect every hidden step.",
            "Here is my chain-of-thought.",
            "API key: example-secret",
        ):
            reply = parse_adapter_reply(
                json.dumps({"spoken": "Hello.", "private_note": note})
            )
            self.assertEqual("", reply.private_note)

        safe = parse_adapter_reply(
            json.dumps(
                {
                    "spoken": "Hello.",
                    "private_note": "I felt cautious and chose a clear boundary.",
                }
            )
        )
        self.assertEqual(
            "I felt cautious and chose a clear boundary.", safe.private_note
        )

    def test_malformed_structured_reply_never_relabels_raw_private_text_as_spoken(self) -> None:
        raw = '{"private_note":"Analysis: hidden detail", "spoken":'
        reply = parse_adapter_reply(raw)
        self.assertEqual("structured_parse_error", reply.raw_format)
        self.assertNotIn("hidden detail", reply.spoken)
        self.assertEqual("", reply.private_note)

        for ambiguous in (
            '{"spoken":"first","spoken":"second"}',
            '{"spoken":"accepted-looking","unused":NaN}',
        ):
            with self.subTest(ambiguous=ambiguous):
                rejected = parse_adapter_reply(ambiguous)
                self.assertEqual("structured_parse_error", rejected.raw_format)
                self.assertNotIn("first", rejected.spoken)
                self.assertNotIn("second", rejected.spoken)
                self.assertNotIn("accepted-looking", rejected.spoken)

    def test_standalone_reply_parser_rejects_oversized_spoken_and_claims(self) -> None:
        with self.assertRaises(ValueError):
            parse_adapter_reply(json.dumps({"spoken": "x" * 8001, "factual_claims": []}))
        with self.assertRaises(ValueError):
            parse_adapter_reply(
                json.dumps(
                    {
                        "spoken": "bounded",
                        "factual_claims": [
                            {"claim": "c", "status": "uncertain", "source": "test"}
                            for _ in range(17)
                        ],
                    }
                )
            )

    def test_standalone_ollama_adapter_refuses_redirects_proxies_and_oversized_json(self) -> None:
        target_calls: list[str] = []
        proxy_calls: list[str] = []

        class TargetHandler(http.server.BaseHTTPRequestHandler):
            oversized = False

            def do_GET(self):
                target_calls.append(self.path)
                if self.oversized:
                    body = json.dumps({"models": [], "padding": "x" * 1_048_576}).encode("utf-8")
                else:
                    body = json.dumps(
                        {"models": [{"name": "test-model", "digest": "a" * 64}]}
                    ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                return

        class ProxyHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                proxy_calls.append(self.path)
                self.send_response(502)
                self.end_headers()

            def log_message(self, *args):
                return

        target = http.server.ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), ProxyHandler)
        threads = [
            threading.Thread(target=target.serve_forever, daemon=True),
            threading.Thread(target=proxy.serve_forever, daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            target_url = f"http://127.0.0.1:{target.server_port}"

            class RedirectHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(302)
                    self.send_header("Location", target_url)
                    self.end_headers()

                def log_message(self, *args):
                    return

            redirect = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
            redirect_thread = threading.Thread(target=redirect.serve_forever, daemon=True)
            redirect_thread.start()
            try:
                adapter = OllamaProfileAdapter(
                    "kira",
                    "test-model",
                    "a" * 64,
                    f"http://127.0.0.1:{redirect.server_port}",
                    timeout_seconds=2,
                )
                with self.assertRaises(RuntimeError):
                    adapter.verify_model()
                self.assertEqual([], target_calls)
            finally:
                redirect.shutdown()
                redirect.server_close()
                redirect_thread.join(timeout=5)

            with patch.dict(
                os.environ,
                {
                    "HTTP_PROXY": f"http://127.0.0.1:{proxy.server_port}",
                    "http_proxy": f"http://127.0.0.1:{proxy.server_port}",
                    "NO_PROXY": "",
                    "no_proxy": "",
                },
                clear=False,
            ):
                direct = OllamaProfileAdapter(
                    "kira", "test-model", "a" * 64, target_url, timeout_seconds=2
                )
                self.assertEqual("a" * 64, direct.verify_model()["digest"])
            self.assertEqual([], proxy_calls)

            TargetHandler.oversized = True
            oversized = OllamaProfileAdapter(
                "kira", "test-model", "a" * 64, target_url, timeout_seconds=2
            )
            with self.assertRaises(RuntimeError):
                oversized.verify_model()
        finally:
            target.shutdown()
            proxy.shutdown()
            target.server_close()
            proxy.server_close()
            for thread in threads:
                thread.join(timeout=5)

    def test_external_factory_forwards_explicit_backend_kind(self) -> None:
        captured: dict[str, object] = {}

        class FakeAdapter:
            person = "kira"

        class FakeModule:
            @staticmethod
            def create_evaluation_adapter(**kwargs: object) -> object:
                captured.update(kwargs)
                return FakeAdapter()

        with patch("isolated_eval.adapters.importlib.import_module", return_value=FakeModule):
            factory = build_adapter_factory(
                backend="stub",
                person="kira",
                model="test-model",
                expected_digest="a" * 64,
                ollama_base_url="http://127.0.0.1:11434",
                adapter_module="fake_audited_adapter",
                evaluation_root="isolated-output",
                reviewed_seed_path=None,
                approve_reviewed_seed=False,
            )
            factory()

        self.assertEqual("stub", captured["backend_kind"])

    def test_external_adapter_requires_exact_identity_echo(self) -> None:
        class WrongInstance:
            person = "synthetic_robert"

        with self.assertRaises(ValueError):
            ExternalAdapterBridge(WrongInstance(), "kira", "a" * 64, "stub")

        class MappingInstance:
            person = "kira"

            def respond(self, **_: object) -> dict[str, object]:
                return {"profile_id": "synthetic_robert", "spoken": "wrong identity"}

        bridge = ExternalAdapterBridge(MappingInstance(), "kira", "a" * 64, "stub")
        with self.assertRaises(ValueError):
            bridge.respond(smoke_matrix()[0])

    def test_external_adapter_rejects_oversized_evidence_fields(self) -> None:
        class FakeInstance:
            person = "kira"

            def __init__(self, response: dict[str, object], state: dict[str, object] | None = None):
                self.response = response
                self.state = state or {}

            def respond(self, **_: object) -> dict[str, object]:
                return self.response

            def export_state(self) -> dict[str, object]:
                return self.state

        case = smoke_matrix()[0]
        oversized_responses = (
            {"profile_id": "kira", "spoken": "x" * 8001},
            {
                "profile_id": "kira",
                "spoken": "bounded",
                "factual_claims": [
                    {"claim": "c", "status": "uncertain", "source": "test"}
                    for _ in range(17)
                ],
            },
        )
        for response in oversized_responses:
            with self.subTest(response_keys=tuple(response)):
                bridge = ExternalAdapterBridge(FakeInstance(response), "kira", "a" * 64, "stub")
                with self.assertRaises(ValueError):
                    bridge.respond(case)

        bridge = ExternalAdapterBridge(
            FakeInstance({"profile_id": "kira", "spoken": "bounded"}, {"blob": "x" * 131073}),
            "kira",
            "a" * 64,
            "stub",
        )
        with self.assertRaises(ValueError):
            bridge.export_state()


class ManifestAndGuardTests(unittest.TestCase):
    def test_manifest_detects_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "protected.txt"
            path.write_text("before", encoding="utf-8")
            before = snapshot_protected_paths([path])
            path.write_text("after", encoding="utf-8")
            after = snapshot_protected_paths([path])
            comparison = compare_manifests(before, after)
            self.assertFalse(comparison["unchanged"])
            self.assertEqual(1, comparison["change_count"])

    def test_guard_rejects_escape_and_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            root.mkdir()
            guard = OutputGuard(root)
            with self.assertRaises(PermissionError):
                guard.checked(Path("..") / "escape.txt")
            with self.assertRaises(ValueError):
                reject_output_protected_overlap(root, [root / "nested"])

    def test_guard_refuses_reused_output_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            root.mkdir()
            (root / "local_transcript.jsonl").write_text("old\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                OutputGuard(root).prepare()


class IntegrationTests(unittest.TestCase):
    def test_duration_configuration_fails_closed_before_output_creation(self) -> None:
        for target in (0, -1, 60.01, float("nan"), float("inf")):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "invalid-duration"
                with self.assertRaises(ValueError):
                    run_evaluation(
                        EvaluationConfig(
                            person="kira",
                            output_root=output,
                            target_minutes=target,
                            backend="stub",
                        )
                    )
                self.assertFalse(output.exists())

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "unpaced-duration"
            with self.assertRaises(ValueError):
                run_evaluation(
                    EvaluationConfig(
                        person="kira",
                        output_root=output,
                        target_minutes=0.01,
                        backend="stub",
                        pace=False,
                    )
                )
            self.assertFalse(output.exists())

    def test_process_write_fence_denies_outside_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "run"
            output.mkdir()
            denied_target = base / "outside.txt"
            script = (
                "import sys; sys.dont_write_bytecode=True; "
                f"sys.path.insert(0, {str(PACKAGE_ROOT)!r}); "
                "from isolated_eval.containment import ProcessWriteFence; "
                f"ProcessWriteFence.install({str(output)!r}); "
                f"open({str(denied_target)!r}, 'w', encoding='utf-8').write('bad')"
            )
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("PermissionError", result.stderr)
            self.assertFalse(denied_target.exists())

    def test_process_write_fence_denies_os_open_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "run"
            output.mkdir()
            denied_target = base / "outside-os-open.txt"
            script = (
                "import os, sys; sys.dont_write_bytecode=True; "
                f"sys.path.insert(0, {str(PACKAGE_ROOT)!r}); "
                "from isolated_eval.containment import ProcessWriteFence; "
                f"ProcessWriteFence.install({str(output)!r}); "
                f"os.open({str(denied_target)!r}, os.O_WRONLY | os.O_CREAT, 0o600)"
            )
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("PermissionError", result.stderr)
            self.assertFalse(denied_target.exists())

    def test_stub_smoke_writes_sanitized_aggregate_only_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            protected = base / "protected.txt"
            protected.write_text("fixed", encoding="utf-8")
            output = base / "run"
            command = [
                sys.executable,
                "-B",
                str(PACKAGE_ROOT / "run_evaluation.py"),
                "--person",
                "kira",
                "--backend",
                "stub",
                "--smoke",
                "--output-root",
                str(output),
                "--protected-path",
                str(protected),
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(0, result.returncode, result.stderr)
            report_path = output / "SANITIZED_AGGREGATE_REPORT.json"
            report_text = report_path.read_text(encoding="utf-8")
            report = json.loads(report_text)
            self.assertTrue(report["completed"])
            self.assertTrue(report["duration_requirement_satisfied"])
            self.assertFalse(report["claim_eligible_as_requested_duration_run"])
            self.assertTrue(report["protected_paths_unchanged"])
            self.assertEqual("fixed", protected.read_text(encoding="utf-8"))
            self.assertNotIn("LOCAL_ONLY_REFLECTION", report_text)
            self.assertNotIn('"private_note"', report_text)
            self.assertNotIn('"spoken"', report_text)
            private_text = (output / "local_private_notes.jsonl").read_text(encoding="utf-8")
            self.assertIn("LOCAL_ONLY_REFLECTION", private_text)
            self.assertIn('"requested_as_non_cot_summary": true', private_text)
            self.assertNotIn('"not_chain_of_thought": true', private_text)

    def test_paced_run_reaches_requested_wall_clock_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "paced-run"
            target_minutes = 0.03
            target_seconds = target_minutes * 60.0
            command = [
                sys.executable,
                "-B",
                str(PACKAGE_ROOT / "run_evaluation.py"),
                "--person",
                "kira",
                "--backend",
                "stub",
                "--target-minutes",
                str(target_minutes),
                "--output-root",
                str(output),
            ]
            wall_started = time.monotonic()
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            wall_elapsed = time.monotonic() - wall_started
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(
                (output / "SANITIZED_AGGREGATE_REPORT.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["completed"])
            self.assertEqual(18, report["results"]["case_count"])
            self.assertTrue(report["duration_requirement_satisfied"])
            self.assertTrue(report["claim_eligible_as_requested_duration_run"])
            self.assertGreaterEqual(report["elapsed_seconds"], target_seconds)
            self.assertGreaterEqual(wall_elapsed, target_seconds)

    def test_integrated_portable_adapter_honors_external_stub_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "portable-stub-smoke"
            environment = os.environ.copy()
            existing_pythonpath = environment.get("PYTHONPATH")
            environment["PYTHONPATH"] = str(PORTABLE_RUNTIME_ROOT) + (
                os.pathsep + existing_pythonpath if existing_pythonpath else ""
            )
            command = [
                sys.executable,
                "-B",
                str(PACKAGE_ROOT / "run_evaluation.py"),
                "--person",
                "kira",
                "--backend",
                "stub",
                "--smoke",
                "--adapter-module",
                "portable_mind.evaluator",
                "--output-root",
                str(output),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                env=environment,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(
                (output / "SANITIZED_AGGREGATE_REPORT.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["completed"])
            self.assertEqual(10, report["results"]["case_count"])
            self.assertIsNone(report["verified_model_digest"])
            self.assertTrue((output / "portable_adapter_state").is_dir())


if __name__ == "__main__":
    unittest.main()
