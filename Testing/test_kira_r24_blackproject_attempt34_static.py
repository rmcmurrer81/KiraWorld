"""Static verification for prepared, unexecuted R24 Attempt 34."""

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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT34_CONFIG.json"
)
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt34.py"
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_34_BMESH_LIFETIME_REACQUISITION_PROPOSAL.md"
)
EXPECTED_CONFIG_SHA256 = "897e1a35b4334677d6a829f65bdad82b7b310359298ff888bc71bc42e9fd40be"
EXPECTED_WORKER_SHA256 = "42b302a28048204acd95f554569a0cce2f1234c74f7b95ae4d0e7e73c26aa538"
EXPECTED_PROPOSAL_SHA256 = "dd31c267190e22db8ff4b101700ca86dc9979cd4085b7d74df211341d63db545"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    path.relative_to(ROOT)
    return path


class Attempt34StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("attempt34_static", WORKER)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def assert_record(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(sha256_file(path), record["sha256"], label)
        return path

    def test_01_artifact_hashes_and_compile(self) -> None:
        self.assertEqual(CONFIG.stat().st_size, 8413)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(WORKER.stat().st_size, 21920)
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 9491)
        self.assertEqual(sha256_file(PROPOSAL), EXPECTED_PROPOSAL_SHA256)
        compile(self.source, str(WORKER), "exec")
        self.assertIn(EXPECTED_CONFIG_SHA256, self.source)

    def test_02_every_binding_and_proposal_is_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            self.assert_record(label, record)
        self.assert_record("proposal", self.config["proposal"])

    def test_03_static_loader_overlay_and_derived_source_pass(self) -> None:
        loaded = self.module.load_config()
        self.assertEqual(loaded, self.config)
        verified = self.module.verify_overlay(loaded)
        self.assertEqual(len(verified["records"]), 15)
        base = project_path(
            self.config["bindings"]["attempt31_worker"]["path"]
        ).read_text(encoding="utf-8")
        patched = self.module.patch_attempt31_source(base, loaded)
        compile(patched, "attempt34_derived_attempt31", "exec")
        self.assertEqual(
            self.module.sha256_text(patched),
            "0311bc721f9872fc76262b883bdb3f79b7424c70053dc5d3105714d4867fa2f0",
        )
        self.assertEqual(base.count(self.module.OLD_CAPTURE_BLOCK), 1)
        self.assertEqual(patched.count(self.module.NEW_CAPTURE_BLOCK), 1)
        self.assertNotIn(self.module.OLD_CAPTURE_BLOCK, patched)

    def test_04_attempt33_append_pass_lifecycle_failure_and_integrity_are_exact(self) -> None:
        bindings = self.config["bindings"]
        append = json.loads(
            project_path(bindings["attempt33_append_inventory"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            append["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_BEFORE_CLEANUP",
        )
        self.assertEqual(
            append["actual_appended_object_names_sha256"],
            "ef4ed395b5f7fc8c0a2d549a23c547d20d74cd45137e16cd68cc08482e08bb85",
        )
        self.assertEqual(append["actual_new_collection_names"], [])
        failure = json.loads(
            project_path(bindings["attempt33_failure"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(failure["error_type"], "ReferenceError")
        self.assertEqual(failure["error"], "BMesh data of type BMVert has been removed")
        self.assertIn("line 1708, in attempt31_capture_local_domain", failure["traceback"])
        self.assertIn("line 1709, in <genexpr>", failure["traceback"])
        self.assertFalse(failure["render_reached"])
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        external = json.loads(
            project_path(bindings["attempt33_external_integrity"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(external["blender_exit_code"], 1)
        self.assertIsNone(external["native_invocation_error"])
        self.assertTrue(external["pre_post_exact"])
        self.assertEqual(external["before"], external["after"])
        self.assertEqual(len(external["before"]), 180)

    def test_05_old_and_new_lifecycle_blocks_are_hash_bound_and_unique(self) -> None:
        patch = self.config["lifecycle_patch"]
        self.assertEqual(
            self.module.sha256_text(self.module.OLD_CAPTURE_BLOCK),
            "781c8059de111e2471ebbb6e25369059a33b0451fdc75ca4c6c2c6ef39663973",
        )
        self.assertEqual(
            self.module.sha256_text(self.module.NEW_CAPTURE_BLOCK),
            "fdc48d58a6c809569c8f09480f858d6814cafdb2293387dcd013210fd2d43949",
        )
        self.assertEqual(patch["old_block_sha256"], self.module.sha256_text(self.module.OLD_CAPTURE_BLOCK))
        self.assertEqual(patch["new_block_sha256"], self.module.sha256_text(self.module.NEW_CAPTURE_BLOCK))
        self.assertEqual(
            patch["derived_source_sha256"],
            "0311bc721f9872fc76262b883bdb3f79b7424c70053dc5d3105714d4867fa2f0",
        )
        self.assertEqual(patch["exact_replacement_count"], 1)

    def test_06_every_identity_and_key_is_materialized_before_layer_creation(self) -> None:
        block = self.module.NEW_CAPTURE_BLOCK
        tag = block.index('captured["patch_tag_snapshot"] = _begin_tagged_preservation')
        for statement in (
            "selected_face_index_ids =",
            "selected_vertex_index_ids =",
            "selected_edge_index_ids =",
            "local_boundary_edge_index_ids =",
            "cycle_vertex_index_ids =",
            "interior_vertex_index_ids =",
            "immutable_boundary_vertex_keys =",
            "immutable_boundary_edge_keys =",
            'captured["local_boundary_vertex_keys"] =',
            'captured["local_boundary_edge_keys"] =',
        ):
            self.assertLess(block.index(statement), tag, statement)

    def test_07_no_pre_layer_bmesh_wrapper_escapes(self) -> None:
        block = self.module.NEW_CAPTURE_BLOCK
        tag = block.index('captured["patch_tag_snapshot"] = _begin_tagged_preservation')
        returned = block.index("            return {", tag)
        tail = block[tag:returned]
        for statement in (
            "selected_faces = {bm.faces[index]",
            "selected_vertices = {",
            "selected_edges = {bm.edges[index]",
            "local_boundary_edges = {",
            "interior = {bm.verts[index]",
            "reacquired_cycle = provider.ordered_cycle(local_boundary_edges)",
            "cycle = [",
        ):
            self.assertIn(statement, tail)
        for name in (
            '"selected_faces": selected_faces',
            '"selected_vertices": selected_vertices',
            '"selected_edges": selected_edges',
            '"local_boundary_edges": local_boundary_edges',
            '"local_boundary": set(cycle)',
            '"interior": interior',
            '"cycle": cycle',
        ):
            self.assertIn(name, block[returned:])
        self.assertIn("No pre-layer BMesh element wrapper may cross this boundary", tail)

    def test_08_reacquired_domain_is_fully_revalidated_fail_closed(self) -> None:
        block = self.module.NEW_CAPTURE_BLOCK
        for condition in (
            "selected_face_index_ids",
            "selected_vertex_index_ids",
            "selected_edge_index_ids",
            "local_boundary_edge_index_ids",
            "cycle_vertex_index_ids",
            "interior_vertex_index_ids",
            "reacquired_vertices_from_faces != selected_vertices",
            "reacquired_edges_from_faces != selected_edges",
            "reacquired_boundary_edges != local_boundary_edges",
            "selected_vertices - set(cycle) != interior",
            "reacquired_boundary_edge_ids != boundary_edge_ids",
            "immutable_boundary_vertex_keys",
            "immutable_boundary_edge_keys",
            "post_layer_global_vertices.intersection(selected_vertices)",
            "Attempt 34 post-layer domain reacquisition drifted",
        ):
            self.assertIn(condition, block)

    def test_09_candidate_algorithm_and_hard_gates_remain_byte_bound(self) -> None:
        base = json.loads(
            project_path(self.config["bindings"]["attempt31_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        selected = base["selected_candidate"]
        self.assertEqual(selected["candidate"], "targeted_complete_vertex_stars_2_6_20_28")
        self.assertEqual(
            [
                selected["face_count"],
                selected["vertex_count"],
                selected["edge_count"],
                selected["interior_vertex_count"],
                selected["boundary_edge_count"],
            ],
            [104, 73, 176, 33, 40],
        )
        self.assertEqual(base["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(base["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"], 1e-10)
        self.assertNotIn("def reconstruct_local_domain", self.source)
        self.assertIn("attempt33.run_blender(config_path, runtime_config)", self.source)

    def test_10_static_import_is_blender_free_and_has_no_save_render_export_api(self) -> None:
        top_imports = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                top_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
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

    def test_11_orchestration_is_provenanced_relabelled_and_restored(self) -> None:
        for statement in (
            'result["attempt34_lifecycle_patch"]',
            'result["schema"] = result["schema"].replace("attempt33", "attempt34")',
            'result["attempt34_orchestration"]',
            "attempt33.load_module = attempt34_loader",
            "attempt33.relabel_base_evidence = attempt34_relabel",
            "attempt33.__file__ = str(Path(__file__).resolve())",
            "attempt33.load_module = original_loader",
            "attempt33.relabel_base_evidence = original_relabel",
            "attempt33.__file__ = original_file",
        ):
            self.assertIn(statement, self.source)
        run = self.source.index("attempt33.run_blender(config_path, runtime_config)")
        finally_index = self.source.index("finally:", run)
        self.assertLess(run, finally_index)

    def test_12_wrapper_records_integrity_before_propagating_failure(self) -> None:
        source = self.proposal
        invocation = source.index("& $blender --background")
        finally_index = source.index("} finally {", invocation)
        after = source.index("$after = Get-Attempt34Inventory $targets", finally_index)
        create = source.index("[System.IO.FileMode]::CreateNew", after)
        self.assertLess(invocation, finally_index)
        self.assertLess(finally_index, after)
        self.assertLess(after, create)
        for text in (
            "if (-not $exact)",
            "if ($null -ne $invocationError)",
            "if ($exitCode -ne 0)",
        ):
            self.assertGreater(source.index(text, create), create)
        self.assertEqual(source.count("$ErrorActionPreference = 'Continue'"), 1)
        self.assertIn("$ErrorActionPreference = $savedPreference", source)

    def test_13_prepared_state_has_no_runtime_artifacts_and_no_overclaim(self) -> None:
        output = project_path(self.config["runtime_overlay"]["output"]["root"])
        self.assertFalse(output.exists())
        for key in ("stdout", "stderr", "external_integrity"):
            self.assertFalse(project_path(self.config["launch_contract"][key]).exists())
        truth = self.config["truth"]
        self.assertTrue(truth["attempt33_append_pass_bound"])
        self.assertTrue(truth["attempt33_lifecycle_failure_bound"])
        for key, value in truth.items():
            if key not in {"attempt33_append_pass_bound", "attempt33_lifecycle_failure_bound"}:
                self.assertFalse(value, key)

    def test_14_tamper_detection_rejects_scope_patch_and_source_drift(self) -> None:
        tampered = json.loads(json.dumps(self.config))
        tampered["scope"]["repair_domain_change_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden scope"):
            self.module.validate_config(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["lifecycle_patch"]["new_block_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "lifecycle patch contract"):
            self.module.validate_config(tampered)
        base = project_path(self.config["bindings"]["attempt31_worker"]["path"]).read_text(
            encoding="utf-8"
        )
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.patch_attempt31_source(
                base.replace(self.module.OLD_CAPTURE_BLOCK, "", 1), self.config
            )
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            self.module.patch_attempt31_source(
                base + self.module.OLD_CAPTURE_BLOCK, self.config
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
