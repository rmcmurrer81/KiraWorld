from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from Core.media_classification_corrections import (
    EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
    GENERAL_LIBRARY_MEDIA,
    MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
    MediaClassificationBindingError,
    MediaClassificationCorrectionStore,
    looks_like_media_classification_correction,
    opaque_media_id_for_path,
    parse_media_classification_correction,
)


class MediaClassificationParserTests(unittest.TestCase):
    def test_owner_examples_parse_to_exact_categories(self) -> None:
        examples = (
            (
                "This is not explicit. It is a mainstream R-rated movie.",
                "R",
                MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            ),
            (
                "Non-adults can watch this only with an adult.",
                "UNRATED",
                MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            ),
            (
                "This belongs in general library media.",
                "UNRATED",
                GENERAL_LIBRARY_MEDIA,
            ),
            (
                "This was marked general by mistake; it is explicit adult-only material.",
                "UNRATED",
                EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
            ),
            (
                "Change the rating to PG-13.",
                "PG-13",
                GENERAL_LIBRARY_MEDIA,
            ),
            (
                "Change the rating to TV-MA.",
                "TV-MA",
                MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            ),
        )
        for text, rating, category in examples:
            with self.subTest(text=text):
                intent = parse_media_classification_correction(text)
                self.assertTrue(intent.applied)
                self.assertFalse(intent.needs_clarification)
                self.assertEqual(intent.resulting_content_rating, rating)
                self.assertEqual(intent.resulting_access_category, category)

    def test_not_explicit_does_not_become_explicit(self) -> None:
        mature = parse_media_classification_correction(
            "No, this is not explicit; it is mainstream R-rated media."
        )
        self.assertEqual(
            mature.resulting_access_category,
            MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
        )
        unresolved = parse_media_classification_correction("This is not explicit.")
        self.assertTrue(unresolved.needs_clarification)

        curly = "This isn’t explicit; it is mainstream R-rated media."
        self.assertTrue(looks_like_media_classification_correction(curly))
        self.assertEqual(
            parse_media_classification_correction(curly).resulting_access_category,
            MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
        )

    def test_unknown_ask_me_language_requires_clarification(self) -> None:
        intent = parse_media_classification_correction(
            "The rating is unknown; ask me before restricting or opening it."
        )
        self.assertFalse(intent.applied)
        self.assertTrue(intent.needs_clarification)
        self.assertIsNone(intent.resulting_access_category)

    def test_negated_change_or_category_never_applies_the_negated_result(self) -> None:
        examples = (
            "Do not change the rating to R.",
            "Don't set the rating to PG-13.",
            "This is not general library media.",
            "This should not be explicit adult-only material.",
            "I don't think this should be explicit adult-only material.",
            "This is a mainstream R-rated movie, but I am not changing this item.",
        )
        for text in examples:
            with self.subTest(text=text):
                intent = parse_media_classification_correction(text)
                self.assertFalse(intent.applied)
                self.assertTrue(intent.needs_clarification)

    def test_filename_words_are_not_classification_evidence(self) -> None:
        for text in (
            "adult_swim_movie.mp4",
            "Open Data/library/movies/something_R_rated_name.mp4",
            "The title is General Hospital.",
        ):
            with self.subTest(text=text):
                self.assertTrue(
                    parse_media_classification_correction(text).needs_clarification
                )

    def test_chat_prefilter_accepts_corrections_but_not_incidental_rated_movie_talk(self) -> None:
        for text in (
            "This is not explicit. It is a mainstream R-rated movie.",
            "Change the rating to PG-13.",
            "This was marked general by mistake; it is explicit adult-only material.",
            "The rating is unknown; ask me before opening it.",
        ):
            with self.subTest(text=text):
                self.assertTrue(looks_like_media_classification_correction(text))
        self.assertFalse(
            looks_like_media_classification_correction(
                "I liked that R-rated movie and want to discuss the ending."
            )
        )


class MediaClassificationCorrectionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = (
            self.root
            / "Data"
            / "owner_corrections"
            / "owner_media_classification_corrections.jsonl"
        )
        self.path = "Data/library/movies/example/movie_v1.mp4"
        self.media_id = opaque_media_id_for_path(self.path)
        self.file_hash = "a" * 64
        self.now = datetime(2026, 8, 1, 20, 5, 6, 123456, tzinfo=timezone.utc)
        self.store = MediaClassificationCorrectionStore(
            self.ledger, utc_clock=lambda: self.now
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def append(self, text: str, **overrides: object):
        values = {
            "media_id": self.media_id,
            "file_sha256": self.file_hash,
            "project_relative_library_path": self.path,
            "title": "Example Movie",
            "version": "theatrical cut",
            "previous_access_category": GENERAL_LIBRARY_MEDIA,
            "previous_classification_source": "automatic_local_metadata",
            "robert_exact_correction_text": text,
            "current_content_rating": "PG-13",
        }
        values.update(overrides)
        return self.store.append_correction(**values)

    def test_append_only_history_and_latest_exact_record_wins(self) -> None:
        first_text = "Non-adults can watch this only with an adult."
        second_text = "This belongs in general library media."
        first = self.append(first_text)
        second = self.append(
            second_text,
            previous_access_category=MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            previous_classification_source="robert_exact_item_natural_language",
        )

        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        self.assertEqual(first.record["append_sequence"], 1)
        self.assertEqual(second.record["append_sequence"], 2)
        self.assertEqual(
            self.store.latest_for(self.media_id, self.file_hash)[
                "resulting_access_category"
            ],
            GENERAL_LIBRARY_MEDIA,
        )
        self.assertEqual(
            [record["robert_exact_correction_text"] for record in self.store.history_for(self.media_id, self.file_hash)],
            [first_text, second_text],
        )

        physical_lines = self.ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(physical_lines), 2)
        self.assertEqual(json.loads(physical_lines[0])["append_sequence"], 1)
        reopened = MediaClassificationCorrectionStore(self.ledger)
        self.assertEqual(reopened.record_count, 2)
        self.assertEqual(
            reopened.latest_for(self.media_id, self.file_hash)["append_sequence"], 2
        )
        self.assertEqual(
            [record["append_sequence"] for record in reopened.latest_records()],
            [2],
        )

    def test_record_contains_exact_binding_provenance_and_timestamp(self) -> None:
        exact_text = "  This belongs in general library media.  "
        result = self.append(exact_text)
        record = result.record
        self.assertEqual(record["opaque_media_id"], self.media_id)
        self.assertEqual(record["file_sha256"], self.file_hash)
        self.assertEqual(record["project_relative_library_path"], self.path)
        self.assertEqual(record["title"], "Example Movie")
        self.assertEqual(record["version"], "theatrical cut")
        self.assertEqual(record["previous_access_category"], GENERAL_LIBRARY_MEDIA)
        self.assertEqual(record["previous_content_rating"], "PG-13")
        self.assertEqual(record["previous_classification_source"], "automatic_local_metadata")
        self.assertEqual(record["robert_exact_correction_text"], exact_text)
        self.assertEqual(record["correction_utc"], "2026-08-01T20:05:06.123456Z")

    def test_file_hash_is_an_exact_version_binding(self) -> None:
        self.append("This belongs in general library media.")
        self.assertIsNotNone(self.store.latest_for(self.media_id, self.file_hash))
        self.assertIsNone(self.store.latest_for(self.media_id, "b" * 64))

    def test_media_id_and_path_mismatch_fails_without_write(self) -> None:
        other_path = "Data/library/movies/example/other.mp4"
        with self.assertRaises(MediaClassificationBindingError):
            self.append(
                "This belongs in general library media.",
                project_relative_library_path=other_path,
            )
        self.assertEqual(self.store.record_count, 0)
        self.assertFalse(self.ledger.exists())

    def test_ambiguous_request_does_not_create_ledger_record(self) -> None:
        result = self.append(
            "The rating is unknown; ask me before restricting or opening it."
        )
        self.assertFalse(result.applied)
        self.assertTrue(result.needs_clarification)
        self.assertEqual(self.store.record_count, 0)
        self.assertFalse(self.ledger.exists())
        self.assertFalse(self.ledger.parent.exists())

    def test_similar_title_does_not_receive_an_item_correction(self) -> None:
        self.append("Change the rating to TV-MA.")
        similar_path = "Data/library/movies/example/movie_v2.mp4"
        similar_id = opaque_media_id_for_path(similar_path)
        self.assertIsNone(self.store.latest_for(similar_id, self.file_hash))
        self.assertIsNone(self.store.latest_for(self.media_id, "c" * 64))

    def test_controlled_root_rejects_ledger_redirection_outside_exact_directory(self) -> None:
        controlled = self.root / "Data" / "owner_corrections"
        controlled.parent.mkdir(parents=True, exist_ok=True)
        with self.assertRaisesRegex(Exception, "directly inside"):
            MediaClassificationCorrectionStore(
                self.root / "elsewhere" / "media.jsonl",
                allowed_root=controlled,
            )

        safe = MediaClassificationCorrectionStore(
            controlled / "media.jsonl",
            allowed_root=controlled,
        )
        self.assertEqual(safe.record_count, 0)
        self.assertFalse(controlled.exists())


if __name__ == "__main__":
    unittest.main()
