"""Click-to-select TemporaryAI live chat.

This is a lightweight GUI wrapper around temporary_ai_live_chat.py so Robert
can choose a candidate by clicking its name instead of typing an id.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Canvas, Checkbutton, Frame, IntVar, Label, Listbox, Tk, filedialog, messagebox, scrolledtext
from typing import Any

from PIL import Image, ImageTk

from temporary_ai_live_chat import (
    OUT_DIR,
    PROJECT_ROOT,
    ask_model,
    archive_candidate,
    candidate_workbench_dir,
    finalize_model_artifacts,
    latest_candidates,
    load_candidate,
    now_iso,
    read_json,
    rel,
    refresh_candidate_sources,
    safe_output_name,
    save_reply_artifacts,
    source_grounded_text_route_readiness,
    source_readiness,
    source_readiness_label,
    slug,
    write_json,
)
from Core.downloaded_person_chat_catalog import (
    bind_review_and_voice_route,
    exact_candidate_voice_binding,
)
from Core.person_mind_runtime import finalize_person_turn
from Core.profile_bounded_candidate_review import (
    load_profile_bounded_candidate,
    profile_bounded_review_readiness,
)
from profile_bounded_candidate_chat import ask_profile_bounded_model

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_living_portrait import (
    POSE_ORDER,
    avatar_body_root,
    begins_with_greeting,
    ensure_avatar_body_manifest,
    ensure_avatar_build_plan,
    infer_emotion,
    pose_for_motion,
    resolve_avatar_pose_paths,
    speaking_seconds,
)
from Core.avatar_activity_state import discover_pose_manifest, discover_rigged_model, write_avatar_activity_state
from Core.embedded_edge_avatar import EmbeddedEdgeAvatar
from Core.portable_os_voice import (
    OSVoiceRoute,
    cached_candidate_os_voice_route,
    speak_with_os_voice,
)
from Core.private_self_voice_authorization import validate_private_self_voice_authorization
from Core.synthetic_robert_voice_route import is_synthetic_robert_persistent_identity
from tools.import_avatar_pose_sheet import import_pose_sheet

TEMP_AI_LOOP_ROOT = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_project_loops"
OLLAMA_HEALTH_URL = os.getenv("KIRA_OLLAMA_HEALTH_URL", "http://localhost:11434/api/tags")
OLLAMA_EXE = os.getenv("KIRA_OLLAMA_EXE", "")

try:
    from Core.voice_output import load_candidate_voice_config, speak_text
except Exception:
    load_candidate_voice_config = None
    speak_text = None


def _explicit_boolean(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "allowed", "enabled", "ready"}:
            return True
        if normalized in {"0", "false", "no", "off", "blocked", "disabled", "not_ready"}:
            return False
    return None


def _voice_profile_binding_reason(
    candidate: dict[str, Any],
    voice_profile: dict[str, Any],
) -> str:
    """Require exact candidate binding plus exact voice/target profile identity."""

    profile = candidate.get("profile") if isinstance(candidate.get("profile"), dict) else {}
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    declared_candidate_id = str(profile.get("candidate_id") or "").strip()
    if not candidate_id:
        return "candidate_id_missing"
    if not declared_candidate_id:
        return "candidate_profile_candidate_id_missing"
    if declared_candidate_id != candidate_id:
        return "candidate_profile_candidate_id_mismatch"

    binding = exact_candidate_voice_binding(candidate_id)
    if not isinstance(binding, dict):
        return "exact_candidate_voice_binding_missing"
    if str(binding.get("candidate_id") or "").strip() != candidate_id:
        return "exact_candidate_voice_binding_id_mismatch"
    if str(voice_profile.get("voice_id") or "").strip() != str(
        binding.get("expected_voice_id") or ""
    ).strip():
        return "voice_profile_voice_id_mismatch"
    if str(voice_profile.get("target_name") or "").strip() != str(
        binding.get("expected_target_name") or ""
    ).strip():
        return "voice_profile_target_name_mismatch"
    if str(voice_profile.get("target_type") or "").strip() != str(
        binding.get("expected_target_type") or ""
    ).strip():
        return "voice_profile_target_type_mismatch"
    if binding.get("profile_bounded_custom_voice_allowed") is True:
        if str(voice_profile.get("candidate_id") or "").strip() != candidate_id:
            return "voice_profile_candidate_id_mismatch"
    return ""


def _read_bound_voice_profile(
    path: Path,
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        binding = exact_candidate_voice_binding(str(candidate.get("candidate_id") or ""))
        expected_hash = (
            str(binding.get("expected_profile_sha256") or "").strip().lower()
            if isinstance(binding, dict)
            else ""
        )
        if not expected_hash or hashlib.sha256(raw).hexdigest() != expected_hash:
            return {}, "voice_profile_sha256_mismatch"
        payload = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"voice_profile_invalid_json:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return {}, "voice_profile_root_not_object"
    reason = _voice_profile_binding_reason(candidate, payload)
    return (payload, "") if not reason else ({}, reason)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bound_custom_voice_readiness(
    candidate: dict[str, Any],
    voice_profile: dict[str, Any],
    project_root: Path,
) -> tuple[bool, str]:
    """Validate exact private reconstruction profile status and WAV bytes."""

    candidate_id = str(candidate.get("candidate_id") or "").strip()
    binding = exact_candidate_voice_binding(candidate_id)
    if not isinstance(binding, dict):
        return False, "exact candidate voice binding is missing"
    if binding.get("profile_bounded_custom_voice_allowed") is not True:
        return False, "candidate-specific custom voice is not authorized for bounded review"
    if binding.get("authentic_voice_claim_allowed") is not False:
        return False, "custom voice binding lacks the required non-authentic boundary"

    status = voice_profile.get("status")
    status = status if isinstance(status, dict) else {}
    if status.get("ready_for_use") is not True:
        return False, "candidate-specific voice profile is not ready for use"
    if status.get("ready_for_text_tts") is not True:
        return False, "candidate-specific voice profile is not ready for text-to-speech"
    if status.get("bounded_profile_review_tts_allowed") is not True:
        return False, "candidate-specific voice profile is not approved for bounded review TTS"
    if status.get("authentic_voice_claim_allowed") is not False:
        return False, "candidate-specific voice profile lacks the non-authentic boundary"

    source_audio = voice_profile.get("source_audio")
    source_audio = source_audio if isinstance(source_audio, dict) else {}
    expected_path = str(binding.get("approved_reference_path") or "").replace("\\", "/")
    declared_path = str(source_audio.get("approved_reference_wav") or "").replace("\\", "/")
    expected_hash = str(binding.get("approved_reference_sha256") or "").strip().lower()
    declared_hash = str(source_audio.get("approved_reference_sha256") or "").strip().lower()
    if not expected_path or declared_path != expected_path:
        return False, "approved reference path does not match the exact candidate binding"
    if not expected_hash or declared_hash != expected_hash:
        return False, "approved reference hash declaration does not match the exact candidate binding"
    raw_path = Path(expected_path)
    if raw_path.is_absolute():
        return False, "approved reference path must be project-relative"
    try:
        root = project_root.resolve()
        reference_path = (root / raw_path).resolve()
        reference_path.relative_to(root)
    except (OSError, ValueError):
        return False, "approved reference path points outside this project"
    if not reference_path.is_file():
        return False, "approved reference WAV is absent from this checkout"
    try:
        if _file_sha256(reference_path) != expected_hash:
            return False, "approved reference WAV SHA-256 mismatch"
    except OSError:
        return False, "approved reference WAV could not be read"
    return True, ""


def _project_voice_profile_path(candidate: dict[str, Any], project_root: Path = PROJECT_ROOT) -> tuple[Path | None, str]:
    """Resolve only the profile declared by the exact candidate-id catalog row."""

    profile = candidate.get("profile") if isinstance(candidate.get("profile"), dict) else {}
    voice = profile.get("voice_and_behavior") if isinstance(profile.get("voice_and_behavior"), dict) else {}
    explicit_path = str(voice.get("voice_profile") or "").strip().replace("\\", "/")
    root = project_root.resolve()
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    binding = exact_candidate_voice_binding(candidate_id)
    if not isinstance(binding, dict):
        return None, "No exact candidate-id voice binding is declared."
    expected_relative = str(binding.get("voice_profile_path") or "").strip().replace("\\", "/")
    if not expected_relative or Path(expected_relative).is_absolute():
        return None, "The exact candidate voice binding has an invalid profile path."
    try:
        expected_path = (root / expected_relative).resolve()
        expected_path.relative_to(root)
    except (OSError, ValueError):
        return None, "The exact candidate voice binding points outside this project."
    if explicit_path:
        raw = Path(explicit_path)
        if raw.is_absolute():
            return None, "The configured voice profile must be a file inside this Kira project."
        try:
            resolved = (root / raw).resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            return None, "The configured voice profile points outside this Kira project."
        if resolved != expected_path:
            return None, "The configured voice profile does not match the exact candidate-id binding."
        if not resolved.is_file():
            return None, f"The configured candidate voice profile is missing: {explicit_path}"
        _payload, binding_reason = _read_bound_voice_profile(resolved, candidate)
        if binding_reason:
            return None, f"Configured voice profile identity binding failed: {binding_reason}"
        return resolved, ""

    if not expected_path.is_file():
        return None, f"The exactly bound candidate voice profile is missing: {expected_relative}"
    _payload, binding_reason = _read_bound_voice_profile(expected_path, candidate)
    if binding_reason:
        return None, f"Mapped voice profile identity binding failed: {binding_reason}"
    return expected_path, ""


_RUNTIME_ERROR_REPLY_PREFIXES = (
    "[TemporaryAI - model offline]",
    "[TemporaryAI - error]",
    "[Draft review - profile-bounded] The local model is offline.",
    "[Draft review - profile-bounded] The bounded review could not answer",
)


def _runtime_error_reply_reason(answer: object) -> str:
    text = str(answer or "").strip()
    for prefix in _RUNTIME_ERROR_REPLY_PREFIXES:
        if text.startswith(prefix):
            return "runtime_source_or_model_error_text"
    return ""


def _voice_text_route_readiness(
    candidate: dict[str, Any],
) -> tuple[bool, str, list[str]]:
    """Revalidate the text route appropriate to this exact review mode."""

    review_mode = str(candidate.get("review_mode") or "").strip()
    if review_mode == "profile_bounded_draft":
        try:
            ready, reasons = profile_bounded_review_readiness(candidate)
        except Exception as exc:
            return False, f"profile_bounded_text_route_check_error:{type(exc).__name__}", []
        if ready is not True:
            return False, "profile_bounded_text_route_denied", [str(item) for item in (reasons or [])]
        decision = candidate.get("text_route_decision")
        decision = decision if isinstance(decision, dict) else {}
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        exact_binding = exact_candidate_voice_binding(candidate_id)
        bounded_custom_voice = bool(
            isinstance(exact_binding, dict)
            and exact_binding.get("profile_bounded_custom_voice_allowed") is True
            and exact_binding.get("authentic_voice_claim_allowed") is False
        )
        required = {
            "allowed": True,
            "review_mode": "profile_bounded_draft",
            "full_source_grounding_complete": False,
            "profile_bounded_label_required": True,
            "voice_output_allowed": True,
            "custom_voice_output_allowed": bounded_custom_voice,
            "generic_os_voice_output_allowed": True,
            "error_or_exception_text_may_reach_tts": False,
        }
        if any(decision.get(key) != value for key, value in required.items()):
            return False, "profile_bounded_text_route_binding_invalid", []
        if exact_binding is not None and candidate.get("voice_route_binding") != exact_binding:
            return False, "profile_bounded_voice_binding_invalid", []
        return True, "", []

    try:
        ready, reasons = source_grounded_text_route_readiness(candidate)
    except Exception as exc:
        return False, f"source_grounded_text_route_check_error:{type(exc).__name__}", []
    if ready is not True:
        return False, "source_grounded_text_route_denied", [str(item) for item in (reasons or [])]
    return True, "", []


def candidate_voice_output_decision(candidate: dict[str, Any], project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Prefer a ready custom pack, then discover a labeled local OS voice.

    Conversation authorization remains fail-closed.  An OS voice is only an
    output fallback for a character that is otherwise allowed to speak; it
    does not bypass a text-only activation plan or claim an authentic voice.
    """

    profile = candidate.get("profile") if isinstance(candidate.get("profile"), dict) else {}
    activation = profile.get("activation_policy") if isinstance(profile.get("activation_policy"), dict) else {}
    voice = profile.get("voice_and_behavior") if isinstance(profile.get("voice_and_behavior"), dict) else {}
    plan = candidate.get("activation_plan") if isinstance(candidate.get("activation_plan"), dict) else {}
    mode_readiness = plan.get("mode_readiness") if isinstance(plan.get("mode_readiness"), dict) else {}
    plan_voice = mode_readiness.get("voice_chat") if isinstance(mode_readiness.get("voice_chat"), dict) else {}
    plan_text = mode_readiness.get("text_chat") if isinstance(mode_readiness.get("text_chat"), dict) else {}
    display = str(profile.get("display_name") or candidate.get("candidate_id") or "This candidate")
    candidate_id = str(candidate.get("candidate_id") or profile.get("candidate_id") or "").strip()
    if is_synthetic_robert_persistent_identity(candidate):
        return {
            "allowed": False,
            "reason": (
                "Synthetic Robert is a persistent-runtime person, not a TemporaryAI; "
                "use his separate portable persistent runtime and approved self-voice route."
            ),
            "route_kind": "persistent_runtime_route_required",
            "profile_path": None,
            "display": display,
        }

    text_route_ready, text_route_reason, text_route_reasons = _voice_text_route_readiness(candidate)
    if not text_route_ready:
        reasons = ", ".join(str(item) for item in text_route_reasons[:4])
        if text_route_reason.endswith("_check_error:RuntimeError"):
            public_reason = "The text-route readiness check failed closed (RuntimeError)."
        elif "_check_error:" in text_route_reason:
            public_reason = (
                "The text-route readiness check failed closed "
                f"({text_route_reason.rsplit(':', 1)[-1]})."
            )
        else:
            public_reason = "The text route denied voice output" + (f" ({reasons})." if reasons else ".")
        return {
            "allowed": False,
            "reason": public_reason,
            "route_kind": text_route_reason.split(":", 1)[0],
            "profile_path": None,
            "display": display,
        }
    text_route_decision = candidate.get("text_route_decision")
    text_route_decision = text_route_decision if isinstance(text_route_decision, dict) else {}
    profile_bounded_generic_route = (
        str(candidate.get("review_mode") or "").strip() == "profile_bounded_draft"
    )
    if text_route_decision and (
        text_route_decision.get("allowed") is not True
        or text_route_decision.get("voice_output_allowed") is not True
        or text_route_decision.get("error_or_exception_text_may_reach_tts") is not False
    ):
        return {
            "allowed": False,
            "reason": "The bound text route does not authorize voice output.",
            "route_kind": "bound_text_route_denied",
            "profile_path": None,
            "display": display,
        }

    if (
        not profile_bounded_generic_route
        and _explicit_boolean(plan_text.get("ready")) is False
    ):
        reason = str(plan_text.get("reason") or "The candidate activation plan has not approved text conversation.").strip()
        return {"allowed": False, "reason": reason, "profile_path": None, "display": display}

    text_permissions: list[bool] = []
    for source in (activation, profile):
        for key in (
            "bounded_text_only_conversation_allowed",
            "bounded_text_conversation_allowed",
            "bounded_owner_text_probe_allowed",
            "owner_probe_allowed",
            "text_chat_allowed",
            "text_voice_chat_allowed",
        ):
            if key in source:
                value = _explicit_boolean(source.get(key))
                if value is not None:
                    text_permissions.append(value)
    text_explicitly_allowed = any(text_permissions)
    text_explicitly_blocked = bool(text_permissions) and not text_explicitly_allowed
    if profile_bounded_generic_route:
        # The profile-bounded readiness check and exact bound route decision
        # above are the authorization for this visibly labelled draft route.
        # A production activation-plan voice denial still blocks custom voice,
        # but must not erase the separately authorized generic OS fallback.
        text_explicitly_allowed = True
        text_explicitly_blocked = False
    if text_explicitly_blocked:
        return {
            "allowed": False,
            "reason": str(
                plan_text.get("reason")
                or activation.get("block_reason")
                or "This candidate is not approved for bounded text conversation."
            ).strip(),
            "profile_path": None,
            "display": display,
        }

    bounded_voice = None
    for source in (activation, voice, profile):
        if "bounded_voice_conversation_allowed" in source:
            bounded_voice = _explicit_boolean(source.get("bounded_voice_conversation_allowed"))
            break
    text_voice = None
    for source in (activation, profile):
        if "text_voice_chat_allowed" in source:
            text_voice = _explicit_boolean(source.get("text_voice_chat_allowed"))
            break
    exact_binding = exact_candidate_voice_binding(candidate_id)
    bounded_custom_voice_authorized = bool(
        profile_bounded_generic_route
        and isinstance(exact_binding, dict)
        and exact_binding.get("profile_bounded_custom_voice_allowed") is True
        and exact_binding.get("authentic_voice_claim_allowed") is False
        and text_route_decision.get("custom_voice_output_allowed") is True
    )
    custom_voice_plan_blocked = False if bounded_custom_voice_authorized else bool(
        _explicit_boolean(plan_voice.get("ready")) is False
        or bounded_voice is False
        or (bounded_voice is None and text_voice is False)
        or _explicit_boolean(voice.get("voice_assignment_allowed")) is False
        or (
            text_route_decision
            and text_route_decision.get("custom_voice_output_allowed") is not True
        )
    )
    if custom_voice_plan_blocked and not text_explicitly_allowed:
        reason = str(
            plan_voice.get("reason")
            or activation.get("block_reason")
            or "This candidate has no approved text conversation route."
        ).strip()
        return {"allowed": False, "reason": reason, "profile_path": None, "display": display}
    voice_profile_path, path_reason = _project_voice_profile_path(candidate, project_root)
    voice_profile: dict[str, Any] = {}
    if voice_profile_path:
        voice_profile, rebound_reason = _read_bound_voice_profile(voice_profile_path, candidate)
        if rebound_reason:
            path_reason = f"Voice profile identity binding changed during read: {rebound_reason}"
            voice_profile_path = None
    status = voice_profile.get("status") if isinstance(voice_profile.get("status"), dict) else {}
    source_audio = voice_profile.get("source_audio") if isinstance(voice_profile.get("source_audio"), dict) else {}
    reference = str(source_audio.get("approved_reference_wav") or "").strip().replace("\\", "/")
    sapi = voice_profile.get("sapi_approximation") if isinstance(voice_profile.get("sapi_approximation"), dict) else {}
    custom_integrity_ready, custom_integrity_reason = _bound_custom_voice_readiness(
        candidate,
        voice_profile,
        project_root,
    )
    custom_authorization_allowed = True
    custom_authorization_reason = ""
    if voice.get("voice_authorization") and voice_profile_path:
        authorization = validate_private_self_voice_authorization(candidate_id, profile, project_root=project_root)
        if not authorization.get("allowed"):
            details = ", ".join(str(item) for item in authorization.get("reasons", [])[:3])
            custom_authorization_allowed = False
            custom_authorization_reason = (
                "The bound private voice authorization did not validate"
                + (f" ({details})." if details else ".")
            )

    custom_ready = bool(
        voice_profile_path
        and custom_integrity_ready
        and status.get("ready_for_use") is True
        and status.get("ready_for_text_tts") is True
        and custom_authorization_allowed
        and not custom_voice_plan_blocked
    )

    generic_os_voice_allowed = bool(
        not text_route_decision
        or text_route_decision.get("generic_os_voice_output_allowed") is True
    )

    preferred_windows_voice = str(sapi.get("voice_name") or "").strip()
    os_route = (
        cached_candidate_os_voice_route(
            candidate_id,
            display,
            str(profile.get("gender_preference") or ""),
            preferred_windows_voice,
        )
        if generic_os_voice_allowed
        else OSVoiceRoute(
            False,
            sys.platform,
            reason="bound_text_route_denies_generic_os_voice",
        )
    )
    fallback_payload = os_route.to_dict()
    if custom_ready:
        label = str(
            (exact_binding or {}).get("review_label")
            or voice_profile.get("target_name")
            or voice_profile.get("name")
            or display
        ).strip()
        return {
            "allowed": True,
            "reason": "",
            "route_kind": "custom_voice_pack",
            "profile_path": voice_profile_path,
            "profile_label": label,
            "authentic_voice_claim": False,
            "review_mode_label_required": profile_bounded_generic_route,
            "display": display,
            "os_fallback_route": fallback_payload if os_route.available else None,
            "os_fallback_reason": "" if os_route.available else os_route.reason,
        }

    # Preserve an exact configured-path/profile binding failure as the primary
    # reason; a later generic readiness result must not hide a cross-person or
    # byte-tampering attempt.  A candidate with no custom binding at all may
    # still report its more useful plan/status reason before falling back.
    binding_failure_primary = (
        path_reason
        if any(
            marker in path_reason
            for marker in (
                "does not match the exact candidate-id binding",
                "identity binding failed",
                "points outside this project",
                "must be a file inside this Kira project",
            )
        )
        else ""
    )
    custom_reason = binding_failure_primary or custom_authorization_reason
    if not custom_reason and custom_voice_plan_blocked:
        custom_reason = str(
            plan_voice.get("reason")
            or "candidate-specific/custom voice route is not approved"
        ).strip()
    if not custom_reason and voice_profile_path and status.get("ready_for_use") is False:
        custom_reason = "candidate-specific voice profile is not ready for use"
    if not custom_reason and voice_profile_path and status.get("ready_for_text_tts") is not True:
        custom_reason = "candidate-specific voice profile is not ready for text-to-speech"
    if not custom_reason and not custom_integrity_ready:
        custom_reason = custom_integrity_reason
    if not custom_reason and voice_profile_path and not reference:
        custom_reason = "candidate has no approved custom reference audio"
    if not custom_reason:
        custom_reason = path_reason or "candidate has no valid custom voice pack"

    if not os_route.available:
        return {
            "allowed": False,
            "reason": (
                f"{custom_reason}; installed operating-system voice unavailable "
                f"({os_route.reason})."
            ),
            "route_kind": "none",
            "profile_path": voice_profile_path,
            "display": display,
            "os_fallback_route": None,
        }
    return {
        "allowed": True,
        "reason": "",
        "route_kind": "os_voice_fallback",
        "profile_path": voice_profile_path,
        "profile_label": f"{os_route.voice_name} (generic {os_route.platform} OS voice)",
        "display": display,
        "os_fallback_route": fallback_payload,
        "custom_voice_unavailable_reason": custom_reason,
    }


