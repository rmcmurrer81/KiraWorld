"""
Local voice output for Kira/Lisa text replies.

Stage rule: this is output only. It does not open the microphone, listen,
transcribe, or change attention state.
"""

from __future__ import annotations

import argparse
import atexit
import copy
import gc
import hashlib
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable
from urllib import request as urllib_request


# Production code imports this module only as ``Core.voice_output``.  Keep the
# old top-level name as a compatibility alias *to this same object* so a late
# legacy import cannot create a second process-local GPU serialization lock.
if __name__ == "Core.voice_output":
    sys.modules.setdefault("voice_output", sys.modules[__name__])
elif __name__ == "voice_output":  # Legacy-first import: prevent a later duplicate.
    sys.modules.setdefault("Core.voice_output", sys.modules[__name__])

if __package__:
    from .dialogue_audio_signal import assess_generated_speech_chunk, gentle_proximity_correction
    from .dialogue_tts import split_for_tts, spoken_words
    from .persistent_blackwell_voice_integration import (
        begin_session as _begin_persistent_blackwell_voice_session_v1,
        feature_enabled as _persistent_blackwell_voice_feature_enabled_v1,
        prewarm as _prewarm_persistent_blackwell_voice_v1,
        release as _release_persistent_blackwell_voice_v1,
        status as _persistent_blackwell_voice_status_v1,
        synthesize as _synthesize_with_persistent_blackwell_voice_v1,
    )
    from .persistent_blackwell_voice_integration_v2 import (
        begin_session as _begin_persistent_blackwell_voice_session_v2,
        feature_enabled as _persistent_blackwell_voice_feature_enabled_v2,
        prewarm as _prewarm_persistent_blackwell_voice_v2,
        release as _release_persistent_blackwell_voice_v2,
        release_if_owner as _release_persistent_blackwell_voice_v2_if_owner,
        status as _persistent_blackwell_voice_status_v2,
        suspend_if_owner as _suspend_persistent_blackwell_voice_v2_if_owner,
        synthesize as _synthesize_with_persistent_blackwell_voice_v2,
    )
else:  # Direct ``Core`` imports used by older launchers/tests.
    from dialogue_audio_signal import assess_generated_speech_chunk, gentle_proximity_correction
    from dialogue_tts import split_for_tts, spoken_words
    from persistent_blackwell_voice_integration import (
        begin_session as _begin_persistent_blackwell_voice_session_v1,
        feature_enabled as _persistent_blackwell_voice_feature_enabled_v1,
        prewarm as _prewarm_persistent_blackwell_voice_v1,
        release as _release_persistent_blackwell_voice_v1,
        status as _persistent_blackwell_voice_status_v1,
        synthesize as _synthesize_with_persistent_blackwell_voice_v1,
    )
    from persistent_blackwell_voice_integration_v2 import (
        begin_session as _begin_persistent_blackwell_voice_session_v2,
        feature_enabled as _persistent_blackwell_voice_feature_enabled_v2,
        prewarm as _prewarm_persistent_blackwell_voice_v2,
        release as _release_persistent_blackwell_voice_v2,
        release_if_owner as _release_persistent_blackwell_voice_v2_if_owner,
        status as _persistent_blackwell_voice_status_v2,
        suspend_if_owner as _suspend_persistent_blackwell_voice_v2_if_owner,
        synthesize as _synthesize_with_persistent_blackwell_voice_v2,
    )


def _persistent_status_has_owned_state(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and (
            value.get("session_owner")
            or value.get("owned_worker_running")
            or value.get("model_loaded")
        )
    )


def _selected_persistent_blackwell_voice_version() -> str:
    # V2 wins only when its distinct flag is explicit.  V1 remains available
    # as a byte-preserved rollback candidate and the normal one-shot router is
    # unchanged when neither flag is enabled.
    if _persistent_blackwell_voice_feature_enabled_v2():
        return "v2"
    if _persistent_blackwell_voice_feature_enabled_v1():
        return "v1"
    return "none"


def persistent_blackwell_voice_feature_enabled() -> bool:
    return _selected_persistent_blackwell_voice_version() != "none"


def persistent_blackwell_voice_status() -> dict[str, Any]:
    v1 = _persistent_blackwell_voice_status_v1()
    v2 = _persistent_blackwell_voice_status_v2()
    selected = _selected_persistent_blackwell_voice_version()
    selected_status = v2 if selected == "v2" else v1 if selected == "v1" else {}
    aggregate_owner = str(v2.get("session_owner") or v1.get("session_owner") or "")
    return {
        **selected_status,
        "selected_candidate_version": selected,
        "application_route_connected": True,
        "production_route_promoted": False,
        "production_route_connected": False,
        # Top-level lifecycle fields always describe the *selected* route.
        # Aggregate state is separately named so a stale rollback worker can
        # never make the selected candidate look warm or inherit its owner.
        "session_owner": str(selected_status.get("session_owner") or ""),
        "owned_worker_running": bool(selected_status.get("owned_worker_running")),
        "model_loaded": bool(selected_status.get("model_loaded")),
        "any_owned_session_owner": aggregate_owner,
        "any_owned_worker_running": bool(
            v1.get("owned_worker_running") or v2.get("owned_worker_running")
        ),
        "any_model_loaded": bool(v1.get("model_loaded") or v2.get("model_loaded")),
        "candidate_versions": {
            "v1": {
                "feature_enabled": bool(v1.get("feature_enabled")),
                "owned_state_present": _persistent_status_has_owned_state(v1),
                "session_owner": str(v1.get("session_owner") or ""),
                "owned_worker_running": bool(v1.get("owned_worker_running")),
                "model_loaded": bool(v1.get("model_loaded")),
            },
            "v2": {
                "feature_enabled": bool(v2.get("feature_enabled")),
                "owned_state_present": _persistent_status_has_owned_state(v2),
                "session_owner": str(v2.get("session_owner") or ""),
                "owned_worker_running": bool(v2.get("owned_worker_running")),
                "model_loaded": bool(v2.get("model_loaded")),
            },
        },
    }


def _release_unselected_persistent_blackwell_voice(selected: str) -> dict[str, Any]:
    # Release only a worker owned by these exact integration singletons.  No
    # process discovery or PID-wide termination is performed.
    releases: dict[str, Any] = {}
    if selected != "v1":
        v1 = _persistent_blackwell_voice_status_v1()
        if _persistent_status_has_owned_state(v1):
            releases["v1"] = _release_persistent_blackwell_voice_v1(
                "persistent_candidate_selection_changed"
            )
    if selected != "v2":
        v2 = _persistent_blackwell_voice_status_v2()
        if _persistent_status_has_owned_state(v2):
            releases["v2"] = _release_persistent_blackwell_voice_v2(
                "persistent_candidate_selection_changed"
            )
    cleanup_proven = all(
        isinstance(result, dict)
        and isinstance(result.get("cleanup"), dict)
        and result["cleanup"].get("owned_worker_closed") is True
        for result in releases.values()
    )
    return {
        "selected_candidate_version": selected,
        "release_attempts": releases,
        "unselected_owned_state_was_present": bool(releases),
        "all_unselected_owned_workers_closed": cleanup_proven,
    }


def begin_persistent_blackwell_voice_session(owner: str) -> dict[str, Any]:
    selected = _selected_persistent_blackwell_voice_version()
    selection_cleanup = _release_unselected_persistent_blackwell_voice(selected)
    if selection_cleanup.get("all_unselected_owned_workers_closed") is not True:
        return {
            "begun": False,
            "reason": "unselected_persistent_worker_cleanup_not_proven",
            "selected_candidate_version": selected,
            "selection_cleanup": selection_cleanup,
            "feature_enabled": selected != "none",
            "playback": False,
            "generated_audio": False,
        }
    if selected == "v2":
        return {
            **_begin_persistent_blackwell_voice_session_v2(owner),
            "selected_candidate_version": "v2",
            "application_route_connected": True,
            "production_route_promoted": False,
        }
    result = _begin_persistent_blackwell_voice_session_v1(owner)
    return {
        **result,
        "selected_candidate_version": selected,
        "application_route_connected": True,
        "production_route_promoted": False,
    }


def prewarm_persistent_blackwell_voice(owner: str) -> dict[str, Any]:
    selected = _selected_persistent_blackwell_voice_version()
    selection_cleanup = _release_unselected_persistent_blackwell_voice(selected)
    if selection_cleanup.get("all_unselected_owned_workers_closed") is not True:
        return {
            "warmed": False,
            "reason": "unselected_persistent_worker_cleanup_not_proven",
            "selected_candidate_version": selected,
            "selection_cleanup": selection_cleanup,
            "playback": False,
            "generated_audio": False,
        }
    if selected == "v2":
        serialized_route = exact_qwen_persistent_v2_resource_serialization_required()
        if not serialized_route:
            return {
                **_prewarm_persistent_blackwell_voice_v2(owner),
                "selected_candidate_version": "v2",
                "application_route_connected": True,
                "production_route_promoted": False,
            }
        resource_lock = exact_qwen_blackwell_v2_resource_lock()
        resource_lock_acquired = resource_lock.acquire(
            timeout=EXACT_QWEN_BLACKWELL_V2_RESOURCE_LOCK_BOUND_SECONDS
        )
        if not resource_lock_acquired:
            return {
                "warmed": False,
                "reason": "exact_qwen_voice_resource_lock_timeout_before_prewarm",
                "selected_candidate_version": "v2",
                "resource_serialization_required": True,
                "resource_lock_acquired": False,
                "fallback_allowed": False,
                "route_blocked": True,
                "application_route_connected": True,
                "production_route_promoted": False,
                "playback": False,
                "generated_audio": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
            }
        try:
            qwen_absence = wait_for_exact_qwen_absence()
            if qwen_absence.get("qwen_absent_proven") is not True:
                return {
                    "warmed": False,
                    "reason": "exact_qwen_absence_not_proven_before_voice_prewarm",
                    "selected_candidate_version": "v2",
                    "resource_serialization_required": True,
                    "resource_lock_acquired": True,
                    "qwen_absence_before_voice_prewarm": qwen_absence,
                    "fallback_allowed": False,
                    "route_blocked": True,
                    "application_route_connected": True,
                    "production_route_promoted": False,
                    "playback": False,
                    "generated_audio": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                }
            result = _prewarm_persistent_blackwell_voice_v2(owner)
            return {
                **result,
                "selected_candidate_version": "v2",
                "resource_serialization_required": True,
                "resource_lock_acquired": True,
                "qwen_absence_before_voice_prewarm": qwen_absence,
                "application_route_connected": True,
                "production_route_promoted": False,
            }
        finally:
            resource_lock.release()
    result = _prewarm_persistent_blackwell_voice_v1(owner)
    return {
        **result,
        "selected_candidate_version": selected,
        "application_route_connected": True,
        "production_route_promoted": False,
    }


def synthesize_with_persistent_blackwell_voice(**kwargs: Any) -> dict[str, Any]:
    selected = _selected_persistent_blackwell_voice_version()
    selection_cleanup = _release_unselected_persistent_blackwell_voice(selected)
    if selection_cleanup.get("all_unselected_owned_workers_closed") is not True:
        return {
            "generated": False,
            "reason": "unselected_persistent_worker_cleanup_not_proven",
            "selected_candidate_version": selected,
            "candidate_attempted": False,
            "fallback_allowed": False,
            "route_blocked": True,
            "cancelled": False,
            "target_cleanup_proven": True,
            "selection_cleanup": selection_cleanup,
            "persistent_route_eligible": False,
            "playback": False,
        }
    if selected == "v2":
        serialized_route = exact_qwen_persistent_v2_resource_serialization_required()
        if not serialized_route:
            return {
                **_synthesize_with_persistent_blackwell_voice_v2(**kwargs),
                "selected_candidate_version": "v2",
                "application_route_connected": True,
                "production_route_promoted": False,
            }
        resource_lock = exact_qwen_blackwell_v2_resource_lock()
        resource_lock_acquired = resource_lock.acquire(
            timeout=EXACT_QWEN_BLACKWELL_V2_RESOURCE_LOCK_BOUND_SECONDS
        )
        if not resource_lock_acquired:
            return {
                "generated": False,
                "reason": "exact_qwen_voice_resource_lock_timeout",
                "selected_candidate_version": "v2",
                "candidate_attempted": False,
                "persistent_route_eligible": False,
                "fallback_allowed": False,
                "route_blocked": True,
                "cancelled": False,
                "target_cleanup_proven": True,
                "resource_serialization_required": True,
                "resource_lock_acquired": False,
                "qwen_absence_before_voice": None,
                "application_route_connected": True,
                "production_route_promoted": False,
                "playback": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
            }
        try:
            qwen_absence = wait_for_exact_qwen_absence()
            if qwen_absence.get("qwen_absent_proven") is not True:
                return {
                    "generated": False,
                    "reason": "exact_qwen_absence_not_proven_before_voice",
                    "selected_candidate_version": "v2",
                    "candidate_attempted": False,
                    "persistent_route_eligible": False,
                    "fallback_allowed": False,
                    "route_blocked": True,
                    "cancelled": False,
                    "target_cleanup_proven": True,
                    "resource_serialization_required": True,
                    "resource_lock_acquired": True,
                    "qwen_absence_before_voice": qwen_absence,
                    "application_route_connected": True,
                    "production_route_promoted": False,
                    "playback": False,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                }
            result = _synthesize_with_persistent_blackwell_voice_v2(**kwargs)
            if result.get("generated") is not True:
                # The exact serialized route never falls through to CPU,
                # generic, SAPI, or the one-shot GPU rollback route.
                result = {
                    **result,
                    "persistent_route_eligible": False,
                    "fallback_allowed": False,
                    "route_blocked": True,
                    "generic_voice_used": False,
                    "sapi_voice_used": False,
                    "playback": False,
                }
            return {
                **result,
                "selected_candidate_version": "v2",
                "resource_serialization_required": True,
                "resource_lock_acquired": True,
                "qwen_absence_before_voice": qwen_absence,
                "lazy_voice_load_before_synthesis": True,
                "application_route_connected": True,
                "production_route_promoted": False,
            }
        finally:
            resource_lock.release()
    result = _synthesize_with_persistent_blackwell_voice_v1(**kwargs)
    return {
        **result,
        "selected_candidate_version": selected,
        "application_route_connected": True,
        "production_route_promoted": False,
    }


def release_persistent_blackwell_voice(reason: str = "explicit_release") -> dict[str, Any]:
    v1_before = _persistent_blackwell_voice_status_v1()
    v2_before = _persistent_blackwell_voice_status_v2()
    v1_release = (
        _release_persistent_blackwell_voice_v1(reason)
        if _persistent_status_has_owned_state(v1_before)
        else None
    )
    v2_release = (
        _release_persistent_blackwell_voice_v2(reason)
        if _persistent_status_has_owned_state(v2_before)
        else None
    )
    releases = [item for item in (v1_release, v2_release) if isinstance(item, dict)]
    owned_worker_closed = all(
        (item.get("cleanup") or {}).get("owned_worker_closed") is True
        for item in releases
    )
    model_was_loaded = any(
        (item.get("cleanup") or {}).get("model_was_loaded") is True
        for item in releases
    )
    return {
        "released": bool(model_was_loaded and owned_worker_closed),
        "release_attempted": bool(releases),
        "model_was_loaded": model_was_loaded,
        "reason": reason,
        "persistent_integration": True,
        "owned_worker_closed": owned_worker_closed,
        "v1_release": v1_release,
        "v2_release": v2_release,
        "playback": False,
        "generated_audio": False,
    }


def release_persistent_blackwell_voice_owner(
    expected_owner: str,
    reason: str = "owner_bound_release",
) -> dict[str, Any]:
    """Cancel only the exact v2 owner captured at a shell session boundary."""

    return {
        **_release_persistent_blackwell_voice_v2_if_owner(expected_owner, reason),
        "selected_candidate_version": "v2",
        "application_route_connected": True,
        "production_route_promoted": False,
    }


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "Voice" / "kira_voice_output_config.json"
# Legacy aliases remain for callers/tests that inspect the accepted CPU
# sidecar directly. Production routing below is governed by the hash-bound
# two-route manifest.
KIRA_CHATTERBOX_SIDECAR_ROOT = PROJECT_ROOT / "Voice" / "sidecars" / "chatterbox_py311"
KIRA_CHATTERBOX_SIDECAR_CONFIG = KIRA_CHATTERBOX_SIDECAR_ROOT / "sidecar_config.json"
KIRA_CHATTERBOX_SIDECAR_WORKER = KIRA_CHATTERBOX_SIDECAR_ROOT / "sidecar_worker.py"
KIRA_CHATTERBOX_SIDECAR_PYTHON = KIRA_CHATTERBOX_SIDECAR_ROOT / ".venv" / "Scripts" / "python.exe"
KIRA_APPROVED_VOICE_ROUTING_CONFIG = (
    PROJECT_ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json"
)
KIRA_APPROVED_REFERENCE_RELATIVE = (
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
    "model_input/approved_reference.wav"
)
KIRA_APPROVED_PROFILE_SHA256 = (
    "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
)
KIRA_APPROVED_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
)
KIRA_QWEN_MODEL = "qwen3.5:9b"
KIRA_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
KIRA_QWEN_PS_ENDPOINT = "http://127.0.0.1:11434/api/ps"
BLACKWELL_RUNTIME_CACHE_ROOT = (
    PROJECT_ROOT / "RecoverySprint" / "runtime_cache" / "blackwell_chatterbox"
)
MAX_CHATTERBOX_SIDECAR_RESPONSE_BYTES = 1024 * 1024


