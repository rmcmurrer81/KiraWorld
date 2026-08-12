from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

from Core import kira_r20_curvilinear_pelvic_patch as r20


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r20_pelvis_only.py"
CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
PREFLIGHT_ATTEMPT_01_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_01/PREFLIGHT_FAILURE.json"
)
PREFLIGHT_ATTEMPT_02_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_02/PREFLIGHT_FAILURE.json"
)
PREFLIGHT_ATTEMPT_03_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_03/PREFLIGHT_FAILURE.json"
)
FREEZE_IDENTITY_CORRECTION = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/"
    "FREEZE_IDENTITY_DIAGNOSIS_ATTEMPT_02_TO_03.json"
)
INTERFACE_ATTRIBUTE_CORRECTION = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/"
    "INTERFACE_AND_ATTRIBUTE_DIAGNOSIS_ATTEMPT_03_TO_04.json"
)
PREFLIGHT_RECONCILIATION_EVIDENCE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_preflight_contract_reconciliation/diagnostic_attempt_01/"
    "DIAGNOSTIC_EVIDENCE.json"
)
PREFLIGHT_RECONCILIATION_CHECKPOINT = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_preflight_contract_reconciliation/diagnostic_attempt_01/CHECKPOINT.md"
)
PREFLIGHT_RECONCILIATION_MANIFEST = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_preflight_contract_reconciliation/diagnostic_attempt_01/"
    "PACKAGE_MANIFEST.json"
)
PASSED_PREFLIGHT_ATTEMPT_04_MANIFEST = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_04/PACKAGE_MANIFEST.json"
)
PASSED_PREFLIGHT_ATTEMPT_04_EVIDENCE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_04/PREFLIGHT_EVIDENCE.json"
)
PASSED_PREFLIGHT_ATTEMPT_04_CHECKPOINT = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_04/CHECKPOINT.md"
)
AUTHOR_ATTEMPT_01_SUMMARY = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_01/AUTHORING_SUMMARY.json"
)
AUTHOR_ATTEMPT_01_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_01/AUTHOR_FAILURE.json"
)
AUTHOR_ATTEMPT_01_CANDIDATE_A_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_01/r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_01_CANDIDATE_B_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_01/r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_01_DIAGNOSIS = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/"
    "AUTHOR_ATTEMPT_01_BASELINE_GATE_DIAGNOSIS_ATTEMPT_02.json"
)
AUTHOR_ATTEMPT_02_SUMMARY = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_02/AUTHORING_SUMMARY.json"
)
AUTHOR_ATTEMPT_02_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_02/AUTHOR_FAILURE.json"
)
AUTHOR_ATTEMPT_02_CANDIDATE_A_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_02/r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_02_CANDIDATE_B_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_02/r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_02_DIAGNOSIS = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/"
    "AUTHOR_ATTEMPT_02_NATIVE_KNEE_DIAGNOSIS_ATTEMPT_03.json"
)
AUTHOR_ATTEMPT_03_SUMMARY = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_03/AUTHORING_SUMMARY.json"
)
AUTHOR_ATTEMPT_03_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_03/AUTHOR_FAILURE.json"
)
AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_03/r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_03/r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json"
)
AUTHOR_ATTEMPT_03_COORDINATE_DIAGNOSIS = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/"
    "AUTHOR_ATTEMPT_03_COORDINATE_SPACE_DIAGNOSIS_ATTEMPT_04.json"
)
R19_BUILD_EVIDENCE = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r19_bald_targeted_correction/attempt_06/BUILD_EVIDENCE.json"
)
AUTHOR_ATTEMPT_02_COMMAND = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_02_COMMAND.md"
)
AUTHOR_ATTEMPT_03_COMMAND = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_03_COMMAND.md"
)
AUTHOR_ATTEMPT_04_COMMAND = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_04_COMMAND.md"
)
DEFERRED_COMMAND = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/DEFERRED_BLENDER_COMMAND.md"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_fixture(*, uneven: bool) -> tuple[list[tuple[float, float, float]], ...]:
    seam = []
    exterior_1 = []
    exterior_2 = []
    normals = []
    count = r20.SEAM_COUNT
    raw_angles = []
    for index in range(count):
        fraction = index / count
        if uneven:
            fraction += 0.014 * math.sin(2.0 * math.pi * fraction) + 0.007 * math.sin(
                6.0 * math.pi * fraction
            )
        raw_angles.append(2.0 * math.pi * fraction)
    for angle in raw_angles:
        radial_x = 0.051 * math.cos(angle)
        radial_z = 0.073 * math.sin(angle)
        surface_y = -0.010 + 0.0022 * math.cos(2.0 * angle)
        seam.append((radial_x, surface_y, 0.87 + radial_z))
        exterior_1.append((1.07 * radial_x, surface_y + 0.001, 0.87 + 1.07 * radial_z))
        exterior_2.append((1.14 * radial_x, surface_y + 0.002, 0.87 + 1.14 * radial_z))
        normals.append((0.0, -1.0, 0.0))
    canonical_seam, order = r20.canonicalize_cycle(seam)
    return (
        list(canonical_seam),
        [exterior_1[index] for index in order],
        [exterior_2[index] for index in order],
        [normals[index] for index in order],
    )


def call_chain(node: ast.AST) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


