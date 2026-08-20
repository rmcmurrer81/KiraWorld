#!/usr/bin/env python3
"""Hostile tests for validate_mind_body_append_only.py.

Every mutation is made inside a TemporaryDirectory.  The accepted workspace
artifacts are copied read-only inputs and are never edited by this suite.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
import validate_mind_body_append_only as validator


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RELATIVES = tuple(validator.EXPECTED_MANIFEST_ENTRIES) + (
    validator.WORK_MANIFEST_PATH,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReadOnlyValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="mind-body-validator-")
        self.root = Path(self.temporary.name)
        (self.root / "outputs").mkdir()
        for relative in FIXTURE_RELATIVES:
            source = SOURCE_ROOT / Path(relative)
            destination = self.root / Path(relative)
            shutil.copy2(source, destination)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def path(self, relative: str) -> Path:
        return self.root / Path(relative)

    def mutate_json(self, relative: str, mutation: Callable[[dict[str, Any]], None]) -> None:
        path = self.path(relative)
        document = json.loads(path.read_text(encoding="utf-8"))
        mutation(document)
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def assert_validation_fails(self, pattern: str) -> None:
        with self.assertRaisesRegex(validator.ValidationError, pattern):
            validator.validate(self.root)

    def test_valid_fixture_passes_without_writing_any_input(self) -> None:
        before = {
            relative: (self.path(relative).stat().st_size, file_sha256(self.path(relative)))
            for relative in FIXTURE_RELATIVES
        }
        result = validator.validate(self.root)
        after = {
            relative: (self.path(relative).stat().st_size, file_sha256(self.path(relative)))
            for relative in FIXTURE_RELATIVES
        }
        self.assertEqual("PASS_STATIC_NO_GO", result["verdict"])
        self.assertTrue(result["read_only"])
        self.assertEqual(0, result["source_writes_performed"])
        self.assertEqual(before, after)

    def test_duplicate_json_key_is_rejected(self) -> None:
        path = self.path(validator.BASELINE_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"schema":"duplicate-probe",', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("duplicate JSON key")

    def test_nonfinite_json_number_is_rejected(self) -> None:
        path = self.path(validator.MIND_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"nonfinite_probe":NaN,', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("nonfinite JSON number")

    def test_overflowed_nonfinite_json_number_is_rejected(self) -> None:
        path = self.path(validator.MIND_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"nonfinite_probe":1e999,', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("nonfinite JSON number")

    def test_checksum_target_tamper_is_rejected(self) -> None:
        path = self.path(validator.MATRIX_PATH)
        text = path.read_text(encoding="utf-8")
        terminal = "Current determination: **STATIC PREPARATION ONLY — NO LIVE, RUNTIME, BLENDER, OUTPUT, OR GO AUTHORITY.**"
        path.write_text(
            text.replace(terminal, "Hostile inserted text.\n\n" + terminal),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("does not match its recorded SHA-256")

    def test_checksum_record_tamper_is_rejected(self) -> None:
        path = self.path(validator.CHECKSUM_PATH)
        text = path.read_text(encoding="utf-8")
        first_digest = text[:64]
        path.write_text(text.replace(first_digest, "0" * 64, 1), encoding="utf-8", newline="\n")
        self.assert_validation_fails("record set or pinned digest mismatch")

    def test_coordinated_artifact_checksum_and_manifest_rehash_is_rejected(self) -> None:
        matrix = self.path(validator.MATRIX_PATH)
        terminal = "Current determination: **STATIC PREPARATION ONLY — NO LIVE, RUNTIME, BLENDER, OUTPUT, OR GO AUTHORITY.**"
        matrix.write_text(
            matrix.read_text(encoding="utf-8").replace(terminal, "Coordinated hostile mutation.\n\n" + terminal),
            encoding="utf-8",
            newline="\n",
        )
        new_digest = file_sha256(matrix)
        checksum = self.path(validator.CHECKSUM_PATH)
        old_digest = validator.EXPECTED_MANIFEST_ENTRIES[validator.MATRIX_PATH].sha256
        checksum.write_text(
            checksum.read_text(encoding="utf-8").replace(old_digest, new_digest),
            encoding="utf-8",
            newline="\n",
        )

        def mutate_manifest(document: dict[str, Any]) -> None:
            for entry in document["mind_body_append_only_artifacts"]:
                if entry["path"] == validator.MATRIX_PATH:
                    entry["bytes"] = matrix.stat().st_size
                    entry["sha256"] = new_digest

        self.mutate_json(validator.WORK_MANIFEST_PATH, mutate_manifest)
        self.assert_validation_fails("record set or pinned digest mismatch")

    def test_work_manifest_identity_claim_tamper_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["mind_body_append_only_artifacts"][0]["bytes"] += 1

        self.mutate_json(validator.WORK_MANIFEST_PATH, mutation)
        self.assert_validation_fails("pinned identities mismatch")

    def test_mind_mapping_count_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_mappings"].pop()

        self.mutate_json(validator.MIND_PATH, mutation)
        self.assert_validation_fails("expected exactly 53 rows")

    def test_mind_materialized_path_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_mappings"][0]["materialized_path"] = "invented/live/path"

        self.mutate_json(validator.MIND_PATH, mutation)
        self.assert_validation_fails("materialized_path: must remain null")

    def test_mind_materialized_pin_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_mappings"][1]["materialized_pin_sha256"] = "0" * 64

        self.mutate_json(validator.MIND_PATH, mutation)
        self.assert_validation_fails("materialized_pin_sha256: must remain null")

    def test_body_class_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["intended_body_v5"]["worksheets"].pop()

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("expected exactly 9 blank schema classes")

    def test_body_populated_intake_value_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            values = document["intended_body_v5"]["worksheets"][0]["values"]
            values[next(iter(values))] = "invented-value"

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("must remain null")

    def test_face_class_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["facial_v4"]["worksheets"].pop()

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("expected exactly 16 blank schema classes")

    def test_face_populated_intake_value_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            values = document["facial_v4"]["worksheets"][0]["values"]
            values[next(iter(values))] = 1

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("must remain null")

    def test_station_scope_stage_slot_is_rejected_when_populated(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12"]["scope_stage_intake_slots"][0]["OWNER_REVIEW"] = {
                "candidate": True
            }

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("OWNER_REVIEW: must remain null")

    def test_station_slot_count_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12"]["scope_stage_intake_slots"].pop()

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("expected six rows")

    def test_station_blank_state_field_count_change_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            del document["station_v12"]["blank_current_state_template"]["asset_identity_sha256"]

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("expected exactly 72 fields")

    def test_station_runtime_elevation_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12"]["blank_current_state_template"]["runtime_authorized"] = True

        self.mutate_json(validator.BODY_PATH, mutation)
        self.assert_validation_fails("must remain null/false")

    def test_baseline_live_elevation_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["global_authority_state"]["live_memory_authorized"] = True

        self.mutate_json(validator.BASELINE_PATH, mutation)
        self.assert_validation_fails("must remain false")

    def test_work_manifest_go_elevation_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["global_authority_state"]["root_go"] = "invented-go"

        self.mutate_json(validator.WORK_MANIFEST_PATH, mutation)
        self.assert_validation_fails("root_go: live/runtime/Blender/output/GO field is elevated")


if __name__ == "__main__":
    unittest.main(verbosity=2)
