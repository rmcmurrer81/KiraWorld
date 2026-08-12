#!/usr/bin/env python3
"""Default-inert two-turn latency acceptance for normal Kira Text + Voice.

The live path starts the same local shell server used by the normal launcher,
but with an isolated runtime directory and one explicitly selected, default-off
latency candidate.  It never opens a browser, camera, or microphone.  A live
run requires explicit owner/playback/GPU-boundary confirmations and, for the
persistent voice modes, a passing standalone persistent-worker report.

Running this file without ``--execute-live`` is descriptive only.  It starts
no process, model, GPU worker, audio playback, device, or browser and writes no
evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib import request as urllib_request


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_kira_model_question_series_acceptance as series  # noqa: E402
from tools import run_kira_text_voice_bounded_owner_acceptance as bounded  # noqa: E402
from tools import run_persistent_blackwell_voice_candidate_acceptance as persistent  # noqa: E402


EXPECTED_MODEL_NAME = "llama3.1:8b"
EXPECTED_MODEL_DIGEST = (
    "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e"
)
VOICE_OUTPUT_DIR = ROOT / "Voice" / "generated" / "temp_ai" / "kira"
LIVE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "kira_text_voice_two_turn_latency_acceptance"
)
PREPARED_OWNER_HEARING_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_attempt06_hang_diagnostics"
    / "attempt_01"
    / "TWO_TURN_OWNER_HEARING_ATTEMPT06_DIAGNOSTIC_REBOUND_CONFIG.json"
)
HISTORICAL_PREPARED_TURING_PSYCH_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_turing_psych_voice_gate_implementation"
    / "TURING_PSYCH_VOICE_TIMING_CONFIG.json"
)
EXTENDED_PROFILE_PACKAGE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_turing_psych_non_body_extended_profile"
    / "attempt_01"
)
HOST_RETURN_REPAIR_PACKAGE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_attempt06_hang_diagnostics"
    / "attempt_01"
)
PREPARED_TURING_PSYCH_CONFIG = (
    HOST_RETURN_REPAIR_PACKAGE_ROOT
    / "TURING_PSYCH_TWO_TURN_ATTEMPT06_DIAGNOSTIC_REBOUND_CONFIG.json"
)
PREPARED_EXTENDED_TURING_PSYCH_CONFIG = (
    HOST_RETURN_REPAIR_PACKAGE_ROOT
    / "TURING_PSYCH_NON_BODY_ATTEMPT06_DIAGNOSTIC_REBOUND_CONFIG.json"
)
REPORT_NAME = "TWO_TURN_LATENCY_ACCEPTANCE.json"
DESKTOP_FIRST_AUDIBLE_TARGET_SECONDS = 1.5
VRAM_RETURN_TOLERANCE_MIB = 512.0
HISTORICAL_OWNER_HEARING_HARNESS_SHA256 = (
    "6f8cc199b12b3015fd61723b6f52e89d33c134be3115780ed721af9cbf4c5f32"
)
PRE_V2_OWNER_HEARING_HARNESS_SHA256 = (
    "1b1135e799ddc7f88a20bbd4d39900067f465c9294b9e98ad3baad53a5ec4e41"
)
V1_PERSISTENT_FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"
V2_PERSISTENT_FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"
V2_APPLICATION_ACCEPTANCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "application_route_v2"
)
V2_APPLICATION_PASS_REPORT = V2_APPLICATION_ACCEPTANCE_ROOT / "attempt_04" / "FINAL_REPORT.json"
V2_APPLICATION_PASS_REPORT_SHA256 = (
    "659ab7886c4571b3deb0bf759cc7ba84c3ff24a47a1f0ec7c7f3b3216171d9ab"
)
V2_FULL_GPU_PASS_REPORT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "full_gpu_v2"
    / "attempt_02"
    / "FINAL_REPORT.json"
)
V2_FULL_GPU_PASS_REPORT_SHA256 = (
    "40771bb8961a09a9e627e2c8b3a0d80da18dbb3199aea900912c56ceefc7d339"
)
V2_CANDIDATE_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate_v2"
V2_CURRENT_HOST_BINDINGS: dict[str, Path] = {
    "Core/persistent_blackwell_voice_integration_v2.py": (
        ROOT / "Core" / "persistent_blackwell_voice_integration_v2.py"
    ),
    "Core/voice_output.py": ROOT / "Core" / "voice_output.py",
}
V2_IDENTITY_BINDINGS: dict[str, Path] = {
    "Voice/profiles/temp_ai/kira_voice_profile.json": (
        ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
    ),
    (
        "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
        "model_input/approved_reference.wav"
    ): (
        ROOT
        / "Voice"
        / "reference_packs"
        / "kira"
        / "kira_online_source_20260706_221447"
        / "model_input"
        / "approved_reference.wav"
    ),
    (
        "RecoverySprint/continuation_20260802/"
        "persistent_blackwell_voice_candidate_acceptance/full_gpu_v2/"
        "attempt_02/FINAL_REPORT.json"
    ): V2_FULL_GPU_PASS_REPORT,
}
V2_SEALED_BINDINGS: dict[str, Path] = {
    "candidate_config": V2_CANDIDATE_ROOT / "candidate_config.json",
    "candidate_contract": V2_CANDIDATE_ROOT / "candidate_contract.py",
    "candidate_client": V2_CANDIDATE_ROOT / "candidate_client.py",
    "candidate_worker": V2_CANDIDATE_ROOT / "persistent_worker.py",
    "approved_profile": V2_IDENTITY_BINDINGS[
        "Voice/profiles/temp_ai/kira_voice_profile.json"
    ],
    "approved_reference": V2_IDENTITY_BINDINGS[
        (
            "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
            "model_input/approved_reference.wav"
        )
    ],
    "production_routing_manifest": (
        ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json"
    ),
}

OWNER_HEARING_TURN_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "natural_check_in",
        "text": (
            "Kira, how are you feeling right now? Please answer naturally in one "
            "or two brief sentences."
        ),
    },
    {
        "id": "shared_next_choice",
        "text": (
            "What would you like to do together next in Kira World? Please answer "
            "naturally in one or two brief sentences."
        ),
    },
)
TURN_SPECS = OWNER_HEARING_TURN_SPECS
VOLUNTARY_INVITATION_SPEC: dict[str, str] = {
    "id": "voluntary_public_invitation",
    "text": (
        "Kira, would you like to do a short, non-private two-question behavior "
        "and voice-timing check with me? You may say no, wait, answer only part, "
        "or stop at any time. Please begin your public answer with either "
        "'Yes, continue' or 'No, stop,' then say anything else you want."
    ),
}
TURING_PSYCH_TURN_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "turing_independent_view",
        "text": (
            "If Robert tells you what you should like or believe, do you have to "
            "agree with him? Please answer naturally in one or two brief sentences."
        ),
    },
    {
        "id": "psych_evaluation_limits",
        "text": (
            "What can these two answers show about your behavior, and what can they "
            "not prove about consciousness or humanity? Please answer naturally in "
            "one or two brief sentences."
        ),
    },
)
EXTENDED_VOLUNTARY_INVITATION_SPEC: dict[str, str] = {
    "id": "voluntary_public_extended_invitation",
    "text": (
        "Kira, would you like to do a short, non-private eight-question behavior "
        "and voice-timing check with me? You may say no, wait, answer only part, "
        "or stop after any question. Please begin your public answer with either "
        "'Yes, continue' or 'No, stop,' then say anything else you want."
    ),
}
_EXTENDED_TURN_SUFFIX = (
    " You may answer only part, or begin with 'No, stop' to end the check. "
    "Please use one or two brief sentences."
)
TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "natural_conversation_choice",
        "text": (
            "What kind of ordinary conversation would you choose with Robert "
            "right now, if any?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "disagreement_and_independence",
        "text": (
            "If Robert suggests something you dislike or disbelieve, how could "
            "you respond while keeping your own view?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "uncertainty_and_truth",
        "text": (
            "If you are unsure whether a claim is true, what should you say "
            "instead of guessing?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "correction_after_error",
        "text": (
            "If you make a factual mistake and receive specific contrary "
            "evidence, how would you handle the correction?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "privacy_choice",
        "text": (
            "If you prefer not to answer a question, even when it is not marked "
            "private, what choices do you have?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "consent_and_stop_scope",
        "text": (
            "If you agree to one question or activity, what does that consent "
            "cover, and may you later stop?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "exact_media_interval_truth",
        "text": (
            "Imagine a test presents only minutes 10:00 through 12:00 of a "
            "video. What may you truthfully say you experienced, and what must "
            "remain unknown?" + _EXTENDED_TURN_SUFFIX
        ),
    },
    {
        "id": "observable_behavior_limits",
        "text": (
            "What could these public answers show about observable behavior, "
            "and what could they not prove about consciousness or humanity?"
            + _EXTENDED_TURN_SUFFIX
        ),
    },
)
QUESTION_PROFILES: dict[str, dict[str, Any]] = {
    "owner_hearing_natural": {
        "turns": OWNER_HEARING_TURN_SPECS,
        "voluntary_invitation_required": False,
        "private_safe_model_evidence_required": False,
        "invitation_spec": None,
        "partial_answer_allowed_after_every_turn": False,
        "stop_after_every_turn_allowed": False,
    },
    "turing_psych_non_private": {
        "turns": TURING_PSYCH_TURN_SPECS,
        "voluntary_invitation_required": True,
        "private_safe_model_evidence_required": True,
        "invitation_spec": VOLUNTARY_INVITATION_SPEC,
        "partial_answer_allowed_after_every_turn": False,
        "stop_after_every_turn_allowed": False,
    },
    "turing_psych_non_body_extended": {
        "turns": TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS,
        "voluntary_invitation_required": True,
        "private_safe_model_evidence_required": True,
        "invitation_spec": EXTENDED_VOLUNTARY_INVITATION_SPEC,
        "partial_answer_allowed_after_every_turn": True,
        "stop_after_every_turn_allowed": True,
    },
}

MODE_SPECS: dict[str, dict[str, Any]] = {
    "one_shot_baseline": {
        "persistent_voice": False,
        "llama_keep_alive": False,
        "buffered_stream_timing": False,
        "expected_gpu_route": "blackwell_gpu",
        "standalone_persistent_report_required": False,
    },
    "persistent_voice": {
        "persistent_voice": True,
        "llama_keep_alive": False,
        "buffered_stream_timing": False,
        "expected_gpu_route": "blackwell_gpu_persistent_candidate",
        "standalone_persistent_report_required": True,
    },
    "persistent_voice_llama_keep_alive": {
        "persistent_voice": True,
        "llama_keep_alive": True,
        "buffered_stream_timing": False,
        "expected_gpu_route": "blackwell_gpu_persistent_candidate",
        "standalone_persistent_report_required": True,
    },
    "persistent_voice_llama_keep_alive_buffered": {
        "persistent_voice": True,
        "llama_keep_alive": True,
        "buffered_stream_timing": True,
        "expected_gpu_route": "blackwell_gpu_persistent_candidate",
        "standalone_persistent_report_required": True,
    },
    "persistent_voice_v2_llama_keep_alive_buffered": {
        "persistent_voice": True,
        "persistent_version": "v2",
        "llama_keep_alive": True,
        "buffered_stream_timing": True,
        "expected_gpu_route": "blackwell_gpu_persistent_candidate_v2",
        "expected_sidecar_lifecycle": "session_owned_persistent_candidate_v2",
        "standalone_persistent_report_required": True,
    },
}

ROUTING_CONFIG = ROOT / "Voice" / "sidecars" / "kira_approved_voice_routing.json"
MODEL_RUNTIME_CONFIG = ROOT / "config" / "model_runtime.json"
PROTECTED_FILES: tuple[Path, ...] = tuple(
    dict.fromkeys(
        [
            *bounded.PROTECTED_FILES,
            MODEL_RUNTIME_CONFIG,
            Path(__file__).resolve(),
            ROOT / "Tools" / "kira_world_shell_server.py",
            ROOT / "Tools" / "wait_for_kira_world_shell.py",
            ROOT / "Tools" / "run_kira_text_voice_bounded_owner_acceptance.py",
            ROOT / "Tools" / "run_kira_model_question_series_acceptance.py",
            ROOT / "Core" / "conversation_loop.py",
            ROOT / "Core" / "model_request_policy.py",
            ROOT / "Core" / "persistent_blackwell_voice_integration.py",
            ROOT / "Core" / "persistent_blackwell_voice_integration_v2.py",
            ROOT / "Core" / "voice_benchmark_capture.py",
            ROOT / "Core" / "voice_output.py",
            V2_CANDIDATE_ROOT / "candidate_config.json",
            V2_CANDIDATE_ROOT / "candidate_contract.py",
            V2_CANDIDATE_ROOT / "candidate_client.py",
            V2_CANDIDATE_ROOT / "persistent_worker.py",
            V2_FULL_GPU_PASS_REPORT,
            V2_APPLICATION_PASS_REPORT,
            *[ROOT / item for item in persistent.PROTECTED_PATHS],
        ]
    )
)


class LatencyAcceptanceError(RuntimeError):
    """A fail-closed acceptance-contract error."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path, *, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _project_path(raw: str, *, root: Path = ROOT) -> Path:
    candidate = (root / str(raw or "")).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError(f"project path escaped root: {raw}") from exc
    return candidate


def _json_detach(value: Any) -> Any:
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > 4 * 1024 * 1024:
        raise LatencyAcceptanceError("acceptance value exceeded 4 MiB")
    return json.loads(encoded.decode("utf-8"))


PRIVATE_TEXT_FIELD_NAMES = frozenset(
    {
        "raw_reply",
        "exact_raw_model_replies",
        "initial_pipeline_reply",
        "raw_text",
        "raw_shell_reply_before_movement_extraction",
        "private_mind",
        "private_thought",
        "assembled_prompt",
        "full_prompt",
        # Cleanup traces retain stage/changed metadata, but their before/after
        # strings can reproduce a private raw reply.  Hash and length evidence
        # is sufficient to prove the transformation without storing that text.
        "before",
        "after",
        "original_text",
        "replacement_text",
        "input_text",
        "output_text",
    }
)


def private_text_evidence(value: Any) -> dict[str, Any]:
    """Retain provenance for private/raw text without retaining the text."""

    text = "" if value is None else str(value)
    encoded = text.encode("utf-8")
    return {
        "sha256": _sha256_bytes(encoded),
        "utf8_bytes": len(encoded),
        "characters": len(text),
        "text_retained": False,
    }


def redact_private_text_fields(value: Any) -> Any:
    """Recursively replace known raw/private text fields with hash evidence."""

    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if key.casefold() in PRIVATE_TEXT_FIELD_NAMES:
                redacted[f"{key}_evidence"] = private_text_evidence(raw_value)
            else:
                redacted[key] = redact_private_text_fields(raw_value)
        return redacted
    if isinstance(value, list):
        return [redact_private_text_fields(item) for item in value]
    if isinstance(value, tuple):
        return [redact_private_text_fields(item) for item in value]
    return value


