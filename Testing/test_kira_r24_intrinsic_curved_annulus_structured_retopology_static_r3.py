from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3.py"
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3"
)
R19_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
CLASSIC_BLEND = ROOT / "Avatar/avatar_builder/tooling/mb_lab_official/data/humanoid_library.blend"


def load_module():
    spec = importlib.util.spec_from_file_location("kira_r24_r3_static", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load R3 static evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntrinsicCurvedAnnulusR3StaticGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.contract = cls.module.load_sealed_contract()
        cls.context = cls.module.exact_context()

    def paired_exact_evidence(self) -> dict[str, object]:
        module = self.module
        expected = module.expected_exact_bindings(self.context)
        weighted = module.expected_weighted_points(self.context)
        return {
            "exact_bindings_r3": {
                name: module.paired_ledger(copy.deepcopy(records))
                for name, records in expected.items()
            },
            "protected_attributes_r3": {
                name: module.paired_ledger(copy.deepcopy(records))
                for name, records in weighted.items()
            },
        }

    def validate_exact(self, evidence: dict[str, object]) -> set[str]:
        failures: set[str] = set()
        self.module._validate_exact_bindings(evidence, self.context, failures)
        return failures

    def uv_evidence(self) -> dict[str, object]:
        module = self.module
        source = self.context["source_mesh"]
        cycle = self.contract["exact_topology"]["outer_boundary_cycle"]
        source_face = sorted(self.context["domains"]["estar"])[0]
        triangle = list(source["faces"][source_face])
        barycentric = [1.0, 0.0, 0.0]
        uv = list(source["texcoords"][triangle[0]])
        evidence = {
            "topology": {
                "face_ledger": module.ledger([
                    {
                        "face_id": 0,
                        "vertices": [cycle[0], cycle[1], 1000],
                        "material_index": 5,
                    }
                ])
            },
            "provenance": {
                "new_vertex_ledger": module.ledger([
                    {
                        "vertex_index": 1000,
                        "source_face_index": source_face,
                        "source_triangle": triangle,
                        "barycentric": barycentric,
                        "uv_records": [{"layer": "TEXCOORD_0", "uv": uv}],
                    }
                ])
            },
        }
        evidence["topology"]["uv_corner_ledger"] = module.ledger(
            module.expected_uv_corner_records(evidence, self.context)
        )
        return evidence

    def test_01_r2_final_package_and_audit_are_byte_exact(self) -> None:
        resolved = self.module.validate_parent_bindings(self.contract)
        self.assertEqual(len(resolved), 7)
        audit = resolved["r2_independent_audit"]
        self.assertEqual(
            self.module.sha256_file(audit),
            "e865a0e9873a988eb369d799f1332afa60ef8f699c386886ce910ce12b3ba32e",
        )

    def test_02_sealed_contract_and_worker_semantic_identity_are_exact(self) -> None:
        self.assertEqual(
            self.module.canonical_sha256(self.module._contract_semantic_projection(self.contract)),
            self.module.SEALED_CONTRACT_SEMANTIC_SHA256,
        )
        self.assertEqual(
            self.module.normalized_worker_sha256(),
            self.contract["authorized_implementation"]["worker_semantic_sha256"],
        )
        self.assertEqual(self.module.contract_bound_failures(self.contract), set())

    def test_03_caller_cannot_replace_or_weaken_sealed_bounds(self) -> None:
        attacks = []
        for angle, area, maximum in (
            (-1.0, -1.0, 160),
            (-math.inf, -math.inf, 160),
            (0.5, 1e-10, 160.5),
            (12.0, float("nan"), 160),
            (12.0, 1e-10, -1),
        ):
            altered = copy.deepcopy(self.contract)
            altered["metric_bounds"] = {
                "minimum_render_triangle_angle_degrees": angle,
                "minimum_render_triangle_area_m2": area,
                "maximum_new_interior_vertices": maximum,
            }
            attacks.append(altered)
        for altered in attacks:
            with self.subTest(bounds=altered["metric_bounds"]):
                failures = self.module._caller_contract_failures(altered, self.contract)
                self.assertIn("contract:caller_mapping_identity", failures)
                self.assertGreaterEqual(len(failures), 2)

    def test_04_real_classic_blend_is_structurally_parseable(self) -> None:
        summary = self.module.parse_blend_artifact(CLASSIC_BLEND)
        self.assertEqual(summary["header"], "BLENDER-v401")
        self.assertGreater(summary["dna"]["structure_count"], 0)
        for code in ("OB", "ME", "AR", "AC", "MA"):
            self.assertGreater(len(summary["semantic_ids"][code]), 0)

    def test_05_real_compressed_r19_blend_has_required_semantic_identity(self) -> None:
        summary = self.module.parse_blend_artifact(R19_BLEND)
        self.assertTrue(summary["compressed_zstd"])
        self.assertEqual(summary["header"], "BLENDER17-01v0501")
        evidence = {
            "artifact": {
                "path": R19_BLEND.relative_to(ROOT).as_posix(),
                "blend_structure": summary,
            }
        }
        failures: set[str] = set()
        self.module._validate_artifact_r3(evidence, self.contract, failures, ROOT)
        self.assertEqual(failures, set())

    def test_06_eighteen_byte_and_header_only_forgeries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kira_r24_r3_blend_forge_") as raw:
            root = Path(raw)
            for name, payload in (
                ("candidate.blend", b"NOT_A_BLENDER_FILE"),
                ("header.blend", b"BLENDER-v401"),
                ("extended.blend", b"BLENDER17-01v0501"),
            ):
                path = root / name
                path.write_bytes(payload)
                with self.subTest(name=name):
                    evidence = {"artifact": {"path": name, "blend_structure": {}}}
                    failures: set[str] = set()
                    self.module._validate_artifact_r3(evidence, self.contract, failures, root)
                    self.assertIn("artifact_r3:parseable_blend", failures)
                    self.assertIn("artifact_r3:semantic_identity", failures)

    def test_07_topology_boundary_coordinates_are_bound_to_source_and_point_ledger(self) -> None:
        module = self.module
        points = module.r2.expected_outer_boundary_records(self.context)["POINT"]
        evidence = {
            "topology": {"vertex_coordinate_ledger": module.ledger([
                {"vertex_index": row["vertex_index"], "coordinate_m": copy.deepcopy(row["coordinate_m"])}
                for row in points
            ])},
            "protected_records": {
                "outer_boundary": {"POINT": module.paired_ledger(copy.deepcopy(points))}
            },
        }
        failures: set[str] = set()
        module._validate_boundary_coordinates(evidence, self.context, failures)
        self.assertEqual(failures, set())
        rows = evidence["topology"]["vertex_coordinate_ledger"]["records"]
        rows[0]["coordinate_m"][0] += 0.01
        evidence["topology"]["vertex_coordinate_ledger"] = module.ledger(rows)
        failures = set()
        module._validate_boundary_coordinates(evidence, self.context, failures)
        self.assertIn("topology_r3:boundary_coordinates_equal_source", failures)
        self.assertIn("topology_r3:boundary_coordinates_equal_protected_point_ledger", failures)

    def test_08_extreme_uv_values_are_rejected_by_source_derivation(self) -> None:
        evidence = self.uv_evidence()
        failures: set[str] = set()
        self.module._validate_uvs(evidence, self.context, failures)
        self.assertEqual(failures, set())
        rows = evidence["provenance"]["new_vertex_ledger"]["records"]
        rows[0]["uv_records"][0]["uv"] = [999.0, -999.0]
        evidence["provenance"]["new_vertex_ledger"] = self.module.ledger(rows)
        failures = set()
        self.module._validate_uvs(evidence, self.context, failures)
        self.assertIn("uv_r3:source_derived_provenance", failures)

    def test_09_complete_face_corner_uv_topology_is_required(self) -> None:
        evidence = self.uv_evidence()
        rows = evidence["topology"]["uv_corner_ledger"]["records"]
        rows.pop()
        evidence["topology"]["uv_corner_ledger"] = self.module.ledger(rows)
        failures: set[str] = set()
        self.module._validate_uvs(evidence, self.context, failures)
        self.assertIn("uv_r3:complete_exact_corner_topology", failures)

    def test_10_complete_exact_material_data_is_required(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["material_inventory"]["candidate"]["records"]
        rows[0].pop("preserved_material_state_sha256")
        evidence["exact_bindings_r3"]["material_inventory"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:material_inventory:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_11_fake_bone_names_are_rejected(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["armature_inventory"]["candidate"]["records"]
        rows[0]["bone_names"] = [f"fake_{index}" for index in range(188)]
        rows[0]["bone_names_sha256"] = self.module.canonical_sha256(rows[0]["bone_names"])
        evidence["exact_bindings_r3"]["armature_inventory"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:armature_inventory:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_12_outside_and_boundary_native_weights_are_required(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["protected_attributes_r3"]["outside_estar"]["candidate"]["records"]
        rows[0].pop("native_weights")
        evidence["protected_attributes_r3"]["outside_estar"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "protected_attributes_r3:outside_estar:weighted_points:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_13_zero_action_digests_are_rejected(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["action_inventory"]["candidate"]["records"]
        for row in rows:
            row["direct_blend_block_sha256"] = "0" * 64
        evidence["exact_bindings_r3"]["action_inventory"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:action_inventory:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_14_zero_or_fabricated_morph_digest_is_rejected(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["morph_inventory"]["candidate"]["records"]
        rows[0]["morph_inventory_sha256"] = "0" * 64
        evidence["exact_bindings_r3"]["morph_inventory"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:morph_inventory:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_15_arbitrary_interface_coordinates_are_rejected(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["interface_local_coordinates"]["candidate"]["records"]
        rows[0]["coordinate_m"] = [999.0, 999.0, 999.0]
        evidence["exact_bindings_r3"]["interface_local_coordinates"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:interface_local_coordinates:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_16_zero_inherited_pair_measurement_hashes_are_rejected(self) -> None:
        evidence = self.paired_exact_evidence()
        rows = evidence["exact_bindings_r3"]["inherited_intersection_measurements"]["candidate"]["records"]
        for row in rows:
            row["measurement_sha256"] = "0" * 64
        evidence["exact_bindings_r3"]["inherited_intersection_measurements"]["candidate"] = self.module.ledger(rows)
        self.assertIn(
            "exact_bindings_r3:inherited_intersection_measurements:candidate_exact",
            self.validate_exact(evidence),
        )

    def test_17_package_inventory_is_exact_and_audit_aware(self) -> None:
        pre = self.contract["package_inventory"]["pre_audit_exact"]
        with tempfile.TemporaryDirectory(prefix="kira_r24_r3_inventory_") as raw:
            root = Path(raw)
            for name in pre:
                (root / name).write_bytes(b"")
            self.assertEqual(self.module.package_inventory_status(root)["state"], "PRE_AUDIT_EXACT")
            (root / "INDEPENDENT_STATIC_AUDIT.md").write_bytes(b"")
            self.assertEqual(self.module.package_inventory_status(root)["state"], "POST_AUDIT_EXACT")
            (root / "unexpected.txt").write_bytes(b"")
            self.assertEqual(self.module.package_inventory_status(root)["state"], "INVALID")

    def test_18_static_gate_remains_ineligible_and_execution_unauthorized(self) -> None:
        result = self.module.evaluate_measured_candidate_evidence(None, self.contract)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["failure_names"], ["measured_candidate_evidence_absent"])
        altered = copy.deepcopy(self.contract)
        altered["metric_bounds"]["minimum_render_triangle_angle_degrees"] = 0.5
        result = self.module.evaluate_measured_candidate_evidence(None, altered)
        self.assertFalse(result["eligible"])
        self.assertIn("contract:caller_mapping_identity", result["failure_names"])


if __name__ == "__main__":
    unittest.main()
