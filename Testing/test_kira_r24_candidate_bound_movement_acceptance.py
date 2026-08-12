#!/usr/bin/env python3
"""CPU/static tests for the future Kira R24 movement acceptance binding."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import kira_r24_candidate_bound_movement_acceptance as acceptance  # noqa: E402


CONTRACT_PATH = PROJECT_ROOT / (
    "Avatar/movement_library/"
    "kira_r24_candidate_bound_movement_acceptance_contract_v1.json"
)
WORKER_PATH = TOOLS_DIR / "kira_r24_candidate_bound_movement_acceptance.py"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class R24CandidateBoundMovementAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = acceptance.load_json(CONTRACT_PATH)

    def _fixture_release(self, root: Path) -> dict[str, object]:
        blend = root / "candidate.blend"
        evidence = root / "candidate_build_evidence.json"
        blend_bytes = b"synthetic-test-only-r24-blend-binding"
        evidence_bytes = b'{"synthetic_test_fixture":true}\n'
        blend.write_bytes(blend_bytes)
        evidence.write_bytes(evidence_bytes)
        fixed = "a" * 64
        oral = [
            {
                "role": role,
                "object": f"fixture_{role}",
                "mesh_data": f"fixture_{role}_mesh",
                "geometry_uv_sha256": fixed,
                "positive_weight_assignment_sha256": "b" * 64,
            }
            for role in ("lips", "teeth", "mouth_interior")
        ]
        return {
            "schema_version": acceptance.RELEASE_SCHEMA,
            "authorization_scope": "STATIC_VALIDATION_ONLY_NO_BLENDER_AUTHORIZATION",
            "candidate_status": "PRIVATE_INACTIVE_COMPLETE_OWNER_REVIEW_CANDIDATE",
            "contract_sha256": acceptance.sha256_file(CONTRACT_PATH),
            "candidate_id": "KIRA_R24_SYNTHETIC_TEST_FIXTURE",
            "candidate_blend": "candidate.blend",
            "candidate_blend_sha256": _digest(blend_bytes),
            "candidate_build_evidence": "candidate_build_evidence.json",
            "candidate_build_evidence_sha256": _digest(evidence_bytes),
            "body_object": "Fixture_R24_Body",
            "body_geometry_uv_sha256": "c" * 64,
            "body_positive_weight_assignment_sha256": "d" * 64,
            "rig_object": "Fixture_R24_Native_188_Rig",
            "rig_rest_sha256": "e" * 64,
            "rig_joint_count": 188,
            "oral_component_bindings": oral,
            "candidate_flags": {
                "private": True,
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_eligible": False,
                "complete_connected_body_claim_is_candidate_only": True,
                "owner_body_approval_inferred": False,
                "biological_function_claimed": False,
            },
        }

    def _fixture_evidence(self, release: dict[str, object]) -> dict[str, object]:
        scenarios = {value["id"]: value for value in self.contract["movement_scenarios"]}
        results = []
        for index, identifier in enumerate(sorted(acceptance.REQUIRED_SCENARIO_IDS)):
            results.append(
                {
                    "id": identifier,
                    "geometry_rig_status": "PASS",
                    "action_or_probe_sha256": f"{index + 1:064x}",
                    "sample_count": 3,
                    "neutral_return_verified": True,
                    "maximum_exact_nonadjacent_self_intersection_pairs": 0,
                    "maximum_pose_induced_or_exposed_pairs": 0,
                    "maximum_body_nail_intersection_pairs": 0,
                    "maximum_unintended_body_prop_penetration_pairs": 0,
                    "deformation_continuity_passed": True,
                    "required_measurements_present": list(scenarios[identifier]["required_measurements"]),
                    "phase_bound_render_ids": [f"{identifier}:start", f"{identifier}:end"],
                    "semantic_world_status": "NOT_EVALUATED_IN_BODY_GATE",
                    "biological_function_claimed": False,
                }
            )
        identity_keys = (
            "candidate_id",
            "candidate_blend_sha256",
            "body_object",
            "body_geometry_uv_sha256",
            "body_positive_weight_assignment_sha256",
            "rig_object",
            "rig_rest_sha256",
            "rig_joint_count",
            "oral_component_bindings",
        )
        return {
            "schema_version": acceptance.EVIDENCE_SCHEMA,
            "contract_sha256": acceptance.sha256_file(CONTRACT_PATH),
            "candidate_binding": {key: release[key] for key in identity_keys},
            "preservation": {
                "source_candidate_sha256_before": release["candidate_blend_sha256"],
                "source_candidate_sha256_after": release["candidate_blend_sha256"],
                "body_geometry_uv_sha256_before": release["body_geometry_uv_sha256"],
                "body_geometry_uv_sha256_after": release["body_geometry_uv_sha256"],
                "body_positive_weight_assignment_sha256_before": release["body_positive_weight_assignment_sha256"],
                "body_positive_weight_assignment_sha256_after": release["body_positive_weight_assignment_sha256"],
                "rig_rest_sha256_before": release["rig_rest_sha256"],
                "rig_rest_sha256_after": release["rig_rest_sha256"],
                "fresh_reopen_verified": True,
                "source_candidate_unchanged": True,
                "new_actions_unassigned_after_reopen": True,
                "temporary_props_fixtures_cameras_and_collections_absent_after_reopen": True,
                "private": True,
                "inactive": True,
                "unpublished": True,
                "body_mesh_mutated": False,
                "rig_rest_mutated": False,
                "weight_assignments_mutated": False,
                "runtime_activation_assignment_export_or_publication_performed": False,
            },
            "scenario_results": results,
            "world_person_runtime_status": "NOT_EVALUATED_IN_BODY_GATE",
            "world_interaction_results": [],
            "biological_function_claimed": False,
            "owner_decision": {
                "status": "PENDING_NOT_APPROVED",
                "path": None,
                "sha256": None,
            },
        }

    def test_contract_is_complete_static_and_unbound(self) -> None:
        summary = acceptance.validate_contract(self.contract)
        self.assertEqual(summary["scenario_count"], 20)
        self.assertEqual(summary["capability_level"], "CONTRACT_ONLY")
        self.assertFalse(summary["candidate_bound"])
        self.assertFalse(summary["blender_authorized"])
        for key in self.contract["release_contract"]["required_exact_fields"]:
            self.assertIsNone(self.contract["prepared_candidate_binding"][key])

    def test_all_requested_motion_domains_are_separate_and_present(self) -> None:
        ids = {value["id"] for value in self.contract["movement_scenarios"]}
        self.assertEqual(ids, acceptance.REQUIRED_SCENARIO_IDS)
        for identifier in (
            "left_knee_bend",
            "right_knee_bend",
            "bilateral_knee_bend",
            "seated_supported_contact",
            "supine_lie_down_and_rise",
            "side_lying_left_right_and_rise",
            "walk_readiness",
            "jog_readiness",
            "run_readiness",
            "book_reach_grasp_contact",
            "tablet_reach_grasp_contact",
            "phone_reach_grasp_contact",
            "door_push_handle_contact",
            "door_pull_handle_contact",
            "handwashing_motion_envelope",
            "shower_motion_envelope",
            "bath_motion_envelope",
            "speech_mouth_lipsync_hooks",
        ):
            self.assertIn(identifier, ids)

    def test_preserved_small_evidence_anchors_are_byte_exact(self) -> None:
        checked = acceptance.validate_reference_anchors(self.contract, PROJECT_ROOT)
        self.assertEqual(len(checked), 6)
        self.assertTrue(all(len(value["sha256"]) == 64 for value in checked))

    def test_known_rejections_are_lessons_not_sources_or_passes(self) -> None:
        records = self.contract["preserved_method_evidence"]
        dispositions = {value["disposition"] for value in records}
        self.assertIn("REJECTED_METHOD_LEARNING_ONLY", dispositions)
        self.assertIn("REJECTED_NOT_A_MOVEMENT_SOURCE", dispositions)
        joined = " ".join(value["lesson"] for value in records).lower()
        self.assertIn("intersection", joined)
        self.assertIn("deformation", joined)
        self.assertIn("contact measurement", joined)

    def test_release_requires_every_exact_candidate_binding_and_real_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = self._fixture_release(root)
            bound = acceptance.validate_release(self.contract, CONTRACT_PATH, release, root)
            self.assertEqual(bound["candidate_id"], "KIRA_R24_SYNTHETIC_TEST_FIXTURE")
            self.assertFalse(bound["blender_authorized"])
            self.assertFalse(bound["runtime_authorized"])

            missing = deepcopy(release)
            missing["body_object"] = None
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_release(self.contract, CONTRACT_PATH, missing, root)

            wrong_hash = deepcopy(release)
            wrong_hash["candidate_blend_sha256"] = "f" * 64
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_release(self.contract, CONTRACT_PATH, wrong_hash, root)

    def test_release_rejects_path_escape_wrong_rig_and_known_rejected_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = self._fixture_release(root)
            escaped = deepcopy(release)
            escaped["candidate_blend"] = "../candidate.blend"
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_release(self.contract, CONTRACT_PATH, escaped, root)
            wrong_rig = deepcopy(release)
            wrong_rig["rig_joint_count"] = 187
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_release(self.contract, CONTRACT_PATH, wrong_rig, root)
            rejected_contract = deepcopy(self.contract)
            rejected_contract["release_contract"]["rejected_candidate_hashes_must_not_be_released"] = [
                release["candidate_blend_sha256"]
            ]
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_release(rejected_contract, CONTRACT_PATH, release, root)

    def test_complete_synthetic_fixture_reaches_body_hooks_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = self._fixture_release(root)
            evidence = self._fixture_evidence(release)
            result = acceptance.validate_evidence(
                self.contract, CONTRACT_PATH, release, evidence, root
            )
            self.assertEqual(result["capability_level"], "BODY_HOOKS_VERIFIED")
            self.assertEqual(result["status"], "GEOMETRY_RIG_PASS_PENDING_OWNER_REVIEW")
            self.assertEqual(result["scenario_count"], 20)
            self.assertEqual(result["world_person_runtime_status"], "NOT_EVALUATED_IN_BODY_GATE")
            self.assertFalse(result["biological_function_claimed"])
            self.assertFalse(result["avatar_builder_method_promoted"])
            self.assertFalse(result["runtime_authorized"])

    def test_missing_scenario_collision_or_measurement_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = self._fixture_release(root)
            evidence = self._fixture_evidence(release)

            missing = deepcopy(evidence)
            missing["scenario_results"] = missing["scenario_results"][:-1]
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, missing, root)

            collision = deepcopy(evidence)
            collision["scenario_results"][0]["maximum_pose_induced_or_exposed_pairs"] = 1
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, collision, root)

            measurement = deepcopy(evidence)
            measurement["scenario_results"][0]["required_measurements_present"] = []
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, measurement, root)

    def test_cross_candidate_and_world_or_biological_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = self._fixture_release(root)
            evidence = self._fixture_evidence(release)

            cross = deepcopy(evidence)
            cross["candidate_binding"]["body_object"] = "Another_Body"
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, cross, root)

            world = deepcopy(evidence)
            world["scenario_results"][0]["semantic_world_status"] = "PASSED"
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, world, root)

            biological = deepcopy(evidence)
            biological["biological_function_claimed"] = True
            with self.assertRaises(acceptance.AcceptanceError):
                acceptance.validate_evidence(self.contract, CONTRACT_PATH, release, biological, root)

    def test_worker_is_cpu_static_and_has_no_execution_surface(self) -> None:
        source = WORKER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import) and node.names
        }
        imports.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertNotIn("bpy", imports)
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("torch", imports)
        self.assertNotIn("cv2", imports)
        self.assertNotIn("sounddevice", imports)
        self.assertNotIn("requests", imports)
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("Popen(", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
