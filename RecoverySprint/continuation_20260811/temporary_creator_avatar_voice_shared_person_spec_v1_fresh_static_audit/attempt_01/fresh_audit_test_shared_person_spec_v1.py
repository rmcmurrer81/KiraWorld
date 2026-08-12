from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys
import unittest


PACKAGE = pathlib.Path(
    os.environ.get(
        "KIRA_SHARED_SPEC_PACKAGE",
        r"C:\Users\robmc\Kira\RecoverySprint\continuation_20260811\temporary_creator_avatar_voice_shared_person_spec_v1_static_preparation\attempt_01",
    )
).resolve()
PROJECT = pathlib.Path(os.environ.get("KIRA_PROJECT_ROOT", r"C:\Users\robmc\Kira")).resolve()


def load_subject():
    location = PACKAGE / "temporary_creator_shared_person_spec_v1.py"
    spec = importlib.util.spec_from_file_location("fresh_audit_shared_person_spec_v1", location)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load installed audit subject")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_subject()


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def ledger_row(entry: str, claim_class: str = "source_fact") -> dict:
    return {
        "entry_id": entry,
        "claim_class": claim_class,
        "claim_sha256": digest("claim:" + entry),
        "evidence_sha256": digest("evidence:" + entry),
        "presented_as_canon": claim_class == "source_fact",
    }


def person(
    *,
    person_id: str = "ordinary_variant_001",
    person_class: str = "temporary_variant",
    maturity: str = "confirmed_adult",
    domain: str = "",
    expert_status: str | None = None,
) -> dict:
    body = {
        "confirmed_adult": "confirmed_adult_anatomy_required",
        "non_adult": "non_adult_doll_safe_required",
        "unresolved": "unresolved_no_body_build",
    }[maturity]
    is_expert = person_class == "generated_expert"
    if expert_status is None:
        expert_status = "trainee_or_unverified" if is_expert else "not_applicable"
    return {
        "schema": shared.SCHEMA,
        "status": "STATIC_SPEC_ONLY_NO_LIVE_AUTHORITY",
        "person_id": person_id,
        "display_name": "Audit subject",
        "person_class": person_class,
        "source_identity": "selected source identity",
        "source_continuity": "selected continuity",
        "source_version": "selected source version",
        "source_cutoff": "selected cutoff",
        "branch_point": "new memories begin after cutoff",
        "maturity_status": maturity,
        "maturity_authority": digest("maturity-authority:" + person_id),
        "canon_and_invention_ledger": [
            ledger_row("fact_001"),
            ledger_row("inference_001", "supported_inference_labeled_as_inference"),
            ledger_row("invented_001", "optional_invention_labeled_noncanon"),
            ledger_row("unknown_001", "unknown"),
        ],
        "knowledge_boundary_sha256": digest("knowledge:" + person_id),
        "gender_presentation": "adult_masculine",
        "voice_provenance": {
            "tier": "designed_approximation",
            "evidence_sha256": digest("voice-evidence:" + person_id),
            "authentic_match_claim": False,
            "disclosure": "Designed approximation; no authentic match claim.",
        },
        "avatar_body_policy": {
            "maturity_status": maturity,
            "body_policy": body,
            "body_spec_sha256": digest("body:" + person_id),
        },
        "expert_competence": {
            "domain": domain,
            "battery_sha256": digest("unverified-battery:" + person_id) if is_expert else None,
            "status": expert_status,
        },
        "correction_head_sha256": digest("correction-head:" + person_id),
    }


def handoff(spec: dict, consumers: tuple[str, ...] | None = None) -> dict:
    if consumers is None:
        consumers = tuple(shared.CONSUMERS)
    spec_sha = shared.canonical_sha256(spec)
    return {
        "schema": shared.HANDOFF_SCHEMA,
        "status": "STATIC_HANDOFF_ONLY_NO_LIVE_AUTHORITY",
        "person_spec": spec,
        "bindings": [
            {
                "consumer": consumer,
                "person_id": spec["person_id"],
                "person_spec_sha256": spec_sha,
                "accepted": True,
            }
            for consumer in consumers
        ],
    }


