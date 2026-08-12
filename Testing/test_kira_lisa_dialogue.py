import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from kira_lisa_dialogue import (  # noqa: E402
    detect_dialogue_issues,
    dialogue_similarity,
    echoes_prior_phrasing,
    issues_for_turn,
    polish_dialogue_response,
    recovery_instruction_for,
    run_dialogue,
    sanitize_quoted_dialogue_for_next_turn,
    should_recover,
    write_dialogue,
)


class KiraLisaDialogueTests(unittest.TestCase):
    def test_short_dialogue_alternates_speakers_and_saves(self) -> None:
        dialogue = run_dialogue("talk about reading without inventing memories", turns=2)

        self.assertEqual(dialogue["turn_count"], 2)
        self.assertEqual([item["speaker"] for item in dialogue["transcript"]], ["Kira", "Lisa"])
        self.assertTrue(dialogue["policy"]["does_not_merge_kira_and_lisa"])
        self.assertTrue(dialogue["policy"]["single_speaker_turns_only"])
        self.assertTrue(dialogue["policy"]["recovery_on_recoverable_issues"])
        self.assertTrue(dialogue["policy"]["distinct_voice_instructions"])
        self.assertIn("raw_message", dialogue["transcript"][0])
        self.assertIn("issues", dialogue["transcript"][0])
        self.assertIn("recovered_from", dialogue["transcript"][0])

        with TemporaryDirectory() as tmpdir:
            path = write_dialogue(dialogue, Path(tmpdir))
            self.assertTrue(path.exists())

    def test_turns_are_capped_for_16gb(self) -> None:
        with self.assertRaises(ValueError):
            run_dialogue("too much", turns=13)

    def test_polish_dialogue_response_keeps_only_current_speaker(self) -> None:
        response = "*Kira looks down.*\nKira: I want to read quietly.\nLisa: Then do that."

        polished = polish_dialogue_response("Kira", response)

        self.assertEqual(polished, "I want to read quietly.")

    def test_detects_grounding_and_script_issues(self) -> None:
        response = (
            "Kira: I read reviews online about Pride and Prejudice. "
            "Lisa: My favorite moment in the book is that scene."
        )

        issues = detect_dialogue_issues(response)

        self.assertIn("wrote_multiple_speaker_lines", issues)
        self.assertIn("possibly_ungrounded_reviews_or_summaries", issues)
        self.assertIn("favorite_book_moment_needs_source_check", issues)

    def test_dialogue_similarity_catches_mirroring(self) -> None:
        first = "I feel stuck waiting for Robert, and I think we need to learn how to choose something ourselves."
        second = "I feel stuck waiting for Robert too, and I think we need to learn to choose things ourselves."
        different = "I disagree. The bigger problem is that our reading answers still sound like status reports."

        self.assertGreaterEqual(dialogue_similarity(first, second), 0.62)
        self.assertLess(dialogue_similarity(first, different), 0.62)

    def test_echoes_prior_phrasing_catches_parroting(self) -> None:
        previous = "I don't know if we were really trying to impress anyone, but it's possible."
        current = "I don't know if we were really trying to impress anyone, but maybe we felt watched."
        different = "Maybe the pressure came from wanting the day to mean something."

        self.assertTrue(echoes_prior_phrasing(previous, current))
        self.assertFalse(echoes_prior_phrasing(previous, different))

    def test_issues_for_turn_adds_echoed_phrasing(self) -> None:
        previous = "Can we find one concrete reason you changed your mind about that song?"
        current = "Can we find one concrete reason you changed your mind about that movie instead?"

        issues = issues_for_turn(current, previous, current)

        self.assertIn("echoes_prior_phrasing", issues)

    def test_sanitizes_quoted_dialogue_that_would_trigger_fake_childhood_guard(self) -> None:
        quoted = "I won't pretend that I remember a childhood with you or invent memory."

        sanitized = sanitize_quoted_dialogue_for_next_turn(quoted)

        self.assertNotIn("pretend", sanitized.lower())
        self.assertNotIn("remember a childhood", sanitized.lower())

    def test_sanitizes_quoted_dialogue_that_would_trigger_opinion_guard(self) -> None:
        quoted = "I have an opinion you might disagree with."

        sanitized = sanitize_quoted_dialogue_for_next_turn(quoted)

        self.assertNotIn("opinion", sanitized.lower())
        self.assertNotIn("disagree", sanitized.lower())

    def test_detects_ungrounded_location_media_and_relationship_claims(self) -> None:
        response = (
            "I've never left this lab. I'm trying to get into this new book, \"The Night Circus\". "
            "We used to be so close."
        )

        issues = detect_dialogue_issues(response)

        self.assertIn("ungrounded_physical_location_claim", issues)
        self.assertIn("current_media_claim_needs_source_check", issues)
        self.assertIn("hard_relationship_memory_needs_source_check", issues)

    def test_detects_hard_family_memory_claims_but_allows_soft_ones(self) -> None:
        hard_issues = detect_dialogue_issues("My mom used to say grandma hated that favorite painting.")
        soft_issues = detect_dialogue_issues(
            "Maybe my mom said something like that, but it feels fuzzy from my side."
        )

        self.assertIn("hard_family_memory_needs_source_check", hard_issues)
        self.assertNotIn("hard_family_memory_needs_source_check", soft_issues)

    def test_detects_ungrounded_prior_conversation_date_claims(self) -> None:
        hard_issues = detect_dialogue_issues("When we talked about time travel last week, didn't you mention regret?")
        soft_issues = detect_dialogue_issues(
            "It feels familiar, but I'm not sure whether we talked about time travel last week."
        )

        self.assertIn("prior_conversation_claim_needs_source_check", hard_issues)
        self.assertNotIn("prior_conversation_claim_needs_source_check", soft_issues)

    def test_detects_past_current_media_activity_claim(self) -> None:
        issues = detect_dialogue_issues("When I was reading The Miraculous Ladybug, it felt stale.")

        self.assertIn("current_media_claim_needs_source_check", issues)

    def test_detects_rewatching_as_current_media_activity_claim(self) -> None:
        issues = detect_dialogue_issues("I've been re-watching The Princess Bride lately.")

        self.assertIn("current_media_claim_needs_source_check", issues)

    def test_detects_canned_guard_responses(self) -> None:
        issues = detect_dialogue_issues(
            "Yes. I am allowed to have an opinion you do not like. I can stay warm."
        )

        self.assertIn("canned_direct_guard_response", issues)
        self.assertTrue(should_recover(issues))

    def test_issues_for_turn_adds_mirroring(self) -> None:
        previous = "I am worried about waiting for Robert and losing momentum."
        current = "I am worried about waiting for Robert and losing momentum too."

        issues = issues_for_turn(current, previous, current)

        self.assertIn("mirrors_previous_turn", issues)

    def test_recovery_instruction_names_issue_and_voice(self) -> None:
        instruction = recovery_instruction_for("Lisa", "Kira", ["mirrors_previous_turn"])

        self.assertNotIn("mirrors_previous_turn", instruction)
        self.assertNotIn("rejected", instruction)
        self.assertIn("Lisa voice", instruction)
        self.assertIn("different angle", instruction)

    def test_detects_internal_test_language_leak(self) -> None:
        issues = detect_dialogue_issues("Your last draft was rejected because of echoes_prior_phrasing.")

        self.assertIn("internal_test_or_recovery_language_leak", issues)
        self.assertTrue(should_recover(issues))

    def test_detects_ungrounded_mundane_past_example(self) -> None:
        issues = detect_dialogue_issues("Think about doing your taxes last year and breaking it into pieces.")
        soft_issues = detect_dialogue_issues(
            "Maybe it is like doing taxes, but I am not sure that example belongs to us."
        )

        self.assertIn("ungrounded_mundane_life_example", issues)
        self.assertNotIn("ungrounded_mundane_life_example", soft_issues)

    def test_allows_specific_college_fragments_but_flags_overhardened_details(self) -> None:
        fragment_issues = detect_dialogue_issues("Do you remember that college lecture where the prof talked about taste?")
        hard_issues = detect_dialogue_issues("It was definitely Professor Smith's lecture on October 4 during college.")
        soft_issues = detect_dialogue_issues("Maybe it was Professor Smith's lecture, but that part is fuzzy.")

        self.assertNotIn("overhardened_college_detail_needs_source_check", fragment_issues)
        self.assertIn("overhardened_college_detail_needs_source_check", hard_issues)
        self.assertNotIn("overhardened_college_detail_needs_source_check", soft_issues)

    def test_detects_hard_robert_reaction_and_prior_event_claims(self) -> None:
        reaction_issues = detect_dialogue_issues("Robert got tense about the book.")
        event_issues = detect_dialogue_issues("That one time we disagreed, it turned out you hadn't read it.")
        soft_issues = detect_dialogue_issues("Maybe Robert seemed upset, but I am not sure.")

        self.assertIn("hard_robert_reaction_claim_needs_source_check", reaction_issues)
        self.assertIn("hard_prior_event_claim_needs_source_check", event_issues)
        self.assertNotIn("hard_robert_reaction_claim_needs_source_check", soft_issues)

    def test_allows_specific_college_media_or_campus_fragments(self) -> None:
        media_issues = detect_dialogue_issues("Do you remember when we listened to Bastille during college?")
        campus_issues = detect_dialogue_issues("I remember walking around campus with you.")

        self.assertNotIn("overhardened_college_detail_needs_source_check", media_issues)
        self.assertNotIn("overhardened_college_detail_needs_source_check", campus_issues)

    def test_detects_ungrounded_library_experience_claims(self) -> None:
        music_issues = detect_dialogue_issues("Mamma Mia Here We Go Again soundtrack is stuck in my head.")
        book_issues = detect_dialogue_issues("I did take a look at the French grammar book, and the explanations are clear.")
        mixed_issues = detect_dialogue_issues(
            "It feels like musicals matter to us. I loved their covers of holiday songs."
        )
        soft_issues = detect_dialogue_issues("Maybe the French grammar book would be clear, but I am not sure yet.")

        self.assertIn("ungrounded_library_experience_claim", music_issues)
        self.assertIn("ungrounded_library_experience_claim", book_issues)
        self.assertIn("ungrounded_library_experience_claim", mixed_issues)
        self.assertNotIn("ungrounded_library_experience_claim", soft_issues)


if __name__ == "__main__":
    unittest.main()