@dataclass
class VoiceOutputConfig:
    enabled: bool = True
    engine: str = "windows_sapi_powershell"
    voice_name: str = ""
    rate: int = -1
    volume: int = 90
    max_chars: int = 1600
    dry_run: bool = False
    chatterbox_reference_audio: str = ""
    chatterbox_device: str = "auto"
    output_dir: str = ""
    play_audio: bool = True
    # Chatterbox PCM calibration. These are zero/off by default so one
    # person's listening preference cannot change any other voice. Robert's
    # approved self-voice profile supplies its private-runtime values.
    pcm_output_gain_db: float = 0.0
    proximity_cut_hz: float = 0.0
    proximity_cut_mix: float = 0.0


_CHATTERBOX_LOCK = threading.Lock()
_CHATTERBOX_MODEL: Any | None = None
_CHATTERBOX_DEVICE: str | None = None
_CHATTERBOX_IDLE_TIMER: threading.Timer | None = None
_CHATTERBOX_IDLE_TOKEN = 0
_CHATTERBOX_LAST_USED_MONOTONIC = 0.0

# Qwen text generation and the exact persistent v2 CUDA voice route share one
# GPU.  This host-only mutex spans the text request and each v2 load/generation
# operation; the integration's own operation lock still owns its child
# protocol.  No default route or feature flag is changed by its existence.
_EXACT_QWEN_BLACKWELL_V2_RESOURCE_LOCK = threading.RLock()
EXACT_QWEN_BLACKWELL_V2_RESOURCE_LOCK_BOUND_SECONDS = 120.0
EXACT_QWEN_ABSENCE_WAIT_SECONDS = 15.0


def exact_qwen_persistent_v2_resource_serialization_required(
    *,
    model_name: str | None = None,
    route_active: bool | None = None,
    model_backend: str | None = None,
) -> bool:
    """Identify only the explicit qwen3.5:9b + persistent-v2 live route."""

    selected_model = str(
        model_name if model_name is not None else os.environ.get("KIRA_MODEL_NAME", "")
    ).strip().casefold()
    selected_backend = str(
        model_backend
        if model_backend is not None
        else os.environ.get("KIRA_MODEL_BACKEND", "")
    ).strip().casefold()
    if route_active is None:
        route_active = any(
            str(os.environ.get(name, "0")).strip().casefold()
            in {"1", "true", "yes", "on"}
            for name in ("KIRA_TEXT_VOICE_CHAT_ACTIVE", "KIRA_WORLD_SHELL_ACTIVE")
        )
    return bool(
        selected_model == KIRA_QWEN_MODEL
        and selected_backend == "ollama"
        and route_active
        and _selected_persistent_blackwell_voice_version() == "v2"
    )


def exact_qwen_blackwell_v2_resource_lock() -> threading.RLock:
    """Return the process-local mutex shared by the exact text/voice route."""

    return _EXACT_QWEN_BLACKWELL_V2_RESOURCE_LOCK

# The accepted Blackwell worker is deliberately one-shot.  Its inexpensive
# policy/runtime self-check used to launch a second Python process before every
# synthesis even though the route, interpreter, artifacts, environment, and
# required CUDA contract had not changed within the owner application's
# process.  Cache only a *successful* Blackwell self-check for this Python
# process.  Synthesis is never cached, CPU is never cached, and the router still
# proves Qwen absence immediately before every GPU synthesis.
_APPROVED_SIDECAR_SELF_CHECK_CACHE_LOCK = threading.Lock()
_APPROVED_SIDECAR_SELF_CHECK_CACHE: dict[str, dict[str, Any]] = {}


def _clear_approved_sidecar_self_check_cache() -> None:
    """Forget session-only Blackwell readiness evidence."""
    with _APPROVED_SIDECAR_SELF_CHECK_CACHE_LOCK:
        _APPROVED_SIDECAR_SELF_CHECK_CACHE.clear()


atexit.register(_clear_approved_sidecar_self_check_cache)


def _release_chatterbox_model_locked() -> dict[str, Any]:
    """Release the cached model while ``_CHATTERBOX_LOCK`` is held."""
    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    started = time.perf_counter()
    telemetry: dict[str, Any] = {
        "model_present_before": _CHATTERBOX_MODEL is not None,
        "device_before": str(_CHATTERBOX_DEVICE or ""),
        "torch_import_attempted": False,
        "cuda_cache_release_attempted": False,
        "cuda_cache_release_completed": False,
    }
    clear_started = time.perf_counter()
    _CHATTERBOX_MODEL = None
    _CHATTERBOX_DEVICE = None
    telemetry["model_reference_clear_seconds"] = round(
        time.perf_counter() - clear_started, 6
    )
    gc_started = time.perf_counter()
    gc.collect()
    telemetry["gc_collect_seconds"] = round(time.perf_counter() - gc_started, 6)
    try:
        torch_started = time.perf_counter()
        telemetry["torch_import_attempted"] = True
        import torch

        telemetry["torch_import_seconds"] = round(
            time.perf_counter() - torch_started, 6
        )

        if torch.cuda.is_available():
            cuda_started = time.perf_counter()
            telemetry["cuda_cache_release_attempted"] = True
            torch.cuda.empty_cache()
            telemetry["cuda_cache_release_completed"] = True
            telemetry["cuda_empty_cache_seconds"] = round(
                time.perf_counter() - cuda_started, 6
            )
    except Exception as exc:
        telemetry["cleanup_error_type"] = type(exc).__name__
    telemetry["total_seconds"] = round(time.perf_counter() - started, 6)
    return telemetry


def _cancel_chatterbox_idle_timer_locked() -> None:
    global _CHATTERBOX_IDLE_TIMER, _CHATTERBOX_IDLE_TOKEN
    _CHATTERBOX_IDLE_TOKEN += 1
    timer = _CHATTERBOX_IDLE_TIMER
    _CHATTERBOX_IDLE_TIMER = None
    if timer is not None:
        timer.cancel()


def _voice_idle_unload_seconds() -> float:
    """Return the configured warm-cache window; zero disables idle unloading."""
    raw = str(os.environ.get("KIRA_VOICE_IDLE_UNLOAD_SECONDS", "0")).strip()
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if not 0.0 < seconds <= 86400.0:
        return 0.0
    return seconds


def _chatterbox_idle_unload_callback(token: int) -> None:
    global _CHATTERBOX_IDLE_TIMER
    with _CHATTERBOX_LOCK:
        if token != _CHATTERBOX_IDLE_TOKEN:
            return
        _CHATTERBOX_IDLE_TIMER = None
        _release_chatterbox_model_locked()


def _schedule_chatterbox_idle_unload_locked() -> bool:
    """Schedule one race-safe model release after the configured idle window."""
    global _CHATTERBOX_IDLE_TIMER, _CHATTERBOX_IDLE_TOKEN, _CHATTERBOX_LAST_USED_MONOTONIC
    _cancel_chatterbox_idle_timer_locked()
    seconds = _voice_idle_unload_seconds()
    if seconds <= 0 or _CHATTERBOX_MODEL is None:
        return False
    _CHATTERBOX_LAST_USED_MONOTONIC = time.monotonic()
    token = _CHATTERBOX_IDLE_TOKEN
    timer = threading.Timer(seconds, _chatterbox_idle_unload_callback, args=(token,))
    timer.daemon = True
    _CHATTERBOX_IDLE_TIMER = timer
    timer.start()
    return True


def _unload_chatterbox_model() -> None:
    """Synchronously release the cached model without racing another render."""
    with _CHATTERBOX_LOCK:
        _cancel_chatterbox_idle_timer_locked()
        _release_chatterbox_model_locked()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_path(relative: Any) -> Path:
    value = Path(str(relative or "").replace("\\", "/"))
    if not value.parts or value.is_absolute() or ".." in value.parts:
        raise ValueError("voice route path must be project-relative")
    resolved = (PROJECT_ROOT / value).resolve()
    resolved.relative_to(PROJECT_ROOT.resolve())
    return resolved


def _matches_exact_kira_approved_reference_path(cfg: VoiceOutputConfig) -> bool:
    raw = str(cfg.chatterbox_reference_audio or "").strip()
    if not raw:
        return False
    try:
        configured = Path(raw)
        if not configured.is_absolute():
            configured = PROJECT_ROOT / configured
        return configured.resolve() == (PROJECT_ROOT / KIRA_APPROVED_REFERENCE_RELATIVE).resolve()
    except (OSError, ValueError):
        return False


def _is_exact_kira_approved_reference(cfg: VoiceOutputConfig) -> bool:
    return (
        str(cfg.engine or "") == "chatterbox_tts"
        and _matches_exact_kira_approved_reference_path(cfg)
    )


