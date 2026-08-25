from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
SOURCE_RELATIVE_PATH = (
    "Voice/local_voice_studio/evidence/"
    "avatar_temporary_creator_voice_integration.json"
)
EXPECTED_SOURCE_PATH = REPOSITORY_ROOT / PurePosixPath(SOURCE_RELATIVE_PATH)
MAX_SOURCE_BYTES = 256 * 1024
MAX_STRING_LENGTH = 512
MAX_CONTAINER_ITEMS = 256
SOURCE_SCHEMA = "kira.local-voice.avatar-temporary-creator-audition-plan.v1"
OUTPUT_SCHEMA = "kira.qwen3.profile-audition-request-plan.v1"
OUTPUT_STATUS = (
    "NONBINDING_AUDITION_REQUESTS_ONLY_NOT_GENERATED_NOT_APPROVED_NOT_ACTIVE"
)
FEASIBILITY_REQUEST_SCHEMA = "kira-qwen3-voice-design-feasibility-v1"
HISTORICAL_DISCLOSURE = (
    "Speculative historical reconstruction; not an authentic recording, "
    "verified voice match, or identity clone."
)

TOP_LEVEL_KEYS = {
    "audition_locale",
    "candidates",
    "integration_boundary",
    "inventory_scope",
    "schema",
    "selection_policy",
    "source_authority",
    "summary",
    "unbound_legacy_voice_profiles",
}
SIMPLE_CANDIDATE_KEYS = {
    "action",
    "audition_brief",
    "canonical_candidate_id",
    "existing_voice",
    "identity_class",
    "mutation_performed",
    "review_blockers",
    "review_gates",
    "source_presence",
    "storage_id",
    "subject_id",
    "temporary_ai_activation_allowed",
    "voice_binding_created",
}
AUDITION_CANDIDATE_KEYS = SIMPLE_CANDIDATE_KEYS | {
    "adapter_status",
    "binding_status",
    "creator_source_attestation",
    "fit_limitations",
    "required_disclosure",
}
BRIEF_KEYS = {
    "age_band",
    "assignment_mode",
    "body_presence",
    "candidate_count",
    "display_name",
    "era",
    "existing_voice_id",
    "gender",
    "identity_kind",
    "language",
    "language_provenance",
    "personality_traits",
    "role",
    "schema",
    "source_attestation",
    "subject_id",
}
SOURCE_ATTESTATION_KEYS = {
    "candidate_id",
    "profile_sha256",
    "registry_alias",
    "registry_sha256",
    "request_sha256",
    "storage_id",
}
SOURCE_PRESENCE_KEYS = {
    "creation_request",
    "profile",
    "voice_discovery_request",
}
AUDITION_REVIEW_GATES_KEYS = {
    "distinctness_review_required",
    "exact_candidate_shared_spec_hash_required",
    "human_audition_required",
    "owner_approval_can_activate",
    "provenance_review_required",
    "source_locale_confirmation_required_before_binding",
    "subject_comparative_selection_required",
}
CREATOR_SOURCE_ATTESTATION_KEYS = {
    "activation_plan_relative_path",
    "activation_plan_sha256",
    "activation_status",
    "creation_request_relative_path",
    "creation_request_sha256",
    "creation_status",
    "voice_discovery_request_relative_path",
    "voice_discovery_request_sha256",
    "voice_discovery_status",
}
SIMPLE_REVIEW_GATES_KEYS = {
    "human_audition_required",
    "owner_approval_can_activate",
    "subject_comparative_selection_required",
}
SELECTION_POLICY_KEYS = {
    "generated_or_historical_candidate_human_audition_required",
    "kira_and_lisa_owner_approval_only_makes_candidates_eligible",
    "kira_and_lisa_subject_comparative_selection_required",
    "kira_current_route_remains_rollback_until_kira_selects",
    "peter_and_marinette_existing_voices_remain_unchanged",
}
LEGACY_PROFILE_KEYS = {
    "explicit_authority_candidate_id",
    "explicit_candidate_id_absent",
    "filename",
    "resolution",
    "voice_id",
    "voice_profile_relative_path",
    "voice_profile_sha256",
    "voice_status",
}
EXISTING_VOICE_KEYSETS = {
    frozenset(
        {
            "voice_id",
            "voice_profile_relative_path",
            "voice_profile_sha256",
            "voice_status",
        }
    ),
    frozenset(
        {
            "policy",
            "voice_id",
            "voice_profile_relative_path",
            "voice_profile_sha256",
            "voice_status",
        }
    ),
    frozenset(
        {
            "automatic_fallback_routes",
            "policy",
            "preferred_route",
            "route_relative_path",
            "route_sha256",
            "voice_id",
            "voice_profile_relative_path",
            "voice_profile_sha256",
        }
    ),
}
AUDITION_ACTIONS = {
    "prepare_nonbinding_audition_brief",
    "prepare_nonbinding_speculative_historical_audition_brief",
}
NON_AUDITION_ACTIONS = {
    "needs_review_source_records_missing",
    "preserve_authorized_self_voice",
    "preserve_current_kira_route",
    "preserve_existing_voice_profile",
}
EXPECTED_AUDITION_IDS = {
    "emily_carter_ai_and_computer_programming_expert_20260605_220651",
    "h_h_holmes_h_h_holmes_20260605_221432",
    "jessica_hale_robotics_engineer_20260611_041314",
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
    "ryan_hale_quantum_mechanics_expert_20260608_200749",
    "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
}
GENDER_PRESENTATION = {
    "female": "adult_woman",
    "male": "adult_man",
}
VARIANT_PALETTES = (
    (
        "calm_clear",
        "c1",
        {
            "pitch": "mid",
            "timbre": "clear",
            "pace": "moderate",
            "warmth": "neutral",
            "confidence": "steady",
            "energy": "calm",
            "accent": "general_american",
            "breathiness": "low",
        },
    ),
    (
        "warm_rounded",
        "c2",
        {
            "pitch": "mid",
            "timbre": "rounded",
            "pace": "moderate",
            "warmth": "warm",
            "confidence": "gentle",
            "energy": "balanced",
            "accent": "general_american",
            "breathiness": "low",
        },
    ),
    (
        "grounded_assured",
        "c3",
        {
            "pitch": "lower_mid",
            "timbre": "grounded",
            "pace": "moderate",
            "warmth": "neutral",
            "confidence": "assured",
            "energy": "balanced",
            "accent": "general_american",
            "breathiness": "low",
        },
    ),
)
ROLE_TEST_TEXT = {
    "emily_carter_generated_expert": (
        "This nonbinding audition tests a clear explanation for an AI and "
        "computer programming expert. A careful answer separates assumptions, "
        "evidence, and practical next steps."
    ),
    "h_h_holmes": (
        HISTORICAL_DISCLOSURE
        + " This nonbinding audition tests clear, neutral narration only."
    ),
    "jessica_hale_generated_expert": (
        "This nonbinding audition tests a clear explanation for a robotics "
        "engineer. The explanation should separate sensing, planning, and safe "
        "physical action."
    ),
    "laura_mitchell_generated_expert": (
        "This nonbinding audition tests a clear explanation for a New Jersey "
        "criminal attorney expert. It distinguishes general information from "
        "advice for a specific case."
    ),
    "ryan_hale_generated_expert": (
        "This nonbinding audition tests a clear explanation for a quantum "
        "mechanics expert. It should define the idea before using an example or "
        "equation."
    ),
    "sarah_bennett_generated_expert": (
        "This nonbinding audition tests a clear explanation for an entertainment "
        "public relations expert. It should identify the audience, message, and "
        "next action."
    ),
}
WINDOWS_RESERVED_NAMES = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _is_link_or_junction(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _validate_tree_shape(value: object, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("source JSON nesting is too deep")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("source JSON contains a non-finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError("source JSON string is too long")
        if any(ord(character) < 32 for character in value):
            raise ValueError("source JSON string contains a control character")
        return
    if isinstance(value, list):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ValueError("source JSON list is too large")
        for item in value:
            _validate_tree_shape(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise ValueError("source JSON object is too large")
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError("source JSON object key is invalid")
            _validate_tree_shape(key, depth + 1)
            _validate_tree_shape(item, depth + 1)
        return
    raise ValueError("source JSON contains an unsupported value")


def _require_exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} keys do not match the required schema")
    return value


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} is not a lowercase SHA-256")
    return value


def _require_identifier(value: object, label: str, maximum: int = 128) -> str:
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,127}", value)
    ):
        raise ValueError(f"{label} is not a safe identifier")
    return value


