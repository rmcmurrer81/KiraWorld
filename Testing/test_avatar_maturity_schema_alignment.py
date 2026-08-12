from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.embodiment_evidence import EMBODIMENT_MATURITY_CLASSES  # noqa: E402
from Core.wearable_component_contract import SUPPORTED_MATURITY_CLASSES  # noqa: E402


class AvatarMaturitySchemaAlignmentTests(unittest.TestCase):
    def _load(self, name: str) -> dict:
        return json.loads(
            (PROJECT_ROOT / "Data" / "schemas" / name).read_text(encoding="utf-8")
        )

    def test_embodiment_approval_artifact_keeps_age_up_as_presentation_only(self) -> None:
        schema = self._load("embodiment_body_approval_artifact_schema.json")
        properties = schema["properties"]
        self.assertEqual(
            set(properties["maturityClass"]["enum"]),
            set(EMBODIMENT_MATURITY_CLASSES),
        )
        self.assertNotIn("adult_aged_up_variant", properties["maturityClass"]["enum"])
        self.assertEqual(
            properties["presentationVariantLabel"]["enum"],
            ["adult_aged_up_variant", None],
        )
        self.assertNotIn("presentationVariantLabel", schema["required"])

    def test_embodiment_registry_matches_active_fail_closed_maturity_set(self) -> None:
        schema = self._load("embodiment_body_approval_registry_schema.json")
        entry = schema["properties"]["entries"]["items"]
        properties = entry["properties"]
        self.assertEqual(
            set(properties["maturityClass"]["enum"]),
            set(EMBODIMENT_MATURITY_CLASSES),
        )
        self.assertNotIn("adult_aged_up_variant", properties["maturityClass"]["enum"])
        self.assertEqual(
            properties["presentationVariantLabel"]["enum"],
            ["adult_aged_up_variant", None],
        )
        self.assertNotIn("presentationVariantLabel", entry["required"])

    def test_wardrobe_registry_matches_active_fail_closed_maturity_set(self) -> None:
        schema = self._load("wardrobe_runtime_approval_registry_schema.json")
        entry = schema["properties"]["entries"]["items"]
        properties = entry["properties"]
        self.assertEqual(
            set(properties["maturity_class"]["enum"]),
            set(SUPPORTED_MATURITY_CLASSES),
        )
        self.assertNotIn("adult_aged_up_variant", properties["maturity_class"]["enum"])
        self.assertEqual(
            properties["presentation_variant_label"]["enum"],
            ["adult_aged_up_variant", None],
        )
        self.assertNotIn("presentation_variant_label", entry["required"])


if __name__ == "__main__":
    unittest.main()
