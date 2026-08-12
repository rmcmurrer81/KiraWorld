from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


from Testing import test_kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6 as r6_tests
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6 as r6
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7 as r7
from tools import kira_r24_r7_semantic_projection as projection
from tools import kira_r24_r7_sealed_controller as controller


ROOT = Path(__file__).resolve().parents[1]
R6_PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6"
)


class R6PostAuditRegression(r6_tests.R6StaticGateTests):
    """Run every R6 regression, correcting only its known post-audit assertion."""

    def test_29_real_r6_package_is_exact_pre_audit(self) -> None:
        self.assertEqual(r6.package_inventory_status()["state"], "POST_AUDIT_EXACT")


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


class RNA:
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier


class Library:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath


class Material:
    def __init__(self, name: str, library: str | None) -> None:
        self.name = name
        self.library = Library(library) if library is not None else None
        self.bl_rna = RNA("Material")


def rna_serializer(value: object, *, skip: set[str] | None = None) -> dict[str, object]:
    del value, skip
    return {}


def curve_serializer(value: object) -> dict[str, object]:
    return {"path": str(getattr(value, "data_path", ""))}


def strip(name: str, children: list[object] | None = None) -> Item:
    return Item(
        name=name,
        type="META" if children else "CLIP",
        fcurves=[],
        modifiers=[],
        strips=children or [],
    )


def artifact_result(*, eligible: bool = True, failures: list[str] | None = None) -> dict[str, object]:
    names = failures or []
    return {
        "schema": "kira.avatar.r24.r7.fresh_artifact_evaluation.v2",
        "artifact_eligible": eligible,
        "eligible": False,
        "failure_names": names,
        "truth": {
            "author_exit_or_process_tree_proved_here": False,
            "acceptance_requires_sealed_controller": True,
            "immutable_snapshot_used": True,
            "extraction_stdout_anonymous_pipe": True,
        },
    }


