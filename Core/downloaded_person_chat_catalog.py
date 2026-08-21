"""Clean-checkout chat routes and exact per-person voice bindings.

The catalog keeps persistent people, the local Lisa route, and TemporaryAI
drafts in separate identity classes.  TemporaryAI custom voice profiles are
bound by exact candidate id and expected voice id; display-name guessing is
not an authorization mechanism.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class PersonChatRoute:
    person_id: str
    display_name: str
    identity_class: str
    launcher: str
    chat_mode: str
    voice_mode: str
    candidate_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


FIXED_PERSON_ROUTES = (
    PersonChatRoute(
        person_id="kira",
        display_name="Kira",
        identity_class="portable_persistent_person",
        launcher=(
            "handoff/hanson_little_sophia_20260819/portable_runtime/launchers/"
            "Kira Text and Voice Chat.cmd"
        ),
        chat_mode="portable_persistent_runtime",
        voice_mode="identity_bound_private_pack_then_text_only",
    ),
    PersonChatRoute(
        person_id="synthetic_robert",
        display_name="Synthetic Robert",
        identity_class="portable_persistent_person",
        launcher=(
            "handoff/hanson_little_sophia_20260819/portable_runtime/launchers/"
            "Synthetic Robert Text and Voice Chat.cmd"
        ),
        chat_mode="portable_persistent_runtime",
        voice_mode="authorized_self_voice_then_text_only",
    ),
    PersonChatRoute(
        person_id="lisa",
        display_name="Lisa",
        identity_class="resident_person",
        launcher="Start_Lisa_Chat.bat",
        chat_mode="resident_text_runtime",
        voice_mode="generic_os_voice_only_when_explicitly_enabled",
    ),
)


TEMPORARY_AI_GUI_LAUNCHER = "Start_TemporaryAI_Live_Chat_GUI.bat"
AUTHORITATIVE_USER_AVATAR_BOUNDARY = (
    "System/Docs/USER_AVATAR_AUTONOMY_AND_VR_HANDOFF_v1.md"
)

# Exact voice binding records.  A profile path discovered from a display name
# is not accepted.  The three owner-directed bounded-review packs below are
# permitted only when the exact profile bytes, candidate/voice/target fields,
# approved-reference path and WAV bytes all match.  This authorizes a private
# reconstruction output route, never an authentic-voice claim or activation.
TEMPORARY_AI_CUSTOM_VOICE_BINDINGS: dict[str, dict[str, Any]] = {
    "h_h_holmes_h_h_holmes_20260605_221432": {
        "voice_profile_path": "Voice/profiles/temp_ai/h_h_holmes_voice_profile.json",
        "expected_profile_sha256": "3c6178fd003d93719591636391c30d18758870d0c825fbdf79c17bc5fc2ddc0d",
        "expected_voice_id": "h_h_holmes_estimated_voice_v1",
        "expected_target_name": "H. H. Holmes",
        "expected_target_type": "",
        "profile_bounded_custom_voice_allowed": False,
        "authentic_voice_claim_allowed": False,
        "review_label": "generic operating-system approximation; not authentic",
    },
    "kathryn_merteuil_kathryn_merteuil_20260605_213017": {
        "voice_profile_path": "Voice/profiles/temp_ai/kathryn_merteuil_voice_profile.json",
        "expected_profile_sha256": "fd6c1ebc7a8f8199737653b90d92cf53056e2652d1e337729378311a14d1c896",
        "expected_voice_id": "kathryn_merteuil_owner_attested_reference_v1",
        "expected_target_name": "Kathryn Merteuil",
        "expected_target_type": "temp_ai",
        "approved_reference_path": "Voice/reference_packs/kathryn_merteuil/owner_attested_youtube_20260717/model_input/approved_reference.wav",
        "approved_reference_sha256": "d0bcfdb7cde7a1c28dcf33c346e1c6a92b3b8cfd7db64e559ff866202b092916",
        "profile_bounded_custom_voice_allowed": True,
        "authentic_voice_claim_allowed": False,
        "review_label": "Kathryn Merteuil exact reviewed reference pack; synthesized new speech",
    },
    "ladybug_marinette_expanded_smoke": {
        "voice_profile_path": "Voice/profiles/temp_ai/ladybug_voice_profile.json",
        "expected_profile_sha256": "22abeadcf9821234b35bf48c6338cbdc89738b2285ef2514b423240f4133b998",
        "expected_voice_id": "ladybug_voice_canon_v1",
        "expected_target_name": "Ladybug",
        "expected_target_type": "temp_ai",
        "approved_reference_path": "Voice/reference_packs/ladybug/ladybug_miraculous_ladybug_s01e05_mr_pigeon_20260619_184235/model_input/approved_reference.wav",
        "approved_reference_sha256": "9bfce1b418d0366bff446a60893513563c4987ec2e7db483b9cfddbbfeed0f2a",
        "profile_bounded_custom_voice_allowed": True,
        "authentic_voice_claim_allowed": False,
        "review_label": "Ladybug exact reviewed reference pack; synthesized new speech",
    },
    "peter_parker_spider_man_no_way_home_final_suit": {
        "voice_profile_path": "Voice/profiles/temp_ai/peter_parker_voice_profile.json",
        "expected_profile_sha256": "04f604b69d13fbfb1ad3b9e27797177bf39e45d1eeb6ed8d0567d9b633b861c1",
        "expected_voice_id": "peter_parker_reviewed_reference_v1",
        "expected_target_name": "Peter Parker",
        "expected_target_type": "temp_ai",
        "approved_reference_path": "Voice/reference_packs/peter_parker/peter_parker_online_source_20260706_035930/model_input/approved_reference.wav",
        "approved_reference_sha256": "0cbeff9bc1811fc626ef649cc1649d209f767bcd64200a0b93d3e8833bbe2af4",
        "profile_bounded_custom_voice_allowed": True,
        "authentic_voice_claim_allowed": False,
        "review_label": "Peter Parker exact reviewed reference pack; synthesized new speech",
    },
}


SYNTHETIC_ROBERT_SEPARATION = {
    "person_id": "synthetic_robert",
    "authoritative_boundary_doc": AUTHORITATIVE_USER_AVATAR_BOUNDARY,
    "synthetic_robert_controls": "synthetic_robert_own_body_and_session_only",
    "user_login_presence": "separate_user_avatar_with_distinct_body_session_and_identity",
    "likeness_rule": "user_avatar_may_visually_resemble_synthetic_robert_without_identity_merge",
    "prohibited": (
        "body_takeover",
        "session_takeover",
        "identity_merge",
        "impersonation",
        "memory_transfer",
        "voice_substitution",
        "body_sharing",
    ),
    "old_13th_floor_body_takeover_concept": "abandoned",
}


def exact_candidate_voice_binding(candidate_id: str) -> dict[str, Any] | None:
    row = TEMPORARY_AI_CUSTOM_VOICE_BINDINGS.get(str(candidate_id))
    if row is None:
        return None
    return {"candidate_id": str(candidate_id), **row}


def bind_review_and_voice_route(
    candidate: Mapping[str, Any],
    *,
    review_mode: str,
    full_source_reason: str = "",
) -> dict[str, Any]:
    """Publish one decision consumed by both reply and voice paths."""

    bound = deepcopy(dict(candidate))
    candidate_id = str(bound.get("candidate_id") or "")
    if review_mode not in {"full_source_grounded_review", "profile_bounded_draft"}:
        raise ValueError("unsupported_review_mode")
    profile_bounded = review_mode == "profile_bounded_draft"
    binding = exact_candidate_voice_binding(candidate_id)
    bounded_custom_voice = bool(
        profile_bounded
        and binding
        and binding.get("profile_bounded_custom_voice_allowed") is True
        and binding.get("authentic_voice_claim_allowed") is False
    )
    bound["review_mode"] = review_mode
    bound["text_route_decision"] = {
        "allowed": True,
        "review_mode": review_mode,
        "full_source_grounding_complete": not profile_bounded,
        "profile_bounded_label_required": profile_bounded,
        "voice_output_allowed": True,
        "custom_voice_output_allowed": not profile_bounded or bounded_custom_voice,
        "generic_os_voice_output_allowed": True,
        "error_or_exception_text_may_reach_tts": False,
        "full_source_route_unavailable_reason": str(full_source_reason),
    }
    if binding is not None:
        bound["voice_route_binding"] = binding
    return bound


def discover_downloaded_person_routes(project_root: str | Path) -> list[PersonChatRoute]:
    """List every checked-in conversational profile without activating it."""

    root = Path(project_root)
    routes = list(FIXED_PERSON_ROUTES)
    candidate_root = root / "TemporaryAI" / "candidates"
    if not candidate_root.is_dir():
        return routes
    for path in sorted(candidate_root.iterdir(), key=lambda item: item.name):
        if not path.is_dir() or not (path / "temporary_ai_profile.json").is_file():
            continue
        # Display names are informational only; runtime selection remains the
        # exact directory/candidate id.
        try:
            profile = json.loads(
                (path / "temporary_ai_profile.json").read_text(encoding="utf-8-sig")
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(profile, dict):
            continue
        routes.append(
            PersonChatRoute(
                person_id=path.name,
                display_name=str(profile.get("display_name") or path.name),
                identity_class="temporary_ai_review_candidate",
                launcher=TEMPORARY_AI_GUI_LAUNCHER,
                chat_mode="runtime_selected_full_or_profile_bounded_review",
                voice_mode="exact_custom_binding_first_else_labeled_generic_os_fallback",
                candidate_id=path.name,
            )
        )
    return routes
