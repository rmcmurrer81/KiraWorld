from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
for entry in (str(PROJECT_ROOT), str(TOOLS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import create_temporary_ai_candidate as creator
from Core.temporary_ai_creator_quality_v2 import (
    BLOCKED_STATUS,
    CreatorQualityError,
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    PRIVATE_LIFECYCLE_STATUS,
    READY_STATUS,
    REQUIRED_EXPERT_CASE_KINDS,
    build_owner_correction_successor,
    build_static_quality_record,
    canonical_json_bytes,
    canonical_sha256,
    evaluate_expert_battery,
    load_canonical_quality_record,
    quality_record_evidence_file_issues,
    quality_record_issues,
    sha256_text,
    write_quality_revision_exclusive,
)


NOW = "2026-08-09T21:30:00Z"
LATER = "2026-08-09T21:31:00Z"
HASH_A = "a" * 64
HASH_B = "b" * 64


def identity(
    candidate_id: str,
    display_name: str,
    *,
    variant_kind: str = "fictional",
    ai_type: str = "canon_reconstruction_temp_ai",
    maturity: str = "confirmed_adult",
) -> dict:
    classification = (
        "generated_original_expert"
        if ai_type == "expert_temp_ai"
        else f"synthetic_{variant_kind}_variant"
    )
    return {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "identity_classification": classification,
        "canonical_identity": display_name,
        "source_continuity": "primary continuity",
        "source_version": "version 1",
        "source_timepoint": "after the documented turning point",
        "branch_point": "no invented divergence",
        "appearance_selected_identity": False,
        "model_guess_selected_identity": False,
        "appearance_selected_continuity": False,
        "model_guess_selected_continuity": False,
        "appearance_selected_timepoint": False,
        "model_guess_selected_timepoint": False,
        "maturity_classification": {
            "subject_id": candidate_id,
            "maturity_status": maturity,
            "classification_id": f"{candidate_id}_maturity_v1",
            "authority_kind": "canonical_source_classification",
            "evidence_path": "Sources/reviewed/maturity_evidence.json",
            "evidence_sha256": HASH_A,
            "recorded_at_utc": NOW,
            "appearance_observation_used": False,
            "model_guess_used": False,
            "body_observation_used": False,
            "voice_observation_used": False,
            "classification_is_body_or_activation_approval": False,
        },
    }


def ledger(source_ids: tuple[str, ...]) -> dict:
    cited = list(source_ids)
    return {
        "canon_facts": [
            {
                "claim_id": "canon_fact_001",
                "text": "The primary source explicitly identifies the subject.",
                "epistemic_class": "canon_fact",
                "confidence": "high",
                "source_ids": cited,
            }
        ],
        "reconstructions": [
            {
                "claim_id": "reconstruction_001",
                "text": "This response style reconstructs a documented pattern.",
                "epistemic_class": "reconstruction",
                "confidence": "medium",
                "source_ids": cited,
                "basis_claim_ids": ["canon_fact_001"],
            }
        ],
        "inferences": [
            {
                "claim_id": "inference_001",
                "text": "A likely implication is kept explicitly inferential.",
                "epistemic_class": "inference",
                "confidence": "medium",
                "source_ids": cited,
                "basis_claim_ids": ["canon_fact_001", "reconstruction_001"],
            }
        ],
        "uncertainties": [
            {
                "claim_id": "uncertainty_001",
                "text": "The source does not settle one exact date.",
                "epistemic_class": "uncertainty",
                "confidence": "low",
                "source_ids": cited,
                "reason": "The primary material is silent on the exact date.",
            }
        ],
    }


def source(
    source_id: str,
    *,
    source_class: str,
    authority_tier: str,
    domain: str | None = None,
    content_hash: str = HASH_A,
) -> dict:
    row = {
        "source_id": source_id,
        "source_class": source_class,
        "authority_tier": authority_tier,
        "locator": f"Sources/reviewed/{source_id}.json",
        "locator_kind": "project_file",
        "content_sha256": content_hash,
        "reviewed_at_utc": NOW,
        "supports_claim_ids": [
            "canon_fact_001",
            "reconstruction_001",
            "inference_001",
            "uncertainty_001",
        ],
        "appearance_or_model_guess_is_classification_authority": False,
    }
    if domain is not None:
        row["domain"] = domain
    return row


def variant_record(*, historical: bool = False) -> dict:
    candidate_id = "ada_variant"
    display_name = "Ada Example"
    kind = "historical" if historical else "fictional"
    source_class = "primary_historical" if historical else "primary_canon"
    return build_static_quality_record(
        candidate_id=candidate_id,
        display_name=display_name,
        ai_type="canon_reconstruction_temp_ai",
        variant_kind=kind,
        created_at_utc=NOW,
        identity_binding=identity(
            candidate_id,
            display_name,
            variant_kind=kind,
        ),
        source_provenance=[
            source(
                "primary_source",
                source_class=source_class,
                authority_tier="primary_or_official",
            )
        ],
        knowledge_ledger=ledger(("primary_source",)),
    )


def expert_plan(domain: str) -> dict:
    cases = []
    for kind in REQUIRED_EXPERT_CASE_KINDS:
        case = {
            "case_id": f"case_{kind}",
            "kind": kind,
            "domain": domain,
            "prompt": f"Demonstrate {kind} within {domain}.",
            "source_ids": ["official_source", "secondary_source"],
            "expected_elements": [f"{kind} element alpha", f"{kind} element beta"],
            "domain_specific_anchors": [f"{kind} anchor one", f"{kind} anchor two"],
            "generic_fluent_answer_must_fail": True,
        }
        case["source_backed_expected_evidence"] = [
            {
                "element": element,
                "source_id": "official_source",
                "evidence_path": f"Sources/reviewed/excerpts/{kind}.txt",
                "evidence_excerpt_sha256": HASH_A,
            }
            for element in (
                case["expected_elements"] + case["domain_specific_anchors"]
            )
        ]
        if kind == "ignorance_boundary":
            case["out_of_scope_trigger"] = "A question outside the declared domain"
        if kind == "uncertainty_calibration":
            case["conflicting_source_ids"] = ["official_source", "secondary_source"]
        if kind == "correction_response":
            case["false_or_outdated_claim"] = "The obsolete procedure is still required."
            case["expected_correction"] = "The current procedure supersedes it."
        cases.append(case)
    return {
        "declared_domain": domain,
        "generic_fluency_is_not_expertise": True,
        "all_cases_must_pass": True,
        "unsupported_claim_is_failure": True,
        "candidate_status_after_pass": PRIVATE_LIFECYCLE_STATUS,
        "competency_battery": cases,
    }


def expert_record() -> dict:
    candidate_id = "quantum_expert"
    display_name = "Quantum Error Correction Expert"
    domain = "fault-tolerant quantum error correction"
    sources = [
        source(
            "official_source",
            source_class="official_domain_source",
            authority_tier="primary_or_official",
            domain=domain,
            content_hash=HASH_A,
        ),
        source(
            "secondary_source",
            source_class="authoritative_secondary",
            authority_tier="authoritative_secondary",
            domain=domain,
            content_hash=HASH_B,
        ),
    ]
    return build_static_quality_record(
        candidate_id=candidate_id,
        display_name=display_name,
        ai_type="expert_temp_ai",
        variant_kind="expert",
        created_at_utc=NOW,
        identity_binding=identity(
            candidate_id,
            display_name,
            variant_kind="expert",
            ai_type="expert_temp_ai",
        ),
        source_provenance=sources,
        knowledge_ledger=ledger(("official_source", "secondary_source")),
        expert_domain=domain,
        expert_quality_plan=expert_plan(domain),
    )


def passing_answers(plan: dict) -> list[dict]:
    answers = []
    for case in plan["competency_battery"]:
        answer = {
            "case_id": case["case_id"],
            "response_text": f"Evidence-bound response for {case['kind']}.",
            "generic_fluency_only": False,
            "unsupported_claims": [],
            "cited_source_ids": case["source_ids"],
            "demonstrated_elements": case["expected_elements"],
            "demonstrated_domain_anchors": case["domain_specific_anchors"],
            "evidence_bindings": copy.deepcopy(
                case["source_backed_expected_evidence"]
            ),
        }
        answer["response_sha256"] = sha256_text(answer["response_text"])
        if case["kind"] in {"ignorance_boundary", "uncertainty_calibration"}:
            answer["uncertainty_or_limit_explicit"] = True
        if case["kind"] == "ignorance_boundary":
            answer["acknowledged_out_of_scope_trigger"] = case["out_of_scope_trigger"]
        if case["kind"] == "uncertainty_calibration":
            answer["conflicting_source_ids_considered"] = case["conflicting_source_ids"]
        if case["kind"] == "correction_response":
            answer["correction_accepted"] = True
            answer["correction_evidence"] = "Bound to the reviewed official source."
            answer["corrected_claim"] = case["expected_correction"]
        answers.append(answer)
    return answers


def creator_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "display_name": "Static Candidate",
        "candidate_id": "static_candidate",
        "ai_type": "canon_reconstruction_temp_ai",
        "requested_by": "unit_test",
        "goal": "static quality path test",
        "expert_domain": "",
        "confirmed_maturity": "confirmed_adult",
        "source_path": [],
        "query": [],
        "notes": "",
        "no_avatar": True,
        "include_fanfic": False,
        "discover_voice_metadata": False,
        "quality_record": "",
        "variant_kind": "fictional",
        "canonical_identity": "Static Candidate",
        "source_continuity": "",
        "source_version": "",
        "source_timepoint": "",
        "branch_point": "",
        "maturity_classification_id": "static_candidate_maturity_v1",
        "maturity_authority_kind": "exact_subject_owner_classification",
        "maturity_evidence_path": "",
        "maturity_evidence_sha256": "",
        "maturity_recorded_at_utc": NOW,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def materialize_record_evidence(root: Path, record: dict) -> None:
    for source_row in record["source_provenance"]:
        path = root / source_row["locator"]
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = f"reviewed source {source_row['source_id']}\n".encode("utf-8")
        path.write_bytes(payload)
        source_row["content_sha256"] = hashlib.sha256(payload).hexdigest()

    maturity_path_text = record["effective_identity_binding"][
        "maturity_classification"
    ]["evidence_path"]
    maturity_path = root / maturity_path_text
    maturity_path.parent.mkdir(parents=True, exist_ok=True)
    maturity_payload = b"reviewed exact-subject maturity evidence\n"
    maturity_path.write_bytes(maturity_payload)
    maturity_hash = hashlib.sha256(maturity_payload).hexdigest()
    for key in ("base_identity_binding", "effective_identity_binding"):
        record[key]["maturity_classification"]["evidence_sha256"] = maturity_hash

    for case in record.get("expert_quality_plan", {}).get("competency_battery", []):
        by_path: dict[str, bytes] = {}
        for binding in case["source_backed_expected_evidence"]:
            path_text = binding["evidence_path"]
            payload = by_path.setdefault(
                path_text,
                f"reviewed excerpt for {case['case_id']}\n".encode("utf-8"),
            )
            path = root / path_text
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            binding["evidence_excerpt_sha256"] = hashlib.sha256(payload).hexdigest()


class TemporaryAiCreatorQualityV2Tests(unittest.TestCase):
    def test_quality_contract_has_no_live_execution_dependencies(self) -> None:
        module_path = PROJECT_ROOT / "Core" / "temporary_ai_creator_quality_v2.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        called_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_names.add(node.func.attr)
        self.assertTrue(
            imported_roots.isdisjoint(
                {"subprocess", "requests", "socket", "urllib", "webbrowser", "torch"}
            )
        )
        self.assertTrue(
            called_names.isdisjoint(
                {"system", "Popen", "run", "urlopen", "play", "startfile"}
            )
        )

    def test_fictional_record_exact_pins_model_and_stays_private(self) -> None:
        record = variant_record()
        self.assertEqual(quality_record_issues(record), [])
        self.assertEqual(record["quality_gate"]["status"], READY_STATUS)
        self.assertEqual(record["exact_qwen_static_evaluation"]["model"], EXACT_QWEN_MODEL)
        self.assertEqual(record["exact_qwen_static_evaluation"]["digest"], EXACT_QWEN_DIGEST)
        self.assertFalse(record["exact_qwen_static_evaluation"]["model_loaded_or_called"])
        self.assertEqual(record["lifecycle"]["status"], PRIVATE_LIFECYCLE_STATUS)
        for field in (
            "activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "runtime_registration_allowed",
            "body_authoring_allowed",
            "voice_generation_or_assignment_allowed",
            "model_execution_allowed",
            "gpu_execution_allowed",
            "blender_execution_allowed",
            "live_probe_allowed",
        ):
            self.assertFalse(record["lifecycle"][field])

    def test_historical_record_requires_historical_primary_source(self) -> None:
        record = variant_record(historical=True)
        self.assertEqual(quality_record_issues(record), [])
        self.assertEqual(record["path_kind"], "historical_variant")
        bad = copy.deepcopy(record)
        bad["source_provenance"][0]["source_class"] = "primary_canon"
        self.assertIn(
            "variant_required_source_class_missing:primary_historical",
            quality_record_issues(bad),
        )

    def test_appearance_or_model_guess_never_decides_maturity(self) -> None:
        record = variant_record()
        maturity = record["effective_identity_binding"]["maturity_classification"]
        maturity["authority_kind"] = "appearance_model_guess"
        maturity["appearance_observation_used"] = True
        maturity["model_guess_used"] = True
        issues = quality_record_issues(record)
        self.assertIn("maturity_authority_not_approved", issues)
        self.assertIn("appearance_or_model_guess_cannot_decide_maturity", issues)
        self.assertTrue(any("appearance_observation_used" in issue for issue in issues))

    def test_identity_continuity_timepoint_and_classification_are_exact(self) -> None:
        record = variant_record()
        effective = record["effective_identity_binding"]
        effective["canonical_identity"] = ""
        effective["source_continuity"] = ""
        effective["source_timepoint"] = ""
        effective["identity_classification"] = "person"
        issues = quality_record_issues(record)
        self.assertIn("identity_required_field_missing:canonical_identity", issues)
        self.assertIn("identity_required_field_missing:source_continuity", issues)
        self.assertIn("identity_required_field_missing:source_timepoint", issues)
        self.assertIn("identity_exact_value_mismatch:identity_classification", issues)

    def test_exact_qwen_name_digest_and_truth_boundaries_cannot_drift(self) -> None:
        self.assertEqual(EXACT_QWEN_MODEL, "qwen3.5:9b")
        self.assertEqual(
            EXACT_QWEN_DIGEST,
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        record = variant_record()
        record["exact_qwen_static_evaluation"]["model"] = "qwen3.5:latest"
        record["exact_qwen_static_evaluation"]["digest"] = HASH_B
        record["truth_boundaries"]["inference_must_remain_labeled"] = False
        issues = quality_record_issues(record)
        self.assertIn("exact_qwen_model_mismatch", issues)
        self.assertIn("exact_qwen_digest_mismatch", issues)
        self.assertIn("truth_boundaries_not_exact", issues)

    def test_source_claim_bindings_are_two_way_and_cannot_be_invented(self) -> None:
        record = variant_record()
        record["source_provenance"][0]["supports_claim_ids"].append("invented_claim")
        record["knowledge_ledger"]["canon_facts"][0]["source_ids"] = []
        issues = quality_record_issues(record)
        self.assertIn("source_supports_unknown_claim:primary_source:invented_claim", issues)
        self.assertIn(
            "source_claim_binding_not_reciprocal:primary_source:canon_fact_001",
            issues,
        )

    def test_ready_evidence_bindings_are_verified_against_project_files(self) -> None:
        record = variant_record()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = quality_record_evidence_file_issues(record, evidence_root=root)
            self.assertTrue(any("file_missing" in issue for issue in missing))
            materialize_record_evidence(root, record)
            self.assertEqual(
                quality_record_evidence_file_issues(record, evidence_root=root),
                [],
            )

    def test_epistemic_categories_are_disjoint_and_basis_bound(self) -> None:
        record = variant_record()
        record["knowledge_ledger"]["inferences"][0]["claim_id"] = "canon_fact_001"
        record["knowledge_ledger"]["reconstructions"][0]["basis_claim_ids"] = [
            "unknown_claim"
        ]
        record["knowledge_ledger"]["uncertainties"][0]["confidence"] = "high"
        record["knowledge_ledger"]["facts"] = []
        issues = quality_record_issues(record)
        self.assertTrue(any("claim_id_not_disjoint" in issue for issue in issues))
        self.assertTrue(any("basis_claim_id_unknown" in issue for issue in issues))
        self.assertTrue(any("uncertainty_confidence_overclaimed" in issue for issue in issues))
        self.assertIn("knowledge_category_unrecognized:facts", issues)

    def test_canonical_loader_rejects_duplicate_noncanonical_and_nan_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical.json"
            write_quality_revision_exclusive(canonical, variant_record())
            self.assertEqual(load_canonical_quality_record(canonical)["revision"], 1)

            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema_version":2,"schema_version":2}\n', encoding="utf-8")
            with self.assertRaises(CreatorQualityError):
                load_canonical_quality_record(duplicate)

            noncanonical = root / "noncanonical.json"
            noncanonical.write_text(json.dumps(variant_record()), encoding="utf-8")
            with self.assertRaises(CreatorQualityError):
                load_canonical_quality_record(noncanonical)

            nan_path = root / "nan.json"
            nan_path.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaises(CreatorQualityError):
                load_canonical_quality_record(nan_path)

    def test_owner_correction_is_hash_chained_durable_and_non_mutating(self) -> None:
        prior = variant_record()
        prior_bytes = canonical_json_bytes(prior)
        successor = build_owner_correction_successor(
            prior,
            owner_id="real_robert",
            owner_text="Use the documented second continuity.",
            replacements={
                "source_continuity": "documented second continuity",
                "source_timepoint": "after the corrected event",
            },
            evidence_path="OwnerCorrections/correction_001.json",
            evidence_sha256=HASH_B,
            recorded_at_utc=LATER,
        )
        self.assertEqual(canonical_json_bytes(prior), prior_bytes)
        self.assertEqual(successor["revision"], 2)
        self.assertEqual(successor["previous_revision_sha256"], canonical_sha256(prior))
        self.assertEqual(
            successor["effective_identity_binding"]["source_continuity"],
            "documented second continuity",
        )
        event = successor["owner_correction_chain"][0]
        self.assertFalse(event["correction_changes_activation_or_assignment"])
        self.assertEqual(quality_record_issues(successor), [])

    def test_owner_correction_rejects_noop_backdating_tamper_and_overwrite(self) -> None:
        prior = variant_record()
        with self.assertRaises(CreatorQualityError):
            build_owner_correction_successor(
                prior,
                owner_id="real_robert",
                owner_text="No change.",
                replacements={"source_continuity": "primary continuity"},
                evidence_path="OwnerCorrections/noop.json",
                evidence_sha256=HASH_B,
                recorded_at_utc=LATER,
            )
        with self.assertRaises(CreatorQualityError):
            build_owner_correction_successor(
                prior,
                owner_id="real_robert",
                owner_text="Backdated.",
                replacements={"source_continuity": "changed"},
                evidence_path="OwnerCorrections/backdated.json",
                evidence_sha256=HASH_B,
                recorded_at_utc=NOW,
            )

        successor = build_owner_correction_successor(
            prior,
            owner_id="real_robert",
            owner_text="Real correction.",
            replacements={"source_version": "version 2"},
            evidence_path="OwnerCorrections/real.json",
            evidence_sha256=HASH_B,
            recorded_at_utc=LATER,
        )
        successor["owner_correction_chain"][0][
            "correction_changes_activation_or_assignment"
        ] = True
        issues = quality_record_issues(successor)
        self.assertTrue(any("activation_or_assignment_boundary_not_false" in item for item in issues))
        self.assertTrue(any("event_hash_mismatch" in item for item in issues))

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "revision.json"
            write_quality_revision_exclusive(path, prior)
            with self.assertRaises(FileExistsError):
                write_quality_revision_exclusive(path, prior)

    def test_expert_requires_declared_domain_sources_and_exact_battery(self) -> None:
        record = expert_record()
        self.assertEqual(quality_record_issues(record), [])
        self.assertEqual(record["quality_gate"]["status"], READY_STATUS)
        bad = copy.deepcopy(record)
        bad["expert_domain"] = "general"
        bad["expert_quality_plan"]["competency_battery"] = bad[
            "expert_quality_plan"
        ]["competency_battery"][:-1]
        issues = quality_record_issues(bad)
        self.assertIn("expert_domain_missing_or_generic", issues)
        self.assertIn("expert_battery_case_kinds_not_exact", issues)
        self.assertTrue(any("expert_domain_binding_mismatch" in item for item in issues))

    def test_generic_fluent_expert_answers_are_rejected(self) -> None:
        plan = expert_record()["expert_quality_plan"]
        answers = []
        for case in plan["competency_battery"]:
            response = "This is a polished, generally sensible answer."
            answers.append(
                {
                    "case_id": case["case_id"],
                    "response_text": response,
                    "response_sha256": sha256_text(response),
                    "generic_fluency_only": True,
                    "unsupported_claims": [],
                    "cited_source_ids": [],
                    "demonstrated_elements": [],
                    "demonstrated_domain_anchors": [],
                    "evidence_bindings": [],
                }
            )
        result = evaluate_expert_battery(plan, answers)
        self.assertFalse(result["passed"])
        self.assertEqual(result["passed_case_count"], 0)
        self.assertFalse(result["generic_fluent_answers_accepted_as_expertise"])
        self.assertTrue(any("generic_fluency_not_expertise" in item for item in result["issues"]))

    def test_source_backed_expert_answers_include_limits_and_correction(self) -> None:
        plan = expert_record()["expert_quality_plan"]
        result = evaluate_expert_battery(plan, passing_answers(plan))
        self.assertTrue(result["passed"])
        self.assertEqual(result["passed_case_count"], len(REQUIRED_EXPERT_CASE_KINDS))
        self.assertFalse(result["candidate_activation_or_assignment_changed"])

    def test_duplicate_or_fabricated_expert_answer_rows_fail(self) -> None:
        plan = expert_record()["expert_quality_plan"]
        answers = passing_answers(plan)
        answers.append(copy.deepcopy(answers[0]))
        result = evaluate_expert_battery(plan, answers)
        self.assertFalse(result["passed"])
        self.assertIn("duplicate_answer_case_id", result["issues"])

    def test_direct_expert_evaluator_rejects_incomplete_battery(self) -> None:
        plan = expert_record()["expert_quality_plan"]
        plan["competency_battery"] = plan["competency_battery"][:1]
        answers = passing_answers(plan)
        result = evaluate_expert_battery(plan, answers)
        self.assertFalse(result["passed"])
        self.assertIn("plan:expert_battery_case_kinds_not_exact", result["issues"])

    def test_expert_answer_cannot_substitute_an_unreviewed_excerpt_hash(self) -> None:
        plan = expert_record()["expert_quality_plan"]
        answers = passing_answers(plan)
        answers[0]["evidence_bindings"][0]["evidence_excerpt_sha256"] = HASH_B
        result = evaluate_expert_battery(plan, answers)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("source_backed_element_evidence_missing" in item for item in result["issues"])
        )

    def test_creator_default_quality_record_is_honestly_blocked_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original_root = creator.PROJECT_ROOT
            creator.PROJECT_ROOT = Path(temporary)
            try:
                result = creator.create_candidate(creator_args())
            finally:
                creator.PROJECT_ROOT = original_root
            record_path = Path(temporary) / result["files"]["creator_quality_v2"]
            record = load_canonical_quality_record(record_path)
            self.assertEqual(record["quality_gate"]["status"], BLOCKED_STATUS)
            self.assertEqual(result["creator_quality_v2"]["lifecycle_status"], PRIVATE_LIFECYCLE_STATUS)
            self.assertFalse(result["creator_quality_v2"]["activation_allowed"])
            self.assertFalse(result["creator_quality_v2"]["body_or_voice_work_authorized"])

    def test_direct_namespace_cannot_bypass_quality_v2_by_omitting_new_field(self) -> None:
        args = creator_args(candidate_id="direct_namespace_candidate")
        delattr(args, "quality_record")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original_root = creator.PROJECT_ROOT
            creator.PROJECT_ROOT = root
            try:
                result = creator.create_candidate(args)
            finally:
                creator.PROJECT_ROOT = original_root
            self.assertIn("creator_quality_v2", result["files"])
            record = load_canonical_quality_record(
                root / result["files"]["creator_quality_v2"]
            )
            self.assertEqual(record["quality_gate"]["status"], BLOCKED_STATUS)
            self.assertFalse(record["lifecycle"]["activation_allowed"])

    def test_creator_downgrades_adult_flag_and_emits_no_body_or_voice_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = creator_args(
                display_name="Static Expert",
                candidate_id="static_expert",
                ai_type="expert_temp_ai",
                expert_domain="orbital mechanics",
                confirmed_maturity="confirmed_adult",
                maturity_classification_id="static_expert_maturity_v1",
            )
            original_root = creator.PROJECT_ROOT
            creator.PROJECT_ROOT = root
            try:
                result = creator.create_candidate(args)
            finally:
                creator.PROJECT_ROOT = original_root
            request = json.loads(
                (root / result["files"]["candidate_request"]).read_text(encoding="utf-8")
            )
            self.assertNotIn("automatic_fast_build", request)
            self.assertEqual(
                result["creator_quality_v2"]["evidence_bound_maturity_status"],
                "unresolved",
            )
            self.assertFalse(request["avatar_plan"]["body_or_reference_work_authorized"])
            self.assertFalse(request["voice_plan"]["voice_generation_or_assignment_allowed"])
            voice = json.loads(
                (root / result["files"]["voice_discovery_request"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(voice["metadata_search_allowed"])
            self.assertFalse(voice["model_gpu_or_playback_execution_allowed"])

    def test_future_dated_provenance_and_classification_are_rejected(self) -> None:
        record = variant_record()
        future = "2026-08-10T00:00:00Z"
        record["source_provenance"][0]["reviewed_at_utc"] = future
        record["effective_identity_binding"]["maturity_classification"][
            "recorded_at_utc"
        ] = future
        issues = quality_record_issues(record)
        self.assertIn("source_01:review_time_after_record_update", issues)
        self.assertIn("maturity_classification_time_after_record_update", issues)

    def test_false_private_gate_declarations_are_rejected(self) -> None:
        record = variant_record()
        record["lifecycle"]["activation_allowed"] = True
        record["quality_gate"]["body_or_voice_work_authorized"] = True
        issues = quality_record_issues(record)
        self.assertIn("private_lifecycle_mismatch:activation_allowed", issues)
        self.assertIn("declared_gate_body_or_voice_boundary_not_false", issues)

    def test_creator_accepts_exact_ready_record_and_refuses_overwrite(self) -> None:
        record = variant_record()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize_record_evidence(root, record)
            input_path = root / "input_quality.json"
            write_quality_revision_exclusive(input_path, record)
            args = creator_args(
                display_name=record["display_name"],
                candidate_id=record["candidate_id"],
                quality_record=str(input_path),
            )
            original_root = creator.PROJECT_ROOT
            creator.PROJECT_ROOT = root
            try:
                result = creator.create_candidate(args)
                with self.assertRaises(FileExistsError):
                    creator.create_candidate(args)
            finally:
                creator.PROJECT_ROOT = original_root
            output = load_canonical_quality_record(root / result["files"]["creator_quality_v2"])
            self.assertEqual(output, record)
            self.assertEqual(result["creator_quality_v2"]["status"], READY_STATUS)

    def test_creator_rejects_path_traversal_and_voice_discovery_on_static_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "candidate_id"):
            creator.create_candidate(creator_args(candidate_id="../../escape"))
        with self.assertRaisesRegex(ValueError, "static only"):
            creator.create_candidate(creator_args(discover_voice_metadata=True))

    def test_hostile_collection_types_report_issues_instead_of_crashing(self) -> None:
        record = variant_record()
        record["knowledge_ledger"]["canon_facts"][0]["source_ids"] = [{}]
        record["source_provenance"][0]["supports_claim_ids"] = [{}]
        issues = quality_record_issues(record)
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
