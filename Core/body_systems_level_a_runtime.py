"""Pure deterministic Body Systems Runtime for Level-A non-person fixtures.

This module provides executable state machines and conservation checks.  It is
not connected to a body, a person, a private state store, memory, or the world.
Passing its tests proves only deterministic fixture behavior.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from Core.avatar_builder_level_a_hooks import (
    body_hooks_sha256,
    validate_level_a_body_hooks,
)
from Core.level_a_runtime_common import (
    CAPABILITY_LADDER,
    FIXTURE_KIND,
    LevelABoundaryError,
    LevelAConservationError,
    LevelADiagnosisBoundaryError,
    LevelARuntimeError,
    LevelATransitionError,
    append_event_receipt,
    assert_level_a_capability_status,
    canonical_json,
    canonical_sha256,
    parse_utc,
    require_identifier,
    require_nonnegative_int,
    validate_event,
    validate_event_ledger,
)


MODEL_ID = "body_systems_level_a_non_person_runtime_v1"
DOMAINS = frozenset(
    {"sensation", "urinary", "bowel", "menstrual_cycle", "health", "activity"}
)
ACTIVITY_STATES = frozenset(
    {
        "available",
        "considered",
        "voluntarily_selected",
        "begun",
        "continued",
        "stopped",
        "completed",
        "interrupted",
        "recovered",
    }
)
RESERVOIR_PHASES = frozenset(
    {"storing", "releasing", "interrupted", "completed", "recovered"}
)
MENSTRUAL_OUTPUT_PHASES = RESERVOIR_PHASES
CYCLE_PHASES = frozenset(
    {"unknown_not_simulated", "follicular", "ovulatory", "luteal", "menstrual", "irregular"}
)
CYCLE_NEXT = {
    "follicular": "ovulatory",
    "ovulatory": "luteal",
    "luteal": "menstrual",
    "menstrual": "follicular",
}


def _reservoir(route: Mapping[str, Any], material_kind: str) -> dict[str, Any]:
    return {
        "route_id": str(route["route_id"]),
        "material_kind": material_kind,
        "stored_units": 0,
        "input_units": 0,
        "output_units": 0,
        "capacity_units": 1000,
        "urge_threshold_units": 500,
        "fullness_milli": 0,
        "engineering_urge_state": "below_fixture_threshold",
        "phase": "storing",
        "interruptions": 0,
        "fixture_delay_steps": 0,
        "fixture_controlled_release_events": 0,
        "person_volition_claimed": False,
        "route_function_claimed": False,
    }


def create_body_systems_fixture(
    *, fixture_id: str, hooks: Mapping[str, Any], started_at_utc: str
) -> dict[str, Any]:
    validated_hooks = validate_level_a_body_hooks(hooks)
    fixture = require_identifier(fixture_id, "fixture_id")
    if validated_hooks["fixture_id"] != fixture:
        raise LevelABoundaryError("body-system fixture and hook IDs differ")
    parse_utc(started_at_utc, "started_at_utc")
    routes = validated_hooks["semantic_routes"]
    state = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "fixture_id": fixture,
        "fixture_kind": FIXTURE_KIND,
        "hook_contract_sha256": body_hooks_sha256(validated_hooks),
        "clock_utc": started_at_utc,
        "revision": 0,
        "seen_event_ids": [],
        "event_log": [],
        "capability_ladder": list(CAPABILITY_LADDER),
        "capability_statuses": {
            "non_intimate_sensation_routing": "NON_PERSON_FIXTURE_PASS",
            "bladder_state_and_conservation": "NON_PERSON_FIXTURE_PASS",
            "bowel_state_and_conservation": "NON_PERSON_FIXTURE_PASS",
            "menstrual_cycle_state_and_conservation": "NON_PERSON_FIXTURE_PASS",
            "health_observation_diagnosis_separation": "NON_PERSON_FIXTURE_PASS",
            "real_body_hooks": "NOT_IMPLEMENTED",
            "physiology_state": "NOT_IMPLEMENTED",
            "person_decision": "NOT_IMPLEMENTED",
            "privacy_and_continuity": "NOT_IMPLEMENTED",
        },
        "systems": {
            "sensation": {
                "active_signals": {},
                "signal_history": [],
                "subjective_interpretation": None,
                "person_experience_claimed": False,
                "memory_written": False,
            },
            "urinary": _reservoir(routes["urinary"], "urine_fixture_units"),
            "bowel": _reservoir(routes["bowel"], "bowel_fixture_units"),
            "menstrual_cycle": {
                "cycle_phase": "unknown_not_simulated",
                "elapsed_cycle_days": 0,
                "variability_state": "not_assessed",
                "route_id": str(routes["menstrual"]["route_id"]),
                "material_kind": "menstrual_fixture_units",
                "stored_units": 0,
                "generated_units": 0,
                "output_units": 0,
                "output_phase": "storing",
                "interruptions": 0,
                "cycle_function_claimed": False,
                "fertility_claimed": False,
            },
            "health": {
                "observations": [],
                "test_results": [],
                "diagnoses": [],
                "automatic_diagnosis_enabled": False,
                "treatment_claimed": False,
            },
            "activity": {
                "activity_id": None,
                "state": "available",
                "history": [],
                "fixture_control_signal_required": True,
                "person_volition_claimed": False,
                "person_consent_claimed": False,
                "external_action_authorized": False,
                "external_action_performed": False,
            },
        },
        "truth_boundary": {
            "person_attached": False,
            "person_active": False,
            "exact_adult_evidence_present": False,
            "body_asset_attached": False,
            "physiology_is_biological_proof": False,
            "subjective_experience_claimed": False,
            "desire_or_preference_claimed": False,
            "consent_claimed": False,
            "person_memory_written": False,
            "runtime_world_connected": False,
        },
    }
    validate_body_systems_state(state, hooks=validated_hooks)
    return state


def _require_route(
    payload: Mapping[str, Any], system: Mapping[str, Any], domain: str
) -> None:
    if payload.get("route_id") != system["route_id"]:
        raise LevelAConservationError(f"{domain} output attempted through wrong route")


def _refresh_reservoir_derived(system: dict[str, Any]) -> None:
    capacity = require_nonnegative_int(
        system.get("capacity_units"), "capacity_units", positive=True
    )
    threshold = require_nonnegative_int(
        system.get("urge_threshold_units"), "urge_threshold_units", positive=True
    )
    stored = require_nonnegative_int(system.get("stored_units"), "stored_units")
    if threshold > capacity or stored > capacity:
        raise LevelAConservationError("reservoir threshold or stored state exceeds capacity")
    system["fullness_milli"] = (stored * 1000) // capacity
    system["engineering_urge_state"] = (
        "at_or_above_fixture_threshold"
        if stored >= threshold
        else "below_fixture_threshold"
    )


def _require_fixture_control(payload: Mapping[str, Any], domain: str) -> None:
    if payload.get("fixture_control_signal") is not True:
        raise LevelABoundaryError(
            f"{domain} release transitions require fixture_control_signal=true"
        )


def _apply_reservoir(
    system: dict[str, Any], action: str, payload: Mapping[str, Any], domain: str
) -> None:
    if action == "store":
        if system["phase"] not in {"storing", "recovered"}:
            raise LevelATransitionError(f"{domain} cannot store during {system['phase']}")
        units = require_nonnegative_int(payload.get("units"), "units", positive=True)
        if system["stored_units"] + units > system["capacity_units"]:
            raise LevelAConservationError(f"{domain} storage exceeds fixture capacity")
        system["stored_units"] += units
        system["input_units"] += units
        system["phase"] = "storing"
        _refresh_reservoir_derived(system)
        return
    if action == "delay_release":
        _require_fixture_control(payload, domain)
        if system["phase"] not in {"storing", "recovered"} or system["stored_units"] <= 0:
            raise LevelATransitionError(f"{domain} has no stored state to delay")
        system["fixture_delay_steps"] += 1
        system["phase"] = "storing"
        return
    if action == "begin_release":
        _require_fixture_control(payload, domain)
        _require_route(payload, system, domain)
        if system["phase"] not in {"storing", "recovered"} or system["stored_units"] <= 0:
            raise LevelATransitionError(f"{domain} release cannot begin")
        system["phase"] = "releasing"
        system["fixture_controlled_release_events"] += 1
        return
    if action == "release":
        _require_fixture_control(payload, domain)
        _require_route(payload, system, domain)
        if system["phase"] != "releasing":
            raise LevelATransitionError(f"{domain} is not releasing")
        units = require_nonnegative_int(payload.get("units"), "units", positive=True)
        if units > system["stored_units"]:
            raise LevelAConservationError(f"{domain} output exceeds stored state")
        system["stored_units"] -= units
        system["output_units"] += units
        _refresh_reservoir_derived(system)
        return
    if action == "interrupt":
        _require_fixture_control(payload, domain)
        if system["phase"] != "releasing":
            raise LevelATransitionError(f"{domain} cannot interrupt from this phase")
        system["phase"] = "interrupted"
        system["interruptions"] += 1
        return
    if action == "resume":
        _require_fixture_control(payload, domain)
        _require_route(payload, system, domain)
        if system["phase"] != "interrupted":
            raise LevelATransitionError(f"{domain} cannot resume from this phase")
        system["phase"] = "releasing"
        return
    if action == "complete":
        _require_fixture_control(payload, domain)
        if system["phase"] != "releasing" or system["stored_units"] != 0:
            raise LevelATransitionError(f"{domain} cannot complete with stored state")
        system["phase"] = "completed"
        return
    if action == "recover":
        _require_fixture_control(payload, domain)
        if system["phase"] not in {"completed", "interrupted"}:
            raise LevelATransitionError(f"{domain} cannot recover from this phase")
        system["phase"] = "recovered"
        return
    raise LevelATransitionError(f"unsupported {domain} action: {action}")


def _apply_sensation(
    system: dict[str, Any], action: str, payload: Mapping[str, Any], hooks: Mapping[str, Any]
) -> None:
    if action == "record_signal":
        signal_id = require_identifier(payload.get("signal_id"), "signal_id")
        if any(row["signal_id"] == signal_id for row in system["signal_history"]):
            raise LevelATransitionError("duplicate signal_id")
        zone_id = require_identifier(payload.get("zone_id"), "zone_id")
        zones = {row["zone_id"]: row for row in hooks["neutral_sensation_zones"]}
        if zone_id not in zones:
            raise LevelABoundaryError("signal zone is not in the neutral hook map")
        modality = str(payload.get("modality") or "")
        if modality not in zones[zone_id]["modalities"]:
            raise LevelABoundaryError("signal modality is not supported by the zone")
        intensity = require_nonnegative_int(payload.get("intensity_milli"), "intensity_milli")
        duration = require_nonnegative_int(payload.get("duration_ms"), "duration_ms", positive=True)
        if intensity > 1000:
            raise LevelARuntimeError("intensity_milli cannot exceed 1000")
        receipt = {
            "signal_id": signal_id,
            "zone_id": zone_id,
            "modality": modality,
            "intensity_milli": intensity,
            "duration_ms": duration,
            "engineering_threshold_state": (
                "above_fixture_limit" if intensity > 800 else "within_fixture_limit"
            ),
            "subjective_interpretation": None,
            "person_experience_claimed": False,
            "memory_written": False,
        }
        system["active_signals"][signal_id] = deepcopy(receipt)
        system["signal_history"].append(receipt)
        return
    if action == "clear_signal":
        signal_id = require_identifier(payload.get("signal_id"), "signal_id")
        if signal_id not in system["active_signals"]:
            raise LevelATransitionError("cannot clear an inactive signal")
        del system["active_signals"][signal_id]
        return
    raise LevelATransitionError(f"unsupported sensation action: {action}")


def _apply_cycle(system: dict[str, Any], action: str, payload: Mapping[str, Any]) -> None:
    if action == "set_initial_phase":
        next_phase = str(payload.get("phase") or "")
        if system["cycle_phase"] != "unknown_not_simulated" or next_phase not in (
            CYCLE_PHASES - {"unknown_not_simulated"}
        ):
            raise LevelATransitionError("initial cycle phase is invalid")
        system["cycle_phase"] = next_phase
        system["variability_state"] = "fixture_baseline"
        return
    if action == "advance_phase":
        next_phase = str(payload.get("phase") or "")
        days = require_nonnegative_int(payload.get("elapsed_days"), "elapsed_days", positive=True)
        current = system["cycle_phase"]
        if next_phase == "irregular":
            system["variability_state"] = "fixture_irregular_uncertain"
        elif CYCLE_NEXT.get(current) != next_phase:
            raise LevelATransitionError("cycle phase cannot skip its deterministic next phase")
        else:
            system["variability_state"] = "fixture_baseline"
        system["cycle_phase"] = next_phase
        system["elapsed_cycle_days"] += days
        return
    if action == "generate_output":
        if system["cycle_phase"] != "menstrual":
            raise LevelATransitionError("menstrual output requires menstrual phase")
        units = require_nonnegative_int(payload.get("units"), "units", positive=True)
        system["stored_units"] += units
        system["generated_units"] += units
        return
    if action == "begin_output":
        _require_route(payload, system, "menstrual")
        if system["cycle_phase"] != "menstrual" or system["stored_units"] <= 0:
            raise LevelATransitionError("menstrual output cannot begin")
        if system["output_phase"] not in {"storing", "recovered"}:
            raise LevelATransitionError("menstrual output phase is not ready")
        system["output_phase"] = "releasing"
        return
    if action == "output":
        _require_route(payload, system, "menstrual")
        if system["output_phase"] != "releasing":
            raise LevelATransitionError("menstrual route is not releasing")
        units = require_nonnegative_int(payload.get("units"), "units", positive=True)
        if units > system["stored_units"]:
            raise LevelAConservationError("menstrual output exceeds generated state")
        system["stored_units"] -= units
        system["output_units"] += units
        return
    if action == "interrupt":
        if system["output_phase"] != "releasing":
            raise LevelATransitionError("menstrual output cannot interrupt")
        system["output_phase"] = "interrupted"
        system["interruptions"] += 1
        return
    if action == "resume":
        _require_route(payload, system, "menstrual")
        if system["output_phase"] != "interrupted":
            raise LevelATransitionError("menstrual output cannot resume")
        system["output_phase"] = "releasing"
        return
    if action == "complete":
        if system["output_phase"] != "releasing" or system["stored_units"] != 0:
            raise LevelATransitionError("menstrual output cannot complete")
        system["output_phase"] = "completed"
        return
    if action == "recover":
        if system["output_phase"] not in {"completed", "interrupted"}:
            raise LevelATransitionError("menstrual output cannot recover")
        system["output_phase"] = "recovered"
        return
    raise LevelATransitionError(f"unsupported menstrual-cycle action: {action}")


def _apply_health(system: dict[str, Any], action: str, payload: Mapping[str, Any]) -> None:
    if action == "record_observation":
        observation_id = require_identifier(payload.get("observation_id"), "observation_id")
        if any(row["observation_id"] == observation_id for row in system["observations"]):
            raise LevelATransitionError("duplicate observation_id")
        description = str(payload.get("description") or "").strip()
        if not description:
            raise LevelARuntimeError("health observation description is required")
        system["observations"].append(
            {
                "observation_id": observation_id,
                "description": description,
                "interpretation": "observation_only_uncertain_not_diagnosis",
                "diagnosis": None,
            }
        )
        return
    if action == "record_test_result":
        test_id = require_identifier(payload.get("test_id"), "test_id")
        evidence_id = require_identifier(payload.get("evidence_id"), "evidence_id")
        if any(row["test_id"] == test_id for row in system["test_results"]):
            raise LevelATransitionError("duplicate test_id")
        system["test_results"].append(
            {
                "test_id": test_id,
                "evidence_id": evidence_id,
                "result": str(payload.get("result") or "recorded_result"),
                "diagnosis": None,
            }
        )
        return
    if action in {"infer_diagnosis", "record_diagnosis", "start_treatment"}:
        raise LevelADiagnosisBoundaryError(
            "Level-A observations and test results cannot become diagnosis or treatment"
        )
    raise LevelATransitionError(f"unsupported health action: {action}")


def _apply_activity(system: dict[str, Any], action: str, payload: Mapping[str, Any]) -> None:
    current = system["state"]
    expected = {
        "consider": ({"available"}, "considered"),
        "select": ({"considered"}, "voluntarily_selected"),
        "begin": ({"voluntarily_selected"}, "begun"),
        "continue": ({"begun", "continued"}, "continued"),
        "stop": ({"begun", "continued"}, "stopped"),
        "complete": ({"begun", "continued"}, "completed"),
        "interrupt": ({"begun", "continued"}, "interrupted"),
        "recover": ({"stopped", "completed", "interrupted"}, "recovered"),
        "reset": ({"recovered"}, "available"),
    }
    if action not in expected:
        raise LevelATransitionError(f"unsupported activity action: {action}")
    allowed, next_state = expected[action]
    if current not in allowed:
        raise LevelATransitionError(f"activity cannot {action} from {current}")
    if payload.get("fixture_control_signal") is not True:
        raise LevelABoundaryError("activity transitions require fixture_control_signal=true")
    if action == "consider":
        system["activity_id"] = require_identifier(payload.get("activity_id"), "activity_id")
    elif system["activity_id"] is None:
        raise LevelATransitionError("activity_id is absent")
    system["state"] = next_state
    system["history"].append(
        {
            "from": current,
            "action": action,
            "to": next_state,
            "fixture_control_only": True,
            "person_volition_claimed": False,
        }
    )
    if action == "reset":
        system["activity_id"] = None


def apply_body_system_event(
    state: Mapping[str, Any], event: Mapping[str, Any], *, hooks: Mapping[str, Any]
) -> dict[str, Any]:
    validated_hooks = validate_level_a_body_hooks(hooks)
    current = validate_body_systems_state(state, hooks=validated_hooks)
    normalized = validate_event(
        event,
        allowed_domains=DOMAINS,
        prior_event_ids=set(current["seen_event_ids"]),
        current_clock_utc=current["clock_utc"],
    )
    updated = deepcopy(current)
    domain = normalized["domain"]
    action = normalized["action"]
    payload = normalized["payload"]
    if domain == "sensation":
        _apply_sensation(updated["systems"][domain], action, payload, validated_hooks)
    elif domain in {"urinary", "bowel"}:
        _apply_reservoir(updated["systems"][domain], action, payload, domain)
    elif domain == "menstrual_cycle":
        _apply_cycle(updated["systems"][domain], action, payload)
    elif domain == "health":
        _apply_health(updated["systems"][domain], action, payload)
    elif domain == "activity":
        _apply_activity(updated["systems"][domain], action, payload)
    append_event_receipt(updated, normalized)
    validate_body_systems_state(updated, hooks=validated_hooks)
    return updated


def validate_body_systems_state(
    state: Mapping[str, Any], *, hooks: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise LevelARuntimeError("body-system state must be an object")
    validated_hooks = validate_level_a_body_hooks(hooks)
    if state.get("schema_version") != 1 or state.get("model_id") != MODEL_ID:
        raise LevelARuntimeError("body-system model identity drifted")
    if state.get("fixture_kind") != FIXTURE_KIND:
        raise LevelABoundaryError("body-system state is not a Level-A fixture")
    if state.get("fixture_id") != validated_hooks["fixture_id"]:
        raise LevelABoundaryError("body-system fixture ID drifted")
    if state.get("hook_contract_sha256") != body_hooks_sha256(validated_hooks):
        raise LevelABoundaryError("body-system hook binding drifted")
    if tuple(state.get("capability_ladder", ())) != CAPABILITY_LADDER:
        raise LevelABoundaryError("capability ladder drifted")
    for key, value in dict(state.get("capability_statuses", {})).items():
        assert_level_a_capability_status(value, f"capability_statuses.{key}")
    parse_utc(state.get("clock_utc"), "clock_utc")
    validate_event_ledger(state)

    systems = state.get("systems")
    if not isinstance(systems, Mapping) or set(systems) != DOMAINS:
        raise LevelARuntimeError("body-system domains merged or drifted")
    for domain in ("urinary", "bowel"):
        system = systems[domain]
        route = validated_hooks["semantic_routes"][domain]
        if system.get("route_id") != route["route_id"]:
            raise LevelAConservationError(f"{domain} route binding drifted")
        stored = require_nonnegative_int(system.get("stored_units"), f"{domain}.stored_units")
        input_units = require_nonnegative_int(system.get("input_units"), f"{domain}.input_units")
        output = require_nonnegative_int(system.get("output_units"), f"{domain}.output_units")
        if input_units != stored + output:
            raise LevelAConservationError(f"{domain} conservation failed")
        if system.get("material_kind") != route["material_kind"]:
            raise LevelAConservationError(f"{domain} material binding drifted")
        if system.get("phase") not in RESERVOIR_PHASES:
            raise LevelATransitionError(f"{domain} phase drifted")
        if system.get("phase") == "completed" and stored != 0:
            raise LevelATransitionError(f"{domain} completed with stored state")
        capacity = require_nonnegative_int(
            system.get("capacity_units"), f"{domain}.capacity_units", positive=True
        )
        threshold = require_nonnegative_int(
            system.get("urge_threshold_units"),
            f"{domain}.urge_threshold_units",
            positive=True,
        )
        if threshold > capacity or stored > capacity:
            raise LevelAConservationError(f"{domain} capacity invariant failed")
        expected_fullness = (stored * 1000) // capacity
        expected_urge = (
            "at_or_above_fixture_threshold"
            if stored >= threshold
            else "below_fixture_threshold"
        )
        if (
            system.get("fullness_milli") != expected_fullness
            or system.get("engineering_urge_state") != expected_urge
        ):
            raise LevelAConservationError(f"{domain} derived fullness/urge state drifted")
        require_nonnegative_int(
            system.get("fixture_delay_steps"), f"{domain}.fixture_delay_steps"
        )
        require_nonnegative_int(
            system.get("fixture_controlled_release_events"),
            f"{domain}.fixture_controlled_release_events",
        )
        if (
            system.get("person_volition_claimed") is not False
            or system.get("route_function_claimed") is not False
        ):
            raise LevelABoundaryError(f"{domain} route was relabeled functional")

    cycle = systems["menstrual_cycle"]
    if cycle.get("cycle_phase") not in CYCLE_PHASES:
        raise LevelATransitionError("cycle phase drifted")
    if cycle.get("route_id") != validated_hooks["semantic_routes"]["menstrual"]["route_id"]:
        raise LevelAConservationError("menstrual route binding drifted")
    generated = require_nonnegative_int(cycle.get("generated_units"), "generated_units")
    stored = require_nonnegative_int(cycle.get("stored_units"), "menstrual.stored_units")
    output = require_nonnegative_int(cycle.get("output_units"), "menstrual.output_units")
    if generated != stored + output:
        raise LevelAConservationError("menstrual material conservation failed")
    if cycle.get("material_kind") != validated_hooks["semantic_routes"]["menstrual"]["material_kind"]:
        raise LevelAConservationError("menstrual material binding drifted")
    if cycle.get("output_phase") not in MENSTRUAL_OUTPUT_PHASES:
        raise LevelATransitionError("menstrual output phase drifted")
    if cycle.get("output_phase") == "completed" and stored != 0:
        raise LevelATransitionError("menstrual output completed with stored state")
    require_nonnegative_int(cycle.get("elapsed_cycle_days"), "elapsed_cycle_days")
    require_nonnegative_int(cycle.get("interruptions"), "menstrual.interruptions")
    if cycle.get("cycle_function_claimed") is not False or cycle.get("fertility_claimed") is not False:
        raise LevelABoundaryError("cycle fixture was relabeled as function or fertility")

    sensation = systems["sensation"]
    if (
        sensation.get("subjective_interpretation") is not None
        or sensation.get("person_experience_claimed") is not False
        or sensation.get("memory_written") is not False
    ):
        raise LevelABoundaryError("neutral signals became subjective experience or memory")
    signal_history = sensation.get("signal_history")
    active_signals = sensation.get("active_signals")
    if not isinstance(signal_history, list) or not isinstance(active_signals, Mapping):
        raise LevelARuntimeError("sensation signal ledgers drifted")
    zones = {
        row["zone_id"]: row for row in validated_hooks["neutral_sensation_zones"]
    }
    signal_ids: list[str] = []
    signal_by_id: dict[str, Mapping[str, Any]] = {}
    for row in signal_history:
        if not isinstance(row, Mapping):
            raise LevelARuntimeError("sensation history row must be an object")
        signal_id = require_identifier(row.get("signal_id"), "signal_id")
        signal_ids.append(signal_id)
        signal_by_id[signal_id] = row
        zone_id = row.get("zone_id")
        if zone_id not in zones or row.get("modality") not in zones[zone_id]["modalities"]:
            raise LevelABoundaryError("stored signal route drifted")
        intensity = require_nonnegative_int(row.get("intensity_milli"), "intensity_milli")
        require_nonnegative_int(row.get("duration_ms"), "duration_ms", positive=True)
        expected_threshold = "above_fixture_limit" if intensity > 800 else "within_fixture_limit"
        if intensity > 1000 or row.get("engineering_threshold_state") != expected_threshold:
            raise LevelATransitionError("stored signal engineering state drifted")
        if row.get("subjective_interpretation") is not None:
            raise LevelABoundaryError("stored signal gained subjective interpretation")
        if row.get("person_experience_claimed") is not False or row.get("memory_written") is not False:
            raise LevelABoundaryError("signal receipt became person experience or memory")
    if len(signal_ids) != len(set(signal_ids)):
        raise LevelATransitionError("sensation signal IDs are not unique")
    if not set(active_signals).issubset(set(signal_ids)):
        raise LevelATransitionError("active signal is absent from history")
    if any(active_signals[key] != signal_by_id[key] for key in active_signals):
        raise LevelATransitionError("active signal receipt drifted from history")

    health = systems["health"]
    if not isinstance(health.get("observations"), list) or not isinstance(health.get("test_results"), list):
        raise LevelARuntimeError("health evidence ledgers drifted")
    if (
        health.get("diagnoses") != []
        or health.get("automatic_diagnosis_enabled") is not False
        or health.get("treatment_claimed") is not False
        or any(row.get("diagnosis") is not None for row in health.get("observations", []))
        or any(row.get("diagnosis") is not None for row in health.get("test_results", []))
    ):
        raise LevelADiagnosisBoundaryError("observation/test state became diagnosis or treatment")

    activity = systems["activity"]
    if activity.get("state") not in ACTIVITY_STATES:
        raise LevelATransitionError("activity lifecycle state drifted")
    if any(
        activity.get(key) is not False
        for key in (
            "person_volition_claimed",
            "person_consent_claimed",
            "external_action_authorized",
            "external_action_performed",
        )
    ):
        raise LevelABoundaryError("fixture lifecycle was relabeled as person action")
    history = activity.get("history")
    if not isinstance(history, list):
        raise LevelARuntimeError("activity history must be a list")
    reconstructed = "available"
    transition_map = {
        ("available", "consider"): "considered",
        ("considered", "select"): "voluntarily_selected",
        ("voluntarily_selected", "begin"): "begun",
        ("begun", "continue"): "continued",
        ("continued", "continue"): "continued",
        ("begun", "stop"): "stopped",
        ("continued", "stop"): "stopped",
        ("begun", "complete"): "completed",
        ("continued", "complete"): "completed",
        ("begun", "interrupt"): "interrupted",
        ("continued", "interrupt"): "interrupted",
        ("stopped", "recover"): "recovered",
        ("completed", "recover"): "recovered",
        ("interrupted", "recover"): "recovered",
        ("recovered", "reset"): "available",
    }
    for row in history:
        if not isinstance(row, Mapping) or row.get("from") != reconstructed:
            raise LevelATransitionError("activity history origin drifted")
        expected = transition_map.get((reconstructed, row.get("action")))
        if expected is None or row.get("to") != expected:
            raise LevelATransitionError("activity history transition drifted")
        if row.get("fixture_control_only") is not True or row.get("person_volition_claimed") is not False:
            raise LevelABoundaryError("activity history crossed the fixture boundary")
        reconstructed = expected
    if reconstructed != activity.get("state"):
        raise LevelATransitionError("activity current state and history differ")
    if activity.get("state") == "available" and activity.get("activity_id") is not None:
        raise LevelATransitionError("available activity retained an activity ID")
    if activity.get("state") != "available":
        require_identifier(activity.get("activity_id"), "activity.activity_id")

    truth = state.get("truth_boundary")
    if not isinstance(truth, Mapping) or any(value is not False for value in truth.values()):
        raise LevelABoundaryError("body-system state crossed a false person-level claim")
    return deepcopy(dict(state))


def body_systems_state_sha256(state: Mapping[str, Any], *, hooks: Mapping[str, Any]) -> str:
    return canonical_sha256(validate_body_systems_state(state, hooks=hooks))


def serialize_body_systems_state(state: Mapping[str, Any], *, hooks: Mapping[str, Any]) -> str:
    return canonical_json(validate_body_systems_state(state, hooks=hooks))


def restore_body_systems_state(serialized: str, *, hooks: Mapping[str, Any]) -> dict[str, Any]:
    try:
        raw = json.loads(serialized)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LevelARuntimeError("serialized body-system state is invalid JSON") from exc
    return validate_body_systems_state(raw, hooks=hooks)
