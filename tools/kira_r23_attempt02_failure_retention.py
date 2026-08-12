#!/usr/bin/env python3
"""Pure helpers for retaining R23 Attempt 02 preflight failure metrics."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from tools.kira_r23_cc0_afes_preflight_core import (
    canonical_index_sha256,
)


def retain_preflight_failure_metrics(
    preflight_locals: Mapping[str, Any],
    expanded_locals: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert captured original-worker locals into JSON-safe evidence.

    The caller captures these locals only after the exact original selector has
    computed all configured ring attempts and raised.  This helper performs no
    geometry, mapping, threshold, gate, or selection work.
    """

    mask_config = expanded_locals.get("mask_config", {})
    configured_rings = [
        int(value)
        for value in mask_config.get("expanded_mask_exterior_ring_candidates", [])
    ]
    attempts = deepcopy(list(expanded_locals.get("attempts", [])))
    recorded_rings = [int(row["exterior_rings"]) for row in attempts]
    allowed = {int(value) for value in expanded_locals.get("allowed", set())}
    path_union = {
        int(value) for value in expanded_locals.get("path_union", set())
    }
    target_distances = {
        int(key): int(value)
        for key, value in expanded_locals.get("target_distances", {}).items()
    }
    hit_faces = {
        int(value) for value in expanded_locals.get("hit_faces", set())
    }
    old_patch = {
        int(value) for value in expanded_locals.get("old_patch", set())
    }
    old_hit_fraction = expanded_locals.get("old_hit_fraction")
    minimum_old_fraction = expanded_locals.get("minimum_old_fraction")
    group_old_records = deepcopy(
        expanded_locals.get("group_old_records", {})
    )

    return {
        "verified_inputs": deepcopy(preflight_locals.get("inputs")),
        "authority_and_r20_reconciliation": deepcopy(
            preflight_locals.get("authority")
        ),
        "r19_source_evidence_contract": deepcopy(
            preflight_locals.get("r19_evidence_contract")
        ),
        "r19_old_patch": deepcopy(preflight_locals.get("old_record")),
        "qualified_cc0_donor": deepcopy(
            preflight_locals.get("donor_evidence")
        ),
        "donor_to_r19_projection": deepcopy(
            preflight_locals.get("projection")
        ),
        "expanded_r19_mask_failure": {
            "old_mask_fit": {
                "projected_hit_face_fraction_inside_old_patch": old_hit_fraction,
                "minimum_required": minimum_old_fraction,
                "per_required_AFES_group": group_old_records,
                "passed": bool(expanded_locals.get("old_mask_fit", False)),
                "expanded_mask_was_computed": True,
            },
            "allowed_chart_face_count": len(allowed),
            "allowed_chart_face_index_sha256": canonical_index_sha256(allowed),
            "path_union_face_count": len(path_union),
            "path_union_face_index_sha256": canonical_index_sha256(path_union),
            "maximum_shortest_path_edges": max(
                target_distances.values(), default=0
            ),
            "old_patch_face_count": len(old_patch),
            "projected_hit_face_count": len(hit_faces),
            "attempts": attempts,
            "retention": {
                "configured_exterior_rings": configured_rings,
                "recorded_exterior_rings": recorded_rings,
                "attempt_count": len(attempts),
                "complete_attempts_array": recorded_rings == configured_rings,
                "selector_returned_a_mask": False,
            },
        },
        "pre_failure_integrity": {
            "source_blend_hash_before": preflight_locals.get(
                "source_hash_before"
            ),
            "r19_body_state_before": preflight_locals.get(
                "body_state_before"
            ),
            "r19_body_state_after_donor_append": preflight_locals.get(
                "body_state_after_donor_append"
            ),
            "r19_body_unchanged_after_donor_append": (
                preflight_locals.get("body_state_before")
                == preflight_locals.get("body_state_after_donor_append")
            ),
        },
    }

