from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from Core.avatar_clothed_visual_diagnostic import (
    REQUIRED_ACTION_POSES,
    REQUIRED_FALSE_TRUTH,
    REQUIRED_REST_VIEWS,
    evaluate_clothed_visual_diagnostic,
    sha256_file,
)


# 256 x 256 opaque PNG, used only as a compact integrity fixture.
PNG_256 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAABFUlEQVR42u3TMQEAIAzAsIF/"
    "z0NGHjQKe9szCwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPgB"
    "fQABT9rU9QAAAABJRU5ErkJggg=="
)


class AvatarClothedVisualDiagnosticTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path, Path, str]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        candidate = root / "Avatar" / "temp_ai" / "adult_fixture_001"
        source_model = candidate / "generated_body" / "fixture_clothed_review_assembly.glb"
        source_model.parent.mkdir(parents=True)
        source_model.write_bytes(b"glTF" + b"\0" * 32)
        output = candidate / "private_review" / "turntable_r1"
        output.mkdir(parents=True)
        model = output / "fixture_clothed_review_model_snapshot.glb"
        model.write_bytes(source_model.read_bytes())
        renders = []
        for view in sorted(REQUIRED_REST_VIEWS):
            path = output / f"fixture_{view}.png"
            path.write_bytes(PNG_256 + view.encode("ascii"))
            renders.append(
                {"view": view, "pose": "rest", "path": path.name, "sha256": sha256_file(path)}
            )
        for frame, pose in enumerate(sorted(REQUIRED_ACTION_POSES), start=10):
            path = output / f"fixture_{pose}.png"
            # Keep exact render hashes distinct without changing the PNG header.
            path.write_bytes(PNG_256 + pose.encode("ascii"))
            renders.append(
                {
                    "view": "front_three_quarter",
                    "pose": pose,
                    "action": f"ordinary_{pose}",
                    "frame": frame,
                    "path": path.name,
                    "sha256": sha256_file(path),
                }
            )
        proof = {
            "schema_version": 1,
            "artifact_type": "private_clothed_avatar_visual_diagnostic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": {
                "project_path": model.relative_to(root).as_posix(),
                "sha256": sha256_file(model),
                "byte_identical_private_snapshot": True,
            },
            "input_model": {
                "project_path": source_model.relative_to(root).as_posix(),
                "sha256_at_render_time": sha256_file(source_model),
            },
            "import_inventory": {
                "mesh_object_count": 8,
                "body_mesh_count": 1,
                "clothing_mesh_count": 3,
                "armature_count": 1,
                "action_names": ["ordinary_walk", "ordinary_sit", "ordinary_reach"],
            },
            "bounds_m": {"minimum": [-1, -1, 0], "maximum": [1, 1, 2]},
            "renders": renders,
            "truth": {
                "private_clothed_diagnostic_only": True,
                **{key: False for key in REQUIRED_FALSE_TRUTH},
            },
        }
        proof_path = output / "fixture_visual_diagnostic.json"
        proof_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
        return temporary, root, proof_path, sha256_file(model)

    def test_exact_private_diagnostic_integrity_passes_without_capability_claim(self) -> None:
        temporary, root, proof, model_sha = self.fixture()
        self.addCleanup(temporary.cleanup)
        result = evaluate_clothed_visual_diagnostic(
            root, proof, expected_model_sha256=model_sha
        )
        self.assertTrue(result["integrity_verified"], result["failures"])
        self.assertEqual("integrity_verified_capabilities_unproven", result["status"])
        self.assertEqual(7, result["render_count"])
        self.assertFalse(result["visual_quality_proven"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_tampered_render_and_unsafe_truth_fail_closed(self) -> None:
        temporary, root, proof, _ = self.fixture()
        self.addCleanup(temporary.cleanup)
        value = json.loads(proof.read_text())
        value["truth"]["stable_visual_deformation_proven"] = True
        proof.write_text(json.dumps(value), encoding="utf-8")
        (proof.parent / value["renders"][0]["path"]).write_bytes(b"tampered")
        result = evaluate_clothed_visual_diagnostic(root, proof)
        self.assertFalse(result["integrity_verified"])
        self.assertTrue(any("sha256_mismatch" in item for item in result["failures"]))
        self.assertIn(
            "unsafe_or_missing_truth_flag:stable_visual_deformation_proven",
            result["failures"],
        )

    def test_current_beth_r5_proof_retains_exact_model_and_stays_unapproved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        proof = (
            root
            / "Avatar"
            / "temp_ai"
            / "beth_smith_ordinary_temp_20260716"
            / "private_review"
            / "clothed_turntable_r5"
            / "beth_clothed_weighting_diagnostic_r5_visual_diagnostic.json"
        )
        result = evaluate_clothed_visual_diagnostic(
            root,
            proof,
            expected_model_sha256=(
                "67c63bb69037825c75b85dcac4b48d3ee9cdbd218e38f78f9477fd8920b2c233"
            ),
        )
        self.assertTrue(result["integrity_verified"], result["failures"])
        self.assertEqual({"walk", "sit", "reach"}, set(result["action_poses"]))
        proof_value = json.loads(proof.read_text(encoding="utf-8"))
        action_frames = {
            record["pose"]: record["frame"]
            for record in proof_value["renders"]
            if record["pose"] in {"walk", "sit", "reach"}
        }
        self.assertEqual({"walk": 18, "sit": 35, "reach": 30}, action_frames)
        self.assertFalse(result["owner_approval_proven"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_current_beth_r6_proof_retains_exact_model_and_stays_unapproved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        proof = (
            root
            / "Avatar"
            / "temp_ai"
            / "beth_smith_ordinary_temp_20260716"
            / "private_review"
            / "clothed_turntable_r6_current"
            / "beth_clothed_r6_current_visual_diagnostic.json"
        )
        result = evaluate_clothed_visual_diagnostic(
            root,
            proof,
            expected_model_sha256=(
                "7dfb403372e323ffe4e60b4559a1052f5493a46ff741b3e60ce767e319ba6b83"
            ),
        )
        self.assertTrue(result["integrity_verified"], result["failures"])
        self.assertEqual({"walk", "sit", "reach"}, set(result["action_poses"]))
        self.assertFalse(result["visual_quality_proven"])
        self.assertFalse(result["owner_approval_proven"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_beth_r7_attempts_are_append_only_integrity_evidence_not_readiness(self) -> None:
        root = Path(__file__).resolve().parents[1]
        candidate = (
            root
            / "Avatar"
            / "temp_ai"
            / "beth_smith_ordinary_temp_20260716"
            / "private_review"
        )
        cases = (
            (
                candidate
                / "clothed_turntable_r7_current"
                / "beth_clothed_r7_current_visual_diagnostic.json",
                "233042ed113f2b31ec331a69fb9e2be248b31ae53d3d25312aa8911802559294",
            ),
            (
                candidate
                / "clothed_turntable_r7_bounded"
                / "beth_clothed_r7_bounded_visual_diagnostic.json",
                "957adebe2d9c9e39830657286ea1aefa6026b6c8f8ae74932406989def67b746",
            ),
        )
        for proof, model_sha256 in cases:
            with self.subTest(proof=proof.parent.name):
                result = evaluate_clothed_visual_diagnostic(
                    root, proof, expected_model_sha256=model_sha256
                )
                self.assertTrue(result["integrity_verified"], result["failures"])
                self.assertFalse(result["visual_quality_proven"])
                self.assertFalse(result["owner_approval_proven"])
                self.assertFalse(result["runtime_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
