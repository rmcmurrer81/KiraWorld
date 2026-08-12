from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock


from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6 as r6
from tools import kira_r24_r6_semantic_projection as projection


ROOT = Path(__file__).resolve().parents[1]
R5_PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r5"
)


class Props:
    def __init__(self, **values: object) -> None:
        self.values = values

    def keys(self):
        return self.values.keys()

    def __getitem__(self, key: str) -> object:
        return self.values[key]


class Item(Props):
    def __init__(self, **values: object) -> None:
        props = values.pop("props", {})
        super().__init__(**props)
        for key, value in values.items():
            setattr(self, key, value)


class R6StaticGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        r6.load_sealed_contract.cache_clear()

    def test_01_contract_and_every_r6_implementation_binding_are_exact(self) -> None:
        contract = r6.load_sealed_contract()
        self.assertEqual(contract["schema"], "kira.avatar.r24.artifact_derived_gate.v6")
        self.assertEqual(
            set(contract["r6_amendments"]),
            {
                "immutable_windows_snapshot_lease",
                "sealed_author_command",
                "full_author_process_tree_quiescence",
                "fresh_evaluator_process",
                "replacement_only_world_quality",
                "nla_custom_node_and_slot_semantics",
                "post_audit_package_state",
            },
        )
        self.assertTrue(all(contract["r6_amendments"].values()))
        self.assertFalse(contract["static_execution_authority"])

    def test_02_worker_and_contract_seals_recompute(self) -> None:
        raw = r6.DEFAULT_CONTRACT.read_bytes()
        contract = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r6.SEALED_CONTRACT_FILE_SHA256)
        self.assertEqual(
            r6.canonical_sha256(r6._semantic_projection(contract)),
            r6.SEALED_CONTRACT_SEMANTIC_SHA256,
        )
        self.assertEqual(
            contract["authorized_implementation"]["worker"]["normalized_semantic_sha256"],
            r6.normalized_worker_sha256(),
        )

    def test_03_rejected_r5_and_its_audit_are_byte_exact_parents(self) -> None:
        expected = {
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R5_CONTRACT.json": (
                4023, "7d1a65fd9d4a732137e62db43a1de0f1d797088819a7bb710459fde2cfc62ecf"
            ),
            "PACKAGE_MANIFEST.json": (
                3468, "bfab9e278d6274c898e2ee40b987eae0e7c0c7bdd5d4298643474c7a84798880"
            ),
            "INDEPENDENT_STATIC_AUDIT.md": (
                17102, "98b2b3f792580a560060576737c58fb04cb81f142bfa9e6edbb86f36e082751d"
            ),
        }
        for name, (size, digest) in expected.items():
            path = R5_PACKAGE / name
            self.assertEqual(path.stat().st_size, size)
            self.assertEqual(r6.sha256_file(path), digest)

    @unittest.skipUnless(os.name == "nt", "R6 immutable lease is intentionally Windows-only")
    def test_04_old_timed_same_size_restore_attack_cannot_open_snapshot_for_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "candidate.blend"
            source.write_bytes(b"GOOD")
            digest = hashlib.sha256(b"GOOD").hexdigest()
            with r6.immutable_snapshot(source, digest, "timed_restore") as snapshot:
                with self.assertRaises(OSError):
                    with snapshot.path.open("r+b") as stream:
                        stream.write(b"EVIL")
                replacement = Path(raw) / "replacement.blend"
                replacement.write_bytes(b"EVIL")
                with self.assertRaises(OSError):
                    os.replace(replacement, snapshot.path)
                self.assertEqual(snapshot.path.read_bytes(), b"GOOD")

    @unittest.skipUnless(os.name == "nt", "R6 immutable lease is intentionally Windows-only")
    def test_05_original_path_can_change_but_verified_snapshot_stays_exact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "candidate.blend"
            source.write_bytes(b"GOOD")
            digest = hashlib.sha256(b"GOOD").hexdigest()
            with r6.immutable_snapshot(source, digest, "decoupled") as snapshot:
                source.write_bytes(b"EVIL")
                self.assertEqual(snapshot.path.read_bytes(), b"GOOD")
                self.assertEqual(r6.sha256_file(snapshot.path), digest)
            self.assertFalse(snapshot.path.exists())

    @unittest.skipUnless(os.name == "nt", "R6 immutable lease is intentionally Windows-only")
    def test_06_snapshot_copy_fails_closed_on_wrong_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "candidate.blend"
            source.write_bytes(b"GOOD")
            with self.assertRaises(r6.R6SnapshotError):
                with r6.immutable_snapshot(source, "0" * 64, "wrong"):
                    self.fail("wrong digest must not yield a snapshot")

    def test_07_extractor_loads_only_snapshot_and_uses_hardened_tokens(self) -> None:
        source = inspect.getsource(r6._invoke_extractor)
        self.assertIn('str(snapshot.path), "--python-exit-code", "1"', source)
        self.assertIn('"--disable-autoexec"', source)
        self.assertIn('"--snapshot", str(snapshot.path)', source)
        self.assertNotIn('str(candidate_path)', source)

    def test_08_extraction_envelope_rejects_a_different_loaded_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "snapshot.blend"
            path.write_bytes(b"GOOD")
            snapshot = r6.ImmutableSnapshot(path, r6.sha256_file(path), 4, 1, Path(raw))
            state = {
                name: []
                for name in (
                    "objects", "mesh_objects", "armature_objects", "mesh_datablocks",
                    "armature_datablocks", "materials", "actions", "images", "node_groups",
                    "collections", "worlds", "scenes", "intersection_reports",
                )
            }
            payload = {
                "schema": "kira.avatar.r24.read_only_blender_extraction.v6",
                "nonce": "a" * 64,
                "snapshot": {"path": str(path), "bytes": 4, "sha256": snapshot.sha256},
                "logical_artifact_sha256": snapshot.sha256,
                "extractor": {"path": str(r6.EXTRACTOR), "bytes": r6.EXTRACTOR.stat().st_size, "sha256": "e" * 64},
                "intersection_helper": {"path": str(r6.INTERSECTION_HELPER), "bytes": r6.INTERSECTION_HELPER.stat().st_size, "sha256": "h" * 64},
                "blender": {"background": True, "loaded_filepath": str(Path(raw) / "evil.blend")},
                "state": state,
                "truth": {"read_only_extraction": True, "blend_saved": False, "snapshot_mutated": False, "in_memory_pose_evaluation_only": True},
                "state_sha256": r6.canonical_sha256(state),
            }
            failures = r6.validate_extraction_envelope(
                payload, snapshot=snapshot, nonce="a" * 64,
                extractor_sha256="e" * 64, helper_sha256="h" * 64,
            )
            self.assertIn("extraction:blender_context", failures)
            snapshot.handle = 0

    def test_09_typed_preflight_is_repeated_against_same_snapshots(self) -> None:
        source = inspect.getsource(r6.artifact_evaluation_only)
        self.assertGreaterEqual(source.count("typed.parse_typed_blend(source_snapshot.path)"), 2)
        self.assertGreaterEqual(source.count("typed.parse_typed_blend(candidate_snapshot.path)"), 2)

    def test_10_old_public_author_capability_and_attestation_entry_are_gone(self) -> None:
        self.assertFalse(hasattr(r6, "_AUTHOR_CAPABILITY"))
        self.assertFalse(hasattr(r6, "_evaluate_post_author"))
        self.assertFalse(hasattr(r6, "run_author_then_evaluate"))
        self.assertNotIn("author_command", inspect.signature(r6.run_sealed_author_then_fresh_evaluator).parameters)

    def test_11_sealed_author_command_is_contract_bound_and_uses_source_snapshot(self) -> None:
        contract = r6.load_sealed_contract()
        snapshot = r6.ImmutableSnapshot(Path("X:/sealed/source.blend"), contract["exact_source"]["preserved_target_blend_sha256"], 1, 0, Path("X:/sealed"))
        command, output = r6._sealed_author_command(
            contract, "attempt_01", "a" * 64, Path("X:/Blender/blender.exe"), snapshot
        )
        self.assertIn(str(snapshot.path), command)
        self.assertIn("--disable-autoexec", command)
        self.assertIn("--python-exit-code", command)
        self.assertEqual(output.name, contract["authorized_implementation"]["candidate_basename"])
        self.assertEqual(output.parent.name, "attempt_01")

    def test_12_static_authority_stops_before_snapshot_or_process_creation(self) -> None:
        with mock.patch.object(r6, "immutable_snapshot", side_effect=AssertionError("must not snapshot")), mock.patch.object(r6.subprocess, "Popen", side_effect=AssertionError("must not launch")):
            result = r6.run_sealed_author_then_fresh_evaluator("attempt_01", Path("blender.exe"))
        self.assertFalse(result["eligible"])
        self.assertEqual(result["failure_names"], ["r6_static_execution_authority_not_granted"])

    def test_13_process_tree_rejects_a_live_descendant_after_direct_exit(self) -> None:
        closed: list[bool] = []

        class FakeJob:
            def assign(self, process): pass
            def resume(self, process): pass
            def wait_quiescent(self, timeout): return True, 1
            def close(self): closed.append(True)

        class FakeProcess:
            pid = 41
            _handle = 42
            returncode = 0
            def communicate(self, timeout): return b"", b""
            def poll(self): return 0

        with mock.patch.object(r6, "_WindowsJob", return_value=FakeJob()), mock.patch.object(r6.subprocess, "Popen", return_value=FakeProcess()):
            with self.assertRaises(r6.R6ProcessProtocolError):
                r6._run_sealed_process_tree(["sealed.exe"], timeout_seconds=1)
        self.assertTrue(closed)

    def test_14_process_tree_records_exact_zero_active_quiescence(self) -> None:
        class FakeJob:
            def assign(self, process): pass
            def resume(self, process): pass
            def wait_quiescent(self, timeout): return True, 0
            def close(self): pass

        class FakeProcess:
            pid = 51
            _handle = 52
            def communicate(self, timeout): return b"", b""
            def poll(self): return 0

        with mock.patch.object(r6, "_WindowsJob", return_value=FakeJob()), mock.patch.object(r6.subprocess, "Popen", return_value=FakeProcess()):
            evidence = r6._run_sealed_process_tree(["sealed.exe", "--exact"], timeout_seconds=1)
        self.assertTrue(evidence.job_signaled)
        self.assertEqual(evidence.active_processes_after_wait, 0)
        self.assertEqual(evidence.returncode, 0)

    def test_15_fresh_evaluator_command_is_exact_separate_python_process(self) -> None:
        contract = r6.load_sealed_contract()
        command = r6._fresh_evaluator_command(
            contract, Path("X:/candidate.blend"), "b" * 64,
            Path("X:/blender.exe"), "c" * 64, Path("X:/result.json"),
        )
        self.assertEqual(command[1], "-B")
        self.assertEqual(Path(command[2]).resolve(), r6.FRESH_EVALUATOR.resolve())
        self.assertIn("--candidate-sha256", command)
        self.assertIn("--nonce", command)

    def test_16_path_only_public_evaluator_remains_fail_closed(self) -> None:
        result = r6.evaluate_candidate_artifact(Path("candidate.blend"), Path("blender.exe"))
        self.assertFalse(result["eligible"])
        self.assertEqual(result["failure_names"], ["path_only_evaluation_forbidden_use_sealed_controller"])

    def test_17_quality_gate_receives_only_derived_replacement_geometry(self) -> None:
        complete = {"kind": "complete_with_inherited_sliver"}
        replacement = {"kind": "replacement_only"}
        contract = {
            "artifact_semantic_identity": {"patch_object_name": "Patch"},
            "metric_bounds": {"minimum_render_triangle_area_m2": 1e-8, "minimum_render_triangle_angle_degrees": 12.0},
        }
        with mock.patch.object(r6.r4, "validate_extracted_pair", return_value={"render:minimum_triangle_area", "render:minimum_triangle_angle"}), mock.patch.object(r6.r5, "validate_complete_protected_state", return_value=set()), mock.patch.object(r6.r5, "validate_complete_child_graphs", return_value=set()), mock.patch.object(r6.r4.r3, "exact_context", return_value={}), mock.patch.object(r6.r4, "_mesh", return_value=complete), mock.patch.object(r6.r4, "derive_repaired_estar_patch", return_value=(set(), replacement)), mock.patch.object(r6.r5, "validate_render_triangulation", return_value=set()) as quality:
            failures = r6.validate_extracted_pair({}, {}, contract)
        self.assertEqual(failures, set())
        self.assertIs(quality.call_args.args[0], replacement)

    def test_18_bad_replacement_world_area_still_fails(self) -> None:
        mesh = {
            "vertices": [
                {"index": 0, "coordinate_local_m": [0.0, 0.0, 0.0]},
                {"index": 1, "coordinate_local_m": [1.0, 0.0, 0.0]},
                {"index": 2, "coordinate_local_m": [0.0, 1.0, 0.0]},
            ],
            "loop_triangles": [{"vertices": [0, 1, 2]}],
            "matrix_world": [[0.001, 0, 0, 0], [0, 0.001, 0, 0], [0, 0, 0.001, 0], [0, 0, 0, 1]],
        }
        with mock.patch.object(r6.r4, "validate_extracted_triangulation_identity", return_value=set()):
            failures = r6.r5.validate_render_triangulation(mesh, 1e-5, 12.0)
        self.assertIn("render:minimum_world_triangle_area", failures)

    def test_19_custom_id_property_value_changes_projection(self) -> None:
        before = projection.custom_properties(Props(controller=0.25, mode="A"))
        after = projection.custom_properties(Props(controller=0.75, mode="A"))
        self.assertNotEqual(before, after)

    def test_20_id_pointer_custom_property_is_bound_by_type_name_and_library(self) -> None:
        value = Item(name="Target", bl_rna=types.SimpleNamespace(identifier="Object"), library=None)
        self.assertEqual(
            projection.value_record(value),
            {"id_rna": "Object", "name": "Target", "library": None},
        )

    def test_21_nla_strip_fcurves_are_serialized(self) -> None:
        strip = Item(
            name="Walk", type="CLIP", rna="strip",
            fcurves=[types.SimpleNamespace(token="curve", data_path="pose.bones", array_index=0)],
            modifiers=[],
        )
        row = projection.nla_strip_record(
            strip,
            rna_serializer=lambda value, skip=None: {"rna": value.rna},
            curve_serializer=lambda value: {"token": value.token},
        )
        self.assertEqual(row["fcurves"], [{"token": "curve"}])

    def test_22_nla_strip_modifiers_are_serialized(self) -> None:
        modifier = Item(type="NOISE", strength=0.75, rna="modifier", props={"seed": 4})
        strip = Item(name="Walk", type="CLIP", rna="strip", fcurves=[], modifiers=[modifier])
        row = projection.nla_strip_record(
            strip,
            rna_serializer=lambda value, skip=None: {"rna": value.rna, "strength": getattr(value, "strength", None)},
            curve_serializer=lambda value: {},
        )
        self.assertEqual(row["modifiers"][0]["custom_properties"], {"seed": 4})
        self.assertEqual(row["modifiers"][0]["rna"]["strength"], 0.75)

    def test_23_color_ramp_element_mutation_changes_projection(self) -> None:
        ramp = Item(color_mode="RGB", hue_interpolation="NEAR", interpolation="LINEAR", elements=[Item(position=0.0, color=(1, 0, 0, 1)), Item(position=1.0, color=(0, 0, 1, 1))])
        before = projection.color_ramp_record(ramp)
        ramp.elements[1].position = 0.8
        after = projection.color_ramp_record(ramp)
        self.assertNotEqual(before, after)

    def test_24_curve_mapping_point_mutation_changes_projection(self) -> None:
        point = Item(location=(0.0, 0.0), handle_type="AUTO")
        mapping = Item(curves=[Item(points=[point])], use_clip=True)
        before = projection.curve_mapping_record(mapping)
        point.location = (0.2, 0.4)
        after = projection.curve_mapping_record(mapping)
        self.assertNotEqual(before, after)

    def test_25_material_slot_link_and_material_are_explicit(self) -> None:
        slot = Item(name="Slot", link="DATA", material=types.SimpleNamespace(name="Skin"))
        before = projection.material_slot_records([slot])
        slot.link = "OBJECT"
        after = projection.material_slot_records([slot])
        self.assertNotEqual(before, after)
        self.assertEqual(before[0]["material"], "Skin")

    def test_26_extractor_explicitly_projects_every_r5_audit_omission(self) -> None:
        source = r6.EXTRACTOR.read_text(encoding="utf-8")
        for token in (
            "projection.custom_properties", "projection.nla_strip_record",
            "projection.node_nested_collections", "projection.material_slot_records",
        ):
            self.assertIn(token, source)

    def test_27_controlled_material_users_normalization_remains_exact(self) -> None:
        contract = {"artifact_semantic_identity": {"required_material_name": "Skin"}}
        base = {"state": {"armature_objects": [], "actions": [], "materials": [{"name": "Skin", "users": 2, "node_tree": {"nodes": []}}]}}
        candidate = copy.deepcopy(base)
        candidate["state"]["materials"][0]["users"] = 3
        self.assertEqual(r6.r5.validate_complete_child_graphs(base, candidate, contract), set())
        candidate["state"]["materials"][0]["users"] = 4
        self.assertIn("child_graph:material:Skin:controlled_users", r6.r5.validate_complete_child_graphs(base, candidate, contract))

    def test_28_package_inventory_supports_exact_pre_and_post_audit_states(self) -> None:
        pre = {
            "CHECKPOINT.md", "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_CONTRACT.json",
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_PROPOSAL.md",
            "PACKAGE_MANIFEST.json", "STATIC_TEST_RESULTS.json",
        }
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            for name in pre:
                (package / name).write_bytes(b"x")
            self.assertEqual(r6.package_inventory_status(package)["state"], "PRE_AUDIT_EXACT")
            (package / "INDEPENDENT_STATIC_AUDIT.md").write_bytes(b"audit")
            self.assertEqual(r6.package_inventory_status(package)["state"], "POST_AUDIT_EXACT")
            (package / "extra.txt").write_bytes(b"bad")
            self.assertEqual(r6.package_inventory_status(package)["state"], "INVALID")

    def test_29_real_r6_package_is_exact_pre_audit(self) -> None:
        self.assertEqual(r6.package_inventory_status()["state"], "PRE_AUDIT_EXACT")

    def test_30_static_evaluation_never_launches_blender_or_grants_authority(self) -> None:
        with mock.patch.object(r6.subprocess, "run", side_effect=AssertionError("must not launch")), mock.patch.object(r6.subprocess, "Popen", side_effect=AssertionError("must not launch")):
            result = r6.static_evaluation()
        self.assertFalse(result["blender_launched"])
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["execution_authority_granted"])
        self.assertTrue(result["fresh_independent_r6_audit_required"])

    def test_31_manifest_binds_exact_package_implementation_and_parent_bytes(self) -> None:
        manifest_path = r6.PACKAGE / "PACKAGE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_bytes())
        self.assertEqual(manifest["schema"], "kira.avatar.r24.r6.package_manifest.v1")
        self.assertNotIn(
            manifest_path.relative_to(ROOT).as_posix(),
            {row["path"] for row in manifest["package_files"]},
        )
        self.assertEqual(
            {Path(row["path"]).name for row in manifest["package_files"]},
            {
                "CHECKPOINT.md",
                "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_CONTRACT.json",
                "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_PROPOSAL.md",
                "STATIC_TEST_RESULTS.json",
            },
        )
        for group in ("package_files", "implementation_files", "parent_files"):
            for row in manifest[group]:
                path = ROOT / row["path"]
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(path.stat().st_size, row["bytes"], str(path))
                self.assertEqual(r6.sha256_file(path), row["sha256"], str(path))


if __name__ == "__main__":
    unittest.main()
