from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest import mock

from PIL import Image

from Core.avatar_neutral_chart_utility import (
    NeutralChartUtilityError,
    PASS_PENDING_RENDER,
    apply_skin_material_selector,
    load_skin_selector_map,
)


ROOT = Path(__file__).resolve().parents[1]
SELECTOR_MAP = (
    "Avatar/library/neutral_nonperson_reference_charts_v2/"
    "skin_material_selector_map_v1.json"
)


def synthetic_body():
    return {
        "schema": "kira.avatar.synthetic_material_test_body.v1",
        "body_id": "invented_adult_test_body_01",
        "synthetic_nonperson": True,
        "geometry_sha256": "a" * 64,
        "material_direction": {
            "source_chart_sha256": None,
            "selector_id": None,
            "chart_label": None,
            "base_srgb": [128, 128, 128],
            "regional_srgb": [],
            "calibrated": False,
        },
    }


class AvatarNeutralChartUtilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selector_map = load_skin_selector_map(ROOT, SELECTOR_MAP)

    def test_all_six_selectors_make_repeatable_material_only_changes(self):
        for selector in self.selector_map["selectors"]:
            selector_id = selector["selector_id"]
            first = apply_skin_material_selector(
                self.selector_map, synthetic_body(), selector_id
            )
            second = apply_skin_material_selector(
                self.selector_map, synthetic_body(), selector_id
            )
            self.assertEqual(first, second)
            self.assertEqual(first["status"], PASS_PENDING_RENDER)
            self.assertNotEqual(first["before_sha256"], first["after_sha256"])
            self.assertIs(first["geometry_unchanged"], True)
            self.assertIs(first["repeatable_material_change"], True)
            self.assertIs(first["render_review_passed"], False)
            self.assertIs(first["photo_replacement_accepted"], False)
            self.assertIs(first["photo_deletion_authorized"], False)

    def test_unknown_selector_and_nonsynthetic_fixture_fail_closed(self):
        with self.assertRaisesRegex(NeutralChartUtilityError, "not present"):
            apply_skin_material_selector(
                self.selector_map, synthetic_body(), "skin_row_99"
            )
        body = synthetic_body()
        body["synthetic_nonperson"] = False
        with self.assertRaisesRegex(NeutralChartUtilityError, "synthetic non-person"):
            apply_skin_material_selector(self.selector_map, body, "skin_row_01")

    def test_truth_boundary_cannot_be_promoted_by_selector_data(self):
        for field in self.selector_map["truth"]:
            changed = copy.deepcopy(self.selector_map)
            changed["truth"][field] = True
            with self.assertRaisesRegex(
                NeutralChartUtilityError, "identity is not the audited v1 map"
            ):
                apply_skin_material_selector(changed, synthetic_body(), "skin_row_01")
        receipt = apply_skin_material_selector(
            self.selector_map, synthetic_body(), "skin_row_01"
        )
        self.assertIs(receipt["render_review_passed"], False)
        self.assertIs(receipt["photo_deletion_authorized"], False)

    def test_selector_or_chart_tampering_fails_closed(self):
        changed = copy.deepcopy(self.selector_map)
        changed["selectors"][0]["regional_srgb"][0][0] -= 1
        with self.assertRaisesRegex(NeutralChartUtilityError, "audited v1 map"):
            apply_skin_material_selector(changed, synthetic_body(), "skin_row_01")

    def test_decoded_chart_pixels_must_match_declared_samples(self):
        fake = Image.new("RGB", (1536, 1024), (0, 0, 0))
        fake.format = "PNG"
        with mock.patch(
            "Core.avatar_neutral_chart_utility.Image.open", return_value=fake
        ):
            with self.assertRaisesRegex(
                NeutralChartUtilityError, "pixels do not match skin_row_01"
            ):
                load_skin_selector_map(ROOT, SELECTOR_MAP)

        changed = copy.deepcopy(self.selector_map)
        changed["chart"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(NeutralChartUtilityError, "audited v1 map"):
            apply_skin_material_selector(changed, synthetic_body(), "skin_row_01")

    def test_map_contains_no_real_person_or_local_task_surface(self):
        path = ROOT / SELECTOR_MAP
        lowered = path.read_text(encoding="utf-8").lower()
        self.assertNotIn("real_person_photograph\": true", lowered)
        self.assertNotIn("codex", lowered)
        self.assertNotIn("handoff", lowered)
        self.assertNotIn("c:\\users\\", lowered)


if __name__ == "__main__":
    unittest.main()
