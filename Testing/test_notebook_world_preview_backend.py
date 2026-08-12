from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import create_world_notebook_request as generator  # noqa: E402
from notebook_world_preview_backend import (  # noqa: E402
    AUTHORIZATION_KIND,
    AUTHORIZATION_STATUS,
    BACKEND_ID,
    HARD_BUDGET,
    PreviewBuildError,
    authorization_binding,
    build_authorized_preview,
)
from serve_pinned_notebook_world_preview import PreviewLaunchConfig, bind_server, verify_generated_preview  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sample_program(world_id: str, request_id: str) -> dict:
    budget = dict(HARD_BUDGET)
    budget.update(
        {
            "max_meshes": 12,
            "max_materials": 8,
            "max_lights": 3,
            "max_triangles": 1000,
            "max_colliders": 8,
            "max_routes": 4,
            "max_route_points": 24,
            "max_rooms": 3,
            "max_spawns": 4,
            "max_cameras": 4,
            "max_filming_marks": 6,
            "max_overlays": 3,
            "max_generated_payload_bytes": 2_000_000,
        }
    )
    return {
        "schema_version": 1,
        "program_kind": "strict_v2_procedural_notebook_world_preview",
        "world_id": world_id,
        "request_id": request_id,
        "status": "prototype_draft",
        "title": "Synthetic preview fixture",
        "subtitle": "One tiny generated room for backend tests.",
        "units": "meters",
        "world_bounds": {"min": [-5, -1, -5], "max": [5, 6, 5]},
        "scene_budget": budget,
        "environment": {
            "background_color": "#112233",
            "fog_color": "#112233",
            "fog_near": 8,
            "fog_far": 35,
        },
        "materials": [
            {
                "id": "floor_material",
                "color": "#334455",
                "roughness": 0.9,
                "metalness": 0.0,
                "opacity": 1.0,
                "truth_label": "style_fill",
                "source_note": "Original lightweight test material.",
            },
            {
                "id": "spawn_material",
                "color": "#55ccaa",
                "roughness": 0.6,
                "metalness": 0.0,
                "opacity": 0.8,
                "truth_label": "style_fill",
                "source_note": "Original unoccupied floor mark.",
            },
            {
                "id": "camera_material",
                "color": "#ccaa55",
                "roughness": 0.6,
                "metalness": 0.0,
                "opacity": 0.8,
                "truth_label": "style_fill",
                "source_note": "Original camera review mark.",
            },
        ],
        "lights": [
            {
                "id": "ambient_light",
                "type": "hemisphere",
                "sky_color": "#ddeeff",
                "ground_color": "#223344",
                "intensity": 2.0,
                "truth_label": "style_fill",
                "source_note": "Original preview-only illumination.",
            }
        ],
        "primitives": [
            {
                "id": "room_floor",
                "primitive": "plane",
                "material_id": "floor_material",
                "position": [0, 0, 0],
                "rotation": [-1.5707963267948966, 0, 0],
                "size": [8, 8],
                "category": "architecture",
                "truth_label": "style_fill",
                "source_note": "Original procedural test-room floor.",
            },
            {
                "id": "future_person_mark_mesh",
                "primitive": "cylinder",
                "material_id": "spawn_material",
                "position": [-1, 0.02, 0],
                "rotation": [0, 0, 0],
                "radius": 0.3,
                "height": 0.03,
                "segments": 16,
                "category": "floor_mark",
                "truth_label": "manual_note_confirmed",
                "source_note": "The fixture requires an unoccupied future-person mark.",
            },
            {
                "id": "review_camera_mark_mesh",
                "primitive": "cylinder",
                "material_id": "camera_material",
                "position": [0, 0.02, 3],
                "rotation": [0, 0, 0],
                "radius": 0.22,
                "height": 0.03,
                "segments": 12,
                "category": "camera_mark",
                "truth_label": "style_fill",
                "source_note": "Original review-camera floor mark.",
            },
            {
                "id": "filming_mark_mesh",
                "primitive": "cylinder",
                "material_id": "camera_material",
                "position": [1, 0.02, 0],
                "rotation": [0, 0, 0],
                "radius": 0.18,
                "height": 0.03,
                "segments": 12,
                "category": "floor_mark",
                "truth_label": "style_fill",
                "source_note": "Original filming alignment mark.",
            },
        ],
        "rooms": [
            {
                "id": "test_room",
                "name": "Test room",
                "purpose": "Bounded procedural backend fixture.",
                "bounds": {"min": [-4, 0, -4], "max": [4, 3, 4]},
                "truth_label": "manual_note_confirmed",
                "source_note": "The automated fixture requests one room.",
            }
        ],
        "colliders": [],
        "support_surfaces": [
            {
                "id": "floor_support",
                "min_x": -4,
                "max_x": 4,
                "min_z": -4,
                "max_z": 4,
                "y": 0,
                "truth_label": "style_fill",
                "source_note": "Procedural floor support metadata.",
            }
        ],
        "spawns": [
            {
                "id": "future_person_spawn",
                "label": "Future person mark",
                "position": [-1, 0, 0],
                "primitive_id": "future_person_mark_mesh",
                "intended_role": "future_test_role",
                "occupant_policy": "mark_only_no_person_loaded",
                "yaw": 0,
                "truth_label": "manual_note_confirmed",
                "source_note": "Unoccupied mark required by the fixture.",
            }
        ],
        "cameras": [
            {
                "id": "test_camera",
                "label": "Test camera",
                "position": [0, 2, 4],
                "target": [0, 1, 0],
                "fov": 55,
                "primitive_id": "review_camera_mark_mesh",
                "truth_label": "style_fill",
                "source_note": "Original overview camera.",
            }
        ],
        "filming_marks": [
            {
                "id": "test_filming_mark",
                "label": "Test filming mark",
                "position": [1, 0, 0],
                "primitive_id": "filming_mark_mesh",
                "mark_type": "performance_mark",
                "truth_label": "style_fill",
                "source_note": "Original alignment mark.",
            }
        ],
        "routes": [
            {
                "id": "clear_test_route",
                "label": "Clear room crossing",
                "avatar_radius": 0.34,
                "points": [[-2, 0, -2], [0, 0, 0], [2, 0, 2]],
                "truth_label": "style_fill",
                "source_note": "Original static route for clearance validation.",
            }
        ],
        "overlays": [
            {
                "id": "future_builder_overlay",
                "title": "Future builder overlay",
                "body": "Informational test hook only.",
                "mode": "informational_future_hook_only",
                "truth_label": "manual_note_confirmed",
                "source_note": "The fixture requires an informational overlay.",
            }
        ],
        "isolation": {
            "world_class": "separate_notebook_world",
            "home_world_mutation_allowed": False,
            "strip_mall_mutation_allowed": False,
            "runtime_registered": False,
            "person_assets_loaded": False,
            "resident_minds_loaded": False,
            "voice_loaded": False,
            "ollama_loaded": False,
        },
        "source_notes": [
            "This is an original procedural backend fixture, not a reconstruction.",
            "All future-person marks are deliberately unoccupied.",
        ],
    }


class PreviewFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.originals = (
            generator.PROJECT_ROOT,
            generator.DEFAULT_WORLD_ROOT,
            generator.DEFAULT_INDEX_PATH,
        )
        generator.PROJECT_ROOT = root
        generator.DEFAULT_WORLD_ROOT = root / "Data" / "world_builds" / "notebook_worlds"
        generator.DEFAULT_INDEX_PATH = root / "Data" / "world_builds" / "notebook_world_index.json"
        # Keep the temporary Windows path short enough for legacy MAX_PATH
        # environments; production uses the much shorter repository root.
        seed = generator.infer_seed("T", category="original_idea")
        generator.apply_seed_overrides(
            seed,
            notebook_world_id="t_notebook_world",
            notebook_title="T Notebook World",
            region="Automated Test",
            country="Virtual",
            starting_area="one bounded test room",
            initial_scope="single_room_backend_fixture",
        )
        paths = generator.create_files(seed, "robert", "automated backend fixture", "private_only", "request_mode", "draft")
        self.request_path = paths["request"]
        request = json.loads(self.request_path.read_text(encoding="utf-8"))
        self.world_id = request["world_plan"]["notebook_world_id"]
        self.request_id = request["request_id"]
        self.request_root = self.request_path.parent
        self.program_path = self.request_root / "procedural_scene_program.json"
        self.authorization_path = self.request_root / "preview_scope_authorization.json"
        self.build_id = "preview_backend_fixture_v1"
        write_json(self.program_path, sample_program(self.world_id, self.request_id))
        self.write_authorization()
        self.template_root = root / "Data" / "world_builder" / "preview_runtime" / "procedural_notebook_preview_v1"
        shutil.copytree(ROOT / "Data" / "world_builder" / "preview_runtime" / "procedural_notebook_preview_v1", self.template_root)
        self.three_module = root / "vendor" / "three.module.js"
        self.three_module.parent.mkdir(parents=True, exist_ok=True)
        self.three_module.write_text("export { fixture } from './three.core.js';\n", encoding="utf-8")
        self.three_core = root / "vendor" / "three.core.js"
        self.three_core.write_text("export const fixture = true;\n", encoding="utf-8")

    def write_authorization(self) -> None:
        authorization = {
            "schema_version": 1,
            "authorization_kind": AUTHORIZATION_KIND,
            "status": AUTHORIZATION_STATUS,
            "authorized_by": "automated_test_fixture",
            "authorized_at": "2026-07-16T12:00:00+00:00",
            "scope_statement": "Authorize one isolated procedural backend fixture only.",
            "world_id": self.world_id,
            "request_id": self.request_id,
            "request_binding": authorization_binding(self.request_path, root=self.root),
            "program_binding": authorization_binding(self.program_path, root=self.root),
            "builder_backend": BACKEND_ID,
            "allowed_build_id": self.build_id,
            "authorized_actions": {
                "build_isolated_procedural_preview": True,
                "serve_scoped_preview": True,
                "approve_world": False,
                "register_runtime": False,
                "place_in_home_world": False,
                "mutate_home_world": False,
                "mutate_strip_mall": False,
                "load_people": False,
                "load_minds": False,
                "load_voice": False,
            },
            "limits": dict(HARD_BUDGET),
        }
        write_json(self.authorization_path, authorization)

    def build(self):
        return build_authorized_preview(
            request_path=self.request_path,
            program_path=self.program_path,
            authorization_path=self.authorization_path,
            build_id=self.build_id,
            root=self.root,
            template_root=self.template_root,
            three_module=self.three_module,
            three_core=self.three_core,
            created_at="2026-07-16T12:00:00+00:00",
        )

    def close(self) -> None:
        generator.PROJECT_ROOT, generator.DEFAULT_WORLD_ROOT, generator.DEFAULT_INDEX_PATH = self.originals


class NotebookWorldPreviewBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="notebook_preview_backend_")
        self.fixture = PreviewFixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.fixture.close()
        self.temporary.cleanup()

    def config(self, result) -> PreviewLaunchConfig:
        return PreviewLaunchConfig(
            root=self.fixture.root,
            manifest_path=result.manifest_path,
            manifest_sha256=result.manifest_sha256,
            world_id=result.world_id,
            request_id=result.request_id,
            registration_relative_path=result.registration_path.relative_to(self.fixture.root).as_posix(),
            display_name="Test preview",
            default_port=0,
        )

    def test_valid_authorized_preview_builds_and_verifies(self) -> None:
        result = self.fixture.build()
        verified = verify_generated_preview(self.config(result))
        self.assertEqual(verified.build_id, self.fixture.build_id)
        self.assertEqual(set(verified.served_urls), {
            "/", "/index.html", "/main.js", "/styles.css",
            "/data/scene_manifest.json", "/data/collision_nav.json",
            "/data/source_truth.json", "/data/resource_budget.json",
            "/data/build_status.json", "/vendor/three/three.module.js",
            "/vendor/three/three.core.js",
        })
        registration = json.loads(result.registration_path.read_text(encoding="utf-8"))
        self.assertFalse(registration["home_world_mutation_allowed"])
        self.assertFalse(registration["runtime_registered"])

    def test_request_tamper_fails_before_output(self) -> None:
        request = json.loads(self.fixture.request_path.read_text(encoding="utf-8"))
        request["isolation_policy"]["home_world_mutation_allowed"] = True
        write_json(self.fixture.request_path, request)
        with self.assertRaisesRegex(PreviewBuildError, "strict-v2|mutation|protected"):
            self.fixture.build()
        self.assertFalse((self.fixture.request_root / "preview_builds" / self.fixture.build_id).exists())

    def test_program_replacement_breaks_exact_authorization_binding(self) -> None:
        program = json.loads(self.fixture.program_path.read_text(encoding="utf-8"))
        program["subtitle"] = "Changed after authorization."
        write_json(self.fixture.program_path, program)
        with self.assertRaisesRegex(PreviewBuildError, "program_binding"):
            self.fixture.build()

    def test_blocked_route_fails_closed(self) -> None:
        program = json.loads(self.fixture.program_path.read_text(encoding="utf-8"))
        program["colliders"] = [
            {
                "id": "blocking_wall",
                "kind": "solid_aabb",
                "min": [-0.2, 0, -4],
                "max": [0.2, 3, 4],
                "truth_label": "style_fill",
                "source_note": "Intentional obstruction for the negative test.",
            }
        ]
        write_json(self.fixture.program_path, program)
        self.fixture.write_authorization()
        with self.assertRaisesRegex(PreviewBuildError, "Route clear_test_route is obstructed"):
            self.fixture.build()

    def test_scene_budget_is_enforced(self) -> None:
        program = json.loads(self.fixture.program_path.read_text(encoding="utf-8"))
        program["scene_budget"]["max_meshes"] = 1
        write_json(self.fixture.program_path, program)
        self.fixture.write_authorization()
        with self.assertRaisesRegex(PreviewBuildError, "above its authorized budget"):
            self.fixture.build()

    def test_program_must_be_request_local(self) -> None:
        outside = self.fixture.root / "outside_program.json"
        outside.write_text(self.fixture.program_path.read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaisesRegex(PreviewBuildError, "request-local"):
            build_authorized_preview(
                request_path=self.fixture.request_path,
                program_path=outside,
                authorization_path=self.fixture.authorization_path,
                build_id=self.fixture.build_id,
                root=self.fixture.root,
                template_root=self.fixture.template_root,
                three_module=self.fixture.three_module,
                three_core=self.fixture.three_core,
            )

    def test_scoped_http_allowlist_and_per_request_hash_check(self) -> None:
        result = self.fixture.build()
        server, port, _ = bind_server(self.config(result), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=3) as response:
                self.assertEqual(response.status, 200)
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/Data/world_builds/notebook_world_index.json", timeout=3)
            self.assertEqual(context.exception.code, 404)
            context.exception.close()
            stylesheet = result.build_root / "preview" / "styles.css"
            stylesheet.write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/styles.css", timeout=3)
            self.assertEqual(context.exception.code, 404)
            context.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
