from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.avatar_body_eye_staged_assembly import (  # noqa: E402
    STAGED_ASSEMBLY_ROOT,
    StagedAssemblyError,
    build_dry_run_plan,
    validate_assembly_inputs,
)


def write_glb(path: Path, document: dict) -> None:
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total = 12 + 8 + len(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
    )


def body_document(head_name: str = "mixamorig:Head_06") -> dict:
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {"name": "Armature", "children": [1, 2]},
            {"name": head_name},
            {"name": "Body", "mesh": 0, "skin": 0},
        ],
        "meshes": [{"name": "BodyMesh", "primitives": [{"attributes": {}}]}],
        "skins": [{"name": "BodySkin", "joints": [1]}],
    }


def eye_document(*, include_right_morph: bool = True) -> dict:
    meshes = [
        {
            "name": "LeftUpperLidMesh",
            "primitives": [{"attributes": {}, "targets": [{}]}],
            "extras": {"targetNames": ["Blink"]},
        },
        {
            "name": "RightUpperLidMesh",
            "primitives": [
                {
                    "attributes": {},
                    **({"targets": [{}]} if include_right_morph else {}),
                }
            ],
            **({"extras": {"targetNames": ["Blink"]}} if include_right_morph else {}),
        },
    ]
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {"name": "EyeRigRoot", "children": [1, 2, 3, 4]},
            {"name": "KiraLeftEyePivot"},
            {"name": "KiraRightEyePivot"},
            {"name": "KiraLeftUpperLid", "mesh": 0},
            {"name": "KiraRightUpperLid", "mesh": 1},
        ],
        "meshes": meshes,
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AvatarBodyEyeStagedAssemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.body = self.root / "inputs/body.glb"
        self.eyes = self.root / "inputs/eyes.glb"
        write_glb(self.body, body_document())
        write_glb(self.eyes, eye_document())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def kwargs(self) -> dict:
        return {
            "subject_id": "kira",
            "run_id": "review_20260718_a",
            "body_path": "inputs/body.glb",
            "body_sha256": digest(self.body),
            "eye_path": "inputs/eyes.glb",
            "eye_sha256": digest(self.eyes),
        }

    def test_dry_run_is_exact_hash_and_creates_nothing(self) -> None:
        before_body = self.body.read_bytes()
        before_eyes = self.eyes.read_bytes()
        plan = build_dry_run_plan(self.root, **self.kwargs())

        self.assertEqual(plan["status"], "dry_run_validated_not_executed")
        self.assertFalse(plan["execution_started"])
        self.assertTrue(plan["private_inactive_staging_only"])
        self.assertFalse(plan["owner_approval_inferred"])
        self.assertFalse(plan["runtime_activation_allowed"])
        self.assertFalse(plan["live_body_replacement_allowed"])
        self.assertFalse(plan["public_export_allowed"])
        self.assertFalse(plan["release_allowed"])
        self.assertEqual(
            plan["attachment"]["recognized_head_joint"], "mixamorig:Head_06"
        )
        self.assertEqual(plan["sources"]["body"]["sha256"], digest(self.body))
        self.assertEqual(plan["sources"]["eyes"]["sha256"], digest(self.eyes))
        self.assertFalse((self.root / STAGED_ASSEMBLY_ROOT).exists())
        self.assertEqual(self.body.read_bytes(), before_body)
        self.assertEqual(self.eyes.read_bytes(), before_eyes)

    def test_hash_mismatch_fails_closed(self) -> None:
        values = self.kwargs()
        values["eye_sha256"] = "0" * 64
        with self.assertRaisesRegex(StagedAssemblyError, "eye-rig GLB SHA-256 mismatch"):
            validate_assembly_inputs(self.root, **values)

    def test_traversal_and_absolute_paths_are_rejected(self) -> None:
        values = self.kwargs()
        values["body_path"] = "../body.glb"
        with self.assertRaisesRegex(StagedAssemblyError, "project-relative"):
            validate_assembly_inputs(self.root, **values)

        values = self.kwargs()
        values["body_path"] = str(self.body.resolve())
        with self.assertRaisesRegex(StagedAssemblyError, "project-relative"):
            validate_assembly_inputs(self.root, **values)

    def test_symlink_source_is_rejected(self) -> None:
        link = self.root / "inputs/body_link.glb"
        try:
            os.symlink(self.body, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        values = self.kwargs()
        values["body_path"] = "inputs/body_link.glb"
        with self.assertRaisesRegex(StagedAssemblyError, "symlink"):
            validate_assembly_inputs(self.root, **values)

    def test_symlink_guard_fails_closed_when_os_symlink_creation_is_unavailable(self) -> None:
        with mock.patch(
            "Core.avatar_body_eye_staged_assembly._has_symlink_component",
            return_value=True,
        ):
            with self.assertRaisesRegex(StagedAssemblyError, "symlink"):
                validate_assembly_inputs(self.root, **self.kwargs())

    def test_append_only_run_directory_must_be_new(self) -> None:
        run_dir = self.root / STAGED_ASSEMBLY_ROOT / "kira/review_20260718_a"
        run_dir.mkdir(parents=True)
        with self.assertRaisesRegex(StagedAssemblyError, "already exists"):
            validate_assembly_inputs(self.root, **self.kwargs())

    def test_body_requires_one_recognized_skin_head_joint(self) -> None:
        write_glb(self.body, body_document("mixamorig:HeadTop_End_07"))
        values = self.kwargs()
        values["body_sha256"] = digest(self.body)
        with self.assertRaisesRegex(StagedAssemblyError, "no recognized head joint"):
            validate_assembly_inputs(self.root, **values)

    def test_eye_rig_requires_separate_controls_and_morphs(self) -> None:
        write_glb(self.eyes, eye_document(include_right_morph=False))
        values = self.kwargs()
        values["eye_sha256"] = digest(self.eyes)
        with self.assertRaisesRegex(StagedAssemblyError, "left/right eye morph"):
            validate_assembly_inputs(self.root, **values)

    def test_external_glb_resource_is_rejected(self) -> None:
        document = eye_document()
        document["images"] = [{"uri": "../../outside.png"}]
        write_glb(self.eyes, document)
        values = self.kwargs()
        values["eye_sha256"] = digest(self.eyes)
        with self.assertRaisesRegex(StagedAssemblyError, "external image URI"):
            validate_assembly_inputs(self.root, **values)


if __name__ == "__main__":
    unittest.main()