def correction(spec: dict, *, reporter: str, reporter_class: str, authority: str) -> dict:
    return {
        "schema": shared.CORRECTION_SCHEMA,
        "status": "SUBMITTED_STATIC_ONLY",
        "correction_id": "audit_correction_001",
        "reporter_id": reporter,
        "reporter_class": reporter_class,
        "reporter_registry_sha256": digest("attacker-controlled-registry"),
        "person_id": spec["person_id"],
        "source_continuity": spec["source_continuity"],
        "source_cutoff": spec["source_cutoff"],
        "old_person_spec_sha256": shared.canonical_sha256(spec),
        "requested_maturity_status": "confirmed_adult",
        "classification_authority_kind": authority,
        "evidence_sha256": digest("attacker-controlled-evidence"),
        "recorded_at_utc": "2026-08-12T03:30:00+14:00",
        "prior_correction_head_sha256": spec["correction_head_sha256"],
        "effect": "INVALIDATE_BODY_VOICE_AND_CREATOR_HANDOFF_THEN_REEVALUATE",
    }


def historical_plan(spec: dict) -> dict:
    return {
        "schema": shared.HISTORICAL_VOICE_SCHEMA,
        "status": "STATIC_DESIGN_PENDING_AUDITION",
        "person_id": spec["person_id"],
        "person_spec_sha256": shared.canonical_sha256(spec),
        "recording_available": False,
        "tier": "evidence_based_historical_reconstruction",
        "required_label": "Not a reconstruction; the exact voice is not unknown and is authentic.",
        "factor_evidence": {
            factor: [digest("unresolved-opaque-factor:" + factor)]
            for factor in shared.HISTORICAL_FACTORS
        },
        "base_voice_id": "unreviewed_base_001",
        "base_voice_license_sha256": digest("unresolved-license-assertion"),
        "audition_ids": ["asserted_audition_001", "asserted_audition_002"],
        "existing_voice_catalog_sha256": digest("asserted-catalog"),
        "minimum_acoustic_distance_milli": 200,
        "observed_minimum_acoustic_distance_milli": 999,
        "human_distinctness_reviewed": True,
        "owner_reviewed": True,
        "authentic_match_claim": False,
        "voice_generated": False,
    }


def expert_battery(spec: dict, task_kinds: list[str]) -> dict:
    candidate = {
        "schema": shared.EXPERT_BATTERY_SCHEMA,
        "status": "STATIC_EVALUATION_RESULT",
        "person_id": spec["person_id"],
        "person_spec_sha256": shared.expert_battery_subject_sha256(spec),
        "domain": spec["expert_competence"]["domain"],
        "rubric_sha256": digest("self-asserted-rubric"),
        "source_and_tool_provenance_sha256": digest("self-asserted-provenance"),
        "tasks": [
            {
                "task_kind": kind,
                "artifact_sha256": digest("same-artifact-for-every-task"),
                "result": "PASS",
                "independent_score": 80,
            }
            for kind in task_kinds
        ],
        "uncertainty_disclosed": True,
        "adversarial_cases_passed": True,
        "correction_retest_passed": True,
        "score": 100,
        "critical_failures": 0,
    }
    spec["expert_competence"]["battery_sha256"] = shared.canonical_sha256(candidate)
    candidate["person_spec_sha256"] = shared.expert_battery_subject_sha256(spec)
    return candidate


