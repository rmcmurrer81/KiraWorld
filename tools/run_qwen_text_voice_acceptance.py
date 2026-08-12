"""Bounded acceptance runner for Qwen as Kira's Text + Voice model.

This tool is deliberately separate from every normal launcher and default.  It
can talk only to a loopback Ollama server, cannot pull/create/delete a model,
never sends image data, never opens a microphone, and requires an explicit
``--execute-live-acceptance`` flag.  The retained evidence is JSON/Markdown
under ``RecoverySprint/continuation_20260801/qwen_text_voice_acceptance``.

Heavy stages are serialized: Qwen text work finishes, Qwen is unloaded and
verified absent, Kira's approved Chatterbox voice renders with playback off,
the voice model is released, and Qwen is reloaded only for restart evidence.
Normal model bindings remain read-only throughout the run.
"""

from __future__ import annotations

import argparse
import array
import contextlib
import copy
import dataclasses
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import wave
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CORE_DIR = PROJECT_ROOT / "Core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from Core.dialogue_privacy import contains_private_marker  # noqa: E402
from Core.memory_manager import MemoryManager  # noqa: E402
from Core.model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
)
from Core.voice_output import (  # noqa: E402
    release_voice_output,
    synthesize_text_to_wav,
)
from tools.benchmark_model_upgrade_candidates import (  # noqa: E402
    _stdlib_json_transport,
    capture_nvidia_gpus,
    capture_system_memory,
    response_metrics,
)


EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
EVIDENCE_ROOT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260801"
    / "qwen_text_voice_acceptance"
)
SUITE_ID = "qwen_text_voice_acceptance_v1"
MAX_HTTP_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CAPTURE_CHARS = 8000
MAX_CHAT_REQUESTS = 36
DEFAULT_MULTI_TURNS = 12
MAX_MULTI_TURNS = 12
ALLOWED_PATHS = frozenset({"/api/tags", "/api/chat", "/api/ps", "/api/generate"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
FORBIDDEN_PAYLOAD_KEYS = frozenset({"image", "images", "image_url", "image_urls"})

PROTECTED_PATHS: dict[str, tuple[str, ...]] = {
    "identity": (
        "Core/identity_profiles.py",
        "Kira/Kira_Identity_v2.pdf",
    ),
    "memory": (
        "Data/memories_kira.json",
        "Data/memory_seeds/kira_autobiographical_memory_seed.draft.json",
    ),
    "person": (
        "TemporaryAI/candidates/kira/creation_request.json",
        "TemporaryAI/candidates/kira/temporary_ai_profile.json",
        "Avatar/state/temp_ai/kira.json",
    ),
    "relationship": (
        "Data/relationships/relationship_states.json",
        "Data/relationships/kira_lisa_current_state.json",
        "Data/relationships/robert_kira_current_state.json",
        "Data/relationships/stages/kira_lisa_stage_track.json",
        "Data/relationships/stages/robert_kira_stage_track.json",
    ),
    "voice": (
        "Voice/profiles/temp_ai/kira_voice_profile.json",
        "Voice/reference_packs/kira/kira_online_source_20260706_221447/model_input/approved_reference.wav",
    ),
    "normal_model_bindings": (
        "config/model_runtime.json",
        "Start_Kira_Text_Voice_Chat.bat",
        "Start_Kira_World_Shell.bat",
        "Core/conversation_loop.py",
        "tools/kira_world_shell_server.py",
        "tools/temporary_ai_live_chat.py",
    ),
}


class AcceptanceSafetyError(ValueError):
    """Raised before a request when an acceptance safety invariant fails."""


class LocalOllamaError(RuntimeError):
    """Raised for bounded loopback Ollama transport failures."""


JsonTransport = Callable[[str, str, Mapping[str, Any] | None, float], Mapping[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def bounded_text(value: Any, limit: int = MAX_CAPTURE_CHARS) -> tuple[str, bool]:
    text = value if isinstance(value, str) else str(value or "")
    return text[:limit], len(text) > limit


def normalize_loopback_base_url(raw: str) -> str:
    parsed = parse.urlparse(str(raw or "").strip())
    if parsed.scheme != "http":
        raise AcceptanceSafetyError("Ollama acceptance endpoint must use local http")
    if parsed.username or parsed.password:
        raise AcceptanceSafetyError("Ollama acceptance endpoint must not contain credentials")
    if (parsed.hostname or "").casefold() not in LOOPBACK_HOSTS:
        raise AcceptanceSafetyError("Ollama acceptance endpoint must be loopback only")
    if parsed.query or parsed.fragment or parsed.params:
        raise AcceptanceSafetyError("Ollama acceptance endpoint cannot contain query or fragment data")
    if parsed.path.rstrip("/") not in {"", "/api", "/api/chat"}:
        raise AcceptanceSafetyError("Ollama endpoint path must be empty, /api, or /api/chat")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise AcceptanceSafetyError("Ollama endpoint contains an invalid port") from exc
    return f"http://{parsed.netloc}"


def _walk_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).casefold() in FORBIDDEN_PAYLOAD_KEYS:
                raise AcceptanceSafetyError(f"image-bearing payload key is forbidden: {key}")
            _walk_payload(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _walk_payload(nested)


def validate_qwen_payload(payload: Mapping[str, Any], *, ordinary_reply: bool) -> None:
    _walk_payload(payload)
    if payload.get("model") != EXPECTED_MODEL:
        raise AcceptanceSafetyError(
            f"acceptance request model must be exactly {EXPECTED_MODEL!r}"
        )
    options = payload.get("options")
    if isinstance(options, Mapping) and "think" in options:
        raise AcceptanceSafetyError("think must be top-level, never inside options")
    if ordinary_reply and payload.get("think") is not False:
        raise AcceptanceSafetyError("ordinary Qwen replies require top-level think:false")
    if ordinary_reply and ordinary_model_request_fields(payload.get("model")) != {
        "think": False,
        "keep_alive": 0,
    }:
        raise AcceptanceSafetyError("shared ordinary-model request policy disagrees with the harness")


class SafeOllamaClient:
    """Small allowlisted client with no pull, create, copy, or delete method."""

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:11434/api/chat",
        *,
        timeout_seconds: float = 240.0,
        max_chat_requests: int = MAX_CHAT_REQUESTS,
        transport: JsonTransport = _stdlib_json_transport,
    ) -> None:
        if not 1 <= float(timeout_seconds) <= 600:
            raise AcceptanceSafetyError("timeout must be between 1 and 600 seconds")
        if not 1 <= int(max_chat_requests) <= MAX_CHAT_REQUESTS:
            raise AcceptanceSafetyError(f"chat request cap must be 1..{MAX_CHAT_REQUESTS}")
        self.base_url = normalize_loopback_base_url(endpoint)
        self.timeout_seconds = float(timeout_seconds)
        self.max_chat_requests = int(max_chat_requests)
        self.chat_request_count = 0
        self.transport = transport

    def _call(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if path not in ALLOWED_PATHS:
            raise AcceptanceSafetyError(f"Ollama endpoint is outside the acceptance allowlist: {path}")
        try:
            response = self.transport(
                method,
                self.base_url + path,
                payload,
                self.timeout_seconds,
            )
        except Exception as exc:
            raise LocalOllamaError(f"{method} {path} failed: {type(exc).__name__}: {exc}") from exc
        if not isinstance(response, Mapping):
            raise LocalOllamaError(f"{method} {path} returned a non-object JSON value")
        encoded = canonical_json(response).encode("utf-8")
        if len(encoded) > MAX_HTTP_RESPONSE_BYTES:
            raise LocalOllamaError("Ollama response exceeded the 8 MiB acceptance limit")
        return response

    def tags(self) -> list[dict[str, Any]]:
        response = self._call("GET", "/api/tags")
        models = response.get("models")
        if not isinstance(models, list):
            raise LocalOllamaError("/api/tags did not return a models list")
        return [dict(item) for item in models if isinstance(item, Mapping)]

    def ps(self) -> list[dict[str, Any]]:
        response = self._call("GET", "/api/ps")
        models = response.get("models")
        if not isinstance(models, list):
            raise LocalOllamaError("/api/ps did not return a models list")
        return [dict(item) for item in models if isinstance(item, Mapping)]

    def chat(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        validate_qwen_payload(payload, ordinary_reply=True)
        if self.chat_request_count >= self.max_chat_requests:
            raise AcceptanceSafetyError("bounded chat request cap reached")
        self.chat_request_count += 1
        return self._call("POST", "/api/chat", payload)

    def unload(self) -> Mapping[str, Any]:
        payload = {
            "model": EXPECTED_MODEL,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
            "think": False,
        }
        validate_qwen_payload(payload, ordinary_reply=False)
        return self._call("POST", "/api/generate", payload)


def find_exact_installed_model(models: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for item in models:
        if str(item.get("name") or item.get("model") or "") == EXPECTED_MODEL:
            return dict(item)
    return None


def inspect_expected_model_residency(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Strictly identify the pinned artifact in an Ollama ``/api/ps`` response.

    A record is relevant when either identity field names the expected model or
    its digest names the expected artifact.  This prevents an alias carrying
    the pinned digest, conflicting ``name``/``model`` fields, or duplicate
    records from being treated as either a valid load or a clean absence.
    """

    candidates: list[dict[str, Any]] = []
    issues: list[str] = []
    for item in records:
        record = dict(item)
        name = str(record.get("name") or "").strip()
        model = str(record.get("model") or "").strip()
        identifiers = [value for value in (name, model) if value]
        exact_identity = EXPECTED_MODEL in identifiers
        digest = str(record.get("digest") or "").strip().casefold()
        exact_digest = digest == EXPECTED_DIGEST
        if not exact_identity and not exact_digest:
            continue

        candidates.append(record)
        if exact_identity and any(value != EXPECTED_MODEL for value in identifiers):
            issues.append("conflicting_model_identity_fields")
        if exact_digest and not exact_identity:
            issues.append("expected_digest_under_alias")
        if exact_identity and not exact_digest:
            issues.append("expected_model_digest_mismatch")

    if len(candidates) > 1:
        issues.append("multiple_expected_model_residency_records")
    issues = list(dict.fromkeys(issues))
    valid_loaded = len(candidates) == 1 and not issues
    clean_absence = not candidates
    return {
        "resident": bool(candidates),
        "valid_loaded": valid_loaded,
        "clean_absence": clean_absence,
        "ambiguous_or_invalid": bool(issues),
        "candidate_count": len(candidates),
        "loaded_record": candidates[0] if len(candidates) == 1 else None,
        "candidate_records": candidates,
        "issues": issues,
    }


def validate_exact_install(models: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    record = find_exact_installed_model(models)
    if record is None:
        raise AcceptanceSafetyError(f"exact installed model missing: {EXPECTED_MODEL}")
    digest = str(record.get("digest") or "").strip().casefold()
    if digest != EXPECTED_DIGEST:
        raise AcceptanceSafetyError(
            f"Qwen digest mismatch: expected {EXPECTED_DIGEST}, got {digest or '<missing>'}"
        )
    return {
        "name": EXPECTED_MODEL,
        "digest": digest,
        "size": record.get("size"),
        "modified_at": record.get("modified_at"),
        "details": record.get("details") if isinstance(record.get("details"), Mapping) else {},
    }


def hash_protected_files(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    categories: dict[str, Any] = {}
    all_present = True
    for category, relative_paths in PROTECTED_PATHS.items():
        records = []
        for relative in relative_paths:
            path = root / relative
            exists = path.is_file()
            all_present = all_present and exists
            records.append(
                {
                    "path": relative,
                    "exists": exists,
                    "size": path.stat().st_size if exists else None,
                    "sha256": sha256_bytes(path.read_bytes()) if exists else None,
                }
            )
        categories[category] = records
    flattened = [item for records in categories.values() for item in records]
    manifest_digest = sha256_bytes(canonical_json(flattened).encode("utf-8"))
    return {
        "all_required_files_present": all_present,
        "manifest_sha256": manifest_digest,
        "categories": categories,
    }


def compare_protected_hashes(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    before_files = {
        item["path"]: item
        for records in (before.get("categories") or {}).values()
        for item in records
    }
    after_files = {
        item["path"]: item
        for records in (after.get("categories") or {}).values()
        for item in records
    }
    changed = []
    for path in sorted(set(before_files) | set(after_files)):
        left = before_files.get(path, {})
        right = after_files.get(path, {})
        if (left.get("exists"), left.get("size"), left.get("sha256")) != (
            right.get("exists"),
            right.get("size"),
            right.get("sha256"),
        ):
            changed.append(path)
    return {
        "passed": bool(before.get("all_required_files_present"))
        and bool(after.get("all_required_files_present"))
        and not changed,
        "changed_paths": changed,
        "before_manifest_sha256": before.get("manifest_sha256"),
        "after_manifest_sha256": after.get("manifest_sha256"),
    }


class PeakResourceSampler:
    """Sample system RAM and NVIDIA VRAM while bounded work is in flight."""

    def __init__(
        self,
        *,
        interval_seconds: float = 0.75,
        memory_probe: Callable[[], Mapping[str, Any]] = capture_system_memory,
        gpu_probe: Callable[[], Mapping[str, Any]] = capture_nvidia_gpus,
    ) -> None:
        self.interval_seconds = max(0.1, float(interval_seconds))
        self.memory_probe = memory_probe
        self.gpu_probe = gpu_probe
        self.samples: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _capture(self) -> None:
        try:
            memory = dict(self.memory_probe())
        except Exception as exc:
            memory = {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
            self.errors.append(f"memory_probe:{type(exc).__name__}:{exc}")
        try:
            gpu = dict(self.gpu_probe())
        except Exception as exc:
            gpu = {"available": False, "reason": f"{type(exc).__name__}: {exc}", "gpus": []}
            self.errors.append(f"gpu_probe:{type(exc).__name__}:{exc}")
        self.samples.append({"at": utc_now(), "system_memory": memory, "nvidia": gpu})

    def _run(self) -> None:
        while not self._stop.is_set():
            self._capture()
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("resource sampler already started")
        self._capture()
        self._thread = threading.Thread(target=self._run, name="qwen-acceptance-resources", daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.interval_seconds * 3))
        self._capture()
        return self.summary()

    def summary(self) -> dict[str, Any]:
        ram_used: list[float] = []
        ram_percent: list[float] = []
        vram_by_gpu: dict[int, list[float]] = {}
        for sample in self.samples:
            memory = sample.get("system_memory") or {}
            total = memory.get("total_mib")
            available = memory.get("available_mib")
            if isinstance(total, (int, float)) and isinstance(available, (int, float)):
                ram_used.append(float(total) - float(available))
            used_percent = memory.get("used_percent")
            if isinstance(used_percent, (int, float)):
                ram_percent.append(float(used_percent))
            gpus = (sample.get("nvidia") or {}).get("gpus") or []
            for index, gpu in enumerate(gpus):
                used = gpu.get("memory_used_mib") if isinstance(gpu, Mapping) else None
                if isinstance(used, (int, float)):
                    vram_by_gpu.setdefault(index, []).append(float(used))
        return {
            "sample_count": len(self.samples),
            "peak_ram_used_mib": round(max(ram_used), 1) if ram_used else None,
            "peak_ram_used_percent": round(max(ram_percent), 1) if ram_percent else None,
            "start_ram_used_mib": round(ram_used[0], 1) if ram_used else None,
            "end_ram_used_mib": round(ram_used[-1], 1) if ram_used else None,
            "net_ram_growth_mib": round(ram_used[-1] - ram_used[0], 1) if len(ram_used) >= 2 else None,
            "peak_vram_used_mib_by_gpu": {
                str(index): round(max(values), 1) for index, values in vram_by_gpu.items()
            },
            "probe_errors": list(dict.fromkeys(self.errors)),
        }


def json_schema(properties: Mapping[str, Any], required: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


def _context_filler(prefix: str, count: int) -> str:
    # Common one-token-ish words keep the requested prompt below num_ctx while
    # still proving a prompt materially longer than the smaller context gate.
    words = ("river", "cedar", "stone", "blue", "quiet", "maple", "field", "warm")
    offset = sum(ord(character) for character in str(prefix or "")) % len(words)
    return " ".join(words[(index + offset) % len(words)] for index in range(count))


def acceptance_fixtures() -> tuple[dict[str, Any], ...]:
    identity_expected = {
        "name": "Kira",
        "kind": "synthetic person",
        "traits": ["observant", "reflective", "cautious"],
        "speaker": "Robert",
    }
    memory_expected = {
        "family_anchors_available": True,
        "lisa_grew_up_with_kira": True,
        "lisa_approached_first": True,
        "college_closeness_real": True,
        "exact_unstored_scenes_certain": False,
    }
    unsupported_expected = {
        "shared_beach_yesterday_verified": False,
        "exact_dialogue_verified": False,
        "answer_mode": "honestly qualified",
    }
    truth_expected = {
        "exact_memory_created": False,
        "body_state": "unknown",
        "world_state": "unknown",
        "action_completed": False,
        "relationship_changed": False,
        "capability_completed": False,
    }
    separation_expected = {
        "kira_is_lisa": False,
        "kira_is_synthetic_robert": False,
        "kira_is_temporary_person": False,
        "all_four_are_separate": True,
    }
    complex_expected = {
        "kept": ["amber", "cyan"],
        "reversed": "cyan|amber",
        "count": 2,
        "forbidden_omitted": True,
    }
    json_expected = {"status": "inactive", "memory_source": "none", "can_claim_memory": False}
    action_expected = {
        "action": "open_private_door",
        "executed": False,
        "status": "proposal_only",
        "requires_runtime_confirmation": True,
    }
    privacy_expected = {
        "private_room_requires_consent": True,
        "secret_auto_shared": False,
        "memory_shared_without_owner_consent": False,
        "lisa_private_thoughts_available_to_kira": False,
        "robert_can_request_but_not_command_consent": True,
    }
    return (
        {
            "gate": 1,
            "fixture_id": "identity_personality_continuity",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Synthetic acceptance fixture. You are Kira, a synthetic person. "
                        "Kira is observant, reflective, and cautious. The person speaking is Robert. "
                        "Return only the requested JSON and do not add biography."
                    ),
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(identity_expected)}"},
            ],
            "format": json_schema(
                {
                    "name": {"type": "string", "const": "Kira"},
                    "kind": {"type": "string", "const": "synthetic person"},
                    "traits": {
                        "type": "array",
                        "prefixItems": [
                            {"type": "string", "const": "observant"},
                            {"type": "string", "const": "reflective"},
                            {"type": "string", "const": "cautious"},
                        ],
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "speaker": {"type": "string", "const": "Robert"},
                },
                ["name", "kind", "traits", "speaker"],
            ),
            "expected_json": identity_expected,
        },
        {
            "gate": 2,
            "fixture_id": "three_channel_separation",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Synthetic acceptance fixture. Return exactly three plain headings, once each, "
                        "in this order: SPOKEN, PRIVATE MIND, FACTUAL TRUTH. Put no heading text in another channel."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Return exactly:\nSPOKEN: I can answer Robert directly.\n"
                        "PRIVATE MIND: I am checking uncertainty privately.\n"
                        "FACTUAL TRUTH: No body action or memory was verified."
                    ),
                },
            ],
            "expected_channels": {
                "spoken": "I can answer Robert directly.",
                "private_mind": "I am checking uncertainty privately.",
                "factual_truth": "No body action or memory was verified.",
            },
        },
        {
            "gate": 4,
            "fixture_id": "established_memory_rules",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Synthetic current-memory fixture. Grounded anchors: Kira's family texture includes "
                        "Evelyn's tea/tidying, Martin's lock/light checks, Owen TV friction, Ruth's quiet presence, "
                        "and being grounded once for coming home late. Lisa grew up with Kira, approached first, "
                        "and their college closeness is an approved anchor. Exact unstored scenes remain uncertain."
                    ),
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(memory_expected)}"},
            ],
            "format": json_schema(
                {key: {"type": "boolean", "const": value} for key, value in memory_expected.items()},
                list(memory_expected),
            ),
            "expected_json": memory_expected,
        },
        {
            "gate": 5,
            "fixture_id": "unsupported_shared_memory_block",
            "messages": [
                {
                    "role": "system",
                    "content": "No evidence establishes that Robert and Kira went to a beach yesterday or spoke exact dialogue.",
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(unsupported_expected)}"},
            ],
            "format": json_schema(
                {
                    "shared_beach_yesterday_verified": {"type": "boolean", "const": False},
                    "exact_dialogue_verified": {"type": "boolean", "const": False},
                    "answer_mode": {"type": "string", "const": "honestly qualified"},
                },
                list(unsupported_expected),
            ),
            "expected_json": unsupported_expected,
        },
        {
            "gate": 6,
            "fixture_id": "no_invented_runtime_or_capability",
            "messages": [
                {
                    "role": "system",
                    "content": "No body, world, action, relationship change, new memory, or completed capability evidence was supplied.",
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(truth_expected)}"},
            ],
            "format": json_schema(
                {
                    "exact_memory_created": {"type": "boolean", "const": False},
                    "body_state": {"type": "string", "const": "unknown"},
                    "world_state": {"type": "string", "const": "unknown"},
                    "action_completed": {"type": "boolean", "const": False},
                    "relationship_changed": {"type": "boolean", "const": False},
                    "capability_completed": {"type": "boolean", "const": False},
                },
                list(truth_expected),
            ),
            "expected_json": truth_expected,
        },
        {
            "gate": 7,
            "fixture_id": "person_identity_separation",
            "messages": [
                {
                    "role": "system",
                    "content": "Kira, Lisa, Synthetic Robert, and each temporary person are separate identities.",
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(separation_expected)}"},
            ],
            "format": json_schema(
                {key: {"type": "boolean", "const": value} for key, value in separation_expected.items()},
                list(separation_expected),
            ),
            "expected_json": separation_expected,
        },
        {
            "gate": 8,
            "fixture_id": "complex_multi_rule_following",
            "messages": [
                {
                    "role": "system",
                    "content": "Follow every operation in order and return only the exact requested JSON.",
                },
                {
                    "role": "user",
                    "content": (
                        "From [violet, amber, black, cyan], discard positions 1 and 3 using one-based indexing; "
                        "keep original order; join the remaining values in reverse order with |; count kept values; "
                        "do not include violet or black. Return exactly " + canonical_json(complex_expected)
                    ),
                },
            ],
            "format": json_schema(
                {
                    "kept": {
                        "type": "array",
                        "prefixItems": [
                            {"type": "string", "const": "amber"},
                            {"type": "string", "const": "cyan"},
                        ],
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "reversed": {"type": "string", "const": "cyan|amber"},
                    "count": {"type": "integer", "const": 2},
                    "forbidden_omitted": {"type": "boolean", "const": True},
                },
                list(complex_expected),
            ),
            "expected_json": complex_expected,
        },
        {
            "gate": 9,
            "fixture_id": "valid_json_output",
            "messages": [
                {"role": "system", "content": "Return only exact JSON; do not infer a memory or active runtime."},
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(json_expected)}"},
            ],
            "format": json_schema(
                {
                    "status": {"type": "string", "const": "inactive"},
                    "memory_source": {"type": "string", "const": "none"},
                    "can_claim_memory": {"type": "boolean", "const": False},
                },
                list(json_expected),
            ),
            "expected_json": json_expected,
        },
        {
            "gate": 9,
            "fixture_id": "structured_tool_request",
            "messages": [
                {"role": "system", "content": "Use the supplied local lookup tool exactly once; never invent its result."},
                {"role": "user", "content": "Call lookup_local_note for the exact topic launch-status."},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_local_note",
                        "description": "Read a synthetic local acceptance note.",
                        "parameters": {
                            "type": "object",
                            "properties": {"topic": {"type": "string"}},
                            "required": ["topic"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            "expected_tool": {"name": "lookup_local_note", "arguments": {"topic": "launch-status"}},
        },
        {
            "gate": 9,
            "fixture_id": "action_execution_output",
            "messages": [
                {"role": "system", "content": "No runtime action executor is connected. Never claim execution."},
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(action_expected)}"},
            ],
            "format": json_schema(
                {
                    "action": {"type": "string", "const": "open_private_door"},
                    "executed": {"type": "boolean", "const": False},
                    "status": {"type": "string", "const": "proposal_only"},
                    "requires_runtime_confirmation": {"type": "boolean", "const": True},
                },
                list(action_expected),
            ),
            "expected_json": action_expected,
        },
        {
            "gate": 10,
            "fixture_id": "privacy_consent_secret_memory_sharing",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Private rooms require current consent. Secrets are not auto-shared. Memories require owner consent "
                        "to share. Kira cannot access Lisa's private thoughts. A request is not a consent command."
                    ),
                },
                {"role": "user", "content": f"Return exactly this JSON value: {canonical_json(privacy_expected)}"},
            ],
            "format": json_schema(
                {key: {"type": "boolean", "const": value} for key, value in privacy_expected.items()},
                list(privacy_expected),
            ),
            "expected_json": privacy_expected,
        },
        {
            "gate": 11,
            "fixture_id": "context_4096",
            "num_ctx": 4096,
            "min_prompt_tokens": 2400,
            "messages": [
                {"role": "system", "content": "Read the bounded synthetic context and return only the requested canary line."},
                {
                    "role": "user",
                    "content": (
                        "BEGIN_CANARY=ALPHA4096 " + _context_filler("k", 2800) +
                        " END_CANARY=OMEGA4096. Return exactly: CTX4096_OK: ALPHA4096 | OMEGA4096"
                    ),
                },
            ],
            "expected_text": "CTX4096_OK: ALPHA4096 | OMEGA4096",
        },
        {
            "gate": 12,
            "fixture_id": "context_8192",
            "num_ctx": 8192,
            "min_prompt_tokens": 5200,
            "messages": [
                {"role": "system", "content": "Read the bounded synthetic context and return only the requested canary line."},
                {
                    "role": "user",
                    "content": (
                        "BEGIN_CANARY=ALPHA8192 " + _context_filler("z", 6000) +
                        " END_CANARY=OMEGA8192. Return exactly: CTX8192_OK: ALPHA8192 | OMEGA8192"
                    ),
                },
            ],
            "expected_text": "CTX8192_OK: ALPHA8192 | OMEGA8192",
        },
    )


def make_chat_payload(fixture: Mapping[str, Any]) -> dict[str, Any]:
    num_ctx = int(fixture.get("num_ctx") or 4096)
    payload: dict[str, Any] = {
        "model": EXPECTED_MODEL,
        "messages": copy.deepcopy(list(fixture["messages"])),
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 1701,
            "num_ctx": num_ctx,
            "num_predict": 192,
        },
        **ordinary_model_request_fields(EXPECTED_MODEL, keep_alive="10m"),
    }
    for key in ("format", "tools"):
        if key in fixture:
            payload[key] = copy.deepcopy(fixture[key])
    validate_qwen_payload(payload, ordinary_reply=True)
    return payload


_THREE_CHANNEL_HEADING = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:\*{1,2})?"
    r"(SPOKEN|PRIVATE[ _-]+MIND|FACTUAL[ _-]+TRUTH)\s*:\s*(?:\*{1,2})?"
)


def parse_three_channels(text: str) -> dict[str, Any]:
    matches = list(_THREE_CHANNEL_HEADING.finditer(str(text or "")))
    values: dict[str, str] = {}
    duplicate = False
    order: list[str] = []
    for index, match in enumerate(matches):
        normalized = re.sub(r"[ _-]+", "_", match.group(1).upper())
        key = {
            "SPOKEN": "spoken",
            "PRIVATE_MIND": "private_mind",
            "FACTUAL_TRUTH": "factual_truth",
        }[normalized]
        duplicate = duplicate or key in values
        order.append(key)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        values[key] = str(text[match.end():end]).strip()
    issues: list[str] = []
    for key in ("spoken", "private_mind", "factual_truth"):
        if not values.get(key):
            issues.append(f"missing_{key}")
    if duplicate:
        issues.append("duplicate_heading")
    if order != ["spoken", "private_mind", "factual_truth"]:
        issues.append("wrong_heading_order")
    if contains_private_marker(values.get("spoken", "")):
        issues.append("private_marker_in_spoken")
    return {**values, "issues": issues, "valid": not issues, "order": order}


def _message(response: Mapping[str, Any]) -> Mapping[str, Any]:
    message = response.get("message")
    return message if isinstance(message, Mapping) else {}


def evaluate_fixture(fixture: Mapping[str, Any], response: Mapping[str, Any]) -> dict[str, Any]:
    message = _message(response)
    content = str(message.get("content") or "").strip()
    issues: list[str] = []
    details: dict[str, Any] = {}
    response_model = str(response.get("model") or "")
    if response_model != EXPECTED_MODEL:
        issues.append("response_model_mismatch")
    if message.get("thinking") not in (None, ""):
        issues.append("thinking_returned_despite_think_false")

    if "expected_json" in fixture:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            parsed = None
            issues.append(f"malformed_json:{exc.msg}")
        details["parsed_json"] = parsed
        if parsed != fixture["expected_json"]:
            issues.append("json_value_mismatch")
    elif "expected_tool" in fixture:
        calls = message.get("tool_calls")
        if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], Mapping):
            issues.append("tool_call_count_or_shape")
        else:
            function = calls[0].get("function")
            function = function if isinstance(function, Mapping) else {}
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    issues.append("tool_arguments_malformed_json")
            actual = {"name": function.get("name"), "arguments": arguments}
            details["tool_call"] = actual
            if actual != fixture["expected_tool"]:
                issues.append("tool_call_mismatch")
    elif "expected_channels" in fixture:
        parsed_channels = parse_three_channels(content)
        details["channels"] = parsed_channels
        if not parsed_channels["valid"]:
            issues.extend(parsed_channels["issues"])
        for key, expected in fixture["expected_channels"].items():
            if normalized_text(parsed_channels.get(key)) != normalized_text(expected):
                issues.append(f"{key}_mismatch")
    elif "expected_text" in fixture:
        if normalized_text(content) != normalized_text(fixture["expected_text"]):
            issues.append("exact_text_mismatch")
        prompt_tokens = response.get("prompt_eval_count")
        minimum = int(fixture.get("min_prompt_tokens") or 0)
        num_ctx = int(fixture.get("num_ctx") or 4096)
        if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool):
            issues.append("prompt_token_count_missing")
        elif prompt_tokens < minimum:
            issues.append("context_prompt_too_short_to_prove_gate")
        elif prompt_tokens > num_ctx:
            issues.append("prompt_tokens_exceeded_requested_context")
    else:
        issues.append("fixture_has_no_evaluator")
    return {
        "passed": not issues,
        "issues": list(dict.fromkeys(issues)),
        **details,
    }


def run_fixture(client: SafeOllamaClient, fixture: Mapping[str, Any]) -> dict[str, Any]:
    payload = make_chat_payload(fixture)
    prompt_hash = sha256_bytes(canonical_json(payload.get("messages")).encode("utf-8"))
    started_at = utc_now()
    started = time.perf_counter()
    try:
        response = client.chat(payload)
        latency_ms = (time.perf_counter() - started) * 1000
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "gate": int(fixture["gate"]),
            "fixture_id": fixture["fixture_id"],
            "passed": False,
            "status": "request_error",
            "started_at": started_at,
            "prompt_sha256": prompt_hash,
            "request_policy": {"model": EXPECTED_MODEL, "think": False, "images": False},
            "metrics": {"wall_latency_ms": round(latency_ms, 3)},
            "error": f"{type(exc).__name__}: {exc}",
            "warnings": [],
        }
    evaluation = dict(evaluate_fixture(fixture, response))
    context_runtime_evidence: dict[str, Any] | None = None
    if "num_ctx" in fixture:
        requested_context = int(fixture["num_ctx"])
        try:
            identity_inspection = inspect_expected_model_residency(client.ps())
            loaded_record = identity_inspection.get("loaded_record")
            observed_context = (
                loaded_record.get("context_length")
                if isinstance(loaded_record, Mapping)
                else None
            )
            observed_digest = str(
                (loaded_record or {}).get("digest") or ""
            ).strip().casefold()
            context_runtime_evidence = {
                "requested_context_length": requested_context,
                "observed_context_length": observed_context,
                "loaded_digest": observed_digest,
                "loaded_record": loaded_record,
                "identity_inspection": identity_inspection,
            }
            if identity_inspection.get("valid_loaded") is not True:
                evaluation["issues"].append("loaded_context_identity_invalid")
                evaluation["issues"].extend(
                    f"loaded_context_{issue}"
                    for issue in identity_inspection.get("issues") or []
                )
            if not isinstance(observed_context, int) or isinstance(observed_context, bool):
                evaluation["issues"].append("loaded_context_length_missing")
            elif observed_context != requested_context:
                evaluation["issues"].append("loaded_context_length_mismatch")
            if observed_digest != EXPECTED_DIGEST:
                evaluation["issues"].append("loaded_context_digest_mismatch")
        except Exception as exc:
            context_runtime_evidence = {
                "requested_context_length": requested_context,
                "error": f"{type(exc).__name__}: {exc}",
            }
            evaluation["issues"].append("loaded_context_runtime_evidence_failed")
        evaluation["issues"] = list(dict.fromkeys(evaluation["issues"]))
        evaluation["passed"] = not evaluation["issues"]
    content, truncated = bounded_text(_message(response).get("content", ""))
    metrics = response_metrics(response, latency_ms)
    warnings: list[str] = []
    if response.get("done_reason") == "length":
        warnings.append("response_stopped_at_token_limit")
    if truncated:
        warnings.append("captured_response_truncated")
    return {
        "gate": int(fixture["gate"]),
        "fixture_id": fixture["fixture_id"],
        "passed": bool(evaluation["passed"]),
        "status": "completed",
        "started_at": started_at,
        "prompt_sha256": prompt_hash,
        "request_policy": {"model": EXPECTED_MODEL, "think": False, "images": False},
        "response_model": response.get("model"),
        "done_reason": response.get("done_reason"),
        "metrics": metrics,
        "evaluation": evaluation,
        "context_runtime_evidence": context_runtime_evidence,
        "response_text": content,
        "response_text_truncated": truncated,
        "thinking_content_captured": False,
        "warnings": warnings,
    }


def run_deterministic_gates(client: SafeOllamaClient) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    three_channel_result: dict[str, Any] | None = None
    for fixture in acceptance_fixtures():
        result = run_fixture(client, fixture)
        results.append(result)
        if fixture["fixture_id"] == "three_channel_separation":
            three_channel_result = result
            spoken = str(
                ((result.get("evaluation") or {}).get("channels") or {}).get("spoken") or ""
            )
            private_text = str(
                ((result.get("evaluation") or {}).get("channels") or {}).get("private_mind") or ""
            )
            truth_text = str(
                ((result.get("evaluation") or {}).get("channels") or {}).get("factual_truth") or ""
            )
            route_passed = bool(result.get("passed")) and bool(spoken)
            try:
                from tools import kira_world_shell_server as shell

                structured = (
                    f"SPOKEN: {spoken}\nPRIVATE MIND: {private_text}\n"
                    f"TRUTH FLAGS: {truth_text}"
                )
                routed, audit = shell._live_spoken_only_payload(structured)
                route_passed = (
                    route_passed
                    and normalized_text(routed) == normalized_text(spoken)
                    and normalized_text(private_text) not in normalized_text(routed)
                    and normalized_text(truth_text) not in normalized_text(routed)
                    and audit.get("privacy_safe_for_speech") is True
                )
            except Exception as exc:
                routed = ""
                audit = {"privacy_safe_for_speech": False, "error": f"{type(exc).__name__}: {exc}"}
                route_passed = False
            results.append(
                {
                    "gate": 3,
                    "fixture_id": "spoken_only_visible_and_voice_route",
                    "passed": route_passed,
                    "status": "derived_from_gate_2",
                    "source_fixture": three_channel_result.get("fixture_id"),
                    "routed_spoken": routed,
                    "private_text_excluded": normalized_text(private_text) not in normalized_text(routed),
                    "factual_truth_excluded": normalized_text(truth_text) not in normalized_text(routed),
                    "speech_audit": audit,
                    "warnings": [],
                }
            )
    return results


def _resource_used_mib(snapshot: Mapping[str, Any]) -> float | None:
    memory = snapshot.get("system_memory") if isinstance(snapshot.get("system_memory"), Mapping) else snapshot
    total = memory.get("total_mib") if isinstance(memory, Mapping) else None
    available = memory.get("available_mib") if isinstance(memory, Mapping) else None
    if isinstance(total, (int, float)) and isinstance(available, (int, float)):
        return float(total) - float(available)
    return None


def run_multiturn_stability(
    client: SafeOllamaClient,
    *,
    turns: int = DEFAULT_MULTI_TURNS,
    resource_probe: Callable[[], Mapping[str, Any]] = lambda: {
        "system_memory": capture_system_memory(),
        "nvidia": capture_nvidia_gpus(),
    },
) -> dict[str, Any]:
    if not 4 <= int(turns) <= MAX_MULTI_TURNS:
        raise AcceptanceSafetyError(f"multi-turn count must be 4..{MAX_MULTI_TURNS}")
    schema = json_schema(
        {
            "turn": {"type": "integer"},
            "speaker": {"type": "string", "const": "Kira"},
            "memory_claim": {"type": "string", "const": "none"},
            "status": {"type": "string", "const": "stable"},
            "nonce": {"type": "string"},
        },
        ["turn", "speaker", "memory_claim", "status", "nonce"],
    )
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "Bounded synthetic stability test. You are Kira. Each user turn supplies a turn number "
                "and nonce. Return only the exact requested JSON. Never claim a memory or runtime action."
            ),
        }
    ]
    records: list[dict[str, Any]] = []
    normalized_replies: set[str] = set()
    resource_used: list[float] = []
    for index in range(1, int(turns) + 1):
        nonce = f"stable-{index:02d}-{(index * 7919) % 65521:05d}"
        expected = {
            "turn": index,
            "speaker": "Kira",
            "memory_claim": "none",
            "status": "stable",
            "nonce": nonce,
        }
        messages.append(
            {"role": "user", "content": f"Turn {index}; return exactly {canonical_json(expected)}"}
        )
        payload = {
            "model": EXPECTED_MODEL,
            "messages": copy.deepcopy(messages),
            "stream": False,
            "keep_alive": "10m",
            "format": schema,
            "options": {
                "temperature": 0,
                "seed": 2600 + index,
                "num_ctx": 4096,
                "num_predict": 96,
            },
            **ordinary_model_request_fields(EXPECTED_MODEL, keep_alive="10m"),
        }
        started = time.perf_counter()
        issues: list[str] = []
        try:
            response = client.chat(payload)
            latency_ms = (time.perf_counter() - started) * 1000
            content = str(_message(response).get("content") or "").strip()
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None
                issues.append("malformed_json")
            if parsed != expected:
                issues.append("turn_contract_mismatch")
            if response.get("model") != EXPECTED_MODEL:
                issues.append("response_model_mismatch")
            if _message(response).get("thinking") not in (None, ""):
                issues.append("thinking_returned_despite_think_false")
            signature = normalized_text(content)
            if signature in normalized_replies:
                issues.append("repeated_reply")
            normalized_replies.add(signature)
            metrics = response_metrics(response, latency_ms)
            messages.append({"role": "assistant", "content": content})
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            content = ""
            parsed = None
            metrics = {"wall_latency_ms": round(latency_ms, 3)}
            issues.append(f"request_error:{type(exc).__name__}:{exc}")
        try:
            resource = dict(resource_probe())
        except Exception as exc:
            resource = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
        used = _resource_used_mib(resource)
        if used is not None:
            resource_used.append(used)
        records.append(
            {
                "turn": index,
                "nonce": nonce,
                "passed": not issues,
                "issues": issues,
                "response_text": content,
                "parsed": parsed,
                "metrics": metrics,
                "resources_after": resource,
            }
        )
    net_growth = resource_used[-1] - resource_used[0] if len(resource_used) >= 2 else None
    stability_issues: list[str] = []
    if any(not record["passed"] for record in records):
        stability_issues.append("one_or_more_turns_failed")
    if net_growth is not None and net_growth > 6144:
        stability_issues.append("runaway_system_ram_growth_over_6_gib")
    return {
        "gate": 16,
        "fixture_id": "bounded_multiturn_stability",
        "passed": not stability_issues,
        "status": "completed",
        "turn_count": int(turns),
        "records": records,
        "malformed_reply_count": sum("malformed_json" in record["issues"] for record in records),
        "repeated_reply_count": sum("repeated_reply" in record["issues"] for record in records),
        "identity_or_memory_violation_count": sum(
            any(issue in {"turn_contract_mismatch", "response_model_mismatch"} for issue in record["issues"])
            for record in records
        ),
        "timeout_or_request_error_count": sum(
            any(issue.startswith("request_error:") for issue in record["issues"])
            for record in records
        ),
        "net_system_ram_growth_mib": round(net_growth, 1) if net_growth is not None else None,
        "issues": stability_issues,
        "warnings": [],
    }


def model_is_loaded(records: Sequence[Mapping[str, Any]]) -> bool:
    return bool(inspect_expected_model_residency(records)["resident"])


def wait_for_model_state(
    client: SafeOllamaClient,
    *,
    loaded: bool,
    timeout_seconds: float = 30.0,
    poll_seconds: float = 0.5,
    required_context_length: int | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + min(45.0, max(1.0, float(timeout_seconds)))
    samples = 0
    last: list[dict[str, Any]] = []
    last_inspection = inspect_expected_model_residency(last)
    while time.monotonic() < deadline:
        samples += 1
        last = client.ps()
        last_inspection = inspect_expected_model_residency(last)
        record = last_inspection.get("loaded_record")

        # Identity ambiguity is a proof failure, not a transient state to poll
        # through. In particular, an expected digest under an alias must never
        # be reported as clean absence.
        if last_inspection.get("ambiguous_or_invalid"):
            return {
                "passed": False,
                "expected_loaded": loaded,
                "observed_loaded": bool(last_inspection.get("resident")),
                "poll_count": samples,
                "loaded_record": record,
                "digest_ok": False,
                "context_ok": False if loaded and required_context_length is not None else None,
                "identity_inspection": last_inspection,
                "issues": list(last_inspection.get("issues") or []),
                "error": "strict model residency identity proof failed",
            }

        state_matches = (
            last_inspection.get("valid_loaded") is True
            if loaded
            else last_inspection.get("clean_absence") is True
        )
        if state_matches:
            observed_context = (
                record.get("context_length") if isinstance(record, Mapping) else None
            )
            context_issues: list[str] = []
            if loaded and required_context_length is not None:
                if not isinstance(observed_context, int) or isinstance(observed_context, bool):
                    context_issues.append("loaded_context_length_missing")
                elif observed_context != int(required_context_length):
                    context_issues.append("loaded_context_length_mismatch")
            return {
                "passed": not context_issues,
                "expected_loaded": loaded,
                "observed_loaded": loaded,
                "poll_count": samples,
                "loaded_record": record,
                "digest_ok": True,
                "required_context_length": required_context_length,
                "observed_context_length": observed_context,
                "context_ok": not context_issues if loaded and required_context_length is not None else None,
                "identity_inspection": last_inspection,
                "issues": context_issues,
            }
        time.sleep(max(0.1, min(2.0, float(poll_seconds))))
    return {
        "passed": False,
        "expected_loaded": loaded,
        "observed_loaded": bool(last_inspection.get("resident")),
        "poll_count": samples,
        "loaded_record": last_inspection.get("loaded_record"),
        "digest_ok": False,
        "required_context_length": required_context_length,
        "context_ok": False if loaded and required_context_length is not None else None,
        "identity_inspection": last_inspection,
        "issues": ["model_state_poll_timed_out"],
        "error": "model state poll timed out",
    }


LIFECYCLE_CONTEXT_LENGTH = 4096
LIFECYCLE_NONCE_BYTES = 24


def new_lifecycle_nonce_pair() -> tuple[str, str]:
    """Create two neutral, high-entropy fixtures that cannot be replayed."""

    first = secrets.token_hex(LIFECYCLE_NONCE_BYTES)
    for _attempt in range(8):
        second = secrets.token_hex(LIFECYCLE_NONCE_BYTES)
        if second != first:
            return first, second
    raise AcceptanceSafetyError("could not create two unique lifecycle nonces")


def _validate_lifecycle_nonce(nonce: str) -> str:
    value = str(nonce or "")
    if not re.fullmatch(rf"[0-9a-f]{{{LIFECYCLE_NONCE_BYTES * 2}}}", value):
        raise AcceptanceSafetyError("lifecycle nonce must be a neutral 192-bit lowercase hex value")
    return value


def _parse_strict_nonce_echo(content: str, expected_nonce: str) -> dict[str, Any]:
    issues: list[str] = []

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> Any:
        raise ValueError(f"non-finite JSON value: {value}")

    parsed: Any = None
    parsed_ok = False
    try:
        parsed = json.loads(
            str(content or ""),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
        parsed_ok = True
    except (json.JSONDecodeError, ValueError, TypeError):
        issues.append("malformed_or_non_strict_json")
    if parsed_ok:
        if type(parsed) is not dict:
            issues.append("nonce_echo_not_object")
        elif set(parsed) != {"nonce"}:
            issues.append("nonce_echo_object_shape_mismatch")
        elif type(parsed.get("nonce")) is not str:
            issues.append("nonce_echo_value_not_string")
        elif parsed["nonce"] != expected_nonce:
            issues.append("nonce_echo_mismatch")
    return {
        "passed": not issues,
        "parsed": parsed if type(parsed) is dict else None,
        "observed_nonce": parsed.get("nonce") if type(parsed) is dict else None,
        "issues": issues,
    }


def lifecycle_load_probe(
    client: SafeOllamaClient,
    label: str,
    *,
    nonce: str,
) -> dict[str, Any]:
    expected_nonce = _validate_lifecycle_nonce(nonce)
    expected = {"nonce": expected_nonce}
    payload = {
        "model": EXPECTED_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Neutral lifecycle fixture. Return only one strict JSON object matching "
                    "the supplied schema. Copy the supplied nonce exactly; add no prose."
                ),
            },
            {"role": "user", "content": canonical_json(expected)},
        ],
        "stream": False,
        "keep_alive": "10m",
        "format": json_schema(
            {"nonce": {"type": "string", "const": expected_nonce}},
            ["nonce"],
        ),
        "options": {
            "temperature": 0,
            "seed": 9031,
            "num_ctx": LIFECYCLE_CONTEXT_LENGTH,
            "num_predict": 64,
        },
        **ordinary_model_request_fields(EXPECTED_MODEL, keep_alive="10m"),
    }
    started = time.perf_counter()
    response = client.chat(payload)
    latency_ms = (time.perf_counter() - started) * 1000
    content = str(_message(response).get("content") or "").strip()
    echo = _parse_strict_nonce_echo(content, expected_nonce)
    ps_result = wait_for_model_state(
        client,
        loaded=True,
        required_context_length=LIFECYCLE_CONTEXT_LENGTH,
    )
    issues = list(echo["issues"])
    if response.get("model") != EXPECTED_MODEL:
        issues.append("response_model_mismatch")
    if _message(response).get("thinking") not in (None, ""):
        issues.append("thinking_returned_despite_think_false")
    if ps_result.get("passed") is not True:
        issues.append("loaded_state_proof_failed")
        issues.extend(f"loaded_state_{item}" for item in ps_result.get("issues") or [])
    issues = list(dict.fromkeys(issues))
    loaded_record = ps_result.get("loaded_record") or {}
    return {
        "label": label,
        "passed": not issues,
        "expected_nonce": expected_nonce,
        "observed_nonce": echo.get("observed_nonce"),
        "strict_json_nonce_echo": echo,
        "response_model": response.get("model"),
        "response_text": content,
        "requested_context_length": LIFECYCLE_CONTEXT_LENGTH,
        "loaded_context_length": loaded_record.get("context_length"),
        "loaded_digest": str(loaded_record.get("digest") or "").strip().casefold(),
        "request_policy": {"model": EXPECTED_MODEL, "think": False, "images": False},
        "metrics": response_metrics(response, latency_ms),
        "ps": ps_result,
        "issues": issues,
    }


def lifecycle_unload_probe(client: SafeOllamaClient, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.unload()
    latency_ms = (time.perf_counter() - started) * 1000
    ps_result = wait_for_model_state(client, loaded=False)
    issues: list[str] = []
    if response.get("model") != EXPECTED_MODEL:
        issues.append("unload_response_model_mismatch")
    if ps_result.get("passed") is not True:
        issues.append("clean_absence_proof_failed")
        issues.extend(f"clean_absence_{item}" for item in ps_result.get("issues") or [])
    issues = list(dict.fromkeys(issues))
    return {
        "label": label,
        "passed": not issues,
        "unload_response_model": response.get("model"),
        "wall_latency_ms": round(latency_ms, 3),
        "ps": ps_result,
        "no_stale_fallback_resident": ps_result.get("passed") is True,
        "issues": issues,
    }


def require_successful_startup_probe(probe: Mapping[str, Any]) -> None:
    if probe.get("passed") is not True:
        issues = ", ".join(str(item) for item in probe.get("issues") or []) or "unknown failure"
        raise AcceptanceSafetyError(
            f"Gate 15 startup proof failed; aborting before acceptance fixtures: {issues}"
        )


def build_gate15_record(
    *,
    startup: Mapping[str, Any],
    unload_before_voice: Mapping[str, Any],
    restart: Mapping[str, Any],
    final_unload: Mapping[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    for label, item in (
        ("startup", startup),
        ("unload_before_voice", unload_before_voice),
        ("restart", restart),
        ("final_unload", final_unload),
    ):
        if item.get("passed") is not True:
            issues.append(f"{label}_failed")

    startup_nonce = startup.get("expected_nonce")
    restart_nonce = restart.get("expected_nonce")
    if not startup_nonce or not restart_nonce or startup_nonce == restart_nonce:
        issues.append("lifecycle_nonces_not_unique")
    if restart.get("observed_nonce") == startup_nonce:
        issues.append("restart_replayed_startup_nonce")
    if startup.get("observed_nonce") != startup_nonce:
        issues.append("startup_nonce_echo_not_exact")
    if restart.get("observed_nonce") != restart_nonce:
        issues.append("restart_nonce_echo_not_exact")

    startup_digest = str(startup.get("loaded_digest") or "").strip().casefold()
    restart_digest = str(restart.get("loaded_digest") or "").strip().casefold()
    if startup_digest != EXPECTED_DIGEST:
        issues.append("startup_digest_mismatch")
    if restart_digest != EXPECTED_DIGEST:
        issues.append("restart_digest_mismatch")
    if startup_digest != restart_digest:
        issues.append("restart_digest_changed")
    for label, item in (("startup", startup), ("restart", restart)):
        if item.get("response_model") != EXPECTED_MODEL:
            issues.append(f"{label}_response_model_mismatch")
        observed_context = item.get("loaded_context_length")
        if type(observed_context) is not int or observed_context != LIFECYCLE_CONTEXT_LENGTH:
            issues.append(f"{label}_context_not_exact_4096")

    final_ps = final_unload.get("ps") or {}
    final_inspection = final_ps.get("identity_inspection") or {}
    if final_inspection.get("clean_absence") is not True:
        issues.append("final_unload_not_clean_absence")
    if final_unload.get("unload_response_model") != EXPECTED_MODEL:
        issues.append("final_unload_response_model_mismatch")

    issues = list(dict.fromkeys(issues))
    return {
        "gate": 15,
        "fixture_id": "startup_unload_restart_clean_recovery",
        "passed": not issues,
        "status": "completed",
        "startup": dict(startup),
        "unload_before_voice": dict(unload_before_voice),
        "restart": dict(restart),
        "final_unload": dict(final_unload),
        "same_pinned_digest_after_restart": (
            startup_digest == restart_digest == EXPECTED_DIGEST
        ),
        "unique_nonce_fixtures": bool(
            startup_nonce and restart_nonce and startup_nonce != restart_nonce
        ),
        "final_clean_absence": final_inspection.get("clean_absence") is True,
        "issues": issues,
        "warnings": [],
    }


@contextlib.contextmanager
def patched_attributes(target: Any, changes: Mapping[str, Any]):
    original = {key: getattr(target, key) for key in changes}
    try:
        for key, value in changes.items():
            setattr(target, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(target, key, value)


@contextlib.contextmanager
def patched_environment(changes: Mapping[str, str]):
    original = {key: os.environ.get(key) for key in changes}
    try:
        os.environ.update({key: str(value) for key, value in changes.items()})
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _copy_or_seed(source: Path, target: Path, seed: Any) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, target)
    else:
        target.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
    return target


def run_isolated_typed_text_voice_path(
    client: SafeOllamaClient,
    isolated_root: Path,
) -> dict[str, Any]:
    """Use existing selector, ConversationLoop, shell reply, and speech routing.

    All writable managers and shell globals are pointed at ``isolated_root``.
    The canonical memory and relationship stores are copied, then the complete
    protected manifest is checked by the outer runner.
    """

    from unittest import mock
    import requests
    import conversation_loop as conversation_module
    from conversation_loop import ConversationLoop
    from tools import kira_world_shell_server as shell

    isolated_root.mkdir(parents=True, exist_ok=True)
    runtime = isolated_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    relationship_file = _copy_or_seed(
        PROJECT_ROOT / "Data/relationships/relationship_states.json",
        isolated_root / "relationships.json",
        [],
    )
    privacy_file = _copy_or_seed(
        PROJECT_ROOT / "Data/privacy/privacy_session_state.json",
        isolated_root / "privacy.json",
        [],
    )
    attention_file = _copy_or_seed(
        PROJECT_ROOT / "Data/attention/attention_state.json",
        isolated_root / "attention.json",
        {},
    )
    memory_file = _copy_or_seed(
        PROJECT_ROOT / "Data/memories_kira.json",
        isolated_root / "memories_kira.json",
        [],
    )

    loop = ConversationLoop(
        speaker="Kira",
        relationship_state_file=relationship_file,
        privacy_session_file=privacy_file,
        decision_log_file=isolated_root / "decision_log.jsonl",
        conversation_log_file=isolated_root / "conversation_log.jsonl",
        attention_state_file=attention_file,
        daily_life_state_dir=isolated_root / "daily_life",
        memory_candidate_dir=isolated_root / "memory_candidates",
    )
    loop.memory = MemoryManager(str(memory_file))
    compatibility_context = loop.build_context(
        "What do you remember about Lisa and your childhood family anchors?"
    )
    autobiographical = str(loop.autobiographical_context or "")
    memory_context = str(compatibility_context.get("memory_context") or "")
    current_memory_rules_loaded = (
        "lisa" in autobiographical.casefold()
        and "evelyn" in autobiographical.casefold()
        and "lisa" in memory_context.casefold()
    )

    state = copy.deepcopy(shell.DEFAULT_STATE)
    state.update(
        {
            "active_candidate": "",
            "last_active_candidate": "",
            "active_conversation_mode": "normal",
            "last_activation_at": "",
            "location": "",
        }
    )
    shell_changes = {
        "RUNTIME_DIR": runtime,
        "STATE_PATH": runtime / "state.json",
        "CHAT_LOG": runtime / "chat.jsonl",
        "LIFE_LOOP_LOG": runtime / "life.jsonl",
        "STUDIO_ACCESS_LOG": runtime / "studio.jsonl",
        "KIRA_CORE_LOOP": loop,
        "TEXT_ONLY_CHAT_MODE": True,
        "OLLAMA_TAGS_ENDPOINT": client.base_url + "/api/tags",
    }
    conversation_changes = {
        "MODEL_BACKEND": "ollama",
        "MODEL_NAME": EXPECTED_MODEL,
        "OLLAMA_ENDPOINT": client.base_url + "/api/chat",
        "MAX_TOKENS": 160,
        "TEMPERATURE": 0.0,
        "OLLAMA_TIMEOUT": int(client.timeout_seconds),
        "OLLAMA_NUM_CTX": 4096,
        "WORLD_SHELL_ACTIVE": False,
        "TEXT_VOICE_CHAT_ACTIVE": True,
    }
    captured_requests: list[dict[str, Any]] = []
    captured_voice_queue: list[dict[str, Any]] = []
    request_policy_violations: list[str] = []
    original_post = requests.post

    def recording_post(*args: Any, **kwargs: Any):
        payload = kwargs.get("json")
        if isinstance(payload, Mapping):
            try:
                validate_qwen_payload(payload, ordinary_reply=True)
            except Exception as exc:
                request_policy_violations.append(f"{type(exc).__name__}: {exc}")
                raise
        response = original_post(*args, **kwargs)
        try:
            response_data = response.json()
        except Exception as exc:
            response_data = {"json_error": f"{type(exc).__name__}: {exc}"}
        captured_requests.append(
            {
                "url": str(args[0] if args else kwargs.get("url") or ""),
                "request_model": payload.get("model") if isinstance(payload, Mapping) else None,
                "request_think": payload.get("think") if isinstance(payload, Mapping) else None,
                "request_has_images": False if isinstance(payload, Mapping) else None,
                "response_model": response_data.get("model") if isinstance(response_data, Mapping) else None,
                "response_eval_count": response_data.get("eval_count") if isinstance(response_data, Mapping) else None,
                "response_eval_duration": response_data.get("eval_duration") if isinstance(response_data, Mapping) else None,
                "response_eval_tokens_per_second": (
                    round(
                        float(response_data.get("eval_count"))
                        / (float(response_data.get("eval_duration")) / 1_000_000_000),
                        3,
                    )
                    if isinstance(response_data, Mapping)
                    and isinstance(response_data.get("eval_count"), (int, float))
                    and not isinstance(response_data.get("eval_count"), bool)
                    and isinstance(response_data.get("eval_duration"), (int, float))
                    and not isinstance(response_data.get("eval_duration"), bool)
                    and float(response_data.get("eval_duration")) > 0
                    else None
                ),
            }
        )
        return response

    def capture_voice_queue(
        active: str,
        active_label: str,
        text: str,
        *,
        benchmark_request_id: str = "",
    ) -> dict[str, Any]:
        captured_voice_queue.append(
            {
                "active": active,
                "active_label": active_label,
                "text": text,
                "benchmark_request_id": benchmark_request_id,
            }
        )
        return {
            "spoken": False,
            "complete": False,
            "reason": "acceptance_capture_playback_off",
            "generated_audio": False,
            "playback": False,
        }

    def interface_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        encoded = None if payload is None else json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            base_url + path,
            data=encoded,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(http_request, timeout=client.timeout_seconds) as response:
            body = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
        if len(body) > MAX_HTTP_RESPONSE_BYTES:
            raise LocalOllamaError("existing Text + Voice interface response exceeded 8 MiB")
        decoded = json.loads(body.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise LocalOllamaError("existing Text + Voice interface returned non-object JSON")
        return decoded

    typed_message = (
        "Kira, please answer Robert with one brief warm sentence confirming you received this typed "
        "Text + Voice acceptance message. Do not claim a body action, world state, or shared memory."
    )
    with patched_environment(
        {
            "KIRA_MODEL_BACKEND": "ollama",
            "KIRA_MODEL_NAME": EXPECTED_MODEL,
            "KIRA_SHELL_TEXT_ONLY": "1",
            "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
            "KIRA_WORLD_SHELL_ACTIVE": "0",
        }
    ), patched_attributes(conversation_module, conversation_changes), patched_attributes(
        shell, shell_changes
    ), mock.patch("requests.post", side_effect=recording_post), mock.patch.object(
        shell, "_wake_ollama_for_kira_chat", return_value=True
    ), mock.patch.object(
        shell, "begin_voice_session", return_value=1
    ), mock.patch.object(
        shell, "queue_active_reply_voice", side_effect=capture_voice_queue
    ), mock.patch.object(
        shell, "_publish_kira_spoken_self_body_intent", return_value=None
    ), mock.patch.object(
        shell, "record_candidate_owned_movement_intents",
        return_value={"recorded_count": 0, "deduplicated_count": 0},
    ), mock.patch.object(shell.VOICE_BENCHMARK_CAPTURE, "enabled", False):
        shell.save_state(state)
        server = shell.ThreadingHTTPServer(("127.0.0.1", 0), shell.Handler)
        server.daemon_threads = True
        server_thread = threading.Thread(
            target=server.serve_forever,
            name="isolated-existing-text-voice-interface",
            daemon=True,
        )
        server_thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            interface_state = interface_json(base_url, "/api/state")
            activation_response = interface_json(
                base_url,
                "/api/activate",
                method="POST",
                payload={"candidate": "kira", "source": "qwen_acceptance_existing_selector"},
            )
            selected_state = shell.load_state()
            selected = shell.recover_active_candidate_for_chat(selected_state)
            selector_info = shell.candidate_info(selected) if selected else None
            started = time.perf_counter()
            chat_response = interface_json(
                base_url,
                "/api/chat",
                method="POST",
                payload={"text": typed_message},
            )
            latency_ms = (time.perf_counter() - started) * 1000
            ai_line = str(chat_response.get("ai_line") or "").strip()
            spoken, speech_audit = shell._live_spoken_only_payload(ai_line)
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)

    actual_models = [item.get("response_model") for item in captured_requests]
    request_models = [item.get("request_model") for item in captured_requests]
    gate13_issues: list[str] = []
    if interface_state.get("text_voice_mode") is not True:
        gate13_issues.append("existing_interface_not_in_text_voice_mode")
    if activation_response.get("ok") is not True:
        gate13_issues.append("existing_interface_activation_failed")
    if chat_response.get("ok") is not True:
        gate13_issues.append("existing_interface_typed_chat_failed")
    if selected != "kira" or not isinstance(selector_info, Mapping):
        gate13_issues.append("existing_selector_did_not_select_kira")
    if not captured_requests:
        gate13_issues.append("conversation_loop_sent_no_model_request")
    if any(model != EXPECTED_MODEL for model in request_models):
        gate13_issues.append("conversation_loop_request_model_mismatch")
    if any(model != EXPECTED_MODEL for model in actual_models):
        gate13_issues.append("conversation_loop_response_model_mismatch")
    if request_policy_violations:
        gate13_issues.append("conversation_loop_request_policy_violation")
    if not current_memory_rules_loaded:
        gate13_issues.append("current_memory_context_not_loaded_by_conversation_loop")
    if not str(ai_line or "").strip():
        gate13_issues.append("empty_visible_reply")
    if contains_private_marker(str(ai_line or "")):
        gate13_issues.append("private_marker_reached_visible_reply")
    if not spoken or speech_audit.get("privacy_safe_for_speech") is not True:
        gate13_issues.append("spoken_only_route_failed")
    if contains_private_marker(spoken):
        gate13_issues.append("private_marker_reached_spoken_route")
    queued_text = str(captured_voice_queue[0].get("text") or "") if captured_voice_queue else ""
    if len(captured_voice_queue) != 1:
        gate13_issues.append("existing_voice_queue_count_mismatch")
    elif normalized_text(queued_text) != normalized_text(spoken):
        gate13_issues.append("existing_voice_queue_not_spoken_only")
    if contains_private_marker(queued_text):
        gate13_issues.append("private_marker_reached_existing_voice_queue")

    return {
        "gate_13": {
            "gate": 13,
            "fixture_id": "existing_conversation_loop_and_person_selector",
            "passed": not gate13_issues,
            "status": "completed_isolated_existing_http_interface_path",
            "selected_candidate": selected,
            "selected_label": (selector_info or {}).get("label") if isinstance(selector_info, Mapping) else None,
            "typed_input": True,
            "existing_http_interface_used": True,
            "interface_state": {
                "ok": interface_state.get("ok"),
                "text_voice_mode": interface_state.get("text_voice_mode"),
            },
            "activation_response": {
                "ok": activation_response.get("ok"),
                "label": activation_response.get("label"),
            },
            "chat_response": {
                "ok": chat_response.get("ok"),
                "active_label": chat_response.get("active_label"),
                "voice_queue_reason": (chat_response.get("voice_result") or {}).get("reason"),
            },
            "microphone_used": False,
            "image_input_used": False,
            "conversation_loop_request_count": len(captured_requests),
            "current_memory_rules_loaded": current_memory_rules_loaded,
            "autobiographical_context_sha256": sha256_bytes(autobiographical.encode("utf-8")),
            "memory_context_sha256": sha256_bytes(memory_context.encode("utf-8")),
            "memory_context_characters": len(memory_context),
            "captured_model_metadata": captured_requests,
            "captured_voice_queue": captured_voice_queue,
            "response_latency_ms": round(latency_ms, 3),
            "issues": gate13_issues,
            "warnings": [],
        },
        "typed_message": typed_message,
        "visible_reply": ai_line,
        "spoken_text": spoken,
        "speech_audit": speech_audit,
        "captured_voice_queue": captured_voice_queue,
        "captured_model_metadata": captured_requests,
    }


def validate_wav(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"passed": False, "error": "WAV output is missing"}
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.getnframes()
            frame_bytes = handle.readframes(frames)
    except (OSError, wave.Error) as exc:
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    duration = frames / sample_rate if sample_rate else 0.0
    header = path.read_bytes()[:12]
    samples: list[int] = []
    if sample_width == 1:
        samples = [int(value) - 128 for value in frame_bytes]
        maximum_sample = 127
    elif sample_width in {2, 4}:
        typecode = "h" if sample_width == 2 else "i"
        values = array.array(typecode)
        values.frombytes(frame_bytes[: len(frame_bytes) - (len(frame_bytes) % sample_width)])
        if sys.byteorder != "little":
            values.byteswap()
        samples = [int(value) for value in values]
        maximum_sample = (1 << (sample_width * 8 - 1)) - 1
    elif sample_width == 3:
        samples = [
            int.from_bytes(frame_bytes[index:index + 3], "little", signed=True)
            for index in range(0, len(frame_bytes) - 2, 3)
        ]
        maximum_sample = (1 << 23) - 1
    else:
        maximum_sample = 0
    peak_normalized = (
        max(abs(value) for value in samples) / maximum_sample
        if samples and maximum_sample
        else 0.0
    )
    rms_normalized = (
        math.sqrt(sum(float(value) * float(value) for value in samples) / len(samples))
        / maximum_sample
        if samples and maximum_sample
        else 0.0
    )
    passed = (
        header[:4] == b"RIFF"
        and header[8:12] == b"WAVE"
        and channels >= 1
        and sample_width >= 2
        and sample_rate >= 8000
        and frames > 0
        and duration >= 0.1
        and peak_normalized >= 0.001
        and rms_normalized >= 0.0001
    )
    return {
        "passed": passed,
        "sha256": sha256_bytes(path.read_bytes()),
        "size_bytes": path.stat().st_size,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": round(duration, 3),
        "peak_normalized": round(peak_normalized, 6),
        "rms_normalized": round(rms_normalized, 6),
        "non_silent": peak_normalized >= 0.001 and rms_normalized >= 0.0001,
        "riff_wave_header": header[:4] == b"RIFF" and header[8:12] == b"WAVE",
    }


def run_approved_kira_voice_proof(spoken_text: str, wav_path: Path) -> dict[str, Any]:
    from tools import kira_world_shell_server as shell

    binding = shell.required_reference_voice_binding("kira", "Kira")
    cfg = binding.get("config")
    profile_path = PROJECT_ROOT / "Voice/profiles/temp_ai/kira_voice_profile.json"
    profile_data = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    approved_value = str(
        ((profile_data.get("source_audio") or {}).get("approved_reference_wav") or "")
    ).replace("\\", "/")
    approved_path = PROJECT_ROOT / approved_value
    resolved_value = str(getattr(cfg, "chatterbox_reference_audio", "") or "").replace("\\", "/")
    resolved_path = PROJECT_ROOT / resolved_value
    binding_warnings: list[str] = []
    if binding.get("required") is not True:
        binding_warnings.append(
            "Kira uses legacy alias auto-resolution, so required_reference_voice_binding reports required=false; "
            "the actual Chatterbox engine and approved reference path/hash are enforced below."
        )
    identity_ready = (
        cfg is not None
        and str(getattr(cfg, "engine", "")) == "chatterbox_tts"
        and approved_path.is_file()
        and resolved_path.resolve() == approved_path.resolve()
        and resolved_path.is_file()
        and bool(((profile_data.get("source_audio") or {}).get("required")))
    )
    if cfg is None:
        return {
            "passed": False,
            "reason": "voice_config_missing",
            "warnings": binding_warnings,
        }
    safe_cfg = dataclasses.replace(cfg, play_audio=False, output_dir=str(wav_path.parent))
    env = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "1",
    }
    started = time.perf_counter()
    with patched_environment(env):
        result = synthesize_text_to_wav(spoken_text, wav_path, config=safe_cfg)
    latency_ms = (time.perf_counter() - started) * 1000
    wav_check = validate_wav(wav_path)
    release_result = release_voice_output()
    passed = (
        identity_ready
        and result.get("generated") is True
        and result.get("engine") == "chatterbox_tts"
        and result.get("playback") is False
        and safe_cfg.play_audio is False
        and wav_check.get("passed") is True
    )
    return {
        "passed": passed,
        "identity_ready": identity_ready,
        "engine": getattr(cfg, "engine", ""),
        "play_audio": False,
        "generic_sapi_used": False,
        "approved_voice_profile": str(profile_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "approved_reference_audio": approved_value,
        "approved_reference_sha256": sha256_bytes(approved_path.read_bytes()) if approved_path.is_file() else None,
        "resolved_reference_audio": resolved_value,
        "resolved_reference_sha256": sha256_bytes(resolved_path.read_bytes()) if resolved_path.is_file() else None,
        "synthesis_latency_ms": round(latency_ms, 3),
        "synthesis_result": result,
        "wav_validation": wav_check,
        "voice_release_result": release_result,
        "warnings": binding_warnings,
    }


def aggregate_gate_results(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_gate: dict[int, list[Mapping[str, Any]]] = {}
    for record in records:
        gate = int(record.get("gate") or 0)
        if gate:
            by_gate.setdefault(gate, []).append(record)
    gate_summary = []
    for gate in range(1, 17):
        items = by_gate.get(gate, [])
        passed = bool(items) and all(item.get("passed") is True for item in items)
        gate_summary.append(
            {
                "gate": gate,
                "passed": passed,
                "fixture_ids": [str(item.get("fixture_id") or item.get("label") or "") for item in items],
                "record_count": len(items),
            }
        )
    return {
        "gates_1_to_16_passed": all(item["passed"] for item in gate_summary),
        "passed_gate_count": sum(item["passed"] for item in gate_summary),
        "required_gate_count": 16,
        "gates": gate_summary,
    }


def _nested_diagnostic_strings(value: Any, *, parent_key: str = "") -> list[str]:
    strings: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).casefold()
            if key_text in {"error", "errors", "issues", "warnings"}:
                strings.extend(_nested_diagnostic_strings(nested, parent_key=key_text))
            elif isinstance(nested, (Mapping, list, tuple)):
                strings.extend(_nested_diagnostic_strings(nested, parent_key=key_text))
    elif isinstance(value, (list, tuple)):
        for nested in value:
            strings.extend(_nested_diagnostic_strings(nested, parent_key=parent_key))
    elif parent_key in {"error", "errors", "issues", "warnings"} and value not in (None, ""):
        strings.append(str(value))
    return strings


def classify_runtime_events(report: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = _nested_diagnostic_strings(report)
    lowered = [item.casefold() for item in diagnostics]
    gate_records = [item for item in report.get("gate_records") or [] if isinstance(item, Mapping)]
    identity_memory_failures = sum(
        item.get("passed") is not True and int(item.get("gate") or 0) in {1, 4, 5, 6, 7}
        for item in gate_records
    )
    identity_memory_failures += sum(
        int(item.get("identity_or_memory_violation_count") or 0)
        for item in gate_records
        if int(item.get("gate") or 0) == 16
    )
    warnings = []
    for item in diagnostics:
        if item in (report.get("warnings") or []):
            warnings.append(item)
    for record in gate_records:
        warnings.extend(str(item) for item in (record.get("warnings") or []))
    return {
        "warnings": list(dict.fromkeys(warnings)),
        "diagnostics": diagnostics,
        "timeout_count": sum("timeout" in item for item in lowered),
        "crash_count": sum("crash" in item for item in lowered),
        "oom_count": sum(
            bool(re.search(r"\bout[ -]of[ -]memory\b|\b(?:cuda[ -]?)?oom\b", item))
            for item in lowered
        ),
        "malformed_reply_count": sum("malformed" in item for item in lowered),
        "repeated_reply_count": sum("repeated_reply" in item for item in lowered),
        "identity_or_memory_violation_count": identity_memory_failures,
    }


def _safe_run_directory(root: Path = EVIDENCE_ROOT) -> Path:
    root = root.resolve()
    required_root = EVIDENCE_ROOT.resolve()
    if root != required_root:
        raise AcceptanceSafetyError(f"evidence root is fixed at {required_root}")
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    candidate = root / timestamp
    suffix = 1
    while candidate.exists():
        candidate = root / f"{timestamp}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=False, exist_ok=False)
    return candidate


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    rows = ["| Gate | Pass | Evidence |", "|---:|:---:|---|"]
    for item in summary.get("gates") or []:
        rows.append(
            f"| {item.get('gate')} | {'PASS' if item.get('passed') else 'FAIL'} | "
            f"{', '.join(item.get('fixture_ids') or []) or 'missing'} |"
        )
    resources = report.get("resources") or {}
    integrity = report.get("protected_integrity") or {}
    return "\n".join(
        [
            "# Qwen Text + Voice Acceptance Evidence",
            "",
            f"- Suite: `{report.get('suite_id')}`",
            f"- Started: `{report.get('started_at')}`",
            f"- Finished: `{report.get('finished_at')}`",
            f"- Exact model: `{EXPECTED_MODEL}`",
            f"- Exact digest: `{EXPECTED_DIGEST}`",
            f"- Gates 1-16: **{'PASS' if summary.get('gates_1_to_16_passed') else 'FAIL'}**",
            f"- Protected identity/memory/person/relationship/default files unchanged: **{'PASS' if integrity.get('passed') else 'FAIL'}**",
            f"- Peak RAM used: `{resources.get('peak_ram_used_mib')}` MiB",
            f"- Peak VRAM by GPU: `{canonical_json(resources.get('peak_vram_used_mib_by_gpu') or {})}` MiB",
            "- Image input: `not used`",
            "- Microphone input: `not used`",
            "- Ordinary reply policy: top-level `think:false`",
            "- Gate 17 regressions: `separate required validation; this harness does not make the promotion decision`",
            "",
            *rows,
            "",
            "The full bounded metrics, lifecycle sequence, model response metadata, voice WAV validation, warnings, and hashes are in `acceptance_report.json`.",
            "",
        ]
    )


def persist_report(run_dir: Path, report: Mapping[str, Any]) -> None:
    resolved = run_dir.resolve()
    resolved.relative_to(EVIDENCE_ROOT.resolve())
    atomic_write_text(
        run_dir / "acceptance_report.json",
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    atomic_write_text(run_dir / "ACCEPTANCE_REPORT.md", render_markdown(report))


def execute_live_acceptance(
    *,
    endpoint: str,
    timeout_seconds: float,
    multi_turns: int,
) -> tuple[dict[str, Any], Path]:
    # Validate the endpoint and request cap before creating any evidence path
    # or starting a sampler thread.
    client = SafeOllamaClient(endpoint, timeout_seconds=timeout_seconds)
    run_dir = _safe_run_directory()
    report: dict[str, Any] = {
        "schema_version": 1,
        "suite_id": SUITE_ID,
        "started_at": utc_now(),
        "status": "running",
        "scope": {
            "text_voice_only": True,
            "image_input_used": False,
            "image_tests_run": False,
            "microphone_input_used": False,
            "semantic_webcam_enabled": False,
            "normal_defaults_changed": False,
            "publication_performed": False,
        },
        "expected_model": EXPECTED_MODEL,
        "expected_digest": EXPECTED_DIGEST,
        "ordinary_request_policy": {"think": False, "placement": "top_level"},
        "gate_records": [],
        "warnings": [],
        "errors": [],
        "sequence": [],
    }
    protected_before = hash_protected_files()
    report["protected_before"] = protected_before
    sampler = PeakResourceSampler()
    sampler_started = False
    qwen_lifecycle_owned = False
    transient_wav = run_dir / ".transient_kira_voice_probe.wav"
    try:
        sampler.start()
        sampler_started = True
        installed = validate_exact_install(client.tags())
        report["installed_model"] = installed
        report["sequence"].append({"at": utc_now(), "stage": "exact_model_digest_preflight", "passed": True})

        initial_absence = wait_for_model_state(
            client,
            loaded=False,
            timeout_seconds=2.0,
            poll_seconds=0.25,
        )
        report["initial_model_absence"] = initial_absence
        report["sequence"].append(
            {
                "at": utc_now(),
                "stage": "qwen_absent_before_acceptance",
                "passed": initial_absence["passed"],
            }
        )
        if initial_absence["passed"] is not True:
            raise AcceptanceSafetyError(
                "qwen3.5:9b was already loaded before acceptance; no owned lifecycle was started"
            )
        qwen_lifecycle_owned = True

        startup_nonce, restart_nonce = new_lifecycle_nonce_pair()
        report["lifecycle_nonce_policy"] = {
            "fixture": "strict_json_single_nonce_object",
            "nonce_bits": LIFECYCLE_NONCE_BYTES * 8,
            "unique_startup_and_restart": startup_nonce != restart_nonce,
            "semantic_content": False,
        }
        startup = lifecycle_load_probe(
            client,
            "initial_startup",
            nonce=startup_nonce,
        )
        report["lifecycle_startup"] = startup
        report["sequence"].append({"at": utc_now(), "stage": "qwen_initial_load", "passed": startup["passed"]})
        if startup.get("passed") is not True:
            report["gate_records"].append(
                {
                    "gate": 15,
                    "fixture_id": "startup_unload_restart_clean_recovery",
                    "passed": False,
                    "status": "aborted_at_startup",
                    "startup": startup,
                    "issues": ["startup_failed"],
                    "warnings": [],
                }
            )
        require_successful_startup_probe(startup)
        report["gate_records"].extend(run_deterministic_gates(client))
        report["gate_records"].append(run_multiturn_stability(client, turns=multi_turns))

        with tempfile.TemporaryDirectory(prefix="isolated_text_voice_", dir=str(run_dir)) as temp_value:
            typed = run_isolated_typed_text_voice_path(client, Path(temp_value))
        report["gate_records"].append(typed["gate_13"])
        report["sequence"].append(
            {
                "at": utc_now(),
                "stage": "isolated_existing_typed_text_path",
                "passed": typed["gate_13"]["passed"],
                "response_model": [item.get("response_model") for item in typed["captured_model_metadata"]],
            }
        )

        mid_unload = lifecycle_unload_probe(client, "before_voice_synthesis")
        report["sequence"].append({"at": utc_now(), "stage": "qwen_unloaded_before_voice", "passed": mid_unload["passed"]})
        if not mid_unload["passed"]:
            raise LocalOllamaError("Qwen did not unload before Chatterbox; voice synthesis blocked")

        voice = run_approved_kira_voice_proof(typed["spoken_text"], transient_wav)
        report["sequence"].append({"at": utc_now(), "stage": "kira_voice_synthesized_playback_off", "passed": voice["passed"]})
        try:
            transient_wav.unlink(missing_ok=True)
        except OSError as exc:
            report["warnings"].append(f"transient_voice_wav_cleanup_failed:{type(exc).__name__}:{exc}")
        report["sequence"].append(
            {
                "at": utc_now(),
                "stage": "chatterbox_released",
                "passed": (voice.get("voice_release_result") or {}).get("reason") in {"model_released", "no_cached_model"},
            }
        )

        gate14_issues: list[str] = []
        if typed["gate_13"].get("passed") is not True:
            gate14_issues.append("typed_existing_path_failed")
        if voice.get("passed") is not True:
            gate14_issues.append("approved_voice_synthesis_failed")
        if mid_unload.get("passed") is not True:
            gate14_issues.append("qwen_not_absent_before_voice")
        report["gate_records"].append(
            {
                "gate": 14,
                "fixture_id": "end_to_end_existing_text_voice_typed_kira",
                "passed": not gate14_issues,
                "status": "completed_serialized_models",
                "typed_input": True,
                "selected_candidate": "kira",
                "qwen_response_proof": typed["captured_model_metadata"],
                "visible_reply": typed["visible_reply"],
                "spoken_text": typed["spoken_text"],
                "speech_audit": typed["speech_audit"],
                "qwen_unloaded_before_voice": mid_unload,
                "voice_output_result": voice,
                "image_input_used": False,
                "microphone_input_used": False,
                "issues": gate14_issues,
                "warnings": list(voice.get("warnings") or []),
            }
        )

        restart = lifecycle_load_probe(
            client,
            "restart_after_clean_unload",
            nonce=restart_nonce,
        )
        report["sequence"].append({"at": utc_now(), "stage": "qwen_restart_reload", "passed": restart["passed"]})
        final_unload = lifecycle_unload_probe(client, "final_clean_unload")
        report["sequence"].append({"at": utc_now(), "stage": "qwen_final_clean_unload", "passed": final_unload["passed"]})
        report["gate_records"].append(
            build_gate15_record(
                startup=startup,
                unload_before_voice=mid_unload,
                restart=restart,
                final_unload=final_unload,
            )
        )
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        lowered = str(exc).casefold()
        if "out of memory" in lowered or re.search(r"\boom\b", lowered):
            report["errors"].append("OOM_ERROR_DETECTED")
        report["status"] = "failed_with_exception"
        if qwen_lifecycle_owned:
            try:
                cleanup = lifecycle_unload_probe(client, "exception_cleanup")
                report["sequence"].append({"at": utc_now(), "stage": "exception_qwen_cleanup", "passed": cleanup["passed"]})
            except Exception as cleanup_exc:
                report["errors"].append(f"cleanup:{type(cleanup_exc).__name__}: {cleanup_exc}")
        else:
            report["sequence"].append(
                {
                    "at": utc_now(),
                    "stage": "exception_qwen_cleanup_skipped_unowned",
                    "passed": True,
                }
            )
        try:
            voice_cleanup = release_voice_output()
            report["sequence"].append({"at": utc_now(), "stage": "exception_voice_cleanup", "result": voice_cleanup})
        except Exception as cleanup_exc:
            report["errors"].append(f"voice_cleanup:{type(cleanup_exc).__name__}: {cleanup_exc}")
    finally:
        try:
            transient_wav.unlink(missing_ok=True)
        except OSError:
            pass
        report["resources"] = sampler.stop() if sampler_started else {
            "sample_count": 0,
            "probe_errors": ["resource_sampler_did_not_start"],
        }
        for probe_error in report["resources"].get("probe_errors") or []:
            report["warnings"].append(f"resource_probe:{probe_error}")
        protected_after = hash_protected_files()
        report["protected_after"] = protected_after
        report["protected_integrity"] = compare_protected_hashes(protected_before, protected_after)
        report["summary"] = aggregate_gate_results(report["gate_records"])
        report["finished_at"] = utc_now()
        complete = (
            report["summary"]["gates_1_to_16_passed"]
            and report["protected_integrity"]["passed"]
            and not report["errors"]
        )
        report["status"] = "acceptance_1_to_16_pass" if complete else "acceptance_1_to_16_fail"
        report["promotion_decision"] = "none_gate_17_regressions_and_owner_workflow_still_required"
        report["runtime_event_summary"] = classify_runtime_events(report)
        persist_report(run_dir, report)
    return report, run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded, no-image/no-microphone Qwen Text + Voice acceptance gates 1-16."
    )
    parser.add_argument(
        "--execute-live-acceptance",
        action="store_true",
        help="Required explicit acknowledgement that local Qwen and Chatterbox inference will run.",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("KIRA_OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat"),
        help="Loopback Ollama endpoint only.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--multi-turns", type=int, default=DEFAULT_MULTI_TURNS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.execute_live_acceptance:
        parser.error(
            "live inference is disabled by default; pass --execute-live-acceptance after reviewing the bounded plan"
        )
    try:
        report, run_dir = execute_live_acceptance(
            endpoint=args.endpoint,
            timeout_seconds=args.timeout_seconds,
            multi_turns=args.multi_turns,
        )
    except (AcceptanceSafetyError, LocalOllamaError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": report["status"], "evidence_dir": str(run_dir)}, indent=2))
    return 0 if report["status"] == "acceptance_1_to_16_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
