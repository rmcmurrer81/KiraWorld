"""
Validate the hardware capability profile.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "profile_id",
    "status",
    "purpose",
    "known_build",
    "planned_upgrade_path",
    "capability_stages",
    "current_planned_stage",
    "activation_policy",
    "success_definition",
}
VALID_STATUS = {"draft", "active", "archived"}
REQUIRED_STAGES = {
    "stage_16gb_setup",
    "stage_64gb_local_life",
    "stage_gpu_expansion",
}
REQUIRED_16GB_BLOCKS = {
    "voice_conversation_as_default",
    "always_on_microphone",
    "webcam_or_vision",
    "avatar_rendering",
    "3d_home_or_notebook_world_runtime",
    "video_understanding",
    "full_temporary_ai_activation",
    "adult_private_temporary_ai_activation",
}
REQUIRED_64GB_ALLOWED = {
    "kira_text_life_sessions",
    "lisa_text_life_sessions",
    "slow_reading_sessions",
    "temporary_ai_limited_text_activation_tests",
}
REQUIRED_GPU_ALLOWED = {
    "voice_input_output_pipeline",
    "vision_and_webcam_tests",
    "avatar_generation_and_render_tests",
    "3d_home_runtime_tests",
    "video_and_media_understanding_tests",
}


def _require_string(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> None:
    if not str(data.get(key, "")).strip():
        errors.append(f"{prefix}.{key} is required.")


def _require_list(errors: list[str], data: dict[str, Any], key: str, prefix: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list.")
        return []
    return value


def _stage_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stages = data.get("capability_stages", [])
    if not isinstance(stages, list):
        return {}
    return {
        str(stage.get("stage_id")): stage
        for stage in stages
        if isinstance(stage, dict) and str(stage.get("stage_id", "")).strip()
    }


def validate_hardware_capability_profile(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append("Missing required fields: " + ", ".join(missing))

    _require_string(errors, data, "profile_id", "root")
    _require_string(errors, data, "purpose", "root")
    if data.get("status") not in VALID_STATUS:
        errors.append("status must be one of: " + ", ".join(sorted(VALID_STATUS)) + ".")

    known_build = data.get("known_build")
    if not isinstance(known_build, dict):
        errors.append("known_build must be an object.")
        known_build = {}
    for key in ("cpu", "motherboard", "storage", "cooler", "power_supply", "case"):
        _require_string(errors, known_build, key, "known_build")
    initial_ram = known_build.get("initial_ram")
    if not isinstance(initial_ram, dict):
        errors.append("known_build.initial_ram must be an object.")
        initial_ram = {}
    if initial_ram.get("capacity_gb") != 16:
        errors.append("known_build.initial_ram.capacity_gb must be 16 for the initial stage.")
    target_ram = known_build.get("target_ram")
    if not isinstance(target_ram, dict):
        errors.append("known_build.target_ram must be an object.")
        target_ram = {}
    if int(target_ram.get("preferred_capacity_gb", 0) or 0) < 64:
        errors.append("known_build.target_ram.preferred_capacity_gb must be at least 64.")

    _require_list(errors, data, "planned_upgrade_path", "root")
    stages = _stage_map(data)
    missing_stages = sorted(REQUIRED_STAGES - set(stages))
    if missing_stages:
        errors.append("capability_stages missing: " + ", ".join(missing_stages))
    if data.get("current_planned_stage") not in stages:
        errors.append("current_planned_stage must match a capability_stages stage_id.")

    for stage_id, stage in stages.items():
        _require_string(errors, stage, "label", f"capability_stages.{stage_id}")
        allowed = set(str(item) for item in _require_list(errors, stage, "allowed_work", f"capability_stages.{stage_id}"))
        blocked = set(str(item) for item in _require_list(errors, stage, "blocked_work", f"capability_stages.{stage_id}"))
        if not isinstance(stage.get("model_guidance"), dict):
            errors.append(f"capability_stages.{stage_id}.model_guidance must be an object.")
        minimum_ram = int(stage.get("minimum_ram_gb", -1) or -1)
        if minimum_ram < 0:
            errors.append(f"capability_stages.{stage_id}.minimum_ram_gb must be a non-negative integer.")
        if stage_id == "stage_16gb_setup":
            if minimum_ram != 16:
                errors.append("stage_16gb_setup.minimum_ram_gb must be 16.")
            missing_blocks = sorted(REQUIRED_16GB_BLOCKS - blocked)
            if missing_blocks:
                errors.append("stage_16gb_setup.blocked_work missing: " + ", ".join(missing_blocks))
        if stage_id == "stage_64gb_local_life":
            if int(stage.get("recommended_ram_gb", 0) or 0) < 64:
                errors.append("stage_64gb_local_life.recommended_ram_gb must be at least 64.")
            missing_allowed = sorted(REQUIRED_64GB_ALLOWED - allowed)
            if missing_allowed:
                errors.append("stage_64gb_local_life.allowed_work missing: " + ", ".join(missing_allowed))
        if stage_id == "stage_gpu_expansion":
            if stage.get("requires_gpu") is not True:
                errors.append("stage_gpu_expansion.requires_gpu must be true.")
            if int(stage.get("minimum_gpu_vram_gb", 0) or 0) < 12:
                errors.append("stage_gpu_expansion.minimum_gpu_vram_gb must be at least 12.")
            missing_allowed = sorted(REQUIRED_GPU_ALLOWED - allowed)
            if missing_allowed:
                errors.append("stage_gpu_expansion.allowed_work missing: " + ", ".join(missing_allowed))

    policy = data.get("activation_policy")
    if not isinstance(policy, dict):
        errors.append("activation_policy must be an object.")
        policy = {}
    for key in (
        "kira_before_lisa_on_new_desktop",
        "temporary_ai_requires_kira_lisa_stability",
        "voice_requires_explicit_stage_check",
        "vision_avatar_world_require_gpu_stage",
        "first_hour_uses_new_desktop_rehearsal",
    ):
        if policy.get(key) is not True:
            errors.append(f"activation_policy.{key} must be true.")
    _require_string(errors, policy, "stage_truth_rule", "activation_policy")
    _require_string(errors, policy, "memory_rule", "activation_policy")

    success = data.get("success_definition")
    if not isinstance(success, list) or len(success) < 5:
        errors.append("success_definition must contain at least 5 statements.")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate hardware capability profile JSON.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_hardware_capability_profile(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
