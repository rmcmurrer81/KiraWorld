from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

from Core import kira_r20_attempt04_quality_diagnostic as diagnostic
from Core import kira_r20_curvilinear_pelvic_patch as r20


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARED = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared_attempt_02"
)
PRIOR_PREPARED = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared"
)
CONFIG = PREPARED / "DIAGNOSTIC_CONFIG.json"
COMMAND = PREPARED / "RUN_DIAGNOSTIC_COMMAND.md"
MANIFEST = PREPARED / "IMPLEMENTATION_MANIFEST.json"
WORKER = PROJECT_ROOT / "tools/blender_diagnose_kira_r20_attempt04_quality_attempt02.py"
TESTS = PROJECT_ROOT / "Testing/test_kira_r20_attempt04_quality_diagnostic_attempt02.py"
SYSTEM_DOC = PROJECT_ROOT / (
    "System/Docs/KIRA_R20_ATTEMPT04_FACE_QUALITY_DIAGNOSTIC_ATTEMPT02_20260802.md"
)
HELPER = PROJECT_ROOT / "Core/kira_r20_attempt04_quality_diagnostic.py"
SEALED_WORKER = PROJECT_ROOT / "tools/blender_author_kira_r20_pelvis_only.py"
PRIOR_CONFIG = PRIOR_PREPARED / "DIAGNOSTIC_CONFIG.json"
OUTPUT = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01"
)

PRIOR_EXACT = {
    "Core/kira_r20_attempt04_quality_diagnostic.py": (
        "89a4674b5be109cedd605d2a51fca6f6bd701fe3b7d4c18f88e8123d631787af",
        21738,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/CHECKPOINT.md": (
        "0828669a8e911f1872fbfbbb39ac0d5309509ce264876d998b6c75af68154a06",
        3372,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/DIAGNOSTIC_CONFIG.json": (
        "9971e3dcaf333df9903c6c154817f74a4b5a78e0daac6b1f80dc0c4512e866b2",
        4736,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/IMPLEMENTATION_MANIFEST.json": (
        "bdfe21e6f79bfce21534c2e65c2b51927ac008243487df469fad27ecc8ab8ecf",
        2370,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/ROLLBACK.md": (
        "ec0c0f456c20b2d256b106c14f788f2d9a2594a7e2a375b7913debff85cbe42d",
        907,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/RUN_DIAGNOSTIC_COMMAND.md": (
        "3d1629828acd304043f18598951966b167e647eafc493fe0ad58413af9c6e966",
        3012,
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_attempt04_quality_diagnostic_prepared/STATIC_TEST_REPORT.json": (
        "1034c7b75cbcc96e8029ca971c8b8c58bacef93cd47fbad19ae595a4684c6586",
        943,
    ),
    "System/Docs/KIRA_R20_ATTEMPT04_FACE_QUALITY_DIAGNOSTIC_20260802.md": (
        "12674ea8c5aa56d71ed28e2dfb18f3df3a63a15e2a3ce7c5a2b2947cc126668b",
        1333,
    ),
    "Testing/test_kira_r20_attempt04_quality_diagnostic.py": (
        "ab1c5c25d73b6400a3092e591a58f97158d1b609296d85f4d9aa3c116fc195c6",
        14541,
    ),
    "tools/blender_diagnose_kira_r20_attempt04_quality.py": (
        "0e7179e88cd53d7f3ba3f7d4fda0e84a4d2ea74443e4019cf117034376e10096",
        23524,
    ),
}

