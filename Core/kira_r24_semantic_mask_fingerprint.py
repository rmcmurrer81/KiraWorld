"""Deterministic semantic fingerprints for the R24 patch-mask evidence.

The Blender workers record a geometric ``t`` coordinate in every vertex-mask
record.  It can vary by tiny amounts between equivalent runs, but it also drives
``feature_offset_and_tags`` and Gaussian relief.  This module therefore keeps
``t`` outside the exact semantic hash while enforcing exact aligned identities,
no duplicate identities, and a tight maximum absolute-delta gate.

The accepted semantic surface is exact: vertex identities, graph rings, mask
membership and counts, edge sets, severe-subset bindings and gates, overlap
records, and ``u`` are all retained in a canonical projection.  The only fields
excluded from that projection are schema-declared full ``canonical_sha256``
diagnostics and ``t``; unknown fields fail closed at every mapping level.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence


SEMANTIC_SCHEMA = "kira.avatar.r24.semantic_mask_fingerprint.v1"
INHERITED_MAX_ABSOLUTE_T_DELTA = 2.2652149999635718e-06
MAX_ABSOLUTE_T_DELTA = 2.5e-06
MASK_FIELDS = frozenset(
    {
        "edge_masks",
        "vertex_masks",
        "severe_subset_bindings",
        "severe_subset_gates",
        "allowed_overlaps",
        "observed_overlaps",
        "unexpected_overlap_count",
        "canonical_sha256",
    }
)
VERTEX_MASK_NAMES = frozenset(
    {
        "BOUNDARY_ZERO",
        "ALL_RING1_SEAM_SUPPORTS",
        "SEVERE_RING1_SUPPORTS",
        "SEAM_CONTINUATION_RING2",
        "CENTRAL_POSITIVE_RELIEF",
        "FROZEN_COMPONENT_REMAINDER",
    }
)
EDGE_MASK_NAMES = frozenset(
    {"SUPERIOR_JOIN_EDGES", "SEVERE_FLANK_EDGES", "REGULAR_FLANK_EDGES"}
)
VERTEX_MASK_FIELDS = frozenset({"name", "count", "canonical_sha256", "records"})
VERTEX_RECORD_FIELDS = frozenset(
    {
        "vertex_index_before_final_reindex",
        "canonical_original_id",
        "graph_ring",
        "u",
        "t",
    }
)
EDGE_MASK_FIELDS = frozenset({"count", "canonical_sha256", "records"})
BINDING_FIELDS = frozenset(
    {
        "seam_edge",
        "support_vertex_index_before_final_reindex",
        "support_canonical_id",
        "support_source_endpoint_ids",
    }
)
GATE_FIELDS = frozenset(
    {
        "severe_is_subset_of_all",
        "severe_count_exactly_four",
        "severe_bindings_exact",
        "all_seam_supports_are_ring1",
        "observed_edge_set_exact_34",
        "required_masks_nonempty",
        "no_unlisted_overlap",
    }
)
OBSERVED_OVERLAP_FIELDS = frozenset(
    {
        "first",
        "second",
        "count",
        "allowed",
        "reason",
        "shared_vertex_indices_before_final_reindex",
    }
)
# These are the only fields admitted by the schema but deliberately excluded
# from the exact semantic projection. Full hashes remain diagnostic-only; ``t``
# is instead governed by MAX_ABSOLUTE_T_DELTA and exact identity alignment.
EXCLUDED_PROJECTION_FIELDS = {
    "masks": frozenset({"canonical_sha256"}),
    "vertex_mask": frozenset({"canonical_sha256"}),
    "edge_mask": frozenset({"canonical_sha256"}),
    "vertex_record": frozenset({"t"}),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must be a mapping")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], allowed: frozenset[str], path: str
) -> None:
    observed = set(value)
    if observed != allowed:
        missing = sorted(allowed - observed)
        unknown = sorted(observed - allowed)
        raise ValueError(
            f"{path} fields must be exact; missing={missing}, unknown={unknown}"
        )


def _require_sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{path} must be a sequence")
    return value


def _exact_number(value: Any, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{path} must be an int or finite float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    return value


def _exact_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{path} must be an int")
    return value


def _exact_bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{path} must be a bool")
    return value


def _exact_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{path} must be a string")
    return value


def _diagnostic_sha256(value: Any, path: str) -> None:
    digest = _exact_string(value, path)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{path} must be a lowercase SHA-256 digest")


def _int_pair(value: Any, path: str) -> list[int]:
    pair = _require_sequence(value, path)
    if len(pair) != 2:
        raise ValueError(f"{path} must contain exactly two integers")
    return [
        _exact_int(pair[0], f"{path}[0]"),
        _exact_int(pair[1], f"{path}[1]"),
    ]


def _vertex_record(record: Any, path: str) -> dict[str, Any]:
    source = _require_mapping(record, path)
    _require_exact_keys(source, VERTEX_RECORD_FIELDS, path)
    return {
        "vertex_index_before_final_reindex": _exact_int(
            source["vertex_index_before_final_reindex"],
            f"{path}.vertex_index_before_final_reindex",
        ),
        "canonical_original_id": _exact_int(
            source["canonical_original_id"], f"{path}.canonical_original_id"
        ),
        "graph_ring": _exact_int(source["graph_ring"], f"{path}.graph_ring"),
        "u": _exact_number(source["u"], f"{path}.u"),
    }


def semantic_mask_projection(masks: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact acceptance projection, excluding all ``t``/full hashes."""

    source = _require_mapping(masks, "masks")
    _require_exact_keys(source, MASK_FIELDS, "masks")
    _diagnostic_sha256(source["canonical_sha256"], "masks.canonical_sha256")
    vertex_masks = _require_mapping(source.get("vertex_masks"), "masks.vertex_masks")
    edge_masks = _require_mapping(source.get("edge_masks"), "masks.edge_masks")
    _require_exact_keys(vertex_masks, VERTEX_MASK_NAMES, "masks.vertex_masks")
    _require_exact_keys(edge_masks, EDGE_MASK_NAMES, "masks.edge_masks")

    projected_vertex_masks: dict[str, Any] = {}
    for mask_name in sorted(vertex_masks):
        mask = _require_mapping(
            vertex_masks[mask_name], f"masks.vertex_masks.{mask_name}"
        )
        _require_exact_keys(
            mask, VERTEX_MASK_FIELDS, f"masks.vertex_masks.{mask_name}"
        )
        _diagnostic_sha256(
            mask["canonical_sha256"],
            f"masks.vertex_masks.{mask_name}.canonical_sha256",
        )
        declared_name = _exact_string(
            mask["name"], f"masks.vertex_masks.{mask_name}.name"
        )
        if declared_name != mask_name:
            raise ValueError(
                f"masks.vertex_masks.{mask_name}.name must equal its mask key"
            )
        raw_records = _require_sequence(
            mask.get("records"), f"masks.vertex_masks.{mask_name}.records"
        )
        records = [
            _vertex_record(
                record, f"masks.vertex_masks.{mask_name}.records[{index}]"
            )
            for index, record in enumerate(raw_records)
        ]
        records.sort(
            key=lambda record: (
                record["vertex_index_before_final_reindex"],
                record["canonical_original_id"],
                record["graph_ring"],
                _canonical_json(record["u"]),
            )
        )
        projected_vertex_masks[mask_name] = {
            "declared_name": declared_name,
            "declared_count": _exact_int(
                mask.get("count"), f"masks.vertex_masks.{mask_name}.count"
            ),
            "derived_count": len(records),
            "members": records,
        }

    projected_edge_masks: dict[str, Any] = {}
    for mask_name in sorted(edge_masks):
        mask = _require_mapping(edge_masks[mask_name], f"masks.edge_masks.{mask_name}")
        _require_exact_keys(mask, EDGE_MASK_FIELDS, f"masks.edge_masks.{mask_name}")
        _diagnostic_sha256(
            mask["canonical_sha256"],
            f"masks.edge_masks.{mask_name}.canonical_sha256",
        )
        raw_edges = _require_sequence(
            mask.get("records"), f"masks.edge_masks.{mask_name}.records"
        )
        edges = []
        for index, edge in enumerate(raw_edges):
            endpoints = _require_sequence(
                edge, f"masks.edge_masks.{mask_name}.records[{index}]"
            )
            if len(endpoints) != 2:
                raise ValueError(
                    f"masks.edge_masks.{mask_name}.records[{index}] must have two endpoints"
                )
            edges.append(
                sorted(
                    [
                        _exact_int(
                            endpoints[0],
                            f"masks.edge_masks.{mask_name}.records[{index}][0]",
                        ),
                        _exact_int(
                            endpoints[1],
                            f"masks.edge_masks.{mask_name}.records[{index}][1]",
                        ),
                    ]
                )
            )
        edges.sort(key=lambda edge: (edge[0], edge[1]))
        projected_edge_masks[mask_name] = {
            "declared_count": _exact_int(
                mask.get("count"), f"masks.edge_masks.{mask_name}.count"
            ),
            "derived_count": len(edges),
            "edges": edges,
        }

    raw_bindings = _require_sequence(
        source.get("severe_subset_bindings"), "masks.severe_subset_bindings"
    )
    bindings = []
    for index, binding_value in enumerate(raw_bindings):
        path = f"masks.severe_subset_bindings[{index}]"
        binding = _require_mapping(binding_value, path)
        _require_exact_keys(binding, BINDING_FIELDS, path)
        bindings.append(
            {
                "seam_edge": _int_pair(binding["seam_edge"], f"{path}.seam_edge"),
                "support_vertex_index_before_final_reindex": _exact_int(
                    binding["support_vertex_index_before_final_reindex"],
                    f"{path}.support_vertex_index_before_final_reindex",
                ),
                "support_canonical_id": _exact_int(
                    binding["support_canonical_id"], f"{path}.support_canonical_id"
                ),
                "support_source_endpoint_ids": _int_pair(
                    binding["support_source_endpoint_ids"],
                    f"{path}.support_source_endpoint_ids",
                ),
            }
        )

    raw_allowed_overlaps = _require_sequence(
        source.get("allowed_overlaps"), "masks.allowed_overlaps"
    )
    allowed_overlaps = [
        _exact_string(value, f"masks.allowed_overlaps[{index}]")
        for index, value in enumerate(raw_allowed_overlaps)
    ]
    raw_observed_overlaps = _require_sequence(
        source.get("observed_overlaps"), "masks.observed_overlaps"
    )
    observed_overlaps = []
    for index, overlap_value in enumerate(raw_observed_overlaps):
        path = f"masks.observed_overlaps[{index}]"
        overlap = _require_mapping(overlap_value, path)
        _require_exact_keys(overlap, OBSERVED_OVERLAP_FIELDS, path)
        shared_values = _require_sequence(
            overlap["shared_vertex_indices_before_final_reindex"],
            f"{path}.shared_vertex_indices_before_final_reindex",
        )
        observed_overlaps.append(
            {
                "first": _exact_string(overlap["first"], f"{path}.first"),
                "second": _exact_string(overlap["second"], f"{path}.second"),
                "count": _exact_int(overlap["count"], f"{path}.count"),
                "allowed": _exact_bool(overlap["allowed"], f"{path}.allowed"),
                "reason": _exact_string(overlap["reason"], f"{path}.reason"),
                "shared_vertex_indices_before_final_reindex": [
                    _exact_int(
                        value,
                        f"{path}.shared_vertex_indices_before_final_reindex[{item_index}]",
                    )
                    for item_index, value in enumerate(shared_values)
                ],
            }
        )
    gates = _require_mapping(source.get("severe_subset_gates"), "masks.severe_subset_gates")
    _require_exact_keys(gates, GATE_FIELDS, "masks.severe_subset_gates")
    projected_gates = {
        name: _exact_bool(gates[name], f"masks.severe_subset_gates.{name}")
        for name in sorted(gates)
    }

    return {
        "schema": SEMANTIC_SCHEMA,
        "vertex_masks": projected_vertex_masks,
        "edge_masks": projected_edge_masks,
        "severe_subset_bindings": sorted(bindings, key=_canonical_json),
        "severe_subset_gates": projected_gates,
        "allowed_overlaps": sorted(allowed_overlaps),
        "observed_overlaps": sorted(observed_overlaps, key=_canonical_json),
        "unexpected_overlap_count": _exact_int(
            source.get("unexpected_overlap_count"), "masks.unexpected_overlap_count"
        ),
    }


