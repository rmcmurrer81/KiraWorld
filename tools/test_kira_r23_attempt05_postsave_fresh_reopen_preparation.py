#!/usr/bin/env python3
"""Warning-fatal, no-Blender tests for the bound Attempt05 reopen package."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_preparation"
)
CONFIG_PATH = PACKAGE / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_CONFIG.json"
)
PREFLIGHT_PATH = ROOT / "tools/kira_r23_attempt05_postsave_fresh_reopen_preflight.py"
WORKER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"
TEMPLATE_PATH = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_postsave_fresh_reopen_verifier_preparation/"
    "KIRA_R23_POSTSAVE_VERIFIER_CONFIG_TEMPLATE.json"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt05PostsavePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.evidence_path = ROOT / cls.config["build_evidence_binding"]["path"]
        cls.evidence = json.loads(cls.evidence_path.read_text(encoding="utf-8"))
        cls.candidate_path = ROOT / cls.config["candidate_binding"]["path"]
        cls.preflight = load(PREFLIGHT_PATH, "_attempt05_reopen_preflight_test")
        cls.worker = load(WORKER_PATH, "_attempt05_reopen_worker_test")

    def test_01_exact_candidate_and_evidence_bindings(self) -> None:
        self.assertEqual(self.config["candidate_binding"]["bytes"], 82564331)
        self.assertEqual(
            self.config["candidate_binding"]["sha256"],
            "394cba65c2ec1fefa22981079c3b53486a4dfd6037e89caf1504990a7cbbce4e",
        )
        self.assertEqual(self.config["build_evidence_binding"]["bytes"], 67468)
        self.assertEqual(
            self.config["build_evidence_binding"]["sha256"],
            "f74268971f83a89e0967799dbb9b032dd6259ab498440337491942fdba832dd8",
        )

    def test_02_zstd_magic_is_preliminary_only(self) -> None:
        self.assertEqual(self.candidate_path.read_bytes()[:4], bytes.fromhex("28b52ffd"))
        result = self.preflight.candidate_container_preflight(
            self.config, self.candidate_path
        )
        self.assertFalse(result["blend_validity_established"])
        self.assertTrue(result["fresh_blender_reopen_still_required"])

    def test_03_author_evidence_binds_exact_candidate(self) -> None:
        self.assertEqual(self.evidence["candidate"], {
            **self.evidence["candidate"],
            "path": self.config["candidate_binding"]["path"],
            "bytes": self.config["candidate_binding"]["bytes"],
            "sha256": self.config["candidate_binding"]["sha256"],
        })

    def test_04_candidate_protection_flags(self) -> None:
        candidate = self.evidence["candidate"]
        self.assertTrue(candidate["inactive"])
        self.assertTrue(candidate["unassigned"])
        self.assertTrue(candidate["unpublished"])
        self.assertFalse(candidate["runtime_eligible"])
        self.assertFalse(candidate["owner_approved"])

    def test_05_forbidden_author_operations_remain_false(self) -> None:
        operations = self.evidence["operations"]
        for key in (
            "source_blend_written", "render_performed", "export_performed",
            "runtime_mutation_performed", "candidate_activated",
        ):
            self.assertFalse(operations[key], key)

    def test_06_fresh_reopen_requires_explicit_flag(self) -> None:
        with self.assertRaises(self.worker.VerificationError):
            self.worker.validate_bound_contract(self.config, explicit_execution=False)

    def test_07_bound_contract_accepts_only_fresh_absent_outputs(self) -> None:
        paths = self.worker.validate_bound_contract(self.config, explicit_execution=True)
        self.assertFalse(paths["evidence_dir"].exists())
        self.assertFalse(paths["render_dir"].exists())
        paths["render_dir"].relative_to(paths["evidence_dir"])

    def test_08_topology_expectations_are_evidence_derived(self) -> None:
        result = self.preflight.verify_topology_expectation_binding(
            self.config, self.evidence
        )
        self.assertTrue(all(result["checks"].values()))
        self.assertTrue(all(result["boundary_semantics_checks"].values()))

    def test_09_inherited_boundaries_preserved_exactly(self) -> None:
        stable = self.evidence["topology"]["stable_boundary_preservation"]
        self.assertEqual((stable["source_count"], stable["final_count"]), (330, 330))
        self.assertEqual(stable["source_sha256"], stable["final_sha256"])
        self.assertEqual((stable["new_count"], stable["missing_count"]), (0, 0))

    def test_10_patch_interface_is_not_misclassified_as_whole_boundary(self) -> None:
        semantics = self.config["boundary_semantics_contract"]
        patch = self.evidence["topology"]["replacement_patch"]
        self.assertEqual(patch["boundary_cycle_lengths"], [91])
        self.assertTrue(
            semantics["replacement_patch_subset_interface_is_not_a_whole_body_open_boundary"]
        )
        self.assertFalse(
            semantics["rejected_pelvic_patch_seam_as_new_whole_body_boundary_allowed"]
        )

    def test_11_no_unsupported_anatomical_boundary_claim(self) -> None:
        self.assertTrue(
            self.config["boundary_semantics_contract"]
            ["inherited_boundaries_may_correspond_to_preexisting_body_openings_but_are_not_individually_anatomically_classified_by_this_package"]
        )

    def test_12_zero_invalid_edge_classes(self) -> None:
        topology = self.evidence["topology"]
        self.assertEqual(topology["greater_than_two_face_nonmanifold"]["final_count"], 0)
        self.assertEqual(topology["loose_edges"]["final_count"], 0)
        self.assertEqual(topology["duplicate_mesh_edge_group_count"], 0)

    def test_13_continuity_and_intersection_thresholds_not_weakened(self) -> None:
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(self.config["continuity_thresholds"], template["continuity_thresholds"])
        thresholds = self.config["continuity_thresholds"]
        self.assertEqual(thresholds["maximum_new_exact_intersection_pairs_per_pose"], 0)
        self.assertEqual(thresholds["maximum_patch_involving_exact_intersection_pairs"], 0)
        self.assertEqual(thresholds["maximum_seam_position_error_m"], 1e-8)
        self.assertEqual(thresholds["maximum_seam_weight_error"], 1e-8)

    def test_14_machine_gates_recheck_seam_and_intersections(self) -> None:
        gates = set(self.config["machine_gates"])
        required = {
            "zero_patch_involving_exact_intersection_pairs",
            "zero_new_exact_intersection_face_pairs_in_each_required_pose",
            "seam_position_continuity", "seam_normal_continuity",
            "seam_tangent_continuity", "seam_uv_continuity",
            "seam_and_patch_native_weight_continuity",
        }
        self.assertTrue(required.issubset(gates))

    def test_15_source_and_candidate_are_immutable(self) -> None:
        contract = self.config["source_candidate_immutability_contract"]
        self.assertTrue(contract["source_and_candidate_open_read_only"])
        self.assertTrue(contract["source_and_candidate_hash_before_and_after"])
        self.assertTrue(contract["candidate_save_forbidden"])
        self.assertTrue(contract["source_save_forbidden"])
        self.assertTrue(contract["export_forbidden"])
        self.assertTrue(contract["activation_assignment_publication_forbidden"])

    def test_16_preflight_cannot_start_blender(self) -> None:
        source = PREFLIGHT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("subprocess.run", source)

    def test_17_future_command_is_exact_fresh_factory_startup(self) -> None:
        command = self.preflight.future_command(self.config)
        self.assertEqual(command[1:4], ["--background", "--factory-startup", "--disable-autoexec"])
        self.assertIn("--execute-fresh-reopen", command)
        self.assertNotIn(self.config["candidate_binding"]["path"], command)

    def test_18_manifest_closes_package_without_self_reference(self) -> None:
        manifest = json.loads((PACKAGE / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        paths = [row["path"] for row in manifest["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertNotIn(
            "RecoverySprint/continuation_20260803/"
            "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_preparation/"
            "PACKAGE_MANIFEST.json",
            paths,
        )
        for row in manifest["artifacts"]:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(self.preflight.sha256_file(path), row["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
