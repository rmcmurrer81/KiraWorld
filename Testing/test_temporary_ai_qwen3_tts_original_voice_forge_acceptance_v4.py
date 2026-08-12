"""Hostile stdlib-only regressions for the append-only inert R4 repair."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import struct
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from types import SimpleNamespace

from tools import qwen3_tts_original_voice_forge_worker_v4 as worker_v4
from tools import qwen3_tts_voice_forge_r3_guards as r3
from tools import qwen3_tts_voice_forge_r4_guards as r4
from tools import run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2 as runner_v2
from tools import run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4 as runner_v4


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded_sha256(value: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode("ascii")
    return "sha256=" + encoded.rstrip("=")


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_wav(
    path: Path, *, frequency: float = 220.0, frames: int = 1600, rate: int = 16000
) -> None:
    samples = [
        int(7000 * math.sin(2 * math.pi * frequency * index / rate))
        for index in range(frames)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def exact_binding() -> dict[str, str]:
    values = {
        "bundle_id": "bundle-r4-a",
        "candidate_id": "candidate-r4-a",
        "opaque_voice_id": "voice-r4-a",
        "ai_type": "expert_temp_ai",
    }
    hashes = [
        "job_sha256",
        "owner_authorization_sha256",
        "queue_binding_sha256",
        "canonical_profile_sha256",
        "canonical_creation_request_sha256",
        "identity_clearance_manifest_sha256",
        "watermark_evidence_manifest_sha256",
        "evaluation_corpus_sha256",
        "voice_design_model_manifest_sha256",
        "base_model_manifest_sha256",
        "environment_spec_sha256",
    ]
    for index, field in enumerate(hashes, start=1):
        values[field] = f"{index:x}" * 64
    return values


def create_bound_output_fixture(root: Path):
    attempt = root / "attempt_01"
    attempt.mkdir()
    reference = attempt / "original_design_reference.wav"
    clone = attempt / "runtime_clone_test.wav"
    prompt_path = attempt / "runtime_clone_prompt.pt"
    write_wav(reference, frequency=197.0)
    write_wav(clone, frequency=263.0)
    prompt_path.write_bytes(b"exact-persisted-r4-prompt")
    seals = {
        "reference_wav": r3.seal_pcm16_wav(reference, attempt),
        "clone_test_wav": r3.seal_pcm16_wav(clone, attempt),
        "runtime_clone_prompt": r3.seal_prompt_file(prompt_path, attempt, "a" * 64),
    }
    prompt_evidence = {
        "exact_saved_reference_reloaded": True,
        "reference_wav_sha256": seals["reference_wav"]["sha256"],
        "persisted_prompt_reload_used_for_generation": True,
        "in_memory_caller_prompt_used_for_generation": False,
        "sha256": seals["runtime_clone_prompt"]["sha256"],
        "created_prompt_semantic_sha256": seals["runtime_clone_prompt"][
            "semantic_sha256"
        ],
        "reloaded_prompt_semantic_sha256": seals["runtime_clone_prompt"][
            "semantic_sha256"
        ],
        "artifact_seal": seals["runtime_clone_prompt"],
    }
    binding = exact_binding()
    profile = {
        "schema": "qwen3_tts_original_voice_profile_candidate_v4",
        "status": "PRIVATE_UNREVIEWED_ENGINEERING_PASS_OWNER_HEARING_PENDING",
        **binding,
        "artifact_seals": seals,
        "persisted_prompt_evidence": prompt_evidence,
        "evaluator_mutation_guard": {
            "artifact_seals": {
                "reference_wav": seals["reference_wav"],
                "clone_test_wav": seals["clone_test_wav"],
            },
            "checkpoints": ["before:evaluate", "after:evaluate", "before_worker_acceptance"],
            "checked_before_and_after_every_evaluator_operation": True,
        },
        "artifacts": {
            "reference_wav": {"sha256": seals["reference_wav"]["sha256"]},
            "clone_test_wav": {"sha256": seals["clone_test_wav"]["sha256"]},
            "clone_prompt_sha256": seals["runtime_clone_prompt"]["sha256"],
        },
        "assignment_allowed": False,
        "activation_allowed": False,
        "publication_or_upload_allowed": False,
        "owner_hearing_acceptance": "PENDING",
    }
    profile_path = attempt / "voice_profile_candidate_v4.json"
    write_json(profile_path, profile)
    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v4",
        "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
        **binding,
        "profile_sha256": r4.sha256_file(profile_path),
        "artifact_seals": seals,
        "artifact_seals_sha256": r4.canonical_sha256(seals),
        "persisted_prompt_evidence": prompt_evidence,
    }
    manifest_path = attempt / "worker_manifest_v4.json"
    write_json(manifest_path, manifest)
    child = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v4",
        "status": manifest["status"],
        **binding,
        "manifest_path": manifest_path.name,
        "manifest_sha256": r4.sha256_file(manifest_path),
        "profile_path": profile_path.name,
        "profile_sha256": r4.sha256_file(profile_path),
        "artifact_seals_sha256": r4.canonical_sha256(seals),
    }
    return attempt, binding, profile, manifest, child


class ExactArtifactAndParentBindingTests(unittest.TestCase):
    def test_parent_reopens_exact_original_synthetic_job_before_nonce(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle_dir = Path(raw)
            job = {
                "schema": "qwen3_tts_original_voice_forge_job_v2",
                "voice_origin": "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE",
                "identity_basis": "original_trait_description",
                "design_traits_text": "A precise original warm alto design",
                "reference_text": "These are the exact reference words.",
                "test_text": "These are the exact clone test words.",
                "language": "English",
            }
            for prefix in ("design_traits", "reference", "test"):
                job[f"{prefix}_text_sha256"] = runner_v2.sha256_text(
                    job[f"{prefix}_text"]
                )
            path = bundle_dir / "job.json"
            write_json(path, job)
            bundle = {"job_path": "job.json", "job_sha256": r4.sha256_file(path)}
            evidence = runner_v4.validate_bound_original_job(
                runner_v2, bundle, bundle_dir
            )
            self.assertEqual(evidence["sha256"], bundle["job_sha256"])
            self.assertEqual(
                evidence["voice_origin"],
                "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE",
            )

            job["voice_origin"] = "PERSON_CLONE"
            write_json(path, job)
            bundle["job_sha256"] = r4.sha256_file(path)
            with self.assertRaises(runner_v4.R4LauncherError):
                runner_v4.validate_bound_original_job(runner_v2, bundle, bundle_dir)

    def test_exact_three_artifacts_and_stdout_bound_outputs_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, _profile, _manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            parsed = r4.parse_child_result(
                (json.dumps(child, separators=(",", ":")) + "\n").encode(), binding
            )
            manifest, profile, evidence = r4.reopen_and_validate_parent_outputs(
                attempt_dir=attempt,
                child_result=parsed,
                expected_binding=binding,
                r3_guards=r3,
            )
            self.assertEqual(manifest["candidate_id"], binding["candidate_id"])
            self.assertEqual(profile["job_sha256"], binding["job_sha256"])
            self.assertTrue(evidence["child_stdout_manifest_profile_hashes_enforced"])
            self.assertEqual(
                set(evidence["independently_reopened_exact_distinct_artifacts"]),
                set(r4.FINAL_ARTIFACT_PATHS),
            )

    def test_parent_rejects_profile_candidate_substitution_even_when_rehashed(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, profile, manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            profile["candidate_id"] = "candidate-r4-b"
            profile_path = attempt / "voice_profile_candidate_v4.json"
            write_json(profile_path, profile)
            manifest["profile_sha256"] = r4.sha256_file(profile_path)
            manifest_path = attempt / "worker_manifest_v4.json"
            write_json(manifest_path, manifest)
            child["profile_sha256"] = r4.sha256_file(profile_path)
            child["manifest_sha256"] = r4.sha256_file(manifest_path)
            with self.assertRaises(r4.R4GuardError):
                r4.reopen_and_validate_parent_outputs(
                    attempt_dir=attempt,
                    child_result=child,
                    expected_binding=binding,
                    r3_guards=r3,
                )

    def test_parent_rejects_false_or_stale_child_profile_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, profile, _manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            profile["owner_hearing_acceptance"] = "FORGED_ACCEPTED"
            write_json(attempt / "voice_profile_candidate_v4.json", profile)
            with self.assertRaises(r4.R4GuardError):
                r4.reopen_and_validate_parent_outputs(
                    attempt_dir=attempt,
                    child_result=child,
                    expected_binding=binding,
                    r3_guards=r3,
                )

    def test_parent_rejects_false_profile_hash_inside_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, _profile, manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            manifest["profile_sha256"] = "0" * 64
            manifest_path = attempt / "worker_manifest_v4.json"
            write_json(manifest_path, manifest)
            child["manifest_sha256"] = r4.sha256_file(manifest_path)
            with self.assertRaises(r4.R4GuardError):
                r4.reopen_and_validate_parent_outputs(
                    attempt_dir=attempt,
                    child_result=child,
                    expected_binding=binding,
                    r3_guards=r3,
                )

    def test_parent_rejects_manifest_job_substitution_even_when_rehashed(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, _profile, manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            manifest["job_sha256"] = "f" * 64
            manifest_path = attempt / "worker_manifest_v4.json"
            write_json(manifest_path, manifest)
            child["manifest_sha256"] = r4.sha256_file(manifest_path)
            with self.assertRaises(r4.R4GuardError):
                r4.reopen_and_validate_parent_outputs(
                    attempt_dir=attempt,
                    child_result=child,
                    expected_binding=binding,
                    r3_guards=r3,
                )

    def test_duplicate_substitute_cannot_satisfy_both_required_wavs(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt = Path(raw)
            write_wav(attempt / "substitute.wav", frequency=777.0)
            (attempt / "runtime_clone_prompt.pt").write_bytes(b"prompt")
            substitute = r3.seal_pcm16_wav(attempt / "substitute.wav", attempt)
            seals = {
                "reference_wav": dict(substitute),
                "clone_test_wav": dict(substitute),
                "runtime_clone_prompt": r3.seal_prompt_file(
                    attempt / "runtime_clone_prompt.pt", attempt, "a" * 64
                ),
            }
            with self.assertRaises(r4.R4GuardError):
                r4.verify_exact_artifact_set(
                    attempt_dir=attempt, seals=seals, r3_guards=r3
                )

    def test_swapped_required_wav_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, _binding, profile, _manifest, _child = create_bound_output_fixture(
                Path(raw)
            )
            seals = dict(profile["artifact_seals"])
            seals["reference_wav"], seals["clone_test_wav"] = (
                seals["clone_test_wav"],
                seals["reference_wav"],
            )
            with self.assertRaises(r4.R4GuardError):
                r4.verify_exact_artifact_set(
                    attempt_dir=attempt, seals=seals, r3_guards=r3
                )

    def test_missing_exact_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, _binding, profile, _manifest, _child = create_bound_output_fixture(
                Path(raw)
            )
            (attempt / "original_design_reference.wav").unlink()
            with self.assertRaises((r4.R4GuardError, r3.R3GuardError, OSError)):
                r4.verify_exact_artifact_set(
                    attempt_dir=attempt,
                    seals=profile["artifact_seals"],
                    r3_guards=r3,
                )

    def test_exact_clone_bytes_changed_after_child_handoff_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            attempt, binding, _profile, _manifest, child = create_bound_output_fixture(
                Path(raw)
            )
            write_wav(attempt / "runtime_clone_test.wav", frequency=901.0)
            with self.assertRaises(r4.R4GuardError):
                r4.reopen_and_validate_parent_outputs(
                    attempt_dir=attempt,
                    child_result=child,
                    expected_binding=binding,
                    r3_guards=r3,
                )

    def test_child_stdout_identity_mismatch_and_extra_output_are_rejected(self):
        binding = exact_binding()
        child = {
            "schema": "qwen3_tts_original_voice_forge_child_result_v4",
            "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
            **binding,
            "manifest_path": "worker_manifest_v4.json",
            "manifest_sha256": "a" * 64,
            "profile_path": "voice_profile_candidate_v4.json",
            "profile_sha256": "b" * 64,
            "artifact_seals_sha256": "c" * 64,
        }
        changed = dict(child)
        changed["candidate_id"] = "candidate-r4-b"
        with self.assertRaises(r4.R4GuardError):
            r4.parse_child_result(json.dumps(changed).encode(), binding)
        with self.assertRaises(r4.R4GuardError):
            r4.parse_child_result(
                ("unexpected\n" + json.dumps(child) + "\n").encode(), binding
            )


def build_wheel(
    project: Path, package: str, version: str, payloads: dict[str, bytes]
) -> tuple[Path, dict]:
    root = project / "wheel_evidence"
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{package}-{version}-cp311-cp311-win_amd64.whl"
    wheel = root / filename
    dist = package.replace("-", "_") + f"-{version}.dist-info"
    members = dict(payloads)
    members[f"{dist}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n".encode()
    )
    members[f"{dist}/WHEEL"] = (
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp311-cp311-win_amd64\n"
    )
    record_name = f"{dist}/RECORD"
    rows = [
        [name, encoded_sha256(payload), str(len(payload))]
        for name, payload in members.items()
    ]
    rows.append([record_name, "", ""])
    output = io.StringIO(newline="")
    csv.writer(output).writerows(rows)
    members[record_name] = output.getvalue().encode("utf-8")
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    row = {
        "version": version,
        "wheel_filename": filename,
        "wheel_evidence_path": wheel.relative_to(project).as_posix(),
        "wheel_sha256": r3.sha256_file(wheel),
        "installer_generated_files": [],
    }
    return wheel, row


def install_wheel(project: Path, venv_rel: Path, wheel: Path, wheel_evidence: dict):
    site = project / venv_rel / "Lib/site-packages"
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel, "r") as archive:
        archive.extractall(site)

    def evidence():
        rows = []
        for path in sorted(item for item in site.rglob("*") if item.is_file()):
            rows.append(
                {
                    "path": path.relative_to(project).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": r3.sha256_file(path),
                }
            )
        record = site / wheel_evidence["record_path"]
        return {
            "version": wheel_evidence["version"],
            "record_path": record.relative_to(project).as_posix(),
            "record_sha256": r3.sha256_file(record),
            "installed_files": rows,
        }

    return site, evidence


class StrictWheelDifferenceTests(unittest.TestCase):
    def make_exact(self, root: Path):
        project = root
        venv_rel = Path("sidecar/.venv")
        wheel, row = build_wheel(
            project,
            "torch",
            "2.11.0+cu130",
            {
                "torch/__init__.py": b"VERSION='2.11.0'\n",
                "torch/_C.cp311-win_amd64.pyd": b"exact-compiled-payload",
            },
        )
        wheel_evidence = r3.attest_wheel_archive(
            project_root=project,
            wheel_root_rel=Path("wheel_evidence"),
            package="torch",
            row=row,
        )
        site, evidence = install_wheel(project, venv_rel, wheel, wheel_evidence)
        return project, venv_rel, row, wheel_evidence, site, evidence

    def test_exact_wheel_with_no_differences_passes_r4(self):
        with tempfile.TemporaryDirectory() as raw:
            project, venv_rel, row, wheel, _site, evidence = self.make_exact(
                Path(raw)
            )
            result = r4.bind_wheel_to_installed_distribution(
                r3_guards=r3,
                project_root=project,
                isolated_venv_rel=venv_rel,
                package="torch",
                row=row,
                installed_evidence=evidence(),
                wheel_evidence=wheel,
            )
            self.assertTrue(result["exact_wheel_to_installed_files_bound_r4"])
            self.assertFalse(
                result["unbound_installer_generated_package_bytes_allowed"]
            )

    def test_installed_r4_override_is_used_by_the_frozen_r3_call_shape(self):
        with tempfile.TemporaryDirectory() as raw:
            project, venv_rel, row, wheel, _site, evidence = self.make_exact(
                Path(raw)
            )
            proxy = SimpleNamespace(
                bind_wheel_to_installed_distribution=
                r3.bind_wheel_to_installed_distribution
            )
            r4.install_r4_wheel_override(proxy)
            result = proxy.bind_wheel_to_installed_distribution(
                project_root=project,
                isolated_venv_rel=venv_rel,
                package="torch",
                row=row,
                installed_evidence=evidence(),
                wheel_evidence=wheel,
            )
            self.assertTrue(proxy._r4_wheel_override_installed)
            self.assertTrue(result["exact_wheel_to_installed_files_bound_r4"])

    def test_arbitrary_pyd_relabelled_bytecode_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            project, venv_rel, row, wheel, site, evidence = self.make_exact(Path(raw))
            injected = site / "torch/injected.pyd"
            injected.write_bytes(b"arbitrary-unbound-executable")
            hostile = {
                **row,
                "installer_generated_files": [
                    {
                        "path": "torch/injected.pyd",
                        "bytes": injected.stat().st_size,
                        "sha256": r3.sha256_file(injected),
                        "reason": "INSTALLER_GENERATED_BYTECODE",
                    }
                ],
            }
            with self.assertRaises(r4.R4GuardError):
                r4.bind_wheel_to_installed_distribution(
                    r3_guards=r3,
                    project_root=project,
                    isolated_venv_rel=venv_rel,
                    package="torch",
                    row=hostile,
                    installed_evidence=evidence(),
                    wheel_evidence=wheel,
                )

    def test_arbitrary_package_payload_cannot_use_metadata_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            project, venv_rel, row, wheel, site, evidence = self.make_exact(Path(raw))
            injected = site / "torch/injected.py"
            injected.write_bytes(b"EXECUTABLE=True\n")
            hostile = {
                **row,
                "installer_generated_files": [
                    {
                        "path": "torch/injected.py",
                        "bytes": injected.stat().st_size,
                        "sha256": r3.sha256_file(injected),
                        "reason": "INSTALLER_METADATA",
                    }
                ],
            }
            with self.assertRaises(r4.R4GuardError):
                r4.bind_wheel_to_installed_distribution(
                    r3_guards=r3,
                    project_root=project,
                    isolated_venv_rel=venv_rel,
                    package="torch",
                    row=hostile,
                    installed_evidence=evidence(),
                    wheel_evidence=wheel,
                )

    def test_exact_non_executable_installer_metadata_path_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            project, venv_rel, row, wheel, site, evidence = self.make_exact(Path(raw))
            metadata_root = wheel["record_path"].rsplit("/", 1)[0]
            installer = site / metadata_root / "INSTALLER"
            installer.write_bytes(b"pip\n")
            allowed = {
                **row,
                "installer_generated_files": [
                    {
                        "path": f"{metadata_root}/INSTALLER",
                        "bytes": installer.stat().st_size,
                        "sha256": r3.sha256_file(installer),
                        "reason": "INSTALLER_METADATA",
                    }
                ],
            }
            result = r4.bind_wheel_to_installed_distribution(
                r3_guards=r3,
                project_root=project,
                isolated_venv_rel=venv_rel,
                package="torch",
                row=allowed,
                installed_evidence=evidence(),
                wheel_evidence=wheel,
            )
            self.assertEqual(
                result["bounded_non_executable_installer_metadata_differences"],
                [f"{metadata_root}/INSTALLER"],
            )


class StaticInertnessAndPreservationTests(unittest.TestCase):
    def test_r4_worker_and_parent_are_inert_before_fresh_audit(self):
        with self.assertRaises(worker_v4.R4ForgeError):
            worker_v4.verify_r4_harness(PROJECT_ROOT)
        with self.assertRaises(runner_v4.R4LauncherError):
            runner_v4.verify_r4_harness()

    def test_runner_and_worker_require_explicit_execution_acknowledgements(self):
        args = argparse.Namespace(
            execute=False,
            bundle_id=None,
            acknowledge_private_unreviewed=False,
            acknowledge_no_download=False,
        )
        with self.assertRaises(runner_v4.R4LauncherError):
            runner_v4.run(args)
        with self.assertRaises(worker_v4.R4ForgeError):
            worker_v4.main([])

    def test_r4_manifest_is_sealed_inert_and_exact(self):
        path = PROJECT_ROOT / "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT")
        self.assertFalse(manifest["execution_allowed"])
        self.assertGreaterEqual(len(manifest["files"]), 22)
        for row in manifest["files"]:
            actual = PROJECT_ROOT / row["path"]
            self.assertEqual(actual.stat().st_size, row["bytes"], row["path"])
            self.assertEqual(r4.sha256_file(actual), row["sha256"], row["path"])

    def test_rejected_r3_and_predecessor_hashes_are_preserved(self):
        expected = {
            "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json": "3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada",
            "tools/qwen3_tts_voice_forge_r3_guards.py": "869ee27a048d2c40b8f1433b1fb17abf94c538f32bf3e74ec68417a2f9b4045c",
            "tools/qwen3_tts_original_voice_forge_worker_v3.py": "dcf9803afe4c519f19ff2eb6fc677454eb5b33d0e0d62861cfefe689ac90b020",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py": "f2aa4dca82bed34a88f46a4e8529829072f1aba0f56e61d12d1be522957eb53d",
            "Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v3.py": "7bb2b518d11a2ab1e19213369fa07cb01815445dff284b2e5c2831203c07d7a8",
            "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R3_INDEPENDENT_AUDIT_20260809.md": "30d82546cdea8ba874ee552ab684fc0404249f6d2635a0aa3831727a28384efb",
            "tools/qwen3_tts_original_voice_forge_worker_v2.py": "b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py": "88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45",
        }
        for rel, digest in expected.items():
            self.assertEqual(r4.sha256_file(PROJECT_ROOT / rel), digest, rel)

    def test_r4_sources_have_no_install_download_or_top_level_model_import(self):
        for rel in (
            "tools/qwen3_tts_voice_forge_r4_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v4.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py",
        ):
            source = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("pip install", source)
            self.assertNotIn("snapshot_download(", source)
            self.assertNotIn("requests.get(", source)
            self.assertNotIn("import torch", source)
            self.assertNotIn("import qwen", source)


if __name__ == "__main__":
    unittest.main()
