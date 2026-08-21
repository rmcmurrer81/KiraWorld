from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from Core.avatar_anatomy_package import read_glb2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / (
    "Avatar/avatar_builder/asset_library/medical_reference/"
    "hra_female_whole_body_cc_by_4_v1_2"
)
MANIFEST_PATH = PACKAGE_ROOT / "SOURCE_MANIFEST.json"

EXPECTED_FILES = {
    "VH_F_Blood_Vasculature.glb": (
        7262232,
        "4b034a65527938ccbeba4f3514c282bd399a4384fb23ba8095b01e2a3219486a",
        108,
    ),
    "VH_F_Heart.glb": (
        1745284,
        "9afdfb2ccf926869813582cfe150dce8cb28377417a968a4f29a5b8dc060428b",
        14,
    ),
    "VH_F_Kidney_L.glb": (
        1330900,
        "8ac1228e4db8c07cbf9f6c6dc7ca522c5b8d61f641927233a29ae6609b577403",
        15,
    ),
    "VH_F_Kidney_R.glb": (
        1356976,
        "a67508e6948723d34a29fea2bc8c96931a8fe2f8a08293fd1c3161cfcf13968e",
        14,
    ),
    "VH_F_Liver.glb": (
        1738032,
        "ad9b0be0ff253e7bfe31bfffc00017dafce226d4f3e7804a81cbb4c2e269d598",
        26,
    ),
    "VH_F_Lung.glb": (
        11240608,
        "a6a81718f4d0974bcbab47c6dc38efc941ad5c7f5f256bf7ff112c710a7fd932",
        65,
    ),
    "VH_F_Pancreas.glb": (
        216380,
        "7aed6a1c35d5bd8514a8b6c77a8b57f02ffd61ba555e83405d037b8ee4e3d2f3",
        5,
    ),
    "VH_F_Small_Intestine.glb": (
        856388,
        "34cc2d8aa0c782080cadc2e8474a727dce50f829bec3a4857202eba97e110efb",
        9,
    ),
}


def strict_json_load(path: Path) -> dict:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


class HraFemaleWholeBodyReferenceIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = strict_json_load(MANIFEST_PATH)

    def test_exact_file_set_hashes_and_glb_structure(self) -> None:
        records = {record["path"]: record for record in self.manifest["files"]}
        self.assertEqual(set(records), set(EXPECTED_FILES))
        self.assertEqual(
            {path.name for path in PACKAGE_ROOT.glob("*.glb")},
            set(EXPECTED_FILES),
        )

        for name, (expected_bytes, expected_sha256, expected_meshes) in EXPECTED_FILES.items():
            with self.subTest(name=name):
                path = PACKAGE_ROOT / name
                data = path.read_bytes()
                record = records[name]
                self.assertEqual(len(data), expected_bytes)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_sha256)
                self.assertEqual(record["bytes"], expected_bytes)
                self.assertEqual(record["sha256"], expected_sha256)
                self.assertEqual(record["mesh_count"], expected_meshes)
                self.assertEqual(len(read_glb2(path)["meshes"]), expected_meshes)
                self.assertEqual(
                    record["url"],
                    f"https://ccf-ontology.hubmapconsortium.org/objects/v1.2/{name}",
                )

    def test_license_attribution_and_reference_only_scope_are_explicit(self) -> None:
        source = self.manifest["source_collection"]
        self.assertEqual(source["license"], "CC BY 4.0")
        self.assertEqual(
            source["license_url"],
            "https://creativecommons.org/licenses/by/4.0/",
        )
        self.assertIn("Human Reference Atlas", source["attribution"])
        self.assertIn("HuBMAP", source["attribution"])
        self.assertEqual(
            self.manifest["status"],
            "SOURCE_REFERENCE_ONLY_NOT_A_BODY_NOT_FUNCTIONAL",
        )

        boundary = set(self.manifest["truth_boundary"])
        self.assertIn("NO_COMPLETE_WHOLE_BODY_CLAIM", boundary)
        self.assertIn(
            "NO_EATING_DRINKING_DIGESTION_ABSORPTION_OR_RESPIRATION_CLAIM",
            boundary,
        )
        self.assertIn("NO_PHYSIOLOGICAL_OR_SUBJECTIVE_FUNCTION_CLAIM", boundary)
        self.assertIn("NO_RUNTIME_ACTIVATION_OR_ASSIGNMENT", boundary)

    def test_coverage_remains_incomplete_and_contains_no_local_tooling_surface(self) -> None:
        coverage = self.manifest["coverage"]
        self.assertEqual(len(coverage["geometry_present"]), len(EXPECTED_FILES))
        self.assertIn(
            "complete_mouth_pharynx_esophagus_stomach_digestive_route",
            coverage["still_open"],
        )
        self.assertIn("all_biological_function", coverage["still_open"])

        for path in (MANIFEST_PATH, PACKAGE_ROOT / "README.md"):
            lowered = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("codex", lowered)
            self.assertNotIn("handoff", lowered)
            self.assertNotIn("c:\\users\\", lowered)
            self.assertNotIn("file://", lowered)


if __name__ == "__main__":
    unittest.main()
