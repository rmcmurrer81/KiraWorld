from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import sys
import types
import unittest

from tools import blender_diagnose_kira_r24_blackproject_candidate_attempt31 as attempt31


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "attempt_31"
)
WORKER = ROOT / "tools" / "blender_diagnose_kira_r24_blackproject_candidate_attempt31.py"
PROPOSAL = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
    / "ATTEMPT_31_SMALLEST_EXISTING_SOURCE_CANDIDATE_PROPOSAL.md"
)
CHECKPOINT = PROPOSAL.with_name("ATTEMPT_31_STATIC_CHECKPOINT.md")
STDOUT = ROOT / "RecoverySprint" / "continuation_20260808" / "attempt31_blender_stdout.log"
STDERR = ROOT / "RecoverySprint" / "continuation_20260808" / "attempt31_blender_stderr.log"
EXTERNAL_INTEGRITY = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "attempt31_external_pre_post_integrity.json"
)


class R24BlackProjectAttempt31StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = attempt31.load_config()
        cls.verified = attempt31.verify_bindings(cls.config)
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        prior_records = list(cls.verified["nested_attempt28_attempt29_records"].values())
        prior_records += [
            cls.verified["records"][name]
            for name in cls.config["preserved_attempt30_package"]["binding_names"]
        ]
        cls.prior_paths = {
            ROOT / record["path"] for record in prior_records
        }
        cls.prior_bytes = {path: path.read_bytes() for path in cls.prior_paths}

    @classmethod
    def tearDownClass(cls) -> None:
        for path, payload in cls.prior_bytes.items():
            if path.read_bytes() != payload:
                raise AssertionError(f"preserved Attempt 28-30 artifact changed: {path}")

    def test_static_import_is_blender_free_and_worker_compiles(self) -> None:
        top_imports = set()
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                top_imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.add(node.module.split(".")[0])
        self.assertTrue({"argparse", "hashlib", "json", "pathlib"}.issubset(top_imports))
        self.assertTrue({"bpy", "bmesh", "numpy", "mathutils"}.isdisjoint(top_imports))
        compile(self.source, str(WORKER), "exec")

    def test_attempt28_and_attempt29_nested_packages_are_exact(self) -> None:
        nested = self.verified["nested_attempt28_attempt29_records"]
        self.assertEqual(len(nested), 20)
        self.assertEqual(
            self.config["nested_preserved_attempt28_package"]["file_count"], 9
        )
        self.assertEqual(
            self.config["nested_preserved_attempt28_package"]["total_bytes"], 72757
        )
        self.assertEqual(
            self.config["nested_preserved_attempt29_package"]["file_count"], 10
        )
        self.assertEqual(
            self.config["nested_preserved_attempt29_package"]["total_bytes"], 104277
        )
        for record in nested.values():
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(attempt31.sha256_file(path), record["sha256"])

    def test_attempt30_static_and_live_package_is_exact(self) -> None:
        package = self.config["preserved_attempt30_package"]
        records = self.verified["records"]
        rows = [records[name] for name in package["binding_names"]]
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(row["bytes"] for row in rows), 685270)
        self.assertEqual(records["attempt30_diagnostic"]["bytes"], 627714)
        self.assertEqual(
            records["attempt30_diagnostic"]["sha256"],
            "d84c44d792cc4726507ff8a856ed67444e0918fb5c1a7e025a18502e6830c506",
        )
        self.assertEqual(records["attempt30_stdout"]["bytes"], 261)
        self.assertEqual(records["attempt30_stderr"]["bytes"], 1157)

    def test_exact_transitive_provider_files_are_bound_and_rehashed(self) -> None:
        records = self.verified["records"]
        expected = {
            "exact_intersection_helper": (
                20087,
                "75c9f9633686776b72ec7bd83362521daae3d9f9497106b0491b8f85490c3ad1",
            ),
            "r21_graft_helper": (
                25054,
                "88854dd51faf47286e2c7e6f7d0c594583150eca2045121667f25543e692106b",
            ),
            "r20_pelvis_helper": (
                202035,
                "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a",
            ),
            "r20_curvilinear_contract": (
                56218,
                "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d",
            ),
            "a09_midpoint_helper": (
                74705,
                "8fcd1c39b9f375f5a48d0aefd761222fe0e65b2a7efe491e6d28f7e794aa49d7",
            ),
            "a08_direct_subdivision_helper": (
                83198,
                "6a75233d53fabebb9afc61e46184d3dbe5718a648317a93f8b2b2792fab7ab1c",
            ),
        }
        for name, (size, digest) in expected.items():
            self.assertEqual(records[name]["bytes"], size)
            self.assertEqual(records[name]["sha256"], digest)
            path = ROOT / records[name]["path"]
            self.assertEqual(path.stat().st_size, size)
            self.assertEqual(attempt31.sha256_file(path), digest)

    def test_attempt30_runtime_truth_is_no_repair_no_save(self) -> None:
        path = ROOT / self.verified["records"]["attempt30_diagnostic"]["path"]
        diagnostic = json.loads(path.read_text(encoding="utf-8"))
        contract = attempt31.verify_candidate_contract(self.config, diagnostic)
        self.assertEqual(contract["eligible_candidate_count"], 7)
        truth = diagnostic["truth"]
        for name in (
            "replacement_boundary_repair_applied",
            "triangulation_performed",
            "mesh_mutated",
            "body_mutated",
            "render_reached",
            "blend_saved",
            "runtime_changed",
            "necessary_candidate_is_sufficient_repair_proof",
        ):
            self.assertFalse(truth[name])

    def test_complete_seven_candidate_manifest_and_selection_are_bound(self) -> None:
        rows = self.config["selection_contract"]["eligible_candidates"]
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows, sorted(rows, key=attempt31._eligible_sort_key))
        self.assertEqual(
            [row["face_count"] for row in rows], [104, 105, 106, 106, 107, 108, 110]
        )
        self.assertTrue(all(row["global_seam_relation"] == "DISJOINT" for row in rows))
        self.assertEqual(rows[0]["candidate"], self.config["selected_candidate"]["candidate"])
        self.assertFalse(
            self.config["selection_contract"]
            ["necessary_checks_are_sufficient_reconstruction_proof"]
        )

    def test_selected_candidate_exact_topology_and_measurements(self) -> None:
        selected = self.config["selected_candidate"]
        self.assertEqual(selected["capture_source_indices"], [2, 6, 20, 28])
        self.assertEqual(selected["source_mesh_vertex_indices"], [90, 418, 407, 91])
        self.assertEqual(len(selected["face_indices"]), 104)
        self.assertEqual(
            attempt31.canonical_sha256(selected["face_indices"]),
            "099d7cb72f1b179aa1b9e352ff7fda76b6b467014ef305cf226a8cd9566ab2c8",
        )
        self.assertEqual(len(selected["boundary_cycle_mesh_vertex_indices"]), 40)
        self.assertEqual(selected["vertex_count"], 73)
        self.assertEqual(selected["edge_count"], 176)
        self.assertEqual(selected["interior_vertex_count"], 33)
        self.assertEqual(selected["minimum_boundary_angle_degrees"], 13.24909246109987)
        self.assertEqual(selected["maximum_chart_deviation_m"], 0.0010360884480178356)
        self.assertEqual(selected["global_seam_relation"], "DISJOINT")

    def test_selected_face_list_is_exact_base_plus_complete_vertex_stars(self) -> None:
        domain_path = ROOT / self.verified["records"]["repair_domain_diagnostic"]["path"]
        domain = json.loads(domain_path.read_text(encoding="utf-8"))
        base = set(
            domain["smallest_qualified_replacement_domain"]["face_indices"]
        )
        selected = self.config["selected_candidate"]
        complete = sorted(base.union(selected["added_complete_vertex_star_face_indices"]))
        self.assertEqual(complete, selected["face_indices"])
        self.assertEqual(len(complete), 104)

    def test_scope_is_later_run_only_and_has_no_render_save_or_activation(self) -> None:
        scope = self.config["scope"]
        self.assertTrue(scope["later_reviewed_blender_launch_required"])
        self.assertTrue(scope["triangulation_allowed_only_during_later_run"])
        self.assertTrue(scope["reconstruction_allowed_only_during_later_run"])
        for name in (
            "source_file_mutation_allowed",
            "prior_evidence_mutation_allowed",
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "boundary_or_global_seam_movement_allowed",
            "quality_gate_reduction_allowed",
            "automatic_alternate_candidate_retry_allowed",
        ):
            self.assertFalse(scope[name])
        self.assertFalse(OUTPUT.exists())

    def test_all_geometry_intersection_and_preservation_gates_remain(self) -> None:
        hard = self.config["unchanged_hard_gates"]
        self.assertEqual(hard["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(hard["minimum_new_triangle_world_area_m2"], 1.0e-10)
        self.assertEqual(hard["maximum_new_interior_vertex_count"], 160)
        self.assertEqual(hard["maximum_quality_refinement_iterations"], 192)
        self.assertEqual(hard["selected_domain_boundary_edge_count"], 40)
        self.assertEqual(hard["global_seam_vertex_count"], 34)
        self.assertEqual(hard["global_seam_coordinate_delta_m"], 0.0)
        self.assertEqual(hard["standalone_patch_exact_genuine_intersections"], 0)
        self.assertEqual(hard["joined_patch_related_exact_genuine_intersections"], 0)
        self.assertEqual(hard["new_whole_body_exact_genuine_intersections"], 0)
        self.assertEqual(hard["preserved_inherited_nonpatch_exact_genuine_intersections"], 29)
        for name in (
            "patch_original_vertex_and_face_id_tags_unique_complete",
            "patch_exact_new_vertex_and_face_counts",
            "patch_outside_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing",
            "patch_temporary_id_layers_removed_before_graft",
            "body_nonpatch_original_vertex_and_face_id_tags_unique_complete",
            "body_nonpatch_exact_float_hex_coordinates_ordered_loops_all_uv_layers_weights_material_smoothing",
            "body_exact_new_vertex_and_face_counts",
            "body_temporary_id_layers_removed_before_final_audit",
            "body_transform_parent_modifier_order_full_settings_vertex_group_inventory_shape_keys_animation_material_slot_order_link_datablock_identity_exact",
            "rig_object_armature_settings_bones_pose_constraints_and_animation_exact",
            "global_action_inventory_exact",
            "protected_original_nonbody_nonrig_object_state_and_mesh_coordinate_topology_uv_material_smoothing_exact",
        ):
            self.assertTrue(hard[name])
        self.assertFalse(hard["save_allowed_without_owner_visual_acceptance"])

    def test_worker_has_no_render_or_blend_save_call(self) -> None:
        forbidden = (
            "bpy.ops.wm.save",
            "save_as_mainfile",
            "save_mainfile",
            "bpy.ops.render",
            "render_paired_evidence(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)
        self.assertIn("bpy.ops.wm.open_mainfile", self.source)
        self.assertIn("provider.reconstruct_local_domain", self.source)
        self.assertIn("provider.r21.join_and_weld", self.source)
        self.assertIn('with path.open("x"', self.source)
        self.assertNotIn("temporary.replace(", self.source)

    def test_worker_sequence_is_fail_closed_before_graft_and_evidence(self) -> None:
        self.assertLess(
            self.source.index("repair = provider.reconstruct_local_domain"),
            self.source.index("provider.r21.remove_old_patch"),
        )
        self.assertLess(
            self.source.index("if not all(structural_gates.values())"),
            self.source.index("report = {"),
        )
        main_source = self.source[self.source.index("def main() -> None:") :]
        self.assertLess(main_source.index("verify_bindings(config)"), main_source.index("run_blender_diagnostic"))

    def test_worker_verifies_imported_files_before_source_open(self) -> None:
        runtime = self.source[self.source.index("def run_blender_diagnostic") :]
        open_index = runtime.index("bpy.ops.wm.open_mainfile")
        provider_verify_index = runtime.index("provider.verify_inputs")
        output_index = runtime.index("output = project_output_path")
        attempt15_config_read_index = runtime.index("attempt15_config = json.loads")
        for token in (
            'records["attempt15_worker"]',
            'records["r21_graft_helper"]',
            'records["r20_pelvis_helper"]',
            'records["r20_curvilinear_contract"]',
            "provider.exact_nonadjacent_intersection_report",
            "provider.r21.exact_nonadjacent_intersection_report",
            "provider.r21.r20.exact_intersections",
            'records["exact_intersection_helper"]',
            "provider.a09,",
            'records["a09_midpoint_helper"]',
            "provider.a09.a08,",
            'records["a08_direct_subdivision_helper"]',
            "provider.a09.a08.exact_intersections",
        ):
            token_index = runtime.index(token)
            self.assertLess(token_index, attempt15_config_read_index)
            self.assertLess(token_index, provider_verify_index)
            self.assertLess(token_index, output_index)
            self.assertLess(token_index, open_index)
        self.assertEqual(runtime[:attempt15_config_read_index].count("_verify_callable_provider_file("), 2)
        self.assertGreaterEqual(
            runtime[:attempt15_config_read_index].count("_verify_imported_module_file("),
            8,
        )
        self.assertIn("IMPORTED_NOT_INVOKED", runtime[:attempt15_config_read_index])

    def test_first_attempt15_config_read_follows_every_alias_check_globally(self) -> None:
        verify_start = self.source.index("def verify_bindings")
        verify_end = self.source.index("\ndef _verify_imported_module_file", verify_start)
        verify_source = self.source[verify_start:verify_end]
        self.assertNotIn("attempt15_config = json.loads", verify_source)
        self.assertNotIn(
            'project_existing_path(records["attempt15_config"]["path"]).read_text',
            verify_source,
        )

        read_token = "attempt15_config = json.loads"
        self.assertEqual(self.source.count(read_token), 1)
        first_read = self.source.index(read_token)
        run_start = self.source.index("def run_blender_diagnostic")
        runtime_before_read = self.source[run_start:first_read]
        for token in (
            "provider.exact_nonadjacent_intersection_report",
            "provider.r21.exact_nonadjacent_intersection_report",
            "provider.r21.r20.exact_intersections",
            "provider.a09,",
            "provider.a09.a08,",
            "provider.a09.a08.exact_intersections",
        ):
            self.assertIn(token, runtime_before_read)
        self.assertEqual(runtime_before_read.count("_verify_callable_provider_file("), 2)
        self.assertGreaterEqual(runtime_before_read.count("_verify_imported_module_file("), 8)
        self.assertLess(first_read, self.source.index("provider.verify_inputs", first_read))
        self.assertLess(first_read, self.source.index("output = project_output_path", first_read))
        self.assertLess(first_read, self.source.index("bpy.ops.wm.open_mainfile", first_read))

    def test_provider_import_alias_manifest_and_tamper_cases_fail_closed(self) -> None:
        contract = self.config["provider_import_contract"]
        callable_rows = contract["callable_aliases"]
        module_rows = contract["module_aliases"]
        self.assertEqual(
            [row["reference"] for row in callable_rows],
            [
                "provider.exact_nonadjacent_intersection_report",
                "provider.r21.exact_nonadjacent_intersection_report",
            ],
        )
        self.assertEqual(
            [row["reference"] for row in module_rows],
            [
                "provider.r21.r20.exact_intersections",
                "provider.a09",
                "provider.a09.a08",
                "provider.a09.a08.exact_intersections",
            ],
        )
        self.assertEqual(module_rows[1]["status"], "IMPORTED_NOT_INVOKED")
        self.assertEqual(module_rows[2]["status"], "IMPORTED_NOT_INVOKED")
        self.assertEqual(module_rows[3]["status"], "IMPORTED_NOT_INVOKED")
        for row in callable_rows + module_rows:
            name = row["binding"]
            changed = copy.deepcopy(self.config)
            changed["bindings"][name]["sha256"] = "0" * 64
            with self.assertRaisesRegex(RuntimeError, "provider import binding"):
                attempt31.validate_config(changed)

    def test_callable_owner_resolution_rejects_missing_or_rebound_module(self) -> None:
        module_name = "_attempt31_static_callable_owner_probe"
        module = types.ModuleType(module_name)

        def exact_probe() -> None:
            return None

        original_module = exact_probe.__module__
        exact_probe.__module__ = module_name
        module.exact_probe = exact_probe
        previous = sys.modules.get(module_name)
        try:
            sys.modules[module_name] = module
            self.assertIs(
                attempt31._module_for_callable(exact_probe, "static probe"), module
            )
            module.exact_probe = lambda: None
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                attempt31._module_for_callable(exact_probe, "static probe")
            del sys.modules[module_name]
            with self.assertRaisesRegex(RuntimeError, "module is absent"):
                attempt31._module_for_callable(exact_probe, "static probe")
            with self.assertRaisesRegex(RuntimeError, "not callable"):
                attempt31._module_for_callable(None, "static probe")
        finally:
            exact_probe.__module__ = original_module
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous

    def test_exact_tagged_preservation_replaces_rounded_snapshots(self) -> None:
        required = (
            "PATCH_VERTEX_TAG",
            "PATCH_FACE_TAG",
            "BODY_VERTEX_TAG",
            "BODY_FACE_TAG",
            "_begin_tagged_preservation(",
            "_finish_tagged_preservation(",
            "float(value).hex()",
            '"ordered_loops"',
            '"select_edge"',
            '"pin_uv"',
            '"weights"',
            '"material_index"',
            '"smooth"',
            '"no_duplicate_or_missing_old_vertex_or_face_tags"',
            '"exact_new_vertex_and_face_counts"',
        )
        for token in required:
            self.assertIn(token, self.source)
        for forbidden in (
            "provider.r21.clear_pose",
            "provider.r21.nonpatch_snapshot",
            "provider.r21.object_digest",
            "provider.inherited_pair_signature",
            "_outside_snapshot",
            "_outside_preserved",
            "round(",
        ):
            self.assertNotIn(forbidden, self.source)
        self.assertLess(
            self.source.index("patch_preservation = _finish_tagged_preservation"),
            self.source.index("body_tag_snapshot = _tag_body_for_preservation"),
        )
        self.assertLess(
            self.source.index("body_tag_snapshot = _tag_body_for_preservation"),
            self.source.index("provider.r21.remove_old_patch"),
        )
        self.assertLess(
            self.source.index("body_preservation = _finish_tagged_preservation"),
            self.source.index("final_exact = provider.r21.exact_audit"),
        )

    def test_body_rig_action_material_and_narrow_protected_contracts_are_exact(self) -> None:
        required = (
            "_object_contract_snapshot(body)",
            "_rig_contract_snapshot(rig)",
            "_action_inventory()",
            "_protected_object_snapshot(body, rig)",
            '"matrix_world"',
            '"matrix_parent_inverse"',
            '"vertex_groups"',
            '"modifiers"',
            '"material_slots"',
            '"shape_keys"',
            '"bone_collections"',
            '"pose_bones"',
            '"constraints"',
            '"global_action_inventory_exact"',
        )
        for token in required:
            self.assertIn(token, self.source)
        scope = self.config["preservation_contract"]["protected_object_claim_scope"]
        self.assertIn("nonbody nonrig", scope)
        self.assertIn("does not claim complete internal state", scope)

    def test_tampering_candidate_scope_gate_or_truth_fails_closed(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["selected_candidate"]["face_indices"][0] += 1
        with self.assertRaisesRegex(RuntimeError, "selected candidate"):
            attempt31.validate_config(changed)
        changed = copy.deepcopy(self.config)
        changed["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"] = 11.999
        with self.assertRaisesRegex(RuntimeError, "hard gate"):
            attempt31.validate_config(changed)
        changed = copy.deepcopy(self.config)
        changed["scope"]["blend_save_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            attempt31.validate_config(changed)
        changed = copy.deepcopy(self.config)
        changed["truth"]["body_repair_proven"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaims"):
            attempt31.validate_config(changed)

    def test_proposal_records_fail_closed_later_launch_block_and_no_current_run(self) -> None:
        proposal_path = ROOT / self.config["proposal"]["path"]
        proposal = proposal_path.read_text(encoding="utf-8")
        self.assertIn("STATIC ONLY", proposal.upper().replace("-", " "))
        self.assertIn(
            "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe",
            proposal,
        )
        self.assertIn(
            "tools\\blender_diagnose_kira_r24_blackproject_candidate_attempt31.py",
            proposal,
        )
        self.assertIn(
            "RecoverySprint\\continuation_20260808\\R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT31_CONFIG.json",
            proposal,
        )
        self.assertIn("--disable-autoexec", proposal)
        self.assertIn("--python-exit-code 1", proposal)
        self.assertIn("1>> $stdout 2>> $stderr", proposal)
        self.assertIn("Get-Attempt31Inventory", proposal)
        self.assertIn("$before =", proposal)
        self.assertIn("$after =", proposal)
        self.assertIn("pre_post_exact", proposal)
        self.assertIn("Attempt 31 refuses to overwrite", proposal)
        self.assertIn("[System.IO.FileMode]::CreateNew", proposal)
        self.assertIn("attempt31_external_pre_post_integrity.json", proposal)
        self.assertIn("sufficient reconstruction proof", proposal.lower())
        self.assertIn("necessary eligibility is not", proposal.lower())
        self.assertFalse(OUTPUT.exists())
        self.assertFalse(STDOUT.exists())
        self.assertFalse(STDERR.exists())
        self.assertFalse(EXTERNAL_INTEGRITY.exists())


if __name__ == "__main__":
    unittest.main()
