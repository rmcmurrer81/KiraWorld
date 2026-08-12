"""No-save R24 Attempt 13 revision-04 measured post-solve simulation.

This append-only worker is derived from the preserved Attempt 12 revision-03
worker and preserves the sealed R19 source plus Attempts 01-12. It keeps every
geometry input and gate unchanged. Support-vector evidence norms are computed
canonically from their serialized components while Blender's native
``mathutils.Vector.length`` measurements remain separately recorded. It never
saves a Blend.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
import traceback

import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_internal_midpoint_panel_neutralized_attempt07 as a07  # noqa: E402
from Core.kira_r24_semantic_mask_effect_fingerprint_v1 import compare_semantic_masks_with_runtime_effect  # noqa: E402


a14 = a07.a14
a09 = a14.a09
a10 = a14.a10
a11 = a14.a11
SOURCE = a14.SOURCE
SOURCE_SHA256 = a14.SOURCE_SHA256
BOUND_SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
BODY_NAME = a14.BODY_NAME
RIG_NAME = a14.RIG_NAME
OUTPUT_ROOT = a14.OUTPUT_ROOT

ATTEMPT_07_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_panel_neutralized_attempt07.py"
ATTEMPT_07_WORKER_SHA256 = "d64a2028f834eee81c4342995b6a7b2a89bdec21f9cf392f09bfc4ac48c5a3db"
ATTEMPT_07_PRE_MASK = OUTPUT_ROOT / "attempt_07/PRE_MASK_DIAGNOSTIC.json"
ATTEMPT_07_PRE_MASK_SHA256 = "b745524451cd3091f0fa505efca122b9f37b77330bf8db5a8504e5209fbac15f"
ATTEMPT_07_PRE_CAP = OUTPUT_ROOT / "attempt_07/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_07_PRE_CAP_SHA256 = "2176ae27a3c929935b72e6e91ea70517726810f0bc4b3d5cb821dcffdf3a5f63"
ATTEMPT_07_FAILURE = OUTPUT_ROOT / "attempt_07/FAILURE.json"
ATTEMPT_07_FAILURE_SHA256 = "7c092c109f43097a620be57f26928cdb615c0eeea09a34de177cdfae82bbb409"
ATTEMPT_07_DIAGNOSIS = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_07_EXACT_CAP_DIAGNOSIS.json"
ATTEMPT_07_DIAGNOSIS_SHA256 = "ec38013f6abdea5fced80218ff09f4536e5e80daf449a885009b508b0daaa19a"
ATTEMPT_08_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_08_EXACT_THREE_SUPPORT_CAP_PROPOSAL.md"
ATTEMPT_08_PROPOSAL_SHA256 = "3396098749f8f5dbc1f8e21a25c2536a6a7d09c2bafb93a8a4f94d407598b346"
ATTEMPT_08_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_exact_three_caps.py"
ATTEMPT_08_WORKER_SHA256 = "32ca67801b3ce72d2b3b2ef378f16a877a09daa0f1dda88e24592d1df5d7124d"
ATTEMPT_08_STDOUT = OUTPUT_ROOT / "attempt_08/BLENDER_STDOUT_STDERR.txt"
ATTEMPT_08_STDOUT_SHA256 = "5af25ddc65740369452b97b4a068a56f7bb18e3c34e3edbb650699fd881d1664"
ATTEMPT_08_FAILURE = OUTPUT_ROOT / "attempt_08/FAILURE.json"
ATTEMPT_08_FAILURE_SHA256 = "a3b9eada4958a46a318454f2b5e88c7628931ef5d80cd2849bf3c77b923c4fc4"
ATTEMPT_09_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_09_STARTUP_BINDING_REPAIR_PROPOSAL.md"
ATTEMPT_09_PROPOSAL_SHA256 = "2520107452255b805902763f64a83b3a54f8014bc947ea62be6e36db395749e1"
ATTEMPT_09_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_exact_three_caps_attempt09.py"
ATTEMPT_09_WORKER_SHA256 = "0ca82d2dbe160f450e55bedc3a0aa1a68ab3f44876707a1f0bb9f63fe7ad0dd4"
ATTEMPT_09_PRE_MASK = OUTPUT_ROOT / "attempt_09/PRE_MASK_DIAGNOSTIC.json"
ATTEMPT_09_PRE_MASK_SHA256 = "0b881a0e16330c373f9b880f9257e5662d4129a52ce730201bcd5d9fcd93037b"
ATTEMPT_09_PRE_CAP = OUTPUT_ROOT / "attempt_09/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_09_PRE_CAP_SHA256 = "790e3569b26329604636cbda44e820ecc6df4ac87a4fb9f6d79a9a253cc21dca"
ATTEMPT_09_SOLVER = OUTPUT_ROOT / "attempt_09/SOLVER_DIAGNOSTIC.json"
ATTEMPT_09_SOLVER_SHA256 = "f23b84bc59b83a0cc5c619d58b361f7fdef988a34a1aa6c6c4e737149185c4a3"
ATTEMPT_09_FAILURE = OUTPUT_ROOT / "attempt_09/FAILURE.json"
ATTEMPT_09_FAILURE_SHA256 = "5e98ca12e2d7123aa7b91acfec3f56955afa70a0801ccc93a50550dbe7963374"
ATTEMPT_09_DIAGNOSIS = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_09_KKT_POSTCAP_DIAGNOSIS.json"
ATTEMPT_09_DIAGNOSIS_SHA256 = "f9d03c336c8c5824d0d8acdac0e2c8a0e09e5edd31a3360db7a7b1843407b86d"
ATTEMPT_10_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_10_MEASURED_POSTSOLVE_CEILING_PROPOSAL.md"
ATTEMPT_10_PROPOSAL_SHA256 = "ba55c2fe7457762a86057a4d7e0ed353fdb9b6735188f8504dbdec1d8099868a"
REJECTED_ATTEMPT_10_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt10.py"
REJECTED_ATTEMPT_10_WORKER_SHA256 = "c7abcd3af6e6da8e084bab721137f3bcc26d969b275ca681b92a5c9c7be906b4"
REJECTED_ATTEMPT_10_CHECKPOINT = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_10_STATIC_CHECKPOINT.md"
REJECTED_ATTEMPT_10_CHECKPOINT_SHA256 = "5e404c839adced2f19f93c3113b0c4b581be33eef5650df6f1ff4e244d568cd7"
REVISION01_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt10_revision01.py"
REVISION01_WORKER_SHA256 = "f36f08ee29652fccac3b626cc821f5d8cb6c36584a7441f129b67a65b051dfd9"
ATTEMPT_10_PRE_MASK = OUTPUT_ROOT / "attempt_10/PRE_MASK_DIAGNOSTIC.json"
ATTEMPT_10_PRE_MASK_SHA256 = "ddd040e808f38e16436148c5b82365aa6c441b32751a078578a4d897fd92fe9a"
ATTEMPT_10_PRE_CAP = OUTPUT_ROOT / "attempt_10/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_10_PRE_CAP_SHA256 = "d7e77ed0dde9b08baba1d99cbdca8dc3ec39e2ded0d2f24092e78099c101536b"
ATTEMPT_10_FAILURE = OUTPUT_ROOT / "attempt_10/FAILURE.json"
ATTEMPT_10_FAILURE_SHA256 = "ec66ea06c7b16545714b85725a136f427faf7859cf9e5cb14bf3daf4d82e7355"
ATTEMPT_11_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_11_REVISION02_SEMANTIC_MASK_FINGERPRINT_PROPOSAL.md"
ATTEMPT_11_PROPOSAL_SHA256 = "2b78ffe7a088339ff416cbf2e3c4a596243695c030d2b48993dbcb4b1702a5fa"
SEMANTIC_HELPER = ROOT / "Core/kira_r24_semantic_mask_fingerprint.py"
SEMANTIC_HELPER_SHA256 = "c68d4121dcdce8ef28cbb04e48708984591569c70a9a70fb4c3565f66a4118e5"
ATTEMPT_11_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt11_revision02.py"
ATTEMPT_11_WORKER_SHA256 = "a0cbca0360ab316d1122fd9f941f0223257dd825f9ec2d1c6fe93812c53b2368"
ATTEMPT_11_PRE_MASK = OUTPUT_ROOT / "attempt_11/PRE_MASK_DIAGNOSTIC.json"
ATTEMPT_11_PRE_MASK_SHA256 = "72416bb6736b9ade70b87db2ed49ef39874f4afde1790c4ad2f81e1ea76dfe94"
ATTEMPT_11_PRE_CAP = OUTPUT_ROOT / "attempt_11/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_11_PRE_CAP_SHA256 = "0c76e898b4ead822b1750861cfab3edcd0cca35f223f9f83b9e062f01fe39c34"
ATTEMPT_11_FAILURE = OUTPUT_ROOT / "attempt_11/FAILURE.json"
ATTEMPT_11_FAILURE_SHA256 = "1dd40afc5afa638ed7359a79c00b006f42a8950c7b52dfe0c53d27e00a08323a"
ATTEMPT_12_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_12_REVISION03_RUNTIME_EFFECT_FINGERPRINT_PROPOSAL.md"
ATTEMPT_12_PROPOSAL_SHA256 = "5c26f2afe81e77221e87b79b12b4afbd4303e782ec181c501a9d642f15b4a56a"
RUNTIME_EFFECT_HELPER = ROOT / "Core/kira_r24_semantic_mask_effect_fingerprint_v1.py"
RUNTIME_EFFECT_HELPER_SHA256 = "dc9200429b1f4a8172282fe2b3b56a263eda3aad18fc146b59fa0a87a6201fb4"
ATTEMPT_12_WORKER = ROOT / "tools/blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt12_revision03.py"
ATTEMPT_12_WORKER_SHA256 = "a03597d16623450d72608fdfffe9bd4c4db252b226f52a3090f4d17ff29370f2"
ATTEMPT_12_PRE_MASK = OUTPUT_ROOT / "attempt_12/PRE_MASK_DIAGNOSTIC.json"
ATTEMPT_12_PRE_MASK_SHA256 = "8614dd1c7a7cb83c05e49a6e55c3590408690f28b3c7ece83897b6d4f1069d93"
ATTEMPT_12_PRE_CAP = OUTPUT_ROOT / "attempt_12/PRE_CAP_DIAGNOSTIC.json"
ATTEMPT_12_PRE_CAP_SHA256 = "73ccdbb0051ee1ba983a95c149d53dfc90b1547e82c4f8abf37e6eb2079ea88a"
ATTEMPT_12_SOLVER = OUTPUT_ROOT / "attempt_12/SOLVER_DIAGNOSTIC.json"
ATTEMPT_12_SOLVER_SHA256 = "cfda494e79549feee2b3e35c4b293be53cd265a969940f979b4d1a3dd4ffc896"
ATTEMPT_12_FAILURE = OUTPUT_ROOT / "attempt_12/FAILURE.json"
ATTEMPT_12_FAILURE_SHA256 = "3bb9012990727a7c049ac0dae3ab747f395a8bd039a88187c2b936d6bd394598"
ATTEMPT_13_PROPOSAL = OUTPUT_ROOT / "PREFLIGHT/ATTEMPT_13_REVISION04_CANONICAL_SERIALIZED_NORM_PROPOSAL.md"
ATTEMPT_13_PROPOSAL_SHA256 = "9c83c411816d6f71832effbc8919c523ee68f57550b4e27a3f3228c5a816764a"
EXPECTED_ATTEMPT_SLOT = "attempt_13"
PROPOSAL = ATTEMPT_13_PROPOSAL

SEVERE_RING_1_CAP_M = a14.SEVERE_RING_1_CAP_M
OTHER_RING_1_CAP_M = a14.OTHER_RING_1_CAP_M
RING_2_CAP_M = a14.RING_2_CAP_M
DEEP_CAP_M = a14.DEEP_CAP_M
OVERALL_CAP_M = 0.00240
P95_CAP_M = a14.P95_CAP_M
RMS_CAP_M = a14.RMS_CAP_M
POSTSOLVE_DEFAULT_SEVERE_CEILING_M = 0.002330
POSTSOLVE_EXCEPTION_CEILINGS_M = {
    (1009, 2398): 0.002010,
    (1097, 1529): 0.002525,
    (2481, 2861): 0.002480,
}
POSTSOLVE_OVERALL_CEILING_M = 0.002525
POSTSOLVE_RMS_CEILING_M = 0.000460
INHERITED_RING_1_CAP_M = 0.00240
INHERITED_TOTAL_BASE_FIT_CAP_M = 0.00240
FINGERPRINT_FLOAT_TOLERANCE_M = 1.0e-12
COEFFICIENT_NORM_TOLERANCE = 1.0e-12
RELIEF_CAP_M = a14.RELIEF_CAP_M
COMBINED_CAP_M = a14.COMBINED_CAP_M
RING_1_SOFT_WEIGHT = a14.RING_1_SOFT_WEIGHT
RING_2_CONTINUATION_WEIGHT = a14.RING_2_CONTINUATION_WEIGHT
RING_2_OTHER_WEIGHT = a14.RING_2_OTHER_WEIGHT
CONSTRAINT_RESIDUAL_TOLERANCE_M = a14.CONSTRAINT_RESIDUAL_TOLERANCE_M
TARGET_BY_CLASS = a14.TARGET_BY_CLASS

atomic_write_json = a14.atomic_write_json
displacement_distribution = a14.displacement_distribution
edge_key = a14.edge_key
edge_class = a14.edge_class

EXPECTED_CAP_BINDINGS = {
    (1009, 2398): {
        "class": "REGULAR_FLANK_EDGES",
        "support_vertex_index_before_final_reindex": 12676,
        "support_canonical_id": -66,
        "support_source_endpoint_ids": [2398, 12507],
        "cap_m": 0.00200,
        "minimum_required_m": 0.0019493451140220463,
    },
    (1097, 1529): {
        "class": "SEVERE_FLANK_EDGES",
        "support_vertex_index_before_final_reindex": 12643,
        "support_canonical_id": -33,
        "support_source_endpoint_ids": [1097, 12563],
        "cap_m": 0.00240,
        "minimum_required_m": 0.0023733727705092336,
    },
    (2481, 2861): {
        "class": "SEVERE_FLANK_EDGES",
        "support_vertex_index_before_final_reindex": 12686,
        "support_canonical_id": -76,
        "support_source_endpoint_ids": [2481, 12476],
        "cap_m": 0.00240,
        "minimum_required_m": 0.0023204652098137387,
    },
}

ACTIVE_OUTPUT: Path | None = None
ACTIVE_EXCEPTION_CAPS = {}
RELIEF_SEQUENCE = deque()
OBSERVED_RUNTIME_PARAMETERS = {}


def sha256(path: Path) -> str:
    return a14.sha256(path)


def relative(path: Path) -> str:
    return a14.relative(path)


def edge_label(edge) -> str:
    return "_".join(map(str, edge))


def load_bound_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value) -> str:
    return a09.a08.canonical_sha256(value)


def exact_vector_record(vector) -> list[float]:
    return [float(value) for value in vector]


def serialized_mathutils_norm(values) -> float:
    """Round-trip serialized components through Blender's native norm path."""

    return float(Vector(tuple(float(value) for value in values)).length)