SEALED_AND_ATTEMPT04_EXACT = {
    "Core/kira_r20_curvilinear_pelvic_patch.py": (
        "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d"
    ),
    "tools/blender_author_kira_r20_pelvis_only.py": (
        "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json": (
        "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc"
    ),
    "Testing/test_kira_r20_pelvis_only_authoring.py": (
        "8e12b0573db0715ea339a163d705aa856142e3fbeee9f02e05e96fb3145bc71a"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/IMPLEMENTATION_MANIFEST.json": (
        "eb585114d2096e9ef76c352a7d6f4c578d71fc960e96c3d69d857213598fa306"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_04/PREFLIGHT_EVIDENCE.json": (
        "ff0645d564f935c5e4bd93a621fcbf3653ba91fc0c1830d84196ec818acea105"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/AUTHORING_SUMMARY.json": (
        "66607972ca0678355b87b425678c952cc2b82fdd193894be7bb2666e5186c7af"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/AUTHOR_FAILURE.json": (
        "e0840aef480144a72221646ef4b67fcda1da5404429e4df46957239a6237f07e"
    ),
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_04/r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json": (
        "468b4a8366ce78231b24fada48771a14ca4e96bc8324aec26b2ccbadddcc2299"
    ),
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "attempt_04/r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json": (
        "a60b8b0ad47cbb87d453a34c845850d5e650b23005913c641cbc6cf1dd31fd28"
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def call_chain(node: ast.AST) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def geometry_fixture() -> tuple[list[tuple[float, float, float]], ...]:
    seam = []
    exterior_1 = []
    exterior_2 = []
    normals = []
    for index in range(r20.SEAM_COUNT):
        fraction = index / r20.SEAM_COUNT
        fraction += 0.014 * math.sin(2.0 * math.pi * fraction)
        angle = 2.0 * math.pi * fraction
        radial_x = 0.051 * math.cos(angle)
        radial_z = 0.073 * math.sin(angle)
        surface_y = -0.010 + 0.0022 * math.cos(2.0 * angle)
        seam.append((radial_x, surface_y, 0.87 + radial_z))
        exterior_1.append((1.07 * radial_x, surface_y + 0.001, 0.87 + 1.07 * radial_z))
        exterior_2.append((1.14 * radial_x, surface_y + 0.002, 0.87 + 1.14 * radial_z))
        normals.append((0.0, -1.0, 0.0))
    canonical, order = r20.canonicalize_cycle(seam)
    return (
        list(canonical),
        [exterior_1[index] for index in order],
        [exterior_2[index] for index in order],
        [normals[index] for index in order],
    )


class CorrectedPureContractTests(unittest.TestCase):
    def test_unchanged_helper_still_records_complete_face_detail(self) -> None:
        seam, first, second, normals = geometry_fixture()
        candidate = r20.CANDIDATES[0]
        positions, _evidence = r20.build_positions(seam, first, second, normals, candidate)
        details = diagnostic.detailed_geometry_quality(
            positions,
            r20.build_quad_topology(),
            list(range(1000, 1000 + r20.SEAM_COUNT)),
            worst_n=32,
            maximum_quad_edge_ratio=3.0,
            coincidence_tolerance_m=1.0e-12,
        )
        self.assertEqual(details["face_count"], 756)
        self.assertEqual(len(details["all_face_metrics"]), 756)
        self.assertEqual(len(details["worst_faces"]), 32)
        self.assertIsInstance(details["all_violating_face_metrics"], list)
        worst = details["worst_faces"][0]
        self.assertEqual(len(worst["vertices"]), 4)
        self.assertEqual(len(worst["edges"]), 4)
        self.assertIn(worst["category"], {
            "seam_to_collar_1",
            "collar_1_to_collar_2",
            "collar_2_to_core_3_to_1_leading",
            "collar_2_to_core_3_to_1_trailing",
            "core_grid",
        })


class CorrectedStaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.prior_config = json.loads(PRIOR_CONFIG.read_text(encoding="utf-8"))
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.calls = {
            call_chain(node.func)
            for node in ast.walk(cls.tree)
            if isinstance(node, ast.Call)
        }

    def test_preserved_first_bundle_is_byte_exact(self) -> None:
        for relative, (digest, size) in PRIOR_EXACT.items():
            path = PROJECT_ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(sha256_file(path), digest, relative)
        manifest = json.loads(
            (PRIOR_PREPARED / "IMPLEMENTATION_MANIFEST.json").read_text(encoding="utf-8")
        )
        listed = set()
        for entry in manifest["files_excluding_this_manifest"]:
            path = PROJECT_ROOT / entry["path"]
            self.assertEqual(path.stat().st_size, entry["size_bytes"], entry["path"])
            self.assertEqual(sha256_file(path), entry["sha256"], entry["path"])
            if path.parent.resolve() == PRIOR_PREPARED.resolve():
                listed.add(path.resolve())
        actual = {
            path.resolve()
            for path in PRIOR_PREPARED.iterdir()
            if path.is_file() and path.name != "IMPLEMENTATION_MANIFEST.json"
        }
        self.assertEqual(listed, actual)

    def test_sealed_author_and_attempt04_evidence_are_exact(self) -> None:
        for relative, digest in SEALED_AND_ATTEMPT04_EXACT.items():
            self.assertEqual(sha256_file(PROJECT_ROOT / relative), digest, relative)

    def test_corrected_config_preserves_exact_diagnostic_subject(self) -> None:
        self.assertEqual(self.config["schema_version"], 2)
        self.assertEqual(self.config["status"], "CORRECTED_PREPARED_NOT_EXECUTED")
        for field in (
            "source_blend",
            "source_blend_sha256",
            "output",
            "candidate_ids",
            "worst_face_count_per_candidate",
            "maximum_quad_edge_ratio_threshold_unchanged",
            "minimum_face_area_threshold_m2_unchanged",
            "coincidence_tolerance_m",
            "expected_attempt_04_quality",
        ):
            self.assertEqual(self.config[field], self.prior_config[field], field)
        self.assertEqual(self.config["candidate_ids"], [
            "r20_candidate_a_balanced_organic",
            "r20_candidate_b_soft_natural",
        ])
        self.assertEqual(self.config["worst_face_count_per_candidate"], 32)
        self.assertEqual(self.config["maximum_quad_edge_ratio_threshold_unchanged"], 3.0)

    def test_corrected_bmesh_truth_is_exact(self) -> None:
        correction = self.config["correction"]
        contract = self.config["contract"]
        self.assertTrue(correction["bmesh_module_loaded_transitively"])
        self.assertFalse(correction["direct_bmesh_import_by_corrected_worker"])
        self.assertFalse(correction["bmesh_construction_or_api_call_by_corrected_worker"])
        self.assertFalse(correction["mesh_edit_or_patch_application_by_corrected_worker"])
        self.assertTrue(contract["bmesh_module_loaded_transitively_expected"])
        self.assertTrue(contract["direct_bmesh_import_by_corrected_worker_forbidden"])
        self.assertTrue(contract["bmesh_construction_or_api_call_by_corrected_worker_forbidden"])
        self.assertTrue(contract["mesh_edit_by_corrected_worker_forbidden"])
        legacy_misstatement_key = "bmesh_imported_or_called" + "_by_diagnostic"
        self.assertNotIn(legacy_misstatement_key, json.dumps(self.config))

    def test_corrected_worker_has_no_direct_bmesh_or_mesh_mutation_call(self) -> None:
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertFalse(any(name == "bmesh" or name.startswith("bmesh.") for name in imports))
        self.assertIn("blender_diagnose_kira_r20_attempt04_quality", imports)
        self.assertIn("prior_diagnostic.sealed_author._open_exact_blend", self.calls)
        self.assertIn("prior_diagnostic.sealed_author.preflight_scene", self.calls)
        self.assertIn("prior_diagnostic.build_exact_candidate_geometry", self.calls)
        forbidden = {
            "prior_diagnostic.run",
            "prior_diagnostic.sealed_author._prepare_candidate_fields",
            "prior_diagnostic.sealed_author._apply_local_patch",
            "prior_diagnostic.sealed_author.run_pose_suite",
            "prior_diagnostic.sealed_author.run_verify_render_mode",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.render.render",
            "bpy.ops.object.mode_set",
        }
        self.assertTrue(forbidden.isdisjoint(self.calls), forbidden.intersection(self.calls))
        self.assertFalse(any(call == "bmesh" or call.startswith("bmesh.") for call in self.calls))
        self.assertFalse(any(call.startswith("bpy.ops.mesh.") for call in self.calls))

    def test_worker_records_transitive_load_and_corrected_evidence_fields(self) -> None:
        self.assertIn('if "bmesh" not in sys.modules:', self.source)
        self.assertIn('"bmesh_module_loaded_transitively": True', self.source)
        self.assertIn('"direct_bmesh_import_by_corrected_worker"', self.source)
        self.assertIn('"bmesh_construction_or_api_call_by_corrected_worker"', self.source)
        self.assertIn('"mesh_edit_by_corrected_worker"', self.source)
        legacy_misstatement_key = "bmesh_imported_or_called" + "_by_diagnostic"
        self.assertNotIn(legacy_misstatement_key, self.source)

    def test_hash_bound_sealed_author_is_the_transitive_import_source(self) -> None:
        sealed_source = SEALED_WORKER.read_text(encoding="utf-8")
        sealed_tree = ast.parse(sealed_source)
        imports_bmesh = any(
            isinstance(node, ast.Import)
            and any(alias.name == "bmesh" for alias in node.names)
            for node in ast.walk(sealed_tree)
        )
        self.assertTrue(imports_bmesh)
        self.assertEqual(
            sha256_file(SEALED_WORKER),
            "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a",
        )

    def test_worker_embeds_exact_config_hash(self) -> None:
        digest = sha256_file(CONFIG)
        self.assertEqual(digest, "5aaefa6440816c8dea289e7070e340c2fc4606fb04a310321ff4a3ae124c93fe")
        self.assertIn(f'CONFIG_SHA256 = "{digest}"', self.source)

    def test_output_is_same_append_only_target_and_absent(self) -> None:
        self.assertEqual(
            self.config["output"],
            "RecoverySprint/continuation_20260802/"
            "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01",
        )
        self.assertFalse(OUTPUT.exists())

    def test_one_exact_corrected_command_only(self) -> None:
        value = COMMAND.read_text(encoding="utf-8")
        self.assertEqual(value.count("```powershell"), 1)
        self.assertEqual(
            value.count("blender_diagnose_kira_r20_attempt04_quality_attempt02.py"), 1
        )
        self.assertEqual(
            value.count("kira_r20_attempt04_quality_diagnostic_prepared_attempt_02\\DIAGNOSTIC_CONFIG.json"),
            1,
        )
        self.assertEqual(value.count("--acknowledge-private-inactive"), 1)
        self.assertNotIn("--mode author", value)
        self.assertNotIn("--mode verify-render", value)
        self.assertNotIn("--candidate-id", value)
        self.assertIn(sha256_file(WORKER), value)
        self.assertIn(sha256_file(CONFIG), value)


class FinalSealTests(unittest.TestCase):
    def test_corrected_manifest_is_exact_complete_and_unexecuted(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["status"],
            "SEALED_STATIC_PASS_CORRECTED_DIAGNOSTIC_ATTEMPT02_PREPARED_NOT_EXECUTED",
        )
        self.assertFalse(manifest["diagnostic_blender_executed"])
        self.assertFalse(manifest["diagnostic_output_exists"])
        self.assertTrue(manifest["bmesh_module_loaded_transitively_expected"])
        self.assertFalse(manifest["bmesh_construction_or_api_call_by_corrected_worker"])
        listed = set()
        for entry in manifest["files_excluding_this_manifest"]:
            path = PROJECT_ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(path.stat().st_size, entry["size_bytes"], entry["path"])
            self.assertEqual(sha256_file(path), entry["sha256"], entry["path"])
            listed.add(path.resolve())
        prepared_files = {
            path.resolve()
            for path in PREPARED.iterdir()
            if path.is_file() and path.name != "IMPLEMENTATION_MANIFEST.json"
        }
        listed_prepared = {path for path in listed if path.parent == PREPARED.resolve()}
        self.assertEqual(listed_prepared, prepared_files)
        expected_external = {
            HELPER.resolve(),
            WORKER.resolve(),
            TESTS.resolve(),
            SYSTEM_DOC.resolve(),
            (PRIOR_PREPARED / "IMPLEMENTATION_MANIFEST.json").resolve(),
        }
        self.assertEqual(listed - listed_prepared, expected_external)
        self.assertFalse(OUTPUT.exists())


if __name__ == "__main__":
    unittest.main()
