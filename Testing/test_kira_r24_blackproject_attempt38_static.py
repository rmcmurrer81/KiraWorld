import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "RecoverySprint" / "continuation_20260808"
PREFLIGHT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
)
CONFIG = RUNTIME / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT38_CONFIG.json"
WORKER = ROOT / "tools" / "blender_diagnose_kira_r24_blackproject_candidate_attempt38.py"
A37_WORKER = ROOT / "tools" / "blender_diagnose_kira_r24_blackproject_candidate_attempt37.py"
A37_CONFIG = RUNTIME / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT37_CONFIG.json"
PROPOSAL = PREFLIGHT / "ATTEMPT_38_LAUNCH_TARGET_OWNERSHIP_PROPOSAL.md"
CHECKPOINT = PREFLIGHT / "ATTEMPT_38_STATIC_CHECKPOINT.md"
ATTEMPT_ROOT = PREFLIGHT.parent / "attempt_38"
STDOUT = RUNTIME / "attempt38_blender_stdout.log"
STDERR = RUNTIME / "attempt38_blender_stderr.log"
INTEGRITY = RUNTIME / "attempt38_external_pre_post_integrity.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Attempt38StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.a37_config = json.loads(A37_CONFIG.read_text(encoding="utf-8"))
        cls.worker_source = WORKER.read_text(encoding="utf-8")
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("attempt38_static", WORKER)
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load Attempt 38 worker")
        cls.worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.worker)
        cls.loaded = cls.worker.load_config(CONFIG)
        cls.verified = cls.worker.verify_overlay(cls.loaded)

    def test_01_artifact_hashes_compile_and_load(self) -> None:
        self.assertEqual(
            sha256(CONFIG),
            "88f70401e42b1cbdb607276ed7c1abe91dbf0bdc2f9634e7bccf6e867bd98556",
        )
        self.assertEqual(
            sha256(WORKER),
            "a9bd17db69fe7d98a37a6c66c9f2d3b0b23346827356fce7b51337dafc4288e1",
        )
        compile(self.worker_source, str(WORKER), "exec")
        self.assertEqual(self.loaded["attempt_id"], "attempt_38")

    def test_02_every_prior_binding_is_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, record["bytes"], label)
            self.assertEqual(sha256(path), record["sha256"], label)
        self.assertEqual(PROPOSAL.stat().st_size, self.config["proposal"]["bytes"])
        self.assertEqual(sha256(PROPOSAL), self.config["proposal"]["sha256"])

    def test_03_attempt37_failure_is_bound_as_launch_only(self) -> None:
        self.assertFalse(PREFLIGHT.parent.joinpath("attempt_37").exists())
        stderr = (RUNTIME / "attempt37_blender_stderr.log").read_bytes()
        decoded = stderr.decode(
            "utf-16" if stderr.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8",
            errors="replace",
        )
        self.assertIn("Attempt 37 runtime target already exists: stdout", decoded)
        self.assertNotIn("quality_refined_cdt_failed", decoded)

    def test_04_geometry_contract_is_exact_attempt37(self) -> None:
        for section in (
            "candidate_selection_patch",
            "nondegrading_repair",
            "unchanged_geometry_and_quality_contract",
        ):
            self.assertEqual(self.config[section], self.a37_config[section], section)
        attempt37 = self.verified["attempt37"]
        self.assertEqual(
            sha256_text(attempt37.ATTEMPT37_CANDIDATE_NEW),
            "a328eeb4e9d23982762b9b996f6f798248ffb7dce03cf676691aab024de13c39",
        )
        self.assertEqual(
            self.verified["derived_attempt15_sha256"],
            "d21bb31e6d0b8b02bf5a3c936bcff69f6a57d532919b231d589f56077ef99068",
        )

    def test_05_all_geometry_and_quality_gates_remain_closed(self) -> None:
        repair = self.config["nondegrading_repair"]
        self.assertEqual(repair["candidate_order"], ["circumcenter", "centroid"])
        self.assertFalse(repair["incenter_reachable"])
        self.assertFalse(repair["trial_mutates_accepted_seed_list"])
        self.assertEqual(repair["cdt_epsilon_m_unchanged"], 1e-12)
        self.assertEqual(repair["minimum_angle_gate_degrees_unchanged"], 12.0)
        self.assertEqual(repair["maximum_seed_count_unchanged"], 160)
        self.assertEqual(repair["maximum_quality_refinement_iterations_unchanged"], 192)
        contract = self.config["unchanged_geometry_and_quality_contract"]
        self.assertEqual(contract["selected_boundary_edge_count"], 40)
        self.assertEqual(
            contract["selected_candidate"],
            "targeted_complete_vertex_stars_2_6_20_28",
        )

    def test_06_worker_checks_only_its_output_root(self) -> None:
        validate_source = self.worker_source.split(
            "def validate_config", 1
        )[1].split("def verify_overlay", 1)[0]
        self.assertIn('project_path(str(output["root"]), must_exist=False).exists()', validate_source)
        self.assertNotIn('for key in ("stdout", "stderr", "external_integrity")', validate_source)
        self.assertNotIn("project_path(str(launch[key])", validate_source)
        self.assertIn("worker_writes_external_targets", validate_source)
        for token in ("STDOUT", "STDERR", "INTEGRITY"):
            self.assertNotIn(f"open({token}", self.worker_source)

    def test_07_wrapper_owns_targets_and_has_exact_lifecycle(self) -> None:
        text = self.checkpoint
        preflight = text.index("foreach ($fresh in @($output, $stdout, $stderr, $integrity))")
        log_create = text.index("foreach ($log in @($stdout, $stderr))", preflight)
        create_new = text.index("[System.IO.FileMode]::CreateNew", log_create)
        before = text.index("$before = Get-Attempt38Inventory", create_new)
        invoke = text.index("& $blender --background", before)
        finally_block = text.index("} finally {", invoke)
        integrity_create = text.index("[System.IO.FileMode]::CreateNew", finally_block)
        nonzero = text.index("if ($exitCode -ne 0)", integrity_create)
        self.assertLess(preflight, log_create)
        self.assertLess(log_create, before)
        self.assertLess(before, invoke)
        self.assertLess(invoke, finally_block)
        self.assertLess(finally_block, integrity_create)
        self.assertLess(integrity_create, nonzero)
        self.assertEqual(text.count("& $blender --background"), 1)

    def test_08_wrapper_integrity_closure_includes_static_package(self) -> None:
        for token in ("$config", "$worker", "$test", "$checkpoint"):
            self.assertIn(token, self.checkpoint)
        self.assertIn("Get-Attempt38Inventory", self.checkpoint)
        self.assertIn("pre_post_exact", self.checkpoint)
        self.assertIn("native_invocation_error", self.checkpoint)
        self.assertIn("even on a nonzero Blender exit", self.checkpoint)

    def test_09_writer_is_append_only_and_preserves_both_provenances(self) -> None:
        attempt37 = self.verified["attempt37"]
        a35 = (ROOT / self.config["bindings"]["attempt35_worker"]["path"]).read_text(
            encoding="utf-8"
        )
        derived = self.worker.patch_attempt35_source(a35, self.config, attempt37)
        self.assertEqual(
            sha256_text(derived),
            "30d503e2c1710445906a9faa734d80cda274768cc24f18fd51d234fc255dd6e8",
        )
        self.assertIn('result["attempt37_nondegrading_cdt_repair"]', derived)
        self.assertIn('result["attempt38_launch_target_ownership_repair"]', derived)
        self.assertIn('module._exclusive_write_once = attempt38_writer', derived)

    def test_10_static_state_has_no_attempt38_runtime_artifacts(self) -> None:
        self.assertFalse(ATTEMPT_ROOT.exists())
        self.assertFalse(STDOUT.exists())
        self.assertFalse(STDERR.exists())
        self.assertFalse(INTEGRITY.exists())
        truth = self.config["truth"]
        self.assertTrue(truth["attempt38_worker_prepared"])
        self.assertTrue(truth["attempt38_config_prepared"])
        self.assertTrue(truth["attempt38_static_tests_prepared"])
        for key in (
            "attempt38_blender_execution_performed",
            "attempt38_candidate_patch_executed_in_blender",
            "attempt38_trial_evidence_written",
            "attempt38_reconstruction_performed",
            "attempt38_body_mutation_performed",
            "attempt38_render_reached",
            "attempt38_blend_saved",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[key], key)

    def test_11_no_save_render_export_activation_or_retry(self) -> None:
        scope = self.config["scope"]
        for key in (
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "automatic_retry_allowed",
            "geometry_change_allowed",
        ):
            self.assertFalse(scope[key], key)
        self.assertNotIn("bpy.ops.wm.save", self.worker_source)
        self.assertNotIn("bpy.ops.render", self.worker_source)

    def test_12_checkpoint_records_static_only_stop_boundary(self) -> None:
        flat = " ".join(self.checkpoint.split())
        for phrase in (
            "STATIC_REPAIR_PREPARED_NOT_RUN",
            "Blender was not launched",
            "No Attempt 38 runtime directory",
            "exact Attempt 37 candidate block",
            "Do not launch Attempt 38",
            "do not retry automatically",
        ):
            self.assertIn(phrase, flat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
