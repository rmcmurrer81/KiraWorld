from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_living_portrait import (  # noqa: E402
    POSE_ORDER,
    avatar_body_root,
    begins_with_greeting,
    ensure_avatar_body_manifest,
    ensure_avatar_build_plan,
    infer_emotion,
    load_avatar_pose_paths,
    pose_for_motion,
    resolve_avatar_pose_paths,
)
from tools.import_avatar_pose_sheet import import_pose_sheet, remove_green_screen  # noqa: E402


class AvatarLivingPortraitTests(unittest.TestCase):
    def test_emotion_and_greeting_detection(self) -> None:
        self.assertTrue(begins_with_greeting("Hello, Robert. I'm glad to see you."))
        self.assertEqual(infer_emotion("I'm excited, this is an amazing idea!"), "excited")

    def test_build_plan_accepts_list_form_profile(self) -> None:
        candidate_id = "avatar_living_portrait_smoke"
        path = ensure_avatar_build_plan(candidate_id, {"visual_identity": {"forms": [{"id": "civilian"}, {"id": "hero"}]}}, [])
        data = json.loads(path.read_text(encoding="utf-8"))
        forms = {item["form"] for item in data["required_reference_views"]}
        self.assertEqual(forms, {"civilian", "hero"})
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass

    def test_generated_pose_manifest_uses_only_existing_frames(self) -> None:
        candidate_id = "avatar_living_portrait_pose_smoke"
        profile = {"visual_identity": {"forms": [{"id": "civilian"}, {"id": "hero"}]}}
        root = avatar_body_root(candidate_id)
        try:
            ensure_avatar_body_manifest(candidate_id, profile)
            neutral = root / "civilian" / "neutral.png"
            neutral.write_bytes(b"pose-smoke")
            paths = load_avatar_pose_paths(candidate_id, profile, "civilian")
            self.assertEqual(paths, {"neutral": neutral})
            self.assertEqual(pose_for_motion("greeting", 5, set(paths)), "neutral")
        finally:
            shutil.rmtree(root.parent, ignore_errors=True)

    def test_missing_hero_body_falls_back_to_ready_civilian_body(self) -> None:
        candidate_id = "avatar_living_portrait_fallback_smoke"
        profile = {
            "visual_identity": {
                "forms": [{"id": "civilian"}, {"id": "hero"}],
                "preferred_chat_form": "hero",
            }
        }
        root = avatar_body_root(candidate_id)
        try:
            ensure_avatar_body_manifest(candidate_id, profile)
            neutral = root / "civilian" / "neutral.png"
            neutral.write_bytes(b"pose-smoke")
            resolved_form, paths = resolve_avatar_pose_paths(candidate_id, profile, "hero")
            self.assertEqual(resolved_form, "civilian")
            self.assertEqual(paths, {"neutral": neutral})
        finally:
            shutil.rmtree(root.parent, ignore_errors=True)

    def test_pose_sheet_import_creates_six_real_frames(self) -> None:
        candidate_id = "avatar_living_portrait_import_smoke"
        candidate_dir = PROJECT_ROOT / "TemporaryAI" / "candidates" / candidate_id
        root = avatar_body_root(candidate_id)
        sheet_path = PROJECT_ROOT / "Data" / "temp" / "avatar_pose_sheet_smoke.png"
        try:
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (candidate_dir / "temporary_ai_profile.json").write_text(
                json.dumps(
                    {
                        "display_name": "Avatar smoke",
                        "visual_identity": {"forms": [{"id": "civilian"}]},
                    }
                ),
                encoding="utf-8",
            )
            sheet_path.parent.mkdir(parents=True, exist_ok=True)
            from PIL import Image

            Image.new("RGB", (900, 1200), "#123456").save(sheet_path)
            created = import_pose_sheet(candidate_id, "civilian", sheet_path)
            self.assertEqual(len(created), 6)
            self.assertTrue(all(path.exists() for path in created))
            self.assertEqual(set(load_avatar_pose_paths(candidate_id, {}, "civilian")), set(POSE_ORDER))
        finally:
            shutil.rmtree(candidate_dir, ignore_errors=True)
            shutil.rmtree(root.parent, ignore_errors=True)
            sheet_path.unlink(missing_ok=True)

    def test_green_screen_cleanup_preserves_subject_and_removes_key(self) -> None:
        from PIL import Image

        image = Image.new("RGBA", (2, 1), (0, 255, 0, 255))
        image.putpixel((1, 0), (240, 200, 170, 255))
        cleaned = remove_green_screen(image)
        self.assertEqual(cleaned.getpixel((0, 0))[3], 0)
        self.assertEqual(cleaned.getpixel((1, 0))[3], 255)


if __name__ == "__main__":
    unittest.main()
