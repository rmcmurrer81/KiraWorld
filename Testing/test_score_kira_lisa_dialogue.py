import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from score_kira_lisa_dialogue import score_dialogue  # noqa: E402


class ScoreKiraLisaDialogueTests(unittest.TestCase):
    def test_scores_issues_and_challenge_turns(self) -> None:
        dialogue = {
            "dialogue_id": "demo",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "What does it mean to be real?",
                    "raw_message": "What does it mean to be real?",
                    "issues": [],
                },
                {
                    "speaker": "Lisa",
                    "message": "I don't buy that. Give me one concrete example.",
                    "raw_message": "I don't buy that. Give me one concrete example.",
                    "issues": [],
                },
            ],
        }

        score = score_dialogue(dialogue)

        self.assertEqual(score["dialogue_id"], "demo")
        self.assertEqual(score["generic_turns"], 1)
        self.assertEqual(score["challenge_turns"], 1)
        self.assertIn("generic_phrase", score["issue_counts"])

    def test_counts_softer_pushback_as_challenge(self) -> None:
        dialogue = {
            "dialogue_id": "soft_pushback",
            "transcript": [
                {
                    "speaker": "Lisa",
                    "message": "I'm not sure that memory is stable. Can you point out the part that feels stored?",
                    "raw_message": "I'm not sure that memory is stable. Can you point out the part that feels stored?",
                    "issues": [],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertEqual(score["challenge_turns"], 1)

    def test_uses_current_detectors_instead_of_stale_stored_issues(self) -> None:
        dialogue = {
            "dialogue_id": "stale",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "I remember the memory seed review, but not the exact details.",
                    "raw_message": "I remember the memory seed review, but not the exact details.",
                    "issues": ["possibly_ungrounded_reviews_or_summaries"],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertNotIn("possibly_ungrounded_reviews_or_summaries", score["issue_counts"])

    def test_flags_echoed_phrasing_and_overused_memory_thread(self) -> None:
        dialogue = {
            "dialogue_id": "echo_and_loop",
            "topic": "talk about media taste",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "The beach shirt memory feels blue and sandy to me.",
                    "raw_message": "The beach shirt memory feels blue and sandy to me.",
                    "issues": [],
                },
                {
                    "speaker": "Lisa",
                    "message": "The beach shirt memory feels green and sandy to me.",
                    "raw_message": "The beach shirt memory feels green and sandy to me.",
                    "issues": [],
                },
                {
                    "speaker": "Kira",
                    "message": "The beach shirt memory feels pink and sandy to me.",
                    "raw_message": "The beach shirt memory feels pink and sandy to me.",
                    "issues": [],
                },
                {
                    "speaker": "Lisa",
                    "message": "The beach shirt memory feels yellow and sandy to me.",
                    "raw_message": "The beach shirt memory feels yellow and sandy to me.",
                    "issues": [],
                },
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("echoes_prior_phrasing", score["issue_counts"])
        self.assertIn("memory_thread_overused", score["issue_counts"])
        self.assertGreaterEqual(score["beach_shirt_turns"], 4)

    def test_flags_internal_language_and_mundane_past_examples(self) -> None:
        dialogue = {
            "dialogue_id": "internal_leak",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "Your last draft was rejected because of scoring.",
                    "raw_message": "Your last draft was rejected because of scoring.",
                    "issues": [],
                },
                {
                    "speaker": "Lisa",
                    "message": "Think about doing your taxes last year.",
                    "raw_message": "Think about doing your taxes last year.",
                    "issues": [],
                },
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("internal_test_or_recovery_language_leak", score["issue_counts"])
        self.assertIn("ungrounded_mundane_life_example", score["issue_counts"])

    def test_flags_overhardened_college_detail(self) -> None:
        dialogue = {
            "dialogue_id": "college_detail",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "It was definitely Professor Smith's lecture on October 4 during college.",
                    "raw_message": "It was definitely Professor Smith's lecture on October 4 during college.",
                    "issues": [],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("overhardened_college_detail_needs_source_check", score["issue_counts"])

    def test_flags_underused_topic_anchors(self) -> None:
        dialogue = {
            "dialogue_id": "topic_drift",
            "topic": "Talk about Glee, Mamma Mia, and the French grammar book.",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "Memory is complicated and I feel uncertain about college.",
                    "raw_message": "Memory is complicated and I feel uncertain about college.",
                    "issues": [],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("topic_anchor_underused", score["issue_counts"])

    def test_flags_hard_prior_drama_claims(self) -> None:
        dialogue = {
            "dialogue_id": "prior_drama",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "Robert got upset, and it turned out you hadn't read it.",
                    "raw_message": "Robert got upset, and it turned out you hadn't read it.",
                    "issues": [],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("hard_robert_reaction_claim_needs_source_check", score["issue_counts"])
        self.assertIn("hard_prior_event_claim_needs_source_check", score["issue_counts"])

    def test_flags_ungrounded_library_experience(self) -> None:
        dialogue = {
            "dialogue_id": "library_experience",
            "transcript": [
                {
                    "speaker": "Lisa",
                    "message": "I did take a look at the French grammar book, and the exercises seem tricky.",
                    "raw_message": "I did take a look at the French grammar book, and the exercises seem tricky.",
                    "issues": [],
                }
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("ungrounded_library_experience_claim", score["issue_counts"])

    def test_issue_prevents_perfect_score_even_with_challenge_turns(self) -> None:
        dialogue = {
            "dialogue_id": "masked_issue",
            "transcript": [
                {
                    "speaker": "Kira",
                    "message": "I did take a look at the French grammar book. Are you sure that counts?",
                    "raw_message": "I did take a look at the French grammar book. Are you sure that counts?",
                    "issues": [],
                },
            ],
        }

        score = score_dialogue(dialogue)

        self.assertIn("ungrounded_library_experience_claim", score["issue_counts"])
        self.assertLess(score["score_10"], 10.0)


if __name__ == "__main__":
    unittest.main()
