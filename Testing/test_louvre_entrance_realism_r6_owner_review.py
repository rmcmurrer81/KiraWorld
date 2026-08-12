from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_entrance_realism_r6_20260716_203000"
    / "preview"
)
MANIFEST = json.loads((PREVIEW / "louvre_entrance_realism_r6_pinned_manifest.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((PREVIEW / "louvre_entrance_realism_r6_contract.json").read_text(encoding="utf-8"))
SMOKE_PATH = ROOT / "Data" / "codex_reports" / "20260716_louvre_entrance_realism_r6_browser_smoke_final.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestLouvreEntranceRealismR6OwnerReview(unittest.TestCase):
    def test_pinned_server_accepts_exact_r6_build(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "serve_louvre_entrance_realism_r6_owner_review.py"), "--verify-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("solo, zero people, bounded approximate entrance/stair only", result.stdout)

    def test_manifest_is_separate_zero_person_bounded_review(self) -> None:
        self.assertEqual(MANIFEST["build_id"], "notebook_world_louvre_entrance_realism_r6_20260716_203000")
        self.assertEqual(MANIFEST["status"], "bounded_owner_review_not_complete_not_approved")
        self.assertTrue(MANIFEST["launch_url"].startswith("http://127.0.0.1:5196/"))
        self.assertNotIn("5183", MANIFEST["launch_url"])
        self.assertNotIn("5195", MANIFEST["launch_url"])
        isolation = MANIFEST["runtime_isolation"]
        self.assertTrue(isolation["solo_review_only"])
        self.assertEqual(isolation["people_loaded"], 0)
        self.assertEqual(isolation["minds_loaded"], 0)
        self.assertTrue(isolation["supplied_real_model_exterior_enabled"])
        self.assertTrue(isolation["bounded_approximate_entrance_owner_review_enabled"])
        self.assertTrue(isolation["bounded_approximate_stair_owner_review_enabled"])
        for name in (
            "temporary_ai_activation_allowed",
            "person_systems_loaded",
            "mind_systems_loaded",
            "voice_systems_loaded",
            "home_world_loaded",
            "home_world_mutation_allowed",
            "tardis_loaded",
            "tardis_mutation_allowed",
            "runtime_registered",
            "full_louvre_interior_enabled",
            "working_elevator_enabled",
            "working_escalator_enabled",
            "gallery_inventory_enabled",
            "artwork_inventory_enabled",
            "r4_port_5183_mutation_allowed",
            "r5_port_5195_mutation_allowed",
        ):
            self.assertFalse(isolation[name], name)

    def test_truth_contract_keeps_real_assets_separate_from_approximation(self) -> None:
        self.assertEqual(CONTRACT["status"], "streaming_scaffold_only_not_complete")
        truth = CONTRACT["truth"]
        self.assertTrue(truth["private_zero_person_review"])
        self.assertTrue(truth["supplied_real_model_exterior"])
        self.assertFalse(truth["alignment_exact"])
        self.assertFalse(truth["interior_complete"])
        self.assertTrue(truth["working_approximate_door_proven_by_smoke"])
        self.assertTrue(truth["working_approximate_stair_proven_by_smoke"])
        for name in ("elevators_proven", "escalators_proven", "gallery_rooms_proven", "artwork_inventory_or_placement_proven"):
            self.assertFalse(truth[name], name)
        dimensions = CONTRACT["evidence"]["explicit_approximations_m"]
        self.assertEqual(dimensions["entrance_clear_width"], 3.0)
        self.assertEqual(dimensions["lower_level_vertical_offset"], -8.0)
        self.assertEqual(dimensions["spiral_treads"], 40)
        lower = next(cell for cell in CONTRACT["cells"] if cell["id"] == "under_pyramid_lower_lobby_stair")
        self.assertEqual(lower["activation_gate"]["kind"], "explicit_portal_authorization")
        self.assertTrue(lower["activation_gate"]["authorization_expires_on_unload"])
        locked = next(cell for cell in CONTRACT["cells"] if cell["id"] == "locked_unbuilt_louvre_continuation")
        self.assertFalse(locked["runtime_loadable"])
        self.assertEqual(locked["build_state"], "locked_unbuilt")

    def test_source_and_served_files_are_hash_pinned(self) -> None:
        for item in MANIFEST["source_inputs"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(path.stat().st_size, item["bytes"], item["path"])
            self.assertEqual(sha256(path), item["sha256"], item["path"])
        actual = {path.resolve() for path in (PREVIEW / "dist").rglob("*") if path.is_file()}
        pinned = set()
        roles = set()
        for item in MANIFEST["served_files"]:
            path = (ROOT / item["path"]).resolve()
            pinned.add(path)
            roles.add(item["role"])
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])
        self.assertEqual(actual, pinned)
        self.assertEqual(roles, {"entrypoint", "style", "bundle", "wide_site_context_glb", "pavillon_sully_facade_glb"})

    def test_supplied_assets_reuse_r5_audited_binaries(self) -> None:
        expected = {
            "the_louvre_context_cutout96m_source_mesh.glb": (107547856, "1a1e69277cbe968e3155d4adf9304a2a51e0be581d949b2184fed2850cb87ecb"),
            "pavillon_sully_facade_lod600k.glb": (30439072, "9015233de2e77a24aea77ad342589c8b78eeff0f3c4021cc890ee22af9ef2d68"),
        }
        for filename, (size, digest) in expected.items():
            public_asset = PREVIEW / "public" / "assets" / filename
            served_asset = PREVIEW / "dist" / "assets" / filename
            self.assertEqual(public_asset.stat().st_size, size)
            self.assertEqual(served_asset.stat().st_size, size)
            self.assertEqual(sha256(public_asset), digest)
            self.assertEqual(sha256(served_asset), digest)
        r4_streaming = ROOT / "Data" / "world_builds" / "notebook_worlds" / "paris_notebook_world" / "builds" / "notebook_world_louvre_courtyard_20260628_210935" / "preview" / "src" / "louvre_cell_streaming.js"
        self.assertEqual(sha256(r4_streaming), "c1691c5aabcc4e727cd6b32f001561de6d2088b1216622cce67ad2f01e017cd1")

    def test_final_browser_smoke_proves_only_bounded_portal_and_stair(self) -> None:
        self.assertTrue(SMOKE_PATH.is_file())
        report = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "passed")
        state = report["state"]
        cell_ids = ["cour_napoleon_real_model_exterior", "pyramid_entrance_transition", "under_pyramid_lower_lobby_stair"]
        self.assertEqual(state["initial"]["managed_loaded_cells"], cell_ids[:1])
        self.assertEqual(state["approach"]["managed_loaded_cells"], cell_ids[:2])
        self.assertFalse(state["collision"]["closedThreshold"]["accepted"])
        self.assertTrue(state["collision"]["openThreshold"]["accepted"])
        operation = state["operation"]
        self.assertEqual(operation["resident"]["managed_loaded_cells"], cell_ids)
        self.assertEqual(operation["objects"]["doorLeaf"], 2)
        self.assertEqual(operation["objects"]["stairTread"], 40)
        for unsupported in ("person", "mind", "voice", "elevator", "escalator", "gallery", "artwork"):
            self.assertEqual(operation["objects"][unsupported], 0, unsupported)
        down = operation["down"]
        up = operation["up"]
        self.assertEqual(len(down), 41)
        self.assertEqual(len(up), 41)
        self.assertEqual((down[0]["floor_y_m"], down[-1]["floor_y_m"]), (0, -8))
        self.assertEqual((up[0]["floor_y_m"], up[-1]["floor_y_m"]), (-8, 0))
        self.assertTrue(all(item["accepted"] for item in down + up))
        self.assertTrue(all(down[index]["floor_y_m"] <= down[index - 1]["floor_y_m"] for index in range(1, len(down))))
        self.assertTrue(all(up[index]["floor_y_m"] >= up[index - 1]["floor_y_m"] for index in range(1, len(up))))
        self.assertEqual(operation["far"]["managed_loaded_cells"], cell_ids[:1])
        self.assertIn(cell_ids[1], operation["far"]["persistent_state_cells"])
        self.assertIn(cell_ids[2], operation["far"]["persistent_state_cells"])
        self.assertEqual(operation["far"]["portal_authorized_cells"], [])
        self.assertEqual(operation["reload"]["managed_loaded_cells"], cell_ids[:2])
        self.assertFalse(operation["restoredBeforeDestination"]["thresholdPassable"])
        self.assertTrue(operation["restoredAfterDestination"]["thresholdPassable"])
        active_budget = operation["resident"]["resource_budgets"]["active_set"]
        self.assertLessEqual(operation["metrics"]["triangles"], active_budget["max_triangles"])
        self.assertLessEqual(operation["metrics"]["draw_calls"], active_budget["max_draw_calls"])
        self.assertLessEqual(state["diagnostics"]["render"]["frameP95Milliseconds"], 55)
        self.assertEqual(report["diagnostics"]["pageErrors"], [])
        self.assertEqual(report["diagnostics"]["consoleErrors"], [])
        self.assertEqual(len(report["screenshots"]), 4)
        for screenshot in report["screenshots"]:
            path = ROOT / screenshot["path"]
            self.assertGreater(path.stat().st_size, 10000)
            self.assertEqual(sha256(path), screenshot["sha256"])


if __name__ == "__main__":
    unittest.main()
