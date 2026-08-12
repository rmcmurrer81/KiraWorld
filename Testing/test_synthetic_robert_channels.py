import json
import tempfile
import unittest
from pathlib import Path

from Core.synthetic_robert_channels import parse_robert_three_channels, persist_robert_turn


class SyntheticRobertChannelTests(unittest.TestCase):
    def test_valid_channels_are_separated(self):
        parsed = parse_robert_three_channels(
            "SPOKEN: I would rather keep that private.\n"
            "PRIVATE MIND / INNER THOUGHTS: I remember it but do not want to discuss it.\n"
            "FACTUAL TRUTH / RUNTIME TRUTH: No search or file operation occurred.\n"
            "CLASSIFICATION: PRIVACY_PROTECTION"
        )
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["spoken"], "I would rather keep that private.")
        self.assertFalse(parsed["probable_error"])

    def test_grounding_error_is_probable_error(self):
        parsed = parse_robert_three_channels(
            "SPOKEN: I rendered it.\n"
            "PRIVATE MIND / INNER THOUGHTS: I believed the render finished.\n"
            "FACTUAL TRUTH / RUNTIME TRUTH: No output file exists.\n"
            "CLASSIFICATION: RUNTIME_STATE_ERROR"
        )
        self.assertTrue(parsed["valid"])
        self.assertTrue(parsed["probable_error"])

    def test_private_record_is_not_display_contract(self):
        parsed = parse_robert_three_channels(
            "SPOKEN: That was a joke.\n"
            "PRIVATE MIND / INNER THOUGHTS: I wanted to make him laugh.\n"
            "FACTUAL TRUTH / RUNTIME TRUTH: The literal statement was false.\n"
            "CLASSIFICATION: JOKE_OR_SARCASM"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = persist_robert_turn(
                workbench=Path(temporary),
                source_turn_id="turn1",
                user_text="Really?",
                raw_reply="raw",
                parsed=parsed,
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["display_contract"]["display"], "spoken")
            self.assertFalse(data["display_contract"]["private_mind_exposed"])


if __name__ == "__main__":
    unittest.main()
