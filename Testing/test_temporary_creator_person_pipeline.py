from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Core import temporary_ai_creator_quality_v3 as quality_v3
from Core import temporary_ai_creator_quality_v4 as quality_v4
from Core.temporary_creator_person_pipeline import (
    ALLOWED_CREATOR_TYPES,
    TemporaryCreatorPipelineError,
    VOICE_SOURCE_REVIEW_KIND,
    canonical_sha256,
    file_sha256,
    orchestrate_temporary_creator,
)
from Testing.test_temporary_ai_creator_quality_v3 import (
    build_authority,
    build_evaluation_authority,
)
from Testing.test_temporary_ai_creator_quality_v4 import (
    NOW,
    base_envelope,
    evaluation_envelope,
    write_envelope,
)


UTC = "2026-08-26T20:00:00Z"


def authenticated_command(text: str) -> dict:
    return {
        "person_id": "real_robert",
        "authority_class": "founder",
        "authenticated": True,
        "authorized": True,
        "command_text": text,
    }


def creator_data(
    creator_type: str,
    subject: str,
    *,
    person_id: str = "",
    display_name: str = "",
    role_title: str = "",
    version: str = "",
    personality: str = "",
) -> dict:
    value = {
        "creator_type": creator_type,
        "subject_or_domain": subject,
        "requested_by": authenticated_command(f"make {subject}"),
    }
    for key, item in (
        ("person_id", person_id),
        ("display_name", display_name),
        ("role_title", role_title),
        ("version_or_timepoint", version),
        ("personality_notes", personality),
    ):
        if item:
            value[key] = item
    return value


def read_json(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text("utf-8"))


def build_real_v4_expert_evidence(root: Path) -> dict:
    authority_root = root / "authority"
    root_sha, request_id = build_authority(authority_root, expert=True)
    create_envelope = base_envelope(
        root,
        root_sha=root_sha,
        request_id=request_id,
        expert=True,
        authorization_id="authorization_pipeline_quantum_create_v4",
        nonce_seed="pipeline-quantum-create",
    )
    create_relative, create_sha = write_envelope(root, create_envelope)
    creation = quality_v4.consume_signed_envelope_v4(
        root,
        envelope_relative=create_relative,
        expected_envelope_sha256=create_sha,
        trusted_now_utc=NOW,
    )

    authority = quality_v3.open_parent_authority(
        authority_root,
        expected_root_sha256=root_sha,
        trusted_now_utc=NOW,
    )
    prepared = quality_v3.prepare_quality_v3(authority, request_id)
    evaluation_root = root / "evaluation_authority"
    evaluation_root.mkdir()
    evaluation_root_sha, evaluation_id = build_evaluation_authority(
        evaluation_root, prepared
    )
    eval_envelope = evaluation_envelope(
        root,
        root_sha=root_sha,
        evaluation_root_sha=evaluation_root_sha,
        request_id=request_id,
        evaluation_id=evaluation_id,
        creation_result=creation,
        authorization_id="authorization_pipeline_quantum_evaluation_v4",
    )
    eval_relative, eval_sha = write_envelope(root, eval_envelope)
    evaluation = quality_v4.consume_signed_envelope_v4(
        root,
        envelope_relative=eval_relative,
        expected_envelope_sha256=eval_sha,
        trusted_now_utc=NOW,
    )
    return {
        "creation": {
            "envelope_relative": create_relative,
            "envelope_sha256": create_sha,
            "outcome_relative": creation["outcome_receipt"],
            "outcome_sha256": file_sha256(root / creation["outcome_receipt"]),
            "quality_record_relative": creation["outputs"]["quality_record"],
            "quality_record_sha256": creation["outputs"]["quality_record_sha256"],
        },
        "evaluation": {
            "envelope_relative": eval_relative,
            "envelope_sha256": eval_sha,
            "outcome_relative": evaluation["outcome_receipt"],
            "outcome_sha256": file_sha256(root / evaluation["outcome_receipt"]),
            "evaluation_result_relative": evaluation["outputs"]["evaluation_result"],
            "evaluation_result_sha256": evaluation["outputs"][
                "evaluation_result_sha256"
            ],
        },
    }