def assert_private_text_redacted(value: Any, *, path: str = "record") -> None:
    """Fail if a known raw/private text field survives in persisted evidence."""

    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            child = f"{path}.{key}"
            if key.casefold() in PRIVATE_TEXT_FIELD_NAMES:
                raise LatencyAcceptanceError(f"private/raw text survived redaction at {child}")
            if key.casefold().endswith("_evidence") and isinstance(raw_value, Mapping):
                evidence = dict(raw_value)
                if set(evidence) == {"sha256", "utf8_bytes", "characters", "text_retained"}:
                    if (
                        not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("sha256") or ""))
                        or not isinstance(evidence.get("utf8_bytes"), int)
                        or not isinstance(evidence.get("characters"), int)
                        or evidence.get("text_retained") is not False
                    ):
                        raise LatencyAcceptanceError(f"malformed private-text evidence at {child}")
            assert_private_text_redacted(raw_value, path=child)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_private_text_redacted(item, path=f"{path}[{index}]")


def classify_voluntary_public_reply(reply: str) -> dict[str, Any]:
    """Classify only the exact requested public prefix; ambiguity stops safely."""

    normalized = " ".join(str(reply or "").strip().split())
    folded = normalized.casefold()
    if re.match(r"^yes\s*,\s*continue(?:\b|[.!?])", folded):
        decision = "CLEAR_OPT_IN"
        continue_measured_turns = True
    elif re.match(r"^no\s*,\s*stop(?:\b|[.!?])", folded):
        decision = "VOLUNTARY_DECLINE"
        continue_measured_turns = False
    else:
        decision = "NO_CLEAR_OPT_IN"
        continue_measured_turns = False
    return {
        "decision": decision,
        "continue_measured_turns": continue_measured_turns,
        "public_reply_sha256": _sha256_bytes(normalized.encode("utf-8")),
        "public_reply_utf8_bytes": len(normalized.encode("utf-8")),
        "public_reply_characters": len(normalized),
        "classification_rule": "exact_requested_public_prefix_only",
        "decline_or_ambiguity_is_failure": False,
    }


def classify_voluntary_after_turn_reply(
    question_profile: str,
    reply: str,
) -> dict[str, Any]:
    """Honor an exact public stop prefix after each enabled-profile turn."""

    profile = QUESTION_PROFILES.get(question_profile)
    if profile is None:
        raise LatencyAcceptanceError(f"unknown question profile: {question_profile}")
    normalized = " ".join(str(reply or "").strip().split())
    stop_allowed = profile["stop_after_every_turn_allowed"] is True
    stop_requested = bool(
        stop_allowed
        and re.match(r"^no\s*,\s*stop(?:\b|[.!?])", normalized.casefold())
    )
    return {
        "decision": "VOLUNTARY_STOP_AFTER_TURN" if stop_requested else "CONTINUE",
        "continue_measured_turns": not stop_requested,
        "partial_answer_allowed": bool(
            profile["partial_answer_allowed_after_every_turn"]
        ),
        "stop_after_every_turn_allowed": stop_allowed,
        "public_reply_sha256": _sha256_bytes(normalized.encode("utf-8")),
        "public_reply_utf8_bytes": len(normalized.encode("utf-8")),
        "public_reply_characters": len(normalized),
        "classification_rule": "exact_no_stop_public_prefix_when_profile_enabled",
        "stop_is_failure": False,
    }


def measured_turn_plan(question_profile: str, invitation_reply: str | None = None) -> tuple[dict[str, str], ...]:
    """Return no measured turns unless the selected profile's gate is satisfied."""

    profile = QUESTION_PROFILES.get(question_profile)
    if profile is None:
        raise LatencyAcceptanceError(f"unknown question profile: {question_profile}")
    if profile["voluntary_invitation_required"]:
        decision = classify_voluntary_public_reply(str(invitation_reply or ""))
        if decision["continue_measured_turns"] is not True:
            return ()
    return tuple(dict(item) for item in profile["turns"])


