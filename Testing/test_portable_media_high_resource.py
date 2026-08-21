from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from Core.shared_person_media_access import SharedPersonMediaAccessPolicy
import build_portable_media_library_index as portable_builder
from tools import kira_world_shell_server as shell
import recommend_reading
import slow_reading
from validate_reading_interest_profile import validate_profile_file
from Core.shared_person_media_access import media_id_for_path


MANIFEST = ROOT / "Data" / "library" / "portable_selection" / "manifest.json"
PORTABLE_INDEX = ROOT / "Data" / "indexes" / "portable_media_library_index.json"
PRIVATE_INDEX = ROOT / "Data" / "indexes" / "media_library_index.json"
PROFILE = ROOT / "config" / "high_resource_media_experiment.json"
LAUNCHER = ROOT / "Start_Kira_High_Resource_Media_Group_Experimental.bat"
DOC = ROOT / "System" / "Docs" / "HIGH_RESOURCE_MEDIA_EXPERIMENT_v1.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class PortableMediaHighResourceTests(unittest.TestCase):
    def test_manifest_and_checked_index_are_exact_non_adult_and_redistribution_aware(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checked = json.loads(PORTABLE_INDEX.read_text(encoding="utf-8"))
        rebuilt = portable_builder.build_index(MANIFEST, project_root=ROOT)
        self.assertEqual(rebuilt, checked)
        self.assertEqual(checked["entry_count"], 6)
        self.assertFalse(checked["private_index_was_read_or_modified"])
        self.assertTrue(checked["usage_policy"]["resident_private_index_remains_primary"])
        self.assertTrue(
            checked["usage_policy"]["no_real_person_avatar_reference_photos"]
        )
        self.assertTrue(checked["usage_policy"]["no_robert_real_photos"])

        entries = checked["entries"]
        self.assertTrue({"novel", "script", "magazine"}.issubset({e["category"] for e in entries}))
        for entry in entries:
            with self.subTest(path=entry["path"]):
                path = ROOT / Path(*Path(entry["path"]).parts)
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, entry["size_bytes"])
                self.assertEqual(sha256(path), entry["sha256"])
                self.assertEqual(entry["content_rating"], "GENERAL")
                self.assertIn(
                    entry["portable_rights"]["lane"],
                    {"project_original", "us_public_domain_or_no_known_restrictions"},
                )
                lowered = entry["path"].casefold()
                for forbidden in (
                    "private_reference_scripts",
                    "private_adult",
                    "avatar/library",
                    "reference_photos",
                    "robert_real",
                ):
                    self.assertNotIn(forbidden, lowered)

        policy = manifest["rights_policy"]
        self.assertFalse(policy["modern_resident_magazines_copied"])
        self.assertFalse(policy["private_reference_scripts_copied"])
        self.assertFalse(policy["real_person_avatar_reference_photos_copied"])
        self.assertFalse(policy["robert_real_photos_copied"])

    def test_portable_index_supports_media_surface_without_private_index(self) -> None:
        policy = SharedPersonMediaAccessPolicy(ROOT)
        # Five PDF rows are media-surface eligible; the Markdown script remains
        # available to paced reading rather than pretending to be page media.
        self.assertGreaterEqual(policy.indexed_supported_count, 5)
        results = policy.search("kira", "reading room")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "magazine")
        self.assertEqual(results[0]["family"], "page_media")
        self.assertFalse(results[0]["adult_scoped"])

    def test_portable_magazine_uses_existing_exact_media_runtime_route(self) -> None:
        source = "Data/library/portable_selection/magazines/reading_room_issue_001.pdf"
        state = {
            "active_candidate": "kira",
            "last_activation_at": "portable_media_runtime_test_revision",
        }
        shell.purge_media_runtime()
        current = shell.SENSORY_BUFFER.current_lease
        if current is not None:
            shell.SENSORY_BUFFER.deactivate(current)
        try:
            sensory_token = shell.browser_sensory_lease(state)
            opened = shell.open_media_runtime(
                state,
                sensory_token,
                media_id_for_path(source),
            )
            self.assertEqual(opened["family"], "page_media")
            self.assertFalse(opened["automatic_playback"])
            self.assertFalse(opened["memory_created"])
            truth = shell.record_media_runtime_event(
                state,
                sensory_token,
                opened["grant_token"],
                "page_presented",
                position_seconds=1.0,
                sequence=1,
            )
            self.assertEqual(truth["page_presentations"], 1)
            self.assertEqual(truth["page_observations"], 0)
            self.assertFalse(truth["completion_claimed"])
            closed = shell.close_media_runtime(
                state,
                sensory_token,
                opened["grant_token"],
                page_duration_seconds=1.0,
                sequence=2,
            )
            self.assertTrue(closed["closed"])
        finally:
            shell.purge_media_runtime()
            current = shell.SENSORY_BUFFER.current_lease
            if current is not None:
                shell.SENSORY_BUFFER.deactivate(current)

    def test_resident_private_index_stays_primary_and_portable_is_additive_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir(parents=True)
            (root / "Data" / "indexes").mkdir(parents=True)
            (root / "config" / "shared_person_media_access.json").write_bytes(
                (ROOT / "config" / "shared_person_media_access.json").read_bytes()
            )
            private_entry = {
                "path": "Data/library/private_primary/book.pdf",
                "name": "Resident title.pdf",
                "extension": ".pdf",
                "media_type": "document",
                "category": "resident_primary",
                "size_bytes": 10,
            }
            private_duplicate = {
                "path": "Data/library/shared/same.pdf",
                "name": "Resident same.pdf",
                "extension": ".pdf",
                "media_type": "document",
                "category": "resident_wins",
                "size_bytes": 20,
            }
            portable_duplicate = dict(private_duplicate)
            portable_duplicate.update(name="Portable same.pdf", category="portable_loses")
            portable_entry = {
                "path": "Data/library/portable_selection/magazines/new.pdf",
                "name": "Portable new.pdf",
                "extension": ".pdf",
                "media_type": "document",
                "category": "portable_addition",
                "size_bytes": 30,
            }
            private_path = root / "Data" / "indexes" / "media_library_index.json"
            portable_path = root / "Data" / "indexes" / "portable_media_library_index.json"
            private_bytes = json.dumps(
                {"index_id": "private", "entries": [private_entry, private_duplicate]},
                indent=2,
            ).encode("utf-8")
            portable_bytes = json.dumps(
                {"index_id": "portable", "entries": [portable_duplicate, portable_entry]},
                indent=2,
            ).encode("utf-8")
            private_path.write_bytes(private_bytes)
            portable_path.write_bytes(portable_bytes)

            policy = SharedPersonMediaAccessPolicy(root)
            self.assertEqual(policy.indexed_supported_count, 3)
            self.assertEqual(policy.authorize_path("kira", private_duplicate["path"])["category"], "resident_wins")
            self.assertEqual(policy.authorize_path("kira", portable_entry["path"])["category"], "portable_addition")
            self.assertEqual(private_path.read_bytes(), private_bytes)
            self.assertEqual(portable_path.read_bytes(), portable_bytes)

    def test_paced_reading_can_build_sessions_for_portable_script_and_magazine(self) -> None:
        for source, expected_type in (
            (
                "Data/library/portable_selection/scripts/the_reading_room_after_rain.md",
                "script",
            ),
            (
                "Data/library/portable_selection/magazines/reading_room_issue_001.pdf",
                "document",
            ),
        ):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as temporary:
                output_path, session = slow_reading.build_session(
                    source,
                    "kira",
                    index_path=PORTABLE_INDEX,
                    output_dir=Path(temporary),
                )
                self.assertEqual(session["material"]["material_type"], expected_type)
                self.assertEqual(session["material"]["source_path"], source)
                self.assertEqual(session["pacing"]["mode"], "slow_consumption")
                self.assertFalse(session["pacing"]["allow_instant_full_ingestion"])
                self.assertTrue(session["memory_policy"]["does_not_become_lived_memory"])
                self.assertFalse(output_path.exists())

    def test_portable_interest_profiles_are_neutral_resident_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing_private = Path(temporary) / "reading_interest_profiles.json"
            with (
                mock.patch.object(
                    recommend_reading, "PRIVATE_PROFILE_PATH", missing_private
                ),
                mock.patch.object(
                    recommend_reading,
                    "PORTABLE_PROFILE_PATH",
                    ROOT / "Data" / "reading" / "portable_reading_interest_profiles.json",
                ),
            ):
                resolved = recommend_reading.resolve_profile_path(missing_private)
        self.assertEqual(resolved, recommend_reading.PORTABLE_PROFILE_PATH)
        profiles = json.loads(resolved.read_text(encoding="utf-8"))
        self.assertEqual(validate_profile_file(profiles), [])
        self.assertEqual({profile["owner"] for profile in profiles}, {"kira", "lisa", "kira_lisa"})
        for profile in profiles:
            with self.subTest(owner=profile["owner"]):
                interests = profile["current_interests"]
                self.assertEqual(interests["active_source_paths"], [])
                self.assertEqual(interests["favorite_source_paths"], [])
                self.assertTrue(
                    profile["privacy"][
                        "portable_defaults_are_not_durable_personal_preferences"
                    ]
                )

    def test_experimental_launcher_is_disabled_by_default_and_uses_existing_capabilities(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('if /I not "%~1"=="--enable-experimental-high-resource" goto DISABLED', source)
        self.assertIn('set "KIRA_WORLD_GROUP_SESSIONS=1"', source)
        self.assertIn('set "KIRA_WORLD_MAX_ACTIVE_SESSIONS=4"', source)
        self.assertIn('set "KIRA_WORLD_RAM_GB_PER_ACTIVE_SESSION=32"', source)
        self.assertIn('call "%~dp0Start_Kira_Text_Voice_Chat.bat"', source)
        self.assertIn("has not been tested on this machine", source)
        self.assertNotIn("Start_Kira_World_Shell.bat", source)
        self.assertLess(source.index("goto DISABLED"), source.index("call \"%~dp0Start_Kira_Text_Voice_Chat.bat\""))

    def test_high_resource_profile_distinguishes_implemented_hardware_and_unconnected(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertFalse(profile["enabled_by_default"])
        self.assertEqual(profile["local_test_status"], "not_run_due_local_ram_and_gpu_restrictions")
        self.assertTrue(profile["hardware_guidance_not_proof"])
        self.assertEqual(profile["hardware_guidance"]["cautious_group_trial_ram_gb"], 64)
        self.assertEqual(profile["hardware_guidance"]["four_session_requested_ceiling_ram_gb"], 128)
        self.assertEqual(profile["requested_runtime"]["requested_max_active_sessions"], 4)
        capability_map = {
            item["capability"]: item["classification"]
            for item in profile["capabilities"]
        }
        self.assertEqual(
            capability_map["multiple_person_text_and_voice_group_routing"],
            "implemented",
        )
        self.assertEqual(capability_map["local_speech_recognition"], "hardware_dependent")
        self.assertEqual(
            capability_map["owner_requested_single_still_vision"],
            "hardware_dependent",
        )
        self.assertEqual(
            capability_map["continuous_semantic_video_understanding"],
            "not_yet_connected",
        )
        self.assertEqual(
            capability_map["simultaneous_animated_3d_group_bodies"],
            "not_yet_connected",
        )
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("not been run or accepted on this machine", doc)
        self.assertIn("planning guidance, not proof", doc)
        self.assertNotIn("Codex", doc)
        self.assertNotIn("handoff", doc.casefold())


if __name__ == "__main__":
    unittest.main()
