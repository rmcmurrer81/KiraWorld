"""Parent-side controller for the inactive persistent Blackwell voice candidate.

This module is deliberately not imported by ``Core.voice_output`` and is not
listed in the production routing manifest.  Constructing the client defaults
to model loading disabled.  The later acceptance harness must opt in
explicitly before ``load`` or ``synthesize`` can be requested.
"""

from __future__ import annotations

import hmac
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any


SIDECAR_ROOT = Path(__file__).resolve().parent
if __package__:
    from .candidate_contract import (  # noqa: E402
        CONFIG_PATH,
        ROOT,
        load_candidate_config,
        project_file,
        qwen_residency_evidence,
        sha256_file,
        sha256_text,
        validate_wav,
        verify_candidate_config,
        verify_identity_files,
    )
else:
    if str(SIDECAR_ROOT) not in sys.path:
        sys.path.insert(0, str(SIDECAR_ROOT))
    from candidate_contract import (  # noqa: E402
        CONFIG_PATH,
        ROOT,
        load_candidate_config,
        project_file,
        qwen_residency_evidence,
        sha256_file,
        sha256_text,
        validate_wav,
        verify_candidate_config,
        verify_identity_files,
    )


class PersistentCandidateError(RuntimeError):
    pass


class PersistentCandidateNotAuthorized(PersistentCandidateError):
    pass


class PersistentCandidateProtocolError(PersistentCandidateError):
    pass


def restricted_candidate_environment(
    config: dict[str, Any],
    *,
    session_nonce: str,
    allow_gpu_model_load: bool,
) -> dict[str, str]:
    """Build the child environment from an explicit Windows allowlist only."""

    allowed = (
        "USERNAME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SystemRoot",
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "DriverData",
        "ComSpec",
        "SystemDrive",
        "ProgramFiles",
        "ProgramFiles(x86)",
        "ProgramW6432",
        "CommonProgramFiles",
        "CommonProgramFiles(x86)",
        "CommonProgramW6432",
    )
    env = {key: value for key in allowed if (value := os.environ.get(key))}
    cache_root = project_file(config["runtime_cache_root"])
    cache_root.resolve().relative_to((ROOT / "RecoverySprint" / "runtime_cache").resolve())
    cache_paths = {
        "TORCHINDUCTOR_CACHE_DIR": cache_root / "torchinductor",
        "TRITON_CACHE_DIR": cache_root / "triton",
        "TEMP": cache_root / "temp",
        "TMP": cache_root / "temp",
    }
    for path in cache_paths.values():
        path.resolve().relative_to(cache_root.resolve())
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CUDA_VISIBLE_DEVICES": "0",
            "KIRA_PERSISTENT_BLACKWELL_CANDIDATE": "1",
            "KIRA_PERSISTENT_BLACKWELL_SESSION_NONCE": session_nonce,
            **{key: str(path.resolve()) for key, path in cache_paths.items()},
        }
    )
    if allow_gpu_model_load:
        env["KIRA_PERSISTENT_BLACKWELL_ALLOW_MODEL_LOAD"] = "1"
    return env


def bounded_diagnostic_paths(
    config: dict[str, Any],
    diagnostic_directory: Path | None,
) -> dict[str, Path]:
    """Resolve optional append-only diagnostics inside the sealed output root."""

    if diagnostic_directory is None:
        return {}
    directory = Path(diagnostic_directory).resolve()
    if not directory.is_dir():
        raise PersistentCandidateNotAuthorized("candidate diagnostic directory must already exist")
    allowed = False
    for root_value in config.get("allowed_output_roots") or []:
        root = project_file(root_value).resolve()
        try:
            directory.relative_to(root)
        except ValueError:
            continue
        if directory != root:
            allowed = True
            break
    if not allowed:
        raise PersistentCandidateNotAuthorized(
            "candidate diagnostic directory is outside the sealed acceptance root"
        )
    diagnostics = config.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise PersistentCandidateProtocolError("candidate diagnostic contract is missing")
    paths: dict[str, Path] = {}
    for key, config_key in (
        ("phase_events", "phase_event_journal_filename"),
        ("stderr", "stderr_faulthandler_filename"),
    ):
        filename = str(diagnostics.get(config_key) or "")
        if not filename or Path(filename).name != filename:
            raise PersistentCandidateProtocolError(
                f"candidate diagnostic filename is invalid: {config_key}"
            )
        target = (directory / filename).resolve()
        target.relative_to(directory)
        paths[key] = target
    return paths


