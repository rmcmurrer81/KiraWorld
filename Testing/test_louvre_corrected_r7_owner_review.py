from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.world_reference_evidence import (  # noqa: E402
    WorldReferenceEvidenceError,
    validate_reference_evidence_contract,
)


BUILD_ID = "notebook_world_louvre_corrected_r7_20260716_235000"
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / BUILD_ID
    / "preview"
)
CONTRACT = json.loads((PREVIEW / "louvre_corrected_r7_contract.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((PREVIEW / "louvre_reference_evidence_r7.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((PREVIEW / "louvre_corrected_r7_pinned_manifest.json").read_text(encoding="utf-8"))
SMOKE_PATH = ROOT / "Data" / "codex_reports" / "20260716_louvre_corrected_r7_browser_smoke_final.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestLouvreCorrectedR7OwnerReview(unittest.TestCase):
    def test_server_accepts_only_the_pinned_r7(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "serve_louvre_corrected_r7_owner_review.py"), "--verify-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("main + 3 smaller pyramids", result.stdout)
        self.assertIn("4 locked portals", result.stdout)
        self.assertIn("zero people/minds", result.stdout)

    def test_owner_rejection_and_isolation_are_explicit(self) -> None:
        self.assertEqual(CONTRACT["build_id"], BUILD_ID)
        self.assertEqual(CONTRACT["status"], "corrected_spatial_blockout_not_realism_not_approved")
        rejection = CONTRACT["owner_rejection"]
        self.assertTrue(rejection["r5_r6_wide_scan_rejected"])
        self.assertFalse(rejection["r7_imports_r5_r6_scan_assets"])
        self.assertFalse(rejection["r7_replaces_r4_r5_r6"])
        isolation = CONTRACT["runtime_isolation"]
        self.assertTrue(isolation["solo_review_only"])
        self.assertEqual((isolation["people_loaded"], isolation["minds_loaded"]), (0, 0))
        for flag in (
            "temporary_ai_activation_allowed",
            "person_systems_loaded",
            "mind_systems_loaded",
            "voice_systems_loaded",
            "ollama_loaded",
            "home_world_loaded",
            "home_world_mutation_allowed",
            "tardis_loaded",
            "tardis_mutation_allowed",
            "runtime_registered",
            "full_louvre_interior_enabled",
            "working_doors_enabled",
            "working_elevator_enabled",
            "working_escalator_enabled",
            "gallery_inventory_enabled",
            "artwork_inventory_enabled",
            "r4_port_5183_mutation_allowed",
            "r5_port_5195_mutation_allowed",
            "r6_port_5196_mutation_allowed",
        ):
            self.assertFalse(isolation[flag], flag)

    def test_spatial_contract_is_main_plus_three_and_west_open(self) -> None:
        anchors = CONTRACT["spatial_anchors"]
        main = anchors["main_pyramid"]
        small = anchors["smaller_pyramidions"]
        self.assertEqual((main["base_width_m"], main["height_m"], main["base_area_m2"]), (35, 21, 1000))
        self.assertEqual(small["count"], 3)
        self.assertEqual(set(small["centers_m"]), {"north", "east", "south"})
        self.assertEqual(small["centers_m"]["north"], [0, 0, -48])
        self.assertEqual(small["centers_m"]["east"], [48, 0, 0])
        self.assertEqual(small["centers_m"]["south"], [0, 0, 48])
        self.assertTrue(anchors["palace_massing"]["west_side_open"])
        self.assertEqual(CONTRACT["coordinate_system"]["courtyard_open_side"], "west")

    def test_evidence_gate_passes_only_bounded_drafts_and_locks_destinations(self) -> None:
        decisions = {item.area_id: item for item in validate_reference_evidence_contract(EVIDENCE)}
        self.assertTrue(decisions["cour_napoleon_bounded_exterior"].evidence_sufficient_for_draft)
        self.assertTrue(decisions["under_pyramid_hall_napoleon_stair_study"].evidence_sufficient_for_draft)
        for area_id in ("richelieu_gallery_cells", "sully_gallery_cells", "denon_gallery_cells"):
            self.assertFalse(decisions[area_id].evidence_sufficient_for_draft)
        hall_sources = {item["source_id"]: item for item in EVIDENCE["areas"][1]["sources"]}
        self.assertEqual(hall_sources["louvre_official_hall_napoleon_area"]["truth_use"], "scale_measurement")
        self.assertEqual(CONTRACT["procedural_study"]["official_hall_area_m2"], 2500)
        self.assertEqual(len(EVIDENCE["portals"]), 4)
        for portal in EVIDENCE["portals"]:
            self.assertEqual(portal["runtime_state"], "closed_locked_solid")
            self.assertTrue(portal["collision_solid"])
            self.assertFalse(portal["opens"])
        unsafe = copy.deepcopy(EVIDENCE)
        unsafe["portals"][-1]["opens"] = True
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(unsafe)

    def test_manifest_hashes_every_input_and_served_file(self) -> None:
        self.assertEqual(MANIFEST["manifest_kind"], "louvre_corrected_r7_pinned_owner_review")
        self.assertEqual(MANIFEST["launch_url"], "http://127.0.0.1:5197/?solo=1&bookmark=west_arrival")
        self.assertEqual(len(MANIFEST["source_inputs"]), 12)
        for item in MANIFEST["source_inputs"] + MANIFEST["served_files"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(path.stat().st_size, item["bytes"], item["path"])
            self.assertEqual(sha256(path), item["sha256"], item["path"])
        actual = {path.resolve() for path in (PREVIEW / "dist").rglob("*") if path.is_file()}
        pinned = {(ROOT / item["path"]).resolve() for item in MANIFEST["served_files"]}
        self.assertEqual(actual, pinned)
        self.assertFalse(any(path.suffix.lower() in {".glb", ".gltf", ".fbx"} for path in actual))
        source_names = " ".join(item["path"].lower() for item in MANIFEST["source_inputs"])
        self.assertNotIn("the_louvre_context", source_names)
        self.assertNotIn("pavillon_sully_facade_lod", source_names)

    def test_unapproved_r7_has_an_explicit_zero_person_review_route(self) -> None:
        route = MANIFEST["owner_review_routing"]
        self.assertTrue(route["registered_in_world_shell_or_tardis"])
        self.assertEqual(route["integration_kind"], "separate_world_shell_owner_review_button")
        self.assertFalse(route["production_destination_replaced"])
        self.assertFalse(route["transports_person"])
        self.assertFalse(route["activates_person"])
        self.assertFalse(route["mutates_shell_location"])
        self.assertEqual(route["launcher"], "Start_Louvre_Corrected_R7_Owner_Review.bat")
        self.assertTrue((ROOT / route["launcher"]).is_file())
        self.assertIn("separate window", route["reason"])

    def test_world_shell_exposes_r7_without_location_or_activation_api(self) -> None:
        source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(encoding="utf-8")
        self.assertIn('"title": "Louvre Corrected R7 Review"', source)
        self.assertIn('"url": LOUVRE_R7_REVIEW_URL', source)
        self.assertIn('"launch_path": "/review/louvre-r7"', source)
        self.assertIn('"transports_person": False', source)
        self.assertIn('"activates_person": False', source)
        self.assertIn('"mutates_shell_location": False', source)
        self.assertIn('id="louvreR7Review"', source)
        self.assertNotIn('id="louvreR7Review" data-location=', source)
        handler_start = source.index('document.querySelector("#louvreR7Review").onclick')
        handler_end = source.index('document.querySelector("#observeFollow").onclick', handler_start)
        handler = source[handler_start:handler_end]
        self.assertIn('window.open(destination.launch_path, "_blank")', handler)
        self.assertIn("reviewWindow.opener = null", handler)
        self.assertNotIn('/api/location', handler)
        self.assertNotIn('/api/activate', handler)

        route_start = source.index('if path == "/review/louvre-r7"')
        route_end = source.index('if path == "/api/messages"', route_start)
        route = source[route_start:route_end]
        self.assertIn("ensure_louvre_r7_review_service()", route)
        self.assertIn('self.send_header("Location", LOUVRE_R7_REVIEW_URL)', route)
        self.assertNotIn('/api/location', route)
        self.assertNotIn('/api/activate', route)

        ensure_start = source.index("def ensure_louvre_r7_review_service")
        ensure_end = source.index("def start_processes", ensure_start)
        ensure = source[ensure_start:ensure_end]
        self.assertIn("louvre_r7_review_health()", ensure)
        self.assertIn('str(LOUVRE_R7_REVIEW_PORT)', ensure)
        self.assertIn('"--no-open"', ensure)

    def test_final_browser_smoke(self) -> None:
        self.assertTrue(SMOKE_PATH.is_file())
        smoke = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(smoke["status"], "passed")
        state = smoke["state"]
        self.assertEqual(state["counts"]["mainPyramid"], 1)
        self.assertEqual(state["counts"]["smallerPyramidion"], 3)
        self.assertEqual(state["counts"]["palaceWingGroup"], 3)
        self.assertEqual(state["counts"]["studyStairTread"], 56)
        self.assertEqual(state["counts"]["lockedPortal"], 4)
        self.assertEqual((state["isolation"]["peopleLoaded"], state["isolation"]["mindsLoaded"]), (0, 0))
        self.assertTrue(state["moveProbes"]["paving"]["accepted"])
        self.assertFalse(state["moveProbes"]["main"]["accepted"])
        self.assertFalse(state["moveProbes"]["northSmall"]["accepted"])
        self.assertFalse(state["moveProbes"]["sully"]["accepted"])
        self.assertLessEqual(state["renderer"]["frameP95Milliseconds"], 55)
        self.assertEqual(smoke["diagnostics"]["pageErrors"], [])
        self.assertEqual(smoke["diagnostics"]["consoleErrors"], [])
        self.assertEqual(smoke["diagnostics"]["requestFailures"], [])
        self.assertEqual(smoke["diagnostics"]["httpErrors"], [])
        self.assertEqual(len(smoke["screenshots"]), 6)
        for item in smoke["screenshots"]:
            path = ROOT / item["path"]
            self.assertGreater(path.stat().st_size, 10_000)
            self.assertEqual(sha256(path), item["sha256"])


if __name__ == "__main__":
    unittest.main()
