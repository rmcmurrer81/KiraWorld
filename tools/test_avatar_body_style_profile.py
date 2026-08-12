"""Pure-Python tests for the identity-free adult body-style profile gate."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_body_style_profile import (
    BodyStyleProfileError,
    DEFAULT_PROFILE_PATH,
    MAX_TARGET_WEIGHT,
    OFFICIAL_TARGET_ROOT,
    SCHEMA_PATH,
    load_validated_body_style_profile,
    validate_body_style_profile,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdultBodyStyleProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="avatar_body_style_profile_"
        )
        self.root = Path(self.temporary.name)
        self.profile = json.loads(
            (PROJECT_ROOT / DEFAULT_PROFILE_PATH).read_text(encoding="utf-8")
        )
        paths = {SCHEMA_PATH, DEFAULT_PROFILE_PATH}
        for license_record in self.profile["source_licenses"]:
            paths.add(Path(license_record["evidence_path"]))
        for target in self.profile["shape_targets"]:
            paths.add(Path(target["path"]))
        for source in self.profile["design_direction"]["sources"]:
            if source["kind"] == "audited_generic_earlier_render":
                paths.add(Path(source["path"]))
                paths.add(Path(source["audit_path"]))
        for relative in paths:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / relative, destination)
        self.write_profile()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_profile(self) -> None:
        path = self.root / DEFAULT_PROFILE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.profile, indent=2) + "\n",
            encoding="utf-8",
        )

    def validate(self) -> dict:
        self.write_profile()
        return validate_body_style_profile(self.root, DEFAULT_PROFILE_PATH)

    def assert_blocked(self, code: str) -> dict:
        report = self.validate()
        self.assertFalse(report["valid"])
        self.assertIn(code, report["blockers"])
        self.assertFalse(report["build_performed"])
        self.assertFalse(report["blender_invoked"])
        self.assertFalse(report["runtime_mutation_performed"])
        return report

    def test_repository_profile_and_every_binding_validate(self) -> None:
        report = validate_body_style_profile(PROJECT_ROOT)
        self.assertTrue(report["valid"], report["blockers"])
        self.assertEqual("VALIDATED_DECLARATIVE_STYLE_PROFILE", report["status"])
        self.assertEqual(12, report["target_count"])
        self.assertEqual(2, report["symmetric_pair_count"])
        self.assertEqual(2, report["design_source_count"])
        self.assertTrue(all(row["verified"] for row in report["resolved_targets"]))
        self.assertEqual(
            _sha256(PROJECT_ROOT / DEFAULT_PROFILE_PATH),
            report["profile_sha256"],
        )
        self.assertEqual(_sha256(PROJECT_ROOT / SCHEMA_PATH), report["schema_sha256"])
        self.assertFalse(report["build_performed"])
        self.assertFalse(report["blender_invoked"])
        self.assertFalse(report["render_performed"])
        self.assertFalse(report["candidate_saved"])
        self.assertFalse(report["runtime_mutation_performed"])
        self.assertFalse(report["runtime_activation_allowed"])

    def test_profile_captures_requested_identity_free_direction(self) -> None:
        self.assertEqual(1.651, self.profile["dimensions"]["target_height_m"])
        self.assertEqual(
            "owner_specified_avatar_target_not_extracted_biometric",
            self.profile["dimensions"]["basis"],
        )
        self.assertFalse(
            self.profile["dimensions"]["private_person_measurements_used"]
        )
        self.assertFalse(
            self.profile["dimensions"]["proportion_or_biometric_indices_present"]
        )
        skin = self.profile["material_profile"]["skin"]
        self.assertEqual("#C7A08E", skin["base_srgb_hex"])
        self.assertFalse(skin["pale_r13_direction_allowed"])
        self.assertEqual("brown", self.profile["eye_profile"]["iris_color_family"])
        hair = self.profile["hair_profile"]
        self.assertEqual(
            "asymmetric_deep_side_part_shoulder_length_loose_waves",
            hair["style"],
        )
        self.assertTrue(hair["wind"]["required"])
        self.assertTrue(hair["wet"]["required"])
        self.assertEqual(
            "SPECIFICATION_ONLY_NOT_RUNTIME_PROVEN",
            hair["readiness_status"],
        )
        self.assertFalse(hair["source_geometry_copied"])

    def test_profile_is_style_only_and_cannot_qualify_or_activate(self) -> None:
        separation = self.profile["separation_contract"]
        self.assertEqual("style_only", separation["layer"])
        self.assertTrue(separation["adult_foundation_qualification_required"])
        self.assertFalse(separation["changes_anatomy_topology"])
        self.assertFalse(separation["contains_or_copies_geometry"])
        self.assertFalse(separation["anatomy_relationships_included"])
        self.assertFalse(separation["can_qualify_adult_foundation"])
        contract = self.profile["application_contract"]
        self.assertFalse(contract["runtime_activation_allowed"])
        self.assertFalse(contract["render_save_or_export_authorized_by_profile"])
        self.assertTrue(
            contract["post_style_topology_anatomy_deformation_review_required"]
        )

    def test_non_adult_or_unconfirmed_authority_fails_closed(self) -> None:
        mutations = (
            ("maturity_status", "unresolved", "authority_maturity_must_be_confirmed_adult"),
            ("age_gate", "all_ages", "authority_age_gate_must_be_adult_only"),
            ("body_class", "unknown", "authority_body_class_must_be_adult_female"),
            ("unknown_or_minor_blocked", False, "authority_unknown_or_minor_not_blocked"),
        )
        original = deepcopy(self.profile["authority"])
        for field, value, blocker in mutations:
            with self.subTest(field=field):
                self.profile["authority"] = deepcopy(original)
                self.profile["authority"][field] = value
                self.assert_blocked(blocker)
        self.profile["authority"] = original

    def test_anatomy_or_geometry_authority_cannot_be_smuggled_into_style(self) -> None:
        self.profile["separation_contract"]["changes_anatomy_topology"] = True
        self.assert_blocked(
            "separation_forbidden_capability_enabled:changes_anatomy_topology"
        )
        self.profile["separation_contract"]["changes_anatomy_topology"] = False
        self.profile["separation_contract"]["copied_anatomy_mesh"] = "forbidden"
        self.assert_blocked(
            "separation_contract_field_unexpected:copied_anatomy_mesh"
        )

    def test_private_measurements_and_indices_are_rejected(self) -> None:
        self.profile["dimensions"]["private_person_measurements_used"] = True
        self.assert_blocked("private_person_measurements_present")
        self.profile["dimensions"]["private_person_measurements_used"] = False
        self.profile["dimensions"]["proportion_or_biometric_indices_present"] = True
        self.assert_blocked("proportion_or_biometric_indices_present")

    def test_target_hash_drift_and_unsafe_paths_are_rejected(self) -> None:
        self.profile["shape_targets"][0]["sha256"] = "0" * 64
        self.assert_blocked("shape_target_0_sha256_mismatch")
        self.profile = json.loads(
            (PROJECT_ROOT / DEFAULT_PROFILE_PATH).read_text(encoding="utf-8")
        )
        self.profile["shape_targets"][0]["path"] = "../escaped.target"
        self.assert_blocked("shape_target_0_path_unsafe")

    def test_target_outside_official_root_is_rejected_even_when_hash_matches(self) -> None:
        outside = self.root / "Avatar/avatar_builder/style_profiles/not_official.target"
        outside.write_text("0 0.0 0.0 0.0\n", encoding="utf-8")
        target = self.profile["shape_targets"][0]
        target["path"] = outside.relative_to(self.root).as_posix()
        target["sha256"] = _sha256(outside)
        self.assert_blocked("shape_target_0_path_outside_allowed_root")

    def test_weights_are_positive_numeric_and_bounded(self) -> None:
        self.assertEqual(0.25, MAX_TARGET_WEIGHT)
        for value in (True, 0.0, -0.1, 0.251):
            with self.subTest(value=value):
                self.profile["shape_targets"][0]["weight"] = value
                self.assert_blocked("shape_target_0_weight_out_of_bounds")

    def test_left_right_pairs_must_be_complete_equal_and_matching(self) -> None:
        self.profile["shape_targets"] = [
            target
            for target in self.profile["shape_targets"]
            if target["target_id"] != "upper_leg_tone_right"
        ]
        self.assert_blocked("symmetry_pair_incomplete:upper_leg_tone")
        self.profile = json.loads(
            (PROJECT_ROOT / DEFAULT_PROFILE_PATH).read_text(encoding="utf-8")
        )
        right = next(
            target
            for target in self.profile["shape_targets"]
            if target["target_id"] == "upper_leg_tone_right"
        )
        right["weight"] = 0.036
        self.assert_blocked("symmetry_pair_weight_mismatch:upper_leg_tone")

    def test_unilateral_target_cannot_claim_bilateral_symmetry(self) -> None:
        left = next(
            target
            for target in self.profile["shape_targets"]
            if target["target_id"] == "upper_arm_tone_left"
        )
        left["symmetry"] = {"mode": "bilateral_single_target"}
        index = self.profile["shape_targets"].index(left)
        self.assert_blocked(f"shape_target_{index}_unilateral_target_marked_bilateral")

    def test_license_binding_and_license_evidence_are_hash_bound(self) -> None:
        self.profile["shape_targets"][0]["license_binding_id"] = "missing_license"
        self.assert_blocked("shape_target_0_license_binding_unknown")
        self.profile = json.loads(
            (PROJECT_ROOT / DEFAULT_PROFILE_PATH).read_text(encoding="utf-8")
        )
        evidence = self.root / self.profile["source_licenses"][0]["evidence_path"]
        evidence.write_bytes(evidence.read_bytes() + b"drift")
        self.assert_blocked("source_license_0_evidence_sha256_mismatch")

    def test_warm_skin_brown_eyes_and_dynamic_hair_fail_closed(self) -> None:
        self.profile["material_profile"]["skin"]["base_srgb_hex"] = "#F2E8E4"
        self.assert_blocked("skin_palette_drifted_from_warm_reference")
        self.profile = json.loads(
            (PROJECT_ROOT / DEFAULT_PROFILE_PATH).read_text(encoding="utf-8")
        )
        self.profile["eye_profile"]["iris_color_family"] = "gray"
        self.assert_blocked("eye_iris_color_must_be_brown")
        self.profile["eye_profile"]["iris_color_family"] = "brown"
        self.profile["hair_profile"]["wind"]["required"] = False
        self.assert_blocked("hair_wind_readiness_not_required")
        self.profile["hair_profile"]["wind"]["required"] = True
        self.profile["hair_profile"]["readiness_status"] = "RUNTIME_PROVEN"
        self.assert_blocked("hair_readiness_status_overclaims_proof")

    def test_render_reference_is_qualitative_only_and_hash_bound(self) -> None:
        render = next(
            source
            for source in self.profile["design_direction"]["sources"]
            if source["kind"] == "audited_generic_earlier_render"
        )
        self.assertEqual(
            "REJECTED_PRIVATE_ENGINEERING_EVIDENCE",
            render["source_candidate_status"],
        )
        self.assertIn("geometry_copy", render["forbidden_uses"])
        self.assertNotIn("geometry_copy", render["allowed_uses"])
        render_path = self.root / render["path"]
        render_path.write_bytes(render_path.read_bytes() + b"drift")
        self.assert_blocked("design_render_sha256_mismatch")

    def test_unknown_fields_and_forbidden_application_authority_block(self) -> None:
        self.profile["unknown_root_field"] = True
        self.assert_blocked("style_profile_field_unexpected:unknown_root_field")
        self.profile.pop("unknown_root_field")
        self.profile["application_contract"]["runtime_activation_allowed"] = True
        self.assert_blocked(
            "application_forbidden_authority_enabled:runtime_activation_allowed"
        )

    def test_loader_returns_validated_profile_and_raises_for_invalid(self) -> None:
        profile, report = load_validated_body_style_profile(
            self.root,
            DEFAULT_PROFILE_PATH,
        )
        self.assertTrue(report["valid"])
        self.assertEqual(self.profile["profile_id"], profile["profile_id"])
        self.profile["authority"]["maturity_status"] = "unresolved"
        self.write_profile()
        with self.assertRaises(BodyStyleProfileError):
            load_validated_body_style_profile(self.root, DEFAULT_PROFILE_PATH)

    def test_official_target_root_is_project_relative(self) -> None:
        self.assertFalse(OFFICIAL_TARGET_ROOT.is_absolute())
        self.assertNotIn("..", OFFICIAL_TARGET_ROOT.parts)
        for target in self.profile["shape_targets"]:
            path = Path(target["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
