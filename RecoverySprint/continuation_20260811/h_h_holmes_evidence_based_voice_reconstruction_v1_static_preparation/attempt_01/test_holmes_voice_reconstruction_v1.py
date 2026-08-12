from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
KIRA = Path(os.environ.get("KIRA_PROJECT_ROOT", r"C:\Users\robmc\Kira"))
PLAN_PATH = ROOT / "HOLMES_VOICE_RECONSTRUCTION_TEST_PLAN.json"
MODULE_PATH = ROOT / "holmes_voice_reconstruction_validator_v1.py"

spec = importlib.util.spec_from_file_location("holmes_voice_reconstruction_validator_v1", MODULE_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def raw(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_01_input_closure_exact() -> None:
    rows = []
    for line in (ROOT / "INPUT_CLOSURE.tsv").read_text(encoding="utf-8").splitlines():
        rel, size_text, digest = line.split("\t")
        path = KIRA / Path(rel)
        data = path.read_bytes()
        assert len(data) == int(size_text)
        assert hashlib.sha256(data).hexdigest() == digest
        rows.append(rel)
    assert len(rows) == 9
    assert len(set(rows)) == 9


def test_02_frozen_plan_validates() -> None:
    assert validator.validate_plan_bytes(PLAN_PATH.read_bytes()) == ()


def test_03_strict_json_duplicate_nonfinite_and_bad_utf8_refuse() -> None:
    duplicate = b'{"schema":"a","schema":"b"}'
    with pytest.raises(validator.PlanValidationError, match="duplicate_key"):
        validator.validate_plan_bytes(duplicate)
    with pytest.raises(validator.PlanValidationError, match="nonfinite_number"):
        validator.validate_plan_bytes(b'{"value":NaN}')
    with pytest.raises(validator.PlanValidationError, match="invalid_utf8"):
        validator.validate_plan_bytes(b"\xff")


def test_04_unicode_direction_control_refuses() -> None:
    altered = plan()
    altered["person"]["display_name"] = "H. H. \u202eHolmes"
    with pytest.raises(validator.PlanValidationError, match="forbidden_format_control"):
        validator.validate_plan_bytes(raw(altered))


@pytest.mark.parametrize(
    "field,value,expected",
    [
        (("current_baseline", "may_be_activated_as_holmes_voice"), True, "baseline_no_activation"),
        (("current_baseline", "classification"), "generic_fallback", "baseline_classification"),
        (("recording_boundary", "authentic_or_exact_match_claim_allowed"), True, "no_authentic_claim"),
        (("recording_boundary", "universal_claim_that_no_recording_exists_anywhere"), True, "no_universal_absence_claim"),
        (("candidate_generation", "generic_windows_or_sapi_fallback_allowed"), True, "no_generic_fallback"),
        (("candidate_generation", "generation_authority"), "ONE_RUN", "no_generation_authority"),
    ],
)
def test_05_false_voice_claims_refuse(field: tuple[str, str], value: object, expected: str) -> None:
    altered = plan()
    altered[field[0]][field[1]] = value
    assert expected in validator.validate_plan_bytes(raw(altered))


def test_06_bool_is_not_candidate_count() -> None:
    altered = plan()
    altered["candidate_generation"]["allowed_candidate_count"] = True
    with pytest.raises(validator.PlanValidationError, match="expected_int"):
        validator.validate_plan_bytes(raw(altered))


def test_07_written_and_regional_sources_cannot_become_personal_voice() -> None:
    altered = plan()
    for row in altered["evidence_ledger"]:
        if row["evidence_id"] == "loc_holmes_own_story_1895":
            row["does_not_support"].remove("biometric_voice")
        if row["evidence_id"] == "loc_american_dialect_society_1931_1937":
            row["does_not_support"].remove("Holmes_personal_voice")
    issues = validator.validate_plan_bytes(raw(altered))
    assert "text_not_biometric" in issues
    assert "dialect_not_personal_voice" in issues


def test_08_catalog_and_body_binding_cannot_be_disabled() -> None:
    altered = plan()
    altered["evaluation"]["requires_full_voice_catalog_snapshot_and_cardinality"] = False
    altered["evaluation"]["requires_per_member_acoustic_comparison_with_method_version"] = False
    altered["evaluation"]["requires_body_variant_and_presentation_spec_sha256"] = False
    issues = validator.validate_plan_bytes(raw(altered))
    assert "requires_full_voice_catalog_snapshot_and_cardinality" in issues
    assert "requires_per_member_acoustic_comparison_with_method_version" in issues
    assert "requires_body_variant_and_presentation_spec_sha256" in issues


def test_09_expert_control_stays_unassigned_and_distinct() -> None:
    altered = plan()
    altered["generated_expert_control"]["expert_person_id"] = "unreviewed_expert"
    altered["generated_expert_control"]["body_variant_sha256"] = "0" * 64
    altered["generated_expert_control"]["voice_candidate_sha256"] = "1" * 64
    altered["generated_expert_control"]["may_use_another_persons_voice"] = True
    issues = validator.validate_plan_bytes(raw(altered))
    assert "expert_unselected" in issues
    assert "expert_assets_unresolved" in issues
    assert "expert_no_reuse" in issues


def test_10_all_current_authority_is_exact_false() -> None:
    for key in plan()["current_authority"]:
        altered = plan()
        altered["current_authority"][key] = True
        assert f"authority_false:{key}" in validator.validate_plan_bytes(raw(altered))


def test_11_live_opener_always_refuses() -> None:
    with pytest.raises(RuntimeError, match="NO_GENERATION_OR_PLAYBACK_AUTHORITY"):
        validator.open_generation_or_playback()


def test_12_contract_is_static_only() -> None:
    contract = json.loads((ROOT / "STATIC_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["status"] == "STATIC_DESIGN_ONLY_PENDING_DIFFERENT_REVIEW"
    assert contract["input_closure_rows"] == 9
    assert contract["live_opener"] == "ABSENT"
    assert contract["execution_authority"] == "NONE"
