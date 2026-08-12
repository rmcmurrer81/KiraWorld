"""Inert R7 worker for the TemporaryAI Qwen3-TTS original voice forge.

The exact R7 static audit decision is verified by the sealed R7 guard before
the append-only one-use worker claim.  Only after that claim may this future
worker load the sealed R6 predecessor graph.  The shipped R7 authorization is
disabled, so the sealed file cannot start a real run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import types
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R7_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json")
R7_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r7_guards.py")
R7_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v7.py")
R7_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py")
R6_PAYLOAD_REL = Path("TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json")
R6_GUARDS_REL = Path("tools/qwen3_tts_voice_forge_r6_guards.py")
R6_WORKER_REL = Path("tools/qwen3_tts_original_voice_forge_worker_v6.py")
R6_RUNNER_REL = Path("tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py")
R6_AUDIT_REL = Path(
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_20260810.md"
)
R6_AUDIT_SHA256 = "9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10"
R2_CORPUS_REL = Path("Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json")
RESERVATION_ROOT_REL = Path("Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v7")
HASH = re.compile(r"[0-9a-f]{64}")

R7_ADDITIONAL_PAYLOADS = {
    R6_PAYLOAD_REL.as_posix(),
    R6_AUDIT_REL.as_posix(),
    R7_GUARDS_REL.as_posix(),
    R7_WORKER_REL.as_posix(),
    R7_RUNNER_REL.as_posix(),
    "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_REPAIR_BOUNDARY_20260810.md",
}


class R7ForgeError(RuntimeError):
    """The R7 worker failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise R7ForgeError(f"duplicate R7 bootstrap JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise R7ForgeError(f"non-finite R7 bootstrap JSON constant: {value}")


def _object(path: Path, expected_hash: str | None, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise R7ForgeError(f"{label} is missing or unsafe")
    payload = path.read_bytes()
    if expected_hash is not None and (
        not HASH.fullmatch(str(expected_hash or "")) or sha256_bytes(payload) != expected_hash
    ):
        raise R7ForgeError(f"{label} differs from its exact hash")
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant
        )
    except R7ForgeError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise R7ForgeError(f"{label} is not strict finite UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise R7ForgeError(f"{label} is not an object")
    return value


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R7ForgeError("R7 worker path escaped project") from exc


def _load_sealed_module(rel: Path, row: dict[str, Any], name: str) -> Any:
    path = (PROJECT_ROOT / rel).resolve()
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != row.get("bytes")
        or sha256_file(path) != row.get("sha256")
    ):
        raise R7ForgeError(f"R7 sealed dependency drift: {rel.as_posix()}")
    source = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
    if sha256_file(path) != row.get("sha256"):
        raise R7ForgeError(f"R7 dependency changed during import: {rel.as_posix()}")
    return module


def _bootstrap_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = _object(PROJECT_ROOT / R7_PAYLOAD_REL, args.payload_manifest_sha256, "R7 worker payload")
    if (
        set(manifest)
        != {
            "schema", "status", "execution_allowed", "self_authorization_allowed",
            "revision", "predecessor_payload_manifest_path",
            "predecessor_payload_manifest_sha256", "rejected_r6_audit_path",
            "rejected_r6_audit_sha256", "files",
        }
        or manifest.get("schema") != "qwen3_tts_voice_forge_payload_manifest_v7"
        or manifest.get("status")
        != "IMMUTABLE_STATIC_PAYLOAD_REQUIRES_FRESH_INDEPENDENT_AUDIT_AND_EXTERNAL_AUTHORIZATION"
        or manifest.get("execution_allowed") is not False
        or manifest.get("self_authorization_allowed") is not False
        or manifest.get("predecessor_payload_manifest_path") != R6_PAYLOAD_REL.as_posix()
        or manifest.get("rejected_r6_audit_path") != R6_AUDIT_REL.as_posix()
        or manifest.get("rejected_r6_audit_sha256") != R6_AUDIT_SHA256
        or sha256_file(PROJECT_ROOT / R6_AUDIT_REL) != R6_AUDIT_SHA256
    ):
        raise R7ForgeError("R7 worker payload is self-authorizing or unbound")
    predecessor = _object(PROJECT_ROOT / R6_PAYLOAD_REL, manifest["predecessor_payload_manifest_sha256"], "R7 predecessor payload")
    predecessor_paths = {row["path"] for row in predecessor.get("files", [])}
    required = predecessor_paths | R7_ADDITIONAL_PAYLOADS
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise R7ForgeError("R7 worker payload inventory is not a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise R7ForgeError("R7 worker payload row is not exact")
        rel = str(row.get("path") or "")
        path = (PROJECT_ROOT / rel).resolve()
        if rel in indexed or rel not in required or rel == R7_PAYLOAD_REL.as_posix() or _relative(path) != rel:
            raise R7ForgeError("R7 worker payload row is duplicate, unexpected, or unsafe")
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != row.get("bytes")
            or not HASH.fullmatch(str(row.get("sha256") or ""))
            or sha256_file(path) != row.get("sha256")
        ):
            raise R7ForgeError(f"R7 worker payload drift: {rel}")
        indexed[rel] = row
    if set(indexed) != required:
        raise R7ForgeError("R7 worker payload inventory is not the exact sealed closure")
    return manifest, indexed


def bootstrap_external_trust(
    args: argparse.Namespace,
) -> tuple[Any, dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Use the one sealed R7 validator before any predecessor import."""

    manifest, indexed = _bootstrap_payload(args)
    r7 = _load_sealed_module(R7_GUARDS_REL, indexed[R7_GUARDS_REL.as_posix()], "qwen3_tts_r7_worker_guards")
    verified_manifest, verified_indexed = r7.verify_payload_manifest(
        project_root=PROJECT_ROOT,
        expected_manifest_sha256=args.payload_manifest_sha256,
        required_payloads=set(indexed),
    )
    authorization, evidence = r7.verify_execution_authorization(
        project_root=PROJECT_ROOT,
        authorization_path=Path(args.execution_authorization),
        expected_authorization_sha256=args.execution_authorization_sha256,
        expected_manifest_sha256=args.payload_manifest_sha256,
        expected_inventory_sha256=r7.payload_inventory_sha256(verified_manifest),
        bundle_id=args.bundle_id,
        run_id=args.run_id,
    )
    return r7, verified_indexed, authorization, evidence, verified_manifest


def canonical_worker_command(r7: Any, args: argparse.Namespace) -> list[str]:
    return [
        str(Path(sys.executable).resolve()), "-I", "-B", str((PROJECT_ROOT / R7_WORKER_REL).resolve()),
        "--execute", "--acknowledge-private-unreviewed", "--bundle-id", args.bundle_id,
        "--run-id", args.run_id, "--pending-dir", str(Path(args.pending_dir).resolve()),
        "--payload-manifest-sha256", args.payload_manifest_sha256,
        "--execution-authorization", str(Path(args.execution_authorization).resolve()),
        "--execution-authorization-sha256", args.execution_authorization_sha256,
    ]


def bootstrap_claim_before_predecessor_import(
    args: argparse.Namespace, r7: Any, authorization: dict[str, Any], indexed: dict[str, dict[str, Any]]
) -> tuple[Path, dict[str, Any], str, dict[str, Any], str]:
    pending = Path(args.pending_dir).resolve()
    if not pending.is_dir() or pending.is_symlink():
        raise R7ForgeError("R7 pending attempt is missing or unsafe")
    command_sha = r7.canonical_sha256(canonical_worker_command(r7, args))
    reservation_path = PROJECT_ROOT / RESERVATION_ROOT_REL / f"{args.execution_authorization_sha256}.json"
    reservation = r7.strict_read_json(reservation_path, label="R7 parent reservation")
    reservation_sha = sha256_file(reservation_path)
    expected_reservation = {
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": _relative(pending),
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "execution_authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "independent_audit_decision_sha256": authorization["independent_audit_decision_sha256"],
        "independent_audit_subject_sha256": authorization["independent_audit_subject_sha256"],
        "independent_auditor_identity_sha256": authorization["independent_auditor_identity_sha256"],
        "independent_audit_report_sha256": authorization["independent_audit_sha256"],
        "generation_seed": authorization["generation_seed"],
        "parent_authorization_ledger_path": (
            r7.R7_PARENT_LEDGER_ROOT_REL
            / f"{args.execution_authorization_sha256}.json"
        ).as_posix(),
        "verified_entry_worker_path": R7_WORKER_REL.as_posix(),
        "verified_entry_worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": command_sha,
    }
    r7.validate_parent_reservation(reservation, expected=expected_reservation)
    ledger_path = (PROJECT_ROOT / reservation["parent_authorization_ledger_path"]).resolve()
    ledger = r7.strict_read_json(ledger_path, label="R7 parent ledger")
    ledger_sha = sha256_file(ledger_path)
    expected_ledger = {
        "authorization_sha256": args.execution_authorization_sha256,
        "authorization_nonce_sha256": authorization["authorization_nonce_sha256"],
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "independent_audit_decision_sha256": authorization["independent_audit_decision_sha256"],
        "independent_audit_subject_sha256": authorization["independent_audit_subject_sha256"],
        "independent_auditor_identity_sha256": authorization["independent_auditor_identity_sha256"],
        "independent_audit_report_sha256": authorization["independent_audit_sha256"],
        "payload_manifest_sha256": args.payload_manifest_sha256,
        "bundle_id": args.bundle_id,
        "run_id": args.run_id,
        "attempt": _relative(pending),
        "parent_reservation_path": _relative(reservation_path),
        "parent_reservation_sha256": reservation_sha,
        "verified_worker_path": R7_WORKER_REL.as_posix(),
        "verified_worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": command_sha,
    }
    r7.validate_parent_ledger(ledger, expected=expected_ledger)
    claim = {
        "schema": "qwen3_tts_voice_forge_worker_launch_claim_v7",
        "status": "WORKER_CLAIMED_ONE_USE_BEFORE_PREDECESSOR_OR_MODEL_IMPORT",
        "utc": r7.utc_now(),
        **{key: value for key, value in expected_ledger.items() if key not in {"verified_worker_path", "verified_worker_sha256", "worker_command_sha256"}},
        "parent_ledger_path": _relative(ledger_path),
        "parent_ledger_sha256": ledger_sha,
        "worker_path": R7_WORKER_REL.as_posix(),
        "worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": command_sha,
        "worker_pid": os.getpid(),
    }
    claim_path, claim_sha = r7.create_worker_launch_claim(
        project_root=PROJECT_ROOT,
        authorization_sha256=args.execution_authorization_sha256,
        claim=claim,
    )
    return claim_path, claim, claim_sha, ledger, ledger_sha


def claim_then_load_predecessors(
    *, args: argparse.Namespace, r7: Any, authorization: dict[str, Any], indexed: dict[str, dict[str, Any]], loader: Callable[[], Any]
) -> tuple[Any, tuple[Path, dict[str, Any], str, dict[str, Any], str]]:
    claim = bootstrap_claim_before_predecessor_import(args, r7, authorization, indexed)
    return loader(), claim


def _install_runtime_phase_capture(r6_worker: Any, capture_box: dict[str, Any]) -> None:
    original = r6_worker._install_seed_and_evaluator_capture

    def install(v2: Any, generation_seed: int) -> dict[str, Any]:
        captured = original(v2, generation_seed)
        events: list[str] = []
        base = v2.OfficialRuntimeV2

        class InstrumentedRuntime(base):
            def load(self, role: str, snapshot: Path) -> None:
                result = super().load(role, snapshot)
                self._r7_loaded_role = role
                events.append("VOICE_DESIGN_LOAD_COMPLETED" if role == "voice_design" else "BASE_LOAD_COMPLETED")
                return result

            def generate_design(self, **kwargs: Any) -> Any:
                result = super().generate_design(**kwargs)
                events.append("VOICE_DESIGN_GENERATION_COMPLETED")
                return result

            def create_prompt(self, **kwargs: Any) -> Any:
                result = super().create_prompt(**kwargs)
                events.append("CLONE_PROMPT_COMPLETED")
                return result

            def generate_clone(self, **kwargs: Any) -> Any:
                result = super().generate_clone(**kwargs)
                events.append("CLONE_GENERATION_COMPLETED")
                return result

            def unload(self) -> None:
                role = getattr(self, "_r7_loaded_role", "")
                result = super().unload()
                events.append("VOICE_DESIGN_UNLOAD_COMPLETED" if role == "voice_design" else "BASE_UNLOAD_COMPLETED")
                self._r7_loaded_role = ""
                return result

        v2.OfficialRuntimeV2 = InstrumentedRuntime
        captured["r7_runtime_phase_events"] = events
        capture_box["captured"] = captured
        return captured

    r6_worker._install_seed_and_evaluator_capture = install


def execute_after_claim(
    *,
    args: argparse.Namespace,
    r7: Any,
    indexed: dict[str, dict[str, Any]],
    authorization: dict[str, Any],
    authorization_evidence: dict[str, Any],
    claim_path: Path,
    claim: dict[str, Any],
    claim_sha: str,
    ledger: dict[str, Any],
    ledger_sha: str,
) -> dict[str, Any]:
    r6_worker = _load_sealed_module(R6_WORKER_REL, indexed[R6_WORKER_REL.as_posix()], "qwen3_tts_r6_worker_for_r7")
    capture_box: dict[str, Any] = {}
    _install_runtime_phase_capture(r6_worker, capture_box)
    r6_child = r6_worker.execute_after_claim(
        args=args,
        indexed=indexed,
        authorization=authorization,
        claim_path=claim_path,
        claim=claim,
        claim_sha=claim_sha,
        ledger=ledger,
        ledger_sha=ledger_sha,
    )
    captured = capture_box.get("captured")
    if not isinstance(captured, dict):
        raise R7ForgeError("R7 runtime phase capture was not exercised")
    pending = Path(args.pending_dir).resolve()
    r6_manifest_path = pending / "worker_manifest_v6.json"
    r6_profile_path = pending / "voice_profile_candidate_v6.json"
    r6_manifest = r7.strict_read_json(r6_manifest_path, expected_sha256=r6_child["manifest_sha256"], label="R7 predecessor manifest")
    r6_profile = r7.strict_read_json(r6_profile_path, expected_sha256=r6_child["profile_sha256"], label="R7 predecessor profile")
    r6_semantic = r6_manifest["semantic_binding_v6"]
    command_sha = r7.canonical_sha256(canonical_worker_command(r7, args))
    semantic = {
        **r6_semantic,
        "worker_instance_nonce_sha256": authorization["worker_instance_nonce_sha256"],
        "execution_authorization_path": _relative(Path(args.execution_authorization)),
        "independent_audit_decision_path": authorization["independent_audit_decision_path"],
        "independent_audit_decision_sha256": authorization["independent_audit_decision_sha256"],
        "independent_audit_subject_sha256": authorization["independent_audit_subject_sha256"],
        "independent_auditor_identity_sha256": authorization["independent_auditor_identity_sha256"],
        "independent_audit_report_path": authorization_evidence["report_path"],
        "independent_audit_report_sha256": authorization_evidence["report_sha256"],
        "evaluation_corpus_sha256": indexed[R2_CORPUS_REL.as_posix()]["sha256"],
        "entry_worker_path": R7_WORKER_REL.as_posix(),
        "entry_worker_sha256": indexed[R7_WORKER_REL.as_posix()]["sha256"],
        "worker_command_sha256": command_sha,
        "evaluator_evidence_sha256": "f" * 64,
        "resource_evidence_sha256": "f" * 64,
    }
    subject_sha = r7.evidence_subject_sha256(semantic)
    r6_evaluator = r7.strict_read_json(
        pending / "evaluator_evidence_v6.json",
        expected_sha256=r6_child["evaluator_evidence_sha256"],
        label="R7 predecessor evaluator",
    )
    collision_results = captured["audio_acceptance"]["collision_results"]
    if not isinstance(collision_results, list) or not collision_results:
        raise R7ForgeError("R7 requires a nonempty exact collision corpus result set")
    evaluator = {
        **r6_evaluator,
        "schema": "qwen3_tts_voice_forge_evaluator_evidence_v7",
        "semantic_binding_sha256": subject_sha,
        "threshold_contract_path": r7.R2_CONTRACT_REL.as_posix(),
        "threshold_contract_sha256": r7.R2_CONTRACT_SHA256,
        "collision_corpus": {
            **r6_evaluator["collision_corpus"],
            "collision_results": collision_results,
            "collision_results_sha256": r7.canonical_sha256(collision_results),
            "maximum_observed_similarity": max(float(row["similarity"]) for row in collision_results),
        },
    }
    evaluator_path = pending / "evaluator_evidence_v7.json"
    r7.write_new_json(evaluator_path, evaluator)
    evaluator_sha = sha256_file(evaluator_path)
    r6_resource = r7.strict_read_json(
        pending / "worker_resource_evidence_v6.json",
        expected_sha256=r6_child["worker_resource_evidence_sha256"],
        label="R7 predecessor resource evidence",
    )
    worker_resource = {
        "schema": "qwen3_tts_voice_forge_worker_resource_evidence_v7",
        "status": "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED",
        "semantic_binding_sha256": subject_sha,
        "worker_reported_telemetry": r6_resource["worker_reported_telemetry"],
        "worker_reported_telemetry_sha256": r6_resource["worker_reported_telemetry_sha256"],
        "worker_reported_timings_seconds": r6_resource["worker_reported_timings_seconds"],
        "worker_reported_timings_sha256": r6_resource["worker_reported_timings_sha256"],
        "predecessor_events": r6_resource["worker_reported_events"],
        "predecessor_events_sha256": r6_resource["worker_reported_events_sha256"],
        "runtime_phase_events": captured["r7_runtime_phase_events"],
        "runtime_phase_events_sha256": r7.canonical_sha256(captured["r7_runtime_phase_events"]),
    }
    worker_resource_path = pending / "worker_resource_evidence_v7.json"
    r7.write_new_json(worker_resource_path, worker_resource)
    resource_sha = sha256_file(worker_resource_path)
    semantic["evaluator_evidence_sha256"] = evaluator_sha
    semantic["resource_evidence_sha256"] = resource_sha
    if r7.evidence_subject_sha256(semantic) != subject_sha:
        raise R7ForgeError("R7 evidence subject changed after final evidence hashes")
    expected_subjects = {
        (str(row["voice_id"]), str(row["kind"])) for row in captured["corpus"]["voices"]
    }
    r7.validate_evaluator_evidence(
        evaluator,
        semantic_binding=semantic,
        project_root=PROJECT_ROOT,
        expected_collision_subjects=expected_subjects,
    )
    r7.validate_worker_resource_evidence(worker_resource, semantic_binding=semantic)
    profile = {
        **r6_profile,
        "schema": "qwen3_tts_original_voice_profile_candidate_v7",
        "r7_status": "PRIVATE_UNREVIEWED_COMPLETE_PARENT_RECONCILIATION_PENDING",
        "predecessor_r6_profile_sha256": r6_child["profile_sha256"],
        "semantic_binding_v7": semantic,
        "semantic_binding_v7_sha256": r7.canonical_sha256(semantic),
        "evaluator_evidence_v7_path": evaluator_path.name,
        "evaluator_evidence_v7_sha256": evaluator_sha,
        "worker_resource_evidence_v7_path": worker_resource_path.name,
        "worker_resource_evidence_v7_sha256": resource_sha,
        "worker_launch_claim_v7_path": _relative(claim_path),
        "worker_launch_claim_v7_sha256": claim_sha,
        "parent_authorization_ledger_v7_path": claim["parent_ledger_path"],
        "parent_authorization_ledger_v7_sha256": ledger_sha,
        "complete_later_use_revalidation_v7_required": True,
    }
    profile_path = pending / "voice_profile_candidate_v7.json"
    r7.write_new_json(profile_path, profile)
    profile_sha = sha256_file(profile_path)
    manifest = {
        "schema": "qwen3_tts_original_voice_forge_worker_manifest_v7",
        "status": "CHILD_GATES_PASSED_PARENT_RECONCILIATION_AND_FINALIZATION_PENDING",
        "semantic_binding_v7": semantic,
        "semantic_binding_v7_sha256": r7.canonical_sha256(semantic),
        "profile_sha256": profile_sha,
        "predecessor_worker_manifest_sha256": r6_child["manifest_sha256"],
        "predecessor_profile_sha256": r6_child["profile_sha256"],
        "worker_launch_claim_path": _relative(claim_path),
        "worker_launch_claim_sha256": claim_sha,
        "parent_authorization_ledger_path": claim["parent_ledger_path"],
        "parent_authorization_ledger_sha256": ledger_sha,
        "evaluator_evidence_path": evaluator_path.name,
        "evaluator_evidence_sha256": evaluator_sha,
        "resource_evidence_path": worker_resource_path.name,
        "resource_evidence_sha256": resource_sha,
        "process_tree_quiescence_required_before_parent_finalization": True,
        "parent_evaluator_and_resource_reconciliation_required": True,
        **r7.FINAL_DISABLED_PERMISSIONS,
    }
    manifest_path = pending / "worker_manifest_v7.json"
    r7.write_new_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)
    child = {
        "schema": "qwen3_tts_original_voice_forge_child_result_v7",
        "status": manifest["status"],
        "semantic_binding_v7_sha256": r7.canonical_sha256(semantic),
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_sha,
        "profile_path": profile_path.name,
        "profile_sha256": profile_sha,
        "evaluator_evidence_path": evaluator_path.name,
        "evaluator_evidence_sha256": evaluator_sha,
        "worker_resource_evidence_path": worker_resource_path.name,
        "worker_resource_evidence_sha256": resource_sha,
        "worker_launch_claim_path": _relative(claim_path),
        "worker_launch_claim_sha256": claim_sha,
    }
    r7.validate_r7_profile_manifest_and_child(
        r6_profile=r6_profile,
        r7_profile=profile,
        r7_manifest=manifest,
        child_result=child,
        semantic_binding=semantic,
        r6_profile_sha256=r6_child["profile_sha256"],
        r6_manifest_sha256=r6_child["manifest_sha256"],
        r7_profile_sha256=profile_sha,
    )
    return child


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-private-unreviewed", action="store_true")
    parser.add_argument("--bundle-id")
    parser.add_argument("--run-id")
    parser.add_argument("--pending-dir")
    parser.add_argument("--payload-manifest-sha256")
    parser.add_argument("--execution-authorization")
    parser.add_argument("--execution-authorization-sha256")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute or not args.acknowledge_private_unreviewed:
        raise R7ForgeError("R7 worker remains inert without exact acknowledgements")
    if not all(
        (
            args.bundle_id, args.run_id, args.pending_dir,
            args.payload_manifest_sha256, args.execution_authorization,
            args.execution_authorization_sha256,
        )
    ):
        raise R7ForgeError("R7 worker lacks exact parent trust arguments")
    r7, indexed, authorization, authorization_evidence, _manifest = bootstrap_external_trust(args)
    claim_path, claim, claim_sha, ledger, ledger_sha = bootstrap_claim_before_predecessor_import(
        args, r7, authorization, indexed
    )
    child = execute_after_claim(
        args=args,
        r7=r7,
        indexed=indexed,
        authorization=authorization,
        authorization_evidence=authorization_evidence,
        claim_path=claim_path,
        claim=claim,
        claim_sha=claim_sha,
        ledger=ledger,
        ledger_sha=ledger_sha,
    )
    payload = r7.canonical_bytes(child)
    sys.stdout.buffer.write(payload + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        print(f"R7 Qwen3-TTS forge worker failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
