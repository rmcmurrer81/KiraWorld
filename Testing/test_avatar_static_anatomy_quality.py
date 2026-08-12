import hashlib
import unittest

from Core.avatar_static_anatomy_quality import (
    ANATOMY_ZONES,
    REQUIRED_VIEWS,
    SHADER_CHANNELS,
    StaticReviewEvidence,
    validate_adult_male_surface_landmarks,
    validate_bounded_geometry_repair,
    validate_static_review,
)


class AvatarStaticAnatomyQualityTests(unittest.TestCase):
    def evidence(self, **changes):
        candidate_hash = hashlib.sha256(b"candidate-v23").hexdigest()
        rendered_hashes = {
            view: hashlib.sha256(f"render:{view}".encode("utf-8")).hexdigest()
            for view in REQUIRED_VIEWS
        }
        values = dict(
            views=sorted(REQUIRED_VIEWS),
            anatomy_zones=sorted(ANATOMY_ZONES),
            shader_channels=sorted(SHADER_CHANNELS),
            hair_color_class="dark_blonde",
            hair_is_removable=True,
            anatomy_is_primary_component=True,
            main_skin_boundary_edges=0,
            main_skin_nonmanifold_edges=0,
            ao_baked_into_albedo=False,
            runtime_claimed=False,
            motion_claimed=False,
            candidate_sha256=candidate_hash,
            rendered_view_sha256=rendered_hashes,
            rendered_view_candidate_sha256={
                view: candidate_hash for view in REQUIRED_VIEWS
            },
            rendered_visual_review_decision="PENDING_OWNER_REVIEW",
            pelvis_attachment_visual_status="PENDING_OWNER_REVIEW",
            pelvis_open_or_spatial_gap_detected=False,
            visual_rejection_reasons=[],
        )
        values.update(changes)
        return StaticReviewEvidence(**values)

    def test_complete_static_evidence_passes_technical_gate_only(self):
        report = validate_static_review(self.evidence())
        self.assertEqual(
            report["status"], "AWAITING ROBERT STATIC LIKENESS REVIEW"
        )
        self.assertEqual(report["technical_gate_status"], "PASS_STATIC_TECHNICAL_GATE")
        self.assertEqual(report["owner_likeness_approval"], "REQUIRED")
        self.assertFalse(report["runtime_activation_allowed"])

    def test_brown_hair_is_rejected_for_current_owner_authority(self):
        report = validate_static_review(self.evidence(hair_color_class="brown"))
        self.assertIn("OWNER_HAIR_COLOR_MISMATCH", report["failures"])

    def test_baked_ao_and_motion_claim_are_blocked(self):
        report = validate_static_review(
            self.evidence(ao_baked_into_albedo=True, motion_claimed=True)
        )
        self.assertIn("AO_OR_CAVITY_BAKED_INTO_SKIN_COLOR", report["failures"])
        self.assertIn("STATIC_REVIEW_MAKES_UNPROVEN_RUNTIME_CLAIM", report["failures"])

    def test_bounded_repair_rejects_global_scaling_and_protected_drift(self):
        report = validate_bounded_geometry_repair({
            "global_scaling_used": True,
            "boolean_union_used": False,
            "imported_reference_surface_used": False,
            "changed_outside_mask_count": 1,
            "hands_fingers_forearms_delta": 0.01,
            "lower_legs_feet_delta": 0,
            "head_face_neck_delta": 0,
        })
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("GLOBAL_SCALING_PROHIBITED", report["failures"])
        self.assertIn("GEOMETRY_CHANGED_OUTSIDE_APPROVED_MASK", report["failures"])

    def test_bounded_repair_preserves_protected_regions(self):
        report = validate_bounded_geometry_repair({
            "global_scaling_used": False,
            "boolean_union_used": False,
            "imported_reference_surface_used": False,
            "changed_outside_mask_count": 0,
            "hands_fingers_forearms_delta": 0,
            "lower_legs_feet_delta": 0,
            "head_face_neck_delta": 0,
        })
        self.assertEqual(report["status"], "PASS_BOUNDED_GEOMETRY_GATE")

    def test_spatial_pelvis_gap_overrides_clean_topology(self):
        report = validate_static_review(
            self.evidence(
                main_skin_boundary_edges=0,
                main_skin_nonmanifold_edges=0,
                pelvis_open_or_spatial_gap_detected=True,
            )
        )
        self.assertEqual(report["technical_gate_status"], "BLOCKED")
        self.assertEqual(
            report["status"], "AWAITING ROBERT STATIC LIKENESS REVIEW"
        )
        self.assertIn("PELVIS_OPEN_OR_SPATIAL_GAP_VISIBLE", report["failures"])
        self.assertFalse(report["runtime_activation_allowed"])

    def test_visual_attachment_rejection_overrides_clean_topology(self):
        report = validate_static_review(
            self.evidence(
                main_skin_boundary_edges=0,
                main_skin_nonmanifold_edges=0,
                rendered_visual_review_decision="REJECTED_BY_OWNER",
                pelvis_attachment_visual_status="REJECTED",
                visual_rejection_reasons=[
                    "root appears detached in the hash-bound side render"
                ],
            )
        )
        self.assertEqual(report["technical_gate_status"], "BLOCKED")
        self.assertIn("PELVIS_ATTACHMENT_VISUALLY_REJECTED", report["failures"])
        self.assertIn(
            "RENDERED_VISUAL_REVIEW_REJECTED_BY_OWNER", report["failures"]
        )
        self.assertEqual(
            report["status"], "AWAITING ROBERT STATIC LIKENESS REVIEW"
        )

    def test_render_hashes_must_bind_to_exact_candidate(self):
        wrong_hash = hashlib.sha256(b"a different body").hexdigest()
        report = validate_static_review(
            self.evidence(
                rendered_view_candidate_sha256={
                    view: wrong_hash for view in REQUIRED_VIEWS
                }
            )
        )
        self.assertEqual(report["technical_gate_status"], "BLOCKED")
        self.assertIn("RENDERED_REVIEW_NOT_BOUND_TO_CANDIDATE", report["failures"])

    def test_owner_approval_still_does_not_grant_runtime_activation(self):
        report = validate_static_review(
            self.evidence(
                rendered_visual_review_decision="APPROVED_BY_OWNER",
                pelvis_attachment_visual_status="ACCEPTED_BY_OWNER",
            )
        )
        self.assertEqual(report["status"], "STATIC_OWNER_APPROVED")
        self.assertEqual(report["technical_gate_status"], "PASS_STATIC_TECHNICAL_GATE")
        self.assertFalse(report["runtime_activation_allowed"])

    def valid_landmarks(self, **changes):
        values = {
            "coordinate_convention": "z_up_negative_y_front",
            "body_height_m": 1.81,
            "primary_skin_component_count": 1,
            "anatomy_primary_skin_same_component": True,
            "main_skin_boundary_edges": 0,
            "main_skin_nonmanifold_edges": 0,
            "separate_anatomy_mesh_count": 0,
            "front_superior_gap_rays": 0,
            "side_root_gap_rays": 0,
            "three_quarter_root_gap_rays": 0,
            "side_silhouette_self_intersections": 0,
            "shaft_root_surface_distance_m": 0.0,
            "scrotal_root_surface_distance_m": 0.0,
            "shaft_root_center": [0.0, -0.13, 0.80],
            "shaft_distal_center": [0.0, -0.16, 0.73],
            "scrotal_root_center": [0.0, -0.10, 0.76],
            "scrotal_lowest_center": [0.0, -0.10, 0.69],
            "shaft_body_width_m": 0.034,
            "glans_max_width_m": 0.038,
            "glans_neck_width_m": 0.031,
            "scrotal_bilateral_envelope_present": True,
            "scrotal_raphe_continuity_present": True,
            "perineal_transition_continuous": True,
        }
        values.update(changes)
        return values

    def test_adult_surface_landmarks_pass_structure_but_still_need_owner(self):
        report = validate_adult_male_surface_landmarks(self.valid_landmarks())
        self.assertEqual(
            report["status"], "PASS_ADULT_MALE_SURFACE_LANDMARK_GATE"
        )
        self.assertTrue(report["owner_visual_review_still_required"])
        self.assertFalse(report["runtime_activation_allowed"])

    def test_rendered_gap_blocks_clean_topology(self):
        report = validate_adult_male_surface_landmarks(
            self.valid_landmarks(front_superior_gap_rays=4)
        )
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn(
            "SUPERIOR_PUBIC_BACKGROUND_GAP_VISIBLE", report["failures"]
        )

    def test_low_disconnected_root_and_wrong_order_are_blocked(self):
        report = validate_adult_male_surface_landmarks(
            self.valid_landmarks(
                shaft_root_surface_distance_m=0.03,
                shaft_root_center=[0.0, -0.13, 0.70],
                scrotal_root_center=[0.0, -0.10, 0.76],
            )
        )
        self.assertIn(
            "SHAFT_ROOT_NOT_CONTINUOUS_WITH_PUBIC_SURFACE",
            report["failures"],
        )
        self.assertIn(
            "SHAFT_ROOT_NOT_SUPERIOR_TO_SCROTAL_ROOT", report["failures"]
        )

    def test_separate_mesh_and_missing_perineal_transition_are_blocked(self):
        report = validate_adult_male_surface_landmarks(
            self.valid_landmarks(
                anatomy_primary_skin_same_component=False,
                separate_anatomy_mesh_count=1,
                perineal_transition_continuous=False,
            )
        )
        self.assertIn("ANATOMY_NOT_IN_PRIMARY_SKIN_COMPONENT", report["failures"])
        self.assertIn("SEPARATE_ANATOMY_MESH_PRESENT", report["failures"])
        self.assertIn("PERINEAL_TRANSITION_NOT_CONTINUOUS", report["failures"])


if __name__ == "__main__":
    unittest.main()
