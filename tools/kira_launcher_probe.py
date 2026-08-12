"""Strictly isolated hidden proof surface for Kira's two normal launchers.

This module is reached only when an existing launcher receives
``KIRA_LAUNCHER_PROBE=1``.  It deliberately does not import or start the Kira
World shell server: that normal server owns bodies, worlds, devices, Studio,
and browser routes which are outside this proof.  The probe instead exercises
the real ``ConversationLoop`` and approved Kira voice functions behind a tiny
authenticated loopback-only API, with every mutable path redirected beneath a
caller-supplied RecoverySprint directory.

The companion ``run_kira_launcher_probes.py`` is the only supported driver.
It proves Qwen residency separately through Ollama's real ``/api/ps`` and
unloads Qwen before asking this server to synthesize voice with playback off.
"""

from __future__ import annotations

import argparse
import array
import dataclasses
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import socket
import sys
import threading
import time
import uuid
import wave
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib import request
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = (PROJECT_ROOT / "RecoverySprint").resolve()
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
EXPECTED_CONTEXT_LENGTH = 4096
APPROVED_VOICE_PROFILE = PROJECT_ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
APPROVED_VOICE_PROFILE_SHA256 = "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
APPROVED_REFERENCE = (
    PROJECT_ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)
APPROVED_REFERENCE_SHA256 = "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
ALLOWED_LAUNCHERS = frozenset({"text_voice_chat", "world_shell"})
MIN_PROBE_PORT = 49152
MAX_PROBE_PORT = 65535
MAX_REQUEST_BYTES = 32 * 1024
MAX_TYPED_CHARS = 1200
MAX_HTTP_RESPONSE_BYTES = 8 * 1024 * 1024


class ProbeSafetyError(ValueError):
    """Raised before work when the hidden probe contract is unsafe."""


