from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.avatar_body_policy_gate import (  # noqa: E402
    BodyPolicyGateError,
    RuntimeActivationApprovalError,
    activate_staged_model_if_approved,
    enforce_body_policy,
    enforce_marinette_live_body_policy,
    evaluate_body_policy,
)
from tools import create_ladybug_avatar_builder_package as package_builder  # noqa: E402


class AvatarBodyPolicyGateTests(unittest.TestCase):
    MARINETTE_ID = "ladybug_marinette_expanded_smoke"

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _fixture(self, root: Path, candidate_id: str, maturity: str) -> tuple[Path, str]:
        adult_asset = root / "Avatar" / "avatar_builder" / "asset_library" / "base_body_reference" / "adult.glb"
        adult_asset.parent.mkdir(parents=True, exist_ok=True)
        adult_asset.write_bytes(b"exact-adult-only-body")
        digest = hashlib.sha256(adult_asset.read_bytes()).hexdigest()
        self._write_json(
            root / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json",
            {
                "records": [
                    {
                        "id": "base_body_reference:adult",
                        "filename": adult_asset.name,
                        "sha256": digest,
                        "adult_only": True,
                        "allowed_for_non_adult": False,
                    }
                ]
            },
        )
        self._write_json(
            root / "Avatar" / "temp_ai" / candidate_id / "avatar_builder_adjustments.json",
            {"maturity_override": maturity, "maturity_reason": "test fixture"},
        )
        return adult_asset, digest

    def test_non_adult_is_blocked_from_exact_adult_only_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adult_asset, _ = self._fixture(root, self.MARINETTE_ID, "non_adult_doll_safe")
            duplicate_source = root / "legacy" / "womenfemale_body_base_rigged.glb"
            duplicate_source.parent.mkdir(parents=True)
            duplicate_source.write_bytes(adult_asset.read_bytes())

            result = evaluate_body_policy(
                project_root=root,
                candidate_id=self.MARINETTE_ID,
                body_treatment="non_adult_doll_safe",
                selected_asset_paths=[duplicate_source],
                expected_maturity_classes={"non_adult_doll_safe"},
            )

            self.assertEqual(result["status"], "failed")
            self.assertIn(
                "non_adult_or_uncertain_candidate_selected_adult_only_assets",
                result["failures"],
            )

    def test_generated_body_is_blocked_when_lineage_points_to_adult_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adult_asset, _ = self._fixture(root, self.MARINETTE_ID, "non_adult_doll_safe")
            generated = root / "Avatar" / "models" / "temp_ai" / self.MARINETTE_ID / "avatar.glb"
            generated.parent.mkdir(parents=True)
            generated.write_bytes(b"derived-generated-body")
            lineage = generated.with_name("avatar_body_base_rebuild_v1.json")
            self._write_json(lineage, {"source_body": str(adult_asset)})

            with self.assertRaisesRegex(
                BodyPolicyGateError,
                "non_adult_or_uncertain_candidate_selected_adult_only_assets",
            ):
                enforce_marinette_live_body_policy(root, generated)

    def test_confirmed_adult_can_use_required_exact_adult_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adult_asset, digest = self._fixture(root, "kira", "adult")
            result = enforce_body_policy(
                project_root=root,
                candidate_id="kira",
                body_treatment="neutral_adult_anatomy",
                selected_asset_paths=[adult_asset],
                expected_maturity_classes={"adult"},
                required_asset_sha256=digest,
            )
            self.assertEqual(result["status"], "passed")

    def test_persisted_non_adult_kira_override_blocks_exact_adult_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adult_asset, digest = self._fixture(root, "kira", "non_adult_doll_safe")
            result = evaluate_body_policy(
                project_root=root,
                candidate_id="kira",
                body_treatment="neutral_adult_anatomy",
                selected_asset_paths=[adult_asset],
                expected_maturity_classes={"adult"},
                required_asset_sha256=digest,
            )
            self.assertEqual(result["maturity_class"], "non_adult_doll_safe")
            self.assertIn(
                "non_adult_or_uncertain_candidate_selected_adult_only_assets",
                result["failures"],
            )
            self.assertIn(
                "candidate_maturity_does_not_match_builder_contract",
                result["failures"],
            )

    def test_adult_cannot_be_routed_to_doll_safe_treatment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._fixture(root, "kira", "adult")
            result = evaluate_body_policy(
                project_root=root,
                candidate_id="kira",
                body_treatment="non_adult_doll_safe",
                expected_maturity_classes={"adult"},
                require_asset_evidence=False,
            )
            self.assertIn(
                "adult_candidate_cannot_use_non_adult_doll_safe_body_treatment",
                result["failures"],
            )

    def test_reference_character_model_cannot_become_preview_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "reference.glb"
            source.write_bytes(b"full-character-reference")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self._write_json(
                root / "Avatar" / "temp_ai" / "gwen" / "avatar_builder_adjustments.json",
                {"maturity_override": "adult"},
            )
            result = evaluate_body_policy(
                project_root=root,
                candidate_id="gwen",
                body_treatment="neutral_adult_anatomy",
                selected_asset_paths=[source],
                declared_asset_records=[
                    {
                        "id": "reference:gwen",
                        "sha256": digest,
                        "reference_only": True,
                        "copy_as_avatar_body_allowed": False,
                    }
                ],
                expected_maturity_classes={"adult"},
                required_asset_sha256=digest,
            )
            self.assertIn("reference_only_asset_cannot_be_used_as_candidate_body", result["failures"])

    def test_current_marinette_live_lineage_is_read_only_and_policy_invalid(self) -> None:
        live_model = (
            PROJECT_ROOT
            / "Avatar"
            / "models"
            / "temp_ai"
            / self.MARINETTE_ID
            / "avatar.glb"
        )
        before = hashlib.sha256(live_model.read_bytes()).hexdigest()
        result = evaluate_body_policy(
            project_root=PROJECT_ROOT,
            candidate_id=self.MARINETTE_ID,
            body_treatment="non_adult_doll_safe",
            selected_asset_paths=[live_model],
            provenance_manifests=[live_model.with_name("avatar_body_base_rebuild_v1.json")],
            expected_maturity_classes={"non_adult_doll_safe"},
        )
        after = hashlib.sha256(live_model.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "non_adult_or_uncertain_candidate_selected_adult_only_assets",
            result["failures"],
        )

    def test_foundation_package_policy_gate_runs_before_any_copy_or_directory_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_root = root / "models"
            model_root.mkdir()
            (model_root / "avatar.glb").write_bytes(b"blocked-live-body")
            target_root = root / "foundation"
            with (
                patch.object(package_builder, "MODEL_ROOT", model_root),
                patch.object(package_builder, "BASE_RIG_ROOT", target_root),
                patch.object(
                    package_builder,
                    "enforce_marinette_live_body_policy",
                    side_effect=BodyPolicyGateError("blocked before copy"),
                ),
                patch.object(package_builder.shutil, "copy2") as copy2,
            ):
                with self.assertRaisesRegex(BodyPolicyGateError, "blocked before copy"):
                    package_builder.copy_foundation_skeleton()
            copy2.assert_not_called()
            self.assertFalse(target_root.exists())

    def test_staged_redo_is_review_only_by_default_and_cannot_replace_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = root / "review" / "redo.glb"
            live = root / "runtime" / "avatar.glb"
            approval = root / "review" / "activation_approval.json"
            backup = root / "runtime" / "backup.glb"
            staged.parent.mkdir(parents=True)
            live.parent.mkdir(parents=True)
            staged.write_bytes(b"new-staged-review-model")
            live.write_bytes(b"existing-live-model")
            before = live.read_bytes()

            result = activate_staged_model_if_approved(
                project_root=root,
                candidate_id=self.MARINETTE_ID,
                staged_model=staged,
                live_model=live,
                approval_artifact=approval,
                activation_requested=False,
                backup_path=backup,
            )

            self.assertEqual(result["status"], "staged_review_only_not_activated")
            self.assertFalse(result["active_model_replaced"])
            self.assertFalse(result["runtime_activation_allowed"])
            self.assertEqual(live.read_bytes(), before)
            self.assertFalse(backup.exists())

    def test_activation_request_without_exact_approval_fails_before_live_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = root / "review" / "redo.glb"
            live = root / "runtime" / "avatar.glb"
            staged.parent.mkdir(parents=True)
            live.parent.mkdir(parents=True)
            staged.write_bytes(b"new-staged-review-model")
            live.write_bytes(b"existing-live-model")
            before = live.read_bytes()

            with self.assertRaisesRegex(
                RuntimeActivationApprovalError,
                "explicit_activation_approval_artifact_missing_or_invalid",
            ):
                activate_staged_model_if_approved(
                    project_root=root,
                    candidate_id=self.MARINETTE_ID,
                    staged_model=staged,
                    live_model=live,
                    approval_artifact=root / "review" / "missing_approval.json",
                    activation_requested=True,
                )
            self.assertEqual(live.read_bytes(), before)

    def test_exact_hash_approval_is_required_before_staged_model_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = root / "review" / "redo.glb"
            live = root / "runtime" / "avatar.glb"
            approval = root / "review" / "activation_approval.json"
            backup = root / "runtime" / "backup.glb"
            staged.parent.mkdir(parents=True)
            live.parent.mkdir(parents=True)
            staged.write_bytes(b"new-approved-staged-model")
            live.write_bytes(b"existing-live-model")
            digest = hashlib.sha256(staged.read_bytes()).hexdigest()
            approval_payload = {
                "schema_version": 1,
                "candidate_id": self.MARINETTE_ID,
                "approval_status": "approved_for_runtime_activation",
                "runtime_activation_allowed": True,
                "approval_scope": "replace_live_avatar_with_exact_staged_model",
                "approved_by": "Robert",
                "approved_at": "2026-07-15T00:00:00+00:00",
                "staged_model": str(staged.relative_to(root)),
                "staged_sha256": "0" * 64,
            }
            self._write_json(approval, approval_payload)
            with self.assertRaisesRegex(
                RuntimeActivationApprovalError,
                "activation_approval_staged_model_sha256_mismatch",
            ):
                activate_staged_model_if_approved(
                    project_root=root,
                    candidate_id=self.MARINETTE_ID,
                    staged_model=staged,
                    live_model=live,
                    approval_artifact=approval,
                    activation_requested=True,
                    backup_path=backup,
                )
            self.assertEqual(live.read_bytes(), b"existing-live-model")
            self.assertFalse(backup.exists())

            approval_payload["staged_sha256"] = digest
            self._write_json(approval, approval_payload)

            result = activate_staged_model_if_approved(
                project_root=root,
                candidate_id=self.MARINETTE_ID,
                staged_model=staged,
                live_model=live,
                approval_artifact=approval,
                activation_requested=True,
                backup_path=backup,
            )

            self.assertEqual(result["status"], "activated_after_explicit_exact_hash_approval")
            self.assertTrue(result["active_model_replaced"])
            self.assertEqual(live.read_bytes(), staged.read_bytes())
            self.assertEqual(backup.read_bytes(), b"existing-live-model")


if __name__ == "__main__":
    unittest.main()