def _load_approved_voice_routing_config() -> dict[str, Any]:
    """Load the two approved routes and verify every referenced artifact.

    Policy/identity failures invalidate the whole router. A route-local file,
    hash, or runtime-status failure invalidates only that route so the accepted
    CPU sidecar can still serve as the automatic identity-preserving fallback.
    """
    result: dict[str, Any] = {
        "valid": False,
        "reason": "approved_voice_routing_unavailable",
        "issues": [],
        "routes": [],
    }
    if not KIRA_APPROVED_VOICE_ROUTING_CONFIG.is_file():
        result["issues"].append("routing_config_missing")
        return result
    try:
        data = json.loads(KIRA_APPROVED_VOICE_ROUTING_CONFIG.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        result["issues"].append(f"routing_config_parse_error:{type(exc).__name__}")
        return result
    if not isinstance(data, dict):
        result["issues"].append("routing_config_not_object")
        return result

    policy = data.get("policy") if isinstance(data.get("policy"), dict) else {}
    global_issues: list[str] = []
    expected_policy = {
        "preferred_route": "blackwell_gpu",
        "automatic_fallback_routes": ["sealed_cpu"],
        "gpu_requires_qwen_absence": True,
        "public_spoken_only": True,
        "playback_inside_sidecar": False,
        "generic_voice_fallback_allowed": False,
        "sapi_fallback_allowed": False,
        "unsealed_in_process_fallback_allowed": False,
        "unload_arbitrary_models_allowed": False,
    }
    if data.get("schema_version") != 1:
        global_issues.append("routing_schema_mismatch")
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            global_issues.append(f"routing_policy_mismatch:{key}")
    if data.get("approved_profile_sha256") != KIRA_APPROVED_PROFILE_SHA256:
        global_issues.append("routing_profile_hash_mismatch")
    if data.get("approved_reference") != KIRA_APPROVED_REFERENCE_RELATIVE:
        global_issues.append("routing_reference_path_mismatch")
    if data.get("approved_reference_sha256") != KIRA_APPROVED_REFERENCE_SHA256:
        global_issues.append("routing_reference_hash_mismatch")
    if data.get("qwen_model") != KIRA_QWEN_MODEL or data.get("qwen_digest") != KIRA_QWEN_DIGEST:
        global_issues.append("routing_qwen_pin_mismatch")

    try:
        profile = _project_path(data.get("approved_profile"))
        reference = _project_path(data.get("approved_reference"))
        if not profile.is_file() or _sha256_file(profile) != KIRA_APPROVED_PROFILE_SHA256:
            global_issues.append("approved_profile_file_hash_mismatch")
        if not reference.is_file() or _sha256_file(reference) != KIRA_APPROVED_REFERENCE_SHA256:
            global_issues.append("approved_reference_file_hash_mismatch")
    except (OSError, ValueError):
        global_issues.append("approved_identity_path_invalid")

    route_values = data.get("routes") if isinstance(data.get("routes"), list) else []
    route_ids = [str(item.get("route_id") or "") for item in route_values if isinstance(item, dict)]
    if route_ids != ["blackwell_gpu", "sealed_cpu"]:
        global_issues.append("approved_route_order_or_identity_mismatch")

    validated_routes: list[dict[str, Any]] = []
    for raw_route in route_values:
        if not isinstance(raw_route, dict):
            continue
        route = dict(raw_route)
        route_issues: list[str] = []
        route_id = str(route.get("route_id") or "")
        expected_device = "cuda" if route_id == "blackwell_gpu" else "cpu"
        expected_role = "preferred" if route_id == "blackwell_gpu" else "automatic_fallback_only"
        expected_environment = (
            "restricted_blackwell_gpu"
            if route_id == "blackwell_gpu"
            else "restricted_cpu_cuda_hidden"
        )
        if route.get("compute_device") != expected_device:
            route_issues.append("compute_device_mismatch")
        if route.get("role") != expected_role:
            route_issues.append("route_role_mismatch")
        if route.get("environment_profile") != expected_environment:
            route_issues.append("environment_profile_mismatch")
        resolved: dict[str, Path] = {}
        for key in ("config", "worker", "python"):
            try:
                path = _project_path(route.get(key))
                resolved[key] = path
                if not path.is_file():
                    route_issues.append(f"{key}_missing")
            except (OSError, ValueError):
                route_issues.append(f"{key}_path_invalid")
        for key in ("config", "worker"):
            path = resolved.get(key)
            if path and path.is_file() and _sha256_file(path) != str(
                route.get(f"{key}_sha256") or ""
            ).casefold():
                route_issues.append(f"{key}_hash_mismatch")
        sidecar_config: dict[str, Any] = {}
        config_path = resolved.get("config")
        if config_path and config_path.is_file():
            try:
                parsed = json.loads(config_path.read_text(encoding="utf-8"))
                sidecar_config = parsed if isinstance(parsed, dict) else {}
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                route_issues.append("sidecar_config_parse_error")
        if not sidecar_config:
            route_issues.append("sidecar_config_invalid")
        else:
            if sidecar_config.get("schema_version") != 1:
                route_issues.append("sidecar_schema_mismatch")
            if sidecar_config.get("approved_profile_sha256") != KIRA_APPROVED_PROFILE_SHA256:
                route_issues.append("sidecar_profile_hash_mismatch")
            if sidecar_config.get("approved_reference") != KIRA_APPROVED_REFERENCE_RELATIVE:
                route_issues.append("sidecar_reference_path_mismatch")
            if sidecar_config.get("approved_reference_sha256") != KIRA_APPROVED_REFERENCE_SHA256:
                route_issues.append("sidecar_reference_hash_mismatch")
            if sidecar_config.get("worker_sha256") != route.get("worker_sha256"):
                route_issues.append("sidecar_worker_binding_mismatch")
            if sidecar_config.get("input_channel") != "public_spoken_only":
                route_issues.append("sidecar_channel_policy_mismatch")
            if sidecar_config.get("playback") is not False:
                route_issues.append("sidecar_playback_policy_mismatch")
            if sidecar_config.get("generic_voice_fallback_allowed") is not False:
                route_issues.append("sidecar_generic_fallback_policy_mismatch")
            if sidecar_config.get("offline_cache_only") is not True:
                route_issues.append("sidecar_offline_policy_mismatch")
            if sidecar_config.get("compute_device") != expected_device:
                route_issues.append("sidecar_compute_device_mismatch")
            if route_id == "blackwell_gpu":
                if sidecar_config.get("production_routing_authorized") is not True:
                    route_issues.append("gpu_production_authorization_missing")
                if sidecar_config.get("production_role") != "preferred_approved_kira_voice":
                    route_issues.append("gpu_production_role_mismatch")
                for evidence_key in ("standalone_acceptance", "serialized_acceptance"):
                    if sidecar_config.get(evidence_key) != route.get(evidence_key) or sidecar_config.get(
                        f"{evidence_key}_sha256"
                    ) != route.get(f"{evidence_key}_sha256"):
                        route_issues.append(f"gpu_{evidence_key}_binding_mismatch")
            elif sidecar_config.get("production_role") != "automatic_approved_kira_fallback_only":
                route_issues.append("cpu_production_role_mismatch")
        if route_id == "blackwell_gpu":
            for evidence_key in ("standalone_acceptance", "serialized_acceptance"):
                try:
                    evidence = _project_path(route.get(evidence_key))
                    if not evidence.is_file() or _sha256_file(evidence) != str(
                        route.get(f"{evidence_key}_sha256") or ""
                    ).casefold():
                        route_issues.append(f"{evidence_key}_hash_mismatch")
                except (OSError, ValueError):
                    route_issues.append(f"{evidence_key}_path_invalid")
        route["valid"] = not route_issues
        route["issues"] = route_issues
        route["resolved"] = {key: path for key, path in resolved.items()}
        route["sidecar_config"] = sidecar_config
        validated_routes.append(route)

    result.update(data)
    result["valid"] = not global_issues
    result["reason"] = "ok" if not global_issues else "approved_voice_routing_contract_failed"
    result["issues"] = global_issues
    result["routes"] = validated_routes
    result["routing_config_sha256"] = _sha256_file(KIRA_APPROVED_VOICE_ROUTING_CONFIG)
    return result


def _load_kira_chatterbox_sidecar_config() -> dict[str, Any] | None:
    """Compatibility accessor for the accepted sealed CPU fallback config."""
    routing = _load_approved_voice_routing_config()
    if routing.get("valid") is not True:
        return None
    for route in routing.get("routes") or []:
        if route.get("route_id") == "sealed_cpu" and route.get("valid") is True:
            return dict(route.get("sidecar_config") or {})
    return None


def _kira_chatterbox_sidecar_binding(cfg: VoiceOutputConfig) -> dict[str, Any] | None:
    if not _is_exact_kira_approved_reference(cfg):
        return None
    routing = _load_approved_voice_routing_config()
    return routing if routing.get("valid") is True else None


def _restricted_sidecar_parent_values() -> dict[str, str]:
    allowed = (
        "USERNAME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA",
        "SystemRoot", "WINDIR", "TEMP", "TMP", "PATH", "PATHEXT",
        "PROGRAMDATA", "DriverData", "ComSpec", "SystemDrive", "ProgramFiles",
        "ProgramFiles(x86)", "ProgramW6432", "CommonProgramFiles",
        "CommonProgramFiles(x86)", "CommonProgramW6432",
    )
    return {key: value for key in allowed if (value := os.environ.get(key))}


def _chatterbox_sidecar_environment(route: dict[str, Any] | None = None) -> dict[str, str]:
    route_id = str((route or {}).get("route_id") or "sealed_cpu")
    env = _restricted_sidecar_parent_values()
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if route_id == "blackwell_gpu":
        cache_root = BLACKWELL_RUNTIME_CACHE_ROOT.resolve()
        cache_root.relative_to((PROJECT_ROOT / "RecoverySprint" / "runtime_cache").resolve())
        cache_paths = {
            "TORCHINDUCTOR_CACHE_DIR": cache_root / "torchinductor",
            "TRITON_CACHE_DIR": cache_root / "triton",
            "TEMP": cache_root / "temp",
            "TMP": cache_root / "temp",
        }
        for path in cache_paths.values():
            path.resolve().relative_to(cache_root)
            path.mkdir(parents=True, exist_ok=True)
        env.update(
            {
                **{key: str(path.resolve()) for key, path in cache_paths.items()},
                "CUDA_VISIBLE_DEVICES": "0",
                "KIRA_BLACKWELL_VOICE_EXPERIMENT": "1",
                "KIRA_APPROVED_GPU_VOICE_PRODUCTION": "1",
            }
        )
    else:
        env.update(
            {
                "CUDA_VISIBLE_DEVICES": "",
                "KIRA_CHATTERBOX_SIDECAR_CHILD": "1",
            }
        )
    return env


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _blackwell_self_check_cache_key(
    route: dict[str, Any],
    child_environment: dict[str, str],
) -> str:
    """Bind a session cache entry to every accepted readiness dependency.

    Only the digest leaves this function.  In particular, user/profile paths
    inherited by the restricted child environment are not copied into audit
    output.  Any artifact or environment change creates a new key and forces a
    fresh worker self-check.
    """
    if str(route.get("route_id") or "") != "blackwell_gpu" or route.get("valid") is not True:
        raise ValueError("only a valid Blackwell route is self-check-cache eligible")
    paths = route.get("resolved") if isinstance(route.get("resolved"), dict) else {}
    config = route.get("sidecar_config") if isinstance(route.get("sidecar_config"), dict) else {}

    required_paths = {
        "routing": KIRA_APPROVED_VOICE_ROUTING_CONFIG,
        "config": Path(paths["config"]),
        "worker": Path(paths["worker"]),
        "python": Path(paths["python"]),
        "profile": _project_path(config.get("approved_profile")),
        "reference": _project_path(config.get("approved_reference")),
    }
    artifact_hashes: dict[str, str] = {}
    for name, path in required_paths.items():
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Blackwell self-check cache artifact missing: {name}")
        artifact_hashes[name] = _sha256_file(resolved)

    # These files are independently verified inside the sealed worker.  Their
    # current hashes are included too, so changing one cannot reuse an earlier
    # successful self-check merely because its expected hash remains in the
    # sidecar config.
    sealed_artifact_hashes: dict[str, str] = {}
    for key in ("shared_worker", "dependency_manifest", "gpu_readiness"):
        if not config.get(key):
            raise ValueError(f"Blackwell self-check cache contract missing {key}")
        path = _project_path(config[key])
        if not path.is_file():
            raise FileNotFoundError(f"Blackwell self-check sealed artifact missing: {key}")
        sealed_artifact_hashes[key] = _sha256_file(path)

    environment_sha256 = _canonical_sha256(
        {str(key): str(value) for key, value in sorted(child_environment.items())}
    )
    contract = {
        "cache_key_schema": 1,
        "route": {
            key: route.get(key)
            for key in (
                "route_id",
                "role",
                "compute_device",
                "environment_profile",
                "config_sha256",
                "worker_sha256",
                "standalone_acceptance_sha256",
                "serialized_acceptance_sha256",
            )
        },
        "artifact_sha256": artifact_hashes,
        "sealed_artifact_sha256": sealed_artifact_hashes,
        "approved_identity": {
            "profile_sha256": KIRA_APPROVED_PROFILE_SHA256,
            "reference_sha256": KIRA_APPROVED_REFERENCE_SHA256,
        },
        "runtime_contract": {
            key: config.get(key)
            for key in (
                "sidecar_id",
                "python_version",
                "chatterbox_version",
                "torch_version",
                "torchaudio_version",
                "cuda_runtime",
                "required_device_name",
                "required_device_capability",
                "required_compiled_architecture",
                "compute_device",
                "input_channel",
                "playback",
                "offline_cache_only",
                "generic_voice_fallback_allowed",
                "production_routing_authorized",
                "production_role",
            )
        },
        "restricted_child_environment_sha256": environment_sha256,
    }
    return _canonical_sha256(contract)


def _self_check_cache_audit(status: str, key_sha256: str | None) -> dict[str, Any]:
    return {
        "scope": "current_python_process",
        "route": "blackwell_gpu",
        "status": status,
        "key_sha256": key_sha256,
        "successful_results_only": True,
        "synthesis_cached": False,
        "qwen_absence_cached": False,
        "cpu_route_cached": False,
        "generic_voice_authorized": False,
    }


def _safe_blackwell_self_check_cache_evidence(raw: Any) -> dict[str, str]:
    """Project cache audit fields to a repeatable, non-private flat shape."""
    audit = raw if isinstance(raw, dict) else {}
    status = str(audit.get("status") or "").strip()
    scope = str(audit.get("scope") or "").strip()
    key_sha256 = str(audit.get("key_sha256") or "").strip().casefold()
    evidence: dict[str, str] = {}
    if status in {
        "hit",
        "miss_stored",
        "miss_not_stored",
        "bypassed_key_contract_error",
    }:
        evidence["blackwell_self_check_cache_status"] = status
    if scope == "current_python_process":
        evidence["blackwell_self_check_cache_scope"] = scope
    if re.fullmatch(r"[0-9a-f]{64}", key_sha256):
        evidence["blackwell_self_check_cache_key_sha256"] = key_sha256
    return evidence


def _qwen_residency_evidence(timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Read exact local residency without loading or unloading any model."""
    try:
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
        with opener.open(
            urllib_request.Request(KIRA_QWEN_PS_ENDPOINT, method="GET"),
            timeout=max(0.2, min(5.0, float(timeout_seconds))),
        ) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Ollama /api/ps response exceeded 1 MiB")
        payload = json.loads(raw.decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise ValueError("Ollama /api/ps did not return a models list")
        qwen_records: list[dict[str, Any]] = []
        for index, item in enumerate(models):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Ollama /api/ps model record {index} was not an object"
                )
            for field in ("name", "model", "digest"):
                if not isinstance(item.get(field), str):
                    raise ValueError(
                        f"Ollama /api/ps model record {index} has invalid {field}"
                    )
            name = item["name"].strip()
            model = item["model"].strip()
            digest = item["digest"].strip().casefold()
            if not name and not model:
                raise ValueError(
                    f"Ollama /api/ps model record {index} has no identity"
                )
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError(
                    f"Ollama /api/ps model record {index} has invalid digest"
                )
            identity = f"{name} {model}".casefold()
            if "qwen" in identity or digest == KIRA_QWEN_DIGEST:
                qwen_records.append({"name": name, "model": model, "digest": digest})
        return {
            "query_succeeded": True,
            "qwen_absent_proven": not qwen_records,
            "qwen_records": qwen_records,
            "endpoint": KIRA_QWEN_PS_ENDPOINT,
            "model_state_changed": False,
        }
    except Exception as exc:
        return {
            "query_succeeded": False,
            "qwen_absent_proven": False,
            "qwen_records": [],
            "endpoint": KIRA_QWEN_PS_ENDPOINT,
            "reason": "qwen_residency_query_failed_gpu_blocked",
            "error": f"{type(exc).__name__}: {exc}",
            "model_state_changed": False,
        }


def wait_for_exact_qwen_absence(
    *,
    timeout_seconds: float = EXACT_QWEN_ABSENCE_WAIT_SECONDS,
    poll_interval_seconds: float = 0.1,
) -> dict[str, Any]:
    """Boundedly prove exact Qwen absence using read-only ``/api/ps`` checks."""

    try:
        bound = max(0.0, min(60.0, float(timeout_seconds)))
    except (TypeError, ValueError):
        bound = EXACT_QWEN_ABSENCE_WAIT_SECONDS
    try:
        interval = max(0.01, min(1.0, float(poll_interval_seconds)))
    except (TypeError, ValueError):
        interval = 0.1
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    last: dict[str, Any] = {}
    while True:
        last = _qwen_residency_evidence(
            timeout_seconds=max(0.2, min(2.0, bound or 0.2))
        )
        records = last.get("qwen_records") if isinstance(last, dict) else None
        evidence_shape_valid = bool(
            isinstance(last, dict)
            and isinstance(records, list)
            and last.get("model_state_changed") is False
            and last.get("endpoint") == KIRA_QWEN_PS_ENDPOINT
        )
        attempts.append(
            {
                "query_succeeded": last.get("query_succeeded") is True,
                "qwen_absent_proven": last.get("qwen_absent_proven") is True,
                "evidence_shape_valid": evidence_shape_valid,
                "qwen_record_count": len(records) if isinstance(records, list) else None,
                "reason": str(last.get("reason") or ""),
            }
        )
        if (
            evidence_shape_valid
            and last.get("query_succeeded") is True
            and last.get("qwen_absent_proven") is True
            and not records
        ):
            return {
                "qwen_absent_proven": True,
                "query_succeeded": True,
                "reason": "exact_qwen_absence_proven",
                "attempt_count": len(attempts),
                "duration_seconds": round(time.monotonic() - started, 6),
                "bounded_wait_seconds": bound,
                "last_evidence": last,
                "attempts": attempts,
                "model_state_changed": False,
            }
        elapsed = time.monotonic() - started
        if elapsed >= bound:
            return {
                "qwen_absent_proven": False,
                "query_succeeded": last.get("query_succeeded") is True,
                "reason": "exact_qwen_absence_not_proven_within_bound",
                "attempt_count": len(attempts),
                "duration_seconds": round(elapsed, 6),
                "bounded_wait_seconds": bound,
                "last_evidence": last,
                "attempts": attempts,
                "model_state_changed": False,
            }
        time.sleep(min(interval, max(0.0, bound - elapsed)))


def suspend_persistent_blackwell_voice_for_exact_qwen(
    reason: str = "before_exact_qwen_text_generation",
    *,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Release exact voice-model residency without discarding the v2 session."""

    started = time.perf_counter()
    selected = _selected_persistent_blackwell_voice_version()
    if selected != "v2":
        return {
            "ready_for_text_generation": False,
            "voice_model_absence_proven": False,
            "reason": "persistent_blackwell_v2_not_selected",
            "selected_candidate_version": selected,
            "playback": False,
            "generated_audio": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
        }

    unselected_cleanup = _release_unselected_persistent_blackwell_voice("v2")
    with _CHATTERBOX_LOCK:
        in_process_model_was_present = _CHATTERBOX_MODEL is not None
        if in_process_model_was_present:
            _cancel_chatterbox_idle_timer_locked()
            _release_chatterbox_model_locked()
        in_process_model_absent = _CHATTERBOX_MODEL is None

    before = _persistent_blackwell_voice_status_v2()
    owner_before = str(before.get("session_owner") or "")
    generation_before = before.get("session_generation")
    generation_before_valid = bool(
        isinstance(generation_before, int)
        and not isinstance(generation_before, bool)
        and generation_before >= 0
    )
    owned_state_present = bool(
        owner_before
        or before.get("owned_worker_running")
        or before.get("model_loaded")
        or before.get("host_last_known_model_loaded")
    )
    if owner_before and generation_before_valid:
        suspend_result = _suspend_persistent_blackwell_voice_v2_if_owner(
            owner_before,
            reason,
            expected_generation=generation_before,
            timeout_seconds=timeout_seconds,
        )
    elif owner_before:
        suspend_result = {
            "suspended": False,
            "ready_for_text_generation": False,
            "model_release_proven": False,
            "owner_matched": True,
            "generation_matched": False,
            "reason": "persistent_blackwell_v2_owner_generation_not_proven",
        }
    elif owned_state_present:
        suspend_result = {
            "suspended": False,
            "ready_for_text_generation": False,
            "model_release_proven": False,
            "owner_matched": False,
            "reason": "persistent_blackwell_v2_owned_state_has_no_owner",
        }
    else:
        suspend_result = {
            "suspended": True,
            "ready_for_text_generation": True,
            "model_release_proven": True,
            "owner_matched": True,
            "reason": "persistent_blackwell_v2_has_no_owned_state",
            "session_owner_preserved": True,
            "owned_worker_preserved": False,
        }
    after = _persistent_blackwell_voice_status_v2()
    owner_after = str(after.get("session_owner") or "")
    generation_after = after.get("session_generation")
    owner_preserved = owner_after == owner_before
    generation_preserved = generation_after == generation_before
    session_preserved = owner_preserved and generation_preserved
    v2_model_absent = bool(
        after.get("model_loaded") is False
        and after.get("host_last_known_model_loaded") is False
    )
    cleanup_proven = (
        unselected_cleanup.get("all_unselected_owned_workers_closed") is True
    )
    ready = bool(
        cleanup_proven
        and in_process_model_absent
        and suspend_result.get("ready_for_text_generation") is True
        and suspend_result.get("model_release_proven") is True
        and session_preserved
        and v2_model_absent
    )
    return {
        "ready_for_text_generation": ready,
        "voice_model_absence_proven": ready,
        "reason": (
            "exact_qwen_voice_resources_suspended"
            if ready
            else "exact_qwen_voice_resource_release_not_proven"
        ),
        "selected_candidate_version": "v2",
        "requested_reason": reason,
        "unselected_candidate_cleanup": unselected_cleanup,
        "in_process_model_was_present": in_process_model_was_present,
        "in_process_model_absent": in_process_model_absent,
        "session_owner_was_present": bool(owner_before),
        "session_owner_preserved": owner_preserved,
        "session_generation_before": generation_before,
        "session_generation_after": generation_after,
        "session_generation_preserved": generation_preserved,
        "owned_worker_was_running": before.get("owned_worker_running") is True,
        "owned_worker_running_after": after.get("owned_worker_running") is True,
        "owned_worker_preserved": suspend_result.get("owned_worker_preserved") is True,
        "v2_model_absent_after": v2_model_absent,
        "suspend": suspend_result,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "arbitrary_model_unload_performed": False,
        "arbitrary_process_termination_performed": False,
        "playback": False,
        "generated_audio": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
    }


def _parse_chatterbox_sidecar_result(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = str(completed.stdout or "")
    if len(stdout.encode("utf-8")) > MAX_CHATTERBOX_SIDECAR_RESPONSE_BYTES:
        return {"generated": False, "reason": "chatterbox_sidecar_response_oversized", "playback": False}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {
            "generated": False,
            "reason": "chatterbox_sidecar_malformed_response",
            "error": str(exc),
            "stderr": str(completed.stderr or "")[-2000:],
            "playback": False,
        }
    if not isinstance(payload, dict):
        return {"generated": False, "reason": "chatterbox_sidecar_non_object_response", "playback": False}
    if completed.returncode != 0 and payload.get("reason") == "ok":
        return {"generated": False, "reason": "chatterbox_sidecar_exit_mismatch", "playback": False}
    return dict(payload)


def _check_kira_chatterbox_sidecar(cfg: VoiceOutputConfig) -> dict[str, Any]:
    if not _is_exact_kira_approved_reference(cfg):
        return {"ready": False, "reason": "not_exact_approved_kira_reference", "playback": False}
    routing = _load_approved_voice_routing_config()
    if routing.get("valid") is not True:
        return {
            "ready": False,
            "reason": routing.get("reason", "approved_voice_routing_unavailable"),
            "issues": routing.get("issues") or [],
            "playback": False,
            "generic_voice_used": False,
        }
    residency = _qwen_residency_evidence()
    attempts: list[dict[str, Any]] = []
    for route in routing.get("routes") or []:
        route_id = str(route.get("route_id") or "")
        attempt: dict[str, Any] = {
            "route_id": route_id,
            "role": route.get("role"),
            "approved": True,
        }
        if route.get("valid") is not True:
            attempt.update({"status": "route_contract_failed", "issues": route.get("issues") or []})
            attempts.append(attempt)
            continue
        if route_id == "blackwell_gpu":
            if str(os.environ.get("KIRA_DISABLE_BLACKWELL_GPU_VOICE", "")).strip().casefold() in {
                "1", "true", "yes", "on"
            }:
                attempt.update({"status": "blocked", "reason": "gpu_route_operator_disabled"})
                attempts.append(attempt)
                continue
            if residency.get("qwen_absent_proven") is not True:
                attempt.update({"status": "blocked", "reason": "qwen_absence_not_proven"})
                attempts.append(attempt)
                continue
        elif str(os.environ.get("KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR", "")).strip().casefold() in {
            "1", "true", "yes", "on"
        }:
            attempt.update({"status": "blocked", "reason": "cpu_route_operator_disabled"})
            attempts.append(attempt)
            continue
        checked = _run_approved_sidecar_self_check(route)
        attempt.update(
            {
                "status": "ready" if checked.get("ready") is True else "self_check_failed",
                "reason": checked.get("reason"),
                "self_check": checked,
            }
        )
        if route_id == "blackwell_gpu" and checked.get("ready") is True:
            post_check_residency = _qwen_residency_evidence()
            residency["after_gpu_self_check"] = post_check_residency
            if post_check_residency.get("qwen_absent_proven") is not True:
                attempt.update(
                    {
                        "status": "blocked",
                        "reason": "qwen_absence_not_proven_after_gpu_self_check",
                    }
                )
        attempts.append(attempt)
        if attempt.get("status") == "ready":
            return {
                **checked,
                "ready": True,
                "route_id": route_id,
                "approved_voice_path_used": route_id,
                "attempted_approved_paths": attempts,
                "qwen_residency": residency,
                "routing_config_sha256": routing.get("routing_config_sha256"),
                "generic_voice_used": False,
                "playback": False,
            }
    return {
        "ready": False,
        "reason": "no_approved_kira_voice_route_ready",
        "attempted_approved_paths": attempts,
        "approved_voice_path_used": None,
        "qwen_residency": residency,
        "routing_config_sha256": routing.get("routing_config_sha256"),
        "generic_voice_used": False,
        "playback": False,
    }


def _run_approved_sidecar_self_check_uncached(
    route: dict[str, Any],
    child_environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    route_id = str(route.get("route_id") or "")
    if route.get("valid") is not True:
        return {
            "ready": False,
            "reason": "approved_route_contract_failed",
            "route_id": route_id,
            "issues": route.get("issues") or [],
            "playback": False,
        }
    paths = route.get("resolved") if isinstance(route.get("resolved"), dict) else {}
    try:
        completed = subprocess.run(
            [str(paths["python"]), str(paths["worker"]), "--self-check"],
            cwd=str(PROJECT_ROOT),
            env=(
                dict(child_environment)
                if child_environment is not None
                else _chatterbox_sidecar_environment(route)
            ),
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (KeyError, OSError, subprocess.SubprocessError) as exc:
        return {
            "ready": False,
            "reason": "approved_sidecar_self_check_process_error",
            "route_id": route_id,
            "error": f"{type(exc).__name__}: {exc}",
            "playback": False,
        }
    result = _parse_chatterbox_sidecar_result(completed)
    issues: list[str] = []
    config = route.get("sidecar_config") or {}
    if completed.returncode != 0 or result.get("ready") is not True:
        issues.append("sidecar_not_ready")
    if result.get("sidecar_id") != config.get("sidecar_id"):
        issues.append("sidecar_identity_mismatch")
    if result.get("reference_sha256") != KIRA_APPROVED_REFERENCE_SHA256:
        issues.append("approved_reference_binding_failed")
    if result.get("playback") is not False or result.get("model_loaded") is not False:
        issues.append("self_check_side_effect_contract_failed")
    if route_id == "blackwell_gpu" and not all((result.get("runtime_cuda_checks") or {}).values()):
        issues.append("blackwell_cuda_self_check_failed")
    if issues:
        return {
            "ready": False,
            "reason": "approved_sidecar_self_check_contract_failed",
            "route_id": route_id,
            "issues": issues,
            "sidecar_result": result,
            "stderr": str(completed.stderr or "")[-2000:],
            "playback": False,
        }
    return {
        **result,
        "ready": True,
        "reason": "approved_sidecar_ready",
        "route_id": route_id,
        "environment_profile": route.get("environment_profile"),
        "worker_reported_legacy_production_preferred": result.get("production_preferred"),
        "production_preferred": route_id == "blackwell_gpu",
        "automatic_approved_fallback_only": route_id == "sealed_cpu",
        "playback": False,
    }


def _run_approved_sidecar_self_check(route: dict[str, Any]) -> dict[str, Any]:
    """Run or reuse one exact, successful, process-session Blackwell check."""
    route_id = str(route.get("route_id") or "")
    if route_id != "blackwell_gpu" or route.get("valid") is not True:
        return _run_approved_sidecar_self_check_uncached(route)

    try:
        child_environment = _chatterbox_sidecar_environment(route)
        key_sha256 = _blackwell_self_check_cache_key(route, child_environment)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        result = _run_approved_sidecar_self_check_uncached(route)
        result["self_check_cache"] = {
            **_self_check_cache_audit("bypassed_key_contract_error", None),
            "error": f"{type(exc).__name__}: {exc}",
        }
        return result

    # Keep the lock through a miss so two queue workers cannot both launch the
    # same one-shot preflight.  The cached object never contains caller-added
    # routing evidence and every return is a deep copy.
    with _APPROVED_SIDECAR_SELF_CHECK_CACHE_LOCK:
        cached = _APPROVED_SIDECAR_SELF_CHECK_CACHE.get(key_sha256)
        if cached is not None:
            result = copy.deepcopy(cached)
            result["self_check_cache"] = _self_check_cache_audit("hit", key_sha256)
            return result

        result = _run_approved_sidecar_self_check_uncached(route, child_environment)
        cache_status = "miss_not_stored"
        if result.get("ready") is True:
            _APPROVED_SIDECAR_SELF_CHECK_CACHE[key_sha256] = copy.deepcopy(result)
            cache_status = "miss_stored"
        result["self_check_cache"] = _self_check_cache_audit(cache_status, key_sha256)
        return result


def _synthesize_with_approved_sidecar(
    text: str,
    target: Path,
    cfg: VoiceOutputConfig,
    route: dict[str, Any],
) -> dict[str, Any]:
    route_id = str(route.get("route_id") or "")
    if route.get("valid") is not True:
        return {
            "generated": False,
            "reason": "approved_route_contract_failed",
            "route_id": route_id,
            "issues": route.get("issues") or [],
            "engine": "chatterbox_tts",
            "playback": False,
        }
    try:
        resolved_target = target.resolve()
        output_relative = resolved_target.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return {
            "generated": False,
            "reason": "chatterbox_sidecar_output_not_project_owned",
            "route_id": route_id,
            "engine": "chatterbox_tts",
            "playback": False,
        }
    request_id = str(uuid.uuid4())
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    payload = {
        "schema_version": 1,
        "request_id": request_id,
        "channel": "public_spoken_only",
        "text": text,
        "text_sha256": text_hash,
        "reference_sha256": KIRA_APPROVED_REFERENCE_SHA256,
        "output_relative": output_relative,
        "pcm_output_gain_db": float(cfg.pcm_output_gain_db),
        "proximity_cut_hz": float(cfg.proximity_cut_hz),
        "proximity_cut_mix": float(cfg.proximity_cut_mix),
    }
    try:
        timeout = max(
            120,
            min(1800, int(os.environ.get("KIRA_CHATTERBOX_SIDECAR_TIMEOUT_SECONDS", "900"))),
        )
    except (TypeError, ValueError):
        timeout = 900
    paths = route.get("resolved") if isinstance(route.get("resolved"), dict) else {}
    try:
        completed = subprocess.run(
            [str(paths["python"]), str(paths["worker"])],
            cwd=str(PROJECT_ROOT),
            env=_chatterbox_sidecar_environment(route),
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "generated": False,
            "reason": "approved_sidecar_timeout",
            "route_id": route_id,
            "engine": "chatterbox_tts",
            "error": str(exc),
            "playback": False,
        }
    except (KeyError, OSError, subprocess.SubprocessError) as exc:
        return {
            "generated": False,
            "reason": "approved_sidecar_process_error",
            "route_id": route_id,
            "engine": "chatterbox_tts",
            "error": f"{type(exc).__name__}: {exc}",
            "playback": False,
        }
    result = _parse_chatterbox_sidecar_result(completed)
    violations: list[str] = []
    if completed.returncode != 0 or result.get("generated") is not True:
        violations.append("sidecar_did_not_generate")
    if result.get("engine") != "chatterbox_tts":
        violations.append("approved_engine_mismatch")
    if result.get("request_id") != request_id:
        violations.append("request_id_mismatch")
    if result.get("text_sha256") != text_hash or result.get("requested_text_bound") is not True:
        violations.append("requested_text_binding_failed")
    if result.get("reference_sha256") != KIRA_APPROVED_REFERENCE_SHA256:
        violations.append("approved_reference_binding_failed")
    if result.get("playback") is not False or result.get("generic_voice_used") is not False:
        violations.append("playback_or_generic_voice_violation")
    if str(result.get("voice_identity_status") or "") != "reviewed_reference_chatterbox":
        violations.append("voice_identity_status_mismatch")
    if result.get("device") != route.get("compute_device"):
        violations.append("compute_device_mismatch")
    if route_id == "blackwell_gpu":
        if (result.get("gpu_proof") or {}).get("actual_gpu_allocation") is not True:
            violations.append("gpu_allocation_not_proven")
        if result.get("gpu_utilization_observed") is not True:
            violations.append("gpu_utilization_not_proven")
        if (result.get("gpu_proof") or {}).get("rejected_warning_matches"):
            violations.append("rejected_gpu_warning")
    try:
        actual_audio = Path(str(result.get("audio_path") or "")).resolve()
    except (OSError, ValueError):
        actual_audio = Path()
    if actual_audio != resolved_target or not resolved_target.is_file():
        violations.append("audio_path_or_file_mismatch")
    if violations:
        return {
            "generated": False,
            "reason": "approved_sidecar_synthesis_contract_failed",
            "route_id": route_id,
            "engine": "chatterbox_tts",
            "issues": violations,
            "sidecar_result": result,
            "stderr": str(completed.stderr or "")[-2000:],
            "playback": False,
        }
    return {
        **result,
        "reason": "ok",
        "engine": "chatterbox_tts",
        "sidecar": True,
        "route_id": route_id,
        "text": text,
        "playback": False,
        "stderr_warning": str(completed.stderr or "")[-2000:] or None,
    }


def _synthesize_with_kira_chatterbox_sidecar(
    text: str,
    target: Path,
    cfg: VoiceOutputConfig,
) -> dict[str, Any]:
    if not _is_exact_kira_approved_reference(cfg):
        return {
            "generated": False,
            "reason": "not_exact_approved_kira_reference",
            "engine": "chatterbox_tts",
            "playback": False,
            "generic_voice_used": False,
        }
    routing = _load_approved_voice_routing_config()
    if routing.get("valid") is not True:
        persistent_cleanup = release_persistent_blackwell_voice(
            "approved_voice_routing_invalid"
        )
        cleanup_proven = persistent_cleanup.get("owned_worker_closed") is True
        return {
            "generated": False,
            "reason": (
                routing.get("reason", "approved_voice_routing_unavailable")
                if cleanup_proven
                else "approved_voice_routing_invalid_and_persistent_cleanup_unproven"
            ),
            "engine": "chatterbox_tts",
            "issues": routing.get("issues") or [],
            "approved_voice_path_used": None,
            "attempted_approved_paths": [],
            "persistent_cleanup": persistent_cleanup,
            "persistent_cleanup_proven": cleanup_proven,
            "generic_voice_used": False,
            "playback": False,
        }
    attempts: list[dict[str, Any]] = []
    preferred_failure_reason: str | None = None
    blackwell_self_check_cache_evidence: dict[str, str] = {}
    persistent_active_failure = False
    persistent_gpu_attempted = False
    persistent_route_id = "blackwell_gpu_persistent_candidate"
    persistent_route_role = "preferred_candidate_pending_owner_acceptance"
    selected_persistent_version = _selected_persistent_blackwell_voice_version()
    v2_route_isolation = selected_persistent_version == "v2"
    if v2_route_isolation:
        persistent_route_id = "blackwell_gpu_persistent_candidate_v2"
        persistent_route_role = "preferred_v2_candidate_pending_owner_acceptance"
    persistent_feature_enabled = persistent_blackwell_voice_feature_enabled()
    if not persistent_feature_enabled:
        selection_cleanup = _release_unselected_persistent_blackwell_voice(
            selected_persistent_version
        )
        if selection_cleanup.get("all_unselected_owned_workers_closed") is not True:
            return {
                "generated": False,
                "reason": "unselected_persistent_worker_cleanup_not_proven",
                "engine": "chatterbox_tts",
                "text": text,
                "approved_voice_path_used": None,
                "approved_voice_attempts": [],
                "selection_cleanup": selection_cleanup,
                "gpu_synthesis_attempted": False,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "generic_voice_used": False,
                "playback": False,
            }
    if persistent_feature_enabled:
        persistent_result = synthesize_with_persistent_blackwell_voice(
            text=text,
            target=target,
            pcm_output_gain_db=float(cfg.pcm_output_gain_db),
            proximity_cut_hz=float(cfg.proximity_cut_hz),
            proximity_cut_mix=float(cfg.proximity_cut_mix),
        )
        if persistent_result.get("selected_candidate_version") == "v2":
            persistent_route_id = "blackwell_gpu_persistent_candidate_v2"
            persistent_route_role = "preferred_v2_candidate_pending_owner_acceptance"
        persistent_eligible = persistent_result.get("persistent_route_eligible") is True
        v2_real_sealed_success = bool(
            persistent_result.get("selected_candidate_version") != "v2"
            or (
                persistent_result.get("test_only_injected_client") is False
                and persistent_result.get("route_id")
                == "blackwell_gpu_persistent_candidate_v2_inactive"
                and persistent_result.get("approved_voice_path_used") == "blackwell_gpu"
            )
        )
        if (
            persistent_result.get("generated") is True
            and persistent_eligible
            and v2_real_sealed_success
        ):
            attempt = {
                "route_id": persistent_route_id,
                "role": persistent_route_role,
                "approved": True,
                "status": "used",
                "reason": "ok",
            }
            attempts.append(attempt)
            return {
                **persistent_result,
                "route_id": persistent_route_id,
                "approved_voice_path_used": "blackwell_gpu",
                "approved_voice_attempts": attempts,
                "approved_voice_routing": {
                    "routing_id": routing.get("routing_id"),
                    "routing_config_sha256": routing.get("routing_config_sha256"),
                    "attempted_approved_paths": attempts,
                    "actual_approved_path_used": "blackwell_gpu",
                    "preferred_path": persistent_route_id,
                    "preferred_path_used": True,
                    "automatic_cpu_fallback_used": False,
                    "preferred_failure_reason": None,
                    "qwen_residency": persistent_result.get(
                        "parent_qwen_residency_before_synthesis"
                    ),
                    "generic_voice_fallback_used": False,
                    "sapi_fallback_used": False,
                    "unsealed_in_process_fallback_used": False,
                    "one_shot_gpu_rollback_invoked": False,
                    "arbitrary_model_unload_performed": False,
                },
                "application_route_connected": True,
                "production_route_promoted": False,
                "gpu_synthesis_attempted": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "generic_voice_used": False,
                "playback": False,
            }
        if persistent_result.get("generated") is True:
            # A test-injected or otherwise unbound result may exercise the
            # integration in unit tests, but it can never be relabeled as an
            # approved Kira voice route and can never fall through.
            return {
                **persistent_result,
                "generated": False,
                "reason": "persistent_blackwell_unapproved_generated_result_blocked",
                "route_id": persistent_route_id,
                "approved_voice_path_used": None,
                "approved_voice_attempts": [
                    {
                        "route_id": persistent_route_id,
                        "role": persistent_route_role,
                        "approved": False,
                        "status": "blocked",
                        "reason": "unapproved_generated_result",
                    }
                ],
                "application_route_connected": True,
                "production_route_promoted": False,
                "gpu_synthesis_attempted": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "generic_voice_used": False,
                "playback": False,
                "route_blocked": True,
                "fallback_allowed": False,
            }
        persistent_cancelled = persistent_result.get("cancelled") is True
        persistent_route_blocked = persistent_result.get("route_blocked") is True
        persistent_candidate_attempted = persistent_result.get("candidate_attempted") is True
        persistent_gpu_attempted = persistent_candidate_attempted
        persistent_fallback_allowed = persistent_result.get("fallback_allowed") is True
        if persistent_cancelled or persistent_route_blocked or (
            persistent_candidate_attempted and not persistent_fallback_allowed
        ):
            block_reason = str(
                persistent_result.get("reason")
                or "persistent_blackwell_v2_route_blocked"
            )
            attempts.append(
                {
                    "route_id": persistent_route_id,
                    "role": persistent_route_role,
                    "approved": True,
                    "status": "cancelled" if persistent_cancelled else "blocked",
                    "reason": block_reason,
                }
            )
            return {
                **persistent_result,
                "generated": False,
                "reason": block_reason,
                "engine": "chatterbox_tts",
                "text": text,
                "approved_voice_path_used": None,
                "approved_voice_attempts": attempts,
                "preferred_failure_reason": block_reason,
                "application_route_connected": True,
                "production_route_promoted": False,
                "gpu_synthesis_attempted": persistent_candidate_attempted,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
                "generic_voice_used": False,
                "playback": False,
            }
        if persistent_eligible:
            persistent_active_failure = True
            preferred_failure_reason = str(
                persistent_result.get("reason") or "persistent_gpu_candidate_failed"
            )
            cleanup = persistent_result.get("owned_worker_cleanup")
            cleanup = cleanup if isinstance(cleanup, dict) else {}
            attempts.append(
                {
                    "route_id": persistent_route_id,
                    "role": persistent_route_role,
                    "approved": True,
                    "status": "synthesis_failed",
                    "reason": preferred_failure_reason,
                }
            )
            # A sealed CPU fallback is safe only after the exact session-owned
            # GPU child is gone. Never scan for or terminate another process.
            if cleanup.get("owned_worker_closed") is not True:
                return {
                    "generated": False,
                    "reason": "persistent_blackwell_owned_worker_cleanup_not_proven",
                    "engine": "chatterbox_tts",
                    "text": text,
                    "approved_voice_path_used": None,
                    "approved_voice_attempts": attempts,
                    "preferred_failure_reason": preferred_failure_reason,
                    "gpu_synthesis_attempted": True,
                    "cpu_synthesis_attempted": False,
                    "automatic_cpu_fallback_used": False,
                    "generic_voice_used": False,
                    "playback": False,
                }
        elif v2_route_isolation:
            # Selecting v2 is an exclusive GPU-route decision for this
            # request. A pre-attempt failure (for example, no owned session or
            # an acceptance-binding failure) may use only the sealed CPU route,
            # and only when v2 explicitly proves that the exact owned worker is
            # closed and no target cleanup debt remains. Missing cleanup
            # evidence is not proof of absence. This path must never fall
            # through to the one-shot Blackwell rollback route.
            cleanup = persistent_result.get("owned_worker_cleanup")
            cleanup = cleanup if isinstance(cleanup, dict) else {}
            cleanup_proven = cleanup.get("owned_worker_closed") is True
            target_cleanup_proven = (
                persistent_result.get("target_cleanup_proven") is True
            )
            sealed_cpu_fallback_safe = bool(
                persistent_fallback_allowed
                and not persistent_cancelled
                and not persistent_route_blocked
                and cleanup_proven
                and target_cleanup_proven
            )
            preferred_failure_reason = str(
                persistent_result.get("reason")
                or "persistent_blackwell_v2_pre_attempt_failed"
            )
            attempts.append(
                {
                    "route_id": persistent_route_id,
                    "role": persistent_route_role,
                    "approved": True,
                    "status": (
                        "pre_attempt_failed_cpu_fallback_only"
                        if sealed_cpu_fallback_safe
                        else "pre_attempt_failed_blocked"
                    ),
                    "reason": preferred_failure_reason,
                }
            )
            if not sealed_cpu_fallback_safe:
                return {
                    **persistent_result,
                    "generated": False,
                    "reason": "persistent_blackwell_v2_fallback_contract_not_proven",
                    "engine": "chatterbox_tts",
                    "text": text,
                    "approved_voice_path_used": None,
                    "approved_voice_attempts": attempts,
                    "preferred_failure_reason": preferred_failure_reason,
                    "application_route_connected": True,
                    "production_route_promoted": False,
                    "gpu_synthesis_attempted": persistent_gpu_attempted,
                    "cpu_synthesis_attempted": False,
                    "automatic_cpu_fallback_used": False,
                    "generic_voice_used": False,
                    "playback": False,
                    "route_blocked": True,
                    "fallback_allowed": False,
                }
            persistent_active_failure = True

    residency = _qwen_residency_evidence()
    for route in routing.get("routes") or []:
        route_id = str(route.get("route_id") or "")
        attempt: dict[str, Any] = {
            "route_id": route_id,
            "role": route.get("role"),
            "approved": True,
        }
        if route_id == "blackwell_gpu" and (
            persistent_active_failure or v2_route_isolation
        ):
            attempt.update(
                {
                    "status": "rollback_route_not_automatic",
                    "reason": (
                        "persistent_v2_selected_cpu_fallback_only"
                        if v2_route_isolation
                        else "persistent_candidate_active_cpu_fallback_only"
                    ),
                }
            )
            attempts.append(attempt)
            continue
        if route.get("valid") is not True:
            attempt.update({"status": "route_contract_failed", "issues": route.get("issues") or []})
            attempts.append(attempt)
            if route_id == "blackwell_gpu":
                preferred_failure_reason = "gpu_route_contract_failed"
            continue
        if route_id == "blackwell_gpu":
            if str(os.environ.get("KIRA_DISABLE_BLACKWELL_GPU_VOICE", "")).strip().casefold() in {
                "1", "true", "yes", "on"
            }:
                preferred_failure_reason = "gpu_route_operator_disabled"
                attempt.update({"status": "blocked", "reason": preferred_failure_reason})
                attempts.append(attempt)
                continue
            if residency.get("qwen_absent_proven") is not True:
                preferred_failure_reason = "qwen_absence_not_proven"
                attempt.update({"status": "blocked", "reason": preferred_failure_reason})
                attempts.append(attempt)
                continue
        elif str(os.environ.get("KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR", "")).strip().casefold() in {
            "1", "true", "yes", "on"
        }:
            attempt.update({"status": "blocked", "reason": "cpu_route_operator_disabled"})
            attempts.append(attempt)
            continue

        checked = _run_approved_sidecar_self_check(route)
        attempt["self_check"] = checked
        if route_id == "blackwell_gpu":
            blackwell_self_check_cache_evidence = _safe_blackwell_self_check_cache_evidence(
                checked.get("self_check_cache")
            )
        if checked.get("ready") is not True:
            attempt.update({"status": "self_check_failed", "reason": checked.get("reason")})
            attempts.append(attempt)
            if route_id == "blackwell_gpu":
                preferred_failure_reason = "gpu_self_check_failed"
            continue
        if route_id == "blackwell_gpu":
            pre_synthesis_residency = _qwen_residency_evidence()
            residency["before_gpu_synthesis"] = pre_synthesis_residency
            if pre_synthesis_residency.get("qwen_absent_proven") is not True:
                preferred_failure_reason = "qwen_remained_resident_after_gpu_self_check"
                attempt.update(
                    {
                        "status": "blocked",
                        "reason": preferred_failure_reason,
                    }
                )
                attempts.append(attempt)
                continue
        synthesis = _synthesize_with_approved_sidecar(text, target, cfg, route)
        attempt.update(
            {
                "status": "used" if synthesis.get("generated") is True else "synthesis_failed",
                "reason": synthesis.get("reason"),
                "contract_issues": synthesis.get("issues") or [],
            }
        )
        attempts.append(attempt)
        if synthesis.get("generated") is True:
            routing_evidence = {
                "routing_id": routing.get("routing_id"),
                "routing_config_sha256": routing.get("routing_config_sha256"),
                "attempted_approved_paths": attempts,
                "actual_approved_path_used": route_id,
                "preferred_path": (
                    persistent_route_id
                    if persistent_active_failure or v2_route_isolation
                    else "blackwell_gpu"
                ),
                "preferred_path_used": route_id == "blackwell_gpu",
                "automatic_cpu_fallback_used": route_id == "sealed_cpu",
                "preferred_failure_reason": preferred_failure_reason,
                "qwen_residency": residency,
                "generic_voice_fallback_used": False,
                "sapi_fallback_used": False,
                "unsealed_in_process_fallback_used": False,
                "one_shot_gpu_rollback_invoked": not (
                    persistent_active_failure or v2_route_isolation
                ),
                "arbitrary_model_unload_performed": False,
            }
            return {
                **synthesis,
                **blackwell_self_check_cache_evidence,
                "approved_voice_path_used": route_id,
                "approved_voice_attempts": attempts,
                "approved_voice_routing": routing_evidence,
                "gpu_synthesis_attempted": bool(
                    persistent_gpu_attempted
                    or (persistent_active_failure and not v2_route_isolation)
                    or route_id == "blackwell_gpu"
                ),
                "cpu_synthesis_attempted": route_id == "sealed_cpu",
                "automatic_cpu_fallback_used": route_id == "sealed_cpu",
                "generic_voice_used": False,
                "playback": False,
            }
        if route_id == "blackwell_gpu":
            preferred_failure_reason = "gpu_synthesis_or_contract_failed"

    return {
        "generated": False,
        "reason": "all_approved_kira_voice_routes_failed",
        "engine": "chatterbox_tts",
        "text": text,
        **blackwell_self_check_cache_evidence,
        "approved_voice_path_used": None,
        "approved_voice_attempts": attempts,
        "approved_voice_routing": {
            "routing_id": routing.get("routing_id"),
            "routing_config_sha256": routing.get("routing_config_sha256"),
            "attempted_approved_paths": attempts,
            "actual_approved_path_used": None,
            "preferred_path": (
                persistent_route_id
                if persistent_active_failure or v2_route_isolation
                else "blackwell_gpu"
            ),
            "preferred_path_used": False,
            "automatic_cpu_fallback_used": False,
            "preferred_failure_reason": preferred_failure_reason,
            "qwen_residency": residency,
            "generic_voice_fallback_used": False,
            "sapi_fallback_used": False,
            "unsealed_in_process_fallback_used": False,
            "one_shot_gpu_rollback_invoked": not (
                persistent_active_failure or v2_route_isolation
            ),
            "arbitrary_model_unload_performed": False,
        },
        "gpu_synthesis_attempted": bool(
            persistent_gpu_attempted
            or (persistent_active_failure and not v2_route_isolation)
            or any(
                item.get("route_id") == "blackwell_gpu"
                and item.get("status") in {"used", "synthesis_failed"}
                for item in attempts
            )
        ),
        "cpu_synthesis_attempted": any(
            item.get("route_id") == "sealed_cpu"
            and item.get("status") in {"used", "synthesis_failed"}
            for item in attempts
        ),
        "automatic_cpu_fallback_used": False,
        "generic_voice_used": False,
        "playback": False,
    }


def warm_voice_output(
    config: VoiceOutputConfig | None = None,
    *,
    session_owner: str = "",
) -> dict[str, Any]:
    """Load the configured Chatterbox model without generating or playing audio.

    World launchers can call this in a background thread so the first spoken
    reply does not also pay the model-load cost.  The normal idle timer still
    owns eventual release, and this function never opens an audio device.
    """
    cfg = config or load_voice_config()
    if not cfg.enabled:
        return {"warmed": False, "reason": "voice_output_disabled", "playback": False, "generated_audio": False}
    if cfg.dry_run:
        return {"warmed": False, "reason": "dry_run", "playback": False, "generated_audio": False}
    if cfg.engine != "chatterbox_tts":
        return {"warmed": False, "reason": "engine_does_not_require_prewarm", "engine": cfg.engine, "playback": False, "generated_audio": False}
    if _is_exact_kira_approved_reference(cfg):
        persistent_status = persistent_blackwell_voice_status()
        persistent_owner = str(session_owner or persistent_status.get("session_owner") or "").strip()
        if exact_qwen_persistent_v2_resource_serialization_required():
            return {
                "warmed": False,
                "ready": True,
                "reason": "activation_prewarm_disabled_for_exact_qwen_resource_serialization",
                "engine": "chatterbox_tts",
                "sidecar": True,
                "sidecar_lifecycle": "session_owned_persistent_candidate_v2_lazy_load",
                "selected_candidate_version": "v2",
                "resource_serialization_required": True,
                "activation_prewarm_disabled": True,
                "lazy_prewarm_before_synthesis": True,
                "session_owner": persistent_owner,
                "session_owner_preserved": bool(persistent_owner),
                "owned_worker_running": bool(
                    persistent_status.get("owned_worker_running")
                ),
                "model_loaded": bool(persistent_status.get("model_loaded")),
                "application_route_connected": True,
                "production_route_promoted": False,
                "playback": False,
                "generated_audio": False,
                "generic_voice_used": False,
                "sapi_voice_used": False,
            }
        if persistent_blackwell_voice_feature_enabled() and persistent_owner:
            result = prewarm_persistent_blackwell_voice(persistent_owner)
            return {
                **result,
                "engine": "chatterbox_tts",
                "sidecar": True,
                "sidecar_lifecycle": str(
                    result.get("sidecar_lifecycle")
                    or (
                        "session_owned_persistent_candidate_v2"
                        if result.get("selected_candidate_version") == "v2"
                        else "session_owned_persistent_candidate"
                    )
                ),
                "application_route_connected": True,
                "production_route_promoted": False,
                "playback": False,
                "generated_audio": False,
            }
        check = _check_kira_chatterbox_sidecar(cfg)
        return {
            **check,
            "warmed": False,
            "ready": check.get("ready") is True,
            "reason": "stateless_sidecar_ready" if check.get("ready") is True else check.get("reason", "sealed_sidecar_unavailable"),
            "engine": "chatterbox_tts",
            "sidecar": True,
            "playback": False,
            "generated_audio": False,
        }

    started = time.perf_counter()
    try:
        import torch
        from chatterbox.tts import ChatterboxTTS
    except Exception as exc:
        return {
            "warmed": False,
            "reason": "chatterbox_import_error",
            "engine": "chatterbox_tts",
            "error": str(exc),
            "playback": False,
            "generated_audio": False,
        }

    device = _resolve_chatterbox_device(cfg, torch)
    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    loaded_now = False
    try:
        with _CHATTERBOX_LOCK:
            _cancel_chatterbox_idle_timer_locked()
            if _CHATTERBOX_MODEL is None or _CHATTERBOX_DEVICE != device:
                if _CHATTERBOX_MODEL is not None:
                    _release_chatterbox_model_locked()
                _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device=device)
                _CHATTERBOX_DEVICE = device
                loaded_now = True
            _schedule_chatterbox_idle_unload_locked()
    except Exception as exc:
        if str(cfg.chatterbox_device or "").strip().lower() == "auto" and device == "cuda":
            release_voice_output()
            fallback = warm_voice_output(replace(cfg, chatterbox_device="cpu"))
            return {
                **fallback,
                "auto_device_fallback": "cpu_after_cuda_prewarm_error",
                "cuda_error": str(exc),
            }
        return {
            "warmed": False,
            "reason": "chatterbox_prewarm_error",
            "engine": "chatterbox_tts",
            "device": device,
            "error": str(exc),
            "duration_seconds": round(time.perf_counter() - started, 3),
            "playback": False,
            "generated_audio": False,
        }
    return {
        "warmed": True,
        "reason": "model_loaded" if loaded_now else "model_already_warm",
        "engine": "chatterbox_tts",
        "device": device,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "playback": False,
        "generated_audio": False,
    }


def release_voice_output(reason: str = "voice_output_release") -> dict[str, Any]:
    """Release a cached voice model without generating or playing audio."""
    release_started = time.perf_counter()
    phase_timings: dict[str, float] = {}
    status_started = time.perf_counter()
    persistent_before = persistent_blackwell_voice_status()
    phase_timings["persistent_status_before_seconds"] = round(
        time.perf_counter() - status_started, 6
    )
    persistent_present = bool(
        persistent_before.get("any_owned_session_owner")
        or persistent_before.get("any_owned_worker_running")
        or persistent_before.get("any_model_loaded")
        or any(
            isinstance(item, dict) and item.get("owned_state_present") is True
            for item in (persistent_before.get("candidate_versions") or {}).values()
        )
    )
    persistent_release_started = time.perf_counter()
    persistent_release = release_persistent_blackwell_voice(reason) if persistent_present else None
    phase_timings["persistent_release_seconds"] = round(
        time.perf_counter() - persistent_release_started, 6
    )
    status_after_started = time.perf_counter()
    persistent_after = persistent_blackwell_voice_status()
    phase_timings["persistent_status_after_seconds"] = round(
        time.perf_counter() - status_after_started, 6
    )
    candidate_after = persistent_after.get("candidate_versions")
    persistent_absence_proven = bool(
        isinstance(candidate_after, dict)
        and {"v1", "v2"}.issubset(candidate_after)
        and not persistent_after.get("any_owned_session_owner")
        and persistent_after.get("any_owned_worker_running") is False
        and persistent_after.get("any_model_loaded") is False
        and all(
            isinstance(candidate_after.get(version), dict)
            and candidate_after[version].get("owned_state_present") is False
            and not candidate_after[version].get("session_owner")
            and candidate_after[version].get("owned_worker_running") is False
            and candidate_after[version].get("model_loaded") is False
            for version in ("v1", "v2")
        )
    )
    lock_wait_started = time.perf_counter()
    with _CHATTERBOX_LOCK:
        phase_timings["in_process_lock_wait_seconds"] = round(
            time.perf_counter() - lock_wait_started, 6
        )
        had_model = _CHATTERBOX_MODEL is not None
        device = _CHATTERBOX_DEVICE or ""
        had_idle_timer = _CHATTERBOX_IDLE_TIMER is not None
        timer_started = time.perf_counter()
        _cancel_chatterbox_idle_timer_locked()
        phase_timings["idle_timer_cancel_seconds"] = round(
            time.perf_counter() - timer_started, 6
        )
        in_process_absence_proven = bool(
            _CHATTERBOX_MODEL is None
            and _CHATTERBOX_DEVICE is None
            and _CHATTERBOX_IDLE_TIMER is None
        )
        skip_direct_cleanup = bool(
            persistent_absence_proven and in_process_absence_proven
        )
        if skip_direct_cleanup:
            direct_cleanup = {
                "performed": False,
                "reason": "exact_persistent_and_in_process_absence_proven",
                "model_present_before": had_model,
                "device_before": str(device),
                "idle_timer_present_before": had_idle_timer,
                "total_seconds": 0.0,
            }
        else:
            direct_cleanup = {
                "performed": True,
                "reason": "absence_not_fully_proven_cleanup_required",
                "idle_timer_present_before": had_idle_timer,
                **_release_chatterbox_model_locked(),
            }
        phase_timings["in_process_cleanup_seconds"] = float(
            direct_cleanup.get("total_seconds") or 0.0
        )
    persistent_model_released = bool(
        isinstance(persistent_release, dict)
        and persistent_release.get("released") is True
        and persistent_release.get("owned_worker_closed") is True
    )
    persistent_cleanup_proven = bool(
        not persistent_present
        or (
            isinstance(persistent_release, dict)
            and persistent_release.get("owned_worker_closed") is True
        )
    )
    persistent_cleanup_failed = bool(not persistent_cleanup_proven)
    phase_timings["total_seconds"] = round(time.perf_counter() - release_started, 6)
    return {
        "released": bool(had_model or persistent_model_released),
        "reason": (
            "persistent_and_in_process_models_released"
            if had_model and persistent_model_released
            else "persistent_model_released"
            if persistent_model_released
            else "model_released"
            if had_model
            else "persistent_session_closed"
            if persistent_present
            and not persistent_cleanup_failed
            else "persistent_worker_cleanup_not_proven"
            if persistent_cleanup_failed
            else "no_cached_model"
        ),
        "device": "cuda" if persistent_model_released else device,
        "persistent_status_before": persistent_before,
        "persistent_status_after": persistent_after,
        "persistent_release": persistent_release,
        "persistent_absence_proven": persistent_absence_proven,
        "persistent_cleanup_proven": persistent_cleanup_proven,
        "in_process_absence_proven": in_process_absence_proven,
        "in_process_cleanup": direct_cleanup,
        "cleanup_phase_timings_seconds": phase_timings,
        "playback": False,
        "generated_audio": False,
    }


def load_voice_config(path: str | Path = DEFAULT_CONFIG_PATH) -> VoiceOutputConfig:
    config_path = Path(path)
    if not config_path.exists():
        return VoiceOutputConfig()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return VoiceOutputConfig(
        enabled=bool(data.get("enabled", True)),
        engine=str(data.get("engine", "windows_sapi_powershell")),
        voice_name=str(data.get("voice_name", "")),
        rate=int(data.get("rate", -1)),
        volume=int(data.get("volume", 90)),
        max_chars=int(data.get("max_chars", 1600)),
        dry_run=bool(data.get("dry_run", False)),
        chatterbox_reference_audio=str(data.get("chatterbox_reference_audio", "")),
        chatterbox_device=str(data.get("chatterbox_device", "auto")),
        output_dir=str(data.get("output_dir", "")),
        play_audio=bool(data.get("play_audio", True)),
        pcm_output_gain_db=float(data.get("pcm_output_gain_db", 0.0)),
        proximity_cut_hz=float(data.get("proximity_cut_hz", 0.0)),
        proximity_cut_mix=float(data.get("proximity_cut_mix", 0.0)),
    )


def clean_text_for_speech(text: str, max_chars: int = 1600) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_#>~]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "."
    return cleaned


def infer_speech_emotion(text: str) -> str:
    """Infer a small prosody hint for the current SAPI approximation."""
    value = text.lower()
    if any(token in value for token in ("excited", "amazing", "wonderful", "can't wait")) or value.count("!") >= 2:
        return "excited"
    if any(token in value for token in ("sorry", "sad", "lonely", "miss you", "hurt")):
        return "gentle"
    if any(token in value for token in ("worried", "afraid", "careful", "concerned", "danger")):
        return "concerned"
    if any(token in value for token in ("thank you", "glad", "happy", "love", "good to see")):
        return "warm"
    return "neutral"


def apply_speech_emotion(config: VoiceOutputConfig, text: str) -> tuple[VoiceOutputConfig, str]:
    """Vary SAPI rate/volume modestly; this is expressive routing, not a voice model."""
    emotion = infer_speech_emotion(text)
    rate_delta = {"excited": 1, "warm": 0, "gentle": -1, "concerned": -1}.get(emotion, 0)
    volume_delta = {"excited": 2, "warm": 0, "gentle": -3, "concerned": -2}.get(emotion, 0)
    adjusted = replace(
        config,
        rate=max(-10, min(10, config.rate + rate_delta)),
        volume=max(0, min(100, config.volume + volume_delta)),
    )
    return adjusted, emotion


def load_candidate_voice_config(profile: dict[str, Any]) -> VoiceOutputConfig:
    """Choose an immediate SAPI approximation without claiming it is a voice clone."""
    cfg = load_voice_config()
    force_sapi = str(os.environ.get("KIRA_VOICE_FORCE_SAPI", "")).strip().lower() in {"1", "true", "yes", "on"}
    gender = str(profile.get("gender_preference", "")).strip().lower()
    if gender == "male":
        cfg.voice_name = "Microsoft David Desktop"
    elif gender == "female":
        cfg.voice_name = "Microsoft Zira Desktop"

    display = str(profile.get("display_name", "")).strip().lower()
    candidate_id = str(profile.get("candidate_id", "")).strip().lower()
    identity_text = f"{display} {candidate_id}"
    aliases: list[str] = []
    if "ladybug" in identity_text or "marinette" in identity_text:
        aliases.append("ladybug")
    if "kira" in identity_text:
        aliases.append("kira")
    if "peter parker" in identity_text or "peter_parker" in identity_text or "spider man" in identity_text or "spider_man" in identity_text:
        aliases.append("peter_parker")
    if (
        "robert_mcmurrer" in identity_text
        or "robert presence" in identity_text
        or "synthetic robert" in identity_text
    ):
        aliases.append("robert_mcmurrer")
    if "kara zor" in identity_text or "kara_zor" in identity_text:
        aliases.append("kara_zor_el")
    if (
        "h. h. holmes" in identity_text
        or "h h holmes" in identity_text
        or "h_h_holmes" in identity_text
    ):
        aliases.append("h_h_holmes")
    slugged = re.sub(r"[^a-z0-9]+", "_", display).strip("_")
    if slugged:
        aliases.append(slugged)

    profile_paths: list[Path] = []
    voice_section = profile.get("voice_and_behavior") if isinstance(profile.get("voice_and_behavior"), dict) else {}
    explicit_profile = str(voice_section.get("voice_profile") or "").strip().replace("\\", "/")
    if explicit_profile and not Path(explicit_profile).is_absolute():
        try:
            resolved_profile = (PROJECT_ROOT / explicit_profile).resolve()
            resolved_profile.relative_to(PROJECT_ROOT.resolve())
            profile_paths.append(resolved_profile)
        except (OSError, ValueError):
            pass
    profile_paths.extend(
        PROJECT_ROOT / "Voice" / "profiles" / "temp_ai" / f"{alias}_voice_profile.json"
        for alias in aliases
    )

    for path in dict.fromkeys(profile_paths):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            profile_alias = path.stem.removesuffix("_voice_profile")
            approximation = data.get("sapi_approximation", {})
            cfg.voice_name = str(approximation.get("voice_name", cfg.voice_name))
            cfg.rate = int(approximation.get("rate", cfg.rate))
            cfg.volume = int(approximation.get("volume", cfg.volume))
            cfg.max_chars = int(approximation.get("max_chars", cfg.max_chars))
            source_audio = data.get("source_audio", {}) if isinstance(data.get("source_audio"), dict) else {}
            reference_wav = str(source_audio.get("approved_reference_wav", "")).strip().replace("\\", "/")
            if reference_wav and not force_sapi and (PROJECT_ROOT / reference_wav).exists():
                cfg.engine = "chatterbox_tts"
                cfg.chatterbox_reference_audio = reference_wav
                device_override = str(os.environ.get("KIRA_CHATTERBOX_DEVICE", "")).strip().lower()
                cfg.chatterbox_device = device_override if device_override in {"auto", "cpu", "cuda"} else "auto"
                cfg.output_dir = str(Path("Voice") / "generated" / "temp_ai" / profile_alias)
                cfg.max_chars = min(cfg.max_chars, 450)
                runtime_audio = (
                    data.get("runtime_audio_postprocess")
                    if isinstance(data.get("runtime_audio_postprocess"), dict)
                    else {}
                )
                cfg.pcm_output_gain_db = float(runtime_audio.get("gain_db", 0.0))
                cfg.proximity_cut_hz = float(runtime_audio.get("proximity_cut_hz", 0.0))
                cfg.proximity_cut_mix = float(runtime_audio.get("proximity_cut_mix", 0.0))
            break
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return cfg


def load_kira_production_voice_config(
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> VoiceOutputConfig:
    """Load Kira's exact approved GPU-first voice route.

    The historical base config still supplies operator controls such as
    enabled/dry-run/playback.  Kira's identity binding is deliberately applied
    afterward so a stale ``KIRA_VOICE_FORCE_SAPI`` value cannot turn an exact
    Kira request into SAPI or another generic voice.  The hash-bound router
    performs the final profile/reference/evidence validation and fails closed
    if any approved artifact is unavailable or changed.
    """

    base = load_voice_config(path)
    routed = load_candidate_voice_config(
        {
            "candidate_id": "kira",
            "display_name": "Kira",
            "gender_preference": "female",
        }
    )
    routed.enabled = base.enabled
    routed.dry_run = base.dry_run
    routed.play_audio = base.play_audio
    routed.engine = "chatterbox_tts"
    routed.chatterbox_reference_audio = KIRA_APPROVED_REFERENCE_RELATIVE
    device_override = str(os.environ.get("KIRA_CHATTERBOX_DEVICE", "")).strip().lower()
    routed.chatterbox_device = (
        device_override if device_override in {"auto", "cpu", "cuda"} else "auto"
    )
    if not routed.output_dir:
        routed.output_dir = str(Path("Voice") / "generated" / "temp_ai" / "kira")
    return routed


def speak_text(text: str, config: VoiceOutputConfig | None = None) -> dict[str, Any]:
    cfg = config or load_voice_config()
    speech_text = clean_text_for_speech(text, cfg.max_chars)
    if not cfg.enabled:
        return {"spoken": False, "reason": "voice_output_disabled", "text": speech_text}
    if not speech_text:
        return {"spoken": False, "reason": "empty_text", "text": speech_text}
    if cfg.dry_run:
        return {"spoken": False, "reason": "dry_run", "text": speech_text}
    if _matches_exact_kira_approved_reference_path(cfg) and cfg.engine != "chatterbox_tts":
        return {
            "spoken": False,
            "reason": "exact_kira_reference_requires_approved_chatterbox_routes",
            "text": speech_text,
            "generic_voice_used": False,
            "sapi_fallback_used": False,
        }
    if cfg.engine == "chatterbox_tts":
        return _speak_with_chatterbox(speech_text, cfg)
    if cfg.engine != "windows_sapi_powershell":
        return {"spoken": False, "reason": f"unsupported_engine:{cfg.engine}", "text": speech_text}

    expressive_cfg, emotion = apply_speech_emotion(cfg, speech_text)
    command = _build_windows_sapi_command(speech_text, expressive_cfg)
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=max(20, min(180, len(speech_text) // 8 + 20)),
        check=False,
    )
    if completed.returncode != 0:
        return {
            "spoken": False,
            "reason": "sapi_error",
            "text": speech_text,
            "stderr": completed.stderr.strip(),
        }
    return {"spoken": True, "reason": "ok", "text": speech_text, "emotion": emotion}


def synthesize_text_to_wav(
    text: str,
    output_path: str | Path,
    config: VoiceOutputConfig | None = None,
) -> dict[str, Any]:
    """Render text to a WAV without playing it."""
    cfg = config or load_voice_config()
    # Target-voice messages must represent the complete durable text.  The
    # Chatterbox writer applies its own short, exact-coverage chunking below.
    speech_text = clean_text_for_speech(text, 0 if cfg.engine == "chatterbox_tts" else cfg.max_chars)
    target = Path(output_path)
    if not cfg.enabled:
        return {"generated": False, "reason": "voice_output_disabled", "text": speech_text}
    if not speech_text:
        return {"generated": False, "reason": "empty_text", "text": speech_text}
    if cfg.dry_run:
        return {"generated": False, "reason": "dry_run", "text": speech_text}
    if _matches_exact_kira_approved_reference_path(cfg) and cfg.engine != "chatterbox_tts":
        return {
            "generated": False,
            "reason": "exact_kira_reference_requires_approved_chatterbox_routes",
            "text": speech_text,
            "generic_voice_used": False,
            "sapi_fallback_used": False,
            "playback": False,
        }
    if cfg.engine == "chatterbox_tts":
        if _is_exact_kira_approved_reference(cfg):
            return _synthesize_with_kira_chatterbox_sidecar(speech_text, target, cfg)
        return _synthesize_with_chatterbox_to_wav(speech_text, target, cfg)
    if cfg.engine != "windows_sapi_powershell":
        return {"generated": False, "reason": f"unsupported_wav_engine:{cfg.engine}", "text": speech_text}
    if os.name != "nt":
        return {"generated": False, "reason": "windows_sapi_unavailable", "text": speech_text}

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.stem}.{os.getpid()}.part.wav")
    try:
        partial.unlink(missing_ok=True)
        expressive_cfg, emotion = apply_speech_emotion(cfg, speech_text)
        payload = {
            "text": speech_text,
            "output_path": str(partial.resolve()),
            "voice_name": expressive_cfg.voice_name,
            "rate": max(-10, min(10, expressive_cfg.rate)),
            "volume": max(0, min(100, expressive_cfg.volume)),
        }
        escaped = json.dumps(payload, ensure_ascii=False).replace("'", "''")
        command = f"""
$payload = '{escaped}' | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = [int]$payload.rate
$speaker.Volume = [int]$payload.volume
if ($payload.voice_name -and $payload.voice_name.Trim().Length -gt 0) {{
  $speaker.SelectVoice($payload.voice_name)
}}
$speaker.SetOutputToWaveFile($payload.output_path)
$speaker.Speak($payload.text)
$speaker.SetOutputToDefaultAudioDevice()
$speaker.Dispose()
""".strip()
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=max(20, min(180, len(speech_text) // 8 + 20)),
            check=False,
        )
        if completed.returncode != 0:
            return {
                "generated": False,
                "reason": "sapi_wav_error",
                "text": speech_text,
                "stderr": completed.stderr.strip(),
                "engine": cfg.engine,
            }
        if not partial.is_file() or partial.stat().st_size <= 44:
            return {"generated": False, "reason": "sapi_wav_missing_output", "text": speech_text, "engine": cfg.engine}
        partial.replace(target)
        return {
            "generated": True,
            "reason": "ok",
            "text": speech_text,
            "engine": cfg.engine,
            "emotion": emotion,
            "audio_path": str(target),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"generated": False, "reason": "sapi_wav_exception", "text": speech_text, "error": str(exc), "engine": cfg.engine}
    finally:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass


def _resolve_chatterbox_device(cfg: VoiceOutputConfig, torch_module: Any) -> str:
    device = str(cfg.chatterbox_device or "auto").strip().lower()
    if device == "auto":
        if not torch_module.cuda.is_available():
            return "cpu"
        try:
            minimum_free_mib = max(
                1024,
                int(os.environ.get("KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB", "6144")),
            )
        except (TypeError, ValueError):
            minimum_free_mib = 6144
        try:
            free_bytes, _total_bytes = torch_module.cuda.mem_get_info()
        except Exception:
            # Auto mode is intentionally fail-closed: an explicit `cuda`
            # override may still be used, but auto never guesses at headroom.
            return "cpu"
        return "cuda" if int(free_bytes) >= minimum_free_mib * 1024 * 1024 else "cpu"
    return device if device in {"cpu", "cuda"} else "cpu"


def _model_audio_to_numpy(wav: Any) -> Any:
    value = wav
    if hasattr(value, "squeeze"):
        value = value.squeeze()
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return value


def postprocess_chatterbox_samples(
    samples: Any,
    *,
    sample_rate: int,
    config: VoiceOutputConfig,
) -> tuple[Any, dict[str, Any]]:
    """Apply one profile-scoped PCM calibration pass after signal validation.

    Both single-turn and streaming playback write this already-calibrated PCM.
    There is no second playback gain, so the setting cannot be applied twice.
    """

    import numpy as np

    arr = np.asarray(samples, dtype=np.float32).reshape(-1)
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    gain_db = float(config.pcm_output_gain_db)
    cutoff_hz = float(config.proximity_cut_hz)
    cut_mix = float(config.proximity_cut_mix)
    if not math.isfinite(gain_db) or not -60.0 <= gain_db <= 6.0:
        raise ValueError("pcm_output_gain_db must be finite and between -60 and +6 dB")
    if not math.isfinite(cutoff_hz) or not 0.0 <= cutoff_hz < sample_rate / 2.0:
        raise ValueError("proximity_cut_hz must be finite, non-negative, and below Nyquist")
    if not math.isfinite(cut_mix) or not 0.0 <= cut_mix <= 1.0:
        raise ValueError("proximity_cut_mix must be finite and between 0 and 1")

    pre_rms = float(np.sqrt(np.mean(np.square(arr, dtype=np.float64)))) if arr.size else 0.0
    pre_peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    corrected = gentle_proximity_correction(
        arr,
        sample_rate=sample_rate,
        cutoff_hz=cutoff_hz,
        mix=cut_mix,
    )
    scaled = corrected * math.pow(10.0, gain_db / 20.0)
    clipped_sample_count = int(np.count_nonzero(np.abs(scaled) > 0.98))
    processed = np.clip(scaled, -0.98, 0.98).astype(np.float32, copy=False)
    post_rms = (
        float(np.sqrt(np.mean(np.square(processed, dtype=np.float64))))
        if processed.size
        else 0.0
    )
    post_peak = float(np.max(np.abs(processed))) if processed.size else 0.0
    return processed, {
        "applied": bool(gain_db != 0.0 or (cutoff_hz != 0.0 and cut_mix != 0.0)),
        "application_count": 1,
        "gain_db": gain_db,
        "proximity_cut_hz": cutoff_hz,
        "proximity_cut_mix": cut_mix,
        "pre_rms": round(pre_rms, 8),
        "pre_peak": round(pre_peak, 8),
        "post_rms": round(post_rms, 8),
        "post_peak": round(post_peak, 8),
        "clipped_sample_count": clipped_sample_count,
        "pitch_changed": False,
    }


def _synthesize_with_chatterbox_to_wav(
    text: str,
    target: Path,
    cfg: VoiceOutputConfig,
) -> dict[str, Any]:
    """Render a complete message with Kira's reviewed reference, never play it."""
    reference = PROJECT_ROOT / cfg.chatterbox_reference_audio if cfg.chatterbox_reference_audio else None
    if not reference or not reference.is_file():
        return {
            "generated": False,
            "reason": "missing_chatterbox_reference_audio",
            "text": text,
            "engine": "chatterbox_tts",
        }
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from chatterbox.tts import ChatterboxTTS
    except Exception as exc:
        return {
            "generated": False,
            "reason": "chatterbox_import_error",
            "text": text,
            "engine": "chatterbox_tts",
            "error": str(exc),
        }

    try:
        chunks, chunk_manifest = split_for_tts(text, max_chars=180)
    except ValueError as exc:
        return {
            "generated": False,
            "reason": "chatterbox_chunking_error",
            "text": text,
            "engine": "chatterbox_tts",
            "error": str(exc),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(
        f".{target.stem}.{os.getpid()}.{threading.get_ident()}.{time.monotonic_ns()}.part.wav"
    )
    device = _resolve_chatterbox_device(cfg, torch)
    unload_after_speak = str(os.environ.get("KIRA_UNLOAD_VOICE_AFTER_SPEAK", "")).strip().lower() in {
        "1", "true", "yes", "on"
    }
    checks: list[dict[str, Any]] = []
    postprocess_checks: list[dict[str, Any]] = []
    sample_rate = 0
    model_was_used = False
    failed_reason = ""
    failed_error = ""

    try:
        partial.unlink(missing_ok=True)
        global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
        with _CHATTERBOX_LOCK:
            _cancel_chatterbox_idle_timer_locked()
            try:
                if _CHATTERBOX_MODEL is None or _CHATTERBOX_DEVICE != device:
                    if _CHATTERBOX_MODEL is not None:
                        _release_chatterbox_model_locked()
                    _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device=device)
                    _CHATTERBOX_DEVICE = device
                model = _CHATTERBOX_MODEL
                sample_rate = int(model.sr)
                model_was_used = True
                with sf.SoundFile(
                    str(partial),
                    mode="w",
                    samplerate=sample_rate,
                    channels=1,
                    subtype="PCM_16",
                    format="WAV",
                ) as output:
                    for index, chunk in enumerate(chunks):
                        accepted = None
                        latest_check: dict[str, Any] = {}
                        for attempt in range(1, 4):
                            wav = model.generate(chunk, audio_prompt_path=str(reference))
                            samples = np.asarray(_model_audio_to_numpy(wav), dtype=np.float32).reshape(-1)
                            latest_check = assess_generated_speech_chunk(
                                samples,
                                sample_rate=sample_rate,
                                queued_word_count=len(spoken_words(chunk)),
                            )
                            latest_check.update({"chunk_index": index, "attempt": attempt})
                            if latest_check.get("passed"):
                                accepted = samples
                                break
                        checks.append(latest_check)
                        if accepted is None:
                            failed_reason = "chatterbox_signal_validation_failed"
                            break
                        processed, postprocess_check = postprocess_chatterbox_samples(
                            accepted,
                            sample_rate=sample_rate,
                            config=cfg,
                        )
                        postprocess_check["chunk_index"] = index
                        postprocess_checks.append(postprocess_check)
                        output.write(processed)
                        if index < len(chunks) - 1:
                            output.write(np.zeros(max(1, int(sample_rate * 0.06)), dtype=np.float32))
            except Exception as exc:
                failed_reason = "chatterbox_wav_generation_error"
                failed_error = str(exc)
            finally:
                if model_was_used and not unload_after_speak:
                    _schedule_chatterbox_idle_unload_locked()

        if (
            failed_reason == "chatterbox_wav_generation_error"
            and str(cfg.chatterbox_device or "").strip().lower() == "auto"
            and device == "cuda"
        ):
            # Preserve the exact same reference voice and public text.  Only
            # the compute device changes, and only after CUDA has failed.
            release_voice_output()
            fallback = _synthesize_with_chatterbox_to_wav(
                text,
                target,
                replace(cfg, chatterbox_device="cpu"),
            )
            return {
                **fallback,
                "auto_device_fallback": "cpu_after_cuda_generation_error",
                "cuda_error": failed_error,
            }
        if failed_reason:
            return {
                "generated": False,
                "reason": failed_reason,
                "text": text,
                "engine": "chatterbox_tts",
                "device": device,
                "error": failed_error,
                "chunk_checks": checks,
            }
        if not partial.is_file() or partial.stat().st_size <= 44:
            return {
                "generated": False,
                "reason": "chatterbox_wav_missing_output",
                "text": text,
                "engine": "chatterbox_tts",
                "device": device,
            }
        partial.replace(target)
        return {
            "generated": True,
            "reason": "ok",
            "text": text,
            "engine": "chatterbox_tts",
            "device": device,
            "audio_path": str(target),
            "voice_identity_status": "reviewed_reference_chatterbox",
            "playback": False,
            "sample_rate": sample_rate,
            "chunks": chunk_manifest,
            "chunk_checks": checks,
            "audio_postprocess": {
                "applied": any(item.get("applied") for item in postprocess_checks),
                "application_count_per_chunk": 1,
                "chunks": postprocess_checks,
            },
        }
    except OSError as exc:
        return {
            "generated": False,
            "reason": "chatterbox_wav_io_error",
            "text": text,
            "engine": "chatterbox_tts",
            "device": device,
            "error": str(exc),
        }
    finally:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        if unload_after_speak and model_was_used:
            _unload_chatterbox_model()


def _speak_with_chatterbox(text: str, cfg: VoiceOutputConfig) -> dict[str, Any]:
    reference = PROJECT_ROOT / cfg.chatterbox_reference_audio if cfg.chatterbox_reference_audio else None
    if not reference or not reference.exists():
        return {"spoken": False, "reason": "missing_chatterbox_reference_audio", "text": text}
    if _is_exact_kira_approved_reference(cfg):
        output_dir = PROJECT_ROOT / (cfg.output_dir or str(Path("Voice") / "generated" / "chatterbox"))
        try:
            output_dir = output_dir.resolve()
            output_dir.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return {
                "spoken": False,
                "reason": "voice_output_dir_not_project_owned",
                "text": text,
                "engine": "chatterbox_tts",
            }
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"tts_{time.strftime('%Y%m%d_%H%M%S')}_{time.monotonic_ns()}.wav"
        synthesis = _synthesize_with_kira_chatterbox_sidecar(text, output_path, replace(cfg, play_audio=False))
        if synthesis.get("generated") is not True:
            return {
                **synthesis,
                "spoken": False,
                "text": text,
            }
        playback = _play_wav(output_path) if cfg.play_audio else {"played": False, "reason": "playback_disabled"}
        return {
            **synthesis,
            "spoken": bool(playback.get("played")),
            "reason": "ok" if playback.get("played") else playback.get("reason", "generated_not_played"),
            "text": text,
            "audio_path": str(output_path.relative_to(PROJECT_ROOT)),
            "playback": bool(playback.get("played")),
            "playback_result": playback,
        }
    unload_after_speak = str(os.environ.get("KIRA_UNLOAD_VOICE_AFTER_SPEAK", "")).strip().lower() in {"1", "true", "yes", "on"}
    try:
        import torch
        import soundfile as sf
        from chatterbox.tts import ChatterboxTTS
    except Exception as exc:
        return {"spoken": False, "reason": "chatterbox_import_error", "text": text, "error": str(exc)}

    device = _resolve_chatterbox_device(cfg, torch)

    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    model_was_used = False
    signal_check: dict[str, Any] = {}
    accepted_samples: Any | None = None
    postprocess_check: dict[str, Any] = {}
    try:
        with _CHATTERBOX_LOCK:
            _cancel_chatterbox_idle_timer_locked()
            if _CHATTERBOX_MODEL is None or _CHATTERBOX_DEVICE != device:
                if _CHATTERBOX_MODEL is not None:
                    _release_chatterbox_model_locked()
                _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device=device)
                _CHATTERBOX_DEVICE = device
            model = _CHATTERBOX_MODEL
            model_was_used = True
            for attempt in range(1, 4):
                wav = model.generate(text, audio_prompt_path=str(reference))
                samples = _model_audio_to_numpy(wav)
                signal_check = assess_generated_speech_chunk(
                    samples,
                    sample_rate=int(model.sr),
                    queued_word_count=len(spoken_words(text)),
                )
                signal_check["attempt"] = attempt
                if signal_check.get("passed"):
                    accepted_samples = samples
                    break
            if not unload_after_speak:
                _schedule_chatterbox_idle_unload_locked()
    except Exception as exc:
        if unload_after_speak:
            _unload_chatterbox_model()
        return {"spoken": False, "reason": "chatterbox_generation_error", "text": text, "error": str(exc)}
    if accepted_samples is None:
        if unload_after_speak:
            _unload_chatterbox_model()
        return {
            "spoken": False,
            "reason": "chatterbox_signal_validation_failed",
            "text": text,
            "engine": "chatterbox_tts",
            "device": device,
            "signal_check": signal_check,
        }

    output_dir = PROJECT_ROOT / (cfg.output_dir or str(Path("Voice") / "generated" / "chatterbox"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"tts_{time.strftime('%Y%m%d_%H%M%S')}_{time.monotonic_ns()}.wav"
    try:
        processed_samples, postprocess_check = postprocess_chatterbox_samples(
            accepted_samples,
            sample_rate=int(model.sr),
            config=cfg,
        )
        sf.write(str(output_path), processed_samples, int(model.sr))
    except Exception as exc:
        if unload_after_speak and model_was_used:
            _unload_chatterbox_model()
        return {"spoken": False, "reason": "chatterbox_save_error", "text": text, "error": str(exc)}

    if unload_after_speak and model_was_used:
        _unload_chatterbox_model()

    playback = {"played": False, "reason": "playback_disabled"}
    if cfg.play_audio:
        playback = _play_wav(output_path)
    result = {
        "spoken": bool(playback.get("played", False)),
        "reason": "ok" if playback.get("played", False) else playback.get("reason", "generated_not_played"),
        "text": text,
        "engine": "chatterbox_tts",
        "device": device,
        "audio_path": str(output_path.relative_to(PROJECT_ROOT)),
        "signal_check": signal_check,
        "audio_postprocess": postprocess_check,
    }
    if unload_after_speak and model_was_used:
        result["model_unloaded_after_speak"] = True
    elif _voice_idle_unload_seconds() > 0:
        result["model_idle_unload_seconds"] = _voice_idle_unload_seconds()
    return result


def _build_windows_sapi_command(text: str, cfg: VoiceOutputConfig) -> str:
    payload = {
        "text": text,
        "voice_name": cfg.voice_name,
        "rate": max(-10, min(10, cfg.rate)),
        "volume": max(0, min(100, cfg.volume)),
    }
    json_payload = json.dumps(payload, ensure_ascii=False)
    escaped = json_payload.replace("'", "''")
    return f"""
$payload = '{escaped}' | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = [int]$payload.rate
$speaker.Volume = [int]$payload.volume
if ($payload.voice_name -and $payload.voice_name.Trim().Length -gt 0) {{
  $speaker.SelectVoice($payload.voice_name)
}}
$speaker.Speak($payload.text)
$speaker.Dispose()
""".strip()


def _play_wav(path: Path) -> dict[str, Any]:
    if os.name == "nt":
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
            return {"played": True, "reason": "ok", "backend": "winsound_sync"}
        except Exception:
            # Keep the older PowerShell player as a compatibility fallback.
            # A new process is slower between chunks, but it is preferable to
            # dropping an otherwise valid reply on an unusual Windows build.
            pass
    escaped = str(path).replace("'", "''")
    command = f"""
Add-Type -AssemblyName System.Windows.Forms
$player = New-Object System.Media.SoundPlayer '{escaped}'
$player.Load()
$player.PlaySync()
""".strip()
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        return {"played": False, "reason": "wav_playback_error", "stderr": completed.stderr.strip()}
    return {"played": True, "reason": "ok", "backend": "powershell_soundplayer_sync"}


def play_wav_file(path: str | Path) -> dict[str, Any]:
    """Play one project-owned WAV synchronously.

    Exposing this narrow wrapper lets the live reply scheduler generate the
    next chunk while exactly one playback worker owns the current chunk.  It
    deliberately rejects path escape and never changes the selected voice.
    """

    target = Path(path)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    try:
        target = target.resolve(strict=True)
        target.relative_to(PROJECT_ROOT.resolve())
    except (OSError, ValueError):
        return {"played": False, "reason": "wav_path_not_project_owned"}
    if target.suffix.lower() != ".wav" or not target.is_file():
        return {"played": False, "reason": "wav_playback_input_missing"}
    result = _play_wav(target)
    result["audio_path"] = str(target.relative_to(PROJECT_ROOT.resolve()))
    return result


_VOICE_ROUTE_DIAGNOSTIC_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:+-]{1,96}$")


def _voice_route_diagnostic_token(value: Any) -> str:
    """Return one bounded machine diagnostic token, never free-form output."""

    token = str(value or "").strip()
    return token if _VOICE_ROUTE_DIAGNOSTIC_TOKEN_RE.fullmatch(token) else ""


def _voice_route_diagnostic_number(value: Any) -> int | float | None:
    """Retain finite resource measurements while rejecting booleans/objects."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return int(value) if isinstance(value, int) else numeric


def _safe_approved_voice_route_evidence(result: dict[str, Any]) -> dict[str, Any]:
    """Project a sidecar result to non-private routing and resource evidence.

    Sidecars may return tracebacks, warning text, or other process diagnostics.
    The live timing lane needs to prove the selected approved path without
    copying any of that free-form material into its benchmark or life log.
    """

    raw_attempts = result.get("approved_voice_attempts")
    attempts: list[dict[str, str]] = []
    # The real router promotes these fields before raw attempt diagnostics are
    # sanitized.  Reading the flat form first makes this projection idempotent:
    # the shell can safely project a Core chunk result again for its life log.
    blackwell_cache_audit: dict[str, Any] = _safe_blackwell_self_check_cache_evidence(
        {
            "status": result.get("blackwell_self_check_cache_status"),
            "scope": result.get("blackwell_self_check_cache_scope"),
            "key_sha256": result.get("blackwell_self_check_cache_key_sha256"),
        }
    )
    if isinstance(raw_attempts, list):
        for raw_attempt in raw_attempts:
            if not isinstance(raw_attempt, dict):
                continue
            attempt: dict[str, str] = {}
            for key in ("route_id", "role", "status", "reason"):
                token = _voice_route_diagnostic_token(raw_attempt.get(key))
                if token:
                    attempt[key] = token
            if attempt.get("route_id"):
                attempts.append(attempt)
            if attempt.get("route_id") == "blackwell_gpu":
                raw_self_check = raw_attempt.get("self_check")
                raw_self_check = raw_self_check if isinstance(raw_self_check, dict) else {}
                raw_cache = raw_self_check.get("self_check_cache")
                nested_cache_audit = _safe_blackwell_self_check_cache_evidence(raw_cache)
                for key, value in nested_cache_audit.items():
                    blackwell_cache_audit.setdefault(key, value)

    summary_parts = []
    for attempt in attempts:
        route_id = attempt["route_id"]
        status = attempt.get("status") or "unknown"
        reason = attempt.get("reason") or ""
        summary_parts.append(":".join(part for part in (route_id, status, reason) if part))
    route_attempt_summary = ",".join(summary_parts)[:160]

    routing = result.get("approved_voice_routing")
    routing = routing if isinstance(routing, dict) else {}
    gpu_proof = result.get("gpu_proof")
    gpu_proof = gpu_proof if isinstance(gpu_proof, dict) else {}
    resources = result.get("resources")
    resources = resources if isinstance(resources, dict) else {}

    route_id = _voice_route_diagnostic_token(result.get("route_id"))
    approved_path = _voice_route_diagnostic_token(result.get("approved_voice_path_used"))
    preferred_failure_reason = _voice_route_diagnostic_token(
        routing.get("preferred_failure_reason")
        or result.get("preferred_failure_reason")
    )
    device = _voice_route_diagnostic_token(result.get("device"))
    statuses_by_route = {
        attempt.get("route_id", ""): attempt.get("status", "")
        for attempt in attempts
    }

    gpu_synthesis_attempted = statuses_by_route.get("blackwell_gpu") in {
        "synthesis_failed",
        "used",
    }
    if isinstance(result.get("gpu_synthesis_attempted"), bool):
        gpu_synthesis_attempted = result["gpu_synthesis_attempted"]
    cpu_synthesis_attempted = statuses_by_route.get("sealed_cpu") in {
        "synthesis_failed",
        "used",
    }
    if isinstance(result.get("cpu_synthesis_attempted"), bool):
        cpu_synthesis_attempted = result["cpu_synthesis_attempted"]
    automatic_cpu_fallback_used = approved_path == "sealed_cpu"
    if isinstance(result.get("automatic_cpu_fallback_used"), bool):
        automatic_cpu_fallback_used = result["automatic_cpu_fallback_used"]

    evidence: dict[str, Any] = {
        "route_id": route_id,
        "approved_voice_path_used": approved_path,
        "device": device,
        "approved_voice_attempts": attempts,
        "route_attempt_summary": route_attempt_summary,
        "preferred_failure_reason": preferred_failure_reason,
        "gpu_synthesis_attempted": gpu_synthesis_attempted,
        "cpu_synthesis_attempted": cpu_synthesis_attempted,
        "automatic_cpu_fallback_used": automatic_cpu_fallback_used,
        **blackwell_cache_audit,
    }
    sidecar_lifecycle = _voice_route_diagnostic_token(result.get("sidecar_lifecycle"))
    if sidecar_lifecycle:
        evidence["sidecar_lifecycle"] = sidecar_lifecycle
    for key in (
        "persistent_worker_reused",
        "staging_promoted_to_caller_target",
        "generic_voice_used",
        "sapi_voice_used",
        "fallback_used",
        "test_only_injected_client",
        "production_route_promoted",
        "production_routing_authorized",
    ):
        if isinstance(result.get(key), bool):
            evidence[key] = result[key]
    gpu_actual_allocation = gpu_proof.get("actual_gpu_allocation")
    if not isinstance(gpu_actual_allocation, bool):
        gpu_actual_allocation = result.get("gpu_actual_allocation")
    if isinstance(gpu_actual_allocation, bool):
        evidence["gpu_actual_allocation"] = gpu_actual_allocation
    gpu_actual_execution = gpu_proof.get("actual_gpu_execution")
    if not isinstance(gpu_actual_execution, bool):
        gpu_actual_execution = result.get("gpu_actual_execution")
    if isinstance(gpu_actual_execution, bool):
        evidence["gpu_actual_execution"] = gpu_actual_execution
    qwen_absent_for_generation = gpu_proof.get(
        "qwen_absence_proven_for_accepted_generation"
    )
    if not isinstance(qwen_absent_for_generation, bool):
        qwen_absent_for_generation = result.get(
            "qwen_absence_proven_for_accepted_generation"
        )
    if isinstance(qwen_absent_for_generation, bool):
        evidence["qwen_absence_proven_for_accepted_generation"] = (
            qwen_absent_for_generation
        )
    if isinstance(result.get("gpu_utilization_observed"), bool):
        evidence["gpu_utilization_observed"] = result["gpu_utilization_observed"]

    numeric_fields = {
        "peak_allocated_bytes": gpu_proof.get("peak_allocated_bytes"),
        "peak_reserved_bytes": gpu_proof.get("peak_reserved_bytes"),
        "peak_process_rss_mib": resources.get("peak_process_rss_mib"),
        "peak_system_ram_used_mib": resources.get("peak_system_ram_used_mib"),
        "baseline_gpu_vram_used_mib": resources.get("baseline_gpu_vram_used_mib"),
        "peak_gpu_vram_used_mib": resources.get("peak_gpu_vram_used_mib"),
        "peak_sidecar_gpu_delta_mib": resources.get("peak_sidecar_gpu_delta_mib"),
        "sidecar_process_seconds": result.get("process_seconds"),
    }
    for key, value in numeric_fields.items():
        if value is None:
            value = result.get(key)
        safe_value = _voice_route_diagnostic_number(value)
        if safe_value is not None:
            evidence[key] = safe_value
    return evidence


def speak_text_chunks_streaming(
    chunks: list[str],
    config: VoiceOutputConfig | None = None,
    *,
    prefetch_capacity: int = 2,
    event_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Generate ordered Chatterbox chunks while the prior chunk is playing.

    Chatterbox still returns a complete waveform per chunk; this is therefore
    bounded producer/consumer scheduling, not sample-level model streaming.
    One synthesis producer and one synchronous playback consumer preserve
    order and prevent overlap.  Completion is reported separately from
    ``spoken`` so a partial audible result can never be mislabeled ``ok``.
    """

    def emit(event: str, details: dict[str, Any], *, monotonic_ns: int | None = None) -> None:
        if event_callback is None:
            return
        payload = {
            **details,
            "monotonic_ns": int(monotonic_ns if monotonic_ns is not None else time.perf_counter_ns()),
        }
        try:
            event_callback(event, payload)
        except Exception:
            # Evidence capture must never break or delay the voice path because
            # an optional writer/collector failed.
            return

    cfg = config or load_voice_config()
    prepared = [clean_text_for_speech(str(chunk or ""), max_chars=0) for chunk in chunks]
    prepared = [chunk for chunk in prepared if chunk]
    if not prepared:
        return {
            "spoken": False,
            "complete": False,
            "reason": "empty_text",
            "chunk_results": [],
        }
    if cfg.engine != "chatterbox_tts":
        results: list[dict[str, Any]] = []
        started = time.perf_counter()
        for index, chunk in enumerate(prepared):
            public_words = spoken_words(chunk)
            combined_started_ns = time.perf_counter_ns()
            emit(
                "chunk_combined_output_start",
                {"chunk_index": index, "public_words": public_words},
                monotonic_ns=combined_started_ns,
            )
            chunk_started = time.perf_counter()
            result = speak_text(chunk, cfg)
            combined_ended_ns = time.perf_counter_ns()
            emit(
                "chunk_combined_output_end",
                {
                    "chunk_index": index,
                    "public_words": public_words,
                    "played": bool(result.get("spoken")),
                    "complete": bool(result.get("spoken")),
                    "reason": str(result.get("reason") or ""),
                },
                monotonic_ns=combined_ended_ns,
            )
            results.append(
                {
                    **result,
                    "chunk_index": index,
                    "elapsed_seconds": round(time.perf_counter() - chunk_started, 3),
                }
            )
            if not result.get("spoken"):
                break
        complete = len(results) == len(prepared) and all(item.get("spoken") for item in results)
        return {
            "spoken": any(item.get("spoken") for item in results),
            "complete": complete,
            "reason": "ok" if complete else "voice_incomplete",
            "pipeline": "serial_non_chatterbox",
            "chunk_results": results,
            "duration_seconds": round(time.perf_counter() - started, 3),
        }

    capacity = max(1, min(8, int(prefetch_capacity)))
    playback_queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=capacity)
    playback_records: dict[int, dict[str, Any]] = {}
    generation_records: dict[int, dict[str, Any]] = {}
    playback_failed = threading.Event()
    pipeline_started = time.perf_counter()

    def playback_worker() -> None:
        prior_ended: float | None = None
        while True:
            item = playback_queue.get()
            try:
                if item is None:
                    return
                index = int(item["chunk_index"])
                public_words = list(item.get("public_words") or [])
                playback_started_ns = time.perf_counter_ns()
                playback_started = playback_started_ns / 1_000_000_000.0
                if cfg.play_audio:
                    emit(
                        "chunk_playback_start",
                        {
                            "chunk_index": index,
                            "public_words": public_words,
                            "played": False,
                            "first_audible_proxy_kind": "playback_api_call_start_not_owner_observed_audible",
                        },
                        monotonic_ns=playback_started_ns,
                    )
                    if index == 0:
                        emit(
                            "first_playback_proxy",
                            {
                                "chunk_index": index,
                                "public_words": public_words,
                                "first_audible_proxy_kind": "playback_api_call_start_not_owner_observed_audible",
                                "owner_true_first_audible_monotonic_ms": None,
                                "owner_observation_required": True,
                            },
                            monotonic_ns=playback_started_ns,
                        )
                else:
                    emit(
                        "chunk_playback_skipped",
                        {
                            "chunk_index": index,
                            "public_words": public_words,
                            "played": False,
                            "playback_reason": "playback_disabled",
                        },
                        monotonic_ns=playback_started_ns,
                    )
                try:
                    result = play_wav_file(str(item["audio_path"])) if cfg.play_audio else {
                        "played": False,
                        "reason": "playback_disabled",
                    }
                except Exception as exc:  # pragma: no cover - defensive audio backend boundary
                    result = {
                        "played": False,
                        "reason": "wav_playback_exception",
                        "error": str(exc),
                    }
                playback_ended_ns = time.perf_counter_ns()
                playback_ended = playback_ended_ns / 1_000_000_000.0
                emit(
                    "chunk_playback_end",
                    {
                        "chunk_index": index,
                        "public_words": public_words,
                        "played": bool(result.get("played")),
                        "playback_reason": str(result.get("reason") or ""),
                    },
                    monotonic_ns=playback_ended_ns,
                )
                record = {
                    **result,
                    "chunk_index": index,
                    "playback_started_seconds": round(playback_started - pipeline_started, 3),
                    "playback_elapsed_seconds": round(playback_ended - playback_started, 3),
                    "continuation_gap_seconds": (
                        0.0
                        if prior_ended is None
                        else round(max(0.0, playback_started - prior_ended), 3)
                    ),
                }
                playback_records[index] = record
                prior_ended = playback_ended
                if not result.get("played"):
                    playback_failed.set()
            finally:
                playback_queue.task_done()

    consumer = threading.Thread(
        target=playback_worker,
        name="kira-voice-chunk-playback",
        daemon=True,
    )
    consumer.start()

    output_dir = PROJECT_ROOT / (cfg.output_dir or str(Path("Voice") / "generated" / "chatterbox"))
    try:
        output_dir = output_dir.resolve()
        output_dir.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        playback_queue.put(None)
        playback_queue.join()
        consumer.join(timeout=2.0)
        return {
            "spoken": False,
            "complete": False,
            "reason": "voice_output_dir_not_project_owned",
            "chunk_results": [],
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    synthesis_cfg = replace(cfg, play_audio=False)
    generation_failed = False

    for index, chunk in enumerate(prepared):
        if playback_failed.is_set():
            generation_failed = True
            generation_records[index] = {
                "generated": False,
                "reason": "playback_failed_before_chunk_generation",
                "chunk_index": index,
                "text": chunk,
            }
            break
        target = output_dir / (
            f"tts_stream_{time.strftime('%Y%m%d_%H%M%S')}_"
            f"{time.monotonic_ns()}_{index:03d}.wav"
        )
        public_words = spoken_words(chunk)
        generated_started_ns = time.perf_counter_ns()
        generated_started = generated_started_ns / 1_000_000_000.0
        emit(
            "chunk_synthesis_start",
            {"chunk_index": index, "public_words": public_words},
            monotonic_ns=generated_started_ns,
        )
        try:
            result = synthesize_text_to_wav(chunk, target, synthesis_cfg)
        except Exception as exc:  # pragma: no cover - defensive model/backend boundary
            result = {
                "generated": False,
                "reason": "voice_synthesis_exception",
                "error": str(exc),
                "text": chunk,
            }
        generation_ended_ns = time.perf_counter_ns()
        generation_ended = generation_ended_ns / 1_000_000_000.0
        route_evidence = _safe_approved_voice_route_evidence(result)
        emit(
            "chunk_synthesis_end",
            {
                "chunk_index": index,
                "public_words": public_words,
                "generated": bool(result.get("generated")),
                "generation_reason": str(result.get("reason") or ""),
                **{
                    key: value
                    for key, value in route_evidence.items()
                    if key != "approved_voice_attempts"
                },
            },
            monotonic_ns=generation_ended_ns,
        )
        record = {
            **result,
            "chunk_index": index,
            "text": chunk,
            "generation_elapsed_seconds": round(generation_ended - generated_started, 3),
            "ready_seconds": round(generation_ended - pipeline_started, 3),
        }
        generation_records[index] = record
        if not result.get("generated"):
            generation_failed = True
            break
        playback_queue.put(
            {
                "chunk_index": index,
                "audio_path": str(target),
                "public_words": public_words,
            }
        )

    playback_queue.put(None)
    playback_queue.join()
    consumer.join(timeout=2.0)

    chunk_results: list[dict[str, Any]] = []
    for index, chunk in enumerate(prepared):
        generated = generation_records.get(index, {})
        played = playback_records.get(index, {})
        route_evidence = _safe_approved_voice_route_evidence(generated)
        chunk_results.append(
            {
                "chunk_index": index,
                "text": chunk,
                "generated": bool(generated.get("generated")),
                "played": bool(played.get("played")),
                "generation_reason": generated.get("reason", "not_generated"),
                "playback_reason": played.get("reason", "not_played"),
                "audio_path": generated.get("audio_path", ""),
                "generation_elapsed_seconds": generated.get("generation_elapsed_seconds"),
                "playback_elapsed_seconds": played.get("playback_elapsed_seconds"),
                "continuation_gap_seconds": played.get("continuation_gap_seconds"),
                **route_evidence,
            }
        )

    played_count = sum(bool(item.get("played")) for item in playback_records.values())
    complete = (
        not generation_failed
        and not playback_failed.is_set()
        and len(generation_records) == len(prepared)
        and len(playback_records) == len(prepared)
        and all(item.get("generated") for item in generation_records.values())
        and all(item.get("played") for item in playback_records.values())
    )
    ordered_playbacks = [playback_records[index] for index in sorted(playback_records)]
    continuation_gaps = [
        float(item.get("continuation_gap_seconds") or 0.0)
        for item in ordered_playbacks[1:]
    ]
    first_playback = ordered_playbacks[0] if ordered_playbacks else {}
    return {
        "spoken": played_count > 0,
        "complete": complete,
        "reason": "ok" if complete else "voice_incomplete",
        "pipeline": "bounded_chunk_prefetch_v1",
        "voice_identity_unchanged": True,
        "chunk_count": len(prepared),
        "played_chunk_count": played_count,
        "chunk_results": chunk_results,
        "first_audio_elapsed_seconds": first_playback.get("playback_started_seconds"),
        "continuation_gap_seconds": continuation_gaps,
        "max_continuation_gap_seconds": round(max(continuation_gaps), 3) if continuation_gaps else 0.0,
        "duration_seconds": round(time.perf_counter() - pipeline_started, 3),
    }


def list_windows_voices() -> list[dict[str, str]]:
    command = """
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.GetInstalledVoices() | ForEach-Object {
  $info = $_.VoiceInfo
  [PSCustomObject]@{
    Name = $info.Name
    Culture = $info.Culture.Name
    Gender = $info.Gender.ToString()
    Age = $info.Age.ToString()
  } | ConvertTo-Json -Compress
}
$speaker.Dispose()
""".strip()
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    voices: list[dict[str, str]] = []
    if completed.returncode != 0:
        return voices
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            voices.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return voices


def main() -> None:
    parser = argparse.ArgumentParser(description="Speak text using Kira's local voice output config.")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list_voices:
        for voice in list_windows_voices():
            print(f"{voice.get('Name', '')} | {voice.get('Culture', '')} | {voice.get('Gender', '')} | {voice.get('Age', '')}")
        return

    config = load_voice_config(args.config)
    if args.dry_run:
        config.dry_run = True
    result = speak_text(args.text, config=config)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
