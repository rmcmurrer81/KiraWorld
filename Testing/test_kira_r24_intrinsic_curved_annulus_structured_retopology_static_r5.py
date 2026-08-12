from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]

from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r5 as r5


def identity(scale: float = 1.0) -> list[list[float]]:
    return [
        [scale, 0.0, 0.0, 0.0],
        [0.0, scale, 0.0, 0.0],
        [0.0, 0.0, scale, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def typed_row(name: str, digest: str = "a" * 64, *, users: int | None = 1) -> dict[str, object]:
    return {
        "name": name,
        "direct_block_sha256": digest,
        "id_user_count_normalized_block_sha256": "b" * 64,
        "id_user_count": users,
    }


def typed_pair() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    source = {
        "semantic_ids": {
            "OB": [typed_row("Body")],
            "ME": [typed_row("BodyMesh")],
            "AR": [typed_row("Armature", "1" * 64)],
            "AC": [typed_row("Action", "2" * 64)],
            "MA": [typed_row("Skin", "3" * 64, users=2)],
        }
    }
    candidate = copy.deepcopy(source)
    candidate["semantic_ids"]["OB"].append(typed_row("Patch"))
    candidate["semantic_ids"]["ME"].append(typed_row("PatchMesh"))
    candidate["semantic_ids"]["MA"][0]["id_user_count"] = 3
    contract = {
        "artifact_semantic_identity": {
            "patch_object_name": "Patch",
            "patch_mesh_name": "PatchMesh",
            "required_material_name": "Skin",
        }
    }
    return source, candidate, contract


def object_row(name: str, data: str, *, collections: list[str]) -> dict[str, object]:
    return {
        "name": name,
        "type": "MESH",
        "data_name": data,
        "parent_name": None,
        "collection_names": collections,
        "hide_viewport": False,
        "hide_render": False,
        "rna": {"visible_camera": True},
        "constraints": [],
        "animation_data": None,
        "pose_bones": [],
    }


def state_pair() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    source_state = {
        "objects": [object_row("Body", "BodyMesh", collections=["Collection"])],
        "mesh_objects": [],
        "armature_objects": [{"object_name": "Rig", "data_semantics": {"constraints": []}}],
        "mesh_datablocks": [
            {"name": "BodyMesh", "users": 1, "object_users": ["Body"], "semantic_sha256": "1" * 64},
            {"name": "OtherMesh", "users": 0, "object_users": [], "semantic_sha256": "2" * 64},
        ],
        "armature_datablocks": [{"name": "Armature", "bones": [{"constraints": []}]}],
        "materials": [{"name": "Skin", "users": 2, "rna": {}, "node_tree": {"nodes": []}}],
        "actions": [{"name": "Action", "fcurves": [{"modifiers": []}]}],
        "images": [{"name": "Packed", "packed_bytes": 3, "packed_sha256": "3" * 64}],
        "node_groups": [],
        "collections": [{"name": "Collection", "objects": ["Body"], "children": [], "rna": {}}],
        "worlds": [{"name": "World", "rna": {"color": [0.1, 0.1, 0.1]}}],
        "scenes": [{"name": "Scene", "nested": {"render": {"resolution_x": 1920}}}],
        "intersection_reports": {},
    }
    candidate_state = copy.deepcopy(source_state)
    candidate_state["objects"].append(object_row("Patch", "PatchMesh", collections=[]))
    candidate_state["mesh_datablocks"].append(
        {"name": "PatchMesh", "users": 1, "object_users": ["Patch"], "semantic_sha256": "4" * 64}
    )
    candidate_state["materials"][0]["users"] = 3
    contract = {
        "artifact_semantic_identity": {
            "body_object_name": "Body",
            "body_mesh_name": "BodyMesh",
            "patch_object_name": "Patch",
            "patch_mesh_name": "PatchMesh",
            "required_material_name": "Skin",
        }
    }
    return {"state": source_state}, {"state": candidate_state}, contract


def triangle_mesh(scale: float) -> dict[str, object]:
    return {
        "matrix_world": identity(scale),
        "vertices": [
            {"index": 0, "coordinate_local_m": [0.0, 0.0, 0.0]},
            {"index": 1, "coordinate_local_m": [0.001, 0.0, 0.0]},
            {"index": 2, "coordinate_local_m": [0.0, 0.001, 0.0]},
        ],
        "polygons": [
            {"index": 0, "vertices": [0, 1, 2], "loop_indices": [0, 1, 2], "material_index": 0}
        ],
        "loops": [
            {"index": 0, "vertex_index": 0},
            {"index": 1, "vertex_index": 1},
            {"index": 2, "vertex_index": 2},
        ],
        "loop_triangles": [
            {"index": 0, "polygon_index": 0, "vertices": [0, 1, 2], "loops": [0, 1, 2], "material_index": 0}
        ],
    }


class R5StaticGateTests(unittest.TestCase):
    def test_01_r5_contract_and_implementation_are_sealed(self) -> None:
        contract = r5.load_sealed_contract()
        self.assertEqual(contract["schema"], "kira.avatar.r24.artifact_derived_gate.v5")
        self.assertEqual(r5.normalized_worker_sha256(), contract["authorized_implementation"]["worker"]["normalized_semantic_sha256"])

    def test_02_r4_audit_is_exact_parent_and_r4_stays_rejected(self) -> None:
        contract = r5.load_sealed_contract()
        self.assertEqual(contract["status"], "STATIC_R5_REPAIRED_GATE_PREPARED_INDEPENDENT_AUDIT_REQUIRED_NOT_EXECUTION_AUTHORIZED")
        self.assertTrue(contract["r5_amendments"]["typed_and_extraction_one_digest"])

    def test_03_invoke_extractor_requires_expected_preflight_digest(self) -> None:
        self.assertIn("expected_sha256", r5._invoke_extractor.__annotations__)
        self.assertNotEqual(r5._invoke_extractor.__defaults__, (900,))

    def test_04_guard_rejects_wrong_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "candidate.blend"
            path.write_bytes(b"one")
            with self.assertRaises(r5.R5ExtractionError):
                with r5._guarded_artifact(path, "0" * 64):
                    pass

    def test_05_guard_detects_in_place_toctou_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "candidate.blend"
            path.write_bytes(b"one")
            with self.assertRaises(r5.R5ExtractionError):
                with r5._guarded_artifact(path) as guard:
                    path.write_bytes(b"two")
                    r5._assert_guard(guard, "adversarial_replacement")

    def test_06_exact_typed_inventory_accepts_only_named_patch_additions(self) -> None:
        source, candidate, contract = typed_pair()
        self.assertEqual(r5.typed_inventory_failures(source, candidate, contract), set())

    def test_07_unlinked_extra_mesh_datablock_is_rejected(self) -> None:
        source, candidate, contract = typed_pair()
        candidate["semantic_ids"]["ME"].append(typed_row("UNLINKED_EXTRA_MESH_DATABLOCK"))
        self.assertIn("typed_sdna:exact_ME_inventory", r5.typed_inventory_failures(source, candidate, contract))

    def test_08_unlinked_extra_armature_datablock_is_rejected(self) -> None:
        source, candidate, contract = typed_pair()
        candidate["semantic_ids"]["AR"].append(typed_row("UNLINKED_EXTRA_ARMATURE_DATABLOCK"))
        self.assertIn("typed_sdna:exact_AR_inventory", r5.typed_inventory_failures(source, candidate, contract))

    def test_09_extracted_unlinked_mesh_inventory_is_also_exact(self) -> None:
        source, candidate, contract = state_pair()
        self.assertEqual(r5.validate_complete_protected_state(source, candidate, contract), set())
        candidate["state"]["mesh_datablocks"].append(
            {"name": "Hidden", "users": 0, "object_users": [], "semantic_sha256": "9" * 64}
        )
        self.assertIn("protected_state:exact_mesh_datablock_inventory", r5.validate_complete_protected_state(source, candidate, contract))

    def test_10_body_hide_and_collection_drift_are_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["objects"][0]["hide_render"] = True
        candidate["state"]["objects"][0]["collection_names"] = []
        self.assertIn("protected_state:object:Body:source_exact", r5.validate_complete_protected_state(source, candidate, contract))

    def test_11_scene_render_and_collection_state_drift_are_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["scenes"][0]["nested"]["render"]["resolution_x"] = 10
        candidate["state"]["collections"][0]["objects"] = []
        failures = r5.validate_complete_protected_state(source, candidate, contract)
        self.assertIn("protected_state:scenes:source_exact", failures)
        self.assertIn("protected_state:collections:source_exact", failures)

    def test_12_detached_patch_cannot_be_linked_to_a_collection(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["objects"][1]["collection_names"] = ["Collection"]
        self.assertIn("protected_state:patch_object_detached", r5.validate_complete_protected_state(source, candidate, contract))

    def test_13_area_is_measured_in_world_space(self) -> None:
        mesh = triangle_mesh(0.00952381)
        failures = r5.validate_render_triangulation(mesh, 1e-10, 0.0)
        self.assertIn("render:minimum_world_triangle_area", failures)

    def test_14_world_area_passes_when_world_triangle_really_exceeds_threshold(self) -> None:
        mesh = triangle_mesh(1.0)
        failures = r5.validate_render_triangulation(mesh, 1e-10, 0.0)
        self.assertNotIn("render:minimum_world_triangle_area", failures)

    def test_15_rig_constraint_child_change_is_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["armature_objects"][0]["data_semantics"]["constraints"].append({"type": "COPY"})
        self.assertIn("child_graph:armature_objects:source_exact", r5.validate_complete_child_graphs(source, candidate, contract))

    def test_16_action_modifier_child_change_is_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["actions"][0]["fcurves"][0]["modifiers"].append({"type": "NOISE", "strength": 1.0})
        self.assertIn("child_graph:actions:source_exact", r5.validate_complete_child_graphs(source, candidate, contract))

    def test_17_same_length_packed_image_change_is_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["images"][0]["packed_sha256"] = "4" * 64
        self.assertIn("protected_state:images:source_exact", r5.validate_complete_protected_state(source, candidate, contract))

    def test_18_material_node_property_change_is_rejected(self) -> None:
        source, candidate, contract = state_pair()
        candidate["state"]["materials"][0]["node_tree"]["nodes"].append({"type": "ShaderNodeValue", "value": 0.5})
        self.assertIn("child_graph:material:Skin:semantic_source_exact", r5.validate_complete_child_graphs(source, candidate, contract))

    def test_19_material_id_us_requires_exact_source_plus_one(self) -> None:
        source, candidate, contract = typed_pair()
        for value in (-32768, 0, 2, 4, 32767):
            changed = copy.deepcopy(candidate)
            changed["semantic_ids"]["MA"][0]["id_user_count"] = value
            self.assertIn(
                "typed_sdna:MA:Skin:controlled_id_us_transition",
                r5.typed_inventory_failures(source, changed, contract),
            )

    def test_20_public_path_only_evaluator_cannot_skip_author_exit(self) -> None:
        result = r5.evaluate_candidate_artifact(Path("candidate.blend"), Path("blender.exe"))
        self.assertFalse(result["eligible"])
        self.assertEqual(result["failure_names"], ["author_exit_attestation_required_use_run_author_then_evaluate"])

    def test_21_forged_author_attestation_is_rejected(self) -> None:
        contract = r5.load_sealed_contract()
        attestation = r5._AuthorExitAttestation(object(), 1, "a" * 64, 0, True, 0, "x", 1, "b" * 64)
        with mock.patch.object(r5, "load_sealed_contract", return_value=contract):
            result = r5._evaluate_post_author(Path("x"), Path("y"), attestation)
        self.assertEqual(result["failure_names"], ["author:clean_exit_not_evaluator_attested"])

    def test_22_controller_waits_and_builds_post_exit_attestation(self) -> None:
        contract = r5.load_sealed_contract()
        runtime = ROOT / contract["authorized_implementation"]["candidate_path_prefix"]
        candidate = runtime / "attempt_99" / "candidate.blend"

        class FakeProcess:
            pid = 4242

            def communicate(self, timeout: int | None = None):
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(b"post-exit")
                return b"", b""

            def poll(self):
                return 0

        captured: dict[str, object] = {}

        def accept(path, blender, attestation):
            captured["attestation"] = attestation
            return {"eligible": False, "failure_names": ["test_stop_before_extraction"]}

        try:
            if candidate.exists():
                candidate.unlink()
            with mock.patch.object(r5.subprocess, "Popen", return_value=FakeProcess()), mock.patch.object(r5, "_evaluate_post_author", side_effect=accept):
                result = r5.run_author_then_evaluate(["sealed-author"], candidate, Path("blender"))
            self.assertEqual(result["failure_names"], ["test_stop_before_extraction"])
            attestation = captured["attestation"]
            self.assertEqual(attestation.pid, 4242)
            self.assertTrue(attestation.wait_completed)
            self.assertEqual(attestation.candidate_sha256, hashlib.sha256(b"post-exit").hexdigest())
        finally:
            if candidate.exists():
                candidate.unlink()
            if candidate.parent.is_dir():
                candidate.parent.rmdir()
            if runtime.is_dir() and not any(runtime.iterdir()):
                runtime.rmdir()

    def test_23_static_evaluation_never_launches_blender_or_grants_authority(self) -> None:
        with mock.patch.object(r5.subprocess, "run", side_effect=AssertionError("must not launch")), mock.patch.object(r5.subprocess, "Popen", side_effect=AssertionError("must not launch")):
            result = r5.static_evaluation()
        self.assertFalse(result["blender_launched"])
        self.assertFalse(result["execution_authority_granted"])
        self.assertFalse(result["candidate_created"])

    def test_24_package_inventory_is_exact_pre_audit(self) -> None:
        self.assertEqual(r5.package_inventory_status()["state"], "PRE_AUDIT_EXACT")


if __name__ == "__main__":
    unittest.main()

