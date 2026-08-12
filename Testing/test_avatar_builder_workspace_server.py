from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import avatar_builder_workspace_server as workspace  # noqa: E402


class AvatarBuilderWorkspaceServerTests(unittest.TestCase):
    CANDIDATE_ID = "spider_gwen_spider_gwen_20260606_013325"

    def test_biological_robert_is_a_separate_inactive_builder_roster_entry(self) -> None:
        candidate_id = "BIOLOGICAL_ROBERT_AVATAR"
        self.assertIn(candidate_id, workspace.candidate_ids())

        record = workspace.candidate_record(candidate_id)
        self.assertEqual(record["label"], "Robert — Biological / Player Avatar")
        self.assertEqual(record["ai_type"], "BIOLOGICAL_USER_AVATAR")
        self.assertEqual(record["person_body_type"], "BIOLOGICAL_USER_AVATAR")
        self.assertEqual(record["body_state"], "NO_BODY")
        self.assertFalse(record["creates_temporary_ai_or_mind"])
        self.assertFalse(record["included_in_synthetic_person_selector"])
        self.assertFalse(record["counts_as_active_synthetic_person"])
        self.assertFalse(record["autonomous_life_loop_allowed"])
        self.assertFalse(record["has_runtime_body"])
        self.assertEqual(record["preview_model_url"], "")
        self.assertEqual(record["body_assignment_sha256"], "")

    def test_biological_robert_body_state_fails_closed_on_unknown_value(self) -> None:
        profile = {
            "person_body_type": "BIOLOGICAL_USER_AVATAR",
            "body_state": "ACTIVATED_WITHOUT_OWNER",
        }
        self.assertEqual(
            workspace.avatar_body_state(profile, {}, has_runtime_body=True),
            "NO_BODY",
        )

    @staticmethod
    def _write_model(root: Path, relative_path: str, mtime_ns: int) -> str:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"glTF-test")
        os.utime(path, ns=(mtime_ns, mtime_ns))
        return "/" + relative_path.replace("\\", "/")

    def _candidate_record(self, root: Path, adjustments: dict) -> dict:
        avatar_root = root / "Avatar" / "temp_ai"
        state_root = root / "Avatar" / "state" / "temp_ai"
        candidate_root = root / "TemporaryAI" / "candidates"
        component_plans_root = (
            root / "Avatar" / "avatar_builder" / "component_production" / "plans"
        )
        with (
            patch.object(workspace, "ROOT", root),
            patch.object(workspace, "AVATAR_TEMP_DIR", avatar_root),
            patch.object(workspace, "AVATAR_STATE_DIR", state_root),
            patch.object(workspace, "TEMP_CANDIDATE_DIR", candidate_root),
            patch.object(
                workspace,
                "COMPONENT_PRODUCTION_PLANS_DIR",
                component_plans_root,
            ),
            patch.object(workspace, "load_adjustments", return_value=adjustments),
        ):
            return workspace.candidate_record(self.CANDIDATE_ID)

    def _write_runtime_state(self, root: Path, runtime_url: str) -> Path:
        state_path = (
            root
            / "Avatar"
            / "state"
            / "temp_ai"
            / f"{self.CANDIDATE_ID}.json"
        )
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "model_url": runtime_url,
                    "model_status": "runtime_rigged_body",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return state_path

    def test_newer_failed_builder_preview_beats_stale_overlay_without_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_url = self._write_model(root, "runtime/avatar.glb", 1_000_000_000)
            overlay_url = self._write_model(root, "review/overlay.glb", 2_000_000_000)
            builder_url = self._write_model(root, "review/builder.glb", 3_000_000_000)
            state_path = self._write_runtime_state(root, runtime_url)
            state_before = state_path.read_bytes()

            record = self._candidate_record(
                root,
                {
                    "approval_status": "failed_visual_quality_gate_real_artifacts_available",
                    "builder_preview_model_url": builder_url,
                    "builder_overlay_calibration_model_url": overlay_url,
                },
            )

            self.assertEqual(record["preview_model_url"], builder_url)
            self.assertEqual(record["runtime_model_url"], runtime_url)
            self.assertNotEqual(record["preview_model_url"], record["runtime_model_url"])
            self.assertEqual(state_path.read_bytes(), state_before)

    def test_newest_staged_real_model_beats_builder_and_overlay_without_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_url = self._write_model(root, "runtime/avatar.glb", 1_000_000_000)
            overlay_url = self._write_model(root, "review/overlay.glb", 2_000_000_000)
            builder_url = self._write_model(root, "review/builder.glb", 3_000_000_000)
            staged_url = self._write_model(root, "review/staged.glb", 4_000_000_000)
            state_path = self._write_runtime_state(root, runtime_url)
            state_before = state_path.read_bytes()

            record = self._candidate_record(
                root,
                {
                    "approval_status": "staged_failed_robert_review_not_approved_for_runtime",
                    "builder_preview_model_url": builder_url,
                    "builder_overlay_calibration_model_url": overlay_url,
                    "latest_kira_adult_body_eye_pass": {
                        "review_model": staged_url.lstrip("/"),
                        "active_model_replaced": False,
                        "approval_status": "staged_failed_robert_review_not_approved_for_runtime",
                    },
                },
            )

            self.assertEqual(record["preview_model_url"], staged_url)
            self.assertEqual(record["runtime_model_url"], runtime_url)
            self.assertEqual(state_path.read_bytes(), state_before)

    def test_overlay_then_runtime_are_read_only_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_url = self._write_model(root, "runtime/avatar.glb", 1_000_000_000)
            overlay_url = self._write_model(root, "review/overlay.glb", 2_000_000_000)
            self._write_runtime_state(root, runtime_url)

            overlay_record = self._candidate_record(
                root,
                {
                    "builder_preview_model_url": "/review/missing-builder.glb",
                    "builder_overlay_calibration_model_url": overlay_url,
                },
            )
            runtime_record = self._candidate_record(root, {})

            self.assertEqual(overlay_record["preview_model_url"], overlay_url)
            self.assertEqual(overlay_record["runtime_model_url"], runtime_url)
            self.assertEqual(runtime_record["preview_model_url"], runtime_url)
            self.assertEqual(runtime_record["runtime_model_url"], runtime_url)

    def test_kira_workspace_uses_exact_live_r6_and_labels_anatomy_limit(self) -> None:
        record = workspace.candidate_record("kira")

        self.assertIn("kira_provisional_body_r6.glb", record["runtime_model_url"])
        self.assertEqual(record["preview_model_url"], record["runtime_model_url"])
        self.assertEqual(record["builder_preview_model_url"], record["runtime_model_url"])
        self.assertEqual(record["preview_model_source"], "runtime_selection")
        self.assertTrue(record["runtime_body_selection_valid"])
        self.assertTrue(record["runtime_body_profile_matches_selection"])
        self.assertTrue(record["adult_external_form_trial"])
        self.assertFalse(record["complete_adult_anatomy_proven"])
        self.assertIn("Complete adult anatomy", record["runtime_body_truth_note"])
        self.assertIn("kira_provisional_body_r5.glb", record["historical_builder_preview_model_url"])
        self.assertEqual(record["preview_skin_tone"], "#e6c0a9")
        self.assertEqual(record["preview_material_contract"], "pre_r6_live_light_untextured_v1")
        self.assertTrue(record["preview_eye_component_valid"])
        self.assertEqual(
            record["preview_eye_component_sha256"],
            workspace.KIRA_STAGED_BROWN_EYE_SHA256,
        )
        self.assertFalse(record["preview_eye_component_display_enabled"])
        self.assertEqual(record["preview_eye_component_fit"], {})
        self.assertIn("visual fit is UNAPPROVED", record["preview_eye_component_status"])
        self.assertIn("incompatible", record["preview_eye_component_fit_status"])

        ui_source = (PROJECT_ROOT / "tools/avatar_builder_workspace_server.py").read_text(encoding="utf-8")
        self.assertIn('metric("Complete Adult Anatomy", item.id === "kira" ? (item.complete_adult_anatomy_proven ? "proven" : "NOT PROVEN")', ui_source)
        self.assertIn('metric("Body Candidate Scope", item.id === "kira" ? (item.adult_external_form_trial ? "R6 adult external-form owner-review trial"', ui_source)
        self.assertIn('id="frameFace"', ui_source)
        self.assertIn('id="inspectEyes"', ui_source)
        self.assertIn("Exact staged warm-brown eye component shown by itself. It is NOT seated in R6", ui_source)
        self.assertIn('modelRoot.userData.seatedInR6 = false', ui_source)
        self.assertIn("The staged brown-eye component is hidden because its R6 eyelid/socket visual fit is UNAPPROVED", ui_source)
        self.assertIn("!item.preview_eye_component_display_enabled", ui_source)
        self.assertIn('id="openKiraGallery"', ui_source)
        self.assertIn('selected !== "kira"', ui_source)
        self.assertIn('kind: "kira_owner_review_gallery"', ui_source)
        self.assertIn('candidate_id == "kira"', ui_source)
        self.assertTrue(workspace.KIRA_CURRENT_OWNER_REVIEW_GALLERY.is_file())
        self.assertEqual(
            workspace.KIRA_CURRENT_OWNER_REVIEW_GALLERY.name,
            "KIRA_ALL_CURRENT_BODY_IMAGES_GALLERY.html",
        )

    def test_kira_temporary_functional_body_is_nested_and_inactive(self) -> None:
        self.assertNotIn(
            "kira_temporary_functional_body_20260730",
            workspace.candidate_ids(),
        )
        record = workspace.candidate_record("kira")
        variants = {item["id"]: item for item in record.get("variants", [])}
        self.assertIn("kira_temporary_functional_body_20260730", variants)
        temporary = variants["kira_temporary_functional_body_20260730"]
        self.assertEqual(temporary["body_state"], "NO_BODY")
        self.assertFalse(temporary["has_runtime_body"])
        self.assertEqual(temporary["runtime_model_url"], "")
        self.assertEqual(temporary["preview_model_url"], "")
        self.assertTrue(temporary["is_build_variant"])
        self.assertEqual(temporary["canonical_subject_id"], "kira")

    def test_kira_staged_eye_binding_is_exact_hash_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            eye_file = root / "eye.glb"
            manifest_path = root / "manifest.json"
            eye_bytes = b"staged-eye-test"
            eye_file.write_bytes(eye_bytes)
            digest = hashlib.sha256(eye_bytes).hexdigest()
            manifest_path.write_text(
                json.dumps(
                    {
                        "eye_rig_sha256": digest,
                        "asset_version": "3.2",
                        "eye_color": "warm brown",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "KIRA_STAGED_BROWN_EYE_RIG", eye_file),
                patch.object(workspace, "KIRA_STAGED_BROWN_EYE_MANIFEST", manifest_path),
                patch.object(workspace, "KIRA_STAGED_BROWN_EYE_SHA256", digest),
            ):
                valid = workspace.kira_builder_eye_preview_binding()
                self.assertTrue(valid["valid"])
                self.assertEqual(valid["sha256"], digest)
                self.assertIn("visual fit is UNAPPROVED", valid["status"])

                eye_file.write_bytes(b"mutated-eye-test")
                invalid = workspace.kira_builder_eye_preview_binding()
                self.assertFalse(invalid["valid"])
                self.assertEqual(invalid["url"], "")
                self.assertIn("failed exact-hash validation", invalid["status"])

    def test_picture_first_contract_status_is_exposed_without_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract = root / "review" / "picture_first_contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                json.dumps(
                    {
                        "status": "blocked_not_staged",
                        "staging_allowed": False,
                        "blocking_reasons": ["missing pictures", "missing landmarks"],
                    }
                ),
                encoding="utf-8",
            )

            record = self._candidate_record(
                root,
                {
                    "picture_first_reconstruction_contract": str(
                        contract.relative_to(root)
                    )
                },
            )

            self.assertEqual(record["reconstruction_contract_status"], "blocked_not_staged")
            self.assertFalse(record["reconstruction_staging_allowed"])
            self.assertEqual(record["reconstruction_failure_count"], 2)
            self.assertEqual(
                record["reconstruction_contract_path"],
                "review/picture_first_contract.json",
            )

    def test_component_body_and_advanced_garment_blockers_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan_path = (
                root
                / "Avatar"
                / "avatar_builder"
                / "component_production"
                / "plans"
                / f"{self.CANDIDATE_ID}.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(
                json.dumps(
                    {
                        "candidate_id": self.CANDIDATE_ID,
                        "production_state": "blocked_general_photo_fit_authoring_missing",
                        "authored_component_set_present": False,
                        "multiview_authoring": {
                            "status": "blocked_review_incomplete",
                            "manifest_path": "Avatar/avatar_builder/multiview_authoring/manifests/private/gwen.draft.json",
                            "manifest_sha256": "a" * 64,
                            "manifest_exact_hash_verified": True,
                            "source_count": 15,
                            "exact_hash_source_count": 15,
                            "reviewed_source_count": 0,
                            "front_view_ready": False,
                            "depth_view_ready": False,
                            "full_body_view_ready": False,
                            "single_calibration_frame_ready": False,
                            "reviewed_landmark_count": 0,
                            "missing_landmark_regions": [
                                "face_outline",
                                "feet",
                            ],
                            "scale_review": {"ready": False, "mode": "pending"},
                            "base_body_review": {"ready": False},
                            "review_gaps": [
                                "source_review_missing:owner_ref_001",
                                "required_landmark_region_coverage_incomplete",
                            ],
                            "integrity_failures": [],
                            "authoring_queue_ready": False,
                            "author_backend_available": False,
                        },
                        "body_private_review_ready": False,
                        "body_blocking_reasons": [
                            "multiview_source_review_incomplete",
                            "photo_reconstruction_contract_not_ready",
                            "component_manifest_missing",
                            "topology_evidence_missing",
                            "stable_rig_evidence_missing",
                            "face_lip_sync_evidence_missing",
                            "locomotion_contact_evidence_missing",
                            "owner_clothed_review_evidence_missing",
                        ],
                        "advanced_garment_capability_ready": False,
                        "garment_blocking_reasons": [
                            "wearable_capability_manifest_missing"
                        ],
                        "next_action": "author_subject_specific_photo_fit_then_queue_adoption",
                    }
                ),
                encoding="utf-8",
            )

            record = self._candidate_record(root, {})

            self.assertEqual(
                record["component_production_state"],
                "blocked_general_photo_fit_authoring_missing",
            )
            self.assertFalse(record["component_set_authored"])
            self.assertEqual(record["body_blocker_count"], 8)
            self.assertIn("multiview evidence", record["body_blocker_categories"])
            self.assertIn("photo/identity inputs", record["body_blocker_categories"])
            self.assertIn("authored components", record["body_blocker_categories"])
            self.assertIn("topology/anatomy", record["body_blocker_categories"])
            self.assertIn("rig/deformation", record["body_blocker_categories"])
            self.assertEqual(record["garment_blocker_count"], 1)
            self.assertEqual(
                record["garment_blocker_categories"], ["wearable clothing"]
            )
            self.assertEqual(
                record["component_plan_path"],
                f"Avatar/avatar_builder/component_production/plans/{self.CANDIDATE_ID}.json",
            )
            self.assertEqual(record["multiview_authoring_status"], "blocked_review_incomplete")
            self.assertEqual(
                record["multiview_manifest_path"],
                "Avatar/avatar_builder/multiview_authoring/manifests/private/gwen.draft.json",
            )
            self.assertTrue(record["multiview_manifest_hash_verified"])
            self.assertEqual(record["multiview_exact_hash_source_count"], 15)
            self.assertEqual(record["multiview_reviewed_source_count"], 0)
            self.assertEqual(record["multiview_missing_landmark_region_count"], 2)
            self.assertEqual(record["multiview_review_gap_count"], 2)
            self.assertFalse(record["multiview_authoring_queue_ready"])
            self.assertFalse(record["multiview_author_backend_available"])

    def test_robert_profile_alias_loads_one_normalized_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plans_root = root / "plans"
            plans_root.mkdir()
            normalized_id = "robert_user_avatar_20260716"
            (plans_root / f"{normalized_id}.json").write_text(
                json.dumps(
                    {
                        "candidate_id": normalized_id,
                        "production_state": "blocked_general_photo_fit_authoring_missing",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                workspace, "COMPONENT_PRODUCTION_PLANS_DIR", plans_root
            ):
                plan, path = workspace.load_component_production_plan(
                    "robert_mcmurrer_presence_ai"
                )

            self.assertEqual(plan["candidate_id"], normalized_id)
            self.assertEqual(path, plans_root / f"{normalized_id}.json")

    def test_hash_bound_stale_component_plan_is_not_shown_as_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plans_root = root / "Avatar" / "avatar_builder" / "component_production" / "plans"
            requests_root = root / "Avatar" / "avatar_builder" / "orchestration_requests"
            plans_root.mkdir(parents=True)
            requests_root.mkdir(parents=True)
            request_path = requests_root / f"{self.CANDIDATE_ID}.json"
            request_path.write_text('{"revision":2}', encoding="utf-8")
            (plans_root / f"{self.CANDIDATE_ID}.json").write_text(
                json.dumps(
                    {
                        "candidate_id": self.CANDIDATE_ID,
                        "production_state": "component_set_authored_ready_for_immutable_adoption",
                        "authored_component_set_present": True,
                        "orchestration_request_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "COMPONENT_PRODUCTION_PLANS_DIR", plans_root),
            ):
                plan, path = workspace.load_component_production_plan(self.CANDIDATE_ID)

            self.assertEqual({}, plan)
            self.assertIsNone(path)

    def test_inactive_avatar_only_variant_is_listed_with_bound_maturity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = root / "Avatar" / "avatar_builder" / "avatar_only_variants"
            variants.mkdir(parents=True)
            variant_id = "gwen_adult_avatar_test"
            (variants / f"{variant_id}.json").write_text(
                json.dumps(
                    {
                        "candidate_id": variant_id,
                        "display_name": "Gwen adult avatar test",
                        "profile_scope": "avatar_only_inactive_variant",
                        "creates_temporary_ai_or_mind": False,
                        "runtime_activation_allowed": False,
                        "maturity": {"lane": "adult"},
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "AVATAR_TEMP_DIR", root / "Avatar" / "temp_ai"),
                patch.object(workspace, "AVATAR_STATE_DIR", root / "Avatar" / "state" / "temp_ai"),
                patch.object(workspace, "TEMP_CANDIDATE_DIR", root / "TemporaryAI" / "candidates"),
                patch.object(workspace, "AVATAR_ONLY_VARIANTS_DIR", variants),
                patch.object(workspace, "load_adjustments", return_value={}),
            ):
                ids = workspace.candidate_ids()
                profile = workspace.load_profile(variant_id)

            self.assertIn(variant_id, ids)
            self.assertEqual(profile["ai_type"], "avatar_only_inactive_variant")
            self.assertEqual(
                profile["age_review"]["maturity_class_override"], "adult"
            )
            self.assertFalse(profile["runtime_activation_allowed"])

    def test_age_up_lane_loads_as_presentation_provenance_not_maturity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = root / "Avatar" / "avatar_builder" / "avatar_only_variants"
            variants.mkdir(parents=True)
            variant_id = "separate_age_progressed_presentation_variant"
            (variants / f"{variant_id}.json").write_text(
                json.dumps(
                    {
                        "candidate_id": variant_id,
                        "display_name": "Separate age-progressed presentation variant",
                        "profile_scope": "avatar_only_inactive_variant",
                        "creates_temporary_ai_or_mind": False,
                        "runtime_activation_allowed": False,
                        "maturity": {"lane": "adult_aged_up_variant"},
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "AVATAR_TEMP_DIR", root / "Avatar" / "temp_ai"),
                patch.object(workspace, "AVATAR_STATE_DIR", root / "Avatar" / "state" / "temp_ai"),
                patch.object(workspace, "TEMP_CANDIDATE_DIR", root / "TemporaryAI" / "candidates"),
                patch.object(workspace, "AVATAR_ONLY_VARIANTS_DIR", variants),
                patch.object(workspace, "load_adjustments", return_value={}),
            ):
                profile = workspace.load_profile(variant_id)

            age_review = profile["age_review"]
            self.assertEqual(
                age_review["age_progression_presentation_label"],
                "adult_aged_up_variant",
            )
            self.assertNotIn("maturity_class_override", age_review)
            maturity = workspace.infer_avatar_maturity_policy(variant_id, profile)
            self.assertEqual(
                maturity["maturity_class"], "uncertain_non_adult_safe_default"
            )
            self.assertEqual(maturity["exact_maturity_status"], "unresolved")
            self.assertFalse(maturity["adult_anatomy_assets_allowed"])

    def test_source_bound_build_variant_is_grouped_under_one_canonical_subject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = root / "Avatar" / "avatar_builder" / "avatar_only_variants"
            variants.mkdir(parents=True)
            canonical = "kira"
            variant_id = "kira_adult_avatar_build_variant_20260716"
            canonical_root = root / "TemporaryAI" / "candidates" / canonical
            canonical_root.mkdir(parents=True)
            (canonical_root / "temporary_ai_profile.json").write_text(
                json.dumps(
                    {
                        "candidate_id": canonical,
                        "display_name": "Kira",
                        "age_review": {"maturity_class_override": "adult"},
                    }
                ),
                encoding="utf-8",
            )
            (variants / f"{variant_id}.json").write_text(
                json.dumps(
                    {
                        "candidate_id": variant_id,
                        "display_name": "Kira Adult Avatar Build Variant",
                        "profile_scope": "avatar_only_inactive_variant",
                        "source_candidate_id": canonical,
                        "creates_temporary_ai_or_mind": False,
                        "runtime_activation_allowed": False,
                        "maturity": {"lane": "adult"},
                        "truth_note": "This is not a second Kira.",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "AVATAR_TEMP_DIR", root / "Avatar" / "temp_ai"),
                patch.object(workspace, "AVATAR_STATE_DIR", root / "Avatar" / "state" / "temp_ai"),
                patch.object(workspace, "TEMP_CANDIDATE_DIR", root / "TemporaryAI" / "candidates"),
                patch.object(workspace, "AVATAR_ONLY_VARIANTS_DIR", variants),
                patch.object(
                    workspace,
                    "COMPONENT_PRODUCTION_PLANS_DIR",
                    root / "Avatar" / "avatar_builder" / "component_production" / "plans",
                ),
                patch.object(workspace, "load_adjustments", return_value={}),
            ):
                ids = workspace.candidate_ids()
                record = workspace.candidate_record(canonical)

            self.assertIn(canonical, ids)
            self.assertNotIn(variant_id, ids)
            self.assertEqual(record["variant_count"], 1)
            self.assertEqual(record["variants"][0]["id"], variant_id)
            self.assertTrue(record["variants"][0]["is_build_variant"])
            self.assertEqual(record["variants"][0]["canonical_subject_id"], canonical)
            self.assertIn("not a second Kira", record["variants"][0]["variant_truth_note"])

    def test_workspace_explains_private_review_boundary_without_claiming_authentication(self) -> None:
        page = workspace.html().decode("utf-8")
        self.assertIn("exact subject and biological Robert only", page)
        self.assertIn("does not provide remote identity authentication", page)
        self.assertIn("Non-adult and uncertain subjects stay doll-safe", page)
        self.assertIn("derived avatar build variant (not a second person)", page)

    def test_superseded_gwen_variant_is_hidden_but_canonical_gwen_remains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = root / "Avatar" / "avatar_builder" / "avatar_only_variants"
            variants.mkdir(parents=True)
            superseded = "spider_gwen_adult_avatar_project_variant_20260716"
            canonical = self.CANDIDATE_ID
            (variants / f"{superseded}.json").write_text(
                json.dumps({"candidate_id": superseded}), encoding="utf-8"
            )
            canonical_root = root / "TemporaryAI" / "candidates" / canonical
            canonical_root.mkdir(parents=True)
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "AVATAR_TEMP_DIR", root / "Avatar" / "temp_ai"),
                patch.object(workspace, "AVATAR_STATE_DIR", root / "Avatar" / "state" / "temp_ai"),
                patch.object(workspace, "TEMP_CANDIDATE_DIR", root / "TemporaryAI" / "candidates"),
                patch.object(workspace, "AVATAR_ONLY_VARIANTS_DIR", variants),
            ):
                ids = workspace.candidate_ids()

            self.assertIn(canonical, ids)
            self.assertNotIn(superseded, ids)
            self.assertEqual(
                canonical, workspace.normalize_workspace_candidate_id(superseded)
            )

    def test_uploaded_picture_is_hash_bound_private_and_unapproved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            avatar_root = root / "Avatar" / "temp_ai"
            raw = b"private-test-picture-bytes"
            with (
                patch.object(workspace, "ROOT", root),
                patch.object(workspace, "AVATAR_TEMP_DIR", avatar_root),
                patch.object(workspace, "load_adjustments", return_value={}),
                patch.object(workspace, "save_adjustments") as save_adjustments,
            ):
                result = workspace.save_uploaded_references(
                    self.CANDIDATE_ID,
                    [
                        {
                            "name": "front.jpg",
                            "type": "image/jpeg",
                            "data_url": "data:image/jpeg;base64,"
                            + base64.b64encode(raw).decode("ascii"),
                        }
                    ],
                )
                manifest = json.loads(
                    (root / result["manifest"]).read_text(encoding="utf-8")
                )

            record = manifest["files"][0]
            self.assertEqual(record["subject_id"], self.CANDIDATE_ID)
            self.assertEqual(record["status"], "uploaded_for_private_review")
            self.assertEqual(record["view"], "unclassified")
            self.assertFalse(record["identity_evidence_approved"])
            self.assertTrue(record["artifact_hash_verified"])
            self.assertEqual(len(record["sha256"]), 64)
            save_adjustments.assert_called_once()


if __name__ == "__main__":
    unittest.main()
