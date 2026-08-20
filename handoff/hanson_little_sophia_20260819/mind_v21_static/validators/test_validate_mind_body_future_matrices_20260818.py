#!/usr/bin/env python3
"""Hostile temporary-copy tests for the future-matrix successor validator."""

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
import validate_mind_body_future_matrices_20260818 as validator


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RELATIVES = tuple(
    dict.fromkeys(
        (
            *validator.SOURCE_IDENTITIES,
            *validator.PRIMARY_IDENTITIES,
            *validator.SUCCESSOR_RECORD_IDENTITIES,
            *validator.ORIGINAL_BASE_IDENTITIES,
        )
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FutureMatrixValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="future-matrix-hostile-")
        self.root = Path(self.temporary.name)
        for relative in FIXTURE_RELATIVES:
            source = SOURCE_ROOT / Path(relative)
            destination = self.root / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
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

    def test_valid_successor_passes_without_workspace_writes(self) -> None:
        before = {
            relative: (self.path(relative).stat().st_size, sha256(self.path(relative)))
            for relative in FIXTURE_RELATIVES
        }
        result = validator.validate(self.root)
        after = {
            relative: (self.path(relative).stat().st_size, sha256(self.path(relative)))
            for relative in FIXTURE_RELATIVES
        }
        self.assertEqual("PASS_STATIC_SUCCESSOR_NO_GO", result["verdict"])
        self.assertEqual(2, result["temporary_rebuild_runs"])
        self.assertEqual(0, result["workspace_writes_performed"])
        self.assertEqual(before, after)

    def test_duplicate_matrix_json_key_is_rejected(self) -> None:
        path = self.path(validator.MIND_MATRIX_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"schema":"duplicate-probe",', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("duplicate JSON key")

    def test_literal_nonfinite_matrix_value_is_rejected(self) -> None:
        path = self.path(validator.MIND_MATRIX_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"nonfinite_probe":NaN,', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("nonfinite JSON number")

    def test_overflowed_nonfinite_matrix_value_is_rejected(self) -> None:
        path = self.path(validator.INTAKE_MATRIX_PATH)
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("{", '{"nonfinite_probe":1e999,', 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_validation_fails("nonfinite JSON number")

    def test_builder_identity_tamper_is_rejected(self) -> None:
        path = self.path(validator.BUILDER_PATH)
        path.write_text(path.read_text(encoding="utf-8") + "\n# hostile\n", encoding="utf-8", newline="\n")
        self.assert_validation_fails("target mismatch")

    def test_semantically_neutral_matrix_byte_tamper_is_rejected(self) -> None:
        path = self.path(validator.MIND_MATRIX_PATH)
        path.write_text(" \n" + path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        self.assert_validation_fails("target mismatch")

    def test_successor_checksum_record_tamper_is_rejected(self) -> None:
        path = self.path(validator.SUCCESSOR_CHECKSUM_PATH)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(text[:64], "0" * 64, 1), encoding="utf-8", newline="\n")
        self.assert_validation_fails("exact record set or digest mismatch")

    def test_successor_manifest_identity_tamper_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["generated_matrices"][0]["bytes"] += 1

        self.mutate_json(validator.SUCCESSOR_MANIFEST_PATH, mutation)
        self.assert_validation_fails(r"generated_matrices\[0\]: mismatch")

    def test_coordinated_matrix_checksum_and_manifest_rehash_is_rejected(self) -> None:
        matrix = self.path(validator.MIND_MATRIX_PATH)
        matrix.write_text(" \n" + matrix.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        new_digest = sha256(matrix)
        old_digest = validator.PRIMARY_IDENTITIES[validator.MIND_MATRIX_PATH].sha256
        checksum = self.path(validator.SUCCESSOR_CHECKSUM_PATH)
        checksum.write_text(
            checksum.read_text(encoding="utf-8").replace(old_digest, new_digest),
            encoding="utf-8",
            newline="\n",
        )

        def mutation(document: dict[str, Any]) -> None:
            document["generated_matrices"][0]["bytes"] = matrix.stat().st_size
            document["generated_matrices"][0]["sha256"] = new_digest

        self.mutate_json(validator.SUCCESSOR_MANIFEST_PATH, mutation)
        self.assert_validation_fails(r"generated_matrices\[0\]: mismatch")

    def test_original_checksum_mutation_is_rejected(self) -> None:
        path = self.path(validator.ORIGINAL_CHECKSUM_PATH)
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.assert_validation_fails("byte count")

    def test_source_identity_mutation_is_rejected(self) -> None:
        path = self.path(validator.MIND_SOURCE_PATH)
        path.write_text(" \n" + path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        self.assert_validation_fails("byte count")

    def test_mind_row_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"].pop()

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("expected 53 rows")

    def test_mind_source_projection_drift_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"][0]["future_component"] = "invented-component"

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("source projection mismatch")

    def test_mind_gate_drift_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"][0]["required_gate_ids"].pop()

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("required_gate_ids: mismatch")

    def test_mind_future_evidence_slot_population_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"][0]["future_evidence_slots"]["implementation_component_path"] = "invented/path"

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("implementation_component_path: must remain null")

    def test_mind_runtime_claim_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"][0]["runtime_or_output_claimed"] = True

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("runtime_or_output_claimed: must remain false")

    def test_mind_row_go_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["domain_acceptance_rows"][0]["row_go"] = "invented-go"

        self.mutate_json(validator.MIND_MATRIX_PATH, mutation)
        self.assert_validation_fails("row_go: must remain null")

    def test_intended_body_row_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["intended_body_v5_review_rows"].pop()

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("expected 9 rows")

    def test_facial_receipt_slot_population_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["facial_v4_review_rows"][0]["authentication_receipt_sha256"] = "0" * 64

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("authentication_receipt_sha256: must remain null")

    def test_facial_row_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["facial_v4_review_rows"].pop()

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("expected 16 rows")

    def test_station_row_reduction_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12_scope_stage_review_rows"].pop()

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("expected 24 rows")

    def test_station_action_elevation_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12_scope_stage_review_rows"][0]["request_or_action_emitted"] = True

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("request_or_action_emitted: must remain false")

    def test_station_row_go_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["station_v12_scope_stage_review_rows"][0]["row_go"] = "invented-go"

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("row_go: must remain null")

    def test_equal_person_boundary_drift_is_rejected(self) -> None:
        def mutation(document: dict[str, Any]) -> None:
            document["authority_ceiling"]["ownership_lease_controller_obedience_control_device_tool_or_service_semantics"] = True

        self.mutate_json(validator.INTAKE_MATRIX_PATH, mutation)
        self.assert_validation_fails("authority_ceiling: mismatch")

    def test_mutated_builder_output_fails_independent_rebuild_comparison(self) -> None:
        path = self.path(validator.BUILDER_PATH)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                "G12_INDEPENDENT_FREEZE_AND_STATIC_CEILING",
                "G12_INDEPENDENT_FREEZE_AND_STATIC_CEILINX",
            ),
            encoding="utf-8",
            newline="\n",
        )
        with self.assertRaisesRegex(validator.ValidationError, "not byte-identical"):
            validator.validate_temporary_rebuild(self.root)

    def test_mutated_source_fails_builder_source_pin_in_temporary_rebuild(self) -> None:
        path = self.path(validator.INTAKE_SOURCE_PATH)
        path.write_text(" \n" + path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(validator.ValidationError, "temporary builder run 1 failed"):
            validator.validate_temporary_rebuild(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
