"""Append-only conversational correction memory for Avatar Builder.

This module records what the owner asked for and computes the scope of the
*next* private build.  It deliberately does not author, approve, activate, or
publish an avatar.  Component isolation and the two-stage spa age-progression
gate are data contracts that authoring workers must consume explicitly.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any


PETER_ADULT_ERA_CANDIDATE_ID = "peter_parker_spider_man_no_way_home_final_suit"
ADULT_MATURITY_CLASSES = frozenset({"adult"})
NON_ADULT_MATURITY_CLASSES = frozenset(
    {"non_adult_doll_safe", "uncertain_non_adult_safe_default"}
)
COMPONENTS = ("body", "face", "eyes", "skin", "rig", "weights", "movement", "hair")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _continuity_timepoint(message: str) -> dict[str, Any]:
    lowered = message.lower()
    markers: list[str] = []
    marker_terms = (
        ("end_of_series", ("end of the series", "series finale", "end of series")),
        ("post_graduation", ("after graduation", "after graduating", "graduated", "post-graduation")),
        ("post_college", ("post-college", "after college", "finished college")),
        ("adult_era", ("adult-era", "adult era", "adult version")),
        ("no_way_home", ("no way home",)),
        ("brand_new_day", ("brand new day",)),
        ("time_jump", ("time jump", "time-jump",)),
        ("not_high_school_era", ("not the high-school", "not the high school", "not high-school", "not high school")),
    )
    for marker, terms in marker_terms:
        if _contains_any(lowered, terms):
            markers.append(marker)

    years = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)[ -]year time[ -]jump\b", lowered)
    if years and "time_jump" not in markers:
        markers.append("time_jump")
    if not markers:
        return {}
    return {
        "owner_text": message.strip(),
        "markers": markers,
        "time_jump_text": years.group(0) if years else "",
        "interpretation_rule": (
            "Use the explicitly requested later continuity/timepoint. An isolated earlier-era "
            "term such as 'high school' is reference context and cannot override it."
        ),
    }


def derive_correction_directives(
    candidate_id: str,
    message: str,
    *,
    requested_maturity_class: str = "",
    previous_maturity_class: str = "",
    age_progression_stage_one_eligibility_gate: dict[str, Any] | None = None,
    age_progression_stage_two_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract narrow component and continuity directives from owner chat."""

    lowered = message.lower()
    components: list[str] = []
    intents: list[str] = []
    instructions: list[dict[str, str]] = []

    hair_hit = _contains_any(lowered, ("hair", "hairline", "bald", "pigtail", "bang", "groom"))
    if hair_hit:
        components.append("hair")
        intents.append("detachable_hair")
        hair_details: list[str] = []
        if _contains_any(lowered, ("look bald", "looks bald", "going bald", "fuller hair", "more hair", "thicker hair", "dense hair")):
            hair_details.append("increase realistic coverage and fullness")
            intents.append("hair_fullness")
        if _contains_any(lowered, ("hairline", "too far back", "receding")):
            hair_details.append("correct the detachable hairline position and coverage")
            intents.append("hairline_fit")
        detail = "; ".join(hair_details) or "apply the requested hairstyle correction"
        instructions.append({
            "area": "hair",
            "instruction": (
                f"Modify only the detachable hair component: {detail}. Preserve the accepted face, "
                "body, eyes, scalp, skin, rig, weights, and movement byte-for-byte."
            ),
        })

    if _contains_any(lowered, ("eye", "eyes", "socket", "sclera", "iris", "pupil")):
        components.append("eyes")
        intents.append("eyes")
        socket_problem = _contains_any(
            lowered,
            ("outside the socket", "outside the sockets", "inside the socket", "inside the sockets", "floating eye", "floating eyes", "socket"),
        )
        if socket_problem:
            intents.append("eye_socket_fit")
        instructions.append({
            "area": "eyes",
            "instruction": (
                "Correct the named eye assembly and verify both eyes are seated inside measured socket rims "
                "with eyelid contact; preserve accepted face/body/hair components."
                if socket_problem
                else "Apply the requested correction to the separate named eye assembly and preserve other accepted components."
            ),
        })

    if _contains_any(lowered, ("face does not look", "face doesn't look", "does not look like", "doesn't look like", "face likeness", "likeness", "face is generic", "generic face")):
        components.append("face")
        intents.append("face_likeness")
        instructions.append({
            "area": "face",
            "instruction": (
                "Reroute the next private face pass to candidate-specific approved references and landmarks; "
                "do not treat a generic face as likeness evidence and preserve accepted body/rig components."
            ),
        })

    if _contains_any(
        lowered,
        (
            "adult body",
            "adult male body",
            "adult female body",
            "adult anatomy",
            "full anatomy",
            "anatomical body",
            "body shape",
            "body fit",
        ),
    ):
        components.append("body")
        intents.append("separate_body_or_anatomy_request")
        instructions.append({
            "area": "body",
            "instruction": (
                "Treat this as a separate body/anatomy request, not as maturity proof or body approval. "
                "Apply the exact maturity and, for spa-origin variants, Stage 2 evidence/choice gate before authoring."
            ),
        })

    continuity = _continuity_timepoint(message)
    if continuity:
        intents.append("continuity_timepoint")
        instructions.append({
            "area": "continuity",
            "instruction": (
                "Use Robert's explicit requested continuity/timepoint for the next private build. "
                "Earlier-era words in reference context cannot silently change the maturity lane."
            ),
        })

    maturity: dict[str, Any] = {}
    requested = requested_maturity_class.strip()
    previous = previous_maturity_class.strip()
    if requested:
        owner_authority = {
            "authority": "Robert_explicit_owner_correction",
            "network_lookup_required": False,
            "offline_owner_confirmation_allowed": True,
            "scope": "fictional_or_character_continuity_and_requested_version_classification",
            "logged_message_required": True,
        }
        maturity = {
            "requested_class": requested,
            "previous_class": previous,
            "owner_authority": owner_authority,
            "classification_correction_is_body_approval": False,
        }
        intents.append(f"maturity:{requested}")
        if requested in ADULT_MATURITY_CLASSES:
            if previous == "adult_aged_up_variant":
                maturity["classification_only_no_body_mutation"] = True
                maturity["exact_maturity_status"] = "confirmed_adult"
                maturity["presentation_variant_label"] = "adult_aged_up_variant"
                maturity["body_lane"] = "preserve_current_doll_safe_until_stage_two"
                maturity["replacement_strategy"] = "metadata_only_preserve_current_body"
                components = [component for component in components if component != "body"]
                instructions.append({
                    "area": "maturity",
                    "instruction": (
                        "Record the separate exact confirmed-adult classification and assign the complete "
                        "adult curriculum immediately. Preserve the current doll-safe body; do not queue "
                        "adult body or anatomy authoring until the resident's separate Stage 2 choice and "
                        "exact evidence pass."
                    ),
                })
            else:
                if candidate_id.strip().lower() == PETER_ADULT_ERA_CANDIDATE_ID or re.search(r"\b(?:he|him|male)\b", lowered):
                    maturity["body_lane"] = "adult_male"
                elif re.search(r"\b(?:she|her|female)\b", lowered):
                    maturity["body_lane"] = "adult_female"
                else:
                    maturity["body_lane"] = "confirmed_adult"
                body_selection_requested = "body" in components
                if previous in NON_ADULT_MATURITY_CLASSES and body_selection_requested:
                    maturity["classification_changed"] = True
                    maturity["replacement_strategy"] = "append_only_new_adult_body_build"
                    maturity["mutate_non_adult_body_in_place"] = False
                if body_selection_requested:
                    instructions.append({
                        "area": "maturity",
                        "instruction": (
                            f"Route the separately requested body build through the {maturity['body_lane']} lane "
                            "from Robert's logged exact-person classification and body instruction. Classification "
                            "is not visual or body approval."
                        ),
                    })
                else:
                    maturity["classification_only_no_body_mutation"] = True
                    maturity["replacement_strategy"] = "metadata_only_preserve_current_body"
                    instructions.append({
                        "area": "maturity",
                        "instruction": (
                            "Record the exact confirmed-adult classification without selecting, rebuilding, "
                            "or altering a body. Body/anatomy selection remains a separate instruction and gate."
                        ),
                    })

    age_progression: dict[str, Any] = {}
    if requested == "adult_aged_up_variant":
        maturity["presentation_variant_label"] = "adult_aged_up_variant"
        maturity["exact_maturity_status"] = "unresolved"
        maturity["body_lane"] = "doll_safe_non_anatomical"
        components = [component for component in components if component != "body"]
        components.append("body")
        stage_two_gate = dict(age_progression_stage_two_gate or {})
        stage_two_authorized = (
            stage_two_gate.get("status") == "passed"
            and stage_two_gate.get("adult_anatomy_allowed") is True
        )
        if stage_two_authorized:
            maturity["exact_maturity_status"] = "confirmed_adult"
            maturity["body_lane"] = "confirmed_adult"
            intents.append("age_progression_stage_2")
            age_progression = {
                "contract": "two_stage_spa_age_progression_v1",
                "separate_variant_required": True,
                "mutate_original_non_adult_body_in_place": False,
                "stage_1": {
                    "status": "passed_exact_evidence",
                    "adult_anatomy_allowed": False,
                },
                "stage_2": {
                    "status": "queued_private_inactive_unapproved",
                    "scope": "adult anatomy authoring on the separate confirmed adult variant",
                    "adult_anatomy_allowed": True,
                    "adult_classification_confirmed": True,
                    "exact_maturity_status": "confirmed_adult",
                    "presentation_variant_label": "adult_aged_up_variant",
                    "complete_adult_curriculum_assignment": "IMMEDIATE",
                    "confirmed_adult_classification_id": stage_two_gate.get(
                        "confirmed_adult_classification_id"
                    ),
                    "resident_adult_anatomy_choice_recorded": True,
                    "runtime_activation_allowed": False,
                },
                "stage_two_gate": stage_two_gate,
            }
            instructions.append({
                "area": "age_progression",
                "instruction": (
                    "Stage 2 only: exact Stage 1, confirmed-adult classification, spa eligibility, and the "
                    "resident's recorded adult-anatomy choice passed. Author adult anatomy on the separate "
                    "adult-aged variant; keep it private, inactive, unapproved, and leave the original "
                    "non-adult body unchanged."
                ),
            })
        else:
            intents.append("age_progression_stage_1")
            stage_one_eligibility_gate = dict(
                age_progression_stage_one_eligibility_gate or {}
            )
            age_progression = {
                "contract": "two_stage_spa_age_progression_v1",
                "separate_variant_required": True,
                "mutate_original_non_adult_body_in_place": False,
                "eligibility_required": {
                    "temporary_origin_verified": True,
                    "permanent_promotion_verified": True,
                    "multiple_prior_activations_verified": True,
                    "minimum_prior_activation_count": 2,
                    "resident_choice_recorded": True,
                    "spa_flow_recorded": True,
                },
                "stage_one_eligibility_gate": stage_one_eligibility_gate,
                "stage_1": {
                    "status": "queued_private_inactive",
                    "scope": (
                        "older/taller presentation derived from Age Progression, proportions, "
                        "rig fit, and an adult_aged_up_variant presentation/build label"
                    ),
                    "adult_anatomy_allowed": False,
                    "anatomy_must_remain_non_adult_safe": True,
                    "exact_maturity_status": "unresolved",
                    "doll_safe_non_anatomical_representation_required": True,
                    "complete_adult_curriculum_assigned": False,
                },
                "stage_2": {
                    "status": "blocked_until_stage_1_evidence_passes",
                    "scope": "adult anatomy authoring on the separate confirmed adult variant",
                    "adult_anatomy_allowed": False,
                },
            }
            instructions.append({
                "area": "age_progression",
                "instruction": (
                    "Stage 1 only: after the promotion, repeated-activation, resident-choice, and spa eligibility "
                    "gate passes, create a separate older/taller Age Progression variant and record only its "
                    "presentation/build label while it remains unresolved and doll-safe. Adult classification, "
                    "curriculum assignment, and adult anatomy remain separate later gates."
                ),
            })

    components = list(dict.fromkeys(components))
    intents = list(dict.fromkeys(intents))
    recognized = bool(components or continuity or maturity or age_progression)
    return {
        "recognized": recognized,
        "candidate_id": candidate_id,
        "components": components,
        "intents": intents,
        "instructions": instructions,
        "continuity": continuity,
        "maturity": maturity,
        "age_progression": age_progression,
    }


