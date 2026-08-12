from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest

from Core.kira_r24_semantic_mask_effect_fingerprint_v1 import (
    ADJUSTED_OFFSET_MAXIMUM_ABSOLUTE_DELTA_M,
    RAW_T_MAXIMUM_ABSOLUTE_DELTA,
    compare_semantic_masks_with_runtime_effect,
    inherited_adjusted_feature_relief,
    inherited_feature_offset_and_tags,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)
ATTEMPT10_PRE_MASK = EVIDENCE_ROOT / "attempt_10" / "PRE_MASK_DIAGNOSTIC.json"
ATTEMPT11_PRE_MASK = EVIDENCE_ROOT / "attempt_11" / "PRE_MASK_DIAGNOSTIC.json"
REVISION03_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt12_revision03.py"
)
RUNTIME_EFFECT_HELPER = (
    ROOT / "Core" / "kira_r24_semantic_mask_effect_fingerprint_v1.py"
)
REVISION03_PROPOSAL = (
    EVIDENCE_ROOT
    / "PREFLIGHT"
    / "ATTEMPT_12_REVISION03_RUNTIME_EFFECT_FINGERPRINT_PROPOSAL.md"
)
EXPECTED_SEMANTIC_SHA256 = (
    "3b6f8c7fd085396deba9ce54c537d610cb1679f33b41724b1494f29a0c81f4c5"
)
IDENTITY_FIELDS = (
    "vertex_index_before_final_reindex",
    "canonical_original_id",
)

BOUND_SHA256 = {
    REVISION03_WORKER: (
        "a03597d16623450d72608fdfffe9bd4c4db252b226f52a3090f4d17ff29370f2"
    ),
    ROOT
    / "Core"
    / "kira_r24_semantic_mask_fingerprint.py": (
        "c68d4121dcdce8ef28cbb04e48708984591569c70a9a70fb4c3565f66a4118e5"
    ),
    RUNTIME_EFFECT_HELPER: (
        "dc9200429b1f4a8172282fe2b3b56a263eda3aad18fc146b59fa0a87a6201fb4"
    ),
    REVISION03_PROPOSAL: (
        "5c26f2afe81e77221e87b79b12b4afbd4303e782ec181c501a9d642f15b4a56a"
    ),
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_direct_subdivision_surface.py": (
        "6a75233d53fabebb9afc61e46184d3dbe5718a648317a93f8b2b2792fab7ab1c"
    ),
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_panel_neutralized.py": (
        "7af00b113268c26f6eca304d95709541f2e56264f539e9c3aa5430aa53e00ea1"
    ),
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt11_revision02.py": (
        "a0cbca0360ab316d1122fd9f941f0223257dd825f9ec2d1c6fe93812c53b2368"
    ),
    EVIDENCE_ROOT
    / "PREFLIGHT"
    / "ATTEMPT_11_REVISION02_SEMANTIC_MASK_FINGERPRINT_PROPOSAL.md": (
        "2b78ffe7a088339ff416cbf2e3c4a596243695c030d2b48993dbcb4b1702a5fa"
    ),
    ATTEMPT10_PRE_MASK: (
        "ddd040e808f38e16436148c5b82365aa6c441b32751a078578a4d897fd92fe9a"
    ),
    EVIDENCE_ROOT
    / "attempt_10"
    / "PRE_CAP_DIAGNOSTIC.json": (
        "d7e77ed0dde9b08baba1d99cbdca8dc3ec39e2ded0d2f24092e78099c101536b"
    ),
    EVIDENCE_ROOT / "attempt_10" / "FAILURE.json": (
        "ec66ea06c7b16545714b85725a136f427faf7859cf9e5cb14bf3daf4d82e7355"
    ),
    ATTEMPT11_PRE_MASK: (
        "72416bb6736b9ade70b87db2ed49ef39874f4afde1790c4ad2f81e1ea76dfe94"
    ),
    EVIDENCE_ROOT
    / "attempt_11"
    / "PRE_CAP_DIAGNOSTIC.json": (
        "0c76e898b4ead822b1750861cfab3edcd0cca35f223f9f83b9e062f01fe39c34"
    ),
    EVIDENCE_ROOT / "attempt_11" / "FAILURE.json": (
        "1dd40afc5afa638ed7359a79c00b006f42a8950c7b52dfe0c53d27e00a08323a"
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(record: dict) -> tuple[int, int]:
    return tuple(record[field] for field in IDENTITY_FIELDS)


def records_for_identity(masks: dict, target: tuple[int, int]):
    for mask in masks["vertex_masks"].values():
        for record in mask["records"]:
            if identity(record) == target:
                yield record


def runtime_parameters_from_masks(masks: dict) -> dict:
    result = {}
    for mask in masks["vertex_masks"].values():
        for record in mask["records"]:
            key = identity(record)
            parameters = {"u": float(record["u"]), "t": float(record["t"])}
            if key in result:
                if result[key] != parameters:
                    raise AssertionError(f"inconsistent fixture identity {key}")
            else:
                result[key] = parameters
    return result


def identities_for_mask(masks: dict, mask_name: str) -> set[tuple[int, int]]:
    return {
        identity(record)
        for record in masks["vertex_masks"][mask_name]["records"]
    }


def load_bound_source_feature_math() -> dict:
    source_path = (
        ROOT / "tools" / "blender_simulate_kira_r24_direct_subdivision_surface.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    selected_names = {
        "gaussian",
        "gaussian2",
        "elliptical_radius",
        "ring_value",
        "feature_offset_and_tags",
    }
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id in {"MAXIMUM_OFFSET_M", "OPENING_SPECS"}
            for target in node.targets
        ):
            body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in selected_names:
            body.append(node)
    namespace = {"math": math}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace


