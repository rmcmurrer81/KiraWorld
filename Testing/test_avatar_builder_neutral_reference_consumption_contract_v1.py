from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "Avatar/avatar_builder/body_systems/neutral_reference_consumption_contract_v1.json"
)
MANIFEST_PATH = (
    ROOT / "Avatar/library/neutral_generated_reference_charts_v1/REFERENCE_ASSET_MANIFEST.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


class AvatarBuilderNeutralReferenceConsumptionContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            CONTRACT_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite number: {value}")
            ),
        )
        cls.manifest = json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite number: {value}")
            ),
        )

    def test_contract_binds_exact_current_manifest(self) -> None:
        binding = self.contract["reference_manifest"]
        self.assertEqual(binding["path"], MANIFEST_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(binding["bytes"], MANIFEST_PATH.stat().st_size)
        self.assertEqual(binding["sha256"], sha256(MANIFEST_PATH))

    def test_every_role_resolves_to_one_exact_manifest_asset(self) -> None:
        assets = self.manifest["generated_assets"] + self.manifest["medical_assets"]
        by_name = {Path(asset["path"]).name: asset for asset in assets}
        seen: set[str] = set()
        for role, names in self.contract["roles"].items():
            self.assertIsInstance(role, str)
            self.assertTrue(names)
            for name in names:
                self.assertIn(name, by_name)
                self.assertNotIn(name, seen)
                seen.add(name)
                path = ROOT / by_name[name]["path"]
                self.assertEqual(by_name[name]["bytes"], path.stat().st_size)
                self.assertEqual(by_name[name]["sha256"], sha256(path))
        self.assertEqual(seen, set(by_name))

    def test_generated_and_medical_authority_remain_separate(self) -> None:
        authority = self.contract["authority"]
        self.assertIs(authority["generated_chart_is_medical_authority"], False)
        self.assertIs(authority["generated_chart_is_identity_or_likeness_evidence"], False)
        self.assertIs(authority["medical_diagram_is_identity_or_likeness_evidence"], False)
        self.assertIs(authority["reference_selection_proves_mesh_or_body_function"], False)

    def test_maturity_hair_activation_and_deletion_fail_closed(self) -> None:
        authority = self.contract["authority"]
        rules = self.contract["selection_rules"]
        self.assertIs(authority["appearance_may_classify_maturity"], False)
        self.assertIs(authority["classification_must_come_from_external_durable_person_profile"], True)
        self.assertIs(rules["nonadult_or_unresolved_lane_must_remain_doll_safe_non_anatomical"], True)
        self.assertIs(rules["hair_runtime_instantiation_on_current_32gb_system_allowed"], False)
        self.assertIs(rules["old_photo_deletion_authorized"], False)
        self.assertIs(rules["automatic_blender_execution_authorized"], False)
        self.assertIs(rules["automatic_body_acceptance_authorized"], False)

    def test_downstream_requires_real_candidate_and_owner_evidence(self) -> None:
        evidence = set(self.contract["required_downstream_evidence"])
        self.assertIn("front_side_rear_and_required_pose renders", evidence)
        self.assertIn("intersection_deformation_contact_and_movement results", evidence)
        self.assertIn("owner_visual_decision", evidence)
        self.assertIn("inactive_private_unassigned_unpublished_state", evidence)


if __name__ == "__main__":
    unittest.main()