def append_correction_event(
    data: dict[str, Any],
    *,
    candidate_id: str,
    message: str,
    directives: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any] | None:
    """Append one hash-chained owner correction without editing older events."""

    if not directives.get("recognized"):
        return None
    events = data.setdefault("correction_memory_events", [])
    if not isinstance(events, list):
        raise ValueError("correction_memory_events_must_be_a_list")
    previous_hash = ""
    if events:
        previous_hash = str(events[-1].get("event_sha256") or "")
        if not SHA256_RE.fullmatch(previous_hash):
            raise ValueError("correction_memory_previous_event_hash_invalid")
    event: dict[str, Any] = {
        "schema_version": 1,
        "sequence": len(events) + 1,
        "recorded_at": recorded_at,
        "candidate_id": candidate_id,
        "speaker": "Robert",
        "source": "Avatar Builder Chat",
        "message": message.strip(),
        "previous_event_sha256": previous_hash,
        "directives": directives,
        "output_policy": {
            "visibility": "private_owner_review_only",
            "active": False,
            "assigned": False,
            "published": False,
            "owner_approved": False,
            "classification_correction_is_body_approval": False,
        },
    }
    event["event_sha256"] = _canonical_sha256(event)
    event["event_id"] = f"correction_{event['sequence']:06d}_{event['event_sha256'][:12]}"
    events.append(event)
    data["correction_memory_schema_version"] = 1
    return event


