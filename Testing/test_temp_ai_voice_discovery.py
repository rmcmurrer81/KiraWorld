from __future__ import annotations

import json
import argparse
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_voice_discovery import (  # noqa: E402
    build_candidate_voice_discovery_request,
    canonical_url,
    resolve_candidate_dir,
    run_voice_discovery,
    validate_request,
)
from tools.discover_temporary_ai_voice import resolve_safe_output_path  # noqa: E402


def base_request(*, kind: str = "fictional_character", living: str = "living") -> dict:
    return {
        "schema_version": 1,
        "request_id": "test_candidate_voice_discovery_v1",
        "candidate_id": "test_candidate",
        "identity_target": {
            "subject_kind": kind,
            "display_name": "Test Person" if kind == "historical_person" else "Test Character",
            "character": {"character_id": "test_character" if kind == "fictional_character" else "", "label": "Test Character" if kind == "fictional_character" else ""},
            "variant": {"variant_id": "home_variant", "label": "Home variant"},
            "speaker": {"speaker_id": "test_speaker", "label": "Test Character"},
            "performer": {
                "performer_id": "test_performer",
                "name": "Living Performer" if living == "living" else "Historical Subject",
                "living_status": living,
                "consent_status": "not_found",
                "consent_evidence_urls": [],
            },
            "version_or_timepoint": "test anchor",
            "identity_aliases": ["Test Character", "Test Person"],
            "excluded_identity_names": ["Wrong Person"],
            "shared_performer_does_not_merge_speakers": True,
        },
        "discovery": {
            "metadata_only": True,
            "allow_media_download": False,
            "allow_audio_extraction": False,
            "allow_model_download": False,
            "recording_queries": [],
            "archive_queries": [],
            "synthetic_model_queries": [],
            "max_results_per_query": 5,
        },
        "seed_recordings": [],
        "seed_synthetic_models": [],
        "historical_voice_factors": {
            "anchor_date_or_era": {"value": "1894", "evidence_urls": ["https://example.org/date"], "confidence": "reviewed"},
            "chronological_age_or_band": {"value": "adult early thirties", "evidence_urls": ["https://example.org/age"], "confidence": "reviewed"},
            "places_and_regions": {"value": ["Chicago"], "evidence_urls": ["https://example.org/place"], "confidence": "reviewed"},
            "education_and_profession": {"value": ["professional education"], "evidence_urls": ["https://example.org/education"], "confidence": "reviewed"},
            "languages_and_dialects": {"value": ["English"], "evidence_urls": ["https://example.org/language"], "confidence": "reviewed"},
            "documented_health_or_voice_notes": {"value": [], "evidence_urls": [], "confidence": "none"},
        },
        "policy": {"activation_allowed": False},
    }


