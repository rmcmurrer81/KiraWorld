from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import intake_avatar_reference_models_20260713 as intake


class AvatarReferenceModelIntakeTests(unittest.TestCase):
    def _model(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"reference-model:" + path.name.encode("utf-8"))

    def test_folder9_subjects_keep_per_subject_maturity_and_reference_only_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "9"
            reference_root = root / "reference_models"
            self._model(source / "beth_smith_nsfw_rick__morty.glb")
            self._model(source / "elsa_frozen_adventures.glb")
            self._model(source / "vincent_van_gogh_ia.glb")

            with (
                patch.object(intake, "REFERENCE_ROOT", reference_root),
                patch.object(intake, "AVATAR_TEMP", root / "avatar_temp"),
                patch.object(intake, "TEMP_CANDIDATES", root / "temp_candidates"),
            ):
                index = intake.intake_folder(source, copy_models=False)

            self.assertEqual(index["copy_mode"], "metadata_only_source_links")
            subjects = {item["subject_id"]: item for item in index["subjects"]}
            self.assertEqual(
                set(subjects),
                {"beth_smith_reference", "elsa_frozen_reference", "vincent_van_gogh_reference"},
            )

            beth = json.loads(
                (reference_root / "beth_smith_reference" / "reference_model_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(beth["maturity_policy"]["maturity_class"], "adult")
            self.assertTrue(beth["models"][0]["adult_only"])
            self.assertFalse(beth["models"][0]["allowed_for_non_adult"])
            self.assertFalse(beth["models"][0]["copy_as_avatar_body_allowed"])
            self.assertEqual(beth["models"][0]["copied_file"], "")

            elsa = json.loads(
                (reference_root / "elsa_frozen_reference" / "reference_model_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(elsa["maturity_policy"]["maturity_class"], "adult")
            self.assertTrue(elsa["maturity_policy"]["adult_anatomy_assets_allowed"])
            self.assertEqual(elsa["maturity_policy"]["supported_versions"]["frozen_2013"]["age"], 21)
            self.assertEqual(elsa["maturity_policy"]["supported_versions"]["frozen_ii_2019"]["age"], 24)
            self.assertTrue(elsa["models"][0]["adult_only"])
            self.assertFalse(elsa["models"][0]["allowed_for_non_adult"])

            vincent = json.loads(
                (reference_root / "vincent_van_gogh_reference" / "reference_model_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(vincent["maturity_policy"]["maturity_class"], "adult")
            self.assertTrue(vincent["models"][0]["adult_only"])
            self.assertFalse(any(reference_root.rglob("*.glb")))

    def test_actor_reference_can_link_to_character_without_copying_or_age_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "5"
            reference_root = root / "reference_models"
            kathryn_id = "kathryn_merteuil_kathryn_merteuil_20260605_213017"
            self._model(source / "sarah_michelle_geller.glb")
            self._model(source / "unrelated_scene.glb")
            (root / "avatar_temp" / kathryn_id).mkdir(parents=True)

            with (
                patch.object(intake, "REFERENCE_ROOT", reference_root),
                patch.object(intake, "AVATAR_TEMP", root / "avatar_temp"),
                patch.object(intake, "TEMP_CANDIDATES", root / "temp_candidates"),
            ):
                index = intake.intake_folder(
                    source,
                    copy_models=False,
                    include_subject_ids={"sarah_michelle_gellar_reference"},
                )

            self.assertEqual(len(index["subjects"]), 1)
            manifest = json.loads(
                (
                    reference_root
                    / "sarah_michelle_gellar_reference"
                    / "reference_model_manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["maturity_policy"]["maturity_class"], "adult")
            self.assertTrue(manifest["models"][0]["reference_only"])
            self.assertFalse(manifest["models"][0]["copy_as_avatar_body_allowed"])
            self.assertTrue(manifest["models"][0]["adult_only"])
            self.assertFalse(manifest["models"][0]["allowed_for_non_adult"])
            self.assertFalse(any(reference_root.rglob("*.glb")))

            link = json.loads(
                (
                    root
                    / "avatar_temp"
                    / kathryn_id
                    / "references"
                    / "model_references"
                    / "sarah_michelle_gellar_reference_manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(link["actor_character_bridge"])
            self.assertIn("face_likeness", link["allowed_reference_uses"])
            self.assertIn("do_not_infer_kathryn_maturity_from_actor_age", link["forbidden_inferences"])


if __name__ == "__main__":
    unittest.main()