def serialized_python_double_norm(values) -> float:
    """Return a diagnostic-only binary64 norm of serialized components."""

    return math.sqrt(sum(float(value) ** 2 for value in values))


def all_finite(value) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(all_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(all_finite(item) for item in value)
    return False


def generated_block_comparison(reference, observed, path=""):
    """Compare deterministic generated values with a strict 1 pm tolerance."""
    mismatches = []

    def compare(expected, actual, location):
        if isinstance(expected, bool) or isinstance(actual, bool):
            if type(expected) is not type(actual) or expected != actual:
                mismatches.append({"path": location, "expected": expected, "observed": actual})
            return
        if isinstance(expected, int) or isinstance(actual, int):
            if type(expected) is not type(actual) or expected != actual:
                mismatches.append({"path": location, "expected": expected, "observed": actual})
            return
        if isinstance(expected, float) or isinstance(actual, float):
            if not isinstance(expected, (int, float)) or not isinstance(actual, (int, float)):
                mismatches.append({"path": location, "expected": expected, "observed": actual})
                return
            expected_float = float(expected)
            actual_float = float(actual)
            if (
                not math.isfinite(expected_float)
                or not math.isfinite(actual_float)
                or abs(expected_float - actual_float) > FINGERPRINT_FLOAT_TOLERANCE_M
            ):
                mismatches.append(
                    {
                        "path": location,
                        "expected": expected_float,
                        "observed": actual_float,
                        "absolute_difference": abs(expected_float - actual_float),
                    }
                )
            return
        if isinstance(expected, str) or expected is None:
            if expected != actual:
                mismatches.append({"path": location, "expected": expected, "observed": actual})
            return
        if isinstance(expected, list):
            if not isinstance(actual, list) or len(expected) != len(actual):
                mismatches.append(
                    {
                        "path": location,
                        "expected_length": len(expected),
                        "observed_length": len(actual) if isinstance(actual, list) else None,
                    }
                )
                return
            for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
                compare(expected_item, actual_item, f"{location}[{index}]")
            return
        if isinstance(expected, dict):
            if not isinstance(actual, dict) or set(expected) != set(actual):
                mismatches.append(
                    {
                        "path": location,
                        "expected_keys": sorted(expected),
                        "observed_keys": sorted(actual) if isinstance(actual, dict) else None,
                    }
                )
                return
            for key in sorted(expected):
                compare(expected[key], actual[key], f"{location}.{key}" if location else key)
            return
        if expected != actual:
            mismatches.append({"path": location, "expected": expected, "observed": actual})

    compare(reference, observed, path)
    return mismatches


def exact_soft_record_comparison(reference_records, observed_records):
    mismatches = []
    if len(reference_records) != len(observed_records):
        return [
            {
                "path": "soft_constraint_records",
                "expected_length": len(reference_records),
                "observed_length": len(observed_records),
            }
        ]
    exact_keys = (
        "vertex_index_before_final_reindex",
        "graph_ring",
        "kind",
        "weight",
        "cap_m",
    )
    generated_keys = ("capped_target_world_m", "capped_target_length_m")
    for index, (expected, observed) in enumerate(zip(reference_records, observed_records)):
        for key in exact_keys:
            if expected.get(key) != observed.get(key):
                mismatches.append(
                    {
                        "path": f"soft_constraint_records[{index}].{key}",
                        "expected": expected.get(key),
                        "observed": observed.get(key),
                    }
                )
        for key in generated_keys:
            mismatches.extend(
                generated_block_comparison(
                    expected.get(key),
                    observed.get(key),
                    f"soft_constraint_records[{index}].{key}",
                )
            )
    return mismatches


def attempt12_revision03_solver_fingerprint(observed):
    reference = load_bound_json(ATTEMPT_09_SOLVER)
    mask_reference = load_bound_json(ATTEMPT_10_PRE_MASK)
    runtime_effect_fingerprint = compare_semantic_masks_with_runtime_effect(
        mask_reference["masks"],
        observed["masks"],
        observed_runtime_parameters=OBSERVED_RUNTIME_PARAMETERS,
    )
    exact_fields = ("method", "hessian_dimension", "constraint_count", "schur_method")
    checks = {
        f"{field}_exact": observed.get(field) == reference.get(field)
        for field in exact_fields
    }
    residual_difference = abs(
        float(observed["maximum_constraint_residual_m"])
        - float(reference["maximum_constraint_residual_m"])
    )
    checks.update(
        {
            "maximum_constraint_residual_matches_within_1pm": residual_difference
            <= FINGERPRINT_FLOAT_TOLERANCE_M,
            "maximum_constraint_residual_still_at_most_20nm": float(
                observed["maximum_constraint_residual_m"]
            )
            <= CONSTRAINT_RESIDUAL_TOLERANCE_M,
            "mask_semantic_and_runtime_effect_gate_passed": (
                runtime_effect_fingerprint["passed"]
            ),
            "exact_cap_policy_exact": observed["attempt08_exact_cap_policy"]
            == reference["attempt08_exact_cap_policy"],
        }
    )
    generated_fields = (
        "lagrange_multipliers",
        "distribution",
        "ring_distributions",
        "severe_ring1_distribution",
        "other_ring1_distribution",
        "attempt08_exception_distributions",
        "attempt08_default_severe_ring1_distribution",
        "attempt08_default_other_ring1_distribution",
    )
    generated_mismatches = []
    for field in generated_fields:
        generated_mismatches.extend(
            generated_block_comparison(reference[field], observed[field], field)
        )
    soft_mismatches = exact_soft_record_comparison(
        reference["soft_constraint_records"], observed["soft_constraint_records"]
    )
    checks["generated_solver_blocks_match_within_1pm"] = not generated_mismatches
    checks["soft_records_identity_caps_weights_exact_vectors_within_1pm"] = not soft_mismatches
    return {
        "reference_path": relative(ATTEMPT_09_SOLVER),
        "reference_sha256": ATTEMPT_09_SOLVER_SHA256,
        "mask_reference_path": relative(ATTEMPT_10_PRE_MASK),
        "mask_reference_sha256": ATTEMPT_10_PRE_MASK_SHA256,
        "float_tolerance_m": FINGERPRINT_FLOAT_TOLERANCE_M,
        "mask_semantic_runtime_effect_fingerprint": runtime_effect_fingerprint,
        "checks": checks,
        "passed": all(checks.values()),
        "residual_absolute_difference_m": residual_difference,
        "generated_mismatches": generated_mismatches[:100],
        "soft_record_mismatches": soft_mismatches[:100],
    }


def attempt10_postsolve_ceiling(edge, classification):
    key = edge_key(edge)
    if key in POSTSOLVE_EXCEPTION_CEILINGS_M:
        return POSTSOLVE_EXCEPTION_CEILINGS_M[key]
    if classification == "SEVERE_FLANK_EDGES":
        return POSTSOLVE_DEFAULT_SEVERE_CEILING_M
    return OTHER_RING_1_CAP_M


def attempt08_build_mask_evidence(
    planes,
    patch_vertices,
    patch_edges,
    seam_vertices,
    distances,
    original_ids,
    parameters,
):
    evidence, masks = a07.corrected_build_mask_evidence(
        planes,
        patch_vertices,
        patch_edges,
        seam_vertices,
        distances,
        original_ids,
        parameters,
    )
    captured = {}
    for vertex in patch_vertices:
        identity = (int(vertex.index), int(original_ids.get(vertex, -1)))
        if identity in captured:
            raise RuntimeError(
                f"duplicate full-precision runtime identity {identity}"
            )
        u, t = parameters[vertex]
        captured[identity] = {"u": float(u), "t": float(t)}
    OBSERVED_RUNTIME_PARAMETERS.clear()
    OBSERVED_RUNTIME_PARAMETERS.update(captured)
    return evidence, masks


def attempt08_constraint_records(body, planes, original_ids):
    runtime, evidence = a14.constraint_records(body, planes, original_ids)
    ACTIVE_EXCEPTION_CAPS.clear()
    seen = set()
    for runtime_record, record in zip(runtime, evidence):
        edge = edge_key(record["boundary_vertex_ids"])
        expected = EXPECTED_CAP_BINDINGS.get(edge)
        if expected is None:
            continue
        support = runtime_record["support"]
        observed = {
            "class": record["seam_class"],
            "support_vertex_index_before_final_reindex": int(support.index),
            "support_canonical_id": int(original_ids.get(support, -1)),
            "support_source_endpoint_ids": list(
                a11.authoritative_endpoint_lookup(support, original_ids)
            ),
        }
        for key in (
            "class",
            "support_vertex_index_before_final_reindex",
            "support_canonical_id",
            "support_source_endpoint_ids",
        ):
            if observed[key] != expected[key]:
                raise RuntimeError(
                    f"Attempt 08 cap exception binding drift for {edge}: {key}"
                )
        minimum = float(record["closest_linear_slope_minimum"]["length_m"])
        if abs(minimum - float(expected["minimum_required_m"])) > 1.0e-9:
            raise RuntimeError(
                f"Attempt 08 measured minimum drift for exact support {edge}"
            )
        cap = float(expected["cap_m"])
        record["ring_1_cap_m"] = cap
        record["closest_linear_slope_minimum"]["within_ring_1_cap"] = (
            minimum <= cap + a09.MOVEMENT_EPSILON_M
        )
        record["normal_only_minimum"]["within_ring_1_cap"] = (
            float(record["normal_only_minimum"]["length_m"])
            <= cap + a09.MOVEMENT_EPSILON_M
        )
        record["attempt06_gate"]["closest_minimum_within_exact_class_cap"] = (
            record["closest_linear_slope_minimum"]["within_ring_1_cap"]
        )
        record["attempt08_exact_cap_override"] = {
            "edge": list(edge),
            **expected,
        }
        ACTIVE_EXCEPTION_CAPS[support] = {"edge": edge, **expected}
        seen.add(edge)
    if seen != set(EXPECTED_CAP_BINDINGS):
        raise RuntimeError("Attempt 08 did not bind all three exact cap exceptions")
    return runtime, evidence


def attempt08_cap_for_vertex(vertex, severe_supports, original_ids, distance):
    if int(distance) != 1:
        raise RuntimeError("Attempt 08 ring-one cap helper received another ring")
    binding = ACTIVE_EXCEPTION_CAPS.get(vertex)
    if binding is not None:
        severe = vertex in severe_supports
        expected_severe = binding["class"] == "SEVERE_FLANK_EDGES"
        if severe != expected_severe:
            raise RuntimeError("Attempt 08 exception severity membership drift")
        if int(vertex.index) != binding[
            "support_vertex_index_before_final_reindex"
        ] or int(original_ids.get(vertex, -1)) != binding["support_canonical_id"]:
            raise RuntimeError("Attempt 08 exception vertex identity drift")
        return float(binding["cap_m"]), (
            "attempt08_exact_exception_" + edge_label(binding["edge"])
        )
    if vertex in severe_supports:
        return SEVERE_RING_1_CAP_M, "ring_1_severe_support_2_25mm"
    return OTHER_RING_1_CAP_M, "ring_1_other_1_50mm"


def attempt08_cap_policy_evidence(distances, original_ids):
    records = []
    for vertex, binding in sorted(
        ACTIVE_EXCEPTION_CAPS.items(), key=lambda item: item[1]["edge"]
    ):
        distance = int(distances[vertex])
        if distance != 1:
            raise RuntimeError("Attempt 08 cap exception is not graph ring one")
        records.append(
            {
                "edge": list(binding["edge"]),
                "support_vertex_index_before_final_reindex": int(vertex.index),
                "support_canonical_id": int(original_ids.get(vertex, -1)),
                "support_source_endpoint_ids": binding[
                    "support_source_endpoint_ids"
                ],
                "seam_class": binding["class"],
                "graph_ring": distance,
                "cap_m": float(binding["cap_m"]),
                "minimum_required_m": float(binding["minimum_required_m"]),
                "minimum_headroom_m": float(binding["cap_m"])
                - float(binding["minimum_required_m"]),
                "relief_fade_required": 0.0,
            }
        )
    if len(records) != 3:
        raise RuntimeError("Attempt 08 cap policy evidence is not exactly three")
    return {
        "records": records,
        "default_severe_ring_one_cap_m": SEVERE_RING_1_CAP_M,
        "default_other_ring_one_cap_m": OTHER_RING_1_CAP_M,
        "overall_exception_ceiling_m": OVERALL_CAP_M,
        "all_targets_unchanged": True,
    }


def attempt08_coupled_fit(
    body: bpy.types.Object,
    bm: bmesh.types.BMesh,
    patch_faces: set[bmesh.types.BMFace],
    patch_vertices: set[bmesh.types.BMVert],
    patch_edges: Sequence[bmesh.types.BMEdge],
    seam_edges: set[bmesh.types.BMEdge],
    seam_vertices: set[bmesh.types.BMVert],
    distances: Mapping[bmesh.types.BMVert, int],
    original_ids: Mapping[bmesh.types.BMVert, int],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
) -> dict[str, Any]:
    global RELIEF_SEQUENCE
    if ACTIVE_OUTPUT is None:
        raise RuntimeError("Attempt 06 output was not allocated")
    vertices = sorted(patch_vertices, key=lambda vertex: int(vertex.index))
    vertex_index = {vertex: index for index, vertex in enumerate(vertices)}
    free_vertices = [vertex for vertex in vertices if vertex not in seam_vertices]
    free_index = {vertex: index for index, vertex in enumerate(free_vertices)}
    neighbors = a09.patch_neighbors(patch_vertices, patch_edges)
    if any(not neighbors.get(vertex) for vertex in vertices):
        raise RuntimeError("Attempt 06 fair-fit graph has an isolated vertex")
    base_local = {vertex: vertex.co.copy() for vertex in vertices}
    base_world = {vertex: body.matrix_world @ vertex.co for vertex in vertices}
    baseline_normals = {
        face: a09.a08.world_face_normal(body, face).copy() for face in patch_faces
    }
    planes = a09.seam_plane_records(body, patch_faces, seam_edges, original_ids)
    mask_evidence, masks = attempt08_build_mask_evidence(
        planes,
        patch_vertices,
        patch_edges,
        seam_vertices,
        distances,
        original_ids,
        parameters,
    )
    runtime_constraints, constraint_evidence = attempt08_constraint_records(
        body, planes, original_ids
    )
    pre_cap = {
        "schema": "kira.avatar.r24.a09_attempt06.pre_cap_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WRITTEN_ATOMICALLY_BEFORE_COUPLED_SOLVE",
        "worker": {
            "path": relative(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "source": {"path": relative(SOURCE), "sha256": sha256(SOURCE)},
        "proposal": {"path": relative(PROPOSAL), "sha256": sha256(PROPOSAL)},
        "selection": {
            "active_constraint_count": len(runtime_constraints),
            "exact_class_targets": TARGET_BY_CLASS,
            "all_34_edges_classified": True,
        },
        "masks": mask_evidence,
        "attempt08_exact_cap_policy": attempt08_cap_policy_evidence(
            distances, original_ids
        ),
        "constraints": constraint_evidence,
        "caps_m": {
            "boundary": 0.0,
            "severe_ring_1": SEVERE_RING_1_CAP_M,
            "other_ring_1": OTHER_RING_1_CAP_M,
            "ring_2": RING_2_CAP_M,
            "deep": DEEP_CAP_M,
            "overall": OVERALL_CAP_M,
            "p95": P95_CAP_M,
            "rms": RMS_CAP_M,
            "relief": RELIEF_CAP_M,
            "combined": COMBINED_CAP_M,
        },
        "soft_weights": {
            "ring_1": RING_1_SOFT_WEIGHT,
            "ring_2_continuation": RING_2_CONTINUATION_WEIGHT,
            "ring_2_other": RING_2_OTHER_WEIGHT,
            "screened_source_fidelity": 18.0,
            "first_differential": 1.0,
            "biharmonic": 0.20,
        },
        "authoritative_midpoint_endpoint_map": a11.authoritative_map_state(),
    }
    reference_pre_mask = load_bound_json(ATTEMPT_10_PRE_MASK)
    reference_pre_cap = load_bound_json(ATTEMPT_10_PRE_CAP)
    current_constraint_sha256 = canonical_sha256(constraint_evidence)
    reference_constraint_sha256 = canonical_sha256(reference_pre_cap["constraints"])
    current_map = pre_cap["authoritative_midpoint_endpoint_map"]
    reference_map = reference_pre_cap["authoritative_midpoint_endpoint_map"]
    runtime_effect_fingerprint = compare_semantic_masks_with_runtime_effect(
        reference_pre_mask["masks"],
        mask_evidence,
        observed_runtime_parameters=OBSERVED_RUNTIME_PARAMETERS,
    )
    pre_cap_fingerprint_checks = {
        "constraint_count_exact": len(constraint_evidence)
        == len(reference_pre_cap["constraints"]),
        "constraints_canonical_sha256_exact": current_constraint_sha256
        == reference_constraint_sha256,
        "mask_semantic_and_runtime_effect_gate_passed": runtime_effect_fingerprint[
            "passed"
        ],
        "authoritative_map_count_exact": int(current_map["count"])
        == int(reference_map["count"]),
        "authoritative_map_canonical_sha256_exact": current_map["canonical_sha256"]
        == reference_map["canonical_sha256"],
    }
    pre_cap["attempt12_revision03_pre_cap_fingerprint"] = {
        "reference_path": relative(ATTEMPT_10_PRE_CAP),
        "reference_sha256": ATTEMPT_10_PRE_CAP_SHA256,
        "reference_mask_path": relative(ATTEMPT_10_PRE_MASK),
        "reference_mask_sha256": ATTEMPT_10_PRE_MASK_SHA256,
        "current_constraints_canonical_sha256": current_constraint_sha256,
        "reference_constraints_canonical_sha256": reference_constraint_sha256,
        "mask_semantic_runtime_effect_fingerprint": runtime_effect_fingerprint,
        "current_map_canonical_sha256": current_map["canonical_sha256"],
        "reference_map_canonical_sha256": reference_map["canonical_sha256"],
        "checks": pre_cap_fingerprint_checks,
        "passed": all(pre_cap_fingerprint_checks.values()),
    }
    atomic_write_json(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json", pre_cap)
    if not all(pre_cap_fingerprint_checks.values()):
        raise RuntimeError(
            "Attempt 12 revision-03 PRE_CAP semantic/runtime-effect fingerprint drifted"
        )
    failed_constraints = [
        record
        for record in constraint_evidence
        if not all(record["attempt06_gate"].values())
    ]
    if failed_constraints:
        raise RuntimeError(
            "Attempt 06 exact midpoint/baseline/class-cap preflight failed"
        )

    count = len(vertices)
    laplacian = np.zeros((count, count), dtype=np.float64)
    for vertex in vertices:
        row = vertex_index[vertex]
        linked = sorted(neighbors[vertex], key=lambda item: int(item.index))
        laplacian[row, row] = 1.0
        reciprocal = 1.0 / len(linked)
        for neighbor in linked:
            laplacian[row, vertex_index[neighbor]] -= reciprocal
    first_energy = laplacian.T @ laplacian
    second_operator = laplacian @ laplacian
    second_energy = second_operator.T @ second_operator
    full_hessian = 18.0 * np.eye(count, dtype=np.float64)
    full_hessian += first_energy
    full_hessian += 0.20 * second_energy
    free_rows = [vertex_index[vertex] for vertex in free_vertices]
    hessian = full_hessian[np.ix_(free_rows, free_rows)].copy()
    target = np.zeros((len(free_vertices), 3), dtype=np.float64)
    severe_supports = masks["SEVERE_RING1_SUPPORTS"]
    continuation = masks["SEAM_CONTINUATION_RING2"]
    soft_records = []
    for vertex in free_vertices:
        distance = int(distances[vertex])
        if distance == 1:
            weight = RING_1_SOFT_WEIGHT
            cap, kind = attempt08_cap_for_vertex(
                vertex, severe_supports, original_ids, distance
            )
        elif distance == 2:
            cap = RING_2_CAP_M
            if vertex in continuation:
                weight = RING_2_CONTINUATION_WEIGHT
                kind = "ring_2_seam_continuation_0_70_of_ring_1"
            else:
                weight = RING_2_OTHER_WEIGHT
                kind = "ring_2_other_0_35_of_ring_1"
        else:
            continue
        requested = a09.capped_vector(
            a09.weighted_plane_target(base_world[vertex], planes), cap
        )
        row = free_index[vertex]
        hessian[row, row] += weight
        target[row, :] += weight * np.asarray(tuple(requested), dtype=np.float64)
        soft_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "graph_ring": distance,
                "kind": kind,
                "weight": weight,
                "cap_m": cap,
                "capped_target_world_m": a09.a08.vector_record(requested),
                "capped_target_length_m": float(requested.length),
            }
        )

    constraint_count = len(runtime_constraints)
    cx = np.zeros((constraint_count, len(free_vertices)), dtype=np.float64)
    cy = np.zeros_like(cx)
    cz = np.zeros_like(cx)
    right_hand_side = np.zeros(constraint_count, dtype=np.float64)
    for row, constraint in enumerate(runtime_constraints):
        support = constraint["support"]
        if support not in free_index:
            raise RuntimeError("Attempt 06 hard support is unexpectedly frozen")
        column = free_index[support]
        coefficient = constraint["coefficient"]
        cx[row, column] = float(coefficient.x)
        cy[row, column] = float(coefficient.y)
        cz[row, column] = float(coefficient.z)
        right_hand_side[row] = float(constraint["rhs"])
    try:
        unconstrained = np.linalg.solve(hessian, target)
        inverse_cx = np.linalg.solve(hessian, cx.T)
        inverse_cy = np.linalg.solve(hessian, cy.T)
        inverse_cz = np.linalg.solve(hessian, cz.T)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"Attempt 06 screened KKT base solve failed: {exc}") from exc
    schur = cx @ inverse_cx + cy @ inverse_cy + cz @ inverse_cz
    residual_target = right_hand_side - (
        cx @ unconstrained[:, 0]
        + cy @ unconstrained[:, 1]
        + cz @ unconstrained[:, 2]
    )
    try:
        multipliers = np.linalg.solve(schur, residual_target)
        schur_method = "direct_solve"
    except np.linalg.LinAlgError:
        multipliers, _residuals, rank, _singular = np.linalg.lstsq(
            schur, residual_target, rcond=None
        )
        schur_method = f"least_squares_rank_{int(rank)}"
    solved = unconstrained.copy()
    solved[:, 0] += inverse_cx @ multipliers
    solved[:, 1] += inverse_cy @ multipliers
    solved[:, 2] += inverse_cz @ multipliers
    solved_world = {vertex: Vector() for vertex in vertices}
    for vertex in free_vertices:
        solved_world[vertex] = Vector(
            tuple(float(value) for value in solved[free_index[vertex], :])
        )
    linear_residuals = (
        cx @ solved[:, 0]
        + cy @ solved[:, 1]
        + cz @ solved[:, 2]
        - right_hand_side
    )
    maximum_constraint_residual = max(
        (abs(float(value)) for value in linear_residuals), default=0.0
    )

    movements = [solved_world[vertex].length for vertex in vertices]
    distribution = displacement_distribution(movements)
    ring_distributions = {}
    for label, predicate in (
        ("ring_0", lambda d: d == 0),
        ("ring_1", lambda d: d == 1),
        ("ring_2", lambda d: d == 2),
        ("deep_interior", lambda d: d >= 3),
    ):
        ring_distributions[label] = displacement_distribution(
            [
                solved_world[vertex].length
                for vertex in vertices
                if predicate(int(distances[vertex]))
            ]
        )
    severe_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in severe_supports]
    )
    other_ring1 = {
        vertex
        for vertex in vertices
        if int(distances[vertex]) == 1 and vertex not in severe_supports
    }
    other_ring1_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in other_ring1]
    )
    exception_vertices = set(ACTIVE_EXCEPTION_CAPS)
    if len(exception_vertices) != 3:
        raise RuntimeError("Attempt 08 exact exception support set is not three")
    exception_distributions = {
        edge_label(binding["edge"]): displacement_distribution(
            [solved_world[vertex].length]
        )
        for vertex, binding in ACTIVE_EXCEPTION_CAPS.items()
    }
    default_severe = severe_supports - exception_vertices
    default_other_ring1 = other_ring1 - exception_vertices
    default_severe_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in default_severe]
    )
    default_other_ring1_distribution = displacement_distribution(
        [solved_world[vertex].length for vertex in default_other_ring1]
    )
    soft_by_vertex = {
        int(record["vertex_index_before_final_reindex"]): record
        for record in soft_records
    }
    support_movement_records = []
    pre_cap_support_identities = []
    for constraint, pre_cap_record in zip(runtime_constraints, constraint_evidence):
        vertex = constraint["support"]
        record = constraint["record"]
        edge = edge_key(record["boundary_vertex_ids"])
        classification = record["seam_class"]
        soft = soft_by_vertex.get(int(vertex.index))
        if soft is None:
            raise RuntimeError("Attempt 10 hard support has no soft-target record")
        ceiling = attempt10_postsolve_ceiling(edge, classification)
        movement = solved_world[vertex]
        coefficient = constraint["coefficient"].copy()
        rhs = float(constraint["rhs"])
        coefficient_components = exact_vector_record(coefficient)
        coefficient_norm = float(coefficient.length)
        coefficient_serialized_mathutils_norm = serialized_mathutils_norm(
            coefficient_components
        )
        coefficient_python_double_norm = serialized_python_double_norm(
            coefficient_components
        )
        minimum = Vector(
            tuple(
                float(value)
                for value in record["closest_linear_slope_minimum"][
                    "vector_world_m"
                ]
            )
        )
        minimum_components = exact_vector_record(minimum)
        movement_components = exact_vector_record(movement)
        minimum_norm = float(minimum.length)
        movement_norm = float(movement.length)
        minimum_serialized_mathutils_norm = serialized_mathutils_norm(
            minimum_components
        )
        movement_serialized_mathutils_norm = serialized_mathutils_norm(
            movement_components
        )
        minimum_python_double_norm = serialized_python_double_norm(
            minimum_components
        )
        movement_python_double_norm = serialized_python_double_norm(
            movement_components
        )
        if coefficient_norm <= 0.0 or minimum_norm <= 0.0 or movement_norm <= 0.0:
            raise RuntimeError("Attempt 10 support vector unexpectedly has zero norm")
        parallel_from_row = coefficient * (rhs / float(coefficient.length_squared))
        nullspace = movement - minimum
        parallel_components = exact_vector_record(parallel_from_row)
        nullspace_components = exact_vector_record(nullspace)
        parallel_norm = float(parallel_from_row.length)
        nullspace_norm = float(nullspace.length)
        parallel_serialized_mathutils_norm = serialized_mathutils_norm(
            parallel_components
        )
        nullspace_serialized_mathutils_norm = serialized_mathutils_norm(
            nullspace_components
        )
        parallel_python_double_norm = serialized_python_double_norm(
            parallel_components
        )
        nullspace_python_double_norm = serialized_python_double_norm(
            nullspace_components
        )
        source_endpoints = list(
            a11.authoritative_endpoint_lookup(vertex, original_ids)
        )
        identity = {
            "edge": list(edge),
            "class": classification,
            "support_vertex_index_before_final_reindex": int(vertex.index),
            "support_canonical_id": int(original_ids.get(vertex, -1)),
            "support_source_endpoint_ids": source_endpoints,
            "graph_ring": int(distances[vertex]),
        }
        pre_cap_identity = {
            "edge": list(edge_key(pre_cap_record["boundary_vertex_ids"])),
            "class": pre_cap_record["seam_class"],
            "support_vertex_index_before_final_reindex": int(
                pre_cap_record["support_vertex_index_before_final_reindex"]
            ),
            "support_canonical_id": int(pre_cap_record["support_canonical_id"]),
            "support_source_endpoint_ids": list(
                pre_cap_record["support_source_endpoint_ids"]
            ),
            "graph_ring": int(distances[vertex]),
        }
        pre_cap_support_identities.append(pre_cap_identity)
        binding = EXPECTED_CAP_BINDINGS.get(edge)
        expected_soft_cap = (
            float(binding["cap_m"])
            if binding is not None
            else (
                SEVERE_RING_1_CAP_M
                if classification == "SEVERE_FLANK_EDGES"
                else OTHER_RING_1_CAP_M
            )
        )
        expected_postsolve_ceiling = (
            POSTSOLVE_EXCEPTION_CEILINGS_M[edge]
            if binding is not None
            else (
                POSTSOLVE_DEFAULT_SEVERE_CEILING_M
                if classification == "SEVERE_FLANK_EDGES"
                else OTHER_RING_1_CAP_M
            )
        )
        expected_kind = (
            "attempt08_exact_exception_" + edge_label(edge)
            if binding is not None
            else (
                "ring_1_severe_support_2_25mm"
                if classification == "SEVERE_FLANK_EDGES"
                else "ring_1_other_1_50mm"
            )
        )
        soft_vector = Vector(
            tuple(float(value) for value in soft["capped_target_world_m"])
        )
        soft_components = exact_vector_record(soft_vector)
        soft_norm = float(soft_vector.length)
        soft_serialized_mathutils_norm = serialized_mathutils_norm(soft_components)
        soft_python_double_norm = serialized_python_double_norm(soft_components)
        row_residual = float(coefficient.dot(movement) - rhs)
        nullspace_row_residual = float(coefficient.dot(nullspace))
        closest_vs_parallel_delta = float((minimum - parallel_from_row).length)
        support_movement_records.append(
            {
                **identity,
                "pre_cap_identity_exact": identity == pre_cap_identity,
                "coefficient_world": coefficient_components,
                "coefficient_norm": coefficient_norm,
                "coefficient_serialized_mathutils_norm": coefficient_serialized_mathutils_norm,
                "coefficient_serialized_mathutils_absolute_difference": abs(
                    coefficient_serialized_mathutils_norm - coefficient_norm
                ),
                "coefficient_python_double_norm": coefficient_python_double_norm,
                "coefficient_python_double_absolute_difference": abs(
                    coefficient_python_double_norm - coefficient_norm
                ),
                "linear_row_rhs_m": rhs,
                "closest_minimum_vector_m": minimum_components,
                "closest_minimum_norm_m": minimum_norm,
                "closest_minimum_serialized_mathutils_norm_m": minimum_serialized_mathutils_norm,
                "closest_minimum_serialized_mathutils_absolute_difference_m": abs(
                    minimum_serialized_mathutils_norm - minimum_norm
                ),
                "closest_minimum_python_double_norm_m": minimum_python_double_norm,
                "closest_minimum_python_double_absolute_difference_m": abs(
                    minimum_python_double_norm - minimum_norm
                ),
                "parallel_from_row_vector_m": parallel_components,
                "parallel_from_row_norm_m": parallel_norm,
                "parallel_from_row_serialized_mathutils_norm_m": parallel_serialized_mathutils_norm,
                "parallel_from_row_serialized_mathutils_absolute_difference_m": abs(
                    parallel_serialized_mathutils_norm - parallel_norm
                ),
                "parallel_from_row_python_double_norm_m": parallel_python_double_norm,
                "parallel_from_row_python_double_absolute_difference_m": abs(
                    parallel_python_double_norm - parallel_norm
                ),
                "closest_minimum_vs_parallel_delta_m": closest_vs_parallel_delta,
                "applied_kkt_vector_m": movement_components,
                "applied_kkt_norm_m": movement_norm,
                "applied_kkt_serialized_mathutils_norm_m": movement_serialized_mathutils_norm,
                "applied_kkt_serialized_mathutils_absolute_difference_m": abs(
                    movement_serialized_mathutils_norm - movement_norm
                ),
                "applied_kkt_python_double_norm_m": movement_python_double_norm,
                "applied_kkt_python_double_absolute_difference_m": abs(
                    movement_python_double_norm - movement_norm
                ),
                "linear_row_residual_m": row_residual,
                "nullspace_vector_m": nullspace_components,
                "nullspace_norm_m": nullspace_norm,
                "nullspace_serialized_mathutils_norm_m": nullspace_serialized_mathutils_norm,
                "nullspace_serialized_mathutils_absolute_difference_m": abs(
                    nullspace_serialized_mathutils_norm - nullspace_norm
                ),
                "nullspace_python_double_norm_m": nullspace_python_double_norm,
                "nullspace_python_double_absolute_difference_m": abs(
                    nullspace_python_double_norm - nullspace_norm
                ),
                "coefficient_dot_nullspace_m": nullspace_row_residual,
                "nullspace_to_kkt_norm_ratio": nullspace_norm / movement_norm,
                "kkt_norm_over_closest_minimum": movement_norm / minimum_norm,
                "soft_target_vector_m": soft_components,
                "soft_target_norm_m": soft_norm,
                "soft_target_serialized_mathutils_norm_m": soft_serialized_mathutils_norm,
                "soft_target_serialized_mathutils_absolute_difference_m": abs(
                    soft_serialized_mathutils_norm - soft_norm
                ),
                "soft_target_python_double_norm_m": soft_python_double_norm,
                "soft_target_python_double_absolute_difference_m": abs(
                    soft_python_double_norm - soft_norm
                ),
                "soft_target_cap_m": float(soft["cap_m"]),
                "soft_target_weight": float(soft["weight"]),
                "soft_target_kind": soft["kind"],
                "postsolve_ceiling_m": float(ceiling),
                "cap_mapping_exact": float(soft["cap_m"])
                == float(expected_soft_cap)
                and float(soft["weight"]) == float(RING_1_SOFT_WEIGHT)
                and soft["kind"] == expected_kind
                and float(ceiling) == float(expected_postsolve_ceiling),
                "within_postsolve_ceiling": movement_norm
                <= float(ceiling) + a09.MOVEMENT_EPSILON_M,
            }
        )
    support_identity_exact = [
        {
            key: record[key]
            for key in (
                "edge",
                "class",
                "support_vertex_index_before_final_reindex",
                "support_canonical_id",
                "support_source_endpoint_ids",
                "graph_ring",
            )
        }
        for record in support_movement_records
    ] == pre_cap_support_identities
    support_coefficient_norms_recompute = all(
        abs(
            serialized_mathutils_norm(record["coefficient_world"])
            - float(record["coefficient_norm"])
        )
        <= COEFFICIENT_NORM_TOLERANCE
        for record in support_movement_records
    )
    support_metric_vector_norms_recompute = all(
        abs(
            serialized_mathutils_norm(record[vector_key])
            - float(record[norm_key])
        )
        <= FINGERPRINT_FLOAT_TOLERANCE_M
        for record in support_movement_records
        for vector_key, norm_key in (
            ("closest_minimum_vector_m", "closest_minimum_norm_m"),
            ("parallel_from_row_vector_m", "parallel_from_row_norm_m"),
            ("applied_kkt_vector_m", "applied_kkt_norm_m"),
            ("nullspace_vector_m", "nullspace_norm_m"),
            ("soft_target_vector_m", "soft_target_norm_m"),
        )
    )
    if (
        len(support_movement_records) != len(runtime_constraints)
        or len(
            {
                record["support_vertex_index_before_final_reindex"]
                for record in support_movement_records
            }
        )
        != len(support_movement_records)
        or len({tuple(record["edge"]) for record in support_movement_records})
        != len(support_movement_records)
        or any(
            record["graph_ring"] != 1 for record in support_movement_records
        )
        or not support_identity_exact
    ):
        raise RuntimeError("Attempt 10 support movement evidence binding failed")
    pre_apply_checks = {
        "inherited_a09_ring1_cap_exactly_2_40mm": a09.RING_1_CAP_M
        == INHERITED_RING_1_CAP_M,
        "inherited_a09_total_base_fit_cap_exactly_2_40mm": a09.TOTAL_BASE_FIT_CAP_M
        == INHERITED_TOTAL_BASE_FIT_CAP_M,
        "all_27_support_identities_exactly_match_pre_cap": support_identity_exact,
        "all_27_support_records_finite": all_finite(support_movement_records),
        "all_support_serialized_coefficient_norms_recompute_within_1e_12": support_coefficient_norms_recompute,
        "all_support_serialized_metric_vector_norms_recompute_within_1pm": support_metric_vector_norms_recompute,
        "all_support_linear_row_residuals_at_most_20nm": all(
            abs(float(record["linear_row_residual_m"]))
            <= CONSTRAINT_RESIDUAL_TOLERANCE_M
            for record in support_movement_records
        ),
        "all_support_nullspace_row_residuals_at_most_20nm": all(
            abs(float(record["coefficient_dot_nullspace_m"]))
            <= CONSTRAINT_RESIDUAL_TOLERANCE_M
            for record in support_movement_records
        ),
        "all_support_soft_and_postsolve_cap_mappings_exact": all(
            bool(record["cap_mapping_exact"])
            for record in support_movement_records
        ),
        "linear_constraint_residual_at_most_20nm": maximum_constraint_residual
        <= CONSTRAINT_RESIDUAL_TOLERANCE_M,
        "boundary_displacement_exact_zero": float(
            ring_distributions["ring_0"]["maximum_m"]
        )
        <= a09.MOVEMENT_EPSILON_M,
        "default_severe_ring1_postsolve_ceiling_2_330mm": float(
            default_severe_distribution["maximum_m"]
        )
        <= POSTSOLVE_DEFAULT_SEVERE_CEILING_M + a09.MOVEMENT_EPSILON_M,
        "default_other_ring1_cap_1_50mm": float(
            default_other_ring1_distribution["maximum_m"]
        )
        <= OTHER_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        **{
            "exception_" + edge_label(binding["edge"]) + "_postsolve_ceiling": float(
                exception_distributions[edge_label(binding["edge"])]["maximum_m"]
            )
            <= POSTSOLVE_EXCEPTION_CEILINGS_M[binding["edge"]]
            + a09.MOVEMENT_EPSILON_M
            for vertex, binding in ACTIVE_EXCEPTION_CAPS.items()
        },
        "all_hard_support_records_within_postsolve_ceiling": all(
            record["within_postsolve_ceiling"]
            for record in support_movement_records
        ),
        "ring2_cap_0_90mm": float(ring_distributions["ring_2"]["maximum_m"])
        <= RING_2_CAP_M + a09.MOVEMENT_EPSILON_M,
        "deep_cap_0_60mm": float(
            ring_distributions["deep_interior"]["maximum_m"]
        )
        <= DEEP_CAP_M + a09.MOVEMENT_EPSILON_M,
        "overall_postsolve_ceiling_2_525mm": float(
            distribution["maximum_m"]
        )
        <= POSTSOLVE_OVERALL_CEILING_M + a09.MOVEMENT_EPSILON_M,
        "p95_cap_0_90mm": float(distribution["p95_m"])
        <= P95_CAP_M + a09.MOVEMENT_EPSILON_M,
        "rms_postsolve_ceiling_0_460mm": float(distribution["rms_m"])
        <= POSTSOLVE_RMS_CEILING_M + a09.MOVEMENT_EPSILON_M,
    }
    solver_base = {
        "schema": "kira.avatar.r24.a09_attempt06.solver_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "ACTIVE_CLASS_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "hessian_dimension": len(free_vertices),
        "constraint_count": constraint_count,
        "schur_method": schur_method,
        "maximum_constraint_residual_m": maximum_constraint_residual,
        "lagrange_multipliers": [float(value) for value in multipliers],
        "soft_constraint_records": soft_records,
        "distribution": distribution,
        "ring_distributions": ring_distributions,
        "severe_ring1_distribution": severe_distribution,
        "other_ring1_distribution": other_ring1_distribution,
        "attempt08_exception_distributions": exception_distributions,
        "attempt08_default_severe_ring1_distribution": default_severe_distribution,
        "attempt08_default_other_ring1_distribution": default_other_ring1_distribution,
        "attempt10_support_movement_records": support_movement_records,
        "attempt10_postsolve_policy": {
            "default_severe_m": POSTSOLVE_DEFAULT_SEVERE_CEILING_M,
            "exceptions_m": {
                edge_label(edge): value
                for edge, value in POSTSOLVE_EXCEPTION_CEILINGS_M.items()
            },
            "overall_m": POSTSOLVE_OVERALL_CEILING_M,
            "rms_m": POSTSOLVE_RMS_CEILING_M,
            "soft_target_caps_changed": False,
        },
        "masks": mask_evidence,
        "attempt08_exact_cap_policy": attempt08_cap_policy_evidence(
            distances, original_ids
        ),
        "exception_distributions": exception_distributions,
        "default_severe_ring1_distribution": default_severe_distribution,
        "default_other_ring1_distribution": default_other_ring1_distribution,
    }
    solver_fingerprint = attempt12_revision03_solver_fingerprint(solver_base)
    legacy_attempt09_checks = {
        "default_severe_at_most_2_25mm": float(
            default_severe_distribution["maximum_m"]
        )
        <= SEVERE_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        "default_other_at_most_1_50mm": float(
            default_other_ring1_distribution["maximum_m"]
        )
        <= OTHER_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
        "edge_1009_2398_at_most_2_00mm": float(
            exception_distributions["1009_2398"]["maximum_m"]
        )
        <= 0.00200 + a09.MOVEMENT_EPSILON_M,
        "edge_1097_1529_at_most_2_40mm": float(
            exception_distributions["1097_1529"]["maximum_m"]
        )
        <= 0.00240 + a09.MOVEMENT_EPSILON_M,
        "edge_2481_2861_at_most_2_40mm": float(
            exception_distributions["2481_2861"]["maximum_m"]
        )
        <= 0.00240 + a09.MOVEMENT_EPSILON_M,
        "overall_at_most_2_40mm": float(distribution["maximum_m"])
        <= INHERITED_TOTAL_BASE_FIT_CAP_M + a09.MOVEMENT_EPSILON_M,
        "rms_at_most_0_45mm": float(distribution["rms_m"])
        <= RMS_CAP_M + a09.MOVEMENT_EPSILON_M,
    }
    legacy_attempt09_cap_comparisons = {
        "status": "WARNING_ONLY_PRESERVED_FAILURE_TRUTH_NOT_AUTO_ACCEPTANCE",
        "all_legacy_caps_pass": all(legacy_attempt09_checks.values()),
        "checks": legacy_attempt09_checks,
        "observed_m": {
            "default_severe_maximum": float(
                default_severe_distribution["maximum_m"]
            ),
            "default_other_maximum": float(
                default_other_ring1_distribution["maximum_m"]
            ),
            "edge_1009_2398": float(
                exception_distributions["1009_2398"]["maximum_m"]
            ),
            "edge_1097_1529": float(
                exception_distributions["1097_1529"]["maximum_m"]
            ),
            "edge_2481_2861": float(
                exception_distributions["2481_2861"]["maximum_m"]
            ),
            "overall_maximum": float(distribution["maximum_m"]),
            "rms": float(distribution["rms_m"]),
        },
        "legacy_caps_m": {
            "default_severe": SEVERE_RING_1_CAP_M,
            "default_other": OTHER_RING_1_CAP_M,
            "edge_1009_2398": 0.00200,
            "edge_1097_1529": 0.00240,
            "edge_2481_2861": 0.00240,
            "overall": INHERITED_TOTAL_BASE_FIT_CAP_M,
            "rms": RMS_CAP_M,
        },
        "not_used_as_revision01_acceptance": True,
    }
    pre_apply_checks[
        "attempt12_revision03_solver_semantic_runtime_effect_fingerprint_before_geometry"
    ] = solver_fingerprint["passed"]
    solver_base["attempt12_revision03_solver_fingerprint"] = solver_fingerprint
    solver_base["legacy_attempt09_cap_comparisons"] = (
        legacy_attempt09_cap_comparisons
    )
    solver_base["attempt10_revision01_support_evidence"] = {
        "count": len(support_movement_records),
        "canonical_sha256": canonical_sha256(support_movement_records),
        "records": support_movement_records,
        "nullspace_magnitudes_are_measurements_not_auto_acceptance": True,
    }
    if not all(pre_apply_checks.values()):
        atomic_write_json(
            ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json",
            {
                **solver_base,
                "status": "FAIL_CLOSED_BEFORE_GEOMETRY_APPLICATION",
                "checks": pre_apply_checks,
            },
        )
        failed_check_names = sorted(
            name for name, passed in pre_apply_checks.items() if not passed
        )
        raise RuntimeError(
            "Attempt 13 pre-geometry solver/evidence gates failed: "
            + ", ".join(failed_check_names)
        )

    world_to_local = body.matrix_world.inverted().to_3x3()
    for vertex in vertices:
        vertex.co = base_local[vertex] + world_to_local @ solved_world[vertex]
    for vertex in seam_vertices:
        vertex.co = base_local[vertex].copy()
    bm.normal_update()
    shape = a09.local_shape_quality(body, patch_faces, baseline_normals)
    seam = a09.a08.seam_edge_records(
        body, patch_faces, seam_edges, original_ids, parameters
    )
    class_values = {name: [] for name in TARGET_BY_CLASS}
    class_records = []
    for record in seam["records"]:
        key = edge_key(record["boundary_vertex_ids"])
        classification = edge_class(key)
        value = float(record["normal_dot"])
        class_values[classification].append(value)
        class_records.append(
            {
                "edge": list(key),
                "class": classification,
                "target_dot": TARGET_BY_CLASS[classification],
                "achieved_dot": value,
                "passed": value >= TARGET_BY_CLASS[classification],
            }
        )
    seam_values = [float(record["normal_dot"]) for record in seam["records"]]
    seam_minimum = min(seam_values, default=-1.0)
    seam_median = statistics.median(seam_values) if seam_values else -1.0
    seam_dihedral = math.degrees(math.acos(max(-1.0, min(1.0, seam_minimum))))
    intersections = a09.exact_patch_intersection_summary(bm, patch_faces)
    post_checks = {
        **pre_apply_checks,
        "orientation_preserved": bool(shape["orientations_preserved"]),
        "nondegenerate": float(shape["minimum_face_area_world_m2"]) > 1.0e-10,
        "edge_ratio_at_most_8": float(shape["maximum_edge_ratio"])
        <= a09.MAXIMUM_EDGE_RATIO,
        "patch_exact_intersections_zero": intersections["patch_genuine_pair_count"]
        == 0,
        "whole_exact_intersections_29": intersections["whole_genuine_pair_count"]
        == a09.INHERITED_WHOLE_INTERSECTIONS,
        "superior_all_at_least_0_985": min(
            class_values["SUPERIOR_JOIN_EDGES"], default=-1.0
        )
        >= 0.985,
        "severe_all_at_least_0_900": min(
            class_values["SEVERE_FLANK_EDGES"], default=-1.0
        )
        >= 0.900,
        "regular_all_at_least_0_965": min(
            class_values["REGULAR_FLANK_EDGES"], default=-1.0
        )
        >= 0.965,
        "whole_seam_minimum_at_least_0_900": seam_minimum >= 0.900,
        "whole_seam_median_at_least_0_965": seam_median >= 0.965,
        "whole_seam_dihedral_at_most_25_841933": seam_dihedral <= 25.841933,
    }
    solver_diagnostic = {
        **solver_base,
        "status": (
            "BASE_FIT_HARD_GATES_PASS"
            if all(post_checks.values())
            else "BASE_FIT_HARD_GATE_FAILURE"
        ),
        "shape": shape,
        "seam_minimum_dot": seam_minimum,
        "seam_median_dot": seam_median,
        "maximum_seam_dihedral_degrees": seam_dihedral,
        "seam_class_records": class_records,
        "intersections": intersections,
        "checks": post_checks,
    }
    atomic_write_json(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json", solver_diagnostic)
    if not all(post_checks.values()):
        for vertex in vertices:
            vertex.co = base_local[vertex].copy()
        bm.normal_update()
        raise RuntimeError("Attempt 06 base fit failed an exact structural gate")

    selected_by_support = {
        int(constraint["support"].index): constraint["record"]
        for constraint in runtime_constraints
    }
    movement_records = []
    for vertex in vertices:
        displacement = solved_world[vertex]
        if displacement.length <= a09.MOVEMENT_EPSILON_M:
            continue
        selected = selected_by_support.get(int(vertex.index))
        movement_records.append(
            {
                "vertex_index_before_final_reindex": int(vertex.index),
                "original_vertex_id": int(original_ids.get(vertex, -1)),
                "graph_ring": int(distances[vertex]),
                "boundary_vertex_ids": (
                    list(selected["boundary_vertex_ids"])
                    if selected is not None
                    else []
                ),
                "selected_hard_seam_support": selected is not None,
                "applied_world_vector_m": a09.a08.vector_record(displacement),
                "applied_world_m": float(displacement.length),
            }
        )
    accepted_trial = {
        "scale": 1.0,
        "passed": True,
        "checks": post_checks,
        "shape": shape,
        "seam_minimum_dot": seam_minimum,
        "seam_median_dot": seam_median,
        "maximum_seam_dihedral_degrees": seam_dihedral,
        "intersections": intersections,
        "distribution": distribution,
        "ring_maxima_m": {
            "0": float(ring_distributions["ring_0"]["maximum_m"]),
            "1": float(ring_distributions["ring_1"]["maximum_m"]),
            "2": float(ring_distributions["ring_2"]["maximum_m"]),
            "deep": float(ring_distributions["deep_interior"]["maximum_m"]),
        },
    }
    RELIEF_SEQUENCE = deque(
        {
            "vertex_index_before_final_reindex": int(vertex.index),
            "canonical_original_id": int(original_ids.get(vertex, -1)),
            "source_endpoint_ids": list(
                a11.AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.get(vertex, ())
            ),
            "graph_ring": int(distances[vertex]),
            "u": float(parameters[vertex][0]),
            "t": float(parameters[vertex][1]),
            "central_positive_relief": vertex
            in masks["CENTRAL_POSITIVE_RELIEF"],
        }
        for vertex in vertices
    )
    a14.RELIEF_SEQUENCE = RELIEF_SEQUENCE
    return {
        "method": "ACTIVE_CLASS_LINEAR_SEAM_SLOPE_SCHUR_KKT_COUPLED_L_L2_V1",
        "absolute_position_minimal_surface_solve_used": False,
        "laplacian_shape": list(map(int, laplacian.shape)),
        "free_hessian_shape": list(map(int, hessian.shape)),
        "fidelity_weight": 18.0,
        "first_differential_weight": 1.0,
        "biharmonic_weight": 0.20,
        "ring_1_soft_constraint_weight": RING_1_SOFT_WEIGHT,
        "ring_2_continuation_weight": RING_2_CONTINUATION_WEIGHT,
        "ring_2_other_weight": RING_2_OTHER_WEIGHT,
        "selected_hard_constraint_count": constraint_count,
        "selected_hard_constraints": constraint_evidence,
        "constraint_records": constraint_evidence,
        "linear_constraint_maximum_residual_m": maximum_constraint_residual,
        "schur_method": schur_method,
        "backtracking_used": False,
        "backtracking_reason": "scaling would invalidate active hard seam rows",
        "backtracking_trials": [accepted_trial],
        "accepted_trial": accepted_trial,
        "movement_records": movement_records,
        "movement_distribution": distribution,
        "ring_distributions": ring_distributions,
        "severe_ring1_distribution": severe_distribution,
        "other_ring1_distribution": other_ring1_distribution,
        "attempt08_exception_distributions": exception_distributions,
        "attempt08_default_severe_ring1_distribution": default_severe_distribution,
        "attempt08_default_other_ring1_distribution": default_other_ring1_distribution,
        "attempt08_exact_cap_policy": attempt08_cap_policy_evidence(
            distances, original_ids
        ),
        "attempt10_support_movement_records": support_movement_records,
        "attempt10_postsolve_policy": {
            "default_severe_m": POSTSOLVE_DEFAULT_SEVERE_CEILING_M,
            "exceptions_m": {
                edge_label(edge): value
                for edge, value in POSTSOLVE_EXCEPTION_CEILINGS_M.items()
            },
            "overall_m": POSTSOLVE_OVERALL_CEILING_M,
            "rms_m": POSTSOLVE_RMS_CEILING_M,
            "soft_target_caps_changed": False,
        },
        "targeted_support_vertex_count": constraint_count,
        "all_other_fairing_displacement_zero": len(movement_records)
        == constraint_count,
        "maximum_support_movement_m": max(
            (
                float(record["applied_world_m"])
                for record in movement_records
                if record["selected_hard_seam_support"]
            ),
            default=0.0,
        ),
        "maximum_ring_2_applied_world_m": float(
            ring_distributions["ring_2"]["maximum_m"]
        ),
        "sharp_boundary_edges_cleared": False,
        "boundary_displacement_exact_zero": bool(
            pre_apply_checks["boundary_displacement_exact_zero"]
        ),
        "caps_m": {
            "default_severe_ring_1": SEVERE_RING_1_CAP_M,
            "default_other_ring_1": OTHER_RING_1_CAP_M,
            "attempt08_exact_support_overrides": {
                edge_label(binding["edge"]): float(binding["cap_m"])
                for binding in ACTIVE_EXCEPTION_CAPS.values()
            },
            "ring_2": RING_2_CAP_M,
            "deep_interior": DEEP_CAP_M,
            "overall_exact_exception_ceiling": OVERALL_CAP_M,
            "p95": P95_CAP_M,
            "rms": RMS_CAP_M,
        },
        "mask_evidence": mask_evidence,
        "seam_class_records": class_records,
    }

def attempt08_zero_relief_evidence():
    fades = {}
    relief = {}
    for record in a14.FADE_RECORDS:
        fades.setdefault(
            int(record["vertex_index_before_final_reindex"]), []
        ).append(record)
    for record in a14.RELIEF_RECORDS:
        relief.setdefault(
            int(record["vertex_index_before_final_reindex"]), []
        ).append(record)
    records = []
    passed = True
    for binding in EXPECTED_CAP_BINDINGS.values():
        index = int(binding["support_vertex_index_before_final_reindex"])
        fade_records = fades.get(index, [])
        relief_records = relief.get(index, [])
        exact = (
            len(fade_records) == 1
            and len(relief_records) == 1
            and int(fade_records[0]["graph_ring"]) == 1
            and float(fade_records[0]["new_fade"]) == 0.0
            and int(relief_records[0]["graph_ring"]) == 1
            and not bool(relief_records[0]["central_positive_relief"])
        )
        passed = passed and exact
        records.append(
            {
                "edge": list(next(
                    edge for edge, expected in EXPECTED_CAP_BINDINGS.items()
                    if expected is binding
                )),
                "support_vertex_index_before_final_reindex": index,
                "fade_record_count": len(fade_records),
                "relief_record_count": len(relief_records),
                "graph_ring": (
                    int(fade_records[0]["graph_ring"])
                    if len(fade_records) == 1
                    else None
                ),
                "new_fade": (
                    float(fade_records[0]["new_fade"])
                    if len(fade_records) == 1
                    else None
                ),
                "central_positive_relief": (
                    bool(relief_records[0]["central_positive_relief"])
                    if len(relief_records) == 1
                    else None
                ),
                "applied_relief_is_exact_zero": exact,
            }
        )
    return {"passed": passed, "records": records}


def attempt08_gates(body, applied):
    result = a14.attempt06_gates(body, applied)
    checks = dict(result["checks"])
    obsolete = {
        "attempt06_severe_ring1_at_most_2_25mm",
        "attempt06_other_ring1_at_most_1_50mm",
        "attempt06_base_fit_overall_at_most_2_25mm",
    }
    if not obsolete <= set(checks):
        raise RuntimeError("Attempt 08 could not find all replaced class-wide gates")
    for name in obsolete:
        checks.pop(name)
    base_fit = applied["base_fit"]
    exception_distributions = base_fit["attempt08_exception_distributions"]
    zero_relief = attempt08_zero_relief_evidence()
    checks.update(
        {
            "attempt08_exact_exception_count_three": len(
                exception_distributions
            )
            == 3,
            "attempt08_edge_1009_2398_at_most_2_00mm": float(
                exception_distributions["1009_2398"]["maximum_m"]
            )
            <= 0.00200 + a09.MOVEMENT_EPSILON_M,
            "attempt08_edge_1097_1529_at_most_2_40mm": float(
                exception_distributions["1097_1529"]["maximum_m"]
            )
            <= 0.00240 + a09.MOVEMENT_EPSILON_M,
            "attempt08_edge_2481_2861_at_most_2_40mm": float(
                exception_distributions["2481_2861"]["maximum_m"]
            )
            <= 0.00240 + a09.MOVEMENT_EPSILON_M,
            "attempt08_default_severe_at_most_2_25mm": float(
                base_fit[
                    "attempt08_default_severe_ring1_distribution"
                ]["maximum_m"]
            )
            <= SEVERE_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt08_default_other_ring1_at_most_1_50mm": float(
                base_fit[
                    "attempt08_default_other_ring1_distribution"
                ]["maximum_m"]
            )
            <= OTHER_RING_1_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt08_overall_base_fit_at_most_2_40mm": float(
                base_fit["movement_distribution"]["maximum_m"]
            )
            <= OVERALL_CAP_M + a09.MOVEMENT_EPSILON_M,
            "attempt08_all_three_exception_relief_exact_zero": zero_relief[
                "passed"
            ],
            "attempt08_combined_at_most_4_5mm": float(
                applied["combined_displacement"]["maximum_m"]
            )
            <= COMBINED_CAP_M + a09.MOVEMENT_EPSILON_M,
        }
    )
    result["checks"] = checks
    result["passed"] = all(checks.values())
    result["attempt08"] = {
        "exact_cap_policy": base_fit["attempt08_exact_cap_policy"],
        "zero_relief_evidence": zero_relief,
        "exception_distributions": exception_distributions,
        "default_severe_ring1_distribution": base_fit[
            "attempt08_default_severe_ring1_distribution"
        ],
        "default_other_ring1_distribution": base_fit[
            "attempt08_default_other_ring1_distribution"
        ],
    }
    return result


