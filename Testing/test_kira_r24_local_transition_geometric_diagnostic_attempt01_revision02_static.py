"""Static-only acceptance for R24 attempt_01 diagnostic revision 02."""

from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic_attempt_01_revision_02_static"
)
CONFIG = PACKAGE / "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_REVISION02_CONFIG.json"
WRAPPER = PACKAGE / "run_local_transition_geometric_diagnostic_attempt01_revision02_once.ps1"
WORKER = ROOT / "tools/blender_diagnose_kira_r24_local_transition_geometric_attempt01_revision02.py"
CANONICAL = ROOT / "tools/r24_local_transition_canonical_inventory.py"
ATTEMPT01 = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic_attempt_01_static"
)
RUNTIME_OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic/attempt_01"
)
RUNTIME_CACHE = ROOT / (
    "RecoverySprint/runtime_cache/"
    "kira_r24_local_transition_geometric_diagnostic/attempt_01"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dotted_call_name(node: ast.Call) -> str:
    parts = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


class LocalTransitionGeometricAttempt01Revision02StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker = load_module("r24_attempt01_revision02_static", WORKER)
        cls.canonical = load_module("r24_canonical_inventory_static", CANONICAL)
        cls.overlay = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.config = cls.worker.load_config(CONFIG)
        cls.worker.validate_config(cls.config)
        cls.base_config = json.loads(
            (ROOT / cls.overlay["base_config"]["path"]).read_text(encoding="utf-8")
        )

    def test_01_attempt01_is_preserved_byte_for_byte(self) -> None:
        expected = {
            "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_CONFIG.json": "87f9fa8b72e6f1abc6c6cf83c1289913252ca015b424cedfb5061b306b113ae9",
            "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_PROPOSAL.md": "35a5b32affa1ac05aaaa15d91dab9cfd5580fe5ddb1365784138dc89d3889dca",
            "run_local_transition_geometric_diagnostic_attempt01_once.ps1": "376ed6efc967b4d6cd0b41cf7ba802244823295e67314423f17506029ba3601a",
            "CHECKPOINT.md": "5c8f18c01c28053ce7b91c8bbeed6a5b9a1ca94e90b896d68701d03101f5fd81",
            "INDEPENDENT_STATIC_AUDIT.md": "7cb40e8129cf7275d9183ef61f2a54965223c34f874f16dd1d23aaf0929bb1fc",
        }
        self.assertEqual({path.name for path in ATTEMPT01.iterdir()}, set(expected))
        for name, digest in expected.items():
            self.assertEqual(sha256_file(ATTEMPT01 / name), digest, name)

    def test_02_revision_inherits_exact_envelope_and_every_gate(self) -> None:
        for key in (
            "immutable_bindings",
            "protected_inventories",
            "source_mesh",
            "domains",
            "candidate_generator",
            "chart",
            "hard_gates",
            "output_contract",
            "scope",
            "truth",
        ):
            self.assertEqual(self.config[key], self.base_config[key], key)
        self.assertEqual(self.config["static_revision"], 2)
        self.assertEqual(self.config["domains"]["strict_envelope_face_count"], 161)
        self.assertEqual(self.config["domains"]["d2_face_count"], 88)
        self.assertEqual(self.config["domains"]["strict_envelope_collar_face_count"], 73)
        self.assertEqual(self.config["candidate_generator"]["levels"], 192)

    def test_03_shared_python_canonicalization_matches_all_config_hashes(self) -> None:
        for expected in self.config["protected_inventories"]:
            self.assertEqual(
                self.canonical.canonical_inventory(ROOT, expected["root"]),
                expected,
                expected["root"],
            )
        self.assertEqual(
            self.worker.verify_protected_inventories(self.config),
            self.config["protected_inventories"],
        )

    def test_04_wrapper_functionally_invokes_the_same_canonicalization(self) -> None:
        for expected in self.config["protected_inventories"]:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(WRAPPER),
                    "-CanonicalInventoryRoot",
                    expected["root"],
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(json.loads(completed.stdout), expected, expected["root"])
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())

    def test_05_wrapper_has_no_independent_inventory_serializer_or_sum(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("& py -B $canonicalInventoryTool --project $project --root $RelativeRoot", source)
        self.assertIn("[pscustomobject][ordered]", source)
        self.assertNotIn("Measure-Object", source)
        self.assertNotIn("compact = ConvertTo-Json", source)
        invocation_lines = [line for line in source.splitlines() if re.match(r"^\s*& \$blender\b", line)]
        self.assertEqual(len(invocation_lines), 1)
        self.assertIn("1> $temporaryStdout 2> $temporaryStderr", invocation_lines[0])

    def test_06_exact_barycentrics_follow_actual_triangle_order(self) -> None:
        t = Fraction(2, 7)
        self.assertEqual(
            self.worker.exact_edge_barycentric_weights((9, 2, 5), 2, 5, t),
            (Fraction(0), Fraction(5, 7), Fraction(2, 7)),
        )
        self.assertEqual(
            self.worker.exact_edge_barycentric_weights((5, 9, 2), 2, 5, t),
            (Fraction(2, 7), Fraction(0), Fraction(5, 7)),
        )
        coordinates = [(0.0, 0.0, 0.0)] * 10
        coordinates[2] = (7.0, 0.0, 0.0)
        coordinates[5] = (0.0, 7.0, 0.0)
        coordinates[9] = (100.0, 200.0, 300.0)
        weights = self.worker.exact_edge_barycentric_weights((9, 2, 5), 2, 5, t)
        self.assertEqual(
            self.worker.reconstruct_triangle_point((9, 2, 5), weights, coordinates),
            (5.0, 2.0, 0.0),
        )

    def test_07_functional_opposite_triangle_proof_calls_triangle_reconstruction(self) -> None:
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        coordinates = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ]
        incidence = self.worker.edge_incidence(faces)
        phi = {0: Fraction(0), 1: Fraction(1), 2: Fraction(0), 3: Fraction(1)}
        calls = []
        original = self.worker.reconstruct_triangle_point

        def recording_reconstruction(triangle, weights, points):
            calls.append(tuple(triangle))
            return original(triangle, weights, points)

        self.worker.reconstruct_triangle_point = recording_reconstruction
        try:
            proof = self.worker.verify_opposite_triangle_reconstructions(
                1, faces, coordinates, incidence, set(range(4)), phi, self.config
            )
        finally:
            self.worker.reconstruct_triangle_point = original
        self.assertEqual(proof["point_count"], 4)
        self.assertTrue(proof["actual_opposite_triangle_vertex_order_used"])
        self.assertTrue(proof["direct_edge_interpolation_independently_compared"])
        self.assertEqual(len(calls), 8)
        self.assertTrue(any(call in faces for call in calls))

    def test_08_other_reconstruction_is_not_endpoint_alias_code(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("other_triangle = tuple(int(vertex) for vertex in faces[other_face])", source)
        self.assertIn("other_bary = exact_edge_barycentric_weights(other_triangle, first, second, t)", source)
        self.assertIn("other_reconstruction = reconstruct_triangle_point(other_triangle, other_bary, coordinates)", source)
        self.assertIn("other_delta = distance(direct, other_reconstruction)", source)

    def test_09_worker_and_wrapper_remain_read_only_no_save_no_render(self) -> None:
        worker_tree = ast.parse(WORKER.read_text(encoding="utf-8"))
        base_tree = ast.parse((ROOT / self.overlay["base_worker"]["path"]).read_text(encoding="utf-8"))
        calls = sorted(
            {
                dotted_call_name(node)
                for tree in (worker_tree, base_tree)
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and dotted_call_name(node).startswith("bpy.ops")
            }
        )
        self.assertEqual(calls, ["bpy.ops.wm.open_mainfile"])
        combined = (WORKER.read_text(encoding="utf-8") + (ROOT / self.overlay["base_worker"]["path"]).read_text(encoding="utf-8")).lower()
        for forbidden in ("save_as_mainfile", "bpy.ops.render", "bpy.ops.export", "bmesh.ops", ".co ="):
            self.assertNotIn(forbidden, combined)
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)

    def test_10_static_revision_truth_and_output_absence(self) -> None:
        self.assertEqual(self.overlay["attempt_id"], "attempt_01")
        self.assertEqual(self.overlay["static_revision"], 2)
        self.assertFalse(self.overlay["scope"]["blender_launch_authorized"])
        self.assertTrue(self.overlay["scope"]["static_only"])
        self.assertTrue(all(not self.overlay["scope"][key] for key in ("mesh_mutation_allowed", "save_allowed", "render_allowed", "retry_allowed")))
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())


if __name__ == "__main__":
    unittest.main()
