import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from build_remote_phone_persistence_manifest import (  # noqa: E402
    build_persistence_manifest,
    compare_manifests,
)


class RemotePhonePersistenceManifestTests(unittest.TestCase):
    def test_manifest_tracks_remote_contact_and_private_media(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            remote_dir = root / "Data" / "remote_contact" / "events"
            media_dir = root / "Data" / "private_media" / "events"
            remote_dir.mkdir(parents=True)
            media_dir.mkdir(parents=True)
            (remote_dir / "text.json").write_text(
                json.dumps(
                    {
                        "event_id": "text_1",
                        "initiator": "real_robert",
                        "recipient": "kira",
                        "channel": "pre_gpu_text_message",
                        "delivery_state": "queued",
                        "response_state": "waiting",
                    }
                ),
                encoding="utf-8",
            )
            (media_dir / "picture.json").write_text(
                json.dumps(
                    {
                        "event_id": "picture_1",
                        "status": "active",
                        "access_and_scope": {"allowed_scope": "pair_private"},
                    }
                ),
                encoding="utf-8",
            )

            manifest = build_persistence_manifest(root)
            paths = {item["path"] for item in manifest["files"]}

            self.assertEqual(manifest["file_count"], 2)
            self.assertIn("Data/remote_contact/events/text.json", paths)
            self.assertIn("Data/private_media/events/picture.json", paths)

    def test_compare_fails_when_update_drops_history(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            remote_dir = root / "Data" / "remote_contact" / "events"
            remote_dir.mkdir(parents=True)
            event_path = remote_dir / "text.json"
            event_path.write_text('{"event_id": "text_1"}', encoding="utf-8")

            before = build_persistence_manifest(root)
            event_path.unlink()
            after = build_persistence_manifest(root)

            problems = compare_manifests(before, after)

            self.assertTrue(any("Missing persistent file" in problem for problem in problems))

    def test_compare_fails_when_update_changes_history(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            remote_dir = root / "Data" / "remote_contact" / "events"
            remote_dir.mkdir(parents=True)
            event_path = remote_dir / "text.json"
            event_path.write_text('{"event_id": "text_1", "message_text": "old"}', encoding="utf-8")

            before = build_persistence_manifest(root)
            event_path.write_text('{"event_id": "text_1", "message_text": "new"}', encoding="utf-8")
            after = build_persistence_manifest(root)

            problems = compare_manifests(before, after)

            self.assertTrue(any("Changed persistent file" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
