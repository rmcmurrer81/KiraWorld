from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import run_avatar_builder_subject_school_20260712 as school  # noqa: E402
from tools import run_avatar_builder_subject_school_real_model_pass_20260713 as real_pass  # noqa: E402
from tools import run_avatar_builder_school_20260712 as generic_school  # noqa: E402


class AvatarBuilderSubjectSchoolSafetyTests(unittest.TestCase):
    MARINETTE_ID = "ladybug_marinette_expanded_smoke"

    def test_marinette_cannot_be_stamped_adult_by_gwen_school(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            avatar_temp = Path(temp_dir) / "Avatar" / "temp_ai"
            adjustment_path = avatar_temp / self.MARINETTE_ID / "avatar_builder_adjustments.json"
            with patch.object(school, "AVATAR_TEMP_DIR", avatar_temp):
                with self.assertRaisesRegex(ValueError, "Gwen-specific"):
                    school.update_candidate_adjustments(
                        self.MARINETTE_ID,
                        {},
                        Path(temp_dir) / "progress.json",
                        Path(temp_dir) / "index.json",
                    )
            self.assertFalse(adjustment_path.exists())

    def test_both_gwen_runners_reject_marinette_before_work(self) -> None:
        with self.assertRaisesRegex(ValueError, "Gwen-specific"):
            school.gwen_subject_profile(self.MARINETTE_ID, [])
        with self.assertRaisesRegex(ValueError, "Gwen-specific"):
            real_pass.run_normal(Namespace(candidate_id=self.MARINETTE_ID, run_id=""))

    def test_generic_school_failure_marker_rejects_name_alias_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            avatar_temp = Path(temp_dir) / "Avatar" / "temp_ai"
            with patch.object(generic_school, "AVATAR_TEMP", avatar_temp):
                with self.assertRaisesRegex(ValueError, "exact canonical IDs"):
                    generic_school.mark_candidate_failed(
                        "minor_gwen",
                        Path(temp_dir) / "curriculum.json",
                        Path(temp_dir) / "progress.json",
                        {},
                    )
            self.assertFalse((avatar_temp / "minor_gwen").exists())

    def test_gwen_profile_persists_passed_adult_only_base_gate(self) -> None:
        profile = school.gwen_subject_profile(school.GWEN_ID, [])
        self.assertEqual(profile["age_review"]["maturity_class_override"], "adult")
        self.assertTrue(profile["required_source_asset_policy"]["adult_only"])
        self.assertFalse(profile["required_source_asset_policy"]["allowed_for_non_adult"])
        self.assertEqual(profile["body_policy_validation"]["status"], "passed")

    def test_gwen_school_rejects_required_path_when_exact_asset_identity_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            swapped_base = Path(temp_dir) / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
            swapped_base.write_bytes(b"different-model-at-reviewed-path")
            with patch.object(school, "GWEN_REQUIRED_BASE", swapped_base):
                with self.assertRaisesRegex(ValueError, "exact identity"):
                    school.validate_gwen_body_selection(school.GWEN_ID, swapped_base)

    def test_profile_fails_closed_when_central_body_policy_rejects_selection(self) -> None:
        with patch.object(
            school,
            "validate_avatar_body_policy",
            return_value={"status": "failed", "failures": ["test_policy_rejection"]},
        ):
            with self.assertRaisesRegex(ValueError, "test_policy_rejection"):
                school.gwen_subject_profile(school.GWEN_ID, [])

    def test_failed_visual_gate_and_jsonl_remain_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_id = real_pass.GWEN_ID
            run_id = "avatar_builder_subject_school_gwen_test"
            subject_runs = root / "subject_runs"
            assignments = root / "assignments"
            avatar_temp = root / "avatar_temp"
            base = root / "adult_base.glb"
            model = root / "generated_model.glb"
            base.write_bytes(b"adult-base")
            model.write_bytes(b"generated-model")

            run_root = subject_runs / run_id
            artifact_root = run_root / "real_model_artifacts"
            artifact_root.mkdir(parents=True)
            (run_root / "subject_profile.json").write_text(
                json.dumps({"candidate_id": candidate_id}), encoding="utf-8"
            )
            (artifact_root / "artifact_manifest.json").write_text(
                json.dumps(
                    {
                        "candidate_id": candidate_id,
                        "model": "generated_model.glb",
                        "source_base": "adult_base.glb",
                        "views": {},
                        "visual_quality_gate_data": {"status": "failed", "grade": "F"},
                    }
                ),
                encoding="utf-8",
            )

            expected_jsonl = root / "proof" / "movement_learning_attempts.jsonl"
            stage_dir = assignments / run_id / "001_motion"
            stage_dir.mkdir(parents=True)
            (stage_dir / "assignment.json").write_text(
                json.dumps(
                    {
                        "expected_artifacts": [
                            {"expected_path": "proof/movement_learning_attempts.jsonl"}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(real_pass, "ROOT", root),
                patch.object(real_pass, "SUBJECT_RUN_ROOT", subject_runs),
                patch.object(real_pass, "ASSIGNMENT_ROOT", assignments),
                patch.object(real_pass, "AVATAR_TEMP", avatar_temp),
                patch.object(real_pass, "BASE_FEMALE", base),
                patch.object(
                    real_pass,
                    "validate_gwen_body_selection",
                    return_value={
                        "validation": {"status": "passed"},
                        "selected_base": {"id": "test-adult-base"},
                    },
                ),
            ):
                result = real_pass.finalize_assignments(run_id)

            assignment = json.loads((stage_dir / "assignment.json").read_text(encoding="utf-8"))
            manifest = json.loads((artifact_root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(result["ok"])
            self.assertEqual(result["missing_count"], 1)
            self.assertFalse(expected_jsonl.exists())
            self.assertEqual(
                assignment["expected_artifacts"][0]["status"],
                "missing_unsupported_expected_artifact_type_jsonl",
            )
            self.assertEqual(assignment["grade"]["current_grade"], "failed_visual_quality_gate")
            self.assertEqual(
                manifest["status"],
                "real_model_artifacts_failed_visual_quality_gate_with_missing_expected_files",
            )

    def test_failed_visual_gate_returns_failure_even_when_no_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_id = real_pass.GWEN_ID
            run_id = "avatar_builder_subject_school_gwen_quality_failure"
            subject_runs = root / "subject_runs"
            assignments = root / "assignments"
            avatar_temp = root / "avatar_temp"
            base = root / "adult_base.glb"
            model = root / "generated_model.glb"
            base.write_bytes(b"adult-base")
            model.write_bytes(b"generated-model")

            run_root = subject_runs / run_id
            artifact_root = run_root / "real_model_artifacts"
            artifact_root.mkdir(parents=True)
            (run_root / "subject_profile.json").write_text(
                json.dumps({"candidate_id": candidate_id}), encoding="utf-8"
            )
            (artifact_root / "artifact_manifest.json").write_text(
                json.dumps(
                    {
                        "candidate_id": candidate_id,
                        "model": "generated_model.glb",
                        "source_base": "adult_base.glb",
                        "views": {},
                        "visual_quality_gate_data": {"status": "failed", "grade": "F"},
                    }
                ),
                encoding="utf-8",
            )
            stage_dir = assignments / run_id / "001_quality"
            stage_dir.mkdir(parents=True)
            (stage_dir / "assignment.json").write_text(
                json.dumps({"expected_artifacts": []}), encoding="utf-8"
            )

            with (
                patch.object(real_pass, "ROOT", root),
                patch.object(real_pass, "SUBJECT_RUN_ROOT", subject_runs),
                patch.object(real_pass, "ASSIGNMENT_ROOT", assignments),
                patch.object(real_pass, "AVATAR_TEMP", avatar_temp),
                patch.object(real_pass, "BASE_FEMALE", base),
                patch.object(
                    real_pass,
                    "validate_gwen_body_selection",
                    return_value={
                        "validation": {"status": "passed"},
                        "selected_base": {"id": "test-adult-base"},
                    },
                ),
            ):
                result = real_pass.finalize_assignments(run_id)

            assignment = json.loads((stage_dir / "assignment.json").read_text(encoding="utf-8"))
            manifest = json.loads((artifact_root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["missing_count"], 0)
            self.assertFalse(result["ok"])
            self.assertEqual(assignment["grade"]["current_grade"], "failed_visual_quality_gate")
            self.assertEqual(
                manifest["status"], "real_model_artifacts_generated_failed_visual_quality_gate"
            )


if __name__ == "__main__":
    unittest.main()
