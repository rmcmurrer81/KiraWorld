from __future__ import annotations

import hashlib
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from serve_legal_day_spa_notebook_world import (  # noqa: E402
    BUILD_MANIFEST,
    BUILD_MANIFEST_SHA256,
    REGISTRATION as PINNED_REGISTRATION,
    allowed_asset_urls,
    bind_server,
    pinned_preview_relative_path,
    verify_pinned_build,
)
from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402


REGISTRATION = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "legal_day_spa_notebook_world"
    / "builds"
    / "notebook_world_legal_day_spa_staged_20260715"
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SpaNotebookRegistrationTests(unittest.TestCase):
    def test_code_pinned_manifest_binds_registration_and_index_anchor(self) -> None:
        verified = verify_pinned_build()
        self.assertEqual(verified.manifest_path, BUILD_MANIFEST)
        self.assertEqual(verified.manifest_sha256, BUILD_MANIFEST_SHA256)
        self.assertEqual(
            verified.registration_sha256,
            hashlib.sha256(PINNED_REGISTRATION.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            verified.registration_sha256,
            "6073a442cb9058739aa8cace0969cc5d7e92488b37053deb045eb6ae08aa34a6",
        )
        self.assertEqual(
            verified.index_anchor_sha256,
            "f40768bcd4f9c5ac9a728c6fd1654170787804076d39bfe9eb3fe33d8cd31267",
        )
        self.assertEqual(len(verified.role_paths["model_asset"]), 5)
        self.assertEqual(len(verified.role_paths["three_runtime"]), 3)

    def test_integrity_failure_happens_before_socket_bind(self) -> None:
        with (
            patch(
                "serve_legal_day_spa_notebook_world.verify_pinned_build",
                side_effect=ValueError("simulated tamper"),
            ),
            patch("serve_legal_day_spa_notebook_world.ThreadingHTTPServer") as server_constructor,
        ):
            with self.assertRaisesRegex(ValueError, "simulated tamper"):
                bind_server(0)
        server_constructor.assert_not_called()

    def test_index_registers_spa_only_in_separate_world(self) -> None:
        index = read(ROOT / "Data" / "world_builds" / "notebook_world_index.json")
        worlds = index["notebook_worlds"]
        self.assertIn("legal_day_spa_notebook_world", worlds)
        spa_anchors = worlds["legal_day_spa_notebook_world"]["anchors"]
        self.assertEqual([item["request_id"] for item in spa_anchors], ["notebook_world_legal_day_spa_staged_20260715"])
        for world_id, world in worlds.items():
            if world_id == "legal_day_spa_notebook_world":
                continue
            self.assertFalse(any("legal_day_spa" in str(item.get("request_id", "")) for item in world.get("anchors", [])))

    def test_request_is_structurally_valid(self) -> None:
        request = read(REGISTRATION / "notebook_world_request.json")
        self.assertEqual(validate_notebook_world_request(request), [])
        self.assertEqual(request["world_plan"]["notebook_world_id"], "legal_day_spa_notebook_world")

    def test_gate_preserves_home_world_and_strip_mall(self) -> None:
        gate = read(REGISTRATION / "approval_gate.json")
        placement = read(REGISTRATION / "placement.json")
        self.assertFalse(gate["world_builder_may_commit_to_home_world"])
        self.assertTrue(gate["strip_mall_must_remain"])
        self.assertFalse(placement["home_world_modified"])
        self.assertFalse(placement["strip_mall_deleted"])

    def test_registered_preview_and_resource_report_exist(self) -> None:
        registration = read(REGISTRATION / "preview_registration.json")
        self.assertTrue((ROOT / registration["preview"]).is_file())
        self.assertTrue((ROOT / registration["resource_report"]).is_file())
        self.assertFalse(registration["loads_kira"])
        self.assertFalse(registration["loads_ollama"])
        self.assertFalse(registration["launcher_follows_latest_pointer"])
        self.assertTrue(registration["launcher_pins_registered_preview"])
        self.assertFalse(registration["server_scope"]["entire_workspace_served"])

    def test_launcher_resolves_pinned_registered_preview(self) -> None:
        resolved = ROOT / pinned_preview_relative_path()
        registration = read(REGISTRATION / "preview_registration.json")
        self.assertEqual(resolved, ROOT / registration["preview"])
        self.assertIn("spa_preview_20260715_221820", resolved.as_posix())

    def test_scoped_server_serves_preview_and_exact_assets_but_not_private_workspace(self) -> None:
        assets = allowed_asset_urls()
        server, port = bind_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"Legal Day Spa Preview", response.read())

            asset_url = next(iter(assets))
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}{quote(asset_url, safe='/')}",
                method="HEAD",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(int(response.headers["content-length"]), 100)

            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/Data/identity/robert_presence_ai_variant_policy_20260712.json",
                    timeout=5,
                )
            self.assertEqual(blocked.exception.code, 404)
            blocked.exception.close()

            for path in ("/scene_data.json", "/%2e%2e/Data/launch/hardware_capability_profile.json"):
                with self.assertRaises(urllib.error.HTTPError) as divergent:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5)
                self.assertEqual(divergent.exception.code, 404)
                divergent.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