def attempt10_all_support_zero_relief_evidence(base_fit):
    fades = {}
    relief = {}
    for record in a14.FADE_RECORDS:
        fades.setdefault(
            int(record["vertex_index_before_final_reindex"]), []
        ).append(record)
    for record in a14.RELIEF_RECORDS:
        relief.setdefault(
            int(record["vertex_index_before_final_reindex"]), []
        ).append(record)
    records = []
    passed = True
    for support in base_fit["attempt10_support_movement_records"]:
        index = int(support["support_vertex_index_before_final_reindex"])
        fade_records = fades.get(index, [])
        relief_records = relief.get(index, [])
        fade = fade_records[0] if len(fade_records) == 1 else None
        relief_record = relief_records[0] if len(relief_records) == 1 else None
        adjusted_offset = (
            float(relief_record["adjusted_offset_before_fade_m"])
            if relief_record is not None
            and "adjusted_offset_before_fade_m" in relief_record
            else None
        )
        new_fade = (
            float(fade["new_fade"])
            if fade is not None and "new_fade" in fade
            else None
        )
        applied_relief = (
            adjusted_offset * new_fade
            if adjusted_offset is not None and new_fade is not None
            else None
        )
        identity_exact = (
            support["graph_ring"] == 1
            and fade is not None
            and relief_record is not None
            and int(fade["vertex_index_before_final_reindex"]) == index
            and int(relief_record["vertex_index_before_final_reindex"]) == index
            and int(relief_record["canonical_original_id"])
            == int(support["support_canonical_id"])
            and list(relief_record.get("source_endpoint_ids", []))
            == list(support["support_source_endpoint_ids"])
            and int(fade["graph_ring"]) == 1
            and int(relief_record["graph_ring"]) == 1
        )
        exact = (
            identity_exact
            and all_finite(fade)
            and all_finite(relief_record)
            and adjusted_offset is not None
            and math.isfinite(adjusted_offset)
            and new_fade is not None
            and math.isfinite(new_fade)
            and new_fade == 0.0
            and not bool(relief_record["central_positive_relief"])
            and applied_relief == 0.0
        )
        passed = passed and exact
        records.append(
            {
                "edge": support["edge"],
                "class": support["class"],
                "support_vertex_index_before_final_reindex": index,
                "support_canonical_id": support["support_canonical_id"],
                "support_source_endpoint_ids": support[
                    "support_source_endpoint_ids"
                ],
                "graph_ring": support["graph_ring"],
                "fade_record_count": len(fade_records),
                "relief_record_count": len(relief_records),
                "identity_exact": identity_exact,
                "new_fade": new_fade,
                "adjusted_offset_before_fade_m": adjusted_offset,
                "central_positive_relief": (
                    bool(relief_record["central_positive_relief"])
                    if relief_record is not None
                    else None
                ),
                "applied_relief_m": applied_relief,
                "all_numbers_finite": all_finite(fade)
                and all_finite(relief_record)
                and adjusted_offset is not None
                and math.isfinite(adjusted_offset)
                and new_fade is not None
                and math.isfinite(new_fade),
                "adjusted_offset_times_fade_exact_zero": applied_relief == 0.0,
                "applied_relief_is_exact_zero": exact,
            }
        )
    return {
        "passed": passed
        and len(records) == 27
        and len(
            {
                record["support_vertex_index_before_final_reindex"]
                for record in records
            }
        )
        == 27,
        "all_exact_identities_unique": len(
            {
                (
                    tuple(record["edge"]),
                    record["support_vertex_index_before_final_reindex"],
                    record["support_canonical_id"],
                    tuple(record["support_source_endpoint_ids"]),
                )
                for record in records
            }
        )
        == 27,
        "identity_count": len(
            {
                (
                    tuple(record["edge"]),
                    record["support_vertex_index_before_final_reindex"],
                    record["support_canonical_id"],
                    tuple(record["support_source_endpoint_ids"]),
                )
                for record in records
            }
        ),
        "count": len(records),
        "records_canonical_sha256": canonical_sha256(records),
        "records": records,
    }


