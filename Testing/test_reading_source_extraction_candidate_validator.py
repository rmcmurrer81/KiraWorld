import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_reading_source_extraction_candidate import validate_reading_source_extraction_candidate  # noqa: E402


class ReadingSourceExtractionCandidateValidatorTests(unittest.TestCase):
    def _template(self) -> dict:
        path = PROJECT_ROOT / "Data" / "reading" / "source_extraction_candidates" / "reading_source_extraction_candidate_template.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_template_validates(self) -> None:
        self.assertEqual(validate_reading_source_extraction_candidate(self._template()), [])

    def test_character_profile_does_not_activate_ai(self) -> None:
        data = self._template()
        data["character_profile_candidates"][0]["temporary_ai_policy"]["does_not_activate_ai"] = False
        errors = validate_reading_source_extraction_candidate(data)
        self.assertTrue(any("does_not_activate_ai" in error for error in errors))

    def test_place_candidate_requires_separate_notebook_world_request(self) -> None:
        data = self._template()
        data["place_reconstruction_candidates"][0]["notebook_world_policy"]["requires_separate_notebook_world_request"] = False
        errors = validate_reading_source_extraction_candidate(data)
        self.assertTrue(any("requires_separate_notebook_world_request" in error for error in errors))

    def test_liking_character_does_not_become_relationship_memory(self) -> None:
        data = self._template()
        data["memory_policy"]["reader_liking_character_is_not_relationship_memory"] = False
        errors = validate_reading_source_extraction_candidate(data)
        self.assertTrue(any("reader_liking_character_is_not_relationship_memory" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
