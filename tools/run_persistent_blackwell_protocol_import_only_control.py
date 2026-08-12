#!/usr/bin/env python3
"""Prepare or run one protocol-faithful Torch-import-only control.

The default invocation is inert.  The explicitly gated control reuses the
sealed candidate's real client transport, real worker ``serve`` loop, real
stdin reader, real stdout/stderr drains, real phase journal fsync, real
ResourceSampler, and real 120-second load watchdog.  A diagnostic runtime
subclass returns immediately after ``imports.torch``.

It never imports Torchaudio or Chatterbox, calls a Torch CUDA API, loads a
model, generates or plays audio, or invokes Ollama.  The production candidate
files remain byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import importlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))

import candidate_client
import candidate_contract


CONFIG_PATH = CANDIDATE_ROOT / "candidate_config.json"
ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control"
)
DEFENDER_CHANGE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "defender_blackwell_voice_narrow_exclusion"
)
EXACT_DEFENDER_TARGET = (
    ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu" / ".venv"
).resolve()
DEFENDER_APPLY_HELPER = ROOT / "tools" / "apply_defender_blackwell_voice_exclusion.ps1"
DEFENDER_APPLY_HELPER_SHA256 = (
    "87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919"
)
DIAGNOSTIC_OPT_IN = "KIRA_PERSISTENT_BLACKWELL_IMPORT_ONLY_CONTROL"
DEFAULT_TIMEOUT_SECONDS = 1100.0
EXPECTED_BASELINE_HASHES = {
    "candidate_client": "b57e1a57625f8d3c55881795611b440aaf91aeb7466ee2f1231ee7bedbc3e9f1",
    "candidate_contract": "e74ce6ad83b181d5f8ca786764d5e61e2cc5e053aaebf29065063151aed38cbc",
    "candidate_config": "8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57",
    "candidate_worker": "bbf33447e7b742a3f2c79da6f7a3527b37a069e32bb888ed3d1e833345388085",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def exact_candidate_hashes() -> dict[str, str]:
    return {
        "candidate_client": sha256_file(CANDIDATE_ROOT / "candidate_client.py"),
        "candidate_contract": sha256_file(CANDIDATE_ROOT / "candidate_contract.py"),
        "candidate_config": sha256_file(CONFIG_PATH),
        "candidate_worker": sha256_file(CANDIDATE_ROOT / "persistent_worker.py"),
    }


def allocate_attempt_directory() -> Path:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        candidate = ATTEMPT_ROOT / f"attempt_{number:02d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("no append-only protocol-import control attempt is available")


def no_active_blender_evidence() -> dict[str, Any]:
    """Use Get-Process, not CIM/WMI, and never stop a discovered process."""

    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "$p=@(Get-Process -Name blender -ErrorAction SilentlyContinue | "
            "Select-Object Id,Path,StartTime); "
            "[pscustomobject]@{count=$p.Count;processes=$p} | "
            "ConvertTo-Json -Depth 4 -Compress"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return {
            "query_succeeded": False,
            "active": None,
            "error": completed.stderr[-2000:],
            "query_kind": "Get-Process_not_CIM_or_WMI",
        }
    payload = json.loads(completed.stdout or "{}")
    count = int(payload.get("count") or 0)
    return {
        "query_succeeded": True,
        "active": count > 0,
        "count": count,
        "processes": payload.get("processes") or [],
        "query_kind": "Get-Process_not_CIM_or_WMI",
        "processes_terminated": False,
    }


def validate_defender_state_evidence(
    path_value: str,
    expected_sha256: str,
    expected_present: bool,
) -> dict[str, Any]:
    expected = str(expected_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("exact Defender-state evidence SHA-256 is required")
    path = Path(path_value).resolve()
    path.relative_to(DEFENDER_CHANGE_ROOT.resolve())
    if path.name not in {
        "PRECHANGE.json",
        "POST_APPLY_BASELINE.json",
        "POSTCHANGE.json",
        "ROLLBACK.json",
    }:
        raise ValueError("Defender-state evidence filename is not accepted")
    actual = sha256_file(path)
    if not hmac.compare_digest(actual, expected):
        raise ValueError("Defender-state evidence hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    target = Path(str(payload.get("exact_target_path") or "")).resolve()
    if target != EXACT_DEFENDER_TARGET:
        raise ValueError("Defender-state evidence target mismatch")
    if payload.get("exact_target_present") is not expected_present:
        raise ValueError("Defender exclusion state does not match operator binding")
    if payload.get("defender_disabled") is not False:
        raise ValueError("Defender-state evidence does not preserve Defender")
    other_exclusions = payload.get("other_exclusions_preserved")
    if other_exclusions not in {True, "NOT_PROVEN_NO_MACHINE_PRESTATE"}:
        raise ValueError("Defender-state evidence reports unrelated exclusion drift")
    if payload.get("apply_helper_sha256") != DEFENDER_APPLY_HELPER_SHA256:
        raise ValueError("Defender-state evidence was not bound to the sole apply helper")
    if sha256_file(DEFENDER_APPLY_HELPER) != DEFENDER_APPLY_HELPER_SHA256:
        raise ValueError("sole Defender apply helper changed")
    return {
        "path": relative(path),
        "sha256": actual,
        "exact_target_path": str(target),
        "exact_target_present": expected_present,
        "defender_disabled": False,
        "other_exclusions_preserved": other_exclusions,
        "paired_machine_prechange_available": payload.get(
            "machine_prechange_state_available"
        ),
        "paired_pre_post_causality_claimed": payload.get(
            "paired_pre_post_causality_claimed"
        ),
        "apply_helper_sha256": payload.get("apply_helper_sha256"),
    }


class ImportOnlyProtocolClient(candidate_client.PersistentBlackwellVoiceCandidateClient):
    """Real candidate client transport with only its child command specialized."""

    def _command(self) -> list[str]:
        return [
            str(candidate_contract.project_file(self.config["python"])),
            str(Path(__file__).resolve()),
            "--child-serve-import-only",
        ]

    def _spawn(
        self,
        command: list[str],
        environment: dict[str, str],
    ) -> subprocess.Popen[bytes]:
        exact_environment = dict(environment)
        exact_environment[DIAGNOSTIC_OPT_IN] = "1"
        return super()._spawn(command, exact_environment)

    def load_import_only(self) -> dict[str, Any]:
        if not self.allow_gpu_model_load:
            raise candidate_client.PersistentCandidateNotAuthorized(
                "import-only control requires the bounded load-request environment opt-in"
            )
        # Deliberately call the real request transport directly.  Calling the
        # production load() helper would query Ollama before sending the same
        # request, which is outside this import-only diagnostic contract.
        response = self._request("load")
        required = {
            "ready": True,
            "reason": "protocol_faithful_torch_import_only_complete",
            "import_only": True,
            "cuda_api_invoked": False,
            "model_loaded": False,
            "audio_generated": False,
        }
        mismatches = {
            key: {"expected": value, "actual": response.get(key)}
            for key, value in required.items()
            if response.get(key) != value
        }
        if mismatches:
            raise candidate_client.PersistentCandidateProtocolError(
                f"import-only diagnostic response mismatch: {mismatches}"
            )
        return response


def child_serve_import_only() -> int:
    """Run the actual worker protocol with a Torch-only diagnostic runtime."""

    if os.environ.get(DIAGNOSTIC_OPT_IN) != "1":
        raise RuntimeError("import-only diagnostic process opt-in is absent")

    worker = importlib.import_module("persistent_worker")
    config = candidate_contract.load_candidate_config(CONFIG_PATH)
    startup_ledger = candidate_contract.PhaseLedger()
    with startup_ledger.phase("startup.config_load"):
        config = candidate_contract.load_candidate_config(CONFIG_PATH)
    with startup_ledger.phase("startup.sealed_contract_verification"):
        candidate_contract.verify_candidate_config(config)
        if exact_candidate_hashes() != EXPECTED_BASELINE_HASHES:
            raise RuntimeError("restored Attempt 06 candidate hashes changed")
    with startup_ledger.phase("startup.restricted_environment"):
        environment = candidate_contract.verify_restricted_environment(
            config,
            require_load_opt_in=False,
        )
    if not environment:
        raise RuntimeError("restricted import-only environment was not verified")

    class TorchImportOnlyRuntime(worker.PersistentVoiceRuntime):
        def load(
            self,
            *,
            phase_event_callback: Any | None = None,
        ) -> dict[str, Any]:
            ledger = candidate_contract.PhaseLedger(event_callback=phase_event_callback)
            operation_started_ns = time.perf_counter_ns()
            sampler: Any | None = None
            sampler_start_started_ns: int | None = None
            sampler_start_finished_ns: int | None = None
            active_threads: list[dict[str, Any]] = []
            try:
                with ledger.phase("load.restricted_environment"):
                    cache_paths = self._environment_verifier(
                        self.config,
                        require_load_opt_in=True,
                    )
                with ledger.phase("load.runtime_dependency_metadata"):
                    runtime_versions = self._runtime_metadata_verifier(self.config)
                with ledger.phase("load.approved_identity_hashes"):
                    identity = self._identity_verifier(self.config)
                with ledger.phase("load.qwen_absence_omitted_import_only_no_ollama"):
                    qwen = {
                        "query_performed": False,
                        "ollama_invoked": False,
                        "reason": "import_only_control_forbids_ollama",
                    }
                sampler = self._resource_sampler_factory()
                sampler_start_started_ns = time.perf_counter_ns()
                sampler.start()
                sampler_start_finished_ns = time.perf_counter_ns()
                active_threads = [
                    {
                        "name": thread.name,
                        "daemon": bool(thread.daemon),
                        "alive": bool(thread.is_alive()),
                    }
                    for thread in threading.enumerate()
                ]
                with ledger.phase("imports.torch"):
                    torch = importlib.import_module("torch")
                numpy_module = sys.modules.get("numpy")
                resources = sampler.stop()
                sampler = None
                return {
                    "ready": True,
                    "reason": "protocol_faithful_torch_import_only_complete",
                    "import_only": True,
                    "torch_version": str(torch.__version__),
                    "numpy_loaded_transitively": numpy_module is not None,
                    "numpy_version": (
                        str(getattr(numpy_module, "__version__", ""))
                        if numpy_module is not None
                        else None
                    ),
                    "cuda_api_invoked": False,
                    "torchaudio_imported": "torchaudio" in sys.modules,
                    "chatterbox_imported": any(
                        name == "chatterbox" or name.startswith("chatterbox.")
                        for name in sys.modules
                    ),
                    "model_loaded": False,
                    "audio_generated": False,
                    "playback_performed": False,
                    "ollama_invoked": False,
                    "qwen_residency": qwen,
                    "identity": identity,
                    "cache_paths": cache_paths,
                    "runtime_versions": runtime_versions,
                    "active_threads_before_import": active_threads,
                    "sampler_start_timing": {
                        "started_monotonic_ns": sampler_start_started_ns,
                        "finished_monotonic_ns": sampler_start_finished_ns,
                        "elapsed_seconds": round(
                            (sampler_start_finished_ns - sampler_start_started_ns)
                            / 1_000_000_000,
                            9,
                        ),
                    },
                    "phase_timings": ledger.records,
                    "operation_seconds": round(
                        (time.perf_counter_ns() - operation_started_ns) / 1_000_000_000,
                        9,
                    ),
                    "resources": resources,
                    "lifecycle": self.lifecycle(),
                }
            except Exception as exc:
                resources = (
                    sampler.stop()
                    if sampler is not None
                    else {"sample_count": 0, "sampling_started": False}
                )
                return {
                    "ready": False,
                    "reason": "protocol_faithful_torch_import_only_failed",
                    "import_only": True,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-12000:],
                    "cuda_api_invoked": False,
                    "model_loaded": False,
                    "audio_generated": False,
                    "playback_performed": False,
                    "ollama_invoked": False,
                    "phase_timings": ledger.records,
                    "resources": resources,
                    "lifecycle": self.lifecycle(),
                }

    worker.PersistentVoiceRuntime = TorchImportOnlyRuntime
    nonce = str(os.environ.get("KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE") or "")
    return int(worker.serve(config, nonce, startup_ledger.records))


def run_control(
    *,
    expected_config_sha256: str,
    expected_tool_sha256: str,
    defender_evidence_path: str,
    defender_evidence_sha256: str,
    defender_exclusion_present: bool,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    actual_hashes = exact_candidate_hashes()
    if actual_hashes != EXPECTED_BASELINE_HASHES:
        raise RuntimeError(f"restored Attempt 06 candidate hashes changed: {actual_hashes}")
    if not hmac.compare_digest(
        str(expected_config_sha256 or "").strip().casefold(),
        actual_hashes["candidate_config"],
    ):
        raise ValueError("operator-bound candidate config SHA-256 mismatch")
    tool_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(
        str(expected_tool_sha256 or "").strip().casefold(),
        tool_hash,
    ):
        raise ValueError("operator-bound import-control tool SHA-256 mismatch")
    defender = validate_defender_state_evidence(
        defender_evidence_path,
        defender_evidence_sha256,
        defender_exclusion_present,
    )
    blender = no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")

    attempt = allocate_attempt_directory()
    marker_path = attempt / "ATTEMPT_STARTED.json"
    report_path = attempt / "PROTOCOL_IMPORT_ONLY_CONTROL.json"
    started_at = utc_now()
    marker_sha256 = write_json_exclusive(
        marker_path,
        {
            "schema_version": 1,
            "artifact_kind": "persistent_blackwell_protocol_import_only_control_started",
            "started_at": started_at,
            "candidate_hashes": actual_hashes,
            "tool_sha256": tool_hash,
            "defender_state": defender,
            "no_active_blender": blender,
            "cuda_api_invoked": False,
            "model_loaded": False,
            "audio_generated": False,
        },
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_protocol_import_only_control",
        "started_at": started_at,
        "status": "started",
        "candidate_hashes": actual_hashes,
        "tool_sha256": tool_hash,
        "defender_state": defender,
        "no_active_blender": blender,
        "attempt_started_marker": {
            "path": relative(marker_path),
            "sha256": marker_sha256,
        },
        "request_timeout_seconds": timeout_seconds,
        "real_candidate_client_transport": True,
        "real_worker_serve_loop": True,
        "real_resource_sampler": True,
        "real_phase_event_fsync": True,
        "real_load_watchdog": True,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
    }
    client: ImportOnlyProtocolClient | None = None
    try:
        client = ImportOnlyProtocolClient(
            allow_gpu_model_load=True,
            startup_timeout_seconds=30.0,
            request_timeout_seconds=timeout_seconds,
            diagnostic_directory=attempt,
        )
        report["hello"] = client.start()
        report["status_before_import"] = client.status()
        report["load_import_only"] = client.load_import_only()
        report["phase_events"] = client.events
        report["passed"] = (
            report["load_import_only"].get("ready") is True
            and report["load_import_only"].get("torch_version") == "2.11.0+cu130"
            and report["load_import_only"].get("torchaudio_imported") is False
            and report["load_import_only"].get("chatterbox_imported") is False
            and report["load_import_only"].get("cuda_api_invoked") is False
            and report["load_import_only"].get("model_loaded") is False
        )
        report["status"] = "passed" if report["passed"] else "failed_preserved"
    except Exception as exc:
        report.update(
            {
                "passed": False,
                "status": "failed_preserved",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc()[-16000:],
                "phase_events": client.events if client is not None else [],
            }
        )
    finally:
        report["cleanup"] = client.close() if client is not None else None
        report["finished_at"] = utc_now()
        report["candidate_hashes_after"] = exact_candidate_hashes()
        report["candidate_unchanged"] = (
            report["candidate_hashes_after"] == EXPECTED_BASELINE_HASHES
        )
        write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_protocol_import_only_control_description",
        "status": "PREPARED_NOT_EXECUTED",
        "candidate_hashes": exact_candidate_hashes(),
        "expected_candidate_hashes": EXPECTED_BASELINE_HASHES,
        "actual_candidate_worker_and_client_reused": True,
        "stop_boundary": "immediately_after_imports.torch",
        "resource_sampler": "exact_control_behavior",
        "cuda_api_invoked": False,
        "torchaudio_imported": False,
        "chatterbox_imported": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "production_routing_changed": False,
        "defender_changed_by_this_tool": False,
        "exact_defender_target": str(EXACT_DEFENDER_TARGET),
        "default_timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    }


def static_self_check() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    client_start = source.index("class ImportOnlyProtocolClient")
    child_start = source.index("\ndef child_serve_import_only", client_start)
    run_start = source.index("\ndef run_control", child_start)
    client_source = source[client_start:child_start]
    child_source = source[child_start:run_start]
    actual_hashes = exact_candidate_hashes()
    checks = {
        "candidate_exact_attempt06_hashes": actual_hashes == EXPECTED_BASELINE_HASHES,
        "candidate_config_verifies": bool(
            candidate_contract.verify_candidate_config(
                candidate_contract.load_candidate_config(CONFIG_PATH)
            )
        ),
        "sole_defender_apply_helper_exact": (
            sha256_file(DEFENDER_APPLY_HELPER) == DEFENDER_APPLY_HELPER_SHA256
        ),
        "real_client_subclass": issubclass(
            ImportOnlyProtocolClient,
            candidate_client.PersistentBlackwellVoiceCandidateClient,
        ),
        "real_request_transport_used": 'self._request("load")' in client_source,
        "real_worker_serve_used": "worker.serve(" in child_source,
        "real_resource_sampler_used": "self._resource_sampler_factory()" in child_source,
        "torch_import_only_boundary": 'importlib.import_module("torch")' in child_source,
        "no_top_level_torch_import": "\nimport torch\n" not in source,
        "no_torchaudio_import_call": 'import_module("torchaudio")' not in child_source,
        "no_chatterbox_import_call": (
            'import_module("chatterbox")' not in child_source
            and "from chatterbox" not in child_source
        ),
        "no_torch_cuda_call": "torch.cuda" not in child_source,
        "no_ollama_call": (
            "qwen_residency_evidence(" not in child_source
            and "/api/ps" not in child_source
        ),
        "no_playback_call": not any(
            marker in child_source
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "defender_not_changed_by_probe": not any(
            marker in source
            for marker in (
                "Add" + "-MpPreference",
                "Remove" + "-MpPreference",
                "Set" + "-MpPreference",
            )
        ),
    }
    return {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_protocol_import_only_control_static_self_check",
        "checks": checks,
        "passed": all(checks.values()),
        "candidate_hashes": actual_hashes,
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "gpu_used": False,
        "model_loaded": False,
        "audio_generated": False,
        "ollama_invoked": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--describe", action="store_true")
    group.add_argument("--static-self-check", action="store_true")
    group.add_argument("--run-control", action="store_true")
    group.add_argument("--child-serve-import-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--expected-probe-tool-sha256", default="")
    parser.add_argument("--defender-state-evidence", default="")
    parser.add_argument("--expected-defender-state-evidence-sha256", default="")
    parser.add_argument(
        "--expected-defender-exclusion-state",
        choices=("present", "absent"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.child_serve_import_only:
        return child_serve_import_only()
    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    if not args.run_control:
        print(json.dumps(describe(), indent=2, sort_keys=True))
        return 0
    if not args.confirm_no_active_blender:
        raise SystemExit("--confirm-no-active-blender is required")
    if args.expected_defender_exclusion_state is None:
        raise SystemExit("--expected-defender-exclusion-state is required")
    timeout_seconds = max(300.0, min(1500.0, float(args.timeout_seconds)))
    report_path, report = run_control(
        expected_config_sha256=args.expected_candidate_config_sha256,
        expected_tool_sha256=args.expected_probe_tool_sha256,
        defender_evidence_path=args.defender_state_evidence,
        defender_evidence_sha256=args.expected_defender_state_evidence_sha256,
        defender_exclusion_present=args.expected_defender_exclusion_state == "present",
        timeout_seconds=timeout_seconds,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "passed": report.get("passed") is True,
                "status": report.get("status"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.get("passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