def route_next_private_build(data: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Set the current route pointer while the event log remains append-only."""

    directives = event.get("directives") if isinstance(event.get("directives"), dict) else {}
    components = list(directives.get("components") or [])
    maturity = directives.get("maturity") if isinstance(directives.get("maturity"), dict) else {}
    age_progression = (
        directives.get("age_progression")
        if isinstance(directives.get("age_progression"), dict)
        else {}
    )
    components = [component for component in COMPONENTS if component in set(components)]
    preserved = [component for component in COMPONENTS if component not in set(components)]
    route = {
        "schema_version": 1,
        "source_event_id": event["event_id"],
        "source_event_sha256": event["event_sha256"],
        "status": (
            "classification_recorded_no_body_build_queued"
            if maturity.get("classification_only_no_body_mutation") is True
            else "queued_private_inactive_unapproved"
        ),
        "components_to_rebuild": components,
        "components_to_preserve": preserved,
        "component_isolation_required": True,
        "body_lane": maturity.get("body_lane") or "preserve_current_maturity_lane",
        "replacement_strategy": maturity.get("replacement_strategy") or "append_only_corrected_candidate",
        "preserve_previous_candidate_revision": True,
        "superseded_candidate_deletion_allowed": False,
        "continuity": directives.get("continuity") or {},
        "age_progression": age_progression,
        "visibility": "private_owner_review_only",
        "runtime_activation_allowed": False,
        "assignment_allowed": False,
        "publication_allowed": False,
        "owner_approval_required": True,
        "classification_correction_is_body_approval": False,
    }
    if components == ["hair"]:
        route["hair_only_contract"] = {
            "detachable_component_only": True,
            "regenerate_body_face_eyes_skin_rig_weights_or_movement": False,
            "body_or_identity_revision_allowed": False,
        }
    data["next_private_build_route"] = route
    if age_progression:
        data["age_progression_contract"] = age_progression
    data["candidate_build_visibility"] = "private_owner_review_only"
    data["runtime_activation_allowed"] = False
    data["assignment_allowed"] = False
    data["publication_allowed"] = False
    data["owner_approval_required"] = True
    data["approval_status"] = "correction_queued_private_inactive_unapproved"
    return route


def verify_correction_event_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    previous_hash = ""
    for index, event in enumerate(events, start=1):
        if event.get("sequence") != index:
            failures.append(f"event_{index}_sequence_mismatch")
        if event.get("previous_event_sha256") != previous_hash:
            failures.append(f"event_{index}_previous_hash_mismatch")
        stored_hash = str(event.get("event_sha256") or "")
        payload = dict(event)
        payload.pop("event_id", None)
        payload.pop("event_sha256", None)
        computed_hash = _canonical_sha256(payload)
        if stored_hash != computed_hash:
            failures.append(f"event_{index}_content_hash_mismatch")
        expected_id = f"correction_{index:06d}_{stored_hash[:12]}"
        if event.get("event_id") != expected_id:
            failures.append(f"event_{index}_id_mismatch")
        previous_hash = stored_hash
    return {
        "schema_version": 1,
        "event_count": len(events),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "head_event_sha256": previous_hash,
    }


def evaluate_age_progression_stage_one_eligibility(
    eligibility_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed before an eligible promoted temporary starts Stage 1."""

    failures: list[str] = []
    if eligibility_evidence.get("status") != "passed":
        failures.append("spa_age_progression_eligibility_evidence_not_passed")
    if eligibility_evidence.get("temporary_origin_verified") is not True:
        failures.append("temporary_origin_not_verified")
    if eligibility_evidence.get("permanent_promotion_verified") is not True:
        failures.append("permanent_promotion_not_verified")
    activation_count = eligibility_evidence.get("prior_activation_count")
    if (
        isinstance(activation_count, bool)
        or not isinstance(activation_count, int)
        or activation_count < 2
    ):
        failures.append("multiple_prior_activations_not_exactly_verified")
    if eligibility_evidence.get("multiple_prior_activations_verified") is not True:
        failures.append("multiple_prior_activations_not_verified")
    if eligibility_evidence.get("resident_choice_recorded") is not True:
        failures.append("resident_age_progression_choice_not_recorded")
    if eligibility_evidence.get("spa_flow_recorded") is not True:
        failures.append("spa_flow_not_recorded")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "status": "blocked" if failures else "passed",
        "stage_one_allowed": not failures,
        "minimum_prior_activation_count": 2,
        "verified_facts": {
            "temporary_origin_verified": (
                eligibility_evidence.get("temporary_origin_verified") is True
            ),
            "permanent_promotion_verified": (
                eligibility_evidence.get("permanent_promotion_verified") is True
            ),
            "multiple_prior_activations_verified": (
                eligibility_evidence.get("multiple_prior_activations_verified") is True
            ),
            "prior_activation_count": (
                activation_count
                if isinstance(activation_count, int)
                and not isinstance(activation_count, bool)
                else None
            ),
            "resident_choice_recorded": (
                eligibility_evidence.get("resident_choice_recorded") is True
            ),
            "spa_flow_recorded": (
                eligibility_evidence.get("spa_flow_recorded") is True
            ),
        },
        "failures": failures,
        "adult_anatomy_allowed": False,
        "runtime_activation_allowed": False,
    }


