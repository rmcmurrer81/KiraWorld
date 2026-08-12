from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_PREVIEW = ROOT / "Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview"
HOME_SOURCE = HOME_PREVIEW / "src/main.js"
HOME_INDEX = HOME_PREVIEW / "index.html"
SHELL_SOURCE = ROOT / "tools/kira_world_shell_server.py"
POLICY = ROOT / "Data/world_builds/notebook_worlds/home_world/config/legacy_strip_mall_runtime_policy_20260716.json"
AUDIT = ROOT / "Data/world_builder/audits/home_world_strip_mall_cost_audit_20260716.json"
COLLECTION = ROOT / "Data/world_builds/notebook_collections/education_notebook_collection_20260716"
CORE = ROOT / "Data/world_builds/notebook_worlds/college_campus_core_notebook_world/builds/notebook_world_college_campus_20260716_021505"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class HomeWorldEmptyLotPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = HOME_SOURCE.read_text(encoding="utf-8")

    def test_legacy_source_is_opt_in_and_default_startup_skips_construction(self) -> None:
        self.assertIn('const HOME_WORLD_LEGACY_STRIP_MALL_ENABLED = params.get("stripMall") === "1";', self.source)
        self.assertEqual(self.source.count("addStripMall();"), 1)
        self.assertRegex(
            self.source,
            r"if \(HOME_WORLD_LEGACY_STRIP_MALL_ENABLED\) \{\s*addStripMall\(\);\s*\} else \{",
        )
        self.assertIn('mode: "empty_lot_default"', self.source)
        self.assertIn('sourceDeleted: false', self.source)
        self.assertIn('spaPlacedHere: false', self.source)

    def test_disabled_named_place_has_no_building_or_door_affordance(self) -> None:
        disabled_place = re.search(
            r'if \(!HOME_WORLD_LEGACY_STRIP_MALL_ENABLED\) \{\s*return activeAvatarPlaceEntry\("empty former strip-mall lot"(.+?)\n\s*\}\s*return activeAvatarPlaceEntry\("strip mall shopfront"',
            self.source,
            re.DOTALL,
        )
        self.assertIsNotNone(disabled_place)
        block = disabled_place.group(1)
        self.assertIn('category: "empty_lot"', block)
        self.assertIn('nearDoor: false', block)
        self.assertIn('canEnter: false', block)

    def test_policy_and_audit_preserve_source_without_placing_spa(self) -> None:
        policy = load_json(POLICY)
        audit = load_json(AUDIT)
        self.assertEqual(policy["default_runtime_state"], "empty_lot")
        self.assertFalse(policy["legacy_source_deleted"])
        self.assertEqual(policy["restore_switch"], "?stripMall=1")
        self.assertFalse(policy["spa_placed_on_site"])
        estimate = policy["source_expansion_estimate_if_restored"]
        self.assertEqual(estimate["procedural_mesh_objects"], 128)
        self.assertEqual(estimate["static_colliders"], 37)
        self.assertEqual(estimate["door_colliders"], 5)
        self.assertEqual(estimate["interaction_zones"], 6)
        self.assertEqual(estimate["canvas_sign_textures"], 5)
        self.assertEqual(audit["status"], "static_audit_complete_live_ab_not_run")
        self.assertFalse(audit["method"]["browser_started"])
        self.assertFalse(audit["method"]["live_gpu_vram_measured"])

    def test_shell_and_preview_describe_the_default_empty_site_truthfully(self) -> None:
        shell = SHELL_SOURCE.read_text(encoding="utf-8")
        index = HOME_INDEX.read_text(encoding="utf-8")
        self.assertIn("empty former strip-mall lot", shell)
        self.assertIn("There is no shopfront or door to enter by default", shell)
        self.assertIn("The spa is a separate notebook world", shell)
        self.assertIn("former strip-mall site is intentionally empty by default", index)
        self.assertIn("?stripMall=1", index)

    def test_current_production_bundle_contains_new_runtime_policy(self) -> None:
        bundles = list((HOME_PREVIEW / "dist/assets").glob("index-*.js"))
        self.assertEqual(len(bundles), 1)
        bundle = bundles[0].read_text(encoding="utf-8")
        self.assertIn("empty former strip-mall lot", bundle)
        self.assertIn("no_exit_intent_at_review", bundle)
        self.assertIn("?stripMall=1", bundle)


class PersistentQuietReadingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = HOME_SOURCE.read_text(encoding="utf-8")

    def test_long_reading_policy_is_voluntary_persistent_and_chat_safe(self) -> None:
        self.assertIn("initialReviewSeconds: 8 * 60 * 60", self.source)
        self.assertIn("continuationReviewSeconds: 4 * 60 * 60", self.source)
        self.assertIn("minimumSelfChosenSeconds: 4 * 60 * 60", self.source)
        self.assertIn("chatDoesNotEndActivity: true", self.source)
        self.assertIn("explicit_new_embodied_intent_or_voluntary_exit_only", self.source)
        self.assertIn("quiet_activity_chat_interruption_preserved", self.source)
        self.assertIn("no_exit_intent_at_review", self.source)
        self.assertIn("quiet_activity_voluntary_exit", self.source)

    def test_long_reading_walks_to_couch_without_hold_teleport(self) -> None:
        self.assertIn("function startActiveAvatarPersistentHomeRead", self.source)
        self.assertIn('startActiveAvatarPracticeRouteSkill("walk_to_persistent_couch_reading"', self.source)
        self.assertIn('teleported: false', self.source)
        self.assertNotIn("activeMarker.position.copy(skill.position)", self.source)
        self.assertIn("positionLockedByTeleport: false", self.source)

    def test_tablet_and_support_truth_are_preserved_and_observable(self) -> None:
        self.assertIn('heldPropKind: "tablet"', self.source)
        self.assertIn("if (skill.heldPropKind) setActiveHeldProp(skill.heldPropKind);", self.source)
        self.assertIn("id: skill.postureState.surface", self.source)
        self.assertGreaterEqual(self.source.count("persistentQuietActivity: persistentQuietActivitySnapshot()"), 3)
        self.assertIn("quietActivityState()", self.source)
        self.assertIn("continueQuietActivity(hours = 4)", self.source)
        self.assertIn("exitQuietActivity(reason = \"voluntary_debug_exit\")", self.source)


class MemorialUnionPlanningTests(unittest.TestCase):
    def test_program_is_complete_planning_only_and_excludes_private_memory(self) -> None:
        plan = load_json(COLLECTION / "memorial_union_student_center_plan.json")
        self.assertEqual(plan["status"], "planning_only_no_scene_built")
        self.assertFalse(plan["truth_boundary"]["real_memorial_union_geometry_claimed"])
        self.assertFalse(plan["truth_boundary"]["private_memory_geometry_allowed"])
        public_zones = {item["zone"] for item in plan["public_program"]}
        self.assertTrue({
            "arrival_information_and_wayfinding",
            "food_hall",
            "college_store",
            "lounges_and_study",
            "meetings_events_and_student_organizations",
            "student_services",
        }.issubset(public_zones))
        operations = plan["operational_support_program"]
        self.assertIn("receiving and loading", operations["food_service_back_of_house"])
        self.assertIn("custodial closets on each public level", operations["building_operations"])
        self.assertIn("code-reviewed exits and occupant loads", operations["public_health_access_and_safety"])
        self.assertFalse(plan["resource_and_build_policy"]["co_load_with_kira_mind_or_body"])
        self.assertFalse(plan["resource_and_build_policy"]["preview_allowed_now"])

    def test_core_and_collection_link_the_memorial_union_plan(self) -> None:
        manifest = load_json(COLLECTION / "collection_manifest.json")
        arrangement = load_json(COLLECTION / "college_campus_arrangement.json")
        request = load_json(CORE / "notebook_world_request.json")
        scene = load_json(CORE / "scene_plan.json")
        self.assertEqual(manifest["planning_artifacts"][0]["status"], "planning_only_no_scene_built")
        self.assertIn("Memorial Union", manifest["members"][0]["scope"])
        self.assertIn("Memorial Union college store", arrangement["member_order"][0]["zones"])
        self.assertIn("memorial_union_program_plan_path", request["world_plan"])
        layer = next(item for item in scene["build_layers"] if item["layer"] == "memorial_union_student_center_program")
        self.assertEqual(layer["status"], "planning_only_waiting_for_public_sources_program_review_and_blueprint")
        self.assertFalse(layer["private_memory_geometry_used"])


if __name__ == "__main__":
    unittest.main()