class R20PureTopologyTests(unittest.TestCase):
    def test_exact_golden_topology(self) -> None:
        record = r20.topology_contract()
        self.assertEqual(record["vertices_including_reused_seam"], 774)
        self.assertEqual(record["new_vertices"], 740)
        self.assertEqual(record["faces"], 756)
        self.assertEqual(record["quads"], 756)
        self.assertEqual(record["edges"], 1529)
        self.assertEqual(record["boundary_edges"], 34)
        self.assertTrue(record["boundary_is_exact_seam"])
        self.assertEqual(record["nonmanifold_edges"], 0)
        self.assertEqual(record["connected_components"], 1)
        self.assertLessEqual(record["maximum_vertex_valence"], 6)
        self.assertEqual(record["euler_disk_value"], 1)
        self.assertEqual(
            record["connectivity_sha256"],
            "761981c7b14b769fb1d750deef946ab95019821c2280383d7e1c5cf15c47b749",
        )

    def test_canonical_cycle_rotation_and_reversal_invariant(self) -> None:
        values = [
            (
                0.05 * math.cos(2.0 * math.pi * index / r20.SEAM_COUNT),
                0.04 * math.sin(2.0 * math.pi * index / r20.SEAM_COUNT),
                0.9 + 0.02 * math.sin(4.0 * math.pi * index / r20.SEAM_COUNT),
            )
            for index in range(r20.SEAM_COUNT)
        ]
        expected, _ = r20.canonicalize_cycle(values)
        for offset in (1, 7, 19, 33):
            rotated = values[offset:] + values[:offset]
            actual, _ = r20.canonicalize_cycle(rotated)
            self.assertEqual(actual, expected)
            reversed_actual, _ = r20.canonicalize_cycle(list(reversed(rotated)))
            self.assertEqual(reversed_actual, expected)

    def test_canonical_cycle_ambiguous_direction_fails(self) -> None:
        values = [(float(index), float(index + 1), float(index * index)) for index in range(34)]
        values[0] = (0.0, -100.0, 0.0)
        values[1] = (1.0, 2.0, 5.0)
        values[-1] = (1.0, 3.0, 5.0)
        with self.assertRaisesRegex(ValueError, "direction rule is ambiguous"):
            r20.canonicalize_cycle(values)

    def test_explicit_34_to_102_transition_faces(self) -> None:
        faces = r20.build_quad_topology()
        transition = faces[68:136]
        perimeter = r20.core_perimeter_indices()
        for index in range(r20.SEAM_COUNT):
            start = index * 3
            self.assertEqual(
                transition[index * 2],
                (
                    r20.COLLAR_2_OFFSET + index,
                    perimeter[start],
                    perimeter[start + 1],
                    perimeter[start + 2],
                ),
            )
            self.assertEqual(
                transition[index * 2 + 1],
                (
                    r20.COLLAR_2_OFFSET + index,
                    perimeter[start + 2],
                    perimeter[(start + 3) % r20.CORE_PERIMETER_COUNT],
                    r20.COLLAR_2_OFFSET + (index + 1) % r20.SEAM_COUNT,
                ),
            )

    def test_fake_mask_selector_success_and_failure(self) -> None:
        faces = []
        columns = 5
        for row in range(4):
            for column in range(4):
                top_left = row * columns + column
                faces.append(
                    (
                        top_left,
                        top_left + 1,
                        top_left + columns + 1,
                        top_left + columns,
                    )
                )
        selected = {5, 6, 9, 10}
        record = r20.mask_topology_contract(faces, selected)
        self.assertEqual(record["selected_face_count"], 4)
        self.assertEqual(record["selected_face_connected_components"], 1)
        self.assertEqual(record["incident_vertex_count"], 9)
        self.assertEqual(record["interface_edge_count"], 8)
        self.assertEqual(record["interface_vertex_count"], 8)
        self.assertTrue(record["interface_degree_two"])
        self.assertEqual(record["interface_connected_components"], 1)
        self.assertEqual(record["removable_interior_vertex_count"], 1)
        disconnected = r20.mask_topology_contract(faces, {0, 15})
        self.assertEqual(disconnected["selected_face_connected_components"], 2)
        with self.assertRaises(ValueError):
            r20.mask_topology_contract(faces, {999})


