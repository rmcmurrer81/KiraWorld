"""Hostile static/mocked regressions for the append-only inert R3 repair."""

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
from unittest import mock

from tools import qwen3_tts_original_voice_forge_worker_v3 as worker_v3
from tools import qwen3_tts_voice_forge_r3_guards as guards
from tools import run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3 as runner_v3


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded_sha256(value: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode("ascii")
    return "sha256=" + encoded.rstrip("=")


def write_wav(path: Path, *, frequency: float = 220.0, frames: int = 1600, rate: int = 16000) -> None:
    samples = [int(7000 * math.sin(2 * math.pi * frequency * index / rate)) for index in range(frames)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(struct.pack(f"<{len(samples)}h", *samples))


class FakePromptRuntime:
    def __init__(self) -> None:
        self.reference_seen = None
        self.created_prompt = None
        self.generation_prompt = None

    def create_prompt(self, *, reference, reference_text):
        self.reference_seen = reference
        self.created_prompt = {
            "reference_text": reference_text,
            "rate": reference[1],
            "first_sample": reference[0][0],
            "vectors": [1.0, 2.0, 3.0],
        }
        return self.created_prompt

    def serialize_prompt(self, prompt):
        return json.dumps(prompt, sort_keys=True).encode("utf-8")

    def deserialize_prompt(self, payload):
        return json.loads(payload.decode("utf-8"))

    def generate_clone(self, *, text, language, prompt):
        self.generation_prompt = prompt
        return [0.1, -0.1, 0.2, -0.2], 24000


class CleanEvaluator:
    def __init__(self) -> None:
        self.calls = []

    def evaluate(self, path, **kwargs):
        self.calls.append(("evaluate", path, kwargs))
        return {"ok": True}

    def speaker_embedding(self, path):
        self.calls.append(("speaker_embedding", path))
        return {"embedding": [0.1, 0.2]}

    def import_provenance_evidence(self):
        self.calls.append(("import_provenance_evidence",))
        return {"ok": True}


class MutatingEvaluator(CleanEvaluator):
    def __init__(self, target: Path) -> None:
        super().__init__()
        self.target = target

    def evaluate(self, path, **kwargs):
        result = super().evaluate(path, **kwargs)
        write_wav(self.target, frequency=880.0)
        return result


class PromptAndArtifactTests(unittest.TestCase):
    def test_persisted_prompt_is_reloaded_and_only_reload_reaches_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            write_wav(attempt / "original_design_reference.wav")
            base = FakePromptRuntime()
            runtime = guards.PersistedPromptRuntime(base, attempt)
            original = runtime.create_prompt(reference=([99.0], 1), reference_text="reference")
            payload = runtime.serialize_prompt(original)
            (attempt / "runtime_clone_prompt.pt").write_bytes(payload)
            runtime.generate_clone(text="test", language="English", prompt=original)
            evidence = runtime.prompt_evidence()
            self.assertTrue(evidence["persisted_prompt_reload_used_for_generation"])
            self.assertFalse(evidence["in_memory_caller_prompt_used_for_generation"])
            self.assertIsNot(base.generation_prompt, original)
            self.assertEqual(base.generation_prompt, original)
            self.assertEqual(base.reference_seen[1], 16000)
            self.assertNotEqual(base.reference_seen[0][0], 99.0)
            self.assertEqual(evidence["sha256"], sha256_bytes(payload))
            self.assertEqual(
                evidence["created_prompt_semantic_sha256"],
                evidence["reloaded_prompt_semantic_sha256"],
            )

    def test_corrupt_persisted_prompt_fails_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            write_wav(attempt / "original_design_reference.wav")
            base = FakePromptRuntime()
            runtime = guards.PersistedPromptRuntime(base, attempt)
            prompt = runtime.create_prompt(reference=([], 0), reference_text="reference")
            runtime.serialize_prompt(prompt)
            (attempt / "runtime_clone_prompt.pt").write_bytes(b"NOT_A_VALID_PROMPT")
            with self.assertRaises(guards.R3GuardError):
                runtime.generate_clone(text="test", language="English", prompt=prompt)
            self.assertIsNone(base.generation_prompt)

    def test_semantically_substituted_prompt_fails_even_when_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            write_wav(attempt / "original_design_reference.wav")
            base = FakePromptRuntime()
            runtime = guards.PersistedPromptRuntime(base, attempt)
            prompt = runtime.create_prompt(reference=([], 0), reference_text="reference")
            runtime.serialize_prompt(prompt)
            substitute = dict(prompt)
            substitute["vectors"] = [9.0, 9.0, 9.0]
            (attempt / "runtime_clone_prompt.pt").write_text(json.dumps(substitute), encoding="utf-8")
            with self.assertRaises(guards.R3GuardError):
                runtime.generate_clone(text="test", language="English", prompt=prompt)

    def test_evaluator_mutation_is_detected_on_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            reference = attempt / "original_design_reference.wav"
            clone = attempt / "runtime_clone_test.wav"
            write_wav(reference)
            write_wav(clone, frequency=330.0)
            guarded = guards.EvaluatorMutationGuard(MutatingEvaluator(reference), attempt)
            with self.assertRaises(guards.R3GuardError):
                guarded.evaluate(reference, expected_text="x")

    def test_every_clean_evaluator_operation_gets_before_and_after_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            write_wav(attempt / "original_design_reference.wav")
            write_wav(attempt / "runtime_clone_test.wav", frequency=330.0)
            guarded = guards.EvaluatorMutationGuard(CleanEvaluator(), attempt)
            guarded.import_provenance_evidence()
            guarded.speaker_embedding(attempt / "original_design_reference.wav")
            guarded.evaluate(attempt / "runtime_clone_test.wav")
            evidence = guarded.final_evidence()
            self.assertEqual(len(evidence["checkpoints"]), 7)
            self.assertIn("before:import_provenance_evidence", evidence["checkpoints"])
            self.assertIn("after:evaluate", evidence["checkpoints"])
            self.assertEqual(evidence["checkpoints"][-1], "before_worker_acceptance")

    def test_post_worker_pre_parent_wav_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt = Path(tmp)
            reference = attempt / "original_design_reference.wav"
            clone = attempt / "runtime_clone_test.wav"
            prompt = attempt / "runtime_clone_prompt.pt"
            write_wav(reference)
            write_wav(clone, frequency=330.0)
            prompt.write_bytes(b"prompt")
            seals = {
                "reference_wav": guards.seal_pcm16_wav(reference, attempt),
                "clone_test_wav": guards.seal_pcm16_wav(clone, attempt),
                "runtime_clone_prompt": guards.seal_prompt_file(
                    prompt, attempt, "a" * 64
                ),
            }
            manifest = {
                "schema": "qwen3_tts_original_voice_forge_worker_manifest_v3",
                "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
                "artifact_seals": seals,
                "persisted_prompt_evidence": {
                    "persisted_prompt_reload_used_for_generation": True,
                    "in_memory_caller_prompt_used_for_generation": False,
                    "sha256": seals["runtime_clone_prompt"]["sha256"],
                    "reloaded_prompt_semantic_sha256": "a" * 64,
                },
            }
            profile = {"artifact_seals": seals}
            guards.validate_parent_artifacts(
                attempt_dir=attempt, worker_manifest=manifest, profile=profile
            )
            write_wav(clone, frequency=880.0)
            with self.assertRaises(guards.R3GuardError):
                guards.validate_parent_artifacts(
                    attempt_dir=attempt, worker_manifest=manifest, profile=profile
                )

    def test_silent_replacement_is_rejected_structurally(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.wav"
            with wave.open(str(path), "wb") as writer:
                writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000)
                writer.writeframes(struct.pack("<1600h", *([0] * 1600)))
            with self.assertRaises(guards.R3GuardError):
                guards.seal_pcm16_wav(path, Path(tmp))


def make_distribution(site: Path, name: str, version: str, module_payload: bytes) -> dict:
    canonical_dir = name.replace("-", "_")
    module = site / f"{canonical_dir}.py"
    root = site / f"{canonical_dir}-{version}.dist-info"
    root.mkdir(parents=True, exist_ok=True)
    module.write_bytes(module_payload)
    metadata = root / "METADATA"
    metadata.write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n", encoding="utf-8")
    record = root / "RECORD"
    rows = []
    for path in (module, metadata):
        rel = path.relative_to(site).as_posix()
        payload = path.read_bytes()
        rows.append([rel, encoded_sha256(payload), str(len(payload))])
    rows.append([record.relative_to(site).as_posix(), "", ""])
    with record.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)
    return {
        "name": name,
        "version": version,
        "module": module,
        "metadata_root": root,
        "record": record,
    }


def distribution_evidence(project: Path, dist: dict) -> dict:
    files = []
    site = dist["metadata_root"].parent
    for path in (dist["module"], dist["metadata_root"] / "METADATA", dist["record"]):
        files.append({
            "path": path.relative_to(project).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": guards.sha256_file(path),
        })
    return {
        "version": dist["version"],
        "record_path": dist["record"].relative_to(project).as_posix(),
        "record_sha256": guards.sha256_file(dist["record"]),
        "installed_files": files,
    }


def write_inventory(project: Path, site: Path, distributions, ownership_overrides=None):
    ownership_overrides = ownership_overrides or {}
    distribution_rows = []
    owners_by_path = {}
    for dist in distributions:
        evidence = distribution_evidence(project, dist)
        distribution_rows.append({
            "name": dist["name"], "version": dist["version"],
            "record_path": evidence["record_path"],
            "record_sha256": evidence["record_sha256"],
        })
        for path in (dist["module"], dist["metadata_root"] / "METADATA", dist["record"]):
            owners_by_path[path.relative_to(site).as_posix()] = [dist["name"]]
    file_rows = []
    for path in sorted(item for item in site.rglob("*") if item.is_file()):
        rel = path.relative_to(site).as_posix()
        owners = ownership_overrides.get(rel, owners_by_path.get(rel, []))
        file_rows.append({
            "path": rel, "bytes": path.stat().st_size,
            "sha256": guards.sha256_file(path),
            "owner_distributions": owners,
            "loose_unowned_file": not owners,
        })
    manifest = project / "inventory.json"
    manifest.write_text(json.dumps({
        "schema": "qwen3_tts_complete_site_packages_inventory_v2",
        "status": "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY",
        "complete_file_inventory": True,
        "site_packages_root": site.relative_to(project).as_posix(),
        "distributions": distribution_rows,
        "files": file_rows,
    }, indent=2), encoding="utf-8")
    spec = {"site_packages_inventory": {
        "manifest_path": manifest.relative_to(project).as_posix(),
        "manifest_sha256": guards.sha256_file(manifest),
    }}
    return spec


class DistributionEnumerationTests(unittest.TestCase):
    def test_omitted_dist_info_cannot_be_relabelled_loose(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            site = project / venv_rel / "Lib/site-packages"
            site.mkdir(parents=True)
            accepted = make_distribution(site, "accepted", "1.0", b"accepted=1\n")
            omitted = make_distribution(site, "omitteddep", "1.0", b"omitted=1\n")
            overrides = {
                path.relative_to(site).as_posix(): []
                for path in (omitted["module"], omitted["metadata_root"] / "METADATA", omitted["record"])
            }
            spec = write_inventory(project, site, [accepted], overrides)
            evidence = {"accepted": distribution_evidence(project, accepted)}
            with self.assertRaises(guards.R3GuardError):
                guards.verify_authoritative_distribution_inventory(
                    project_root=project, isolated_venv_rel=venv_rel, spec=spec,
                    distribution_evidence=evidence,
                    base_verifier=lambda **kwargs: {"base": True},
                    base_verifier_style="worker",
                )

    def test_complete_one_to_one_dist_info_inventory_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            site = project / venv_rel / "Lib/site-packages"
            site.mkdir(parents=True)
            first = make_distribution(site, "first", "1.0", b"first=1\n")
            second = make_distribution(site, "second-dep", "2.0", b"second=2\n")
            spec = write_inventory(project, site, [first, second])
            evidence = {
                "first": distribution_evidence(project, first),
                "second-dep": distribution_evidence(project, second),
            }
            result = guards.verify_authoritative_distribution_inventory(
                project_root=project, isolated_venv_rel=venv_rel, spec=spec,
                distribution_evidence=evidence,
                base_verifier=lambda **kwargs: {"base": True},
                base_verifier_style="worker",
            )
            self.assertTrue(result["claimed_transitive_distribution_completeness_proven"])
            self.assertEqual(result["enumerated_distribution_count"], 2)

    def test_dist_info_files_marked_loose_fail_even_when_distribution_declared(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            site = project / venv_rel / "Lib/site-packages"
            site.mkdir(parents=True)
            dist = make_distribution(site, "declared", "1.0", b"x=1\n")
            overrides = {
                (dist["metadata_root"] / "METADATA").relative_to(site).as_posix(): []
            }
            spec = write_inventory(project, site, [dist], overrides)
            with self.assertRaises(guards.R3GuardError):
                guards.verify_authoritative_distribution_inventory(
                    project_root=project, isolated_venv_rel=venv_rel, spec=spec,
                    distribution_evidence={"declared": distribution_evidence(project, dist)},
                    base_verifier=lambda **kwargs: {"base": True},
                    base_verifier_style="worker",
                )


def build_wheel(project: Path, package: str, version: str, payloads: dict[str, bytes]) -> tuple[Path, dict]:
    root = project / "wheel_evidence"
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{package}-{version}-cp311-cp311-win_amd64.whl"
    wheel = root / filename
    dist = package.replace("-", "_") + f"-{version}.dist-info"
    members = dict(payloads)
    members[f"{dist}/METADATA"] = f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n".encode()
    members[f"{dist}/WHEEL"] = b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp311-cp311-win_amd64\n"
    record_name = f"{dist}/RECORD"
    rows = [[name, encoded_sha256(payload), str(len(payload))] for name, payload in members.items()]
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
        "wheel_sha256": guards.sha256_file(wheel),
        "installer_generated_files": [],
    }
    return wheel, row


def install_wheel_members(project: Path, venv_rel: Path, wheel: Path, wheel_evidence: dict) -> dict:
    site = project / venv_rel / "Lib/site-packages"
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel, "r") as archive:
        archive.extractall(site)
    rows = []
    for path in sorted(item for item in site.rglob("*") if item.is_file()):
        rows.append({
            "path": path.relative_to(project).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": guards.sha256_file(path),
        })
    record = site / wheel_evidence["record_path"]
    return {
        "version": wheel_evidence["version"],
        "record_path": record.relative_to(project).as_posix(),
        "record_sha256": guards.sha256_file(record),
        "installed_files": rows,
    }


class WheelBindingTests(unittest.TestCase):
    def test_metadata_only_torch_wheel_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _wheel, row = build_wheel(project, "torch", "2.11.0+cu130", {})
            with self.assertRaises(guards.R3GuardError):
                guards.attest_wheel_archive(
                    project_root=project, wheel_root_rel=Path("wheel_evidence"),
                    package="torch", row=row,
                )

    def test_wrong_package_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _wheel, row = build_wheel(project, "torch", "2.11.0+cu130", {
                "torch_fake/__init__.py": b"fake\n",
                "torch_fake/_C.cp311-win_amd64.pyd": b"fake-pyd",
            })
            with self.assertRaises(guards.R3GuardError):
                guards.attest_wheel_archive(
                    project_root=project, wheel_root_rel=Path("wheel_evidence"),
                    package="torch", row=row,
                )

    def test_real_payload_wheel_binds_every_installed_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            wheel, row = build_wheel(project, "torch", "2.11.0+cu130", {
                "torch/__init__.py": b"__version__='2.11.0'\n",
                "torch/_C.cp311-win_amd64.pyd": b"real-compiled-payload",
                "torch/core.py": b"CORE=1\n",
            })
            wheel_evidence = guards.attest_wheel_archive(
                project_root=project, wheel_root_rel=Path("wheel_evidence"),
                package="torch", row=row,
            )
            installed = install_wheel_members(project, venv_rel, wheel, wheel_evidence)
            binding = guards.bind_wheel_to_installed_distribution(
                project_root=project, isolated_venv_rel=venv_rel,
                package="torch", row=row, installed_evidence=installed,
                wheel_evidence=wheel_evidence,
            )
            self.assertTrue(binding["exact_wheel_to_installed_record_and_files_bound"])
            self.assertGreater(binding["wheel_members_bound_to_installed_files"], 0)

    def test_same_name_version_different_installed_torch_code_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            wheel, row = build_wheel(project, "torch", "2.11.0+cu130", {
                "torch/__init__.py": b"ORIGINAL=1\n",
                "torch/_C.cp311-win_amd64.pyd": b"real-compiled-payload",
            })
            wheel_evidence = guards.attest_wheel_archive(
                project_root=project, wheel_root_rel=Path("wheel_evidence"),
                package="torch", row=row,
            )
            installed = install_wheel_members(project, venv_rel, wheel, wheel_evidence)
            changed = project / venv_rel / "Lib/site-packages/torch/__init__.py"
            changed.write_bytes(b"SUBSTITUTED=1\n")
            for evidence_row in installed["installed_files"]:
                if evidence_row["path"].endswith("torch/__init__.py"):
                    evidence_row["bytes"] = changed.stat().st_size
                    evidence_row["sha256"] = guards.sha256_file(changed)
            with self.assertRaises(guards.R3GuardError):
                guards.bind_wheel_to_installed_distribution(
                    project_root=project, isolated_venv_rel=venv_rel,
                    package="torch", row=row, installed_evidence=installed,
                    wheel_evidence=wheel_evidence,
                )

    def test_undeclared_installer_generated_difference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_rel = Path("sidecar/.venv")
            wheel, row = build_wheel(project, "torchaudio", "2.11.0+cu130", {
                "torchaudio/__init__.py": b"AUDIO=1\n",
                "torchaudio/_torchaudio.cp311-win_amd64.pyd": b"compiled-audio",
            })
            wheel_evidence = guards.attest_wheel_archive(
                project_root=project, wheel_root_rel=Path("wheel_evidence"),
                package="torchaudio", row=row,
            )
            installed = install_wheel_members(project, venv_rel, wheel, wheel_evidence)
            extra = project / venv_rel / "Lib/site-packages/torchaudio/__pycache__/x.pyc"
            extra.parent.mkdir(parents=True)
            extra.write_bytes(b"bytecode")
            installed["installed_files"].append({
                "path": extra.relative_to(project).as_posix(), "bytes": extra.stat().st_size,
                "sha256": guards.sha256_file(extra),
            })
            with self.assertRaises(guards.R3GuardError):
                guards.bind_wheel_to_installed_distribution(
                    project_root=project, isolated_venv_rel=venv_rel,
                    package="torchaudio", row=row, installed_evidence=installed,
                    wheel_evidence=wheel_evidence,
                )


class StaticInertnessAndPreservationTests(unittest.TestCase):
    def test_fresh_r3_manifest_blocks_worker_and_parent_execution(self):
        with self.assertRaises(worker_v3.R3ForgeError):
            worker_v3.verify_r3_harness(PROJECT_ROOT)
        with self.assertRaises(runner_v3.R3LauncherError):
            runner_v3.verify_r3_harness()

    def test_r3_manifest_inventory_is_exact_before_audit(self):
        manifest_path = PROJECT_ROOT / "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT")
        self.assertFalse(manifest["execution_allowed"])
        self.assertEqual(len(manifest["files"]), 14)
        for row in manifest["files"]:
            path = PROJECT_ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"], row["path"])
            self.assertEqual(guards.sha256_file(path), row["sha256"], row["path"])

    def test_runner_is_inert_without_execute(self):
        args = argparse.Namespace(
            execute=False, bundle_id=None, acknowledge_private_unreviewed=False,
            acknowledge_no_download=False,
        )
        with self.assertRaises(runner_v3.R3LauncherError):
            runner_v3.run(args)

    def test_worker_is_inert_without_acknowledgement(self):
        with self.assertRaises(worker_v3.R3ForgeError):
            worker_v3.main([])

    def test_r2_frozen_principal_hashes_are_unchanged(self):
        expected = {
            "tools/qwen3_tts_original_voice_forge_worker_v2.py": "b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py": "88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45",
            "Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.py": "7bc62d1ca1976354bbca7d838c1c0c6f0af3fcb9860508f91ff756122f285972",
            "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json": "682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4",
        }
        for rel, digest in expected.items():
            self.assertEqual(guards.sha256_file(PROJECT_ROOT / rel), digest, rel)

    def test_attempt_02_audit_is_preserved(self):
        path = PROJECT_ROOT / "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_REPAIRED_INDEPENDENT_AUDIT_ATTEMPT_02_20260809.md"
        self.assertTrue(path.is_file())
        self.assertEqual(
            guards.sha256_file(path),
            "304f28d06cd37e45693dd88206a7979cde5c8e7cf729c33cf9dc36e2e59bad00",
        )

    def test_source_has_no_install_download_or_model_execution_at_import(self):
        for rel in (
            "tools/qwen3_tts_voice_forge_r3_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v3.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py",
        ):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("pip install", text)
            self.assertNotIn("snapshot_download(", text)
            self.assertNotIn("requests.get(", text)


if __name__ == "__main__":
    unittest.main()
