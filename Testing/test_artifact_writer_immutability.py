from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core import dialogue_continuity  # noqa: E402
from Data.world_builder import build_item_prefab_library as prefab_library  # noqa: E402
from tools import prepare_dialogue_speech_export_20260715 as speech_export  # noqa: E402


class SpeechExportImmutabilityTests(unittest.TestCase):
    def test_hash_addressed_writer_reuses_only_identical_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            value = {"safe": True, "spoken": "Hello."}
            first, digest = speech_export._immutable_json_artifact(
                output,
                artifact_stem="dialogue_spoken_only",
                value=value,
            )
            original = first.read_bytes()
            second, second_digest = speech_export._immutable_json_artifact(
                output,
                artifact_stem="dialogue_spoken_only",
                value=value,
            )

            self.assertEqual(first, second)
            self.assertEqual(digest, second_digest)
            self.assertEqual(digest, hashlib.sha256(original).hexdigest())
            self.assertIn(f".sha256-{digest}.json", first.name)

            first.write_bytes(b"corrupt prior artifact")
            with self.assertRaisesRegex(RuntimeError, "Refusing to replace"):
                speech_export._immutable_json_artifact(
                    output,
                    artifact_stem="dialogue_spoken_only",
                    value=value,
                )
            self.assertEqual(b"corrupt prior artifact", first.read_bytes())

    def test_main_never_overwrites_legacy_export_or_reparsed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "session.json"
            output = root / "exports"
            output.mkdir()
            source.write_text(
                json.dumps(
                    {
                        "dialogue_id": "immutable_test",
                        "transcript": [
                            {
                                "turn": 1,
                                "speaker": "Kira",
                                "spoken": "Safe hello.",
                                "raw": (
                                    "SPOKEN:\nSafe hello.\n\nPRIVATE MIND:\nPrivate."
                                    "\n\nTRUTH FLAGS:\nconfirmed"
                                ),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            legacy_export = output / "session_spoken_only_privacy_checked.json"
            legacy_reparsed = output / "session_reparsed_review_copy.json"
            legacy_export.write_bytes(b"legacy export must remain")
            legacy_reparsed.write_bytes(b"legacy review must remain")

            stdout = io.StringIO()
            argv = [
                "prepare_dialogue_speech_export_20260715.py",
                str(source),
                "--output-dir",
                str(output),
                "--write-reparsed-review-copy",
            ]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                self.assertEqual(0, speech_export.main())
            result = json.loads(stdout.getvalue())

            self.assertEqual(b"legacy export must remain", legacy_export.read_bytes())
            self.assertEqual(b"legacy review must remain", legacy_reparsed.read_bytes())
            for path_key, hash_key in (
                ("spoken_only_export", "spoken_only_export_sha256"),
                ("reparsed_review_copy", "reparsed_review_copy_sha256"),
            ):
                artifact = Path(result[path_key])
                self.assertTrue(artifact.is_file())
                self.assertNotIn(artifact, {legacy_export, legacy_reparsed})
                actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
                self.assertEqual(actual, result[hash_key])
                self.assertIn(f".sha256-{actual}.json", artifact.name)


class ContinuityCandidateImmutabilityTests(unittest.TestCase):
    def test_candidate_is_hash_addressed_reused_and_never_clobbered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.json"
            source.write_text("{}", encoding="utf-8")
            stable_candidate = {"schema_version": 1, "status": "review_required_not_promoted"}
            legacy = (
                root
                / "Data"
                / "dialogues"
                / "kira_robert_intro"
                / "continuity_candidates"
                / "source.continuity_candidate.json"
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"legacy candidate must remain")

            with patch.object(
                dialogue_continuity,
                "build_continuity_candidate",
                return_value=stable_candidate,
            ):
                first = dialogue_continuity.write_continuity_candidate(
                    {}, source_path=source, project_root=root, contamination_count=0
                )
                second = dialogue_continuity.write_continuity_candidate(
                    {}, source_path=source, project_root=root, contamination_count=0
                )
                self.assertEqual(first, second)
                actual = hashlib.sha256(first.read_bytes()).hexdigest()
                self.assertIn(f".sha256-{actual}.json", first.name)
                self.assertEqual(b"legacy candidate must remain", legacy.read_bytes())

                first.write_bytes(b"corrupt candidate")
                with self.assertRaisesRegex(RuntimeError, "Refusing to replace"):
                    dialogue_continuity.write_continuity_candidate(
                        {}, source_path=source, project_root=root, contamination_count=0
                    )
                self.assertEqual(b"corrupt candidate", first.read_bytes())


class SupplementalManifestAtomicityTests(unittest.TestCase):
    @staticmethod
    def _library(path: Path) -> None:
        path.write_text(json.dumps({"prefabs": []}), encoding="utf-8")

    def test_rejects_source_output_same_resolved_file_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library = root / "library.json"
            self._library(library)
            before = library.read_bytes()

            with self.assertRaisesRegex(ValueError, "must be different files"):
                prefab_library.write_supplemental_interaction_manifest(
                    library_path=library,
                    output_path=root / "missing" / ".." / "library.json",
                )
            self.assertEqual(before, library.read_bytes())

    def test_unique_temp_does_not_collide_with_legacy_fixed_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library = root / "library.json"
            output = root / "manifest.json"
            legacy_temp = root / "manifest.json.tmp"
            self._library(library)
            legacy_temp.write_bytes(b"another process owns this")

            prefab_library.write_supplemental_interaction_manifest(
                library_path=library,
                output_path=output,
            )

            self.assertEqual(b"another process owns this", legacy_temp.read_bytes())
            self.assertEqual([], list(root.glob(".manifest.json.*.tmp")))
            self.assertEqual([], json.loads(output.read_text(encoding="utf-8"))["prefabs"])

    def test_atomic_replace_failure_preserves_output_and_cleans_unique_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library = root / "library.json"
            output = root / "manifest.json"
            self._library(library)
            output.write_bytes(b"published prior report")

            with patch.object(prefab_library.os, "replace", side_effect=OSError("blocked")):
                with self.assertRaisesRegex(OSError, "blocked"):
                    prefab_library.write_supplemental_interaction_manifest(
                        library_path=library,
                        output_path=output,
                    )

            self.assertEqual(b"published prior report", output.read_bytes())
            self.assertEqual([], list(root.glob(".manifest.json.*.tmp")))

    def test_hardlink_alias_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library = root / "library.json"
            alias = root / "alias.json"
            self._library(library)
            try:
                os.link(library, alias)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")
            before = library.read_bytes()

            with self.assertRaisesRegex(ValueError, "must be different files"):
                prefab_library.write_supplemental_interaction_manifest(
                    library_path=library,
                    output_path=alias,
                )
            self.assertEqual(before, library.read_bytes())


if __name__ == "__main__":
    unittest.main()
