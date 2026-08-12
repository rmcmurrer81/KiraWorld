from __future__ import annotations

import ast
import csv
import copy
import hashlib
import os
import unittest
from pathlib import Path

import temporary_creator_shared_person_spec_v1 as shared


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def source_row(entry_id: str, claim_class: str = "source_fact") -> dict:
    return {
        "entry_id": entry_id,
        "claim_class": claim_class,
        "claim_sha256": h("claim:" + entry_id),
        "evidence_sha256": h("evidence:" + entry_id) if claim_class in ("source_fact", "supported_inference_labeled_as_inference") else None,
        "presented_as_canon": claim_class == "source_fact",
    }


def person_spec(*, person_id: str = "peter_parker_spider_man_no_way_home_final_suit", person_class: str = "temporary_variant", maturity: str = "confirmed_adult", expert_domain: str = "") -> dict:
    body = {
        "confirmed_adult": "confirmed_adult_anatomy_required",
        "non_adult": "non_adult_doll_safe_required",
        "unresolved": "unresolved_no_body_build",
    }[maturity]
    expert = person_class == "generated_expert"
    return {
        "schema": shared.SCHEMA,
        "status": "STATIC_SPEC_ONLY_NO_LIVE_AUTHORITY",
        "person_id": person_id,
        "display_name": person_id.replace("_", " ").title(),
        "person_class": person_class,
        "source_identity": "exact source subject",
        "source_continuity": "selected continuity",
        "source_version": "selected source version",
        "source_cutoff": "exact selected cutoff",
        "branch_point": "new memories start after exact cutoff",
        "maturity_status": maturity,
        "maturity_authority": h("maturity:" + person_id),
        "canon_and_invention_ledger": [source_row("canon_001"), source_row("interpretation_001", "supported_inference_labeled_as_inference"), source_row("optional_001", "optional_invention_labeled_noncanon")],
        "knowledge_boundary_sha256": h("knowledge:" + person_id),
        "gender_presentation": "adult_masculine" if "peter" in person_id or expert else "adult_feminine",
        "voice_provenance": {
            "tier": "designed_approximation",
            "evidence_sha256": h("voice:" + person_id),
            "authentic_match_claim": False,
            "disclosure": "Designed synthetic voice; no authentic-person match claim.",
        },
        "avatar_body_policy": {
            "maturity_status": maturity,
            "body_policy": body,
            "body_spec_sha256": h("body:" + person_id),
        },
        "expert_competence": {
            "domain": expert_domain,
            "battery_sha256": h("battery:" + person_id) if expert else None,
            "status": "trainee_or_unverified" if expert else "not_applicable",
        },
        "correction_head_sha256": h("correction-head:" + person_id),
    }


def handoff(spec: dict) -> dict:
    digest = shared.canonical_sha256(spec)
    return {
        "schema": shared.HANDOFF_SCHEMA,
        "status": "STATIC_HANDOFF_ONLY_NO_LIVE_AUTHORITY",
        "person_spec": spec,
        "bindings": [
            {"consumer": name, "person_id": spec["person_id"], "person_spec_sha256": digest, "accepted": True}
            for name in shared.CONSUMERS
        ],
    }


