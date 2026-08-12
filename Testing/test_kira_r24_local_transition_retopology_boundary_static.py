from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_retopology_boundary/"
    "LOCAL_TRANSITION_RETOPOLOGY_STATIC_PROPOSAL.md"
)
REPAIR_DOMAIN = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02/"
    "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
)
SOURCE_IDENTITY = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_30/"
    "SOURCE_RING_MAPPING_DIAGNOSTIC.json"
)
ATTEMPT46 = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_46/"
    "COMPOUND_LOCAL_BLOCKER_STARS_DIAGNOSTIC.json"
)
ATTEMPT47_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "ATTEMPT47_RUNTIME_WRAPPER_LOG_PREFLIGHT_CONFLICT_CHECKPOINT.md"
)
TOPOLOGY_DIAGNOSTIC = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_01/"
    "BLACKPROJECT_ATTEMPT02_INTERSECTION_TOPOLOGY.json"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compact_json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LocalTransitionRetopologyStaticBoundaryTests(unittest.TestCase):
    def test_bound_source_files_are_exact(self) -> None:
        expected = {
            "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/kira_r19_bald_targeted_material_movement_correction.blend": "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f",
            "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/BUILD_EVIDENCE.json": "f1c20f0570418506150f60df25a6b6ac548597b3108878b1920116f3d0fd714c",
            "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/PACKAGE_MANIFEST.json": "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c",
            "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/attempt_02/r19_patch_reconstruction_probe.blend": "47cbf26279bc3b75076caf43f96c1c3441dd86e48ad0c404f7a45504985add4d",
            "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/attempt_02/PATCH_RECONSTRUCTION_PROBE.json": "d168e7ee1051e9405d88371303625619bcf0f09cd2c66c89599b3a2567042a05",
            "Avatar/avatar_builder/asset_library/base_body_reference/base_female_character_blackproject_cc_by_4.glb": "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
            "Avatar/avatar_builder/asset_library/base_body_reference/base_female_character_blackproject_cc_by_4.AUTHORITY.json": "d632a501edb2177aed7299aa257b61784685bdf2d9c88fa280370b640c4b508c",
            "RecoverySprint/continuation_20260807/r24_blackproject_patch_reconstruction_diagnostic/attempt_01/BLACKPROJECT_ATTEMPT02_INTERSECTION_TOPOLOGY.json": "349bfe8d587dc45628679b5768d1e17255e3114b3a5eccc5d18437e26a4c3ded",
            "RecoverySprint/continuation_20260807/r24_blackproject_patch_reconstruction_diagnostic/attempt_02/BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json": "c14e5f7324ae3e4279eb6408b52de7eaecb372fb9afa8caf191f875b411473a3",
            "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_30/SOURCE_RING_MAPPING_DIAGNOSTIC.json": "d84c44d792cc4726507ff8a856ed67444e0918fb5c1a7e025a18502e6830c506",
            "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_46/COMPOUND_LOCAL_BLOCKER_STARS_DIAGNOSTIC.json": "5b6b0e7f4596dbb674a8bc36d59a9cc31f122eadaa4a39125727d6ea0c38ea0a",
            "RecoverySprint/continuation_20260808/ATTEMPT47_RUNTIME_WRAPPER_LOG_PREFLIGHT_CONFLICT_CHECKPOINT.md": "8e6c2eb624e5fa3d155d8f649a31f860470785ddb7d71b6634063d80ec3b1458",
            "System/Docs/KIRA_R18_MEDICAL_EXTERNAL_ANATOMY_AND_BATHROOM_READINESS_BOUNDARY_20260801.md": "21b71a8ecd869d0ac26ec40cc0a63371c4c99490d115676b50a2b3bda811fb41",
            "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/KIRA_R18_EXACT_CORRECTION_MASKS_20260801.md": "563ec2cf6cbed0eaff34e4d59c3c494639c168c945aa2bfdf2c5cd1a084fd527",
            "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/KIRA_R17_FULL_PACKAGE_REVERIFICATION_20260801.md": "f087d3c3512598754b3ae57a6c13c2a38419befeb6374be0b8f8022da8d615e1",
        }
        for relative, expected_hash in expected.items():
            with self.subTest(relative=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file())
                self.assertEqual(file_sha256(path), expected_hash)

    def test_proposal_is_exact_and_static_only(self) -> None:
        self.assertEqual(
            file_sha256(PROPOSAL),
            "64df882c44c23eb58f81bbcc94311269ac80f1444b27e144ec74e6c3cc18c3e7",
        )
        text = PROPOSAL.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn("status: `static_boundary_only_not_runtime_attempt`", lower)
        self.assertIn("d4 \\ d2", lower)
        self.assertIn("source triangle index plus normalized", lower)
        self.assertIn("fails closed", lower)
        self.assertIn("not body-repair proof", lower)
        self.assertNotIn("attempt_48", lower)
        self.assertNotIn("blender.exe", lower)
        self.assertNotIn("bpy.", lower)
        self.assertNotIn("open_mainfile", lower)

    def test_source_component_and_global_interface_are_exact(self) -> None:
        topology = json.loads(TOPOLOGY_DIAGNOSTIC.read_text(encoding="utf-8"))
        source = topology["attempt02"]
        self.assertEqual(source["object_name"], "Object_23")
        self.assertEqual(source["mesh_name"], "Ariel_Mesh_Genitalia_0")
        self.assertEqual(
            (source["vertex_count"], source["edge_count"], source["face_count"]),
            (736, 2171, 1436),
        )
        self.assertEqual(len(source["boundary_cycle_vertex_indices"]), 34)
        self.assertEqual(topology["attempt02_to_r24_interface"]["maximum_nearest_distance_m"], 0.0)
        self.assertTrue(topology["attempt02_to_r24_interface"]["bijection"])

        identity = json.loads(SOURCE_IDENTITY.read_text(encoding="utf-8"))
        evidence = identity["source_identity_contract_evidence"]
        self.assertTrue(evidence["all_identity_and_sanity_checks_pass"])
        self.assertEqual(
            evidence["composite_topology_record_sha256"],
            "fcd30613876f514aeac1a0b2f71c8ceaddceeb701a78695a04a3eaa54ac7639a",
        )
        self.assertEqual(identity["global_seam"]["vertex_count"], 34)
        self.assertEqual(identity["global_seam"]["edge_count"], 34)
        self.assertFalse(identity["global_seam"]["coordinates_mutated"])
        self.assertEqual(
            identity["global_seam"]["world_coordinates_sha256"],
            "5a8aece38276bfff3caad1e8e993f30cc16e8972fc98d8795461b9b94e54d497",
        )

    def test_d2_core_and_fixed_boundary_infeasibility_are_exact(self) -> None:
        identity = json.loads(SOURCE_IDENTITY.read_text(encoding="utf-8"))
        current = identity["current_domain"]
        self.assertEqual(current["face_count"], 88)
        self.assertEqual(current["vertex_count"], 61)
        self.assertEqual(current["edge_count"], 148)
        self.assertEqual(current["boundary_edge_count"], 32)
        self.assertEqual(
            current["face_indices_sha256"],
            "aeb5ea5249c5e8883e5372e04b8844f6b4d449ccd36e72af8c0a213ec79d1426",
        )
        self.assertEqual(
            current["vertex_indices_sha256"],
            "276358504d91cf2d0f16eda7180e181eada12ae8cb441e32904982f25e5127a2",
        )
        self.assertEqual(
            current["boundary_edge_indices_sha256"],
            "238138b6e51d5afe916d94e19c2b8b940f7a27d48620f966198ccf98ce79d45b",
        )
        self.assertEqual(
            current["boundary_cycle_mesh_vertex_indices_sha256"],
            "a5ee656fc9d0db3489c06931b0c60a16eefd676038412fe9c1cbb886dc0c9e90",
        )
        self.assertAlmostEqual(
            current["boundary_angle_analysis"]["minimum_boundary_interior_angle_degrees"],
            8.546625076881082,
            places=12,
        )
        proof = identity["fixed_pslg_proof"]
        self.assertFalse(proof["another_interior_seed_can_repair_fixed_boundary"])
        self.assertEqual(proof["required_minimum_angle_degrees"], 12.0)
        self.assertTrue(identity["truth"]["fixed_32_edge_boundary_globally_infeasible_at_12_degrees"])

    def test_d2_d3_d4_and_exact_collar_hashes(self) -> None:
        report = json.loads(REPAIR_DOMAIN.read_text(encoding="utf-8"))
        domains = {domain["face_ring_expansion"]: domain for domain in report["domains"]}
        expected = {
            2: {
                "face_count": 88,
                "face_hash": "aeb5ea5249c5e8883e5372e04b8844f6b4d449ccd36e72af8c0a213ec79d1426",
                "vertex_count": 61,
                "vertex_hash": "276358504d91cf2d0f16eda7180e181eada12ae8cb441e32904982f25e5127a2",
                "boundary_count": 32,
                "boundary_hash": "238138b6e51d5afe916d94e19c2b8b940f7a27d48620f966198ccf98ce79d45b",
                "cycle_hash": "a5ee656fc9d0db3489c06931b0c60a16eefd676038412fe9c1cbb886dc0c9e90",
                "minimum_rings": 5,
            },
            3: {
                "face_count": 117,
                "face_hash": "d12d26c986576ce562c7fff3c2473fa8408eb5dbe7106bdbda0f5c8a9c206020",
                "vertex_count": 84,
                "vertex_hash": "d0bc1376a29e20ad103cd402af5993bcb0d7d8ffdd9cb937ee193eac968f5215",
                "boundary_count": 49,
                "boundary_hash": "5534b8bea75fca2273f41866736a59ca116644b21a36363ccb0bf68a5c551e1b",
                "cycle_hash": "d48c2a531d4d24a49ca5f8dc2c14ab8ed75a7fccb6e9abf1126e25faf26331ed",
                "minimum_rings": 4,
            },
            4: {
                "face_count": 152,
                "face_hash": "3fe5b3c84b731478cdfb8cec667f0cfc66651b086a4d5921a5c54f669d4f43b7",
                "vertex_count": 98,
                "vertex_hash": "7985685e5328ca0612a6f3f64160d6e48679dcbf6488cbb4a79416141bbed4ce",
                "boundary_count": 42,
                "boundary_hash": "ddc197b0b762b849170963bab5dcd5a5c0fe930323ce14f09fcbf2a42aa7349f",
                "cycle_hash": "7f44acf7bab996799e0ac750c76b21d9e0e06d9dc3b9795b20894e72d8e74881",
                "minimum_rings": 4,
            },
        }
        for ring, values in expected.items():
            domain = domains[ring]
            with self.subTest(ring=ring):
                self.assertEqual(len(domain["face_indices"]), values["face_count"])
                self.assertEqual(compact_json_sha256(domain["face_indices"]), values["face_hash"])
                self.assertEqual(len(domain["vertex_indices"]), values["vertex_count"])
                self.assertEqual(compact_json_sha256(domain["vertex_indices"]), values["vertex_hash"])
                self.assertEqual(len(domain["boundary_edges"]), values["boundary_count"])
                self.assertEqual(compact_json_sha256(domain["boundary_edges"]), values["boundary_hash"])
                self.assertEqual(
                    compact_json_sha256(domain["boundary_cycle_vertex_indices"][0]),
                    values["cycle_hash"],
                )
                self.assertEqual(
                    domain["minimum_vertex_ring_distance_from_global_seam"],
                    values["minimum_rings"],
                )
                self.assertFalse(domain["touches_global_34_vertex_seam"])

        d2_faces = set(domains[2]["face_indices"])
        d4_faces = set(domains[4]["face_indices"])
        d2_vertices = set(domains[2]["vertex_indices"])
        d4_vertices = set(domains[4]["vertex_indices"])
        self.assertTrue(d2_faces < d4_faces)
        self.assertTrue(d2_vertices < d4_vertices)
        collar_faces = sorted(d4_faces - d2_faces)
        collar_vertices = sorted(d4_vertices - d2_vertices)
        self.assertEqual(len(collar_faces), 64)
        self.assertEqual(
            compact_json_sha256(collar_faces),
            "0fab4f296d7b234044e0651a8c10a08cabf7c784510c0a720085e2e21c1dd25b",
        )
        self.assertEqual(len(collar_vertices), 37)
        self.assertEqual(
            compact_json_sha256(collar_vertices),
            "f35742843a93a7a0fbfee7cdcea94236438cf1f2889fd265349cfb631d19987b",
        )
        self.assertTrue(set(report["exact_collision"]["seed_face_indices"]) <= d2_faces)

    def test_attempt46_rejection_and_attempt47_terminal_rule_are_bound(self) -> None:
        attempt46 = json.loads(ATTEMPT46.read_text(encoding="utf-8"))
        candidate = attempt46["targeted_complete_vertex_star_candidates"][0]
        self.assertFalse(candidate["simple_projected_boundary"])
        self.assertAlmostEqual(
            candidate["boundary_angle_analysis"]["minimum_boundary_interior_angle_degrees"],
            10.810841145214567,
            places=12,
        )
        self.assertAlmostEqual(
            candidate["chart"]["maximum_absolute_boundary_deviation_m"],
            0.0022750297794118524,
            places=15,
        )
        self.assertEqual(candidate["forced_ear_feasibility"]["obstruction_count"], 1)
        self.assertEqual(attempt46["necessary_eligible_candidate_count"], 0)
        self.assertFalse(attempt46["truth"]["executable_body_repair_justified"])

        checkpoint = ATTEMPT47_CHECKPOINT.read_text(encoding="utf-8")
        self.assertIn("Attempt 47 is closed and must never be retried", checkpoint)
        self.assertIn("Do not create Attempt 48", checkpoint)
        self.assertIn("bounded local-transition", checkpoint)
        self.assertIn("No source Blend was opened", checkpoint)

    def test_protected_r17_and_r18_package_anchors_remain_exact(self) -> None:
        expected = {
            "Avatar/private_owner_review/kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816/kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816.blend": "7f7a6519ee5902fb01b247add864a4f41f4be6e600ab917cc5195ca9ea21e493",
            "Avatar/private_owner_review/kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816/BUILD_EVIDENCE.json": "5a2965bb77b50aa5217e5eedda66d58bfaa5b54f4faa74a1808bbab6a94b8188",
            "Avatar/private_owner_review/kira_profiled_adult_candidate_r18_bald_targeted_20260802_051548/kira_profiled_adult_candidate_r18_bald_targeted_20260802_051548.blend": "97f39c44ec1bc9efac0b5b794e47122e505dd83bbd518bf2f73fd614160091ea",
            "Avatar/private_owner_review/kira_profiled_adult_candidate_r18_bald_targeted_20260802_051548/BUILD_EVIDENCE.json": "93151a3cbab4b325a47c0b587ba9582809fa716345536bf076674a163bf98a95",
            "Avatar/private_owner_review/kira_profiled_adult_candidate_r18_bald_targeted_20260802_051548/PACKAGE_MANIFEST.json": "fe5a0a7a1afd79042b8e5d871f62a5819879319df47ae31a4134de5cfc6682c2",
        }
        for relative, expected_hash in expected.items():
            with self.subTest(relative=relative):
                self.assertEqual(file_sha256(ROOT / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
