from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.voice_sample_review_panel import (  # noqa: E402
    ALL_GROUPS,
    ALL_STATUSES,
    build_source_context,
    can_approve_target,
    filter_review_clips,
    format_clip_row,
    launch_source_context,
    next_unreviewed_clip_id,
    persist_review_decision,
    review_panel_identity,
    review_status_counts,
)


class VoiceSampleReviewPanelTests(unittest.TestCase):
    def test_panel_identity_is_target_source_and_pack_specific(self) -> None:
        elsa = review_panel_identity(
            {
                "pack_id": "elsa_pack_001",
                "target": {
                    "name": "Elsa",
                    "id": "elsa",
                    "form_or_version": "adult Frozen II English",
                },
                "source": {"path": "Data/library/frozen_ii.mp4"},
            },
            Path("fallback_pack"),
        )
        kathryn = review_panel_identity(
            {
                "pack_id": "kathryn_pack_001",
                "target": {
                    "name": "Kathryn Merteuil",
                    "id": "kathryn_merteuil",
                    "form_or_version": "adult-present unaired pilot",
                },
                "source": {"path": "Data/library/cruel_intentions_pilot.mp4"},
            },
            Path("fallback_pack"),
        )

        self.assertEqual(elsa["window_title"], "Elsa Voice Candidate Review — identity unverified")
        self.assertEqual(elsa["source_name"], "frozen_ii.mp4")
        self.assertEqual(elsa["pack_id"], "elsa_pack_001")
        self.assertNotEqual(elsa["target_name"], kathryn["target_name"])
        self.assertNotEqual(elsa["source_name"], kathryn["source_name"])

    def test_filters_by_human_status_and_acoustic_group_without_equating_them(self) -> None:
        clips = [
            {"clip_id": "clip_1", "review_status": "unreviewed"},
            {"clip_id": "clip_2", "review_status": "approved_target"},
            {"clip_id": "clip_3", "review_status": "rejected_other_speaker"},
        ]
        groups = {"clip_1": "female_4", "clip_2": "female_4", "clip_3": "male_2"}

        self.assertEqual(filter_review_clips(clips, groups, ALL_GROUPS, ALL_STATUSES), clips)
        self.assertEqual(
            [clip["clip_id"] for clip in filter_review_clips(clips, groups, "female_4", "unreviewed")],
            ["clip_1"],
        )
        row = format_clip_row(
            {
                "clip_id": "clip_1",
                "review_status": "unreviewed",
                "start_seconds": 1.0,
                "end_seconds": 2.25,
                "duration_seconds": 1.25,
            },
            "female_4",
        )
        self.assertIn("group=female_4", row)
        self.assertNotIn("speaker=Elsa", row)

    def test_counts_human_review_states(self) -> None:
        counts = review_status_counts(
            [
                {"review_status": "unreviewed"},
                {"review_status": "approved_target"},
                {"review_status": "rejected_other_speaker"},
                {"review_status": "rejected_noisy"},
            ]
        )
        self.assertEqual(
            counts,
            {"total": 4, "unreviewed": 1, "approved_target": 1, "rejected": 2},
        )

    def test_approval_requires_context_for_the_exact_clip(self) -> None:
        first = {"clip_id": "clip_1"}
        second = {"clip_id": "clip_2"}
        self.assertFalse(can_approve_target(first, set()))
        self.assertTrue(can_approve_target(first, {"clip_1"}))
        self.assertFalse(can_approve_target(second, {"clip_1"}))

    def test_next_unreviewed_wraps_and_never_returns_current_row(self) -> None:
        clips = [
            {"clip_id": "clip_1", "review_status": "unreviewed"},
            {"clip_id": "clip_2", "review_status": "rejected_noisy"},
            {"clip_id": "clip_3", "review_status": "unreviewed"},
        ]
        self.assertEqual(next_unreviewed_clip_id(clips, 0), "clip_3")
        self.assertEqual(next_unreviewed_clip_id(clips, 2), "clip_1")
        self.assertEqual(
            next_unreviewed_clip_id(
                [{"clip_id": "only", "review_status": "unreviewed"}], 0
            ),
            "",
        )

    def test_review_decision_is_persisted_immediately(self) -> None:
        clip = {"clip_id": "clip_1", "review_status": "unreviewed"}
        clips = [clip]
        persisted_manifest = {"review": {"approved_clip_count": 1}}
        with patch(
            "tools.voice_sample_review_panel.update_pack_review",
            return_value=persisted_manifest,
        ) as update:
            result = persist_review_decision(
                Path("pack"), clips, clip, "approved_target"
            )
        self.assertIs(result, persisted_manifest)
        self.assertEqual(clip["review_status"], "approved_target")
        update.assert_called_once_with(Path("pack"), clips)

    def test_failed_immediate_save_restores_previous_review_status(self) -> None:
        clip = {"clip_id": "clip_1", "review_status": "unreviewed"}
        with patch(
            "tools.voice_sample_review_panel.update_pack_review",
            side_effect=OSError("disk unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "disk unavailable"):
                persist_review_decision(
                    Path("pack"), [clip], clip, "rejected_noisy"
                )
        self.assertEqual(clip["review_status"], "unreviewed")

    def test_source_context_gate_is_recorded_before_external_launch(self) -> None:
        opened: set[str] = set()

        def launcher(_path: str) -> None:
            self.assertIn("clip_7", opened)

        launch_source_context(Path("clip_7_context.mp4"), "clip_7", opened, launcher)
        self.assertEqual(opened, {"clip_7"})

    def test_source_context_gate_rolls_back_when_player_fails(self) -> None:
        opened: set[str] = set()

        def launcher(_path: str) -> None:
            raise OSError("no player")

        with self.assertRaisesRegex(OSError, "no player"):
            launch_source_context(Path("clip.mp4"), "clip_7", opened, launcher)
        self.assertEqual(opened, set())

    def test_builds_bounded_video_context_without_approving_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            source = root / "source.mp4"
            source.write_bytes(b"movie")
            manifest = {"source": {"path": str(source)}}
            clip = {"clip_id": "clip_0007", "start_seconds": 10.0, "end_seconds": 12.0}

            def fake_run(command, **_kwargs):
                Path(command[-1]).write_bytes(b"context")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("tools.voice_sample_review_panel.resolve_ffmpeg", return_value="ffmpeg"), patch(
                "tools.voice_sample_review_panel.subprocess.run", side_effect=fake_run
            ) as run:
                output = build_source_context(pack, manifest, clip)

            self.assertEqual(output.name, "clip_0007_context.mp4")
            self.assertEqual(output.read_bytes(), b"context")
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("-ss") + 1], "8.500")
            self.assertEqual(command[command.index("-t") + 1], "5.000")
            self.assertNotIn("approved", output.name)


if __name__ == "__main__":
    unittest.main()
