from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from Core.avatar_builder_qwen35_visual_intake import (
    AvatarVisualIntakeError,
    QWEN_VISUAL_DIGEST,
    QWEN_VISUAL_MODEL,
    prepare_avatar_visual_intake,
    record_exact_person_owner_correction,
    validate_visual_observation_output,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AvatarBuilderQwen35VisualIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.source_root = self.root / "Avatar" / "private_refs"
        self.source_root.mkdir(parents=True)
        self.image = self.source_root / "front.png"
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"private synthetic test frame")

    def tearDown(self) -> None:
        self._temp.cleanup()

    def preflight(self, lane: str = "adult", *, passed: bool = True):
        return {
            "status": "passed" if passed else "blocked",
            "authoring_allowed": passed,
            "registry_binding_verified": True,
            "canonical_candidate_id": "example_person",
            "canonical_profile": {
                "path": "TemporaryAI/candidates/example_person/temporary_ai_profile.json",
                "sha256": "b" * 64,
            },
            "identity": {
                "subject_id": "example_subject",
                "identity_class": "fictional_character",
                "selected_version": "series_finale_adult_era",
                "version_required": True,
            },
            "maturity": {"lane": lane},
            "failures": [] if passed else ["maturity_unresolved_authoring_blocked"],
        }

    def evaluator(self, preflight):
        def evaluate(root: Path, candidate_id: str, subject_id: str):
            self.assertEqual(root, self.root.resolve())
            self.assertEqual(candidate_id, "example_person")
            self.assertEqual(subject_id, "example_subject")
            return preflight

        return evaluate

    def provenance(self):
        return {
            "source_kind": "owner_supplied_fictional_reference",
            "rights_basis": "Owner authorized project-private reconstruction study.",
            "title_or_version": "Series finale adult-era design",
            "origin_record": "owner intake record visual_ref_001",
            "owner_authorized_private_use": True,
            "public_export_allowed": False,
        }

    def image_source(self):
        return {
            "opaque_media_id": "visual_ref_001",
            "media_kind": "image",
            "project_relative_path": "Avatar/private_refs/front.png",
            "sha256": sha256(self.image),
            "subject_binding_id": "subject_binding_001",
            "private_reconstruction_only": True,
            "provenance": self.provenance(),
        }

    def request(self):
        return {
            "candidate_id": "example_person",
            "subject_id": "example_subject",
            "model": QWEN_VISUAL_MODEL,
            "model_digest": QWEN_VISUAL_DIGEST,
            "authorized_source_roots": ["Avatar/private_refs"],
            "subject_binding": {
                "binding_id": "subject_binding_001",
                "candidate_id": "example_person",
                "subject_id": "example_subject",
                "subject_kind": "fictional",
                "selected_by_robert": True,
                "selection_text_sha256": "a" * 64,
                "selected_timepoint": "after the series finale time jump",
                "selected_version_or_era": "series_finale_adult_era",
                "face_identity_claim_allowed": False,
            },
            "source_items": [self.image_source()],
        }

    def prepare(self, *, lane: str = "adult", passed: bool = True, request=None):
        return prepare_avatar_visual_intake(
            self.root,
            request or self.request(),
            _profile_evaluator=self.evaluator(self.preflight(lane, passed=passed)),
        )

    def valid_output(self):
        return {
            "schema_version": 1,
            "coverage": "BOUND_STILLS_AND_EXACT_VIDEO_SAMPLE_FRAMES_ONLY",
            "identity_status": "USER_SELECTED_SUBJECT_BINDING_ONLY_NOT_MODEL_IDENTIFIED",
            "maturity_inference": False,
            "subject_binding_id": "subject_binding_001",
            "observations": [
                {
                    "observation_id": "obs_001",
                    "category": "eyebrow",
                    "description": "The visible brow has a softly angled outer third.",
                    "confidence": "medium",
                    "uncertainty": "Lighting obscures some individual hairs.",
                    "source_bindings": [
                        {"opaque_media_id": "visual_ref_001", "sha256": sha256(self.image)}
                    ],
                }
            ],
            "contradictions": [],
            "suggestions": {
                "morph": [
                    {
                        "suggestion_id": "morph_001",
                        "description": "Consider a gentle outer brow arch in a later owner-reviewed draft.",
                        "based_on_observation_ids": ["obs_001"],
                        "confidence": "medium",
                        "uncertainty": "A second frontal reference would improve confidence.",
                    }
                ],
                "material": [],
                "hair": [],
            },
            "global_uncertainties": ["Only one frontal still is available."],
            "mutation_requested": False,
        }

    def test_prepares_inert_exact_qwen_plan_without_authoring(self) -> None:
        plan = self.prepare()
        self.assertEqual(plan["model_identity"]["model"], "qwen3.5:9b")
        self.assertEqual(plan["model_identity"]["digest"], QWEN_VISUAL_DIGEST)
        self.assertEqual(plan["profile_authority"]["template_lane"], "confirmed_adult_template")
        self.assertFalse(plan["decision_authority"]["model_may_infer_maturity_from_appearance"])
        self.assertEqual(plan["execution"]["status"], "STATIC_INERT_PREPARATION_ONLY")
        self.assertFalse(plan["execution"]["ollama_called"])
        self.assertFalse(plan["execution"]["blender_called"])
        self.assertFalse(plan["output_scope"]["direct_body_mutation_allowed"])
        self.assertEqual(len(plan["plan_sha256"]), 64)

    def test_non_adult_and_uncertain_profiles_are_doll_safe(self) -> None:
        non_adult = self.prepare(lane="non_adult_doll_safe")
        self.assertEqual(
            non_adult["profile_authority"]["template_lane"],
            "non_adult_doll_safe_template",
        )
        self.assertFalse(
            non_adult["profile_authority"]["adult_template_lane_selected"]
        )
        self.assertFalse(
            non_adult["profile_authority"]["adult_anatomy_authoring_authorized"]
        )
        uncertain = self.prepare(lane="unresolved_doll_safe", passed=False)
        self.assertEqual(
            uncertain["profile_authority"]["template_lane"],
            "non_adult_doll_safe_template",
        )
        self.assertFalse(
            uncertain["profile_authority"]["authoring_allowed_by_profile_preflight"]
        )

    def test_model_digest_is_exact_and_has_no_fallback(self) -> None:
        request = self.request()
        request["model_digest"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "approved qwen3.5:9b digest"):
            self.prepare(request=request)
        request = self.request()
        request["model"] = "llama3.1:8b"
        with self.assertRaisesRegex(RuntimeError, "exact qwen3.5:9b"):
            self.prepare(request=request)

    def test_source_must_be_allowlisted_private_and_exactly_hashed(self) -> None:
        request = self.request()
        request["source_items"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(AvatarVisualIntakeError, "SHA-256 mismatch"):
            self.prepare(request=request)
        outside = self.root / "Avatar" / "outside.png"
        outside.write_bytes(self.image.read_bytes())
        request = self.request()
        request["source_items"][0]["project_relative_path"] = "Avatar/outside.png"
        request["source_items"][0]["sha256"] = sha256(outside)
        with self.assertRaisesRegex(AvatarVisualIntakeError, "outside authorized_source_roots"):
            self.prepare(request=request)
        request = self.request()
        request["source_items"][0]["private_reconstruction_only"] = False
        with self.assertRaisesRegex(AvatarVisualIntakeError, "must remain private"):
            self.prepare(request=request)

    def test_fictional_timepoint_must_match_canonical_version(self) -> None:
        request = self.request()
        request["subject_binding"]["selected_version_or_era"] = "high_school_era"
        with self.assertRaisesRegex(AvatarVisualIntakeError, "conflicts with canonical profile"):
            self.prepare(request=request)

    def test_video_is_exact_sampled_frame_not_full_viewing(self) -> None:
        video = self.source_root / "clip.mp4"
        video.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"bounded video fixture")
        request = self.request()
        frame = self.image_source()
        frame.update(
            {
                "media_kind": "video_sample_frame",
                "parent_video": {
                    "opaque_media_id": "video_001",
                    "project_relative_path": "Avatar/private_refs/clip.mp4",
                    "sha256": sha256(video),
                },
                "sample_timestamp_seconds": 12.5,
                "sample_index": 3,
                "sample_method": "preextracted_exact_frame",
                "full_video_viewing_claim_allowed": False,
            }
        )
        request["source_items"] = [frame]
        plan = self.prepare(request=request)
        self.assertEqual(plan["source_items"][0]["sample_timestamp_seconds"], 12.5)
        self.assertFalse(plan["source_items"][0]["full_video_viewing_claim_allowed"])
        self.assertFalse(plan["coverage_contract"]["full_video_viewing_claim_allowed"])
        request["source_items"][0]["full_video_viewing_claim_allowed"] = True
        with self.assertRaisesRegex(AvatarVisualIntakeError, "full-video claim"):
            self.prepare(request=request)

    def test_output_is_source_bound_suggestions_only(self) -> None:
        plan = self.prepare()
        result = validate_visual_observation_output(self.valid_output(), plan)
        self.assertEqual(result["authoritative_template_lane"], "confirmed_adult_template")
        self.assertFalse(result["model_selected_template_lane"])
        self.assertFalse(result["runtime_activation_allowed"])
        self.assertEqual(
            result["observations"][0]["source_bindings"][0]["sha256"],
            sha256(self.image),
        )

    def test_output_rejects_identity_maturity_unbound_sources_and_mutation(self) -> None:
        plan = self.prepare()
        output = self.valid_output()
        output["observations"][0]["description"] = "The person is identified as Robert."
        with self.assertRaisesRegex(AvatarVisualIntakeError, "face identity claim"):
            validate_visual_observation_output(output, plan)
        output = self.valid_output()
        output["maturity_inference"] = True
        with self.assertRaisesRegex(AvatarVisualIntakeError, "maturity inference"):
            validate_visual_observation_output(output, plan)
        output = self.valid_output()
        output["observations"][0]["description"] = "This appears to be an adult woman."
        with self.assertRaisesRegex(AvatarVisualIntakeError, "maturity inference"):
            validate_visual_observation_output(output, plan)
        output = self.valid_output()
        output["observations"][0]["source_bindings"][0]["opaque_media_id"] = "unknown_ref"
        with self.assertRaisesRegex(AvatarVisualIntakeError, "unknown source"):
            validate_visual_observation_output(output, plan)
        output = self.valid_output()
        output["suggestions"]["morph"][0]["description"] = "Modify the mesh and activate it now."
        with self.assertRaisesRegex(AvatarVisualIntakeError, "prohibited direct action"):
            validate_visual_observation_output(output, plan)

    def test_output_rejects_a_tampered_intake_plan(self) -> None:
        plan = self.prepare()
        plan["profile_authority"]["template_lane"] = "confirmed_adult_template"
        plan["subject_binding"]["selected_timepoint"] = "silently changed"
        with self.assertRaisesRegex(AvatarVisualIntakeError, "integrity check failed"):
            validate_visual_observation_output(self.valid_output(), plan)

    def test_robert_corrections_are_exact_person_append_only(self) -> None:
        memory = {}
        first = record_exact_person_owner_correction(
            memory,
            candidate_id="example_person",
            message="Use the character from the end of the series, not the high-school era.",
            recorded_at="2026-08-09T12:00:00Z",
        )
        second = record_exact_person_owner_correction(
            memory,
            candidate_id="example_person",
            message="No, this version is an adult; use an adult body.",
            recorded_at="2026-08-09T12:01:00Z",
            requested_maturity_class="adult",
            previous_maturity_class="non_adult_doll_safe",
        )
        self.assertEqual(first["event"]["sequence"], 1)
        self.assertEqual(second["event"]["sequence"], 2)
        self.assertEqual(second["verification"]["status"], "passed")
        self.assertEqual(
            memory["correction_memory_events"][1]["previous_event_sha256"],
            memory["correction_memory_events"][0]["event_sha256"],
        )
        request = self.request()
        request["correction_memory"] = memory
        plan = self.prepare(request=request)
        self.assertEqual(plan["correction_memory"]["chain_status"], "passed")
        self.assertEqual(
            plan["correction_memory"]["latest_exact_person_event_id"],
            second["event"]["event_id"],
        )

    def test_pending_adult_correction_cannot_be_inferred_from_media(self) -> None:
        memory = {}
        record_exact_person_owner_correction(
            memory,
            candidate_id="example_person",
            message="No, this version is an adult; use an adult body.",
            recorded_at="2026-08-09T12:01:00Z",
            requested_maturity_class="adult",
            previous_maturity_class="non_adult_doll_safe",
        )
        request = self.request()
        request["correction_memory"] = memory
        with self.assertRaisesRegex(AvatarVisualIntakeError, "canonical profile"):
            self.prepare(lane="non_adult_doll_safe", request=request)

    def test_harness_is_static_and_has_no_model_or_blender_execution_imports(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "tools" / "prepare_avatar_qwen35_visual_intake.py").read_text(encoding="utf-8")
        folded = source.casefold()
        self.assertNotIn("import requests", folded)
        self.assertNotIn("import ollama", folded)
        self.assertNotIn("import bpy", folded)
        self.assertNotIn("subprocess", folded)
        self.assertIn("static qwen 3.5 avatar builder visual intake", folded)


if __name__ == "__main__":
    unittest.main()
