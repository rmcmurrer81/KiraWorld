from __future__ import annotations

import ast
import copy
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

from tools import blender_author_kira_r24_external_surface_operation as author
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3 as r3


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "blender_author_kira_r24_external_surface_operation.py"


class MockAdapter:
    def __init__(self, *, fail_at: str | None = None, linked_proof: bool = False) -> None:
        self.fail_at = fail_at
        self.linked_proof = linked_proof
        self.live_state = "ORIGINAL"
        self.stage_count = 0
        self.activate_count = 0
        self.finalize_count = 0
        self.rollback_count = 0

    def protected_snapshot(self) -> str:
        return "protected-original-sha256" if self.live_state == "ORIGINAL" else "protected-drift-sha256"

    def stage(self, plan: author.AuthorPlan) -> object:
        self.stage_count += 1
        if self.fail_at == "stage":
            raise RuntimeError("synthetic stage failure")
        return {"plan": plan.plan_sha256}

    def inspect(self, stage: object, plan: author.AuthorPlan) -> dict[str, object]:
        del stage
        if self.fail_at == "inspect":
            raise RuntimeError("synthetic inspect failure")
        return {
            "plan_sha256": plan.plan_sha256,
            "outside_sha256": plan.outside_sha256,
            "proof_collection_link_count": 1 if self.linked_proof else 0,
            "proof_face_count": author.EXPECTED_SOURCE_FACE_COUNT,
            "replacement_face_count": author.EXPECTED_ESTAR_FACE_COUNT,
            "boundary_vertex_count": author.EXPECTED_BOUNDARY_COUNT,
            "new_interior_vertex_count": len(plan.interior_vertices),
            "material_name": author.MATERIAL_NAME,
            "body_staged_not_live": True,
            "maximum_world_displacement_m": 0.001,
            "minimum_world_triangle_area_m2": 1.0e-7,
            "save_performed": False,
        }

    def activate(self, stage: object) -> None:
        del stage
        self.activate_count += 1
        if self.fail_at == "activate":
            raise RuntimeError("synthetic activation failure")
        if self.fail_at == "protected_drift":
            self.live_state = "DRIFT"

    def finalize(self, stage: object) -> None:
        del stage
        self.finalize_count += 1
        if self.fail_at == "finalize":
            raise RuntimeError("synthetic finalize failure")

    def rollback(self, stage: object | None) -> None:
        del stage
        self.rollback_count += 1
        self.live_state = "ORIGINAL"


