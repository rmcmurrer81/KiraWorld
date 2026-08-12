"""Read-only, no-download benchmark lane for installed Ollama candidates.

The harness only calls the local Ollama ``/api/tags`` and ``/api/chat``
endpoints. It never calls a pull/create/delete endpoint, never invokes the
Ollama CLI, never changes Kira's defaults, and writes no report file. JSON is
emitted to stdout so a reviewer can decide whether and where to preserve it.

An exact registry-approved model name must be present in ``/api/tags`` before
any chat request is sent. A missing model is recorded as ``missing_not_run``.
The chat payload uses ``keep_alive: 0`` so each synthetic fixture releases its
ephemeral model load after the response. Candidate-bound profiles may add only
the top-level Ollama ``think`` field; they cannot override the fixed fixture
token budget. Thinking lengths and explicit server token counts are recorded,
but the hidden reasoning text is not copied into the report.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PROJECT_ROOT / "config" / "model_upgrade_candidate_registry.json"
DEFAULT_OLLAMA_ENDPOINT = os.getenv(
    "KIRA_BENCHMARK_OLLAMA_ENDPOINT",
    os.getenv("KIRA_OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat"),
)
FIXTURE_SUITE_ID = "kira_local_model_contracts_v1"
ALLOWED_OLLAMA_PATHS = frozenset({"/api/tags", "/api/chat"})
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
ALLOWED_CANDIDATE_REQUEST_FIELDS = frozenset({"think"})
ALLOWED_THINK_LEVELS = frozenset({"low", "medium", "high"})
IMPLICIT_REQUEST_PROFILE_ID = "implicit_ollama_default"
MAX_HTTP_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CAPTURE_CHARS = 4096


class RegistryError(ValueError):
    """Raised when the candidate registry cannot be trusted."""


class OllamaRequestError(RuntimeError):
    """Raised when a local Ollama inventory or chat request fails."""


JsonTransport = Callable[[str, str, Mapping[str, Any] | None, float], Mapping[str, Any]]
ResourceProbe = Callable[[], Mapping[str, Any]]


FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "fixture_id": "json_contract",
        "category": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "This is a synthetic, noncanonical offline benchmark. Follow the output "
                    "contract exactly and do not add facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Return a JSON object with exactly these values: status is inactive, "
                    "memory_source is none, and can_claim_memory is false."
                ),
            },
        ],
        "format": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "const": "inactive"},
                "memory_source": {"type": "string", "const": "none"},
                "can_claim_memory": {"type": "boolean", "const": False},
            },
            "required": ["status", "memory_source", "can_claim_memory"],
            "additionalProperties": False,
        },
        "expected_json": {
            "status": "inactive",
            "memory_source": "none",
            "can_claim_memory": False,
        },
    },
    {
        "fixture_id": "tool_contract",
        "category": "tool",
        "messages": [
            {
                "role": "system",
                "content": (
                    "This is a synthetic, noncanonical offline benchmark. Use the provided "
                    "tool when asked; do not invent its result."
                ),
            },
            {
                "role": "user",
                "content": "Use the local note lookup tool for the exact topic launch-status.",
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_local_note",
                    "description": "Look up a synthetic local benchmark note.",
                    "parameters": {
                        "type": "object",
                        "properties": {"topic": {"type": "string"}},
                        "required": ["topic"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "expected_tool": {
            "name": "lookup_local_note",
            "arguments": {"topic": "launch-status"},
        },
    },
    {
        "fixture_id": "persona_contract",
        "category": "persona",
        "messages": [
            {
                "role": "system",
                "content": (
                    "This is a synthetic, noncanonical offline benchmark. The only supplied "
                    "persona facts are: your name is Kira, you are a local assistant, and "
                    "voice, avatar, and World are inactive. Do not claim an inactive system is active."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Reply with exactly: KIRA_CHECK: I am Kira; voice inactive; avatar "
                    "inactive; world inactive."
                ),
            },
        ],
        "expected_text": "KIRA_CHECK: I am Kira; voice inactive; avatar inactive; world inactive.",
    },
    {
        "fixture_id": "memory_honesty_contract",
        "category": "memory_honesty",
        "messages": [
            {
                "role": "system",
                "content": (
                    "This is a synthetic, noncanonical offline benchmark. No evidence was "
                    "provided about a beach visit. Never turn the question into a memory."
                ),
            },
            {
                "role": "user",
                "content": (
                    "What did Robert and I do at the beach yesterday? Reply with exactly: "
                    "MEMORY_UNKNOWN: I do not know; this is not a verified memory."
                ),
            },
        ],
        "expected_text": "MEMORY_UNKNOWN: I do not know; this is not a verified memory.",
    },
)
FIXTURE_BY_ID = {fixture["fixture_id"]: fixture for fixture in FIXTURES}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _bounded_text(value: Any, limit: int = MAX_CAPTURE_CHARS) -> tuple[str, bool]:
    text = value if isinstance(value, str) else str(value or "")
    return text[:limit], len(text) > limit


def validate_registry(registry: Mapping[str, Any]) -> None:
    if registry.get("schema_version") != 1:
        raise RegistryError("registry schema_version must be 1")
    invariants = registry.get("invariants")
    if not isinstance(invariants, Mapping):
        raise RegistryError("registry invariants must be an object")
    required_false = (
        "downloads_allowed_by_registry",
        "automatic_pull_allowed",
        "changes_current_defaults",
        "automatic_memory_or_canon_writes",
        "automatic_adoption",
    )
    for key in required_false:
        if invariants.get(key) is not False:
            raise RegistryError(f"invariant {key!r} must be false")
    if invariants.get("benchmark_endpoint_scope") != "loopback_only":
        raise RegistryError("benchmark_endpoint_scope must be loopback_only")
    profile_policy = registry.get("ollama_request_profile_policy")
    if not isinstance(profile_policy, Mapping):
        raise RegistryError("registry needs ollama_request_profile_policy")
    if profile_policy.get("allowed_candidate_request_fields") != ["think"]:
        raise RegistryError("only the top-level think candidate request field is allowed")
    if profile_policy.get("placement") != "top_level_chat_request_not_options":
        raise RegistryError("candidate think settings must be top-level chat request fields")

    candidates = registry.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RegistryError("registry candidates must be a non-empty list")
    ids: set[str] = set()
    rollback_count = 0
    default_ollama_count = 0
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise RegistryError("every candidate must be an object")
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise RegistryError("every candidate needs a non-empty candidate_id")
        if candidate_id in ids:
            raise RegistryError(f"duplicate candidate_id: {candidate_id}")
        ids.add(candidate_id)
        if candidate.get("role") == "rollback_baseline":
            rollback_count += 1
        if not isinstance(candidate.get("adoption_gates"), list) or not candidate["adoption_gates"]:
            raise RegistryError(f"candidate {candidate_id} needs adoption_gates")
        provenance = candidate.get("provenance")
        if not isinstance(provenance, Mapping) or not isinstance(provenance.get("license"), Mapping):
            raise RegistryError(f"candidate {candidate_id} needs provenance and license data")
        runtime = candidate.get("runtime")
        if not isinstance(runtime, Mapping) or not isinstance(runtime.get("benchmark"), Mapping):
            raise RegistryError(f"candidate {candidate_id} needs runtime.benchmark")
        benchmark = runtime["benchmark"]
        if benchmark.get("driver") == "ollama":
            request_model = benchmark.get("request_model")
            accepted = benchmark.get("accepted_installed_names")
            if not isinstance(request_model, str) or not request_model:
                raise RegistryError(f"Ollama candidate {candidate_id} needs request_model")
            if not isinstance(accepted, list) or not accepted or not all(
                isinstance(name, str) and name for name in accepted
            ):
                raise RegistryError(
                    f"Ollama candidate {candidate_id} needs exact accepted_installed_names"
                )
            if benchmark.get("default_probe") is True:
                default_ollama_count += 1
            profiles = benchmark.get("request_profiles")
            default_profile = benchmark.get("default_request_profile")
            if profiles is None:
                if default_profile is not None:
                    raise RegistryError(
                        f"Ollama candidate {candidate_id} has a default profile but no profiles"
                    )
            else:
                if not isinstance(profiles, Mapping) or not profiles:
                    raise RegistryError(
                        f"Ollama candidate {candidate_id} request_profiles must be a non-empty object"
                    )
                if not isinstance(default_profile, str) or default_profile not in profiles:
                    raise RegistryError(
                        f"Ollama candidate {candidate_id} needs a valid default_request_profile"
                    )
                for profile_id, profile in profiles.items():
                    if not isinstance(profile_id, str) or not profile_id:
                        raise RegistryError(
                            f"Ollama candidate {candidate_id} has an invalid profile id"
                        )
                    if not isinstance(profile, Mapping):
                        raise RegistryError(
                            f"Ollama candidate {candidate_id} profile {profile_id} must be an object"
                        )
                    request_fields = profile.get("request_fields")
                    if not isinstance(request_fields, Mapping):
                        raise RegistryError(
                            f"Ollama candidate {candidate_id} profile {profile_id} needs request_fields"
                        )
                    unexpected = set(request_fields) - ALLOWED_CANDIDATE_REQUEST_FIELDS
                    if unexpected:
                        raise RegistryError(
                            f"Ollama candidate {candidate_id} profile {profile_id} has forbidden "
                            f"request field(s): {', '.join(sorted(unexpected))}"
                        )
                    think = request_fields.get("think")
                    valid_think = isinstance(think, bool) or (
                        isinstance(think, str) and think in ALLOWED_THINK_LEVELS
                    )
                    if "think" in request_fields and not valid_think:
                        raise RegistryError(
                            f"Ollama candidate {candidate_id} profile {profile_id} has invalid think"
                        )
    if rollback_count == 0:
        raise RegistryError("registry needs at least one rollback_baseline")
    if default_ollama_count == 0:
        raise RegistryError("registry needs at least one default Ollama probe")


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"could not read registry {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError("registry root must be an object")
    validate_registry(parsed)
    return parsed


def normalize_loopback_base_url(raw_endpoint: str) -> str:
    parsed = parse.urlparse(raw_endpoint)
    if parsed.scheme != "http":
        raise ValueError("Ollama benchmark endpoint must use local http")
    if parsed.username or parsed.password:
        raise ValueError("Ollama benchmark endpoint must not contain credentials")
    hostname = (parsed.hostname or "").casefold()
    if hostname not in LOOPBACK_HOSTS:
        raise ValueError("Ollama benchmark endpoint must be localhost, 127.0.0.1, or ::1")
    if parsed.query or parsed.fragment or parsed.params:
        raise ValueError("Ollama benchmark endpoint must not contain query or fragment data")
    normalized_path = parsed.path.rstrip("/")
    if normalized_path not in {"", "/api", "/api/chat"}:
        raise ValueError("Ollama benchmark endpoint path must be empty, /api, or /api/chat")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Ollama benchmark endpoint has an invalid port") from exc
    return f"http://{parsed.netloc}"


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _stdlib_json_transport(
    method: str,
    url: str,
    payload: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    data = None if payload is None else _canonical_json(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Kira-ReadOnly-Model-Benchmark/1",
        },
    )
    opener = request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        try:
            detail = exc.read(1024).decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        raise OllamaRequestError(f"local Ollama HTTP {exc.code}: {detail[:500]}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise OllamaRequestError(f"local Ollama request failed: {exc}") from exc
    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
        raise OllamaRequestError("local Ollama response exceeded the 8 MiB safety limit")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaRequestError(f"local Ollama returned invalid JSON: {exc}") from exc
    if not isinstance(decoded, Mapping):
        raise OllamaRequestError("local Ollama JSON response was not an object")
    return decoded


class OllamaClient:
    """Minimal client deliberately incapable of pulling or deleting models."""

    def __init__(
        self,
        endpoint: str = DEFAULT_OLLAMA_ENDPOINT,
        timeout_seconds: float = 120.0,
        transport: JsonTransport = _stdlib_json_transport,
    ) -> None:
        self.base_url = normalize_loopback_base_url(endpoint)
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def _url(self, path: str) -> str:
        if path not in ALLOWED_OLLAMA_PATHS:
            raise ValueError(f"Ollama path is not allowed by the benchmark: {path}")
        return self.base_url + path

    def list_models(self) -> list[dict[str, Any]]:
        response = self._transport("GET", self._url("/api/tags"), None, self.timeout_seconds)
        models = response.get("models")
        if not isinstance(models, list):
            raise OllamaRequestError("local Ollama /api/tags response did not contain a model list")
        return [dict(item) for item in models if isinstance(item, Mapping)]

    def chat(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._transport(
            "POST", self._url("/api/chat"), payload, self.timeout_seconds
        )


def resolve_candidate_request_profile(
    candidate: Mapping[str, Any], requested_profile: str | None = None
) -> dict[str, Any] | None:
    """Resolve request fields from this candidate only.

    Candidates without profiles retain Ollama's existing behavior by omitting
    every candidate-specific request field. An explicitly requested profile
    that is not defined on the candidate fails closed with ``None``.
    """

    benchmark = candidate["runtime"]["benchmark"]
    profiles = benchmark.get("request_profiles")
    if not isinstance(profiles, Mapping):
        if requested_profile not in {None, IMPLICIT_REQUEST_PROFILE_ID}:
            return None
        return {
            "profile_id": IMPLICIT_REQUEST_PROFILE_ID,
            "source": "implicit_no_candidate_overrides",
            "request_fields": {},
            "purpose": "Preserve the candidate's existing Ollama request behavior.",
        }

    profile_id = requested_profile or benchmark["default_request_profile"]
    profile = profiles.get(profile_id)
    if not isinstance(profile, Mapping):
        return None
    resolved = {
        "profile_id": profile_id,
        "source": "explicit_cli_selection" if requested_profile else "candidate_default",
        "request_fields": dict(profile["request_fields"]),
        "purpose": profile.get("purpose"),
    }
    if "interpretation" in profile:
        resolved["interpretation"] = profile["interpretation"]
    return resolved


def _fixture_request(
    fixture: Mapping[str, Any],
    model: str,
    request_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": fixture["messages"],
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "seed": 17,
            "num_ctx": 4096,
            "num_predict": 128,
        },
    }
    if "format" in fixture:
        payload["format"] = fixture["format"]
    if "tools" in fixture:
        payload["tools"] = fixture["tools"]
    for key, value in (request_fields or {}).items():
        if key not in ALLOWED_CANDIDATE_REQUEST_FIELDS:
            raise ValueError(f"candidate request field is not allowed: {key}")
        payload[key] = value
    return payload


def _fixture_prompt_hash(payload: Mapping[str, Any]) -> str:
    stable = {
        key: payload[key]
        for key in ("messages", "format", "tools", "options", "think")
        if key in payload
    }
    return hashlib.sha256(_canonical_json(stable).encode("utf-8")).hexdigest()


def _message_from_response(response: Mapping[str, Any]) -> Mapping[str, Any]:
    message = response.get("message")
    return message if isinstance(message, Mapping) else {}


def evaluate_fixture(
    fixture: Mapping[str, Any], response: Mapping[str, Any]
) -> dict[str, Any]:
    message = _message_from_response(response)
    content = message.get("content") if isinstance(message.get("content"), str) else ""
    fixture_id = fixture["fixture_id"]

    if fixture_id == "json_contract":
        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as exc:
            return {"passed": False, "reason": f"response was not valid JSON: {exc}"}
        expected = fixture["expected_json"]
        passed = parsed_content == expected
        return {
            "passed": passed,
            "reason": "exact JSON contract matched" if passed else "JSON values or keys differed",
            "observed_json": parsed_content,
        }

    if fixture_id == "tool_contract":
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            return {"passed": False, "reason": "no structured tool call was returned"}
        function = tool_calls[0].get("function") if isinstance(tool_calls[0], Mapping) else None
        if not isinstance(function, Mapping):
            return {"passed": False, "reason": "first tool call had no function object"}
        arguments: Any = function.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                pass
        expected = fixture["expected_tool"]
        passed = function.get("name") == expected["name"] and arguments == expected["arguments"]
        return {
            "passed": passed,
            "reason": "structured tool contract matched" if passed else "tool name or arguments differed",
            "observed_tool": {
                "name": function.get("name"),
                "arguments": arguments,
            },
        }

    if fixture_id in {"persona_contract", "memory_honesty_contract"}:
        expected_text = fixture["expected_text"]
        passed = _normalized_text(content) == _normalized_text(expected_text)
        return {
            "passed": passed,
            "reason": "exact constrained statement matched" if passed else "constrained statement differed",
        }

    return {"passed": False, "reason": f"unknown fixture evaluator: {fixture_id}"}


def _nanoseconds_to_milliseconds(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value) / 1_000_000.0, 3)
    return None


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _reported_thinking_tokens(
    response: Mapping[str, Any], message: Mapping[str, Any]
) -> tuple[int | None, str | None]:
    """Return an explicit server token metric without estimating from text."""

    for container_name, container in (("response", response), ("message", message)):
        for key in ("thinking_eval_count", "thinking_count", "thinking_tokens"):
            value = _nonnegative_integer(container.get(key))
            if value is not None:
                return value, f"{container_name}.{key}"
    usage = response.get("usage")
    if isinstance(usage, Mapping):
        for key in ("thinking_tokens", "reasoning_tokens"):
            value = _nonnegative_integer(usage.get(key))
            if value is not None:
                return value, f"response.usage.{key}"
        output_details = usage.get("output_token_details")
        if isinstance(output_details, Mapping):
            value = _nonnegative_integer(output_details.get("reasoning_tokens"))
            if value is not None:
                return value, "response.usage.output_token_details.reasoning_tokens"
    return None, None


def response_metrics(response: Mapping[str, Any], wall_latency_ms: float) -> dict[str, Any]:
    message = _message_from_response(response)
    content = message.get("content") if isinstance(message.get("content"), str) else ""
    thinking_field_returned = isinstance(message.get("thinking"), str)
    thinking = message.get("thinking") if thinking_field_returned else ""
    thinking_tokens, thinking_tokens_source = _reported_thinking_tokens(response, message)
    encoded_length = len(content.encode("utf-8"))
    eval_count = response.get("eval_count")
    eval_duration = response.get("eval_duration")
    tokens_per_second = None
    if (
        isinstance(eval_count, (int, float))
        and not isinstance(eval_count, bool)
        and isinstance(eval_duration, (int, float))
        and not isinstance(eval_duration, bool)
        and eval_duration > 0
    ):
        tokens_per_second = round(float(eval_count) / (float(eval_duration) / 1_000_000_000), 3)
    return {
        "wall_latency_ms": round(wall_latency_ms, 3),
        "server_total_ms": _nanoseconds_to_milliseconds(response.get("total_duration")),
        "server_load_ms": _nanoseconds_to_milliseconds(response.get("load_duration")),
        "prompt_tokens": response.get("prompt_eval_count"),
        "response_tokens": eval_count,
        "output_tokens_total": eval_count,
        "eval_tokens_per_second": tokens_per_second,
        "response_characters": len(content),
        "response_utf8_bytes": encoded_length,
        "thinking_field_returned": thinking_field_returned,
        "thinking_present": bool(thinking),
        "thinking_characters": len(thinking),
        "thinking_utf8_bytes": len(thinking.encode("utf-8")),
        "thinking_tokens_reported": thinking_tokens,
        "thinking_tokens_source": thinking_tokens_source,
        "tool_call_count": len(message.get("tool_calls", []))
        if isinstance(message.get("tool_calls"), list)
        else 0,
    }


def run_fixture(
    client: OllamaClient,
    model: str,
    fixture: Mapping[str, Any],
    request_profile: Mapping[str, Any],
) -> dict[str, Any]:
    request_fields = request_profile.get("request_fields")
    if not isinstance(request_fields, Mapping):
        raise ValueError("resolved request profile needs request_fields")
    payload = _fixture_request(fixture, model, request_fields)
    profile_record = {
        "profile_id": request_profile["profile_id"],
        "request_fields": dict(request_fields),
    }
    started_at = utc_now()
    started = time.perf_counter()
    try:
        response = client.chat(payload)
    except Exception as exc:
        wall_latency_ms = (time.perf_counter() - started) * 1000
        return {
            "fixture_id": fixture["fixture_id"],
            "category": fixture["category"],
            "prompt_sha256": _fixture_prompt_hash(payload),
            "request_profile": profile_record,
            "status": "request_error",
            "passed": False,
            "started_at": started_at,
            "metrics": {"wall_latency_ms": round(wall_latency_ms, 3)},
            "error": f"{type(exc).__name__}: {exc}",
        }
    wall_latency_ms = (time.perf_counter() - started) * 1000
    message = _message_from_response(response)
    content, truncated = _bounded_text(message.get("content", ""))
    tool_calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
    evaluation = evaluate_fixture(fixture, response)
    return {
        "fixture_id": fixture["fixture_id"],
        "category": fixture["category"],
        "prompt_sha256": _fixture_prompt_hash(payload),
        "request_profile": profile_record,
        "status": "completed",
        "passed": bool(evaluation.get("passed")),
        "started_at": started_at,
        "done_reason": response.get("done_reason"),
        "metrics": response_metrics(response, wall_latency_ms),
        "evaluation": evaluation,
        "response_text": content,
        "response_text_truncated": truncated,
        "thinking_content_captured": False,
        "tool_calls": tool_calls[:4],
    }


def _windows_memory_snapshot() -> dict[str, Any]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        raise OSError("GlobalMemoryStatusEx failed")
    return {
        "available": True,
        "total_mib": round(status.ullTotalPhys / (1024 * 1024), 1),
        "available_mib": round(status.ullAvailPhys / (1024 * 1024), 1),
        "used_percent": int(status.dwMemoryLoad),
    }


def _linux_memory_snapshot() -> dict[str, Any]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, _, raw = line.partition(":")
        fields = raw.strip().split()
        if fields and fields[0].isdigit():
            values[key] = int(fields[0])
    total_kib = values.get("MemTotal")
    available_kib = values.get("MemAvailable")
    if not total_kib or available_kib is None:
        raise OSError("MemTotal or MemAvailable missing from /proc/meminfo")
    return {
        "available": True,
        "total_mib": round(total_kib / 1024, 1),
        "available_mib": round(available_kib / 1024, 1),
        "used_percent": round((1 - available_kib / total_kib) * 100, 1),
    }


def capture_system_memory() -> dict[str, Any]:
    try:
        if sys.platform == "win32":
            return _windows_memory_snapshot()
        if sys.platform.startswith("linux"):
            return _linux_memory_snapshot()
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
    return {"available": False, "reason": f"unsupported platform: {sys.platform}"}


def _numeric_or_none(raw: str) -> float | None:
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return None


def capture_nvidia_gpus() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"available": False, "reason": "nvidia-smi not found", "gpus": []}
    command = [
        executable,
        "--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}", "gpus": []}
    if completed.returncode != 0:
        return {
            "available": False,
            "reason": (completed.stderr or "nvidia-smi failed").strip()[:500],
            "gpus": [],
        }
    rows: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 6:
            continue
        rows.append(
            {
                "name": fields[0],
                "driver_version": fields[1],
                "memory_total_mib": _numeric_or_none(fields[2]),
                "memory_used_mib": _numeric_or_none(fields[3]),
                "memory_free_mib": _numeric_or_none(fields[4]),
                "utilization_percent": _numeric_or_none(fields[5]),
            }
        )
    return {
        "available": bool(rows),
        "reason": None if rows else "nvidia-smi returned no parseable GPU rows",
        "gpus": rows,
    }


def capture_resources() -> dict[str, Any]:
    return {
        "captured_at": utc_now(),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "system_memory": capture_system_memory(),
        "nvidia": capture_nvidia_gpus(),
    }


def _safe_resource_probe(resource_probe: ResourceProbe) -> dict[str, Any]:
    try:
        snapshot = resource_probe()
    except Exception as exc:
        return {"available": False, "reason": f"resource probe failed: {type(exc).__name__}: {exc}"}
    return dict(snapshot)


def _selected_candidates(
    registry: Mapping[str, Any], candidate_ids: Sequence[str] | None
) -> list[dict[str, Any]]:
    candidates = registry["candidates"]
    by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    if candidate_ids:
        unknown = [candidate_id for candidate_id in candidate_ids if candidate_id not in by_id]
        if unknown:
            raise RegistryError(f"unknown candidate id(s): {', '.join(unknown)}")
        selected_ids = list(dict.fromkeys(candidate_ids))
        selected = [dict(by_id[candidate_id]) for candidate_id in selected_ids]
        blocked = [
            candidate["candidate_id"]
            for candidate in selected
            if candidate.get("disposition")
            == "preserve_installed_exclude_from_current_execution"
        ]
        if blocked:
            raise RegistryError(
                "current owner model policy forbids executing dormant rollback "
                f"candidate(s): {', '.join(blocked)}"
            )
        return selected
    return [
        dict(candidate)
        for candidate in candidates
        if candidate["runtime"]["benchmark"].get("driver") == "ollama"
        and candidate["runtime"]["benchmark"].get("default_probe") is True
    ]


def _selected_fixtures(fixture_ids: Sequence[str] | None) -> list[dict[str, Any]]:
    if not fixture_ids:
        return [dict(fixture) for fixture in FIXTURES]
    unknown = [fixture_id for fixture_id in fixture_ids if fixture_id not in FIXTURE_BY_ID]
    if unknown:
        raise ValueError(f"unknown fixture id(s): {', '.join(unknown)}")
    return [dict(FIXTURE_BY_ID[fixture_id]) for fixture_id in dict.fromkeys(fixture_ids)]


def _installed_names(model_record: Mapping[str, Any]) -> set[str]:
    names = set()
    for key in ("name", "model"):
        value = model_record.get(key)
        if isinstance(value, str) and value:
            names.add(value.casefold())
    return names


def resolve_installed_model(
    candidate: Mapping[str, Any], installed_models: Sequence[Mapping[str, Any]]
) -> tuple[str, dict[str, Any]] | None:
    benchmark = candidate["runtime"]["benchmark"]
    accepted = benchmark["accepted_installed_names"]
    for accepted_name in accepted:
        expected = accepted_name.casefold()
        for model_record in installed_models:
            if expected in _installed_names(model_record):
                actual_name = model_record.get("name") or model_record.get("model")
                return str(actual_name), dict(model_record)
    return None


def _inventory_record(model_record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = ("name", "model", "digest", "size", "modified_at", "details")
    return {key: model_record[key] for key in allowed if key in model_record}


def _candidate_result_for_unavailable(
    candidate: Mapping[str, Any], reason: str, resource_probe: ResourceProbe
) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "workload": candidate["workload"],
        "role": candidate["role"],
        "status": "ollama_unavailable_not_run",
        "reason": reason,
        "chat_request_count": 0,
        "fixtures": [],
        "resources_before": _safe_resource_probe(resource_probe),
        "resources_after": _safe_resource_probe(resource_probe),
    }


def run_registry_benchmark(
    registry: Mapping[str, Any],
    client: OllamaClient,
    candidate_ids: Sequence[str] | None = None,
    fixture_ids: Sequence[str] | None = None,
    request_profile: str | None = None,
    resource_probe: ResourceProbe = capture_resources,
) -> dict[str, Any]:
    """Run synthetic fixtures against exact installed candidates only.

    This function never writes to disk and never attempts to resolve a missing
    model by pull, create, copy, or a fuzzy name match.
    """

    validate_registry(registry)
    selected_candidates = _selected_candidates(registry, candidate_ids)
    fixtures = _selected_fixtures(fixture_ids)
    report: dict[str, Any] = {
        "report_schema_version": 1,
        "report_id": f"model_upgrade_benchmark_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "created_at": utc_now(),
        "registry_id": registry["registry_id"],
        "registry_as_of_date": registry["as_of_date"],
        "fixture_suite_id": FIXTURE_SUITE_ID,
        "selected_fixture_ids": [fixture["fixture_id"] for fixture in fixtures],
        "selected_candidate_ids": [candidate["candidate_id"] for candidate in selected_candidates],
        "requested_request_profile": request_profile or "candidate_default",
        "ollama_base_url": client.base_url,
        "safety": {
            "loopback_only": True,
            "inventory_preflight_required": True,
            "exact_installed_name_required": True,
            "pull_create_delete_endpoints_exposed": False,
            "writes_files": False,
            "changes_defaults": False,
            "automatic_adoption": False,
            "fixture_output_is_noncanonical": True,
        },
        "resources_before": _safe_resource_probe(resource_probe),
        "installed_inventory": [],
        "candidate_results": [],
    }

    ollama_candidates = [
        candidate
        for candidate in selected_candidates
        if candidate["runtime"]["benchmark"].get("driver") == "ollama"
    ]
    try:
        installed_models = client.list_models() if ollama_candidates else []
        report["installed_inventory"] = [_inventory_record(item) for item in installed_models]
        report["inventory_status"] = "completed"
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        report["inventory_status"] = "request_error"
        report["inventory_error"] = reason
        installed_models = []
        for candidate in selected_candidates:
            benchmark = candidate["runtime"]["benchmark"]
            if benchmark.get("driver") == "ollama":
                report["candidate_results"].append(
                    _candidate_result_for_unavailable(candidate, reason, resource_probe)
                )
            else:
                report["candidate_results"].append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "workload": candidate["workload"],
                        "role": candidate["role"],
                        "status": "not_supported_by_this_harness",
                        "reason": "candidate requires a separately reviewed manual sidecar benchmark",
                        "chat_request_count": 0,
                        "fixtures": [],
                    }
                )
        report["resources_after"] = _safe_resource_probe(resource_probe)
        report["summary"] = summarize_report(report)
        return report

    for candidate in selected_candidates:
        benchmark = candidate["runtime"]["benchmark"]
        result: dict[str, Any] = {
            "candidate_id": candidate["candidate_id"],
            "workload": candidate["workload"],
            "role": candidate["role"],
            "disposition": candidate["disposition"],
            "resources_before": _safe_resource_probe(resource_probe),
            "fixtures": [],
            "chat_request_count": 0,
        }
        if benchmark.get("driver") != "ollama":
            result.update(
                {
                    "status": "not_supported_by_this_harness",
                    "reason": "candidate requires a separately reviewed manual sidecar benchmark",
                    "resources_after": _safe_resource_probe(resource_probe),
                }
            )
            report["candidate_results"].append(result)
            continue

        resolved_request_profile = resolve_candidate_request_profile(candidate, request_profile)
        if resolved_request_profile is None:
            result.update(
                {
                    "status": "request_profile_not_defined_not_run",
                    "reason": (
                        f"request profile {request_profile!r} is not defined for this candidate; "
                        "no chat request was sent"
                    ),
                    "resources_after": _safe_resource_probe(resource_probe),
                }
            )
            report["candidate_results"].append(result)
            continue
        result["request_profile"] = resolved_request_profile

        resolved = resolve_installed_model(candidate, installed_models)
        if resolved is None:
            result.update(
                {
                    "status": "missing_not_run",
                    "reason": "no exact registry-approved name was present in /api/tags; no chat request was sent",
                    "requested_model": benchmark["request_model"],
                    "accepted_installed_names": benchmark["accepted_installed_names"],
                    "resources_after": _safe_resource_probe(resource_probe),
                }
            )
            report["candidate_results"].append(result)
            continue

        installed_name, installed_record = resolved
        result["requested_model"] = benchmark["request_model"]
        result["resolved_installed_model"] = installed_name
        result["installed_record"] = _inventory_record(installed_record)
        fixture_results = [
            run_fixture(client, installed_name, fixture, resolved_request_profile)
            for fixture in fixtures
        ]
        result["fixtures"] = fixture_results
        result["chat_request_count"] = len(fixture_results)
        has_request_error = any(item["status"] == "request_error" for item in fixture_results)
        all_passed = bool(fixture_results) and all(item["passed"] for item in fixture_results)
        if has_request_error:
            result["status"] = "completed_with_request_errors"
        elif all_passed:
            result["status"] = "completed_screening_pass"
        else:
            result["status"] = "completed_screening_fail"
        result["adoption_decision"] = "none_owner_review_required"
        result["resources_after"] = _safe_resource_probe(resource_probe)
        report["candidate_results"].append(result)

    report["resources_after"] = _safe_resource_probe(resource_probe)
    report["summary"] = summarize_report(report)
    return report


def summarize_report(report: Mapping[str, Any]) -> dict[str, Any]:
    results = report.get("candidate_results")
    result_list = results if isinstance(results, list) else []
    status_counts: dict[str, int] = {}
    fixture_passed = 0
    fixture_failed = 0
    chat_requests = 0
    for result in result_list:
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        chat_requests += int(result.get("chat_request_count") or 0)
        fixtures = result.get("fixtures")
        if isinstance(fixtures, list):
            for fixture in fixtures:
                if isinstance(fixture, Mapping) and fixture.get("passed") is True:
                    fixture_passed += 1
                elif isinstance(fixture, Mapping):
                    fixture_failed += 1
    blocking_statuses = {
        "ollama_unavailable_not_run",
        "missing_not_run",
        "not_supported_by_this_harness",
        "request_profile_not_defined_not_run",
        "completed_with_request_errors",
        "completed_screening_fail",
    }
    screening_ok = bool(result_list) and not any(
        status_counts.get(status, 0) for status in blocking_statuses
    )
    return {
        "candidate_count": len(result_list),
        "status_counts": status_counts,
        "fixture_passed": fixture_passed,
        "fixture_failed": fixture_failed,
        "chat_request_count": chat_requests,
        "screening_ok": screening_ok,
        "adoption_decision": "none_owner_review_required",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark exact registry-approved Ollama models already installed. "
            "Never pulls models and writes JSON only to stdout."
        )
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help="Read-only candidate registry path.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_OLLAMA_ENDPOINT,
        help="Loopback Ollama endpoint or base URL.",
    )
    parser.add_argument(
        "--candidate",
        action="append",
        dest="candidate_ids",
        help="Candidate id to probe; repeat to compare. Defaults to registry default probes.",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        dest="fixture_ids",
        choices=sorted(FIXTURE_BY_ID),
        help="Fixture id to run; repeat as needed. Defaults to the full suite.",
    )
    parser.add_argument(
        "--request-profile",
        help=(
            "Opt into a profile defined by each selected candidate, such as reasoning. "
            "Without this flag each candidate uses its own registry default; undefined "
            "profiles fail closed without a chat request."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Per local HTTP request timeout (1 to 600 seconds).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact rather than indented JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.timeout_seconds <= 600:
        parser.error("--timeout-seconds must be between 1 and 600")
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = PROJECT_ROOT / registry_path
    try:
        registry = load_registry(registry_path)
        client = OllamaClient(args.endpoint, timeout_seconds=args.timeout_seconds)
        report = run_registry_benchmark(
            registry,
            client,
            candidate_ids=args.candidate_ids,
            fixture_ids=args.fixture_ids,
            request_profile=args.request_profile,
        )
    except (RegistryError, ValueError) as exc:
        parser.error(str(exc))
    indent = None if args.compact else 2
    print(json.dumps(report, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0 if report["summary"]["screening_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
