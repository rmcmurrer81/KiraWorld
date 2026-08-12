import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import build_legal_day_spa_preview_20260714 as spa  # noqa: E402


class LegalDaySpaBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection_report = spa.build_asset_selection_report()
        cls.scene = spa.build_scene(cls.selection_report)
        cls.report = spa.validate_static_routes(cls.scene)

    def test_wall_geometry_is_deterministic_and_every_door_has_an_aperture(self) -> None:
        second_scene = spa.build_scene()
        self.assertEqual(self.scene["wall_runs"], second_scene["wall_runs"])
        self.assertEqual(self.scene["walls"], second_scene["walls"])
        self.assertEqual(self.scene["doors"], second_scene["doors"])
        self.assertEqual(spa.door_wall_overlaps(self.scene), [])
        self.assertEqual({door["orientation"] for door in self.scene["doors"]}, {"along_x", "along_z"})
        declared_openings = {
            door_id
            for wall_run in self.scene["wall_runs"]
            for door_id in wall_run["openings"]
        }
        self.assertEqual(declared_openings, {door["id"] for door in self.scene["doors"]})

    def test_every_interaction_and_door_approach_target_has_capsule_clearance(self) -> None:
        self.assertEqual(spa.target_clearance_failures(self.scene, spa.AVATAR_RADIUS_METERS), [])

    def test_open_and_closed_door_semantics_are_real(self) -> None:
        self.assertEqual(len(self.report["door_state_tests"]), len(self.scene["doors"]))
        for row in self.report["door_state_tests"]:
            with self.subTest(door=row["door_id"]):
                self.assertEqual(row["status"], "passed")
                self.assertEqual(row["open_crossing"], "passed")
                self.assertEqual(row["closed_crossing"], "blocked_as_expected")
                self.assertEqual(row["open_threshold_center"], "clear")
                self.assertEqual(row["closed_threshold_center"], "blocked_as_expected")

    def test_round_trips_cover_every_public_room(self) -> None:
        self.assertEqual(self.report["static_validation_status"], "passed")
        self.assertEqual(self.report["failures"], [])
        self.assertEqual(self.report["public_room_coverage"]["uncovered_rooms"], [])
        self.assertGreaterEqual(len(self.report["round_trip_routes"]), 10)
        for row in self.report["round_trip_routes"]:
            with self.subTest(route=row["route_id"]):
                self.assertEqual(row["status"], "passed_round_trip")
                self.assertEqual(row["forward"]["status"], "passed_static_capsule_path")
                self.assertEqual(row["reverse"]["status"], "passed_static_capsule_path")
                self.assertTrue(row["forward"]["path"])
                self.assertTrue(row["reverse"]["path"])
                self.assertEqual(row["runtime_kira_test"], "not_run")
        self.assertEqual(self.report["runtime_kira_test"], "not_run")
        self.assertFalse(self.report["ready_for_approval"])

    def test_required_structural_artifacts_and_gate_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            out_dir = project_dir / "preview_builds" / "test_build"
            spa.write_json(project_dir / "latest_preview_build.json", {
                "build_id": "prior_failed_build",
                "status": "staged_preview_failed_robert_realism_review",
                "robert_review": "prior/robert_review_failed.json",
            })
            result = spa.build_preview_artifacts(
                out_dir,
                project_dir=project_dir,
                build_id="test_build",
                update_latest=True,
            )

            required_files = [
                out_dir / "index.html",
                out_dir / "scene_data.json",
                out_dir / "floorplan.svg",
                out_dir / "blueprint.json",
                project_dir / "blueprint.json",
                out_dir / "ai_route_test_report.json",
                out_dir / "nav_collision_report.json",
                out_dir / "approval_gate.json",
            ]
            self.assertTrue(all(path.is_file() for path in required_files))

            route_report = json.loads((out_dir / "ai_route_test_report.json").read_text(encoding="utf-8"))
            nav_report = json.loads((out_dir / "nav_collision_report.json").read_text(encoding="utf-8"))
            gate = json.loads((out_dir / "approval_gate.json").read_text(encoding="utf-8"))
            latest = json.loads((project_dir / "latest_preview_build.json").read_text(encoding="utf-8"))
            self.assertEqual(route_report["static_validation_status"], "passed")
            self.assertEqual(nav_report["runtime_kira_test"], "not_run")
            self.assertFalse(nav_report["ready_for_approval"])
            self.assertEqual(gate["status"], "not_approved")
            self.assertFalse(gate["world_builder_may_commit_to_home_world"])
            self.assertEqual(gate["runtime_kira_route_test"], "not_run")
            self.assertEqual(gate["robert_approval"], "not_granted")
            self.assertEqual(gate["prior_failed_review"]["build_id"], "prior_failed_build")
            self.assertEqual(latest["status"], "staged_preview_not_approved")
            self.assertTrue(latest["not_placed_in_home_world"])
            self.assertEqual(result["latest"], latest)

    def test_asset_selection_report_records_library_queries_and_pinned_real_prefabs(self) -> None:
        report = self.selection_report
        query = report["library_query"]
        expected_roles = {
            "waiting_sofa",
            "consultation_chair",
            "restroom_toilet",
            "restroom_sink_cabinet",
            "waiting_coffee_table",
        }

        self.assertEqual(
            query["query_order"],
            ["component_library", "item_prefab_library", "controlled_project_descriptor_if_unindexed"],
        )
        for library_name in ("component_library", "item_prefab_library"):
            with self.subTest(library=library_name):
                library = query[library_name]
                self.assertTrue((PROJECT_ROOT / library["path"]).is_file())
                self.assertTrue(library["generated_at"])
                self.assertGreater(library["source_count"], 0)
                self.assertGreater(library["prefab_count"], 0)
        self.assertEqual(query["item_prefab_library"]["error_count"], 0)

        selections = {row["role"]: row for row in report["selections"]}
        queries = {row["role"]: row for row in query["queries"]}
        self.assertEqual(set(selections), expected_roles)
        self.assertEqual(set(queries), expected_roles)
        self.assertEqual(report["selected_count"], len(expected_roles))
        self.assertEqual(report["failed_selection_count"], 0)
        self.assertFalse(report["home_world_modified"])

        for role, selection in selections.items():
            with self.subTest(role=role):
                role_query = queries[role]
                self.assertEqual(selection["status"], "selected_real_prefab")
                self.assertEqual(selection["render_mode"], "real_prefab")
                self.assertEqual(selection["load_failure_status"], "failed_missing_real_prefab")
                self.assertTrue(selection["no_block_fallback"])
                self.assertEqual(selection["failures"], [])
                self.assertEqual(selection["source_sha256"], selection["expected_sha256"])
                self.assertRegex(selection["source_sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue((PROJECT_ROOT / selection["source"]).is_file())
                self.assertTrue(selection["source_url"].startswith("/Data/world_builder/"))
                self.assertEqual(role_query["requested_prefab_id"], selection["prefab_id"])
                self.assertEqual(role_query["requested_tags"], selection["requested_tags"])
                self.assertEqual(role_query["query_order"][:2], ["component_library", "item_prefab_library"])
                if selection["selection_stage"] == "item_prefab_library_after_component_query":
                    self.assertIn(selection["prefab_id"], role_query["item_candidate_ids"])
                    self.assertGreater(role_query["item_candidate_count"], 0)
                else:
                    self.assertEqual(
                        selection["selection_stage"],
                        "controlled_project_descriptor_after_current_library_query",
                    )
                    self.assertEqual(role_query["query_order"][-1], "controlled_project_descriptor")
                    self.assertEqual(role_query["current_library_result"], "recent_candidate_not_indexed")

    def test_real_prefab_visuals_have_no_block_or_proxy_fallback_render_path(self) -> None:
        instances = self.scene["asset_instances"]
        proxies = {row["name"]: row for row in self.scene["collision_proxies"]}

        self.assertEqual(self.scene["furniture"], [])
        self.assertEqual(len(instances), 6)
        self.assertEqual(
            {row["role"] for row in instances},
            {
                "waiting_sofa",
                "consultation_chair",
                "restroom_toilet",
                "restroom_sink_cabinet",
                "waiting_coffee_table",
            },
        )
        for instance in instances:
            with self.subTest(instance=instance["id"]):
                self.assertEqual(instance["status"], "selected_real_prefab")
                self.assertEqual(instance["render_mode"], "real_prefab")
                self.assertFalse(instance["solid"])
                self.assertTrue(instance["uniform_box3_fit"])
                self.assertTrue(instance["bottom_align"])
                self.assertTrue(instance["no_block_fallback"])
                self.assertEqual(instance["load_failure_status"], "failed_missing_real_prefab")
                self.assertEqual(instance["selector"], {"kind": "scene_root"})
                self.assertIn(instance["collision_proxy_id"], proxies)
                self.assertEqual(proxies[instance["collision_proxy_id"]]["asset_role"], instance["role"])

        for proxy in proxies.values():
            with self.subTest(proxy=proxy["name"]):
                self.assertEqual(proxy["kind"], "collision_proxy")
                self.assertFalse(proxy["visual"])
                self.assertEqual(proxy["render_mode"], "never_render_static_validation_only")
        for fixture in self.scene["code_native_fixtures"]:
            self.assertEqual(fixture["status"], "purpose_built_code_native")

        html = spa.HTML_TEMPLATE
        self.assertIn('import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";', html)
        self.assertIn("Promise.all(sceneData.asset_instances.map(loadRealPrefab))", html)
        self.assertIn('status: instance.load_failure_status || "failed_missing_real_prefab"', html)
        self.assertIn("Deliberately no primitive, colored-block, or semantic fallback", html)
        self.assertIn("window.spaReview.ready = true", html)
        self.assertIn("loadPromise: assetLoadPromise", html)
        self.assertIn("snapshot: () => ({", html)
        self.assertNotIn("sceneData.furniture", html)
        self.assertNotIn("for (const proxy of sceneData.collision_proxies)", html)

    def test_missing_asset_report_leaves_required_roles_visually_empty(self) -> None:
        expected_missing_roles = {
            "front_storefront_door",
            "reception_counter",
            "consultation_desk_tablet",
            "treatment_table_a",
            "treatment_table_b",
            "treatment_room_stools",
            "treatment_side_counters_and_sinks",
            "styling_salon_chair",
            "styling_shampoo_basin",
            "styling_mirror",
            "relaxation_lounges",
            "clean_towel_storage",
            "dirty_linen_hamper",
            "laundry_machines",
            "staff_utility_sink",
            "accessible_grab_rails",
            "spa_ceiling_light_fixtures",
        }
        missing_report = spa.missing_asset_report(self.selection_report)
        missing = {row["role"]: row for row in missing_report["missing_assets"]}
        selected_roles = {
            row["role"]
            for row in self.selection_report["selections"]
            if row["status"] == "selected_real_prefab"
        }

        self.assertEqual(set(missing), expected_missing_roles)
        self.assertEqual(
            {row["role"] for row in self.scene["missing_asset_roles"]},
            expected_missing_roles,
        )
        self.assertTrue(selected_roles.isdisjoint(expected_missing_roles))
        self.assertTrue(
            {row["role"] for row in self.scene["asset_instances"]}.isdisjoint(expected_missing_roles)
        )
        for role, row in missing.items():
            with self.subTest(role=role):
                self.assertEqual(row["status"], "failed_missing_real_prefab")
                self.assertFalse(row["visual_created"])
                self.assertIsNone(row["source"])
                self.assertIsNone(row["prefab_id"])
                self.assertTrue(row["reason"])
                self.assertFalse(row["block_fallback_allowed"])

        self.assertEqual(missing_report["status"], "failed_missing_real_prefabs_visual_gate_unresolved")
        self.assertFalse(missing_report["visual_gate_passed"])
        self.assertFalse(missing_report["approval_ready"])
        self.assertEqual(
            missing_report["forbidden_substitutions"],
            self.selection_report["forbidden_substitutions"],
        )

    def test_collision_proxies_preserve_exact_door_and_round_trip_results(self) -> None:
        proxy_by_name = {row["name"]: row for row in self.scene["collision_proxies"]}
        obstacle_names = {row["name"] for row in spa._solid_obstacles(self.scene)}
        expected_obstacles = {
            row["name"] for row in [*self.scene["walls"], *self.scene["collision_proxies"]]
        }
        nav = spa.nav_report(self.scene, self.report)

        self.assertEqual(obstacle_names, expected_obstacles)
        for instance in self.scene["asset_instances"]:
            with self.subTest(instance=instance["id"]):
                proxy = proxy_by_name[instance["collision_proxy_id"]]
                self.assertEqual(proxy["asset_role"], instance["role"])
                self.assertEqual(proxy["asset_status"], "selected_real_prefab")
                self.assertFalse(proxy["visual"])

        self.assertEqual(len(self.scene["doors"]), 11)
        self.assertEqual(len(self.report["door_state_tests"]), 11)
        self.assertTrue(all(row["status"] == "passed" for row in self.report["door_state_tests"]))
        self.assertEqual(len(self.scene["public_route_tests"]), 12)
        self.assertEqual(len(self.report["round_trip_routes"]), 12)
        self.assertTrue(
            all(row["status"] == "passed_round_trip" for row in self.report["round_trip_routes"])
        )
        self.assertEqual(self.report["door_wall_overlap_failures"], [])
        self.assertEqual(self.report["target_clearance_failures"], [])
        self.assertEqual(self.report["failures"], [])
        self.assertEqual(self.report["static_validation_status"], "passed")
        self.assertEqual(nav["door_count"], 11)
        self.assertEqual(nav["door_state_tests_passed"], 11)
        self.assertEqual(nav["round_trip_routes_required"], 12)
        self.assertEqual(nav["round_trip_routes_passed"], 12)

    def test_asset_credits_and_approval_gate_preserve_attribution_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            out_dir = project_dir / "preview_builds" / "real_prefab_test"
            spa.write_json(project_dir / "latest_preview_build.json", {
                "build_id": "prior_failed_build",
                "status": "staged_preview_failed_robert_realism_review",
                "robert_review": "prior/robert_review_failed.json",
            })
            result = spa.build_preview_artifacts(
                out_dir,
                project_dir=project_dir,
                build_id="real_prefab_test",
                update_latest=True,
            )

            report_paths = {
                "asset_selection_report.json": out_dir / "asset_selection_report.json",
                "asset_credits.json": out_dir / "asset_credits.json",
                "missing_asset_report.json": out_dir / "missing_asset_report.json",
            }
            self.assertTrue(all(path.is_file() for path in report_paths.values()))
            selection = json.loads(report_paths["asset_selection_report.json"].read_text(encoding="utf-8"))
            credits = json.loads(report_paths["asset_credits.json"].read_text(encoding="utf-8"))
            missing = json.loads(report_paths["missing_asset_report.json"].read_text(encoding="utf-8"))
            gate = json.loads((out_dir / "approval_gate.json").read_text(encoding="utf-8"))
            latest = json.loads((project_dir / "latest_preview_build.json").read_text(encoding="utf-8"))

            selected_rows = [row for row in selection["selections"] if row["status"] == "selected_real_prefab"]
            selected_shas = {row["source_sha256"] for row in selected_rows}
            credits_by_sha = {row["source_sha256"]: row for row in credits["credits"]}
            self.assertEqual(set(credits_by_sha), selected_shas)
            self.assertEqual(len(credits_by_sha), len(credits["credits"]))
            for sha, credit in credits_by_sha.items():
                with self.subTest(credit=sha):
                    matching = [row for row in selected_rows if row["source_sha256"] == sha]
                    self.assertRegex(sha, r"^[0-9a-f]{64}$")
                    self.assertTrue((PROJECT_ROOT / credit["local_source"]).is_file())
                    self.assertTrue(credit["source_url"].startswith("https://"))
                    self.assertTrue(credit["author"])
                    self.assertTrue(credit["author_url"].startswith("https://"))
                    self.assertEqual(credit["license"], "CC-BY-4.0")
                    self.assertEqual(credit["license_url"], spa.LICENSE_URL)
                    self.assertEqual(set(credit["roles"]), {row["role"] for row in matching})
                    self.assertEqual(
                        set(credit["prefab_ids"]),
                        {row["prefab_id"] for row in matching if row.get("prefab_id")},
                    )

            artifact_status = {row["artifact"]: row["status"] for row in gate["required_artifacts"]}
            self.assertTrue(
                all(artifact_status[name] == "present" for name in report_paths)
            )
            failure_by_kind = {row["kind"]: row for row in gate["failures"]}
            self.assertIn("missing_required_real_prefabs", failure_by_kind)
            self.assertIn("prior_failed_visual_realism_review_unresolved", failure_by_kind)
            self.assertFalse(
                failure_by_kind["missing_required_real_prefabs"]["fallback_visuals_created"]
            )
            self.assertEqual(
                set(failure_by_kind["missing_required_real_prefabs"]["roles"]),
                {row["role"] for row in missing["missing_assets"]},
            )
            self.assertEqual(gate["status"], "not_approved")
            self.assertFalse(gate["world_builder_may_commit_to_home_world"])
            self.assertEqual(gate["structural_static_validation"], "passed")
            self.assertEqual(gate["runtime_kira_route_test"], "not_run")
            self.assertEqual(gate["robert_approval"], "not_granted")
            self.assertEqual(gate["visual_realism_review"], "failed_prior_review_unresolved")
            self.assertTrue(gate["requirements"]["requires_all_semantic_real_prefabs"])
            self.assertEqual(gate["prior_failed_review"]["build_id"], "prior_failed_build")
            self.assertEqual(latest["status"], "staged_preview_not_approved")
            self.assertTrue(latest["not_placed_in_home_world"])
            self.assertEqual(result["approval_gate"], gate)


if __name__ == "__main__":
    unittest.main()
