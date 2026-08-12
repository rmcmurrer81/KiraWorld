"""Append-only inert R3 worker for TemporaryAI original expert voices.

R3 reuses the frozen R2 implementation only after an independently accepted
R3 manifest has sealed both it and the R3 guards.  It adds persisted-prompt
reload/use proof, evaluator mutation guards, authoritative distribution
enumeration, and exact wheel-to-installed-file binding.  It performs no work
without the parent reservation and explicit acknowledgement.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R3_MANIFEST_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json")
R3_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v3.py")
R3_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r3_guards.py")
R2_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v2.py")
R3_OUTPUT_ROOT_REL = Path("Voice/voice_forge/private_review_v3")
R3_FAILURE_STATUS = "FAILED_TEXT_PLUS_SILENCE_ONLY"


class R3ForgeError(RuntimeError):
    """The append-only R3 worker failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise R3ForgeError(f"cannot read trusted JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R3ForgeError(f"trusted JSON is not an object: {path}")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
                + b"\n"
            )
    except FileExistsError as exc:
        raise R3ForgeError(f"append-only R3 evidence already exists: {path}") from exc


def verify_r3_harness(project_root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = (project_root / R3_MANIFEST_REL).resolve()
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "qwen3_tts_voice_forge_harness_manifest_v3"
        or manifest.get("status") != "INDEPENDENT_AUDIT_ACCEPTED_FOR_ONE_BOUNDED_RUN"
        or manifest.get("execution_allowed") is not True
    ):
        raise R3ForgeError("R3 harness has not passed a fresh independent audit")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R3ForgeError("R3 manifest file inventory is invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("path") or ""):
            raise R3ForgeError("R3 manifest row is invalid")
        rel = str(row["path"])
        if rel in indexed:
            raise R3ForgeError("R3 manifest path is duplicated")
        path = (project_root / rel).resolve()
        try:
            path.relative_to(project_root.resolve())
        except ValueError as exc:
            raise R3ForgeError("R3 manifest path escaped the project") from exc
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or sha256_file(path) != row.get("sha256")
        ):
            raise R3ForgeError(f"R3 manifest file drift: {rel}")
        indexed[rel] = row
    required = {
        R3_WORKER_REL.as_posix(),
        R3_GUARDS_REL.as_posix(),
        R2_WORKER_REL.as_posix(),
        "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json",
        "Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json",
        "Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json",
        "Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json",
    }
    if not required.issubset(indexed):
        raise R3ForgeError("R3 manifest omits a controlling predecessor or repair file")
    return manifest, indexed


