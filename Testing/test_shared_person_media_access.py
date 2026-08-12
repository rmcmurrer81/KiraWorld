from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Core.shared_person_media_access import (
    AdultScopedMediaDenied,
    GENERAL_LIBRARY_MEDIA,
    MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
    IndexedMediaNotFound,
    SharedPersonMediaAccessError,
    SharedPersonMediaAccessPolicy,
    media_id_for_path,
)


class SharedPersonMediaAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "Data" / "indexes").mkdir(parents=True)
        (self.root / "Avatar" / "avatar_builder" / "policies").mkdir(parents=True)
        (self.root / "config" / "shared_person_media_access.json").write_text(
            json.dumps(
                {
                    "explicit_adult_candidate_ids": ["kira", "peter_adult"],
                    "explicit_non_adult_candidate_ids": ["marinette"],
                    "explicit_adult_only_path_prefixes": [
                        "Data/library/private_adult_videos/",
                        "Data/library/novels/romance/mature_and_erotic_romance/",
                    ],
                    "explicit_adult_only_exact_paths": [
                        "Data/library/magazines/entertainment_and_culture/sex_magazine_14.pdf"
                    ],
                    "mature_mainstream_path_prefixes": [
                        "Data/library/movies/mature_mainstream/"
                    ],
                    "mature_mainstream_exact_paths": [],
                    "mature_mainstream_metadata_ratings": ["R", "TV-MA"],
                }
            ),
            encoding="utf-8",
        )
        self.ordinary_path = "Data/library/magazines/film_history.pdf"
        self.adult_path = "Data/library/private_adult_videos/sample.mp4"
        self.erotic_path = (
            "Data/library/novels/romance/mature_and_erotic_romance/"
            "eight_erotic_nights.pdf"
        )
        self.sex_magazine_path = (
            "Data/library/magazines/entertainment_and_culture/sex_magazine_14.pdf"
        )
        self.adult_swim_path = (
            "Data/library/video_skits_and_parodies/general/robot_chicken_adult_swim.mp4"
        )
        self.mature_movie_path = "Data/library/movies/mature_mainstream/sample_r_movie.mp4"
        (self.root / "Data" / "indexes" / "media_library_index.json").write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "path": self.ordinary_path,
                            "name": "film_history.pdf",
                            "extension": ".pdf",
                            "media_type": "document",
                            "category": "magazines",
                            "size_bytes": 123,
                        },
                        {
                            "path": self.adult_path,
                            "name": "sample.mp4",
                            "extension": ".mp4",
                            "media_type": "video",
                            "category": "private_adult_media",
                            "size_bytes": 456,
                        },
                        {
                            "path": self.erotic_path,
                            "name": "eight_erotic_nights.pdf",
                            "extension": ".pdf",
                            "media_type": "document",
                            "category": "novel",
                            "size_bytes": 234,
                        },
                        {
                            "path": self.sex_magazine_path,
                            "name": "sex_magazine_14.pdf",
                            "extension": ".pdf",
                            "media_type": "document",
                            "category": "magazines",
                            "size_bytes": 345,
                        },
                        {
                            "path": self.adult_swim_path,
                            "name": "robot_chicken_adult_swim.mp4",
                            "extension": ".mp4",
                            "media_type": "video",
                            "category": "skit_or_parody_video",
                            "size_bytes": 567,
                        },
                        {
                            "path": self.mature_movie_path,
                            "name": "sample_r_movie.mp4",
                            "extension": ".mp4",
                            "media_type": "video",
                            "category": "movie",
                            "content_rating": "R",
                            "size_bytes": 678,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        (self.root / "Avatar" / "avatar_builder" / "policies" / "candidate_identity_variant_registry.json").write_text(
            json.dumps(
                {
                    "candidates": [
                        {"canonical_candidate_id": "registry_adult", "maturity_policy": {"lane": "adult"}},
                        {"canonical_candidate_id": "registry_child", "maturity_policy": {"lane": "non_adult_doll_safe"}},
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.policy = SharedPersonMediaAccessPolicy(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_non_adult_search_never_returns_adult_folder(self) -> None:
        self.assertEqual(self.policy.search("marinette", "private adult"), [])
        results = self.policy.search("marinette", "film")
        self.assertEqual(len(results), 1)
        self.assertNotIn("path", results[0])

    def test_non_adult_direct_id_and_path_both_fail(self) -> None:
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_media_id("marinette", media_id_for_path(self.adult_path))
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_path("marinette", self.adult_path)

    def test_curated_nonliteral_adult_paths_are_denied(self) -> None:
        for path in (self.erotic_path, self.sex_magazine_path):
            with self.subTest(path=path), self.assertRaises(AdultScopedMediaDenied):
                self.policy.authorize_path("marinette", path)

    def test_broad_adult_title_keyword_does_not_false_positive(self) -> None:
        opened = self.policy.authorize_path("marinette", self.adult_swim_path)
        self.assertFalse(opened["adult_scoped"])

    def test_mature_mainstream_is_discoverable_but_requires_fresh_coview(self) -> None:
        results = self.policy.search("marinette", "sample r movie")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["adult_coview_required"])
        opened = self.policy.authorize_path("marinette", self.mature_movie_path)
        self.assertTrue(opened["requires_adult_coview"])
        adult_opened = self.policy.authorize_path("kira", self.mature_movie_path)
        self.assertFalse(adult_opened["requires_adult_coview"])

    def test_unresolved_identity_fails_closed_for_adult_folder(self) -> None:
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_path("unknown_person", self.adult_path)
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_path("registry_child", self.adult_path)

    def test_explicit_and_registry_adults_may_open_adult_folder(self) -> None:
        self.assertTrue(self.policy.authorize_path("kira", self.adult_path)["adult_scoped"])
        self.assertTrue(self.policy.authorize_path("registry_adult", self.adult_path)["adult_scoped"])

    def test_opaque_result_id_resolves_only_exact_index_entry(self) -> None:
        result = self.policy.search("kira", "film history")[0]
        opened = self.policy.authorize_media_id("kira", result["media_id"])
        self.assertEqual(opened["path"], self.ordinary_path)
        with self.assertRaises(IndexedMediaNotFound):
            self.policy.authorize_media_id("kira", "0" * 64)

    def test_path_escape_and_case_variant_are_not_direct_bypasses(self) -> None:
        with self.assertRaises(Exception):
            self.policy.authorize_path("kira", "Data/library/../private_adult_videos/sample.mp4")
        with self.assertRaises(SharedPersonMediaAccessError):
            self.policy.authorize_path("marinette", self.adult_path.upper())

    def test_latest_exact_item_owner_correction_overrides_folder_without_propagating(self) -> None:
        media_id = media_id_for_path(self.adult_path)
        base_record = {
            "correction_id": "correction_000001",
            "media_id": media_id,
            "file_sha256": "a" * 64,
            "project_relative_library_path": self.adult_path,
            "resulting_content_rating": "R",
            "resulting_access_category": MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
            "corrected_at_utc": "2026-08-02T03:00:00Z",
        }
        self.policy.apply_owner_correction(base_record)

        corrected = self.policy.authorize_path("marinette", self.adult_path)
        self.assertTrue(corrected["requires_adult_coview"])
        self.assertEqual(
            corrected["classification_source"], "robert_exact_item_correction"
        )
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_path("marinette", self.erotic_path)

        latest = dict(base_record)
        latest.update(
            correction_id="correction_000002",
            resulting_content_rating="PG-13",
            resulting_access_category=GENERAL_LIBRARY_MEDIA,
            corrected_at_utc="2026-08-02T03:01:00Z",
        )
        context = self.policy.apply_owner_correction(latest)
        self.assertEqual(context["access_class"], GENERAL_LIBRARY_MEDIA)
        self.assertEqual(
            self.policy.owner_correction_binding(media_id)["file_sha256"],
            "a" * 64,
        )
        self.assertEqual(len(self.policy.owner_correction_bindings()), 1)
        self.assertFalse(
            self.policy.remove_owner_correction(
                media_id,
                expected_file_sha256="b" * 64,
            )
        )
        self.assertFalse(
            self.policy.authorize_media_id("marinette", media_id)[
                "requires_adult_coview"
            ]
        )

        self.assertTrue(
            self.policy.remove_owner_correction(
                media_id,
                expected_file_sha256="a" * 64,
            )
        )
        self.assertIsNone(self.policy.owner_correction_binding(media_id))
        with self.assertRaises(AdultScopedMediaDenied):
            self.policy.authorize_media_id("marinette", media_id)

        wrong_path = dict(latest)
        wrong_path["project_relative_library_path"] = self.erotic_path
        with self.assertRaises(SharedPersonMediaAccessError):
            self.policy.apply_owner_correction(wrong_path)


if __name__ == "__main__":
    unittest.main()
