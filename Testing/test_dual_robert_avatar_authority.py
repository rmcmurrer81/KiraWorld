import unittest

from Core.dual_robert_avatar_authority import (
    evaluate_dual_robert_construction_request,
    final_assets_are_separate,
)


def allowed(target):
    return {
        "target_id": target,
        "confirmed_adult": True,
        "private_reference_access": True,
        "ordinary_review_route": "clothed_only",
        "copy_private_sources": False,
        "public_export": False,
        "runtime_activation": False,
        "use_other_person_identity_surface": False,
    }


class DualRobertAuthorityTests(unittest.TestCase):
    def test_exact_two_targets_are_authorized(self):
        for target in ("BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"):
            self.assertTrue(
                evaluate_dual_robert_construction_request(allowed(target))[
                    "authorized_for_private_construction"
                ]
            )

    def test_kira_and_unrelated_people_are_blocked(self):
        for target in ("kira", "lisa", "temporary_person", ""):
            self.assertFalse(
                evaluate_dual_robert_construction_request(allowed(target))[
                    "authorized_for_private_construction"
                ]
            )

    def test_public_activation_and_source_copy_fail_closed(self):
        request = allowed("BIOLOGICAL_ROBERT_AVATAR")
        request.update(public_export=True, runtime_activation=True, copy_private_sources=True)
        result = evaluate_dual_robert_construction_request(request)
        self.assertFalse(result["authorized_for_private_construction"])
        self.assertEqual(len(result["failures"]), 3)

    def test_final_mutable_assets_must_differ(self):
        common = {
            "body_path": "same.glb",
            "body_sha256": "a" * 64,
            "component_manifest_path": "same-components.json",
            "rig_manifest_path": "same-rig.json",
        }
        result = final_assets_are_separate(
            {"target_id": "BIOLOGICAL_ROBERT_AVATAR", **common},
            {"target_id": "SYNTHETIC_ROBERT_TWIN_BODY", **common},
        )
        self.assertFalse(result["separate_final_assets"])
        self.assertEqual(len(result["failures"]), 4)


if __name__ == "__main__":
    unittest.main()