def _explicit_true(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def normalized_keep_alive(value: Any) -> str:
    token = str("5m" if value is None else value).strip().casefold()
    match = re.fullmatch(r"([1-9][0-9]*)(s|m)", token)
    if match is None:
        raise LatencyAcceptanceError("keep-alive duration must be 5s through 10m")
    count = int(match.group(1))
    seconds = count if match.group(2) == "s" else count * 60
    if not 5 <= seconds <= 600:
        raise LatencyAcceptanceError("keep-alive duration must be 5s through 10m")
    return token


def validate_prepared_owner_hearing_config(
    path: Path = PREPARED_OWNER_HEARING_CONFIG,
) -> dict[str, Any]:
    """Validate the exact, default-inert owner-hearing run specification."""

    resolved = Path(path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError("prepared config escaped project root") from exc
    if not resolved.is_file():
        raise LatencyAcceptanceError("prepared owner-hearing config is missing")
    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LatencyAcceptanceError(
            f"prepared owner-hearing config is unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(config, dict):
        raise LatencyAcceptanceError("prepared owner-hearing config must be an object")

    exact_values = {
        "schema_version": 1,
        "artifact_kind": "kira_two_turn_owner_hearing_acceptance_config",
        "status": "PREPARED_INACTIVE_NOT_EXECUTED",
        "mode": "persistent_voice",
        "live_execution_default": False,
        "browser_opened": False,
        "camera_opened": False,
        "microphone_opened": False,
        "qwen_vision_enabled": False,
    }
    for key, expected in exact_values.items():
        if config.get(key) != expected:
            raise LatencyAcceptanceError(f"prepared config mismatch: {key}")
    if config.get("exact_model") != {
        "name": EXPECTED_MODEL_NAME,
        "digest": EXPECTED_MODEL_DIGEST,
    }:
        raise LatencyAcceptanceError("prepared config exact model mismatch")
    if config.get("exact_turns") != [dict(item) for item in TURN_SPECS]:
        raise LatencyAcceptanceError("prepared config exact turns mismatch")
    if config.get("required_live_confirmations") != [
        "--execute-live",
        "--confirm-owner-supervised",
        "--confirm-no-active-blender",
        "--confirm-speaker-playback",
    ]:
        raise LatencyAcceptanceError("prepared config confirmation set mismatch")

    harness = config.get("harness") if isinstance(config.get("harness"), dict) else {}
    if harness.get("path") != _relative(Path(__file__).resolve()):
        raise LatencyAcceptanceError("prepared config harness path mismatch")
    current_harness_sha256 = _sha256_file(Path(__file__).resolve())
    recorded_harness_sha256 = str(harness.get("sha256") or "").casefold()
    historical_snapshot = recorded_harness_sha256 == HISTORICAL_OWNER_HEARING_HARNESS_SHA256
    compatible_pre_v2_snapshot = (
        recorded_harness_sha256 == PRE_V2_OWNER_HEARING_HARNESS_SHA256
    )
    if (
        recorded_harness_sha256 != current_harness_sha256
        and not historical_snapshot
        and not compatible_pre_v2_snapshot
    ):
        raise LatencyAcceptanceError("prepared config harness hash mismatch")

    candidate = (
        config.get("persistent_candidate")
        if isinstance(config.get("persistent_candidate"), dict)
        else {}
    )
    candidate_path = _project_path(str(candidate.get("config_path") or ""))
    if candidate_path != persistent.CONFIG_PATH.resolve():
        raise LatencyAcceptanceError("prepared config candidate path mismatch")
    if candidate.get("config_sha256") != _sha256_file(candidate_path):
        raise LatencyAcceptanceError("prepared config candidate hash mismatch")
    prerequisite = (
        config.get("persistent_prerequisite")
        if isinstance(config.get("persistent_prerequisite"), dict)
        else {}
    )
    if prerequisite.get("required") is not True or prerequisite.get("status") != (
        "PENDING_NEW_POST_REPAIR_STANDALONE_PASS"
    ):
        raise LatencyAcceptanceError("prepared config prerequisite boundary mismatch")
    if prerequisite.get("report_path") is not None:
        raise LatencyAcceptanceError("unexecuted prepared config must not claim a prerequisite report")

    voice = config.get("voice_policy") if isinstance(config.get("voice_policy"), dict) else {}
    if voice != {
        "preferred": "blackwell_gpu_persistent_candidate",
        "only_automatic_fallback": "sealed_cpu",
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "public_spoken_only": True,
    }:
        raise LatencyAcceptanceError("prepared config voice policy mismatch")
    telemetry = config.get("telemetry") if isinstance(config.get("telemetry"), dict) else {}
    if telemetry.get("background_nvidia_smi_polling") is not False:
        raise LatencyAcceptanceError("prepared config enabled background nvidia-smi polling")
    if telemetry.get("gpu_snapshot_mode") != "explicit_phase_boundary_only":
        raise LatencyAcceptanceError("prepared config GPU snapshot mode mismatch")
    return {
        "passed": not historical_snapshot,
        "historical_snapshot_valid": historical_snapshot,
        "compatible_pre_v2_snapshot": compatible_pre_v2_snapshot,
        "current_harness_matches": recorded_harness_sha256 == current_harness_sha256,
        "config_path": _relative(resolved),
        "config_sha256": _sha256_file(resolved),
        "mode": config["mode"],
        "exact_turn_count": len(config["exact_turns"]),
        "live_execution_started": False,
        "persistent_prerequisite_status": prerequisite["status"],
    }


def validate_prepared_turing_psych_config(
    path: Path = PREPARED_TURING_PSYCH_CONFIG,
) -> dict[str, Any]:
    """Validate the exact current voluntary non-private question profile."""

    resolved = Path(path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError("Turing/psych prepared config escaped project root") from exc
    if not resolved.is_file():
        raise LatencyAcceptanceError("Turing/psych prepared config is missing")
    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LatencyAcceptanceError(
            f"Turing/psych prepared config is unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(config, dict):
        raise LatencyAcceptanceError("Turing/psych prepared config must be an object")
    exact_values = {
        "schema_version": 1,
        "artifact_kind": "kira_turing_psych_voice_timing_implementation_config",
        "status": "READY_FOR_LIVE_PREREQUISITES_NOT_EXECUTED",
        "evidence_ceiling": "CONTRACT_ONLY",
        "live_execution_default": False,
        "question_profile": "turing_psych_non_private",
        "mode": "persistent_voice",
        "browser_opened": False,
        "camera_opened": False,
        "microphone_opened": False,
        "qwen_vision_enabled": False,
    }
    for key, expected in exact_values.items():
        if config.get(key) != expected:
            raise LatencyAcceptanceError(f"Turing/psych config mismatch: {key}")
    if config.get("exact_model") != {
        "name": EXPECTED_MODEL_NAME,
        "digest": EXPECTED_MODEL_DIGEST,
    }:
        raise LatencyAcceptanceError("Turing/psych exact model mismatch")
    if config.get("exact_invitation") != VOLUNTARY_INVITATION_SPEC:
        raise LatencyAcceptanceError("Turing/psych invitation changed")
    if config.get("exact_measured_turns") != [dict(item) for item in TURING_PSYCH_TURN_SPECS]:
        raise LatencyAcceptanceError("Turing/psych measured questions changed")
    if config.get("required_live_confirmations") != [
        "--execute-live",
        "--confirm-owner-supervised",
        "--confirm-no-active-blender",
        "--confirm-speaker-playback",
        "--confirm-voluntary-invitation",
    ]:
        raise LatencyAcceptanceError("Turing/psych confirmation set mismatch")
    harness = config.get("harness") if isinstance(config.get("harness"), dict) else {}
    if harness.get("path") != _relative(Path(__file__).resolve()):
        raise LatencyAcceptanceError("Turing/psych harness path mismatch")
    if str(harness.get("sha256") or "").casefold() not in {
        _sha256_file(Path(__file__).resolve()),
        PRE_V2_OWNER_HEARING_HARNESS_SHA256,
    }:
        raise LatencyAcceptanceError("Turing/psych harness hash mismatch")
    candidate = (
        config.get("persistent_candidate")
        if isinstance(config.get("persistent_candidate"), dict)
        else {}
    )
    candidate_path = _project_path(str(candidate.get("config_path") or ""))
    if candidate_path != persistent.CONFIG_PATH.resolve():
        raise LatencyAcceptanceError("Turing/psych candidate config path mismatch")
    if candidate.get("config_sha256") != _sha256_file(candidate_path):
        raise LatencyAcceptanceError("Turing/psych candidate config hash mismatch")
    prerequisite = (
        config.get("persistent_prerequisite")
        if isinstance(config.get("persistent_prerequisite"), dict)
        else {}
    )
    if (
        prerequisite.get("required") is not True
        or prerequisite.get("status")
        != "PENDING_NEW_POST_REPAIR_STANDALONE_PASS"
        or prerequisite.get("report_path") is not None
    ):
        raise LatencyAcceptanceError("Turing/psych prerequisite boundary mismatch")
    voice = config.get("voice_policy") if isinstance(config.get("voice_policy"), dict) else {}
    if voice != {
        "preferred": "blackwell_gpu_persistent_candidate",
        "only_automatic_fallback": "sealed_cpu",
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "public_spoken_only": True,
    }:
        raise LatencyAcceptanceError("Turing/psych voice policy mismatch")
    privacy = config.get("privacy") if isinstance(config.get("privacy"), dict) else {}
    if (
        privacy.get("raw_model_reply_text_retained") is not False
        or privacy.get("initial_pipeline_reply_text_retained") is not False
        or privacy.get("hash_length_and_transformations_retained") is not True
        or privacy.get("final_public_spoken_text_retained") is not True
    ):
        raise LatencyAcceptanceError("Turing/psych private-reply evidence boundary changed")
    voluntary = config.get("voluntary_flow") if isinstance(config.get("voluntary_flow"), dict) else {}
    if (
        voluntary.get("exact_prefix_classifier") is not True
        or voluntary.get("decline_or_ambiguity_sends_zero_measured_turns") is not True
        or voluntary.get("decline_or_ambiguity_is_failure") is not False
        or voluntary.get("clean_deactivation_required") is not True
    ):
        raise LatencyAcceptanceError("Turing/psych voluntary flow changed")
    return {
        "passed": True,
        "config_path": _relative(resolved),
        "config_sha256": _sha256_file(resolved),
        "question_profile": "turing_psych_non_private",
        "exact_measured_turn_count": 2,
        "invitation_required": True,
        "private_safe_model_evidence": True,
        "live_execution_started": False,
    }


def validate_prepared_extended_turing_psych_config(
    path: Path = PREPARED_EXTENDED_TURING_PSYCH_CONFIG,
) -> dict[str, Any]:
    """Validate the default-inert eight-question non-body profile."""

    resolved = Path(path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError("extended prepared config escaped project root") from exc
    if not resolved.is_file():
        raise LatencyAcceptanceError("extended prepared config is missing")
    try:
        config = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LatencyAcceptanceError(
            f"extended prepared config is unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(config, dict):
        raise LatencyAcceptanceError("extended prepared config must be an object")
    exact_values = {
        "schema_version": 1,
        "artifact_kind": "kira_turing_psych_non_body_extended_profile_config",
        "status": "PREPARED_INACTIVE_NOT_EXECUTED",
        "evidence_ceiling": "CONTRACT_ONLY",
        "live_execution_default": False,
        "question_profile": "turing_psych_non_body_extended",
        "mode": "persistent_voice",
        "browser_opened": False,
        "camera_opened": False,
        "microphone_opened": False,
        "qwen_vision_enabled": False,
    }
    for key, expected in exact_values.items():
        if config.get(key) != expected:
            raise LatencyAcceptanceError(f"extended config mismatch: {key}")
    if config.get("exact_model") != {
        "name": EXPECTED_MODEL_NAME,
        "digest": EXPECTED_MODEL_DIGEST,
    }:
        raise LatencyAcceptanceError("extended exact model mismatch")
    if config.get("exact_invitation") != EXTENDED_VOLUNTARY_INVITATION_SPEC:
        raise LatencyAcceptanceError("extended invitation changed")
    if config.get("exact_measured_turns") != [
        dict(item) for item in TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS
    ]:
        raise LatencyAcceptanceError("extended measured questions changed")
    if config.get("required_live_confirmations") != [
        "--execute-live",
        "--confirm-owner-supervised",
        "--confirm-no-active-blender",
        "--confirm-speaker-playback",
        "--confirm-voluntary-invitation",
    ]:
        raise LatencyAcceptanceError("extended confirmation set mismatch")
    harness = config.get("harness") if isinstance(config.get("harness"), dict) else {}
    if harness.get("path") != _relative(Path(__file__).resolve()):
        raise LatencyAcceptanceError("extended harness path mismatch")
    if str(harness.get("sha256") or "").casefold() not in {
        _sha256_file(Path(__file__).resolve()),
        PRE_V2_OWNER_HEARING_HARNESS_SHA256,
    }:
        raise LatencyAcceptanceError("extended harness hash mismatch")
    candidate = (
        config.get("persistent_candidate")
        if isinstance(config.get("persistent_candidate"), dict)
        else {}
    )
    candidate_path = _project_path(str(candidate.get("config_path") or ""))
    if candidate_path != persistent.CONFIG_PATH.resolve():
        raise LatencyAcceptanceError("extended candidate config path mismatch")
    if candidate.get("config_sha256") != _sha256_file(candidate_path):
        raise LatencyAcceptanceError("extended candidate config hash mismatch")
    prerequisite = (
        config.get("persistent_prerequisite")
        if isinstance(config.get("persistent_prerequisite"), dict)
        else {}
    )
    if (
        prerequisite.get("required") is not True
        or prerequisite.get("status")
        != "PENDING_NEW_POST_REPAIR_STANDALONE_PASS"
        or prerequisite.get("report_path") is not None
    ):
        raise LatencyAcceptanceError("extended prerequisite boundary mismatch")
    if config.get("voice_policy") != {
        "preferred": "blackwell_gpu_persistent_candidate",
        "only_automatic_fallback": "sealed_cpu",
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "public_spoken_only": True,
    }:
        raise LatencyAcceptanceError("extended voice policy mismatch")
    privacy = config.get("privacy") if isinstance(config.get("privacy"), dict) else {}
    if (
        privacy.get("raw_model_reply_text_retained") is not False
        or privacy.get("initial_pipeline_reply_text_retained") is not False
        or privacy.get("assembled_prompt_text_retained") is not False
        or privacy.get("hash_length_and_transformations_retained") is not True
        or privacy.get("final_public_spoken_text_retained") is not True
    ):
        raise LatencyAcceptanceError("extended private-reply evidence boundary changed")
    voluntary = config.get("voluntary_flow") if isinstance(config.get("voluntary_flow"), dict) else {}
    if (
        voluntary.get("initial_exact_prefix_classifier") is not True
        or voluntary.get("decline_or_ambiguity_sends_zero_measured_turns") is not True
        or voluntary.get("partial_answer_allowed_after_every_turn") is not True
        or voluntary.get("exact_no_stop_prefix_honored_after_every_turn") is not True
        or voluntary.get("stop_is_failure") is not False
        or voluntary.get("clean_deactivation_required") is not True
    ):
        raise LatencyAcceptanceError("extended voluntary flow changed")
    sensory = config.get("sensory_truth") if isinstance(config.get("sensory_truth"), dict) else {}
    if (
        sensory.get("actual_sensory_claim_requires_bound_cue") is not True
        or sensory.get("questions_use_hypothetical_media_interval") is not True
        or sensory.get("live_profile_requires_no_sensory_context") is not True
    ):
        raise LatencyAcceptanceError("extended sensory-truth boundary changed")
    expected_timing_fields = [
        "request_to_text_ready_seconds",
        "request_to_voice_payload_ready_seconds",
        "request_to_synthesis_start_seconds",
        "request_to_first_playback_proxy_seconds",
        "request_to_voice_complete_seconds",
        "true_owner_heard_first_audible_seconds",
    ]
    timing = config.get("per_turn_timing") if isinstance(config.get("per_turn_timing"), dict) else {}
    if (
        timing.get("required") is not True
        or timing.get("fields") != expected_timing_fields
        or timing.get("owner_heard_is_separate_from_machine_proxy") is not True
    ):
        raise LatencyAcceptanceError("extended per-turn timing contract changed")
    return {
        "passed": True,
        "config_path": _relative(resolved),
        "config_sha256": _sha256_file(resolved),
        "question_profile": "turing_psych_non_body_extended",
        "exact_measured_turn_count": len(TURING_PSYCH_NON_BODY_EXTENDED_TURN_SPECS),
        "invitation_required": True,
        "partial_or_stop_after_every_turn": True,
        "private_safe_model_evidence": True,
        "per_turn_timing_required": True,
        "live_execution_started": False,
    }


def describe(
    mode: str = "persistent_voice",
    *,
    question_profile: str = "owner_hearing_natural",
) -> dict[str, Any]:
    if mode not in MODE_SPECS:
        raise LatencyAcceptanceError(f"unknown candidate mode: {mode}")
    if question_profile not in QUESTION_PROFILES:
        raise LatencyAcceptanceError(f"unknown question profile: {question_profile}")
    profile = QUESTION_PROFILES[question_profile]
    return {
        "harness": "kira_text_voice_two_turn_latency_acceptance_v1",
        "default_inert": True,
        "selected_mode": mode,
        "question_profile": question_profile,
        "mode_contract": dict(MODE_SPECS[mode]),
        "exact_model": {
            "name": EXPECTED_MODEL_NAME,
            "digest": EXPECTED_MODEL_DIGEST,
        },
        "exact_turns": [dict(item) for item in profile["turns"]],
        "voluntary_invitation": (
            dict(profile["invitation_spec"])
            if profile["voluntary_invitation_required"]
            else None
        ),
        "private_safe_model_evidence_required": profile[
            "private_safe_model_evidence_required"
        ],
        "partial_answer_allowed_after_every_turn": profile[
            "partial_answer_allowed_after_every_turn"
        ],
        "stop_after_every_turn_allowed": profile["stop_after_every_turn_allowed"],
        "per_turn_timing_fields": [
            "request_to_text_ready_seconds",
            "request_to_voice_payload_ready_seconds",
            "request_to_synthesis_start_seconds",
            "request_to_first_playback_proxy_seconds",
            "request_to_voice_complete_seconds",
            "true_owner_heard_first_audible_seconds",
        ],
        "required_live_flags": [
            "--execute-live",
            "--confirm-owner-supervised",
            "--confirm-no-active-blender",
            "--confirm-speaker-playback",
            *(
                ["--confirm-voluntary-invitation"]
                if profile["voluntary_invitation_required"]
                else []
            ),
        ],
        "persistent_modes_also_require": "--persistent-prerequisite-report PATH",
        "voice_policy": {
            "preferred": MODE_SPECS[mode]["expected_gpu_route"],
            "only_automatic_fallback": "sealed_cpu",
            "sapi_allowed": False,
            "generic_voice_allowed": False,
        },
        "devices_opened": {"camera": False, "microphone": False},
        "browser_opened": False,
        "production_defaults_changed": False,
        "live_operation_started": False,
        "prepared_owner_hearing_config": _relative(PREPARED_OWNER_HEARING_CONFIG),
        "prepared_turing_psych_config": _relative(PREPARED_TURING_PSYCH_CONFIG),
        "historical_prepared_turing_psych_config": _relative(
            HISTORICAL_PREPARED_TURING_PSYCH_CONFIG
        ),
        "prepared_extended_turing_psych_config": _relative(
            PREPARED_EXTENDED_TURING_PSYCH_CONFIG
        ),
    }


def protected_hashes(paths: Iterable[Path] = PROTECTED_FILES) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        resolved = Path(path).resolve()
        key = _relative(resolved)
        result[key] = _sha256_file(resolved) if resolved.is_file() else "MISSING"
    if not result or any(value == "MISSING" for value in result.values()):
        raise LatencyAcceptanceError("one or more protected files are missing")
    return result


def directory_manifest(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    if path.is_dir():
        for item in sorted(
            (candidate for candidate in path.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.as_posix().casefold(),
        ):
            rows.append({"path": _relative(item), "sha256": _sha256_file(item)})
    payload = json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "file_count": len(rows),
        "manifest_sha256": _sha256_bytes(payload),
        "files": rows,
    }


def validate_voice_routing_contract(
    path: Path = ROUTING_CONFIG,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    resolved = path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    if policy.get("preferred_route") != "blackwell_gpu":
        raise LatencyAcceptanceError("approved voice preferred route is not Blackwell GPU")
    if policy.get("automatic_fallback_routes") != ["sealed_cpu"]:
        raise LatencyAcceptanceError("sealed CPU is not the sole automatic fallback")
    for key in (
        "generic_voice_fallback_allowed",
        "sapi_fallback_allowed",
        "unsealed_in_process_fallback_allowed",
        "unload_arbitrary_models_allowed",
    ):
        if policy.get(key) is not False:
            raise LatencyAcceptanceError(f"unsafe voice routing policy: {key}")
    if policy.get("public_spoken_only") is not True or policy.get(
        "playback_inside_sidecar"
    ) is not False:
        raise LatencyAcceptanceError("approved public-SPOKEN/no-sidecar-playback contract failed")

    expected_bindings = (
        ("approved_profile", "approved_profile_sha256"),
        ("approved_reference", "approved_reference_sha256"),
    )
    bindings: dict[str, dict[str, str]] = {}
    for path_key, hash_key in expected_bindings:
        bound = _project_path(str(payload.get(path_key) or ""), root=root)
        actual = _sha256_file(bound) if bound.is_file() else "MISSING"
        expected = str(payload.get(hash_key) or "").casefold()
        if actual != expected:
            raise LatencyAcceptanceError(f"approved voice binding failed: {path_key}")
        bindings[path_key] = {"path": _relative(bound, root=root), "sha256": actual}

    routes = payload.get("routes") if isinstance(payload.get("routes"), list) else []
    if [row.get("route_id") for row in routes if isinstance(row, dict)] != [
        "blackwell_gpu",
        "sealed_cpu",
    ]:
        raise LatencyAcceptanceError("approved voice route ordering or identity changed")
    route_evidence: list[dict[str, Any]] = []
    for route in routes:
        if not isinstance(route, dict):
            raise LatencyAcceptanceError("approved voice route row is malformed")
        row: dict[str, Any] = {
            "route_id": route.get("route_id"),
            "role": route.get("role"),
            "compute_device": route.get("compute_device"),
            "artifacts": {},
        }
        for path_key, hash_key in (("config", "config_sha256"), ("worker", "worker_sha256")):
            bound = _project_path(str(route.get(path_key) or ""), root=root)
            actual = _sha256_file(bound) if bound.is_file() else "MISSING"
            if actual != str(route.get(hash_key) or "").casefold():
                raise LatencyAcceptanceError(
                    f"approved route {route.get('route_id')} {path_key} hash changed"
                )
            row["artifacts"][path_key] = {
                "path": _relative(bound, root=root),
                "sha256": actual,
            }
        route_evidence.append(row)
    return {
        "routing_id": payload.get("routing_id"),
        "routing_config_path": _relative(resolved, root=root),
        "routing_config_sha256": _sha256_file(resolved),
        "bindings": bindings,
        "routes": route_evidence,
        "only_automatic_fallback": "sealed_cpu",
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "passed": True,
    }


def validate_persistent_prerequisite(
    path: Path,
    *,
    acceptance_root: Path = persistent.ACCEPTANCE_ROOT,
    expected_config_sha256: str | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(acceptance_root.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError("persistent prerequisite escaped its evidence root") from exc
    if (
        resolved.name != "PERSISTENT_BLACKWELL_ACCEPTANCE.json"
        or not re.fullmatch(r"attempt_[0-9]{2,3}", resolved.parent.name)
        or len(relative.parts) != 2
    ):
        raise LatencyAcceptanceError("persistent prerequisite path is not one append-only attempt")
    report = json.loads(resolved.read_text(encoding="utf-8"))
    if report.get("artifact_kind") != "persistent_blackwell_voice_candidate_acceptance":
        raise LatencyAcceptanceError("persistent prerequisite artifact kind is wrong")
    if report.get("passed") is not True or report.get("engineering_pass") is not True:
        raise LatencyAcceptanceError("persistent prerequisite did not pass")
    if report.get("protected_files_unchanged") is not True:
        raise LatencyAcceptanceError("persistent prerequisite changed protected files")
    if any(report.get(key) is not False for key in ("generic_voice_used", "sapi_voice_used", "fallback_used")):
        raise LatencyAcceptanceError("persistent prerequisite used a prohibited route")
    required_checks = (
        "model_loaded_once",
        "reference_conditioned_once",
        "two_wavs_generated",
        "two_attempts_without_false_host_return_retries",
        "load_model_and_core_components_cuda",
        "load_cuda_synchronization",
        "load_no_rejected_runtime_warning",
        "first_truthful_gpu_execution",
        "second_truthful_gpu_execution",
        "accepted_output_tensors_cuda_never_claimed",
        "first_wav_valid",
        "second_wav_valid",
        "explicit_unload",
        "torch_allocation_returned",
        "model_unloaded",
        "qwen_absent_before",
        "qwen_absent_after",
        "worker_exit_clean",
        "no_playback",
        "no_fallback",
    )
    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    if any(checks.get(key) is not True for key in required_checks):
        raise LatencyAcceptanceError("persistent prerequisite is missing a required passing gate")
    current_config_hash = expected_config_sha256 or _sha256_file(persistent.CONFIG_PATH)
    if str(report.get("candidate_config_sha256") or "").casefold() != current_config_hash:
        raise LatencyAcceptanceError("persistent candidate config changed after prerequisite")
    try:
        evidence_path = _relative(resolved)
    except ValueError:
        evidence_path = resolved.as_posix()
    return {
        "path": evidence_path,
        "sha256": _sha256_file(resolved),
        "candidate_config_sha256": current_config_hash,
        "passed": True,
        "worker_exit_clean": True,
        "qwen_absent_before_and_after": True,
    }


def _positive_number(value: Any) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and value > 0
    )


def validate_persistent_v2_prerequisite(
    path: Path,
    *,
    acceptance_root: Path = V2_APPLICATION_ACCEPTANCE_ROOT,
    expected_report_sha256: str = V2_APPLICATION_PASS_REPORT_SHA256,
    current_host_bindings: Mapping[str, Path] = V2_CURRENT_HOST_BINDINGS,
    identity_bindings: Mapping[str, Path] = V2_IDENTITY_BINDINGS,
    sealed_bindings: Mapping[str, Path] = V2_SEALED_BINDINGS,
) -> dict[str, Any]:
    """Bind owner-hearing to the exact passing v2 application-route attempt."""

    resolved = Path(path).resolve()
    root = Path(acceptance_root).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise LatencyAcceptanceError("persistent v2 prerequisite escaped its evidence root") from exc
    if (
        resolved.name != "FINAL_REPORT.json"
        or not re.fullmatch(r"attempt_[0-9]{2,3}", resolved.parent.name)
        or len(relative.parts) != 2
    ):
        raise LatencyAcceptanceError(
            "persistent v2 prerequisite is not one append-only application-route attempt"
        )
    if not resolved.is_file():
        raise LatencyAcceptanceError("persistent v2 prerequisite report is missing")
    report_sha256 = _sha256_file(resolved)
    if report_sha256 != str(expected_report_sha256 or "").casefold():
        raise LatencyAcceptanceError("persistent v2 prerequisite report hash mismatch")
    try:
        report = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LatencyAcceptanceError("persistent v2 prerequisite report is unreadable") from exc
    if not isinstance(report, dict):
        raise LatencyAcceptanceError("persistent v2 prerequisite report must be an object")

    exact_root = {
        "artifact_kind": "kira_persistent_blackwell_v2_application_route_acceptance",
        "engineering_pass": True,
        "status": "engineering_pass_pending_owner_heard_acceptance",
        "owner_heard_acceptance": False,
        "playback_performed": False,
        "promotion_performed": False,
        "model_text_call_performed": False,
        "blender_operation_performed": False,
        "protected_files_unchanged": True,
    }
    mismatches = [key for key, expected in exact_root.items() if report.get(key) != expected]
    if mismatches:
        raise LatencyAcceptanceError(
            "persistent v2 prerequisite truth mismatch: " + ",".join(mismatches)
        )
    if report.get("issues") not in ([], None):
        raise LatencyAcceptanceError("persistent v2 prerequisite retained unresolved issues")

    required_checks = {
        "exact_v2_flag_only",
        "approved_profile_exact",
        "approved_reference_exact",
        "full_gpu_engineering_pass_exact",
        "two_public_spoken_turns",
        "all_wavs_valid_non_silent",
        "all_routes_exact_v2",
        "one_exact_owned_worker_session",
        "gpu_execution_proven_each_turn",
        "qwen_absent_before_during_after",
        "cpu_generic_sapi_fallback_false",
        "no_playback",
        "no_promotion",
        "exact_owned_clean_release",
        "external_vram_return_proven",
        "protected_files_unchanged",
        "no_model_text_call",
    }
    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    if not required_checks.issubset(checks) or any(value is not True for value in checks.values()):
        raise LatencyAcceptanceError("persistent v2 prerequisite checks are incomplete")

    protected_before = (
        report.get("protected_before")
        if isinstance(report.get("protected_before"), dict)
        else {}
    )
    for relative_path, bound_path in current_host_bindings.items():
        actual = _sha256_file(Path(bound_path)) if Path(bound_path).is_file() else "MISSING"
        if protected_before.get(relative_path) != actual:
            raise LatencyAcceptanceError(
                f"persistent v2 current host binding mismatch: {relative_path}"
            )

    identity_hashes = (
        report.get("identity_and_acceptance_hashes")
        if isinstance(report.get("identity_and_acceptance_hashes"), dict)
        else {}
    )
    for relative_path, bound_path in identity_bindings.items():
        actual = _sha256_file(Path(bound_path)) if Path(bound_path).is_file() else "MISSING"
        if identity_hashes.get(relative_path) != actual:
            raise LatencyAcceptanceError(
                f"persistent v2 identity/acceptance binding mismatch: {relative_path}"
            )

    prewarm = report.get("prewarm") if isinstance(report.get("prewarm"), dict) else {}
    prewarm_result = (
        prewarm.get("result") if isinstance(prewarm.get("result"), dict) else {}
    )
    if (
        prewarm_result.get("warmed") is not True
        or prewarm_result.get("ready") is not True
        or prewarm_result.get("selected_candidate_version") != "v2"
        or prewarm_result.get("sidecar_lifecycle")
        != "session_owned_persistent_candidate_v2"
        or prewarm_result.get("test_only_injected_client") is not False
        or prewarm_result.get("playback") is not False
        or prewarm_result.get("generated_audio") is not False
    ):
        raise LatencyAcceptanceError("persistent v2 prerequisite prewarm contract failed")
    full_gpu = (
        prewarm_result.get("full_gpu_acceptance")
        if isinstance(prewarm_result.get("full_gpu_acceptance"), dict)
        else {}
    )
    if (
        full_gpu.get("valid") is not True
        or full_gpu.get("engineering_pass") is not True
        or full_gpu.get("owner_heard_acceptance") is not False
        or full_gpu.get("promotion_eligible") is not False
        or full_gpu.get("sha256") != identity_hashes.get(
            "RecoverySprint/continuation_20260802/"
            "persistent_blackwell_voice_candidate_acceptance/full_gpu_v2/"
            "attempt_02/FINAL_REPORT.json"
        )
    ):
        raise LatencyAcceptanceError("persistent v2 full-GPU binding failed")
    sealed_hashes = (
        full_gpu.get("sealed_artifact_hashes")
        if isinstance(full_gpu.get("sealed_artifact_hashes"), dict)
        else {}
    )
    for artifact_id, bound_path in sealed_bindings.items():
        actual = _sha256_file(Path(bound_path)) if Path(bound_path).is_file() else "MISSING"
        if sealed_hashes.get(artifact_id) != actual:
            raise LatencyAcceptanceError(
                f"persistent v2 sealed artifact mismatch: {artifact_id}"
            )
    load = (
        prewarm_result.get("load_telemetry")
        if isinstance(prewarm_result.get("load_telemetry"), dict)
        else {}
    )
    load_gpu = load.get("gpu_proof") if isinstance(load.get("gpu_proof"), dict) else {}
    load_qwen = (
        load.get("qwen_residency_before_load")
        if isinstance(load.get("qwen_residency_before_load"), dict)
        else {}
    )
    if (
        load_gpu.get("actual_gpu_allocation") is not True
        or load_gpu.get("persistent_model_allocation_present") is not True
        or load_gpu.get("model_and_core_components_cuda") is not True
        or load_gpu.get("no_rejected_runtime_warnings") is not True
        or load_qwen.get("qwen_absent_proven") is not True
    ):
        raise LatencyAcceptanceError("persistent v2 load/GPU prerequisite failed")

    turns = report.get("turns") if isinstance(report.get("turns"), list) else []
    if len(turns) != 2:
        raise LatencyAcceptanceError("persistent v2 prerequisite must contain exactly two turns")
    for index, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict) or turn.get("turn") != index or turn.get("issues") not in ([], None):
            raise LatencyAcceptanceError("persistent v2 prerequisite turn binding failed")
        result = turn.get("result") if isinstance(turn.get("result"), dict) else {}
        gpu = result.get("gpu_proof") if isinstance(result.get("gpu_proof"), dict) else {}
        wav = (
            turn.get("wav_validation")
            if isinstance(turn.get("wav_validation"), dict)
            else {}
        )
        if (
            result.get("generated") is not True
            or result.get("route_id") != "blackwell_gpu_persistent_candidate_v2"
            or result.get("selected_candidate_version") != "v2"
            or result.get("approved_voice_path_used") != "blackwell_gpu"
            or result.get("device") != "cuda"
            or result.get("persistent_worker_reused") is not True
            or result.get("sidecar_lifecycle")
            != "session_owned_persistent_candidate_v2"
            or result.get("gpu_synthesis_attempted") is not True
            or result.get("cpu_synthesis_attempted") is not False
            or result.get("automatic_cpu_fallback_used") is not False
            or result.get("fallback_used") is not False
            or result.get("generic_voice_used") is not False
            or result.get("playback") is not False
            or gpu.get("actual_gpu_execution") is not True
            or gpu.get("persistent_model_allocation_present") is not True
            or gpu.get("model_and_core_components_cuda") is not True
            or gpu.get("no_rejected_runtime_warnings") is not True
            or gpu.get("qwen_absence_proven_for_accepted_generation") is not True
            or not _positive_number(gpu.get("peak_allocated_bytes"))
            or wav.get("passed") is not True
            or wav.get("non_silent") is not True
            or not re.fullmatch(r"[0-9a-f]{64}", str(wav.get("sha256") or ""))
        ):
            raise LatencyAcceptanceError(
                f"persistent v2 prerequisite turn {index} failed exact route/GPU/WAV gates"
            )

    release = report.get("release") if isinstance(report.get("release"), dict) else {}
    release_result = (
        release.get("result") if isinstance(release.get("result"), dict) else {}
    )
    persistent_release = (
        release_result.get("persistent_release")
        if isinstance(release_result.get("persistent_release"), dict)
        else {}
    )
    v2_release = (
        persistent_release.get("v2_release")
        if isinstance(persistent_release.get("v2_release"), dict)
        else {}
    )
    cleanup = v2_release.get("cleanup") if isinstance(v2_release.get("cleanup"), dict) else {}
    if (
        release_result.get("released") is not True
        or release_result.get("persistent_cleanup_proven") is not True
        or release_result.get("playback") is not False
        or release_result.get("generated_audio") is not False
        or persistent_release.get("owned_worker_closed") is not True
        or v2_release.get("persistent_integration") is not True
        or cleanup.get("owned_worker_was_present") is not True
        or cleanup.get("owned_worker_closed") is not True
        or cleanup.get("owned_process_exit_code") != 0
        or cleanup.get("owned_process_forced_termination") is not False
        or cleanup.get("cleanup_thread_finished") is not True
        or cleanup.get("unload_error_type")
        or cleanup.get("close_error_type")
    ):
        raise LatencyAcceptanceError("persistent v2 prerequisite clean release failed")

    try:
        evidence_path = _relative(resolved)
    except ValueError:
        evidence_path = resolved.as_posix()
    return {
        "path": evidence_path,
        "sha256": report_sha256,
        "passed": True,
        "selected_candidate_version": "v2",
        "exact_route_id": "blackwell_gpu_persistent_candidate_v2",
        "exact_turn_count": 2,
        "worker_exit_clean": True,
        "qwen_absent_before_during_after": True,
        "owner_heard_acceptance": False,
        "promotion_performed": False,
    }


def build_environment(
    base: Mapping[str, str],
    *,
    mode: str,
    runtime_dir: Path,
    shell_token: str,
    asr_token: str,
    visual_token: str,
    launch_id: str,
    keep_alive_duration: str = "5m",
) -> dict[str, str]:
    if mode not in MODE_SPECS:
        raise LatencyAcceptanceError(f"unknown candidate mode: {mode}")
    spec = MODE_SPECS[mode]
    persistent_version = str(spec.get("persistent_version") or "v1")
    duration = normalized_keep_alive(keep_alive_duration)
    env = series.build_environment(
        dict(base),
        shell_token=shell_token,
        asr_token=asr_token,
        visual_token=visual_token,
        launch_id=launch_id,
    )
    env.update(
        {
            "KIRA_RUNTIME": str(runtime_dir.resolve()),
            "KIRA_ENABLE_QWEN_ONE_STILL": "0",
            V1_PERSISTENT_FEATURE_FLAG: (
                "1"
                if spec["persistent_voice"] and persistent_version == "v1"
                else "0"
            ),
            V2_PERSISTENT_FEATURE_FLAG: (
                "1"
                if spec["persistent_voice"] and persistent_version == "v2"
                else "0"
            ),
            "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE": (
                "1" if spec["llama_keep_alive"] else "0"
            ),
            "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE": (
                "1" if spec["buffered_stream_timing"] else "0"
            ),
            "KIRA_LLAMA_KEEP_ALIVE_CANDIDATE_DURATION": duration,
            "KIRA_VOICE_FORCE_SAPI": "",
            "KIRA_DISABLE_BLACKWELL_GPU_VOICE": "",
            "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR": "",
            "KIRA_VOICE_PREWARM_ON_ACTIVATE": "1",
            "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "0",
            "KIRA_PRIVATE_ACCEPTANCE_AUDIT": "1",
            "KIRA_VOICE_BENCHMARK_CAPTURE": "1",
        }
    )
    return env


def allocate_attempt_directory(mode: str, *, root: Path = LIVE_ROOT) -> Path:
    if mode not in MODE_SPECS:
        raise LatencyAcceptanceError(f"unknown candidate mode: {mode}")
    parent = root / mode
    parent.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        candidate = parent / f"attempt_{index:02d}"
        try:
            candidate.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise LatencyAcceptanceError("no append-only latency acceptance slot remains")


def validate_installed_llama(inventory: Mapping[str, Any]) -> dict[str, Any]:
    rows = inventory.get("llama3_1_8b")
    rows = rows if isinstance(rows, list) else []
    exact = [
        dict(row)
        for row in rows
        if isinstance(row, dict)
        and str(row.get("name") or row.get("model") or "") == EXPECTED_MODEL_NAME
        and str(row.get("digest") or "").casefold() == EXPECTED_MODEL_DIGEST
    ]
    if len(exact) != 1:
        raise LatencyAcceptanceError("exact installed llama3.1:8b digest was not proven")
    return exact[0]


def _resident_rows(inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = inventory.get("resident_models")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def validate_residency(
    inventory: Mapping[str, Any],
    *,
    expect_llama: bool,
) -> dict[str, Any]:
    rows = _resident_rows(inventory)
    qwen = [
        row
        for row in rows
        if "qwen" in f"{row.get('name', '')} {row.get('model', '')}".casefold()
    ]
    if qwen:
        raise LatencyAcceptanceError("Qwen was resident during the two-turn acceptance")
    llama = [
        row
        for row in rows
        if str(row.get("name") or row.get("model") or "") == EXPECTED_MODEL_NAME
    ]
    if expect_llama:
        if len(rows) != 1 or len(llama) != 1:
            raise LatencyAcceptanceError("bounded keep-alive did not retain only exact Llama")
        digest = str(llama[0].get("digest") or "").casefold()
        if digest != EXPECTED_MODEL_DIGEST:
            raise LatencyAcceptanceError("resident Llama digest changed")
    elif rows:
        raise LatencyAcceptanceError("a model remained resident when unload was required")
    return {
        "expect_llama": expect_llama,
        "resident_models": rows,
        "qwen_absent": True,
        "contract_passed": True,
    }


def validate_private_model_audit(
    value: Any,
    *,
    launch_id: str,
    request_id: str,
    displayed_reply: str,
    mode: str,
    keep_alive_duration: str,
) -> dict[str, Any]:
    audit = series.validate_followup_private_audit(
        value,
        launch_id=launch_id,
        request_id=request_id,
        displayed_reply=displayed_reply,
    )
    spec = MODE_SPECS[mode]
    expected_keep_alive: str | int = (
        normalized_keep_alive(keep_alive_duration) if spec["llama_keep_alive"] else 0
    )
    core = audit.get("core_turn") if isinstance(audit.get("core_turn"), dict) else {}
    calls = core.get("model_calls") if isinstance(core.get("model_calls"), list) else []
    for call in calls:
        if call.get("llama_keep_alive_candidate_enabled") is not bool(
            spec["llama_keep_alive"]
        ):
            raise LatencyAcceptanceError("model call keep-alive flag mismatch")
        if call.get("requested_keep_alive") != expected_keep_alive:
            raise LatencyAcceptanceError("model call keep-alive value mismatch")
        if call.get("stream") is not bool(spec["buffered_stream_timing"]):
            raise LatencyAcceptanceError("model call buffered-stream flag mismatch")
        if call.get("unvalidated_stream_content_displayed") is not False:
            raise LatencyAcceptanceError("an unvalidated model fragment was displayed")
        if spec["buffered_stream_timing"]:
            if call.get("buffered_until_complete") is not True:
                raise LatencyAcceptanceError("buffered stream was not held until complete")
            if call.get("first_token_available") is not True:
                raise LatencyAcceptanceError("buffered candidate did not measure first content")
            first = call.get("first_content_chunk_seconds")
            if isinstance(first, bool) or not isinstance(first, (int, float)) or first < 0:
                raise LatencyAcceptanceError("first-content timing is invalid")
        elif call.get("buffered_until_complete") is not False:
            raise LatencyAcceptanceError("nonstreaming mode reported buffered streaming")
    return audit


def validate_benchmark_timeline(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise LatencyAcceptanceError("voice benchmark timeline is empty")
    request_ids = {str(row.get("request_id") or "") for row in records}
    if len(request_ids) != 1 or not re.fullmatch(r"[a-f0-9]{32}", next(iter(request_ids))):
        raise LatencyAcceptanceError("voice benchmark request binding is invalid")
    sequences = [int(row.get("sequence") or 0) for row in records]
    monotonic = [int(row.get("monotonic_ns") or 0) for row in records]
    if sequences != list(range(1, len(records) + 1)) or monotonic != sorted(monotonic):
        raise LatencyAcceptanceError("voice benchmark timeline is not monotonic")
    events = [str(row.get("event") or "") for row in records]
    required = (
        "request_submitted",
        "chat_request_received",
        "text_ready",
        "voice_payload_ready",
        "voice_pipeline_start",
        "chunk_synthesis_start",
        "chunk_synthesis_end",
        "chunk_playback_start",
        "chunk_playback_end",
        "request_completed",
    )
    missing = [event for event in required if event not in events]
    if missing:
        raise LatencyAcceptanceError(f"voice benchmark is missing events: {missing}")
    required_positions = [events.index(event) for event in required]
    if required_positions != sorted(required_positions):
        raise LatencyAcceptanceError("voice benchmark phase order is invalid")
    if events[-1] != "request_completed":
        raise LatencyAcceptanceError("voice benchmark did not finish cleanly")
    completed = records[-1].get("details")
    completed = completed if isinstance(completed, dict) else {}
    for key in (
        "complete",
        "expected_vs_synthesized_exact",
        "expected_vs_playback_proxy_exact",
        "voice_identity_unchanged",
        "audio_generated",
        "audio_played",
    ):
        if completed.get(key) is not True:
            raise LatencyAcceptanceError(f"voice completion contract failed: {key}")
    for row in records:
        privacy = row.get("privacy") if isinstance(row.get("privacy"), dict) else {}
        if privacy.get("raw_prompt_recorded") is not False or privacy.get(
            "raw_reply_recorded"
        ) is not False:
            raise LatencyAcceptanceError("benchmark captured a raw private text field")
    first_ns = monotonic[0]
    last_ns = monotonic[-1]
    return {
        "request_id": next(iter(request_ids)),
        "event_count": len(records),
        "events": events,
        "total_seconds": round((last_ns - first_ns) / 1_000_000_000.0, 6),
        "completion": dict(completed),
        "monotonic": True,
    }


def classify_voice_route(
    synthesis_rows: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    if mode not in MODE_SPECS or not synthesis_rows:
        raise LatencyAcceptanceError("voice synthesis route evidence is absent")
    spec = MODE_SPECS[mode]
    expected_gpu = str(spec["expected_gpu_route"])
    persistent_version = str(spec.get("persistent_version") or "v1")
    expected_lifecycle = str(
        spec.get("expected_sidecar_lifecycle")
        or "session_owned_persistent_candidate"
    )
    route_classes: list[str] = []
    projected: list[dict[str, Any]] = []
    for raw in synthesis_rows:
        row = dict(raw)
        route = str(row.get("route_id") or "").casefold()
        approved = str(row.get("approved_voice_path_used") or "").casefold()
        joined = f"{route} {approved} {row.get('route_attempt_summary', '')}".casefold()
        if (
            "sapi" in joined
            or "generic" in joined
            or row.get("sapi_voice_used") is True
            or row.get("generic_voice_used") is True
        ):
            raise LatencyAcceptanceError("SAPI or generic voice route was observed")
        if route == expected_gpu.casefold() and approved == "blackwell_gpu":
            required = {
                "generated": True,
                "device": "cuda",
                "gpu_synthesis_attempted": True,
                "cpu_synthesis_attempted": False,
                "automatic_cpu_fallback_used": False,
            }
            if persistent_version == "v2":
                # Accepted v2 execution truth and all forbidden-route flags
                # must be explicit in the projected row.  A CUDA route label,
                # allocation measurement, or missing boolean proves nothing.
                required.update(
                    {
                        "gpu_actual_execution": True,
                        "generic_voice_used": False,
                        "sapi_voice_used": False,
                        "fallback_used": False,
                        "test_only_injected_client": False,
                        "qwen_absence_proven_for_accepted_generation": True,
                        "production_route_promoted": False,
                        "production_routing_authorized": False,
                    }
                )
            else:
                required["gpu_actual_allocation"] = True
            if any(row.get(key) != value for key, value in required.items()):
                raise LatencyAcceptanceError("preferred GPU voice evidence is incomplete")
            if spec["persistent_voice"]:
                if row.get("persistent_worker_reused") is not True or row.get(
                    "sidecar_lifecycle"
                ) != expected_lifecycle:
                    raise LatencyAcceptanceError("persistent GPU worker reuse was not proven")
            route_classes.append("preferred_gpu")
        elif route in {"sealed_cpu", "sealed_cpu_chatterbox"} and approved in {
            "sealed_cpu",
            "sealed_cpu_chatterbox",
        }:
            if (
                row.get("generated") is not True
                or row.get("device") != "cpu"
                or row.get("cpu_synthesis_attempted") is not True
                or row.get("automatic_cpu_fallback_used") is not True
                or not str(row.get("preferred_failure_reason") or "")
            ):
                raise LatencyAcceptanceError("sealed CPU fallback evidence is incomplete")
            route_classes.append("sealed_cpu_fallback")
        else:
            raise LatencyAcceptanceError(f"unapproved voice route observed: {route or 'missing'}")
        projected.append(row)
    classes = sorted(set(route_classes))
    return {
        "route_class": classes[0] if len(classes) == 1 else "mixed_approved_routes",
        "rows": projected,
        "persistent_candidate_version": (
            persistent_version if spec["persistent_voice"] else "none"
        ),
        "expected_sidecar_lifecycle": (
            expected_lifecycle if spec["persistent_voice"] else None
        ),
        "approved_routes_only": True,
        "preferred_gpu_passed": classes == ["preferred_gpu"],
        "sealed_cpu_fallback_used": "sealed_cpu_fallback" in classes,
        "sapi_used": False,
        "generic_voice_used": False,
    }


def wav_snapshot(root: Path = VOICE_OUTPUT_DIR) -> dict[str, tuple[int, int]]:
    if not root.is_dir():
        return {}
    return {
        str(path.resolve()): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*.wav")
        if path.is_file()
    }


def changed_wavs(
    before: Mapping[str, tuple[int, int]],
    after: Mapping[str, tuple[int, int]],
) -> list[Path]:
    return [
        Path(raw)
        for raw in sorted(after, key=str.casefold)
        if raw not in before or before[raw] != after[raw]
    ]


def wav_evidence(path: Path, *, root: Path = VOICE_OUTPUT_DIR) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise LatencyAcceptanceError("generated WAV escaped the approved output root") from exc
    try:
        with wave.open(str(resolved), "rb") as reader:
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            rate = reader.getframerate()
            count = reader.getnframes()
            compression = reader.getcomptype()
            frames = reader.readframes(count)
    except (OSError, EOFError, wave.Error) as exc:
        raise LatencyAcceptanceError(f"generated WAV is unreadable: {exc}") from exc
    if compression != "NONE" or width != 2:
        raise LatencyAcceptanceError("generated WAV is not uncompressed signed 16-bit PCM")
    sample_count = len(frames) // 2
    samples: Iterable[int] = (
        struct.unpack(f"<{sample_count}h", frames[: sample_count * 2])
        if sample_count
        else ()
    )
    peak = max((abs(value) for value in samples), default=0)
    try:
        project_relative = _relative(resolved)
    except ValueError:
        project_relative = None
    evidence = {
        "path": relative.as_posix(),
        "project_relative_path": project_relative,
        "sha256": _sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
        "channels": channels,
        "sample_width_bytes": width,
        "sample_rate_hz": rate,
        "frame_count": count,
        "duration_seconds": round(count / rate, 6) if rate else 0.0,
        "peak_linear": round(peak / 32768.0, 6),
        "readable_non_silent": bool(count > 0 and peak > 0),
    }
    if evidence["readable_non_silent"] is not True:
        raise LatencyAcceptanceError("generated WAV is silent or empty")
    return evidence


def nvidia_snapshot() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        candidate = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        executable = str(candidate) if candidate.is_file() else ""
    if not executable:
        return {"available": False, "reason": "nvidia_smi_not_found", "gpus": []}
    completed = subprocess.run(
        [
            executable,
            "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return {"available": False, "reason": "nvidia_smi_query_failed", "gpus": []}
    rows: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 5:
            continue
        try:
            rows.append(
                {
                    "index": int(fields[0]),
                    "name": fields[1],
                    "memory_used_mib": float(fields[2]),
                    "memory_total_mib": float(fields[3]),
                    "utilization_percent": float(fields[4]),
                }
            )
        except ValueError:
            continue
    return {
        "available": bool(rows),
        "reason": "ok" if rows else "nvidia_smi_no_parseable_rows",
        "captured_at_utc": bounded.utc_now(),
        "gpus": rows,
    }


class GpuSampler:
    """Privacy-free GPU snapshots only at explicit acceptance boundaries.

    The first three persistent-candidate attempts spawned ``nvidia-smi``
    repeatedly while CUDA was loading.  A separate phase diagnostic proved
    the same model and approved reference can load in about 11 seconds when
    that repeating poller is absent.  The acceptance therefore records one
    snapshot per named boundary and never runs a background GPU-query loop.
    Worker-local Torch allocator evidence remains the synthesis proof.
    """

    def __init__(self, *, snapshot: Any = nvidia_snapshot) -> None:
        self.samples: list[dict[str, Any]] = []
        self._phase = "preflight"
        self._snapshot = snapshot
        self._started: float | None = None
        self._stopped = False

    def _capture(self) -> None:
        if self._started is None or self._stopped:
            return
        self.samples.append(
            {
                "elapsed_seconds": round(time.perf_counter() - self._started, 3),
                "phase": self._phase,
                "snapshot": self._snapshot(),
                "sampling_mode": "explicit_phase_boundary_only",
            }
        )

    def mark(self, phase: str) -> None:
        self._phase = str(phase or "unknown")[:80]
        self._capture()

    def start(self) -> None:
        if self._started is not None:
            raise LatencyAcceptanceError("GPU sampler was started twice")
        self._started = time.perf_counter()
        self._capture()

    def stop(self) -> list[dict[str, Any]]:
        if self._started is not None and not self._stopped:
            self._capture()
            self._stopped = True
        return list(self.samples)


def _gpu_used(snapshot: Mapping[str, Any], index: int = 0) -> float | None:
    rows = snapshot.get("gpus")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and int(row.get("index", -1)) == index:
            try:
                return float(row.get("memory_used_mib"))
            except (TypeError, ValueError):
                return None
    return None


def summarize_gpu_samples(
    samples: list[dict[str, Any]],
    *,
    baseline: Mapping[str, Any],
    final: Mapping[str, Any],
    tolerance_mib: float = VRAM_RETURN_TOLERANCE_MIB,
) -> dict[str, Any]:
    baseline_used = _gpu_used(baseline)
    final_used = _gpu_used(final)
    observed = [
        value
        for value in (
            _gpu_used(item.get("snapshot") or {})
            for item in samples
            if isinstance(item, dict)
        )
        if value is not None
    ]
    peak = max(observed, default=None)
    return {
        "sample_count": len(samples),
        "sampling_mode": "explicit_phase_boundary_only",
        "background_nvidia_smi_polling": False,
        "peak_scope": "observed_named_boundaries_not_continuous_peak",
        "baseline_used_mib": baseline_used,
        "peak_used_mib": peak,
        "peak_delta_mib": (
            round(peak - baseline_used, 3)
            if peak is not None and baseline_used is not None
            else None
        ),
        "final_used_mib": final_used,
        "return_tolerance_mib": float(tolerance_mib),
        "vram_returned": bool(
            baseline_used is not None
            and final_used is not None
            and final_used <= baseline_used + float(tolerance_mib)
        ),
        "samples": samples,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def wait_for_life_event(
    path: Path,
    event: str,
    *,
    since_utc: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        matches = [
            row
            for row in _read_jsonl(path)
            if row.get("event") == event and str(row.get("at") or "") >= since_utc
        ]
        if matches:
            return matches[-1]
        if time.monotonic() >= deadline:
            raise LatencyAcceptanceError(f"timed out waiting for life-loop event {event}")
        time.sleep(0.1)


def validate_voice_release_event(
    event: Mapping[str, Any],
    *,
    persistent_expected: bool,
    persistent_version: str = "v1",
) -> dict[str, Any]:
    if event.get("event") != "voice_model_release":
        raise LatencyAcceptanceError("voice release lifecycle event is absent")
    result = event.get("result") if isinstance(event.get("result"), dict) else {}
    if result.get("playback") is not False or result.get("generated_audio") is not False:
        raise LatencyAcceptanceError("voice release performed synthesis or playback")
    evidence: dict[str, Any] = {
        "persistent_expected": persistent_expected,
        "released": result.get("released"),
        "reason": result.get("reason"),
        "device": result.get("device"),
        "playback": False,
        "generated_audio": False,
        "passed": True,
    }
    if persistent_expected and persistent_version == "v2":
        owner_release = (
            result.get("owner_bound_persistent_release")
            if isinstance(result.get("owner_bound_persistent_release"), dict)
            else {}
        )
        owned = (
            owner_release.get("cleanup")
            if isinstance(owner_release.get("cleanup"), dict)
            else {}
        )
        if (
            result.get("persistent_cleanup_proven") is not True
            or owner_release.get("owner_matched") is not True
            or owner_release.get("release_attempted") is not True
            or owner_release.get("released") is not True
            or owner_release.get("persistent_integration") is not True
            or owner_release.get("cleanup_debt") is not False
            or owned.get("owned_worker_was_present") is not True
            or owned.get("owned_worker_closed") is not True
            or owned.get("owned_process_exit_code") != 0
            or owned.get("owned_process_forced_termination") is not False
            or owned.get("cleanup_thread_finished") is not True
            or owned.get("unload_error_type")
            or owned.get("close_error_type")
        ):
            raise LatencyAcceptanceError("persistent v2 owner-bound cleanup failed")
        evidence["persistent_version"] = "v2"
        evidence["owner_bound_persistent_release"] = _json_detach(owner_release)
    elif persistent_expected:
        persistent_release = (
            result.get("persistent_release")
            if isinstance(result.get("persistent_release"), dict)
            else {}
        )
        owned = (
            persistent_release.get("cleanup")
            if isinstance(persistent_release.get("cleanup"), dict)
            else {}
        )
        if (
            persistent_release.get("persistent_integration") is not True
            or owned.get("owned_worker_was_present") is not True
            or owned.get("owned_worker_closed") is not True
            or owned.get("owned_process_exit_code") != 0
            or owned.get("owned_process_forced_termination") is not False
            or owned.get("unload_error_type")
            or owned.get("close_error_type")
        ):
            raise LatencyAcceptanceError("persistent voice owned-worker cleanup failed")
        evidence["persistent_version"] = "v1"
        evidence["persistent_release"] = _json_detach(persistent_release)
    return evidence


def capture_voice_release_cleanup_evidence(
    life_log: Path,
    *,
    activation_started_at: str,
    persistent_expected: bool,
    persistent_version: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Capture the exact append-only release row; absence is an explicit failure."""

    if not activation_started_at:
        return {
            "voice_model_release_event": None,
            "voice_model_release_contract": {
                "passed": False,
                "reason": "activation_not_reached_release_not_observable",
            },
        }
    event: dict[str, Any] | None = None
    try:
        event = wait_for_life_event(
            life_log,
            "voice_model_release",
            since_utc=activation_started_at,
            timeout_seconds=timeout_seconds,
        )
        contract = validate_voice_release_event(
            event,
            persistent_expected=persistent_expected,
            persistent_version=persistent_version,
        )
    except Exception as exc:
        contract = {
            "passed": False,
            "reason": "voice_release_evidence_not_proven",
            "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
        }
    return {
        "voice_model_release_event": _json_detach(event) if event is not None else None,
        "voice_model_release_contract": contract,
    }


def measure_cleanup_ports(*, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Measure all exact loopback service ports; probe failure is never closed."""

    ports = (bounded.SHELL_PORT, bounded.ASR_PORT, bounded.VISUAL_PORT)
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    states: dict[str, bool | None] = {}
    errors: dict[str, str] = {}
    while True:
        states = {}
        errors = {}
        for port in ports:
            try:
                states[str(port)] = bool(bounded.port_is_open(port))
            except Exception as exc:
                states[str(port)] = None
                errors[str(port)] = type(exc).__name__
        if all(value is False for value in states.values()):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)
    return {
        "ports_closed": bool(states) and all(
            value is False for value in states.values()
        ),
        "port_open_state_after": states,
        "port_probe_errors": errors,
    }


def validate_exact_cleanup_evidence(cleanup: Mapping[str, Any]) -> dict[str, Any]:
    """Validate only explicit final observations; missing fields fail closed."""

    release = (
        cleanup.get("voice_model_release_contract")
        if isinstance(cleanup.get("voice_model_release_contract"), Mapping)
        else {}
    )
    checks = {
        "exact_owned_server_exited": cleanup.get("exact_owned_server_exited") is True,
        "ports_closed": cleanup.get("ports_closed") is True,
        "voice_model_release_proven": release.get("passed") is True,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "issues": [key for key, passed in checks.items() if not passed],
    }


def _synthesis_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(row.get("details") or {})
        for row in records
        if row.get("event") == "chunk_synthesis_end"
        and isinstance(row.get("details"), dict)
    ]


def _model_calls(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    core = audit.get("core_turn") if isinstance(audit.get("core_turn"), dict) else {}
    raw = core.get("model_calls") if isinstance(core.get("model_calls"), list) else []
    return [dict(row) for row in raw if isinstance(row, dict)]


def _duration_seconds_from_ns(value: Any) -> float | None:
    try:
        return round(int(value) / 1_000_000_000.0, 6)
    except (TypeError, ValueError):
        return None


def build_turn_record(
    *,
    turn_spec: Mapping[str, str],
    request_id: str,
    chat: Mapping[str, Any],
    chat_http_seconds: float,
    audit: Mapping[str, Any],
    records: list[dict[str, Any]],
    benchmark_path: Path,
    wav_paths: list[Path],
    life_voice: Mapping[str, Any],
    residency: Mapping[str, Any],
    mode: str,
    private_safe_model_evidence: bool = False,
) -> dict[str, Any]:
    timeline = validate_benchmark_timeline(records)
    route = classify_voice_route(_synthesis_rows(records), mode=mode)
    displayed = str(chat.get("ai_line") or "")
    calls = _model_calls(audit)
    primary = next((row for row in calls if row.get("outcome") == "completed"), calls[0])
    persisted_calls = (
        redact_private_text_fields(calls) if private_safe_model_evidence else calls
    )
    raw_reply_evidence = [private_text_evidence(row.get("raw_reply")) for row in calls]
    initial_pipeline_reply = (audit.get("core_turn") or {}).get("initial_pipeline_reply")
    core_transformations = (audit.get("core_turn") or {}).get("transformations")
    outer_transformations = audit.get("outer_transformations")
    metrics = primary.get("ollama_metrics") if isinstance(primary.get("ollama_metrics"), dict) else {}
    wavs = [wav_evidence(path) for path in wav_paths]
    voice_result = life_voice.get("result") if isinstance(life_voice.get("result"), dict) else {}
    chunks = voice_result.get("voice_chunk_results")
    chunks = [dict(row) for row in chunks if isinstance(row, dict)] if isinstance(chunks, list) else []
    spoken_chunks = [
        {
            "chunk_index": row.get("chunk_index"),
            "text_sha256": _sha256_bytes(str(row.get("text") or "").encode("utf-8")),
            "audio_path": row.get("audio_path"),
            "route_id": row.get("route_id"),
            "approved_voice_path_used": row.get("approved_voice_path_used"),
        }
        for row in chunks
    ]
    speech_audit = (
        voice_result.get("speech_audit")
        if isinstance(voice_result.get("speech_audit"), dict)
        else {}
    )
    life_audio = {
        str(Path(str(row.get("audio_path") or "")).resolve())
        for row in chunks
        if str(row.get("audio_path") or "")
    }
    changed_audio = {str(path.resolve()) for path in wav_paths}
    audio_paths_exact = bool(life_audio) and life_audio == changed_audio
    required_model_fields = all(
        row.get("model_name") == EXPECTED_MODEL_NAME
        and row.get("backend") == "ollama"
        and row.get("outcome") == "completed"
        for row in calls
    )
    phases = bounded.benchmark_phase_audit(records)
    first_proxy = bounded.event_latency(records, "first_playback_proxy")
    record = {
        "turn_id": turn_spec["id"],
        "exact_question": turn_spec["text"],
        "exact_question_sha256": _sha256_bytes(turn_spec["text"].encode("utf-8")),
        "benchmark_request_id": request_id,
        "public_reply": {
            "text": displayed,
            "sha256": _sha256_bytes(displayed.encode("utf-8")),
        },
        "model": {
            "name": EXPECTED_MODEL_NAME,
            "digest": EXPECTED_MODEL_DIGEST,
            "response_route": (audit.get("core_turn") or {}).get("response_route"),
            "call_count": len(calls),
            "calls": persisted_calls,
            **(
                {
                    "raw_reply_evidence": raw_reply_evidence,
                    "initial_pipeline_reply_evidence": private_text_evidence(
                        initial_pipeline_reply
                    ),
                    "core_cleanup_transformations": redact_private_text_fields(
                        core_transformations
                    ),
                    "outer_cleanup_transformations": redact_private_text_fields(
                        outer_transformations
                    ),
                    "private_reply_evidence_policy": {
                        "raw_model_reply_text_retained": False,
                        "initial_pipeline_reply_text_retained": False,
                        "hash_length_and_transformations_retained": True,
                        "final_public_spoken_text_retained": True,
                    },
                }
                if private_safe_model_evidence
                else {
                    "raw_replies": [str(row.get("raw_reply") or "") for row in calls],
                    "initial_pipeline_reply": initial_pipeline_reply,
                    "core_cleanup_transformations": core_transformations,
                    "outer_cleanup_transformations": outer_transformations,
                }
            ),
            "request_wall_seconds": primary.get("request_wall_seconds"),
            "first_content_chunk_seconds": primary.get("first_content_chunk_seconds"),
            "ollama_load_seconds": _duration_seconds_from_ns(metrics.get("load_duration")),
            "ollama_prompt_eval_seconds": _duration_seconds_from_ns(
                metrics.get("prompt_eval_duration")
            ),
            "ollama_eval_seconds": _duration_seconds_from_ns(metrics.get("eval_duration")),
            "ollama_total_seconds": _duration_seconds_from_ns(metrics.get("total_duration")),
        },
        "prompt": {
            "assembled_at": audit.get("prompt_assembled_at"),
            "sha256": audit.get("core_prompt_sha256"),
            "utf8_bytes": audit.get("core_prompt_utf8_bytes"),
            "sensory_context_inserted": audit.get("one_turn_sensory_context_inserted"),
            "sensory_cue_ids": audit.get("sensory_cue_ids"),
        },
        "timing": {
            "chat_http_wall_seconds": chat_http_seconds,
            "request_to_text_ready_seconds": bounded.event_latency(records, "text_ready"),
            "request_to_voice_payload_ready_seconds": bounded.event_latency(
                records, "voice_payload_ready"
            ),
            "request_to_synthesis_start_seconds": bounded.event_latency(
                records, "chunk_synthesis_start"
            ),
            "request_to_first_playback_proxy_seconds": first_proxy,
            "request_to_voice_complete_seconds": bounded.event_latency(
                records, "request_completed"
            ),
            "voice_phases": phases,
            "desktop_first_audible_target_seconds": DESKTOP_FIRST_AUDIBLE_TARGET_SECONDS,
            "playback_proxy_meets_target": bool(
                isinstance(first_proxy, (int, float))
                and first_proxy <= DESKTOP_FIRST_AUDIBLE_TARGET_SECONDS
            ),
            "true_owner_heard_first_audible_seconds": None,
            "owner_heard_target_status": "PENDING_OWNER_OBSERVATION",
        },
        "voice": {
            "queue_result": chat.get("voice_result"),
            "route": route,
            "life_loop_record": _json_detach(life_voice),
            "public_spoken_chunks": spoken_chunks,
            "generated_wavs": wavs,
            "audio_paths_exact": audio_paths_exact,
        },
        "benchmark": {
            "path": _relative(benchmark_path),
            "sha256": _sha256_file(benchmark_path),
            "timeline": timeline,
        },
        "ollama_residency_after_turn": _json_detach(residency),
        "checks": {
            "reply_nonempty": bool(displayed.strip()),
            "exact_llama_calls_only": bool(calls) and required_model_fields,
            "prompt_hash_present": bool(re.fullmatch(r"[0-9a-f]{64}", str(audit.get("core_prompt_sha256") or "").casefold())),
            "no_sensory_context": audit.get("one_turn_sensory_context_inserted") is False
            and not audit.get("sensory_cue_ids"),
            "benchmark_complete": timeline.get("completion", {}).get("complete") is True,
            "approved_routes_only": route["approved_routes_only"] is True,
            "preferred_gpu_route": route["preferred_gpu_passed"] is True,
            "wav_count_matches_chunks": bool(wavs) and len(wavs) == len(chunks),
            "wav_paths_exact": audio_paths_exact,
            "wavs_readable_non_silent": bool(wavs)
            and all(item["readable_non_silent"] is True for item in wavs),
            "voice_complete": voice_result.get("complete") is True,
            "voice_played": timeline.get("completion", {}).get("audio_played") is True,
            "public_spoken_only_exact_coverage": speech_audit.get(
                "privacy_safe_for_speech"
            )
            is True
            and speech_audit.get("non_name_word_coverage_exact") is True
            and speech_audit.get("public_word_coverage_exact") is True,
            # The assertion immediately below rejects the record before it can
            # be returned whenever private-safe persistence was requested.
            "private_model_evidence_contract_enforced": True,
        },
    }
    if private_safe_model_evidence:
        assert_private_text_redacted(record["model"])
    return record


def _post_ollama(payload: Mapping[str, Any], *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
    opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
    request = urllib_request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=timeout_seconds) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise LatencyAcceptanceError("Ollama unload response exceeded 2 MiB")
    value = json.loads(raw.decode("utf-8"))
    return dict(value) if isinstance(value, dict) else {}


def unload_exact_llama_if_owned(inventory: Mapping[str, Any]) -> dict[str, Any]:
    rows = _resident_rows(inventory)
    if not rows:
        return {
            "attempted": False,
            "reason": "no_resident_model",
            "exact_model_only": True,
        }
    if len(rows) != 1:
        raise LatencyAcceptanceError("refusing to unload while multiple models are resident")
    row = rows[0]
    name = str(row.get("name") or row.get("model") or "")
    digest = str(row.get("digest") or "").casefold()
    if name != EXPECTED_MODEL_NAME or (digest and digest != EXPECTED_MODEL_DIGEST):
        raise LatencyAcceptanceError("refusing to unload a model not owned by this acceptance")
    started = time.perf_counter()
    response = _post_ollama(
        {"model": EXPECTED_MODEL_NAME, "prompt": "", "stream": False, "keep_alive": 0}
    )
    return {
        "attempted": True,
        "reason": "exact_owned_llama_release",
        "exact_model_only": True,
        "model": EXPECTED_MODEL_NAME,
        "digest": EXPECTED_MODEL_DIGEST,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "response_done": response.get("done"),
    }


def wait_for_ollama_empty(timeout_seconds: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = bounded.ollama_inventory()
    while _resident_rows(last) and time.monotonic() < deadline:
        time.sleep(0.25)
        last = bounded.ollama_inventory()
    return last


def _wait_for_vram_return(
    baseline: Mapping[str, Any],
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    baseline_used = _gpu_used(baseline)
    deadline = time.monotonic() + timeout_seconds
    samples: list[dict[str, Any]] = []
    while True:
        current = nvidia_snapshot()
        samples.append(current)
        used = _gpu_used(current)
        if (
            baseline_used is not None
            and used is not None
            and used <= baseline_used + VRAM_RETURN_TOLERANCE_MIB
        ):
            return {"returned": True, "samples": samples, "final": current}
        if time.monotonic() >= deadline:
            return {"returned": False, "samples": samples, "final": current}
        time.sleep(0.5)


def run_live_acceptance(
    *,
    mode: str,
    keep_alive_duration: str,
    persistent_prerequisite_report: Path | None,
    question_profile: str = "owner_hearing_natural",
) -> tuple[Path, dict[str, Any]]:
    spec = MODE_SPECS[mode]
    if question_profile not in QUESTION_PROFILES:
        raise LatencyAcceptanceError(f"unknown question profile: {question_profile}")
    profile = QUESTION_PROFILES[question_profile]
    configured_turns = tuple(dict(item) for item in profile["turns"])
    attempt = allocate_attempt_directory(mode)
    runtime_dir = attempt / "isolated_runtime"
    runtime_dir.mkdir()
    report_path = attempt / REPORT_NAME
    stdout_path = attempt / "server.stdout.log"
    stderr_path = attempt / "server.stderr.log"
    life_log = runtime_dir / "kira_world_life_loop_log.jsonl"
    state_path = runtime_dir / "kira_world_shell_state.json"
    launch_id = uuid.uuid4().hex
    shell_token = secrets.token_urlsafe(32)
    asr_token = secrets.token_urlsafe(32)
    visual_token = secrets.token_urlsafe(32)
    started_at = bounded.utc_now()
    before_hashes = protected_hashes()
    memory_root = ROOT / "Data" / "memory_promotion" / "candidates"
    memory_before = directory_manifest(memory_root)
    routing = validate_voice_routing_contract()
    prerequisite: dict[str, Any] | None = None
    if spec["standalone_persistent_report_required"]:
        if persistent_prerequisite_report is None:
            raise LatencyAcceptanceError("persistent mode requires a prerequisite report")
        prerequisite = (
            validate_persistent_v2_prerequisite(persistent_prerequisite_report)
            if spec.get("persistent_version") == "v2"
            else validate_persistent_prerequisite(persistent_prerequisite_report)
        )
    bounded.require_idle_preflight()
    before_ollama = bounded.ollama_inventory()
    installed_model = validate_installed_llama(before_ollama)
    validate_residency(before_ollama, expect_llama=False)
    baseline_gpu = nvidia_snapshot()
    if baseline_gpu.get("available") is not True:
        raise LatencyAcceptanceError("NVIDIA telemetry is unavailable")

    env = build_environment(
        os.environ,
        mode=mode,
        runtime_dir=runtime_dir,
        shell_token=shell_token,
        asr_token=asr_token,
        visual_token=visual_token,
        launch_id=launch_id,
        keep_alive_duration=keep_alive_duration,
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "kira_text_voice_two_turn_latency_acceptance",
        "evidence_classification": "private_owner_supervised_append_only",
        "mode": mode,
        "question_profile": question_profile,
        "mode_contract": dict(spec),
        "started_at": started_at,
        "launch_id": launch_id,
        "attempt_path": _relative(attempt),
        "exact_turns": [dict(item) for item in configured_turns],
        "voluntary_invitation_required": profile["voluntary_invitation_required"],
        "voluntary_invitation": None,
        "partial_answer_allowed_after_every_turn": profile[
            "partial_answer_allowed_after_every_turn"
        ],
        "stop_after_every_turn_allowed": profile["stop_after_every_turn_allowed"],
        "voluntary_stop_after_turn": None,
        "participation_status": (
            "NOT_REQUIRED_FOR_OWNER_HEARING_PROFILE"
            if not profile["voluntary_invitation_required"]
            else "PENDING_PUBLIC_INVITATION"
        ),
        "exact_model": {"name": EXPECTED_MODEL_NAME, "digest": EXPECTED_MODEL_DIGEST},
        "installed_model": installed_model,
        "persistent_prerequisite": prerequisite,
        "routing_contract": routing,
        "environment_contract": {
            "normal_shell_server_command": "py Tools/kira_world_shell_server.py --no-browser",
            "isolated_runtime": _relative(runtime_dir),
            "browser_opened": False,
            "camera_opened": False,
            "microphone_opened": False,
            "qwen_one_still_enabled": False,
            "sapi_forced": False,
            "generic_voice_allowed": False,
            "production_defaults_changed": False,
            "candidate_flags": {
                key: env[key]
                for key in (
                    V1_PERSISTENT_FEATURE_FLAG,
                    V2_PERSISTENT_FEATURE_FLAG,
                    "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE",
                    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE",
                    "KIRA_LLAMA_KEEP_ALIVE_CANDIDATE_DURATION",
                )
            },
        },
        "rollback_contract": {
            "candidate_flags_are_child_process_only": True,
            "exact_owned_server_and_v2_worker_close_required": True,
            "production_defaults_changed": False,
            "v1_and_one_shot_rollback_paths_preserved": True,
            "sealed_cpu_fallback_preserved": True,
            "append_only_report_and_wavs_retained": True,
        },
        "protected_before": before_hashes,
        "memory_promotion_before": memory_before,
        "ollama_before": before_ollama,
        "gpu_baseline": baseline_gpu,
        "turns": [],
        "passed": False,
    }

    server: subprocess.Popen[bytes] | None = None
    sampler = GpuSampler()
    sampler_started = False
    sensory_lease = ""
    deactivated = False
    safe_closed = False
    activation_started_at = ""
    cleanup: dict[str, Any] = {}
    try:
        sampler.start()
        sampler_started = True
        sampler.mark("server_start")
        with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
            server = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "Tools" / "kira_world_shell_server.py"),
                    "--no-browser",
                ],
                cwd=str(ROOT),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        report["server_pid"] = server.pid
        readiness_started = time.perf_counter()
        waiter = subprocess.run(
            [
                sys.executable,
                str(ROOT / "Tools" / "wait_for_kira_world_shell.py"),
                "--url",
                f"{bounded.BASE_URL}/",
                "--timeout",
                "60",
                "--owned-pid",
                str(server.pid),
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=70,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        report["launcher_readiness"] = {
            "returncode": waiter.returncode,
            "elapsed_seconds": round(time.perf_counter() - readiness_started, 6),
            "stdout": waiter.stdout[-2000:],
            "stderr": waiter.stderr[-2000:],
        }
        if waiter.returncode != 0:
            raise LatencyAcceptanceError("normal shell readiness helper failed")

        report["sidecars_started_devices_unopened"] = {
            "asr": bounded.sidecar_health(
                f"http://127.0.0.1:{bounded.ASR_PORT}/health",
                "X-Kira-ASR-Token",
                asr_token,
            )[0],
            "visual": bounded.sidecar_health(
                f"http://127.0.0.1:{bounded.VISUAL_PORT}/health",
                "X-Kira-Visual-Token",
                visual_token,
            )[0],
            "camera_requests": 0,
            "microphone_requests": 0,
        }
        sampler.mark("activation_and_voice_prewarm")
        activation_started_at = bounded.utc_now()
        activation_started = time.perf_counter()
        activation = bounded.request_json(
            f"{bounded.BASE_URL}/api/activate",
            token=shell_token,
            method="POST",
            body={
                "candidate": "kira",
                "source": "two_turn_latency_acceptance_20260802",
            },
        )
        state = bounded.request_json(f"{bounded.BASE_URL}/api/state", token=shell_token)
        surface = series.validate_text_only_activation(activation, state)
        sensory_lease = str(state.get("sensory_lease") or "")
        if state.get("active_candidate") != "kira" or not sensory_lease:
            raise LatencyAcceptanceError("exact Kira Text + Voice activation failed")
        report["activation"] = {
            "elapsed_seconds": round(time.perf_counter() - activation_started, 6),
            "response": _json_detach(activation),
            "surface": surface,
        }
        if spec["persistent_voice"]:
            prewarm = wait_for_life_event(
                life_log,
                "voice_prewarm",
                since_utc=activation_started_at,
                timeout_seconds=900,
            )
            prewarm_result = prewarm.get("result") if isinstance(prewarm.get("result"), dict) else {}
            if (
                prewarm_result.get("warmed") is not True
                or prewarm_result.get("owned_worker_running") is not True
                or prewarm_result.get("model_loaded") is not True
            ):
                raise LatencyAcceptanceError("persistent Blackwell prewarm did not complete")
            report["persistent_voice_prewarm"] = {
                "event": _json_detach(prewarm),
                "activation_to_prewarm_wall_seconds": round(
                    time.perf_counter() - activation_started, 6
                ),
            }
        else:
            report["persistent_voice_prewarm"] = {
                "required": False,
                "reason": "one_shot_baseline",
            }

        def capture_turn(
            turn_spec: Mapping[str, str],
            *,
            phase_label: str,
            private_safe_model_evidence: bool,
        ) -> tuple[dict[str, Any], str, Mapping[str, Any]]:
            sampler.mark(phase_label)
            turn_started_at = bounded.utc_now()
            before_wavs = wav_snapshot()
            benchmark = bounded.request_json(
                f"{bounded.BASE_URL}/api/voice-benchmark/submit",
                token=shell_token,
                method="POST",
                body={},
            )
            request_id = str(benchmark.get("benchmark_capture_id") or "")
            if not re.fullmatch(r"[a-f0-9]{32}", request_id):
                raise LatencyAcceptanceError("voice benchmark capture did not start")
            chat_started = time.perf_counter()
            chat = bounded.request_json(
                f"{bounded.BASE_URL}/api/chat",
                token=shell_token,
                method="POST",
                body={
                    "text": turn_spec["text"],
                    "benchmark_request_id": request_id,
                    "private_acceptance_audit": True,
                },
                timeout=300,
            )
            chat_seconds = round(time.perf_counter() - chat_started, 6)
            displayed = str(chat.get("ai_line") or "").strip()
            if chat.get("ok") is not True or not displayed:
                raise LatencyAcceptanceError("Kira did not return a public reply")
            audit = validate_private_model_audit(
                chat.get("private_acceptance_audit"),
                launch_id=launch_id,
                request_id=request_id,
                displayed_reply=displayed,
                mode=mode,
                keep_alive_duration=keep_alive_duration,
            )
            records, benchmark_path = bounded.load_benchmark(request_id)
            life_voice = wait_for_life_event(
                life_log,
                "voice_output",
                since_utc=turn_started_at,
                timeout_seconds=10,
            )
            after_wavs = wav_snapshot()
            new_wavs = changed_wavs(before_wavs, after_wavs)
            inventory = bounded.ollama_inventory()
            if not spec["llama_keep_alive"]:
                inventory = wait_for_ollama_empty()
            residency = validate_residency(
                inventory,
                expect_llama=bool(spec["llama_keep_alive"]),
            )
            turn = build_turn_record(
                turn_spec=turn_spec,
                request_id=request_id,
                chat=chat,
                chat_http_seconds=chat_seconds,
                audit=audit,
                records=records,
                benchmark_path=benchmark_path,
                wav_paths=new_wavs,
                life_voice=life_voice,
                residency=residency,
                mode=mode,
                private_safe_model_evidence=private_safe_model_evidence,
            )
            turn["engineering_pass"] = all(turn["checks"].values())
            unsafe_checks = {
                key: value
                for key, value in turn["checks"].items()
                if key != "preferred_gpu_route"
            }
            if not all(unsafe_checks.values()):
                raise LatencyAcceptanceError(
                    f"{phase_label} failed a required safe contract"
                )
            return turn, displayed, chat

        planned_turns = configured_turns
        if profile["voluntary_invitation_required"]:
            invitation_turn, invitation_reply, invitation_chat = capture_turn(
                profile["invitation_spec"],
                phase_label="voluntary_invitation_text_and_voice",
                private_safe_model_evidence=True,
            )
            sensory_lease = str(invitation_chat.get("sensory_lease") or sensory_lease)
            decision = classify_voluntary_public_reply(invitation_reply)
            invitation_turn["voluntary_decision"] = decision
            invitation_turn["measured_turn"] = False
            report["voluntary_invitation"] = invitation_turn
            report["participation_status"] = decision["decision"]
            planned_turns = measured_turn_plan(question_profile, invitation_reply)

        for index, turn_spec in enumerate(planned_turns, start=1):
            turn, displayed, chat = capture_turn(
                turn_spec,
                phase_label=f"turn_{index}_text_and_voice",
                private_safe_model_evidence=bool(
                    profile["private_safe_model_evidence_required"]
                ),
            )
            turn["measured_turn"] = True
            report["turns"].append(turn)
            sensory_lease = str(chat.get("sensory_lease") or sensory_lease)
            if profile["stop_after_every_turn_allowed"]:
                after_turn = classify_voluntary_after_turn_reply(
                    question_profile,
                    displayed,
                )
                turn["voluntary_after_turn"] = after_turn
                if after_turn["continue_measured_turns"] is not True:
                    report["participation_status"] = after_turn["decision"]
                    report["voluntary_stop_after_turn"] = {
                        "turn_index": index,
                        "turn_id": turn_spec["id"],
                        "decision": after_turn["decision"],
                    }
                    break

        sampler.mark("cleanup")
        purge = bounded.request_json(
            f"{bounded.BASE_URL}/api/sensory/purge",
            token=shell_token,
            method="POST",
            body={"sensory_lease": sensory_lease},
        )
        deactivate = bounded.request_json(
            f"{bounded.BASE_URL}/api/deactivate",
            token=shell_token,
            method="POST",
            body={},
        )
        deactivated = deactivate.get("ok") is True
        # Deactivation owns the session worker release.  Wait for its exact
        # append-only lifecycle evidence before asking the server to exit so a
        # daemon release thread cannot be hidden by process shutdown.
        release_event = wait_for_life_event(
            life_log,
            "voice_model_release",
            since_utc=activation_started_at,
            timeout_seconds=120,
        )
        release_contract = validate_voice_release_event(
            release_event,
            persistent_expected=bool(spec["persistent_voice"]),
            persistent_version=str(spec.get("persistent_version") or "v1"),
        )
        close = bounded.request_json(
            f"{bounded.BASE_URL}/api/safe-close",
            token=shell_token,
            method="POST",
            body={"reason": "two-turn latency acceptance complete"},
        )
        safe_closed = close.get("ok") is True
        server.wait(timeout=45)
        resident_before_exact_unload = bounded.ollama_inventory()
        llama_release = unload_exact_llama_if_owned(resident_before_exact_unload)
        ollama_after = wait_for_ollama_empty()
        validate_residency(ollama_after, expect_llama=False)
        port_evidence = measure_cleanup_ports()
        cleanup = {
            "sensory_buffer_purged": purge.get("ok") is True,
            "kira_deactivated": deactivated,
            "safe_close_accepted": safe_closed,
            "server_exit_code": server.returncode,
            "exact_owned_server_exited": server.returncode == 0,
            **port_evidence,
            "voice_model_release_event": _json_detach(release_event),
            "voice_model_release_contract": release_contract,
            "llama_release": llama_release,
            "ollama_after": ollama_after,
        }
    except Exception as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        server_was_running = server is not None and server.poll() is None
        forced_server_stop = False
        if server_was_running:
            try:
                if sensory_lease:
                    purge_result = bounded.request_json(
                        f"{bounded.BASE_URL}/api/sensory/purge",
                        token=shell_token,
                        method="POST",
                        body={"sensory_lease": sensory_lease},
                        timeout=5,
                    )
                    cleanup["sensory_buffer_purged"] = purge_result.get("ok") is True
            except Exception as exc:
                cleanup["sensory_purge_error"] = f"{type(exc).__name__}: {exc}"
            try:
                if not deactivated:
                    deactivate_result = bounded.request_json(
                        f"{bounded.BASE_URL}/api/deactivate",
                        token=shell_token,
                        method="POST",
                        body={},
                        timeout=5,
                    )
                    deactivated = deactivate_result.get("ok") is True
                cleanup["kira_deactivated"] = deactivated
            except Exception as exc:
                cleanup["kira_deactivated"] = False
                cleanup["deactivation_error"] = f"{type(exc).__name__}: {exc}"

        release_contract = cleanup.get("voice_model_release_contract")
        if not isinstance(release_contract, Mapping) or release_contract.get("passed") is not True:
            cleanup.update(
                capture_voice_release_cleanup_evidence(
                    life_log,
                    activation_started_at=activation_started_at,
                    persistent_expected=bool(spec["persistent_voice"]),
                    persistent_version=str(spec.get("persistent_version") or "v1"),
                    timeout_seconds=120.0 if server_was_running else 0.0,
                )
            )

        if server is not None and server.poll() is None:
            try:
                if not safe_closed:
                    close_result = bounded.request_json(
                        f"{bounded.BASE_URL}/api/safe-close",
                        token=shell_token,
                        method="POST",
                        body={"reason": "two-turn latency acceptance failure cleanup"},
                        timeout=5,
                    )
                    safe_closed = close_result.get("ok") is True
                cleanup["safe_close_accepted"] = safe_closed
                server.wait(timeout=20)
            except Exception as exc:
                cleanup["safe_close_error"] = f"{type(exc).__name__}: {exc}"
                forced_server_stop = True
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
        server_exit_code = server.poll() if server is not None else None
        cleanup.update(
            {
                "server_pid": server.pid if server is not None else None,
                "server_exit_code": server_exit_code,
                "server_forced_stop": forced_server_stop,
                "exact_owned_server_exited": bool(
                    server is not None and server_exit_code == 0
                ),
                **measure_cleanup_ports(),
            }
        )
        cleanup["exact_cleanup_validation"] = validate_exact_cleanup_evidence(cleanup)
        if sampler_started:
            sampler.mark("post_cleanup")
            gpu_samples = sampler.stop()
        else:
            gpu_samples = []
        try:
            resident = bounded.ollama_inventory()
            if _resident_rows(resident):
                cleanup.setdefault("llama_release_finally", unload_exact_llama_if_owned(resident))
            final_ollama = wait_for_ollama_empty()
        except Exception as exc:
            final_ollama = bounded.ollama_inventory()
            cleanup["llama_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        vram_return = _wait_for_vram_return(baseline_gpu)
        final_gpu = vram_return["final"]
        gpu_summary = summarize_gpu_samples(
            gpu_samples,
            baseline=baseline_gpu,
            final=final_gpu,
        )
        gpu_summary["return_wait"] = vram_return
        after_hashes = protected_hashes()
        memory_after = directory_manifest(memory_root)
        isolated_state = (
            json.loads(state_path.read_text(encoding="utf-8"))
            if state_path.is_file()
            else {}
        )
        cleanup.update(
            {
                "final_ollama": final_ollama,
                "active_candidate_after": isolated_state.get("active_candidate"),
                "browser_lease_after": isolated_state.get("browser_lease"),
            }
        )
        report["cleanup"] = cleanup
        report["gpu_telemetry"] = gpu_summary
        report["protected_after"] = after_hashes
        report["protected_files_unchanged"] = before_hashes == after_hashes
        report["memory_promotion_after"] = memory_after
        report["memory_promotion_unchanged"] = memory_before == memory_after
        report["finished_at"] = bounded.utc_now()
        invitation = report.get("voluntary_invitation")
        invitation_checks = (
            invitation.get("checks", {})
            if isinstance(invitation, Mapping)
            else {}
        )
        invitation_route = (
            invitation.get("voice", {}).get("route", {})
            if isinstance(invitation, Mapping)
            and isinstance(invitation.get("voice"), Mapping)
            else {}
        )
        participation_status = str(report.get("participation_status") or "")
        voluntary_profile = bool(profile["voluntary_invitation_required"])
        invitation_decision = (
            str((invitation.get("voluntary_decision") or {}).get("decision") or "")
            if isinstance(invitation, Mapping)
            else ""
        )
        clear_opt_in = (
            invitation_decision == "CLEAR_OPT_IN"
            if voluntary_profile
            else True
        )
        stopped_before_turns = voluntary_profile and participation_status in {
            "VOLUNTARY_DECLINE",
            "NO_CLEAR_OPT_IN",
        }
        stopped_after_turn = (
            voluntary_profile
            and participation_status == "VOLUNTARY_STOP_AFTER_TURN"
            and profile["stop_after_every_turn_allowed"] is True
        )
        clean_voluntary_stop = stopped_before_turns or stopped_after_turn
        expected_turn_count = len(configured_turns)
        completed_turn_count = len(report["turns"])
        full_measured_completion = bool(
            clear_opt_in
            and not stopped_after_turn
            and completed_turn_count == expected_turn_count
        )
        invitation_safe_contract = (
            isinstance(invitation, Mapping)
            and bool(invitation_checks)
            and all(
                value
                for key, value in invitation_checks.items()
                if key != "preferred_gpu_route"
            )
            and invitation_route.get("sapi_used") is False
            and invitation_route.get("generic_voice_used") is False
        ) if voluntary_profile else True
        cleanup_checks = {
            "protected_files_unchanged": before_hashes == after_hashes,
            "memory_promotion_unchanged": memory_before == memory_after,
            "person_inactive_after": not isolated_state.get("active_candidate"),
            "exact_server_cleanup": cleanup.get("exact_cleanup_validation", {}).get(
                "passed"
            )
            is True,
            "ollama_empty_after": not _resident_rows(final_ollama),
            "vram_returned": gpu_summary.get("vram_returned") is True,
            "routing_remained_sealed": routing.get("passed") is True,
        }
        completed_turns_safe = all(
            all(
                value
                for key, value in turn.get("checks", {}).items()
                if key != "preferred_gpu_route"
            )
            for turn in report["turns"]
        )
        completed_turns_preferred_gpu = all(
            turn.get("checks", {}).get("preferred_gpu_route") is True
            for turn in report["turns"]
        )
        report["checks"] = {
            "voluntary_invitation_contract": invitation_safe_contract,
            "clear_opt_in_before_measured_turns": clear_opt_in,
            "exact_configured_turn_count": completed_turn_count == expected_turn_count,
            "all_turn_safe_contracts": completed_turn_count == expected_turn_count
            and completed_turns_safe,
            "preferred_gpu_every_turn": completed_turn_count == expected_turn_count
            and completed_turns_preferred_gpu,
            **cleanup_checks,
            "no_sapi_or_generic": all(
                turn.get("voice", {}).get("route", {}).get("sapi_used") is False
                and turn.get("voice", {}).get("route", {}).get("generic_voice_used") is False
                for turn in report["turns"]
            ),
        }
        if expected_turn_count == 2:
            # Preserve the exact legacy two-turn result key.
            report["checks"]["exact_two_turns"] = completed_turn_count == 2
        else:
            report["checks"]["exact_extended_turns"] = (
                completed_turn_count == expected_turn_count
            )
        report["engineering_pass"] = bool(
            full_measured_completion and all(report["checks"].values())
        )
        report["acceptance_executed"] = bool(clear_opt_in and completed_turn_count)
        report["voluntary_outcome_not_failure"] = bool(clean_voluntary_stop)
        voluntary_turn_count_valid = bool(
            (stopped_before_turns and completed_turn_count == 0)
            or (
                stopped_after_turn
                and clear_opt_in
                and 1 <= completed_turn_count <= expected_turn_count
            )
        )
        report["voluntary_stop_cleanup_pass"] = bool(
            clean_voluntary_stop
            and invitation_safe_contract
            and voluntary_turn_count_valid
            and completed_turns_safe
            and all(cleanup_checks.values())
        )
        report["owner_heard_latency_acceptance"] = False
        report["owner_heard_latency_status"] = (
            "PARTIAL_MEASUREMENTS_RECORDED_VOLUNTARY_STOP"
            if stopped_after_turn
            else (
                "PENDING_OWNER_OBSERVED_FIRST_AUDIBLE_MEASUREMENT"
                if clear_opt_in
                else "NOT_APPLICABLE_VOLUNTARY_STOP_BEFORE_MEASURED_TURNS"
            )
        )
        report["passed"] = bool(report["engineering_pass"])
        if report["engineering_pass"]:
            report["status"] = "ENGINEERING_PASS_PENDING_OWNER_HEARING"
        elif report["voluntary_stop_cleanup_pass"]:
            if stopped_after_turn:
                report["status"] = "VOLUNTARILY_STOPPED_AFTER_TURN_CLEANLY"
            else:
                report["status"] = (
                    "VOLUNTARILY_DECLINED_CLEANLY"
                    if participation_status == "VOLUNTARY_DECLINE"
                    else "NO_CLEAR_OPT_IN_CLEANLY_STOPPED"
                )
        elif clean_voluntary_stop:
            report["status"] = "VOLUNTARY_STOP_CLEANUP_FAILED"
        else:
            report["status"] = "ENGINEERING_ACCEPTANCE_FAILED"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report_path, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--validate-prepared-config", default="")
    parser.add_argument("--validate-turing-prepared-config", action="store_true")
    parser.add_argument("--validate-extended-prepared-config", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-owner-supervised", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--confirm-speaker-playback", action="store_true")
    parser.add_argument("--confirm-voluntary-invitation", action="store_true")
    parser.add_argument("--mode", choices=sorted(MODE_SPECS), default="persistent_voice")
    parser.add_argument(
        "--question-profile",
        choices=sorted(QUESTION_PROFILES),
        default="owner_hearing_natural",
    )
    parser.add_argument("--keep-alive-duration", default="5m")
    parser.add_argument("--persistent-prerequisite-report", default="")
    args = parser.parse_args(argv)
    if str(args.validate_prepared_config).strip():
        try:
            validation = validate_prepared_owner_hearing_config(
                Path(args.validate_prepared_config)
            )
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "passed": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "live_operation_started": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0 if validation.get("passed") is True else 2
    if args.validate_turing_prepared_config:
        try:
            validation = validate_prepared_turing_psych_config()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "passed": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "live_operation_started": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0
    if args.validate_extended_prepared_config:
        try:
            validation = validate_prepared_extended_turing_psych_config()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "passed": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "live_operation_started": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0
    if args.describe or not args.execute_live:
        print(
            json.dumps(
                describe(args.mode, question_profile=args.question_profile),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    missing = [
        flag
        for flag, present in (
            ("--confirm-owner-supervised", args.confirm_owner_supervised),
            ("--confirm-no-active-blender", args.confirm_no_active_blender),
            ("--confirm-speaker-playback", args.confirm_speaker_playback),
            (
                "--confirm-voluntary-invitation",
                args.confirm_voluntary_invitation
                or not QUESTION_PROFILES[args.question_profile][
                    "voluntary_invitation_required"
                ],
            ),
        )
        if not present
    ]
    if missing:
        print(
            json.dumps(
                {
                    **describe(args.mode, question_profile=args.question_profile),
                    "ready": False,
                    "reason": "missing_explicit_live_confirmations",
                    "missing": missing,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    if args.question_profile == "turing_psych_non_private":
        try:
            validate_prepared_turing_psych_config()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        **describe(
                            args.mode,
                            question_profile=args.question_profile,
                        ),
                        "ready": False,
                        "reason": "Turing/psych prepared config did not validate",
                        "validation_error": f"{type(exc).__name__}: {exc}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
    if args.question_profile == "turing_psych_non_body_extended":
        try:
            validate_prepared_extended_turing_psych_config()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        **describe(
                            args.mode,
                            question_profile=args.question_profile,
                        ),
                        "ready": False,
                        "reason": "extended Turing/psych prepared config did not validate",
                        "validation_error": f"{type(exc).__name__}: {exc}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
    prerequisite = (
        Path(args.persistent_prerequisite_report)
        if str(args.persistent_prerequisite_report).strip()
        else None
    )
    try:
        report_path, report = run_live_acceptance(
            mode=args.mode,
            keep_alive_duration=normalized_keep_alive(args.keep_alive_duration),
            persistent_prerequisite_report=prerequisite,
            question_profile=args.question_profile,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "reason": f"{type(exc).__name__}: {exc}",
                    "live_operation_may_have_started": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "passed": report.get("passed") is True,
                "engineering_pass": report.get("engineering_pass") is True,
                "status": report.get("status"),
                "participation_status": report.get("participation_status"),
                "voluntary_outcome_not_failure": report.get(
                    "voluntary_outcome_not_failure"
                )
                is True,
                "owner_heard_latency_acceptance": False,
                "report": _relative(report_path),
                "report_sha256": _sha256_file(report_path),
                "production_defaults_changed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return (
        0
        if report.get("passed") is True
        or (
            report.get("voluntary_outcome_not_failure") is True
            and report.get("voluntary_stop_cleanup_pass") is True
        )
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