class R20PureFieldTests(unittest.TestCase):
    def test_both_candidates_pass_smooth_and_uneven_quality(self) -> None:
        for uneven in (False, True):
            seam, first, second, normals = geometry_fixture(uneven=uneven)
            for candidate in r20.CANDIDATES:
                positions, evidence = r20.build_positions(
                    seam, first, second, normals, candidate
                )
                self.assertEqual(tuple(positions[:34]), tuple(seam))
                self.assertEqual(len(positions), 774)
                self.assertLessEqual(evidence["maximum_absolute_feature_offset_m"], 0.005)
                quality = r20.geometry_quality(positions)
                self.assertEqual(quality["face_count"], 756)
                self.assertEqual(quality["degenerate_face_count_at_1e_10_m2"], 0)
                self.assertGreater(quality["minimum_face_area_m2"], 1.0e-10)
                self.assertLessEqual(quality["maximum_quad_edge_ratio"], 3.0)

    def test_harmonic_uv_and_self_crossing_rejection(self) -> None:
        values = [
            (
                0.5 + 0.35 * math.cos(2.0 * math.pi * index / 34),
                0.5 + 0.42 * math.sin(2.0 * math.pi * index / 34),
            )
            for index in range(34)
        ]
        solved, evidence = r20.harmonic_uv(values)
        self.assertEqual(tuple(solved[:34]), tuple(values))
        self.assertEqual(len(solved), 774)
        self.assertTrue(evidence["exact_seam_values_retained"])
        crossed = list(values)
        crossed[1], crossed[18] = crossed[18], crossed[1]
        with self.assertRaisesRegex(ValueError, "self-crosses"):
            r20.harmonic_uv(crossed)

    def test_harmonic_weights_constant_and_deterministic_top_four(self) -> None:
        constant = [{"pelvis": 0.6, "spine": 0.4} for _ in range(34)]
        solved = r20.harmonic_weights(constant)
        self.assertEqual(solved.records[:34], tuple(constant))
        for record in solved.records[34:]:
            self.assertAlmostEqual(record["pelvis"], 0.6, places=8)
            self.assertAlmostEqual(record["spine"], 0.4, places=8)
            self.assertAlmostEqual(sum(record.values()), 1.0, places=8)
        varied = []
        for index in range(34):
            varied.append(
                {
                    "a": 0.30 + 0.001 * index,
                    "b": 0.25,
                    "c": 0.20,
                    "d": 0.15,
                    "e": 0.10 - 0.001 * index,
                }
            )
        first = r20.harmonic_weights(varied)
        second = r20.harmonic_weights(varied)
        self.assertEqual(first.records, second.records)
        self.assertLessEqual(first.maximum_positive_influences_after_projection, 4)
        self.assertTrue(all(len(record) <= 4 for record in first.records[34:]))

    def test_named_external_landmark_sets(self) -> None:
        groups = r20.landmark_vertex_sets()
        expected_counts = {
            "mons": 117,
            "labia_majora_left": 72,
            "labia_majora_right": 72,
            "labia_minora_left": 32,
            "labia_minora_right": 32,
            "clitoral_hood_and_restrained_glans": 12,
            "vestibule": 42,
            "external_urethral_meatus_rim": 16,
            "external_urethral_meatus_blind_cap": 9,
            "vaginal_opening_introitus_rim": 26,
            "vaginal_opening_introitus_blind_cap": 30,
            "posterior_fourchette": 6,
            "continuous_perineum": 20,
            "separate_anal_region_rim": 16,
            "separate_anal_region_blind_cap": 9,
        }
        self.assertEqual({name: len(values) for name, values in groups.items()}, expected_counts)
        self.assertEqual(
            r20.EXTERNAL_LANDMARK_ORDER,
            (
                "clitoral_hood_and_restrained_glans",
                "external_urethral_meatus",
                "vaginal_opening_introitus",
                "posterior_fourchette",
                "continuous_perineum",
                "separate_anal_region",
            ),
        )
        self.assertTrue(all(0 <= index < 774 for values in groups.values() for index in values))


