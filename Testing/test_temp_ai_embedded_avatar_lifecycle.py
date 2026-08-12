from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from tools.temporary_ai_live_chat_gui import TemporaryAILiveChatGUI  # noqa: E402


class TemporaryAIEmbeddedAvatarLifecycleTests(unittest.TestCase):
    def test_existing_embedded_avatar_is_reattached_without_restart(self) -> None:
        candidate_id = "ladybug_marinette_expanded_smoke"
        avatar = SimpleNamespace(
            candidate_id=candidate_id,
            ensure_attached=Mock(return_value=True),
            resize=Mock(),
            stop=Mock(),
        )
        root = SimpleNamespace(
            after_cancel=Mock(),
            update_idletasks=Mock(),
            after=Mock(),
        )
        gui = SimpleNamespace(
            closing=False,
            embedded_avatar=avatar,
            embedded_candidate_id=None,
            embedded_start_after_id=None,
            root=root,
            visual_box=SimpleNamespace(pack_forget=Mock()),
            visual_caption=SimpleNamespace(config=Mock()),
            publish_avatar_state=Mock(),
            show_2d_avatar_fallback=Mock(),
            open_3d_avatar=Mock(),
        )

        with patch(
            "tools.temporary_ai_live_chat_gui.discover_rigged_model",
            return_value=PROJECT_ROOT / "Avatar/models/temp_ai/ladybug/avatar.glb",
        ):
            TemporaryAILiveChatGUI.schedule_embedded_avatar(gui, candidate_id)

        avatar.ensure_attached.assert_called_once_with()
        avatar.stop.assert_not_called()
        gui.show_2d_avatar_fallback.assert_not_called()
        gui.visual_box.pack_forget.assert_called_once_with()
        avatar.resize.assert_called_once_with()
        self.assertEqual(gui.embedded_candidate_id, candidate_id)

    def test_life_loop_start_keeps_avatar_and_never_stops_it(self) -> None:
        source = (PROJECT_ROOT / "tools/temporary_ai_live_chat_gui.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "start_life_loop"
        )
        calls = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        self.assertTrue(
            any(node.func.attr == "schedule_embedded_avatar" for node in calls),
            "Starting a life loop must reattach the existing embedded avatar.",
        )
        self.assertFalse(
            any(
                node.func.attr == "stop"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "embedded_avatar"
                for node in calls
            ),
            "Starting a life loop must not stop or recreate the embedded avatar.",
        )


if __name__ == "__main__":
    unittest.main()