class R7HostileStaticTests(unittest.TestCase):
    def test_01_contract_is_fresh_and_recursively_immutable(self) -> None:
        first = r7.load_sealed_contract()
        second = r7.load_sealed_contract()
        self.assertIsNot(first, second)
        self.assertFalse(first["static_execution_authority"])
        with self.assertRaises(TypeError):
            first["static_execution_authority"] = True
        with self.assertRaises(TypeError):
            first["authorized_implementation"]["candidate_basename"] = "evil.blend"
        self.assertFalse(hasattr(r7.load_sealed_contract, "cache_clear"))

    def test_02_worker_controller_and_contract_seals_recompute(self) -> None:
        raw = r7.DEFAULT_CONTRACT.read_bytes()
        overlay = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r7.SEALED_CONTRACT_FILE_SHA256)
        self.assertEqual(
            r7.canonical_sha256(r7._semantic_projection(overlay)),
            r7.SEALED_CONTRACT_SEMANTIC_SHA256,
        )
        implementation = overlay["authorized_implementation"]
        self.assertEqual(
            implementation["worker"]["normalized_semantic_sha256"],
            r7.normalized_worker_sha256(),
        )
        self.assertEqual(
            implementation["sealed_controller"]["normalized_semantic_sha256"],
            r7.normalized_sealed_python_sha256(r7.SEALED_CONTROLLER),
        )

    def test_03_complete_r6_parent_package_is_exact_and_post_audit(self) -> None:
        overlay = json.loads(r7.DEFAULT_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            set(overlay["parent_bindings"]),
            {
                "r6_contract", "r6_proposal", "r6_checkpoint", "r6_manifest",
                "r6_static_results", "r6_audit",
            },
        )
        for record in overlay["parent_bindings"].values():
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(r7.sha256_file(path), record["sha256"])
        self.assertEqual(r6.package_inventory_status()["state"], "POST_AUDIT_EXACT")

    def test_04_runtime_dependency_inventory_is_complete_and_exact(self) -> None:
        contract = r7.load_sealed_contract()
        runtime = contract["authorized_implementation"]["runtime_dependencies"]
        self.assertEqual(
            set(runtime),
            {
                "base_worker", "r2_worker", "r3_worker", "r4_worker",
                "r5_worker", "r6_worker", "typed_r4", "typed_r5", "r4_extractor",
                "r5_extractor", "r7_projection", "r7_extractor",
                "intersection_helper", "r7_author", "r7_evaluator",
            },
        )
        for record in runtime.values():
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(r7.sha256_file(path), record["sha256"])

    @unittest.skipUnless(os.name == "nt", "deny-write/delete leases are Windows-only")
    def test_05_dependency_swap_is_denied_for_entire_lease(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "dependency.py"
            path.write_bytes(b"GOOD")
            replacement = Path(raw) / "replacement.py"
            replacement.write_bytes(b"EVIL")
            lease = controller.ReadDenyWriteDeleteLease(path)
            try:
                with self.assertRaises(OSError):
                    with path.open("r+b") as stream:
                        stream.write(b"EVIL")
                with self.assertRaises(OSError):
                    os.replace(replacement, path)
                self.assertEqual(path.read_bytes(), b"GOOD")
            finally:
                lease.close()

    def test_06_controller_imports_project_code_only_after_leases(self) -> None:
        source = r7.SEALED_CONTROLLER.read_text(encoding="utf-8")
        lease_index = source.index("with lease_exact_paths(paths):")
        import_index = source.index("from tools import kira_r24_intrinsic")
        self.assertGreater(import_index, lease_index)
        self.assertIn("frozen_overlay", source)
        self.assertIn("_merge_contract_overlay(frozen_overlay", source)

    def test_07_controller_command_is_exact_and_not_caller_selected(self) -> None:
        contract = r7.load_sealed_contract()
        command = r7._sealed_controller_command(
            contract, "attempt_01", Path("X:/Blender/blender.exe")
        )
        self.assertEqual(command[1], "-B")
        self.assertEqual(Path(command[2]).resolve(), r7.SEALED_CONTROLLER.resolve())
        self.assertEqual(Path(command[4]).resolve(), r7.DEFAULT_CONTRACT.resolve())
        self.assertNotIn("author_command", inspect.signature(r7.run_sealed_author_then_fresh_evaluator).parameters)

    @unittest.skipUnless(os.name == "nt", "sealed controller is Windows-only")
    def test_08_real_fresh_controller_refuses_before_blender(self) -> None:
        contract = r7.load_sealed_contract()
        command = r7._sealed_controller_command(
            contract, "attempt_01", Path("X:/not-a-real-blender.exe")
        )
        with tempfile.TemporaryDirectory() as raw:
            environment = r7._restricted_child_environment(Path(raw))
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                shell=False,
                env=environment,
                timeout=60,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", "replace"))
        envelope = json.loads(completed.stdout)
        self.assertNotEqual(envelope["controller"]["pid"], os.getpid())
        self.assertEqual(
            envelope["result"]["failure_names"],
            ["r7_static_execution_authority_not_granted"],
        )
        self.assertTrue(envelope["truth"]["dependency_leases_held_through_result"])

    def test_09_internal_static_stop_precedes_blender_and_snapshot(self) -> None:
        contract = r7.load_sealed_contract()
        with mock.patch.object(r7, "immutable_snapshot", side_effect=AssertionError("no snapshot")), mock.patch.object(r7.r4, "validate_blender_runtime", side_effect=AssertionError("no Blender")):
            result = r7.execute_from_fresh_controller(
                contract,
                "attempt_01",
                Path("blender.exe"),
                dependency_bundle_sha256="a" * 64,
                controller_pid=123,
            )
        self.assertEqual(result["failure_names"], ["r7_static_execution_authority_not_granted"])
        self.assertEqual(
            r7.validate_controller_gate_result(
                result,
                required_schema=contract["authorized_implementation"]["required_gate_schema"],
                dependency_bundle_sha256="a" * 64,
            ),
            set(),
        )

    def test_10_extractor_binds_every_behavior_dependency_and_uses_pipe(self) -> None:
        source = (ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r7.py").read_text(encoding="utf-8")
        for token in (
            "--projection-sha256", "--r5-extractor-sha256",
            "--r4-extractor-sha256", "--intersection-helper-sha256",
            "KIRA_R24_R7_EXTRACTION:",
        ):
            self.assertIn(token, source)
        self.assertNotIn('parser.add_argument("--output"', source)
        self.assertNotIn("os.open(", source)

    def _extraction_fixture(self, snapshot: r7.ImmutableSnapshot) -> tuple[dict[str, object], dict[str, object]]:
        contract = r7.load_sealed_contract()
        dependencies = r7._extractor_dependency_records(contract)
        state = {
            name: []
            for name in (
                "objects", "mesh_objects", "armature_objects", "mesh_datablocks",
                "armature_datablocks", "materials", "actions", "images",
                "node_groups", "collections", "worlds", "scenes",
                "intersection_reports",
            )
        }
        payload = {
            "schema": "kira.avatar.r24.read_only_blender_extraction.v7",
            "nonce": "b" * 64,
            "snapshot": {
                "path": str(snapshot.path), "bytes": snapshot.bytes,
                "sha256": snapshot.sha256,
            },
            "logical_artifact_sha256": snapshot.sha256,
            "dependencies": {
                role: {
                    "path": str((ROOT / record["path"]).resolve()),
                    "bytes": record["bytes"], "sha256": record["sha256"],
                }
                for role, record in dependencies.items()
            },
            "blender": {
                "version": "5.1.0", "background": True,
                "loaded_filepath": str(snapshot.path),
                "loaded_file_sha256": snapshot.sha256,
            },
            "state": state,
            "truth": {
                "read_only_extraction": True, "blend_saved": False,
                "snapshot_mutated": False, "in_memory_pose_evaluation_only": True,
            },
            "state_sha256": r7.canonical_sha256(state),
        }
        return payload, dependencies

    def test_11_extraction_envelope_is_exact_and_rejects_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "snapshot.blend"
            path.write_bytes(b"GOOD")
            snapshot = r7.ImmutableSnapshot(path, r7.sha256_file(path), 4, 0, Path(raw))
            payload, dependencies = self._extraction_fixture(snapshot)
            self.assertEqual(
                r7.validate_extraction_envelope(
                    payload, snapshot=snapshot, nonce="b" * 64,
                    dependency_records=dependencies,
                ),
                set(),
            )
            payload["unsealed"] = True
            self.assertIn(
                "extraction:exact_envelope",
                r7.validate_extraction_envelope(
                    payload, snapshot=snapshot, nonce="b" * 64,
                    dependency_records=dependencies,
                ),
            )

    def test_12_extractor_pipe_decoder_rejects_ambiguous_envelopes(self) -> None:
        nonce = "c" * 64
        payload = {"ok": True}
        line = b"KIRA_R24_R7_EXTRACTION:" + nonce.encode() + b":" + r7.canonical_json(payload)
        self.assertEqual(r7._decode_extractor_stdout(b"Blender log\n" + line + b"\n", nonce), payload)
        with self.assertRaises(r7.R7SnapshotError):
            r7._decode_extractor_stdout(line + b"\n" + line + b"\n", nonce)

    def test_13_evaluator_uses_only_stdout_anonymous_pipe(self) -> None:
        evaluator_source = r7.FRESH_EVALUATOR.read_text(encoding="utf-8")
        active_controller_source = inspect.getsource(r7.run_sealed_author_then_fresh_evaluator)
        self.assertNotIn("--output", evaluator_source)
        self.assertNotIn("result.json", evaluator_source)
        self.assertNotIn("output.read_text", active_controller_source)
        self.assertIn("controller_tree.stdout", active_controller_source)

    def _evaluator_fixture(self, candidate: Path):
        contract = r7.load_sealed_contract()
        author = r7.ProcessTreeEvidence(11, "d" * 64, 0, "e" * 64, True, 0, b"", b"")
        evaluator = r7.ProcessTreeEvidence(12, "f" * 64, 0, "1" * 64, True, 0, b"", b"")
        record = contract["authorized_implementation"]["runtime_dependencies"]["r7_evaluator"]
        payload = {
            "schema": "kira.avatar.r24.r7.fresh_evaluator_envelope.v2",
            "controller_nonce": "2" * 64,
            "author_job_nonce": author.job_nonce,
            "candidate": {
                "path": str(candidate.resolve()), "bytes": candidate.stat().st_size,
                "sha256": r7.sha256_file(candidate),
            },
            "immutable_source_snapshot_sha256": "3" * 64,
            "author": {"command_sha256": author.command_sha256, "pid": 11, "job_quiescent": True},
            "evaluator": {
                "pid": 12,
                "path": str((ROOT / record["path"]).resolve()),
                "bytes": record["bytes"], "sha256": record["sha256"],
            },
            "dependency_bundle_sha256": "4" * 64,
            "artifact_result": artifact_result(),
            "truth": {
                "fresh_process": True, "stdout_anonymous_pipe_only": True,
                "writable_result_path_used": False,
            },
        }
        kwargs = {
            "contract": contract, "candidate": candidate,
            "candidate_sha256": r7.sha256_file(candidate),
            "controller_nonce": "2" * 64,
            "immutable_snapshot_sha256": "3" * 64,
            "author": author, "evaluator_tree": evaluator,
            "dependency_bundle_sha256": "4" * 64,
        }
        return payload, kwargs

    def test_14_evaluator_outer_and_artifact_schemas_are_strict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            candidate = Path(raw) / "candidate.blend"
            candidate.write_bytes(b"BODY")
            payload, kwargs = self._evaluator_fixture(candidate)
            self.assertEqual(r7.validate_fresh_evaluator_envelope(payload, **kwargs), set())
            attacked = copy.deepcopy(payload)
            attacked["extra"] = True
            self.assertIn("evaluator:exact_envelope", r7.validate_fresh_evaluator_envelope(attacked, **kwargs))
            attacked = copy.deepcopy(payload)
            attacked["artifact_result"]["extra"] = True
            self.assertIn(
                "evaluator:artifact_result:exact_fields",
                r7.validate_fresh_evaluator_envelope(attacked, **kwargs),
            )

    def test_15_result_file_replacement_has_no_input_to_pipe_decoder(self) -> None:
        good = {"schema": "good"}
        with tempfile.TemporaryDirectory() as raw:
            fake = Path(raw) / "result.json"
            fake.write_text('{"schema":"evil"}', encoding="utf-8")
            self.assertEqual(
                r7._decode_exact_json_stdout(r7.canonical_json(good), "test"), good
            )
            self.assertEqual(json.loads(fake.read_text(encoding="utf-8"))["schema"], "evil")

    def test_16_nla_meta_child_drift_changes_projection(self) -> None:
        a = projection.nla_strip_record(
            strip("META", [strip("A")]),
            rna_serializer=rna_serializer, curve_serializer=curve_serializer,
        )
        b = projection.nla_strip_record(
            strip("META", [strip("B")]),
            rna_serializer=rna_serializer, curve_serializer=curve_serializer,
        )
        self.assertNotEqual(a, b)
        self.assertEqual(a["children"][0]["name"], "A")

    def test_17_nla_meta_cycle_and_depth_fail_closed(self) -> None:
        cyclic = strip("cycle")
        cyclic.strips = [cyclic]
        with self.assertRaises(projection.ProjectionError):
            projection.nla_strip_record(
                cyclic, rna_serializer=rna_serializer,
                curve_serializer=curve_serializer,
            )
        chain = strip("leaf")
        for index in range(18):
            chain = strip(f"meta_{index}", [chain])
        with self.assertRaises(projection.ProjectionError):
            projection.nla_strip_record(
                chain, rna_serializer=rna_serializer,
                curve_serializer=curve_serializer,
            )

    def test_18_same_name_cross_library_material_targets_are_distinct(self) -> None:
        slot_a = Item(name="Body", link="DATA", material=Material("Skin", "//A/library.blend"))
        slot_b = Item(name="Body", link="DATA", material=Material("Skin", "//B/library.blend"))
        a = projection.material_slot_records([slot_a])
        b = projection.material_slot_records([slot_b])
        self.assertNotEqual(a, b)
        self.assertEqual(a[0]["material_target"]["id_rna"], "Material")

    def test_19_ambiguous_material_identity_fails_closed(self) -> None:
        first = Material("Skin", "//A/library.blend")
        second = Material("Skin", "//A/library.blend")
        with self.assertRaises(projection.ProjectionError):
            projection.material_slot_records(
                [
                    Item(name="A", link="DATA", material=first),
                    Item(name="B", link="DATA", material=second),
                ]
            )
        rows = projection.material_slot_records(
            [
                Item(name="A", link="DATA", material=first),
                Item(name="B", link="OBJECT", material=first),
            ]
        )
        self.assertEqual(rows[0]["material_target"], rows[1]["material_target"])

    def test_20_dependency_bundle_is_deterministic_and_full(self) -> None:
        contract = r7.load_sealed_contract()
        rows = r7._dependency_bundle_rows(contract)
        roles = [row["role"] for row in rows]
        self.assertEqual(len(roles), len(set(roles)))
        for role in ("contract", "worker", "controller", "python", "runtime:r7_projection", "runtime:r5_extractor"):
            self.assertIn(role, roles)
        self.assertEqual(r7.canonical_sha256(rows), r7.canonical_sha256(r7._dependency_bundle_rows(contract)))

    def test_21_package_inventory_accepts_only_exact_pre_or_post_audit(self) -> None:
        self.assertEqual(r7.package_inventory_status()["state"], "PRE_AUDIT_EXACT")
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            for name in r7.package_inventory_status()["pre_audit"]:
                (package / name).write_bytes(b"x")
            self.assertEqual(r7.package_inventory_status(package)["state"], "PRE_AUDIT_EXACT")
            (package / "INDEPENDENT_STATIC_AUDIT.md").write_bytes(b"audit")
            self.assertEqual(r7.package_inventory_status(package)["state"], "POST_AUDIT_EXACT")
            (package / "extra.txt").write_bytes(b"no")
            self.assertEqual(r7.package_inventory_status(package)["state"], "INVALID")

    def test_22_manifest_binds_every_package_implementation_and_parent(self) -> None:
        manifest_path = r7.PACKAGE / "PACKAGE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "kira.avatar.r24.r7.package_manifest.v1")
        for section in ("package_files", "implementation_files", "parent_files"):
            for record in manifest[section]:
                path = ROOT / record["path"]
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(r7.sha256_file(path), record["sha256"])

    def test_23_static_evaluation_grants_no_execution_or_body_authority(self) -> None:
        result = r7.static_evaluation()
        self.assertFalse(result["blender_launched"])
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["execution_authority_granted"])
        self.assertTrue(result["fresh_independent_r7_audit_required"])

    def test_24_r7_sources_parse_without_blender_import_or_execution(self) -> None:
        import ast
        for path in (
            Path(r7.__file__), r7.SEALED_CONTROLLER, r7.FRESH_EVALUATOR,
            ROOT / "tools/kira_r24_r7_semantic_projection.py",
            ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r7.py",
        ):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
