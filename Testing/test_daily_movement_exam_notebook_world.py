from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from serve_daily_movement_exam_notebook_world import bind_server, verify_pinned_build  # noqa: E402
from verify_daily_movement_exam_notebook_world import read_program, verify_program  # noqa: E402


BUILD = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "daily_movement_exam_notebook_world"
    / "builds"
    / "notebook_world_daily_movement_exam_20260717_160706"
)


class DailyMovementExamNotebookWorldTests(unittest.TestCase):
    def test_static_exam_contract_and_every_route_pass(self) -> None:
        result = verify_program(read_program())
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["primitive_count"], 52)
        self.assertEqual(result["material_count"], 15)
        self.assertEqual(result["collider_count"], 16)
        self.assertEqual(result["route_count"], 9)
        self.assertEqual(result["station_count"], 8)
        self.assertTrue(all(route["passed"] for route in result["route_results"]))

    def test_pinned_build_is_zero_person_and_has_no_model_binding(self) -> None:
        verified = verify_pinned_build()
        self.assertEqual(verified.world_id, "daily_movement_exam_notebook_world")
        self.assertEqual(
            verified.request_id,
            "notebook_world_daily_movement_exam_20260717_160706",
        )
        self.assertNotIn("model_asset", verified.role_paths)
        self.assertIn("/data/scene_program.json", verified.served_urls)
        self.assertIn("/vendor/three/build/three.core.js", verified.served_urls)
        self.assertIn("/vendor/three/examples/jsm/controls/PointerLockControls.js", verified.served_urls)

        registration = verified.registration
        for key in (
            "loads_person_assets",
            "loads_kira_body",
            "loads_kira_mind",
            "loads_voice",
            "loads_ollama",
            "loads_second_person",
            "modifies_home_world",
            "runtime_registered",
            "body_skill_execution_allowed",
        ):
            self.assertIs(registration[key], False, key)
        self.assertIs(registration["owner_camera_walk_only"], True)
        self.assertIs(registration["route_probe_is_a_person"], False)

    def test_runtime_and_owner_approval_remain_blocked(self) -> None:
        approval = json.loads((BUILD / "approval_gate.json").read_text(encoding="utf-8"))
        resource = json.loads(
            (BUILD / "resource_isolation_gate.json").read_text(encoding="utf-8")
        )
        quality = json.loads((BUILD / "quality_gate.json").read_text(encoding="utf-8"))
        program = read_program()

        self.assertIs(approval["world_builder_may_commit_to_world"], False)
        self.assertIs(approval["world_builder_may_import_to_home_world"], False)
        self.assertIs(approval["requires_robert_approval"], True)
        self.assertIs(resource["notebook_world_runtime_started"], False)
        self.assertIs(resource["loads_kira_body"], False)
        self.assertIs(resource["loads_kira_mind"], False)
        self.assertIs(resource["loads_voice"], False)
        self.assertEqual(quality["gates"]["runtime_route"], "blocked")
        self.assertEqual(quality["gates"]["explicit_robert_approval"], "blocked")
        self.assertEqual(program["status"], "prototype_draft")

    def test_preview_truthfully_labels_the_probe_and_no_person_state(self) -> None:
        html = (BUILD / "preview" / "index.html").read_text(encoding="utf-8")
        script = (BUILD / "preview" / "main.js").read_text(encoding="utf-8")
        self.assertIn("ZERO PEOPLE LOADED", html)
        self.assertIn("clearance probe, not Kira", html)
        self.assertIn("peopleLoaded: 0", script)
        self.assertIn("mindsLoaded: 0", script)
        self.assertIn("voiceLoaded: false", script)
        self.assertIn("homeWorldLoaded: false", script)
        self.assertIn("personActivationAllowed: false", script)
        self.assertIn("bodySkillExecutionAllowed: false", script)

    def test_loopback_server_serves_only_manifest_bound_files(self) -> None:
        server, port = bind_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{port}"
            with urlopen(f"{base}/index.html", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"ZERO PEOPLE LOADED", response.read())
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            with urlopen(f"{base}/data/scene_program.json", timeout=5) as response:
                scene_program = json.loads(response.read().decode("utf-8"))
                self.assertEqual(scene_program["world_id"], "daily_movement_exam_notebook_world")
                self.assertIs(scene_program["isolation"]["person_assets_loaded"], False)
            with self.assertRaises(HTTPError) as forbidden:
                urlopen(f"{base}/registration.json", timeout=5)
            self.assertEqual(forbidden.exception.code, 404)
            forbidden.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