class TemporaryCreatorPersonPipelineTests(unittest.TestCase):
    def test_expert_voice_profile_follows_gender_and_uses_neutral_default(self) -> None:
        cases = (
            ("Female", "stable_calm_female_v1", "feminine"),
            ("Male", "stable_warm_male_v1", "masculine"),
            ("Doesn't matter", "stable_neutral_narrator_v1", "neutral"),
        )
        for gender, profile_id, presentation in cases:
            with self.subTest(gender=gender), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                data = creator_data("expert", "astronomy", person_id="astronomy_expert")
                data["gender_preference"] = gender
                result = orchestrate_temporary_creator(
                    root,
                    Path("TemporaryAI/creator_work_orders/astronomy_expert"),
                    data,
                    created_at_utc=UTC,
                )
                voice = read_json(
                    root, result["workspace_relative"] + "/voice_generator_work_order.json"
                )
                avatar = read_json(
                    root, result["workspace_relative"] + "/avatar_builder_work_order.json"
                )
                selected = voice["selected_generation_lane"][
                    "recommended_stable_voice_profile"
                ]
                self.assertEqual(selected["profile_id"], profile_id)
                self.assertEqual(selected["voice_presentation"], presentation)
                self.assertEqual(
                    selected["current_truth"],
                    "static_style_recommendation_only_unsynthesized",
                )
                self.assertEqual(avatar["recommended_stable_voice_profile"], selected)
                self.assertEqual(
                    avatar["body_voice_codesign_id"],
                    voice["selected_generation_lane"]["body_voice_codesign_id"],
                )
                self.assertFalse(voice["audio_generated"])

    def test_exactly_three_creator_choices_and_invalid_choice_stays_draft(self) -> None:
        self.assertEqual(
            ALLOWED_CREATOR_TYPES, frozenset({"expert", "fictional", "historical"})
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = orchestrate_temporary_creator(
                root,
                Path("TemporaryAI/creator_work_orders/invalid"),
                creator_data("generated_original", "Mira"),
                created_at_utc=UTC,
            )
            self.assertEqual(result["overall_status"], "draft")
            self.assertFalse(result["written_files"])
            self.assertFalse(
                (root / "TemporaryAI/creator_work_orders/invalid").exists()
            )

    def test_workspace_parent_selects_shared_id_child_and_mismatch_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = creator_data("expert", "botany", person_id="botany")
            result = orchestrate_temporary_creator(
                root,
                Path("TemporaryAI/creator_work_orders"),
                data,
                created_at_utc=UTC,
            )
            self.assertEqual(
                result["workspace_relative"],
                "TemporaryAI/creator_work_orders/botany",
            )
            with self.assertRaisesRegex(
                TemporaryCreatorPipelineError,
                "workspace_outside_creator_work_order_root",
            ):
                orchestrate_temporary_creator(
                    root,
                    Path("TemporaryAI/creator_work_orders/someone_else"),
                    data,
                    created_at_utc=UTC,
                )

    def test_expert_command_creates_deterministic_parallel_codesign_orders(self) -> None:
        with tempfile.TemporaryDirectory(prefix=quality_v4.TEST_ROOT_PREFIX) as temporary:
            root = Path(temporary)
            evidence = build_real_v4_expert_evidence(root)
            data = creator_data(
                "expert",
                "fault-tolerant quantum error correction",
                person_id="quantum_expert",
                display_name="Quantum Error Correction Expert",
                role_title="quantum error correction expert",
                personality="Patient, precise, and candid about uncertainty.",
            )
            workspace = Path("TemporaryAI/creator_work_orders/quantum_expert")
            first = orchestrate_temporary_creator(
                root,
                workspace,
                data,
                created_at_utc=UTC,
                v4_evidence=evidence,
            )
            second = orchestrate_temporary_creator(
                root,
                workspace,
                data,
                created_at_utc=UTC,
                v4_evidence=evidence,
            )
            self.assertEqual(first, second)
            self.assertEqual(first["person_id"], "quantum_expert")
            self.assertEqual(first["stages"]["v4_static_gate"]["status"], "ready")
            self.assertEqual(first["stages"]["mind_knowledge"]["status"], "queued")
            self.assertEqual(first["stages"]["avatar_builder"]["status"], "queued")
            self.assertEqual(first["stages"]["voice_generator"]["status"], "queued")
            self.assertEqual(
                first["stages"]["kira_world_residency"]["status"], "blocked"
            )

            avatar = read_json(root, workspace.as_posix() + "/avatar_builder_work_order.json")
            voice = read_json(root, workspace.as_posix() + "/voice_generator_work_order.json")
            mind = read_json(root, workspace.as_posix() + "/mind_knowledge_work_order.json")
            residency = read_json(
                root, workspace.as_posix() + "/kira_world_residency_work_order.json"
            )
            ids = {row["person_id"] for row in (avatar, voice, mind, residency)}
            self.assertEqual(ids, {"quantum_expert"})
            self.assertEqual(
                avatar["body_voice_codesign_id"],
                voice["selected_generation_lane"]["body_voice_codesign_id"],
            )
            self.assertEqual(avatar["execution_status"], "queued")
            self.assertEqual(voice["execution_status"], "queued")
            self.assertFalse(avatar["avatar_or_body_created"])
            self.assertFalse(voice["audio_generated"])
            self.assertFalse(residency["person_present_in_kira_world"])
            self.assertFalse(
                residency["promotion_policy"]["creation_can_promote"]
            )

            readiness = read_json(
                root, workspace.as_posix() + "/shared_person_readiness.json"
            )
            manifest = read_json(
                root, workspace.as_posix() + "/person_manifest.json"
            )
            self.assertEqual(
                manifest["subject_or_domain"],
                "fault-tolerant quantum error correction",
            )
            self.assertEqual(readiness["v4_evidence"], evidence)
            self.assertEqual(readiness["status"], "blocked")
            self.assertFalse(readiness["ready_for_existing_surface_registration"])
            self.assertFalse(
                readiness["existing_surfaces"]["kira_text_voice_chat"]["discoverable"]
            )
            self.assertFalse(
                readiness["existing_surfaces"]["kira_world_shell"]["discoverable"]
            )

    def test_fictional_acceptance_queues_identity_matched_video_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = creator_data(
                "fictional",
                "Avery Vale",
                version="The Lantern Archive, volume one endpoint",
                personality="Curious, brave, and playful.",
            )
            workspace = Path("TemporaryAI/creator_work_orders")
            result = orchestrate_temporary_creator(
                root, workspace, data, created_at_utc=UTC
            )
            workspace = Path(result["workspace_relative"])
            voice = read_json(
                root, workspace.as_posix() + "/voice_generator_work_order.json"
            )
            avatar = read_json(
                root, workspace.as_posix() + "/avatar_builder_work_order.json"
            )
            self.assertEqual(result["overall_status"], "queued")
            self.assertTrue(voice["online_recording_discovery_first"])
            queries = " ".join(
                voice["discovery_request"]["discovery"]["recording_queries"]
            )
            self.assertIn("Avery Vale", queries)
            self.assertIn("The Lantern Archive", queries)
            self.assertIn(
                "voice_source_identity_rights_review_not_present",
                voice["execution_blockers"],
            )
            self.assertFalse(voice["audio_generated"])
            self.assertFalse(avatar["avatar_or_body_created"])
            self.assertTrue(
                avatar["autonomous_visual_reference_plan"][
                    "identity_ambiguity_must_fail_closed"
                ]
            )

    def test_historical_minimal_command_autonomously_plans_life_point(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = creator_data("historical", "JFK")
            workspace = Path("TemporaryAI/creator_work_orders")
            result = orchestrate_temporary_creator(
                root, workspace, data, created_at_utc=UTC
            )
            workspace = Path(result["workspace_relative"])
            manifest = read_json(root, workspace.as_posix() + "/person_manifest.json")
            request = read_json(
                root, workspace.as_posix() + "/temporary_person_request.json"
            )
            voice = read_json(
                root, workspace.as_posix() + "/voice_generator_work_order.json"
            )
            self.assertEqual(result["overall_status"], "queued")
            self.assertEqual(manifest["display_name"], "JFK")
            identity = manifest["identity_resolution"]
            self.assertEqual(identity["status"], "queued")
            self.assertEqual(identity["confidence"], "provisional_low")
            self.assertIn("rank_primary_historical", identity["resolution_strategy"])
            self.assertFalse(request["clarifications_needed"])
            self.assertFalse(request["per_source_owner_approval_required"])
            self.assertTrue(voice["online_recording_discovery_first"])
            self.assertTrue(
                voice["discovery_request"]["discovery"]["recording_queries"]
            )
            self.assertFalse(result["truth"]["activation_performed"])

    def test_reviewed_no_recording_emits_non_authentic_reconstruction_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = creator_data(
                "historical",
                "Amelia North",
                person_id="amelia_north",
                version="1912, immediately after the documented expedition",
            )
            workspace = Path("TemporaryAI/creator_work_orders/amelia_north")
            first = orchestrate_temporary_creator(
                root, workspace, data, created_at_utc=UTC
            )
            voice = read_json(
                root, workspace.as_posix() + "/voice_generator_work_order.json"
            )
            review = {
                "schema_version": 1,
                "record_kind": VOICE_SOURCE_REVIEW_KIND,
                "person_id": "amelia_north",
                "discovery_request_sha256": voice["discovery_request_sha256"],
                "outcome": "no_usable_recording",
                "evaluated_by": "offline_evidence_ranker_v1",
                "evaluated_at_utc": UTC,
                "source_review_complete": True,
                "identity_review_complete": True,
                "rights_review_complete": True,
                "voice_model_use_authorized": False,
                "selected_recording_identity_bound": False,
                "selected_recording_sha256": "",
                "search_evidence_sha256": "7" * 64,
                "reviewed_source_count": 4,
                "no_usable_reason": "No identity-bound recording with usable rights survived review.",
                "reconstruction_factors": {
                    "age_or_life_stage": "adult in the selected 1912 life point",
                    "origin_or_region": "documented North Atlantic coastal region",
                    "primary_language": "English",
                    "era_or_timepoint": "1912",
                    "physiology_notes": "No documented vocal impairment; uncertainty retained.",
                    "personality_notes": "Measured, curious, and expedition-focused.",
                },
                "activation_allowed": False,
            }
            evidence_path = root / "evidence/amelia_no_recording.json"
            evidence_path.parent.mkdir(parents=True)
            evidence_path.write_text(
                json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            second = orchestrate_temporary_creator(
                root,
                workspace,
                data,
                created_at_utc=UTC,
                voice_source_evidence={
                    "record_relative": "evidence/amelia_no_recording.json",
                    "record_sha256": file_sha256(evidence_path),
                },
            )
            self.assertEqual(first["person_id"], second["person_id"])
            updated = read_json(
                root, workspace.as_posix() + "/voice_generator_work_order.json"
            )
            fallback = updated["reconstructed_voice_fallback"]
            self.assertEqual(
                fallback["authenticity_label"], "NON_AUTHENTIC_RECONSTRUCTED_VOICE"
            )
            self.assertTrue(fallback["must_not_be_called_authentic_official_or_exact"])
            self.assertEqual(fallback["status"], "blocked")
            self.assertIn(
                "signed_v4_static_evidence_not_ready", fallback["blockers"]
            )
            self.assertIsNone(updated["selected_generation_lane"])
            self.assertFalse(fallback["voice_generated"])

    def test_caller_cannot_promote_or_claim_surface_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = creator_data("expert", "botany", person_id="botany")
            data.update(
                {
                    "founder_approval_present": True,
                    "ram_capacity_verified": True,
                    "residency_capacity_verified": True,
                }
            )
            data["permanent_promotion_requested"] = bool(1)
            workspace = Path("TemporaryAI/creator_work_orders/botany")
            result = orchestrate_temporary_creator(
                root, workspace, data, created_at_utc=UTC
            )
            self.assertFalse(result["activation_allowed"])
            self.assertFalse(result["permanent_promotion_allowed"])
            promotion = result["promotion_policy"]["permanent_promotion"]
            self.assertEqual(promotion["status"], "blocked")
            self.assertFalse(promotion["founder_approval_present"])
            self.assertFalse(promotion["ram_capacity_verified"])
            self.assertFalse(promotion["residency_capacity_verified"])


if __name__ == "__main__":
    unittest.main()