class TemporaryAIVoiceDiscoveryTests(unittest.TestCase):
    def test_voice_discovery_output_rejects_reserved_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request_path = Path(temporary) / "voice_discovery_request.json"
            with self.assertRaisesRegex(ValueError, "reserved candidate file"):
                resolve_safe_output_path(request_path, "temporary_ai_profile.json")
            with self.assertRaisesRegex(ValueError, "reserved candidate file"):
                resolve_safe_output_path(request_path, "activation_plan.json")
            with self.assertRaisesRegex(ValueError, "reserved candidate file"):
                resolve_safe_output_path(request_path, "voice_discovery_request.json")

    def test_voice_discovery_output_rejects_existing_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request_path = Path(temporary) / "voice_discovery_request.json"
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaisesRegex(ValueError, "cannot be a symlink"):
                    resolve_safe_output_path(
                        request_path,
                        "voice_discovery_index_link.json",
                    )

    def test_voice_discovery_output_accepts_scoped_versioned_index_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request_path = Path(temporary) / "voice_discovery_request.json"
            output = resolve_safe_output_path(
                request_path,
                "voice_discovery_index_review_20260716.json",
            )
            self.assertEqual(
                output.name,
                "voice_discovery_index_review_20260716.json",
            )

    def test_canonical_url_removes_tracking_and_normalizes_youtube(self) -> None:
        self.assertEqual(
            canonical_url("https://youtu.be/Vtbo9op9sAI?si=tracking"),
            "https://www.youtube.com/watch?v=Vtbo9op9sAI",
        )

    def test_canonical_url_rejects_local_and_non_public_ip_literals(self) -> None:
        for url in (
            "http://localhost:8768/private",
            "http://service.localhost/private",
            "http://ollama:11434/api",
            "http://printer.local/private",
            "http://127.0.0.1:11434/api",
            "http://10.0.0.5/private",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/private",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                canonical_url(url)

        with self.assertRaises(ValueError):
            canonical_url("https://example.org@127.0.0.1/private")

    def test_generic_candidate_scaffold_is_metadata_only(self) -> None:
        profile = {
            "candidate_id": "future_character",
            "display_name": "Future Character",
            "ai_type": "canon_reconstruction_temp_ai",
            "ui_category": "Fictional Character",
            "gender_preference": "Female",
        }
        request = build_candidate_voice_discovery_request(profile, {})
        self.assertTrue(request["discovery"]["metadata_only"])
        self.assertFalse(request["discovery"]["allow_media_download"])
        self.assertIn("english tts", request["discovery"]["synthetic_model_queries"])
        self.assertIn("female tts", request["discovery"]["synthetic_model_queries"])
        self.assertTrue(
            any("official dialogue clip" in query for query in request["discovery"]["recording_queries"])
        )
        self.assertFalse(request["discovery"]["auto_select_recording"])
        self.assertTrue(request["review_requirements"]["target_only_speaker_verification_required"])
        self.assertTrue(request["review_requirements"]["metadata_rank_never_auto_assigns_a_voice"])
        self.assertFalse(request["policy"]["activation_allowed"])

    def test_request_rejects_media_or_model_download(self) -> None:
        request = base_request()
        request["discovery"]["allow_media_download"] = True
        with self.assertRaisesRegex(ValueError, "cannot enable"):
            validate_request(request)

    def test_request_rejects_local_seed_even_without_metadata_search(self) -> None:
        request = base_request()
        request["seed_recordings"] = [{"url": "http://127.0.0.1:11434/api", "title": "local"}]
        with self.assertRaisesRegex(ValueError, "non-public"):
            run_voice_discovery(request, metadata_search=False)

    def test_request_cannot_grant_activation(self) -> None:
        request = base_request()
        request["policy"]["activation_allowed"] = True
        with self.assertRaisesRegex(ValueError, "cannot grant"):
            validate_request(request)

    def test_shared_performer_does_not_merge_home_and_space_speakers(self) -> None:
        request = base_request()
        request["identity_target"]["speaker"] = {"speaker_id": "home_beth", "label": "Home Beth"}
        request["identity_target"]["performer"] = {
            "performer_id": "sarah_chalke",
            "name": "Sarah Chalke",
            "living_status": "living",
            "consent_status": "not_found",
        }
        request["seed_recordings"] = [
            {
                "url": "https://www.youtube.com/watch?v=Vtbo9op9sAI",
                "title": "Beth Falls for Space Beth",
                "speakers_present": ["home_beth", "space_beth"],
                "performers_present": ["sarah_chalke"],
                "speaker_identity_verification": {"status": "mixed_character_speakers_same_credited_performer"},
                "recording_authenticity_status": "verified_broadcast_performance",
            }
        ]
        result = run_voice_discovery(request)
        item = result["recording_candidates"][0]
        self.assertEqual(item["speakers_present"], ["home_beth", "space_beth"])
        self.assertEqual(item["performers_present"], ["sarah_chalke"])
        self.assertEqual(item["identity_binding"]["speaker"]["speaker_id"], "home_beth")
        self.assertTrue(item["identity_binding"]["shared_performer_does_not_merge_speakers"])

    def test_official_clip_without_rights_or_living_performer_consent_is_blocked(self) -> None:
        request = base_request()
        request["seed_recordings"] = [
            {
                "url": "https://example.org/official-clip",
                "title": "Official Test Character Clip",
                "authority": "official_primary",
                "speaker_identity_verification": {"status": "verified_target_speaker"},
                "recording_authenticity_status": "verified_broadcast_performance",
                "rights": {"voice_model_or_training_rights": "not_established", "performer_consent_status": "not_found"},
            }
        ]
        item = run_voice_discovery(request)["recording_candidates"][0]
        blockers = " ".join(item["eligibility"]["blocked_reasons"])
        self.assertIn("rights", blockers)
        self.assertIn("living-performer consent", blockers)
        self.assertFalse(item["eligibility"]["eligible_for_voice_model_input_now"])
        self.assertFalse(item["eligibility"]["official_voice_claim_allowed"])

    def test_open_model_license_is_not_voice_identity_permission(self) -> None:
        request = base_request()
        request["seed_synthetic_models"] = [
            {
                "url": "https://huggingface.co/example/open-tts",
                "model_id": "example/open-tts",
                "license_id": "mit",
                "voice_identity_type": "unknown_review_required",
                "voice_or_dataset_rights_documented": False,
                "claims_target_performer_or_character_voice": True,
            }
        ]
        item = run_voice_discovery(request)["synthetic_model_candidates"][0]
        self.assertTrue(item["eligibility"]["eligible_for_technical_license_review"])
        self.assertFalse(item["eligibility"]["eligible_for_candidate_voice_now"])
        blockers = " ".join(item["eligibility"]["blocked_reasons"])
        self.assertIn("dataset", blockers)
        self.assertIn("living performer", blockers)

    def test_named_identity_model_query_is_treated_as_target_voice_claim(self) -> None:
        request = base_request()
        request["seed_synthetic_models"] = [
            {
                "url": "https://huggingface.co/example/test-character-voice",
                "model_id": "example/test-character-voice",
                "title": "Test Character voice",
                "discovery_query": "Test Character voice tts",
                "license_id": "mit",
                "voice_identity_type": "unknown_review_required",
                "voice_or_dataset_rights_documented": False,
            }
        ]
        item = run_voice_discovery(request)["synthetic_model_candidates"][0]
        self.assertTrue(item["claims_target_performer_or_character_voice"])
        self.assertIn("Test Character", item["matched_target_identity_labels"])
        self.assertTrue(any("living performer" in reason for reason in item["eligibility"]["blocked_reasons"]))

    def test_clean_segment_and_diarization_requirements_are_explicit(self) -> None:
        request = base_request()
        request["seed_recordings"] = [{"url": "https://example.org/mixed", "title": "Test Character and Friend", "speakers_present": ["test_speaker", "friend"]}]
        gate = run_voice_discovery(request)["recording_candidates"][0]["clean_segment_gate"]
        self.assertTrue(gate["diarization_required_if_mixed_or_unknown"])
        self.assertTrue(gate["human_target_speaker_review_required"])
        self.assertEqual(gate["approved_clean_seconds"], 0.0)
        self.assertTrue(any("20 seconds" in requirement for requirement in gate["requirements"]))
        self.assertTrue(any("not speaker identity proof" in requirement for requirement in gate["requirements"]))
        self.assertFalse(gate["diarization_is_speaker_identity_proof"])
        self.assertFalse(gate["target_only_segment_verification"]["passed"])
        self.assertEqual(
            gate["target_only_segment_verification"]["minimum_reviewed_seconds"],
            20.0,
        )

    def test_recording_review_ranking_prioritizes_reviewed_exact_source_but_never_selects_it(self) -> None:
        request = base_request()
        request["seed_recordings"] = [
            {
                "source_id": "low_fan_lead",
                "url": "https://example.org/fan",
                "title": "Test Character fan trailer",
            },
            {
                "source_id": "official_exact_lead",
                "url": "https://studio.example.org/test-character-scene",
                "title": "Test Character official scene",
                "publisher_verification": {
                    "status": "official_rightsholder_page",
                    "evidence_urls": ["https://studio.example.org/test-character"],
                },
                "continuity_binding": {
                    "status": "verified_exact_selected_continuity",
                    "selected_title": "Home variant",
                    "evidence_urls": ["https://studio.example.org/test-character"],
                },
                "performer_credit_binding": {
                    "status": "official_credit_bound_to_target_speaker_and_title",
                    "performer_id": "test_performer",
                    "evidence_urls": ["https://studio.example.org/test-character"],
                },
            },
        ]
        result = run_voice_discovery(request)
        ranked = result["ranked_recording_review_queue"]
        self.assertEqual(ranked[0]["source_id"], "official_exact_lead")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        best = result["recording_candidates"][0]
        self.assertTrue(best["identity_evidence_gate"]["passed"])
        self.assertFalse(best["review_ranking"]["auto_select_allowed"])
        self.assertFalse(best["technical_quality_gate"]["passed"])
        self.assertFalse(result["readiness_gates"]["voice_reference_ready"])
        self.assertFalse(result["selection"]["voice_assigned"])

    def test_exact_publisher_registry_enriches_search_metadata_without_granting_rights(self) -> None:
        request = base_request()
        request["source_authority_registry"] = [
            {
                "publisher": "Official Studio",
                "publisher_url": "https://www.youtube.com/@officialstudio",
                "status": "platform_verified_publisher_candidate",
                "evidence_urls": ["https://studio.example.org/social"],
            }
        ]
        request["seed_recordings"] = [
            {
                "url": "https://www.youtube.com/watch?v=official1",
                "title": "Test Character clip",
                "publisher": "Official Studio",
                "publisher_url": "https://www.youtube.com/@officialstudio",
            }
        ]
        item = run_voice_discovery(request)["recording_candidates"][0]
        gate = item["source_authority_gate"]
        self.assertEqual(gate["status"], "possible_official_source_pending_review")
        self.assertFalse(gate["voice_use_rights_proven"])
        self.assertIn(
            "source authority/provenance is not fully reviewed",
            item["eligibility"]["blocked_reasons"],
        )

    def test_exact_identity_evidence_requires_matching_performer_id(self) -> None:
        request = base_request()
        request["seed_recordings"] = [
            {
                "url": "https://example.org/wrong-performer",
                "title": "Test Character official scene",
                "continuity_binding": {
                    "status": "verified_exact_selected_continuity",
                    "selected_title": "Home variant",
                },
                "performer_credit_binding": {
                    "status": "official_credit_bound_to_target_speaker_and_title",
                    "performer_id": "different_performer",
                },
            }
        ]
        gate = run_voice_discovery(request)["recording_candidates"][0]["identity_evidence_gate"]
        self.assertTrue(gate["continuity"]["passed"])
        self.assertFalse(gate["performer_credit"]["performer_id_matches"])
        self.assertFalse(gate["performer_credit"]["passed"])
        self.assertFalse(gate["passed"])

    def test_historical_without_verified_recording_is_speculative_only(self) -> None:
        request = base_request(kind="historical_person", living="deceased")
        result = run_voice_discovery(request)
        lane = result["historical_person_lane"]
        self.assertFalse(lane["verified_recording_available"])
        self.assertEqual(lane["recording_evidence"], [])
        self.assertIn("speculative educational reconstruction", lane["design"]["required_label"])
        self.assertIn("exact biometric timbre", lane["design"]["uninferred_traits"])
        self.assertFalse(lane["authentic_voice_claim_allowed_now"])
        self.assertFalse(lane["design"]["voice_generated"])

    def test_verified_historical_recording_still_needs_clean_segment_review(self) -> None:
        request = base_request(kind="historical_person", living="deceased")
        request["seed_recordings"] = [
            {
                "source_id": "archive_primary_recording",
                "url": "https://archive.example.org/item/1",
                "title": "Verified Test Person recording",
                "speaker_identity_verification": {"status": "verified_historical_subject", "evidence_urls": ["https://archive.example.org/catalog/1"]},
                "recording_authenticity_status": "verified_original_recording",
                "rights": {"voice_model_or_training_rights": "public_domain_voice_model_use_reviewed"},
            }
        ]
        result = run_voice_discovery(request)
        lane = result["historical_person_lane"]
        self.assertEqual(lane["status"], "verified_recording_candidates_found_but_not_ingested_or_model_ready")
        self.assertFalse(result["recording_candidates"][0]["eligibility"]["eligible_for_voice_model_input_now"])

    def test_metadata_search_uses_injected_providers_and_never_claims_download(self) -> None:
        request = base_request()
        request["discovery"].update(
            {
                "recording_queries": ["test query"],
                "archive_queries": ["archive query"],
                "synthetic_model_queries": ["model query"],
            }
        )
        calls: list[str] = []

        def video(query: str, _limit: int) -> list[dict]:
            calls.append(f"video:{query}")
            return [{"url": "https://example.org/video", "title": "Test Character clip"}]

        def archive(query: str, _limit: int) -> list[dict]:
            calls.append(f"archive:{query}")
            return [{"url": "https://example.org/archive", "title": "Test Character archive"}]

        def model(query: str, _limit: int) -> list[dict]:
            calls.append(f"model:{query}")
            return [{"url": "https://example.org/model", "title": "generic model", "license_id": "mit"}]

        result = run_voice_discovery(
            request,
            metadata_search=True,
            video_search=video,
            archive_search=archive,
            model_search=model,
        )
        self.assertEqual(calls, ["video:test query", "archive:archive query", "model:model query"])
        self.assertEqual(len(result["recording_candidates"]), 2)
        self.assertEqual(len(result["synthetic_model_candidates"]), 1)
        self.assertFalse(result["operation_evidence"]["media_download_attempted"])
        self.assertFalse(result["operation_evidence"]["model_download_attempted"])
        self.assertRegex(result["request_sha256"], r"^[0-9a-f]{64}$")

    def test_non_allowlisted_public_seed_is_indexed_without_direct_fetch(self) -> None:
        request = base_request()
        request["seed_recordings"] = [{"url": "https://example.org/public-audio-page", "title": "Test Character source"}]
        calls: list[str] = []

        def direct(url: str) -> dict:
            calls.append(url)
            return {}

        result = run_voice_discovery(request, metadata_search=True, direct_video_metadata=direct)
        self.assertEqual(calls, [])
        self.assertEqual(len(result["recording_candidates"]), 1)
        self.assertEqual(result["provider_skips"][0]["provider"], "direct_video_metadata")

    def test_wrong_identity_search_result_is_rejected_as_metadata_lead(self) -> None:
        request = base_request()
        request["seed_recordings"] = [{"url": "https://example.org/wrong", "title": "Wrong Person documentary"}]
        relevance = run_voice_discovery(request)["recording_candidates"][0]["metadata_relevance"]
        self.assertEqual(relevance["status"], "rejected_wrong_or_ambiguous_identity_metadata")

    def test_candidate_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_candidate_dir("../outside")

    def test_cli_request_only_does_not_run_providers_or_generate_voice(self) -> None:
        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "discover_temporary_ai_voice.py"),
            "--candidate-id",
            "beth_smith_ordinary_temp_20260716",
            "--request-only",
        ]
        completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "request_ready_not_run")
        self.assertFalse(payload["media_downloaded"])
        self.assertFalse(payload["voice_generated"])

    def test_cli_reserved_output_is_blocked_without_overwriting_request(self) -> None:
        request_path = (
            PROJECT_ROOT
            / "TemporaryAI"
            / "candidates"
            / "beth_smith_ordinary_temp_20260716"
            / "voice_discovery_request.json"
        )
        before = request_path.read_bytes()
        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "discover_temporary_ai_voice.py"),
            "--candidate-id",
            "beth_smith_ordinary_temp_20260716",
            "--output",
            "voice_discovery_request.json",
        ]

        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("reserved candidate file", completed.stderr)
        self.assertEqual(request_path.read_bytes(), before)

    def test_creation_paths_queue_request_and_require_explicit_metadata_action(self) -> None:
        creator = (PROJECT_ROOT / "tools" / "create_temporary_ai_candidate.py").read_text(encoding="utf-8")
        control_center = (PROJECT_ROOT / "tools" / "temporary_ai_control_center.py").read_text(encoding="utf-8")
        self.assertIn('"voice_discovery_request": base / "voice_discovery_request.json"', creator)
        self.assertIn('"--discover-voice-metadata"', creator)
        self.assertIn("Find Voice Sources (Metadata Only)", control_center)
        self.assertIn('"--metadata-search"', control_center)

    def test_candidate_builder_writes_voice_request_without_network_search(self) -> None:
        tools_path = str(PROJECT_ROOT / "tools")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        import create_temporary_ai_candidate as creator

        args = argparse.Namespace(
            display_name="Offline Voice Scaffold Test",
            candidate_id="offline_voice_scaffold_test",
            ai_type="canon_reconstruction_temp_ai",
            requested_by="unit_test",
            goal="test",
            expert_domain="",
            source_path=[],
            query=[],
            notes="",
            no_avatar=True,
            include_fanfic=False,
            discover_voice_metadata=False,
        )
        original_root = creator.PROJECT_ROOT
        try:
            with tempfile.TemporaryDirectory() as temporary:
                creator.PROJECT_ROOT = Path(temporary)
                result = creator.create_candidate(args)
                request_path = Path(temporary) / result["files"]["voice_discovery_request"]
                self.assertTrue(request_path.exists())
                request = json.loads(request_path.read_text(encoding="utf-8"))
                self.assertTrue(request["discovery"]["metadata_only"])
                self.assertFalse(request["discovery"]["allow_media_download"])
                self.assertEqual(result["voice_discovery"]["status"], "request_created_metadata_search_not_run")
        finally:
            creator.PROJECT_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
