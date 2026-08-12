import tempfile
import unittest
import hashlib
from pathlib import Path

from Core.shared_person_workbench import (
    personal_workbench,
    standalone_video_studio_access,
    video_studio_access,
)


class SharedPersonVideoStudioAccessTests(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "Data/core_ai_workbenches/kira").mkdir(parents=True)
        (root / "Data/core_ai_workbenches/lisa").mkdir(parents=True)
        (root / "TemporaryAI/candidates/robert_mcmurrer_presence_ai/workbench").mkdir(
            parents=True)
        launcher = (
            root / "VideoStudioDevelopment" / "chat_first_production"
            / "START_CHAT_FIRST_STUDIO.bat"
        )
        launcher.parent.mkdir(parents=True)
        launcher.write_text("@echo off\n", encoding="utf-8")
        return root

    def test_each_person_has_a_separate_existing_architecture_workbench(self):
        root = self.make_root()
        paths = {
            personal_workbench(root, person)
            for person in ("kira", "lisa", "robert_mcmurrer_presence_ai")
        }
        self.assertEqual(3, len(paths))

    def test_studio_opens_with_zero_one_or_multiple_active_people(self):
        root = self.make_root()
        cases = (
            {"active_person": "", "active_people": []},
            {"active_person": "kira", "active_people": ["kira"]},
            {
                "active_person": "kira",
                "active_people": ["kira", "lisa", "robert_mcmurrer_presence_ai"],
            },
        )
        for case in cases:
            with self.subTest(case=case):
                result = video_studio_access(
                    root,
                    active_person=case["active_person"],
                    active_people=case["active_people"],
                    requested_person="robert_mcmurrer_presence_ai",
                )
                self.assertTrue(result["allowed"])
                self.assertEqual(result["mode"], "standalone_owner_decision")
                self.assertTrue(result["legacy_person_bound_access_superseded"])
                self.assertFalse(result["person_context_attached"])
                self.assertFalse(result["person_state_inspected"])
                self.assertFalse(result["person_state_mutated"])
                self.assertFalse(result["active_person_count_condition"])
                self.assertFalse(result["automatic_person_studio_switching"])
                self.assertFalse(result["automatic_publication"])

    def test_opening_studio_leaves_identity_workbench_life_memory_and_voice_unchanged(self):
        root = self.make_root()
        sentinels = {
            "Data/runtime/kira_world_shell_state.json": b'{"active_candidate":"kira"}',
            "Data/runtime/kira_world_life_loop_state.json": b'{"running":true}',
            "Data/runtime/kira_voice_state.json": b'{"voice":"approved"}',
            "Data/core_ai_workbenches/kira/memory.json": b'{"memory":"private"}',
            "Data/core_ai_workbenches/lisa/memory.json": b'{"memory":"private"}',
            "TemporaryAI/candidates/robert_mcmurrer_presence_ai/workbench/memory.json": b'{"memory":"private"}',
        }
        paths = []
        for relative, payload in sentinels.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            paths.append(path)
        before = {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        }

        result = standalone_video_studio_access(root)

        after = {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        }
        self.assertTrue(result["allowed"])
        self.assertEqual(before, after)
        self.assertFalse(result["person_state_inspected"])
        self.assertFalse(result["person_state_mutated"])
        self.assertEqual(result["lifecycle_action"], "none")
        self.assertIsNone(result["person_id"])
        self.assertIsNone(result["workbench"])

    def test_missing_protected_launcher_fails_without_inspecting_person_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = standalone_video_studio_access(Path(temporary))
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "protected_standalone_studio_launcher_missing")
        self.assertFalse(result["person_state_inspected"])
        self.assertFalse(result["person_state_mutated"])