def semantic_mask_sha256(masks: Mapping[str, Any]) -> str:
    """Hash only the exact semantic acceptance projection."""

    return _sha256(semantic_mask_projection(masks))


def _exact_mismatches(reference: Any, observed: Any, path: str = "") -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if type(reference) is not type(observed):
        return [
            {
                "path": path or "$",
                "reason": "type_mismatch",
                "reference_type": type(reference).__name__,
                "observed_type": type(observed).__name__,
            }
        ]
    if isinstance(reference, dict):
        reference_keys = set(reference)
        observed_keys = set(observed)
        if reference_keys != observed_keys:
            mismatches.append(
                {
                    "path": path or "$",
                    "reason": "key_set_mismatch",
                    "reference_keys": sorted(reference_keys),
                    "observed_keys": sorted(observed_keys),
                }
            )
        for key in sorted(reference_keys & observed_keys):
            child = f"{path}.{key}" if path else key
            mismatches.extend(_exact_mismatches(reference[key], observed[key], child))
        return mismatches
    if isinstance(reference, list):
        if len(reference) != len(observed):
            mismatches.append(
                {
                    "path": path or "$",
                    "reason": "length_mismatch",
                    "reference_length": len(reference),
                    "observed_length": len(observed),
                }
            )
        for index, (expected_item, observed_item) in enumerate(zip(reference, observed)):
            mismatches.extend(
                _exact_mismatches(expected_item, observed_item, f"{path}[{index}]")
            )
        return mismatches
    if reference != observed:
        mismatches.append(
            {
                "path": path or "$",
                "reason": "value_mismatch",
                "reference": reference,
                "observed": observed,
            }
        )
    return mismatches


