"""Static verification for prepared, unexecuted R24 Attempt 33."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT33_CONFIG.json"
)
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt33.py"
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_33_EXACT_APPEND_RECONSTRUCTION_PROPOSAL.md"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_33_STATIC_CHECKPOINT.md"
)
EXPECTED_CONFIG_SHA256 = "715163fe202baccb219d385e162d944e67f2b06b0ce656ce17d41e5a00a0840a"
EXPECTED_WORKER_SHA256 = "f5ec3bc9c874bcb6541aa902b9a541cec7fd13099d0ebc3f5fd36910174eb126"
EXPECTED_PROPOSAL_SHA256 = "7c2c264a960221f6cac8037ffc6737dfe4fbea6bd8cb17d13ad69c210064fb4e"
EXPECTED_NAMES = [
    "216c8bc711374b3fbf0155edac218dc1.fbx.001",
    "Icosphere",
    "Object_2.001",
    "Object_23",
    "Object_4",
    "RootNode.001",
    "Sketchfab_model.001",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    path.relative_to(ROOT)
    return path


class Attempt33StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("attempt33_static", WORKER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def assert_record(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(sha256_file(path), record["sha256"], label)
        return path

    def test_01_artifact_hashes_and_worker_compile(self) -> None:
        self.assertEqual(CONFIG.stat().st_size, 10032)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(WORKER.stat().st_size, 18865)
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 9187)
        self.assertEqual(sha256_file(PROPOSAL), EXPECTED_PROPOSAL_SHA256)
        compile(self.source, str(WORKER), "exec")
        self.assertIn(EXPECTED_CONFIG_SHA256, self.source)

    def test_02_every_binding_and_proposal_is_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            self.assert_record(label, record)
        self.assert_record("proposal", self.config["proposal"])

    def test_03_worker_static_loader_and_overlay_verifier_pass(self) -> None:
        loaded = self.module.load_config()
        self.assertEqual(loaded, self.config)
        verified = self.module.verify_overlay(loaded)
        self.assertEqual(len(verified["records"]), 20)
        self.assertEqual(
            verified["attempt32_status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_NO_SAVE",
        )

    def test_04_attempt32_runtime_pass_and_external_integrity_are_exact(self) -> None:
        bindings = self.config["bindings"]
        inventory = json.loads(
            project_path(bindings["attempt32_inventory"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            inventory["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_NO_SAVE",
        )
        observation = inventory["append_observation"]
        self.assertEqual(observation["actual_appended_object_names"], EXPECTED_NAMES)
        self.assertEqual(observation["actual_new_collection_names"], [])
        self.assertEqual(
            observation["returned_target_slots"],
            [
                {
                    "index": 0,
                    "is_none": False,
                    "pointer": observation["returned_target_slots"][0]["pointer"],
                    "name": "Object_23",
                    "type": "MESH",
                    "data_name": "Ariel_Mesh_Genitalia_0",
                }
            ],
        )
        self.assertTrue(inventory["sealed_body_pre_post_exact"])
        self.assertTrue(inventory["bound_files_pre_post_exact"])
        for key in (
            "scene_link_reached",
            "dependency_cleanup_reached",
            "geometry_mutation_reached",
            "triangulation_reached",
            "reconstruction_reached",
            "graft_reached",
            "render_reached",
            "blend_saved",
            "runtime_changed",
        ):
            self.assertFalse(inventory[key], key)
        external = json.loads(
            project_path(bindings["attempt32_external_integrity"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(external["blender_exit_code"], 0)
        self.assertIsNone(external["native_invocation_error"])
        self.assertTrue(external["pre_post_exact"])
        self.assertEqual(external["before"], external["after"])
        self.assertEqual(len(external["before"]), 169)

    def test_05_exact_attempt16_contract_is_reused(self) -> None:
        contract = self.config["attempt16_append_contract"]
        attempt16 = json.loads(
            project_path(self.config["bindings"]["attempt16_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract, attempt16["append_contract"])
        self.assertEqual(contract["expected_appended_object_names"], EXPECTED_NAMES)
        self.assertEqual(
            canonical_sha256(EXPECTED_NAMES),
            "ef4ed395b5f7fc8c0a2d549a23c547d20d74cd45137e16cd68cc08482e08bb85",
        )
        dependencies = [name for name in EXPECTED_NAMES if name != "Object_23"]
        self.assertEqual(
            contract["dependency_object_names_removed_in_memory_only"], dependencies
        )
        self.assertEqual(
            canonical_sha256(dependencies),
            "b73a8998e582f5267f85bf9bf1a0bc5c89889fbb2d7c68ea44670b2e924d6269",
        )

    def test_06_attempt31_later_domain_engine_is_exact_and_only_output_is_overlaid(self) -> None:
        base = json.loads(
            project_path(self.config["bindings"]["attempt31_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        selected = base["selected_candidate"]
        self.assertEqual(selected["candidate"], "targeted_complete_vertex_stars_2_6_20_28")
        self.assertEqual(selected["face_count"], 104)
        self.assertEqual(selected["vertex_count"], 73)
        self.assertEqual(selected["edge_count"], 176)
        self.assertEqual(selected["interior_vertex_count"], 33)
        self.assertEqual(selected["boundary_edge_count"], 40)
        self.assertEqual(selected["minimum_boundary_angle_degrees"], 13.24909246109987)
        self.assertEqual(
            base["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0
        )
        self.assertEqual(
            base["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"],
            1e-10,
        )
        self.assertEqual(
            self.config["runtime_overlay"]["selected_candidate_inherited_without_change"],
            selected["candidate"],
        )
        self.assertIn('runtime_config = deepcopy(base_config)', self.source)
        self.assertIn('runtime_config["output"] = deepcopy', self.source)

    def test_07_blender_import_is_runtime_local_and_no_save_render_export_api_exists(self) -> None:
        top_imports = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                top_imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                top_imports.append(node.module)
        self.assertNotIn("bpy", top_imports)
        self.assertNotIn("bmesh", top_imports)
        for forbidden in (
            "save_as_mainfile",
            "save_mainfile",
            "write_homefile",
            "write_still",
            "bpy.ops.render",
            "export_scene",
            "export_mesh",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_08_every_append_gate_precedes_cleanup(self) -> None:
        source = self.source
        inventory_gate = source.index("if actual_names != expected_names")
        collection_gate = source.index('if any(signature["collection_names"]')
        signature_gate = source.index("patch_signature is None")
        dependency_gate = source.index("if sorted(name for name in actual_names")
        evidence_write = source.index("original_writer(inventory_path, inventory)", dependency_gate)
        detach = source.index("adult.parent = None")
        remove_dependencies = source.index("bpy.data.objects.remove(value, do_unlink=True)")
        self.assertLess(inventory_gate, detach)
        self.assertLess(collection_gate, detach)
        self.assertLess(signature_gate, detach)
        self.assertLess(dependency_gate, evidence_write)
        self.assertLess(evidence_write, detach)
        self.assertLess(detach, remove_dependencies)

    def test_09_cleanup_is_the_exact_attempt16_direction(self) -> None:
        for statement in (
            "adult.parent = None",
            "adult.matrix_parent_inverse.identity()",
            "adult.matrix_world = body.matrix_world.copy()",
            "adult.modifiers.remove(modifier)",
            "bpy.data.objects.remove(value, do_unlink=True)",
            "bpy.context.scene.collection.objects.link(adult)",
            "bpy.context.view_layer.update()",
        ):
            self.assertIn(statement, self.source)
        self.assertIn("module.append_patch = corrected_append_patch", self.source)
        self.assertNotIn("from tools.blender_simulate_kira_r24_blackproject_local_reconstruction_attempt15", self.source)

    def test_10_base_provider_and_writer_are_restored_in_finally(self) -> None:
        source = self.source
        run = source.index("base.run_blender_diagnostic(runtime_config, base_verified)")
        finally_index = source.index("finally:", run)
        self.assertLess(run, finally_index)
        for statement in (
            "base._load_module = original_loader",
            "base._exclusive_write_once = original_writer",
            "base.DEFAULT_CONFIG = original_default_config",
        ):
            self.assertGreater(source.index(statement, finally_index), finally_index)

    def test_11_evidence_is_exclusive_and_correctly_provenanced(self) -> None:
        self.assertIn('original_writer(inventory_path, inventory)', self.source)
        self.assertNotIn("write_text(", self.source)
        self.assertNotIn(".replace(path", self.source)
        self.assertIn('result["attempt33_orchestration"]', self.source)
        self.assertIn('"base_attempt31_worker"', self.source)
        self.assertIn('"attempt32_runtime_authority"', self.source)

    def test_12_wrapper_always_records_integrity_before_failure_propagation(self) -> None:
        source = self.proposal
        invocation = source.index("& $blender --background")
        finally_index = source.index("} finally {", invocation)
        post = source.index("$after = Get-Attempt33Inventory $targets", finally_index)
        create = source.index("[System.IO.FileMode]::CreateNew", post)
        integrity_failure = source.index("if (-not $exact)", create)
        invocation_failure = source.index("if ($null -ne $invocationError)", create)
        exit_failure = source.index("if ($exitCode -ne 0)", create)
        self.assertLess(invocation, finally_index)
        self.assertLess(finally_index, post)
        self.assertLess(post, create)
        self.assertLess(create, integrity_failure)
        self.assertLess(create, invocation_failure)
        self.assertLess(create, exit_failure)
        self.assertEqual(source.count("$ErrorActionPreference = 'Continue'"), 1)
        self.assertIn("$ErrorActionPreference = $savedPreference", source)

    def test_13_prepared_state_has_no_runtime_artifacts(self) -> None:
        output = project_path(self.config["runtime_overlay"]["output"]["root"])
        launch = self.config["launch_contract"]
        self.assertFalse(output.exists())
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse(project_path(launch[key]).exists(), key)

    def test_14_static_truth_does_not_claim_execution_or_repair(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["attempt32_runtime_pass_bound"])
        for key, value in truth.items():
            if key != "attempt32_runtime_pass_bound":
                self.assertFalse(value, key)

    def test_15_tamper_detection_rejects_scope_contract_and_output_drift(self) -> None:
        tampered = json.loads(json.dumps(self.config))
        tampered["scope"]["blend_save_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden scope"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["attempt16_append_contract"]["expected_appended_object_names"].pop()
        with self.assertRaisesRegex(RuntimeError, "append contract drifted"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["runtime_overlay"]["output"]["root"] = "drift"
        with self.assertRaisesRegex(RuntimeError, "output overlay drifted"):
            self.module.validate_config(tampered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
