from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from Core.avatar_nail_weight_constrained_projection_v1 import (
    NailWeightConstrainedProjectionError,
)
from Core.kira_r24_brow_nail_component_contract_v1 import (
    BROW_BINDINGS,
    BROW_SOURCE_PATH,
    BROW_SOURCE_SHA256,
    EXPECTED_RENDER_KEYS,
    KiraR24ComponentContractError,
    MAXIMUM_CLEARANCE_M,
    MAXIMUM_FREE_EDGE_M,
    MAXIMUM_REFERENCE_CENTER_ERROR_M,
    MAXIMUM_SAMPLE_DISPLACEMENT_M,
    MINIMUM_CLEARANCE_M,
    MODE,
    NAIL_BINDINGS,
    NAIL_PLATE_THICKNESS_M,
    OLD_BROW_NAME,
    REQUIRED_POSE_KEYS,
    R21_REJECTED_SOURCE_SHA256,
    SCHEMA,
    select_connected_weight_constrained_grid_v2,
    validate_config,
    validate_no_save_transaction,
    validate_pose_gate_matrix,
    validate_reference_bound_candidate,
    validate_render_inventory,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def hit(component: int, *, ordinal: int = 0) -> dict[str, object]:
    return {
        "ray_hit_ordinal": ordinal,
        "ray_depth_m": 0.001 + ordinal * 0.001,
        "distance_to_expected_point_m": 0.0002 + ordinal * 0.0001,
        "evaluated_triangle_index": 100 + ordinal,
        "raw_triangle_index": 200 + ordinal,
        "raw_component_id": component,
        "expected_family_weight": 1.0,
        "foreign_digit_family_weight": 0.0,
        "wrong_side_digit_weight": 0.0,
        "expected_family_is_dominant": True,
        "outward_normal_alignment": 0.95,
    }


def base_config() -> dict[str, object]:
    source_nails = []
    for nail_id, source_object, bone in NAIL_BINDINGS:
        source_nails.append(
            {
                "nail_id": nail_id,
                "source_object": source_object,
                "bone": bone,
                "complete_mesh_sha256": digest(f"complete:{nail_id}"),
                "geometry_uv_sha256": digest(f"geometry:{nail_id}"),
                "positive_weight_sha256": digest(f"weights:{nail_id}"),
                "world_matrix_sha256": digest(f"matrix:{nail_id}"),
                "modifier_stack_sha256": digest(f"modifiers:{nail_id}"),
                "corrected_anchor_world_m": [0.1, -0.2, 0.3],
            }
        )
    return {
        "schema": SCHEMA,
        "mode": MODE,
        "status": "PREPARED_NOT_RUN",
        "candidate": {
            "path": "Avatar/private_owner_review/future_r24.blend",
            "sha256": digest("future-r24"),
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_activation_allowed": False,
            "full_scene_state_sha256": digest("full-scene-state"),
            "body": {
                "object": "Future_R24_Body",
                "complete_mesh_sha256": digest("body-complete-mesh"),
                "geometry_uv_sha256": digest("body-geometry"),
                "positive_weight_sha256": digest("body-weights"),
                "world_matrix_sha256": digest("body-matrix"),
                "modifier_stack_sha256": digest("body-modifiers"),
            },
            "rig": {
                "object": "Future_R24_Rig",
                "rest_pose_sha256": digest("rig-rest"),
                "pose_sha256": digest("rig-pose"),
                "world_matrix_sha256": digest("rig-matrix"),
            },
            "replaceable_old_brow": {
                "object": OLD_BROW_NAME,
                "complete_mesh_sha256": digest("old-brow-complete-mesh"),
                "geometry_uv_sha256": digest("old-brow-geometry"),
                "positive_weight_sha256": digest("old-brow-weights"),
                "world_matrix_sha256": digest("old-brow-matrix"),
                "modifier_stack_sha256": digest("old-brow-modifiers"),
            },
            "source_nails": source_nails,
        },
        "brow_source": {
            "path": BROW_SOURCE_PATH,
            "sha256": BROW_SOURCE_SHA256,
            "author_new_brow_geometry": False,
            "objects": [
                {
                    **dict(row),
                    "bones": list(row["bones"]),
                }
                for row in BROW_BINDINGS
            ],
        },
        "gates": {
            "component_id_zero_rejected": True,
            "corrected_reference_center_controls_placement": True,
            "full_modifier_stack_bound": True,
            "full_scene_state_bound": True,
            "render_before_any_save": True,
            "all_pose_contact_intersection_gates_required": True,
            "no_third_brow_authoring": True,
            "no_partial_candidate": True,
            "maximum_reference_center_error_m": MAXIMUM_REFERENCE_CENTER_ERROR_M,
            "maximum_sample_displacement_m": MAXIMUM_SAMPLE_DISPLACEMENT_M,
            "minimum_clearance_m": MINIMUM_CLEARANCE_M,
            "maximum_clearance_m": MAXIMUM_CLEARANCE_M,
            "maximum_free_edge_m": MAXIMUM_FREE_EDGE_M,
            "nail_plate_thickness_m": NAIL_PLATE_THICKNESS_M,
        },
        "pose_evidence": {
            "path": "RecoverySprint/future_pose_evidence.json",
            "sha256": digest("pose-file"),
            "candidate_sha256": digest("future-r24"),
        },
        "output": {
            "evidence_dir": "RecoverySprint/future_component_preparation/attempt_01",
            "render_staging_dir": "RecoverySprint/future_component_preparation/attempt_01/renders",
            "candidate_blend": None,
            "save_blend_allowed": False,
        },
    }


def valid_pose_matrix(candidate_sha: str) -> dict[str, object]:
    return {
        "candidate_sha256": candidate_sha,
        "poses": [
            {
                "pose": key,
                "action": f"action_{key}",
                "action_sha256": digest(f"action:{key}"),
                "frame": 1,
                "contact_gate_passed": True,
                "all_20_nails_attached": True,
                "all_clearance_gates_passed": True,
                "no_body_nail_intersections": True,
                "no_nail_pair_overlap": True,
                "nail_count": 20,
                "exact_body_nail_crossing_pair_count": 0,
                "tested_nail_pair_count": 190,
                "minimum_clearance_m": MINIMUM_CLEARANCE_M,
                "maximum_clearance_m": MAXIMUM_CLEARANCE_M,
            }
            for key in REQUIRED_POSE_KEYS
        ],
    }


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(r"C:\synthetic_project")

    def test_complete_unbound_template_is_valid_without_file_reads(self) -> None:
        result = validate_config(base_config(), project_root=self.root, verify_files=False)
        self.assertEqual(result["candidate_sha256"], digest("future-r24"))
        self.assertEqual(len(result["source_nails"]), 20)

    def test_missing_candidate_hash_fails_closed(self) -> None:
        config = base_config()
        config["candidate"]["sha256"] = ""
        with self.assertRaises(KiraR24ComponentContractError):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_missing_full_scene_binding_fails_closed(self) -> None:
        config = base_config()
        config["candidate"]["full_scene_state_sha256"] = ""
        with self.assertRaisesRegex(KiraR24ComponentContractError, "full_scene"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_complete_body_mesh_binding_is_mandatory(self) -> None:
        config = base_config()
        config["candidate"]["body"]["complete_mesh_sha256"] = ""
        with self.assertRaisesRegex(KiraR24ComponentContractError, "complete_mesh"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_complete_replaceable_component_bindings_are_mandatory(self) -> None:
        old_brow = base_config()
        old_brow["candidate"]["replaceable_old_brow"]["modifier_stack_sha256"] = ""
        with self.assertRaisesRegex(KiraR24ComponentContractError, "modifier_stack"):
            validate_config(old_brow, project_root=self.root, verify_files=False)
        source_nail = base_config()
        source_nail["candidate"]["source_nails"][0]["world_matrix_sha256"] = ""
        with self.assertRaisesRegex(KiraR24ComponentContractError, "world_matrix"):
            validate_config(source_nail, project_root=self.root, verify_files=False)

    def test_rejected_r21_source_cannot_be_rebound(self) -> None:
        config = base_config()
        config["candidate"]["sha256"] = R21_REJECTED_SOURCE_SHA256
        config["pose_evidence"]["candidate_sha256"] = R21_REJECTED_SOURCE_SHA256
        with self.assertRaisesRegex(KiraR24ComponentContractError, "rejected R21"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_third_brow_authoring_fails(self) -> None:
        config = base_config()
        config["brow_source"]["author_new_brow_geometry"] = True
        with self.assertRaisesRegex(KiraR24ComponentContractError, "third-brow"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_brow_fingerprint_drift_fails(self) -> None:
        config = base_config()
        config["brow_source"]["objects"][0]["geometry_uv_sha256"] = digest("wrong")
        with self.assertRaisesRegex(KiraR24ComponentContractError, "brow fingerprints"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_missing_or_wrong_nail_binding_fails(self) -> None:
        missing = base_config()
        missing["candidate"]["source_nails"].pop()
        with self.assertRaisesRegex(KiraR24ComponentContractError, "twenty"):
            validate_config(missing, project_root=self.root, verify_files=False)
        wrong = base_config()
        wrong["candidate"]["source_nails"][0]["bone"] = "wrong"
        with self.assertRaisesRegex(KiraR24ComponentContractError, "binding drifted"):
            validate_config(wrong, project_root=self.root, verify_files=False)

    def test_save_or_blend_output_fails(self) -> None:
        config = base_config()
        config["output"]["save_blend_allowed"] = True
        config["output"]["candidate_blend"] = "Avatar/private_owner_review/output.blend"
        with self.assertRaisesRegex(KiraR24ComponentContractError, "no-save"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_threshold_drift_fails(self) -> None:
        config = base_config()
        config["gates"]["maximum_sample_displacement_m"] = 0.0041
        with self.assertRaisesRegex(KiraR24ComponentContractError, "exactly"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_pose_evidence_must_bind_same_candidate(self) -> None:
        config = base_config()
        config["pose_evidence"]["candidate_sha256"] = digest("another")
        with self.assertRaisesRegex(KiraR24ComponentContractError, "another candidate"):
            validate_config(config, project_root=self.root, verify_files=False)

    def test_output_and_candidate_paths_cannot_escape_project(self) -> None:
        config = base_config()
        config["output"]["evidence_dir"] = "../outside"
        with self.assertRaisesRegex(KiraR24ComponentContractError, "outside"):
            validate_config(config, project_root=self.root, verify_files=False)


class ConnectedComponentTests(unittest.TestCase):
    def test_component_zero_only_fails(self) -> None:
        stacks = [[hit(0)] for _ in range(81)]
        with self.assertRaises(NailWeightConstrainedProjectionError):
            select_connected_weight_constrained_grid_v2(stacks, center_sample_index=40)

    def test_zero_cannot_stitch_disconnected_samples(self) -> None:
        stacks = [[hit(0), hit(7, ordinal=1)] for _ in range(81)]
        stacks[17] = [hit(0)]
        with self.assertRaises(NailWeightConstrainedProjectionError):
            select_connected_weight_constrained_grid_v2(stacks, center_sample_index=40)

    def test_positive_component_is_selected_and_zero_ignored(self) -> None:
        stacks = [[hit(0), hit(7, ordinal=1)] for _ in range(81)]
        result = select_connected_weight_constrained_grid_v2(
            stacks, center_sample_index=40
        )
        self.assertEqual(result["selected_raw_component_id"], 7)
        self.assertTrue(all(row["raw_component_id"] == 7 for row in result["selected_hits"]))


class ReferenceBindingTests(unittest.TestCase):
    def points(self, offset: float = 0.0) -> list[list[float]]:
        return [[offset, 0.0, 0.0] for _ in range(81)]

    def test_complete_bounded_grid_passes(self) -> None:
        result = validate_reference_bound_candidate(
            reference_center=[0.0, 0.0, 0.0],
            candidate_center=[0.001, 0.0, 0.0],
            projected_points=self.points(0.001),
            expected_points=self.points(0.0),
        )
        self.assertTrue(result["all_reference_binding_gates_passed"])

    def test_center_or_centroid_escape_fails(self) -> None:
        with self.assertRaisesRegex(KiraR24ComponentContractError, "candidate center"):
            validate_reference_bound_candidate(
                reference_center=[0.0, 0.0, 0.0],
                candidate_center=[0.0016, 0.0, 0.0],
                projected_points=self.points(),
                expected_points=self.points(),
            )
        with self.assertRaisesRegex(KiraR24ComponentContractError, "centroid"):
            validate_reference_bound_candidate(
                reference_center=[0.0, 0.0, 0.0],
                candidate_center=[0.0, 0.0, 0.0],
                projected_points=self.points(0.0016),
                expected_points=self.points(0.0016),
            )

    def test_sample_displacement_and_incomplete_grid_fail(self) -> None:
        projected = self.points()
        projected[-1] = [0.0041, 0.0, 0.0]
        with self.assertRaisesRegex(KiraR24ComponentContractError, "4 mm"):
            validate_reference_bound_candidate(
                reference_center=[0.0, 0.0, 0.0],
                candidate_center=[0.0, 0.0, 0.0],
                projected_points=projected,
                expected_points=self.points(),
            )
        with self.assertRaisesRegex(KiraR24ComponentContractError, "9x9"):
            validate_reference_bound_candidate(
                reference_center=[0.0, 0.0, 0.0],
                candidate_center=[0.0, 0.0, 0.0],
                projected_points=self.points()[:-1],
                expected_points=self.points()[:-1],
            )


class PoseRenderTransactionTests(unittest.TestCase):
    def test_complete_pose_matrix_passes(self) -> None:
        candidate = digest("candidate")
        result = validate_pose_gate_matrix(valid_pose_matrix(candidate), candidate)
        self.assertEqual(result["required_pose_count"], len(REQUIRED_POSE_KEYS))

    def test_pose_contact_intersection_or_clearance_failure_stops(self) -> None:
        candidate = digest("candidate")
        for field, value in (
            ("contact_gate_passed", False),
            ("exact_body_nail_crossing_pair_count", 1),
            ("maximum_clearance_m", MAXIMUM_CLEARANCE_M + 0.000001),
        ):
            matrix = valid_pose_matrix(candidate)
            matrix["poses"][0][field] = value
            with self.assertRaises(KiraR24ComponentContractError):
                validate_pose_gate_matrix(matrix, candidate)

    def test_missing_pose_fails(self) -> None:
        candidate = digest("candidate")
        matrix = valid_pose_matrix(candidate)
        matrix["poses"].pop()
        with self.assertRaisesRegex(KiraR24ComponentContractError, "inventory"):
            validate_pose_gate_matrix(matrix, candidate)

    def test_exact_png_inventory_passes_and_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = {}
            for key in EXPECTED_RENDER_KEYS:
                path = root / f"{key}.png"
                path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
                records[key] = path.name
            result = validate_render_inventory(root, records)
            self.assertEqual(result["render_count"], 8)
            bad = dict(records)
            bad.pop(EXPECTED_RENDER_KEYS[-1])
            with self.assertRaisesRegex(KiraR24ComponentContractError, "eight"):
                validate_render_inventory(root, bad)

    def test_no_save_transaction_requires_order_and_forbids_save(self) -> None:
        events = [
            "exact_bindings_verified",
            "components_built_in_memory",
            "pose_gates_validated",
            "renders_validated",
            "protected_state_reverified",
            "evidence_written",
            "no_save_exit",
        ]
        self.assertTrue(validate_no_save_transaction(events)["transaction_passed"])
        swapped = copy.copy(events)
        swapped[2], swapped[3] = swapped[3], swapped[2]
        with self.assertRaisesRegex(KiraR24ComponentContractError, "out of order"):
            validate_no_save_transaction(swapped)
        with self.assertRaisesRegex(KiraR24ComponentContractError, "save event"):
            validate_no_save_transaction(events[:-1] + ["save_blend", "no_save_exit"])


if __name__ == "__main__":
    unittest.main()