def load_sealed_module(
    *, project_root: Path, rel: Path, row: dict[str, Any], module_name: str
) -> Any:
    path = (project_root / rel).resolve()
    if path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
        raise R3ForgeError(f"sealed module changed before import: {rel.as_posix()}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise R3ForgeError(f"cannot load sealed module: {rel.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != path or sha256_file(path) != row.get("sha256"):
        raise R3ForgeError(f"sealed module origin/hash changed after import: {rel.as_posix()}")
    return module


def install_r3_preimport_guards(v2: Any, guards: Any) -> None:
    """Replace only the two rejected R2 environment proof functions."""

    original_site = v2.verify_complete_site_packages_inventory

    def site_guard(*, project_root: Path, spec: dict[str, Any], distribution_evidence: dict[str, Any]) -> dict[str, Any]:
        return guards.verify_authoritative_distribution_inventory(
            project_root=project_root,
            isolated_venv_rel=v2.ISOLATED_VENV_REL,
            spec=spec,
            distribution_evidence=distribution_evidence,
            base_verifier=original_site,
            base_verifier_style="worker",
        )

    def wheel_payload_guard(*, project_root: Path, package: str, row: dict[str, Any]) -> dict[str, Any]:
        return guards.attest_wheel_archive(
            project_root=project_root,
            wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
            package=package,
            row=row,
        )

    v2.verify_complete_site_packages_inventory = site_guard
    v2.verify_wheel_archive = wheel_payload_guard
    v2.HARNESS_MANIFEST_REL = R3_MANIFEST_REL
    v2.WORKER_REL = R3_WORKER_REL
    v2.OUTPUT_ROOT_REL = R3_OUTPUT_ROOT_REL


def make_runtime_class(v2: Any, guards: Any) -> type:
    class OfficialRuntimeR3(v2.OfficialRuntimeV2):
        def load_reference_prompt_audio(self, path: Path) -> tuple[Any, int]:
            waveform, rate = self.torchaudio.load(str(path))
            if int(waveform.shape[0]) != 1 or int(waveform.shape[1]) <= 0:
                raise R3ForgeError("saved prompt reference did not reload as nonempty mono audio")
            return waveform[0].detach().cpu(), int(rate)

        def deserialize_prompt(self, payload: bytes) -> Any:
            if self.torch is None:
                raise R3ForgeError("Torch is unavailable for trusted prompt reload")
            return self.torch.load(
                io.BytesIO(payload), map_location="cpu", weights_only=False
            )

        def _exact_wheel_bindings(
            self, spec: dict[str, Any], project_root: Path, evidence: dict[str, Any]
        ) -> dict[str, Any]:
            bindings: dict[str, Any] = {}
            for package in ("torch", "torchaudio"):
                wheel = guards.attest_wheel_archive(
                    project_root=project_root,
                    wheel_root_rel=v2.WHEEL_EVIDENCE_ROOT_REL,
                    package=package,
                    row=spec["distributions"][package],
                )
                bindings[package] = guards.bind_wheel_to_installed_distribution(
                    project_root=project_root,
                    isolated_venv_rel=v2.ISOLATED_VENV_REL,
                    package=package,
                    row=spec["distributions"][package],
                    installed_evidence=evidence["distributions"][package],
                    wheel_evidence=wheel,
                )
            return bindings

        def environment_evidence(self, spec: dict[str, Any], project_root: Path) -> dict[str, Any]:
            evidence = super().environment_evidence(spec, project_root)
            evidence["exact_wheel_to_installed_bindings"] = self._exact_wheel_bindings(
                spec, project_root, evidence
            )
            evidence["r3_four_blocker_preflight"] = True
            return evidence

        def post_execution_provenance(
            self, spec: dict[str, Any], project_root: Path
        ) -> dict[str, Any]:
            evidence = super().post_execution_provenance(spec, project_root)
            records = {
                package: v2.verify_installed_distribution(
                    project_root=project_root, package=package, row=row
                )
                for package, row in sorted(spec["distributions"].items())
            }
            distribution_wrapper = {"distributions": records}
            evidence["exact_wheel_to_installed_bindings_reverified"] = self._exact_wheel_bindings(
                spec, project_root, distribution_wrapper
            )
            evidence["r3_four_blocker_postflight"] = True
            return evidence

    OfficialRuntimeR3.__name__ = "OfficialRuntimeR3"
    return OfficialRuntimeR3


def execute_r3(
    *, project_root: Path, bundle_id: str, attempt_dir: Path,
    v2: Any, guards: Any,
) -> dict[str, Any]:
    trusted = v2.load_trusted_bundle(project_root, bundle_id, require_ready_environment=True)
    reservation = read_json(attempt_dir / "parent_reservation.json")
    if (
        reservation.get("verified_entry_worker_path") != R3_WORKER_REL.as_posix()
        or reservation.get("verified_entry_worker_sha256")
        != sha256_file(project_root / R3_WORKER_REL)
        or reservation.get("verified_frozen_core_worker_path")
        != R2_WORKER_REL.as_posix()
        or reservation.get("verified_frozen_core_worker_sha256")
        != sha256_file(project_root / R2_WORKER_REL)
    ):
        raise R3ForgeError("parent reservation did not bind the R3 entry worker and frozen R2 core")
    runtime_holder: dict[str, Any] = {}
    evaluator_holder: dict[str, Any] = {}
    RuntimeR3 = make_runtime_class(v2, guards)

    def runtime_factory() -> Any:
        proxy = guards.PersistedPromptRuntime(RuntimeR3(), attempt_dir)
        runtime_holder["runtime"] = proxy
        return proxy

    def evaluator_factory(environment: dict[str, Any], root: Path) -> Any:
        proxy = guards.EvaluatorMutationGuard(
            v2.OfficialSpeechEvaluatorV2(environment, root), attempt_dir
        )
        evaluator_holder["evaluator"] = proxy
        return proxy

    result = v2.execute_verified_bundle(
        trusted=trusted,
        attempt_dir=attempt_dir,
        runtime_factory=runtime_factory,
        evaluator_factory=evaluator_factory,
        identity_analyzer_factory=v2.OfficialIdentityAnalyzerV2,
    )
    runtime = runtime_holder.get("runtime")
    evaluator = evaluator_holder.get("evaluator")
    if runtime is None or evaluator is None:
        raise R3ForgeError("R3 runtime/evaluator guards were not exercised")
    prompt_evidence = runtime.prompt_evidence()
    evaluator_evidence = evaluator.final_evidence()
    seals = {
        **evaluator_evidence["artifact_seals"],
        "runtime_clone_prompt": prompt_evidence["artifact_seal"],
    }
    guards.verify_final_artifact_set(attempt_dir, seals)

    predecessor_profile_path = attempt_dir / "voice_profile_candidate_v2.json"
    predecessor_manifest_path = attempt_dir / "worker_manifest_v2.json"
    predecessor_profile = read_json(predecessor_profile_path)
    predecessor_manifest = read_json(predecessor_manifest_path)
    if (
        predecessor_profile.get("status")
        != "PRIVATE_UNREVIEWED_ENGINEERING_PASS_OWNER_HEARING_PENDING"
        or predecessor_manifest.get("status")
        != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT"
    ):
        raise R3ForgeError("frozen R2 core did not pass before R3 sealing")
    for label, artifact in (
        ("reference_wav", predecessor_profile["artifacts"]["reference_wav"]),
        ("clone_test_wav", predecessor_profile["artifacts"]["clone_test_wav"]),
    ):
        if artifact.get("sha256") != seals[label]["sha256"]:
            raise R3ForgeError("R2 core artifact hash differs from final R3 seal")
    if predecessor_profile["artifacts"].get("clone_prompt_sha256") != seals["runtime_clone_prompt"]["sha256"]:
        raise R3ForgeError("R2 core prompt hash differs from final persisted prompt")

    profile = {
        **predecessor_profile,
        "schema": "qwen3_tts_original_voice_profile_candidate_v3",
        "r3_repair_status": "FOUR_REPRODUCED_ATTEMPT_02_BLOCKERS_CLOSED_STATICALLY",
        "predecessor_profile_sha256": sha256_file(predecessor_profile_path),
        "artifact_seals": seals,
        "persisted_prompt_evidence": prompt_evidence,
        "evaluator_mutation_guard": evaluator_evidence,
        "assignment_allowed": False,
        "activation_allowed": False,
        "publication_or_upload_allowed": False,
        "owner_hearing_acceptance": "PENDING",
        "independent_audit": "REQUIRED",
    }
    profile_path = attempt_dir / "voice_profile_candidate_v3.json"
    write_new_json(profile_path, profile)
    guards.verify_final_artifact_set(attempt_dir, seals)

    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v3",
        "status": "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT",
        "bundle_id": trusted.bundle["bundle_id"],
        "candidate_id": trusted.bundle["candidate_id"],
        "opaque_voice_id": trusted.bundle["opaque_voice_id"],
        "private_append_only": True,
        "single_use_nonce_consumed": True,
        "predecessor_worker_manifest_sha256": sha256_file(predecessor_manifest_path),
        "predecessor_result_sha256": result["manifest_sha256"],
        "profile_sha256": sha256_file(profile_path),
        "artifact_seals": seals,
        "persisted_prompt_evidence": prompt_evidence,
        "evaluator_mutation_guard": evaluator_evidence,
        "authoritative_distribution_enumeration": True,
        "exact_torch_and_torchaudio_wheel_to_installed_binding": True,
        "owner_hearing_acceptance": "PENDING",
        "independent_audit": "REQUIRED",
        "watermark_status": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
        "network_boundary": "OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL",
        "network_nonuse_proven": False,
        "activation_assignment_publication_or_upload_allowed": False,
        "failure_policy": R3_FAILURE_STATUS,
        "clean_worker_exit": "PARENT_MUST_CONFIRM_AFTER_EXIT",
    }
    manifest_path = attempt_dir / "worker_manifest_v3.json"
    write_new_json(manifest_path, manifest)
    guards.verify_final_artifact_set(attempt_dir, seals)
    return {
        "status": manifest["status"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "profile_path": str(profile_path),
        "profile_sha256": sha256_file(profile_path),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--attempt-dir")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute or not args.acknowledge_private_unreviewed:
        raise R3ForgeError("R3 worker is inert without exact execution acknowledgement")
    if not args.bundle_id or not args.attempt_dir:
        raise R3ForgeError("bundle ID and parent-reserved attempt are required")
    _manifest, indexed = verify_r3_harness(PROJECT_ROOT)
    guards = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R3_GUARDS_REL,
        row=indexed[R3_GUARDS_REL.as_posix()],
        module_name="qwen3_tts_voice_forge_r3_guards_sealed",
    )
    v2 = load_sealed_module(
        project_root=PROJECT_ROOT,
        rel=R2_WORKER_REL,
        row=indexed[R2_WORKER_REL.as_posix()],
        module_name="qwen3_tts_original_voice_forge_worker_v2_sealed_for_r3",
    )
    install_r3_preimport_guards(v2, guards)
    result = execute_r3(
        project_root=PROJECT_ROOT,
        bundle_id=args.bundle_id,
        attempt_dir=Path(args.attempt_dir).resolve(),
        v2=v2,
        guards=guards,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R3 Qwen3-TTS forge failed closed: {exc}", file=sys.stderr)
        if not isinstance(exc, (R3ForgeError, SystemExit)):
            traceback.print_exc()
        raise SystemExit(2)
