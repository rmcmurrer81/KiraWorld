"""Three-layer facade for deterministic Level-A body/life fixture evidence.

The facade keeps Avatar Builder hooks, Body Systems Runtime, and the
Person/World boundary independently hashed.  It never binds a body asset,
activates a person, supplies adult-classification evidence, authorizes an
external action, or writes a synthetic person's memory.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from Core.avatar_builder_level_a_hooks import (
    body_hooks_sha256,
    create_level_a_body_hooks,
    validate_level_a_body_hooks,
)
from Core.body_systems_level_a_runtime import (
    DOMAINS as BODY_DOMAINS,
    apply_body_system_event,
    body_systems_state_sha256,
    create_body_systems_fixture,
    validate_body_systems_state,
)
from Core.level_a_runtime_common import (
    CAPABILITY_LADDER,
    FIXTURE_KIND,
    LevelABoundaryError,
    LevelARuntimeError,
    LevelATransitionError,
    SHA256_RE,
    assert_level_a_capability_status,
    canonical_json,
    canonical_sha256,
    parse_utc,
    require_identifier,
    validate_event,
)
from Core.person_world_level_a_runtime import (
    DOMAINS as PERSON_WORLD_DOMAINS,
    apply_person_world_event,
    create_person_world_fixture,
    person_world_state_sha256,
    validate_person_world_state,
)


MODEL_ID = "level_a_body_life_fixture_bundle_v1"
LAYER_NAMES = frozenset(
    {"avatar_builder_hooks", "body_systems_runtime", "person_world_runtime"}
)
EVENT_LAYERS = frozenset({"body_systems_runtime", "person_world_runtime"})


def _layer_hashes(bundle: Mapping[str, Any]) -> dict[str, str]:
    layers = bundle["layers"]
    hooks = layers["avatar_builder_hooks"]
    return {
        "avatar_builder_hooks": body_hooks_sha256(hooks),
        "body_systems_runtime": body_systems_state_sha256(
            layers["body_systems_runtime"], hooks=hooks
        ),
        "person_world_runtime": person_world_state_sha256(
            layers["person_world_runtime"]
        ),
    }


def create_level_a_body_life_fixture(
    *, fixture_id: str, actor_fixture_ids: list[str], started_at_utc: str
) -> dict[str, Any]:
    fixture = require_identifier(fixture_id, "fixture_id")
    parse_utc(started_at_utc, "started_at_utc")
    hooks = create_level_a_body_hooks(fixture)
    bundle = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "fixture_id": fixture,
        "fixture_kind": FIXTURE_KIND,
        "started_at_utc": started_at_utc,
        "clock_utc": started_at_utc,
        "revision": 0,
        "seen_event_ids": [],
        "orchestration_log": [],
        "capability_ladder": list(CAPABILITY_LADDER),
        "capability_statuses": {
            "three_layer_contract": "NON_PERSON_FIXTURE_PASS",
            "deterministic_state_and_route_tests": "NON_PERSON_FIXTURE_PASS",
            "persistence_and_false_memory_tests": "NON_PERSON_FIXTURE_PASS",
            "body_hooks_verified": "NOT_IMPLEMENTED",
            "physiology_state_verified": "NOT_IMPLEMENTED",
            "person_decision_integrated": "NOT_IMPLEMENTED",
            "privacy_and_continuity_pass": "NOT_IMPLEMENTED",
            "owner_supervised_pass": "NOT_IMPLEMENTED",
            "generalization_pass": "NOT_IMPLEMENTED",
            "avatar_builder_method_promoted": "NOT_IMPLEMENTED",
        },
        "layers": {
            "avatar_builder_hooks": hooks,
            "body_systems_runtime": create_body_systems_fixture(
                fixture_id=fixture, hooks=hooks, started_at_utc=started_at_utc
            ),
            "person_world_runtime": create_person_world_fixture(
                fixture_id=fixture,
                actor_fixture_ids=actor_fixture_ids,
                started_at_utc=started_at_utc,
            ),
        },
        "integration": {
            "body_asset_binding": None,
            "active_person_ids": [],
            "exact_subject_bound_adult_evidence": {},
            "person_private_store_binding": None,
            "world_action_adapter_binding": None,
            "runtime_selector_binding": None,
        },
        "truth_boundary": {
            "body_hooks_verified": False,
            "physiology_verified": False,
            "person_decision_integrated": False,
            "person_privacy_integrated": False,
            "person_memory_written": False,
            "person_lived_experience_claimed": False,
            "external_action_authorized": False,
            "runtime_activated": False,
            "adult_body_or_person_used": False,
        },
    }
    validate_level_a_body_life_fixture(bundle)
    return bundle


def apply_level_a_fixture_event(
    bundle: Mapping[str, Any], *, layer: str, event: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_level_a_body_life_fixture(bundle)
    if layer not in EVENT_LAYERS:
        raise LevelABoundaryError(
            "Avatar Builder hooks are immutable in Level A; use a new fixture contract"
        )
    allowed_domains = BODY_DOMAINS if layer == "body_systems_runtime" else PERSON_WORLD_DOMAINS
    normalized = validate_event(
        event,
        allowed_domains=allowed_domains,
        prior_event_ids=set(current["seen_event_ids"]),
        current_clock_utc=current["clock_utc"],
    )
    before_hashes = _layer_hashes(current)
    updated = deepcopy(current)
    hooks = updated["layers"]["avatar_builder_hooks"]
    if layer == "body_systems_runtime":
        updated["layers"][layer] = apply_body_system_event(
            updated["layers"][layer], normalized, hooks=hooks
        )
    else:
        updated["layers"][layer] = apply_person_world_event(
            updated["layers"][layer], normalized
        )
    after_hashes = _layer_hashes(updated)
    untouched = sorted(LAYER_NAMES - {layer})
    for sibling in untouched:
        if before_hashes[sibling] != after_hashes[sibling]:
            raise LevelABoundaryError(f"event mutated sibling layer: {sibling}")
    updated["seen_event_ids"].append(normalized["event_id"])
    updated["revision"] += 1
    updated["clock_utc"] = normalized["at_utc"]
    updated["orchestration_log"].append(
        {
            "event_id": normalized["event_id"],
            "at_utc": normalized["at_utc"],
            "changed_layer": layer,
            "changed_layer_before_sha256": before_hashes[layer],
            "changed_layer_after_sha256": after_hashes[layer],
            "unchanged_sibling_sha256": {
                name: before_hashes[name] for name in untouched
            },
            "event_is_person_memory": False,
            "event_is_lived_experience": False,
            "external_action_performed": False,
        }
    )
    validate_level_a_body_life_fixture(updated)
    return updated


def validate_level_a_body_life_fixture(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise LevelARuntimeError("Level-A fixture bundle must be an object")
    if bundle.get("schema_version") != 1 or bundle.get("model_id") != MODEL_ID:
        raise LevelARuntimeError("Level-A fixture bundle identity drifted")
    fixture = require_identifier(bundle.get("fixture_id"), "fixture_id")
    if bundle.get("fixture_kind") != FIXTURE_KIND:
        raise LevelABoundaryError("bundle is not a Level-A non-person fixture")
    if tuple(bundle.get("capability_ladder", ())) != CAPABILITY_LADDER:
        raise LevelABoundaryError("capability ladder drifted")
    statuses = bundle.get("capability_statuses")
    if not isinstance(statuses, Mapping) or not statuses:
        raise LevelARuntimeError("capability status map is absent")
    for key, value in statuses.items():
        assert_level_a_capability_status(value, f"capability_statuses.{key}")
    started_at = parse_utc(bundle.get("started_at_utc"), "started_at_utc")
    clock = parse_utc(bundle.get("clock_utc"), "clock_utc")
    if clock < started_at:
        raise LevelATransitionError("bundle clock precedes fixture start")
    revision = bundle.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise LevelARuntimeError("bundle revision must be a nonnegative integer")
    seen = bundle.get("seen_event_ids")
    log = bundle.get("orchestration_log")
    if not isinstance(seen, list) or not isinstance(log, list):
        raise LevelARuntimeError("bundle event ledger is absent")
    if revision != len(seen) or len(seen) != len(log) or len(seen) != len(set(seen)):
        raise LevelATransitionError("bundle event ledger or revision drifted")
    if [row.get("event_id") for row in log] != seen:
        raise LevelATransitionError("bundle event ordering drifted")
    if any(
        row.get("event_is_person_memory") is not False
        or row.get("event_is_lived_experience") is not False
        or row.get("external_action_performed") is not False
        for row in log
    ):
        raise LevelABoundaryError("bundle audit evidence became person state or action")

    layers = bundle.get("layers")
    if not isinstance(layers, Mapping) or set(layers) != LAYER_NAMES:
        raise LevelARuntimeError("three exact runtime layers are required")
    hooks = validate_level_a_body_hooks(layers["avatar_builder_hooks"])
    body = validate_body_systems_state(layers["body_systems_runtime"], hooks=hooks)
    person_world = validate_person_world_state(layers["person_world_runtime"])
    if any(layer["fixture_id"] != fixture for layer in (hooks, body, person_world)):
        raise LevelABoundaryError("fixture identity differs across layers")

    initial_hooks = create_level_a_body_hooks(fixture)
    initial_body = create_body_systems_fixture(
        fixture_id=fixture,
        hooks=initial_hooks,
        started_at_utc=str(bundle["started_at_utc"]),
    )
    initial_person_world = create_person_world_fixture(
        fixture_id=fixture,
        actor_fixture_ids=list(person_world["actor_fixture_ids"]),
        started_at_utc=str(bundle["started_at_utc"]),
    )
    chain_hashes: dict[str, str] = {
        "avatar_builder_hooks": body_hooks_sha256(initial_hooks),
        "body_systems_runtime": body_systems_state_sha256(
            initial_body, hooks=initial_hooks
        ),
        "person_world_runtime": person_world_state_sha256(initial_person_world),
    }
    prior_time = None
    child_event_receipts = {
        "body_systems_runtime": {
            row["event_id"]: row for row in body["event_log"]
        },
        "person_world_runtime": {
            row["event_id"]: row for row in person_world["event_log"]
        },
    }
    body_ids = set(child_event_receipts["body_systems_runtime"])
    world_ids = set(child_event_receipts["person_world_runtime"])
    if body_ids.intersection(world_ids) or body_ids.union(world_ids) != set(seen):
        raise LevelATransitionError("bundle and child event inventories differ")
    exact_log_fields = {
        "event_id",
        "at_utc",
        "changed_layer",
        "changed_layer_before_sha256",
        "changed_layer_after_sha256",
        "unchanged_sibling_sha256",
        "event_is_person_memory",
        "event_is_lived_experience",
        "external_action_performed",
    }
    for index, row in enumerate(log):
        if not isinstance(row, Mapping) or set(row) != exact_log_fields:
            raise LevelATransitionError(f"orchestration receipt {index} fields drifted")
        changed = row.get("changed_layer")
        if changed not in EVENT_LAYERS:
            raise LevelATransitionError("orchestration log names an invalid changed layer")
        siblings = row.get("unchanged_sibling_sha256")
        if not isinstance(siblings, Mapping) or set(siblings) != LAYER_NAMES - {changed}:
            raise LevelATransitionError("orchestration sibling evidence drifted")
        before_hashes = dict(siblings)
        before_hashes[changed] = row.get("changed_layer_before_sha256")
        after_hash = row.get("changed_layer_after_sha256")
        for value in (*before_hashes.values(), after_hash):
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise LevelATransitionError("orchestration layer hash is invalid")
        for name in LAYER_NAMES:
            if name in chain_hashes and chain_hashes[name] != before_hashes[name]:
                raise LevelATransitionError(f"orchestration hash chain broke for {name}")
        if before_hashes[changed] == after_hash:
            raise LevelATransitionError("changed layer hash did not change")
        chain_hashes[changed] = after_hash
        receipt_time = parse_utc(row.get("at_utc"), f"orchestration_log[{index}].at_utc")
        if prior_time is not None and receipt_time < prior_time:
            raise LevelATransitionError("orchestration time moved backward")
        prior_time = receipt_time
        child_receipt = child_event_receipts[changed].get(row.get("event_id"))
        if child_receipt is None or child_receipt.get("at_utc") != row.get("at_utc"):
            raise LevelATransitionError("orchestration receipt and child event differ")
    if prior_time is not None and prior_time != parse_utc(bundle.get("clock_utc"), "clock_utc"):
        raise LevelATransitionError("orchestration final time and bundle clock differ")
    current_hashes = _layer_hashes(bundle)
    if chain_hashes != current_hashes:
        raise LevelATransitionError("orchestration hash chain does not reach current layers")

    integration = bundle.get("integration")
    if not isinstance(integration, Mapping):
        raise LevelABoundaryError("Level-A integration boundary is absent")
    if (
        integration.get("body_asset_binding") is not None
        or integration.get("active_person_ids") != []
        or integration.get("exact_subject_bound_adult_evidence") != {}
        or integration.get("person_private_store_binding") is not None
        or integration.get("world_action_adapter_binding") is not None
        or integration.get("runtime_selector_binding") is not None
    ):
        raise LevelABoundaryError("Level A crossed a body/person/world integration gate")
    truth = bundle.get("truth_boundary")
    if not isinstance(truth, Mapping) or not truth or any(value is not False for value in truth.values()):
        raise LevelABoundaryError("Level-A bundle crossed a false implementation claim")
    return deepcopy(dict(bundle))


def level_a_fixture_sha256(bundle: Mapping[str, Any]) -> str:
    return canonical_sha256(validate_level_a_body_life_fixture(bundle))


def serialize_level_a_fixture(bundle: Mapping[str, Any]) -> str:
    return canonical_json(validate_level_a_body_life_fixture(bundle))


def restore_level_a_fixture(serialized: str) -> dict[str, Any]:
    try:
        raw = json.loads(serialized)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LevelARuntimeError("serialized Level-A fixture is invalid JSON") from exc
    return validate_level_a_body_life_fixture(raw)