class TestR24ExternalSurfaceAuthorOperation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = r3.exact_context()
        cls.plan = author.build_author_plan(cls.context)

    def quality_passing_plan(self) -> author.AuthorPlan:
        geometry = dict(self.plan.geometry)
        geometry["minimum_triangle_angle_degrees_local"] = 12.5
        geometry["boundary_maximum_local_displacement"] = 0.0
        # This fixture exercises transaction mechanics only.  It is not an R24
        # candidate and cannot be serialized by the production controller.
        return replace(self.plan, geometry=geometry)

    def test_01_import_is_blender_inert_and_has_no_main_side_effect(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_imports = {
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("bpy", top_imports)
        self.assertNotIn("bmesh", top_imports)
        self.assertNotIn("save_as_mainfile", source)
        self.assertNotIn("write_still", source)
        self.assertNotIn("static_r4", source)
        self.assertFalse(any(isinstance(node, ast.If) and any(isinstance(item, ast.Name) and item.id == "__name__" for item in ast.walk(node.test)) for node in tree.body))
        before = set(sys.modules)
        spec = importlib.util.spec_from_file_location("_r24_author_inert_probe", MODULE_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec.name, None)
        self.assertNotIn("bpy", set(sys.modules) - before)
        self.assertNotIn("bmesh", set(sys.modules) - before)

    def test_02_exact_boundary_face_and_vertex_budgets(self) -> None:
        self.assertEqual(len(self.plan.complete_faces), 1436)
        self.assertEqual(len(self.plan.replacement_faces), 161)
        self.assertEqual(len(self.plan.boundary_cycle), 41)
        self.assertEqual(len(self.plan.interior_vertices), 61)
        self.assertLessEqual(len(self.plan.interior_vertices), 160)
        self.assertEqual(self.plan.topology["boundary_edge_count"], 41)
        self.assertEqual(self.plan.topology["invalid_edge_count"], 0)
        self.assertEqual(self.plan.topology["connected_components"], 1)
        self.assertEqual(self.plan.topology["euler_characteristic"], 1)

    def test_03_complete_patch_keeps_every_outside_face_exact(self) -> None:
        source_faces = self.context["source_mesh"]["faces"]
        for index in self.context["domains"]["outside"]:
            self.assertEqual(self.plan.complete_faces[index], tuple(source_faces[index]))
        first = author.build_author_plan(self.context)
        second = author.build_author_plan(self.context)
        self.assertEqual(first.outside_sha256, second.outside_sha256)
        self.assertEqual(first.plan_sha256, second.plan_sha256)

    def test_04_boundary_is_fixed_and_every_interior_binding_is_new(self) -> None:
        source_positions = self.context["source_mesh"]["positions"]
        for index in self.plan.boundary_cycle:
            self.assertEqual(self.plan.positions[index], tuple(source_positions[index]))
            self.assertEqual(self.plan.provenance[index][2], (0.0, 0.0, 0.0))
        for index in self.plan.interior_vertices:
            self.assertNotEqual(self.plan.positions[index], tuple(source_positions[index]))
            self.assertGreater(sum(value * value for value in self.plan.provenance[index][2]), 0.0)
        boundary = set(self.plan.boundary_cycle)
        self.assertTrue(
            all(
                any(vertex not in boundary for vertex in self.context["source_mesh"]["faces"][face_index])
                for face_index in self.context["domains"]["estar"]
            )
        )

    def test_05_one_hot_binding_preserves_uv_normal_and_native_weights(self) -> None:
        source = self.context["source_mesh"]
        for vertex_index in self.plan.interior_vertices[:12]:
            source_face, barycentric, _displacement = self.plan.provenance[vertex_index]
            payload = author.interpolate_source_payload(self.context, source_face, barycentric)
            face = source["faces"][source_face]
            offset = barycentric.index(1.0)
            self.assertEqual(face[offset], vertex_index)
            self.assertEqual(payload["uv"], [float(value) for value in source["texcoords"][vertex_index]])
            expected = {
                int(joint): float(weight)
                for joint, weight in zip(source["joints"][vertex_index], source["weights"][vertex_index], strict=True)
                if float(weight) > 0.0
            }
            total = sum(expected.values())
            self.assertEqual(
                payload["joint_weights"],
                [[joint, expected[joint] / total] for joint in sorted(expected)],
            )

    def test_06_known_exact_proposal_fails_quality_before_staging(self) -> None:
        self.assertLess(self.plan.geometry["minimum_triangle_angle_degrees_local"], 12.0)
        adapter = MockAdapter()
        with self.assertRaises(author.R24AuthorGeometryGateError):
            author._apply_plan_transaction(self.plan, adapter)
        self.assertEqual(adapter.stage_count, 0)
        self.assertEqual(adapter.rollback_count, 0)

    def test_07_mock_transaction_is_deterministic_and_never_claims_acceptance(self) -> None:
        plan = self.quality_passing_plan()
        first_adapter = MockAdapter()
        second_adapter = MockAdapter()
        first = author._apply_plan_transaction(plan, first_adapter)
        second = author._apply_plan_transaction(plan, second_adapter)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "AUTHORED_IN_MEMORY_FRESH_R5_EVALUATION_REQUIRED_NOT_ACCEPTED")
        self.assertFalse(first["proof_object_linked"])
        self.assertFalse(first["save_performed"])
        self.assertFalse(first["candidate_accepted"])
        self.assertEqual(first_adapter.stage_count, 1)
        self.assertEqual(first_adapter.activate_count, 1)
        self.assertEqual(first_adapter.finalize_count, 1)
        self.assertEqual(first_adapter.rollback_count, 0)

    def test_08_linked_proof_is_rejected_and_rolled_back(self) -> None:
        adapter = MockAdapter(linked_proof=True)
        with self.assertRaises(author.R24AuthorOperationError):
            author._apply_plan_transaction(self.quality_passing_plan(), adapter)
        self.assertEqual(adapter.activate_count, 0)
        self.assertEqual(adapter.rollback_count, 1)
        self.assertEqual(adapter.protected_snapshot(), "protected-original-sha256")

    def test_09_failures_are_atomic_before_and_after_activation(self) -> None:
        for failure in ("stage", "inspect", "activate", "protected_drift", "finalize"):
            with self.subTest(failure=failure):
                adapter = MockAdapter(fail_at=failure)
                with self.assertRaises((RuntimeError, author.R24AuthorOperationError)):
                    author._apply_plan_transaction(self.quality_passing_plan(), adapter)
                self.assertEqual(adapter.rollback_count, 1)
                self.assertEqual(adapter.protected_snapshot(), "protected-original-sha256")

    def test_10_stage_contract_carries_material_uv_weight_and_scope_truth(self) -> None:
        plan = self.quality_passing_plan()
        adapter = MockAdapter()
        result = author._apply_plan_transaction(plan, adapter)
        self.assertEqual(result["stage"]["material_name"], author.MATERIAL_NAME)
        self.assertEqual(result["stage"]["outside_sha256"], plan.outside_sha256)
        self.assertEqual(result["stage"]["proof_collection_link_count"], 0)
        self.assertEqual(result["authorized_mutated_objects"], [author.BODY_OBJECT_NAME, author.PROOF_OBJECT_NAME])
        self.assertEqual(
            result["evidence_sha256"],
            author.canonical_sha256({key: value for key, value in result.items() if key != "evidence_sha256"}),
        )

    def test_11_context_and_body_semantic_identity_fail_closed(self) -> None:
        changed = copy.deepcopy(self.context)
        changed["source_mesh"]["positions"][0][0] += 1.0e-5
        with self.assertRaisesRegex(author.R24AuthorOperationError, "source-mesh context changed"):
            author.build_author_plan(changed)

        class Mesh:
            name = "Wrong_Mesh"

        class Body:
            name = author.BODY_OBJECT_NAME
            type = "MESH"
            data = Mesh()

        with self.assertRaisesRegex(author.R24AuthorOperationError, "exact already-open R19 body"):
            author.author_external_surface_r24(
                body=Body(),
                context=self.context,
                rig=object(),
                bpy_module=object(),
            )


if __name__ == "__main__":
    unittest.main()
