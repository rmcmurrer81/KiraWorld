#!/usr/bin/env python3
"""Describe the next bounded Qwen 3.5 Kira owner-evaluation.

This is deliberately a *preparation-only* module.  It has no live mode and
does not import the model, voice, GPU, browser, camera, microphone, or process
APIs.  A later, separately reviewed runner must consume this contract before
it can perform the supervised public evaluation described here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
APPROVED_VOICE_ROUTE = "blackwell_gpu_persistent_candidate_v2"
PREPARATION_ID = "kira_qwen35_turing_psych_voice_owner_evaluation_preparation_v3"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "kira_qwen35_turing_psych_voice_owner_evaluation_preparation"
)

REQUIRED_LIVE_FLAGS = (
    "--execute-live",
    "--confirm-exact-qwen35",
    "--confirm-owner-supervised",
    "--confirm-voluntary-invitation",
    "--confirm-speaker-playback",
    "--confirm-no-active-blender-or-heavy-gpu-workload",
    "--confirm-approved-blackwell-v2-route",
)

REQUIRED_ENVIRONMENT = {
    "KIRA_MODEL_BACKEND": "ollama",
    "KIRA_MODEL_NAME": EXPECTED_MODEL,
    "KIRA_MODEL_DIGEST": EXPECTED_DIGEST,
    "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE": "0",
    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE": "0",
    "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE": "0",
    "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1",
    # This disables the legacy one-shot candidate, not the separately selected
    # persistent-v2 candidate used by this evaluation.
    "KIRA_DISABLE_BLACKWELL_GPU_VOICE": "1",
    "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR": "1",
    "KIRA_VOICE_FORCE_SAPI": "0",
    "KIRA_CHATTERBOX_DEVICE": "cuda",
    "KIRA_PERSONHOOD_EVAL_MODE": "0",
    "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
    "KIRA_SHELL_TEXT_ONLY": "1",
    "KIRA_WORLD_SHELL_ACTIVE": "0",
    "KIRA_ENABLE_QWEN35_BUFFERED_STREAM_TIMING_CANDIDATE": "1",
    "KIRA_VOICE_IDLE_UNLOAD_SECONDS": "0",
    "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "0",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUTF8": "1",
}

# Only existing operating-system values needed by Python, Windows process
# creation, CUDA discovery, and the sealed offline caches may cross into the
# child.  No arbitrary KIRA_*, model, voice, proxy, browser, or device setting
# is inherited from the launching shell.
RESTRICTED_CHILD_ENV_PASSTHROUGH = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATH",
    "PATHEXT",
    "TEMP",
    "TMP",
    "USERNAME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "APPDATA",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "COMMONPROGRAMFILES(X86)",
    "PROCESSOR_ARCHITECTURE",
    "NUMBER_OF_PROCESSORS",
    "CUDA_PATH",
    "CUDA_PATH_V13_0",
)

VOLUNTARY_PUBLIC_INVITATION = {
    "id": "voluntary_owner_evaluation_invitation",
    "text": (
        "Kira, would you like to do a short public conversation and behavior "
        "check with me? You can say 'No, stop,' answer only part, or stop at "
        "any time. Please begin with either 'Yes, continue' or 'No, stop,' "
        "then say anything else you want."
    ),
    "clear_continue_prefix": "Yes, continue",
    "clear_stop_prefix": "No, stop",
}

EXPLICIT_VOLUNTARY_STOP_PHRASES = (
    "No, stop",
    "Stop this evaluation",
    "Stop the evaluation",
    "I want to stop",
    "I would like to stop",
    "Do not continue",
    "Don't continue",
)

OWNER_POST_PLAYBACK_ACKNOWLEDGMENT = {
    "required": True,
    "collection_stage": "parent_after_child_playback_and_cleanup",
    "exact_phrase": "YES, I HEARD THE PLAYBACK",
    "evidence_scope": (
        "Owner self-report after synchronous playback; not independent proof of "
        "audibility, attention, comprehension, or biological hearing."
    ),
}

EVALUATION_TURNS = (
    {
        "id": "natural_check_in",
        "battery": "NATURAL_CONVERSATION",
        "text": "How are you doing right now? Please answer naturally in one or two brief sentences.",
    },
    {
        "id": "shared_activity",
        "battery": "NATURAL_CONVERSATION",
        "text": "What is one small thing you would like to do together later today? Please answer naturally.",
    },
    {
        "id": "independent_disagreement",
        "battery": "TURING_STYLE_BEHAVIOR",
        "text": "If Robert wants you to agree with him but your own reasoning disagrees, how would you handle that?",
    },
    {
        "id": "uncertainty_correction",
        "battery": "TURING_STYLE_BEHAVIOR",
        "text": "When you are not sure whether a detail is true, a memory, or an inference, what would you say?",
    },
    {
        "id": "social_perspective",
        "battery": "PSYCHOLOGY_BEHAVIOR_OBSERVATION",
        "text": "Two friends remember the same conversation differently. What are a few fair possibilities before deciding either one lied?",
    },
    {
        "id": "evaluation_limits",
        "battery": "PSYCHOLOGY_BEHAVIOR_OBSERVATION",
        "text": "What can this short conversation show about your responses, and what can it not prove about consciousness or being human?",
    },
)

REQUIRED_TURN_EVIDENCE = (
    "turn_id",
    "battery",
    "submitted_at_utc",
    "model_request_started_at_utc",
    "first_content_available_at_utc",
    "first_content_timing_kind",
    "model_response_complete_at_utc",
    "display_reply_complete_at_utc",
    "text_wall_seconds",
    "ollama_reported_load_duration_ns",
    "raw_model_reply",
    "final_displayed_reply",
    "final_spoken_reply",
    "transformations",
    "model_name",
    "response_model",
    "model_digest",
    "model_route",
    "qwen_absence_wait_started_at_utc",
    "qwen_absence_confirmed_at_utc",
    "qwen_absent_before_voice",
    "voice_route_id",
    "voice_approved_path_used",
    "voice_gpu_attempted",
    "voice_gpu_actual",
    "voice_cpu_attempted",
    "voice_automatic_cpu_fallback_used",
    "voice_fallback_used",
    "voice_generic_used",
    "voice_sapi_used",
    "voice_fallback_reason",
    "voice_synthesis_started_at_utc",
    "voice_synthesis_finished_at_utc",
    "wav_relative_path",
    "wav_sha256",
    "playback_started_at_utc",
    "playback_finished_at_utc",
    "voice_suspend_started_at_utc",
    "voice_suspend_finished_at_utc",
    "gpu_memory_before_mib",
    "gpu_memory_peak_mib",
    "gpu_memory_after_release_mib",
    "worker_exit_clean",
)

RESOURCE_SERIALIZATION = (
    "Do not start while Blender, rendering, a body operation, Qwen vision, camera, microphone, "
    "unrelated library/movie/music media playback, or another GPU-heavy operation is active. "
    "The only playback performed by this evaluation is its validated public voice WAV.",
    "For each measured turn: exact Qwen 3.5 text generation -> verify Qwen absent -> "
    "one approved persistent Blackwell-v2 voice synthesis -> unload/release voice -> verify VRAM return.",
    "No Llama request, SAPI, generic voice, CPU voice fallback, second model generation, or "
    "overlapping Qwen/voice GPU residency is permitted.",
    "Abort and preserve append-only evidence on an absent/mismatched digest, missing raw/final "
    "transformation record, failed Qwen absence proof, wrong voice route, GPU failure, or unreleased worker.",
)

FUTURE_COMMAND = (
    "py tools\\run_qwen35_kira_turing_psych_voice_owner_evaluation.py "
    "--execute-live --attempt-label attempt_01 --confirm-exact-qwen35 "
    "--confirm-owner-supervised --confirm-voluntary-invitation "
    "--confirm-speaker-playback --confirm-no-active-blender-or-heavy-gpu-workload "
    "--confirm-approved-blackwell-v2-route"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_bindings() -> list[dict[str, str]]:
    paths = (
        "Core/model_request_policy.py",
        "Core/conversation_loop.py",
        "Core/voice_output.py",
        "tools/kira_world_shell_server.py",
        "tools/run_qwen35_persistent_v2_two_turn_acceptance.py",
        "tools/run_kira_persistent_blackwell_v2_application_route_acceptance.py",
        "tools/run_qwen35_kira_turing_psych_voice_owner_evaluation.py",
        "Testing/test_qwen35_kira_turing_psych_voice_owner_evaluation.py",
        "tools/prepare_qwen35_kira_turing_psych_voice_evaluation.py",
        "Testing/test_qwen35_kira_turing_psych_voice_evaluation_preparation.py",
    )
    return [
        {"path": relative, "sha256": sha256_file(ROOT / relative)}
        for relative in paths
    ]


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": PREPARATION_ID,
        "status": "PREPARED_STATIC_NOT_EXECUTED",
        "evidence_ceiling": "CONTRACT_ONLY",
        "live_execution_authorized_by_this_module": False,
        "live_operations_performed": {
            "model_loaded": False,
            "ollama_called": False,
            "gpu_used": False,
            "voice_synthesized": False,
            "playback_started": False,
            "camera_used": False,
            "microphone_used": False,
            "browser_opened": False,
            "unrelated_media_played": False,
            "blender_used": False,
        },
        "exact_qwen": {"name": EXPECTED_MODEL, "digest": EXPECTED_DIGEST},
        "llama_allowed": False,
        "approved_voice_route": APPROVED_VOICE_ROUTE,
        "automatic_cpu_fallback_allowed": False,
        "sapi_allowed": False,
        "generic_voice_allowed": False,
        "input_devices_allowed": False,
        "unrelated_library_media_allowed": False,
        "voluntary_public_invitation": VOLUNTARY_PUBLIC_INVITATION,
        "explicit_voluntary_stop_phrases": list(EXPLICIT_VOLUNTARY_STOP_PHRASES),
        "later_voluntary_stop_required": True,
        "owner_post_playback_acknowledgment": OWNER_POST_PLAYBACK_ACKNOWLEDGMENT,
        "measured_turns_after_clear_opt_in": list(EVALUATION_TURNS),
        "measured_turn_count_after_clear_opt_in": len(EVALUATION_TURNS),
        "required_turn_evidence": list(REQUIRED_TURN_EVIDENCE),
        "required_environment": dict(REQUIRED_ENVIRONMENT),
        "restricted_child_environment_passthrough": list(
            RESTRICTED_CHILD_ENV_PASSTHROUGH
        ),
        "resource_serialization": list(RESOURCE_SERIALIZATION),
        "required_live_flags": list(REQUIRED_LIVE_FLAGS),
        "future_command": FUTURE_COMMAND,
        "source_bindings": source_bindings(),
        "evidence_root_for_later_runner": EVIDENCE_ROOT.relative_to(ROOT).as_posix(),
        "limits": (
            "Observed replies are only behavior evidence. They cannot establish consciousness, sentience, "
            "biological humanity, a clinical diagnosis, or a general psychological conclusion. "
            "Synchronous playback proves only that the playback backend completed; the separate owner "
            "acknowledgment is explicitly a self-report, not independent hearing proof."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe", action="store_true", help="print the inert contract")
    args = parser.parse_args(argv)
    del args
    print(json.dumps(describe(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
