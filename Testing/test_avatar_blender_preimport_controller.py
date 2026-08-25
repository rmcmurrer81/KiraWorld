"""Hostile non-Blender tests for the pre-import controller boundary."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_preimport_controller as controller


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_process(root: str, run_id: str, start, queue) -> None:
    start.wait(10)
    try:
        store = controller.OneRunClaimStore(Path(root))
        claim = store.reserve(
            run_id=run_id,
            request_record={"schema": "test", "operation": "build"},
        )
        queue.put(("won", claim.claim_sha256))
    except controller.ClaimAlreadyExists:
        queue.put(("rejected", "already_claimed"))
    except Exception as exc:  # pragma: no cover - diagnostic only
        queue.put(("error", type(exc).__name__))


def _outcome_process(
    root: str,
    run_id: str,
    claim_sha256: str,
    request_sha256: str,
    start,
    queue,
) -> None:
    start.wait(10)
    claim_root = Path(root)
    claim = controller.OneRunClaim(
        run_id=run_id,
        claim_path=claim_root / f"{run_id}.claim.json",
        outcome_path=claim_root / f"{run_id}.outcome.json",
        claim_sha256=claim_sha256,
        request_sha256=request_sha256,
    )
    try:
        digest = controller.OneRunClaimStore(claim_root).terminalize(
            claim,
            status="BLOCKED_NATIVE_BOUNDARY_REQUIRED",
            reason_code="native_boundary_required",
            binding_sha256="1" * 64,
        )
        queue.put(("won", digest))
    except controller.OutcomeAlreadyExists:
        queue.put(("rejected", "already_terminal"))
    except Exception as exc:  # pragma: no cover - diagnostic only
        queue.put(("error", type(exc).__name__))


class _FakeProvider:
    provider_id = "unreviewed_test_provider"
    interface_version = controller.NATIVE_PROVIDER_INTERFACE

    def __init__(self) -> None:
        self.called = False

    def launch_held_suspended_and_verify(self, **kwargs):
        self.called = True
        raise AssertionError("unreviewed provider must never be called")


class _ExplodingProvider:
    @property
    def provider_id(self):
        raise RuntimeError("property must not orphan a claimed run")


class _UnhashableProvider:
    provider_id = []
    interface_version = controller.NATIVE_PROVIDER_INTERFACE

    @property
    def interface_version(self):
        raise RuntimeError("property must not orphan a claimed run")


class BlenderPreImportControllerTests(unittest.TestCase):
    def _make_policy_tree(self, root: Path, operation: str = "build"):
        installation = root / "Blender 5.1"
        interpreter_dir = installation / "5.1" / "python" / "bin"
        interpreter_dir.mkdir(parents=True)
        blender = installation / "blender.exe"
        interpreter = interpreter_dir / "python.exe"
        worker_name = (
            controller.BUILD_WORKER_NAME
            if operation == "build"
            else controller.AUDIT_WORKER_NAME
        )
        worker = root / worker_name
        config = root / controller.CARRIER_CONFIG_NAME
        blender.write_bytes(b"bounded fake Blender image")
        interpreter.write_bytes(b"bounded fake bundled interpreter")
        worker.write_text("# bounded worker fixture\n", encoding="utf-8")
        config.write_text('{"schema_version":1}\n', encoding="utf-8")
        policy = controller.ControllerPolicy(
            policy_id=f"fixture_{operation}_policy",
            operation=operation,
            artifacts=(
                controller.ArtifactBinding("blender_executable", blender, _sha(blender)),
                controller.ArtifactBinding("bundled_interpreter", interpreter, _sha(interpreter)),
                controller.ArtifactBinding("worker_script", worker, _sha(worker)),
                controller.ArtifactBinding("config", config, _sha(config)),
            ),
        )
        return policy

    def _write_authorization(
        self,
        root: Path,
        policy: controller.ControllerPolicy,
        run_id: str,
    ) -> controller.ArtifactBinding:
        by_role = policy.by_role
        zeros = "0" * 64
        record = {
            "schema": controller.AUTHORIZATION_SCHEMA,
            "status": controller.AUTHORIZATION_STATUS,
            "one_run_id": run_id,
            "issued_at_utc": "2026-08-25T12:00:00Z",
            "config_sha256": by_role["config"].sha256,
            "source_sha256": zeros,
            "candidate_blend_path": "Avatar/test/candidate.blend",
            "build_report_path": "Avatar/test/build.json",
            "audit_report_path": "Avatar/test/audit.json",
            "blender_executable_sha256": by_role["blender_executable"].sha256,
            "preflight_receipt_sha256": zeros,
            "controller_sha256": zeros,
            "builder_sha256": (
                by_role["worker_script"].sha256
                if policy.operation == "build"
                else zeros
            ),
            "auditor_sha256": (
                by_role["worker_script"].sha256
                if policy.operation == "audit"
                else zeros
            ),
            "intersection_auditor_sha256": zeros,
            "build_allowed": True,
            "audit_allowed": True,
            "background_required": True,
            "factory_startup_required": True,
            "autoexec_disabled_required": True,
            "overwrite_allowed": False,
            "source_mutation_allowed": False,
            "hair_allowed": False,
            "clothing_allowed": False,
            "internal_anatomy_allowed": False,
            "identity_styling_allowed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        path = root / controller.AUTHORIZATION_NAME
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        return controller.ArtifactBinding("authorization", path, _sha(path))

    def test_release_policy_binds_exact_machine_files_and_remains_blocked(self) -> None:
        evidence_path = PROJECT_ROOT / controller.MACHINE_EVIDENCE_RELATIVE_PATH
        evidence = controller.read_strict_json(evidence_path, max_bytes=512 * 1024)
        self.assertIs(evidence["execution_trust_boundary_closed"], False)
        self.assertEqual([], evidence["native_boundary"]["reviewed_provider_ids"])
        self.assertIs(controller.EXECUTION_TRUST_BOUNDARY_CLOSED, False)
        self.assertEqual(frozenset(), controller.REVIEWED_NATIVE_PROVIDER_IDS)
        for operation in ("build", "audit"):
            policy = controller.load_machine_policy(operation=operation)
            self.assertEqual(operation, policy.operation)
            for binding in policy.artifacts:
                held = controller.acquire_held_artifact(binding)
                try:
                    self.assertEqual(binding.sha256, held.sha256)
                    self.assertEqual(1, held.link_count)
                finally:
                    held.close()

    def test_exact_command_has_one_fixed_grammar(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            policy = self._make_policy_tree(root)
            authorization = root / controller.AUTHORIZATION_NAME
            authorization.write_text("{}", encoding="utf-8")
            command = controller.build_exact_command(policy, authorization)
            self.assertEqual(str(policy.by_role["blender_executable"].path), command[0])
            self.assertEqual(controller.REQUIRED_BLENDER_FLAGS, command[1:4])
            self.assertEqual("--python", command[4])
            self.assertEqual(str(policy.by_role["worker_script"].path), command[5])
            self.assertEqual("--", command[6])
            self.assertEqual(("--config", "--authorization"), (command[7], command[9]))
            self.assertEqual(11, len(command))

    @unittest.skipUnless(os.name == "nt", "Windows environment grammar")
    def test_environment_is_minimal_and_does_not_inherit_injection_variables(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            environment = controller.build_sanitized_environment(
                system_root=Path(os.environ["SystemRoot"]),
                temp_root=Path(raw),
            )
        self.assertEqual(
            {"SystemRoot", "WINDIR", "ComSpec", "PATH", "TEMP", "TMP"},
            set(environment),
        )
        for forbidden in (
            "PYTHONPATH",
            "PYTHONHOME",
            "BLENDER_USER_SCRIPTS",
            "BLENDER_USER_CONFIG",
        ):
            self.assertNotIn(forbidden, environment)

    def test_policy_rejects_wrong_worker_and_interpreter_layout(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            policy = self._make_policy_tree(root)
            bindings = list(policy.artifacts)
            wrong_worker = root / "unrelated.py"
            wrong_worker.write_text("pass\n", encoding="utf-8")
            bindings[2] = controller.ArtifactBinding("worker_script", wrong_worker, _sha(wrong_worker))
            with self.assertRaisesRegex(controller.InvalidRequest, "worker name"):
                controller.ControllerPolicy("fixture_build_policy", "build", tuple(bindings))

            wrong_python = root / "python.exe"
            wrong_python.write_bytes(b"wrong location")
            bindings = list(policy.artifacts)
            bindings[1] = controller.ArtifactBinding(
                "bundled_interpreter", wrong_python, _sha(wrong_python)
            )
            with self.assertRaisesRegex(controller.InvalidRequest, "outside Blender"):
                controller.ControllerPolicy("fixture_build_policy", "build", tuple(bindings))

    def test_hash_mismatch_and_hard_link_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            path = root / controller.BUILD_WORKER_NAME
            path.write_bytes(b"one")
            with self.assertRaisesRegex(controller.ArtifactBindingError, "hash differs"):
                controller.acquire_held_artifact(
                    controller.ArtifactBinding("worker_script", path, "0" * 64)
                )

            alias = root / "alias.py"
            os.link(path, alias)
            with self.assertRaisesRegex(controller.ArtifactBindingError, "multiply linked"):
                controller.acquire_held_artifact(
                    controller.ArtifactBinding("worker_script", path, _sha(path))
                )

    @unittest.skipUnless(os.name == "nt", "Windows share-mode hold")
    def test_held_file_rejects_ordinary_write_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            path = root / controller.BUILD_WORKER_NAME
            path.write_bytes(b"held content")
            held = controller.acquire_held_artifact(
                controller.ArtifactBinding("worker_script", path, _sha(path))
            )
            try:
                with self.assertRaises(OSError):
                    path.write_bytes(b"replacement")
                replacement = root / "replacement.py"
                replacement.write_bytes(b"replacement")
                with self.assertRaises(OSError):
                    os.replace(replacement, path)
                self.assertEqual(b"held content", path.read_bytes())
            finally:
                held.close()

    def test_held_file_close_is_idempotent_after_descriptor_reuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            held_path = root / controller.BUILD_WORKER_NAME
            other_path = root / "other.bin"
            held_path.write_bytes(b"held")
            other_path.write_bytes(b"other")
            held = controller.acquire_held_artifact(
                controller.ArtifactBinding("worker_script", held_path, _sha(held_path))
            )
            held.close()
            other_fd = os.open(other_path, os.O_RDONLY | int(getattr(os, "O_BINARY", 0)))
            try:
                held.close()
                self.assertEqual(b"other", os.read(other_fd, 5))
            finally:
                os.close(other_fd)

    def test_claim_is_atomic_across_processes_and_replay_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            queue = context.Queue()
            run_id = "concurrent_claim_01"
            processes = [
                context.Process(target=_claim_process, args=(raw, run_id, start, queue))
                for _ in range(5)
            ]
            for process in processes:
                process.start()
            start.set()
            results = [queue.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(0, process.exitcode)
            self.assertEqual(1, sum(status == "won" for status, _ in results))
            self.assertEqual(4, sum(status == "rejected" for status, _ in results))
            with self.assertRaises(controller.ClaimAlreadyExists):
                controller.OneRunClaimStore(Path(raw)).reserve(
                    run_id=run_id,
                    request_record={"schema": "test", "operation": "build"},
                )

    def test_terminal_outcome_is_atomic_private_and_single_use(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            store = controller.OneRunClaimStore(Path(raw))
            claim = store.reserve(
                run_id="terminal_record_01",
                request_record={"schema": "test", "operation": "build"},
            )
            digest = store.terminalize(
                claim,
                status="BLOCKED_NATIVE_BOUNDARY_REQUIRED",
                reason_code="native_boundary_required",
                binding_sha256="1" * 64,
            )
            self.assertRegex(digest, controller.SHA256_RE)
            record = json.loads(claim.outcome_path.read_text(encoding="utf-8"))
            self.assertNotIn("path", " ".join(record))
            self.assertIs(record["body_created"], False)
            self.assertIs(record["runtime_activation_allowed"], False)
            with self.assertRaises(controller.OutcomeAlreadyExists):
                store.terminalize(
                    claim,
                    status="PREFLIGHT_REJECTED",
                    reason_code="invalid_request",
                    binding_sha256=None,
                )

    def test_terminal_outcome_has_one_cross_process_winner(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            store = controller.OneRunClaimStore(root)
            claim = store.reserve(
                run_id="terminal_race_01",
                request_record={"schema": "test", "operation": "build"},
            )
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            queue = context.Queue()
            processes = [
                context.Process(
                    target=_outcome_process,
                    args=(
                        raw,
                        claim.run_id,
                        claim.claim_sha256,
                        claim.request_sha256,
                        start,
                        queue,
                    ),
                )
                for _ in range(4)
            ]
            for process in processes:
                process.start()
            start.set()
            results = [queue.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(20)
                self.assertEqual(0, process.exitcode)
            self.assertEqual(1, sum(status == "won" for status, _ in results))
            self.assertEqual(3, sum(status == "rejected" for status, _ in results))

    def test_tampered_or_fabricated_claim_cannot_terminalize_or_succeed(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            store = controller.OneRunClaimStore(root)
            claim = store.reserve(
                run_id="claim_tamper_01",
                request_record={"schema": "test", "operation": "build"},
            )
            original = claim.claim_path.read_text(encoding="utf-8")
            claim.claim_path.write_text(original.replace("CLAIMED_ONCE", "CLAIMED_TWICE"), encoding="utf-8")
            with self.assertRaisesRegex(controller.InvalidRequest, "hash differs"):
                store.terminalize(
                    claim,
                    status="BLOCKED_NATIVE_BOUNDARY_REQUIRED",
                    reason_code="native_boundary_required",
                    binding_sha256=None,
                )
            claim.claim_path.write_bytes(original.encode("utf-8"))
            with self.assertRaisesRegex(controller.InvalidRequest, "terminal status"):
                store.terminalize(
                    claim,
                    status="SUCCEEDED",
                    reason_code="native_boundary_required",
                    binding_sha256=None,
                )
            fabricated = controller.OneRunClaim(
                run_id="fabricated_claim_01",
                claim_path=root / "fabricated_claim_01.claim.json",
                outcome_path=root / "fabricated_claim_01.outcome.json",
                claim_sha256="0" * 64,
                request_sha256="0" * 64,
            )
            with self.assertRaisesRegex(controller.InvalidRequest, "unavailable"):
                store.terminalize(
                    fabricated,
                    status="PREFLIGHT_REJECTED",
                    reason_code="invalid_request",
                    binding_sha256=None,
                )
            traversal = controller.OneRunClaim(
                run_id="../escaped_claim_01",
                claim_path=root.parent / "escaped_claim_01.claim.json",
                outcome_path=root.parent / "escaped_claim_01.outcome.json",
                claim_sha256="0" * 64,
                request_sha256="0" * 64,
            )
            with self.assertRaisesRegex(controller.InvalidRequest, "run_id grammar"):
                store.terminalize(
                    traversal,
                    status="PREFLIGHT_REJECTED",
                    reason_code="invalid_request",
                    binding_sha256=None,
                )
            self.assertFalse(traversal.outcome_path.exists())

    @unittest.skipUnless(os.name == "nt", "Controller binds the Windows environment")
    def test_valid_preflight_terminalizes_blocked_and_never_calls_provider(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            claim_root = root / "claims"
            temp_root = root / "temp"
            claim_root.mkdir()
            temp_root.mkdir()
            policy = self._make_policy_tree(root)
            run_id = "blocked_native_01"
            authorization = self._write_authorization(root, policy, run_id)
            request = controller.LaunchRequest(
                run_id=run_id,
                operation="build",
                authorization=authorization,
                claim_root=claim_root,
                temp_root=temp_root,
                system_root=Path(os.environ["SystemRoot"]),
            )
            provider = _FakeProvider()
            result = controller.BlenderPreImportController(policy).submit(
                request,
                provider=provider,
            )
            self.assertEqual("BLOCKED_NATIVE_BOUNDARY_REQUIRED", result.status)
            self.assertFalse(result.process_started)
            self.assertFalse(provider.called)
            self.assertIsNotNone(result.binding_sha256)
            outcome = json.loads(
                (claim_root / f"{run_id}.outcome.json").read_text(encoding="utf-8")
            )
            self.assertEqual("BLOCKED_NATIVE_BOUNDARY_REQUIRED", outcome["status"])

    @unittest.skipUnless(os.name == "nt", "Controller binds the Windows environment")
    def test_even_mutated_trust_constants_cannot_reach_provider_method(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            claim_root = root / "claims"
            temp_root = root / "temp"
            claim_root.mkdir()
            temp_root.mkdir()
            policy = self._make_policy_tree(root)
            run_id = "sealed_provider_01"
            authorization = self._write_authorization(root, policy, run_id)
            request = controller.LaunchRequest(
                run_id=run_id,
                operation="build",
                authorization=authorization,
                claim_root=claim_root,
                temp_root=temp_root,
                system_root=Path(os.environ["SystemRoot"]),
            )
            provider = _FakeProvider()
            with mock.patch.object(controller, "EXECUTION_TRUST_BOUNDARY_CLOSED", True), mock.patch.object(
                controller,
                "REVIEWED_NATIVE_PROVIDER_IDS",
                frozenset({provider.provider_id}),
            ):
                result = controller.BlenderPreImportController(policy).submit(request, provider=provider)
            self.assertEqual("PREFLIGHT_REJECTED", result.status)
            self.assertEqual("reviewed_native_boundary_required", result.reason_code)
            self.assertFalse(provider.called)

    @unittest.skipUnless(os.name == "nt", "Controller binds the Windows environment")
    def test_malformed_provider_properties_terminalize_blocked(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            claim_root = root / "claims"
            temp_root = root / "temp"
            claim_root.mkdir()
            temp_root.mkdir()
            policy = self._make_policy_tree(root)
            run_id = "malformed_provider_01"
            authorization = self._write_authorization(root, policy, run_id)
            result = controller.BlenderPreImportController(policy).submit(
                controller.LaunchRequest(
                    run_id=run_id,
                    operation="build",
                    authorization=authorization,
                    claim_root=claim_root,
                    temp_root=temp_root,
                    system_root=Path(os.environ["SystemRoot"]),
                ),
                provider=_ExplodingProvider(),
            )
            self.assertEqual("BLOCKED_NATIVE_BOUNDARY_REQUIRED", result.status)
            self.assertTrue((claim_root / f"{run_id}.outcome.json").is_file())

            second_run = "unhashable_provider_01"
            second_authorization = self._write_authorization(root, policy, second_run)
            second_result = controller.BlenderPreImportController(policy).submit(
                controller.LaunchRequest(
                    run_id=second_run,
                    operation="build",
                    authorization=second_authorization,
                    claim_root=claim_root,
                    temp_root=temp_root,
                    system_root=Path(os.environ["SystemRoot"]),
                ),
                provider=_UnhashableProvider(),
            )
            self.assertEqual("BLOCKED_NATIVE_BOUNDARY_REQUIRED", second_result.status)
            self.assertTrue((claim_root / f"{second_run}.outcome.json").is_file())

    def test_machine_evidence_rejects_authority_capability_and_schema_drift(self) -> None:
        evidence = controller.read_strict_json(
            PROJECT_ROOT / controller.MACHINE_EVIDENCE_RELATIVE_PATH,
            max_bytes=512 * 1024,
        )
        mutations = []
        authority = json.loads(json.dumps(evidence))
        authority["body_created"] = True
        mutations.append(authority)
        capability = json.loads(json.dumps(evidence))
        capability["verified_static_capabilities"]["atomic_terminal_outcome"] = False
        mutations.append(capability)
        extra = json.loads(json.dumps(evidence))
        extra["unexpected_authority"] = False
        mutations.append(extra)
        nested_extra = json.loads(json.dumps(evidence))
        nested_extra["native_boundary"]["unexpected_native_authority"] = False
        mutations.append(nested_extra)
        for mutation in mutations:
            with self.subTest(keys=set(mutation)), self.assertRaises(controller.InvalidRequest):
                controller.validate_machine_evidence(mutation)

    @unittest.skipUnless(os.name == "nt", "Controller binds the Windows environment")
    def test_authorization_tamper_is_terminal_and_launches_nothing(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            claim_root = root / "claims"
            temp_root = root / "temp"
            claim_root.mkdir()
            temp_root.mkdir()
            policy = self._make_policy_tree(root)
            run_id = "tampered_auth_01"
            authorization = self._write_authorization(root, policy, run_id)
            value = json.loads(authorization.path.read_text(encoding="utf-8"))
            value["runtime_activation_allowed"] = True
            authorization.path.write_text(json.dumps(value), encoding="utf-8")
            authorization = controller.ArtifactBinding(
                "authorization", authorization.path, _sha(authorization.path)
            )
            request = controller.LaunchRequest(
                run_id=run_id,
                operation="build",
                authorization=authorization,
                claim_root=claim_root,
                temp_root=temp_root,
                system_root=Path(os.environ["SystemRoot"]),
            )
            provider = _FakeProvider()
            result = controller.BlenderPreImportController(policy).submit(request, provider=provider)
            self.assertEqual("PREFLIGHT_REJECTED", result.status)
            self.assertEqual("invalid_request", result.reason_code)
            self.assertFalse(provider.called)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_excess_depth(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            for name, content in (
                ("duplicate.json", '{"a":1,"a":2}'),
                ("nonfinite.json", '{"a":NaN}'),
            ):
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(controller.InvalidRequest):
                    controller.read_strict_json(path, max_bytes=1024)
            nested: object = "leaf"
            for _ in range(controller.MAX_JSON_DEPTH + 2):
                nested = {"next": nested}
            path = root / "deep.json"
            path.write_text(json.dumps(nested), encoding="utf-8")
            with self.assertRaises(controller.InvalidRequest):
                controller.read_strict_json(path, max_bytes=4096)

    def test_unc_and_symlink_inputs_fail_closed(self) -> None:
        with self.assertRaises(controller.InvalidRequest):
            controller.OneRunClaimStore(Path(r"\\server\share\claims"))
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw:
            root = Path(raw)
            source = root / controller.BUILD_WORKER_NAME
            source.write_text("pass\n", encoding="utf-8")
            link = root / "linked_worker.py"
            try:
                link.symlink_to(source)
            except OSError:
                self.skipTest("symlink creation is unavailable")
            with self.assertRaises(controller.InvalidRequest):
                controller.acquire_held_artifact(
                    controller.ArtifactBinding("worker_script", link, _sha(source))
                )

    @unittest.skipUnless(os.name == "nt", "Windows process-image query")
    def test_windows_process_image_helper_reports_current_image(self) -> None:
        image = controller.query_windows_process_image(os.getpid())
        self.assertTrue(image.is_file())
        self.assertTrue(os.path.samefile(image, Path(sys.executable)))
        expected = controller.acquire_held_artifact(
            controller.ArtifactBinding(
                "blender_executable",
                Path(sys.executable),
                _sha(Path(sys.executable)),
            )
        )
        try:
            attestation = controller.verify_windows_process_image(os.getpid(), expected)
            self.assertTrue(attestation["process_image_verified"])
            self.assertFalse(attestation["path_published"])
            self.assertEqual(_sha(Path(sys.executable)), attestation["sha256"])
        finally:
            expected.close()


if __name__ == "__main__":
    unittest.main()