class ProbeRuntimeError(RuntimeError):
    """Raised when a live proof invariant is not met."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_probe_root(raw: str | os.PathLike[str], *, project_root: Path = PROJECT_ROOT) -> Path:
    """Return an absolute strict RecoverySprint descendant without traversal."""

    text = str(raw or "").strip().strip('"')
    if not text:
        raise ProbeSafetyError("KIRA_LAUNCHER_PROBE_ROOT is required")
    supplied = Path(text)
    if not supplied.is_absolute():
        raise ProbeSafetyError("probe root must be an absolute path")
    if ".." in supplied.parts:
        raise ProbeSafetyError("probe root must not contain parent traversal")
    recovery_root = (project_root / "RecoverySprint").resolve()
    candidate = supplied.resolve(strict=False)
    try:
        relative = candidate.relative_to(recovery_root)
    except ValueError as exc:
        raise ProbeSafetyError("probe root must be beneath the repository RecoverySprint directory") from exc
    if not relative.parts:
        raise ProbeSafetyError("probe root must be a strict descendant, not RecoverySprint itself")
    if candidate == recovery_root:
        raise ProbeSafetyError("probe root must be a strict descendant, not RecoverySprint itself")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in relative.parts):
        raise ProbeSafetyError("probe root components may contain only letters, digits, dot, underscore, and hyphen")
    return candidate


def validate_probe_port(raw: str | int) -> int:
    text = str(raw or "").strip()
    if not re.fullmatch(r"[0-9]{5}", text):
        raise ProbeSafetyError("probe port must be a five-digit integer")
    port = int(text)
    if not MIN_PROBE_PORT <= port <= MAX_PROBE_PORT:
        raise ProbeSafetyError(f"probe port must be in {MIN_PROBE_PORT}..{MAX_PROBE_PORT}")
    return port


def require_available_loopback_port(port: int) -> None:
    """Fail before creating evidence if the caller's port is already occupied."""

    safe_port = validate_probe_port(port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", safe_port))
        except OSError as exc:
            raise ProbeSafetyError(f"probe port {safe_port} is unavailable on loopback") from exc


def validate_probe_token(raw: str) -> str:
    token = str(raw or "").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise ProbeSafetyError("KIRA_LAUNCHER_PROBE_TOKEN must be 256-bit lowercase hexadecimal")
    return token


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ProbeSafetyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_strict_json_object(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise ProbeSafetyError("request body must be a non-empty bounded JSON object")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeSafetyError("request body must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ProbeSafetyError("request body must be a JSON object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    actual = set(value)
    if actual != expected:
        raise ProbeSafetyError(
            "request keys must be exactly " + ", ".join(sorted(expected))
        )


def safe_probe_child(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve(strict=False)
    try:
        relative = candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ProbeSafetyError("probe output escaped the isolated root") from exc
    if not relative.parts:
        raise ProbeSafetyError("probe output must be beneath the isolated root")
    return candidate


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def _copy_seed(source: Path, target: Path) -> None:
    if not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ProbeSafetyError(f"isolated seed target already exists: {target}")
    shutil.copyfile(source, target)


def configure_probe_environment() -> None:
    """Pin all model/device capabilities before importing runtime modules."""

    safe_values = {
        "KIRA_MODEL_BACKEND": "ollama",
        "KIRA_MODEL_NAME": EXPECTED_MODEL,
        "KIRA_OLLAMA_ENDPOINT": OLLAMA_BASE_URL + "/api/chat",
        "KIRA_OLLAMA_NUM_CTX": str(EXPECTED_CONTEXT_LENGTH),
        "KIRA_OLLAMA_TIMEOUT": "240",
        "KIRA_MAX_TOKENS": "192",
        "KIRA_WORLD_SHELL_ACTIVE": "0",
        "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
        "KIRA_SHELL_TEXT_ONLY": "1",
        "KIRA_PRE_RAM_KIRA_ONLY": "1",
        "KIRA_PERSONHOOD_EVAL_MODE": "1",
        "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "1",
        "KIRA_VOICE_IDLE_UNLOAD_SECONDS": "0",
        "KIRA_CHATTERBOX_DEVICE": "cpu",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in (
        "KIRA_VOICE_FORCE_SAPI",
        "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR",
        "KIRA_ASR_PORT",
        "KIRA_ASR_SESSION_TOKEN",
    ):
        os.environ.pop(key, None)
    os.environ.update(safe_values)


def _local_ollama_json(
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    if path not in {"/api/tags", "/api/ps", "/api/generate"}:
        raise ProbeSafetyError(f"Ollama route is not allowed in launcher probe: {path}")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    req = request.Request(
        OLLAMA_BASE_URL + path,
        data=body,
        method=method,
        headers={"content-type": "application/json"} if body is not None else {},
    )
    with request.urlopen(req, timeout=max(1.0, min(60.0, timeout))) as response:
        raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
        raise ProbeRuntimeError("Ollama response exceeded the probe limit")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ProbeRuntimeError("Ollama returned a non-object JSON response")
    return value


def _ollama_models(path: str) -> list[dict[str, Any]]:
    models = _local_ollama_json("GET", path).get("models")
    if not isinstance(models, list):
        raise ProbeRuntimeError(f"{path} did not return a models list")
    if any(not isinstance(item, dict) for item in models):
        raise ProbeRuntimeError(f"{path} returned a malformed model record")
    return [dict(item) for item in models]


def validate_exact_qwen_install_and_clean_start() -> dict[str, Any]:
    exact = []
    for item in _ollama_models("/api/tags"):
        identifiers = {str(item.get("name") or ""), str(item.get("model") or "")}
        if EXPECTED_MODEL in identifiers:
            exact.append(item)
    if len(exact) != 1:
        raise ProbeRuntimeError("exactly one installed qwen3.5:9b record is required")
    digest = str(exact[0].get("digest") or "").casefold()
    if digest != EXPECTED_DIGEST:
        raise ProbeRuntimeError("installed qwen3.5:9b digest does not match the promoted artifact")
    resident = _ollama_models("/api/ps")
    if resident:
        raise ProbeRuntimeError("launcher probe requires an empty Ollama /api/ps at activation")
    return {"model": EXPECTED_MODEL, "digest": digest, "installed_record": exact[0]}


def unload_qwen_and_wait(timeout_seconds: float = 30.0) -> dict[str, Any]:
    response = _local_ollama_json(
        "POST",
        "/api/generate",
        {
            "model": EXPECTED_MODEL,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
            "think": False,
        },
        timeout=30.0,
    )
    deadline = time.monotonic() + max(1.0, min(45.0, timeout_seconds))
    last: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        last = _ollama_models("/api/ps")
        if not last:
            return {"passed": True, "unload_response": response, "resident_models": []}
        time.sleep(0.25)
    return {"passed": False, "unload_response": response, "resident_models": last}


def validate_wav(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 44:
        return {"passed": False, "reason": "wav_missing_or_empty"}
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            frames = handle.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        return {"passed": False, "reason": f"wav_parse_error:{type(exc).__name__}"}
    if sample_width != 2 or channels not in {1, 2} or sample_rate <= 0 or frame_count <= 0:
        return {"passed": False, "reason": "wav_format_invalid"}
    samples = array.array("h")
    samples.frombytes(frames)
    if not samples:
        return {"passed": False, "reason": "wav_has_no_samples"}
    peak = max(abs(int(value)) for value in samples) / 32768.0
    rms = math.sqrt(sum(int(value) ** 2 for value in samples) / len(samples)) / 32768.0
    passed = peak >= 0.001 and rms >= 0.0001
    return {
        "passed": passed,
        "reason": "ok" if passed else "wav_is_silent",
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frames": frame_count,
        "duration_seconds": round(frame_count / sample_rate, 3),
        "peak_normalized": round(peak, 6),
        "rms_normalized": round(rms, 6),
    }


class ProbeSession:
    """One activation, one typed turn, one voice render, then close."""

    def __init__(self, root: Path, launcher_id: str) -> None:
        if launcher_id not in ALLOWED_LAUNCHERS:
            raise ProbeSafetyError("unrecognized launcher id")
        self.root = root
        self.launcher_id = launcher_id
        self.lock = threading.RLock()
        self.state_path = safe_probe_child(root, "state", "launcher_probe_state.json")
        self.person_state_path = safe_probe_child(root, "Data", "person", "kira_probe_person_state.json")
        self.event_log = safe_probe_child(root, "logs", "launcher_probe_events.jsonl")
        self.chat_log = safe_probe_child(root, "logs", "conversation_log.jsonl")
        self.loop: Any | None = None
        self.active = False
        self.chat_count = 0
        self.voice_count = 0
        self.last_reply = ""
        self.created_at = utc_now()
        self._record_state("ready")

    def _record_state(self, phase: str, **changes: Any) -> None:
        state = {
            "schema_version": 1,
            "probe_mode": True,
            "launcher_id": self.launcher_id,
            "phase": phase,
            "active_candidate": "kira" if self.active else "",
            "typed_only": True,
            "voice_playback": False,
            "body_activated": False,
            "world_activated": False,
            "microphone_active": False,
            "asr_active": False,
            "studio_access": False,
            "tablet_access": False,
            "location_routes": False,
            "publication_allowed": False,
            "chat_count": self.chat_count,
            "voice_count": self.voice_count,
            "created_at": self.created_at,
            "updated_at": utc_now(),
            **changes,
        }
        _write_json(self.state_path, state)

    def _event(self, event: str, **values: Any) -> None:
        _append_jsonl(
            self.event_log,
            {"at": utc_now(), "event": event, "launcher_id": self.launcher_id, **values},
        )

    def _seed_isolated_inputs(self) -> None:
        seeds = (
            (PROJECT_ROOT / "Data" / "memories_kira.json", safe_probe_child(self.root, "Data", "memories_kira.json")),
            (
                PROJECT_ROOT / "Data" / "relationships" / "relationship_states.json",
                safe_probe_child(self.root, "Data", "relationships", "relationship_states.json"),
            ),
            (
                PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json",
                safe_probe_child(self.root, "Data", "privacy", "privacy_session_state.json"),
            ),
            (
                PROJECT_ROOT / "Data" / "attention" / "attention_state.json",
                safe_probe_child(self.root, "Data", "attention", "attention_state.json"),
            ),
            (
                PROJECT_ROOT / "Data" / "daily_life" / "runtime" / "kira_daily_life_state.json",
                safe_probe_child(self.root, "Data", "daily_life", "runtime", "kira_daily_life_state.json"),
            ),
        )
        for source, target in seeds:
            _copy_seed(source, target)

    def _build_conversation_loop(self) -> Any:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        core_dir = PROJECT_ROOT / "Core"
        if str(core_dir) not in sys.path:
            sys.path.insert(0, str(core_dir))
        from Core import conversation_loop as conversation_module
        from Core.daily_life_manager import DailyLifeManager as RealDailyLifeManager

        daily_state = safe_probe_child(self.root, "Data", "daily_life", "runtime")
        daily_logs = safe_probe_child(self.root, "Data", "daily_life", "logs", "events")
        reading_sessions = safe_probe_child(self.root, "Data", "reading", "sessions")
        reading_root = safe_probe_child(self.root, "Data", "reading")

        def isolated_daily_life_manager(*_args: Any, **_kwargs: Any) -> Any:
            return RealDailyLifeManager(
                state_dir=daily_state,
                log_dir=daily_logs,
                reading_session_dir=reading_sessions,
                reading_recommendation_dir=reading_root,
            )

        original_daily_manager = conversation_module.DailyLifeManager
        conversation_module.DailyLifeManager = isolated_daily_life_manager
        try:
            loop = conversation_module.ConversationLoop(
                speaker="Kira",
                relationship_state_file=safe_probe_child(
                    self.root, "Data", "relationships", "relationship_states.json"
                ),
                privacy_session_file=safe_probe_child(
                    self.root, "Data", "privacy", "privacy_session_state.json"
                ),
                decision_log_file=safe_probe_child(self.root, "Data", "logs", "decision_log.jsonl"),
                conversation_log_file=self.chat_log,
                attention_state_file=safe_probe_child(
                    self.root, "Data", "attention", "attention_state.json"
                ),
                daily_life_state_dir=daily_state,
                memory_candidate_dir=safe_probe_child(
                    self.root, "Data", "memory_promotion", "candidates"
                ),
            )
            # ConversationLoop's legacy MemoryManager constructor still takes
            # one relative path.  It was created while cwd is the probe root;
            # pin the retained object to that same absolute path so a future
            # cwd change cannot redirect a later explicit memory promotion.
            loop.memory.memory_path = safe_probe_child(self.root, "Data", "memories_kira.json")
            return loop
        finally:
            conversation_module.DailyLifeManager = original_daily_manager

    def activate(self, body: Mapping[str, Any]) -> dict[str, Any]:
        _require_exact_keys(body, {"candidate"})
        if body.get("candidate") != "kira":
            raise ProbeSafetyError("launcher probe can activate only Kira")
        with self.lock:
            if self.active or self.loop is not None:
                raise ProbeSafetyError("Kira may be activated exactly once in a launcher probe")
            install = validate_exact_qwen_install_and_clean_start()
            self._seed_isolated_inputs()
            self.loop = self._build_conversation_loop()
            self.active = True
            _write_json(
                self.person_state_path,
                {
                    "schema_version": 1,
                    "candidate": "kira",
                    "active": True,
                    "interface": "typed_text_and_local_voice_probe",
                    "body_active": False,
                    "world_active": False,
                    "microphone_active": False,
                    "publication_allowed": False,
                    "updated_at": utc_now(),
                },
            )
            self._record_state("active", model=EXPECTED_MODEL, context_length=EXPECTED_CONTEXT_LENGTH)
            self._event("kira_activated", model=EXPECTED_MODEL, digest=EXPECTED_DIGEST)
            return {
                "ok": True,
                "candidate": "kira",
                "label": "Kira",
                "typed_only": True,
                "body_activated": False,
                "world_activated": False,
                "voice_prewarm_started": False,
                "model": install["model"],
                "digest": install["digest"],
                "requested_context_length": EXPECTED_CONTEXT_LENGTH,
            }

    def chat(self, body: Mapping[str, Any]) -> dict[str, Any]:
        _require_exact_keys(body, {"candidate", "text"})
        if body.get("candidate") != "kira":
            raise ProbeSafetyError("launcher probe accepts typed turns only for Kira")
        text = body.get("text")
        if not isinstance(text, str):
            raise ProbeSafetyError("typed chat text must be a string")
        text = text.strip()
        if not text or len(text) > MAX_TYPED_CHARS or "\x00" in text:
            raise ProbeSafetyError(f"typed chat text must contain 1..{MAX_TYPED_CHARS} safe characters")
        with self.lock:
            if not self.active or self.loop is None:
                raise ProbeSafetyError("Kira must be activated before chat")
            if self.chat_count >= 1:
                raise ProbeSafetyError("launcher probe permits exactly one typed chat turn")
            started = time.perf_counter()
            reply = str(self.loop.process(text) or "").strip()
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            if not reply or reply.startswith("[Kira - model offline]") or reply.startswith("[Kira - error]"):
                raise ProbeRuntimeError("real ConversationLoop did not return a live Qwen reply")
            self.chat_count = 1
            self.last_reply = reply
            self._record_state("chat_complete", model=EXPECTED_MODEL, context_length=EXPECTED_CONTEXT_LENGTH)
            self._event(
                "typed_chat_complete",
                candidate="kira",
                request_chars=len(text),
                public_reply_chars=len(reply),
                latency_ms=latency_ms,
            )
            return {
                "ok": True,
                "candidate": "kira",
                "reply": reply,
                "typed_input": True,
                "model": EXPECTED_MODEL,
                "requested_context_length": EXPECTED_CONTEXT_LENGTH,
                "latency_ms": latency_ms,
                "body_action": False,
                "world_action": False,
                "voice_playback": False,
            }

    def synthesize_voice(self, body: Mapping[str, Any]) -> dict[str, Any]:
        _require_exact_keys(body, {"candidate", "source"})
        if body.get("candidate") != "kira" or body.get("source") != "last_public_reply":
            raise ProbeSafetyError("voice proof is bound to Kira's last public reply")
        with self.lock:
            if not self.active or not self.last_reply or self.chat_count != 1:
                raise ProbeSafetyError("one completed Kira chat turn is required before voice proof")
            if self.voice_count >= 1:
                raise ProbeSafetyError("launcher probe permits exactly one voice render")
            if _ollama_models("/api/ps"):
                raise ProbeRuntimeError("Qwen must be unloaded and /api/ps empty before voice synthesis")
            if sha256_file(APPROVED_VOICE_PROFILE) != APPROVED_VOICE_PROFILE_SHA256:
                raise ProbeRuntimeError("approved Kira voice profile hash mismatch")
            if sha256_file(APPROVED_REFERENCE) != APPROVED_REFERENCE_SHA256:
                raise ProbeRuntimeError("approved Kira reference WAV hash mismatch")

            from Core.dialogue_privacy import contains_private_marker
            from Core.voice_output import (
                clean_text_for_speech,
                load_candidate_voice_config,
                release_voice_output,
                synthesize_text_to_wav,
            )

            spoken = clean_text_for_speech(self.last_reply, 0)
            if not spoken or contains_private_marker(spoken):
                raise ProbeRuntimeError("last reply is not a safe public-spoken voice source")
            cfg = load_candidate_voice_config(
                {
                    "candidate_id": "kira",
                    "display_name": "Kira",
                    "gender_preference": "female",
                    "voice_and_behavior": {
                        "voice_profile": "Voice/profiles/temp_ai/kira_voice_profile.json"
                    },
                }
            )
            reference = (PROJECT_ROOT / str(cfg.chatterbox_reference_audio)).resolve()
            if cfg.engine != "chatterbox_tts" or reference != APPROVED_REFERENCE.resolve():
                raise ProbeRuntimeError("approved Kira Chatterbox binding is not exact")
            voice_dir = safe_probe_child(self.root, "Voice", "generated")
            output = safe_probe_child(self.root, "Voice", "generated", "kira_last_public_reply.wav")
            if output.exists():
                raise ProbeSafetyError("voice output already exists; probe outputs are never overwritten")
            safe_cfg = dataclasses.replace(
                cfg,
                enabled=True,
                dry_run=False,
                play_audio=False,
                output_dir=str(voice_dir),
                chatterbox_device="cpu",
            )
            started = time.perf_counter()
            result = synthesize_text_to_wav(spoken, output, config=safe_cfg)
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            wav = validate_wav(output)
            release = release_voice_output()
            if (
                result.get("generated") is not True
                or result.get("engine") != "chatterbox_tts"
                or result.get("playback") is not False
                or wav.get("passed") is not True
            ):
                raise ProbeRuntimeError("approved Kira playback-off voice proof failed")
            self.voice_count = 1
            self._record_state("voice_complete", model_resident=False)
            self._event(
                "approved_voice_rendered",
                output=str(output.relative_to(self.root)).replace("\\", "/"),
                wav_sha256=wav["sha256"],
                latency_ms=latency_ms,
                playback=False,
            )
            return {
                "ok": True,
                "candidate": "kira",
                "engine": "chatterbox_tts",
                "generic_voice_used": False,
                "playback": False,
                "output": str(output.relative_to(self.root)).replace("\\", "/"),
                "approved_voice_profile_sha256": APPROVED_VOICE_PROFILE_SHA256,
                "approved_reference_sha256": APPROVED_REFERENCE_SHA256,
                "latency_ms": latency_ms,
                "wav": wav,
                "voice_release": release,
            }

    def close(self, body: Mapping[str, Any]) -> dict[str, Any]:
        _require_exact_keys(body, {"reason"})
        if body.get("reason") != "controlled_launcher_probe_complete":
            raise ProbeSafetyError("probe close reason is not authorized")
        with self.lock:
            release: dict[str, Any] = {
                "released": False,
                "reason": "voice_module_not_loaded",
                "playback": False,
            }
            try:
                from Core.voice_output import release_voice_output

                release = release_voice_output()
            except ImportError:
                pass
            unload = unload_qwen_and_wait()
            self.active = False
            _write_json(
                self.person_state_path,
                {
                    "schema_version": 1,
                    "candidate": "kira",
                    "active": False,
                    "interface": "closed_launcher_probe",
                    "body_active": False,
                    "world_active": False,
                    "microphone_active": False,
                    "publication_allowed": False,
                    "updated_at": utc_now(),
                },
            )
            self._record_state(
                "closed",
                clean_model_absence=bool(unload.get("passed")),
                clean_voice_release=release.get("reason") in {"model_released", "no_cached_model"},
            )
            self._event(
                "probe_closed",
                model_absent=bool(unload.get("passed")),
                voice_release_reason=release.get("reason"),
            )
            return {
                "ok": bool(unload.get("passed")),
                "closed": True,
                "model_unload": unload,
                "voice_release": release,
                "child_processes_started_by_server": 0,
            }


class ProbeHttpServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], session: ProbeSession, token: str) -> None:
        self.probe_session = session
        self.probe_token = token
        super().__init__(address, ProbeHandler)


class ProbeHandler(BaseHTTPRequestHandler):
    server_version = "KiraLauncherProbe/1"

    @property
    def probe_server(self) -> ProbeHttpServer:
        return self.server  # type: ignore[return-value]

    def _json(self, code: int, value: Mapping[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = str(self.headers.get("x-kira-launcher-probe-token") or "")
        return secrets.compare_digest(supplied, self.probe_server.probe_token)

    def _body(self) -> dict[str, Any]:
        content_type = str(self.headers.get("content-type") or "").split(";", 1)[0].strip().casefold()
        if content_type != "application/json":
            raise ProbeSafetyError("content-type must be application/json")
        raw_length = str(self.headers.get("content-length") or "")
        if not raw_length.isdigit():
            raise ProbeSafetyError("content-length is required")
        length = int(raw_length)
        if not 1 <= length <= MAX_REQUEST_BYTES:
            raise ProbeSafetyError("request body size is outside the probe limit")
        return parse_strict_json_object(self.rfile.read(length))

    def do_GET(self) -> None:
        if self.client_address[0] != "127.0.0.1" or not self._authorized():
            self._json(403, {"ok": False, "error": "forbidden"})
            return
        path = urlparse(self.path).path
        if path != "/healthz":
            self._json(404, {"ok": False, "error": "route_not_available_in_probe"})
            return
        session = self.probe_server.probe_session
        self._json(
            200,
            {
                "ok": True,
                "probe_mode": True,
                "launcher_id": session.launcher_id,
                "typed_kira_only": True,
                "model": EXPECTED_MODEL,
                "context_length": EXPECTED_CONTEXT_LENGTH,
                "root": str(session.root),
                "forbidden_capabilities_loaded": [],
            },
        )

    def do_POST(self) -> None:
        if self.client_address[0] != "127.0.0.1" or not self._authorized():
            self._json(403, {"ok": False, "error": "forbidden"})
            return
        path = urlparse(self.path).path
        routes = {
            "/api/activate": self.probe_server.probe_session.activate,
            "/api/chat": self.probe_server.probe_session.chat,
            "/api/voice": self.probe_server.probe_session.synthesize_voice,
            "/api/close": self.probe_server.probe_session.close,
        }
        operation = routes.get(path)
        if operation is None:
            self._json(404, {"ok": False, "error": "route_not_available_in_probe"})
            return
        try:
            result = operation(self._body())
        except ProbeSafetyError as exc:
            self._json(400, {"ok": False, "error": "probe_safety_rejection", "reason": str(exc)})
            return
        except Exception as exc:
            self._json(
                500,
                {
                    "ok": False,
                    "error": "probe_runtime_failure",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )
            return
        self._json(200, result)
        if path == "/api/close":
            threading.Thread(target=self.probe_server.shutdown, daemon=True).start()

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def prepare_unique_probe_root(root: Path) -> None:
    if root.exists():
        if not root.is_dir():
            raise ProbeSafetyError("probe root exists but is not a directory")
        if any(root.iterdir()):
            raise ProbeSafetyError("probe root must be new or empty; proof roots are never reused")
    else:
        root.mkdir(parents=True, exist_ok=False)


def serve(*, launcher_id: str, probe_root: str, port: str | int, token: str) -> int:
    if launcher_id not in ALLOWED_LAUNCHERS:
        raise ProbeSafetyError("launcher id is not one of the two normal Kira launchers")
    root = resolve_probe_root(probe_root)
    safe_port = validate_probe_port(port)
    safe_token = validate_probe_token(token)
    if str(os.environ.get("KIRA_LAUNCHER_PROBE") or "") != "1":
        raise ProbeSafetyError("hidden launcher probe mode was not explicitly enabled")
    if resolve_probe_root(os.environ.get("KIRA_LAUNCHER_PROBE_ROOT", "")) != root:
        raise ProbeSafetyError("probe root argument does not match launcher environment")
    if validate_probe_port(os.environ.get("KIRA_LAUNCHER_PROBE_PORT", "")) != safe_port:
        raise ProbeSafetyError("probe port argument does not match launcher environment")
    if validate_probe_token(os.environ.get("KIRA_LAUNCHER_PROBE_TOKEN", "")) != safe_token:
        raise ProbeSafetyError("probe token argument does not match launcher environment")

    require_available_loopback_port(safe_port)
    prepare_unique_probe_root(root)
    configure_probe_environment()
    os.chdir(root)
    session = ProbeSession(root, launcher_id)
    server = ProbeHttpServer(("127.0.0.1", safe_port), session, safe_token)
    print(
        json.dumps(
            {
                "event": "kira_launcher_probe_ready",
                "launcher_id": launcher_id,
                "port": safe_port,
                "root": str(root),
                "pid": os.getpid(),
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        try:
            unload_qwen_and_wait(timeout_seconds=10.0)
        except Exception:
            pass
        try:
            from Core.voice_output import release_voice_output

            release_voice_output()
        except Exception:
            pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve_parser = subparsers.add_parser("serve", help="serve one hidden launcher probe")
    serve_parser.add_argument("--launcher-id", required=True, choices=sorted(ALLOWED_LAUNCHERS))
    serve_parser.add_argument("--probe-root", required=True)
    serve_parser.add_argument("--port", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "serve":
            return serve(
                launcher_id=args.launcher_id,
                probe_root=args.probe_root,
                port=args.port,
                token=os.environ.get("KIRA_LAUNCHER_PROBE_TOKEN", ""),
            )
    except (ProbeSafetyError, ProbeRuntimeError, OSError, ValueError) as exc:
        print(f"Kira launcher probe refused to start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
