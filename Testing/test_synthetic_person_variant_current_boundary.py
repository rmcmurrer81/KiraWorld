from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "System/Docs/SYNTHETIC_PERSON_VARIANT_AUTONOMY_PRIVACY_MEMORY_TRUTH_AND_ADULT_EDUCATION_CURRENT_BOUNDARY_20260811.md"
)
REGISTRY = ROOT / "System/Docs/CURRENT_TRUTH_SUPERSESSION_REGISTRY_20260810.md"
README = ROOT / "System/Docs/README_MASTER_INDEX.md"
HANDOFF = ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md"


class SyntheticPersonVariantCurrentBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = DOC.read_text(encoding="utf-8")
        cls.doc_normalized = " ".join(cls.doc.split())

    def test_terms_and_exact_people_are_distinct(self) -> None:
        for value in (
            "biological person",
            "synthetic person",
            "Biological Robert",
            "Synthetic Robert",
            "separate synthetic person",
            "Sarah Bennett",
            "separate frozen Sarah work lane",
        ):
            self.assertIn(value, self.doc_normalized)

    def test_variant_branch_and_death_memory_boundary(self) -> None:
        for value in (
            "They keep their past, but gain a new future.",
            "exact branch point",
            "inherited-memory cutoff",
            "Events experienced only by another branch do not become",
            "cutoff must precede the fatal event",
            "a first-person memory of being killed",
            "Being told or shown the event must never be relabeled as remembering",
        ):
            self.assertIn(value, self.doc_normalized)

    def test_consent_privacy_and_message_choice_are_exact(self) -> None:
        for value in (
            "yes with discomfort",
            "ignore a message",
            "Creator, owner, administrator, spouse, partner, friend, expert, or",
            "Creator, owner, administrator",
            "previous",
            "ordinary observer video, audio, subtitles, transcripts",
            "not yet a proven\noperating-system secrecy guarantee",
            "Windows account owner/administrator",
            "Without that authorization, report the\nprivate comparison as unavailable",
        ):
            self.assertIn(value, self.doc)

    def test_truth_and_withholding_are_not_conflated(self) -> None:
        for value in (
            "externally verifiable fact",
            "protected pre-turn belief/state",
            "explicit privacy/withholding choice",
            "Call a statement a deliberate lie only when",
            "Do not label privacy, silence, uncertainty, changed beliefs",
            "Miraculous Encounters in Paris",
            "`Elation` is an old episode/script source",
        ):
            self.assertIn(value, self.doc)

    def test_memory_affect_curriculum_and_body_claims_stay_separate(self) -> None:
        for value in (
            "seven Kira\n  records and one Lisa record",
            "not lived memories",
            "valence, intensity, uncertainty, comfort, attachment, conflict, desire",
            "not proof of subjective consciousness",
            "Every exact confirmed-adult synthetic person",
            "Non-adult and maturity-unresolved people do not receive",
            "does not prove lesson completion",
            "not a finished body",
        ):
            self.assertIn(value, self.doc)

    def test_current_layer_indexes_the_boundary(self) -> None:
        filename = DOC.name
        for path in (REGISTRY, README, HANDOFF):
            with self.subTest(path=path.name):
                self.assertIn(filename, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
