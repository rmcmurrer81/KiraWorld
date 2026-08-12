import json
import hashlib
import math
import re
import unittest
from pathlib import Path

from Core.notebook_world_cell_streaming import load_contract, plan_interest


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "preview"
)
CONTRACT_PATH = PREVIEW / "louvre_exterior_contract.json"
MAIN_JS_PATH = PREVIEW / "src" / "main.js"
INDEX_PATH = PREVIEW / "index.html"
PINNED_MANIFEST_PATH = PREVIEW / "louvre_solo_pinned_build_manifest.json"
SERVER_PATH = ROOT / "tools" / "serve_louvre_solo_notebook_world_test.py"
LAUNCHER_PATH = ROOT / "Start_Louvre_Solo_Notebook_World_Test.bat"
LAUNCH_SUPERVISOR_PATH = ROOT / "tools" / "launch_louvre_solo_notebook_world_test.py"
STREAMING_CONTRACT_PATH = PREVIEW / "louvre_cell_streaming_contract.json"
STREAMING_RUNTIME_PATH = PREVIEW / "src" / "louvre_cell_streaming.js"
TARDIS_DESTINATION_PATH = ROOT / "Data" / "world_access" / "tardis_destinations" / "louvre_solo_owner_review.json"
TARDIS_GATEWAY_PATH = ROOT / "Data" / "world_access" / "tardis_notebook_world_gateway.json"
SHELL_SERVER_PATH = ROOT / "tools" / "kira_world_shell_server.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LouvreSoloNotebookWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.main_js = MAIN_JS_PATH.read_text(encoding="utf-8")
        cls.index_html = INDEX_PATH.read_text(encoding="utf-8")
        cls.pinned_manifest = json.loads(PINNED_MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.server_source = SERVER_PATH.read_text(encoding="utf-8")
        cls.launch_supervisor_source = LAUNCH_SUPERVISOR_PATH.read_text(encoding="utf-8")
        cls.streaming_contract = load_contract(STREAMING_CONTRACT_PATH)
        cls.streaming_runtime = STREAMING_RUNTIME_PATH.read_text(encoding="utf-8")
        cls.tardis_destination = json.loads(TARDIS_DESTINATION_PATH.read_text(encoding="utf-8"))
        cls.tardis_gateway = json.loads(TARDIS_GATEWAY_PATH.read_text(encoding="utf-8"))
        cls.shell_server_source = SHELL_SERVER_PATH.read_text(encoding="utf-8")

    def test_runtime_is_a_fail_closed_solo_bounded_circulation_review(self) -> None:
        runtime = self.contract["runtime_isolation"]
        self.assertTrue(runtime["solo_review_only"])
        self.assertFalse(runtime["temporary_ai_activation_allowed"])
        self.assertEqual(runtime["people_loaded"], 0)
        self.assertEqual(runtime["minds_loaded"], 0)
        self.assertFalse(runtime["voice_loaded"])
        self.assertFalse(runtime["ollama_loaded"])
        self.assertFalse(runtime["home_world_loaded"])
        self.assertFalse(runtime["home_world_mutation_allowed"])
        self.assertFalse(runtime["strip_mall_mutation_allowed"])
        self.assertFalse(runtime["runtime_registered"])
        self.assertFalse(runtime["interior_enabled"])
        self.assertTrue(runtime["bounded_approximate_circulation_owner_review_enabled"])
        self.assertFalse(runtime["full_louvre_interior_enabled"])
        self.assertFalse(runtime["elevators_enabled"])
        self.assertFalse(runtime["artwork_enabled"])
        self.assertFalse(runtime["gallery_enabled"])
        self.assertFalse(runtime["tardis_present_by_default"])
        self.assertEqual(self.contract["status"], "prototype_draft_not_final_not_approved")

    def test_official_dimensions_and_current_sources_are_bound(self) -> None:
        pyramid = self.contract["scale"]["main_pyramid"]
        self.assertEqual(pyramid["height_m"], 21)
        self.assertEqual(pyramid["base_width_m"], 35)
        self.assertEqual(pyramid["base_area_m2"], 1000)
        urls = {source["url"] for source in self.contract["official_sources"]}
        self.assertIn(
            "https://www.louvre.fr/en/explore/the-palace/a-pyramid-for-a-symbol",
            urls,
        )
        self.assertIn(
            "https://www.louvre.fr/en/visit/map-entrances-directions",
            urls,
        )
        self.assertIn(
            "https://api-www.louvre.fr/sites/default/files/2026-05/2026-05_Plan_Louvre_EN.pdf",
            urls,
        )
        self.assertIn(
            "https://www.louvre.fr/en/visit/accessibility/visitors-with-physical-disabilities",
            urls,
        )

    def test_robert_supplied_circulation_evidence_is_hash_bound_and_limited(self) -> None:
        evidence = self.contract["robert_supplied_visual_evidence"]
        self.assertEqual(len(evidence), 4)
        for item in evidence:
            with self.subTest(path=item["path"]):
                path = ROOT / item["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(sha256_file(path), item["sha256"])
                self.assertTrue(item["supports"])
                self.assertTrue(item["does_not_support"])
        unsupported = " ".join(
            limitation for item in evidence for limitation in item["does_not_support"]
        )
        self.assertIn("door mechanism", unsupported)
        self.assertIn("elevators", unsupported)

    def test_exactly_two_small_cour_napoleon_pyramids_are_rendered(self) -> None:
        rendered = re.findall(
            r'createSquarePyramid\("(?:west|east) small Cour Napoleon pyramid approximate placement"',
            self.main_js,
        )
        self.assertEqual(len(rendered), 2)
        self.assertNotIn("small pyramid placeholder north", self.main_js)
        official_facts = " ".join(self.contract["officially_supported_facts"])
        self.assertIn("two smaller pyramids", official_facts)

    def test_all_static_routes_clear_declared_colliders(self) -> None:
        clearance = self.contract["scale"]["avatar_clearance_radius_m"]
        colliders = self.contract["colliders"]
        for route in self.contract["routes"]:
            with self.subTest(route=route["id"]):
                for start, end in zip(route["points"], route["points"][1:]):
                    distance = math.dist(start, end)
                    steps = max(1, math.ceil(distance / 0.25))
                    for step in range(steps + 1):
                        amount = step / steps
                        x = start[0] + (end[0] - start[0]) * amount
                        z = start[1] + (end[1] - start[1]) * amount
                        for collider in colliders:
                            center_x, center_z = collider["center"]
                            half_x, half_z = collider["half_extents"]
                            blocked = (
                                abs(x - center_x) < half_x + clearance
                                and abs(z - center_z) < half_z + clearance
                            )
                            self.assertFalse(
                                blocked,
                                f"{route['id']} intersects {collider['id']} at {(x, z)}",
                            )

    def test_landmarks_and_collision_contract_are_nonempty_and_meter_scaled(self) -> None:
        self.assertEqual(self.contract["scale"]["world_units"], "meters")
        self.assertEqual(self.contract["scale"]["eye_height_m"], 1.68)
        self.assertGreaterEqual(len(self.contract["landmarks"]), 6)
        self.assertGreaterEqual(len(self.contract["colliders"]), 12)
        self.assertGreaterEqual(len(self.contract["routes"]), 5)
        landmark_ids = {landmark["id"] for landmark in self.contract["landmarks"]}
        self.assertIn("pyramid_scale_view", landmark_ids)
        self.assertIn("pyramid_entrance_apron", landmark_ids)
        self.assertIn("north_facade_view", landmark_ids)

    def test_solo_mode_suppresses_actor_manifest_and_tardis_arrival(self) -> None:
        self.assertIn(
            'const showActors = showActorsRequested && !soloLouvreMode;',
            self.main_js,
        )
        self.assertIn(
            'const parisTardisArrived = !soloLouvreMode &&',
            self.main_js,
        )
        self.assertIn("if (!showActors) return;", self.main_js)
        self.assertNotIn("\nbuildLouvreInterior();", self.main_js)
        self.assertIn("window.__previewReady = true", self.main_js)

    def test_visible_truth_and_exportable_feedback_controls_exist(self) -> None:
        for element_id in (
            "truthPanel",
            "truthPanelBody",
            "feedbackToggle",
            "feedbackPanel",
            "feedbackCategory",
            "feedbackVerdict",
            "feedbackNote",
            "feedbackSave",
            "feedbackExport",
            "reviewPackageExport",
            "packageStatus",
            "feedbackStatus",
            "landmarkStatus",
            "reviewMetrics",
            "routeMetric",
            "walkMetric",
            "collisionMetric",
            "bookmarkPanel",
            "bookmarkSelect",
            "bookmarkGo",
            "bookmarkNext",
            "bookmarkLink",
            "bookmarkCopy",
            "truthMarkersToggle",
        ):
            self.assertIn(f'id="{element_id}"', self.index_html)
        self.assertEqual(self.contract["feedback"]["export_format"], "local_json_download")
        self.assertFalse(self.contract["feedback"]["server_write_enabled"])
        self.assertIn("exportReviewFeedback", self.main_js)
        self.assertIn("buildOwnerReviewPackage", self.main_js)
        self.assertIn("self_contained_json_with_embedded_png_capture", json.dumps(self.contract))
        self.assertIn("localStorage.setItem", self.main_js)

    def test_truth_markers_bookmarks_and_measurements_are_explicit(self) -> None:
        markers = self.contract["in_world_truth_markers"]
        bookmarks = self.contract["review_bookmarks"]
        self.assertGreaterEqual(len(markers), 5)
        self.assertGreaterEqual(len(bookmarks), 5)
        marker_truth = {marker["truth"] for marker in markers}
        self.assertIn("approximate", marker_truth)
        self.assertIn("locked", marker_truth)
        self.assertTrue(any(value.startswith("mixed_official") for value in marker_truth))

        bookmark_ids = [bookmark["id"] for bookmark in bookmarks]
        self.assertEqual(len(bookmark_ids), len(set(bookmark_ids)))
        self.assertIn("arrival_scale", bookmark_ids)
        self.assertIn("entrance_human", bookmark_ids)
        self.assertIn("two_small_pyramids", bookmark_ids)
        for bookmark in bookmarks:
            with self.subTest(bookmark=bookmark["id"]):
                self.assertEqual(len(bookmark["position"]), 3)
                self.assertEqual(len(bookmark["target"]), 3)
                self.assertFalse(
                    any(
                        abs(bookmark["position"][0] - collider["center"][0])
                        < collider["half_extents"][0]
                        and abs(bookmark["position"][2] - collider["center"][1])
                        < collider["half_extents"][1]
                        for collider in self.contract["colliders"]
                    ),
                    "Bookmark starts inside a declared collider",
                )
                self.assertIn(
                    bookmark["route_id"],
                    {route["id"] for route in self.contract["routes"]},
                )
        self.assertEqual(
            self.contract["review_measurements"]["route_progress_method"],
            "nearest point projected onto the active route polyline",
        )
        self.assertEqual(self.contract["review_measurements"]["collision_event_debounce_ms"], 750)
        self.assertFalse(self.contract["review_package"]["server_write_enabled"])
        self.assertTrue(self.contract["review_package"]["client_side_only"])
        self.assertIn("measureRouteAt", self.main_js)
        self.assertIn("recordReviewCollision", self.main_js)

    def test_approximation_and_locked_unknown_lists_are_explicit(self) -> None:
        self.assertGreaterEqual(len(self.contract["approximations"]), 5)
        self.assertGreaterEqual(len(self.contract["locked_unknowns"]), 3)
        locked = " ".join(self.contract["locked_unknowns"])
        self.assertIn("under-Pyramid areas outside the bounded circulation blockout", locked)
        self.assertIn("Richelieu, Sully, and Denon gallery rooms", locked)
        self.assertIn("central tube lift's exact placement", locked)

    def test_built_files_and_source_inputs_are_hash_pinned(self) -> None:
        manifest = self.pinned_manifest
        self.assertEqual(
            manifest["manifest_kind"],
            "solo_review_code_pinned_notebook_world_build",
        )
        self.assertEqual(manifest["status"], "prototype_draft_not_final_not_approved")
        self.assertEqual(
            manifest["launch_url"],
            "http://127.0.0.1:5183/?solo=1&bookmark=arrival_scale",
        )
        self.assertEqual(
            [bookmark["id"] for bookmark in manifest["review_bookmarks"]],
            [bookmark["id"] for bookmark in self.contract["review_bookmarks"]],
        )
        for item in manifest["source_inputs"] + manifest["served_files"]:
            with self.subTest(path=item["path"]):
                path = ROOT / item["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, item["bytes"])
                self.assertEqual(sha256_file(path), item["sha256"])

        pinned_source_paths = {item["path"] for item in manifest["source_inputs"]}
        self.assertIn(
            "Data/world_access/tardis_notebook_world_gateway.json",
            pinned_source_paths,
        )
        self.assertIn(
            "System/Docs/LOUVRE_BOUNDED_CIRCULATION_OWNER_REVIEW_v2.md",
            pinned_source_paths,
        )

        dist = PREVIEW / "dist"
        actual = {path.resolve() for path in dist.rglob("*") if path.is_file()}
        pinned = {Path(ROOT / item["path"]).resolve() for item in manifest["served_files"]}
        self.assertEqual(actual, pinned)

    def test_launcher_is_read_only_loopback_and_forces_solo_query(self) -> None:
        self.assertTrue(LAUNCHER_PATH.is_file())
        self.assertIn('LOOPBACK_HOST = "127.0.0.1"', self.server_source)
        self.assertIn('set(query).issubset({"solo", "bookmark"})', self.server_source)
        self.assertIn('bookmark_values[0] in allowed_bookmarks', self.server_source)
        self.assertIn('self.send_header("Location", "/?solo=1&bookmark=arrival_scale")', self.server_source)
        self.assertIn("def do_POST", self.server_source)
        self.assertIn("This solo-review server is read-only", self.server_source)
        self.assertNotIn("TemporaryAI/", self.server_source)
        self.assertNotIn("kira_world_shell_server", self.server_source)

    def test_launcher_waits_for_exact_health_before_opening_browser(self) -> None:
        launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertIn("launch_louvre_solo_notebook_world_test.py", launcher)
        self.assertNotIn("serve_louvre_solo_notebook_world_test.py", launcher)
        self.assertIn('if requested_path == "/healthz":', self.server_source)
        self.assertIn('"service": "louvre_solo_owner_review"', self.server_source)
        self.assertIn('HEALTH_PROTOCOL = "louvre_bounded_circulation_owner_review_r4"', self.server_source)
        self.assertIn('EXPECTED_PROTOCOL = "louvre_bounded_circulation_owner_review_r4"', self.launch_supervisor_source)
        self.assertIn('EXPECTED_BUILD_ID = "louvre_owner_review_20260716_r4_bounded_circulation"', self.launch_supervisor_source)
        self.assertIn("wait_for_health", self.launch_supervisor_source)
        waited_at = self.launch_supervisor_source.index("wait_for_health(args.port")
        self.assertLess(
            waited_at,
            self.launch_supervisor_source.index("webbrowser.open(url)", waited_at),
        )
        self.assertIn("people_loaded", self.launch_supervisor_source)
        self.assertIn("minds_loaded", self.launch_supervisor_source)

    def test_tardis_lists_only_the_safe_owner_review_scope(self) -> None:
        destination = self.tardis_destination
        self.assertEqual(destination["listing_mode"], "owner_review_destination_not_finished_world_area")
        self.assertEqual(destination["allowed_caller"], "robert_avatar")
        self.assertTrue(destination["travel_ready_for_owner_solo_review"])
        self.assertFalse(destination["travel_ready_for_activated_people"])
        self.assertFalse(destination["runtime_registered_as_complete"])
        self.assertTrue(destination["review_capabilities"]["approximate_two_leaf_door_animation_and_collision_test"])
        self.assertTrue(destination["review_capabilities"]["approximate_two_way_walkable_spiral_stair_blockout"])
        self.assertTrue(destination["review_capabilities"]["visible_only_non_operable_escalator_blockout"])
        self.assertEqual(destination["query_contract"]["solo"], "1")
        self.assertEqual(destination["query_contract"]["bookmark"], "arrival_scale")
        self.assertTrue(all(value is False for value in destination["completion"].values() if isinstance(value, bool)))
        listed = self.tardis_gateway["interior_console"]["owner_review_destinations"]
        self.assertEqual([item["destination_id"] for item in listed], ["louvre_solo_owner_review"])
        self.assertIn("Louvre approximate Pyramid circulation review (draft)", self.main_js)
        self.assertIn("ownerReviewOnly: true", self.main_js)
        self.assertIn('solo: "1", bookmark: "arrival_scale"', self.main_js)
        self.assertIn('f"http://127.0.0.1:{WORLD_PORT}/?area=louvre&solo=1"', self.shell_server_source)
        self.assertIn('"&bookmark=arrival_scale&caller=robert_avatar"', self.shell_server_source)
        self.assertIn("bounded approximate Pyramid door/spiral-descent review", listed[0]["listing_truth"])

    def test_streaming_contract_loads_only_the_bounded_review_slice(self) -> None:
        contract = self.streaming_contract
        self.assertFalse(contract["truth"]["interior_complete"])
        self.assertFalse(contract["truth"]["elevators_proven"])
        self.assertFalse(contract["truth"]["gallery_rooms_proven"])
        loadable = [cell["id"] for cell in contract["cells"] if cell["runtime_loadable"]]
        self.assertEqual(
            loadable,
            [
                "cour_napoleon_exterior",
                "pyramid_entrance_transition",
                "under_pyramid_level_minus_2_circulation",
            ],
        )
        plan = plan_interest(contract, [(0, 1.68, 62)])
        self.assertEqual(plan.desired_cells, ("cour_napoleon_exterior",))
        door_plan = plan_interest(contract, [(0, 1.68, 34)])
        self.assertEqual(
            door_plan.desired_cells,
            ("cour_napoleon_exterior", "pyramid_entrance_transition"),
        )
        threshold_without_authorization = plan_interest(contract, [(0, 1.68, 17)])
        self.assertNotIn(
            "under_pyramid_level_minus_2_circulation",
            threshold_without_authorization.desired_cells,
        )
        threshold_plan = plan_interest(
            contract,
            [(0, 1.68, 17)],
            authorized_cells=("under_pyramid_level_minus_2_circulation",),
        )
        self.assertEqual(set(threshold_plan.desired_cells), set(loadable))
        self.assertIn("transactional_preload_before_unload", self.streaming_runtime)
        self.assertIn("state_preserved_across_reload", self.streaming_runtime)
        self.assertIn("blocked_before_source_unload", self.streaming_runtime)
        self.assertIn("Locked/unbuilt Louvre cell cannot register", self.streaming_runtime)
        self.assertIn("createLouvreCellStreamingScaffold", self.main_js)
        self.assertIn("createApproximatePyramidEntranceCell", self.main_js)
        self.assertIn("createApproximateUnderPyramidCirculationCell", self.main_js)
        self.assertIn("visible-only approximate escalator blockout - non-operable", self.main_js)
        self.assertNotIn("louvre_runtime_kind = \"elevator\"", self.main_js)


if __name__ == "__main__":
    unittest.main()
