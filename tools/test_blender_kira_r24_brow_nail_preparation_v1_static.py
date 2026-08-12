from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "Core" / "kira_r24_brow_nail_component_contract_v1.py"
ADAPTER_PATH = (
    ROOT
    / "tools"
    / "blender_avatar_blackproject_weight_constrained_nail_projection_v2.py"
)
WORKER_PATH = ROOT / "tools" / "blender_prepare_kira_r24_brow_nail_components_v1.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tree(path: Path) -> ast.Module:
    return ast.parse(source(path), filename=str(path))


def function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function absent: {name}")


def called_attribute_names(node: ast.AST) -> list[str]:
    result = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            result.append(child.func.attr)
    return result


class NoSaveScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker_source = source(WORKER_PATH)
        cls.worker_tree = tree(WORKER_PATH)
        cls.adapter_source = source(ADAPTER_PATH)
        cls.adapter_tree = tree(ADAPTER_PATH)

    def test_worker_and_adapter_are_syntax_valid(self) -> None:
        compile(self.worker_source, str(WORKER_PATH), "exec")
        compile(self.adapter_source, str(ADAPTER_PATH), "exec")

    def test_worker_and_adapter_have_no_blend_open_or_save_call(self) -> None:
        forbidden = {
            "open_mainfile",
            "save_as_mainfile",
            "save_mainfile",
            "save",
        }
        for parsed in (self.worker_tree, self.adapter_tree):
            self.assertTrue(forbidden.isdisjoint(called_attribute_names(parsed)))

    def test_worker_rejects_dirty_or_wrong_loaded_candidate(self) -> None:
        text = self.worker_source
        self.assertIn("bpy.data.filepath", text)
        self.assertIn("bpy.data.is_dirty", text)
        self.assertIn("sha256_file(candidate_path)", text)
        self.assertIn("validate_config(config, project_root=ROOT, verify_files=True)", text)

    def test_worker_never_names_a_candidate_blend_output(self) -> None:
        text = self.worker_source
        self.assertIn('"candidate_blend_saved": False', text)
        self.assertNotIn("OUTPUT_BLEND", text)


class ExactBrowTransplantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker_source = source(WORKER_PATH)
        cls.worker_tree = tree(WORKER_PATH)

    def test_only_fixed_attempt02_bindings_are_used(self) -> None:
        text = self.worker_source
        self.assertIn("BROW_SOURCE_PATH", text)
        self.assertIn("BROW_BINDINGS", text)
        self.assertIn("bpy.data.libraries.load", text)
        self.assertIn("third_brow_authored", text)

    def test_transplant_function_does_not_author_brow_mesh_geometry(self) -> None:
        node = function_node(self.worker_tree, "transplant_exact_attempt02_brows")
        text = ast.unparse(node)
        self.assertNotIn("meshes.new", text)
        self.assertNotIn("from_pydata", text)
        self.assertNotIn("bmesh", text)
        self.assertIn("mesh_geometry_digest", text)
        self.assertIn("weight_digest", text)

    def test_both_native_brow_hashes_are_verified_after_rebind(self) -> None:
        node = function_node(self.worker_tree, "transplant_exact_attempt02_brows")
        text = ast.unparse(node)
        self.assertGreaterEqual(text.count("mesh_geometry_digest"), 2)
        self.assertGreaterEqual(text.count("weight_digest"), 2)
        self.assertIn("native brow bone", text)


class NailMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter_source = source(ADAPTER_PATH)
        cls.worker_source = source(WORKER_PATH)

    def test_adapter_uses_repaired_positive_component_selector(self) -> None:
        self.assertIn("select_connected_weight_constrained_grid_v2", self.adapter_source)
        self.assertIn("selected_raw_component_id", self.adapter_source)
        self.assertIn("<= 0", self.adapter_source)
        self.assertIn("component_id_zero_rejected", self.adapter_source)

    def test_reference_center_and_displacement_gates_are_live(self) -> None:
        self.assertIn("reference_center_world", self.adapter_source)
        self.assertIn("MAXIMUM_REFERENCE_CENTER_ERROR_M", self.adapter_source)
        self.assertIn("validate_reference_bound_candidate", self.adapter_source)
        contract = source(CONTRACT_PATH)
        self.assertIn("MAXIMUM_REFERENCE_CENTER_ERROR_M = 0.0015", contract)
        self.assertIn("MAXIMUM_SAMPLE_DISPLACEMENT_M = 0.004", contract)

    def test_worker_requires_all_twenty_and_uses_v2_builder(self) -> None:
        self.assertIn("build_weight_constrained_nail_v2", self.worker_source)
        self.assertIn("len(inventory) != 20", self.worker_source)
        self.assertIn("len(built) != 20", self.worker_source)
        self.assertIn("Kira_R24_Natural_Nail", self.worker_source)

    def test_adapter_captures_full_modifier_stack(self) -> None:
        self.assertIn("modifier.bl_rna.properties", self.adapter_source)
        self.assertIn("modifier_stack_sha256", self.adapter_source)
        self.assertIn("full_modifier_stack_unchanged", self.adapter_source)


class PoseRenderAndSceneGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker_source = source(WORKER_PATH)
        cls.worker_tree = tree(WORKER_PATH)
        cls.contract_source = source(CONTRACT_PATH)

    def test_exact_candidate_scene_hash_is_required(self) -> None:
        self.assertIn("full_scene_state_sha256", self.contract_source)
        self.assertIn("candidate full scene state", self.worker_source)
        self.assertIn("protected full scene state changed", self.worker_source)

    def test_all_pose_contact_and_intersection_gates_are_invoked(self) -> None:
        text = self.worker_source
        self.assertIn("validate_pose_gate_matrix", text)
        self.assertIn("action_sha256", text)
        self.assertIn("exact_pair_record", text)
        self.assertIn("nail_pair_audit", text)
        self.assertIn("contact_gate_passed", text)
        self.assertIn("exact_body_nail_crossing_pair_count", text)

    def test_pose_validation_precedes_render_and_evidence(self) -> None:
        main = function_node(self.worker_tree, "main")
        lines: dict[str, int] = {}
        for node in ast.walk(main):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    lines.setdefault(node.func.id, node.lineno)
                elif isinstance(node.func, ast.Attribute):
                    lines.setdefault(node.func.attr, node.lineno)
        self.assertLess(lines["run_all_bound_pose_gates"], lines["render_after_pose_gates"])
        self.assertLess(lines["render_after_pose_gates"], lines["_exclusive_json"])

    def test_exact_eight_png_inventory_is_validated(self) -> None:
        text = self.worker_source
        self.assertIn("EXPECTED_RENDER_KEYS", text)
        self.assertIn("validate_render_inventory", text)
        self.assertIn("render_count", text)

    def test_transaction_is_explicitly_no_save(self) -> None:
        text = self.worker_source
        self.assertIn("validate_no_save_transaction", text)
        self.assertIn('"no_save_exit"', text)
        self.assertIn("ALL_GATES_PASSED_NO_BLEND_SAVED", text)


if __name__ == "__main__":
    unittest.main()
