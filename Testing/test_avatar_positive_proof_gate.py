from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_positive_proof_gate import (  # noqa: E402
    _project_file,
    build_downstream_release_plan,
    evaluate_positive_proof,
)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AvatarPositiveProofGateTests(unittest.TestCase):
    def install_fixture(self, root: Path) -> Path:
        policy = {
            "schema_version": 1,
            "owner_authority_id": "real_robert",
            "maximum_concurrent_downstream_builds": 1,
            "required_component_artifacts": ["body", "eyes", "hair", "clothing", "rig"],
            "required_gates": [
                "topology_lane_correct",
                "visual_likeness_reviewed",
                "clothed_visual_integrity",
                "stable_rig",
                "walk_sit_reach_deformation",
                "skin_material_and_deformation_integrity",
                "face_controls",
                "visible_realistic_eyes",
                "feet_and_ground_contact",
                "walk_stop_turn",
                "sit_stand_lie_rise",
                "prop_contact",
                "separate_clothing_integrity",
                "privacy_review",
                "owner_visual_approval",
            ],
            "required_owner_decision": "approve_body_for_two_subject_autobuild_qualification",
            "runtime_activation_allowed": False,
            "current_proof_path": "",
        }
        policy_path = root / "Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json"
        registry_path = root / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        backlog_path = root / "Avatar/avatar_builder/authoring_backlogs/body_authoring_backlog_after_positive_proof_20260716.json"
        write_json(policy_path, policy)
        write_json(
            registry_path,
            {
                "schema_version": 1,
                "candidates": [
                    {
                        "canonical_candidate_id": "proof_person",
                        "subject_id": "proof_subject",
                    }
                ],
            },
        )
        write_json(
            backlog_path,
            {
                "candidate_identity_registry_sha256": sha(registry_path),
                "next_owner_reviewed_likeness_builds": [
                    {"candidate_id": "proof_person"},
                    {"candidate_id": "next_person"},
                ],
            },
        )
        component_bindings = {}
        component_hashes = {}
        for name in policy["required_component_artifacts"]:
            path = root / f"artifacts/{name}.bin"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture-{name}".encode())
            component_bindings[name] = {"path": f"artifacts/{name}.bin", "sha256": sha(path)}
            component_hashes[name] = sha(path)
        approval = {
            "owner_authority_id": "real_robert",
            "decision": "approve_body_for_two_subject_autobuild_qualification",
            "candidate_id": "proof_person",
            "subject_id": "proof_subject",
            "build_id": "proof_build_v1",
            "reviewed_in_motion": True,
            "reviewed_clothed": True,
            "counts_toward_two_subject_gate": True,
            "release_downstream_autobuild": False,
            "component_sha256": component_hashes,
        }
        approval_path = root / "reviews/owner_approval.json"
        write_json(approval_path, approval)
        proof = {
            "schema_version": 1,
            "status": "owner_approved_positive_proof",
            "candidate_id": "proof_person",
            "subject_id": "proof_subject",
            "build_id": "proof_build_v1",
            "candidate_identity_registry_sha256": sha(registry_path),
            "components": component_bindings,
            "gates": {name: True for name in policy["required_gates"]},
            "owner_approval": {
                "path": "reviews/owner_approval.json",
                "sha256": sha(approval_path),
            },
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        proof_path = root / "reviews/positive_proof.json"
        write_json(proof_path, proof)
        return proof_path

    def test_production_gate_is_locked_without_a_proof(self) -> None:
        result = evaluate_positive_proof(PROJECT_ROOT)
        self.assertFalse(result["release_allowed"])
        self.assertEqual(result["status"], "locked_no_positive_proof")

    def test_complete_exact_fixture_qualifies_only_one_subject(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proof_path = self.install_fixture(root)
            result = evaluate_positive_proof(root, proof_path)
            self.assertTrue(result["subject_qualification_ready"])
            self.assertFalse(result["release_allowed"])
            self.assertEqual(result["maximum_concurrent_downstream_builds"], 1)
            self.assertEqual(
                result["status"], "positive_proof_passed_subject_qualification_only"
            )
            with self.assertRaisesRegex(ValueError, "one-subject positive proof"):
                build_downstream_release_plan(root, result)

    def test_one_failed_motion_gate_keeps_everything_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proof_path = self.install_fixture(root)
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            proof["gates"]["feet_and_ground_contact"] = False
            write_json(proof_path, proof)
            result = evaluate_positive_proof(root, proof_path)
            self.assertFalse(result["release_allowed"])
            self.assertIn("gate_not_passed:feet_and_ground_contact", result["failures"])

    def test_parent_directory_symlink_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.install_fixture(root)
            alias = root / "reviews_alias"
            try:
                alias.symlink_to(root / "reviews", target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable for this Windows account: {exc}")
            result = evaluate_positive_proof(root, Path("reviews_alias/positive_proof.json"))
            self.assertFalse(result["release_allowed"])
            self.assertEqual(result["status"], "locked_invalid_positive_proof")
            self.assertIn("positive_proof_path_invalid", result["failures"])
            absolute_result = evaluate_positive_proof(
                root, alias / "positive_proof.json"
            )
            self.assertFalse(absolute_result["release_allowed"])
            self.assertIn("positive_proof_path_invalid", absolute_result["failures"])

    def test_parent_symlink_check_is_not_limited_to_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = Path.is_symlink

            def fake_is_symlink(path: Path) -> bool:
                if path == root / "review_parent":
                    return True
                return original(path)

            with mock.patch.object(Path, "is_symlink", fake_is_symlink):
                self.assertIsNone(
                    _project_file(root, "review_parent/proof.json")
                )


if __name__ == "__main__":
    unittest.main()
