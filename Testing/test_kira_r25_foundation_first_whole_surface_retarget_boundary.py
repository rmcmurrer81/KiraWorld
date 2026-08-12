import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_foundation_first_whole_surface_retarget_boundary_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR25FoundationFirstBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_all_immutable_bindings_match_current_bytes(self) -> None:
        groups = self.contract["immutable_inputs"]
        bindings = []
        for group in groups.values():
            for value in group.values():
                if isinstance(value, dict) and "path" in value and "sha256" in value:
                    bindings.append(value)
        self.assertGreaterEqual(len(bindings), 12)
        for binding in bindings:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            if "bytes" in binding:
                self.assertEqual(path.stat().st_size, binding["bytes"], binding["path"])
            self.assertEqual(sha256(path), binding["sha256"], binding["path"])

    def test_r19_is_reference_only_and_exact_mask_is_excluded(self) -> None:
        inputs = self.contract["immutable_inputs"]
        r19 = inputs["r19_appearance_target"]
        mask = inputs["r20_exact_rejected_region"]
        self.assertTrue(r19["must_remain_byte_for_byte_unchanged"])
        self.assertFalse(r19["topology_or_rig_donor"])
        self.assertTrue(mask["excluded_from_r19_appearance_fit"])
        self.assertEqual(mask["selected_face_count"], 376)
        self.assertEqual(mask["incident_vertex_count"], 206)
        self.assertEqual(mask["removable_interior_vertex_count"], 172)
        self.assertEqual(mask["interface_vertex_count"], 34)
        self.assertEqual(mask["interface_edge_count"], 34)

    def test_foundation_remains_the_only_candidate_topology(self) -> None:
        foundation = self.contract["immutable_inputs"]["qualified_continuous_foundation"]
        topology = foundation["topology"]
        self.assertTrue(foundation["candidate_topology_donor"])
        self.assertTrue(foundation["must_remain_topologically_identical"])
        self.assertEqual(
            topology,
            {
                "vertices": 14658,
                "edges": 30632,
                "faces": 15976,
                "connected_components": 1,
                "boundary_edges": 0,
                "nonmanifold_internal_edges": 0,
                "degenerate_faces": 0,
                "duplicate_triangles": 0,
                "nonadjacent_intersection_pairs": 0,
            },
        )

    def test_no_cut_graft_or_r24_minor_successor(self) -> None:
        method = self.contract["materially_different_method"]
        terminal = self.contract["immutable_inputs"]["terminal_r24_evidence"]
        self.assertFalse(method["topology_change_allowed"])
        self.assertFalse(method["cut_or_graft_allowed"])
        self.assertFalse(method["r19_pelvic_vertex_or_face_copy_allowed"])
        self.assertTrue(terminal["must_not_be_reopened_as_minor_r8_or_v4"])

    def test_all_execution_and_acceptance_truth_fails_closed(self) -> None:
        scope = self.contract["scope"]
        for key in (
            "runtime_eligible",
            "owner_approved",
            "execution_authority",
            "blender_authority",
            "activation_authority",
            "assignment_authority",
            "export_authority",
        ):
            self.assertFalse(scope[key], key)
        for key, value in self.contract["required_preconditions_before_blender"].items():
            self.assertFalse(value, key)
        truth = self.contract["implementation_truth"]
        self.assertTrue(truth["r25_contract_only"])
        for key, value in truth.items():
            if key != "r25_contract_only":
                self.assertFalse(value, key)

    def test_receipt_is_authoritative_but_not_implemented(self) -> None:
        receipt = self.contract["authoritative_artifact_boundary"]
        self.assertEqual(receipt["identity"], "canonical_mesh_rig_material_receipt")
        self.assertFalse(receipt["blend_is_authoritative"])
        self.assertFalse(receipt["implemented"])


if __name__ == "__main__":
    unittest.main()
