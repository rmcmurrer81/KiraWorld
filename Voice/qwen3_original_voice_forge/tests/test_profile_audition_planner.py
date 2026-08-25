from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import feasibility_worker
import profile_audition_planner as planner


EXPECTED_SUBJECTS = {
    "emily_carter_generated_expert",
    "h_h_holmes",
    "jessica_hale_generated_expert",
    "laura_mitchell_generated_expert",
    "ryan_hale_generated_expert",
    "sarah_bennett_generated_expert",
}
EXCLUDED_IDENTITIES = {
    "beth_smith",
    "kathryn_merteuil_adult_continuation",
    "kira",
    "peter_parker_nwh",
    "robert_mcmurrer",
}


def source_document() -> dict[str, object]:
    return json.loads(planner.EXPECTED_SOURCE_PATH.read_text(encoding="utf-8"))


class ProfileAuditionPlannerTests(unittest.TestCase):
    def test_current_plan_yields_only_six_complete_nonbinding_bundles(self) -> None:
        plan = planner.build_request_plan()
        self.assertEqual(plan["schema"], planner.OUTPUT_SCHEMA)
        self.assertEqual(plan["status"], planner.OUTPUT_STATUS)
        self.assertEqual(len(plan["bundles"]), 6)
        self.assertEqual(
            {bundle["subject_id"] for bundle in plan["bundles"]}, EXPECTED_SUBJECTS
        )
        output_identity_ids = {
            value
            for bundle in plan["bundles"]
            for value in (bundle["subject_id"], bundle["canonical_candidate_id"])
        }
        self.assertTrue(EXCLUDED_IDENTITIES.isdisjoint(output_identity_ids))
        self.assertFalse(plan["policy"]["generated_audio"])
        self.assertFalse(plan["policy"]["binding_created"])
        self.assertFalse(plan["policy"]["activation_allowed"])
        self.assertFalse(plan["policy"]["route_changed"])
        self.assertFalse(plan["policy"]["profile_mutation_performed"])
        self.assertFalse(plan["policy"]["preserved_existing_voice_included"])
        self.assertFalse(plan["policy"]["missing_source_identity_included"])

    def test_requests_are_stable_bounded_and_feasibility_worker_valid(self) -> None:
        first = planner.build_request_plan()
        second = planner.build_request_plan()
        first_ids = [
            variant["request"]["candidate_id"]
            for bundle in first["bundles"]
            for variant in bundle["variants"]
        ]
        second_ids = [
            variant["request"]["candidate_id"]
            for bundle in second["bundles"]
            for variant in bundle["variants"]
        ]
        self.assertEqual(first_ids, second_ids)
        self.assertEqual(len(first_ids), 18)
        self.assertEqual(len(set(first_ids)), 18)
        self.assertTrue(all(len(candidate_id) <= 64 for candidate_id in first_ids))

        source_before = hashlib.sha256(planner.EXPECTED_SOURCE_PATH.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "qwen-request-bundles"
            manifest = planner.write_request_plan(first, output_root)
            self.assertEqual(manifest, output_root / "audition-request-plan.json")
            written = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(written, first)
            for bundle in first["bundles"]:
                for variant in bundle["variants"]:
                    request_path = output_root / variant["request_relative_path"]
                    loaded = feasibility_worker.load_request(request_path)
                    self.assertEqual(loaded, variant["request"])
                    self.assertEqual(
                        feasibility_worker.sha256_file(request_path),
                        variant["request_sha256"],
                    )
        source_after = hashlib.sha256(planner.EXPECTED_SOURCE_PATH.read_bytes()).hexdigest()
        self.assertEqual(source_before, source_after)

    def test_gender_mapping_and_palettes_do_not_guess_missing_dimensions(self) -> None:
        plan = planner.build_request_plan()
        expected_presentations = {
            "emily_carter_generated_expert": "adult_woman",
            "h_h_holmes": "adult_man",
            "jessica_hale_generated_expert": "adult_woman",
            "laura_mitchell_generated_expert": "adult_woman",
            "ryan_hale_generated_expert": "adult_man",
            "sarah_bennett_generated_expert": "adult_woman",
        }
        generic_by_palette: dict[str, dict[str, str]] = {}
        for bundle in plan["bundles"]:
            self.assertEqual(
                bundle["presentation_mapping"]["qwen_presentation"],
                expected_presentations[bundle["subject_id"]],
            )
            self.assertEqual(bundle["locale"]["value"], "en-US")
            self.assertEqual(
                bundle["locale"]["provenance"], "application_audition_default"
            )
            self.assertFalse(bundle["locale"]["sufficient_for_binding"])
            self.assertEqual(
                bundle["locale"]["blocker"],
                "source_locale_confirmation_required_before_binding",
            )
            self.assertIn("body", bundle["unfilled_dimensions_not_guessed"])
            self.assertIn("personality", bundle["unfilled_dimensions_not_guessed"])
            self.assertIn("confirmed_locale", bundle["unfilled_dimensions_not_guessed"])
            self.assertEqual(len(bundle["variants"]), 3)
            for variant in bundle["variants"]:
                traits = dict(variant["request"]["voice_traits"])
                self.assertEqual(
                    traits.pop("presentation"), expected_presentations[bundle["subject_id"]]
                )
                previous = generic_by_palette.setdefault(variant["palette_id"], traits)
                self.assertEqual(previous, traits)

    def test_historical_disclosure_is_exact_and_legacy_voice_is_not_carried(self) -> None:
        plan = planner.build_request_plan()
        historical = next(
            bundle for bundle in plan["bundles"] if bundle["subject_id"] == "h_h_holmes"
        )
        self.assertEqual(historical["required_disclosure"], planner.HISTORICAL_DISCLOSURE)
        self.assertFalse(historical["authenticity_claimed"])
        self.assertFalse(historical["identity_clone_claimed"])
        self.assertFalse(historical["existing_voice_carried_forward"])
        serialized = json.dumps(plan, sort_keys=True)
        self.assertNotIn("h_h_holmes_estimated_voice_v1", serialized)
        for variant in historical["variants"]:
            text = variant["request"]["text"]
            self.assertTrue(text.startswith(planner.HISTORICAL_DISCLOSURE))
            self.assertNotIn("H. H. Holmes", text)
            self.assertEqual(
                variant["request"]["intent"],
                "generated_original_no_named_person_imitation",
            )
            self.assertFalse(variant["request"]["named_person_imitation"])

    def test_duplicate_nonfinite_oversize_and_wrong_schema_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            planner.parse_source_bytes(b'{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, "non-finite"):
            planner.parse_source_bytes(b'{"value":NaN}')
        with self.assertRaisesRegex(ValueError, "size"):
            planner.parse_source_bytes(b" " * (planner.MAX_SOURCE_BYTES + 1))

        document = source_document()
        document["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "keys"):
            planner.validate_source_document(document)
        document = source_document()
        document["schema"] = "kira.local-voice.unknown.v1"
        with self.assertRaisesRegex(ValueError, "schema"):
            planner.validate_source_document(document)

    def test_missing_source_locale_gender_disclosure_and_path_attacks_fail(self) -> None:
        document = source_document()
        eligible = next(
            candidate
            for candidate in document["candidates"]
            if candidate["canonical_candidate_id"]
            == "emily_carter_ai_and_computer_programming_expert_20260605_220651"
        )
        eligible["source_presence"]["profile"] = False
        with self.assertRaisesRegex(ValueError, "source records"):
            planner.validate_source_document(document)

        document = source_document()
        eligible = next(
            candidate
            for candidate in document["candidates"]
            if candidate["canonical_candidate_id"]
            == "emily_carter_ai_and_computer_programming_expert_20260605_220651"
        )
        eligible["audition_brief"]["language"] = "en-GB"
        with self.assertRaisesRegex(ValueError, "locale"):
            planner.validate_source_document(document)

        document = source_document()
        eligible = next(
            candidate
            for candidate in document["candidates"]
            if candidate["canonical_candidate_id"]
            == "emily_carter_ai_and_computer_programming_expert_20260605_220651"
        )
        eligible["audition_brief"]["gender"] = "unknown"
        with self.assertRaisesRegex(ValueError, "presentation"):
            planner.validate_source_document(document)

        document = source_document()
        historical = next(
            candidate
            for candidate in document["candidates"]
            if candidate["canonical_candidate_id"]
            == "h_h_holmes_h_h_holmes_20260605_221432"
        )
        historical["required_disclosure"] = "historical voice"
        with self.assertRaisesRegex(ValueError, "disclosure"):
            planner.validate_source_document(document)

        document = source_document()
        document["source_authority"]["registry_relative_path"] = "../../private.json"
        with self.assertRaisesRegex(ValueError, "relative path"):
            planner.validate_source_document(document)

    def test_trusted_input_and_new_external_output_paths_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            alternate = Path(temporary) / planner.EXPECTED_SOURCE_PATH.name
            alternate.write_bytes(planner.EXPECTED_SOURCE_PATH.read_bytes())
            with self.assertRaisesRegex(ValueError, "trusted integration plan"):
                planner.load_source_plan(alternate)

            relative_output = Path("relative-output")
            with self.assertRaisesRegex(ValueError, "absolute"):
                planner._validate_output_root(relative_output)

            existing = Path(temporary) / "already-exists"
            existing.mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                planner._validate_output_root(existing)

        repository_output = planner.REPOSITORY_ROOT / "forbidden-planner-output"
        with self.assertRaisesRegex(ValueError, "outside"):
            planner._validate_output_root(repository_output)

    def test_modified_in_memory_plan_cannot_be_written(self) -> None:
        plan = planner.build_request_plan()
        modified = deepcopy(plan)
        modified["bundles"][0]["variants"][0]["request_relative_path"] = "../../escape.json"
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "rejected-output"
            with self.assertRaisesRegex(ValueError, "trusted source"):
                planner.write_request_plan(modified, output_root)
            self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()
