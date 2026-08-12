"""Fail-closed validation and interest planning for notebook-world cells.

This module plans which *already authored and runtime-loadable* cells may be in
memory near one or more presences.  It never turns an unbuilt contract entry
into geometry and never promotes a cell's completion state.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ALLOWED_LOADABLE_STATES = {
    "prototype_owner_review_not_approved",
    "owner_approved_runtime_cell",
}

RESOURCE_BUDGET_KEYS = (
    "asset_bytes",
    "triangles",
    "texture_bytes",
    "draw_calls",
)


class CellStreamingContractError(ValueError):
    """Raised when a streaming contract could permit unsupported loading."""


@dataclass(frozen=True)
class InterestPlan:
    desired_cells: tuple[str, ...]
    load_cells: tuple[str, ...]
    retain_cells: tuple[str, ...]
    unload_cells: tuple[str, ...]
    nearby_blocked_cells: tuple[str, ...]

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "desired_cells": list(self.desired_cells),
            "load_cells": list(self.load_cells),
            "retain_cells": list(self.retain_cells),
            "unload_cells": list(self.unload_cells),
            "nearby_blocked_cells": list(self.nearby_blocked_cells),
        }


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CellStreamingContractError(f"Expected a finite number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise CellStreamingContractError(f"Expected a finite number, got {value!r}")
    return number


def _position(value: Sequence[Any], *, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise CellStreamingContractError(f"{label} must contain exactly three coordinates")
    return tuple(_finite_number(item) for item in value)  # type: ignore[return-value]


def _validated_bounds(cell: Mapping[str, Any]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    bounds = cell.get("bounds_m")
    if not isinstance(bounds, Mapping):
        raise CellStreamingContractError(f"Runtime-loadable cell {cell.get('id')!r} has no bounds_m")
    minimum = _position(bounds.get("min"), label=f"{cell.get('id')}.bounds_m.min")
    maximum = _position(bounds.get("max"), label=f"{cell.get('id')}.bounds_m.max")
    if any(low >= high for low, high in zip(minimum, maximum)):
        raise CellStreamingContractError(f"Cell {cell.get('id')!r} has empty or inverted bounds")
    return minimum, maximum


def validate_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("contract_kind") != "notebook_world_proximity_cell_streaming_contract":
        raise CellStreamingContractError("Unexpected cell-streaming contract kind")
    if contract.get("status") != "streaming_scaffold_only_not_complete":
        raise CellStreamingContractError("The Louvre streaming scaffold must remain explicitly incomplete")

    truth = contract.get("truth")
    if not isinstance(truth, Mapping):
        raise CellStreamingContractError("Missing truth block")
    forbidden_true = (
        "interior_complete",
        "working_doors_proven",
        "stairs_proven",
        "escalators_proven",
        "elevators_proven",
        "gallery_rooms_proven",
        "artwork_inventory_or_placement_proven",
    )
    promoted = [key for key in forbidden_true if truth.get(key) is not False]
    if promoted:
        raise CellStreamingContractError(f"Unsupported Louvre truth flags were promoted: {', '.join(promoted)}")

    policy = contract.get("streaming_policy")
    if not isinstance(policy, Mapping):
        raise CellStreamingContractError("Missing streaming_policy")
    load_radius = _finite_number(policy.get("load_radius_m"))
    retain_radius = _finite_number(policy.get("retain_radius_m"))
    if load_radius <= 0 or retain_radius <= load_radius:
        raise CellStreamingContractError("retain_radius_m must be greater than the positive load_radius_m")
    max_cells = policy.get("max_active_cells_per_presence")
    if isinstance(max_cells, bool) or not isinstance(max_cells, int) or not (1 <= max_cells <= 32):
        raise CellStreamingContractError("max_active_cells_per_presence must be an integer from 1 to 32")
    if policy.get("per_presence_interest_sets") is not True or policy.get("union_interest_sets_for_shared_world") is not True:
        raise CellStreamingContractError("Per-presence and shared-world union interest sets must be explicit")
    if policy.get("unload_hysteresis_required") is not True:
        raise CellStreamingContractError("Unload hysteresis must remain enabled")
    never_load = set(policy.get("never_load_build_states") or [])
    required_never_load = {"locked_unbuilt", "source_research_required_unbuilt", "owner_review_blocked"}
    if not required_never_load.issubset(never_load):
        raise CellStreamingContractError("The never-load build-state set is incomplete")
    transaction_order = policy.get("transaction_order")
    transaction_text = " ".join(str(item).lower() for item in transaction_order or [])
    if not isinstance(transaction_order, list) or "destination" not in transaction_text or "unload" not in transaction_text:
        raise CellStreamingContractError("The streaming policy must stage/validate destinations before source unload")

    resource_budgets = contract.get("resource_budgets")
    if not isinstance(resource_budgets, Mapping):
        raise CellStreamingContractError("Missing explicit resource_budgets")
    active_budget = resource_budgets.get("active_set")
    per_cell_budgets = resource_budgets.get("per_cell")
    if not isinstance(active_budget, Mapping) or not isinstance(per_cell_budgets, Mapping):
        raise CellStreamingContractError("Resource budgets require active_set and per_cell limits")
    for key in RESOURCE_BUDGET_KEYS:
        if _finite_number(active_budget.get(f"max_{key}")) < 0:
            raise CellStreamingContractError(f"Active-set max_{key} cannot be negative")
    if _finite_number(active_budget.get("max_transaction_latency_ms")) <= 0:
        raise CellStreamingContractError("Active-set transaction latency budget must be positive")

    cells = contract.get("cells")
    if not isinstance(cells, list) or not cells:
        raise CellStreamingContractError("Contract has no cells")
    ids: list[str] = []
    for cell in cells:
        if not isinstance(cell, Mapping):
            raise CellStreamingContractError("Each cell must be an object")
        cell_id = str(cell.get("id") or "")
        if not cell_id:
            raise CellStreamingContractError("A cell has no id")
        ids.append(cell_id)
        state = str(cell.get("build_state") or "")
        loadable = cell.get("runtime_loadable") is True
        completion = cell.get("completion")
        if not isinstance(completion, Mapping) or completion.get("complete") is not False:
            raise CellStreamingContractError(f"Cell {cell_id!r} is not explicitly incomplete")
        if loadable:
            if state not in ALLOWED_LOADABLE_STATES:
                raise CellStreamingContractError(f"Cell {cell_id!r} has a blocked build state but is runtime-loadable")
            _validated_bounds(cell)
            binding = cell.get("runtime_binding")
            if not isinstance(binding, Mapping) or not binding.get("source"):
                raise CellStreamingContractError(f"Cell {cell_id!r} has no runtime binding")
            budget = per_cell_budgets.get(cell_id)
            if not isinstance(budget, Mapping):
                raise CellStreamingContractError(f"Runtime-loadable cell {cell_id!r} has no per-cell resource budget")
            for key in RESOURCE_BUDGET_KEYS:
                value = _finite_number(budget.get(f"max_{key}"))
                if value < 0 or value > _finite_number(active_budget.get(f"max_{key}")):
                    raise CellStreamingContractError(f"Cell {cell_id!r} has an invalid max_{key} budget")
            if _finite_number(budget.get("max_stage_latency_ms")) <= 0:
                raise CellStreamingContractError(f"Cell {cell_id!r} stage latency budget must be positive")
        else:
            if state not in never_load:
                raise CellStreamingContractError(f"Non-loadable cell {cell_id!r} is not in a never-load state")
            if cell.get("runtime_binding") is not None:
                raise CellStreamingContractError(f"Unbuilt cell {cell_id!r} unexpectedly has a runtime binding")
            if cell.get("bounds_m") is not None:
                raise CellStreamingContractError(f"Unbuilt cell {cell_id!r} must not invent spatial bounds")
        anchor = cell.get("proximity_anchor_m")
        if anchor is not None:
            if not isinstance(anchor, Mapping) or not str(anchor.get("truth") or ""):
                raise CellStreamingContractError(f"Cell {cell_id!r} proximity anchor has no truth label")
            _position(anchor.get("position"), label=f"{cell_id}.proximity_anchor_m.position")

    if len(ids) != len(set(ids)):
        raise CellStreamingContractError("Cell ids are not unique")
    known = set(ids)
    for cell in cells:
        unknown = set(cell.get("adjacent_cells") or []) - known
        if unknown:
            raise CellStreamingContractError(f"Cell {cell['id']!r} references unknown adjacent cells: {sorted(unknown)}")
        activation_gate = cell.get("activation_gate")
        if activation_gate is not None:
            if not isinstance(activation_gate, Mapping) or activation_gate.get("kind") != "explicit_portal_authorization":
                raise CellStreamingContractError(f"Cell {cell['id']!r} has an unsupported activation gate")
            portal_cell = str(activation_gate.get("portal_cell") or "")
            if portal_cell not in known or portal_cell == cell["id"]:
                raise CellStreamingContractError(f"Cell {cell['id']!r} has an invalid portal authorization source")
            if activation_gate.get("authorization_expires_on_unload") is not True:
                raise CellStreamingContractError(f"Cell {cell['id']!r} portal authorization must expire on unload")

    portal_rules = contract.get("portal_rules")
    if not isinstance(portal_rules, Mapping):
        raise CellStreamingContractError("Missing portal_rules")
    for required_true in (
        "closed_or_unbuilt_portal_is_solid",
        "door_animation_does_not_prove_route_completion",
        "destination_cell_must_be_loaded_and_collision_ready_before_opening",
        "vertical_transport_requires_motion_collision_arrival_and_return_tests",
    ):
        if portal_rules.get(required_true) is not True:
            raise CellStreamingContractError(f"Portal rule {required_true!r} must be true")


def _distance_to_bounds(
    position: tuple[float, float, float],
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
) -> float:
    squared = 0.0
    for coordinate, low, high in zip(position, minimum, maximum):
        if coordinate < low:
            squared += (low - coordinate) ** 2
        elif coordinate > high:
            squared += (coordinate - high) ** 2
    return math.sqrt(squared)


def plan_interest(
    contract: Mapping[str, Any],
    positions: Iterable[Sequence[float]],
    *,
    currently_loaded: Iterable[str] = (),
    authorized_cells: Iterable[str] = (),
) -> InterestPlan:
    """Return a bounded load/retain/unload plan without loading any assets."""

    validate_contract(contract)
    points = tuple(_position(point, label="presence position") for point in positions)
    if not points:
        raise CellStreamingContractError("At least one physical presence/camera position is required")
    cells = {str(cell["id"]): cell for cell in contract["cells"]}
    loaded = set(currently_loaded)
    authorized = set(authorized_cells)
    unknown_loaded = loaded - set(cells)
    if unknown_loaded:
        raise CellStreamingContractError(f"Currently loaded set contains unknown cells: {sorted(unknown_loaded)}")
    unknown_authorized = authorized - set(cells)
    if unknown_authorized:
        raise CellStreamingContractError(f"Authorized set contains unknown cells: {sorted(unknown_authorized)}")

    policy = contract["streaming_policy"]
    load_radius = float(policy["load_radius_m"])
    retain_radius = float(policy["retain_radius_m"])
    notice_radius = float(policy["blocked_cell_notice_radius_m"])
    max_per_presence = int(policy["max_active_cells_per_presence"])

    distances: dict[str, float] = {}
    for cell_id, cell in cells.items():
        if cell["runtime_loadable"] is not True:
            continue
        if cell.get("activation_gate") is not None and cell_id not in authorized and cell_id not in loaded:
            continue
        minimum, maximum = _validated_bounds(cell)
        distances[cell_id] = min(_distance_to_bounds(point, minimum, maximum) for point in points)

    desired = [cell_id for cell_id, distance in distances.items() if distance <= load_radius]
    desired.sort(key=lambda cell_id: (distances[cell_id], cell_id))
    global_limit = max_per_presence * len(points)
    desired = desired[:global_limit]

    retained = sorted(
        cell_id
        for cell_id in loaded
        if cell_id in distances and distances[cell_id] <= retain_radius and cell_id not in desired
    )
    target = set(desired) | set(retained)
    to_load = sorted(target - loaded)
    to_unload = sorted(loaded - target)

    nearby_blocked: list[tuple[float, str]] = []
    for cell_id, cell in cells.items():
        if cell["runtime_loadable"] is True:
            continue
        anchor = cell.get("proximity_anchor_m")
        if not anchor:
            continue
        anchor_point = _position(anchor["position"], label=f"{cell_id} proximity anchor")
        distance = min(math.dist(point, anchor_point) for point in points)
        if distance <= notice_radius:
            nearby_blocked.append((distance, cell_id))
    nearby_blocked.sort()

    return InterestPlan(
        desired_cells=tuple(desired),
        load_cells=tuple(to_load),
        retain_cells=tuple(retained),
        unload_cells=tuple(to_unload),
        nearby_blocked_cells=tuple(cell_id for _distance, cell_id in nearby_blocked),
    )