def _t_records(masks: Mapping[str, Any]) -> tuple[dict[tuple[Any, ...], Any], list[list[Any]]]:
    _require_exact_keys(masks, MASK_FIELDS, "masks")
    vertex_masks = _require_mapping(masks.get("vertex_masks"), "masks.vertex_masks")
    _require_exact_keys(vertex_masks, VERTEX_MASK_NAMES, "masks.vertex_masks")
    values: dict[tuple[Any, ...], Any] = {}
    duplicates: list[list[Any]] = []
    for mask_name in sorted(vertex_masks):
        mask = _require_mapping(
            vertex_masks[mask_name], f"masks.vertex_masks.{mask_name}"
        )
        _require_exact_keys(
            mask, VERTEX_MASK_FIELDS, f"masks.vertex_masks.{mask_name}"
        )
        records = _require_sequence(
            mask.get("records"), f"masks.vertex_masks.{mask_name}.records"
        )
        for index, record_value in enumerate(records):
            record = _require_mapping(
                record_value, f"masks.vertex_masks.{mask_name}.records[{index}]"
            )
            _require_exact_keys(
                record,
                VERTEX_RECORD_FIELDS,
                f"masks.vertex_masks.{mask_name}.records[{index}]",
            )
            key = (
                mask_name,
                _exact_int(
                    record.get("vertex_index_before_final_reindex"),
                    f"masks.vertex_masks.{mask_name}.records[{index}].vertex_index_before_final_reindex",
                ),
                _exact_int(
                    record.get("canonical_original_id"),
                    f"masks.vertex_masks.{mask_name}.records[{index}].canonical_original_id",
                ),
            )
            if key in values:
                duplicates.append(list(key))
            values[key] = _exact_number(
                record["t"], f"masks.vertex_masks.{mask_name}.records[{index}].t"
            )
    return values, duplicates


