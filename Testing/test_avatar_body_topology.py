from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_body_topology import (  # noqa: E402
    RIG_STABILITY_TESTS,
    evaluate_body_candidate_readiness,
    inspect_glb_topology,
)


def glb_bytes(document: dict) -> bytes:
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total = 12 + 8 + len(payload)
    return struct.pack("<4sII", b"glTF", 2, total) + struct.pack(
        "<II", len(payload), 0x4E4F534A
    ) + payload


def complete_rig_document() -> dict:
    joint_names = [
        "Pelvis",
        "Spine",
        "Neck",
        "Head",
        "LeftUpperArm",
        "LeftForeArm",
        "LeftHand",
        "RightUpperArm",
        "RightForeArm",
        "RightHand",
        "LeftUpLeg",
        "LeftLeg",
        "LeftFoot",
        "RightUpLeg",
        "RightLeg",
        "RightFoot",
        "LeftThumb1",
        "RightThumb1",
    ]
    nodes = [{"name": name} for name in joint_names]
    nodes.append({"name": "PRIVATE_RAW_MESH_NAME", "mesh": 0, "skin": 0})
    return {
        "asset": {"version": "2.0"},
        "accessors": [
            {"count": 300, "type": "VEC3", "componentType": 5126},
            {"count": 300, "type": "VEC4", "componentType": 5123},
            {"count": 300, "type": "VEC4", "componentType": 5126},
            {"count": 900, "type": "SCALAR", "componentType": 5123},
        ],
        "meshes": [
            {
                "name": "PRIVATE_INTIMATE_SURFACE_NAME",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2},
                        "indices": 3,
                    }
                ],
            }
        ],
        "nodes": nodes,
        "skins": [{"joints": list(range(len(joint_names)))}],
        "materials": [{"name": "PRIVATE_MATERIAL_NAME"}],
    }


def passing_attestations(digest: str) -> tuple[dict, dict]:
    base = {
        "artifact_sha256": digest,
        "exact_artifact_hash_verified": True,
        "review_status": "passed",
        "reviewed_by": "authorized_private_reviewer",
        "reviewed_at": "2026-07-16T00:00:00-04:00",
    }
    anatomy = {
        **base,
        "confirmed_adult_subject": True,
        "complete_adult_topology_review_passed": True,
        "continuous_body_surface_review_passed": True,
        "private_review_completed": True,
        "intimate_review_render_retained": False,
    }
    rig = {
        **base,
        "test_results": {name: "passed" for name in RIG_STABILITY_TESTS},
    }
    return anatomy, rig


class AvatarBodyTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, name: str, payload: bytes) -> Path:
        path = self.root / name
        path.write_bytes(payload)
        return path

    def test_malformed_glb_fails_closed_without_disclosing_path(self) -> None:
        path = self.write("PRIVATE_SOURCE.glb", b"not a glb")
        report = inspect_glb_topology(path, artifact_id="opaque_candidate")

        self.assertFalse(report["valid_glb"])
        self.assertFalse(report["humanoid_rig_structurally_ready"])
        self.assertNotIn(str(path), json.dumps(report))

    def test_mesh_without_skin_is_not_a_humanoid_rig(self) -> None:
        document = {
            "asset": {"version": "2.0"},
            "accessors": [{"count": 3}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        }
        report = inspect_glb_topology(self.write("mesh.glb", glb_bytes(document)))

        self.assertTrue(report["valid_glb"])
        self.assertFalse(report["humanoid_rig_structurally_ready"])
        self.assertEqual(report["topology_metrics"]["skin_count"], 0)

    def test_weighted_core_humanoid_is_structurally_ready_but_not_motion_proven(self) -> None:
        path = self.write("candidate.glb", glb_bytes(complete_rig_document()))
        report = inspect_glb_topology(path)

        self.assertTrue(report["humanoid_rig_structurally_ready"])
        self.assertFalse(report["stable_working_rig_proven"])
        self.assertFalse(report["anatomical_completeness_proven"])
        self.assertEqual(
            report["canonical_rig_evidence"]["missing_core_roles"], []
        )

    def test_mixamo_arm_and_leg_names_cover_the_canonical_limb_roles(self) -> None:
        document = complete_rig_document()
        for node in document["nodes"]:
            if node.get("name") == "LeftUpperArm":
                node["name"] = "mixamorig:LeftArm_09"
            elif node.get("name") == "RightUpperArm":
                node["name"] = "mixamorig:RightArm_033"
            elif node.get("name") == "LeftLeg":
                node["name"] = "mixamorig:LeftLeg_056"
            elif node.get("name") == "RightLeg":
                node["name"] = "mixamorig:RightLeg_061"

        report = inspect_glb_topology(
            self.write("mixamo-candidate.glb", glb_bytes(document))
        )

        self.assertTrue(report["humanoid_rig_structurally_ready"])
        self.assertEqual(report["canonical_rig_evidence"]["missing_core_roles"], [])

    def test_invalid_weight_accessor_layout_cannot_pass_as_weighted_rig(self) -> None:
        document = complete_rig_document()
        document["accessors"][1]["type"] = "VEC3"
        path = self.write("bad-weights.glb", glb_bytes(document))
        report = inspect_glb_topology(path)

        self.assertFalse(report["humanoid_rig_structurally_ready"])
        self.assertEqual(
            report["topology_metrics"]["weighted_skinned_primitive_count"], 0
        )
        self.assertGreater(
            report["topology_metrics"]["invalid_attribute_layout_count"], 0
        )

    def test_anatomy_and_motion_claims_require_exact_hash_attestations(self) -> None:
        path = self.write("candidate.glb", glb_bytes(complete_rig_document()))
        first = inspect_glb_topology(path)
        anatomy, rig = passing_attestations(first["sha256"])

        wrong_anatomy = dict(anatomy, artifact_sha256="f" * 64)
        wrong = inspect_glb_topology(
            path, anatomy_attestation=wrong_anatomy, rig_attestation=rig
        )
        self.assertFalse(wrong["anatomical_completeness_proven"])
        self.assertTrue(wrong["stable_working_rig_proven"])

        passed = inspect_glb_topology(
            path, anatomy_attestation=anatomy, rig_attestation=rig
        )
        self.assertTrue(passed["anatomical_completeness_proven"])
        self.assertTrue(passed["stable_working_rig_proven"])

    def test_reference_library_asset_cannot_be_promoted_to_candidate(self) -> None:
        path = self.write("reference.glb", glb_bytes(complete_rig_document()))
        first = inspect_glb_topology(path)
        anatomy, rig = passing_attestations(first["sha256"])
        report = inspect_glb_topology(
            path, anatomy_attestation=anatomy, rig_attestation=rig
        )
        readiness = evaluate_body_candidate_readiness(
            report,
            subject_id="robert_user_avatar",
            subject_maturity="adult",
            request_complete_adult_anatomy=True,
            lineage={
                "candidate_sha256": first["sha256"],
                "subject_id": "robert_user_avatar",
                "lineage_reviewed": True,
                "new_subject_specific_mesh_authored": False,
                "reference_mesh_copied_into_candidate": True,
                "selected_directly_from_reference_library": True,
                "body_and_clothes_are_separate_artifacts": True,
                "normal_review_route": "clothed_only",
            },
        )

        self.assertFalse(readiness["staging_allowed"])
        self.assertIn(
            "reference_library_asset_cannot_be_selected_as_candidate_body",
            readiness["failures"],
        )

    def test_new_hash_bound_adult_candidate_can_reach_private_clothed_stage(self) -> None:
        path = self.write("new-subject-body.glb", glb_bytes(complete_rig_document()))
        first = inspect_glb_topology(path)
        anatomy, rig = passing_attestations(first["sha256"])
        report = inspect_glb_topology(
            path, anatomy_attestation=anatomy, rig_attestation=rig
        )
        readiness = evaluate_body_candidate_readiness(
            report,
            subject_id="robert_user_avatar",
            subject_maturity="adult",
            request_complete_adult_anatomy=True,
            lineage={
                "candidate_sha256": first["sha256"],
                "subject_id": "robert_user_avatar",
                "lineage_reviewed": True,
                "new_subject_specific_mesh_authored": True,
                "reference_mesh_copied_into_candidate": False,
                "selected_directly_from_reference_library": False,
                "body_and_clothes_are_separate_artifacts": True,
                "normal_review_route": "clothed_only",
            },
        )

        self.assertTrue(readiness["staging_allowed"])
        self.assertEqual(readiness["status"], "ready_for_private_clothed_stage")
        self.assertFalse(readiness["runtime_activation_allowed"])

    def test_non_adult_candidate_cannot_use_adult_complete_topology_lane(self) -> None:
        path = self.write("new-subject-body.glb", glb_bytes(complete_rig_document()))
        first = inspect_glb_topology(path)
        anatomy, rig = passing_attestations(first["sha256"])
        report = inspect_glb_topology(
            path, anatomy_attestation=anatomy, rig_attestation=rig
        )
        readiness = evaluate_body_candidate_readiness(
            report,
            subject_id="non_adult_subject",
            subject_maturity="non_adult_doll_safe",
            request_complete_adult_anatomy=True,
            lineage={
                "candidate_sha256": first["sha256"],
                "subject_id": "non_adult_subject",
                "lineage_reviewed": True,
                "new_subject_specific_mesh_authored": True,
                "reference_mesh_copied_into_candidate": False,
                "selected_directly_from_reference_library": False,
                "body_and_clothes_are_separate_artifacts": True,
                "normal_review_route": "clothed_only",
            },
        )

        self.assertFalse(readiness["staging_allowed"])
        self.assertIn(
            "complete_adult_anatomy_forbidden_for_subject_maturity",
            readiness["failures"],
        )

    def test_public_report_omits_raw_names_and_private_path(self) -> None:
        path = self.write("owner-private-source.glb", glb_bytes(complete_rig_document()))
        report = inspect_glb_topology(path, artifact_id="robert_candidate_opaque")
        encoded = json.dumps(report)

        self.assertNotIn(str(path), encoded)
        self.assertNotIn("PRIVATE_RAW_MESH_NAME", encoded)
        self.assertNotIn("PRIVATE_INTIMATE_SURFACE_NAME", encoded)
        self.assertNotIn("PRIVATE_MATERIAL_NAME", encoded)
        self.assertFalse(report["privacy"]["preview_created"])


if __name__ == "__main__":
    unittest.main()