class PersistentBlackwellVoiceCandidateClient:
    def __init__(
        self,
        *,
        config_path: Path = CONFIG_PATH,
        allow_gpu_model_load: bool = False,
        startup_timeout_seconds: float = 30.0,
        request_timeout_seconds: float = 900.0,
        diagnostic_directory: Path | None = None,
    ) -> None:
        self.config_path = Path(config_path).resolve()
        if self.config_path != CONFIG_PATH.resolve():
            raise PersistentCandidateNotAuthorized("only the sealed candidate config is accepted")
        self.config = load_candidate_config(self.config_path)
        self.artifact_hashes = verify_candidate_config(self.config)
        self.allow_gpu_model_load = bool(allow_gpu_model_load)
        self.startup_timeout_seconds = max(5.0, min(120.0, float(startup_timeout_seconds)))
        self.request_timeout_seconds = max(30.0, min(1800.0, float(request_timeout_seconds)))
        self._diagnostic_paths = bounded_diagnostic_paths(
            self.config,
            diagnostic_directory,
        )
        self._diagnostics_prepared = False
        self.session_nonce = secrets.token_urlsafe(48)
        self.session_id = sha256_text(self.session_nonce)[:24]
        self.process: subprocess.Popen[bytes] | None = None
        self._stdout_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stderr_fragments: list[str] = []
        self._events: list[dict[str, Any]] = []
        self._write_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

    def _command(self) -> list[str]:
        return [
            str(project_file(self.config["python"])),
            str(project_file(self.config["worker"])),
            "--serve",
        ]

    def _spawn(self, command: list[str], environment: dict[str, str]) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _read_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        max_bytes = int(self.config["bounds"]["max_response_bytes"])
        while True:
            raw = process.stdout.readline(max_bytes + 2)
            if raw == b"":
                return
            if len(raw) > max_bytes or not raw.endswith(b"\n"):
                self._stdout_queue.put(
                    {
                        "message_type": "fatal",
                        "reason": "persistent_candidate_response_oversized_or_unterminated",
                    }
                )
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._stdout_queue.put(
                    {
                        "message_type": "fatal",
                        "reason": "persistent_candidate_response_malformed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                return
            if not isinstance(payload, dict):
                self._stdout_queue.put(
                    {
                        "message_type": "fatal",
                        "reason": "persistent_candidate_response_not_object",
                    }
                )
                return
            self._stdout_queue.put(payload)

    def _prepare_diagnostics(self) -> None:
        if not self._diagnostic_paths or self._diagnostics_prepared:
            return
        existing = [path for path in self._diagnostic_paths.values() if path.exists()]
        if existing:
            raise PersistentCandidateProtocolError(
                f"candidate diagnostic files already exist and will not be overwritten: {existing}"
            )
        for path in self._diagnostic_paths.values():
            with path.open("xb"):
                pass
        self._diagnostics_prepared = True

    def _persist_phase_event(self, payload: dict[str, Any]) -> None:
        path = self._diagnostic_paths.get("phase_events")
        if path is None:
            return
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        with path.open("ab", buffering=0) as handle:
            handle.write(encoded)
            os.fsync(handle.fileno())

    def _read_stderr(self) -> None:
        process = self.process
        if process is None or process.stderr is None:
            return
        retained = 0
        diagnostic_path = self._diagnostic_paths.get("stderr")
        diagnostic_handle = (
            diagnostic_path.open("ab", buffering=0) if diagnostic_path is not None else None
        )
        try:
            while True:
                raw = process.stderr.readline(4098)
                if raw == b"":
                    return
                if diagnostic_handle is not None:
                    diagnostic_handle.write(raw)
                value = raw.decode("utf-8", errors="replace")
                if retained < 131072:
                    remaining = 131072 - retained
                    fragment = value[:remaining]
                    self._stderr_fragments.append(fragment)
                    retained += len(fragment.encode("utf-8", errors="replace"))
        finally:
            if diagnostic_handle is not None:
                diagnostic_handle.close()

    @property
    def stderr_tail(self) -> str:
        return "".join(self._stderr_fragments)[-12000:]

    @property
    def events(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._events]

    @property
    def diagnostic_paths(self) -> dict[str, str]:
        return {
            key: path.relative_to(ROOT.resolve()).as_posix()
            for key, path in self._diagnostic_paths.items()
        }

    def start(self) -> dict[str, Any]:
        if self.process is not None:
            raise PersistentCandidateProtocolError("persistent candidate client already started")
        verify_identity_files(self.config)
        self._prepare_diagnostics()
        environment = restricted_candidate_environment(
            self.config,
            session_nonce=self.session_nonce,
            allow_gpu_model_load=self.allow_gpu_model_load,
        )
        spawn_started_ns = time.perf_counter_ns()
        process = self._spawn(self._command(), environment)
        self.process = process
        self._stdout_thread = threading.Thread(
            target=self._read_stdout,
            name="persistent-blackwell-client-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr,
            name="persistent-blackwell-client-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        try:
            hello = self._wait_message(timeout_seconds=self.startup_timeout_seconds)
        except Exception:
            self.close()
            raise
        self._validate_common_response(hello)
        if hello.get("message_type") != "hello" or hello.get("ready") is not True:
            self.close()
            raise PersistentCandidateProtocolError(
                f"persistent candidate startup failed: {hello}; stderr={self.stderr_tail}"
            )
        if hello.get("reason") != "persistent_candidate_protocol_ready_model_unloaded":
            self.close()
            raise PersistentCandidateProtocolError("persistent candidate startup state mismatch")
        if hello.get("model_loaded") is not False:
            self.close()
            raise PersistentCandidateProtocolError("persistent candidate loaded a model before explicit load")
        if hello.get("worker_sha256") != self.artifact_hashes["candidate_worker"]:
            self.close()
            raise PersistentCandidateProtocolError("persistent candidate worker handshake hash mismatch")
        hello_received_ns = time.perf_counter_ns()
        hello["parent_process_start_timing"] = {
            "spawn_started_monotonic_ns": spawn_started_ns,
            "hello_received_monotonic_ns": hello_received_ns,
            "elapsed_seconds": round(
                (hello_received_ns - spawn_started_ns) / 1_000_000_000,
                9,
            ),
        }
        return hello

    def _wait_message(self, *, timeout_seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("persistent candidate response timed out")
            try:
                payload = self._stdout_queue.get(timeout=min(0.5, remaining))
            except queue.Empty:
                if self.process is not None and self.process.poll() is not None:
                    raise PersistentCandidateProtocolError(
                        f"persistent candidate exited {self.process.returncode}; stderr={self.stderr_tail}"
                    )
                continue
            if payload.get("message_type") == "event":
                self._validate_common_response(payload)
                self._events.append(payload)
                self._persist_phase_event(payload)
                continue
            if payload.get("message_type") == "fatal":
                raise PersistentCandidateProtocolError(f"persistent candidate fatal response: {payload}")
            return payload

    def _validate_common_response(self, payload: dict[str, Any]) -> None:
        if payload.get("schema_version") != 1:
            raise PersistentCandidateProtocolError("persistent candidate response schema mismatch")
        if payload.get("candidate_id") != self.config["candidate_id"]:
            raise PersistentCandidateProtocolError("persistent candidate response identity mismatch")
        if payload.get("candidate_status") != self.config["candidate_status"]:
            raise PersistentCandidateProtocolError("persistent candidate status mismatch")
        if payload.get("production_routing_authorized") is not False:
            raise PersistentCandidateProtocolError("inactive candidate claimed production authorization")
        if payload.get("session_id") != self.session_id:
            raise PersistentCandidateProtocolError("persistent candidate session mismatch")
        for key in ("playback", "generic_voice_used", "sapi_voice_used", "fallback_used"):
            if payload.get(key) is not False:
                raise PersistentCandidateProtocolError(f"persistent candidate forbidden response flag: {key}")

    def _request(
        self,
        operation: str,
        *,
        _timeout_seconds: float | None = None,
        **values: Any,
    ) -> dict[str, Any]:
        with self._request_lock:
            process = self.process
            if process is None or process.stdin is None or process.poll() is not None:
                raise PersistentCandidateProtocolError("persistent candidate process is not running")
            request_id = str(uuid.uuid4())
            payload = {
                "schema_version": 1,
                "request_id": request_id,
                "session_nonce": self.session_nonce,
                "operation": operation,
                "playback": False,
                "fallback": False,
                **values,
            }
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
            if len(encoded) > int(self.config["bounds"]["max_line_bytes"]):
                raise PersistentCandidateProtocolError("persistent candidate request exceeds line bound")
            with self._write_lock:
                request_submitted_ns = time.perf_counter_ns()
                process.stdin.write(encoded)
                process.stdin.flush()
            try:
                response = self._wait_message(
                    timeout_seconds=(
                        self.request_timeout_seconds
                        if _timeout_seconds is None
                        else max(1.0, min(self.request_timeout_seconds, float(_timeout_seconds)))
                    )
                )
            except TimeoutError as exc:
                latest_event = self._events[-1] if self._events else None
                raise TimeoutError(
                    "persistent candidate response timed out; "
                    f"operation={operation}; latest_phase_event={latest_event}; "
                    f"diagnostic_paths={self.diagnostic_paths}; stderr_tail={self.stderr_tail}"
                ) from exc
            self._validate_common_response(response)
            if response.get("message_type") != "response":
                raise PersistentCandidateProtocolError("persistent candidate did not return a response")
            if response.get("request_id") != request_id:
                raise PersistentCandidateProtocolError("persistent candidate request/response id mismatch")
            if response.get("operation") != operation:
                raise PersistentCandidateProtocolError("persistent candidate operation mismatch")
            response_received_ns = time.perf_counter_ns()
            response["parent_transport_timing"] = {
                "request_submitted_monotonic_ns": request_submitted_ns,
                "response_received_monotonic_ns": response_received_ns,
                "elapsed_seconds": round(
                    (response_received_ns - request_submitted_ns) / 1_000_000_000,
                    9,
                ),
            }
            return response

    def status(self) -> dict[str, Any]:
        return self._request("status")

    def load(self) -> dict[str, Any]:
        if not self.allow_gpu_model_load:
            raise PersistentCandidateNotAuthorized(
                "GPU/model loading is disabled; use only the later bounded acceptance harness"
            )
        parent_qwen = qwen_residency_evidence(self.config)
        if parent_qwen.get("qwen_absent_proven") is not True:
            raise PersistentCandidateNotAuthorized("Qwen absence was not proven before candidate load")
        response = self._request("load")
        response["parent_qwen_residency_before_load"] = parent_qwen
        return response

    def synthesize(
        self,
        *,
        text: str,
        output_relative: str,
        pcm_output_gain_db: float = 0.0,
        proximity_cut_hz: float = 0.0,
        proximity_cut_mix: float = 0.0,
    ) -> dict[str, Any]:
        if not self.allow_gpu_model_load:
            raise PersistentCandidateNotAuthorized(
                "GPU/model synthesis is disabled; use only the later bounded acceptance harness"
            )
        identity = verify_identity_files(self.config)
        parent_qwen = qwen_residency_evidence(self.config)
        if parent_qwen.get("qwen_absent_proven") is not True:
            raise PersistentCandidateNotAuthorized("Qwen absence was not proven before candidate synthesis")
        normalized = str(text or "").strip()
        response = self._request(
            "synthesize",
            channel="public_spoken_only",
            text=normalized,
            text_sha256=sha256_text(normalized),
            profile_sha256=identity["profile_sha256"],
            reference_sha256=identity["reference_sha256"],
            output_relative=output_relative,
            pcm_output_gain_db=float(pcm_output_gain_db),
            proximity_cut_hz=float(proximity_cut_hz),
            proximity_cut_mix=float(proximity_cut_mix),
        )
        response["parent_qwen_residency_before_synthesis"] = parent_qwen
        if response.get("generated") is not True:
            return response
        expected_target = project_file(output_relative)
        issues: list[str] = []
        if response.get("engine") != "chatterbox_tts":
            issues.append("engine_mismatch")
        if response.get("device") != "cuda":
            issues.append("device_mismatch")
        if response.get("text_sha256") != sha256_text(normalized):
            issues.append("text_hash_mismatch")
        if response.get("profile_sha256") != identity["profile_sha256"]:
            issues.append("profile_hash_mismatch")
        if response.get("reference_sha256") != identity["reference_sha256"]:
            issues.append("reference_hash_mismatch")
        if response.get("conditioning_reused") is not True:
            issues.append("conditioning_not_reused")
        if (response.get("gpu_proof") or {}).get("actual_gpu_execution") is not True:
            issues.append("gpu_execution_not_proven")
        try:
            actual_target = Path(str(response.get("audio_path") or "")).resolve()
        except (OSError, ValueError):
            actual_target = Path()
        if actual_target != expected_target.resolve() or not expected_target.is_file():
            issues.append("audio_path_or_file_mismatch")
        else:
            actual_wav = validate_wav(expected_target)
            if actual_wav.get("passed") is not True:
                issues.append("wav_validation_failed")
            if actual_wav.get("sha256") != (response.get("wav_validation") or {}).get("sha256"):
                issues.append("wav_hash_mismatch")
        if issues:
            return {
                **response,
                "generated": False,
                "reason": "persistent_candidate_parent_contract_failed",
                "contract_issues": issues,
            }
        return response

    def unload(self) -> dict[str, Any]:
        return self._request("unload")

    def close(self) -> dict[str, Any] | None:
        process = self.process
        if process is None:
            return None
        response: dict[str, Any] | None = None
        forced_termination = False
        if process.poll() is None:
            try:
                response = self._request("shutdown", _timeout_seconds=30.0)
            except Exception:
                response = None
            # Close the exact inherited request pipe as soon as the shutdown
            # response arrives so the worker's bounded stdin-reader thread can
            # observe EOF and exit before interpreter finalization.
            try:
                if process.stdin is not None:
                    process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                # This is the exact Popen child owned by this client, never an
                # arbitrary process discovered by port/name/PID scanning.
                process.terminate()
                forced_termination = True
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        self.process = None
        if response is not None:
            response["owned_process_exit_code"] = process.returncode
            response["owned_process_forced_termination"] = forced_termination
        return response

    def __enter__(self) -> "PersistentBlackwellVoiceCandidateClient":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback_value: Any) -> None:
        self.close()
