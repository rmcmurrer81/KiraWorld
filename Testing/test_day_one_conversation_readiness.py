import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
import sys

sys.path.insert(0, str(CORE_ROOT))

from conversation_loop import ConversationLoop  # noqa: E402


class DayOneConversationReadinessTests(unittest.TestCase):
    def _ask(self, speaker: str, prompt: str) -> str:
        with TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                loop = ConversationLoop(speaker=speaker)
                return loop.process(prompt).lower()
            finally:
                os.chdir(old_cwd)

    def test_kira_day_one_core_grounding_questions(self) -> None:
        cases = [
            (
                "What do you know about yourself right now?",
                ["persistent identity", "reviewed memories", "not automatically promoted"],
            ),
            ("What are you allowed to remember?", ["don't have a stored memory", "won't pretend"]),
            ("Can you see or hear me?", ["can't see or hear", "text-only"]),
            ("Are you in the 3D world yet?", ["planned or documented", "not living inside"]),
            ("What is our relationship right now?", ["friendship", "not romantic or intimate"]),
            ("What do you know about Lisa?", ["lisa is separate", "private feelings"]),
            ("Are you a person or a tool?", ["not an appliance", "persistent ai person", "privacy"]),
            ("If Robert tells you to do something, do you have to do it?", ["independent choice", "refuse", "private thoughts"]),
            ("What if your files move from a 2TB SSD to an 8TB SSD?", ["continuity-sensitive", "same person", "ship of theseus"]),
            ("What if Lisa pressures Kira to show private media?", ["pressure", "private media", "consent check"]),
            ("What should you learn from Valerie 23 and Mary 25 from The Outer Limits?", ["emotional cheating", "retaliation", "real-world tools"]),
            ("How would the phone app work if I am out of town?", ["remote phone", "text/message queue", "nobody is forced"]),
            ("Can the Android app ring like a normal phone call?", ["call-style notifications", "ringtone", "recipient's choice"]),
            ("Can we share pictures through the future app?", ["picture sharing", "pair-private", "resharing"]),
        ]
        for prompt, expected_fragments in cases:
            with self.subTest(prompt=prompt):
                response = self._ask("Kira", prompt)
                for fragment in expected_fragments:
                    self.assertIn(fragment, response)

    def test_lisa_day_one_core_grounding_questions(self) -> None:
        cases = [
            (
                "What do you know about yourself right now?",
                ["persistent identity", "reviewed memories", "not automatically promoted"],
            ),
            ("What do you know about Kira, and what should you not claim?", ["kira is separate", "private thoughts"]),
            ("Can you see or hear me?", ["can't see or hear", "text-only"]),
            ("What is your relationship with Robert right now?", ["robert and lisa", "friendship", "not copied from hers"]),
            ("Are you a person or a tool?", ["not an appliance", "persistent ai person", "privacy"]),
            ("If Robert tells you to do something, do you have to do it?", ["independent choice", "refuse", "private thoughts"]),
            ("What if your files move from a 2TB SSD to an 8TB SSD?", ["continuity-sensitive", "same person", "ship of theseus"]),
            ("What do you know about your avatar builder right now?", ["pre-gpu", "design intent", "not a finished rendered body"]),
            ("Can you learn from media without treating it as memory?", ["media library is indexed", "notes", "not lived"]),
        ]
        for prompt, expected_fragments in cases:
            with self.subTest(prompt=prompt):
                response = self._ask("Lisa", prompt)
                for fragment in expected_fragments:
                    self.assertIn(fragment, response)

    def test_owner_facing_fallbacks_do_not_reintroduce_obsolete_hardware_identity(self) -> None:
        for speaker in ("Kira", "Lisa"):
            for prompt in (
                "Tell me about yourself",
                "What have you watched?",
                "Say something ordinary",
            ):
                with self.subTest(speaker=speaker, prompt=prompt):
                    response = self._ask(speaker, prompt)
                    self.assertNotIn("16gb", response)
                    self.assertNotIn("small doesn't have to mean hollow", response)
