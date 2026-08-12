"""Hostile stdlib-only tests for the inert R5 voice-forge successor."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import inspect
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(rel: str, name: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R5 = load("tools/qwen3_tts_voice_forge_r5_guards.py", "r5_guards_tests")
RUNNER = load(
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py",
    "r5_runner_tests",
)
WORKER = load(
    "tools/qwen3_tts_original_voice_forge_worker_v5.py",
    "r5_worker_tests",
)


def write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def strict_map() -> dict:
    result = {}
    for package, wheel, record in (
        ("torch", "1" * 64, "2" * 64),
        ("torchaudio", "3" * 64, "4" * 64),
    ):
        metadata = [f"{package}-1.0.dist-info/INSTALLER"]
        result[package] = {
            "exact_wheel_sha256": wheel,
            "installed_record_sha256": record,
            "wheel_members_bound_to_installed_files": 4,
            "installer_generated_differences": metadata,
            "installed_real_package_payload_count": 2,
            "exact_wheel_to_installed_record_and_files_bound": True,
            "bounded_non_executable_installer_metadata_differences": metadata,
            "unbound_installer_generated_package_bytes_allowed": False,
            "exact_wheel_to_installed_files_bound_r4": True,
        }
    return result


def full_capsule() -> dict:
    bindings = strict_map()
    result = {}
    for package in ("torch", "torchaudio"):
        prefix = package
        dist = f"{package}-1.0.dist-info"
        members = {
            f"{prefix}/__init__.py": {
                "bytes": 10,
                "sha256": "5" * 64,
                "record_self": False,
            },
            f"{prefix}/kernel.pyd": {
                "bytes": 20,
                "sha256": "6" * 64,
                "record_self": False,
            },
            f"{dist}/RECORD": {
                "bytes": 30,
                "sha256": bindings[package]["installed_record_sha256"],
                "record_self": True,
            },
        }
        installed = [
            {
                "path": f"Voice/sidecars/test/Lib/site-packages/{path}",
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            }
            for path, row in members.items()
        ]
        installed.append(
            {
                "path": f"Voice/sidecars/test/Lib/site-packages/{dist}/INSTALLER",
                "bytes": 4,
                "sha256": "7" * 64,
            }
        )
        result[package] = {
            "environment_distribution_spec_sha256": "8" * 64,
            "installed_record_evidence": {
                "version": "1.0",
                "record_path": f"Voice/sidecars/test/Lib/site-packages/{dist}/RECORD",
                "record_sha256": bindings[package]["installed_record_sha256"],
                "record_rows_verified": len(installed),
                "installed_files": installed,
            },
            "wheel_archive_evidence": {
                "package": package,
                "sha256": bindings[package]["exact_wheel_sha256"],
                "record_path": f"{dist}/RECORD",
                "members": members,
                "real_importable_payload_proven": True,
            },
            "strict_binding": bindings[package],
        }
    return result


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_top_level_key_rejected(self):
        with self.assertRaises(R5.R5GuardError):
            R5.strict_json_bytes(b'{"a":1,"a":2}', "duplicate")

    def test_duplicate_nested_key_rejected(self):
        with self.assertRaises(R5.R5GuardError):
            R5.strict_json_bytes(b'{"a":{"b":1,"b":2}}', "nested duplicate")

    def test_valid_nested_json_passes(self):
        self.assertEqual(R5.strict_json_bytes(b'{"a":{"b":1}}', "valid"), {"a": {"b": 1}})

    def test_child_requires_canonical_one_lf(self):
        value = {"schema": "child", "a": 1}
        payload = R5.canonical_bytes(value) + b"\n"
        self.assertEqual(
            R5.parse_canonical_child_result(
                payload, expected_schema="child", exact_keys={"schema", "a"}
            ),
            value,
        )

    def test_child_rejects_pretty_json(self):
        with self.assertRaises(R5.R5GuardError):
            R5.parse_canonical_child_result(
                b'{"schema": "child", "a": 1}\n',
                expected_schema="child",
                exact_keys={"schema", "a"},
            )

    def test_child_rejects_duplicate_key_even_when_last_value_expected(self):
        with self.assertRaises(R5.R5GuardError):
            R5.parse_canonical_child_result(
                b'{"a":0,"a":1,"schema":"child"}\n',
                expected_schema="child",
                exact_keys={"schema", "a"},
            )

    def test_child_rejects_extra_newline(self):
        with self.assertRaises(R5.R5GuardError):
            R5.parse_canonical_child_result(
                b'{"a":1,"schema":"child"}\n\n',
                expected_schema="child",
                exact_keys={"schema", "a"},
            )


class ManifestTrustTests(unittest.TestCase):
    def make_project(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        files = {"tools/a.py": b"print('a')\n", "tools/b.py": b"print('b')\n"}
        rows = []
        for rel, payload in files.items():
            path = root / rel
            write(path, payload)
            rows.append(
                {
                    "path": rel,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        manifest = {
            "schema": "qwen3_tts_voice_forge_payload_manifest_v5",
            "status": "IMMUTABLE_PAYLOAD_REQUIRES_EXTERNAL_AUTHORIZATION",
            "execution_allowed": False,
            "self_authorization_allowed": False,
            "files": rows,
        }
        path = root / "payload.json"
        payload = json.dumps(manifest, sort_keys=True).encode()
        write(path, payload)
        return temporary, root, path, payload, files

    def test_external_hash_pins_exact_manifest(self):
        temporary, root, path, payload, files = self.make_project()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(R5, "R5_PAYLOAD_MANIFEST_REL", Path("payload.json")):
            parsed, indexed = R5.verify_payload_manifest(
                project_root=root,
                expected_manifest_sha256=hashlib.sha256(payload).hexdigest(),
                required_payloads=set(files),
            )
        self.assertFalse(parsed["execution_allowed"])
        self.assertEqual(set(indexed), set(files))

    def test_manifest_cannot_change_own_status_and_rehash_itself(self):
        temporary, root, path, payload, files = self.make_project()
        self.addCleanup(temporary.cleanup)
        changed = json.loads(payload)
        changed["execution_allowed"] = True
        changed["status"] = "INDEPENDENT_AUDIT_ACCEPTED_ONE_BOUNDED_RUN"
        path.write_text(json.dumps(changed), encoding="utf-8")
        with mock.patch.object(R5, "R5_PAYLOAD_MANIFEST_REL", Path("payload.json")):
            with self.assertRaises(R5.R5GuardError):
                R5.verify_payload_manifest(
                    project_root=root,
                    expected_manifest_sha256=hashlib.sha256(payload).hexdigest(),
                    required_payloads=set(files),
                )

    def test_manifest_extra_inventory_row_rejected(self):
        temporary, root, path, payload, files = self.make_project()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(R5, "R5_PAYLOAD_MANIFEST_REL", Path("payload.json")):
            with self.assertRaises(R5.R5GuardError):
                R5.verify_payload_manifest(
                    project_root=root,
                    expected_manifest_sha256=hashlib.sha256(payload).hexdigest(),
                    required_payloads={"tools/a.py"},
                )

    def test_manifest_duplicate_json_key_rejected(self):
        temporary, root, path, _payload, files = self.make_project()
        self.addCleanup(temporary.cleanup)
        duplicate = b'{"schema":"qwen3_tts_voice_forge_payload_manifest_v5","schema":"x"}'
        path.write_bytes(duplicate)
        with mock.patch.object(R5, "R5_PAYLOAD_MANIFEST_REL", Path("payload.json")):
            with self.assertRaises(R5.R5GuardError):
                R5.verify_payload_manifest(
                    project_root=root,
                    expected_manifest_sha256=hashlib.sha256(duplicate).hexdigest(),
                    required_payloads=set(files),
                )


class AuthorizationTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        rejected = root / "System/Docs/r4.md"
        audit = root / "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_TEST.md"
        write(rejected, b"rejected audit")
        write(audit, b"accepted audit")
        now = datetime.now(timezone.utc)
        authorization = {
            "schema": "qwen3_tts_voice_forge_execution_authorization_v5",
            "status": "INDEPENDENT_AUDIT_ACCEPTED_ONE_BOUNDED_RUN",
            "execution_allowed": True,
            "one_use": True,
            "payload_manifest_path": R5.R5_PAYLOAD_MANIFEST_REL.as_posix(),
            "payload_manifest_sha256": "1" * 64,
            "independent_audit_path": audit.relative_to(root).as_posix(),
            "independent_audit_sha256": hashlib.sha256(b"accepted audit").hexdigest(),
            "rejected_r4_audit_path": rejected.relative_to(root).as_posix(),
            "rejected_r4_audit_sha256": hashlib.sha256(b"rejected audit").hexdigest(),
            "bundle_id": "bundle-test",
            "run_id": "run-test",
            "authorization_nonce_sha256": "2" * 64,
            "issued_utc": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "expires_utc": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
        }
        auth_path = root / "Data/voice/authorizations/qwen3_tts_voice_forge_v5/auth.json"
        payload = json.dumps(authorization, sort_keys=True).encode()
        write(auth_path, payload)
        return temporary, root, rejected, auth_path, payload, authorization

    def verify(self, root, rejected, auth_path, payload, **overrides):
        with (
            mock.patch.object(R5, "R4_REJECTED_AUDIT_REL", rejected.relative_to(root)),
            mock.patch.object(
                R5,
                "R4_REJECTED_AUDIT_SHA256",
                hashlib.sha256(rejected.read_bytes()).hexdigest(),
            ),
        ):
            return R5.verify_execution_authorization(
                project_root=root,
                authorization_path=auth_path,
                expected_authorization_sha256=hashlib.sha256(payload).hexdigest(),
                expected_manifest_sha256=overrides.get("manifest", "1" * 64),
                bundle_id=overrides.get("bundle", "bundle-test"),
                run_id=overrides.get("run", "run-test"),
            )

    def test_exact_external_authorization_passes(self):
        temporary, root, rejected, path, payload, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        authorization, evidence = self.verify(root, rejected, path, payload)
        self.assertTrue(authorization["one_use"])
        self.assertEqual(evidence["sha256"], hashlib.sha256(payload).hexdigest())

    def test_wrong_external_authorization_hash_rejected(self):
        temporary, root, rejected, path, payload, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(R5.R5GuardError):
            with (
                mock.patch.object(R5, "R4_REJECTED_AUDIT_REL", rejected.relative_to(root)),
                mock.patch.object(R5, "R4_REJECTED_AUDIT_SHA256", hashlib.sha256(rejected.read_bytes()).hexdigest()),
            ):
                R5.verify_execution_authorization(
                    project_root=root,
                    authorization_path=path,
                    expected_authorization_sha256="f" * 64,
                    expected_manifest_sha256="1" * 64,
                    bundle_id="bundle-test",
                    run_id="run-test",
                )

    def test_authorization_cannot_rebind_manifest(self):
        temporary, root, rejected, path, payload, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(R5.R5GuardError):
            self.verify(root, rejected, path, payload, manifest="9" * 64)

    def test_authorization_cannot_rebind_bundle(self):
        temporary, root, rejected, path, payload, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(R5.R5GuardError):
            self.verify(root, rejected, path, payload, bundle="attacker-bundle")

    def test_authorization_outside_fixed_root_rejected(self):
        temporary, root, rejected, path, payload, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        outside = root / "auth.json"
        outside.write_bytes(payload)
        with self.assertRaises(R5.R5GuardError):
            self.verify(root, rejected, outside, payload)

    def test_disabled_authorization_status_rejected(self):
        temporary, root, rejected, path, _payload, authorization = self.fixture()
        self.addCleanup(temporary.cleanup)
        authorization["status"] = "DISABLED_TEMPLATE_FRESH_INDEPENDENT_R5_AUDIT_REQUIRED"
        authorization["execution_allowed"] = False
        payload = json.dumps(authorization, sort_keys=True).encode()
        path.write_bytes(payload)
        with self.assertRaises(R5.R5GuardError):
            self.verify(root, rejected, path, payload)

    def test_duplicate_key_authorization_rejected(self):
        temporary, root, rejected, path, _payload, _authorization = self.fixture()
        self.addCleanup(temporary.cleanup)
        payload = b'{"schema":"qwen3_tts_voice_forge_execution_authorization_v5","schema":"attacker"}'
        path.write_bytes(payload)
        with self.assertRaises(R5.R5GuardError):
            self.verify(root, rejected, path, payload)


class ProvenanceTests(unittest.TestCase):
    def test_all_five_exact_maps_pass(self):
        value = strict_map()
        result = R5.reconcile_provenance_maps(
            parent_preflight=value,
            reservation=json.loads(json.dumps(value)),
            worker_pre_model=json.loads(json.dumps(value)),
            worker_post_execution=json.loads(json.dumps(value)),
            parent_postflight=json.loads(json.dumps(value)),
        )
        self.assertTrue(result["all_five_maps_strictly_equal"])

    def test_worker_forged_map_rejected_by_equality(self):
        value = strict_map()
        forged = json.loads(json.dumps(value))
        forged["torch"]["wheel_members_bound_to_installed_files"] = 999
        with self.assertRaises(R5.R5GuardError):
            R5.reconcile_provenance_maps(
                parent_preflight=value,
                reservation=value,
                worker_pre_model=forged,
                worker_post_execution=value,
                parent_postflight=value,
            )

    def test_injected_pyd_rejected_even_with_true_flags(self):
        forged = strict_map()
        forged["torch"]["bounded_non_executable_installer_metadata_differences"] = [
            "torch/injected.pyd"
        ]
        forged["torch"]["installer_generated_differences"] = ["torch/injected.pyd"]
        with self.assertRaises(R5.R5GuardError):
            R5.require_strict_provenance_map(forged, "forged")

    def test_arbitrary_dist_info_extra_rejected(self):
        forged = strict_map()
        forged["torch"]["bounded_non_executable_installer_metadata_differences"] = [
            "torch-1.0.dist-info/attacker.txt"
        ]
        forged["torch"]["installer_generated_differences"] = [
            "torch-1.0.dist-info/attacker.txt"
        ]
        with self.assertRaises(R5.R5GuardError):
            R5.require_strict_provenance_map(forged, "forged")

    def test_parent_postflight_change_rejected(self):
        value = strict_map()
        post = json.loads(json.dumps(value))
        post["torchaudio"]["installed_record_sha256"] = "a" * 64
        with self.assertRaises(R5.R5GuardError):
            R5.reconcile_provenance_maps(
                parent_preflight=value,
                reservation=value,
                worker_pre_model=value,
                worker_post_execution=value,
                parent_postflight=post,
            )

    def test_complete_installed_and_wheel_maps_match_across_all_five_phases(self):
        value = full_capsule()
        result = R5.reconcile_full_provenance_capsules(
            parent_preflight=value,
            reservation=json.loads(json.dumps(value)),
            worker_pre_model=json.loads(json.dumps(value)),
            worker_post_execution=json.loads(json.dumps(value)),
            parent_postflight=json.loads(json.dumps(value)),
        )
        self.assertTrue(result["all_five_complete_capsules_strictly_equal"])

    def test_injected_installed_pyd_absent_from_wheel_map_rejected(self):
        value = full_capsule()
        files = value["torch"]["installed_record_evidence"]["installed_files"]
        files.append(
            {
                "path": "Voice/sidecars/test/Lib/site-packages/torch/injected.pyd",
                "bytes": 99,
                "sha256": "9" * 64,
            }
        )
        value["torch"]["installed_record_evidence"]["record_rows_verified"] += 1
        with self.assertRaises(R5.R5GuardError):
            R5.require_full_provenance_capsule(value, "injected")

    def test_complete_worker_file_map_substitution_rejected(self):
        value = full_capsule()
        worker = json.loads(json.dumps(value))
        worker["torch"]["installed_record_evidence"]["installed_files"][0][
            "sha256"
        ] = "a" * 64
        with self.assertRaises(R5.R5GuardError):
            R5.reconcile_full_provenance_capsules(
                parent_preflight=value,
                reservation=value,
                worker_pre_model=worker,
                worker_post_execution=value,
                parent_postflight=value,
            )


class EvidenceAndFinalizationTests(unittest.TestCase):
    def test_incident_is_reserved_before_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            incident = R5.reserve_incident(Path(temporary), "bundle-test", "run-test")
            self.assertTrue((incident / "failure_slot_reserved.json").is_file())

    def test_failure_collision_advances_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            incident = Path(temporary)
            (incident / "failure_001.json").write_text("occupied", encoding="utf-8")
            path = R5.preserve_failure_or_raise(
                incident,
                exc=RuntimeError("boom"),
                stage="TEST",
                attempt=None,
                worker_started=False,
                traceback_text="trace",
            )
            self.assertEqual(path.name, "failure_002.json")
            self.assertEqual((incident / "failure_001.json").read_text(), "occupied")

    def test_failure_write_loss_is_never_silent(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(R5, "write_new_json", side_effect=OSError("disk full")):
                with self.assertRaises(R5.R5EvidenceError):
                    R5.preserve_failure_or_raise(
                        Path(temporary),
                        exc=RuntimeError("boom"),
                        stage="TEST",
                        attempt=None,
                        worker_started=False,
                        traceback_text="trace",
                    )

    def test_parent_owned_sibling_finalization_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pending = root / "attempt_001"
            pending.mkdir()
            (pending / "a.bin").write_bytes(b"a")
            finalized = R5.finalize_pending_tree(pending, root / "finalized_attempt_001")
            self.assertEqual((finalized / "a.bin").read_bytes(), b"a")
            self.assertFalse(pending.exists())

    def test_preoccupied_finalization_fails_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pending = root / "attempt_001"
            target = root / "finalized_attempt_001"
            pending.mkdir()
            target.mkdir()
            (target / "owner.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaises(R5.R5GuardError):
                R5.finalize_pending_tree(pending, target)
            self.assertEqual((target / "owner.txt").read_text(), "preserve")

    def test_durable_acceptance_reopens_exact_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "a.bin", b"a")
            acceptance = {"schema": "acceptance", "value": 1}
            calls = []

            def validate():
                calls.append(True)

            result = R5.durable_acceptance_with_held_artifacts(
                finalized_root=root,
                relative_paths=["a.bin"],
                acceptance_path=root / "acceptance.json",
                acceptance=acceptance,
                semantic_validator=validate,
                handle_context=lambda _paths: contextlib.nullcontext([]),
            )
            self.assertEqual(len(calls), 2)
            self.assertTrue(result["post_acceptance_reopen_passed"])

    def test_mutation_during_acceptance_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "a.bin", b"a")
            calls = 0

            def validate():
                nonlocal calls
                calls += 1
                if calls == 2:
                    (root / "a.bin").write_bytes(b"changed")

            with self.assertRaises(R5.R5GuardError):
                R5.durable_acceptance_with_held_artifacts(
                    finalized_root=root,
                    relative_paths=["a.bin"],
                    acceptance_path=root / "acceptance.json",
                    acceptance={"schema": "acceptance"},
                    semantic_validator=validate,
                    handle_context=lambda _paths: contextlib.nullcontext([]),
                )

    def test_one_use_authorization_ledger_rejects_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pending = root / "Voice/voice_forge/private_review_v5/run-test/bundle-test/attempt_001"
            pending.mkdir(parents=True)
            authorization = {"authorization_nonce_sha256": "a" * 64}
            with (
                mock.patch.object(RUNNER, "PROJECT_ROOT", root),
                mock.patch.object(
                    RUNNER,
                    "AUTH_LEDGER_ROOT_REL",
                    Path("Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v5"),
                ),
            ):
                RUNNER.consume_execution_authorization(
                    R5,
                    authorization=authorization,
                    authorization_sha256="b" * 64,
                    payload_manifest_sha256="c" * 64,
                    bundle_id="bundle-test",
                    run_id="run-test",
                    pending=pending,
                )
                with self.assertRaises(R5.R5EvidenceError):
                    RUNNER.consume_execution_authorization(
                        R5,
                        authorization=authorization,
                        authorization_sha256="b" * 64,
                        payload_manifest_sha256="c" * 64,
                        bundle_id="bundle-test",
                        run_id="run-test",
                        pending=pending,
                    )

    def test_later_use_reopens_acceptance_hash_and_artifact_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            finalized = root / "finalized_attempt_001"
            finalized.mkdir()
            (finalized / "voice.wav").write_bytes(b"voice")
            snapshot = R5.artifact_snapshot(finalized, ["voice.wav"])
            payload_manifest = root / RUNNER.PAYLOAD_MANIFEST_REL
            write(payload_manifest, b"{}")
            audit = root / "System/Docs/audit.md"
            write(audit, b"audit")
            authorization_path = root / "Data/voice/authorizations/qwen3_tts_voice_forge_v5/auth.json"
            authorization = {
                "independent_audit_path": audit.relative_to(root).as_posix(),
                "independent_audit_sha256": hashlib.sha256(b"audit").hexdigest(),
            }
            write(authorization_path, json.dumps(authorization).encode())
            acceptance = {
                "schema": "qwen3_tts_original_voice_forge_parent_acceptance_v5",
                "owner_hearing_acceptance": "PENDING",
                "activation_assignment_publication_or_upload_allowed": False,
                "payload_manifest_sha256": hashlib.sha256(b"{}").hexdigest(),
                "execution_authorization": {
                    "path": authorization_path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
                },
                "held_finalized_relative_paths": ["voice.wav"],
                "final_artifact_snapshot": snapshot,
            }
            path = root / "acceptance.json"
            R5.write_new_json(path, acceptance)
            with mock.patch.object(RUNNER, "PROJECT_ROOT", root):
                observed = RUNNER.reopen_acceptance_for_later_use(
                    R5,
                    finalized=finalized,
                    acceptance_path=path,
                    expected_acceptance_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            self.assertEqual(observed, acceptance)
            (finalized / "voice.wav").write_bytes(b"changed")
            with mock.patch.object(RUNNER, "PROJECT_ROOT", root):
                with self.assertRaises(RUNNER.R5LauncherError):
                    RUNNER.reopen_acceptance_for_later_use(
                        R5,
                        finalized=finalized,
                        acceptance_path=path,
                        expected_acceptance_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    )


class InertnessTests(unittest.TestCase):
    def test_runner_without_execute_fails_before_model_path(self):
        args = SimpleNamespace(
            execute=False,
            acknowledge_private_unreviewed=False,
            acknowledge_no_download=False,
            bundle_id=None,
            run_id=None,
        )
        with self.assertRaises(RUNNER.R5LauncherError):
            RUNNER.run(args)

    def test_shipped_r5_sources_do_not_import_torch_or_qwen(self):
        for rel in (
            "tools/qwen3_tts_voice_forge_r5_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v5.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("import torch", text)
            self.assertNotIn("import qwen", text.lower())

    def test_worker_containment_is_suspended_job_and_exact_tree_termination(self):
        text = (ROOT / "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("0x00000004 | 0x00000200 | 0x01000000", text)
        self.assertIn("AssignProcessToJobObject", text)
        self.assertIn("NtResumeProcess", text)
        self.assertIn("TerminateJobObject", text)

    def test_parent_external_trust_precedes_guard_dependency_import(self):
        source = inspect.getsource(RUNNER.run)
        self.assertLess(
            source.index("bootstrap_verify_external_trust(args)"),
            source.index("R5_GUARDS_REL"),
        )

    def test_worker_external_trust_precedes_guard_dependency_import(self):
        source = inspect.getsource(WORKER.main)
        self.assertLess(
            source.index("bootstrap_verify_external_trust(args)"),
            source.index("R5_GUARDS_REL"),
        )

    def test_sealed_parent_and_worker_load_exact_source_not_bytecode_cache(self):
        for module in (RUNNER, WORKER):
            source = inspect.getsource(module.load_sealed_module)
            self.assertIn("source = path.read_bytes()", source)
            self.assertIn("compile(source", source)
            self.assertNotIn("spec_from_file_location", source)


if __name__ == "__main__":
    unittest.main()
