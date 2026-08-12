"""Controlled live proof driver for Kira's two existing normal launchers.

Nothing live runs without ``--execute-live-proofs``.  When explicitly enabled,
the driver invokes each existing BAT launcher through its hidden isolated
branch, submits one typed Kira turn through the real ConversationLoop, proves
the exact promoted Qwen artifact and 4096 context through Ollama ``/api/ps``,
unloads Qwen, renders the approved Kira voice with playback off, closes the
launcher, and verifies protected hashes plus clean process/model absence.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.kira_launcher_probe import (  # noqa: E402
    EXPECTED_CONTEXT_LENGTH,
    EXPECTED_DIGEST,
    EXPECTED_MODEL,
    MAX_HTTP_RESPONSE_BYTES,
    ProbeRuntimeError,
    ProbeSafetyError,
    resolve_probe_root,
    validate_probe_port,
)
from tools.run_qwen_text_voice_acceptance import (  # noqa: E402
    SafeOllamaClient,
    compare_protected_hashes,
    hash_protected_files,
    inspect_expected_model_residency,
    validate_exact_install,
    wait_for_model_state,
)


LAUNCHERS: tuple[tuple[str, str], ...] = (
    ("text_voice_chat", "Start_Kira_Text_Voice_Chat.bat"),
    ("world_shell", "Start_Kira_World_Shell.bat"),
)
PROBE_PATHS = frozenset({"/healthz", "/api/activate", "/api/chat", "/api/voice", "/api/close"})
TYPED_PROOF_PROMPT = (
    "Tell me one small thing you are curious about today. Reply in one short sentence."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def sanitized_launcher_environment(root: Path, port: int, token: str) -> dict[str, str]:
    """Pass only OS essentials plus the exact hidden-probe contract."""

    allowed = (
        "SystemRoot",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
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
    env.update(
        {
            "KIRA_LAUNCHER_PROBE": "1",
            "KIRA_LAUNCHER_PROBE_ROOT": str(root),
            "KIRA_LAUNCHER_PROBE_PORT": str(port),
            "KIRA_LAUNCHER_PROBE_TOKEN": token,
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
    )
    return env


def probe_json_request(
    port: int,
    token: str,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    if path not in PROBE_PATHS:
        raise ProbeSafetyError(f"launcher proof route is outside the allowlist: {path}")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    req = request.Request(
        f"http://127.0.0.1:{validate_probe_port(port)}{path}",
        data=body,
        method=method,
        headers={
            "x-kira-launcher-probe-token": token,
            **({"content-type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with request.urlopen(req, timeout=max(1.0, min(600.0, timeout))) as response:
            raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        raw = exc.read(MAX_HTTP_RESPONSE_BYTES + 1)
        detail = raw.decode("utf-8", errors="replace")[:2000]
        raise ProbeRuntimeError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
        raise ProbeRuntimeError("launcher probe response exceeded 8 MiB")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ProbeRuntimeError("launcher probe returned a non-object JSON response")
    return value


def wait_for_probe_ready(
    process: subprocess.Popen[str],
    *,
    port: int,
    token: str,
    launcher_id: str,
    root: Path,
    timeout: float = 30.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(2.0, min(60.0, timeout))
    last_error = "server did not answer"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ProbeRuntimeError(
                f"{launcher_id} launcher exited before readiness with code {process.returncode}"
            )
        try:
            health = probe_json_request(port, token, "GET", "/healthz", timeout=2.0)
            if (
                health.get("ok") is True
                and health.get("probe_mode") is True
                and health.get("launcher_id") == launcher_id
                and health.get("typed_kira_only") is True
                and health.get("model") == EXPECTED_MODEL
                and health.get("context_length") == EXPECTED_CONTEXT_LENGTH
                and Path(str(health.get("root") or "")).resolve() == root.resolve()
                and health.get("forbidden_capabilities_loaded") == []
            ):
                return health
            last_error = "health response did not match the exact probe contract"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    raise ProbeRuntimeError(f"{launcher_id} launcher readiness timed out: {last_error}")


def _process_snapshot(process: subprocess.Popen[str]) -> list[dict[str, Any]]:
    try:
        import psutil

        root = psutil.Process(process.pid)
        records = [root, *root.children(recursive=True)]
        return [
            {
                "pid": item.pid,
                "create_time": item.create_time(),
                "name": item.name(),
                "cmdline": item.cmdline(),
            }
            for item in records
        ]
    except Exception:
        return [{"pid": process.pid, "create_time": None, "name": "", "cmdline": []}]


def _prove_processes_absent(records: list[dict[str, Any]]) -> dict[str, Any]:
    remaining: list[dict[str, Any]] = []
    try:
        import psutil

        for record in records:
            pid = int(record.get("pid") or 0)
            if pid <= 0 or not psutil.pid_exists(pid):
                continue
            try:
                current = psutil.Process(pid)
                prior_created = record.get("create_time")
                if prior_created is not None and abs(current.create_time() - float(prior_created)) > 0.01:
                    continue
                remaining.append({"pid": pid, "name": current.name(), "cmdline": current.cmdline()})
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
    except Exception as exc:
        return {"passed": False, "remaining": remaining, "error": f"{type(exc).__name__}: {exc}"}
    return {"passed": not remaining, "remaining": remaining}


def _terminate_owned_process_tree(process: subprocess.Popen[str]) -> dict[str, Any]:
    """Terminate only the launcher process and descendants created beneath it."""

    terminated: list[int] = []
    killed: list[int] = []
    errors: list[str] = []
    try:
        import psutil

        try:
            parent = psutil.Process(process.pid)
            descendants = parent.children(recursive=True)
        except psutil.NoSuchProcess:
            descendants = []
            parent = None
        for child in reversed(descendants):
            try:
                child.terminate()
                terminated.append(child.pid)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
            except Exception as exc:
                errors.append(f"terminate child {child.pid}: {type(exc).__name__}: {exc}")
        _, alive = psutil.wait_procs(descendants, timeout=8.0)
        for child in alive:
            try:
                child.kill()
                killed.append(child.pid)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
            except Exception as exc:
                errors.append(f"kill child {child.pid}: {type(exc).__name__}: {exc}")
        if alive:
            psutil.wait_procs(alive, timeout=5.0)
        if parent is not None:
            try:
                parent.terminate()
                terminated.append(parent.pid)
                parent.wait(timeout=5.0)
            except psutil.TimeoutExpired:
                parent.kill()
                killed.append(parent.pid)
                parent.wait(timeout=5.0)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
    except Exception as exc:
        errors.append(f"psutil cleanup failed: {type(exc).__name__}: {exc}")
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5.0)
                terminated.append(process.pid)
            except Exception as fallback_exc:
                errors.append(f"fallback cleanup failed: {type(fallback_exc).__name__}: {fallback_exc}")
    return {"passed": process.poll() is not None and not errors, "terminated_pids": terminated, "killed_pids": killed, "errors": errors}


def _find_chatterbox_sidecars() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    try:
        import psutil

        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = [str(item) for item in (process.info.get("cmdline") or [])]
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            joined = " ".join(cmdline).replace("\\", "/").casefold()
            if "voice/sidecars/chatterbox_py311/sidecar_worker.py" in joined:
                found.append({"pid": process.info.get("pid"), "name": process.info.get("name"), "cmdline": cmdline})
    except Exception as exc:
        found.append({"probe_error": f"{type(exc).__name__}: {exc}"})
    return found


def _artifact_inventory(root: Path) -> dict[str, Any]:
    records = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
        records.append(
            {
                "path": str(resolved.relative_to(root.resolve())).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
            }
        )
    forbidden = [
        item["path"]
        for item in records
        if item["path"].casefold().endswith((".glb", ".gltf", ".blend", ".mp4", ".webm"))
    ]
    return {"passed": not forbidden, "file_count": len(records), "files": records, "forbidden_artifacts": forbidden}


def run_one_launcher(
    *,
    launcher_id: str,
    launcher_name: str,
    root: Path,
    port: int,
    ollama: SafeOllamaClient,
) -> dict[str, Any]:
    launcher = PROJECT_ROOT / launcher_name
    if not launcher.is_file():
        raise ProbeRuntimeError(f"launcher is missing: {launcher_name}")
    if root.exists():
        raise ProbeSafetyError(f"launcher-specific probe root already exists: {root}")
    token = secrets.token_hex(32)
    environment = sanitized_launcher_environment(root, port, token)
    comspec = environment.get("ComSpec") or environment.get("COMSPEC") or "cmd.exe"
    started_at = utc_now()
    process = subprocess.Popen(
        [comspec, "/d", "/c", str(launcher)],
        cwd=str(PROJECT_ROOT),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    snapshot: list[dict[str, Any]] = []
    closed = False
    evidence: dict[str, Any] = {
        "launcher_id": launcher_id,
        "launcher": launcher_name,
        "root": str(root),
        "port": port,
        "started_at": started_at,
        "process_pid": process.pid,
    }
    try:
        evidence["health"] = wait_for_probe_ready(
            process,
            port=port,
            token=token,
            launcher_id=launcher_id,
            root=root,
        )
        snapshot = _process_snapshot(process)
        activation = probe_json_request(
            port,
            token,
            "POST",
            "/api/activate",
            {"candidate": "kira"},
            timeout=30.0,
        )
        if (
            activation.get("ok") is not True
            or activation.get("candidate") != "kira"
            or activation.get("model") != EXPECTED_MODEL
            or activation.get("digest") != EXPECTED_DIGEST
            or activation.get("requested_context_length") != EXPECTED_CONTEXT_LENGTH
            or activation.get("body_activated") is not False
            or activation.get("world_activated") is not False
        ):
            raise ProbeRuntimeError("activation response did not meet the Kira-only contract")
        evidence["activation"] = activation

        chat = probe_json_request(
            port,
            token,
            "POST",
            "/api/chat",
            {"candidate": "kira", "text": TYPED_PROOF_PROMPT},
            timeout=300.0,
        )
        if (
            chat.get("ok") is not True
            or chat.get("candidate") != "kira"
            or not str(chat.get("reply") or "").strip()
            or chat.get("model") != EXPECTED_MODEL
            or chat.get("requested_context_length") != EXPECTED_CONTEXT_LENGTH
            or chat.get("body_action") is not False
            or chat.get("world_action") is not False
            or chat.get("voice_playback") is not False
        ):
            raise ProbeRuntimeError("typed chat response did not meet the exact launcher proof contract")
        evidence["chat"] = chat

        loaded = wait_for_model_state(
            ollama,
            loaded=True,
            timeout_seconds=30.0,
            required_context_length=EXPECTED_CONTEXT_LENGTH,
        )
        if loaded.get("passed") is not True:
            raise ProbeRuntimeError("Ollama /api/ps did not prove exact Qwen digest and context")
        evidence["loaded_model_proof"] = loaded

        evidence["driver_unload_response"] = dict(ollama.unload())
        absence_before_voice = wait_for_model_state(
            ollama,
            loaded=False,
            timeout_seconds=30.0,
        )
        if absence_before_voice.get("passed") is not True or ollama.ps():
            raise ProbeRuntimeError("Qwen did not reach clean /api/ps absence before voice")
        evidence["absence_before_voice"] = absence_before_voice

        voice = probe_json_request(
            port,
            token,
            "POST",
            "/api/voice",
            {"candidate": "kira", "source": "last_public_reply"},
            timeout=600.0,
        )
        if (
            voice.get("ok") is not True
            or voice.get("candidate") != "kira"
            or voice.get("engine") != "chatterbox_tts"
            or voice.get("generic_voice_used") is not False
            or voice.get("playback") is not False
            or not isinstance(voice.get("wav"), dict)
            or voice["wav"].get("passed") is not True
        ):
            raise ProbeRuntimeError("approved Kira voice response did not meet the proof contract")
        evidence["voice"] = voice

        close = probe_json_request(
            port,
            token,
            "POST",
            "/api/close",
            {"reason": "controlled_launcher_probe_complete"},
            timeout=45.0,
        )
        closed = True
        if close.get("ok") is not True or close.get("closed") is not True:
            raise ProbeRuntimeError("launcher close did not prove clean model unload")
        evidence["close"] = close
        stdout, stderr = process.communicate(timeout=45.0)
        evidence["launcher_exit_code"] = process.returncode
        if process.returncode != 0:
            raise ProbeRuntimeError(f"launcher exited with code {process.returncode}")
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "launcher_stdout.log").write_text(stdout, encoding="utf-8")
        (root / "logs" / "launcher_stderr.log").write_text(stderr, encoding="utf-8")

        final_models = ollama.ps()
        final_inspection = inspect_expected_model_residency(final_models)
        evidence["final_model_absence"] = {
            "passed": not final_models and final_inspection.get("clean_absence") is True,
            "models": final_models,
            "identity_inspection": final_inspection,
        }
        evidence["process_absence"] = _prove_processes_absent(snapshot)
        evidence["chatterbox_sidecar_absence"] = {
            "passed": not (sidecars := _find_chatterbox_sidecars()),
            "processes": sidecars,
        }
        evidence["artifacts"] = _artifact_inventory(root)
        evidence["passed"] = all(
            item.get("passed") is True
            for item in (
                evidence["loaded_model_proof"],
                evidence["absence_before_voice"],
                evidence["final_model_absence"],
                evidence["process_absence"],
                evidence["chatterbox_sidecar_absence"],
                evidence["artifacts"],
            )
        )
        evidence["completed_at"] = utc_now()
        return evidence
    finally:
        if process.poll() is None:
            if not closed:
                try:
                    probe_json_request(
                        port,
                        token,
                        "POST",
                        "/api/close",
                        {"reason": "controlled_launcher_probe_complete"},
                        timeout=15.0,
                    )
                except Exception:
                    pass
            try:
                process.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                _terminate_owned_process_tree(process)
        try:
            ollama.unload()
            wait_for_model_state(ollama, loaded=False, timeout_seconds=15.0)
        except Exception:
            pass


def prepare_run_root(raw: str) -> Path:
    root = resolve_probe_root(raw)
    if root.exists():
        if not root.is_dir() or any(root.iterdir()):
            raise ProbeSafetyError("driver probe root must be new or empty")
    return root


def run_live_proofs(root: Path, text_voice_port: int, world_shell_port: int) -> dict[str, Any]:
    if text_voice_port == world_shell_port:
        raise ProbeSafetyError("the two launchers require distinct high ports")
    if root.exists():
        if any(root.iterdir()):
            raise ProbeSafetyError("driver probe root is not empty")
    else:
        root.mkdir(parents=True, exist_ok=False)

    report: dict[str, Any] = {
        "schema_version": 1,
        "suite": "qwen_normal_launcher_isolated_proofs_v1",
        "started_at": utc_now(),
        "expected_model": EXPECTED_MODEL,
        "expected_digest": EXPECTED_DIGEST,
        "expected_context_length": EXPECTED_CONTEXT_LENGTH,
        "probe_root": str(root),
        "ports": {"text_voice_chat": text_voice_port, "world_shell": world_shell_port},
        "live_execution_authorized": True,
        "launchers": [],
    }
    protected_before = hash_protected_files()
    report["protected_before"] = protected_before
    ollama = SafeOllamaClient(timeout_seconds=300.0, max_chat_requests=1)
    report["installed_model"] = validate_exact_install(ollama.tags())
    preflight_models = ollama.ps()
    if preflight_models:
        raise ProbeRuntimeError("launcher proof requires an empty Ollama /api/ps preflight")
    report["preflight_model_absence"] = {"passed": True, "models": []}

    ports = {"text_voice_chat": text_voice_port, "world_shell": world_shell_port}
    for launcher_id, launcher_name in LAUNCHERS:
        launcher_root = root / launcher_id
        try:
            result = run_one_launcher(
                launcher_id=launcher_id,
                launcher_name=launcher_name,
                root=launcher_root,
                port=ports[launcher_id],
                ollama=ollama,
            )
        except Exception as exc:
            result = {
                "launcher_id": launcher_id,
                "launcher": launcher_name,
                "root": str(launcher_root),
                "port": ports[launcher_id],
                "passed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        report["launchers"].append(result)

    protected_after = hash_protected_files()
    report["protected_after"] = protected_after
    report["protected_integrity"] = compare_protected_hashes(protected_before, protected_after)
    final_models = ollama.ps()
    report["final_model_absence"] = {
        "passed": not final_models,
        "models": final_models,
        "identity_inspection": inspect_expected_model_residency(final_models),
    }
    report["final_chatterbox_sidecar_absence"] = {
        "passed": not (sidecars := _find_chatterbox_sidecars()),
        "processes": sidecars,
    }
    report["completed_at"] = utc_now()
    report["passed"] = (
        len(report["launchers"]) == 2
        and all(item.get("passed") is True for item in report["launchers"])
        and report["protected_integrity"].get("passed") is True
        and report["final_model_absence"].get("passed") is True
        and report["final_chatterbox_sidecar_absence"].get("passed") is True
    )
    _write_json(root / "launcher_probe_report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live-proofs", action="store_true")
    parser.add_argument("--probe-root", required=True)
    parser.add_argument("--text-voice-port", required=True)
    parser.add_argument("--world-shell-port", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = prepare_run_root(args.probe_root)
        text_voice_port = validate_probe_port(args.text_voice_port)
        world_shell_port = validate_probe_port(args.world_shell_port)
        if text_voice_port == world_shell_port:
            raise ProbeSafetyError("the two launchers require distinct high ports")
        if not args.execute_live_proofs:
            print(
                json.dumps(
                    {
                        "live_execution": False,
                        "status": "plan_only",
                        "probe_root": str(root),
                        "ports": {
                            "text_voice_chat": text_voice_port,
                            "world_shell": world_shell_port,
                        },
                        "launchers": [name for _, name in LAUNCHERS],
                        "next_step": "rerun with --execute-live-proofs only in a controlled empty-model window",
                    },
                    indent=2,
                )
            )
            return 0
        report = run_live_proofs(root, text_voice_port, world_shell_port)
        print(json.dumps({"passed": report["passed"], "report": str(root / "launcher_probe_report.json")}, indent=2))
        return 0 if report["passed"] else 1
    except Exception as exc:
        print(f"Kira launcher proofs failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
