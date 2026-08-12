"""Pure/static tests for the profiled Kira post-build auditors.

These tests never import bpy, invoke Blender, open a candidate, render, save,
export, activate, or create evidence beneath the real project audit root.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_profiled_kira_candidate_audit_contract import (
    AUDIT_ROOT,
    GLB_EVIDENCE_NAME,
    MAIN_EVIDENCE_NAME,
    evaluate_glb_append_preflight,
    evaluate_postbuild_audit_preflight,
    inventory_glb_container,
    sha256_file,
    verify_inputs_unchanged,
)


MAIN_SCRIPT = PROJECT_ROOT / "tools/blender_audit_profiled_kira_adult_candidate.py"
GLB_SCRIPT = PROJECT_ROOT / "tools/blender_fresh_import_profiled_kira_private_glb.py"
CONTRACT = PROJECT_ROOT / "Core/avatar_profiled_kira_candidate_audit_contract.py"
DOC = PROJECT_ROOT / "System/Docs/AVATAR_BUILDER_PROFILED_KIRA_POSTBUILD_AUDIT_20260801.md"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AuditFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.candidate_id = "kira_profiled_adult_candidate_fixture_20260801"
        self.candidate_dir = root / "Avatar/private_owner_review" / self.candidate_id
        self.candidate_dir.mkdir(parents=True)
        self.blend = self.candidate_dir / f"{self.candidate_id}.blend"
        self.blend.write_bytes(b"exact-private-blend-fixture")
        self.build = self.candidate_dir / "BUILD_EVIDENCE.json"
        self.build.write_text(
            json.dumps({"candidate_id": self.candidate_id}), encoding="utf-8"
        )
        self.glb = self.candidate_dir / f"{self.candidate_id}.private.glb"
        self.glb.write_bytes(b"exact-private-glb-fixture")
        self.output_relative = AUDIT_ROOT / f"{self.candidate_id}__audit_attempt_01"

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def preflight(self, **overrides: object) -> dict:
        values: dict[str, object] = {
            "blend_path": self.relative(self.blend),
            "blend_sha256": sha256_file(self.blend),
            "build_evidence_sha256": sha256_file(self.build),
            "output_dir": self.output_relative,
            "optional_glb_path": self.relative(self.glb),
            "optional_glb_sha256": sha256_file(self.glb),
        }
        values.update(overrides)
        return evaluate_postbuild_audit_preflight(self.root, **values)


class ProfiledKiraAuditContractTests(unittest.TestCase):
    def test_pure_glb_container_inventory_reports_weight_morph_channels(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.glb"
            payload = {
                "asset": {"version": "2.0"},
                "scene": 0,
                "scenes": [{"nodes": [0]}],
                "nodes": [{"name": "ResponsiveHair", "mesh": 0}],
                "meshes": [
                    {
                        "name": "ResponsiveHairMesh",
                        "weights": [0.0],
                        "primitives": [{"attributes": {}, "targets": [{"POSITION": 0}]}],
                    }
                ],
                "skins": [{"name": "OfficialRig", "joints": []}],
                "materials": [{"name": "BlackHair"}],
                "accessors": [{"count": 2, "type": "SCALAR"}],
                "animations": [
                    {
                        "name": "HairResponse",
                        "samplers": [{"input": 0, "output": 0}],
                        "channels": [
                            {"sampler": 0, "target": {"node": 0, "path": "weights"}}
                        ],
                    }
                ],
            }
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            encoded += b" " * ((-len(encoded)) % 4)
            total = 12 + 8 + len(encoded)
            path.write_bytes(
                struct.pack("<4sII", b"glTF", 2, total)
                + struct.pack("<II", len(encoded), 0x4E4F534A)
                + encoded
            )
            report = inventory_glb_container(path)
            self.assertEqual(report["node_count"], 1)
            self.assertEqual(report["mesh_count"], 1)
            self.assertEqual(report["skin_count"], 1)
            self.assertEqual(report["material_count"], 1)
            self.assertEqual(report["animation_count"], 1)
            self.assertEqual(report["weight_channel_count"], 1)
            self.assertEqual(report["weight_channels_without_declared_morph_targets"], 0)
            self.assertTrue(
                report["weight_animation_channels"][0][
                    "weight_channel_has_declared_morph_targets"
                ]
            )
            self.assertFalse(report["fresh_import_survival_proven"])

    def test_preflight_binds_exact_inputs_and_performs_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = AuditFixture(Path(raw))
            report = fixture.preflight()
            self.assertTrue(report["ready"], report["blockers"])
            self.assertEqual(report["status"], "READY_FOR_FRESH_PROCESS_READ_ONLY_AUDIT")
            self.assertEqual(report["resolved"]["candidate_id"], fixture.candidate_id)
            self.assertEqual(report["resolved"]["output_directory"], fixture.output_relative.as_posix())
            self.assertFalse((fixture.root / fixture.output_relative).exists())
            self.assertFalse(report["candidate_mutation_allowed"])
            self.assertFalse(report["render_allowed"])
            self.assertFalse(report["save_allowed"])
            self.assertFalse(report["export_allowed"])
            self.assertFalse(report["activation_allowed"])

    def test_wrong_hash_wrong_glb_pair_and_existing_output_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = AuditFixture(Path(raw))
            wrong_hash = fixture.preflight(blend_sha256="0" * 64)
            self.assertFalse(wrong_hash["ready"])
            self.assertIn("candidate_blend_sha256_mismatch", wrong_hash["blockers"])
            half_glb = fixture.preflight(optional_glb_sha256=None)
            self.assertFalse(half_glb["ready"])
            self.assertIn(
                "optional_glb_path_and_sha256_required_together", half_glb["blockers"]
            )
            (fixture.root / fixture.output_relative).mkdir(parents=True)
            existing = fixture.preflight()
            self.assertFalse(existing["ready"])
            self.assertIn("audit_output_exists_refuse_overwrite", existing["blockers"])

    def test_candidate_and_output_path_confinement_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = AuditFixture(Path(raw))
            escaped = fixture.preflight(output_dir=Path("../escaped_attempt"))
            self.assertFalse(escaped["ready"])
            self.assertIn("audit_output_path_unsafe", escaped["blockers"])
            wrong_root = fixture.preflight(
                output_dir=Path("Temp") / f"{fixture.candidate_id}__audit_attempt_01"
            )
            self.assertFalse(wrong_root["ready"])
            self.assertIn(
                "audit_output_not_direct_versioned_audit_child", wrong_root["blockers"]
            )

    def test_second_stage_requires_exact_main_evidence_and_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = AuditFixture(Path(raw))
            output = fixture.root / fixture.output_relative
            output.mkdir(parents=True)
            main = output / MAIN_EVIDENCE_NAME
            main.write_text(
                json.dumps({"candidate_id": fixture.candidate_id}), encoding="utf-8"
            )
            report = evaluate_glb_append_preflight(
                fixture.root,
                glb_path=fixture.relative(fixture.glb),
                glb_sha256=sha256_file(fixture.glb),
                audit_output_dir=fixture.output_relative,
                main_evidence_sha256=sha256_file(main),
            )
            self.assertTrue(report["ready"], report["blockers"])
            self.assertEqual(
                report["resolved"]["fresh_evidence_path"],
                (fixture.output_relative / GLB_EVIDENCE_NAME).as_posix(),
            )
            self.assertFalse((output / GLB_EVIDENCE_NAME).exists())
            (output / GLB_EVIDENCE_NAME).write_text("already exists", encoding="utf-8")
            overwrite = evaluate_glb_append_preflight(
                fixture.root,
                glb_path=fixture.relative(fixture.glb),
                glb_sha256=sha256_file(fixture.glb),
                audit_output_dir=fixture.output_relative,
                main_evidence_sha256=sha256_file(main),
            )
            self.assertFalse(overwrite["ready"])
            self.assertIn(
                "glb_audit_evidence_exists_refuse_overwrite", overwrite["blockers"]
            )

    def test_input_integrity_rehash_detects_any_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = AuditFixture(Path(raw))
            binding = {
                "blend": {
                    "path": fixture.relative(fixture.blend),
                    "sha256": sha256_file(fixture.blend),
                },
                "build_evidence": {
                    "path": fixture.relative(fixture.build),
                    "sha256": sha256_file(fixture.build),
                },
            }
            self.assertTrue(verify_inputs_unchanged(fixture.root, binding)["passed"])
            fixture.blend.write_bytes(b"changed")
            changed = verify_inputs_unchanged(fixture.root, binding)
            self.assertFalse(changed["passed"])
            self.assertIn("input_changed_or_unavailable:blend", changed["blockers"])


class ProfiledKiraAuditStaticBlenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_source = MAIN_SCRIPT.read_text(encoding="utf-8")
        cls.glb_source = GLB_SCRIPT.read_text(encoding="utf-8")
        cls.contract_source = CONTRACT.read_text(encoding="utf-8")
        cls.main_tree = ast.parse(cls.main_source)
        cls.glb_tree = ast.parse(cls.glb_source)

    def test_blender_scripts_parse_and_main_entrypoints_are_guarded(self) -> None:
        for tree in (self.main_tree, self.glb_tree):
            guarded = [
                node for node in tree.body
                if isinstance(node, ast.If)
                and any(
                    isinstance(value, ast.Constant) and value.value == "__main__"
                    for value in ast.walk(node.test)
                )
            ]
            self.assertEqual(len(guarded), 1)

    def test_main_auditor_has_exact_relationship_and_pose_deformation_gates(self) -> None:
        for token in (
            "exact_nonadjacent_intersection_report",
            "LANDMARK_GROUPS",
            "SUBGROUPS",
            "scaled_adult_surface_settings",
            "ADULT_SURFACE_DETAIL_METHOD_ID",
            "adult_relationship_surface_detail_method",
            "adult_female_surface_detail_method_id",
            "v1_base_authoring_report_exact",
            "v2_structured_detail_report_exact",
            "v2_structured_detail_preserved_topology_and_rig",
            "posterior_landmark_memberships_rebound_to_curved_frame",
            "GLOBAL_EDGE_RATIO_BOUNDS",
            "PELVIC_EDGE_RATIO_BOUNDS",
            "symmetric_upperleg_flexion",
            "asymmetric_upperleg_lunge",
            "symmetric_pelvis_open",
            "left_knee_flexion",
            "right_knee_flexion",
            "bilateral_knee_flexion",
            "zero_new_pelvic_patch_exact_intersections_over_rest",
            "all_relationship_regions_noncollapsed",
            "ordering_preserved",
            "relief_preserved",
            "maximum_positive_influence_count",
            "exactly one marked primary adult surface",
        ):
            self.assertIn(token, self.main_source)
        self.assertEqual(
            self.main_source.count('"runtime_qualified": False'),
            2,
        )

    def test_no_render_save_export_or_activation_operation_exists(self) -> None:
        combined = self.main_source + "\n" + self.glb_source
        for prohibited in (
            "bpy.ops.render",
            "save_as_mainfile",
            "save_mainfile",
            "export_scene.gltf",
            "runtime_body_selection",
            "roster_registration(",
        ):
            self.assertNotIn(prohibited, combined)
        self.assertIn("bpy.ops.import_scene.gltf", self.glb_source)
        self.assertIn("use_scripts=False", self.main_source)

    def test_append_only_evidence_names_and_factory_startup_checks_are_explicit(self) -> None:
        for source in (self.main_source, self.glb_source):
            self.assertIn("bpy.app.background", source)
            self.assertIn("--factory-startup", source)
            self.assertIn("--disable-autoexec", source)
            self.assertIn("activation_allowed", source)
        self.assertIn("MAIN_EVIDENCE_NAME", self.main_source)
        self.assertIn("GLB_EVIDENCE_NAME", self.glb_source)
        self.assertIn("refusing to overwrite", self.main_source.lower())
        self.assertIn("refusing to overwrite", self.glb_source.lower())

    def test_glb_stage_truthfully_inventories_survival_without_runtime_claim(self) -> None:
        for token in (
            "source_to_fresh_import_object_and_morph_survival",
            "glb_container_inventory_before_import",
            "partial_scene_after_import_error",
            "hair_curve_to_mesh_and_morph_survival",
            "CURVE_CONVERTED_TO_MESH",
            "missing_expected_action_names",
            "missing_expected_material_names",
            "hair_wind_left_dry",
            "hair_wet_wind_right",
            "runtime_loaded_or_exercised",
            '"runtime_qualified": False',
        ):
            self.assertIn(token, self.glb_source)

    def test_pure_contract_contains_no_blender_dependency_or_write(self) -> None:
        self.assertNotIn("import bpy", self.contract_source)
        self.assertNotIn("write_text", self.contract_source)
        self.assertNotIn("mkdir", self.contract_source)
        self.assertNotIn("unlink", self.contract_source)
        self.assertNotIn("remove(", self.contract_source)

    def test_documentation_contains_both_exact_clean_process_commands(self) -> None:
        source = DOC.read_text(encoding="utf-8")
        for token in (
            "blender_audit_profiled_kira_adult_candidate.py",
            "blender_fresh_import_profiled_kira_private_glb.py",
            "--background --factory-startup --disable-autoexec",
            "--blend-sha256",
            "--build-evidence-sha256",
            "--main-evidence-sha256",
            MAIN_EVIDENCE_NAME,
            GLB_EVIDENCE_NAME,
            "does not qualify runtime",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
