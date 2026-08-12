"""Focused regression tests for reusable Avatar Builder method promotion."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_reusable_method_registry import (
    REGISTRY_PATH,
    archived_rejection_entry,
    canonical_sha256,
    evaluate_reusable_method_promotion,
    evaluate_reusable_method_selection,
    private_payload_findings,
    registry_with_promoted_method,
)
from Core.avatar_builder_orchestration import (
    evaluate_avatar_builder_orchestration,
)

REPORT_DIR = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/proofs/"
    "reusable_method_promotion_gate_20260730"
)
REPORT_PATH = REPORT_DIR / "TEST_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )


def binding(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
    }


def make_fixture(root: Path) -> tuple[dict, dict]:
    policy_source = (
        PROJECT_ROOT
        / "Avatar/avatar_builder/policies/"
        "reusable_method_promotion_gate_v1.json"
    )
    policy_target = (
        root
        / "Avatar/avatar_builder/policies/"
        "reusable_method_promotion_gate_v1.json"
    )
    policy_target.parent.mkdir(parents=True, exist_ok=True)
    policy_target.write_bytes(policy_source.read_bytes())

    implementation = (
        root
        / "Avatar/avatar_builder/tooling/reusable_methods/"
        "generic_surface_bridge.py"
    )
    implementation.parent.mkdir(parents=True, exist_ok=True)
    implementation.write_text(
        "def build_generic_bridge(boundary_cycle, transition_rows):\n"
        "    return tuple(boundary_cycle), int(transition_rows)\n",
        encoding="utf-8",
    )
    definition = {
        "method_id": "generic_surface_bridge",
        "method_version": "1.0.0",
        "method_scope": "GENERIC_AVATAR_BUILDER_METHOD",
        "method_kind": "bounded_surface_bridge",
        "method_author_id": "builder_author_a",
        "description": "Build a bounded bridge from a clean ordered cycle.",
        "implementation": binding(root, implementation),
        "parameter_schema": {
            "boundary_cycle_input": "ordered_generic_cycle",
            "transition_rows": "positive_integer"
        },
        "person_specific": False,
        "private_training_data_used": False
    }
    definition_sha = canonical_sha256(definition)

    foundation = (
        root
        / "Avatar/avatar_builder/private_owner_reviews/"
        "foundation_approvals/exact_foundation.blend"
    )
    foundation.parent.mkdir(parents=True, exist_ok=True)
    foundation.write_bytes(b"exact-approved-static-foundation-fixture")
    review = foundation.parent / "owner_review_manifest.json"
    write_json(
        review,
        {
            "schema_version": 1,
            "views": ["front", "rear", "left_profile", "right_profile"],
            "exact_bytes_reviewed": True
        },
    )
    approval = foundation.parent / "owner_approval.json"
    write_json(
        approval,
        {
            "schema_version": 1,
            "artifact_type": (
                "biological_robert_static_foundation_owner_approval"
            ),
            "status": "OWNER_APPROVED_EXACT_FOUNDATION",
            "owner_authority_id": "real_robert",
            "decision": "APPROVE_BIOLOGICAL_ROBERT_STATIC_FOUNDATION",
            "subject_id": "biological_robert",
            "approved_at": "2026-07-30T00:00:00Z",
            "foundation_artifact": binding(root, foundation),
            "owner_review_manifest": binding(root, review),
            "private_source_paths_embedded": False,
            "movement_approved": False,
            "runtime_activation_allowed": False
        },
    )

    fixture_root = (
        root
        / "Avatar/avatar_builder/proofs/generic_method_generalization"
    )
    evidence_a = fixture_root / "generic_adult_a_evidence.json"
    evidence_b = fixture_root / "generic_adult_b_evidence.json"
    write_json(evidence_a, {"passed": True, "fixture": "generic_adult_a"})
    write_json(evidence_b, {"passed": True, "fixture": "generic_adult_b"})
    proof = fixture_root / "generalization_proof.json"
    write_json(
        proof,
        {
            "schema_version": 1,
            "artifact_type": (
                "avatar_builder_reusable_method_generalization_proof"
            ),
            "status": "PASSED",
            "method_id": "generic_surface_bridge",
            "method_version": "1.0.0",
            "method_definition_sha256": definition_sha,
            "method_author_id": "builder_author_a",
            "independent_evaluator": {
                "id": "validator_b",
                "role": (
                    "independent_non_private_generalization_validator"
                )
            },
            "evaluated_at": "2026-07-30T00:10:00Z",
            "fixtures": [
                {
                    "fixture_id": "generic_adult_a",
                    "identity_source_class": (
                        "NON_PRIVATE_SYNTHETIC_FIXTURE"
                    ),
                    "private_data_used": False,
                    "person_specific_source_used": False,
                    "evidence": binding(root, evidence_a)
                },
                {
                    "fixture_id": "generic_adult_b",
                    "identity_source_class": (
                        "NON_PRIVATE_SYNTHETIC_FIXTURE"
                    ),
                    "private_data_used": False,
                    "person_specific_source_used": False,
                    "evidence": binding(root, evidence_b)
                }
            ],
            "results": {
                "topology": True,
                "visual_quality": True,
                "deformation_readiness": True,
                "private_data_exclusion": True,
                "runtime_nonmutation": True
            },
            "runtime_mutation_performed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False
        },
    )
    proposal = {
        "schema_version": 1,
        "submission_type": (
            "AVATAR_BUILDER_REUSABLE_METHOD_PROMOTION_REQUEST"
        ),
        "method_definition": definition,
        "owner_approved_foundation_record": binding(root, approval),
        "generalization_proof": binding(root, proof),
        "runtime_mutation_requested": False,
        "public_export_requested": False
    }
    return proposal, {
        "approval": approval,
        "proof": proof,
    }


def run() -> dict:
    rows: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: object) -> None:
        rows.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    current_selection = evaluate_reusable_method_selection(
        PROJECT_ROOT,
        "same_surface_relief_trial",
    )
    record(
        "current_rejected_method_is_not_selectable",
        current_selection["passed"] is False
        and "reusable_method_not_selectable"
        in current_selection["failures"],
        current_selection,
    )
    orchestration = evaluate_avatar_builder_orchestration(
        {
            "candidate_id": "generic_test_candidate",
            "subject_id": "generic_test_subject",
            "render_requested": False,
            "runtime_activation_requested": False,
            "reusable_method_id": "same_surface_relief_trial",
        },
        project_root=PROJECT_ROOT,
    )
    record(
        "normal_orchestration_blocks_rejected_method_selection",
        orchestration["capability_gates"]["reusable_method_selection"][
            "passed"
        ]
        is False
        and "reusable_method_not_selectable"
        in orchestration["capability_gates"]["reusable_method_selection"][
            "failures"
        ],
        orchestration["capability_gates"]["reusable_method_selection"],
    )

    with tempfile.TemporaryDirectory(prefix="kira_reusable_method_gate_") as tmp:
        root = Path(tmp)
        proposal, paths = make_fixture(root)
        valid = evaluate_reusable_method_promotion(root, proposal)
        record(
            "exact_approval_plus_independent_generalization_passes",
            valid["promotion_allowed"] is True
            and valid["selectable"] is False,
            valid,
        )

        missing_approval = deepcopy(proposal)
        missing_approval["owner_approved_foundation_record"]["path"] = (
            "Avatar/avatar_builder/private_owner_reviews/"
            "foundation_approvals/missing.json"
        )
        blocked = evaluate_reusable_method_promotion(root, missing_approval)
        record(
            "missing_exact_owner_approval_blocks",
            blocked["promotion_allowed"] is False
            and "owner_foundation_record_path_invalid" in blocked["failures"],
            blocked["failures"],
        )

        missing_proof = deepcopy(proposal)
        missing_proof["generalization_proof"]["path"] = (
            "Avatar/avatar_builder/proofs/missing.json"
        )
        blocked = evaluate_reusable_method_promotion(root, missing_proof)
        record(
            "missing_generalization_proof_blocks",
            blocked["promotion_allowed"] is False
            and "generalization_proof_path_invalid" in blocked["failures"],
            blocked["failures"],
        )

        private_variants = {
            "private_photo_path": {
                "source": r"C:\Users\robmc\Desktop\reference\5958.jpg"
            },
            "identity_measurement": {"body_measurements": {"waist_cm": 90}},
            "person_coordinate": {"vertex_deltas": [[1, 0.01, 0.02, 0.03]]},
            "anatomy_observation": {
                "anatomy_observations": ["private visual note"]
            },
            "person_identity": {
                "notes": "Robert-specific repair technique"
            },
        }
        for label, contamination in private_variants.items():
            contaminated = deepcopy(proposal)
            contaminated["method_definition"]["contamination"] = contamination
            blocked = evaluate_reusable_method_promotion(root, contaminated)
            record(
                f"private_payload_blocked_{label}",
                blocked["promotion_allowed"] is False
                and bool(
                    private_payload_findings(
                        contaminated["method_definition"]
                    )
                ),
                blocked["failures"],
            )

        registry = {
            "schema_version": 1,
            "registry_id": "test_registry",
            "selectable_methods": [],
            "rejected_method_archive": [],
        }
        promoted = registry_with_promoted_method(
            registry,
            proposal,
            valid,
            promoted_at="2026-07-30T00:20:00Z",
        )
        registry_file = root / REGISTRY_PATH
        write_json(registry_file, promoted)
        selected = evaluate_reusable_method_selection(
            root,
            "generic_surface_bridge",
        )
        record(
            "only_explicitly_registered_pass_is_selectable",
            selected["passed"] is True,
            selected,
        )

        contaminated = deepcopy(proposal)
        contaminated["method_definition"]["source"] = (
            r"C:\Users\robmc\Desktop\reference\5958.jpg"
        )
        rejected_evaluation = evaluate_reusable_method_promotion(
            root,
            contaminated,
        )
        archived = archived_rejection_entry(
            contaminated,
            rejected_evaluation,
            archived_at="2026-07-30T00:30:00Z",
        )
        serialized = json.dumps(archived).lower()
        record(
            "rejected_archive_omits_raw_private_payload",
            archived["selectable"] is False
            and archived["raw_payload_stored"] is False
            and archived["private_data_stored"] is False
            and "desktop" not in serialized
            and "5958" not in serialized,
            archived,
        )

    passed_count = sum(row["passed"] is True for row in rows)
    report = {
        "schema_version": 1,
        "suite": "avatar_reusable_method_promotion_gate",
        "status": "PASSED" if passed_count == len(rows) else "FAILED",
        "passed": passed_count,
        "failed": len(rows) - passed_count,
        "tests": rows,
        "current_registry": str(REGISTRY_PATH),
        "current_promoted_method_count": 0,
        "runtime_mutation_performed": False,
        "ui_modified": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_PATH, report)
    return report


if __name__ == "__main__":
    result = run()
    print(REPORT_PATH)
    print(json.dumps(result, indent=2))