class R24Revision03RuntimeEffectFingerprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.attempt10_masks = load_json(ATTEMPT10_PRE_MASK)["masks"]
        cls.attempt11_masks = load_json(ATTEMPT11_PRE_MASK)["masks"]

    def test_bound_attempt11_effect_evidence_passes_revision03(self) -> None:
        result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, self.attempt11_masks
        )
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(
            result["reference_semantic_sha256"], EXPECTED_SEMANTIC_SHA256
        )
        self.assertEqual(
            result["observed_semantic_sha256"], EXPECTED_SEMANTIC_SHA256
        )
        self.assertEqual(result["unique_aligned_vertex_count"], 753)
        self.assertEqual(result["changed_t_count"], 679)
        self.assertEqual(result["semantic_tag_mismatch_count"], 0)
        self.assertEqual(
            result["maximum_absolute_raw_t_delta"],
            5.349714999991484e-06,
        )
        self.assertEqual(
            result["maximum_absolute_adjusted_offset_delta_m"],
            6.61503382938522e-08,
        )
        self.assertLess(
            result["maximum_absolute_raw_t_delta"],
            RAW_T_MAXIMUM_ABSOLUTE_DELTA,
        )
        self.assertLess(
            result["maximum_absolute_adjusted_offset_delta_m"],
            ADJUSTED_OFFSET_MAXIMUM_ABSOLUTE_DELTA_M,
        )
        maximum = max(
            result["records"],
            key=lambda record: record["absolute_adjusted_offset_delta_m"],
        )
        self.assertEqual(
            (
                maximum["vertex_index_before_final_reindex"],
                maximum["canonical_original_id"],
            ),
            (1009, 1009),
        )
        self.assertEqual(
            maximum["reference_effect"]["adjusted_offset_before_fade_m"],
            0.00042489927792069857,
        )
        self.assertEqual(
            maximum["observed_effect"]["adjusted_offset_before_fade_m"],
            0.0004249654282589924,
        )

    def test_helper_matches_bound_source_math_at_every_evidence_state(self) -> None:
        source = load_bound_source_feature_math()
        source_feature = source["feature_offset_and_tags"]
        gaussian2 = source["gaussian2"]
        for masks in (self.attempt10_masks, self.attempt11_masks):
            parameters = runtime_parameters_from_masks(masks)
            central = identities_for_mask(masks, "CENTRAL_POSITIVE_RELIEF")
            for vertex_identity, coordinates in parameters.items():
                with self.subTest(identity=vertex_identity, t=coordinates["t"]):
                    u = coordinates["u"]
                    t = coordinates["t"]
                    expected_original, expected_tags = source_feature(u, t)
                    observed_original, observed_tags = inherited_feature_offset_and_tags(
                        u, t
                    )
                    self.assertEqual(observed_original, expected_original)
                    self.assertEqual(set(observed_tags), expected_tags)

                    expected_delta = 0.0
                    if vertex_identity in central:
                        left_major = 0.00255 * gaussian2(
                            u, t, -0.31, 0.46, 0.15, 0.25
                        )
                        right_major = 0.00242 * gaussian2(
                            u, t, 0.32, 0.46, 0.15, 0.25
                        )
                        left_minor = 0.00134 * gaussian2(
                            u, t, -0.095, 0.47, 0.050, 0.20
                        )
                        right_minor = 0.00122 * gaussian2(
                            u, t, 0.108, 0.47, 0.052, 0.20
                        )
                        hood = 0.00110 * gaussian2(
                            u, t, -0.006, 0.285, 0.120, 0.065
                        )
                        glans = 0.00044 * gaussian2(
                            u, t, -0.010, 0.320, 0.045, 0.032
                        )
                        expected_delta = (
                            0.12 * (left_major + right_major)
                            + 0.10 * (left_minor + right_minor)
                            + 0.15 * (hood + glans)
                        )
                    expected_adjusted = max(
                        -0.003,
                        min(0.003, float(expected_original) + expected_delta),
                    )
                    adjusted = inherited_adjusted_feature_relief(
                        u, t, vertex_identity in central
                    )
                    self.assertEqual(
                        adjusted["positive_increment_before_clamp_m"],
                        expected_delta,
                    )
                    self.assertEqual(
                        adjusted["adjusted_offset_before_fade_m"],
                        expected_adjusted,
                    )
                    self.assertEqual(
                        set(adjusted["semantic_tags"]), expected_tags
                    )

    def test_plus_point_125_fails_the_independent_raw_gate(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        target = (1009, 1009)
        for record in records_for_identity(observed, target):
            record["t"] += 0.125
        result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, observed
        )
        self.assertFalse(result["passed"])
        self.assertTrue(result["checks"]["semantic_projection_exact"])
        self.assertFalse(
            result["checks"]["maximum_absolute_raw_t_delta_within_1e_05"]
        )
        self.assertAlmostEqual(result["maximum_absolute_raw_t_delta"], 0.125)

    def test_sub_raw_gate_effect_perturbation_fails_effect_ceiling(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        target = (1009, 1009)
        source_t = next(records_for_identity(observed, target))["t"]
        runtime_t = source_t + 9.0e-06
        for record in records_for_identity(observed, target):
            record["t"] = round(runtime_t, 12)
        runtime_parameters = runtime_parameters_from_masks(observed)
        runtime_parameters[target]["t"] = runtime_t
        result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks,
            observed,
            observed_runtime_parameters=runtime_parameters,
        )
        self.assertFalse(result["passed"])
        self.assertTrue(
            result["checks"]["maximum_absolute_raw_t_delta_within_1e_05"]
        )
        self.assertTrue(result["checks"]["semantic_tags_exact"])
        self.assertFalse(
            result["checks"][
                "maximum_absolute_adjusted_offset_delta_within_1e_07_m"
            ]
        )
        self.assertGreater(
            result["maximum_absolute_adjusted_offset_delta_m"], 1.0e-07
        )
        self.assertEqual(
            result["runtime_parameter_source"],
            "full_precision_observed_memory_with_12_decimal_bound_reference",
        )

    def test_sub_raw_gate_tag_threshold_flip_is_rejected(self) -> None:
        reference = deepcopy(self.attempt10_masks)
        observed = deepcopy(self.attempt10_masks)
        target = identity(
            reference["vertex_masks"]["BOUNDARY_ZERO"]["records"][0]
        )
        mons_threshold_t = 0.16 + 0.16 * math.sqrt(
            -2.0 * math.log(0.00016 / 0.00118)
        )
        for record in records_for_identity(reference, target):
            record["u"] = 0.0
            record["t"] = mons_threshold_t - 1.0e-07
        for record in records_for_identity(observed, target):
            record["u"] = 0.0
            record["t"] = mons_threshold_t + 1.0e-07
        result = compare_semantic_masks_with_runtime_effect(reference, observed)
        self.assertFalse(result["passed"])
        self.assertTrue(result["checks"]["semantic_projection_exact"])
        self.assertTrue(
            result["checks"]["maximum_absolute_raw_t_delta_within_1e_05"]
        )
        self.assertFalse(result["checks"]["semantic_tags_exact"])
        self.assertEqual(result["semantic_tag_mismatch_count"], 1)

    def test_exact_membership_gate_is_retained(self) -> None:
        observed = deepcopy(self.attempt10_masks)
        shared = sorted(
            identities_for_mask(observed, "SEAM_CONTINUATION_RING2")
            & identities_for_mask(observed, "CENTRAL_POSITIVE_RELIEF")
        )
        self.assertTrue(shared)
        target = shared[0]
        central = observed["vertex_masks"]["CENTRAL_POSITIVE_RELIEF"]
        central["records"] = [
            record for record in central["records"] if identity(record) != target
        ]
        central["count"] -= 1
        result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, observed
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["semantic_projection_exact"])
        self.assertFalse(
            result["checks"][
                "graph_rings_u_memberships_and_central_membership_exact"
            ]
        )

    def test_exact_u_and_identity_drift_are_rejected(self) -> None:
        observed_u = deepcopy(self.attempt10_masks)
        target = identity(
            observed_u["vertex_masks"]["BOUNDARY_ZERO"]["records"][0]
        )
        for record in records_for_identity(observed_u, target):
            record["u"] += 1.0e-12
        u_result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, observed_u
        )
        self.assertFalse(u_result["passed"])
        self.assertFalse(u_result["checks"]["semantic_projection_exact"])
        self.assertFalse(
            u_result["checks"][
                "graph_rings_u_memberships_and_central_membership_exact"
            ]
        )

        observed_identity = deepcopy(self.attempt10_masks)
        boundary = identities_for_mask(observed_identity, "BOUNDARY_ZERO")
        all_other = set().union(
            *(
                identities_for_mask(observed_identity, name)
                for name in observed_identity["vertex_masks"]
                if name != "BOUNDARY_ZERO"
            )
        )
        unique_target = sorted(boundary - all_other)[0]
        record = next(records_for_identity(observed_identity, unique_target))
        record["canonical_original_id"] += 100_000
        identity_result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, observed_identity
        )
        self.assertFalse(identity_result["passed"])
        self.assertFalse(
            identity_result["checks"]["unique_identity_sets_aligned_exactly"]
        )

    def test_duplicate_and_disagreeing_repeated_records_are_rejected(self) -> None:
        duplicate = deepcopy(self.attempt10_masks)
        mask = duplicate["vertex_masks"]["BOUNDARY_ZERO"]
        mask["records"].append(deepcopy(mask["records"][0]))
        mask["count"] += 1
        duplicate_result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, duplicate
        )
        self.assertFalse(duplicate_result["passed"])
        self.assertFalse(
            duplicate_result["checks"][
                "observed_membership_identities_have_no_duplicates"
            ]
        )

        inconsistent = deepcopy(self.attempt10_masks)
        shared = sorted(
            identities_for_mask(inconsistent, "SEAM_CONTINUATION_RING2")
            & identities_for_mask(inconsistent, "CENTRAL_POSITIVE_RELIEF")
        )
        target = shared[0]
        central_records = inconsistent["vertex_masks"][
            "CENTRAL_POSITIVE_RELIEF"
        ]["records"]
        next(
            record for record in central_records if identity(record) == target
        )["t"] += 1.0e-07
        inconsistent_result = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks, inconsistent
        )
        self.assertFalse(inconsistent_result["passed"])
        self.assertTrue(inconsistent_result["checks"]["semantic_projection_exact"])
        self.assertFalse(
            inconsistent_result["checks"][
                "observed_repeated_identity_records_consistent"
            ]
        )

    def test_unknown_fields_fail_closed(self) -> None:
        cases = []
        top = deepcopy(self.attempt10_masks)
        top["future_unreviewed_field"] = True
        cases.append(top)
        record = deepcopy(self.attempt10_masks)
        record["vertex_masks"]["BOUNDARY_ZERO"]["records"][0][
            "future_unreviewed_field"
        ] = True
        cases.append(record)
        for observed in cases:
            with self.subTest():
                with self.assertRaisesRegex(
                    ValueError, r"fields must be exact.*unknown"
                ):
                    compare_semantic_masks_with_runtime_effect(
                        self.attempt10_masks, observed
                    )

        runtime_parameters = runtime_parameters_from_masks(self.attempt10_masks)
        target = next(iter(runtime_parameters))
        runtime_parameters[target]["future_unreviewed_field"] = True
        with self.assertRaisesRegex(ValueError, r"fields must be exact.*unknown"):
            compare_semantic_masks_with_runtime_effect(
                self.attempt10_masks,
                self.attempt10_masks,
                observed_runtime_parameters=runtime_parameters,
            )

    def test_full_precision_runtime_parameters_must_cover_and_round_back(self) -> None:
        runtime_parameters = runtime_parameters_from_masks(self.attempt10_masks)
        exact = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks,
            self.attempt10_masks,
            observed_runtime_parameters=runtime_parameters,
        )
        self.assertTrue(exact["passed"], exact["checks"])
        self.assertTrue(
            exact["checks"][
                "runtime_parameters_cover_observed_identities_exactly"
            ]
        )
        self.assertTrue(
            exact["checks"][
                "runtime_parameters_round_to_serialized_evidence_exactly"
            ]
        )

        incomplete = deepcopy(runtime_parameters)
        incomplete.pop(next(iter(incomplete)))
        missing = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks,
            self.attempt10_masks,
            observed_runtime_parameters=incomplete,
        )
        self.assertFalse(missing["passed"])
        self.assertFalse(
            missing["checks"][
                "runtime_parameters_cover_observed_identities_exactly"
            ]
        )

        not_round_trippable = deepcopy(runtime_parameters)
        target = next(iter(not_round_trippable))
        not_round_trippable[target]["u"] += 1.0e-07
        rounded = compare_semantic_masks_with_runtime_effect(
            self.attempt10_masks,
            self.attempt10_masks,
            observed_runtime_parameters=not_round_trippable,
        )
        self.assertFalse(rounded["passed"])
        self.assertFalse(
            rounded["checks"][
                "runtime_parameters_round_to_serialized_evidence_exactly"
            ]
        )

    def test_worker_is_static_append_only_bound_and_no_save(self) -> None:
        source = REVISION03_WORKER.read_text(encoding="utf-8")
        ast.parse(source, filename=str(REVISION03_WORKER))
        ast.parse(
            RUNTIME_EFFECT_HELPER.read_text(encoding="utf-8"),
            filename=str(RUNTIME_EFFECT_HELPER),
        )
        self.assertIn('EXPECTED_ATTEMPT_SLOT = "attempt_12"', source)
        self.assertIn("planned_output = next_append_only_output()", source)
        self.assertIn("planned_output.name != EXPECTED_ATTEMPT_SLOT", source)
        self.assertIn("ACTIVE_OUTPUT.name != EXPECTED_ATTEMPT_SLOT", source)
        self.assertGreaterEqual(
            source.count("compare_semantic_masks_with_runtime_effect("), 2
        )
        self.assertGreaterEqual(
            source.count(
                "observed_runtime_parameters=OBSERVED_RUNTIME_PARAMETERS"
            ),
            2,
        )
        self.assertIn("duplicate full-precision runtime identity", source)
        self.assertNotIn("bpy.ops.wm.save", source)
        self.assertNotIn("save_as_mainfile", source)

        required_bindings = (
            '"revision-03 runtime-effect helper"',
            '"preserved A08 feature-formula worker"',
            '"attempt_12 revision-03 proposal"',
            '"attempt_11 revision-02 worker"',
            '"attempt_11 pre-mask"',
            '"attempt_11 pre-cap"',
            '"attempt_11 failure"',
        )
        allocation = source.index("planned_output = next_append_only_output()")
        source_load = source.index("bpy.ops.wm.open_mainfile")
        for binding in required_bindings:
            with self.subTest(binding=binding):
                location = source.index(binding)
                self.assertLess(location, allocation)
                self.assertLess(location, source_load)

        expected_constants = (
            'RUNTIME_EFFECT_HELPER_SHA256 = "dc9200429b1f4a8172282fe2b3b56a263eda3aad18fc146b59fa0a87a6201fb4"',
            'ATTEMPT_12_PROPOSAL_SHA256 = "5c26f2afe81e77221e87b79b12b4afbd4303e782ec181c501a9d642f15b4a56a"',
            'ATTEMPT_11_WORKER_SHA256 = "a0cbca0360ab316d1122fd9f941f0223257dd825f9ec2d1c6fe93812c53b2368"',
            'ATTEMPT_11_PRE_MASK_SHA256 = "72416bb6736b9ade70b87db2ed49ef39874f4afde1790c4ad2f81e1ea76dfe94"',
            'ATTEMPT_11_PRE_CAP_SHA256 = "0c76e898b4ead822b1750861cfab3edcd0cca35f223f9f83b9e062f01fe39c34"',
            'ATTEMPT_11_FAILURE_SHA256 = "1dd40afc5afa638ed7359a79c00b006f42a8950c7b52dfe0c53d27e00a08323a"',
        )
        for constant in expected_constants:
            self.assertIn(constant, source)
        self.assertFalse((EVIDENCE_ROOT / "attempt_12").exists())

    def test_bound_sources_helpers_and_attempt10_11_evidence_are_exact(self) -> None:
        for path, expected in BOUND_SHA256.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), expected)


if __name__ == "__main__":
    unittest.main()