class R20PureCoordinateSpaceTests(unittest.TestCase):
    def test_exact_r19_seam_meter_scale_roundtrip_and_identity(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        contract = config["attempt_04_coordinate_space_contract"]
        preflight = json.loads(PASSED_PREFLIGHT_ATTEMPT_04_EVIDENCE.read_text(encoding="utf-8"))
        source = json.loads(R19_BUILD_EVIDENCE.read_text(encoding="utf-8"))
        matrix = source["immutable_component_verification"]["immutable_mesh_states"][
            "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
        ]["matrix_world"]
        self.assertEqual(matrix, contract["body_matrix_world"])
        local = preflight["mask"]["canonical_seam_local_coordinates"]
        serialized_world = preflight["mask"]["canonical_seam_world_coordinates"]
        inverse, _normal, evidence = r20.positive_affine_transform_matrices(matrix)
        self.assertAlmostEqual(
            r20.closed_cycle_median_edge_scale(serialized_world),
            contract["preflight_serialized_world_median_edge_scale_m"],
            delta=1.0e-15,
        )
        self.assertAlmostEqual(
            r20.closed_cycle_median_edge_scale(local),
            contract["preflight_serialized_local_median_edge_scale"],
            delta=1.0e-15,
        )
        self.assertLess(
            r20.affine_roundtrip_maximum_delta(local, matrix, inverse),
            contract["maximum_seam_local_roundtrip_delta_local_units"],
        )
        generated_world = ((0.0, 0.0, 0.85), (0.01, -0.02, 0.88))
        generated_local = r20.transform_affine_points(inverse, generated_world)
        local_write = tuple(tuple(point) for point in local) + generated_local
        self.assertEqual(local_write[: r20.SEAM_COUNT], tuple(tuple(point) for point in local))
        self.assertEqual(len(local_write) - r20.SEAM_COUNT, 2)
        self.assertTrue(evidence["orientation_preserving"])

    def test_inverse_transpose_normal_math_supports_nonuniform_shear(self) -> None:
        matrix = (
            (2.0, 0.25, 0.0, 1.0),
            (0.0, 3.0, 0.2, -2.0),
            (0.0, 0.0, 4.0, 0.5),
            (0.0, 0.0, 0.0, 1.0),
        )
        _inverse, normal_matrix, evidence = r20.positive_affine_transform_matrices(matrix)
        transformed_normal = r20.transform_normals(normal_matrix, ((0.0, 0.0, 1.0),))[0]
        tangent_x = (matrix[0][0], matrix[1][0], matrix[2][0])
        tangent_y = (matrix[0][1], matrix[1][1], matrix[2][1])
        self.assertAlmostEqual(sum(a * b for a, b in zip(transformed_normal, tangent_x)), 0.0, delta=1e-12)
        self.assertAlmostEqual(sum(a * b for a, b in zip(transformed_normal, tangent_y)), 0.0, delta=1e-12)
        self.assertTrue(evidence["nonuniform_scale_and_shear_supported"])
        self.assertFalse(
            json.loads(CONFIG.read_text(encoding="utf-8"))["attempt_04_coordinate_space_contract"][
                "arbitrary_nonuniform_scale_or_shear_supported"
            ]
        )

    def test_unsafe_affine_transforms_fail_closed(self) -> None:
        matrices = (
            ((-1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
            ((0.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)),
            ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.01, 0.0, 0.0, 1.0)),
        )
        for matrix in matrices:
            with self.assertRaises(ValueError):
                r20.positive_affine_transform_matrices(matrix)


class R20WorkerStaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.calls = [node for node in ast.walk(cls.tree) if isinstance(node, ast.Call)]

    def test_worker_parses_and_binds_exact_inputs(self) -> None:
        self.assertIn(sha256_file(CONFIG), self.source)
        self.assertIn(r20.SOURCE_BLEND_SHA256, self.source)
        self.assertIn(r20.SOURCE_PACKAGE_MANIFEST_SHA256, self.source)
        self.assertIn(r20.PLAN_SHA256, self.source)
        self.assertIn(r20.FREEZE_LEDGER_SHA256, self.source)
        self.assertIn(r20.SOURCE_LEDGER_SHA256, self.source)
        self.assertIn(sha256_file(FREEZE_IDENTITY_CORRECTION), self.source)
        self.assertIn(sha256_file(PROJECT_ROOT / "Core/kira_r20_curvilinear_pelvic_patch.py"), self.source)
        self.assertIn("exact_file_set_matches", self.source)
        self.assertIn("EXPECTED_SOURCE_MANIFEST_ENTRIES = 49", self.source)

    def test_exactly_one_guarded_save_call_site(self) -> None:
        save_calls = [
            node
            for node in self.calls
            if call_chain(node.func) == "bpy.ops.wm.save_as_mainfile"
        ]
        self.assertEqual(len(save_calls), 1)
        functions = {
            node.name: node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("_save_candidate_once", functions)
        self.assertTrue(any(call is save_calls[0] for call in ast.walk(functions["_save_candidate_once"])))
        self.assertIn("refusing to overwrite candidate Blend", self.source)
        self.assertIn("append-only authoring output already exists", self.source)

    def test_no_prohibited_global_or_export_operations(self) -> None:
        prohibited = {
            "bpy.ops.object.join",
            "bmesh.ops.remove_doubles",
            "bpy.ops.mesh.remove_doubles",
            "bpy.ops.mesh.normals_make_consistent",
            "bpy.ops.export_scene.gltf",
            "bpy.ops.export_mesh.stl",
            "bpy.ops.wm.alembic_export",
            "mesh.normals_split_custom_set",
        }
        actual = {call_chain(node.func) for node in self.calls}
        self.assertTrue(prohibited.isdisjoint(actual), prohibited.intersection(actual))
        self.assertNotIn("keyframe_insert", actual)
        self.assertNotIn("bpy.ops.object.modifier_apply", actual)
        self.assertNotIn("normals_split_custom_set", actual)

    def test_modes_and_private_state_are_explicit(self) -> None:
        for value in ("preflight", "author", "verify-render"):
            self.assertIn(value, self.source)
        for marker in (
            "r20_private_owner_review_only",
            "r20_inactive",
            "r20_unassigned",
            "r20_unpublished",
            "r20_runtime_eligible",
            "r20_owner_approved",
            "r20_scalp_hair_dependency",
        ):
            self.assertIn(marker, self.source)
        self.assertIn("separate_anatomy_objects_created", self.source)
        self.assertIn("internal_function_claimed", self.source)

    def test_toilet_and_visual_rejection_evidence_is_required(self) -> None:
        for marker in (
            "toilet_seat_contact_and_clearance",
            "minimum_signed_patch_to_rim_gap_m",
            "no_patch_to_seat_penetration",
            "broad inverted trapezoid or triangular panel",
            "straight superior edge",
            "central dark cavity or crease",
            "urethral meatus",
            "fourchette",
            "separate anal region",
        ):
            self.assertIn(marker, self.source)

    def test_config_and_explicit_protected_hashes(self) -> None:
        self.assertEqual(
            sha256_file(CONFIG),
            "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc",
        )
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(config["candidates"]), 2)
        self.assertTrue(all(config[name] is True for name in ("private", "inactive", "unassigned", "unpublished")))
        self.assertTrue(
            all(
                config[name] is False
                for name in (
                    "runtime_eligible",
                    "owner_approved",
                    "scalp_hair_loaded",
                    "body_activation_allowed",
                    "clothing_allowed",
                    "export_allowed",
                    "publication_allowed",
                )
            )
        )
        for path_key, hash_key in (
            ("source_blend", "source_blend_sha256"),
            ("source_package_manifest", "source_package_manifest_sha256"),
            ("r20_plan", "r20_plan_sha256"),
            ("r20_freeze_ledger", "r20_freeze_ledger_sha256"),
            ("r20_source_ledger", "r20_source_ledger_sha256"),
            ("interface_evidence", "interface_evidence_sha256"),
            ("freeze_identity_correction", "freeze_identity_correction_sha256"),
            ("prior_failed_preflight_attempt_03", "prior_failed_preflight_attempt_03_sha256"),
            ("interface_attribute_correction", "interface_attribute_correction_sha256"),
            ("preflight_reconciliation_evidence", "preflight_reconciliation_evidence_sha256"),
            ("preflight_reconciliation_checkpoint", "preflight_reconciliation_checkpoint_sha256"),
            ("preflight_reconciliation_manifest", "preflight_reconciliation_manifest_sha256"),
            ("passed_preflight_attempt_04_manifest", "passed_preflight_attempt_04_manifest_sha256"),
            ("passed_preflight_attempt_04_evidence", "passed_preflight_attempt_04_evidence_sha256"),
            ("passed_preflight_attempt_04_checkpoint", "passed_preflight_attempt_04_checkpoint_sha256"),
            ("author_attempt_01_summary", "author_attempt_01_summary_sha256"),
            ("author_attempt_01_failure", "author_attempt_01_failure_sha256"),
            ("author_attempt_01_candidate_a_failure", "author_attempt_01_candidate_a_failure_sha256"),
            ("author_attempt_01_candidate_b_failure", "author_attempt_01_candidate_b_failure_sha256"),
            ("author_attempt_01_diagnosis", "author_attempt_01_diagnosis_sha256"),
            ("author_attempt_02_summary", "author_attempt_02_summary_sha256"),
            ("author_attempt_02_failure", "author_attempt_02_failure_sha256"),
            ("author_attempt_02_candidate_a_failure", "author_attempt_02_candidate_a_failure_sha256"),
            ("author_attempt_02_candidate_b_failure", "author_attempt_02_candidate_b_failure_sha256"),
            ("author_attempt_02_diagnosis", "author_attempt_02_diagnosis_sha256"),
            ("author_attempt_03_summary", "author_attempt_03_summary_sha256"),
            ("author_attempt_03_failure", "author_attempt_03_failure_sha256"),
            ("author_attempt_03_candidate_a_failure", "author_attempt_03_candidate_a_failure_sha256"),
            ("author_attempt_03_candidate_b_failure", "author_attempt_03_candidate_b_failure_sha256"),
            ("author_attempt_03_coordinate_diagnosis", "author_attempt_03_coordinate_diagnosis_sha256"),
        ):
            self.assertEqual(
                sha256_file(PROJECT_ROOT / config[path_key]),
                config[hash_key],
                path_key,
            )

    def test_attempt03_preserves_slot_repair_and_binds_append_only_output(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        expected_slots = [
            "R19_WarmTexture_Torso_Attempt06_BoundedSurfaceResponse",
            "R19_WarmTexture_Arms_Attempt06_BoundedSurfaceResponse",
            "R19_WarmTexture_Legs_Attempt06_BoundedSurfaceResponse",
            "R19_WarmTexture_Face_Attempt06_BoundedSurfaceResponse",
            "R19_WarmTexture_Ears_Attempt06_BoundedSurfaceResponse",
            "R19_WarmTexture_Genitalia_Attempt06_BoundedSurfaceResponse",
        ]
        self.assertEqual(config["expected_r19_material_slots"], expected_slots)
        self.assertEqual(config["patch_material_slot"], 5)
        self.assertEqual(config["patch_material"], expected_slots[5])
        self.assertEqual(expected_slots[1], "R19_WarmTexture_Arms_Attempt06_BoundedSurfaceResponse")
        self.assertTrue(config["preflight_output"].endswith("/preflight_attempt_04"))
        self.assertEqual(
            config["prior_failed_preflight_sha256"],
            "c7b537780d4871679a298ccc47e0acab9b0e9d190afd7d48d3ccae999e35e03a",
        )
        self.assertEqual(
            sha256_file(PREFLIGHT_ATTEMPT_01_FAILURE),
            config["prior_failed_preflight_sha256"],
        )
        failure = json.loads(PREFLIGHT_ATTEMPT_01_FAILURE.read_text(encoding="utf-8"))
        self.assertEqual(failure["status"], "FAILED_CLOSED")
        self.assertEqual(failure["error"], "R19 exact regional material binding drifted")
        self.assertIn("actual_material_slots", self.source)
        self.assertIn("expected_material_slots", self.source)
        self.assertIn("PATCH_MATERIAL_SLOT = 5", self.source)

    def test_attempt03_exact_freeze_identity_correction_and_whole_inventory(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            config["prior_failed_preflight_attempt_02_sha256"],
            "ccbfe304673c5527f5be3897b54fc39ba1be23895de32f40dd1e5034303370e2",
        )
        self.assertEqual(
            sha256_file(PREFLIGHT_ATTEMPT_02_FAILURE),
            config["prior_failed_preflight_attempt_02_sha256"],
        )
        failure = json.loads(PREFLIGHT_ATTEMPT_02_FAILURE.read_text(encoding="utf-8"))
        self.assertEqual(failure["status"], "FAILED_CLOSED")
        self.assertEqual(failure["error"], "frozen separate mesh object missing: Icosphere")
        self.assertEqual(
            sha256_file(FREEZE_IDENTITY_CORRECTION),
            config["freeze_identity_correction_sha256"],
        )
        correction = json.loads(FREEZE_IDENTITY_CORRECTION.read_text(encoding="utf-8"))
        self.assertEqual(
            correction["root_cause"]["classification"],
            "HISTORICAL_IN_MEMORY_UNLINKED_OBJECT_PROMOTED_TO_PERSISTED_FREEZE_RECORD",
        )
        self.assertFalse(
            correction["read_only_serialization_inspection"][
                "serialized_object_id_named_Icosphere_present"
            ]
        )
        self.assertEqual(
            correction["read_only_serialization_inspection"][
                "serialized_protected_component_count_including_primary"
            ],
            32,
        )
        self.assertEqual(
            len(correction["expected_protected_object_to_mesh_bindings"]), 32
        )
        self.assertEqual(
            len(correction["expected_review_context_object_to_mesh_bindings"]), 15
        )
        freeze_contract = config["freeze_identity_contract"]
        self.assertEqual(freeze_contract["persisted_separate_protected_component_count"], 31)
        self.assertEqual(freeze_contract["total_protected_component_count"], 32)
        self.assertTrue(freeze_contract["whole_exact_inventory_required"])
        self.assertFalse(freeze_contract["loose_object_matching_allowed"])
        for marker in (
            "whole exact source mesh inventory changed",
            "missing_objects",
            "extra_objects",
            "mesh_binding_mismatches",
            "actual_protected_bindings",
            "actual_review_context_bindings",
            "loose_object_matching_used",
        ):
            self.assertIn(marker, self.source)

    def test_attempt04_binds_failed_attempt_and_whole_reconciliation(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["schema_version"], 7)
        self.assertEqual(
            sha256_file(PREFLIGHT_ATTEMPT_03_FAILURE),
            "3afa5894348d862974e3829c3c4dad5fa0d1aed92bf7c7c503d058d75c0f50ab",
        )
        failure = json.loads(PREFLIGHT_ATTEMPT_03_FAILURE.read_text(encoding="utf-8"))
        self.assertEqual(failure["status"], "FAILED_CLOSED")
        self.assertIn("0.12830215951281168", failure["error"])
        self.assertEqual(
            sha256_file(INTERFACE_ATTRIBUTE_CORRECTION),
            config["interface_attribute_correction_sha256"],
        )
        self.assertEqual(
            sha256_file(PREFLIGHT_RECONCILIATION_EVIDENCE),
            config["preflight_reconciliation_evidence_sha256"],
        )
        self.assertEqual(
            sha256_file(PREFLIGHT_RECONCILIATION_CHECKPOINT),
            config["preflight_reconciliation_checkpoint_sha256"],
        )
        self.assertEqual(
            sha256_file(PREFLIGHT_RECONCILIATION_MANIFEST),
            config["preflight_reconciliation_manifest_sha256"],
        )
        self.assertIn("_bijective_coordinate_set_match", self.source)
        self.assertIn("licensed_record_order_used_as_adjacency", self.source)
        self.assertIn("adult_boundary_to_base_vertices", self.source)
        self.assertIn("historical_ordered_boundary_field_used_as_adjacency", self.source)

    def test_attempt04_exact_surviving_attributes_and_local_normal_gate(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        contract = config["attempt_04_interface_attribute_contract"]
        self.assertTrue(contract["surviving_nonpatch_attribute_elements_exact"])
        self.assertEqual(contract["new_patch_custom_normal_short2"], [0, 0])
        self.assertFalse(contract["whole_mesh_normal_setter_allowed"])
        self.assertFalse(contract["global_normal_recalculation_allowed"])
        for marker in (
            "PLANNED_SURVIVING_ATTRIBUTE_RULES",
            "all_surviving_custom_normal_short2_values_exact",
            "new_patch_uv_selection_values_all_false",
            "decoded custom normals drifted outside the seam fan",
            "minimum_seam_to_preserved_exterior_dot",
            "patch_custom_normal_all_zero_auto_sentinel",
            "sharp_edge_attribute_modified_by_normal_work",
            "localized_attribute_and_normal_gate",
            "ordinary_and_opposite_light_normal_heatmaps_required",
        ):
            self.assertIn(marker, self.source)
        self.assertIn("seam_normal_heatmap_light_a", self.source)
        self.assertIn("seam_normal_heatmap_light_b", self.source)
        calls = {call_chain(node.func) for node in self.calls}
        self.assertFalse(any(value.endswith("normals_split_custom_set") for value in calls))

    def test_attempt04_has_one_preflight_command_and_no_author_command(self) -> None:
        value = DEFERRED_COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("--mode preflight"), 1)
        self.assertNotIn("--mode author", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertIn("preflight_attempt_04", value)
        self.assertIn(
            "4d7aabfdaa1559fb4a23326d223da9cc38e3157a74580ae5c3a33be8a5463276",
            value,
        )

    def test_author_attempt01_failure_is_bound_and_attempt02_is_append_only(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(sha256_file(PASSED_PREFLIGHT_ATTEMPT_04_MANIFEST), config["passed_preflight_attempt_04_manifest_sha256"])
        self.assertEqual(sha256_file(PASSED_PREFLIGHT_ATTEMPT_04_EVIDENCE), config["passed_preflight_attempt_04_evidence_sha256"])
        self.assertEqual(sha256_file(PASSED_PREFLIGHT_ATTEMPT_04_CHECKPOINT), config["passed_preflight_attempt_04_checkpoint_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_01_SUMMARY), config["author_attempt_01_summary_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_01_FAILURE), config["author_attempt_01_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_01_CANDIDATE_A_FAILURE), config["author_attempt_01_candidate_a_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_01_CANDIDATE_B_FAILURE), config["author_attempt_01_candidate_b_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_01_DIAGNOSIS), config["author_attempt_01_diagnosis_sha256"])
        summary = json.loads(AUTHOR_ATTEMPT_01_SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["successful_candidate_count"], 0)
        self.assertTrue(summary["source_r19_unchanged"])
        for path in (AUTHOR_ATTEMPT_01_CANDIDATE_A_FAILURE, AUTHOR_ATTEMPT_01_CANDIDATE_B_FAILURE):
            failure = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(failure["error"], "evaluated R20 patch contains a non-quad")
            self.assertIn("baseline_pose_suite = run_pose_suite", failure["traceback"])

    def test_attempt02_baseline_skips_only_candidate_patch_gates(self) -> None:
        functions = {
            node.name: node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }
        suite = functions["run_pose_suite"]
        conditional = next(
            node
            for node in ast.walk(suite)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "candidate_patch_present"
        )
        body_calls = {
            call_chain(node.func)
            for statement in conditional.body
            for node in ast.walk(statement)
            if isinstance(node, ast.Call)
        }
        baseline_calls = {
            call_chain(node.func)
            for statement in conditional.orelse
            for node in ast.walk(statement)
            if isinstance(node, ast.Call)
        }
        self.assertIn("evaluated_patch_quality", body_calls)
        self.assertIn("evaluated_external_landmarks", body_calls)
        self.assertIn("exact_cross_intersections", body_calls)
        self.assertNotIn("evaluated_patch_quality", baseline_calls)
        self.assertNotIn("evaluated_external_landmarks", baseline_calls)
        self.assertIn("NOT_EVALUATED_SOURCE_R19_BASELINE_NO_R20_PATCH", self.source)

        author = functions["_author_candidate"]
        ordered_calls = [
            (node.lineno, call_chain(node.func))
            for node in ast.walk(author)
            if isinstance(node, ast.Call)
        ]
        first_baseline = min(line for line, name in ordered_calls if name == "run_pose_suite")
        prepare = min(line for line, name in ordered_calls if name == "_prepare_candidate_fields")
        apply_patch = min(line for line, name in ordered_calls if name == "_apply_local_patch")
        second_suite = max(line for line, name in ordered_calls if name == "run_pose_suite")
        self.assertLess(first_baseline, prepare)
        self.assertLess(prepare, apply_patch)
        self.assertLess(apply_patch, second_suite)

        quality = functions["evaluated_patch_quality"]
        quality_source = ast.get_source_segment(self.source, quality)
        self.assertIn("len(polygon.vertices) != 4", quality_source)
        self.assertIn("len(patch_faces) == 756", quality_source)
        self.assertIn("min(areas, default=0.0) > 1.0e-10", quality_source)
        self.assertIn("folded == 0", quality_source)

    def test_attempt02_has_one_exact_author_command(self) -> None:
        value = AUTHOR_ATTEMPT_02_COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("--mode author"), 1)
        self.assertNotIn("--mode preflight", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertNotIn("--candidate-id", value)
        self.assertIn("attempt_02", value)
        self.assertIn(
            "64cf8a7e03a345b41fd65e352831cb0831b786ef5e260c22b55bdc17f1d9c61e",
            value,
        )

    def test_author_attempt02_failure_remains_bound(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_02_SUMMARY), config["author_attempt_02_summary_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_02_FAILURE), config["author_attempt_02_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_02_CANDIDATE_A_FAILURE), config["author_attempt_02_candidate_a_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_02_CANDIDATE_B_FAILURE), config["author_attempt_02_candidate_b_failure_sha256"])
        self.assertEqual(sha256_file(AUTHOR_ATTEMPT_02_DIAGNOSIS), config["author_attempt_02_diagnosis_sha256"])
        summary = json.loads(AUTHOR_ATTEMPT_02_SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["successful_candidate_count"], 0)
        self.assertTrue(summary["source_r19_unchanged"])

    def test_attempt03_uses_exact_native_shins_and_x_axis(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        worker_source = WORKER.read_text(encoding="utf-8")
        config_source = CONFIG.read_text(encoding="utf-8")
        for old_name in ("lowerleg01.L", "lowerleg01.R"):
            self.assertNotIn(old_name, worker_source)
            self.assertNotIn(old_name, config_source)
        contract = config["attempt_03_native_knee_contract"]
        self.assertEqual(contract["left_shin_bone"], "lShin_07")
        self.assertEqual(contract["right_shin_bone"], "rShin_023")
        self.assertEqual(contract["manual_rotation_axis"], "X")
        self.assertEqual(contract["manual_knee_angles_degrees"], [30, 55, 80])
        self.assertIn("isolated bilateral shin-flexion stress diagnostics", contract["manual_knee_state_scope"])
        self.assertFalse(contract["manual_knee_states_reproduce_full_r19_actions"])
        self.assertEqual(contract["selected_seated_action"], "KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A")
        self.assertEqual(contract["selected_supine_action"], "KIRA_R19_ATTEMPT05_SUPINE_FACE_UP_A")
        self.assertEqual(contract["frozen_action_evaluation_frame"], 30)
        self.assertTrue(contract["natural_owner_views_use_frozen_r19_actions"])
        self.assertIn('"selected_supine_action": SELECTED_SUPINE_ACTION', worker_source)
        self.assertIn('"frozen_action_evaluation_frame": POSE_FRAME', worker_source)
        self.assertIn('"natural_owner_views_use_frozen_r19_actions": True', worker_source)
        self.assertIn('KNEE_BONES = {"left": "lShin_07", "right": "rShin_023"}', worker_source)
        self.assertIn('KNEE_ROTATION_AXIS = "X"', worker_source)
        self.assertIn("bone.rotation_euler.x = math.radians(float(degrees))", worker_source)
        self.assertNotIn("bone.rotation_euler.z", worker_source)

        evidence = json.loads(R19_BUILD_EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(sha256_file(R19_BUILD_EVIDENCE), contract["evidence_sha256"])
        seated = evidence["movement_candidates"]["supported_seated"]
        self.assertEqual(seated[0]["action"], "KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A")
        self.assertEqual(seated[0]["rotations_degrees_xyz"]["lShin_07"], [72.0, 0.0, 0.0])
        self.assertEqual(seated[0]["rotations_degrees_xyz"]["rShin_023"], [72.0, 0.0, 0.0])
        self.assertEqual(seated[1]["action"], "KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_B")
        self.assertEqual(seated[1]["rotations_degrees_xyz"]["lShin_07"], [78.0, 0.0, 0.0])
        self.assertEqual(seated[1]["rotations_degrees_xyz"]["rShin_023"], [78.0, 0.0, 0.0])

    def test_attempt03_historical_command_and_output_are_preserved(self) -> None:
        value = AUTHOR_ATTEMPT_03_COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("--mode author"), 1)
        self.assertNotIn("--mode preflight", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertNotIn("--candidate-id", value)
        self.assertIn("attempt_03", value)
        self.assertIn("cc5df55927f501b06d093a128d59e67f7dee6978f22cc468cc9009c20ce5e649", value)
        self.assertTrue(AUTHOR_ATTEMPT_03_SUMMARY.exists())

    def test_author_attempt03_failure_is_bound_and_attempt04_is_append_only(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            config["status"],
            "AUTHOR_ATTEMPT_03_FAILED_CLOSED_ATTEMPT_04_COORDINATE_SPACE_REPAIR_PREPARED_NOT_EXECUTED",
        )
        self.assertTrue(config["author_output"].endswith("/attempt_04"))
        for path, key in (
            (AUTHOR_ATTEMPT_03_SUMMARY, "author_attempt_03_summary_sha256"),
            (AUTHOR_ATTEMPT_03_FAILURE, "author_attempt_03_failure_sha256"),
            (AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE, "author_attempt_03_candidate_a_failure_sha256"),
            (AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE, "author_attempt_03_candidate_b_failure_sha256"),
            (AUTHOR_ATTEMPT_03_COORDINATE_DIAGNOSIS, "author_attempt_03_coordinate_diagnosis_sha256"),
        ):
            self.assertEqual(sha256_file(path), config[key])
        summary = json.loads(AUTHOR_ATTEMPT_03_SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["successful_candidate_count"], 0)
        self.assertTrue(summary["source_r19_unchanged"])
        for path in (AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE, AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE):
            failure = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                failure["error"],
                "seam median edge scale is implausible: 1.8541125424006801",
            )
        self.assertFalse(
            (PROJECT_ROOT / "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04").exists()
        )

    def test_attempt04_builds_and_checks_in_project_meters_then_writes_local(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        contract = config["attempt_04_coordinate_space_contract"]
        self.assertEqual(contract["construction_and_quality_space"], "project_world_meters")
        self.assertTrue(contract["live_full_precision_seam_from_canonical_ids"])
        self.assertTrue(contract["serialized_world_seam_is_crosscheck_not_construction_input"])
        self.assertEqual(
            contract["serialized_crosscheck_authority"],
            "passed_preflight_attempt_04_hash_bound_canonical_arrays",
        )
        self.assertTrue(contract["full_affine_exterior_ring_point_transform"])
        self.assertTrue(contract["inverse_transpose_normal_transform_and_renormalization"])
        self.assertEqual(contract["inverse_transform_generated_vertex_count"], 740)
        self.assertTrue(contract["original_seam_local_coordinates_reused_exactly"])
        self.assertTrue(contract["source_transform_must_match_exact_r19_matrix"])
        self.assertFalse(contract["arbitrary_nonuniform_scale_or_shear_supported"])
        self.assertTrue(contract["unsupported_transform_variation_fails_closed"])
        self.assertEqual(contract["maximum_seam_local_roundtrip_delta_local_units"], 1e-9)
        self.assertEqual(contract["maximum_generated_project_roundtrip_delta_m"], 1e-9)
        self.assertIn('seam_project_m = tuple(', source)
        self.assertIn('body.matrix_world @ Vector(point)', source)
        self.assertIn('sealed_preflight_mask["canonical_seam_world_coordinates"]', source)
        self.assertIn('positions_project_m, geometry_evidence = patch_contract.build_positions(', source)
        self.assertIn('quality = patch_contract.geometry_quality(positions_project_m, faces)', source)
        self.assertIn('generated_project_m = positions_project_m[patch_contract.SEAM_COUNT :]', source)
        self.assertIn('positions_body_local = seam_local + generated_body_local', source)
        self.assertIn('prepared["positions_body_local"][patch_contract.SEAM_COUNT :]', source)
        self.assertIn('"maximum_body_local_position_delta"', source)
        self.assertIn('"maximum_world_position_delta_m"', source)
        self.assertIn('"seam_affine_roundtrip_delta_unit": "body_local_units"', source)
        self.assertIn('"generated_project_roundtrip_delta_unit": "project_world_meters"', source)

    def test_attempt04_normal_order_and_saved_quality_are_world_consistent(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn('transformed_face_normals = patch_contract.transform_normals(', source)
        self.assertIn('average = sum((Vector(value) for value in transformed_face_normals)', source)
        self.assertIn('old_normal = _average_patch_normal_project_m(', source)
        self.assertIn('generated_normal = _face_normal_from_positions(faces[0], positions_project_m)', source)
        self.assertIn('"winding_comparison_coordinate_space": "project_world_meters"', source)
        verify = ast.get_source_segment(
            source,
            next(
                node
                for node in ast.walk(ast.parse(source))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "verify_saved_structure"
            ),
        )
        self.assertIn('positions_project_m = [', verify)
        self.assertIn('body.matrix_world @ Vector(position)', verify)
        self.assertIn('patch_contract.geometry_quality(', verify)
        self.assertIn('quality["coordinate_space"] = "project_world_meters"', verify)

    def test_attempt04_has_one_exact_author_command_and_no_output(self) -> None:
        value = AUTHOR_ATTEMPT_04_COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("--mode author"), 1)
        self.assertNotIn("--mode preflight", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertNotIn("--candidate-id", value)
        self.assertIn("attempt_04", value)
        self.assertIn(sha256_file(CONFIG), value)
        self.assertFalse(
            (PROJECT_ROOT / "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/attempt_04").exists()
        )


if __name__ == "__main__":
    unittest.main()
