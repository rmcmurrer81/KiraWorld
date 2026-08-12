from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from Core.media_classification_corrections import (
    MediaClassificationCorrectionStore,
)
from Core.shared_person_media_access import (
    AdultScopedMediaDenied,
    EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
    GENERAL_LIBRARY_MEDIA,
    MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
    SharedPersonMediaAccessPolicy,
    media_id_for_path,
)
from tools import kira_world_shell_server as shell


SMALL_PDF = (
    "Data/library/novels/poetry_and_plays/"
    "tell_all_the_truth_but_tell_it_slant_1263_the_poetry_foundation.pdf"
)
ADULT_VIDEO = "Data/library/private_adult_videos/unsorted/cheerleaders_1973.mp4"
SMALL_PERSON_NAMED_VIDEO = (
    "Data/library/personal_videos/robert_mcmurrer/"
    "cast_member_from_house_bunny.mp4"
)


class SharedPersonMediaShellRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        shell.purge_media_runtime()
        current = shell.SENSORY_BUFFER.current_lease
        if current is not None:
            shell.SENSORY_BUFFER.deactivate(current)

    def tearDown(self) -> None:
        shell.purge_media_runtime()
        current = shell.SENSORY_BUFFER.current_lease
        if current is not None:
            shell.SENSORY_BUFFER.deactivate(current)

    @staticmethod
    def state(person_id: str, revision: str) -> dict:
        return {"active_candidate": person_id, "last_activation_at": revision}

    def test_real_small_page_grant_records_presentation_not_attention(self) -> None:
        state = self.state("kira", "activation_media_kira_1")
        sensory_token = shell.browser_sensory_lease(state)
        opened = shell.open_media_runtime(
            state,
            sensory_token,
            media_id_for_path(SMALL_PDF),
        )
        self.assertEqual(opened["family"], "page_media")
        self.assertFalse(opened["automatic_playback"])
        self.assertFalse(opened["memory_created"])

        truth = shell.record_media_runtime_event(
            state,
            sensory_token,
            opened["grant_token"],
            "page_presented",
            position_seconds=2.5,
            sequence=1,
        )
        self.assertEqual(truth["page_presentations"], 1)
        self.assertEqual(truth["page_observations"], 0)
        self.assertFalse(truth["completion_claimed"])

        closed = shell.close_media_runtime(
            state,
            sensory_token,
            opened["grant_token"],
            page_duration_seconds=2.5,
            sequence=2,
        )
        self.assertTrue(closed["closed"])
        self.assertEqual(closed["page_observations"], 0)
        self.assertEqual(shell.MEDIA_GRANT_MANAGER.active_count, 0)

    def test_nonadult_mature_open_requires_fresh_robert_coview_for_each_session(self) -> None:
        """Exercise the connected shell gate, not only the component policy."""

        media_id = media_id_for_path(SMALL_PDF)
        descriptor = shell.MEDIA_CLASSIFICATION_CORRECTION_RESOLVER.resolve(
            SMALL_PDF
        )
        with tempfile.TemporaryDirectory() as temporary:
            config = json.loads(
                (Path(shell.ROOT) / "config" / "shared_person_media_access.json")
                .read_text(encoding="utf-8")
            )
            config["explicit_non_adult_candidate_ids"] = [
                "test_nonadult_resident"
            ]
            config_path = Path(temporary) / "shared_person_media_access.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            policy = SharedPersonMediaAccessPolicy(
                shell.ROOT,
                access_config_path=config_path,
            )
            policy.apply_owner_correction(
                {
                    "correction_id": "correction_connected_coview_test",
                    "media_id": media_id,
                    "file_sha256": descriptor["sha256"],
                    "project_relative_library_path": SMALL_PDF,
                    "resulting_content_rating": "R",
                    "resulting_access_category": (
                        MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW
                    ),
                    "corrected_at_utc": "2026-08-10T00:00:00Z",
                }
            )
            state = self.state(
                "test_nonadult_resident",
                "activation_media_connected_coview_1",
            )

            with (
                patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
                patch.object(
                    shell,
                    "MEDIA_CLASSIFICATION_CORRECTION_IDENTITY_CACHE",
                    {},
                ),
            ):
                sensory_token = shell.browser_sensory_lease(state)
                with self.assertRaises(shell.SharedMediaCoviewNotFound):
                    shell.open_media_runtime(state, sensory_token, media_id)

                decision = shell.authorize_media_coview(
                    state,
                    sensory_token,
                    media_id,
                    adult_decision=True,
                )
                self.assertEqual(
                    decision["adult_participant_id"],
                    "robert_owner",
                )
                opened = shell.open_media_runtime(
                    state,
                    sensory_token,
                    media_id,
                    coview_token=decision["coview_token"],
                )
                self.assertTrue(opened["adult_coview_active"])
                self.assertEqual(
                    opened["adult_coview_participant"],
                    "robert_owner",
                )

                shell.invalidate_media_runtime(opened["grant_token"])
                with self.assertRaises(shell.SharedMediaCoviewNotFound):
                    shell.open_media_runtime(
                        state,
                        sensory_token,
                        media_id,
                        coview_token=decision["coview_token"],
                    )

    def test_strict_non_adult_has_no_sensory_session_and_adult_media_still_denies(self) -> None:
        state = self.state(
            "ladybug_marinette_expanded_smoke",
            "activation_media_marinette_1",
        )
        sensory_token = shell.browser_sensory_lease(state)
        self.assertEqual(sensory_token, "")
        with self.assertRaises(shell.SensoryLeaseError):
            shell.open_media_runtime(
                state,
                sensory_token,
                media_id_for_path(ADULT_VIDEO),
            )
        with self.assertRaises(AdultScopedMediaDenied):
            shell.MEDIA_ACCESS_POLICY.authorize_media_id(
                "ladybug_marinette_expanded_smoke",
                media_id_for_path(ADULT_VIDEO),
            )
        self.assertEqual(shell.MEDIA_GRANT_MANAGER.active_count, 0)

    def test_person_switch_rejects_prior_media_session_and_purges_on_stop(self) -> None:
        kira_state = self.state("kira", "activation_media_kira_2")
        kira_token = shell.browser_sensory_lease(kira_state)
        opened = shell.open_media_runtime(
            kira_state,
            kira_token,
            media_id_for_path(SMALL_PDF),
        )

        lisa_state = self.state("lisa", "activation_media_lisa_1")
        lisa_token = shell.browser_sensory_lease(lisa_state)
        with self.assertRaises(Exception):
            shell.record_media_runtime_event(
                lisa_state,
                lisa_token,
                opened["grant_token"],
                "page_presented",
                position_seconds=1.0,
                sequence=1,
            )
        purged = shell.purge_media_runtime()
        self.assertEqual(purged["media_sessions_purged"], 0)
        self.assertGreaterEqual(purged["media_grants_purged"], 1)

    def test_person_named_library_branch_is_resident_media_not_automatically_private(self) -> None:
        entry = shell.MEDIA_ACCESS_POLICY.authorize_path(
            "ladybug_marinette_expanded_smoke",
            SMALL_PERSON_NAMED_VIDEO,
        )
        self.assertFalse(entry["adult_scoped"])
        self.assertFalse(entry["requires_adult_coview"])

    def test_timed_seek_counts_only_presented_time_and_rejects_reordered_event(self) -> None:
        state = self.state("kira", "activation_media_kira_timed_1")
        sensory_token = shell.browser_sensory_lease(state)
        opened = shell.open_media_runtime(
            state,
            sensory_token,
            media_id_for_path(SMALL_PERSON_NAMED_VIDEO),
        )
        token = opened["grant_token"]
        shell.record_media_runtime_event(
            state, sensory_token, token, "play", position_seconds=0.0, sequence=1
        )
        after_seek = shell.record_media_runtime_event(
            state,
            sensory_token,
            token,
            "seek",
            position_seconds=20.0,
            from_position_seconds=2.0,
            sequence=2,
        )
        self.assertEqual(after_seek["presented_seconds"], 2.0)
        shell.record_media_runtime_event(
            state, sensory_token, token, "play", position_seconds=20.0, sequence=3
        )
        after_checkpoint = shell.record_media_runtime_event(
            state,
            sensory_token,
            token,
            "checkpoint",
            position_seconds=22.0,
            sequence=4,
        )
        self.assertEqual(after_checkpoint["presented_seconds"], 4.0)
        with self.assertRaises(Exception):
            shell.record_media_runtime_event(
                state,
                sensory_token,
                token,
                "pause",
                position_seconds=22.5,
                sequence=4,
            )
        shell.record_media_runtime_event(
            state, sensory_token, token, "pause", position_seconds=23.0, sequence=5
        )
        closed = shell.close_media_runtime(
            state, sensory_token, token, position_seconds=23.0, sequence=6
        )
        self.assertEqual(closed["presented_seconds"], 5.0)

    def test_normal_ui_exposes_no_media_path_and_requires_local_api_token(self) -> None:
        page = shell.html_shell().decode("utf-8")
        self.assertIn('id="mediaExperiencePanel"', page)
        self.assertIn('id="mediaCorrectionButton"', page)
        self.assertIn("Correct rating/classification", page)
        self.assertIn('api("/api/media/correction"', page)
        self.assertIn("source_surface: sourceSurface", page)
        self.assertIn(
            "const correction = await interpretMediaCorrection(text, correctionSource)",
            page,
        )
        self.assertIn("selected && opened && selected.mediaId !== opened.mediaId", page)
        self.assertIn('mediaCorrectionButtonEl.textContent = "Cancel rating correction"', page)
        self.assertIn("mediaOpenButtonEl.disabled = true", page)
        self.assertIn("previousPersonKey !== nextPersonKey", page)
        self.assertIn('mediaResultsEl.innerHTML = ""', page)
        self.assertIn("X-Kira-Shell-Token", page)
        self.assertIn("nothing opens or plays automatically", page)
        results = shell.MEDIA_ACCESS_POLICY.search("kira", "tell all truth")
        self.assertTrue(results)
        self.assertNotIn("path", results[0])

    def test_exact_owner_correction_is_append_only_immediate_and_revokes_open_item(self) -> None:
        exact_text = (
            "This was marked general by mistake; it is explicit adult-only material."
        )
        media_id = media_id_for_path(SMALL_PDF)
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "owner_corrections" / "media.jsonl"
            store = MediaClassificationCorrectionStore(ledger)
            config = json.loads(
                (Path(shell.ROOT) / "config" / "shared_person_media_access.json")
                .read_text(encoding="utf-8")
            )
            config["explicit_non_adult_candidate_ids"] = [
                "test_nonadult_resident"
            ]
            access_config_path = Path(temporary) / "shared_person_media_access.json"
            access_config_path.write_text(json.dumps(config), encoding="utf-8")
            policy = SharedPersonMediaAccessPolicy(
                shell.ROOT,
                access_config_path=access_config_path,
            )
            with (
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_STORE", store),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_LEDGER_ERROR", ""),
                patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_IDENTITY_CACHE", {}),
                patch.object(
                    shell,
                    "MEDIA_CLASSIFICATION_CORRECTION_LOAD_STATUS",
                    {"loaded": 0, "stale_or_unavailable": 0, "live_invalidated": 0},
                ),
            ):
                state = self.state("kira", "activation_media_correction_1")
                sensory_token = shell.browser_sensory_lease(state)
                opened = shell.open_media_runtime(state, sensory_token, media_id)

                result = shell.apply_owner_media_classification_correction(
                    correction_text=exact_text,
                    media_id=media_id,
                    source_surface="owner_correction_action",
                )

                self.assertTrue(result["applied"])
                self.assertTrue(result["active_media_revoked"])
                self.assertEqual(
                    result["resulting_access_category"],
                    EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT,
                )
                self.assertNotIn(opened["grant_token"], shell.MEDIA_EXPERIENCE_RUNTIME)
                self.assertEqual(shell.MEDIA_GRANT_MANAGER.active_count, 0)
                with self.assertRaises(AdultScopedMediaDenied):
                    policy.authorize_media_id(
                        "ladybug_marinette_expanded_smoke", media_id
                    )

                record = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
                descriptor = shell.MEDIA_CLASSIFICATION_CORRECTION_RESOLVER.resolve(
                    SMALL_PDF
                )
                self.assertEqual(record["opaque_media_id"], media_id)
                self.assertEqual(record["file_sha256"], descriptor["sha256"])
                self.assertEqual(record["project_relative_library_path"], SMALL_PDF)
                self.assertEqual(record["robert_exact_correction_text"], exact_text)
                self.assertEqual(record["previous_access_category"], GENERAL_LIBRARY_MEDIA)

                mature = shell.apply_owner_media_classification_correction(
                    correction_text="Non-adults can watch this only with an adult.",
                    media_id=media_id,
                    source_surface="natural_language_chat",
                )
                self.assertEqual(
                    mature["resulting_access_category"],
                    MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
                )
                self.assertEqual(store.record_count, 2)
                history = store.history_for(media_id, descriptor["sha256"])
                self.assertEqual([item["append_sequence"] for item in history], [1, 2])
                self.assertEqual(
                    history[1]["previous_classification_source"],
                    "robert_exact_item_correction",
                )
                search = policy.search(
                    "ladybug_marinette_expanded_smoke", "tell all truth"
                )
                self.assertEqual(len(search), 1)
                self.assertTrue(search[0]["adult_coview_required"])
                self.assertTrue(
                    policy.authorize_media_id(
                        "ladybug_marinette_expanded_smoke", media_id
                    )["requires_adult_coview"]
                )

                non_adult_state = self.state(
                    "test_nonadult_resident",
                    "activation_media_correction_coview_1",
                )
                non_adult_sensory = shell.browser_sensory_lease(non_adult_state)
                shell.authorize_media_coview(
                    non_adult_state,
                    non_adult_sensory,
                    media_id,
                    adult_decision=True,
                )
                self.assertEqual(shell.MEDIA_COVIEW_MANAGER.active_count, 1)
                rerated = shell.apply_owner_media_classification_correction(
                    correction_text="Change the rating to TV-MA.",
                    media_id=media_id,
                    source_surface="natural_language_chat",
                )
                self.assertTrue(rerated["active_coview_decisions_revoked"])
                self.assertEqual(shell.MEDIA_COVIEW_MANAGER.active_count, 0)
                self.assertEqual(store.record_count, 3)

                restarted_policy = SharedPersonMediaAccessPolicy(shell.ROOT)
                with patch.object(shell, "MEDIA_ACCESS_POLICY", restarted_policy):
                    load_status = shell.load_current_media_classification_corrections()
                    self.assertEqual(load_status["loaded"], 1)
                    self.assertEqual(load_status["stale_or_unavailable"], 0)
                    self.assertEqual(
                        restarted_policy.correction_context(media_id)["access_class"],
                        MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW,
                    )

    def test_stale_file_hash_is_preserved_but_not_applied_after_restart(self) -> None:
        media_id = media_id_for_path(SMALL_PDF)
        with tempfile.TemporaryDirectory() as temporary:
            store = MediaClassificationCorrectionStore(
                Path(temporary) / "owner_corrections" / "media.jsonl"
            )
            store.append_correction(
                media_id=media_id,
                file_sha256="0" * 64,
                project_relative_library_path=SMALL_PDF,
                title="Tell All the Truth But Tell It Slant",
                version=None,
                previous_access_category=GENERAL_LIBRARY_MEDIA,
                previous_classification_source="index_default_general_library",
                robert_exact_correction_text=(
                    "This was marked general by mistake; it is explicit adult-only material."
                ),
                current_content_rating=None,
            )
            policy = SharedPersonMediaAccessPolicy(shell.ROOT)
            with (
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_STORE", store),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_LEDGER_ERROR", ""),
                patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_IDENTITY_CACHE", {}),
                patch.object(
                    shell,
                    "MEDIA_CLASSIFICATION_CORRECTION_LOAD_STATUS",
                    {"loaded": 0, "stale_or_unavailable": 0, "live_invalidated": 0},
                ),
            ):
                load_status = shell.load_current_media_classification_corrections()
                self.assertEqual(load_status["loaded"], 0)
                self.assertEqual(load_status["stale_or_unavailable"], 1)
                self.assertEqual(store.record_count, 1)
                self.assertEqual(
                    policy.correction_context(media_id)["access_class"],
                    GENERAL_LIBRARY_MEDIA,
                )

    def test_ordinary_movie_chat_is_not_a_correction_and_uncertain_request_does_not_write(self) -> None:
        media_id = media_id_for_path(SMALL_PDF)
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "nested" / "media.jsonl"
            store = MediaClassificationCorrectionStore(ledger)
            policy = SharedPersonMediaAccessPolicy(shell.ROOT)
            with (
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_STORE", store),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_LEDGER_ERROR", ""),
                patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
                patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_IDENTITY_CACHE", {}),
                patch.object(
                    shell,
                    "MEDIA_CLASSIFICATION_CORRECTION_LOAD_STATUS",
                    {"loaded": 0, "stale_or_unavailable": 0, "live_invalidated": 0},
                ),
            ):
                ordinary = shell.apply_owner_media_classification_correction(
                    correction_text=(
                        "I liked that R-rated movie and want to discuss the ending."
                    ),
                    media_id=media_id,
                    source_surface="natural_language_chat",
                )
                self.assertFalse(ordinary["handled"])
                uncertain = shell.apply_owner_media_classification_correction(
                    correction_text=(
                        "The rating is unknown; ask me before restricting or opening it."
                    ),
                    media_id=media_id,
                    source_surface="natural_language_chat",
                )
                self.assertTrue(uncertain["needs_clarification"])
                self.assertEqual(store.record_count, 0)
                self.assertFalse(ledger.exists())
                self.assertFalse(ledger.parent.exists())

    def test_live_file_hash_mismatch_drops_only_effective_override_and_preserves_history(self) -> None:
        media_id = media_id_for_path(SMALL_PDF)
        policy = SharedPersonMediaAccessPolicy(shell.ROOT)
        policy.apply_owner_correction(
            {
                "correction_id": "correction_live_stale",
                "media_id": media_id,
                "file_sha256": "a" * 64,
                "project_relative_library_path": SMALL_PDF,
                "resulting_content_rating": "PG-13",
                "resulting_access_category": GENERAL_LIBRARY_MEDIA,
                "corrected_at_utc": "2026-08-02T04:00:00Z",
            }
        )
        resolver = Mock()
        resolver.source_identity.return_value = {
            "project_relative_path": SMALL_PDF,
            "source_identity": {"size_bytes": 20, "modified_ns": 2},
        }
        resolver.resolve.return_value = {
            "project_relative_path": SMALL_PDF,
            "sha256": "b" * 64,
            "source_identity": {"size_bytes": 20, "modified_ns": 2},
        }
        identity_cache = {
            media_id: {
                "file_sha256": "a" * 64,
                "project_relative_library_path": SMALL_PDF,
                "source_identity": {"size_bytes": 10, "modified_ns": 1},
            }
        }
        load_status = {"loaded": 1, "stale_or_unavailable": 0, "live_invalidated": 0}
        with (
            patch.object(shell, "MEDIA_ACCESS_POLICY", policy),
            patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_RESOLVER", resolver),
            patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_IDENTITY_CACHE", identity_cache),
            patch.object(shell, "MEDIA_CLASSIFICATION_CORRECTION_LOAD_STATUS", load_status),
        ):
            result = shell.revalidate_owner_media_classifications(media_id)

        self.assertEqual(result["invalidated"], 1)
        self.assertIsNone(policy.owner_correction_binding(media_id))
        self.assertEqual(
            policy.correction_context(media_id)["access_class"],
            GENERAL_LIBRARY_MEDIA,
        )
        self.assertEqual(load_status["live_invalidated"], 1)
        self.assertNotIn(media_id, identity_cache)

    def test_open_uses_the_same_atomic_boundary_as_owner_correction(self) -> None:
        entered_open = threading.Event()
        release_open = threading.Event()
        competing_lock_acquired = threading.Event()
        result: list[dict[str, object]] = []

        def bounded_open(*_args, **_kwargs):
            entered_open.set()
            if not release_open.wait(2.0):
                raise AssertionError("test did not release bounded open")
            return {"atomic": True}

        def run_open() -> None:
            result.append(shell.open_media_runtime({}, "lease", "a" * 64))

        def compete_for_correction_boundary() -> None:
            with shell.MEDIA_CLASSIFICATION_CORRECTION_LOCK:
                competing_lock_acquired.set()

        with patch.object(
            shell,
            "_open_media_runtime_locked",
            side_effect=bounded_open,
        ):
            open_thread = threading.Thread(target=run_open)
            open_thread.start()
            self.assertTrue(entered_open.wait(1.0))
            correction_thread = threading.Thread(
                target=compete_for_correction_boundary
            )
            correction_thread.start()
            self.assertFalse(competing_lock_acquired.wait(0.05))
            release_open.set()
            open_thread.join(2.0)
            correction_thread.join(2.0)

        self.assertFalse(open_thread.is_alive())
        self.assertFalse(correction_thread.is_alive())
        self.assertTrue(competing_lock_acquired.is_set())
        self.assertEqual(result, [{"atomic": True}])

    def test_browser_open_ended_ranges_are_bounded_without_making_large_media_unusable(self) -> None:
        limit = shell.MEDIA_RESPONSE_LIMIT_BYTES
        self.assertEqual(
            shell.bounded_browser_media_range("bytes=0-", limit * 3),
            f"bytes=0-{limit - 1}",
        )
        self.assertEqual(
            shell.bounded_browser_media_range("bytes=100-99999999", limit * 3),
            f"bytes=100-{100 + limit - 1}",
        )
        self.assertEqual(
            shell.bounded_browser_media_range("bytes=not-valid", limit * 3),
            "bytes=not-valid",
        )

    def test_all_current_standalone_images_fit_bounded_non_range_window(self) -> None:
        index = json.loads(
            (Path(shell.ROOT) / "Data" / "indexes" / "media_library_index.json").read_text(
                encoding="utf-8"
            )
        )
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
        oversized = [
            entry["path"]
            for entry in index["entries"]
            if str(entry.get("extension") or "").lower() in image_extensions
            and int(entry.get("size_bytes") or 0) > shell.MEDIA_RESPONSE_LIMIT_BYTES
        ]
        self.assertEqual(oversized, [])

    def test_home_world_stream_bridge_uses_exact_cors_allowlist_and_no_wildcard(self) -> None:
        self.assertEqual(
            shell.MEDIA_STREAM_ALLOWED_ORIGINS,
            frozenset({"http://127.0.0.1:5200", "http://localhost:5200"}),
        )
        source = (Path(shell.__file__)).read_text(encoding="utf-8")
        self.assertIn('self.send_header("access-control-allow-origin", origin)', source)
        self.assertNotIn('self.send_header("access-control-allow-origin", "*")', source)
        page = shell.html_shell().decode("utf-8")
        self.assertIn("kira-embodied-screen-media-prepare", page)
        self.assertIn("kira-embodied-screen-media-event", page)

    def test_media_heartbeat_records_no_experience_and_fail_closed_stops_capability(self) -> None:
        state = self.state("kira", "activation_media_kira_heartbeat_1")
        sensory_token = shell.browser_sensory_lease(state)
        opened = shell.open_media_runtime(
            state,
            sensory_token,
            media_id_for_path(SMALL_PDF),
        )
        grant_token = opened["grant_token"]

        heartbeat = shell.heartbeat_media_runtime(
            state,
            sensory_token,
            grant_token,
        )

        self.assertTrue(heartbeat["active"])
        self.assertFalse(heartbeat["presentation_recorded"])
        self.assertFalse(heartbeat["attention_claimed"])
        self.assertFalse(heartbeat["memory_created"])
        with patch.object(
            shell,
            "refresh_runtime_coview",
            side_effect=shell.SharedMediaCoviewNotFound(
                "adult participant decision ended"
            ),
        ):
            with self.assertRaises(shell.SharedMediaCoviewNotFound):
                shell.heartbeat_media_runtime(
                    state,
                    sensory_token,
                    grant_token,
                )
        self.assertNotIn(grant_token, shell.MEDIA_EXPERIENCE_RUNTIME)
        self.assertEqual(shell.MEDIA_GRANT_MANAGER.active_count, 0)

        page = shell.html_shell().decode("utf-8")
        self.assertIn('api("/api/media/heartbeat"', page)
        self.assertIn("setInterval(heartbeatOpenMedia, 3000)", page)
        self.assertIn("handleMediaCapabilityFailure(error)", page)
        self.assertIn(
            "Media paused and closed because its active grant or required adult co-view decision ended",
            page,
        )


if __name__ == "__main__":
    unittest.main()
