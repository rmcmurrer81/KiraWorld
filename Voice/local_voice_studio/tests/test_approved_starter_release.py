from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from .support import ROOT

from kira_local_voice.approved_starter_release import (
    ApprovedStarterVoiceRelease,
    DEFAULT_MANIFEST_RELATIVE_PATH,
)
from kira_local_voice.errors import NotFoundError, ValidationError


PROJECT_ROOT = ROOT.parents[1]


class ApprovedStarterVoiceReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = ApprovedStarterVoiceRelease(PROJECT_ROOT)

    def test_exact_consumer_matrix_resolves_only_two_generic_routes(self) -> None:
        expected_consumers = {
            "avatar_builder.nonbinding_preview.female",
            "avatar_builder.nonbinding_preview.male",
            "hackathon.health_companion.voice.female",
            "hackathon.health_companion.voice.male",
            "hackathon.setsignal.voice.female",
            "hackathon.setsignal.voice.male",
            "hackathon.unitday.voice.female",
            "hackathon.unitday.voice.male",
            "hackathon.unitline.voice.female",
            "hackathon.unitline.voice.male",
            "temporary_creator.nonbinding_preview.female",
            "temporary_creator.nonbinding_preview.male",
        }
        self.assertEqual(set(self.release.payload["consumer_defaults"]), expected_consumers)
        resolved = {self.release.resolve(item).voice_id for item in expected_consumers}
        self.assertEqual(resolved, {"af_heart", "am_fenrir"})
        self.assertTrue(
            all(
                self.release.resolve(item).assignment_class == "generic_product_voice"
                for item in expected_consumers
            )
        )

    def test_unknown_or_subject_selector_fails_closed(self) -> None:
        for selector in ("kira", "lisa", "h_h_holmes", "peter_parker", "new.consumer"):
            with self.subTest(selector=selector), self.assertRaises(NotFoundError):
                self.release.resolve(selector)

    def test_existing_character_authorities_are_preserved_without_audio_export(self) -> None:
        preserved = {
            item["candidate_id"]: item
            for item in self.release.payload["preserved_existing_authorities"]
        }
        self.assertEqual(
            set(preserved),
            {
                "ladybug_marinette_expanded_smoke",
                "peter_parker_spider_man_no_way_home_final_suit",
            },
        )
        self.assertTrue(
            all(item["released_audio_in_this_manifest"] is False for item in preserved.values())
        )

    def test_protected_subjects_have_no_starter_assignment(self) -> None:
        blocked = {
            item["subject_id"]: item
            for item in self.release.payload["blocked_subject_assignments"]
        }
        self.assertEqual(set(blocked), {"kira", "lisa", "h_h_holmes"})
        self.assertTrue(all(item["status"] == "not_assigned" for item in blocked.values()))
        self.assertTrue(all(item["starter_route_id"] is None for item in blocked.values()))

    def test_release_inventory_is_approved_only_and_hash_bound(self) -> None:
        inventory = self.release.release_inventory()
        wavs = [item for item in inventory if item["relative_path"].endswith(".wav")]
        self.assertEqual(
            {item["relative_path"] for item in wavs},
            {
                "Voice/local_voice_studio/auditions/catalog_20260825/calm_female_approved.wav",
                "Voice/local_voice_studio/auditions/catalog_20260825/warm_male_approved.wav",
            },
        )
        joined = "\n".join(item["relative_path"].casefold() for item in inventory)
        for forbidden in ("neutral_audition", "reference_pack", "model_input", ".pt", ".pth", "cache"):
            self.assertNotIn(forbidden, joined)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in inventory))

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name).resolve()
        payload = deepcopy(self.release.payload)
        paths = {DEFAULT_MANIFEST_RELATIVE_PATH.as_posix()}
        paths.add(payload["owner_approval"]["relative_path"])
        paths.add(payload["provider"]["source_relative_path"])
        paths.update(payload["release_boundary"]["distributable_audio_paths"])
        paths.update(payload["release_boundary"]["distributable_metadata_paths"])
        for item in payload["preserved_existing_authorities"]:
            paths.add(item["profile_relative_path"])
        for records in payload["protected_authority_evidence"].values():
            paths.update(item["relative_path"] for item in records)
        for relative in paths:
            source = PROJECT_ROOT / Path(relative)
            target = root / Path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return temporary, root, payload

    @staticmethod
    def _write_manifest(root: Path, payload: dict) -> None:
        path = root / DEFAULT_MANIFEST_RELATIVE_PATH
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_tampered_approval_file_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / payload["owner_approval"]["relative_path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValidationError, "owner approval content digest mismatch"):
            ApprovedStarterVoiceRelease(root)

    def test_unapproved_voice_or_third_route_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        extra = deepcopy(payload["routes"][0])
        extra["route_id"] = "starter.unapproved"
        extra["voice_id"] = "af_bella"
        payload["routes"].append(extra)
        self._write_manifest(root, payload)
        with self.assertRaisesRegex(ValidationError, "exactly two"):
            ApprovedStarterVoiceRelease(root)

    def test_route_cannot_point_to_unapproved_catalog_audition(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        payload["routes"][0]["approved_preview_relative_path"] = (
            "Voice/local_voice_studio/auditions/catalog_20260825/af_heart_neutral_audition.wav"
        )
        self._write_manifest(root, payload)
        with self.assertRaisesRegex(ValidationError, "not an approved release file"):
            ApprovedStarterVoiceRelease(root)

    def test_resident_assignment_flag_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        payload["routes"][0]["resident_assignment_created"] = True
        self._write_manifest(root, payload)
        with self.assertRaisesRegex(ValidationError, "cannot assign"):
            ApprovedStarterVoiceRelease(root)

    def test_protected_subject_cannot_receive_route(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        payload["blocked_subject_assignments"][1]["starter_route_id"] = "starter.calm_female"
        self._write_manifest(root, payload)
        with self.assertRaisesRegex(ValidationError, "received a starter assignment"):
            ApprovedStarterVoiceRelease(root)

    def test_character_profile_drift_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        entry = payload["preserved_existing_authorities"][0]
        path = root / entry["profile_relative_path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValidationError, "content digest mismatch"):
            ApprovedStarterVoiceRelease(root)

    def test_provider_source_drift_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / payload["provider"]["source_relative_path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValidationError, "provider content digest mismatch"):
            ApprovedStarterVoiceRelease(root)

    def test_post_load_preview_drift_fails_closed_before_resolution(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        release = ApprovedStarterVoiceRelease(root)
        path = root / payload["routes"][0]["approved_preview_relative_path"]
        path.write_bytes(path.read_bytes() + b"\x00")
        with self.assertRaisesRegex(ValidationError, "preview content digest mismatch"):
            release.resolve("hackathon.unitday.voice.female")

    def test_post_load_manifest_drift_fails_closed_before_inventory(self) -> None:
        temporary, root, _payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        release = ApprovedStarterVoiceRelease(root)
        path = root / DEFAULT_MANIFEST_RELATIVE_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValidationError, "manifest changed after validation"):
            release.release_inventory()

    def test_linked_preview_fails_closed_when_links_are_available(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / payload["routes"][0]["approved_preview_relative_path"]
        original = path.with_name("approved_preview_original.wav")
        path.replace(original)
        try:
            path.symlink_to(original)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(ValidationError, "link or reparse point"):
            ApprovedStarterVoiceRelease(root)

    def test_consumer_cannot_silently_change_routes(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        payload["consumer_defaults"]["hackathon.unitday.voice.female"] = "starter.warm_male"
        self._write_manifest(root, payload)
        with self.assertRaisesRegex(ValidationError, "consumer defaults differ"):
            ApprovedStarterVoiceRelease(root)

    def test_duplicate_json_key_fails_closed(self) -> None:
        temporary, root, payload = self._fixture()
        self.addCleanup(temporary.cleanup)
        path = root / DEFAULT_MANIFEST_RELATIVE_PATH
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('"schema":', '"schema": "duplicate",\n  "schema":', 1), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
            ApprovedStarterVoiceRelease(root)

    def test_manifest_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "traversal"):
            ApprovedStarterVoiceRelease(
                PROJECT_ROOT,
                manifest_relative_path=Path("../approved_starter_voice_release_v1.json"),
            )


if __name__ == "__main__":
    unittest.main()
