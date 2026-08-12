"""Static verification for prepared, unexecuted R24 Attempt 32."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_PATCH_APPEND_INVENTORY_ATTEMPT32_CONFIG.json"
)
WORKER = ROOT / "tools/blender_diagnose_kira_r24_patch_append_inventory_attempt32.py"
PROPOSAL = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_32_PATCH_APPEND_INVENTORY_PROPOSAL.md"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_32_STATIC_CHECKPOINT.md"
)
EXPECTED_CONFIG_SHA256 = (
    "941facf7a0f984b87b3e30851553a7409c5ca895cc0afdf3fdb9de99c89cdfe9"
)
EXPECTED_PROPOSAL_SHA256 = (
    "6e613001ebac802140f85b98923312092c2d461b98db22e502eb1cd74f331eaa"
)
EXPECTED_NAMES = [
    "216c8bc711374b3fbf0155edac218dc1.fbx.001",
    "Icosphere",
    "Object_2.001",
    "Object_23",
    "Object_4",
    "RootNode.001",
    "Sketchfab_model.001",
]
EXPECTED_NAMES_SHA256 = (
    "ef4ed395b5f7fc8c0a2d549a23c547d20d74cd45137e16cd68cc08482e08bb85"
)
EXPECTED_DEPENDENCY_SHA256 = (
    "b73a8998e582f5267f85bf9bf1a0bc5c89889fbb2d7c68ea44670b2e924d6269"
)
EXPECTED_EMPTY_LIST_SHA256 = (
    "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
)


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


class Attempt32StaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.worker_source = WORKER.read_text(encoding="utf-8")
        cls.worker_tree = ast.parse(cls.worker_source)
        cls.proposal_source = PROPOSAL.read_text(encoding="utf-8")
        cls.hash_cache: dict[Path, str] = {}

    @classmethod
    def cached_hash(cls, path: Path) -> str:
        if path not in cls.hash_cache:
            cls.hash_cache[path] = sha256_file(path)
        return cls.hash_cache[path]

    def assert_record_exact(self, label: str, record: dict[str, object]) -> Path:
        path = project_path(str(record["path"]))
        self.assertTrue(path.is_file(), label)
        self.assertEqual(path.stat().st_size, int(record["bytes"]), label)
        self.assertEqual(self.cached_hash(path), record["sha256"], label)
        return path

    def assert_package_exact(
        self, manifest: dict[str, object], package_name: str
    ) -> None:
        package = manifest[package_name]
        bindings = manifest["bindings"]
        names = package["binding_names"]
        self.assertEqual(len(names), package["file_count"], package_name)
        self.assertEqual(
            sum(int(bindings[name]["bytes"]) for name in names),
            package["total_bytes"],
            package_name,
        )
        for name in names:
            self.assert_record_exact(f"{package_name}:{name}", bindings[name])

    def test_01_config_proposal_and_worker_compile(self) -> None:
        self.assertEqual(self.cached_hash(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(CONFIG.stat().st_size, 16635)
        self.assertEqual(self.cached_hash(PROPOSAL), EXPECTED_PROPOSAL_SHA256)
        self.assertEqual(PROPOSAL.stat().st_size, 13455)
        proposal_record = self.config["proposal"]
        self.assert_record_exact("proposal", proposal_record)
        compile(self.worker_source, str(WORKER), "exec")
        self.assertIn(EXPECTED_CONFIG_SHA256, self.worker_source)

    def test_02_every_direct_binding_is_byte_and_hash_exact(self) -> None:
        for label, record in self.config["bindings"].items():
            self.assert_record_exact(label, record)

    def test_03_attempt31_failure_and_wrapper_absence_are_exact(self) -> None:
        bindings = self.config["bindings"]
        failure = json.loads(
            project_path(bindings["attempt31_failure"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        contract = self.config["attempt31_failure_contract"]
        self.assertEqual(failure["error_type"], "RuntimeError")
        self.assertEqual(failure["error"], "unexpected Attempt 02 patch append inventory")
        self.assertIn("provider.append_patch", failure["traceback"])
        self.assertIn("line 127, in append_patch", failure["traceback"])
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["render_reached"])
        self.assertFalse(failure["runtime_changed"])
        self.assertEqual(contract["provider_line"], 127)
        self.assertFalse(project_path(contract["attempt31_external_integrity_path"]).exists())

    def test_04_attempt28_through_31_packages_remain_exact(self) -> None:
        self.assert_package_exact(self.config, "preserved_attempt31_package")
        attempt31 = json.loads(
            project_path(self.config["bindings"]["attempt31_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assert_package_exact(attempt31, "preserved_attempt30_package")
        attempt30 = json.loads(
            project_path(attempt31["bindings"]["attempt30_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assert_package_exact(attempt30, "preserved_attempt28_package")
        self.assert_package_exact(attempt30, "preserved_attempt29_package")
        self.assertEqual(self.config["nested_preserved_attempt28_package"]["file_count"], 9)
        self.assertEqual(
            self.config["nested_preserved_attempt28_package"]["total_bytes"], 72757
        )
        self.assertEqual(self.config["nested_preserved_attempt29_package"]["file_count"], 10)
        self.assertEqual(
            self.config["nested_preserved_attempt29_package"]["total_bytes"], 104277
        )
        self.assertEqual(self.config["nested_preserved_attempt30_package"]["file_count"], 10)
        self.assertEqual(
            self.config["nested_preserved_attempt30_package"]["total_bytes"], 685270
        )

    def test_05_historical_authority_package_is_exact(self) -> None:
        authority = self.config["bound_historical_append_authority"]
        expected_names = [
            "r21_attempt01_append_failure_evidence",
            "attempt16_config",
            "attempt16_worker",
            "attempt16_static_test",
            "attempt16_append_inventory",
            "attempt18_append_inventory",
            "attempt19_append_inventory",
            "attempt20_append_inventory",
            "attempt21_append_inventory",
            "attempt22_append_inventory",
            "attempt23_append_inventory",
            "attempt24_append_inventory",
            "attempt25_append_inventory",
            "attempt26_append_inventory",
            "attempt27_append_inventory",
        ]
        self.assertEqual(authority["binding_names"], expected_names)
        self.assertEqual(authority["file_count"], 15)
        self.assertEqual(authority["total_bytes"], 98243)
        self.assertEqual(authority["passing_inventory_attempts"], [16, *range(18, 28)])
        total = 0
        for label in expected_names:
            record = self.config["bindings"][label]
            self.assert_record_exact(label, record)
            total += record["bytes"]
        self.assertEqual(total, 98243)

    def test_06_r21_evidence_records_exact_known_cause_and_distinct_patch(self) -> None:
        record = self.config["bindings"]["r21_attempt01_append_failure_evidence"]
        evidence = json.loads(project_path(record["path"]).read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "FAILED_CLOSED_BEFORE_BODY_MUTATION_OR_SAVE")
        match = re.search(r"inventory: (\[.*\])$", evidence["error"])
        self.assertIsNotNone(match)
        names = ast.literal_eval(match.group(1))
        self.assertEqual(names, EXPECTED_NAMES)
        self.assertFalse(evidence["body_mutation_reached"])
        self.assertFalse(evidence["blend_saved"])
        self.assertFalse(evidence["render_performed"])
        self.assertFalse(evidence["activation_assignment_export_publication_performed"])
        self.assertEqual(
            evidence["source_reconstructed_patch_blend_sha256"],
            "8f0feb0b0732feba1c46a128e318be7f66ed37ff2ed5657d7270c31efd8a9a0f",
        )
        self.assertNotEqual(
            evidence["source_reconstructed_patch_blend_sha256"],
            self.config["bindings"]["preserved_patch_blend"]["sha256"],
        )

    def test_07_exact_seven_object_and_dependency_contract_is_canonical(self) -> None:
        contract = self.config["historical_append_contract"]
        self.assertEqual(contract["expected_appended_object_names"], EXPECTED_NAMES)
        self.assertEqual(canonical_sha256(EXPECTED_NAMES), EXPECTED_NAMES_SHA256)
        self.assertEqual(
            contract["expected_appended_object_names_sha256"], EXPECTED_NAMES_SHA256
        )
        dependencies = [name for name in EXPECTED_NAMES if name != "Object_23"]
        self.assertEqual(
            contract["dependency_object_names_removed_in_memory_only_by_future_reconstruction"],
            dependencies,
        )
        self.assertEqual(canonical_sha256(dependencies), EXPECTED_DEPENDENCY_SHA256)
        self.assertEqual(contract["dependency_object_names_sha256"], EXPECTED_DEPENDENCY_SHA256)
        self.assertEqual(contract["expected_new_collection_names"], [])
        self.assertEqual(canonical_sha256([]), EXPECTED_EMPTY_LIST_SHA256)
        self.assertEqual(
            contract["expected_new_collection_names_sha256"], EXPECTED_EMPTY_LIST_SHA256
        )
        self.assertFalse(contract["attempt32_cleanup_allowed"])
        self.assertIn("Reuse and audit the exact Attempt 16", contract["future_reconstruction_direction"])

    def test_08_every_historical_inventory_matches_normalized_attempt16(self) -> None:
        attempts = self.config["bound_historical_append_authority"][
            "passing_inventory_attempts"
        ]
        normalized_reference = None
        for attempt in attempts:
            label = f"attempt{attempt}_append_inventory"
            record = self.config["bindings"][label]
            inventory = json.loads(project_path(record["path"]).read_text(encoding="utf-8"))
            self.assertEqual(
                inventory["schema"],
                f"kira.avatar.r24.blackproject_attempt{attempt}.append_inventory.v1",
            )
            self.assertEqual(
                inventory["status"],
                "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS",
            )
            self.assertEqual(inventory["requested_object"], "Object_23")
            self.assertEqual(inventory["expected_appended_object_names"], EXPECTED_NAMES)
            self.assertEqual(inventory["actual_appended_object_names"], EXPECTED_NAMES)
            self.assertEqual(
                inventory["expected_appended_object_names_sha256"], EXPECTED_NAMES_SHA256
            )
            self.assertEqual(
                inventory["actual_appended_object_names_sha256"], EXPECTED_NAMES_SHA256
            )
            for field in (
                "missing_object_names",
                "extra_object_names",
                "expected_new_collection_names",
                "actual_new_collection_names",
                "missing_collection_names",
                "extra_collection_names",
            ):
                self.assertEqual(inventory[field], [], f"attempt {attempt}: {field}")
            self.assertEqual(len(inventory["object_signatures"]), 7)
            self.assertFalse(inventory["geometry_mutation_reached"])
            self.assertFalse(inventory["render_reached"])
            self.assertFalse(inventory["blend_saved"])
            normalized = {
                key: value
                for key, value in inventory.items()
                if key not in {"schema", "created_utc"}
            }
            if normalized_reference is None:
                normalized_reference = normalized
            else:
                self.assertEqual(normalized, normalized_reference, f"attempt {attempt}")

    def test_09_object23_signature_is_exact(self) -> None:
        inventory_record = self.config["bindings"]["attempt16_append_inventory"]
        inventory = json.loads(
            project_path(inventory_record["path"]).read_text(encoding="utf-8")
        )
        signatures = {value["name"]: value for value in inventory["object_signatures"]}
        self.assertEqual(
            signatures["Object_23"],
            {
                "name": "Object_23",
                "type": "MESH",
                "data_name": "Ariel_Mesh_Genitalia_0",
                "parent_name": "Object_4",
                "collection_names": [],
                "modifiers": [
                    {"name": "Armature", "type": "ARMATURE", "object": "Object_4"}
                ],
            },
        )
        expected = self.config["historical_append_contract"]["requested_patch_signature"]
        self.assertEqual(expected["name"], "Object_23")
        self.assertEqual(expected["type"], "MESH")
        self.assertEqual(expected["data_name"], "Ariel_Mesh_Genitalia_0")
        self.assertEqual(expected["parent_name"], "Object_4")

    def test_10_worker_loads_one_requested_slot_and_inventories_all_declared_data(self) -> None:
        self.assertIn("with bpy.data.libraries.load(str(patch_blend), link=False)", self.worker_source)
        self.assertIn("target.objects = [requested]", self.worker_source)
        self.assertIn("source_library_object_names", self.worker_source)
        self.assertIn("returned_target_slots", self.worker_source)
        self.assertIn("int(value.as_pointer())", self.worker_source)
        for collection_name in (
            "objects",
            "meshes",
            "armatures",
            "materials",
            "images",
            "node_groups",
            "actions",
            "curves",
            "cameras",
            "lights",
            "collections",
            "scenes",
            "worlds",
        ):
            self.assertIn(collection_name, self.config["data_collection_names"])
        self.assertEqual(len(self.config["data_collection_names"]), 13)

    def test_11_authoritative_gate_replaces_obsolete_singleton_gate(self) -> None:
        source = self.worker_source
        obsolete = source.index('"obsolete_attempt15_singleton_predicate"')
        authoritative = source.index("require_exact_append_contract(config, append_observation)")
        write = source.index('output / str(output_contract["diagnostic"])')
        self.assertLess(obsolete, authoritative)
        self.assertLess(authoritative, write)
        self.assertIn('"exactly_one_new_mesh_passes"', source)
        self.assertNotIn("if attempt15_new_meshes", source)
        self.assertTrue(
            self.config["diagnostic_contract"][
                "attempt15_exactly_one_new_mesh_predicate_is_obsolete_and_observation_only"
            ]
        )
        self.assertTrue(
            self.config["diagnostic_contract"][
                "require_exact_historical_seven_object_ordered_inventory"
            ]
        )

    def test_12_worker_has_no_mutation_cleanup_render_save_or_export_calls(self) -> None:
        banned_imports = {"bmesh", "numpy", "mathutils.geometry"}
        imported = set()
        for node in ast.walk(self.worker_tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(imported.isdisjoint(banned_imports))

        banned_call_suffixes = {
            ".link",
            ".unlink",
            ".remove",
            ".select_set",
            ".save_as_mainfile",
            ".save_mainfile",
            ".write_homefile",
            ".render",
            ".join",
            ".export_scene",
            ".export_mesh",
        }

        def dotted(node: ast.AST) -> str:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return f"{dotted(node.value)}.{node.attr}"
            return ""

        calls = [dotted(node.func) for node in ast.walk(self.worker_tree) if isinstance(node, ast.Call)]
        for call in calls:
            self.assertFalse(any(call.endswith(suffix) for suffix in banned_call_suffixes), call)
        for node in ast.walk(self.worker_tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    name = dotted(target)
                    if name == "target.objects":
                        continue
                    self.assertFalse(
                        name.endswith((".parent", ".matrix_world", ".matrix_parent_inverse")),
                        name,
                    )
        for forbidden in ("reconstruct_local_domain(", "delaunay_2d_cdt(", "weld", "graft_patch("):
            self.assertNotIn(forbidden, self.worker_source)

    def test_13_worker_enforces_body_and_bound_file_pre_post_exactness(self) -> None:
        source = self.worker_source
        body_before = source.index("body_before = sealed_body_digest(body)")
        append = source.index("with bpy.data.libraries.load(str(patch_blend), link=False)")
        body_after = source.index("body_after = sealed_body_digest(body)")
        body_gate = source.index("if body_after != body_before")
        files_before = source.index("verified_before = verify_manifest(config_path, config)")
        files_after = source.index("verified_after = verify_manifest(config_path, config)")
        files_gate = source.index("if verified_after != verified_before")
        self.assertLess(files_before, append)
        self.assertLess(body_before, append)
        self.assertLess(append, body_after)
        self.assertLess(body_after, body_gate)
        self.assertLess(files_after, files_gate)
        self.assertIn('"sealed_body_pre_post_exact": True', source)
        self.assertIn('"bound_files_pre_post_exact": True', source)

    def test_14_evidence_is_exclusive_and_truthful(self) -> None:
        self.assertIn('with path.open("x"', self.worker_source)
        self.assertIn("output.mkdir(parents=True, exist_ok=False)", self.worker_source)
        self.assertNotIn(".replace(", self.worker_source)
        self.assertNotIn("write_text(", self.worker_source)
        for flag in (
            '"scene_link_reached": False',
            '"dependency_cleanup_reached": False',
            '"geometry_mutation_reached": False',
            '"triangulation_reached": False',
            '"reconstruction_reached": False',
            '"graft_reached": False',
            '"render_reached": False',
            '"blend_saved": False',
            '"runtime_changed": False',
        ):
            self.assertIn(flag, self.worker_source)

    def test_15_wrapper_finally_writes_integrity_before_propagating_failure(self) -> None:
        source = self.proposal_source
        self.assertEqual(source.count("$ErrorActionPreference = 'Continue'"), 1)
        invocation = source.index("& $blender --background")
        finally_index = source.index("} finally {", invocation)
        after = source.index("$after = Get-Attempt32Inventory $targets", finally_index)
        integrity_create = source.index(
            "[System.IO.FileMode]::CreateNew", source.index("$integrityStream", after)
        )
        propagate_integrity = source.index("if (-not $integrityPass)", integrity_create)
        propagate_invocation = source.index("if ($null -ne $nativeInvocationError)", integrity_create)
        propagate_exit = source.index("if ($blenderExitCode -ne 0)", integrity_create)
        self.assertLess(invocation, finally_index)
        self.assertLess(finally_index, after)
        self.assertLess(after, integrity_create)
        self.assertLess(integrity_create, propagate_integrity)
        self.assertLess(integrity_create, propagate_invocation)
        self.assertLess(integrity_create, propagate_exit)
        self.assertIn("$ErrorActionPreference = $savedErrorActionPreference", source)
        self.assertIn("pre_post_exact = $integrityPass", source)

    def test_16_wrapper_refuses_overwrite_and_recurses_manifest_bindings(self) -> None:
        source = self.proposal_source
        self.assertIn("foreach ($freshPath in @($output, $stdout, $stderr, $integrity))", source)
        self.assertIn("Attempt 32 refuses to overwrite", source)
        self.assertIn("[System.IO.FileMode]::CreateNew", source)
        self.assertIn("$manifestQueue.Enqueue($config)", source)
        self.assertIn("if ($null -ne $manifest.bindings)", source)
        self.assertIn("$manifestQueue.Enqueue($boundPath)", source)
        self.assertIn("Integrity target escapes project", source)

    def test_17_prepared_state_has_no_attempt32_runtime_artifacts(self) -> None:
        output = project_path(self.config["output"]["root"])
        launch = self.config["launch_contract"]
        self.assertFalse(output.exists())
        self.assertFalse(project_path(launch["stdout"]).exists())
        self.assertFalse(project_path(launch["stderr"]).exists())
        self.assertFalse(project_path(launch["external_integrity"]).exists())
        truth = self.config["truth"]
        self.assertEqual(self.config["status"], "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN")
        for key in (
            "attempt32_blender_execution_performed",
            "attempt32_patch_append_performed",
            "attempt32_inventory_captured",
            "attempt32_body_mutation_performed",
            "attempt32_triangulation_performed",
            "attempt32_reconstruction_performed",
            "attempt32_graft_performed",
            "attempt32_render_reached",
            "attempt32_blend_saved",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[key], key)

    def test_18_tamper_detection_rejects_contract_drift(self) -> None:
        spec = importlib.util.spec_from_file_location("attempt32_worker", WORKER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tampered = json.loads(json.dumps(self.config))
        tampered["historical_append_contract"]["expected_appended_object_names"].pop()
        with self.assertRaisesRegex(RuntimeError, "exactly seven"):
            module.validate_historical_contract(tampered)
        tampered = json.loads(json.dumps(self.config))
        tampered["historical_append_contract"]["expected_new_collection_names"] = ["Drift"]
        with self.assertRaisesRegex(RuntimeError, "unexpectedly permits"):
            module.validate_historical_contract(tampered)

    def test_19_runtime_gate_rejects_slot_or_existing_collection_link_drift(self) -> None:
        spec = importlib.util.spec_from_file_location("attempt32_worker_gate", WORKER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        objects = []
        for name in EXPECTED_NAMES:
            record = {
                "name": name,
                "type": "EMPTY",
                "data_name": None,
                "parent_name": None,
                "collection_names": [],
                "modifiers": [],
            }
            if name == "Object_23":
                record.update(
                    {
                        "type": "MESH",
                        "data_name": "Ariel_Mesh_Genitalia_0",
                        "parent_name": "Object_4",
                        "modifiers": [
                            {
                                "name": "Armature",
                                "type": "ARMATURE",
                                "object": "Object_4",
                            }
                        ],
                    }
                )
            objects.append(record)
        observation = {
            "returned_target_slots": [
                {
                    "index": 0,
                    "is_none": False,
                    "name": "Object_23",
                    "type": "MESH",
                    "data_name": "Ariel_Mesh_Genitalia_0",
                }
            ],
            "actual_appended_object_names": EXPECTED_NAMES,
            "actual_new_collection_names": [],
            "new_named_data_blocks": {"objects": objects},
        }
        module.require_exact_append_contract(self.config, observation)

        slot_drift = json.loads(json.dumps(observation))
        slot_drift["returned_target_slots"][0]["is_none"] = True
        with self.assertRaisesRegex(RuntimeError, "returned target slot drifted"):
            module.require_exact_append_contract(self.config, slot_drift)

        link_drift = json.loads(json.dumps(observation))
        link_drift["new_named_data_blocks"]["objects"][3]["collection_names"] = [
            "ExistingCollection"
        ]
        with self.assertRaisesRegex(RuntimeError, "linked to collections"):
            module.require_exact_append_contract(self.config, link_drift)


if __name__ == "__main__":
    unittest.main(verbosity=2)
