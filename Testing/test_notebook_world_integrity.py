from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from notebook_world_integrity import canonical_json_sha256, verify_code_pinned_build  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def binding(root: Path, relative: str, role: str, url: str | None = None) -> dict:
    path = root / relative
    result = {
        "role": role,
        "path": relative,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if url is not None:
        result["url"] = url
    return result


def synthetic_build(root: Path) -> tuple[Path, str, str, str]:
    world_id = "test_notebook_world"
    request_id = "notebook_world_integrity_test"
    registration_relative = "Data/test_build/registration.json"
    entry_relative = "Data/test_build/preview/index.html"
    write_json(root / registration_relative, {"request_id": request_id})
    entry = root / entry_relative
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("<!doctype html><title>pinned</title>\n", encoding="utf-8")
    anchor = {
        "request_id": request_id,
        "scene_folder": "Data/test_build",
        "status": "test",
    }
    write_json(
        root / "Data/world_builds/notebook_world_index.json",
        {"schema_version": 1, "notebook_worlds": {world_id: {"anchors": [anchor]}}},
    )
    registration_binding = binding(root, registration_relative, "registration")
    entry_binding = binding(root, entry_relative, "entry_html", "/index.html")
    manifest = {
        "schema_version": 1,
        "manifest_kind": "code_pinned_notebook_world_build",
        "world_id": world_id,
        "request_id": request_id,
        "build_id": "test_build",
        "registration": {
            key: registration_binding[key] for key in ("path", "sha256", "bytes")
        },
        "entrypoint": {
            key: entry_binding[key] for key in ("url", "path", "sha256", "bytes")
        },
        "index_registration": {
            "path": "Data/world_builds/notebook_world_index.json",
            "scene_folder": "Data/test_build",
            "anchor_sha256": canonical_json_sha256(anchor),
        },
        "files": [registration_binding, entry_binding],
    }
    manifest_path = root / "Data/test_build/pinned_build_manifest.json"
    write_json(manifest_path, manifest)
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest_path, manifest_sha, registration_relative, entry_relative


class NotebookWorldIntegrityTests(unittest.TestCase):
    def verify(self, root: Path, manifest_path: Path, manifest_sha: str, registration: str):
        return verify_code_pinned_build(
            root=root,
            manifest_path=manifest_path,
            expected_manifest_sha256=manifest_sha,
            expected_world_id="test_notebook_world",
            expected_request_id="notebook_world_integrity_test",
            expected_registration_relative_path=registration,
            required_roles={"registration", "entry_html"},
        )

    def test_valid_synthetic_build_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, digest, registration, _ = synthetic_build(root)
            verified = self.verify(root, manifest, digest, registration)
            self.assertEqual(verified.manifest_sha256, digest)
            self.assertEqual(verified.served_urls["/"], verified.served_urls["/index.html"])

    def test_file_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, digest, registration, entry = synthetic_build(root)
            (root / entry).write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.verify(root, manifest, digest, registration)

    def test_manifest_path_divergence_fails_even_with_new_code_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest, _, registration, _ = synthetic_build(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["files"][1]["path"] = "Data/test_build/preview/../preview/index.html"
            write_json(manifest, data)
            digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "normalized project-relative"):
                self.verify(root, manifest, digest, registration)


if __name__ == "__main__":
    unittest.main()
