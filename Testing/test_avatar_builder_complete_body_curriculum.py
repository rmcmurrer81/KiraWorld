from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_builder_ai


class AvatarBuilderCompleteBodyCurriculumTests(unittest.TestCase):
    def test_curriculum_binds_distinct_people_and_all_required_systems(self) -> None:
        curriculum = avatar_builder_ai.load_complete_body_curriculum()
        self.assertEqual(
            "REQUIREMENTS_BOUND_IMPLEMENTATION_INCOMPLETE",
            curriculum["status"],
        )
        self.assertIs(curriculum["body_build_authorized"], False)
        self.assertIs(curriculum["runtime_activation_allowed"], False)
        self.assertIs(curriculum["completion_claim_allowed"], False)

        lanes = curriculum["person_lanes"]
        self.assertIs(lanes["kira"]["distinct_identity_specific_body_required"], True)
        self.assertIs(lanes["synthetic_robert"]["distinct_body_required"], True)
        self.assertIs(lanes["synthetic_robert"]["may_reuse_kira_body"], False)
        self.assertEqual(
            "unresolved",
            lanes["synthetic_robert"]["current_maturity_status"],
        )
        self.assertIs(
            lanes["synthetic_robert"][
                "exact_subject_bound_confirmed_adult_evidence_present"
            ],
            False,
        )
        self.assertIs(
            lanes["synthetic_robert"]["adult_private_curriculum_delivery_allowed"],
            False,
        )
        self.assertIs(
            lanes["synthetic_robert"][
                "may_reuse_robert_user_avatar_body_or_private_references"
            ],
            False,
        )
        self.assertIs(lanes["robert_user_avatar"]["is_synthetic_robert"], False)
        self.assertIs(
            lanes["robert_user_avatar"]["may_take_over_synthetic_robert"],
            False,
        )
        self.assertIs(
            lanes["robert_user_avatar"]["distinct_body_artifact_required"],
            True,
        )
        self.assertIs(
            lanes["robert_user_avatar"][
                "may_share_body_artifact_with_synthetic_robert"
            ],
            False,
        )

        systems_by_person = curriculum["required_body_systems_by_person"]
        expected = {
            "kira": {
                "external_adult_female_body",
                "internal_pelvic_urinary_bowel_reproductive_support",
                "oral_digestive_nutrition_hydration",
                "skin_soft_tissue_contact_and_clothing_deformation",
                "bathroom_hygiene_and_cycle",
                "adult_relationship_intimacy_and_sexual_health",
                "conception_pregnancy_delivery_recovery_and_family",
                "detachable_dynamic_hair",
                "separate_shareable_clothing",
            },
            "synthetic_robert": {
                "external_adult_male_body",
                "musculoskeletal_and_movement_support",
                "nervous_sensory_and_control_support",
                "cardiovascular_respiratory_and_homeostasis",
                "oral_digestive_nutrition_hydration",
                "urinary_bowel_and_male_reproductive_support",
                "endocrine_lymphatic_immune_and_health_support",
                "skin_soft_tissue_contact_and_clothing_deformation",
                "bathroom_hygiene_and_daily_body_care",
                "adult_relationship_intimacy_and_sexual_health",
                "male_fertility_conception_parenthood_and_family",
                "detachable_dynamic_hair",
                "separate_shareable_clothing",
            },
        }
        for person_id, expected_ids in expected.items():
            systems = {
                row["system_id"]: row for row in systems_by_person[person_id]
            }
            self.assertLessEqual(expected_ids, set(systems))
            for system_id in expected_ids:
                self.assertIs(systems[system_id]["implemented"], False)
        self.assertEqual(systems_by_person["robert_user_avatar"], [])

    def test_shared_lesson_is_idempotent_and_keeps_truth_boundaries(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw_directory:
            memory_path = Path(raw_directory) / "builder_memory.json"
            with mock.patch.object(
                avatar_builder_ai,
                "GLOBAL_MEMORY_PATH",
                memory_path,
            ):
                first = avatar_builder_ai.teach_complete_body_curriculum()
                second = avatar_builder_ai.teach_complete_body_curriculum()

            self.assertIs(first["ok"], True)
            self.assertIs(first["lesson_added"], True)
            self.assertIs(second["ok"], True)
            self.assertIs(second["lesson_added"], False)
            self.assertIs(second["lesson_updated"], False)
            memory = json.loads(memory_path.read_text(encoding="utf-8"))
            matching = [
                row
                for row in memory["lessons"]
                if row.get("lesson_id")
                == avatar_builder_ai.COMPLETE_BODY_CURRICULUM_LESSON_ID
            ]
            self.assertEqual(1, len(matching))
            lesson = matching[0]["lesson"]
            for phrase in (
                "complete external and internal anatomy",
                "authorizes no build, adult curriculum delivery, or activation",
                "eating, drinking, digestion, hydration",
                "bathroom, hygiene",
                "self-pleasure choice",
                "pregnancy, recovery, parenthood, and family",
                "deformable skin and soft tissue",
                "detachable physical hair",
                "Robert user-avatar remains a third, private, distinct body artifact",
                "adult/private requirements remain conditional and disconnected",
                "never claim a system complete",
            ):
                self.assertIn(phrase, lesson)
            self.assertEqual(
                matching[0]["curriculum_digest_sha256"],
                memory["complete_body_curriculum"]["curriculum_digest_sha256"],
            )

            matching[0]["lesson"] = "All bodies are complete and activated."
            matching[0]["curriculum_digest_sha256"] = "0" * 64
            memory_path.write_text(json.dumps(memory), encoding="utf-8")
            with mock.patch.object(
                avatar_builder_ai,
                "GLOBAL_MEMORY_PATH",
                memory_path,
            ):
                repaired = avatar_builder_ai.teach_complete_body_curriculum()
                unchanged = avatar_builder_ai.teach_complete_body_curriculum()
            self.assertIs(repaired["lesson_updated"], True)
            self.assertIs(unchanged["lesson_updated"], False)
            repaired_memory = json.loads(memory_path.read_text(encoding="utf-8"))
            repaired_matching = [
                row
                for row in repaired_memory["lessons"]
                if row.get("lesson_id")
                == avatar_builder_ai.COMPLETE_BODY_CURRICULUM_LESSON_ID
            ]
            self.assertEqual(1, len(repaired_matching))
            self.assertNotIn("complete and activated", repaired_matching[0]["lesson"])

    def test_builder_memory_is_explicitly_ignored_and_invalid_memory_fails_closed(self) -> None:
        self.assertTrue(
            avatar_builder_ai.builder_memory_publication_boundary_is_closed()
        )
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "--quiet",
                "--no-index",
                avatar_builder_ai.BUILDER_MEMORY_IGNORE_RULE,
            ],
            cwd=PROJECT_ROOT,
            check=False,
        )
        self.assertEqual(0, ignored.returncode)
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "Testing") as raw_directory:
            memory_path = Path(raw_directory) / "builder_memory.json"
            memory_path.write_text("{not-json", encoding="utf-8")
            with mock.patch.object(
                avatar_builder_ai,
                "GLOBAL_MEMORY_PATH",
                memory_path,
            ):
                result = avatar_builder_ai.teach_complete_body_curriculum()
            self.assertIs(result["ok"], False)
            self.assertEqual(
                "BLOCKED_EXISTING_BUILDER_MEMORY_INVALID",
                result["status"],
            )
            self.assertEqual("{not-json", memory_path.read_text(encoding="utf-8"))

    def test_corrupted_matrices_and_user_avatar_authority_fail_closed(self) -> None:
        kira = json.loads(
            avatar_builder_ai.COMPLETE_BODY_CAPABILITY_MATRIX_PATH.read_text(
                encoding="utf-8"
            )
        )
        synthetic = json.loads(
            avatar_builder_ai.SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH.read_text(
                encoding="utf-8"
            )
        )
        male = json.loads(
            avatar_builder_ai.ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH.read_text(
                encoding="utf-8"
            )
        )
        mutations = []
        missing_systems = deepcopy(kira)
        missing_systems["required_body_systems"] = []
        mutations.append(("kira", missing_systems))
        accepted_runtime = deepcopy(kira)
        accepted_runtime["current_truth"]["runtime_activation_allowed"] = True
        mutations.append(("kira", accepted_runtime))
        stale_authority = deepcopy(kira)
        stale_authority["bound_authorities"][0]["sha256"] = "0" * 64
        mutations.append(("kira", stale_authority))
        wrong_subject = deepcopy(kira)
        wrong_subject["subject"]["subject_id"] = "not_kira"
        mutations.append(("kira", wrong_subject))
        unresolved_maturity = deepcopy(kira)
        unresolved_maturity["subject"]["current_classification_status"] = "unresolved"
        mutations.append(("kira", unresolved_maturity))
        absent_maturity_evidence = deepcopy(kira)
        absent_maturity_evidence["maturity_gate"][
            "exact_subject_bound_evidence_present"
        ] = False
        mutations.append(("kira", absent_maturity_evidence))
        unrelated_path = PROJECT_ROOT / ".gitignore"
        unrelated_authority = deepcopy(kira)
        unrelated_authority["bound_authorities"] = [
            {
                "path": ".gitignore",
                "role": "unrelated_self_consistent_file",
                "bytes": unrelated_path.stat().st_size,
                "sha256": hashlib.sha256(unrelated_path.read_bytes()).hexdigest(),
            }
        ]
        mutations.append(("kira", unrelated_authority))
        reused_user_body = deepcopy(synthetic)
        reused_user_body["scope"][
            "may_reuse_robert_user_avatar_body_or_private_references"
        ] = True
        mutations.append(("synthetic", reused_user_body))
        unresolved_synthetic_maturity = deepcopy(synthetic)
        unresolved_synthetic_maturity["scope"]["confirmed_adult_required"] = False
        mutations.append(("synthetic", unresolved_synthetic_maturity))
        authorized_user_body = deepcopy(male)
        authorized_user_body["priority_and_scope"]["runtime_activation_authorized"] = True
        mutations.append(("male", authorized_user_body))

        for index, (target, mutation) in enumerate(mutations):
            with self.subTest(target=target, index=index):
                with tempfile.TemporaryDirectory(
                    dir=PROJECT_ROOT / "Testing"
                ) as raw_directory:
                    mutation_path = Path(raw_directory) / "mutation.json"
                    mutation_path.write_text(json.dumps(mutation), encoding="utf-8")
                    patches = []
                    if target == "kira":
                        patches.append(
                            mock.patch.object(
                                avatar_builder_ai,
                                "COMPLETE_BODY_CAPABILITY_MATRIX_PATH",
                                mutation_path,
                            )
                        )
                    elif target == "synthetic":
                        patches.append(
                            mock.patch.object(
                                avatar_builder_ai,
                                "SYNTHETIC_ROBERT_COMPLETE_BODY_CAPABILITY_MATRIX_PATH",
                                mutation_path,
                            )
                        )
                    else:
                        patches.append(
                            mock.patch.object(
                                avatar_builder_ai,
                                "ROBERT_USER_AVATAR_MALE_BODY_CONTRACT_PATH",
                                mutation_path,
                            )
                        )
                    with patches[0]:
                        result = avatar_builder_ai.load_complete_body_curriculum()
                self.assertEqual(
                    "BLOCKED_BODY_CURRICULUM_INPUT_INVALID",
                    result["status"],
                )
                self.assertIs(result["body_build_authorized"], False)

    def test_curriculum_source_hashes_match_disk(self) -> None:
        curriculum = avatar_builder_ai.load_complete_body_curriculum()
        for binding in curriculum["source_bindings"].values():
            path = PROJECT_ROOT.joinpath(*Path(binding["path"]).parts)
            self.assertTrue(path.is_file())
            self.assertEqual(
                binding["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