def speak_candidate_reply(
    answer: str,
    candidate: dict[str, Any],
    decision: dict[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Revalidate identity/source/route, then try custom before generic OS."""

    if not decision.get("allowed"):
        return {"spoken": False, "reason": str(decision.get("reason") or "voice_not_allowed")}
    if is_synthetic_robert_persistent_identity(candidate):
        return {
            "spoken": False,
            "reason": "synthetic_robert_persistent_runtime_voice_route_required",
            "route_kind": "persistent_runtime_route_required",
        }
    runtime_error_reason = _runtime_error_reply_reason(answer)
    if runtime_error_reason:
        return {
            "spoken": False,
            "reason": runtime_error_reason,
            "route_kind": "none",
        }
    text_route_ready, text_route_reason, text_route_reasons = _voice_text_route_readiness(candidate)
    if not text_route_ready:
        return {
            "spoken": False,
            "reason": text_route_reason,
            "text_route_reasons": text_route_reasons,
            "route_kind": "none",
        }

    # A decision crosses a thread boundary and is therefore only a hint.  The
    # exact candidate/source/profile/installed-OS route is rebuilt here so a
    # stale or crafted dictionary cannot select another person's voice.
    fresh_decision = candidate_voice_output_decision(candidate, project_root)
    if not fresh_decision.get("allowed"):
        return {
            "spoken": False,
            "reason": str(fresh_decision.get("reason") or "voice_revalidation_failed"),
            "route_kind": str(fresh_decision.get("route_kind") or "none"),
        }
    decision = fresh_decision
    fallback_data = decision.get("os_fallback_route")
    fallback_route = OSVoiceRoute(**fallback_data) if isinstance(fallback_data, dict) else None
    if decision.get("route_kind") == "custom_voice_pack":
        if speak_text is not None and load_candidate_voice_config is not None:
            try:
                profile = deepcopy(candidate.get("profile", {}) or {})
                voice = profile.get("voice_and_behavior") if isinstance(profile.get("voice_and_behavior"), dict) else {}
                voice = dict(voice)
                resolved_profile_path = Path(decision["profile_path"]).resolve()
                voice["voice_profile"] = resolved_profile_path.relative_to(
                    project_root.resolve()
                ).as_posix()
                profile["voice_and_behavior"] = voice
                primary = speak_text(answer, load_candidate_voice_config(profile))
                if isinstance(primary, dict) and primary.get("spoken") is True:
                    return {
                        **primary,
                        "route_kind": "custom_voice_pack",
                        "fallback_attempted": False,
                        "profile_label": decision.get("profile_label"),
                        "authentic_voice_claim": False,
                        "review_mode_label_required": decision.get(
                            "review_mode_label_required", False
                        ),
                    }
                if not isinstance(primary, dict):
                    primary = {"spoken": False, "reason": "custom_voice_backend_invalid_result"}
            except Exception as exc:
                primary = {
                    "spoken": False,
                    "reason": "custom_voice_backend_error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
        else:
            primary = {"spoken": False, "reason": "custom_voice_backend_not_loaded"}
        if fallback_route is None:
            return {**primary, "route_kind": "custom_voice_pack", "fallback_attempted": False}
        fallback = speak_with_os_voice(answer, fallback_route)
        return {
            **fallback,
            "route_kind": "os_voice_fallback",
            "fallback_attempted": True,
            "custom_voice_result": primary,
        }
    if fallback_route is None:
        return {"spoken": False, "reason": "os_voice_route_missing", "route_kind": "none"}
    return {
        **speak_with_os_voice(answer, fallback_route),
        "route_kind": "os_voice_fallback",
        "fallback_attempted": False,
    }


def ollama_executable() -> str:
    if OLLAMA_EXE:
        return OLLAMA_EXE
    found = shutil.which("ollama")
    if found:
        return found
    local = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
    if local.exists():
        return str(local)
    return ""


def ollama_available(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_HEALTH_URL, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def ensure_ollama_running(timeout: float = 15.0) -> tuple[bool, str]:
    if ollama_available(timeout=2.0):
        return True, "Ollama is running."
    exe = ollama_executable()
    if not exe:
        return False, "Ollama is not running and ollama.exe was not found."
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        subprocess.Popen(
            [exe, "serve"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except Exception as exc:
        return False, f"Ollama is not running and could not be started: {exc}"

    deadline = time.time() + timeout
    while time.time() < deadline:
        if ollama_available(timeout=2.0):
            return True, "Ollama was started."
        time.sleep(1)
    return False, "Ollama was started, but the local model endpoint did not answer yet."


def load_candidate_for_review_chat(candidate_id: str) -> dict[str, Any]:
    """Prefer the full source-grounded route, then a labelled draft review.

    A clean checkout may intentionally omit unfinished/private source-pack
    inputs.  That must not weaken the strict loader.  Incomplete candidates
    instead receive a separate profile-only review context whose replies are
    visibly labelled and cannot claim activation, memories, voice identity,
    body, or world presence.
    """

    full_failure = ""
    try:
        candidate = load_candidate(candidate_id)
        route_ready, route_reasons = source_grounded_text_route_readiness(candidate)
        readiness = source_readiness(candidate)
        if route_ready and readiness.get("status") in {
            "ready",
            "source_grounding_reviewed",
        }:
            return bind_review_and_voice_route(
                candidate,
                review_mode="full_source_grounded_review",
            )
        full_failure = ",".join(
            [str(readiness.get("status") or "source_readiness_incomplete")]
            + [str(reason) for reason in route_reasons]
        )
    except Exception as exc:
        full_failure = f"{type(exc).__name__}:{exc}"

    candidate = load_profile_bounded_candidate(PROJECT_ROOT, candidate_id)
    return bind_review_and_voice_route(
        candidate,
        review_mode="profile_bounded_draft",
        full_source_reason=full_failure,
    )


def initial_candidate_index(
    candidate_paths: list[Path],
    requested_candidate_id: object,
) -> int | None:
    """Resolve only an exact checked-in candidate id from launcher input."""

    requested = str(requested_candidate_id or "").strip()
    if not requested:
        return None
    for index, path in enumerate(candidate_paths):
        if path.name == requested:
            return index
    return None


class TemporaryAILiveChatGUI:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("TemporaryAI Live Chat")
        self.root.geometry("1500x820")
        self.root.minsize(1260, 720)
        self.root.configure(bg="#0b1220")

        self.candidate_paths: list[Path] = []
        self.candidate = None
        self.display = "TemporaryAI"
        self.role = ""
        self.history: list[dict[str, str]] = []
        self.records: list[dict] = []
        self.last_answer = ""
        self.json_path: Path | None = None
        self.monitor_path: Path | None = None
        self.worker_queue: queue.Queue[tuple[str, str, list[str]]] = queue.Queue()
        # Voice is always an explicit per-person opt-in.  A checked box from a
        # previous session/person must never cause a new candidate to speak.
        self.voice_enabled = IntVar(value=0)
        self.preview_photo = None
        self.visual_photo = None
        self.visual_source_image = None
        self.visual_source_path: Path | None = None
        self.visual_pose_images: dict[str, Image.Image] = {}
        self.visual_pose_paths: dict[str, Path] = {}
        self.visual_form = "auto"
        self.visual_motion = "idle"
        self.visual_emotion = "calm"
        self.visual_motion_until = 0.0
        self.visual_tick = 0
        self.loop_process: subprocess.Popen | None = None
        self.avatar_process: subprocess.Popen | None = None
        self.loop_run_id = ""
        self.loop_json_path: Path | None = None
        self.loop_monitor_path: Path | None = None
        self.loop_stop_path: Path | None = None
        self.loop_live_notes_path: Path | None = None
        self.loop_worker_log_path: Path | None = None
        self.embedded_start_after_id = None
        self.embedded_candidate_id = ""
        self.closing = False

        self.build_ui()
        self.embedded_avatar = EmbeddedEdgeAvatar(self.avatar_host, PROJECT_ROOT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.reload_candidates()
        self.apply_initial_candidate_selection_from_environment()
        self.root.after(200, self.drain_worker_queue)
        self.root.after(2000, self.poll_life_loop)
        self.root.after(120, self.animate_visual)
        self.root.after(200, self.poll_embedded_avatar)

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=330)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))
        visual = Frame(outer, bg="#111827", bd=1, relief="solid", width=300)
        visual.pack(side=RIGHT, fill=Y, padx=(10, 0))
        visual.pack_propagate(False)
        right = Frame(outer, bg="#111827", bd=1, relief="solid")
        right.pack(side=LEFT, fill=BOTH, expand=True)

        Label(left, text="TemporaryAI Candidates", fg="#f9fafb", bg="#111827", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        Label(left, text="Click a name, then Start Chat.", fg="#cbd5e1", bg="#111827").pack(anchor="w", padx=12, pady=(0, 8))
        self.candidate_list = Listbox(left, bg="#0b1220", fg="#f9fafb", selectbackground="#2563eb", height=13)
        self.candidate_list.pack(fill=X, expand=False, padx=12, pady=(0, 6))
        self.candidate_list.bind("<Double-Button-1>", lambda _event: self.start_selected_chat())
        self.candidate_list.bind("<<ListboxSelect>>", lambda _event: self.update_candidate_preview())

        self.preview_box = Label(
            left,
            text="No preview image",
            fg="#94a3b8",
            bg="#0b1220",
            bd=1,
            relief="solid",
            wraplength=240,
            justify="center",
        )
        self.preview_box.pack(fill=X, padx=12, pady=(0, 2))
        self.preview_caption = Label(
            left,
            text="",
            fg="#94a3b8",
            bg="#111827",
            wraplength=250,
            justify="center",
        )
        self.preview_caption.pack(fill=X, padx=12, pady=(0, 8))

        Button(left, text="Start Chat With Selected", command=self.start_selected_chat, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Reload Candidates", command=self.reload_candidates, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Refresh Sources", command=self.refresh_selected_sources, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Open Candidate Folder", command=self.open_selected_folder, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Open Workbench Projects", command=self.open_workbench_projects, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Archive Selected", command=self.archive_selected_candidate, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Save Last Reply", command=self.save_last_reply, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Start Life Loop", command=self.start_life_loop, height=1).pack(fill=X, padx=12, pady=(8, 2))
        Button(left, text="End Life Loop Safely", command=self.end_life_loop_safely, height=1).pack(fill=X, padx=12, pady=2)
        Button(left, text="Open Life Loop Log", command=self.open_life_loop_log, height=1).pack(fill=X, padx=12, pady=2)
        self.voice_toggle = Checkbutton(
            left,
            text="Voice output",
            variable=self.voice_enabled,
            command=self.on_voice_toggle,
            bg="#111827",
            fg="#f9fafb",
            selectcolor="#1f2937",
            activebackground="#111827",
            activeforeground="#f9fafb",
        )
        self.voice_toggle.pack(anchor="w", padx=12, pady=(8, 4))

        Label(visual, text="Current Appearance", fg="#f9fafb", bg="#111827", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        form_row = Frame(visual, bg="#111827")
        form_row.pack(fill=X, padx=12, pady=(0, 8))
        Button(form_row, text="Auto", command=lambda: self.set_visual_form("auto")).pack(side=LEFT, fill=X, expand=True, padx=(0, 2))
        Button(form_row, text="Civilian", command=lambda: self.set_visual_form("civilian")).pack(side=LEFT, fill=X, expand=True, padx=2)
        Button(form_row, text="Hero", command=lambda: self.set_visual_form("hero")).pack(side=LEFT, fill=X, expand=True, padx=(2, 0))
        self.avatar_host = Frame(
            visual,
            bg="#0b1220",
            bd=1,
            relief="solid",
            width=270,
            height=500,
        )
        self.avatar_host.pack(fill=BOTH, expand=True, padx=12, pady=(0, 6))
        self.avatar_host.pack_propagate(False)
        self.visual_box = Canvas(
            self.avatar_host,
            bg="#0b1220",
            bd=0,
            highlightthickness=0,
            width=270,
            height=500,
        )
        self.visual_box.pack(fill=BOTH, expand=True)
        self.visual_caption = Label(visual, text="", fg="#cbd5e1", bg="#111827", wraplength=270, justify="left")
        self.visual_caption.pack(fill=X, padx=12, pady=(0, 6))
        self.voice_status = Label(visual, text="Voice: not checked", fg="#93c5fd", bg="#111827", wraplength=270, justify="left")
        self.voice_status.pack(fill=X, padx=12, pady=(0, 8))
        Button(visual, text="Import Reviewed Appearance", command=self.import_reviewed_appearance).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Import Generated Pose Sheet", command=self.import_generated_pose_sheet).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Open Avatar References", command=self.open_avatar_references).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Open Generated Body Folder", command=self.open_generated_body_folder).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Restart Embedded 3D Avatar", command=self.open_3d_avatar).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Open Avatar Build Plan", command=self.open_avatar_build_plan).pack(fill=X, padx=12, pady=2)
        Button(visual, text="Open Voice Review", command=self.open_voice_review).pack(fill=X, padx=12, pady=(2, 12))

        self.status = Label(right, text="Select a candidate to begin.", fg="#93c5fd", bg="#111827", anchor="w")
        self.status.pack(fill=X, padx=12, pady=(12, 4))
        self.chat = scrolledtext.ScrolledText(right, wrap="word", bg="#0b1220", fg="#f9fafb", insertbackground="#f9fafb")
        self.chat.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))
        self.input = scrolledtext.ScrolledText(right, wrap="word", bg="#1f2937", fg="#f9fafb", insertbackground="#f9fafb", height=4)
        self.input.pack(fill=X, padx=12, pady=(0, 8))
        self.input.bind("<Return>", self.on_enter)
        row = Frame(right, bg="#111827")
        row.pack(fill=X, padx=12, pady=(0, 12))
        Button(row, text="Send", command=self.send_message, height=2).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row, text="Quit", command=self.close, height=2).pack(side=RIGHT, fill=X, expand=True, padx=(4, 0))

    def log_chat(self, speaker: str, text: str) -> None:
        self.chat.insert(END, f"{speaker}  {datetime.now().strftime('%I:%M %p')}\n{text}\n\n")
        self.chat.see(END)

    def reload_candidates(self) -> None:
        self.candidate_paths = latest_candidates(limit=50)
        self.candidate_list.delete(0, END)
        for path in self.candidate_paths:
            try:
                candidate = load_candidate_for_review_chat(path.name)
                profile = candidate.get("profile", {})
                readiness = (
                    "profile-bounded draft"
                    if candidate.get("review_mode") == "profile_bounded_draft"
                    else source_readiness_label(candidate)
                )
            except Exception:
                profile = read_json(path / "temporary_ai_profile.json", {})
                readiness = "load error"
            display = profile.get("display_name", path.name)
            role = profile.get("role_title", "")
            label = f"{display} - {role}" if role else display
            label = f"[{readiness}] {label}"
            self.candidate_list.insert(END, label)
        if self.candidate_paths:
            self.candidate_list.selection_set(0)
            self.update_candidate_preview()
        self.status.config(text=f"Loaded {len(self.candidate_paths)} candidate(s).")

    def apply_initial_candidate_selection_from_environment(self) -> bool:
        """Open the exact candidate selected by the unified local launcher."""

        requested = os.getenv("TEMP_AI_INITIAL_CANDIDATE_ID", "").strip()
        if not requested:
            return False
        index = initial_candidate_index(self.candidate_paths, requested)
        if index is None:
            self.status.config(
                text=(
                    "The requested candidate is not present in this checkout; "
                    "select an available candidate."
                )
            )
            return False
        self.candidate_list.selection_clear(0, END)
        self.candidate_list.selection_set(index)
        self.candidate_list.see(index)
        self.update_candidate_preview()
        self.status.config(text=f"Opening exact candidate: {requested}")
        # Starting the review does not call the model or enable voice.  It only
        # prepares the selected text session; the first user message remains
        # the first generation request and voice stays an explicit checkbox.
        self.root.after(0, self.start_selected_chat)
        return True

    def candidate_avatar_manifest_path(self, candidate_id: str) -> Path:
        return PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "references" / "avatar_reference_manifest.json"

    def desktop_intake_reference_items(self, candidate_id: str) -> list[dict]:
        root = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "references" / "desktop_intake"
        if not root.exists():
            return []
        images: list[Path] = []
        for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            images.extend(root.rglob(suffix))
        candidate_key = candidate_id.lower()

        def intake_rank(path: Path) -> tuple[int, float]:
            name = path.stem.lower()
            score = 0
            if "fullview" in name or "full_body" in name:
                score += 8
            if "supergirl_from_my_adventures" in name or "kara_zor" in name:
                score += 6
            if "kathryn_merteuil" in name or "cameron_phillips" in name:
                score += 6
            if "kara" in candidate_key and any(token in name for token in ("jimmy_and_kara", "eye_to_eye", "with_clark")):
                score -= 20
            return score, path.stat().st_mtime

        ranked_images = sorted(images, key=intake_rank, reverse=True)
        return [
            {
                "title": path.name,
                "source_title": "Desktop avatar reference intake",
                "provider": "Robert-provided reference intake",
                "status": "intake_pending_review",
                "review_required": True,
                "local_file": rel(path),
                "form": "unknown",
                "view": "unclassified",
                "full_body_reviewed": False,
            }
            for path in ranked_images
        ]

    def first_available_image_path(self, candidate_id: str) -> Path | None:
        manifest_path = self.candidate_avatar_manifest_path(candidate_id)
        manifest = read_json(manifest_path, {})
        for item in manifest.get("references", []) or []:
            status = str(item.get("status", "")).lower()
            if status.startswith("rejected") or status in {"wrong_version", "archived"}:
                continue
            local_file = item.get("local_file", "")
            if not local_file:
                continue
            path = Path(str(local_file))
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if path.exists():
                return path
        # A manifest is authoritative. Do not revive rejected images merely
        # because their old files remain in the download folder. Robert's
        # separate desktop intake is allowed as a clearly unreviewed fallback.
        if manifest_path.exists():
            intake = self.desktop_intake_reference_items(candidate_id)
            if intake:
                path = PROJECT_ROOT / str(intake[0]["local_file"])
                return path if path.exists() else None
            return None
        downloaded = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "references" / "downloaded"
        if downloaded.exists():
            for path in sorted(downloaded.iterdir()):
                if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    return path
        return None

    def first_preview_image_path(self, candidate_id: str) -> Path | None:
        """Use the strongest reviewed character reference, not the first download."""
        image_path, _item = self.best_visual_image(candidate_id)
        return image_path

    def avatar_reference_items(self, candidate_id: str) -> list[dict]:
        manifest = read_json(self.candidate_avatar_manifest_path(candidate_id), {})
        items = [item for item in (manifest.get("references", []) or []) if isinstance(item, dict)]
        known = {str(item.get("local_file", "")) for item in items}
        items.extend(
            item for item in self.desktop_intake_reference_items(candidate_id)
            if str(item.get("local_file", "")) not in known
        )
        return items

    def best_visual_image(self, candidate_id: str) -> tuple[Path | None, dict]:
        items = self.avatar_reference_items(candidate_id)
        wanted = self.visual_form
        scored: list[tuple[int, Path, dict]] = []
        for item in items:
            status = str(item.get("status", "")).lower()
            if status.startswith("rejected") or status in {"wrong_version", "archived"}:
                continue
            raw = str(item.get("local_file", ""))
            if not raw:
                continue
            path = Path(raw)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            if not path.exists():
                continue
            form = str(item.get("form", "unknown")).lower()
            identity_text = f"{candidate_id} {item.get('title', '')} {item.get('source_title', '')}".lower()
            score = 0
            if wanted == "auto":
                score += 2
            elif form == wanted:
                score += 8
            elif form == "unknown":
                score += 1
            if item.get("full_body_reviewed"):
                score += 12
            if str(item.get("view", "")).lower() == "full_body":
                score += 6
            candidate_terms = [term for term in ("marinette", "ladybug", "kara", "supergirl") if term in candidate_id.lower()]
            if any(term in str(item.get("title", "")).lower() for term in candidate_terms):
                score += 5
            if any(token in identity_text for token in (
                "logo", "voice actor", "performer", "cast photo", "cristina vee",
            )):
                score -= 30
            if "kara" in candidate_id.lower() and any(
                token in identity_text for token in ("jimmy_and_kara", "eye_to_eye", "with_clark")
            ):
                score -= 20
            scored.append((score, path, item))
        if scored:
            _score, path, item = max(scored, key=lambda row: row[0])
            return path, item
        return self.first_available_image_path(candidate_id), {}

    def set_visual_form(self, form: str) -> None:
        self.visual_form = form
        candidate_id = self.selected_candidate_id()
        if candidate_id:
            self.update_large_visual(candidate_id)
            self.publish_avatar_state("standing naturally", source="form_control")

    def import_reviewed_appearance(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showwarning("Candidate needed", "Select a TemporaryAI candidate first.")
            return
        if self.visual_form not in {"civilian", "hero"}:
            messagebox.showwarning(
                "Choose a form",
                "Click Civilian or Hero first, then import the matching reviewed image.",
            )
            return
        selected = filedialog.askopenfilenames(
            title=f"Import reviewed {self.visual_form} reference",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if not selected:
            return
        manifest_path = self.candidate_avatar_manifest_path(candidate_id)
        manifest = read_json(manifest_path, {})
        manifest.setdefault("policy", {})["robert_review_required_before_avatar_generation"] = True
        references = manifest.setdefault("references", [])
        destination_dir = manifest_path.parent / "user_provided"
        destination_dir.mkdir(parents=True, exist_ok=True)
        imported = 0
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for index, raw_path in enumerate(selected, start=1):
            source = Path(raw_path)
            suffix = source.suffix.lower() if source.suffix else ".png"
            destination = destination_dir / f"{self.visual_form}_{stamp}_{index:02d}{suffix}"
            shutil.copy2(source, destination)
            full_body = messagebox.askyesno(
                "Full-body reference?",
                f"Does {source.name} show the complete body from head to feet?",
            )
            references.append({
                "title": source.name,
                "url": "",
                "kind": "user_reviewed_reference",
                "source_title": "Robert-provided exact-version reference",
                "provider": "Robert reviewed import",
                "review_required": False,
                "status": "reviewed_user_reference",
                "local_file": rel(destination),
                "error": "",
                "form": self.visual_form,
                "view": "full_body" if full_body else "unclassified",
                "full_body_reviewed": full_body,
            })
            imported += 1
        manifest["status"] = "reviewed_references_available"
        manifest["updated_at"] = now_iso()
        write_json(manifest_path, manifest)
        self.update_candidate_preview()
        self.update_large_visual(candidate_id)
        messagebox.showinfo(
            "Appearance imported",
            f"Imported {imported} reviewed {self.visual_form} reference(s).",
        )

    def import_generated_pose_sheet(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showwarning("Candidate needed", "Select a TemporaryAI candidate first.")
            return
        if self.visual_form not in {"civilian", "hero", "default"}:
            messagebox.showwarning(
                "Choose a form",
                "Click Civilian or Hero first, then import the matching generated pose sheet.",
            )
            return
        selected = filedialog.askopenfilename(
            title=f"Import generated {self.visual_form} 3 x 2 pose sheet",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if not selected:
            return
        try:
            import_pose_sheet(candidate_id, self.visual_form, Path(selected))
            self.update_large_visual(candidate_id)
            messagebox.showinfo(
                "Generated body imported",
                "Imported neutral, looking, waving, and talking poses. The live window will now animate only those real frames.",
            )
        except Exception as exc:
            messagebox.showerror("Pose-sheet import failed", str(exc))

    def candidate_voice_status_text(self, candidate_id: str) -> str:
        try:
            candidate = load_candidate_for_review_chat(candidate_id)
        except Exception as exc:
            return f"Voice unavailable: candidate policy could not be loaded ({exc})."
        decision = candidate_voice_output_decision(candidate)
        if not decision["allowed"]:
            return f"Voice unavailable (text only): {decision['reason']}"
        state = "on" if self.voice_enabled.get() else "off"
        route_label = (
            "candidate-specific voice pack"
            if decision.get("route_kind") == "custom_voice_pack"
            else "generic installed OS voice fallback"
        )
        return (
            f"Voice available but {state}: {route_label} "
            f"{decision.get('profile_label') or candidate_id}. Check Voice output to enable it."
        )

    def apply_voice_controls(self, candidate: dict[str, Any] | None, *, reset: bool = False) -> dict[str, Any]:
        if not candidate:
            self.voice_enabled.set(0)
            self.voice_toggle.config(state="disabled")
            decision = {
                "allowed": False,
                "reason": "Select and start a candidate first.",
                "profile_path": None,
            }
            self.voice_status.config(text=f"Voice unavailable (text only): {decision['reason']}")
            return decision
        decision = candidate_voice_output_decision(candidate)
        if reset or not decision["allowed"]:
            self.voice_enabled.set(0)
        self.voice_toggle.config(state="normal" if decision["allowed"] else "disabled")
        if decision["allowed"]:
            state = "on" if self.voice_enabled.get() else "off"
            route_label = (
                "candidate-specific voice pack"
                if decision.get("route_kind") == "custom_voice_pack"
                else "generic installed OS voice fallback"
            )
            text = (
                f"Voice available but {state}: {route_label} "
                f"{decision.get('profile_label') or candidate.get('candidate_id', '')}. "
                "Check Voice output to enable it."
            )
        else:
            text = f"Voice unavailable (text only): {decision['reason']}"
        self.voice_status.config(text=text)
        return decision

    def on_voice_toggle(self) -> None:
        if not self.voice_enabled.get():
            self.apply_voice_controls(self.candidate)
            return
        decision = self.apply_voice_controls(self.candidate)
        if decision["allowed"]:
            route_text = (
                "the ready candidate-specific pack; an installed OS voice is only its runtime fallback"
                if decision.get("route_kind") == "custom_voice_pack"
                else "a generic installed operating-system voice, not an authentic or cloned character voice"
            )
            self.voice_status.config(
                text=f"Voice on: using {route_text}."
            )
            return
        messagebox.showwarning("Voice remains off", decision["reason"])

    def queue_reply_voice(self, answer: str) -> bool:
        if not self.voice_enabled.get():
            return False
        error_reason = _runtime_error_reply_reason(answer)
        if error_reason:
            self.voice_status.config(text="Voice not queued: runtime source/model error text is never spoken.")
            return False
        decision = self.apply_voice_controls(self.candidate)
        if not decision["allowed"]:
            self.voice_enabled.set(0)
            return False
        threading.Thread(
            target=speak_candidate_reply,
            args=(answer, deepcopy(self.candidate), deepcopy(decision)),
            daemon=True,
        ).start()
        return True

    def update_large_visual(self, candidate_id: str) -> None:
        try:
            candidate = load_candidate_for_review_chat(candidate_id)
            profile = candidate.get("profile", {}) or {}
        except Exception:
            candidate = {}
            profile = {}
        resolved_form, self.visual_pose_paths = resolve_avatar_pose_paths(
            candidate_id,
            profile,
            self.visual_form,
        )
        self.visual_pose_images = {}
        for pose, path in self.visual_pose_paths.items():
            try:
                pose_image = Image.open(path).convert("RGBA")
                pose_image.thumbnail((250, 470))
                self.visual_pose_images[pose] = pose_image
            except Exception:
                continue
        image_path, item = self.best_visual_image(candidate_id)
        self.apply_voice_controls(candidate)
        if self.visual_pose_images:
            pose = "neutral" if "neutral" in self.visual_pose_images else next(iter(self.visual_pose_images))
            self.visual_source_image = self.visual_pose_images[pose].copy()
            self.visual_source_path = self.visual_pose_paths.get(pose)
            self.render_visual_frame()
            self.visual_caption.config(
                text=(
                    f"Showing: {resolved_form.title()} generated 2D pose preview"
                    + (
                        f" ({self.visual_form.title()} body not ready)\n"
                        if self.visual_form not in {"auto", resolved_form}
                        else "\n"
                    )
                    + f"Status: {len(self.visual_pose_images)} generated pose frame(s); identity review pending\n"
                    + f"Motion: {self.visual_motion} | Mood: {self.visual_emotion}\n"
                    + f"{rel(avatar_body_root(candidate_id))}"
                )
            )
            ensure_avatar_build_plan(candidate_id, profile, self.avatar_reference_items(candidate_id))
            return
        if not image_path:
            self.visual_photo = None
            self.visual_source_image = None
            self.draw_visual_message("No reviewed appearance yet.\n\nImport exact-version references, then generate and import a pose sheet.")
            self.visual_caption.config(text=f"Form: {self.visual_form.title()}\nGenerated body: not ready")
            return
        try:
            image = Image.open(image_path).convert("RGBA")
            image.thumbnail((250, 470))
            self.visual_source_image = image.copy()
            self.visual_source_path = image_path
            self.render_visual_frame()
            form = str(item.get("form", "unknown")).title()
            full_body = bool(item.get("full_body_reviewed")) or str(item.get("view", "")).lower() == "full_body"
            readiness = "reviewed full-body" if full_body else "reference image; full body still needs review"
            self.visual_caption.config(text=f"Showing: {form}\nStatus: {readiness}\nMotion: reference still; generated poses not ready\n{rel(image_path)}")
            try:
                ensure_avatar_build_plan(candidate_id, profile, self.avatar_reference_items(candidate_id))
            except Exception:
                pass
        except Exception as exc:
            self.visual_photo = None
            self.visual_source_image = None
            self.draw_visual_message(f"Appearance preview failed:\n{exc}")
            self.visual_caption.config(text="")

    def draw_visual_message(self, text: str) -> None:
        self.visual_box.delete("all")
        self.visual_box.create_text(135, 245, text=text, fill="#94a3b8", width=235, justify="center")

    def set_avatar_motion_from_reply(self, text: str) -> None:
        self.visual_emotion = infer_emotion(text)
        if begins_with_greeting(text):
            self.visual_motion = "greeting"
            self.visual_motion_until = time.time() + 3.2
            self.publish_avatar_state("greeting Robert", source="live_chat")
        else:
            self.visual_motion = "talking"
            self.visual_motion_until = time.time() + speaking_seconds(text)
            self.publish_avatar_state("talking with Robert", source="live_chat")

    def publish_avatar_state(self, activity: str, source: str = "live_chat") -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            return
        suggested_form = self.visual_form if self.visual_form in {"civilian", "hero", "sleepwear"} else ""
        try:
            write_avatar_activity_state(
                candidate_id,
                activity,
                suggested_form=suggested_form,
                source=source,
                mood=self.visual_emotion,
                metadata={"chat_window": True},
            )
        except Exception:
            pass

    def render_visual_frame(self) -> None:
        if self.visual_source_image is None:
            return
        self.visual_tick += 1
        now = time.time()
        if self.visual_motion != "idle" and now >= self.visual_motion_until:
            self.visual_motion = "idle"
            self.publish_avatar_state("standing naturally", source="live_chat_idle")
        pose = pose_for_motion(self.visual_motion, self.visual_tick, set(self.visual_pose_images))
        image = self.visual_pose_images.get(pose, self.visual_source_image)
        colors = {"joy": "#10261d", "excited": "#172554", "concern": "#282012", "sad": "#172033", "calm": "#0b1220"}
        stage = Image.new("RGBA", (270, 500), colors.get(self.visual_emotion, "#0b1220"))
        x = (stage.width - image.width) // 2
        y = max(5, stage.height - image.height - 10)
        stage.alpha_composite(image, (x, y))
        self.visual_photo = ImageTk.PhotoImage(stage)
        self.visual_box.delete("all")
        self.visual_box.create_image(135, 250, image=self.visual_photo)

    def animate_visual(self) -> None:
        if self.closing:
            return
        try:
            self.render_visual_frame()
        finally:
            if not self.closing:
                self.root.after(120, self.animate_visual)

    def open_avatar_references(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            return
        path = PROJECT_ROOT / "Avatar" / "temp_ai" / candidate_id / "references"
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def open_generated_body_folder(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            return
        try:
            candidate = load_candidate(candidate_id)
            ensure_avatar_body_manifest(candidate_id, candidate.get("profile", {}) or {})
            os.startfile(avatar_body_root(candidate_id))
        except Exception as exc:
            messagebox.showerror("Generated body folder failed", str(exc))

    def open_avatar_build_plan(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            return
        try:
            candidate = load_candidate(candidate_id)
            plan = ensure_avatar_build_plan(candidate_id, candidate.get("profile", {}) or {}, self.avatar_reference_items(candidate_id))
            os.startfile(str(plan))
        except Exception as exc:
            messagebox.showerror("Avatar plan failed", str(exc))

    def open_voice_review(self) -> None:
        launcher = PROJECT_ROOT / "Start_Voice_Reference_Control_Center.bat"
        if launcher.exists():
            os.startfile(launcher)
        else:
            messagebox.showinfo("Voice review", "The voice reference review launcher was not found.")

    def update_candidate_preview(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            self.preview_photo = None
            self.visual_photo = None
            self.visual_source_image = None
            self.preview_box.config(image="", text="No preview image")
            self.preview_caption.config(text="")
            self.draw_visual_message("Select a candidate")
            self.visual_caption.config(text="")
            self.apply_voice_controls(None)
            return
        image_path = self.first_preview_image_path(candidate_id)
        if not image_path:
            self.preview_photo = None
            self.preview_box.config(image="", text="No preview image yet.\nClick Refresh Sources.")
            self.preview_caption.config(text="")
            self.update_large_visual(candidate_id)
            self.schedule_embedded_avatar(candidate_id)
            return
        try:
            image = Image.open(image_path)
            image.thumbnail((120, 85))
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_box.config(image=self.preview_photo, text="")
            self.preview_caption.config(text=rel(image_path))
            self.update_large_visual(candidate_id)
            self.schedule_embedded_avatar(candidate_id)
        except Exception as exc:
            self.preview_photo = None
            self.preview_box.config(image="", text=f"Preview failed:\n{exc}")
            self.preview_caption.config(text="")
            self.update_large_visual(candidate_id)
            self.schedule_embedded_avatar(candidate_id)

    def selected_candidate_id(self) -> str | None:
        selection = self.candidate_list.curselection()
        if not selection:
            return None
        return self.candidate_paths[selection[0]].name

    def open_3d_avatar(self, force_restart: bool = True) -> None:
        self.embedded_start_after_id = None
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        try:
            candidate = load_candidate(candidate_id)
            display = str(candidate.get("profile", {}).get("display_name") or candidate_id)
            if not discover_rigged_model(candidate_id):
                self.embedded_avatar.stop()
                self.show_2d_avatar_fallback()
                self.visual_caption.config(
                    text="Living 2D appearance\nA generated pose sheet is not a rigged 3D body"
                )
                self.status.config(text=f"{display} is using the reviewed 2D appearance for now.")
                return
            if (
                not force_restart
                and self.embedded_avatar.candidate_id == candidate_id
                and self.embedded_avatar.ensure_attached()
            ):
                self.embedded_candidate_id = candidate_id
                self.visual_box.pack_forget()
                self.visual_caption.config(text="Embedded local WebGL appearance\nStatus: 3D model v1 loaded")
                return
            self.show_2d_avatar_fallback()
            self.embedded_candidate_id = candidate_id
            self.publish_avatar_state("standing naturally", source="embedded_avatar_start")
            self.visual_caption.config(text=f"Starting embedded 3D appearance for {display}...")
            self.status.config(text=f"Starting {display}'s embedded 3D appearance.")
            self.embedded_avatar.start(candidate_id, display)
        except Exception as exc:
            self.show_2d_avatar_fallback()
            self.status.config(text=f"Embedded 3D unavailable; using the 2D appearance: {exc}")

    def schedule_embedded_avatar(self, candidate_id: str, force_restart: bool = False) -> None:
        if self.closing:
            return
        if not discover_rigged_model(candidate_id):
            self.embedded_avatar.stop()
            self.embedded_candidate_id = None
            self.show_2d_avatar_fallback()
            return
        if force_restart:
            if self.embedded_start_after_id is not None:
                try:
                    self.root.after_cancel(self.embedded_start_after_id)
                except Exception:
                    pass
                self.embedded_start_after_id = None
            self.show_2d_avatar_fallback()
            self.embedded_avatar.stop()
            self.embedded_candidate_id = None
            self.visual_caption.config(text="Refreshing embedded 3D appearance...")
            self.embedded_start_after_id = self.root.after(500, lambda: self.open_3d_avatar(False))
            return
        if (
            self.embedded_avatar.candidate_id == candidate_id
            and self.embedded_avatar.ensure_attached()
        ):
            if self.embedded_start_after_id is not None:
                try:
                    self.root.after_cancel(self.embedded_start_after_id)
                except Exception:
                    pass
                self.embedded_start_after_id = None
            self.embedded_candidate_id = candidate_id
            self.visual_box.pack_forget()
            self.publish_avatar_state("standing naturally", source="candidate_selection")
            self.root.update_idletasks()
            self.embedded_avatar.resize()
            self.root.after(80, self.embedded_avatar.resize)
            self.root.after(300, self.embedded_avatar.resize)
            return
        if self.embedded_start_after_id is not None:
            try:
                self.root.after_cancel(self.embedded_start_after_id)
            except Exception:
                pass
        self.show_2d_avatar_fallback()
        self.embedded_start_after_id = self.root.after(350, lambda: self.open_3d_avatar(False))

    def show_2d_avatar_fallback(self) -> None:
        if not self.visual_box.winfo_manager():
            self.visual_box.pack(fill=BOTH, expand=True)
        self.render_visual_frame()

    def poll_embedded_avatar(self) -> None:
        if self.closing:
            return
        for kind, candidate_id, note in self.embedded_avatar.poll():
            if candidate_id != self.selected_candidate_id():
                continue
            if kind == "ready":
                if self.embedded_avatar.ensure_attached():
                    self.visual_box.pack_forget()
                    self.visual_caption.config(text="Embedded local WebGL appearance\nStatus: 3D model v1 loaded")
                    self.status.config(text=f"{note} Chat and appearance controls remain active.")
                else:
                    self.show_2d_avatar_fallback()
                    self.status.config(text="The 3D window did not attach; restarting it once.")
                    self.schedule_embedded_avatar(candidate_id, force_restart=True)
            else:
                self.show_2d_avatar_fallback()
                self.visual_caption.config(text=f"2D appearance fallback\nEmbedded 3D unavailable: {note}")
                self.status.config(text="Embedded 3D was unavailable; the reviewed 2D appearance is still active.")
        if (
            self.embedded_avatar.candidate_id == self.selected_candidate_id()
            and self.embedded_avatar.is_live()
        ):
            if not self.embedded_avatar.ensure_attached():
                candidate_id = self.selected_candidate_id()
                if candidate_id:
                    self.schedule_embedded_avatar(candidate_id, force_restart=True)
        self.root.after(200, self.poll_embedded_avatar)

    def start_selected_chat(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        try:
            self.candidate = load_candidate_for_review_chat(candidate_id)
        except Exception as exc:
            messagebox.showerror("Candidate load failed", str(exc))
            return
        profile = self.candidate["profile"]
        self.display = profile.get("display_name", candidate_id)
        self.role = profile.get("role_title", "")
        run_id = f"temporary_ai_live_chat_{slug(candidate_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.json_path = OUT_DIR / f"{run_id}.json"
        self.monitor_path = OUT_DIR / f"{run_id}.monitor.md"
        self.history = []
        self.records = []
        self.last_answer = ""
        self.apply_voice_controls(self.candidate, reset=True)
        self.chat.delete("1.0", END)
        bounded = self.candidate.get("review_mode") == "profile_bounded_draft"
        self.status.config(
            text=(
                f"Profile-bounded draft review with {self.display}"
                if bounded
                else f"Talking with {self.display}" + (f" ({self.role})" if self.role else "")
            )
        )
        self.write_transcript()
        if bounded:
            self.log_chat(
                "System",
                (
                    f"You are reviewing the checked-in draft profile for {self.display}. "
                    "Every reply is labelled profile-bounded. This is not verified canon, "
                    "activation, memory proof, an authentic voice, a body, or world presence."
                ),
            )
            self.show_2d_avatar_fallback()
        else:
            self.log_chat("System", f"You are now talking with {self.display}. Ask the question directly; you do not need to type her name.")
            self.schedule_embedded_avatar(candidate_id)
            self.publish_avatar_state("standing naturally", source="chat_started")

    def start_life_loop(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        if self.loop_process and self.loop_process.poll() is None:
            messagebox.showinfo("Life loop already running", "End the current TemporaryAI life loop safely before starting another.")
            return
        try:
            review_candidate = load_candidate_for_review_chat(candidate_id)
        except Exception as exc:
            messagebox.showerror("Candidate load failed", str(exc))
            return
        if review_candidate.get("review_mode") == "profile_bounded_draft":
            messagebox.showinfo(
                "Life loop unavailable",
                "This candidate is available only for labelled profile-bounded draft review. "
                "That route cannot start a life loop, body, or world presence.",
            )
            return
        ok, wake_note = ensure_ollama_running(timeout=20.0)
        if not ok:
            self.status.config(text="Ollama/model server is offline.")
            messagebox.showerror(
                "Local model offline",
                wake_note + "\n\nStart Ollama, then try Start Life Loop again.",
            )
            return
        self.status.config(text=wake_note)
        try:
            candidate = load_candidate(candidate_id)
        except Exception as exc:
            messagebox.showerror("Candidate load failed", str(exc))
            return
        profile = candidate.get("profile", {})
        display = profile.get("display_name", candidate_id)
        self.loop_run_id = f"temporary_ai_life_loop_{slug(candidate_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        TEMP_AI_LOOP_ROOT.mkdir(parents=True, exist_ok=True)
        self.loop_json_path = TEMP_AI_LOOP_ROOT / f"{self.loop_run_id}.json"
        self.loop_monitor_path = TEMP_AI_LOOP_ROOT / f"{self.loop_run_id}.monitor.md"
        self.loop_stop_path = TEMP_AI_LOOP_ROOT / f"{self.loop_run_id}.stop"
        self.loop_live_notes_path = TEMP_AI_LOOP_ROOT / f"{self.loop_run_id}.robert_live_notes.md"
        self.loop_worker_log_path = TEMP_AI_LOOP_ROOT / f"{self.loop_run_id}.worker.log"
        if self.loop_stop_path.exists():
            self.loop_stop_path.unlink()
        if self.loop_live_notes_path.exists():
            self.loop_live_notes_path.unlink()

        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "temporary_ai_project_loop.py"),
            "--candidate-id",
            candidate_id,
            "--cycles",
            "999999",
            "--pause-minutes",
            "2",
            "--run-id",
            self.loop_run_id,
            "--stop-file",
            str(self.loop_stop_path),
            "--online-research",
            "--research-interval",
            "3",
        ]
        worker_log = self.loop_worker_log_path.open("a", encoding="utf-8") if self.loop_worker_log_path else subprocess.DEVNULL
        self.loop_process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=worker_log,
            stderr=worker_log,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        self.status.config(text=f"Life loop running for {display}. You can keep chatting here.")
        self.log_chat("System", f"Started life loop for {display}. It will work in saved cycles until you click End Life Loop Safely.")
        # Keep the existing WebGL child alive while the worker starts. Restarting
        # Edge here used to make the appearance blink out, and a delayed/stale
        # ready event could leave the panel permanently blank.
        self.schedule_embedded_avatar(candidate_id)
        self.publish_avatar_state("standing naturally", source="life_loop_started")

    def append_loop_live_note(self, speaker: str, text: str) -> None:
        if not self.loop_process or self.loop_process.poll() is not None or not self.loop_live_notes_path:
            return
        self.loop_live_notes_path.parent.mkdir(parents=True, exist_ok=True)
        with self.loop_live_notes_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## {speaker} at {now_iso()}\n{text.strip()}\n")

    def end_life_loop_safely(self) -> None:
        if not self.loop_process or self.loop_process.poll() is not None:
            messagebox.showinfo("No active loop", "No TemporaryAI life loop is currently running from this window.")
            return
        if not self.loop_stop_path:
            messagebox.showerror("Stop path missing", "This loop has no stop file path.")
            return
        self.loop_stop_path.parent.mkdir(parents=True, exist_ok=True)
        self.loop_stop_path.write_text(
            f"Safe stop requested from TemporaryAI Live Chat at {now_iso()}.\n",
            encoding="utf-8",
        )
        self.status.config(text="Safe stop requested. The life loop will stop before the next cycle.")
        self.log_chat("System", "Safe stop requested for the TemporaryAI life loop. It will finish the current cycle or wait period and then stop.")

    def open_life_loop_log(self) -> None:
        if self.loop_monitor_path and self.loop_monitor_path.exists():
            os.startfile(str(self.loop_monitor_path))
            return
        if self.loop_json_path and self.loop_json_path.exists():
            os.startfile(str(self.loop_json_path.parent))
            return
        os.startfile(str(TEMP_AI_LOOP_ROOT))

    def poll_life_loop(self) -> None:
        if self.loop_json_path and self.loop_json_path.exists():
            data = read_json(self.loop_json_path, {})
            cycles_done = len(data.get("cycles", []) or [])
            status = data.get("status", "")
            if self.loop_process and self.loop_process.poll() is None:
                self.status.config(text=f"Life loop running: {cycles_done} cycle(s) saved. Status: {status or 'running'}.")
            elif self.loop_process and self.loop_process.poll() is not None and status == "running":
                exit_code = self.loop_process.poll()
                data["status"] = "failed_worker_exited"
                data["updated_at"] = now_iso()
                data["failure_note"] = f"Worker process exited with code {exit_code}. See worker log."
                write_json(self.loop_json_path, data)
                if self.loop_monitor_path:
                    with self.loop_monitor_path.open("a", encoding="utf-8") as handle:
                        handle.write(
                            f"\n## Worker Exited\n- exit_code: {exit_code}\n"
                            f"- worker_log: {rel(self.loop_worker_log_path) if self.loop_worker_log_path else ''}\n"
                        )
                self.status.config(text=f"Life loop worker exited before completing normally. Saved {cycles_done} cycle(s).")
            elif status:
                self.status.config(text=f"Life loop {status}: {cycles_done} cycle(s) saved.")
        self.root.after(5000, self.poll_life_loop)

    def on_enter(self, event):
        if event.state & 0x0001:
            return None
        self.send_message()
        return "break"

    def send_message(self) -> None:
        if not self.candidate:
            self.start_selected_chat()
            if not self.candidate:
                return
        message = self.input.get("1.0", END).strip()
        if not message:
            return
        self.input.delete("1.0", END)
        self.log_chat("Robert", message)
        self.append_loop_live_note("Robert", message)
        self.status.config(text=f"{self.display} is thinking...")
        threading.Thread(target=self.ask_worker, args=(message,), daemon=True).start()

    def ask_worker(self, message: str) -> None:
        candidate_context = self.candidate
        try:
            candidate_id = str((self.candidate or {}).get("candidate_id", ""))
            if candidate_id:
                candidate_context = load_candidate_for_review_chat(candidate_id)
            ok, wake_note = ensure_ollama_running(timeout=20.0)
            if not ok:
                answer = f"[TemporaryAI - model offline] {wake_note}"
                generated_files = []
            elif candidate_context.get("review_mode") == "profile_bounded_draft":
                answer = ask_profile_bounded_model(candidate_context, self.history, message)
                generated_files = []
            else:
                answer = ask_model(candidate_context, self.history, message)
                answer, generated_files = finalize_model_artifacts(
                    candidate_context,
                    self.history,
                    message,
                    answer,
                )
        except Exception as exc:
            answer = f"[TemporaryAI - error] {exc}"
            generated_files = []
        candidate_id = str((candidate_context or {}).get("candidate_id", "unknown_candidate"))
        turn_id = f"{self.json_path.stem if self.json_path else 'temporary_ai_gui'}_turn_{len(self.records) + 1:04d}"
        mind_turn = finalize_person_turn(
            person_id=candidate_id,
            person_label=self.display,
            raw_reply=answer,
            source_turn_id=turn_id,
            body_active=False,
            activity_controller_active=False,
        )
        self.worker_queue.put(
            (
                message,
                mind_turn["channels"]["spoken"],
                [rel(path) for path in generated_files],
                candidate_context,
                mind_turn,
            )
        )

    def drain_worker_queue(self) -> None:
        try:
            while True:
                message, answer, generated_files, candidate_context, mind_turn = self.worker_queue.get_nowait()
                self.candidate = candidate_context
                self.last_answer = answer
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": answer})
                record = {
                    "turn": len(self.records) + 1,
                    "robert": message,
                    "candidate": answer,
                    "generated_files": generated_files,
                    "mind_evidence": rel(Path(mind_turn["evidence_path"])),
                    "action_requests": mind_turn["channels"]["runtime_truth"]["action_requests"],
                    "action_results": mind_turn["channels"]["runtime_truth"]["action_results"],
                    "created_at": now_iso(),
                }
                self.records.append(record)
                self.log_chat(self.display, answer)
                # A public sentence is never reinterpreted as a motor command.
                # This review GUI has no confirmed body controller, so actions
                # remain separately recorded and honestly blocked.
                self.queue_reply_voice(answer)
                self.status.config(text=f"Talking with {self.display}" + (f" ({self.role})" if self.role else ""))
                self.write_transcript()
        except queue.Empty:
            pass
        self.root.after(200, self.drain_worker_queue)

    def write_transcript(self) -> None:
        if not self.candidate or not self.json_path or not self.monitor_path:
            return
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.json_path, {
            "candidate": self.candidate,
            "records": self.records,
            "updated_at": now_iso(),
        })
        lines = [
            f"# {self.json_path.stem}",
            f"- candidate_id: {self.candidate['candidate_id']}",
            f"- display_name: {self.display}",
            f"- role: {self.role}",
            "",
        ]
        for record in self.records:
            lines.extend([
                f"## Turn {record['turn']}",
                f"- **Robert**: {record['robert']}",
                f"- **{self.display}**: {record['candidate']}",
            ])
            generated_files = record.get("generated_files") or []
            if generated_files:
                lines.append("- **Saved generated files**:")
                lines.extend(f"  - {path}" for path in generated_files)
            lines.append("")
        self.monitor_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def save_last_reply(self) -> None:
        if not self.candidate:
            messagebox.showinfo("No chat", "Start a chat first.")
            return
        if not self.last_answer:
            messagebox.showinfo("Nothing to save", "There is no TemporaryAI reply to save yet.")
            return
        workspaces = self.candidate.get("attached_workspaces", [])
        if not workspaces:
            messagebox.showinfo("No workspace", "This candidate has no attached workspace outputs folder.")
            return
        outputs = Path(workspaces[0].get("outputs_folder", ""))
        if not outputs.is_absolute():
            outputs = PROJECT_ROOT / outputs
        outputs.mkdir(parents=True, exist_ok=True)
        saved = save_reply_artifacts(
            outputs,
            safe_output_name(f"{self.display}_reply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"),
            self.last_answer,
            title=f"{self.display} draft",
        )
        messagebox.showinfo("Saved", "Saved to:\n" + "\n".join(rel(path) for path in saved))

    def open_selected_folder(self) -> None:
        selection = self.candidate_list.curselection()
        if not selection:
            return
        path = self.candidate_paths[selection[0]]
        if path.exists():
            os.startfile(str(path))

    def open_workbench_projects(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        try:
            candidate = load_candidate(candidate_id)
            outputs = candidate_workbench_dir(candidate) / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)
            os.startfile(str(outputs))
        except Exception as exc:
            messagebox.showerror("Workbench unavailable", str(exc))

    def archive_selected_candidate(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        path = self.candidate_paths[self.candidate_list.curselection()[0]]
        profile = read_json(path / "temporary_ai_profile.json", {})
        display = profile.get("display_name", candidate_id)
        if not messagebox.askyesno(
            "Archive candidate",
            f"Archive {display}?\n\nThis removes it from the active TemporaryAI list but keeps the files in an archive folder.",
        ):
            return
        try:
            record = archive_candidate(candidate_id)
        except Exception as exc:
            messagebox.showerror("Archive failed", str(exc))
            return
        if self.candidate and self.candidate.get("candidate_id") == candidate_id:
            self.candidate = None
            self.history = []
            self.records = []
            self.last_answer = ""
            self.chat.delete("1.0", END)
        self.reload_candidates()
        self.status.config(text=f"Archived {display}: {record.get('candidate_archive', '')}")

    def refresh_selected_sources(self) -> None:
        candidate_id = self.selected_candidate_id()
        if not candidate_id:
            messagebox.showinfo("Pick a candidate", "Click a candidate name first.")
            return
        try:
            result = refresh_candidate_sources(candidate_id)
        except Exception as exc:
            messagebox.showerror("Source refresh failed", str(exc))
            return
        self.reload_candidates()
        self.update_candidate_preview()
        self.status.config(
            text=(
                f"Refreshed {candidate_id}: "
                f"{result.get('fetched_count', 0)}/{result.get('source_count', 0)} sources, "
                f"web={result.get('expanded_web_results', 0)}, "
                f"avatar_refs={result.get('avatar_reference_count', 0)}, "
                f"lookup={result.get('lookup_status', '')}"
            )
        )
        messagebox.showinfo(
            "Sources refreshed",
            "\n".join([
                f"Candidate: {candidate_id}",
                f"Fetched: {result.get('fetched_count', 0)}/{result.get('source_count', 0)}",
                f"Web results: {result.get('expanded_web_results', 0)}",
                f"Avatar references: {result.get('avatar_reference_count', 0)}",
                f"Lookup: {result.get('lookup_status', '')} {result.get('matched_title', '')}".strip(),
                f"Pack: {result.get('pack_path', '')}",
            ]),
        )

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        if self.embedded_start_after_id is not None:
            try:
                self.root.after_cancel(self.embedded_start_after_id)
            except Exception:
                pass
        try:
            self.embedded_avatar.stop()
        except Exception:
            pass
        if self.avatar_process and self.avatar_process.poll() is None:
            try:
                self.avatar_process.terminate()
            except Exception:
                pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    TemporaryAILiveChatGUI().run()
