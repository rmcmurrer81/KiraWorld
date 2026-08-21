from __future__ import annotations

import json
from pathlib import Path
import unittest

from Core.avatar_repository_media_boundary import (
    evaluate_repository_media_candidate,
    replacement_chart_is_machine_useful,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "Avatar/avatar_builder/policies/repository_real_person_media_boundary_v1.json"


def strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def candidate(**updates):
    value = {
        "content_class": "synthetic_avatar_geometry",
        "repository_path": "Avatar/review/synthetic_robert_body.glb",
        "repository_visibility": "private",
        "is_real_person_photograph": False,
        "contains_real_person_photograph_pixels": False,
        "source_photographs_included": False,
        "public_export": False,
        "synthetic_unclothed_body": True,
        "confirmed_adult": True,
        "target_id": "SYNTHETIC_ROBERT_TWIN_BODY",
        "synthetic_geometry": True,
    }
    value.update(updates)
    return value


class AvatarRepositoryMediaBoundaryTests(unittest.TestCase):
    def test_policy_is_strict_and_forbids_all_real_person_photos(self):
        policy = json.loads(
            POLICY.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        scope = policy["repository_scope"]
        self.assertIs(scope["real_person_photographs_allowed"], False)
        self.assertIs(scope["real_person_photo_derivatives_containing_source_pixels_allowed"], False)
        self.assertIs(scope["local_photo_deletion_authorized"], False)
        self.assertEqual(
            set(policy["synthetic_body_rule"]["robert_target_ids"]),
            {"BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"},
        )

    def test_real_photos_crops_annotations_contacts_and_textures_are_blocked(self):
        for content_class in (
            "real_person_photograph",
            "cropped_real_person_photograph",
            "annotated_real_person_photograph",
            "real_person_photograph_contact_sheet",
            "real_person_photograph_texture",
        ):
            result = evaluate_repository_media_candidate(
                candidate(
                    content_class=content_class,
                    repository_path="Avatar/library/reference.png",
                    is_real_person_photograph=True,
                    synthetic_unclothed_body=False,
                    confirmed_adult=False,
                    synthetic_geometry=False,
                )
            )
            self.assertFalse(result["allowed_for_private_repository"], content_class)

    def test_synthetic_adult_robert_body_geometry_is_allowed_privately(self):
        for target in ("BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"):
            result = evaluate_repository_media_candidate(candidate(target_id=target))
            self.assertTrue(result["allowed_for_private_repository"], result["failures"])
            self.assertIs(result["real_person_photographs_allowed"], False)

    def test_embedded_photo_public_or_nonadult_unclothed_body_is_blocked(self):
        attacks = (
            {"contains_real_person_photograph_pixels": True},
            {"source_photographs_included": True},
            {"repository_visibility": "public", "public_export": True},
            {"confirmed_adult": False},
            {"content_class": "synthetic_avatar_render", "repository_path": "render.png"},
        )
        for updates in attacks:
            result = evaluate_repository_media_candidate(candidate(**updates))
            self.assertFalse(result["allowed_for_private_repository"], updates)

    def test_neutral_chart_needs_every_machine_utility_receipt(self):
        proof = {
            "exact_chart_hash_verified": True,
            "machine_readable_selector_ids_verified": True,
            "avatar_builder_selection_receipt_verified": True,
            "synthetic_before_after_hashes_verified": True,
            "repeatable_change_verified": True,
            "visual_and_structural_review_passed": True,
            "photo_coverage_mapping_verified": True,
        }
        self.assertTrue(replacement_chart_is_machine_useful(proof))
        for field in tuple(proof):
            changed = dict(proof)
            changed[field] = False
            self.assertFalse(replacement_chart_is_machine_useful(changed), field)

    def test_policy_and_code_contain_no_local_task_surface(self):
        combined = POLICY.read_text(encoding="utf-8") + (ROOT / "Core/avatar_repository_media_boundary.py").read_text(encoding="utf-8")
        lowered = combined.lower()
        self.assertNotIn("codex", lowered)
        self.assertNotIn("handoff", lowered)
        self.assertNotIn("c:\\users\\", lowered)


if __name__ == "__main__":
    unittest.main()