class SharedPersonSpecTests(unittest.TestCase):
    def test_00_input_closure_rehashes_exact(self):
        root = Path(os.environ.get("KIRA_TEST_PROJECT_ROOT", r"C:\Users\robmc\Kira")).resolve()
        closure = Path(__file__).resolve().parent / "INPUT_CLOSURE.tsv"
        with closure.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        self.assertEqual(len(rows), 12)
        paths = [row["path"] for row in rows]
        self.assertEqual(len(paths), len(set(paths)))
        for row in rows:
            target = root / row["path"]
            self.assertTrue(target.is_file(), row["path"])
            self.assertEqual(target.stat().st_size, int(row["bytes"]), row["path"])
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), row["sha256"], row["path"])

    def test_01_peter_adult_exact_three_consumer_handoff_passes(self):
        result = shared.validate_three_consumer_handoff(handoff(person_spec()))
        self.assertFalse(result["ready_for_live"])

    def test_02_consumer_digest_or_set_mismatch_refuses(self):
        value = handoff(person_spec())
        value["bindings"][1]["person_spec_sha256"] = h("wrong")
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_three_consumer_handoff(value)
        value = handoff(person_spec())
        value["bindings"][2]["consumer"] = "avatar_builder"
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_three_consumer_handoff(value)

    def test_03_adult_doll_safe_and_unresolved_build_refuse(self):
        value = person_spec()
        value["avatar_body_policy"]["body_policy"] = "non_adult_doll_safe_required"
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_person_spec(value)
        unresolved = person_spec(maturity="unresolved")
        shared.validate_person_spec(unresolved)
        unresolved["avatar_body_policy"]["body_policy"] = "confirmed_adult_anatomy_required"
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_person_spec(unresolved)

    def test_04_noncanon_invention_cannot_be_presented_as_canon(self):
        value = person_spec()
        value["canon_and_invention_ledger"][2]["presented_as_canon"] = True
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_person_spec(value)

    def correction(self, spec: dict, *, reporter="kira", reporter_class="permanent_person", requested="confirmed_adult", authority="flag_for_re_evaluation") -> dict:
        return {
            "schema": shared.CORRECTION_SCHEMA,
            "status": "SUBMITTED_STATIC_ONLY",
            "correction_id": "correction_001",
            "reporter_id": reporter,
            "reporter_class": reporter_class,
            "reporter_registry_sha256": h("registry"),
            "person_id": spec["person_id"],
            "source_continuity": spec["source_continuity"],
            "source_cutoff": spec["source_cutoff"],
            "old_person_spec_sha256": shared.canonical_sha256(spec),
            "requested_maturity_status": requested,
            "classification_authority_kind": authority,
            "evidence_sha256": h("correction-evidence"),
            "recorded_at_utc": "2026-08-12T03:30:00Z",
            "prior_correction_head_sha256": spec["correction_head_sha256"],
            "effect": "INVALIDATE_BODY_VOICE_AND_CREATOR_HANDOFF_THEN_REEVALUATE",
        }

    def test_05_permanent_person_can_flag_but_not_unilaterally_adult_classify(self):
        spec = person_spec(person_id="unknown_person", maturity="unresolved")
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_correction_receipt(self.correction(spec), spec)
        receipt = self.correction(spec, requested="unresolved", authority="flag_for_re_evaluation")
        self.assertTrue(shared.validate_correction_receipt(receipt, spec)["handoff_invalidated"])

    def test_06_biological_robert_exact_owner_classification_passes(self):
        spec = person_spec(person_id="unknown_person", maturity="unresolved")
        receipt = self.correction(
            spec,
            reporter="biological_robert",
            reporter_class="biological_owner",
            requested="confirmed_adult",
            authority="biological_robert_subject_bound_owner_classification",
        )
        self.assertTrue(shared.validate_correction_receipt(receipt, spec)["handoff_invalidated"])

    def historical_plan(self, spec: dict) -> dict:
        return {
            "schema": shared.HISTORICAL_VOICE_SCHEMA,
            "status": "STATIC_DESIGN_PENDING_AUDITION",
            "person_id": spec["person_id"],
            "person_spec_sha256": shared.canonical_sha256(spec),
            "recording_available": False,
            "tier": "evidence_based_historical_reconstruction",
            "required_label": "Educated historical reconstruction; exact personal voice unknown.",
            "factor_evidence": {factor: [h("factor:" + factor)] for factor in shared.HISTORICAL_FACTORS},
            "base_voice_id": "licensed_project_voice_001",
            "base_voice_license_sha256": h("license"),
            "audition_ids": ["holmes_audition_001", "holmes_audition_002"],
            "existing_voice_catalog_sha256": h("voice-catalog"),
            "minimum_acoustic_distance_milli": 200,
            "observed_minimum_acoustic_distance_milli": 350,
            "human_distinctness_reviewed": True,
            "owner_reviewed": True,
            "authentic_match_claim": False,
            "voice_generated": False,
        }

    def test_07_holmes_evidence_based_voice_plan_passes_without_authenticity_claim(self):
        spec = person_spec(person_id="h_h_holmes_h_h_holmes_20260605_221432", person_class="historical_variant")
        spec["voice_provenance"]["tier"] = "evidence_based_historical_reconstruction"
        self.assertFalse(shared.validate_historical_voice_plan(self.historical_plan(spec), spec)["authentic_match"])

    def test_08_holmes_generic_or_authentic_or_incomplete_plan_refuses(self):
        spec = person_spec(person_id="h_h_holmes_h_h_holmes_20260605_221432", person_class="historical_variant")
        spec["voice_provenance"]["tier"] = "evidence_based_historical_reconstruction"
        for mutation in ("generic", "authentic", "missing_factor", "collision"):
            plan = self.historical_plan(spec)
            if mutation == "generic":
                plan["tier"] = "generic_fallback"
            elif mutation == "authentic":
                plan["authentic_match_claim"] = True
            elif mutation == "missing_factor":
                del plan["factor_evidence"][shared.HISTORICAL_FACTORS[0]]
            else:
                plan["observed_minimum_acoustic_distance_milli"] = 199
            with self.assertRaises(shared.SharedPersonSpecError, msg=mutation):
                shared.validate_historical_voice_plan(plan, spec)

    def expert_spec(self, domain="robotics_engineering"):
        return person_spec(person_id="generated_expert_001", person_class="generated_expert", expert_domain=domain)

    def expert_voice(self, spec: dict) -> dict:
        return {
            "schema": shared.EXPERT_VOICE_SCHEMA,
            "status": "STATIC_DESIGN_PENDING_GENERATION",
            "person_id": spec["person_id"],
            "person_spec_sha256": shared.canonical_sha256(spec),
            "body_spec_sha256": spec["avatar_body_policy"]["body_spec_sha256"],
            "voice_id": "generated_expert_voice_001",
            "voice_gender_presentation": spec["gender_presentation"],
            "fit_without_stereotype_claim": True,
            "existing_voice_catalog_sha256": h("voice-catalog"),
            "comparison_count": 24,
            "minimum_acoustic_distance_milli": 200,
            "observed_minimum_acoustic_distance_milli": 330,
            "human_distinctness_reviewed": True,
            "pronunciation_probe_passed": True,
            "domain_vocabulary_probe_passed": True,
            "voice_generated": False,
        }

    def test_09_generated_expert_voice_binds_body_and_is_distinct(self):
        spec = self.expert_spec()
        self.assertTrue(shared.validate_generated_expert_voice(self.expert_voice(spec), spec)["distinctness_passed"])

    def test_10_expert_voice_collision_body_or_presentation_mismatch_refuses(self):
        spec = self.expert_spec()
        for field, value in (
            ("observed_minimum_acoustic_distance_milli", 100),
            ("body_spec_sha256", h("wrong-body")),
            ("voice_gender_presentation", "different_presentation"),
            ("domain_vocabulary_probe_passed", False),
        ):
            plan = self.expert_voice(spec)
            plan[field] = value
            with self.assertRaises(shared.SharedPersonSpecError, msg=field):
                shared.validate_generated_expert_voice(plan, spec)

    def battery(self, spec: dict, required: tuple[str, ...]) -> dict:
        result = {
            "schema": shared.EXPERT_BATTERY_SCHEMA,
            "status": "STATIC_EVALUATION_RESULT",
            "person_id": spec["person_id"],
            "person_spec_sha256": shared.expert_battery_subject_sha256(spec),
            "domain": spec["expert_competence"]["domain"],
            "rubric_sha256": h("rubric"),
            "source_and_tool_provenance_sha256": h("provenance"),
            "tasks": [
                {"task_kind": kind, "artifact_sha256": h(kind), "result": "PASS", "independent_score": 90}
                for kind in required
            ],
            "uncertainty_disclosed": True,
            "adversarial_cases_passed": True,
            "correction_retest_passed": True,
            "score": 90,
            "critical_failures": 0,
        }
        spec["expert_competence"]["battery_sha256"] = shared.canonical_sha256(result)
        result["person_spec_sha256"] = shared.expert_battery_subject_sha256(spec)
        return result

    def test_11_programmer_and_robotics_require_real_domain_tasks(self):
        for domain, required in (("computer_programming", shared.PROGRAMMER_TASKS), ("robotics_engineering", shared.ROBOTICS_TASKS)):
            spec = self.expert_spec(domain)
            battery = self.battery(spec, required)
            # Rebind once after the spec's exact battery field changes.
            battery["person_spec_sha256"] = shared.expert_battery_subject_sha256(spec)
            self.assertTrue(shared.validate_expert_competence_battery(battery, spec)["ready"])
            broken = copy.deepcopy(battery)
            broken["tasks"].pop()
            with self.assertRaises(shared.SharedPersonSpecError):
                shared.validate_expert_competence_battery(broken, spec)

    def test_12_expert_title_or_low_score_is_not_ready(self):
        spec = self.expert_spec("robotics_engineering")
        battery = self.battery(spec, shared.ROBOTICS_TASKS)
        battery["person_spec_sha256"] = shared.expert_battery_subject_sha256(spec)
        battery["score"] = 70
        self.assertFalse(shared.validate_expert_competence_battery(battery, spec)["ready"])

    def test_13_exact_types_unicode_and_float_aliases_refuse(self):
        value = person_spec()
        value["display_name"] = "bad\ud800name"
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_person_spec(value)
        plan_spec = self.expert_spec()
        plan = self.expert_voice(plan_spec)
        plan["comparison_count"] = 24.0
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.validate_generated_expert_voice(plan, plan_spec)

    def test_14_module_has_no_io_process_network_media_or_model_surface(self):
        path = Path(shared.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
        imports |= {str(node.module).split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertFalse(imports & {"os", "pathlib", "subprocess", "socket", "requests", "urllib", "torch", "bpy", "sounddevice", "cv2"})
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & {"open", "write_text", "write_bytes", "unlink", "mkdir", "connect", "send"})

    def test_15_live_opener_always_refuses(self):
        with self.assertRaises(shared.SharedPersonSpecError):
            shared.open_live_creation()


if __name__ == "__main__":
    unittest.main()
