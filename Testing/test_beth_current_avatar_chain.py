from __future__ import annotations

import json
from pathlib import Path
import unittest

from Core.avatar_clothed_visual_diagnostic import evaluate_clothed_visual_diagnostic
from Core.avatar_component_production import (
    plan_orchestration_request,
    process_job,
    sha256_file,
)
from Core.avatar_profile_preflight import evaluate_orchestration_identity_preflight


class BethCurrentAvatarChainTests(unittest.TestCase):
    CANDIDATE_ID = "beth_smith_ordinary_temp_20260716"
    CURRENT_JOB_ID = "acb1b1d3f6980ee3ba5e690705b6c9e735c574f1235451a42b9327d4cd3cfc90"

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.orchestration_path = (
            cls.root
            / "Avatar"
            / "avatar_builder"
            / "orchestration_requests"
            / f"{cls.CANDIDATE_ID}.json"
        )
        cls.production_request_path = (
            cls.root
            / "Avatar"
            / "avatar_builder"
            / "component_production_requests"
            / f"{cls.CANDIDATE_ID}.json"
        )
        cls.plan_path = (
            cls.root
            / "Avatar"
            / "avatar_builder"
            / "component_production"
            / "plans"
            / f"{cls.CANDIDATE_ID}.json"
        )

    def read(self, path: Path) -> dict:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertIsInstance(value, dict)
        return value

    def test_live_components_status_request_and_orchestration_are_exactly_aligned(self) -> None:
        orchestration = self.read(self.orchestration_path)
        request = self.read(self.production_request_path)
        authority_path = self.root / request["component_authority"]["path"]
        authority = self.read(authority_path)
        self.assertEqual(
            request["component_authority"]["sha256"], sha256_file(authority_path)
        )
        self.assertEqual(
            request["orchestration_binding"]["sha256"],
            sha256_file(self.orchestration_path),
        )
        for role in ("body", "hair", "eyes", "clothes"):
            source = request["source_components"][role]
            digest = sha256_file(self.root / source["path"])
            self.assertEqual(source["sha256"], digest)
            self.assertEqual(authority[f"{role}_sha256"], digest)
            self.assertEqual(
                orchestration["components"][role]["artifact_sha256"], digest
            )
        self.assertFalse(authority["runtime_activation_allowed"])
        self.assertFalse(orchestration["runtime_activation_requested"])
        self.assertFalse(request["runtime_activation_requested"])
        self.assertFalse(request["public_export_requested"])

    def test_r6_visual_failure_evidence_is_durable_and_current(self) -> None:
        orchestration = self.read(self.orchestration_path)
        stable = orchestration["readiness_evidence"]["stable_rig"]
        diagnostic = stable["diagnostic_artifact"]
        review = stable["assistant_visual_failure_review"]
        diagnostic_path = self.root / diagnostic["path"]
        review_path = self.root / review["path"]
        self.assertEqual(diagnostic["sha256"], sha256_file(diagnostic_path))
        self.assertEqual(review["sha256"], sha256_file(review_path))
        result = evaluate_clothed_visual_diagnostic(
            self.root,
            diagnostic_path,
            expected_model_sha256=diagnostic["clothed_assembly_sha256"],
        )
        self.assertTrue(result["integrity_verified"], result["failures"])
        self.assertFalse(result["visual_quality_proven"])
        self.assertFalse(result["owner_approval_proven"])
        self.assertFalse(result["runtime_activation_allowed"])
        visual_review = self.read(review_path)
        self.assertTrue(
            visual_review["decision"].startswith("blocked_continue_reauthor"),
            visual_review["decision"],
        )
        self.assertFalse(visual_review["stable_rig_proven"])
        self.assertFalse(visual_review["wearable_behavior_proven"])
        self.assertFalse(visual_review["runtime_activation_allowed"])

    def test_plan_is_a_fresh_recomputation_of_current_orchestration(self) -> None:
        orchestration = self.read(self.orchestration_path)
        expected = plan_orchestration_request(
            orchestration,
            identity_preflight=evaluate_orchestration_identity_preflight(
                self.root, orchestration
            ),
        )
        expected["orchestration_request_sha256"] = sha256_file(
            self.orchestration_path
        )
        self.assertEqual(expected, self.read(self.plan_path))
        self.assertTrue(expected["authored_component_set_present"])
        self.assertFalse(expected["body_private_review_ready"])
        self.assertFalse(expected["activation_allowed"])

    def test_current_immutable_job_matches_live_request_and_revalidates(self) -> None:
        job_path = (
            self.root
            / "Avatar"
            / "avatar_builder"
            / "component_production"
            / "queued"
            / f"{self.CURRENT_JOB_ID}.json"
        )
        job = self.read(job_path)
        self.assertEqual(
            job["production_request"]["sha256"],
            sha256_file(self.production_request_path),
        )
        self.assertEqual(
            job["orchestration_binding"]["sha256"],
            sha256_file(self.orchestration_path),
        )
        result = process_job(self.root, job_path)
        self.assertEqual("already_processed_verified", result["status"])
        self.assertEqual(self.CURRENT_JOB_ID, result["job_id"])
        manifest_path = self.root / result["package_manifest"]
        manifest = self.read(manifest_path)
        self.assertEqual(result["package_manifest_sha256"], sha256_file(manifest_path))
        self.assertFalse(manifest["stable_rig_proven"])
        self.assertFalse(manifest["owner_review_proven"])
        self.assertFalse(manifest["runtime_activation_allowed"])
        self.assertFalse(manifest["public_export_allowed"])

    def test_current_handoffs_name_the_current_job(self) -> None:
        for relative in (
            "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
            "System/Docs/AVATAR_FUNCTIONAL_V2_HANDOFF_20260630.md",
            "Data/codex_reports/20260716_avatar_component_production_and_route_split.md",
            "Data/codex_reports/20260716_beth_clothed_diagnostic_r6.md",
            "Data/codex_reports/20260716_beth_clothing_authoring_r7_design_blocker.md",
        ):
            text = (self.root / relative).read_text(encoding="utf-8-sig")
            self.assertIn(self.CURRENT_JOB_ID, text, relative)


if __name__ == "__main__":
    unittest.main()