def _require_safe_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{label} is not a bounded relative path")
    if "\\" in value or ":" in value:
        raise ValueError(f"{label} is not a POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} is not a safe relative path")
    return value


def _validate_recursive_attestations(value: object) -> None:
    if isinstance(value, list):
        for item in value:
            _validate_recursive_attestations(item)
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key.endswith("_sha256"):
            _require_sha256(item, key)
        elif key.endswith("_relative_path"):
            _require_safe_relative_path(item, key)
        _validate_recursive_attestations(item)


def parse_source_bytes(payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_SOURCE_BYTES:
        raise ValueError("source plan size is outside the allowed bound")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("source plan is not valid UTF-8") from error
    document = json.loads(
        text,
        object_pairs_hook=strict_object,
        parse_constant=reject_constant,
    )
    _validate_tree_shape(document)
    return validate_source_document(document)


def validate_source_document(document: object) -> dict[str, Any]:
    plan = _require_exact_keys(document, TOP_LEVEL_KEYS, "source plan")
    if plan["schema"] != SOURCE_SCHEMA:
        raise ValueError("unsupported source plan schema")
    if plan["inventory_scope"] != "current_temporary_ai_profile":
        raise ValueError("unexpected source inventory scope")

    locale = _require_exact_keys(
        plan["audition_locale"],
        {"provenance", "sufficient_for_binding", "value", "written_to_source_profiles"},
        "audition_locale",
    )
    if locale != {
        "provenance": "application_audition_default",
        "sufficient_for_binding": False,
        "value": "en-US",
        "written_to_source_profiles": False,
    }:
        raise ValueError("audition locale is not the explicit unbound en-US default")

    boundary = _require_exact_keys(
        plan["integration_boundary"],
        {
            "audition_audio_generated",
            "next_stage",
            "runtime_route_changed",
            "shared_person_spec_promotion_claimed",
            "source_profiles_modified",
            "temporary_ai_activated",
            "voice_binding_created",
            "voice_profiles_overwritten",
        },
        "integration_boundary",
    )
    for key in (
        "audition_audio_generated",
        "runtime_route_changed",
        "shared_person_spec_promotion_claimed",
        "source_profiles_modified",
        "temporary_ai_activated",
        "voice_binding_created",
        "voice_profiles_overwritten",
    ):
        if boundary[key] is not False:
            raise ValueError(f"source integration boundary is not read-only: {key}")
    if boundary["next_stage"] != (
        "immutable audition bundles and audio only after runtime evidence and human review"
    ):
        raise ValueError("source integration boundary next stage is unexpected")

    source_authority = _require_exact_keys(
        plan["source_authority"],
        {
            "registry_relative_path",
            "registry_sha256",
            "trusted_preflight_relative_path",
            "trusted_preflight_sha256",
        },
        "source_authority",
    )
    _require_safe_relative_path(
        source_authority["registry_relative_path"], "registry_relative_path"
    )
    _require_sha256(source_authority["registry_sha256"], "registry_sha256")
    _require_safe_relative_path(
        source_authority["trusted_preflight_relative_path"],
        "trusted_preflight_relative_path",
    )
    _require_sha256(
        source_authority["trusted_preflight_sha256"], "trusted_preflight_sha256"
    )

    summary = _require_exact_keys(
        plan["summary"],
        {
            "activation_allowed_count",
            "binding_ready_count",
            "needs_review_count",
            "nonbinding_audition_brief_count",
            "preserved_voice_or_route_count",
            "registered_candidate_count",
            "source_profile_present_count",
        },
        "summary",
    )
    for key, value in summary.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"summary count is invalid: {key}")

    selection_policy = _require_exact_keys(
        plan["selection_policy"], SELECTION_POLICY_KEYS, "selection_policy"
    )
    if any(value is not True for value in selection_policy.values()):
        raise ValueError("selection_policy does not preserve current protections")
    legacy_profiles = plan["unbound_legacy_voice_profiles"]
    if not isinstance(legacy_profiles, list) or len(legacy_profiles) != 3:
        raise ValueError("unbound_legacy_voice_profiles must be a list")
    for index, legacy_profile in enumerate(legacy_profiles):
        profile = _require_exact_keys(
            legacy_profile, LEGACY_PROFILE_KEYS, f"legacy profile {index}"
        )
        _require_identifier(
            profile["explicit_authority_candidate_id"],
            f"legacy profile {index} authority",
        )
        if profile["explicit_candidate_id_absent"] is not True:
            raise ValueError("legacy profile does not preserve absence status")
        if (
            not isinstance(profile["filename"], str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,127}\.json", profile["filename"])
        ):
            raise ValueError("legacy profile filename is invalid")
    _validate_recursive_attestations(plan)

    candidates = plan["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    seen_ids: set[str] = set()
    audition_ids: set[str] = set()
    preserved_count = 0
    missing_count = 0
    profile_present_count = 0
    for index, raw_candidate in enumerate(candidates):
        if not isinstance(raw_candidate, dict):
            raise ValueError(f"candidate {index} is not an object")
        action = raw_candidate.get("action")
        if action in AUDITION_ACTIONS:
            candidate = _require_exact_keys(
                raw_candidate, AUDITION_CANDIDATE_KEYS, f"candidate {index}"
            )
        elif action in NON_AUDITION_ACTIONS:
            candidate = _require_exact_keys(
                raw_candidate, SIMPLE_CANDIDATE_KEYS, f"candidate {index}"
            )
        else:
            raise ValueError(f"candidate {index} has an unsupported action")

        canonical_id = _require_identifier(
            candidate["canonical_candidate_id"], f"candidate {index} id"
        )
        if canonical_id in seen_ids:
            raise ValueError("duplicate canonical candidate id")
        seen_ids.add(canonical_id)
        _require_identifier(candidate["storage_id"], f"candidate {index} storage_id")
        _require_identifier(candidate["subject_id"], f"candidate {index} subject_id")
        presence = _require_exact_keys(
            candidate["source_presence"], SOURCE_PRESENCE_KEYS, "source_presence"
        )
        if not all(isinstance(presence[key], bool) for key in SOURCE_PRESENCE_KEYS):
            raise ValueError("source_presence values must be booleans")
        if presence["profile"]:
            profile_present_count += 1
        if candidate["mutation_performed"] is not False:
            raise ValueError("source candidate reports a mutation")
        if candidate["temporary_ai_activation_allowed"] is not False:
            raise ValueError("source candidate permits activation")
        if candidate["voice_binding_created"] is not False:
            raise ValueError("source candidate reports a voice binding")

        if action in AUDITION_ACTIONS:
            audition_ids.add(canonical_id)
            _validate_audition_candidate(candidate)
        else:
            if candidate["audition_brief"] is not None:
                raise ValueError("non-audition candidate contains an audition brief")
            simple_gates = _require_exact_keys(
                candidate["review_gates"], SIMPLE_REVIEW_GATES_KEYS, "review_gates"
            )
            if any(not isinstance(value, bool) for value in simple_gates.values()):
                raise ValueError("non-audition review gates must be booleans")
            _validate_existing_voice(candidate["existing_voice"])
            if action.startswith("preserve_"):
                preserved_count += 1
            if action == "needs_review_source_records_missing":
                missing_count += 1

    if audition_ids != EXPECTED_AUDITION_IDS:
        raise ValueError("eligible audition candidates do not match the current six")
    if summary["registered_candidate_count"] != len(candidates):
        raise ValueError("registered candidate summary does not match")
    if summary["nonbinding_audition_brief_count"] != len(audition_ids):
        raise ValueError("audition summary does not match")
    if summary["preserved_voice_or_route_count"] != preserved_count:
        raise ValueError("preserved voice summary does not match")
    if summary["needs_review_count"] != missing_count:
        raise ValueError("needs-review summary does not match")
    if summary["source_profile_present_count"] != profile_present_count:
        raise ValueError("source-profile summary does not match")
    if summary["activation_allowed_count"] != 0 or summary["binding_ready_count"] != 0:
        raise ValueError("source plan unexpectedly permits activation or binding")
    return plan


def _validate_existing_voice(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or frozenset(value) not in EXISTING_VOICE_KEYSETS:
        raise ValueError("existing voice does not match a known preserved schema")
    if "automatic_fallback_routes" in value:
        routes = value["automatic_fallback_routes"]
        if (
            not isinstance(routes, list)
            or not routes
            or any(not isinstance(route, str) or not route for route in routes)
        ):
            raise ValueError("existing voice fallback routes are invalid")


def _validate_audition_candidate(candidate: dict[str, Any]) -> None:
    if candidate["adapter_status"] != "ready_for_nonbinding_audition":
        raise ValueError("audition adapter is not ready")
    if candidate["binding_status"] != "needs_review":
        raise ValueError("audition candidate is not blocked from binding")
    if candidate["source_presence"] != {
        "creation_request": True,
        "profile": True,
        "voice_discovery_request": True,
    }:
        raise ValueError("audition candidate is missing required source records")
    if candidate["review_blockers"] != ["locale"]:
        raise ValueError("audition candidate is missing the locale blocker")
    gates = _require_exact_keys(
        candidate["review_gates"], AUDITION_REVIEW_GATES_KEYS, "review_gates"
    )
    if gates != {
        "distinctness_review_required": True,
        "exact_candidate_shared_spec_hash_required": True,
        "human_audition_required": True,
        "owner_approval_can_activate": False,
        "provenance_review_required": True,
        "source_locale_confirmation_required_before_binding": True,
        "subject_comparative_selection_required": False,
    }:
        raise ValueError("audition candidate review gates are unsafe")
    creator_attestation = _require_exact_keys(
        candidate["creator_source_attestation"],
        CREATOR_SOURCE_ATTESTATION_KEYS,
        "creator_source_attestation",
    )
    if (
        creator_attestation["activation_status"] != "pending_review"
        or creator_attestation["voice_discovery_status"]
        not in {
            "metadata_discovery_request_not_run",
            "metadata_discovery_request_ready",
        }
        or creator_attestation["creation_status"]
        not in {"draft_pending_review", "needs_clarification"}
    ):
        raise ValueError("creator source attestation status is unsafe")

    brief = _require_exact_keys(candidate["audition_brief"], BRIEF_KEYS, "audition_brief")
    if brief["schema"] != "kira.local-voice.design-brief.v1":
        raise ValueError("unsupported audition brief schema")
    if brief["candidate_count"] != 3:
        raise ValueError("audition brief must request exactly three candidates")
    if brief["assignment_mode"] != "assign_if_missing":
        raise ValueError("unsupported audition assignment mode")
    if brief["age_band"] != "adult":
        raise ValueError("only the authored adult age band is supported")
    if brief["existing_voice_id"] is not None:
        raise ValueError("audition brief attempts to carry an existing voice")
    if brief["language"] != "en-US" or brief["language_provenance"] != "application_audition_default":
        raise ValueError("audition brief locale is not the explicit application default")
    gender = brief["gender"]
    if gender not in GENDER_PRESENTATION:
        raise ValueError("audition brief gender has no exact presentation mapping")
    if brief["body_presence"] != "not_authored":
        raise ValueError("planner does not consume body-derived guesses")
    if brief["personality_traits"] != []:
        raise ValueError("planner does not consume personality-derived guesses")
    if brief["era"] not in {"unspecified", "historical"}:
        raise ValueError("audition brief era is unsupported")
    expected_fit_limitations = {
        "body_not_authored_zero_affinity",
        "locale_confirmation_required_before_binding",
        "personality_tags_not_authored_zero_affinity",
    }
    if brief["era"] == "unspecified":
        expected_fit_limitations.add("era_not_authored_zero_affinity")
    if (
        not isinstance(candidate["fit_limitations"], list)
        or set(candidate["fit_limitations"]) != expected_fit_limitations
        or len(candidate["fit_limitations"]) != len(expected_fit_limitations)
    ):
        raise ValueError("audition fit limitations do not preserve missing dimensions")
    if not isinstance(brief["display_name"], str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9 .&'+-]{0,79}", brief["display_name"]
    ):
        raise ValueError("audition display name is invalid")
    if not isinstance(brief["role"], str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9 .&+'/-]{0,119}", brief["role"]
    ):
        raise ValueError("audition role is invalid")
    if brief["subject_id"] != candidate["subject_id"]:
        raise ValueError("audition subject id does not match candidate")
    attestation = _require_exact_keys(
        brief["source_attestation"], SOURCE_ATTESTATION_KEYS, "source_attestation"
    )
    if attestation["candidate_id"] != candidate["canonical_candidate_id"]:
        raise ValueError("source attestation candidate id does not match")
    if attestation["storage_id"] != candidate["storage_id"]:
        raise ValueError("source attestation storage id does not match")
    if attestation["registry_alias"] is not None:
        _require_identifier(attestation["registry_alias"], "registry_alias")

    if candidate["canonical_candidate_id"] == "h_h_holmes_h_h_holmes_20260605_221432":
        if candidate["action"] != "prepare_nonbinding_speculative_historical_audition_brief":
            raise ValueError("historical candidate action is not speculative")
        if candidate["required_disclosure"] != HISTORICAL_DISCLOSURE:
            raise ValueError("historical candidate disclosure is not exact")
        if candidate["identity_class"] != "historical_person" or brief["identity_kind"] != "historical":
            raise ValueError("historical candidate identity classification is invalid")
        _validate_existing_voice(candidate["existing_voice"])
    else:
        if candidate["action"] != "prepare_nonbinding_audition_brief":
            raise ValueError("generated candidate action is invalid")
        if candidate["required_disclosure"] is not None:
            raise ValueError("generated expert has an unexpected disclosure")
        if candidate["identity_class"] != "generated_expert" or brief["identity_kind"] != "original":
            raise ValueError("generated candidate identity classification is invalid")
        if candidate["existing_voice"] is not None:
            raise ValueError("generated candidate unexpectedly carries an existing voice")


def load_source_plan(path: Path = EXPECTED_SOURCE_PATH) -> tuple[dict[str, Any], bytes, str]:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("source plan path must be the exact absolute trusted path")
    if supplied != EXPECTED_SOURCE_PATH:
        raise ValueError("source plan path is not the trusted integration plan")
    inspected = REPOSITORY_ROOT
    for part in PurePosixPath(SOURCE_RELATIVE_PATH).parts:
        inspected /= part
        if _is_link_or_junction(inspected):
            raise ValueError("source plan path contains a link or junction")
    if not supplied.is_file() or _is_link_or_junction(supplied):
        raise ValueError("source plan is missing or unsafe")
    payload = supplied.read_bytes()
    return parse_source_bytes(payload), payload, sha256_bytes(payload)


def _stable_request_id(subject_id: str, canonical_id: str, palette_id: str, code: str) -> str:
    prefix = subject_id[:38].rstrip("_-")
    digest = hashlib.sha256(
        f"{canonical_id}\0{palette_id}".encode("utf-8")
    ).hexdigest()[:12]
    candidate_id = f"{prefix}_{code}_{digest}"
    if len(candidate_id) > 64 or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", candidate_id):
        raise ValueError("generated request id is unsafe")
    return candidate_id


def _stable_seed(canonical_id: str, palette_id: str) -> int:
    digest = hashlib.sha256(
        f"seed\0{canonical_id}\0{palette_id}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _request_bytes(request: dict[str, Any]) -> bytes:
    return (json.dumps(request, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_request_plan(path: Path = EXPECTED_SOURCE_PATH) -> dict[str, Any]:
    source, source_bytes, source_sha256 = load_source_plan(path)
    source_candidates = {
        candidate["canonical_candidate_id"]: candidate
        for candidate in source["candidates"]
        if candidate["action"] in AUDITION_ACTIONS
    }
    bundles: list[dict[str, Any]] = []
    for canonical_id in sorted(EXPECTED_AUDITION_IDS):
        candidate = source_candidates[canonical_id]
        brief = candidate["audition_brief"]
        subject_id = brief["subject_id"]
        presentation = GENDER_PRESENTATION[brief["gender"]]
        variants: list[dict[str, Any]] = []
        for palette_id, code, generic_traits in VARIANT_PALETTES:
            request_id = _stable_request_id(subject_id, canonical_id, palette_id, code)
            voice_traits = {"presentation": presentation, **generic_traits}
            request = {
                "schema": FEASIBILITY_REQUEST_SCHEMA,
                "candidate_id": request_id,
                "language": "English",
                "text": ROLE_TEST_TEXT[subject_id],
                "voice_traits": voice_traits,
                "seed": _stable_seed(canonical_id, palette_id),
                "intent": "generated_original_no_named_person_imitation",
                "named_person_imitation": False,
                "nonproduction_feasibility": True,
            }
            encoded = _request_bytes(request)
            relative_path = f"requests/{subject_id}/{palette_id}.json"
            _require_safe_relative_path(relative_path, "generated request path")
            variants.append(
                {
                    "palette_id": palette_id,
                    "request_relative_path": relative_path,
                    "request_sha256": sha256_bytes(encoded),
                    "request": request,
                }
            )

        disclosure = candidate["required_disclosure"]
        bundles.append(
            {
                "bundle_id": subject_id,
                "canonical_candidate_id": canonical_id,
                "subject_id": subject_id,
                "identity_class": candidate["identity_class"],
                "display_name": brief["display_name"],
                "role": brief["role"],
                "source_attestation": brief["source_attestation"],
                "presentation_mapping": {
                    "source_gender": brief["gender"],
                    "qwen_presentation": presentation,
                },
                "locale": {
                    "value": "en-US",
                    "provenance": "application_audition_default",
                    "sufficient_for_binding": False,
                    "blocker": "source_locale_confirmation_required_before_binding",
                },
                "unfilled_dimensions_not_guessed": [
                    "body",
                    "personality",
                    *( ["era"] if brief["era"] == "unspecified" else [] ),
                    "confirmed_locale",
                ],
                "required_disclosure": disclosure,
                "authenticity_claimed": False,
                "identity_clone_claimed": False,
                "existing_voice_carried_forward": False,
                "variants": variants,
            }
        )

    return {
        "schema": OUTPUT_SCHEMA,
        "status": OUTPUT_STATUS,
        "source": {
            "relative_path": SOURCE_RELATIVE_PATH,
            "bytes": len(source_bytes),
            "sha256": source_sha256,
            "schema": SOURCE_SCHEMA,
        },
        "audition_locale": {
            "value": "en-US",
            "provenance": "application_audition_default",
            "sufficient_for_binding": False,
            "blocker": "source_locale_confirmation_required_before_binding",
        },
        "policy": {
            "candidate_count_per_bundle": 3,
            "generated_audio": False,
            "binding_created": False,
            "activation_allowed": False,
            "route_changed": False,
            "profile_mutation_performed": False,
            "preserved_existing_voice_included": False,
            "missing_source_identity_included": False,
            "named_person_imitation": False,
        },
        "bundles": bundles,
    }


def _validate_output_root(path: Path) -> Path:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise ValueError("output root must be a new absolute path without traversal")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", supplied.name):
        raise ValueError("output root name is unsafe")
    if supplied.name.endswith((".", " ")):
        raise ValueError("output root name has an unsafe Windows suffix")
    if supplied.name.rstrip(" .").lower() in WINDOWS_RESERVED_NAMES:
        raise ValueError("output root name is reserved on Windows")
    parent = supplied.parent
    if not parent.is_dir() or _is_link_or_junction(parent):
        raise ValueError("output parent is missing or unsafe")
    resolved_parent = parent.resolve(strict=True)
    resolved_target = resolved_parent / supplied.name
    if resolved_target.exists():
        raise ValueError("output root already exists")
    try:
        resolved_target.relative_to(REPOSITORY_ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("output root must remain outside the KiraWorld repository")
    return resolved_target


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as destination:
        destination.write(encoded)
        destination.flush()
        os.fsync(destination.fileno())


def write_request_plan(plan: dict[str, Any], output_root: Path) -> Path:
    # Rebuild from the trusted source immediately before writing. This both
    # closes a source-change race and prevents callers from injecting a path or
    # request into an otherwise plausible-looking plan object.
    if plan != build_request_plan():
        raise ValueError("request plan does not exactly match the trusted source")
    root = _validate_output_root(output_root)
    root.mkdir(mode=0o700)
    requests_root = root / "requests"
    requests_root.mkdir(mode=0o700)
    for bundle in plan["bundles"]:
        bundle_root = requests_root / bundle["subject_id"]
        bundle_root.mkdir(mode=0o700)
        for variant in bundle["variants"]:
            destination = root / PurePosixPath(variant["request_relative_path"])
            encoded = _request_bytes(variant["request"])
            if sha256_bytes(encoded) != variant["request_sha256"]:
                raise ValueError("request hash changed before write")
            with destination.open("xb") as target:
                target.write(encoded)
                target.flush()
                os.fsync(target.fileno())
    manifest_path = root / "audition-request-plan.json"
    _write_json_exclusive(manifest_path, plan)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create nonbinding Qwen audition request bundles from the trusted profile plan."
    )
    parser.add_argument("--source", type=Path, default=EXPECTED_SOURCE_PATH)
    parser.add_argument("--output-root", required=True, type=Path)
    arguments = parser.parse_args()
    plan = build_request_plan(arguments.source)
    manifest = write_request_plan(plan, arguments.output_root)
    print(
        json.dumps(
            {
                "status": OUTPUT_STATUS,
                "manifest": manifest.name,
                "bundle_count": len(plan["bundles"]),
                "request_count": sum(len(bundle["variants"]) for bundle in plan["bundles"]),
                "source_sha256": plan["source"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
