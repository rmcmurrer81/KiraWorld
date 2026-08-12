"""Avatar Builder hook contract for neutral Level-A non-person fixtures.

The hook map owns only semantic locations and route attachment names.  It has
no mesh, person identity, private coordinates, physiology, preference, memory,
or consent authority.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from Core.level_a_runtime_common import (
    FIXTURE_KIND,
    LevelABoundaryError,
    LevelARuntimeError,
    assert_level_a_capability_status,
    canonical_sha256,
    require_identifier,
)


HOOK_CONTRACT_ID = "avatar_builder_level_a_body_hooks_v1"

NEUTRAL_ZONES = (
    {
        "zone_id": "left_forearm_surface",
        "modalities": ["touch", "pressure", "temperature"],
        "intimate": False,
    },
    {
        "zone_id": "right_palm_surface",
        "modalities": ["touch", "pressure", "temperature"],
        "intimate": False,
    },
    {
        "zone_id": "upper_back_surface",
        "modalities": ["touch", "pressure", "temperature"],
        "intimate": False,
    },
    {
        "zone_id": "abdomen_surface",
        "modalities": ["touch", "pressure", "temperature"],
        "intimate": False,
    },
    {
        "zone_id": "left_foot_sole",
        "modalities": ["touch", "pressure", "temperature"],
        "intimate": False,
    },
)

ROUTES = {
    "urinary": {
        "route_id": "level_a_urinary_route",
        "material_kind": "urine_fixture_units",
        "ordered_nodes": ["bladder_fixture_store", "urinary_fixture_outlet"],
        "external_endpoint": "urinary_fixture_outlet",
    },
    "bowel": {
        "route_id": "level_a_bowel_route",
        "material_kind": "bowel_fixture_units",
        "ordered_nodes": ["bowel_fixture_store", "bowel_fixture_outlet"],
        "external_endpoint": "bowel_fixture_outlet",
    },
    "menstrual": {
        "route_id": "level_a_menstrual_route",
        "material_kind": "menstrual_fixture_units",
        "ordered_nodes": ["uterine_fixture_store", "menstrual_fixture_outlet"],
        "external_endpoint": "menstrual_fixture_outlet",
    },
}


def create_level_a_body_hooks(fixture_id: str) -> dict[str, Any]:
    fixture = require_identifier(fixture_id, "fixture_id")
    hooks = {
        "schema_version": 1,
        "hook_contract_id": HOOK_CONTRACT_ID,
        "fixture_id": fixture,
        "fixture_kind": FIXTURE_KIND,
        "capability_statuses": {
            "neutral_sensation_zone_schema": "NON_PERSON_FIXTURE_PASS",
            "semantic_route_attachment_schema": "NON_PERSON_FIXTURE_PASS",
            "exact_body_landmark_binding": "NOT_IMPLEMENTED",
            "internal_geometry_binding": "NOT_IMPLEMENTED",
            "person_body_adapter": "NOT_IMPLEMENTED",
        },
        "neutral_sensation_zones": deepcopy(list(NEUTRAL_ZONES)),
        "semantic_routes": deepcopy(ROUTES),
        "body_asset_binding": None,
        "private_geometry_or_identity_payload": None,
        "truth_boundary": {
            "body_hooks_verified": False,
            "mesh_connected": False,
            "internal_geometry_exists": False,
            "route_patency_or_flow_proven": False,
            "physiology_implemented": False,
            "person_attached": False,
            "subjective_experience_claimed": False,
        },
    }
    validate_level_a_body_hooks(hooks)
    return hooks


def validate_level_a_body_hooks(hooks: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(hooks, Mapping):
        raise LevelARuntimeError("body hooks must be an object")
    if hooks.get("schema_version") != 1 or hooks.get("hook_contract_id") != HOOK_CONTRACT_ID:
        raise LevelARuntimeError("Level-A body-hook identity drifted")
    require_identifier(hooks.get("fixture_id"), "fixture_id")
    if hooks.get("fixture_kind") != FIXTURE_KIND:
        raise LevelABoundaryError("body hooks are not a non-person fixture")
    for key, value in dict(hooks.get("capability_statuses", {})).items():
        assert_level_a_capability_status(value, f"capability_statuses.{key}")

    zones = hooks.get("neutral_sensation_zones")
    if not isinstance(zones, list) or not zones:
        raise LevelARuntimeError("neutral sensation zones are required")
    zone_ids: list[str] = []
    for zone in zones:
        if not isinstance(zone, Mapping):
            raise LevelARuntimeError("sensation zone must be an object")
        zone_id = require_identifier(zone.get("zone_id"), "zone_id")
        zone_ids.append(zone_id)
        if zone.get("intimate") is not False:
            raise LevelABoundaryError("Level-A sensation zones must be non-intimate")
        modalities = zone.get("modalities")
        if not isinstance(modalities, list) or not modalities:
            raise LevelARuntimeError("sensation-zone modalities are required")
        if not set(modalities).issubset({"touch", "pressure", "temperature"}):
            raise LevelABoundaryError("unsupported or subjective sensation modality")
    if len(zone_ids) != len(set(zone_ids)):
        raise LevelARuntimeError("sensation zone IDs must be unique")

    routes = hooks.get("semantic_routes")
    if not isinstance(routes, Mapping) or set(routes) != set(ROUTES):
        raise LevelARuntimeError("exact urinary, bowel, and menstrual routes are required")
    endpoints: list[str] = []
    all_nodes: dict[str, set[str]] = {}
    for domain, route in routes.items():
        if not isinstance(route, Mapping):
            raise LevelARuntimeError(f"{domain} route must be an object")
        nodes = [require_identifier(value, f"{domain}.ordered_nodes") for value in route.get("ordered_nodes", [])]
        if len(nodes) < 2 or route.get("external_endpoint") != nodes[-1]:
            raise LevelARuntimeError(f"{domain} route endpoint drifted")
        if route.get("route_id") != ROUTES[domain]["route_id"]:
            raise LevelARuntimeError(f"{domain} route ID drifted")
        if route.get("material_kind") != ROUTES[domain]["material_kind"]:
            raise LevelARuntimeError(f"{domain} material kind drifted")
        endpoints.append(str(route["external_endpoint"]))
        all_nodes[domain] = set(nodes)
    if len(endpoints) != len(set(endpoints)):
        raise LevelABoundaryError("fixture route endpoints must remain disjoint")
    route_names = sorted(all_nodes)
    for index, left in enumerate(route_names):
        for right in route_names[index + 1 :]:
            if all_nodes[left].intersection(all_nodes[right]):
                raise LevelABoundaryError(f"{left} and {right} routes merged")

    if hooks.get("body_asset_binding") is not None:
        raise LevelABoundaryError("Level-A hooks cannot bind a real body asset")
    if hooks.get("private_geometry_or_identity_payload") is not None:
        raise LevelABoundaryError("Level-A hooks cannot contain private geometry")
    truth = hooks.get("truth_boundary", {})
    if any(value is not False for value in truth.values()):
        raise LevelABoundaryError("Level-A body hooks crossed a false truth boundary")
    return deepcopy(dict(hooks))


def body_hooks_sha256(hooks: Mapping[str, Any]) -> str:
    return canonical_sha256(validate_level_a_body_hooks(hooks))