def evaluate_age_progression_stage_two_gate(
    route: dict[str, Any],
    stage_one_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed before adding adult anatomy to an age-progressed variant."""

    age_progression = route.get("age_progression") if isinstance(route.get("age_progression"), dict) else {}
    eligibility = stage_one_evidence.get("eligibility") if isinstance(stage_one_evidence.get("eligibility"), dict) else {}
    failures: list[str] = []
    if age_progression.get("contract") != "two_stage_spa_age_progression_v1":
        failures.append("two_stage_age_progression_contract_missing")
    if stage_one_evidence.get("status") != "passed":
        failures.append("stage_one_evidence_not_passed")
    if stage_one_evidence.get("separate_variant") is not True:
        failures.append("age_progression_must_use_separate_variant")
    if stage_one_evidence.get("presentation_variant_label") != (
        "adult_aged_up_variant"
    ):
        failures.append("adult_aged_up_presentation_label_missing")
    if stage_one_evidence.get("exact_maturity_status_at_stage_one") != "unresolved":
        failures.append("stage_one_exact_maturity_must_be_unresolved")
    if stage_one_evidence.get("maturity_class") == "adult_aged_up_variant":
        failures.append("presentation_label_must_not_be_stored_as_maturity_class")
    classification = (
        stage_one_evidence.get("confirmed_adult_classification_evidence")
        if isinstance(
            stage_one_evidence.get("confirmed_adult_classification_evidence"), dict
        )
        else {}
    )
    variant_candidate_id = str(
        stage_one_evidence.get("variant_candidate_id") or ""
    ).strip()
    if not classification:
        failures.append("confirmed_adult_classification_evidence_missing")
    if not variant_candidate_id:
        failures.append("age_progression_variant_candidate_id_missing")
    if str(classification.get("classification_id") or "").strip() == "":
        failures.append("confirmed_adult_classification_id_missing")
    if (
        not variant_candidate_id
        or str(classification.get("subject_id") or "").strip().lower()
        != variant_candidate_id.lower()
    ):
        failures.append("confirmed_adult_classification_subject_mismatch")
    if classification.get("maturity_status") != "confirmed_adult":
        failures.append("confirmed_adult_maturity_status_missing")
    if classification.get("authority") != "Robert_explicit_owner_confirmation":
        failures.append("confirmed_adult_classification_authority_missing")
    if classification.get("offline_confirmation_allowed") is not True:
        failures.append("confirmed_adult_offline_authority_not_recorded")
    if classification.get("network_lookup_required") is not False:
        failures.append("confirmed_adult_network_independence_not_recorded")
    source_text = str(classification.get("source_text") or "")
    source_text_sha256 = str(
        classification.get("source_text_sha256") or ""
    ).strip().lower()
    if (
        source_text.strip() == ""
        or not SHA256_RE.fullmatch(source_text_sha256)
        or hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        != source_text_sha256
    ):
        failures.append("confirmed_adult_source_text_sha256_invalid")
    recorded_at = str(classification.get("recorded_at_utc") or "").strip()
    try:
        recorded = datetime.fromisoformat(
            recorded_at[:-1] + "+00:00" if recorded_at.endswith("Z") else recorded_at
        )
    except ValueError:
        recorded = None
    if recorded is None or recorded.tzinfo is None or recorded.utcoffset() is None:
        failures.append("confirmed_adult_recorded_at_utc_invalid")
    if stage_one_evidence.get("older_taller_presentation_verified") is not True:
        failures.append("older_taller_presentation_not_verified")
    if stage_one_evidence.get("adult_anatomy_absent") is not True:
        failures.append("stage_one_must_not_contain_adult_anatomy")
    if stage_one_evidence.get("resident_adult_anatomy_choice_recorded") is not True:
        failures.append("resident_stage_two_adult_anatomy_choice_not_recorded")
    digest = str(stage_one_evidence.get("artifact_sha256") or "").lower()
    if not SHA256_RE.fullmatch(digest):
        failures.append("stage_one_artifact_sha256_invalid")
    required_eligibility = (
        "temporary_origin_verified",
        "permanent_promotion_verified",
        "multiple_prior_activations_verified",
        "resident_choice_recorded",
        "spa_flow_recorded",
    )
    if eligibility.get("status") != "passed":
        failures.append("spa_age_progression_eligibility_status_not_passed")
    for field in required_eligibility:
        if eligibility.get(field) is not True:
            failures.append(f"{field}_missing")
    activation_count = eligibility.get("prior_activation_count")
    if (
        isinstance(activation_count, bool)
        or not isinstance(activation_count, int)
        or activation_count < 2
    ):
        failures.append("prior_activation_count_below_multiple")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": 1,
        "status": "blocked" if failures else "passed",
        "adult_anatomy_allowed": not failures,
        "presentation_variant_label": "adult_aged_up_variant",
        "exact_maturity_status": "confirmed_adult" if not failures else "unresolved",
        "confirmed_adult_classification_id": (
            str(classification.get("classification_id")) if not failures else None
        ),
        "stage_two_action": (
            "author_new_adult_anatomy_on_separate_inactive_variant"
            if not failures
            else "no_adult_anatomy_authoring"
        ),
        "failures": failures,
        "runtime_activation_allowed": False,
        "owner_approval_required_after_stage_two": True,
    }