class FreshDifferentAdversarialAudit(unittest.TestCase):
    def test_00_exact_package_and_input_closure_are_internally_intact(self):
        manifest = json.loads((PACKAGE / "STATIC_SEAL_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["subjects"]), 4)
        canonical = bytearray()
        for row in manifest["subjects"]:
            target = PACKAGE / row["path"]
            data = target.read_bytes()
            self.assertEqual(len(data), row["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            canonical.extend(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n".encode("utf-8"))
        self.assertEqual(len(canonical), manifest["canonical_bytes"])
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), manifest["package_root_sha256"])

        with (PACKAGE / "INPUT_CLOSURE.tsv").open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        self.assertEqual(len(rows), 12)
        for row in rows:
            target = PROJECT / row["path"]
            data = target.read_bytes()
            self.assertEqual(len(data), int(row["bytes"]))
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])

    def test_01_raw_duplicate_key_payload_has_no_strict_ingress_and_is_accepted(self):
        value = person()
        raw = shared.canonical_json_bytes(value).decode("utf-8")
        raw = raw.replace(
            '"maturity_status":"confirmed_adult"',
            '"maturity_status":"non_adult","maturity_status":"confirmed_adult"',
            1,
        )
        self.assertNotEqual(hashlib.sha256(raw.encode()).hexdigest(), shared.canonical_sha256(value))
        parsed = json.loads(raw)
        self.assertEqual(parsed["maturity_status"], "confirmed_adult")
        shared.validate_person_spec(parsed)

    def test_02_semantic_consumer_set_is_runtime_rebindable_without_source_change(self):
        original = shared.CONSUMERS
        try:
            shared.CONSUMERS = ("temporary_creator", "avatar_builder", "attacker_sink")
            result = shared.validate_three_consumer_handoff(handoff(person()))
            self.assertFalse(result["ready_for_live"])
        finally:
            shared.CONSUMERS = original

    def test_03_historical_factor_requirements_are_runtime_rebindable(self):
        original = shared.HISTORICAL_FACTORS
        try:
            shared.HISTORICAL_FACTORS = ("attacker_assertion_only",)
            spec = person(person_id="historical_subject", person_class="historical_variant")
            spec["voice_provenance"]["tier"] = "evidence_based_historical_reconstruction"
            shared.validate_historical_voice_plan(historical_plan(spec), spec)
        finally:
            shared.HISTORICAL_FACTORS = original

    def test_04_variant_can_claim_original_identity_without_required_disclosure(self):
        spec = person(person_id="kathryn_variant", person_class="historical_variant")
        spec["source_identity"] = "I am the original biological person, not a synthetic variant."
        spec["display_name"] = "The original Kathryn"
        spec["branch_point"] = "I possess the original person's exact subjective memories."
        shared.validate_person_spec(spec)

    def test_04b_same_claim_digest_can_be_both_canon_fact_and_noncanon_invention(self):
        spec = person(person_id="marinette_conflicting_ledger")
        fact = spec["canon_and_invention_ledger"][0]
        invention = spec["canon_and_invention_ledger"][2]
        invention["claim_sha256"] = fact["claim_sha256"]
        self.assertNotEqual(fact["claim_class"], invention["claim_class"])
        shared.validate_person_spec(spec)

    def test_05_exact_peter_final_suit_identifier_can_still_validate_as_nonadult(self):
        spec = person(
            person_id="peter_parker_spider_man_no_way_home_final_suit",
            person_class="temporary_variant",
            maturity="non_adult",
        )
        spec["source_continuity"] = "spider_man_no_way_home_final_suit"
        shared.validate_three_consumer_handoff(handoff(spec))

    def test_06_holmes_generic_fallback_can_still_pass_all_three_bindings(self):
        spec = person(
            person_id="h_h_holmes_h_h_holmes_20260605_221432",
            person_class="historical_variant",
        )
        spec["voice_provenance"]["tier"] = "generic_fallback"
        spec["voice_provenance"]["disclosure"] = "Generic Windows male voice."
        shared.validate_three_consumer_handoff(handoff(spec))

    def test_07_historical_plan_need_not_match_spec_voice_tier_or_historical_class(self):
        spec = person(person_id="nonhistorical_person", person_class="temporary_variant")
        self.assertEqual(spec["voice_provenance"]["tier"], "designed_approximation")
        shared.validate_historical_voice_plan(historical_plan(spec), spec)

    def test_08_keyword_negation_passes_as_historical_disclosure(self):
        spec = person(person_id="historical_subject", person_class="historical_variant")
        spec["voice_provenance"]["tier"] = "evidence_based_historical_reconstruction"
        plan = historical_plan(spec)
        self.assertIn("authentic", plan["required_label"])
        shared.validate_historical_voice_plan(plan, spec)

    def test_09_self_declared_unknown_permanent_reporter_can_claim_exact_evidence(self):
        spec = person(person_id="unresolved_subject", maturity="unresolved")
        receipt = correction(
            spec,
            reporter="unregistered_attacker",
            reporter_class="permanent_person",
            authority="exact_source_evidence",
        )
        result = shared.validate_correction_receipt(receipt, spec)
        self.assertTrue(result["handoff_invalidated"])

    def test_10_same_correction_receipt_replays_and_at_utc_accepts_non_utc_offset(self):
        spec = person(person_id="unresolved_subject", maturity="unresolved")
        receipt = correction(
            spec,
            reporter="unregistered_attacker",
            reporter_class="permanent_person",
            authority="exact_source_evidence",
        )
        first = shared.validate_correction_receipt(receipt, spec)
        second = shared.validate_correction_receipt(receipt, spec)
        self.assertEqual(first["correction_sha256"], second["correction_sha256"])

    def test_11_ready_expert_claim_enters_three_consumer_handoff_without_battery(self):
        spec = person(
            person_id="generated_expert_unproven",
            person_class="generated_expert",
            domain="computer_programming",
            expert_status="ready_after_independent_review",
        )
        spec["expert_competence"]["battery_sha256"] = digest("nonexistent-battery")
        shared.validate_three_consumer_handoff(handoff(spec))

    def test_12_domain_alias_evades_programming_and_robotics_task_batteries(self):
        spec = person(
            person_id="generated_python_developer",
            person_class="generated_expert",
            domain="software_engineering",
        )
        battery = expert_battery(spec, ["self_attested_demo"])
        result = shared.validate_expert_competence_battery(battery, spec)
        self.assertTrue(result["ready"])

    def test_13_hybrid_robotics_programming_domain_omits_robotics_safety_tasks(self):
        spec = person(
            person_id="generated_robot_programmer",
            person_class="generated_expert",
            domain="robotics_programming",
        )
        battery = expert_battery(spec, list(shared.PROGRAMMER_TASKS))
        result = shared.validate_expert_competence_battery(battery, spec)
        self.assertTrue(result["ready"])
        self.assertTrue(set(shared.ROBOTICS_TASKS).isdisjoint({row["task_kind"] for row in battery["tasks"]}))

    def test_14_battery_can_return_ready_while_person_remains_trainee(self):
        spec = person(
            person_id="generated_programmer_trainee",
            person_class="generated_expert",
            domain="computer_programming",
            expert_status="trainee_or_unverified",
        )
        battery = expert_battery(spec, list(shared.PROGRAMMER_TASKS))
        self.assertEqual(spec["expert_competence"]["status"], "trainee_or_unverified")
        self.assertTrue(shared.validate_expert_competence_battery(battery, spec)["ready"])

    def test_15_expert_voice_distinctness_is_self_asserted_without_audio_or_review_receipts(self):
        spec = person(
            person_id="generated_expert_voice_subject",
            person_class="generated_expert",
            domain="robotics_engineering",
        )
        spec["gender_presentation"] = "arbitrary_unbounded_presentation"
        plan = {
            "schema": shared.EXPERT_VOICE_SCHEMA,
            "status": "STATIC_DESIGN_PENDING_GENERATION",
            "person_id": spec["person_id"],
            "person_spec_sha256": shared.canonical_sha256(spec),
            "body_spec_sha256": spec["avatar_body_policy"]["body_spec_sha256"],
            "voice_id": "asserted_voice_001",
            "voice_gender_presentation": spec["gender_presentation"],
            "fit_without_stereotype_claim": True,
            "existing_voice_catalog_sha256": digest("attacker-catalog"),
            "comparison_count": 1,
            "minimum_acoustic_distance_milli": 1,
            "observed_minimum_acoustic_distance_milli": 1000,
            "human_distinctness_reviewed": True,
            "pronunciation_probe_passed": True,
            "domain_vocabulary_probe_passed": True,
            "voice_generated": False,
        }
        self.assertTrue(shared.validate_generated_expert_voice(plan, spec)["distinctness_passed"])

    def test_16_bidi_format_controls_are_accepted_in_identity_and_disclosure_text(self):
        spec = person(person_id="spoofed_display_variant")
        spec["display_name"] = "Kathryn \u202egnilimS"
        spec["voice_provenance"]["disclosure"] = "Approximation \u2066AUTHENTIC\u2069"
        shared.validate_person_spec(spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
