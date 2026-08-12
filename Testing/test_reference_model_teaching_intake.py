from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.reference_model_teaching_intake import (  # noqa: E402
    IntakeError,
    build_intake_manifest,
    build_routes,
    inspect_archive,
    inspect_glb,
    write_consumer_route_links,
    write_intake_outputs,
)


def write_glb(path: Path, *, animation: bool = True, humanoid: bool = True) -> None:
    node_names = (
        ["Hips", "Spine", "Neck", "Head", "LeftShoulder", "LeftUpperArm", "LeftForeArm", "LeftHand", "LeftUpLeg", "LeftLeg", "LeftFoot"]
        if humanoid
        else ["Door", "Hinge"]
    )
    nodes = [{"name": name} for name in node_names]
    nodes.append({"name": "Mesh", "mesh": 0, "skin": 0})
    document = {
        "asset": {"version": "2.0", "generator": "unit-test"},
        "buffers": [{"byteLength": 0}],
        "accessors": [
            {"count": 4, "type": "VEC3", "componentType": 5126},
            {"count": 4, "type": "VEC4", "componentType": 5123},
            {"count": 4, "type": "VEC4", "componentType": 5126},
            {"count": 2, "type": "SCALAR", "componentType": 5126, "min": [0.0], "max": [1.0]},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2}, "targets": [{"POSITION": 0}]}]}],
        "skins": [{"joints": list(range(len(node_names)))}],
        "nodes": nodes,
        "scenes": [{"nodes": [len(nodes) - 1]}],
        "scene": 0,
    }
    if animation:
        document["animations"] = [
            {
                "name": "Walk",
                "samplers": [{"input": 3, "output": 0}],
                "channels": [{"sampler": 0, "target": {"node": 0, "path": "translation"}}],
            }
        ]
    raw = json.dumps(document, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    total = 12 + 8 + len(raw)
    path.write_bytes(
        b"glTF"
        + struct.pack("<II", 2, total)
        + struct.pack("<II", len(raw), 0x4E4F534A)
        + raw
    )


class ReferenceModelTeachingIntakeTests(unittest.TestCase):
    def test_glb_reports_skin_animation_morphs_and_humanoid_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sci_fi_girl_walkcycle.glb"
            write_glb(path)
            result = inspect_glb(path)
            self.assertEqual(result["status"], "valid_glb2")
            self.assertEqual(result["counts"]["animations"], 1)
            self.assertEqual(result["counts"]["skinned_primitives"], 1)
            self.assertEqual(result["counts"]["morph_targets"], 1)
            self.assertTrue(result["likely_humanoid_rig"])
            self.assertEqual(result["animations"][0]["duration_seconds"], 1.0)

    def test_archive_is_metadata_only_and_license_claim_stays_unreviewed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "asset.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("source/model.glb", b"not imported")
                archive.writestr("LICENSE.txt", "CC BY 4.0")
            result = inspect_archive(path, kind="zip")
            self.assertEqual(result["status"], "valid_archive_metadata_only")
            self.assertNotIn("unsafe_path_entry", result["archive_risk_flags"])
            self.assertEqual(result["license"]["status"], "license_claim_detected_unreviewed")
            self.assertFalse(result["license"]["geometry_import_allowed"])
            self.assertEqual(len(result["model_entries"]), 1)

    def test_unsafe_archive_path_is_flagged_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.glb", b"x")
            result = inspect_archive(path, kind="zip")
            self.assertIn("unsafe_path_entry", result["archive_risk_flags"])

    def test_manifest_routes_motion_world_and_restricted_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "91"
            root.mkdir()
            write_glb(root / "sci-fi_girl_walkcycle_test.glb")
            write_glb(root / "old_wooden_door.glb", animation=False, humanoid=False)
            write_glb(root / "beretta_pistol_fps_animation.glb")
            manifest = build_intake_manifest(root, project_root=Path(temp), catalog_paths=[])
            routes = build_routes(manifest)
            self.assertEqual(manifest["file_count"], 3)
            self.assertEqual(routes["movement"]["entry_count"], 1)
            self.assertEqual(routes["world"]["entry_count"], 1)
            self.assertEqual(routes["blocked"]["entry_count"], 1)
            for route in routes.values():
                self.assertFalse(route["runtime_activation_allowed"])
                self.assertFalse(route["automatic_import_allowed"])
                self.assertFalse(route["automatic_retarget_allowed"])

    def test_exact_duplicate_and_existing_catalog_match_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "91"
            root.mkdir()
            payload = b"same bytes"
            (root / "one.zip").write_bytes(payload)
            (root / "two.zip").write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            catalog = Path(temp) / "catalog.json"
            catalog.write_text(json.dumps({"records": [{"sha256": digest}]}), encoding="utf-8")
            manifest = build_intake_manifest(root, project_root=Path(temp), catalog_paths=[catalog])
            self.assertEqual(manifest["duplicate_set_count"], 1)
            self.assertEqual(manifest["unique_file_hashes"], 1)
            self.assertTrue(all(record["existing_catalog_matches"] for record in manifest["files"]))

    def test_outputs_are_content_addressed_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            root = Path(temp) / "91"
            root.mkdir()
            write_glb(root / "pc_gamer_animation.glb")
            manifest = build_intake_manifest(root, project_root=project, catalog_paths=[])
            outputs = write_intake_outputs(manifest, project_root=project)
            links = write_consumer_route_links(outputs, manifest, project_root=project)
            self.assertTrue(outputs.manifest.is_file())
            self.assertTrue(outputs.root.name.startswith(manifest["inventory_sha256"][:16] + "_"))
            payload = json.loads(outputs.manifest.read_text(encoding="utf-8"))
            self.assertFalse(payload["authority"]["avatar_or_person_activation_authorized"])
            for link in (links.avatar, links.movement, links.world):
                link_payload = json.loads(link.read_text(encoding="utf-8"))
                self.assertFalse(link_payload["automatic_import_allowed"])
                self.assertFalse(link_payload["runtime_activation_allowed"])
            outputs.manifest.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(IntakeError):
                write_intake_outputs(manifest, project_root=project)


if __name__ == "__main__":
    unittest.main()