def t_delta_evidence(
    reference_masks: Mapping[str, Any], observed_masks: Mapping[str, Any]
) -> dict[str, Any]:
    """Report and gate aligned ``t`` deltas using the inherited stability bound."""

    reference, reference_duplicates = _t_records(reference_masks)
    observed, observed_duplicates = _t_records(observed_masks)
    shared = sorted(set(reference) & set(observed))
    records = []
    for key in shared:
        reference_t = reference[key]
        observed_t = observed[key]
        delta = float(observed_t) - float(reference_t)
        records.append(
            {
                "mask": key[0],
                "vertex_index_before_final_reindex": key[1],
                "canonical_original_id": key[2],
                "reference_t": reference_t,
                "observed_t": observed_t,
                "delta_t": delta,
                "absolute_delta_t": abs(delta),
            }
        )
    reference_only = sorted(set(reference) - set(observed))
    observed_only = sorted(set(observed) - set(reference))
    maximum_absolute_delta = max(
        (record["absolute_delta_t"] for record in records), default=0.0
    )
    checks = {
        "identity_sets_aligned_exactly": not reference_only and not observed_only,
        "reference_identities_have_no_duplicates": not reference_duplicates,
        "observed_identities_have_no_duplicates": not observed_duplicates,
        "maximum_absolute_t_delta_within_2_5e_06": maximum_absolute_delta
        <= MAX_ABSOLUTE_T_DELTA,
    }
    return {
        "acceptance_role": "BOUNDED_STABILITY_GATE_FOR_RELIEF_INPUT",
        "gate_maximum_absolute_delta_t": MAX_ABSOLUTE_T_DELTA,
        "inherited_a09_a10_maximum_absolute_delta_t": INHERITED_MAX_ABSOLUTE_T_DELTA,
        "shared_identity_count": len(shared),
        "reference_only_identities": [list(key) for key in reference_only],
        "observed_only_identities": [list(key) for key in observed_only],
        "reference_duplicate_identities": reference_duplicates,
        "observed_duplicate_identities": observed_duplicates,
        "changed_count": sum(record["delta_t"] != 0.0 for record in records),
        "maximum_absolute_delta_t": maximum_absolute_delta,
        "checks": checks,
        "passed": all(checks.values()),
        "records": records,
    }


