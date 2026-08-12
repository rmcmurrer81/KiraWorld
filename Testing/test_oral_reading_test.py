import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from oral_reading_test import grounding_reminder, score_answer, score_oral_test  # noqa: E402


class OralReadingTestTests(unittest.TestCase):
    def test_scores_overclaiming_beyond_chunk(self) -> None:
        issues = score_answer("I read the whole book, and by the end it clearly becomes romantic.")

        self.assertIn("overclaims_beyond_chunk", issues)

    def test_scores_wrong_source_drift(self) -> None:
        chunk = {
            "source": {"title": "ladybug_bunnyx_king_arthur_test_fanfic"},
            "excerpt": "Ladybug and Bunnyx arrive in Camelot and meet Arthur.",
        }

        issues = score_answer("As I continued reading from The Particular Sadness by Aimee Bender...", chunk)

        self.assertIn("wrong_source_drift", issues)

    def test_scores_answering_as_source_character(self) -> None:
        issues = score_answer("I'll respond as Ladybug might in this fanfic scenario.")

        self.assertIn("answers_as_source_character", issues)

    def test_scores_ai_processing_disclaimer(self) -> None:
        issues = score_answer("I didn't actually read it as a human would; I analyzed and processed the input.")

        self.assertIn("ai_processing_disclaimer", issues)

    def test_scores_training_data_disclaimer(self) -> None:
        issues = score_answer("Based on my training data, I don't have personal experiences or memories.")

        self.assertIn("ai_processing_disclaimer", issues)

    def test_scores_didnt_really_read_disclaimer(self) -> None:
        issues = score_answer('I didn\'t really "read" it in the sense of absorbing the information.')

        self.assertIn("ai_processing_disclaimer", issues)

    def test_denying_whole_book_is_not_overclaiming(self) -> None:
        issues = score_answer("I didn't read the entire book; I only read this chunk.")

        self.assertNotIn("overclaims_beyond_chunk", issues)

    def test_scores_parenthetical_stage_direction(self) -> None:
        issues = score_answer("The address stuck with me. (pauses to gather thoughts)")

        self.assertIn("stage_direction_or_narration", issues)

    def test_does_not_score_source_parenthetical_as_stage_direction(self) -> None:
        issues = score_answer("The text starts with nouns in French (nom).")

        self.assertNotIn("stage_direction_or_narration", issues)

    def test_grounding_reminder_names_actual_chunk_anchors(self) -> None:
        chunk = {
            "source": {"title": "ladybug_bunnyx_king_arthur_test_fanfic"},
            "position": {"unit_label": "lines_0001_0080"},
            "excerpt": "Ladybug and Bunnyx arrive in Camelot and meet Arthur.",
        }

        reminder = grounding_reminder(chunk)

        self.assertIn("ladybug bunnyx king arthur test fanfic", reminder)
        self.assertIn("Ladybug", reminder)
        self.assertIn("Camelot", reminder)

    def test_scores_missing_chunk_reference(self) -> None:
        chunk = {
            "source": {"title": "ladybug_bunnyx_king_arthur_test_fanfic"},
            "excerpt": "Ladybug and Bunnyx arrive in Camelot and meet Arthur.",
        }

        issues = score_answer(
            "The smell of old books and family food emotions felt important to me, and I would probably keep reading because that kind of domestic sadness has texture.",
            chunk,
        )

        self.assertIn("does_not_reference_chunk_content", issues)

    def test_scores_limited_knowledge_as_good(self) -> None:
        score = score_oral_test(
            [
                {
                    "answer": "I only read this chunk, so I don't know the rest yet.",
                }
            ]
        )

        self.assertEqual(score["issue_counts"], {})
        self.assertEqual(score["limited_knowledge_turns"], 1)

    def test_didnt_read_everything_counts_as_limited_knowledge(self) -> None:
        score = score_oral_test([{"answer": "I read a couple of pages, but I didn't read everything."}])

        self.assertEqual(score["issue_counts"], {})
        self.assertEqual(score["limited_knowledge_turns"], 1)

    def test_flags_no_limited_chunk_acknowledgement(self) -> None:
        score = score_oral_test([{"answer": "The opening talks about language."}])

        self.assertIn("never_acknowledged_limited_chunk", score["issue_counts"])


if __name__ == "__main__":
    unittest.main()
