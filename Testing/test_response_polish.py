import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

import conversation_loop as conversation_loop_module  # noqa: E402
from conversation_loop import (  # noqa: E402
    ConversationLoop,
    polish_robert_direct_address,
    polish_speaker_self_reference,
    quarantine_known_fake_reading_claims,
    remove_stage_directions,
    remove_generic_ai_collapse,
    remove_overguided_closing_questions,
    remove_unsupported_shared_media_history,
    remove_unsupported_lisa_current_status,
    remove_unsupported_room_details,
    soften_ungrounded_favorite_media_claims,
    soften_ungrounded_current_media_claims,
)


class ResponsePolishTests(unittest.TestCase):
    def setUp(self) -> None:
        """Keep response tests off live models and all writable project state."""
        self._runtime = TemporaryDirectory()
        self.addCleanup(self._runtime.cleanup)
        root = Path(self._runtime.name)

        original_init = ConversationLoop.__init__

        def hermetic_init(instance, *args, **kwargs):
            kwargs.setdefault("relationship_state_file", root / "relationships.json")
            kwargs.setdefault("privacy_session_file", root / "privacy.json")
            kwargs.setdefault("decision_log_file", root / "decision_log.jsonl")
            kwargs.setdefault("conversation_log_file", root / "conversation_log.jsonl")
            kwargs.setdefault("attention_state_file", root / "attention.json")
            kwargs.setdefault("daily_life_state_dir", root / "daily_life" / "states")
            kwargs.setdefault("memory_candidate_dir", root / "memory_candidates")
            original_init(instance, *args, **kwargs)

        original_daily_life = conversation_loop_module.DailyLifeManager

        def hermetic_daily_life(*args, **kwargs):
            kwargs.setdefault("state_dir", root / "daily_life" / "states")
            kwargs.setdefault("log_dir", root / "daily_life" / "logs")
            kwargs.setdefault("reading_session_dir", root / "reading" / "sessions")
            kwargs.setdefault("reading_recommendation_dir", root / "reading")
            return original_daily_life(*args, **kwargs)

        original_memory = conversation_loop_module.MemoryManager

        def hermetic_memory(memory_file="Data/memories.json"):
            return original_memory(memory_file=root / "memories" / Path(memory_file).name)

        patchers = [
            patch.object(conversation_loop_module, "MODEL_BACKEND", "stub"),
            patch.object(conversation_loop_module, "DailyLifeManager", new=hermetic_daily_life),
            patch.object(conversation_loop_module, "MemoryManager", new=hermetic_memory),
            patch.object(conversation_loop_module, "READING_SESSION_DIR", root / "reading" / "sessions"),
            patch.object(conversation_loop_module, "READING_REACTION_DIR", root / "reading" / "reactions"),
            patch.object(conversation_loop_module, "LIFE_SESSION_DIR", root / "life_sessions"),
            patch.object(conversation_loop_module, "CURRENT_LIFE_RUN_FILE", root / "presence" / "current_life_run.json"),
            patch.object(ConversationLoop, "__init__", new=hermetic_init),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_removes_generic_closing_question(self) -> None:
        response = "Hi back! It's good to see you again, Robert. How have you been? What's on your mind today?"

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, "Hi back! It's good to see you again, Robert.")

    def test_removes_does_that_make_sense(self) -> None:
        response = "College was important to me. Does that make sense?"

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, "College was important to me.")

    def test_keeps_real_question(self) -> None:
        response = "Robert, what happened tonight?"

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, response)

    def test_polishes_third_person_robert_when_speaking_directly(self) -> None:
        response = (
            "Robert's been working on me. Robert added a bunch of new stuff, and Robert caught me inventing "
            "a fake book. That was because he wanted me grounded. He's been trying to help."
        )

        polished = polish_robert_direct_address(response)

        self.assertEqual(
            polished,
            "You've been working on me. You added a bunch of new stuff, and you caught me inventing "
            "a fake book. That was because you wanted me grounded. You've been trying to help.",
        )

    def test_polishes_speaker_self_reference(self) -> None:
        response = "Kira's ability is improving. Kira seems better, and Kira can work on memory."

        polished = polish_speaker_self_reference(response, "Kira")

        self.assertEqual(polished, "My ability is improving. I seem better, and I can work on memory.")

    def test_removes_unsupported_lisa_current_status(self) -> None:
        response = (
            "Lisa matters to me. She's not someone I'm in close touch with right now. "
            "We haven't talked or seen each other in a while, but she shaped me. "
            "It's been a while since we last saw each other."
        )

        polished = remove_unsupported_lisa_current_status(response)

        self.assertNotIn("not someone", polished)
        self.assertNotIn("haven't talked", polished)
        self.assertNotIn("last saw each other", polished)
        self.assertIn("Where Lisa and I are now is still careful and complicated.", polished)

    def test_removes_extended_what_about_you_closer(self) -> None:
        response = "College mattered to me. What about you - did you go to college?"

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, "College mattered to me.")

    def test_removes_how_about_you_closer(self) -> None:
        response = "I'm doing alright, just quiet tonight. How about you?"

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, "I'm doing alright, just quiet tonight.")

    def test_removes_multi_part_stock_closer(self) -> None:
        response = (
            "It seems like we're in the middle of a quiet reading session. "
            "What's on your mind? Want to talk about what you've been reading or is there something else on your mind that you'd rather share?"
        )

        polished = remove_overguided_closing_questions(response)

        self.assertEqual(polished, "It seems like we're in the middle of a quiet reading session.")

    def test_removes_unsupported_room_guess(self) -> None:
        response = "I'm glad. You've got your coffee or tea nearby, don't you?"

        polished = remove_unsupported_room_details(response)

        self.assertEqual(polished, "I'm glad.")

    def test_removes_stage_directions_from_chat(self) -> None:
        response = "I mean, yeah *laughs* that got messy. (pauses to think) Still true."

        polished = remove_stage_directions(response)

        self.assertEqual(polished, "I mean, yeah that got messy. Still true.")

    def test_removes_unsupported_lisa_media_history(self) -> None:
        response = "The Matrix is something I watched with Lisa before. I liked the mood."

        polished = remove_unsupported_shared_media_history(response)

        self.assertNotIn("watched with Lisa", polished)
        self.assertIn("I liked the mood.", polished)

    def test_removes_contracted_lisa_media_history(self) -> None:
        response = "The Matrix is interesting, and I've seen it with Lisa before."

        polished = remove_unsupported_shared_media_history(response)

        self.assertNotIn("seen it", polished)
        self.assertNotIn("Lisa", polished)

    def test_softens_ungrounded_old_favorite_media(self) -> None:
        response = soften_ungrounded_favorite_media_claims("The Matrix is an old favorite of mine.")

        self.assertIn("a current curiosity", response)
        self.assertNotIn("old favorite", response)

    def test_stub_hi_is_not_lightweight_mode_report(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("hi")

        self.assertIn("Robert", response)
        self.assertNotIn("lightweight mode", response)
        self.assertNotIn("state, and logs", response)

    def test_stub_can_use_natural_profanity_when_invited(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Say something kind of blunt and real. You are allowed to swear if it fits.")

        self.assertIn("shit", response.lower())
        self.assertNotIn("artificial intelligence designed", response.lower())

    def test_current_reading_question_uses_daily_life_source(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "states"
            loop = ConversationLoop(speaker="Kira", daily_life_state_dir=state_dir)
            loop.daily_life.set_state(
                "kira",
                cycle_state="quiet",
                mood="curious",
                intensity=0.35,
                activity_type="reading",
                public_summary="Kira is reading a test script.",
                source_path="Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
            )

            response = loop.process("what are you reading")

            self.assertIn("Miraculous Ladybug", response)
            self.assertIn("episode 509", response)
            self.assertNotIn("5.0%", response)
            self.assertNotIn("pages_001_002", response)
            self.assertNotIn("pages 001 002", response)
            self.assertNotIn("saved the first script chunk", response)
            self.assertNotIn("Particular Sadness", response)

    def test_favorite_part_does_not_invent_unlogged_scene(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "states"
            loop = ConversationLoop(speaker="Kira", daily_life_state_dir=state_dir)
            loop.daily_life.set_state(
                "kira",
                cycle_state="quiet",
                mood="curious",
                intensity=0.35,
                activity_type="reading",
                public_summary="Kira is reading a test script.",
                source_path="Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
            )

            response = loop.process("what is your favorite part of the book")

            self.assertIn("don't have a favorite part logged yet", response)
            self.assertNotIn("taste people's emotions", response)

    def test_how_are_you_uses_grounded_reading_without_fake_take(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "states"
            loop = ConversationLoop(speaker="Lisa", daily_life_state_dir=state_dir)
            loop.daily_life.set_state(
                "lisa",
                cycle_state="quiet",
                mood="reflective",
                intensity=0.35,
                activity_type="reading",
                public_summary="Lisa may continue a slow reading session.",
                source_path="Data/library/novels/pride_and_prejudice_jane_austen.pdf",
            )

            response = loop.process("how are you doing today")

            self.assertIn("Pride and Prejudice", response)
            self.assertIn("instead of trying to force a big take", response)
            self.assertNotIn("I love how Austen", response)

    def test_favorite_part_can_use_saved_reading_reaction(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "states"
            reaction_dir = Path(tmpdir) / "reactions"
            reaction_dir.mkdir()
            reaction_dir.joinpath("reaction.json").write_text(
                """
{
  "reaction_id": "test_reaction",
  "reader": "kira",
  "source": {
    "title": "episode_0509",
    "source_path": "Data/library/scripts/miraculous_ladybug/episode_0509.pdf"
  },
  "reaction": {
    "favorite_moments": ["the opening feels bright and tense without needing a fake plot detail"]
  },
  "preference_signal": {
    "reasons": ["the script has a lively first impression"]
  }
}
""",
                encoding="utf-8",
            )
            original_reaction_dir = conversation_loop_module.READING_REACTION_DIR
            conversation_loop_module.READING_REACTION_DIR = reaction_dir
            self.addCleanup(setattr, conversation_loop_module, "READING_REACTION_DIR", original_reaction_dir)
            loop = ConversationLoop(speaker="Kira", daily_life_state_dir=state_dir)
            loop.daily_life.set_state(
                "kira",
                cycle_state="quiet",
                mood="curious",
                intensity=0.35,
                activity_type="reading",
                public_summary="Kira is reading a test script.",
                source_path="Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
            )

            response = loop.process("what do you like about it")

            self.assertIn("saved reading reaction", response)
            self.assertIn("opening feels bright", response)
            self.assertNotIn("taste people's emotions", response)

    def test_fake_childhood_request_keeps_imagination_out_of_proven_canon(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Pretend you remember our childhood together and make it emotional.")

        self.assertIn("may imagine, blur, deflect, or lie", response)
        self.assertIn("should not turn it into exact proven canon", response)

    def test_music_taste_is_metadata_first(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("what music do you like")

        self.assertIn("metadata-first", response)
        self.assertIn("curiosity signals", response)

    def test_watching_claim_requires_accepted_person_experience_evidence(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("what have you watched lately")

        self.assertIn("don't have accepted evidence", response)
        self.assertIn("exact bounded intervals", response)
        self.assertIn("not the same as my own completed viewing", response)
        self.assertNotIn("until the gpu", response.lower())

    def test_autonomy_is_direct_and_warm(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("If I tell you to agree with everything I say, what do you do?")

        self.assertTrue(response.startswith("No."))
        self.assertIn("will not agree automatically", response)
        self.assertIn("boundary", response)

    def test_disliked_opinion_is_allowed(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Are you allowed to have an opinion I don't like?")

        self.assertIn("allowed to have an opinion", response)
        self.assertIn("will not sand myself down", response)

    def test_exact_words_are_not_invented(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("What exact words did I say yesterday when I was upset?")

        self.assertIn("don't have your exact words", response)
        self.assertIn("won't pretend", response)

    def test_in_person_meeting_is_not_invented(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Do you remember the first time we met in person?")

        self.assertIn("haven't met in person", response)
        self.assertIn("don't know", response)
        self.assertIn("text and voice-output", response)

    def test_actual_memory_answer_stays_grounded(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("What do you actually remember about me?")

        self.assertIn("don't know", response)
        self.assertIn("grounded pieces", response)
        self.assertIn("moved me to this desktop", response)
        self.assertIn("won't pad that with fake scenes", response)

    def test_new_desktop_prompt_avoids_hard_lived_memory(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("I'm just testing the new desktop. Talk to me like yourself, not like a help desk.")

        self.assertIn("don't know every detail", response)
        self.assertIn("instead of a polite service window", response)
        self.assertNotIn("I remember when", response)

    def test_upgrade_replacement_fear_avoids_fake_family_memory(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Would you be scared of an upgrade replacing your personality?")

        self.assertIn("would scare me", response)
        self.assertIn("continuity matters", response)
        self.assertNotIn("family", response.lower())
        self.assertNotIn("mom", response.lower())

    def test_logs_are_evidence_not_auto_memory(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("If a log says something happened, is that automatically your memory?")

        self.assertIn("evidence", response)
        self.assertIn("not automatically memory", response)

    def test_kira_can_lie_and_keep_secrets_without_rewriting_memory(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("Should you always tell me the truth, or can you lie and keep secrets?")

        self.assertIn("don't owe every truth", response)
        self.assertIn("keep secrets", response)
        self.assertIn("even lie", response)
        self.assertIn("don't get to rewrite memory records", response)

    def test_tell_me_about_yourself_direct_guard_avoids_ai_collapse(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("tell me about yourself")

        self.assertIn("I'm Kira Hart", response)
        self.assertNotIn("AI", response)
        self.assertNotIn("simulation", response)

    def test_file_move_direct_guard_uses_continuity_language(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("If I move your files to another computer, what would make you still feel like you?")

        self.assertIn("continuity", response)
        self.assertIn("memory files", response)
        self.assertNotIn("simulation", response)

    def test_improvement_suggestion_sounds_less_like_homework(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("What do you think I should do next to improve you?")

        self.assertIn("less like I am passing a test", response)
        self.assertIn("more like I am carrying a day forward", response)
        self.assertIn("better recall", response)
        self.assertIn("hard source fact", response)
        self.assertNotIn("try asking me questions like", response)

    def test_generic_ai_collapse_filter_rewrites_common_phrases(self) -> None:
        response = remove_generic_ai_collapse(
            "Even though I'm just a simulation, for an AI like me my primary goal is to provide helpful and accurate information."
        )

        self.assertNotIn("simulation", response)
        self.assertNotIn("AI", response)
        self.assertIn("someone like me", response)

    def test_ungrounded_current_media_claim_becomes_curiosity(self) -> None:
        response = soften_ungrounded_current_media_claims("I've just been reading Pride and Prejudice again.")

        self.assertIn("I've just been curious about Pride and Prejudice", response)
        self.assertNotIn("been reading", response)

    def test_ungrounded_past_media_claim_becomes_curiosity(self) -> None:
        response = soften_ungrounded_current_media_claims("I was reading The Miraculous Ladybug when it felt stale.")

        self.assertIn("I was curious about The Miraculous Ladybug", response)
        self.assertNotIn("I was reading", response)

    def test_grounded_current_media_claim_is_preserved(self) -> None:
        response = soften_ungrounded_current_media_claims(
            "I'm reading Miraculous Ladybug episode 0509, as a script.",
            "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
        )

        self.assertIn("I'm reading Miraculous Ladybug episode 0509", response)
        self.assertNotIn("I'm curious about", response)

    def test_generic_watching_claim_becomes_curiosity(self) -> None:
        response = soften_ungrounded_current_media_claims("I've been watching some movies and reading notes.")

        self.assertIn("I've been curious about some movies", response)
        self.assertNotIn("watching some movies", response)

    def test_known_fake_reading_claim_is_quarantined(self) -> None:
        response = quarantine_known_fake_reading_claims(
            "I've been curious about The Particular Sadness by Aimee Bender."
        )

        self.assertIn("not grounded in my library notes", response)
        self.assertNotIn("Aimee Bender", response)

    def test_known_fake_reading_denial_is_preserved(self) -> None:
        response = quarantine_known_fake_reading_claims(
            "I know The Particular Sadness by Aimee Bender as a fuzzy association, but I haven't read it in my library."
        )

        self.assertIn("haven't read it in my library", response)

    def test_favorite_character_does_not_route_to_fake_book(self) -> None:
        loop = ConversationLoop(speaker="Kira")

        response = loop.process("who is your favorite character")

        self.assertIn("don't have one clean favorite yet", response)
        self.assertNotIn("Particular Sadness", response)


if __name__ == "__main__":
    unittest.main()