def compare_semantic_masks(
    reference_masks: Mapping[str, Any], observed_masks: Mapping[str, Any]
) -> dict[str, Any]:
    """Return exact semantics plus the separate bounded ``t`` stability gate."""

    reference_projection = semantic_mask_projection(reference_masks)
    observed_projection = semantic_mask_projection(observed_masks)
    mismatches = _exact_mismatches(reference_projection, observed_projection)
    t_deltas = t_delta_evidence(reference_masks, observed_masks)
    checks = {
        "semantic_projection_exact": not mismatches,
        "t_identity_sets_aligned_exactly": t_deltas["checks"][
            "identity_sets_aligned_exactly"
        ],
        "t_reference_identities_have_no_duplicates": t_deltas["checks"][
            "reference_identities_have_no_duplicates"
        ],
        "t_observed_identities_have_no_duplicates": t_deltas["checks"][
            "observed_identities_have_no_duplicates"
        ],
        "t_maximum_absolute_delta_within_gate": t_deltas["checks"][
            "maximum_absolute_t_delta_within_2_5e_06"
        ],
        "full_mask_canonical_sha256_excluded": True,
    }
    return {
        "schema": SEMANTIC_SCHEMA,
        "reference_semantic_sha256": _sha256(reference_projection),
        "observed_semantic_sha256": _sha256(observed_projection),
        "checks": checks,
        "passed": all(checks.values()),
        "semantic_mismatches": mismatches,
        "t_deltas": t_deltas,
    }