def attempt10_gates(body, applied):
    result = attempt08_gates(body, applied)
    checks = dict(result["checks"])
    replaced = {
        "attempt08_edge_1009_2398_at_most_2_00mm",
        "attempt08_edge_1097_1529_at_most_2_40mm",
        "attempt08_edge_2481_2861_at_most_2_40mm",
        "attempt08_default_severe_at_most_2_25mm",
        "attempt08_overall_base_fit_at_most_2_40mm",
        "attempt08_all_three_exception_relief_exact_zero",
        "base_fit_rms_at_most_0_45mm",
    }
    if not replaced <= set(checks):
        raise RuntimeError("Attempt 10 could not find every replaced Attempt 08 gate")
    for name in replaced:
        checks.pop(name)
    base_fit = applied["base_fit"]
    exceptions = base_fit["attempt08_exception_distributions"]
    all_support_relief = attempt10_all_support_zero_relief_evidence(base_fit)
    checks.update(
        {
            "attempt10_edge_1009_2398_at_most_2_010mm": float(
                exceptions["1009_2398"]["maximum_m"]
            )
            <= POSTSOLVE_EXCEPTION_CEILINGS_M[(1009, 2398)]
            + a09.MOVEMENT_EPSILON_M,
            "attempt10_edge_1097_1529_at_most_2_525mm": float(
                exceptions["1097_1529"]["maximum_m"]
            )
            <= POSTSOLVE_EXCEPTION_CEILINGS_M[(1097, 1529)]
            + a09.MOVEMENT_EPSILON_M,
            "attempt10_edge_2481_2861_at_most_2_480mm": float(
                exceptions["2481_2861"]["maximum_m"]
            )
            <= POSTSOLVE_EXCEPTION_CEILINGS_M[(2481, 2861)]
            + a09.MOVEMENT_EPSILON_M,
            "attempt10_default_severe_at_most_2_330mm": float(
                base_fit[
                    "attempt08_default_severe_ring1_distribution"
                ]["maximum_m"]
            )
            <= POSTSOLVE_DEFAULT_SEVERE_CEILING_M + a09.MOVEMENT_EPSILON_M,
            "attempt10_overall_base_fit_at_most_2_525mm": float(
                base_fit["movement_distribution"]["maximum_m"]
            )
            <= POSTSOLVE_OVERALL_CEILING_M + a09.MOVEMENT_EPSILON_M,
            "attempt10_rms_at_most_0_460mm": float(
                base_fit["movement_distribution"]["rms_m"]
            )
            <= POSTSOLVE_RMS_CEILING_M + a09.MOVEMENT_EPSILON_M,
            "attempt10_all_27_supports_relief_exact_zero": all_support_relief[
                "passed"
            ],
            "attempt10_all_27_zero_relief_identities_unique": all_support_relief[
                "all_exact_identities_unique"
            ],
        }
    )
    result["checks"] = checks
    result["passed"] = all(checks.values())
    result["attempt10"] = {
        "postsolve_policy": base_fit["attempt10_postsolve_policy"],
        "support_movement_records": base_fit[
            "attempt10_support_movement_records"
        ],
        "all_support_zero_relief": all_support_relief,
    }
    return result


