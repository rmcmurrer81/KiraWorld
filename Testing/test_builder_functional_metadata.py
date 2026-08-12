from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Data.world_builder import build_item_prefab_library as prefab_library  # noqa: E402


class BuilderFunctionalMetadataTests(unittest.TestCase):
    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_functional_tagging_covers_wardrobe_storage_and_surfaces(self) -> None:
        scores = prefab_library.tag_text(
            "robe hook towel rack clothing laundry closet linen shelf placement surface"
        )
        for tag in (
            "hook",
            "towel_rack",
            "clothing",
            "robe",
            "laundry",
            "closet",
            "shelf",
            "placement_surface",
        ):
            self.assertIn(tag, scores)
        self.assertIn("hook", prefab_library.tag_text("Wall_Hooks_A_29"))

        self.assertIn(
            "placement_surface",
            prefab_library.add_derived_functional_tags(["bed"]),
        )
        robe_tags = prefab_library.add_derived_functional_tags(["robe"])
        self.assertIn("clothing", robe_tags)

    def test_hook_prefab_detects_named_anchor_but_remains_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=prefab_library.ROOT) as temp_dir:
            source = Path(temp_dir) / "wall_hook.gltf"
            source.write_text(
                json.dumps(
                    {
                        "asset": {"version": "2.0"},
                        "nodes": [
                            {"name": "Wall Hook", "children": [1]},
                            {"name": "hang_point", "mesh": 0},
                        ],
                        "meshes": [{"name": "Hook Mesh", "primitives": []}],
                        "scenes": [{"name": "wall hook"}],
                    }
                ),
                encoding="utf-8",
            )

            prefabs, source_info = prefab_library.build_prefabs_for_source(source)

        hook = next(prefab for prefab in prefabs if prefab.get("nodeName") == "Wall Hook")
        self.assertIn("hook", hook["functionalTags"])
        manifest = hook["interactionManifest"]
        self.assertEqual(manifest["missingRequiredAnchors"], [])
        self.assertEqual(manifest["detectedAnchors"][0]["role"], "hang_point")
        self.assertEqual(manifest["status"], "anchors_named_behavior_evidence_required")
        self.assertFalse(manifest["runtimeReady"])
        self.assertGreater(source_info["functionalPrefabCount"], 0)

    def test_robe_contract_requires_both_sleeves_belt_ends_and_identity(self) -> None:
        anchor_roles = [
            "grip_point",
            "hook_loop",
            "left_sleeve_portal",
            "right_sleeve_portal",
            "left_belt_end",
            "right_belt_end",
        ]
        nodes = [{"name": role} for role in anchor_roles]
        metadata = prefab_library.build_functional_prefab_metadata(["robe"], nodes, None)
        manifest = metadata["interactionManifest"]

        self.assertEqual(manifest["missingRequiredAnchors"], [])
        self.assertIn("dress", {item["id"] for item in manifest["capabilities"]})
        self.assertIn("both_sleeve_passages", manifest["evidenceRequirements"])
        self.assertIn("belt_end_hand_contact", manifest["evidenceRequirements"])
        self.assertTrue(manifest["stateModel"]["persistentObjectIdRequired"])
        self.assertFalse(manifest["stateModel"]["duplicationAllowed"])
        self.assertFalse(manifest["runtimeReady"])

    def test_report_generates_separate_interaction_manifest_library(self) -> None:
        functional = prefab_library.build_functional_prefab_metadata(
            ["shelf"],
            [{"name": "placement_surface"}],
            None,
        )
        prefab = {
            "id": "test_shelf",
            "kind": "node_prefab",
            "source": "test/shelf.gltf",
            "sourceFile": "shelf.gltf",
            "nodeIndex": 0,
            "nodeName": "Linen Shelf",
            "meshCount": 1,
            "tags": ["shelf", "placement_surface"],
            "primaryTag": "shelf",
            "confidence": "high",
            **functional,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "library"
            with patch.object(prefab_library, "OUT_ROOT", out), patch.object(
                prefab_library, "PREFAB_ROOT", out / "prefabs"
            ):
                prefab_library.write_reports([prefab], [], [])
            report = json.loads(
                (out / "interaction_manifest_library.json").read_text(encoding="utf-8")
            )

        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["prefabCount"], 1)
        self.assertEqual(report["runtimeReadyCount"], 0)
        self.assertEqual(report["prefabs"][0]["id"], "test_shelf")
        self.assertFalse(report["prefabs"][0]["interactionManifest"]["runtimeReady"])

    def test_source_id_changes_for_same_size_content_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "same_size.glb"
            source.write_bytes(b"first-content")
            first_id = prefab_library.source_id_for(source)
            source.write_bytes(b"other-content")
            self.assertEqual(len(b"first-content"), len(b"other-content"))
            second_id = prefab_library.source_id_for(source)
            clone = Path(temp_dir) / "same_bytes_different_path.glb"
            clone.write_bytes(b"other-content")
            clone_id = prefab_library.source_id_for(clone)

        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(second_id, clone_id)
        self.assertEqual(len(first_id), 16)
        self.assertEqual(len(second_id), 16)

    def test_supplemental_refresh_writes_only_interaction_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "wall_hook.gltf"
            source.write_text(
                json.dumps(
                    {
                        "asset": {"version": "2.0"},
                        "nodes": [
                            {"name": "Wall Hook", "children": [1]},
                            {"name": "hang_point", "mesh": 0},
                        ],
                        "meshes": [{"name": "Hook Mesh", "primitives": []}],
                    }
                ),
                encoding="utf-8",
            )
            library = root / "item_prefab_library.json"
            library.write_text(
                json.dumps(
                    {
                        "prefabs": [
                            {
                                "id": "legacy_size_bound_id",
                                "kind": "node_prefab",
                                "source": str(source),
                                "sourceFile": source.name,
                                "nodeIndex": 0,
                                "nodeName": "Wall Hook",
                                "nodePath": ["Wall Hook"],
                                "materialNames": [],
                                "tags": ["wall"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output = root / "interaction_manifest_library.json"
            library_before = self._sha256(library)
            source_before = self._sha256(source)

            report = prefab_library.write_supplemental_interaction_manifest(
                library_path=library,
                output_path=output,
            )

            self.assertEqual(self._sha256(library), library_before)
            self.assertEqual(self._sha256(source), source_before)
            self.assertTrue(output.is_file())
            self.assertEqual(report["generationMode"], "non_destructive_supplemental_metadata_refresh")
            self.assertFalse(report["prefabPayloadsCopied"])
            self.assertFalse(report["prefabDescriptorsRewritten"])
            self.assertFalse(report["itemPrefabLibraryRewritten"])
            self.assertEqual(report["prefabCount"], 1)
            self.assertEqual(report["prefabs"][0]["prefabId"], "legacy_size_bound_id")
            self.assertEqual(
                report["prefabs"][0]["contentSourceId"],
                prefab_library.source_id_for(source),
            )
            self.assertIn("hook", report["prefabs"][0]["functionalTags"])
            self.assertFalse(report["prefabs"][0]["interactionManifest"]["runtimeReady"])


if __name__ == "__main__":
    unittest.main()
