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

import Core.avatar_asset_library as avatar_asset_library_module  # noqa: E402

from Core.avatar_asset_library import (  # noqa: E402
    build_adult_face_body_trials,
    build_avatar_asset_library,
    classify_avatar_asset,
    infer_avatar_maturity_policy,
    run_hair_style_trials,
    validate_candidate_maturity_identity,
    validate_avatar_body_policy,
    validate_wardrobe_asset_compatibility,
    write_avatar_builder_learning_plans,
)


class AvatarAssetLibraryTests(unittest.TestCase):
    def _fake_model(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"glb-test-data:" + path.name.encode("utf-8"))

    def _fake_glb_with_node_name(self, path: Path, node_name: str) -> None:
        payload = json.dumps(
            {"asset": {"version": "2.0"}, "nodes": [{"name": node_name}]},
            separators=(",", ":"),
        ).encode("utf-8")
        payload += b" " * ((4 - len(payload) % 4) % 4)
        total = 12 + 8 + len(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"glTF"
            + (2).to_bytes(4, "little")
            + total.to_bytes(4, "little")
            + len(payload).to_bytes(4, "little")
            + (0x4E4F534A).to_bytes(4, "little")
            + payload
        )

    def _skinned_wearable_glb(self, path: Path) -> None:
        binary = b"\x00" * 36
        document = {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": len(binary)}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": 12},
                {"buffer": 0, "byteOffset": 12, "byteLength": 8},
                {"buffer": 0, "byteOffset": 20, "byteLength": 16},
            ],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 1, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5123, "count": 1, "type": "VEC4"},
                {"bufferView": 2, "componentType": 5126, "count": 1, "type": "VEC4"},
            ],
            "meshes": [
                {
                    "name": "robe_wearable",
                    "primitives": [
                        {"attributes": {"POSITION": 0, "JOINTS_0": 1, "WEIGHTS_0": 2}}
                    ],
                }
            ],
            "nodes": [
                {"name": "root_joint"},
                {"name": "robe_skinned_mesh", "mesh": 0, "skin": 0},
            ],
            "skins": [{"name": "foundation_skeleton_v1", "joints": [0]}],
            "scenes": [{"nodes": [0, 1]}],
            "scene": 0,
        }
        payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
        payload += b" " * ((4 - len(payload) % 4) % 4)
        total = 12 + 8 + len(payload) + 8 + len(binary)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"glTF"
            + (2).to_bytes(4, "little")
            + total.to_bytes(4, "little")
            + len(payload).to_bytes(4, "little")
            + (0x4E4F534A).to_bytes(4, "little")
            + payload
            + len(binary).to_bytes(4, "little")
            + (0x004E4942).to_bytes(4, "little")
            + binary
        )

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_json(self, path: Path, payload: dict) -> str:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self._sha256(path)

    def _evidence_payload(
        self,
        *,
        asset_sha256: str,
        body_sha256: str,
        rig_signature: str,
        maturity_class: str = "adult",
    ) -> dict:
        return {
            "schema_version": 1,
            "artifact_type": "wardrobe_fit_rig_evidence",
            "status": "passed",
            "producer": {
                "kind": "independent_wardrobe_evidence_pipeline",
                "self_declared": False,
                "run_id": "isolated_wardrobe_test_run",
            },
            "independent_from_asset_intake": True,
            "bindings": {
                "asset_sha256": asset_sha256,
                "body_sha256": body_sha256,
                "rig_signature": rig_signature,
                "maturity_class": maturity_class,
            },
            "checks": {
                "glb_structure": "passed",
                "body_fit": "passed",
                "rig_compatibility": "passed",
                "skinning": "passed",
                "sleeve_openings": "passed",
                "collision": "passed",
            },
        }

    def _approval_payload(
        self,
        *,
        asset_sha256: str,
        body_sha256: str,
        rig_signature: str,
        evidence_sha256: str,
        maturity_class: str = "adult",
    ) -> dict:
        return {
            "schema_version": 1,
            "artifact_type": "wardrobe_runtime_activation_approval",
            "status": "approved",
            "decision": "approve",
            "approval_scope": "exact_wardrobe_runtime_activation",
            "reviewer": {"kind": "human", "id": "robert"},
            "independent_from_builder_declaration": True,
            "bindings": {
                "asset_sha256": asset_sha256,
                "body_sha256": body_sha256,
                "rig_signature": rig_signature,
                "maturity_class": maturity_class,
            },
            "evidence_artifact_sha256": evidence_sha256,
        }

    def _approval_registry_payload(
        self,
        *,
        approval_sha256: str,
        asset_sha256: str,
        body_sha256: str,
        rig_signature: str,
        maturity_class: str = "adult",
    ) -> dict:
        return {
            "schema_version": 1,
            "registry_type": "owner_controlled_wardrobe_runtime_approval_registry",
            "owner": "Robert",
            "status": "active_fail_closed",
            "entries": [
                {
                    "approval_id": "owner_approved_test_entry",
                    "status": "active",
                    "owner_approved": True,
                    "approved_by": "Robert",
                    "approved_at": "2026-07-15T20:00:00-04:00",
                    "approval_artifact_sha256": approval_sha256,
                    "asset_sha256": asset_sha256,
                    "body_sha256": body_sha256,
                    "rig_signature": rig_signature,
                    "maturity_class": maturity_class,
                }
            ],
            "policy": {
                "default": "deny",
                "sidecar_claims_are_proof": False,
                "caller_supplied_hashes_are_trust_anchors": False,
                "exact_approval_hash_must_be_listed": True,
                "registry_file_integrity_must_match_pinned_code_hash": True,
                "current_runtime_wearables_approved": 1,
            },
        }

    def test_asset_library_classifies_and_copies_builder_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            library = root / "library"
            self._fake_model(source / "short_hair_cut_in_layers_with_bones.glb")
            self._fake_model(source / "female_anatomy_study_progress_2.glb")
            self._fake_model(source / "hand_animation_test.glb")
            self._fake_model(source / "school_shoes.glb")
            self._fake_model(source / "gameready_human_mouth_and_tongue.glb")
            self._fake_model(source / "realistic_woman_walking_animated.glb")

            manifest = build_avatar_asset_library(
                source_roots=[source],
                library_root=library,
            )

            self.assertEqual(manifest["asset_count"], 6)
            self.assertEqual(manifest["categories"]["hair_reference"], 1)
            self.assertEqual(manifest["categories"]["adult_anatomy_reference"], 1)
            self.assertEqual(manifest["categories"]["motion_reference"], 2)
            self.assertEqual(manifest["categories"]["shoe_reference"], 1)
            self.assertEqual(manifest["categories"]["face_mouth_reference"], 1)
            anatomy = [
                record
                for record in manifest["records"]
                if record["category"] == "adult_anatomy_reference"
            ][0]
            self.assertTrue(anatomy["adult_only"])
            self.assertFalse(anatomy["allowed_for_non_adult"])
            for record in manifest["records"]:
                self.assertTrue((PROJECT_ROOT / record["local_file"]).exists() or (library / record["local_file"]).exists())

    def test_asset_library_reindexes_existing_copied_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            library = Path(temp_dir) / "library"
            self._fake_model(library / "hair_reference" / "beautiful_hair_1_6e5776fa64.glb")
            self._fake_model(library / "adult_anatomy_reference" / "male_nude_2_a30390340f.glb")

            manifest = build_avatar_asset_library(
                source_roots=[],
                library_root=library,
                copy_assets=False,
            )

            self.assertEqual(manifest["asset_count"], 2)
            self.assertEqual(manifest["categories"]["hair_reference"], 1)
            self.assertEqual(manifest["categories"]["adult_anatomy_reference"], 1)
            anatomy = [
                record
                for record in manifest["records"]
                if record["category"] == "adult_anatomy_reference"
            ][0]
            self.assertTrue(anatomy["adult_only"])
            self.assertTrue(anatomy["local_file"].endswith("male_nude_2_a30390340f.glb"))

    def test_womenfemale_base_is_adult_only_even_when_compound_name_is_one_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            library = Path(temp_dir) / "library"
            self._fake_model(
                library
                / "base_body_reference"
                / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
            )
            manifest = build_avatar_asset_library(
                source_roots=[],
                library_root=library,
                copy_assets=False,
            )
            record = manifest["records"][0]
            self.assertTrue(record["adult_only"])
            self.assertFalse(record["allowed_for_non_adult"])

    def test_learning_plans_include_skin_body_hair_shoe_and_age_policy(self) -> None:
        manifest = {
            "records": [
                {"id": "shoe_reference:school_shoes:abc", "category": "shoe_reference", "filename": "school_shoes.glb", "local_file": "Avatar/avatar_builder/asset_library/shoe_reference/school_shoes.glb"},
                {"id": "hair_reference:short:abc", "category": "hair_reference", "filename": "short_hair.glb", "local_file": "Avatar/avatar_builder/asset_library/hair_reference/short_hair.glb"},
                {"id": "base_body_reference:base:abc", "category": "base_body_reference", "filename": "base_female.glb", "local_file": "Avatar/avatar_builder/asset_library/base_body_reference/base_female.glb"},
                {"id": "adult_anatomy_reference:adult:abc", "category": "adult_anatomy_reference", "filename": "adult_reference.glb", "local_file": "Avatar/avatar_builder/asset_library/adult_anatomy_reference/adult_reference.glb", "adult_only": True},
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            written = write_avatar_builder_learning_plans(manifest, builder_root=Path(temp_dir))

            self.assertIn("hair_generation_curriculum", written)
            self.assertIn("body_generation_curriculum", written)
            self.assertIn("adult_face_body_trials", written)
            self.assertIn("shoe_generation_curriculum", written)
            self.assertIn("skin_tone_templates", written)
            self.assertIn("spa_age_up_policy", written)
            skin = json.loads(Path(written["skin_tone_templates"]).read_text(encoding="utf-8"))
            spa = json.loads(Path(written["spa_age_up_policy"]).read_text(encoding="utf-8"))
            spa_first_hash = hashlib.sha256(
                Path(written["spa_age_up_policy"]).read_bytes()
            ).hexdigest()
            written_again = write_avatar_builder_learning_plans(
                manifest, builder_root=Path(temp_dir)
            )
            spa_second_hash = hashlib.sha256(
                Path(written_again["spa_age_up_policy"]).read_bytes()
            ).hexdigest()
            self.assertEqual(spa_first_hash, spa_second_hash)
        self.assertEqual(skin["kira_current_assignment"]["template_id"], "caucasian_light_neutral_adult")
        self.assertFalse(
            spa["curriculum_assignment"][
                "spa_completion_alone_unlocks_complete_adult_curriculum"
            ]
        )
        self.assertTrue(
            spa["curriculum_assignment"][
                "resulting_variant_requires_separate_exact_confirmed_adult_classification"
            ]
        )
        self.assertEqual(
            spa["curriculum_assignment"]["on_confirmed_adult_classification"],
            "ASSIGN_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM_IMMEDIATELY",
        )
        self.assertFalse(
            spa["curriculum_assignment"][
                "assignment_depends_on_relationship_interest_anatomy_or_experience"
            ]
        )
        self.assertFalse(
            spa["curriculum_assignment"][
                "classification_or_curriculum_automatically_adds_adult_anatomy"
            ]
        )
        self.assertEqual(
            spa["curriculum_assignment"][
                "non_adult_or_unresolved_body_representation"
            ],
            "doll_safe_non_anatomical",
        )
        self.assertTrue(
            spa["curriculum_assignment"][
                "guaranteed_minimum_is_not_an_exhaustive_ceiling"
            ]
        )
        self.assertFalse(
            spa["curriculum_assignment"][
                "adult_curriculum_modules_inherited_by_non_adult_or_unresolved"
            ]
        )

    def test_adult_face_body_trials_keep_hair_and_current_avatars_out(self) -> None:
        manifest = {
            "records": [
                {"id": "base_body_reference:male:abc", "category": "base_body_reference", "filename": "male_base.glb", "local_file": "Avatar/avatar_builder/asset_library/base_body_reference/male_base.glb"},
                {"id": "adult_anatomy_reference:male:abc", "category": "adult_anatomy_reference", "filename": "male_anatomy.glb", "local_file": "Avatar/avatar_builder/asset_library/adult_anatomy_reference/male_anatomy.glb", "adult_only": True},
                {"id": "eye_reference:human_eye:abc", "category": "eye_reference", "filename": "human_eye.glb", "local_file": "Avatar/avatar_builder/asset_library/eye_reference/human_eye.glb"},
            ]
        }

        plan = build_adult_face_body_trials(manifest)

        self.assertTrue(plan["no_hair_until_later"])
        trial_ids = {trial["id"] for trial in plan["trials"]}
        self.assertIn("peter_parker_tom_holland_adult_face_body_no_hair_v1", trial_ids)
        self.assertIn("gwen_stacy_earth65_adult_face_body_no_hair_v1", trial_ids)
        for trial in plan["trials"]:
            self.assertIn("hair", trial["source_policy"])
            self.assertIn("excluded", trial["source_policy"]["hair"])
            self.assertTrue(any("overwriting" in item for item in trial["reject_conditions"]))
        robert = next(trial for trial in plan["trials"] if trial["target_type"] == "user")
        self.assertFalse(robert["source_policy"]["may_be_used_for_other_avatars"])

    def test_age_up_label_is_unresolved_until_exact_classification_and_choice(self) -> None:
        normal = infer_avatar_maturity_policy(
            "ladybug_marinette_expanded_smoke",
            {"display_name": "Marinette Dupain-Cheng", "role_title": "student"},
        )
        self.assertEqual(normal["maturity_class"], "non_adult_doll_safe")
        self.assertFalse(normal["anatomy_allowed"])

        aged_up = infer_avatar_maturity_policy(
            "ladybug_marinette_aged_up_variant",
            {
                "display_name": "Adult Marinette",
                "metadata": {"age_up_variant": True},
            },
        )
        self.assertEqual(
            aged_up["maturity_class"], "uncertain_non_adult_safe_default"
        )
        self.assertEqual(
            aged_up["presentation_variant_label"], "adult_aged_up_variant"
        )
        self.assertEqual(aged_up["exact_maturity_status"], "unresolved")
        self.assertFalse(aged_up["anatomy_allowed"])
        self.assertTrue(aged_up["doll_safe_body_allowed"])

        source_text = "Robert confirms this exact separate variant is an adult."
        evidence = {
            "classification_id": "adult-classification-001",
            "subject_id": "ladybug_marinette_aged_up_variant",
            "maturity_status": "confirmed_adult",
            "authority": "Robert_explicit_owner_confirmation",
            "offline_confirmation_allowed": True,
            "network_lookup_required": False,
            "recorded_at_utc": "2026-08-03T12:00:00Z",
            "source_text": source_text,
            "source_text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        }
        confirmed_without_choice = infer_avatar_maturity_policy(
            "ladybug_marinette_aged_up_variant",
            {
                "candidate_id": "ladybug_marinette_aged_up_variant",
                "metadata": {"age_up_variant": True},
                "age_review": {
                    "maturity_class_override": "adult",
                    "confirmed_adult_classification_evidence": evidence,
                },
            },
        )
        self.assertEqual(
            confirmed_without_choice["exact_maturity_status"], "confirmed_adult"
        )
        self.assertEqual(
            confirmed_without_choice["presentation_variant_label"],
            "adult_aged_up_variant",
        )
        self.assertFalse(confirmed_without_choice["anatomy_allowed"])
        self.assertTrue(confirmed_without_choice["doll_safe_body_allowed"])

        confirmed_with_choice = infer_avatar_maturity_policy(
            "ladybug_marinette_aged_up_variant",
            {
                "candidate_id": "ladybug_marinette_aged_up_variant",
                "metadata": {"age_up_variant": True},
                "age_review": {
                    "maturity_class_override": "adult",
                    "confirmed_adult_classification_evidence": evidence,
                    "resident_adult_anatomy_choice_recorded": True,
                },
            },
        )
        self.assertTrue(confirmed_with_choice["anatomy_allowed"])

    def test_kira_is_adult_for_anatomy_policy(self) -> None:
        policy = infer_avatar_maturity_policy("kira", {"display_name": "Kira"})
        self.assertEqual(policy["maturity_class"], "adult")
        self.assertTrue(policy["adult_anatomy_assets_allowed"])

    def test_canonical_adult_names_do_not_upgrade_non_adult_alias_ids(self) -> None:
        for candidate_id in ("minor_gwen", "child_kira", "teen_peter"):
            with self.subTest(candidate_id=candidate_id):
                policy = infer_avatar_maturity_policy(
                    candidate_id,
                    {"candidate_id": candidate_id, "display_name": candidate_id},
                )
                self.assertEqual(policy["maturity_class"], "non_adult_doll_safe")
                validation = validate_candidate_maturity_identity(candidate_id, {"candidate_id": candidate_id})
                self.assertEqual(validation["status"], "passed")

        canonical_gwen = infer_avatar_maturity_policy(
            "spider_gwen_spider_gwen_20260606_013325",
            {"candidate_id": "spider_gwen_spider_gwen_20260606_013325"},
        )
        self.assertEqual(canonical_gwen["maturity_class"], "adult")

    def test_maturity_override_from_builder_policy(self) -> None:
        policy = infer_avatar_maturity_policy(
            "peter_parker_spider_man_no_way_home_final_suit",
            {
                "display_name": "Peter Parker",
                "age_review": {
                    "maturity_class_override": "adult",
                    "reason": "Robert selected Peter as an adult avatar-builder test pick.",
                },
            },
        )
        self.assertEqual(policy["maturity_class"], "adult")
        self.assertTrue(policy["adult_anatomy_assets_allowed"])

    def test_only_non_adults_get_doll_safe_body_policy(self) -> None:
        generic_adult_words = infer_avatar_maturity_policy(
            "adult_college_student",
            {
                "display_name": "Adult College Student",
                "metadata": {"note": "adult policy test and adult anatomy reference"},
            },
        )
        self.assertEqual(
            generic_adult_words["maturity_class"],
            "uncertain_non_adult_safe_default",
        )
        self.assertTrue(generic_adult_words["doll_safe_body_allowed"])
        self.assertFalse(generic_adult_words["adult_anatomy_assets_allowed"])

        for candidate_id in ("akira_child", "elisa_child"):
            policy = infer_avatar_maturity_policy(candidate_id, {"display_name": candidate_id})
            self.assertEqual(policy["maturity_class"], "non_adult_doll_safe")
            self.assertTrue(policy["doll_safe_body_allowed"])
            self.assertFalse(policy["adult_anatomy_assets_allowed"])

        aged_up = infer_avatar_maturity_policy(
            "marinette_aged_up_variant",
            {"display_name": "Marinette aged-up variant"},
        )
        self.assertEqual(
            aged_up["maturity_class"], "uncertain_non_adult_safe_default"
        )
        self.assertEqual(
            aged_up["presentation_variant_label"], "adult_aged_up_variant"
        )
        self.assertTrue(aged_up["doll_safe_body_allowed"])
        self.assertFalse(aged_up["adult_anatomy_assets_allowed"])

    def test_exact_adult_classification_rejects_tamper_wrong_subject_and_replay(self) -> None:
        source_text = "No, this exact version is an adult."
        evidence = {
            "classification_id": "classification-exact-001",
            "subject_id": "exact_variant_a",
            "maturity_status": "confirmed_adult",
            "authority": "Robert_explicit_owner_confirmation",
            "offline_confirmation_allowed": True,
            "network_lookup_required": False,
            "recorded_at_utc": "2026-08-03T12:00:00Z",
            "source_text": source_text,
            "source_text_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        }

        def policy(subject: str, exact: dict) -> dict:
            return infer_avatar_maturity_policy(
                subject,
                {
                    "candidate_id": subject,
                    "age_review": {
                        "maturity_class_override": "adult",
                        "confirmed_adult_classification_evidence": exact,
                    },
                },
            )

        self.assertEqual(policy("exact_variant_a", evidence)["exact_maturity_status"], "confirmed_adult")
        tampered_text = dict(evidence, source_text=source_text + " changed")
        self.assertEqual(policy("exact_variant_a", tampered_text)["exact_maturity_status"], "unresolved")
        tampered_hash = dict(evidence, source_text_sha256="f" * 64)
        self.assertEqual(policy("exact_variant_a", tampered_hash)["exact_maturity_status"], "unresolved")
        wrong_subject = dict(evidence, subject_id="someone_else")
        self.assertEqual(policy("exact_variant_a", wrong_subject)["exact_maturity_status"], "unresolved")
        self.assertEqual(policy("exact_variant_b", evidence)["exact_maturity_status"], "unresolved")

    def test_body_policy_validator_rejects_cross_age_treatments_and_assets(self) -> None:
        adult = infer_avatar_maturity_policy("kira", {"display_name": "Kira"})
        adult_gate = validate_avatar_body_policy(adult, body_treatment="non_adult_doll_safe")
        self.assertEqual(adult_gate["status"], "failed")
        self.assertIn(
            "adult_candidate_cannot_use_non_adult_doll_safe_body_treatment",
            adult_gate["failures"],
        )

        non_adult = infer_avatar_maturity_policy(
            "test_child",
            {"display_name": "Test Child"},
        )
        non_adult_gate = validate_avatar_body_policy(
            non_adult,
            body_treatment="neutral_adult_anatomy",
            selected_assets=[{"id": "beth_adult_reference", "adult_only": True}],
        )
        self.assertEqual(non_adult_gate["status"], "failed")
        self.assertEqual(non_adult_gate["blocked_assets"], ["beth_adult_reference"])

        adult_rig_gate = validate_avatar_body_policy(
            non_adult,
            body_treatment="adult_female_rig",
            selected_assets=[
                {
                    "id": "womenfemale_adult_base",
                    "adult_only": False,
                    "allowed_for_non_adult": False,
                }
            ],
        )
        self.assertEqual(adult_rig_gate["status"], "failed")
        self.assertIn(
            "non_adult_or_uncertain_candidate_cannot_use_adult_anatomy_body_treatment",
            adult_rig_gate["failures"],
        )
        self.assertEqual(adult_rig_gate["blocked_assets"], ["womenfemale_adult_base"])

    def test_folder9_models_classify_by_whole_asset_not_embedded_hand_bones(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            beth = root / "beth_smith_nsfw_rick__morty.glb"
            elsa = root / "elsa_frozen_adventures.glb"
            vincent = root / "vincent_van_gogh_ia.glb"
            for path in (beth, elsa, vincent):
                self._fake_model(path)

            beth_policy = classify_avatar_asset(beth)
            elsa_policy = classify_avatar_asset(elsa)
            vincent_policy = classify_avatar_asset(vincent)
            self.assertIsNotNone(beth_policy)
            self.assertEqual(beth_policy["category"], "adult_anatomy_reference")
            self.assertTrue(beth_policy["adult_only"])
            self.assertEqual(elsa_policy["category"], "character_reference")
            self.assertTrue(elsa_policy["adult_only"])
            self.assertFalse(elsa_policy["allowed_for_non_adult"])
            self.assertEqual(vincent_policy["category"], "character_reference")
            self.assertTrue(vincent_policy["adult_only"])

    def test_both_supported_elsa_movie_versions_are_exact_adult_identities(self) -> None:
        for candidate_id, expected_age in (
            ("elsa_frozen_2013", 21),
            ("elsa_frozen_ii_2019", 24),
        ):
            with self.subTest(candidate_id=candidate_id):
                policy = infer_avatar_maturity_policy(
                    candidate_id,
                    {
                        "candidate_id": candidate_id,
                        "display_name": "Elsa",
                        "metadata": {"canon_age": expected_age},
                    },
                )
                self.assertEqual(policy["maturity_class"], "adult")
                self.assertTrue(policy["adult_anatomy_assets_allowed"])
                self.assertFalse(policy["doll_safe_body_allowed"])

        child_alias = infer_avatar_maturity_policy(
            "child_elsa_frozen_2013",
            {"display_name": "Child Elsa"},
        )
        self.assertEqual(child_alias["maturity_class"], "non_adult_doll_safe")

    def test_sarah_michelle_gellar_model_is_adult_reference_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = Path(temp_dir) / "sarah_michelle_geller.glb"
            self._fake_model(model)
            policy = classify_avatar_asset(model)
            self.assertEqual(policy["category"], "character_reference")
            self.assertTrue(policy["adult_only"])
            self.assertFalse(policy["allowed_for_non_adult"])

    def test_embedded_confirmed_adult_character_identity_is_adult_only(self) -> None:
        for embedded_name in (
            "Elsa Frozen",
            "Sarah Michelle Gellar",
            "Vincent van Gogh",
        ):
            with self.subTest(embedded_name=embedded_name), tempfile.TemporaryDirectory() as temp_dir:
                model = Path(temp_dir) / "generic_character_model.glb"
                self._fake_glb_with_node_name(model, embedded_name)
                policy = classify_avatar_asset(model)
                self.assertEqual(policy["category"], "character_reference")
                self.assertTrue(policy["adult_only"])
                self.assertFalse(policy["allowed_for_non_adult"])

    def test_single_model_file_can_be_intaken_without_scanning_its_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "beth_smith_nsfw_rick__morty.glb"
            library = root / "library"
            self._fake_model(source)
            manifest = build_avatar_asset_library(source_roots=[source], library_root=library)
            self.assertEqual(manifest["asset_count"], 1)
            self.assertEqual(manifest["categories"], {"adult_anatomy_reference": 1})
            self.assertTrue(Path(manifest["records"][0]["source_file"]).samefile(source))

    def test_wardrobe_intake_keeps_construction_world_and_wearable_forms_separate(self) -> None:
        expected = {
            "terry_cloth_fabric.glb": "fabric_reference",
            "bathrobe_garment.glb": "garment_reference",
            "robe_sewing_pattern.glb": "sewing_pattern_reference",
            "folded_robe_world_form.glb": "world_form_reference",
            "kira_robe_wearable.glb": "wearable_reference",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for filename, category in expected.items():
                with self.subTest(filename=filename):
                    model = root / filename
                    self._fake_model(model)
                    policy = classify_avatar_asset(model)
                    self.assertEqual(policy["category"], category)
                    self.assertEqual(policy["asset_domain"], "wardrobe")
                    self.assertTrue(
                        policy["maturity_compatibility"]["must_not_change_subject_maturity"]
                    )
                    self.assertIn("required_body_sha256", policy["body_compatibility"])
                    self.assertIn("required_rig_signature", policy["rig_compatibility"])
                    self.assertFalse(policy["runtime_activation_allowed"])

    def test_wardrobe_manifest_records_hash_bound_provenance_and_sidecar_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            library = root / "library"
            robe = source / "robe_wearable.glb"
            self._fake_model(robe)
            body_hash = "a" * 64
            sidecar = robe.with_suffix(".avatar.json")
            sidecar.write_text(
                json.dumps(
                    {
                        "maturity_scope": "adult_only",
                        "required_body_id": "kira_current_body",
                        "required_body_sha256": body_hash,
                        "required_rig_signature": "foundation_skeleton_v1:abc123",
                        "skinning_status": "skinned",
                        "fit_evidence_status": "passed",
                        "rig_evidence_status": "passed",
                        "approval_status": "approved",
                        "approval_artifact_sha256": "f" * 64,
                        "runtime_activation_allowed": True,
                        "creator": "local supervised builder",
                        "license": "private_reference",
                    }
                ),
                encoding="utf-8",
            )

            manifest = build_avatar_asset_library(
                source_roots=[source],
                library_root=library,
            )

            self.assertEqual(manifest["schema_version"], 2)
            record = manifest["records"][0]
            self.assertEqual(record["category"], "wearable_reference")
            self.assertTrue(record["adult_only"])
            self.assertEqual(record["body_compatibility"]["required_body_sha256"], body_hash)
            self.assertEqual(
                record["rig_compatibility"]["required_rig_signature"],
                "foundation_skeleton_v1:abc123",
            )
            self.assertEqual(record["provenance"]["source_sha256"], record["sha256"])
            self.assertEqual(record["provenance"]["declared"]["license"], "private_reference")
            self.assertEqual(record["body_compatibility"]["fit_evidence_status"], "not_tested")
            self.assertEqual(record["rig_compatibility"]["skinning_status"], "unverified")
            self.assertIn("runtime_activation_allowed", record["ignored_untrusted_proof_claims"])
            self.assertNotIn("approval_artifact_sha256", record)

            staged = validate_wardrobe_asset_compatibility(
                record,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature="foundation_skeleton_v1:abc123",
            )
            self.assertEqual(staged["status"], "failed")
            self.assertFalse(staged["runtime_activation_allowed"])
            self.assertIn("invalid_glb_header", staged["compatibility_failures"])
            self.assertIn("evidence_artifact_missing", staged["evidence_failures"])
            self.assertIn("approval_artifact_missing", staged["approval_failures"])
            self.assertIn(
                "approval_artifact_hash_not_listed_in_owner_registry",
                staged["approval_failures"],
            )

    def test_wardrobe_runtime_gate_accepts_only_separate_bound_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            library = root / "library"
            robe = source / "robe_wearable.glb"
            self._skinned_wearable_glb(robe)
            body_hash = "a" * 64
            rig = "foundation_skeleton_v1:abc123"
            robe.with_suffix(".avatar.json").write_text(
                json.dumps(
                    {
                        "maturity_scope": "adult_only",
                        "required_body_sha256": body_hash,
                        "required_rig_signature": rig,
                    }
                ),
                encoding="utf-8",
            )
            record = build_avatar_asset_library(
                source_roots=[source],
                library_root=library,
            )["records"][0]
            evidence = root / "independent_evidence.json"
            evidence_hash = self._write_json(
                evidence,
                self._evidence_payload(
                    asset_sha256=record["sha256"],
                    body_sha256=body_hash,
                    rig_signature=rig,
                ),
            )
            approval = root / "human_approval.json"
            approval_hash = self._write_json(
                approval,
                self._approval_payload(
                    asset_sha256=record["sha256"],
                    body_sha256=body_hash,
                    rig_signature=rig,
                    evidence_sha256=evidence_hash,
                ),
            )

            untrusted_result = validate_wardrobe_asset_compatibility(
                record,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature=rig,
                evidence_artifact=evidence,
                approval_artifact=approval,
            )
            registry = root / "owner_registry.json"
            registry_hash = self._write_json(
                registry,
                self._approval_registry_payload(
                    approval_sha256=approval_hash,
                    asset_sha256=record["sha256"],
                    body_sha256=body_hash,
                    rig_signature=rig,
                ),
            )
            with patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PATH",
                registry,
            ), patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PINNED_SHA256",
                registry_hash,
            ):
                result = validate_wardrobe_asset_compatibility(
                    record,
                    maturity_class="adult",
                    body_sha256=body_hash,
                    rig_signature=rig,
                    evidence_artifact=evidence,
                    approval_artifact=approval,
                )
            registry.write_text(registry.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PATH",
                registry,
            ), patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PINNED_SHA256",
                registry_hash,
            ):
                tampered_registry_result = validate_wardrobe_asset_compatibility(
                    record,
                    maturity_class="adult",
                    body_sha256=body_hash,
                    rig_signature=rig,
                    evidence_artifact=evidence,
                    approval_artifact=approval,
                )

        self.assertFalse(untrusted_result["runtime_activation_allowed"])
        self.assertIn(
            "approval_artifact_hash_not_listed_in_owner_registry",
            untrusted_result["approval_failures"],
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["compatible_for_staged_testing"])
        self.assertTrue(result["runtime_activation_allowed"])
        self.assertEqual(result["glb_validation"]["status"], "passed")
        self.assertEqual(result["evidence_artifact"]["sha256"], evidence_hash)
        self.assertEqual(result["approval_artifact"]["sha256"], approval_hash)
        self.assertFalse(tampered_registry_result["runtime_activation_allowed"])
        self.assertIn(
            "owner_approval_registry_integrity_hash_mismatch",
            tampered_registry_result["approval_failures"],
        )

    def test_owner_approval_registry_defaults_empty_and_missing_registry_fails(self) -> None:
        default_registry = avatar_asset_library_module.load_wardrobe_approval_registry()
        self.assertEqual(default_registry["status"], "passed")
        self.assertEqual(default_registry["entries"], [])
        self.assertEqual(default_registry["sha256"], default_registry["pinned_sha256"])

        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing_registry.json"
            with patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PATH",
                missing,
            ), patch.object(
                avatar_asset_library_module,
                "WARDROBE_APPROVAL_REGISTRY_PINNED_SHA256",
                "0" * 64,
            ):
                missing_registry = avatar_asset_library_module.load_wardrobe_approval_registry()

        self.assertEqual(missing_registry["status"], "failed")
        self.assertIn("owner_approval_registry_missing", missing_registry["failures"])
        self.assertIn(
            "owner_approval_registry_integrity_hash_mismatch",
            missing_registry["failures"],
        )

    def test_fake_non_glb_cannot_be_approved_by_matching_self_authored_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            library = root / "library"
            robe = source / "adult_robe_wearable.glb"
            self._fake_model(robe)
            body_hash = "a" * 64
            rig = "foundation_skeleton_v1:abc123"
            robe.with_suffix(".avatar.json").write_text(
                json.dumps(
                    {
                        "required_body_sha256": body_hash,
                        "required_rig_signature": rig,
                        "fit_evidence_status": "passed",
                        "rig_evidence_status": "passed",
                        "skinning_status": "skinned",
                        "approval_status": "approved",
                        "approval_artifact_sha256": "1" * 64,
                    }
                ),
                encoding="utf-8",
            )
            record = build_avatar_asset_library(
                source_roots=[source],
                library_root=library,
            )["records"][0]
            evidence = root / "evidence.json"
            evidence_hash = self._write_json(
                evidence,
                self._evidence_payload(
                    asset_sha256=record["sha256"],
                    body_sha256=body_hash,
                    rig_signature=rig,
                ),
            )
            approval = root / "approval.json"
            approval_hash = self._write_json(
                approval,
                self._approval_payload(
                    asset_sha256=record["sha256"],
                    body_sha256=body_hash,
                    rig_signature=rig,
                    evidence_sha256=evidence_hash,
                ),
            )
            result = validate_wardrobe_asset_compatibility(
                record,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature=rig,
                evidence_artifact=evidence,
                approval_artifact=approval,
            )

        self.assertIn("invalid_glb_header", result["compatibility_failures"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_valid_glb_still_blocks_when_evidence_or_approval_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            robe = root / "adult_robe_wearable.glb"
            self._skinned_wearable_glb(robe)
            body_hash = "a" * 64
            rig = "foundation_skeleton_v1:abc123"
            policy = classify_avatar_asset(robe)
            policy["sha256"] = self._sha256(robe)
            policy["local_file"] = str(robe)
            policy["body_compatibility"]["required_body_sha256"] = body_hash
            policy["rig_compatibility"]["required_rig_signature"] = rig
            result = validate_wardrobe_asset_compatibility(
                policy,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature=rig,
            )

        self.assertTrue(result["compatible_for_staged_testing"])
        self.assertIn("evidence_artifact_missing", result["evidence_failures"])
        self.assertIn("approval_artifact_missing", result["approval_failures"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_tampered_evidence_breaks_approval_hash_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            robe = root / "adult_robe_wearable.glb"
            self._skinned_wearable_glb(robe)
            asset_hash = self._sha256(robe)
            body_hash = "a" * 64
            rig = "foundation_skeleton_v1:abc123"
            policy = classify_avatar_asset(robe)
            policy.update({"sha256": asset_hash, "local_file": str(robe)})
            policy["body_compatibility"]["required_body_sha256"] = body_hash
            policy["rig_compatibility"]["required_rig_signature"] = rig
            evidence = root / "evidence.json"
            original_evidence_hash = self._write_json(
                evidence,
                self._evidence_payload(
                    asset_sha256=asset_hash,
                    body_sha256=body_hash,
                    rig_signature=rig,
                ),
            )
            approval = root / "approval.json"
            approval_hash = self._write_json(
                approval,
                self._approval_payload(
                    asset_sha256=asset_hash,
                    body_sha256=body_hash,
                    rig_signature=rig,
                    evidence_sha256=original_evidence_hash,
                ),
            )
            tampered = self._evidence_payload(
                asset_sha256=asset_hash,
                body_sha256=body_hash,
                rig_signature=rig,
            )
            tampered["checks"]["collision"] = "failed"
            self._write_json(evidence, tampered)
            result = validate_wardrobe_asset_compatibility(
                policy,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature=rig,
                evidence_artifact=evidence,
                approval_artifact=approval,
            )

        self.assertIn("evidence_check_not_passed:collision", result["evidence_failures"])
        self.assertIn(
            "approval_evidence_artifact_hash_mismatch",
            result["approval_failures"],
        )
        self.assertFalse(result["runtime_activation_allowed"])

    def test_wrong_artifact_bindings_and_arbitrary_approval_hash_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            robe = root / "adult_robe_wearable.glb"
            self._skinned_wearable_glb(robe)
            asset_hash = self._sha256(robe)
            body_hash = "a" * 64
            rig = "foundation_skeleton_v1:abc123"
            policy = classify_avatar_asset(robe)
            policy.update({"sha256": asset_hash, "local_file": str(robe)})
            policy["body_compatibility"]["required_body_sha256"] = body_hash
            policy["rig_compatibility"]["required_rig_signature"] = rig
            evidence = root / "evidence.json"
            evidence_hash = self._write_json(
                evidence,
                self._evidence_payload(
                    asset_sha256=asset_hash,
                    body_sha256="b" * 64,
                    rig_signature=rig,
                ),
            )
            approval_payload = self._approval_payload(
                asset_sha256=asset_hash,
                body_sha256=body_hash,
                rig_signature="wrong-rig",
                evidence_sha256=evidence_hash,
            )
            approval = root / "approval.json"
            self._write_json(approval, approval_payload)
            result = validate_wardrobe_asset_compatibility(
                policy,
                maturity_class="adult",
                body_sha256=body_hash,
                rig_signature=rig,
                evidence_artifact=evidence,
                approval_artifact=approval,
            )

        self.assertIn("evidence_body_hash_mismatch", result["evidence_failures"])
        self.assertIn("approval_rig_signature_mismatch", result["approval_failures"])
        self.assertIn(
            "approval_artifact_hash_not_listed_in_owner_registry",
            result["approval_failures"],
        )
        self.assertFalse(result["runtime_activation_allowed"])

    def test_wardrobe_compatibility_fails_closed_on_body_rig_and_maturity(self) -> None:
        asset = classify_avatar_asset(Path("adult_robe_wearable.glb"))
        result = validate_wardrobe_asset_compatibility(
            asset,
            maturity_class="non_adult_doll_safe",
            body_sha256="b" * 64,
            rig_signature="different_rig",
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("maturity_class_not_allowed_for_garment", result["failures"])
        self.assertIn("exact_body_hash_not_declared", result["failures"])
        self.assertIn("rig_signature_not_declared", result["failures"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_hair_trials_grade_missing_traits_instead_of_auto_approving(self) -> None:
        manifest = {
            "records": [
                {
                    "id": "hair_reference:short_hair_cut_in_layers_with_bones:abc",
                    "category": "hair_reference",
                    "filename": "short_hair_cut_in_layers_with_bones.glb",
                    "local_file": "Avatar/avatar_builder/asset_library/hair_reference/short.glb",
                },
                {
                    "id": "hair_reference:long_reddish_hair_for_game:def",
                    "category": "hair_reference",
                    "filename": "long_reddish_hair_for_game.glb",
                    "local_file": "Avatar/avatar_builder/asset_library/hair_reference/red.glb",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_hair_style_trials(manifest, trial_root=Path(temp_dir))

        self.assertIn(report["trials"]["tom_holland_peter_parker"]["grade"], {"C", "D"})
        self.assertIn("twin_pigtails", report["trials"]["marinette_dupain_cheng"]["missing_required_traits"])
        self.assertNotIn(report["trials"]["marinette_dupain_cheng"]["grade"], {"A", "B"})


if __name__ == "__main__":
    unittest.main()