def next_append_only_output() -> Path:
    """Resolve the next attempt slot without creating it."""

    indexes = []
    if OUTPUT_ROOT.is_dir():
        for child in OUTPUT_ROOT.iterdir():
            if child.is_dir() and child.name.startswith("attempt_"):
                try:
                    indexes.append(int(child.name.split("_")[-1]))
                except ValueError:
                    continue
    return OUTPUT_ROOT / f"attempt_{max(indexes, default=0) + 1:02d}"


def main() -> None:
    global ACTIVE_OUTPUT, RELIEF_SEQUENCE
    worker = Path(__file__).resolve()
    if SOURCE_SHA256 != BOUND_SOURCE_SHA256:
        raise RuntimeError("Attempt 13 revision-04 inherited sealed-source hash drifted")
    for path, expected, label in (
        (SOURCE, SOURCE_SHA256, "sealed R19 source"),
        (SEMANTIC_HELPER, SEMANTIC_HELPER_SHA256, "revision-02 semantic helper"),
        (
            RUNTIME_EFFECT_HELPER,
            RUNTIME_EFFECT_HELPER_SHA256,
            "revision-03 runtime-effect helper",
        ),
        (
            a09.A08_WORKER,
            a09.A08_WORKER_SHA256,
            "preserved A08 feature-formula worker",
        ),
        (ATTEMPT_07_WORKER, ATTEMPT_07_WORKER_SHA256, "attempt_07 worker"),
        (ATTEMPT_07_PRE_MASK, ATTEMPT_07_PRE_MASK_SHA256, "attempt_07 pre-mask"),
        (ATTEMPT_07_PRE_CAP, ATTEMPT_07_PRE_CAP_SHA256, "attempt_07 pre-cap"),
        (ATTEMPT_07_FAILURE, ATTEMPT_07_FAILURE_SHA256, "attempt_07 failure"),
        (ATTEMPT_07_DIAGNOSIS, ATTEMPT_07_DIAGNOSIS_SHA256, "attempt_07 diagnosis"),
        (ATTEMPT_08_PROPOSAL, ATTEMPT_08_PROPOSAL_SHA256, "attempt_08 cap proposal"),
        (ATTEMPT_08_WORKER, ATTEMPT_08_WORKER_SHA256, "attempt_08 worker"),
        (ATTEMPT_08_STDOUT, ATTEMPT_08_STDOUT_SHA256, "attempt_08 stdout/stderr"),
        (ATTEMPT_08_FAILURE, ATTEMPT_08_FAILURE_SHA256, "attempt_08 failure"),
        (ATTEMPT_09_PROPOSAL, ATTEMPT_09_PROPOSAL_SHA256, "attempt_09 startup proposal"),
        (ATTEMPT_09_WORKER, ATTEMPT_09_WORKER_SHA256, "attempt_09 worker"),
        (ATTEMPT_09_PRE_MASK, ATTEMPT_09_PRE_MASK_SHA256, "attempt_09 pre-mask"),
        (ATTEMPT_09_PRE_CAP, ATTEMPT_09_PRE_CAP_SHA256, "attempt_09 pre-cap"),
        (ATTEMPT_09_SOLVER, ATTEMPT_09_SOLVER_SHA256, "attempt_09 solver"),
        (ATTEMPT_09_FAILURE, ATTEMPT_09_FAILURE_SHA256, "attempt_09 failure"),
        (ATTEMPT_09_DIAGNOSIS, ATTEMPT_09_DIAGNOSIS_SHA256, "attempt_09 diagnosis"),
        (ATTEMPT_10_PROPOSAL, ATTEMPT_10_PROPOSAL_SHA256, "attempt_10 proposal"),
        (
            REJECTED_ATTEMPT_10_WORKER,
            REJECTED_ATTEMPT_10_WORKER_SHA256,
            "rejected attempt_10 worker proposal",
        ),
        (
            REJECTED_ATTEMPT_10_CHECKPOINT,
            REJECTED_ATTEMPT_10_CHECKPOINT_SHA256,
            "rejected attempt_10 static checkpoint",
        ),
        (REVISION01_WORKER, REVISION01_WORKER_SHA256, "attempt_10 revision-01 worker"),
        (ATTEMPT_10_PRE_MASK, ATTEMPT_10_PRE_MASK_SHA256, "attempt_10 pre-mask"),
        (ATTEMPT_10_PRE_CAP, ATTEMPT_10_PRE_CAP_SHA256, "attempt_10 pre-cap"),
        (ATTEMPT_10_FAILURE, ATTEMPT_10_FAILURE_SHA256, "attempt_10 failure"),
        (ATTEMPT_11_PROPOSAL, ATTEMPT_11_PROPOSAL_SHA256, "attempt_11 revision-02 proposal"),
        (ATTEMPT_11_WORKER, ATTEMPT_11_WORKER_SHA256, "attempt_11 revision-02 worker"),
        (ATTEMPT_11_PRE_MASK, ATTEMPT_11_PRE_MASK_SHA256, "attempt_11 pre-mask"),
        (ATTEMPT_11_PRE_CAP, ATTEMPT_11_PRE_CAP_SHA256, "attempt_11 pre-cap"),
        (ATTEMPT_11_FAILURE, ATTEMPT_11_FAILURE_SHA256, "attempt_11 failure"),
        (ATTEMPT_12_PROPOSAL, ATTEMPT_12_PROPOSAL_SHA256, "attempt_12 revision-03 proposal"),
        (ATTEMPT_12_WORKER, ATTEMPT_12_WORKER_SHA256, "attempt_12 revision-03 worker"),
        (ATTEMPT_12_PRE_MASK, ATTEMPT_12_PRE_MASK_SHA256, "attempt_12 pre-mask"),
        (ATTEMPT_12_PRE_CAP, ATTEMPT_12_PRE_CAP_SHA256, "attempt_12 pre-cap"),
        (ATTEMPT_12_SOLVER, ATTEMPT_12_SOLVER_SHA256, "attempt_12 solver"),
        (ATTEMPT_12_FAILURE, ATTEMPT_12_FAILURE_SHA256, "attempt_12 failure"),
        (ATTEMPT_13_PROPOSAL, ATTEMPT_13_PROPOSAL_SHA256, "attempt_13 revision-04 proposal"),
        (a07.ATTEMPT_06_WORKER, a07.ATTEMPT_06_WORKER_SHA256, "attempt_06 worker"),
        (a14.PROPOSAL, a14.PROPOSAL_SHA256, "attempt_06 proposal"),
        (a14.ATTEMPT_05_REPORT, a14.ATTEMPT_05_REPORT_SHA256, "attempt_05 report"),
    ):
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"{label} hash drifted")
    planned_output = next_append_only_output()
    if planned_output.name != EXPECTED_ATTEMPT_SLOT:
        raise RuntimeError(
            f"append-only attempt slot is {planned_output.name}, expected {EXPECTED_ATTEMPT_SLOT}"
        )
    ACTIVE_OUTPUT = a09.allocate_output()
    if (
        ACTIVE_OUTPUT.resolve() != planned_output.resolve()
        or ACTIVE_OUTPUT.name != EXPECTED_ATTEMPT_SLOT
    ):
        raise RuntimeError(
            f"append-only attempt slot is {ACTIVE_OUTPUT.name}, expected {EXPECTED_ATTEMPT_SLOT}"
        )
    a14.ACTIVE_OUTPUT = ACTIVE_OUTPUT
    a11.AUTHORITATIVE_ENDPOINTS_BY_MIDPOINT.clear()
    a11.AUTHORITATIVE_MAP_RECORDS.clear()
    a11.AUTHORITATIVE_MAP_SHA256 = None
    a11.CAPTURE_INVOCATIONS = 0
    ACTIVE_EXCEPTION_CAPS.clear()
    RELIEF_SEQUENCE.clear()
    OBSERVED_RUNTIME_PARAMETERS.clear()
    a14.RELIEF_SEQUENCE.clear()
    a14.RELIEF_RECORDS.clear()
    a14.FADE_RECORDS.clear()
    a14.PENDING_FADE = None

    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or native rig is absent")
    a09.a08.r24_base.clear_pose(rig)
    source_shape_key_count = (
        len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
    )
    preflight = a09.a08.original_patch_preflight(body)
    a10.SOURCE_FACE_ID_BY_VERTICES = {
        frozenset(map(int, preflight["faces"][face_index])): int(face_index)
        for face_index in preflight["patch_faces"]
    }

    prior_refinement = a09.face_refinement_templates
    prior_solver = a09.solve_coupled_fair_fit
    prior_selected = a10.selected_seam_targets
    prior_endpoint = a10.source_endpoint_ids_for_midpoint
    prior_feature = a09.a08.feature_offset_and_tags
    prior_smoothstep = a09.a08.smoothstep
    prior_ring1_cap = a09.RING_1_CAP_M
    prior_overall_cap = a09.TOTAL_BASE_FIT_CAP_M
    prior_a07_file = a07.__file__
    a09.face_refinement_templates = a11.capture_authoritative_refinement_map
    a09.solve_coupled_fair_fit = attempt08_coupled_fit
    a10.selected_seam_targets = a14.selected_seam_targets
    a10.source_endpoint_ids_for_midpoint = a11.authoritative_endpoint_lookup
    a09.a08.feature_offset_and_tags = a14.attempt06_feature_offset_and_tags
    a09.a08.smoothstep = a14.attempt06_smoothstep
    a09.RING_1_CAP_M = INHERITED_RING_1_CAP_M
    a09.TOTAL_BASE_FIT_CAP_M = INHERITED_TOTAL_BASE_FIT_CAP_M
    a07.__file__ = str(worker)
    try:
        applied = a09.refine_and_shape(body, rig, preflight)
    finally:
        a09.face_refinement_templates = prior_refinement
        a09.solve_coupled_fair_fit = prior_solver
        a10.selected_seam_targets = prior_selected
        a10.source_endpoint_ids_for_midpoint = prior_endpoint
        a09.a08.feature_offset_and_tags = prior_feature
        a09.a08.smoothstep = prior_smoothstep
        a09.RING_1_CAP_M = prior_ring1_cap
        a09.TOTAL_BASE_FIT_CAP_M = prior_overall_cap
        a07.__file__ = prior_a07_file
    if a14.RELIEF_SEQUENCE or a14.PENDING_FADE is not None:
        raise RuntimeError("Attempt 08 relief/fade sequence was not fully consumed")
    zero_relief = attempt08_zero_relief_evidence()
    applied["attempt08_exact_cap_policy"] = applied["base_fit"][
        "attempt08_exact_cap_policy"
    ]
    applied["attempt08_zero_relief"] = zero_relief
    gates = attempt10_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = a09.a08.r24_render.render_evidence(body, applied, render_directory)
    paired = a09.render_uniform_clay_pairs_without_subdivision(
        render_directory, applied
    )
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired
    map_state = a11.authoritative_map_state()
    report = {
        "schema": "kira.avatar.r24.a09_attempt13_revision04_canonical_serialized_norm_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "NO_SAVE_STRUCTURAL_GATES_PASS_VISUAL_OWNER_REVIEW_REQUIRED"
            if gates["passed"]
            else "NO_SAVE_STRUCTURAL_OR_SEMANTIC_GATE_FAILURE_RETAINED_FOR_DIAGNOSIS"
        ),
        "source": {
            "path": relative(SOURCE),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha256(SOURCE),
            "unchanged": sha256(SOURCE) == SOURCE_SHA256,
            "body": BODY_NAME,
            "rig": RIG_NAME,
            "source_shape_key_count": source_shape_key_count,
        },
        "worker": {
            "path": relative(worker),
            "bytes": worker.stat().st_size,
            "sha256": sha256(worker),
        },
        "semantic_fingerprint_helper": {
            "path": relative(SEMANTIC_HELPER),
            "sha256": SEMANTIC_HELPER_SHA256,
            "verified_before_attempt_allocation_and_source_load": True,
        },
        "runtime_effect_fingerprint_helper": {
            "path": relative(RUNTIME_EFFECT_HELPER),
            "sha256": RUNTIME_EFFECT_HELPER_SHA256,
            "verified_before_attempt_allocation_and_source_load": True,
            "bound_formula_sources": {
                "base_feature_worker_sha256": a09.A08_WORKER_SHA256,
                "positive_relief_worker_sha256": a07.ATTEMPT_06_WORKER_SHA256,
            },
        },
        "proposals": {
            "exact_three_support_caps": {
                "path": relative(ATTEMPT_08_PROPOSAL),
                "sha256": sha256(ATTEMPT_08_PROPOSAL),
            },
            "startup_binding_repair": {
                "path": relative(ATTEMPT_09_PROPOSAL),
                "sha256": sha256(ATTEMPT_09_PROPOSAL),
            },
            "measured_postsolve_ceilings": {
                "path": relative(ATTEMPT_10_PROPOSAL),
                "sha256": sha256(ATTEMPT_10_PROPOSAL),
            },
            "semantic_mask_fingerprint_repair": {
                "path": relative(ATTEMPT_11_PROPOSAL),
                "sha256": sha256(ATTEMPT_11_PROPOSAL),
            },
            "runtime_effect_fingerprint_repair": {
                "path": relative(ATTEMPT_12_PROPOSAL),
                "sha256": sha256(ATTEMPT_12_PROPOSAL),
            },
            "canonical_serialized_norm_repair": {
                "path": relative(ATTEMPT_13_PROPOSAL),
                "sha256": sha256(ATTEMPT_13_PROPOSAL),
            },
        },
        "preserved_attempt_07": {
            "worker_sha256": ATTEMPT_07_WORKER_SHA256,
            "pre_mask_sha256": ATTEMPT_07_PRE_MASK_SHA256,
            "pre_cap_sha256": ATTEMPT_07_PRE_CAP_SHA256,
            "failure_sha256": ATTEMPT_07_FAILURE_SHA256,
            "diagnosis_sha256": ATTEMPT_07_DIAGNOSIS_SHA256,
        },
        "preserved_attempt_08": {
            "worker_sha256": ATTEMPT_08_WORKER_SHA256,
            "stdout_stderr_sha256": ATTEMPT_08_STDOUT_SHA256,
            "failure_sha256": ATTEMPT_08_FAILURE_SHA256,
        },
        "preserved_attempt_09": {
            "worker_sha256": ATTEMPT_09_WORKER_SHA256,
            "pre_mask_sha256": ATTEMPT_09_PRE_MASK_SHA256,
            "pre_cap_sha256": ATTEMPT_09_PRE_CAP_SHA256,
            "solver_sha256": ATTEMPT_09_SOLVER_SHA256,
            "failure_sha256": ATTEMPT_09_FAILURE_SHA256,
            "diagnosis_sha256": ATTEMPT_09_DIAGNOSIS_SHA256,
        },
        "preserved_attempt_10_revision01": {
            "worker": {
                "path": relative(REVISION01_WORKER),
                "sha256": REVISION01_WORKER_SHA256,
            },
            "pre_mask_sha256": ATTEMPT_10_PRE_MASK_SHA256,
            "pre_cap_sha256": ATTEMPT_10_PRE_CAP_SHA256,
            "failure_sha256": ATTEMPT_10_FAILURE_SHA256,
            "mutation_allowed": False,
        },
        "preserved_attempt_11_revision02": {
            "worker": {
                "path": relative(ATTEMPT_11_WORKER),
                "sha256": ATTEMPT_11_WORKER_SHA256,
            },
            "semantic_helper_sha256": SEMANTIC_HELPER_SHA256,
            "pre_mask_sha256": ATTEMPT_11_PRE_MASK_SHA256,
            "pre_cap_sha256": ATTEMPT_11_PRE_CAP_SHA256,
            "failure_sha256": ATTEMPT_11_FAILURE_SHA256,
            "safe_pre_geometry_failure_preserved": True,
            "mutation_allowed": False,
        },
        "preserved_attempt_12_revision03": {
            "worker": {
                "path": relative(ATTEMPT_12_WORKER),
                "sha256": ATTEMPT_12_WORKER_SHA256,
            },
            "pre_mask_sha256": ATTEMPT_12_PRE_MASK_SHA256,
            "pre_cap_sha256": ATTEMPT_12_PRE_CAP_SHA256,
            "solver_sha256": ATTEMPT_12_SOLVER_SHA256,
            "failure_sha256": ATTEMPT_12_FAILURE_SHA256,
            "safe_pre_geometry_failure_preserved": True,
            "mutation_allowed": False,
        },
        "preserved_rejected_attempt_10_proposal": {
            "worker": {
                "path": relative(REJECTED_ATTEMPT_10_WORKER),
                "sha256": REJECTED_ATTEMPT_10_WORKER_SHA256,
            },
            "static_checkpoint": {
                "path": relative(REJECTED_ATTEMPT_10_CHECKPOINT),
                "sha256": REJECTED_ATTEMPT_10_CHECKPOINT_SHA256,
            },
            "executed": False,
            "reason": "independent pre-run audit rejected inherited-cap mutation and incomplete evidence",
        },
        "attempt10_only_behavioral_change": (
            "measured post-solve ceilings are evaluated while inherited A09 "
            "ring-one and total bindings remain exactly 2.40mm; KKT calculation "
            "and soft-target clamps remain unchanged"
        ),
        "revision01_evidence_change": (
            "pre-geometry A09 solver fingerprint, exact 27-support parallel/KKT/"
            "nullspace evidence, preserved legacy cap failures, and canonical "
            "zero-relief identity/product checks"
        ),
        "revision02_evidence_change": (
            "PRE_CAP and solver mask gates use the exact semantic projection; "
            "unknown fields fail closed; aligned duplicate-free runtime t deltas "
            "must stay within 2.5e-06; no new full-mask canonical hash is bound"
        ),
        "revision03_evidence_change": (
            "raw t drift must stay within 1e-05 and the exact inherited pure "
            "feature/relief calculation must preserve semantic tags with adjusted "
            "pre-fade offset drift at most 1e-07m for every unique aligned vertex"
        ),
        "revision04_evidence_change": (
            "serialized support-vector components are reconstructed through native "
            "mathutils Vector.length for the unchanged strict self-consistency gates; "
            "Python double-precision component norms and differences are diagnostic "
            "only; no solver, geometry, target, cap, mask, topology, or source "
            "binding changes"
        ),
        "only_change_from_attempt_08_worker": (
            "startup preservation tuple resolves Attempt 06 worker constants "
            "through the Attempt 07 wrapper; evidence bindings and append-only "
            "attempt_09 metadata added"
        ),
        "body_behavior_preserved_from_attempt_08": (
            "identity-bound caps 2.0/2.4/2.4mm for exactly three graph-ring-one "
            "supports with zero relief; targets, KKT, partitions, and all other "
            "geometry rules unchanged"
        ),
        "pre_mask_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "PRE_MASK_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "PRE_MASK_DIAGNOSTIC.json"),
        },
        "pre_cap_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "PRE_CAP_DIAGNOSTIC.json"),
        },
        "solver_diagnostic": {
            "path": relative(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
            "sha256": sha256(ACTIVE_OUTPUT / "SOLVER_DIAGNOSTIC.json"),
        },
        "authoritative_midpoint_endpoint_map": {
            "binding_source": map_state["binding_source"],
            "count": map_state["count"],
            "canonical_sha256": map_state["canonical_sha256"],
        },
        "preflight": {
            "patch_face_count": len(preflight["patch_faces"]),
            "patch_vertex_count": len(preflight["patch_vertices"]),
            "boundary_vertex_count": len(preflight["boundary_vertices"]),
            "boundary_edge_count": len(preflight["boundary_edges"]),
            "boundary_position_sha256": preflight["boundary_position_sha256"],
            "boundary_edge_sha256": preflight["boundary_edge_sha256"],
            "topology": preflight["topology"],
        },
        "application": applied,
        "gates": gates,
        "renders": renders,
        "visual_gate": {
            "status": "PENDING_SEPARATE_INDEPENDENT_REVIEW",
            "structural_pass_does_not_override_visual_failure": True,
            "requirements_unchanged_from_attempt_06": True,
        },
        "operations": {
            "blend_saved": False,
            "source_overwritten": False,
            "runtime_or_person_state_changed": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External private visual/topology simulation only. No internal tract, "
            "continence, elimination, reproduction, pregnancy, sensation, subjective "
            "state, owner approval, runtime readiness, or biological function is "
            "implemented or claimed."
        ),
    }
    atomic_write_json(ACTIVE_OUTPUT / "SIMULATION_REPORT.json", report)
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        trace = traceback.format_exc()
        output = ACTIVE_OUTPUT or a14.ACTIVE_OUTPUT
        if output is not None:
            failure = {
                "schema": "kira.avatar.r24.a09_attempt13_revision04_canonical_serialized_norm_failure.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "NO_SAVE_FAILURE_PRESERVED",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": trace,
                "source": {
                    "path": relative(SOURCE),
                    "sha256": sha256(SOURCE) if SOURCE.is_file() else None,
                },
                "worker": {
                    "path": relative(Path(__file__).resolve()),
                    "sha256": sha256(Path(__file__).resolve()),
                },
                "semantic_fingerprint_helper": {
                    "path": relative(SEMANTIC_HELPER),
                    "sha256": SEMANTIC_HELPER_SHA256,
                    "verified_before_attempt_allocation_and_source_load": True,
                },
                "runtime_effect_fingerprint_helper": {
                    "path": relative(RUNTIME_EFFECT_HELPER),
                    "sha256": RUNTIME_EFFECT_HELPER_SHA256,
                    "verified_before_attempt_allocation_and_source_load": True,
                    "bound_formula_sources": {
                        "base_feature_worker_sha256": a09.A08_WORKER_SHA256,
                        "positive_relief_worker_sha256": (
                            a07.ATTEMPT_06_WORKER_SHA256
                        ),
                    },
                },
                "attempt_07_failure_sha256": ATTEMPT_07_FAILURE_SHA256,
                "attempt_08_failure_sha256": ATTEMPT_08_FAILURE_SHA256,
                "attempt_09_failure_sha256": ATTEMPT_09_FAILURE_SHA256,
                "preserved_attempt_10": {
                    "revision01_worker_sha256": REVISION01_WORKER_SHA256,
                    "pre_mask_sha256": ATTEMPT_10_PRE_MASK_SHA256,
                    "pre_cap_sha256": ATTEMPT_10_PRE_CAP_SHA256,
                    "failure_sha256": ATTEMPT_10_FAILURE_SHA256,
                },
                "preserved_attempt_11": {
                    "revision02_worker_sha256": ATTEMPT_11_WORKER_SHA256,
                    "revision02_helper_sha256": SEMANTIC_HELPER_SHA256,
                    "pre_mask_sha256": ATTEMPT_11_PRE_MASK_SHA256,
                    "pre_cap_sha256": ATTEMPT_11_PRE_CAP_SHA256,
                    "failure_sha256": ATTEMPT_11_FAILURE_SHA256,
                },
                "preserved_attempt_12": {
                    "revision03_worker_sha256": ATTEMPT_12_WORKER_SHA256,
                    "pre_mask_sha256": ATTEMPT_12_PRE_MASK_SHA256,
                    "pre_cap_sha256": ATTEMPT_12_PRE_CAP_SHA256,
                    "solver_sha256": ATTEMPT_12_SOLVER_SHA256,
                    "failure_sha256": ATTEMPT_12_FAILURE_SHA256,
                },
                "pre_mask_diagnostic_present": (
                    output / "PRE_MASK_DIAGNOSTIC.json"
                ).is_file(),
                "pre_cap_diagnostic_present": (
                    output / "PRE_CAP_DIAGNOSTIC.json"
                ).is_file(),
                "solver_diagnostic_present": (
                    output / "SOLVER_DIAGNOSTIC.json"
                ).is_file(),
                "operations": {
                    "blend_saved": False,
                    "source_overwritten": False,
                    "runtime_or_person_state_changed": False,
                },
            }
            atomic_write_json(output / "FAILURE.json", failure)
        print(trace, file=sys.stderr)
        raise
